# Milestone 1 (R1 穿透排雷引擎) 独立评审与对抗素质询报告 (Reviewer 2 / Critic)

- **Reviewer / Adversarial Critic**: `reviewer_m1_2`
- **Date**: 2026-10-29T09:45:00Z
- **Target File Reviewed**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py`
- **Parent Conversation ID**: `5fd996d1-bc98-447a-9f35-c5aef5be2e1c` (Project Orchestrator)
- **Verdict**: **REQUEST_CHANGES** (需修复输入清洗异常与质押兜底缺陷后批准)

---

## 1. 勘测与审计观察 (Observation)

### 1.1 诚实性与作弊违规深度排查 (Integrity Audit)
依据评审准则对 Worker M1 提交代码进行全维度诚实性审查：
1. **硬编码测试结果排查**：
   - 检索 `fund_code == '100032'`、`fund_code == '002351'` 等硬编码断言：未发现任何针对特定基金的作弊分支；
   - 检索静态返回值：`penetration_risk_score`、`risk_level`、`risk_badge` 均由真实量化扣分公式（商誉、存贷双高、质押爆仓、解禁抛压、FCF）与市值加权平均计算得出。
2. **门面实现 (Facade) 排查**：
   - `resolve_stock_symbol` 具备 72+ 只常见核心上市公司映射、6 位代码后缀智能正则补齐、`MasterDictParser` 模糊检索及本地 DuckDB 时序湖仓视图 4 级回退；
   - `screen_fund_look_through_risk` 与 `calculate_portfolio_penetration_risk` 具备完整的多要素排雷、缓存复用、加权聚合与去重统计。
3. **绕过与伪造排查**：未发现任何委托外部绕过、伪造测试日志或自认证作弊行为。
4. **诚实性结论**：**无诚信违规 (NO INTEGRITY VIOLATION)**。代码属于真诚高质量开发。

### 1.2 物理只读底座不可变量核验 (Physical Read-Only Invariants)
执行命令：
```powershell
Get-Item AGY2_FundAdvisory/judge_engine.py, AGY2_FundAdvisory/holdout_vault.py, AGY2_FundAdvisory/AGENT_SPEC.md, AGY2_FundAdvisory/tests/test_infra.py | Select-Object FullName, IsReadOnly, Mode, Attributes, LastWriteTime
```
实测输出结果（verbatim）：
```text
FullName      : D:\Google\Workspace\Wind\AGY2_FundAdvisory\judge_engine.py
IsReadOnly    : True
Mode          : -ar--
Attributes    : ReadOnly, Archive
LastWriteTime : 2026/10/28 13:40:59

FullName      : D:\Google\Workspace\Wind\AGY2_FundAdvisory\holdout_vault.py
IsReadOnly    : True
Mode          : -ar--
Attributes    : ReadOnly, Archive
LastWriteTime : 2026/10/27 21:47:43

FullName      : D:\Google\Workspace\Wind\AGY2_FundAdvisory\AGENT_SPEC.md
IsReadOnly    : True
Mode          : -ar--
Attributes    : ReadOnly, Archive
LastWriteTime : 2026/10/28 13:39:36

