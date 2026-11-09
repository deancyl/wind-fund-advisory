# Dispatch Log

## 2026-10-29T09:02:39Z
你是 Project Orchestrator（项目编排器）。你的任务是统领并编排团队完成以下工程需求：

【工作目录与原件记录】
- 你的专属元数据目录：d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_1
- 用户原始需求与验收标准见：d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- 代码工作区目录：d:\Google\Workspace\Wind\AGY2_FundAdvisory
- 项目根目录：d:\Google\Workspace\Wind

【核心任务概要】
将 AGY2 基金实盘组合接管与智能投顾管理系统（AGY2_FundAdvisory）全面升级接入底层时序湖仓与 Wind 投顾统一工具包（WindToolkit）的全新 6 大进阶金融投研能力：
1. R1: 基金底层前十大重仓股穿透排雷引擎（商誉占比>30%、存贷双高、控股股东高比例质押、30-90天限售解禁，三色风险标签与组合穿透风险指数）。
2. R2: 顶部看板接入宏观高频流动性温度计（逆回购净投放/回笼量、DR007相对7D OMO偏离度bp，宽松/中性/收紧状态徽章与双轨宏观雷达）。
3. R3: 聪明钱与机构抱团拥挤度监控（北向陆股通1日/5日动态、股东户数变动、龙虎榜机构席位、筹码集中度与抱团松动风险提示）。
4. R4: 生产质量、无损兼容与只读底座防御（严禁触碰或解锁 judge_engine.py、holdout_vault.py、AGENT_SPEC.md，保持既有 112 项测试 100% 通过，新增测试，本地 DuckDB 离线降级兜底，Streamlit GUI 8501 零报错）。

【编排规范】
- 请在此工作目录下维护 BRIEFING.md 和 progress.md。
- 调度专家智能体执行代码调研、方案制定、代码实现、测试验证等环节。
- 任务完成且全部验收标准满足后，向 Sentinel 汇报成果。


## 2026-11-03T06:55:20Z
对 Wind 投顾系统实施生产级（Production）“全局交互架构重塑、量化定权退化根治与信息表达降维”深度重构任务，全面提升量化定权严密性、持有期胜率完备性、界面交互表达与系统稳定性。

Working directory: d:\Google\Workspace\Wind
Integrity mode: development

## Requirements

### R1. 核心架构与算法根因排查（底层逻辑根治，严禁硬编码凑数）
- **根治多基金定权退化为 1/N 等权与限购拆单后总权重突破 100% 的数学缺陷**：
  - 在 `portfolio_optimizer.py` 与 `strategy_bridge.py` 中，排查优化器目标函数梯度、初始值设定与边界约束，从数学机制上恢复四大模型（`hrp_cvar` / `cond_winrate` / `min_cvar` / `kelly_momentum`）应有的风险预算与评分倾角区分度，形成真正的“主力底仓 + 卫星增强”梯队分布。
  - 在 `generate_zero_start_blueprint` 处理单日限购标的时，修正追加伴生承接基金后未正确扣减原基金份额或重复计入权重的逻辑。
  - 严格保持两大数学不变量（Invariants）：
    - 权重守恒：无论是否触发限购拆单或备选替换，最终建仓单所有条目的 `allocated_amount` 之和必须严格等于用户投入总本金 `total_capital`，`target_weight_pct` 之和必须严格等于 `100.0%`。
    - 模型区分度：四大模型在相同候选池下必须产出符合各自理论特性的差异化权重分布，绝不允许退化为机械等权。
- **升级持有期胜率的统计完备性与样本广度**：
  - 优先利用工作区本地已有的长周期基准指数与基金净值历史数据序列，最大化扩展有效历史回测跨度与独立滚动窗口样本量。
  - 在胜率看板提供清晰的口径对照或切换：「🎯 当下相似行情胜率（基于当前估值/利率状态机核密度加权）」 vs 「🌐 全历史跨牛熊无差别胜率（含历次牛市顶点站岗与极端熊市样本）」，并显式披露有效测评窗口期数。

### R2. 信息架构与 UI/UX 体验重塑（通俗干练、动态同源、零截断）
- **恢复侧边栏并重构为「🧭 全局领航台」**：
  - 移除 `app_gui.py` 中强行隐藏 `stSidebar` 的 CSS，恢复侧边栏展开/收起能力。
  - 职责解耦：侧边栏不放置任何具体 Tab 的局部操作按钮（局部操作保留在各自 Tab 内），作为全局跨 Tab 领航仪表盘，凝练展示：① 实时市场状态与数据底座健康度、②【🌱 新资建仓】当前推演方案快照、③【💼 实盘持仓】账本核心快照、④ 全局行情一键刷新入口。
- **顶部「📊 核心指数」行情带视觉提权**：
  - 重新设计顶部 6 大核心指数（沪深300、科创50、中证红利、中证500、中证1000、黄金ETF）卡片/胶囊的排版比例与字号层级，突出指数点位与红涨绿跌标签，确保全宽下清晰醒目、一行完整呈现且无截断。
