# Execution Plan: G10 Generation Visual Subtraction, Filter & UI Elevation

## Objective
Implement G10 visual subtraction, eliminate text wrapping / line breaks, deduplicate cards, filter realtime news with financial whitelist/blacklist, elevate Tab navigation above dual-wing dashboard, verify via browser walkthrough, run full regression tests, push Git tag v4.0-G10, conduct Victory Audit, and generate G11 instructions.

## Milestones
1. **Survey & Technical Assessment (Phase 0)**
   - Dispatch 3 Explorers:
     - Explorer 1: Inspect `app_gui.py` (Top 3 sector cards, dual-wing dashboard layout, Tab hoisting, action bar, sidebar deduplication, card styling in Tab 1 & Tab 2).
     - Explorer 2: Inspect `advisory_engine.py` (_synthesize_quantitative_evidence logic), `data_loader.py` (fetch_realtime_market_news_and_catalysts financial whitelist/blacklist), and `portfolio_manager.py` (simulate_portfolio_cvar_bootstrap_instance scaling calibration).
     - Explorer 3: Inspect existing test suites (`tests/test_adv_final_closure.py`, `tests/test_g3_evolution_loop.py`, `tests/test_infra.py`, etc.) for obsolete UI text assertions that might fail due to visual subtraction.
2. **Milestone 1 (M1): Visual Subtraction & Backend Logic Implementation**
   - Implement the six surgeries across `app_gui.py`, `advisory_engine.py`, `data_loader.py`, `portfolio_manager.py`.
   - Update tests if obsolete UI text assertions block simplified UI.
   - Run unit / delta tests.
   - Review, challenge, and forensic audit.
3. **Milestone 2 (M2): Service Restart & Browser Multi-Modal Inspection**
   - Clean cache and smoothly restart Streamlit on port 8501.
   - Inspect `/browser` at http://localhost:8501 across desktop and 640px mobile viewports.
   - Verify zero text wrapping, no junk news, no duplicate buttons, tabs visible on first screen.
4. **Milestone 3 (M3): Full Regression, Audit, Git Tag v4.0-G10 & G11 Generation**
   - Run 100% test suite.
   - Check read-only invariant files.
   - Clean data dir.
   - Git add, commit, tag `v4.0-G10`, push.
   - Independent Victory Audit.
   - Generate G11 prompt in final output.
