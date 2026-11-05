# Project: 专业买方投顾终端进阶升级 (Advisor Terminal Advanced Upgrade)

## Architecture
- **Financial Facts & Compliance Engine**:
  - `AGY2_FundAdvisory/advisory_engine.py`:
    - `RADAR_SECTOR_CATALOG["dividend_low_vol"]`: benchmark_index 与 index_code 彻底纠偏为 `H30269`，消除 `000978` 医药100指数错配。
    - `_calc_dynamic_sector_metrics`: 统一 14 赛道动量与 Bias20 价格口径，对红利类指数引入分红密集期孤立脉冲跳空平滑机制，消除假性超买误报。
  - `AGY2_FundAdvisory/data_loader.py`:
    - `IndexValuationEngine`: 移除 H30269 词条中的 `"aliases": ["000978"]`，单源同真映射 `csindex_H30269.parquet`。
  - `AGY2_FundAdvisory/trading_clock_fee.py` & `portfolio_manager.py`:
    - 识别 QDII 海外品种（050025、001071、013402 等），美股 QDII 赋予 `T+2 确认 · T+6~T+8 到账` 跨时区交割清算规则。
    - 同公司基金转换 (`calculate_rebalance_routes`) 与 `calculate_rebalance_net_utility` 彻底排除 QDII 基金与跨 TA 品种。
    - Tab 2 T+2 在途踏空风险计算排除 QDII 基金。
    - 动态生成 4 档估值可信度标识（指数高准度 / 债基看久期票息 / 美股休市·看隔夜期指 / 季报重仓估算）。
  - 合规清理：
    - `app_gui.py`、`winrate_engine.py`、`strategy_bridge.py` 彻底剔除违规“保本率”，统一替换为合规术语「正收益概率 (≥0%)」或「本金安全率」。
- **Performance & Fragment Architecture**:
  - `AGY2_FundAdvisory/app_gui.py`:
    - 引入 Streamlit 原生 `@st.fragment` 装饰器，将四大独立交互区块解耦为局部刷新组件：
      1. `render_sidebar_index_corridor()`: 侧边栏「核心指数行情走廊」自选配置与局部刷新；
      2. `render_tab2_fast_bar_and_holdings_table()`: Tab 2 持仓账本「极速录基吧台」与「主持仓表编辑」；
      3. `render_tab3_backtest_content()`: Tab 3 组合回测「回测对象与对标基准切换」；
      4. `render_tab4_toolbox_content()`: Tab 4 穿透工具「穿透组合切换与 A/C 算费器」。
    - 首屏延迟计算保护：通过 Fragment 阻断机制，确保 Tab 1 / Tab 2 调参不级联触发 Tab 3 / Tab 4 重仓穿透计算；为回测增加 `@st.cache_data(ttl=300)`。
    - 侧边栏「市场状态与底座」及顶部卡片统一渲染「📡 数据源健康度与时效状态徽章 (Data Freshness Badge)」：
      `🟢 实时盘中行情已连接 (更新于 HH:MM:SS)` / `🟡 离线湖仓快照兜底模式 (基准日 YYYY-MM-DD)`。
- **UI/UX Visual Elevation & Post-Trade Closed-Loop**:
  - `AGY2_FundAdvisory/app_gui.py`:
    - 首屏双翼看板视觉提权：单行高密度常驻信息栏「📢 今日脉搏晨报 + 🎯 Top 3 机会赛道胶囊 + 🚨 风险预警汇总徽章」；受控折叠详情卡片，释放首屏净空间给四大主工作区。
    - Tab 2 主持仓表防丢数自动入库拦截器：`_detect_table_diffs(edited_table, pm)` 检测差异并提示；在保存、诊断、一键执行 3 处入口前置自动无感执行 `_commit_holdings_from_table(edited_table, pm)`。
    - Tab 1 建仓表与 Tab 2 主持仓表附加 4 档估值可信度标识；建仓单/调仓单/在途对账表标注 QDII 清算规则。
    - Tab 2「🗄️ 账本环境与实盘档案」绘制 Plotly《实盘账户累计净值 vs 沪深300基准走势图》。
    - Tab 2 步骤三调仓执行单底部提供「✅ 我已在手机端按此方案下单 -> 一键将调仓单同步至当前账本持仓」快捷按钮。
  - `AGY2_FundAdvisory/portfolio_manager.py`:
    - `PortfolioManager` 增补维护 `nav_history`（日期、总资产、份额净值、同期沪深300基准），持久化至 JSON 与 SQLite。
