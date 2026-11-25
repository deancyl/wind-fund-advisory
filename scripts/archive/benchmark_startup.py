import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path("AGY2_FundAdvisory").resolve()))

def bench(name, fn):
    t0 = time.time()
    try:
        res = fn()
        dt = time.time() - t0
        print(f"[{dt:6.2f}s] {name}")
        return res
    except Exception as e:
        dt = time.time() - t0
        print(f"[{dt:6.2f}s] {name} (FAILED: {e})")
        return None

t_total_0 = time.time()

# 1. 基础导入
t0 = time.time()
from data_loader import (
    DataLoader,
    fetch_realtime_market_news_and_catalysts,
    fetch_market_turnover_and_sentiment,
    fetch_or_calc_index_valuations,
    validate_and_fetch_code,
    fetch_custom_realtime_indices
)
from strategy_bridge import StrategyBridge
from portfolio_manager import MultiLedgerManager
from advisory_engine import ActiveRiskSentry, OpportunityRadarEngine, generate_chief_advisor_memo
print(f"[{time.time()-t0:6.2f}s] Base modules import")

# 2. MultiLedgerManager 初始化与获取活跃账本
mlm = bench("MultiLedgerManager.get_instance()", lambda: MultiLedgerManager.get_instance())
active_lid = mlm.get_active_ledger_id()
pm = bench(f"mlm.get_pm('{active_lid}')", lambda: mlm.get_pm(active_lid))

# 3. StrategyBridge 快照
snapshot = bench("StrategyBridge.get_latest_market_snapshot()", lambda: StrategyBridge.get_latest_market_snapshot(force_reload=False, auto_sync=False))

# 4. 盘中信号与网格
intraday_eval = bench("StrategyBridge.evaluate_intraday_signal()", lambda: StrategyBridge.evaluate_intraday_signal())
rebal_grid = bench("StrategyBridge.get_rebalance_grid_status()", lambda: StrategyBridge.get_rebalance_grid_status())

# 5. pm._recalculate_totals & calculate_intraday_pnl
bench("pm._recalculate_totals()", lambda: pm._recalculate_totals())
bench("pm.calculate_intraday_pnl()", lambda: pm.calculate_intraday_pnl())

# 6. 行情网关与走廊估值
bench("fetch_market_turnover_and_sentiment()", lambda: fetch_market_turnover_and_sentiment())
bench("fetch_custom_realtime_indices()", lambda: fetch_custom_realtime_indices(codes=["000300", "000905", "399006", "000922"], use_cache=True))
bench("fetch_or_calc_index_valuations()", lambda: fetch_or_calc_index_valuations(force_refresh=False))

# 7. ActiveRiskSentry
sentry_obj = ActiveRiskSentry()
bench("sentry_obj.inspect_portfolio()", lambda: sentry_obj.inspect_portfolio(pm, investor_risk_tier="C3", snapshot=snapshot))

# 8. OpportunityRadarEngine
radar_engine = bench("OpportunityRadarEngine() init", lambda: OpportunityRadarEngine())
bench("radar_engine.get_opportunity_ranking_matrix()", lambda: radar_engine.get_opportunity_ranking_matrix(top_k=3, force_refresh=False))

# 9. 首席备忘录生成
bench("generate_chief_advisor_memo()", lambda: generate_chief_advisor_memo(pm, snapshot=snapshot))

print(f"\nTOTAL PIPELINE TIME: {time.time() - t_total_0:.2f}s")
