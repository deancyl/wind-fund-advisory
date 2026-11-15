## 2026-11-15T08:15:22Z
【E2E Test Writer: Milestone 2 Test Suite & Regression Fixes】
Working directory: d:\Google\Workspace\Wind
Your state folder: d:\Google\Workspace\Wind\.agents\teamwork\teamwork_test_writer_m2_1
Authoritative user request: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Project plan: d:\Google\Workspace\Wind\PROJECT.md
Test infrastructure spec: d:\Google\Workspace\Wind\TEST_INFRA.md
Explorer investigation: d:\Google\Workspace\Wind\.agents\teamwork\teamwork_explorer_e2e_1\analysis.md

Your task:
1. Read ORIGINAL_REQUEST.md, PROJECT.md, and TEST_INFRA.md (specifically § Feature 7 - § Feature 14).
2. Fix the 2 known non-readonly test regressions documented in Explorer analysis:
   - In `tests/test_g16_phase1_memo_and_combat29.py`: line 219 assertion update to accept `"0深套 ｜ 结构优良"` or `"建仓标的"`:
     `assert ("建仓标的" in call_arg or "0深套 ｜ 结构优良" in call_arg)`
   - In `tests/test_g15_phase2_memo_and_timemachine.py`: line 250 update `target_date` to `"2028-01-01"` (future date beyond lakehouse max date 2026-11-13) so that `with pytest.raises(ValueError, match="缺乏前推回测样本"):` triggers properly.
   - Run `py -3 -m pytest tests/test_g16_phase1_memo_and_combat29.py tests/test_g15_phase2_memo_and_timemachine.py -v` via run_command to verify 100% pass.
3. Create and write `tests/test_g19_m2_routing_and_rolling_dca.py` exclusively.
4. The test suite must comprehensively cover:
   - Feature 7: 首次加载存量账本自动路由 (when portfolio funds >= 10 and not initial routed, auto route to Tab 2, set tab2_view_mode, tab2_diagnosed=True, tab2_rebalanced=True, pending_cross_tab_jump).
   - Feature 8: 样式集中合并与手机端列选择器 (chief-memo styles in global stylesheet, stColumn in mobile button group without breaking number input buttons).
   - Feature 9: 近3年滚动发车盲测胜率实证表 (StrategyBridge.calculate_rolling_dca_3y_backtest with bi-monthly/quarterly 180d/365d win rates, avg return, excess return vs CSI300, full fee deductions).
   - Feature 10: 摩擦账单动态精算与回测全额扣费 (eliminate cagr=16.85, mdd=-16.76 fake constants in calculate_mutual_fund_friction_bill, daily 0.75%/250 mgmt/custody fee in time machine backtest).
   - Feature 11: OCR 识别双通道并集与词表扩充 (do NOT early return when clean_res >= 1, union fusion of spatial bounding boxes and text, exclude A500 and lockup period confusion words).
   - Feature 12: IS_MOBILE_VIEW 激活与响应式布局.
   - Feature 13: Tab 2 工具坞扁平化与前置人话解读卡片 (radio toggle, Brinson, heatmap, scatter plot lead cards).
5. Follow the 4-tier methodology in TEST_INFRA.md: Tier 1, Tier 2, Tier 3, and Tier 4 scenarios.
6. Run the test file using `py -3 -m pytest tests/test_g19_m2_routing_and_rolling_dca.py -v` via run_command to verify test compilation and execution.
7. Write your handoff report to `d:\Google\Workspace\Wind\.agents\teamwork\teamwork_test_writer_m2_1\handoff.md`.
8. Send a message to your orchestrator when done.
