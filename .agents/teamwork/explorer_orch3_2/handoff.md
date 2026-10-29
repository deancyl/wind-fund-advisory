# Handoff Report — GUI & Workflow Survey (`app_gui.py`)

## 1. Observation (客观观察事实)

1. **`cat_map` 硬编码现状**：
   - 源码位置：`d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py` 第 1869 至 1874 行。
   - 原文定义：
     ```python
     cat_map = {
         "100032": "A股红利高股息", "005561": "A股红利低波", "011612": "科技成长进攻", "011613": "科技成长进攻",
         "016633": "中小盘成长", "016634": "中小盘成长", "161017": "中盘均衡", "001053": "中盘均衡",
         "110020": "核心蓝筹", "007339": "核心蓝筹", "000216": "黄金对冲", "000217": "黄金对冲",
         "002351": "纯债固收", "018757": "纯债固收", "050025": "美股海外对冲", "001071": "美股海外对冲"
     }
     ```
   - 引用调用点：第 1877 行 `cat = cat_map.get(c, "其他存量资产")`、第 1881 行、第 1888 行及第 1918 行。
   - 影响：赛道备选金牌标的（如 090010、012643、013841）、限购伴生标的及用户自定义导入的任意基金均被无条件判定为 `"其他存量资产"`，造成大类配置缺口图表失真。

2. **现场推演与白盒步骤面板现状**：
   - 源码位置：`app_gui.py` 第 637 至 693 行。
   - 现有现场推演使用 `st.status` 与 `st.progress`，但内部没有微小延迟，本地执行耗时仅约 0.12 秒，瞬态闪现，缺乏 1.2~1.8 秒的运算反馈体验。
   - 推演白盒结构分散：Step 1 选基漏斗在行 815-875（折叠框）；Step 2 4张决策信号卡片（趋势生命线、风格动量、大小盘结构、股债性价比）在行 997-1052，且**仅在场景二（存量调仓）展示，场景一（从 0 建仓）不可见**；Step 3 实境回测在行 699-810；Step 4 交易摩擦与回本卡片在行 1106-1145（仅在场景二展示）。

3. **顶部 7 张核心卡片现状**：
   - 源码位置：`app_gui.py` 第 288 至 378 行，使用 `st.columns(7)` 布局。
   - CSS 定义在第 68-100 行：`.main-metric-card` 容器高度固定 94px，`.metric-value-huge` 字体为 `19px` 且包含 `white-space: nowrap; overflow: hidden; text-overflow: ellipsis;`。
   - 现象：在 1080p 屏幕且展开侧边栏时，列宽仅约 175~185px，主数值（如 `🟢 震荡收息期`、`4,053.2 (+0.5%)`、`+¥12,345.67`）极易被浏览器渲染截断为省略号；卡片中充斥 ERP、DR007、期指贴水、期权 IV 等专业黑话，缺乏 ⓘ 悬停原理解析。

4. **步骤三《建仓/调仓执行单》与存量调仓单表格现状**：
   - 建仓执行单（行 952-956）：源码显式定义 `cols_9 = ["基金代码", "基金名称", "份额", "目标占比(%)", "精确买入金额(元)", "最新净值", "实时估值涨跌(%)", "排雷与拥挤度", "实操分红与限购指引"]`，被 `tests/test_acceptance_r1_r7.py` 第 320 行正则测试强行锁定；最后一列内容（行 920）长度达 35+ 字。
   - 存量调仓单（行 1167-1205）：共有 16 列数据，在 1080p 屏幕下存在严重的横向滚动条；未统一使用规范醒目图标（`➕ 建议加仓`、`➖ 建议减仓`、`🔒 未满7天锁仓保护`、`⏳ 临近30天免赎期缓卖`）。

5. **《三句话看懂本方案》卡片现状**：
   - 检索全工程源码，目前完全不存在该组件，属于本次架构升级必须全新增补的模块。

6. **测试用例与断言现状**：
   - `tests/test_acceptance_r1_r7.py`：断言源码必须显式定义 `cols_9` 且列名严格吻合；断言 4 个 expander 默认 `expanded=False`；AppTest 模式 A 滑块联动 C1/C4/C5 必须无异常。
   - `tests/test_e2e_gui_render.py`：断言 `hasattr(app_gui, "strategy_fn_for_tier")`；`test_bug6_streamlit_apptest_full_render` 覆盖 C1~C5 全档位 AppTest 渲染测试，命令验证耗时 63 秒，结果 100% PASSED。
   - `tests/test_ui_and_logic_refinements.py`：断言卡片标题必须使用 `#b91c1c`, `#15803d`, `#b45309`, `#0369a1`；禁止正文使用浅灰 `#cbd5e1`；步骤一必须使用 `with st.container(border=True):`，并保持 `gui_scenario_mode_v2`、`plan_capital_input`、`btn_run_simulation_now` 等关键组件 key。

---

## 2. Logic Chain (推演逻辑链条)

1. **大类分类器迁移逻辑**：
   - 基于 Observation 1，`cat_map` 仅覆盖 16 个写死代码，任何动态替换、拆单伴生及外部导入基金都会被 fallback 为 `"其他存量资产"`。
   - 推导出：必须将 `cat_map` 彻底从 `app_gui.py` 移除，平滑重定向为调用 `portfolio_manager.py` 的统一资产分类解析器 `pm.classify_fund_asset_class(fund_code)`，利用基金名称/跟踪指数/投资类型进行通用推导。

