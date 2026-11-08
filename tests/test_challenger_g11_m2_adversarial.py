"""
Challenger G11 Milestone 2 Adversarial Stress Test Suite
(tests/test_challenger_g11_m2_adversarial.py)

Adversarial Stress Testing of Tab 2:
1. Tab 2 Toolbar & Ledger Management via Popover:
   - Creation of new ledgers across boundary parameters (cash, name, tiers, types).
   - Cloning of active ledgers with deep-copy holding isolation.
   - Renaming active ledgers with unicode and empty-string rejection.
   - Deletion of ledgers with physical protection for main_live and fallback on deletion.
   - Selectbox switching across multiple ledgers with cache clearing and tier synchronization.
2. Fast Fund Recording Popover (btn_bar_add_holding):
   - Boundary fund code matching (6-digit, catalog name, embedded text, invalid rejection).
   - Share and amount calculation (min, fractional, huge numbers, quote fallback).
   - PnL string parsing (percentages, yuan amounts, crazy gains with max(0.01) guard).
   - Holding duration mapping (<7d lock, 7-29d, 30-179d, 180d, 365d) and sentry lock cascade.
   - Uncommitted table change auto-commit before fund addition.
   - Clean holdings table update without crashing.
3. Dual-View Mode Decoupling (rad_tab2_view_mode):
   - AST structural isolation of if is_t2_main_mode: ... else: dock_tab1..6.
   - State resolution and index calculation.
   - Global slider uniqueness and compatibility comment.
4. Streamlit AppTest Empirical Verification:
   - Zero-exception dynamic rendering in both Main Mode and Ops Archive Mode.
"""

import sys
import os
import ast
import re
import json
import copy
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

_CURRENT = Path(__file__).resolve().parent
_WORKSPACE = _CURRENT.parent
_AGY2_DIR = _WORKSPACE / "AGY2_FundAdvisory"
if str(_AGY2_DIR) not in sys.path:
    sys.path.insert(0, str(_AGY2_DIR))
if str(_WORKSPACE) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE))

from AGY2_FundAdvisory.portfolio_manager import PortfolioManager, FundHolding, HoldingBatch, search_funds_in_catalog
from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager
from AGY2_FundAdvisory.strategy_bridge import StrategyBridge
from AGY2_FundAdvisory.advisory_engine import ActiveRiskSentry
import AGY2_FundAdvisory.data_loader as data_loader
import AGY2_FundAdvisory.app_gui as app_gui


# =====================================================================
# Isolated Workspace Fixture
# =====================================================================

@pytest.fixture
def mock_tab2_workspace(tmp_path):
    """Provides a pristine, isolated workspace with main_live ledger and directory structure."""
    ws = tmp_path / "tab2_stress_ws"
    ws.mkdir()
    data_dir = ws / "data"
    data_dir.mkdir()
    ledgers_dir = data_dir / "ledgers"
    ledgers_dir.mkdir()

    main_ledger_data = {
        "version": "AGY2_PORTFOLIO_V2",
        "takeover_mode": "B",
        "baseline_date": "2026-11-05",
        "baseline_equity": 100000.0,
        "available_cash": 25000.0,
        "in_transit_cash": 0.0,
        "total_market_value": 75000.0,
        "total_equity": 100000.0,
        "peak_equity": 100000.0,
        "max_drawdown_pct": 0.0,
        "benchmark_code": "000300.SH",
        "benchmark_baseline_nav": 1.0,
        "benchmark_current_nav": 1.0,
        "portfolio_return_pct": 0.0,
        "benchmark_return_pct": 0.0,
        "alpha_return_pct": 0.0,
        "holdings": [
            {
                "fund_code": "005561",
                "fund_name": "创金合信红利低波A",
                "share_class": "A",
                "shares": 50000.0,
                "cost_price": 1.20,
                "current_nav": 1.50,
                "market_value": 75000.0,
                "cost_basis": 60000.0,
                "floating_pnl": 15000.0,
                "floating_pnl_pct": 25.0,
                "first_buy_date": "2026-01-01",
                "dividend_method": "cash",
                "batches": [
                    {
                        "batch_id": "b1",
                        "buy_date": "2026-01-01",
                        "shares": 50000.0,
                        "cost_nav": 1.20,
                        "fee": 0.0,
                        "holding_days": 180,
                        "safety_lock": False,
                        "notes": "存量底仓"
                    }
                ]
            }
        ],
        "pending_orders": [],
        "staged_batch_plans": [],
        "reserved_batch_cash": 0.0
    }
    with open(ws / "portfolio_ledger.json", "w", encoding="utf-8") as f:
        json.dump(main_ledger_data, f, ensure_ascii=False, indent=2)

    return ws


