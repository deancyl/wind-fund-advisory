# -*- coding: utf-8 -*-
"""
Independent Victory Verification & Stress Testing Suite
Author: Victory Auditor (Zero shared context)
"""
import sys
import hashlib
from pathlib import Path

# Paths
AUDITOR_DIR = Path(__file__).resolve().parent
WORKSPACE = AUDITOR_DIR.parent.parent.parent
AGY2_DIR = WORKSPACE / "AGY2_FundAdvisory"

sys.path.insert(0, str(AGY2_DIR))
sys.path.insert(0, str(WORKSPACE))

from portfolio_manager import PortfolioManager
from strategy_bridge import StrategyBridge, TIER_TARGET_WEIGHTS, RISK_TIERS_CONFIG
import app_gui

def test_1_slider_linkage():
    print("[Test 1] Slider real-time linkage & tier allocations...")
    # Test boundary mappings
    assert app_gui.map_slider_to_tier(-5.0) == "C1"
    assert app_gui.map_slider_to_tier(5.0) == "C1"
    assert app_gui.map_slider_to_tier(8.0) == "C1"
    assert app_gui.map_slider_to_tier(8.1) == "C2"
    assert app_gui.map_slider_to_tier(10.0) == "C2"
    assert app_gui.map_slider_to_tier(12.0) == "C2"
    assert app_gui.map_slider_to_tier(12.1) == "C3"
    assert app_gui.map_slider_to_tier(15.0) == "C3"
    assert app_gui.map_slider_to_tier(18.0) == "C3"
    assert app_gui.map_slider_to_tier(18.1) == "C4"
    assert app_gui.map_slider_to_tier(25.0) == "C4"
    assert app_gui.map_slider_to_tier(30.0) == "C4"
    assert app_gui.map_slider_to_tier(30.1) == "C5"
    assert app_gui.map_slider_to_tier(60.0) == "C5"
    assert app_gui.map_slider_to_tier(100.0) == "C5"

    blueprints = {}
    for tier in ["C1", "C2", "C3", "C4", "C5"]:
        bp = StrategyBridge.generate_zero_start_blueprint(total_capital=100000.0, tier=tier)
        assert abs(bp["total_capital"] - 100000.0) < 0.01
        assert bp["tier"] == tier
        items = bp["items"]
        codes = [it["fund_code"] for it in items]
        weights = {it["fund_code"]: it["target_weight_pct"] for it in items}
        blueprints[tier] = weights
        if tier == "C1":
            assert "011613" not in codes
            assert (weights.get("002351", 0) + weights.get("000086", 0)) >= 65.0
        elif tier in ["C4", "C5"]:
            assert "011613" in codes
            assert weights["011613"] >= 25.0
        if tier == "C5":
            assert "016634" in codes
            assert "013841" in codes

    # Ensure all 5 tiers have distinct allocations
    tiers = list(blueprints.keys())
    for i in range(len(tiers)):
        for j in range(i + 1, len(tiers)):
            assert blueprints[tiers[i]] != blueprints[tiers[j]], f"{tiers[i]} equals {tiers[j]}"
    print("  -> PASS: All 5 tiers dynamically differentiated, C4/C5 contain 011613, C1 safe bonds.")

def test_2_account_drawdown_reset():
    print("[Test 2] Account setup drawdown reset...")
    pm = PortfolioManager()
    # Heavily corrupt prior state
    pm.baseline_equity = 999999.0
    pm.peak_equity = 888888.0
    pm.max_drawdown_pct = 75.0
    pm.portfolio_return_pct = -50.0
    pm.benchmark_return_pct = -30.0
    pm.alpha_return_pct = -20.0
    pm.available_cash = 1000.0

    bp = StrategyBridge.generate_zero_start_blueprint(total_capital=100000.0, tier="C3")
    res = pm.apply_zero_start_blueprint(bp)
    assert res["status"] == "SUCCESS"
    assert abs(pm.baseline_equity - 100000.0) < 0.1
    assert abs(pm.peak_equity - 100000.0) < 0.1
    assert pm.peak_equity == pm.total_equity
    assert pm.max_drawdown_pct == 0.0
    assert pm.portfolio_return_pct == 0.0
    assert pm.benchmark_return_pct == 0.0
    assert pm.alpha_return_pct == 0.0

    assert "001071" in pm.holdings
    h_001071 = pm.holdings["001071"]
    assert h_001071.is_core_strategy is True
    assert "替换" not in h_001071.transition_tag
    assert ("核心" in h_001071.transition_tag or "底仓" in h_001071.transition_tag)
    print("  -> PASS: Account baseline and peak reset, drawdown 0.0, 001071 tagged as core without replacement.")

def test_3_bank_double_high_exemption():
    print("[Test 3] Financial / bank double-high exemption...")
    pm = PortfolioManager()
    target_banks = ["招商银行", "农业银行", "交通银行", "江苏银行"]
    found_banks = 0
    for fund_code in ["100032", "005561"]:
        res = pm.screen_fund_look_through_risk(fund_code)
        for stk in res.get("top_stocks_screen", []):
            s_name = stk.get("stock_name", "")
            if any(b in s_name for b in target_banks):
                found_banks += 1
                assert stk.get("double_high_risk") is False, f"{s_name} double_high_risk must be False"
                assert stk.get("double_high_exempt") is True, f"{s_name} double_high_exempt must be True"
                assert "金融" in stk.get("double_high_status", "") or "豁免" in stk.get("double_high_status", "")
                deductions = stk.get("deductions_detail", [])
                for d in deductions:
                    assert "存贷双高" not in d[0], f"{s_name} must have 0 deduction for double-high"
    assert found_banks >= 4, f"Found {found_banks} bank instances, expected >= 4"
    print(f"  -> PASS: {found_banks} bank instances verified: double_high_risk=False, deduction=0, status=exemption.")

