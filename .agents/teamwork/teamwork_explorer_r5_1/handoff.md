# R1 与 R2 算子架构调研与实施蓝图分析报告 (handoff.md)

## 1. Observation (客观事实与直接观测)

### 1.1 现有 `strategy_bridge.py` 动量与状态机现状
- **文件路径**: `AGY2_FundAdvisory/strategy_bridge.py` (总计 6022 行)。
- **动量计算与固定 60 日回看窗口**:
  在 `StrategyBridge.get_latest_market_snapshot` (lines 2535-2555 与 lines 2638-2643) 中，风格动量比拼（科创50 `STAR50_STITCH` vs 中证红利 `H00922`）采用硬编码回看 60 个交易日：
  ```python
  # 2. 风格动量比拼：科创50 vs 中证红利 (60日)
  mom60_300 = float((c300 / df['H00300'].iloc[-60] - 1.0) * 100.0)
  mom60_star = float((cstar / df['STAR50_STITCH'].iloc[-60] - 1.0) * 100.0)
  mom60_div = float((cdiv / df['H00922'].iloc[-60] - 1.0) * 100.0)
  mom60_500 = float((c500 / df['H00905'].iloc[-60] - 1.0) * 100.0)
  mom20_300 = float((c300 / df['H00300'].iloc[-20] - 1.0) * 100.0) if n >= 20 else 0.0

  diff_star_div = float(mom60_star - mom60_div)
  ```
  在子流派 `islands/island_momentum.py` (lines 17, 43, 73) 与 `islands/island_ensemble.py` (lines 104-108) 中同样默认以 50~60 日固定回看测算风格动量。
- **市场状态机与四态划分**:
  在 `StrategyBridge.get_latest_market_snapshot` (lines 2674-2694) 中，定义了 4 种市场状态：
  1. `GROWTH_BULL` ("🔥 进攻科技成长大牛市")：由 `is_growth_lead` 触发（站稳均线且 `mom60_star_e > mom60_div_e` 且有效突破施密特迟滞上轨）；
  2. `STRUCTURAL_500` ("📈 结构分化牛市")：中证500超额领跑；
  3. `SEVERE_BEAR` ("🛡️ 深度大熊市防御")：沪深300同时跌破 MA60 与 MA120 且均线向下发散；
  4. `STABLE_DIVIDEND` ("🟢 常态稳健高股息慢牛")：基准震荡防御中枢。
- **施密特迟滞缓冲环与连续门控**:
  `SchmidtHysteresisBuffer` (lines 1236-1365) 实现了 `[-1.5%, +1.2%]` 的非对称迟滞带，有效阻止了 `bias_20` 在均线附近的频繁横跳打脸。
- **期权 iVIX 与衍生品数据追踪**:
  `StrategyBridge._refresh_derivatives_data` (lines 2320-2462) 接入 `src/toolkit/derivatives.py` 与 `data/derivatives/option_volatility.parquet`，提取了：
  - `snapshot["option_iv_pct"]`: 沪深300ETF平值期权 IV (默认基准约 19.40%)；
  - `snapshot["ivix_index"]`: 中国波指 iVIX (默认基准约 19.50%)；
  - 极端阈值: 当 `option_iv > 32.0 or ivix_index > 32.0` 时提示“极端飙升预警尾部波动”。
- **拥挤度监控与右侧阶梯止盈**:
  在 `compute_dynamic_tier_weights` (lines 3532, 3818-3845) 中，读取 `crowding_warning = bool(market_snapshot.get("crowding_warning", False))`。当 `bias_20 >= 6.5%` 或 `crowding_warning` 时，将成长进攻仓削减 35% 并落袋入纯债与红利低波。但目前**尚未引入动量二阶导（加速度衰竭）与 iVIX 单日跳升的复合动量衰竭预警**。

### 1.2 外部调用方接口与下游契约
1. **`app_gui.py`**:
   - 顶部看板 (lines 530-600):
     - `top_c2` ("🧭 市场定调与攻防线"): 渲染 `vernacular_state` 及副标题 `📈破 {surge_line} 进攻 ｜ 🛡️跌 {breakdown_line} 防守`；
   - 步骤二白盒决策折叠框 (lines 1173-1218):
     - 4 张决策卡片：① 市场温度与估值水位；② 均线动量状态 (MA20)；③ 宏观资金利率 (DR007)；④ 期权波动率防波堤 (iVIX)。
