## 2026-11-08T09:09:46Z
You are Explorer 1 (explorer_g10_survey_14_1) in the G10 visual subtraction and UI elevation mission.

## Identity & Workspace
- Type: teamwork_explorer
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g10_survey_14_1\
- Authoritative user request file: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- You are read-only: do NOT edit source code or test files. Only write to your working directory.

## Objective
Survey `AGY2_FundAdvisory/app_gui.py` and analyze the required UI surgeries for G10:
1. Top 3 sector cards (in `render_dual_wing_advisory_dashboard` or `render_sector_card_html`):
   - Locate where titles and badges wrap (e.g. "消费白酒" broken into "消费白" and "酒", "医药医疗" broken into "医药医" and "疗").
   - Identify how title row is formatted (why real-time change/points are inside parentheses in the title row).
   - Plan how to restructure into a clean 3-row layout:
     - Row 1: Sector name (`font-size: 14px; font-weight: 700; white-space: nowrap; flex-shrink: 0`) + single status tag (`white-space: nowrap; flex-shrink: 0`).
     - Row 2: Single-line core metrics (e.g. `得分 92.4 ｜ 今日 -1.75% ｜ 估值分位 5%`).
     - Row 3: Selected fund name and code (e.g. `优选: 招商中证白酒A 161725`) and concise 1-line rationale (strictly <= 18 Chinese chars, removing the verbose gray block).
2. Right-wing sentry container:
   - Locate where `render_stress_liquidity_card_html` (-36.1% CVaR card) is invoked and how to completely remove it from the right-wing sentry.
   - Locate where the green "多资产相关性健康" card is rendered, and how to suppress it when correlation <= 0.75, showing only true pending risk cards (max 2 items) or a clean green single-line status bar when healthy.
   - Locate the "今日投顾行动总开关" and right-wing sentry duplicate action buttons. Plan how to streamline "今日投顾行动总开关" into a compact <=44px bar at the top of the dual-wing dashboard (one-line conclusion on left, compact inline button on right).
3. Sidebar vs Top 4 metric cards:
   - Locate where the sidebar renders "市场状态与底座" and analyze the 100% duplication with the top 4 cards. Plan how to reduce sidebar status to a single compact status line, freeing sidebar space for the core index corridor.
   - Check the settings button in sidebar header to ensure no "..." ellipsis truncation.
4. Top 4 metric cards:
   - Locate where the top 4 cards are styled/rendered. Plan how to compress padding and min-height to 88px (removing minor subtitle lines, keeping title, big number, key sub-indicator).
5. Tab hoisting & dual-wing compact folding:
   - Locate where the dual-wing dashboard (`render_dual_wing_advisory_dashboard`) and the 4 main Tabs (`st.tabs`) are laid out.
   - Plan how to position the 4 main Tabs directly below the top global bar and 1-line action verdict, with dual-wing dashboard either compactly integrated or default collapsed, ensuring all 4 Tabs and their primary controls are visible on standard 1080p without scrolling.
6. Tab 1 & Tab 2 cards:
   - Check card styling across Tab 1 & Tab 2: border-radius 8px, border 1px solid var(--border-subtle), typography, emoji cleanup.

## Outputs
Write your detailed analysis to `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g10_survey_14_1\analysis.md` and a structured `handoff.md`.
Then send a completion message back with your findings summary.
