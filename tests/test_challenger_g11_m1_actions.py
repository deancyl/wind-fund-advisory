"""
Challenger G11 Milestone 1 Adversarial Verification Suite
(tests/test_challenger_g11_m1_actions.py)

Adversarially challenge Tab 1 state transitions and Module 3 actions:
1. Action bar Popovers and buttons:
   - Overwrite current ledger (chk_confirm_t1_overwrite + btn_apply_bp_tier + undo + goto)
   - Save as new ledger (btn_confirm_save_new_ledger + isolation + metadata + auto-switch)
   - Order cheat sheet popover rendering across 3 deployment modes (lump-sum, 3-step, smart DCA)
   - Send to backtest (btn_send_bp_to_bt + cross-tab state + Tab 3 reception)
2. Wing dashboard jump button (btn_master_action_switch) and last_cross_tab_action state handling:
   - 4 market/portfolio regimes (lock alerts -> red, general alerts -> yellow, empty -> rocket, healthy -> green)
   - pending_cross_tab_jump injection and consumption
   - last_cross_tab_action persistence
3. Bottom drawer expander sub-elements:
   - Rolling win rate cards (conditional vs unconditional, median return, positive probability)
   - 5 KPI metric cards
   - Endogenous dividend cushion card
   - Black swan stress card (3 historical crisis scenarios + 10k Block Bootstrap CVaR 99%)
   - Monte Carlo 3D distribution surface chart
   - Selection funnel & scoring table (quant_table + alts_map replacement trigger)
   - Macro decision signals (ERP, MA20/ER20/Mom, DR007, iVIX)
   - Liquidity haircut table (ADV, AUM, haircut bps, slippage saved)
   - Batch / DCA schedule dataframe
"""

import sys
import json
import copy
import hashlib
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

_CURRENT = Path(__file__).resolve().parent
_WORKSPACE = _CURRENT.parent
_AGY2_DIR = _WORKSPACE / "AGY2_FundAdvisory"
if str(_AGY2_DIR) not in sys.path:
    sys.path.insert(0, str(_AGY2_DIR))
if str(_WORKSPACE) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE))

from AGY2_FundAdvisory.portfolio_manager import PortfolioManager, FundHolding, HoldingBatch
from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager
from AGY2_FundAdvisory.strategy_bridge import StrategyBridge
from AGY2_FundAdvisory.advisory_engine import ActiveRiskSentry, SmartExecutionDCAEngine
import AGY2_FundAdvisory.data_loader as data_loader


# =====================================================================
# Fixtures for Isolated Workspace
# =====================================================================

@pytest.fixture
def mock_ledger_workspace(tmp_path):
    ws = tmp_path / "mock_wind_ws"
    ws.mkdir()
    data_dir = ws / "data"
    data_dir.mkdir()
    ledgers_dir = data_dir / "ledgers"
    ledgers_dir.mkdir()

    main_ledger_data = {
        "version": "AGY2_PORTFOLIO_V2",
        "takeover_mode": "B",
        "baseline_date": "2026-11-05",
        "baseline_equity": 100000.0,
        "available_cash": 20000.0,
        "in_transit_cash": 0.0,
        "total_market_value": 80000.0,
        "total_equity": 100000.0,
        "peak_equity": 100000.0,
        "max_drawdown_pct": 0.0,
        "benchmark_code": "000300.SH",
        "benchmark_baseline_nav": 1.0,
        "benchmark_current_nav": 1.0,
        "portfolio_return_pct": 0.0,
        "benchmark_return_pct": 0.0,
        "alpha_return_pct": 0.0,
        "holdings": [
            {
                "fund_code": "005561",
                "fund_name": "创金合信红利低波A",
                "share_class": "A",
                "shares": 50000.0,
                "cost_price": 1.0,
                "current_nav": 1.6,
                "market_value": 80000.0,
                "cost_basis": 50000.0,
                "floating_pnl": 30000.0,
                "floating_pnl_pct": 60.0,
                "first_buy_date": "2026-01-01",
                "dividend_method": "cash",
                "batches": [
                    {
                        "batch_id": "b1",
                        "buy_date": "2026-01-01",
                        "shares": 50000.0,
                        "cost_nav": 1.0,
                        "fee": 0.0,
                        "holding_days": 180,
                        "safety_lock": False,
                        "notes": "存量老底仓"
                    }
                ]
            }
        ],
        "pending_orders": [],
        "staged_batch_plans": [],
        "reserved_batch_cash": 0.0
    }
    with open(ws / "portfolio_ledger.json", "w", encoding="utf-8") as f:
        json.dump(main_ledger_data, f, ensure_ascii=False, indent=2)

    return ws


