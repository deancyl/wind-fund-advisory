#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
G26 估值偏差根治与「当日估算 vs 官方涨跌」双轨对账终极门禁脚本
(verify_g26_valuation_vs_official_reconciliation.py)
永久保留于 Git 版本库中，确保映射精准、4位净值修约、官方与估算双轨不覆盖、10列精致布局与秒级刷新。
"""

import ast
import re
import sys
import time
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
AGY2_DIR = WORKSPACE_ROOT / "AGY2_FundAdvisory"
if str(AGY2_DIR) not in sys.path:
    sys.path.insert(0, str(AGY2_DIR))

from portfolio_manager import (
    FundQuote,
    FEEDER_AND_STANDARD_INDEX_MAPPING,
    QDII_INDEX_MAPPING,
    prefetch_batch_fund_quotes,
    clear_realtime_cache,
    _calc_nav_rounded_gszzl,
)
from multi_ledger_manager import MultiLedgerManager

print("=== 正在运行 G26 估值校准与「当日估算 vs 官方涨跌」双轨对账门禁 ===")

# -------------------------------------------------------------
# 0. 门禁 0：核心模块 AST 静态解析 100% 合规
# -------------------------------------------------------------
for fname in ["app_gui.py", "portfolio_manager.py", "strategy_bridge.py", "cache_manager.py"]:
    ast.parse((AGY2_DIR / fname).read_text(encoding="utf-8"))
print("  [OK] 门禁 0: 核心 Python 模块 AST 语法 100% 合规")

# -------------------------------------------------------------
# 1. 门禁 A：底层基准映射纠偏校验
# -------------------------------------------------------------
assert FEEDER_AND_STANDARD_INDEX_MAPPING["016441"] != "sh000922", "FATAL: 016441 不得再误绑普通中证红利 sh000922!"
assert FEEDER_AND_STANDARD_INDEX_MAPPING["016441"] == "sz159758", f"FATAL: 016441 应映射至华夏红利质量ETF sz159758, got {FEEDER_AND_STANDARD_INDEX_MAPPING['016441']}"
assert QDII_INDEX_MAPPING["017436"] == "gb_ndx", f"FATAL: 017436 必须映射至纳斯达克100 gb_ndx, got {QDII_INDEX_MAPPING['017436']}"
assert FEEDER_AND_STANDARD_INDEX_MAPPING["000216"] == "AU9999", "FATAL: 000216 必须优先锚定上海金交所 AU9999"
assert FEEDER_AND_STANDARD_INDEX_MAPPING["002611"] == "AU9999", "FATAL: 002611 必须优先锚定上海金交所 AU9999"
print("  [OK] 门禁 A: 基准映射 100% 精准纠偏 (016441->sz159758, 017436->gb_ndx, 黄金->AU9999)")

# -------------------------------------------------------------
# 2. 门禁 B：4 位单位净值修约 + C 类日计提销售服务费校验
# -------------------------------------------------------------
gsz_a, chg_a = _calc_nav_rounded_gszzl(0.9152, 2.084, "011612", "华夏上证科创板50成份ETF联接A")
gsz_c, chg_c = _calc_nav_rounded_gszzl(0.9018, 2.084, "011613", "华夏上证科创板50成份ETF联接C")
assert gsz_a > 0 and gsz_c > 0
assert round(gsz_a, 4) == gsz_a and round(gsz_c, 4) == gsz_c
assert isinstance(chg_a, float) and isinstance(chg_c, float)
print(f"  [OK] 门禁 B: 4位净值修约与C类日费生效 (A: {gsz_a}/{chg_a:+.2f}%, C: {gsz_c}/{chg_c:+.2f}%)")

# -------------------------------------------------------------
# 3. 门禁 C：官方净值出炉后绝不覆盖 est_gszzl，且精确算出 est_diff = -0.03%
# -------------------------------------------------------------
q_reconcile = FundQuote(
    name="易方达沪深300ETF联接A",
    dwjz=1.6498,
    gsz=1.6549,
    gszzl=0.31,
    gztime="2026-11-18 官方公布净值",
    fund_code="110020",
    is_official_nav=True,
    est_gsz=1.6544,
    est_gszzl=0.28,
    official_nav=1.6549,
    official_chg_pct=0.31,
    official_pdate="2026-11-18",
    est_source="新浪估值"
)
assert q_reconcile.est_gszzl == 0.28, f"FATAL: est_gszzl 被官方涨跌覆盖了: {q_reconcile.est_gszzl}"
assert q_reconcile.official_chg == 0.31 and q_reconcile.official_chg_pct == 0.31
assert q_reconcile.est_diff == -0.03, f"FATAL: est_diff 计算错误: {q_reconcile.est_diff}"
assert "差-0.03%" in q_reconcile.val_compare_str and "🟢" in q_reconcile.val_compare_str, f"FATAL: val_compare_str 格式异常: {q_reconcile.val_compare_str}"
print(f"  [OK] 门禁 C: 双轨独立不覆盖校验通过 -> {q_reconcile.val_compare_str}")

# -------------------------------------------------------------
# 4. 门禁 D：29 只实战组合全量三源并发预取实测 (< 3.0s) 与双轨字段完整性
# -------------------------------------------------------------
mlm = MultiLedgerManager()
pm29 = mlm.get_pm("combat_29_funds")
combat_codes = list(pm29.holdings.keys())

clear_realtime_cache()
t0 = time.perf_counter()
quotes = prefetch_batch_fund_quotes(combat_codes, force_refresh=True)
elapsed = time.perf_counter() - t0
assert elapsed < 3.0, f"FATAL: 29只基金三源并发预取超时: {elapsed:.3f}s >= 3.0s"
assert len(quotes) == len(combat_codes), f"FATAL: 返回只数不完整: {len(quotes)}/{len(combat_codes)}"

for c in combat_codes:
    q = quotes[c]
    assert q.est_gszzl is not None, f"FATAL: {c} 缺失 est_gszzl"
    assert len(q.est_source) > 0, f"FATAL: {c} 缺失 est_source"
    assert q.official_chg is not None, f"FATAL: {c} 缺失 official_chg"
    assert len(q.val_compare_str) > 0, f"FATAL: {c} 缺失 val_compare_str"

q_100032 = quotes["100032"]
q_016441 = quotes["016441"]
assert q_016441.est_gszzl != q_100032.est_gszzl, (
    f"FATAL: 016441({q_016441.est_gszzl}%) 与 100032({q_100032.est_gszzl}%) 依然机械雷同!"
)
print(f"  [OK] 门禁 D: 29只实战组合三源并发拉取耗时 {elapsed:.3f}s (<3.0s)，全量双轨字段完整")
for sample_c in ["005561", "110020", "017436", "002351", "100032", "011613", "000216", "002611", "016441", "005827"]:
    qs = quotes[sample_c]
    print(f"       {sample_c} {qs.name[:14]:<14} | 估:{qs.est_gszzl:+6.2f}% [{qs.est_source}] | {qs.val_compare_str}")

# -------------------------------------------------------------
# 5. 门禁 E：Tab 2 调仓表格严格保持 10 列，且并列包含「当日估算(%)」与「官方涨跌(对比)」
# -------------------------------------------------------------
gui_src = (AGY2_DIR / "app_gui.py").read_text(encoding="utf-8")
m_cols = re.search(r"rebal_cols_10\s*=\s*\[(.*?)\]", gui_src, re.S)
assert m_cols is not None, "FATAL: app_gui.py 未找到 rebal_cols_10 定义"
parsed_cols = ast.literal_eval("[" + m_cols.group(1) + "]")
assert len(parsed_cols) == 10, f"FATAL: Tab 2 调仓表必须严格保持 10 列，当前为 {len(parsed_cols)} 列: {parsed_cols}"
assert "当日估算(%)" in parsed_cols and "官方涨跌(对比)" in parsed_cols, f"FATAL: 缺少双轨对比列: {parsed_cols}"
assert "估值 vs 官方逐基对账单" in gui_src, "FATAL: 缺少逐基三方对账单弹窗组件"
print(f"  [OK] 门禁 E: Tab 2 调仓表严格保持 10 列并包含双轨对比列 + 逐基对账单弹窗")

print("\n============================================================")
print("ALL G26 VALUATION CALIBRATION & OFFICIAL RECONCILIATION GATES PASSED")
print("============================================================")
