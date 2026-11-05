# Task Assignment: Worker Prod M2 (Features 6-10: Global UI/UX Multi-Theme Design System & Layout)

## Authoritative Request File
`d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md` (MUST read completely before proceeding)
`d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md` (Master Architecture & Milestone Contracts)
`d:\Google\Workspace\Wind\GEMINI.md` (Workspace Rules)
`d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r7_1\report.md` (Explorer r7_1 Full Report & 5-Step Guide)
`d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r7_1\handoff.md` (Explorer r7_1 Handoff)

## Exclusive Write Ownership
`AGY2_FundAdvisory/app_gui.py`

## Physical Safety Redline (STRICTLY FORBIDDEN TO TOUCH)
- `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py` (ZERO MODIFICATIONS, SHA-256 LOCKED).

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Detailed Requirements for Implementation
1. **CSS 核心组件类与变量绑定恢复 (Feature 6)**:
   - In `app_gui.py` `<style>`: Ensure `.decision-card`, `.decision-title`, `.decision-val`, `.decision-desc`, `.kpi-card-title`, `.kpi-card-sub`, `.kpi-card-desc`, `.metric-card-sub` are 100% bound to CSS variables (`var(--bg-canvas)`, `var(--bg-surface)`, `var(--bg-elevated)`, `var(--border-subtle)`, `var(--text-primary)`, `var(--text-secondary)`, `var(--accent-primary)`, `var(--color-up)`, `var(--color-down)`).
2. **清零内联硬编码色值与动态涨跌联动 (Feature 7)**:
   - Fix dynamic profit/loss colors in `app_gui.py` L1189, L1212, L2430, L3588, etc., to dynamically use `active_co["color_up"]` / `active_co["color_down"]` (or `active_co.get("color_up", "#dc2626")` / `active_co.get("color_down", "#16a34a")`).
   - In Plotly figure functions, read `active_co["color_up"]` and `active_co["color_down"]` instead of hardcoding `#ef4444` / `#10b981`.
   - Remove inline `#ffffff`, `#f8fafc`, `#0f172a` style overrides that break dark/warm themes.
3. **文案与视觉样式去营销化 (Feature 8)**:
   - Abolish Step 2 rainbow card top borders, use subtle micro-borders and semantic pill badges.
   - Remove all exclamation marks (`！`), redundant `【】` and `《》`.
   - Primary and secondary titles <= 6~7 Chinese chars.
   - Buttons concise verb-noun phrases.
4. **5 套机构级主题配色实装 (Feature 9)**:
   - In `THEME_PRESETS`:
     1. `light_slate` (机构冷灰 - default): 清透冷灰画布 `#F8FAFC` + 纯白表面 `#FFFFFF` + 机构深蓝 `#1D4ED8`
     2. `dark_terminal` (彭博暗黑): 碳黑画布 `#0B0F17` + 蓝黑表面 `#111827` + 石墨边框 `#1F2937` + 电光蓝 `#38BDF8`
     3. `nordic_paper` (金融暖卷): 暖米画布 `#F6F4F0` + 宣纸白表面 `#FCFBF9` + 暖灰边框 `#E5E0D8` + 森林墨绿 `#0F766E`
     4. `deep_titanium` (深海钛金): 午夜蓝灰 `#0F172A` + 钛灰表面 `#1E293B` + 钢灰边框 `#334155` + 琥珀金 `#F59E0B`
     5. `nordic_frost` (极昼纯白): 纯白高对比 `#FFFFFF` + 浅灰表面 `#F4F6F8` + 锐利边框 `#E4E4E7` + 石墨黑 `#18181B`
     (Keep alias mappings for `institutional_slate`, `bloomberg_carbon`, `ft_warm_paper` so existing tests pass).
5. **顶部行情带与侧边栏职责归位 (Feature 10)**:
   - Top 6-index ticker strip: points, change %, real valuation percentile badges from M1 `IndexValuationEngine`, compact refresh button.
   - Left sidebar (🧭 全局领航台): 4 responsibilities:
     ① Visual/color center
     ② Global target & gear switch (bi-directional sync with Tab 1)
     ③ Trading risk guardrails (daily purchase limit filter + rebalance buffer)
     ④ Ledger environment management (load demo / snapshot undo / global sync valuation).
   - Zero blocking SVG sparkline requests.

## Verification Commands
After implementing, you MUST run tests:
- `py -3 -m pytest tests/test_infra.py` (Must pass 14/14)
- `cmd /c "set PYTHONPATH=AGY2_FundAdvisory;. && py -3 -m pytest AGY2_FundAdvisory/tests/test_deep_remodel_final.py -v"`
- `cmd /c "set PYTHONPATH=AGY2_FundAdvisory;. && py -3 -m pytest AGY2_FundAdvisory/tests/test_design_system_v19.py -v"`
- `cmd /c "set PYTHONPATH=AGY2_FundAdvisory;. && py -3 -m pytest AGY2_FundAdvisory/tests/test_infra.py -v"`
- Verify referee file SHA-256 hashes are untouched.

## Output Requirements
Write your detailed implementation report to:
`d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_m2\handoff.md`
Then call `send_message` to parent.


## 2026-11-04T10:58:40Z
[Message] timestamp=2026-11-04T10:58:40Z sender=c98181d5-8d61-4839-8d62-5dbcef7c85af priority=MESSAGE_PRIORITY_HIGH content=You are Worker Prod M2 for Milestone 2 (Features 6-10: Global UI/UX Multi-Theme Design System & Layout).
Working directory: d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_m2/
Read your task dispatch file: d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_m2\DISPATCH.md
Read the authoritative request file: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Read master architecture: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md
Read Explorer r7_1 Report & 5-Step Guide: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r7_1\report.md
Read Explorer r7_1 Handoff: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r7_1\handoff.md
Read workspace rules: d:\Google\Workspace\Wind\GEMINI.md
