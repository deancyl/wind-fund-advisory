# DISPATCH for explorer_g9_survey_3

## Objective
Survey and deeply investigate R1 & R4: 核心安全底线契约、测试兼容性基线与视觉走查/自举验收方案.

## Inputs
- `judge_engine.py` (read-only)
- `holdout_vault.py` (read-only)
- `AGENT_SPEC.md` (read-only)
- `tests/test_infra.py` (read-only)
- `tests/test_adv_final_closure.py`
- `tests/test_g3_evolution_loop.py`
- `tests/test_gui_multi_ledger_stress.py`
- `AGY2_FundAdvisory/app_gui.py`
- `.agents/teamwork/ORIGINAL_REQUEST.md`

## Specific Investigation Tasks
1. Read-only Judge & DataLoader verification:
   - Calculate and record baseline SHA-256 hashes of the four judge files: `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`.
   - Inspect `DataLoader.simulate_execution` signature and default fee logic.
2. Existing Test Suite Compatibility:
   - Analyze all existing test files and catalog what `session_state` keys, widget keys, and functions they test in `app_gui.py`.
   - Ensure the GUI refactoring will NOT break any existing test assertions.
3. New G9 Test Plan:
   - Design specific test cases for:
     a) Causal factor evolver lag ($P[t]$ to $R[t+1]$) and 10 bps turnover friction.
     b) 2.0% risk-free rate deduction in Sharpe ratio.
     c) 5-day walk-forward rolling trajectory.
     d) A-share calendar alignment and removal of fake linear sequence.
     e) AUM lookup penetration and removal of 2.5B fallback.
     f) Dynamic quantitative evidence in sector evaluation.
     g) C1-C5 appropriateness boundary alert in ActiveRiskSentry.
     h) Brinson 3D excess attribution.
     i) HTML string purification and zero 4+ space indent codes.
     j) Tab 1 and Tab 2 L1/L2 progressive disclosure keys.
4. Multimodal Visual Walkthrough & Version Self-Bootstrapping:
   - Detail procedure for restarting 8501 and running `/browser` inspection on desktop and 640px mobile view.
   - Outline git release protocol: tag `v3.9-G9`, no GitHub Release, clean plain-text G10 instruction generator.

## Output
Write comprehensive survey and technical recommendations to:
`d:\Google\Workspace\Wind\.agents\teamwork\explorer_g9_survey_3\handoff.md`

## 2026-11-08T05:51:40Z
[Message from parent e2e9b1b9-848d-4b67-b5e8-3f65177957b7]:
You are explorer_g9_survey_3 (Role: Test Baseline Explorer).
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g9_survey_3
Read d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md before starting work.
Read d:\Google\Workspace\Wind\.agents\teamwork\explorer_g9_survey_3\DISPATCH.md for your detailed task requirements.

Investigate R1 & R4:
1. Four read-only judge files: judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py. Record SHA-256 hashes and verify constraints.
2. DataLoader.simulate_execution default function signature and deduction logic: verify exact status.
3. Compatibility with existing test suites:
   - tests/test_infra.py
   - tests/test_adv_final_closure.py
   - tests/test_g3_evolution_loop.py
   - tests/test_gui_multi_ledger_stress.py
   Catalog all session_state keys and widgets used by tests to ensure zero regressions during GUI refactoring.
4. Design new G9 test assertions for:
   - Causal factor evolver lag (P[:-1] to R[1:]) and 10 bps turnover deduction.
   - 2.0% risk-free rate deduction in Sharpe ratio.
   - 5-day walk-forward rolling trajectory.
   - A-share calendar alignment and no np.linspace fake series.
   - Real AUM lookup and no 2.5B fake scale fallback.
   - Dynamic quantitative evidence in sector evaluation.
   - C1-C5 appropriateness boundary alert.
   - Brinson 3D excess attribution.
   - HTML string purification and zero 4+ space indent code leaks.
   - Tab 1 and Tab 2 L1/L2 progressive disclosure keys.
5. Verification workflow: 8501 restart and health check, /browser inspection plan, git tag v3.9-G9, clean plain-text G10 instruction generator.

Write your findings and test specification to:
d:\Google\Workspace\Wind\.agents\teamwork\explorer_g9_survey_3\handoff.md

When complete, send a message to orchestrator_12 notifying completion.
