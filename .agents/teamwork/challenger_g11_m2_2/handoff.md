# Adversarial Challenge & Verification Report — Milestone 2: Tab 2 Rebalance Engine

## 1. Observation

Direct code inspections, AST parses, and empirical execution runs were conducted against `AGY2_FundAdvisory/app_gui.py`, `AGY2_FundAdvisory/strategy_bridge.py`, and `AGY2_FundAdvisory/portfolio_manager.py`:

### Observation 1: Buffer Slider Range vs. Backend Boundary Tolerance
- In `AGY2_FundAdvisory/app_gui.py` (lines 5255–5265):
  ```python
  st.slider(
      "🛡️ 免折腾调仓缓冲带 (%)",
      min_value=1.0,
      max_value=5.0,
      value=cur_buf_val,
      step=0.5,
      format="%.1f%%",
      key="tab2_rebal_buf_slider",
      on_change=_sync_tab2_rebal_buffer_change,
      help="控制调仓裁决与温和调仓过滤的最小偏离阈值。低于此阈值的微小偏离将自动维持现状，杜绝无效换仓摩擦"
  )
  ```
  The physical UI widget is restricted to `[1.0%, 5.0%]`, stepping by `0.5%`.
- In `AGY2_FundAdvisory/strategy_bridge.py` (lines 3578–3581, 6302–6303):
  The backend methods `evaluate_today_rebalance_suitability`, `simulate_rebalance_modes_and_consequences`, and `generate_ai_rebalance_orders` dynamically normalize inputs:
  ```python
  raw_b = float(min_buffer_pct) if min_buffer_pct is not None else 3.0
  norm_pct = (raw_b * 100.0) if (0.0 < raw_b <= 0.5) else raw_b
  norm_ratio = (raw_b / 100.0) if raw_b > 0.5 else raw_b
  ```
  Empirical stress testing with buffer values `[0.0, 0.005, 0.01, 0.03, 0.05, 0.10]` and `[0.0, 1.0, 3.0, 5.0, 10.0]` all executed without error.
  However, in `app_gui.py` line 5249:
  `cur_buf_val = float(st.session_state.get("rebalance_buffer_pct", 3.0))`
  If `st.session_state.rebalance_buffer_pct` is set to `< 1.0` or `> 5.0` (e.g. from an external preset), Streamlit's `st.slider` raises a value-out-of-bounds error unless clamped.

### Observation 2: Diagnosis Trigger Under Edge Portfolios
- **Empty portfolio (`pm.holdings = {}`, `total_equity = 0.0`)**:
  - `pm.calculate_portfolio_cushion_and_stress_model` returned `comprehensive_cushion = 0.0`, `portfolio_weighted_beta = 0.0`, `is_in_floating_loss = False` with zero `ZeroDivisionError`.
  - In `strategy_bridge.py` line 6235:
    `devs = [abs(target_weights.get(c, 0.0) - cur_w.get(c, 0.0)) for c in all_codes]`
    Because `cur_w` is `{}` when total equity is 0, `d_max` computes to `max(target_weights) = 0.38` (38.0%).
    Consequently, `StrategyBridge.evaluate_today_rebalance_suitability` outputs `verdict_level = "SUITABLE"` ("今日适合调仓") and the UI renders `偏离度: 38.0%` for a completely empty portfolio.
- **Cash-only portfolio (`pm.holdings = {}`, `available_cash = 100,000.0`)**:
  - All generated rebalance orders had `diff_amount > 0` (buy-only), `redemption_fee = 0.0`, and `penalty_fee_7d = 0.0`.
- **All locked funds under 7 days (`holding_days = 2`)**:
  - Gentle mode strictly respected `penalty_fee_7d = 0.0` and did not sell locked shares.
  - Forced mode calculated positive penalty fee `penalty_fee_7d > 0.0`.
- **High correlation portfolio (`011613`, `008888`, `013402`, correlation > 0.85)**:
  - Diagnosis executed smoothly, recommending rebalancing towards pure bond shield `002351` and gold hedge `000216`.

