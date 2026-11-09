# BRIEFING — 2026-11-09T08:26:00Z

## Mission
Milestone 2: UI/UX 全面重构、砍除伪交易按钮、全宽大胶囊导航与图例上浮，实施在 AGY2_FundAdvisory/app_gui.py。

## 🔒 My Identity
- Archetype: teamwork_worker
- Roles: implementer, qa, specialist
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\worker_g13_m2
- Original parent: ff97c74e-8951-4fdf-b683-3caf0969e6bd
- Milestone: Milestone 2: UI/UX 全面重构、砍除伪交易按钮、全宽大胶囊导航与图例上浮

## 🔒 Key Constraints
- NEVER touch or modify the 4 strictly read-only files:
  `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py` (and `AGY2_FundAdvisory/tests/test_infra.py`).
- `DataLoader.simulate_execution` default signature and default fee deduction logic MUST remain 100% intact.
- Scope & write ownership: File owned exclusively: `AGY2_FundAdvisory/app_gui.py`.
- DO NOT CHEAT. All implementations must be genuine.
- Use Chinese for all user/parent communication.

## Current Parent
- Conversation ID: ff97c74e-8951-4fdf-b683-3caf0969e6bd
- Updated: 2026-11-09T08:26:00Z

## Task Summary
- **What to build**:
  1. 首屏零阻塞秒开：在 `render_dual_wing_advisory_dashboard` 禁止首次加载计算耗时雷达/套利函数，纯内存渲染参谋条；
  2. 彻底删除首屏右上角红色大按钮与右侧空白死区，使 expander 100% 全宽；
  3. 彻底清理双翼看板内部伪操作跳转按钮与臃肿嵌套（删除一键锁定、择机置换、入备选池等按钮，移除嵌套对照尺，将4个大市场扫描工具移至 Tab 4 二级子 Tab）；
  4. 全宽四宫格大胶囊主导航栏 CSS 改造（并与 Tab 4 二级 subtabs 隔离）；
  5. 消除四大主 Tab 内部开头重复打印的巨型标题与 Tab 4 顶栏合并；
  6. Tab 3 回测图 Plotly 图例上浮透明与零遮挡，新增后视镜幸存者效应警示卡与动态策略对照开关。
- **Success criteria**: 界面秒开、无伪操作、UI排版现代清爽、测试全部通过、无语法及运行报错。
- **Interface contracts**: PROJECT.md, ORIGINAL_REQUEST.md, Explorer 1 & 2 handoff reports.
- **Code layout**: `AGY2_FundAdvisory/app_gui.py`.

## Key Decisions Made
- 投顾提示条采用纯内存判断（`pm.holdings` 与 `snapshot`），首屏渲染耗时 < 5ms。
- 彻底消灭 `col_wing_btn` 与 `btn_master_action_switch`，将 `st.expander` 提升为 100% 全宽容器，消除右侧 18% 垂直死区。
- 清除双翼看板内所有伪操作按钮（`btn_batch_lock_all_7d`, `btn_add_radar_pool_`, `btn_sentry_act_`, `btn_sentry_evid_`），右翼收敛为干净纯粹的纯文本建议卡片。
- 注入深度 CSS 选择器实现 100% 全宽四宫格大胶囊导航（46px, 16px bold, 激活深海蓝+纯白文字），并以 `:not([data-testid="stTabContent"] ...)` 与二级子 Tab 严格物理隔离。
- Tab 4 顶栏选择器与成分档案合并为单行紧凑摘要卡（3.8 / 6.2 分列），下方构建 6 大二级子 Tab，完好承接原首屏 4 大深度分析工具（带完整向下 expander 头部）。
- Tab 3 Plotly 图表边距扩大至 `margin(t=75)`，图例置于图表外部上方透明背景（`y=1.06, bgcolor="rgba(0,0,0,0)"`），牛熊文字缩小淡化（`size=9, muted color`），并挂载当前持仓静态回测后视镜警示卡与样本外动态策略对照开关。

## Artifact Index
- `d:\Google\Workspace\Wind\.agents\teamwork\worker_g13_m2\DISPATCH.md` — Dispatch instructions
- `d:\Google\Workspace\Wind\.agents\teamwork\worker_g13_m2\progress.md` — Progress tracker
- `d:\Google\Workspace\Wind\.agents\teamwork\worker_g13_m2\handoff.md` — Final handoff report
- `d:\Google\Workspace\Wind\scripts\verify_m2_deliverables.py` — Delivery verification script

## Change Tracker
- **Files modified**: `AGY2_FundAdvisory/app_gui.py` (Exclusive ownership: Milestone 2 UI/UX complete redesign)
- **Build status**: pass (`py -3 -m py_compile AGY2_FundAdvisory/app_gui.py`)
- **Pending issues**: none

## Quality Status
- **Build/test result**: All core and regression suites passed (`tests/test_infra.py` 14/14, `tests/test_adv_final_closure.py` 14/14, `tests/test_streamlit_apptest_run.py` 1/1, `tests/test_ui_pro_redesign_verification.py` 3/3, `tests/test_g8_ux_and_realtime_fusion.py` 7/7). 4 read-only judge files have 0 modifications.
- **Lint status**: clean
- **Tests added/modified**: `scripts/verify_m2_deliverables.py` verified 100%

## Loaded Skills
- None
