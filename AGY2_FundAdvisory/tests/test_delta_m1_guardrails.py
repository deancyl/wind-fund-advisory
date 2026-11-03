import pytest
from pathlib import Path
from unittest.mock import patch
from AGY2_FundAdvisory.portfolio_manager import (
    PortfolioManager,
    replace_restricted_funds_with_alternatives
)
from AGY2_FundAdvisory.strategy_bridge import StrategyBridge
from AGY2_FundAdvisory.trading_clock_fee import FeeMatrixCalculator


def test_replace_restricted_funds_with_alternatives():
    """验证开启单日限购过滤时，050025 被平滑替换为 001071 且权重归一化。"""
    raw_weights = {"002351": 0.40, "100032": 0.30, "050025": 0.30}
    new_w, rep_map = replace_restricted_funds_with_alternatives(raw_weights, min_limit=1000.0)
    assert "050025" not in new_w, "050025 should be replaced"
    assert "001071" in new_w, "001071 should be selected as alternative"
    assert abs(new_w["001071"] - 0.30) < 1e-4
    assert rep_map.get("050025") == "001071"
    assert abs(sum(new_w.values()) - 1.0) < 1e-4


def test_blueprint_purchase_limit_guardrail():
    """验证建仓单中开启限额过滤时全额买入备选标的，杜绝拆单碎片。"""
    raw_weights = {"002351": 0.40, "100032": 0.30, "050025": 0.30}
    bp = PortfolioManager.generate_zero_start_blueprint(
        total_capital=100000.0,
        target_weights_funds=raw_weights,
        min_purchase_limit=1000.0
    )
    items = bp["items"]
    codes = [it["fund_code"] for it in items]
    assert "050025" not in codes
    assert "001071" in codes
    spx_item = next(it for it in items if it["fund_code"] == "001071")
    assert abs(spx_item["allocated_amount"] - 30000.0) < 1e-2
    assert not spx_item.get("has_split", False)
    assert spx_item.get("action_guide") == "不限购正常买"


def test_rebalance_buffer_parameter_passing():
    """验证调仓缓冲阈值动态调节：高阈值不触发调仓，低阈值触发调仓。"""
    # 偏离 3.5%，门槛 4.0% -> 不调
    r1 = FeeMatrixCalculator.is_rebalance_actionable(0.20, 0.235, 100000.0, min_buffer_pct=4.0)
    assert not r1["actionable"]

    # 偏离 2.0%，门槛 1.5% -> 调
    r2 = FeeMatrixCalculator.is_rebalance_actionable(0.20, 0.220, 100000.0, min_buffer_pct=1.5)
    assert r2["actionable"]


def test_trigger_lines_sidebar_and_card2_alignment():
    """验证侧边栏与主看板 Card 2 的攻防红线点位完全同源一致。"""
    from streamlit.testing.v1 import AppTest

    mock_snapshot = {
        "c300_price": 4053.0,
        "m20_price": 4140.0,
        "trigger_lines": {
            "surge_line": 4190.0,
            "breakdown_line": 3992.0
        },
        "surge_line": 4190.0,
        "breakdown_line": 3992.0,
        "market_state": "震荡收息期",
        "er_snr": 0.65,
        "latest_date": "2026-11-03"
    }

    with patch("AGY2_FundAdvisory.strategy_bridge.StrategyBridge.get_latest_market_snapshot", return_value=mock_snapshot):
        gui_path = Path("AGY2_FundAdvisory/app_gui.py").resolve()
        at = AppTest.from_file(str(gui_path), default_timeout=30)
        at.run()
        assert not at.exception

        all_text = " ".join(m.value for m in at.markdown if m.value)
        assert "4,190" in all_text, "4,190 surge_line not rendered"
        assert "3,992" in all_text, "3,992 breakdown_line not rendered"
        assert "4,102" not in all_text, "Hardcoded 4,102 still rendered in sidebar!"
        assert "2026-11-03" in all_text, "Base date 2026-11-03 not rendered in sidebar"


def test_sidebar_buttons_order_and_demo_first():
    """验证侧边栏 button[0] 严格为【🚀 加载演示组合】"""
    from streamlit.testing.v1 import AppTest

    gui_path = Path("AGY2_FundAdvisory/app_gui.py").resolve()
    at = AppTest.from_file(str(gui_path), default_timeout=30)
    at.run()
    assert not at.exception
    assert len(at.sidebar.button) >= 3
    assert "加载演示组合" in at.sidebar.button[0].label
    assert "一键撤销快照" in at.sidebar.button[1].label
    assert "全局同步" in at.sidebar.button[2].label
