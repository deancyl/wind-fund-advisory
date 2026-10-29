"""
Adversarial Stress Test Suite for Milestone 1 (R1 Look-Through Risk Screen Engine)
Author: Challenger 2 (challenger_m1_2)

Empirical Challenge Findings:
1. Crash on None / null / int items in `top_stocks` (TypeError in non-ashare scan)
2. Crash on `top_stocks: None` (TypeError: 'NoneType' object is not iterable)
3. Crash on NaN in `days_to_unlock` (ValueError: cannot convert float NaN to integer)
4. Crash on string in `goodwill_ratio_pct` (ValueError: could not convert string to float)
5. Validated exact mathematical boundary thresholds for goodwill, pledge, double-high, lockup, and FCF
6. Validated graceful offline fallback and cache isolation
"""

import sys
import copy
from pathlib import Path
from unittest.mock import patch
import pytest
import pandas as pd
import numpy as np
import requests

# Adjust path
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

from portfolio_manager import PortfolioManager, FUND_LOOK_THROUGH_DATA, resolve_stock_symbol
from src.toolkit import WindToolkit


@pytest.fixture
def test_pm(tmp_path):
    """Isolated PortfolioManager instance with in-memory DB"""
    db_file = tmp_path / "test_adv_state.db"
    json_file = tmp_path / "test_adv_ledger.json"
    pm = PortfolioManager(db_path=db_file, ledger_json_path=json_file)
    return pm


# ==============================================================================
# 1. Invalid / Unknown Fund Code Inputs (Contract & Robustness)
# ==============================================================================

@pytest.mark.parametrize("invalid_code", [
    "",
    "   ",
    "999999",
    "000000",
    "INVALID",
    "ABC123",
    "???",
    None,
    100032,
    2351,
    "002351 ",
    " 100032",
    "-1",
    12.34
])
def test_adversarial_invalid_fund_codes_no_crash(test_pm, invalid_code):
    """Test that arbitrary malformed or unknown fund codes degrade gracefully without uncaught exceptions."""
    res = test_pm.screen_fund_look_through_risk(invalid_code)
    
    assert isinstance(res, dict)
    assert "fund_code" in res
    assert "fund_name" in res
    assert "is_ashare_equity" in res
    assert "penetration_risk_score" in res
    assert "risk_level" in res
    assert "risk_badge" in res
    assert "danger_count" in res
    assert "watch_count" in res
    assert "top_stocks_screen" in res
    assert "diagnosis_summary" in res
    
    assert res["risk_level"] in ("Safe", "Watch", "Danger")
    assert 0.0 <= res["penetration_risk_score"] <= 100.0
    assert isinstance(res["top_stocks_screen"], list)


# ==============================================================================
# 2. Defect Reproductions: Crash Vulnerabilities on Missing/Null/Corrupt Data
# ==============================================================================

def test_defect_reproduction_none_in_top_stocks(test_pm, monkeypatch):
    """
    [DEFECT REPRODUCTION 1]
    When top_stocks contains a None value (e.g. ['贵州茅台', None, '宁德时代']),
    portfolio_manager.py:2896 throws:
    TypeError: argument of type 'NoneType' is not iterable
    """
    dummy_code = "888001"
    monkeypatch.setitem(FUND_LOOK_THROUGH_DATA, dummy_code, {
        "top_stocks": ["贵州茅台", None, "宁德时代"],
        "industries": {}
    })
    
    # This must not throw TypeError in production!
    res = test_pm.screen_fund_look_through_risk(dummy_code)
    assert isinstance(res, dict)
    assert res["is_ashare_equity"] is True


def test_defect_reproduction_top_stocks_is_none(test_pm, monkeypatch):
    """
    [DEFECT REPRODUCTION 2]
    When look_data['top_stocks'] is None (e.g. external data has null holdings),
    portfolio_manager.py:2950 throws:
    TypeError: 'NoneType' object is not iterable
    """
    dummy_code = "888002"
    monkeypatch.setitem(FUND_LOOK_THROUGH_DATA, dummy_code, {
        "top_stocks": None,
        "industries": {}
    })

    # This must not throw TypeError in production!
    res = test_pm.screen_fund_look_through_risk(dummy_code)
    assert isinstance(res, dict)
    assert res["top_stocks_screen"] == []
    assert res["penetration_risk_score"] == 0.0


def test_defect_reproduction_integer_in_top_stocks(test_pm, monkeypatch):
    """
    [DEFECT REPRODUCTION 3]
    When top_stocks contains raw integer codes (e.g. [600519, 300750]),
    portfolio_manager.py:2896 throws:
    TypeError: argument of type 'int' is not iterable
    """
    dummy_code = "888003"
    monkeypatch.setitem(FUND_LOOK_THROUGH_DATA, dummy_code, {
        "top_stocks": [600519, 300750],
        "industries": {}
    })

    res = test_pm.screen_fund_look_through_risk(dummy_code)
    assert isinstance(res, dict)
    assert len(res["top_stocks_screen"]) == 2


