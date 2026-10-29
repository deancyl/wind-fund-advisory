"""
A 股公募基金交易时钟与全维手续费精算引擎单元测试套件
"""

from datetime import datetime, date, time
import pytest
import pandas as pd

from trading_clock_fee import TradingClock, FeeMatrixCalculator, MarketWindowStatus


@pytest.fixture
def clock():
    return TradingClock()


@pytest.fixture
def calc():
    return FeeMatrixCalculator()


def test_trading_clock_trade_days(clock):
    # 周末应判定为非交易日 (无论是否有外部日历)
    saturday = date(2026, 10, 24)
    sunday = date(2026, 10, 25)
    monday = date(2026, 10, 26)

    assert not clock.is_trade_day(saturday)
    assert not clock.is_trade_day(sunday)
    assert clock.is_trade_day(monday)


def test_trading_clock_offsets(clock):
    monday = date(2026, 10, 26)
    t_plus_1 = clock.get_offset_trade_day(monday, 1)
    t_plus_2 = clock.get_offset_trade_day(monday, 2)

    assert t_plus_1 == "2026-10-27"
    assert t_plus_2 == "2026-10-28"


def test_trading_clock_windows(clock):
    trade_date = date(2026, 10, 26)

    # 1. 盘前准备期 (09:00)
    dt_pre = datetime.combine(trade_date, time(9, 0, 0))
    st_pre = clock.get_market_window_status(dt_pre)
    assert st_pre.window_type == "CLOSED_PREMARKET"
    assert st_pre.effective_trade_date == "2026-10-26"
    assert not st_pre.is_golden_window

    # 2. 盘中观察期 (10:30)
    dt_obs = datetime.combine(trade_date, time(10, 30, 0))
    st_obs = clock.get_market_window_status(dt_obs)
    assert st_obs.window_type == "OBSERVATION"
    assert st_obs.effective_trade_date == "2026-10-26"
    assert not st_obs.is_golden_window

    # 3. 🟢 黄金执行窗口 (14:35)
    dt_golden = datetime.combine(trade_date, time(14, 35, 0))
    st_golden = clock.get_market_window_status(dt_golden)
    assert st_golden.window_type == "GOLDEN_WINDOW"
    assert st_golden.is_golden_window
    assert st_golden.effective_trade_date == "2026-10-26"
    assert "25:" in st_golden.countdown_str  # 距 15:00 还剩 25 分钟

    # 4. 临界关账窗口 (14:58)
    dt_crit = datetime.combine(trade_date, time(14, 58, 0))
    st_crit = clock.get_market_window_status(dt_crit)
    assert st_crit.window_type == "CRITICAL_CLOSING"

    # 5. 15:00 之后延时窗口 (15:05)
    dt_post = datetime.combine(trade_date, time(15, 5, 0))
    st_post = clock.get_market_window_status(dt_post)
    assert st_post.window_type == "POST_MARKET_DELAYED"
    assert st_post.is_after_market
    assert st_post.effective_trade_date == "2026-10-27"


def test_settlement_dates_calculation(clock):
    trade_date = date(2026, 10, 26)

    # 15:00 前申报
    dt_before_15 = datetime.combine(trade_date, time(14, 30, 0))
    res = clock.calculate_settlement_dates(dt_before_15, confirm_cycle="T+1", arrive_cycle="T+2")
    assert res["effective_trade_date"] == "2026-10-26"
    assert res["confirm_date"] == "2026-10-27"
    assert res["arrive_date"] == "2026-10-28"
    assert not res["is_delayed"]

    # 15:00 之后申报
    dt_after_15 = datetime.combine(trade_date, time(15, 10, 0))
    res_delayed = clock.calculate_settlement_dates(dt_after_15, confirm_cycle="T+1", arrive_cycle="T+2")
    assert res_delayed["effective_trade_date"] == "2026-10-27"
    assert res_delayed["confirm_date"] == "2026-10-28"
    assert res_delayed["arrive_date"] == "2026-10-29"
    assert res_delayed["is_delayed"]


def test_fee_calculator_redemption_tiers(calc):
    # A 类持有期梯级测试
    r_a_3d, is_pen_a, _ = calc.get_redemption_fee_rate("A", 3)
    assert r_a_3d == 0.0150
    assert is_pen_a

    r_a_15d, is_pen_a15, _ = calc.get_redemption_fee_rate("A", 15)
    assert r_a_15d == 0.0075
    assert not is_pen_a15

    r_a_60d, _, _ = calc.get_redemption_fee_rate("A", 60)
    assert r_a_60d == 0.0050

    r_a_200d, _, _ = calc.get_redemption_fee_rate("A", 200)
    assert r_a_200d == 0.0025

    r_a_400d, _, _ = calc.get_redemption_fee_rate("A", 400)
    assert r_a_400d == 0.0000

    # C 类持有期梯级测试
    r_c_3d, is_pen_c, _ = calc.get_redemption_fee_rate("C", 3)
    assert r_c_3d == 0.0150
    assert is_pen_c

    r_c_15d, _, _ = calc.get_redemption_fee_rate("C", 15)
    assert r_c_15d == 0.0050

    r_c_35d, is_pen_c35, _ = calc.get_redemption_fee_rate("C", 35)
    assert r_c_35d == 0.0000
    assert not is_pen_c35


