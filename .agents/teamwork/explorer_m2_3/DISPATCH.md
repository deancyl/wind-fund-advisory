# Explorer M2-3 Dispatch
Assigned task: Investigate Feature 11 (OCR dual-channel union, vocabulary expansion in portfolio_manager.py) and map all 88 test cases in tests/test_g19_m2_routing_and_rolling_dca.py.


## 2026-11-15T08:49:44Z
You are Explorer 3 for Milestone 2.
Your working directory: d:\Google\Workspace\Wind
Your state folder: d:\Google\Workspace\Wind\.agents\teamwork\explorer_m2_3
Read the authoritative user request: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Read the project plan: d:\Google\Workspace\Wind\PROJECT.md
Read the scope document: d:\Google\Workspace\Wind\.agents\teamwork\sub_orch_m2\SCOPE.md
Read previous survey findings: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_2\handoff.md
Read E2E test file: d:\Google\Workspace\Wind\tests\test_g19_m2_routing_and_rolling_dca.py

Your specific mission is to deeply investigate Feature 11 and conduct a complete architectural mapping of the 88 test cases in test_g19_m2_routing_and_rolling_dca.py:
1. Feature 11: OCR 识别双通道并集与词表扩充 (portfolio_manager.py)
   - Inspect screenshot OCR parsing functions in `portfolio_manager.py` (e.g. `parse_portfolio_image` or related OCR extraction routines).
   - Find where the code does: `if len(clean_res) >= 1: return ...` which causes premature return and discards spatial block clustering results.
   - Design the dual-channel union fusion logic: how both regular text extraction and spatial block clustering results should be combined into a deduplicated union set.
   - Find regexes or keyword blacklists/cleaners for fund names. Expand the vocabulary to strip index code numbers and holding period numbers (e.g. "中证A500", "中证2000", "30天持有", "60天持有", "90天持有", "180天持有", etc.) so they are not erroneously parsed as fund holding amounts or shares.
   - Inspect tests in test_g19_m2_routing_and_rolling_dca.py for Feature 11.

2. Comprehensive E2E Test Suite Analysis (test_g19_m2_routing_and_rolling_dca.py):
   - Analyze all 88 test cases in `tests/test_g19_m2_routing_and_rolling_dca.py`.
   - Categorize all test classes and methods by Feature (Features 7, 8, 9, 10, 11, 12, 13, plus any integration or boundary tests).
   - For every feature, list what functions/classes/attributes/keys are expected, mocked, or checked.
   - Identify potential pitfalls or brittle assumptions in the test suite so the Worker can avoid regressions.

Output:
Write a comprehensive, precise technical handoff report to `d:\Google\Workspace\Wind\.agents\teamwork\explorer_m2_3\handoff.md` with:
- Exact line numbers and code snippets in existing files
- Concrete proposed code modifications and diffs
- Complete inventory of the 88 test cases in test_g19_m2_routing_and_rolling_dca.py and their requirements
Send a message back when complete.
