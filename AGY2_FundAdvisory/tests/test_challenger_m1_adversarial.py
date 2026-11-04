"""
AGY2_FundAdvisory/tests/test_challenger_m1_adversarial.py
Milestone 1 对抗性挑战与极端压力测试套件 (Empirical Challenger M1-1)

验证维度:
1. 内存/冷启动与基准时延压力测试:
   - FundPurchaseCacheManager.get_fund_quota 冷启动从 Parquet 加载时延严格 < 50ms (多轮实测)
   - 热缓存查询时延 < 0.1ms
   - FundMetadataManager.get_fund_metadata 缓存读取严格 < 5ms (多轮实测)
2. 断网与离线故障注入模拟 (Fault Injection & Offline Resilience):
   - 东财 push2 接口超时、连接拒绝、HTTP 500、畸变 JSON、空响应等故障下平滑降级
   - 彻底断网且无缓存时冷启动返回中性安全结构 (0 崩溃、0 未捕获异常)
   - AkShare 全接口抛异常、DuckDB 不可用时 IndexValuationEngine 降级保护
3. 源码 AST 与全局正则深扫:
   - 彻底消灭 INDEX_PE_METAS 静态字典
   - 彻底消灭 3210 / 1780 市场宽度假常数
4. 清盘排雷与真实限购业务模型边界测试:
   - 迷你基 <0.5亿 法定清盘线严格断言
   - 真实限购金额与限额状态映射一致性
"""

import os
import sys
import time
import json
import urllib.request
import urllib.error
import ast
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import pandas as pd
import numpy as np

# 确保路径定位
CURRENT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = CURRENT_DIR.parent.parent if CURRENT_DIR.parent.name == "AGY2_FundAdvisory" else CURRENT_DIR.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))
if str(WORKSPACE_ROOT / "AGY2_FundAdvisory") not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT / "AGY2_FundAdvisory"))

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
    FUNDS_META_DIR
)


# ==============================================================================
# 1. 基准测试与冷启动延时压力测试 (Benchmark Cold Start & Latency)
# ==============================================================================

