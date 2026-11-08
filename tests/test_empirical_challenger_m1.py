# -*- coding: utf-8 -*-
"""
Empirical Challenge Test Suite for Milestone 1:
- Bug 3: _apply_fund_valuation_calibration & _apply_qdii_valuation_correction
- Bug 4: SmartExecutionDCAEngine.compute_portfolio_weighted_bias_and_erp

Written by teamwork_challenger (empirical challenger).
Adversarial challenge, property-based tests, boundary conditions, zero/negative inputs, and stress testing.
"""

import math
import random
import sys
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Ensure workspace root and AGY2_FundAdvisory are in sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from AGY2_FundAdvisory.advisory_engine import SmartExecutionDCAEngine
from AGY2_FundAdvisory.portfolio_manager import (
    INDEX_AND_FEEDER_BENCHMARK_MAP,
    QDII_BENCHMARK_MAP,
    FundQuote,
    _apply_fund_valuation_calibration,
    _apply_qdii_valuation_correction,
    clear_realtime_cache,
)


# =====================================================================
# Challenge Group 1: Bug 3 - Feeder Funds (0.95 Factor) & Boundary Tests
# =====================================================================

class TestBug3FeederFundValuationCalibration:
    """
    Adversarial verification of Feeder fund calibration with 0.95 factor:
    - Positive, negative, zero, and extreme benchmark movements
    - Boundary threshold (0.1% for domestic index/feeder funds)
    - Name keyword matching ("联接", "feeder")
    - NAV formula & dwjz edge cases
    """

    @pytest.mark.parametrize("b_change,expected_gszzl", [
        (10.0, 9.50),    # +10% * 0.95 = 9.50%
        (5.0, 4.75),     # +5% * 0.95 = 4.75%
        (2.0, 1.90),     # +2% * 0.95 = 1.90%
        (0.5, round(0.5 * 0.95, 2)),     # +0.5% * 0.95 = 0.474999... -> float round yields 0.47% (IEEE-754 round-to-even)
        (-0.5, round(-0.5 * 0.95, 2)),   # -0.5% * 0.95 = -0.474999... -> float round yields -0.47%
        (-2.0, -1.90),   # -2% * 0.95 = -1.90%
        (-5.0, -4.75),   # -5% * 0.95 = -4.75%
        (-10.0, -9.50),  # -10% * 0.95 = -9.50%
    ])
    def test_adv_feeder_fund_various_benchmark_moves(self, b_change: float, expected_gszzl: float):
        """测试 ETF 联接基金在不同基准涨跌幅下的 0.95 仓位折算"""
        mock_index_quote = {
            "name": "科创50ETF",
            "symbol": "sh588000",
            "change_pct": b_change,
            "point": 1.050,
        }
        q_in = FundQuote(
            name="华夏科创50ETF联接A",
            dwjz=1.2000,
            gsz=1.2000,
            gszzl=0.0,  # 天天基金盘中滞后为 0.0
            gztime="2026-11-08 14:30",
            fund_code="011613",
            valuation_corrected=False
        )
        with patch("AGY2_FundAdvisory.portfolio_manager.fetch_realtime_index_quote", return_value=mock_index_quote):
            q_out = _apply_fund_valuation_calibration(q_in)

        assert q_out.valuation_corrected is True
        assert q_out.gszzl == expected_gszzl
        assert q_out.gsz == round(1.2000 * (1.0 + expected_gszzl / 100.0), 4)
        assert "基准纠偏: sh588000" in q_out.gztime

    def test_adv_feeder_fund_zero_benchmark_change(self):
        """
        测试基准涨跌幅为 0.0% 时：
        1. 基金原估值非零且滞后 (如 0.8%) -> 偏差 > 0.1% -> 触发校准为 0.0%
        2. 基金原估值为 0.0% -> q.gszzl == 0.0 满足 -> 标记已校准为 0.0%
        3. 基金原估值为 0.05% (偏差 <= 0.1% 且非零) -> 不触发校准
        """
        mock_zero = {"symbol": "sh588000", "change_pct": 0.0}

        # 情况 1: 原估值滞后为 0.8%
        with patch("AGY2_FundAdvisory.portfolio_manager.fetch_realtime_index_quote", return_value=mock_zero):
            q1 = FundQuote(
                name="华夏科创50ETF联接A",
                dwjz=1.0000,
                gsz=1.0080,
                gszzl=0.8,
                gztime="14:30",
                fund_code="011613"
            )
            out1 = _apply_fund_valuation_calibration(q1)
            assert out1.valuation_corrected is True
            assert out1.gszzl == 0.0
            assert out1.gsz == 1.0000

        # 情况 2: 原估值已是 0.0%
        with patch("AGY2_FundAdvisory.portfolio_manager.fetch_realtime_index_quote", return_value=mock_zero):
            q2 = FundQuote(
                name="华夏科创50ETF联接A",
                dwjz=1.0000,
                gsz=1.0000,
                gszzl=0.0,
                gztime="14:30",
                fund_code="011613"
            )
            out2 = _apply_fund_valuation_calibration(q2)
            assert out2.valuation_corrected is True
            assert out2.gszzl == 0.0

        # 情况 3: 原估值为 0.05% (abs(0.05 - 0.0) = 0.05 <= 0.1 且 != 0.0) -> 不触发纠偏
        with patch("AGY2_FundAdvisory.portfolio_manager.fetch_realtime_index_quote", return_value=mock_zero):
            q3 = FundQuote(
                name="华夏科创50ETF联接A",
                dwjz=1.0000,
                gsz=1.0005,
                gszzl=0.05,
                gztime="14:30",
                fund_code="011613"
            )
            out3 = _apply_fund_valuation_calibration(q3)
            assert out3.valuation_corrected is False
            assert out3.gszzl == 0.05

    def test_adv_feeder_fund_boundary_01pct_tolerance(self):
        """
        精确边界测试：A 股指数/联接基金的 0.1% 偏差阈值
        当基准涨跌幅为 +2.00%，联接理论校准值为 +1.90% (2.00 * 0.95)：
        - 原估值为 1.98% (偏差 0.08% <= 0.1%) -> 不触发校准
        - 原估值为 1.79% (偏差 0.11% > 0.1%) -> 严格触发校准为 1.90%
        - 原估值为 2.02% (偏差 0.12% > 0.1%) -> 严格触发校准为 1.90%
        """
        mock_index = {"symbol": "sh588000", "change_pct": 2.00}

        # 偏差 0.08% <= 0.1% -> 不触发
        with patch("AGY2_FundAdvisory.portfolio_manager.fetch_realtime_index_quote", return_value=mock_index):
            q_within = FundQuote(
                name="华夏科创50ETF联接A",
                dwjz=1.0000,
                gsz=1.0198,
                gszzl=1.98,
                gztime="14:30",
                fund_code="011613"
            )
            res_within = _apply_fund_valuation_calibration(q_within)
            assert res_within.valuation_corrected is False
            assert res_within.gszzl == 1.98

        # 偏差 0.11% > 0.1% (下方超卖滞后) -> 触发
        with patch("AGY2_FundAdvisory.portfolio_manager.fetch_realtime_index_quote", return_value=mock_index):
            q_under = FundQuote(
                name="华夏科创50ETF联接A",
                dwjz=1.0000,
                gsz=1.0179,
                gszzl=1.79,
                gztime="14:30",
                fund_code="011613"
            )
            res_under = _apply_fund_valuation_calibration(q_under)
            assert res_under.valuation_corrected is True
            assert res_under.gszzl == 1.90

        # 偏差 0.12% > 0.1% (上方超买滞后) -> 触发
        with patch("AGY2_FundAdvisory.portfolio_manager.fetch_realtime_index_quote", return_value=mock_index):
            q_over = FundQuote(
                name="华夏科创50ETF联接A",
                dwjz=1.0000,
                gsz=1.0202,
                gszzl=2.02,
                gztime="14:30",
                fund_code="011613"
            )
            res_over = _apply_fund_valuation_calibration(q_over)
            assert res_over.valuation_corrected is True
            assert res_over.gszzl == 1.90

    @pytest.mark.parametrize("fund_name", [
        "易方达中证红利低波动ETF联接A",
        "华夏半导体芯片ETF feeder C",
        "南方中证500ETF Feeder",
        "富国中证1000ETF联接C",
    ])
    def test_adv_feeder_naming_recognition(self, fund_name: str):
        """测试中英文联接基金关键词 ('联接', 'feeder', 'Feeder') 均能识别为 0.95 仓位折算"""
        mock_quote = {"symbol": "sh512890", "change_pct": 2.0}
        q = FundQuote(
            name=fund_name,
            dwjz=1.0,
            gsz=1.0,
            gszzl=0.0,
            gztime="14:30",
            fund_code="005561"
        )
        with patch("AGY2_FundAdvisory.portfolio_manager.fetch_realtime_index_quote", return_value=mock_quote):
            out = _apply_fund_valuation_calibration(q)
            assert out.valuation_corrected is True
            # 2.0 * 0.95 = 1.90
            assert out.gszzl == 1.90

    def test_adv_feeder_fund_zero_dwjz_defensive(self):
        """防御性测试：当 dwjz <= 0 时，calibrated_gsz 应安全回退为 q.gsz，不发生崩溃"""
        mock_quote = {"symbol": "sh588000", "change_pct": 3.0}
        q_zero_dwjz = FundQuote(
            name="华夏科创50ETF联接A",
            dwjz=0.0,
            gsz=1.5555,
            gszzl=0.0,
            gztime="14:30",
            fund_code="011613"
        )
        with patch("AGY2_FundAdvisory.portfolio_manager.fetch_realtime_index_quote", return_value=mock_quote):
            out = _apply_fund_valuation_calibration(q_zero_dwjz)
            assert out.valuation_corrected is True
            assert out.gszzl == round(3.0 * 0.95, 2)
            assert out.gsz == 1.5555  # 回退保持原 gsz

    def test_adv_already_corrected_short_circuits(self):
        """短路防护：如果 q.valuation_corrected 为 True，绝不再次发起网络请求"""
        q_done = FundQuote(
            name="华夏科创50ETF联接A",
            dwjz=1.0000,
            gsz=1.0190,
            gszzl=1.90,
            gztime="14:30 (基准纠偏)",
            fund_code="011613",
            valuation_corrected=True
        )
        # Mock 抛异常以确保短路
        with patch("AGY2_FundAdvisory.portfolio_manager.fetch_realtime_index_quote", side_effect=RuntimeError("Must not call!")):
            out = _apply_fund_valuation_calibration(q_done)
            assert out.valuation_corrected is True
            assert out.gszzl == 1.90


