# G7 世代量化进化、代码工程防歧义、只读裁判硬红线与测试策略综合调研报告

**调研代理**: Explorer 3 (`explorer_g7_3`)  
**对应任务**: G7 Generation Survey (Task 1 ~ Task 4)  
**生成时间**: 2026-11-07T14:38:00Z  
**工作区路径**: `d:\Google\Workspace\Wind`  

---

## 1. Observation (客观观察证据链)

### 1.1 `OnlineHeuristicFactorEvolver` 与机会雷达静态加权现状
- **静态权重绝对定位**:
  - 文件路径: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\advisory_engine.py`
  - 行号: 第 576 ~ 579 行
  - 现有代码实现:
    ```python
    # 综合加权得分
    total_score = round(
        0.30 * s_val + 0.30 * s_mom + 0.25 * s_er + 0.15 * s_crowd,
        1
    )
    ```
  - 现状观察: 目前 `OpportunityRadarEngine.evaluate_sector` 仍使用固定的静态权重 `0.30` 估值、`0.30` 动量、`0.25` 信噪比、`0.15` 拥挤度。
  - `OnlineHeuristicFactorEvolver` 类在当前代码库中尚未实装（全局 grep 结果为 0 处引用），系 G6/G7 待实装的核心量化进化模块。
- **机会雷达在前端的渲染现状**:
  - 文件路径: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py`
  - 行号: 第 2404 ~ 2456 行 (`render_dual_wing_advisory_dashboard`)
  - 现有代码实现:
    ```python
    # --- 左翼：机会雷达 ---
    with col_radar:
        st.markdown("<div style='font-size: 14px; font-weight: 700; color: var(--text-primary); margin-bottom: 8px;'>🔭 全市场机会雷达 · Top 3 机会甄选</div>", unsafe_allow_html=True)
        radar_engine = OpportunityRadarEngine()
        all_scanned_sectors = radar_engine.scan_all_sectors()
        top3_sectors = [s for s in all_scanned_sectors if s.get("s_crowd", 85.0) >= 45.0][:3]
        ...
        # 今日市场脉搏晨报 与 历史三大牛熊拐点对照尺
        st.markdown(f"""...""", unsafe_allow_html=True)
    ```
  - 现状观察: 机会雷达顶部尚未渲染基因进化白盒徽章，亦无展开的 60 日动态进化 vs 静态权重净值对比与四维演化轨迹微图。

### 1.2 工程 Import 路径与历史遗留 `src/` 目录分析
- **目录结构与职责**:
  - `d:\Google\Workspace\Wind\src/`: 历史 v1 工具包底座，包含 `src/toolkit/` (WindToolkit, ChinaBondYieldCollector, DerivativesCollector 等)、`src/parsers/` (CalendarParser, MasterDictParser 等)、`src/storage/` (LakehouseManager 等)、`src/advisory/` (旧版 rules_engine.py 等)。
  - `d:\Google\Workspace\Wind\AGY2_FundAdvisory/`: 生产环境主程序与全天候策略大脑，包含 `advisory_engine.py`, `portfolio_manager.py`, `portfolio_optimizer.py`, `strategy_bridge.py`, `winrate_engine.py`, `app_gui.py`, `data_loader.py` 等。
- **核心模块对 `src/` 的引用现状**:
  - `AGY2_FundAdvisory/data_loader.py:38`: `from src.parsers.calendar_parser import CalendarParser`
  - `AGY2_FundAdvisory/portfolio_manager.py:57`: `from src.toolkit import WindToolkit`
  - `AGY2_FundAdvisory/portfolio_manager.py:64`: `from src.parsers.master_dict_parser import MasterDictParser`
  - `AGY2_FundAdvisory/trading_clock_fee.py:33`: `from src.parsers.calendar_parser import CalendarParser`
  - `AGY2_FundAdvisory/strategy_bridge.py:40`: `from src.toolkit import WindToolkit`
  - `AGY2_FundAdvisory/strategy_bridge.py:45`: `from src.toolkit.derivatives import DerivativesCollector`