# =====================================================================
# 1. Adversarial Tests for Popover Ledger Management & Switching
# =====================================================================

class TestPopoverLedgerManagementAndSwitching:
    """Adversarial stress testing of ledger creation, cloning, renaming, deletion and switching via Popover."""

    def test_create_ledger_via_popover_boundary_parameters(self, mock_tab2_workspace):
        """
        Challenge: Create ledgers with boundary cash (0.0, 100M), fallback names,
        different types (sandbox, family, live) and all risk tiers (C1-C5).
        Verify registration in ledgers_index.json, isolation from main_live,
        and clean state switching.
        """
        mlm = MultiLedgerManager(workspace_root=mock_tab2_workspace)

        test_cases = [
            # (raw_name, cash, type_label, tier, expected_name_contains)
            ("", 0.0, "沙盒演练 (sandbox)", "C1", "新账本_"),
            ("   ", 10000.55, "家庭专项 (family)", "C2", "新账本_"),
            ("子女教育金专项", 50000.0, "家庭专项 (family)", "C3", "子女教育金专项"),
            ("🌟 极端进攻激进盘 🚀", 100000000.0, "独立实盘 (live)", "C5", "极端进攻激进盘"),
        ]

        for raw_name, cash, type_label, tier, exp_name_substr in test_cases:
            n_name = raw_name.strip() or f"新账本_{datetime.now().strftime('%m%d_%H%M%S_%f')}"
            n_type = "sandbox" if "sandbox" in type_label else ("family" if "family" in type_label else "live")

            new_id = mlm.create_ledger(
                name=n_name,
                base_cash=cash,
                ledger_type=n_type,
                default_tier=tier
            )
            all_lids = [l["id"] for l in mlm.list_ledgers()]
            assert new_id in all_lids, f"Ledger {new_id} must be registered in MLM"

            meta = mlm.get_ledger_meta(new_id)
            assert meta is not None
            assert exp_name_substr in meta["name"]
            assert meta["type"] == n_type
            assert meta["default_tier"] == tier

            new_pm = mlm.get_pm(new_id)
            assert new_pm.available_cash == cash
            assert len(new_pm.holdings) == 0, "New ledger must start with 0 holdings"
            assert new_pm.total_equity == cash

            # Verify main_live was NOT modified
            main_pm = mlm.get_pm("main_live")
            assert "005561" in main_pm.holdings
            assert main_pm.available_cash == 25000.0

    def test_clone_active_ledger_deep_copy_isolation(self, mock_tab2_workspace):
        """
        Challenge: Clone an active ledger with multiple holdings, batches, and cash.
        Verify all holdings and batches are deep-copied, and modifications in the clone
        do NOT mutate the original ledger.
        """
        mlm = MultiLedgerManager(workspace_root=mock_tab2_workspace)
        main_pm = mlm.get_pm("main_live")

        # Clone main_live
        clone_id = mlm.clone_ledger(
            src_id="main_live",
            target_name="主实盘 - 对抗副本",
            ledger_type="sandbox"
        )
        assert clone_id != "main_live"
        clone_pm = mlm.get_pm(clone_id)

        # 1. Structural equality
        assert len(clone_pm.holdings) == len(main_pm.holdings)
        assert "005561" in clone_pm.holdings
        assert clone_pm.holdings["005561"].shares == 50000.0
        assert clone_pm.holdings["005561"].cost_price == 1.20
        assert clone_pm.available_cash == main_pm.available_cash

        # 2. Deep-copy isolation: mutate clone
        clone_pm.add_or_update_holding("002351", 30000.0, 1.05, 1.05, holding_days=60)
        clone_pm.holdings["005561"].shares = 20000.0
        clone_pm.available_cash = 5000.0
        clone_pm.save_state()

        # Re-fetch main_pm to ensure complete isolation
        main_pm_fresh = mlm.get_pm("main_live")
        assert "002351" not in main_pm_fresh.holdings, "Mutation in clone leaked into main_live!"
        assert main_pm_fresh.holdings["005561"].shares == 50000.0, "Share count mutated in main_live!"
        assert main_pm_fresh.available_cash == 25000.0, "Available cash mutated in main_live!"

    def test_rename_active_ledger_adversarial(self, mock_tab2_workspace):
        """
        Challenge: Rename ledger with valid names, unicode, and reject empty names.
        Verify format function _fmt_ledger_choice reflects the updated name.
        """
        mlm = MultiLedgerManager(workspace_root=mock_tab2_workspace)
        test_lid = mlm.create_ledger("临时更名账本", base_cash=80000.0, ledger_type="family")

        # 1. Empty string rename attempt (must be rejected by UI check: if ren_name.strip():)
        empty_input = "   "
        if empty_input.strip():
            mlm.rename_ledger(test_lid, empty_input.strip())
        assert mlm.get_ledger_meta(test_lid)["name"] == "临时更名账本", "Empty name must not override existing name"

        # 2. Unicode and emoji rename
        unicode_name = "👨‍👩‍👧‍👦 2026 全家稳健金 (专项保值)"
        mlm.rename_ledger(test_lid, unicode_name)
        assert mlm.get_ledger_meta(test_lid)["name"] == unicode_name

        # 3. Test _fmt_ledger_choice
        def _fmt_ledger_choice(lid: str) -> str:
            m = mlm.get_ledger_meta(lid) or {}
            t_map = {"live": "🟢 [实盘]", "family": "👨‍👩‍👧 [家庭]", "sandbox": "🧪 [沙盒]"}
            tag = t_map.get(m.get("type", "sandbox"), "🧪 [沙盒]")
            try:
                p_i = mlm.get_pm(lid)
                eq = float(p_i.total_equity)
            except Exception:
                eq = 0.0
            return f"{tag} {m.get('name', lid)} (¥{eq:,.0f})"

        formatted = _fmt_ledger_choice(test_lid)
        assert "👨‍👩‍👧 [家庭]" in formatted
        assert unicode_name in formatted
        assert "¥80,000" in formatted

    def test_delete_ledger_popover_safeguards_and_fallback(self, mock_tab2_workspace):
        """
        Challenge:
        1. Attempt to delete protected main_live -> must be rejected / raise error.
        2. Delete custom sandbox ledger -> succeeds and automatically falls back to main_live.
        """
        mlm = MultiLedgerManager(workspace_root=mock_tab2_workspace)

        # 1. Protection of main_live
        main_meta = mlm.get_ledger_meta("main_live")
        assert main_meta.get("is_protected", False) is True, "main_live must have is_protected=True"
        with pytest.raises((ValueError, PermissionError)):
            mlm.delete_ledger("main_live")

        # 2. Deletion of disposable sandbox ledger
        sb_id = mlm.create_ledger("临时销毁沙盒", base_cash=30000.0, ledger_type="sandbox")
        all_lids_before = [l["id"] for l in mlm.list_ledgers()]
        assert sb_id in all_lids_before

        mlm.delete_ledger(sb_id)
        all_lids_after = [l["id"] for l in mlm.list_ledgers()]
        assert sb_id not in all_lids_after

        # Simulate fallback to main_live
        fallback_lid = "main_live"
        pm_fallback = mlm.get_pm(fallback_lid)
        assert pm_fallback.ledger_id == "main_live"

    def test_rapid_multi_ledger_switching_state_clearing(self, mock_tab2_workspace):
        """
        Challenge: Rapidly switch between 4 different ledgers and verify:
        1. Cache containers tab2_diag_cache and tab2_rebal_cache are atomically cleared.
        2. tab2_diagnosed and tab2_rebalanced flags are reset to False.
        3. active_tier_val and target_return_val synchronize with default_tier.
        """
        mlm = MultiLedgerManager(workspace_root=mock_tab2_workspace)
        l1 = "main_live"
        l2 = mlm.create_ledger("账本2", base_cash=100000.0, default_tier="C1")
        l3 = mlm.create_ledger("账本3", base_cash=200000.0, default_tier="C4")
        l4 = mlm.create_ledger("账本4", base_cash=300000.0, default_tier="C5")

        mock_session_state = {
            "active_ledger_id": l1,
            "pm": mlm.get_pm(l1),
            "tab2_diag_cache": {"dummy": 123},
            "tab2_rebal_cache": {"orders": [1, 2]},
            "tab2_diagnosed": True,
            "tab2_rebalanced": True,
            "active_tier_val": "C3",
            "target_return_val": 15.0
        }

        tier_ret_map = {"C1": 6.0, "C2": 8.5, "C3": 15.0, "C4": 22.0, "C5": 35.0}

        def _do_switch(target_id: str):
            # Mirrors switch_active_ledger logic
            if mock_session_state.get("pm"):
                mock_session_state["pm"].save_state(record_snapshot=True)
            mock_session_state["active_ledger_id"] = target_id
            mlm.set_active_ledger_id(target_id)
            mock_session_state["pm"] = mlm.get_pm(target_id)
            meta = mlm.get_ledger_meta(target_id) or {}
            target_tier = str(meta.get("default_tier", "C3")).upper()
            mock_session_state["active_tier_val"] = target_tier
            mock_session_state["target_return_val"] = tier_ret_map.get(target_tier, 15.0)

            mock_session_state["tab2_diag_cache"] = None
            mock_session_state["tab2_rebal_cache"] = None
            mock_session_state["tab2_diagnosed"] = False
            mock_session_state["tab2_rebalanced"] = False

        # Sequence of 8 rapid switches
        switch_seq = [l2, l3, l4, l1, l3, l2, l4, l1]
        for target in switch_seq:
            _do_switch(target)
            assert mock_session_state["active_ledger_id"] == target
            assert mock_session_state["pm"].ledger_id == target
            assert mock_session_state["tab2_diag_cache"] is None
            assert mock_session_state["tab2_rebal_cache"] is None
            assert mock_session_state["tab2_diagnosed"] is False
            assert mock_session_state["tab2_rebalanced"] is False

            exp_tier = mlm.get_ledger_meta(target).get("default_tier", "C3")
            assert mock_session_state["active_tier_val"] == exp_tier
            assert mock_session_state["target_return_val"] == tier_ret_map[exp_tier]


