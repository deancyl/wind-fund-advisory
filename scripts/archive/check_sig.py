import inspect
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
AGY2_DIR = ROOT_DIR / "AGY2_FundAdvisory"
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(AGY2_DIR))

from strategy_bridge import StrategyBridge

sig = inspect.signature(StrategyBridge.generate_ai_rebalance_orders)
print("Signature:", sig)