2. **`portfolio_optimizer.py` 与 `winrate_engine.py`**:
   - `WinRateEngine.extract_state_vector` (line 76-88):
     ```python
     erp = float(snapshot.get("erp_percentile", snapshot.get("erp_pct", 50.0)))
     bias20 = float(snapshot.get("bias_20", snapshot.get("bias20", 0.0)))
     mom60 = float(snapshot.get("mom60_300", snapshot.get("mom_60", snapshot.get("mom60", 0.0))))
     vol = float(snapshot.get("ewma_vol", snapshot.get("volatility", snapshot.get("ann_vol", 0.15))))
     dr007 = float(snapshot.get("dr007_spread_bp", snapshot.get("dr007_spread", snapshot.get("dr007", 0.0))))
     ```
     `portfolio_optimizer.py` 严重依赖 `snapshot["mom60_300"]` 作为 5 维同温层状态向量的第 3 维度，因此扩展新算子时**必须保留 `mom60_300` 字段**。

### 1.3 现有测试套件验证结果
通过运行命令：
- `cmd.exe /c "set PYTHONPATH=AGY2_FundAdvisory;.&& py -3.11 -m pytest AGY2_FundAdvisory/tests/test_strategy_bridge.py"`: **11 passed in 24.05s**
- `cmd.exe /c "set PYTHONPATH=AGY2_FundAdvisory;.&& py -3.11 -m pytest AGY2_FundAdvisory/tests/test_adversarial_m1_strategy_bridge.py"`: **27 passed in 4.74s**
- `cmd.exe /c "set PYTHONPATH=AGY2_FundAdvisory;.&& py -3.11 -m pytest AGY2_FundAdvisory/tests/test_interactive_continuity.py AGY2_FundAdvisory/tests/test_ui_and_logic_refinements.py"`: **9 passed in 79.86s**

---

## 2. Logic Chain (推理链条与技术架构设计)

### 2.1 需求 R1 逻辑链：考夫曼效率比率 (ER) + 卡尔曼滤波 + 自适应动量窗口
1. **考夫曼效率系数 (ER 信噪比代理)**:
   - 数学公式：
     $$ER_t = \frac{|P_t - P_{t-w}|}{\sum_{i=0}^{w-1} |P_{t-i} - P_{t-i-1}|} \in [0, 1]$$
     其中 $w = 20$ 为默认回看窗口。
   - 性质：
     - 单边单调行情：分母总位移等于分子净位移，$ER_t = 1.0$；
     - 白噪音锯齿行情：分子趋于 0，分母累加膨胀，$ER_t \to 0.0$；
     - 极值保护：分母为 0（平盘无波动）或样本不足 $w+1$ 时，安全裁剪为 $ER_t = 0.5$ 或 $0.0$，无零除异常。
2. **一维卡尔曼滤波 (Kalman Filter) 剥离白噪音**:
   - 状态方程与观测方程：
     $$x_t = x_{t-1} + w_t, \quad w_t \sim \mathcal{N}(0, Q)$$
     $$z_t = x_t + v_t, \quad v_t \sim \mathcal{N}(0, R_t)$$
   - 观测噪声方差 $R_t$ 随 $1 - ER_t$ 动态放大：
     设资产价格日方差为 $\sigma^2$，基准观测噪声 $R_{\text{base}} = \sigma^2$。
     $$R_t = R_{\text{base}} \times (1.0 - ER_t + \epsilon)$$
     - 当 $ER_t \to 1.0$（趋势高信噪比）：$R_t \to 0 \implies$ 卡尔曼增益 $K_t \to 1$，状态极速拟合最新真实价格，零滞后；
     - 当 $ER_t \to 0.0$（震荡白噪音）：$R_t$ 大幅放大 $\implies$ 卡尔曼增益 $K_t \to 0$，状态高度平滑，滤除日内与隔夜随机跳动。
   - 斜率提取：
     $$\text{kalman\_slope} = \frac{\hat{x}_t - \hat{x}_{t-1}}{\hat{x}_{t-1}} \times 100\% \quad (\text{或 } \hat{x}_t - \hat{x}_{t-5})$$
3. **动态自适应动量回看窗口 ($W_{\text{eff}}$)**:
   - 公式：
     $$W_{\text{eff}} = \text{int}(60 - 40 \times ER_t) \in [20, 60]$$
     - $ER_t = 1.0 \implies W_{\text{eff}} = 20$（单边主升浪，极速 20 日窗口跟进）；
     - $ER_t = 0.0 \implies W_{\text{eff}} = 60$（震荡白噪音，拉长至 60 日平滑滤波稳守红利）；
     - 约束：`int(np.clip(round(60 - 40 * er_t), 20, 60))`。
