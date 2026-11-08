# BRIEFING — 2026-11-08T12:02:00Z

## Mission
Investigate AGY2_FundAdvisory/app_gui.py for Top Area and Tab 1 refactoring per requirements R1 & R2, reference specs, produce structured handoff report.

## 🔒 My Identity
- Archetype: explorer
- Roles: survey, investigation, synthesis
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g11_survey_1\
- Original parent: c6b4ebd0-c5f1-4175-8ba5-3bd0979b970d
- Milestone: G11 Minimalist Refactoring Survey (Top Area & Tab 1)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Workspace-only learn invariant (do NOT write outside working directory metadata)
- Thorough line-by-line inspection of app_gui.py top area and Tab 1

## Current Parent
- Conversation ID: c6b4ebd0-c5f1-4175-8ba5-3bd0979b970d
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `AGY2_FundAdvisory/app_gui.py` (CSS, Top Area, Dual-Wing expander, Tab 1 end-to-end)
  - `tests/test_infra.py`, `tests/test_adv_final_closure.py`, `tests/test_g3_evolution_loop.py`, `tests/test_g8_ux_and_realtime_fusion.py`, `tests/test_g10_correlation_liquidity_and_stress.py`, `tests/test_anticheat_full_closure.py`, `tests/test_challenger_g9_m2_stress.py`, `tests/test_challenger_g9_m2_adversarial.py`
  - Reference specs: `agy2_fundadvisory_ultra_minimalist_spec.md`, `agy2_app_gui (2).md`, `ORIGINAL_REQUEST.md`
- **Key findings**:
  1. Top Area: 4 cards currently at lines 2558-2638 with min-height 88px. Standalone banner at lines 2761-2772 and cross-action banner at lines 3147-3160 clutter the top. Dual-wing expander at line 2787 should absorb the today action conclusion.
  2. Tab 1: Spans lines 3220-4537. Contains step indicator (3272), caption (3233), gray AI box (3347), duplicate buttons (3617-3634), 3-step artificial gates (3638, 4080), PCR banner (4198), summary advice (4411).
  3. Tab 1 Refactoring: Can be cleanly restructured into 3 modules: Module 1 (single-line control bar with popover & single primary button), Module 2 (compact 3-column metric bar + execution dataframe), Module 3 (4-button action bar + single white-box expander).
  4. Test Compatibility: `tab1_sel_model_type` must use clean names to pass `test_anticheat_full_closure.py:404`. Keep `# 跨区联动指令已生效承接横幅` comment for `test_g8_ux_and_realtime_fusion.py:222`. Preserve keys `chk_confirm_t1_overwrite`, `btn_apply_bp_tier`, `btn_undo_t1_overwrite`, `btn_confirm_save_new_ledger`, `btn_send_bp_to_bt`.
- **Unexplored areas**: Tab 2 and Tab 3/4 refactoring (handled by peer agents).

## Key Decisions Made
- Mapped exact line ranges and proposed refactoring chunks for Top Area and Tab 1.
- Documented test compatibility requirements to avoid regressions.
- Outlined precise CSS modifications for 82px card lock and 1.2rem container padding.

## Artifact Index
- DISPATCH.md — task assignment
- BRIEFING.md — persistent working memory
- progress.md — liveness heartbeat
- handoff.md — comprehensive survey and implementation blueprint

