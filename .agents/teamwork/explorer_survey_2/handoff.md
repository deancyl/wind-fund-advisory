# Explorer 2 深度调研与架构交接报告 (R4 & R5 动态风险预算与在途摩擦拦截)

## 摘要 (Executive Summary)
本报告针对 AGY2_FundAdvisory 量化投顾自进化引擎中的 **R4（滚动 EWMA 波动率倒数与动态风险预算配权）** 与 **R5（调仓净效用拦截器与真实 A/C 阶梯费率及 T+2 在途踏空折价）** 展开了深度只读调研。全面勘测了 `data_loader.py`、`strategy_bridge.py`、`portfolio_manager.py` 与 `trading_clock_fee.py` 的现有类结构、函数签名、数据依赖、硬性裁判红线与测试断言，给出了高精度的代码植入点、数学公式与伪代码设计，为后续 Agent-2 的实施提供自包含、零歧义的落地蓝图。

---

## 1. 观察 (Observation)

### 1.1 系统只读裁判基建文件核验 (Strict Read-Only Invariants)
严格核验以下 4 个基建文件，确认其物理完整性并严格维持只读，严禁任何侵入与篡改：
1. **`AGY2_FundAdvisory/judge_engine.py`** (42,175 字节)：
   - 核心类：`JudgeEngine`，关键函数 `compute_ast_hash`、`probe_look_ahead_bias`、`run_judge`。
   - 包含 AST 日历年份静态反作弊扫描、因果探针（历史截面 $T$ 与 $T+20$ 浮点误差 $\le 10^{-7}$）、6 大风格切片全量回归、参数高原存活检验与 DSR 试错惩罚。
2. **`AGY2_FundAdvisory/holdout_vault.py`** (5,685 字节)：
   - 核心类：`HoldoutVault`，异常类 `HoldoutVaultExhaustedError`。
   - 锁死 2025-07-01 至今盲测切片，硬性上限最多测试 3 次。
3. **`AGY2_FundAdvisory/AGENT_SPEC.md`** (8,237 字节)：
   - 约束：统一对标 50/50 本土股债基准；非 A 股外援（黄金+美股）$\le 20\%$；A 股本土权益 $\ge 55\%$；扣除 $Rf = 2.0\%$；纯债仓位 $\le 50\%$；CAGR $\ge 11.5\%$；MaxDD $\le 15.5\%$；Slice 2 累计 $\ge +38\%$，Slice 6 累计 $\ge +18\%$。
4. **`AGY2_FundAdvisory/tests/test_infra.py`** (10,524 字节，264 行)：
   - 15 项裁判基建测试（已实测验证 100% 通过，耗时 5.86s）。

### 1.2 `data_loader.py` 代码与数据接口现况
- **文件路径**：`d:\Google\Workspace\Wind\AGY2_FundAdvisory\data_loader.py` (536 行)
- **核心类与接口**：
  - `DataLoader` 类（第 47~536 行）
  - `load_total_return_matrix(start_date="2018-01-01", end_date=None, force_rebuild=False)` (第 68~106 行)：从本地 Parquet 缓存 `aligned_matrix_total_return.parquet` 快速读取标准化对齐矩阵，包含全量对齐列：`['date', 'H00300', 'H00905', 'H00852', 'H00922', 'H30269', '930609', 'H11009', 'STAR50_STITCH', 'AU9999', 'SPX_CNY', 'BENCHMARK_30_70', 'BENCHMARK_50_50']`。
  - `simulate_execution(weights_df, prices_df, is_otc=True, penalty_days=7, penalty_rate=0.015, etf_impact=0.001)` (第 436~536 行)：T+1 确认模拟、买入未满 7 天赎回 1.50% 扣费及 ETF 冲击成本计算。
- **现状缺陷与 R4 缺口**：
  - `DataLoader` 当前**完全缺失**滚动 60 日指数加权移动平均（EWMA）年化波动率 $\sigma_{k, t}$ 与相关性矩阵计算工具方法，导致上层动态风控无法基于最新截面实时感知资产波动率放大。

