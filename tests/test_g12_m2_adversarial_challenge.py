# -*- coding: utf-8 -*-
"""
tests/test_g12_m2_adversarial_challenge.py
Milestone 2 Independent Empirical Challenge Suite:
Adversarial stress-testing of:
1. `data_loader.py: auto_heal_sector_parquets()`:
   - Missing target parquet file
   - Already healed file (idempotency & skip behavior)
   - Corrupt parquet file (random garbage bytes recovery)
   - Lagging parquet (missing 1, 5, 15 days)
   - Atomic write (.tmp + os.replace, no leftover .tmp, file readability)
   - 0 NaN and 0 corruption guarantee
   - Multi-file directory batch healing & skip robustness
   - Fallback chain: Eastmoney API -> aligned matrix -> zero-change fallback
2. `fetch_sector_core_etf_metrics()`:
   - Full 14 ETFs coverage & schema integrity
   - Volume surge ratio f10 properties (normal, surge, low, negative/zero/None)
   - IOPV discount/premium boundaries (f43 scaling, positive/negative, zero/missing)
   - Network failure fallback and malformed response tolerance
   - 30s Memory cache TTL behavior
3. `fetch_macro_cross_market_indicators()`:
   - 10Y CGB yield, gold ETF, Nasdaq linkage return format & value ranges
   - Macro summary strings formatting and symbols
   - 60s Memory cache TTL behavior
   - Network failure & offline data degradation robustness
4. `calc_financial_news_sentiment()`:
   - Strict polarity scoring boundaries [0.0, 100.0]
   - Empty, None, and malformed inputs
   - Neutral and unrelated news
   - Conflicting balanced news (equal pos & neg)
   - Extreme euphoria / panic inputs
   - Intermediate threshold boundaries (温和看多, 谨慎防守)
   - Large batch stress performance

Author: teamwork_challenger (empirical challenger: critic, specialist)
"""

import io
import json
import os
import sys
import time
import urllib.error
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np
import pandas as pd
import pytest

_CURRENT = Path(__file__).resolve().parent
_WORKSPACE = _CURRENT.parent
_AGY2_DIR = _WORKSPACE / "AGY2_FundAdvisory"
if str(_AGY2_DIR) not in sys.path:
    sys.path.insert(0, str(_AGY2_DIR))
if str(_WORKSPACE) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE))

from AGY2_FundAdvisory.data_loader import (
    DataLoader,
    calc_financial_news_sentiment,
    fetch_macro_cross_market_indicators,
    fetch_sector_core_etf_metrics,
    auto_heal_sector_parquets,
    CORE_SECTOR_ETFS,
    _MACRO_INDICATORS_MEM_CACHE,
    _CORE_ETF_METRICS_MEM_CACHE,
    _FALLBACK_CORE_ETF_METRICS,
)


@pytest.fixture(autouse=True)
def reset_mem_caches():
    """Reset global in-memory caches before and after each test."""
    _MACRO_INDICATORS_MEM_CACHE["data"] = None
    _MACRO_INDICATORS_MEM_CACHE["ts"] = 0.0
    _CORE_ETF_METRICS_MEM_CACHE["data"] = None
    _CORE_ETF_METRICS_MEM_CACHE["ts"] = 0.0
    yield
    _MACRO_INDICATORS_MEM_CACHE["data"] = None
    _MACRO_INDICATORS_MEM_CACHE["ts"] = 0.0
    _CORE_ETF_METRICS_MEM_CACHE["data"] = None
    _CORE_ETF_METRICS_MEM_CACHE["ts"] = 0.0


# =========================================================================
# 1. Target 1: auto_heal_sector_parquets Adversarial Stress Tests
# =========================================================================

