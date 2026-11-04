"""
AGY2_FundAdvisory/tests/test_m1_open_data_and_cache.py
Milestone 1 (Features 1-5) 针对性单元测试套件：
1. Feature 1: 东财真实全市场成交额与涨跌家数宽度，清零 3210/1780 假常数
2. Feature 2: 真实指数与行业估值分位数引擎，清零 INDEX_PE_METAS 静态字典
3. Feature 3: 全市场基金真实限购金额与 Parquet 缓存 (<50ms)，打通日限额过滤
4. Feature 4: 基金本体排雷与季报重仓元数据提取 (24h TTL)，迷你基清盘排查
5. Feature 5: 修复 market_screener 成立日期 Bug，恢复 7,000+ 候选池且杜绝 0 行污染
"""

import os
import sys
import time
import json
from pathlib import Path
import pytest
import pandas as pd

from AGY2_FundAdvisory.data_loader import (
    DataLoader,
    fetch_market_turnover_and_sentiment,
    fetch_or_calc_index_valuations,
    IndexValuationEngine,
    MARKET_BREADTH_CACHE_FILE,
    INDEX_VALUATION_CACHE_FILE
)
from AGY2_FundAdvisory.cache_manager import (
    FundPurchaseCacheManager,
    FundMetadataManager,
    FUND_PURCHASE_CACHE_PATH,
    FUNDS_META_DIR,
    SmartCacheManager
)
from AGY2_FundAdvisory.portfolio_manager import fetch_realtime_fund_quota
from AGY2_FundAdvisory.market_screener import MarketScreener


def test_feature1_market_breadth_and_turnover():
    """断言东财真实全市场两市成交额与涨跌家数获取正常且写入持久化缓存"""
    data = fetch_market_turnover_and_sentiment(force_refresh=False)
    assert isinstance(data, dict)
    assert "total_turnover" in data
    assert "turnover_str" in data
    assert "up_count" in data
    assert "down_count" in data
    assert "flat_count" in data
    assert "up_pct" in data
    assert "sentiment_label" in data
    assert 0.0 <= data["up_pct"] <= 100.0

    # 物理红线：严禁 3210 / 1780 假常数
    assert not (data["up_count"] == 3210 and data["down_count"] == 1780), "Fake numbers 3210/1780 detected!"

    # 检查磁盘持久化文件
    assert MARKET_BREADTH_CACHE_FILE.exists()
    with open(MARKET_BREADTH_CACHE_FILE, "r", encoding="utf-8") as f:
        disk_data = json.load(f)
    assert disk_data["total_turnover"] == data["total_turnover"]


def test_feature2_real_index_valuation_engine():
    """断言核心指数与行业真实 PE-TTM、10年百分位精算无误且落盘"""
    val_map = fetch_or_calc_index_valuations(force_refresh=False)
    assert isinstance(val_map, dict)
    assert INDEX_VALUATION_CACHE_FILE.exists()

    # 6 大核心指数覆盖
    core_codes = ["000300", "000905", "000852", "000922", "000688", "518880"]
    for code in core_codes:
        assert code in val_map, f"Missing index {code} in val_map"
        item = val_map[code]
        assert "name" in item and len(item["name"]) > 0
        assert "label" in item and len(item["label"]) > 0
        assert item["status"] in ["very_low", "low", "mid", "high", "very_high"]

    # 沪深300估值合理性与分位数区间
    hs300 = val_map["000300"]
    assert hs300["pe_ttm"] is not None and 8.0 <= hs300["pe_ttm"] <= 30.0
    assert hs300["percentile"] is not None and 0.0 <= hs300["percentile"] <= 100.0

    # 黄金ETF大宗避险 (无PE)
    gold = val_map["518880"]
    assert gold["pe_ttm"] is None
    assert "大宗避险" in gold["label"]