def test_subscription_fee_calculator(calc):
    # A 类 1 折申购费
    sub_a = calc.calculate_subscription_fee(10000.0, share_class="A", discount=0.10, standard_rate=0.015)
    assert sub_a["fee_rate_pct"] == 0.15
    assert sub_a["fee_amount"] == 14.98
    assert sub_a["net_investment"] == 9985.02

    # C 类 0 申购费
    sub_c = calc.calculate_subscription_fee(10000.0, share_class="C")
    assert sub_c["fee_rate_pct"] == 0.0
    assert sub_c["fee_amount"] == 0.0
    assert sub_c["net_investment"] == 10000.0


def test_break_even_days_calculator(calc):
    res = calc.calculate_break_even_days(
        standard_sub_rate=0.015,
        discount=0.10,
        sales_service_annual_rate=0.0040,
        max_days=365
    )
    assert "break_even_day" in res
    assert 30 <= res["break_even_day"] <= 365
    assert "curve_df" in res
    assert len(res["curve_df"]) == 365


def test_delayed_rebalance_evaluation(calc):
    # 持有 C 类 28 天 (差 2 天满 30 天免赎回费)
    res_28d = calc.evaluate_delayed_rebalance(
        holding_days=28,
        share_class="C",
        market_value=50000.0,
        expected_annual_alpha=0.08,
        max_lookahead_days=5
    )
    assert res_28d["is_in_delay_window"]
    assert res_28d["wait_days"] == 2
    assert res_28d["rate_now"] == 0.0050
    assert res_28d["rate_next"] == 0.0000
    assert res_28d["fee_saved"] == 250.0  # 50000 * 0.5%
    assert res_28d["should_delay"]
    assert res_28d["recommendation"] == "LOCK_UNTIL_MATURE"

    # 持有 C 类 45 天 (已远超 30 天，不在临界窗口)
    res_45d = calc.evaluate_delayed_rebalance(
        holding_days=45,
        share_class="C",
        market_value=50000.0
    )
    assert not res_45d["is_in_delay_window"]
    assert res_45d["recommendation"] == "EXECUTE_NOW"


def test_rebalance_buffer_filtering(calc):
    # 权重偏离度仅 1.5% < 3.0% 门槛
    res_filter = calc.is_rebalance_actionable(
        current_weight=0.35,
        target_weight=0.365,
        portfolio_equity=100000.0,
        min_buffer_pct=3.0
    )
    assert not res_filter["actionable"]
    assert "偏离度不足3%过滤" in res_filter["reason"] or "< 最小调仓过滤门槛" in res_filter["reason"]

    # 权重偏离度 5.0% >= 3.0% 门槛
    res_pass = calc.is_rebalance_actionable(
        current_weight=0.35,
        target_weight=0.40,
        portfolio_equity=100000.0,
        min_buffer_pct=3.0
    )
    assert res_pass["actionable"]


def test_break_even_days_target_recommendation(calc):
    # 测试指定 20 天短期战术持有期 (应强力推荐 C 类)
    res_20d = calc.calculate_break_even_days(
        standard_sub_rate=0.015,
        discount=0.10,
        sales_service_annual_rate=0.0040,
        max_days=365,
        target_holding_days=20,
        investment_amount=50000.0
    )
    assert res_20d["target_recommendation"]["recommended_class"] == "C"
    assert res_20d["target_recommendation"]["saving_amount"] > 0
    assert "推荐选择【C 类份额】" in res_20d["target_recommendation"]["summary"]

    # 测试指定 365 天长线战略底仓持有期 (应强力推荐 A 类)
    res_365d = calc.calculate_break_even_days(
        standard_sub_rate=0.015,
        discount=0.10,
        sales_service_annual_rate=0.0040,
        max_days=365,
        target_holding_days=365,
        investment_amount=50000.0
    )
    assert res_365d["target_recommendation"]["recommended_class"] == "A"
    assert res_365d["target_recommendation"]["saving_amount"] > 0
    assert "推荐选择【A 类份额】" in res_365d["target_recommendation"]["summary"]

