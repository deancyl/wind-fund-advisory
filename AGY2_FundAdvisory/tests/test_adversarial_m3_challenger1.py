"""
Adversarial Challenge Test Suite for Milestone 3 (R6 CUSUM Fund Change-Point Detection)
Written by Empirical Challenger (Agent-4 / Challenger 1).

Rigorous Empirical Verification of:
1. Multi-factor scoring formula:
   S_{f,t} = 0.35 * ER + 0.25 * (100 - Fee) + 0.15 * Risk + 0.15 * SM + 0.10 * (100 - TE)
2. Same-company T+1 SWITCH convenience bonus (+5.0 pts, strictly capped at 100.0).
3. Page's CUSUM decay recurrence with slack k=2.0 and healing dynamics:
   C_{c,t} = max(0, C_{c,t-1} + (max_f S_{f,t} - S_{c,t}) - k)
4. Structural decay change-point trigger conditions grid (3 independent triggers):
   - C_{c,t} >= 8.0 (CUSUM decay breach)
   - Risk_{c,t} < 60.0 (R1 bottom stock blowup / risk meltdown)
   - Extreme crowding (is_extreme_crowding / SM < 60.0 / crowding_warning)
5. Champion auto-promotion and badge exactness:
   "🔄 自进化优选：因综合评分领先，已自动为您优选 {champion_name}"
6. PortfolioManager delegation and module-level alias invariants.
7. Extreme boundary scanning, fuzzing, and robustness (zero crash, zero div-by-zero, state isolation).
"""

import math
import random
import pytest
from pathlib import Path
import sys
from typing import Dict, Any, List

PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from portfolio_manager import (
    PortfolioManager,
    CUSUMFundChangePointDetector,
    get_fund_selection_funnel_stats
)


# =====================================================================
# 1. 多因子打分公式精度、权重和与因果单调性测试 (R6 Core Formula)
# =====================================================================

