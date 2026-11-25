import sys
from pathlib import Path
sys.path.insert(0, str(Path("AGY2_FundAdvisory").resolve()))
import time
from portfolio_manager import PortfolioManager

pm = PortfolioManager()
print(f"Holdings count: {len(pm.holdings)}")

t0 = time.time()
r1 = pm.calculate_look_through_industry_exposure()
t1 = time.time()
print(f"calculate_look_through_industry_exposure: {t1 - t0:.3f}s")

r2 = pm.calculate_stock_overlap_matrix()
t2 = time.time()
print(f"calculate_stock_overlap_matrix: {t2 - t1:.3f}s")

r3 = pm.calculate_portfolio_penetration_risk()
t3 = time.time()
print(f"calculate_portfolio_penetration_risk: {t3 - t2:.3f}s")

r4 = pm.get_portfolio_look_through_stocks_df()
t4 = time.time()
print(f"get_portfolio_look_through_stocks_df: {t4 - t3:.3f}s")

r5 = pm.evaluate_dynamic_correlation_mutation_instance(threshold=0.75)
t5 = time.time()
print(f"evaluate_dynamic_correlation_mutation_instance: {t5 - t4:.3f}s")

r6 = pm.simulate_portfolio_cvar_bootstrap_instance(total_capital=100000.0, investor_risk_tier="C3", n_simulations=500)
t6 = time.time()
print(f"simulate_portfolio_cvar_bootstrap_instance: {t6 - t5:.3f}s")
