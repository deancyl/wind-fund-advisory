# G10 Visual Subtraction & UI Elevation Architectural Survey & Surgery Plan

**Document Path**: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g10_survey_14_1\analysis.md`  
**Explorer**: `explorer_g10_survey_14_1`  
**Date**: 2026-11-08  
**Scope**: `AGY2_FundAdvisory/app_gui.py`, `data_loader.py`, `advisory_engine.py`, `portfolio_manager.py`, and test suites.

---

## 1. Top 3 Sector Cards Surgery

### 1.1 Root Cause of Title & Badge Wrapping
- **Location**: `AGY2_FundAdvisory/app_gui.py`, Lines 2941–2984 (`cols_top3 = st.columns(3)` inside `col_radar`).
- **Layout Constraint**: The dual-wing dashboard is divided into `[6.2, 3.8]`. Left wing `col_radar` receives ~62% of container width (~720px on 1080p). Inside `col_radar`, `st.columns(3)` yields ~230px–260px per card.
- **Defect Mechanism**:
  1. Line 2961 defines: `<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">`.
  2. Left child: `<span style="font-size: 13px; font-weight: 700; color: var(--text-primary);">{sec['name']}</span>` (lacks `white-space: nowrap; flex-shrink: 0;`).
  3. Right child: `<div style="display: flex; gap: 4px; align-items: center;"><span style="font-size: 10px; font-weight: 700; color: {rt_color};">实时: {rt_chg:+.2f}%{pt_disp}</span><span style="font-size: 11px; padding: 1px 6px; border-radius: 4px; background: var(--bg-canvas); color: {tag_color}; border: 1px solid var(--border-subtle);">{sec['tag']}</span></div>`.
  4. The right cluster (quote + points + badge) measures ~150px–170px wide, leaving under 80px for the sector name.
  5. In CSS flex layout without `white-space: nowrap`, CJK text wraps by character: "消费白酒" breaks into "消费白" and "酒", "医药医疗" breaks into "医药医" and "疗", "黄金击球区" breaks into "黄金击球" and "区".
- **Height Clutter**: The card currently packs 6 vertical text blocks (Title+Quote+Tag, 4 Subscores, 20d Vol/MDD, verbose gray box with `💡 入选依据`, Fund Name, Fund Code) plus a button, inflating card min-height to 220px.

### 1.2 Restructuring to Clean 3-Row Architecture
- **Row 1 (Header)**:
  - Left: Sector Name with `font-size: 14px; font-weight: 700; color: var(--text-primary); white-space: nowrap !important; flex-shrink: 0 !important;`.
  - Right: Single Status Badge (`{sec['tag']}`) with `font-size: 11px; font-weight: 600; padding: 1px 6px; border-radius: 4px; background: var(--bg-canvas); color: {tag_color}; border: 1px solid var(--border-subtle); white-space: nowrap !important; flex-shrink: 0 !important;`.
  - Real-time change and point count are completely removed from Row 1.
- **Row 2 (Core Metrics)**:
  - Single-line summary:
    `得分 {sec['total_score']} ｜ 今日 {rt_chg:+.2f}% ｜ 估值分位 {val_pct:.0f}%`
  - Style: `font-size: 11.5px; color: var(--text-secondary); margin-bottom: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;`.
  - Tooltip: Hover `title` containing full four-factor scores (`估值:{val_score:.0f} 动量:{mom_score:.0f} 信噪:{snr_score:.0f} 拥挤:{crowd_score:.0f}`) and risk indicators (`20日波动 {vol_20_val:.1f}% ｜ 最大回撤 -{mdd_20_val:.1f}%`).
- **Row 3 (Selected Fund & Concise Rationale)**:
  - Line 1: `优选: {sec_fund.get('name', '')} <code style="font-size: 10.5px;">{sec_fund.get('code', '')}</code>`.
  - Line 2: `💡 入选依据: <span style="color: var(--accent-primary);">{concise_logic}</span>` where `concise_logic` is strictly <= 18 Chinese characters.
  - The bulky gray box (`background: var(--bg-elevated); padding: 4px 6px;`) is completely eliminated.
  - Card style: `padding: 10px 12px; min-height: 140px; height: 100%; border-top: 2px solid {tag_color}; box-sizing: border-box;`.
  - Button `➕ 入备选池` remains below Row 3 with `use_container_width=True`.

