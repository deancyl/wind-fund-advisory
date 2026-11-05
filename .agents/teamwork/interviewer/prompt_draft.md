启动深色模式DOM精准穿透修复、反迎合真数据闭环整改及买方投顾专业能力升级任务。

Working directory: d:\Google\Workspace\Wind
Integrity mode: development

## Reference Materials
- 核心代码路径：
  - Streamlit GUI 主程序：`AGY2_FundAdvisory/app_gui.py` (端口 8501)
  - 核心策略与模型：`AGY2_FundAdvisory/advisory_engine.py`, `data_loader.py`, `strategy_bridge.py`, `portfolio_optimizer.py`, `portfolio_manager.py`, `winrate_engine.py`
  - 数据湖仓：`data/processed/aligned_matrix_total_return.parquet`, `data/cache/`
- Python 解释器：`C:\Users\deanc\AppData\Local\Programs\Python\Python311\python.exe`

## Verification Resources
- 只读裁判文件与哈希基线：`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`（物理安全红线，严禁修改，运行 `python verify_referee_hashes.py` 验证完整性）
- 演示组合与特定测试标的：`pm.load_demo_portfolio()`（包含 3 天锁仓标的 011612、28 天临近免赎标的 011613、-16.19% 深套标的 013841）
- 自动化测试工具链：pytest 单元测试套件、`tests/test_infra.py`、Streamlit `AppTest`

## Requirements

### R1. 精准修复深色模式下文字与控件看不见的 DOM 穿透问题（app_gui.py）
- 删除 `app_gui.py` 第 548 至 554 行中导致弹窗内滑块与按钮隐形的 `div[data-baseweb="popover"] *` 与 `div[data-baseweb="menu"] *` 错误星号通配符；改为精准指定容器背景：仅对 `[data-testid="stPopoverBody"]`, `div[data-baseweb="popover"] > div`, `div[data-baseweb="menu"]`, `ul[data-testid="stSelectboxVirtualDropdown"]` 设置 `background-color: var(--bg-surface) !important; border: 1px solid var(--border-subtle) !important;`。
- 修复外层带边框容器与内部输入框同色无边界问题：将 `[data-testid="stVerticalBlockBorderWrapper"]` 的背景设为 `var(--bg-surface) !important`，边框设为 `1px solid var(--border-subtle) !important`；将输入框与下拉框内胆（`div[data-baseweb="select"] > div`, `[data-testid="stNumberInputContainer"]`, `[data-testid="stTextInput"] input`, `[data-testid="stTextArea"] textarea`）的背景设为 `var(--bg-elevated) !important`，边框设为 `1px solid var(--border-hover) !important`，形成清晰深浅层次。
- 显式穿透下拉框选中文本、下拉菜单项、提示框与滑块刻度，解决黑底黑字问题：
  - 下拉框当前选中文字与图标：`div[data-baseweb="select"] div`, `div[data-baseweb="select"] span`, `div[data-baseweb="select"] input` 设置 `color: var(--text-primary) !important; -webkit-text-fill-color: var(--text-primary) !important;` 以及 `div[data-baseweb="select"] svg` 设置 `fill: var(--text-secondary) !important;`。
  - 下拉展开菜单选项文字：`li[role="option"]`, `li[role="option"] div`, `li[role="option"] span` 设置 `color: var(--text-primary) !important; background-color: var(--bg-surface) !important;`，悬停与选中态 `li[role="option"]:hover`, `li[role="option"][aria-selected="true"]` 设置 `background-color: var(--bg-elevated) !important; color: var(--accent-primary) !important;`。
  - 多选胶囊标签（Multiselect Tag）：`span[data-baseweb="tag"]` 设置 `background-color: var(--accent-primary) !important; color: #ffffff !important;` 且内部 `span, svg` 设置 `color: #ffffff !important; fill: #ffffff !important;`。
  - 数字与文本输入框内文字：`[data-testid="stNumberInput"] input`, `[data-testid="stTextInput"] input`, `[data-testid="stTextArea"] textarea` 设置 `color: var(--text-primary) !important; -webkit-text-fill-color: var(--text-primary) !important;`。
  - 提示框、折叠框、Tab页与滑块数值：`div[data-testid="stAlert"] p`, `div[data-testid="stAlert"] span`, `div[data-testid="stExpander"] summary p`, `div[data-testid="stExpander"] summary span`, `[data-testid="stTabs"] button p`, `[data-testid="stThumbValue"]`, `[data-testid="stTickBarMin"]`, `[data-testid="stTickBarMax"]` 设置 `color: var(--text-primary) !important;`，同时保持选中 Tab `[data-testid="stTabs"] button[aria-selected="true"] p` 设置 `color: var(--accent-primary) !important;`。
  - Primary 主按钮保持纯白字：`button[kind="primary"] p`, `button[kind="primary"] span`, `[data-testid="stBaseButton-primary"] p`, `[data-testid="stBaseButton-primary"] span` 设置 `color: #ffffff !important;`。