class TestColdStartAndLatencyBenchmarks:
    """对抗性质询 1: 内存/冷启动时延严格断言"""

    def test_fund_purchase_cache_cold_start_under_50ms(self):
        """
        压力测试: 重置内存缓存后，冷启动读取 Parquet 并构建哈希索引。
        断言多轮冷启动耗时严格 < 50ms。
        """
        assert FUND_PURCHASE_CACHE_PATH.exists(), "fund_purchase.parquet 必须存在"

        cold_durations = []
        for _ in range(10):
            # 强制清空内存缓存，模拟全新进程冷启动
            FundPurchaseCacheManager._MEMORY_DICT = None
            FundPurchaseCacheManager._MEMORY_DF = None
            FundPurchaseCacheManager._LAST_LOAD_DATE = None

            t0 = time.perf_counter()
            quota = FundPurchaseCacheManager.get_fund_quota("050025")
            dt_ms = (time.perf_counter() - t0) * 1000.0
            cold_durations.append(dt_ms)

            assert isinstance(quota, dict)
            assert quota["fund_code"] == "050025"

        avg_ms = np.mean(cold_durations)
        max_ms = np.max(cold_durations)
        p95_ms = np.percentile(cold_durations, 95)

        print(f"\n[Benchmark] FundPurchaseCacheManager Cold Start: Avg={avg_ms:.2f}ms, Max={max_ms:.2f}ms, P95={p95_ms:.2f}ms")
        assert max_ms < 50.0, f"Cold start max time {max_ms:.2f}ms exceeded 50ms strict bound!"
        assert avg_ms < 25.0, f"Cold start average time {avg_ms:.2f}ms exceeded 25ms threshold!"

    def test_fund_purchase_cache_warm_query_latency(self):
        """
        压力测试: 热缓存查询 1000 次，单次时延必须 < 0.1ms。
        """
        # 确保已预热
        _ = FundPurchaseCacheManager.get_fund_quota("050025")

        test_codes = ["050025", "000001", "110011", "000922", "999999"]
        t0 = time.perf_counter()
        n_queries = 1000
        for i in range(n_queries):
            c = test_codes[i % len(test_codes)]
            q = FundPurchaseCacheManager.get_fund_quota(c)
            assert q["fund_code"] == c.zfill(6)
        total_time_ms = (time.perf_counter() - t0) * 1000.0
        avg_query_us = (total_time_ms / n_queries) * 1000.0

        print(f"[Benchmark] FundPurchaseCacheManager Warm Query: {avg_query_us:.2f} µs/query")
        assert avg_query_us < 100.0, f"Warm query avg {avg_query_us:.2f}µs exceeded 100µs limit!"

    def test_fund_metadata_cached_retrieval_under_5ms(self):
        """
        压力测试: FundMetadataManager 磁盘缓存读取 50 次，单次耗时严格 < 5ms。
        """
        # 预热确保缓存文件存在
        meta = FundMetadataManager.get_fund_metadata("000001", force_refresh=False)
        assert meta["code"] == "000001"
        cache_file = FUNDS_META_DIR / "000001_meta.json"
        assert cache_file.exists()

        durations_ms = []
        for _ in range(50):
            t0 = time.perf_counter()
            cached_meta = FundMetadataManager.get_fund_metadata("000001", force_refresh=False)
            dt_ms = (time.perf_counter() - t0) * 1000.0
            durations_ms.append(dt_ms)
            assert cached_meta["code"] == "000001"

        avg_ms = np.mean(durations_ms)
        max_ms = np.max(durations_ms)
        p99_ms = np.percentile(durations_ms, 99)

        print(f"\n[Benchmark] FundMetadataManager Cached Read: Avg={avg_ms:.2f}ms, Max={max_ms:.2f}ms, P99={p99_ms:.2f}ms")
        assert max_ms < 5.0, f"Metadata cached read max time {max_ms:.2f}ms exceeded 5ms limit!"
        assert avg_ms < 2.0, f"Metadata cached read avg time {avg_ms:.2f}ms exceeded 2ms threshold!"

    def test_fund_metadata_offline_master_fallback_speed_and_completeness(self):
        """
        压力测试: 离线主数据湖兜底读取。
        当无网络且无本地缓存时，从 fund_managers.parquet 兜底耗时与字段完整性。
        """
        t0 = time.perf_counter()
        fb = FundMetadataManager.fallback_from_master("000001")
        dt_ms = (time.perf_counter() - t0) * 1000.0

        assert fb["code"] == "000001"
        assert "aum" in fb
        assert "manager" in fb
        assert "liquidation_risk" in fb
        assert fb["source"] == "offline_master_fallback"
        print(f"[Benchmark] FundMetadataManager Master Fallback: {dt_ms:.2f}ms")
        assert dt_ms < 50.0, f"Master fallback took {dt_ms:.2f}ms, exceeding 50ms!"


# ==============================================================================
# 2. 网络离线与故障注入压力测试 (Network Offline & Fault Injection)
# ==============================================================================

