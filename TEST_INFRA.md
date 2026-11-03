# E2E Test Infra: Wind Advisory System Production Deep Refactoring

## Test Philosophy
- Requirement-driven, mathematically sound, visual and interaction integrity.
- Verification Tiers:
  - Tier 1: Mathematical Invariants (Weight conservation to 100.0%, Allocated amount == total_capital, no penny leakage).
  - Tier 2: Model Differentiation (Differentiated risk budget distribution across all 4 models and candidate sizes 6 & 12).
  - Tier 3: Win Rate Statistics Expansion & Dual-Mode Consistency.
  - Tier 4: UI/UX Structural Assertions (Sidebar restored, 6-index single line, 4-model cards, popover, dynamic attribution, titles <= 7 Chinese chars).
  - Tier 5: Adversarial and Regression Stability (No regressions in existing test suite, read-only files untouched).

## Test Architecture
- Test files:
  - `AGY2_FundAdvisory/tests/test_production_refactor_invariants.py` (New dedicated E2E & Invariant suite)
  - `AGY2_FundAdvisory/tests/test_ui_final_polish.py` (Aligned for new titles & sidebar)
  - `AGY2_FundAdvisory/tests/test_adversarial_m3_challenger2.py` (Aligned for new titles)
  - All existing test suites in `AGY2_FundAdvisory/tests/`
- Execution: `pytest AGY2_FundAdvisory/tests/`

## Feature Checklist
| Feature | Tier 1 | Tier 2 | Tier 3 | Tier 4 | Tier 5 |
|---------|:------:|:------:|:------:|:------:|:------:|
| M1.1 Optimizer Smooth Gradient & Differentiation | ✓ | ✓ | | | ✓ |
| M1.2 Weight Conservation & Penny Exactness | ✓ | | | | ✓ |
| M1.3 Purchasing Limit Split Deduction | ✓ | | | | ✓ |
| M2.1 2005-2026 Sample Expansion | | | ✓ | | ✓ |
| M2.2 Dual-Mode Win Rate Calculation & Disclosure | | | ✓ | | ✓ |
| M3.1 Sidebar Navigation Restoration | | | | ✓ | ✓ |
| M3.2 Top 6 Indices Single-Line Format | | | | ✓ | ✓ |
| M3.3 4-Model Cards & 6-Dim Popover | | | | ✓ | ✓ |
| M3.4 3 Dynamic Attribution Cards | | | | ✓ | ✓ |
| M3.5 <= 7 Chars Title Enforcement | | | | ✓ | ✓ |