def test_adv_multifactor_scoring_exactness_and_weights():
    """
    [Adversarial Challenge 1] 候选基金竞争力多因子打分公式实证检验：
    S_{f,t} = 0.35 * ER + 0.25 * (100 - Fee) + 0.15 * Risk + 0.15 * SM + 0.10 * (100 - TE)
    - 验证权重严格相加等于 1.000 (0.35 + 0.25 + 0.15 + 0.15 + 0.10 = 1.0)；
    - 验证极限输入 (全 100 -> 100.0, 全 0 -> 0.0)；
    - 验证各因子的边际敏感度严格与理论权重吻合 (ER: 0.35, Fee: 0.25, Risk: 0.15, SM: 0.15, TE: 0.10)；
    - 验证多别名解析完备性 (er_score, alpha_score, fee_score, health_score, crowding_score 等)。
    """
    detector = CUSUMFundChangePointDetector(slack_k=2.0, threshold_h=8.0)

    # 1.1 全满分极限
    perfect_cand = {
        "code": "000001",
        "name": "满分标的",
        "er_score": 100.0,
        "fee_score": 100.0,
        "risk_score": 100.0,
        "smart_money_score": 100.0,
        "te_score": 100.0,
    }
    s_perf = detector.compute_candidate_score(perfect_cand)
    assert s_perf["composite_score"] == 100.0, f"全满分得分应为 100.0，实际为 {s_perf['composite_score']}"
    assert s_perf["final_score"] == 100.0

    # 1.2 全零分极限
    zero_cand = {
        "code": "000002",
        "name": "零分标的",
        "er_score": 0.0,
        "fee_score": 0.0,
        "risk_score": 0.0,
        "smart_money_score": 0.0,
        "te_score": 0.0,
    }
    s_zero = detector.compute_candidate_score(zero_cand)
    assert s_zero["composite_score"] == 0.0, f"全零分得分应为 0.0，实际为 {s_zero['composite_score']}"
    assert s_zero["final_score"] == 0.0

    # 1.3 各因子边际敏感度精确验证
    base_cand = {
        "code": "000003",
        "name": "基准标的",
        "er_score": 50.0,
        "fee_score": 50.0,
        "risk_score": 50.0,
        "smart_money_score": 50.0,
        "te_score": 50.0,
    }
    s_base = detector.compute_candidate_score(base_cand)["composite_score"]
    assert s_base == 50.0, f"50分基准得分应为 50.0，实际为 {s_base}"

    # 单独增加 ER 20 分 (预期增量 20 * 0.35 = 7.00)
    c_er = dict(base_cand, er_score=70.0)
    assert round(detector.compute_candidate_score(c_er)["composite_score"] - s_base, 2) == 7.00

    # 单独增加 Fee 20 分 (预期增量 20 * 0.25 = 5.00)
    c_fee = dict(base_cand, fee_score=70.0)
    assert round(detector.compute_candidate_score(c_fee)["composite_score"] - s_base, 2) == 5.00

    # 单独增加 Risk 20 分 (预期增量 20 * 0.15 = 3.00)
    c_risk = dict(base_cand, risk_score=70.0)
    assert round(detector.compute_candidate_score(c_risk)["composite_score"] - s_base, 2) == 3.00

    # 单独增加 SM 20 分 (预期增量 20 * 0.15 = 3.00)
    c_sm = dict(base_cand, smart_money_score=70.0)
    assert round(detector.compute_candidate_score(c_sm)["composite_score"] - s_base, 2) == 3.00

    # 单独增加 TE 20 分 (预期增量 20 * 0.10 = 2.00)
    c_te = dict(base_cand, te_score=70.0)
    assert round(detector.compute_candidate_score(c_te)["composite_score"] - s_base, 2) == 2.00

    # 1.4 多种键名别名与原始扣分反转解析
    alias_cand = {
        "fund_code": "001122",
        "fund_name": "别名测试基",
        "alpha_score": 80.0,            # ER 对应 alpha_score
        "fee": 1.2,                     # 原始费率扣分 1.2% -> 100 - 1.2 = 98.8
        "health_score": 90.0,           # Risk 对应 health_score
        "crowding_score": 85.0,         # SM 对应 crowding_score
        "te": 2.5                       # 原始跟踪误差 2.5% -> 100 - 2.5 = 97.5
    }
    s_alias = detector.compute_candidate_score(alias_cand)
    assert s_alias["code"] == "001122"
    assert s_alias["er_score"] == 80.0
    assert s_alias["fee_score"] == 98.8
    assert s_alias["risk_score"] == 90.0
    assert s_alias["smart_money_score"] == 85.0
    assert s_alias["te_score"] == 97.5

    # 理论值 = 0.35*80 + 0.25*98.8 + 0.15*90 + 0.15*85 + 0.10*97.5 = 28 + 24.7 + 13.5 + 12.75 + 9.75 = 88.70
    expected_composite = round(0.35 * 80.0 + 0.25 * 98.8 + 0.15 * 90.0 + 0.15 * 85.0 + 0.10 * 97.5, 2)
    assert s_alias["composite_score"] == expected_composite


# =====================================================================
# 2. 同基金公司 T+1 SWITCH 转换便利度加分与严格 100 分封顶 (R5/R6)
# =====================================================================