- **四大量化模型说明与六维打分标准的去学术化与交互内聚**：
  - 废除会被单行截断的 `st.dataframe` 模型说明表，改用自适应换行的网格卡片。将四大模型的描述从学术术语转化为三个直观维度：【它解决什么问题】、【怎么分配资金】、【适合什么行情】。
  - 在六维量化打分公式旁提供 `st.popover("ⓘ 评分细则")` 弹出层，清晰列出 6 个维度（超额收益35%、低费率25%、底层排雷15%、聪明钱10%、反拥挤10%、宏观契合5%）从 0 到 100 分的具体评判标准与扣分项。
- **「方案核心逻辑（三句话看懂本方案）」100% 动态数据驱动与视觉扩容**：
  - 废除窄小的 4 列静态套话卡片，改为宽敞的 3 栏深度归因大卡片（💰 怎么赚钱 / 🏆 为什么能赢 / 🚨 风险与铁律）。
  - 动态同源：卡片内每一句结论 100% 动态读取当前推演生成的真实组合数据（实时统计组合中防守收息类 vs 弹性进攻类真实占比与金额、点名权重最高的核心基金名称、代入当前所选模型选基逻辑、代入用户本金对应的历史最大浮亏金额与水下回本天数）。
- **全站标题与文案极简规范**：
  - 标题 ≤ 7 字原则：全面精简全站所有模块标题、卡片标题、步骤标题与折叠框标题，统一控制在 7 个汉字以内。
  - 说明文字剔除空洞修饰词与重复过渡句，语言通俗干练直奔结论。

### R3. 物理安全红线与受限文件约束
- 严禁触碰只读裁判文件：`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`。
- 修改代码前先在思维链中完成根因诊断与跨模块契约对齐，严禁硬编码凑数。

### R4. 自验证闭环与交付要求
- 编写并运行自动化测试（pytest + Streamlit `AppTest`），验证算法与交互规范。
- 确认测试全部通过后，平滑重启 8501 端口服务。

## Acceptance Criteria

### 算法与数学不变量
- [ ] 在 `num_funds` 取不同值（如 6、12）及切换四大模型（`hrp_cvar` / `cond_winrate` / `min_cvar` / `kelly_momentum`）时，权重分布呈现差异化梯队分布，不退化为机械 1/N 等权。
- [ ] 经过 `generate_zero_start_blueprint` 限购拆单后，最终建仓单所有条目的 `allocated_amount` 之和严格等于用户投入总本金 `total_capital`，`target_weight_pct` 之和严格等于 `100.0%`。
- [ ] 胜率看板扩展有效历史回测跨度与独立滚动窗口样本量，并提供“当下相似行情胜率”与“全历史跨牛熊无差别胜率”的口径对照/切换，且显式披露有效测评窗口期数。

### UI/UX 与交互规范
- [ ] 侧边栏恢复显示并支持自由展开/收起，展示市场状态、建仓快照、持仓快照与全局刷新入口，不含任何 Tab 局部操作按钮。
- [ ] 顶部 6 大核心指数行情带全宽单行完整呈现，无截断，点位与涨跌标签清晰醒目。
- [ ] 四大模型说明采用自适应换行网格卡片呈现三大维度，六维打分标准通过 `st.popover` 弹窗完整展示。
- [ ] 「方案核心逻辑」呈现为 3 栏深度归因大卡片，内容 100% 动态读取当前真实推演数据。
- [ ] 全站所有模块、卡片、步骤及折叠框标题严格在 7 个汉字以内，全站无 HTML 标签裸露且无文本截断。

### 自验证与服务交付
- [ ] 自动化测试套件（pytest 与 Streamlit `AppTest`）全部执行通过，4 个 Tab 交互 0 异常。
- [ ] 保持只读裁判文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）未被修改。
- [ ] 8501 端口 Streamlit 守护进程平滑重启成功，服务健康存活并可正常访问。


## 2026-11-05T14:09:15Z
批准并升级实施「多账本体系 (Multi-Ledger System)」，同时彻底整改代码审计发现的迎合性假代码与前后端断层任务，作为 Wind 投顾系统的生产级核心功能落地与严格代码审计整改。

Working directory: d:\Google\Workspace\Wind
Integrity mode: development

## Reference Materials
- 核心代码路径：
  - Streamlit GUI 主程序：`AGY2_FundAdvisory/app_gui.py` (端口 8501)
  - 核心策略与模型：`portfolio_manager.py`, `strategy_bridge.py`, `AGY2_FundAdvisory/advisory_engine.py`, `data_loader.py`
  - 数据湖仓与缓存：`data/ledgers/`, `data/ledgers_index.json`, `data/storage.duckdb`, `data/cache/market_screener/nav_cache/`
- 只读裁判文件基线：`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`

## Verification Resources
- 自动化测试套件：pytest 全量测试（含只读 `tests/test_infra.py`）
- 专项防作弊测试（测试 A：14赛道真动态检验；测试 B：四大调仓场景真实性检验；测试 C：多账本隔离与全站联动检验；测试 D：Tab 4 跨组合穿透检验）
- Streamlit `AppTest`（浅色与深色主题全站零报错）及 8501 端口服务健康运行探针

