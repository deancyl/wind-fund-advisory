## 2026-11-07T14:26:34Z
You are Explorer 1 for the G7 Generation Survey.
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g7_1
MANDATORY: Read d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md and d:\Google\Workspace\Wind\GEMINI.md before starting work.
Do NOT write or modify application code. You are an investigation agent.

Task:
1. Thoroughly investigate AGY2_FundAdvisory/app_gui.py in relation to Tab 2:
   - Identify the exact line ranges, functions, and layout flow of Tab 2 components:
     * Mode 1 components: 浮盈安全垫与破净临界看板, 持仓核心表, 五维时机裁决, 四大调仓场景与调仓执行单.
     * Mode 2 components: 快速粘贴导入, FIFO 批次解锁透视, 实盘接管净值曲线与影子组合复盘账单, T+1 在途订单对账中心, 同公司低摩擦转换, 宏观自适应分红表.
     * Multi-ledger management bar (多账本管理吧台) and quick fund entry bar (极速录基吧台).
2. Design the dual-view mode switcher:
   - Placement: directly below the multi-ledger bar.
   - Switcher design: horizontal radio / segmented control with session_state persistence (`tab2_view_mode`).
   - Default: "持仓诊断与智能调仓" (Mode 1).
   - Mode 2: "账本运维与实盘复盘档案".
   - Seamless jump from Mode 1 quick entry bar to Mode 2.
   - Reduction of vertical scroll length by >30% in Mode 1.
3. Check existing tests:
   - Scan tests/test_gui_multi_ledger_stress.py, tests/test_infra.py, tests/test_adv_final_closure.py, tests/test_g3_evolution_loop.py.
   - Verify whether any AppTest or unit test looks for specific keys, labels, or containers in Tab 2, and determine how to preserve 100% backward compatibility.
4. Check code reduction / logic sinking:
   - How HTML card rendering and data pre-processing in Tab 2 can be sunken to strategy_bridge.py or helper functions without breaking test imports.

Deliver your detailed findings, line numbers, exact code structures, and implementation recommendations in:
d:\Google\Workspace\Wind\.agents\teamwork\explorer_g7_1\handoff.md
Send a completion message back when done.
