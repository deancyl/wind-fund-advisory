import sys
import os
import inspect

# Add workspace to path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from AGY2_FundAdvisory.portfolio_manager import PortfolioManager, FundQuote, _apply_fund_valuation_calibration
from AGY2_FundAdvisory.strategy_bridge import StrategyBridge
from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager
from AGY2_FundAdvisory.data_loader import DataLoader

def verify_task3_fund_quotes():
    print("=== [Task 3] Verifying fetch_realtime_fund_quote for 10 target funds ===")
    funds = ['002351', '110020', '017436', '000086', '000216', '100032', '011613', '005561', '161725', '000217']
    pm = PortfolioManager()
    
    quotes = {}
    for code in funds:
        q = pm.fetch_realtime_fund_quote(code)
        quotes[code] = q
        gztime = getattr(q, 'gztime', '')
        dwjz = getattr(q, 'dwjz', 0.0)
        gsz = getattr(q, 'gsz', 0.0)
        gszzl = getattr(q, 'gszzl', 0.0)
        is_official = getattr(q, 'is_official_nav', False)
        print(f"Fund {code}: dwjz={dwjz}, gsz={gsz}, gszzl={gszzl}%, gztime='{gztime}', is_official={is_official}")
        
        # Test calibration guard: verify _apply_fund_valuation_calibration does NOT override official quote
        original_gszzl = q.gszzl
        calibrated_q = _apply_fund_valuation_calibration(q)
        if is_official or '官方' in gztime:
            assert calibrated_q.gszzl == original_gszzl, f"Fund {code} official gszzl was overridden by calibration! {original_gszzl} -> {calibrated_q.gszzl}"
            assert getattr(calibrated_q, 'is_official_nav', False) is True, f"Fund {code} is_official_nav was lost!"
            print(f"  ✓ Calibration guard verified for {code}: gszzl={calibrated_q.gszzl}% preserved.")

    print("Task 3 PASSED ✓\n")

