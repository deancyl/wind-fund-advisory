import sys
import os
import pytest

sys.path.insert(0, os.path.abspath("AGY2_FundAdvisory"))

from portfolio_manager import PortfolioManager, PendingOrder
from portfolio_optimizer import calculate_portfolio_risk_contributions, WinRateOptimizer


def test_pcr_mathematical_sum_and_risk_guard():
    """验证 PCR 风险贡献度数学和恒等于 100.0% 及以损定仓护栏"""
    w = {"005561": 0.35, "100032": 0.25, "011612": 0.20, "001071": 0.20}
    res = calculate_portfolio_risk_contributions(w)
    
    assert "pcr" in res
    assert abs(res["total_pcr"] - 100.0) < 1e-4
    assert abs(sum(res["pcr"].values()) - 100.0) < 1e-4
    assert res["is_risk_concentrated"] is True
    assert "以损定仓护栏" in res["risk_budget_warning"]


def test_pending_order_t_plus_1_reconciliation():
    """验证在途订单 T+1 对账入库与资金回补"""
    pm = PortfolioManager()
    pm.load_demo_portfolio()
    initial_cash = pm.available_cash
    
    # 模拟一笔在途申购订单
    test_oid = "TEST_ORD_REC_001"
    mock_ord = PendingOrder(
        order_id=test_oid,
        created_at="2026-11-04 14:35:00",
        effective_trade_date="2026-11-04",
        action="BUY",
        fund_code="005561",
        fund_name="创金合信中证红利低波动A",
        amount=5000.0,
        shares=0.0,
        est_nav=1.258,
        est_fee=0.0,
        status="PENDING",
        notes="自动化测试在途单"
    )
    pm.pending_orders.append(mock_ord)
    pm.in_transit_cash += 5000.0
    
    # T+1 对账确认
    rec_res = pm.reconcile_pending_order(test_oid, confirmed_nav=1.258)
    assert rec_res["status"] == "SUCCESS"
    assert rec_res["confirmed_nav"] == 1.258
    
    # 验证订单状态变为 CONFIRMED，且持仓增加了对应的 FIFO 批次
    found_order = next((o for o in pm.pending_orders if o.order_id == test_oid), None)
    assert found_order is not None
    assert found_order.status == "CONFIRMED"
    
    h = pm.holdings["005561"]
    has_rec_batch = any(b.batch_id == f"B_REC_{test_oid}" for b in h.batches)
    assert has_rec_batch is True


def test_rebalance_net_utility_interception():
    """验证调仓净效用 Delta U 门禁与摩擦精算"""
    pm = PortfolioManager()
    pm.load_demo_portfolio()
    
    # 跨公司调仓小金额（摩擦大、预期超额低，应触发拦截）
    util_low = pm.calculate_rebalance_net_utility(
        from_fund_code="011612",  # 持有仅 3 天，触发 1.5% 惩罚赎回费
        to_fund_code="005561",
        amount=1000.0
    )
    assert util_low["exact_redemption_fee"] == 15.0  # 1.5% 惩罚费
    assert util_low["total_friction_and_risk_cost"] > 15.0
    assert util_low["delta_u"] <= 0.0
    assert util_low["should_intercept"] is True
    assert "建议原地持仓不动" in util_low["interception_badge"]
    
    # 同公司转换（华夏 011613 换 011612，同公司在途成本为 0）
    util_same = pm.calculate_rebalance_net_utility(
        from_fund_code="011613",
        to_fund_code="011612",
        amount=10000.0
    )
    assert util_same["is_same_company"] is True
    assert util_same["in_transit_opportunity_cost"] == 0.0
    assert util_same["delta_t_arrive"] == 0
