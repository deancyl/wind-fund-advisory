# BRIEFING — 2026-11-15T09:06:00Z

## Mission
Investigate Features 9 and 10 (Rolling DCA empirical blind test table & dynamic friction bill + full fee backtest), and produce exact implementation blueprints with code diffs.

## 🔒 My Identity
- Archetype: explorer
- Roles: [investigator, synthesizer]
- Working directory: d:\Google\Workspace\Wind
- State folder: d:\Google\Workspace\Wind\.agents\teamwork\explorer_m2_2
- Original parent: 14ba2224-f6f2-408b-8da5-a5ce3b8fff98
- Milestone: Milestone 2

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Strictly follow workspace rules (GEMINI.md) and communication guidelines
- Zero lookahead bias, strict fee deductions in rolling DCA
- Eliminate pseudo-constants in `calculate_mutual_fund_friction_bill`
- Deduct full public fund fees in `run_historical_time_machine_backtest`

## Current Parent
- Conversation ID: 14ba2224-f6f2-408b-8da5-a5ce3b8fff98
- Updated: 2026-11-15T09:06:00Z

## Investigation State
- **Explored paths**:
  - `tests/test_g19_m2_routing_and_rolling_dca.py` (TestFeature9, TestFeature10, Tier 4 Scenario 4)
  - `AGY2_FundAdvisory/strategy_bridge.py:5900-6070` (friction bill, presets), `7086-7268` (time machine backtest)
  - `AGY2_FundAdvisory/app_gui.py:7396-7520` (historical blind backtest UI)
- **Key findings**:
  1. `calculate_rolling_dca_3y_backtest` missing from `StrategyBridge`; tested sampling 18 bi-monthly and 12 quarterly periods over 750 trading days with zero lookahead and full fee deduction (win rates ~88-91%).
  2. `calculate_mutual_fund_friction_bill` has fake constants `16.85` and `-16.76`; return type annotation broke test regex; tested dynamic computation from matrix giving CAGR 4.79% for pure bond.
  3. `run_historical_time_machine_backtest` missed daily `0.0075 / 250.0` management & custody fee in `eff_day_ret`.
  4. `get_combat_29_vs_reconstructed_6_preset` missing `"raw_29"` and `"reconstructed_6"` alias keys.
- **Unexplored areas**: None for Features 9 & 10. Investigation 100% complete.

## Key Decisions Made
- Formulate complete, tested blueprints for `calculate_rolling_dca_3y_backtest` and `calculate_mutual_fund_friction_bill` dynamic calculation.
- Add UI blueprint in `app_gui.py` around line 7495 for dual-period metric cards and interactive `st.dataframe`.

## Artifact Index
- `handoff.md` — Complete 5-component technical handoff report with exact line numbers, code snippets, diffs, and verification steps.
