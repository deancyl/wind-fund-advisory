# Independent Review & Adversarial QA Report: Milestone 1

- **Agent**: `reviewer_m1_2` (Independent Reviewer & Adversarial Critic)
- **Role**: reviewer, critic
- **Target**: Milestone 1 Implementation across `app_gui.py`, `portfolio_manager.py`, `strategy_bridge.py`
- **Timestamp**: 2026-11-09T17:24:00Z
- **Verdict**: **APPROVE**

---

## 1. Observation

### 1.1 Direct Code Observations

1. **3D Surface Chart Removal & 2D Table Alias**:
   - `AGY2_FundAdvisory/app_gui.py`: Line 2147 defines `render_monte_carlo_stress_table(stress_data, expander_title=...)`. It iterates over `stress_data.get("scenarios", [])`, extracting `predicted_mdd_pct`, `h300_mdd_pct`, `excess_defense_pct`, `predicted_loss_amount`, and `liquidation_days`, building a clean 2D crisis table comparing "2008全球金融危机", "2015流动性踩踏", and "2024小盘股危机" with investor risk tolerance.
   - Line 2194 defines `render_monte_carlo_3d_chart(stress_data, *args, **kwargs)` as a direct alias delegating to `render_monte_carlo_stress_table`.
   - Line 4461 (Tab 1) and line 5288 (Tab 2) invoke `render_monte_carlo_stress_table(bootstrap_stress_data)` and `render_monte_carlo_stress_table(real_stress_data, ...)`.
   - Lines 3145-3151: The previous `st.code(rule_expr_txt, language="text")` is replaced with `pd.DataFrame` rendering `Mom_Win`, `Vol_Pulse`, and `Panic_Safe` parameter mechanism table with an advisory conclusion caption.

2. **Right-Wing Alert Sentry Bug Fix**:
   - `AGY2_FundAdvisory/app_gui.py`: Line 3062 (`_top_lvl_rank`) and line 3274 (`_sentry_alert_sorter`) implement severity sorting:
     - `raw_lvl in ("red", "critical")` -> `(0, 0)`
     - `raw_lvl in ("yellow", "warning")` -> `(1, 0)` (or `(1, 1)` if "规模待核验" in text)
     - `raw_lvl in ("info", "notice")` or green -> `(3, 0)`
   - Line 3289 extracts `raw_lvl = str(alert.get("level", "WARNING")).lower()`, correctly recognizing `"red"`, `"critical"`, `"CRITICAL"`, `"yellow"`, `"warning"`, `"WARNING"`.
   - Line 3294 assigns red badge `🔴` and `var(--color-up)` border to red alerts; yellow badge `🟡` and `var(--accent-primary)` border to yellow alerts.
   - Line 3305 extracts `detail_str = alert.get("desc") or alert.get("detail") or alert.get("message", "")`.
   - Line 3306 extracts `action_str = alert.get("action") or alert.get("suggested_action", "")`.

3. **Tab 2 DataFrame Column Headers & Action Buttons**:
   - `AGY2_FundAdvisory/app_gui.py`: Line 2199 defines `format_micro_execution_slices_df(v_slices)` which maps:
     - `phase` -> `执行阶段`
     - `label` -> `窗口类型`
     - `vol_ratio` -> `分配比例` (formatted as `{v*100:.0f}%`)
     - `slice_amount` -> `建议挂单金额(元)` (formatted as `¥{v:,.2f}`)
     - `strategy` -> `微观执行策略`
   - Line 4681 (Tab 1) and line 5976 (Tab 2) apply `format_micro_execution_slices_df`.
   - Lines 6001-6075: The duplicate full-width blue overwrite button `btn_confirm_follow_rebalance_tab2` has been completely deleted. The bottom toolbar consolidates actions into a 3-part layout:
     - (1) `✅ 采纳并写入账本` / `📌 保存明日预案` / `✅ 采纳并执行调仓`
     - (2) `📋 复制下单小抄`
     - (3) `📈 送入回测对比`
   - Lines 4929-5040 organize the top 6-button utility bar: `➕ 极速录基`, `📋 批量导入`, `📸 截图导入`, `↩️ 撤销修改`, `🔄 同步估值`, `⚙️ 账本管理`.

