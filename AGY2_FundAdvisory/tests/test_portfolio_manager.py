"""
实盘基金投资组合接管与智能投顾管理引擎单元测试套件
验证：
1. 极简快照冷启动 (模式 A) 与基准重置
2. 历史账本热接管 (模式 B) 与先进先出 (FIFO) 批次队列
3. 7 天 1.50% 惩罚性赎回费强力安全拦截
4. 在途资金交收时差 (Cash-in-Transit) 与三级路由 (同公司转换/现金垫付/两阶段换仓)
5. 在途订单次日 (T+1) 净值校准与对账入库
6. 单日限购额度超限拆单与备选标的溢出路由 (Quota & Fallback)
7. 分红除权校准 (现金分红入账 vs 红利再投资免申购费加仓)
8. 场内 ETF 溢价率监控 (> 0.8% 预警)
9. SQLite / JSON 双轨持久化与 Undo 快照一键回滚
"""

import os
from pathlib import Path
import pytest
import sqlite3
from unittest.mock import patch

from portfolio_manager import PortfolioManager, FundHolding, HoldingBatch, PendingOrder


@pytest.fixture
def temp_pm(tmp_path):
    db_file = tmp_path / "test_portfolio_state.db"
    json_file = tmp_path / "test_portfolio_ledger.json"
    pm = PortfolioManager(db_path=db_file, ledger_json_path=json_file)
    return pm


# =====================================================================
# 1. 模式 A：极简快照冷启动测试
# =====================================================================

def test_takeover_mode_a_cold_start(temp_pm):
    fund_items = [
        {"fund_code": "005561", "amount": 50000.0, "nav": 1.25, "holding_tag": ">=30d"},
        {"fund_code": "100032", "amount": 30000.0, "nav": 1.00, "holding_tag": None} # 缺省 7 天锁
    ]
    res = temp_pm.takeover_mode_a(fund_items=fund_items, available_cash=20000.0, baseline_date="2026-10-28")

    assert res["status"] == "SUCCESS"
    assert res["mode"] == "MODE_A_COLD_START"
    assert res["funds_count"] == 2
    assert temp_pm.baseline_equity == 100000.0 # 50000 + 30000 + 20000
    assert temp_pm.available_cash == 20000.0

    # 验证 100032 缺省自动挂载 7 天安全观察锁
    h_100032 = temp_pm.holdings["100032"]
    assert h_100032.batches[0].safety_lock
    assert h_100032.batches[0].holding_days == 0

    # 验证 005561 已持满 30 天无安全锁
    h_005561 = temp_pm.holdings["005561"]
    assert not h_005561.batches[0].safety_lock
    assert h_005561.batches[0].holding_days == 45


# =====================================================================
# 2. 模式 B：历史账本热接管与 FIFO 批次队列构建
# =====================================================================

def test_takeover_mode_b_hot_takeover(temp_pm):
    records = [
        {"fund_code": "005561", "buy_date": "2026-06-01", "shares": 20000.0, "cost_nav": 1.10, "current_nav": 1.25, "fee": 10.0},
        {"fund_code": "005561", "buy_date": "2026-09-01", "shares": 10000.0, "cost_nav": 1.20, "current_nav": 1.25, "fee": 5.0}
    ]
    res = temp_pm.takeover_mode_b(historical_records=records, available_cash=10000.0, baseline_date="2026-10-28")

    assert res["status"] == "SUCCESS"
    h = temp_pm.holdings["005561"]
    assert h.shares == 30000.0
    assert len(h.batches) == 2
    # 加权成本: (20000*1.10 + 10000*1.20) / 30000 = 1.1333
    assert abs(h.cost_price - 1.1333) < 0.001
    assert h.cost_basis == 34000.0
    assert h.market_value == 37500.0
    assert h.floating_pnl == 3500.0


# =====================================================================
# 3. 7 天 1.50% 惩罚性赎回费强力拦截与 FIFO 逐级扣减
# =====================================================================