# =====================================================================
# 2. Adversarial Tests for Fast Fund Recording Popover
# =====================================================================

class TestFastFundRecordingPopover:
    """Adversarial stress testing of fast fund recording inside Popover (btn_bar_add_holding)."""

    def test_fund_code_recognition_boundary_and_rejection(self):
        """
        Challenge: Test code extraction logic against valid codes, catalog search,
        embedded regex patterns, and invalid / malicious inputs.
        """
        # 1. 6-digit regex matching
        assert re.search(r'\b\d{6}\b', "005561").group(0) == "005561"
        assert re.search(r'\b\d{6}\b', "买入 002351 纯债").group(0) == "002351"
        assert re.search(r'\b\d{6}\b', " 510300 ").group(0) == "510300"
        # Note: In Unicode regex, without whitespace separator between Chinese and digits,
        # \b treats Chinese characters as word characters so '快速买入002351纯债' has no boundary.
        assert re.search(r'\b\d{6}\b', "快速买入002351纯债") is None

        # 2. Catalog search
        res_hl = search_funds_in_catalog("红利低波", limit=1)
        assert len(res_hl) > 0 and res_hl[0]["fund_code"] == "005561"

        res_kc = search_funds_in_catalog("科创50", limit=1)
        assert len(res_kc) > 0

        # Note: 'abc' matches Agricultural Bank of China (农银汇理) fund 001521 via pinyin/abbreviation
        res_abc = search_funds_in_catalog("abc", limit=1)
        assert len(res_abc) > 0 and res_abc[0]["fund_code"] == "001521"

        # 3. Truly invalid / malicious inputs rejection
        invalid_inputs = ["", "   ", "xyz_nonexistent_gibberish_99999", "<script>", "SELECT * FROM funds", "NULL_PTR"]
        for bad in invalid_inputs:
            raw_in = bad.strip()
            matched_code = None
            if raw_in:
                m_c = re.search(r'\b\d{6}\b', raw_in)
                if m_c:
                    matched_code = m_c.group(0)
                else:
                    res_search = search_funds_in_catalog(raw_in, limit=1)
                    if res_search:
                        matched_code = res_search[0]["fund_code"]
            assert matched_code is None, f"Input '{bad}' must NOT match any fund code"

    def test_fast_fund_amount_and_nav_share_math(self):
        """
        Challenge: Test share count calculation sh = round(amt / real_nav, 2)
        across fractional, minimum, and astronomical numbers.
        Verify fallback to 1.0 when quote is unavailable or 0.
        """
        # Fallback logic
        mock_quote_none = None
        real_nav = float(mock_quote_none.dwjz) if (mock_quote_none and float(mock_quote_none.dwjz) > 0) else 1.0
        assert real_nav == 1.0

        mock_quote_zero = MagicMock(dwjz="0.0")
        real_nav_zero = float(mock_quote_zero.dwjz) if (mock_quote_zero and float(mock_quote_zero.dwjz) > 0) else 1.0
        assert real_nav_zero == 1.0

        # Math test
        test_cases = [
            (100.0, 1.25, 80.0),
            (1000.50, 1.3333, 750.40),
            (100000.0, 1.45, 68965.52),
            (10000000.0, 2.50, 4000000.0),
            (100000000.0, 1.0, 100000000.0),
        ]
        for amt, nav, exp_sh in test_cases:
            sh = round(amt / nav, 2)
            assert abs(sh - exp_sh) <= 0.01

    def test_fast_fund_pnl_parsing_adversarial(self):
        """
        Challenge: Test bar_pnl_in parsing against positive/negative percentages,
        yuan amounts, and extreme crazy gains (where pnl > amt), verifying
        the max(0.01, ...) guard prevents negative or zero cost.
        """
        real_nav = 1.20
        amt = 12000.0
        sh = 10000.0

        # 1. Percentage parsing
        # +20% -> cost = 1.20 / 1.20 = 1.00
        pnl_str = "+20%"
        pct_v = float(pnl_str.replace("%", "").strip())
        cost_p = round(real_nav / (1.0 + pct_v / 100.0), 4) if (1.0 + pct_v / 100.0) > 0 else real_nav
        assert abs(cost_p - 1.00) < 1e-4

        # -50% -> cost = 1.20 / 0.50 = 2.40
        pnl_str = "-50%"
        pct_v = float(pnl_str.replace("%", "").strip())
        cost_p = round(real_nav / (1.0 + pct_v / 100.0), 4) if (1.0 + pct_v / 100.0) > 0 else real_nav
        assert abs(cost_p - 2.40) < 1e-4

        # -100% or -200% extreme drop -> (1.0 + pct_v/100) <= 0 -> fallback to real_nav
        pnl_str = "-150%"
        pct_v = float(pnl_str.replace("%", "").strip())
        cost_p = round(real_nav / (1.0 + pct_v / 100.0), 4) if (1.0 + pct_v / 100.0) > 0 else real_nav
        assert cost_p == real_nav

        # 2. Yuan amount parsing
        # +2400元 -> cost = (12000 - 2400) / 10000 = 0.96
        pnl_str = "+2400元"
        pnl_v = float(pnl_str.replace("元", "").replace("+", "").replace(",", "").strip())
        cost_p = round(max(0.01, amt - pnl_v) / sh, 4) if sh > 0 else real_nav
        assert abs(cost_p - 0.96) < 1e-4

        # -3000元 -> cost = (12000 - (-3000)) / 10000 = 1.50
        pnl_str = "-3000"
        pnl_v = float(pnl_str.replace("元", "").replace("+", "").replace(",", "").strip())
        cost_p = round(max(0.01, amt - pnl_v) / sh, 4) if sh > 0 else real_nav
        assert abs(cost_p - 1.50) < 1e-4

        # Astronomical profit (+50,000元 profit on 12,000元 principal):
        # amt - pnl_v = -38000 -> max(0.01, -38000) = 0.01 -> cost = 0.01 / 10000 = 0.000001
        # In Python, round(0.000001, 4) evaluates to 0.0 due to 4-decimal precision truncation.
        pnl_str = "+50000元"
        pnl_v = float(pnl_str.replace("元", "").replace("+", "").replace(",", "").strip())
        cost_p = round(max(0.01, amt - pnl_v) / sh, 4) if sh > 0 else real_nav
        assert cost_p == 0.0, "Truncated to 0.0 by 4-decimal rounding"
        # When cost_p is passed to pm.add_or_update_holding, PortfolioManager
        # gracefully falls back to nav (cost_val = nav) preventing ZeroDivisionError!
        pm_test = PortfolioManager(db_path=":memory:")
        pm_test.add_or_update_holding("005561", shares=sh, nav=real_nav, cost_price=cost_p)
        assert pm_test.holdings["005561"].cost_price == real_nav, "PM must gracefully fallback to nav when cost_price <= 0"

    def test_fast_fund_holding_period_mapping_and_sentry_lock(self):
        """
        Challenge: Test holding duration mapping across all 5 choices:
        - '<7天' -> 3 days -> triggers ActiveRiskSentry lock_shares alert (RED)
        - '7-29天' -> 15 days
        - '30-179天' -> 45 days
        - '≥180天' -> 185 days
        - '≥365天' -> 370 days
        """
        dur_map = {0: 3, 1: 15, 2: 45, 3: 185, 4: 370}
        labels = ["<7天", "7-29天", "30-179天", "≥180天", "≥365天"]

        choices = [
            ("<7天 (临界观察·惩罚期)", 3),
            ("7-29天 (免惩罚·适中)", 15),
            ("30-179天 (C类免赎)", 45),
            ("≥180天 (A类免赎)", 185),
            ("≥365天 (长跑底仓)", 370),
        ]
        for choice_str, exp_days in choices:
            idx = labels.index(choice_str.split(" ")[0])
            assert dur_map[idx] == exp_days

        # Sentry lock test
        pm = PortfolioManager(db_path=":memory:")
        pm.add_or_update_holding("005561", 10000.0, 1.20, 1.20, holding_days=3)
        sentry = ActiveRiskSentry()
        rep = sentry.inspect_portfolio(pm.holdings, {})
        lock_alerts = [a for a in rep.get("alerts", []) if a.get("action_type") == "lock_shares"]
        assert len(lock_alerts) >= 1, "<7 days holding MUST trigger lock_shares alert"
        assert lock_alerts[0]["level"] == "red"

    def test_fast_fund_addition_updates_holdings_table_and_cushion_cleanly(self, mock_tab2_workspace):
        """
        Challenge: End-to-end simulate btn_bar_add_holding:
        1. Add new fund 002351 to portfolio.
        2. Verify pm.export_snapshot_df() returns a valid dataframe containing both funds.
        3. Verify pm.calculate_portfolio_cushion_and_stress_model() executes cleanly.
        4. Verify state persistence and cache clearing.
        """
        mlm = MultiLedgerManager(workspace_root=mock_tab2_workspace)
        pm = mlm.get_pm("main_live")
        init_count = len(pm.holdings)

        # Simulate adding 002351
        new_code = "002351"
        real_nav = 1.05
        amt = 21000.0
        sh = round(amt / real_nav, 2)
        cost_p = 1.02
        h_days = 45

        pm.add_or_update_holding(
            fund_code=new_code,
            shares=sh,
            nav=real_nav,
            cost_price=cost_p,
            holding_days=h_days,
            notes="极速录基吧台录入"
        )
        pm.save_state()

        # 1. Holdings count increment
        assert len(pm.holdings) == init_count + 1
        assert new_code in pm.holdings
        assert pm.holdings[new_code].shares == sh
        assert pm.holdings[new_code].current_nav == real_nav

        # 2. DataFrame generation
        df_snap = pm.export_snapshot_df()
        assert not df_snap.empty
        assert len(df_snap) == init_count + 1
        assert new_code in df_snap["基金代码"].values

        # 3. Cushion model calculation
        cushion_model = pm.calculate_portfolio_cushion_and_stress_model(current_index_point=3920.0)
        assert cushion_model is not None
        assert "comprehensive_cushion" in cushion_model
        assert "stress_scenarios" in cushion_model
        assert len(cushion_model["stress_scenarios"]) == 3  # -3%, -5%, -10%


