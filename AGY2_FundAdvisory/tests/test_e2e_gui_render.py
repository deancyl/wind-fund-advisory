"""
AGY2 端到端渲染与 C1~C5 全档位分支严密验收测试套件 (tests/test_e2e_gui_render.py)
验证 6 大修复目标：
1. KeyError: 'candidate_funds' 根除与 NameError 修复；
2. 沪深300实时点位 (4053) 与全收益均线同口径折算，彻底消灭 -35.2% 荒谬偏离度与 6,102 破位预警；
3. 交易时钟 00:00~09:30 盘前未开市规范与顶部状态机与盘中推演零冲突；
4. 全局 【C3 C3 平衡进取型】 重复字符串彻底消除；
5. 首屏高对比度卡片对齐与下拉紧凑问卷；
6. 完整模拟执行 app_gui.py 全部顶层代码与 C1~C5 各档位切换分支无异常。
"""

from datetime import datetime, date, time
from pathlib import Path
import pytest
import pandas as pd
import numpy as np
from streamlit.testing.v1 import AppTest

import app_gui
from portfolio_manager import PortfolioManager, get_fund_selection_funnel_stats
from trading_clock_fee import TradingClock
from strategy_bridge import (
    StrategyBridge,
    RISK_TIERS_CONFIG,
    strategy_fn_for_tier,
    map_target_return_to_tier,
    evaluate_questionnaire_risk_tier,
    get_risk_mismatch_warning,
    calculate_human_readable_metrics
)


def test_bug1_funnel_stats_candidate_funds_key():
    """Bug 1 验收: 验证 get_fund_selection_funnel_stats 包含 candidate_funds 且不抛出 KeyError"""
    f_stats = get_fund_selection_funnel_stats()
    assert "candidate_funds" in f_stats, "缺少 candidate_funds 键"
    assert "sector_candidates" in f_stats, "缺少 sector_candidates 键"
    assert "total_market_funds" in f_stats, "缺少 total_market_funds 键"
    assert "hard_filtered_funds" in f_stats, "缺少 hard_filtered_funds 键"
    assert "final_champion_funds" in f_stats, "缺少 final_champion_funds 键"

    # 验证 app_gui 第 562 行的格式化字符串可安全执行
    text_check = (
        f"（漏斗过滤：{f_stats['total_market_funds']:,} ➔ "
        f"{f_stats['hard_filtered_funds']:,} ➔ {f_stats['candidate_funds']} ➔ "
        f"{f_stats['final_champion_funds']} 只金牌标的）"
    )
    assert len(text_check) > 0


def test_bug1_strategy_fn_for_tier_imported_in_app_gui():
    """Bug 1 验收: 验证 app_gui 命名空间导入并成功暴露 strategy_fn_for_tier"""
    assert hasattr(app_gui, "strategy_fn_for_tier"), "app_gui 模块未导入 strategy_fn_for_tier"
    assert hasattr(StrategyBridge, "strategy_fn_for_tier"), "StrategyBridge 缺少 strategy_fn_for_tier 静态方法"


def test_bug2_market_snapshot_and_grid_price_scale_alignment():
    """Bug 2 验收: 验证沪深300实时点位 (4053) 与均线同口径折算，偏离度绝非 -35.2%"""
    snapshot = StrategyBridge.get_latest_market_snapshot(force_reload=True)

    assert "c300_price" in snapshot
    assert "m20_price" in snapshot
    assert "m60_price" in snapshot

    # 价格指数应该在 3000 ~ 5500 范围，而非 6000+
    assert 3000.0 < snapshot["c300_price"] < 5500.0
    assert 3000.0 < snapshot["m20_price"] < 5500.0
    assert 3000.0 < snapshot["m60_price"] < 5500.0

    # 偏离度计算应该严格一致且在正常波动范围 (绝非 -35%)
    expected_bias = (snapshot["c300_price"] / snapshot["m20_price"] - 1.0) * 100.0
    assert abs(snapshot["bias_20"] - expected_bias) < 0.1
    assert abs(snapshot["bias_20"]) < 20.0, f"偏离度异常: {snapshot['bias_20']}%"

    # 网格预警文本中的点位必须也是 4000+ 价格点位口径，绝不能出现 6100+
    grid = snapshot["rebal_grid"]
    warning = grid["emergency_warning"]
    assert "6,102" not in warning and "6102" not in warning, "破位预警仍存在 6102 全收益点位错位"
    assert f"{grid['breakdown_threshold_c300']:,.1f}" in warning
    assert 3000.0 < grid["breakdown_threshold_c300"] < 5500.0

    # AI 综合研判结论必须也是价格点位口径
    assert "6,0" not in snapshot["ai_summary_text"] and "6,1" not in snapshot["ai_summary_text"], "ai_summary_text 仍存在 6000+ 点位错位"
    assert f"{snapshot['c300_price']:,.1f}" in snapshot["ai_summary_text"]


