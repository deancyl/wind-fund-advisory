# -*- coding: utf-8 -*-
import sys
from pathlib import Path
import numpy as np
import pandas as pd

WORKSPACE_ROOT = Path("d:/Google/Workspace/Wind")
sys.path.insert(0, str(WORKSPACE_ROOT))
sys.path.insert(0, str(WORKSPACE_ROOT / "AGY2_FundAdvisory"))

from strategy_bridge import StrategyBridge
from portfolio_optimizer import QUANT_MODELS_CATALOG, WinRateOptimizer, recommend_model_for_regime, simulate_black_swan_stress

print(f"QUANT_MODELS_CATALOG total entries: {len(QUANT_MODELS_CATALOG)}", flush=True)

models_to_test = [
    "hrp_robust",
    "core_satellite",
    "all_weather",
    "black_litterman",
    "conditional_winrate",
    "cvar_tail",
    "kelly_momentum",
]

print("\nTesting compute_n_funds_model_portfolio for 7 primary models...", flush=True)
for m in models_to_test:
    res = StrategyBridge.compute_n_funds_model_portfolio(
        tier="C3",
        target_return_pct=15.0,
        num_funds=6,
        model_type=m,
        capital=100000.0
    )
    opt_w = res.get("optimal_weights", {})
    assert len(opt_w) == 6, f"Model {m} produced {len(opt_w)} weights, expected 6"
    w_sum = sum(opt_w.values())
    diff = abs(w_sum - 1.0)
    assert diff < 1e-6, f"Model {m} weight sum {w_sum} != 1.0 (diff={diff})"
    assert all(w >= 0.0 for w in opt_w.values()), f"Model {m} has negative weight: {opt_w}"
    std_val = np.std(list(opt_w.values()))
    assert std_val > 0.005, f"Model {m} collapsed to equal weights (std={std_val})"
    print(f"  PASS: {m} -> sum={w_sum:.8f}, std={std_val:.4f}, funds={list(opt_w.keys())}", flush=True)

print("\nTesting macro regime recommendation...", flush=True)
rec = recommend_model_for_regime({"erp_percentile": 80.0, "bias_20": 1.5, "dr007_7d_ma": 1.6, "ivix_index": 16.0}, target_return_pct=20.0)
print(f"  Recommended for breakout: {rec['recommended_model_name']} ({rec['recommended_model_key']})", flush=True)
assert rec['recommended_model_key'] == 'kelly_momentum'

rec2 = recommend_model_for_regime({"erp_percentile": 20.0, "bias_20": -3.5, "dr007_7d_ma": 2.2, "ivix_index": 28.0}, target_return_pct=10.0)
print(f"  Recommended for high vol defense: {rec2['recommended_model_name']} ({rec2['recommended_model_key']})", flush=True)
assert rec2['recommended_model_key'] == 'cvar_tail'

rec3 = recommend_model_for_regime({"erp_percentile": 70.0, "bias_20": 0.5, "dr007_7d_ma": 1.6, "ivix_index": 16.0}, target_return_pct=8.0)
print(f"  Recommended for conservative: {rec3['recommended_model_name']} ({rec3['recommended_model_key']})", flush=True)
assert rec3['recommended_model_key'] == 'core_satellite'

rec4 = recommend_model_for_regime({"erp_percentile": 45.0, "bias_20": 3.5, "dr007_7d_ma": 1.8, "ivix_index": 23.0}, target_return_pct=12.0)
print(f"  Recommended for all-weather: {rec4['recommended_model_name']} ({rec4['recommended_model_key']})", flush=True)
assert rec4['recommended_model_key'] == 'all_weather'

rec5 = recommend_model_for_regime({"erp_percentile": 55.0, "bias_20": 1.0, "dr007_7d_ma": 1.7, "ivix_index": 18.0, "market_state": "结构分化轮动期", "er_snr": 0.70}, target_return_pct=12.0)
print(f"  Recommended for BL views: {rec5['recommended_model_name']} ({rec5['recommended_model_key']})", flush=True)
assert rec5['recommended_model_key'] == 'black_litterman'

rec6 = recommend_model_for_regime({"erp_percentile": 68.0, "bias_20": 0.8, "dr007_7d_ma": 1.6, "ivix_index": 18.0, "market_state": "高性价比磨底期"}, target_return_pct=12.0)
print(f"  Recommended for HRP: {rec6['recommended_model_name']} ({rec6['recommended_model_key']})", flush=True)
assert rec6['recommended_model_key'] == 'hrp_robust'

rec7 = recommend_model_for_regime({"erp_percentile": 52.0, "bias_20": 0.5, "dr007_7d_ma": 1.7, "ivix_index": 18.0, "market_state": "震荡市"}, target_return_pct=12.0)
print(f"  Recommended for Conditional WinRate: {rec7['recommended_model_name']} ({rec7['recommended_model_key']})", flush=True)
assert rec7['recommended_model_key'] == 'conditional_winrate'

print("\nTesting simulate_black_swan_stress...", flush=True)
stress_res = simulate_black_swan_stress({"005561": 0.35, "100032": 0.20, "000216": 0.20, "017436": 0.15, "011613": 0.10})
assert len(stress_res["scenarios"]) == 3
for sc in stress_res["scenarios"]:
    print(f"  Scenario: {sc['name']} | MaxDD: -{sc['max_dd_pct']}% | Loss: -¥{sc['max_loss_amt']} | Recovery: {sc['recovery_str']} | Excess: +{sc['excess_defense_pct']}%", flush=True)
    assert sc["max_dd_pct"] > 0
    assert sc["max_loss_amt"] > 0
    assert sc["recovery_str"] != ""

print("\nALL 7 INSTITUTIONAL MODELS, MACRO ROUTING AND BLACK SWAN STRESS TEST FULLY VERIFIED!", flush=True)
