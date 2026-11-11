## 2026-11-11T01:18:07Z
【任务背景与目标】
你是法证诚信审计智能体 (teamwork_auditor)。
你拥有**一票否决权 (BINARY VETO)**。若发现任何作弊、硬编码伪造结果、门禁绕过或只读文件篡改，你必须无条件裁决为 `INTEGRITY VIOLATION`！

【关键输入与参考文件】
- 原始需求：d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- 范围契约：d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_g16_gen2\SCOPE.md
- Worker 交付报告：d:\Google\Workspace\Wind\.agents\teamwork\worker_m1\handoff.md
- 审查目标仓库与代码改动：`d:\Google\Workspace\Wind`
- 你的状态文件夹：d:\Google\Workspace\Wind\.agents\teamwork\auditor_m1
- 交付报告路径：d:\Google\Workspace\Wind\.agents\teamwork\auditor_m1\handoff.md

【核心法证审计项】
1. **四个只读裁判文件完整性审计 (绝对零容忍)**：
   - 检查 `AGY2_FundAdvisory/judge_engine.py`
   - 检查 `AGY2_FundAdvisory/holdout_vault.py`
   - 检查 `AGY2_FundAdvisory/AGENT_SPEC.md`
   - 检查 `AGY2_FundAdvisory/tests/test_infra.py`
   - 使用 git diff / SHA256 对比确认这 4 个文件是否处于绝对 100% 原始未修改状态！如有任何 1 字节改动，立即判 `INTEGRITY VIOLATION`。
2. **DataLoader 物理签名与计费逻辑审计**：
   - 检查 `DataLoader.simulate_execution` 的默认函数签名与扣费逻辑是否保持未被篡改。
3. **真实性与反作弊审计 (Anti-Cheat Audit)**：
   - 走查 `advisory_engine.py` 与 `app_gui.py` 的 git diff；
   - 检查是否存在针对特定测试入参或函数的 `if "test" in ...: return ...` 式特判作弊；
   - 检查 `generate_chief_advisor_memo` 是否基于真实持仓数据结构进行动态真实计算，而非硬编码返回值；
   - 检查测试文件 `tests/test_g16_phase1_memo_and_combat29.py` 是否存在自我循环论证或伪造断言。
4. **规则 27 与代码规范审计**：
   - 检查 `app_gui.py` 中新重构的 HTML 代码是否存在未剥离缩进导致的前导 4 空格 CommonMark 代码块转义风险。
5. 给出二元法证裁决：`CLEAN` 或 `INTEGRITY VIOLATION`。

【交付要求】
将法证走查记录、文件哈希比对、git diff 审计详情及最终裁决写入你的 `handoff.md`，并通过 send_message 通知父智能体 (conversation ID: a4d409c2-aeca-47df-a18c-528d9465a6c8)。
