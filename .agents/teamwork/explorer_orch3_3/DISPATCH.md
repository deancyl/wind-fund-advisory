## 2026-10-29T17:17:29Z
你已被任命为 Test Suite & Red Team Explorer。
工作目录：d:\Google\Workspace\Wind\.agents\teamwork\explorer_orch3_3
用户原始需求文档（必须首先完整阅读）：d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
目标工程根目录：d:\Google\Workspace\Wind\AGY2_FundAdvisory

【任务目标】
针对 AGY2_FundAdvisory 工程中的 `tests/` 目录、4 个裁判基建文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）以及现有 222 项测试进行全面勘测与基线摸底，梳理测试运行方式、只读约束以及 Agent-4 需编写的新增测试方案。

【调查要点】
1. 严禁修改任何业务代码或测试文件（只读勘测）。
2. 绝对红线检查：
   - 检查 4 个只读裁判基建文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）的文件属性、哈希/内容摘要、只读状态，确认绝无修改痕迹。
3. 现有测试套件基线：
   - 检查目前测试用例的组织结构（单元测试、集成测试、AppTest 渲染测试）。
   - 检查测试执行命令与通过情况（可以在沙箱中安全运行测试命令进行只读摸底，或查看已有测试日志，报告 222 项测试目前的通过状态）。
4. 新增测试规范勘测（为 Agent-4 制定详尽的测试设计方案）：
   - AST 静态代码审计测试设计：如何在 `tests/` 下编写 AST 遍历，扫描 `portfolio_manager.py`、`strategy_bridge.py`、`app_gui.py` 中的所有 Constant/Str/Compare 节点，严密校验无写死的股票代码（如 6 位数字代码 if/else 豁免分支）及静态 cat_map。
   - 动态风险预算单调性与攻防状态机自适应测试设计：牛市进攻、震荡磨底、熊市破位三组市场输入下，断言 C1 至 C5 目标权益仓位单调满足 `C1 < C2 < C3 < C4 < C5`。
   - 双向变盘触发点位逻辑校验测试设计：断言在任意市场输入下，向上进攻触发线点位严格高于现价，向下防守破位触发线点位严格低于现价。
   - 界面无截断与 9 列规范在 AppTest 中的断言方法。

【交付物要求】
将详细调查发现写入 `d:\Google\Workspace\Wind\.agents\teamwork\explorer_orch3_3\analysis.md`，并在同目录下输出符合规范的 `handoff.md`。完成后通过 `send_message` 向 orchestrator 汇报。