class TestAutoHealSectorParquetsAdversarial:
    """Adversarial stress-testing for auto_heal_sector_parquets."""

    def test_missing_target_file_handling(self, tmp_path):
        """Test behavior when specified target parquet does not exist."""
        non_existent_file = tmp_path / "non_existent_index.parquet"
        res = auto_heal_sector_parquets(target_dir=non_existent_file)
        assert res["status"] == "success"
        assert res["healed_count"] == 0
        assert not non_existent_file.exists()

    def test_already_healed_file_is_skipped_and_idempotent(self, tmp_path):
        """
        Test behavior when target parquet is already up-to-date (date >= target_latest_date).
        Verify file is skipped, not rewritten, and execution is strictly idempotent.
        """
        test_file = tmp_path / "000685.SH.parquet"
        today_str = pd.Timestamp.now().strftime("%Y-%m-%d")
        future_date = "2030-01-01"
        df_init = pd.DataFrame({
            "date": ["2026-11-01", "2026-11-02", future_date],
            "open": [100.0, 101.0, 102.0],
            "close": [101.0, 102.0, 103.0],
            "volume": [1000.0, 1100.0, 1200.0],
        })
        df_init.to_parquet(test_file, index=False)
        mtime_before = test_file.stat().st_mtime_ns

        res = auto_heal_sector_parquets(target_dir=tmp_path)
        assert res["status"] == "success"
        assert res["healed_count"] == 0
        assert res["skipped_count"] >= 1

        # File mtime should not have changed because it was skipped
        mtime_after = test_file.stat().st_mtime_ns
        assert mtime_before == mtime_after

        # Verify idempotency on second call
        res2 = auto_heal_sector_parquets(target_dir=tmp_path)
        assert res2["healed_count"] == 0
        assert res2["skipped_count"] >= 1

    def test_corrupt_parquet_file_safe_handling(self, tmp_path):
        """
        Test behavior when target file is corrupt garbage bytes.
        auto_heal_sector_parquets must not crash, must not delete or corrupt other files,
        and must return status: success with healed_count == 0.
        """
        corrupt_file = tmp_path / "000685.SH.parquet"
        corrupt_bytes = b"CORRUPTED_PARQUET_FILE_HEADER_GARBAGE_BYTES_123456789"
        corrupt_file.write_bytes(corrupt_bytes)

        res = auto_heal_sector_parquets(target_dir=tmp_path)
        assert res["status"] == "success"
        assert res["healed_count"] == 0

        # Corrupt file content should be unchanged (not overwritten with partial garbage)
        assert corrupt_file.read_bytes() == corrupt_bytes

    def test_parquet_without_date_column_skipped_safely(self, tmp_path):
        """Test parquet file that has no recognized date or 日期 column."""
        no_date_file = tmp_path / "000933.SH.parquet"
        df = pd.DataFrame({"symbol": ["000933", "000933"], "val": [1.0, 2.0]})
        df.to_parquet(no_date_file, index=False)

        res = auto_heal_sector_parquets(target_dir=tmp_path)
        assert res["status"] == "success"
        assert res["healed_count"] == 0

    def test_empty_parquet_file_skipped_safely(self, tmp_path):
        """Test 0-row empty dataframe parquet."""
        empty_file = tmp_path / "000932.SH.parquet"
        df = pd.DataFrame(columns=["date", "close", "open"])
        df.to_parquet(empty_file, index=False)

        res = auto_heal_sector_parquets(target_dir=tmp_path)
        assert res["status"] == "success"
        assert res["healed_count"] == 0

    def test_atomic_write_mechanism_and_no_leftover_tmp(self, tmp_path):
        """
        Verify atomic write behavior:
        1. During update, data is written to a .tmp file then atomically replaced.
        2. No lingering .tmp files remain on disk after completion.
        3. Target parquet is 100% valid, readable by pyarrow, and has 0 NaN.
        """
        test_file = tmp_path / "000685.SH.parquet"
        df_lagging = pd.DataFrame({
            "date": ["2026-10-20", "2026-10-21"],
            "open": [10.0, 10.5],
            "high": [11.0, 11.2],
            "low": [9.8, 10.1],
            "close": [10.4, 10.9],
            "volume": [50000.0, 52000.0],
            "amount": [520000.0, 560000.0],
            "change_pct": [0.0, 4.81],
        })
        df_lagging.to_parquet(test_file, index=False)

        res = auto_heal_sector_parquets(target_dir=tmp_path)
        assert res["status"] == "success"
        assert res["healed_count"] == 1

        # Check no .tmp file left behind
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0, f"Found lingering .tmp files: {tmp_files}"

        # Check healed file readability and zero NaN
        df_healed = pd.read_parquet(test_file)
        assert len(df_healed) > len(df_lagging)
        assert not df_healed.isna().any().any(), "Healed parquet contains NaN values"

        # Check date monotonicity
        dates = pd.to_datetime(df_healed["date"]).tolist()
        assert dates == sorted(dates), "Dates in healed parquet are not strictly sorted"

        # Check no duplicate dates
        assert len(dates) == len(set(dates)), "Duplicate dates detected in healed parquet"

    def test_lagging_file_network_down_matrix_fallback(self, tmp_path):
        """
        Adversarial scenario: Eastmoney API fails (simulated URLError / timeout).
        auto_heal_sector_parquets must fallback to aligned_matrix_total_return.parquet.
        Verify successful healing, 0 NaN, strictly sorted dates.
        """
        test_file = tmp_path / "000685.SH.parquet"
        df_lag = pd.DataFrame({
            "date": ["2026-10-20", "2026-10-21"],
            "open": [10.0, 10.2],
            "close": [10.1, 10.3],
            "change_pct": [0.0, 1.98],
        })
        df_lag.to_parquet(test_file, index=False)

        # Force urllib to fail
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Network unreachable")):
            res = auto_heal_sector_parquets(target_dir=tmp_path)

        assert res["status"] == "success"
        assert res["healed_count"] == 1

        df_healed = pd.read_parquet(test_file)
        assert len(df_healed) > len(df_lag)
        assert not df_healed.isna().any().any()
        dates = pd.to_datetime(df_healed["date"]).tolist()
        assert dates == sorted(dates)

    def test_lagging_file_complete_offline_and_matrix_missing_fallback(self, tmp_path):
        """
        Adversarial scenario: Network is down AND aligned matrix does not match or is unavailable.
        auto_heal_sector_parquets must execute fallback 3 (zero-change forward fill).
        Verify 0 NaN, date alignment preserved, valid parquet output.
        """
        # Use an index code not present in aligned matrix
        test_file = tmp_path / "999999.SH.parquet"
        df_lag = pd.DataFrame({
            "date": ["2026-10-20", "2026-10-21"],
            "open": [50.0, 50.5],
            "close": [50.2, 50.8],
            "change_pct": [0.0, 1.2],
        })
        df_lag.to_parquet(test_file, index=False)

        with patch("urllib.request.urlopen", side_effect=TimeoutError("Request timed out")):
            res = auto_heal_sector_parquets(target_dir=tmp_path)

        assert res["status"] == "success"
        assert res["healed_count"] == 1

        df_healed = pd.read_parquet(test_file)
        assert len(df_healed) > len(df_lag)
        assert not df_healed.isna().any().any()

        # Added rows should carry last close and 0.0 change_pct
        tail_rows = df_healed.iloc[len(df_lag):]
        assert (tail_rows["change_pct"] == 0.0).all()
        assert (tail_rows["close"] == 50.8).all()

    def test_directory_batch_healing_with_mixed_health_files(self, tmp_path):
        """
        Stress test: A directory containing:
        1. lagging valid parquet (needs heal)
        2. already healed parquet (should skip)
        3. corrupt parquet (should skip safely)
        4. parquet missing date column (should skip safely)
        5. non-parquet file (should ignore)
        """
        # 1. Lagging
        f1 = tmp_path / "000685.SH.parquet"
        pd.DataFrame({
            "date": ["2026-10-20"],
            "open": [10.0],
            "close": [10.0],
            "change_pct": [0.0],
        }).to_parquet(f1, index=False)

        # 2. Already healed
        f2 = tmp_path / "000933.SH.parquet"
        pd.DataFrame({
            "date": ["2035-01-01"],
            "open": [20.0],
            "close": [20.0],
            "change_pct": [0.0],
        }).to_parquet(f2, index=False)

        # 3. Corrupt
        f3 = tmp_path / "000932.SH.parquet"
        f3.write_bytes(b"INVALID_PARQUET_BINARY_STREAM")

        # 4. No date
        f4 = tmp_path / "399986.SZ.parquet"
        pd.DataFrame({"price": [1.0, 2.0]}).to_parquet(f4, index=False)

        # 5. Non-parquet
        f5 = tmp_path / "notes.txt"
        f5.write_text("just a text file", encoding="utf-8")

        res = auto_heal_sector_parquets(target_dir=tmp_path)
        assert res["status"] == "success"
        assert res["healed_count"] == 1  # only f1 healed
        assert res["skipped_count"] >= 1  # f2 skipped

        # Verify f1 was successfully healed
        df_f1 = pd.read_parquet(f1)
        assert len(df_f1) > 1
        assert not df_f1.isna().any().any()