def test_fifo_redemption_penalty_interception(temp_pm):
    # 录入包含 < 7 天批次的持仓
    records = [
        {"fund_code": "011612", "buy_date": "2026-10-26", "shares": 5000.0, "cost_nav": 1.00, "current_nav": 1.00} # 持有仅 2 天
    ]
    temp_pm.takeover_mode_b(historical_records=records, available_cash=0.0, baseline_date="2026-10-28")

    # 尝试卖出未满 7 天批次，必须触发 PermissionError 强力阻断
    with pytest.raises(PermissionError) as exc_info:
        temp_pm.execute_fifo_redemption(fund_code="011612", shares_to_sell=2000.0, force_penalty=False)

    assert "7天安全红线拦截" in str(exc_info.value)
    assert "1.50%" in str(exc_info.value)

    # 验证强行卖出 (force_penalty=True) 能扣减并准确扣除 1.50% 手续费
    res_forced = temp_pm.execute_fifo_redemption(fund_code="011612", shares_to_sell=2000.0, force_penalty=True)
    assert res_forced["total_shares_redeemed"] == 2000.0
    assert res_forced["gross_amount"] == 2000.0
    assert res_forced["fee_amount"] == 30.0 # 2000 * 1.5% = 30.0
    assert res_forced["net_amount"] == 1970.0
    assert temp_pm.holdings["011612"].shares == 3000.0


def test_fifo_batch_ordering(temp_pm):
    # 两个批次：批次 1 持有 > 365 天 (满1年免赎回费 0.00%)，批次 2 持有 15 天 (赎回费 0.75%)
    records = [
        {"fund_code": "005561", "buy_date": "2025-01-01", "shares": 10000.0, "cost_nav": 1.10, "current_nav": 1.20},
        {"fund_code": "005561", "buy_date": "2026-10-13", "shares": 10000.0, "cost_nav": 1.15, "current_nav": 1.20}
    ]
    temp_pm.takeover_mode_b(historical_records=records, available_cash=0.0, baseline_date="2026-10-28")

    # 赎回 15000 份：应耗尽批次 1 (10000份，0%赎回费)，并从批次 2 扣减 5000 份 (0.75%赎回费)
    res = temp_pm.execute_fifo_redemption(fund_code="005561", shares_to_sell=15000.0)
    assert len(res["batch_details"]) == 2

    b1_detail = res["batch_details"][0]
    assert b1_detail["redeemed_shares"] == 10000.0
    assert b1_detail["fee_rate_pct"] == 0.00
    assert b1_detail["fee_amount"] == 0.00

    b2_detail = res["batch_details"][1]
    assert b2_detail["redeemed_shares"] == 5000.0
    assert b2_detail["fee_rate_pct"] == 0.75
    # 5000 * 1.20 * 0.75% = 45.0
    assert b2_detail["fee_amount"] == 45.0

    assert temp_pm.holdings["005561"].shares == 5000.0


# =====================================================================
# 4. 在途资金交收时差与三级路由优先级测试
# =====================================================================

def test_rebalance_routes_priorities(temp_pm):
    # 构建场景：持仓有 华夏科创50 C (011613, 华夏基金)，可用现金充裕
    records = [
        {"fund_code": "011613", "buy_date": "2026-09-01", "shares": 30000.0, "cost_nav": 1.00, "current_nav": 1.00}
    ]
    temp_pm.takeover_mode_b(historical_records=records, available_cash=50000.0, baseline_date="2026-10-28")

    # 目标配置：减仓 011613，换入同公司 011612 (华夏科创50 A) 与 创金合信 005561
    target_weights = {
        "011612": 0.30, # 华夏科创50 A (同属华夏基金 -> 应匹配为 PRIORITY_1_SWITCH)
        "005561": 0.50  # 创金合信红利低波 (跨公司，但现金充裕 -> 应匹配为 PRIORITY_2_CASH_ADVANCE)
    }

    plan = temp_pm.generate_rebalance_plan(target_weights=target_weights, min_buffer_pct=3.0)
    routes = plan["routes"]

    route_types = [r["route_priority"] for r in routes]
    assert "PRIORITY_1_SWITCH" in route_types
    assert "PRIORITY_2_CASH_ADVANCE" in route_types

    # 验证提交订单到 pending_orders
    oids = temp_pm.submit_rebalance_orders(routes)
    assert len(oids) >= 2
    assert len(temp_pm.pending_orders) >= 2

    # 验证在途现金与扣减
    assert any(o.action == "SWITCH" for o in temp_pm.pending_orders)
    assert any(o.action == "BUY" for o in temp_pm.pending_orders)


def test_rebalance_priority_3_two_step(temp_pm):
    # 场景：无可用现金 (available_cash=0)，且跨公司调仓 -> 必须进入 PRIORITY_3_TWO_STEP 两阶段
    records = [
        {"fund_code": "005561", "buy_date": "2026-09-01", "shares": 30000.0, "cost_nav": 1.00, "current_nav": 1.00}
    ]
    temp_pm.takeover_mode_b(historical_records=records, available_cash=0.0, baseline_date="2026-10-28")

    target_weights = {
        "011612": 0.50 # 华夏科创50 (不同公司，且现金不足)
    }

    plan = temp_pm.generate_rebalance_plan(target_weights=target_weights, min_buffer_pct=3.0)
    routes = plan["routes"]

    assert any(r["route_priority"] == "PRIORITY_3_TWO_STEP" for r in routes)


