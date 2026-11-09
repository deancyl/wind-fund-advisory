# Forensic Integrity Audit Report — Milestone 1

**Work Product**: Milestone 1 Deliverables (`app_gui.py`, `portfolio_manager.py`, `strategy_bridge.py`, `tests/test_delta_m1_guardrails.py`)  
**Profile**: General Project (Forensic Integrity)  
**Auditor**: `auditor_m1_1`  
**Date**: 2026-11-10T01:23:30Z  
**Verdict**: **CLEAN**

---

## 1. Observation

Direct empirical observations from independent tool commands and code inspections:

### 1.1 Physical Referee Protection
SHA256 checksums and git status of the four protected referee files and `DataLoader`:

| File | SHA256 Checksum | Git Diff Status | Result |
|---|---|---|---|
| `AGY2_FundAdvisory/judge_engine.py` | `76f930371176de7ee6a413174b030101e3210ac6e037f5d10fe229af31cc07be` | 0 lines modified (Clean) | **PASS** |
| `AGY2_FundAdvisory/holdout_vault.py` | `88122eaf647040a410e2fd95da81077db10149a498a47340ff40b670bd031d2a` | 0 lines modified (Clean) | **PASS** |
| `AGY2_FundAdvisory/AGENT_SPEC.md` | `a346586f9bd2dc0ee83e665bd18e7a6471464c9f7b658e392b989b800cd63957` | 0 lines modified (Clean) | **PASS** |
| `tests/test_infra.py` | `48bee0da300d7c0a0848ec1376e4b9b2e55224d2736081713b4340f0362cd100` | 0 lines modified (Clean) | **PASS** |
| `AGY2_FundAdvisory/data_loader.py` | `a501ae047ea6bbd4d4d453a42a2dff79e8a53c0d7a669d52b2f4141874315cf1` | 0 lines modified (Clean) | **PASS** |

- `DataLoader.simulate_execution` signature in `AGY2_FundAdvisory/data_loader.py:1437`:
  ```python
  @staticmethod
  def simulate_execution(
      weights_df: pd.DataFrame,
      prices_df: pd.DataFrame,
      is_otc: bool = True,
      penalty_days: int = 7,
      penalty_rate: float = 0.015,
      etf_impact: float = 0.001
  ) -> pd.DataFrame:
  ```
  The signature and default 7-day 1.50% penalty fee logic are 100% intact with zero modifications.

### 1.2 Anti-Cheating & Source Code Verification
Git diff inspection across all modified files (`portfolio_manager.py`, `strategy_bridge.py`, `app_gui.py`):
1. **3D Chart & RuleTree Removal**:
   - `render_monte_carlo_stress_table` in `app_gui.py:2147` dynamically constructs a 2D table from `stress_data.get("scenarios")` evaluating predicted MDD, loss amount, H300 comparison, excess defense, and contract compliance against `risk_tolerance_mdd`.
   - Call sites in Tab 1 (`app_gui.py:4461`) and Tab 2 (`app_gui.py:5288`) invoke `render_monte_carlo_stress_table` directly.
   - Compatibility alias `render_monte_carlo_3d_chart` in `app_gui.py:2194` delegates to `render_monte_carlo_stress_table`.
   - The obscure `st.code(rule_expr_txt)` block in the factor evolution popover (`app_gui.py:3145-3151`) is replaced with an actionable 2D parameter mechanism table (`df_rule`).
2. **Right-Wing Alert Sentry**:
   - Alert sorters (`_top_lvl_rank` at line 3062 and `_sentry_alert_sorter` at line 3274) rank `("red", "critical")` at priority `(0, 0)`, `("yellow", "warning")` at `(1, 0)`, and "规模待核验" at `(1, 1)`.
   - Details are extracted via `alert.get("desc") or alert.get("detail") or alert.get("message", "")`.
   - Actions are extracted via `alert.get("action") or alert.get("suggested_action", "")`.
   - No mock stubs or artificial hardcoded values.
3. **Tab 2 DataFrame Column Formatting**:
   - `format_micro_execution_slices_df` in `app_gui.py:2199` is a genuine DataFrame transformer that maps `phase, label, vol_ratio, slice_amount, strategy` to Chinese headers, with percentage and currency formatting.
   - Rendered via `st.dataframe(format_micro_execution_slices_df(sample_slices))` in Tab 1 (`line 4692`) and Tab 2 (`line 5976`).
   - The duplicate full-width overwrite button was cleanly excised from the bottom of Tab 2; action buttons are organized into a concise 3-part layout (`col_exec_ai`, `col_copy_sheet`, `col_send_bt`).
