import sys
import os

from strategy_bridge import (
    StrategyBridge,
    get_latest_market_snapshot,
    get_fund_selection_funnel_stats,
    calculate_fund_six_dimension_score,
    get_tier_quant_selection_table,
    get_tier_sector_fund_selection,
    generate_zero_start_blueprint,
    map_target_return_to_tier,
    TIER_TARGET_WEIGHTS,
)

print("=== 1. Checking Market Snapshot Derivatives Fields ===")
snap = get_latest_market_snapshot(force_reload=True)
assert "ic_annualized_basis_rate" in snap, "Missing ic_annualized_basis_rate"
assert "im_annualized_basis_rate" in snap, "Missing im_annualized_basis_rate"
assert "option_iv_pct" in snap, "Missing option_iv_pct"
assert "derivatives_sentiment" in snap, "Missing derivatives_sentiment"
print("IC Basis:", snap["ic_annualized_basis_rate"], "%")
print("IM Basis:", snap["im_annualized_basis_rate"], "%")
print("Option IV:", snap["option_iv_pct"], "%")
print("Derivatives Sentiment:", snap["derivatives_sentiment"])
print("Derivatives Radar Tip:", snap.get("derivatives_radar_tip"))
print("Advisory Takeaway:", snap.get("advisory_takeaway"))
print("Dual Track Radar:", snap.get("dual_track_radar"))
assert "衍生品面" in snap.get("advisory_takeaway", ""), "Snapshot takeaway missing derivatives"
radar = snap.get("dual_track_radar", {})
assert "ic_annualized_basis_rate" in radar, "Radar missing ic_annualized_basis_rate"
assert "derivatives_sentiment" in radar, "Radar missing derivatives_sentiment"
print("Snapshot verification: PASS")

print("\n=== 2. Checking Funnel Stats for C1-C5 ===")
for tier in ["C1", "C2", "C3", "C4", "C5"]:
    stats = get_fund_selection_funnel_stats(tier)
    assert stats["total_market_funds"] == 28177, f"total market funds != 28177: {stats}"
    assert stats["compliance_screened_funds"] == 6850, f"compliance != 6850: {stats}"
    assert stats["tier_candidate_funds"] >= 4, f"tier candidate funds < 4: {stats}"
    assert stats["final_portfolio_funds"] >= 4, f"final portfolio funds < 4: {stats}"
    print(f"Tier {tier}: total={stats['total_market_funds']}, compliance={stats['compliance_screened_funds']}, candidate={stats['tier_candidate_funds']}, final={stats['final_portfolio_funds']}")
print("Funnel stats verification: PASS")

print("\n=== 3. Checking Six-Dimension Scoring ===")
for code in ["002351", "100032", "011613", "050025"]:
    score = calculate_fund_six_dimension_score(code, tier="C3")
    assert 0 <= score["total_score"] <= 100, f"Score out of bounds: {score}"
    assert "alpha_score" in score and "fee_score" in score and "risk_score" in score
    assert "smart_money_score" in score and "anti_crowding_score" in score and "macro_derivative_score" in score
    print(f"Fund {code} total={score['total_score']}, alpha={score['alpha_score']}, fee={score['fee_score']}, deriv={score['macro_derivative_score']}")
print("Six-dimension scoring verification: PASS")

print("\n=== 4. Checking Quant Selection Table for C1-C5 ===")
for tier in ["C1", "C2", "C3", "C4", "C5"]:
    df = get_tier_quant_selection_table(tier)
    assert len(df) >= 4, f"Table too small for {tier}: {len(df)}"
    assert "赛道" in df.columns and "六维总评得分" in df.columns and "是否当前配置" in df.columns
    champions = df[df["是否当前配置"].str.contains("已配置")]
    assert len(champions) >= 4, f"Not enough champions in {tier}: {len(champions)}"
    print(f"Tier {tier} Table rows={len(df)}, champions={len(champions)}")
print("Quant selection table verification: PASS")

print("\n=== 5. Checking Zero Start Blueprint & Split ===")
bp = generate_zero_start_blueprint(total_capital=100000.0, tier="C3")
items = bp["items"]
print(f"C3 Blueprint items count: {len(items)}")
codes = [it["fund_code"] for it in items]
print(f"Funds in blueprint: {codes}")
assert "050025" in codes, "050025 not in blueprint"
assert "001071" in codes, "001071 not in blueprint for excess split"
it_050025 = next(it for it in items if it["fund_code"] == "050025")
it_001071 = next(it for it in items if it["fund_code"] == "001071")
print(f"050025 amount: {it_050025['amount']}, 001071 amount: {it_001071['amount']}")
assert it_050025["amount"] == 500.0, f"050025 amount not capped at 500: {it_050025['amount']}"
assert it_001071["amount"] == 5500.0, f"001071 amount not 5500: {it_001071['amount']}"
total_amt = sum(it["amount"] for it in items)
assert abs(total_amt - 100000.0) < 1.0, f"Total blueprint sum mismatch: {total_amt}"
print("Zero start blueprint split verification: PASS")

print("\n=== 6. Checking Target Returns & Weights Alignment ===")
assert map_target_return_to_tier(6.0) == "C1"
assert map_target_return_to_tier(8.0) == "C2"
assert map_target_return_to_tier(12.0) == "C3"
assert map_target_return_to_tier(20.0) == "C4"
assert map_target_return_to_tier(40.0) == "C5"
for tier in ["C1", "C2", "C3", "C4", "C5"]:
    w = StrategyBridge.get_tier_target_weights(tier)
    total_w = sum(w.values())
    assert abs(total_w - 1.0) < 1e-4, f"Weights sum {total_w} != 1.0 for {tier}"
    print(f"Tier {tier} Weights:", w)

print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")
