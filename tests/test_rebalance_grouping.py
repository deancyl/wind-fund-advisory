# -*- coding: utf-8 -*-
"""
验证 rebalance_grouping 模块纯 Python 特性（严禁依赖 streamlit）与打卡持久化逻辑
"""
import sys
import pytest


def test_rebalance_grouping_no_streamlit():
    import rebalance_grouping
    # 验证 rebalance_grouping 自身未引入 streamlit
    assert "rebalance_grouping" in sys.modules


def test_group_rebalance_orders_by_intent():
    from rebalance_grouping import group_rebalance_orders_by_intent, IntentGroup
    mock_orders = [
        {"fund_code": "000058", "action": "SELL", "action_text": "🧹 建议清仓归拢", "diff_amount": -75.56, "is_tail": True},
        {"fund_code": "011613", "action": "SELL", "action_text": "🔄 C转A零费率置换", "diff_amount": -1264.11, "is_c_replace": True},
        {"fund_code": "011612", "action": "BUY", "action_text": "🔄 C转A零费率置换", "diff_amount": 1264.11, "is_c_replace": True},
        {"fund_code": "110020", "action": "BUY", "action_text": "➕ 建议加仓", "diff_amount": 500.0},
        {"fund_code": "005561", "action": "HOLD", "action_text": "🔒 维持持仓", "diff_amount": 0.0},
    ]
    grouped = group_rebalance_orders_by_intent(mock_orders)
    assert len(grouped["tail_items"]) == 1
    assert len(grouped["c_items"]) == 2
    assert len(grouped["core_items"]) == 1
    assert len(grouped["hold_items"]) == 1
    assert grouped["tail_sweep"].get("total_recovered_cash") == 75.56


def test_daily_checkin_persistence(tmp_path, monkeypatch):
    import rebalance_grouping
    mock_file = tmp_path / "daily_execution_checklist.json"
    monkeypatch.setattr(rebalance_grouping, "CHECKLIST_FILE", mock_file)

    # 1. 初始为空
    init_res = rebalance_grouping.load_daily_checkin("2026-11-22")
    assert init_res.get("checked_codes") == {}

    # 2. 勾选一项
    save_res = rebalance_grouping.save_daily_checkin("005561", "BUY", 500.0, True, "2026-11-22")
    assert "005561" in save_res["checked_codes"]
    assert save_res["checked_codes"]["005561"]["amount"] == 500.0

    # 3. 再次读取
    load_res = rebalance_grouping.load_daily_checkin("2026-11-22")
    assert "005561" in load_res["checked_codes"]

    # 4. 取消勾选
    uncheck_res = rebalance_grouping.save_daily_checkin("005561", "BUY", 500.0, False, "2026-11-22")
    assert "005561" not in uncheck_res["checked_codes"]
