import sys
from pathlib import Path
ws = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ws / "AGY2_FundAdvisory"))
sys.path.insert(0, str(ws))

from strategy_bridge import StrategyBridge
from advisory_engine import SmartExecutionDCAEngine

snap = StrategyBridge.get_latest_market_snapshot()
print("Current Market Snapshot:")
print("  erp_percentile:", snap.get("erp_percentile"))
print("  bias_20:", snap.get("bias_20"))
print("  pe_ttm_300:", snap.get("pe_ttm_300"))
print("  treasury_10y:", snap.get("treasury_10y"))
print("  market_state:", snap.get("market_state"))

# Current Smart DCA
alloc = [{"code": "005561", "name": "创金合信红利低波A", "weight": 0.5}, {"code": "510300", "name": "沪深300ETF", "weight": 0.5}]
dca_now = SmartExecutionDCAEngine.plan_smart_dca(
    total_capital=100000.0,
    allocations=alloc,
    erp_percentile=snap.get("erp_percentile", 81.9),
    bias_20=snap.get("bias_20", 0.0),
    periods=12
)
print("Current DCA:")
print("  multiplier:", dca_now["multiplier"])
print("  multiplier_tag:", dca_now["multiplier_tag"])
print("  valuation_status:", dca_now["valuation_status"])

# Historical inflection signals
infl = SmartExecutionDCAEngine.verify_historical_inflection_signals()
print("\nHistorical Inflections:")
for k in ["2021_top", "2022_bottom", "2024_bottom"]:
    print(f"  {k}:", infl.get(k))
