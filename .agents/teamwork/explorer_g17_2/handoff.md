# Handoff Report — Explorer G17-2

## 1. Observation
1. **手机端截图缺陷直接观测**：
   - 图像路径：`C:/Users/deanc/.gemini/antigravity/brain/1395b6f9-733c-4446-9cdb-f33a19e5f711/.user_uploaded/media_1794406255999_c8abd7ad.png`。
   - 观测现象：
     - 顶层主导航仅显示「🌱 新资建仓」、「💼 持仓调仓」、「📈 组合回测」，第 4 个主 Tab「🔍 穿透工具」被整体截断，完全不可见。
     - 顶部 4 张全局指标卡垂直单列串联堆叠，占满整个首屏纵向空间。
     - 五维备忘录由 5 个巨大的文本卡片垂直连续纵向排列（今日行动准则、宏观与政策面、国际与汇率面、产业与估值面、存量持仓病灶），文本量约 600 字，占满两屏以上。
     - 备忘录标题栏的「买方高密情报矩阵」徽章因空间挤压文字呈现竖排断裂。
     - 备忘录下方独立堆叠了一个「今日投顾参谋」折叠框，存在同质化双重堆叠。
     - 表格前三列为「基金代码、基金名称、份额」，关键决策列「建议金额、操作建议、盈亏率」均被溢出截断在右侧滚动区域。
2. **源码法证行号与规则提取**：
   - `AGY2_FundAdvisory/app_gui.py:1274-1284`：顶层主导航被定义为 `grid-template-columns: repeat(4, 1fr) !important; gap: 10px !important;`；按钮声明 `height: 46px !important; font-size: 16px !important; padding: 0 10px !important;`。
   - `AGY2_FundAdvisory/app_gui.py:1632-1670`：`@media (max-width: 640px)` 媒体查询中完全缺失针对顶层主导航与顶栏指标卡的流式网格规则。
   - `AGY2_FundAdvisory/app_gui.py:288-370`：`render_chief_advisor_memo_card` 在 `@media (max-width: 768px)` 下仅将 `.chief-memo-grid-2x2` 改为 `grid-template-columns: 1fr !important;`，导致 4 个详细文本框垂直堆叠，且标题栏未设 `white-space: nowrap`。
   - `AGY2_FundAdvisory/app_gui.py:3597-3615`：首屏同时执行了 `render_chief_advisor_memo_card(memo_top)` 与 `st.expander(f"{act_status_icon} {expander_title}")`，造成双重容器垂直堆叠。
   - `AGY2_FundAdvisory/app_gui.py:2475-2515`：`switch_active_ledger` 仅更新了 `st.session_state.active_ledger_id` 与 `pm` 实例，并将诊断状态重置为 `False`，未向 `st.session_state["pending_cross_tab_jump"]` 注入跳转指令，导致用户切换存量账本后依然留在 Tab 0。
   - `AGY2_FundAdvisory/app_gui.py:4467, 5952, 6705`：Tab 0、Tab 1 的 DataFrame 列定义数组中，关键的买入金额（第 6 列）、盈亏率（第 8 列）、调仓操作（第 8 列）严重靠后。
   - `AGY2_FundAdvisory/app_gui.py:2217-2255`：`render_liquidity_haircut_table` 在订单金额较小（折价为 0.00 元）时依然渲染完整 10 列大表折叠框。
3. **测试契约观测**：
   - `cmd /c "set PYTHONPATH=... && py -3 -m pytest AGY2_FundAdvisory\tests\test_infra.py"`：15 passed in 12.58s。
   - `tests/test_adversarial_m2_challenger2_timemachine_and_memo.py:98-143` 明确断言 `render_chief_advisor_memo_card` 在输入 None 或空字典时不调用 `st.markdown`，在正常渲染时单行绝不包含 4 个前导空格，且支持缺失键的偏字典。

## 2. Logic Chain
1. **主导航截断推导**：
   - 观测到桌面端导航采用 `grid-template-columns: repeat(4, 1fr)` 且按钮为 `16px` 字号。
   - 移动端视口宽度为 390px，扣除左右安全外边距 24px 后仅剩 366px。
   - 4 个中文按钮单项最小字宽 + padding 约为 96px，4 项共需 384px + 30px gap = 414px > 366px。
   - 由于 CSS 缺乏移动端自适应覆盖，Streamlit 容器发生溢出截断，导致第 4 项「🔍 穿透工具」被推出视口。
   - 因此，必须在 `@media (max-width: 768px)` 中将其重构为 2×2 网格（`grid-template-columns: repeat(2, 1fr) !important;`），每项宽约 177px，保证 100% 完整容纳。
