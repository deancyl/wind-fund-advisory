import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
AGY2_DIR = ROOT_DIR / "AGY2_FundAdvisory"
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(AGY2_DIR))

from strategy_bridge import StrategyBridge

snap = StrategyBridge.get_latest_market_snapshot(force_reload=False, auto_sync=False) or {}
print("Snapshot keys:", list(snap.keys())[:30])
print("market_regime:", snap.get("market_regime"))
print("advisory_verdict:", snap.get("advisory_verdict"))
print("c300_price / c300:", snap.get("c300_price"), snap.get("c300"))
print("trigger_lines:", snap.get("trigger_lines"))
