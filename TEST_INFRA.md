# E2E Test Infra: AGY2_FundAdvisory WindToolkit Integration

## Test Philosophy
- Opaque-box, requirement-driven. No dependency on implementation design.
- Methodology: Category-Partition + Boundary Value Analysis + Pairwise Combinatorial + Real-World Workload Testing.
- Read-only protection: absolutely zero modification or unlocking of `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `test_infra.py`.
- Zero regression: 100% pass on all existing 112 tests.

## Feature Inventory
| # | Feature | Source (requirement) | Tier 1 | Tier 2 | Tier 3 |
|---|---------|---------------------|:------:|:------:|:------:|
| 1 | Goodwill Ratio Screen (>30%) | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 2 | Double-High Fraud Screen | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 3 | Controlling Shareholder Pledge | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 4 | Lockup Expiration Calendar (30-90D) | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 5 | Fund Look-Through 3-Color Tags | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 6 | Portfolio Penetration Risk Index | ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ |
| 7 | OMO Net Injection/Drainage | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 8 | DR007 vs 7D OMO Spread (bp) | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 9 | Macro Liquidity Status (宽松/中性/收紧)| ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 10 | Dual-Track Macro Radar | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 11 | Extreme Tightening Defense | ORIGINAL_REQUEST §R2 | 5 | 5 | ✓ |
| 12 | Northbound 1D/5D Smart Money | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ |
| 13 | Shareholder Concentration Trend | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ |
| 14 | Dragon & Tiger Institutional Net | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ |
| 15 | Crowding Loosening Warning | ORIGINAL_REQUEST §R3 | 5 | 5 | ✓ |
| 16 | Top Status Bar GUI Render | ORIGINAL_REQUEST §R2, §R4 | 5 | 5 | ✓ |
| 17 | GUI 3-Color Tags & Risk Table | ORIGINAL_REQUEST §R1, §R4 | 5 | 5 | ✓ |
| 18 | Offline DuckDB Fallback | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ |
| 19 | Read-Only Invariants Verification | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ |
| 20 | Existing 112 Tests Zero Regression | ORIGINAL_REQUEST §R4 | 5 | 5 | ✓ |

## Test Architecture
- Test runner: `pytest`
- Invocation command:
  ```powershell
  $env:PYTHONPATH="AGY2_FundAdvisory;."
  python -m pytest AGY2_FundAdvisory/tests
  ```
- Dedicated integration test file: `AGY2_FundAdvisory/tests/test_toolkit_integration.py`
- Test case format: Pytest test functions with assertions, edge-case parametrized fixtures, and mocked network disconnects.

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Full Portfolio Holding Risk Scan | F1, F2, F3, F4, F5, F6, F17 | High |
| 2 | Macro Liquidity Shock & Radar Defense | F7, F8, F9, F10, F11, F16 | High |
| 3 | Smart Money Northbound + Crowding Alert in Selection | F12, F13, F14, F15, F18 | High |
| 4 | Offline Lakehouse Disconnect Fallback | F1, F7, F12, F18, F21 | High |
| 5 | Full GUI Render End-to-End without Unhandled Exceptions | F5, F6, F10, F15, F16, F17, F22 | High |

## Coverage Thresholds
- Tier 1: ≥5 per feature
- Tier 2: ≥5 per feature (boundary and extreme values)
- Tier 3: Pairwise coverage of major feature interactions
- Tier 4: ≥5 realistic application scenarios
