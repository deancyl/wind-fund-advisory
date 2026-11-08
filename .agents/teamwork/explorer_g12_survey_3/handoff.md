# G12 Survey & Deep Diagnosis Handoff Report: 7D GP Factor Evolver, Real-Time Cross-Section Injection, and UI/Engine Audit

- **Date**: 2026-11-08T15:15:00Z
- **Author**: `teamwork_explorer`
- **Scope**: G12 Generation Survey Phase
- **Focus**:
  1. `OnlineHeuristicFactorEvolver` 7D GP Upgrade & Real-Time Cross-Section Injection
  2. Double-Wing Popover 🧬 Factor Evolution Visualization in `app_gui.py`
  3. Deep Code Diagnosis & Audit Synthesis (`agy2 (1).md` & `agy2_fundadvisory_deep_code_diagnosis.md`)
  4. Four Code Circuit Bugs & Risk Sentry Wiring in `app_gui.py` and `advisory_engine.py`

---

## 1. Observation

### 1.1 `OnlineHeuristicFactorEvolver` Current Implementation
- **File**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\advisory_engine.py`
  - **Lines 247–271**: `class OnlineHeuristicFactorEvolver` initialization:
    ```python
    self.population_size = max(16, int(population_size))
    self.generations = max(5, int(generations))
    self.random_seed = random_seed
    self.static_weights = np.array([0.30, 0.30, 0.25, 0.15], dtype=float)
    ```
    Chromosome size is strictly 4D: `w = [w_val, w_mom, w_snr, w_crowd]`.
  - **Lines 272–386**: `_extract_sector_price_matrix(window_days: int = 140)`:
    Purely reads historical Parquet files (`aligned_matrix_total_return.parquet`, fallback parquets, nav caches). Does **not** accept `realtime_quotes` or append today's intraday price at the sequence tail. If today is intraday, the price matrix ends at yesterday's close.
  - **Lines 387–468**: `_build_factor_tensor_and_returns(price_matrix, horizon, sector_ids)`:
    Constructs `F` of shape `(horizon, S_num, 4)` and `R` of shape `(horizon, S_num)`.
    Channel 0: `s_val` (long-term valuation percentile)
    Channel 1: `s_mom` (20-day MA20 bias & slope)
    Channel 2: `s_er` (20-day Kaufman efficiency ratio / SNR)
    Channel 3: `s_crowd` (anti-crowding score, 42 to 96)
  - **Lines 469–534**: `_evaluate_population(pop, F, R)`:
    Calculates `scores = np.einsum("tsd,kd->tsk", F, pop)` where `pop` is `(N, 4)`.
    Enforces lag-1 causal alignment `P_eff = P[:-1, :, :]`, `R_eff = R[1:, :]`.
    Deducts 20 bps round-trip turnover friction: `friction_cost = 0.0020 * daily_to`.
    Deducts 2.0% annual risk-free rate: `(mean_r - 0.02 / 250.0) / std_r * np.sqrt(250.0)`.
  - **Lines 535–632**: `evolve_factor_weights`:
    Evolves 4D weights across `lookback_days=60` and returns:
    `"weights": best_w_list` (4 elements), `"weights_dict"`, `"sharpe"`, `"mdd"`, `"turnover"`, `"elapsed_ms"`.
  - **Lines 633–765**: `get_60d_rolling_nav_and_trajectory`:
    Runs 12 Walk-Forward slices ($12 \times 5 = 60$ days), records 4D weights trajectory.
  - **Lines 776–779**: `OpportunityRadarEngine.__init__`:
    ```python
    self.evolver = OnlineHeuristicFactorEvolver()
    self.evolved_result = self.evolver.evolve_factor_weights()
    self.factor_weights = self.evolved_result["weights"]
    ```
    Note: `self.realtime_quotes` is loaded in line 774, but is NOT passed to `evolve_factor_weights`.

### 1.2 Popover Factor Evolution Visualization in `app_gui.py`
- **File**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py`
  - **Lines 2800–2814**:
    ```python
    with col_rad_head2:
        with st.popover(f"🧬 因子进化: 估{w_factors[0]*100:.0f}% 动{w_factors[1]*100:.0f}% 噪{w_factors[2]*100:.0f}% 拥{w_factors[3]*100:.0f}%", use_container_width=True):
            st.markdown("##### 🧬 在线启发式因子基因自适应进化算子")
            st.caption("基于 14 大赛道真实 60 日收益与特征张量，纯 NumPy 向量化演化，严格约束换手率与回撤。")
            traj_data = radar_engine.evolver.get_60d_rolling_nav_and_trajectory()
            c_m1, c_m2, c_m3 = st.columns(3)
            c_m1.metric("超额 Alpha", f"{traj_data.get('alpha_pct', 0.0):+.2f}%")
            c_m2.metric("最大回撤", f"-{traj_data.get('mdd_dynamic_pct', 0.0):.2f}%")
            c_m3.metric("换手率惩罚", f"-{evo_res.get('turnover', 0.0):.1f}%")
            df_traj = pd.DataFrame({
                "日期": traj_data.get("dates", [])[-15:],
                "动态净值": traj_data.get("nav_dynamic", [])[-15:],
                "静态基准": traj_data.get("nav_static", [])[-15:],
            })
            st.line_chart(df_traj.set_index("日期"))
    ```
    Currently lacks:
    1. Market emergency state mode recognition (`smooth`, `vol_pulse`, `panic_oversold`).
    2. Evolved optimal rule expressions.

