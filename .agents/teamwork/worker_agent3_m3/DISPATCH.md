## 2026-10-29T17:29:38Z
[Message] timestamp=2026-10-29T17:29:38Z sender=6e8d54f5-05f1-4da4-a35e-9c3d019df46f priority=MESSAGE_PRIORITY_HIGH content=你已被任命为 GUI & Workflow White-box Designer (Agent-3)。
工作目录：d:\Google\Workspace\Wind\.agents\teamwork\worker_agent3_m3
用户原始需求文档（必须首先完整阅读）：d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
项目总体架构与契约：d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_3\PROJECT.md
前置勘测分析报告：d:\Google\Workspace\Wind\.agents\teamwork\explorer_orch3_2\analysis.md
目标工程根目录：d:\Google\Workspace\Wind\AGY2_FundAdvisory

【独占写权限文件】
你唯一拥有独占写入权限的文件为：`d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py`
严禁修改其他任何业务文件或测试文件！绝对严禁触碰 4 个系统只读裁判基建文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）。

【MANDATORY INTEGRITY WARNING】
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

【核心重构任务】
1. 彻底移除第 1869-1874 行的静态 `cat_map` 字典，调用 `portfolio_manager.py` 的统一资产分类解析器 `pm.classify_fund_asset_class(code)`（包含本地健壮性兜底），彻底消灭核心策略基金被误归为“其他存量资产”的缺陷。
2. 重构步骤二为四阶量化推演工作流白盒：
   - 点击【⚡ 立即现场推演】或切换档位时，引入 `time.sleep(0.35)` 步进阶梯，将演算反馈稳定控制在 1.2 至 1.8 秒舒适节奏；
   - 提供 4 个独立可自由展开/收起的推演白盒步骤面板：
     - Step 1：全市场 28,177 只公募基金四级漏斗海选（展开展示淘汰数据流、六维评分加权公式，以及当前档位各入选赛道的《冠军标的 vs 同赛道备选六维得分 PK 明细表》与一键替换下拉框）；
     - Step 2：宏观与衍生品四维状态机实时定调（展开展示 4 张决策信号卡片并用通俗语言解释为什么今天系统选择进攻、震荡收息或防守）；
     - Step 3：2018-2026 跨牛熊 2,000+ 交易日实境回测与压力测试（展开展示五大人话指标量化归因与不同市场环境表现定位表）；
     - Step 4：交易摩擦精算、限购拆单与实盘执行清单（展开展示手续费精算、预计股息覆盖回本周期与限购自动拆单路由逻辑）。
3. 顶部 7 张核心卡片零截断与白话翻译：
   - 主数值微调至 15~16px 紧凑单行显示，消除省略号截断；
   - 标题主数值通俗简练（如 `🟢 震荡收息期`、`🔥 科技主升浪`、`📈 结构分化期`、`🛡️ 熊市防守期`），专业黑话收进 ⓘ 悬停提示中。
4. 新增《三句话看懂本方案：怎么赚钱、为什么能赢、风险与铁律》三栏作战卡片：
   - 放置在步骤二推演白盒之后、步骤三执行单之前；
   - 第一栏：收益引擎拆解；第二栏：跨资产低相关对冲反脆弱机制；第三栏：历史最极端浮亏金额、最长回本天数与 7 天不赎、便宜区不割两条铁律。
5. 执行单与存量调仓单 9 列精简：
   - 建仓执行单：严格保留源码中的 `cols_9` 列表声明以兼容既有正则断言，最后一列提炼为 15 字以内核心动作指令，详细原理解析置于表头 ⓘ 悬停；
   - 存量调仓表：同样控制在 9 列以内，在 1080p 屏幕下无横向滚动条，用醒目图标直接标明操作动作（`➕ 建议加仓`、`➖ 建议减仓`、`🔒 未满7天锁仓保护`、`⏳ 临近30天免赎期缓卖`）。
6. 全量兼容既有 AppTest 断言（组件 key `gui_scenario_mode_v2`、`plan_capital_input`、`btn_run_simulation_now`，对比度色值，`expanded=False` 等），本地运行 `pytest tests/test_e2e_gui_render.py` 与 `pytest tests/test_acceptance_r1_r7.py` 验证 100% 通过。

【交付物要求】
在 `d:\Google\Workspace\Wind\.agents\teamwork\worker_agent3_m3\changes.md` 记录详细改动，在 `handoff.md` 输出测试运行命令与结果。完成后使用 `send_message` 向 orchestrator 汇报。