# =====================================================================
# 5. 在途待确认订单次日 (T+1) 真实净值对账校准
# =====================================================================

def test_pending_order_reconciliation(temp_pm):
    order = PendingOrder(
        order_id="ORD_REC_TEST_01",
        created_at="2026-10-27 14:35:00",
        effective_trade_date="2026-10-27",
        action="BUY",
        fund_code="005561",
        fund_name="创金合信中证红利低波动指数A",
        amount=10000.0,
        est_fee=15.0,
        est_confirm_date="2026-10-28",
        status="PENDING"
    )
    temp_pm.pending_orders.append(order)
    temp_pm.save_state(record_snapshot=True)

    # 次日以真实净值 1.2500 对账
    rec_res = temp_pm.reconcile_pending_order("ORD_REC_TEST_01", confirmed_nav=1.2500)
    assert rec_res["status"] == "SUCCESS"
    assert order.status == "CONFIRMED"

    # 验证新基金已入账，净买入金额 = 10000 / (1 + 0.15%) = 9985.02
    # 份额 = 9985.02 / 1.25 = 7988.02
    h = temp_pm.holdings["005561"]
    assert abs(h.shares - 7988.02) < 0.1
    assert h.current_nav == 1.2500


# =====================================================================
# 6. 单日限购额度拆单与备选标的溢出路由 (Quota & Fallback)
# =====================================================================

def test_quota_limit_and_fallback_routing(temp_pm):
    # 博时标普500 (050025) 模拟单日限购 500 元，备选 001071 (摩根标普500)
    temp_pm.available_cash = 20000.0
    temp_pm.takeover_mode_a(fund_items=[], available_cash=20000.0)

    # 目标买入标普 500 配置 5000 元 (大幅超出 500 元限购)
    target_weights = {
        "050025": 0.25 # 25% * 20000 = 5000 元
    }

    def mock_quota(fund_code, *args, **kwargs):
        code = str(fund_code).zfill(6)
        if code == "050025":
            return {"fund_code": "050025", "daily_limit": 500.0, "status": "限制大额", "is_limited": True}
        elif code == "001071":
            return {"fund_code": "001071", "daily_limit": 1e11, "status": "开放申购", "is_limited": False}
        return {"fund_code": code, "daily_limit": 1e11, "status": "开放申购", "is_limited": False}

    with patch("portfolio_manager.fetch_realtime_fund_quota", side_effect=mock_quota):
        plan = temp_pm.generate_rebalance_plan(target_weights=target_weights, min_buffer_pct=3.0)
        routes = plan["routes"]

        assert len(routes) == 1
        r_spx = routes[0]
        assert r_spx["buy_amount"] == 500.0 # 主基金锁定在单日限额 500 元
        assert r_spx["overflow_amount"] == 4500.0 # 超出部分 4500 元
        assert r_spx["fallback_code"] == "001071" # 路由至备选标的

        # 提交执行，应分裂生成两笔买入订单
        oids = temp_pm.submit_rebalance_orders(routes)
        assert len(oids) == 2
        assert any(o.fund_code == "050025" and o.amount == 500.0 for o in temp_pm.pending_orders)
        assert any(o.fund_code == "001071" and o.amount == 4500.0 for o in temp_pm.pending_orders)


# =====================================================================
# 7. 分红除权校准 (现金分红 vs 红利再投资)
# =====================================================================

def test_process_dividend(temp_pm):
    records = [
        {"fund_code": "005561", "buy_date": "2026-01-01", "shares": 10000.0, "cost_nav": 1.10, "current_nav": 1.30, "dividend_method": "cash"}
    ]
    temp_pm.takeover_mode_b(historical_records=records, available_cash=5000.0, baseline_date="2026-10-28")

    # 1. 测试现金分红：每份分红 0.05 元，除权净值 1.25
    div_res = temp_pm.process_dividend(fund_code="005561", dividend_per_share=0.05, ex_nav=1.25)
    assert div_res["dividend_cash"] == 500.0 # 10000 * 0.05
    assert temp_pm.available_cash == 5500.0 # 5000 + 500
    assert temp_pm.holdings["005561"].current_nav == 1.25
    assert temp_pm.holdings["005561"].shares == 10000.0

    # 2. 测试红利再投资：每份分红 0.10 元，折算新增份额免申购费入账
    div_reinvest_res = temp_pm.process_dividend(fund_code="005561", dividend_per_share=0.10, ex_nav=1.20, force_method="reinvest")
    assert div_reinvest_res["dividend_cash"] == 1000.0 # 10000 * 0.10
    # 转换为 1000 / 1.20 = 833.33 份
    assert abs(temp_pm.holdings["005561"].shares - 10833.33) < 0.1


