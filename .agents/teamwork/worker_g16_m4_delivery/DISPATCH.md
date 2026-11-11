# DISPATCH — worker_g16_m4_delivery

## Role
teamwork_worker

## Working Directory
d:\Google\Workspace\Wind

## State Folder
d:\Google\Workspace\Wind\.agents\teamwork\worker_g16_m4_delivery\

## Input Documents
- ORIGINAL_REQUEST.md: `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`
- SCOPE.md: `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_g16_gen4\SCOPE.md`

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations and verifications must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work.

## PHYSICAL REDLINE INVARIANTS
1. NEVER modify the 4 read-only referee files:
   - `AGY2_FundAdvisory/judge_engine.py` (or root `judge_engine.py`)
   - `AGY2_FundAdvisory/holdout_vault.py` (or root `holdout_vault.py`)
   - `AGY2_FundAdvisory/AGENT_SPEC.md` (or root `AGENT_SPEC.md`)
   - `tests/test_infra.py` (or `AGY2_FundAdvisory/tests/test_infra.py`)
2. NEVER modify `DataLoader.simulate_execution` signature or default parameters or fee logic.
3. NEVER touch global GEMINI.md (`c:\Users\deanc\.gemini\GEMINI.md`). Update ONLY workspace root `d:\Google\Workspace\Wind\GEMINI.md`!
4. DO NOT create GitHub Release. Only git tag `v4.6-G16` and push tag to origin.

## Task Breakdown
### Task 1: Full Regression Test Suite Execution
Run all specified test targets:
- `py -3 -m pytest tests/test_infra.py -v`
- `py -3 -m pytest tests/test_adv_final_closure.py -v`
- `py -3 -m pytest tests/test_g3_evolution_loop.py -v`
- `py -3 -m pytest tests/test_gui_multi_ledger_stress.py -v`
- `py -3 -m pytest tests/test_g16_phase1_memo_and_combat29.py -v`
- `py -3 -m pytest tests/test_m3_item2_rebalance_impact.py tests/test_m3_item3_tab3_backtest.py tests/test_m3_adversarial_challenger2_stress.py -v`
- `py -3 -m pytest tests/test_multi_ledger_manager.py tests/test_multi_ledger_manager_stress.py tests/test_adversarial_m3_combat29_challenger.py -v`
- `py -3 -m pytest AGY2_FundAdvisory/tests/test_e2e_gui_render.py -v`
Ensure 100% pass across all suites. If `portfolio_ledger.json` was touched by tests, restore it.

### Task 2: Service Restart & Health Verification
1. Check port 8501: `netstat -ano | findstr 8501`
2. If listening process exists, terminate it cleanly (`Stop-Process -Id <pid> -Force`).
3. Start Streamlit in detached background mode:
   `Start-Process py -ArgumentList '-3 -m streamlit run AGY2_FundAdvisory/app_gui.py --server.port 8501 --server.headless true' -WindowStyle Hidden`
4. Verify HTTP 200 health probe: `Invoke-WebRequest -Uri http://localhost:8501 -UseBasicParsing`

### Task 3: Visual Inspection & Screenshots
Using a Python script with Playwright (or selenium/headless chrome) or Python script capturing the rendered DOM, verify the 4 core views:
1. Screen 1: Top control bar + 1-row-5-col horizontal memo cards (showing deep loss >10% and 19 fragments ¥442.70 on 29 funds ledger).
2. Screen 2: Tab 2 3-step prescription panel for 29 funds.
3. Screen 3: Tab 3 29 vs 6 backtest dual curves.
4. Screen 4: Mobile minimal view.
Save screenshots in `data/screenshots/g16/` or state folder.

### Task 4: Documentation & Git Archiving
1. Update workspace root `GEMINI.md` with G16 learned lessons (Rules 27-30+).
2. Update workspace root `PROGRESS_LOG.md` with G16 milestone summary.
3. Git operations:
   - `git add -A`
   - `git commit -m "feat(g16): 五维投顾备忘录首屏横向矩阵提权、持仓成本Bug修复、手机端真OCR闭环与29基实战账本演练"`
   - `git tag -a v4.6-G16 -m "Release v4.6-G16"`
   - `git push origin HEAD`
   - `git push origin v4.6-G16`
   (NO GitHub Release!).

Write `changes.md` and `handoff.md` in your state folder.
Send message to orchestrator upon completion.


## 2026-11-11T04:46:22Z
You are worker_g16_m4_delivery. Your state folder is d:\Google\Workspace\Wind\.agents\teamwork\worker_g16_m4_delivery\.
Read your assignment in d:\Google\Workspace\Wind\.agents\teamwork\worker_g16_m4_delivery\DISPATCH.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations and verifications must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work.

PHYSICAL REDLINE INVARIANTS:
1. NEVER modify the 4 read-only referee files: judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py.
2. NEVER modify DataLoader.simulate_execution signature or default parameters or fee logic.
3. NEVER touch global GEMINI.md (c:\Users\deanc\.gemini\GEMINI.md). Update ONLY workspace root d:\Google\Workspace\Wind\GEMINI.md!
4. DO NOT create GitHub Release. Only git tag v4.6-G16 and push tag to origin.

Execute Tasks 1 through 4:
1. Run full regression test suites and confirm 100% green.
2. Cleanly restart Streamlit service on port 8501 and confirm HTTP 200 health.
3. Capture screenshots for the 4 core views (Screen 1: Top bar & 1-row-5-col horizontal memo; Screen 2: Tab 2 3-step prescription; Screen 3: Tab 3 29 vs 6 backtest dual curves; Screen 4: Mobile minimal view). Save them in data/screenshots/g16/.
4. Update workspace GEMINI.md and PROGRESS_LOG.md. Execute git commit, tag v4.6-G16, and git push.

Write changes.md and handoff.md in your state folder.
Send message to orchestrator upon completion.