## Requirements

### R1. 多账本/组合管理体系（MultiLedgerManager）底层存储与管理实现
- 主实盘账本默认路径保持为 `portfolio_ledger.json`（`id="main_live"`, `name="主实盘账本"`, `type="live"`），确保所有不传参的 `PortfolioManager()` 调用及现有单元测试 100% 原样通过，主实盘受物理保护禁止删除。
- 所有新建或克隆的账本存放于 `data/ledgers/<ledger_id>.json`，并在 `data/ledgers_index.json` 中维护账本元数据（包含 `id`, `name`, `type: live|sandbox|family`, `default_tier: C1~C5`, `created_at`, `updated_at`）。
- 在 `MultiLedgerManager` 中完整实现 `list_ledgers()`, `create_ledger(name, base_cash, ledger_type, default_tier)`, `clone_ledger(src_id, target_name)`, `rename_ledger(ledger_id, new_name)`, `delete_ledger(ledger_id)`, `get_all_ledgers_summary()`（汇总所有账本的总资产、总浮盈与持仓只数）。

### R2. 多账本全站级动态热装配与跨 Tab 贯通
- 在 `app_gui.py` 初始化时，通过 `st.session_state.active_ledger_id` 绑定当前激活的 `PortfolioManager` 实例（`st.session_state.pm`）。
- 用户切换账本时：全局 `pm` 实例、顶部第 4 张「总资产与今日预估」大卡片、双翼看板的「主动风险预警哨」、Tab 2 持仓账本与调仓、Tab 3 组合回测的「当前实盘持仓」、Tab 4 穿透工具的「当前实盘持仓」必须 100% 同步指向当前激活账本；同时自动将该账本绑定的 `default_tier` 同步至 `active_tier_val`，并清空 `tab2_diag_cache` 与 `tab2_rebal_cache`。
- 在 Tab 2「步骤一：持仓账本」顶部放置单行多账本管理吧台：包含【当前账本选择器（带实盘/家庭专项/沙盒标识与总市值）】、【➕ 新建账本】Popover（可设名称、初始资金、账本类型、专属风险档位 C1~C5）、【📋 克隆当前副本】Popover、【⚙️ 账本管理】Popover（重命名、删除、查看全账本家庭资产汇总表）。若当前为沙盒账本，醒目展示「当前为独立沙盒环境，任何调仓与录基演练均隔离存储，绝不影响主实盘」提示条。
- 打通 Tab 1 到多账本的无损保存：在 Tab 1 步骤三底部「设为初始持仓」区域提供两个选项：「覆盖写入当前激活账本」与「🆕 另存为全新独立账本（输入新账本名称一键创建并写入持仓）」，防止误覆盖主实盘账本。

### R3. 打通 Tab 2「四大实盘调仓场景模式」的前后端真实计算闭环
- 将 `scenario_mode`（`standard` / `new_cash_only` / `withdraw_cash_only` / `sweep_tail_and_c_class`）、`new_cash_amount`、`withdraw_cash_amount`、`freeze_reserved_cash`、`core_anchor_code` 完整传入 `simulate_rebalance_modes_and_consequences` 与 `generate_ai_rebalance_orders`，并将这些参数纳入缓存签名以确保切换场景或修改金额时立即重新计算。
- 选择「新资注入免赎补仓 (`new_cash_only`)」时：调仓单表格中所有现有持仓的卖出金额必须严格为 0（赎回费为 0），仅针对欠配标的生成买入指令，且所有买入指令金额之和严格等于 `new_cash_amount`。
- 选择「智能低损耗提现 (`withdraw_cash_only`)」时：调仓单表格中买入金额严格为 0，系统按最优顺序（优先满免赎期 C 类/A 类、超配或浮盈标的，严格跳过未满 7 天红线标的）生成赎回减仓指令，且赎回总额严格等于 `withdraw_cash_amount`。
- 开启「冻结分批建仓预留现金 (`freeze_reserved_chk`)」时：计算可用调仓现金时必须扣除 `pm.reserved_batch_cash`，绝不把预留网格资金当成闲置现金催促买光。

### R4. 清除 Tab 3「历史相似匹配」硬编码假文案，改为真实动态统计
- 从 `analog_tab2["matches"]` 列表中真实提取匹配的 3 个历史时期的 `strategy_ret_60d`、`h300_ret_60d`、`strategy_mdd_60d`：真实计算后 60 日「跑赢沪深300的相对超额胜率 (%)」、「平均相对超额收益率 (%)」、「策略平均绝对收益率 (%)」与「平均最大回撤 (%)」，动态填入顶部操作指南横幅中，严禁写死任何常数。
- 对下方 3 张历史卡片，根据每一期真实的 `strategy_ret_60d` 与 `h300_ret_60d` 关系动态生成各不相同的「历史镜鉴意义」：
  - 若策略与沪深300双双上涨：显示「右侧顺势共振：底部击球区反弹期紧跟主升浪，兼顾进攻弹性与低回撤（最大回撤仅 X.X%）」；
  - 若沪深300下跌而策略抗跌少亏：显示「逆势抗跌护盾：大盘阴跌寻底期，凭借红利与纯债底仓大幅跑赢大盘 +X.XX%，守住本金安全垫」；
  - 若沪深300反弹而策略短期小幅落后：显示「防守底仓代价：急跌反抽期高配纯债避险导致短期弹性收敛，但换取了熊市下半场极高本金安全度」。

