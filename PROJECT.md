# Project: Wind 投顾系统全栈升级 (Global UI/UX Design System, Real Open Data, Quant Modules & Verification)

## Architecture
- **Web UI & Visualization Layer**: `AGY2_FundAdvisory/app_gui.py`
  - 5 套机构级主题配色 (`THEME_PRESETS`) + 全局 CSS 变量绑定系统
  - 动态盈亏涨跌色全站联动 (`active_co`: A股红涨绿跌 vs 国际绿涨红跌)
  - 顶部 6 大指数实时行情带 (含点位、涨跌幅、真实估值标签、紧凑刷新)
  - 🧭 全局领航台侧边栏：视觉中枢、目标档位快切、风控护栏、账本环境管理
  - 四大核心 Tab 错误隔离边界 (`try ... except Exception as e: st.error(...)`)
- **Data & Persistent Cache Layer**: `AGY2_FundAdvisory/data_loader.py`, `market_screener.py`, `cache_manager.py`, `data/cache/`
  - 东财两市实时宽度与成交额接口 (`push2.eastmoney.com` `f6/f104/f105/f106`)，彻底清除 `3210/1780` (M1 DONE)
  - AkShare 指数估值与 CSI 估值引擎，动态计算 PE-TTM/PB/股息率及历史分位数，缓存至 `data/cache/index_valuation.json`，替换 `INDEX_PE_METAS` (M1 DONE)
  - 公募基金全市场申购限额 (`ak.fund_purchase_em`)，落盘至 `data/cache/fund_purchase.parquet` (读取 14.29ms < 50ms) (M1 DONE)
  - 基金本体排雷与季报重仓穿透 (天天基金 JS API)，带 24h TTL 缓存与离线兜底 (M1 DONE)
  - 修复 `market_screener.py` 成立日期 bug，恢复 7,362 只候选池 (M1 DONE)
- **Quant Strategy & Execution Layer**: `AGY2_FundAdvisory/strategy_bridge.py`, `portfolio_manager.py`, `portfolio_optimizer.py`
  - 【🔭 全市场机会雷达】：覆盖 14 大赛道，计算估值分位、考夫曼信噪比 $ER_{20}$、MA20 动量拐点（超买 >+6% 折价）、拥挤度安全分；输出 Top 3 推荐赛道及对应六维最高分公募基金，支持一键纳入备选池
  - 【🚨 主动风险预警哨】：4 维状态自动巡检（FIFO 批次持仓天数 <=3d 预警、7d 脱离惩罚、C 类 30d 零费；赛道拥挤度超买；基金规模 <0.5 亿/经理变更/风格漂移本体排雷；大盘攻防线 MA20/MA60/MA120 突破/破位）
  - 【🌊 分批建仓与智能定投算子】：Tab 1 步骤三实装建仓节奏单选（模式一一次性建仓；模式二稳健三步分批建仓 50%/30%/20%，资金严格守恒 $\sum C_i \equiv \text{total\_capital}$；模式三估值自适应智能定投，根据 ERP 与 Bias20 输出 0.0x~2.0x 乘数与排期表）
- **Physical Safety Redline Layer**:
  - `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`（物理只读红线，SHA256 绝对锁定，严禁修改）

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | 东财真实全市场涨跌家数与量能 | 获取 f6, f104, f105, f106，清零 3210/1780 假常数，带本地 JSON 缓存与降级 | M1 (DONE) | R2 |
| 2 | 真实指数估值分位数与百分位引擎 | akshare/CSI 估值与历史序列计算分位，缓存至 data/cache/index_valuation.json，替换 INDEX_PE_METAS | M1 (DONE) | R2 |
| 3 | 全市场基金真实限购金额与缓存 | ak.fund_purchase_em() 缓存至 data/cache/fund_purchase.parquet (14ms)，打通限额过滤 | M1 (DONE) | R2 |
| 4 | 基金本体排雷与季报重仓元数据 | 天天基金接口提取 AUM (<0.5亿清盘排查)、经理任职与回报、季报股债仓位与前十大重仓，24h TTL 缓存 | M1 (DONE) | R2 |
| 5 | 修复 market_screener 成立日期 Bug | 修复 ak.fund_name_em 缺少 inception_date 导致候选池为空问题，恢复 7,362 只 | M1 (DONE) | R2 |
| 6 | CSS 核心组件类与变量绑定恢复 | 重建 .decision-card, .decision-title 等类，100% 绑定 var(--bg-canvas) 等 CSS 变量 | M2 | R1 |
| 7 | 清零内联硬编码色值与动态涨跌联动 | 清除 safe_markdown_html 与 Plotly 中硬编码 Hex 色值，盈亏颜色与图表动态读取 active_co | M2 | R1 |
| 8 | 文案与视觉样式去营销化 | 废除五彩彩虹顶边，清除感叹号、多余书名号与方括号，标题控制在 6~7 字，按钮精炼 | M2 | R1 |
| 9 | 5 套机构级主题配色实装 | light_slate (默认), dark_terminal, nordic_paper, deep_titanium, nordic_frost (含别名兼容) | M2 | R1 |
| 10 | 顶部行情带与侧边栏职责归位 | 顶部 6 大指数行情带实装点位、涨跌幅与真实估值标签；侧边栏聚焦视觉/目标/风控/账本四大职责 | M2 | R1 |
| 11 | 【🔭 全市场机会雷达】引擎与看板 | 覆盖 14 赛道，计算估值/ER/动量/拥挤度得分，输出 Top 3 机会赛道与六维最优基金，支持一键加入备选池 | M3 | R3 |
| 12 | 【🚨 主动风险预警哨】四维巡检 | FIFO 批次解锁提醒 (<=3d, 7d, 30d)、拥挤超买预警、基金本体排雷预警、大盘攻防线预警 | M3 | R3 |
| 13 | 【🌊 分批建仓与智能定投算子】 | 模式一一键建仓；模式二三步分批 (50%/30%/20%，资金守恒)；模式三估值自适应定投 (ERP+Bias20 乘数) | M3 | R3 |
| 14 | 物理裁判文件哈希锁定与只读审计 | 校验 judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py SHA256 哈希 | M4 | R4 |
| 15 | 自动化单元测试与 AppTest 回归验证 | 编写针对新数据与投顾算子的针对性测试，Streamlit AppTest 验证 5 套主题与 4 个 Tab 0 异常 | M4 | R5 |
| 16 | 8501 端口平滑重启与服务健康自检 | 遵循瞬态端口非破坏性甄别，平滑重启服务并验证 HTTP 200 探针存活 | M4 | R5 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | 免费开源真实数据底座升级与持久化缓存 | Features 1-5 (R2): 东财市场宽度/量能, 真实指数估值分位, 基金真实限购 Parquet 缓存, 基金本体排雷与季报重仓, 修复 market_screener | none | DONE |
| M2 | 全局 UI/UX 多配色设计系统重构与 5 套高定主题 | Features 6-10 (R1): CSS 类与变量绑定, 清零内联色值与动态涨跌色联动, 去营销化文案与微边框, 5 套主题预设, 顶部行情带与侧边栏重构 | M1 (for real valuation tags) | PLANNED |
| M3 | 实装三大投顾核心业务模块 | Features 11-13 (R3): 全市场机会雷达, 主动风险预警哨, 分批建仓与智能定投算子及 UI 接入 | M1, M2 | PLANNED |
| M4 | 物理红线哈希审计、全套自动化回归测试与服务重启 | Features 14-16 (R4, R5): 裁判文件哈希审计, 假常数清零断言, 新算子增量测试, AppTest 4-Tab 回归, 8501 端口平滑重启 | M1, M2, M3 | PLANNED |

