## 2026-11-15T09:03:02Z
You are Worker 1 for Milestone 2.
Your working directory: d:\Google\Workspace\Wind
Your state folder: d:\Google\Workspace\Wind\.agents\teamwork\worker_m2_1

Authoritative user request: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Project plan: d:\Google\Workspace\Wind\PROJECT.md
Scope document: d:\Google\Workspace\Wind\.agents\teamwork\sub_orch_m2\SCOPE.md

Detailed technical handoffs from 3 Explorers (MUST READ FIRST):
- Explorer 1 (Features 7, 8, 12, 13 in app_gui.py): d:\Google\Workspace\Wind\.agents\teamwork\explorer_m2_1\handoff.md
- Explorer 2 (Features 9, 10 in strategy_bridge.py, app_gui.py): d:\Google\Workspace\Wind\.agents\teamwork\explorer_m2_2\handoff.md
- Explorer 3 (Feature 11 in portfolio_manager.py & 88 E2E tests inventory): d:\Google\Workspace\Wind\.agents\teamwork\explorer_m2_3\handoff.md

Your exclusive write ownership:
- AGY2_FundAdvisory/app_gui.py
- AGY2_FundAdvisory/strategy_bridge.py
- AGY2_FundAdvisory/portfolio_manager.py
- tests/test_g19_m2_routing_and_rolling_dca.py (if regex type annotation adjustment is needed)

Physical security baseline:
DO NOT modify judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py.
DO NOT modify DataLoader.simulate_execution default signature & default fee logic.

Scope & Implementation Objectives (Features 7 to 13):
1. Feature 7: 首次加载存量持仓账本自动路由 (app_gui.py)
2. Feature 8: 样式集中合并与手机端列选择器 (app_gui.py)
3. Feature 9: 近 3 年滚动发车盲测胜率实证表 (strategy_bridge.py, app_gui.py)
4. Feature 10: 摩擦账单动态精算与回测全额扣费 (strategy_bridge.py)
5. Feature 11: OCR 识别双通道并集与词表扩充 (portfolio_manager.py)
6. Feature 12: IS_MOBILE_VIEW 激活与响应式布局 (app_gui.py)
7. Feature 13: Tab 2 工具坞扁平化与前置人话解读卡片 (app_gui.py)

Verification Requirement:
- Run: py -3 -m pytest tests/test_g19_m2_routing_and_rolling_dca.py -v
- MUST reach: 88 passed, 0 failed (100% pass rate).