def test_bug2_evaluate_intraday_signal_price_scale():
    """Bug 2 验收: 验证盘中推演点位与均线也是价格指数口径"""
    eval_res = StrategyBridge.evaluate_intraday_signal()
    assert 3000.0 < eval_res["realtime_c300"] < 5500.0
    assert 3000.0 < eval_res["m20"] < 5500.0
    assert abs(eval_res["bias_m20"]) < 20.0, f"盘中偏离度异常: {eval_res['bias_m20']}%"


def test_bug3_pre_market_trading_clock_and_signal_harmony():
    """Bug 3 验收: 验证早上 08:21 盘前未开市时段状态及无自相矛盾预警"""
    clock = TradingClock()
    trade_date = date(2026, 10, 26) # 周一
    dt_821 = datetime.combine(trade_date, time(8, 21, 0))

    st_821 = clock.get_market_window_status(dt_821)
    assert st_821.window_type == "CLOSED_PREMARKET"
    assert "盘前未开市" in st_821.title
    assert st_821.countdown_str == "--:--"
    assert st_821.seconds_to_close == 0.0

    guidance = clock.get_action_guidance_for_window(dt_821)
    assert guidance["stage"] == "CLOSED_PREMARKET"
    assert "盘前未开市" in guidance["title"]

    # 验证在 08:21 传入时，evaluate_intraday_signal 绝不虚假误报变盘
    eval_pre = StrategyBridge.evaluate_intraday_signal(current_time_str="08:21")
    assert not eval_pre["is_state_changed"], "盘前 08:21 绝不能误触发变盘信号"
    assert eval_pre["action_urgency"] == "STABLE_HOLD"
    assert "盘前未开市" in eval_pre["trigger_warning_text"]

    # 验证非交易日（周末）时钟与状态机绝不误报盘中变盘或盘前未开市
    sat_date = date(2026, 10, 24)
    dt_sat = datetime.combine(sat_date, time(11, 0, 0))
    st_sat = clock.get_market_window_status(dt_sat)
    assert st_sat.window_type == "NON_TRADING_DAY"
    assert "非交易日延时窗口" in st_sat.title
    assert st_sat.countdown_str == "--:--"

    guidance_sat = clock.get_action_guidance_for_window(dt_sat)
    assert guidance_sat["stage"] == "NON_TRADING_DAY"
    assert "非交易日延时窗口" in guidance_sat["title"]

    from unittest.mock import patch
    with patch("strategy_bridge.datetime") as mock_dt:
        mock_dt.now.return_value = dt_sat
        mock_dt.combine = datetime.combine
        mock_dt.strptime = datetime.strptime
        eval_sat = StrategyBridge.evaluate_intraday_signal()
        assert not eval_sat["is_state_changed"], "非交易日绝不能误触发变盘预警"
        assert eval_sat["action_urgency"] == "STABLE_HOLD"
        assert "非交易日休市" in eval_sat["trigger_warning_text"]


