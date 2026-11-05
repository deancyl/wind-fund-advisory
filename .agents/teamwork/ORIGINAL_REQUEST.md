# Original User Request

## Initial Request — 2026-11-05T14:06:32Z

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

## Acceptance Criteria

### 多账本体系与跨 Tab 联动
- [ ] 主实盘账本默认路径保持为 `portfolio_ledger.json`，受物理保护禁止删除；新建/克隆账本存放于 `data/ledgers/<ledger_id>.json`，元数据索引由 `data/ledgers_index.json` 维护。
- [ ] `MultiLedgerManager` 完整实现增、删、改、克隆、列表与全账本家庭汇总统计功能。
- [ ] 切换账本时全局 `pm`、顶部第 4 张卡片、预警哨、Tab 2、Tab 3、Tab 4 100% 同步指向当前激活账本，同步更新 `default_tier` 至 `active_tier_val` 并清空 Tab 2 缓存。
- [ ] Tab 2 顶部多账本管理吧台功能完整（当前账本选择器、新建 Popover、克隆 Popover、管理 Popover、沙盒提示）；Tab 1 支持覆盖写入当前账本或另存为全新账本。

### 四大实盘调仓场景真实性闭环
- [ ] `scenario_mode` 及所有场景参数真实传入 `simulate_rebalance_modes_and_consequences` 与 `generate_ai_rebalance_orders` 并纳入缓存签名。
- [ ] `new_cash_only` 场景下卖出金额为 0，买入金额总和严格等于 `new_cash_amount`。
- [ ] `withdraw_cash_only` 场景下买入金额为 0，赎回金额总和严格等于 `withdraw_cash_amount`，且严格避开未满 7 天红线标的。
- [ ] 开启 `freeze_reserved_chk` 时，可用调仓现金严格扣除 `pm.reserved_batch_cash`。

### 历史相似匹配动态统计
- [ ] Tab 3 历史相似匹配指标由 `analog_tab2["matches"]` 真实动态计算相对超额胜率、平均超额收益率、策略平均绝对收益率与平均最大回撤，无写死常数。
- [ ] 3 张历史卡片底部镜鉴文案根据真实收益关系动态分类生成各自独立的归因文案。

### Tab 4 穿透工具联动与精准资产分类
- [ ] 4 个穿透底层函数支持 `holdings_override`，聪明钱分析联动遍历当前选定持仓。
- [ ] `PortfolioManager.classify_fund_asset_class` 本体方法精准映射各细分赛道与宽基、债券、黄金，无笼统“其他权益资产”。

### 14 赛道真实动态指标
- [ ] 14 个赛道动态指标全部基于真实历史净值序列计算，没有任何赛道同时等于默认兜底值 (0.50, 1.0, 85.0)，且不同赛道指标具备真实区分度。
- [ ] `get_sector_valuation_percentile` 无空 `pass` 和硬编码常数返回值。

### 预警哨折叠聚合与界面紧凑化
- [ ] 同类预警数量 >= 2 时折叠聚合为单张卡片，支持一键批量加入 `tab2_locked_funds`。
- [ ] 预警区域布局紧凑或采用限定最大高度的滚动容器（`max-height: 320px; overflow-y: auto`）。

### 物理安全红线与自动化防作弊测试
- [ ] 4 大裁判文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）未被修改，SHA256 完全一致。
- [ ] `DataLoader.simulate_execution` 默认签名与扣费逻辑保持原样。
- [ ] 运行 pytest 全量测试（含只读 `tests/test_infra.py`）100% 通过。
- [ ] 专项防作弊测试 A（14赛道真动态检验）：调用 `OpportunityRadarEngine().scan_all_sectors()`，断言 14 个赛道无一共享兜底值 (0.50, 1.0, 85.0) 且具备真实区分度。
- [ ] 专项防作弊测试 B（四大调仓场景真实性检验）：以 `new_cash_only` 和 `withdraw_cash_only` 分别调用 `generate_ai_rebalance_orders`，断言指令金额与方向完全符合约束。
- [ ] 专项防作弊测试 C（多账本隔离与全站联动检验）：使用 MultiLedgerManager 创建沙盒账本、克隆账本、修改沙盒持仓，断言主实盘账本完好无损，且删除保护生效。
- [ ] 专项防作弊测试 D（Tab 4 跨组合穿透检验）：传入不同组合的 `holdings_override` 调用穿透计算，断言结果动态变化且 `classify_fund_asset_class` 无泛化其他权益资产。
- [ ] 运行 Streamlit `AppTest` 确认浅色与深色主题全站零报错，8501 端口服务平滑重启。
