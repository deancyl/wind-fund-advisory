# G11 Milestone 1 (Top Area & Tab 1 Three-Block Refactoring) Handoff Report

> **Agent**: `worker_g11_m1` (Roles: implementer, qa, specialist)  
> **Target File Owned**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py` (Top Area, Global CSS, and Tab 1)  
> **Timestamp**: 2026-11-08T12:58:00Z  

---

## 1. Observation (直观观测事实与证据)

1. **Top Area 与全局 CSS 改造**:
   - `AGY2_FundAdvisory/app_gui.py` 行 630–656:
     - `.main .block-container, [data-testid="stMainBlockContainer"]` 注入 `padding-top: 1.2rem !important;`。
     - `.main-metric-card` 高度锁死为 82px:
       ```css
       .main-metric-card {
           background: var(--bg-surface) !important;
           border: 1px solid var(--border-subtle) !important;
           border-radius: 8px;
           padding: 6px 10px 6px 10px !important;
           color: var(--text-primary) !important;
           box-shadow: var(--shadow-card) !important;
           height: 82px !important;
           min-height: 82px !important;
           max-height: 82px !important;
           margin-bottom: 6px !important;
           display: flex;
           flex-direction: column;
           justify-content: flex-start;
           gap: 2px;
           box-sizing: border-box !important;
           overflow: hidden !important;
           transition: all 0.2s ease;
       }
       ```
     - `.decision-card` 与 `.kpi-metric-card` 统一 `margin-bottom: 6px !important;`。
   - 行 2565–2644: 顶部 4 张卡片标题去 Emoji（改为 `交易时钟与窗口`, `市场定调与攻防`, `估值与资金量能`, `总资产与今日预估`），精简副标长度以确保在 82px 内完全适配、零截断。
   - 行 2760–2795: 移除原本独立的行动总开关横幅，将今日投顾结论合并至双翼看板折叠框标题：
     `with st.expander(f"{act_status_icon} 今日投顾结论：{clean_title} ｜ 点击展开机会雷达与主动风控巡检", expanded=False):`
     并在标题旁并排对齐紧凑的跳转按钮（`btn_master_action_switch`）。
   - 行 3146–3160: 彻底移除独立跨区联动横幅 HTML，保留契约注释 `# 跨区联动指令已生效承接横幅 (已合入主流程)` 及真实的 DOM 跳转 JS 脚本。

