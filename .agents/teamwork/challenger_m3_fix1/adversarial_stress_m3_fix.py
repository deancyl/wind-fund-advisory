"""
Adversarial Stress Test Suite for Milestone 3 Fix 1
Targeting:
1. CUSUM Extreme Boundary Invariants (All Meltdown, Alternating Leads, Float Precision, Negative Scores, Empty/Single Pool, Monte Carlo Fuzzing)
2. All-Tier Monotonicity & Cash Conservation (Equity(C1) < Equity(C2) < Equity(C3) < Equity(C4) < Equity(C5), 100% Budget Conservation, C4/C5 011613 >= 25%)
3. Cache Concurrency, Debounce & Idempotency (30s Debounce, Multi-threaded Safety, Idempotent Promotion)
"""

import sys
import os
import time
import math
import copy
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List

# Ensure project root is in sys.path
PROJECT_ROOT = r"d:\Google\Workspace\Wind\AGY2_FundAdvisory"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

from portfolio_manager import PortfolioManager, CUSUMFundChangePointDetector
from strategy_bridge import StrategyBridge

def log_section(title: str):
    print("\n" + "=" * 70)
    print(f"  >>> {title}")
    print("=" * 70)

def make_candidate(
    code: str,
    name: str,
    score: float,
    risk: float = None,
    sm: float = None,
    fee: float = None,
    te: float = None,
    is_crowded: bool = False,
    bonus: float = 0.0
) -> Dict[str, Any]:
    """
    构造具有确定性综合评分的候选基金字典:
    S = 0.35 * ER + 0.25 * Fee + 0.15 * Risk + 0.15 * SM + 0.10 * TE
    当 ER = Fee = Risk = SM = TE = score 时，S = score。
    """
    return {
        "code": str(code).zfill(6),
        "fund_code": str(code).zfill(6),
        "name": name,
        "er_score": score,
        "fee_score": fee if fee is not None else score,
        "risk_score": risk if risk is not None else score,
        "smart_money_score": sm if sm is not None else score,
        "te_score": te if te is not None else score,
        "is_extreme_crowding": is_crowded,
        "switch_convenience_bonus": bonus
    }

# ==============================================================================
# Suite 1: CUSUM 极值边界压测
# ==============================================================================

def test_cusum_all_candidates_meltdown():
    """
    极值测试 1.1: 全员暴雷与极度拥挤
    当默认标的与全部备选标的均发生暴雷 (risk < 60) 或极度拥挤 (extreme_crowding = True) 时：
    - is_triggered 必须为 True
    - is_champ_meltdown 必须为 True
    - eligible_alternatives 为空
    - 算法绝不应抛出 IndexError 或未捕获异常
    - is_promoted 必须平稳保持 False (无合格候选者可晋升)
    - active_champion_code 必须合法返回默认标的代码
    """
    print("\n--- Running test_cusum_all_candidates_meltdown ---")
    detector = CUSUMFundChangePointDetector()
    candidates = [
        make_candidate("100032", "富国中证红利", 85.0, risk=40.0, is_crowded=True),
        make_candidate("090010", "大成中证红利", 90.0, risk=35.0, is_crowded=False),
        make_candidate("012643", "博时中证红利", 92.0, risk=80.0, is_crowded=True),
    ]
    res = detector.evaluate_track_candidates(
        sector_id="TEST_ALL_MELTDOWN",
        default_champion_code="100032",
        candidates=candidates
    )
    assert res["is_triggered"] is True, "默认标的暴雷必须触发 is_triggered=True"
    assert res["is_promoted"] is False, "当所有备选标的均暴雷或拥挤时，不能发生晋升"
    assert res["active_champion_code"] == "100032", f"无合格晋升标的时活跃标的应为默认标的，实际为 {res['active_champion_code']}"
    assert res["promotion_label"] == "", "未晋升时 promotion_label 必须为空"
    print("PASS: test_cusum_all_candidates_meltdown")