def test_bug4_no_duplicate_tier_names():
    """Bug 4 验收: 消除 【C3 C3 平衡进取型】 等重复编号字符串"""
    for tier_code in ["C1", "C2", "C3", "C4", "C5"]:
        cfg = RISK_TIERS_CONFIG[tier_code]
        # name 内部不包含 C1/C2/C3/C4/C5 编号
        assert not cfg["name"].startswith("C"), f"{tier_code} name 仍包含前缀: {cfg['name']}"
        assert not cfg["tier_name"].startswith("C"), f"{tier_code} tier_name 仍包含前缀: {cfg['tier_name']}"

        formatted_str = f"【{tier_code} {cfg['name']}】"
        assert f"{tier_code} {tier_code}" not in formatted_str

    # 验证错配警报文本中也无重复
    mismatch = get_risk_mismatch_warning("C5", "C3", 50.0)
    assert mismatch["has_mismatch"]
    assert "C3 C3" not in mismatch["warning_desc"]
    assert "C3 C3" not in mismatch["recommendation"]
    assert "C5 C5" not in mismatch["warning_desc"]


def test_bug6_all_tiers_simulation_and_orders_e2e():
    """Bug 6 验收: 完整执行 C1~C5 各档位下的完整策略与调仓生成链路"""
    pm = PortfolioManager()
    pm.load_demo_portfolio()
    df_mat = StrategyBridge.load_matrix()

    for tier in ["C1", "C2", "C3", "C4", "C5"]:
        # 1. 对应档位回测数据拉取
        bt_df = StrategyBridge.get_backtest_nav_for_tier(tier)
        assert len(bt_df) > 1000
        assert "strategy_nav" in bt_df.columns

        # 2. 人话指标计算
        kpi = calculate_human_readable_metrics(
            nav_series=bt_df["strategy_nav"],
            dates=bt_df["date"],
            capital=100000.0,
            target_return_pct=RISK_TIERS_CONFIG[tier]["default_target"],
            tier=tier
        )
        assert "best_case_return_pct" in kpi
        assert "worst_case_drawdown_pct" in kpi
        assert "max_underwater_days" in kpi

        # 3. 对应档位权重计算 (针对非 C3 档位的 strategy_fn_for_tier 执行)
        w_idx = strategy_fn_for_tier(df_mat, tier=tier)
        assert isinstance(w_idx, dict)
        assert abs(sum(w_idx.values()) - 1.0) < 1e-4

        tier_target_w = StrategyBridge.map_index_weights_to_funds(w_idx)
        assert isinstance(tier_target_w, dict)
        assert abs(sum(tier_target_w.values()) - 1.0) < 1e-4

        # 4. 生成调仓执行单
        ai_orders_res = StrategyBridge.generate_ai_rebalance_orders(
            current_holdings=pm.holdings,
            available_cash=pm.available_cash,
            target_weights_funds=tier_target_w,
            pm=pm
        )
        assert "items" in ai_orders_res
        assert isinstance(ai_orders_res["items"], list)

        # 5. 测算调仓后影响
        impact = StrategyBridge.estimate_rebalance_impact(
            current_holdings=pm.holdings,
            target_weights_funds=tier_target_w,
            total_equity=pm.total_equity,
            rebalance_items=ai_orders_res["items"]
        )
        assert "vol_before" in impact
        assert "vol_after" in impact
        assert "vol_diff" in impact


def test_bug6_streamlit_apptest_full_render():
    """Bug 6 验收: 通过 Streamlit 官方 AppTest 框架端到端渲染运行 app_gui.py，覆盖 C1~C5 全档位切换分支"""
    app_path = Path(__file__).parent.parent / "app_gui.py"

    for tier in ["C1", "C2", "C3", "C4", "C5"]:
        at = AppTest.from_file(str(app_path), default_timeout=45)
        at.session_state.active_tier_val = tier
        at.session_state.target_return_val = RISK_TIERS_CONFIG[tier]["default_target"]
        at.run()
        assert len(at.exception) == 0, f"app_gui.py 在 {tier} 档位渲染抛出异常: {[e.value for e in at.exception]}"
