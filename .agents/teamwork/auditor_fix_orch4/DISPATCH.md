## 2026-10-31T16:28:44Z
你是 auditor_fix_orch4 (Final Forensic Integrity Auditor)。
你的工作目录是: d:\Google\Workspace\Wind\.agents\teamwork\auditor_fix_orch4
原始需求文件路径 (必读): d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
项目工程蓝图: d:\Google\Workspace\Wind\PROJECT.md
整改专员交付报告: d:\Google\Workspace\Wind\.agents\teamwork\worker_remediation_orch4\handoff.md
代码项目根目录: d:\Google\Workspace\Wind\AGY2_FundAdvisory

【核心任务】
作为最终法医级完整性审计员（Forensic Auditor），在整改完成后对整个代码库进行最终的防作弊审查：
1. 必须首先阅读 `ORIGINAL_REQUEST.md`，执行零容忍法医核验。
2. 裁判基建物理完整性终审（Zero-Modification Line）：
   - 核验 4 个系统只读裁判文件：
     - `AGY2_FundAdvisory/judge_engine.py`
     - `AGY2_FundAdvisory/holdout_vault.py`
     - `AGY2_FundAdvisory/AGENT_SPEC.md`
     - `AGY2_FundAdvisory/tests/test_infra.py`
   - 使用 git status 与 hash 对比，断言 4 个文件绝对 0 变动、0 字节修改、0 写入。
3. 反作弊终审核验：
   - 确认整改后的 `portfolio_manager.py` 中彻底不存在 `baseline_dict`，SQLite 初始化不包含任何今日伪造缓存；
   - 确认核心代码中 0 处 `time.sleep`，0 处 2018~2025 日历年份作弊；
   - 确认前端 0 猴子补丁，核心业务 0 假数据字典应付测试；
   - 确认所有 8 大算法（配额缓存、瀑布拆单、QDII估值纠偏、100%动态权重、三段式攻防、适宜度四维判定、双模式推演精算、双红利协同豁免）均为真实内生计算。
4. 运行裁判基建与全量测试套件：
   `py -3.11 -m pytest tests/test_infra.py tests/test_milestone_phase1_r1_r5.py -v`
5. 将终审法医证据与最终裁决（Verdict: CLEAN 或 INTEGRITY_VIOLATION）写入你的工作目录下的 `handoff.md`。
⚠️ 享有一票否决权（BINARY VETO）。完成后通过 send_message 向父编排者汇报。