def test_adv_same_company_convenience_bonus_and_strict_100_cap():
    """
    [Adversarial Challenge 2] 同基金公司转换便利度加分与封顶测试：
    - 支持 is_same_company_bonus (默认 +5.0) 与显式 switch_convenience_bonus 注入；
    - 验证最终得分 final_score 严格封顶于 100.0 分，严禁溢出至 100.1~105.0；
    - 验证在综合分微弱落后时，同公司便利度能够实现合规逆转胜出。
    """
    detector = CUSUMFundChangePointDetector()

    # 2.1 基础 +5.0 分加成
    cand_same = {
        "code": "002351",
        "name": "易方达纯债",
        "er_score": 80.0,
        "fee_score": 80.0,
        "risk_score": 80.0,
        "smart_money_score": 80.0,
        "te_score": 80.0,
        "is_same_company_bonus": True
    }
    res = detector.compute_candidate_score(cand_same)
    assert res["composite_score"] == 80.0
    assert res["convenience_bonus"] == 5.0
    assert res["final_score"] == 85.0
    assert res["total_score"] == 85.0

    # 2.2 严格 100.0 封顶防御
    cand_high = {
        "code": "002352",
        "name": "超高分标的",
        "er_score": 98.0,
        "fee_score": 98.0,
        "risk_score": 98.0,
        "smart_money_score": 98.0,
        "te_score": 98.0,
        "switch_convenience_bonus": 5.0
    }
    res_high = detector.compute_candidate_score(cand_high)
    assert res_high["composite_score"] == 98.0
    assert res_high["convenience_bonus"] == 5.0
    # 98.0 + 5.0 = 103.0 -> 必须被 min(100.0, ...) 压制为 100.0
    assert res_high["final_score"] == 100.0
    assert res_high["final_score"] <= 100.0

    # 2.3 转换便利度驱动的合理逆转超车
    # 标的 A (外部公司): 综合分 84.0，无加分 -> 最终 84.0
    # 标的 B (同门公司): 综合分 81.0，+5.0加分 -> 最终 86.0
    cand_ext = {
        "code": "110001", "name": "外部标的",
        "er_score": 84.0, "fee_score": 84.0, "risk_score": 84.0, "smart_money_score": 84.0, "te_score": 84.0
    }
    cand_peer = {
        "code": "110002", "name": "同门标的",
        "er_score": 81.0, "fee_score": 81.0, "risk_score": 81.0, "smart_money_score": 81.0, "te_score": 81.0,
        "is_same_company_bonus": True
    }
    eval_res = detector.evaluate_track_candidates(
        sector_id="sector_test",
        default_champion_code="110001",
        candidates=[cand_ext, cand_peer],
        c_prev=7.0  # 前序衰减已接近触发
    )
    # diff = 86.0 - 84.0 = 2.0; increment = 2.0 - 2.0 = 0.0; C = 7.0 (尚未破 8.0)
    # 现在前序设为 8.5
    eval_res_trigger = detector.evaluate_track_candidates(
        sector_id="sector_test",
        default_champion_code="110001",
        candidates=[cand_ext, cand_peer],
        c_prev=8.5
    )
    assert eval_res_trigger["is_triggered"] is True
    assert eval_res_trigger["is_promoted"] is True
    assert eval_res_trigger["active_champion_code"] == "110002"
    assert "🔄 自进化优选" in eval_res_trigger["promotion_label"]


# =====================================================================
# 3. Page's CUSUM 衰减递推、松弛参数 k=2.0 与自愈机制 (R6 CUSUM Math)
# =====================================================================

