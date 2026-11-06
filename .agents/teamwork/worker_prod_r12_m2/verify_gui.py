import sys
from pathlib import Path

# Add paths
WS_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(WS_ROOT) not in sys.path:
    sys.path.insert(0, str(WS_ROOT))
if str(WS_ROOT / "AGY2_FundAdvisory") not in sys.path:
    sys.path.insert(0, str(WS_ROOT / "AGY2_FundAdvisory"))

from AGY2_FundAdvisory.advisory_engine import SmartExecutionDCAEngine
from AGY2_FundAdvisory.portfolio_manager import PortfolioManager, FundHolding
from AGY2_FundAdvisory.strategy_bridge import StrategyBridge
from AGY2_FundAdvisory.app_gui import (
    render_historical_inflection_ruler_html,
    render_portfolio_cushion_and_stress_card_html
)

def test_inflection_ruler_rendering():
    print("--- 1. Testing render_historical_inflection_ruler_html ---")
    ruler = StrategyBridge.get_historical_inflection_ruler(current_erp=82.6, current_bias=-2.07)
    html = render_historical_inflection_ruler_html(ruler)
    assert "历史三大牛熊拐点实盘对照尺" in html
    assert "2021" in html
    assert "0.50x" in html
    assert "2022" in html
    assert "1.93x" in html
    assert "2024" in html
    assert "1.94x" in html
    assert "今日实时" in html
    assert "1.76x" in html
    print("Passed: inflection ruler rendered with 4 nodes perfectly!")

def test_cushion_stress_card_rendering():
    print("--- 2. Testing render_portfolio_cushion_and_stress_card_html ---")
    pm = PortfolioManager()
    cushion_model = pm.calculate_portfolio_cushion_and_stress_model(current_index_point=3920.0)
    html = render_portfolio_cushion_and_stress_card_html(cushion_model)
    assert "浮盈安全垫抗震承压与本金破净临界看板" in html
    assert "组合加权 Beta" in html
    assert "β =" in html
    assert "综合安全垫厚度" in html
    assert "单日急跌 -3%" in html
    assert "周度回调 -5%" in html
    assert "极端回调 -10%" in html
    assert "破净安全边际" in html or "回本临界反弹" in html
    print("Passed: cushion stress card rendered with Beta, Cushion, and 3-stress scenarios perfectly!")

def test_tail_valuation_anomaly():
    print("--- 3. Testing evaluate_tail_valuation_anomaly integration ---")
    res_spike = StrategyBridge.evaluate_tail_valuation_anomaly("005561", "创金红利低波A", realtime_quote=2.5)
    assert res_spike["anomaly_type"] == "ANTI_CHASING"
    assert "防追高" in res_spike["anomaly_tag"]

    res_pit = StrategyBridge.evaluate_tail_valuation_anomaly("011613", "华夏科创50C", realtime_quote=-4.0)
    assert res_pit["anomaly_type"] == "GOLDEN_PIT"
    assert "黄金坑" in res_pit["anomaly_tag"]

    res_norm = StrategyBridge.evaluate_tail_valuation_anomaly("002351", "易方达纯债A", realtime_quote=0.01)
    assert res_norm["anomaly_type"] == "NORMAL"
    print("Passed: tail valuation anomaly tags verified!")

def test_differential_slippage_bps():
    print("--- 4. Testing differential slippage bps ---")
    m_bond = SmartExecutionDCAEngine.get_fund_real_volatility_and_bias("002351", "易方达纯债A")
    m_div = SmartExecutionDCAEngine.get_fund_real_volatility_and_bias("005561", "创金红利低波A")
    m_star = SmartExecutionDCAEngine.get_fund_real_volatility_and_bias("011613", "华夏科创50C")

    slip_bond = SmartExecutionDCAEngine.calculate_vwap_execution_slippage(
        order_amount=50000.0, fund_code="002351", fund_name="易方达纯债A",
        volatility=m_bond["volatility"], bias_20=m_bond["bias_20"]
    )
    slip_div = SmartExecutionDCAEngine.calculate_vwap_execution_slippage(
        order_amount=50000.0, fund_code="005561", fund_name="创金红利低波A",
        volatility=m_div["volatility"], bias_20=m_div["bias_20"]
    )
    slip_star = SmartExecutionDCAEngine.calculate_vwap_execution_slippage(
        order_amount=50000.0, fund_code="011613", fund_name="华夏科创50C",
        volatility=m_star["volatility"], bias_20=m_star["bias_20"]
    )
    print(f"Differential bps: bond={slip_bond['slippage_saved_bps']} bps, div={slip_div['slippage_saved_bps']} bps, tech={slip_star['slippage_saved_bps']} bps")
    assert slip_star["slippage_saved_bps"] > slip_div["slippage_saved_bps"] > slip_bond["slippage_saved_bps"]
    print("Passed: tech > dividend > bond differential slippage verified!")

if __name__ == "__main__":
    test_inflection_ruler_rendering()
    test_cushion_stress_card_rendering()
    test_tail_valuation_anomaly()
    test_differential_slippage_bps()
    print("\n🎉 ALL GUI AND LOGIC VERIFICATIONS PASSED SUCCESSFULLY!")
