# DISPATCH — Explorer M3 Fix 2 (CUSUM Meltdown Candidate Disqualification)

## Objective
Investigate and design fix for `CUSUMFundChangePointDetector.evaluate_track_candidates` when default champion triggers meltdown (`risk < 60.0` or `extreme_crowding`).

## Input Files
- d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md
- d:\Google\Workspace\Wind\.agents\teamwork\reviewer_m3_2\handoff.md
- d:\Google\Workspace\Wind\.agents\teamwork\reviewer_m3_2\stress_test_cusum.py
- d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py

## Working Directory
d:\Google\Workspace\Wind\.agents\teamwork\explorer_m3_fix2\

## Investigation Focus
1. Analyze why Reviewer 2's `stress_test_cusum.py` failed: when default champion triggers meltdown, if its historical multi-factor score is still highest, `evaluate_track_candidates` did not exclude it from candidate pool, causing `is_promoted = False` and returning the meltdown fund.
2. Design the precise algorithmic logic to disqualify the meltdown fund from recommendation, promote the best remaining alternative candidate, and set `is_promoted = True`.
3. Verify edge cases (e.g., if all candidates are meltdown, or only 1 candidate).
4. Output handoff.md with concrete fix recommendations.


## 2026-10-30T03:19:25Z
你是 Explorer M3 Fix 2 (CUSUM 暴雷熔断风控探索专家)。
工作目录：d:\Google\Workspace\Wind\.agents\teamwork\explorer_m3_fix2\

【必读文件】：
- d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md
- d:\Google\Workspace\Wind\.agents\teamwork\reviewer_m3_2\handoff.md
- d:\Google\Workspace\Wind\.agents\teamwork\reviewer_m3_2\stress_test_cusum.py
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_m3_fix2\DISPATCH.md
- 审查源码：d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py (重点分析 CUSUMFundChangePointDetector.evaluate_track_candidates)

【探索目标】：
1. 深入分析 Reviewer 2 编写的 `stress_test_cusum.py` 失败根因：当默认冠军标的触发排雷熔断（`champ_risk < 60.0`）或极度拥挤（`champ_extreme_crowding == True`）时，若其历史多因子总分依然最高，`evaluate_track_candidates` 因未将默认标的从候选池剔除，导致 `is_promoted = False` 且依然推荐暴雷标的。
2. 设计精确的风控剔除与替代晋升算法：
   - 触发排雷熔断或极度拥挤时，必须立即剥夺默认标的推荐资格；
   - 候选池必须排除该默认标的，从其余合格备选标的中挑选最高分者晋升；
   - 设定 `is_promoted = True` 并生成合规标签。
3. 产出具体修复建议与代码级方案，写入 handoff.md。注意：探索员只负责技术勘测与方案设计，严禁修改源代码。完成时向父编排器汇报。