# =====================================================================
# 8. 场内 ETF 溢价率监控 (> 0.8% 预警)
# =====================================================================

def test_check_etf_premiums(temp_pm):
    test_quotes = {
        "510300": {"price": 3.980, "iopv": 3.975, "name": "沪深300ETF"}, # 溢价 0.12% < 0.8%
        "588000": {"price": 1.050, "iopv": 1.035, "name": "科创50ETF"}   # 溢价 1.45% > 0.8%
    }
    alerts = temp_pm.check_etf_premiums(test_quotes)
    assert len(alerts) == 1
    assert alerts[0]["code"] == "588000"
    assert alerts[0]["premium_pct"] > 0.8
    assert "高溢价" in alerts[0]["warning_msg"]


# =====================================================================
# 9. 持久化存储与 Undo 快照一键回滚测试
# =====================================================================

def test_persistence_and_undo(temp_pm):
    temp_pm.takeover_mode_a(
        fund_items=[{"fund_code": "005561", "amount": 20000.0, "nav": 1.20}],
        available_cash=10000.0
    )
    initial_shares = temp_pm.holdings["005561"].shares

    # 进行修改
    temp_pm.available_cash = 50000.0
    temp_pm.save_state(record_snapshot=True)
    assert temp_pm.available_cash == 50000.0

    # 一键撤销回滚
    undo_ok = temp_pm.undo()
    assert undo_ok
    assert temp_pm.available_cash == 10000.0
    assert temp_pm.holdings["005561"].shares == initial_shares


# =====================================================================
# 10. 演示实盘组合完整载入测试
# =====================================================================

def test_load_demo_portfolio(temp_pm):
    res = temp_pm.load_demo_portfolio()
    assert res["status"] == "SUCCESS"
    assert res["holdings_count"] == 6
    assert res["pending_orders_count"] == 1
    assert "005561" in temp_pm.holdings
    assert "011612" in temp_pm.holdings # 未满 7 天新买基
    assert "011613" in temp_pm.holdings # 待满 30 天基
    assert "013841" in temp_pm.holdings # 非标深套基


# =====================================================================
# 11. 纯减仓卖出路由生成与在途现金闭环测试
# =====================================================================

def test_pure_sell_route_generation(temp_pm):
    # 构建场景：持仓有 005561 (40,000元)，无买入目标，要求全部卖出降仓变现
    records = [
        {"fund_code": "005561", "buy_date": "2026-06-01", "shares": 30000.0, "cost_nav": 1.00, "current_nav": 1.20}
    ]
    temp_pm.takeover_mode_b(historical_records=records, available_cash=10000.0, baseline_date="2026-10-28")

    # 目标配置：005561 清仓，全部持有现金
    plan = temp_pm.generate_rebalance_plan(target_weights={"005561": 0.0}, min_buffer_pct=3.0)
    routes = plan["routes"]

    assert len(routes) == 1
    r = routes[0]
    assert r["route_priority"] == "SELL_TO_CASH"
    assert r["fund_code"] == "005561"
    assert r["shares_to_sell"] == 30000.0

    # 提交执行，应从 holdings 扣减 005561 份额，并生成 SELL 在途订单
    oids = temp_pm.submit_rebalance_orders(routes)
    assert len(oids) == 1
    assert "005561" not in temp_pm.holdings # 份额已被扣减，杜绝双重计算
    assert temp_pm.in_transit_cash > 0 # 转入在途资金


# =====================================================================
# 12. 基金转换 (SWITCH) 转出基金份额立即扣减与防虚增测试
# =====================================================================

def test_switch_deducts_source_fund_shares(temp_pm):
    # 持有 华夏科创50 C (011613) 30000 份
    records = [
        {"fund_code": "011613", "buy_date": "2026-08-01", "shares": 30000.0, "cost_nav": 1.00, "current_nav": 1.00}
    ]
    temp_pm.takeover_mode_b(historical_records=records, available_cash=0.0, baseline_date="2026-10-28")

    # 目标：转换 20000 份至同公司华夏科创50 A (011612)
    # 011612 占比 20000 / 30000 = 66.67%
    target_weights = {"011612": 0.6667}
    plan = temp_pm.generate_rebalance_plan(target_weights=target_weights, min_buffer_pct=3.0)
    routes = [r for r in plan["routes"] if r["route_priority"] == "PRIORITY_1_SWITCH"]
    assert len(routes) == 1

    # 提交执行转换
    temp_pm.submit_rebalance_orders(routes)

    # 核心验证：转出标的 011613 必须已被扣减对应份额，不再保留全部 30000 份！
    assert "011613" in temp_pm.holdings
    rem_shares = temp_pm.holdings["011613"].shares
    assert abs(rem_shares - 10000.0) <= 2.0 # 30000 - 20001 = 9999 份 (容忍 66.67% 四舍五入误差)