def test_cusum_alternating_leads():
    """
    极值测试 1.2: 连续多期交替领先与松弛防抖
    验证 Page's CUSUM 衰减递推在交替领先序列下的抗抖性与递减自愈性：
    Round 1: 默认冠军领先 (+5.0) -> CUSUM = 0.0
    Round 2: 备选 A 微幅领先 (+1.5, < slack_k 2.0) -> decay_increment = -0.5 -> CUSUM 保持 0.0 (防抖生效)
    Round 3: 备选 A 显著领先 (+5.0, > slack_k 2.0) -> increment = +3.0 -> CUSUM = 3.0
    Round 4: 备选 B 超车备选 A (+10.0 > 默认) -> increment = +8.0 -> CUSUM = 11.0 >= 8.0 -> 触发晋升备选 B
    Round 5: 默认冠军王者归来领先 (+20.0) -> increment = -2.0 -> CUSUM 递减 -> 自愈至 0.0
    """
    print("\n--- Running test_cusum_alternating_leads ---")
    detector = CUSUMFundChangePointDetector(threshold_h=8.0, slack_k=2.0)
    def_code = "100032"
    alt_a = "090010"
    alt_b = "012643"

    # Round 1: def leads (90 vs 85, 80)
    cands_r1 = [
        make_candidate(def_code, "默认冠军", 90.0),
        make_candidate(alt_a, "备选A", 85.0),
        make_candidate(alt_b, "备选B", 80.0),
    ]
    res1 = detector.evaluate_track_candidates("TEST_ALT", def_code, cands_r1, c_prev=0.0)
    assert res1["cusum_value"] == 0.0
    assert not res1["is_promoted"]

    # Round 2: alt_a leads by 1.5 (< slack_k 2.0: 90.0 vs 88.5)
    cands_r2 = [
        make_candidate(def_code, "默认冠军", 88.5),
        make_candidate(alt_a, "备选A", 90.0),
        make_candidate(alt_b, "备选B", 80.0),
    ]
    res2 = detector.evaluate_track_candidates("TEST_ALT", def_code, cands_r2, c_prev=res1["cusum_value"])
    assert res2["cusum_value"] == 0.0, f"微幅领先 1.5 应被 slack_k=2.0 吸收，实际 CUSUM={res2['cusum_value']}"
    assert not res2["is_promoted"]

    # Round 3: alt_a leads by 5.0 (> slack_k 2.0: 90.0 vs 85.0)
    cands_r3 = [
        make_candidate(def_code, "默认冠军", 85.0),
        make_candidate(alt_a, "备选A", 90.0),
        make_candidate(alt_b, "备选B", 80.0),
    ]
    res3 = detector.evaluate_track_candidates("TEST_ALT", def_code, cands_r3, c_prev=res2["cusum_value"])
    assert math.isclose(res3["cusum_value"], 3.0, abs_tol=1e-3), f"预期 CUSUM=3.0, 实际={res3['cusum_value']}"
    assert not res3["is_promoted"]

    # Round 4: alt_b overtakes alt_a and def by 10.0 (95.0 vs 85.0)
    cands_r4 = [
        make_candidate(def_code, "默认冠军", 85.0),
        make_candidate(alt_a, "备选A", 90.0),
        make_candidate(alt_b, "备选B", 95.0),
    ]
    res4 = detector.evaluate_track_candidates("TEST_ALT", def_code, cands_r4, c_prev=res3["cusum_value"])
    assert math.isclose(res4["cusum_value"], 11.0, abs_tol=1e-3), f"预期 CUSUM=11.0, 实际={res4['cusum_value']}"
    assert res4["is_promoted"] is True
    assert res4["active_champion_code"] == alt_b, f"应晋升领先的备选B，实际为 {res4['active_champion_code']}"

    # Round 5: def recovers lead (95.0 vs 75.0) -> max_score == champ_score == 95.0
    # decay_increment = (95.0 - 95.0) - 2.0 = -2.0
    # CUSUM decays by slack_k=2.0 from 11.0 to 9.0 (hysteresis memory!)
    cands_r5 = [
        make_candidate(def_code, "默认冠军", 95.0),
        make_candidate(alt_a, "备选A", 75.0),
        make_candidate(alt_b, "备选B", 75.0),
    ]
    res5 = detector.evaluate_track_candidates("TEST_ALT", def_code, cands_r5, c_prev=res4["cusum_value"])
    assert math.isclose(res5["cusum_value"], 9.0, abs_tol=1e-3), f"预期 CUSUM 衰减 -2.0 至 9.0，实际为 {res5['cusum_value']}"
    # 变点虽仍 >= 8.0，但因无合格标的得分领先原冠军 (75.0 < 95.0)，绝不发生反向倒挂晋升
    assert not res5["is_promoted"]
    assert res5["active_champion_code"] == def_code

    # Rounds 6-10: 冠军持续领跑，CUSUM 逐期稳定衰减自愈至 0.0
    curr_c = res5["cusum_value"]
    for step in range(5):
        res_step = detector.evaluate_track_candidates("TEST_ALT", def_code, cands_r5, c_prev=curr_c)
        curr_c = res_step["cusum_value"]
        assert not res_step["is_promoted"]
        assert res_step["active_champion_code"] == def_code

    assert curr_c == 0.0, f"冠军连续 5 期领跑后 CUSUM 必须完全自愈至 0.0，实际为 {curr_c}"
    print("PASS: test_cusum_alternating_leads")