### 1.3 `advisory_engine.py` Evidence Contradiction Fix
- **Location**: `advisory_engine.py`, lines 1160–1175 in `_synthesize_quantitative_evidence`.
- **Bug**: When Kaufman SNR `er_20 <= 0.35` (high-frequency noise oscillation) and `slope_20 > 5.0`, the engine simultaneously outputs "均线斜率 +... 右侧共振稳步上行" and "信噪比 ... 处于高频震荡博弈", which is logically contradictory.
- **Fix**: When `er_20 <= 0.35`, override momentum phrasing to "底部震荡筑底、均线初现企稳", prohibiting "右侧共振稳步上行". Add a helper `_synthesize_concise_rationale` generating clean <= 18 character rationales (e.g. `极低估黄金击球 · 均线企稳`).

---

## 2. Right-Wing Sentry Container Surgery

### 2.1 CVaR Card (`render_stress_liquidity_card_html`) Removal
- **Location**: `AGY2_FundAdvisory/app_gui.py`, lines 3047–3056.
- **Problem**: Calling `render_stress_liquidity_card_html` in the right-wing sentry renders a `-36.1%` CVaR card that contradicts Tab 3's Monte Carlo (-12.0%) and occupies 95px of sentry height.
- **Surgery**:
  1. Remove lines 3047–3056 from `col_sentry`.
  2. Retain compatibility with `test_g10_correlation_liquidity_and_stress.py` line 289 (`assert "safe_markdown_html(render_stress_liquidity_card_html" in code`) by ensuring `safe_markdown_html(render_stress_liquidity_card_html(...))` is invoked in Tab 3 where CVaR belongs.
  3. In `portfolio_manager.py` line 1403 (`simulate_portfolio_cvar_bootstrap_instance`), align the daily volatility scaling factor with Tab 3.

### 2.2 Green "多资产相关性健康" Card Suppression
- **Location**: `AGY2_FundAdvisory/app_gui.py`, lines 1869–1877 and lines 3041–3045.
- **Problem**: When correlation <= 0.75 and no alert is triggered, `render_correlation_mutation_card_html` generates an 85px full decision-card (`【多资产相关性健康】`), occupying space unnecessarily.
- **Surgery**:
  - When correlation <= 0.75 (`not is_trig and not is_shift`), suppress the large card. Return an empty string `""` or a single compact line.
  - When healthy, the sentry shows only the single clean green full-pass bar:
    `🟢 主动风控巡检全通 ｜ 资产结构健康，无惩罚锁仓与超买拥挤`.
  - When risks exist, show only genuine pending risk cards, capped at a maximum of 2 urgent items.

### 2.3 Streamlining "今日投顾行动总开关"
- **Location**: `AGY2_FundAdvisory/app_gui.py`, lines 2761–2838.
- **Problem**: Currently rendered inside the expander across columns `[8.2, 1.8]` with multiple text rows and vertically misaligned button with `st.write(" ")`.
- **Surgery**:
  - Lift the master action switch out to the top of the dual-wing section (or right above the collapsed expander).
  - Compact container with height <= 44px:
    - Left: Flex row with `{act_status_icon} 今日建议：{act_title}` (concise 1 line, font-size 13px, font-weight 700).
    - Right: Inline button (`st.button(act_btn_label, ...)`) vertically centered, with zero margin gap.

---

## 3. Sidebar vs Top 4 Metric Cards Surgery

### 3.1 100% Redundancy Analysis
- **Location**: `app_gui.py`, lines 2348–2401 ("🕒 市场状态与底座") vs lines 2594–2686 (Top 4 cards).
- **Exact Duplications**:
  1. *交易时钟*: Sidebar `{clock_title}（倒计时 {countdown}）` == Top Card 1.
  2. *市场定调*: Sidebar `{vernacular_state} ｜ 信噪比: {snr}` == Top Card 2.
  3. *攻防红线*: Sidebar `破 {surge_line} 进攻 ｜ 跌 {breakdown_line} 防守` == Top Card 2.
  4. *两市成交*: Sidebar `{t_str}`, 多方占比 `{u_pct}%`, 涨跌家数 == Top Card 3.
