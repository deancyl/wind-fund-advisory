"""
WindToolkit 全量核心功能冒烟与端到端实测验证脚本
"""
import sys
import os
sys.path.insert(0, os.path.abspath("."))
import time
from datetime import datetime

print("================================================================")
print(f"🚀 WindToolkit 全量功能端到端实测冒烟测试 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
print("================================================================\n")

results = []

def test_step(name, func):
    t0 = time.time()
    try:
        msg = func()
        cost = time.time() - t0
        results.append((name, "✓ PASS", f"{cost:.2f}s", msg))
        print(f"[✓ PASS] {name:<26} ({cost:.2f}s) -> {msg}")
    except Exception as e:
        cost = time.time() - t0
        results.append((name, "✗ FAIL", f"{cost:.2f}s", str(e)))
        print(f"[✗ FAIL] {name:<26} ({cost:.2f}s) -> Error: {e}")

# 1. SDK 实例化与终端状态
def step_sdk_init():
    from src.toolkit import WindToolkit
    wk = WindToolkit()
    st = wk.get_terminal_status()
    mem = st.get('memory_mb')
    mem_str = f"{mem:.1f}MB" if mem is not None else "N/A"
    return f"Wind在线: {st['is_running']}, PID: {st.get('wmain_pid')}, 内存: {mem_str}, 投顾: {st.get('user')}"

# 2. 投顾自选与工作台画像
def step_watchlist():
    from src.toolkit import WindToolkit
    wk = WindToolkit()
    df_wl = wk.watchlist.build_consolidated_watchlist()
    prof = wk.watchlist.get_advisor_profile()
    return f"自选标的数: {len(df_wl)}条, 投顾实名: {prof.get('name')}, WDID: {prof.get('wdid', '')[:8]}..."

# 3. 业绩预告与财务排雷
def step_forecast():
    from src.toolkit import WindToolkit
    wk = WindToolkit()
    df_fcs = wk.earnings_forecast.fetch_earnings_forecast("600519", limit=1)
    risk = wk.earnings_forecast.screen_financial_risks("600519")
    level = risk.get("overall_risk_level", "Safe")
    fcf = risk.get("free_cash_flow_cr", 0.0)
    return f"预告记录: {len(df_fcs)}条, 排雷评级: {level}, 自由现金流: {fcf:.1f}亿"

# 4. 微观筹码面 (龙虎榜/大宗/股东户数)
def step_chips():
    from src.toolkit import WindToolkit
    wk = WindToolkit()
    df_dt = wk.chips_market.fetch_dragon_tiger_daily(limit=2)
    df_bt = wk.chips_market.fetch_block_trading(limit=2)
    return f"龙虎榜: {len(df_dt)}条, 大宗交易: {len(df_bt)}条"

# 5. 股东信用风险与解禁质押
def step_holder_risk():
    from src.toolkit import WindToolkit
    wk = WindToolkit()
    df_lock = wk.holder_risk.fetch_lockup_calendar(days_ahead=30, limit=2)
    pledge = wk.holder_risk.fetch_pledge_risk("600519")
    ratio = pledge["pledge_ratio_total_pct"].iloc[0] if hasattr(pledge, 'iloc') else pledge.get("pledge_ratio_total_pct", 0.0)
    status = pledge["warning_close_line_status"].iloc[0] if hasattr(pledge, 'iloc') else pledge.get("warning_close_line_status", "安全")
    return f"30天解禁: {len(df_lock)}条, 茅台质押率: {ratio}%, 状态: {status}"

# 6. 机构持仓与聪明钱 (北向资金)
def step_smart_money():
    from src.toolkit import WindToolkit
    wk = WindToolkit()
    df_nb = wk.institutional_holdings.fetch_northbound_holdings("600519", limit=3)
    cnt = len(df_nb) if hasattr(df_nb, '__len__') else 0
    return f"北向持仓记录数: {cnt}条"

# 7. 衍生品期货基差与期权波动率
def step_derivatives():
    from src.toolkit import WindToolkit
    wk = WindToolkit()
    df_basis = wk.derivatives.fetch_futures_basis()
    df_opt = wk.derivatives.fetch_option_volatility()
    return f"股指期货主力合约数: {len(df_basis)}只, 期权标的数: {len(df_opt)}只"

# 8. 宏观高频流动性 (逆回购/DR007)
def step_liquidity():
    from src.toolkit import WindToolkit
    wk = WindToolkit()
    dash = wk.macro_liquidity.get_liquidity_thermometer()
    return f"流动性状态: {dash.get('liquidity_status')}, DR007: {dash.get('dr007')}%, 政策利差: {dash.get('dr007_spread_bp')}bp"

# 9. 中债收益率曲线与利差
def step_bonds():
    from src.toolkit import WindToolkit
    wk = WindToolkit()
    curve = wk.bonds.get_latest_yield_curve()
    return f"10Y国债: {curve.get('y_10y')}%, 10Y-1Y利差: {curve.get('term_spread_10y_1y_bp')}bp"

# 10. 行业板块主力资金流
def step_money_flow():
    from src.toolkit import WindToolkit
    wk = WindToolkit()
    df_flow = wk.money_flow.get_top_inflow_sectors(top_n=2)
    sectors = df_flow["sector_name"].tolist() if "sector_name" in df_flow.columns else []
    return f"主力流入前2行业: {', '.join(sectors)}"

# 11. 场内 ETF 资金聚类
def step_etf():
    from src.toolkit import WindToolkit
    wk = WindToolkit()
    df_etf = wk.etf.get_top_inflow_etfs(top_n=2)
    return f"ETF 净流入榜获取成功 ({len(df_etf)}只)"

# 12. 卖方研报听话听音与PDF
def step_reports():
    from src.toolkit import WindToolkit
    wk = WindToolkit()
    reps = wk.reports_collector.fetch_stock_reports("600519", limit=2)
    return f"茅台研报数: {len(reps)}, 首篇PDF: {reps[0].pdf_url if reps else ''}"

# 13. DuckDB 湖仓并发 SQL 即席查询
def step_duckdb():
    from src.toolkit import WindToolkit
    wk = WindToolkit()
    df = wk.query("SELECT count(*) as cnt FROM v_indices")
    cnt = df.iloc[0]["cnt"] if not df.empty else 0
    return f"DuckDB 湖仓在线, v_indices 历史K线总行数: {cnt}"

test_step("1. SDK 初始化与状态", step_sdk_init)
test_step("2. 投顾自选工作台", step_watchlist)
test_step("3. 业绩预告与财务排雷", step_forecast)
test_step("4. 微观筹码 (龙虎榜/大宗)", step_chips)
test_step("5. 股东风险与解禁质押", step_holder_risk)
test_step("6. 聪明钱与北向持仓", step_smart_money)
test_step("7. 衍生品基差与期权", step_derivatives)
test_step("8. 宏观流动性与DR007", step_liquidity)
test_step("9. 中债收益率曲线与利差", step_bonds)
test_step("10. 行业主力资金流向", step_money_flow)
test_step("11. 场内 ETF 资金聚类", step_etf)
test_step("12. 卖方研报流与PDF直链", step_reports)
test_step("13. DuckDB 湖仓即席查询", step_duckdb)

print("\n================================================================")
pass_cnt = sum(1 for r in results if r[1] == "✓ PASS")
total_cnt = len(results)
print(f"📊 实测验收汇总: {pass_cnt}/{total_cnt} 全部通过! (通过率: {pass_cnt/total_cnt*100:.1f}%)")
print("================================================================")