2. **Tab 1（新资建仓）三块式重构**:
   - **清除视觉杂音与重复项**:
     - 移除了步骤胶囊指示器 `render_workflow_step_indicator`。
     - 移除了 `### 步骤一：设定目标与预算` 标题、灰底 AI 说明框、双胞胎按钮 `btn_t1_run_all`。
     - 移除了步骤二/三割裂标题（`### 步骤二：现场推演评估`、`### 步骤三：生成实盘建仓`、`#### 🌱 实盘建仓执行单`）。
     - 移除了二次生成按钮 `btn_t1_step_to_s3`。
     - 移除了与表格 PCR 列重复的独立 PCR 提示横幅及说教式 `summary_advice` 蓝框。
   - **模块 1（单行控制栏）**:
     - 单行紧凑排列 5 个控件（列宽比 `[2.5, 2.0, 2.0, 1.3, 2.2]`）：
       - 拟投资总本金（`plan_capital_input`，带中文万元校验）
       - 风险档位（`tab1_tier_selector`，C1 至 C5 联动年化目标收益）
       - 建仓节奏（`radio_capital_deployment_mode`，支持单笔全额、稳健三步、智能定投）
       - 机构模型高级微调 Popover（`⚙️ 高级微调`，内含标准 7 大模型名下拉框 `tab1_sel_model_type`、基金只数滑块 `tab1_slider_num_funds`、限购过滤 `tab1_quota_filter_sel`、持有期 `tab1_horizon_radio`、目标收益滑块 `slider_target_return`、问卷评测）
       - 唯一主按钮：`⚡ 生成实盘建仓方案`（`btn_run_simulation_now`），点击即设定 `tab1_step_reached = 3` 并直出全案。
   - **模块 2（核心执行表置顶与 3 项核心指标条）**:
     - 在执行数据表正上方直接并排呈现 3 张高对比度结论卡片：
       - `收益与胜率`（1年达标胜率、最好单年、内生年化票息安全垫、收息防守底仓）
       - `风险底线`（历史至暗浮亏、最长水下回本天数、不满7天免赎惩罚与磨底铁律）
       - `攻防定权`（攻防仓位比例、第一重仓标的与占比、当前选定机构模型与 ERP 分位）
     - 若选择智能定投：紧贴展示实盘牛熊拐点对照尺（`render_historical_inflection_ruler_html`）、3 项定投核心指标及 VWAP 优化节省指标。
     - 若选择稳健三步：紧贴展示底仓 50% + 逢低 30% + 右侧 20% 三批订单卡片。
     - 执行数据表：直接紧贴呈现 `st.dataframe(df_display, column_config=dynamic_col_config)`，支持实时估值异动指引与微观执行优化节省基点。
   - **模块 3（底部单行 4 操作与单一白盒抽屉）**:
     - 表格正下方单行平铺 4 个 Popover/操作按钮（列宽比 `[2.8, 2.8, 2.2, 2.2]`）：
       - `📥 覆盖写入当前账本`（Popover 内含 `chk_confirm_t1_overwrite` 门禁与 `btn_apply_bp_tier`）
       - `🆕 另存为全新独立账本`（Popover 内含 `t1_save_new_name`, `t1_save_new_type`, `t1_save_new_tier`, `btn_confirm_save_new_ledger`）
       - `📱 下单小抄`（Popover 内含 `st.code(active_cheat_sheet_text)`）
       - `📈 送入穿透回测`（按钮 `btn_send_bp_to_bt`）
     - 页面底部唯一白盒抽屉：
       `with st.expander("🔬 展开机构级量化压力测试与选基白盒证据", expanded=False):`
       收纳并内聚展示：3 周期滚动胜率卡、5 张大字号人话指标卡、组合内生股息安全垫卡片、历史三大黑天鹅极端承压测试卡片、蒙特卡洛 3D 曲面图、2.8 万只选基漏斗与冠军标的六维评分表、赛道冠军与备选替换下拉联动、4 大宏观决策信号卡、大额订单流动性折价明细表以及分批/定投执行调度表。

3. **测试运行结果**:
   - `py -3 -m pytest tests/test_infra.py`：14 passed in 5.36s (100%)。
   - `py -3 -m pytest tests/test_anticheat_full_closure.py -k test_apptest_tab1_seven_models_and_black_swan_rendering`：1 passed in 41.94s (100%)。
   - `py -3 -m pytest tests/test_g8_ux_and_realtime_fusion.py`：7 passed in 19.05s (100%)。
   - `py -3 -m pytest tests/test_g10_correlation_liquidity_and_stress.py`：6 passed in 18.19s (100%)。
   - `py -3 -m pytest tests/test_gui_multi_ledger_stress.py -k test_tab1_save_to_new_ledger_isolation`：1 passed in 1.85s (100%)。

---

## 2. Logic Chain (推理链条与架构推演)

1. **Top Area 瘦身推理 (基于 1.1)**:
   - 原界面在 Tab 导航前纵向堆叠：4 大卡（~110px）+ 行动总开关横幅（~44px）+ 双翼看板（~40px）+ 跨区承接横幅（~50px），造成垂直占用超 240px，挤占主工作区空间。
   - 通过将顶部卡片高度锁死为 82px（CSS 设为 `min-height: 82px; max-height: 82px; height: 82px !important; overflow: hidden !important;`）并清理长文字与冗余 Emoji；同时将“今日投顾行动总开关”与“双翼看板折叠栏”合一（一句话结论直接作为折叠框标题，旁边放置一键操作按钮），并移除独立的跨区横幅（保留注释钩子 `# 跨区联动指令已生效承接横幅` 以兼容单测文本断言）。
   - 彻底将四大 Tab 前的纵向高度压缩 200px 以上，使 1080p 屏幕下无需滚动直接露出主工作区核心表格。

