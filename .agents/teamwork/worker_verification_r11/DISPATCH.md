## 2026-11-06T01:18:22Z

【Task: Three-Stage Lightweight Verification & Special Tests Execution】
You are a Worker. You execute build/test commands and verify functionality without modifying codebase files.

You MUST read the authoritative user request first:
`d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`

Your working directory: `d:\Google\Workspace\Wind\.agents\teamwork\worker_verification_r11\`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Tasks:
1. Run the three-stage lightweight verification per caller directive:
   `py -3 -m pytest tests/test_adv_final_closure.py tests/test_adv_upgrade_suite.py tests/test_infra.py -v`
2. Run Special Test 1:
   Write a small verification script or run inline python to verify that `pm.classify_fund_asset_class` for all 9 key test funds:
   - 161726 (中盘均衡 / 医药)
   - 161725 (核心蓝筹 / 白酒)
   - 160418 (A股红利高股息 / 银行)
   - 013402 (科技成长进攻 / 恒科)
   - 008888 (科技成长进攻 / 半导体)
   - 050025 (美股海外对冲 / 标普QDII)
   - 005561 (A股红利低波)
   - 002351 (纯债固收)
   - 000216 (黄金对冲)
   ALL return one of the 9 standard categories, and 0 return "其他权益资产".
3. Run Special Test 2:
   Verify that:
   - `StrategyBridge.calculate_portfolio_yield_cushion` returns real dynamic calculated values (weighted_yield_pct, annual_cushion_amount, monthly_equivalent_amount, cash_dividend_payout_est).
   - `pm.evaluate_rebalance_audit` returns real dynamic values (current_actual_equity, shadow_hold_equity, rebalance_value_add, saved_penalty_and_buffer_fees).
   - When modifying a holding's `current_nav`, both `current_actual_equity` and `shadow_hold_equity` dynamically and genuinely reflect the change!
4. Run Special Test 3:
   - Run Streamlit AppTest (`py -3 -m pytest tests/test_streamlit_apptest_run.py -v`) to verify all 4 tabs have zero unhandled exceptions.
   - Check if 8501 port service is healthy (`curl -I http://127.0.0.1:8501/_stcore/health` or via python urllib). If not running, start it or inspect its status in accordance with Windows transient port collision rules.
5. Inspect `app_gui.py` to confirm:
   - `FundHolding, HoldingItem` are in the reimport branch around line 148.
   - `_commit_edited_holdings_table` is called in `btn_tab2_all`.
   - `@st.fragment` is safely used in Tab 4 `with box_tab2:` and NEVER in `st.sidebar`.
   - QDII funds are excluded from Tab 2 same-company switch dock.

Output:
Write your full test outputs, execution evidence, and analysis to:
`d:\Google\Workspace\Wind\.agents\teamwork\worker_verification_r11\verification_report.md`
And write your handoff report to:
`d:\Google\Workspace\Wind\.agents\teamwork\worker_verification_r11\handoff.md`
Send a message when you are done.
