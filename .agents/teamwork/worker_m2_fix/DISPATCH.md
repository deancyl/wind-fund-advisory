## 2026-11-11T02:11:00Z
【任务背景与目标】
你是具有高可靠全栈开发能力的执行智能体 (teamwork_worker)。
当前任务：Milestone 2 门禁缺陷修复 (Remediation) —— 修复 `app_gui.py` 手机极简模式 Card 3/Card 4 尾仓清扫判定规则，与 `advisory_engine.py` 完全对齐，消除对腰部持仓 `005827 易方达蓝筹` (¥124.14) 的误卷入，使手机模式全屏统一锁定 19 只免赎碎片与 ¥442.70 平账！

【强制诚信警告 (MANDATORY INTEGRITY WARNING)】
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

【关键输入与参考文件】
- 原始需求：d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- 审查员反馈报告：d:\Google\Workspace\Wind\.agents\teamwork\reviewer_m2_1\handoff.md
- 独占所有权文件：`d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py`
- 状态文件夹：d:\Google\Workspace\Wind\.agents\teamwork\worker_m2_fix
- 交付报告路径：d:\Google\Workspace\Wind\.agents\teamwork\worker_m2_fix\handoff.md

【精准修改要求】
1. **`app_gui.py` 第 3003~3015 行附近**：
   在手机模式 Card 3 扫描 `tail_items` 时，将原本粗暴的 `0 < mv_h < 200.0 and min_d >= 30` 替换为与 `advisory_engine.py`（以及 ActiveRiskSentry 维度 13）严格对齐的判定规则：
   ```python
   tail_items = []
   if pm.holdings:
       for fc, h in pm.holdings.items():
           mv_h = getattr(h, "shares", 0.0) * getattr(h, "current_nav", 1.0)
           s_cls = getattr(h, "share_class", "A")
           fname = getattr(h, "fund_name", fc)
           min_d = min((getattr(b, "holding_days", 30) for b in getattr(h, "batches", [])), default=getattr(h, "holding_days", 30))
           is_tail = (0 < mv_h < 100.0) or (100.0 <= mv_h < 200.0 and (s_cls == "C" or any(k in fname for k in ["联接", "ETF", "指数", "红包", "体验", "尾仓", "碎片"])))
           is_fee_free = (s_cls == "C" and min_d >= 30) or (s_cls != "C" and min_d >= 365)
           if is_tail and is_fee_free:
               tail_items.append((fc, fname, mv_h, min_d))
   ```
   实测确认：在 `combat_29_funds` 下，`005827 易方达蓝筹`（¥124.14，A类，浮亏 -¥27.28）被正确保留在持仓中不被卖出，Card 3 与 Card 4 准确展示 **19 只免赎碎片（合计资金 ¥442.70）**，与正上方的 Card 2 达到 100% 完美平账与同屏一致！

2. **更新测试用例 `tests/test_m2_features.py`**：
   在测试中增加对手机模式扫描 `tail_items` 的数值断言：
   - 断言 `combat_29_funds` 账本下扫出的免赎尾仓数量严格为 19；
   - 断言总金额严格等于 442.70；
   - 断言 `005827` 不在清扫列表中。

3. **运行回归测试并确保 100% 绿灯**：
   - `pytest tests/test_m2_features.py`
   - `pytest tests/test_infra.py`
   - 确认四个只读裁判文件零改动。

【交付要求】
将修改详情、测试执行命令与输出写入 `d:\Google\Workspace\Wind\.agents\teamwork\worker_m2_fix\handoff.md`，并通过 send_message 通知父智能体 (conversation ID: a4d409c2-aeca-47df-a18c-528d9465a6c8)。