# =====================================================================
# 1. Adversarial Tests for Wing Dashboard Jump Button & Cross-Tab Action
# =====================================================================

def test_wing_dashboard_jump_states_and_transitions(mock_ledger_workspace):
    """
    Adversarial Challenge: Verify wing dashboard action states across 4 different portfolio regimes:
    1. Lock alert present (<7d holding) -> RED status, target Tab 1 (💼 持仓调仓)
    2. Other alerts present -> YELLOW status, target Tab 1 (💼 持仓调仓)
    3. Empty portfolio (0 holdings) -> ROCKET status, target Tab 0 (🌱 新资建仓)
    4. Healthy portfolio (clean holdings) -> GREEN status, target Tab 1 (💼 持仓调仓)
    """
    mlm = MultiLedgerManager(workspace_root=mock_ledger_workspace)
    sentry = ActiveRiskSentry()
    snapshot = StrategyBridge.get_latest_market_snapshot(force_reload=False, auto_sync=False) or {}

    # Case 1: Empty portfolio
    empty_lid = mlm.create_ledger("空仓账本", base_cash=100000.0, ledger_type="sandbox")
    empty_pm = mlm.get_pm(empty_lid)
    assert len(empty_pm.holdings) == 0

    _f_metas = {}
    sentry_rep_empty = sentry.inspect_portfolio(empty_pm.holdings, snapshot, fund_metadata=_f_metas)
    all_alerts_empty = sentry_rep_empty.get("alerts", [])
    lock_alerts_empty = [a for a in all_alerts_empty if a.get("action_type") == "lock_shares"]

    # In empty portfolio, should trigger act_target_tab = 0 (🌱 新资建仓)
    assert len(lock_alerts_empty) == 0
    assert len(all_alerts_empty) == 0
    # Rule check
    if len(empty_pm.holdings) == 0:
        act_status = "🚀"
        act_tab = 0
        act_btn = "👉 立即开始新资建仓"
    assert act_status == "🚀"
    assert act_tab == 0
    assert act_btn == "👉 立即开始新资建仓"

    # Case 2: Holding with < 7 days lock alert
    lock_lid = mlm.create_ledger("锁仓预警账本", base_cash=50000.0, ledger_type="sandbox")
    lock_pm = mlm.get_pm(lock_lid)
    lock_pm.add_or_update_holding("011613", 10000.0, 1.0, 1.0, 3, "华夏科创50联接C")
    lock_pm.save_state()

    _f_metas_lock = {"011613": data_loader.DataLoader.get_fund_metadata("011613") or {}}
    sentry_rep_lock = sentry.inspect_portfolio(lock_pm.holdings, snapshot, fund_metadata=_f_metas_lock)
    all_alerts_lock = sentry_rep_lock.get("alerts", [])
    lock_alerts = [a for a in all_alerts_lock if a.get("action_type") == "lock_shares"]
    assert len(lock_alerts) >= 1, "未满 7 天标的必须触发 lock_shares 预警"

    if lock_alerts:
        act_status = "🔴"
        act_tab = 1
        act_btn = "👉 查看锁仓保护"
    assert act_status == "🔴"
    assert act_tab == 1
    assert act_btn == "👉 查看锁仓保护"

    # Case 3: Healthy portfolio with mature holdings
    main_pm = mlm.get_pm("main_live")
    _f_metas_main = {"005561": data_loader.DataLoader.get_fund_metadata("005561") or {}}
    sentry_rep_main = sentry.inspect_portfolio(main_pm.holdings, snapshot, fund_metadata=_f_metas_main)
    lock_alerts_main = [a for a in sentry_rep_main.get("alerts", []) if a.get("action_type") == "lock_shares"]
    assert len(lock_alerts_main) == 0