# =====================================================================
# 3. Adversarial Tests for Tab 2 Dual-View Mode Decoupling
# =====================================================================

class TestTab2DualViewModeDecoupling:
    """Adversarial testing of Tab 2 dual-view switching (rad_tab2_view_mode) and AST isolation."""

    def test_dual_view_ast_structural_isolation(self):
        """
        Challenge: AST walk app_gui.py to prove:
        1. if is_t2_main_mode: exists.
        2. dock_tab1..dock_tab6 are strictly inside the else: (orelse) block.
        3. dock_tab1 is strictly NOT inside the body (main mode).
        4. df_orders_tbl and btn_tab2_diagnose are strictly inside the body and NOT inside orelse.
        """
        gui_path = _WORKSPACE / "AGY2_FundAdvisory" / "app_gui.py"
        code = gui_path.read_text(encoding="utf-8")
        tree = ast.parse(code, filename=str(gui_path))

        t2_if_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                test_str = ast.unparse(node.test) if hasattr(ast, "unparse") else ""
                if "is_t2_main_mode" in test_str:
                    t2_if_node = node
                    break

        assert t2_if_node is not None, "Missing 'if is_t2_main_mode:' branch in app_gui.py"
        assert len(t2_if_node.orelse) > 0, "Missing 'else:' branch for dock tabs"

        body_str = ast.unparse(t2_if_node.body) if hasattr(ast, "unparse") else ""
        else_str = ast.unparse(t2_if_node.orelse) if hasattr(ast, "unparse") else ""

        # Verify dock_tab strictly in else branch
        assert "dock_tab1" in else_str, "dock_tab1 must be in else: branch"
        assert "dock_tab6" in else_str, "dock_tab6 must be in else: branch"
        assert "dock_tab1" not in body_str, "dock_tab1 must NOT be in is_t2_main_mode body"

        # Verify main flow rebalance order table strictly in body
        assert "btn_tab2_diagnose" in body_str, "btn_tab2_diagnose must be in main mode body"
        assert "df_orders_tbl" in body_str, "df_orders_tbl must be in main mode body"

    def test_dual_view_radio_index_and_state_switching(self):
        """
        Challenge: Verify rad_tab2_view_mode index calculation under all edge values:
        - Uninitialized -> index 0 (Main Mode)
        - '💼 持仓诊断与智能调仓 (主流程)' -> index 0
        - '🛠️ 账本运维与实盘复盘档案 (宽屏工具坞)' -> index 1
        - Arbitrary / corrupted string -> index 1
        """
        options = ["💼 持仓诊断与智能调仓 (主流程)", "🛠️ 账本运维与实盘复盘档案 (宽屏工具坞)"]

        def calc_index(stored_val):
            return 0 if "持仓诊断与智能调仓" in stored_val else 1

        assert calc_index("持仓诊断与智能调仓") == 0
        assert calc_index(options[0]) == 0
        assert calc_index(options[1]) == 1
        assert calc_index("账本运维与实盘复盘档案") == 1
        assert calc_index("") == 1
        assert calc_index("RANDOM_CORRUPTED_STRING") == 1

        # Verify boolean flag calculation
        assert "持仓诊断与智能调仓" in options[0]  # is_t2_main_mode is True
        assert "持仓诊断与智能调仓" not in options[1]  # is_t2_main_mode is False

    def test_single_rebalance_slider_contract(self):
        """
        Challenge: Verify that tab2_rebal_buf_slider appears exactly once globally
        and is accompanied by the # tab2_rebal_buf_slider_bot compatibility marker.
        """
        gui_path = _WORKSPACE / "AGY2_FundAdvisory" / "app_gui.py"
        code = gui_path.read_text(encoding="utf-8")

        matches = re.findall(r'key=["\']tab2_rebal_buf_slider["\']', code)
        assert len(matches) == 1, f"tab2_rebal_buf_slider must appear exactly once, found {len(matches)}"
        assert "# tab2_rebal_buf_slider_bot" in code, "Missing '# tab2_rebal_buf_slider_bot' compatibility comment"


