"""
自动化测试集：Trial 29 策略桥接器与实盘组合风控升级校验 (test_strategy_bridge.py)
验证：
1. strategy_bridge.py 实时计算非硬编码指标、ERP 分位数与 Trial 29 状态机推演；
2. A/C 份额自动路由与指数权重映射无偏差；
3. evolution.db 真实历史胜率与 6 大风格切片数据结构；
4. get_penalty_free_redeemable_shares 在混合批次下的精确份额裁剪与零惩罚赎回；
5. 场内 ETF 溢价监控读取湖仓真实数据；
6. 外部未录入基金严禁假股票欺骗重合度矩阵。
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from strategy_bridge import StrategyBridge, INDEX_TO_FUND_MAP
from portfolio_manager import PortfolioManager, HoldingBatch, FundHolding


@pytest.fixture
def temp_pm(tmp_path):
    db_file = tmp_path / "test_portfolio_state.db"
    json_file = tmp_path / "test_portfolio_ledger.json"
    pm = PortfolioManager(db_path=db_file, ledger_json_path=json_file)
    return pm


def test_strategy_bridge_snapshot_real_data():
    """验证市场截面数据为真实计算，非写死假数据"""
    snapshot = StrategyBridge.get_latest_market_snapshot(force_reload=True)

    assert isinstance(snapshot["latest_date"], str)
    assert snapshot["latest_date"] >= "2026-10-01"

    # 沪深300 均线与偏离度
    assert snapshot["c300"] > 0
    assert snapshot["m20"] > 0
    assert snapshot["m60"] > 0
    assert snapshot["m120"] > 0
    assert isinstance(snapshot["bias_20"], float)
    assert isinstance(snapshot["bias_60"], float)
    assert isinstance(snapshot["dist_to_m20_breakout"], float)
    assert snapshot["dist_to_m20_breakout"] >= 0.0

    # 动量指标
    assert isinstance(snapshot["mom60_300"], float)
    assert isinstance(snapshot["mom60_star"], float)
    assert isinstance(snapshot["mom60_div"], float)
    assert isinstance(snapshot["mom60_500"], float)
    assert isinstance(snapshot["diff_star_div"], float)
    assert isinstance(snapshot["diff_500_300"], float)

    # 股债性价比与利率
    assert snapshot["treasury_10y"] > 0.0
    assert snapshot["pe_ttm_300"] > 0.0
    assert 0.0 <= snapshot["erp_percentile"] <= 100.0

    # 状态机输出
    valid_states = [
        "🟢 常态稳健高股息慢牛",
        "🔥 进攻科技成长大牛市",
        "📈 结构分化牛市",
        "🛡️ 深度大熊市防御"
    ]
    assert snapshot["market_state"] in valid_states
    assert snapshot["state_streak"] >= 1
    assert "今日 AI 综合研判结论" in snapshot["ai_summary_text"]

    # 权重校验
    w_idx = snapshot["target_weights_index"]
    w_funds = snapshot["target_weights_funds"]
    assert len(w_idx) >= 4
    assert sum(w_idx.values()) == pytest.approx(1.0, abs=1e-3)
    assert sum(w_funds.values()) == pytest.approx(1.0, abs=1e-3)


def test_strategy_bridge_fund_mapping():
    """验证指数目标权重至公募基金的 A/C 份额自动路由映射"""
    # 进攻牛市权重
    growth_weights = {
        "STAR50_STITCH": 0.44,
        "H00300": 0.10,
        "H00852": 0.12,
        "H00905": 0.06,
        "H00922": 0.06,
        "AU9999": 0.14,
        "SPX_CNY": 0.06,
        "H11009": 0.02
    }
    fund_w = StrategyBridge.map_index_weights_to_funds(growth_weights)

    # 必须映射为对应的 C 类波段进攻基
    assert "011613" in fund_w  # 华夏科创50 C
    assert fund_w["011613"] == 0.44
    assert "007339" in fund_w  # 易方达沪深300 C
    assert fund_w["007339"] == 0.10
    assert "016634" in fund_w  # 富国中证1000 C
    assert fund_w["016634"] == 0.12
    assert "001053" in fund_w  # 华夏中证500 C
    assert fund_w["001053"] == 0.06

    # 底仓映射 A 类
    assert "100032" in fund_w  # 富国中证红利 A
    assert "000216" in fund_w  # 华安黄金 A
    assert "050025" in fund_w  # 博时标普500 A
    assert "002351" in fund_w  # 易方达纯债 A


def test_strategy_bridge_trial29_metrics():
    """验证从 evolution.db 提取的 Trial 29 真实指标与 6 大切片全胜记录"""
    metrics = StrategyBridge.load_trial29_metrics()

    assert metrics["trial_id"] == 29
    assert metrics["cagr_full"] == 11.93
    assert metrics["cagr_holdout"] == 21.31
    assert metrics["overall_mdd"] == -14.81
    assert metrics["survival_rate"] == 100.0

    df_slices = metrics["slices_df"]
    assert len(df_slices) == 6

    # 验证 6/6 切片全部录得正向超额收益
    for _, row in df_slices.iterrows():
        excess_str = row["超额Alpha"].replace("%", "").replace("+", "")
        excess_val = float(excess_str)
        assert excess_val > 0.0, f"切片 {row['切片名称与时期']} 超额未跑赢基准: {excess_val}"


def test_strategy_bridge_backtest_series():
    """验证策略全周期 2018-2026 净值曲线与水下回撤生成"""
    df_bt = StrategyBridge.get_backtest_nav_and_drawdown(force_reload=False)

    assert len(df_bt) >= 2100
    expected_cols = [
        'date', 'strategy_nav', 'benchmark_50_50_nav', 'h300_nav',
        'strategy_drawdown', 'h300_drawdown',
        'weight_ashare', 'weight_bond', 'weight_gold', 'weight_spx'
    ]
    for col in expected_cols:
        assert col in df_bt.columns

    # 净值起始归一化 1.0
    assert df_bt['strategy_nav'].iloc[0] == pytest.approx(1.0, abs=1e-2)
    assert df_bt['benchmark_50_50_nav'].iloc[0] == pytest.approx(1.0, abs=1e-2)
    assert df_bt['h300_nav'].iloc[0] == pytest.approx(1.0, abs=1e-2)

    # 最终净值大幅跑赢基准
    assert df_bt['strategy_nav'].iloc[-1] > 2.5
    assert df_bt['strategy_nav'].iloc[-1] > df_bt['benchmark_50_50_nav'].iloc[-1]

    # 回撤在容忍范围内
    assert df_bt['strategy_drawdown'].min() >= -15.50


def test_penalty_free_redeemable_shares_and_mixed_batches(tmp_path):
    """
    核心风控用例：验证当某只基金同时存在已满 7 天批次与未满 7 天批次时，
    调仓推演沙盒自动将卖出份额锁死在免惩罚安全批次内，严禁无脑传 force_penalty=True 触发 1.50% 扣款！
    """
    db_file = tmp_path / "test_pm_fifo.db"
    json_file = tmp_path / "test_pm_fifo.json"
    pm = PortfolioManager(db_path=db_file, ledger_json_path=json_file)

    # 构造混合批次持仓：
    # 批次 1: 买入 30 天前，6,000 份（已满 7 天，免惩罚费）
    # 批次 2: 买入 2 天前，4,000 份（未满 7 天，触发 1.50% 惩罚锁）
    today_dt = datetime.now().date()
    records = [
        {
            "fund_code": "005561",
            "buy_date": (today_dt - timedelta(days=30)).strftime("%Y-%m-%d"),
            "shares": 6000.0,
            "cost_nav": 1.00,
            "current_nav": 1.00,
            "holding_days": 30,
            "safety_lock": False
        }
    ]
    pm.takeover_mode_b(historical_records=records, available_cash=10000.0, baseline_date=str(today_dt))

    # 追加第二批次（仅持 2 天）
    b2 = HoldingBatch(
        batch_id="B_UNSAFE_002",
        buy_date=(today_dt - timedelta(days=2)).strftime("%Y-%m-%d"),
        shares=4000.0,
        cost_nav=1.00,
        fee=0.0,
        holding_days=2,
        safety_lock=True,
        notes="未满7天新买批次"
    )
    pm.holdings["005561"].batches.append(b2)
    pm.holdings["005561"].shares = 10000.0
    pm._recalculate_totals()

    # 1. 验证 get_penalty_free_redeemable_shares 精准返回 6,000 份
    free_shares = pm.get_penalty_free_redeemable_shares("005561")
    assert free_shares == 6000.0

    # 2. 调仓减仓：目标将 005561 从 50% 权重降低到 10% (理论需卖出 8,000 份)
    # 系统必须自动将卖出份额裁剪至 6,000 份，保护未满 7 天批次
    target_weights = {"005561": 0.10, "100032": 0.50}
    plan = pm.generate_rebalance_plan(target_weights=target_weights, min_buffer_pct=3.0)

    sell_act = [s for s in plan["sell_actions"] if s["fund_code"] == "005561"][0]
    assert sell_act["shares"] == 6000.0  # 自动锁死在 6000 份！
    assert sell_act["has_penalty"] is False  # 本次卖出不触碰惩罚批次
    assert "部分批次保护" in sell_act["staged_advice"]

    # 3. 执行调仓下单：必须成功执行，且 force_penalty=False 零异常抛出
    routes = plan["routes"]
    sell_routes = [r for r in routes if r.get("fund_code") == "005561"]
    assert len(sell_routes) > 0

    order_ids = pm.submit_rebalance_orders(sell_routes)
    assert len(order_ids) > 0

    # 4. 验证剩余持仓：批次 1 恰好耗尽，批次 2 完整保留 4,000 份，未受任何误伤
    assert "005561" in pm.holdings
    rem_h = pm.holdings["005561"]
    assert rem_h.shares == 4000.0
    assert len(rem_h.batches) == 1
    assert rem_h.batches[0].holding_days == 2


def test_etf_premiums_real_data(temp_pm):
    """验证 check_etf_premiums 能够自动加载本地湖仓真实 ETF 数据"""
    alerts = temp_pm.check_etf_premiums()
    assert isinstance(alerts, list)
    if len(alerts) > 0:
        alert = alerts[0]
        assert "code" in alert
        assert "premium_pct" in alert
        assert alert["premium_pct"] > 0.8
        assert alert["is_offline_snapshot"] is True


def test_external_fund_no_fake_stocks(temp_pm):
    """验证输入未收录的外部基金时，禁止伪造 '标的_xxx_重仓1' 欺骗重合度矩阵"""
    # 注入一只未知外部基金代码 999999
    temp_pm.add_or_update_holding(fund_code="999999", amount=20000.0, nav=1.0)

    overlap_res = temp_pm.calculate_stock_overlap_matrix()
    assert "999999" in overlap_res.get("pending_external_funds", [])

    # 检查 alerts 包含待穿透标记
    alerts = overlap_res.get("alerts", [])
    found_pending = any("待穿透外部主动基" in a.get("warning_msg", "") and "999999" in a.get("warning_msg", "") for a in alerts)
    assert found_pending


def test_multi_batch_no_share_inflation_on_update(temp_pm):
    """验证多批次持仓在重复保存或同步数据表时，绝不会发生份额虚增膨胀 (Anti-Inflation Guard)"""
    today_dt = datetime.now().date()
    records = [
        {
            "fund_code": "005561",
            "buy_date": (today_dt - timedelta(days=30)).strftime("%Y-%m-%d"),
            "shares": 6000.0,
            "cost_nav": 1.00,
            "current_nav": 1.00,
            "holding_days": 30,
            "safety_lock": False
        }
    ]
    temp_pm.takeover_mode_b(historical_records=records, available_cash=10000.0)

    # 追加第二批次 4000 份
    temp_pm.add_or_update_holding(
        fund_code="005561",
        shares=4000.0,
        nav=1.00,
        holding_days=3,
        append_batch=True
    )
    assert temp_pm.holdings["005561"].shares == 10000.0
    assert len(temp_pm.holdings["005561"].batches) == 2

    # 模拟数据表直接编辑同步 (保存 3 次)
    for _ in range(3):
        temp_pm.add_or_update_holding(
            fund_code="005561",
            shares=10000.0,
            nav=1.05,
            cost_price=1.00,
            holding_days=3,
            append_batch=False
        )

    # 验证总份额依然是精确的 10,000 份，杜绝膨胀成 14,000 或更高！
    assert temp_pm.holdings["005561"].shares == 10000.0
    assert len(temp_pm.holdings["005561"].batches) == 2
    assert temp_pm.holdings["005561"].batches[0].shares == 6000.0
    assert temp_pm.holdings["005561"].batches[1].shares == 4000.0


def test_ai_rebalance_orders_safe_clipping_and_chinese_routes(temp_pm):
    """验证 AI 调仓建议执行单能精准裁剪未满 7 天批次并输出规范中文化路由标签"""
    today_dt = datetime.now().date()
    # 构造仅持有 5,000 份未满 7 天批次的持仓
    records = [
        {
            "fund_code": "005561",
            "buy_date": (today_dt - timedelta(days=2)).strftime("%Y-%m-%d"),
            "shares": 5000.0,
            "cost_nav": 1.00,
            "current_nav": 1.00,
            "holding_days": 2,
            "safety_lock": True
        }
    ]
    temp_pm.takeover_mode_b(historical_records=records, available_cash=5000.0)

    # 目标权重将 005561 降至 0%
    target_weights = {"100032": 1.0}
    ai_orders = StrategyBridge.generate_ai_rebalance_orders(
        current_holdings=temp_pm.holdings,
        available_cash=temp_pm.available_cash,
        target_weights_funds=target_weights,
        pm=temp_pm
    )

    items = ai_orders["items"]
    item_5561 = [it for it in items if it["fund_code"] == "005561"][0]
    # 必须强力拦截卖出，diff_amount 裁剪为 0，防止触发惩罚费
    assert item_5561["action"] == "HOLD"
    assert item_5561["diff_amount"] == 0.0
    assert "7天安全" in item_5561["safety_warning"]

    # 验证路由标签为专业中文字符串
    for it in items:
        assert not it["route_priority"].startswith("PRIORITY_")
        assert ("优先级" in it["route_priority"] or "减仓" in it["route_priority"] or "维持" in it["route_priority"])

    # 验证零资产组合防御
    zero_orders = StrategyBridge.generate_ai_rebalance_orders({}, 0.0, target_weights)
    assert zero_orders["total_equity"] == 0.0
    assert len(zero_orders["items"]) == 0

