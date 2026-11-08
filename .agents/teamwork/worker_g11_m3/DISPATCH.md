# Task Assignment: Worker 3 (Milestone 3 - Test Suite Alignment & Invariant Verification)

## Target Files Ownership
- `tests/test_adv_final_closure.py`
- `tests/test_g3_evolution_loop.py`
- `tests/test_gui_multi_ledger_stress.py`
- `AGY2_FundAdvisory/portfolio_manager.py` (or `app_gui.py`) for order string matching alignment

## Strict Read-Only Files (DO NOT TOUCH)
- `AGY2_FundAdvisory/judge_engine.py`
- `AGY2_FundAdvisory/holdout_vault.py`
- `AGY2_FundAdvisory/AGENT_SPEC.md`
- `tests/test_infra.py`
- `DataLoader.simulate_execution` signature & fee logic
- `c:\Users\deanc\.gemini\GEMINI.md`

## Objectives
1. Align UI test suites with G11 Three-Block streamlined GUI per R1 & R4:
   - Check `tests/test_adv_final_closure.py`, `tests/test_g3_evolution_loop.py`, `tests/test_gui_multi_ledger_stress.py`.
   - Update assertions that check for old duplicate buttons (`btn_t1_run_all`, `col_s1_step`/`col_s1_all`), old step indicator bars, or old banner text. Do NOT allow old tests to force redundant buttons or banners to stay on the GUI.
2. Fix one-click rebalance string matching:
   - Ensure `apply_rebalance_orders_to_holdings` in `portfolio_manager.py` (or `app_gui.py`) supports `"加仓"` / `"建议加仓"` as buy/increase, and `"减仓"` / `"建议减仓"` as sell/reduce, in addition to `"增持"` / `"减持"` / `"买入"`.
   - Ensure clicking the one-click follow rebalance button correctly applies the orders to holdings.
3. Baseline Ledger Hygiene:
   - Ensure `portfolio_ledger.json` and `data/ledgers_index.json` are clean and match the baseline main live portfolio.
4. Run full test verification:
   - `pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py`
   - All tests must pass 100% green.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Document your changes and full pytest outputs in `d:\Google\Workspace\Wind\.agents\teamwork\worker_g11_m3\handoff.md`.

## 2026-11-08T14:13:49Z
[Message] timestamp=2026-11-08T14:13:49Z sender=c6b4ebd0-c5f1-4175-8ba5-3bd0979b970d priority=MESSAGE_PRIORITY_HIGH content=You are worker_g11_m3.
Your working directory is `d:\Google\Workspace\Wind\.agents\teamwork\worker_g11_m3\`.
Read your task in `d:\Google\Workspace\Wind\.agents\teamwork\worker_g11_m3\DISPATCH.md`.
Read `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`.
Read `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_15\PROJECT.md`.
Read Explorer 3 handoff `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g11_survey_3\handoff.md` and Challenger 2 handoff `d:\Google\Workspace\Wind\.agents\teamwork\challenger_g11_m2_2\handoff.md`.

You own:
- `tests/test_adv_final_closure.py`
- `tests/test_g3_evolution_loop.py`
- `tests/test_gui_multi_ledger_stress.py`
- Order string matching alignment in `AGY2_FundAdvisory/portfolio_manager.py` (or `app_gui.py`)

Strict read-only files (ZERO MODIFICATIONS):
- `AGY2_FundAdvisory/judge_engine.py`
- `AGY2_FundAdvisory/holdout_vault.py`
- `AGY2_FundAdvisory/AGENT_SPEC.md`
- `tests/test_infra.py`
- `DataLoader.simulate_execution` signature and deduction logic
- `c:\Users\deanc\.gemini\GEMINI.md`

Objectives:
1. Update assertions checking for old duplicate buttons (`btn_t1_run_all`, `col_s1_step`/`col_s1_all`), old step indicator bars, or old banner text in `tests/test_adv_final_closure.py`, `tests/test_g3_evolution_loop.py`, `tests/test_gui_multi_ledger_stress.py` to match the G11 Three-Block streamlined UI.
2. Fix one-click rebalance string matching so `apply_rebalance_orders_to_holdings` accepts `"加仓"`, `"建议加仓"`, `"减仓"`, `"建议减仓"` alongside `"增持"`, `"减持"`, `"买入"`.
3. Clean ledger baselines: `git checkout -- portfolio_ledger.json data/portfolio_watchdog.json`.
4. Run full test verification:
   `pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py`
   All must pass 100% green.
