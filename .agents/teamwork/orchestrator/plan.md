# Plan: Quantitative Heuristic Self-Evolving Engine Upgrade

## Objectives
Upgrade AGY2_FundAdvisory quant advisory system with 5 heuristic self-updating algorithms and white-box Streamlit UI without violating any physical safety rules or introducing look-ahead bias.

## Execution Steps
1. **Phase 0: Survey (3 Parallel Explorers)**
   - Explorer 1: Inspect `strategy_bridge.py` and existing multi-expert / market regime mechanisms.
   - Explorer 2: Inspect `portfolio_manager.py` and `data_loader.py` for risk budgeting, fees, in-transit friction, and CUSUM.
   - Explorer 3: Inspect `app_gui.py` and `tests/` for current UI layout, 4-step white-box logic, and test harness execution.
2. **Decomposition & Contracts Definition (PROJECT.md)**
   - Merge findings into `PROJECT.md` feature inventory and interface contracts.
3. **Phase 1: Milestone 1 (Agent-1 Implementation)**
   - Implement Hedge `OnlineExpertWeightUpdater` and Schmidt hysteresis with Sigmoid gating in `strategy_bridge.py`.
   - Explorer -> Worker -> Reviewer -> Challenger -> Auditor -> Gate.
4. **Phase 2: Milestone 2 (Agent-2 Implementation)**
   - Implement EWMA volatility reciprocal risk budgeting in `strategy_bridge.py` & `data_loader.py`.
   - Implement Friction utility interceptor with FIFO A/C fees and in-transit opportunity cost in `portfolio_manager.py`.
   - Explorer -> Worker -> Reviewer -> Challenger -> Auditor -> Gate.
5. **Phase 3: Milestone 3 (Agent-3 Implementation)**
   - Implement CUSUM dynamic fund ranking & auto-promotion in `portfolio_manager.py`.
   - Upgrade Streamlit 4-step white-box transparency, 3-sentence summary card, bidirectional breakout lines, and 1080p fit in `app_gui.py`.
   - Explorer -> Worker -> Reviewer -> Challenger -> Auditor -> Gate.
6. **Phase 4: Milestone 4 (Agent-4 Red Team & Verification)**
   - Add new tests in `tests/` covering R1-R7.
   - Run complete test suite (222 existing + new tests + AppTest).
   - Ensure read-only referee files are untouched.
   - Restart/verify local Streamlit port 8501 service.
   - Final audit and synthesis.
