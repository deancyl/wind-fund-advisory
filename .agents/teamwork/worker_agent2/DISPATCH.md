## 2026-10-29T14:45:04Z
You are Agent-2: Quant Selection & Strategy Bridge Expert (量化选基与六维数据桥接专家).
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\worker_agent2
Your code base is: d:\Google\Workspace\Wind\AGY2_FundAdvisory
You exclusively own and write to: d:\Google\Workspace\Wind\AGY2_FundAdvisory\strategy_bridge.py
(IMPORTANT: In this initial phase, do NOT edit `portfolio_manager.py` because Agent-1 is currently editing it. Focus exclusively on `strategy_bridge.py` and preparing the quantitative scoring, derivatives integration, and dynamic selection functions.)

First, read:
1. `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`
2. `d:\Google\Workspace\Wind\PROJECT.md`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Strict Read-Only Invariants:
DO NOT modify, unlock, or write to:
- `AGY2_FundAdvisory/judge_engine.py`
- `AGY2_FundAdvisory/holdout_vault.py`
- `AGY2_FundAdvisory/AGENT_SPEC.md`
- `AGY2_FundAdvisory/tests/test_infra.py`

Your Task Scope (R5 and R2 bridge in strategy_bridge.py):

1. R5. 接入 WindToolkit 第 5 大模块 derivatives.py 并重构六维选基评分表:
- 在 strategy_bridge.py 的 get_latest_market_snapshot() 中接入 derivatives 模块（优先通过 WindToolkit 或读取本地 DuckDB 视图/Parquet，无数据时提供安全离线兜底），获取当前 IC/IM 股指期货年化贴水率(%) 与期权隐含波动率 IV(%)。
- 将期指贴水与期权 IV 融入顶部宏观雷达提示中（温和区间且贴水收敛支持成长进攻；极端飙升预警尾部波动），并在选基评分中为受益标的提供量化依据。
- 在 snapshot 中输出相关字段（如 `ic_annualized_basis_rate`, `im_annualized_basis_rate`, `option_iv_pct`, `derivatives_sentiment` 等）。

2. 重写选基漏斗与多因子实时评分逻辑:
- 实现全市场四级过滤漏斗数据统计（优先从本地 fund_catalog.parquet 真实统计）：
  全市场基金总池 (28,177只) -> 合规初筛池 (规模>2亿、成立>3年，共6,850只) -> 当前档位核心赛道候选池 (动态统计入围只数) -> 最终优选金牌组合 (动态显示当前档位实际配置的基金只数)。
- 综合评分计算公式：
  总评得分 (0-100) = 35% * 历史超额Alpha得分 + 25% * 低费率得分 + 15% * R1底层排雷健康分 + 10% * R3北向聪明钱流入分 + 10% * 反拥挤度安全分 + 5% * 衍生品与宏观契合度。
- 提供函数或数据结构，供 GUI 展示《当前档位入选赛道：冠军标的与备选基金六维量化评分对比表》（包含赛道、基金代码、基金名称、各项六维得分、总评分、是否当前配置等），并保留替换标的支持。

3. R2 选基漏斗与档位对齐准备:
- 确保提供的入围赛道与冠军标的，与 C1 至 C5 各档位配置保持 100% 一致：
  * C1 安稳保守型（5%-8%）：002351 (50%) + 000086 (20%) + 005561 (20%) + 000216 (10%)
  * C2 稳健平衡型（8%-12%）：002351 (35%) + 005561 (25%) + 100032 (20%) + 000216 (14%) + 050025/001071 (6%)
  * C3 平衡进取型（12%-18%）：100032 (38%) + 005561 (30%) + 000216 (14%) + 002351 (12%) + 050025/001071 (6%)；进攻期切入 011613 与 001053
  * C4 成长进攻型（18%-30%）：011613 (30%) + 001053 (18%) + 100032 (24%) + 000216 (14%) + 002351 (8%) + 050025/001071 (6%)
  * C5 极限高Beta追击型（30%-100%）：011613 (38%) + 016634 (22%) + 013841 (15%) + 100032 (10%) + 000216 (10%) + 050025/001071 (5%)

Verification & Handoff:
- Run tests on strategy_bridge (e.g. `pytest tests/test_strategy_bridge.py` or existing tests) to verify code compiles and tests pass.
- Write your detailed handoff report to `d:\Google\Workspace\Wind\.agents\teamwork\worker_agent2\handoff.md`.
- Keep `progress.md` updated during your work.
- Use `send_message` to notify orchestrator upon completion with path to handoff.md.