# =====================================================================
# 13. 单只基金安全增补与删除 (不冲刷其余持仓) 测试
# =====================================================================

def test_single_fund_add_and_delete(temp_pm):
    temp_pm.takeover_mode_a(
        fund_items=[{"fund_code": "005561", "amount": 20000.0, "nav": 1.20}],
        available_cash=10000.0
    )
    assert len(temp_pm.holdings) == 1

    # 单只新增 100032，不影响 005561
    res_add = temp_pm.add_or_update_holding(
        fund_code="100032",
        shares=10000.0,
        nav=1.0500,
        holding_days=15,
        dividend_method="cash"
    )
    assert res_add["status"] == "SUCCESS"
    assert len(temp_pm.holdings) == 2
    assert "005561" in temp_pm.holdings
    assert "100032" in temp_pm.holdings

    # 删除 005561
    del_ok = temp_pm.delete_holding("005561")
    assert del_ok
    assert len(temp_pm.holdings) == 1
    assert "005561" not in temp_pm.holdings
    assert "100032" in temp_pm.holdings


# =====================================================================
# 14. CSV / Excel 历史交易明细导入 (模式 B) 与快照导入导出测试
# =====================================================================

def test_csv_import_mode_b(temp_pm):
    import pandas as pd
    df_raw = pd.DataFrame([
        {"代码": "005561", "买入日期": "2026-05-01", "确认份额": 15000.0, "成本净值": 1.10, "当前净值": 1.25, "手续费": 5.0, "分红方式": "cash"},
        {"代码": "100032", "买入日期": "2026-08-10", "确认份额": 20000.0, "成本净值": 0.95, "当前净值": 1.08, "手续费": 8.0, "分红方式": "cash"}
    ])
    res = temp_pm.import_historical_transactions_df(df_raw, available_cash=25000.0, baseline_date="2026-10-28")
    assert res["status"] == "SUCCESS"
    assert len(temp_pm.holdings) == 2
    assert temp_pm.available_cash == 25000.0
    assert temp_pm.holdings["005561"].shares == 15000.0

    # 导出快照并重新导入
    df_snap = temp_pm.export_snapshot_df()
    assert not df_snap.empty
    assert "基金代码" in df_snap.columns

    temp_pm.holdings.clear()
    imp_snap_res = temp_pm.import_snapshot_df(df_snap)
    assert imp_snap_res["status"] == "SUCCESS"
    assert len(temp_pm.holdings) == 2


# =====================================================================
# 15. 基准重置、超额收益 (Alpha) 与最大回撤动态追踪测试
# =====================================================================

def test_benchmark_reset_and_alpha_drawdown(temp_pm):
    temp_pm.takeover_mode_a(
        fund_items=[{"fund_code": "005561", "amount": 100000.0, "nav": 1.00}],
        available_cash=0.0,
        benchmark_nav=1000.0
    )
    assert temp_pm.baseline_equity == 100000.0
    assert temp_pm.peak_equity == 100000.0
    assert temp_pm.max_drawdown_pct == 0.0

    # 基金净值上涨到 1.15 (组合涨 +15%)，基准点位涨到 1050 (基准涨 +5%)
    temp_pm.holdings["005561"].current_nav = 1.15
    diag = temp_pm.update_benchmark_and_drawdown(current_benchmark_nav=1050.0)

    assert diag["portfolio_return_pct"] == 15.0
    assert diag["benchmark_return_pct"] == 5.0
    assert diag["alpha_return_pct"] == 10.0 # Alpha = 15% - 5% = +10%
    assert temp_pm.peak_equity == 115000.0

    # 基金净值回调至 1.035 (组合从 115,000 跌至 103,500，回撤 10%)
    temp_pm.holdings["005561"].current_nav = 1.035
    diag2 = temp_pm.update_benchmark_and_drawdown(current_benchmark_nav=1040.0)
    assert diag2["max_drawdown_pct"] == 10.0 # 峰值回撤 10%


# =====================================================================
# 16. 穿透行业暴露加权计算与重仓股重合度热力图测试
# =====================================================================