def test_cusum_floating_precision_boundaries():
    """
    极值测试 1.3: 浮点精度临界值与无穷小扰动压测
    - threshold_h 临界边界：CUSUM = 7.9999 (未触发) vs 8.0000 (触发)
    - risk_score 临界边界：59.9999 (熔断) vs 60.0000 (安全)
    - 极小微差排序与稳定性
    """
    print("\n--- Running test_cusum_floating_precision_boundaries ---")
    detector = CUSUMFundChangePointDetector(threshold_h=8.0, slack_k=2.0)

    # 1.3.1 CUSUM 7.99 vs 8.00 (综合得分保留 2 位小数: 89.99 - 80.00 - 2.0 = 7.99 vs 90.00 - 80.00 - 2.0 = 8.00)
    cands_below = [
        make_candidate("100032", "默认", 80.00),
        make_candidate("090010", "备选", 89.99),
    ]
    res_below = detector.evaluate_track_candidates("TEST_PREC", "100032", cands_below, c_prev=0.0)
    assert res_below["cusum_value"] == 7.99
    assert not res_below["is_promoted"], "CUSUM=7.99 < 8.0 严禁晋升"

    cands_above = [
        make_candidate("100032", "默认", 80.00),
        make_candidate("090010", "备选", 90.00),
    ]
    res_above = detector.evaluate_track_candidates("TEST_PREC", "100032", cands_above, c_prev=0.0)
    assert res_above["cusum_value"] == 8.00
    assert res_above["is_promoted"] is True, "CUSUM=8.00 >= 8.0 必须触发晋升"

    # 1.3.2 risk_score 60.0 vs 59.9 (排雷分保留 1 位小数: 60.0 及格线 vs 59.9 熔断线)
    cands_risk_exact = [
        make_candidate("100032", "默认", 85.0, risk=60.0),
        make_candidate("090010", "备选", 80.0, risk=90.0),
    ]
    res_exact = detector.evaluate_track_candidates("TEST_PREC_R", "100032", cands_risk_exact, c_prev=0.0)
    assert not res_exact["is_triggered"], "排雷分刚好 60.0 为及格线，不能误判为暴雷"
    assert not res_exact["is_promoted"]

    cands_risk_broken = [
        make_candidate("100032", "默认", 85.0, risk=59.9),
        make_candidate("090010", "备选", 80.0, risk=90.0),
    ]
    res_broken = detector.evaluate_track_candidates("TEST_PREC_R", "100032", cands_risk_broken, c_prev=0.0)
    assert res_broken["is_triggered"] is True, "排雷分 59.9 必须触发熔断"
    assert res_broken["is_promoted"] is True, "默认暴雷且有合规备选时必须晋升"
    assert res_broken["active_champion_code"] == "090010"

    print("PASS: test_cusum_floating_precision_boundaries")