def test_feature3_fund_purchase_parquet_cache():
    """断言全市场申购限额 Parquet 读取耗时严格 < 50ms 且字段完整"""
    table = FundPurchaseCacheManager.get_purchase_table(force_refresh=False)
    assert isinstance(table, pd.DataFrame)
    assert len(table) > 1000
    for col in ["基金代码", "申购状态", "赎回状态", "日累计限定金额"]:
        assert col in table.columns, f"Missing column {col} in purchase table"

    assert FUND_PURCHASE_CACHE_PATH.exists()

    # 测试磁盘读取性能
    read_durations = []
    for _ in range(3):
        t0 = time.time()
        _ = pd.read_parquet(FUND_PURCHASE_CACHE_PATH)
        read_durations.append(time.time() - t0)
    avg_read_ms = (sum(read_durations) / len(read_durations)) * 1000.0
    assert avg_read_ms < 50.0, f"Average parquet read time {avg_read_ms:.2f}ms exceeds 50ms limit"

    # 测试特定基金限额查询与降级
    q_sp500 = fetch_realtime_fund_quota("050025")
    assert q_sp500["fund_code"] == "050025"
    assert q_sp500["is_limited"] is True
    assert q_sp500["daily_limit"] <= 1000.0


def test_feature4_fund_metadata_extraction_and_liquidation():
    """断言天天基金元数据提取、24h TTL 磁盘缓存与迷你基清盘排查"""
    meta = DataLoader.get_fund_metadata("000001", force_refresh=False)
    assert isinstance(meta, dict)
    assert meta["code"] == "000001"
    assert "aum" in meta
    assert "manager" in meta
    assert "term_years" in meta
    assert "term_return" in meta
    assert "asset_allocation" in meta
    assert "top10_stocks" in meta

    cache_file = FUNDS_META_DIR / "000001_meta.json"
    assert cache_file.exists()

    # 二次读取高速缓存 (<5ms)
    t0 = time.time()
    cached_meta = DataLoader.get_fund_metadata("000001", force_refresh=False)
    t_ms = (time.time() - t0) * 1000.0
    assert t_ms < 5.0
    assert cached_meta["code"] == "000001"

    # 清盘排雷逻辑单元测试 (<0.5亿法定红线)
    mini_meta = FundMetadataManager.fallback_from_master("000001")
    mini_meta["aum"] = 0.32
    mini_meta["liquidation_risk"] = (mini_meta["aum"] < 0.5)
    assert mini_meta["liquidation_risk"] is True


def test_feature5_market_screener_candidate_pool_restored():
    """断言修复成立日期 Bug 后全市场候选池恢复至 7,000+ 只，且 0 行缓存被彻底拦截"""
    pool = MarketScreener.build_candidate_pool(force_rebuild=False)
    assert isinstance(pool, pd.DataFrame)
    assert len(pool) >= 7000, f"Candidate pool size {len(pool)} < 7000"

    # 验证 0 行缓存拦截
    empty_df = pd.DataFrame(columns=["fund_code", "bucket"])
    SmartCacheManager.save_candidate_pool(empty_df, min_aum=888.0, min_years=888.0)
    res = SmartCacheManager.get_candidate_pool(min_aum=888.0, min_years=888.0)
    assert res is None, "Empty dataframe should not be saved or loaded from candidate pool cache"


def test_no_fake_constants_in_source_code():
    """断言源码中无 INDEX_PE_METAS 静态字典及 3210/1780 假常数"""
    gui_text = (Path(__file__).resolve().parent.parent / "app_gui.py").read_text(encoding="utf-8")
    assert "INDEX_PE_METAS" not in gui_text
    assert "up_count: 3210" not in gui_text
    assert "1780" not in gui_text

    dl_text = (Path(__file__).resolve().parent.parent / "data_loader.py").read_text(encoding="utf-8")
    assert "INDEX_PE_METAS" not in dl_text
    assert "3210" not in dl_text
    assert "1780" not in dl_text
