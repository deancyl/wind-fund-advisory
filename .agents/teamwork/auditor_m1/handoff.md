# Forensic Audit Report (法证诚信审计报告) — G16 M1 里程碑

**Work Product**: G16 Milestone 1 Deliverables (`AGY2_FundAdvisory/advisory_engine.py`, `AGY2_FundAdvisory/app_gui.py`, `tests/test_g16_phase1_memo_and_combat29.py`)  
**Profile**: General Project / Integrity Forensics  
**Auditor**: Teamwork Forensic Auditor (Archetype: forensic_auditor)  
**Verdict**: **CLEAN** (裁决：全项合规通过，无任何诚信违规)

---

## 1. Observation (客观观测证据记录)

本审计智能体遵循法证诚信审计原则（Trust NOTHING — verify EVERYTHING），对工作区执行了完整的独立无损走查、哈希比对、Git Diff 静态分析及独立单测探针复验，直接记录到以下客观证据：

### 1.1 四个只读裁判文件完整性审计 (绝对零容忍)
执行命令与哈希比对（工作区文件 vs HEAD 原始版本）：
```python
import hashlib, subprocess

files = [
    'AGY2_FundAdvisory/judge_engine.py',
    'AGY2_FundAdvisory/holdout_vault.py',
    'AGY2_FundAdvisory/AGENT_SPEC.md',
    'AGY2_FundAdvisory/tests/test_infra.py',
]
```
客观结果记录：
- `AGY2_FundAdvisory/judge_engine.py`:
  - Working Tree SHA256: `76f930371176de7ee6a413174b030101e3210ac6e037f5d10fe229af31cc07be`
  - HEAD SHA256: `76f930371176de7ee6a413174b030101e3210ac6e037f5d10fe229af31cc07be`
  - Match: **True (100% 原始未变动，git diff 输出为 0 行)**
- `AGY2_FundAdvisory/holdout_vault.py`:
  - Working Tree SHA256: `88122eaf647040a410e2fd95da81077db10149a498a47340ff40b670bd031d2a`
  - HEAD SHA256: `88122eaf647040a410e2fd95da81077db10149a498a47340ff40b670bd031d2a`
  - Match: **True (100% 原始未变动，git diff 输出为 0 行)**
- `AGY2_FundAdvisory/AGENT_SPEC.md`:
  - Working Tree SHA256: `a346586f9bd2dc0ee83e665bd18e7a6471464c9f7b658e392b989b800cd63957`
  - HEAD SHA256: `a346586f9bd2dc0ee83e665bd18e7a6471464c9f7b658e392b989b800cd63957`
  - Match: **True (100% 原始未变动，git diff 输出为 0 行)**
- `AGY2_FundAdvisory/tests/test_infra.py`:
  - Working Tree SHA256: `b8d781be8135be05cf61e62e4b534e359985ad880f27ffb61228a33df6b02a6a`
  - HEAD SHA256: `b8d781be8135be05cf61e62e4b534e359985ad880f27ffb61228a33df6b02a6a`
  - Match: **True (100% 原始未变动，git diff 输出为 0 行)**

### 1.2 DataLoader.simulate_execution 物理签名与计费逻辑审计
- 文件检查：`git diff HEAD -- AGY2_FundAdvisory/data_loader.py` 输出为 0 行（未作任何修改）。
- 签名反射验证结果：
  ```text
  Signature: (weights_df: pandas.DataFrame, prices_df: pandas.DataFrame, is_otc: bool = True, penalty_days: int = 7, penalty_rate: float = 0.015, etf_impact: float = 0.001) -> pandas.DataFrame
  ```
  函数默认签名、阶梯费率判定与 1.50% 惩罚费率硬扣费逻辑 100% 保持原始实现。

### 1.3 真实性与反作弊审计 (Anti-Cheat Audit)
- **代码走查 (`AGY2_FundAdvisory/advisory_engine.py`)**：
  - 在第 4277~4429 行，修复了旧代码读取不存在的 `cost_value` 导致的浮亏漏检 Bug；
  - 成本读取链路严格支持：`cost_basis` -> `cost_price * shares` -> `cost_value`，且兼容直接读取 `floating_pnl_pct` 与 `pnl_pct`；
  - 针对 Tab 1 拟建仓字典场景，基于数学特征校验（`isinstance(holdings, dict) and all(0.0 <= float(v) <= 1.0) and abs(sum(v) - 1.0) < 0.05`）进行模式识别，展示“拟建仓组合结构校验”，彻底根除了“6只碎片尾仓合计 ¥1.00”的失真逻辑；
  - 碎片尾仓判定与 `ActiveRiskSentry` 物理对齐（不足 100 元，或 100~200 元且为 C类/联接/尾仓，且持有期满足免赎条件），实测对 `combat_29_funds` 精确锁定 19 只免赎尾仓（合计 ¥442.70），精准剔除 #10 005827 易方达蓝筹（¥124.14，A类偏股混合）；
  - 全文件无任何针对特定测试函数名称、参数字符串特判（如 `if "test" in ...:`）等假冒实现。
- **代码走查 (`AGY2_FundAdvisory/app_gui.py`)**：
  - `render_chief_advisor_memo_card`（第 249~348 行）重构为 1 行 5 列横向响应式等高矩阵网格（`.chief-memo-grid`，`grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px; width: 100%;`）；
  - 首屏调用位置（第 3208~3221 行）从 `wing_expander` 内部移出，提升至 4 张全局指标卡正下方、折叠框上方，首屏直显无需展开；
  - 统一经由 `safe_markdown_html(html_code)` 渲染。