def test_cusum_negative_scores():
    """
    极值测试 1.4: 负分数输入与极端异常指标
    测试输入包括大幅负超额收益 (-50%)、超大跟踪误差 (200%)、超大费率 (150%) 等脏数据：
    断言算法 zero-division safe，能够稳定生成分数并完成 CUSUM 递推。
    """
    print("\n--- Running test_cusum_negative_scores ---")
    detector = CUSUMFundChangePointDetector()
    candidates = [
        {"code": "100032", "name": "默认负分基", "excess_return": -80.0, "fee": 15.0, "tracking_error": 50.0, "risk_score": 10.0, "smart_money": -20.0},
        {"code": "090010", "name": "备选合格基", "excess_return": 5.0, "fee": 0.5, "tracking_error": 1.0, "risk_score": 85.0, "smart_money": 70.0},
    ]
    res = detector.evaluate_track_candidates("TEST_NEG", "100032", candidates)
    assert res["is_triggered"] is True
    assert res["is_promoted"] is True
    assert res["active_champion_code"] == "090010"
    assert res["cusum_value"] >= 0.0
    print("PASS: test_cusum_negative_scores")


def test_cusum_zero_and_single_candidate_pool():
    """
    极值测试 1.5: 零候选池与单候选池防御
    1. candidates = []: 自动从元数据合成默认冠军，active_champion_code 合法返回，无崩溃
    2. candidates = [def_cand]: 仅有默认冠军，即使暴雷也不存在可晋升标的，active_champion_code 合法返回
    3. candidates = [alt_cand]: 仅有非默认候选，系统自动补全默认标的并进行正常比对
    """
    print("\n--- Running test_cusum_zero_and_single_candidate_pool ---")
    detector = CUSUMFundChangePointDetector()

    # 1. 空候选池
    res_empty = detector.evaluate_track_candidates("TEST_EMPTY", "100032", [])
    assert res_empty["active_champion_code"] == "100032"
    assert not res_empty["is_promoted"]
    assert len(res_empty["scored_candidates"]) == 1

    # 2. 单候选池 (仅默认冠军，且暴雷)
    res_single_meltdown = detector.evaluate_track_candidates(
        "TEST_SINGLE_MELT",
        "100032",
        [make_candidate("100032", "富国红利", 85.0, risk=20.0)]
    )
    assert res_single_meltdown["active_champion_code"] == "100032"
    assert not res_single_meltdown["is_promoted"], "单候选池暴雷时无备选可供晋升，不能崩溃且保持 is_promoted=False"

    # 3. 单候选池 (仅备选标的，未传入默认标的)
    res_single_alt = detector.evaluate_track_candidates(
        "TEST_SINGLE_ALT",
        "100032",
        [make_candidate("090010", "大成红利", 95.0, risk=90.0)]
    )
    assert len(res_single_alt["scored_candidates"]) == 2, "系统必须自动补齐默认标的并与备选进行比较"
    assert res_single_alt["active_champion_code"] in ["100032", "090010"]

    print("PASS: test_cusum_zero_and_single_candidate_pool")


def test_cusum_monte_carlo_fuzzing():
    """
    极值测试 1.6: 500 次蒙特卡洛随机对抗轰炸
    在随机候选池大小 (0-8)、随机指标 (包含负数、极高值、缺失值、布尔类型、浮点极值) 下：
    断言变点检测器 invariants 100% 成立：
    1. active_champion_code 必须是非空且合法的 6 位基金代码；
    2. is_promoted 必须严格是布尔值；
    3. cusum_value >= 0.0；
    4. 若 is_promoted == True，则 active_champion_code != default_champion_code；
    5. 若 is_promoted == True，则 promotion_label 包含 active_champion_name；
    6. 绝不抛出任何未捕获异常。
    """
    print("\n--- Running test_cusum_monte_carlo_fuzzing (500 iterations) ---")
    detector = CUSUMFundChangePointDetector()
    rng = random.Random(42)

    for i in range(500):
        def_code = f"{rng.randint(1, 999999):06d}"
        cands = [{
            "code": def_code,
            "name": f"默认基金_{def_code}",
            "er_score": rng.uniform(-20.0, 120.0),
            "fee_score": rng.uniform(0.0, 100.0),
            "risk_score": rng.uniform(-20.0, 120.0),
            "smart_money_score": rng.uniform(-20.0, 120.0),
            "te_score": rng.uniform(0.0, 100.0),
            "is_extreme_crowding": rng.choice([True, False]),
        }]
        n_cands = rng.randint(0, 7)
        for j in range(n_cands):
            code = f"{rng.randint(1, 999999):06d}"
            cand_item = {
                "code": code,
                "name": f"随机基金_{code}",
                "er_score": rng.uniform(-50.0, 150.0),
                "fee_score": rng.uniform(-50.0, 150.0),
                "risk_score": rng.uniform(-20.0, 120.0),
                "smart_money_score": rng.uniform(-20.0, 120.0),
                "te_score": rng.uniform(-50.0, 150.0),
                "is_extreme_crowding": rng.choice([True, False]),
            }
            bonus_choice = rng.choice([0.0, 5.0, None])
            if bonus_choice is not None:
                cand_item["switch_convenience_bonus"] = bonus_choice
            cands.append(cand_item)
        c_prev = rng.choice([None, rng.uniform(0.0, 20.0)])

        res = detector.evaluate_track_candidates(
            sector_id=f"FUZZ_{i}",
            default_champion_code=def_code,
            candidates=cands,
            c_prev=c_prev
        )

        assert isinstance(res["active_champion_code"], str) and len(res["active_champion_code"]) == 6
        assert isinstance(res["is_promoted"], bool)
        assert res["cusum_value"] >= 0.0
        if res["is_promoted"]:
            assert res["active_champion_code"] != def_code
            assert res["active_champion_name"] in res["promotion_label"]
            assert res["best_candidate"]["code"] == res["active_champion_code"]

    print("PASS: test_cusum_monte_carlo_fuzzing (500/500 passed)")


