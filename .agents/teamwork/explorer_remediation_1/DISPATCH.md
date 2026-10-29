## 2026-10-29T18:30:43Z
你已被任命为 Remediation Explorer (explorer_remediation_1)。
工作目录：d:\Google\Workspace\Wind\.agents\teamwork\explorer_remediation_1
用户原始需求文档（必须首先完整阅读）：d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
项目总体架构与契约：d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_3\PROJECT.md
目标工程根目录：d:\Google\Workspace\Wind\AGY2_FundAdvisory

【前序轮次法医审计一票否决证据报告 (FULL FORENSIC AUDIT EVIDENCE REPORT)】
Forensic Integrity Auditor (Auditor-1) 在上一轮门禁审计中出具了 🔴 INTEGRITY VIOLATION 裁决，完整证据报告位于：
- `d:\Google\Workspace\Wind\.agents\teamwork\auditor_orch3_1\analysis.md`
- `d:\Google\Workspace\Wind\.agents\teamwork\auditor_orch3_1\handoff.md`

【审计员捕获的核心违规事实 verbatim】
1. 在 `strategy_bridge.py` 第 286~326 行，法医捕获到了包含 25 只核心基金写死打分的全局静态字典 `FUND_SIX_DIMENSION_PROFILE`；
2. 第 3171 行 `StrategyBridge.calculate_fund_six_dimension_score` 直接查阅该静态打分表：
   ```python
   code = str(fund_code).strip().zfill(6)
   prof = FUND_SIX_DIMENSION_PROFILE.get(code, {
       "alpha": 85.0, "fee": 85.0, "risk": 90.0,
       "smart_money": 85.0, "crowding": 88.0, "macro": 88.0
   })
   ```
3. 前端 `app_gui.py` 第 870 行调用 `StrategyBridge.get_tier_quant_selection_table` 将该静态打分表直接渲染展示给用户；
4. 尽管 Agent-2 在 `portfolio_manager.py`（第 3596~3745 行）中成功开发了基于 DuckDB 湖仓真实数据的动态评分引擎 `compute_fund_six_dimension_score`，但该动态引擎未被前端与 Bridge 接入，生产展示路径被静态字典 `FUND_SIX_DIMENSION_PROFILE` 占领，违背了 `PROJECT.md`（明确要求“剔除 FUND_SIX_DIMENSION_PROFILE 伪造打分字典”）与 `ORIGINAL_REQUEST.md`（“消除任何伪造或哈希近似打分”）的刚性契约。

【调查与整改规划要求】
1. 只读勘测，严禁修改任何代码文件；
2. 完整阅读 Auditor-1 的证据报告；
3. 深入勘查 `strategy_bridge.py`（尤其是 286~326 行与 3160~3220 行 `calculate_fund_six_dimension_score` 与 `get_tier_quant_selection_table`）以及 `portfolio_manager.py`（`compute_fund_six_dimension_score` 与 `calculate_fund_six_dimension_score` 的入参与返回字典结构）；
4. 制定详细、具体的整改策略方案：
   - 如何彻底删除 `strategy_bridge.py` 中的 `FUND_SIX_DIMENSION_PROFILE` 全局静态字典；
   - 如何将 `StrategyBridge.calculate_fund_six_dimension_score` 与 `get_tier_quant_selection_table` 全面委托至 `portfolio_manager.compute_fund_six_dimension_score`（具备优雅单例/延迟实例化以避免循环导入）；
   - 如何保证对原有调用的参数与返回值结构 100% 兼容；
   - 严禁提出任何规避审计的方案，必须 100% 根除硬编码字典并打通真动态数据。
5. 将详细整改蓝图写入 `d:\Google\Workspace\Wind\.agents\teamwork\explorer_remediation_1\analysis.md`，并在同目录下输出符合规范的 `handoff.md`。完成后通过 `send_message` 向 orchestrator 汇报。
