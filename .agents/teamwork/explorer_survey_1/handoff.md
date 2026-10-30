# Handoff Report: Explorer 1 Investigation of Strategy Bridge & Regime Modules

## 1. Observation

### 1.1 Project Structure & Read-Only Invariants
通过对 `d:\Google\Workspace\Wind\AGY2_FundAdvisory` 进行目录与代码扫描，观察到以下架构事实：
1. **系统只读裁判基建文件（4个绝对红线文件）**：
   - `judge_engine.py` (42,175 字节)：实现 AST 语法树无年份硬编码扫描 (`compute_ast_hash`)、因果探针 (`probe_look_ahead_bias`)、6 大风格切片回归与参数高原存活检验。只读且严禁修改。
   - `holdout_vault.py` (5,685 字节)：管理 2025-07-01 至今的盲测隔离切片，硬性熔断锁最多调用 3 次 (`HoldoutVaultExhaustedError`)。只读且严禁修改。
   - `AGENT_SPEC.md` (8,237 字节)：规定 No Look-Ahead Bias、50/50 股债基准、6 风格切片定义、四大正交进化流派与硬红线。只读且严禁修改。
   - `tests/test_infra.py` (10,524 字节)：裁判基建专用回归测试集。只读且严禁修改。
   - 在 `tests/test_acceptance_r1_r7.py` (第 424-450 行) 中存在针对上述 4 个文件的严格完整性断言：`test_readonly_invariants_strictly_unmodified`。

### 1.2 既有模型与正交流派现状
1. **正交子岛分布 (`islands/`)**：
   - `islands/island_erp.py` (4,985 字节)：宏观股债性价比。基于历史 350 日 $H00300 / H11009$ 比价分位数计算 ERP 代理值；极低估值区超配高弹性科创50，高估值区超配纯债与黄金。
   - `islands/island_momentum.py` (5,151 字节)：A 股风格截面动量。基于 50 日风格动量比拼科创50与中证红利，在顺势期重配科创50与成长宽基。
   - `islands/island_breadth.py` (4,880 字节)：市场宽度与均线偏离度。利用 $Bias = (c300 - MA60)/MA60$ 探测极端超买超卖，深度超卖（$Bias < -5.0\%$）逆向吸筹，极端超买（$Bias > 8.0\%$）止盈至纯债与红利。
   - `islands/island_ensemble.py` (7,307 字节)：Trial 29 正交集成策略。由 4 大硬编码布尔条件切换 4 组离散静态权重（成长主升浪、结构牛市、极端大熊市、常态稳健高股息）。
2. **流动性与衍生品数据现状 (`strategy_bridge.py`)**：
   - `_refresh_liquidity_thermometer` (行 1648-1741)：收集 DR007 (1.389%)、7D 逆回购政策利率 (1.50%)、DR007 息差 bp、公开市场净投放等。
   - `_refresh_derivatives_data` (行 1744-1887)：收集股指期货 IC/IM/IF/IH 年化贴水率与期权 IV（50ETF IV、科创50 IV、IVIX 指数）。
   - **现有缺陷**：目前流动性与衍生品数据仅作为辅助展示字段注入快照字典，尚未抽象为独立输出组合权重的第 4 个量化专家流派，缺少在线权重动态自更新机制。

### 1.3 状态机判定、MA20 计算与锯齿打脸现象
1. **状态机与 MA20 现行实现**：
   - 文件：`strategy_bridge.py`
   - MA20 计算位置：第 1917 行 `m20 = float(c300_series.tail(20).mean())`
   - 偏离度计算位置：第 1944 行 `bias_20 = float((c300 / m20 - 1.0) * 100.0)`
   - 突破距离计算位置：第 1949-1956 行：
     ```python
     if c300 < m20:
         dist_to_m20_breakout = float((m20 / c300 - 1.0) * 100.0)
         m20_status_desc = f"承压于 MA20 之下 ({bias_20:.2f}%)，距突破触发进攻还差 +{dist_to_m20_breakout:.2f}%"
     else:
         dist_to_m20_breakout = float((c300 / m20 - 1.0) * 100.0)
         m20_status_desc = f"站上 MA20 生命线 (+{dist_to_m20_breakout:.2f}%)，处于多头趋势保护"
     ```
   - 状态转移判定位置：第 2067-2103 行与第 2333-2348 行：
     ```python
     cond_trend = (c300_e > m20_e) and (c300_e > m60_e) and ...
     cond_breakout = (c300_e > m20_e) and (c300_e > m60_e) and (mom20_300_e > 6.0)
     is_growth_lead = cond_trend or cond_breakout or cond_super
     ```
