# 对抗性质检报告 (Adversarial Challenge Handoff Report)

- **Agent Identity**: `challenger_m3_1` (Roles: `[critic, specialist]`)
- **Mission**: 对 G15 Phase 3 实施成果（长截图高清切片、负收益保真与会计恒等式、碎片尾仓免赎清理判定与 29 基实战账本）执行对抗性极限压力测试并给出质检裁决
- **Parent Conversation ID**: `9a123e21-7525-4c57-9715-710c2a94c199`
- **Working Directory**: `d:\Google\Workspace\Wind\.agents\teamwork\challenger_m3_1\`
- **Adversarial Test Suite**: `tests/test_adversarial_m3_challenger1_ocr_slicing_and_tail.py`
- **Final Verdict**: **`APPROVE`** (无保留全数核准)

---

## 一、 Observation (直接客观观测证据)

### 1. 独立编写并执行 32 项对抗性压力测试 (100% PASS)
- **执行命令**: `py -3 -m pytest tests/test_adversarial_m3_challenger1_ocr_slicing_and_tail.py -v`
- **执行结果**: `32 passed in 16.16s`
- **对抗测试维度分布**:
  - `TestImageSlicingAdversarial`: 15 项测试，覆盖 100px 至 12,000px 极端长宽比切片数量数学推导、像素连续性零漏行验证及退化/损坏输入。
  - `TestTextParsingAndAccountingIdentity`: 11 项测试，覆盖 10 种负收益/千分符/带收益率干扰格式，以及 19 只百元以下微小尾仓保真提取。
  - `TestTailCleanerBoundaryStress`: 2 项综合边界测试，覆盖 100元/200元临界金额、A类/C类份额、主动权益腰部底仓保护与持有期免赎门槛。
  - `TestCombat29FundsPortfolioAccounting`: 2 项核心账本平账与场景调仓执行测试，勾稽分厘平账、-¥936.78 深套亏损源与 19 只尾仓归拢。
  - `TestHighThroughputAndResilience`: 2 项高吞吐与脏数据注入测试，覆盖 50 次切片高频循环（耗时 < 1.5s）与异常文本容错。

### 2. 图像切片边界与零漏行实证检验 (Zero-Pixel-Drop Invariant)
- **观测对象**: `portfolio_manager.py` 第 1592-1636 行 `slice_long_screenshot_for_ocr`。
- **极限高度验证**:
  - $H=100\text{px}$ / $500\text{px}$ / $999\text{px}$ / $1000\text{px}$：严格输出 1 个切片，偏移 $y=0$；
  - $H=1001\text{px}$：临界触发第 2 切片，切片 0 高度 1000px，切片 1 偏移 $y=850$，重叠恰好 150px；
  - $H=8000\text{px}$：生成 10 切片，相邻切片重叠严格为 150px；
  - $H=12000\text{px}$：生成 14 切片，全长无断层；
- **像素全覆盖实证**:
  - 对 $H \in \{500, 1000, 1001, 1500, 2700, 8000, 12000\}$ 构建 RGB 行序号像素矩阵，切片后逐行累加覆盖直方图：
  - 观测结果：$\forall y \in [0, H-1]$，$\text{coverage}[y] \ge 1$，未覆盖漏行数严格为 0（**0 Pixel Gap**）；
  - 相邻切片重叠区间 $(y_{\text{next}}, y_{\text{curr}} + h_{\text{curr}})$ 严格满足 $\text{coverage}[y] \ge 2$ 且像素差矩阵范数严格为 0。

### 3. 负收益符号保真与会计恒等式反算 (No-abs & Accounting Identity)
- **观测对象**: `portfolio_manager.py` 第 1447-1513 行 `parse_smart_text_holdings`。
- **负收益提取格式对抗**:
  - `持有收益 -428.48` $\rightarrow \text{floating\_pnl} = -428.48$（无 `abs()` 篡改）；
  - `收益 -312.36` $\rightarrow \text{floating\_pnl} = -312.36$；
  - `亏损 175.76` 与 `亏损 -175.76` $\rightarrow \text{floating\_pnl} = -175.76$；
  - `累计收益 -1,428.48`（含千分符）$\rightarrow \text{floating\_pnl} = -1428.48$；
  - `收益率 -17.13% 持有收益 -428.48` $\rightarrow$ 准确提取金额 -428.48，未被百分比截断干扰。
- **会计恒等式验证**:
  - 针对所有提取项：$\text{cost\_basis} = \text{market\_value} - \text{floating\_pnl}$；
  - 在亏损状态下：$\text{cost\_basis} = 2072.52 - (-428.48) = 2501.00 > \text{market\_value}$，彻底终结历史版本中将亏损篡改为盈利的严重逻辑颠倒缺陷。
- **百元以下尾仓提取保真**:
  - 对 19 只实操尾仓（从 89.60元、50.00元 直至 0.59元、1.06元）进行全量批处理测试：
  - 19 只全部如实提取其微小金额，无一被旧版本 `>= 100` 约束丢弃或回退为默认的 10,000.00 元。

### 4. 碎片尾仓诊断阈值与主动权益腰部底仓保护 (Tail Cleaner Defense)
- **观测对象**: `advisory_engine.py` 第 3103-3135 行（维度 13 碎片尾仓清理）与 `portfolio_manager.py` 第 8302-8308 行。
- **阈值边界判定矩阵**:
  - $M_{\text{val}} = 99.99$ 元（满期）$\rightarrow$ 判定为碎片尾仓 (`True`)；
  - $M_{\text{val}} = 100.00$ 元（A类无特征字）$\rightarrow$ 保护为腰部资产 (`False`)；
  - $M_{\text{val}} = 124.14$ 元（真实标的 `005827 易方达蓝筹精选混合`）$\rightarrow$ 准确识别为主动权益腰部资产，严禁误杀 (`False`)；
  - $M_{\text{val}} = 150.00$ 元（C类或含“联接/ETF/指数/红包/体验/尾仓”）$\rightarrow$ 准确判定为碎片尾仓 (`True`)；
  - $M_{\text{val}} = 395.73$ 元（`000217 华安黄金ETF联接C`）与 524.24 元（`161725 招商白酒LOF`）$\rightarrow$ 金额 $\ge 200$ 元，均不作为碎片尾仓 (`False`)。
- **免赎持有天数安全红线 (Rule 2 & Rule 7 惩罚防御)**:
  - C类持有 29 天（未满 30 天免赎期）$\rightarrow$ 严禁判定为可清理碎片（`tail_alerts` 结果为 0）；
  - C类持有 5 天（处于 7 天惩罚期）$\rightarrow$ 严禁赎回，守死 1.50% 证监会惩罚红线；
  - A类持有 364 天（未满 365 天）$\rightarrow$ 严禁判定为可清理碎片；
  - A类持有 365 天与 C类持有 30 天 $\rightarrow$ 准确触发零费率免赎清理建议。

### 5. 用户真实 29 只基金实战组合分厘平账与场景调仓执行
- **观测对象**: `multi_ledger_manager.py` `combat_29_funds` 账本。
- **实战账本数学勾稽**:
  - 7 大核心持仓合计: $5681.55 + 5279.05 + 4536.85 + 4101.71 + 2432.90 + 2072.52 + 1023.71 = 25,128.29$ 元；
  - 3 只腰部持仓合计: $524.24 + 395.73 + 124.14 = 1,044.11$ 元；
  - 19 只碎片尾仓合计: $89.60 + 76.00 + \dots + 0.59 = 442.70$ 元；
  - 总资产数学求和: $25,128.29 + 1,044.11 + 442.70 = \mathbf{26,615.10}$ 元（分厘不差）；
  - 3 大深套亏损源浮亏总额: $-428.48 - 332.54 - 175.76 = -936.78$ 元；
- **一键清扫场景调仓 (`sweep_tail_and_c_class`) 执行**:
  - 生成 19 笔卖出指令（涵盖全部 19 只碎片尾仓），7 大核心与 3 只腰部资产（005827 等）卖出数量严格为 0；
  - 卖出总金额严格为 442.70 元，总赎回费用严格为 0.00 元；
  - 生成 1 笔买入指令：将净回收的 442.70 元全额申购纯债压舱石 `002351 易方达裕祥回报债券A`。

### 6. 基线与回归测试套件全量验证
- `py -3 -m pytest tests/test_infra.py tests/test_g15_phase3_ocr_and_combat29.py -v`:
  - `19 passed in 11.77s`，基线裁判文件零受损，系统基础能力稳固。

---

## 二、 Logic Chain (严密逻辑推导链)

1. **[切片完整性]**:
   - 由观测 1 与 2 可知，`slice_long_screenshot_for_ocr` 在步长 $\Delta y = \text{target\_height} - \text{overlap} = 850\text{px}$ 的迭代下，终止条件为 `end_y >= h`。
   - 由于每个切片区间为 $[y, \min(y + 1000, h)]$，且 $y_{k+1} = y_k + 850 < y_k + 1000$，任意两相邻切片区间交集严格为 $[y_{k+1}, y_k + 1000]$，长度恰好为 $150\text{px}$。
   - 对 100px 至 12000px 的全覆盖实证实测表明，无任何像素行遗漏，证明手机长截图在纵向切片送入 OCR 时绝不会发生因切线截断而导致文字丢失的物理缺陷。
2. **[负收益与会计恒等式保真]**:
   - 由观测 3 可知，正则解析器在剥离百分比干扰后，直接提取负号与数值赋给 `floating_pnl`，彻底移除了历史遗留的 `abs()` 函数。
   - 恒等式 $\text{cost\_basis} = \text{market\_value} - \text{floating\_pnl}$ 在负收益时等价于投入成本高于现存市值，真实反映浮亏实质；百元以下尾仓不再受 `>=100` 硬过滤阻断，实现了散户红包零头到大额底仓的全保真提取。
3. **[碎片尾仓清理边界风控]**:
   - 由观测 4 可知，碎片判定以 100 元为绝对下界，100~200 元区间通过 C 类标签及特征关键词（“联接”、“ETF”、“指数”等）建立二次过滤器。
   - 这一双阶分流结构成功使持仓金额为 124.14 元的主动权益 A 类标的（005827 易方达蓝筹精选）免遭误杀，精准锁定了真正需要清理的 19 只体验金零头与红包尾仓（¥442.70）。
   - 同时，持有期硬门槛（C类 $\ge 30$ 天、A类 $\ge 365$ 天）从逻辑根源杜绝了在常规调仓中触发 1.50% 巨额惩罚费的可能。
4. **[实战账本自洽性]**:
   - 由观测 5 可知，`combat_29_funds` 在底层资产市值、深套浮亏、持有天数及调仓方案各维度均完美自洽，且场景调仓能够严格按照 0 赎回费将 ¥442.70 资金平移至 002351。

---

## 三、 Caveats (边界、假设与潜在限制)

1. **极低分辨率超窄截图极限**:
   - 若用户上传经过即时通讯软件极端压缩的缩略图（例如宽度仅 100px、字高仅 2~3px），OCR 文字识别引擎本身的字形特征抽取受限于物理信息论上界。此边界属于输入数据源退化，系统在前端设计了交互式 `st.data_editor` 表格以便用户在入库前进行人工确认与校正。
2. **A 类基金 365 天免赎假设**:
   - 绝大多数公募基金 A 类份额在持有满 1 年（365天）后赎回费率降为 0.00%（少数定开或特殊长周期品种为 730 天）。实战账本统一设置批次持有天数为 400 天，全面越过了所有标准公募基金的阶梯收费期。

---

## 四、 Conclusion (终审裁决)

基于 32 项对抗性压力测试、19 项基线与集成测试（合计 **51/51 项 100% 绿灯全通**）的充分实证：
- 长截图高清切片算法满足**零像素漏行（Zero-Pixel-Drop）**与原始宽度保真；
- 正则解析与会计核算满足**负收益严格保真**与**会计恒等式自洽**；
- 碎片尾仓清理器满足**腰部主动资产保护**与**免赎惩罚严格防御**；
- 29 只基金实战存量账本满足**¥26,615.10 精确平账**与**三阶手术平滑执行**。

**裁决结果**: **`APPROVE` (通过验收)**。

---

## 五、 Verification Method (独立复现与验证指引)

任何审计代理或主控代理均可通过以下命令一键独立复现本报告的全部实证结论：

```powershell
# 1. 运行本报告所创设的 32 项对抗性压力测试套件
py -3 -m pytest tests/test_adversarial_m3_challenger1_ocr_slicing_and_tail.py -v

# 2. 运行 Phase 3 核心功能与平账测试套件
py -3 -m pytest tests/test_g15_phase3_ocr_and_combat29.py -v

# 3. 运行裁判基准防线测试套件
py -3 -m pytest tests/test_infra.py -v

# 4. 命令行分厘平账与尾仓扫描快速单行验证
py -3 -c "from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager; from AGY2_FundAdvisory.advisory_engine import ActiveRiskSentry; mlm = MultiLedgerManager.get_instance(); pm = mlm.get_pm('combat_29_funds'); assert len(pm.holdings) == 29; assert abs(pm.total_market_value - 26615.10) < 0.01; sentry = ActiveRiskSentry(); rep = sentry.inspect_portfolio(pm.holdings); tail_alerts = [a for a in rep['alerts'] if a.get('dimension') == '碎片尾仓清理']; assert tail_alerts[0]['tail_count'] == 19; assert abs(tail_alerts[0]['recoverable_cash'] - 442.70) < 0.01; print('ALL 29 FUNDS COMBAT VERIFICATIONS PASSED')"
```
