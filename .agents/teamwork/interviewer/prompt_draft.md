启动终极专业度与工程闭环校准：修复热重载与一键全案漏网Bug、打通全目录资产分类对齐、实装真实数学公式驱动的股息安全垫与影子组合调仓复盘、以及安全局部刷新。

Working directory: d:\Google\Workspace\Wind
Integrity mode: development

## Reference Materials
- 核心代码路径：
  - Streamlit GUI 主程序：`AGY2_FundAdvisory/app_gui.py` (端口 8501)
  - 核心策略与模型：`portfolio_manager.py`, `strategy_bridge.py`, `data_loader.py`
  - 只读裁判文件：`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`

## Verification Resources
- 自动化测试套件：pytest 全量测试（含只读 `tests/test_infra.py`）
- 专项测试 1：验证 `pm.classify_fund_asset_class` 对 161726、161725、160418、013402、008888、050025、005561、002351、000216 全部返回 9 大标准类别，无一返回“其他权益资产”
- 专项测试 2：验证 `StrategyBridge.calculate_portfolio_yield_cushion` 与 `pm.evaluate_rebalance_audit` 返回真实动态计算数值，且修改持仓 `current_nav` 时影子资产与实盘资产随之真实联动
- 专项测试 3：运行 Streamlit `AppTest` 验证全站 4 个 Tab 零异常报错，8501 端口服务平滑重启

## Requirements

### R1. 精准修复热重载导入遗漏与一键全案表格自动保存拦截
- 在 `app_gui.py` 第 131 行 `if _need_reimport or not st.session_state.get("_modules_initialized"):` 内部的 `from portfolio_manager import (...)` 中，显式补上 `FundHolding, HoldingItem`，确保模块发生热重载时 Tab 4 缓存函数不抛出 `NameError`。
- 在 Tab 2「🚀 一键执行全案」按钮分支（`if st.button("🚀 一键执行全案", ...):`，`app_gui.py` 第 2385~2395 行）内第一行，补齐自动保存调用：`if "edited_table" in locals() and edited_table is not None: _commit_edited_holdings_table(edited_table, pm)`，确保用户在主持仓表中修改市值、盈亏或调仓意愿后直接点击全案时修改 100% 自动入库生效。

### R2. 升级资产大类分类器消除死代码，实现全基金池标准大类对齐
- 直接升级 `portfolio_manager.py` 中的 `PortfolioManager.classify_fund_asset_class(self, fund_code: str, fund_name: str = "") -> str` 本体方法，并在 `app_gui.py` 第 176~205 行去掉 `if not hasattr` 条件，保持两端代码完全一致（注意：在 `portfolio_manager.py` 内部严禁顶层导入 `strategy_bridge` 以防循环导入，仅查询自身模块的 `holdings`、`CORE_STRATEGY_POOL`、`EXTENDED_FUND_CATALOG`、`SECTOR_FUND_SELECTION` 及 `resolve_fund_meta`）。
- 当传入的 `fund_name` 为空或等于代码时，自动依次从 `self.holdings`、`CORE_STRATEGY_POOL`、`EXTENDED_FUND_CATALOG`、`SECTOR_FUND_SELECTION` 中反查真实基金名称与 category。
- 采用与现有优化器及 AI 目标配比 100% 兼容的标准资产大类映射规则：
  - 名称含 [债, 国债, 利差, 固收, 纯债, 中短债, 裕祥] 或代码 in ["002351", "018757", "000191", "003376"] -> "纯债固收"
  - 名称含 [黄金, AU, 金ETF, Gold, 博时黄金, 华安易富黄金] 或代码 in ["000216", "518880", "002611", "000929"] -> "黄金对冲"
  - 名称含 [标普, 纳斯达克, 纳指, 海外, 美股, SPX, NDX, QDII, 全球] 或代码 in ["050025", "001071", "161125", "040046", "270042"] -> "美股海外对冲"
  - 名称含 [红利低波, 低波, 红利低波动] 或代码 in ["005561", "512890", "007466", "008114"] -> "A股红利低波"
  - 名称含 [红利, 股息, 银行, 金融, 价值, 央企] 或代码 in ["100032", "160418", "090010", "001594"] -> "A股红利高股息"
  - 名称含 [科创, 芯片, 半导体, 集成电路, 科技, 人工智能, 信息, 恒生科技, 恒科, 互联网, 创业板, 军工, 新能源, 光伏] 或代码 in ["011612", "011613", "008888", "013841", "013402", "017436", "001618"] -> "科技成长进攻"
  - 名称含 [1000, 中小盘, 小盘, 微盘, 2000] 或代码 in ["004194", "016634", "001053"] -> "中小盘成长"
  - 名称含 [500, 中盘, 中证500, 医药, 生物, 医疗, 健康, 创金合信医疗] 或代码 in ["000478", "161726", "003095", "001717"] -> "中盘均衡"
  - 名称含 [300, 沪深300, 蓝筹, 上证50, 核心, 50ETF, 白酒, 消费, 食品, 饮料, 沪港深] 或代码 in ["110020", "161725", "000311", "110011"] -> "核心蓝筹"
  确保上述所有主流宽基与行业基金 100% 落入这 9 大标准类别，使 Tab 4 的「资产大类配比图」与「资产缺口分析表」完全对齐，彻底消灭“61.5% 其他权益资产”。

