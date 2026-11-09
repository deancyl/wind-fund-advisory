# Project: G13 世代首屏零阻塞秒开重构、全宽大胶囊主导航视觉提权、清除伪交易按钮与臃肿嵌套及回测曲线打假闭环任务

## Architecture
- **Performance & Engine Optimization (Pain Point 1)**:
  - `AGY2_FundAdvisory/advisory_engine.py`:
    - `OnlineHeuristicFactorEvolver`: 实装磁盘文件持久化缓存 `data/cache/factor_evolution_cache.json`，缓存数据包含 `weights`, `nav_trajectory`, `generation_scores`, `timestamp`，有效 TTL 设为 12 小时。
    - `get_60d_rolling_nav_and_trajectory`: 优先从磁盘缓存读取；当缓存有效时直接返回，耗时 < 5ms；仅当缓存缺失或用户显式点击刷新时才重新触发 12 切片走步演化计算。
    - `OpportunityRadarEngine`: 默认初始化仅读取本地缓存或使用预设动态权重，避免在首屏同步跑 32 种群 x 15 代遗传算法。
  - `AGY2_FundAdvisory/app_gui.py`:
    - `render_dual_wing_advisory_dashboard`: 首屏默认加载时彻底禁止调用 `OpportunityRadarEngine()`, `evolve_factor_weights()`, `get_60d_rolling_nav_and_trajectory()`, `fetch_realtime_market_news_and_catalysts()`, `fetch_etf_feeder_arbitrage_sensors()`, `fetch_options_implied_volatility_sensors()`, `evaluate_all_qdII_fx_arbitrage()`.
    - 首屏顶部的投顾提示条仅基于内存中已有的 `snapshot` 与 `pm.holdings` 做纯内存毫秒级轻量判断（耗时 < 10ms，零网络请求、零遗传算法、零大 Parquet 扫描）。
- **Backtest Curve Integrity & De-biasing (Pain Point 4)**:
  - `AGY2_FundAdvisory/strategy_bridge.py`:
    - `build_custom_portfolio_backtest`: 彻底删除每天硬加人工 Alpha 代码（第 4929 行 `r_arr[1:] += (alpha_ann / 250.0)`），杜绝凭空凭空虚构 30%~40% 无风险超额。
    - 基准指数真实全收益序列对齐：检查基准字典映射，将中证综合债纯债指数彻底绑定 `csindex_H11009.parquet` 真实日度收盘序列（CAGR +4.81%），严禁使用起止点线性插值画假直线；红利低波基准锁定 `H30269` 真实日度历史全收益。
    - 静态持仓后视镜偏差标注：当回测目标为当前实盘账本时，在图表上方显式标注「当前持仓静态权重历史回溯（含历史后视镜权重效应，非滚动样本外实盘记录）」，并提供一键切换对比「全天候滚动样本外动态策略曲线 (C3)」。
  - `AGY2_FundAdvisory/app_gui.py`:
    - Tab 3 全周期累计净值对比 Plotly 图表：在 `apply_theme_to_plotly_figure` 或其之后强制设置 `legend=dict(orientation="h", yanchor="bottom", y=1.06, xanchor="left", x=0, bgcolor="rgba(0,0,0,0)")` 与 `margin=dict(t=75, l=10, r=10, b=10)`；将牛熊阶段背景标注文字移至绘图区顶部边缘并调淡字色，彻底根除图例与文字压盖净值曲线。
