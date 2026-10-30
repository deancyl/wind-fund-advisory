# BRIEFING — 2026-10-30T03:32:00Z

## Mission
深入探索 test_acceptance_r1_r7.py 中 test_slider_realtime_linkage_mode_a 断言失败原因，梳理 C4/C5 进攻性与 M2 EWMA 动态风险预算的机制与兼容方案，输出兼顾两者的技术方案与代码级修复建议。

## 🔒 My Identity
- Archetype: explorer
- Roles: [explorer, synthesizer]
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_m3_fix3
- Original parent: 7eb668ae-6843-4834-9b3d-3455ac86af88
- Milestone: M3 Fix 3

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- 严禁修改 4 个裁判基建文件 (judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py)
- 只负责技术勘测与方案设计，严禁修改源代码
- 产出分析报告 handoff.md 写入自身工作目录并通过 send_message 向编排器汇报

## Current Parent
- Conversation ID: 7eb668ae-6843-4834-9b3d-3455ac86af88
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `tests/test_acceptance_r1_r7.py` (line 52-116: test_slider_realtime_linkage_mode_a)
  - `strategy_bridge.py` (lines 135-146: FUND_TO_PROXY_INDEX; lines 252-300: TIER_TARGET_WEIGHTS; lines 3317-3649: compute_dynamic_tier_weights; lines 3860-3960: generate_zero_start_blueprint)
  - `data_loader.py` (compute_ewma_volatility_and_correlation, STAR50_STITCH vol=0.3727)
  - `tests/test_adversarial_m2_challenger.py` (lines 62-85: test_adv_ewma_volatility_pulse_budget_transfer, line 73: assert w_pulse_c4["011613"] <= 0.20)
  - `tests/test_architecture_m3.py` (lines 250-300: monotonicity C1 < C2 < C3 < C4 < C5)
  - `tests/test_m2_r4_r5_optimization.py` (lines 85-92: w_stress C4 pure bond transfer)
  - Git commit history (`c0cdb4e` vs `db2c31b`)
- **Key findings**:
  1. 根因链条完整闭环：在 M2 中，`generate_zero_start_blueprint` 接入 `compute_dynamic_tier_weights`。由于科创50（STAR50_STITCH）日常内生 EWMA 波动率为 37.27%，在 Step 4 遭遇 `0.18 / vol = 0.483` 统一基准缩放（从 30% 砍至 14.49%）。随后 Step 6 为守住 C4 权益下限（77%），执行全局统一等比放大（1.3575x）。由于低波品种 100032（富国红利）Step 4 未被削减，被等比推高至 32.58%，而科创50仅回升至 19.67%。这不仅导致测试断言 `>= 25.0%` 失败，且导致 C4“成长进攻型”最大持仓畸形变为红利股。
  2. 对抗性红线探测：`test_adversarial_m2_challenger.py:73` 严格断言在极端脉冲冲击（`df_pulse` 波动率 > 45%）下，C4 中 011613 必须缩减至 `<= 0.20`。因此，绝不能在 `compute_dynamic_tier_weights` 中无条件硬编码 `>= 0.25`，否则会直接击穿 M2 既有红队对抗用例。
  3. 兼容修复方案：在 `generate_zero_start_blueprint`（建仓蓝图引擎）中，沿用 lines 3889-3896 现有的 C2/C3 SPX 兜底保护范式，为 C4/C5 进攻档位注入进攻底仓保护（若 011613 < 0.25，则从因等比缩放虚高的 100032 调回差额预算至 25.0%）。既保证极端脉冲下 `compute_dynamic_tier_weights` 纯正的 EWMA 风险预算机制与 `<0.20` 测试通过，又保证从 0 建仓蓝图满足 C4 进攻性定义与 `test_acceptance_r1_r7.py` 的 `>= 25.0%` 断言，同时 100% 保持权益单调性与资金守恒。
- **Unexplored areas**: None (勘测全面完成)

## Key Decisions Made
- 确立“蓝图层保底回归 + 动态层纯正保留”的双轨兼容架构，杜绝单边修改导致对抗用例反向报错。

## Artifact Index
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_m3_fix3\DISPATCH.md — 派发指令与任务目标
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_m3_fix3\BRIEFING.md — 持续认知与工作记忆
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_m3_fix3\handoff.md — 5-Component 深度探索与方案报告