# =====================================================================
# Challenge Group 2: Bug 3 - Pure Index Funds (1.0 Factor) & Keyword Mapping
# =====================================================================

class TestBug3PureIndexFundValuationCalibration:
    """
    Adversarial verification of Pure Index Funds (1.0 factor, no feeder discount):
    - Exact 1.0 factor scaling across range of changes
    - Keyword fallback mapping for funds without explicit code mapping
    """

    @pytest.mark.parametrize("b_change", [6.0, 3.2, 1.0, -1.5, -4.5, -9.0])
    def test_adv_pure_index_fund_exact_100_factor(self, b_change: float):
        """纯指数基金 (如 100032 富国中证红利指数增强A) 必须使用 1.0 仓位折算"""
        mock_index_quote = {
            "name": "中证红利ETF",
            "symbol": "sh515080",
            "change_pct": b_change,
        }
        q_in = FundQuote(
            name="富国中证红利指数增强A",
            dwjz=1.5000,
            gsz=1.5000,
            gszzl=0.0,
            gztime="14:30",
            fund_code="100032",
            valuation_corrected=False
        )
        with patch("AGY2_FundAdvisory.portfolio_manager.fetch_realtime_index_quote", return_value=mock_index_quote):
            q_out = _apply_fund_valuation_calibration(q_in)

        assert q_out.valuation_corrected is True
        # 1.0 系数：gszzl 应与 b_change 严格相等
        assert q_out.gszzl == round(b_change, 2)
        assert q_out.gsz == round(1.5000 * (1.0 + b_change / 100.0), 4)

    @pytest.mark.parametrize("fund_code,fund_name,expected_symbol", [
        ("999001", "某某中证科创创业指数A", "sh588000"),
        ("999002", "天弘中证芯片产业指数C", "sz159995"),
        ("999003", "广发中证红利低波动指数A", "sh512890"),
        ("999004", "易方达沪深300指数增强A", "sh510300"),
        ("999005", "华夏中证500指数智选C", "sh510500"),
        ("999006", "国泰中证1000指数增强A", "sh560010"),
        ("999007", "某某中证白酒指数分级", "sz399997"),
    ])
    def test_adv_pure_index_name_keyword_fallback(self, fund_code: str, fund_name: str, expected_symbol: str):
        """对未在字典硬编码代码表中的纯指数基金，验证名称关键字能正确匹配基准代码并 1.0 校准"""
        mock_index_quote = {
            "symbol": expected_symbol,
            "change_pct": 2.50,
        }
        q = FundQuote(
            name=fund_name,
            dwjz=1.0000,
            gsz=1.0000,
            gszzl=0.0,
            gztime="14:30",
            fund_code=fund_code,
            valuation_corrected=False
        )
        with patch("AGY2_FundAdvisory.portfolio_manager.fetch_realtime_index_quote", return_value=mock_index_quote) as mock_fetch:
            out = _apply_fund_valuation_calibration(q)
            assert out.valuation_corrected is True
            assert out.gszzl == 2.50
            mock_fetch.assert_called_once_with(expected_symbol, use_cache=True)