### 1.3 `strategy_bridge.py` 动态风险预算现况与断言约束
- **文件路径**：`d:\Google\Workspace\Wind\AGY2_FundAdvisory\strategy_bridge.py` (4,084 行)
- **核心方法**：
  - `compute_dynamic_tier_weights(cls, history_df=None, tier="C3", market_snapshot=None, **kwargs)` (第 2823~3058 行)：
    - 当前签名支持入参多态互换：`(history_df, tier, market_snapshot)` 或 `(tier=..., market_snapshot=...)`，非法档位默认回退至 `"C3"`。
    - 状态机识别：根据 `market_snapshot` 中的 `market_state_code` 或均线形态分为 `"BULL"`, `"BEAR"`, `"OSCILLATING"`。
    - 当前配权实现：通过硬编码的 3 张静态字典表 `bull_weights[tier]`, `bear_weights[tier]`, `oscillating_weights[tier]` 进行映射。
- **档位风险预算配置 (`RISK_TIERS_CONFIG`, 第 135~228 行)**：
  | 档位 | 目标 CAGR | 最大回撤上限 (MaxDD) | 权益仓位区间 | 核心防御底线 |
  | :---: | :---: | :---: | :---: | :--- |
  | **C1** | 5% ~ 8% | 5.0% | 15% ~ 20% | 纯债 65%~75% + 黄金 10%~15% + 红利低波 15%~20% |
  | **C2** | 8% ~ 12% | 10.0% | 30% ~ 40% | 纯债 45%~50% + 黄金 10% + 红利低波 25%~30% |
  | **C3** | 12% ~ 18% | 15.0% | 50% ~ 78% | 高股息红利 38%~68% + 科技成长 44% + 纯债黄金防守 |
  | **C4** | 18% ~ 30% | 25.0% | 75% ~ 85% | 科技小盘成长 65%~75% + 红利底仓 20% + 适度黄金纯债 |
  | **C5** | 30% ~ 100%+ | 40.0% | 85% ~ 95% | 极限高 Beta 权益 85%~95% (科创50 + 中证1000 + 中证500) |
- **Challenger-1 压测刚性断言 (`test_stress_quant_model_challenger.py`)**：
  1. **全域单调性恒成立**：
     $$\text{Equity}(C1) < \text{Equity}(C2) < \text{Equity}(C3) < \text{Equity}(C4) < \text{Equity}(C5)$$
     $$\text{Defensive}(C1) > \text{Defensive}(C2) > \text{Defensive}(C3) > \text{Defensive}(C4) > \text{Defensive}(C5)$$
  2. **深度熊市破位态算法止损硬红线**：
     $$\text{Equity}(C4) \le 55\%, \quad \text{Defensive}(C4) \ge 45\%$$
     $$\text{Equity}(C5) \le 70\%, \quad \text{Defensive}(C5) \ge 30\%$$
  3. **权重纯洁性**：所有权重之和必须严格为 1.0000 (容差 $10^{-4}$)，无 NaN，无负数。

### 1.4 `portfolio_manager.py` 与 `trading_clock_fee.py` 费率、调仓与在途摩擦现况
- **费率精算引擎 (`trading_clock_fee.py:FeeMatrixCalculator`)**：
  - A 类阶梯赎回费 (`A_REDEMPTION_TIERS`)：
    `[0~6d: 1.50%, 7~29d: 0.75%, 30~179d: 0.50%, 180~364d: 0.25%, >=365d: 0.00%]`
  - C 类阶梯赎回费 (`C_REDEMPTION_TIERS`)：
    `[0~6d: 1.50%, 7~29d: 0.50%, >=30d: 0.00%]`
  - 申购费：A 类 0.15% (1折申购)，C 类 0.00%。
  - 调仓过滤：`is_rebalance_actionable` 过滤偏离度 $< 3\%$ 的微调。