def test_look_through_industry_and_stock_overlap(temp_pm):
    # 装载演示组合 (含 011612 与 013841)
    temp_pm.load_demo_portfolio()

    # 穿透行业分布
    df_ind = temp_pm.calculate_look_through_industry_exposure()
    assert not df_ind.empty
    assert "行业" in df_ind.columns
    assert "暴露占比(%)" in df_ind.columns
    # 行业暴露总和应接近 100%
    assert abs(df_ind["暴露占比(%)"].sum() - 100.0) < 5.0

    # 前十大重仓股重合度
    overlap_res = temp_pm.calculate_stock_overlap_matrix()
    matrix = overlap_res["matrix"]
    alerts = overlap_res["alerts"]
    assert matrix.shape[0] >= 2
    # 011612 (科创50) 与 013841 (芯片混合) 应触发伪分散重合度报警
    has_chip_alert = any("011612" in a["fund1"] or "011612" in a["fund2"] for a in alerts)
    assert has_chip_alert


# =====================================================================
# 17. 现金分红成本净值调降防虚假暴跌测试
# =====================================================================

def test_ex_dividend_cost_nav_adjustment(temp_pm):
    records = [
        {"fund_code": "005561", "buy_date": "2026-01-01", "shares": 10000.0, "cost_nav": 1.20, "current_nav": 1.30, "dividend_method": "cash"}
    ]
    temp_pm.takeover_mode_b(historical_records=records, available_cash=5000.0, baseline_date="2026-10-28")

    # 现金分红 0.10 元，除权净值 1.20
    div_res = temp_pm.process_dividend(fund_code="005561", dividend_per_share=0.10, ex_nav=1.20)
    assert div_res["dividend_cash"] == 1000.0

    # 核心验证：批次成本净值从 1.20 自动折算调低至 1.10，绝不产生账面虚假亏损！
    h = temp_pm.holdings["005561"]
    assert h.batches[0].cost_nav == 1.10
    assert h.floating_pnl == 1000.0 # 10000 * (1.20 - 1.10) = 1000.0 盈余保持一致！


# =====================================================================
# 18. R1: 账户账本基准重置、回撤清零与核心伴生标的无替换标签测试
# =====================================================================

def test_r1_portfolio_state_reset_and_core_strategy_tags(temp_pm):
    # 模拟旧组合残留污染状态
    temp_pm.peak_equity = 999999.0
    temp_pm.max_drawdown_pct = 75.5
    temp_pm.portfolio_return_pct = -45.0
    temp_pm.benchmark_return_pct = -30.0
    temp_pm.alpha_return_pct = -15.0

    bp = PortfolioManager.generate_zero_start_blueprint(total_capital=100000.0, tier="C3")
    res = temp_pm.apply_zero_start_blueprint(bp)

    assert res["status"] == "SUCCESS"
    assert temp_pm.baseline_equity == 100000.0
    assert abs(temp_pm.peak_equity - 100000.0) <= 0.05
    assert temp_pm.max_drawdown_pct == 0.0
    assert temp_pm.portfolio_return_pct == 0.0
    assert temp_pm.benchmark_return_pct == 0.0
    assert temp_pm.alpha_return_pct == 0.0

    # 验证所有核心标的与伴生标的均被打上核心策略底仓标签，严禁包含“替换”
    for code, h in temp_pm.holdings.items():
        assert h.is_core_strategy is True, f"Holding {code} should be core strategy"
        assert h.transition_tag == "核心策略底仓", f"Holding {code} tag: {h.transition_tag}"
        assert "替换" not in (h.transition_tag or "")

    # 验证 takeover_mode_a 状态清零
    temp_pm.peak_equity = 888888.0
    temp_pm.max_drawdown_pct = 60.0
    temp_pm.takeover_mode_a([
        {"fund_code": "100032", "amount": 60000.0, "nav": 1.0},
        {"fund_code": "002351", "amount": 40000.0, "nav": 1.0}
    ], available_cash=0.0)
    assert temp_pm.baseline_equity == 100000.0
    assert temp_pm.peak_equity == 100000.0
    assert temp_pm.max_drawdown_pct == 0.0

    # 验证 import_from_smart_text replace_existing 状态清零
    temp_pm.peak_equity = 777777.0
    temp_pm.max_drawdown_pct = 50.0
    smart_input = "100032 50000元；002351 50000元"
    temp_pm.import_from_smart_text(smart_input, available_cash=0.0, replace_existing=True)
    assert temp_pm.baseline_equity == 100000.0
    assert temp_pm.peak_equity == 100000.0
    assert temp_pm.max_drawdown_pct == 0.0


# =====================================================================
# 19. R3: 金融股存贷双高排雷豁免与底层重仓股去重合并宽表测试
# =====================================================================

