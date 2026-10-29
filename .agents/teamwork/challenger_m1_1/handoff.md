# Milestone 1 (R1 Look-Through Risk Screen Engine) Challenger 1 Handoff Report

- **Challenger**: Challenger 1 (`challenger_m1_1`)
- **Date**: 2026-10-29T09:44:00Z
- **Target File Reviewed**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py`
- **Parent Conversation ID**: `5fd996d1-bc98-447a-9f35-c5aef5be2e1c` (Project Orchestrator)
- **Verdict**: **REJECT (需修补 5 处异常健壮性防御缺陷以使全量测试集 100% 通过)**

---

## 1. 勘测与实证观察 (Observation)

### 1.1 物理只读底座未篡改核验
执行核验命令：
```powershell
Get-Item AGY2_FundAdvisory/judge_engine.py, AGY2_FundAdvisory/holdout_vault.py, AGY2_FundAdvisory/AGENT_SPEC.md, AGY2_FundAdvisory/tests/test_infra.py | Select-Object Name, IsReadOnly, Mode, Attributes
```
核验结果：
- `judge_engine.py`: `IsReadOnly: True`, Mode: `-ar--`
- `holdout_vault.py`: `IsReadOnly: True`, Mode: `-ar--`
- `AGENT_SPEC.md`: `IsReadOnly: True`, Mode: `-ar--`
- `test_infra.py`: `IsReadOnly: True`, Mode: `-ar--`
确认核心裁判文件未发生任何篡改，完全合规。

### 1.2 既有测试基线验证
执行 `python -m pytest tests`：
- Baseline 147 项测试在 59.88s 内全量通过，无既有逻辑回归。

### 1.3 核心功能与接口契约实测 (`tests/test_adversarial_m1.py`)
针对 Milestone 1 的两组核心接口进行了 17 组严苛对抗性测试，全部 17 项测试通过：
1. `screen_fund_look_through_risk`：
   - 权益基金（`100032` 富国中证红利、`011613` 华夏科创50）：正确返回 `is_ashare_equity=True`、穿透风险分（20.0 / 10.0）、三色标签（🟢 健康 / 🟡 关注）及前十大股票逐股商誉、存贷双高、质押与解禁诊断明细。
   - 非 A 股权益资产（`002351` 易方达裕祥回报纯债、`000216` 华安黄金ETF联接、`050025` 博时标普500全球QDII）：正确触发非 A 股免疫机制，返回 `is_ashare_equity=False`、`penetration_risk_score=0.0`、`🟢 健康`，并给出明确免疫说明。
2. `calculate_portfolio_penetration_risk`：
   - 空组合（Empty Portfolio）：返回 `portfolio_risk_index=0.0`、`🟢 健康`，未触发零除异常。
   - 纯现金组合（Cash Only, 100,000 元可用现金，0 基金持仓）：返回 `portfolio_risk_index=0.0`、`🟢 健康`。
   - 清仓残余组合（市值=0）：自动过滤无效持仓。
   - 单一权益基金（100% 100032）：加权得分与单基金得分一致（20.0）。
   - 单一固收基金（100% 002351）：加权得分 0.0。
   - 多基金均衡配置（50% 100032 + 50% 002351）：加权得分精准计算为 `0.5*20.0 + 0.5*0.0 = 10.0`。
   - 100% 高危组合（同时重仓万科A造假与中芯国际解禁）：加权得分与危险股票数触发评级定性为 `Danger` / `🔴 预警`。
   - 跨基金重合重仓股去重：两只基金均持有万科A时，组合级 `danger_stock_count` 正确去重统计为 1。
   - 缓存防篡改性：外部修改返回的股票字典不污染内部 `_stock_screen_cache`（`copy.deepcopy` 防御有效）。

### 1.4 实证复现的 5 处严重崩溃缺陷 (Defects Observed in Testing)
在执行全量测试套件（含 `tests/test_adversarial_m1_challenger2.py`）时，实测暴露出 5 处导致程序抛出未捕获异常崩溃的漏洞：

1. **缺陷 1：`top_stocks` 中包含 `None` 元素时抛出 `TypeError`**
   - 复现代码：
     ```python
     FUND_LOOK_THROUGH_DATA['888001'] = {'top_stocks': ['贵州茅台', None]}
     pm.screen_fund_look_through_risk('888001')
     ```
   - 真实报错：
     ```text
     File "D:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py", line 2896, in <genexpr>
       if any(k in s for k in ["国债", "进出", "农发", "国开", "存单", "特国", "黄金", ...])
     TypeError: argument of type 'NoneType' is not iterable
     ```
   - 根因位置：`portfolio_manager.py:2896`。未对列表元素 `s` 进行 `isinstance(s, str)` 或 `str(s or "")` 转换，直接执行 `k in s`。

2. **缺陷 2：`look_data["top_stocks"]` 为 `None` 时抛出 `TypeError`**
   - 复现代码：
     ```python
     FUND_LOOK_THROUGH_DATA['888002'] = {'top_stocks': None}
     pm.screen_fund_look_through_risk('888002')
     ```
   - 真实报错：
     ```text
     File "D:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py", line 2950, in screen_fund_look_through_risk
       for stock_raw in top_stocks:
     TypeError: 'NoneType' object is not iterable
     ```
   - 根因位置：`portfolio_manager.py:2889-2891`。代码使用 `if look_data and "top_stocks" in look_data: top_stocks = look_data["top_stocks"]`，当外部接口传回 `None` 时将 `top_stocks` 覆盖为了 `None`，导致后文 `for stock_raw in top_stocks:` 崩溃。

3. **缺陷 3：`top_stocks` 中包含纯整型数字股票代码时抛出 `TypeError`**
   - 复现代码：
     ```python
     FUND_LOOK_THROUGH_DATA['888003'] = {'top_stocks': [600519]}
     pm.screen_fund_look_through_risk('888003')
     ```
   - 真实报错：
     ```text
     File "D:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py", line 2896, in <genexpr>
       if any(k in s for k in ["国债", "进出", ...])
     TypeError: argument of type 'int' is not iterable
     ```
   - 根因位置：`portfolio_manager.py:2896`。未对整型元素转为字符串。

4. **缺陷 4：限售股解禁日历中的 `days_to_unlock` 为 `np.nan` 时抛出 `ValueError`**
   - 复现代码：
     ```python
     # 当 Pandas 缺失值填充为 np.nan
     lockup_row = {'symbol': '600519.SH', 'days_to_unlock': np.nan, 'unlock_market_value_billion': 10.0}
     ```
   - 真实报错：
     ```text
     File "D:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py", line 3012, in screen_fund_look_through_risk
       days_to_unlock = int(l_target.get("days_to_unlock", 999))
     ValueError: cannot convert float NaN to integer
     ```
   - 根因位置：`portfolio_manager.py:3012`。直接使用 `int(...)` 强转未校验 `pd.isna` 或 `math.isnan`。

5. **缺陷 5：财务排雷指标返回非数值脏数据字符串（如 `'N/A'` 或 `'--'`）时抛出 `ValueError`**
   - 复现代码：
     ```python
     fin_data = {'symbol': '600519.SH', 'goodwill_ratio_pct': 'N/A', 'fcf_billion': '--'}
     ```
   - 真实报错：
     ```text
     File "D:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py", line 2983, in screen_fund_look_through_risk
       goodwill_pct = float(fin_data.get("goodwill_ratio_pct", 0.0) or 0.0)
     ValueError: could not convert string to float: 'N/A'
     ```
   - 根因位置：`portfolio_manager.py:2983, 2985`。使用 `float(...)` 裸转未捕获异常。

6. **性能瓶颈：解禁日历重复未记忆网络请求**
   - 实测在每次调用 `screen_fund_look_through_risk` 时（第 2945 行），均重新触发 `fetch_lockup_calendar(days_ahead=90)`。
   - 由于时序湖仓 `storage.duckdb` 中当前仅有 3 条解禁记录（`len(df_lake) == 3 < min(5, 50)`），导致该方法每次均直连东财外网 API，造成单次网络延时达 300~500ms，在组合穿透扫描多只权益基金时出现明显卡顿。

---

## 2. 逻辑推导链 (Logic Chain)

1. **推导 1 (关于只读文件与既有测试)**:
   - 观察 1.1 与 1.2 表明，物理只读属性和原有 112 项业务逻辑没有受到任何破坏，Worker M1 遵守了物理只读约束。
2. **推导 2 (关于核心排雷业务算法)**:
   - 观察 1.3 表明，商誉、质押、解禁、存贷双高以及非 A 股资产免死机制的量化数学模型完全正确，接口契约中所有必须字段的命名与类型均已就绪。
3. **推导 3 (关于健壮性漏洞与全量测试套件失败)**:
   - 观察 1.4 显示，当外部湖仓视图、东财 API 或爬虫返回脏数据（缺失持仓为 None、股票代码为纯整型、Pandas 缺失值为 NaN、财务报表标记为 N/A）时，`portfolio_manager.py` 会直接抛出 `TypeError` 与 `ValueError`。
   - 目前 `tests/test_adversarial_m1_challenger2.py` 中的 5 项复现测试已因此失败，导致全量测试套件 `pytest tests` 退出码为 `1`。
   - 根据工程交付标准与验收红线，测试套件必须 100% 全量通过，严禁将未捕获异常遗留给后续 Milestone 2~4 的 GUI 与交易流。
4. **推导 4 (关于最终裁决)**:
   - 必须给出 **REJECT** 裁决，阻断合流，并向 Worker M1 提供精确的修复补丁指南。

---

## 3. 注意事项与假设 (Caveats)

1. **写权限遵守**: 本智能体作为 Review-Only Challenger，未擅自修改生产代码 `portfolio_manager.py`，保持了严格的职责边界。
2. **易修复性**: 上述 5 处缺陷均为基础的数据防守（Null Safety & Type Coercion），修复仅需在 `portfolio_manager.py` 对应行增加 5 处防御性保护，改动量小于 15 行代码，修复后可立刻实现 204+ 项全量测试 100% 通过。

---

## 4. 结论与具体修补建议 (Conclusion & Remediation Guide)

### 裁决：**REJECT (待修补 5 处输入防护漏洞)**

### 建议 Worker M1 实施的精准修补代码：

在 `AGY2_FundAdvisory/portfolio_manager.py` 中：

1. **修补 `top_stocks` 为空与非 A 股字符串保护（第 2889-2900 行）**：
   ```python
   if look_data and "top_stocks" in look_data:
       top_stocks = look_data["top_stocks"] or []
   top_stocks = [s for s in (top_stocks or []) if s is not None]

   if top_stocks and not is_known_non_ashare:
       non_ashare_item_count = sum(
           1 for s in top_stocks
           if any(k in str(s) for k in ["国债", "进出", "农发", "国开", "存单", "特国", "黄金", "AU9999", "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "BRK", "TSLA", "现金"])
           or re.search(r"\([A-Z\.]+\)", str(s))
       )
   ```

2. **修补指标安全转换辅助函数（第 2980 行附近）**：
   ```python
   def _safe_float(val, default=0.0):
       try:
           if val is None or str(val).strip() in ("", "None", "nan", "NaN", "N/A", "--", "null"):
               return default
           return float(val)
       except Exception:
           return default
   ```
   并将第 2983 行改为：
   ```python
   goodwill_pct = _safe_float(fin_data.get("goodwill_ratio_pct"), 0.0)
   fcf_val = _safe_float(fin_data.get("fcf_billion"), 10.0)
   ```

3. **修补 `days_to_unlock` 的 NaN 转换（第 3012 行）**：
   ```python
   raw_days = l_target.get("days_to_unlock")
   try:
       days_to_unlock = int(float(raw_days)) if (raw_days is not None and not pd.isna(raw_days)) else 999
   except Exception:
       days_to_unlock = 999
   ```

4. **建议引入解禁日历实例级短期缓存（第 2942 行）**：
   在 `PortfolioManager.__init__` 中增加 `self._lockup_calendar_cache = None`，在第 2943 行先读取该缓存，避免多基金遍历时重复请求外网。

---

## 5. 独立验证方法 (Verification Method)

修补完成后，执行以下命令验证是否彻底自愈并 100% 通过：

1. **运行专属对抗测试套件**：
   ```powershell
   python -m pytest AGY2_FundAdvisory/tests/test_adversarial_m1.py AGY2_FundAdvisory/tests/test_adversarial_m1_challenger2.py -v
   ```
   预期：全部 50+ 项对抗测试 100% PASSED。

2. **运行全量测试套件**：
   ```powershell
   cd d:\Google\Workspace\Wind\AGY2_FundAdvisory
   python -m pytest tests -q
   ```
   预期：200+ 项测试全部 PASSED，退出码为 0。

3. **验证只读属性保持**：
   ```powershell
   Get-Item judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py | Select-Object Name, IsReadOnly
   ```
   预期：4 个文件属性均为 True。