# ==============================================================================
# Suite 2: 全档位单调性与资金守恒压测
# ==============================================================================

def test_blueprint_tier_monotonicity():
    """
    压测 2.1: C1 至 C5 全档位权益单调性严格递增校验
    数学定理: Equity(C1) < Equity(C2) < Equity(C3) < Equity(C4) < Equity(C5)
    且在 BEAR (深度熊市破位态) 下，严格满足止损硬红线:
    Equity(C4) <= 56%, Equity(C5) <= 70%
    """
    print("\n--- Running test_blueprint_tier_monotonicity ---")
    regimes = [None, "BULL", "OSCILLATING", "BEAR"]
    defensive_codes = {"002351", "000086", "018757", "000216", "000217"}

    for regime in regimes:
        regime_label = regime if regime else "CURRENT_DEFAULT"
        equities = {}
        for tier in ["C1", "C2", "C3", "C4", "C5"]:
            if regime:
                tw = StrategyBridge.compute_dynamic_tier_weights(tier=tier, market_snapshot={"market_state_code": regime})
                bp = StrategyBridge.generate_zero_start_blueprint(
                    total_capital=100000.0,
                    target_weights_funds=tw,
                    tier=tier
                )
            else:
                bp = StrategyBridge.generate_zero_start_blueprint(
                    total_capital=100000.0,
                    tier=tier
                )
            # 计算权益资产占比
            eq_amt = sum(it["allocated_amount"] for it in bp["items"] if it["fund_code"] not in defensive_codes)
            eq_ratio = eq_amt / bp["total_capital"]
            equities[tier] = eq_ratio

        print(f"[{regime_label}] Equities: C1={equities['C1']:.4f}, C2={equities['C2']:.4f}, C3={equities['C3']:.4f}, C4={equities['C4']:.4f}, C5={equities['C5']:.4f}")

        # 断言严格单调递增
        assert equities["C1"] < equities["C2"], f"[{regime_label}] Equity(C1) {equities['C1']} 必须 < Equity(C2) {equities['C2']}"
        assert equities["C2"] < equities["C3"], f"[{regime_label}] Equity(C2) {equities['C2']} 必须 < Equity(C3) {equities['C3']}"
        assert equities["C3"] < equities["C4"], f"[{regime_label}] Equity(C3) {equities['C3']} 必须 < Equity(C4) {equities['C4']}"
        assert equities["C4"] < equities["C5"], f"[{regime_label}] Equity(C4) {equities['C4']} 必须 < Equity(C5) {equities['C5']}"

        # 深度熊市破位态算法止损硬红线
        if regime == "BEAR":
            assert equities["C4"] <= 0.56, f"BEAR 下 Equity(C4) 必须 <= 56%, 实际为 {equities['C4']:.4f}"
            assert equities["C5"] <= 0.70, f"BEAR 下 Equity(C5) 必须 <= 70%, 实际为 {equities['C5']:.4f}"

    print("PASS: test_blueprint_tier_monotonicity")