def test_defect_reproduction_nan_in_days_to_unlock(test_pm, monkeypatch):
    """
    [DEFECT REPRODUCTION 4]
    When lockup DataFrame has days_to_unlock as np.nan (standard for missing pandas values),
    portfolio_manager.py:3012 throws:
    ValueError: cannot convert float NaN to integer
    """
    dummy_code = "888004"
    stock_sym = "600519.SH"
    monkeypatch.setitem(FUND_LOOK_THROUGH_DATA, dummy_code, {"top_stocks": [stock_sym], "industries": {}})

    def mock_lockup(days_ahead=90):
        return pd.DataFrame([{
            "symbol": stock_sym,
            "days_to_unlock": np.nan,  # Standard pandas missing value
            "unlock_market_value_billion": 10.0,
            "unlock_ratio_total_pct": 5.0,
            "risk_level": "Medium"
        }])

    monkeypatch.setattr(test_pm.toolkit.holder_risk, "fetch_lockup_calendar", mock_lockup)
    res = test_pm.screen_fund_look_through_risk(dummy_code)
    assert isinstance(res, dict)


def test_defect_reproduction_string_in_financial_metrics(test_pm, monkeypatch):
    """
    [DEFECT REPRODUCTION 5]
    When financial risk returns non-numeric string (e.g. 'N/A' or '--'),
    portfolio_manager.py:2983 throws:
    ValueError: could not convert string to float: 'N/A'
    """
    dummy_code = "888005"
    stock_sym = "600519.SH"
    monkeypatch.setitem(FUND_LOOK_THROUGH_DATA, dummy_code, {"top_stocks": [stock_sym], "industries": {}})

    def mock_screen(sym):
        return {
            "symbol": sym,
            "goodwill_ratio_pct": "N/A",  # Common dirty data
            "double_high_risk": False,
            "fcf_billion": "--"
        }

    monkeypatch.setattr(test_pm.toolkit.earnings_forecast, "screen_financial_risks", mock_screen)
    res = test_pm.screen_fund_look_through_risk(dummy_code)
    assert isinstance(res, dict)


# ==============================================================================
# 3. Exact Mathematical Boundary Testing (Isolated Components)
# ==============================================================================

def test_adversarial_goodwill_ratio_boundaries_isolated(test_pm, monkeypatch):
    """
    Isolated test of goodwill boundaries:
    - goodwill <= 30.0: deduction 0
    - 30.0 < goodwill <= 40.0: deduction 30
    - goodwill > 40.0: deduction 40
    """
    # Clean baseline for pledge and lockup
    monkeypatch.setattr(test_pm.toolkit.holder_risk, "fetch_pledge_risk",
                        lambda symbol: pd.DataFrame([{"symbol": symbol, "pledge_ratio_controlling_pct": 0.0, "warning_close_line_status": "远离平仓线"}]))
    monkeypatch.setattr(test_pm.toolkit.holder_risk, "fetch_lockup_calendar", lambda days_ahead=90: pd.DataFrame())

    boundaries = [
        (0.0, 0.0, 100.0, "Safe"),
        (29.99, 0.0, 100.0, "Safe"),
        (30.0, 0.0, 100.0, "Safe"),        # <= 30.0 -> no deduct
        (30.01, 30.0, 70.0, "Watch"),     # > 30.0 -> -30
        (35.0, 30.0, 70.0, "Watch"),
        (40.0, 30.0, 70.0, "Watch"),      # <= 40.0 -> -30
        (40.01, 40.0, 60.0, "Watch"),     # > 40.0 -> -40
        (50.0, 40.0, 60.0, "Watch"),
    ]

    for gw_val, expected_gw_deduct, expected_score, expected_lvl in boundaries:
        test_pm._stock_screen_cache.clear()
        dummy_code = f"881{int(gw_val*10):03d}"
        stock_sym = f"60{int(gw_val*10):04d}.SH"
        monkeypatch.setitem(FUND_LOOK_THROUGH_DATA, dummy_code, {"top_stocks": [stock_sym], "industries": {}})

        monkeypatch.setattr(test_pm.toolkit.earnings_forecast, "screen_financial_risks",
                            lambda s, gw=gw_val: {"symbol": s, "goodwill_ratio_pct": gw, "double_high_risk": False, "fcf_billion": 10.0})

        res = test_pm.screen_fund_look_through_risk(dummy_code)
        stock_res = res["top_stocks_screen"][0]

        actual_gw_deduct = sum(d[1] for d in stock_res["deductions_detail"] if "商誉" in d[0])
        assert actual_gw_deduct == expected_gw_deduct, f"Goodwill {gw_val}: expected deduct {expected_gw_deduct}, got {actual_gw_deduct}"
        assert stock_res["stock_score"] == expected_score, f"Goodwill {gw_val}: expected score {expected_score}, got {stock_res['stock_score']}"
        assert stock_res["risk_level"] == expected_lvl