2. **深层问题定位**：
   - 突破与退出门槛为单一刀锋硬阈值（0.0%）。指数在 MA20 附近哪怕出现 $+0.05\%$ 与 $-0.05\%$ 的微幅波动，状态机都会在 `GROWTH_BULL` 与 `STABLE_DIVIDEND` 之间频繁翻转（Whipsaw）。
   - 每次翻转触发大额资产配置阶跃式跳变（如科创50从 0% 暴增至 44%），不仅产生频繁换手与滑点，还极易在场外基金触发未满 7 天的 1.50% 惩罚性赎回费。

### 1.4 资产与基金映射
1. `INDEX_TO_FUND_MAP` (行 57-131)：理论指数至公募基金映射：
   - 常驻底仓映射 A 类：`H00922` -> `100032` (富国红利增强A), `H30269` -> `005561` (创金合信红利低波A), `AU9999` -> `000216` (华安黄金A), `H11009` -> `002351` (易方达纯债A), `SPX_CNY` -> `050025` (博时标普500A)。
   - 波段进攻仓强制映射 C 类（0申购费+满30天0赎回费）：`STAR50_STITCH` -> `011613` (华夏科创50C), `H00852` -> `016634` (富国中证1000C), `H00905` -> `001053` (华夏中证500C), `H00300` -> `007339` (易方达沪深300C)。
2. `StrategyBridge.map_index_weights_to_funds` (行 2369-2391)：执行从指数权重到基金代码权重的映射。
3. `SECTOR_FUND_SELECTION_BY_TIER` (行 290-795)：定义 C1~C5 每一档各赛道的冠军基金标的及备选标的。

---

## 2. Logic Chain

### 2.1 R2 在线多专家乘性权重自更新算法 (`OnlineExpertWeightUpdater`) 演绎链
1. **输入与流派正交化**：
   系统需管理 $K=4$ 个独立正交流派输出的目标权重 $\mathbf{w}_{i, t}$：
   - Expert 1 (`trend_momentum`): 顺应截面趋势，主升浪偏向科创50与中盘小盘；
   - Expert 2 (`erp_macro`): 锚定宏观股债利差，极度低估时逆向增配权益，高估时撤回纯债；
   - Expert 3 (`ma_contrarian`): 跟踪 MA60/120 均线偏离，负偏离超卖时吸筹，正偏离超买时兑现；
   - Expert 4 (`liquidity_basis`): 监控资金面 DR007 息差与期指基差/期权 IV，流动性宽松且基差收敛时进攻，流动性骤紧或极端贴水/波动率飙升时避险。
2. **净效用评估 $u_{i, t}$**：
   在历史截面 $t \le T$ 滚动窗口内，每个专家组合在 $t$ 日产生真实组合收益 $r_{i, t} = \mathbf{w}_{i, t-1}^\top \mathbf{R}_t$、滚动方差 $\sigma_{i, t}^2$ 与双边换手率 $\text{Turnover}_{i, t} = \sum_m |w_{i, t}^m - w_{i, t-1}^m|$。
   根据公式：
   $$u_{i, t} = r_{i, t} - 0.5 \lambda \sigma_{i, t}^2 - c \cdot \text{Turnover}_{i, t}$$
   频繁打脸、换手率高或回撤大的流派，其净效用 $u_{i, t}$ 将被惩罚为负数。
3. **指数衰减与乘性更新**：
   按 Exponentially Weighted Average Forecaster 公式更新权重：
   $$P_{i, t+1} = \frac{P_{i, t}^\gamma \cdot \exp(\eta \cdot u_{i, t})}{\sum_{j=1}^K P_{j, t}^\gamma \cdot \exp(\eta \cdot u_{j, t})}$$
   其中 $\gamma = 0.985$ 使得旧表现指数级衰减，$\eta$ 为学习率（建议 $\eta \in [5, 15]$）。
   实时截面 $T$ 输出的 $P_{i, T}$ 保证 $\sum_{i=1}^4 P_{i, T} = 1.0$。
4. **合成目标权重与白盒透传**：
   最终自适应配置由 4 大专家实时加权：$\mathbf{W}_T = \sum_{i=1}^4 P_{i, T} \mathbf{w}_{i, T}$。
   同时将 $P_{i, T}$ 透明注入 `snapshot["expert_weights"]` 与 `snapshot["expert_details"]`，供前端步骤二卡片渲染。

### 2.2 R3 施密特迟滞缓冲环与 Sigmoid 连续仓位门控演绎链
1. **迟滞死区阻断微幅震荡打脸**：
   在现价偏离 MA20 的区间设置非对称迟滞带：
   - 进攻触发上轨：指数有效突破 MA20 达 $+1.2\%$（或综合得分 $Z_t \ge +0.60$）；
   - 防守退出下轨：指数有效跌破 MA20 达 $-1.5\%$（或综合得分 $Z_t < +0.20$）；
   - 死区锁定：当指数在 $[-1.5\%, +1.2\%]$ 震荡带内，**强制锁定保持前一交易日的既有状态**，禁止触发状态翻转。