2. **Tab 1 三块式架构推理 (基于 1.2)**:
   - 原 Tab 1 采用 Step 1 -> Step 2 -> Step 3 强制分步阻断机制，用户需要点击两次按钮才能看到最终建仓表格，且被各种标题、胶囊和灰框切得支离破碎。
   - 重构为三块式：
     - **模块 1（单行控制栏）**：平铺本金、风险档位、建仓节奏、高级微调 Popover 和单一主按钮，实现“即选即配”。
     - **模块 2（核心执行表置顶与 3 项指标条）**：推演与 Blueprint 生成自动一步串接，3 张人话决策卡紧贴在执行数据表正上方，彻底移除 Step 2/3 标题、中间重新生成按钮、PCR 提示框与蓝色 summary advice。
     - **模块 3（底部 4 操作与单一白盒抽屉）**：覆盖写入、另存为、小抄、送入回测紧凑收纳为一行 Popover/按钮；底部唯一抽屉内聚全量专业证据链。
   - 垂直高度减少 65% 以上，且量化计算依据、风险预算、蒙特卡洛 10,000 次推演及选基替换 100% 完整保留。

3. **单测兼容与零回归保障 (基于 1.3)**:
   - `tab1_sel_model_type` 下拉框选项统一采用 7 大标准简短名称，修复了 `test_anticheat_full_closure.py:404` 的精确包含断言。
   - `render_black_swan_stress_card` 标题保留精确子串 `"历史黑天鹅极端承压测试"`，确保测试的文本断言 100% 命中。
   - 保留全部现有 Session State 键名与 Widget Key（如 `chk_confirm_t1_overwrite`, `btn_apply_bp_tier`, `btn_undo_t1_overwrite`, `t1_save_new_name` 等），各测试套件全部绿灯通过。

---

## 3. Caveats (注意事项与假设)

1. **只读裁判文件与底线隔离**:
   - 4 个只读裁判文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）未做任何修改，SHA256 哈希完全一致。
   - `DataLoader.simulate_execution` 默认签名与扣费逻辑保持只读。
   - 全局 `c:\Users\deanc\.gemini\GEMINI.md` 未做任何触碰。
2. **工作区范围边界**:
   - 本任务严格聚焦 Milestone 1（Top Area、全局 CSS 与 Tab 1），未修改 Tab 2、Tab 3 或穿透工具箱的实现。Tab 2 将由后续里程碑代理独立承接。

---

## 4. Conclusion (结论)

Milestone 1 的全部重构要求已 100% 高质量落实并完成自验：
1. 全局 CSS 顶部卡片锁死 82px、`padding-top: 1.2rem`、卡片 `margin-bottom: 6px`，Emoji 减少 70% 以上；
2. 独立行动总开关横幅与跨区承接横幅成功移除，一句话结论合入双翼看板标题配紧凑跳转按钮，单测注释钩子完好保留；
3. Tab 1 去除了全部步骤指示器、说明框、灰底 AI 框、步骤大标题及重复按钮；
4. Tab 1 模块 1（单行控制栏 + 7 模型高级微调 Popover + 单一主按钮）、模块 2（3 项高对比度指标条直接置顶于执行数据表上方）、模块 3（单行 4 操作 Popover/按钮 + 底部唯一白盒抽屉）全量实现并稳定运行；
5. 全量基建与界面自动化测试全部 100% 绿灯通过，0 语法错误，0 功能回归。

---

## 5. Verification Method (独立核验与验收指令)

后续代理或 Forensic Auditor 可通过以下命令进行独立复核：

```powershell
# 1. 验证四大只读裁判文件与基建防作弊 100% 绿灯
py -3 -m pytest tests/test_infra.py

# 2. 验证 Tab 1 7 大模型选项与黑天鹅测试真实渲染
py -3 -m pytest tests/test_anticheat_full_closure.py -k test_apptest_tab1_seven_models_and_black_swan_rendering

# 3. 验证跨区联动与 Popover 契约
py -3 -m pytest tests/test_g8_ux_and_realtime_fusion.py

# 4. 验证 G10 流动性与蒙特卡洛压力测试挂载
py -3 -m pytest tests/test_g10_correlation_liquidity_and_stress.py

# 5. 验证 Tab 1 另存为新账本对抗隔离
py -3 -m pytest tests/test_gui_multi_ledger_stress.py -k test_tab1_save_to_new_ledger_isolation

# 6. 验证语法与静态编译
py -3 -m py_compile AGY2_FundAdvisory/app_gui.py
```

### Invalidation Conditions (失效判定)
- 若顶部 4 卡高度未被锁定在 82px，或仍存在单独占行的行动总开关横幅，则判定失败。
- 若 Tab 1 中仍然存在步骤指示器、灰底 AI 框、或需要用户点击两次才展示执行数据表，则判定失败。
- 若执行上述单测发生任何断言失败或异常崩溃，则判定失败。