### 1.3 Four Circuit Bugs Directly Observed in Code
- **Bug 1: Right-wing correlation mutation card false-negative dead circuit**
  - **File**: `AGY2_FundAdvisory/app_gui.py`, Line 2987:
    `if corr_eval_res.get("is_mutation_alarm") or corr_eval_res.get("is_regime_shift_risk"):`
  - **File**: `AGY2_FundAdvisory/portfolio_manager.py`, Lines 8627–8645:
    `evaluate_dynamic_correlation_mutation` returns keys:
    `"is_triggered"`, `"is_liquidity_shift_triggered"`, `"alert_level"`, `"status": "MUTATION_ALERT"`.
    It **never** returns `"is_mutation_alarm"` or `"is_regime_shift_risk"`. Thus the alarm card never renders when correlation jumps!
- **Bug 2: Sentry inspection missing parameters in `app_gui.py` causing Dimension 8 & 9 dead circuits**
  - **File**: `AGY2_FundAdvisory/app_gui.py`, Line 2725:
    `sentry_rep = sentry.inspect_portfolio(pm_instance.holdings, snapshot_dict, fund_metadata=_f_metas)`
  - **File**: `AGY2_FundAdvisory/advisory_engine.py`, Line 1947:
    Dimension 8 (investor suitability check) checks `investor_risk_tier or snapshot.get("investor_risk_tier")`. Because neither was passed, Dimension 8 was completely skipped.
  - **File**: `AGY2_FundAdvisory/advisory_engine.py`, Line 2041:
    Dimension 9 (intraday valuation swing & cushion consumption) checks `snapshot.get("fund_quotes") or snapshot.get("realtime_quotes")`. Because `snapshot_dict` had no `fund_quotes`, Dimension 9 was completely skipped.
- **Bug 3: Index & ETF feeder fund intraday valuation tracking error**
  - Feeder funds (联接基金) and index funds were relying solely on delayed quarterly top 10 holdings from Tiantian Fund, rather than anchoring to the realtime index/ETF quote with a 0.95 exposure factor.
- **Bug 4: Smart DCA multiplier target alignment**
  - `SmartExecutionDCAEngine.plan_smart_dca` defaulted to CSI 300's bias instead of aligning with the target portfolio's weighted bias & ERP.

### 1.4 Test Suite Baseline Verification
- We executed the following test commands synchronously and verified pass rates:
  - `py -3 -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py`: **50 passed in 98.14s**.
  - `py -3 -m pytest tests/test_causality_adversarial_m1.py tests/test_g9_causal_brinson_and_suitability.py tests/test_g7_architecture_and_decoupling.py`: **19 passed in 3.93s**.
  - `py -3 -m pytest tests/test_g10_correlation_liquidity_and_stress.py`: **6 passed in 22.01s**.