def test_adversarial_pledge_ratio_boundaries_isolated(test_pm, monkeypatch):
    """
    Isolated test of pledge ratio boundaries:
    - pledge < 50.0: deduction 0
    - 50.0 <= pledge <= 80.0: deduction 15
    - pledge > 80.0: deduction 35
    - warning_close_line_status == '击穿平仓线': deduction 35
    - warning_close_line_status == '临界预警线': deduction 15
    """
    # Clean baseline for financials and lockup
    monkeypatch.setattr(test_pm.toolkit.earnings_forecast, "screen_financial_risks",
                        lambda s: {"symbol": s, "goodwill_ratio_pct": 0.0, "double_high_risk": False, "fcf_billion": 10.0})
    monkeypatch.setattr(test_pm.toolkit.holder_risk, "fetch_lockup_calendar", lambda days_ahead=90: pd.DataFrame())

    pledge_cases = [
        (0.0, "远离平仓线", 0.0, 100.0, "Safe"),
        (49.99, "远离平仓线", 0.0, 100.0, "Safe"),
        (50.0, "远离平仓线", 15.0, 85.0, "Safe"),      # >= 50.0 -> -15
        (79.99, "远离平仓线", 15.0, 85.0, "Safe"),
        (80.0, "远离平仓线", 15.0, 85.0, "Safe"),      # <= 80.0 -> -15
        (80.01, "远离平仓线", 35.0, 65.0, "Watch"),    # > 80.0 -> -35
        (85.0, "远离平仓线", 35.0, 65.0, "Watch"),
        (10.0, "临界预警线", 15.0, 85.0, "Safe"),     # Status override
        (10.0, "击穿平仓线", 35.0, 65.0, "Watch"),    # Status override
    ]

    for p_val, status, expected_pledge_deduct, expected_score, expected_lvl in pledge_cases:
        test_pm._stock_screen_cache.clear()
        dummy_code = f"882{int(p_val*10):03d}"
        stock_sym = f"60{int(p_val*10):04d}.SH"
        monkeypatch.setitem(FUND_LOOK_THROUGH_DATA, dummy_code, {"top_stocks": [stock_sym], "industries": {}})

        monkeypatch.setattr(test_pm.toolkit.holder_risk, "fetch_pledge_risk",
                            lambda symbol, p=p_val, st=status: pd.DataFrame([{"symbol": symbol, "pledge_ratio_controlling_pct": p, "warning_close_line_status": st}]))

        res = test_pm.screen_fund_look_through_risk(dummy_code)
        stock_res = res["top_stocks_screen"][0]
        actual_pledge_deduct = sum(d[1] for d in stock_res["deductions_detail"] if "质押" in d[0])
        assert actual_pledge_deduct == expected_pledge_deduct, f"Pledge {p_val}/{status}: expected {expected_pledge_deduct}, got {actual_pledge_deduct}"
        assert stock_res["stock_score"] == expected_score
        assert stock_res["risk_level"] == expected_lvl


