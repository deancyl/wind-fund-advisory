## 2026-11-08T00:08:56Z
【身份与目录】
你作为团队对抗验证员 1 (teamwork_challenger)。
工作目录：d:\Google\Workspace\Wind\.agents\teamwork\challenger_g9_m2_1
原始需求：d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md（必须首先完整阅读）
项目规划：d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_10\PROJECT.md
工人交付报告：d:\Google\Workspace\Wind\.agents\teamwork\worker_g9_m2\handoff.md

【核心对抗任务】
编写独立探针与对抗测试代码，验证 `PortfolioManager.evaluate_rebalance_audit` 的 Brinson-Fachler 经典模型：
1. **数学恒等式对抗探针**：
   - 构造多种复杂的调仓情景（包含多只同大类基金、跨大类调仓、纯债/黄金/美股QDII混合）；
   - 断言数学恒等式在浮点误差 $10^{-4}$ 内绝对严格成立：
     `abs(allocation_effect_yuan + selection_effect_yuan - total_active_add_yuan) < 1e-4`
     `abs(allocation_effect_pct + selection_effect_pct - total_active_add_pct) < 1e-4`
2. **极端边界对抗探针**：
   - 边界 1：单一资产组合；
   - 边界 2：全现金组合（无任何基金持仓）；
   - 边界 3：新调入标的属于基准完全未持有的大类；
   - 验证以上边界绝不抛出除以零或 KeyError 异常；
3. **原有 7 个顶级键向下兼容性断言**；
4. 给出对抗裁决：**APPROVE** 或 **REQUEST_CHANGES**，写入 handoff.md 并通过 send_message 发送。