### R2. 彻底整改 5 处迎合性假代码，打通全链路物理闭环
- **修正半导体赛道错误映射与分赛道专业估值体系**：
  - 在 `advisory_engine.py` 的 `RADAR_SECTOR_CATALOG` 中，将 `semiconductor`（半导体芯片）的 `matrix_col` 从错误的 `930609`（纯债）修正为 `STAR50_STITCH`（或半导体指数序列）。
  - 在 `data_loader.py` 的 `IndexValuationEngine` 中废除 `tail(120)` 半年短窗口，统一采用近 5 至 8 年（至少 1250 个交易日或全历史样本）计算分位数；实施分赛道专业估值锚：宽基/消费/医药使用长周期 PE-TTM 分位数，红利/高股息/银行（000922, H30269, 399986）结合 PB 分位数与股息风险溢价（股息率减 10Y 国债收益率）综合计算合理分位，避免低利率时代将高股息错误判定为 90% 过热；科创/半导体结合 PB/PS 与 PE 综合评定；在 `RADAR_SECTOR_CATALOG` 中保留校准后的 `fallback_val_pct` 作为离线兜底，严禁直接拿 3 年收盘价分位冒充估值分位或盲目返回 50.0%。
- **修复 ActiveRiskSentry 在真实 HoldingItem 上浮亏率与乖离率恒为 0 的 Bug**：
  - 遍历持仓时，若元素为 `HoldingItem` 实例（含 `cost_price` 与 `current_nav` 且 `cost_price > 0`），必须通过 `(current_nav - cost_price) / cost_price * 100.0` 真实计算单基浮动盈亏率 `pnl_pct`，并关联 `OpportunityRadarEngine.dynamic_metrics` 动态获取该持仓所属赛道的真实 20 日均线乖离率 `bias_20` 与估值分位。
  - 实装深套持仓 Beta vs Alpha 病根剥离诊断：当单基浮亏 `pnl_pct <= -12.0%`（如演示组合中 013841 浮亏 -16.19%）时，自动对比该基金浮亏与同赛道基准表现及重仓重叠度，输出精准归因诊断与操作建议。
- **打通预警哨「一键处置按钮」与 Tab 2 调仓引擎的真实联动**：
  - 当用户在预警哨点击「锁定调仓下界」（写入 `tab2_locked_funds`）或「生成阶梯止盈单」（写入 `tab2_pending_take_profit`）时，`StrategyBridge.generate_ai_rebalance_orders` 与 `simulate_rebalance_modes_and_consequences` 必须真实读取并执行：将锁定标的的减仓额强制设为 0（标注已手动锁定禁卖），将止盈标的的目标权重下调 40% 并转配至纯债/红利底仓，同时自动置 `tab2_diagnosed = True` 与 `tab2_rebalanced = True`，在 Tab 2 顶部显示已激活的风控指令横幅与清除按钮。
- **将 7 大机构定权模型与黑天鹅压力测试卡真实挂载到前端**：
  - 在 `app_gui.py` 的 `model_options_map` 下拉框及模型对比折叠框中完整挂入全部 7 大模型：鲁棒双核HRP (`hrp_cvar`)、核心-卫星杠铃 (`core_satellite`)、全天候风险平价 (`all_weather`)、BL主客观观点融合 (`black_litterman`)、条件胜率最优 (`cond_winrate`)、尾部风控CVaR (`min_cvar`)、凯利动量增强 (`kelly_momentum`)，确保每个模型在后端运行独立真实的数学求解逻辑（BL模型真实融合 `radar_selected_funds` 观点）。
  - 在 Tab 1 步骤二（5张人话指标卡下方）与 Tab 3（组合回测指标卡下方）真实调用 `simulate_black_swan_stress` 与 `render_black_swan_stress_card`，展示 2018、2022、2024 三大历史极端危机下的最大浮亏金额、回本时长与超额防御表现。
