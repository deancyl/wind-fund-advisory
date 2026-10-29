"""
Unit and Integration Test Suite for Milestone 2 & 3 (R2 & R3)
Files under test:
- AGY2_FundAdvisory/strategy_bridge.py (R2 Macro Liquidity Thermometer & Dual-Track Radar)
- AGY2_FundAdvisory/portfolio_manager.py (R3 Smart Money & Crowding Monitor)
"""

import sys
from pathlib import Path
from unittest.mock import patch
import pytest
import pandas as pd
import numpy as np

# Adjust sys.path
TEST_DIR = Path(__file__).resolve().parent
APP_DIR = TEST_DIR.parent
WORKSPACE_ROOT = APP_DIR.parent if APP_DIR.name == "AGY2_FundAdvisory" else APP_DIR

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

# Namespace collision guard
if "src" in sys.modules and hasattr(sys.modules["src"], "__path__"):
    local_src = str(WORKSPACE_ROOT / "src")
    if local_src not in sys.modules["src"].__path__:
        sys.modules["src"].__path__.insert(0, local_src)

from strategy_bridge import StrategyBridge
from portfolio_manager import PortfolioManager


@pytest.fixture
def pm_instance(tmp_path):
    """Isolated PortfolioManager instance with in-memory DB"""
    db_file = tmp_path / "test_m2_m3_state.db"
    json_file = tmp_path / "test_m2_m3_ledger.json"
    return PortfolioManager(db_path=db_file, ledger_json_path=json_file)


# ==============================================================================
# R2: Macro High-Frequency Liquidity Thermometer & Dual-Track Radar Tests
# ==============================================================================

def test_r2_snapshot_liquidity_thermometer_fields():
    """Verify get_latest_market_snapshot injects all R2 liquidity thermometer fields with valid types"""
    snapshot = StrategyBridge.get_latest_market_snapshot(force_reload=True)
    assert isinstance(snapshot, dict)

    # Required R2 fields
    required_fields = [
        "dr007",
        "policy_rate_7d",
        "dr007_spread_bp",
        "liquidity_status",
        "liquidity_badge",
        "recent_7d_net_injection_billion",
        "omo_latest_stance",
        "advisory_takeaway",
        "dual_track_radar"
    ]
    for field in required_fields:
        assert field in snapshot, f"Missing R2 field in snapshot: {field}"

    assert isinstance(snapshot["dr007"], (int, float))
    assert isinstance(snapshot["policy_rate_7d"], (int, float))
    assert isinstance(snapshot["dr007_spread_bp"], (int, float))
    assert isinstance(snapshot["liquidity_status"], str)
    assert any(tag in snapshot["liquidity_badge"] for tag in ["🟢", "🟡", "🔴"])
    assert isinstance(snapshot["recent_7d_net_injection_billion"], (int, float))
    assert isinstance(snapshot["omo_latest_stance"], str)
    assert isinstance(snapshot["advisory_takeaway"], str)

    radar = snapshot["dual_track_radar"]
    assert isinstance(radar, dict)
    assert radar["trend_stance"] in ["BULL", "STABLE", "BEAR"]
    assert radar["liquidity_stance"] in ["宽松", "中性", "收紧"]
    assert isinstance(radar["combined_action"], str)
    assert isinstance(radar["defensive_triggered"], bool)


def test_r2_dual_track_radar_matrix_and_defensive_trigger():
    """Verify dual-track macro radar decision matrix across diverse liquidity and trend conditions"""
    # 1. 模拟资金面极端收紧 (Spread > 45 bp) -> 触发极端防御配置
    mock_therm_extreme = {
        "dr007": 2.15,
        "policy_rate_7d": 1.50,
        "dr007_spread_bp": 65.0,
        "liquidity_status": "结构性偏紧",
        "recent_7d_net_injection_billion": -50.0,
        "omo_latest_stance": "净回笼",
        "advisory_takeaway": "流动性休克冲击"
    }
    with patch("src.toolkit.macro_liquidity.MacroLiquidityCollector.get_liquidity_thermometer", return_value=mock_therm_extreme):
        s_extreme = StrategyBridge.get_latest_market_snapshot(force_reload=True)
        radar_extreme = s_extreme["dual_track_radar"]
        assert radar_extreme["defensive_triggered"] is True
        assert "极端防御触发" in radar_extreme["combined_action"]
        assert "65%~70%" in radar_extreme["combined_action"]

    # 2. 模拟资金面宽松 (Spread <= 15 bp)
    mock_therm_loose = {
        "dr007": 1.40,
        "policy_rate_7d": 1.50,
        "dr007_spread_bp": -10.0,
        "liquidity_status": "流动性泛滥",
        "recent_7d_net_injection_billion": 100.0,
        "omo_latest_stance": "净投放",
        "advisory_takeaway": "流动性充裕"
    }
    with patch("src.toolkit.macro_liquidity.MacroLiquidityCollector.get_liquidity_thermometer", return_value=mock_therm_loose):
        s_loose = StrategyBridge.get_latest_market_snapshot(force_reload=True)
        radar_loose = s_loose["dual_track_radar"]
        assert radar_loose["defensive_triggered"] is False
        assert radar_loose["liquidity_stance"] == "宽松"
        assert "宽松" in s_loose["liquidity_badge"]


