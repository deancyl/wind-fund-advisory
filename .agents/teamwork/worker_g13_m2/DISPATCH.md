## 2026-11-09T07:48:18Z

You are worker_g13_m2, a teamwork_worker.
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\worker_g13_m2\
You MUST read the user's original request file before starting:
d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Also read the detailed Explorer 2 handoff report (crucial, has exact code line numbers and CSS templates):
d:\Google\Workspace\Wind\.agents\teamwork\explorer_g13_survey_2\handoff.md
And Explorer 1 handoff report:
d:\Google\Workspace\Wind\.agents\teamwork\explorer_g13_survey_1\handoff.md
And reference:
d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_1\PROJECT.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

PHYSICAL SAFETY RED LINES:
- NEVER touch or modify the 4 strictly read-only files:
  `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py` (and `AGY2_FundAdvisory/tests/test_infra.py`).
- `DataLoader.simulate_execution` default signature and default fee deduction logic MUST remain 100% intact.

YOUR SCOPE & WRITE OWNERSHIP (Milestone 2: UI/UX 全面重构、砍除伪交易按钮、全宽大胶囊导航与图例上浮):
File you own exclusively:
- `AGY2_FundAdvisory/app_gui.py`

DETAILED TASKS:
1. 首屏零阻塞秒开在 `app_gui.py` 的彻底落地:
   - In `render_dual_wing_advisory_dashboard`:
     Thoroughly forbid calling `OpportunityRadarEngine()`, `evolve_factor_weights()`, `get_60d_rolling_nav_and_trajectory()`, `fetch_realtime_market_news_and_catalysts()`, `fetch_etf_feeder_arbitrage_sensors()`, `fetch_options_implied_volatility_sensors()`, `evaluate_all_qdII_fx_arbitrage()` on default initial page load!
     Top advisory tip bar must be purely in-memory using `snapshot` and `pm.holdings` (<10ms).
     When user expands radar detail or popover, use cached data from `data/cache/factor_evolution_cache.json` or precomputed radar dynamic metrics.
2. 彻底删除首屏右上角红色大按钮与右侧空白死区:
   - In `render_dual_wing_advisory_dashboard` (around L2786-2804):
     Delete `col_wing_btn` and `btn_master_action_switch` ("👉 查看锁仓保护 / 查看今日调仓单 / 检视持仓账本").
     Eliminate `col_wing_exp, col_wing_btn = st.columns([8.2, 1.8])`, make `st.expander` 100% full width!
     Advisory bar text must be human-readable, e.g.:
     `今日投顾参谋：持仓含 2 只未满 7 天标的，赎回需扣 1.5% 惩罚费，调仓算法已自动为您避开卖出 ｜ 点击展开市场机会与持仓体检` (dynamically based on locked fund count).
3. 彻底清理双翼看板内部的所有伪操作跳转按钮与臃肿嵌套:
   - Right-wing sentry: delete "一键批量锁定这2只标的调仓下界" button (`btn_batch_lock_all_7d`), and delete all buttons like "择机置换", "平衡赛道敞口", "穿透到底层" (`btn_sentry_act_*`, `btn_sentry_evid_*`) under each risk card. Right-wing only displays a clean, compact buttonless list with 1~3 core risk tips & recommendations.
   - Left-wing sector cards: delete the 3 "+ 入备选池" buttons (`btn_add_radar_pool_*`), directly display the selected fund name and 6-digit code in the card.
   - Move 5 bloated nested modules out of dual-wing expander:
     ① Nested "历史三大牛熊拐点实盘对照尺": remove from dual-wing dashboard (eliminate text collision); keep only in Tab 1 smart DCA mode and fix width/flex to prevent overlap.
     ② "查看全市场 14 大赛道量化温度计总表"
     ③ "场内ETF与场外联接 14:45 尾盘折溢价套利感知"
     ④ "50ETF与300ETF认沽期权隐含波动率防暴跌哨"
     ⑤ "跨境QDII溢价与外汇期货锁汇成本套利精算"
     Move tools ②-⑤ into Tab 4 "穿透工具" secondary sub-tabs (keep their expander headers intact as sub-modules).
     Ensure dual-wing expander expanded height strictly <= 220px with just "左翼 Top 3 赛道卡 + 右翼极简风险提示列表".
4. 全宽四宫格大胶囊主导航栏 CSS 改造:
   - In CSS injection block of `app_gui.py`:
     - Style `[data-testid="stMainBlockContainer"] > div > div > [data-testid="stTabs"] > [data-baseweb="tab-list"]`:
       `display: grid !important; grid-template-columns: repeat(4, 1fr) !important; gap: 10px !important; background: var(--bg-elevated) !important; padding: 6px !important; border-radius: 10px !important; border: 1px solid var(--border-subtle) !important; margin-bottom: 14px !important;`
     - Style top main tab buttons:
       `height: 46px !important; font-size: 16px !important; font-weight: 700 !important; border-radius: 8px !important; justify-content: center !important; background: var(--bg-surface) !important; border: 1px solid var(--border-subtle) !important; box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;`
     - Style active main tab button `button[aria-selected="true"]`:
       `background: var(--accent-primary) !important; color: #ffffff !important; border-color: var(--accent-primary) !important; box-shadow: 0 4px 12px rgba(29, 78, 216, 0.25) !important;`
       And force all internal span / p text in active button to `#ffffff !important`.
     - Strict isolation: ensure Tab 4 secondary sub-tabs keep their compact underline style (use `:not([data-testid="stTabContent"] ...)` selectors as detailed in Explorer 2 report).
5. 消除四大主 Tab 内部开头重复打印的巨型标题与 Tab 4 顶栏合并:
   - Delete duplicate `st.subheader("🌱 新资建仓")`, `st.subheader("💼 持仓调仓")`, `st.subheader("📈 组合回测")`, `st.subheader("🔍 穿透工具")` and captions from the beginning of the 4 tabs.
   - In Tab 4, merge "选择穿透体检组合对象" and "当前体检组合成分档案" into a single compact top summary row.
6. Tab 3 回测图 Plotly 图例上浮透明与零遮挡:
   - In Tab 3 Plotly figure layout (`fig_nav` around L6770-6790):
     Ensure `legend=dict(orientation="h", yanchor="bottom", y=1.06, xanchor="left", x=0, bgcolor="rgba(0,0,0,0)")` and `margin=dict(t=75, l=10, r=10, b=10)` are preserved (or applied after `apply_theme_to_plotly_figure` so they are not overwritten!).
     Move bull/bear stage text to top edge with muted color. Ensure zero text/legend overlapping curves.

Verification:
- Run AppTest or unit tests (e.g. `py -3 -m pytest tests/test_infra.py`).
- Ensure no Python syntax errors or crashes when importing `app_gui.py`.

Deliver your complete report to:
`d:\Google\Workspace\Wind\.agents\teamwork\worker_g13_m2\handoff.md`
And notify parent via send_message.
