# AGY2-FundAdvisory Technical Wiki & Whitepaper (v1.0.7)

<p align="center">
  <a href="WIKI.md"><strong>[ 简体中文 ]</strong></a> &nbsp;|&nbsp; <strong>[ English ]</strong>
</p>

This document is the official core system-level technical whitepaper and wiki for **AGY2-FundAdvisory (All-Weather Robo-Advisory & Public Fund Quant Takeover Platform v1.0.7)**.
It systematically details the system's architecture philosophy, Engineering Constitution v6.0, data lakehouse specifications, single-HTTP batch prefetch engine, dual-track independent valuation reconciliation, Combat-29 fund rebalance and tail sweeping models, 12D active risk sentry, derivatives arbitrage, micro-execution order scheduling, asset conservation accounting, 3-tier progressive UI/UX design standards, and automated verification gates.

---

## Table of Contents
1. [System Positioning & Commercial-Free Architecture](#1-system-positioning--commercial-free-architecture)
2. [Open High-Frequency Data Foundation & Sub-Second Batch Lakehouse](#2-open-high-frequency-data-foundation--sub-second-batch-lakehouse)
   - 2.1 Local High-Fidelity Lakehouse & Eradication of 34 Constants
   - 2.2 Single-HTTP Batch Prefetch Engine (`prefetch_batch_fund_quotes`)
   - 2.3 Official NAV Supremacy via Eastmoney Mobile Clearing API
   - 2.4 Dual-Track Valuation & Reconciliation Framework
   - 2.5 4-Decimal NAV Rounding & C-Class Continuous Daily Fees
   - 2.6 Feeder Fund Dynamic Beta Covariance Regression & Metadata Single Source of Truth
   - 2.7 Midnight Non-Trading Write Protection & Flat-Quotation Filtering
3. [Full-Stack 7 Institutional Quant Allocation Models & Formulations](#3-full-stack-7-institutional-quant-allocation-models--formulations)
   - 3.1 Robust Dual-Core HRP (Hierarchical Risk Parity)
   - 3.2 Core-Satellite Barbell Strategy
   - 3.3 All-Weather Risk Parity
   - 3.4 Black-Litterman (BL) Subjective/Objective View Fusion
   - 3.5 State-Conditional Win Rate Optimization
   - 3.6 Tail-Risk CVaR (Conditional Value-at-Risk)
   - 3.7 Half-Kelly Momentum Enhancement
   - 3.8 Percent Contribution to Risk (PCR %) & Loss-Constrained Sizing
   - 3.9 9 Asset Classes Brinson-Fachler 3D Performance Attribution
   - 3.10 10,000-Iteration Block Resampling Monte Carlo Stress Test (CVaR 99%)
   - 3.11 Out-of-Sample Dynamic Multi-Factor Weight Scoring & Causal Slicing
   - 3.12 Single-Fund Realized 20-Day Annualized Volatility Penetration
4. [Combat-29 Fund Ledger & Self-Consistent Rebalance Engine](#4-combat-29-fund-ledger--self-consistent-rebalance-engine)
   - 4.1 Real Investor Asset Ledger (`combat_29_funds`)
   - 4.2 Forced Sweeping of Fragmented Tail Positions (< 200 RMB)
   - 4.3 Pure Bond Anchor Deduplication & Merging (002351 vs. 000086)
   - 4.4 Semantic Isolation between Core Holdings (>= 500 RMB) and Tail Positions
   - 4.5 Automated Cost-Free C-to-A Share Class Conversion
5. [Twelve-Dimensional Active Risk Sentry (ActiveRiskSentry 12D)](#5-twelve-dimensional-active-risk-sentry-activerisksentry-12d)
   - 5.1 7-Day CSRC Penalty Fee & FIFO Pessimistic Batch Sizing
   - 5.2 Approaching Exemption Countdown Protection
   - 5.3 C-Class 30-Day Exemption Switch & Fee Ladder Warning
   - 5.4 Right-Side Breakdown & Trailing Peak Take-Profit (Bias20 Staged Profit Lock)
   - 5.5 Overbought Crowding & Mean-Reversion Penalty Discount
   - 5.6 Deep Loss (-12%) Sector Beta Mispricing vs. Manager Alpha Deterioration
   - 5.7 Sector & Fund Management Company Exposure Hard Caps (35%)
   - 5.8 Mini-Fund (< 50M RMB) Liquidation Risk Early Warning
   - 5.9 CSI 300 Trend Inflection Sentry
   - 5.10 Dynamic Correlation Mutation Defense (Ang & Chen 2002)
   - 5.11 Investor Suitability (C1~C5) Risk Tier Gradient & Volatility Reduction
   - 5.12 50ETF & 300ETF Put Option IV Surge (+30%) Anti-Crash Sentry
6. [Micro-Execution Scheduling, Derivatives Arbitrage & Asset Conservation](#6-micro-execution-scheduling-derivatives-arbitrage--asset-conservation)
   - 6.1 Dynamic Micro-Slippage Optimization (`calculate_vwap_execution_slippage`)
   - 6.2 On-Market ETF vs. Feeder 14:45 Intraday Discount/Premium Arbitrage
   - 6.3 Cross-Border QDII Premium & USD/CNH Forward Swap Point Hedging Cost Arbitrage
   - 6.4 Intra-Company Free Rapid Fund Conversion (Zero Drag & Fee Savings)
   - 6.5 Large-Amount DCA Multi-Day Volatility-Adaptive Order Scheduling
   - 6.6 In-Transit Order Asset Conservation Accounting Model
   - 6.7 14:30 Closing Intraday Valuation Abnormality Two-Way Alerts
7. [Occam's Razor & 3-Tier Progressive UI/UX Design System](#7-occams-razor--3-tier-progressive-uiux-design-system)
   - 7.1 Tier 1: Executive Verdict Bar (<= 110px)
   - 7.2 Tier 2: Folded Dual Analytical Drawers (Radar & 10D Quant Votes)
   - 7.3 Tier 3: Native Full-Width Reconciliation Expander & KPI Summary Cards
   - 7.4 Five Deep Chart Reading Guides (💡 How to Read + 🎯 Action Signal)
   - 7.5 Mobile Responsive 4-Column Layout (?view=mobile)
   - 7.6 Multimodal Screenshot OCR & Fast Candidate Search
8. [Automated Verification Gates & Anti-Cheating Invariants](#8-automated-verification-gates--anti-cheating-invariants)
   - 8.1 G28 Production-Readiness & Clean Debt Gate
   - 8.2 Four Read-Only Referee Files SHA256 Invariant
   - 8.3 G27 Routing & Reconciliation Verification
   - 8.4 G26 Valuation Calibration & Dual-Track Gate
   - 8.5 G25 Performance & Consistency Gate

---

## 1. System Positioning & Commercial-Free Architecture

### 1.1 Background & Decoupling from Commercial Intranets
Traditional institutional quantitative research platforms are heavily intertwined with commercial financial terminals (e.g., Wind Financial Terminal or Bloomberg). In open-source buy-side advisory, independent studios, and personal quant trading, these proprietary commercial dependencies pose fatal bottlenecks:
1. **Intranet IP & Machine Binding**: Cannot be easily deployed on standard personal computers, cloud Linux servers, or containerized headless runners;
2. **Single-Process Mutex Deadlocks**: Commercial desktop process locks frequently cause unexpected fatal crashes;
3. **Black-Box Data & Lookahead Bias**: Closed protocols hinder independent verification of split/dividend adjustments and cash drag calculations.

### 1.2 Modern Robo-Advisory System Philosophy (Engineering Constitution v6.0)
**AGY2-FundAdvisory v1.0.7** strictly establishes four guiding pillars:
- **Zero-Cheating Invariant**: Every metric and decision must be calculated dynamically via mathematical formulations; hardcoded constant results are strictly prohibited;
- **Official NAV Supremacy**: Evening official clearing NAV carries absolute authority; post-market valuation models are forbidden from overwriting authentic official figures;
- **Full Buy-Side Perspective**: Incorporates transaction friction, FIFO holding penalties, cash drag interest losses, and intra-company conversion channels into the objective function;
- **Occam's Razor Progressive Disclosure**: Eradicates text walls; delivers an executive verdict within 3 seconds while allowing layered on-demand access to deep quant analytics.

---

## 2. Open High-Frequency Data Foundation & Sub-Second Batch Lakehouse

### 2.1 Local High-Fidelity Lakehouse & Eradication of 34 Constants
- **Sample Coverage**: Encompasses daily total return series from January 2018 to December 2026 (~2,000 trading days) spanning broad-based equities, sectors, cross-border indices, commodities, and safe-haven bonds;
- **Zero Hardcoded Constants**: Eradicated all 34 historical hardcoded constants (e.g., `7.2385` for USD/CNH, `4.4200` for CGB 10Y, and `11569.50` for CSI Dividend Low Volatility baseline), connecting every formula directly to live APIs and offline Parquet lakehouse slices.

### 2.2 Single-HTTP Batch Prefetch Engine (`prefetch_batch_fund_quotes`)
In v1.0.7, the traditional N+1 serial network request bottleneck has been permanently solved:
- **Single Batch Request**: Leverages Eastmoney mobile API parameter `Fcodes=code1,code2,...` to retrieve the latest NAV and live intraday quotes for all 29 funds in a **single HTTP request (< 0.3s)**;
- **Thread Pool Concurrency**: Non-cached items are concurrently fetched via `ThreadPoolExecutor`, writing to disk only once at the conclusion of the batch;
- **Sub-Second Performance**: Full portfolio synchronization, NAV updating, and intraday PnL reconciliation is compressed to **0.95 seconds** (< 1.5s hard gate).

### 2.3 Official NAV Supremacy via Eastmoney Mobile Clearing API
- Official NAV date (`PDATE` / `jzrq`) must satisfy `>= latest_completed_trade_str` (the latest closed trading day computed from the authentic China trading calendar);
- Upon meeting this condition, the holding is flagged as `is_official_nav = True`, directly adopting official NAV and daily return rate;
- **Absolute Prohibition**: Once `is_official_nav == True`, post-market valuation formulas are strictly prohibited from overwriting official figures.

### 2.4 Dual-Track Valuation & Reconciliation Framework
- **Intraday Window (09:30~15:00)**: Eastmoney `FundMNFInfo` (`GSZZL`) and Tiantian Fund `fundgz` serve as primary sources (`real_tiantian_live = True`);
- **Four-Tier Penetration Fallback**: Only activated when official valuation centers lack coverage (index tracking, pure bonds, QDII FX translation, and top-10 stock weighting);
- **Evening Reconciliation**: Intraday estimates are archived to evaluate fund-by-fund Mean Absolute Error (MAE) and root-cause attribution (e.g., cash drag, FX timezone differences, manager active alpha divergence).

### 2.5 4-Decimal NAV Rounding & C-Class Continuous Daily Fees
- Daily return rates are calculated strictly following the official 4-decimal NAV rounding convention (e.g., `0.9343`);
- For C-class shares, continuous sales service fee deductions (0.20%~0.40% annually, ~0.1 to 0.15 bps/day) are factored into performance calculations.

### 2.6 Feeder Fund Dynamic Beta Covariance Regression & Metadata Single Source of Truth
- Fixed dead code in `get_calibrated_feeder_beta`, added `fund_name` parameter to correctly identify feeder funds;
- Implemented in-memory caching (`_DAILY_ALIGNED_RETURNS_MEM_CACHE`) for aligned return matrices;
- Relocated secondary bond `018757` from equity index mappings into `SECONDARY_BOND_CODES`.

### 2.7 Midnight Non-Trading Write Protection & Flat-Quotation Filtering
- From `00:00 to 09:34`, disk archive write operations are strictly blocked to prevent dirty snapshot overwrites;
- Intraday writes require `abs(est_gszzl) > 1e-6` to eliminate flat-quotation noise.

---

## 3. Full-Stack 7 Institutional Quant Allocation Models & Formulations

### 3.1 Robust Dual-Core HRP (Hierarchical Risk Parity)
Resolves Markowitz mean-variance matrix inversion instability across correlated assets:
1. **Hierarchical Tree Clustering**: Constructs a tree based on correlation distance $d_{i,j} = \sqrt{\frac{1 - \rho_{i,j}}{2}}$;
2. **Matrix Quasi-Diagonalization**: Reorders covariance matrix so correlated assets cluster along the diagonal;
3. **Recursive Bisection & Downside CVaR Weighting**: Allocates capital top-down using subset variance and downside 95% CVaR.

### 3.2 Core-Satellite Barbell Strategy
- **Core Anchor (70%~80%)**: Pure bonds and high-dividend low-volatility assets generating stable coupon cash flows;
- **Satellite Alpha (20%~30%)**: Technology, semiconductors, and overseas QDII capturing market momentum and alpha.

### 3.3 All-Weather Risk Parity
Enforces equal marginal risk contribution across all constituent assets:
$$\text{RC}_i = w_i \frac{(\Sigma w)_i}{\sqrt{w^T \Sigma w}} = \frac{1}{N} \sigma_p$$
Balances portfolio performance across growth and inflation economic regimes.

### 3.4 Black-Litterman (BL) Subjective/Objective View Fusion
Blends reverse-optimized market equilibrium prior $\Pi = \lambda \Sigma w_{\text{mkt}}$ with views $Q$ derived from 14-sector quant thermometers:
$$E(R) = \left[(\tau \Sigma)^{-1} + P^T \Omega^{-1} P\right]^{-1} \left[(\tau \Sigma)^{-1} \Pi + P^T \Omega^{-1} Q\right]$$

### 3.5 State-Conditional Win Rate Optimization
Matches the current macro 5D state $\mathbf{x}_{T_{\text{now}}} = [\text{ERP}, \text{Bias}_{20}, \text{DR007}, \text{iVIX}, \text{Turnover}]$ with historical regimes using Gaussian kernel similarity:
$$K(\mathbf{x}, \mathbf{x}_t) = \exp\left(-\frac{\|\mathbf{x} - \mathbf{x}_t\|^2}{2\sigma^2}\right)$$
Solves for weights that maximize 1-year rolling target achievement probability.

### 3.6 Tail-Risk CVaR (Conditional Value-at-Risk)
Minimizes expected loss beyond the VaR threshold at confidence $\alpha = 95\%$:
$$\min_{w} \text{CVaR}_\alpha(w) = \min_{w} \left( \zeta + \frac{1}{1-\alpha} \frac{1}{T} \sum_{t=1}^T \max(0, -w^T r_t - \zeta) \right)$$

### 3.7 Half-Kelly Momentum Enhancement
Controls leverage using Kaufman's Efficiency Ratio $\text{ER}_{20} = \frac{|\Delta P_{20}|}{\sum |\Delta P_1|}$:
$$f^* = \frac{1}{2} \cdot \frac{p \cdot b - q}{b} \cdot \text{ER}_{20}$$

### 3.8 Percent Contribution to Risk (PCR %)
$$\text{PCR}_i = \frac{w_i (\Sigma w)_i}{w^T \Sigma w} \times 100\%, \quad \sum_{i=1}^N \text{PCR}_i = 100.0\%$$

### 3.9 9 Asset Classes Brinson-Fachler 3D Performance Attribution
Decomposes excess return orthogonally into:
- **Allocation Effect**: $Q_{\text{alloc}} = \sum (w_i - W_i)(R_i^{\text{bm}} - R^{\text{bm}})$;
- **Selection Effect**: $Q_{\text{select}} = \sum W_i (r_i - R_i^{\text{bm}})$;
- **Interaction & Savings**: $Q_{\text{inter}}$, incorporating intra-company fee waivers and FIFO penalty avoidance;
- Identity: $R_{\text{portfolio}} - R_{\text{benchmark}} = Q_{\text{alloc}} + Q_{\text{select}} + Q_{\text{inter}}$.

### 3.10 10,000-Iteration Block Resampling Monte Carlo Stress Test
Circular Block Bootstrap (10-day block length) preserving autocorrelation and volatility clustering:
- Enforces $\text{CVaR}_{99\%} \ge \text{VaR}_{99\%} \ge \text{VaR}_{95\%}$;
- Overlays non-linear liquidity discounts based on underlying ADV/AUM metrics.

### 3.11 Out-of-Sample Dynamic Multi-Factor Weight Scoring & Causal Slicing
Evaluates performance strictly on historical data prior to day $d$ ($F_{\text{prev}}[-1, :, :]$) minus two-way 20 bps turnover friction.

### 3.12 Single-Fund Realized 20-Day Annualized Volatility Penetration
Calculates 20-day realized volatility $\sigma_{\text{ann}}$ directly from offline lakehouse returns, spanning pure bonds (~1.6 bps) to technology equities (~42.8 bps).

---

## 4. Combat-29 Fund Ledger & Self-Consistent Rebalance Engine

### 4.1 Real Investor Asset Ledger (`combat_29_funds`)
- Fully supports user authentic 29-fund portfolio with real share counts, cost bases, and market valuations;
- Strictly complies with the Anti-Cheating Invariant: modifying authentic holdings to fit test assertions is forbidden.

### 4.2 Forced Sweeping of Fragmented Tail Positions (< 200 RMB)
- Tail positions with market value $< 200$ RMB meeting the 7-day exemption (19 funds) are strictly assigned a 0.00% target weight;
- Action locked to "🧹 Sweep Tail" (SELL), forbidding counter-trend add-ons.

### 4.3 Pure Bond Anchor Deduplication & Merging (002351 vs. 000086)
- When holding core anchor `002351` (E Fund Yuxiang Return), redundant targets (`000086`) automatically have their target weight merged into `002351`;
- Prevents redundant opening of new bond positions.

### 4.4 Semantic Isolation between Core Holdings (>= 500 RMB) and Tail Positions
- Core holdings undergoing reductions are strictly labeled as "➖ Reduce Position";
- "Sweep Tail" label is strictly reserved for holdings $< 500$ RMB.

### 4.5 Automated Cost-Free C-to-A Share Class Conversion
- Identifies C-class holdings held $\ge 30$ days (`011613` STAR 50C);
- Generates zero-fee switch instructions into `011612` (A-class), terminating continuous sales service fee erosion.

---

## 5. Twelve-Dimensional Active Risk Sentry (ActiveRiskSentry 12D)

### 5.1 7-Day CSRC Penalty Fee & FIFO Pessimistic Batch Sizing
- CSRC regulation enforces a 1.50% penalty on mutual fund shares redeemed within 7 days;
- FIFO sizing evaluates `min(holding_days)` across batches;
- Sets rebalance lower bound to locked shares, preventing automated sales of penalized batches.

### 5.2 Approaching Exemption Countdown Protection
Alerts "1~2 days countdown" when holdings are at days 5~6, preventing premature redemptions.

### 5.3 C-Class 30-Day Exemption Switch & Fee Ladder Warning
Guides switching to zero-fee A-class anchors when holding duration exceeds 30 days.

### 5.4 Right-Side Breakdown & Trailing Peak Take-Profit (Bias20 Staged Profit Lock)
Issues `TAKE_PROFIT` signal when $\text{Bias}_{20} > 6.0\%$ during technical rallies, locking 40% profits.

### 5.5 Overbought Crowding & Mean-Reversion Penalty Discount
Applies mean-reversion discounts when sector crowding scores exceed 85.

### 5.6 Deep Loss (-12%) Sector Beta Mispricing vs. Manager Alpha Deterioration
Distinguishes between systemic sector downturns (hold patient) and fund manager alpha breakdown (reallocate).

### 5.7 Sector & Fund Management Company Exposure Hard Caps (35%)
Caps single fund management company or high-beta tech exposure at 35.0%.

### 5.8 Mini-Fund (< 50M RMB) Liquidation Risk Early Warning
Flags funds with consolidated AUM $< 50\text{M RMB}$ for priority liquidation.

### 5.9 CSI 300 Trend Inflection Sentry
Monitors CSI 300 relation to MA20/MA60 to adjust offensive/defensive postures.

### 5.10 Dynamic Correlation Mutation Defense (Ang & Chen 2002)
Triggers hedging reallocation into pure bonds and gold when dividend and high-beta correlation exceeds 0.80 during market downturns.

### 5.11 Investor Suitability (C1~C5) Risk Tier Gradient
Enforces equity allocation ceilings matching C1~C5 suitability profiles.

### 5.12 50ETF & 300ETF Put Option IV Surge (+30%) Anti-Crash Sentry
Emits red crash hedge alerts when put option IV surges >30% over historical volatility below MA20.

---

## 6. Micro-Execution Scheduling, Derivatives Arbitrage & Asset Conservation

### 6.1 Dynamic Micro-Slippage Optimization (`calculate_vwap_execution_slippage`)
Analyzes 14:45~15:00 VWAP to calculate dynamic execution savings in basis points (bps).

### 6.2 On-Market ETF vs. Feeder 14:45 Intraday Discount/Premium Arbitrage
- Premium $> +1.0\%$: Buy OTC feeder fund at 15:00 NAV to avoid secondary market bubbles;
- Discount $< -1.0\%$: Purchase discounted ETF on-market;
- Band $[-1.0\%, +1.0\%]$: Hold neutral.

### 6.3 Cross-Border QDII Premium & USD/CNH Forward Swap Point Hedging Cost Arbitrage
Calculates forward hedge prices $F = S + \text{swap\_points}/10000$ and net annualized yield enhancements.

### 6.4 Intra-Company Free Rapid Fund Conversion
Routes rebalancing through intra-company conversions (`PRIORITY_1_SWITCH`), saving 3.5 days of cash drag and redemption friction.

### 6.5 Large-Amount DCA Multi-Day Volatility-Adaptive Order Scheduling
Splits orders $> 10,000$ RMB across 3 to 5 trading days based on 20-day volatility $\sigma_{\text{day}}$.

### 6.6 In-Transit Order Asset Conservation Accounting Model
Enforces total equity conservation across pending orders:
$$\text{Total Equity}_{\text{post}} = \text{Total Equity}_{\text{pre}} - \text{Estimated Fees}$$

### 6.7 14:30 Closing Intraday Valuation Abnormality Two-Way Alerts
Anti-chasing and golden-pit dip buying guidance.

---

## 7. Occam's Razor & 3-Tier Progressive UI/UX Design System

### 7.1 Tier 1: Executive Verdict Bar (<= 110px)
- 1-line macroeconomic verdict;
- Position causal formula;
- 5 concise capsules ($\le 20$ characters) delivering daily operational stance in 3 seconds.

### 7.2 Tier 2: Folded Dual Analytical Drawers
- **Drawer 1**: Top 3 Opportunities & Active Risk Radar;
- **Drawer 2**: 10D Quant Consensus Votes & Historical Inflection Ruler.

### 7.3 Tier 3: Native Full-Width Reconciliation Expander & KPI Summary Cards
- Relocated from popover into native wide-screen `st.expander`;
- Top KPI summary cards for published counts, MAE, dual-source spread, and 4-dec rounding.

### 7.4 Five Deep Chart Reading Guides
Two-line reading capsules (`💡 How to Read` + `🎯 Action Signal`) directly above key Plotly charts with transparent floating legends.

### 7.5 Mobile Responsive 4-Column Layout (?view=mobile)
Adapts complex desktop tables into 4-column simplified tables and 2x2 metric grids, eliminating horizontal scrollbars and `ValueError` unpacking errors.

### 7.6 Multimodal Screenshot OCR & Fast Candidate Search
Supports camera/screenshot slice OCR recognition with match confidence warnings (`<0.85` flagged in yellow).

---

## 8. Automated Verification Gates & Anti-Cheating Invariants

### 8.1 G28 Production-Readiness & Clean Debt Gate
- `verify_g28_production_readiness.py`: Verifies dynamic Beta, 10D neutrality, wide expander, and chart reading guides;
- `verify_g28_clean_debt_gate.py`: Scans entire codebase confirming zero hardcoded constants.

### 8.2 Four Read-Only Referee Files SHA256 Invariant
`verify_readonly_hashes.py` verifies:
- `judge_engine.py`: `76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF31CC07BE`
- `holdout_vault.py`: `88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670BD031D2A`
- `AGENT_SPEC.md`: `A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B800CD63957`
- `tests/test_infra.py`: `48BEE0DA300D7C0A0848EC1376E4B9B2E55224D2736081713B4340F0362CD100`

### 8.3 G27 Routing & Reconciliation Verification
Validates live multi-source routing with 29-fund reconciliation MAE strictly $< 20$ bps and green-light compliance $\ge 70\%$.

### 8.4 G26 Valuation Calibration & Dual-Track Gate
Validates 4-decimal rounding, C-class daily fee deduction, index benchmark mapping, and dual-track non-overwriting.

### 8.5 G25 Performance & Consistency Gate
Validates 29-fund batch refresh latency $< 1.5$ seconds (actual 0.95s), pure bond deduplication, and tail position sweeping.

---

*AGY2-FundAdvisory Quantitative Research Team · Release Date: 2026-11-19*