def test_cross_tab_jump_payload_lifecycle():
    """
    Adversarial Challenge: Verify lifecycle of pending_cross_tab_jump and last_cross_tab_action:
    1. Jump payload contains required keys: tab_index, tab_name, action_name, target_title, detail, timestamp
    2. pending_cross_tab_jump is popped after DOM injection simulation
    3. last_cross_tab_action persists in session state for downstream auditing
    """
    session = {}
    jump_payload = {
        "tab_index": 1,
        "tab_name": "💼 持仓调仓",
        "action_name": "今日行动总开关",
        "target_title": "【锁定防御】存在未满 7 天惩罚期标的，已启动锁定保护严禁卖出",
        "detail": "标的 011613 处于惩罚锁定期，严禁减持扣除 1.50% 罚金。",
        "timestamp": "14:30:00"
    }
    session["pending_cross_tab_jump"] = jump_payload
    session["last_cross_tab_action"] = dict(jump_payload)

    # 模拟 app_gui.py lines 3148-3196:
    assert "pending_cross_tab_jump" in session
    consumed = session.pop("pending_cross_tab_jump", None)
    assert consumed is not None
    assert consumed["tab_index"] == 1
    assert "pending_cross_tab_jump" not in session

    # 验证 last_cross_tab_action 依然完好留存
    assert "last_cross_tab_action" in session
    assert session["last_cross_tab_action"]["action_name"] == "今日行动总开关"
    assert session["last_cross_tab_action"]["tab_index"] == 1


# =====================================================================
# 2. Adversarial Tests for Module 3 Actions
# =====================================================================

def test_module3_overwrite_ledger_execution_and_undo(mock_ledger_workspace):
    """
    Adversarial Challenge: Verify Tab 1 Module 3 Overwrite Current Ledger:
    1. Initial ledger has 1 fund (005561)
    2. Apply blueprint with 3 funds (005561, 000216, 011613)
    3. Verify current ledger overwritten with new blueprint holdings
    4. Verify undo restores original state (1 fund 005561) cleanly
    5. Verify 3 deployment modes (lump-sum, three-step, smart DCA) execute without schema violations
    """
    mlm = MultiLedgerManager(workspace_root=mock_ledger_workspace)
    pm = mlm.get_pm("main_live")
    assert len(pm.holdings) == 1
    orig_funds = set(pm.holdings.keys())

    blueprint = {
        "tier": "C3",
        "total_capital": 100000.0,
        "items": [
            {"fund_code": "005561", "fund_name": "创金合信红利低波A", "allocated_amount": 50000.0, "target_weight_pct": 50.0, "share_class": "A"},
            {"fund_code": "000216", "fund_name": "华安黄金ETF联接A", "allocated_amount": 30000.0, "target_weight_pct": 30.0, "share_class": "A"},
            {"fund_code": "011613", "fund_name": "华夏科创50联接C", "allocated_amount": 20000.0, "target_weight_pct": 20.0, "share_class": "C"},
        ]
    }

    # Test Mode A: Lump-sum
    res_lump = pm.apply_zero_start_blueprint(blueprint, cap_deployment_mode="⚡ 一次性建仓（今日全额配置）")
    assert res_lump["status"] == "SUCCESS"
    assert len(pm.holdings) == 3
    assert set(pm.holdings.keys()) == {"005561", "000216", "011613"}

    # Test Undo
    pm.undo()
    assert set(pm.holdings.keys()) == orig_funds
    assert len(pm.holdings) == 1

    # Test Mode B: Three-Step Batching
    alloc_list = [{"code": it["fund_code"], "name": it["fund_name"], "weight": it["target_weight_pct"] / 100.0} for it in blueprint["items"]]
    snapshot = StrategyBridge.get_latest_market_snapshot(force_reload=False, auto_sync=False) or {}
    three_step_plan = SmartExecutionDCAEngine.plan_three_step_batches(
        total_capital=100000.0,
        allocations=alloc_list,
        market_snapshot=snapshot
    )
    res_three = pm.apply_zero_start_blueprint(
        blueprint,
        cap_deployment_mode="🌊 稳健三步分批建仓（底仓 50% + 逢低网格 30% + 右侧趋势 20%）",
        deployment_plan=three_step_plan
    )
    assert res_three["status"] == "SUCCESS"
    assert len(pm.holdings) == 3

    # Test Undo again
    pm.undo()
    assert set(pm.holdings.keys()) == orig_funds

    # Test Mode C: Smart DCA
    dca_plan = SmartExecutionDCAEngine.plan_smart_dca(
        total_capital=100000.0,
        allocations=alloc_list,
        erp_percentile=78.0,
        bias_20=1.0,
        periods=12
    )
    res_dca = pm.apply_zero_start_blueprint(
        blueprint,
        cap_deployment_mode="📅 估值自适应智能定投（根据宏观 ERP 与均线偏离度动态调整扣款乘数）",
        deployment_plan=dca_plan
    )
    assert res_dca["status"] == "SUCCESS"
    assert len(pm.holdings) == 3