- **Crucial Existing Test Assertions to Respect**:
  - `tests/test_g7_architecture_and_decoupling.py:42`:
    `assert len(res.get("weights", [])) == 4`
    `assert len(radar.factor_weights) == 4`
    `assert res.get("elapsed_ms") < 250.0`
    `assert len(traj.get("dates")) == 60`
    `assert len(traj.get("trajectory")) == 60`
  - `tests/test_causality_adversarial_m1.py:141-155`:
    Passes 4D population `pop = np.array([[0.3, 0.3, 0.25, 0.15], ...])` into `_evaluate_population(pop, F, R)` and expects 4D einsum compatibility!
  - `tests/test_adv_final_closure.py:39`:
    Asserts `pm.classify_fund_asset_class("002351") != "其他权益资产"`.

---

## 2. Logic Chain

### 2.1 Why 7D GP Upgrade is Required
1. *Observation 1.1*: The current `OnlineHeuristicFactorEvolver` searches only a 4-dimensional linear simplex $w_0 + w_1 + w_2 + w_3 = 1$.
2. *Audit Reference (`agy2 (1).md` & `agy2_fundadvisory_deep_code_diagnosis.md`)*: Linear weights on 60-day smoothed indicators are completely blind to intraday flash crashes, volume explosions, or sudden volatility spikes.
3. *Logic*: To handle extreme shocks without breaking the linear base, the chromosome must be expanded to 7 dimensions:
   - **Genes 0–3**: Base factor weights $[w_{\text{val}}, w_{\text{mom}}, w_{\text{snr}}, w_{\text{crowd}}]$ where $\sum_{i=0}^3 w_i = 1.0$ and $w_i \ge 0.05$.
   - **Gene 4 ($g_{\text{adapt\_mom}} \in [0.0, 1.0]$)**: Adaptive momentum window parameter. Blends 5-day sharp capture momentum $s_{\text{mom\_5}}$ and 20-day trend momentum $s_{\text{mom\_20}}$:
     $$s_{\text{mom\_eff}} = (1 - g_{\text{adapt\_mom}}) \cdot s_{\text{mom\_20}} + g_{\text{adapt\_mom}} \cdot s_{\text{mom\_5}}$$
   - **Gene 5 ($g_{\text{vol\_thresh}} \in [1.2, 2.5]$)**: Volatility pulse penalty threshold. When short-term 5-day volatility spikes relative to 60-day baseline ($\text{VolRatio} = \sigma_5 / \sigma_{60} > g_{\text{vol\_thresh}}$), an exponential penalty decay is applied:
     $$\text{Decay}_{\text{vol}} = \exp\left(-1.5 \cdot \max(0.0, \text{VolRatio} - g_{\text{vol\_thresh}})\right)$$
     $$\text{Score}_{\text{penalized}} = \text{Score}_{\text{base}} \cdot \text{Decay}_{\text{vol}}$$
   - **Gene 6 ($g_{\text{safety\_boost}} \in [0.0, 1.0]$)**: Sudden drop flight-to-safety operator. When the broader market plunges intraday ($r_{\text{mkt}} \le -1.5\%$), safe haven assets (`pure_bond` and `domestic_gold`) receive an immediate additive score boost:
     $$\text{Boost}_{\text{safe}} = g_{\text{safety\_boost}} \cdot \frac{\max(0, -r_{\text{mkt}} - 0.01)}{0.02} \cdot 30.0 \cdot \mathbb{I}_{\text{safe}}$$

### 2.2 Real-Time Cross-Section Injection
1. *Observation 1.1*: Parquet data stores history up to $T_{\text{last}}$. Intraday prices are received in `realtime_quotes`.
2. *Logic*:
   - In `_extract_sector_price_matrix(window_days, realtime_quotes=None)`:
     If `realtime_quotes` is provided:
     For each of the 14 sectors, look up real-time price $p_{\text{today}}$ (using `change_pct` or valid `point`).
     Append today's row to `price_matrix` (or update the last row if today's date is already present).
   - In `_build_factor_tensor_and_returns`:
     Because `price_matrix[-1, :]` contains today's intraday price, the last return $R[-1, :]$ reflects today's real-time move, and `sub_p[-1, :]` incorporates today's intraday level.
     Thus, `F[-1, :, :]` reflects today's 5-day momentum, volatility ratio, and safe haven status!
   - *Causality Invariant*: In historical training slices, `P[:-1]` still acts on `R[1:]`. Intraday injection at the very tail allows today's evolved strategy to output today's decision for the upcoming session ($T+1$).