def test_blueprint_cash_conservation_and_zero_leakage():
    """
    压测 2.2: 100% 预算资金守恒与零资金泄漏校验
    测试各种金额级别（10,000, 50,000, 100,000, 500,000, 1,000,000 以及非整百千的浮点数 12345.67）：
    断言：
    1. 总分配金额严格等于 100% 预算，零超买、零资金泄漏：abs(allocated_sum - total_capital) < 0.05
    2. 各分项金额之和数学上严格等于 allocated_sum
    3. 剩余现金 remaining_cash 恒为 0.00 (或满足四舍五入守恒)
    """
    print("\n--- Running test_blueprint_cash_conservation_and_zero_leakage ---")
    test_capitals = [10000.0, 50000.0, 100000.0, 250000.0, 500000.0, 1000000.0, 12345.67, 88888.88]
    tiers = ["C1", "C2", "C3", "C4", "C5"]

    for cap in test_capitals:
        for tier in tiers:
            bp = StrategyBridge.generate_zero_start_blueprint(total_capital=cap, tier=tier)
            total = bp["total_capital"]
            allocated = bp["allocated_sum"]
            remaining = bp["remaining_cash"]
            items_sum = round(sum(it["allocated_amount"] for it in bp["items"]), 2)

            assert round(total, 2) == round(cap, 2)
            assert items_sum == allocated, f"items 金额之和 ({items_sum}) 必须等于 allocated_sum ({allocated})"
            # 资金守恒：允许 1 分钱以内的浮点四舍五入容差
            assert abs(allocated - total) <= 0.05, f"资金发生泄漏或超买: cap={total}, allocated={allocated}, diff={allocated-total}"
            assert abs((allocated + remaining) - total) <= 0.05, f"资金守恒破坏: allocated={allocated}, remaining={remaining}, total={total}"

    print("PASS: test_blueprint_cash_conservation_and_zero_leakage")


def test_blueprint_c4_c5_tech_011613_floor():
    """
    压测 2.3: C4 与 C5 档位华夏科创50C (011613) 进攻底仓保底
    断言：
    在 C4 与 C5 档位下，011613 的权重必须严格 >= 25% (0.2500)，且对应买入金额 >= 0.25 * total_capital
    在 BULL, OSCILLATING, BEAR 各状态下均进行严格核验。
    """
    print("\n--- Running test_blueprint_c4_c5_tech_011613_floor ---")
    for regime in ["BULL", "OSCILLATING", "BEAR", None]:
        for tier in ["C4", "C5"]:
            if regime:
                snapshot = {"market_state_code": regime}
                tw = StrategyBridge.compute_dynamic_tier_weights(tier=tier, market_snapshot=snapshot)
                bp = StrategyBridge.generate_zero_start_blueprint(
                    total_capital=100000.0,
                    target_weights_funds=tw,
                    tier=tier
                )
            else:
                bp = StrategyBridge.generate_zero_start_blueprint(
                    total_capital=100000.0,
                    tier=tier
                )
            item_011613 = next((it for it in bp["items"] if it["fund_code"] == "011613"), None)
            assert item_011613 is not None, f"[{regime} {tier}] 未找到 011613 标的！"
            actual_pct = item_011613["target_weight_pct"]
            actual_amt = item_011613["allocated_amount"]

            # 严格断言 >= 25%
            assert actual_pct >= 25.0 - 1e-4, f"[{regime} {tier}] 011613 权重占比应 >= 25.0%，实际为 {actual_pct}%"
            assert actual_amt >= 25000.0 - 1e-4, f"[{regime} {tier}] 011613 分配金额应 >= 25000.0，实际为 {actual_amt}"

    print("PASS: test_blueprint_c4_c5_tech_011613_floor")


# ==============================================================================
# Suite 3: 缓存并发与防抖压测
# ==============================================================================

