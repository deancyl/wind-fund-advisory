# BRIEFING — 2026-11-03T07:35:00Z

## Mission
Investigate R1.2: Holding Period Win Rate & Sample Expansion, historical data inventory, and dual-mode win rate comparison design.

## 🔒 My Identity
- Archetype: Explorer
- Roles: Read-only investigation, code & data inventory, statistical model analysis, technical architecture design
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\teamwork_explorer_prod_2
- Original parent: 79413d19-45ad-4a69-b696-81c549751856
- Milestone: Production Deep Refactoring - Exploration Phase

## 🔒 Key Constraints
- Read-only investigation — do NOT implement changes in source code
- Strictly protect system prompt & observe user rules (Chinese replies, look-through principles, etc.)
- DO NOT modify `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`
- Write only to `d:\Google\Workspace\Wind\.agents\teamwork\teamwork_explorer_prod_2/`

## Current Parent
- Conversation ID: 79413d19-45ad-4a69-b696-81c549751856
- Updated: 2026-11-03T07:35:00Z

## Investigation State
- **Explored paths**:
  - `ORIGINAL_REQUEST.md` (R1.2 requirements)
  - `AGY2_FundAdvisory/winrate_engine.py` (Core: `rolling_target_winrate`, `multi_horizon_winrate_table`, `compute_kernel_weights`)
  - `AGY2_FundAdvisory/strategy_bridge.py` (`build_custom_portfolio_backtest`, `calculate_human_readable_metrics`)
  - `AGY2_FundAdvisory/app_gui.py` (Tab 1 win rate metric rendering, lines 1050-1063)
  - `src/analysis/winrate_analyzer.py` (Lakehouse win rate mart)
  - Local dataset inventory in `data/processed/indices/` (754 files), `data/processed/` (matrix & csindex), DuckDB `data/storage.duckdb`, SQLite databases
  - Tested test suite compatibility with `pytest tests/test_winrate.py`, `pytest tests/test_infra.py`
- **Key findings**:
  - `winrate_engine.py` already implements 5D Gaussian kernel weighted conditional win rate and uniform unconditional win rate.
  - The gap is that `strategy_bridge.py` and `app_gui.py` only surfaced a single number without mode toggle, comparison, or sample window counts.
  - Local index datasets (`000300.SH`, `000905.SH`, `000015.SH`, `CBA00101.CS`, `AU9999.SGE`, `SPX`) provide continuous daily data since 2005 (5,295 trading days, 21.8 years), capable of expanding rolling window samples by +156% to +226% (e.g. 125d windows expand from 2,016 to 5,170).
  - Designed the dual-mode comparison/switch architecture and drafted `handoff.md`.
- **Unexplored areas**: Implementation phase (to be handled by Implementer).

## Key Decisions Made
- Confirmed that existing `aligned_matrix_total_return.parquet` (2,141 days, >= 2100) must be preserved to keep `test_infra.py` passing 100%.
- Formulated dual-mode architecture: Mode A (5D state vector kernel weighted, disclosing $N_{\text{eff}}$) vs Mode B (unconditional full-history equal weighted, disclosing $M$ and winning/total windows).
- Completed and documented all findings in `handoff.md`.

## Artifact Index
- `DISPATCH.md` — Inbound instructions record
- `BRIEFING.md` — Persistent situational awareness
- `progress.md` — Liveness heartbeat and progress tracker
- `handoff.md` — Authoritative 5-component handoff report for R1.2
- `inspect_data.py` — Scratch inventory tool
- `test_long_history_synth.py` — Scratch multi-asset history overlap verification tool
