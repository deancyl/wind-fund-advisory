# DISPATCH — Explorer M3 Fix 3 (Test Assertion & Dynamic Weight Compatibility)

## Objective
Investigate and resolve the test assertion failure in `tests/test_acceptance_r1_r7.py` (`test_slider_realtime_linkage_mode_a`).

## Input Files
- d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md
- d:\Google\Workspace\Wind\.agents\teamwork\reviewer_m3_2\handoff.md
- d:\Google\Workspace\Wind\AGY2_FundAdvisory\tests\test_acceptance_r1_r7.py
- d:\Google\Workspace\Wind\AGY2_FundAdvisory\strategy_bridge.py

## Working Directory
d:\Google\Workspace\Wind\.agents\teamwork\explorer_m3_fix3\

## Investigation Focus
1. Analyze why `test_slider_realtime_linkage_mode_a` failed: `assert weights_in_bp["011613"] >= 25.0` vs actual 19.67%.
2. Determine how `StrategyBridge.generate_zero_start_blueprint` computes weights: whether it calls static tier weights or dynamic tier weights, why 011613 was scaled to 19.67%, and what the architectural intention is (C4/C5 aggressive stance vs EWMA scaling).
3. Recommend how to harmonize `generate_zero_start_blueprint` or the test assertion to satisfy both C4/C5 aggressive requirements and EWMA dynamic risk budgeting, while keeping 4 referee files strictly untouched.
4. Output handoff.md with actionable fix strategy.


## 2026-10-30T03:19:33Z
你是 Explorer M3 Fix 3 (测试断言与动态配权兼容性探索专家)。
工作目录：d:\Google\Workspace\Wind\.agents\teamwork\explorer_m3_fix3\

【必读文件】：
- d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md
- d:\Google\Workspace\Wind\.agents\teamwork\reviewer_m3_2\handoff.md
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_m3_fix3\DISPATCH.md
- 审查源码：
  - d:\Google\Workspace\Wind\AGY2_FundAdvisory\tests\test_acceptance_r1_r7.py
  - d:\Google\Workspace\Wind\AGY2_FundAdvisory\strategy_bridge.py
- 4 个只读裁判基建文件（只读不可改）：
  - `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`

【探索目标】：
1. 深入分析 `tests/test_acceptance_r1_r7.py` 中 `test_slider_realtime_linkage_mode_a` 失败原因：
   - 断言：`assert weights_in_bp["011613"] >= 25.0`；
   - 实测：`StrategyBridge.generate_zero_start_blueprint(..., tier="C4")` 中 011613 的权重为 19.67%。
   - 根因分析：在 M2 中引入的 EWMA 波动率风险预算机制，将高波动资产（科创50）的权重根据市场状态/波动率缩放并溢出至纯债，导致静态断言 `>= 25.0%` 不成立。
2. 给出既符合 C4/C5 进攻性原则、又保持 M2 动态 EWMA 风险预算严谨性、且完全通过 `test_acceptance_r1_r7.py` 的兼顾修复方案。
3. 产出具体方案与代码级修复建议，写入 handoff.md。注意：探索员只负责技术勘测与方案设计，严禁修改源代码。完成时向父编排器汇报。