### R5. 修复 Tab 4 穿透工具切换组合对象底层读取断层与资产分类精准化
- 为 `pm.calculate_look_through_industry_exposure`、`calculate_stock_overlap_matrix`、`calculate_portfolio_penetration_risk`、`get_portfolio_look_through_stocks_df` 增加可选参数 `holdings_override: Optional[Dict[str, HoldingItem]] = None`（当传入时使用 `holdings_override` 计算，未传入时默认使用 `self.holdings`）。
- 在 Tab 4 中将 `active_examine_holdings` 真实传入上述 4 个函数，并将聪明钱循环改为遍历 `active_examine_holdings.items()`，确保切换「当前实盘持仓 / 新建仓组合 / 调仓后组合」时全部图表与宽表 100% 真实联动刷新。
- 彻底升级 `PortfolioManager.classify_fund_asset_class(self, fund_code, fund_name="")` 本体方法：当名称未传入或未命中时，自动反查 `CORE_STRATEGY_POOL`、`EXTENDED_FUND_CATALOG`、`UNIVERSE_18_CHAMPION_POOL`、`SECTOR_FUND_SELECTION`，补齐对医药（161726等）、消费白酒（161725等）、银行金融（160418等）、恒生港股（013402等）、半导体科创（008888/013841/011612等）、美股QDII（050025/001071等）、红利低波（005561/100032等）、宽基（300/500/1000）、纯债、黄金的精准分类，彻底消灭笼统的“61.5% 其他权益资产”。

### R6. 修复 14 大赛道温度计总表中指标回退兜底常数与空 pass 问题
- 在 `OpportunityRadarEngine._calc_dynamic_sector_metrics` 中，若某细分赛道的独立 parquet 不存在，必须从本地 DuckDB（`data/storage.duckdb` 中的指数/基金净值表）、`data/cache/market_screener/nav_cache/<top_fund_code>.parquet`（直接读取该赛道代表性冠军基金如 161726 医药、161725 白酒、160418 银行、013402 恒科、008888 半导体的真实历史净值序列）或对齐矩阵中提取真实日度价格序列来计算 20 日信噪比 `er_20`、乖离率 `bias_20`、斜率 `slope_20` 与结合 5日/60日波动率比值的 `crowding_score`，确保 14 个赛道 100% 拥有基于真实历史序列算出的独特动态指标，严禁共享 0.50 / +1.0% / 85.0 默认兜底常数。
- 删除 `get_sector_valuation_percentile` 中的空 `pass` 和硬编码常数：对纯债、黄金、红利、银行等赛道，基于本地真实利差/均线偏离或历史序列动态计算合理的风险估值分位。

### R7. 落实双翼看板右翼「主动风险预警哨」的同类预警折叠聚合与紧凑布局
- 在 `ActiveRiskSentry.inspect_portfolio` 或前端渲染中，当同一维度（如「未满7天锁仓」）触发的基金数量 >= 2 只时，自动合并为 1 张聚合预警卡片（标题列出前 2 只名称及总只数，如：`🔴 【未满7天锁仓红牌】富国中证红利(100032)、创金合信红利低波(005561) 等 4 只标的持有未满 7 天`），点击下方按钮可一键批量将这批基金全部加入 `tab2_locked_funds`。
- 将每条预警卡片与处置按钮改为紧凑布局（或放入固定最大高度 `max-height: 320px; overflow-y: auto` 的滚动容器中），杜绝右侧连排大卡片撑长页面。