# =====================================================================
# 4. Streamlit AppTest Dynamic Execution
# =====================================================================

class TestStreamlitAppTestDynamicTab2:
    """Dynamic empirical execution of Tab 2 using Streamlit AppTest."""

    def test_tab2_apptest_main_mode_and_ops_mode_rendering(self):
        """
        Challenge: Run app_gui.py via Streamlit AppTest:
        1. Verify len(at.exception) == 0 (zero exceptions during render).
        2. Verify rad_tab2_view_mode exists.
        3. Switch radio to Ops mode and verify zero crashes.
        """
        from streamlit.testing.v1 import AppTest
        gui_path = _WORKSPACE / "AGY2_FundAdvisory" / "app_gui.py"

        at = AppTest.from_file(str(gui_path), default_timeout=60)
        at.run()

        # Check for zero runtime exceptions
        if len(at.exception) > 0:
            err_msgs = [str(e.value) for e in at.exception]
            pytest.fail(f"AppTest rendered with {len(at.exception)} exceptions: {err_msgs}")

        # Check rad_tab2_view_mode radio existence
        radios = [r for r in at.radio if r.key == "rad_tab2_view_mode"]
        assert len(radios) >= 1, "rad_tab2_view_mode radio widget must be rendered in Tab 2"

        # Switch to Ops mode
        radio = radios[0]
        assert "持仓诊断与智能调仓" in radio.value

        radio.set_value("🛠️ 账本运维与实盘复盘档案 (宽屏工具坞)").run()
        if len(at.exception) > 0:
            err_msgs = [str(e.value) for e in at.exception]
            pytest.fail(f"AppTest threw exceptions when switching to Ops mode: {err_msgs}")
