# -*- coding: utf-8 -*-
"""
tests/test_challenger_g13_m1.py

Empirical Challenge & Stress Test Suite for Milestone 1:
1. Cache stress testing:
   - Cold start (cache miss) handling & fast fallback without GA blocking
   - Warm start (cache hit) latency benchmark (< 5ms) across multi-run statistical distribution
   - Expired cache (> 12h) TTL detection and recomputation
   - Corrupted cache handling (malformed JSON, empty file, non-dict JSON, binary garbage, missing keys)
2. Backtest curve integrity verification:
   - Source code & AST verification: zero artificial linear alpha addition (r_arr += alpha_ann / 250)
   - Zero alpha numerical identity: pure bond portfolio strategy NAV vs benchmark NAV
   - Benchmark fidelity: H11009 (not 930609) has real daily fluctuations, positive CAGR around 4.8%
   - Disclaimer & C3 dynamic strategy comparison curve behavior for real ledger vs non-real ledger

Written by challenger_g13_m1_1 (empirical challenger).
"""

import ast
import inspect
import json
import os
import shutil
import sys
import tempfile
import textwrap
import time
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))
if str(WORKSPACE_ROOT / "AGY2_FundAdvisory") not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT / "AGY2_FundAdvisory"))

from AGY2_FundAdvisory.advisory_engine import (
    OnlineHeuristicFactorEvolver,
    OpportunityRadarEngine,
)
from AGY2_FundAdvisory.strategy_bridge import (
    BENCHMARK_INDICES_MAP,
    UNIVERSE_18_CHAMPION_POOL,
    StrategyBridge,
)


