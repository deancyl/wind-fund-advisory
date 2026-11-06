# G5 世代工程闭环实施计划 (plan.md)

## 任务目标
实装 G5 世代四大真量化投顾能力（单基真实波动率穿透、历史三大拐点实盘对照、浮盈安全垫破净临界推演、14:30 尾盘估值异动防御）、完成前端 UI 紧凑联动、执行 /browser 视觉走查与全量门禁回归、归档 v3.5-G5 并生成 G6 世代指令。

## 阶段规划

### 阶段 0：全局勘测与技术基线摸底 (Survey)
- 派发 3 位 Explorer 调查现有代码基线：
  - Explorer 1: 勘测 `advisory_engine.py` 中 `calculate_vwap_execution_slippage` 的三档回退常数、本地净值/日线缓存、真实波动率及 bias_20 算法现状；
  - Explorer 2: 勘测历史三大拐点对照信号实现 (`verify_historical_inflection_signals`) 及前端接入点（首屏/Tab 1）；14:30 尾盘盘中实时估值 `gszzl` 与波动率预警逻辑；
  - Explorer 3: 勘测 `portfolio_manager.py`、`strategy_bridge.py` 与 `app_gui.py` 中持仓账本浮盈、Beta 计算、破净临界点及回本推演机制；现有测试套件现状。
- 汇总生成 `PROJECT.md`。

### 阶段 1 (M1)：量化核心模型与算法升级 (Quantitative Core Engine)
- Worker 编写实现：
  1. 单基 20 日真实年化波动率与自身 20 日均线乖离率 bias_20 穿透算法，消除固定回退常数 (0.04, 0.14, 0.18)；
  2. 历史三大拐点对照尺数据模型与接口输出；
  3. 账本加权 Beta、浮盈安全垫厚度、本金破净安全边际（沪深300跌幅点位）及大盘急跌情景推演模型；
  4. 14:30 尾盘实时估值异动（急涨防追高、急跌黄金坑）预警规则引擎；
- 门禁循环：Explorer -> Worker -> Reviewers (2) -> Challengers (2) -> Auditor -> Gate check.

### 阶段 2 (M2)：前端 Streamlit 界面深度联动与紧凑自适应排版 (GUI Integration)
- Worker 编写实现：
  1. 首屏/Tab 1 接入紧凑一行式历史三大拐点对照条；
  2. Tab 2 概览区接入加权 Beta、浮盈安全垫厚度、破净安全边际及 -3%/-5%/-10% 抗震情景推演卡片；
  3. Tab 2 调仓执行表与定投计划接入尾盘估值异动标签与差异化损耗基点；
  4. 遵循界面复杂度守恒原则，精简冗余文案，实施移动端 640px 紧凑 CSS 排版；
- 门禁循环：Explorer -> Worker -> Reviewers (2) -> Challengers (2) -> Auditor -> Gate check.

### 阶段 3 (M3)：视觉走查、全量回归、法证审计与版本交付 (Visual & Audit Delivery)
- 重启 8501 服务；
- 执行多模态视觉核查走查（四大 Tab、亮暗色主题、移动端视口）；
- 扩展 `tests/test_g3_evolution_loop.py` 专项测试，运行全量测试套件；
- 独立法证审计（teamwork_auditor）严格核查 4 大只读文件未篡改、无硬编码常数、无伪造数据；
- 更新 GEMINI.md 与 PROGRESS_LOG.md；
- Git commit，打 tag `v3.5-G5`，git push 同步；
- 编写 handoff.md 并向 Sentinel 发起胜利宣告。
