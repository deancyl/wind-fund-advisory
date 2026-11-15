# BRIEFING — 2026-11-15T08:10:00Z

## Mission
Investigate Feature 6 (Capsule 4 and Capsule 5 unified coordination in `generate_chief_advisor_memo` & `render_chief_advisor_memo_card`) and Test Coverage / Compatibility for Milestone 1 (Features 1-6). Formulate exact implementation design and comprehensive test suite `tests/test_g19_m1_ten_dimension_and_memo.py`.

## 🔒 My Identity
- Archetype: explorer
- Roles: investigation, synthesis
- Working directory: d:\Google\Workspace\Wind
- State folder: d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_3
- Original parent: a29ecba0-a4ab-4a58-a8c7-4276082800c0
- Milestone: Milestone 1 (M1: 十维真实投票与汇率校验及胶囊联动)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Do NOT edit source files or existing tests
- Adhere to GEMINI.md rules (Chinese response, no hardcoded limits, safe UI/layout invariants, etc.)
- Referee files are read-only: judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py
- DataLoader.simulate_execution default signature & default fee logic strictly preserved

## Current Parent
- Conversation ID: a29ecba0-a4ab-4a58-a8c7-4276082800c0
- Updated: 2026-11-15T08:10:00Z

## Investigation State
- **Explored paths**:
  - `AGY2_FundAdvisory/advisory_engine.py`: lines 4460-4835 (`generate_chief_advisor_memo`), lines 2131-2570 (`ActiveRiskSentry`)
  - `AGY2_FundAdvisory/app_gui.py`: lines 268-458 (`render_chief_advisor_memo_card`), line 301 (6.6676 fallback), line 288 (None timestamp split bug), lines 3645-3657 (`generate_chief_advisor_memo` caller in GUI)
  - `AGY2_FundAdvisory/data_loader.py`: line 1436 (`DataLoader.simulate_execution` signature)
  - Referee files verified: `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py` (SHA256 intact, 14/14 tests pass)
  - Real combat 29-fund inspection: `deep_loss_count: 18, frag_count: 19, frag_amt: 442.7` confirmed live while Capsule 5 was producing disconnected `维持底仓吃息`
  - Existing test audit: `test_g17_advisory_real_data_and_ten_dimension.py` (5/5 passed), `test_g16_phase1_memo_and_combat29.py` (10 passed, 1 line 219 fails due to `建仓标的` missing from compact capsule sub), `test_challenger_m1_adv_memo.py` (adversarial None timestamp crash in line 288)
- **Key findings**:
  - Live reproduction confirmed: For `combat_29_funds`, Capsule 4 reports 18 deep loss funds and 19 tail fragments, while Capsule 5 blindly reports "维持底仓吃息" based solely on macro ERP/Bias, creating a complete disconnect.
  - Fix design: When `frag_count > 0` or `deep_loss_count > 0` or stop-profit red alerts exist, Capsule 5 prioritizes account-level actionable directives: e.g. `清扫19只尾仓·置换深套` with subtitle `清扫19只尾仓 ｜ 置换18只深套`.
  - GUI alignment: `render_chief_advisor_memo_card` top banner `今日裁决` automatically aligns with Capsule 5 verdict, Card 4 renders `建仓标的分散 ｜ 结构优良` in construction mode (fixing G16 test), and `ts` handles None safely.
  - Comprehensive M1 test suite designed for `tests/test_g19_m1_ten_dimension_and_memo.py` covering Features 1 through 6.
- **Unexplored areas**: None for M1 Feature 6 & Test Coverage scope.

## Key Decisions Made
- Fully documented 5-component handoff report with exact line-by-line diff proposals for the Worker.
- Complete test suite architecture designed covering Features 1-6.

## Artifact Index
- DISPATCH.md — Task dispatch
- BRIEFING.md — Persistent context
- progress.md — Liveness heartbeat
- handoff.md — 5-component handoff report