### 2.3 Dual 4D/7D Backwards Compatibility in `_evaluate_population`
1. *Observation 1.4*: Existing test `test_causality_adversarial_m1.py` passes 4D `pop` (`(N, 4)`) and 4D `F` (`(T, S, 4)`).
2. *Observation 1.4*: `test_g7_architecture_and_decoupling.py` asserts `len(res["weights"]) == 4`.
3. *Logic*:
   - In `_evaluate_population(pop, F, R)`:
     If `pop.shape[1] == 4`:
     Execute the original einsum: `scores = np.einsum("tsd,kd->tsk", F[:, :, :4], pop)`.
     If `pop.shape[1] == 7`:
     Execute the 7D vectorized tensor scoring (adaptive momentum + vol decay + safe boost).
   - In `evolve_factor_weights`:
     Return `"weights": best_w_list[:4]` (length 4, guaranteeing $100\%$ pass on existing tests).
     Return `"chromosome_7d": best_chrom_list` (length 7).
     Return `"operator_genes": {...}`.
     Return `"market_emergency_mode"` and `"evolved_rule_expression"`.
   - Elapsed time with NumPy vectorization: $< 30$ ms, well under 250 ms.

### 2.4 Popover UI Integration
1. *Observation 1.2*: Popover currently displays only 3 metrics and a line chart.
2. *Logic*:
   Inside `st.popover`:
   1. Keep button label compact: `f"🧬 因子进化: 估{w_factors[0]*100:.0f}% 动{w_factors[1]*100:.0f}% 噪{w_factors[2]*100:.0f}% 拥{w_factors[3]*100:.0f}%"`.
   2. At the top of the popover body:
      - Render **Market Emergency State Mode Recognition** badge:
        - `smooth`: `🟢 市场状态：平稳蓄势均衡态 (Smooth Regime)`
        - `vol_pulse`: `⚡ 市场状态：波动率脉冲防爆态 (Vol-Pulse Regime)`
        - `panic_oversold`: `🚨 市场状态：突发急跌避险态 (Flight-to-Safety Regime)`
      - Render **Evolved Optimal Rule Expression**:
        e.g. `Score = 0.28*Val + 0.32*Mom(5d:35%, 20d:65%) + 0.25*SNR + 0.15*Crowd - VolPulsePenalty(>1.70x) + SafeBoost(+25pts)`
   3. Below the rule, retain existing 3 metric cards (`超额 Alpha`, `最大回撤`, `换手率惩罚`) and 60d rolling NAV chart.
   This fulfills all G12 requirements without adding clutter or violating the 3-block architecture!

---

## 3. Caveats

1. **Read-Only Referees**:
   `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py` must never be touched.
   `DataLoader.simulate_execution` default signature and fee structure must remain intact.
2. **Global GEMINI.md Invariant**:
   All new learnings and rules must be written to the local `d:\Google\Workspace\Wind\GEMINI.md` and `PROGRESS_LOG.md`. Global `c:\Users\deanc\.gemini\GEMINI.md` is strictly forbidden.
3. **CommonMark 4+ Space Indented Block Leak (Rule 27)**:
   Any custom HTML injected into Streamlit must pass through `_clean_html(...)` and `safe_markdown_html(...)` to prevent raw HTML code leak.
4. **Offline Resilience**:
   When network is unreachable, `realtime_quotes` will be empty. The code must gracefully fall back to Parquet without throwing exceptions or generating NaN arrays.
5. **No Release Creation**:
   Git operations for G12 must strictly avoid creating GitHub Releases (`git tag -a v4.2-G12` only).

---

## 4. Conclusion & Implementation Blueprint

### 4.1 Proposed Implementation Plan

#### Step 1: `AGY2_FundAdvisory/advisory_engine.py` Upgrades
1. **Extend `OnlineHeuristicFactorEvolver`**:
   - `__init__`: Add `self.static_chromosome = np.array([0.30, 0.30, 0.25, 0.15, 0.30, 1.80, 0.35])`.
   - `_extract_sector_price_matrix`: Accept `realtime_quotes: Optional[Dict[str, Any]] = None`. When provided, append/update today's price row.
   - `_build_factor_tensor_and_returns`: Compute 7-channel tensor `F` (Val, Mom20, SNR, Crowd, Mom5, VolRatio, SafeAsset).
   - `_evaluate_population`: Vectorized support for both 4D (backward-compatible) and 7D (adaptive momentum, vol pulse penalty, safe boost).
   - `evolve_factor_weights`: Search 7D space ($N=32$, $G=15$), determine `market_emergency_mode`, format `evolved_rule_expression`, return both 4D `weights` and 7D metadata.
   - `get_60d_rolling_nav_and_trajectory`: Support 7D rolling Walk-Forward trajectory.
