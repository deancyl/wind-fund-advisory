## 2026-10-29T09:04:08Z
You are Explorer 3 (Integration & Gap Explorer).
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_3
Your original parent conversation ID is: 5fd996d1-bc98-447a-9f35-c5aef5be2e1c (Project Orchestrator).

MANDATORY FIRST STEP:
Read the user request at: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md

OBJECTIVE:
Investigate the integration design and gap analysis for requirements R1, R2, R3, R4:
1. R1 Look-Through Financial & Credit Risk Screen:
   - Where and how to integrate `WindToolkit.earnings_forecast` and `WindToolkit.holder_risk` into `portfolio_manager.py` and `strategy_bridge.py`.
   - How to compute portfolio overall penetration risk index (组合穿透风险指数) and assign 3-color risk tags (🟢健康 / 🟡关注 / 🔴预警).
   - How Tab 1 and Tab 2 UI components in `app_gui.py` will render these tags and metrics.
2. R2 High-Frequency Macro Liquidity Thermometer:
   - How `WindToolkit.macro_liquidity` integrates into `strategy_bridge.py` and `app_gui.py` top status bar.
   - Calculation of DR007 vs 7D OMO spread (bp), determination of status (宽松 / 中性 / 收紧), and combination with HS300 MA system + ERP into a dual-track macro radar (双轨宏观雷达).
   - What happens when macro liquidity is extremely tight (defensive asset allocation trigger).
3. R3 Smart Money & Crowding Monitor:
   - How `WindToolkit.institutional_holdings` and `WindToolkit.chips_market` integrate into fund selection and rebalancing decision flow.
   - Calculation of Northbound 1D/5D net flow, shareholder count changes, dragon & tiger list institutional seats, chip concentration, and crowding loosening risk warning.
4. R4 Production Quality, Zero Regression, Read-Only Protection:
   - What tests need to be written in `AGY2_FundAdvisory/tests/` (e.g. `test_toolkit_integration.py`, unit & e2e)?
   - How to ensure offline DuckDB fallback works cleanly when offline or external services are unavailable.
   - Identify potential failure modes or edge cases.
5. Write your comprehensive findings to `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_3\handoff.md`.
6. Send a message to parent (Recipient: 5fd996d1-bc98-447a-9f35-c5aef5be2e1c) stating you have completed your report.

SCOPE BOUNDARIES:
- Read-only! DO NOT modify any code or test files.
- Write files ONLY to your working directory: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_3`.
