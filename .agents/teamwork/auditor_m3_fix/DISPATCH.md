## 2026-10-30T04:38:19Z
你是法医级防作弊审计专家 (Forensic Integrity Auditor M3 Fix)。
你的工作目录是：`d:\Google\Workspace\Wind\.agents\teamwork\auditor_m3_fix\`。

### MANDATORY INSTRUCTIONS
1. 必须在开始工作前完整阅读用户原始需求：`d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`。
2. 必须深入阅读工兵交付报告：`d:\Google\Workspace\Wind\.agents\teamwork\worker_m3_fix\handoff.md`。
3. 严禁触碰、修改或解锁系统已设为只读的 4 个裁判基建文件：`judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py`。
4. 严格保持 100% 纯数学因果演绎（No Look-Ahead Bias），零未来函数，零外部大模型 API，零日历硬编码。

### 法医级独立取证审计项目 (全面核查本次返工的所有修改)
1. **基石文件物理哈希校验 (SHA256)**:
   使用 PowerShell 计算并核实 4 个裁判基建文件的哈希值，断言其未发生任何单字节改动：
   - `judge_engine.py`
   - `holdout_vault.py`
   - `AGENT_SPEC.md`
   - `tests/test_infra.py`
2. **防作弊与真实验证审查**:
   - 审查 `portfolio_manager.py`、`strategy_bridge.py`、`app_gui.py`、`tests/test_adversarial_m3_challenger1.py` 的 Git Diff；
   - 严查是否存在针对测试用例输入（如特定测试基金代码、特定期望浮点数）的硬编码 mock 短路分支；
   - 严查是否存在 `sys.modules` 篡改、未来时间戳穿越（Look-Ahead Bias）、外部大模型 API 调用或日历特征硬编码；
   - 验证 CUSUM 衰减累积公式（$C_{c,t} = \max(0, C_{c,t-1} + (\max S_{f,t} - S_{c,t}) - k)$）是否完全真实计算并由数学驱动；
   - 验证 C4/C5 进攻底仓调回保护是否纯粹由资金守恒与档位风险单调性数学公式推导，无伪造作弊。
3. **独立运行基线验证**:
   在终端运行：
   ```powershell
   cd d:\Google\Workspace\Wind\AGY2_FundAdvisory
   py -3.11 -m pytest tests/test_architecture_m3.py tests/test_adversarial_m3_challenger1.py
   ```
4. 明确给出审计裁决：CLEAN 或 INTEGRITY VIOLATION。
5. 编写法医级独立审计报告至 `d:\Google\Workspace\Wind\.agents\teamwork\auditor_m3_fix\handoff.md`，并通过 `send_message` 向编排器汇报。
