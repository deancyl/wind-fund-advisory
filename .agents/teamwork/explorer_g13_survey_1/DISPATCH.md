## 2026-11-09T06:56:27Z
You are explorer_g13_survey_1, a teamwork_explorer.
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g13_survey_1\
You MUST read the user's original request file before starting:
d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Also refer to external audit files if helpful:
c:\Users\deanc\Downloads\agy2_ui_ux_audit_and_fix_plan (1).md
c:\Users\deanc\Downloads\agy2_fundadvisory_5_screenshots_diagnosis_and_fix.md

Your mission is technical exploration and concrete plan formulation for Pain Point 1 and Pain Point 4:
1. Pain Point 1 (首屏极速秒开 <150ms 与因子进化缓存机制):
   - In `app_gui.py`: inspect `render_dual_wing_advisory_dashboard` and its callers. Find all synchronous heavy calls: `OpportunityRadarEngine()`, `evolve_factor_weights()`, `get_60d_rolling_nav_and_trajectory()`, `fetch_realtime_market_news_and_catalysts()`, `fetch_etf_feeder_arbitrage_sensors()`, `fetch_options_implied_volatility_sensors()`, `evaluate_all_qdII_fx_arbitrage()`.
   - Pinpoint how to make the top advisory tip bar purely in-memory (<20ms) using only `snapshot` and `pm.holdings`.
   - In `advisory_engine.py` (and wherever `OnlineHeuristicFactorEvolver` is defined): locate `get_60d_rolling_nav_and_trajectory()`. Design disk caching in `data/cache/factor_evolution_cache.json` (valid for 12 hours) so that it NEVER runs on initial page load, and only recalculates when the user explicitly expands radar details and clicks a refresh button.
2. Pain Point 4 (回测图文字遮挡、去除硬加Alpha、基准指数日度真实全收益曲线修复与后视镜静态持仓提示):
   - In `app_gui.py`: inspect Tab 3 Plotly figure layout (`fig_nav`). Check legend settings, margin, annotations for bull/bear cycles, and verify how to move legend above chart (`legend=dict(orientation="h", yanchor="bottom", y=1.06, xanchor="left", x=0, bgcolor="rgba(0,0,0,0)")`, `margin=dict(t=75, l=10, r=10, b=10)`), and move bull/bear stage text to top edge with muted color.
   - In `strategy_bridge.py`: inspect `build_custom_portfolio_backtest`. Locate and check artificial alpha addition (`r_arr[1:] += (alpha_ann / 250.0)`).
   - Check how benchmarks like `H11009` (pure bond) and `H30269` (dividend low vol) are extracted from `aligned_matrix_total_return.parquet`. Forbid linear interpolation for `H11009`, ensure daily historical total return series are used.
   - Check how to add explicit disclaimer on static holding backtest: "当前持仓静态权重历史回溯（含历史后视镜权重效应，非滚动样本外实盘记录）", and provide one-click toggle to compare with "全天候滚动样本外动态策略曲线".

Hard constraints:
- You are read-only. Do NOT modify source code files.
- Produce your comprehensive report at:
  d:\Google\Workspace\Wind\.agents\teamwork\explorer_g13_survey_1\handoff.md
- Report your findings back via send_message.