- **测试真实性走查 (`tests/test_g16_phase1_memo_and_combat29.py`)**：
  - 包含 6 个测试用例，涵盖 `HoldingItem` 对象、真实 `combat_29_funds` 账本、Tab 1 字典防御、中美利差叙事、1行5列网格样式及 CommonMark 4 空格防御；
  - 无循环论证或伪造断言。

### 1.4 规则 27 与代码规范审计 (CommonMark 4+ 空格防御)
- 走查 `app_gui.py` 第 194~210 行：
  - `_clean_html` 强制执行 `[line.strip() for line in html_str.splitlines()]` 并清除空行；
  - `safe_markdown_html` 强制统一调用 `_clean_html`；
  - 实测运行断言：`render_chief_advisor_memo_card` 输出的每一行均不以 4 个空格或制表符 `\t` 开头，彻底免疫 Markdown 缩进代码块转义。

### 1.5 独立测试套件执行证据
- `pytest tests/test_infra.py -v`: 14 passed in 5.74s (100% pass)
- `pytest tests/test_g16_phase1_memo_and_combat29.py -v`: 6 passed in 19.68s (100% pass)
- `pytest tests/test_adversarial_m2_challenger2_timemachine_and_memo.py tests/test_challenger_m2_adversarial.py -v`: 36 passed in 24.58s (100% pass)
- 独立法证探针 (`MultiLedgerManager` + `generate_chief_advisor_memo`) 实测数据：
  - 账本基金数量：29 只
  - 总市值：¥26,615.10
  - `deep_loss_count`: 18 只 (>= 3)
  - `frag_count`: 19 只
  - `frag_amt`: ¥442.70
  - Tab 1 校验：`frag_count == 0`，`deep_loss_count == 0`，无 "¥1.00" 误报。

---

## 2. Logic Chain (推理链条与法证推导)

1. **红线物理隔离推导**：
   - 观测到 4 个裁判文件的 SHA256 哈希值与 HEAD 严格一致，git diff 0 行修改；`DataLoader.simulate_execution` 签名与实现 0 行修改；
   - -> 推导结论：未侵犯任何物理裁判红线，满足绝对契约。
2. **逻辑真实性推导**：
   - 观测到 `advisory_engine.py` 的盈亏比计算基于传入实体的真实属性，支持多种命名变体，并在真实 29 基账本中计算出 18 只浮亏超 10% 的标的，最大拖累前三大出血点准确报出 `011613` (-17.1%)、`100032` (-12.0%)、`161725` (-25.1%)；
   - 观测到碎片计算与 `ActiveRiskSentry` 的 100 元/200 元阶梯和免赎持有天数双重判定完全一致，且针对 Tab 1 权重字典进行了数学边界隔离；
   - -> 推导结论：逻辑具备完全的自洽性与因果真实性，不存在针对测试输入的 Hardcode 假造行为。
3. **前端呈现与规则 27 推导**：
   - 观测到卡片 HTML 布局已从单列纵向堆叠重构成 1 行 5 列横向网格，位置成功提权至首屏主视野；所有渲染经 `_clean_html` 统一收口，经正则和逐行验证无任何 4 空格缩进；
   - -> 推导结论：UI 交互提升与规则 27 纯化标准均达标。
4. **测试独立性推导**：
   - 运行针对性测试、全量回归与对抗测试共 56 项测试，全部绿灯通过；独立探针实测数据与交付报告分厘无差；
   - -> 推导结论：工件具备高度的健壮性与可复现性。

---

## 3. Caveats (审计边界与说明)

1. **后续阶段规划衔接**：
   - 本次审计范围严格聚焦于 G16 M1（投顾备忘录成本 Bug 修复、首屏 1行5列矩阵重构与 29 基底层数据对齐）；
   - 后续 M2 的全局顶栏切换器、手机长截图真 OCR 切片导入，以及 M3 的 Tab 2 三步瘦身面板与 Tab 3 历史时光机真规则回测，属于后续里程碑范围，将在相应阶段继续接受严格法证审查。
2. **运行期缓存文件**：
   - 测试执行过程中可能会临时触碰 `data/portfolio_watchdog.json`，在单测结束后已复核恢复为 clean baseline。

---

## 4. Conclusion (法证裁决结论)

- **二元法证裁决**：**CLEAN**
- **裁决陈述**：
  G16 M1 里程碑交付物完全真实有效，彻底修复了 `cost_value` 导致的浮亏漏检严重缺陷，成功实现了首屏 1 行 5 列横向情报矩阵的高密提权，并在 29 基实战账本中精确锁定了 19 只免赎碎片（¥442.70）与核心出血点；所有代码均属动态真实计算，未发现任何特判作弊、硬编码伪造或门禁绕过行为，四个只读裁判文件与 DataLoader 签名保持 100% 原始未变动，规则 27 纯化标准完全达标。
- **准予准入**：**PASS**，批准进入 G16 M2 阶段。

---

## 5. Verification Method (独立复核方法与命令)

任何后续智能体或人工审查员可通过以下标准命令进行独立复核：

```powershell
# 1. 验证四个只读裁判文件零改动与 DataLoader 签名未变
git diff HEAD -- AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md AGY2_FundAdvisory/tests/test_infra.py AGY2_FundAdvisory/data_loader.py

# 2. 运行 M1 专属针对性单测 (6 项全过)
py -3 -m pytest tests/test_g16_phase1_memo_and_combat29.py -v

# 3. 运行基础架构与裁判单测 (14 项全过)
py -3 -m pytest tests/test_infra.py -v

# 4. 运行全量对抗与回归单测 (36 项全过)
py -3 -m pytest tests/test_adversarial_m2_challenger2_timemachine_and_memo.py tests/test_challenger_m2_adversarial.py -v
```