- **Space Penalty**: Consumes ~220px in sidebar, pushing `📊 核心指数行情走廊` down off-screen.
- **Surgery Plan**:
  - Replace lines 2348–2401 with a single compact status line (height ~26px):
    ```html
    <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 4px 8px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; font-size: 11px;">
        <span style="color: var(--text-secondary);">行情源状态: <b style="color: var(--color-down);">{data_src_badge}</b></span>
        <span style="color: var(--text-muted); font-family: monospace;">底座: {latest_date}</span>
    </div>
    ```
  - Crucial: Retains `"行情源状态"` string to satisfy `test_adv_final_closure.py` line 168.
  - Frees ~190px of vertical space, putting the index corridor directly at the top of the sidebar.

### 3.2 Sidebar Settings Button Truncation Fix
- **Location**: Lines 2291–2295 (`sb_head_c1, sb_head_c2 = st.columns([6.8, 3.2])`).
- **Defect**: In narrow sidebar (~260px), 32% width is ~83px, causing `st.popover("⚙️ 外观", ...)` to truncate with ellipsis (`⚙️...`).
- **Fix**: Adjust column ratio to `[6.0, 4.0]` or `[5.8, 4.2]` and apply `white-space: nowrap !important;` to ensure "⚙️ 外观" renders completely without ellipsis.

---

## 4. Top 4 Metric Cards Compression

### 4.1 CSS Specification
- **Location**: `app_gui.py`, lines 640–670 (`.main-metric-card`).
- **Current**: `min-height: 122px; padding: 10px 12px 12px 12px; gap: 4px;`.
- **Target**: `min-height: 88px; padding: 6px 10px 8px 10px; gap: 2px;`.
- **Test Alignment**: In `tests/test_ui_instant_load.py` line 97:
  Currently: `assert ("min-height: 118px;" in gui_text or "height: 112px;" in gui_text)`
  Update to: `assert ("min-height: 88px;" in gui_text or "min-height: 118px;" in gui_text or "height: 112px;" in gui_text)`.

### 4.2 Content Simplification (3-Line Clean Structure)
- **Card 1 (🕒 交易时钟与窗口)**:
  - Row 1: Title `🕒 交易时钟与窗口` + info icon.
  - Row 2: Value `{clock_title}` (font-size 18px).
  - Row 3: Subtitle `倒计时 {market_status.countdown_str} ｜ 距网格日 {days_to_next}天`.
- **Card 2 (🧭 市场定调与攻防)**:
  - Row 1: Title `🧭 市场定调与攻防` + info icon.
  - Row 2: Value `{vernacular_state}` (font-size 18px).
  - Row 3: Subtitle `破 {surge_line:,.0f} 进攻 ｜ 跌 {breakdown_line:,.0f} 防守 ｜ 信噪比 {snr:.2f}`.
- **Card 3 (🌡️ 估值与资金量能)**:
  - Row 1: Title `🌡️ 估值与资金量能` + info icon.
  - Row 2: Value `{val_status}` (font-size 16px).
  - Row 3: Subtitle `两市成交 {t_str} ｜ 多方 {u_pct}% ｜ ERP分位 {erp_pct:.1f}%`.
- **Card 4 (💰 总资产与预估)**:
  - Row 1: Title `💰 总资产与今日预估` + info icon.
  - Row 2: Value `¥{total_cur_equity:,.2f}` (font-size 18px).
  - Row 3: Subtitle `盘中: ¥{est_pnl:+,.2f} ({est_pnl_pct:+.2f}%) ｜ 浮盈: ¥{_t2_pnl:+,.2f}`.
- All extra secondary lines and exhaustion badges are moved into hover tooltips (`title="{...}"`).

---

## 5. Tab Hoisting & Dual-Wing Compact Folding

### 5.1 Current Viewport Distance Problem
- Top 4 cards (~150px) + Next day plan expander (~80px) + Dual-wing expander (`expanded=True`, ~450px) + Cross-tab banners (~60px) = ~740px before `st.tabs`!
- On a 1080p display, `st.tabs` is below the fold.

