# -*- coding: utf-8 -*-
"""
AGY2 v6.0-G31 反假数据与同源一致性强门禁
==========================================
强制验证：
1. AST 语法全绿；
2. 彻底消灭 G30 全部 11 个硬编码假行情与假盈亏常数；
3. 强制验证已接入真实同源数据源 (calculate_intraday_pnl, fetch_realtime_index_quote, target_weights)；
4. 严禁无二次确认的一键直接回滚；
5. 体积预算 <= 450 行，0 Plotly 图表；
6. 真实数据实算动态断言 (实战 29 只真实盈亏与指数点位均为动态实算，非伪造静态值)。
"""

import ast
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
AGY2_DIR = ROOT / "AGY2_FundAdvisory"
base = AGY2_DIR if (AGY2_DIR / "app_gui.py").exists() else ROOT
for p in [str(ROOT), str(AGY2_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)


def run_g31_gate():
    brief_file = base / "ui_daily_brief.py"
    gui_file = base / "app_gui.py"
    brief_txt = brief_file.read_text(encoding="utf-8")
    gui_txt = gui_file.read_text(encoding="utf-8")

    print("============================================================")
    print("AGY2 v6.0-G31 反假数据与同源一致性强门禁")
    print("============================================================")

    # 1. AST 语法全绿
    print("--- [Gate 1] AST 语法全绿核验 ---")
    ast.parse(brief_txt, filename="ui_daily_brief.py")
    ast.parse(gui_txt, filename="app_gui.py")
    print("  ✅ ui_daily_brief.py 与 app_gui.py AST 解析 100% 成功")

    # 2. 彻底消灭 G30 全部硬编码假行情与假盈亏常数
    print("--- [Gate 2] 彻底消灭 G30 全部硬编码假行情与假盈亏常数 ---")
    forbidden_fakes = [
        "3950.0", "1025.0", "4120.0", "0.38",
        'snap.get("today_pnl_pct"',
        'snap.get("c300_chg"',
        'snap.get("kc50_close"',
        'snap.get("hldb_close"',
        'snap.get("market_regime"',
        'getattr(pm, "target_weights"',
        "添加请求已记录，进入专家实验室可核准买入",
    ]
    for bad in forbidden_fakes:
        assert bad not in brief_txt, f"ui_daily_brief.py 仍残留 G30 假数据或空壳代码: {bad}"
    print(f"  ✅ 全部 {len(forbidden_fakes)} 项硬编码假数字/错误键名/空壳文本物理清零")

    # 3. 强制验证已接入真实同源数据源
    print("--- [Gate 3] 真实同源数据源真实接线核验 ---")
    assert "calculate_intraday_pnl" in brief_txt, "极简页必须调用 pm.calculate_intraday_pnl() 计算真实今日盈亏"
    assert "fetch_realtime_index_quote" in brief_txt, "极简页必须调用 fetch_realtime_index_quote 获取真实三大指数"
    assert "target_weights" in brief_txt, "极简页必须接收真实 target_weights 参数供发薪定投使用"
    print("  ✅ calculate_intraday_pnl、fetch_realtime_index_quote、target_weights 全真实接线")

    # 4. 严禁无二次确认的一键直接回滚
    print("--- [Gate 4] 顶栏撤回防误触二次确认核验 ---")
    assert 'if st.button("↩️"' not in gui_txt, "顶栏撤回按钮必须经过 popover 二次确认，严禁单击直接覆盖账本"
    assert "with st.popover(\"↩️\"" in gui_txt or "st.popover(\"↩️\"" in gui_txt, "顶栏必须使用 st.popover 提供二次确认"
    print("  ✅ 顶栏撤回按钮通过 st.popover 二次确认保护，杜绝手滑误操作")

    # 5. 体积与极简预算守卫
    print("--- [Gate 5] 体积与极简交互预算守卫 ---")
    line_cnt = len(brief_txt.splitlines())
    assert line_cnt <= 450, f"ui_daily_brief.py 超出体积上限: {line_cnt} (上限 450 行)"
    assert "st.plotly_chart(" not in brief_txt, "极简页严禁堆砌 Plotly 图表"
    print(f"  ✅ ui_daily_brief.py 严格受控: {line_cnt} 行 (<= 450 行), 0 Plotly 图表")

    # 6. 真实数据实算动态断言 (实战 29 只真实盈亏与指数点位动态实算)
    print("--- [Gate 6] 真实行情与真实持仓动态实算断言 ---")
    from portfolio_manager import PortfolioManager, fetch_realtime_index_quote
    q_c300 = fetch_realtime_index_quote("000300")
    assert isinstance(q_c300, dict), "fetch_realtime_index_quote 必须返回有效字典"
    assert q_c300.get("point") is not None, "沪深300点位必须存在"
    assert abs(float(q_c300["point"]) - 3950.0) > 1e-3, "沪深300点位不得为硬编码常数 3950.0"

    pm = PortfolioManager(ledger_id="combat_29_funds")
    pnl = pm.calculate_intraday_pnl()
    assert isinstance(pnl, dict), "calculate_intraday_pnl 必须返回有效字典"
    assert "total_est_pnl" in pnl and "total_est_pnl_pct" in pnl, "盈亏字段必须完备"
    assert abs(float(pnl["total_est_pnl_pct"]) - 0.38) > 1e-3, "今日预估盈亏不得为假常数 0.38%"
    print(f"  ✅ 沪深300真实点位: {q_c300['point']:.2f} ({q_c300['change_pct']:+.2f}%)，实盘29只今日预估盈亏: {pnl['total_est_pnl_pct']:+.2f}% (¥{pnl['total_est_pnl']:+,.2f})")

    print("============================================================")
    print(f"🎉 ALL G31 REAL-DATA PARITY & ANTI-FAKE GATES PASSED (ui_daily_brief.py: {line_cnt} lines)")
    print("============================================================")


if __name__ == "__main__":
    run_g31_gate()