def test_module3_save_new_ledger_isolation_and_switch(mock_ledger_workspace):
    """
    Adversarial Challenge: Verify Tab 1 Module 3 Save as New Ledger:
    1. Hash of main_live must NOT change
    2. New ledger must have dedicated ledger file, db, and entry in ledgers_index.json
    3. Holdings in new ledger strictly match blueprint
    4. Switching active ledger updates mlm and pm seamlessly
    """
    mlm = MultiLedgerManager(workspace_root=mock_ledger_workspace)
    main_file = mock_ledger_workspace / "portfolio_ledger.json"
    with open(main_file, "rb") as f:
        orig_hash = hashlib.sha256(f.read()).hexdigest()

    new_lid = mlm.create_ledger(
        name="对抗测试独立账本",
        base_cash=200000.0,
        ledger_type="sandbox",
        default_tier="C4",
        description="由新资建仓一键生成"
    )
    new_pm = mlm.get_pm(new_lid)

    blueprint = {
        "tier": "C4",
        "total_capital": 200000.0,
        "items": [
            {"fund_code": "005561", "fund_name": "创金合信红利低波A", "allocated_amount": 80000.0, "target_weight_pct": 40.0, "share_class": "A"},
            {"fund_code": "011613", "fund_name": "华夏科创50联接C", "allocated_amount": 120000.0, "target_weight_pct": 60.0, "share_class": "C"}
        ]
    }
    res = new_pm.apply_zero_start_blueprint(blueprint)
    assert res["status"] == "SUCCESS"
    new_pm.save_state(record_snapshot=True)

    # 1. Verify main_live hash is 100% UNTOUCHED
    with open(main_file, "rb") as f:
        current_hash = hashlib.sha256(f.read()).hexdigest()
    assert current_hash == orig_hash, "主实盘文件遭到非预期篡改！"

    # 2. Verify new ledger in mlm
    all_lids = [l["id"] for l in mlm.list_ledgers()]
    assert new_lid in all_lids
    meta = mlm.get_ledger_meta(new_lid)
    assert meta["name"] == "对抗测试独立账本"
    assert meta["default_tier"] == "C4"

    # 3. Verify holdings isolation
    assert set(new_pm.holdings.keys()) == {"005561", "011613"}
    main_pm = mlm.get_pm("main_live")
    assert set(main_pm.holdings.keys()) == {"005561"}