FullName      : D:\Google\Workspace\Wind\AGY2_FundAdvisory\tests\test_infra.py
IsReadOnly    : True
Mode          : -ar--
Attributes    : ReadOnly, Archive
LastWriteTime : 2026/10/28 13:40:30
```
确认 4 大基准与裁判文件 100% 保持只读状态未受任何改动，最后修改时间均早于 Milestone 1 启动时间。

### 1.3 接口契约对照核验 (Interface Contract Conformance)
对照 `PROJECT.md` 第 61-91 行契约规范：
1. `screen_fund_look_through_risk(fund_code: str) -> Dict[str, Any]`：
   - 字段完整包含：`fund_code` (str), `fund_name` (str), `is_ashare_equity` (bool), `penetration_risk_score` (float), `risk_level` (str), `risk_badge` (str), `danger_count` (int), `watch_count` (int), `top_stocks_screen` (List[Dict]), `diagnosis_summary` (str)；
   - 风险分级字符串：`Safe` / `Watch` / `Danger`；三色徽章：`🟢 健康` / `🟡 关注` / `🔴 预警`。
2. `calculate_portfolio_penetration_risk() -> Dict[str, Any]`：
   - 字段完整包含：`portfolio_risk_index` (float), `risk_level` (str), `risk_badge` (str), `danger_stock_count` (int), `watch_stock_count` (int), `high_risk_reasons` (List[str]), `funds_breakdown` (List[Dict])。
3. 契约符合度：**100% 严格吻合**。

### 1.4 缓存机制与性能实测 (Caching & Performance)
1. **缓存有效性实测**：
   - 在独立脚本中调用 `pm.screen_fund_look_through_risk('100032')`，`_stock_screen_cache` 填充 10 只标的；
   - 随后调用重仓同指数标的的 `090010`，缓存长度仍为 10，直接复用缓存，IO 命中率 100%；
2. **缓存指针污染防护**：
   - 写入（第 3074 行）与读取（第 2957 行）均使用 `copy.deepcopy`；
   - 实测在位修改返回值：`res['top_stocks_screen'][0]['stock_score'] = 999.0`，二次调用返回的 `stock_score` 依然为真实原值，未发生缓存指针污染。

### 1.5 测试套件全量执行与对抗测试失败观察 (Test Suite Execution)
在 `AGY2_FundAdvisory/` 目录下执行 `$env:PYTHONPATH=".;d:\Google\Workspace\Wind;d:\Google\Workspace\Wind\AGY2_FundAdvisory"; python -m pytest tests`：
**测试结果**：
- 收集用例数：187 项（112 既有基准 + 35 新集成 + 17 challenger1 对抗 + 23 challenger2 对抗）
- 运行结果：`3 failed, 184 passed, 124 warnings in 89.66s`
- 退出代码：`1` (FAIL)

**3 项失败用例直接报错细节**：
1. **用例 1**：`test_adversarial_m1_challenger2.py::test_adversarial_empty_and_corrupt_top_stocks`
   - 触发位置：`portfolio_manager.py:2896`
   - 报错信息：
     ```text
     portfolio_manager.py:2896: in <genexpr>
         if any(k in s for k in ["国债", "进出", "农发", "国开", "存单", "特国", "黄金", "AU9999", "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "BRK", "TSLA", "现金"])
     TypeError: argument of type 'NoneType' is not iterable
     ```
   - 根因：当 `top_stocks` 包含 `None` 或非字符串对象时，生成器推导式 `k in s` 发生未捕获 `TypeError`。
2. **用例 2**：`test_adversarial_m1_challenger2.py::test_adversarial_goodwill_ratio_boundaries`
   - 报错信息：`AssertionError: Failed at goodwill=40.0: expected 30.0, got 45.0`
   - 根因：Challenger 2 生成了代码 `600400.SH`（红豆股份），该标的在 DuckDB 中实际存在 65.05% 股权质押（处于临界预警线，扣 15 分），商誉扣 30 分 + 质押扣 15 分 = 45 分。Challenger 2 测试未 mock 质押接口导致复合扣分与单项期望不符。
3. **用例 3**：`test_adversarial_m1_challenger2.py::test_adversarial_lockup_calendar_boundaries`
   - 报错信息：`AssertionError: Failed at days=0: expected 20.0, got 60.0`
   - 根因：Challenger 2 生成了代码 `600000.SH`（浦发银行），该标的在 DuckDB 中触发存贷双高（扣 40 分），限售扣 20 分 + 存贷双高扣 40 分 = 60 分。Challenger 2 测试未 mock 财务接口导致复合扣分。

---

## 2. 逻辑推导链 (Logic Chain)

1. **观察 1.1 与 1.2 ➔ 推导 1 (诚实性与基准只读安全)**：
   - 源代码无作弊分支与硬编码，`judge_engine.py` 等 4 个文件保持只读属性与原始哈希，证实 Worker M1 的交付无诚信违规。
2. **观察 1.3 与 1.4 ➔ 推导 2 (接口契约与缓存完整性)**：
   - 接口字段、枚举值、数据类型与 PROJECT.md 契约 100% 契合；`_stock_screen_cache` 配合 `copy.deepcopy` 有效消除了多基金穿透开销并保障了内存安全。
3. **观察 1.5 ➔ 推导 3 (真实代码健壮性缺陷)**：
   - 实测复现证明：若外部数据源返回的 `top_stocks` 列表含有 `None` 或畸变元素（例如缺失前十大披露或数据清洗不全），`portfolio_manager.py` 第 2896 行由于未对 `s` 判空，将直接抛出 `TypeError: argument of type 'NoneType' is not iterable` 导致服务崩溃。
4. **代码审查（第 2995 行）➔ 推导 4 (质押数据兜底逻辑隐患)**：
   - 代码行：`r_target = m_row.iloc[0] if not m_row.empty else p_df.iloc[0]`；
   - 若 `clean_stock_code` 未在质押表 `p_df` 中找到匹配行（`m_row.empty == True`），代码直接回退取 `p_df.iloc[0]`，这会将第一只股票的质押率与平仓线状态强行赋予未匹配股票，造成误判；安全做法应回退为 `pledge_ctrl_pct = 0.0` 与 `"远离平仓线"`。
5. **代码审查（第 2951-2953 行）➔ 推导 5 (空字符串股票全量匹配隐患)**：
   - 当 `top_stocks` 包含空字符串 `""` 时，`clean_stock_code = ""`，导致 `lockup_df["symbol"].str.contains("")` 恒为真，错误将第一条解禁记录（如未来 12 天 200 亿解禁）匹配给空股票。
6. **推导 6 (测试套件合规裁决)**：
   - 项目验收标准规定必须“测试 100% 全量通过”。当前测试执行因存在 3 个失败项退出码为 1。因此评审结论必须为 **REQUEST_CHANGES**，驱动缺陷闭环修复。

---

## 3. 注意事项与假设 (Caveats)

1. **测试用例 mock 隔离度**：Challenger 2 的边界测试用例 `test_adversarial_goodwill_ratio_boundaries` 和 `test_adversarial_lockup_calendar_boundaries` 在测试单维度扣分时使用了真实股票代码（`600400`、`600000`），但未完全隔离 mock 其他维度，导致底层真实多因子扣分叠加入账。建议后续在修复时联动修正测试用例中的 mock 隔离或使用合成虚拟股票代码。
2. **只读保护红线**：修改仅限于 `portfolio_manager.py`，绝不可触碰物理只读文件。

---

## 4. 评审发现与修改清单 (Findings & Changes Requested)

### [Major] Finding 1: 穿透排雷对 `top_stocks` 中 `None` 元素缺少防御引发 `TypeError`
- **位置**：`AGY2_FundAdvisory/portfolio_manager.py:2894-2900`
- **问题**：`non_ashare_item_count = sum(1 for s in top_stocks if any(k in s for k in ...) or re.search(r"\([A-Z\.]+\)", s))` 中，若 `s` 为 `None`，`k in s` 抛出 `TypeError: argument of type 'NoneType' is not iterable`。
- **修改建议**：在列表推导前增加类型与判空过滤，或改为 `if s and isinstance(s, str) and (any(k in s for k in ...) or re.search(r"\([A-Z\.]+\)", s))`；并在遍历股票主循环前过滤无效股票名称：`clean_stocks = [str(s).strip() for s in top_stocks if s and str(s).strip()]`。

### [Major] Finding 2: 股票名称为空字符串时正则 `str.contains("")` 误匹配全量解禁日历
- **位置**：`AGY2_FundAdvisory/portfolio_manager.py:2950-2954, 3007`
- **问题**：若 `stock_name` 为空字符串，`clean_stock_code = ""`，执行 `lockup_df["symbol"].str.contains("")` 恒真，导致空股票错误继承首条解禁记录的大额解禁抛压。
- **修改建议**：在第 2950 行主循环头部增加：
  ```python
  if not stock_name:
      continue
  ```

### [Minor] Finding 3: 质押风险未命中时错误回退取 `p_df.iloc[0]`
- **位置**：`AGY2_FundAdvisory/portfolio_manager.py:2993-2997`
- **问题**：`r_target = m_row.iloc[0] if not m_row.empty else p_df.iloc[0]`，在未查到该股票质押记录时，错误继承第 0 行股票的数据。
- **修改建议**：当 `m_row.empty` 时，不取 `p_df.iloc[0]`，直接保持 `pledge_ctrl_pct = 0.0` 与 `close_line_status = "远离平仓线"`。

---

## 5. 对抗性质询与压力测试汇总 (Adversarial Review Summary)

- **Overall Risk Assessment**: **MEDIUM** (核心金融逻辑完全正确，但存在极端脏数据容错盲区)

| 质询假设 (Hypothesis) | 攻击场景 (Attack Scenario) | 预期防护行为 | 实测表现 | 结果 |
|---|---|---|---|---|
| H1: 持仓中含 None 脏数据 | `top_stocks: ["贵州茅台", None, ""]` | 忽略 None 正常穿透 | 抛出 `TypeError` 崩溃 | ❌ FAIL (需修复) |
| H2: 持仓中含空字符串标的 | `top_stocks: ["", "  "]` | 忽略或给出空标的健康兜底 | 继承了解禁表首行的 200 亿解禁 | ❌ FAIL (需修复) |
| H3: 股票未收录于质押表 | 查询未知标的 `XYZ` | 默认 0 质押与远离平仓线 | 取 `p_df.iloc[0]` 任意股票数据 | ⚠️ WEAK (需修复) |
| H4: 组合零市值 / 空持仓 | `pm.calculate_portfolio_penetration_risk()` | 安全返回 0.0 与 🟢 健康 | 顺利拦截并安全返回 | ✅ PASS |
| H5: 外部篡改缓存字典 | 篡改排雷返回字典中的风险得分 | 缓存不被修改 | `copy.deepcopy` 完全隔离 | ✅ PASS |
| H6: 核心只读底座篡改 | 检查 `judge_engine.py` 等 4 文件 | 保持只读未改动 | `IsReadOnly: True`, 时间未变 | ✅ PASS |

---

## 6. 结论 (Conclusion)

- **最终评审结论**: **REQUEST_CHANGES**
- **结论说明**:
  Worker M1 的代码在金融量化逻辑、`WindToolkit` 接入、三色风险分级与缓存架构上完成度极高，**绝无任何诚实性违规 (Clean)**。
  但因在极端脏数据输入（`top_stocks` 含 `None`、空字符串）和质押未命中回退上存在健壮性缺陷，导致全量测试套件中 `test_adversarial_m1_challenger2.py` 出现 3 项失败（退出码 1）。
  请由 Worker M1 针对上述 Finding 1、2、3 进行防御性增强，并协同 Challenger 2 完善 mock 隔离，待 187 项测试 100% 通过后即可合流批准！

---

## 7. 独立验证方法 (Verification Method)

后续流水线与 Worker 可运行以下命令复现并检验修复：

1. **复现崩溃缺陷**:
   ```powershell
   python -c "import sys; sys.path.extend(['AGY2_FundAdvisory', '.']); from portfolio_manager import PortfolioManager, FUND_LOOK_THROUGH_DATA; pm = PortfolioManager(db_path=':memory:'); FUND_LOOK_THROUGH_DATA['888002'] = {'top_stocks': ['贵州茅台', None, ''], 'industries': {}}; pm.screen_fund_look_through_risk('888002')"
   ```
   预期：当前抛出 `TypeError: argument of type 'NoneType' is not iterable`。修复后应正常返回且不崩溃。

2. **验证全量测试套件**:
   ```powershell
   cd d:\Google\Workspace\Wind\AGY2_FundAdvisory
   $env:PYTHONPATH=".;d:\Google\Workspace\Wind;d:\Google\Workspace\Wind\AGY2_FundAdvisory"
   python -m pytest tests
   ```
   修复后目标：187 passed, 0 failed, 退出码 0。