- **Testing & Safety Baseline**:
  - 4 大裁判文件 SHA256 绝对锁定：`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`。
  - `DataLoader.simulate_execution` 默认签名与扣费逻辑严格保留。
  - 针对性自动化测试套件与 Streamlit AppTest 4 Tab 全量 0 异常验证。

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | 红利低波指数代码纠偏为 H30269 | RADAR_SECTOR_CATALOG 修正代码，清除 IndexValuationEngine 中 000978 别名 | M1 | 一.1 |
| 2 | QDII 基金识别与跨时区交割规则 | 识别美股与海外品种，标注 T+2 确认、T+6~T+8 到账，排除同公司 T+1 转换与 T+2 踏空 | M1 | 一.2a |
| 3 | 4 档基金估值可信度标识 | 指数高准度 / 债基看久期票息 / 美股休市·看隔夜期指 / 季报重仓估算 | M1 | 一.2b |
| 4 | 全站剔除违规“保本率”词汇 | 替换为合规术语「正收益概率 (≥0%)」或「本金安全率」 | M1 | 一.3 |
| 5 | 14 赛道 Bias20 价格口径与分红平滑 | 优先采用价格指数或日线分红脉冲平滑，消除虚假超买脉冲 | M1 | 一.4 |
| 6 | @st.fragment 四大独立区块解耦 | 侧边栏自选走廊、Tab 2 录基与表格、Tab 3 回测、Tab 4 穿透与算费器局部刷新 | M2 | 二.1 |
| 7 | 首屏延迟计算与穿透缓存保护 | 阻止 Tab 1/Tab 2 调参流经 Tab 3/Tab 4 重仓穿透，增设回测轻量缓存 | M2 | 二.1 |
| 8 | 📡 数据源健康度与时效状态徽章 | 实时盘中行情已连接 vs 离线湖仓快照兜底模式透明化呈现 | M2 | 二.2 |
| 9 | 双翼看板首屏视觉提权与受控折叠 | 单行高密度常驻信息条 + 详情卡片折叠切换，释放四大主工作区空间 | M3 | 三.1 |
| 10 | Tab 2 主持仓表防丢数自动保存 | 未保存差异提示，保存/诊断/执行全案 3 处统一自动前置入库 | M3 | 三.2 |
| 11 | 建仓/持仓/在途单 QDII 与估值标签贯通 | Tab 1、Tab 2 估值可信度展示与在途 QDII 跨时区清算标注 | M3 | 一.2 |
| 12 | 实盘账本历史净值记账曲线 | PortfolioManager 维护 nav_history，Tab 2 绘制累计净值 vs 沪深300走势图 | M3 | 三.3 |
| 13 | 调仓执行单手机端一键跟单打卡 | 步骤三底部提供一键将调仓单同步至当前账本持仓快捷按钮 | M3 | 三.3 |
| 14 | E2E 专项验收测试套件 | tests/test_adv_upgrade_suite.py 断言代码纠偏、保本清理、QDII规则与 AppTest | M4 | 四.1-2 |
| 15 | 全量测试回归与生产平滑重启 | pytest 全量 100% 通过（含 test_infra.py），8501 守护进程平滑重启 | M4 | 四.1-2 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | 金融事实与合规瑕疵底层引擎与交割体系修复 | Features 1-5: H30269纠偏, QDII清算规则与同公司排除, 4档估值标签生成, 保本词汇清理, Bias20分红平滑 | none | PLANNED |
| M2 | @st.fragment 架构性能飞跃与数据新鲜度透明化 | Features 6-8: 4大区块局部刷新, 首屏延迟计算保护, 数据新鲜度透明徽章 | none | PLANNED |
| M3 | 首屏视觉提权、表格防丢数自动保存与实盘净值记账闭环 | Features 9-13: 双翼看板折叠提权, 表格未保存自动同步, QDII与估值标签贯通, nav_history记账走势图, 一键跟单打卡 | M1, M2 | PLANNED |
| M4 | E2E 全量回归、专项合规与防作弊测试、8501 生产交付 | Features 14-15: 专项测试套件, pytest全量回归, 裁判文件哈希验证, 8501重启与健康探针 | M1, M2, M3 | PLANNED |

## Interface Contracts
### M1: Financial Facts & Compliance Engine Interface
- **advisory_engine.py**:
  - `RADAR_SECTOR_CATALOG["dividend_low_vol"]["benchmark_index"] == "H30269"`
  - `RADAR_SECTOR_CATALOG["dividend_low_vol"]["index_code"] == "H30269"`
  - `RADAR_SECTOR_CATALOG["dividend_low_vol"]["fallback_parquet"] = "data/processed/csindex_H30269.parquet"`
  - `_calc_dynamic_sector_metrics`: returns dynamic `er_20`, `bias_20`, `slope_20`, `crowding_score` with dividend smoothing.
- **data_loader.py**:
  - `IndexValuationEngine`: maps `H30269` to `csindex_H30269.parquet`, `"aliases"` does NOT contain `"000978"`.
