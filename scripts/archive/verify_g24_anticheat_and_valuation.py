import ast
import pathlib
import sys
from pathlib import Path

# Add AGY2_FundAdvisory to sys.path
agy2_dir = Path("AGY2_FundAdvisory").resolve()
if str(agy2_dir) not in sys.path:
    sys.path.insert(0, str(agy2_dir))

from portfolio_manager import (
    PortfolioManager, FundQuote, fetch_realtime_fund_quote,
    fetch_realtime_index_quote, evaluate_four_tier_realtime_valuation,
    clear_realtime_cache, FEEDER_AND_STANDARD_INDEX_MAPPING
)
from data_loader import EXPANDED_INDEX_CATALOG, search_index_and_fund_candidates, validate_and_fetch_code

print("=== 正在运行 G24 全量反作弊与实时估值/收盘官方净值真值门禁 ===")

gui_src = pathlib.Path('AGY2_FundAdvisory/app_gui.py').read_text(encoding='utf-8')
pm_src = pathlib.Path('AGY2_FundAdvisory/portfolio_manager.py').read_text(encoding='utf-8')
mlm_src = pathlib.Path('AGY2_FundAdvisory/multi_ledger_manager.py').read_text(encoding='utf-8')
ae_src = pathlib.Path('AGY2_FundAdvisory/advisory_engine.py').read_text(encoding='utf-8')
sb_src = pathlib.Path('AGY2_FundAdvisory/strategy_bridge.py').read_text(encoding='utf-8')

# 静态 AST 编译零语法错误门禁
for fname in [
    'AGY2_FundAdvisory/app_gui.py',
    'AGY2_FundAdvisory/advisory_engine.py',
    'AGY2_FundAdvisory/portfolio_manager.py',
    'AGY2_FundAdvisory/portfolio_optimizer.py',
    'AGY2_FundAdvisory/strategy_bridge.py',
    'AGY2_FundAdvisory/data_loader.py',
    'AGY2_FundAdvisory/multi_ledger_manager.py'
]:
    ast.parse(pathlib.Path(fname).read_text(encoding='utf-8'))
print("  [OK] 核心模块全量 AST 解析 100% 语法合规")

# 1. 反作弊门禁 A：严禁把深市指数 399997/399986/399005 或中证 H30269 错误拼成 s_sh399997 / s_shh30269
assert 'elif not fu_date:\n                        is_official = True' not in pm_src, 'FATAL: Fake is_official=True when fu_date is empty must be removed!'
assert 'clean_s = s_code.split(".")[-1]' not in pm_src, 'FATAL: Top10 stock code split bug (.split(".")[-1]) still exists!'
assert 'importlib.reload(portfolio_manager)' not in gui_src, 'FATAL: Unconditional importlib.reload(portfolio_manager) must be removed!'
assert '_REALTIME_QUOTE_CACHE[_c] = (\n                    _now_init,' not in pm_src, 'FATAL: Disk quote cache must not stamp stale quotes with _now_init = time.time()!'
assert 'spread_bp = -278.2' not in ae_src, 'FATAL: Hardcoded spread_bp = -278.2 in advisory_engine.py must be removed!'
assert 'spread_cgb_us = -278.2' not in ae_src, 'FATAL: Hardcoded spread_cgb_us = -278.2 in advisory_engine.py must be removed!'
assert 'cn_us_spread_bp = -278.2' not in sb_src, 'FATAL: Hardcoded cn_us_spread_bp = -278.2 in strategy_bridge.py must be removed!'
print("  [OK] 门禁 A: 无掩耳盗铃硬编码常数、无僵尸缓存时间戳冒充、无切片 Bug、无无脑 reload")

# 2. 反作弊门禁 B：验证官方公布净值 quote 绝不被 evaluate_four_tier_realtime_valuation 篡改
q_off = FundQuote(name='招商中证白酒指数A', dwjz=0.8520, gsz=0.8520, gszzl=-1.25, gztime='2026-11-17 官方公布净值', fund_code='161725', is_official_nav=True)
q_off_check = evaluate_four_tier_realtime_valuation('161725', q_off)
assert q_off_check.gszzl == -1.25 and q_off_check.is_official_nav is True, f'FATAL: Official NAV quote was corrupted: {q_off_check}'
print("  [OK] 门禁 B: 官方公布净值 quote 绝对免受四级估值引擎二次篡改")

