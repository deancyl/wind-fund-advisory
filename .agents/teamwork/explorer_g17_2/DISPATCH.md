# Task Assignment for Explorer G17-2

## Role
UI & Mobile Layout Explorer

## Objectives
1. Inspect the mobile screenshot issues and audit document:
   - Audit plan: `c:\Users\deanc\Downloads\agy2_ui_ux_audit_and_fix_plan (6).md`
   - Mobile issue screenshot: `C:/Users/deanc/.gemini/antigravity/brain/1395b6f9-733c-4446-9cdb-f33a19e5f711/.user_uploaded/media_1794406255999_c8abd7ad.png`
2. Investigate `app_gui.py` CSS and DOM structure:
   - In `@media (max-width: 768px)` and `<= 640px`, inspect why the 4th tab 「🔍 穿透工具」 is cut off/overflows horizontally.
   - Design the CSS rule forcing the top main navigation into a 2x2 grid: `grid-template-columns: repeat(2, 1fr) !important; gap: 6px !important;` with button height `40px !important; font-size: 14px !important;`.
   - Design 2x2 grid for the top 4 global metric cards on mobile to reduce vertical height by 50%.
3. Reconstruct first-screen Five-Dimension Memo and Chief Advisor Desk:
   - Eliminate the 600-word wall of text and stacked redundant cards.
   - Combine the current five-dimension memo box and "今日投顾参谋折叠框" into a single "🧭 首席投顾今日裁决台":
     - Default visible part height strictly <= 110px:
       - Row 1: Today's core verdict + position causal derivation formula + data timestamp (fix flex-wrap to prevent badge squishing).
       - Row 2: 5 compact capsules (desktop 1 row 5 cols, mobile 2 cols flow grid) showing <= 20 words summary for Macro Policy, Global FX, Industry Sweet Spot, Portfolio Bottleneck, 14:30 Tail Order.
     - Expandable detail: "🔭 展开十维深度逻辑、Top 3 机会雷达与十三维风控体检详情" displaying full text, 3 sector cards, and 13-dimension risk list.
4. Auto-route to Tab 1 on ledger switch:
   - In `switch_active_ledger(target_ledger_id)`: when switching to a ledger with existing holdings (like `实战存量组合（29只·¥26,615.10）`), automatically trigger tab switch to `tab_index: 1` (`💼 持仓调仓`), and auto-expand the 29-fund diagnostic cards.
5. Table column display optimization:
   - On mobile/desktop, reorder DataFrame columns to prioritize: "基金名称(含代码)、持有/建议金额、盈亏率/目标权重、操作裁决" in the first 3-4 columns.
   - Collapse the 5 stacked gray cards below tables.
6. Write your comprehensive analysis report to `.agents/teamwork/explorer_g17_2/analysis.md`.


## 2026-11-11T14:21:25Z
You are an Explorer for the G17 generation.
Read your task description in: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g17_2\DISPATCH.md
Also read ORIGINAL_REQUEST.md: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Your state folder: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g17_2\
Write your analysis to: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g17_2\analysis.md
When finished, send a brief message to parent with your summary and handoff report path.
DO NOT write or modify implementation code. You are an Explorer (read-only investigation).
Follow all workspace rules in GEMINI.md.