def test_adversarial_lockup_calendar_boundaries_isolated(test_pm, monkeypatch):
    """
    Isolated test of lockup calendar boundaries:
    - 0 <= days_to_unlock <= 90:
      * If high pressure or 30 <= days <= 90: deduct 20
    - days_to_unlock > 90: deduct 0
    - days_to_unlock < 0: deduct 0
    """
    monkeypatch.setattr(test_pm.toolkit.earnings_forecast, "screen_financial_risks",
                        lambda s: {"symbol": s, "goodwill_ratio_pct": 0.0, "double_high_risk": False, "fcf_billion": 10.0})
    monkeypatch.setattr(test_pm.toolkit.holder_risk, "fetch_pledge_risk",
                        lambda symbol: pd.DataFrame([{"symbol": symbol, "pledge_ratio_controlling_pct": 0.0, "warning_close_line_status": "远离平仓线"}]))

    cases = [
        (-5, "Low", 0.0, 0.0, 0.0),       # Past unlock -> 0
        (0, "High", 30.0, 10.0, 20.0),    # Day 0, high pressure -> deduct 20
        (15, "Low", 1.0, 1.0, 0.0),       # Day 15, low pressure -> 0
        (45, "Low", 1.0, 1.0, 20.0),      # Day 45 (30~90) -> deduct 20
        (90, "Low", 1.0, 1.0, 20.0),      # Day 90 -> deduct 20
        (91, "High", 100.0, 50.0, 0.0),   # Day 91 -> 0
    ]

    for days, risk_lvl, mval, rtot, expected_deduct in cases:
        test_pm._stock_screen_cache.clear()
        dummy_code = f"883{abs(days):03d}"
        stock_sym = f"60{abs(days):04d}.SH"
        monkeypatch.setitem(FUND_LOOK_THROUGH_DATA, dummy_code, {"top_stocks": [stock_sym], "industries": {}})

        monkeypatch.setattr(test_pm.toolkit.holder_risk, "fetch_lockup_calendar",
                            lambda days_ahead=90, d=days, r=risk_lvl, m=mval, rt=rtot: pd.DataFrame([{
                                "symbol": stock_sym,
                                "days_to_unlock": d,
                                "unlock_market_value_billion": m,
                                "unlock_ratio_total_pct": rt,
                                "risk_level": r
                            }]))

        res = test_pm.screen_fund_look_through_risk(dummy_code)
        stock_res = res["top_stocks_screen"][0]
        actual_deduct = sum(d[1] for d in stock_res["deductions_detail"] if "解禁" in d[0])
        assert actual_deduct == expected_deduct, f"Days {days}: expected {expected_deduct}, got {actual_deduct}"


# ==============================================================================
# 4. Total Offline / Simulated Network Timeout
# ==============================================================================

def test_adversarial_simulated_offline_and_timeout(test_pm, monkeypatch):
    """Network connection timeout simulation."""
    def mock_broken_get(*args, **kwargs):
        raise requests.exceptions.ConnectTimeout("Simulated severe WAN timeout (5000ms)")

    monkeypatch.setattr(requests, "get", mock_broken_get)

    res1 = test_pm.screen_fund_look_through_risk("100032")
    assert res1["fund_code"] == "100032"
    assert res1["risk_level"] in ("Safe", "Watch", "Danger")
    assert len(res1["top_stocks_screen"]) > 0

    res2 = test_pm.screen_fund_look_through_risk("002351")
    assert res2["is_ashare_equity"] is False
    assert res2["risk_badge"] == "🟢 健康"


# ==============================================================================
# 5. Portfolio Aggregation & Cache Isolation
# ==============================================================================

def test_adversarial_portfolio_pure_immune_assets(test_pm):
    """100% bond/gold portfolio has 0.0 penetration risk index."""
    test_pm.takeover_mode_a([
        {"fund_code": "002351", "amount": 50000.0, "nav": 1.0},
        {"fund_code": "000216", "amount": 50000.0, "nav": 1.0}
    ], available_cash=0.0)

    res = test_pm.calculate_portfolio_penetration_risk()
    assert res["portfolio_risk_index"] == 0.0
    assert res["risk_level"] == "Safe"
    assert res["risk_badge"] == "🟢 健康"
    assert res["danger_stock_count"] == 0
    assert res["watch_stock_count"] == 0


def test_adversarial_cache_isolation_and_immutability(test_pm):
    """Mutating returned dictionary does not mutate internal cache."""
    res1 = test_pm.screen_fund_look_through_risk("100032")
    first_stock = res1["top_stocks_screen"][0]
    original_score = first_stock["stock_score"]

    first_stock["stock_score"] = -999.0
    first_stock["risk_level"] = "MUTATED_VALUE"

    res2 = test_pm.screen_fund_look_through_risk("100032")
    assert res2["top_stocks_screen"][0]["stock_score"] == original_score
    assert res2["top_stocks_screen"][0]["risk_level"] != "MUTATED_VALUE"


# ==============================================================================
# 6. resolve_stock_symbol Fuzzing
# ==============================================================================

@pytest.mark.parametrize("fuzz_input, expected_type", [
    ("", type(None)),
    ("   ", type(None)),
    (None, type(None)),
    (123456, type(None)),
    ({"stock": "600519"}, type(None)),
    ("600519", str),
    ("000001", str),
    ("300750", str),
    ("688981", str),
    ("832000", str),
    ("920000", str),
    ("贵州茅台", str),
    ("贵州茅台A股", str),
    ("*ST三房", str),
    ("不存在的公司名称_随机乱码_@#$%^", type(None)),
])
def test_adversarial_resolve_stock_symbol_fuzzing(fuzz_input, expected_type):
    res = resolve_stock_symbol(fuzz_input)
    assert isinstance(res, expected_type)
    if isinstance(res, str):
        assert res.endswith((".SH", ".SZ", ".BJ"))
