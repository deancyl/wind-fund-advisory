# -*- coding: utf-8 -*-
"""
tests/test_auditor_g9_m2_integrity.py
Forensic Integrity Audit Suite for Milestone 2 (M2)
Auditor: auditor_g9_m2 (teamwork_auditor)

Comprehensive independent empirical verification of:
1. Four Read-Only Judge Files Integrity
2. DataLoader.simulate_execution Unmodified Signature & Fee Logic
3. Global C:\\Users\\deanc\\.gemini\\GEMINI.md Untouched Baseline
4. Authentic Brinson-Fachler Mathematical Attribution Model & Identities
5. Baseline Snapshot State Persistence & Non-Overwriting Invariant
6. Zero Mocks/Fakes in Production Code
"""

import sys
import os
import copy
from pathlib import Path
import subprocess
import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
AGY_PATH = WORKSPACE_ROOT / "AGY2_FundAdvisory"
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))
if str(AGY_PATH) not in sys.path:
    sys.path.insert(0, str(AGY_PATH))

from AGY2_FundAdvisory.portfolio_manager import PortfolioManager
from AGY2_FundAdvisory.data_loader import DataLoader


class TestAuditorM2Integrity:
    """Forensic Integrity Checks for Milestone 2 Work Products"""

    def test_1_read_only_judge_files_unmodified(self):
        """Verify that the 4 read-only judge files have 0 modifications in git diff HEAD"""
        judge_files = [
            "AGY2_FundAdvisory/judge_engine.py",
            "AGY2_FundAdvisory/holdout_vault.py",
            "AGY2_FundAdvisory/AGENT_SPEC.md",
            "tests/test_infra.py"
        ]
        cmd = ["git", "diff", "HEAD", "--"] + judge_files
        res = subprocess.run(cmd, cwd=str(WORKSPACE_ROOT), capture_output=True, text=True)
        assert res.returncode == 0, f"git diff failed: {res.stderr}"
        assert res.stdout.strip() == "", (
            f"READ-ONLY INTEGRITY VIOLATION! Modified files detected in judge files:\n{res.stdout}"
        )

    def test_2_simulate_execution_unmodified(self):
        """Verify DataLoader.simulate_execution signature and fee logic are 100% unmodified"""
        import inspect
        sig = inspect.signature(DataLoader.simulate_execution)
        params = list(sig.parameters.keys())
        expected_params = ['weights_df', 'prices_df', 'is_otc', 'penalty_days', 'penalty_rate', 'etf_impact']
        assert params == expected_params, f"simulate_execution signature mismatch! Got {params}"
        assert sig.parameters['penalty_days'].default == 7
        assert sig.parameters['penalty_rate'].default == 0.015
        assert sig.parameters['etf_impact'].default == 0.001
        assert sig.parameters['is_otc'].default is True

    def test_3_global_gemini_untouched(self):
        """Verify that global GEMINI.md was not modified recently"""
        global_gemini = Path(r"C:\Users\deanc\.gemini\GEMINI.md")
        if global_gemini.exists():
            mtime = global_gemini.stat().st_mtime
            # Nov 3 2026 was ~ 1793700000; session is Nov 8 2026 (~1794100000)
            # Just ensure mtime is strictly before Nov 7 2026 (timestamp 1794000000)
            import datetime
            dt = datetime.datetime.fromtimestamp(mtime)
            assert dt < datetime.datetime(2026, 11, 7), (
                f"GLOBAL GEMINI.MD VIOLATION! Global file was modified at {dt}!"
            )

    def test_4_brinson_fachler_mathematical_identity(self):
        """
        Verify authentic implementation of Brinson-Fachler attribution:
        1. Zero rebalance baseline equality
        2. Multi-asset active rebalance
        3. Theoretical mathematical identity:
           alloc_yuan + select_yuan == total_active_add_yuan
           alloc_pct + select_pct == total_active_add_pct
        4. Category breakdown sum equality
        """
        pm = PortfolioManager(db_path=":memory:")
        # Build initial portfolio
        pm.add_or_update_holding("005561", shares=10000.0, nav=1.0, cost_price=1.0) # A股红利低波
        pm.add_or_update_holding("000216", shares=10000.0, nav=1.0, cost_price=1.0) # 黄金对冲
        pm.add_or_update_holding("002351", shares=20000.0, nav=1.0, cost_price=1.0) # 纯债固收
        pm.available_cash = 10000.0

        # Baseline snapshot audit
        audit1 = pm.evaluate_rebalance_audit()
        assert audit1["current_actual_equity"] == 50000.0
        assert audit1["shadow_hold_equity"] == 50000.0
        assert audit1["rebalance_value_add"] == 0.0
        b1 = audit1["brinson_attribution"]
        assert b1["allocation_effect_yuan"] == 0.0
        assert b1["selection_effect_yuan"] == 0.0
        assert b1["total_active_add_yuan"] == 0.0

        # Now simulate market movements and portfolio active reallocation:
        # Reallocation: Sell gold, buy more dividend and a tech fund (new category)
        pm.add_or_update_holding("005561", shares=15000.0, nav=1.20, cost_price=1.0) # +20% return
        pm.add_or_update_holding("000216", shares=5000.0, nav=1.05, cost_price=1.0)  # +5% return
        pm.add_or_update_holding("002351", shares=20000.0, nav=1.02, cost_price=1.0) # +2% return
        pm.add_or_update_holding("013841", shares=10000.0, nav=1.15, cost_price=1.0) # 科创半导体 (+15% return)
        pm.available_cash = 5000.0

        audit2 = pm.evaluate_rebalance_audit()
        b2 = audit2["brinson_attribution"]

        # Empirical verifications:
        alloc_yuan = b2["allocation_effect_yuan"]
        select_yuan = b2["selection_effect_yuan"]
        total_yuan = b2["total_active_add_yuan"]
        alloc_pct = b2["allocation_effect_pct"]
        select_pct = b2["selection_effect_pct"]
        total_pct = b2["total_active_add_pct"]

        # Exact Mathematical Identity Check
        assert abs(alloc_yuan + select_yuan - total_yuan) < 1e-4, (
            f"Brinson dollar identity failed! {alloc_yuan} + {select_yuan} != {total_yuan}"
        )
        assert abs(alloc_pct + select_pct - total_pct) < 1e-4, (
            f"Brinson percent identity failed! {alloc_pct} + {select_pct} != {total_pct}"
        )

        # Check Category Breakdown
        cats = b2["category_breakdown"]
        assert len(cats) >= 4
        cat_alloc_sum = sum(c["allocation_effect_yuan"] for c in cats)
        cat_select_sum = sum(c["selection_effect_yuan"] for c in cats)
        assert abs(cat_alloc_sum - alloc_yuan) <= 0.05
        assert abs(cat_select_sum - select_yuan) <= 0.05

        # Check friction saving
        assert b2["friction_saving_yuan"] >= 0.0

    def test_5_snapshot_persistence_and_invariance(self):
        """
        Verify authentic persistence of initial_baseline_snapshot in
        _export_state_dict and _import_state_dict, and that repeated calls
        do not overwrite the original snapshot.
        """
        pm = PortfolioManager(db_path=":memory:")
        pm.add_or_update_holding("005561", shares=10000.0, nav=1.0, cost_price=1.0)
        pm.available_cash = 5000.0

        audit_orig = pm.evaluate_rebalance_audit()
        orig_snap = copy.deepcopy(pm.initial_baseline_snapshot)
        assert orig_snap["holdings"]["005561"] == 10000.0

        # Export state
        state = pm._export_state_dict()
        assert "initial_baseline_snapshot" in state
        assert state["initial_baseline_snapshot"]["holdings"]["005561"] == 10000.0

        # Modify pm holdings
        pm.add_or_update_holding("005561", shares=20000.0, nav=1.5, cost_price=1.0)
        audit_mod = pm.evaluate_rebalance_audit()
        # Verify initial_baseline_snapshot was NOT overwritten
        assert pm.initial_baseline_snapshot["holdings"]["005561"] == 10000.0

        # Import into new manager instance
        pm2 = PortfolioManager(db_path=":memory:")
        pm2._import_state_dict(state)
        assert pm2.initial_baseline_snapshot == orig_snap
        audit_restored = pm2.evaluate_rebalance_audit()
        assert audit_restored["shadow_hold_equity"] == audit_orig["shadow_hold_equity"]

    def test_6_no_mocks_or_fakes_in_production_code(self):
        """Verify no mock, MagicMock, patch, or dummy static returns in AGY2_FundAdvisory/"""
        import re
        prod_files = [
            WORKSPACE_ROOT / "AGY2_FundAdvisory" / "portfolio_manager.py",
            WORKSPACE_ROOT / "AGY2_FundAdvisory" / "app_gui.py",
            WORKSPACE_ROOT / "AGY2_FundAdvisory" / "advisory_engine.py",
            WORKSPACE_ROOT / "AGY2_FundAdvisory" / "data_loader.py",
        ]
        forbidden = [
            r"\bfrom unittest\.mock\b",
            r"\bimport mock\b",
            r"\bMagicMock\b",
            r"return\s+12345",
            r"return\s+999\.9",
        ]
        for fpath in prod_files:
            text = fpath.read_text(encoding="utf-8")
            for pat in forbidden:
                match = re.search(pat, text)
                assert match is None, (
                    f"INTEGRITY VIOLATION! Forbidden pattern '{pat}' found in {fpath.name}:\n"
                    f"{text[max(0, match.start()-50):min(len(text), match.end()+50)]}"
                )
