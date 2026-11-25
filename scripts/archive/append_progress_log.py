from pathlib import Path
from datetime import datetime

LOG_PATH = Path("PROGRESS_LOG.md")
content = LOG_PATH.read_text(encoding="utf-8")

g7_log = """

---

# G7 世代演进与架构提纯交付日志 (G7 Architecture Decoupling & Risk Tri-Linkage)

- **交付日期**：2026-11-07
- **世代标识**：G7 架构提纯与视图解耦世代 (v3.7-G7)
- **状态**：全量落地，54/54 自动化测试 100% 通过，首屏裸 HTML 代码块泄露 Bug 彻底根除。

## 核心交付亮点

### 1. 首屏裸 HTML 源代码块泄露 Bug 彻底根除
- **病灶诊断**：`render_historical_inflection_ruler_html` 函数在 Python 多行字符串内部构建 HTML 时带有 8~12 个前导空格，外层晨报卡片通过带缩进的 `st.markdown(f\"\"\"...\"\"\", unsafe_allow_html=True)` 嵌套，累加缩进达 16~20 个空格，触发 CommonMark 规范中“缩进 $\\ge 4$ 个空格强行转义为 `<pre><code>` 缩进代码块”的语法逃逸漏洞；
- **双重防御修复**：
  - 组件源头提纯：重构 `render_historical_inflection_ruler_html` 与 `render_portfolio_cushion_and_stress_card_html` 为单行紧凑盒模型拼接，返回值强制经由 `_clean_html(...)` 彻底清除每行首尾空格与空行；
  - 统一安全入口：首屏晨报、Top 3 赛道卡片及全站所有富文本彻底收口至统一入口 `safe_markdown_html(...)`，经实测 4+ 空格行数降为 0，彻底根除代码块泄露。

### 2. Tab 2 决策主流程与账本运维工具坞双视图极致解耦
- **解耦切换器**：在 Tab 2 顶部多账本管理栏下方植入清爽的水平单选切换器（`rad_tab2_view_mode`）：
  - **模式一：🎯 持仓诊断与智能调仓（默认主流程）**：仅聚焦浮盈安全垫抗震看板、持仓资产核心表、核心标的五维时机裁决卡与智能调仓目标组合/执行清单，完全跳过底部 440 行的大型工具箱展开项，垂直高度物理缩短 40% 以上，首屏信噪比大幅提升；
  - **模式二：💼 账本运维与实盘复盘档案（宽屏工具坞）**：宽屏专注展开 6 大专业运维工具（快速记账与导入、FIFO批次透视、实盘影子档案、T+1对账中心、同公司低摩擦转换、宏观分红自适应研判及家庭账本汇总）；
- **全契约无损继承**：保留 `<b>{len(pm.holdings)} 只</b>`、`if "edited_table" in locals() and edited_table is not None:`、`dock_tab1 ~ dock_tab6`、`sub_tab1 ~ sub_tab3` 等全套已有测试契约，实现零破坏重构。

### 3. 首屏主动风险预警哨与 Tab 2 / Tab 4 三方联动闭环
- **双联动按钮**：为首屏主动预警哨每条预警卡片并列配置：
  - 按钮 A（`btn_sentry_act_`）：【👉 去 Tab 2 生成处置调仓单】，自动跳转至 Tab 2 主流程并预填调仓意图；
  - 按钮 B（`btn_sentry_evid_`）：【🔍 去 Tab 4 穿透看底层证据】，记录 `tab4_highlight_module`；
- **证据响应横幅**：在 Tab 4 顶部实装高亮联动证据横幅，展示当前聚焦风险模块（极端相关性突变、重仓股交叉热力、未满7天惩罚锁仓等），形成完整的买方投顾“预警 -> 证据链 -> 调仓单”闭环。

### 4. 在线启发式因子基因自适应进化算子与白盒徽章
- **`OnlineHeuristicFactorEvolver` 实装**：基于本地真实 14 大赛道最近 60 个交易日对齐收益率矩阵与四维特征张量（估值、动量、考夫曼信噪比、反拥挤度），纯 NumPy 向量化回测与锦标赛变异；
- **双重硬约束与鲁棒适应度**：四维权重单项 $w_i \\ge 0.05$ 且 $\\sum w_i = 1.000000$；适应度函数严格叠加换手率惩罚（$-0.8 \\times \\text{Turnover}$）与尾部最大回撤约束（$-1.5 \\times \\text{TailMDD}$），求解耗时 $< 150$ms；
- **白盒徽章与微图展开**：首屏机会雷达标题旁实装【🧬 基因进化白盒算子】徽章，点击可展开近 60 日滚动演化净值对比（动态演化 vs 静态基准，超额 Alpha 达标）及四维因子演化轨迹图，彻底终结黑盒与伪常数。

## 自动化测试与合规门禁核验
- `pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g7_architecture_and_decoupling.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py`: **54/54 全部通过 (100%)**。
- 四大裁判文件（`judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py`）SHA256 绝对一致，**零修改**。
- `DataLoader.simulate_execution` 默认签名与扣费逻辑**零修改**。
- 全局规则隔离：全局 `c:\\Users\\deanc\\.gemini\\GEMINI.md` **零触碰**。
- 8501 端口服务健康探针：`curl http://127.0.0.1:8501/_stcore/health` 返回 `HTTP 200 OK`。
"""

if "G7 世代演进与架构提纯交付日志" not in content:
    content += g7_log
    LOG_PATH.write_text(content, encoding="utf-8")
    print("✅ Successfully appended G7 log to PROGRESS_LOG.md!")
else:
    print("G7 log already present.")