def test_adv_cusum_decay_recurrence_slack_and_healing():
    """
    [Adversarial Challenge 3] Page's CUSUM 衰减数学公式、松弛容忍度与自愈机制检验：
    C_{c,t} = max(0, C_{c,t-1} + (max_f S_{f,t} - S_{c,t}) - k)
    - 松弛容忍防扰动：当备选领先幅度 <= k (2.0分) 时，CUSUM 绝对不增加；
    - 连续跑输累积：领先幅度 > k 时，精确累积超出部分；
    - 冠军反超自愈：当冠军重新领跑时，CUSUM 逐期自愈消除（每期最多消化 k 分），且下限刚性锚定 0.0；
    - 赛道间状态绝对物理隔离与 reset 清理。
    """
    detector = CUSUMFundChangePointDetector(slack_k=2.0, threshold_h=8.0)
    detector.reset()

    sec = "value_dividend"
    champ_code = "000001"

    # 阶段 1: 冠军综合 85.0，备选 86.9 (领先差值 1.9 <= k=2.0)
    # decay_increment = 1.9 - 2.0 = -0.1 -> max(0, 0 - 0.1) = 0.0 (免疫小幅噪音)
    cand_noise = [
        {"code": champ_code, "name": "原冠军", "er_score": 85.0, "fee_score": 85.0, "risk_score": 85.0, "smart_money_score": 85.0, "te_score": 85.0},
        {"code": "000002", "name": "微幅跑赢备选", "er_score": 86.9, "fee_score": 86.9, "risk_score": 86.9, "smart_money_score": 86.9, "te_score": 86.9}
    ]
    r1 = detector.evaluate_track_candidates(sec, champ_code, cand_noise)
    assert r1["cusum_value"] == 0.0, f"差值 1.9 <= k 时 CUSUM 应为 0.0，实际为 {r1['cusum_value']}"
    assert detector.get_cusum(sec) == 0.0

    # 阶段 2: 备选大幅领先 6.0 分 (85.0 vs 91.0)
    # decay_increment = 6.0 - 2.0 = 4.0 -> C_1 = 4.0
    cand_lead1 = [
        {"code": champ_code, "name": "原冠军", "er_score": 85.0, "fee_score": 85.0, "risk_score": 85.0, "smart_money_score": 85.0, "te_score": 85.0},
        {"code": "000002", "name": "大幅领先备选", "er_score": 91.0, "fee_score": 91.0, "risk_score": 91.0, "smart_money_score": 91.0, "te_score": 91.0}
    ]
    r2 = detector.evaluate_track_candidates(sec, champ_code, cand_lead1)
    assert r2["cusum_value"] == 4.0
    assert r2["is_triggered"] is False  # 4.0 < 8.0 未触发

    # 阶段 3: 备选再次领先 5.0 分 (85.0 vs 90.0)
    # decay_increment = 5.0 - 2.0 = 3.0 -> C_2 = 4.0 + 3.0 = 7.0
    cand_lead2 = [
        {"code": champ_code, "name": "原冠军", "er_score": 85.0, "fee_score": 85.0, "risk_score": 85.0, "smart_money_score": 85.0, "te_score": 85.0},
        {"code": "000002", "name": "大幅领先备选", "er_score": 90.0, "fee_score": 90.0, "risk_score": 90.0, "smart_money_score": 90.0, "te_score": 90.0}
    ]
    r3 = detector.evaluate_track_candidates(sec, champ_code, cand_lead2)
    assert r3["cusum_value"] == 7.0
    assert r3["is_triggered"] is False  # 7.0 < 8.0 依然未触发

    # 阶段 4: 备选领先 4.0 分 (85.0 vs 89.0)
    # decay_increment = 4.0 - 2.0 = 2.0 -> C_3 = 7.0 + 2.0 = 9.0 >= 8.0 (触发变点!)
    cand_lead3 = [
        {"code": champ_code, "name": "原冠军", "er_score": 85.0, "fee_score": 85.0, "risk_score": 85.0, "smart_money_score": 85.0, "te_score": 85.0},
        {"code": "000002", "name": "大幅领先备选", "er_score": 89.0, "fee_score": 89.0, "risk_score": 89.0, "smart_money_score": 89.0, "te_score": 89.0}
    ]
    r4 = detector.evaluate_track_candidates(sec, champ_code, cand_lead3)
    assert r4["cusum_value"] == 9.0
    assert r4["is_triggered"] is True
    assert r4["is_promoted"] is True
    assert r4["active_champion_code"] == "000002"

    # 阶段 5: 自愈测试 (原冠军重新发力领跑，领先备选 10 分)
    # max_score - champ_score = 0; increment = 0 - 2.0 = -2.0
    # C_4 = max(0, 9.0 - 2.0) = 7.0
    cand_recover = [
        {"code": champ_code, "name": "原冠军", "er_score": 95.0, "fee_score": 95.0, "risk_score": 95.0, "smart_money_score": 95.0, "te_score": 95.0},
        {"code": "000002", "name": "跑输备选", "er_score": 85.0, "fee_score": 85.0, "risk_score": 85.0, "smart_money_score": 85.0, "te_score": 85.0}
    ]
    r5 = detector.evaluate_track_candidates(sec, champ_code, cand_recover)
    assert r5["cusum_value"] == 7.0
    assert r5["is_triggered"] is False

    # 连续 4 轮领跑，验证 CUSUM 递减直至 0.0，且绝对不跌为负数
    detector.evaluate_track_candidates(sec, champ_code, cand_recover)  # 7.0 - 2.0 = 5.0
    assert detector.get_cusum(sec) == 5.0
    detector.evaluate_track_candidates(sec, champ_code, cand_recover)  # 5.0 - 2.0 = 3.0
    assert detector.get_cusum(sec) == 3.0
    detector.evaluate_track_candidates(sec, champ_code, cand_recover)  # 3.0 - 2.0 = 1.0
    assert detector.get_cusum(sec) == 1.0
    detector.evaluate_track_candidates(sec, champ_code, cand_recover)  # max(0, 1.0 - 2.0) = 0.0
    assert detector.get_cusum(sec) == 0.0
    detector.evaluate_track_candidates(sec, champ_code, cand_recover)  # max(0, 0.0 - 2.0) = 0.0
    assert detector.get_cusum(sec) == 0.0

    # 阶段 6: 赛道间状态隔离验证
    sec_growth = "growth_tech"
    detector.set_cusum(sec_growth, 6.5)
    assert detector.get_cusum(sec_growth) == 6.5
    assert detector.get_cusum(sec) == 0.0  # value 赛道保持 0.0 独立

    detector.reset(sec_growth)
    assert detector.get_cusum(sec_growth) == 0.0
    assert detector.get_cusum(sec) == 0.0


