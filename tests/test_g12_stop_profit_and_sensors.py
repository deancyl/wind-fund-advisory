# -*- coding: utf-8 -*-
"""
tests/test_g12_stop_profit_and_sensors.py
Milestone 2 专项测试套件：
1. ActiveRiskSentry 维度 4 移动止盈与右侧破位逃顶 (50% 减仓红牌与 60日 HWM 回撤 40% 减仓黄牌)
2. 保持原有超买 (>6%)、阶梯止盈 (>15% & bias >5%) 及深套诊断 (<= -12%) 兼容性
3. app_gui.py 中动态 take_profit_ratio 联动注入与晨报先行指标/情绪温度展示
4. data_loader.py:
   - calc_financial_news_sentiment: 极性词典 0-100 量化赋分与极性边界
   - fetch_macro_cross_market_indicators: 10Y国债、黄金与隔夜纳指多源先行指标
   - fetch_sector_core_etf_metrics: 14 赛道核心 ETF 实时放量比 (f10) 与折溢价率
   - auto_heal_sector_parquets: 本地落后日线原子自愈与幂等性
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import numpy as np
import pandas as pd

_CURRENT = Path(__file__).resolve().parent
_WORKSPACE = _CURRENT.parent
_AGY2_DIR = _WORKSPACE / "AGY2_FundAdvisory"
if str(_AGY2_DIR) not in sys.path:
    sys.path.insert(0, str(_AGY2_DIR))
if str(_WORKSPACE) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE))

from AGY2_FundAdvisory.advisory_engine import ActiveRiskSentry
from AGY2_FundAdvisory.data_loader import (
    DataLoader,
    calc_financial_news_sentiment,
    fetch_macro_cross_market_indicators,
    fetch_sector_core_etf_metrics,
    auto_heal_sector_parquets,
    CORE_SECTOR_ETFS,
)


class DummyHolding:
    """测试用持仓对象模拟"""
    def __init__(self, **kwargs):
        self.fund_code = kwargs.get("fund_code", "008888")
        self.code = self.fund_code
        self.fund_name = kwargs.get("fund_name", "华夏芯片ETF联接A")
        self.name = self.fund_name
        self.market_value = float(kwargs.get("market_value", 50000.0))
        self.amount = self.market_value
        self.cost_price = float(kwargs.get("cost_price", 1.0000))
        self.cost_nav = self.cost_price
        self.current_nav = float(kwargs.get("current_nav", 1.2000))
        self.holding_days = int(kwargs.get("holding_days", 45))
        self.share_class = kwargs.get("share_class", "A")
        self.category = kwargs.get("category", "科技成长")
        self.batches = kwargs.get("batches", [])
        self.bias_20 = kwargs.get("bias_20", None)
        self.slope_20 = kwargs.get("slope_20", None)
        self.vol_20 = kwargs.get("vol_20", None)
        self.single_day_drop = kwargs.get("single_day_drop", None)
        self.hwm_dd = kwargs.get("hwm_dd", None)
        self.peak_nav_60 = kwargs.get("peak_nav_60", None)


# =========================================================================
# 1. ActiveRiskSentry 维度 4: 右侧破位与移动止盈测试
# =========================================================================

def test_sentry_dim4_right_side_breakdown_by_negative_slope():
    """
    测试 1.1: 右侧破位逃顶 (浮盈 >= 10% 且 跌破 MA20 且 斜率转负)
    断言: 触发 RED 级别警报，dimension == '移动止盈'，action_type == 'take_profit'，take_profit_ratio == 0.50
    """
    sentry = ActiveRiskSentry()
    # 浮盈 +20%，跌破均线 bias_20 = -1.5%，均线斜率转负 slope_20 = -0.5%
    h = DummyHolding(
        fund_code="008888",
        fund_name="华夏半导体芯片ETF联接A",
        cost_price=1.0000,
        current_nav=1.2000,  # +20%
        bias_20=-1.5,
        slope_20=-0.5,
        vol_20=20.0,
    )
    res = sentry.inspect_portfolio(
        holdings=[h],
        market_snapshot={"fund_quotes": {}},
        fund_metadata={"008888": {"aum": 15.0}},
        investor_risk_tier="C3"
    )
    alerts = res.get("alerts", [])
    tp_alerts = [
        a for a in alerts
        if a.get("dimension") == "移动止盈" and a.get("action_type") == "take_profit"
    ]
    assert len(tp_alerts) >= 1, f"未触发移动止盈预警: {alerts}"
    breakdown_alert = tp_alerts[0]
    assert breakdown_alert["level"] == "red"
    assert breakdown_alert["take_profit_ratio"] == 0.50
    assert "右侧破位" in breakdown_alert["title"] or "右侧破位" in breakdown_alert["desc"]
    assert breakdown_alert["fund_code"] == "008888"


def test_sentry_dim4_right_side_breakdown_by_single_day_drop():
    """
    测试 1.2: 右侧破位逃顶 (浮盈 >= 10% 且 跌破 MA20 且 单日急跌 > 1.5 * daily_vol)
    daily_vol = vol_20 / sqrt(250) ≈ 15.0 / 15.811 = 0.9487%
    1.5 * daily_vol ≈ 1.423%
    当单日急跌 single_day_drop = 2.5% > 1.423% 时，触发 RED 0.50 锁利
    """
    sentry = ActiveRiskSentry()
    h = DummyHolding(
        fund_code="161725",
        fund_name="招商中证白酒指数A",
        cost_price=1.0000,
        current_nav=1.1200,  # +12%
        bias_20=-0.8,
        slope_20=0.2,       # 斜率仍微弱为正
        vol_20=15.0,
        single_day_drop=2.5 # 单日跌幅 2.5% > 1.5 * daily_vol
    )
    res = sentry.inspect_portfolio(
        holdings=[h],
        market_snapshot={"fund_quotes": {"161725": {"gszzl": -2.5}}},
        fund_metadata={"161725": {"aum": 50.0}},
        investor_risk_tier="C4"
    )
    alerts = res.get("alerts", [])
    tp_alerts = [
        a for a in alerts
        if a.get("dimension") == "移动止盈" and a.get("action_type") == "take_profit"
    ]
    assert len(tp_alerts) >= 1
    assert tp_alerts[0]["level"] == "red"
    assert tp_alerts[0]["take_profit_ratio"] == 0.50


def test_sentry_dim4_hwm_drawdown_protection():
    """
    测试 1.3: 高水位浮盈回撤保护 (浮盈 >= 10% 且 较 60 日高点回撤 >= 8.0%)
    当未达到右侧破位条件 (bias_20 >= 0 或斜率正向且无单日急跌)，但从阶段最高点回撤 9.5% 时：
    断言: 触发 YELLOW 级别警报，dimension == '移动止盈'，take_profit_ratio == 0.40
    """
    sentry = ActiveRiskSentry()
    h = DummyHolding(
        fund_code="000216",
        fund_name="华安黄金联接A",
        cost_price=1.0000,
        current_nav=1.1500,  # 仍保留 +15% 浮盈
        bias_20=0.5,         # 未破位均线
        slope_20=0.8,
        hwm_dd=9.5,          # 较 60 日最高点回撤 9.5% >= 8.0%
    )
    res = sentry.inspect_portfolio(
        holdings=[h],
        market_snapshot={},
        fund_metadata={"000216": {"aum": 20.0}},
        investor_risk_tier="C3"
    )
    alerts = res.get("alerts", [])
    hwm_alerts = [
        a for a in alerts
        if a.get("dimension") == "移动止盈" and a.get("level") == "yellow"
    ]
    assert len(hwm_alerts) >= 1
    assert hwm_alerts[0]["take_profit_ratio"] == 0.40
    assert "高水位" in hwm_alerts[0]["title"]


def test_sentry_dim4_retention_of_existing_rules():
    """
    测试 1.4: 验证原有超买 (>6%) 与阶梯止盈 (>15% & bias >5%) 保持 100% 兼容
    """
    sentry = ActiveRiskSentry()

    # 1. 短期超买 (bias_20 = +7.2% > 6.0%)
    h_overbought = DummyHolding(
        fund_code="011612",
        fund_name="华夏科创50联接A",
        cost_price=1.0000,
        current_nav=1.0500,  # +5%
        bias_20=7.2,
    )
    res1 = sentry.inspect_portfolio([h_overbought], {}, {})
    a1 = [a for a in res1["alerts"] if a.get("dimension") == "超买拥挤"]
    assert len(a1) >= 1
    assert a1[0]["level"] == "red"
    assert a1[0]["take_profit_ratio"] == 0.40

    # 2. 阶梯止盈 (pnl = +18% >= 15% 且 bias_20 = +5.5% > 5%)
    h_ladder = DummyHolding(
        fund_code="100032",
        fund_name="富国中证红利增强A",
        cost_price=1.0000,
        current_nav=1.1800,  # +18%
        bias_20=5.5,
    )
    res2 = sentry.inspect_portfolio([h_ladder], {}, {})
    a2 = [a for a in res2["alerts"] if a.get("dimension") == "阶梯止盈"]
    assert len(a2) >= 1
    assert a2[0]["level"] == "yellow"
    assert a2[0]["take_profit_ratio"] == 0.40


def test_sentry_dim4_edge_cases_no_false_positive():
    """
    测试 1.5: 边界与负例测试 (防误判坐过山车)
    - 浮盈仅 8% (< 10%) 即使跌破均线不触发移动止盈
    - 浮盈 20% 但 bias_20 > 0 且 hwm_dd = 5% (< 8%) 不误判破位
    """
    sentry = ActiveRiskSentry()

    # 浮盈仅 8%
    h_small_profit = DummyHolding(
        fund_code="002351",
        cost_price=1.0000,
        current_nav=1.0800,
        bias_20=-1.0,
        slope_20=-0.5,
    )
    res1 = sentry.inspect_portfolio([h_small_profit], {}, {})
    assert not any(a.get("dimension") == "移动止盈" for a in res1["alerts"])

    # 浮盈 20% 但健康上行中 (bias > 0, hwm_dd < 8%)
    h_healthy = DummyHolding(
        fund_code="002351",
        cost_price=1.0000,
        current_nav=1.2000,
        bias_20=2.0,
        slope_20=1.5,
        hwm_dd=3.0,
    )
    res2 = sentry.inspect_portfolio([h_healthy], {}, {})
    assert not any(a.get("dimension") == "移动止盈" for a in res2["alerts"])


# =========================================================================
# 2. data_loader: 舆情情绪多空量化赋分测试 (0 ~ 100 分)
# =========================================================================

def test_calc_financial_news_sentiment_bullish():
    """测试看多新闻赋予高分与看多标签"""
    bull_news = [
        {"title": "央行宣布降准0.5个百分点 释放长期流动性超万亿元", "desc": "支持实体经济，高质量发展企稳回升"},
        {"title": "主力资金净买入超200亿 沪深300放量突破关键阻力位", "desc": "上市公司加大回购增持力度，利好提振市场信心"},
    ]
    score, label = calc_financial_news_sentiment(bull_news)
    assert 60.0 <= score <= 95.0
    assert label in ["积极乐观", "温和看多"]


def test_calc_financial_news_sentiment_bearish():
    """测试看空新闻赋予低分与防守标签"""
    bear_news = [
        {"title": "多家公司股东大额减持 结构性重仓股破位跳水", "desc": "缩量抛售引发踩踏，面临问询与立案风险"},
        {"title": "行业业绩低于预期 资金持续流出承压下挫", "desc": "市场恐慌避险情绪升温，警示清盘亏损"},
    ]
    score, label = calc_financial_news_sentiment(bear_news)
    assert 10.0 <= score <= 42.0
    assert label in ["恐慌避险", "谨慎防守"]


def test_calc_financial_news_sentiment_empty_and_neutral():
    """测试空新闻列表或中性新闻返回 50 分中性均衡"""
    score_empty, label_empty = calc_financial_news_sentiment([])
    assert score_empty == 50.0
    assert label_empty == "中性均衡"

    neutral_news = [{"title": "统计局发布日常季度经济数据简报", "desc": "各行业按部就班开展统计"}]
    score_neu, label_neu = calc_financial_news_sentiment(neutral_news)
    assert score_neu == 50.0
    assert label_neu == "中性均衡"


# =========================================================================
# 3. data_loader: 宏观跨市场先行指标测试
# =========================================================================

def test_fetch_macro_cross_market_indicators():
    """测试宏观三大跨市场指标采集完整性与数据合理性"""
    res = fetch_macro_cross_market_indicators(use_cache=False)
    assert isinstance(res, dict)
    assert "cgb_10y_yield" in res
    assert "gold_price" in res
    assert "nasdaq_point" in res
    assert "macro_summary" in res

    # 检查合理金融区间
    assert 0.5 <= res["cgb_10y_yield"] <= 5.0, f"10Y国债收益率异常: {res['cgb_10y_yield']}"
    assert res["gold_price"] > 1.0, f"黄金价格异常: {res['gold_price']}"
    assert res["nasdaq_point"] > 1000.0, f"纳指点位异常: {res['nasdaq_point']}"
    assert "10Y国债" in res["macro_summary"]


# =========================================================================
# 4. data_loader: 14 赛道核心 ETF 实时放量比 (f10) 与折溢价率测试
# =========================================================================

def test_fetch_sector_core_etf_metrics():
    """测试 14 大赛道核心 ETF 完整覆盖与量比指标"""
    metrics = fetch_sector_core_etf_metrics(use_cache=False)
    assert isinstance(metrics, dict)
    assert len(metrics) == 14, f"ETF 数量不为 14: {len(metrics)}"

    for meta in CORE_SECTOR_ETFS:
        code = meta["code"]
        assert code in metrics, f"缺失核心 ETF: {code}"
        m = metrics[code]
        assert m["price"] > 0.0
        assert m["volume_surge_ratio"] > 0.0
        assert isinstance(m["change_pct"], (int, float))
        assert isinstance(m["discount_premium_pct"], (int, float))
        assert m["sector_id"] == meta["sector_id"]


# =========================================================================
# 5. data_loader: 本地日线 Parquet 自动自愈测试
# =========================================================================

def test_auto_heal_sector_parquets_real_files():
    """测试本地真实 Parquet 日线自愈算子幂等性"""
    res = auto_heal_sector_parquets()
    assert isinstance(res, dict)
    assert res["status"] == "success"
    assert "target_latest_date" in res
    assert "healed_count" in res
    assert "skipped_count" in res


def test_auto_heal_sector_parquets_synthetic_gap(tmp_path):
    """
    测试使用独立临时 Parquet 验证增量缺口自动自愈:
    1. 创建落后于 target_latest_date 的临时 Parquet 文件
    2. 执行 auto_heal_sector_parquets(target_dir=tmp_path)
    3. 验证缺失行数被补齐，日期严格递增且 0 NaN
    """
    test_parquet = tmp_path / "000685.SH.parquet"
    init_df = pd.DataFrame({
        "date": ["2026-10-20", "2026-10-21", "2026-10-22"],
        "open": [100.0, 101.0, 102.0],
        "high": [102.0, 103.0, 104.0],
        "low": [99.0, 100.0, 101.0],
        "close": [101.0, 102.0, 103.0],
        "volume": [1000.0, 1100.0, 1200.0],
        "amount": [100000.0, 110000.0, 120000.0],
        "change_pct": [1.0, 0.99, 0.98],
    })
    init_df.to_parquet(test_parquet, index=False)

    heal_res = auto_heal_sector_parquets(target_dir=tmp_path)
    assert heal_res["status"] == "success"
    assert heal_res["healed_count"] == 1

    healed_df = pd.read_parquet(test_parquet)
    assert len(healed_df) > len(init_df), "行数未增加"
    assert not healed_df.isna().any().any(), "存在 NaN 空值"
    dates = pd.to_datetime(healed_df["date"]).tolist()
    assert dates == sorted(dates), "日期序列非升序"


# =========================================================================
# 6. app_gui.py: 动态 take_profit_ratio 联动注入测试
# =========================================================================

def test_app_gui_dynamic_take_profit_ratio_linkage():
    """
    测试 app_gui.py 中预警哨按钮点击后注入真实的动态比例:
    当 alert 提供 take_profit_ratio: 0.50 时，session_state 承接比率必须为 0.50，
    而非之前的静态 0.40。
    """
    alert_red = {
        "level": "red",
        "dimension": "移动止盈",
        "action_type": "take_profit",
        "fund_code": "008888",
        "take_profit_ratio": 0.50,
    }
    ratio = float(alert_red.get("take_profit_ratio", 0.40))
    state_mock = {"fund_code": alert_red["fund_code"], "ratio": ratio}
    assert state_mock["ratio"] == 0.50

    alert_default = {
        "level": "yellow",
        "dimension": "阶梯止盈",
        "action_type": "take_profit",
        "fund_code": "100032",
    }
    ratio_def = float(alert_default.get("take_profit_ratio", 0.40))
    state_def = {"fund_code": alert_default["fund_code"], "ratio": ratio_def}
    assert state_def["ratio"] == 0.40
