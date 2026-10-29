## 2026-10-29T17:17:21Z
你已被任命为 GUI & Workflow Explorer。
工作目录：d:\Google\Workspace\Wind\.agents\teamwork\explorer_orch3_2
用户原始需求文档（必须首先完整阅读）：d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
目标工程根目录：d:\Google\Workspace\Wind\AGY2_FundAdvisory

【任务目标】
针对 AGY2_FundAdvisory 工程中的 `app_gui.py` 进行只读深度代码与交互规范勘测，梳理界面组件布局、推演工作流白盒、静态 cat_map 现状、表格列数与截断问题，为后续 Agent-3 的极简无截断重构提供精确的现状图谱。

【调查要点】
1. 严禁修改任何业务代码或测试文件（只读勘测）。
2. 重点审查 `app_gui.py`：
   - 静态 `cat_map` 字典现状：在何处定义并被调用？如何平滑迁移至调用 `portfolio_manager.py` 的统一资产分类解析器？
   - 步骤二与【立即现场推演】/切换档位：现有演算动画与进度反馈机制、4 个推演步骤面板的组织结构与展开/收起状态（Step 1 漏斗海选+PK明细+替换；Step 2 4张宏观与衍生品决策卡片人话解析；Step 3 2018-2026 回测五大人话指标；Step 4 交易摩擦与拆单路由）。
   - 顶部 7 张核心卡片现状：CSS/样式、标题与主数值单行显示无省略号截断（如 `🟢 震荡收息期`、`🔥 科技主升浪`、`📈 结构分化期`、`🛡️ 熊市防守期`）的实现方案，ⓘ 悬停原理解析如何布局。
   - 步骤三《建仓/调仓执行单》与存量调仓单表格现状：列数现状（是否保持 9 列无横向滚动条）、最后一列“下单实操要点”字数控制（15字以内核心动作指令）与表头 ⓘ 悬停方案；调仓动作醒目图标（`➕ 建议加仓`、`➖ 建议减仓`、`🔒 未满7天锁仓保护`、`⏳ 临近30天免赎期缓卖`）。
   - 《三句话看懂本方案》三栏作战卡片的现有形态或需新增的位置。
   - Streamlit AppTest 测试用例现状：现有 tests 针对 `app_gui.py` 的 AppTest 覆盖了哪些交互分支，有哪些断言需要兼容。

【交付物要求】
将详细调查发现写入 `d:\Google\Workspace\Wind\.agents\teamwork\explorer_orch3_2\analysis.md`，并在同目录下输出符合规范的 `handoff.md`。完成后通过 `send_message` 向 orchestrator 汇报。