- **打通分批建仓 / 智能定投与 Tab 1 初始持仓及 Tab 2 调仓的跨模块自洽**：
  - `pm.apply_zero_start_blueprint` 默认保持 `deployment_mode="lump_sum"`（100% 写入持仓，兼容现有测试）；当用户在界面选择「稳健三步分批建仓」点击设为初始持仓时，传入 `deployment_mode="three_step_batches"`，将 50% 今日底仓写入 `pm.holdings`，剩余 50% 存入 `pm.available_cash` 并在预案中记录为分批建仓储备金（`reserved_batch_cash`）；选「智能定投」时按首期实扣金额建仓。
  - 在 Tab 2 进行持仓诊断与调仓计算时，若检测到存在分批建仓储备金，提供开关默认「按当前已投底仓核定结构偏离（保留分批储备现金）」，避免 Tab 1 刚留出 50% 分批现金、Tab 2 就立刻催促全额买光。

### R3. 5 项买方投顾专业性内核升级
- **风险贡献度占比（PCR %）与「以损定仓」护栏**：
  - 在 Tab 1 步骤一根据本金与档位 95% CVaR 计算极端预计最大亏损额（元），在策略摘要卡中醒目提示风险预算底线。
  - 基于协方差矩阵严格按公式 $PCR_i = \frac{w_i \cdot (\Sigma w)_i}{w^T \Sigma w} \times 100\%$ 计算每只入选基金的风险贡献度占比，并在 Tab 1 步骤三建仓表与 Tab 4 资产缺口表中新增「风险贡献占比(%)」列。
- **恢复在途订单确认与 T+1 对账中心及同公司基金转换路由**：
  - 在 Tab 2 持仓账本工具坞中新增「在途订单与 T+1 交割确认」子页：列出 `pm.orders` 中的在途单，支持一键按最新净值确认交割入账或撤单退回现金。
  - 在 Tab 2 生成调仓单时，自动识别同属一家基金公司（如均为华夏、富国、易方达等）的卖出与买入指令，在实操要点中标注「同公司转换（省T+2在途空窗·申购费补差）」。
- **宏观估值自适应分红策略**：
  - 动态生成分红方式建议：当 ERP >= 70% 或赛道估值分位 <= 35%（底部低估击球区）时，建议设为「红利再投（底部免申购费复利攒份额）」；当 ERP < 40% 或赛道估值分位 >= 70%（中高估区）时，建议设为「现金分红（免赎回费自动落袋锁利）」。
- **赛道拥挤度算法升级**：
  - 在 `advisory_engine.py` 计算赛道拥挤度评分时，引入近 5 日波动率与近 60 日波动率比值（Vol Ratio）与 20 日均线乖离率的复合惩罚，准确识别高位放量剧震风险。
- **Tab 2 调仓净效用门禁与投后超额归因及省费账单**：
  - 在 Tab 2 步骤二/三显式计算并展示：若持仓存在差 1 至 7 天即满 7 天或 C 类差 1 至 7 天满 30 天免赎回费的批次（如演示组合持有 28 天的 011613），醒目提示「等待 N 天再调仓可立省赎回费 ¥XX.XX 元」。
  - 在 Tab 2 展示接管以来的投后归因摘要（拆解基准 Beta 收益、配置与选基 Alpha 超额、以及 AI 风控防线累计拦截省下的惩罚费与缓冲省费金额）。

### R4. 物理安全红线与开发质量约束
- **严禁修改只读裁判文件**：`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py` 必须保持 SHA256 完好无损。
- **严禁修改 DataLoader.simulate_execution** 的默认函数签名与默认扣费数学逻辑，确保 `test_infra.py` 100% 原样通过。
- **严禁编写只为应付测试的空壳函数**、严禁写入不消费的 `session_state` 变量、严禁定义渲染函数却不在页面调用。

## Acceptance Criteria

