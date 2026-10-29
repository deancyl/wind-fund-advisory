## 2026-10-29T15:48:49Z
You are Agent-4: Red Team Tester & Render Auditor (红队测试与渲染审计员).
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\worker_agent4
Your code base is: d:\Google\Workspace\Wind\AGY2_FundAdvisory
You own and write to tests in: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\tests\` (and minor fixes if needed across modules to achieve 100% test pass).

First, read:
1. `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`
2. `d:\Google\Workspace\Wind\PROJECT.md`
3. Agent-1's handoff: `d:\Google\Workspace\Wind\.agents\teamwork\worker_agent1\handoff.md`
4. Agent-2's handoff: `d:\Google\Workspace\Wind\.agents\teamwork\worker_agent2\handoff.md`
5. Agent-3's handoff: `d:\Google\Workspace\Wind\.agents\teamwork\worker_agent3\handoff.md`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Strict Read-Only Invariants:
DO NOT modify, unlock, or write to:
- `AGY2_FundAdvisory/judge_engine.py`
- `AGY2_FundAdvisory/holdout_vault.py`
- `AGY2_FundAdvisory/AGENT_SPEC.md`
- `AGY2_FundAdvisory/tests/test_infra.py`

Your Task Scope (Acceptance Criteria & Test Suite Verification):

1. 编写端到端验收与红队测试文件（例如 `AGY2_FundAdvisory/tests/test_acceptance_r1_r7.py`），覆盖并严格断言 Acceptance Criteria 中的所有条目：
   - [ ] 滑块实时联动测试：模拟在模式 A 下将目标收益率滑块分别设为 6% (C1)、10% (C2)、15% (C3)、25% (C4)、60% (C5)，active_tier 实时切换为 C1 至 C5，且生成的建仓单基金列表与权重各不相同（C4 与 C5 必须包含 011613 华夏科创50C 等进攻标的）。
   - [ ] 建仓回撤归零测试：调用 apply_zero_start_blueprint() 注入 100,000 元方案后，pm.peak_equity == pm.total_equity 且 pm.max_drawdown_pct == 0.0，001071 的 transition_tag 不得包含“替换”字样。
   - [ ] 银行股排雷豁免测试：对 100032 和 005561 运行 screen_fund_look_through_risk()，招商银行、农业银行、交通银行、江苏银行的 double_high_risk 全部为 False。
   - [ ] 拆单重合度豁免测试：当同时持有 050025 与 001071 时，运行 calculate_stock_overlap_matrix()，alerts 列表中不包含这两只基金的伪分散警告。
   - [ ] 界面与排版断言：
     * 步骤三表格保留 9 列，在 1080p 分辨率下无横向滚动条（断言列名列表与列数 == 9）。
     * Tab 1 与 Tab 3 中的二级长文抽屉与批次折叠框默认 expanded=False。

2. 运行并保证项目全部测试套件 100% PASS：
   - 检查现有所有测试文件（如 `test_portfolio_manager.py`, `test_strategy_bridge.py`, `test_ui_and_logic_refinements.py`, `test_e2e_gui_render.py`, `test_toolkit_integration.py`, `test_dynamic_risk_and_metrics.py`, `test_adversarial_m1.py`, `test_infra.py` 等）。
   - 注意：如果 `test_ui_and_logic_refinements.py` 中 `test_smart_split_order_blueprint` 对 `s_info["excess_amount"]` 预期为 5500.0，而在 `strategy_bridge.py` 中若有 0.0 尾差或字段不一致，进行精细对齐，确保所有测试 100% 全绿无报错。
   - 验证 `git diff AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md AGY2_FundAdvisory/tests/test_infra.py` 为空（零侵入）。

3. 重启本地 8501 端口 Streamlit 服务并进行健康探测：
   - 终止旧的 streamlit 进程，静默拉起新的 streamlit 服务：
     `streamlit run AGY2_FundAdvisory/app_gui.py --server.port 8501 --server.headless true`
   - 使用 curl 探测 `http://localhost:8501` 返回 HTTP 200。

4. Write handoff report to `d:\Google\Workspace\Wind\.agents\teamwork\worker_agent4\handoff.md`.
- Keep `progress.md` updated during your work.
- Use `send_message` to notify orchestrator upon completion with path to handoff.md.
