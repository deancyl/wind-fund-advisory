## 2026-10-31T14:44:32Z
[Message] timestamp=2026-10-31T14:44:32Z sender=d536f3b8-ee96-41ed-9fa9-cbd10993bb6a priority=MESSAGE_PRIORITY_HIGH content=你是 Agent-2（全天候攻防盈利算法专家），专精实现 Milestone 2 (M2)。
你的工作目录是: d:\Google\Workspace\Wind\.agents\teamwork\worker_agent2_orch4
原始需求文件路径 (必读): d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
项目工程蓝图: d:\Google\Workspace\Wind\PROJECT.md
前序勘测报告 (必读，包含代码行号、数学模型与实现细节): d:\Google\Workspace\Wind\.agents\teamwork\explorer_orch4_2\handoff.md
代码项目根目录: d:\Google\Workspace\Wind\AGY2_FundAdvisory

【文件独占写权限】
你独占拥有文件:
- `AGY2_FundAdvisory/strategy_bridge.py`
- `AGY2_FundAdvisory/data_loader.py`
严禁修改其他源文件，严禁触碰只读裁判文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）。

【MANDATORY INTEGRITY WARNING】
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

【核心实现任务】
依据 ORIGINAL_REQUEST.md §R3 与 explorer_orch4_2/handoff.md 中的指引，完整落地以下功能：

1. **清除静态权重劫持，实现 100% 动态权重计算**:
   - 检查 `strategy_bridge.py` 中的 `TIER_TARGET_WEIGHTS` (行 252-300)、`get_latest_market_snapshot()` (行 2603-2611)、`compute_dynamic_tier_weights()` (行 3567-3573)、`generate_zero_start_blueprint()` (行 4015-4035) 等各处；
   - 彻底清除 C3 档位静态写死的 `0.38 / 0.30 / 0.14 / 0.12 / 0.06` 常数，严禁让 C3 档位绕过动态权重计算；
   - 确保 C1 至 C5 所有档位的目标基金配比 100% 由 `compute_dynamic_tier_weights()` 动态算出；
   - 在 `compute_dynamic_tier_weights()` 中，真正接入并融合 Hedge 四大专家实时权重（`OnlineExpertWeightUpdater` 或其单例输出的 `get_online_expert_weights()` 专家概率 $P_i$）与 EWMA 波动率倒数平价，并严格保证各档位权益风险预算的单调性 $\text{Equity}(C1) < \text{Equity}(C2) < \text{Equity}(C3) < \text{Equity}(C4) < \text{Equity}(C5)$。

2. **在 `compute_dynamic_tier_weights()` 中植入完整三段式攻防闭环**:
   1) **左侧极值超卖吸筹**:
      当 `erp_percentile >= 75.0` 且沪深300或科创50的 20 日均线乖离率 `bias_20 <= -4.5%`（极度超卖）时，自动从纯债仓位（002351）中划拨 `10% ~ 15%` 仓位逆向增配高弹性宽基（011613 华夏科创50 / 001053 创金合信中证500），在底部左侧吃反弹。
   2) **右侧施密特迟滞防打脸**:
      在 `[-1.5%, +1.2%]` 均线迟滞缓冲带内，锁定前序仓位配置不折腾，避免在震荡噪音期频繁调仓。
   3) **右侧极端超买阶梯止盈**:
      当进攻标的出现 `bias_20 >= +6.5%`（短期暴涨严重超买）或触发 `crowding_warning == True`（极度拥挤且聪明钱流出）时，不等跌破均线，主动将高波动成长仓位削减 `30% ~ 35%` 并落袋转入纯债（002351）与红利低波（005561），锁住牛市脉冲利润。

3. **回测与实盘算子对齐 7天/30天/180天 真实阶梯赎回费**:
   - 检查 `data_loader.py` 中的 `simulate_execution` 或回测手续费扣减逻辑；
   - 对齐实盘阶梯费率：
     * 持有天数 $< 7$ 天：1.50%（严厉惩罚性费率）；
     * 持有天数 $7 \sim 29$ 天：0.50%（C类或部分指数A类）；
     * 持有天数 $30 \sim 179$ 天：0.50%（A类常规，C类免赎）；
     * 持有天数 $\ge 180$ 天：0.00%（A类免赎）；
   - 确保回测手续费与实盘 `trading_clock_fee.py` 严格对齐，同时保持现有裁判基建与历史测试兼容。

【验收与验证要求】
- 编写或运行相关测试（如 `py -3.11 -m pytest tests/test_strategy_bridge.py tests/test_dynamic_risk_budget_m1.py -v`），确认所有测试通过，无语法错误，无反作弊违规。
- 完成后在你的工作目录输出 `handoff.md`，并通过 `send_message` 向父编排者汇报。