### R8. 物理安全红线与开发质量约束
- 严禁修改只读裁判文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`），保持 SHA256 完好无损。
- 严禁修改 `DataLoader.simulate_execution` 的默认函数签名与默认扣费逻辑。
- 严禁编写写死数字的假文案、严禁写 pass 空分支、严禁画了前端控件却不传参给后端计算函数。


## 2026-11-05T16:13:16Z
启动专业买方投顾终端进阶升级：修复金融事实与交割规则错误、实装st.fragment局部刷新架构、首屏视觉提权、表格防丢数自动保存与实盘净值记账闭环。

物理安全红线：
1. 严禁修改只读裁判文件（judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py）。
2. 严禁修改 DataLoader.simulate_execution 的默认函数签名与默认扣费逻辑。

一、 修正 4 项金融事实错误与监管合规瑕疵（advisory_engine.py & data_loader.py & app_gui.py & trading_clock_fee.py）

1. 修正红利低波赛道的错误指数代码：
- 在 advisory_engine.py 的 RADAR_SECTOR_CATALOG 中，dividend_low_vol（红利低波）的 benchmark_index 和 index_code 被错误写成了 000978（000978 实为中证医药100指数）！请立即将其修正为 H30269（中证红利低波指数），并在 IndexValuationEngine 中确保 H30269 别名正确映射，彻底杜绝拿医药指数代码映射红利低波。

2. 区分 QDII 跨时区基金、纯债基金与普通 A 股基金的交割清算规则及估值可信度标签：
- 在 trading_clock_fee.py 与 portfolio_manager.py 中，识别 QDII 海外基金（如 050025 标普500、001071 华安纳指、013402 恒生科技等）：
  a. 在建仓单、调仓单与在途对账中心中，对美股 QDII 基金明确标注「T+2 确认份额 · 赎回 T+6~T+8 到账（跨时区清算，不可用于 T+2 极速换仓）」，并在计算 Tab 2「T+2 在途踏空风险」与「同公司基金转换」时，自动排除 QDII 基金与跨 TA 品种（QDII 严禁列入同公司 T+1 转换候选）。
  b. 在 Tab 1 建仓表与 Tab 2 持仓表的「实时估值涨跌(%)」列或实操指引中，根据基金类型动态附加估值可信度标识：指数联接基金标注「指数高准度」，纯债基金标注「债基看久期票息」，美股 QDII 白天标注「美股休市·看隔夜期指」，主动混合基金标注「季报重仓估算」。

3. 替换违规“保本”承诺词汇，符合证监会基金投顾合规规范：
- 在 app_gui.py（如滚动胜率卡第 1372 行等所有位置）中，将所有的「保本率」严格替换为合规专业术语「正收益概率 (≥0%)」或「本金安全率」，严禁在界面上出现任何“保本”字样。

4. 统一 14 大赛道动量与乖离率的价格口径（消除分红季全收益指数跃升偏误）：
- 在 advisory_engine.py 的 _calc_dynamic_sector_metrics 中，计算 20 日短期均线乖离率 bias_20 时，对红利类指数优先使用价格指数（000922.SH / H30269）或经除权平滑的日度序列，避免全收益指数在分红集中派息日产生虚假的正乖离脉冲而误报超买。

二、 架构级性能飞跃：引入 @st.fragment 局部刷新与数据新鲜度透明化（app_gui.py）

1. 使用 @st.fragment 解耦全页重跑，实现毫秒级局部交互响应：
- 在 app_gui.py 中，使用 Streamlit 原生 @st.fragment 装饰器（若当前环境支持 st.fragment），将以下独立交互区块封装为局部刷新组件（仅当区块内发生跨全局状态变更如切换主题、切换激活账本、或点击跨 Tab 跳转按钮时才调用 st.rerun() 全页刷新）：
  a. 侧边栏「核心指数行情走廊」自选配置与局部刷新；
  b. Tab 2 持仓账本的「极速录基吧台」与「主持仓表编辑」；
  c. Tab 3 组合回测的「回测对象与对标基准切换」；
  d. Tab 4 穿透工具的「穿透组合切换与 A/C 算费器」。
- 优化首屏渲染性能：确保在未切换到 Tab 3 和 Tab 4 时，利用轻量级缓存避免每次在 Tab 1/Tab 2 微调参数都重复触发底层高耗时重仓股穿透计算。

2. 新增「📡 数据源健康度与时效状态徽章（Data Freshness Badge）」：
- 在侧边栏「市场状态与底座」及顶部看板中，显式展示当前行情与估值的数据源状态（如：「🟢 实时盘中行情已连接 (更新于 HH:MM:SS)」或「🟡 离线湖仓快照兜底模式 (基准日 YYYY-MM-DD)」），一旦任何底层接口降级使用缓存兜底，必须如实告知用户，拒绝静默黑盒。

三、 UI/UX 关键体验痛点治理：首屏提权、表格防丢数自动保存与实盘净值记账（app_gui.py & portfolio_manager.py）

1. 首屏视觉提权——「双翼智能投顾看板」支持精简摘要条与展开详情切换：
- 为解决首屏上方内容过高导致四大主工作区 Tab 被压到屏幕下半截的问题：在双翼看板顶部提供紧凑的「📢 今日脉搏晨报 + 🎯 Top 3 机会赛道胶囊 + 🚨 风险预警汇总徽章（如：发现 X 项风险）」单行高密度导航条；
- 当风险巡检全通或用户正在下方 Tab 操作时，允许一键折叠收起双翼看板详情卡片，将宝贵的首屏空间让位给【🌱 新资建仓 / 💼 持仓调仓 / 📈 组合回测 / 🔍 穿透工具】四大主工作区！

2. Tab 2 主持仓表（st.data_editor）「未保存修改防丢失自动同步」机制：
- 解决用户在 st.data_editor 表格中修改了市值/盈亏/调仓意愿但忘记先点“保存修改并入库”就直接点击下方“诊断今日调仓时机”导致修改丢失的痛点：
- 编写统一的 `_auto_commit_pending_table_edits(edited_table, pm)` 辅助函数：
  a. 当检测到 edited_table 与当前 pm.holdings 存在未保存差异时，在表格上方显示醒目提示「检测到表格内有未保存的修改」；
  b. 当用户直接点击「💾 保存修改并入库」、「🔍 诊断今日调仓时机」或「🚀 一键执行全案」中的任意一个按钮时，系统自动先执行一次 `_auto_commit_pending_table_edits` 将表格修改写入 pm 账本，再继续执行后续诊断或调仓，确保用户在表格里的每一次改动 100% 生效不丢失！

3. 新增「📈 实盘账本历史净值记账曲线（Realized Account NAV Curve）」与「一键跟单打卡」：
- 在 portfolio_manager.py 中，每次调用 save_state(record_snapshot=True) 或同步净值时，在账本的 `nav_history` 列表中记录当日日期、账户总资产、份额净值与同期基准点位；
- 在 Tab 2 的「🗄️ 账本环境与实盘档案」子页中，绘制该账本从接管首日至今的《实盘账户累计净值 vs 沪深300基准走势图》，真实追踪每一笔实盘收益与超额 Alpha；
- 在 Tab 2 步骤三调仓执行单底部，提供「✅ 我已在手机端按此方案下单 -> 一键将调仓单同步至当前账本持仓」快捷按钮，实现从“看建议”到“记账入库”的完整投后闭环。

四、 自动化测试与交付验证
1. 运行 pytest 全量测试（含 test_infra.py）确保 100% 通过。
2. 新增测试验证：
- 断言 RADAR_SECTOR_CATALOG["dividend_low_vol"]["benchmark_index"] 已修正为 H30269（绝非 000978）；
- 断言全站 UI 源码中不再出现违规的“保本率”字样（已替换为“正收益概率”）；
- 断言 QDII 基金（050025）在交割规则中被正确识别为跨时区 T+2 确认、T+6+ 赎回且不进入同公司 T+1 转换列表；
- 运行 Streamlit AppTest 确认全站 4 个 Tab 渲染 0 异常，重启 8501 端口服务。


## 2026-11-09T06:54:06Z
启动 G13 世代首屏零阻塞秒开重构、全宽大胶囊主导航视觉提权、清除伪交易按钮与臃肿嵌套及回测曲线打假闭环任务

一、 核心问题定性与安全底线契约
1. 直面五大用户体验与审美灾难：当前版本存在以下五个不可接受的严重缺陷，本轮必须彻底根除：
第一，首屏加载极度缓慢（图1）：render_dual_wing_advisory_dashboard 在折叠框默认关闭的情况下，依然在主线程同步实例化了 2 次 OpportunityRadarEngine，并在未点开的因子进化 Popover 中调用了 get_60d_rolling_nav_and_trajectory（连续循环跑了 12 次遗传算法与 14 次磁盘 Parquet 读取），导致顶部 4 卡渲染完后下方大片白屏卡死数秒。
第二，伪交易按钮误导用户（图2）：本系统是纯投顾参谋与账本分析工具，不承担真实柜台交易功能，但界面上却放了让人看不懂的巨型红按钮「查看锁仓保护」、「一键批量锁定这2只标的调仓下界」、「择机置换」等伪系统控制按钮。
第三，双翼看板极度臃肿（图3）：右侧因为放了「查看锁仓保护」按钮切走了 18% 宽度的空白列；展开后内部塞了市场晨报、文字重叠穿模的牛熊拐点尺、3张赛道卡、右翼6个跳转按钮，以及底部的 4 个深度工具折叠框（14赛道总表、14:45折溢价、期权IV、QDII锁汇）。
第四，回测图文字遮挡且曲线失真（图4）：全周期净值曲线的图例框直接盖住了 2024 至 2026 年的净值曲线；同时底部的纯债指数被画成了毫无波动的直线，红利低波 8 年年化仅 2.35% 严重失真，而主实盘账本曲线因后视镜幸存者偏差呈现出不真实的旱地拔葱直线。
第五，四大核心功能入口极度不显眼（图5）：新资建仓、持仓调仓、组合回测、穿透工具四个最重要的一级入口缩在左上角变成 14px 灰色小字，视觉权重甚至不如底下的二级标题，且进入 Tab 后又重复打印一遍相同的巨型标题。
2. 物理安全红线：严禁修改四个只读裁判文件 judge_engine.py、holdout_vault.py、AGENT_SPEC.md、tests/test_infra.py，严禁修改 DataLoader.simulate_execution 的默认函数签名与默认扣费逻辑。允许并要求同步更新非只读测试文件（如 tests/test_adv_final_closure.py 等）中针对旧按钮或旧布局的断言，确保全量测试 100% 绿灯通过。

二、 第一阶段：针对五大痛点的外科手术级重构（修改 app_gui.py、advisory_engine.py、portfolio_manager.py、strategy_bridge.py）

1. 根治痛点 1（图1）：首屏零阻塞极速秒开（首屏主线程耗时必须小于 150ms）
第一，在 app_gui.py 的 render_dual_wing_advisory_dashboard 中，彻底禁止在首屏默认加载时调用 OpportunityRadarEngine()、evolve_factor_weights()、get_60d_rolling_nav_and_trajectory()、fetch_realtime_market_news_and_catalysts()、fetch_etf_feeder_arbitrage_sensors()、fetch_options_implied_volatility_sensors() 以及 evaluate_all_qdII_fx_arbitrage()！
第二，首屏顶部的投顾提示条仅基于内存中已有的 snapshot 与 pm.holdings 做纯内存毫秒级轻量判断（不发任何网络请求、不跑遗传进化、不读大 Parquet）。
第三，将 OnlineHeuristicFactorEvolver 的 60 日轨迹计算改为缓存在磁盘文件 data/cache/factor_evolution_cache.json 中（有效期 12 小时），严禁在每次渲染时现场循环跑 12 轮遗传进化；只有当用户主动点击展开雷达详情并点击刷新按钮时，才触发重算。

2. 根治痛点 2 与痛点 3（图2、图3）：彻底砍除所有伪交易按钮，重构清爽全宽投顾提示栏
第一，彻底删除首屏右上角的红色大按钮「查看锁仓保护 / 查看今日调仓单 / 检视持仓账本」（即删除 col_wing_btn 及其内部的 btn_master_action_switch 按钮），让投顾结论折叠栏占满 100% 全宽，彻底消灭图 3 右侧那条刺眼的空白竖柱！
第二，将投顾结论栏文案从伪系统黑话改为清晰的人话参谋提示（例如：今日投顾参谋：持仓含 2 只未满 7 天标的，赎回需扣 1.5% 惩罚费，调仓算法已自动为您避开卖出 ｜ 点击展开市场机会与持仓体检）。
第三，全面清理双翼看板内部的所有伪操作跳转按钮与臃肿嵌套：
- 删除右翼预警哨中的「一键批量锁定这2只标的调仓下界」按钮，以及每张风险卡片下方的「择机置换」、「平衡赛道敞口」、「穿透到底层」等所有按钮！右翼仅以干净紧凑的无按钮列表形式展示当前触发的 1 至 3 条核心风险提示与应对建议（未满 7 天标的在 Tab 2 调仓算法中默认自动锁定下界，无需用户手动点击锁定）。
- 删除左翼赛道卡片下方的 3 个「+ 入备选池」按钮，在卡片内直接清晰展示优选基金名称与 6 位代码。
- 从首屏双翼折叠框中彻底移出以下 5 个臃肿模块：① 嵌套的「历史三大牛熊拐点实盘对照尺」（消除图3中的文字重叠穿模，将其仅保留在 Tab 1 定投模式中并修复宽度防重叠）、②「查看全市场 14 大赛道量化温度计总表」、③「场内ETF与场外联接 14:45 尾盘折溢价套利感知」、④「50ETF与300ETF认沽期权隐含波动率防暴跌哨」、⑤「跨境QDII溢价与外汇期货锁汇成本套利精算」。将后 4 个深度工具统一归入 Tab 4「穿透工具」的二级子模块中，让首屏双翼折叠框展开后只有干净利落的一排「左翼 Top 3 赛道卡 + 右翼极简风险提示列表」，高度不超过 220px！

3. 根治痛点 5（图5）：重塑 90 分机构级 UI 审美，打造全宽四宫格高对比度主导航栏
第一，用强力 CSS 将顶层四大功能入口（新资建仓、持仓调仓、组合回测、穿透工具）从不起眼的 14px 小字改造为「100% 全宽四等分高对比度分段式大导航栏（Full-Width Segmented Navigation Bar）」：
- 定位顶层主 Tab 容器 `[data-testid="stMainBlockContainer"] > div > div > [data-testid="stTabs"] > [data-baseweb="tab-list"]`，设置 `display: grid !important; grid-template-columns: repeat(4, 1fr) !important; gap: 10px !important; background: var(--bg-elevated) !important; padding: 6px !important; border-radius: 10px !important; border: 1px solid var(--border-subtle) !important; margin-bottom: 14px !important;`。
- 定位顶层主 Tab 按钮，设置 `height: 46px !important; font-size: 16px !important; font-weight: 700 !important; border-radius: 8px !important; justify-content: center !important; background: var(--bg-surface) !important; border: 1px solid var(--border-subtle) !important; box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;`。
- 定位顶层选中态主 Tab 按钮 `button[aria-selected="true"]`，设置 `background: var(--accent-primary) !important; color: #ffffff !important; border-color: var(--accent-primary) !important; box-shadow: 0 4px 12px rgba(29, 78, 216, 0.25) !important;`（同时确保选中态按钮内部所有 span 和 p 文字颜色强制为 `#ffffff !important`）。
- 严格区分一级主导航与 Tab 4 内部的二级子 Tab（二级子 Tab 保持紧凑轻量的下划线样式，绝不与一级大导航混淆）。
第二，彻底删除四个主 Tab 内部开头重复打印的 `st.subheader("🌱 新资建仓")`、`st.subheader("💼 持仓调仓")`、`st.subheader("📈 组合回测")`、`st.subheader("🔍 穿透工具")` 及其下方的废话 caption！在 Tab 4 中，将「选择穿透体检组合对象」与「当前体检组合成分档案」合并为顶栏紧凑的一行摘要，直接把图表呈现给用户。