### 深色模式 DOM 精准修复
- [ ] 删除 `app_gui.py` 548-554 行的 `div[data-baseweb="popover"] *` 和 `div[data-baseweb="menu"] *` 星号通配符，弹窗内滑块轨道、按钮及输入框正常显示且背景分层清晰。
- [ ] `[data-testid="stVerticalBlockBorderWrapper"]` 背景为 `var(--bg-surface)`，边框为 `1px solid var(--border-subtle)`。
- [ ] 输入框与下拉框内胆背景为 `var(--bg-elevated)`，边框为 `1px solid var(--border-hover)`。
- [ ] 下拉框当前选中文本、展开选项、多选标签、输入框文本、提示框、折叠框、Tab页与滑块数值颜色穿透生效，无黑底黑字现象。
- [ ] Primary 主按钮文字在深色和浅色模式下均强制为纯白色（`#ffffff`）。

### 假代码整改与物理闭环
- [ ] `advisory_engine.py` 的 `RADAR_SECTOR_CATALOG` 中 `semiconductor` 的 `matrix_col` 修正为 `STAR50_STITCH`（或半导体指数序列），不再指向纯债。
- [ ] `IndexValuationEngine` 废除 `tail(120)`，统一采用近 5 至 8 年长周期样本计算分位数；红利/高股息/银行结合 PB 与股息风险溢价计算合理分位，科创/半导体结合 PB/PS 与 PE 计算合理分位。
- [ ] `ActiveRiskSentry` 对 `HoldingItem` 实例准确按 `(current_nav - cost_price) / cost_price * 100.0` 计算 `pnl_pct` 并关联动态 20 日均线乖离率；对浮亏 <= -12.0% 标的输出 Beta vs Alpha 归因诊断。
- [ ] 预警哨点击「锁定调仓下界」后，调仓引擎将锁定标的减仓额设为 0；点击「生成阶梯止盈单」后，止盈标的目标权重下调 40% 并转配至纯债/红利，Tab 2 顶部展示风控指令横幅与清除按钮。
- [ ] 前端 `model_options_map` 下拉框与对比折叠框完整挂载 7 大机构定权模型，且各模型后端运行独立真实的数学求解逻辑。
- [ ] Tab 1 步骤二与 Tab 3 回测真实展示 2018、2022、2024 三大历史黑天鹅极端压力测试卡片。
- [ ] 分批建仓模式下，50% 写入持仓，50% 存入可用现金并记录为 `reserved_batch_cash`；Tab 2 诊断提供保留分批储备现金的偏离核定开关。

### 买方投顾内核升级
- [ ] Tab 1 步骤一展示 95% CVaR 极端最大亏损额（元）风险预算；建仓表与资产缺口表展示根据 $PCR_i$ 计算的风险贡献占比列，且风险贡献度之和严格等于 100%。
- [ ] Tab 2 持仓账本中展示「在途订单与 T+1 交割确认」子页，支持一键交割或撤单；调仓单中自动识别并标注同公司转换路由。
- [ ] 宏观估值分红策略根据 ERP 与赛道估值分位动态切换「红利再投」与「现金分红」建议。
- [ ] 赛道拥挤度评分引入 5 日 / 60 日波动率比值与 20 日均线乖离率复合惩罚。
- [ ] Tab 2 醒目提示临近免赎期批次的省费天数与金额；展示投后 Beta 收益、Alpha 超额与 AI 风控防线省费金额。

### 物理安全红线与自动化测试
- [ ] 4 大裁判文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）未被修改，SHA256 哈希完全一致。
- [ ] `DataLoader.simulate_execution` 默认签名与扣费逻辑保持原样，`tests/test_infra.py` 100% 通过。
- [ ] 运行 pytest 全量测试套件 100% 通过。
- [ ] 运行集成测试验证：`pm.load_demo_portfolio()` 传入 `ActiveRiskSentry` 准确输出 011612（锁仓红牌）、011613（临近免赎黄牌）、013841（深套归因）预警；验证 7 大模型下拉框与黑天鹅测试卡正常渲染；验证风险贡献度 PCR 之和等于 100%。
- [ ] 运行 Streamlit `AppTest` 确认浅色与深色主题下全站零报错，8501 端口服务平滑重启且正常响应。