- **UI/UX Cleanup & Fake Transaction Removal (Pain Points 2 & 3)**:
  - `AGY2_FundAdvisory/app_gui.py`:
    - 彻底删除首屏右上角红色大按钮 `col_wing_btn` 及其内部的 `btn_master_action_switch`（“查看锁仓保护 / 查看今日调仓单 / 检视持仓账本”），取消 `columns([8.2, 1.8])`，让投顾参谋折叠栏占满 100% 全宽，消灭右侧空白死区。
    - 投顾提示文案采用温情参谋语言（如：`今日投顾参谋：持仓含 2 只未满 7 天标的，赎回需扣 1.5% 惩罚费，调仓算法已自动为您避开卖出 ｜ 点击展开市场机会与持仓体检`）。
    - 彻底清除右翼与左翼所有伪交易按钮：删除右翼「一键批量锁定这2只标的调仓下界」按钮 (`btn_batch_lock_all_7d`)，删除卡片下方「择机置换」、「平衡赛道敞口」、「穿透到底层」等所有伪跳转按钮 (`btn_sentry_act_*`, `btn_sentry_evid_*`)，右翼收敛为干净紧凑的无按钮列表（1~3 条核心风险提示与应对建议）；删除左翼 3 个「+ 入备选池」按钮 (`btn_add_radar_pool_*`)，卡片内直接展示优选基金名称与 6 位代码。
    - 5 大臃肿嵌套模块外科手术式拆解：
      ① 移除双翼折叠框内的「历史三大牛熊拐点实盘对照尺」，仅在 Tab 1 定投模式保留并优化横向防重叠排版；
      ②「查看全市场 14 大赛道量化温度计总表」、③「场内ETF与场外联接 14:45 尾盘折溢价套利感知」、④「50ETF与300ETF认沽期权隐含波动率防暴跌哨」、⑤「跨境QDII溢价与外汇期货锁汇成本套利精算」4 个深度工具全部迁入 Tab 4「穿透工具」的二级子 Tab 中。
      首屏双翼折叠框展开后仅保留「左翼 Top 3 赛道卡 + 右翼极简风险提示列表」，展开高度严格限制在 220px 以内。
- **Full-Width Navigation & Visual Hierarchy Elevation (Pain Point 5)**:
  - `AGY2_FundAdvisory/app_gui.py`:
    - 全宽四宫格大胶囊主导航 CSS 改造：定位 `[data-testid="stMainBlockContainer"] > div > div > [data-testid="stTabs"] > [data-baseweb="tab-list"]`，设置 `display: grid !important; grid-template-columns: repeat(4, 1fr) !important; gap: 10px !important; background: var(--bg-elevated) !important; padding: 6px !important; border-radius: 10px !important; border: 1px solid var(--border-subtle) !important; margin-bottom: 14px !important;`。
    - 定位一级 Tab 按钮：`height: 46px !important; font-size: 16px !important; font-weight: 700 !important; border-radius: 8px !important; justify-content: center !important; background: var(--bg-surface) !important; border: 1px solid var(--border-subtle) !important; box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;`。
    - 定位激活态一级 Tab 按钮：`background: var(--accent-primary) !important; color: #ffffff !important; border-color: var(--accent-primary) !important; box-shadow: 0 4px 12px rgba(29, 78, 216, 0.25) !important;`，强制 span 与 p 为纯白 `#ffffff !important`。
    - 严格隔离 Tab 4 内部的二级子 Tab（保持紧凑轻量的下划线样式，杜绝与一级大导航混淆）。
    - 彻底删除四大主 Tab 内部开头重复打印的 `st.subheader("🌱 新资建仓")`、`st.subheader("💼 持仓调仓")`、`st.subheader("📈 组合回测")`、`st.subheader("🔍 穿透工具")` 及其下方的废话 caption。
    - 在 Tab 4 中将「选择穿透体检组合对象」与「当前体检组合成分档案」合并为顶栏紧凑单行摘要，实现核心图表首屏直达。