# =====================================================================
# Challenge Group 3: Bug 3 - QDII Funds (1.5% Strict Boundary)
# =====================================================================

class TestBug3QDIISpecificBoundaries:
    """
    Adversarial verification of QDII / Global asset calibration:
    - Strict 1.5% deviation boundary condition
    - IEEE-754 floating point considerations
    - QDII feeder vs QDII pure fund factor
    - Code and keyword recognition
    """

    def test_adv_qdii_150_boundary_positive_side(self):
        """
        正向基准偏差 1.5% 临界测试：
        基准为 0.0% 时：
        - 偏差 1.5000% -> abs(1.50 - 0.0) <= 1.5 -> 绝不触发
        - 偏差 1.5001% -> abs(1.5001 - 0.0) > 1.5 -> 严格触发
        """
        mock_bench = {"symbol": "sh513500", "change_pct": 0.0}

        # 1.5000% 刚好在边界上
        with patch("AGY2_FundAdvisory.portfolio_manager.fetch_realtime_index_quote", return_value=mock_bench):
            q_exact = FundQuote(
                name="博时标普500ETF联接A",
                dwjz=2.0000,
                gsz=2.0300,
                gszzl=1.50,
                gztime="14:30",
                fund_code="050025",
                valuation_corrected=False
            )
            res_exact = _apply_fund_valuation_calibration(q_exact)
            assert res_exact.valuation_corrected is False
            assert res_exact.gszzl == 1.50

        # 1.5001% 超过边界
        with patch("AGY2_FundAdvisory.portfolio_manager.fetch_realtime_index_quote", return_value=mock_bench):
            q_over = FundQuote(
                name="博时标普500ETF联接A",
                dwjz=2.0000,
                gsz=2.0301,
                gszzl=1.5001,
                gztime="14:30",
                fund_code="050025",
                valuation_corrected=False
            )
            res_over = _apply_fund_valuation_calibration(q_over)
            assert res_over.valuation_corrected is True
            assert res_over.gszzl == 0.0  # 0.0 * 0.95 = 0.0

    def test_adv_qdii_150_boundary_negative_side(self):
        """
        负向基准偏差 1.5% 临界测试：
        基准为 0.0% 时：
        - 偏差 -1.5000% -> abs(-1.50 - 0.0) <= 1.5 -> 绝不触发
        - 偏差 -1.5001% -> abs(-1.5001 - 0.0) > 1.5 -> 严格触发
        """
        mock_bench = {"symbol": "sh513500", "change_pct": 0.0}

        # -1.5000% 刚好在边界上
        with patch("AGY2_FundAdvisory.portfolio_manager.fetch_realtime_index_quote", return_value=mock_bench):
            q_exact_neg = FundQuote(
                name="广发纳斯达克100ETF联接A",
                dwjz=1.8000,
                gsz=1.7730,
                gszzl=-1.50,
                gztime="14:30",
                fund_code="006075",
                valuation_corrected=False
            )
            res_exact_neg = _apply_fund_valuation_calibration(q_exact_neg)
            assert res_exact_neg.valuation_corrected is False
            assert res_exact_neg.gszzl == -1.50

        # -1.5001% 超过边界
        with patch("AGY2_FundAdvisory.portfolio_manager.fetch_realtime_index_quote", return_value=mock_bench):
            q_over_neg = FundQuote(
                name="广发纳斯达克100ETF联接A",
                dwjz=1.8000,
                gsz=1.7729,
                gszzl=-1.5001,
                gztime="14:30",
                fund_code="006075",
                valuation_corrected=False
            )
            res_over_neg = _apply_fund_valuation_calibration(q_over_neg)
            assert res_over_neg.valuation_corrected is True
            assert res_over_neg.gszzl == 0.0

    def test_adv_qdii_non_zero_benchmark_perturbation(self):
        """
        非零基准涨跌幅时的 1.5% 边界测试：
        基准为 -3.00%：
        - 基金估值 -1.50% (差值 abs(-1.50 - (-3.00)) = 1.50%) -> 不触发
        - 基金估值 -1.49% (差值 abs(-1.49 - (-3.00)) = 1.51%) -> 触发
        校准后由于是联接基金，结果为 round(-3.00 * 0.95, 2) = -2.85%
        """
        mock_bench = {"symbol": "sh513500", "change_pct": -3.00}

        # 差值刚好 1.50%
        with patch("AGY2_FundAdvisory.portfolio_manager.fetch_realtime_index_quote", return_value=mock_bench):
            q_exact = FundQuote(
                name="博时标普500ETF联接A",
                dwjz=2.0000,
                gsz=1.9700,
                gszzl=-1.50,
                gztime="14:30",
                fund_code="050025",
                valuation_corrected=False
            )
            out_exact = _apply_fund_valuation_calibration(q_exact)
            assert out_exact.valuation_corrected is False

        # 差值 1.51%
        with patch("AGY2_FundAdvisory.portfolio_manager.fetch_realtime_index_quote", return_value=mock_bench):
            q_over = FundQuote(
                name="博时标普500ETF联接A",
                dwjz=2.0000,
                gsz=1.9702,
                gszzl=-1.49,
                gztime="14:30",
                fund_code="050025",
                valuation_corrected=False
            )
            out_over = _apply_fund_valuation_calibration(q_over)
            assert out_over.valuation_corrected is True
            # -3.00 * 0.95 = -2.85
            assert out_over.gszzl == -2.85

    def test_adv_gold_feeder_fund_is_qdii_gold_contract(self):
        """
        验证 000216 华安易富黄金ETF联接A：
        纳入 is_qdii_or_gold 分支，受 1.5% 阈值保护，同时具备联接基金 0.95 仓位折算
        """
        mock_gold = {"symbol": "sh518880", "change_pct": 2.00}

        # 偏差 1.0% (<= 1.5%) -> 不纠偏
        with patch("AGY2_FundAdvisory.portfolio_manager.fetch_realtime_index_quote", return_value=mock_gold):
            q_gold_small_dev = FundQuote(
                name="华安易富黄金ETF联接A",
                dwjz=1.5000,
                gsz=1.5150,
                gszzl=1.00,
                gztime="14:30",
                fund_code="000216"
            )
            out_small = _apply_fund_valuation_calibration(q_gold_small_dev)
            assert out_small.valuation_corrected is False

        # 偏差 1.8% (> 1.5%) -> 触发纠偏，并按 0.95 折算: 2.00 * 0.95 = 1.90%
        with patch("AGY2_FundAdvisory.portfolio_manager.fetch_realtime_index_quote", return_value=mock_gold):
            q_gold_large_dev = FundQuote(
                name="华安易富黄金ETF联接A",
                dwjz=1.5000,
                gsz=1.5030,
                gszzl=0.20,
                gztime="14:30",
                fund_code="000216"
            )
            out_large = _apply_fund_valuation_calibration(q_gold_large_dev)
            assert out_large.valuation_corrected is True
            assert out_large.gszzl == 1.90