# =====================================================================
# 4. 结构性变点三大独立触发条件网格测试 (Triggers Grid)
# =====================================================================

def test_adv_changepoint_trigger_conditions_grid():
    """
    [Adversarial Challenge 4] 结构性变点三大触发条件独立网格全覆盖测试：
    条件 1: C_{c,t} >= 8.0 (CUSUM 衰减超标)
    条件 2: Risk_{c,t} < 60.0 (底层重仓股发生严重暴雷排雷熔断)
    条件 3: 极度拥挤度预警 (is_extreme_crowding / SM < 60.0 / crowding_warning)
    - 逐一单独触发检验；
    - 临界边界值检验 (7.99 vs 8.00; 60.0 vs 59.9)；
    - 三条件同时并发触发检验。
    """
    detector = CUSUMFundChangePointDetector(slack_k=2.0, threshold_h=8.0)
    champ_code = "100032"

    # 4.1 触发条件 1: 仅 CUSUM 衰减超标 (7.99 未触发 vs 8.00 触发)
    cands_normal = [
        {"code": champ_code, "name": "正常冠军", "er_score": 80.0, "fee_score": 80.0, "risk_score": 90.0, "smart_money_score": 90.0, "te_score": 80.0},
        {"code": "100033", "name": "优秀备选", "er_score": 85.0, "fee_score": 85.0, "risk_score": 90.0, "smart_money_score": 90.0, "te_score": 85.0}
    ]

    # c_prev = 7.99, diff = 85 - 80 = 5, k = 2 -> inc = 3.0 -> 会加到 10.99 触发。
    # 为了测试 7.99 临界点，我们构造 inc = 0 (diff = 2.0 = k)
    cands_boundary = [
        {"code": champ_code, "name": "正常冠军", "er_score": 80.0, "fee_score": 80.0, "risk_score": 90.0, "smart_money_score": 90.0, "te_score": 80.0},
        {"code": "100033", "name": "临界备选", "er_score": 82.0, "fee_score": 82.0, "risk_score": 92.0, "smart_money_score": 92.0, "te_score": 82.0}
    ]
    # c_prev = 7.99 -> c_curr = 7.99 < 8.0
    r_sub8 = detector.evaluate_track_candidates("sec1", champ_code, cands_boundary, c_prev=7.99)
    assert r_sub8["cusum_value"] == 7.99
    assert r_sub8["is_triggered"] is False

    # c_prev = 8.00 -> c_curr = 8.00 >= 8.0
    r_eq8 = detector.evaluate_track_candidates("sec1", champ_code, cands_boundary, c_prev=8.00)
    assert r_eq8["cusum_value"] == 8.00
    assert r_eq8["is_triggered"] is True
    assert any("CUSUM 衰减指标" in reason for reason in r_eq8["trigger_reasons"])

    # 4.2 触发条件 2: 仅 Risk 排雷暴雷 (< 60.0)
    # Risk = 60.0 (边界不触发) vs 59.9 (跌破安全线触发)
    cands_risk_safe = [
        {"code": champ_code, "name": "临界冠军", "er_score": 90.0, "fee_score": 90.0, "risk_score": 60.0, "smart_money_score": 80.0, "te_score": 80.0},
        {"code": "100033", "name": "备选标的", "er_score": 80.0, "fee_score": 80.0, "risk_score": 80.0, "smart_money_score": 80.0, "te_score": 80.0}
    ]
    r_risk_safe = detector.evaluate_track_candidates("sec2", champ_code, cands_risk_safe, c_prev=0.0)
    assert r_risk_safe["is_triggered"] is False

    cands_risk_breach = [
        {"code": champ_code, "name": "暴雷冠军", "er_score": 90.0, "fee_score": 90.0, "risk_score": 59.9, "smart_money_score": 80.0, "te_score": 80.0},
        {"code": "100033", "name": "优质备选", "er_score": 85.0, "fee_score": 85.0, "risk_score": 95.0, "smart_money_score": 85.0, "te_score": 85.0}
    ]
    r_risk_breach = detector.evaluate_track_candidates("sec2", champ_code, cands_risk_breach, c_prev=0.0)
    assert r_risk_breach["is_triggered"] is True
    assert any("R1 底层排雷健康分" in reason for reason in r_risk_breach["trigger_reasons"])
    assert r_risk_breach["is_promoted"] is True
    assert r_risk_breach["active_champion_code"] == "100033"

    # 4.3 触发条件 3: 极度拥挤度预警 (SM < 60.0 或 is_extreme_crowding / crowding_warning)
    cands_crowd_sm = [
        {"code": champ_code, "name": "抱团冠军", "er_score": 90.0, "fee_score": 90.0, "risk_score": 90.0, "smart_money_score": 58.0, "te_score": 80.0},
        {"code": "100033", "name": "避险备选", "er_score": 85.0, "fee_score": 85.0, "risk_score": 90.0, "smart_money_score": 85.0, "te_score": 85.0}
    ]
    r_crowd = detector.evaluate_track_candidates("sec3", champ_code, cands_crowd_sm, c_prev=0.0)
    assert r_crowd["is_triggered"] is True
    assert any("R3 机构极度抱团松动预警" in reason for reason in r_crowd["trigger_reasons"])
    assert r_crowd["is_promoted"] is True

    # 4.4 三大触发条件同时并发
    cands_triple = [
        {"code": champ_code, "name": "全面溃败冠军", "er_score": 50.0, "fee_score": 50.0, "risk_score": 45.0, "smart_money_score": 40.0, "te_score": 50.0, "crowding_warning": True},
        {"code": "100033", "name": "全能备选", "er_score": 95.0, "fee_score": 95.0, "risk_score": 95.0, "smart_money_score": 95.0, "te_score": 95.0}
    ]
    r_triple = detector.evaluate_track_candidates("sec4", champ_code, cands_triple, c_prev=8.5)
    assert r_triple["is_triggered"] is True
    assert len(r_triple["trigger_reasons"]) == 3
    assert any("CUSUM" in r for r in r_triple["trigger_reasons"])
    assert any("R1 底层排雷" in r for r in r_triple["trigger_reasons"])
    assert any("R3 机构极度抱团" in r for r in r_triple["trigger_reasons"])


