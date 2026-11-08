# BRIEFING — 2026-11-08T07:02:00Z

## Mission
Milestone 2 (M2) — GUI 交互降噪、HTML 纯化与傻瓜化操作流重构 (app_gui.py).

## 🔒 My Identity
- Archetype: worker
- Roles: implementer, qa
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\worker_g9_m2_13\
- Original parent: 2831984c-f528-4299-90cd-e299c33dd502
- Milestone: M2 (GUI Interaction Denoising, HTML Purification & Foolproof Workflow)

## 🔒 Key Constraints
- Exclusive write ownership: `AGY2_FundAdvisory/app_gui.py`, new/updated test files under `tests/`
- Strict prohibition: NEVER modify the 4 referee files: `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`
- Strict prohibition: NEVER modify `DataLoader.simulate_execution` signature or default fee logic
- Strict prohibition: NEVER modify global `c:\Users\deanc\.gemini\GEMINI.md`
- Preserve critical test keys and session state variables:
  `active_ledger_id`, `active_tier_val`, `mlm`, `pm`, `slider_target_return`, `tab1_step_reached`, `tab1_trigger_sim`, `tab2_diag_cache`, `tab2_diagnosed`, `tab2_rebal_cache`, `tab2_rebalanced`, `target_return_val`, `tab1_num_funds`, `tab1_model_type`, `custom_fund_overrides`, `purchase_limit_filter`.

## Current Parent
- Conversation ID: 2831984c-f528-4299-90cd-e299c33dd502
- Updated: 2026-11-08T07:02:00Z

## Task Summary
- **What to build**:
  1. Fix raw HTML leakage across the app: wrap all HTML in `_clean_html(...)` and route `st.markdown(..., unsafe_allow_html=True)` through `safe_markdown_html`. (Completed)
  2. Slim down dual-wing dashboard and introduce "Today's One-Sentence Foolproof Action Switch". (Completed)
  3. Tab 1 New Capital Allocation: Auto-host parameters with AI recommendations (L1 simple level) and 1-click execution sheet generation; collapse 16-card cognitive overload to 3 human-readable summary cards + expandable whitebox evidence. (Completed)
  4. Tab 2 Portfolio Rebalancing: Denoise top cards and cushion indicators, popoverize quick fund entry bar, enforce strict dual-view physical isolation (Diagnostic/Rebalance vs Ledger DevOps), single buffer slider. (Completed)
  5. Retain 100% test compatibility. (Completed)
- **Success criteria**: All existing and new tests pass cleanly; HTML code blocks completely eliminated; L1 UX simplified without breaking L2 deep audit capability.
- **Interface contracts**: `app_gui.py` public API and session state keys.

## Key Decisions Made
- [Rule 27 HTML Purification]: Wrapped all rich HTML components in `_clean_html` and replaced all raw `st.markdown(..., unsafe_allow_html=True)` calls with `safe_markdown_html`. Static scan shows 0 remaining unsafe calls.
- [Dual-Wing Dashboard]: Integrated `ActiveRiskSentry` and market environment to output "Today's Action Switch" banner (🔴 / 🟡 / 🚀 / 🟢) with cross-tab direct jump button.
- [Tab 1 L1/L2 Decoupling]: Compacted Step 1 to capital input + C1-C5 choice, moving 7 models & quota filters into auto-hosted panel. Merged execution button into 1-click generation. Step 2 shows 3 core human cards (How to make money / Risk floor / Why we can win) with a collapsible drawer for whitebox tests.
- [Tab 2 Denoising & Popover]: Packaged -3%/-5%/-10% stress scenarios into an accordion inside the cushion card. Replaced 5-column quick entry bar with a Popover inside the holdings table toolbar. Indented tools dock under `else:` branch for strict physical isolation.

## Change Tracker
- **Files modified**:
  - `AGY2_FundAdvisory/app_gui.py`: Complete M2 implementation.
  - `tests/test_sidebar_remodel_and_bugfixes.py`: Updated path resolution for AGY2_FundAdvisory workspace structure.
- **Build status**: 100% PASS (60/60 core tests pass, 20/20 stress tests pass).
- **Pending issues**: None.

## Quality Status
- **Build/test result**: 60 passed in 78.05s on core suite; 20 passed in 38.63s on stress suite.
- **Lint status**: Clean (py_compile passed with 0 errors).
- **Tests added/modified**: `tests/test_sidebar_remodel_and_bugfixes.py` verified and passing.

## Artifact Index
- `.agents/teamwork/worker_g9_m2_13/DISPATCH.md` — Dispatch instructions
- `.agents/teamwork/worker_g9_m2_13/BRIEFING.md` — Situational awareness
- `.agents/teamwork/worker_g9_m2_13/progress.md` — Liveness & progress tracking
- `.agents/teamwork/worker_g9_m2_13/handoff.md` — Final handoff report