# =====================================================================
# Challenge Group 4: Bug 3 - Pure Bond Fund Exemption & Cache Invalidation
# =====================================================================

class TestBug3BondExemptionAndFailureModes:
    """
    Adversarial verification of Bond Exemption & Cache Resilience:
    - 002351 & other bond funds never trigger calibration
    - Network exception graceful degradation
    - Cache invalidation via clear_realtime_cache()
    """

    @pytest.mark.parametrize("bond_code,bond_name", [
        ("002351", "招商产业债A"),
        ("002352", "招商产业债C"),
        ("110008", "易方达稳健收益债券B"),
        ("001383", "易方达纯债债券A"),
        ("485111", "工银双利债券A"),
    ])
    def test_adv_pure_bond_funds_never_calibrated(self, bond_code: str, bond_name: str):
        """各类纯债与稳健固收基金绝不应被误判为指数或联接基金进行校准"""
        mock_any = {"symbol": "sh510300", "change_pct": 5.00}
        q_bond = FundQuote(
            name=bond_name,
            dwjz=1.3500,
            gsz=1.3503,
            gszzl=0.02,
            gztime="14:30",
            fund_code=bond_code,
            valuation_corrected=False
        )
        with patch("AGY2_FundAdvisory.portfolio_manager.fetch_realtime_index_quote", return_value=mock_any):
            out = _apply_fund_valuation_calibration(q_bond)
            assert out.valuation_corrected is False
            assert out.gszzl == 0.02
            assert out.gsz == 1.3503

    def test_adv_network_exception_graceful_recovery(self):
        """当底层实时行情接口抛出网络连接异常时，必须优雅降级返回原 quote，绝不让上游崩溃"""
        q = FundQuote(
            name="华夏科创50ETF联接A",
            dwjz=1.0000,
            gsz=1.0000,
            gszzl=0.0,
            gztime="14:30",
            fund_code="011613"
        )
        with patch("AGY2_FundAdvisory.portfolio_manager.fetch_realtime_index_quote", side_effect=ConnectionError("Gateway timeout")):
            out = _apply_fund_valuation_calibration(q)
            assert out.valuation_corrected is False
            assert out.gszzl == 0.0

    def test_adv_cache_invalidation_lifecycle(self):
        """验证 clear_realtime_cache 能够有效清理内存防抖缓存"""
        from AGY2_FundAdvisory.portfolio_manager import _REALTIME_QUOTE_CACHE
        # 预设缓存
        _REALTIME_QUOTE_CACHE["999999"] = (1000.0, MagicMock())
        assert "999999" in _REALTIME_QUOTE_CACHE
        # 执行清空
        clear_realtime_cache()
        assert len(_REALTIME_QUOTE_CACHE) == 0