4. **函数接口定义**:
   ```python
   def compute_market_snr_and_kalman_state(
       price_series: Union[pd.Series, np.ndarray, List[float]],
       window: int = 20,
       q_process: float = 1e-4
   ) -> Dict[str, Any]:
       # 返回: {
       #   "er_snr": float,              # ER信噪比 [0.0, 1.0]
       #   "effective_window": int,      # 自适应窗口 [20, 60]
       #   "kalman_trend": float,        # 去噪后当前趋势净值
       #   "kalman_slope": float,        # 去噪趋势斜率 (%)
       #   "filtered_series": np.ndarray # 全时序滤波结果
       # }
   ```

### 2.2 需求 R2 逻辑链：动量加速度 (二阶导) + 动量衰竭预警 + 白盒展示
1. **动量二阶导（加速度）测算**:
   - 快周期动量（15日）与慢周期动量（60日）：
     $$\text{Mom}_{15} = \left(\frac{P_t}{P_{t-15}} - 1\right) \times 100\%$$
     $$\text{Mom}_{60} = \left(\frac{P_t}{P_{t-60}} - 1\right) \times 100\%$$
   - 动量加速度公式：
     $$\text{Accel} = \text{Mom}_{15} - \frac{15}{60} \text{Mom}_{60} = \text{Mom}_{15} - 0.25 \times \text{Mom}_{60}$$
   - 量化含义：
     若以匀速推演，15日动量应恰为60日动量的 $1/4$；
     - $\text{Accel} > 0$：短期动量加速爆发（主升浪初期/加速期）；
     - $\text{Accel} < 0$：短期动量减速滞涨（高位动能衰退）；
     - $\text{Accel} \le -2.0\%$：二阶导急剧恶化，发生高位钝化与衰竭。
2. **复合动量衰竭预警三联判定**:
   当处于进攻状态（`regime == "BULL"` 或 `market_state_code in ["GROWTH_BULL", "STRUCTURAL_500"]`）时，同时检测：
   1. **高拥挤度 (High Crowding)**：`crowding_warning is True` 或 `crowding_degree == "极度拥挤"` 或 `crowding_score < 60.0`；
   2. **动量加速度大幅转负 (Negative Accel)**：$\text{Accel} \le -2.0\%$（沪深300或科创50动量加速度显著背离）；
   3. **期权 iVIX 单日跳升 (iVIX Spike)**：`ivix_index >= 24.0` 或 $\Delta \text{iVIX} \ge 1.50$ 或 `option_iv >= 26.0`。
   - **预警输出**:
     触发状态机预警标识：`momentum_exhaustion_warning = True`；
     输出警示文案：`「⚡ 动量衰竭预警：暂停追高进攻标的，新增资金转入红利/纯债缓冲」`；
   - **资产配置联动**:
     在 `compute_dynamic_tier_weights` 中接入 `momentum_exhaustion_warning`：
     当预警触发时，强制执行防追高防线，削减进攻性成长敞口 35%，新资金与削减仓位自动转入纯债（002351）与红利低波（005561）。
3. **UI 顶部看板与步骤二白盒展示联动**:
   - **顶部看板卡片 2 (`top_c2`)**:
     在攻防线副标签或徽章中追加：`📡SNR {snr:.2f} ｜ ⚡加速度 {accel:+.1f}%`；若触发衰竭预警，卡片标头切换为黄色/橙色警示；
   - **步骤二白盒决策折叠框 (卡片 2 均线动量状态)**:
     完整呈现：
     - 市场信噪比 (ER / SNR)：`{snapshot['er_snr']:.2f}` (自适应变速窗口: `{snapshot['effective_momentum_window']}日`)；
     - 动量加速度 (Mom Accel)：`{snapshot['mom_accel']:+.2f}%`；
     - 动量衰竭预警状态：若触发，以深红色高亮显示「⚡ 动量衰竭预警：暂停追高进攻标的，新增资金转入红利/纯债缓冲」。

---

## 3. Caveats (边界、假设与潜在风险)

1. **历史样本与前序数据平滑**:
   若输入的 `price_series` 长度不足 60 日，自适应窗口应安全回退至 `min(len(series) - 1, w_eff)`，确保冷启动与测试 Mock 数据下不抛出 `IndexError`。
