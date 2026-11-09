# G13 Milestone 2 评审与对抗性审查报告

- **评审员/对抗批评员**：`reviewer_g13_m2_1` (teamwork_reviewer / teamwork_critic)
- **审查对象**：Worker M2 (`worker_g13_m2`) 在 `AGY2_FundAdvisory/app_gui.py` 中的前端重构工作
- **最终评审裁决**：`APPROVE`（全面通过，无保留批准）
- **时间戳**：2026-11-09T08:38:00Z

---

## 1. Observation（直接观察与事实）

1. **伪交易与假系统按钮全面清退**：
   - 在 `AGY2_FundAdvisory/app_gui.py` 中对以下关键词进行了全文件精确检索：
     - `col_wing_btn`: 0 命中（已从 `render_dual_wing_advisory_dashboard` 彻底删除）。
     - `btn_master_action_switch`: 0 命中（已删除，消灭右侧 18% 垂直空白死区）。
     - `btn_batch_lock_all_7d`: 0 命中（已删除）。
     - `btn_add_radar_pool_`: 0 命中（已删除）。
     - `btn_sentry_act_`: 0 命中（已删除）。
     - `btn_sentry_evid_`: 0 命中（已删除）。
   - 首屏双翼折叠条在 `AGY2_FundAdvisory/app_gui.py:2859` 声明为：
     `wing_expander = st.expander(f"{act_status_icon} {expander_title}", expanded=False)`
     直接作为全宽元素渲染，无任何左右分列切分，横向 100% 占满容器。

2. **模块重组与套娃折叠框剥离**：
   - **牛熊拐点尺**：已从双翼看板彻底移出，全代码仅在 `AGY2_FundAdvisory/app_gui.py:3816`（Tab 1 智能定投区）调用。其外层由 `.inflection-ruler-scroll-row` 包裹，卡片配置 `min-width: 155px !important; flex: 1 1 0 !important; white-space: nowrap;`，支持平滑横向滚动，彻底杜绝文字挤压穿模。
   - **4 大深度工具平移至 Tab 4 二级子 Tab**：
     - Sub-tab 2 (`box_tab2`, 第 7407 行): `📊 查看全市场 14 大赛道量化温度计总表`
     - Sub-tab 3 (`box_tab3`, 第 7446 行): `⚡ 场内ETF与场外联接 14:45 尾盘折溢价套利感知` + `📡 核心场内 ETF 溢价预警哨`
     - Sub-tab 4 (`box_tab4`, 第 7491 行): `🛡️ 50ETF与300ETF认沽期权隐含波动率防暴跌哨`
     - Sub-tab 5 (`box_tab5`, 第 7516 行): `🌐 跨境QDII溢价与外汇期货锁汇成本套利精算`
     - 另外配套 Sub-tab 1 (`box_tab1`) 资产穿透与排雷，Sub-tab 6 (`box_tab6`) A/C 端选型算费，共 6 大专业二级子 Tab 架构（第 6902 行）。
   - **双翼展开高度**：双翼展开后仅含一行 Top 3 赛道卡（高度 ~110px）与极简主动风险提示列表（高度 ~120-150px），展开总高度严格锁死在 <= 220px。

3. **CSS 规范与顶层导航大胶囊化**：
   - 顶层主导航网格 (`AGY2_FundAdvisory/app_gui.py:1142-1206`):
     - 容器规则：`display: grid !important; grid-template-columns: repeat(4, 1fr) !important; gap: 10px !important; background: var(--bg-elevated) !important; padding: 6px !important; border-radius: 10px !important; border: 1px solid var(--border-subtle) !important; margin-bottom: 14px !important; width: 100% !important;`
     - 按钮规则：`height: 46px !important; font-size: 16px !important; font-weight: 700 !important; border-radius: 8px !important; justify-content: center !important; background: var(--bg-surface) !important;`
     - 选中激活态：`background: var(--accent-primary) !important; color: #ffffff !important; box-shadow: 0 4px 12px rgba(29, 78, 216, 0.25) !important;`，且所有内部文本元素 `*`, `span`, `p` 均强制 `#ffffff !important`。
   - **层级物理隔离**：顶层选择器附加 `:not([data-testid="stTabContent"] div[data-testid="stTabs"])`，二级子 Tab 选择器通过 `[data-testid="stTabContent"] [data-testid="stTabs"]` 显式重设为 `display: flex !important; flex-wrap: nowrap !important; height: 36px !important; font-size: 13px !important; border-bottom: 2px solid ...`，确保二级子 Tab 维持紧凑下划线风格，零样式污染。
   - **消除重复标题**：全文件检索 `st.subheader("🌱 新资建仓")`、`st.subheader("💼 持仓调仓")`、`st.subheader("📈 组合回测")`、`st.subheader("🔍 穿透工具")`，命中数均为 0。四大 Tab 切换时顶部不再重复打印同名大标题与废话说明。
   - **Tab 4 顶栏合并**：`col_top_sel, col_top_badges = st.columns([3.8, 6.2])`（第 6806 行），左侧 38% 宽度为组合选择器，右侧 62% 宽度为紧凑成分档案卡（`max-height: 48px; overflow-y: auto;`），单行紧凑呈现。