4. **Tab 4 Secondary Navigation & 017436 Name Unification**:
   - `AGY2_FundAdvisory/app_gui.py`: Lines 7240-7255 implement `st.segmented_control` with `st.radio(..., horizontal=True)` fallback for 6 sub-tools: "📊 资产穿透与排雷", "🌡️ 14赛道温度计", "⚡ 尾盘折溢价套利", "🛡️ 期权防暴跌哨", "🌐 跨境QDII与锁汇", "💡 A/C端选型算费". Each tool is isolated under `if sel_sub_mod == "..."`.
   - `AGY2_FundAdvisory/portfolio_manager.py` (lines 842, 847) and `AGY2_FundAdvisory/strategy_bridge.py` (lines 491, 588, 704, 820) unify fund `017436` to `"华安纳斯达克100ETF联接A"`. No "华宝" string exists in the repository for `017436`.
   - `AGY2_FundAdvisory/strategy_bridge.py`: Lines 3767-3785 query `CORE_STRATEGY_POOL`, `EXTENDED_FUND_CATALOG`, and `PortfolioManager.resolve_fund_meta(code)`, falling back to `优选标的_{code}`, completely eliminating `存量标的_XXXXXX`.
   - `strategy_bridge.py` line 3792 sets `h_holding_days = -1` when fund is not held; `app_gui.py` line 5868 checks `is_held = it.get("market_value", 0.0) > 0`, ensuring new buy targets (`diff_amt > 0`) never trigger 7-day penalty lock warnings.

5. **"📱 手机极简盯盘视图 / 🖥️ 桌面专业模式" Toggle**:
   - `AGY2_FundAdvisory/app_gui.py`: Lines 2468-2476 implement the sidebar layout mode toggle (`st.session_state.app_view_layout_mode` radio).
   - Lines 2746-2862 render the 3-card stream when `app_view_layout_mode == "📱 手机极简盯盘"`:
     - Card 1: 今日总资产与预估盈亏 (`total_cur_equity`, `est_pnl`, `_t2_pnl`, `available_cash`, `in_transit_cash`)
     - Card 2: 14:30 尾盘关键操作指令 (`c_status`, lock-in defense notices or healthy structure statement)
     - Card 3: 核心风险提醒 (ActiveRiskSentry alerts sorted by severity, top 3) + 手机持仓长截图一键更新 uploader
     - Ends with `st.stop()` to eliminate wide tables, tabs, and heavy charts.

### 1.2 Test Execution Results

- Command: `py -3 -m pytest tests/test_infra.py`
  - Output: `14 passed in 6.31s`
- Command: `py -3 -m pytest tests/test_adv_final_closure.py`
  - Output: `14 passed, 59 warnings in 34.37s`
- Command: `py -3 -m pytest tests/test_delta_m1_guardrails.py`
  - Output: `5 passed in 19.68s`
- Total: **33 passed, 0 failed**.

### 1.3 Physical Safety Redlines & Integrity Verification

- Command: `git diff HEAD -- judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py AGY2_FundAdvisory/data_loader.py`
  - Output: Empty (0 bytes changed).
  - All 5 redline files are **100% bit-for-bit identical** to HEAD.
- Integrity Check:
  - No hardcoded test mocks or dummy outputs detected.
  - No bypasses of intended logic.
  - No fabricated logs.
  - Independent verification executed directly in Windows Native environment.

---

## 2. Logic Chain

1. **3D Surface Removal to 2D Table**:
   - Observation: `render_monte_carlo_3d_chart` previously produced an uninformative flat 3D surface because C1-C5 MDD values were identical across tiers.
   - Inference: Replacing this with `render_monte_carlo_stress_table` presenting historical scenarios ("2008", "2015", "2024"), predicted losses in RMB, contract comparisons, and liquidation days delivers direct, human-readable investor value.
   - Keeping `render_monte_carlo_3d_chart` as an alias guarantees that any external or existing test call sites do not crash.

2. **Alert Sentry Severity & Deserialization**:
   - Observation: `ActiveRiskSentry` produces lowercase `"red"` and `"yellow"` levels, and puts descriptions in `"desc"`. Frontend checked for exact uppercase `"CRITICAL"` and `"detail"`.
   - Inference: Normalizing `str(alert.get("level", "WARNING")).lower()` and checking `in ("red", "critical")` and `in ("yellow", "warning")` repairs the disconnection, restoring accurate red/yellow badges and explanatory text for all 12 risk dimensions.

