# Milestone 1 Code Review & Adversarial Challenge Report

- **Reviewer Agent**: `reviewer_m1_1`
- **Roles**: reviewer, critic
- **Target**: Milestone 1 Implementation across `app_gui.py`, `portfolio_manager.py`, `strategy_bridge.py`, `tests/`
- **Timestamp**: 2026-11-09T17:35:00Z
- **Verdict**: **APPROVE**

---

## 1. Observation

### 1.1 Physical Safety Redlines & Integrity Audit
- **Git Status & Diff**:
  Executed `git status --porcelain judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py AGY2_FundAdvisory/data_loader.py` and `git diff HEAD -- judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py AGY2_FundAdvisory/data_loader.py`.
  Result: Exit code 0, empty diff. All 4 referee files (`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`) and `DataLoader.simulate_execution` in `data_loader.py` are **100% untouched**.
- **Integrity Violation Scan**:
  - No hardcoded test values or fake outputs embedded in `app_gui.py`, `portfolio_manager.py`, or `strategy_bridge.py`.
  - No facade implementations or shortcuts detected.
  - Zero integrity violations detected.

### 1.2 Automated Test Suite Execution
- `py -3 -m pytest tests/test_infra.py`:
  ```text
  ============================= 14 passed in 7.05s ==============================
  ```
- `py -3 -m pytest tests/test_adv_final_closure.py`:
  ```text
  ====================== 14 passed, 59 warnings in 35.61s =======================
  ```
- `py -3 -m pytest tests/test_delta_m1_guardrails.py`:
  ```text
  ============================= 5 passed in 20.87s ==============================
  ```
- **Total Test Count**: 33 tests passed, 0 failed, 0 errors.

### 1.3 Milestone 1 Implementation Verification

1. **3D Surface Chart Removal & Factor Evolver 2D Table**:
   - `AGY2_FundAdvisory/app_gui.py` line 2147: `render_monte_carlo_stress_table(stress_data, expander_title=...)` generates a clean 2D crisis stress comparison table across 3 historical scenarios ("2008全球金融危机", "2015流动性踩踏", "2024小盘股危机").
   - Line 2194: `render_monte_carlo_3d_chart` is preserved as an alias calling `render_monte_carlo_stress_table`.
   - Lines 4461 & 5288: Tab 1 and Tab 2 directly invoke `render_monte_carlo_stress_table`.
   - Lines 3145-3150: The arcane `st.code(rule_expr_txt)` RuleTree code block is replaced by a structured 2D parameter mechanism table (`Mom_Win`, `Vol_Pulse`, `Panic_Safe`) and advisory caption.

2. **Right-Wing Alert Sentry Case-Insensitive Matching & Extraction**:
   - `AGY2_FundAdvisory/app_gui.py` lines 3062-3078 (`_top_lvl_rank`) and lines 3274-3286 (`_sentry_alert_sorter`):
     - `_lvl = str(a.get("level", "yellow")).lower()`
     - Red/critical alerts return priority `(0, 0)`, placing fatal risk alerts at the very top.
     - Warning alerts return `(1, 0)`, with "规模待核验" deprioritized to `(1, 1)`.
   - Lines 3289-3306:
     - `is_red = raw_lvl in ("red", "critical")` -> displays `🔴` badge and `var(--color-up)` left border.
     - `is_yellow = raw_lvl in ("yellow", "warning")` -> displays `🟡` badge and `var(--accent-primary)` left border.
     - Details extracted via `alert.get("desc") or alert.get("detail") or alert.get("message", "")`.
     - Action extracted via `alert.get("action") or alert.get("suggested_action", "")`.

3. **Tab 2 DataFrame Column Headers & Action Bar Layout**:
   - `AGY2_FundAdvisory/app_gui.py` lines 2199-2216: `format_micro_execution_slices_df(v_slices)` maps `phase, label, vol_ratio, slice_amount, strategy` to `执行阶段, 窗口类型, 分配比例, 建议挂单金额(元), 微观执行策略`, and formats `分配比例` as percentage (`15%`) and `建议挂单金额(元)` as currency (`¥1,500.00`).
   - Line 5976 renders `format_micro_execution_slices_df(v_slices)`.
   - Lines 4928-5050 organize the 6-key action toolbar: `➕ 极速录基`, `📋 批量导入`, `📸 截图导入`, `↩️ 撤销修改`, `🔄 同步估值`, `⚙️ 账本与环境管理`.
   - Lines 6001-6075: The duplicate full-width blue overwrite button at the bottom was removed. Action bar is consolidated into a 3-slot row: (1) `✅ 采纳并写入账本` / `📌 保存明日预案` / `✅ 采纳并执行调仓`, (2) `📋 复制下单小抄`, (3) `📈 送入回测对比`.

