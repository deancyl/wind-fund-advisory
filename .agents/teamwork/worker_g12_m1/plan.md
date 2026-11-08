# Worker G12 M1 Plan
Implement 4 Circuit-Breaker Bugs & Sentry Parameter Penetration:
1. Bug 1: Correlation card key fix in app_gui.py and aliases in portfolio_manager.py
2. Bug 2: Sentry inspect_portfolio parameter penetration & fund quotes injection in app_gui.py
3. Bug 3: Index & Feeder fund valuation calibration with 0.95 factor in portfolio_manager.py
4. Bug 4: Portfolio weighted MA20 bias & ERP in SmartExecutionDCAEngine & app_gui.py
5. Write targeted unit tests in tests/test_g12_circuit_breakers_and_sentry.py
6. Run full regression tests