- **trading_clock_fee.py & portfolio_manager.py**:
  - `is_qdii_fund(fund_code: str, fund_name: str = "") -> bool`:
    checks code in `{"050025", "001071", "013402"}` or name contains `("标普", "纳斯达克", "纳指", "恒生", "QDII", "海外")`.
  - `get_fund_valuation_credibility(fund_code: str, fund_name: str = "", asset_class: str = "") -> Tuple[str, str]`:
    returns `(badge_text, tooltip)`. e.g. `("指数高准度", ...)`, `("债基看久期票息", ...)`, `("美股休市·看隔夜期指", ...)`, `("季报重仓估算", ...)`.
  - `calculate_settlement_dates(..., is_qdii: bool = False)`:
    if `is_qdii`: confirm `T+2`, arrive `T+7`, note `「T+2 确认份额 · 赎回 T+6~T+8 到账（跨时区清算，不可用于 T+2 极速换仓）」`.
  - `calculate_rebalance_routes`:
    if `is_qdii_fund(s_code) or is_qdii_fund(b_code)` -> strictly forbid `PRIORITY_1_SWITCH` (T+1 conversion).

### M2: @st.fragment Architecture Interface
- **app_gui.py**:
  - Decorator: `safe_fragment = getattr(st, "fragment", lambda f=None, **k: f if f else (lambda fn: fn))`
  - Functions:
    - `@safe_fragment def render_sidebar_index_corridor()`:局部响应，刷新按钮显式 `st.rerun(scope="app")`
    - `@safe_fragment def render_tab2_fast_bar_and_holdings_table(pm: PortfolioManager)`: 局部响应，保存/入库/删除按钮显式 `st.rerun(scope="app")`
    - `@safe_fragment def render_tab3_backtest_content(pm: PortfolioManager, snapshot: Dict[str, Any])`
    - `@safe_fragment def render_tab4_toolbox_content(pm: PortfolioManager, snapshot: Dict[str, Any])`
  - Freshness probe: `inspect_data_freshness_status() -> Tuple[str, str, str]` (`badge_text`, `status_color`, `details`).

### M3: UI/UX & NAV Tracking Interface
- **app_gui.py**:
  - `_detect_table_diffs(edited_table: pd.DataFrame, pm: PortfolioManager) -> bool`
  - `_commit_holdings_from_table(edited_table: pd.DataFrame, pm: PortfolioManager) -> bool`
  - Intercept buttons: "💾 保存修改并入库", "🔍 诊断今日调仓时机", "🚀 一键执行全案" -> auto commit first!
  - Dual-wing dashboard: `render_dual_wing_summary_bar(pulse_text, top3_sectors, sentry_alerts)` + collapsible detail expander.
  - One-click follow: Button `✅ 我已在手机端按此方案下单 -> 一键将调仓单同步至当前账本持仓` -> updates `pm.holdings` directly.
- **portfolio_manager.py**:
  - `PortfolioManager.nav_history: List[Dict[str, Any]]`:
    entries: `{"date": "YYYY-MM-DD", "total_assets": float, "unit_nav": float, "benchmark_point": float}`.
  - Recorded in `save_state(record_snapshot=True)` and `sync_holdings_live_nav()`.

### M4: Verification & Delivery Interface
- Tests in `tests/test_adv_upgrade_suite.py`:
  - `test_dividend_low_vol_index_code_is_h30269`: assert H30269 and not 000978.
  - `test_no_baoben_in_ui_code`: grep `保本率` in app_gui.py yields 0 occurrences.
  - `test_qdii_delivery_and_conversion_rules`: assert 050025 T+2 confirm / T+6+ arrive, excluded from same-company T+1 conversion.
  - `test_streamlit_apptest_4tabs_zero_exception`: 4 Tabs render with 0 exceptions.

## Code Layout
- `AGY2_FundAdvisory/`
  - `advisory_engine.py`: H30269纠偏, Bias20分红平滑, 雷达指标 (M1)
  - `data_loader.py`: H30269别名清理, 数据新鲜度探针 (M1, M2)
  - `trading_clock_fee.py`: QDII跨时区规则, 4档估值标签 (M1)
  - `portfolio_manager.py`: QDII同公司排除, nav_history记账, 持仓同步 (M1, M3)
  - `strategy_bridge.py`: 调仓路由QDII排除, 保本词汇合规替换 (M1)
  - `winrate_engine.py`: 保本率术语合规规范 (M1)
  - `app_gui.py`: @st.fragment 架构, 数据新鲜度徽章, 首屏提权, 表格防丢数, 实盘走势图与一键跟单 (M2, M3)
- `tests/`
  - `test_infra.py`: 只读测试基线（绝对只读）
  - `test_adv_upgrade_suite.py`: 专项升级验收测试套件 (M4)