# =====================================================================
# Challenge Group 5: Bug 4 - compute_portfolio_weighted_bias_and_erp
# =====================================================================

class TestBug4PortfolioWeightedBiasAndERP:
    """
    Adversarial verification of SmartExecutionDCAEngine.compute_portfolio_weighted_bias_and_erp:
    - Empty, None, and zero-weight allocations
    - Single asset (equity vs bond vs gold)
    - 50/50 mix mathematical correctness
    - Multi-asset convex combinations
    - Extreme positive / negative biases and strict clipping [10.0, 95.0]
    - Property-based testing over 1,000 randomized synthetic portfolios
    """

    def test_adv_empty_and_none_allocations(self):
        """测试空列表、None 以及空字典场景下的回退保证"""
        # 显式传入宏观快照
        snap = {"erp_percentile": 82.5, "c300_bias_20": -3.2}
        erp, bias = SmartExecutionDCAEngine.compute_portfolio_weighted_bias_and_erp([], snapshot=snap)
        assert erp == 82.5
        assert bias == -3.2

        # 传入 None allocations
        erp_none, bias_none = SmartExecutionDCAEngine.compute_portfolio_weighted_bias_and_erp(None, snapshot=snap)
        assert erp_none == 82.5
        assert bias_none == -3.2

        # 缺省快照
        erp_def, bias_def = SmartExecutionDCAEngine.compute_portfolio_weighted_bias_and_erp([])
        assert erp_def == 78.0
        assert bias_def == 0.0

    def test_adv_single_equity_asset(self):
        """
        单只权益资产：
        f_erp = np.clip(macro_erp - f_bias * 1.5, 10.0, 95.0)
        """
        alloc = [{"code": "011613", "name": "华夏科创50联接", "weight": 1.0, "bias_20": 4.0}]
        erp, bias = SmartExecutionDCAEngine.compute_portfolio_weighted_bias_and_erp(alloc, snapshot={"erp_percentile": 70.0})
        assert bias == 4.0
        # 70.0 - 4.0 * 1.5 = 64.0
        assert erp == 64.0

    def test_adv_single_defensive_assets(self):
        """
        防守标的（债券、固收、黄金、货币、裕祥）：
        无论自身 bias 如何，ERP 始终对齐宏观中性 ERP，消除伪超买超卖失真
        """
        defensive_names = ["招商产业债A", "易方达裕祥回报", "华安黄金联接A", "建信货币", "工银固收+"]
        for fn in defensive_names:
            alloc = [{"code": "000001", "name": fn, "weight": 0.8, "bias_20": 5.0}]
            erp, bias = SmartExecutionDCAEngine.compute_portfolio_weighted_bias_and_erp(alloc, snapshot={"erp_percentile": 75.0})
            assert erp == 75.0, f"{fn} 应严格对齐宏观中性 ERP 75.0"
            assert bias == 5.0

    def test_adv_50_50_mix_mathematics(self):
        """
        50/50 混合建仓篮子数学核查：
        50% 科技 (超买 bias=+6.0%) + 50% 红利低波 (超卖 bias=-4.0%)
        - 加权 bias = 0.5 * 6.0 + 0.5 * (-4.0) = +1.00%
        - 科技 ERP = clip(70 - 6.0*1.5, 10, 95) = 61.0%
        - 红利 ERP = clip(70 - (-4.0)*1.5, 10, 95) = 76.0%
        - 加权 ERP = 0.5 * 61.0 + 0.5 * 76.0 = 68.50%
        """
        alloc = [
            {"code": "011613", "name": "华夏科创50联接", "weight": 0.5, "bias_20": 6.0},
            {"code": "005561", "name": "易方达红利低波联接A", "weight": 0.5, "bias_20": -4.0},
        ]
        erp, bias = SmartExecutionDCAEngine.compute_portfolio_weighted_bias_and_erp(alloc, snapshot={"erp_percentile": 70.0})
        assert bias == 1.00
        assert erp == 68.50

    def test_adv_multi_asset_unnormalized_weights(self):
        """
        权重未归一化容错测试：
        用户传入任意比例（如 10, 20, 30, 40，和为 100），计算逻辑必须自动归一化
        """
        alloc = [
            {"code": "001", "name": "标的1", "weight": 20.0, "bias_20": 2.0},
            {"code": "002", "name": "标的2", "weight": 80.0, "bias_20": -3.0},
        ]
        # 归一化权重: 0.2 与 0.8
        # bias = 0.2 * 2.0 + 0.8 * (-3.0) = 0.4 - 2.4 = -2.00
        # erp: 标的1: 70 - 2.0*1.5 = 67; 标的2: 70 - (-3.0)*1.5 = 74.5
        # 加权 ERP: 0.2 * 67 + 0.8 * 74.5 = 13.4 + 59.6 = 73.00
        erp, bias = SmartExecutionDCAEngine.compute_portfolio_weighted_bias_and_erp(alloc, snapshot={"erp_percentile": 70.0})
        assert bias == -2.00
        assert erp == 73.00

    def test_adv_extreme_biases_strict_clipping(self):
        """
        极端乖离率与数值严格有界性断言：
        ERP 必须严格被夹在 [10.0, 95.0] 区间内，绝不允许下溢至负数或上溢超 100%
        """
        # 1. 极端狂热泡沫: bias = +100.0%
        alloc_bubble = [{"code": "001", "name": "泡沫资产", "weight": 1.0, "bias_20": 100.0}]
        erp_bubble, bias_bubble = SmartExecutionDCAEngine.compute_portfolio_weighted_bias_and_erp(
            alloc_bubble, snapshot={"erp_percentile": 70.0}
        )
        assert bias_bubble == 100.0
        # 70 - 100*1.5 = -80 -> clip 到 10.0
        assert erp_bubble == 10.0

        # 2. 极端恐慌砸盘黄金坑: bias = -100.0%
        alloc_panic = [{"code": "002", "name": "恐慌资产", "weight": 1.0, "bias_20": -100.0}]
        erp_panic, bias_panic = SmartExecutionDCAEngine.compute_portfolio_weighted_bias_and_erp(
            alloc_panic, snapshot={"erp_percentile": 70.0}
        )
        assert bias_panic == -100.0
        # 70 - (-100)*1.5 = 220 -> clip 到 95.0
        assert erp_panic == 95.0

    def test_adv_zero_total_weight_resilience(self):
        """异常输入防御：所有资产权重均为 0.0 时，total_w <= 0.0 机制启动，不抛 ZeroDivisionError"""
        alloc_zero = [
            {"code": "001", "name": "资产A", "weight": 0.0, "bias_20": 2.0},
            {"code": "002", "name": "资产B", "weight": 0.0, "bias_20": -2.0},
        ]
        erp, bias = SmartExecutionDCAEngine.compute_portfolio_weighted_bias_and_erp(alloc_zero, snapshot={"erp_percentile": 70.0})
        # 此时 w = 0.0 / 1.0 = 0.0，累计为 0.0
        assert bias == 0.0
        assert erp == 0.0

    def test_adv_missing_bias20_automatic_fallback(self):
        """当 allocation 字典中缺失 bias_20 键时，自动调用 get_fund_real_volatility_and_bias 反查"""
        alloc_no_bias = [
            {"code": "011613", "name": "华夏科创50联接", "weight": 1.0}
        ]
        with patch.object(SmartExecutionDCAEngine, "get_fund_real_volatility_and_bias", return_value={"bias_20": 3.5}) as mock_m:
            erp, bias = SmartExecutionDCAEngine.compute_portfolio_weighted_bias_and_erp(
                alloc_no_bias, snapshot={"erp_percentile": 70.0}
            )
            assert bias == 3.5
            # 70.0 - 3.5 * 1.5 = 64.75
            assert erp == 64.75
            mock_m.assert_called_once_with("011613", "华夏科创50联接")

    def test_adv_property_based_mathematical_bounding_stress_1000_runs(self):
        """
        【重要实证挑战】基于 1000 次蒙特卡洛随机资产组合的数学性质与有界性检验：
        1. 加权乖离率必须处于资产篮子最小与最大 bias 之间（凸组合性质）
        2. 加权 ERP 必须是有界的非 NaN、非 Inf，且在 [10.0, 95.0]（或包含中性防守资产时的有界闭区间内）
        """
        rng = random.Random(42)
        asset_names_pool = [
            ("011613", "科创50ETF联接"),
            ("005561", "红利低波联接A"),
            ("008888", "芯片ETF联接"),
            ("161725", "招商白酒指数"),
            ("002351", "招商产业债A"),
            ("000216", "华安黄金ETF联接"),
            ("110008", "易方达稳健固收"),
        ]

        for _ in range(1000):
            n_assets = rng.randint(1, 10)
            macro_erp = rng.uniform(20.0, 90.0)
            c300_bias = rng.uniform(-10.0, 10.0)

            chosen = rng.choices(asset_names_pool, k=n_assets)
            allocs = []
            biases = []
            for code, name in chosen:
                b = rng.uniform(-150.0, 150.0)
                w = rng.uniform(0.01, 100.0)
                allocs.append({"code": code, "name": name, "weight": w, "bias_20": b})
                biases.append(b)

            snap = {"erp_percentile": macro_erp, "c300_bias_20": c300_bias}
            erp_out, bias_out = SmartExecutionDCAEngine.compute_portfolio_weighted_bias_and_erp(allocs, snapshot=snap)

            # 1. 严格非空与非极端浮点
            assert not math.isnan(erp_out)
            assert not math.isinf(erp_out)
            assert not math.isnan(bias_out)
            assert not math.isinf(bias_out)

            # 2. 凸组合性质 (加权均值必处于最小与最大值之间，允许浮点公差 1e-2)
            min_b = min(biases)
            max_b = max(biases)
            assert min_b - 0.05 <= bias_out <= max_b + 0.05, f"bias {bias_out} 超出凸组合范围 [{min_b}, {max_b}]"

            # 3. ERP 严格边界控制
            # 防守标的取 macro_erp, 权益标的被 clip 到 [10.0, 95.0]
            min_possible_erp = min(10.0, macro_erp)
            max_possible_erp = max(95.0, macro_erp)
            assert min_possible_erp - 0.05 <= erp_out <= max_possible_erp + 0.05, (
                f"erp {erp_out} 超出边界 [{min_possible_erp}, {max_possible_erp}]"
            )
