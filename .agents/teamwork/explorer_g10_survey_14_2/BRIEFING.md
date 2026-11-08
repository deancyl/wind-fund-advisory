# BRIEFING — 2026-11-08T09:22:00Z

## Mission
Survey `advisory_engine.py`, `data_loader.py`, and `portfolio_manager.py` for G10 visual subtraction, quantitative rationale accuracy, news whitelist/blacklist filtering, and CVaR Monte Carlo calibration.

## 🔒 My Identity
- Archetype: teamwork_explorer
- Roles: explorer, analyst
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g10_survey_14_2\
- Original parent: 496bfcfb-72ea-446e-b3dc-c85871c12398
- Milestone: G10 Visual Subtraction and UI Elevation Survey

## 🔒 Key Constraints
- Read-only investigation — do NOT implement or edit source/test files
- Only write to working directory (.agents/teamwork/explorer_g10_survey_14_2/)
- Four referee files strictly read-only: judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py
- DataLoader.simulate_execution signature and fee logic strictly read-only

## Current Parent
- Conversation ID: 496bfcfb-72ea-446e-b3dc-c85871c12398
- Updated: 2026-11-08T09:20:48Z

## Investigation State
- **Explored paths**:
  - `AGY2_FundAdvisory/advisory_engine.py`: lines 1135-1185 (`_synthesize_quantitative_evidence`), 1316-1358 (`evaluate_sector`).
  - `AGY2_FundAdvisory/data_loader.py`: lines 62-180 (`fetch_market_turnover_and_sentiment`), 247-450 (`fetch_realtime_market_news_and_catalysts`).
  - `AGY2_FundAdvisory/portfolio_manager.py`: lines 8674-8995 (`simulate_portfolio_cvar_bootstrap`), 8995-9016 (`simulate_portfolio_cvar_bootstrap_instance`).
  - `AGY2_FundAdvisory/winrate_engine.py`: lines 935-1060 (`simulate_monte_carlo_block_bootstrap_stress`).
  - `AGY2_FundAdvisory/app_gui.py`: lines 1897-1938 (`render_stress_liquidity_card_html`), 2940-2985 (Top 3 cards), 3040-3080 (Right wing sentry), 6800-6815 (Tab 3 stress card).
- **Key findings**:
  1. `advisory_engine.py`: `er_20 < 0.35` contradiction resolved by checking ER before claiming momentum resonance; designed concise rationale strictly <= 18 Chinese characters while preserving `core_logic` for test compatibility.
  2. `data_loader.py`: Formulated 32-term whitelist and 9-term blacklist; fallback uses turnover and market sentiment.
  3. `portfolio_manager.py`: Identified root cause of -36.1% vs -12.0% (210-day 2008 loss compressed into 60 days with -0.50%/day drift vs Tab 3's real daily returns block bootstrap); designed calibration and right-wing card removal.
- **Unexplored areas**: None for survey scope.

## Key Decisions Made
- Fully documented findings in `analysis.md` and `handoff.md`.
- Ready to message parent agent with structured summary.

## Artifact Index
- DISPATCH.md — incoming dispatch instructions
- BRIEFING.md — persistent state memory
- progress.md — liveness heartbeat
- analysis.md — detailed findings and exact line numbers / code diff proposals
- handoff.md — 5-component handoff report
