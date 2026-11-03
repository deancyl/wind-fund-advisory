启动“量化引擎抗白噪音与市场节奏自适应升级 + UI逻辑收官修复”任务，在核心算法中引入考夫曼信噪比卡尔曼滤波、动量加速度防追高、随机矩阵理论(RMT)去噪与跳跃扩散分块自助法，并同步落实 app_gui.py 的交互收官修复与测试验证。

Working directory: d:\Google\Workspace\Wind
Integrity mode: development

物理安全红线：严禁触碰只读裁判文件（judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py）。所有新增算子集中在 data_loader.py、winrate_engine.py、portfolio_optimizer.py、strategy_bridge.py 与 app_gui.py 中实现。

## Verification Resources
- 现有测试套件位于 `tests/` 目录（包含 `test_interactive_continuity.py`、`test_ui_and_logic_refinements.py` 等）。
- 物理安全红线裁判文件：`judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py`（只读，严禁修改）。
- 团队依据任务需求新建针对性单元测试与 AppTest 验证。

## Requirements

### R1. 引入考夫曼效率系数（ER 信噪比）与卡尔曼滤波自适应变速器（strategy_bridge.py）
- 实现 `compute_market_snr_and_kalman_state(price_series, window=20)`：
  - 计算考夫曼效率系数（信噪比代理指标）$ER_t = \frac{|P_t - P_{t-w}|}{\sum_{i=0}^{w-1} |P_{t-i} - P_{t-i-1}|} \in [0, 1]$（$ER \to 1$ 代表高信噪比单边趋势，$ER \to 0$ 代表纯白噪音震荡）；
  - 使用一维卡尔曼滤波（观测噪声方差 $R$ 随 $1 - ER_t$ 动态放大）提取剥离日度白噪音后的真实趋势净值与斜率。
- 动态自适应动量窗口：根据实时信噪比 $ER_t$，将风格比拼的动量回看窗口从死板的 `60日` 升级为动态无级变速窗口 $W_{\text{eff}} = \text{int}(60 - 40 \times ER_t) \in [20, 60]$（趋势越强、信噪比越高，回看窗口自动缩短至 20 日极速跟进主升浪；震荡白噪音越大，窗口自动拉长至 60 日稳守红利底仓）。

### R2. 引入动量二阶导（加速度衰竭）与期权 iVIX 脉冲防追高与提前止盈算子（strategy_bridge.py）
- 同时监控快周期动量（15日）与慢周期动量（60日），计算动量加速度（二阶导数）$\text{Accel} = \text{Mom}_{15} - \frac{15}{60}\text{Mom}_{60}$。
- 当处于进攻状态但检测到“高拥挤度 + 动量加速度大幅转负（高位滞涨衰竭）+ 期权 iVIX 单日跳升”时（判定阈值与参数由团队结合现有代码常模与量化实践合理设定），自动在状态机中触发「⚡ 动量衰竭预警：暂停追高进攻标的，新增资金转入红利/纯债缓冲」，并在顶部看板与步骤二白盒面板中展示实时市场信噪比（SNR）与动量加速度。

### R3. 实装随机矩阵理论（RMT Marchenko-Pastur）与 Ledoit-Wolf 收缩协方差去噪算子（data_loader.py & portfolio_optimizer.py）
- 在 `DataLoader.compute_ewma_volatility_and_correlation` 及 `WinRateOptimizer` 构建协方差/相关性矩阵时，加入 `denoise_covariance_matrix(corr_matrix, n_obs=60, shrink_alpha=0.15)`。
- 计算 Marchenko-Pastur 理论白噪音特征值上限 $\lambda_+ = (1 + \sqrt{N / T})^2$；将所有 $\le \lambda_+$ 的随机白噪音特征值替换为它们的均值（保持矩阵迹不变），重构去噪后的相关性矩阵并叠加 `shrink_alpha=0.15` 的对角收缩（Ledoit-Wolf Shrinkage），确保矩阵严格正定且彻底滤除伪相关白噪音。

### R4. 升级厚尾跳跃扩散（Jump-Diffusion）与分块自助法（Block Bootstrap）压力测试（winrate_engine.py）
- 在 `WinRateEngine.monte_carlo_winrate` 中，废除纯正态独立同分布抽样，改为 70% 历史分块自助抽样（Circular Block Bootstrap, block_size=10，完整保留 A 股真实的波动率聚集与自相关） + 30% Student-t（自由度 $\nu=5$）厚尾白噪音扰动，使蒙特卡洛达标概率与 95% CVaR 尾部底线真实反映 A 股极端行情。

### R5. 同步确认并保护 app_gui.py 的交互收官修复与指标展示
- 保持 Tab 1 步骤一「模式 B：30秒风险承受力测评定档」的 3 道测评问卷分支正常可用。
- 保持 Tab 1 修改参数重新推演步骤二时自动收起旧步骤三（`tab1_step_reached = 2` 并清空 `tab1_step3_cache`），且切换赛道备选基金时同步刷新缓存。
- 在 Tab 2 步骤三保持「🎯 选择调仓目标组合」切换（支持对齐 Tab 1 最新优选组合 vs 核心指数全天候池），并在持仓发生增删改时自动失效 `tab2_diag_cache` 与 `tab2_rebal_cache`。
- 保持 Tab 2 盘中观察期（09:30~14:30）的防冲动执行勾选确认锁正常生效。
- 在顶部看板或步骤二白盒面板中清晰展示实时【市场信噪比 (ER / SNR)】与【动量加速度 (Momentum Accel)】指标。

## Acceptance Criteria

### 算法去噪与自适应变速
- [ ] 实现 `denoise_covariance_matrix`，经 RMT 去噪后相关性矩阵的条件数（Condition Number）显著下降且矩阵严格对称正定。
- [ ] 实现 `compute_market_snr_and_kalman_state`，考夫曼信噪比 $ER_t$ 在单边趋势下自动将动量窗口缩短至近 20 日，在纯白噪音震荡序列下自动拉长窗口至近 60 日。
- [ ] 动量二阶导 $\text{Accel}$ 在快慢动量出现分歧时准确反映加速度衰竭，并在触发衰竭条件时输出预警状态。
- [ ] 蒙特卡洛抽样采用 70% Circular Block Bootstrap (block_size=10) + 30% Student-t ($\nu=5$) 混合抽样，保留波动率聚集特性。

### UI 交互与白盒展示
- [ ] Tab 1 模式 B 的 3 道风险测评问卷分支交互与定档计算完全正常。
- [ ] Tab 1 重算步骤二时步骤三自动折叠收起且清空旧缓存；切换备选基金时缓存同步刷新。
- [ ] Tab 2 调仓目标组合支持在 Tab 1 最新优选组合与核心指数池之间平滑切换，持仓变动时诊断与调仓缓存正确失效。
- [ ] Tab 2 盘中观察期（09:30~14:30）具备防冲动确认勾选机制，未勾选时禁止执行。
- [ ] 顶部看板或步骤二白盒面板实时渲染市场信噪比（ER / SNR）与动量加速度数值。

### 红线守卫与系统验证
- [ ] 只读裁判文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）未被任何改动（MD5/Git 校验一致）。
- [ ] 全量针对性 pytest 测试与 Streamlit AppTest（含 `test_interactive_continuity.py`、`test_ui_and_logic_refinements.py`）0 异常 100% 通过。
- [ ] 8501 端口 Streamlit 服务平滑重启可用。
