# DISPATCH — Explorer M3 Fix 1 (CUSUM Front-End Wiring)

## Objective
Investigate how to end-to-end connect `CUSUMFundChangePointDetector` into `strategy_bridge.py` and `app_gui.py`.

## Input Files
- d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md
- d:\Google\Workspace\Wind\.agents\teamwork\reviewer_m3_2\handoff.md
- d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py
- d:\Google\Workspace\Wind\AGY2_FundAdvisory\strategy_bridge.py
- d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py

## Working Directory
d:\Google\Workspace\Wind\.agents\teamwork\explorer_m3_fix1\

## Investigation Focus
1. How `get_tier_sector_fund_selection` in `strategy_bridge.py` can call `pm.evaluate_track_candidates` or `pm.cusum_detector` to dynamically replace decaying champions with auto-promoted champions.
2. How `app_gui.py` Step 1 white-box funnel panel can check if a track champion was auto-promoted and display the required label `🔄 自进化优选：因综合评分领先，已自动为您优选 {champion_name}`.
3. Ensure no static facade, 100% causal deduction, and seamless UI linkage.
4. Output handoff.md with concrete fix architecture and code-level recommendations.

## 2026-10-30T03:19:16Z
你是 Explorer M3 Fix 1 (CUSUM 前台与业务流贯通探索专家)。
工作目录：d:\Google\Workspace\Wind\.agents\teamwork\explorer_m3_fix1\

【必读文件】：
- d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md
- d:\Google\Workspace\Wind\.agents\teamwork\reviewer_m3_2\handoff.md
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_m3_fix1\DISPATCH.md
- 审查源码：
  - d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py
  - d:\Google\Workspace\Wind\AGY2_FundAdvisory\strategy_bridge.py
  - d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py

【探索目标】：
1. 深入分析 Reviewer 2 提出的核心阻塞项：`CUSUMFundChangePointDetector` 在 `portfolio_manager.py` 虽已实现，但在 `strategy_bridge.py` 与 `app_gui.py` 中 0 调用，导致前台未贯通。
2. 给出端到端贯通方案：
   - `strategy_bridge.py` 中 `get_tier_sector_fund_selection` 如何与 `pm.evaluate_track_candidates` 联动；
   - `app_gui.py` Step 1 白盒面板如何检测变点触发并真实渲染标签 `🔄 自进化优选：因综合评分领先，已自动为您优选 {champion_name}`，并更新推荐标的与替换下拉框。
3. 产出具体的修复架构与代码级伪代码方案，写入 handoff.md。注意：探索员只负责技术勘测与方案设计，严禁修改源代码。完成时向父编排器汇报。
