"""
单元测试集：实盘核心升级与交易员挑刺系统级修复验证 (tests/test_live_rebalance_upgrades.py)

验证范围：
1. data_loader: 破除硬编码日期与动态 sync_latest_market_data() 增量对齐；
2. strategy_bridge: stitch_today_live_tail() 盘中尾盘动态拼接；
3. strategy_bridge: get_rebalance_grid_status() 10日调仓网格日历与紧急破位阈值；
4. portfolio_manager: check_etf_premiums() 实时估值 IOPV 口径与 QDII/黄金溢价防割肉；
5. portfolio_manager: generate_incremental_investment_plan() 发工资/增量资金免赎回费智能补仓；
6. portfolio_manager: calculate_intraday_pnl() 盘中实时预估浮盈亏与 95% 仓位法规系数校准；
7. strategy_bridge: get_backtest_nav_and_drawdown() 双口径净值（指数理论 vs 场外联接 95% 仓位）。
"""

from datetime import datetime
import pandas as pd
import pytest

from data_loader import DataLoader
from strategy_bridge import StrategyBridge
from portfolio_manager import PortfolioManager, FundHolding, HoldingBatch


@pytest.fixture
def temp_pm(tmp_path):
    db_file = tmp_path / "test_live_state.db"
    json_file = tmp_path / "test_live_ledger.json"
    pm = PortfolioManager(db_path=db_file, ledger_json_path=json_file)
    return pm


# =====================================================================
# 1. data_loader: 增量行情同步与动态日期检测
# =====================================================================

def test_sync_latest_market_data_structure():
    """验证 sync_latest_market_data 能正确识别本地 parquet 结构并返回有效数据框"""
    df = DataLoader.sync_latest_market_data()
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "date" in df.columns
    assert len(df) >= 2138
    assert "H00300" in df.columns
    assert "BENCHMARK_50_50" in df.columns


# =====================================================================
# 2. strategy_bridge: stitch_today_live_tail 盘中动态拼接
# =====================================================================

def test_stitch_today_live_tail_forced():
    """验证强制开启 force_live 时，能够动态拼接今日盘中实时虚拟行"""
    df_raw = StrategyBridge.load_matrix(force_reload=False)
    assert not df_raw.empty
    original_len = len(df_raw)

    df_stitched, is_stitched = StrategyBridge.stitch_today_live_tail(df_raw, force_live=True)
    assert is_stitched is True
    assert len(df_stitched) == original_len + 1

    last_row = df_stitched.iloc[-1]
    today_str = datetime.now().strftime("%Y-%m-%d")
    assert str(last_row["date"])[:10] == today_str

    # 验证关键资产列全部存在且为有效浮点数
    for col in ["H00300", "H00905", "H00852", "STAR50_STITCH", "H00922", "H30269", "930609", "AU9999", "SPX_CNY"]:
        assert col in df_stitched.columns
        assert not pd.isna(last_row[col])
        assert last_row[col] > 0


# =====================================================================
# 3. strategy_bridge: get_rebalance_grid_status 10日调仓网格与紧急破位阈值
# =====================================================================

def test_get_rebalance_grid_status():
    """验证 10 日调仓网格计算、倒计时及紧急破位阈值有效性"""
    grid = StrategyBridge.get_rebalance_grid_status()
    assert isinstance(grid, dict)
    assert "rebal_period" in grid
    assert "days_since_rebal" in grid
    assert "days_to_next_rebal" in grid
    assert 0 <= grid["days_to_next_rebal"] <= 10
    assert "is_rebal_day" in grid
    assert "next_rebal_date" in grid
    assert "c300_current" in grid
    assert "breakdown_threshold_c300" in grid
    assert grid["surge_threshold_pct"] == 3.9
    assert "surge_threshold_c300" in grid
    assert "countdown_display" in grid
    assert "emergency_warning" in grid


def test_snapshot_includes_rebal_grid_and_live_tail():
    """验证最新市场快照包含网格状态与实时尾盘元数据"""
    snapshot = StrategyBridge.get_latest_market_snapshot(force_reload=True, force_live_tail=True)
    assert "rebal_grid" in snapshot
    assert "is_live_tail_stitched" in snapshot
    assert "live_tail_timestamp" in snapshot
    assert snapshot["is_live_tail_stitched"] is True
    StrategyBridge._cached_snapshot = None


# =====================================================================
# 4. portfolio_manager: check_etf_premiums 实时估值 IOPV 口径
# =====================================================================

