# Scope & Project Specification: G6 Generation

## Architecture
- `AGY2_FundAdvisory/data_loader.py`: Realtime quote fetching and market flash news & catalysts parser (`fetch_realtime_market_news_and_catalysts`).
- `AGY2_FundAdvisory/advisory_engine.py`: `OpportunityRadarEngine` intraday K-line splicing + `OnlineHeuristicFactorEvolver` pure NumPy vectorized genetic evolutionary engine (<50ms) + dynamic factor weights replacing static 0.30/0.30/0.25/0.15.
- `AGY2_FundAdvisory/portfolio_optimizer.py`: C1~C5 target volatility ceilings (`TARGET_VOLATILITY_BY_TIER`) and `apply_target_volatility_risk_control`.
- `AGY2_FundAdvisory/portfolio_manager.py`: Dividend reinvestment vs cash dividend switching cost-benefit calculation for holdings >= 1 year (0.50% redemption fee + in-transit loss saved).
- `AGY2_FundAdvisory/app_gui.py`: Chart 1 twin-wing dashboard upgrade (Morning report pulse evidence chain, Top 3 sector cards with realtime change & 4D scores, Risk Patrol header cleanup & padding fix, Genetic Programming whitebox badge, Tab 1 & Tab 2 target vol and dividend rebalancing cards).
- `tests/test_g3_evolution_loop.py`: New comprehensive tests for G6 capabilities.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Intraday K-line Quote Splicing | Splice intraday price & change_pct to OpportunityRadarEngine K-line | M1 | Survey |
| 2 | Realtime Market News & Catalysts Fetcher | Eastmoney/Sina 7x24 flash news, 2s timeout, cache, keyword tagging | M1 | Survey |
| 3 | OnlineHeuristicFactorEvolver | NumPy vectorized rolling backtest over 60 trading days, 32 individuals, <50ms | M1 | Survey |
| 4 | Dynamic Factor Weight Integration | Replace lines 575-578 static weights with evolved weights & whitebox badge data | M1 | Survey |
| 5 | Target Volatility Risk Control | C1~C5 target vol ceilings, 20-day weighted rolling vol check, reduction to pure bond/cash | M2 | Survey |
| 6 | Dividend Reinvestment vs Cash Rebalance | Holdings >= 365 days, zero fee & zero transit friction savings calculation | M2 | Survey |
| 7 | Morning Report Pulse Upgrade | Second-precision timestamp, turnover volume, sentiment, 2-3 flash news items, quantitative stance | M3 | Survey |
| 8 | Top 3 Sector Cards Upgrade | Realtime intraday change pct, 4D factor score breakdown, selection rationale | M3 | Survey |
| 9 | Risk Patrol Header & Container Fix | Remove gray suffix `[主动风险预警哨 · 四维巡检升级版]`, fix container height & padding | M3 | Survey |
| 10 | Genetic Programming Whitebox Badge | Whitebox badge above Opportunity Radar showing 60d evolution, dynamic weights, OOS gain | M3 | Survey |
| 11 | Tab 1 & Tab 2 Risk & Dividend Cards | Target vol warning & reduction card, Tab 2 dividend cash switching advice card | M3 | Survey |
| 12 | Process Management & Restart | Clean 8501 process, clear Streamlit cache, clean start | M4 | Survey |
| 13 | Browser Visual Inspection | /browser multimodal walk-through in light, dark, 640px mobile viewports | M4 | Survey |
| 14 | Automated Test Suite Verification | tests/test_g3_evolution_loop.py new G6 tests, 100% pass across all 4 test suites | M5 | Survey |
| 15 | Read-Only & Cleanliness Verification | Verify 4 referee files zero diff, clean data/ledgers_index.json, no temp scripts | M5 | Survey |
| 16 | Documentation & Learning Isolation | Update root GEMINI.md & PROGRESS_LOG.md (zero touch to global config) | M5 | Survey |
| 17 | Git Versioning | Git add, commit G6, git tag v3.6-G6, git push HEAD and tags (NO RELEASE) | M5 | Survey |
| 18 | G7 Instruction Generation | Pure-text G7 directive starting with /goal /teamwork, satisfying all 4 rules | M5 | Survey |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Data & Advisory Core | Features 1, 2, 3, 4 (data_loader.py, advisory_engine.py) | Survey | IN_PROGRESS |
| M2 | Risk Control & Rebalancing | Features 5, 6 (portfolio_optimizer.py, portfolio_manager.py) | M1 contracts | PLANNED |
| M3 | GUI Front-end & Evidence Chain | Features 7, 8, 9, 10, 11 (app_gui.py) | M1, M2 | PLANNED |
| M4 | Process Restart & Visual Inspection | Features 12, 13 (8501 service, browser walk-through) | M3 | PLANNED |
| M5 | Test Suite, Audit, Git Tag & G7 | Features 14, 15, 16, 17, 18 (tests, audit, git, doc) | M4 | PLANNED |

