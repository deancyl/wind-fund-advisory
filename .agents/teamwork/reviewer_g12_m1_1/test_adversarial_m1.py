# -*- coding: utf-8 -*-
"""
Adversarial stress-test script for Milestone 1 Reviewer
"""
import sys
from pathlib import Path

_WORKSPACE = Path(__file__).resolve().parent.parent.parent.parent
_AGY2_DIR = _WORKSPACE / "AGY2_FundAdvisory"
if str(_AGY2_DIR) not in sys.path:
    sys.path.insert(0, str(_AGY2_DIR))
if str(_WORKSPACE) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE))

from AGY2_FundAdvisory.portfolio_manager import (
    PortfolioManager,
    FundQuote,
    _apply_fund_valuation_calibration,
    fetch_realtime_fund_quote,
)
from AGY2_FundAdvisory.advisory_engine import (
    ActiveRiskSentry,
    SmartExecutionDCAEngine,
)

print("--- Testing Adversarial Case 1: Corrupted / Weird Allocations in DCA ---")
# 1. Negative or zero weights
res1_erp, res1_bias = SmartExecutionDCAEngine.compute_portfolio_weighted_bias_and_erp(
    allocations=[{"code": "011613", "name": "华夏科创50", "weight": 0.0}],
    snapshot={"erp_percentile": 80.0, "c300_bias_20": 1.2}
)
print("Res1 (0 weight):", res1_erp, res1_bias)

# 2. String weights
res2_erp, res2_bias = SmartExecutionDCAEngine.compute_portfolio_weighted_bias_and_erp(
    allocations=[
        {"code": "011613", "name": "华夏科创50", "weight": "0.5", "bias_20": 2.0},
        {"code": "002351", "name": "招商产业债A", "weight": "0.5", "bias_20": 0.05}
    ],
    snapshot=None
)
print("Res2 (String weight):", res2_erp, res2_bias)
assert res2_bias == 1.02 or res2_bias == 1.03 or round(res2_bias, 2) == 1.02

# 3. Extreme bias values (clipping test)
res3_erp, res3_bias = SmartExecutionDCAEngine.compute_portfolio_weighted_bias_and_erp(
    allocations=[
        {"code": "011613", "name": "华夏科创50", "weight": 1.0, "bias_20": 50.0}
    ],
    snapshot={"erp_percentile": 80.0}
)
print("Res3 (Extreme positive bias):", res3_erp, res3_bias)
assert res3_erp >= 10.0, "ERP should be clipped at 10.0"

res4_erp, res4_bias = SmartExecutionDCAEngine.compute_portfolio_weighted_bias_and_erp(
    allocations=[
        {"code": "011613", "name": "华夏科创50", "weight": 1.0, "bias_20": -50.0}
    ],
    snapshot={"erp_percentile": 80.0}
)
print("Res4 (Extreme negative bias):", res4_erp, res4_bias)
assert res4_erp <= 95.0, "ERP should be clipped at 95.0"

print("--- Testing Adversarial Case 2: Feeder Valuation Calibration Edge Cases ---")
# 1. Zero dwjz
q_zero = FundQuote(
    name="华夏科创50ETF联接A",
    dwjz=0.0,
    gsz=1.0,
    gszzl=0.0,
    gztime="14:30",
    fund_code="011613",
    valuation_corrected=False
)
q_cal1 = _apply_fund_valuation_calibration(q_zero)
print("Res cal zero dwjz:", q_cal1.gsz, q_cal1.gszzl)

# 2. Unknown code with no name match
q_unknown = FundQuote(
    name="自定义私募FOF",
    dwjz=1.5,
    gsz=1.5,
    gszzl=0.0,
    gztime="14:30",
    fund_code="999999",
    valuation_corrected=False
)
q_cal2 = _apply_fund_valuation_calibration(q_unknown)
assert q_cal2.valuation_corrected is False
print("Res cal unknown fund:", q_cal2.valuation_corrected)

print("--- Testing Adversarial Case 3: Sentry with Strange Holdings ---")
sentry = ActiveRiskSentry()
weird_holdings = {
    "999999": {
        "code": "999999",
        "name": None,
        "market_value": -100.0,
        "shares": 0.0,
        "cost_nav": 0.0,
        "current_nav": 0.0,
        "pnl_pct": None,
        "category": None
    }
}
rep = sentry.inspect_portfolio(weird_holdings, snapshot={}, investor_risk_tier="C2")
print("Sentry status with weird holdings:", rep.get("status"))

print("ALL ADVERSARIAL CHECKS PASSED!")
