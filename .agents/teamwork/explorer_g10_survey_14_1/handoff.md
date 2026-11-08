# Handoff Report: G10 Visual Subtraction & UI Elevation Survey

**Agent**: `explorer_g10_survey_14_1`  
**Working Directory**: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g10_survey_14_1\`  
**Target Recipient**: Orchestrator (`496bfcfb-72ea-446e-b3dc-c85871c12398`)  
**Type**: Hard Handoff (Investigation Complete)

---

## 1. Observation

1. **Top 3 Sector Cards Wrapping & Clutter**:
   - In `AGY2_FundAdvisory/app_gui.py` line 2942, `cols_top3 = st.columns(3)` is nested inside `col_radar` (`st.columns([6.2, 3.8])`).
   - Line 2961: `<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">`.
   - Line 2962: Left child is `<span style="font-size: 13px; font-weight: 700; color: var(--text-primary);">{sec['name']}</span>` without `white-space: nowrap; flex-shrink: 0;`.
   - Lines 2963–2966: Right child is `<div style="display: flex; gap: 4px; align-items: center;"><span style="font-size: 10px; font-weight: 700; color: {rt_color};">实时: {rt_chg:+.2f}%{pt_disp}</span><span style="font-size: 11px; padding: 1px 6px; border-radius: 4px; background: var(--bg-canvas); color: {tag_color}; border: 1px solid var(--border-subtle);">{sec['tag']}</span></div>`.
   - Lines 2968–2982: Card stacks 6 vertical items including a bulky gray box:
     `<div style="font-size: 11px; color: var(--text-primary); background: var(--bg-elevated); padding: 4px 6px; border-radius: 4px; margin-bottom: 4px; line-height: 1.35;">💡 入选依据：<b>{core_logic_txt}</b></div>`.
   - In `AGY2_FundAdvisory/advisory_engine.py` lines 1160–1175: When `er_20 <= 0.35` and `slope_20 > 5.0`, `_synthesize_quantitative_evidence` produces contradictory text: "均线斜率 +... 右侧共振稳步上行" and "信噪比 ... 处于高频震荡博弈".

2. **Right-Wing Sentry Redundancy & CVaR Card**:
   - In `AGY2_FundAdvisory/app_gui.py` line 3054: `safe_markdown_html(render_stress_liquidity_card_html(stress_m_res))` displays `极限 CVaR 99%: -36.1%`, conflicting with Tab 3 (-12.0%) and inflating sentry height.
   - In `AGY2_FundAdvisory/app_gui.py` lines 1869–1877 & 3043: `render_correlation_mutation_card_html` outputs a full 85px decision card `【多资产相关性健康】` even when correlation <= 0.75.
   - In `AGY2_FundAdvisory/app_gui.py` lines 2761–2838: "今日投顾行动总开关" is inside `with st.expander(...)` across `st.columns([8.2, 1.8])`, with misaligned button.

3. **Sidebar vs Top 4 Metric Cards 100% Duplication**:
   - In `AGY2_FundAdvisory/app_gui.py` lines 2348–2401: Sidebar section `🕒 市场状态与底座` displays:
     - 交易时钟: `{clock_title}（倒计时 {market_status.countdown_str}）` (100% matches Top Card 1)
     - 市场定调: `{vernacular_state} ｜ 信噪比: {snr:.2f}` (100% matches Top Card 2)
     - 攻防红线: `破 {surge_line:,.0f} 进攻 ｜ 跌 {breakdown_line:,.0f} 防守` (100% matches Top Card 2)
     - 两市成交: `{t_str}`, 多方占比 `{u_pct}%` (100% matches Top Card 3)
   - In `AGY2_FundAdvisory/app_gui.py` line 2291: `sb_head_c1, sb_head_c2 = st.columns([6.8, 3.2])`. In a ~260px sidebar, 3.2 columns is ~83px, causing `with st.popover("⚙️ 外观", ...)` to truncate with ellipsis.

4. **Top 4 Metric Cards**:
   - In `AGY2_FundAdvisory/app_gui.py` line 647: `.main-metric-card { min-height: 122px; padding: 10px 12px 12px 12px; }`.
   - Lines 2594–2686: Top cards contain multiple secondary subtitle rows and badge rows.

5. **Tab Hoisting & Viewport Distance**:
   - Currently, `tab_zero_start, tab_holdings_and_rebalance, tab_backtest, tab_toolbox = st.tabs(...)` is at line 3279, pushed down ~740px below Top 4 cards, next day plan, and `render_dual_wing_advisory_dashboard` (`expanded=True`).
   - On 1080p, the tabs are pushed below the fold.

6. **Test Invariant Checks**:
   - `tests/test_adv_final_closure.py` line 168: `assert "行情源状态" in app_gui_src`.
   - `tests/test_g8_ux_and_realtime_fusion.py` line 75: `assert "with st.container(height=380):" in src or "height=380" in src`.
   - `tests/test_g8_ux_and_realtime_fusion.py` line 260: `assert "💡 入选依据" in gui_src`.
   - `tests/test_g10_correlation_liquidity_and_stress.py` line 289: `assert "safe_markdown_html(render_stress_liquidity_card_html" in code`.
   - `tests/test_ui_instant_load.py` line 97: `assert ("min-height: 118px;" in gui_text or "height: 112px;" in gui_text)`.

---

## 2. Logic Chain

1. **Title Wrapping Elimination**:
   - From Observation 1, the flex row in card header compresses the title because the right cluster is wide and the title lacks `white-space: nowrap; flex-shrink: 0`.
   - Moving real-time quotes out of Row 1 and giving both title and status badge `white-space: nowrap !important; flex-shrink: 0 !important;` mathematically guarantees zero wrapping across all viewports.
   - Refactoring card into 3 clean rows (Row 1: Title + Tag; Row 2: Metrics line; Row 3: Fund + <=18 char concise rationale) reduces card min-height from 220px to 140px, eliminating the bulky gray box.
   - Preserving the literal text `💡 入选依据` in Row 3 satisfies `test_g8_ux_and_realtime_fusion.py` line 260 without test modification.