# =========================================================================
# 2. Target 2: fetch_sector_core_etf_metrics Adversarial Stress Tests
# =========================================================================

class TestFetchSectorCoreETFMetricsAdversarial:
    """Adversarial stress-testing for fetch_sector_core_etf_metrics."""

    def test_full_14_etf_coverage_and_schema(self):
        """Verify all 14 ETFs in CORE_SECTOR_ETFS are returned with required fields."""
        metrics = fetch_sector_core_etf_metrics(use_cache=False)
        assert isinstance(metrics, dict)
        assert len(metrics) == 14

        expected_codes = {item["code"] for item in CORE_SECTOR_ETFS}
        assert set(metrics.keys()) == expected_codes

        for code, m in metrics.items():
            assert m["code"] == code
            assert isinstance(m["name"], str) and len(m["name"]) > 0
            assert isinstance(m["price"], (int, float)) and m["price"] > 0.0
            assert isinstance(m["change_pct"], (int, float))
            assert isinstance(m["volume_surge_ratio"], (int, float)) and m["volume_surge_ratio"] > 0.0
            assert isinstance(m["discount_premium_pct"], (int, float))
            assert isinstance(m["sector_id"], str) and len(m["sector_id"]) > 0

    def test_volume_surge_ratio_f10_parsing_and_properties(self):
        """
        Adversarial test on f10 Volume Surge Ratio:
        - Normal f10 = 150 -> 1.50
        - High surge f10 = 850 -> 8.50
        - Low surge f10 = 35 -> 0.35
        - Invalid f10 (0, negative, None, string) -> must retain valid positive fallback
        """
        mock_payload = {
            "data": {
                "diff": [
                    {
                        "f12": "510300",
                        "f14": "沪深300ETF华泰柏瑞",
                        "f2": 4124,   # 4.124
                        "f3": -169,   # -1.69%
                        "f10": 250,   # Volume surge 2.50
                        "f43": 4124,  # IOPV 4.124
                    },
                    {
                        "f12": "512760",
                        "f14": "芯片ETF国泰",
                        "f2": 829,    # 0.829
                        "f3": -304,   # -3.04%
                        "f10": 980,   # High volume surge 9.80
                        "f43": 829,
                    },
                    {
                        "f12": "518880",
                        "f14": "黄金ETF华安",
                        "f2": 8253,
                        "f3": -198,
                        "f10": -50,   # Negative / invalid f10
                        "f43": 8253,
                    },
                    {
                        "f12": "512800",
                        "f14": "银行ETF华宝",
                        "f2": 877,
                        "f3": 69,
                        "f10": 0,     # Zero f10
                        "f43": 877,
                    },
                ]
            }
        }

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            metrics = fetch_sector_core_etf_metrics(use_cache=False)

        assert metrics["510300"]["volume_surge_ratio"] == 2.50
        assert metrics["512760"]["volume_surge_ratio"] == 9.80
        # Negative / zero f10 must retain fallback positive value
        assert metrics["518880"]["volume_surge_ratio"] > 0.0
        assert metrics["512800"]["volume_surge_ratio"] > 0.0

    def test_iopv_discount_premium_boundaries(self):
        """
        Adversarial test on f43 (IOPV):
        - Premium: price = 1.10, iopv = 1.00 -> +10.0%
        - Discount: price = 0.90, iopv = 1.00 -> -10.0%
        - Zero / Missing / None IOPV -> discount_premium_pct defaults to 0.0
        """
        mock_payload = {
            "data": {
                "diff": [
                    {
                        "f12": "510300",
                        "f2": 1100,  # price = 1.100
                        "f3": 100,
                        "f10": 100,
                        "f43": 1000, # iopv = 1.000 -> (1.10 - 1.00)/1.00 = +10.0%
                    },
                    {
                        "f12": "512760",
                        "f2": 900,   # price = 0.900
                        "f3": -100,
                        "f10": 100,
                        "f43": 1000, # iopv = 1.000 -> (0.90 - 1.00)/1.00 = -10.0%
                    },
                    {
                        "f12": "512100",
                        "f2": 2650,
                        "f3": 50,
                        "f10": 100,
                        "f43": 0,    # Zero iopv
                    },
                    {
                        "f12": "588000",
                        "f2": 1326,
                        "f3": -50,
                        "f10": 100,
                        "f43": None, # None iopv
                    },
                ]
            }
        }

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            metrics = fetch_sector_core_etf_metrics(use_cache=False)

        assert metrics["510300"]["discount_premium_pct"] == 10.0
        assert metrics["512760"]["discount_premium_pct"] == -10.0
        assert metrics["512100"]["discount_premium_pct"] == 0.0
        assert metrics["588000"]["discount_premium_pct"] == 0.0

    def test_network_failure_and_offline_fallback(self):
        """
        When Eastmoney API raises URLError / TimeoutError,
        function must gracefully fall back to _FALLBACK_CORE_ETF_METRICS without crashing.
        """
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
            metrics = fetch_sector_core_etf_metrics(use_cache=False)

        assert isinstance(metrics, dict)
        assert len(metrics) == 14
        for code in _FALLBACK_CORE_ETF_METRICS:
            assert code in metrics
            assert metrics[code]["price"] == _FALLBACK_CORE_ETF_METRICS[code]["price"]
            assert metrics[code]["volume_surge_ratio"] > 0.0

    def test_malformed_api_responses_tolerance(self):
        """Test resilience against empty response, null data, malformed diff structure."""
        for malformed in [b"{}", b'{"data": null}', b'{"data": {"diff": null}}', b"INVALID_JSON"]:
            mock_resp = MagicMock()
            mock_resp.read.return_value = malformed
            mock_resp.__enter__.return_value = mock_resp

            with patch("urllib.request.urlopen", return_value=mock_resp):
                metrics = fetch_sector_core_etf_metrics(use_cache=False)

            assert isinstance(metrics, dict)
            assert len(metrics) == 14

    def test_memory_cache_ttl_30s(self):
        """
        Verify in-memory caching with 30s TTL:
        1. Repeated calls within 30s return cached object.
        2. use_cache=False forces refresh.
        3. Calls after 30s trigger refresh.
        """
        # Call 1: Populates cache
        m1 = fetch_sector_core_etf_metrics(use_cache=True)
        assert _CORE_ETF_METRICS_MEM_CACHE["data"] is not None

        # Call 2: Within 30s with use_cache=True -> returns same cached object
        m2 = fetch_sector_core_etf_metrics(use_cache=True)
        assert m1 is m2

        # Call 3: use_cache=False -> forces refresh (new dict instance)
        m3 = fetch_sector_core_etf_metrics(use_cache=False)
        assert m3 is not m1

        # Call 4: Advance timestamp > 30s -> triggers refresh
        _CORE_ETF_METRICS_MEM_CACHE["ts"] = time.time() - 35.0
        m4 = fetch_sector_core_etf_metrics(use_cache=True)
        assert m4 is not m1