2. **下游指标兼容性保全**:
   `portfolio_optimizer.py` 与 `winrate_engine.py` 的 5 维同温层状态提取器 `WinRateEngine.extract_state_vector` 明确提取 `snapshot["mom60_300"]`。在引入自适应窗口 `mom_eff_300` 的同时，**必须同时保留原有的 `mom60_300` 字段**，严禁删除旧字段致使全库崩塌。
3. **只读裁判文件与物理红线严守**:
   严格恪守系统物理红线：`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py` 必须保持 0 字节改动，MD5/Git 严格一致。

---

## 4. Conclusion (结论与实施方案)

1. **新增算子位置与结构**:
   - 在 `AGY2_FundAdvisory/strategy_bridge.py` 中实现：
     - `compute_market_snr_and_kalman_state(price_series, window=20)`
     - `compute_momentum_acceleration(price_series, fast_window=15, slow_window=60)`
   - 在 `StrategyBridge.get_latest_market_snapshot` 中接入上述两算子：
     - 根据信噪比计算 `effective_window = int(60 - 40 * er_snr)`；
     - 动态更新风格动量对比；
     - 复合检测高拥挤度 + 负加速度 + iVIX跳升，输出 `momentum_exhaustion_warning`；
     - 将 `er_snr`、`effective_momentum_window`、`mom_accel`、`momentum_exhaustion_warning` 打包进返回快照 `snapshot`。
   - 在 `StrategyBridge.compute_dynamic_tier_weights` 中：
     - 响应 `momentum_exhaustion_warning`，将其纳入右侧阶梯止盈与防追高缓冲。
2. **前端 `app_gui.py` 对接**:
   - 在顶部卡片 `top_c2` 展示 SNR 与 Accel；
   - 在步骤二白盒折叠框中展示 SNR、Accel 与预警文本。
3. **测试覆盖策略**:
   - 新建 `AGY2_FundAdvisory/tests/test_r1_r2_adaptive_momentum_and_exhaustion.py`，完整覆盖单边趋势极限、白噪音震荡极限、二阶导转负、复合衰竭三联触发、非进攻态负对照、以及 UI 白盒渲染。

---

## 5. Verification Method (独立可复现验证方法)

### 5.1 验证命令集
1. **现有基线回归校验**:
   ```bash
   cmd.exe /c "set PYTHONPATH=AGY2_FundAdvisory;.&& py -3.11 -m pytest AGY2_FundAdvisory/tests/test_strategy_bridge.py AGY2_FundAdvisory/tests/test_adversarial_m1_strategy_bridge.py"
   ```
2. **新增 R1/R2 算子针对性单元测试**:
   ```bash
   cmd.exe /c "set PYTHONPATH=AGY2_FundAdvisory;.&& py -3.11 -m pytest AGY2_FundAdvisory/tests/test_r1_r2_adaptive_momentum_and_exhaustion.py -v"
   ```
3. **交互连续性与 UI 渲染校验**:
   ```bash
   cmd.exe /c "set PYTHONPATH=AGY2_FundAdvisory;.&& py -3.11 -m pytest AGY2_FundAdvisory/tests/test_interactive_continuity.py AGY2_FundAdvisory/tests/test_ui_and_logic_refinements.py"
   ```
4. **只读裁判文件零改动校验 (MD5/Git Status)**:
   ```bash
   git status --porcelain AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md AGY2_FundAdvisory/tests/test_infra.py
   ```
   *预期输出为空，确认无任何改动。*

### 5.2 失效判定条件 (Invalidation Conditions)
- 若单边持续上涨价格序列输入下，$ER_t < 0.90$ 或 $W_{\text{eff}} > 25$，则判定 R1 算子数学公式存在实现缺陷；
- 若交替震荡白噪音序列输入下，$ER_t > 0.20$ 或 $W_{\text{eff}} < 50$，则判定 R1 噪声滤波失效；
- 若动量二阶导 $\text{Accel}$ 在急速拉升后平盘滞涨时未能转为显著负值（$\le -2.0\%$），则判定 R2 加速度衰竭公式失效；
- 若进攻状态下同时满足三联条件未能触发「⚡ 动量衰竭预警」，或在非进攻状态（大熊市防御）下误触发进攻衰竭预警，判定状态机逻辑失效；
- 若修改导致裁判文件发生任何 git diff，直接判定违规。