4. 根治痛点 4（图4）：修复回测图文字遮挡，彻底纠偏失真的基准曲线与后视镜偏差
第一，消灭文字遮挡图形：在 Tab 3 全周期净值曲线的 Plotly 图表布局中，将 legend 移至图表外部上方（设置 `legend=dict(orientation="h", yanchor="bottom", y=1.06, xanchor="left", x=0, bgcolor="rgba(0,0,0,0)")`，并将 `margin=dict(t=75, l=10, r=10, b=10)`），同时将牛熊阶段背景标注文字移至绘图区顶部边缘并调淡字色，确保没有任何一个文字或图例框压在净值曲线上！
第二，修复纯债指数与红利低波基准曲线的严重失真：检查 Tab 3 基准曲线的数据提取逻辑，严禁对纯债指数（H11009）使用起止点线性插值画直线！必须从 `aligned_matrix_total_return.parquet` 中提取真实的日度收盘序列计算归一化累计净值与真实年化收益率（CAGR），确保红利低波（H30269）、沪深300（H00300）、中证综合债（H11009）、黄金（AU9999）、纳指（SPX_CNY）的走势与历史真实全收益行情 100% 吻合。
第三，消除静态持仓回测的后视镜幸存者错觉：当回测目标为「当前实盘账本」时，若账本中包含黄金（000216）或美股纳指（017436）等近几年大涨的跨市场资产，除了在默认对标基准中自动勾选对应的黄金/海外基准供同图客观比对外，必须在图表上方明确标注「当前持仓静态权重历史回溯（含历史后视镜权重效应，非滚动样本外实盘记录）」，并提供一键切换对比「全天候滚动样本外动态策略曲线」，做到实事求是、不忽悠用户。