def test_check_etf_premiums_accuracy(temp_pm):
    """验证 ETF IOPV 溢价计算：A股ETF联动跟踪指数盘中涨跌幅、QDII/黄金识别溢价及时间戳"""
    alerts = temp_pm.check_etf_premiums()
    assert isinstance(alerts, list)
    assert len(alerts) >= 1  # 含有高溢价标的预警 (例如 159941 纳指ETF 或 豆粕ETF)

    for p in alerts:
        assert "code" in p
        assert "name" in p
        assert "price" in p
        assert "iopv" in p
        assert "premium_pct" in p
        assert "timestamp" in p
        assert "warning_msg" in p
        assert p["price"] > 0
        assert p["iopv"] > 0
        assert p["premium_pct"] > 0.8
        expected_premium = round(((p["price"] - p["iopv"]) / p["iopv"]) * 100.0, 3)
        assert abs(p["premium_pct"] - expected_premium) < 1e-2


# =====================================================================
# 5. portfolio_manager: generate_incremental_investment_plan 增量补仓
# =====================================================================

def test_generate_incremental_investment_plan(temp_pm):
    """验证增量免赎回费智能补仓：100% 纯买入、0 卖出、0 赎回费"""
    # 初始化部分持仓模拟真实账户
    temp_pm.holdings["100032"] = FundHolding(
        fund_code="100032",
        fund_name="富国中证红利指数增强A",
        share_class="A",
        shares=10000.0,
        cost_price=1.000,
        current_nav=1.000,
        first_buy_date="2026-01-01",
        dividend_method="cash",
        company="富国基金",
        is_core_strategy=True,
        batches=[HoldingBatch(batch_id="b1", buy_date="2026-01-01", shares=10000.0, cost_nav=1.000, fee=10.0, holding_days=300, safety_lock=False, notes="")]
    )
    temp_pm.available_cash = 2000.0
    temp_pm._recalculate_totals()

    target_weights = {
        "100032": 0.38,
        "005561": 0.30,
        "000216": 0.14,
        "002351": 0.12,
        "050025": 0.06
    }

    # 注入增量资金 10,000 元
    new_cash = 10000.0
    plan = temp_pm.generate_incremental_investment_plan(new_cash, target_weights)

    assert plan["is_zero_sell"] is True
    assert plan["total_redemption_fee"] == 0.0
    assert plan["new_cash"] == 10000.0
    assert plan["new_total_equity"] == temp_pm.total_equity + 10000.0

    buy_actions = plan["buy_actions"]
    assert len(buy_actions) > 0

    # 验证所有动作均为买入且无卖出
    for act in buy_actions:
        assert act["amount"] > 0
        assert act["redemption_fee"] == 0.0
        assert act["route_priority"] == "PRIORITY_2_CASH_ADVANCE"

    # 验证总分配金额等于注入金额（误差不超过0.1元舍入）
    total_allocated = sum(act["amount"] for act in buy_actions)
    assert abs(total_allocated - new_cash) < 0.1

    # 验证可直接用于生成在途订单
    routes = plan["routes"]
    assert len(routes) == len(buy_actions)
    oids = temp_pm.submit_rebalance_orders(routes)
    assert len(oids) == len(routes)


def test_generate_incremental_plan_zero_cash(temp_pm):
    """验证注入 0 元时安全返回空动作"""
    target_weights = {"100032": 0.5, "005561": 0.5}
    plan = temp_pm.generate_incremental_investment_plan(0.0, target_weights)
    assert plan["buy_actions"] == []
    assert plan["routes"] == []
    assert plan["is_zero_sell"] is True


# =====================================================================
# 6. portfolio_manager: calculate_intraday_pnl 盘中预估浮盈亏
# =====================================================================

def test_calculate_intraday_pnl(temp_pm):
    """验证盘中预估浮盈亏计算与 95% 法规仓位系数折算"""
    temp_pm.holdings["100032"] = FundHolding(
        fund_code="100032",
        fund_name="富国中证红利指数增强A",
        share_class="A",
        shares=10000.0,
        cost_price=1.000,
        current_nav=1.000,
        first_buy_date="2026-01-01",
        dividend_method="cash",
        company="富国基金",
        is_core_strategy=True,
        batches=[HoldingBatch(batch_id="b1", buy_date="2026-01-01", shares=10000.0, cost_nav=1.000, fee=10.0, holding_days=300, safety_lock=False, notes="")]
    )
    temp_pm.available_cash = 0.0
    temp_pm._recalculate_totals()

    pnl_res = temp_pm.calculate_intraday_pnl()
    assert "total_est_pnl" in pnl_res
    assert "total_est_pnl_pct" in pnl_res
    assert "total_market_value" in pnl_res
    assert pnl_res["total_market_value"] == 10000.0
    assert "timestamp" in pnl_res
    assert "100032" in pnl_res["fund_pnl"]

    f_pnl = pnl_res["fund_pnl"]["100032"]
    # 验证 95% 法规系数折算关系
    expected_est_pnl = round(10000.0 * (f_pnl["gszzl"] / 100.0) * 0.95, 2)
    assert abs(f_pnl["est_pnl"] - expected_est_pnl) < 1e-2