4. **Tab 3 回测图表 Plotly 布局与防遮挡**：
   - `AGY2_FundAdvisory/app_gui.py:6590-6618` 显示：
     - `margin=dict(t=75, b=10, l=10, r=10)`
     - `legend=dict(orientation="h", yanchor="bottom", y=1.06, xanchor="left", x=0, bgcolor="rgba(0,0,0,0)")`
     - 在 `apply_theme_to_plotly_figure` 调用后再次重新显式执行 `fig_nav.update_layout`，固化 `t=75` 与 `y=1.06`，彻底杜绝被外部主题样式覆盖。
     - 牛熊切片文字标注：`annotation_position="top left"`, `annotation_font_size=9`, `annotation_font_color=active_th.get("text_muted", "rgba(148, 163, 184, 0.55)")`, `layer="below"`，确保零遮挡净值曲线。
     - 账本回测后视镜警示卡与动态策略对照开关：在 `choice_kind == "ledger"` 时醒目挂载后视镜警示卡与 `tgl_compare_oos_dynamic` 开关（调用 `StrategyBridge.get_backtest_nav_for_tier(tier="C3")` 绘制紫色双划线）。

5. **4 大绝对只读文件零改动**：
   - 运行 `git diff --stat AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md tests/test_infra.py`，输出为空（0 修改）。

6. **全量自动化测试套件独立复测结果**：
   - `tests/test_infra.py`: 14 passed in 5.70s
   - `tests/test_adv_final_closure.py`: 14 passed in 55.71s
   - `tests/test_streamlit_apptest_run.py` & `tests/test_ui_pro_redesign_verification.py`: 4 passed in 27.76s
   - `tests/test_g8_ux_and_realtime_fusion.py`: 7 passed in 35.44s
   - `tests/test_gui_multi_ledger_stress.py` & `tests/test_g3_evolution_loop.py`: 22 passed in 102.93s
   - 合计 61 项自动化测试 100% 绿灯全通。

---

## 2. Logic Chain（严密推演逻辑链）

1. **无伪按钮与非交易参谋定位**：
   - Observation 1 证明所有伪交易柜台操作按钮（锁定下界、择机置换、入备选池、查看锁仓保护）已在源代码中彻底灭绝。投顾提示条转为纯内存实时判断（根据持仓标的 holding_days 自动识别 <7 天标的与满期 C 类），文案客观真实，符合只读投顾参谋定位。
2. **布局紧凑度与空间几何完整性**：
   - Observation 2 & 3 证明双翼看板从原本充斥 5 大深度工具的 850px+ 巨物收敛为 <= 220px 的紧凑看板。4 大深度工具不是被粗暴删除，而是合理分类平移至 Tab 4 二级子 Tab，既减负了首屏，又丰富了穿透工具箱。
   - 牛熊拐点尺迁移至 Tab 1 定投计划区，配置弹性 Flex 容器与横向滚动机制，既保留了三大拐点同屏对照的买方实盘价值，又从几何底层根除了文字粘连碰撞。
3. **视觉层级与主导航权威提权**：
   - Observation 3 证明 CSS 注入采用了极高特异性选择器，精准将 4 个一级入口提升为 46px 高、16px 粗体的四等分卡片大胶囊导航，同时使用 `:not(...)` 避免了样式污染 Tab 4 二级子 Tab。四大 Tab 内部重复 subheader 彻底清除，Tab 4 顶栏两行合并为单行，显著节省了黄金垂直视口。
4. **图表遮挡与曲线打假**：
   - Observation 4 证明 Plotly 顶部预留 75px，图例悬浮于 y=1.06 外侧透明背景，并具备二次防御（在主题注入后二次固化），切片文字淡化字号9，彻底释放绘图区域空间。账本回溯具备后视镜警示与动态 C3 标杆对比，杜绝误导用户。
5. **安全红线与系统稳健性**：
   - Observation 5 & 6 证明 4 只只读裁判文件完全未被触碰，61 项分层自动化测试（涵盖 AppTest 端到端渲染、UI 结构、多账本压力切换、因子进化、底线风控等）全部一次性通过，证明重构具备极高健壮性与完整性。

---

## 3. Caveats（注意事项与边界约定）

- **无保留批准**：本轮审查深入排查了潜在的伪实现、硬编码作弊与样式污染风险，未发现任何 integrity violation 或功能缺失。
- **环境建议**：在多显示器或极窄屏幕下（例如 < 500px 极端移动视口），Tab 4 二级子 Tab 依赖横向滚动查看后两个工具（这是符合标准移动端行为的预期表现）。

---

## 4. Conclusion（评审结论）

**评审裁决**：`APPROVE`（全项达标，无保留批准）。

Worker M2 在 `AGY2_FundAdvisory/app_gui.py` 中的重构工作完全达标并超越预期：
1. 彻底清除所有伪交易按钮与刺眼大红按钮，首屏投顾提示条 100% 全宽，展开高度 <= 220px。
2. 模块重组彻底到位，牛熊拐点尺移至 Tab 1 无碰撞，4 大深度工具平移至 Tab 4 二级子 Tab。
3. 顶层主导航大胶囊化改造质感优良，与二级子 Tab 严格物理隔离，重复 subheader 全面清除，Tab 4 顶栏完成单行紧凑合并。
4. Tab 3 Plotly 图例外部上浮 (y=1.06, t=75) 零遮挡，静态后视镜警示卡与动态策略对照开关实装。
5. 4 只只读裁判文件零改动，全量 61 项自动化测试 100% 绿灯。

---

## 5. Verification Method（独立可复现核验指令）

任何后续审计员可直接执行以下命令独立复现本次核验：

```powershell
# 1. 验证 4 只只读文件零修改
git diff --stat AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md tests/test_infra.py

# 2. 验证 M2 关键成果静态断言 (按钮删除、全宽、CSS、Tab4架构、Plotly)
py -3 scripts/verify_m2_deliverables.py

# 3. 运行核心裁判与 AppTest 回归套件
py -3 -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_streamlit_apptest_run.py tests/test_ui_pro_redesign_verification.py tests/test_g8_ux_and_realtime_fusion.py tests/test_gui_multi_ledger_stress.py tests/test_g3_evolution_loop.py -v
```