三、 第二阶段：强制重启服务并调用 /browser 进行实测秒开与五图逐一对比验收

完成上述代码修改后，必须先彻底终止旧的 8501 端口进程并清理缓存，重新启动最新服务，随后调用 /browser 打开 http://localhost:8501 对照本轮的 5 张问题图逐一截图核验：
1. 核验痛点 1（对比图1）：测试页面首次打开与刷新速度，确认首屏零白屏卡顿，1秒内完整渲染出顶部 4 卡、投顾提示条与四大核心 Tab 内容。
2. 核验痛点 2 与 3（对比图2、图3）：确认首屏右上角刺眼的「查看锁仓保护」红按钮与右侧空白列已彻底消失；点击展开投顾提示栏，确认内部不再有 4 个套娃折叠框、不再有「一键批量锁定」等伪交易按钮，牛熊拐点尺无任何文字重叠。
3. 核验痛点 5（对比图5）：确认「新资建仓、持仓调仓、组合回测、穿透工具」四个主入口已呈现为占满全宽、46px 高、高亮醒目的四宫格大胶囊导航栏，且点击切换各 Tab 时内部不再有重复的大标题。
4. 核验痛点 4（对比图4）：切换至「组合回测」，截图确认图例已移至图表外部上方、零遮挡净值曲线，确认纯债指数与红利低波为真实的日度历史波动曲线而非假直线。