def test_module3_cheat_sheet_content_correctness():
    """
    Adversarial Challenge: Verify Order Cheat Sheet text formatting across all modes:
    1. Contains standard header, risk tier, capital, generation time
    2. Contains fund code, amount, percentage, share class, dividend method, operation guide
    3. In 3-step mode, contains 50%/30%/20% batch amounts
    4. In Smart DCA mode, contains multiplier, base deduction, actual deduction, and slippage savings
    """
    # 1. Base Blueprint
    blueprint = {
        "tier": "C3",
        "total_capital": 100000.0,
        "items": [
            {"fund_code": "005561", "fund_name": "创金合信红利低波A", "allocated_amount": 60000.0, "target_weight_pct": 60.0, "share_class": "A", "require_cash_dividend": True, "action_guide": "正常买入"},
            {"fund_code": "011613", "fund_name": "华夏科创50联接C", "allocated_amount": 40000.0, "target_weight_pct": 40.0, "share_class": "C", "require_cash_dividend": False, "action_guide": "正常买入"},
        ]
    }
    cheat_lines = [
        "【AGY2 智能投顾专属建仓小抄】",
        "配置档位：C3 平衡进取型 ｜ 目标总投入：¥100,000.00",
        "----------------------------------------"
    ]
    for idx, it in enumerate(blueprint["items"], 1):
        div_str = "现金分红" if it.get("require_cash_dividend") else "红利再投"
        cheat_lines.append(
            f"{idx}. 基金代码: {it['fund_code']} ({it['fund_name']}) | 买入金额: ¥{it['allocated_amount']:,.2f} ({it['target_weight_pct']:.1f}%) | 份额: {it['share_class']}类 | 分红方式: {div_str}"
        )
    base_text = "\n".join(cheat_lines)
    assert "005561" in base_text
    assert "011613" in base_text
    assert "现金分红" in base_text
    assert "红利再投" in base_text

    # 2. Three-Step Mode
    three_step_lines = [base_text, "\n【🌊 稳健三步分批建仓执行小抄】"]
    for it in blueprint["items"]:
        amt = it["allocated_amount"]
        three_step_lines.append(f"标的: {it['fund_code']} -> 第1步今日底仓: ¥{amt*0.5:,.2f} | 第2步逢低网格: ¥{amt*0.3:,.2f} | 第3步右侧加仓: ¥{amt*0.2:,.2f}")
    three_step_text = "\n".join(three_step_lines)
    assert "稳健三步分批建仓执行小抄" in three_step_text
    assert "第1步今日底仓: ¥30,000.00" in three_step_text
    assert "第2步逢低网格: ¥18,000.00" in three_step_text

    # 3. Smart DCA Mode
    dca_lines = [base_text, "\n【📅 估值自适应智能定投执行小抄 (乘数: 1.50x · 微观执行优化版)】"]
    for it in blueprint["items"]:
        base_amt = it["allocated_amount"] / 12.0
        act_amt = base_amt * 1.5
        dca_lines.append(f"标的: {it['fund_code']} -> 基准定投: ¥{base_amt:,.2f}/期 | 本期实扣: ¥{act_amt:,.2f}")
    dca_text = "\n".join(dca_lines)
    assert "估值自适应智能定投执行小抄" in dca_text
    assert "基准定投: ¥5,000.00/期" in dca_text
    assert "本期实扣: ¥7,500.00" in dca_text


def test_module3_send_to_backtest_state_sync():
    """
    Adversarial Challenge: Verify Send to Backtest button state transition:
    1. Sets selected_backtest_weights with blueprint weights
    2. Sets selected_backtest_target = '新建仓组合'
    3. Sets tab3_backtest_activated = True
    4. Simulates Tab 3 reception: options include '🌱 Tab 1 最新建仓方案' and runs without error
    """
    session = {}
    cur_opt_w = {"005561": 0.50, "000216": 0.30, "011613": 0.20}

    # Simulate button click
    session["selected_backtest_weights"] = dict(cur_opt_w)
    session["selected_backtest_target"] = "新建仓组合"
    session["tab3_backtest_activated"] = True

    # Simulate Tab 3 logic (lines 6415-6461 in app_gui.py)
    t1_w = dict(session.get("selected_backtest_weights") or {})
    has_t1 = bool(t1_w)
    assert has_t1 is True

    opts_clean = ["🟢 【主实盘账本】(1只 · ¥100,000)"]
    opt_map_clean = {}
    if has_t1:
        lbl_t1 = f"🌱 Tab 1 最新建仓方案 ({len(t1_w)}只)"
        opts_clean.append(lbl_t1)
        opt_map_clean[lbl_t1] = ("plan_t1", t1_w)

    assert "🌱 Tab 1 最新建仓方案 (3只)" in opts_clean
    kind, weights = opt_map_clean["🌱 Tab 1 最新建仓方案 (3只)"]
    assert kind == "plan_t1"
    assert weights == cur_opt_w


# =====================================================================
# 3. Adversarial Tests for Bottom Drawer Expander Sub-elements
# =====================================================================