2. **顶栏指标卡高度压缩推导**：
   - 观测到 `top_c1..c4 = st.columns(4)` 在 `<768px` 被强制单列堆叠，总高度达 340px。
   - 将其改为 `display: flex; flex-wrap: wrap;` 且每列 `calc(50% - 6px)`，在手机端以 2×2 田字格呈现，垂直高度压降 50%（至 ~150px）。
3. **首屏文字墙消灭与双框合流推导**：
   - 观测到五维备忘录 5 块巨型文本框约 600 字直接平铺，且下方紧跟独立抽屉。
   - 认知负荷过重且与下方抽屉信息同质化。
   - 重构为单一「🧭 首席投顾今日裁决台」：首屏常驻直显区高度严格控制在 ≤ 110px（第一行核心定调 + 仓位推导公式 + 时间戳，第二行 5 颗 ≤20 字精要胶囊）；详细文段、Top 3 机会雷达卡与主动风控哨收纳于可点击展开的抽屉内。
4. **存量账本自动路由推导**：
   - 观测到 `switch_active_ledger` 切换后因缺乏跳转信号停留在 Tab 0。
   - 在函数中判定若 `len(new_pm.holdings) > 0`，则注入 `pending_cross_tab_jump`（`tab_index: 1`）并设置 `tab2_diagnosed = True`。
   - 页面 rerun 时已有的 DOM 注入脚本会立即触发 `tabs[1].click()`，实现平滑跳转并即刻展示 29 基实战诊断与三阶手术单。
5. **表格列顺序优化推导**：
   - 窄屏下横向展示容量有限（通常仅露出 3~4 列）。
   - 将决策最关心的「标的名称/代码、金额、盈亏率/占比、操作建议」置于最左侧 1~4 列，使用户一目了然，无需右滑。

## 3. Caveats
1. **测试用例签名依赖**：`tests/test_phase2_apptest_gui.py` 属于较早世代的测试套件，部分断言针对早期旧代码（如 `top_c1..top_btn = st.columns`）。本次 G17 重构必须确保 `tests/test_infra.py` 与 `test_adversarial_m2_challenger2_timemachine_and_memo.py` 100% 绿灯。
2. **纯前端样式与状态机设计**：本 Explorer 仅进行只读法证与方案设计，未修改任何生产代码文件。所有修改建议已形成精确代码蓝图供 Implementer 使用。

## 4. Conclusion
G17 世代的手机端与首屏交互缺陷病灶明确、根因清晰。通过在全局 CSS 中注入移动端 2×2 主导航与田字格指标卡样式、将五维备忘录与参谋栏合流为 ≤110px 极简裁决台、在账本切换函数中补齐跨 Tab 路由、并优化表格列优先级，可彻底解决手机端截断与首屏冗长问题，完全达到准商用机构级交互标准。

## 5. Verification Method
1. **自动化测试**：
   ```powershell
   cmd /c "set PYTHONPATH=D:\Google\Workspace\Wind\AGY2_FundAdvisory;D:\Google\Workspace\Wind && py -3 -m pytest AGY2_FundAdvisory\tests\test_infra.py"
   cmd /c "set PYTHONPATH=D:\Google\Workspace\Wind\AGY2_FundAdvisory;D:\Google\Workspace\Wind && py -3 -m pytest tests\test_adversarial_m2_challenger2_timemachine_and_memo.py"
   ```
2. **手机视口视觉核验 (390x844)**：
   - 确认四大主 Tab 呈现 2×2 网格，「🔍 穿透工具」100% 露出且无溢出；
   - 确认顶栏指标卡呈 2×2 田字格，首屏高度减半；
   - 确认首席投顾裁决台常驻高度 ≤ 110px，无 600 字文墙；
   - 切换至「实战存量组合（29只）」确认自动进入「💼 持仓调仓」并展开实战诊断。
3. **失效条件 (Invalidation Conditions)**：
   - 若手机视口下出现第 4 个 Tab 无法点击或被切断，则 CSS 选择器优先级不足；
   - 若 `render_chief_advisor_memo_card` 输出包含 4 个前导空格的行，则会破坏 CommonMark 缩进防线。