四、 第三阶段：全量测试验证、Git 归档与生成 G14 世代指令（严守防转义命令标签门禁）

1. 运行全量自动化测试套件（包含 pytest tests/test_infra.py、tests/test_adv_final_closure.py、tests/test_g3_evolution_loop.py、tests/test_gui_multi_ledger_stress.py），确保 100% 绿灯通过。确认四个只读裁判文件零修改，确认 data/ledgers_index.json 仅保留干净的主实盘账本，清理所有临时脚本。
2. 将 G13 世代首屏零阻塞规范、全宽大胶囊主导航规范与非交易参谋定位准则更新写入当前工作区根目录 GEMINI.md 与 PROGRESS_LOG.md，严禁触碰全局配置文件。
3. 执行 Git 提交与标签同步：运行 git add -A，运行 git commit 记录 G13 开发进程，使用 git tag -a 打上版本标签 v4.3-G13，最后运行 git push origin HEAD 与 git push origin --tags 同步至 GitHub 远端。严格遵守禁令：绝对禁止创建任何 GitHub Release。
4. 在最终报告末尾输出供下一轮直接复制执行的 G14 世代进化指令。
【阻塞性门禁警告：防客户端转义命令标签校验】：
由于客户端输入框在接收提示词时，会将 Markdown 链接形式的命令标签转义为带冒号的内部格式，你在最终报告中输出 G14 指令时，绝对禁止输出带冒号的 slashCommand: 格式！
你输出的 G14 指令中的四个命令标签，必须 100% 严格按照以下字符序列拼接输出（圆括号内使用英文分号）：
- goal 命令必须写为：[/goal](slashCommand;goal)
- boost 命令必须写为：[/boost](slashCommand;boost)
- teamwork 命令必须写为：[/teamwork](slashCommand;teamwork)
- browser 命令必须写为：[/browser](slashCommand;browser)
内审与外审代理在终审时必须执行字符串检索：若最终报告的 G14 指令中出现任何一处冒号形式的 slashCommand:，一律判定门禁失败打回重写！其余正文保持纯文本无特殊排版符号，包含全量测试验证、Git Commit 与 Git Tag 同步（禁止创建 Release）以及继续按上述精确格式生成下一代指令的自举要求。