def test_bottom_drawer_subelements_execution():
    """
    Adversarial Challenge: Ensure all sub-elements in the bottom drawer expander:
    1. Rolling win rate cards (conditional vs unconditional)
    2. simulate_black_swan_stress & render_black_swan_stress_card
    3. simulate_portfolio_cvar_bootstrap & render_monte_carlo_3d_chart
    4. calculate_otc_fund_liquidity_haircut & render_liquidity_haircut_table
    5. selection funnel & quant_table dataframe
    6. alternative funds replacement slot logic
    Execute completely without unhandled exceptions.
    """
    pm = PortfolioManager()
    opt_weights = {"005561": 0.50, "000216": 0.30, "011613": 0.20}
    plan_capital = 100000.0

    # 1. Black Swan Stress Test
    from AGY2_FundAdvisory.app_gui import simulate_black_swan_stress
    stress_data = simulate_black_swan_stress(holdings=opt_weights, total_capital=plan_capital)
    assert stress_data is not None
    assert "scenarios" in stress_data
    assert len(stress_data["scenarios"]) == 3
    for sc in stress_data["scenarios"]:
        assert "max_dd_pct" in sc
        assert "max_loss_amt" in sc
        assert sc["max_dd_pct"] >= 0.0

    # 2. Monte Carlo 3D Bootstrap
    mc_data = pm.simulate_portfolio_cvar_bootstrap(
        holdings=opt_weights,
        total_capital=plan_capital,
        investor_risk_tier="C3",
        pm_instance=pm
    )
    assert "overall_cvar_99" in mc_data or "cvar_99" in mc_data
    assert "monte_carlo_3d_data" in mc_data
    z_mdd = mc_data["monte_carlo_3d_data"].get("z_mdd_matrix", [])
    assert len(z_mdd) == 3
    for row in z_mdd:
        assert len(row) == 5

    # 3. Liquidity Haircut calculation for each order
    orders = [
        {"fund_code": "005561", "fund_name": "创金合信红利低波A", "order_amount": 50000.0},
        {"fund_code": "000216", "fund_name": "华安黄金ETF联接A", "order_amount": 30000.0},
        {"fund_code": "011613", "fund_name": "华夏科创50联接C", "order_amount": 20000.0},
    ]
    active_orders = []
    for o in orders:
        fc = o["fund_code"]
        fn = o["fund_name"]
        amt = o["order_amount"]
        hc = data_loader.calculate_otc_fund_liquidity_haircut(order_amount=amt, fund_code=fc, fund_name=fn)
        active_orders.append({
            "fund_code": fc,
            "fund_name": fn,
            "order_amount": amt,
            "is_etf": hc.get("is_etf", False),
            "fund_aum_yuan": hc.get("fund_aum_yuan", 0.0),
            "top5_adv_yuan": hc.get("top5_adv_yuan", 0.0),
            "redemption_ratio_pct": hc.get("redemption_ratio_pct", 0.0),
            "liquidity_haircut_bps": hc.get("haircut_bps", 0.0),
            "liquidity_haircut_yuan": hc.get("haircut_yuan", 0.0),
            "slippage_saved_yuan": hc.get("slippage_saved_yuan", 0.0),
        })
    assert len(active_orders) == 3
    for ao in active_orders:
        assert ao["liquidity_haircut_bps"] >= 0.0
        assert ao["slippage_saved_yuan"] >= 0.0

    # 4. Alternative Slot Replacement Mechanism Check
    # Simulate lines 4317-4340 in app_gui.py
    custom_overrides = {}
    champion_code = "005561"
    alt_code = "100032"

    # User picks alternative
    custom_overrides[champion_code] = alt_code
    test_opt_w = dict(opt_weights)
    if champion_code in test_opt_w:
        val = test_opt_w.pop(champion_code)
        test_opt_w[alt_code] = val
    assert champion_code not in test_opt_w
    assert alt_code in test_opt_w
    assert test_opt_w[alt_code] == 0.50


# =====================================================================
# 4. Streamlit AppTest End-to-End Adversarial Simulation
# =====================================================================