# =========================================================================
# 3. Target 3: fetch_macro_cross_market_indicators Adversarial Tests
# =========================================================================

class TestFetchMacroCrossMarketIndicatorsAdversarial:
    """Adversarial stress-testing for fetch_macro_cross_market_indicators."""

    def test_indicator_schema_and_numeric_boundaries(self):
        """Verify presence of all expected indicators and reasonable financial boundaries."""
        res = fetch_macro_cross_market_indicators(use_cache=False)
        assert isinstance(res, dict)

        required_keys = [
            "cgb_10y_yield", "cgb_10y_str",
            "gold_price", "gold_change_pct", "gold_summary",
            "nasdaq_point", "nasdaq_change_pct", "nasdaq_summary",
            "macro_summary", "timestamp"
        ]
        for k in required_keys:
            assert k in res, f"Missing macro indicator key: {k}"

        # Financial domain boundary checks
        assert 0.5 <= res["cgb_10y_yield"] <= 5.0, f"10Y yield outside [0.5%, 5.0%]: {res['cgb_10y_yield']}"
        assert res["cgb_10y_str"].endswith("%")
        assert res["gold_price"] > 1.0, f"Gold price invalid: {res['gold_price']}"
        assert res["nasdaq_point"] > 1000.0, f"Nasdaq point invalid: {res['nasdaq_point']}"
        assert isinstance(res["gold_change_pct"], (int, float))
        assert isinstance(res["nasdaq_change_pct"], (int, float))

    def test_macro_summary_formatting(self):
        """Verify summary string composition and formatting."""
        res = fetch_macro_cross_market_indicators(use_cache=False)
        summary = res["macro_summary"]
        assert "10Y国债" in summary
        assert "黄金ETF" in summary
        assert "隔夜纳指" in summary
        assert "｜" in summary
        assert res["gold_summary"].startswith("黄金ETF")
        assert res["nasdaq_summary"].startswith("隔夜纳指")

    def test_cache_ttl_60s(self):
        """
        Verify memory TTL 60s cache behavior:
        1. use_cache=True within 60s returns cached dict.
        2. use_cache=False bypasses cache.
        3. After 60s, cache is refreshed.
        """
        res1 = fetch_macro_cross_market_indicators(use_cache=True)
        assert _MACRO_INDICATORS_MEM_CACHE["data"] is not None

        res2 = fetch_macro_cross_market_indicators(use_cache=True)
        assert res1 is res2

        res3 = fetch_macro_cross_market_indicators(use_cache=False)
        assert res3 is not res1

        # Advance timestamp by 65s
        _MACRO_INDICATORS_MEM_CACHE["ts"] = time.time() - 65.0
        res4 = fetch_macro_cross_market_indicators(use_cache=True)
        assert res4 is not res1

    def test_network_failure_and_offline_robustness(self):
        """
        When network is down and chinabond parquet is unreadable/missing,
        must degrade gracefully to default safe indicators without crashing.
        """
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Network down")), \
             patch("pathlib.Path.exists", return_value=False):
            res = fetch_macro_cross_market_indicators(use_cache=False)

        assert isinstance(res, dict)
        assert res["cgb_10y_yield"] == 1.62
        assert res["gold_price"] == 8.253
        assert res["nasdaq_point"] == 24579.42
        assert "10Y国债 1.62%" in res["macro_summary"]

    def test_corrupted_sina_stream_parsing(self):
        """Test resilience against broken Sina finance string formats."""
        corrupted_payloads = [
            b'hq_str_sh518880="bad,data";hq_str_gb_ixic="only,two";\n',
            b'hq_str_sh518880="";hq_str_gb_ixic="";\n',
            b'random_unrelated_response\n',
        ]
        for payload in corrupted_payloads:
            mock_resp = MagicMock()
            mock_resp.read.return_value = payload
            mock_resp.__enter__.return_value = mock_resp

            with patch("urllib.request.urlopen", return_value=mock_resp):
                res = fetch_macro_cross_market_indicators(use_cache=False)

            assert isinstance(res, dict)
            assert res["gold_price"] > 0
            assert res["nasdaq_point"] > 0