## Interface Contracts
### data_loader.py ↔ advisory_engine.py
- `data_loader.fetch_realtime_market_news_and_catalysts(timeout: float = 2.0) -> Dict[str, Any]`
  Returns:
  ```python
  {
      "status": "success",
      "timestamp": "2026-11-07 22:05:00",
      "flash_news": [
          {"time": "...", "title": "...", "tags": ["macro", "csi_300"]},
          ...
      ],
      "summary_bullets": ["...", "..."],
      "market_turnover": {"sh": ..., "sz": ..., "total_str": "..."},
      "sentiment_ratio": float
  }
  ```
- `advisory_engine.OpportunityRadarEngine`:
  - `_calc_dynamic_sector_metrics()`: splices realtime quote `(1.0 + change_pct / 100.0) * s[-1]` as current bar.
  - `OnlineHeuristicFactorEvolver`:
    ```python
    class OnlineHeuristicFactorEvolver:
        def __init__(self, population_size: int = 32, n_generations: int = 8): ...
        def evolve(self, returns_matrix: np.ndarray, baseline_weights: np.ndarray) -> Dict[str, Any]:
            # returns dict: {"weights": np.ndarray [val, mom, snr, crowd], "oos_excess_sharpe": float, "generations": int, ...}
    ```
  - `OpportunityRadarEngine.get_evolution_badge_data() -> Dict[str, Any]`

### portfolio_optimizer.py ↔ app_gui.py
- `TARGET_VOLATILITY_BY_TIER = {"C1": 0.05, "C2": 0.08, "C3": 0.12, "C4": 0.16, "C5": 0.22}`
- `apply_target_volatility_risk_control(current_holdings: List[Dict], user_risk_tier: str = "C3") -> Dict[str, Any]`
  Returns:
  ```python
  {
      "is_over_budget": bool,
      "user_risk_tier": "C3",
      "target_vol": 0.12,
      "current_port_vol": 0.145,
      "reduction_ratio": 0.1724, # (0.145 - 0.12) / 0.145
      "reduction_plan": [
          {"code": "...", "name": "...", "current_weight": 0.20, "target_weight": 0.1655, "reduce_amount": ...},
      ],
      "transfer_target": {"code": "002351", "name": "易方达稳健收益债券B", "increase_amount": ...}
  }
  ```

### portfolio_manager.py ↔ app_gui.py
- `evaluate_dividend_cash_rebalancing(ledger_or_holdings) -> List[Dict[str, Any]]`
  Returns:
  ```python
  [
      {
          "code": "100032",
          "name": "富国中证红利指数A",
          "holding_days": 420,
          "eligible": True,
          "annual_dividend_est": 2600.0,
          "saved_redemption_fee": 13.0, # 0.50%
          "saved_transit_friction": 5.2, # 0.20%
          "total_saved": 18.2,
          "action_recommendation": "建议将分红方式设为【现金分红】，零摩擦派现再定投"
      }
  ]
  ```

## Code Layout
- `AGY2_FundAdvisory/data_loader.py`
- `AGY2_FundAdvisory/advisory_engine.py`
- `AGY2_FundAdvisory/portfolio_optimizer.py`
- `AGY2_FundAdvisory/portfolio_manager.py`
- `AGY2_FundAdvisory/app_gui.py`
- `tests/test_g3_evolution_loop.py`
- `GEMINI.md` (root)
- `PROGRESS_LOG.md` (root)