# =====================================================================
# 7. strategy_bridge: 双口径净值输出（指数理论 vs 场外联接 95% 仓位）
# =====================================================================

def test_get_backtest_nav_and_drawdown_dual_track():
    """验证历史回测数据返回双口径净值（包含 strategy_nav 与 strategy_nav_otc）"""
    df_bt = StrategyBridge.get_backtest_nav_and_drawdown()
    assert not df_bt.empty
    assert "strategy_nav" in df_bt.columns
    assert "strategy_nav_otc" in df_bt.columns
    assert "benchmark_50_50_nav" in df_bt.columns
    assert "h300_nav" in df_bt.columns

    # 验证场外联接净值受 95% 仓位与 5% 现金拖累，整体收益略低于 100% 仓位指数理论
    last_strategy_nav = df_bt["strategy_nav"].iloc[-1]
    last_otc_nav = df_bt["strategy_nav_otc"].iloc[-1]
    assert last_strategy_nav > 1.0
    assert last_otc_nav > 1.0
    # 在牛市/上涨周期中，95% 仓位因现金拖累低于 100% 指数理论
    assert last_strategy_nav >= last_otc_nav


# =====================================================================
# 8. 专项硬伤验证：周末不乱拼接、湖仓过滤A股虚假高溢价、账本表双口径
# =====================================================================

def test_stitch_today_live_tail_weekend_safety():
    """验证在非交易日/周末时，stitch_today_live_tail 严格静默，不生成周末虚拟行"""
    from unittest.mock import patch
    df_raw = StrategyBridge.load_matrix(force_reload=False)
    # 模拟周六上午 10:30 (2026-10-31 为周六)
    saturday_dt = datetime(2026, 10, 31, 10, 30, 0)
    with patch("strategy_bridge.datetime") as mock_dt:
        mock_dt.now.return_value = saturday_dt
        mock_dt.strptime = datetime.strptime
        df_res, stitched = StrategyBridge.stitch_today_live_tail(df_raw, force_live=False)
        assert stitched is False
        assert len(df_res) == len(df_raw)


def test_check_etf_premiums_lakehouse_filtering(temp_pm):
    """验证湖仓扫描时，过滤常规 A 股宽基/行业 ETF，仅精准预警真实 QDII 与商品黄金的高溢价标的"""
    alerts = temp_pm.check_etf_premiums()
    assert isinstance(alerts, list)
    # 真实高溢价 QDII/商品应在合理区间 (1 ~ 30 只)，绝不能触发 800+ 只的全市场假警报
    assert 1 <= len(alerts) <= 30
    # 验证常规 A 股宽基绝对不出现在高溢价预警中
    alert_codes = {a["code"] for a in alerts}
    assert "510300" not in alert_codes  # 沪深300ETF
    assert "588000" not in alert_codes  # 科创50ETF
    assert "510500" not in alert_codes  # 中证500ETF


def test_export_snapshot_df_includes_calibrated_pnl_pct(temp_pm):
    """验证持仓快照明细表包含 95% 仓位法规系数校准后的今日预估浮盈亏率(%)"""
    temp_pm.holdings["005561"] = FundHolding(
        fund_code="005561",
        fund_name="创金合信红利低波A",
        share_class="A",
        shares=10000.0,
        cost_price=1.200,
        current_nav=1.250,
        first_buy_date="2026-01-01",
        dividend_method="cash",
        company="创金合信",
        is_core_strategy=True,
        batches=[HoldingBatch(batch_id="b1", buy_date="2026-01-01", shares=10000.0, cost_nav=1.200, fee=5.0, holding_days=200, safety_lock=False, notes="")]
    )
    temp_pm._recalculate_totals()
    df_snapshot = temp_pm.export_snapshot_df()
    assert not df_snapshot.empty
    assert "盘中预估盈亏(元)" in df_snapshot.columns
    assert "今日预估盈亏率(%)" in df_snapshot.columns
    row = df_snapshot.iloc[0]
    expected_pct = round(row["今日实时估值涨跌(%)"] * 0.95, 2)
    assert abs(row["今日预估盈亏率(%)"] - expected_pct) <= 0.02