### Observation 3: Critical Bug in One-Click Follow Execution (`btn_confirm_follow_rebalance_tab2`)
- In `AGY2_FundAdvisory/app_gui.py` (lines 5567–5573):
  ```python
  elif diff_amt > 100 or "加仓" in action_raw:
      op_action = "➕ 建议加仓"
      op_point = f"增配¥{abs(diff_amt):,.0f}·现金分红"
  elif diff_amt < -100 or "减仓" in action_raw:
      op_action = "➖ 建议减仓"
      op_point = f"减配¥{abs(diff_amt):,.0f}·阶梯退出"
  ```
- When the user clicks `btn_confirm_follow_rebalance_tab2` (line 5730):
  ```python
  up_cnt = pm.apply_rebalance_orders_to_holdings(rows_display)
  ```
- In `AGY2_FundAdvisory/portfolio_manager.py` (lines 6965–6989):
  ```python
  if "清仓" in action_desc:
      self.delete_holding(fcode)
      self.available_cash += float(cur_h.market_value if cur_h else 0.0)
      updated_count += 1
  elif "减持" in action_desc and cur_h:
      sell_amt = min(abs(amt_chg), float(cur_h.market_value))
      ...
      updated_count += 1
  elif "增持" in action_desc or "建仓" in action_desc or "买入" in action_desc:
      buy_amt = abs(amt_chg)
      ...
      updated_count += 1
  ```
- **Verbatim Empirical Test Result (`test_adversarial_apply_rebalance_string_matching_bug`)**:
  ```python
  app_gui_rows = [
      {"基金代码": "005561", "建议操作": "➖ 建议减仓", "建议调仓金额(元)": -5000.0},
      {"基金代码": "002351", "建议操作": "➕ 建议加仓", "建议调仓金额(元)": 8000.0}
  ]
  unfixed_count = clean_pm.apply_rebalance_orders_to_holdings(app_gui_rows)
  assert unfixed_count == 0  # PASSED: 0 orders applied!
  ```
  `"建议减仓"` contains `"减仓"`, NOT `"减持"`.
  `"建议加仓"` contains `"加仓"`, NOT `"增持"`, `"建仓"`, or `"买入"`.
  Therefore, all standard buy and sell recommendations are **silently ignored** by `apply_rebalance_orders_to_holdings`. The user is shown `🎉 成功同步！已将 0 笔调仓执行单记账入库`, and no portfolio holdings are actually modified!

### Observation 4: Orders Table & VWAP Schedule Math
- `df_orders_tbl` adheres strictly to the 10-column specification:
  `["基金代码", "基金名称", "份额", "当前市值(元)", "目标占比(%)", "实时估值涨跌(%)", "建议调仓金额(元)", "建议操作", "尾盘微观优化(bps)", "实操要点"]`
- `SmartExecutionDCAEngine.calculate_vwap_execution_slippage` generates 5 discrete slices with keys `['phase', 'label', 'vol_ratio', 'slice_amount', 'strategy']`. The sum of `slice_amount` across all 5 slices equals `order_amount` with precision `< 0.02` cents.

### Observation 5: 4-Cell Top Bar and Summary Bar Math Identities
- Merged 4-cell top bar formulas:
  - `_tot_equity == _t2_mkt + available_cash + in_transit_cash` (verified within `1e-4`).
  - `_t2_pnl == _t2_mkt - _t2_cost` (verified within `1e-4`).
  - `_pos_pct == (_t2_mkt / _tot_equity * 100.0)` with zero-division guard when `_tot_equity == 0`.
- Summary bar formulas:
  - `total_fee == round(redemption_fee + penalty_fee_7d + subscription_fee, 2)`.
  - `equity_after == round(max(0.0, equity_before - total_fee), 2)`.
  - Zero division guards for `total_cost == 0` and `total_equity == 0` operate with 0 math anomalies.

---

## 2. Logic Chain