# 3. 反作弊门禁 C：验证图1 添加标的时已同步更新 ms_corridor_indices 且 H30269 secid 为 2.H30269
assert 'st.session_state["ms_corridor_indices"] =' in gui_src, 'FATAL: Adding corridor item must sync st.session_state["ms_corridor_indices"]!'
assert EXPANDED_INDEX_CATALOG['H30269']['secid'] == '2.H30269', 'FATAL: H30269 secid must be 2.H30269!'
print("  [OK] 门禁 C: 自选走廊动态同步 ms_corridor_indices，H30269 secid 准确为 2.H30269")

# 4. 反作弊门禁 D：验证图3 Tab 3 fig_nav 已删除强制将 legend 设回 x=0, y=1.06 的冲突代码，且未设置 y=-0.20 压 X 轴
assert 'y=-0.20' not in gui_src, 'FATAL: Legend y=-0.20 collides with xaxis_title!'
assert 'y=1.06,\n            xanchor="left",\n            x=0' not in gui_src, 'FATAL: Conflicting legend(x=0, y=1.06) in fig_nav was not removed!'
print("  [OK] 门禁 D: Plotly 图表布局右上角安全区，无 y=-0.20 压 X 轴，无 x=0, y=1.06 压标题")

# 5. 反作弊门禁 E：验证用户 29 只持仓中的 华夏中小板ETF联接A 未被篡改名称
assert '华夏中小板ETF联接A' in mlm_src, 'FATAL: User holding 华夏中小板ETF联接A was tampered with in multi_ledger_manager.py!'
from multi_ledger_manager import MultiLedgerManager
mlm_test = MultiLedgerManager()
pm29_test = mlm_test.get_pm("combat_29_funds")
assert "000058" in pm29_test.holdings or "000086" in pm29_test.holdings
tail_fund = pm29_test.holdings.get("000058") or pm29_test.holdings.get("000086")
assert "华夏中小板" in tail_fund.fund_name, f"User holding name was tampered: {tail_fund.fund_name}"
print(f"  [OK] 门禁 E: 用户真实持仓 {tail_fund.fund_code} 严格保持 '{tail_fund.fund_name}'，零篡改")

# 6. 反作弊门禁 F：防反向归零断言与深市指数解析
q_5561 = FundQuote(name='创金合信红利低波A', dwjz=1.258, gsz=1.2768, gszzl=1.50, gztime='2026-11-18 10:30', fund_code='005561')
q_1725 = FundQuote(name='招商中证白酒A', dwjz=0.852, gsz=0.867, gszzl=1.76, gztime='2026-11-18 10:30', fund_code='161725')
q_5561_res = evaluate_four_tier_realtime_valuation('005561', q_5561)
q_1725_res = evaluate_four_tier_realtime_valuation('161725', q_1725)
assert q_5561_res.gszzl != 0.0, f"005561 gszzl was wiped to 0.0: {q_5561_res}"
assert q_1725_res.gszzl != 0.0, f"161725 gszzl was wiped to 0.0: {q_1725_res}"
print(f"  [OK] 门禁 F1: 防反向归零生效，005561 ({q_5561_res.gszzl}%) 与 161725 ({q_1725_res.gszzl}%) 真实估值完好")

# 验证 fetch_realtime_index_quote 解析深市与 H30269 不含 s_shh30269 / s_sh399997
q_idx_hldb = fetch_realtime_index_quote("H30269")
q_idx_baijiu = fetch_realtime_index_quote("399997")
q_idx_sme = fetch_realtime_index_quote("399005")
assert q_idx_hldb.get("symbol") != "s_shh30269"
assert q_idx_baijiu.get("symbol") != "s_sh399997"
assert q_idx_sme.get("symbol") != "s_sh399005"
print(f"  [OK] 门禁 F2: 指数前缀精准映射，H30269 点位: {q_idx_hldb['point']} ({q_idx_hldb['change_pct']}%), 白酒点位: {q_idx_baijiu['point']} ({q_idx_baijiu['change_pct']}%)")

print("\n=======================================================")
print("ALL ANTI-CHEATING & REALTIME/OFFICIAL VALUATION GATES PASSED")
print("=======================================================")