2. **Update `OpportunityRadarEngine`**:
   - In `__init__`, pass `self.realtime_quotes` to `self.evolver.evolve_factor_weights(realtime_quotes=self.realtime_quotes)`.
   - In `evaluate_sector`, incorporate 7D operator rules (adaptive momentum 5d/20d, vol penalty, safe boost).
3. **Upgrade `ActiveRiskSentry.inspect_portfolio` (Trailing Stop & Right-Side Break)**:
   - In Dimension 4, add:
     ① Right-side trend break profit lock: When `pnl_pct >= 10.0%` and `bias_20 < 0` and (`slope_20 < 0` or intraday plunge), issue red warning to lock 50% profit.
     ② High-water mark drawdown protection: When `pnl_pct >= 15.0%` and drawdown from 60d high $> 8.0%$, issue warning.

#### Step 2: `AGY2_FundAdvisory/app_gui.py` Fixes & UI Wiring
1. **Fix Circuit Bug 1**:
   Line 2987: Change `corr_eval_res.get("is_mutation_alarm") or corr_eval_res.get("is_regime_shift_risk")` to:
   `corr_eval_res.get("is_triggered") or corr_eval_res.get("is_liquidity_shift_triggered")`.
2. **Fix Circuit Bug 2**:
   Line 2725: Pass `investor_risk_tier=st.session_state.get("active_tier_val", "C3")`, and ensure `snapshot_dict["fund_quotes"] = fund_quotes` so Dimensions 8 & 9 are active.
3. **Enhance Popover 🧬**:
   In lines 2800–2814, add:
   - Market emergency state recognition badge (`smooth`, `vol_pulse`, `panic_oversold`).
   - Evolved optimal rule expression string.
   - Preserve existing metrics and line chart.

#### Step 3: Targeted Unit Tests
Create `tests/test_g12_factor_evolver_and_circuit_closure.py`:
- Test 1: Real-time cross section injection into `_extract_sector_price_matrix` & `_build_factor_tensor_and_returns`.
- Test 2: 7D chromosome evolution & vectorization speed ($< 250$ ms).
- Test 3: Backward compatibility of `_evaluate_population` with 4D `pop`.
- Test 4: Market emergency mode recognition under simulated normal, vol-pulse, and panic shock conditions.
- Test 5: Right-side trailing stop profit alert triggering in `inspect_portfolio`.
- Test 6: Circuit bug fixes validation (correlation mutation key alignment & sentry parameter passthrough).

---

## 5. Verification Method

To independently verify the survey findings and the proposed implementation:

1. **Check 4 Referee Files Immutability**:
   ```powershell
   git status --porcelain judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py
   ```
   Must output nothing (0 changes).

2. **Run Full Test Suite**:
   ```powershell
   py -3 -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py tests/test_causality_adversarial_m1.py tests/test_g9_causal_brinson_and_suitability.py tests/test_g7_architecture_and_decoupling.py tests/test_g10_correlation_liquidity_and_stress.py
   ```
   All tests must pass ($100\%$ green).

3. **Verify 7D Evolver Performance**:
   ```python
   from AGY2_FundAdvisory.advisory_engine import OnlineHeuristicFactorEvolver
   evolver = OnlineHeuristicFactorEvolver(population_size=32, generations=15)
   res = evolver.evolve_factor_weights(force_refresh=True)
   assert len(res["weights"]) == 4
   assert len(res["chromosome_7d"]) == 7
   assert res["elapsed_ms"] < 250.0
   assert res["market_emergency_mode"] in ["smooth", "vol_pulse", "panic_oversold"]
   ```

4. **Verify GUI Popover**:
   Start Streamlit service and verify `http://127.0.0.1:8501/_stcore/health`.
   Open popover `🧬 因子进化` and confirm:
   - Status badge displays correctly (no raw HTML leak).
   - Evolved rule expression is visible.
   - 60d rolling NAV chart renders cleanly.
