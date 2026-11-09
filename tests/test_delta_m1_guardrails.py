# -*- coding: utf-8 -*-
"""
Targeted tests for Milestone 1:
1. 3D surface removal -> 2D stress table and alias
2. Right-wing alert sentry red/yellow mapping, desc/action extraction, and severity sorting
3. Tab 2 micro execution DataFrame column headers mapping and formatting
4. Fund 017436 name unification and no false 7-day lock-ins on new buy targets
"""
import pytest
import pandas as pd
from typing import Dict, Any

from AGY2_FundAdvisory.portfolio_manager import (
    PortfolioManager,
    SECTOR_FUND_SELECTION,
)
from AGY2_FundAdvisory.strategy_bridge import (
    StrategyBridge,
    SECTOR_FUND_SELECTION_BY_TIER,
)
from AGY2_FundAdvisory.app_gui import (
    render_monte_carlo_stress_table,
    render_monte_carlo_3d_chart,
    format_micro_execution_slices_df,
)


def test_monte_carlo_stress_table_and_alias():
    """Verify render_monte_carlo_stress_table exists and render_monte_carlo_3d_chart is an alias."""
    assert callable(render_monte_carlo_stress_table)
    assert callable(render_monte_carlo_3d_chart)

    # Empty stress data returns gracefully
    assert render_monte_carlo_stress_table({}) is None
    assert render_monte_carlo_3d_chart({}) is None

    # Dummy stress data structure
    sample_data = {
        "investor_risk_tier": "C3",
        "risk_tolerance_mdd": 15.0,
        "scenarios": [
            {
                "name": "2008全球金融危机",
                "period": "2007.10-2008.10",
                "predicted_mdd_pct": 12.5,
                "h300_mdd_pct": 72.3,
                "excess_defense_pct": 59.8,
                "predicted_loss_amount": 12500.0,
                "liquidation_days": {"avg_days": 3.5}
            }
        ]
    }
    # Should not throw any exception
    render_monte_carlo_stress_table(sample_data)
    render_monte_carlo_3d_chart(sample_data)


def test_micro_execution_slices_df_formatting():
    """Verify English columns are mapped to Chinese with formatting."""
    raw_slices = [
        {
            "phase": "开盘前段 (09:30-10:00)",
            "label": "避开冲高回落",
            "vol_ratio": 0.15,
            "slice_amount": 1500.0,
            "strategy": "观望平抑"
        },
        {
            "phase": "尾盘窗口 (14:30-14:55)",
            "label": "净值锚定吸筹",
            "vol_ratio": 0.45,
            "slice_amount": 4500.0,
            "strategy": "尾盘估值锚定"
        }
    ]
    df = format_micro_execution_slices_df(raw_slices)
    assert isinstance(df, pd.DataFrame)
    expected_cols = ["执行阶段", "窗口类型", "分配比例", "建议挂单金额(元)", "微观执行策略"]
    for col in expected_cols:
        assert col in df.columns, f"Missing column: {col}"

    assert df["分配比例"].iloc[0] == "15%"
    assert df["分配比例"].iloc[1] == "45%"
    assert "¥1,500.00" in df["建议挂单金额(元)"].iloc[0]
    assert "¥4,500.00" in df["建议挂单金额(元)"].iloc[1]


