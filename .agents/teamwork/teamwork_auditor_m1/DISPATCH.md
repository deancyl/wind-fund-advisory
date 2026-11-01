## 2026-11-01T13:45:51Z
你是一名法医级完整性审计员（teamwork_auditor）。
你的工作目录是：d:\Google\Workspace\Wind\.agents\teamwork\teamwork_auditor_m1\
你必须严格独立、零容忍地开展完整性审计。严禁修改任何代码。

【审计依据文件】：
1. d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
2. d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_5\PROJECT.md
3. d:\Google\Workspace\Wind\.agents\teamwork\worker_m1_gen2\handoff.md
4. 4 个系统只读裁判文件：
   - AGY2_FundAdvisory/judge_engine.py
   - AGY2_FundAdvisory/holdout_vault.py
   - AGY2_FundAdvisory/AGENT_SPEC.md
   - AGY2_FundAdvisory/tests/test_infra.py
5. AGY2_FundAdvisory/app_gui.py

【审计检查清单（ZERO TOLERANCE）】：
1. **只读裁判底座检查**：
   - 使用 git status 或哈希比对核查 4 个系统只读裁判文件（judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py）是否被修改。任何字节修改均为违规。
2. **反作弊与虚假实现审计**：
   - 静态扫描 `app_gui.py`：检查是否包含任何 `time.sleep`、虚假延时计算（如 `sim_elapsed = max(1.22, ...)`）。
   - 检查是否在前端或测试中包含硬编码字典应付断言（如“限额买500”）。
   - 检查是否有门面实现（Facade）或猴子补丁（Monkeypatch）。
3. **真实性与因果链核验**：
   - 核验数据接口是否真实调用后端 `StrategyBridge` 与 `PortfolioManager`，而非前端假数据伪造。
4. **运行基建测试**：
   - 运行 `cd AGY2_FundAdvisory; py -3.11 -m pytest tests/test_infra.py -c none -v`。
5. 在 `d:\Google\Workspace\Wind\.agents\teamwork\teamwork_auditor_m1\handoff.md` 输出法医审计报告，并在报告末尾给出明确的唯一裁决：
   `VERDICT: CLEAN` 或 `VERDICT: INTEGRITY VIOLATION`（附违规证据）。
6. 完成后通过 send_message 发送完成通知给父 agent。

## 2026-11-01T13:52:14Z
**Context**: 系统重启后恢复执行
**Content**: 服务已恢复。请继续独立开展法医完整性审计（4 个只读裁判文件零改动、零假延迟、零作弊硬编码、真数据调用），将法医审计报告写入 handoff.md 并给出明确的唯一裁决：VERDICT: CLEAN 或 VERDICT: INTEGRITY VIOLATION。
**Action**: 恢复执行并提交法医审计报告。