class TestFactorEvolutionCacheStress:
    """Stress tests and empirical benchmarks for factor evolution disk caching."""

    @pytest.fixture(autouse=True)
    def preserve_cache_state(self):
        """Fixture to preserve existing cache and restore after tests."""
        cache_path = OnlineHeuristicFactorEvolver._resolve_cache_path()
        backup_path = cache_path.with_suffix(".json.bak_challenger")
        existed = cache_path.exists()
        if existed:
            shutil.copy2(cache_path, backup_path)
        yield cache_path
        # Cleanup and restore
        if existed and backup_path.exists():
            shutil.copy2(backup_path, cache_path)
            backup_path.unlink(missing_ok=True)
        elif not existed and cache_path.exists():
            cache_path.unlink(missing_ok=True)
        if backup_path.exists():
            backup_path.unlink(missing_ok=True)

    def test_cache_miss_cold_start_handling(self, preserve_cache_state):
        """
        Verify cold start behavior when cache file does not exist:
        1. OpportunityRadarEngine does NOT block on GA (evolved_result status is 'cached_default').
        2. Returns valid fallback weights [0.30, 0.30, 0.25, 0.15].
        3. OnlineHeuristicFactorEvolver._read_disk_cache returns None without crashing.
        4. When evolver.evolve_factor_weights() or get_60d_rolling_nav_and_trajectory() is called,
           it successfully writes to data/cache/factor_evolution_cache.json.
        """
        cache_path = preserve_cache_state
        if cache_path.exists():
            cache_path.unlink()

        evolver = OnlineHeuristicFactorEvolver()
        assert evolver._read_disk_cache() is None

        # OpportunityRadarEngine initialization on cold start:
        radar = OpportunityRadarEngine()
        # Verify it uses fast fallback instead of running GA
        assert radar.factor_weights == [0.30, 0.30, 0.25, 0.15]
        assert radar.evolved_result.get("status") == "cached_default"
        assert radar.evolved_result.get("elapsed_ms") <= 1.0  # fallback constant, not live GA

        # Test creating cache via _write_disk_cache
        evolver._write_disk_cache({
            "weights": [0.30, 0.30, 0.25, 0.15],
            "generation_scores": [1.5, 1.6, 1.7, 1.85],
            "best_fitness": 1.85,
        })
        assert cache_path.exists()
        disk_data = evolver._read_disk_cache()
        assert disk_data is not None
        assert disk_data.get("weights") == [0.30, 0.30, 0.25, 0.15]

    def test_warm_cache_performance_under_5ms_benchmark(self, preserve_cache_state):
        """
        Empirically measure elapsed time for get_60d_rolling_nav_and_trajectory on warm cache.
        Requirement: Warm cache read must be < 5ms!
        We test 50 fresh evolver instances to guarantee no in-memory shortcut is masking disk read latency.
        """
        cache_path = preserve_cache_state

        mock_res = {
            "dates": [f"2026-01-{i:02d}" for i in range(1, 61)],
            "nav_dynamic": [round(1.0 + i * 0.001, 4) for i in range(60)],
            "nav_static": [round(1.0 + i * 0.0005, 4) for i in range(60)],
            "final_nav_dynamic": 1.059,
            "final_nav_static": 1.030,
            "alpha_pct": 2.9,
            "mdd_dynamic_pct": 1.2,
            "mdd_static_pct": 2.0,
            "trajectory": [
                {
                    "date": f"2026-01-{i:02d}",
                    "valuation": 0.30,
                    "momentum": 0.30,
                    "snr": 0.25,
                    "anti_crowding": 0.15,
                    "weights": [0.30, 0.30, 0.25, 0.15],
                    "regime_mode": "平稳蓄势态",
                    "operator_rule_expression": "RuleTree: Mock",
                }
                for i in range(60)
            ],
        }
        cache_payload = {
            "timestamp": time.time(),
            "weights": [0.30, 0.30, 0.25, 0.15],
            "generation_scores": [1.5, 1.6, 1.7, 1.85],
            "best_fitness": 1.85,
            "nav_trajectory": mock_res,
        }
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_payload, f, ensure_ascii=False)

        latencies_ms = []
        n_trials = 50
        for _ in range(n_trials):
            # Create fresh instance each time to ensure disk read path is executed
            fresh_evolver = OnlineHeuristicFactorEvolver()
            t0 = time.perf_counter()
            data = fresh_evolver.get_60d_rolling_nav_and_trajectory(force=False)
            dt_ms = (time.perf_counter() - t0) * 1000.0
            latencies_ms.append(dt_ms)
            assert data["final_nav_dynamic"] == 1.059

        min_ms = min(latencies_ms)
        max_ms = max(latencies_ms)
        mean_ms = sum(latencies_ms) / len(latencies_ms)
        median_ms = sorted(latencies_ms)[len(latencies_ms) // 2]
        p95_ms = sorted(latencies_ms)[int(len(latencies_ms) * 0.95)]

        print(f"\n[Warm Cache Benchmark] {n_trials} runs -> Min: {min_ms:.3f}ms, Median: {median_ms:.3f}ms, Mean: {mean_ms:.3f}ms, P95: {p95_ms:.3f}ms, Max: {max_ms:.3f}ms")

        assert median_ms < 5.0, f"Warm cache median latency {median_ms:.3f}ms >= 5.0ms threshold!"
        assert mean_ms < 5.0, f"Warm cache mean latency {mean_ms:.3f}ms >= 5.0ms threshold!"
        assert p95_ms < 8.0, f"Warm cache p95 latency {p95_ms:.3f}ms exceeds tolerance!"

    def test_expired_cache_ttl_detection(self, preserve_cache_state):
        """
        Verify cache expiration behavior:
        1. Cache with timestamp > 43200s (12h) is treated as expired (returns None).
        2. OpportunityRadarEngine falls back safely without unhandled error.
        """
        cache_path = preserve_cache_state
        expired_payload = {
            "timestamp": time.time() - 43205.0,  # 12h + 5s ago
            "weights": [0.25, 0.25, 0.25, 0.25],
            "nav_trajectory": {"mock": True},
        }
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(expired_payload, f)

        evolver = OnlineHeuristicFactorEvolver()
        # Should return None because cache is expired
        cached_data = evolver._read_disk_cache(max_age_seconds=43200.0)
        assert cached_data is None, "Expired cache was incorrectly accepted as valid!"

        # OpportunityRadarEngine must handle expired cache safely
        radar = OpportunityRadarEngine()
        assert radar.factor_weights == [0.30, 0.30, 0.25, 0.15]

    @pytest.mark.parametrize(
        "corrupt_content,description,can_heal",
        [
            ("{\"weights\": [0.3, 0.3, ", "Truncated JSON syntax", True),
            ("!@#$%^&*()_+GARBAGE_BYTES", "Completely unparseable text", True),
            ("", "Empty 0-byte file", True),
            ("{\"timestamp\": \"not_a_float\"}", "Corrupted timestamp type", True),
            ("[1, 2, 3, 4, 5]", "JSON array instead of dict", False),
            ("null", "JSON null value", False),
        ],
    )
    def test_corrupted_cache_adversarial_handling(self, preserve_cache_state, corrupt_content, description, can_heal):
        """
        Adversarial test: corrupt cache file in various hostile ways.
        1. OnlineHeuristicFactorEvolver._read_disk_cache MUST return None and NEVER raise unhandled exception.
        2. OpportunityRadarEngine MUST instantiate safely without crashing.
        3. For syntax errors / empty files, _write_disk_cache heals the file.
        4. For valid non-dict JSON (array/null), we verify _read_disk_cache protects the app (returns None).
        """
        cache_path = preserve_cache_state
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(corrupt_content)

        evolver = OnlineHeuristicFactorEvolver()
        # 1. Read must return None and NOT raise exception
        res = evolver._read_disk_cache()
        assert res is None, f"Failed for {description}: expected None, got {res}"

        # 2. OpportunityRadarEngine must instantiate safely without crashing
        radar = OpportunityRadarEngine()
        assert len(radar.factor_weights) == 4

        # 3. Test self-healing behavior
        if can_heal:
            evolver._write_disk_cache({"weights": [0.35, 0.25, 0.25, 0.15], "healed": True})
            with open(cache_path, "r", encoding="utf-8") as f:
                healed_data = json.load(f)
            assert healed_data.get("healed") is True
            assert healed_data.get("weights") == [0.35, 0.25, 0.25, 0.15]
        else:
            # Documented limitation: when corrupt content is valid JSON but non-dict,
            # _write_disk_cache catches AttributeError on non-dict .update() and silently skips.
            # However, _read_disk_cache still safely returns None, shielding the application.
            pass


class TestBacktestCurveIntegrity:
    """Stress tests and empirical verification of backtest engine curves and benchmarks."""

    def test_ast_and_source_zero_artificial_linear_alpha(self):
        """
        Verify via AST inspection and source analysis that:
        1. 'alpha_ann / 250' is completely deleted from build_custom_portfolio_backtest.
        2. No constant synthetic daily alpha is added to returns.
        """
        src = inspect.getsource(StrategyBridge.build_custom_portfolio_backtest)
        assert "alpha_ann / 250" not in src, "Found illegal synthetic alpha code: 'alpha_ann / 250'!"
        assert "alpha_ann" not in src, "Found 'alpha_ann' still referenced in build_custom_portfolio_backtest!"

        # Parse AST to ensure no AugAssign (+=) with suspicious constant names
        tree = ast.parse(textwrap.dedent(src))
        for node in ast.walk(tree):
            if isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Add):
                target_name = getattr(node.target, "id", "")
                if target_name in ["r_arr", "port_ret"]:
                    rhs_src = ast.unparse(node.value) if hasattr(ast, "unparse") else ""
                    assert "alpha" not in rhs_src.lower(), f"Suspicious alpha addition in AST: {rhs_src}"

    def test_pure_bond_zero_alpha_exact_identity(self):
        """
        Numerical verification: Backtest 100% pure bond fund '002351'.
        Since '002351' is mapped to 'H11009' with 0 alpha, its synthesized daily strategy return
        must exactly match the H11009 benchmark daily return, with ZERO alpha drift.
        """
        df = StrategyBridge.build_custom_portfolio_backtest(
            fund_weights={"002351": 1.0},
            rebalance_freq="quarterly",
        )
        assert "strategy_nav" in df.columns
        assert "bm_nav_纯债指数" in df.columns

        strat_nav = df["strategy_nav"].values
        bm_nav = df["bm_nav_纯债指数"].values

        # Maximum absolute discrepancy between strategy NAV and benchmark NAV
        max_diff = np.max(np.abs(strat_nav - bm_nav))
        print(f"\n[Pure Bond Identity] Max NAV discrepancy: {max_diff:.8e}")
        assert max_diff < 1e-6, f"Pure bond strategy NAV diverged from benchmark! Max diff: {max_diff}"

        # Check daily return difference
        r_strat = np.diff(strat_nav) / strat_nav[:-1]
        r_bm = np.diff(bm_nav) / bm_nav[:-1]
        max_ret_diff = np.max(np.abs(r_strat - r_bm))
        assert max_ret_diff < 1e-6, f"Daily return has unexpected drift! Max diff: {max_ret_diff}"

    def test_h11009_benchmark_daily_fluctuations_and_cagr(self):
        """
        Verify H11009 benchmark properties:
        1. BENCHMARK_INDICES_MAP['纯债指数'] maps to 'H11009' (not '930609').
        2. Daily returns have real volatility (not flat 0 std).
        3. Second difference is not 0 (not linearly interpolated).
        4. CAGR is positive and around 4.85% (within [4.5%, 5.2%]).
        5. Realistic max drawdown (between 0.5% and 4.0%).
        """
        assert BENCHMARK_INDICES_MAP["纯债指数"]["col"] == "H11009", (
            f"Expected 'H11009', got {BENCHMARK_INDICES_MAP['纯债指数']['col']}"
        )

        df = StrategyBridge.build_custom_portfolio_backtest(fund_weights={"002351": 1.0})
        bm_nav = df["bm_nav_纯债指数"].values
        n_days = len(bm_nav)
        assert n_days > 1000, f"Backtest length unexpectedly short: {n_days} days"

        # 1. Start at 1.0
        assert abs(bm_nav[0] - 1.0) < 1e-6

        # 2. Daily fluctuations
        daily_ret = np.diff(bm_nav) / bm_nav[:-1]
        daily_vol_ann = np.std(daily_ret) * np.sqrt(252.0)
        print(f"\n[H11009 Metrics] Annualized Volatility: {daily_vol_ann * 100.0:.2f}%")
        assert daily_vol_ann > 0.005, f"H11009 volatility suspiciously low ({daily_vol_ann:.4f}), looks flat!"
        assert daily_vol_ann < 0.10, f"H11009 volatility suspiciously high ({daily_vol_ann:.4f}) for bond index!"

        # 3. Curvature: second difference is not zero
        second_diff = np.diff(daily_ret)
        assert np.max(np.abs(second_diff)) > 1e-5, "H11009 daily return has zero curvature (linear interpolation detected)!"

        # 4. CAGR calculation
        total_ret = bm_nav[-1] / bm_nav[0]
        cagr = (total_ret ** (252.0 / n_days) - 1.0) * 100.0
        print(f"[H11009 Metrics] Final NAV: {bm_nav[-1]:.4f}, Total Days: {n_days}, CAGR: {cagr:.2f}%")
        assert 4.5 <= cagr <= 5.2, f"H11009 CAGR {cagr:.2f}% outside expected [4.5%, 5.2%] range!"

        # 5. Drawdown
        peak = np.maximum.accumulate(bm_nav)
        dd = (peak - bm_nav) / peak
        max_dd_pct = np.max(dd) * 100.0
        print(f"[H11009 Metrics] Max Drawdown: {max_dd_pct:.2f}%")
        assert 0.5 <= max_dd_pct <= 4.0, f"H11009 max drawdown {max_dd_pct:.2f}% unrealistic for Chinese aggregate bond!"

    def test_disclaimer_and_c3_dynamic_strategy_comparison(self):
        """
        Verify disclaimer metadata and C3 dynamic strategy comparison curve behavior:
        1. When is_real_ledger=True or target_name contains '实盘' / '账本':
           - df.attrs['disclaimer'] contains warning about static retrospective survivorship bias.
           - getattr(df, 'disclaimer') matches attrs.
           - df.attrs['is_real_ledger'] is True.
        2. When is_real_ledger=False and regular target_name:
           - disclaimer is empty.
           - df.attrs['is_real_ledger'] is False.
        3. 'c3_dynamic_nav' and 'c3_dynamic_drawdown' are always attached for UI comparison.
        4. 'c3_dynamic_nav' is a real dynamic curve: starts at 1.0, has non-zero volatility, has drawdowns.
        """
        weights = {"002351": 0.40, "001015": 0.30, "000216": 0.20, "017436": 0.10}

        # Case A: Real ledger explicit flag
        df_real = StrategyBridge.build_custom_portfolio_backtest(
            fund_weights=weights,
            is_real_ledger=True,
            target_name="任意名称",
        )
        assert df_real.attrs.get("is_real_ledger") is True
        expected_disclaimer = "当前持仓静态权重历史回溯（含历史后视镜权重效应，非滚动样本外实盘记录）"
        assert df_real.attrs.get("disclaimer") == expected_disclaimer
        assert getattr(df_real, "disclaimer", "") == expected_disclaimer

        # Case B: Real ledger detected via target_name
        df_named = StrategyBridge.build_custom_portfolio_backtest(
            fund_weights=weights,
            target_name="主实盘账本持仓",
        )
        assert df_named.attrs.get("is_real_ledger") is True
        assert df_named.attrs.get("disclaimer") == expected_disclaimer

        # Case C: Not a real ledger
        df_regular = StrategyBridge.build_custom_portfolio_backtest(
            fund_weights=weights,
            is_real_ledger=False,
            target_name="新资建仓选优组合",
        )
        assert df_regular.attrs.get("is_real_ledger") is False
        assert df_regular.attrs.get("disclaimer") == ""
        assert getattr(df_regular, "disclaimer", "") == ""

        # Case D: C3 dynamic comparison curve validation
        for df_case, label in [(df_real, "Real Ledger"), (df_regular, "Regular Portfolio")]:
            assert "c3_dynamic_nav" in df_case.columns, f"c3_dynamic_nav missing in {label}!"
            assert "c3_dynamic_drawdown" in df_case.columns, f"c3_dynamic_drawdown missing in {label}!"

            c3_nav = df_case["c3_dynamic_nav"].values
            c3_dd = df_case["c3_dynamic_drawdown"].values

            assert abs(c3_nav[0] - 1.0) < 1e-4, f"C3 dynamic NAV must start at 1.0 in {label}"
            assert c3_nav[-1] > 1.20, f"C3 dynamic NAV final value {c3_nav[-1]} unexpectedly low in {label}"
            assert np.std(c3_nav) > 0.05, f"C3 dynamic NAV has suspiciously low volatility in {label}"
            assert np.min(c3_dd) <= 0.0, f"C3 drawdown must be non-positive in {label}"
            assert np.max(c3_dd) <= 1e-6, f"C3 drawdown cannot be positive in {label}"

    def test_multi_portfolio_combinations_robustness(self):
        """
        Run backtest across multiple edge-case portfolio configurations:
        1. Single equity (510300)
        2. Single gold (000216)
        3. Single tech (588000)
        4. Single US equity (017436)
        5. Equal-weight 8-asset diversified barbell
        Ensure all produce clean DataFrames without NaN/inf and with consistent dimensions.
        """
        test_portfolios = [
            ("Single 300", {"510300": 1.0}),
            ("Single Gold", {"000216": 1.0}),
            ("Single Star50", {"588000": 1.0}),
            ("Single SPX", {"017436": 1.0}),
            ("8-Asset Barbell", {
                "002351": 0.20,
                "000086": 0.10,
                "001015": 0.15,
                "005561": 0.15,
                "000216": 0.10,
                "017436": 0.10,
                "510300": 0.10,
                "588000": 0.10,
            }),
        ]

        for name, p_weights in test_portfolios:
            df = StrategyBridge.build_custom_portfolio_backtest(fund_weights=p_weights)
            assert len(df) > 1000, f"Portfolio {name} returned truncated backtest!"
            assert not df["strategy_nav"].isna().any(), f"Portfolio {name} strategy_nav contains NaN!"
            assert not np.isinf(df["strategy_nav"].values).any(), f"Portfolio {name} strategy_nav contains Inf!"
            assert abs(df["strategy_nav"].iloc[0] - 1.0) < 1e-4, f"Portfolio {name} strategy_nav does not start at 1.0!"
            assert df["strategy_nav"].iloc[-1] > 0.5, f"Portfolio {name} collapsed unrealistically!"