2. **Sigmoid 仓位连续门控消除阶跃冲击**：
   通过综合因子（趋势斜率、科创-红利动量差、ERP 分位数、期权 IV）归一化合成连续得分 $Z_t \in [-2, 2]$。
   利用 Sigmoid 门控算子：
   $$g(Z_t) = \frac{1}{1 + \exp(-k \cdot Z_t)}$$
   使进攻资产权重在 $w_{min}$ 与 $w_{max}$ 之间平滑过渡，彻底杜绝单日跳跃 40%+ 的极端阶跃式调仓。
3. **双向变盘触发线精确定位**：
   在 UI 顶部卡片输出明确数值：
   - 向上突破进攻线：$\text{Line}_{up} = \text{MA20} \times (1 + 0.012)$，严格高于现价（未进攻时）；
   - 向下跌破防守线：$\text{Line}_{down} = \text{MA20} \times (1 - 0.015)$，严格低于现价（进攻态时）。

---

## 3. Caveats

1. **历史截面无未来函数约束**：
   在计算滚动效用与更新 $P_{i, T}$ 时，必须严格截断至 $t \le T$，严禁使用全样本未来均值或全局极值做标准化（符合 `judge_engine.py` 检验A 因果探针红线）。
2. **日历年份硬编码禁令**：
   代码中严禁出现 `'2018'`, `'2019'`, `'YYYY-MM-DD'` 等日历字符串，所有回看天数必须采用基于交易日序的动态内生窗口（符合检验A+ AST 反作弊锁）。
3. **计算性能考量**：
   若逐日重新推演全部历史切片的 $K=4$ 专家回测，可能引起首次页面加载耗时较长。建议在 `OnlineExpertWeightUpdater` 中采用窗口增量缓存或仅在近 60~120 个交易日的活跃切片内滚动更新。
4. **4 个基建文件零修改红线**：
   `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py` 必须保持字节级不变。

---

## 4. Conclusion & Precise Code Insertion Blueprint

### 4.1 代码结构与插入点设计

```
strategy_bridge.py
├── [行 904-924] TierWeightsDict
├── [🌟 新增插入点 A - 行 925 前]:
│   ├── class OnlineExpertWeightUpdater
│   │   ├── compute_expert_weights(history_df, window_days=60, eta=10.0, gamma=0.985, ...) -> Dict[str, Any]
│   │   ├── get_orthogonal_expert_streams(history_df) -> Dict[str, Dict[str, float]]
│   │   └── blend_expert_weights(expert_weights, expert_portfolios) -> Dict[str, float]
│   │
│   └── class SchmidtHysteresisBuffer
│       ├── compute_composite_z(trend_slope, diff_star_div, erp_percentile, option_iv) -> float
│       ├── evaluate_state_transition(current_bias_20, composite_z, prev_state_is_attack) -> Tuple[bool, str]
│       ├── compute_sigmoid_gating(z_score, k=3.0) -> float
│       └── get_hysteresis_trigger_lines(m20_price) -> Dict[str, float]
│
├── [行 925-1046] strategy_fn_for_tier:
│   └── 融合 Sigmoid 门控 g(Z_t) 与施密特状态过滤
│
├── [行 1339] class StrategyBridge:
│   ├── 静态类属性 _expert_updater = None, _schmidt_buffer = None
│   ├── get_online_expert_weights() 类方法暴露
│   │
│   ├── [行 1948-1956] get_latest_market_snapshot:
│   │   └── 接入 get_hysteresis_trigger_lines，生成符合 R7 规范的双向变盘触发线
│   │
│   ├── [行 2067-2103] get_latest_market_snapshot (状态机判定):
│   │   └── 接入 SchmidtHysteresisBuffer.evaluate_state_transition
│   │       在 [-1.5%, +1.2%] 死区内锁定原有状态
│   │
│   ├── [行 2205-2215] get_latest_market_snapshot (快照字典组装):
│   │   └── 注入 expert_weights, expert_details, trigger_lines, sigmoid_gate
│   │
│   └── [行 2282-2350] _calculate_state_streak:
│       └── 采用施密特迟滞过滤时序计算持续天数，保证状态连续性
```

### 4.2 详细接口与签名规范

