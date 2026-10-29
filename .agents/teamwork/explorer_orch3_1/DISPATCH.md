## 2026-10-29T17:17:12Z
你已被任命为 Core Quant Engine Explorer。
工作目录：d:\Google\Workspace\Wind\.agents\teamwork\explorer_orch3_1
用户原始需求文档（必须首先完整阅读）：d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
目标工程根目录：d:\Google\Workspace\Wind\AGY2_FundAdvisory

【任务目标】
针对 AGY2_FundAdvisory 工程中的 `strategy_bridge.py` 和 `portfolio_manager.py` 进行只读深度代码与架构勘测，全面梳理现状、硬编码排查点、动态模型与接口契约，为后续 Agent-1 与 Agent-2 的无硬编码重构提供精确的现状图谱。

【调查要点】
1. 严禁修改任何业务代码或测试文件（只读勘测）。
2. 重点审查 `strategy_bridge.py`：
   - `compute_dynamic_tier_weights` 当前实现逻辑：目标波动率与最大回撤边界约束、三态自适应调节（进攻态、震荡态、破位防御态）、C1~C5 单调性支持现状。
   - `get_rebalance_grid_status` 点位计算现状：MA20/60/120 相对位置、向上突破进攻线（是否严格高于现价）、向下跌破防守线（是否严格低于现价）、双向触发点位倒挂风险排查。
   - 宏观状态与衍生品桥接现状。
3. 重点审查 `portfolio_manager.py`：
   - `screen_fund_look_through_risk` 当前排雷逻辑：是否存在针对特定股票代码的硬编码 if/else 或豁免列表？如何落地三层通用排雷（第一层申万/标准行业金融业态识别；第二层重资产硬科技/公用事业现金流与资产结构交叉校验；第三层高现金高息融资真伪造假识别）。
   - 统一资产分类解析器（如 `classify_fund_asset_class` 或类似方法）现状：是否已有动态解析器？能否全面替代 app_gui.py 中的静态 cat_map？
   - 六维选基评分（Alpha、费率、排雷健康度、北向聪明钱、反拥挤度、期指贴水契合度）的实现方式与正规化（0~100）现状，是否存在伪造打分或哈希近似。
   - `apply_zero_start_blueprint` 等建仓/调仓函数的接口参数与现有行为。
4. 梳理 `strategy_bridge.py` 与 `portfolio_manager.py` 之间的接口调用契约。

【交付物要求】
将详细调查发现写入 `d:\Google\Workspace\Wind\.agents\teamwork\explorer_orch3_1\analysis.md`，并在同目录下输出符合规范的 `handoff.md`。完成后通过 `send_message` 向 orchestrator 汇报。
