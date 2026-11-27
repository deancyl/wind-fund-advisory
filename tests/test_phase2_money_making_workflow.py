# -*- coding: utf-8 -*-
"""
AGY2 Phase 2 (v2.3.0) Money-Making Workflow & API Regression Gate Suite:
  - Exact Newton-Raphson / Bisection XIRR accuracy & per-ledger cashflow CRUD
  - Holding-level 3-stage trailing take-profit & 7-day penalty radar
  - Smart staged entry plan (bias_20 > 3.5% hot throttle, quota split, <=12m C-share)
  - 14:30 cutoff quick brief (golden window vs after-hours)
  - Live FastAPI endpoint integration
"""
import sys
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
AGY2_DIR = ROOT_DIR / "AGY2_FundAdvisory"
for p in (str(AGY2_DIR), str(ROOT_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)


def test_compute_xirr_exact_analytical_cases():
    from phase2_workflow_engine import compute_xirr

    # 1. Exact 1-year +20% simple compound
    r1 = compute_xirr([(date(2025, 1, 1), -10000.0), (date(2026, 1, 1), 12000.0)])
    assert r1 is not None and abs(r1 - 0.20) < 1e-4, f"Expected 0.20, got {r1}"

    # 2. Mid-year cash injection (bank DCA investor):
    # -10,000 on 2025-01-01 + -10,000 on 2025-07-02 -> 21,500 on 2026-01-01
    # Average capital ~15,000 for 1 year => ~+10% annualized (higher than simple 7.5%!)
    r2 = compute_xirr([
        (date(2025, 1, 1), -10000.0),
        (date(2025, 7, 2), -10000.0),
        (date(2026, 1, 1), 21500.0),
    ])
    assert r2 is not None and 0.095 < r2 < 0.106, f"Expected ~10.1% XIRR, got {r2}"

    # 3. Negative return case (-15% over 1 year)
    r3 = compute_xirr([(date(2025, 1, 1), -10000.0), (date(2026, 1, 1), 8500.0)])
    assert r3 is not None and abs(r3 - (-0.15)) < 1e-4

    # 4. Invalid single-sided flows must return None
    assert compute_xirr([(date(2025, 1, 1), -1000.0), (date(2026, 1, 1), -500.0)]) is None


def test_ledger_cashflow_crud_isolated_sandbox(tmp_path, monkeypatch):
    import runtime_paths
    from phase2_workflow_engine import (
        append_ledger_cashflow,
        delete_ledger_cashflow,
        summarize_ledger_xirr,
    )

    monkeypatch.setenv("AGY2_DATA_DIR", str(tmp_path))
    lid = "test_sandbox_p2"

    r1 = append_ledger_cashflow(lid, "2025-01-10", "BUY", 10000.0, "005561", "创金合信红利低波A", "首笔建仓")
    r2 = append_ledger_cashflow(lid, "2025-07-10", "BUY", 10000.0, "005561", "创金合信红利低波A", "回调加仓")
    r3 = append_ledger_cashflow(lid, "2025-10-10", "DIVIDEND", 500.0, "005561", "创金合信红利低波A", "现金分红")

    summary = summarize_ledger_xirr(lid, holdings={}, total_equity=22000.0, as_of_date=date(2026, 1, 10))
    assert summary["is_estimated"] is False
    assert summary["record_count"] == 3
    assert summary["total_invested"] == 20000.0
    assert summary["total_withdrawn"] == 500.0
    assert summary["net_profit"] == 2500.0
    assert summary["xirr_pct"] is not None and 14.0 < summary["xirr_pct"] < 20.0

    assert delete_ledger_cashflow(lid, r3["id"]) is True
    assert delete_ledger_cashflow(lid, "nonexistent") is False
    summary2 = summarize_ledger_xirr(lid, holdings={}, total_equity=22000.0, as_of_date=date(2026, 1, 10))
    assert summary2["record_count"] == 2
    assert r1["id"] != r2["id"]


def test_holding_trailing_take_profit_radar_all_states():
    from phase2_workflow_engine import evaluate_holding_take_profit_radar

    dates = pd.bdate_range("2026-01-02", periods=100)
    # 000001: peaked at 1.50 then dropped to 1.38 (-8.0% from peak), while cost=1.10 (+25.5% gain) => LOCK_PARTIAL
    nav_1 = np.linspace(1.10, 1.50, 90).tolist() + np.linspace(1.49, 1.38, 10).tolist()
    # 000002: steadily climbing to 1.30 (0% dd from peak), cost=1.05 (+23.8% gain) => TARGET_REACHED
    nav_2 = np.linspace(1.05, 1.30, 100).tolist()
    nav_df = pd.DataFrame({"000001": nav_1, "000002": nav_2}, index=dates)

    holdings = {
        "000001": {"shares": 1000.0, "cost_price": 1.10, "current_nav": 1.38, "holding_days": 120, "first_buy_date": "2026-01-05"},
        "000002": {"shares": 1000.0, "cost_price": 1.05, "current_nav": 1.30, "holding_days": 120, "first_buy_date": "2026-01-05"},
        "000003": {"shares": 1000.0, "cost_price": 1.00, "current_nav": 1.25, "holding_days": 4, "first_buy_date": "2026-11-24"},
        "000004": {"shares": 1000.0, "cost_price": 1.20, "current_nav": 1.02, "holding_days": 180, "first_buy_date": "2026-05-01"},
        "000005": {"shares": 1000.0, "cost_price": 1.00, "current_nav": 1.05, "holding_days": 60, "first_buy_date": "2026-09-15"},
    }
    res = evaluate_holding_take_profit_radar(holdings, nav_matrix=nav_df, target_profit_pct=15.0, trailing_dd_pct=4.5)
    assert res["000001"]["status"] == "LOCK_PARTIAL" and res["000001"]["suggested_redeem_ratio"] > 0
    assert res["000002"]["status"] == "TARGET_REACHED"
    assert res["000003"]["status"] == "HOLD_PENALTY"
    assert res["000004"]["status"] == "DEEP_VALUE_ZONE"
    assert res["000005"]["status"] == "NORMAL"


def test_staged_entry_plan_hot_throttle_quota_split_and_c_share():
    from phase2_workflow_engine import build_staged_entry_plan

    items = [
        {"fund_code": "008163", "fund_name": "南方标普红利低波50ETF联接A", "bucket_label": "红利低波价值", "weight_pct": 50.0, "bias_20": 4.8, "daily_limit": 1e10, "c_share_code": "008164"},
        {"fund_code": "000614", "fund_name": "华安德国(DAX)联接(QDII)A", "bucket_label": "海外QDII", "weight_pct": 50.0, "bias_20": -1.2, "daily_limit": 1000.0, "c_share_code": "015016"},
    ]
    plan = build_staged_entry_plan(items, total_amount=60000.0, horizon_months=6, mode="smart_3_tranche", market_regime="震荡分歧")
    assert len(plan["tranches"]) == 3
    assert plan["hot_throttled_count"] == 1
    assert plan["quota_split_count"] == 1

    # Hot fund (008163, ¥30,000 total) MUST throttle tranche 1 to 25% = ¥7,500 (not 40% = ¥12,000)
    t1_orders = {o["fund_code"]: o for o in plan["tranches"][0]["orders"]}
    assert abs(t1_orders["008163"]["amount"] - 7500.0) < 1.0
    assert t1_orders["008163"]["is_hot_throttled"] is True
    assert t1_orders["008163"]["c_share_code"] == "008164"

    # Normal fund (000614, ¥30,000 total) gets 40% = ¥12,000 -> split over 12 days at ¥1,000/day
    assert abs(t1_orders["000614"]["amount"] - 12000.0) < 1.0
    assert t1_orders["000614"]["split_days"] == 12
    assert "008164" in plan["copyable_checklist_text"] and "015016" in plan["copyable_checklist_text"]


def test_cutoff_quick_brief_golden_window_and_api_endpoints():
    import api_server
    from phase2_workflow_engine import build_cutoff_quick_brief

    # Simulate Friday 14:40 CST (golden window 14:30~14:55)
    brief = build_cutoff_quick_brief(
        holdings_rows=[{
            "fund_code": "005561",
            "fund_name": "红利低波A",
            "take_profit": {"status": "LOCK_PARTIAL", "action_tip": "触发移动止盈，建议落袋 1/3"},
        }],
        now_dt=datetime(2026, 11, 27, 14, 40, 0),
    )
    assert brief["is_golden_window"] is True
    assert brief["profit_lock_count"] == 1
    assert len(brief["priority_actions"]) == 1 and brief["priority_actions"][0]["tag"] == "移动止盈落袋"

    # API endpoint smoke checks
    h_res = api_server.api_v1_holdings()
    assert "items" in h_res
    if h_res["items"]:
        assert "take_profit" in h_res["items"][0]

    cf_res = api_server.api_v1_ledger_cashflows_get()
    assert "xirr_pct" in cf_res and "source_label" in cf_res

    cb_res = api_server.api_v1_trading_cutoff_brief()
    assert "window_type" in cb_res and "effective_trade_date" in cb_res and "priority_actions" in cb_res
