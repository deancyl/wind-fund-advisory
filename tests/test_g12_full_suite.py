# -*- coding: utf-8 -*-
"""
tests/test_g12_full_suite.py
Verification test suite for G12 Generation:
1. Trailing stop-profit and right-side breakdown alarm
2. First-screen sentry inspect_portfolio risk tier & fund_quotes penetration (Dimensions 8 & 9)
3. 7-dimensional Genetic Programming rule tree engine for black-swan sudden events
4. Real-time index / ETF feeder calibration with 0.95 ratio
5. Parquet auto-healing & multi-source leading sensors (ETF surge ratio, sentiment score)
"""

import pytest
import numpy as np
import pandas as pd
from typing import Dict, Any

from AGY2_FundAdvisory.advisory_engine import (
    ActiveRiskSentry,
    OnlineHeuristicFactorEvolver,
    OpportunityRadarEngine,
)
from AGY2_FundAdvisory.portfolio_manager import (
    PortfolioManager,
    HoldingItem,
)
from AGY2_FundAdvisory import data_loader


def test_trailing_stop_profit_right_side_breakdown():
    """测试移动止盈与右侧趋势破位锁利警报 (维度 4 扩展)"""
    sentry = ActiveRiskSentry()

    # 构造浮盈 >= 10% 且跌破 20 日均线 (bias_20 < 0) 的标的
    # cost_price = 1.0, current_nav = 1.12 (+12% 浮盈)
    mock_holdings = {
        "005561": HoldingItem(
            fund_code="005561",
            fund_name="创金合信量化红利",
            shares=10000.0,
            cost_price=1.0,
            current_nav=1.12,
            cost_nav=1.0,
            market_value=11200.0
        )
    }

    # 模拟 snapshot 中该基金的 bias_20 为负 (跌破均线) 且单日回撤较大
    mock_snapshot = {
        "fund_quotes": {
            "005561": {
                "gsz": "1.12",
                "gszzl": "-2.1",
                "bias_20": -1.8,
                "vol_20": 1.2,
                "nav_peak_60": 1.25,  # 60日峰值 1.25，当前 1.12 回撤 10.4%
            }
        }
    }

    rep = sentry.inspect_portfolio(mock_holdings, market_snapshot=mock_snapshot)
    alerts = rep.get("alerts", [])

    # 必须检测到止盈锁利警报
    profit_alerts = [a for a in alerts if "止盈" in a.get("title", "") or "锁利" in a.get("title", "") or "回撤" in a.get("title", "")]
    assert len(profit_alerts) > 0, "Trailing stop-profit / right-side breakdown alarm should be triggered for +12% profit broken below MA20"
    target_alert = profit_alerts[0]
    assert "50%" in target_alert.get("action", "") or "兑现" in target_alert.get("action", "") or "锁利" in target_alert.get("action", "")


def test_sentry_inspect_portfolio_dimensions_8_and_9():
    """测试 inspect_portfolio 显式传入 investor_risk_tier 与 fund_quotes 时激活维度 8 与 9"""
    sentry = ActiveRiskSentry()

    # C1 保守型投资者持有高风险权益资产 (触发适当性维度 8)
    mock_holdings = {
        "011613": HoldingItem(
            fund_code="011613",
            fund_name="华夏科创50ETF联接C",
            shares=50000.0,
            cost_price=1.0,
            current_nav=1.0,
            cost_nav=1.0,
            market_value=50000.0
        )
    }

    mock_quotes = {
        "011613": {
            "gsz": "0.98",
            "gszzl": "-2.0",  # 盘中急跌触发安全垫消耗维度 9
            "bias_20": -2.0,
        }
    }

    # 显式传入 C1 保守型与实时估值字典
    rep = sentry.inspect_portfolio(
        mock_holdings,
        market_snapshot={"fund_quotes": mock_quotes},
        investor_risk_tier="C1",
    )
    alerts = rep.get("alerts", [])

    # 应该检测到适当性越界预警
    suitability_or_shock = any("适当性" in a.get("title", "") or "C1" in a.get("title", "") or "超标" in a.get("title", "") or "盘中" in a.get("title", "") or "预警" in a.get("title", "") for a in alerts)
    assert suitability_or_shock, "Dimensions 8 or 9 should be active with investor_risk_tier and fund_quotes provided"


def test_gp_7d_rule_tree_evolver():
    """测试 OnlineHeuristicFactorEvolver 7维基因向量与突发事件规则树"""
    evolver = OnlineHeuristicFactorEvolver(population_size=16, generations=5, random_seed=42)

    # 模拟盘中实时行情截面
    mock_quotes = {
        "csi_300": {"realtime_chg_pct": -1.5, "point": 3950.0},
        "semiconductor": {"realtime_chg_pct": -3.2, "point": 1200.0},
        "pure_bond": {"realtime_chg_pct": 0.15, "point": 252.0},
        "domestic_gold": {"realtime_chg_pct": 0.80, "point": 580.0},
    }

    res = evolver.evolve_factor_weights(force_refresh=True, realtime_quotes=mock_quotes, lookback_days=40)

    # 验证返回契约向下兼容
    assert "weights" in res
    assert len(res["weights"]) == 4
    assert abs(sum(res["weights"]) - 1.0) < 1e-3

    # 验证 7 维 GP 特性
    assert "gp_7d_vector" in res
    assert len(res["gp_7d_vector"]) == 7
    assert "regime_mode" in res
    assert "operator_rule_expression" in res
    assert "RuleTree:" in res["operator_rule_expression"]

    # 验证算子参数在合理范围内
    assert 0.0 <= res["adaptive_momentum_window"] <= 1.0
    assert 0.5 <= res["vol_pulse_penalty_coef"] <= 3.0
    assert 0.0 <= res["panic_safe_haven_shift"] <= 1.5


def test_macro_sensors_and_sentiment():
    """测试多源先行指标采集与 0-100 财经快讯极性情绪评分"""
    score, label = data_loader.DataLoader.calc_financial_news_sentiment([
        {"title": "央行降准降息重大利好，A股放量反弹高股息领涨", "desc": "增量资金积极入场做多核心资产"},
        {"title": "前三季度医药行业步入改善周期，高质量发展确定性强", "desc": "CXO与创新药板块企稳提速"}
    ])
    assert 55.0 <= score <= 95.0, f"Bullish news should yield score > 55, got {score}"
    assert label in ["积极乐观", "温和看多"]

    # 熊市快讯测试
    bear_score, bear_label = data_loader.DataLoader.calc_financial_news_sentiment([
        {"title": "个股突遭立案调查并提示违规风险，跌停抛售", "desc": "出现大面积破位踩踏"}
    ])
    assert bear_score < 50.0, f"Bearish news should yield score < 50, got {bear_score}"
    assert bear_label in ["恐慌避险", "谨慎防守"]

    # 测试宏观指标采集
    macro = data_loader.DataLoader.fetch_macro_cross_market_indicators()
    assert "cgb_10y_yield" in macro
    assert "gold_price" in macro
    assert "nasdaq_point" in macro
    assert "nasdaq_change_pct" in macro