#### 1. `OnlineExpertWeightUpdater` 规范接口
```python
class OnlineExpertWeightUpdater:
    def __init__(self, gamma: float = 0.985, eta: float = 10.0, risk_lambda: float = 1.0, cost_c: float = 0.0015):
        self.gamma = gamma
        self.eta = eta
        self.risk_lambda = risk_lambda
        self.cost_c = cost_c

    def get_orthogonal_expert_streams(self, history_df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """
        获取当前截面四大正交分析流派独立输出的目标资产权重字典：
        - 'trend_momentum': 趋势动量专家 (islands.island_momentum)
        - 'erp_macro': ERP宏观估值专家 (islands.island_erp)
        - 'ma_contrarian': 均线乖离逆向专家 (islands.island_breadth)
        - 'liquidity_basis': 流动性与期指基差专家 (结合 DR007 与股指贴水)
        """
        ...

    def compute_expert_weights(
        self,
        history_df: pd.DataFrame,
        window_days: int = 60
    ) -> Dict[str, Any]:
        """
        执行 Hedge 乘性权重更新，返回：
        {
            "weights": {"trend_momentum": P1, "erp_macro": P2, "ma_contrarian": P3, "liquidity_basis": P4},
            "sum_weights": 1.0,
            "blended_target_weights": {"STAR50_STITCH": ..., "H00922": ..., ...},
            "details": {...}
        }
        """
        ...
```

#### 2. `SchmidtHysteresisBuffer` 规范接口
```python
class SchmidtHysteresisBuffer:
    def __init__(self, upper_threshold: float = 1.2, lower_threshold: float = -1.5, z_upper: float = 0.60, z_lower: float = 0.20):
        self.upper_threshold = upper_threshold  # +1.2%
        self.lower_threshold = lower_threshold  # -1.5%
        self.z_upper = z_upper                  # +0.60
        self.z_lower = z_lower                  # +0.20

    def evaluate_state_transition(
        self,
        bias_20: float,
        composite_z: float,
        is_currently_attack: bool
    ) -> Tuple[bool, str]:
        """
        根据双阈值迟滞环判定状态转移：
        - 非进攻态 -> 必须 bias_20 >= +1.2% 或 composite_z >= 0.60 才进入进攻态
        - 进攻态 -> 必须 bias_20 <= -1.5% 或 composite_z < 0.20 才退出进攻态
        - 中间 [-1.5%, +1.2%] 死区：保持 is_currently_attack 原状不变
        返回: (new_is_attack, transition_reason)
        """
        ...

    @staticmethod
    def compute_sigmoid_gating(z_score: float, k: float = 3.0) -> float:
        """g(Z_t) = 1 / (1 + exp(-k * Z_t))"""
        ...
```

---

## 5. Verification Method

后续实施阶段可通过以下自动化测试独立验证：

1. **R2 在线多专家权重更新单测**：
   - 编写 `tests/test_expert_weight_updater.py`：
     - 测试 1：验证在全历史切片下 `updater.compute_expert_weights(df)["weights"]` 四大专家权重和严格等于 `1.0`（允许误差 `1e-5`）。
     - 测试 2：在科技成长主升行情切片（Slice 2 / Slice 6），断言 `trend_momentum` 权重显著高于平均值；在震荡下跌或高估值切片，断言 `erp_macro` 或 `ma_contrarian` 权重获得自适应提升。
     - 测试 3：单期权重更新符合乘性更新数学公式，验证衰减半衰期 $\gamma=0.985$ 与换手惩罚项生效。
2. **R3 施密特迟滞环与防打脸单测**：
   - 编写 `tests/test_schmidt_hysteresis.py`：
     - 测试 1：构造沪深300 在 MA20 附近 $\pm 0.5\%$ 微幅震荡序列（如连续 10 天交替 $+0.3\%, -0.4\%, +0.5\%, -0.3\%$），断言状态机保持锁定，换手率降为 0，不触发频繁满仓/清仓横跳。
     - 测试 2：验证从非进攻态必须超过 $+1.2\%$（或 $Z_t \ge 0.60$）才能转为进攻态；从进攻态必须跌破 $-1.5\%$（或 $Z_t < 0.20$）才退出进攻态。
     - 测试 3：测试 Sigmoid 门控 $g(Z_t)$ 输出在 $(0, 1)$ 之间单调平滑连续，无突变跳跃。
     - 测试 4：断言变盘触发线计算正确：向上进攻线严格高于现价，向下防守线严格低于现价。
3. **裁判基建完整性与全量回归**：
   - 执行命令：`pytest tests/`
   - 实测基线数据：全量 246 项测试（涵盖 `test_acceptance_r1_r7.py`, `test_infra.py`, `test_strategy_bridge.py`, `test_adversarial_*.py` 等 17 个测试集）**100% 全部通过 (246 passed, 0 failed, 耗时 408.85s)**。
   - 断言 4 个裁判文件未受任何改动，因果探针零报警，Streamlit 端到端渲染及所有量化计算均处于健康受控状态。
