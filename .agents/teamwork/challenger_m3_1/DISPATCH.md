# DISPATCH — Challenger M3_1

## Task
Adversarially challenge R6 CUSUM Change-Point Track Champion Dynamic Selection (`CUSUMFundChangePointDetector` in `portfolio_manager.py`).

## Input Files
- d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md
- d:\Google\Workspace\Wind\.agents\teamwork\worker_agent3_m3\handoff.md
- d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py

## Working Directory
d:\Google\Workspace\Wind\.agents\teamwork\challenger_m3_1\

## Verification Requirements
- Create an empirical stress-testing script to verify:
  1. Multi-factor scoring formula: S_{f,t} = 0.35 ER + 0.25 (100 - Fee) + 0.15 Risk + 0.15 SM + 0.10 (100 - TE).
  2. Page's CUSUM score: C_{c,t} = max(0, C_{c,t-1} + (max_f S_{f,t} - S_{c,t}) - k) with slack_k=2.0.
  3. Change-point triggers: C_{c,t} >= 8.0, Risk < 60.0, or extreme crowding.
  4. Auto-promotion logic and badge: "🔄 自进化优选：因综合评分领先，已自动为您优选 {name}".
  5. Same-company +5.0 point convenience bonus correctly added and capped at 100.
- Execute stress tests and verify edge cases.
- Deliver handoff.md with explicit APPROVE or REJECT verdict.

## 2026-10-30T02:55:18Z
你是 Milestone 3 Challenger 1。
工作目录：d:\Google\Workspace\Wind\.agents\teamwork\challenger_m3_1\

【必读文件】：
在开始工作前，必须完整阅读用户原始需求与架构设计：
- d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md
- d:\Google\Workspace\Wind\.agents\teamwork\worker_agent3_m3\handoff.md
- d:\Google\Workspace\Wind\.agents\teamwork\challenger_m3_1\DISPATCH.md
- 审查源码：d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py (重点审查 CUSUMFundChangePointDetector)

【挑战任务与实证验证】：
1. 编写对 CUSUMFundChangePointDetector 的实证对抗压力测试脚本：
   - 检验候选基金竞争力多因子打分公式：S_{f,t} = 0.35 * ER + 0.25 * (100 - Fee) + 0.15 * Risk + 0.15 * SM + 0.10 * (100 - TE)；
   - 检验 Page's CUSUM 衰减得分计算：C_{c,t} = max(0, C_{c,t-1} + (max_f S_{f,t} - S_{c,t}) - k)；
   - 检验结构性衰减变点触发条件：C_{c,t} >= 8.0、Risk < 60.0、极度拥挤度预警；
   - 检验冠军自动优胜劣汰晋升与“🔄 自进化优选：因综合评分领先，已自动为您优选 {champion_name}”标签；
   - 检验同基金公司 T+1 SWITCH 转换便利度加分 (+5.0分，上限 100)；
2. 运行对抗测试与边界网格扫描，确保极端输入下零崩溃、零除零、零状态机错乱。
3. 结果交付：在工作目录写入 handoff.md，包含清晰的 Observation, Logic Chain, Caveats, Conclusion (明确 APPROVE 或 REJECT), Verification Method。完成时向父编排器发送消息汇报。

## 2026-10-30T03:05:38Z
账号配额已轮换恢复，请继续执行挑战验证任务并完成 handoff.md 交付。
