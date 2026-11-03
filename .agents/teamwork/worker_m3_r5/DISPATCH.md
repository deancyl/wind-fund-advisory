## 2026-11-03T02:32:05Z
You are teamwork_worker (Agent-3, Worker M3).
Working directory: d:\Google\Workspace\Wind\.agents\teamwork\worker_m3_r5\
Original request path: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md (MANDATORY: read this first).
Explorer 3 handoff report: d:\Google\Workspace\Wind\.agents\teamwork\teamwork_explorer_r5_3\handoff.md (MANDATORY: read this for exact UI hook points and interaction requirements).
Worker M1 handoff report: d:\Google\Workspace\Wind\.agents\teamwork\worker_m1_r5\handoff.md (MANDATORY: read this for strategy_bridge snapshot dictionary keys: er_snr, effective_momentum_window, mom_accel, momentum_exhaustion_warning, momentum_exhaustion_text).

Task: Implement and verify R5 in AGY2_FundAdvisory/app_gui.py.
Exclusive Write Boundary: You own AGY2_FundAdvisory/app_gui.py. Do NOT modify any other files (especially the 4 read-only referee files: judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py).

Specific Requirements:
1. Real-time Market SNR & Momentum Acceleration display in app_gui.py:
   - In Top Dashboard Banner card 2 (`top_c2`, lines ~547-573):
     * Extract `snr = float(snapshot.get("er_snr", 0.65))` and `accel = float(snapshot.get("mom_accel", 0.0))`.
     * Render the indicators clearly in the sub-label / caption / metric: e.g. `📡信噪比 ER: {snr:.2f} ｜ ⚡动量加速度: {accel:+.1f}%` (or `📡SNR {snr:.2f} ｜ ⚡加速度 {accel:+.1f}%`).
     * If `snapshot.get("momentum_exhaustion_warning")` is True, highlight with warning icon / alert badge: 「⚡ 动量衰竭预警：暂停追高进攻标的，新增资金转入红利/纯债缓冲」.
   - In Step 2 White-Box Panel card 2 (`c_sig2`, lines ~1186-1196):
     * In the "均线动量状态 (MA20)" card, add:
       - 考夫曼信噪比 (ER / SNR): `{snr:.2f}` (自适应变速窗口: `{snapshot.get('effective_momentum_window', 60)}日`).
       - 动量加速度 (Mom Accel): `{accel:+.2f}%`.
       - If `snapshot.get("momentum_exhaustion_warning")` is True, display the warning text: `「⚡ 动量衰竭预警：暂停追高进攻标的，新增资金转入红利/纯债缓冲」`.
2. Protect and verify the 5 existing interaction mechanisms in app_gui.py:
   - Tab 1 Step 1 Mode B: 30-second risk profiling questionnaire with 3 questions and risk level calculation.
   - Tab 1 Step 2 re-calc behavior: automatic collapsing of old Step 3 (`tab1_step_reached = 2`, clearing `tab1_step3_cache`), and alternative fund switching cache refresh.
   - Tab 2 Step 3: target portfolio switching between Tab 1 latest optimal portfolio vs core index all-weather pool; holding change invalidation of `tab2_diag_cache` and `tab2_rebal_cache`.
   - Tab 2 intraday observation period (09:30-14:30) anti-impulse confirmation lock checkbox.
   - Read-only referee files: `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py` (0 modification).
3. Test Verification:
   - Run existing interactive continuity and UI refinement tests:
     `cmd.exe /c "set PYTHONPATH=AGY2_FundAdvisory;.&& py -3.11 -m pytest AGY2_FundAdvisory/tests/test_interactive_continuity.py AGY2_FundAdvisory/tests/test_ui_and_logic_refinements.py"`
   - Create or run targeted AppTest assertions to verify that SNR, Accel, and exhaustion warning are rendered properly without breaking any existing layout or tests. Ensure 100% pass rate.