- **持仓与批次管理 (`portfolio_manager.py`)**：
  - `get_penalty_free_redeemable_shares(fund_code)` (第 4512 行)：严格按 FIFO 顺序累加 `holding_days >= 7 and not safety_lock` 批次，遇到首个未满 7 天批次即截断返回，安全保护持仓。
  - `execute_fifo_redemption(fund_code, shares_to_sell, force_penalty=False)` (第 4533 行)：严格 FIFO 扣减，未满 7 天且未开启 force 时坚决阻断抛出 `PermissionError`。
  - `generate_rebalance_plan(target_weights, min_buffer_pct=3.0)` (第 4627 行)：
    - 生成卖出与买入指令；
    - 匹配路由优先级：`PRIORITY_1_SWITCH` (同公司转换，T+1)、`PRIORITY_2_CASH_ADVANCE` (现金垫付，T+1)、`PRIORITY_3_TWO_STEP` (两阶段跨公司，T+2/T+3)、`SELL_TO_CASH` (减仓变现，T+2)；
    - **当前缺陷**：未执行预估净效用 $\Delta U$ 拦截计算，未能折算跨公司 2~4 天的在途踏空风险成本 $\text{InTransitOpportunityCost}(\Delta t, \sigma_{index})$，未标记 `"🛡️ 摩擦/在途损耗大于预期收益，建议原地持仓不动"`，且选基漏斗未包含同公司转换便利度加分。

---

## 2. 逻辑链推演 (Logic Chain)

### 2.1 R4 波动率倒数配权与纯债压舱石转移逻辑
1. **输入与观察映射**：根据 1.2 与 1.3，底层基金均可映射至全收益指数代理序列（`002351->H11009`, `005561->H30269`, `100032->H00922`, `011613->STAR50_STITCH`, `001053->H00905`, `016634->H00852`, `013841->STAR50_STITCH`, `050025->SPX_CNY`, `000216->AU9999`）。
2. **波动率计算**：基于过去 60 个交易日日度对数或百分比收益率，按指数平滑（半衰衰减/span=60）计算年化波动率：
   $$\sigma_{k, t} = \sqrt{252 \times \text{EWMA\_Var}_{60}(r_{k})}$$
3. **波动率倒数加权**：
   对于权益类资产 $k$，根据信号得分 $S_{k, t}$ 与滚动波动率 $\sigma_{k, t}$ 调整风险暴露：
   $$w'_{k, t} = S_{k, t} \times \frac{\bar{\sigma}_{equity}}{\sigma_{k, t}}$$
   当资产短期由于题材炒作波动率异常脉冲放大（例如芯片/微盘 $\sigma > 35\%$）或处于高拥挤态时，$\frac{\bar{\sigma}}{\sigma_k} < 1.0$，其风险敞口被自动削减。