## Interface Contracts
### M1 ↔ M2: Index Valuation & Market Breadth Interface
- **File**: `data/cache/index_valuation.json` & `data/cache/market_breadth.json`
- **Schema**:
  - `index_valuation.json`: `{ "<symbol>": { "name": str, "pe_ttm": float, "percentile": float, "label": str, "status": "low"|"mid"|"high" } }`
  - `market_breadth.json`: `{ "turnover_str": str, "turnover_val": float, "up_count": int, "down_count": int, "flat_count": int, "up_pct": float, "timestamp": str }`
- **Status**: Verified and operational.

### M1 ↔ M3: Fund Purchase Quota & Screening Interface
- **File**: `data/cache/fund_purchase.parquet` & `data/cache/funds/{code}_meta.json`
- **Schema**:
  - `fund_purchase.parquet`: columns `['基金代码', '申购状态', '赎回状态', '日累计限定金额']`, cold read latency 14.29ms (<50ms).
  - `{code}_meta.json`: `{ "code": str, "aum": float, "manager": str, "term_years": float, "term_return": float, "asset_allocation": { "stock": float, "bond": float, "cash": float }, "top10_stocks": list[str] }`
- **Status**: Verified and operational.

### M2 ↔ M3: UI Radar & DCA Component Container Interface
- **File**: `AGY2_FundAdvisory/app_gui.py`
- **Contract**:
  - 机会雷达组件以可折叠/常驻卡片形式挂载于行情带正下方或 Tab 顶部专属区域；
  - 分批建仓选择器集成于 Tab 1 步骤三实盘交割单，输出 `st.session_state.execution_plan` 并向交割单组件传递 `capital_deployment_mode` 及对应批次明细。

### M3 ↔ M4: Test Contracts & Mathematical Invariants
- **Contract 1 (Capital Conservation)**:
  - 稳健三步分批建仓算法必须保证：`abs(batch_1_amount + batch_2_amount + batch_3_amount - total_capital) < 1e-4`。
- **Contract 2 (FIFO Holding Days & Penalty Lock)**:
  - 调仓优化器严格遵守持有期 $<7$ 天份额 `locked_shares` 约束，严禁建议卖出。
- **Contract 3 (DCA Multiplier Boundedness)**:
  - 估值自适应定投乘数严格处于 $[0.0, 2.0]$ 区间。

## Code Layout
- `AGY2_FundAdvisory/`
  - `app_gui.py`: UI 视图与设计系统 (M2, M3)
  - `data_loader.py`: 数据加载与外部接口 (M1 DONE)
  - `market_screener.py`: 标的筛选器 (M1 DONE, M3)
  - `cache_manager.py`: 本地缓存与持久化存储 (M1 DONE)
  - `portfolio_manager.py`: 组合管理、选基评分与持仓批次 (M3)
  - `portfolio_optimizer.py`: 组合优化器、调仓路径与定投算子 (M3)
  - `strategy_bridge.py`: 策略桥接与建仓蓝图 (M3)
  - `tests/`: 单元与集成测试套件 (M4)
- `tests/`:
  - `test_infra.py`: 只读测试基线（物理只读）
  - 新增针对性增量测试 (M4)
