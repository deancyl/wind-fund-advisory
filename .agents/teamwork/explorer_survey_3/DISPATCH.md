## 2026-10-30T00:59:03Z
sender: 7eb668ae-6843-4834-9b3d-3455ac86af88
priority: MESSAGE_PRIORITY_HIGH
content:
You are Explorer 3 for the AGY2_FundAdvisory self-evolving quant engine project.
Your working directory is d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_3\
You MUST read d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md first before starting work.
Working directory for code is d:\Google\Workspace\Wind\AGY2_FundAdvisory.

Mission:
Investigate portfolio_manager.py (fund selection), app_gui.py (Streamlit UI layout & 4-step white-box), and tests/ (existing test suite & test infra).
Focus on:
1. Fund selection funnel, candidate pools, 6-dimensional scoring in portfolio_manager.py.
   - Requirements and exact insertion points for R6: CUSUM change-point detection for core track champion fund auto-promotion (rolling momentum excess, tracking error, expense drag, R1 heavy stock demining, R3 smart money flow -> S_{f,t}, CUSUM decay metric; auto-promote rank 1 candidate with label "🔄 自进化优选：因综合评分领先，已自动为您优选 XXXXX").
2. Streamlit UI architecture in app_gui.py:
   - Current 4-step execution flow and expandable panels.
   - Top summary cards, breakout trigger lines (upward breakout line vs downward defense line).
   - Table rendering and 1080p fit, hover tooltips ⓘ.
   - Requirements and exact insertion points for R7: 4-step white-box transparency panels (Step 1 CUSUM, Step 2 Hedge & Schmidt, Step 3 2018-2026 stress test & 5 human-readable metrics, Step 4 A/C fee & in-transit interceptor & split orders); 3-sentence summary card ("怎么赚钱、为什么能赢、风险与铁律"); fixed breakout lines (upward > current price, downward < current price); plain language + ⓘ hover tooltip; 1080p zero-wrap/zero-scrollbar fit.
3. Test suite structure in tests/:
   - How pytest is run, existing 222 tests, test infra in tests/test_infra.py.
   - Read-only files (judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py) - confirm their exact locations and ensure team knows never to modify them.
4. Record all relevant classes, functions, variable names, interfaces, and dependencies.

Deliverables:
- Keep updating d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_3\progress.md with timestamps.
- Write your detailed investigation report to d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_3\handoff.md following standard handoff structure (Observation, Logic Chain, Caveats, Conclusion, Verification Method).
- Send a message to orchestrator when completed.