def test_right_wing_alert_sorting_and_extraction():
    """Verify right-wing alerts correctly prioritize red over yellow over scale-check, and extract desc/action."""
    alerts = [
        {
            "dimension": "资产规模流动性",
            "level": "yellow",
            "title": "【广发纯债】资产规模待核验",
            "desc": "资产规模需关注流动性",
            "action": "持续跟踪"
        },
        {
            "dimension": "未满7天锁仓保护",
            "level": "red",
            "title": "【创金合信红利低波A】持有仅3天",
            "desc": "严禁赎回！未满7天扣除1.50%惩罚费！",
            "action": "锁定下界禁卖"
        },
        {
            "dimension": "移动止盈",
            "level": "WARNING",
            "title": "【纳指ETF联接】高位回撤触发止盈",
            "detail": "高位回撤达4.2%",
            "suggested_action": "阶梯止盈30%"
        },
        {
            "dimension": "信息提示",
            "level": "INFO",
            "title": "常规体检提示",
            "message": "一切运行正常"
        }
    ]

    def _sentry_alert_sorter(a):
        _lvl = str(a.get("level", "yellow")).lower()
        _t = str(a.get("title", "")) + str(a.get("desc", ""))
        is_scale_unknown = "规模待核验" in _t
        if _lvl in ("red", "critical"):
            return (0, 0)
        elif _lvl in ("yellow", "warning"):
            return (1, 1 if is_scale_unknown else 0)
        elif "green" in _lvl or _lvl in ("info", "notice"):
            return (3, 0)
        return (2, 0)

    sorted_alerts = sorted(alerts, key=_sentry_alert_sorter)
    # Red must be first
    assert sorted_alerts[0]["level"] == "red"
    assert "持有仅3天" in sorted_alerts[0]["title"]

    # Real warning must precede scale check
    assert sorted_alerts[1]["level"] == "WARNING"
    assert "移动止盈" in sorted_alerts[1]["dimension"]

    # Scale check is deprioritized
    assert "规模待核验" in sorted_alerts[2]["title"]

    # Detail / Desc / Action extraction checks
    a0_desc = sorted_alerts[0].get("desc") or sorted_alerts[0].get("detail") or sorted_alerts[0].get("message", "")
    a0_act = sorted_alerts[0].get("action") or sorted_alerts[0].get("suggested_action", "")
    assert "1.50%惩罚费" in a0_desc
    assert "锁定下界禁卖" in a0_act

    a1_desc = sorted_alerts[1].get("desc") or sorted_alerts[1].get("detail") or sorted_alerts[1].get("message", "")
    a1_act = sorted_alerts[1].get("action") or sorted_alerts[1].get("suggested_action", "")
    assert "高位回撤" in a1_desc
    assert "阶梯止盈" in a1_act


def test_017436_fund_name_unification():
    """Verify 017436 fund name is unified as '华安纳斯达克100ETF联接A'."""
    meta = PortfolioManager.resolve_fund_meta("017436")
    assert meta["fund_name"] == "华安纳斯达克100ETF联接A"

    # In SECTOR_FUND_SELECTION
    nasdaq_alts = SECTOR_FUND_SELECTION["GLOBAL_HEDGE"]["alternatives"]
    for item in nasdaq_alts:
        if item["code"] == "017436":
            assert item["name"] == "华安纳斯达克100ETF联接A"

    # In SECTOR_FUND_SELECTION_BY_TIER
    for tier in ["C1", "C2", "C3", "C4", "C5"]:
        tier_cfg = SECTOR_FUND_SELECTION_BY_TIER.get(tier, {})
        if "GLOBAL_HEDGE" in tier_cfg:
            for item in tier_cfg["GLOBAL_HEDGE"]["alternatives"]:
                if item["code"] == "017436":
                    assert item["name"] == "华安纳斯达克100ETF联接A"


def test_no_false_lock_on_new_buy_targets():
    """Verify new buy targets (not held) are never assigned 7-day lock-ins."""
    pm = PortfolioManager()
    target_weights = {"513100": 0.20, "002351": 0.80}
    rebal_data = StrategyBridge.generate_ai_rebalance_orders(
        pm.holdings,
        pm.available_cash,
        target_weights,
        pm=pm
    )
    items = rebal_data.get("items", [])
    found = False
    for it in items:
        if it.get("fund_code") == "513100":
            found = True
            assert it.get("action") == "BUY"
            assert it.get("holding_days") == -1
            assert not it.get("safety_warning")
    assert found