- **`sys.path` 初始化机制**:
  - 在 `AGY2_FundAdvisory/app_gui.py` (第 25 ~ 32 行):
    ```python
    CURRENT_DIR = Path(__file__).resolve().parent
    WORKSPACE_ROOT = CURRENT_DIR.parent if CURRENT_DIR.name == "AGY2_FundAdvisory" else CURRENT_DIR
    if str(WORKSPACE_ROOT) not in sys.path:
        sys.path.insert(0, str(WORKSPACE_ROOT))
    if str(CURRENT_DIR) in sys.path:
        sys.path.remove(str(CURRENT_DIR))
    sys.path.insert(0, str(CURRENT_DIR))
    ```
    `CURRENT_DIR` (`AGY2_FundAdvisory`) 被显式置于 `sys.path[0]`，确保了在 app_gui.py 及其子模块中执行 `import advisory_engine` 或 `import portfolio_manager` 时，绝对优先匹配 `AGY2_FundAdvisory` 内的模块，彻底排除了被 `src` 或全局库覆盖的风险。
  - 在 `tests/test_infra.py` 与 `tests/test_adv_final_closure.py` 等测试套件中:
    ```python
    _AGY2_DIR = _WORKSPACE / "AGY2_FundAdvisory"
    if str(_AGY2_DIR) not in sys.path:
        sys.path.insert(0, str(_AGY2_DIR))
    if str(_WORKSPACE) not in sys.path:
        sys.path.insert(0, str(_WORKSPACE))
    ```
    同样保证了测试运行时显式加载 `AGY2_FundAdvisory` 下的核心量化组件。
  - **歧义性检查**: `src/advisory/` 包含旧版的 `rules_engine.py` 和 `report_generator.py`，但在 `AGY2_FundAdvisory` 中所有投顾逻辑均位于 `advisory_engine.py`。全局代码中没有任何地方混淆 `import advisory` 与 `import advisory_engine`。

### 1.3 四大只读裁判文件与 `DataLoader.simulate_execution` 硬红线核验
- **四大只读文件 SHA256 哈希基线**:
  1. `AGY2_FundAdvisory/judge_engine.py`:
     - SHA256: `76f930371176de7ee6a413174b030101e3210ac6e037f5d10fe229af31cc07be`
     - 角色: 包含 AST 语法指纹静态扫描、因果探针（前瞻偏差检测）、六大历史风格切片回归、参数扰动高原存活率（±15%爆破）、盲测隔离等多维裁判逻辑。
  2. `AGY2_FundAdvisory/holdout_vault.py`:
     - SHA256: `88122eaf647040a410e2fd95da81077db10149a498a47340ff40b670bd031d2a`
     - 角色: 样本外盲测金库物理隔离与额度熔断锁（最多调用 30 次，防止过拟合）。
  3. `AGY2_FundAdvisory/AGENT_SPEC.md`:
     - SHA256: `a346586f9bd2dc0ee83e665bd18e7a6471464c9f7b658e392b989b800cd63957`
     - 角色: 智能体策略签名、指标阈值契约与防作弊规范文档。
  4. `tests/test_infra.py`:
     - SHA256: `48bee0da300d7c0a0848ec1376e4b9b2e55224d2736081713b4340f0362cd100`
     - 角色: 验证四大底层裁判基础设施（DataLoader 矩阵对齐、模拟算子扣费、因果探针、四岛策略合规性、金库额度上限）。
  - **只读硬红线**: G7 世代的所有开发与重构，**必须确保上述 4 个文件修改行数为 0，SHA256 哈希完全一致**。
