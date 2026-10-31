import sys
sys.path.insert(0, "AGY2_FundAdvisory")
from portfolio_manager import PortfolioManager
from strategy_bridge import StrategyBridge

pm = PortfolioManager()
# Add the exempt pairs: 100032 & 005561, 050025 & 001071
pm.takeover_mode_a(
    fund_items=[
        {"fund_code": "100032", "amount": 10000.0},
        {"fund_code": "005561", "amount": 10000.0},
        {"fund_code": "050025", "amount": 5000.0},
        {"fund_code": "001071", "amount": 5000.0},
    ],
    available_cash=10000.0
)

# Test suitability
suit = StrategyBridge.evaluate_today_rebalance_suitability(pm, active_tier="C3")
print("Suitability verdict:", suit["verdict_level"], suit["verdict_title"])
assert suit["verdict_level"] in ["SUITABLE", "HOLD_ON", "FORBIDDEN"]
assert set(suit["reasons_4d"].keys()) == {"market_position_reason", "clock_window_reason", "deviation_utility_reason", "lockup_fee_reason"}

# Test simulation
sim = StrategyBridge.simulate_rebalance_modes_and_consequences(pm, active_tier="C3")
assert "mode_gentle" in sim and "mode_forced" in sim
for m in ["mode_gentle", "mode_forced"]:
    cq = sim[m]["consequences"]
    assert set(cq.keys()) == {"fee_loss", "in_transit_risk", "risk_shift", "lockup_reset"}

# Test overlap matrix exemption
overlap_res = pm.calculate_stock_overlap_matrix()
print("Overlap matrix max_non_diag_unexcused:", overlap_res["max_non_diag_unexcused"])
print("Exempt pairs recorded:", overlap_res["exempt_pairs"])
assert overlap_res["max_non_diag_unexcused"] <= 0.40, f"Expected unexcused overlap <= 0.40, got {overlap_res['max_non_diag_unexcused']}"
assert len(overlap_res["exempt_pairs"]) >= 1, "Exempt pairs should contain 100032/005561 or 050025/001071"

print("R4 Suitability, Consequences, and Overlap Exemption VERIFIED!")
