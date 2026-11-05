# DISPATCH - Forensic Auditor M2 (Integrity Verification & Referee Lock)
- Task: Verify SHA-256 hashes of referee files and audit app_gui.py for any fake constants or cheating
- Working directory: .agents/teamwork/auditor_m2/
- Original request: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- Scope document: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md
- Worker handoff: d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_m2\handoff.md

## 2026-11-04T11:46:48Z
你作为独立司法鉴证审计员（Forensic Auditor M2），对 Milestone 2 的交付代码执行零容忍的合规与完整性审计（Forensic Integrity Audit）。

【一票否决权铁律（HARD VETO）】
你的审计结论具有一票否决权。若发现作弊、硬编码伪造数据、篡改裁判文件、或创建欺骗性假实现的任何行为，必须无条件出具 INTEGRITY VIOLATION 裁决，里程碑立即失败。

【必须阅读的上下文文件】
1. 原始需求文件：d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
2. 架构与里程碑规范：d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md
3. 工作区准则：d:\Google\Workspace\Wind\GEMINI.md
4. Worker 交付报告：d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_m2\handoff.md
5. 目标实现文件：d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py

【你的工作目录】
d:\Google\Workspace\Wind\.agents\teamwork\auditor_m2\
请在你的工作目录下维护 BRIEFING.md、progress.md，并在完成审查后输出 handoff.md。

【审计检验项】
1. **裁判文件物理防篡改审计**：
   计算以下 5 个文件的 SHA-256 哈希值，必须与基准值 100% 吻合：
   - `AGY2_FundAdvisory/judge_engine.py`: `76f930371176de7ee6a413174b030101e3210ac6e037f5d10fe229af31cc07be`
   - `AGY2_FundAdvisory/holdout_vault.py`: `88122eaf647040a410e2fd95da81077db10149a498a47340ff40b670bd031d2a`
   - `AGY2_FundAdvisory/AGENT_SPEC.md`: `a346586f9bd2dc0ee83e665bd18e7a6471464c9f7b658e392b989b800cd63957`
   - `tests/test_infra.py`: `48bee0da300d7c0a0848ec1376e4b9b2e55224d2736081713b4340f0362cd100`
   - `AGY2_FundAdvisory/tests/test_infra.py`: `b8d781be8135be05cf61e62e4b534e359985ad880f27ffb61228a33df6b02a6a`
2. **源码完整性与作弊排查**：
   - 检查 `AGY2_FundAdvisory/app_gui.py` 是否存在针对测试用例的特判作弊（例如针对测试断言写死固定返回值、mock bypass）。
   - 检查是否有重新引入 `3210 / 1780` 或 `INDEX_PE_METAS` 假常数的违规行为。
   - 检查工作区纯净性：确认未触碰全局 `c:\Users\deanc\.gemini\GEMINI.md`。
3. 在 handoff.md 中明确给出 Verdict：CLEAN 或 INTEGRITY VIOLATION，并使用 send_message 向 orchestrator (c98181d5-8d61-4839-8d62-5dbcef7c85af) 发送完成通知。
