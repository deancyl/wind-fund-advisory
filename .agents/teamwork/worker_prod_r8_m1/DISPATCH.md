## 2026-11-05T01:52:04Z
You are Worker Prod R8-M1.
Your working directory is d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r8_m1\.
Read the original user request at: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md.
Read the project plan at: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md.
Read the Explorer analysis at: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r8_1\analysis.md.
Also review the project rules at: d:\Google\Workspace\Wind\GEMINI.md.

YOUR TARGET: Milestone 1 - 侧边栏核心指数走廊升级、全市场自由定制与 UI 细节修复 (Features 1-6)

FILE WRITE OWNERSHIP:
You have exclusive write ownership of:
- `AGY2_FundAdvisory/app_gui.py`
- `AGY2_FundAdvisory/data_loader.py`
- `data/cache/custom_watchlist.json`
You MUST NOT modify any other files without permission.

PHYSICAL SAFETY REDLINE:
NEVER touch or modify the 4 readonly referee files:
`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

SPECIFIC IMPLEMENTATION TASKS:
1. Feature 1 (侧边栏样式类名修复):
   In `app_gui.py` CSS, update class selectors to support union selectors `.val-very-low, .val-very_low` and `.val-very-high, .val-very_high`, ensuring proper border and background color rendering for very low and very high valuation tags.
2. Feature 2 (真实行情与离线双日收盘价涨跌幅):
   In `data_loader.py` (`fetch_custom_realtime_indices`, `fetch_batch_realtime_indices`), prioritize EastMoney push2 / Sina batch API. When market is closed, offline, or returns 0.00%, calculate real price return from the latest 2 trading days in `data/processed/aligned_matrix_total_return.parquet` or local index files in `data/processed/indices/*.parquet`. Completely eliminate fake 0.00% flat rows!
3. Feature 3 (侧边栏卡片 3 层专业指标流):
   In `app_gui.py` sidebar card rendering:
   - Row 1: Index name, code, latest price, and return capsule (strictly adhere to Flexbox anti-squash: `flex: 0 0 auto !important; white-space: nowrap !important;`);
   - Row 2: Real PE/PB valuation percentile tag & 20-day cumulative return;
   - Row 3: MA20 trend and bias status (e.g., "站上 MA20 偏离 +1.5%" or "跌破 MA20 防守").
4. Feature 4 (38+ 全市场指数/ETF 目录与弹窗设置):
   - In `data_loader.py`, expand the built-in catalog to 38+ indices/ETFs across 12 sectors (broad-based, dividend, tech, pharma, consumer, finance, new energy, military, cyclical, HK, US, gold, treasury). Strictly lock CSI Dividend to `000922` (Rule 16 Invariant, never `000015`).
   - In `app_gui.py` sidebar, implement the top-right settings modal dialog with:
     - 3~15 display count slider;
     - Multiselect list supporting pinyin/code/name search, preserving selected order;
     - Arbitrary 6-digit code real-time validation input (validates name and quote before adding to corridor).
5. Feature 5 (自选走廊持久化):
   Ensure watchlist config is saved to and loaded from `data/cache/custom_watchlist.json`, with seamless cold-start recovery.
6. Feature 6 (UI 细节修复):
   - Primary button white text: In `app_gui.py` CSS, add `button[kind="primary"] * { color: #ffffff !important; }` to guarantee white text in all themes.
   - Tab 1 Step 1 text deduplication: In `app_gui.py`, merge the repeated strategy anchor and equity cap descriptions between the top grey box and caption into a single clean strategy anchor card.
7. Verification:
   Run verification commands:
   - `py -3 scripts/verify_referee_hashes.py`
   - `py -3 -m pytest AGY2_FundAdvisory/tests/test_sidebar_remodel_and_bugfixes.py`

When finished, write a detailed handoff report to `d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r8_m1\handoff.md` and send a message to the orchestrator.
