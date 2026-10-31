"""
Adversarial Quantitative Stress Test Harness (Challenger Orch4-1)
Targeting:
- R2: Realtime Fund Limit Waterfall Order Splitting & DCA Overflow Precision
- R2: QDII Cross-Market Valuation Correction Exact Threshold & Idempotency
- R3: Dynamic Weights Full-Grid Monotonicity & Boundary Invariants (3,800+ Scenarios)
"""

import os
import sys
import copy
import math
import itertools
import pytest
import numpy as np
import pandas as pd
from pathlib import Path
from unittest.mock import patch, MagicMock

# 确保导入 AGY2_FundAdvisory 根目录模块
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from portfolio_manager import (
    PortfolioManager,
    FundQuote,
    fetch_realtime_fund_quota,
    fetch_realtime_fund_quote,
    _apply_qdii_valuation_correction,
    CORE_STRATEGY_POOL,
)
from strategy_bridge import StrategyBridge


EQUITY_ASSETS = {"100032", "005561", "011613", "001053", "016634", "013841", "007339", "050025", "001071"}
DEFENSIVE_ASSETS = {"002351", "000086", "018757", "000216", "000217"}


# =============================================================================
# 1. LIMIT & WATERFALL ORDER SPLITTING ADVERSARIAL STRESS TESTS
# =============================================================================
class TestWaterfallQuotaStress:
    """对抗极限压测：实时限额与多级瀑布流拆单算法"""

    @pytest.fixture
    def pm_instance(self, tmp_path):
        db_file = tmp_path / "test_adv_quota.db"
        json_file = tmp_path / "test_adv_quota.json"
        return PortfolioManager(db_path=db_file, ledger_json_path=json_file)

    def test_adv_quota_zero_primary_overflow(self, pm_instance):
        """
        极限场景 1：
        首选标的限额为 0 元 (暂停申购)，总资金 1,000,000 元。
        备选标的 1 限额 1,000 元，备选标的 2 限额 2,000 元，其余备选暂停申购 (0 元)。
        断言：
        1. 首选标的未被分配金额 (allocated_amount == 0，不进入 items)；
        2. 备选 1 严格分配 1,000 元，action_guide 包含 '单日限额¥1000·已拆单'；
        3. 备选 2 严格分配 2,000 元，action_guide 包含 '单日限额¥2000·已拆单'；
        4. 剩余资金精准进入 dca_plan，定投天数 >= 2；
        5. 分厘平账：allocated_sum + remaining_cash == total_capital；
        6. 各 items 分配金额之和精确等于 allocated_sum。
        """
        total_capital = 1_000_000.0

        def mock_quota_adversarial_1(fund_code, *args, **kwargs):
            code = str(fund_code).zfill(6)
            if code == "050025":  # 首选标普500
                return {"fund_code": code, "status": "暂停申购", "daily_limit": 0.0, "is_limited": True}
            elif code == "001071":  # 备选 1
                return {"fund_code": code, "status": "限制大额", "daily_limit": 1000.0, "is_limited": True}
            elif code == "006075":  # 备选 2
                return {"fund_code": code, "status": "限制大额", "daily_limit": 2000.0, "is_limited": True}
            elif code in ["017436", "017437"]:  # 其余备选
                return {"fund_code": code, "status": "暂停申购", "daily_limit": 0.0, "is_limited": True}
            # 其余非 QDII 基金正常开放
            return {"fund_code": code, "status": "开放申购", "daily_limit": 1e11, "is_limited": False}

        with patch("portfolio_manager.fetch_realtime_fund_quota", side_effect=mock_quota_adversarial_1):
            bp = pm_instance.generate_zero_start_blueprint(total_capital=total_capital, tier="C3")

            items = bp["items"]
            # 找到 QDII 赛道标的
            qdii_items = [it for it in items if it["fund_code"] in ["050025", "001071", "006075", "017436"]]

            # 050025 暂停申购，分配金额为 0，不应存在于有效买入 items 中
            assert not any(it["fund_code"] == "050025" for it in qdii_items), "暂停申购首选不应分配任何资金"

            # 备选 1: 001071
            it_001071 = next((it for it in qdii_items if it["fund_code"] == "001071"), None)
            assert it_001071 is not None, "备选 1 (001071) 应被拆单分配"
            assert it_001071["allocated_amount"] == 1000.0
            assert "1000" in it_001071["action_guide"]
            assert "已拆单" in it_001071["action_guide"]

            # 备选 2: 006075
            it_006075 = next((it for it in qdii_items if it["fund_code"] == "006075"), None)
            assert it_006075 is not None, "备选 2 (006075) 应被拆单分配"
            assert it_006075["allocated_amount"] == 2000.0
            assert "2000" in it_006075["action_guide"]
            assert "已拆单" in it_006075["action_guide"]

            # C3 标普500 目标比例为 6%，1,000,000 元总资金对应 60,000 元
            # 备选 1 分配 1,000，备选 2 分配 2,000，未分配金额应为 57,000 元
            expected_unallocated = 60000.0 - 3000.0
            assert "dca_plan" in bp, "必须生成 dca_plan"
            dca_str = bp["dca_plan"]
            assert str(int(expected_unallocated)) in dca_str, f"dca_plan 必须包含未分配额度 {int(expected_unallocated)}: {dca_str}"
            assert "QDII" in dca_str
            assert "定投" in dca_str

            # 分厘平账校验
            alloc_sum = bp["allocated_sum"]
            rem_cash = bp["remaining_cash"]
            assert round(alloc_sum + rem_cash, 2) == round(total_capital, 2), "资金总额分厘平账失败"
            items_sum = round(sum(it["allocated_amount"] for it in items), 2)
            assert items_sum == alloc_sum, f"items 累加 ({items_sum}) 与 allocated_sum ({alloc_sum}) 不一致"

    def test_adv_quota_tiny_primary_unconstrained_alt(self, pm_instance):
        """
        极限场景 2：
        首选标的限额极小 (10 元)，总资金 1,000,000 元。
        备选标的未限购 (1e11)。
        断言：
        1. 首选标的分配正好 10.0 元，action_guide 为 '单日限额¥10·已拆单'；
        2. 备选标的分配 59,990.0 元，action_guide 为 '承接超额·不限购正常买'；
        3. 两者合计正好 60,000.0 元；
        4. 无需生成 dca_plan (资金已被备选完全承接)；
        5. 分厘平账：allocated_sum + remaining_cash == total_capital。
        """
        total_capital = 1_000_000.0

        def mock_quota_adversarial_2(fund_code, *args, **kwargs):
            code = str(fund_code).zfill(6)
            if code == "050025":
                return {"fund_code": code, "status": "限制大额", "daily_limit": 10.0, "is_limited": True}
            elif code == "001071":
                return {"fund_code": code, "status": "开放申购", "daily_limit": 1e11, "is_limited": False}
            return {"fund_code": code, "status": "开放申购", "daily_limit": 1e11, "is_limited": False}

        with patch("portfolio_manager.fetch_realtime_fund_quota", side_effect=mock_quota_adversarial_2):
            bp = pm_instance.generate_zero_start_blueprint(total_capital=total_capital, tier="C3")
            items = bp["items"]

            it_prim = next((it for it in items if it["fund_code"] == "050025"), None)
            it_alt = next((it for it in items if it["fund_code"] == "001071"), None)

            assert it_prim is not None
            assert it_prim["allocated_amount"] == 10.0
            assert it_prim["action_guide"] == "单日限额¥10·已拆单"

            assert it_alt is not None
            assert it_alt["allocated_amount"] == 59990.0
            assert it_alt["action_guide"] == "承接超额·不限购正常买"

            assert round(it_prim["allocated_amount"] + it_alt["allocated_amount"], 2) == 60000.0
            assert "dca_plan" not in bp, "完全承接情况下不应出现 dca_plan"

            # 平账
            alloc_sum = bp["allocated_sum"]
            rem_cash = bp["remaining_cash"]
            assert round(alloc_sum + rem_cash, 2) == round(total_capital, 2)

    def test_adv_quota_all_alternatives_suspended(self, pm_instance):
        """
        极限场景 3：
        首选标的与所有备选标的全线暂停申购 (0 元)。
        总资金 1,000,000 元。
        断言：
        1. 该赛道买入金额为 0，没有任何标的进入 items；
        2. 全额 60,000 元进入 dca_plan，明确提示受全市场 QDII 限额约束；
        3. remaining_cash 准确等于 60,000 元 (其余 940,000 分配给其余正常资产)；
        4. allocated_sum + remaining_cash == total_capital 分厘平账。
        """
        total_capital = 1_000_000.0

        def mock_quota_adversarial_3(fund_code, *args, **kwargs):
            code = str(fund_code).zfill(6)
            if code in ["050025", "001071", "006075", "017436", "017437"]:
                return {"fund_code": code, "status": "暂停申购", "daily_limit": 0.0, "is_limited": True}
            return {"fund_code": code, "status": "开放申购", "daily_limit": 1e11, "is_limited": False}

        with patch("portfolio_manager.fetch_realtime_fund_quota", side_effect=mock_quota_adversarial_3):
            bp = pm_instance.generate_zero_start_blueprint(total_capital=total_capital, tier="C3")
            items = bp["items"]

            qdii_items = [it for it in items if it["fund_code"] in ["050025", "001071", "006075", "017436", "017437"]]
            assert len(qdii_items) == 0, "全线暂停申购时不应有 QDII 标的产生分配"

            assert "dca_plan" in bp
            assert "60000" in bp["dca_plan"]
            assert bp["remaining_cash"] == 60000.0
            assert bp["allocated_sum"] == 940000.0
            assert round(bp["allocated_sum"] + bp["remaining_cash"], 2) == total_capital

    @pytest.mark.parametrize("cap", [100.0, 1000.0, 10000.0, 100000.0, 1000000.0, 10000000.0, 100000000.0])
    def test_adv_quota_capital_scale_invariance_and_penny_reconciliation(self, pm_instance, cap):
        """
        极限场景 4：
        跨 7 个数量级资本规模 (100元 ~ 1亿元) 的分厘平账不变性与无负数/无 NaN 校验。
        """
        def mock_quota_sweep(fund_code, *args, **kwargs):
            code = str(fund_code).zfill(6)
            if code == "050025":
                return {"fund_code": code, "status": "限制大额", "daily_limit": 500.0, "is_limited": True}
            elif code == "001071":
                return {"fund_code": code, "status": "限制大额", "daily_limit": 1000.0, "is_limited": True}
            return {"fund_code": code, "status": "开放申购", "daily_limit": 1e11, "is_limited": False}

        with patch("portfolio_manager.fetch_realtime_fund_quota", side_effect=mock_quota_sweep):
            bp = pm_instance.generate_zero_start_blueprint(total_capital=cap, tier="C3")
            items = bp["items"]

            for it in items:
                assert it["allocated_amount"] >= 0.0, "分配金额不可为负"
                assert not math.isnan(it["allocated_amount"]), "分配金额不可为 NaN"
                assert not math.isinf(it["allocated_amount"]), "分配金额不可为 Inf"

            alloc_sum = bp["allocated_sum"]
            rem_cash = bp["remaining_cash"]
            assert round(alloc_sum + rem_cash, 2) == round(cap, 2), f"资本 {cap} 平账失败"
            items_sum = round(sum(it["allocated_amount"] for it in items), 2)
            assert items_sum == alloc_sum


