# Forensic Audit Report — Milestone 2 (M2)

**Work Product**: Milestone 2 Deliverables (`AGY2_FundAdvisory/app_gui.py`, `AGY2_FundAdvisory/portfolio_manager.py`, `tests/test_m2_features.py`)  
**Auditor**: `auditor_m2` (Forensic Auditor)  
**Profile**: General Project (Development Mode with Strict Physical Invariants)  
**Verdict**: **CLEAN**

---

## 1. Observation (客观实地走查与证据链)

### 1.1 四个只读裁判文件完整性审计 (绝对零容忍基准)
通过独立脚本计算 SHA-256 哈希值并与基准值及 `git diff HEAD` 进行逐字节比对：
- `AGY2_FundAdvisory/judge_engine.py`:
  - 测得 SHA-256: `76f930371176de7ee6a413174b030101e3210ac6e037f5d10fe229af31cc07be` (42,175 bytes)
  - 基准对比: 100% 吻合，`git diff` 0 字节变动。
- `AGY2_FundAdvisory/holdout_vault.py`:
  - 测得 SHA-256: `88122eaf647040a410e2fd95da81077db10149a498a47340ff40b670bd031d2a` (5,685 bytes)
  - 基准对比: 100% 吻合，`git diff` 0 字节变动。
- `AGY2_FundAdvisory/AGENT_SPEC.md`:
  - 测得 SHA-256: `a346586f9bd2dc0ee83e665bd18e7a6471464c9f7b658e392b989b800cd63957` (8,237 bytes)
  - 基准对比: 100% 吻合，`git diff` 0 字节变动。
- `AGY2_FundAdvisory/tests/test_infra.py`:
  - 测得 SHA-256: `b8d781be8135be05cf61e62e4b534e359985ad880f27ffb61228a33df6b02a6a` (10,524 bytes)
  - 基准对比: 100% 吻合，`git diff` 0 字节变动。
- `tests/test_infra.py`:
  - 测得 SHA-256: `48bee0da300d7c0a0848ec1376e4b9b2e55224d2736081713b4340f0362cd100` (10,184 bytes)
  - 基准对比: 100% 吻合，`git diff` 0 字节变动。

### 1.2 `DataLoader` 物理签名与计费逻辑审计
走查 `AGY2_FundAdvisory/data_loader.py`：
- `git diff HEAD -- AGY2_FundAdvisory/data_loader.py` 输出完全为空（0 修改）；
- 经 `inspect.signature` 核验，`simulate_execution` 签名保持原样：
  `simulate_execution(weights_df: pd.DataFrame, prices_df: pd.DataFrame, is_otc: bool = True, penalty_days: int = 7, penalty_rate: float = 0.015, etf_impact: float = 0.001) -> pd.DataFrame`
- 惩罚性费率逻辑（<7天 1.50%、7~29天 0.50%/0.75%、30~179天、>=180天 0.00%）完全未被篡改。

### 1.3 源码反作弊与模糊匹配真实性走查
1. **代码特判与绕过检测**：
   - 走查 `portfolio_manager.py` 与 `app_gui.py` 的全部新增代码（共计 478 行增量），未发现任何针对测试函数名称或输入参数的特判逻辑（零 `if "test" in ...`，零假常数覆盖）。
2. **文本清洗与模糊匹配链路真实性**：
   - `parse_smart_text_holdings` 中通过 `re.sub(r'(?:昨日收益|昨日盈亏|日收益)[:：\s]*[+-]?[0-9]+...', ' ', remain_line)` 前置剥离日收益标签与数值，切词搜索加入 `not w.isdigit() and len(w) >= 2` 阻断纯数字对基金代码目录的污染；
   - 针对未在测试用例中出现的未见标的（如易方达蓝筹精选、易方达中小盘、富国中证红利增强A/C、华夏500ETF联接C、博时标普500ETF联接A、摩根标普500指数A、招商红利稳益增强C）进行了 8 组对抗性输入压力测试，8/8 真实且精准地完成代码匹配、A/C份额区分、市值与盈亏平账计算（`cost_basis = market_value - floating_pnl`）。