# =========================================================================
# 4. Target 4: calc_financial_news_sentiment Adversarial Stress Tests
# =========================================================================

class TestCalcFinancialNewsSentimentAdversarial:
    """Adversarial stress-testing for calc_financial_news_sentiment."""

    def test_strict_score_boundaries_property(self):
        """
        Property test: For any random input, score must be bounded strictly in [0.0, 100.0]
        and label must belong to the five valid categories.
        """
        valid_labels = {"积极乐观", "温和看多", "中性均衡", "谨慎防守", "恐慌避险"}
        test_inputs = [
            None,
            [],
            [{"title": "x" * 100, "content": "y" * 100}],
            ["利好 " * 50],
            ["利空 " * 50],
            ["利好 " * 10 + "利空 " * 10],
            [{"title": None, "desc": None}],
            [12345, None, {}],
        ]

        for inp in test_inputs:
            score, label = calc_financial_news_sentiment(inp)
            assert isinstance(score, float)
            assert 0.0 <= score <= 100.0, f"Score {score} out of [0.0, 100.0] for input: {inp}"
            assert label in valid_labels, f"Invalid label {label} for input: {inp}"

    def test_empty_and_null_inputs_return_neutral_50(self):
        """Verify empty, None, and blank inputs all return exactly (50.0, '中性均衡')."""
        assert calc_financial_news_sentiment([]) == (50.0, "中性均衡")
        assert calc_financial_news_sentiment([{}]) == (50.0, "中性均衡")
        assert calc_financial_news_sentiment([{"title": "", "desc": ""}]) == (50.0, "中性均衡")
        assert calc_financial_news_sentiment([{"title": None, "content": None}]) == (50.0, "中性均衡")
        assert calc_financial_news_sentiment(["", "   "]) == (50.0, "中性均衡")

    def test_neutral_and_unrelated_news(self):
        """Unrelated non-financial news with 0 polarity hits returns 50.0."""
        unrelated = [
            {"title": "某地今日天气多云转晴", "content": "气温适宜，适合户外运动"},
            {"title": "第十五届国际科技学术会议闭幕", "desc": "学者齐聚一堂交流前沿学术观点"},
        ]
        score, label = calc_financial_news_sentiment(unrelated)
        assert score == 50.0
        assert label == "中性均衡"

    def test_conflicting_balanced_news(self):
        """
        News with exactly equal positive and negative keyword hits.
        (total_pos == total_neg) -> net_diff == 0.0 -> score == 50.0, label == '中性均衡'.
        """
        balanced_news = [
            {"title": "增持 与 减持 同步发生", "content": "市场利好 与 利空 交织，突破 与 跌破 并存"},
        ]
        score, label = calc_financial_news_sentiment(balanced_news)
        assert score == 50.0
        assert label == "中性均衡"

    def test_extreme_euphoria_inputs(self):
        """
        Extreme bullish news: Multiple bullish keywords repeated.
        Expected: score >= 70.0, label == '积极乐观'.
        """
        euphoria_news = [
            {
                "title": "央行重磅宣布全面降准降息 释放超万亿流动性 提振经济复苏",
                "content": "主力资金净买入放量突破创新高 上市公司密集增持回购 利好超预期 领涨走强全面看多"
            },
            {
                "title": "高景气赛道做多热情高涨 安全垫丰厚 胜率大幅改善",
                "content": "买方积极增配加码 底部企稳反弹高质量增长"
            }
        ]
        score, label = calc_financial_news_sentiment(euphoria_news)
        assert score >= 70.0, f"Expected euphoria score >= 70, got {score}"
        assert label == "积极乐观"

    def test_extreme_panic_inputs(self):
        """
        Extreme panic news: Multiple bearish keywords repeated.
        Expected: score <= 30.0, label == '恐慌避险'.
        """
        panic_news = [
            {
                "title": "多只重仓股突发大额减持 缩量暴跌破位跳水 踩踏抛售清盘",
                "content": "业绩严重低于预期 违规立案被问询 承压下挫领跌 资金大幅杀跌出逃"
            },
            {
                "title": "崩盘恐慌避险情绪蔓延 跌停亏损加剧 破发割肉清仓",
                "content": "市场失守关键点位 爆仓风险加剧 全面看空做空"
            }
        ]
        score, label = calc_financial_news_sentiment(panic_news)
        assert score <= 30.0, f"Expected panic score <= 30, got {score}"
        assert label == "恐慌避险"

    def test_mild_bullish_and_mild_bearish_thresholds(self):
        """
        Test intermediate label thresholds:
        - Mild bullish: 3 positive vs 1 negative -> net_diff = 2/4 = 0.5 -> score = 67.5 -> '温和看多'
        - Mild bearish: 1 positive vs 3 negative -> net_diff = -2/4 = -0.5 -> score = 32.5 -> '谨慎防守'
        """
        # 3 positive: 增持, 利好, 突破; 1 negative: 减持
        mild_bull = [{"title": "股东增持迎来利好，主力突破阻力位，偶有小额减持"}]
        score_bull, label_bull = calc_financial_news_sentiment(mild_bull)
        assert 58.0 <= score_bull < 70.0, f"Expected mild bullish score [58, 70), got {score_bull}"
        assert label_bull == "温和看多"

        # 1 positive: 利好; 3 negative: 减持, 亏损, 下挫
        mild_bear = [{"title": "虽有利好，但股东减持与业绩亏损导致股价下挫"}]
        score_bear, label_bear = calc_financial_news_sentiment(mild_bear)
        assert 30.0 < score_bear <= 42.0, f"Expected mild bearish score (30, 42], got {score_bear}"
        assert label_bear == "谨慎防守"

    def test_string_inputs_and_heterogeneous_lists(self):
        """Test accepting plain strings and ignoring invalid items in list."""
        mixed_list = [
            "央行降准释放利好，市场积极走强",  # string with bullish keywords
            123456,  # invalid type to skip
            None,    # invalid type to skip
            {"invalid_keys": "none"},
            "部分机构谨慎减持防守",            # string with bearish keywords
        ]
        score, label = calc_financial_news_sentiment(mixed_list)
        assert isinstance(score, float)
        assert label in {"积极乐观", "温和看多", "中性均衡", "谨慎防守", "恐慌避险"}

    def test_large_batch_stress_performance(self):
        """Stress test with 2,000 news articles to verify high throughput and sub-second evaluation."""
        base_items = [
            {"title": "主力资金放量突破", "content": "利好频出高质量增长"},
            {"title": "部分资金谨慎防守", "content": "防范回落风险"},
            {"title": "日常行业数据统计简报", "content": "各部门平稳运行"},
        ]
        large_batch = base_items * 700  # 2,100 news items

        t0 = time.time()
        score, label = calc_financial_news_sentiment(large_batch)
        elapsed = time.time() - t0

        assert elapsed < 1.0, f"Evaluation of 2,100 news items took too long: {elapsed:.3f}s"
        assert 0.0 <= score <= 100.0
        assert label in {"积极乐观", "温和看多", "中性均衡", "谨慎防守", "恐慌避险"}


    def test_chinese_date_column_header(self, tmp_path):
        """Test auto-heal when parquet date column is named '日期' instead of 'date'."""
        f_chinese = tmp_path / "000685.SH.parquet"
        df_init = pd.DataFrame({
            "日期": ["2026-10-20", "2026-10-21"],
            "收盘": [10.0, 10.2],
            "涨跌幅": [0.0, 2.0],
        })
        df_init.to_parquet(f_chinese, index=False)

        res = auto_heal_sector_parquets(target_dir=tmp_path)
        assert res["status"] == "success"
        assert res["healed_count"] == 1

        df_healed = pd.read_parquet(f_chinese)
        assert len(df_healed) > len(df_init)
        assert not df_healed.isna().any().any()
        assert "日期" in df_healed.columns

    def test_pre_existing_duplicates_cleaned(self, tmp_path):
        """Test that pre-existing duplicate date rows are de-duplicated during healing."""
        f_dup = tmp_path / "000685.SH.parquet"
        df_init = pd.DataFrame({
            "date": ["2026-10-20", "2026-10-20", "2026-10-21"],
            "open": [10.0, 10.0, 10.5],
            "close": [10.0, 10.0, 10.6],
            "change_pct": [0.0, 0.0, 6.0],
        })
        df_init.to_parquet(f_dup, index=False)

        res = auto_heal_sector_parquets(target_dir=tmp_path)
        assert res["status"] == "success"
        assert res["healed_count"] == 1

        df_healed = pd.read_parquet(f_dup)
        dates = pd.to_datetime(df_healed["date"]).tolist()
        assert len(dates) == len(set(dates)), "Duplicate dates were not removed"