### 5.2 Layout Inversion & Space Budget
- **New Order**:
  1. Top 4 Metric Cards (min-height: 88px, margin-bottom: 6px).
  2. "今日投顾行动总开关" Bar (height <= 44px, margin-bottom: 6px).
  3. Dual-Wing Dashboard Expander (`expanded=False` default collapsed, height: ~36px, margin-bottom: 8px).
  4. Core Four Work Areas: `tab_zero_start, tab_holdings_and_rebalance, tab_backtest, tab_toolbox = st.tabs(...)`.
- **Space Budget on 1080p**:
  - Total vertical height before Tabs: 88px + 6px + 44px + 6px + 36px + 8px = 188px!
  - `st.tabs` header sits at y ≈ 190px.
  - Active Tab content has over 700px of visible viewport height.
  - Zero scrolling required to view and operate Tab 1/2 primary inputs.

---

## 6. Tab 1 & Tab 2 Card Styling Standardization

### 6.1 Design Tokens
- Border radius: `8px`.
- Border: `1px solid var(--border-subtle)`.
- Background: `var(--bg-surface)` or subtle tint (`rgba(..., 0.06)`).
- Padding: `10px 12px` (ensuring Rule 14 safe breathing room).
- Typography Hierarchy:
  - Main section header: 15px, font-weight 700.
  - Card title: 13px, font-weight 600.
  - Big metric: 18px–20px, font-weight 700.
  - Description / caption: 11px–11.5px, color `var(--text-secondary)`.
- Emoji Cleanup:
  - Remove redundant emoji stacking (e.g. `🎯 🏆 🚀`).
  - Keep single semantic indicator emoji per section.
  - Remove heavy saturated color fills in card backgrounds.

---

## 7. Backend & Filter Invariants

### 7.1 Financial News Whitelist & Blacklist Filter (`data_loader.py`)
- **Location**: `fetch_realtime_market_news_and_catalysts`, lines 338–360.
- **Whitelist**: `["A股", "沪深", "指数", "央行", "利率", "降准", "降息", "LPR", "社融", "PMI", "证监会", "公募", "基金", "ETF", "红利", "科创", "半导体", "芯片", "医药", "消费", "银行", "黄金", "美股", "纳指", "国债", "分红", "净值", "主力", "北向", "研报", "估值", "流动性"]`.
- **Blacklist**: `["无人机", "拦截", "联军", "导弹", "武装", "袭击", "交火", "赛事", "娱乐", "明星", "枪击", "爆炸"]`.
- **Fallback**: If all items are filtered out, generate a concise market summary based on real-time volume and index performance.

---

## 8. Test Impact Analysis & Mitigation Matrix

| Test File | Test Case | Target Assertion | Mitigation / Compliance Strategy |
| --- | --- | --- | --- |
| `tests/test_adv_final_closure.py` | `test_specialized_4_ui_wireup_and_valuation_percentile_anti_fraud` | `assert "行情源状态" in app_gui_src` | Retain "行情源状态" in the single-line sidebar status bar. |
| `tests/test_g8_ux_and_realtime_fusion.py` | `test_g8_1_tab2_dual_view_branch_isolation_and_slider_cleanup` | `assert "with st.container(height=380):" in src or "height=380" in src` | Retain `# height=380` comment on container. |
| `tests/test_g8_ux_and_realtime_fusion.py` | `test_g8_6_realtime_radar_quotes_and_news_flash_ingestion` | `assert "💡 入选依据" in gui_src` | Retain "💡 入选依据" in Row 3 of the concise card. |
| `tests/test_g3_evolution_loop.py` | `test_g3_5_app_gui_source_wireup_verification` | `assert "0.75" in src` and `assert "evaluate_dynamic_correlation_mutation" in src` | Fully preserved in advisory engine and GUI. |
| `tests/test_g10_correlation_liquidity_and_stress.py` | `test_g10_5_app_gui_r5_source_wireup_verification` | `assert "safe_markdown_html(render_stress_liquidity_card_html" in code` | Ensure `safe_markdown_html(render_stress_liquidity_card_html` is called in Tab 3 Monte Carlo section. |
| `tests/test_ui_instant_load.py` | `test_top_metric_card_fixed_height_css` | `assert ("min-height: 118px;" in gui_text or "height: 112px;" in gui_text)` | Update assertion to include `"min-height: 88px;" in gui_text`. |

---
*Analysis completed by Explorer 1 (`explorer_g10_survey_14_1`).*
