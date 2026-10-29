# Milestone 1 (R1 Look-Through Risk Screen Engine) Adversarial Challenge Report

- **Challenger**: Challenger 2 (`challenger_m1_2`)
- **Date**: 2026-10-29T09:41:00Z
- **Target File Reviewed**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py`
- **Parent Conversation ID**: `5fd996d1-bc98-447a-9f35-c5aef5be2e1c` (Project Orchestrator)
- **Verdict**: **REJECT** (发现 5 项未捕获运行时异常崩溃缺陷，阻断生产级极端/脏数据高可用)

---

## 1. 勘测与实验观察 (Observation)

本智能体编写并运行了端到端对抗压力测试套件 `AGY2_FundAdvisory/tests/test_adversarial_m1_challenger2.py`（共计 40 项严苛测试），并直接针对生产代码 `portfolio_manager.py` 执行了边界极值与异常数据注入。

### 1.1 缺陷 1：`top_stocks` 中存在 `None` 项时引发未捕获 `TypeError`
- **文件与行号**：`AGY2_FundAdvisory/portfolio_manager.py:2893-2898`
- **源代码**：
  ```python
  2893: if top_stocks and not is_known_non_ashare:
  2894:     non_ashare_item_count = sum(
  2895:         1 for s in top_stocks
  2896:         if any(k in s for k in ["国债", "进出", "农发", "国开", "存单", "特国", "黄金", "AU9999", "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "BRK", "TSLA", "现金"])
  2897:         or re.search(r"\([A-Z\.]+\)", s)
  2898:     )
  ```
- **复现用例与命令**：
  ```python
  FUND_LOOK_THROUGH_DATA['999888'] = {'top_stocks': ['贵州茅台', None, '宁德时代']}
  pm.screen_fund_look_through_risk('999888')
  ```
- **实际异常输出 (Verbatim Error)**：
  ```text
  TypeError: argument of type 'NoneType' is not iterable
  AGY2_FundAdvisory\portfolio_manager.py:2896: in <genexpr>
      if any(k in s for k in ["国债", "进出", ...])
  ```

---

### 1.2 缺陷 2：`look_data['top_stocks']` 为 `None` 时引发未捕获 `TypeError`
- **文件与行号**：`AGY2_FundAdvisory/portfolio_manager.py:2884, 2890, 2950`
- **源代码**：
  ```python
  2884: top_stocks = []
  2885: look_data = FUND_LOOK_THROUGH_DATA.get(code)
  2886: if not look_data or "top_stocks" not in look_data:
  2887:     look_data = self._fetch_external_fund_holdings(code)
  2888: 
  2889: if look_data and "top_stocks" in look_data:
  2890:     top_stocks = look_data["top_stocks"]
  ...
  2950: for stock_raw in top_stocks:
  ```
- **复现用例与命令**：
  ```python
  FUND_LOOK_THROUGH_DATA['999885'] = {'top_stocks': None}
  pm.screen_fund_look_through_risk('999885')
  ```
- **实际异常输出 (Verbatim Error)**：
  ```text
  TypeError: 'NoneType' object is not iterable
  AGY2_FundAdvisory\portfolio_manager.py:2950: in screen_fund_look_through_risk
      for stock_raw in top_stocks:
  ```

---

### 1.3 缺陷 3：`top_stocks` 中存在纯数字代码（如整数 `600519`）时引发未捕获 `TypeError`
- **文件与行号**：`AGY2_FundAdvisory/portfolio_manager.py:2896`
- **复现用例与命令**：
  ```python
  FUND_LOOK_THROUGH_DATA['999884'] = {'top_stocks': [600519, 300750]}
  pm.screen_fund_look_through_risk('999884')
  ```
- **实际异常输出 (Verbatim Error)**：
  ```text
  TypeError: argument of type 'int' is not iterable
  AGY2_FundAdvisory\portfolio_manager.py:2896: in <genexpr>
      if any(k in s for k in ["国债", "进出", ...])
  ```

---

### 1.4 缺陷 4：解禁日历 `days_to_unlock` 为 `np.nan` 时引发未捕获 `ValueError`
- **文件与行号**：`AGY2_FundAdvisory/portfolio_manager.py:3012`
- **源代码**：
  ```python
  3012: days_to_unlock = int(l_target.get("days_to_unlock", 999))
  ```
- **复现用例与命令**：
  ```python
  pm.toolkit.holder_risk.fetch_lockup_calendar = lambda days_ahead=90: pd.DataFrame([{
      'symbol': '600519.SH',
      'days_to_unlock': np.nan,
      'unlock_market_value_billion': 10.0,
      'unlock_ratio_total_pct': 5.0,
      'risk_level': 'Medium'
  }])
  pm.screen_fund_look_through_risk('100032')
  ```
- **实际异常输出 (Verbatim Error)**：
  ```text
  ValueError: cannot convert float NaN to integer
  AGY2_FundAdvisory\portfolio_manager.py:3012: in screen_fund_look_through_risk
      days_to_unlock = int(l_target.get("days_to_unlock", 999))
  ```

---

### 1.5 缺陷 5：财务排雷指标返回非数值字符（如 `'N/A'`、`'--'`）时引发未捕获 `ValueError`
- **文件与行号**：`AGY2_FundAdvisory/portfolio_manager.py:2983, 2985, 2996`
- **源代码**：
  ```python
  2983: goodwill_pct = float(fin_data.get("goodwill_ratio_pct", 0.0) or 0.0)
  2985: fcf_val = float(fin_data.get("fcf_billion", 10.0) if fin_data.get("fcf_billion") is not None else 10.0)
  2996: pledge_ctrl_pct = float(r_target.get("pledge_ratio_controlling_pct", 0.0) or 0.0)
  ```
- **复现用例与命令**：
  ```python
  pm.toolkit.earnings_forecast.screen_financial_risks = lambda s: {
      'symbol': s,
      'goodwill_ratio_pct': 'N/A',
      'double_high_risk': False,
      'fcf_billion': '--'
  }
  pm.screen_fund_look_through_risk('100032')
  ```
- **实际异常输出 (Verbatim Error)**：
  ```text
  ValueError: could not convert string to float: 'N/A'
  AGY2_FundAdvisory\portfolio_manager.py:2983: in screen_fund_look_through_risk
      goodwill_pct = float(fin_data.get("goodwill_ratio_pct", 0.0) or 0.0)
  ```

---

### 1.6 成功验证与通过项
以下项目在对抗测试中表现完全合规且健壮：
1. **未知与畸形基金代码输入**：传入 `""`、`"   "`、`"INVALID"`、`"ABC123"`、`None`、`100032`、`"-1"` 等，均未抛出任何未捕获异常，安全返回合规字典结构；
2. **商誉扣分数学分界线**：在孤立环境下验证，$gw \le 30.0\%$ 扣 0 分；$30.01\% \sim 40.0\%$ 精确扣 30 分；$> 40.0\%$ 精确扣 40 分；
3. **控股股东质押分界线**：$pledge \le 50.0\%$ 扣 0 分；$50.0\% \sim 80.0\%$ 扣 15 分；$> 80.0\%$ 扣 35 分；平仓线与预警线状态覆写精准生效；
4. **存贷双高标准测试**：货币资金 $\ge 100$ 亿、有息负债 $\ge 150$ 亿、负债/现金 $\ge 1.2$ 三重交集判定准确；
5. **纯非 A 股免疫机制**：全纯债与黄金组合计算组合穿透风险分恒为 0.0，三色徽章为 `🟢 健康`；
6. **离线高可用容灾**：网络连接超时与断网模拟下，平滑降级至本地湖仓与离线模型，无未捕获异常；
7. **缓存隔离与防外部篡改**：外部修改返回对象不会污染 `_stock_screen_cache` 内存池。

---

## 2. 逻辑推导链 (Logic Chain)

1. **从观察 1.1 / 1.3 到推导**：
   - 在第 2895-2897 行，代码使用 `for s in top_stocks: if any(k in s for k in ...)`。在 Python 中，当 `s` 为 `None` 或整数 `int` 时，操作符 `k in s` 直接触发 `TypeError`。
   - 由于外部基金重仓股解析（`_fetch_external_fund_holdings`）或外部持仓湖仓中存在空值或纯数字类型，该未防护的循环会直接导致前端与投顾计算链路崩溃。
2. **从观察 1.2 到推导**：
   - 在第 2890 行，`top_stocks = look_data["top_stocks"]`，若外部字典值为 `None`，则变量 `top_stocks` 被赋值为 `None`。
   - 随后的第 2950 行 `for stock_raw in top_stocks:` 未做非空兜底，导致对 `None` 执行迭代引发 `TypeError: 'NoneType' object is not iterable`。
3. **从观察 1.4 到推导**：
   - Pandas 在处理缺失数值列时，默认将缺失项填充为 `np.nan`（浮点型 NaN）。
   - 在第 3012 行，直接执行 `int(l_target.get("days_to_unlock", 999))` 时，若该字段值为 `np.nan`，Python 原生 `int(float('nan'))` 必然抛出 `ValueError`。
4. **从观察 1.5 到推导**：
   - 外部网络 API 或本地 CSV/Parquet 导入时，部分上市公司未披露字段常表示为 `'N/A'` 或 `'--'`。
   - 第 2983、2985、2996 行直接采用 `float(...)` 进行强转，一旦遇到非数值字符串立即崩溃，违背了“无任何未捕获异常抛出”与“离线鲁棒降级”的硬性要求。
5. **从所有观察到结论**：
   - 鉴于以上 5 处未捕获异常均可在特定真实边界数据下稳定复现并造成系统崩溃，本 Milestone 1 交付物未能完全满足鲁棒性与异常防护标准，必须判定为 **REJECT**，由 Worker M1 实施自愈修复。

---

## 3. 注意事项与假设 (Caveats)

- **只读审阅边界**：根据智能体角色约束，Challenger 严格保持 review-only，绝不擅自修改 `portfolio_manager.py` 生产代码。
- **测试代码规范**：所有对抗性测试均放置于合规目录 `AGY2_FundAdvisory/tests/test_adversarial_m1_challenger2.py` 中，未在 `.agents/teamwork/` 下遗留任何源码或测试代码。

---

## 4. 结论与修复指引 (Conclusion & Actionable Fixes)

**判定结果**: **REJECT**

建议 Worker M1 实施以下 4 处针对性补丁：

### 修复指引 1：安全浮点/整型解析辅助函数
在 `portfolio_manager.py` 的工具函数区添加：
```python
def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        if val is None or pd.isna(val):
            return default
        return float(val)
    except Exception:
        return default
```

### 修复指引 2：`top_stocks` 提取与非空兜底 (第 2889-2890 行)
```python
if look_data and "top_stocks" in look_data and look_data["top_stocks"] is not None:
    top_stocks = look_data["top_stocks"]
else:
    top_stocks = []
```

### 修复指引 3：非 A 股资产特征判定防崩保护 (第 2893-2901 行)
```python
if top_stocks and not is_known_non_ashare:
    non_ashare_item_count = sum(
        1 for s in top_stocks
        if s and (any(k in str(s) for k in ["国债", "进出", "农发", "国开", "存单", "特国", "黄金", "AU9999", "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "BRK", "TSLA", "现金"])
        or re.search(r"\([A-Z\.]+\)", str(s)))
    )
    if non_ashare_item_count >= max(1, int(len(top_stocks) * 0.5)):
        is_known_non_ashare = True
```

### 修复指引 4：财务与解禁数值解析安全保护 (第 2983-3015 行)
```python
goodwill_pct = _safe_float(fin_data.get("goodwill_ratio_pct"), 0.0)
double_high = bool(fin_data.get("double_high_risk", False))
fcf_val = _safe_float(fin_data.get("fcf_billion"), 10.0)
pledge_ctrl_pct = _safe_float(r_target.get("pledge_ratio_controlling_pct"), 0.0)

raw_days = l_target.get("days_to_unlock")
days_to_unlock = int(_safe_float(raw_days, 999)) if raw_days is not None and not pd.isna(raw_days) else None
unlock_val = _safe_float(l_target.get("unlock_market_value_billion"), 0.0)
unlock_ratio = _safe_float(l_target.get("unlock_ratio_total_pct"), 0.0)
```

---

## 5. 独立复现与验证方法 (Verification Method)

执行以下命令直接复现 5 大缺陷：

```powershell
python -m pytest AGY2_FundAdvisory/tests/test_adversarial_m1_challenger2.py -v -k "test_defect_reproduction"
```

预期结果：在修复前，5 项复现用例 100% 报错失败（3 项 `TypeError`，2 项 `ValueError`）。修复后，该 5 项用例及全部 40 项用例应 100% 全绿通过。