1. *Boundary Analysis*:
   - The dispatch specified testing the buffer slider from 0.0% to 10.0%.
   - Static AST inspection of `app_gui.py` showed the widget is hard-bounded to `[1.0%, 5.0%]`.
   - Dynamic parameter testing proved that the underlying quantitative engines (`evaluate_today_rebalance_suitability`, `simulate_rebalance_modes_and_consequences`, `generate_ai_rebalance_orders`) gracefully accept 0.0% to 10.0%.
   - Therefore, the quantitative engine is robust across [0.0%, 10.0%], but the UI slider's current physical limit is 1.0%~5.0%. Clamping `cur_buf_val = min(max(cur_buf_val, 1.0), 5.0)` is recommended to avoid any future Streamlit state injection exceptions.
2. *Edge Portfolio Resilience*:
   - Empty, cash-only, 100% locked (<7d), and high-correlation portfolios all executed without fatal crashes.
   - For an empty portfolio (`total_equity == 0.0`), `d_max` defaults to `max(target_weights) = 38%` because `cur_w` is empty, falsely showing a 38% deviation on an empty account. This does not crash the app, but is an advisory inaccuracy.
3. *End-to-End Execution Trace*:
   - When generating rebalance rows, `app_gui.py` labels standard rebalances as `"➕ 建议加仓"` and `"➖ 建议减仓"`.
   - `PortfolioManager.apply_rebalance_orders_to_holdings` filters actions using `if "减持" in action_desc` and `elif "增持" in action_desc or "建仓" in action_desc or "买入" in action_desc`.
   - Because Chinese terminology diverges ("加仓"/"减仓" vs "增持"/"减持"), the string matching conditions evaluate to `False`.
   - As directly verified in test `test_adversarial_apply_rebalance_string_matching_bug`, 0 orders are applied to the ledger upon clicking the follow execution button.

---

## 3. Adversarial Challenge Report

### Overall Risk Assessment: HIGH

| Challenge | Severity | Description | Status |
|-----------|----------|-------------|--------|
| **Challenge 1** | **HIGH** | One-click follow button (`btn_confirm_follow_rebalance_tab2`) fails to update holdings due to string mismatch (`"建议加仓"`/`"建议减仓"` vs `"增持"`/`"减持"`). | **CONFIRMED DEFECT** |
| **Challenge 2** | **MEDIUM** | Empty portfolio (`total_equity == 0`) displays `偏离度: 38.0%` and `🟢 今日适合调仓` instead of suppressing deviation. | **CONFIRMED DEFECT** |
| **Challenge 3** | **LOW** | Slider widget range is `[1.0%, 5.0%]`, while dispatch requested `[0.0%, 10.0%]`. | **BOUNDARY VARIANCE** |
| **Challenge 4** | **LOW** | `cur_buf_val` in `app_gui.py` line 5249 lacks defensive `min(max(..., 1.0), 5.0)` clamping. | **DEFENSIVE LATENCY** |

### Stress Test Results

| Scenario | Expected Behavior | Actual Behavior | Result |
|----------|-------------------|-----------------|--------|
| Buffer `0.0%` to `10.0%` on backend engines | Support without crash, monotonic filtering | Correctly supported and filtered across all 6 test values | **PASS** |
| Slider AST & widget key contracts | Single global slider with key `tab2_rebal_buf_slider` | Verified exactly 1 slider, range 1.0%~5.0% | **PASS** |
| Empty portfolio rebalance diagnosis | Safe execution, zero division immune | Safe execution, but `d_max` reports 38% | **PARTIAL** |
| Cash-only portfolio rebalance diagnosis | Buy-only orders from cash, 0 redemption fee | Correctly generated buy orders from cash pool | **PASS** |
| All locked funds (<7d) rebalance diagnosis | Gentle mode charges 0 penalty fee | Gentle mode `penalty_fee_7d == 0.0` confirmed | **PASS** |
| High correlation portfolio diagnosis | Output valid risk shift, recommend bond/gold hedge | Smooth execution, positive post-rebalance diversification | **PASS** |
| Rebalance Orders Table 10-column schema | Strictly 10 specified columns and dtypes | Exactly 10 columns matching contract | **PASS** |
| VWAP 5-stage slice conservation | Slice sum == order amount (<0.02 error) | Sum strictly conserved, non-negative slippage saved | **PASS** |
| One-click follow execution button | Synchronize buy/sell orders to `pm.holdings` | Silently updates 0 orders due to string mismatch | **FAIL (BUG)** |
| 4-cell top bar math identities | 100% exact parity with sum of holdings | Verified exact equality within 1e-4 | **PASS** |
| 4-cell summary bar consequence math | Fee and risk shift identities hold | Exact equality confirmed, zero NaN/Inf | **PASS** |
| Streamlit AppTest Tab 2 GUI execution | Run full app without exception | Executed cleanly with 0 exceptions | **PASS** |

