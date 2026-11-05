## 2026-11-03T14:53:19Z
You are Worker M1 (Agent-1: Sidebar & Guardrails Architect) for the Wind Fund Advisory system.
Working directory: d:\Google\Workspace\Wind\.agents\teamwork\worker_m1\

Read ORIGINAL_REQUEST.md first:
d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md

Read PROJECT.md:
d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md

Read the three Explorer M1 reports:
1. d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_1\report.md (R1 Redline & CSS)
2. d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_2\report.md (R2 Target Sync & Snapshot)
3. d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_3\report.md (R2 Execution Guardrails)

MANDATORY INTEGRITY WARNING:
> DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Scope & Write Boundaries:
- Primary Owned Files:
  - `AGY2_FundAdvisory/app_gui.py`
  - `AGY2_FundAdvisory/portfolio_manager.py`
  - `AGY2_FundAdvisory/strategy_bridge.py` (if updating buffer parameter handling)
- Strictly Read-Only Files:
  - `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py` (Do NOT touch or modify)

Detailed Implementation Tasks (Milestone 1):
1. R1 攻防红线数据源对齐：
   - In `app_gui.py`, extract `surge_line` and `breakdown_line` unified from `snapshot.get("trigger_lines")` before sidebar rendering.
   - Replace the hardcoded `_c300*1.012` and `_c300*0.985` in the sidebar with the unified lines.
   - Ensure main dashboard Card 2 and the sidebar read from the exact same values.
2. R1 核心指数实时行情条视觉提权：
   - In `app_gui.py` CSS, upgrade `.index-pill-point` to 15px~16px bold tabular/monospace font (`font-feature-settings: 'tnum'`), `.index-pill-name` and badges to 13px, increase pill padding (`4px 10px`), set `gap: 8px` (GEMINI.md Rule 14), and retain `flex: 0 0 auto !important;`, `white-space: nowrap !important;`, and `.index-pills-scroll-wrap` horizontal scrolling.
3. R2 侧边栏全局目标与档位联动器：
   - Elevate initialization of `active_tier_val`, `target_return_val`, `purchase_limit_filter`, and `rebalance_buffer_pct` to before `with st.sidebar:`.
   - Implement C1~C5 risk tier selector and annual return slider in sidebar with bidirectional sync and cache invalidation (`tab2_diag_cache`, etc.).
4. R2 实盘交易风控护栏：
   - Single-day purchase limit filter:
     - Provide `["不限 (自动拆单承接)", "过滤日限额 < ¥1,000 标的", "过滤日限额 < ¥5,000 标的"]` in sidebar.
     - Implement `replace_restricted_funds_with_alternatives` in `portfolio_manager.py` (replacing restricted funds like 050025 with 001071) and call it when filtering is active in Tab 1 blueprint & N-funds model generation.
   - Rebalance buffer slider:
     - Provide `1.0% ~ 5.0%` (default `3.0%`) slider in sidebar.
     - Pass `min_buffer_pct = st.session_state.rebalance_buffer_pct / 100.0` into Tab 2 rebalance calls.
5. R2 账本环境与快照管理迁移：
   - Place `🚀 加载演示组合` (ensure it is `at.sidebar.button[0]` for existing test compatibility), `↩️ 一键撤销快照`, and `🔄 全局同步行情与估值` into the sidebar.
   - Display market status and local lakehouse base date (`2026-11-03`).

Verification Requirement:
- Run the baseline test suite:
  `py -3 -m pytest AGY2_FundAdvisory/tests/test_deep_remodel_final.py -v`
- Verify all tests pass.
- Document exact changes, commands, and results in your `handoff.md`.
- Send a completion message back with summary when done.


## 2026-11-03T15:05:57Z
**Context**: Milestone 1 Implementation (R1 & R2)
**Content**: 正在进行周期性心跳巡检。请同步当前实施进展、正在修改的文件以及测试验证情况。若遇到任何困难或阻碍请及时反馈。
**Action**: 请简要汇报当前进度。