def test_r3_financial_stock_double_high_exemption_and_look_through_df(temp_pm):
    # 验证 100032 中招商银行、农业银行、交通银行、江苏银行存贷双高豁免
    res_100032 = temp_pm.screen_fund_look_through_risk("100032")
    bank_stocks = [s for s in res_100032["top_stocks_screen"] if any(b in s["stock_name"] for b in ["银行", "农商"])]
    assert len(bank_stocks) >= 3
    for s in bank_stocks:
        assert s["double_high_risk"] is False, f"Bank {s['stock_name']} double_high_risk should be False"
        assert s["double_high_status"] == "金融业豁免（正常）", f"Status mismatch for {s['stock_name']}: {s['double_high_status']}"
        assert not any("存贷双高" in d[0] for d in s["deductions_detail"]), f"Bank {s['stock_name']} should not have double_high deduction"

    # 验证 005561 中江苏银行、农业银行、交通银行、北京银行等豁免
    res_005561 = temp_pm.screen_fund_look_through_risk("005561")
    bank_stocks_005561 = [s for s in res_005561["top_stocks_screen"] if any(b in s["stock_name"] for b in ["银行", "农商"])]
    assert len(bank_stocks_005561) >= 4
    for s in bank_stocks_005561:
        assert s["double_high_risk"] is False
        assert s["double_high_status"] == "金融业豁免（正常）"

    # 验证底层重仓股穿透去重合并与排序
    temp_pm.takeover_mode_a([
        {"fund_code": "100032", "amount": 60000.0, "nav": 1.0},
        {"fund_code": "005561", "amount": 40000.0, "nav": 1.0}
    ], available_cash=0.0)

    df_look = temp_pm.get_portfolio_look_through_stocks_df()
    assert not df_look.empty
    assert "关联持仓基金" in df_look.columns
    assert "占组合总市值比例(%)" in df_look.columns

    # 验证股票代码唯一去重
    stock_names = df_look["股票名称"].tolist()
    assert len(stock_names) == len(set(stock_names)), "Look-through stocks must be aggregated to unique rows"

    # 共同持仓股 (如江苏银行、农业银行、中国神华) 关联持仓基金列出两只基金
    sh_row = df_look[df_look["股票名称"] == "中国神华"].iloc[0]
    assert "005561" in sh_row["关联持仓基金"] and "100032" in sh_row["关联持仓基金"]

    # 验证按持仓占比降序排列
    weights = df_look["占组合总市值比例(%)"].tolist()
    assert weights == sorted(weights, reverse=True)


# =====================================================================
# 20. R4: 限购拆单前后表格一致性与同源份额重合度误报豁免测试
# =====================================================================

def test_r4_quota_split_blueprint_consistency_and_overlap_exemption(temp_pm):
    # 验证 generate_zero_start_blueprint 超限额自动拆单为两行独立记录
    def mock_quota(fund_code, *args, **kwargs):
        code = str(fund_code).zfill(6)
        if code == "050025":
            return {"fund_code": "050025", "daily_limit": 500.0, "status": "限制大额", "is_limited": True}
        elif code == "001071":
            return {"fund_code": "001071", "daily_limit": 1e11, "status": "开放申购", "is_limited": False}
        return {"fund_code": code, "daily_limit": 1e11, "status": "开放申购", "is_limited": False}

    with patch("portfolio_manager.fetch_realtime_fund_quota", side_effect=mock_quota):
        bp = PortfolioManager.generate_zero_start_blueprint(total_capital=100000.0, tier="C3")
        items = bp["items"]

        # 050025 分配金额 6,000 元 > daily_limit 500 元
        spx_050025 = [it for it in items if it["fund_code"] == "050025"]
        spx_001071 = [it for it in items if it["fund_code"] == "001071"]
        assert len(spx_050025) == 1
        assert len(spx_001071) == 1
        assert spx_050025[0]["allocated_amount"] == 500.0
        assert spx_001071[0]["allocated_amount"] == 5500.0
        assert spx_050025[0]["target_weight_pct"] == 0.5
        assert spx_001071[0]["target_weight_pct"] == 5.5

    # 验证官方限购拆单伴生组在 calculate_stock_overlap_matrix 中豁免伪分散报警
    temp_pm.takeover_mode_a([
        {"fund_code": "050025", "amount": 500.0, "nav": 1.0},
        {"fund_code": "001071", "amount": 5500.0, "nav": 1.0},
        {"fund_code": "011612", "amount": 10000.0, "nav": 1.0},
        {"fund_code": "011613", "amount": 10000.0, "nav": 1.0}
    ], available_cash=0.0)

    overlap_res = temp_pm.calculate_stock_overlap_matrix()
    alerts = overlap_res["alerts"]
    exempt_pairs = overlap_res.get("exempt_pairs", [])

    # 050025 与 001071 绝不报警
    has_spx_alert = any(
        ("050025" in a.get("fund1", "") and "001071" in a.get("fund2", "")) or
        ("001071" in a.get("fund1", "") and "050025" in a.get("fund2", ""))
        for a in alerts
    )
    assert not has_spx_alert, "Official quota split pair 050025 & 001071 must not trigger alert"

    # 011612 与 011613 (同一指数 A/C 份额) 绝不报警
    has_ac_alert = any(
        ("011612" in a.get("fund1", "") and "011613" in a.get("fund2", "")) or
        ("011613" in a.get("fund1", "") and "011612" in a.get("fund2", ""))
        for a in alerts
    )
    assert not has_ac_alert, "Same index A/C share pair 011612 & 011613 must not trigger alert"

    # 豁免清单中明确记录说明
    exempt_pair_keys = [frozenset({p["fund1"], p["fund2"]}) for p in exempt_pairs]
    assert frozenset({"050025", "001071"}) in exempt_pair_keys
    assert frozenset({"011612", "011613"}) in exempt_pair_keys


