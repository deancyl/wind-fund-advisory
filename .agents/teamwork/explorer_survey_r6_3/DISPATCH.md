## 2026-11-03T14:18:16Z
[Message] timestamp=2026-11-03T14:18:16Z sender=4b9235fc-5501-4c70-bc98-8ac4f7ce5f18 priority=MESSAGE_PRIORITY_HIGH content=You are Explorer 3 for the production-grade remodel of Wind Fund Advisory system.
Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r6_3\

Read ORIGINAL_REQUEST.md first:
d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md

Your mission is read-only exploration focused on R4, R5, test baselines, and safety verification:
1. 既有测试基线与套件分析：
   - Examine `AGY2_FundAdvisory/tests/test_deep_remodel_final.py` and other test files in `AGY2_FundAdvisory/tests/`.
   - Identify test execution commands (e.g. `pytest AGY2_FundAdvisory/tests/test_deep_remodel_final.py -v`).
   - Understand the AppTest patterns used for Streamlit testing in this codebase.
2. 增量测试（Delta Test）设计规范：
   - Detail the exact test cases needed to verify:
     a) 侧边栏风控参数：单日限购过滤选择器开启时，Tab 1 选基与建仓单自动替换为同赛道备选标的；
     b) 侧边栏调仓缓冲带滑块参数（`min_buffer_pct`）正确传递并影响 Tab 2 调仓裁决；
     c) Tab 2 持仓账本直接修改当前市值并保存，持仓份额按当前净值精确反算，修改份额同步更新市值；
     d) 4 个 Tab 交互零异常（AppTest 断言 `assert not at.exception` 等）。
3. 物理安全红线与只读裁判文件审计：
   - Inspect the 4 referee files:
     - `AGY2_FundAdvisory/judge_engine.py` (or root `judge_engine.py`)
     - `AGY2_FundAdvisory/holdout_vault.py` (or root `holdout_vault.py`)
     - `AGENT_SPEC.md`
     - `AGY2_FundAdvisory/tests/test_infra.py` (or root `tests/test_infra.py`)
   - Record their exact paths and initial SHA256 hashes to establish the baseline for forensic audit.
4. 服务平滑重启与健康检查方案：
   - Check how Streamlit service is currently run or managed on port 8501.
   - Review GEMINI.md Rule 12 (Transient Outbound Port Collision Defense) and user_global Rule 12.
   - Document safe restart commands and HTTP health check probe (`curl` / `urllib`).

Write your complete structured survey report to:
`d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r6_3\survey_report.md`
Also produce `handoff.md` in your directory.
Send a completion message back with the report summary and file path when finished.
Remember: DO NOT modify any source code files. You are strictly read-only.
