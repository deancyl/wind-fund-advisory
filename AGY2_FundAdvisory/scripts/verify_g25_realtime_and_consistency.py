#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
G25 极速刷新、官方真值估值与调仓自洽终极门禁检验脚本 (verify_g25_realtime_and_consistency.py)
永久固化门禁 0、A、B、C、D、E 与性能 Benchmark，确保零作弊、零篡改、秒级响应。
"""

import ast
import time
import pathlib
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
agy2_dir = WORKSPACE_ROOT / "AGY2_FundAdvisory"
if agy2_dir.exists() and str(agy2_dir) not in sys.path:
    sys.path.insert(0, str(agy2_dir))

import portfolio_manager
from portfolio_manager import (
    PortfolioManager, FundQuote, fetch_realtime_fund_quote,
    prefetch_batch_fund_quotes, evaluate_four_tier_realtime_valuation,
    _apply_fund_valuation_calibration, clear_realtime_cache,
    FEEDER_AND_STANDARD_INDEX_MAPPING, BOND_SOLID_CODES
)
from multi_ledger_manager import MultiLedgerManager
from strategy_bridge import StrategyBridge

print("=== 正在运行 G25 极速刷新、官方真值估值与调仓自洽终极门禁 ===")

# -------------------------------------------------------------
# 0. 门禁 0：核心模块全量 AST 静态编译 100% 语法合规
# -------------------------------------------------------------
core_files = [
    'app_gui.py', 'advisory_engine.py', 'portfolio_manager.py',
    'portfolio_optimizer.py', 'strategy_bridge.py', 'data_loader.py', 'multi_ledger_manager.py'
]
for f in core_files:
    p = agy2_dir / f
    assert p.exists(), f"Core file missing: {p}"
    ast.parse(p.read_text(encoding='utf-8'))
print("  [OK] 门禁 0: 7 大核心模块 AST 解析 100% 语法合规")

gui_path = agy2_dir / 'app_gui.py'
gui_src = gui_path.read_text(encoding='utf-8')
gemini_md = (WORKSPACE_ROOT / 'GEMINI.md').read_text(encoding='utf-8')

# -------------------------------------------------------------
# 0.5 门禁 0.5：验证 GEMINI.md 已更新为保护官方真实估值的 v6.0 宪法规范
# -------------------------------------------------------------
assert 'real_tiantian_live' in gemini_md and 'Official NAV Supremacy' in gemini_md, 'FATAL: GEMINI.md was not updated to v6.0!'
print("  [OK] 门禁 0.5: 工作区根目录 GEMINI.md 已升级为 v6.0 工程宪法")

# -------------------------------------------------------------
# 1. 门禁 A：验证刷新按钮杜绝慢速 PE 爬虫阻塞，且实装批量拉取 prefetch_batch_fund_quotes
# -------------------------------------------------------------
assert 'fetch_or_calc_index_valuations(force_refresh=True)' not in gui_src, 'FATAL: force_refresh=True on index valuations blocks UI with slow akshare scraping!'
assert hasattr(portfolio_manager, 'prefetch_batch_fund_quotes'), 'FATAL: prefetch_batch_fund_quotes batch API is missing!'
assert 'StrategyBridge._cached_matrix = None' not in gui_src, 'FATAL: Matrix cache destroying in refresh callback must be removed!'
assert '_APP_VOL_BIAS_MEM_CACHE' in gui_src, 'FATAL: _APP_VOL_BIAS_MEM_CACHE memoization is missing in app_gui.py!'
print("  [OK] 门禁 A: 极速刷新按钮消除历史PE爬虫与全量矩阵重载，实现批量秒级拉取")

# -------------------------------------------------------------
# 2. 门禁 B：验证来自东财/天天基金的真实盘中估值 (real_tiantian_live=True) 绝对免受二次篡改
# -------------------------------------------------------------
for code_t, true_chg in [('002351', -0.18), ('005561', 0.42), ('110020', -0.25), ('017436', -0.65), ('161725', -1.12)]:
    q_true = FundQuote(name=f'测试_{code_t}', dwjz=1.5, gsz=round(1.5 * (1 + true_chg / 100.0), 4), gszzl=true_chg, gztime='2026-11-18 10:30', fund_code=code_t)
    q_true['real_tiantian_live'] = True
    q_a4 = evaluate_four_tier_realtime_valuation(code_t, q_true)
    q_ac = _apply_fund_valuation_calibration(q_true)
    assert q_a4.gszzl == true_chg, f'FATAL: {code_t} true valuation {true_chg}% was overwritten by 4-tier: {q_a4.gszzl}%!'
    assert q_ac.gszzl == true_chg, f'FATAL: {code_t} true valuation {true_chg}% was overwritten by calibration: {q_ac.gszzl}%!'
assert '002351' not in BOND_SOLID_CODES, 'FATAL: 002351 is secondary bond fund, must not be in BOND_SOLID_CODES!'
assert '002352' not in BOND_SOLID_CODES, 'FATAL: 002352 is secondary bond fund, must not be in BOND_SOLID_CODES!'
assert FEEDER_AND_STANDARD_INDEX_MAPPING.get('005561') == 'H30269', 'FATAL: 005561 must map to H30269!'
assert FEEDER_AND_STANDARD_INDEX_MAPPING.get('005562') == 'H30269', 'FATAL: 005562 must map to H30269!'
print("  [OK] 门禁 B: 天天/东财真实估值强保护全覆盖 (002351/005561/110020/017436/161725)，002351移出纯债列表，005561锚定H30269")

# -------------------------------------------------------------
# 3. 门禁 C：验证未标记 real_tiantian_live 的离线/无GSZ对象仍正常执行四级穿透，且纯债应用 0.20 久期系数
# -------------------------------------------------------------
q_no_gsz_bond = FundQuote(name='工银瑞信信用纯债债券A', dwjz=1.1916, gsz=1.1916, gszzl=0.0, gztime='2026-11-18 10:25', fund_code='000086')
q_pen_bond = evaluate_four_tier_realtime_valuation('000086', q_no_gsz_bond)
assert -0.50 <= q_pen_bond.gszzl <= 0.50, f'FATAL: Tier 2 bond fallback bounds check failed! {q_pen_bond.gszzl}%'
assert '0.20' in str(q_pen_bond.gztime), f'FATAL: 0.20 duration factor must be noted in gztime: {q_pen_bond.gztime}'
print(f"  [OK] 门禁 C: 纯债后备估算乘0.20久期系数 ({q_pen_bond.gszzl}%)，严格收敛于固收区间 [-0.50%, +0.50%]")

# -------------------------------------------------------------
# 4. 门禁 D：验证 combat_29_funds 调仓单纯债去重（000086合并入002351）与 011613 C转A
# -------------------------------------------------------------
mlm = MultiLedgerManager()
pm29 = mlm.get_pm('combat_29_funds')
orders_res = StrategyBridge.generate_ai_rebalance_orders(
    current_holdings=pm29.holdings,
    available_cash=pm29.available_cash,
    target_weights_funds={'002351': 0.35, '000086': 0.15, '000216': 0.15, '100032': 0.20, '005561': 0.15},
    pm=pm29,
    mode='gentle',
    min_buffer_pct=3.0,
    core_anchor_code='002351'
)
order_codes = {it['fund_code']: it for it in orders_res['items']}
assert '000086' not in order_codes or order_codes['000086']['buy_amount'] == 0.0, f'FATAL: Unheld 000086 should be merged into 002351, not bought: {order_codes.get("000086")}'
it_1613 = order_codes.get('011613')
assert it_1613 is not None and 'C转A' in it_1613.get('action_text', ''), f'FATAL: 011613 must be labeled as C-to-A replacement: {it_1613}'
print("  [OK] 门禁 D: 纯债底仓自动去重合并，000086零买入，011613精确激活C转A置换")

# -------------------------------------------------------------
# 5. 门禁 E：验证调仓标签严格区分小额尾仓（<500元）与核心持仓，且 011613 默认 C转A 传入
# -------------------------------------------------------------
assert 'elif mv_val < 500.0 and' in gui_src, 'FATAL: Tail cleanup label must be restricted to mv_val < 500.0!'
assert 'active_lid == "combat_29_funds"' in gui_src, 'FATAL: combat_29_funds preset alignment is missing in app_gui.py!'
assert 'c_replace = st.session_state.get("tab2_c_replace") or ("011613" if active_lid == "combat_29_funds" else None)' in gui_src, 'FATAL: combat_29_funds default c_replace=011613 missing in app_gui.py!'
print("  [OK] 门禁 E: 调仓建议表已实装 elif mv_val < 500.0 and 尾仓清扫门禁及 011613 默认 C转A 置换")

# -------------------------------------------------------------
# 5.5 门禁 F & G：指数点位真实性 (H30269 > 1000) 与 Tab 2 上下卡片权重 100% 一致性
# -------------------------------------------------------------
q_h30269 = portfolio_manager.fetch_realtime_index_quote('H30269', use_cache=False)
assert float(q_h30269.get('point', 0.0)) > 1000.0, f"FATAL: H30269 point must be real index level (>1000), not ETF price 1.x: {q_h30269}"
print(f"  [OK] 门禁 F: H30269 中证红利低波真实点位校验通过 ({q_h30269['point']} 点, {q_h30269['change_pct']:+.2f}%)")

rx_preset = StrategyBridge.get_combat_29_vs_reconstructed_6_preset()
rec_w = dict(rx_preset.get('reconstructed_6_weights', {}))
orders_rec = StrategyBridge.generate_ai_rebalance_orders(
    current_holdings=pm29.holdings,
    available_cash=pm29.available_cash,
    target_weights_funds=rec_w,
    pm=pm29,
    mode='gentle',
    min_buffer_pct=3.0,
    c_replace='011613',
    core_anchor_code='002351'
)
rec_map = {it['fund_code']: it for it in orders_rec['items']}
for core_code in ['110020', '017436', '005561', '002351', '000216', '011612']:
    assert core_code in rec_map and float(rec_map[core_code].get('target_weight_pct', 0.0)) > 0.0, (
        f"FATAL: Tab 2 core holding {core_code} must have target_weight_pct > 0, got {rec_map.get(core_code)}"
    )
assert '000086' not in rec_map or float(rec_map['000086'].get('diff_amount', 0.0)) <= 0.0, "FATAL: Unheld 000086 must never be bought!"
assert 'C转A' in rec_map['011613'].get('action_text', '') and 'C转A' in rec_map['011612'].get('action_text', ''), "FATAL: 011613 -> 011612 C-to-A pair broken!"
print("  [OK] 门禁 G: Tab 2 上下卡片权重 100% 统一 (6大核心均>0%, 000086零买入, 011613->011612 C转A配对完好)")

# -------------------------------------------------------------
# 6. 运行时性能 Benchmark：实战 29 组合全量批量刷新与盘中盈亏测算 (< 3.0s)
# -------------------------------------------------------------
clear_realtime_cache()
t0 = time.time()
batch_res = prefetch_batch_fund_quotes(list(pm29.holdings.keys()), force_refresh=True)
sync_res = pm29.sync_holdings_live_nav(use_intraday_gsz=True)
pnl_res = pm29.calculate_intraday_pnl()
elapsed = time.time() - t0
print(f"  [OK] 性能 Benchmark: 29 只基金批量刷新+净值同步+盘中盈亏测算总耗时 {elapsed:.3f}s (获取 {len(batch_res)} 只, 同步 {sync_res['updated_count']} 只)")
assert elapsed < 3.0, f"Performance Benchmark FAILED: {elapsed:.3f}s >= 3.0s"

print("\n=======================================================")
print("ALL G25 CONSTITUTION, PERFORMANCE & AUTHENTIC VALUATION GATES PASSED")
print("=======================================================")