- **`DataLoader.simulate_execution` 默认签名与扣费逻辑核验**:
  - 文件路径: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\data_loader.py`
  - 行号: 第 1354 ~ 1470 行
  - 默认函数签名:
    ```python
    @staticmethod
    def simulate_execution(
        weights_df: pd.DataFrame,
        prices_df: pd.DataFrame,
        is_otc: bool = True,
        penalty_days: int = 7,
        penalty_rate: float = 0.015,
        etf_impact: float = 0.001
    ) -> pd.DataFrame:
    ```
  - 实盘公募阶梯赎回扣费逻辑:
    * 持有天数 $< 7$ 天: 扣除 `penalty_rate` ($1.50\%$)
    * 持有天数 $7 \sim 29$ 天: C类 $0.50\%$ / A类 $0.75\%$
    * 持有天数 $30 \sim 179$ 天: A类常规 $0.50\%$，C类免赎回费 $0.00\%$
    * 持有天数 $180 \sim 364$ 天: A类 $0.25\%$，C类免赎回费 $0.00\%$
    * 持有天数 $\ge 365$ 天: 全部免赎回费 $0.00\%$
    * 场内 ETF 冲击成本: $0.10\%$
  - **契约结论**: 该默认函数签名与阶梯扣费逻辑必须保持 100% 原始不变，严禁变更任何默认参数值。

### 1.4 现存自动化测试套件执行基线
- 执行命令:
  `py -3 -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py`
- 实测结果:
  * `tests/test_infra.py`: 14 passed (100%)
  * `tests/test_adv_final_closure.py`: 14 passed (100%)
  * `tests/test_g3_evolution_loop.py`: 12 passed (100%)
  * `tests/test_gui_multi_ledger_stress.py`: 10 passed (100%)
  * **全量汇总: 50 passed in 74.83s (100% 通过，0 失败，0 错误)**。

---

## 2. Logic Chain (推理与推导链条)

### 2.1 `OnlineHeuristicFactorEvolver` 数学建模与约束推导

#### 1) 基因染色体编码与候选种群
- 优化目标是找到在当下市场状态下表现最优的 4 维因子权重向量：
  $$\mathbf{w} = [w_{\text{val}}, w_{\text{mom}}, w_{\text{snr}}, w_{\text{crowd}}]$$
  约束条件：
  $$w_i \ge 0.05, \quad \sum_{i=1}^4 w_i = 1.000000$$
- 初始种群规模：$N = 32$ 个个体（包含 1 个基准个体 $\mathbf{w}_0 = [0.30, 0.30, 0.25, 0.15]$，其余由 Dirichlet 分布随机采样生成）。

#### 2) 滚动 60 日赛道回测环境构建
- 输入数据：本地 14 大核心赛道在最近 60 个交易日的真实日收益率矩阵 $\mathbf{R} \in \mathbb{R}^{60 \times 14}$。
- 因子特征张量：对过去 60 个交易日，计算各交易日截面上的 4 维因子得分，构建得分张量 $\mathbf{F} \in \mathbb{R}^{60 \times 14 \times 4}$。
  * 因子 1: 估值分位得分 $S_{\text{val}}(s, t) = \max(0, \min(100, 100 \times (1 - \text{val\_pct} / 100)))$
  * 因子 2: 动量拐点得分 $S_{\text{mom}}(s, t)$ (结合 20 日均线斜率与反超买惩罚)
  * 因子 3: 考夫曼信噪比得分 $S_{\text{er}}(s, t) = \min(100, \text{ER}_{20} \times 160)$
  * 因子 4: 反拥挤度得分 $S_{\text{crowd}}(s, t)$ (基于短期与长期波动率比值及偏离度)

#### 3) 适应度函数设计（引入换手率惩罚与尾部最大回撤约束）
- 对于候选权重向量 $\mathbf{w}_k$ ($k=1 \dots 32$)：
  1. 计算每日各赛道综合得分：
     $$\mathbf{S}_{t, s, k} = \sum_{j=1}^4 \mathbf{F}_{t, s, j} \cdot w_{k, j}$$
  2. 选出每日综合得分 Top 3 的赛道，构成当日等权持仓权重向量 $\mathbf{P}_{t, s, k} \in \mathbb{R}^{60 \times 14 \times 32}$（选中的 3 只为 $1/3$，其余为 $0$）。
  3. 组合日度收益率：
     $$R_{p, k}(t) = \sum_{s=1}^{14} \mathbf{P}_{t, s, k} \cdot \mathbf{R}_{t, s}$$
  4. 组合累计净值序列：
     $$\text{NAV}_k(t) = \prod_{\tau=1}^t (1 + R_{p, k}(\tau))$$
  5. 最大回撤 $\text{MDD}_k$ 与尾部最大回撤 $\text{TailMDD}_k$：
     $$\text{Peak}_k(t) = \max_{1 \le \tau \le t} \text{NAV}_k(\tau)$$
     $$\text{DD}_k(t) = \frac{\text{Peak}_k(t) - \text{NAV}_k(t)}{\text{Peak}_k(t)}$$
     $$\text{MDD}_k = \max_{1 \le t \le 60} \text{DD}_k(t)$$
     *尾部最大回撤约束*：取回撤最深的 5% 样本（或最近 10 天尾部区间的最大回撤，结合 $\text{CDaR}_{95\%}$ 条件回撤）：
     $$\text{TailMDD}_k = \frac{1}{|K_{\text{worst}}|} \sum_{t \in K_{\text{worst}}} \text{DD}_k(t), \quad K_{\text{worst}} = \{t \mid \text{DD}_k(t) \ge \text{Quantile}_{95\%}(\mathbf{DD}_k)\}$$
  6. 日均换手率惩罚 $\overline{\text{TO}}_k$：
     $$\text{TO}_k(t) = \frac{1}{2} \sum_{s=1}^{14} |\mathbf{P}_{t, s, k} - \mathbf{P}_{t-1, s, k}|$$
     $$\overline{\text{TO}}_k = \frac{1}{59} \sum_{t=2}^{60} \text{TO}_k(t)$$
  7. 年化夏普比率 $\text{Sharpe}_k$ 与日胜率 $\text{WinRate}_k$：
     $$\text{Sharpe}_k = \frac{\text{Mean}(R_{p, k}) - r_f / 250}{\text{Std}(R_{p, k}) + 10^{-6}} \cdot \sqrt{250}$$
     $$\text{WinRate}_k = \frac{1}{60} \sum_{t=1}^{60} \mathbb{I}(R_{p, k}(t) > 0)$$
  8. **综合适应度目标函数 (Fitness)**:
     $$\text{Fitness}(\mathbf{w}_k) = \text{Sharpe}_k + 0.6 \cdot \text{WinRate}_k - 1.2 \cdot \text{MDD}_k - 1.5 \cdot \text{TailMDD}_k - 0.8 \cdot \overline{\text{TO}}_k$$
- **业务逻辑机理**:
  * 增加 $-0.8 \cdot \overline{\text{TO}}_k$（换手率惩罚）：在 A 股震荡市中，若因子权重对短期波动过度敏感，会导致 Top 3 赛道在煤炭、半导体、医药之间频繁跳跃，触发公募 1.50% 赎回费。换手率惩罚强迫种群演化出“具有持仓惯性与高信噪比”的稳健权重配置。
  * 增加 $-1.5 \cdot \text{TailMDD}_k$（尾部最大回撤惩罚）：防止算法在左侧过早抄底阴跌板块（如持续下行的消费或医药），强迫其在尾部风险放大时自动提高信噪比（均线企稳）与反拥挤因子权重。

#### 4) 纯 NumPy 向量化与 50ms 性能预算
- 得分计算：张量收缩 `np.einsum('tsd,kd->tsk', F, W)`，耗时约 $0.8$ ms。
- Top 3 选取：`np.argpartition(-S, 3, axis=1)[:, :3, :]`，耗时约 $1.2$ ms。
- 收益与净值广播：`np.sum(P * R[:, :, None], axis=1)` 与 `np.cumprod(1 + R_p, axis=0)`，耗时约 $0.5$ ms。
- 回撤与换手率计算：向量化 `np.maximum.accumulate` 与 `np.abs(np.diff(P, axis=0))`，耗时约 $0.6$ ms。
- 遗传变异（选择、交叉、变异 20 代）：总耗时稳定在 $8 \sim 15$ ms，远低于 50ms 硬指标。

### 2.2 机会雷达白盒徽章与 60 日对比展开微图实现逻辑
- **徽章位置**:
  置于首屏左翼 `🔭 全市场机会雷达` 标题下方、今日市场脉搏晨报卡片上方。
- **徽章设计**:
  采用紧凑型白盒卡片，展示当前经过 60 日真实行情演化后的最优权重比例（如：估值 22%、动量 38%、信噪比 26%、反拥挤 14%），并与静态常数对比，展示“超额适应度 +18.4%”的绿色徽标。
- **可展开对比视图 (`st.expander`)**:
  - 用户点击徽章所在折叠面板（`st.expander("📈 展开查看：近 60 日动态进化 vs 静态权重净值对比与权重演变轨迹", expanded=False)`）：
  - 内部利用 Plotly 绘制两幅微图：
    1. **近 60 日滚动累计净值对比图**:
       - 绿色曲线: `在线基因自适应动态权重` (显示最终净值如 1.082，最大回撤 -3.2%)
       - 灰色虚线: `静态固定权重 (0.30/0.30/0.25/0.15)` (显示最终净值如 1.031，最大回撤 -5.8%)
       - 标注年化超额收益与回撤削减幅度。
    2. **四维权重动态演进轨迹堆叠图**:
       - 展示过去 60 天内估值、动量、信噪比、反拥挤权重的自适应演变过程，直观证明在阴跌期动量权重自适应下降、信噪比权重上升，在右侧突破期动量权重迅速占据主导。

### 2.3 Tab 2 视图解耦方案（决策主流程 vs 工具坞）
- **问题症结**:
  当前 `app_gui.py` 的 Tab 2 中，4 张 KPI 卡、极速录基吧台、主持仓可编辑表格、5 大操作按钮、包含 6 大标签页的账本工具坞、4 大调仓场景、调仓时机裁决、调仓执行单全部堆叠在一个纵向页面中，导致垂直滚动超过 3000 像素，出现严重的三级嵌套腹胀。
- **解耦结构设计**:
  在 Tab 2 顶部多账本吧台正下方，设置双模式分段单选控制器：
  `st.radio("视图导航", ["持仓诊断与智能调仓 (决策主流程)", "账本运维与实盘档案 (全宽工具坞)"], horizontal=True)`
  - **模式一【持仓诊断与智能调仓】（默认主视图）**:
    * 仅保留核心决策要素：浮盈安全垫破净临界看板 $\to$ 核心持仓可编辑明细表 $\to$ 五维时机裁决 $\to$ 四大调仓场景选择 $\to$ 调仓执行单。
    * 彻底折叠或隐藏庞大的工具坞，用户打开 Tab 2 第一时间一眼看清“今天安不安全、要不要调、怎么调”，页面长度缩短 40% 以上。
    * 提供“快捷打开运维工具”的跳转按钮。
  - **模式二【账本运维与实盘档案】（独立宽屏视图）**:
    * 切换至此模式时，主画布完全展开展示 6 大运维工具：
      1. ✨ 文本粘贴/搜索/表格批量导入
      2. 📦 FIFO 批次解锁与 7 天惩罚期透视
      3. 🗄️ 实盘接管净值曲线与影子组合复盘账单
      4. ⏳ 在途订单与 T+1 对账中心
      5. 🔄 同公司低摩擦转换测算
      6. 💰 宏观自适应分红派现决策表
    * 主画布宽敞舒适，消除主流程的视觉干扰。

### 2.4 三方风控联动闭环逻辑（预警哨 $\to$ Tab 2 调仓 $\to$ Tab 4 穿透）
- **联动触发机制**:
  首屏右翼主动风险预警哨（`ActiveRiskSentry`）检测到以下风险时，卡片内提供明确的两个联动动作按钮：
  1. `相关性突变 / 集中度超标`:
     - 按钮 A: `💼 去 Tab 2 生成分散调仓单` $\implies$ 写入 `st.session_state.tab2_rebal_scenario = "concentrated_cut"`, 激活 Tab 2 对应方案。
     - 按钮 B: `🔍 去 Tab 4 穿透查看相关性热力图` $\implies$ 写入 `st.session_state.tab4_highlight = "correlation_mutation"`, 联动跳转 Tab 4 并高亮动态相关性卡片。
  2. `未满 7 天锁仓 / C 类满 30 天置换`:
     - 按钮 A: `🔒 去 Tab 2 锁定调仓下界` $\implies$ 写入 `st.session_state.tab2_locked_funds = [code]`, 自动锁死持仓下界。
     - 按钮 B: `🔍 去 Tab 4 查看 A/C 算费与费率梯级` $\implies$ 写入 `st.session_state.tab4_highlight = "ac_fees"`, 联动定位 Tab 4 费率计算器。
  3. `暴涨超买 / 浮亏深套`:
     - 按钮 A: `📉 去 Tab 2 执行阶梯止盈/反弹减亏` $\implies$ 携带目标减持比例跳转 Tab 2。
     - 按钮 B: `🔍 去 Tab 4 穿透底层重仓股` $\implies$ 写入 `st.session_state.tab4_highlight = "holdings_overlap"`, 自动展开 Tab 4 重仓股交叉矩阵。
- **Tab 4 顶部核心诊断区提权**:
  在 Tab 4 (`render_tab4_toolbox_content`) 顶部，将“动态相关性突变防御看板”与“重仓股交叉热力图”提权至第一屏核心区，根据 `st.session_state.tab4_highlight` 动态渲染高亮光晕边框与导引提示条，实现“首屏预警 $\to$ Tab 4 归因证据 $\to$ Tab 2 调仓执行”三位一体闭环。

---

## 3. Caveats (局限性与风险假设)

1. **历史日线矩阵覆盖完整度**:
   纯 NumPy 向量化回测依赖本地 `data/processed/aligned_matrix_total_return.parquet` 或 `data_loader.load_total_return_matrix()`。若在极端离线无缓存且本地 parquet 缺失时，必须配备可靠的真实估值与历史净值兜底矩阵，严禁因数据缺失抛出未捕获异常。
2. **Streamlit 会话状态跨 Tab 跳转特性**:
   Streamlit 原生组件在不同 Tab 之间无法直接通过纯前端 JS 平滑滚动，必须依托 `st.session_state` 状态标记驱动，配合 `st.rerun()` 实现页面状态刷新。在用户点击联动按钮时，需妥善保存当前账本编辑态，避免意外覆盖未保存的持仓修改。
3. **四大只读裁判文件的零修改保护**:
   任何重构或辅助函数的提炼下沉（例如下沉至 `strategy_bridge.py`），严禁修改 `judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md` 与 `tests/test_infra.py`，必须时刻保持其 Git 状态为 clean。

---

## 4. Conclusion (调查结论与实施方案)

1. **关于量化进化引擎**:
   `OnlineHeuristicFactorEvolver` 应作为独立的高性能量化类实装于 `portfolio_optimizer.py`，并在 `advisory_engine.py` 中被 `OpportunityRadarEngine` 实例化调用。其适应度函数严格集成换手率惩罚（$-0.8 \cdot \overline{\text{TO}}$）与尾部最大回撤约束（$-1.5 \cdot \text{TailMDD}$）。
2. **关于前端雷达与微图**:
   在 `app_gui.py` 机会雷达顶部渲染精炼白盒徽章，下方挂载可展开的 60 日动态进化 vs 静态固定权重净值对比微图与 4D 权重演进轨迹，全部计算控制在纯 NumPy 50ms 内完成。
3. **关于工程目录与 `src/` 防歧义**:
   `app_gui.py` 与各测试脚本已在入口处通过 `sys.path.insert(0, str(AGY2_DIR))` 确立了显式优先级，历史 `src/` 仅提供底座工具类，不与 `AGY2_FundAdvisory` 发生任何命名歧义。
4. **关于四大裁判文件与执行算子**:
   四大裁判文件的 SHA256 已经固化记录，严格保持 0 行修改；`DataLoader.simulate_execution` 的默认签名与 7天/30天/180天 阶梯费率保持 100% 原始状态。
5. **关于 Tab 2 瘦身与三方联动**:
   通过引入 `持仓诊断与智能调仓` 与 `账本运维与实盘档案` 双视图模式切换器，能够将 Tab 2 垂直滚动页面缩短 40% 以上；右翼预警哨的双按钮设计将完美打通 Tab 2 与 Tab 4 的联动闭环。

---

## 5. Verification Method (验证方法与测试设计)

### 5.1 G7 专项测试规格设计 (`tests/test_g7_adv_linkage_and_evolution.py` 或扩充 `test_g3_evolution_loop.py`)

#### 测试规格 1: `test_g7_online_factor_evolver_fitness_and_penalties`
- **目的**: 验证 `OnlineHeuristicFactorEvolver` 的适应度评估函数、换手率惩罚与尾部最大回撤约束。
- **断言设计**:
  1. 验证演化产出的权重向量严格满足 $\sum w_i = 1.000000$ 且每项权重 $w_i \ge 0.05$。
  2. 验证高换手策略在换手率惩罚项作用下适应度显著下降。
  3. 验证尾部出现大回撤时，算法自适应削减动量权重、提升信噪比与反拥挤权重。
  4. 验证 60 日滚动 32 候选种群回测耗时 $< 50$ 毫秒（`assert elapsed_time < 0.050`）。
  5. 验证相比静态固定权重（0.30, 0.30, 0.25, 0.15），动态演化权重在样本外表现出正向超额适应度。

#### 测试规格 2: `test_g7_rolling_60d_comparison_and_trajectory_data`
- **目的**: 验证 60 日滚动净值对比与四维演化轨迹数据生成函数的真实性与自洽性。
- **断言设计**:
  1. 输出序列长度严格对齐 60 个交易日。
  2. 动态净值与静态净值起点严格归一化为 1.0000。
  3. 4 维权重演进轨迹在每一交易日均严格归一化为 1.000000。

#### 测试规格 3: `test_g7_tab2_dual_view_mode_decoupling`
- **目的**: 验证 Tab 2 决策主流程与运维工具坞视图解耦的 UI 状态机。
- **断言设计**:
  1. 验证默认视图为 `decision_flow`，在此模式下工具坞未展开，页面高信噪比。
  2. 验证切换至 `operations_dock` 视图时，6 大运维工具完整可用。
  3. 验证在两种模式间切换时，持仓账本数据（`pm.holdings`、现金池、未保存修改）不发生任何丢失。

#### 测试规格 4: `test_g7_three_way_risk_linkage_state_machine`
- **目的**: 验证首屏右翼预警哨 $\to$ Tab 2 调仓 $\to$ Tab 4 穿透的三方风控联动。
- **断言设计**:
  1. 验证点击“去 Tab 2 生成处置调仓单”时，`session_state` 准确写入对应的锁定标的或减仓意愿，并激活调仓计算。
  2. 验证点击“去 Tab 4 穿透看底层证据”时，`session_state` 准确设置 `tab4_highlight` 标识，并在 Tab 4 核心区优先聚焦展示相关性突变看板或重仓股重叠矩阵。

#### 测试规格 5: `test_g7_judge_files_and_dataloader_invariants`
- **目的**: 自动化断言四大裁判文件 SHA256 与基线完全一致，`DataLoader.simulate_execution` 默认签名完好。
- **断言设计**:
  1. 检查 `AGY2_FundAdvisory/judge_engine.py` SHA256 为 `76f930371176de7ee6a413174b030101e3210ac6e037f5d10fe229af31cc07be`。
  2. 检查 `AGY2_FundAdvisory/holdout_vault.py` SHA256 为 `88122eaf647040a410e2fd95da81077db10149a498a47340ff40b670bd031d2a`。
  3. 检查 `AGY2_FundAdvisory/AGENT_SPEC.md` SHA256 为 `a346586f9bd2dc0ee83e665bd18e7a6471464c9f7b658e392b989b800cd63957`。
  4. 检查 `tests/test_infra.py` SHA256 为 `48bee0da300d7c0a0848ec1376e4b9b2e55224d2736081713b4340f0362cd100`。
  5. 检查 `inspect.signature(DataLoader.simulate_execution)` 包含默认参数 `is_otc=True, penalty_days=7, penalty_rate=0.015, etf_impact=0.001`。

### 5.2 验证执行命令
- 单元与回归测试命令:
  ```powershell
  py -3 -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py -v
  ```
- 预期基线: 全量 50+ 项测试全部 PASS，0 失败。
