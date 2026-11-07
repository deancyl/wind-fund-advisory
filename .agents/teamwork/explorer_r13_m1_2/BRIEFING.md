# BRIEFING — 2026-11-07T14:17:45Z

## Mission
Formulate exact implementation plan and production-ready code design for Milestone 1: Target Volatility Risk Control and Dividend Cash Rebalancing.

## 🔒 My Identity
- Archetype: explorer
- Roles: investigation, synthesis
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_r13_m1_2\
- Original parent: 970e6279-6781-4b89-b765-9b8036125fe8
- Milestone: Milestone 1 (Target Volatility Risk Control & Dividend Cash Rebalancing)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement directly in source code.
- Zero modification to four referee files: judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py.
- DataLoader.simulate_execution signature and fee rules MUST NOT be modified.
- Zero violation of <7 days 1.50% penalty fee.
- FIFO batch integrity.
- Weights must strictly normalize to 1.000000.
- All messages in Chinese.

## Current Parent
- Conversation ID: 970e6279-6781-4b89-b765-9b8036125fe8
- Updated: 2026-11-07T14:17:45Z

## Investigation State
- **Explored paths**:
  * `AGY2_FundAdvisory/portfolio_optimizer.py` (Line 215-260, 1420-1600)
  * `AGY2_FundAdvisory/portfolio_manager.py` (Line 240-300, 2375-2420, 2568-2620, 7730-7790, 8163-8350)
  * `AGY2_FundAdvisory/advisory_engine.py` (Line 1260-1410)
  * `AGY2_FundAdvisory/strategy_bridge.py` (Line 6115-6150, 6470-6500)
  * `AGY2_FundAdvisory/app_gui.py` (Tab 1 Line 2684-2750, Tab 2 Line 4008-4150, 5070-5150, 5300-5400)
  * `tests/test_g3_evolution_loop.py` & `tests/test_infra.py`
- **Key findings**:
  1. `TARGET_VOLATILITY_BY_TIER` (C1: 0.05, C2: 0.08, C3: 0.12, C4: 0.16, C5: 0.22) strictly corresponds to C1~C5 risk profiles.
  2. `SmartExecutionDCAEngine.get_fund_real_volatility_and_bias`穿透本地 Parquet 湖仓，可提供真实的 20 日年化波动率。
  3. `apply_target_volatility_risk_control` 可优雅地在超标时计算压降比例，将高波资产平移至纯债 `002351` 并将权重严密归一化为 1.000000。
  4. 公募基金个人股息免征所得税（0%）。持有期 $\ge 365$ 天的红利基金若通过现金分红再配置，可省去 0.50% 赎回费与 0.20% T+2 在途损耗（合计 0.70%），且不重置 7 天惩罚锁定期。
  5. 全量自动化测试 50 项已验证 100% 通过；4 个裁判文件保持洁净零修改。
- **Unexplored areas**: None for M1-2 scope.

## Key Decisions Made
- `portfolio_optimizer.py`: 采用加权年化波动率保守上界作为触发器，兼顾离线确定性与对高波资产的直接约束；输出结构包含 `reduction_plan`、`transfer_target` 与 `adjusted_weights`。
- `portfolio_manager.py`: 采用 `DIVIDEND_YIELD_MAP` 标准基线（100032: 5.2%, 005561: 5.5%, 002351: 2.6% 等），精准核算 0.50% 免赎收益与 0.20% 免在途收益，同时支持独立函数与实例方法。
- 实施代码与测试用例完全设计就绪，写于 `report.md` 与 `handoff.md`。

## Artifact Index
- `DISPATCH.md` — 调度指令记录
- `progress.md` — 执行进度心跳追踪
- `BRIEFING.md` — 态势感知工作记忆
- `report.md` — 详细技术方案与完整实现源码
- `handoff.md` — 5-部分自包含交接报告
