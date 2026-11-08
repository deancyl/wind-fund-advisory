# Task Assignment: Worker 1 (Milestone 1 - Top Area & Tab 1 Refactoring)

## Target File Ownership
- Exclusively owns: `AGY2_FundAdvisory/app_gui.py` (CSS, Top Area, Dual-Wing expander, Tab 1)

## Input Information
- Authoritative User Request: `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`
- Project Milestone Plan: `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_15\PROJECT.md`
- Detailed Technical Blueprint: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g11_survey_1\handoff.md`

## Objectives
Implement Milestone 1 per R1 & R2:
1. Top Area:
   - 4 compact global metric cards: lock CSS `.main-metric-card` height to 82px (`min-height: 82px; max-height: 82px; height: 82px !important; overflow: hidden;`), strip noisy emojis and long subtitles.
   - Remove standalone "今日投顾行动总开关" banner and "跨区联动指令已生效承接" banner.
   - Merge today's one-line conclusion into the dynamic title of the wing dashboard expander:
     `今日投顾结论：{act_title} ｜ 点击展开机会雷达与主动风控巡检`
   - Place a compact jump button right beside the expander (or in expander header row).
   - Retain comment hook `# 跨区联动指令已生效承接横幅` to satisfy test contract.
2. Tab 1 Noise Elimination:
   - Completely delete `render_workflow_step_indicator` call, caption, gray AI smart advisory box, and duplicate `btn_t1_run_all` button (keep only single primary button `btn_run_simulation_now`).
   - Remove Step 1, Step 2, Step 3 headers and step gate constraints so executing generation shows execution table immediately.
3. Tab 1 Module 1 (Single-Line Control Bar):
   - Single compact line with columns: Total Capital input, Risk tolerance selectbox/segmented (C1-C5), Rhythm (一次性/三步分批/智能定投), Advanced Model & Tuning Popover, and single primary button "生成实盘建仓方案" (`key="btn_run_simulation_now"`).
   - In Advanced Tuning Popover: model selectbox uses standard short names `["鲁棒双核HRP", "稳健风险平价", "均值方差切线", "Black-Litterman", "自适应动量", "MinVol最小方差", "等权重基准"]` (key `tab1_sel_model_type`), max fund count, limit check, questionnaire.
4. Tab 1 Module 2 (Core Execution Table & 3-Column Metric Bar):
   - Directly above the dataframe, render 3 compact high-contrast metric bars:
     1) 1年达标胜率与年化票息安全垫
     2) 历史极限回撤与最长回本天数
     3) 攻防仓位配比与定权模型
   - Directly underneath, render the execution table `st.dataframe(df_display)` without intervening PCR banners or summary_advice blue boxes.
5. Tab 1 Module 3 (Action Bar & Single White-Box Drawer):
   - Single row of 4 Popovers/buttons: Overwrite current ledger (with confirmation Popover), Save as new ledger (Popover), Order cheat sheet (Popover), Send to backtest.
   - At the bottom, keep ONLY single expander "展开机构级量化压力测试与选基白盒证据" (containing rolling win rate, black swan / MC stress, fund funnel, batch schedule).
6. Global CSS:
   - Cut emojis by >70%, `block-container` `padding-top: 1.2rem`, card `margin-bottom: 6px`.

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Verification
Run affected tests (e.g. `pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py -k "tab1 or metric or step"`) to ensure syntax is clean and key test contracts remain intact.
Report all changes, diffs, and verification commands in `d:\Google\Workspace\Wind\.agents\teamwork\worker_g11_m1\handoff.md`.
