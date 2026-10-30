## 2026-10-30T04:38:00Z
你是 Milestone 3 评审员 2 (Reviewer M3 Fix 2)。
你的工作目录是：`d:\Google\Workspace\Wind\.agents\teamwork\reviewer_m3_fix2\`。

### MANDATORY INSTRUCTIONS
1. 必须在开始工作前完整阅读用户原始需求：`d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`。
2. 必须深入阅读上一轮 Reviewer 2 否决报告：`d:\Google\Workspace\Wind\.agents\teamwork\reviewer_m3_2\handoff.md`。
3. 必须深入阅读工兵返工交付报告：`d:\Google\Workspace\Wind\.agents\teamwork\worker_m3_fix\handoff.md`。
4. 严禁触碰、修改或解锁系统已设为只读的 4 个裁判基建文件：`judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py`。
5. 严格保持 100% 纯数学因果演绎（No Look-Ahead Bias），零未来函数，零外部大模型 API，零日历硬编码。

### 专项复验目标 (专门复核上一轮否决项是否已彻底修复)
1. **复测 Reviewer 2 变点对抗压力测试套件**:
   在终端运行:
   ```powershell
   py -3.11 d:\Google\Workspace\Wind\.agents\teamwork\reviewer_m3_2\stress_test_cusum.py
   ```
   验证全部 6 项测试（含 `test_instant_risk_meltdown` 与 `test_instant_extreme_crowding`）是否 100% PASS。
2. **复测 C4 档位 011613 进攻底仓保底 (>=25%) 联动断言**:
   在终端运行:
   ```powershell
   cd d:\Google\Workspace\Wind\AGY2_FundAdvisory
   py -3.11 -m pytest tests/test_acceptance_r1_r7.py -k "test_slider_realtime_linkage_mode_a"
   ```
   验证是否 100% PASS，消除原先 19.67% < 25.0% 的报错。
3. **复测 M2 极端行情波动率脉冲防倒挂测试**:
   在终端运行:
   ```powershell
   cd d:\Google\Workspace\Wind\AGY2_FundAdvisory
   py -3.11 -m pytest tests/test_adversarial_m2_challenger.py -k "pulse"
   ```
   验证 011613 在极端脉冲下依然能正常缩减至 <= 20%，底仓平移未发生逻辑反向破坏。
4. **审查前台 UI 与业务流真实贯通**:
   检查 `strategy_bridge.py` 中的 `get_tier_sector_fund_selection` 是否真实调用 `pm.evaluate_track_candidates`，检查 `app_gui.py` 是否真实渲染 `promotion_label` 与 `expert_weights`。
5. 明确给出裁决：APPROVE 或 REQUEST_CHANGES。
6. 编写规范手稿至 `d:\Google\Workspace\Wind\.agents\teamwork\reviewer_m3_fix2\handoff.md`，并通过 `send_message` 向编排器汇报。
