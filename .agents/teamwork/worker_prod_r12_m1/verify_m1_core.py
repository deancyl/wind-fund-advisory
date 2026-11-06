import sys
from pathlib import Path

# Ensure workspace root in sys.path
WS_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(WS_ROOT) not in sys.path:
    sys.path.insert(0, str(WS_ROOT))
if str(WS_ROOT / "AGY2_FundAdvisory") not in sys.path:
    sys.path.insert(0, str(WS_ROOT / "AGY2_FundAdvisory"))

from AGY2_FundAdvisory.advisory_engine import SmartExecutionDCAEngine
from AGY2_FundAdvisory.portfolio_manager import PortfolioManager, FundHolding
from AGY2_FundAdvisory.strategy_bridge import StrategyBridge

def main():
    print("=== 1. 单基真实波动率与单基乖离率穿透 ===")
    funds = ['002351', '000216', '005561', '100032', '017436', '011613']
    for f in funds:
        m = SmartExecutionDCAEngine.get_fund_real_volatility_and_bias(f)
        print(f"Fund {f}: vol={m['volatility']}, bias20={m['bias_20']}, sigma_day={m['sigma_day']}")

    # 差异化滑点测试：50000元下高波科技基金节省必须远大于纯债
    slip_bond = SmartExecutionDCAEngine.calculate_vwap_execution_slippage(50000.0, '002351')
    slip_div = SmartExecutionDCAEngine.calculate_vwap_execution_slippage(50000.0, '005561')
    slip_star = SmartExecutionDCAEngine.calculate_vwap_execution_slippage(50000.0, '011613')
    print(f"50000元节省基点: 纯债={slip_bond['slippage_saved_bps']}, 红利={slip_div['slippage_saved_bps']}, 科创={slip_star['slippage_saved_bps']}")
    assert slip_star['slippage_saved_bps'] > slip_div['slippage_saved_bps'] > slip_bond['slippage_saved_bps']

    # plan_smart_dca 单基穿透
    plan = SmartExecutionDCAEngine.plan_smart_dca(
        total_capital=100000.0,
        allocations=[
            {'code': '002351', 'name': '易方达裕祥纯债A', 'weight': 0.3},
            {'code': '005561', 'name': '创金红利低波A', 'weight': 0.4},
            {'code': '011613', 'name': '华夏科创50C', 'weight': 0.3}
        ]
    )
    assert len(plan['fund_orders']) == 3
    o_bond, o_div, o_star = plan['fund_orders']
    print(f"DCA orders saved bps: 纯债={o_bond['slippage_saved_bps']}, 红利={o_div['slippage_saved_bps']}, 科创={o_star['slippage_saved_bps']}")
    assert o_star['slippage_saved_bps'] > o_div['slippage_saved_bps'] > o_bond['slippage_saved_bps']

    print("\n=== 2. 历史三大拐点对照尺 ===")
    ruler = SmartExecutionDCAEngine.get_historical_inflection_ruler()
    assert len(ruler['nodes']) == 4
    n_2021, n_2022, n_2024, n_now = ruler['nodes']
    assert n_2021['multiplier'] <= 0.50, f"2021 multiplier {n_2021['multiplier']} must be <= 0.5"
    assert n_2022['multiplier'] >= 1.50, f"2022 multiplier {n_2022['multiplier']} must be >= 1.5"
    assert n_2024['multiplier'] >= 1.80, f"2024 multiplier {n_2024['multiplier']} must be >= 1.8"
    assert n_now['multiplier'] >= 1.50, f"Today multiplier {n_now['multiplier']} in accumulation"
    print("Ruler verified: 2021=", n_2021['multiplier'], "2022=", n_2022['multiplier'], "2024=", n_2024['multiplier'], "today=", n_now['multiplier'])

    print("\n=== 3. 14:30 尾盘实时估值异动预警 ===")
    spike = SmartExecutionDCAEngine.evaluate_tail_valuation_anomaly('005561', realtime_quote=2.5)
    assert spike['anomaly_type'] == 'ANTI_CHASING'
    assert spike['amount_multiplier'] == 0.60
    pit = SmartExecutionDCAEngine.evaluate_tail_valuation_anomaly('011613', realtime_quote=-4.0)
    assert pit['anomaly_type'] == 'GOLDEN_PIT'
    assert pit['amount_multiplier'] == 1.15
    norm = SmartExecutionDCAEngine.evaluate_tail_valuation_anomaly('005561', realtime_quote=0.0)
    assert norm['anomaly_type'] == 'NORMAL'
    assert norm['amount_multiplier'] == 1.00
    print("Anomaly verified: spike=", spike['anomaly_tag'], "pit=", pit['anomaly_tag'], "norm=", norm['anomaly_tag'])

    print("\n=== 4. 浮盈安全垫抗震承压与破净临界模型 ===")
    pm = PortfolioManager()
    beta_013841 = pm.calculate_asset_historical_beta('013841')
    assert abs(beta_013841 - 1.2346) < 0.05, f"013841 beta was {beta_013841}"
    print("013841 beta corrected:", beta_013841)

    cushion_model = pm.calculate_portfolio_cushion_and_stress_model()
    assert cushion_model['portfolio_weighted_beta'] > 0
    assert cushion_model['comprehensive_cushion'] > 0
    assert len(cushion_model['stress_scenarios']) == 3
    assert cushion_model['stress_scenarios'][0]['remaining_cushion_yuan'] > 0
    print("Model calculated: beta=", cushion_model['portfolio_weighted_beta'], "cushion=", cushion_model['comprehensive_cushion'], "ratio=", cushion_model['cushion_ratio_pct'], "%")

    loss_pm = PortfolioManager(db_path=":memory:", ledger_json_path="loss_test.json")
    loss_pm.holdings = {
        '005561': FundHolding(fund_code='005561', fund_name='创金红利低波A', shares=10000.0, cost_price=2.5, current_nav=2.0, market_value=20000.0, cost_basis=25000.0, floating_pnl=-5000.0, floating_pnl_pct=-20.0)
    }
    loss_pm.available_cash = 0.0
    loss_pm.in_transit_cash = 0.0
    loss_model = loss_pm.calculate_portfolio_cushion_and_stress_model(current_index_point=3920.0)
    assert loss_model['is_in_floating_loss'] is True
    assert loss_model['recovery_rise_pct'] > 0
    print("Loss model verified: recovery rise = +", loss_model['recovery_rise_pct'], "%, summary =", loss_model['safety_margin_summary'])

    cash_pm = PortfolioManager(db_path=":memory:", ledger_json_path="cash_test.json")
    cash_pm.holdings = {}
    cash_pm.available_cash = 100000.0
    cash_pm.in_transit_cash = 0.0
    cash_model = cash_pm.calculate_portfolio_cushion_and_stress_model()
    assert cash_model['portfolio_weighted_beta'] == 0.0
    assert "100% 现金流动性" in cash_model['safety_margin_summary']
    print("Cash model verified: beta=0, summary =", cash_model['safety_margin_summary'])

    print("\n=== 5. StrategyBridge 静态桥接全面核验 ===")
    assert StrategyBridge.get_historical_inflection_ruler()['all_inflections_verified'] is True
    assert StrategyBridge.evaluate_tail_valuation_anomaly('005561', realtime_quote=2.5)['anomaly_type'] == 'ANTI_CHASING'
    assert abs(StrategyBridge.calculate_asset_historical_beta('013841') - 1.2346) < 0.05
    assert StrategyBridge.calculate_portfolio_cushion_and_stress_model()['portfolio_weighted_beta'] > 0
    print("StrategyBridge verified completely!")

    print("\n🎉 ALL G5 CORE QUANT TEST ASSERTIONS PASSED WITH 100% SUCCESS!")

if __name__ == "__main__":
    main()