# =============================================================================
# 2. QDII VALUATION CORRECTION ADVERSARIAL STRESS TESTS
# =============================================================================
class TestQdiiValuationAdversarial:
    """对抗极限压测：QDII 估值纠偏阈值精确性与幂等性"""

    @pytest.mark.parametrize("benchmark_change", [0.0, 1.0, 2.0])
    def test_adv_qdii_deviation_canonical_sequence(self, benchmark_change):
        """
        精确对齐原始任务需求中的偏离序列：
        构造偏离序列: -5.0%, -1.6%, -1.5%, 0.0%, +1.4%, +1.5%, +3.0%
        断言：
        - 绝对偏差 <= 1.5% 时 (-1.5%, 0.0%, +1.4%, +1.5%)，严格不执行纠偏，valuation_corrected == False，gsz 和 gszzl 保持原值；
        - 绝对偏差 > 1.5% 时 (-5.0%, -1.6%, +3.0%)，精准执行 benchmark_change * 0.95 覆盖纠偏并重新计算 gsz，valuation_corrected == True。
        """
        deviations = [
            (-5.0, True),   # abs(-5.0) = 5.0 > 1.5 -> Trigger
            (-1.6, True),   # abs(-1.6) = 1.6 > 1.5 -> Trigger
            (-1.5, False),  # abs(-1.5) = 1.5 <= 1.5 -> NO Trigger
            (0.0, False),   # abs(0.0) = 0.0 <= 1.5 -> NO Trigger
            (+1.4, False),  # abs(1.4) = 1.4 <= 1.5 -> NO Trigger
            (+1.5, False),  # abs(1.5) = 1.5 <= 1.5 -> NO Trigger
            (+3.0, True),   # abs(3.0) = 3.0 > 1.5 -> Trigger
        ]

        dwjz = 2.0000
        mock_bench_quote = {"symbol": "sh513500", "change_pct": benchmark_change, "price": 1.50}

        for dev, expected_trigger in deviations:
            fund_gszzl = round(benchmark_change + dev, 4)
            initial_gsz = round(dwjz * (1.0 + fund_gszzl / 100.0), 4)

            q_in = FundQuote(
                name="博时标普500ETF联接A",
                dwjz=dwjz,
                gsz=initial_gsz,
                gszzl=fund_gszzl,
                gztime="2026-10-31 14:30",
                fund_code="050025",
                valuation_corrected=False
            )

            with patch("portfolio_manager.fetch_realtime_index_quote", return_value=mock_bench_quote):
                q_out = _apply_qdii_valuation_correction(q_in)

                if expected_trigger:
                    assert q_out.valuation_corrected is True, f"偏差 {dev}% 应触发纠偏但未触发"
                    expected_gszzl = round(benchmark_change * 0.95, 2)
                    expected_gsz = round(dwjz * (1.0 + expected_gszzl / 100.0), 4)
                    assert q_out.gszzl == expected_gszzl, f"纠偏后涨跌幅错误: 预期 {expected_gszzl}, 实际 {q_out.gszzl}"
                    assert q_out.gsz == expected_gsz, f"纠偏后净值错误: 预期 {expected_gsz}, 实际 {q_out.gsz}"
                    assert "基准纠偏" in q_out.gztime
                else:
                    assert q_out.valuation_corrected is False, f"偏差 {dev}% 不应触发纠偏但被触发了"
                    assert q_out.gszzl == fund_gszzl
                    assert q_out.gsz == initial_gsz
                    assert "基准纠偏" not in q_out.gztime

    def test_adv_qdii_micro_boundary_perturbation(self):
        """
        微扰边界对抗测试：
        在基准涨跌幅为 0.0 时：
        偏差 1.5000% 不触发；
        偏差 1.5001% 严格触发。
        """
        benchmark_change = 0.0
        dwjz = 2.0000
        mock_bench_quote = {"symbol": "sh513500", "change_pct": benchmark_change, "price": 1.50}

        with patch("portfolio_manager.fetch_realtime_index_quote", return_value=mock_bench_quote):
            # 刚好 1.5%
            q_boundary_exact = FundQuote(
                name="博时标普500ETF联接A",
                dwjz=dwjz,
                gsz=2.0300,
                gszzl=1.5,
                gztime="2026-10-31 14:30",
                fund_code="050025",
                valuation_corrected=False
            )
            res_exact = _apply_qdii_valuation_correction(q_boundary_exact)
            assert res_exact.valuation_corrected is False

            # 大于 1.5%
            q_boundary_over = FundQuote(
                name="博时标普500ETF联接A",
                dwjz=dwjz,
                gsz=2.0301,
                gszzl=1.5001,
                gztime="2026-10-31 14:30",
                fund_code="050025",
                valuation_corrected=False
            )
            res_over = _apply_qdii_valuation_correction(q_boundary_over)
            assert res_over.valuation_corrected is True

    def test_adv_qdii_ieee754_boundary_finding(self):
        """
        【重要实证挑战发现】IEEE-754 二进制浮点微漂移实证：
        当基准为 -3.2，基金为 -1.7 时，数学名义差为 1.50，但 Python 二进制浮点算式:
        abs(-1.7 - (-3.2)) == 1.5000000000000002 > 1.5 为 True。
        断言底层算子在此类浮点微漂移下的真实执行行为，并记录为实证报告 Caveat。
        """
        b_change = -3.2
        fund_gszzl = -1.7
        float_diff = abs(fund_gszzl - b_change)
        assert float_diff > 1.5, "证实 IEEE-754 存在 2e-16 微漂移"

        mock_bench = {"symbol": "sh513500", "change_pct": b_change, "price": 1.50}
        with patch("portfolio_manager.fetch_realtime_index_quote", return_value=mock_bench):
            q = FundQuote(
                name="博时标普500ETF联接A",
                dwjz=2.0000,
                gsz=1.9660,
                gszzl=fund_gszzl,
                gztime="2026-10-31 14:30",
                fund_code="050025",
                valuation_corrected=False
            )
            res = _apply_qdii_valuation_correction(q)
            # 实证证实：底层直接使用 abs(q.gszzl - b_change) > 1.5，因浮点微漂移为 1.5000000000000002，判定为 True
            assert res.valuation_corrected is True
            assert res.gszzl == round(-3.2 * 0.95, 2)

    def test_adv_qdii_correction_idempotency(self):
        """
        纠偏幂等性测试：
        已被标记 valuation_corrected == True 的对象，二次调用严禁重复 * 0.95。
        """
        q_corrected = FundQuote(
            name="博时标普500ETF联接A",
            dwjz=2.0000,
            gsz=2.0190,
            gszzl=0.95,
            gztime="2026-10-31 14:30 (基准纠偏: sh513500 +1.00%)",
            fund_code="050025",
            valuation_corrected=True
        )
        res = _apply_qdii_valuation_correction(q_corrected)
        assert res.valuation_corrected is True
        assert res.gszzl == 0.95
        assert res.gsz == 2.0190

    def test_adv_non_qdii_unaffected(self):
        """
        非 QDII 标的 (如纯债 002351, 红利 100032) 不受 QDII 纠偏影响。
        """
        q_bond = FundQuote(
            name="招商产业债A",
            dwjz=1.5000,
            gsz=1.5000,
            gszzl=-5.0,  # 异常偏离
            gztime="2026-10-31 14:30",
            fund_code="002351",
            valuation_corrected=False
        )
        res = _apply_qdii_valuation_correction(q_bond)
        assert res.valuation_corrected is False
        assert res.gszzl == -5.0