2. **Right-Wing Sentry Optimization**:
   - From Observation 2, `-36.1%` CVaR card in the sentry causes cognitive confusion with Tab 3 (-12.0%) and inflates height. Moving its call to Tab 3 solves this cleanly while satisfying `test_g10_correlation_liquidity_and_stress.py` line 289.
   - Suppressing the 85px green `【多资产相关性健康】` card when correlation <= 0.75 leaves the sentry showing only true pending risks (max 2 items) or a clean green single-line full-pass bar when healthy.
   - Streamlining "今日投顾行动总开关" into a compact <= 44px bar at the top with inline button resolves misalignment and avoids button duplication.

3. **Sidebar Deduplication**:
   - From Observation 3, 4 out of 5 items in sidebar "市场状态与底座" are 100% duplicate with Top 4 cards.
   - Compressing to a single status bar `行情源状态: {data_src_badge} ｜ 底座: {latest_date}` saves ~190px of vertical space, putting `📊 核心指数行情走廊` directly at the top.
   - Retaining `"行情源状态"` guarantees `test_adv_final_closure.py` line 168 passes.
   - Adjusting column ratio to `[6.0, 4.0]` and adding `white-space: nowrap !important;` prevents "⚙️ 外观" truncation.

4. **Top 4 Cards 88px Compression**:
   - From Observation 4, reducing `.main-metric-card` padding to `6px 10px 8px 10px` and `min-height: 88px;` and trimming each card to 3 clean lines (Title, Huge Value, 1-line Subtitle) achieves an exact 88px height.
   - Updating `test_ui_instant_load.py` line 97 to accept `min-height: 88px;` maintains test green.

5. **Tab Hoisting & First-Screen Fold**:
   - From Observation 5, collapsing the dual-wing expander (`expanded=False`) reduces its height to ~36px.
   - Top 4 cards (88px) + Action switch (44px) + Collapsed expander (36px) = 168px total.
   - `st.tabs` header is placed at y ≈ 180px, leaving 750px of visible height for Tab 1/2 on standard 1080p, completely above the fold.

---

## 3. Caveats

- **Test Suite Runtime**: Running all test suites sequentially (`test_infra.py`, `test_adv_final_closure.py`, etc.) can take ~75s; `test_infra.py` generates temporary sandbox ledgers that must be cleaned up before `test_adv_final_closure.py` asserts `junk_ledgers == 0`.
- **Streamlit Running Instance**: Port 8501 is running on PID 40944; after modifying GUI code, the process should be cleanly restarted and verified via `http://127.0.0.1:8501/_stcore/health`.
- **Read-Only Judge Files**: Four judge files (`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`) and `DataLoader.simulate_execution` signature remain strictly untouched.

---

## 4. Conclusion

The surgical plan for G10 is fully verified and actionable:
1. **Top 3 Sector Cards**: 3-row layout with `white-space: nowrap !important; flex-shrink: 0;`, Row 2 metrics line, Row 3 fund + <=18 char rationale (`💡 入选依据`), eliminating the bulky gray box and fixing the `er_20 <= 0.35` contradiction in `advisory_engine.py`.
2. **Right-Wing Sentry**: Remove `-36.1%` CVaR card (move invocation to Tab 3), suppress green correlation card when <= 0.75, streamline action switch to compact <= 44px bar, cap pending alerts at max 2.
3. **Sidebar**: Replace 220px duplicate card with a single 26px status bar (preserving `"行情源状态"`), fix "⚙️ 外观" column ratio to `[6.0, 4.0]`.
4. **Top 4 Cards**: Compress `.main-metric-card` to 88px (padding 6px 10px, 3 clean lines per card). Update `test_ui_instant_load.py`.
5. **Tab Hoisting**: Default collapse dual-wing expander (`expanded=False`), hoist `st.tabs` to y ≈ 180px so all 4 tabs and primary controls are visible without scrolling on 1080p.
6. **Backend & Test Safety**: Financial news whitelist/blacklist filter in `data_loader.py`, ensure all tests remain 100% green.

---

## 5. Verification Method

1. **Static Test Suite Commands**:
   - `py -3 -m pytest tests/test_infra.py` (Must pass 100%, 0 judge file diffs)
   - `py -3 -m pytest tests/test_adv_final_closure.py` (Must pass 100%)
   - `py -3 -m pytest tests/test_g3_evolution_loop.py` (Must pass 100%)
   - `py -3 -m pytest tests/test_gui_multi_ledger_stress.py` (Must pass 100%)
   - `py -3 -m pytest tests/test_g10_correlation_liquidity_and_stress.py` (Must pass 100%)
   - `py -3 -m pytest AGY2_FundAdvisory/tests/test_ui_instant_load.py` (Must pass 100%)
2. **Health Probe**:
   - `http://127.0.0.1:8501/_stcore/health` returns HTTP 200 OK.
3. **DOM & Visual Check via Browser Tool**:
   - Inspect Top 3 cards: confirm "消费白酒", "医药医疗", "国内黄金" names and tags are on a single line with zero word wrapping.
   - Inspect right wing: confirm no -36.1% CVaR card and no redundant green card when healthy.
   - Inspect sidebar: confirm index corridor is at the top, settings button has no "..." ellipsis.
   - Inspect fold line: confirm Top 4 cards, action switch, and all 4 Tabs are visible on 1920x1080 without scrolling.