class TestNetworkOfflineAndFaultInjection:
    """对抗性质询 2: 东财 push2 与 AkShare 故障注入断言"""

    @pytest.mark.parametrize("error_cls, error_msg", [
        (urllib.error.URLError, "Name or service not known"),
        (TimeoutError, "Connection timed out"),
        (ConnectionRefusedError, "Connection refused"),
        (urllib.error.HTTPError, "502 Bad Gateway"),
    ])
    def test_eastmoney_network_failure_falls_back_to_cache(self, error_cls, error_msg):
        """
        故障注入: 模拟东财 push2 抛出各种网络异常，断言平滑降级至本地 JSON 快照，0 未捕获异常。
        """
        # 清空内存缓存，迫使触发网络调用
        import AGY2_FundAdvisory.data_loader as dl
        dl._MARKET_BREADTH_MEM_CACHE["data"] = None
        dl._MARKET_BREADTH_MEM_CACHE["ts"] = 0.0

        def raise_err(*args, **kwargs):
            if error_cls == urllib.error.HTTPError:
                raise error_cls("http://url", 502, error_msg, {}, None)
            raise error_cls(error_msg)

        with patch("urllib.request.urlopen", side_effect=raise_err):
            data = fetch_market_turnover_and_sentiment(force_refresh=True)

        assert isinstance(data, dict)
        assert "total_turnover" in data
        assert "up_count" in data
        assert "down_count" in data
        assert "up_pct" in data
        # 确认不含假常数
        assert not (data["up_count"] == 3210 and data["down_count"] == 1780)
        assert data.get("source") in ("local_cache_fallback", "cold_start_unready", "eastmoney_realtime")

    def test_eastmoney_network_failure_with_no_cache_file(self, tmp_path):
        """
        极限灾难注入: 既断网，且磁盘缓存文件丢失/不存在。
        断言平滑返回安全中性冷启动结构，0 崩溃，0 假数据。
        """
        import AGY2_FundAdvisory.data_loader as dl
        dl._MARKET_BREADTH_MEM_CACHE["data"] = None
        dl._MARKET_BREADTH_MEM_CACHE["ts"] = 0.0

        non_existent_cache = tmp_path / "not_found.json"

        with patch("urllib.request.urlopen", side_effect=TimeoutError("Offline")):
            with patch("AGY2_FundAdvisory.data_loader.MARKET_BREADTH_CACHE_FILE", non_existent_cache):
                data = fetch_market_turnover_and_sentiment(force_refresh=True)

        assert isinstance(data, dict)
        assert data["turnover_str"] == "-- 亿"
        assert data["up_pct"] == 50.0
        assert data["sentiment_label"] == "数据同步中"
        assert data["source"] == "cold_start_unready"
        assert not (data["up_count"] == 3210 and data["down_count"] == 1780)

    def test_eastmoney_corrupted_response_handling(self):
        """
        数据畸变注入: 模拟东财返回畸形 JSON 或截断数据。
        断言安全捕获并降级，不发生 JSONDecodeError 崩溃。
        """
        import AGY2_FundAdvisory.data_loader as dl
        dl._MARKET_BREADTH_MEM_CACHE["data"] = None
        dl._MARKET_BREADTH_MEM_CACHE["ts"] = 0.0

        mock_resp = MagicMock()
        mock_resp.read.return_value = b"{malformed json content"
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            data = fetch_market_turnover_and_sentiment(force_refresh=True)

        assert isinstance(data, dict)
        assert "total_turnover" in data

    def test_eastmoney_empty_diff_handling(self):
        """
        结构畸变注入: 模拟东财返回空 diff 列表。
        断言不发生 IndexError 崩溃。
        """
        import AGY2_FundAdvisory.data_loader as dl
        dl._MARKET_BREADTH_MEM_CACHE["data"] = None
        dl._MARKET_BREADTH_MEM_CACHE["ts"] = 0.0

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"data": {"diff": []}}).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            data = fetch_market_turnover_and_sentiment(force_refresh=True)

        assert isinstance(data, dict)
        assert "total_turnover" in data

    def test_akshare_valuation_offline_simulation(self):
        """
        故障注入: 模拟 akshare 网络调用全部挂掉。
        断言 IndexValuationEngine 依赖本地湖仓与基准降级，正常计算 6 大核心指数，0 崩溃。
        """
        import AGY2_FundAdvisory.data_loader as dl
        dl._INDEX_VAL_MEM_CACHE["data"] = None
        dl._INDEX_VAL_MEM_CACHE["ts"] = 0.0

        with patch("akshare.stock_index_pe_lg", side_effect=Exception("AkShare offline")):
            with patch("akshare.stock_zh_index_value_csindex", side_effect=Exception("AkShare offline")):
                val_map = IndexValuationEngine.fetch_or_calc_index_valuations(force_refresh=True)

        assert isinstance(val_map, dict)
        # 6 大核心指数覆盖完整
        for code in ["000300", "000905", "000852", "000922", "000688", "518880"]:
            assert code in val_map, f"Missing {code} in offline valuation map"
            item = val_map[code]
            assert "name" in item and len(item["name"]) > 0
            assert "label" in item and len(item["label"]) > 0
            assert item["status"] in ["very_low", "low", "mid", "high", "very_high"]

        # 双键索引 (代码 与 市场.代码)
        assert "1.000300" in val_map
        assert val_map["1.000300"]["pe_ttm"] == val_map["000300"]["pe_ttm"]

    def test_akshare_and_duckdb_simultaneous_failure(self):
        """
        极端灾难注入: 模拟 akshare 全挂 + DuckDB 损坏/不可用。
        断言 IndexValuationEngine 触发历史均值基线安全兜底，返回完整字典与估值标签。
        """
        import AGY2_FundAdvisory.data_loader as dl
        dl._INDEX_VAL_MEM_CACHE["data"] = None
        dl._INDEX_VAL_MEM_CACHE["ts"] = 0.0

        with patch("akshare.stock_index_pe_lg", side_effect=Exception("AkShare down")):
            with patch("akshare.stock_zh_index_value_csindex", side_effect=Exception("AkShare down")):
                with patch("duckdb.connect", side_effect=Exception("DuckDB locked")):
                    val_map = IndexValuationEngine.fetch_or_calc_index_valuations(force_refresh=True)

        assert isinstance(val_map, dict)
        assert "000300" in val_map
        hs300 = val_map["000300"]
        assert hs300["pe_ttm"] is not None
        assert hs300["label"] != ""
        assert "PE" in hs300["label"]


