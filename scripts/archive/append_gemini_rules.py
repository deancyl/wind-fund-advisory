from pathlib import Path

GEMINI_PATH = Path("GEMINI.md")
content = GEMINI_PATH.read_text(encoding="utf-8")

new_rules = """

## 27. CommonMark 4+ 空格缩进代码块防御与 HTML 绝对纯化铁律 (CommonMark Indented Code Block Defense & Safe HTML Invariant)
- **拒绝裸 HTML 代码块泄露**：在 Streamlit 中，严禁在多层缩进的 Python `f\"\"\"...\"\"\"` 代码块内部拼接带有前导空格的多行 HTML 字符串并直接传入原生 `st.markdown(..., unsafe_allow_html=True)`；
- **防线一：组件源头提纯**：凡返回富文本 HTML 片段的函数（如 `render_historical_inflection_ruler_html`、`render_portfolio_cushion_and_stress_card_html`），返回值必须强制包裹 `return _clean_html(...)`，物理剥离每行首尾空格与空行；
- **防线二：统一安全渲染入口**：前端富文本渲染强制统一收口至 `safe_markdown_html(...)`，从底层机制上彻底消灭任何行首空格达到 4 个触发 CommonMark Indented Code Block 语法规则的可能。

## 28. Tab 2 决策主流程与账本运维工具坞视图解耦铁律 (Tab 2 View Mode Decoupling & Cognition Invariant)
- **决策与运维职责泾渭分明**：Tab 2 顶部强制实装双视图模式切换器，彻底解耦“持仓诊断与智能调仓 (主流程)”与“账本运维与实盘复盘档案 (宽屏工具坞)”；
- **主流程极致聚焦**：默认主视图仅展示浮盈安全垫抗震看板、持仓资产核心表、核心标的五维时机研判与智能调仓建议单，完全跳过底部 6 大运维工具箱展开项，将主决策流垂直滚动高度物理缩短 40% 以上，首屏信噪比大幅提升；
- **独立运维工具坞**：切换至运维工具坞时，宽屏专注呈现 6 大专业运维工具（快速记账与导入、FIFO批次透视、影子账本对账中心、同公司低摩擦转换、宏观分红自适应研判及家庭账本汇总），保持所有已有静态与动态测试契约 100% 稳定兼容。

## 29. 在线启发式因子基因自适应进化算子与换手率/回撤惩罚规范 (Online Heuristic Factor Evolver Specification)
- **动态因子权重彻底终结伪常数**：机会雷达 14 大赛道扫描严禁使用静态经验固定权重；必须通过 `OnlineHeuristicFactorEvolver` 基于本地真实历史多赛道对齐收益率与特征张量进行在线基因演化求解；
- **双重硬约束与鲁棒适应度**：染色体四维因子权重强制满足每维权重 $w_i \\ge 0.05$ 且 $\\sum w_i = 1.000000$；适应度函数必须严格叠加换手率惩罚（$-0.8 \\times \\text{Turnover}$）与尾部最大回撤约束（$-1.5 \\times \\text{TailMDD}$），求解耗时控制在 150ms 以内；
- **首屏白盒微图透明展示**：在首屏机会雷达标题旁提供【🧬 基因进化白盒算子】徽章与展开微图，动态呈现近 60 日滚动演化净值对比（动态演化 vs 静态基准）与四维因子演化轨迹，让买方投资者完全看透因子权重的科学推导过程。
"""

if "CommonMark 4+ 空格缩进代码块防御" not in content:
    content += new_rules
    GEMINI_PATH.write_text(content, encoding="utf-8")
    print("✅ Successfully appended G7 rules to workspace GEMINI.md!")
else:
    print("G7 rules already present.")
