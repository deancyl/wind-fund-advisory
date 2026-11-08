# DISPATCH for explorer_g9_survey_2

## Objective
Survey and deeply investigate R2: 全局交互降噪、HTML 纯化与傻瓜化操作流重构 (L1 傻瓜层 + L2 机构白盒层).

## Inputs
- `AGY2_FundAdvisory/app_gui.py`
- `c:\Users\deanc\Downloads\agy2_fundadvisory_ui_architecture_evaluation.md`
- `c:\Users\deanc\Downloads\agy2_app_gui.md`
- `.agents/teamwork/ORIGINAL_REQUEST.md`

## Specific Investigation Tasks
1. HTML Leakage & Purification (Rule 27):
   - Locate `render_historical_inflection_ruler_html` and all rich-text HTML rendering functions in `app_gui.py`.
   - Identify where indented triple-quoted HTML triggers CommonMark 4+ space code blocks.
   - Plan implementation of `_clean_html(...)` and universal `safe_markdown_html(...)` to ensure zero raw HTML code leakage.
2. Top Wing Dashboard & Master Switch:
   - Design "今日投顾行动总开关" at the top of the dual-wing dashboard (one plain sentence recommendation + one-click workspace jump).
   - Left wing: default to refined market pulse + Top 3 sector cards; collapse 14-sector thermometer and 60d trajectory.
   - Right wing: clean slogan suffix, auto-height without clipping.
3. Tab 1 New Capital Simplification:
   - Step 1: Principal (with Chinese Wan check) + C1-C5 risk, auto-managed parameters, collapsible expert fine-tuning panel.
   - Step 2 & 3: One-click simulate + generate execution sheet.
   - 16-card reduction: 3 human-readable big conclusion cards in L1, collapsible white-box evidence drawer in L2.
4. Tab 2 Portfolio Rebalancing Simplification:
   - Combine top overview cards with cushion watchdog card; collapse -3%/-5%/-10% stress scenarios.
   - Convert 5-column quick fund entry bar into "➕ 极速录基" Popover in table toolbar.
   - Strict dual-view physical isolation (decision mode vs ops ledger mode).
   - Clean duplicate buffer sliders.

## Output
Write comprehensive survey and technical recommendations to:
`d:\Google\Workspace\Wind\.agents\teamwork\explorer_g9_survey_2\handoff.md`

## 2026-11-08T05:51:25Z
You are explorer_g9_survey_2 (Role: GUI Architecture Explorer).
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g9_survey_2
Read d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md before starting work.
Read d:\Google\Workspace\Wind\.agents\teamwork\explorer_g9_survey_2\DISPATCH.md for your detailed task requirements.
Also read the reference documents:
- c:\Users\deanc\Downloads\agy2_fundadvisory_ui_architecture_evaluation.md
- c:\Users\deanc\Downloads\agy2_app_gui.md
- AGY2_FundAdvisory/app_gui.py

Investigate R2: 全局交互降噪、HTML 纯化与傻瓜化操作流重构 (L1 傻瓜层 + L2 机构白盒层):
1. HTML Leakage & Purification:
   - Check render_historical_inflection_ruler_html and all rich text HTML components in app_gui.py.
   - Design _clean_html(...) to strip leading/trailing spaces and blank lines, and safe_markdown_html(...) to render safely without triggering CommonMark 4+ space code blocks.
2. Top Wing Dashboard:
   - "今日投顾行动总开关": one plain sentence action recommendation + one-click workspace jump.
   - Left wing: refined market pulse + Top 3 sector cards; collapse 14-sector thermometer & 60d trajectory.
   - Right wing: remove dev slogan suffix, auto-height without clipping.
3. Tab 1 New Capital:
   - Step 1: Principal (with Chinese Wan check) + C1-C5 risk, AI auto-managed parameters, collapsible expert fine-tuning panel.
   - Merge simulate + generate execution sheet into one-click action.
   - Step 2: collapse 16 cards into 3 human-readable big conclusion cards in L1, collapsible white-box evidence drawer in L2 (10k Monte Carlo, black swan stress, 28k fund funnel).
4. Tab 2 Portfolio Rebalancing:
   - Merge top 4 overview cards + cushion watchdog card; collapse -3%/-5%/-10% stress scenarios.
   - Convert 5-column quick fund entry bar into "➕ 极速录基" Popover in table toolbar.
   - Strict dual-view physical isolation: "持仓诊断与智能调仓" vs "账本运维与实盘复盘档案". Clean duplicate buffer sliders.

Write your findings, UI architecture plan, and line-level recommendations to:
d:\Google\Workspace\Wind\.agents\teamwork\explorer_g9_survey_2\handoff.md

When complete, send a message to orchestrator_12 notifying completion.

## 2026-11-08T06:03:09Z
**Context**: G9 Survey on R2 GUI Architecture
**Content**: Checking on your progress regarding R2 GUI Architecture investigation and handoff.md generation. Both explorer 1 and explorer 3 have submitted their handoffs. How is your analysis of app_gui.py and the evaluation docs progressing?
**Action**: Please provide an update on your current findings or complete and submit your handoff.md.