4. **溢出预算转移至纯债**：
   削减释放的权重预算 $\Delta W = \sum (S_k - w'_k)^+$ 100% 转移至组合内的低波纯债标的（`002351` 易方达裕祥 / `000086` 工银纯债）。
5. **单调性与边界保护**：将权重投影至该档位硬性约束区间（例如 C4 权益不突破 85%、C1 权益不突破 20%，熊市 C4 权益 $\le 55\%$、C5 权益 $\le 70\%$），确保 100% 兼容 1.3 中的 Challenger-1 压测断言。

### 2.2 R5 调仓净效用拦截器与在途摩擦精算逻辑
1. **净效用理论模型**：
   调仓决策应当满足净效用增量 $\Delta U > \text{MinNetBenefitThreshold}$：
   $$\Delta U = \text{ExpectedAlphaGain}_{20d} - \text{ExactRedemptionFee} - \text{SubscriptionFee} - \text{InTransitOpportunityCost}(\Delta t, \sigma_{index})$$
2. **各变量精确求值**：
   - **$\text{ExpectedAlphaGain}_{20d}$**：20 个交易日滚动超额增益。根据转入标的与转出标的的六维评分差（或动量差、历史 Alpha），折算 20 天预期收益：
     $$\text{ExpectedAlphaGain}_{20d} = \text{Amount} \times (\alpha_{in} - \alpha_{out}) \times \frac{20}{250}$$
   - **$\text{ExactRedemptionFee}$**：基于 FIFO 批次真实持有天数精确核算。若持有 $<7$ 天直接阻断；若 $7\sim 29$ 天，A 类扣 0.75%，C 类扣 0.50%；满期则按阶梯递减。
   - **$\text{SubscriptionFee}$**：同公司转换（`SWITCH`）享受转签优惠或仅补差价（取 $0.15\%$ 或 C 类 $0.00\%$）；跨公司申购 A 类收取 $0.15\%$，C 类 $0.00\%$。
   - **$\text{InTransitOpportunityCost}$**：
     - 同公司基金转换：$\Delta t_{arrive} = 0 \implies \text{InTransitOpportunityCost} = 0.0$。
     - 跨公司赎回再申购：$\Delta t_{arrive} = 2$ 天（国内权益）至 $4$ 天（QDII/跨境）。在资金未在市的空窗期，面临市场单边上涨踏空或反向波动的风险折价：
       $$\text{InTransitOpportunityCost} = \text{Amount} \times \sigma_{index} \times \sqrt{\frac{\Delta t_{arrive}}{250}}$$
3. **阈值拦截规则**：
   设定 $\text{MinNetBenefitThreshold} = 0.0$（或保守门槛 $0.10\%$ 金额）。若 $\Delta U \le \text{Threshold}$，表明本次调仓“省不下手续费，还承担在途踏空风险”，拦截器判定为不放行，标记 `🛡️ 摩擦/在途损耗大于预期收益，建议原地持仓不动`。
4. **同公司选基便利度加分 (Convenience Bonus)**：
   在选基评分中，若备选基金与当前持仓同属于一家基金公司（如易方达、富国、华夏），给予 $+5.0$ 分转换便利度加分，促使其在赛道评分中晋升第一，优先撮合同公司 T+1 SWITCH，从源头上抹平在途损耗。

---

## 3. 架构设计与代码植入点 (Architecture & Insertion Blueprint)

### 3.1 模块与文件全景依赖图
```
AGY2_FundAdvisory/
├── data_loader.py
│   └── DataLoader
│       └── [NEW] compute_ewma_volatility_and_correlation()  <-- R4 底层算子
├── strategy_bridge.py
│   └── StrategyBridge
│       ├── [ENHANCE] compute_dynamic_tier_weights()          <-- R4 倒数配权+纯债压舱
│       └── [ENHANCE] get_tier_sector_fund_selection()        <-- R5 同公司便利度加分
└── portfolio_manager.py
    └── PortfolioManager
        ├── [NEW] calculate_rebalance_net_utility()          <-- R5 净效用精算拦截核心
        ├── [ENHANCE] generate_rebalance_plan()              <-- R5 拦截标记与路由优选
        └── [ENHANCE] compute_fund_six_dimension_score()     <-- R5 转换便利度加分
```

### 3.2 详细设计规格与代码模板

#### 规范 1：`data_loader.py` 植入点
- **目标位置**：`data_loader.py` 类 `DataLoader` 内部（建议置于 `simulate_execution` 之前，约第 435 行）。
- **接口代码**：
```python
    @staticmethod
    def compute_ewma_volatility_and_correlation(
        df: pd.DataFrame,
        window: int = 60,
        span: int = 60,
        asset_cols: Optional[List[str]] = None
    ) -> Tuple[pd.Series, pd.DataFrame]:
        """
        [R4 核心算子] 实时计算各资产过去 window (60) 日 EWMA 年化波动率与相关性矩阵
        """
        default_cols = [
            'H00300', 'H00905', 'H00852', 'H00922', 'H30269',
            'STAR50_STITCH', 'AU9999', 'SPX_CNY', '930609', 'H11009'
        ]
        cols = [c for c in (asset_cols or default_cols) if c in df.columns]
        if df is None or len(df) < 10 or not cols:
            # 优雅降级兜底
            default_vol = pd.Series({c: 0.18 for c in cols})
            default_vol['H11009'] = 0.035
            default_vol['930609'] = 0.030
            default_vol['H30269'] = 0.140
            default_vol['AU9999'] = 0.130
            return default_vol, pd.DataFrame(np.eye(len(cols)), index=cols, columns=cols)

        sub_df = df[cols].tail(window)
        ret_df = sub_df.pct_change().dropna()
        if len(ret_df) < 5:
            default_vol = pd.Series({c: 0.18 for c in cols})
            return default_vol, pd.DataFrame(np.eye(len(cols)), index=cols, columns=cols)

        # EWMA 方差与年化波动率 sigma = sqrt(252 * var)
        ewma_var = ret_df.ewm(span=span, adjust=True).var().iloc[-1]
        # 避免非正方差
        ewma_var = ewma_var.clip(lower=1e-8)
        ewma_vol_ann = np.sqrt(ewma_var * 252.0)
        corr_matrix = ret_df.corr().fillna(0.0)

        return ewma_vol_ann, corr_matrix
```

#### 规范 2：`strategy_bridge.py` 植入点
- **目标位置**：`strategy_bridge.py` 中的 `compute_dynamic_tier_weights`（第 2823~3058 行）。
- **映射关系**：
```python
FUND_TO_PROXY_INDEX = {
    "002351": "H11009", "000086": "H11009", "018757": "H11009",
    "005561": "H30269", "005562": "H30269",
    "100032": "H00922", "008682": "H00922",
    "000216": "AU9999", "000217": "AU9999",
    "050025": "SPX_CNY", "001071": "SPX_CNY",
    "011613": "STAR50_STITCH", "011612": "STAR50_STITCH",
    "001053": "H00905", "161017": "H00905",
    "016634": "H00852", "016633": "H00852",
    "013841": "STAR50_STITCH", "013840": "STAR50_STITCH",
    "007339": "H00300", "110020": "H00300"
}
```
- **核心逻辑重构**：
```python
        # 1. 解析基础字典 base_dict (bull_weights / bear_weights / oscillating_weights)
        # 2. 获取行情矩阵以计算 60 日 EWMA 波动率
        mat_df = history_df if (history_df is not None and len(history_df) >= 30) else None
        if mat_df is None:
            try:
                mat_df = cls.load_matrix(auto_sync=False)
            except Exception:
                mat_df = None

        if mat_df is not None and len(mat_df) >= 30:
            from data_loader import DataLoader
            ewma_vols, corr_mat = DataLoader.compute_ewma_volatility_and_correlation(mat_df, window=60, span=60)
            
            # 3. 波动率倒数加权与纯债压舱转移
            adjusted_weights = {}
            trimmed_budget = 0.0
            equity_codes = [c for c in target_dict if c not in ["002351", "000086", "018757", "000216", "000217"]]
            
            for code, base_w in target_dict.items():
                if code in equity_codes:
                    proxy = FUND_TO_PROXY_INDEX.get(code, "H00300")
                    vol = float(ewma_vols.get(proxy, 0.18))
                    # 基准波动率设为 0.18，若资产波动率放大 (>0.22)，按比例收缩
                    scaling = min(1.20, max(0.50, 0.18 / max(vol, 0.08)))
                    new_w = base_w * scaling
                    if new_w < base_w:
                        trimmed_budget += (base_w - new_w)
                        adjusted_weights[code] = new_w
                    else:
                        adjusted_weights[code] = base_w
                else:
                    adjusted_weights[code] = base_w
            
            # 将溢出的风险预算转移至纯债压舱石 (002351)
            bond_code = "002351" if "002351" in adjusted_weights else ("000086" if "000086" in adjusted_weights else None)
            if bond_code and trimmed_budget > 0:
                adjusted_weights[bond_code] = adjusted_weights.get(bond_code, 0.0) + trimmed_budget
            
            target_dict = adjusted_weights
        
        # 4. 执行严谨的边界投影与单调性守护 (确保 100% 满足 Challenger-1 压测)
```

#### 规范 3：`portfolio_manager.py` 净效用拦截器与在途摩擦精算
- **目标位置**：`portfolio_manager.py` 中新增 `calculate_rebalance_net_utility`，并在 `generate_rebalance_plan`（第 4627 行）中装配。
- **接口代码**：
```python
    def calculate_rebalance_net_utility(
        self,
        from_fund_code: str,
        to_fund_code: str,
        amount: float,
        expected_alpha_20d: Optional[float] = None,
        market_snapshot: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        [R5 核心拦截器] 精算单笔拟调仓净效用 Delta U:
        Delta U = ExpectedAlphaGain_20d - ExactRedemptionFee(FIFO) - SubscriptionFee - InTransitOpportunityCost(Delta t, sigma_index)
        """
        amt = float(max(0.0, amount))
        from_meta = self.resolve_fund_meta(from_fund_code)
        to_meta = self.resolve_fund_meta(to_fund_code)
        
        # 1. 同公司检测与在途时差
        is_same_company = bool(
            from_meta.get("company") and
            to_meta.get("company") and
            from_meta.get("company") == to_meta.get("company")
        )
        
        # 2. 真实 FIFO 赎回费测算
        exact_redemption_fee = 0.0
        h_from = self.holdings.get(from_fund_code)
        if h_from and amt > 0:
            calc_shares = min(h_from.shares, amt / max(h_from.current_nav, 0.001))
            rem_s = calc_shares
            for b in h_from.batches:
                if rem_s <= 1e-4:
                    break
                t_s = min(b.shares, rem_s)
                rate, is_pen, _ = FeeMatrixCalculator.get_redemption_fee_rate(h_from.share_class, b.holding_days)
                exact_redemption_fee += (t_s * h_from.current_nav * rate)
                rem_s -= t_s
        exact_redemption_fee = round(exact_redemption_fee, 2)
        
        # 3. 前端申购费测算
        if is_same_company:
            # 同公司基金转换享受费率优惠 (补偿转签差价约 0.15% 或 C类0)
            sub_fee = 0.0 if to_meta.get("share_class") == "C" else round(amt * 0.0015, 2)
            delta_t_arrive = 0
            in_transit_cost = 0.0
        else:
            # 跨公司赎回再申购
            sub_calc = FeeMatrixCalculator.calculate_subscription_fee(amt, share_class=to_meta.get("share_class", "A"))
            sub_fee = sub_calc.get("fee_amount", round(amt * 0.0015, 2))
            
            # 在途踏空风险成本: 国内基金 T+2 到账, QDII T+4 到账
            is_qdii = any(k in to_meta.get("fund_name", "") for k in ["QDII", "标普", "纳斯达克"]) or to_fund_code in ["050025", "001071"]
            delta_t_arrive = 4 if is_qdii else 2
            
            snap = market_snapshot or {}
            sigma_index = float(snap.get("c300_annualized_vol", 0.18))
            # 在途风险成本 = Amount * sigma * sqrt(Delta t / 250)
            in_transit_cost = round(amt * sigma_index * np.sqrt(delta_t_arrive / 250.0), 2)
            
        # 4. 20 日预期 Alpha 增益
        if expected_alpha_20d is not None:
            exp_alpha = float(expected_alpha_20d)
        else:
            # 基于六维总分差推算预期年化超额 (每分约对应 0.2% 年化超额)
            score_to = self.compute_fund_six_dimension_score(to_fund_code).get("total_score", 85.0)
            score_from = self.compute_fund_six_dimension_score(from_fund_code).get("total_score", 80.0)
            alpha_annual = max(0.0, (score_to - score_from) * 0.002)
            exp_alpha = round(amt * alpha_annual * (20.0 / 250.0), 2)
            
        # 5. 净效用 Delta U 与拦截判定
        total_friction = round(exact_redemption_fee + sub_fee + in_transit_cost, 2)
        delta_u = round(exp_alpha - total_friction, 2)
        
        min_threshold = 0.0
        should_intercept = (delta_u <= min_threshold)
        
        interception_badge = "🛡️ 摩擦/在途损耗大于预期收益，建议原地持仓不动" if should_intercept else "✅ 预期收益覆盖摩擦，建议调仓"
        
        return {
            "from_fund_code": from_fund_code,
            "to_fund_code": to_fund_code,
            "amount": amt,
            "is_same_company": is_same_company,
            "delta_t_arrive": delta_t_arrive,
            "expected_alpha_gain_20d": exp_alpha,
            "exact_redemption_fee": exact_redemption_fee,
            "subscription_fee": sub_fee,
            "in_transit_opportunity_cost": in_transit_cost,
            "total_friction_and_risk_cost": total_friction,
            "delta_u": delta_u,
            "should_intercept": should_intercept,
            "interception_badge": interception_badge
        }
```

#### 规范 4：同公司选基便利度加分 (Convenience Bonus)
- **目标位置**：`portfolio_manager.py:compute_fund_six_dimension_score` 与 `strategy_bridge.py:get_tier_sector_fund_selection`。
- **机制**：
  若备选基金所属基金公司在用户当前持仓公司集合 `held_companies = {h.company for h in self.holdings.values() if h.shares > 0}` 中，在六维打分中赋予 `+5.0` 分：
  ```python
  if fund_company and fund_company in held_companies:
      switch_convenience_bonus = 5.0
      total_score = min(100.0, total_score + switch_convenience_bonus)
  ```
  引导算法在同赛道多标的竞争时，自动推荐与现有持仓同门派的冠军，消除在途摩擦。

---

## 4. 边界与注意事项 (Caveats)

1. **测试性能与并发开销**：
   `test_stress_quant_model_challenger.py` 包含从 1000 点到 10000 点的全域点位扫描与极端扰动测试。`compute_dynamic_tier_weights` 必须保持极高计算效率（建议缓存 60 日 EWMA 序列，避免每一轮重算全量 Parquet）。
2. **空矩阵与极端非标入参容错**：
   在单元测试中，部分测试用例会传入 `history_df=None` 或极短的 DataFrame（如 10 行）。此时必须平滑回退至预置基准字典，严禁抛出 `IndexError` 或 `KeyError`。
3. **持仓状态持久化与在途队列隔离**：
   当 `Delta U <= 0` 触发拦截并标记为 `🛡️ 摩擦/在途损耗大于预期收益，建议原地持仓不动` 时，该路由不得生成执行订单，避免向 `pending_orders` 写入无效换仓单。

---

## 5. 结论 (Conclusion)

- **可行性论证**：R4 与 R5 的量化数学逻辑完全内生封闭，不依赖任何外部黑盒 API，完全符合因果律与防作弊规范。
- **分工接口契约**：
  - **Agent-2** 可直接在 `data_loader.py` 中植入 `DataLoader.compute_ewma_volatility_and_correlation`，在 `strategy_bridge.py` 中重构 `compute_dynamic_tier_weights`。
  - **Agent-2** 与 **Agent-3** 协同在 `portfolio_manager.py` 中集成 `calculate_rebalance_net_utility` 与同公司便利度加分，并向 `generate_rebalance_plan` 注入拦截标记。
  - 4 个系统只读裁判基建文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）继续受到严格隔离保护。

---

## 6. 独立验证方法 (Verification Method)

在实施完成后，可通过以下命令与测试用例进行独立验证：

1. **基建与裁判测试验证**：
   ```powershell
   cd AGY2_FundAdvisory
   python -m pytest tests/test_infra.py -q
   ```
   *断言*：15 项基建测试全部通过，无日历硬编码或因果泄露。

2. **R4 动态风险预算与对抗压测验证**：
   ```powershell
   cd AGY2_FundAdvisory
   python -m pytest tests/test_stress_quant_model_challenger.py tests/test_dynamic_risk_and_metrics.py -q
   ```
   *断言*：全域点位扫描不倒挂、单调性定理 `Equity(C1) < Equity(C2) < Equity(C3) < Equity(C4) < Equity(C5)` 恒成立，熊市 C4/C5 减仓防爆仓通过。

3. **R5 交易时钟、费率与在途拦截专项验证**：
   ```powershell
   cd AGY2_FundAdvisory
   python -m pytest tests/test_trading_clock_fee.py tests/test_portfolio_manager.py -q
   ```
   *断言*：FIFO 批次扣减、7天强拦截、在途踏空成本与 `🛡️ 摩擦/在途损耗大于预期收益，建议原地持仓不动` 拦截标记准确触发。

4. **全量回归基线验证 (Empirical Baseline Pass)**：
   ```powershell
   cd AGY2_FundAdvisory
   python -m pytest tests/ -q
   ```
   *实测基线*：全量套件共 246 项测试（`246 passed in 408.77s`，零错误通过）。任何新增算法与修改均须保持此全量回归 100% 通过。

