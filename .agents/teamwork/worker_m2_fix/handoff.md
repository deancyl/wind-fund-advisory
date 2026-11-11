# Milestone 2 门禁缺陷修复 (Remediation) 交付报告 (Handoff Report)

## 1. Observation (客观实地走查与证据链)

根据调度单与审查员反馈报告 (`reviewer_m2_1/handoff.md`)，对 `AGY2_FundAdvisory/app_gui.py` 手机极简模式 Card 3/Card 4 尾仓清扫判定规则进行了针对性修正与端到端实证验证：

1. **缺陷根因走查**：
   - 走查位置：`AGY2_FundAdvisory/app_gui.py` 原第 3003~3013 行。
   - 原始逻辑：仅通过 `0 < mv_h < 200.0 and min_d >= 30` 粗筛。
   - 产生问题：在 `combat_29_funds` 实战账本中，第 10 号持仓 `005827 易方达蓝筹精选混合`（市值 ¥124.14，份额类别 A 类，持仓天数 1041 天，浮亏 -¥27.28）属于用户的“3 只腰部核心主动持仓”之一，因市值落入 100~200 元且持有天数 > 30 天，被错误卷入尾仓清扫列表。
   - 导致 Card 2 显示 `🧹 19只碎片(¥442.70)`，而 Card 3/Card 4 却显示 `20 只免赎碎片 (¥566.84)`，界面存在同屏矛盾。

2. **代码修改实录**：
   - 文件：`AGY2_FundAdvisory/app_gui.py` 第 3003~3015 行。
   - 将扫描规则完全对齐 `advisory_engine.py`（以及 ActiveRiskSentry 维度 13）：
     ```python
     # c) 卡片 3：🧹 碎片尾仓一键清扫卡
     # 动态扫描持仓中的免赎碎片尾仓（与 advisory_engine.py 及 ActiveRiskSentry 维度13 严格对齐）
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
     
     t_count = len(tail_items)
     t_cash = sum(x[2] for x in tail_items)
     ```

3. **测试用例扩充实录**：
   - 文件：`tests/test_m2_features.py`。
   - 在 `test_app_gui_source_code_integrity` 中追加对该严密过滤 AST/正则特征的核验。
   - 新增独立测试函数 `test_mobile_tail_sweep_rule_and_combat29_alignment()`：
     - 断言 `combat_29_funds` 账本下扫出的免赎尾仓数量严格为 19；
     - 断言总金额严格等于 442.70；
     - 断言 `005827` 绝不在清扫列表中。

4. **自动化测试执行结果**：
   - 执行命令：`py -3 -m pytest tests/test_m2_features.py -v`
     输出：`6 passed, 31 warnings in 43.88s` (100% PASS)。
   - 执行命令：`py -3 -m pytest tests/test_infra.py`
     输出：`14 passed in 5.73s` (100% PASS)。

5. **四个只读裁判文件校验**：
   - 执行命令：`git status --porcelain judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py`
     输出：完全为空（0 修改，完全未被触碰）。

---

## 2. Logic Chain (推理与逻辑链)

1. **需求与风控溯源**：
   - 根据原始需求及 GEMINI.md 第 1 条穿透铁律与第 3 条反向踏空防御准则，29 基账本中包含 7 大主力核心、3 只腰部持仓（161725、000217、005827）和 19 只微型碎片尾仓。
   - `005827 易方达蓝筹精选混合` 为 A 类份额、主动偏股型基金，当前持有市值 ¥124.14，累计浮亏 -¥27.28。其市值 $\ge 100$ 元，且非 C 类、非指数/ETF/联接/红包，因此绝不属于“碎片尾仓”。
2. **同源规则统一消除矛盾**：
   - `advisory_engine.py` 的备忘录算子对尾仓的定义是：市值 $<100$ 元，或在 $100 \sim 200$ 元之间但属于 C 类或含有指数/联接/红包等特征字样；且免赎条件为 C 类 $\ge 30$ 天、非 C 类 $\ge 365$ 天。
   - 将该规则注入 `app_gui.py` 的手机模式 Card 3 扫描逻辑后，`005827` 在 `is_tail` 判断中判定为 False，被安全留在组合中。
3. **同屏平账闭环**：
   - Card 2（备忘录摘要）：渲染 `🧹 19只碎片(¥442.70)`；
   - Card 3（瘦身建议卡）：检测到 `19` 只免赎碎片尾仓（合计沉淀资金 `¥442.70`）；
   - Card 4（下单小抄）：生成 `• 碎片清扫: 建议赎回 19 只尾仓 (¥442.70)，资金买入 002351 易方达裕祥纯债`；
   - 一键按钮提示：`将 19 只免赎碎片 (¥442.70) 全额平移归集至 002351`；
   - 整个手机界面完全消除冲突，达到 100% 同屏一致与精确平账。

---

## 3. Caveats (限制条件与边界假设)

1. 本次修复完全遵循最小改动原则，仅修改了独占所有权的 `AGY2_FundAdvisory/app_gui.py` 和测试套件 `tests/test_m2_features.py`。
2. 保持四个只读裁判文件零改动：`judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py`。
3. 无其他假设或未决事项。

---

## 4. Conclusion (裁决结论)

- **缺陷修复状态**：**COMPLETE (已彻底修复并验证通过)**
- **结果**：
  - `005827 易方达蓝筹`（¥124.14）被排除出清扫列表，受到坚决保护不割肉；
  - 手机模式 Card 2、Card 3、Card 4 全屏数据统一锁定 **19 只 · ¥442.70**；
  - `tests/test_m2_features.py` 全部 6 项测试通过（含新增的真实数值与持仓排他性断言）；
  - `tests/test_infra.py` 14 项基础设施门禁全部通过。

---

## 5. Verification Method (独立核验与验收指令)

```powershell
# 1. 验证 combat_29_funds 真实尾仓计算准确对齐 19 只与 ¥442.70，且排除 005827
py -3 -c "from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager; pm = MultiLedgerManager.get_instance().get_pm('combat_29_funds'); tails = [(fc, getattr(h, 'shares', 0.0)*getattr(h, 'current_nav', 1.0)) for fc, h in pm.holdings.items() if ((0 < getattr(h, 'shares', 0.0)*getattr(h, 'current_nav', 1.0) < 100.0) or (100.0 <= getattr(h, 'shares', 0.0)*getattr(h, 'current_nav', 1.0) < 200.0 and (getattr(h, 'share_class', 'A') == 'C' or any(k in getattr(h, 'fund_name', '') for k in ['联接', 'ETF', '指数', '红包', '体验', '尾仓', '碎片'])))) and ((getattr(h, 'share_class', 'A') == 'C' and min((getattr(b, 'holding_days', 30) for b in getattr(h, 'batches', [])), default=30) >= 30) or (getattr(h, 'share_class', 'A') != 'C' and min((getattr(b, 'holding_days', 30) for b in getattr(h, 'batches', [])), default=30) >= 365))]; print('Count:', len(tails), 'Total:', round(sum(x[1] for x in tails), 2)); assert len(tails) == 19; assert abs(sum(x[1] for x in tails) - 442.70) < 0.1; assert '005827' not in [x[0] for x in tails]; print('PASS!')"

# 2. 运行 M2 专项测试套件 (包含源码完整性、数值对齐与 AppTest 渲染)
py -3 -m pytest tests/test_m2_features.py -v

# 3. 运行基础门禁核验
py -3 -m pytest tests/test_infra.py

# 4. 核验四个裁判文件 0 修改
git status --porcelain judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py
```