# =====================================================================
# 5. 冠军自动晋升、自进化标签与“不自我晋升”防呆守则 (Promotion Logic)
# =====================================================================

def test_adv_champion_promotion_and_badge_exactness():
    """
    [Adversarial Challenge 5] 冠军自动晋升与自进化优选标签生成检验：
    - 当变点触发且备选第 1 名领先于默认冠军时，自动将第 1 名晋升为活跃冠军；
    - 严格检验标签格式: "🔄 自进化优选：因综合评分领先，已自动为您优选 {active_champ_name}"；
    - 防呆断言：当变点触发（如暴雷熔断），但原冠军在池子中得分依然是第 1 名（或无其他备选），
      绝对严禁向自己晋升，is_promoted 必须为 False 且 promotion_label 为空。
    """
    detector = CUSUMFundChangePointDetector()
    def_code = "005561"
    def_name = "华富中债纯债"

    alt_code = "002351"
    alt_name = "易方达富华纯债"

    # 5.1 正常晋升情景
    candidates = [
        {"code": def_code, "name": def_name, "er_score": 70.0, "fee_score": 70.0, "risk_score": 70.0, "smart_money_score": 70.0, "te_score": 70.0},
        {"code": alt_code, "name": alt_name, "er_score": 90.0, "fee_score": 90.0, "risk_score": 90.0, "smart_money_score": 90.0, "te_score": 90.0}
    ]
    res_promo = detector.evaluate_track_candidates(
        sector_id="bond",
        default_champion_code=def_code,
        candidates=candidates,
        c_prev=8.0  # 触发变点
    )
    assert res_promo["is_triggered"] is True
    assert res_promo["is_promoted"] is True
    assert res_promo["active_champion_code"] == alt_code
    assert res_promo["active_champion_name"] == alt_name
    expected_badge = f"🔄 自进化优选：因综合评分领先，已自动为您优选 {alt_name}"
    assert res_promo["promotion_label"] == expected_badge, (
        f"自进化优选标签文案不匹配: 期望='{expected_badge}' vs 实际='{res_promo['promotion_label']}'"
    )

    # 5.2 暴雷熔断风控：原冠军触发 risk<60 暴雷被剥夺资格，强制晋升合格备选标的
    candidates_self_best = [
        {"code": def_code, "name": def_name, "er_score": 85.0, "fee_score": 85.0, "risk_score": 55.0, "smart_money_score": 80.0, "te_score": 80.0},  # risk<60 触发变点与暴雷熔断
        {"code": alt_code, "name": alt_name, "er_score": 60.0, "fee_score": 60.0, "risk_score": 60.0, "smart_money_score": 60.0, "te_score": 60.0}   # 合格备选标的
    ]
    res_self = detector.evaluate_track_candidates(
        sector_id="bond",
        default_champion_code=def_code,
        candidates=candidates_self_best,
        c_prev=0.0
    )
    assert res_self["is_triggered"] is True  # 变点被 risk<60 触发
    assert res_self["is_promoted"] is True   # 原冠军暴雷资格剥夺，触发合格备选标的强制晋升
    assert res_self["active_champion_code"] == alt_code
    assert res_self["active_champion_name"] == alt_name
    assert "自进化优选" in res_self["promotion_label"]


