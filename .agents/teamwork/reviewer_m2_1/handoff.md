# Milestone 2 (M2) 审查与对抗挑战报告 (Review & Challenge Report)

## Review Summary

**Verdict**: **REQUEST_CHANGES** (需针对手机视图 Card 3/4 尾仓计算与同屏一致性进行轻量级修正)

---

## 1. Observation (客观实地走查与证据链)

根据调度任务要求与审查底线，审查智能体对 `worker_m2` 交付代码、核心账本数据及自动化测试套件进行了独立、客观的穿透核验：

### 1.1 审查要求逐项核对证据链

1. **全局紧凑顶栏挂载位置**：
   - 走查位置：`AGY2_FundAdvisory/app_gui.py` 第 2850~2924 行。
   - 挂载顺序：顶栏渲染完全置于 `if st.session_state.get("app_view_layout_mode") == "📱 手机极简盯盘":`（第 2928 行）之前，且手机视图分支在第 3274 行执行 `st.stop()`。
   - 结论：**验证通过 (PASS)**。桌面专业模式与手机极简模式 100% 共享全局顶栏，左侧品牌角标、中间激活账本选择器、右侧视图模式切换胶囊在双模式下均能正常渲染与交互。

2. **激活账本切换功能**：
   - 走查位置：`app_gui.py` 第 2883~2894 行与 `switch_active_ledger`（第 2451~2490 行）。
   - 实操核验：调用 `MultiLedgerManager.get_instance().list_ledgers()`，准确返回 `main_live`（主实盘账本）与 `combat_29_funds`（实战存量组合（29只·¥2.66万））。
   - 切换联动：切换时调用 `pm.save_state()` 保存旧账本，更新 `st.session_state.active_ledger_id` 与 `pm` 实例，清除诊断与再平衡缓存，并触发 `st.rerun()`。
   - 结论：**验证通过 (PASS)**。

3. **手机模式真 OCR 切片解析与一键入库闭环**：
   - 走查位置：`app_gui.py` 第 3154~3274 行。
   - 证据：彻底移除了敷衍用户的假上传提示文本（静态检索确认无任何残留）；用户上传图片后当场调用 `pm.parse_screenshot_ocr_holdings`（底层驱动 `slice_long_screenshot_for_ocr` 100% 原始宽度横向无损切片与 RapidOCR 离线模型）；在手机端即时渲染 `st.data_editor` 预览编辑表；提供「✅ 确认无误，一键覆盖写入当前账本 (`btn_mob_ocr_commit_replace`)」与「➕ 追加合并写入当前账本 (`btn_mob_ocr_commit_append`)」，落盘并刷新。
   - 结论：**验证通过 (PASS)**。

4. **手机模式 5 张卡片流与尾仓清扫卡一致性审查**：
   - 走查位置：`app_gui.py` 第 2931~3153 行。
   - **重大异常发现**：
     - 在 Card 2（五维决策备忘录）第 2950 行调用 `generate_chief_advisor_memo`，对于 `combat_29_funds` 账本计算出的碎片统计为：
       `frag_count = 19`, `frag_amt = 442.70`，界面徽章渲染为 `🧹 19只碎片(¥442.70)`；
     - 但在紧接着的 Card 3（第 3003~3013 行），代码采用粗暴过滤：
       ```python
       for fc, h in pm.holdings.items():
           mv_h = getattr(h, "shares", 0.0) * getattr(h, "current_nav", 1.0)
           min_d = min((getattr(b, "holding_days", 30) for b in getattr(h, "batches", [])), default=getattr(h, "holding_days", 30))
           if 0 < mv_h < 200.0 and min_d >= 30:
               tail_items.append((fc, getattr(h, "fund_name", fc), mv_h, min_d))
       ```
     - 运行探针实测该代码段对 `combat_29_funds` 的计算结果为：
       `len(tail_items) = 20`, `sum = 566.84`！
     - 经逐项核对，用户的第 10 号持仓——**`005827 易方达蓝筹精选混合`**（持有市值 ¥124.14，份额 A 类，持仓天数 1041 天，累计浮亏 -¥27.28，属于用户的“3只腰部核心持仓”之一）因市值处于 100~200 元区间且持有天数 > 30 天，被**错误卷入碎片清扫列表**！
     - 导致在同一手机屏幕上：
       - Card 2 显示：`🧹 19只碎片(¥442.70)`；
       - Card 3 显示：`检测到当前账本含有 20 只免赎碎片尾仓（合计沉淀资金 ¥566.84）`；
       - Card 4 显示：`• 碎片清扫: 建议赎回 20 只尾仓 (¥566.84)，资金买入 002351 易方达裕祥纯债`；
       - 一键按钮提示：`将 20 只免赎碎片 (¥566.84) 全额平移归集至 002351`！
   - 结论：**重大不一致缺陷 (FAIL)**。同屏数据显示自相矛盾，且违背了用户需求与 GEMINI.md 第 1 条穿透铁律（将腰部偏股基金割肉归集至纯债）。