# =============================================================================
# 3. DYNAMIC WEIGHTS FULL-GRID MONOTONICITY ADVERSARIAL STRESS TESTS
# =============================================================================
def _generate_extreme_grid_scenarios():
    """
    生成覆盖 3,840 组极端市场指标组合：
    1. 市场宏观环境 regime: [BULL, OSCILLATING, BEAR, None]
    2. ERP 极端分位数: [0.0, 15.0, 50.0, 75.0, 95.0]
    3. 20日均线乖离率 bias_20: [-15.0, -5.0, -4.5, -1.0, 0.0, 1.0, 6.5, 12.0]
    4. 拥挤度警报 crowding_warning: [False, True]
    5. 动量专家权重 p_mom: [0.05, 0.25, 0.55, 0.95]
    6. 波动率水平 c300_annualized_vol: [0.08, 0.18, 0.50]
    """
    regimes = ["BULL", "OSCILLATING", "BEAR", None]
    erp_list = [0.0, 15.0, 50.0, 75.0, 95.0]
    bias_list = [-15.0, -5.0, -4.5, -1.0, 0.0, 1.0, 6.5, 12.0]
    crowding_list = [False, True]
    p_mom_list = [0.05, 0.25, 0.55, 0.95]
    vol_list = [0.08, 0.18, 0.50]

    scenarios = []
    for r, erp, bias, crowd, pmom, vol in itertools.product(
        regimes, erp_list, bias_list, crowding_list, p_mom_list, vol_list
    ):
        snap = {
            "regime": r,
            "erp_percentile": erp,
            "bias_20": bias,
            "bias_20_star": bias - 1.0,
            "crowding_warning": crowd,
            "c300_annualized_vol": vol,
            "expert_weights": {
                "trend_momentum": pmom,
                "erp_macro": (1.0 - pmom) / 3.0,
                "ma_contrarian": (1.0 - pmom) / 3.0,
                "liquidity_basis": (1.0 - pmom) / 3.0,
            }
        }
        if r:
            snap["market_state_code"] = "GROWTH_BULL" if r == "BULL" else ("SEVERE_BEAR" if r == "BEAR" else "OSCILLATING")
        scenarios.append(snap)
    return scenarios


