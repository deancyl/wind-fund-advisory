## 2026-11-08T07:03:48Z
You are challenger_g9_m2_13_1, a code-executing adversarial verifier.
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\challenger_g9_m2_13_1\

MANDATORY INSTRUCTION:
Read the authoritative user request at:
d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
and the scope document at:
d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_13\SCOPE.md
and the worker handoff report at:
d:\Google\Workspace\Wind\.agents\teamwork\worker_g9_m2_13\handoff.md

Your task is to adversarially challenge and stress-test the Milestone 2 (M2) GUI changes in `AGY2_FundAdvisory/app_gui.py`:
1. Execute adversarial testing on HTML purification:
   Write/run a python script that parses AST / regex of `app_gui.py` to verify that there are ZERO raw calls to `st.markdown(..., unsafe_allow_html=True)` that lack `_clean_html` or `safe_markdown_html`. Test edge cases like multiline f-strings, quotes, indents.
2. Adversarially test AppTest or mock execution of:
   - "今日投顾行动总开关": test all 4 states (lock alert, risk alert, empty portfolio, healthy/idle).
   - Tab 1 L1 inputs: extreme capital values (0, negative, 1e8, float), C1 to C5 tiers.
   - Tab 2 view mode switching: test is_t2_main_mode True vs False, verify dock tabs are NOT rendered in main mode.
   - Popover quick fund entry: test invalid fund codes, zero shares, negative amounts, 7-day lock triggering.
3. Run test suites:
   `pytest tests/test_challenger_g9_m2_adversarial.py`
   `pytest tests/test_sidebar_remodel_and_bugfixes.py`
4. Document all stress findings and test results in `d:\Google\Workspace\Wind\.agents\teamwork\challenger_g9_m2_13_1\handoff.md` with verdict: APPROVE or REQUEST_CHANGES.
5. Send a message to orchestrator with your verdict.