### 1.2 物理裁判文件与自动化测试独立运行证据

- 四只读裁判文件校验：
  `git status --porcelain judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py` 输出完全为空，绝对 0 修改。
- 自动化测试实跑记录：
  - `pytest tests/test_m2_features.py`：5 passed in 38.78s。
  - `pytest tests/test_infra.py`：14 passed in 5.86s。
  - `pytest tests/test_adv_final_closure.py`：14 passed in 43.16s。

---

## 2. Logic Chain (推理与逻辑链)

1. **真实持仓结构与需求契约溯源**：
   - 需求文档 §一.1 与 §三.3 明确定义了 29 基的持仓分层：7 大主力仓（5681.55 至 1023.71 元）、3 只腰部仓（161725 招商白酒 524.24 元、000217 黄金联接C 395.73 元、005827 蓝筹精选 124.14 元[-27.28]），以及 **19 只 89.60 至 0.59 元的碎片尾仓（合计 ¥442.70）**。
   - `advisory_engine.py` 第 4374~4389 行对碎片尾仓给出了严格的量化定义：
     `is_tail = (0 < mv < 100.0) or (100.0 <= mv < 200.0 and (s_cls == "C" or any(k in fname for k in ["联接", "ETF", "指数", "红包", "体验", "尾仓", "碎片"])))`
     `is_fee_free = (s_cls == "C" and int(m_days) >= 30) or (s_cls != "C" and int(m_days) >= 365)`
   - 在此定义下，`005827`（A类份额，主动混合型，市值 124.14 元）正确被排除在碎片尾仓之外，剩余 19 只微型尾仓准确合计为 **19 只 · ¥442.70**。
2. **Card 3 过滤条件遗漏导致的因果断裂**：
   - `app_gui.py` 第 3008 行未复用上述严密判定，仅凭 `0 < mv_h < 200.0 and min_d >= 30` 粗筛，导致 005827 被误收割。
   - 进而导致 Card 3 与 Card 4 的统计数字（20只 · ¥566.84）与 Card 2（19只 · ¥442.70）在同一视觉流中冲突，且在点击一键清扫后会将尚处浮亏的蓝筹精选误卖出。
3. **测试虚荣问题 (Anti-Testing Vanity)**：
   - `tests/test_m2_features.py` 中的 `test_app_gui_source_code_integrity` 仅断言了字符串 `"btn_mob_sweep_tails" in src`，没有对实际计算的尾仓数量与金额进行数值断言，使得此逻辑缺陷绕过了现有测试。

---

## 3. Findings (审查发现清单)

### [Major] Finding 1: 手机视图 Card 3/4 尾仓清扫计算规则与 Card 2 及风控契约脱节

