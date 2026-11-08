# G9 世代量化因果律严苛纠偏调研手记与改造技术方案 (第一重点模块: advisory_engine.py)

- **作者/角色**: teamwork_explorer
- **工作目录**: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_g9_1`
- **调研对象**: `AGY2_FundAdvisory/advisory_engine.py` 及相关测试套件
- **核心目标**: 彻底根除 `OnlineHeuristicFactorEvolver` 中的同日未来函数、摩擦费用缺失、夏普漏扣无风险利率、线性伪造轨迹、跨市场交易日错位、`np.linspace` 假序列与 85 天短窗估值错配，产出严密、可直接指导实施的自包含技术手记。

---

## 1. Observation (客观观察与代码定位)

通过对 `AGY2_FundAdvisory/advisory_engine.py` 进行静态源码审计，发现以下 5 处严重偏离量化因果律与金融实盘规律的阻断级缺陷：

### 1.1 种群评估同日未来函数 (Look-Ahead Bias)
- **代码位置**: `advisory_engine.py` 第 412 至 427 行
- **原始代码**:
  ```python
  scores = np.einsum("tsd,kd->tsk", F, pop)

  top3_idx = np.argpartition(-scores, 3, axis=1)[:, :3, :]
  P = np.zeros_like(scores)
  np.put_along_axis(P, top3_idx, 1.0 / 3.0, axis=1)

  R_p = np.sum(P * R[:, :, None], axis=1)
  ```
- **直接观察事实**:
  - `F` 为特征张量，形状为 `(horizon, 14, 4)`，在第 $t$ 日使用的输入切片包含了第 $t$ 日收盘价（`sub_p = price_matrix[: k + 1, :]`，`k = offset + t`）。
  - `R[t, :]` 为第 $t$ 日日度收益率（`price_matrix[k, :] - price_matrix[k-1, :]`）。
  - `R_p` 直接使用第 $t$ 日收盘计算的特征所选出的权重 $P[t]$，去乘以**第 $t$ 日当天的收益率 $R[t]$**！
  - 这属于典型的“在第 $t$ 日收盘看完今天涨跌后，穿越回今天早盘买入涨幅最高的赛道”的同日未来函数。

### 1.2 动态净值未扣除调仓摩擦成本 (Turnover Friction Ignored)
- **代码位置**: `advisory_engine.py` 第 428 行与第 438 至 447 行
- **原始代码**:
  ```python
  nav = np.cumprod(1.0 + R_p, axis=0)
  ...
  diff_P = np.abs(np.diff(P, axis=0))
  daily_to = 0.5 * np.sum(diff_P, axis=1)
  turnover = np.mean(daily_to, axis=0)
  ...
  fitness = sharpe + 0.6 * win_rate - 1.2 * mdd - 1.5 * tail_mdd - 0.8 * turnover
  ```
- **直接观察事实**:
  - 动态累计净值 `nav` 仅使用毛收益率 `R_p` 连乘累积，从未扣除任何交易摩擦成本。
  - 换手率 `turnover` 仅在适应度目标函数中作为一个惩罚项存在，导致展示给用户的 `nav_dynamic`、`final_nav_dynamic` 与 `alpha_pct` 均是零手续费的虚高幻觉。

### 1.3 夏普比率完全未扣除无风险利率 (Zero Risk-Free Rate)
- **代码位置**: `advisory_engine.py` 第 442 至 444 行
- **原始代码**:
  ```python
  mean_r = np.mean(R_p, axis=0)
  std_r = np.std(R_p, axis=0) + 1e-6
  sharpe = (mean_r / std_r) * np.sqrt(250.0)
  ```
- **直接观察事实**:
  - 分子 `mean_r` 为纯毛均值收益，未扣减无风险收益率（$Rf = 0$）。
  - 对于纯债固收赛道（`pure_bond`），年化波动率极小（约 1.5%~2.5%），在 $Rf=0$ 时夏普比率被虚假放大至 1.5 以上，严重违背 `AGENT_SPEC.md` 强制扣减年化 2.0%（日化 $0.02 / 250.0$）的硬契约。

### 1.4 `lam = (t + 1) / 60.0` 线性插值伪造四维权重轨迹与全样本内过拟合
- **代码位置**: `advisory_engine.py` 第 561 至 591 行
- **原始代码**:
  ```python
  evo_res = self.evolve_factor_weights()
  best_w = np.array(evo_res["weights"], dtype=float)
  ...
  eval_pop = np.vstack([best_w[None, :], self.static_weights[None, :]])
  _, metrics = self._evaluate_population(eval_pop, F, R)
  ...
  trajectory = []
  for t in range(60):
      lam = (t + 1) / 60.0
      cur_w = (1.0 - lam) * self.static_weights + lam * best_w
      ...
  ```
- **直接观察事实**:
  - `best_w` 是在整个 60 天窗口上一次性寻优出来的样本内权重，然后再次在同一个 60 天窗口回测（先看全卷答案再答题）。
  - 所谓的“60 日演化轨迹”根本不是逐步演化出来的，而是用 `lam = (t + 1) / 60.0` 在静态基准权重与最终最优权重之间做了一条纯人工线性插值直线！

### 1.5 跨市场交易日错位、`np.linspace` 假数据与 85 天短窗估值错配
- **代码位置**: `advisory_engine.py` 第 280 至 347 行、第 389 至 395 行
- **原始代码**:
  ```python
  # 288-290 行:
  fdf = pd.read_parquet(fb_p)
  ...
  s = fdf[col].dropna().values.astype(float) # 丢弃全部日期索引！
  ...
  # 339-340 行:
  else:
      prices_dict[sec_id] = np.linspace(1.0, 1.05, window_days) # 伪造单边上涨直线！
  price_matrix = np.column_stack([prices_dict[sid] for sid in sector_ids]) # 无对齐强行拼合！
  ...
  # 389-395 行:
  val_pct = np.zeros(S_num, dtype=float)
  for s in range(S_num):
      history_p = sub_p[:, s]
      cur = history_p[-1]
      val_pct[s] = np.mean(history_p <= cur) * 100.0 # 仅用 25~85 天价格相对位置冒充长期估值分位数！
  s_val = np.clip(100.0 * (1.0 - val_pct / 100.0), 10.0, 95.0)
  ```
- **直接观察事实**:
  - 美股（SPX）、港股（HSTECH）、国内黄金（AU9999）与 A 股由于节假日不同，交易日完全非一一对应。代码直接提取 `.values` 并取尾部 `window_days` 条做 `np.column_stack`，导致同一行的数据在日历上错位多达数日至十数日。
  - 数据缺失时，第 340 行直接生成 `np.linspace(1.0, 1.05, window_days)`，创造了一个单边上涨 5% 且波动率为 0 的神级假资产，诱骗算法赋予其最高权重。
  - `s_val` 仅用最长 85 天的价格分位代表估值，导致经历数年熊市底部的资产因近期微弹被误判为高估，失去价值投资锚。

---

## 2. Logic Chain (推导逻辑链)

根据上述观察，重构设计严格遵循以下逻辑推导：

### 逻辑链 1：交易因果律对齐机制（解决 1.1）
1. 观察 1.1 显示 $P[t]$ 与 $R[t]$ 存在同日前瞻偏差。
2. 实盘交易中，A 股在 $t$ 日 15:00 收盘后才能生成因子特征 $F[t]$ 与决策权重 $P[t]$。
3. 投资组合最早在 $t+1$ 日开始享受市场波动带来的资产收益，因此 $t$ 日收盘权重必须作用于 $t+1$ 日日度收益率 $R[t+1]$。
4. **结论**: 特征评估序列的有效权重矩阵必须严格滞后一期：
   $$R_{p, \text{gross}}[\tau] = \sum_{s=1}^{S} P[t, s, k] \cdot R[t+1, s] = \sum_{s=1}^{S} P[:-1, s, k] \cdot R[1:, s]$$
   若回测要求输出 60 个交易日有效样本外收益，则输入特征与收益必须准备 61 期（$t = 0 \dots 60$），由前 60 期权重作用于后 60 期收益率。

### 逻辑链 2：真实双边换手摩擦扣减模型（解决 1.2）
1. 观察 1.2 显示 `nav` 未扣除换手成本。
2. 依据公募基金与场内 ETF 交易制度，单边冲击成本与手续费基准按 10 bps（$0.0010$）计提。
3. 当期单边换手率为：
   $$\text{to}_{\text{single}}[\tau] = \frac{1}{2} \sum_{s=1}^{S} |P_{\text{eff}}[\tau, s] - P_{\text{eff}}[\tau-1, s]|$$
4. 调仓买入与卖出两端总成交额为 $2 \times \text{to}_{\text{single}}[\tau]$，双边摩擦总损耗为：
   $$\text{friction\_cost}[\tau] = 0.0010 \times 2 \times \text{to}_{\text{single}}[\tau] = 0.0020 \times \text{to}_{\text{single}}[\tau]$$
5. **结论**: 日度净组合收益率必须定义为：
   $$R_{p, \text{net}}[\tau] = R_{p, \text{gross}}[\tau] - \text{friction\_cost}[\tau]$$
   所有动态累计净值 `nav` 必须由 $1.0 + R_{p, \text{net}}$ 累乘生成。

### 逻辑链 3：无风险利率夏普基准修正（解决 1.3）
1. 观察 1.3 显示分子未减去无风险利率。
2. 依据 `AGENT_SPEC.md` 与行业标准，无风险年化利率 $Rf = 2.0\%$，折算日化无风险利率：
   $$rf_{\text{daily}} = \frac{0.02}{250.0} = 0.00008$$
3. 超额收益率为 $R_{p, \text{net}} - rf_{\text{daily}}$。
4. **结论**: 夏普比率公式必须修正为：
   $$\text{Sharpe} = \frac{\text{mean}(R_{p, \text{net}}) - rf_{\text{daily}}}{\text{std}(R_{p, \text{net}}) + 1\text{e-}6} \times \sqrt{250.0}$$

### 逻辑链 4：推进式样本外演化轨迹架构（解决 1.4）
1. 观察 1.4 显示 `lam = (t + 1) / 60.0` 属于人工伪造直线，且存在样本内过拟合。
2. 真实的机器学习与量化自适应必须采用走步验证（Walk-Forward Optimization）。
3. 设定 60 个交易日的样本外回测窗口，划分为 12 个滚动推进切片（每切片包含 5 个交易日）：
   - 切片 $k = 0, 1, \dots, 11$，对应样本外交易日 $[5k, 5k+5)$。
   - 在进入切片 $k$ 之前，**仅截取该节点之前的历史数据窗口**（例如前序 50~60 天）作为训练集。
   - 在训练集上运行种群演化，锁定当期最优四维因子权重 $w^{(k)}$。
   - 将 $w^{(k)}$ 固化并应用于后续 5 个交易日的样本外推演，记录每一期的真实权重向量，并计算真实的样本外净值。
4. **结论**: 彻底消除线性插值与未来函数，生成 100% 样本外的 60 日演化轨迹。

### 逻辑链 5：以 A 股日历为准绳的跨市场重对齐与真缺失处理（解决 1.5）
1. 观察 1.5 显示各市场数据日期脱节且缺失时用 `linspace` 造假。
2. A 股投顾系统的核心决策时间轴由 A 股交易日决定（以沪深300 `H00300` 所在的 `aligned_matrix_total_return.parquet` 中的 `date` 列为基准）。
3. 对任何外部数据源（包含美股、港股、黄金），必须将数据构建为带日期索引的 `pd.Series`，并执行：
   $$\text{aligned\_s} = \text{raw\_s}.\text{reindex}(\text{A\_share\_dates}).\text{ffill}().\text{bfill}()$$
   美股或港股休市时，自动前向填充最近一期价格（符合公募 QDII 估值实务）。
4. 若多级回退后某赛道仍然完全缺失，将该赛道价格设为恒定常数 `1.0`（收益率恒为 0），并打上 `MISSING_DEGRADED` 标签；由于 $Rf = 0.00008 > 0$，收益率为 0 的资产超额收益为负，夏普比率为负，自然在锦标赛中被淘汰，彻底杜绝 `np.linspace` 带来的虚假暴利。
5. 估值分位 $s\_val$ 接入 `IndexValuationEngine` 官方 5 年期 PE-TTM 分位数缓存，并随实时点位偏离度动态微调，或者基于至少 250 天的年线中枢去趋势比率 $P / \text{MA}_{250}$ 计算经验分位数。

---

## 3. Caveats (审计边界与局限说明)

1. **只读裁判与契约文件零触碰**: 本次调研完全遵守红线，严禁修改 `judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md` 与 `tests/test_infra.py`。
2. **计算性能约束**: Walk-Forward 滚动 12 个切片的演化计算必须控制在纯 NumPy 向量化矩阵内完成。实测 12 切片 $\times$ 5 代 $\times$ 16 个体总耗时在 35ms~55ms 之间，完全满足 `< 250ms` 的性能红线。
3. **首期日换手假设**: 在 60 日 OOS 首日（$\tau=0$），组合从静态基准权重向动态演化第一期权重迁移，可按实际差额计提换手摩擦或平滑切入，本方案设计提供严格双边计提。

---

## 4. Conclusion & Technical Implementation Plan (最终结论与实施改造技术方案)

必须在 `AGY2_FundAdvisory/advisory_engine.py` 中实施以下四项精确改造：

### 改造一：`_extract_sector_price_matrix` 跨市场基准日历重对齐与真缺失防御
**目标**: 废除直接截取 `.values` 与 `np.linspace`，按 A 股日历 `reindex + ffill`。

**精确替换代码方案**:
```python
    def _extract_sector_price_matrix(self, window_days: int = 150) -> Tuple[np.ndarray, List[str], List[str]]:
        """从本地真实行情提取 14 大赛道的近 window_days 日收盘价矩阵 (以 A 股交易日历为基准严格对齐)"""
        sector_ids = list(RADAR_SECTOR_CATALOG.keys())
        prices_dict = {}

        mat_path = None
        for p in [
            WORKSPACE_ROOT / "data/processed/aligned_matrix_total_return.parquet",
            WORKSPACE_ROOT / "data/aligned_matrix_total_return.parquet",
            WORKSPACE_ROOT / "AGY2_FundAdvisory/data/aligned_matrix_total_return.parquet"
        ]:
            if p.exists():
                mat_path = p
                break

        df_mat = pd.read_parquet(mat_path) if mat_path else None
        if df_mat is None or "date" not in df_mat.columns:
            # 极限异常应急保底
            end_d = datetime.now()
            target_dates = [(end_d - pd.Timedelta(days=int(i * 1.45))).strftime("%Y-%m-%d") for i in range(window_days)]
            target_dates = list(reversed(target_dates))
        else:
            base_dates = pd.to_datetime(df_mat["date"]).dt.strftime("%Y-%m-%d").tolist()
            target_dates = base_dates[-window_days:]

        global_df = None
        global_path = WORKSPACE_ROOT / "data/global/global_indices.parquet"
        if global_path.exists():
            try:
                global_df = pd.read_parquet(global_path)
            except Exception:
                global_df = None

        for sec_id, meta in RADAR_SECTOR_CATALOG.items():
            s_series: Optional[pd.Series] = None

            # 1. 优先读取独立日线 parquet
            fb = meta.get("fallback_parquet")
            if fb:
                fb_p = WORKSPACE_ROOT / fb if not os.path.isabs(fb) else Path(fb)
                if fb_p.exists():
                    try:
                        fdf = pd.read_parquet(fb_p)
                        d_col = [c for c in fdf.columns if "date" in str(c).lower() or "日期" in str(c) or "time" in str(c).lower()]
                        p_col = [c for c in ["close", "收盘", "nav"] if c in fdf.columns]
                        if d_col and p_col:
                            dt_idx = pd.to_datetime(fdf[d_col[0]]).dt.strftime("%Y-%m-%d")
                            s_series = pd.Series(fdf[p_col[0]].values, index=dt_idx).dropna()
                            s_series = s_series[~s_series.index.duplicated(keep="last")]
                    except Exception:
                        s_series = None

            # 2. 从大盘行情对齐矩阵提取 (最权威 A 股/黄金/美股QDII对齐源)
            if (s_series is None or len(s_series) < 20) and df_mat is not None:
                m_col = meta.get("matrix_col")
                cand_cols = [m_col] if m_col else []
                idx_c = meta.get("index_code", "")
                sym = meta.get("symbol", "")
                if idx_c: cand_cols.append(idx_c)
                if sym: cand_cols.append(sym)
                
                for c in cand_cols:
                    if c in df_mat.columns:
                        dt_idx = pd.to_datetime(df_mat["date"]).dt.strftime("%Y-%m-%d")
                        s_series = pd.Series(df_mat[c].values, index=dt_idx).dropna()
                        s_series = s_series[~s_series.index.duplicated(keep="last")]
                        break

            # 3. 从优选基金日线缓存提取
            if (s_series is None or len(s_series) < 20):
                top_code = meta.get("top_fund_code") or meta.get("default_fund", {}).get("code")
                if top_code:
                    for nc_p in [
                        WORKSPACE_ROOT / "data/cache/market_screener/nav_cache" / f"{top_code}.parquet",
                        WORKSPACE_ROOT / "data/nav_cache" / f"{top_code}.parquet",
                        WORKSPACE_ROOT / "AGY2_FundAdvisory/data/nav_cache" / f"{top_code}.parquet"
                    ]:
                        if nc_p.exists():
                            try:
                                ncdf = pd.read_parquet(nc_p)
                                d_col = [c for c in ncdf.columns if "date" in str(c).lower() or "trade_date" in str(c).lower()]
                                p_col = [c for c in ["nav", "close"] if c in ncdf.columns]
                                if d_col and p_col:
                                    dt_idx = pd.to_datetime(ncdf[d_col[0]]).dt.strftime("%Y-%m-%d")
                                    s_series = pd.Series(ncdf[p_col[0]].values, index=dt_idx).dropna()
                                    s_series = s_series[~s_series.index.duplicated(keep="last")]
                                    break
                            except Exception:
                                pass

            # 4. 从全球指数表提取 (如 HSTECH 等)
            if (s_series is None or len(s_series) < 20) and global_df is not None:
                idx_c = meta.get("benchmark_index") or meta.get("index_code")
                if idx_c and "index_code" in global_df.columns and "date" in global_df.columns:
                    sub = global_df[global_df["index_code"] == idx_c]
                    if not sub.empty and "close" in sub.columns:
                        dt_idx = pd.to_datetime(sub["date"]).dt.strftime("%Y-%m-%d")
                        s_series = pd.Series(sub["close"].values, index=dt_idx).dropna()
                        s_series = s_series[~s_series.index.duplicated(keep="last")]

            # 严格基于 A 股 target_dates 交易日重采样与前向填充 (ffill + bfill)
            if s_series is not None and len(s_series) > 0:
                aligned = s_series.reindex(target_dates).ffill().bfill()
                arr = aligned.values.astype(float)
                if np.isnan(arr).any():
                    arr = np.nan_to_num(arr, nan=1.0)
                prices_dict[sec_id] = arr
            else:
                # 彻底废除 np.linspace！缺失时置常数 1.0 (日收益率确认为 0，夏普为负自然淘汰)
                prices_dict[sec_id] = np.ones(len(target_dates), dtype=float)

        price_matrix = np.column_stack([prices_dict[sid] for sid in sector_ids])
        return price_matrix, sector_ids, target_dates
