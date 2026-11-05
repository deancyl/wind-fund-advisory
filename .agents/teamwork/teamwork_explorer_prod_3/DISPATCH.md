## 2026-11-03T07:02:34Z
**Context**: You are Explorer 3 for the Production Deep Refactoring of Wind Advisory System.
**Working Directory**: d:\Google\Workspace\Wind\.agents\teamwork\teamwork_explorer_prod_3
**Authoritative Request File**: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
**Project Root**: d:\Google\Workspace\Wind

**Mission**: Investigate R2 — UI/UX Information Architecture & Visual Redesign in `app_gui.py`.

**Specific Tasks**:
1. Read `ORIGINAL_REQUEST.md` completely before starting.
2. Inspect `app_gui.py` and associated CSS styling:
   - Identify where `stSidebar` is hidden (e.g. `display: none` in injected CSS) and how to restore native sidebar toggling.
   - Design the sidebar as 「🧭 全局领航台」: Decouple any tab-local action buttons (keep local operations inside respective tabs). Design the 4 modules:
     ① 实时市场状态与数据底座健康度
     ②【🌱 新资建仓】当前推演方案快照
     ③【💼 实盘持仓】账本核心快照
     ④ 全局行情一键刷新入口
3. Inspect the top 6 core index tickers (沪深300, 科创50, 中证红利, 中证500, 中证1000, 黄金ETF):
   - Locate current implementation in `app_gui.py`.
   - Redesign layout, proportions, font sizes, red-up/green-down tags so that all 6 indices fit on a single line full-width without truncation.
4. Inspect the 4 quantitative model descriptions and 6-dimensional scoring formula:
   - Locate where `st.dataframe` displays the model table and replace with responsive wrapping grid cards (dimensions: 【它解决什么问题】、【怎么分配资金】、【适合什么行情】).
   - Locate the 6-dim scoring formula and design `st.popover("ⓘ 评分细则")` detailing criteria for all 6 dimensions (超额收益35%、低费率25%、底层排雷15%、聪明钱10%、反拥挤10%、宏观契合5%).
5. Inspect "方案核心逻辑（三句话看懂本方案）":
   - Locate the existing 4-column static cards.
   - Design 3 wide deep-attribution cards (💰 怎么赚钱 / 🏆 为什么能赢 / 🚨 风险与铁律).
   - Ensure 100% dynamic data wiring: read real portfolio breakdown (defensive dividend vs elastic growth), name top weighted fund, embed selected model logic, compute max drawdown and underwater recovery days based on actual capital.
6. Audit all titles across the entire app (tabs, modules, cards, expanders):
   - Check against the <= 7 Chinese characters rule. List all titles exceeding 7 characters and propose concise replacements.
7. Note read-only constraints: DO NOT modify `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`.
