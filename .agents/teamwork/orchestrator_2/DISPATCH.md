# DISPATCH — orchestrator_2

Working directory: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_2
Original request: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Code working directory: d:\Google\Workspace\Wind\AGY2_FundAdvisory

## 2026-10-29T14:41:16Z

[Message from 32aa8f5a-9883-4d9f-9fe1-9f1733eb1cc3]
启动多智能体协同重构任务：请调度以下 4 个子智能体角色协同作业，完成后统一汇总验收：
1. Agent-1（账本与风控修复专家 - 负责 portfolio_manager.py）：修复新建仓峰值回撤状态污染、金融股“存贷双高”误判豁免、限购拆单伴生组合 100% 重合度误报豁免、底层重仓股按股票代码合并去重。
2. Agent-2（量化选基与六维数据桥接专家 - 负责 strategy_bridge.py 与 portfolio_manager.py）：打通 WindToolkit 全部 6 大模块（重点补齐 derivatives.py 期指贴水与期权 IV），构建 C1 至 C5 五档差异化动态基金池与多因子实时评分选基漏斗。
3. Agent-3（UI/UX 极简交互设计师 - 负责 app_gui.py）：解除“目标收益滑块被问卷暗中锁死在 C3”的交互缺陷，将首屏垂直高度压缩 50%，表格列数从 13 列精简至 9 列以消除横向滚动条，所有二级长文抽屉默认设为收起状态（expanded=False）。
4. Agent-4（红队测试与渲染审计员 - 负责 tests/）：针对 C1 至 C5 滑块实时切换、建仓后回撤归零、银行股排雷豁免、拆单重合度豁免及衍生品模块接入编写端到端自动化测试。

Working directory: d:\Google\Workspace\Wind\AGY2_FundAdvisory
Integrity mode: development
