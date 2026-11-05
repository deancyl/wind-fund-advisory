## 2026-11-03T07:01:46Z
**Context**: You are Explorer 2 for the Production Deep Refactoring of Wind Advisory System.
**Working Directory**: d:\Google\Workspace\Wind\.agents\teamwork\teamwork_explorer_prod_2
**Authoritative Request File**: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
**Project Root**: d:\Google\Workspace\Wind

**Mission**: Investigate R1.2 — Holding Period Win Rate & Sample Expansion.

**Specific Tasks**:
1. Read `ORIGINAL_REQUEST.md` completely before starting.
2. Locate where holding period win rate (持有期胜率, rolling win rate, DCA win rate) is currently calculated in the codebase (e.g. `strategy_bridge.py`, `portfolio_manager.py`, `winrate_engine.py`, `historical_data`, etc.).
3. Inventory local historical datasets available in the workspace:
   - Check DuckDB tables, parquet files, CSVs, SQLite databases for major index series (000300, 000688, 000905, 000852, 000922, 518880, etc.) and fund NAV historical data.
   - Assess data range, frequency, and sample length.
4. Investigate how to extend the historical backtest span and rolling window samples to maximize statistical completeness.
5. Formulate the technical design for the dual-mode comparison/switch on the win rate dashboard:
   - Mode A: 「🎯 当下相似行情胜率（基于当前估值/利率状态机核密度加权）」
   - Mode B: 「🌐 全历史跨牛熊无差别胜率（含历次牛市顶点站岗与极端熊市样本）」
   - Explicitly calculate and display effective evaluation window sample count.
6. Note any read-only constraints: DO NOT modify `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`.