4. **Tab 4 Secondary Navigation**:
   - `app_gui.py:7240` implements single-row navigation via `st.segmented_control` with `st.radio(horizontal=True)` fallback.
   - Individual sub-modules render selectively based on `if sel_sub_mod == "...":`.
5. **017436 Name Unification**:
   - Unified as `"华安纳斯达克100ETF联接A"` in `portfolio_manager.py` (lines 842, 847), `strategy_bridge.py` (lines 491, 588, 704, 820), and `app_gui.py` (line 2327).
   - In `strategy_bridge.py:3792`, `h_holding_days` defaults to `-1` when a fund is not currently held, preventing false 7-day penalty lock-ins on new buy targets.
6. **Mobile View Mode**:
   - `app_gui.py:2468` provides `app_view_layout_mode` radio switch.
   - `app_gui.py:2746-2861` implements a dedicated 3-card mobile stream:
     1. Card 1: Total equity, daily estimated PnL, and cumulative profit.
     2. Card 2: 14:30 operational window directives and lock-in notices.
     3. Card 3: Core risk warnings (red/yellow) and screenshot uploader.
     4. Concludes with `st.stop()` to eliminate desktop tables and visual noise.

### 1.3 Test Suite Execution
Independently executed the test suites from clean Python 3.11 environment:

```
1. py -3 -m pytest tests/test_infra.py
   Result: 14 passed in 5.99s (100% pass, 0 failed, 0 skipped)

2. py -3 -m pytest tests/test_adv_final_closure.py
   Result: 14 passed in 39.07s (100% pass, 0 failed, 0 skipped)

3. py -3 -m pytest tests/test_delta_m1_guardrails.py
   Result: 5 passed in 28.34s (100% pass, 0 failed, 0 skipped)
```
Total: **33 tests passed, 0 failed, 0 skipped**.

---

## 2. Logic Chain

1. **Referee File Integrity**:
   - Physical referee protection mandates zero modifications to `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`, and `DataLoader.simulate_execution`.
   - Inspection of git status and SHA256 hashes shows 0 byte alterations across all referee targets.
   - `DataLoader.simulate_execution` maintains its exact signature and fee calculation logic.
   - Therefore, the physical referee boundary remains intact and uncompromised.

2. **Absence of Cheating or Facades**:
   - Inspection of the AST and source code of all changes confirms that `render_monte_carlo_stress_table`, `format_micro_execution_slices_df`, and `_sentry_alert_sorter` are genuine algorithms operating on dynamic runtime inputs.
   - No hardcoded string returns or mock return constants bypass real business logic.
   - Fund naming unification was verified across catalog dictionaries and bridge lookup routes.

3. **Empirical Verification of Tests**:
   - All 33 unit and integration tests were executed independently by the auditor.
   - All test assertions evaluate genuine conditions without mocks that bypass the underlying modules.
   - Zero test failures or skipped items were encountered.

---

## 3. Caveats

- `tests/test_adv_final_closure.py` emits urllib3 insecure HTTPS warnings for external EastMoney quotation endpoints; these are network deprecation warnings and do not affect test logic or code integrity.
- In environments running Streamlit versions prior to 1.40, `st.segmented_control` falls back gracefully to `st.radio(horizontal=True)`.

---

## 4. Conclusion

All forensic integrity checks pass without violation.
- **Physical Referee Protection**: 100% Unmodified
- **Code Authenticity**: 100% Genuine Implementation
- **Test Suite Pass Rate**: 33/33 (100%)
- **Verdict**: **CLEAN**

The Milestone 1 work product is fully accepted and approved for Milestone 2 progression.

---

## 5. Verification Method

To independently reproduce the forensic verification:

```bash
# 1. Verify referee file hashes
py -3 -c "import hashlib; print([hashlib.sha256(open(f, 'rb').read()).hexdigest() for f in ['AGY2_FundAdvisory/judge_engine.py', 'AGY2_FundAdvisory/holdout_vault.py', 'AGY2_FundAdvisory/AGENT_SPEC.md', 'tests/test_infra.py', 'AGY2_FundAdvisory/data_loader.py']])"

# 2. Run independent test suite
py -3 -m pytest tests/test_infra.py
py -3 -m pytest tests/test_adv_final_closure.py
py -3 -m pytest tests/test_delta_m1_guardrails.py
```