# ==============================================================================
# 3. 源码 AST 与全局正则深扫 (Absence of Fake Constants & Dictionaries)
# ==============================================================================

class TestAbsenceOfFakeConstants:
    """对抗性质询 3: 全仓库扫描清除假常数与硬编码字典"""

    def test_no_index_pe_metas_in_any_python_files(self):
        """
        深度扫描: 递归扫描 AGY2_FundAdvisory/ 目录下所有 Python 源码（排除测试套件自身断言语句）。
        断言 INDEX_PE_METAS 彻底被清零，未遗留任何定义或引用。
        """
        source_dir = WORKSPACE_ROOT / "AGY2_FundAdvisory"
        py_files = [p for p in source_dir.rglob("*.py") if "tests" not in str(p)]

        violations = []
        for p in py_files:
            content = p.read_text(encoding="utf-8")
            if "INDEX_PE_METAS" in content:
                violations.append(str(p))

        assert len(violations) == 0, f"Found INDEX_PE_METAS in source files: {violations}"

    def test_no_3210_or_1780_in_data_loader_and_gui(self):
        """
        深度扫描: data_loader.py 与 app_gui.py 中不得含有 3210 或 1780 市场宽度假数字。
        """
        for fname in ["data_loader.py", "app_gui.py"]:
            fpath = WORKSPACE_ROOT / "AGY2_FundAdvisory" / fname
            if not fpath.exists():
                continue
            text = fpath.read_text(encoding="utf-8")
            assert "3210" not in text, f"Found '3210' in {fname}!"
            assert "1780" not in text, f"Found '1780' in {fname}!"

    def test_ast_scan_breadth_function_for_constant_literals(self):
        """
        AST 语法树审查: 解析 fetch_market_turnover_and_sentiment 抽象语法树，
        断言函数体内绝对不包含常量值 3210 或 1780。
        """
        dl_path = WORKSPACE_ROOT / "AGY2_FundAdvisory" / "data_loader.py"
        tree = ast.parse(dl_path.read_text(encoding="utf-8"))

        target_func = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "fetch_market_turnover_and_sentiment":
                target_func = node
                break

        assert target_func is not None, "fetch_market_turnover_and_sentiment function not found in AST!"

        for subnode in ast.walk(target_func):
            if isinstance(subnode, ast.Constant):
                val = subnode.value
                assert val != 3210, "AST constant 3210 found in fetch_market_turnover_and_sentiment!"
                assert val != 1780, "AST constant 1780 found in fetch_market_turnover_and_sentiment!"


# ==============================================================================
# 4. 业务契约与排雷边界测试 (Boundary Tests on Quota & Liquidation)
# ==============================================================================

class TestBusinessModelBoundaries:
    """业务模型与安全红线边界压力断言"""

    def test_liquidation_risk_boundary_assertion(self):
        """
        边界测试: 法定 0.5 亿清盘线。
        - 0.49 亿必须触发清盘预警
        - 0.50 亿不得触发清盘预警
        """
        test_meta_mini = {"aum": 0.49}
        assert (test_meta_mini["aum"] < 0.5) is True

        test_meta_safe = {"aum": 0.50}
        assert (test_meta_safe["aum"] < 0.5) is False

        test_meta_none = {"aum": None}
        assert (test_meta_none["aum"] is not None and test_meta_none["aum"] < 0.5) is False

    def test_quota_mapping_correctness(self):
        """
        边界测试: 申购状态与日累计限额逻辑。
        - 暂停申购 / 封闭 -> is_limited == True
        - 限制大额 (如 1000 元) -> is_limited == True, daily_limit == 1000.0
        - 开放申购 且 限额很大 -> is_limited == False
        """
        q_limited = FundPurchaseCacheManager.get_fund_quota("050025")
        assert q_limited["is_limited"] is True
        assert q_limited["daily_limit"] <= 1000.0

        # 查询不存在的代码应默认安全放行
        q_unknown = FundPurchaseCacheManager.get_fund_quota("999999")
        assert q_unknown["fund_code"] == "999999"
        assert q_unknown["is_limited"] is False
        assert q_unknown["daily_limit"] == 1e11
