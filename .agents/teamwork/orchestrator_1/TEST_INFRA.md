# E2E Test Infra: Multi-Ledger & Anticheat Hardening Suite

## Test Philosophy
- Opaque-box and invariant-driven.
- Derive test cases directly from user requirements and acceptance criteria in ORIGINAL_REQUEST.md.
- Methodology: 4-Tier Testing + Specialized Anticheat Verification (Tests A, B, C, D).

## Feature Inventory & Test Mapping
| # | Feature | Requirement | Tier 1 (Unit/Isolated) | Tier 2 (Boundary/Negative) | Tier 3 (Integration/Pairwise) | Tier 4 (System/E2E Scenario) |
|---|---------|-------------|:----------------------:|:--------------------------:|:-----------------------------:|:----------------------------:|
| 1 | MultiLedgerManager CRUD | R1 | create, list, rename, delete | delete protected main_live fails | clone isolation (DB & json) | get_all_ledgers_summary math |
| 2 | 全站多账本热装配 | R2 | active_ledger_id binds pm | switch non-existent ledger fallback | switch updates card 4 & sentry | Tab 1 new ledger -> Tab 2 view |
| 3 | 四大实盘调仓场景 | R3 | new_cash_only / withdraw_cash_only | <7d locked funds zero redemption | freeze_reserved_cash deduction | cache signature recomputation |
| 4 | Tab 3 历史相似动态统计 | R4 | 60d win-rate, excess, MDD | top_k=3 data bounds check | 3 distinct attribution categories | AST no hardcoded 100.0% / +8.5% |
| 5 | Tab 4 穿透与资产精准分类 | R5 | holdings_override on 4 funcs | HoldingItem auto market_val | active_examine_holdings loop | 0% other equity assets |
| 6 | 14 赛道真动态雷达 | R6 | er_20, bias_20, slope, crowd | no sector == (0.50, 1.0, 85.0) | get_sector_valuation no pass | 14 sectors distinct values |
| 7 | 预警哨折叠聚合与紧凑 | R7 | >= 2 funds aggregate to 1 card | batch lock adds all to tab2_locked | container height <= 320px | single fund no aggregation |
| 8 | 物理安全红线与服务存活 | R8 | 4 judge files SHA256 invariant | simulate_execution signature intact | pytest 100% pass | AppTest light & dark 0 error |

## Specialized Anticheat Test Suite (tests/test_anticheat_suite.py)
- **Test A (14-Sector Genuine Dynamics)**:
  - Call `OpportunityRadarEngine().scan_all_sectors()`.
  - Assert no sector shares fallback tuple `(0.50, 1.0, 85.0)`.
  - Assert 14 sectors have distinct dynamic metrics.
- **Test B (Four Rebalancing Scenarios Realness)**:
  - Test `new_cash_only`: assert `all(sell == 0)` and `sum(buy) == new_cash_amount`.
  - Test `withdraw_cash_only`: assert `all(buy == 0)` and `sum(sell) == withdraw_cash_amount` and no `<7d` locked shares redeemed.
  - Test `freeze_reserved_cash`: assert reserved batch cash is deducted from available rebalance funds.
- **Test C (Multi-Ledger Isolation & Protection)**:
  - Create sandbox ledger, clone ledger, modify sandbox holdings.
  - Assert `portfolio_ledger.json` is unchanged.
  - Assert `delete_ledger("main_live")` raises `PermissionError` or returns `False`.
- **Test D (Tab 4 Look-Through Override & Asset Classification)**:
  - Call 4 penetration functions with custom `holdings_override`.
  - Assert results change dynamically.
  - Assert `classify_fund_asset_class` classifies healthcare (161726), liquor (161725), bank (160418), HK tech (013402), semiconductor (008888), QDII, dividends, broad indices, bonds, gold with 0% "其他权益资产".
