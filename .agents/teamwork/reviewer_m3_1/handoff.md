# G15 Phase 3 独立评审与对抗审查报告 (Handoff Report)

- **Agent Identity**: `reviewer_m3_1` (Roles: `[reviewer, critic]`)
- **Mission**: 对 G15 第三阶段交付（手机长截图高清切片识别导入、碎片尾仓免赎清理器、29 只基金实战存量账本及 Tab 2 交互）进行独立质量评审与对抗性压力测试
- **Parent Conversation ID**: `9a123e21-7525-4c57-9715-710c2a94c199`
- **Working Directory**: `d:\Google\Workspace\Wind\.agents\teamwork\reviewer_m3_1\`

---

## 审查裁决 (Verdict)

**裁定结论**: **APPROVE (审查通过)**
**诚信红线**: 零违规（无伪造输出、无硬编码测试桩、无虚假 facade、4 物理裁判文件及 `DataLoader.simulate_execution` 100% 零修改）

---

## 一、 Observation (直接客观观测证据)

### 1. 物理安全只读红线核验
- 执行命令：`git diff HEAD -- judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py AGY2_FundAdvisory/data_loader.py`
- 观测结果：输出为空，Diff 为 0，表明 4 个物理裁判文件及 `DataLoader.simulate_execution` 签名与默认扣费逻辑保持 100% 原始未动。

### 2. 自动化测试套件执行证据
- **命令 1 (Phase 3 单元与历史闭环测试)**：
  `py -3 -m pytest tests/test_g15_phase3_ocr_and_combat29.py tests/test_adv_final_closure.py -v`
  - `test_slice_long_screenshot_for_ocr_dimensions_and_overlap`: **PASSED**
  - `test_fuzzy_match_fund_by_name_accuracy`: **PASSED**
  - `test_activerisksentry_dimension_13_tail_cleaner`: **PASSED**
  - `test_combat_29_funds_ledger_exact_accounting`: **PASSED**
  - `test_accounting_identity_and_negative_sign_preservation`: **PASSED**
  - `TestAdvFinalClosure` (14 项专项闭环用例): 全部 **PASSED**
  - 测试汇总：**19 passed, 59 warnings in 36.89s**。
- **命令 2 (裁判基线与多阶段全量护栏回归)**：
  `py -3 -m pytest tests/test_infra.py tests/test_delta_m1_guardrails.py tests/test_g15_phase2_memo_and_timemachine.py -v`
  - 测试汇总：**27 passed in 31.49s**。

### 3. 关键实现与会计恒等式代码核查
- **长截图自适应切片算法 (`AGY2_FundAdvisory/portfolio_manager.py:1592-1635`)**：
  保持 100% 原始宽度（`w, h = img.size; cropped = img.crop((0, cur_y, w, end_y))`），纵向按 `target_height=1000`、`overlap=150` 步进。当 `overlap >= target_height` 时包含防死循环安全兜底（`step = max(1, target_height // 2)`）。
- **全市场 28,177 基金字典模糊匹配 (`portfolio_manager.py:1638-1768`)**：
  单例加载 `data/master/fund_catalog.parquet`，优先匹配 6 位代码与 29 只实战存量/核心池别名，剥离省略号及各类标点噪点，结合 `difflib.SequenceMatcher` 与 bigram 预筛加速。
- **负收益保真与会计恒等式反算 (`portfolio_manager.py:1452-1500, 1870-1910`)**：
  彻底移除既有 `abs()` 强制取正，严格保留原始负号。会计恒等式满足 `cost_basis = round(max(0.01, mv_val - pnl_val), 2)` 与 `shares = round(mv_val / cur_nav, 4)`。移除了 `>= 100` 硬编码门槛，支持精准抓取百元以下小额零头尾仓。
- **ActiveRiskSentry 第 13 维碎片尾仓风控 (`AGY2_FundAdvisory/advisory_engine.py:3100-3135`)**：
  判定条件精确限定为：金额 < 100 元，或 100~200 元且为 C 类/指数联接/体验金尾仓；持有天数达标免赎（A类≥365天，C类≥30天）。严格保护主动权益 A 类腰部底仓（如 005827 易方达蓝筹精选 124.14 元未被列入）。
- **combat_29_funds 实战账本分厘平账 (`AGY2_FundAdvisory/multi_ledger_manager.py:189-290`)**：
  - 7 大核心持仓：¥25,128.29
  - 3 只腰部持仓：¥1,044.11
  - 19 只免赎碎片尾仓：¥442.70
  - 总市值合计：$\mathbf{26,615.10}$ 元（误差严格为 0.00 元）
  - 持有天数统一初始化为 400 天（满期免赎，赎回费 0.00%）
  - 深套三大亏损源：#5 (100032, -¥332.54), #6 (011613, -¥428.48), #8 (161725, -¥175.76)，合计浮亏精确为 **-¥936.78**。
- **Tab 2 前端交互落地 (`AGY2_FundAdvisory/app_gui.py:5123-5214, 5744-5844`)**：
  - 顶部工具栏实装 `with st.popover("📸 截图导入")`，支持上传 PNG/JPG，调用 `pm.parse_screenshot_ocr_holdings`，并展示 `st.data_editor` 可核验预览表与覆盖/追加写入双按钮；
  - 诊断区实装「🧹 碎片尾仓一键瘦身建议卡」，支持一键清仓 19 只尾仓并归集至纯债 `002351`；
  - 针对 `combat_29_funds` 渲染专属三阶重塑与减亏手术卡（含 011613 华夏同公司零在途转 A 类、白酒网格/平换宽基、调仓前后全周期对比）。

---

## 二、 Logic Chain (严密逻辑推导链)

1. **[逻辑起点：数据精度与保真要求]**
   - 原始需求要求真实还原用户 29 笔持仓，包括 -936.78 元浮亏源与百元以下碎片。
   - 观测到此前代码存在 `abs()` 反转负收益和 `>=100` 丢弃零头的缺陷。
   - 现有代码修正已移除 `abs()`，保留负号并严格实施会计反算，使数据源头具备真实可信性。
2. **[技术实现：长图切片与模糊识别闭环]**
   - 手机滚动长截图若整图压缩输入 OCR 会产生字体模糊，切片算法固定原图 100% 宽度，以 1000px 高度配合 150px 纵向重叠切块，保证单行卡片绝不被切断。
   - OCR 文本聚合后结合全市场 28,177 基金大字典与别名库，通过正则提取与空间块聚合完成字段结构化，前端辅以 `st.data_editor` 供用户手工微调，形成了技术解析与交互确认的双重防线。
3. **[风控与治理：第 13 维精准除草而不伤主干]**
   - 碎片清理若条件过于粗糙可能误伤优质腰部资产。
   - 本次实装对 <100 元与 100~200 元做精细区分，对 A 类主动权益腰部底仓（如 005827 蓝筹精选）予以保留，仅对 19 只纯碎片和红包体验金进行扫尾，回收 ¥442.70 定向归集至纯债 002351，兼顾了清爽降噪与资产安全。
4. **[推导结论]**
   - 所有需求点（切片算法、全字典模糊匹配、第13维风控、29基实战账本精准平账、Tab 2 卡片交互）均真实落地且经测试验证，未见任何欺骗性假常数或作弊实现。

---

## 三、 Adversarial Stress-Testing (对抗性压力测试)

作为 Adversarial Critic，执行了针对极端边界与失效模式的攻击性测试：

| 测试场景 | 攻击输入 / 假设挑战 | 预期防御机制 | 实测结果 | 结论 |
|---|---|---|---|---|
| **切片空输入与损坏字节** | `b''` 或 `b'corrupted_data'` | 不抛出未捕获异常，优雅返回 `[]` | 均返回 `[]`，未崩溃 | **PASS** |
| **超小尺寸图片 (h < 1000px)** | 500x200 像素微缩图 | 不过度切片，直接返回 1 个完整切块且 y_offset=0 | 返回 1 个切块，模式自动转 RGB | **PASS** |
| **病态重叠参数 (overlap > height)** | height=1000, overlap=1200 | 步长不可 <= 0，防死循环 | 自动触发 `step = max(1, target_height // 2)`，正常完成切片 | **PASS** |
| **模糊匹配空与无关联文本** | `""` 或 `"完全不存在的火星测试基金XYZ999"` | 返回 `{}`，不产生幻觉匹配 | 准确返回 `{}` | **PASS** |
| **尾仓免赎天数临界突破 (C类)** | C 类持有 29 天（未达 30 天） | 触发赎回费，严禁判定为免赎碎片 | 未触发「碎片尾仓清理」预警 | **PASS** |
| **尾仓免赎天数临界突破 (A类)** | A 类持有 364 天（未达 365 天） | 触发阶梯赎回费，严禁判定为免赎碎片 | 未触发「碎片尾仓清理」预警 | **PASS** |
| **腰部底仓免伤防御** | 005827 易方达蓝筹 (¥124.14, A类) | 属于主动权益底仓，严禁被误杀 | 准确保留，未在 `tail_codes` 中出现 | **PASS** |
| **真实长截图本地解析** | 读取用户上传真实截图 (37.6KB) | 切片与 OCR 不抛崩溃异常 | 成功切出 2 个切片并执行 RapidOCR 解析 | **PASS** |

---

## 四、 Caveats (审计边界与注意事项)

1. **真实手机长截图 OCR 识别率边界**：
   在测试用户本地真实截图时，由于原图在传输过程中被压缩为较小字节文件（37.6KB），分辨率降低导致部分模糊文本识别受限。前端在 Tab 2 `📸 截图导入` popover 中设计了 `st.data_editor` 可编辑表格，允许用户在确认入库前进行补充与手工修正，此设计为合理的工程容错防线。
2. **多账本会话隔离**：
   `combat_29_funds` 作为只读预置账本注入 `ledgers_index.json`，在用户或测试会话对其进行调仓模拟时，状态保存在会话快照中，重新加载仍可重置回基准状态。

---

## 五、 Conclusion (最终审查结论)

- **审定结论**：**APPROVE (审查通过)**
- **代码质量评价**：逻辑严密、数学与会计恒等式精确平账、算法防线完备、交互体验优雅合规，无任何作弊或 Facade 违规。

---

## 六、 Verification Method (独立复现与核验指南)

任何后续审计者均可通过以下命令独立复现本报告结论：

```powershell
# 1. 核验 4 个物理裁判文件零修改
git diff HEAD -- judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py AGY2_FundAdvisory/data_loader.py

# 2. 运行 G15 Phase 3 单元与历史闭环测试 (19/19 PASS)
py -3 -m pytest tests/test_g15_phase3_ocr_and_combat29.py tests/test_adv_final_closure.py -v

# 3. 运行裁判基线与多阶段全量护栏回归 (27/27 PASS)
py -3 -m pytest tests/test_infra.py tests/test_delta_m1_guardrails.py tests/test_g15_phase2_memo_and_timemachine.py -v

# 4. 独立验证 29 基账本精确平账至 26615.10 元与 19 只免赎碎片
py -3 -c "from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager; mlm = MultiLedgerManager.get_instance(); pm = mlm.get_pm('combat_29_funds'); assert len(pm.holdings) == 29; assert abs(pm.total_market_value - 26615.10) < 0.05; print('29 Funds Ledger PASSED')"
py -3 -c "from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager; from AGY2_FundAdvisory.advisory_engine import ActiveRiskSentry; mlm = MultiLedgerManager.get_instance(); pm = mlm.get_pm('combat_29_funds'); sentry = ActiveRiskSentry(); rep = sentry.inspect_portfolio(pm.holdings); tail_alerts = [a for a in rep['alerts'] if a.get('dimension') == '碎片尾仓清理']; assert tail_alerts[0]['tail_count'] == 19; assert abs(tail_alerts[0]['recoverable_cash'] - 442.70) < 0.05; print('Tail Cleaner 19 Funds / 442.70 Yuan PASSED')"
```