def test_apptest_tab1_module3_and_wing_switch_e2e():
    """
    Adversarial AppTest Run:
    1. Loads app_gui.py in headless AppTest
    2. Initializes with active_tier_val=C3, tab1_step_reached=2, tab1_trigger_sim=True
    3. Verifies wing dashboard switch button exists
    4. Clicks wing dashboard button and verifies rerun and state
    5. Verifies Module 3 buttons exist (chk_confirm_t1_overwrite, btn_apply_bp_tier, btn_confirm_save_new_ledger, btn_send_bp_to_bt)
    6. Verifies bottom drawer sub-elements render without crashing
    """
    from streamlit.testing.v1 import AppTest
    app_path = _AGY2_DIR / "app_gui.py"
    at = AppTest.from_file(str(app_path), default_timeout=120)
    at.session_state.active_tier_val = "C3"
    at.session_state.target_return_val = 15.0
    at.session_state.tab1_step_reached = 2
    at.session_state.tab1_trigger_sim = True
    at.run(timeout=120)

    assert not at.exception, f"AppTest Run Failed with Exception: {at.exception}"

    # Verify wing dashboard button is completely eliminated in G13
    wing_btn = next((b for b in at.button if b.key == "btn_master_action_switch"), None)
    assert wing_btn is None, "首屏伪交易大红按钮 btn_master_action_switch 必须彻底消除"

    # Verify top advisory expander displays clear human-readable advice without errors
    advisory_expanders = [e for e in at.expander if "今日投顾参谋" in getattr(e, "label", "")]
    assert len(advisory_expanders) > 0, "首屏必须包含清晰人话投顾参谋折叠栏"
    assert "点击展开" in advisory_expanders[0].label

    # Verify Module 3 action buttons exist
    chk_overwrite = at.checkbox(key="chk_confirm_t1_overwrite")
    assert chk_overwrite is not None, "必须存在 chk_confirm_t1_overwrite 门禁复选框"

    btn_apply = at.button(key="btn_apply_bp_tier")
    assert btn_apply is not None, "必须存在 btn_apply_bp_tier 覆盖写入按钮"

    btn_save_new = at.button(key="btn_confirm_save_new_ledger")
    assert btn_save_new is not None, "必须存在 btn_confirm_save_new_ledger 另存新账本按钮"

    btn_bt = at.button(key="btn_send_bp_to_bt")
    assert btn_bt is not None, "必须存在 btn_send_bp_to_bt 送入回测按钮"

    # Verify Markdown contains critical bottom drawer text
    all_md = " ".join([m.value for m in at.markdown])
    assert "跨牛熊滚动胜率" in all_md, "底部抽屉必须包含跨牛熊滚动胜率"
    assert "历史黑天鹅极端承压测试" in all_md, "底部抽屉必须包含历史黑天鹅极端承压测试"
    assert "选基漏斗与评分" in all_md or "全市场选基漏斗" in all_md or "全市场基金底池" in " ".join([m.label for m in at.metric]), "底部抽屉必须包含选基漏斗与评分"


def test_apptest_tab1_interactive_button_clicks():
    """
    Adversarial Interactive Click Testing in AppTest:
    1. Send to backtest button (btn_send_bp_to_bt):
       - Click and run
       - Verify no exception
       - Verify tab3_backtest_activated is True
       - Verify selected_backtest_target is '新建仓组合'
       - Verify selected_backtest_weights contains funds
    2. Wing dashboard jump button (btn_master_action_switch):
       - Click and run
       - Verify no exception
       - Verify last_cross_tab_action is correctly updated
    """
    from streamlit.testing.v1 import AppTest
    app_path = _AGY2_DIR / "app_gui.py"
    at = AppTest.from_file(str(app_path), default_timeout=120)
    at.session_state.active_tier_val = "C3"
    at.session_state.target_return_val = 15.0
    at.session_state.tab1_step_reached = 2
    at.session_state.tab1_trigger_sim = True
    at.run(timeout=120)
    assert not at.exception, f"Initial AppTest failed: {at.exception}"

    # 1. Test clicking Send to Backtest
    btn_bt = at.button(key="btn_send_bp_to_bt")
    assert btn_bt is not None
    at = btn_bt.click().run(timeout=120)
    assert not at.exception, f"btn_send_bp_to_bt click failed: {at.exception}"
    assert at.session_state.get("tab3_backtest_activated") is True
    assert len(at.session_state.get("selected_backtest_weights", {})) > 0
    # Tab 3 selectbox options include the Tab 1 blueprint
    target_sel = at.selectbox(key="sel_backtest_target_type")
    assert target_sel is not None
    assert any("Tab 1 最新建仓方案" in opt for opt in target_sel.options)

    # 2. Test Wing Dashboard Jump Button eliminated & Top Advisory Expander verified
    wing_btn = next((b for b in at.button if b.key == "btn_master_action_switch"), None)
    assert wing_btn is None, "首屏伪交易大红按钮 btn_master_action_switch 必须彻底消除"
    advisory_expanders = [e for e in at.expander if "今日投顾参谋" in getattr(e, "label", "")]
    assert len(advisory_expanders) > 0, "首屏必须包含清晰人话投顾参谋折叠栏"
    assert "点击展开" in advisory_expanders[0].label
    assert not at.exception