def test_4_daily_limit_and_overlap_matrix():
    print("[Test 4] Daily limit split & overlap matrix exemption...")
    # Daily limit splitting: C3 allocation of 050025 with capital 100,000 is 6,000 > 500
    bp = StrategyBridge.generate_zero_start_blueprint(total_capital=100000.0, tier="C3")
    items = bp["items"]
    spx_primary = next((it for it in items if it["fund_code"] == "050025"), None)
    spx_fallback = next((it for it in items if it["fund_code"] == "001071"), None)
    assert spx_primary is not None, "050025 must be present"
    assert spx_fallback is not None, "001071 must be present"
    assert spx_primary["allocated_amount"] == 500.0
    assert spx_fallback["allocated_amount"] == 5500.0
    assert spx_primary["has_split"] is True
    assert spx_fallback["has_split"] is True

    # Overlap matrix test
    pm = PortfolioManager()
    pm.holdings.clear()
    pm.takeover_mode_a([
        {"fund_code": "050025", "fund_name": "博时标普500ETF联接A", "shares": 500.0, "cost_nav": 1.0, "share_class": "A", "first_buy_date": "2024-01-01"},
        {"fund_code": "001071", "fund_name": "摩根标普500指数(QDII)人民币A", "shares": 5500.0, "cost_nav": 1.0, "share_class": "A", "first_buy_date": "2024-01-01"}
    ], available_cash=0.0)
    mat_res = pm.calculate_stock_overlap_matrix()
    for a in mat_res.get("alerts", []):
        assert {a.get("fund1"), a.get("fund2")} != {"050025", "001071"}, "050025 & 001071 must NOT trigger alert"
    exempt_pairs = mat_res.get("exempt_pairs", [])
    assert any({p.get("fund1"), p.get("fund2")} == {"050025", "001071"} for p in exempt_pairs)

    # Adversarial check: non-exempt pair 011612 & 013841 MUST trigger alert
    pm_adv = PortfolioManager()
    pm_adv.holdings.clear()
    pm_adv.takeover_mode_a([
        {"fund_code": "011612", "fund_name": "华夏科创50A", "shares": 10000.0, "cost_nav": 1.0, "share_class": "A", "first_buy_date": "2024-01-01"},
        {"fund_code": "013841", "fund_name": "银华芯片C", "shares": 10000.0, "cost_nav": 1.0, "share_class": "C", "first_buy_date": "2024-01-01"}
    ], available_cash=0.0)
    adv_res = pm_adv.calculate_stock_overlap_matrix()
    assert any({a.get("fund1"), a.get("fund2")} == {"011612", "013841"} for a in adv_res.get("alerts", []))
    print("  -> PASS: 050025 split into 500 + 5500, overlap matrix exempted without false alert, adversarial pair triggers alert.")

def test_5_ui_layout_specs():
    print("[Test 5] UI layout & table specs...")
    gui_file = AGY2_DIR / "app_gui.py"
    content = gui_file.read_text(encoding="utf-8")
    import re
    cols_match = re.search(r"cols_9\s*=\s*\[(.*?)\]", content, re.DOTALL)
    assert cols_match is not None
    cols = [c.strip().strip('"').strip("'") for c in re.findall(r'["\'](.*?)["\']', cols_match.group(1))]
    assert len(cols) == 9
    expected = [
        "基金代码", "基金名称", "份额", "目标占比(%)",
        "精确买入金额(元)", "最新净值", "实时估值涨跌(%)",
        "排雷与拥挤度", "实操分红与限购指引"
    ]
    assert cols == expected, f"Columns mismatch: {cols}"
    assert re.search(r'st\.expander\(.*五大人话硬核指标.*expanded\s*=\s*False', content) is not None
    assert re.search(r'st\.expander\(exp_funnel_title,\s*expanded\s*=\s*False\)', content) is not None
    assert re.search(r'st\.expander\(.*一键复制小抄.*expanded\s*=\s*False', content) is not None
    assert re.search(r'st\.expander\(.*FIFO.*expanded\s*=\s*False', content) is not None
    print("  -> PASS: 9 columns verified on step 3 table, 4 key expanders default expanded=False.")

def test_6_readonly_infra_files():
    print("[Test 6] 4 read-only infrastructure files check...")
    expected_hashes = {
        "judge_engine.py": "76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF31CC07BE",
        "holdout_vault.py": "88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670BD031D2A",
        "AGENT_SPEC.md": "A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B800CD63957",
        "tests/test_infra.py": "B8D781BE8135BE05CF61E62E4B534E359985AD880F27FFB61228A33DF6B02A6A"
    }
    for rel_path, exp_hash in expected_hashes.items():
        file_path = AGY2_DIR / rel_path
        assert file_path.exists(), f"File {file_path} missing!"
        hasher = hashlib.sha256()
        hasher.update(file_path.read_bytes())
        calc_hash = hasher.hexdigest().upper()
        assert calc_hash == exp_hash, f"Hash mismatch for {rel_path}: {calc_hash} != {exp_hash}"
    print("  -> PASS: All 4 infrastructure files 100% untouched with identical SHA-256 hashes.")

if __name__ == "__main__":
    test_1_slider_linkage()
    test_2_account_drawdown_reset()
    test_3_bank_double_high_exemption()
    test_4_daily_limit_and_overlap_matrix()
    test_5_ui_layout_specs()
    test_6_readonly_infra_files()
    print("\nALL 6 INDEPENDENT ADVERSARIAL AUDIT CHECKS PASSED 100%!")