### R3. QDII 跨时区交割标注与同公司 T+1 转换隔离
- 在 Tab 2 工具坞「🔄 同公司基金低摩擦转换」（`app_gui.py` 第 2335~2365 行）中，扫描候选基金时自动排除 QDII 海外基金（代码 in ["050025", "001071", "013402"] 或名称含 [标普, 纳指, 纳斯达克, 恒生, QDII, 美股, 黄金]），并在页面上方增加提示条：「💡 交割规则说明：海外 QDII 基金（T+2确认、赎回 T+6~T+8 到账）与跨注册登记机构品种不支持同公司 T+1 极速转换，系统已自动过滤保护」。
- 在 Tab 1 步骤三建仓表与 Tab 2 持仓表中，为每只基金根据类型提供精准估值与交割提示（指数联接标注「指数高准度·T+1确认」，纯债标注「票息底仓·看久期」，美股/港股 QDII 标注「跨时区T+2确认·看隔夜外盘」）。

### R4. 实装组合年度股息与票息安全垫精算引擎（真实数学公式）
- 在 `StrategyBridge` 中实装静态方法 `calculate_portfolio_yield_cushion(weights_or_holdings: Any, total_capital: float, pm: Any = None) -> Dict[str, Any]`：
  - 基于各标准资产大类的真实底层股息率/到期票息率基准（A股红利低波: 5.2%, A股红利高股息: 4.8%, 核心蓝筹: 2.8%, 中盘均衡: 1.8%, 中小盘成长: 1.0%, 科技成长进攻: 0.6%, 纯债固收: 2.75%, 美股海外对冲: 1.3%, 黄金对冲: 0.0%），对组合内每只基金按权重加权求和，计算：
    1) `weighted_yield_pct`：组合加权年化股息与票息率 (%)；
    2) `annual_cushion_amount`：`total_capital * (weighted_yield_pct / 100.0)`（组合每年由底层企业分红与债券票息产生的内生安全垫总额，元/年）；
    3) `monthly_equivalent_amount`：`annual_cushion_amount / 12.0`（折合月均内生收息安全垫，元/月）；
    4) `cash_dividend_payout_est`：统计组合中分红方式设为 cash（现金分红）的红利/权益基金预计每年直接派发到账的现金分红金额（元/年）。
- 在 Tab 1 步骤二（方案核心归因旁）与 Tab 2 步骤一（资产基线横幅内）醒目展示该内生收息安全垫指标，帮助用户在市场震荡期看清组合的现金流造血能力。

### R5. 实装实盘调仓决策复盘 vs 初始躺平影子组合（真实数学公式）
- 在 `PortfolioManager` 中维护真实的初始基准持仓快照 `self.initial_baseline_snapshot`（记录接管首日或首次建仓时的 `{fund_code: shares}` 与 `initial_cash`）。
- 编写方法 `pm.evaluate_rebalance_audit() -> Dict[str, Any]`，严格按真实数学公式计算（严禁硬编码常数）：
  1) `current_actual_equity`：当前实盘总资产 `self.total_equity`；
  2) `shadow_hold_equity`：若从基准确立日起一分钱不调仓（保持 `initial_baseline_snapshot` 的份额不变，乘以各基金今日最新 `current_nav` 加 `initial_cash`）的今日影子总资产；
  3) `rebalance_value_add`：`current_actual_equity - shadow_hold_equity`（调仓与主动管理带来的真实净增厚金额，元）；
  4) `saved_penalty_and_buffer_fees`：统计当前持仓中因 <7天 锁仓拦截免除的 1.50% 惩罚费总额 + 临期 C 类缓卖省下的 0.50% 赎回费总额。