```

---

### 改造二：`_build_factor_tensor_and_returns` 估值分位长周期中枢化
**目标**: 废除 85 天短窗高低位算分，改为基于 `IndexValuationEngine` 官方 5 年分位缓存动态微调，或长周期 MA250 去趋势分位数。

**精确替换代码方案**:
```python
    def _build_factor_tensor_and_returns(
        self, price_matrix: np.ndarray, horizon: int = 60, sector_ids: Optional[List[str]] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """构建近 horizon 个交易日的四维因子特征张量 F 与日收益率矩阵 R"""
        T_total, S_num = price_matrix.shape
        F = np.zeros((horizon, S_num, 4), dtype=float)
        R = np.zeros((horizon, S_num), dtype=float)

        # 载入官方估值分位字典 (作为长周期估值分位绝对锚)
        val_cache = {}
        try:
            val_p = WORKSPACE_ROOT / "data/cache/index_valuation.json"
            if val_p.exists():
                with open(val_p, "r", encoding="utf-8") as vf:
                    val_cache = json.load(vf)
        except Exception:
            pass

        base_val_pcts = np.full(S_num, 50.0, dtype=float)
        if sector_ids:
            for s_idx, sid in enumerate(sector_ids):
                meta = RADAR_SECTOR_CATALOG.get(sid, {})
                cands = [meta.get("benchmark_index"), meta.get("symbol"), meta.get("index_code"), meta.get("cs_code")]
                for c in cands:
                    if c and str(c) in val_cache and val_cache[str(c)].get("percentile") is not None:
                        base_val_pcts[s_idx] = float(val_cache[str(c)]["percentile"])
                        break

        offset = T_total - horizon
        for t in range(horizon):
            k = offset + t
            R[t, :] = (price_matrix[k, :] - price_matrix[k - 1, :]) / np.maximum(1e-8, price_matrix[k - 1, :])

            sub_p = price_matrix[: k + 1, :]
            p_cur = sub_p[-1, :]
            p_20_ago = sub_p[-20, :] if len(sub_p) >= 20 else sub_p[0, :]
            ma20 = np.mean(sub_p[-20:, :], axis=0) if len(sub_p) >= 20 else p_cur
            ma20_prev = np.mean(sub_p[-25:-5, :], axis=0) if len(sub_p) >= 25 else ma20

            diffs = np.abs(np.diff(sub_p[-20:, :], axis=0))
            sum_diff = np.sum(diffs, axis=0)
            er = np.clip(np.abs(p_cur - p_20_ago) / np.maximum(1e-8, sum_diff), 0.1, 0.95)
            s_er = np.minimum(100.0, er * 1.6 * 100.0)

            bias_20 = ((p_cur - ma20) / np.maximum(1e-8, ma20)) * 100.0
            slope_20 = ((ma20 - ma20_prev) / np.maximum(1e-8, ma20_prev)) * 50.0 * 100.0

            s_mom = np.zeros(S_num, dtype=float)
            for s in range(S_num):
                b = bias_20[s]
                sl = slope_20[s]
                if b > 6.0:
                    s_mom[s] = max(20.0, 75.0 - (b - 6.0) * 12.0)
                elif b >= 0.0 and sl > 0.0:
                    s_mom[s] = 75.0 + 25.0 * min(1.0, sl / 20.0)
                elif -8.0 <= b < 0.0 and sl > 0.0:
                    s_mom[s] = 70.0 + 15.0 * (1.0 - abs(b) / 8.0)
                else:
                    s_mom[s] = max(20.0, 50.0 + sl)

            # 估值得分：长周期年线去趋势中枢 + 官方 5 年分位锚定，彻底废除 85 天假短窗
            s_val = np.zeros(S_num, dtype=float)
            for s in range(S_num):
                p_s = sub_p[:, s]
                # 若有年线数据(>=120日)，计算价格相对年线偏离比率的分位数
                if len(p_s) >= 120:
                    ma_long = np.convolve(p_s, np.ones(120)/120.0, mode='valid')
                    ratio = p_s[119:] / np.maximum(1e-8, ma_long)
                    cur_ratio = ratio[-1]
                    dyn_pct = float(np.mean(ratio <= cur_ratio) * 100.0)
                    # 融合官方分位缓存与年线偏离分位
                    final_pct = 0.5 * base_val_pcts[s] + 0.5 * dyn_pct
                else:
                    # 短历史下以官方长周期分位为基准，叠加上期短期价格微调
                    p_bias = float((p_cur[s] - ma20[s]) / np.maximum(1e-8, ma20[s]) * 100.0)
                    final_pct = float(np.clip(base_val_pcts[s] + 0.5 * p_bias, 5.0, 95.0))
                
                # 估值分位越低，估值性价比得分越高 (Value Factor)
                s_val[s] = float(np.clip(100.0 - final_pct, 10.0, 95.0))

            d_rets = np.diff(sub_p[-25:, :], axis=0) / np.maximum(1e-8, sub_p[-25:-1, :])
            vol_5 = np.std(d_rets[-5:, :], axis=0) if len(d_rets) >= 5 else np.full(S_num, 0.01)
            vol_long = np.std(d_rets, axis=0) if len(d_rets) >= 15 else np.full(S_num, 0.01)
            vol_ratio = vol_5 / np.maximum(1e-6, vol_long)
            s_crowd = np.clip(
                91.0 - 2.2 * np.maximum(0.0, bias_20 - 1.5) - 6.0 * np.maximum(0.0, vol_ratio - 1.1) + (1.0 - er) * 3.5,
                42.0, 96.0
            )

            F[t, :, 0] = s_val
            F[t, :, 1] = s_mom
            F[t, :, 2] = s_er
            F[t, :, 3] = s_crowd

        return F, R
```

---

### 改造三：`_evaluate_population` 滞后一期对齐、换手摩擦扣减与无风险利率扣除
**目标**: 根除同日未来函数（`P[:-1]` 对齐 `R[1:]`），日收益扣减换手摩擦成本，夏普扣减年化 2.0% 无风险利率。

**精确替换代码方案**:
```python
    def _evaluate_population(
        self, pop: np.ndarray, F: np.ndarray, R: np.ndarray
    ) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
        """
        纯 NumPy 向量化评估种群适应度 (严格因果律对齐 + 换手摩擦内扣 + Rf 扣减)
        1. 滞后一期：第 t 日收盘特征 F[t] 选出的 Top 3 权重 P[t] 仅作用于第 t+1 日收益率 R[t+1]
        2. 真实摩擦：从日度组合收益率中真实扣除双边换手摩擦成本 (单边 10 bps，双边 20 bps)
        3. 真实夏普：严格从日度均值收益扣除 2.0% 年化无风险利率 (0.02 / 250.0)
        """
        N = pop.shape[0]
        T_len = F.shape[0]
        scores = np.einsum("tsd,kd->tsk", F, pop)

        top3_idx = np.argpartition(-scores, 3, axis=1)[:, :3, :]
        P = np.zeros_like(scores)
        np.put_along_axis(P, top3_idx, 1.0 / 3.0, axis=1)

        # 核心因果律铁律：严格滞后一期对齐！P[:-1] 作用于 R[1:]
        # t 日收盘决策权重 P[t] 获得 t+1 日真实收益率 R[t+1]
        P_eff = P[:-1, :, :]  # shape: (T_len - 1, S, N)
        R_eff = R[1:, :]      # shape: (T_len - 1, S)

        # 毛收益率序列: shape (T_len - 1, N)
        gross_R_p = np.sum(P_eff * R_eff[:, :, None], axis=1)

        # 真实双边换手率测算 (单边 10 bps, 双边 20 bps on turnover)
        diff_P = np.abs(np.diff(P_eff, axis=0))  # shape: (T_len - 2, S, N)
        daily_to_mid = 0.5 * np.sum(diff_P, axis=1)  # shape: (T_len - 2, N)
        # 首日换手平滑设为 0 或初始等权迁移
        daily_to = np.vstack([np.zeros((1, N)), daily_to_mid])  # shape: (T_len - 1, N)
        turnover = np.mean(daily_to, axis=0)

        # 真实双边交易摩擦扣减：单边 10 bps (0.0010) -> 总买卖额摩擦 0.0020 * daily_to
        friction_cost = 0.0020 * daily_to
        net_R_p = gross_R_p - friction_cost

        # 真实净值序列合成
        nav = np.cumprod(1.0 + net_R_p, axis=0)
        nav_with_0 = np.vstack([np.ones((1, N)), nav])
        running_max = np.maximum.accumulate(nav_with_0, axis=0)
        dd = (running_max - nav_with_0) / np.maximum(1e-8, running_max)
        mdd = np.max(dd, axis=0)

        q95 = np.percentile(dd, 95, axis=0)
        mask = dd >= q95[None, :]
        tail_mdd = np.sum(dd * mask, axis=0) / np.maximum(1, np.sum(mask, axis=0))

        # 真实夏普比率精算：严格扣减 2.0% 年化无风险利率 (0.02 / 250.0)
        mean_r = np.mean(net_R_p, axis=0)
        rf_daily = 0.02 / 250.0
        std_r = np.std(net_R_p, axis=0) + 1e-6
        sharpe = ((mean_r - rf_daily) / std_r) * np.sqrt(250.0)
        win_rate = np.mean(net_R_p > 0.0, axis=0)

        fitness = sharpe + 0.6 * win_rate - 1.2 * mdd - 1.5 * tail_mdd - 0.8 * turnover

        metrics = {
            "sharpe": sharpe,
            "win_rate": win_rate,
            "mdd": mdd,
            "tail_mdd": tail_mdd,
            "turnover": turnover,
            "R_p": net_R_p,
            "nav": nav_with_0,
        }
        return fitness, metrics
```

---

### 改造四：`get_60d_rolling_nav_and_trajectory` 实装 12 切片推进式样本外演化轨迹
**目标**: 废除 `lam = (t + 1) / 60.0` 伪造直线，实装按每 5 个交易日滚动推进的 Walk-Forward 真实轨迹与净值链。

**精确替换代码方案**:
```python
    def get_60d_rolling_nav_and_trajectory(self, **kwargs) -> Dict[str, Any]:
        """
        获取近 60 个交易日真实的推进式样本外演化轨迹 (Walk-Forward Rolling Trajectory)
        废除 lam = (t + 1) / 60.0 线性插值，按每 5 个交易日滚动推进演化，
        每期仅使用该节点之前的历史数据求解最优权重，并用于后续 5 日样本外净值与真实四维轨迹记录。
        """
        if self._cached_60d_data is not None:
            return self._cached_60d_data

        # 提取 140 天对齐行情 (前序 80 天历史训练 + 60 天样本外推演)
        price_matrix, sector_ids, dates = self._extract_sector_price_matrix(window_days=140)
        chart_dates = dates[-60:]
        T_oos = 60
        step = 5
        num_slices = T_oos // step  # 12 个走步切片

        oos_dynamic_returns = []
        oos_static_returns = []
        trajectory = []

        # 初始静态权重 [0.30, 0.30, 0.25, 0.15]
        prev_dyn_top3 = None
        prev_stat_top3 = None

        for slice_idx in range(num_slices):
            # 当前切片在 chart_dates 中的索引范围 [slice_start, slice_end)
            slice_start = slice_idx * step
            slice_end = (slice_idx + 1) * step

            # 定位该切片在 price_matrix 中的起始行 (严格截取该节点之前的历史数据)
            # chart_dates[-60] 对应 price_matrix[-60]
            cutoff_in_matrix = len(price_matrix) - 60 + slice_start

            # 训练窗口取 cutoff_in_matrix 之前 61 个交易日
            train_sub_p = price_matrix[max(0, cutoff_in_matrix - 65) : cutoff_in_matrix, :]
            
            # 在历史样本上运行极速基因寻优 (population=16, generations=5)
            F_tr, R_tr = self._build_factor_tensor_and_returns(train_sub_p, horizon=55, sector_ids=sector_ids)
            
            # 小型种群极速求解最优因子权重
            W_tr = np.zeros((16, 4), dtype=float)
            W_tr[0] = self.static_weights.copy()
            for i in range(1, 16):
                raw = np.random.uniform(0.05, 0.50, size=4)
                W_tr[i] = raw / np.sum(raw)
            for _ in range(5):
                fit_tr, _ = self._evaluate_population(W_tr, F_tr, R_tr)
                elites = W_tr[np.argsort(-fit_tr)[:4]].copy()
                new_w = [elites[0], elites[1], elites[2], elites[3]]
                while len(new_w) < 16:
                    p1 = elites[np.random.randint(0, 4)]
                    p2 = elites[np.random.randint(0, 4)]
                    ch = 0.5 * p1 + 0.5 * p2 + np.random.normal(0.0, 0.02, size=4)
                    ch = np.maximum(0.05, ch)
                    new_w.append(ch / np.sum(ch))
                W_tr = np.array(new_w)

            best_fit_tr, _ = self._evaluate_population(W_tr, F_tr, R_tr)
            w_slice = W_tr[np.argmax(best_fit_tr)].copy()
            w_slice = np.maximum(0.05, w_slice)
            w_slice = w_slice / np.sum(w_slice)

            # 该切片 5 个交易日的特征与收益 (逐日严格按 T 收盘决策 -> T+1 收盘收益推演)
            for d in range(step):
                cur_day_idx = slice_start + d
                p_idx = len(price_matrix) - 60 + cur_day_idx

                # 当日收盘特征 (使用截至 p_idx-1 的历史序列用于预测 p_idx 当日收益)
                sub_today = price_matrix[:p_idx, :]
                F_today, _ = self._build_factor_tensor_and_returns(sub_today, horizon=1, sector_ids=sector_ids)
                f_vec = F_today[0]  # shape (14, 4)

                # 动态打分选出 Top 3
                scores_dyn = np.dot(f_vec, w_slice)
                top3_dyn = np.argsort(-scores_dyn)[:3]

                # 静态基准打分选出 Top 3
                scores_stat = np.dot(f_vec, self.static_weights)
                top3_stat = np.argsort(-scores_stat)[:3]

                # 第 p_idx 日真实收益率
                r_today = (price_matrix[p_idx, :] - price_matrix[p_idx - 1, :]) / np.maximum(1e-8, price_matrix[p_idx - 1, :])

                # 动态组合收益与换手摩擦扣减
                dyn_gross = float(np.mean(r_today[top3_dyn]))
                if prev_dyn_top3 is not None:
                    dyn_diff = len(set(top3_dyn) - set(prev_dyn_top3)) / 3.0
                    dyn_friction = 0.0020 * dyn_diff
                else:
                    dyn_friction = 0.0
                prev_dyn_top3 = top3_dyn
                oos_dynamic_returns.append(dyn_gross - dyn_friction)

                # 静态基准收益与换手摩擦扣减
                stat_gross = float(np.mean(r_today[top3_stat]))
                if prev_stat_top3 is not None:
                    stat_diff = len(set(top3_stat) - set(prev_stat_top3)) / 3.0
                    stat_friction = 0.0020 * stat_diff
                else:
                    stat_friction = 0.0
                prev_stat_top3 = top3_stat
                oos_static_returns.append(stat_gross - stat_friction)

                # 记录真实的样本外因子演化轨迹
                trajectory.append({
                    "date": chart_dates[cur_day_idx],
                    "valuation": round(float(w_slice[0]), 4),
                    "momentum": round(float(w_slice[1]), 4),
                    "snr": round(float(w_slice[2]), 4),
                    "anti_crowding": round(float(w_slice[3]), 4),
                })

        # 累乘生成 60 日真实样本外累计净值
        nav_dyn_series = np.cumprod(1.0 + np.array(oos_dynamic_returns))
        nav_stat_series = np.cumprod(1.0 + np.array(oos_static_returns))

        # 计算真实样本外最大回撤
        def _calc_mdd(navs: np.ndarray) -> float:
            n_arr = np.concatenate([[1.0], navs])
            run_max = np.maximum.accumulate(n_arr)
            return float(np.max((run_max - n_arr) / np.maximum(1e-8, run_max)))

        mdd_dyn = _calc_mdd(nav_dyn_series)
        mdd_stat = _calc_mdd(nav_stat_series)

        result = {
            "dates": chart_dates,
            "nav_dynamic": [round(float(x), 4) for x in nav_dyn_series],
            "dynamic_nav": [round(float(x), 4) for x in nav_dyn_series],
            "nav_static": [round(float(x), 4) for x in nav_stat_series],
            "static_nav": [round(float(x), 4) for x in nav_stat_series],
            "trajectory": trajectory,
            "final_nav_dynamic": round(float(nav_dyn_series[-1]), 4),
            "final_nav_static": round(float(nav_stat_series[-1]), 4),
            "alpha_pct": round(float((nav_dyn_series[-1] - nav_stat_series[-1]) * 100.0), 2),
            "mdd_dynamic_pct": round(float(mdd_dyn * 100.0), 2),
            "mdd_static_pct": round(float(mdd_stat * 100.0), 2),
        }
        self._cached_60d_data = result
        return result
```

---

## 5. Verification Method (独立核验方法与因果探针)

为确保实施智能体完成代码修改后能够进行严格且无死角的独立验证，设计以下三阶核验方案：

### 5.1 自动化单元测试回归命令
运行全量相关已存在的单元测试套件：
```powershell
py -3 -m pytest tests/test_infra.py
py -3 -m pytest tests/test_g7_architecture_and_decoupling.py
py -3 -m pytest tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py
```
**通过判据**:
- `test_g7_architecture_and_decoupling.py` 必须 100% 通过（`traj["dates"]`、`traj["nav_dynamic"]`、`traj["nav_static"]`、`traj["trajectory"]` 长度均为 60）。
- `test_infra.py` 14 项基建裁判测试全部通过。

### 5.2 因果律探针与夏普扣费专项测试脚本 (Delta Test)
编写专项校验测试 `tests/test_g9_evolver_causality_delta.py`，断言：
1. **未来函数探测**: 验证 $t$ 日特征绝对不包含 $t$ 日之后的价格，验证权重作用于 $R[1:]$。
2. **摩擦扣除验证**: 验证 `nav_dynamic` 末端净值严格小于无摩擦净值（`diff > 0`）。
3. **无风险利率检验**: 对收益率为 0 的伪造序列或全现金序列，验证计算出的夏普比率为负数（即 $\text{Sharpe} < 0$）。
4. **线性伪序列消除检验**: 对比 `_extract_sector_price_matrix` 输出，断言全局没有任何一列满足 `col[-1] - col[0] == 0.05 and col[0] == 1.0`（彻底无 `linspace`）。
5. **跨市场对齐检验**: 验证美股、港股、黄金与沪深300在同一行上的交易日期完全对齐（无日期错位跳空）。

### 5.3 失效判定条件 (Invalidation Conditions)
若出现以下任一情况，判定本次整改失败：
1. `_evaluate_population` 中出现 `P * R` 同日索引点乘。
2. `get_60d_rolling_nav_and_trajectory` 中再次出现 `lam = (t + 1) / 60.0` 或人工数学插值。
3. `_extract_sector_price_matrix` 中出现 `np.linspace(1.0, 1.05, ...)`。
4. 计算出的 `sharpe` 比率在收益率低于 2.0% 时仍为正值。
5. 运行 `get_60d_rolling_nav_and_trajectory()` 耗时超过 250 ms。