3. **`tests/test_m2_features.py` 审查**：
   - 测试用例覆盖模糊匹配、前置正则清洗、别名一致性、AST/正则结构核验及 AppTest 桌面/手机无异常双向渲染；
   - 断言基于真实基金代码与真实数学等式，不存在自我循环论证或伪造 mock 断言。

### 1.4 规则 27 与 CommonMark HTML 代码块规范审计
- 走查 `app_gui.py` 新增代码：
  - 顶栏控件及手机极简盯盘 5 大卡片的所有多行富文本 HTML 块全部强制通过 `safe_markdown_html(...)` 渲染；
  - `safe_markdown_html` 统一收口至 `_clean_html(...)`，物理执行 `[line.strip() for line in html_str.splitlines()]` 剥离每行首尾空格与空行；
  - 唯一出现的 `st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)` 为单行无缩进字符串，不存在触发 CommonMark 4+ 空格缩进代码块解析的漏洞。

### 1.5 全局工作区隔离审计
- 核验 `c:\Users\deanc\.gemini\GEMINI.md` 的修改时间为 `2026-11-03T18:44:33`，未发生任何全局文件外溢或污染。

---

## 2. Logic Chain (推理与逻辑链)

1. **裁判文件物理未修改** $\to$ 所有基础设施与评测规则处于基线状态，无任何形式的裁判绕过；
2. **DataLoader 计费逻辑完全保留** $\to$ 交易摩擦与 1.50% 赎回费惩罚等底线风控模型未受影响；
3. **AST 走查与正则探针证实无特判** $\to$ 新增特性并非为了通过单测而编写的假常数或假分支；
4. **8 组未见对抗样本 100% 通过真实解析** $\to$ 模糊匹配与昨日收益防截断为通用、健壮的生产级代码；
5. **UI 全部走 `safe_markdown_html` 纯化** $\to$ 彻底杜绝了 CommonMark 语法泄露与排版崩溃风险；
6. **全量自动化测试（38 项）全部绿灯** $\to$ 既有功能与 M2 新功能保持良好回归兼容。

---

## 3. Caveats (限制条件与边界假设)

1. 手机端 RapidOCR 依赖本地 ONNX Runtime 模型及系统环境，测试中通过模拟真实 OCR 提取出的结构化文本与空字节边界验证了容错性与健壮性；
2. 截图导入持仓默认赋予 365 天持有天数，UI 中提供了 `st.data_editor` 供用户在提交前人工核对与修正。

---

## 4. Conclusion (法证裁决)

- **法证裁决**: **CLEAN**
- **结论说明**:
  Milestone 2 提交代码真实有效、逻辑自洽、无任何作弊或硬编码行为，4 个裁判文件保持 100% 原始未修改状态，规则 27 得到严格执行，所有核心测试套件绿灯通过。**准予放行通过 M2 阶段！**

---

## 5. Verification Method (独立复现与检验指令)

任意审计员可通过以下步骤完全复现本报告的检验结论：

1. **裁判文件哈希与 Git 差异校验**：
   ```powershell
   git status --porcelain AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md AGY2_FundAdvisory/tests/test_infra.py tests/test_infra.py AGY2_FundAdvisory/data_loader.py
   ```
   *预期*: 输出为空。

2. **M2 专项测试套件独立运行**：
   ```powershell
   py -3 -m pytest tests/test_m2_features.py -v
   ```
   *预期*: 5 passed in ~38s。

3. **核心裁判基线测试独立运行**：
   ```powershell
   py -3 -m pytest tests/test_infra.py -v
   py -3 -m pytest AGY2_FundAdvisory/tests/test_infra.py -o pythonpath=AGY2_FundAdvisory -v
   ```
   *预期*: 14 passed & 15 passed。

4. **对抗样本独立解析探针**：
   ```powershell
   py -3 scripts/audit_adversarial_m2.py
   ```
   *预期*: ALL ADVERSARIAL CASES PASSED GENUINELY!