- 在 Tab 2 工具坞「🗄️ 账本环境与实盘档案」子页的净值曲线下方，渲染「📊 买方投顾价值与调仓复盘账单」3 列指标卡（① 实盘当前总资产 vs 初始躺平影子总资产；② 调仓主动管理净增厚；③ AI 风控防线累计为您拦截避免的惩罚费与赎回费损耗）。

### R6. 数据源健康度徽座与安全的 @st.fragment 局部刷新
- 在侧边栏「🕒 市场状态与底座」卡片中新增一行「📡 行情源状态」：根据 `mb_data.get("source")` 与实时行情缓存状态，动态显示 🟢 东财/新浪实时盘中源 或 🟡 本地湖仓离线快照兜底，让数据真实性与时效性一目了然。
- 在主工作区 Tab 4 中，将独立的「💡 A/C算费工具」子渲染逻辑封装为带 `@st.fragment` 装饰器的函数（使用 `getattr(st, "fragment", lambda f: f)` 优雅兼容，且绝对不在 `st.sidebar` 内部或涉及侧边栏的函数上使用），使修改费率与天数滑块时实现毫秒级局部刷新。

### R7. 物理安全红线与开发质量约束
- 严禁修改只读裁判文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）。
- 严禁修改 `DataLoader.simulate_execution` 的默认签名与默认扣费逻辑。
- 严禁编写任何写死常数的假计算（如写死影子超额 +1.2% 或写死省费金额），所有展示数字必须由底层持仓份额、净值与费率算子实时算出。
- 严禁在 `st.sidebar` 内部或涉及侧边栏的函数上使用 `@st.fragment`（会触发 `StreamlitAPIException` 崩溃）。

## Acceptance Criteria

### 工程漏洞修复与资产分类对齐
- [ ] `app_gui.py` 热重载导入块包含 `FundHolding, HoldingItem`，模块发生热重载时 Tab 4 缓存函数无 `NameError`。
- [ ] Tab 2「🚀 一键执行全案」点击后优先执行表格数据自动入库，修改内容 100% 自动入库生效。
- [ ] `PortfolioManager.classify_fund_asset_class` 本体方法升级并移除 `app_gui.py` 中的 `if not hasattr` 条件，对医药(161726)、白酒(161725)、银行(160418)、恒科(013402)、半导体(008888)、美股QDII(050025)、红利低波(005561)、纯债(002351)、黄金(000216)等 100% 映射至 9 大标准类别，Tab 4 资产大类配比图与缺口分析表对齐且无“61.5% 其他权益资产”。
- [ ] Tab 2 工具坞「🔄 同公司基金低摩擦转换」候选标的自动排除 QDII 海外基金并展示说明；Tab 1 与 Tab 2 显示各基金对应类型交割与估值提示。

### 买方投顾数学模型升级与 UI 局部刷新
- [ ] `StrategyBridge.calculate_portfolio_yield_cushion` 静态方法基于 9 大类真实基准和持仓权重动态输出加权收益率、年化安全垫金额、月均等效金额及现金分红预估，在 Tab 1 步骤二与 Tab 2 步骤一正常展示。
- [ ] `PortfolioManager.evaluate_rebalance_audit` 严格按实际净值与基准份额计算影子资产、主动管理净增厚及规避的费率损耗，在 Tab 2 账本档案子页以 3 列指标卡真实渲染。
- [ ] 侧边栏市场状态卡片动态显示行情源健康度徽座（实时源或离线快照）。
- [ ] Tab 4「A/C算费工具」安全接入 `@st.fragment` 实现毫秒级局部刷新，侧边栏无任何 `@st.fragment` 引用。

### 物理安全红线与自动化测试
- [ ] 4 大裁判文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）未被修改。
- [ ] `DataLoader.simulate_execution` 默认函数签名与扣费逻辑保持原样。
- [ ] 运行 pytest 全量测试（含只读 `tests/test_infra.py`）100% 通过。
- [ ] 专项测试 1 通过：验证 `pm.classify_fund_asset_class` 对 161726、161725、160418、013402、008888、050025、005561、002351、000216 全部返回 9 大标准类别，无一返回“其他权益资产”。
- [ ] 专项测试 2 通过：验证 `StrategyBridge.calculate_portfolio_yield_cushion` 与 `pm.evaluate_rebalance_audit` 返回真实动态计算数值，且当修改持仓 `current_nav` 时影子资产与实盘资产随之真实变化。
- [ ] 专项测试 3 通过：运行 Streamlit `AppTest` 验证全站 4 个 Tab 零异常报错，8501 端口服务平滑重启。