2. **步骤二工作流白盒整合逻辑**：
   - 基于 Observation 2，当前 4 个推演步骤分散在 Tab 1 的不同位置甚至错位出现在步骤三场景二内部，从 0 建仓用户无法看到宏观决策信号卡片，且推演计算无节奏反馈。
   - 推导出：步骤二应提炼重构为 4 个清晰独立、可自由展开/收起的面板（Step 1 漏斗海选+PK明细+替换；Step 2 4张宏观与衍生品决策信号卡片；Step 3 实境回测与五大人话指标；Step 4 交易摩擦与限购拆单路由）；推演按钮引入 `time.sleep(0.35)` 阶梯，将节奏严格锁定在 1.2~1.8 秒。

3. **顶部卡片零截断与 ⓘ 悬停逻辑**：
   - 基于 Observation 3，在 7 等分栅格下，19px 字体在 180px 宽度内必然发生省略号截断。
   - 推导出：必须将主数值字体微调至 15~16px，标题与副标题改为通俗易懂的简练表述（如 `🟢 震荡收息期`、`🔥 科技主升浪`、`📈 结构分化期`、`🛡️ 熊市防守期`），专业黑话收进 ⓘ 悬停解析中，彻底消除省略号。

4. **双表格 9 列与字数控制逻辑**：
   - 基于 Observation 4，建仓单虽为 9 列但最后一列字符过长（35+字）；存量调仓单更是多达 16 列导致严重横向滚动条。
   - 推导出：
     - 建仓单：严格保留源码中的 `cols_9` 变量以满足既有正则测试，最后一列内容压缩至 15 字以内核心指令，详细原理解析移至表头 ⓘ 悬停。
     - 存量调仓单：从 16 列合并精简至 9 列，使用规范图标标明调仓动作（`➕`、`➖`、`🔒`、`⏳`），彻底消除横向滚动条。

5. **《三句话看懂本方案》落地逻辑**：
   - 基于 Observation 5，该模块是全新需求，且在推演结论之后、具体执行单之前展示最符合认知动线。
   - 推导出：将其设计为三栏作战卡片（收益引擎拆解、跨资产对冲反脆弱机制、极端浮亏与两条铁律），放置在步骤二与步骤三之间。

6. **既有测试兼容与防破坏逻辑**：
   - 基于 Observation 6，既有测试包含多项 AST 源码正则断言与 AppTest 端到端渲染断言。
   - 推导出：Agent-3 重构时必须将既有 key、变量名 `cols_9`、色值以及 `expanded=False` 设为不可变基线，确保改动 100% 向后兼容。

---

## 3. Caveats (注意事项与边界说明)

1. **依赖关系**：`app_gui.py` 迁移 `cat_map` 依赖于 `portfolio_manager.py`（Agent-2）提供统一的 `classify_fund_asset_class(fund_code: str) -> str` 方法。在 Agent-2 就绪前，Agent-3 可先提供具备兜底推导能力的本地包装或与 Agent-2 协同对齐接口签名。
2. **测试执行耗时**：Streamlit AppTest 全档位渲染测试（`test_bug6_streamlit_apptest_full_render`）需逐一执行 C1 至 C5 完整链路，单次执行耗时约 60 秒，重构验证时需留出充足执行等待时间。
3. **AST 源码正则敏感性**：`test_acceptance_r1_r7.py` 对 `cols_9 = [...]` 和特定 expander 标题进行了正则扫描，重构时不能擅自重命名变量或变更关键断言标题。

---

## 4. Conclusion (勘测结论与行动建议)

1. **静态分类器彻底根除**：准确定位并明确迁移路径，彻底消除 16 只死代码 `cat_map`。
2. **四阶推演白盒架构重塑**：确立了 4 个独立展开/收起面板的统一编排方案，并将推演耗时控制在 1.2~1.8 秒。
3. **交互瘦身与零截断落地**：确立了顶部 7 张卡片 15~16px 紧凑单行无省略号方案，建仓单 15 字指令表头 ⓘ 悬停方案，以及存量调仓单 16 列➔9 列带图标精简方案。
4. **增补作战卡片**：明确了《三句话看懂本方案》在步骤二与三之间的三栏卡片落地形态。
5. **安全回归基线确立**：梳理出 3 大测试文件的全部核心断言清单，为后续 Agent-3 极简无截断重构提供了 100% 确定性的现状图谱。

---

## 5. Verification Method (独立验证方法)

后继 Agent 或评审员可通过以下步骤独立核验本报告发现：

1. **检查 `cat_map` 现状**：
   ```powershell
   Get-Content AGY2_FundAdvisory/app_gui.py | Select-String -Pattern "cat_map" -Context 2,5
   ```
   可核验第 1869-1874 行的硬编码字典与第 1877、1881、1888、1918 行的调用点。

2. **验证现有 AppTest 渲染测试通过情况**：
   ```powershell
   cd AGY2_FundAdvisory
   python -m pytest tests/test_e2e_gui_render.py -k "test_bug6_streamlit_apptest_full_render" -v
   ```
   预期输出：`1 passed, 7 deselected in ~63s`。

3. **验证界面排版与 cols_9 正则测试**：
   ```powershell
   cd AGY2_FundAdvisory
   python -m pytest tests/test_acceptance_r1_r7.py -k "test_gui_step3_table_columns" -v
   ```
   预期输出：`1 passed`。

4. **验证高对比度与组件 key 测试**：
   ```powershell
   cd AGY2_FundAdvisory
   python -m pytest tests/test_ui_and_logic_refinements.py -k "test_visual_contrast or test_first_screen" -v
   ```
   预期输出：`2 passed`。