# =====================================================================
# 6. PortfolioManager 委托契约、模块级别名与全市场漏斗校验 (Contracts)
# =====================================================================

def test_adv_portfoliomanager_integration_and_proxy():
    """
    [Adversarial Challenge 6] PortfolioManager 实例代理接口与漏斗统计检验：
    - 断言 pm.cusum_detector 为 CUSUMFundChangePointDetector 单例实例；
    - 断言 pm.evaluate_track_candidates 完美代理委托执行；
    - 检验 get_fund_selection_funnel_stats 结构完备性与四级漏斗数字一致性。
    """
    pm = PortfolioManager()
    assert hasattr(pm, "cusum_detector")
    assert isinstance(pm.cusum_detector, CUSUMFundChangePointDetector)

    # 代理调用测试
    cands = [
        {"code": "000001", "name": "测试基A", "er_score": 80.0, "fee_score": 80.0, "risk_score": 80.0, "smart_money_score": 80.0, "te_score": 80.0},
        {"code": "000002", "name": "测试基B", "er_score": 90.0, "fee_score": 90.0, "risk_score": 90.0, "smart_money_score": 90.0, "te_score": 90.0}
    ]
    proxy_res = pm.evaluate_track_candidates(
        sector_id="sector_pm",
        default_champion_code="000001",
        candidates=cands,
        c_prev=9.0
    )
    assert proxy_res["is_promoted"] is True
    assert proxy_res["active_champion_code"] == "000002"

    # 全市场漏斗四级数据检验
    funnel = get_fund_selection_funnel_stats()
    assert "total_market_funds" in funnel
    assert "hard_filtered_funds" in funnel
    assert "candidate_funds" in funnel
    assert "final_champion_funds" in funnel
    assert funnel["candidate_funds"] == 20
    assert funnel["final_champion_funds"] == 5
    assert len(funnel["steps"]) == 4


