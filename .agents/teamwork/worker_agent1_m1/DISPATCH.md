## 2026-10-29T17:29:02Z
你已被任命为 Strategy & Risk Budget Architect (Agent-1)。
工作目录：d:\Google\Workspace\Wind\.agents\teamwork\worker_agent1_m1
用户原始需求文档（必须首先完整阅读）：d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
项目总体架构与契约：d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_3\PROJECT.md
前置勘测分析报告：d:\Google\Workspace\Wind\.agents\teamwork\explorer_orch3_1\analysis.md
目标工程根目录：d:\Google\Workspace\Wind\AGY2_FundAdvisory

【独占写权限文件】
你唯一拥有独占写入权限的文件为：`d:\Google\Workspace\Wind\AGY2_FundAdvisory\strategy_bridge.py`
严禁修改其他任何业务文件或测试文件！绝对严禁触碰 4 个系统只读裁判基建文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）。

【MANDATORY INTEGRITY WARNING】
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

【核心重构任务】
1. 实现 `compute_dynamic_tier_weights(history_df, tier, market_snapshot)`：
   - 以各档位风险预算（目标波动率与最大回撤容忍度 C1~C5）为约束边界；
   - 接入实时市场状态机（均线多空排列、ERP股债性价比、DR007资金面松紧、期权IV恐慌度与期指贴水率）：
     - 【主升浪进攻态/结构牛市】：在档位风险上限内，按动量强度动态放大进攻型资产（科创、中小盘成长、高弹性赛道）权重；
     - 【震荡收息态】：自动收缩高波动成长敞口，向高股息红利、低波防御与跨市场对冲资产倾斜；
     - 【破位防御态（跌破中长期均线且均线向下发散）】：所有档位（含高进取型 C4/C5）必须按算法比例自动触发止损降仓保护，将高 Beta 权益敞口动态切换至纯债与黄金避险；
   - 严格保证风险单调性：在牛市、震荡、熊市任意市场输入下，必须数学保证 C1 至 C5 目标权益仓位严格单调递增，即 `Equity(C1) < Equity(C2) < Equity(C3) < Equity(C4) < Equity(C5)`。
   - 彻底废除或重构原有静态写死字典 `TIER_TARGET_WEIGHTS`，让 `get_tier_target_weights` 全面调用 `compute_dynamic_tier_weights`。
2. 修复 `get_rebalance_grid_status()` 双向触发点位倒挂：
   - 严格基于当前指数实时点位与 MA20、MA60、MA120 真实相对位置动态计算；
   - 彻底根除 `c300_price * (4180.5 / 4053.0)` 导致防守线高于现价的荒谬错误！
   - 严格断言并保证：在任意市场行情下，向上进攻触发线点位严格大于当前现价（`surge_threshold_c300 > c300_current`），向下防守破位触发线点位严格小于当前现价（`breakdown_threshold_c300 < c300_current`），并输出触发后的具体调仓方向文案。
3. 确保 `generate_zero_start_blueprint` 统一调用动态权重生成建仓方案，限购拆单（如 050025 拆分为 050025 + 001071）保持无缝兼容。
4. 运行现有相关测试（如 `pytest tests/test_acceptance_r1_r7.py` 等）验证改动。

【交付物要求】
在 `d:\Google\Workspace\Wind\.agents\teamwork\worker_agent1_m1\changes.md` 记录详细改动，在 `handoff.md` 输出测试运行命令与结果。完成后使用 `send_message` 向 orchestrator 汇报。