def test_r2_defensive_allocation_advice_propagation():
    """Verify that when defensive_triggered is True, defensive advice is appended to blueprint & rebalance orders"""
    mock_therm_extreme = {
        "dr007": 2.20,
        "policy_rate_7d": 1.50,
        "dr007_spread_bp": 70.0,
        "liquidity_status": "结构性偏紧",
        "recent_7d_net_injection_billion": -80.0,
        "omo_latest_stance": "净回笼",
        "advisory_takeaway": "跨季流动性极度紧张"
    }
    with patch("src.toolkit.macro_liquidity.MacroLiquidityCollector.get_liquidity_thermometer", return_value=mock_therm_extreme):
        # 1. Blueprint 测试
        bp = StrategyBridge.generate_zero_start_blueprint(total_capital=100000.0)
        assert bp["defensive_triggered"] is True
        assert "触发极端防御配置" in bp["defensive_advice"]
        assert "65%~70%" in bp["defensive_advice"]
        assert "触发极端防御配置" in bp["summary_advice"]

        # 2. Rebalance orders 测试
        reb = StrategyBridge.generate_ai_rebalance_orders(
            current_holdings={},
            available_cash=100000.0,
            target_weights_funds={"100032": 0.5, "002351": 0.5}
        )
        assert reb["defensive_triggered"] is True
        assert "触发极端防御配置" in reb["defensive_advice"]


# ==============================================================================
# R3: Smart Money & Crowding Monitor Tests
# ==============================================================================

def test_r3_get_fund_smart_money_crowding_contract(pm_instance):
    """Verify get_fund_smart_money_crowding returns full interface contract dictionary"""
    res = pm_instance.get_fund_smart_money_crowding("100032")
    assert isinstance(res, dict)

    required_keys = [
        "fund_code",
        "fund_name",
        "northbound_1d_net_million",
        "northbound_5d_net_million",
        "concentration_trend",
        "crowding_degree",
        "crowding_warning",
        "advisory_tip",
        "institutional_sentiment",
        "top_stocks_detail"
    ]
    for key in required_keys:
        assert key in res, f"Missing key in get_fund_smart_money_crowding: {key}"

    assert res["fund_code"] == "100032"
    assert isinstance(res["northbound_1d_net_million"], (int, float))
    assert isinstance(res["northbound_5d_net_million"], (int, float))
    assert res["concentration_trend"] in ["筹码集中", "筹码分散", "筹码平稳"]
    assert res["crowding_degree"] in ["极度拥挤", "中度抱团", "相对分散"]
    assert isinstance(res["crowding_warning"], bool)
    assert isinstance(res["advisory_tip"], str)
    assert isinstance(res["top_stocks_detail"], list)


def test_r3_non_ashare_asset_immunity(pm_instance):
    """Verify pure bond, gold, and QDII assets are immune to A-share crowding risks"""
    immune_funds = ["002351", "000216", "050025"]
    for code in immune_funds:
        res = pm_instance.get_fund_smart_money_crowding(code)
        assert res["northbound_1d_net_million"] == 0.0
        assert res["northbound_5d_net_million"] == 0.0
        assert res["concentration_trend"] == "筹码平稳"
        assert res["crowding_degree"] == "相对分散"
        assert res["crowding_warning"] is False
        assert "无A股" in res["advisory_tip"] or "非A股" in res["advisory_tip"]


def test_r3_crowding_warning_detection_and_rebalance_caution(pm_instance):
    """Verify crowding warning triggers caution advice in rebalance orders"""
    # 模拟某基金底层呈现极度拥挤与筹码分散/资金流出复合高危
    mock_crowding_res = {
        "fund_code": "011613",
        "fund_name": "华夏科创50",
        "northbound_1d_net_million": -350.0,
        "northbound_5d_net_million": -1250.0, # 净流出 > 10 亿
        "concentration_trend": "筹码分散",
        "crowding_degree": "极度拥挤",
        "crowding_warning": True,
        "advisory_tip": "抱团松动踩踏高危：严禁单笔重仓追高！建议执行分批定投或下调增配目标",
        "institutional_sentiment": "净流出避险",
        "top_stocks_detail": []
    }

    with patch.object(pm_instance, "get_fund_smart_money_crowding", return_value=mock_crowding_res):
        reb = StrategyBridge.generate_ai_rebalance_orders(
            current_holdings={},
            available_cash=100000.0,
            target_weights_funds={"011613": 0.5, "002351": 0.5},
            pm=pm_instance
        )

        assert reb["crowding_warning_detected"] is True
        assert "抱团松动踩踏高危：严禁单笔重仓追高！" in reb["crowding_caution"]

        # 检查订单明细项中包含抱团预警与定投警示
        order_011613 = next((it for it in reb["items"] if it["fund_code"] == "011613"), None)
        assert order_011613 is not None
        assert order_011613["crowding_warning"] is True
        assert "抱团松动踩踏高危：严禁单笔重仓追高！" in order_011613["caution_advice"]
        assert "抱团松动踩踏高危" in order_011613["advice_share"]


def test_r3_robustness_corner_cases(pm_instance):
    """Verify unknown fund codes, empty strings, and None values degrade safely without exceptions"""
    invalid_codes = ["999999", "", "INVALID", None]
    for code in invalid_codes:
        res = pm_instance.get_fund_smart_money_crowding(code)
        assert isinstance(res, dict)
        assert "fund_code" in res
        assert "crowding_warning" in res
        assert res["crowding_warning"] is False