3. **Tab 2 DF Chinese Column Mapping & Button Consolidation**:
   - Observation: English column headers (`phase`, `vol_ratio`, `slice_amount`) were directly exposed, and a duplicate blue button existed at the bottom of the rebalance tab.
   - Inference: `format_micro_execution_slices_df` maps headers to Chinese and formats percentages and currency. Removing the duplicate button eliminates double-submission hazards and consolidates workflow into the 3-button action bar.

4. **Tab 4 Secondary Nav & 017436 Consistency**:
   - Observation: Native `st.tabs` created cluttered multi-row tab headers conflicting with top-level primary navigation, and `017436` had conflicting name references.
   - Inference: `st.segmented_control` maintains a compact single-row design. Standardizing `017436` to `"华安纳斯达克100ETF联接A"` and setting `h_holding_days = -1` with `is_held` checks in the frontend eliminates `存量标的_XXXXXX` and false 7-day lock warnings on new buy targets.

5. **Mobile View Architecture**:
   - Observation: Dense tables and charts fail on mobile viewports.
   - Inference: Placing a sidebar toggle with an early `st.stop()` branch renders a 3-card stream focusing on total equity, 14:30 actionable commands, and top risk alerts, fulfilling the mobile UX contract without regressing desktop mode.

---

## 3. Adversarial Challenges & Findings

### Challenge 1 (Minor Finding — Robustness in Stress Table Parsing)
- **Target**: `render_monte_carlo_stress_table` in `AGY2_FundAdvisory/app_gui.py` line 2159.
- **Scenario**: If an upstream engine scenario dictionary contains an explicit `None` value (e.g. `{"excess_defense_pct": None}` or `{"predicted_mdd_pct": None}`), `sc.get("excess_defense_pct", 0.0)` returns `None`, causing `float(None)` to raise a `TypeError`.
- **Blast Radius**: Minor/Low. In standard operation, the Monte Carlo engine produces valid numeric floats.
- **Mitigation Recommendation**: For Milestone 2 or 4 polish, change `float(sc.get("excess_defense_pct", 0.0))` to `float(sc.get("excess_defense_pct") or 0.0)`.

### Challenge 2 (Edge Case — Empty / Non-Held Target Rebalance)
- **Scenario**: When user has an empty portfolio and generates an initial target allocation, ensure no target is flagged with 7-day lock warnings.
- **Stress Test**: Simulated rebalance with empty holdings across 3 new targets (`017436`, `005561`, `002351`).
- **Result**: `action == "BUY"`, `holding_days == -1`, `safety_warning == ""` across all items. **PASS**.

### Challenge 3 (Edge Case — Adversarial Alert Sorting Payload)
- **Scenario**: Alerts list containing non-string levels, empty dicts, missing titles, mixed casing (`CRITICAL`, `critical`, `RED`, `WARNING`).
- **Stress Test**: Fed 11 corrupt and mixed alert payloads into `_sentry_alert_sorter`.
- **Result**: All critical/red alerts sorted to indices 0..2, warnings followed, and no unhandled exceptions were raised. **PASS**.

---

## 4. Caveats

1. **Streamlit Execution Environment**:
   - `st.segmented_control` requires Streamlit >= 1.40. The implementation includes a built-in fallback to `st.radio(..., horizontal=True)`, ensuring robustness across Streamlit versions.
2. **Browser Rendering Acceptance**:
   - Full DOM geometry, CSS responsive styling, and visual snapshot inspection will be formally validated during Milestone 4 via `/browser` verification against `http://localhost:8501`.

---

## 5. Conclusion

Milestone 1 satisfies all functional, architectural, quality, and physical safety requirements. The implementation successfully eliminates the 3D surface chart and RuleTree code box, restores accurate twelve-dimensional risk alert badges and descriptions, localizes Tab 2 execution table headers and removes duplicate action buttons, unifies fund `017436` naming without false lock-in warnings, and adds the mobile watchdog stream. All 33 automated tests pass with 0 failures, and the physical safety redlines remain untouched.

**Final Verdict**: **APPROVE**

---

## 6. Verification Method

To independently reproduce and verify this review:

```powershell
# 1. Verify read-only physical safety redlines
git diff HEAD -- judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py AGY2_FundAdvisory/data_loader.py

# 2. Run read-only infrastructure test suite (14 passed)
py -3 -m pytest tests/test_infra.py

# 3. Run regression closure test suite (14 passed)
py -3 -m pytest tests/test_adv_final_closure.py

# 4. Run targeted Milestone 1 guardrails test suite (5 passed)
py -3 -m pytest tests/test_delta_m1_guardrails.py
```
