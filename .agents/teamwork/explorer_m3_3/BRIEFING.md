# BRIEFING — 2026-11-11T02:39:40Z

## Mission
Investigate Tab 3 backtest preset ("实战存量组合：原始29基 vs 投顾重构6基") and 2024.09 policy reversal rally dynamic rebalance lag fix in `strategy_bridge.py` and `app_gui.py`, respecting the constraint of never modifying `DataLoader.simulate_execution` default signature or fee logic.

## 🔒 My Identity
- Archetype: explorer
- Roles: read-only investigation, code analysis, synthesis, structured report
- Working directory: d:\Google\Workspace\Wind
- State folder: d:\Google\Workspace\Wind\.agents\teamwork\explorer_m3_3
- Original parent: 97fbe156-e8f7-47df-8b1d-f8a8c1c69a5e
- Milestone: Milestone 3 Item 3 (Tab 3 Backtest & Dynamic Lag Fix)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement / do NOT modify any source code files
- DO NOT modify `DataLoader.simulate_execution` default signature or default fee logic
- Adhere strictly to project GEMINI.md rules (Rule 1, 2, 7, 18, 19, 20, 21, etc.)
- Use Chinese for communication and reports

## Current Parent
- Conversation ID: 97fbe156-e8f7-47df-8b1d-f8a8c1c69a5e
- Updated: 2026-11-11T02:39:40Z

## Investigation State
- **Explored paths**:
  - `AGY2_FundAdvisory/strategy_bridge.py` (`build_custom_portfolio_backtest`, `run_historical_time_machine_backtest`, `strategy_fn_for_tier`)
  - `AGY2_FundAdvisory/app_gui.py` (Tab 3 `render_tab3_backtest_content`)
  - `AGY2_FundAdvisory/data_loader.py` (`DataLoader.simulate_execution`)
  - `AGY2_FundAdvisory/multi_ledger_manager.py` (`combat_29_funds` decomposition)
  - `tests/test_infra.py`, `tests/test_adversarial_m2_challenger2_timemachine_and_memo.py`, `tests/test_challenger_m2_adversarial.py`, `tests/test_g15_phase2_memo_and_timemachine.py`
- **Key findings**:
  1. `DataLoader.simulate_execution` is an inviolable referee method; signature and parameters must remain 100% untouched.
  2. The 2024.09 policy reversal lag in the time machine was caused by freezing `norm_w` on day 0 (2024-09-18). The strategy generated an 84% equity breakout signal on 2024-09-24, but the static backtest missed it. Dynamic Point-in-Time rebalancing boosts 3M return from +6.73% to +32.29%, delivering +7.77% Alpha over CSI 300.
  3. The 29-fund portfolio ($¥26,615.10$) mathematically condenses into 6 funds ($100.00\%$ cent-level preservation), eliminating $0.40\%$ C-class annual fees and reclaiming $¥442.70$ in zero-fee fragment liquidity.
  4. Tab 3 should introduce the preset mode `"🎯 实战存量组合：原始29基 vs 投顾重构6基（近1年真规则回测对比）"` and expand `code_to_col_alpha` for all 29 funds.
- **Unexplored areas**: None. Exploration task 100% complete.

## Key Decisions Made
- Reconstructed 6 funds exact weights defined: `005561` (30.49%), `110020` (21.80%), `017436` (17.05%), `002351` (17.54%), `011612` (7.79%), `000216` (5.33%).
- `dynamic_rebalance` in `run_historical_time_machine_backtest` must default to `False` for strict backward compatibility with existing tests, with Tab 3 UI providing a toggle (`default=True`).

## Artifact Index
- `DISPATCH.md` — incoming instructions log
- `BRIEFING.md` — persistent working memory
- `progress.md` — liveness heartbeat
- `analysis.md` — detailed technical findings and proposals
- `handoff.md` — 5-component handoff report
