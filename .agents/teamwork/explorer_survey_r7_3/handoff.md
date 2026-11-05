# Handoff Report — Explorer Survey r7_3 (R3, R4, R5 Investigation)

**Handoff Type**: Hard (Investigation complete)  
**Author**: Explorer Survey r7_3  
**Target Path**: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r7_3\report.md`  
**Date**: 2026-11-04  

---

## 1. Observation (客观观察)

1. **工作区目录与核心代码分布**：
   - `AGY2_FundAdvisory/app_gui.py`（3,874 行，204,415 字节）：包含主界面 Streamlit 视图，第 1420 行定义四大核心 Tab：`tab_zero_start, tab_holdings_and_rebalance, tab_backtest, tab_toolbox = st.tabs(["🌱 新资建仓", "💼 持仓调仓", "📈 组合回测", "🔍 穿透工具"])`。
   - `AGY2_FundAdvisory/app_gui.py` 第 2159~2305 行：Tab 1 步骤三实盘建仓执行单逻辑，当前仅调用 `StrategyBridge.generate_zero_start_blueprint(total_capital=float(plan_capital), ...)` 生成单次全额买入单，尚未实装资金建仓节奏选择器（模式一/二/三）。
   - `AGY2_FundAdvisory/portfolio_manager.py`（7,014 行，330,821 字节）：
     * 第 4703~4820 行定义真实多因子六维量化选基评分引擎 `compute_fund_six_dimension_score`（35% Alpha + 25% Fee + 15% Risk + 10% SmartMoney + 10% Crowding + 5% Macro）；
     * 第 246~278 行定义 `HoldingBatch`（含 `holding_days`, `buy_date`, `shares`, `cost_nav`, `safety_lock`）与 `FundHolding`。
   - `AGY2_FundAdvisory/portfolio_optimizer.py`（1,509 行，68,043 字节）：
     * 第 1090~1200 行定义 `WinRateOptimizer.optimize_rebalance_path`，已接入 `penalty_free_shares` 约束与 $<7$ 天锁仓保护。
   - `data/portfolio_watchdog.json`：持久化盯盘档案，已收录 8 只标的三色灯状态与点位预警。
   - `data/processed/aligned_matrix_total_return.parquet`：包含 2,142 交易日（2018-01-02 至 2026-11-03）的全收益对齐矩阵，列含 `H00300`, `H00905`, `H00852`, `H00922`, `H30269`, `930609`, `H11009`, `STAR50_STITCH`, `AU9999`, `SPX_CNY`, `BENCHMARK_30_70`, `BENCHMARK_50_50`。
   - `data/storage.duckdb`：包含 `v_index_valuations`, `v_indices`, `v_fund_snapshot`, `v_fund_trading_rules`, `v_financial_risk_screen`, `v_pledge_risk`, `v_option_volatility` 等 41 个表与视图。

2. **物理只读文件哈希核验证据**：
   - `AGY2_FundAdvisory/judge_engine.py`: SHA256 = `76f930371176de7ee6a413174b030101e3210ac6e037f5d10fe229af31cc07be`
   - `AGY2_FundAdvisory/holdout_vault.py`: SHA256 = `88122eaf647040a410e2fd95da81077db10149a498a47340ff40b670bd031d2a`
   - `AGY2_FundAdvisory/AGENT_SPEC.md`: SHA256 = `a346586f9bd2dc0ee83e665bd18e7a6471464c9f7b658e392b989b800cd63957`
   - `tests/test_infra.py`: SHA256 = `48bee0da300d7c0a0848ec1376e4b9b2e55224d2736081713b4340f0362cd100`

3. **测试基线执行实测**：
   - 运行 `py -3 -m pytest tests/test_infra.py`：14 passed in 7.49s；
   - 运行 `cmd /c "set PYTHONPATH=AGY2_FundAdvisory;. && py -3 -m pytest AGY2_FundAdvisory/tests/test_infra.py"`：15 passed in 8.47s。

---

## 2. Logic Chain (推理链条)

1. **R3.1 机会雷达实装逻辑**：
   - 依据需求，覆盖 14 大赛道。`data/processed/aligned_matrix_total_return.parquet` 覆盖了其中 10 大核心宽基与大类资产（沪深300、中证500、中证1000、科创50、中证红利、红利低波、纯债、综合债、黄金、标普500），其余 4 个细分行业（半导体芯片、医药医疗、消费白酒、银行高股息）可通过 DuckDB `v_indices` 或对应龙头公募基金净值序列（`013841`, `161726`, `161725`, `160418`）对齐接入。
   - 考夫曼 ER 公式 $ER_{20} = \frac{|\Delta P_{20}|}{\sum |\Delta P_i|}$ 可直接向量化计算，结合 $Bias_{20}$ 与 $Slope_{20}$ 构成动量拐点评分，当 $Bias_{20} > +6\%$ 时触发均值回归折价，严格兑现 GEMINI.md 规则 8。
   - 综合评分 $Score_{\text{radar}} = 0.30 S_{\text{val}} + 0.30 S_{\text{mom}} + 0.25 S_{\text{er}} + 0.15 S_{\text{crowd}}$ 排序前 3 名即可自动产出 Top 3 推荐。
   - Top 3 赛道调用已有的 `compute_fund_six_dimension_score` 选出得分最高标的，在 Streamlit 侧边或行情带下方渲染卡片，附 `➕ 纳入备选池` 按钮更新 `st.session_state.custom_candidate_pool`。

2. **R3.2 主动风险预警哨实装逻辑**：
   - `HoldingBatch` 已持久化记录 `holding_days`。因此 $\le 3$ 天 1.50% 扣款预警、刚满 7 天脱离惩罚提示、C 类刚满 30 天 0 赎回费提示均可精确逐批次触发。
   - 规模 $<0.5$ 亿迷你基清盘风险、经理变更、风格漂移等本体排雷指标可通过 `v_fund_snapshot` 与 `v_financial_risk_screen` 视图检索。
   - 当所有警告列表长度为 0 时，直接渲染 `🟢 巡检全通` 绿色胶囊，实现闭环。

3. **R3.3 分批建仓与智能定投算子实装逻辑**：
   - Tab 1 步骤三目前已有 `blueprint` 生成器。新增 `capital_deployment_mode` 单选组件（模式一、模式二、模式三）。
   - 模式二通过资金守恒拆解 $C_1 = 0.50 C$（买满纯债黄金红利及半仓权益）、$C_2 = 0.30 C$（回踩 MA20/MA60 网格补仓）、$C_3 = 0.20 C$（突破进攻线加仓，未触发前停泊短债/货基），在数值上满足 $C_1+C_2+C_3 \equiv C$。
   - 模式三基于当下 $Pct_{\text{erp}}$ 与 $Bias_{20}$ 动态缩放扣款乘数 $m_t \in [0.0, 2.0]$，并输出期数排期表。

4. **R4 & R5 架构与测试逻辑**：
   - 只读文件哈希锁死，不得修改。
   - 单元测试覆盖 Radar、Watchdog、DCA 核心逻辑；AppTest 覆盖 5 套主题与 4 个 Tab 交互 0 异常。

---

## 3. Caveats (注意事项与边界)

1. **离线与降级兜底**：若外部网络不可用，14 大赛道中的细分行业（半导体、白酒、医药、银行）优先回退至本地 DuckDB 视图与龙头基金净值切片，严禁抛出阻塞性网络异常。
2. **金额守恒浮点精度**：三步分批计算中，除法运算可能出现分厘级尾差（如 $0.3333$ 元），算法必须强制将四舍五入后的尾差（$\pm 0.01$ 元）动态加回至第一批纯债固收资产中，确保 $\sum C_i == C$ 绝对精准。
3. **AppTest 执行耗时**：运行全量 AppTest 时，需保证 `default_timeout >= 60s`，避免 Streamlit 首屏多因子计算被测试框架误杀。

---

## 4. Conclusion (调查结论)

需求 R3、R4、R5 的所有理论模型、代码依赖路径、数学公式与测试策略已完全清晰，方案具备极高的工程可落地性。
详细完整的工程技术规格、字段定义与伪代码已固化于：
`d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r7_3\report.md`。

---

## 5. Verification Method (独立核验方法)

1. **只读文件哈希核验**：
   ```powershell
   py -3 -c "import hashlib, pathlib; print('judge_engine:', hashlib.sha256(pathlib.Path('AGY2_FundAdvisory/judge_engine.py').read_bytes()).hexdigest() == '76f930371176de7ee6a413174b030101e3210ac6e037f5d10fe229af31cc07be')"
   ```
2. **基准测试回归核验**：
   ```powershell
   py -3 -m pytest tests/test_infra.py
   cmd /c "set PYTHONPATH=AGY2_FundAdvisory;. && py -3 -m pytest AGY2_FundAdvisory/tests/test_infra.py"
   ```
3. **交付报告核验**：
   检查 `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r7_3\report.md` 是否完整阐述了 R3.1、R3.2、R3.3、R4、R5 的所有细节。
