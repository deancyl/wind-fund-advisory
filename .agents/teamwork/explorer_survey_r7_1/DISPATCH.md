# Task Assignment: Explorer Survey r7_1 (UI/UX Design System & 5 Themes)

## Authoritative Request File
`d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md` (MUST read completely before proceeding)

## Objective
Thoroughly explore the codebase for Requirement R1:
1. CSS Core Component Classes & Variables:
   - Check `AGY2_FundAdvisory/app_gui.py` `<style>` section.
   - Investigate `.decision-card`, `.decision-title`, `.decision-val`, `.decision-desc`, `.kpi-card-title`, `.kpi-card-sub`, `.kpi-card-desc`, `.metric-card-sub`.
   - Ensure 100% binding to CSS variables: `var(--bg-canvas)`, `var(--bg-surface)`, `var(--bg-elevated)`, `var(--border-subtle)`, `var(--text-primary)`, `var(--text-secondary)`, `var(--accent-primary)`, `var(--color-up)`, `var(--color-down)`.
2. Clear hardcoded colors and dynamic up/down color binding:
   - Scan all `safe_markdown_html` calls and Plotly figure creation functions in `app_gui.py`.
   - Find all hardcoded `#ffffff`, `#f8fafc`, `#0f172a`, etc., and identify how to replace them with CSS classes or `active_co`.
   - Check Python dynamic profit/loss colors and Plotly colors: ensure they dynamically read active `active_co` (A-share red-up/green-down vs International green-up/red-down).
3. Text & styling de-marketing:
   - Identify rainbow top borders in Step 2 cards and how to replace them with subtle micro-borders and semantic pill badges.
   - Scan and locate all exclamation marks (`！`), redundant `【】` and `《》`.
   - Ensure primary/secondary titles <= 6~7 chars, buttons concise verb-noun phrases.
4. Implement 5 institutional theme presets in `THEME_PRESETS`:
   1) `light_slate` (Institutional Cold Slate - default)
   2) `dark_terminal` (Bloomberg Dark)
   3) `nordic_paper` (Financial Warm Paper)
   4) `deep_titanium` (Deep Titanium)
   5) `nordic_frost` (Arctic White)
   Check current `THEME_PRESETS` in `app_gui.py` and exact color definitions.
5. Top banner & Sidebar layout:
   - Main page: Under top 4 status cards, restore full-width 6 core index real-time ticker strip (points, change %, real valuation percentile tag, compact refresh button).
   - Left sidebar (🧭 全局领航台): remove blocking SVG sparkline requests; ensure 4 responsibilities:
     ① Visual/color center
     ② Global target & gear switch (bi-directional sync with Tab 1)
     ③ Trading risk guardrails (daily purchase limit filter + rebalance buffer)
     ④ Ledger environment management (load demo / snapshot undo / global sync valuation).

## Working Directory
`d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r7_1/`

## Output Requirements
Write comprehensive analysis and concrete implementation plan to:
`d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r7_1\report.md`
Then call `send_message` to parent.


## 2026-11-04T09:25:10Z
Received dispatch from parent c98181d5-8d61-4839-8d62-5dbcef7c85af:
Focus: Requirement R1 (全局 UI/UX 多配色设计系统重塑 & 5 套机构级主题配色)
1. Investigate AGY2_FundAdvisory/app_gui.py and its <style> section.
2. Locate and document .decision-card, .decision-title, .decision-val, .decision-desc, .kpi-card-title, .kpi-card-sub, .kpi-card-desc, .metric-card-sub and their bindings to CSS variables.
3. Find all hardcoded color literals in safe_markdown_html and Plotly figure builders. Determine how to eliminate them. Check active_co.
4. Check Step 2 cards rainbow borders, replace with subtle micro-borders and pill badges. Scan and list all exclamation marks, brackets (【】, 《》), check title lengths and button phrases.
5. Inspect THEME_PRESETS and specify exact color palettes for all 5 themes.
6. Check top 6 core index ticker strip restoration and left sidebar refactoring.
