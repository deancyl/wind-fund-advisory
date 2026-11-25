import ast
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
AGY2_DIR = ROOT / "AGY2_FundAdvisory"
for p in [str(ROOT), str(AGY2_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from portfolio_manager import (
    CORE_STRATEGY_POOL,
    FEEDER_AND_STANDARD_INDEX_MAPPING,
    SECONDARY_BOND_CODES,
    get_calibrated_feeder_beta,
)
from advisory_engine import evaluate_ten_dimensional_advisory


def run_g28_gate():
    gui_file = AGY2_DIR / "app_gui.py" if (AGY2_DIR / "app_gui.py").exists() else (ROOT / "app_gui.py")
    pm_file = AGY2_DIR / "portfolio_manager.py" if (AGY2_DIR / "portfolio_manager.py").exists() else (ROOT / "portfolio_manager.py")
    adv_file = AGY2_DIR / "advisory_engine.py" if (AGY2_DIR / "advisory_engine.py").exists() else (ROOT / "advisory_engine.py")

    gui_text = gui_file.read_text(encoding="utf-8")
    pm_text = pm_file.read_text(encoding="utf-8")
    adv_text = adv_file.read_text(encoding="utf-8")

    # 1. AST 语法全绿
    for name, txt in [("app_gui.py", gui_text), ("portfolio_manager.py", pm_text), ("advisory_engine.py", adv_text)]:
        ast.parse(txt, filename=name)

    # 2. 生产界面零模拟按钮校验
    assert "btn_mock_pending_order" not in gui_text, "生产界面仍残留模拟在途申购按钮"
    assert "模拟生成一笔在途申购订单" not in gui_text, "生产界面仍残留模拟按钮文案"

    # 3. 逐基对账单已脱离窄 popover
    assert 'st.popover("🎯 估值 vs 官方逐基对账单"' not in gui_text, "9列对账单不得继续塞在窄 popover 中"

    # 4. 五张深度图表已配备白话导读
    assert gui_text.count("_render_chart_reading_guide(") >= 5, "深度图表白话导读数量不足 5 处"

    # 5. 018757 元数据单一真源校验（严禁既是债基又映射中证红利股票指数）
    assert "018757" not in FEEDER_AND_STANDARD_INDEX_MAPPING, "018757 属于债基，严禁出现在股票指数映射表中"
    assert "018757" in SECONDARY_BOND_CODES, "018757 必须归属 SECONDARY_BOND_CODES"
    assert "债" in CORE_STRATEGY_POOL["018757"]["fund_name"]

    # 6. get_calibrated_feeder_beta 死代码已清除
    assert 'if "联接" in str(code):' not in pm_text, "get_calibrated_feeder_beta 仍存在 str(code) 死代码"
    b_val = get_calibrated_feeder_beta("110020", "sh000300", 0.95, fund_name="易方达沪深300ETF联接A")
    assert 0.90 <= b_val <= 0.97, f"联接基金 Beta 超出区间: {b_val}"

    # 7. 十维投顾数据缺失中立化校验（严禁缺失时仍输出非零仓位加减）
    empty_res = evaluate_ten_dimensional_advisory(snapshot={}, macro_multi={}, sentry_rep={})
    dims = empty_res.get("dimensions", [])
    stale_dims = [d for d in dims if d.get("dimension") in ("宏观经济", "货币政策", "国际联动", "外汇锁汇", "期权与黑天鹅")]
    for d in stale_dims:
        assert d.get("delta_pct", 0.0) == 0.0, f"缺失数据时维度 {d.get('dimension')} 仍输出非零仓位偏移: {d}"

    print("ALL G28 PRODUCTION READINESS GATES PASSED")


if __name__ == "__main__":
    run_g28_gate()