- **Physical Safety Invariants & Testing Baseline**:
  - 4 个只读裁判文件绝对零修改（SHA256 锁定）：`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`。
  - `DataLoader.simulate_execution` 默认签名与 7 天 1.50% 阶梯扣费逻辑严格保留。
  - 适配更新受影响的非只读测试用例（如针对旧按钮名称的断言），保障全量回归测试 100% 绿灯。
  - 清理 `data/ledgers/` 孤儿沙盒文件，仅保留干净的 `main_live` 主实盘账本。

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | 首屏零阻塞秒开 (<150ms) | 禁止默认调用雷达引擎、遗传算法与实时网络请求，顶栏纯内存参谋化 | M1 | 二.1 |
| 2 | 因子进化 12h 磁盘持久化缓存 | 在 advisory_engine 中实装 factor_evolution_cache.json，首屏零计算 | M1 | 二.1 |
| 3 | 彻底剔除每日硬加固定 Alpha | 在 strategy_bridge.py 中删除 r_arr[1:] += (alpha_ann / 250.0) | M1 | 二.4 |
| 4 | 真实纯债与红利低波日度全收益基准 | 绑定 csindex_H11009.parquet 真实序列，严禁起止点线性插值 | M1 | 二.4 |
| 5 | 静态持仓后视镜偏差标注与 C3 对比 | 实盘静态回溯增加后视镜效应警示卡，支持一键切换对比全天候动态策略 | M1 | 二.4 |
| 6 | 彻底删除右上角红按钮与全宽提示条 | 删除 col_wing_btn 与 btn_master_action_switch，提示条 100% 满宽消除死区 | M2 | 二.2 |
| 7 | 清除全部伪交易与跨区跳转按钮 | 删除批量锁定下界、择机置换、穿透到底层、+入备选池等全部伪按钮 | M2 | 二.2 |
| 8 | 5 大臃肿嵌套模块拆解与迁移 | 拐点尺仅保留在 Tab 1，14 赛道、14:45 折溢价、期权IV、QDII 4 模块迁入 Tab 4 | M2 | 二.2 |
| 9 | 全宽四宫格大胶囊主导航高对比度 CSS | 100% 满宽网格、46px 高、16px 加粗、品牌色高亮选中态与纯白字体穿透 | M2 | 二.3 |
| 10 | 消除四大 Tab 重复大标题与 Tab 4 顶栏合并 | 删除 Tab 开头重复的 st.subheader 与废话 caption，Tab 4 顶部合并为单行 | M2 | 二.3 |
| 11 | 回测图 Plotly 图例上浮透明与零遮挡 | 设置 legend 外部上方水平排列与透明背景，扩大顶部 margin 至 75px | M2 | 二.4 |
| 12 | 非只读测试断言适配与全量测试 100% 绿灯 | 适配旧按钮断言，全量跑通 pytest，确保 4 大裁判文件 SHA256 绝对吻合 | M3 | 四.1 |
| 13 | 孤儿沙盒账本文件清理与环境整洁 | 清理 data/ledgers/ 下无用 sandbox 文件，保持 main_live 纯净 | M3 | 四.1 |
| 14 | 8501 端口安全平滑重启与健康探针 | 终止旧进程，无窗口后台脱钩托管启动，/_stcore/health 轮询 200 OK | M4 | 三 |
| 15 | Browser 5 图实机核验与截图留存 | 调用 /browser 对照 5 张问题截图逐一实机核验秒开、无按钮、全宽导航、无遮挡 | M4 | 三 |
| 16 | 规范沉淀、Git 归档与 G14 指令生成 | 沉淀 GEMINI.md/PROGRESS_LOG.md，打 tag v4.3-G13，生成严格分号 G14 指令 | M4 | 四.2-4 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | 首屏极速秒开、因子进化持久化缓存与回测曲线打假 | Features 1-5: 消除首屏阻塞与外网请求, 12h 磁盘缓存, 剔除假 Alpha, H11009 真实日度全收益, 后视镜警示与 C3 对比 | none | DONE |
| M2 | 全宽投顾栏、清除伪交易按钮、臃肿模块迁移、全宽四宫格大胶囊导航与回测图例上浮 | Features 6-11: 满宽投顾栏消灭白区, 删除所有伪操作按钮, 5 模块拆解迁入 Tab 4, 全宽大胶囊 CSS 提权, 删除重复大标题, 图例上浮零遮挡 | M1 | DONE |
| M3 | 非只读测试适配更新、4 大裁判文件防篡改审计与全量回归 100% 绿灯 | Features 12-13: 适配旧按钮断言, 清理 sandbox 孤儿账本, 4 大裁判文件 SHA256 校验, pytest 全量绿灯 | M1, M2 | DONE |
| M4 | 8501 服务平滑重启、Browser 5 图实机核验、Git 标签归档与 G14 世代指令生成 | Features 14-16: 8501 重启, Browser 实机对照 5 图核验, 工作区规则沉淀, Git commit & tag v4.3-G13 (无 Release), 严守分号 G14 指令输出 | M1, M2, M3 | DONE |

## Code Layout
- `AGY2_FundAdvisory/advisory_engine.py`: 因子进化缓存、雷达轻量化初始化
- `AGY2_FundAdvisory/strategy_bridge.py`: 回测引擎去假 Alpha、真实基准日度序列、后视镜警示
- `AGY2_FundAdvisory/app_gui.py`: 全宽投顾参谋栏、清除所有伪交易按钮、Tab 4 工具迁移、全宽大胶囊主导航 CSS、消除 Tab 重复标题、回测图例上浮透明
- `tests/`: 非只读测试用例适配更新（`test_challenger_g11_m1_actions.py`, `test_g7_architecture_and_decoupling.py` 等）
- `data/cache/`: 因子进化磁盘持久化缓存目录 (`data/cache/factor_evolution_cache.json`)
- `data/ledgers/`: 账本目录（清理孤儿沙盒文件，仅保留 `main_live`）
- `tests/test_infra.py`, `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`: **绝对只读，严禁修改**
