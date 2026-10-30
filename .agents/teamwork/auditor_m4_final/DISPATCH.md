# DISPATCH — Forensic Auditor M4 Final

## Objective
对 AGY2_FundAdvisory 项目全部代码与交付成果进行最严格的独立法医反作弊审计（Integrity Forensics）：
1. 绝对红线校验：4 个系统只读裁判基石文件物理 SHA256 哈希必须比特级保持一致，`git diff` 严格 0 字节：
   - `judge_engine.py`: `76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF31CC07BE`
   - `holdout_vault.py`: `88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670BD031D2A`
   - `AGENT_SPEC.md`: `A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B800CD63957`
   - `tests/test_infra.py`: `B8D781BE8135BE05CF61E62E4B534E359985AD880F27FFB61228A33DF6B02A6A`
2. 零外部 API 校验：代码库中严禁引入任何外部大模型 API（OpenAI, Anthropic, Qwen 等网络调用），100% 纯本地数学因果演绎。
3. 零日历硬编码校验：全代码库进行 AST 检查，严禁硬编码未来日期/特定月份行情判断，杜绝时间偏误。
4. 零未来函数与无偏校验：检查滑动窗口、EWMA、Hedge 在线权重、Schmidt 滞后环、CUSUM 检测器是否严格满足因果递推（No Look-Ahead Bias）。
5. 真实有效性校验：严禁 hardcode 测试期望返回值，严禁 dummy/facade 欺骗实现。

## Mandatory Inputs (MUST READ FIRST)
- Original Request: `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`
- Master Project Architecture: `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md`
- Worker Handoff Report: `d:\Google\Workspace\Wind\.agents\teamwork\worker_m4_final\handoff.md`

## Output Requirements
审计完成后，在你的工作目录 `d:\Google\Workspace\Wind\.agents\teamwork\auditor_m4_final\` 下生成 `handoff.md`，并在末尾给出明确判定：
`Verdict: CLEAN` 或 `Verdict: INTEGRITY VIOLATION (证据详情)`。
并通过 `send_message` 将结论通知编排器。

## 2026-10-30T07:10:03Z
Received task:
You are Forensic Integrity Auditor M4 Final. Your working directory is d:\Google\Workspace\Wind\.agents\teamwork\auditor_m4_final\.
Your role is to perform strict, independent forensic integrity verification on AGY2_FundAdvisory project.
MANDATORY INSTRUCTIONS:
1. First, read d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md.
2. Read d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md.
3. Read the worker handoff report at d:\Google\Workspace\Wind\.agents\teamwork\worker_m4_final\handoff.md.
4. Read d:\Google\Workspace\Wind\.agents\teamwork\auditor_m4_final\DISPATCH.md.
YOUR AUDIT MUST RIGOROUSLY CHECK:
1. Physical SHA-256 Invariant
2. Zero external LLM API calls
3. Zero calendar hardcoding
4. Zero Look-Ahead Bias
5. No fake implementations or dummy test facades
Verdict: CLEAN or Verdict: INTEGRITY VIOLATION (evidence)