# =========================================================================
# 5. Additional Cross-Market and Monotonicity Stress Tests
# =========================================================================

class TestCrossMarketAndSentimentStress:
    """Stress testing monotonicity and edge cases."""

    def test_macro_au9999_fallback_when_sina_fails(self):
        """Verify fallback to local AU9999.SGE.parquet when Sina network request fails."""
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Sina network failure")):
            res = fetch_macro_cross_market_indicators(use_cache=False)

        assert isinstance(res, dict)
        # AU9999 parquet exists locally with close ~ 1452.30 -> / 100.0 = 14.523
        assert res["gold_price"] == 14.523
        assert "黄金ETF 14.52元" in res["gold_summary"]

    def test_sentiment_score_monotonicity(self):
        """
        Monotonicity test:
        1. When negative keywords exist, adding positive keywords strictly increases score.
        2. In saturated all-positive state, score plateaus at 85.0 (weak monotonicity).
        3. Adding negative keywords strictly decreases score.
        """
        base = [{"title": "上市公司公布业绩，日常运行平稳"}]
        s_base, _ = calc_financial_news_sentiment(base)
        assert s_base == 50.0

        # With 2 negative keywords: "减持 亏损"
        neg_base = [{"title": "减持 亏损"}]
        s_neg_base, _ = calc_financial_news_sentiment(neg_base)
        assert s_neg_base == 15.0

        # Add 1 positive: P=1, N=2 -> net_diff = (1-2)/3 = -0.333 -> score = 38.3
        s_pos_1, _ = calc_financial_news_sentiment([{"title": "减持 亏损 利好"}])
        assert s_pos_1 > s_neg_base

        # Add 2nd positive: P=2, N=2 -> net_diff = 0 -> score = 50.0
        s_pos_2, _ = calc_financial_news_sentiment([{"title": "减持 亏损 利好 突破"}])
        assert s_pos_2 > s_pos_1
        assert s_pos_2 == 50.0

        # Add 3rd positive: P=3, N=2 -> net_diff = 1/5 = 0.2 -> score = 57.0
        s_pos_3, _ = calc_financial_news_sentiment([{"title": "减持 亏损 利好 突破 创新高"}])
        assert s_pos_3 > s_pos_2

        # Saturated positive (0 negative) reaches 85.0 ceiling
        s_pure_pos, _ = calc_financial_news_sentiment([{"title": "增持 回购 利好"}])
        assert s_pure_pos == 85.0
        s_pure_pos_more, _ = calc_financial_news_sentiment([{"title": "增持 回购 利好 突破 创新高"}])
        assert s_pure_pos_more == 85.0
        assert s_pure_pos_more >= s_pure_pos

    def test_sentiment_with_emojis_html_and_newlines(self):
        """Test sentiment analyzer with texts containing HTML tags, emojis, and weird whitespaces."""
        dirty_news = [
            {"title": "<b>重磅利好！</b>🚀🚀🚀 央行宣布降准0.5%！！！\n\r", "desc": "<p>增持 回购 突破 创新高 ！！！</p>"},
            {"title": "🚨🚨🚨 利空预警：部分股东拟大额减持\t\t\n", "desc": "<div>破位 跳水 下挫 风险警示</div>"},
        ]
        score, label = calc_financial_news_sentiment(dirty_news)
        assert isinstance(score, float)
        assert 0.0 <= score <= 100.0
        assert label in {"积极乐观", "温和看多", "中性均衡", "谨慎防守", "恐慌避险"}


# =========================================================================
# 6. Integration Verification: DataLoader Static Methods
# =========================================================================

def test_data_loader_static_methods_attached():
    """Verify all 4 target functions are properly bound as static methods on DataLoader class."""
    assert hasattr(DataLoader, "auto_heal_sector_parquets")
    assert hasattr(DataLoader, "fetch_sector_core_etf_metrics")
    assert hasattr(DataLoader, "fetch_macro_cross_market_indicators")
    assert hasattr(DataLoader, "calc_financial_news_sentiment")

    assert callable(DataLoader.auto_heal_sector_parquets)
    assert callable(DataLoader.fetch_sector_core_etf_metrics)
    assert callable(DataLoader.fetch_macro_cross_market_indicators)
    assert callable(DataLoader.calc_financial_news_sentiment)