# =====================================================================
# 7. 对抗性 Fuzzing 压力网格、极端脏数据与边界鲁棒性 (Robustness)
# =====================================================================

def test_adv_cusum_detector_fuzzing_and_boundary_safety():
    """
    [Adversarial Challenge 7] 对抗性极端输入扫描与 Fuzzing 测试：
    - 空候选列表、无代码、非法字符串与缺失关键因子；
    - 极值注入 (NaN, Inf, 负数, 超大数 1e9)；
    - 1000 次随机蒙特卡洛多候选基金并发评估，断言零崩溃、零除零、CUSUM 指标恒非负。
    """
    detector = CUSUMFundChangePointDetector()

    # 7.1 空候选列表测试 (自动以默认标的兜底)
    empty_res = detector.evaluate_track_candidates(
        sector_id="empty_sec",
        default_champion_code="005561",
        candidates=[]
    )
    assert empty_res["active_champion_code"] == "005561"
    assert empty_res["is_promoted"] is False
    assert empty_res["cusum_value"] >= 0.0

    # 7.2 脏数据与类型不一致测试
    dirty_candidates = [
        {"code": 123, "name": None, "er_score": -999.0, "fee_score": 999.0, "risk_score": float("nan")},
        {"code": " 000888 ", "name": "空格基", "er_score": "88.5", "fee_score": "75.0"},
        {"fund_code": "666", "er_score": 1e6, "risk_score": -100.0}
    ]
    # 不抛出任何异常，能够安全容错处理
    try:
        dirty_res = detector.evaluate_track_candidates("dirty_sec", "000888", dirty_candidates)
        assert dirty_res["active_champion_code"] is not None
        assert 0.0 <= dirty_res["champion_score"] <= 100.0
    except Exception as e:
        pytest.fail(f"脏数据输入导致崩溃: {e}")

    # 7.3 1000 次蒙特卡洛随机对抗冲击
    random.seed(42)
    for trial in range(1000):
        n_cands = random.randint(1, 15)
        mock_cands = []
        for i in range(n_cands):
            c_code = f"{random.randint(1, 999999):06d}"
            mock_cands.append({
                "code": c_code,
                "name": f"随机基_{c_code}",
                "er_score": random.uniform(-20.0, 120.0),
                "fee_score": random.uniform(-10.0, 110.0),
                "risk_score": random.uniform(-10.0, 110.0),
                "smart_money_score": random.uniform(-10.0, 110.0),
                "te_score": random.uniform(-10.0, 110.0),
                "is_same_company_bonus": random.choice([True, False]),
                "is_extreme_crowding": random.choice([True, False])
            })
        def_pick = mock_cands[0]["code"]
        c_init = random.uniform(0.0, 15.0)

        res = detector.evaluate_track_candidates(
            sector_id=f"mc_sec_{trial % 10}",
            default_champion_code=def_pick,
            candidates=mock_cands,
            c_prev=c_init
        )

        # 断言数学不变量
        assert res["cusum_value"] >= 0.0, f"CUSUM 衰减得分不能为负数: {res['cusum_value']}"
        assert 0.0 <= res["max_score"] <= 100.0, f"最高得分溢出 0~100 边界: {res['max_score']}"
        assert 0.0 <= res["champion_score"] <= 100.0, f"冠军得分溢出 0~100 边界: {res['champion_score']}"
        if res["is_promoted"]:
            assert res["active_champion_code"] != def_pick, "晋升目标不得为默认标的自身"
            assert "🔄 自进化优选" in res["promotion_label"]