4. **Tab 4 Secondary Navigation & 017436 Name Unification**:
   - `AGY2_FundAdvisory/app_gui.py` lines 7240-7255: Replaces multi-row tabs with single-row compact `st.segmented_control` (with fallback to `st.radio(horizontal=True)`).
   - `portfolio_manager.py` (line 842, 847) and `strategy_bridge.py` (lines 491, 588, 704, 820) unify fund `017436` name to `"华安纳斯达克100ETF联接A"`.
   - `strategy_bridge.py` lines 3767-3785: Multi-level catalog lookup (`CORE_STRATEGY_POOL`, `EXTENDED_FUND_CATALOG`, `PortfolioManager.resolve_fund_meta`) completely eliminates `存量标的_XXXXXX`.
   - `strategy_bridge.py` line 3792: `h_holding_days` defaults to `-1` when fund is not held.
   - `app_gui.py` line 5868: `is_held = it.get("market_value", 0.0) > 0` ensures new buy targets never trigger 7-day penalty locks.

5. **"📱 手机极简盯盘视图 / 🖥️ 桌面专业模式" Toggle**:
   - `AGY2_FundAdvisory/app_gui.py` lines 2468-2476: Mode toggle placed in sidebar radio.
   - Lines 2746-2861: When mobile mode is selected, renders 3-card stream:
     ① 今日总资产与预估盈亏卡片 (`total_cur_equity`, `est_pnl`, `_t2_pnl`, cash)
     ② 14:30 尾盘关键操作指令卡片 (`c_status`, `orders_brief`)
     ③ 核心风险提醒与长截图导入入口 (`alerts_list` top 3, file uploader)
     Followed immediately by `st.stop()` to eliminate wide desktop tables.

---

## 2. Logic Chain

1. **Review Verification Chain**:
   - The user specification in `ORIGINAL_REQUEST.md` (lines 146-167) called for:
     (1) Eliminating 3D surface charts and RuleTree code box;
     (2) Fixing right-wing risk alerts (red vs yellow badge, desc/action extraction);
     (3) Localizing Tab 2 execution table headers and eliminating duplicate bottom buttons;
     (4) Compact single-row secondary navigation in Tab 4, unifying fund 017436, and preventing false 7-day locks on new buys;
     (5) Providing a mobile watchdog view toggle.
   - Observations 1.3.1 through 1.3.5 confirm that each required item is implemented in the production code with exact matching logic.
   - Observation 1.1 confirms that referee files are untouched, satisfying the physical safety redline.
   - Observation 1.2 confirms that all 33 unit and integration tests pass without failures.

2. **Adversarial Stress Testing Chain**:
   - Stress-tested `format_micro_execution_slices_df` with empty lists, None values, and malformed dictionary payloads: function returns an empty DataFrame or handles non-standard values without throwing uncaught exceptions.
   - Stress-tested `render_monte_carlo_stress_table` and its alias `render_monte_carlo_3d_chart` with None, missing keys, and scalar `liquidation_days`: both complete gracefully.
   - Verified that `StrategyBridge.generate_ai_rebalance_orders` sets `holding_days = -1` on unheld buy targets, and `app_gui.py` verifies `is_held = market_value > 0`, completely preventing new buy allocations from triggering false 7-day penalty locks.

---

## 3. Caveats

1. **Streamlit Execution Environment**:
   - `st.segmented_control` requires Streamlit >= 1.40. The implemented fallback (`hasattr(st, "segmented_control")` -> `st.radio(horizontal=True)`) provides backward compatibility for older Streamlit runtimes.
2. **Scope of Milestone 1**:
   - Milestone 1 specifically addresses UI/UX layout, alert sentry bug fixes, 3D chart replacement, Tab 2/4 navigation, and mobile view. Milestone 2 features (Chief Advisor Memo, Time Machine Backtest) and Milestone 3 features (OCR slice engine, combat 29-fund ledger) are scoped to subsequent milestones.

---

## 4. Conclusion

The Milestone 1 implementation is **technically sound, fully compliant with specifications, and robust under adversarial scrutiny**. Zero integrity violations or referee file modifications were detected. All 33 automated tests pass cleanly.

**Final Verdict: APPROVE**

---

## 5. Verification Method

To independently verify this verdict:

```powershell
# 1. Verify referee files are 100% untouched
git diff HEAD -- judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py AGY2_FundAdvisory/data_loader.py

# 2. Run read-only physical infrastructure test suite
py -3 -m pytest tests/test_infra.py

# 3. Run full regression closure test suite
py -3 -m pytest tests/test_adv_final_closure.py

# 4. Run targeted Milestone 1 guardrail test suite
py -3 -m pytest tests/test_delta_m1_guardrails.py
```

Expected result: All diff commands output empty strings; all 3 pytest suites pass with 33 passed, 0 failed.
