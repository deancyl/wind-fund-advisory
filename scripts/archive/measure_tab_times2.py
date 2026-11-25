import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path("AGY2_FundAdvisory").resolve()))
from portfolio_manager import MultiLedgerManager, PortfolioManager
from strategy_bridge import StrategyBridge

mlm = MultiLedgerManager.get_instance()
pm = mlm.get_pm("combat_29_funds")
snapshot = StrategyBridge.get_latest_market_snapshot(force_reload=False, auto_sync=False) or {}

from app_gui import render_tab3_backtest_content, render_tab4_toolbox_content

print("Measuring render_tab3_backtest_content...")
t0 = time.time()
try:
    # 模拟 Streamlit 运行环境下或直接调用
    print(f"render_tab3 took {time.time()-t0:.2f}s")
except Exception as e:
    print("Tab3 error:", e)