_CACHED_SCENARIOS = _generate_extreme_grid_scenarios()


class TestDynamicWeightsFullGridMonotonicity:
    """对抗极限压测：3,800+ 极端行情参数网格单调性与数学鲁棒性"""

    @pytest.fixture
    def grid_scenarios(self):
        return _CACHED_SCENARIOS

    def test_adv_grid_size(self, grid_scenarios):
        """断言网格规模严格 >= 1000 组 (当前生成 3,840 组)"""
        assert len(grid_scenarios) >= 1000, f"网格样本量不足 1000 组: {len(grid_scenarios)}"

    def test_adv_full_grid_strict_monotonicity_and_invariants(self, grid_scenarios):
        """
        核心全域网格单调性对抗测试：
        遍历全部 3,840 组极端市场指标组合，逐一计算 C1 至 C5 动态权重并断言：
        1. 严格单调性：Equity(C1) < Equity(C2) < Equity(C3) < Equity(C4) < Equity(C5) 恒成立；
        2. 权重归一化：全档位 sum(w_i) == 1.0 (容差 1e-4)；
        3. 非负性与数值安全：无任何 NaN、无 Inf、无负数权重；
        4. 熊市硬约束边界：在 BEAR 态下，Equity(C4) <= 55%, Equity(C5) <= 70%。
        """
        tiers = ["C1", "C2", "C3", "C4", "C5"]
        failures = []

        for idx, snap in enumerate(grid_scenarios):
            tier_weights = {}
            tier_equities = {}

            for t in tiers:
                try:
                    w = StrategyBridge.compute_dynamic_tier_weights(tier=t, market_snapshot=snap)
                    tier_weights[t] = w
                    # 归一化与数值安全断言
                    total_w = sum(w.values())
                    if abs(total_w - 1.0) > 1e-4:
                        failures.append(f"[Scenario {idx} Tier {t}] Sum of weights != 1.0: {total_w}")
                    for k, v in w.items():
                        if math.isnan(v):
                            failures.append(f"[Scenario {idx} Tier {t} Fund {k}] Weight is NaN")
                        if math.isinf(v):
                            failures.append(f"[Scenario {idx} Tier {t} Fund {k}] Weight is Inf")
                        if v < -1e-6:
                            failures.append(f"[Scenario {idx} Tier {t} Fund {k}] Negative weight: {v}")

                    # 计算权益资产占比
                    eq_sum = sum(w.get(a, 0.0) for a in EQUITY_ASSETS)
                    tier_equities[t] = round(eq_sum, 4)

                except Exception as e:
                    failures.append(f"[Scenario {idx} Tier {t}] Exception raised: {e}")

            # 校验严格单调性: Equity(C1) < Equity(C2) < Equity(C3) < Equity(C4) < Equity(C5)
            e1 = tier_equities.get("C1", 0.0)
            e2 = tier_equities.get("C2", 0.0)
            e3 = tier_equities.get("C3", 0.0)
            e4 = tier_equities.get("C4", 0.0)
            e5 = tier_equities.get("C5", 0.0)

            if not (e1 < e2 < e3 < e4 < e5):
                failures.append(
                    f"[Scenario {idx} Monotonicity Violation] "
                    f"Regime={snap.get('regime')} ERP={snap.get('erp_percentile')} Bias={snap.get('bias_20')} -> "
                    f"C1={e1}, C2={e2}, C3={e3}, C4={e4}, C5={e5}"
                )

            # 熊市硬约束检查
            if snap.get("regime") == "BEAR":
                if e4 > 0.5501:
                    failures.append(f"[Scenario {idx} Bear Bound Violation] Equity(C4) = {e4} > 55%")
                if e5 > 0.7001:
                    failures.append(f"[Scenario {idx} Bear Bound Violation] Equity(C5) = {e5} > 70%")

        assert len(failures) == 0, f"发现 {len(failures)} 处对抗违规项！前 10 项:\n" + "\n".join(failures[:10])

    def test_adv_c3_dynamic_evolution_adversarial(self, grid_scenarios):
        """
        拔除静态常数劫持对抗断言：
        遍历网格断言 C3 权重在全域绝非恒等于静态常数 (0.38, 0.30, 0.14, 0.12, 0.06)，
        且随专家动量因子与波动率发生动态位移。
        """
        hijacked_tuple = (0.38, 0.30, 0.14, 0.12, 0.06)
        distinct_c3_weights = set()

        for snap in grid_scenarios[:200]:  # 取前 200 组切片
            w_c3 = StrategyBridge.compute_dynamic_tier_weights(tier="C3", market_snapshot=snap)
            c3_vals = (
                w_c3.get("100032", 0.0),
                w_c3.get("005561", 0.0),
                w_c3.get("000216", 0.0),
                w_c3.get("002351", 0.0),
                w_c3.get("050025", 0.0)
            )
            distinct_c3_weights.add(c3_vals)
            # 在非震荡默认态下绝不等于写死的常数
            if snap.get("regime") in ["BULL", "BEAR"]:
                assert c3_vals != hijacked_tuple, f"在 {snap.get('regime')} 态下 C3 被静态常数劫持！"

        # 断言 C3 在网格中呈现多样化动态配置形态
        assert len(distinct_c3_weights) >= 10, f"C3 动态分布过于僵死: 仅有 {len(distinct_c3_weights)} 种形态"
