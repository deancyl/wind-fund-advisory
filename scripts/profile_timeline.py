import sys
import time
import importlib
from pathlib import Path

sys.path.insert(0, str(Path("AGY2_FundAdvisory").resolve()))
from streamlit.testing.v1 import AppTest

start_time = time.time()
timeline = []

def record(tag, duration=None):
    elapsed = time.time() - start_time
    if duration is not None:
        msg = f"[{elapsed:6.2f}s] {tag} (cost: {duration:6.2f}s)"
    else:
        msg = f"[{elapsed:6.2f}s] {tag}"
    timeline.append(msg)
    print(msg, flush=True)

patches = [
    ("strategy_bridge", "StrategyBridge", "get_latest_market_snapshot"),
    ("strategy_bridge", "StrategyBridge", "compute_n_funds_model_portfolio"),
    ("strategy_bridge", "StrategyBridge", "generate_zero_start_blueprint"),
    ("strategy_bridge", "StrategyBridge", "build_custom_portfolio_backtest"),
    ("strategy_bridge", "StrategyBridge", "find_historical_analogs"),
    ("strategy_bridge", "StrategyBridge", "run_historical_time_machine_backtest"),
    ("portfolio_manager", "PortfolioManager", "build_custom_portfolio_backtest"),
    ("portfolio_manager", "PortfolioManager", "get_portfolio_look_through_stocks_df"),
    ("portfolio_manager", "PortfolioManager", "calculate_dynamic_correlation_matrix"),
    ("portfolio_manager", "PortfolioManager", "calculate_intraday_pnl"),
    ("portfolio_manager", "PortfolioManager", "screen_fund_look_through_risk"),
    ("portfolio_manager", "PortfolioManager", "get_fund_smart_money_crowding"),
    ("portfolio_manager", "PortfolioManager", "get_portfolio_industry_exposure"),
    ("portfolio_manager", "PortfolioManager", "calculate_portfolio_penetration_risk"),
    ("portfolio_manager", "PortfolioManager", "get_stock_overlap_matrix"),
    ("portfolio_manager", "PortfolioManager", "simulate_portfolio_cvar_bootstrap_instance"),
    ("portfolio_manager", "PortfolioManager", "evaluate_dynamic_correlation_mutation_instance"),
    ("advisory_engine", "OpportunityRadarEngine", "scan_all_sectors"),
    ("advisory_engine", "ActiveRiskSentry", "inspect_portfolio"),
    ("advisory_engine", None, "generate_chief_advisor_memo"),
    ("portfolio_manager", None, "simulate_portfolio_cvar_bootstrap"),
]

def apply_all_patches():
    for mod_name, cls_name, func_name in patches:
        if mod_name in sys.modules:
            mod = sys.modules[mod_name]
            target = getattr(mod, cls_name) if cls_name else mod
            orig = getattr(target, func_name, None)
            if orig and not getattr(orig, "_is_patched", False):
                def make_wrapper(fn, t_name, f_name):
                    def wrapper(*args, **kwargs):
                        t0 = time.time()
                        record(f"--> ENTER {t_name}.{f_name}")
                        try:
                            return fn(*args, **kwargs)
                        finally:
                            record(f"<-- EXIT  {t_name}.{f_name}", duration=time.time() - t0)
                    wrapper._is_patched = True
                    return wrapper
                setattr(target, func_name, make_wrapper(orig, target.__name__ if hasattr(target, "__name__") else str(target), func_name))

_orig_reload = importlib.reload
def _hooked_reload(m):
    res = _orig_reload(m)
    apply_all_patches()
    return res
importlib.reload = _hooked_reload

apply_all_patches()

record("Starting AppTest...")
app_path = (Path("AGY2_FundAdvisory") / "app_gui.py").resolve()
at = AppTest.from_file(str(app_path), default_timeout=120)
try:
    at.run()
    record("AppTest run finished successfully!")
except Exception as e:
    record(f"AppTest run failed with {type(e).__name__}: {e}")

print("\n=== SUMMARY TIMELINE ===")
for line in timeline:
    print(line)