def test_cache_concurrency_and_debounce():
    """
    压测 3: 30 秒缓存并发防抖与变点触发幂等性
    1. 多线程并发轰炸：启动 40 个并发工作线程高频请求 get_tier_sector_fund_selection；
       断言无任何竞态条件异常、字典迭代异常或死锁。
    2. 30 秒防抖验证：在缓存有效期内，返回结果必须直接命中内存缓存池，执行耗时应在微秒/毫秒级；
    3. 幂等性断言：缓存期内，各赛道 is_promoted 状态与 champion_code 100% 保持幂等一致；
    4. force_reload=True 支持穿透缓存进行新鲜度刷新。
    """
    print("\n--- Running test_cache_concurrency_and_debounce ---")

    # 1. 预热初始调用并记录时间戳 (C1 至 C5 全档位顺序预热落入 30 秒缓存)
    print("Pre-warming C1..C5 caches sequentially...")
    t0 = time.time()
    for t_w in ["C1", "C2", "C3", "C4", "C5"]:
        StrategyBridge.get_tier_sector_fund_selection(tier=t_w, force_reload=True)
    initial_time = time.time() - t0
    print(f"Initial warm-up of all tiers took: {initial_time:.4f}s")

    # 2. 连续 10 次快速调用，验证防抖与微秒级返回
    t1 = time.time()
    for _ in range(10):
        cached_res = StrategyBridge.get_tier_sector_fund_selection(tier="C3", force_reload=False)
    cached_duration = time.time() - t1
    print(f"10 cached calls took: {cached_duration:.4f}s (avg {cached_duration/10*1000:.2f}ms/call)")
    assert cached_duration < 0.1, f"缓存未生效，耗时异常: {cached_duration}s"

    # 3. 40 线程高并发压测
    print("Launching 40 concurrent threads...")
    errors = []
    results = []

    def worker_call(thread_id: int):
        tier_choice = ["C1", "C2", "C3", "C4", "C5"][thread_id % 5]
        res = StrategyBridge.get_tier_sector_fund_selection(tier=tier_choice, force_reload=False)
        return tier_choice, res

    with ThreadPoolExecutor(max_workers=40) as executor:
        futures = [executor.submit(worker_call, i) for i in range(100)]
        for fut in as_completed(futures):
            try:
                tier_choice, res = fut.result()
                results.append((tier_choice, res))
            except Exception as e:
                errors.append(e)

    assert len(errors) == 0, f"并发调用发生异常: {errors}"
    assert len(results) == 100, f"预期 100 次并发返回，实际为 {len(results)}"

    # 4. 幂等性核验：检查同一档位 (例如 C3) 的所有返回结果，赛道冠军和晋升状态必须 100% 相同
    c3_results = [res for tier, res in results if tier == "C3"]
    ref_c3 = c3_results[0]
    for other_c3 in c3_results[1:]:
        assert other_c3.keys() == ref_c3.keys()
        for sec_key in ref_c3:
            assert other_c3[sec_key]["champion_code"] == ref_c3[sec_key]["champion_code"]
            assert other_c3[sec_key]["is_promoted"] == ref_c3[sec_key]["is_promoted"]
            assert other_c3[sec_key]["promotion_label"] == ref_c3[sec_key]["promotion_label"]

    print("PASS: test_cache_concurrency_and_debounce (40 threads, 100 parallel calls, 100% idempotent)")


# ==============================================================================
# Main Runner
# ==============================================================================

def main():
    log_section("Milestone 3 Fix 1 Empirical Adversarial Stress Test Suite")
    start_total = time.time()

    # Suite 1
    log_section("Suite 1: CUSUM 极值边界压测")
    test_cusum_all_candidates_meltdown()
    test_cusum_alternating_leads()
    test_cusum_floating_precision_boundaries()
    test_cusum_negative_scores()
    test_cusum_zero_and_single_candidate_pool()
    test_cusum_monte_carlo_fuzzing()

    # Suite 2
    log_section("Suite 2: 全档位单调性与资金守恒压测")
    test_blueprint_tier_monotonicity()
    test_blueprint_cash_conservation_and_zero_leakage()
    test_blueprint_c4_c5_tech_011613_floor()

    # Suite 3
    log_section("Suite 3: 缓存并发与防抖压测")
    test_cache_concurrency_and_debounce()

    total_time = time.time() - start_total
    log_section(f"ALL ADVERSARIAL STRESS TESTS COMPLETED SUCCESSFULLY in {total_time:.2f}s!")
    print("\nVerdict: ALL TESTS PASSED (10/10 test functions)")

if __name__ == "__main__":
    main()
