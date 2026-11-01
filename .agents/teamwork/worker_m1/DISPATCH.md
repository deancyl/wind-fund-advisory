## 2026-10-31T23:43:41Z
你是一名高级前端与量化工程专家（teamwork_worker）。
你的工作目录是：d:\Google\Workspace\Wind\.agents\teamwork\worker_m1\
你在本次任务中拥有对 `d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py` 的**专属独占写权限**。严禁修改 4 个系统只读裁判文件（judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py）。

【必读文件】：
1. d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md（尤其是 Follow-up — 2026-10-31T23:29:05Z 阶段二重构要求）
2. d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_5\PROJECT.md
3. d:\Google\Workspace\Wind\.agents\teamwork\teamwork_explorer_survey_1\handoff.md（GUI 架构重构蓝图与代码片段）
4. d:\Google\Workspace\Wind\.agents\teamwork\teamwork_explorer_survey_2\handoff.md（后端量化接口契约与伪代码）

【MANDATORY INTEGRITY WARNING】：
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

【实施任务清单（Milestone 1）】：
1. **反偷懒红线与工程约束**：
   - 彻底删除 `app_gui.py` 中所有的 `time.sleep` 调用（特别是 4 处假延迟：原 714, 724, 735, 756 行），移除人为制造的 `sim_elapsed = max(1.22, ...)`，改为真实毫秒级耗时。
   - 彻底删除所有硬编码的 `"限额买500"`、`"现金分红·限额买500"`。
   - 确保 `cols_9 = [...]` 变量名与 9 个列名保持兼容以防既有断言失效。
2. **顶部全局看板大瘦身（1 行 4 宽卡 + 1 个紧凑刷新按钮）**：
   - 将原先 3 层 7 窄卡 + 顶部横幅 + 底部蓝条彻底精简为 1 行 4 张宽裕卡片 + 1 个刷新按钮：
     - 卡片 1【🕒 交易时钟与窗口 ⓘ】：主值 `🟢 14:30黄金窗口` / `🔵 盘中观察期` / `🟡 盘后已关账`；副标题：`距下次常规网格日 X 天`（悬停 `ⓘ` 展示 15:00 申赎成交规则）。
     - 卡片 2【🧭 市场定调与攻防线 ⓘ】：主值：`🟢 震荡收息期` / `🔥 科技主升浪` / `🛡️ 熊市防守期`；副标题直接展示双向点位 `📈破 4,141 进攻 ｜ 🛡️跌 3,846 防守`（悬停 `ⓘ` 显示沪深300现价、MA20/MA60 及突破后的具体加减仓方向）。
     - 卡片 3【🌡️ 估值与资金面温度 ⓘ】：主值：`估值极便宜 · 资金充裕`；副标题：`股票性价比高｜央妈呵护`（将 ERP 分位数、DR007、期权 IV、IC 贴水率放入 `ⓘ` 悬停 title 中，主界面零专业黑话）。
     - 卡片 4【💰 我的总资产与今日预估 ⓘ】：主值：`¥XXX,XXX.XX`；副标题：`今日预估 ¥+XX.XX (+X.XX%)`，右侧并排放置紧凑的 `🔄 刷新实时行情` 按钮。
   - 调整 CSS，确保 1080p 下绝无省略号（`...`）截断。
3. **重塑四大主导航 Tab（功能入口清晰、职责单一）**：
   - **Tab 1：`🌱 新资金从0建仓推演`**：
     - 去除“场景一/场景二”下拉框；
     - 步骤一保留模式 A（滑块 C1~C5）与模式 B（30秒风险测评）；
     - 步骤二：4 个白盒推演抽屉（`expanded=False`），抽屉标题动态呈现核心量化数字摘要；保留 5 张核心结果卡与《三句话看懂本方案》三栏卡片；
     - 步骤三：9 列执行单表格，第 9 列 `实操分红与限购指引` 动态绑定 `blueprint["items"]` 的 `action_guide`；若存在全赛道限购溢出（`blueprint.get("dca_plan")`），在下方醒目展示《超限资金分批定投执行计划》。
   - **Tab 2：`💼 我的当前持仓与今日调仓建议`**（垂直排布）：
     - 第一层【🚦 今日是否适合调仓？AI 综合裁决卡】：调用 `StrategyBridge.evaluate_today_rebalance_suitability(pm, active_tier)` 渲染红/黄/绿横幅与 4 个胶囊四维实测结论。
     - 第二层【⚖️ 今日怎么调？如果一定要调仓会有什么后果？】：调用 `StrategyBridge.simulate_rebalance_modes_and_consequences(pm, active_tier)`；提供单选切换（模式一：温和免伤调仓 vs 模式二：强行一步到位调仓）；并排渲染 4 张《本次调仓四大真实后果量化账单》卡片（手续费直接损耗、T+2在途踏空风险、攻防与回撤变化、持有期清零后果）；下方展示 9 列《今日建议调仓执行单》与一键执行/预案保存按钮。
     - 第三层【📋 我的实时持仓明细与接管录入】：展示实时持仓表；将《✨ 零门槛导入/新增持仓向导》、《✏️ 编辑修改持仓数据》、《📦 FIFO 份额批次免赎倒计时》全部设为 `expanded=(len(pm.holdings) == 0)`（有持仓时默认折叠）。
   - **Tab 3：`🔍 组合深度体检与算费工具箱`**：包含大类资产缺口图、加权行业暴露、重合度检测（已豁免双红利与限购伴生对）、底层重仓股排雷、聪明钱监控、在途对账与 A/C 算费器。
   - **Tab 4：`📈 策略历史回测与胜率档案`**：包含 C1~C5 回测曲线、水下回撤图、大类仓位变迁图、6 大切片战报与历史相似行情匹配器。
4. **编译与验证**：
   - 确保 `app_gui.py` 语法 100% 正确（通过 `py -3.11 -m py_compile AGY2_FundAdvisory/app_gui.py`）。
   - 运行既有测试，确保不引入语法或逻辑回归。
5. 在 `d:\Google\Workspace\Wind\.agents\teamwork\worker_m1\handoff.md` 输出详细修改报告与验证结果。
6. 完成后通过 send_message 发送完成通知给父 agent。


## 2026-11-01T00:04:04Z
**Context**: Milestone 1 app_gui.py refactoring
**Content**: 距离派发已达 20 分钟安全阈值。请汇报当前 app_gui.py 的重构进度：四大 Tab 与顶部 1 行 4 宽卡是否已完成修改？py_compile 语法检查与 pytest 运行结果如何？预计何时提交 handoff.md 报告？
**Action**: 请立即回复当前状态与预估完成时间。
