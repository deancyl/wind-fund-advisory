# BRIEFING — 2026-11-09T07:09:00Z

## Mission
Technical exploration and concrete plan formulation for Pain Point 1 (首屏极速秒开 <150ms 与因子进化缓存机制) and Pain Point 4 (回测图文字遮挡、去除硬加Alpha、基准指数日度真实全收益曲线修复与后视镜静态持仓提示).

## 🔒 My Identity
- Archetype: explorer
- Roles: investigation, synthesis
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g13_survey_1\
- Original parent: ff97c74e-8951-4fdf-b683-3caf0969e6bd
- Milestone: G13 Survey 1 (Pain Points 1 & 4)

## 🔒 Key Constraints
- Read-only investigation — do NOT modify source code files
- Provide concrete evidence (file paths, line numbers, code snippets)
- Formulate precise, machine-applicable fix plans and handoff report

## Current Parent
- Conversation ID: ff97c74e-8951-4fdf-b683-3caf0969e6bd
- Updated: 2026-11-09T07:09:00Z

## Investigation State
- **Explored paths**:
  - `AGY2_FundAdvisory/app_gui.py`: lines 2712-3266 (`render_dual_wing_advisory_dashboard`), lines 6700-6786 (`fig_nav` and Tab 3 backtest layout), lines 1816-1848 (`apply_theme_to_plotly_figure`)
  - `AGY2_FundAdvisory/advisory_engine.py`: lines 247-814 (`OnlineHeuristicFactorEvolver`), lines 815-950 (`OpportunityRadarEngine`), lines 1874-1970 (`ActiveRiskSentry.inspect_portfolio`)
  - `AGY2_FundAdvisory/strategy_bridge.py`: lines 157-180 (`BENCHMARK_INDICES_MAP`), lines 4881-4960 (`build_custom_portfolio_backtest`, artificial alpha at line 4929)
  - `data/processed/aligned_matrix_total_return.parquet`: verified columns `H11009`, `H30269`, `930609`, `H00922`, `H00300`, `AU9999`, `SPX_CNY`
  - `data/processed/csindex_H30269.parquet`, `csindex_H11009.parquet`
- **Key findings**:
  - Pain Point 1: `render_dual_wing_advisory_dashboard` blocks main thread with 2x `OpportunityRadarEngine()`, 12-slice walk-forward genetic evolution, 3 external HTTP requests, and 4 heavy nested modules. Can be accelerated to <20ms using pure in-memory `snapshot` & `pm.holdings`, disk cache `data/cache/factor_evolution_cache.json` (12h TTL), and moving 4 depth tools to Tab 4 and 拐点尺 to Tab 1.
  - Pain Point 4: Plotly legend covers curves due to long legend names + `apply_theme_to_plotly_figure` overwriting `margin(t=30)` and `legend.bgcolor=th['bg_surface']`. Solved by setting `margin(t=75)`, `legend(y=1.06, bgcolor="rgba(0,0,0,0)")` and muted stage annotations. Line 4929 in `strategy_bridge.py` contains blatant artificial alpha `r_arr[1:] += (alpha_ann / 250.0)` which must be deleted. `BENCHMARK_INDICES_MAP["纯债指数"]` maps to `930609` instead of `H11009` which is already a daily total return series in `aligned_matrix_total_return.parquet`. Static holding backtest requires disclaimer card and one-click toggle to compare with OOS dynamic strategy.
- **Unexplored areas**: None for Pain Point 1 & Pain Point 4. Investigation complete.

## Key Decisions Made
- Confirmed exact file paths and line numbers for all target modifications.
- Synthesized concrete replacement code snippets ready for implementation agent.
- Documented verification methods using pytest and AppTest.

## Artifact Index
- `DISPATCH.md` — Initial task instruction
- `BRIEFING.md` — Persistent awareness
- `progress.md` — Progress tracker
- `handoff.md` — Complete 5-component handoff report
- `inspect_parquet.py`, `inspect_indices.py`, `inspect_csindex.py`, `check_h30269.py`, `analyze_yearly_returns.py` — Local investigation scripts