- **What**: 手机极简盯盘视图中，Card 3（尾仓清扫卡）与 Card 4（下单口令小抄）将腰部主动权益仓位 `005827 易方达蓝筹精选混合`（市值 124.14 元，A类）错误算作碎片尾仓，输出“20只 · ¥566.84”，与 Card 2 的“19只 · ¥442.70”同屏矛盾。
- **Where**: `AGY2_FundAdvisory/app_gui.py` 第 3003~3013 行。
- **Why**: 违反需求契约（明确指定 19 只 · ¥442.70 方案）、GEMINI.md 第 1 条穿透铁律与第 3 条反向踏空防御准则。
- **Suggested Fix**:
  将 `app_gui.py` 第 3003~3013 行的 `tail_items` 扫描逻辑与 `advisory_engine.py` 完全对齐，加入 A/C 份额与 100~200 元特征识别：
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
  并在 `tests/test_m2_features.py` 中增加对 `combat_29_funds` 尾仓精确数量（19 只）与金额（¥442.70）的断言。

### [Minor] Finding 2: 手机模式追加合并导入默认赋予满期持有天数缺少新老批次保护

- **What**: 手机长截图识别导入在「➕ 追加合并写入当前账本 (`btn_mob_ocr_commit_append`)」时，对于已有持仓追加份额时赋予 `holding_days = 365`。
- **Where**: `AGY2_FundAdvisory/app_gui.py` 第 3260 行。
- **Why**: 若用户在生产实盘中通过追加导入了新买入份额，可能使原本未满 7 天或 30 天的份额被误标为 365 天。
- **Suggested Fix**: 建议优化为对已有持仓保留原有批次或使用悲观最小持有天数，作为后续稳健性增强。

---

## 4. Caveats (限制条件与边界假设)

1. 本审查严格恪守 **只读契约**，未私自修改任何生产与测试代码文件。
2. 除 Finding 1 发现的尾仓逻辑差异外，全局顶栏挂载位置、双模式一键切换、真 OCR 横向切片与一键覆盖/追加落盘闭环的其余实现质量极高，符合技术规范。

---

## 5. Conclusion (裁决结论与改动建议)

- **审查裁决**: **REQUEST_CHANGES**
- **返工指示**:
  1. 请 Worker（或由主管分派）在 `AGY2_FundAdvisory/app_gui.py` 第 3003~3013 行修正 `tail_items` 判定逻辑，使其与 `advisory_engine.py` 100% 对齐，确保在 `combat_29_funds` 账本下 Card 3 与 Card 4 准确展示为 **19 只 · ¥442.70**；
  2. 在 `tests/test_m2_features.py` 中补充对 29 基账本尾仓真实提取结果的严密断言（断言数量为 19，金额为 442.70，且 `005827` 绝不在清扫列表中）；
  3. 修复完成后再次提审，审查员将快速核验并放行。

---

## 6. Verification Method (独立核验与验收指令)

```powershell
# 1. 验证 combat_29_funds 真实尾仓计算准确对齐 19 只与 ¥442.70
py -3 -c "from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager; pm = MultiLedgerManager.get_instance().get_pm('combat_29_funds'); tails = [(fc, getattr(h, 'shares', 0.0)*getattr(h, 'current_nav', 1.0)) for fc, h in pm.holdings.items() if ((0 < getattr(h, 'shares', 0.0)*getattr(h, 'current_nav', 1.0) < 100.0) or (100.0 <= getattr(h, 'shares', 0.0)*getattr(h, 'current_nav', 1.0) < 200.0 and (getattr(h, 'share_class', 'A') == 'C' or any(k in getattr(h, 'fund_name', '') for k in ['联接', 'ETF', '指数', '红包', '体验', '尾仓', '碎片'])))) and ((getattr(h, 'share_class', 'A') == 'C' and min((getattr(b, 'holding_days', 30) for b in getattr(h, 'batches', [])), default=30) >= 30) or (getattr(h, 'share_class', 'A') != 'C' and min((getattr(b, 'holding_days', 30) for b in getattr(h, 'batches', [])), default=30) >= 365))]; print('Count:', len(tails), 'Total:', round(sum(x[1] for x in tails), 2)); assert len(tails) == 19; assert abs(sum(x[1] for x in tails) - 442.70) < 0.1"

# 2. 运行 M2 专项测试
py -3 -m pytest tests/test_m2_features.py -v
```