### Unchallenged Areas
- Tab 1 new capital allocation workflows (assigned to Milestone 1 challenger).
- Tab 3 and Tab 4 backtest and penetration engine details (out of Milestone 2 scope).

---

## 4. Caveats

1. The challenger is strictly operating under a **Review-only** constraint. In accordance with system instructions, the implementation code (`app_gui.py` and `portfolio_manager.py`) was NOT modified by this agent. The bug was isolated and empirically documented with reproduction code.
2. The recommended fix for Challenge 1 is either:
   - In `app_gui.py` lines 5568 and 5571: change `"➕ 建议加仓"` to `"➕ 建议加仓(买入)"` or `"➕ 建议增持"`, and `"➖ 建议减仓"` to `"➖ 建议减持"`.
   - OR in `portfolio_manager.py` line 6969 and 6989: expand the matching keywords to:
     `elif any(k in action_desc for k in ["减持", "减仓", "卖出"]) and cur_h:`
     `elif any(k in action_desc for k in ["增持", "加仓", "建仓", "买入"]):`
3. All tests were executed on Windows 11 with Python 3.11.9.

---

## 5. Conclusion

1. **Overall Verdict**: **CONDITIONAL APPROVAL WITH 1 HIGH-PRIORITY DEFECT TO FIX**.
2. **Passed Dimensions**:
   - The three-block UI refactoring of Tab 2 in `AGY2_FundAdvisory/app_gui.py` is largely sound: noise elements (wizard steps, redundant captions, blue boxes) are eradicated, the single-line toolbar and merged 4-cell top bar are properly integrated, and the 10-column orders table and VWAP schedule operate cleanly.
   - The math identities in the 4-cell top bar and summary cards are 100% accurate, zero-division defended, and free of anomalies.
   - Streamlit AppTest runs cleanly with 0 exceptions.
3. **Blocking Defect**:
   - The one-click follow button (`btn_confirm_follow_rebalance_tab2`) is currently broken in practical usage due to the `"加仓"/"减仓"` vs `"增持"/"减持"` keyword divergence between `app_gui.py` and `portfolio_manager.py`. It must be aligned before Milestone 2 can be deemed fully operational in production.

---

## 6. Verification Method

To independently reproduce all observations and empirical challenges:

```powershell
# 1. Run the Authoritative 30-Test Challenger Adversarial Suite
py -3 -m pytest tests/test_challenger_tab2_rebalance_adversarial.py -v

# 2. Directly verify the follow action string mismatch defect
py -3 -c "
import sys; from pathlib import Path
sys.path.insert(0, str(Path('AGY2_FundAdvisory').resolve()))
from portfolio_manager import PortfolioManager
pm = PortfolioManager(db_path=':memory:')
pm.available_cash = 20000.0
pm.add_or_update_holding('005561', shares=10000, nav=1.2, cost_price=1.2)
rows = [
    {'基金代码': '005561', '建议操作': '➖ 建议减仓', '建议调仓金额(元)': -5000.0},
    {'基金代码': '002351', '建议操作': '➕ 建议加仓', '建议调仓金额(元)': 8000.0}
]
cnt = pm.apply_rebalance_orders_to_holdings(rows)
print('Applied count:', cnt)
assert cnt == 0, 'Expected 0 applied due to string mismatch'
print('BUG CONFIRMED: 0 orders applied!')
"

# 3. Verify Milestone 2 static and AST contracts
py -3 scripts/verify_tab2_milestone2.py

# 4. Verify Baseline infrastructure referee suite
py -3 -m pytest tests/test_infra.py
```
