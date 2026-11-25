import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
AGY2_DIR = ROOT_DIR / "AGY2_FundAdvisory"
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(AGY2_DIR))

from strategy_bridge import StrategyBridge

snap = StrategyBridge.get_latest_market_snapshot(force_reload=False, auto_sync=False) or {}
for k, v in snap.items():
    if any(idx in k.lower() for idx in ["300", "50", "hldb", "chg", "close", "price", "regime", "verdict", "pnl"]):
        print(f"{k}: {v}")