def test_dual_dividend_exemption_and_max_non_diag_unexcused(temp_pm):
    """
    R4 核心测试：策略推荐双红利底仓对 (100032 + 005561) 协同豁免与 max_non_diag_unexcused 精算
    1. 标准推荐组合 (100032 + 005561 + 002351 + 000216 + 050025) 绝不触发任何伪分散告警；
    2. exempt_pairs 明确收录 100032 与 005561 且说明包含 '双红利'；
    3. max_non_diag_unexcused 严格为 0.0；
    4. 对抗测试：引入非豁免且高重合组合 (011612 与 013841) 必须真实触发警报且 max_non_diag_unexcused >= 0.40。
    """
    temp_pm.holdings.clear()
    temp_pm.takeover_mode_a([
        {"fund_code": "100032", "amount": 38000.0, "nav": 1.0, "share_class": "A"},
        {"fund_code": "005561", "amount": 30000.0, "nav": 1.0, "share_class": "A"},
        {"fund_code": "002351", "amount": 14000.0, "nav": 1.0, "share_class": "A"},
        {"fund_code": "000216", "amount": 12000.0, "nav": 1.0, "share_class": "A"},
        {"fund_code": "050025", "amount": 6000.0, "nav": 1.0, "share_class": "A"}
    ], available_cash=0.0)

    res = temp_pm.calculate_stock_overlap_matrix()
    alerts = res.get("alerts", [])
    exempt_pairs = res.get("exempt_pairs", [])
    max_unexcused = res.get("max_non_diag_unexcused", 0.0)

    # 1. 绝不触发任何告警
    assert len(alerts) == 0, f"标准推荐组合严禁触发伪分散告警，实际告警: {alerts}"
    assert max_unexcused < 0.40, f"非豁免最大重合度必须小于 0.40，实际为 {max_unexcused}"
    assert max_unexcused == 0.0, f"标准组合中非豁免对重叠度应为 0.0，实际为 {max_unexcused}"

    # 2. 检查双红利底仓对进入 exempt_pairs
    exempt_sets = [frozenset({p["fund1"], p["fund2"]}) for p in exempt_pairs]
    assert frozenset({"100032", "005561"}) in exempt_sets, "100032 与 005561 必须被纳入豁免池"
    pair_item = next(p for p in exempt_pairs if frozenset({p["fund1"], p["fund2"]}) == frozenset({"100032", "005561"}))
    assert "双红利" in pair_item.get("note", "") or "协同" in pair_item.get("note", "")

    # 3. 对抗测试：加入非豁免高重合基金 (011612 与 013841)
    temp_pm.takeover_mode_a([
        {"fund_code": "011612", "amount": 50000.0, "nav": 1.0, "share_class": "A"},
        {"fund_code": "013841", "amount": 50000.0, "nav": 1.0, "share_class": "C"}
    ], available_cash=0.0)
    adv_res = temp_pm.calculate_stock_overlap_matrix()
    adv_alerts = adv_res.get("alerts", [])
    adv_max_unexcused = adv_res.get("max_non_diag_unexcused", 0.0)

    assert len(adv_alerts) >= 1, "非豁免高重合基金必须触发伪分散告警"
    assert adv_max_unexcused >= 0.40, f"非豁免最大重合度应 >= 0.40，实际为 {adv_max_unexcused}"



