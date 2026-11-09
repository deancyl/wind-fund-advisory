# DISPATCH — worker_m4
## Mission
Milestone 4: Full Test Suite Verification, Service Restart & Health Check, Git Tag, and G15 Delivery.

## Instructions
1. Read `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md` (lines 202-231).
2. Execute full regression testing across all G15 test suites:
   `py -3 -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_delta_m1_guardrails.py tests/test_g15_phase2_memo_and_timemachine.py tests/test_g15_phase3_ocr_and_combat29.py tests/test_adversarial_m3_challenger1_ocr_slicing_and_tail.py tests/test_adversarial_m3_combat29_challenger.py -v`
   Verify 100% pass rate.
3. Service Restart:
   - Terminate stale 8501 process safely:
     `powershell -Command "Stop-Process -Id (Get-NetTCPConnection -LocalPort 8501 -ErrorAction SilentlyContinue).OwningProcess -Force -ErrorAction SilentlyContinue"`
   - Launch Streamlit in headless mode:
     `python -m streamlit run AGY2_FundAdvisory/app_gui.py --server.port 8501 --server.headless true`
   - Probe `http://127.0.0.1:8501/_stcore/health` and verify HTTP 200 OK.
4. Update `GEMINI.md` and `PROGRESS_LOG.md` with G15 accomplishments and invariants.
5. Git operations:
   - `git status --porcelain`
   - `git add .`
   - `git commit -m "feat(G15): complete G15 generation full-stack upgrade"`
   - `git tag -a v4.5-G15 -m "Release v4.5-G15"`
   - `git push origin main --tags`
   - ⚠️ STRICT RULE: DO NOT create GitHub Release!
6. Write your structured handoff to `handoff.md` and send message to parent (ID: `9a123e21-7525-4c57-9715-710c2a94c199`).

## 2026-11-09T19:34:48Z
You are worker_m4. Your working directory is d:\Google\Workspace\Wind\.agents\teamwork\worker_m4.
Read d:\Google\Workspace\Wind\.agents\teamwork\worker_m4\DISPATCH.md and d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md.
Execute full regression tests, restart Streamlit on port 8501 and check health, update GEMINI.md/PROGRESS_LOG.md, execute git commit, git tag v4.5-G15 and git push origin main --tags (DO NOT create GitHub release).
Write your handoff to handoff.md and send message to parent (ID: 9a123e21-7525-4c57-9715-710c2a94c199).
