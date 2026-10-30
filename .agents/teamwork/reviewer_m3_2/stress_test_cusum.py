# -*- coding: utf-8 -*-
"""
Adversarial Stress Test for CUSUMFundChangePointDetector (Milestone 3 / R6)
"""
import sys
from pathlib import Path

# Add AGY2_FundAdvisory to path
proj_dir = Path(__file__).resolve().parents[3] / "AGY2_FundAdvisory"
sys.path.insert(0, str(proj_dir))

from portfolio_manager import PortfolioManager, CUSUMFundChangePointDetector


def test_normal_no_decay():
    """默认标的持续领先，CUSUM 不累积，不触发轮换"""
    det = CUSUMFundChangePointDetector(slack_k=2.0, threshold_h=8.0)
    candidates = [
        {"code": "100032", "name": "富国中证红利A", "er_score": 95, "fee_score": 90, "risk_score": 95, "sm_score": 90, "te_score": 90},
        {"code": "090010", "name": "大成中证红利A", "er_score": 80, "fee_score": 85, "risk_score": 90, "sm_score": 80, "te_score": 85},
    ]
    res = det.evaluate_track_candidates("dividend", "100032", candidates)
    assert not res["is_promoted"]
    assert res["active_champion_code"] == "100032"
    assert res["cusum_value"] == 0.0
    print("PASS: test_normal_no_decay")


def test_cusum_decay_accumulation_and_promotion():
    """备选标的持续跑赢，累积超额突破 h=8.0 阈值，成功触发优选晋升"""
    det = CUSUMFundChangePointDetector(slack_k=2.0, threshold_h=8.0)
    # 备选 090010 持续比 100032 高 5 分
    # 每次衰减增量: (90 - 85) - 2.0 = 3.0 分
    # step 1: C = 3.0
    # step 2: C = 6.0
    # step 3: C = 9.0 >= 8.0 -> 触发!
    candidates = [
        {"code": "100032", "name": "富国中证红利A", "er_score": 85, "fee_score": 85, "risk_score": 85, "sm_score": 85, "te_score": 85},
        {"code": "090010", "name": "大成中证红利A", "er_score": 90, "fee_score": 90, "risk_score": 90, "sm_score": 90, "te_score": 90},
    ]
    
    res1 = det.evaluate_track_candidates("dividend", "100032", candidates)
    assert not res1["is_promoted"]
    assert abs(res1["cusum_value"] - 3.0) < 0.01

    res2 = det.evaluate_track_candidates("dividend", "100032", candidates)
    assert not res2["is_promoted"]
    assert abs(res2["cusum_value"] - 6.0) < 0.01

    res3 = det.evaluate_track_candidates("dividend", "100032", candidates)
    assert res3["is_promoted"]
    assert res3["active_champion_code"] == "090010"
    assert "自进化优选" in res3["promotion_label"]
    print("PASS: test_cusum_decay_accumulation_and_promotion")


def test_instant_risk_meltdown():
    """默认标的发生重大舆情/造假暴雷，底层排雷健康分 < 60，瞬间熔断晋升"""
    det = CUSUMFundChangePointDetector(slack_k=2.0, threshold_h=8.0)
    candidates = [
        {"code": "100032", "name": "富国中证红利A", "er_score": 95, "fee_score": 90, "risk_score": 55, "sm_score": 90, "te_score": 90},
        {"code": "090010", "name": "大成中证红利A", "er_score": 85, "fee_score": 85, "risk_score": 95, "sm_score": 85, "te_score": 85},
    ]
    res = det.evaluate_track_candidates("dividend", "100032", candidates)
    assert res["is_promoted"]
    assert res["active_champion_code"] == "090010"
    assert any("排雷健康分" in r for r in res["trigger_reasons"])
    print("PASS: test_instant_risk_meltdown")


def test_instant_extreme_crowding():
    """默认标的出现严重抱团踩踏预警，瞬间触发反拥挤避险换仓"""
    det = CUSUMFundChangePointDetector(slack_k=2.0, threshold_h=8.0)
    candidates = [
        {"code": "100032", "name": "富国中证红利A", "er_score": 95, "fee_score": 90, "risk_score": 90, "sm_score": 50, "te_score": 90, "is_extreme_crowding": True},
        {"code": "090010", "name": "大成中证红利A", "er_score": 85, "fee_score": 85, "risk_score": 90, "sm_score": 85, "te_score": 85},
    ]
    res = det.evaluate_track_candidates("dividend", "100032", candidates)
    assert res["is_promoted"]
    assert res["active_champion_code"] == "090010"
    assert any("抱团" in r or "拥挤" in r for r in res["trigger_reasons"])
    print("PASS: test_instant_extreme_crowding")


def test_empty_candidates_graceful():
    """极端空备选池防御"""
    det = CUSUMFundChangePointDetector()
    res = det.evaluate_track_candidates("test_sec", "100032", [])
    assert not res["is_promoted"]
    assert res["active_champion_code"] == "100032"
    print("PASS: test_empty_candidates_graceful")


def test_same_company_bonus_tilt():
    """验证 R5 同基金公司转换便利度加分 (+5.0分)"""
    det = CUSUMFundChangePointDetector()
    c1 = {"code": "100032", "er_score": 80, "fee_score": 80, "risk_score": 80, "sm_score": 80, "te_score": 80}
    c2 = {"code": "100033", "er_score": 80, "fee_score": 80, "risk_score": 80, "sm_score": 80, "te_score": 80, "switch_convenience_bonus": 5.0}
    s1 = det.compute_candidate_score(c1)
    s2 = det.compute_candidate_score(c2)
    assert s2["final_score"] == s1["final_score"] + 5.0
    print("PASS: test_same_company_bonus_tilt")


if __name__ == "__main__":
    test_normal_no_decay()
    test_cusum_decay_accumulation_and_promotion()
    test_instant_risk_meltdown()
    test_instant_extreme_crowding()
    test_empty_candidates_graceful()
    test_same_company_bonus_tilt()
    print("ALL ADVERSARIAL STRESS TESTS PASSED!")