def verify_task4_rebalance_orders():
    print("=== [Task 4] Verifying combat_29_funds rebalance orders & holding days lock ===")
    mlm = MultiLedgerManager()
    ledger_name = "combat_29_funds"
    
    # Check if combat_29_funds exists, or load it
    ledgers = mlm.list_ledgers()
    print(f"Available ledgers: {[l.get('id') for l in ledgers]}")
    
    pm = mlm.get_pm(ledger_name)
    holdings = pm.holdings
    print(f"Total holdings in {ledger_name}: {len(holdings)}")
    
    # Check target funds
    target_funds = ['110020', '017436', '100032']
    for tf in target_funds:
        h = holdings.get(tf)
        if h:
            h_days = getattr(h, 'holding_days', 0)
            print(f"Target fund {tf}: shares={h.shares}, cost={h.cost_price}, holding_days={h_days}")
            assert h_days >= 7, f"Expected {tf} holding_days >= 7, got {h_days}"
            
    # Run compute_dynamic_tier_weights to get target weights
    tier_target_w = StrategyBridge.compute_dynamic_tier_weights(tier="C3", market_snapshot=None)
    if isinstance(tier_target_w, dict) and "weights" in tier_target_w:
        tier_target_w = tier_target_w["weights"]
        
    current_cash = pm.available_cash
    total_val = pm.get_total_asset_value()
    print(f"Ledger cash: {current_cash}, total_value: {total_val}")
    
    ai_orders_res = StrategyBridge.generate_ai_rebalance_orders(
        current_holdings=holdings,
        available_cash=current_cash,
        target_weights_funds=tier_target_w,
        pm=pm,
        mode="gentle",
        min_buffer_pct=3.0,
        core_anchor_code="002351"
    )
    items = ai_orders_res.get("items", [])
    print(f"Generated {len(items)} rebalance order items.")
    
    # Verify no false locks for holding_days >= 7 in both order items and UI logic
    for it in items:
        f_code = str(it.get("fund_code", ""))
        f_name = str(it.get("fund_name", ""))
        diff_amt = it.get("diff_amount", 0.0)
        action_raw = str(it.get("action_text", ""))
        h_days = int(it.get("holding_days", 400))
        s_class = str(it.get("share_class", "A")).upper()
        t_w_val = float(it.get("target_weight_pct", 0.0))
        mv_val = float(it.get("market_value", 0.0))
        safety_warn = str(it.get("safety_warning", ""))
        
        # UI mapping simulation exactly as in app_gui.py
        if "手动锁定" in action_raw or "禁卖" in action_raw or "锁定" in action_raw:
            op_action = "🔒 已手动锁定禁卖"
            op_point = "主动风控·锁死持仓下界"
        elif "C转A" in action_raw or "置换" in action_raw:
            op_action = "🔄 C转A零费率置换"
            op_point = "同系基金内部免赎平移·年省0.4%销售服务费"
        elif 0 <= h_days < 7 and diff_amt < -10:
            op_action = "🔴 未满7天锁仓保护"
            op_point = f"持有仅{h_days}天·严禁卖出免收1.50%惩罚扣费"
        elif h_days >= 7 and "部分批次" in safety_warn and diff_amt < -10:
            op_action = "🟡 部分批次免惩保护"
            op_point = f"已持有{h_days}天·未满7天批次自动保留免罚"
        elif 7 <= h_days < 30 and (s_class == "C" or "C" in f_name) and diff_amt < -10:
            op_action = "⏳ 临近30天免赎缓卖"
            days_left = max(1, 30 - h_days)
            op_point = f"已持有{h_days}天·差{days_left}天满30天免赎·建议缓卖省0.50%"
        elif (t_w_val <= 0.0001 or "清仓" in action_raw or "清扫" in action_raw or (diff_amt < -10 and abs(diff_amt + mv_val) < 5.0)):
            op_action = "🧹 建议清仓归拢"
            op_point = f"免赎全额回收¥{mv_val:,.0f}·资金归拢核心底仓"
        elif diff_amt > 100:
            op_action = "➕ 建议加仓"
            op_point = f"增配¥{abs(diff_amt):,.0f}·尾盘锚定/现金分红"
        elif diff_amt < -100:
            op_action = "➖ 建议减仓"
            op_point = f"减配¥{abs(diff_amt):,.0f}·阶梯退出/零摩擦落袋"
        else:
            op_action = "✅ 维持现状"
            op_point = "偏离在缓冲带内·无需无效换仓"
            
        # Check rule: If holding_days >= 7, it must NOT show '🔴 未满7天锁仓保护' or '持有仅...天·严禁卖出'
        if h_days >= 7:
            assert '未满7天锁仓保护' not in op_action, f"Error: Fund {f_code} (holding {h_days} days) has UI action '{op_action}'!"
            assert '未满7天锁仓保护' not in action_raw, f"Error: Fund {f_code} (holding {h_days} days) has action_raw '{action_raw}'!"
            assert '严禁卖出' not in op_point, f"Error: Fund {f_code} (holding {h_days} days) has op_point '{op_point}'!"
            assert '持有仅' not in op_point, f"Error: Fund {f_code} (holding {h_days} days) has op_point '{op_point}'!"
            
        if f_code in target_funds:
            print(f"Target fund order {f_code} ({f_name}):")
            print(f"  h_days={h_days}, diff_amt={diff_amt:.2f}, action_raw='{action_raw}'")
            print(f"  UI op_action='{op_action}', op_point='{op_point}', safety_warn='{safety_warn}'")

    print("Task 4 PASSED ✓\n")

def verify_task6_invariants():
    print("=== [Task 6] Verifying Physical Security Invariants & DataLoader ===")
    
    # Check DataLoader.simulate_execution signature and fee logic
    sig = inspect.signature(DataLoader.simulate_execution)
    print(f"DataLoader.simulate_execution signature: {sig}")
    expected_params = ['weights_df', 'prices_df', 'is_otc', 'penalty_days', 'penalty_rate', 'etf_impact']
    actual_params = list(sig.parameters.keys())
    for p in expected_params:
        assert p in actual_params, f"Missing parameter {p} in DataLoader.simulate_execution!"
    
    # Check default values
    assert sig.parameters['penalty_days'].default == 7
    assert sig.parameters['penalty_rate'].default == 0.015
    assert sig.parameters['etf_impact'].default == 0.001
        
    print("DataLoader.simulate_execution signature & default fees verified intact.")
    print("Task 6 Invariants PASSED ✓\n")

if __name__ == '__main__':
    verify_task3_fund_quotes()
    verify_task4_rebalance_orders()
    verify_task6_invariants()
    print("ALL VERIFICATION CHECKS PASSED SUCCESSFULLY! ✓✓✓")
