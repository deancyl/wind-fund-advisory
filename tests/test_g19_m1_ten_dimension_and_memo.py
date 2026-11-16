# -*- coding: utf-8 -*-
"""
tests/test_g19_m1_ten_dimension_and_memo.py

Wind G19 Milestone 1 Comprehensive Test Suite (Features 1 - 6):
- Feature 1: 维度6产业估值真数据驱动 (14-sector Top3 valuation percentile mean & median)
- Feature 2: 维度7资金情绪多维融合 (turnover, up ratio, 14-sector mean crowding score)
- Feature 3: 维度10期权衍生品与避险 (option_iv_pct, ic_annualized_basis_rate, dynamic correlation)
- Feature 4: 黑天鹅/灰犀牛一票否决熔断门禁 (ivix >= 32.0 or dyn_corr >= 0.80 or usdcnh_chg > 0.60%)
- Feature 5: 拔除 6.6676/5.0000 及跨市场校验哨 (usdcnh [6.85, 7.60], US 10Y ~4.42%)
- Feature 6: 胶囊4持仓病灶与胶囊5今日行动准则知行合一联动

Methodology: 4-Tier Systematic Testing (TEST_INFRA.md)
- Tier 1: Category-Partition (Equivalence Classes)
- Tier 2: Boundary Value Analysis
- Tier 3: Pairwise Combinatorial Testing
- Tier 4: Real-World Workload Testing
"""

import os
import sys
import re
import pytest
import numpy as np
from unittest.mock import patch

# Ensure workspace and AGY2_FundAdvisory in sys.path
WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)
AGY2_DIR = os.path.join(WORKSPACE_DIR, "AGY2_FundAdvisory")
if AGY2_DIR not in sys.path:
    sys.path.insert(0, AGY2_DIR)

from AGY2_FundAdvisory.data_loader import DataLoader
from AGY2_FundAdvisory.advisory_engine import (
    compute_ten_dimension_votes,
    generate_chief_advisor_memo,
    OpportunityRadarEngine,
)
from AGY2_FundAdvisory.strategy_bridge import StrategyBridge
from AGY2_FundAdvisory.portfolio_manager import PortfolioManager
from AGY2_FundAdvisory.app_gui import render_chief_advisor_memo_card
from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager


# ─── Helper Functions & Fixtures ──────────────────────────────────────

def make_14_sectors(top3_avg=28.0, median_val=52.0, avg_crowd=75.0):
    """
    Constructs 14 sectors with precise top-3 valuation average and 14-sector median.
    Top-3 sectors are indexed 0, 1, 2.
    """
    top3_vals = [float(top3_avg), float(top3_avg), float(top3_avg)]
    other_vals = []
    if top3_avg <= median_val:
        # 3 are <= median_val. We need 4 more <= median_val and 7 >= median_val.
        for _ in range(3):
            other_vals.append(float(top3_avg))
        other_vals.append(float(median_val))  # 7th
        other_vals.append(float(median_val))  # 8th
        for i in range(6):
            other_vals.append(float(median_val + (i + 1) * 2.0))
    else:
        # top3_avg > median_val. 3 are >= median_val.
        for i in range(6):
            other_vals.append(max(0.0, float(median_val - (6 - i) * 2.0)))
        other_vals.append(float(median_val))  # 7th
        other_vals.append(float(median_val))  # 8th
        for _ in range(2):
            other_vals.append(float(top3_avg))

    sectors = []
    for i, v in enumerate(top3_vals):
        sectors.append({
            "name": f"核心赛道_{i+1}",
            "sector_id": f"top_{i+1}",
            "val_percentile": float(v),
            "crowding_score": float(avg_crowd),
            "fund": {"code": f"51{i:04d}", "name": f"核心ETF_{i+1}"}
        })
    for i, v in enumerate(other_vals):
        sectors.append({
            "name": f"其他赛道_{i+1}",
            "sector_id": f"other_{i+1}",
            "val_percentile": float(v),
            "crowding_score": float(avg_crowd),
            "fund": {"code": f"15{i:04d}", "name": f"赛道基金_{i+1}"}
        })
    return sectors


def get_dimension_by_id(result: dict, dim_id: int):
    """Extract a single dimension dict by dimension_id (1-10) or name match."""
    dims = result.get("dimensions", [])
    for d in dims:
        if d.get("dimension_id") == dim_id:
            return d
    name_map = {
        1: "宏观经济", 2: "货币政策", 3: "股债ERP", 4: "国际联动",
        5: "外汇锁汇", 6: "产业估值", 7: "资金情绪", 8: "技术信噪比",
        9: "历史同温层", 10: "期权"
    }
    target = name_map.get(dim_id, "")
    for d in dims:
        if target and target in d.get("name", ""):
            return d
    return None


class MockHolding:
    """Mock holding object compatible with generate_chief_advisor_memo."""
    def __init__(self, name: str, code: str, mv: float, cost: float, days: int, share_class: str = "A"):
        self.fund_name = name
        self.fund_code = code
        self.market_value = float(mv)
        self.cost_basis = float(cost)
        self.holding_days = int(days)
        self.share_class = str(share_class).upper()
        self.floating_pnl = float(mv - cost)
        self.floating_pnl_pct = float(((mv / cost) - 1.0) * 100.0) if cost > 0 else 0.0


# ─── Feature 1: 维度6产业估值真数据驱动 ─────────────────────────────────

class TestFeature1SectorValuationGenuineData:
    """Feature 1: 废除列表长度恒真，读取 14 赛道真实估值分位，计算 Top3 均值与中位数定多空"""

    def test_t1_1_1_standard_low_valuation_bull(self):
        """Tier 1: 标准低估买点 - Top3均值=28.0% (<=35%), 市场中位数=52.0% -> BULL (+5%)"""
        sectors = make_14_sectors(top3_avg=28.0, median_val=52.0)
        with patch("AGY2_FundAdvisory.advisory_engine.OpportunityRadarEngine.get_cached_sectors_fast", return_value=sectors):
            res = compute_ten_dimension_votes(radar_top3=sectors[:3], all_sectors=sectors)
            d6 = get_dimension_by_id(res, 6)
            assert d6 is not None, "Dimension 6 must exist"
            assert d6["vote"] == "BULL", f"Expected BULL, got {d6['vote']}"
            assert d6["delta_pct"] in (5.0, 0.05), f"Expected +5% delta, got {d6['delta_pct']}"
            assert "28" in d6["reason"] or "28.0" in d6["reason"], "Reason must report real top3 valuation"
            assert "52" in d6["reason"] or "52.0" in d6["reason"], "Reason must report real market median"

    def test_t1_1_2_market_overheated_bear(self):
        """Tier 1: 全市场过热空方 - Top3均值=42.0%, 市场中位数=76.0% (>70%) -> BEAR (-5%)"""
        sectors = make_14_sectors(top3_avg=42.0, median_val=76.0)
        with patch("AGY2_FundAdvisory.advisory_engine.OpportunityRadarEngine.get_cached_sectors_fast", return_value=sectors):
            res = compute_ten_dimension_votes(radar_top3=sectors[:3], all_sectors=sectors)
            d6 = get_dimension_by_id(res, 6)
            assert d6 is not None
            assert d6["vote"] == "BEAR", f"Expected BEAR, got {d6['vote']}"
            assert d6["delta_pct"] in (-5.0, -0.05), f"Expected -5% delta, got {d6['delta_pct']}"
            assert "76" in d6["reason"] or "76.0" in d6["reason"], "Reason must report real market median"

    def test_t1_1_3_normal_range_neutral(self):
        """Tier 1: 常态震荡中性 - Top3均值=40.0%, 市场中位数=58.0% -> NEUTRAL (0.0%)"""
        sectors = make_14_sectors(top3_avg=40.0, median_val=58.0)
        with patch("AGY2_FundAdvisory.advisory_engine.OpportunityRadarEngine.get_cached_sectors_fast", return_value=sectors):
            res = compute_ten_dimension_votes(radar_top3=sectors[:3], all_sectors=sectors)
            d6 = get_dimension_by_id(res, 6)
            assert d6 is not None
            assert d6["vote"] == "NEUTRAL", f"Expected NEUTRAL, got {d6['vote']}"
            assert d6["delta_pct"] == 0.0, f"Expected 0 delta, got {d6['delta_pct']}"
            assert "40" in d6["reason"] or "40.0" in d6["reason"]

    def test_t1_1_4_historical_extreme_low_bull(self):
        """Tier 1: 历史极值低位 - Top3均值=12.0%, 市场中位数=25.0% -> BULL (+5%)"""
        sectors = make_14_sectors(top3_avg=12.0, median_val=25.0)
        with patch("AGY2_FundAdvisory.advisory_engine.OpportunityRadarEngine.get_cached_sectors_fast", return_value=sectors):
            res = compute_ten_dimension_votes(radar_top3=sectors[:3], all_sectors=sectors)
            d6 = get_dimension_by_id(res, 6)
            assert d6["vote"] == "BULL"
            assert d6["delta_pct"] in (5.0, 0.05)
            assert "12" in d6["reason"] or "12.0" in d6["reason"]

    def test_t1_1_5_missing_val_percentile_fallback(self):
        """Tier 1: 容错与防御性 - val_percentile 字段缺失或 None 时不抛崩溃异常"""
        sectors = [{"name": f"Sec_{i}", "sector_id": f"s_{i}"} for i in range(14)]
        res = compute_ten_dimension_votes(radar_top3=sectors[:3], all_sectors=sectors)
        d6 = get_dimension_by_id(res, 6)
        assert d6 is not None
        assert d6["vote"] in ("BULL", "BEAR", "NEUTRAL")

    def test_t1_2_1_boundary_top3_34_99_bull(self):
        """Tier 2: 35% 临界下界探测 (34.99%) -> BULL"""
        sectors = make_14_sectors(top3_avg=34.99, median_val=60.0)
        with patch("AGY2_FundAdvisory.advisory_engine.OpportunityRadarEngine.get_cached_sectors_fast", return_value=sectors):
            res = compute_ten_dimension_votes(radar_top3=sectors[:3], all_sectors=sectors)
            d6 = get_dimension_by_id(res, 6)
            assert d6["vote"] == "BULL"
            assert d6["delta_pct"] in (5.0, 0.05)

    def test_t1_2_2_boundary_top3_35_00_bull(self):
        """Tier 2: 35% 临界点精确吻合 (35.00%) -> BULL (<=35%)"""
        sectors = make_14_sectors(top3_avg=35.00, median_val=60.0)
        with patch("AGY2_FundAdvisory.advisory_engine.OpportunityRadarEngine.get_cached_sectors_fast", return_value=sectors):
            res = compute_ten_dimension_votes(radar_top3=sectors[:3], all_sectors=sectors)
            d6 = get_dimension_by_id(res, 6)
            assert d6["vote"] == "BULL"
            assert d6["delta_pct"] in (5.0, 0.05)

    def test_t1_2_3_boundary_top3_35_01_neutral(self):
        """Tier 2: 35% 临界上界破位 (35.01%) -> NEUTRAL (0.0%)"""
        sectors = make_14_sectors(top3_avg=35.01, median_val=60.0)
        with patch("AGY2_FundAdvisory.advisory_engine.OpportunityRadarEngine.get_cached_sectors_fast", return_value=sectors):
            res = compute_ten_dimension_votes(radar_top3=sectors[:3], all_sectors=sectors)
            d6 = get_dimension_by_id(res, 6)
            assert d6["vote"] == "NEUTRAL"
            assert d6["delta_pct"] == 0.0

    def test_t1_2_4_boundary_market_70_00_neutral(self):
        """Tier 2: 70% 临界点精确吻合 (70.00%) -> NEUTRAL (70%不触发空头)"""
        sectors = make_14_sectors(top3_avg=50.00, median_val=70.00)
        with patch("AGY2_FundAdvisory.advisory_engine.OpportunityRadarEngine.get_cached_sectors_fast", return_value=sectors):
            res = compute_ten_dimension_votes(radar_top3=sectors[:3], all_sectors=sectors)
            d6 = get_dimension_by_id(res, 6)
            assert d6["vote"] == "NEUTRAL"
            assert d6["delta_pct"] == 0.0

    def test_t1_2_5_boundary_market_70_01_bear(self):
        """Tier 2: 70% 临界上界触发空头 (70.01%) -> BEAR (-5%)"""
        sectors = make_14_sectors(top3_avg=50.00, median_val=70.01)
        with patch("AGY2_FundAdvisory.advisory_engine.OpportunityRadarEngine.get_cached_sectors_fast", return_value=sectors):
            res = compute_ten_dimension_votes(radar_top3=sectors[:3], all_sectors=sectors)
            d6 = get_dimension_by_id(res, 6)
            assert d6["vote"] == "BEAR"
            assert d6["delta_pct"] in (-5.0, -0.05)

    def test_t1_3_1_pairwise_valuation_bull_vs_sentiment_bear(self):
        """Tier 3: 正交组合 - 产业估值低估 (Top3=30%) × 资金情绪衰竭 (拥挤度=48) 各自独立"""
        sectors = make_14_sectors(top3_avg=30.0, median_val=50.0, avg_crowd=48.0)
        snap = {"market_turnover_sentiment": {"turnover_str": "8,000 亿", "up_pct": 35.0}}
        with patch("AGY2_FundAdvisory.advisory_engine.OpportunityRadarEngine.get_cached_sectors_fast", return_value=sectors):
            res = compute_ten_dimension_votes(snapshot=snap, radar_top3=sectors[:3], all_sectors=sectors)
            d6 = get_dimension_by_id(res, 6)
            d7 = get_dimension_by_id(res, 7)
            assert d6["vote"] == "BULL"
            assert d7["vote"] == "BEAR"

    def test_t1_3_2_pairwise_valuation_neutral_vs_circuit_breaker(self):
        """Tier 3: 正交组合 - 产业估值中性 (Top3=45%,中位=55%) × 黑天鹅熔断生效"""
        sectors = make_14_sectors(top3_avg=45.0, median_val=55.0)
        snap = {"ivix_index": 35.0}  # Triggers circuit breaker
        with patch("AGY2_FundAdvisory.advisory_engine.OpportunityRadarEngine.get_cached_sectors_fast", return_value=sectors):
            res = compute_ten_dimension_votes(snapshot=snap, radar_top3=sectors[:3], all_sectors=sectors)
            d6 = get_dimension_by_id(res, 6)
            assert d6["vote"] == "NEUTRAL"
            assert d6["delta_pct"] == 0.0


# ─── Feature 2: 维度7资金情绪多维融合 ──────────────────────────────────

class TestFeature2SentimentMultiDimensionalFusion:
    """Feature 2: 废除单基/默认85分，融合两市成交额、上涨家数占比与 14 赛道平均拥挤度"""

    def test_t2_1_1_standard_bull_sentiment(self):
        """Tier 1: 标准多头主升浪 - 成交1.2万亿, 上涨占比65%, 平均拥挤度=78.0 -> BULL (+2%)"""
        sectors = make_14_sectors(avg_crowd=78.0)
        snap = {
            "market_turnover_sentiment": {"turnover_str": "12,000 亿", "up_pct": 65.0},
            "bias_20": 1.5
        }
        with patch("AGY2_FundAdvisory.advisory_engine.OpportunityRadarEngine.get_cached_sectors_fast", return_value=sectors):
            res = compute_ten_dimension_votes(snapshot=snap, all_sectors=sectors)
            d7 = get_dimension_by_id(res, 7)
            assert d7["vote"] == "BULL"
            assert d7["delta_pct"] in (2.0, 0.02)
            assert "78" in d7["reason"] or "78.0" in d7["reason"]
            assert "65" in d7["reason"]

    def test_t2_1_2_liquidity_drain_bear(self):
        """Tier 1: 流动性枯竭空头 - 成交6500亿, 上涨占比28%, 平均拥挤度=46.0 (<55.0) -> BEAR (-5%)"""
        sectors = make_14_sectors(avg_crowd=46.0)
        snap = {
            "market_turnover_sentiment": {"turnover_str": "6,500 亿", "up_pct": 28.0}
        }
        with patch("AGY2_FundAdvisory.advisory_engine.OpportunityRadarEngine.get_cached_sectors_fast", return_value=sectors):
            res = compute_ten_dimension_votes(snapshot=snap, all_sectors=sectors)
            d7 = get_dimension_by_id(res, 7)
            assert d7["vote"] == "BEAR"
            assert d7["delta_pct"] in (-5.0, -0.05)
            assert "46" in d7["reason"] or "46.0" in d7["reason"]

    def test_t2_1_3_momentum_exhaustion_warning_bear(self):
        """Tier 1: 预警驱动防御 - 动量衰竭预警 -> BEAR (-5%)"""
        sectors = make_14_sectors(avg_crowd=62.0)
        snap = {
            "momentum_exhaustion_warning": True,
            "market_turnover_sentiment": {"turnover_str": "9,000 亿", "up_pct": 45.0}
        }
        with patch("AGY2_FundAdvisory.advisory_engine.OpportunityRadarEngine.get_cached_sectors_fast", return_value=sectors):
            res = compute_ten_dimension_votes(snapshot=snap, all_sectors=sectors)
            d7 = get_dimension_by_id(res, 7)
            assert d7["vote"] == "BEAR"
            assert d7["delta_pct"] in (-5.0, -0.05)

    def test_t2_1_4_sentiment_overheated_neutral(self):
        """Tier 1: 情绪过热防追高 - 拥挤度=88.0, 上涨占比92% (>85%) -> NEUTRAL (0.0%)"""
        sectors = make_14_sectors(avg_crowd=88.0)
        snap = {
            "market_turnover_sentiment": {"turnover_str": "18,000 亿", "up_pct": 92.0}
        }
        with patch("AGY2_FundAdvisory.advisory_engine.OpportunityRadarEngine.get_cached_sectors_fast", return_value=sectors):
            res = compute_ten_dimension_votes(snapshot=snap, all_sectors=sectors)
            d7 = get_dimension_by_id(res, 7)
            assert d7["vote"] == "NEUTRAL"
            assert d7["delta_pct"] == 0.0

    def test_t2_1_5_steady_balance_neutral(self):
        """Tier 1: 稳态平衡 - 平均拥挤度=64.0, 上涨占比50% -> NEUTRAL (0.0%)"""
        sectors = make_14_sectors(avg_crowd=64.0)
        snap = {
            "market_turnover_sentiment": {"turnover_str": "10,000 亿", "up_pct": 50.0}
        }
        with patch("AGY2_FundAdvisory.advisory_engine.OpportunityRadarEngine.get_cached_sectors_fast", return_value=sectors):
            res = compute_ten_dimension_votes(snapshot=snap, all_sectors=sectors)
            d7 = get_dimension_by_id(res, 7)
            assert d7["vote"] == "NEUTRAL"
            assert d7["delta_pct"] == 0.0

    def test_t2_2_1_boundary_crowding_54_99_bear(self):
        """Tier 2: 55.0 临界下界探测 (54.99) -> BEAR (-5%)"""
        sectors = make_14_sectors(avg_crowd=54.99)
        snap = {"market_turnover_sentiment": {"turnover_str": "9,000 亿", "up_pct": 50.0}}
        with patch("AGY2_FundAdvisory.advisory_engine.OpportunityRadarEngine.get_cached_sectors_fast", return_value=sectors):
            res = compute_ten_dimension_votes(snapshot=snap, all_sectors=sectors)
            d7 = get_dimension_by_id(res, 7)
            assert d7["vote"] == "BEAR"
            assert d7["delta_pct"] in (-5.0, -0.05)

    def test_t2_2_2_boundary_crowding_55_00_non_bear(self):
        """Tier 2: 55.0 临界点精确吻合 (55.00) -> 非空头 NEUTRAL"""
        sectors = make_14_sectors(avg_crowd=55.00)
        snap = {"market_turnover_sentiment": {"turnover_str": "9,000 亿", "up_pct": 50.0}}
        with patch("AGY2_FundAdvisory.advisory_engine.OpportunityRadarEngine.get_cached_sectors_fast", return_value=sectors):
            res = compute_ten_dimension_votes(snapshot=snap, all_sectors=sectors)
            d7 = get_dimension_by_id(res, 7)
            assert d7["vote"] != "BEAR"

    def test_t2_2_3_boundary_crowding_71_99_non_bull(self):
        """Tier 2: 72.0 临界下界探测 (71.99) -> 非多头 NEUTRAL"""
        sectors = make_14_sectors(avg_crowd=71.99)
        snap = {"market_turnover_sentiment": {"turnover_str": "12,000 亿", "up_pct": 60.0}}
        with patch("AGY2_FundAdvisory.advisory_engine.OpportunityRadarEngine.get_cached_sectors_fast", return_value=sectors):
            res = compute_ten_dimension_votes(snapshot=snap, all_sectors=sectors)
            d7 = get_dimension_by_id(res, 7)
            assert d7["vote"] != "BULL"

    def test_t2_2_4_boundary_crowding_72_00_up_85_00_bull(self):
        """Tier 2: 72.0 及 85% 临界闭区间 (72.00, 85.00%或84.99%) -> BULL (+2%)"""
        sectors = make_14_sectors(avg_crowd=72.00)
        snap = {"market_turnover_sentiment": {"turnover_str": "14,000 亿", "up_pct": 84.99}, "bias_20": 2.0}
        with patch("AGY2_FundAdvisory.advisory_engine.OpportunityRadarEngine.get_cached_sectors_fast", return_value=sectors):
            res = compute_ten_dimension_votes(snapshot=snap, all_sectors=sectors)
            d7 = get_dimension_by_id(res, 7)
            assert d7["vote"] == "BULL"
            assert d7["delta_pct"] in (2.0, 0.02)

    def test_t2_2_5_boundary_crowding_72_00_up_85_01_neutral(self):
        """Tier 2: 85% 情绪过热边界探测 (85.01%) -> NEUTRAL (0.0%)"""
        sectors = make_14_sectors(avg_crowd=72.00)
        snap = {"market_turnover_sentiment": {"turnover_str": "15,000 亿", "up_pct": 85.01}}
        with patch("AGY2_FundAdvisory.advisory_engine.OpportunityRadarEngine.get_cached_sectors_fast", return_value=sectors):
            res = compute_ten_dimension_votes(snapshot=snap, all_sectors=sectors)
            d7 = get_dimension_by_id(res, 7)
            assert d7["vote"] == "NEUTRAL"

    def test_t2_3_1_pairwise_sentiment_bull_vs_option_bear(self):
        """Tier 3: 正交组合 - 资金情绪多头 (76分) × 期权隐波高企 (IV=30%) 分歧透明"""
        sectors = make_14_sectors(avg_crowd=76.0)
        snap = {
            "market_turnover_sentiment": {"turnover_str": "13,000 亿", "up_pct": 65.0},
            "option_iv_pct": 30.0,
            "bias_20": 1.0
        }
        with patch("AGY2_FundAdvisory.advisory_engine.OpportunityRadarEngine.get_cached_sectors_fast", return_value=sectors):
            res = compute_ten_dimension_votes(snapshot=snap, all_sectors=sectors)
            d7 = get_dimension_by_id(res, 7)
            d10 = get_dimension_by_id(res, 10)
            assert d7["vote"] == "BULL"
            assert d10["vote"] == "BEAR"

    def test_t2_3_2_pairwise_sentiment_bear_vs_fx_normal(self):
        """Tier 3: 正交组合 - 资金情绪空头 (50分) × 离岸汇率波动正常 (7.2385)"""
        sectors = make_14_sectors(avg_crowd=50.0)
        snap = {"spot_usdcnh": 7.2385, "usdcnh_change_pct": 0.05}
        with patch("AGY2_FundAdvisory.advisory_engine.OpportunityRadarEngine.get_cached_sectors_fast", return_value=sectors):
            res = compute_ten_dimension_votes(snapshot=snap, all_sectors=sectors)
            d7 = get_dimension_by_id(res, 7)
            assert d7["vote"] == "BEAR"


# ─── Feature 3: 维度10期权衍生品与避险 ────────────────────────────────

class TestFeature3OptionsDerivativesHedging:
    """Feature 3: 接入真实 option_iv_pct、ic_annualized_basis_rate 与动态相关性预警"""

    def test_t3_1_1_high_iv_bear_hedging(self):
        """Tier 1: 隐波高企避险 - option_iv_pct=31.5% (>28%) -> BEAR (-8%)"""
        snap = {"option_iv_pct": 31.5, "dynamic_correlation": 0.45}
        res = compute_ten_dimension_votes(snapshot=snap)
        d10 = get_dimension_by_id(res, 10)
        assert d10["vote"] == "BEAR"
        assert d10["delta_pct"] in (-8.0, -0.08)
        assert "31.5" in d10["reason"]

    def test_t3_1_2_correlation_mutation_alert_bear(self):
        """Tier 1: 相关性突变一票防守 - dyn_corr=0.78 (>=0.75) -> BEAR (-8%)"""
        snap = {"option_iv_pct": 20.5, "dynamic_correlation": 0.78}
        res = compute_ten_dimension_votes(snapshot=snap)
        d10 = get_dimension_by_id(res, 10)
        assert d10["vote"] == "BEAR"
        assert d10["delta_pct"] in (-8.0, -0.08)

    def test_t3_1_3_safe_basis_cushion_bull(self):
        """Tier 1: 衍生品安全垫充足多头 - option_iv=19.8% (<22%), ic_basis=12.0 (>=8.0) -> BULL (+2%)"""
        snap = {
            "option_iv_pct": 19.8,
            "ic_annualized_basis_rate": 12.0,
            "dynamic_correlation": 0.32
        }
        res = compute_ten_dimension_votes(snapshot=snap)
        d10 = get_dimension_by_id(res, 10)
        assert d10["vote"] == "BULL"
        assert d10["delta_pct"] > 0
        assert "19.8" in d10["reason"]

    def test_t3_1_4_deep_premium_no_cushion_neutral(self):
        """Tier 1: 缺乏基差保护 - option_iv=20.0%, ic_basis=-5.0 (升水无贴水垫) -> NEUTRAL (0.0%)"""
        snap = {
            "option_iv_pct": 20.0,
            "ic_annualized_basis_rate": -5.0,
            "dynamic_correlation": 0.35
        }
        res = compute_ten_dimension_votes(snapshot=snap)
        d10 = get_dimension_by_id(res, 10)
        assert d10["vote"] == "NEUTRAL"
        assert d10["delta_pct"] == 0.0

    def test_t3_1_5_normal_steady_neutral(self):
        """Tier 1: 稳态中性 - option_iv=25.0% (22%~28%), ic_basis=10.0 -> NEUTRAL (0.0%)"""
        snap = {
            "option_iv_pct": 25.0,
            "ic_annualized_basis_rate": 10.0,
            "dynamic_correlation": 0.40
        }
        res = compute_ten_dimension_votes(snapshot=snap)
        d10 = get_dimension_by_id(res, 10)
        assert d10["vote"] == "NEUTRAL"
        assert d10["delta_pct"] == 0.0

    def test_t3_2_1_boundary_iv_28_00_non_bear(self):
        """Tier 2: 28% 临界闭区间探测 (28.00%) -> 非空头"""
        snap = {"option_iv_pct": 28.00, "dynamic_correlation": 0.40, "ic_annualized_basis_rate": 10.0}
        res = compute_ten_dimension_votes(snapshot=snap)
        d10 = get_dimension_by_id(res, 10)
        assert d10["vote"] != "BEAR"

    def test_t3_2_2_boundary_iv_28_01_bear(self):
        """Tier 2: 28% 突破触发避险 (28.01%) -> BEAR (-8%)"""
        snap = {"option_iv_pct": 28.01, "dynamic_correlation": 0.40}
        res = compute_ten_dimension_votes(snapshot=snap)
        d10 = get_dimension_by_id(res, 10)
        assert d10["vote"] == "BEAR"
        assert d10["delta_pct"] in (-8.0, -0.08)

    def test_t3_2_3_boundary_iv_21_99_bull(self):
        """Tier 2: 22% 临界下界探测 (21.99%) -> BULL"""
        snap = {
            "option_iv_pct": 21.99,
            "ic_annualized_basis_rate": 10.0,
            "dynamic_correlation": 0.35
        }
        res = compute_ten_dimension_votes(snapshot=snap)
        d10 = get_dimension_by_id(res, 10)
        assert d10["vote"] == "BULL"

    def test_t3_2_4_boundary_iv_22_00_neutral(self):
        """Tier 2: 22% 临界精确吻合 (22.00%) -> 非多头 (进入中性带)"""
        snap = {
            "option_iv_pct": 22.00,
            "ic_annualized_basis_rate": 10.0,
            "dynamic_correlation": 0.35
        }
        res = compute_ten_dimension_votes(snapshot=snap)
        d10 = get_dimension_by_id(res, 10)
        assert d10["vote"] != "BULL"

    def test_t3_2_5_boundary_dyn_corr_7499_vs_7500(self):
        """Tier 2: 动态相关性 0.75 临界线 (0.7499 无突变; 0.7500 触发突变避险 BEAR)"""
        snap1 = {"option_iv_pct": 24.0, "dynamic_correlation": 0.7499, "ic_annualized_basis_rate": 10.0}
        res1 = compute_ten_dimension_votes(snapshot=snap1)
        assert get_dimension_by_id(res1, 10)["vote"] != "BEAR"

        snap2 = {"option_iv_pct": 24.0, "dynamic_correlation": 0.7500}
        res2 = compute_ten_dimension_votes(snapshot=snap2)
        assert get_dimension_by_id(res2, 10)["vote"] == "BEAR"

    def test_t3_3_1_pairwise_moderate_iv_vs_dyn_corr_mutation(self):
        """Tier 3: 正交组合 - 隐波适中 (25%) × 动态相关性突变 (0.76) 独立触发 BEAR"""
        snap = {"option_iv_pct": 25.0, "dynamic_correlation": 0.76}
        res = compute_ten_dimension_votes(snapshot=snap)
        d10 = get_dimension_by_id(res, 10)
        assert d10["vote"] == "BEAR"
        assert d10["delta_pct"] in (-8.0, -0.08)

    def test_t3_3_2_pairwise_extreme_iv_vs_global_circuit_breaker(self):
        """Tier 3: 正交组合 - 隐波极高 (35%) × 全局黑天鹅熔断生效"""
        snap = {"option_iv_pct": 35.0, "ivix_index": 35.0}
        res = compute_ten_dimension_votes(snapshot=snap)
        d10 = get_dimension_by_id(res, 10)
        assert d10["vote"] == "BEAR"
        assert res.get("circuit_breaker_triggered") is True


# ─── Feature 4: 黑天鹅/灰犀牛一票否决熔断门禁 ─────────────────────────

class TestFeature4CircuitBreakerVeto:
    """Feature 4: ivix >= 32.0 或 dyn_corr >= 0.80 或 usdcnh_chg > 0.60% 触发一票否决"""

    def test_t4_1_1_single_factor_ivix_spike(self):
        """Tier 1: 单因子 IVIX 脉冲 (34.5 >= 32.0) -> 熔断生效，多头加仓归零"""
        snap = {"ivix_index": 34.5, "erp_percentile": 85.0}
        res = compute_ten_dimension_votes(snapshot=snap)
        assert res.get("circuit_breaker_triggered") is True
        for d in res["dimensions"]:
            assert d["delta_pct"] <= 0.0, f"Positive delta {d['name']} must be frozen to 0 under circuit breaker"

    def test_t4_1_2_single_factor_dyn_corr_spike(self):
        """Tier 1: 单因子相关性崩塌 (0.83 >= 0.80) -> 熔断生效"""
        snap = {"dynamic_correlation": 0.83, "erp_percentile": 85.0}
        res = compute_ten_dimension_votes(snapshot=snap)
        assert res.get("circuit_breaker_triggered") is True
        for d in res["dimensions"]:
            assert d["delta_pct"] <= 0.0

    def test_t4_1_3_single_factor_usdcnh_chg_spike(self):
        """Tier 1: 单因子汇率急跌 (日变动 +0.75% > 0.60%) -> 熔断生效"""
        snap = {"usdcnh_change_pct": 0.75, "erp_percentile": 85.0}
        macro_multi = {"change_pct": 0.75}
        res = compute_ten_dimension_votes(snapshot=snap, macro_multi=macro_multi)
        assert res.get("circuit_breaker_triggered") is True
        for d in res["dimensions"]:
            assert d["delta_pct"] <= 0.0

    def test_t4_1_4_three_factors_extreme_resonance(self):
        """Tier 1: 三因子极端共振 (ivix=36, dyn_corr=0.85, usdcnh_chg=1.0%) -> 熔断深度生效"""
        snap = {"ivix_index": 36.0, "dynamic_correlation": 0.85, "usdcnh_change_pct": 1.0}
        macro_multi = {"change_pct": 1.0}
        res = compute_ten_dimension_votes(snapshot=snap, macro_multi=macro_multi)
        assert res.get("circuit_breaker_triggered") is True
        assert len(res.get("circuit_breaker_triggers", [])) >= 2
        assert any(d["delta_pct"] < 0 for d in res["dimensions"])

    def test_t4_1_5_all_safe_no_circuit_breaker(self):
        """Tier 1: 常规安全等价类 (ivix=24, dyn_corr=0.45, usdcnh_chg=0.1%) -> 熔断不生效"""
        snap = {"ivix_index": 24.0, "dynamic_correlation": 0.45, "usdcnh_change_pct": 0.10, "erp_percentile": 85.0}
        macro_multi = {"change_pct": 0.10}
        res = compute_ten_dimension_votes(snapshot=snap, macro_multi=macro_multi)
        assert res.get("circuit_breaker_triggered") is False
        assert any(d["delta_pct"] > 0 for d in res["dimensions"])

    def test_t4_2_1_boundary_ivix_31_99_vs_32_00(self):
        """Tier 2: IVIX 32.0 边界微元探测 (31.99 不触发, 32.00 触发)"""
        res1 = compute_ten_dimension_votes(snapshot={"ivix_index": 31.99, "dynamic_correlation": 0.35, "usdcnh_change_pct": 0.0})
        assert res1.get("circuit_breaker_triggered") is False

        res2 = compute_ten_dimension_votes(snapshot={"ivix_index": 32.00, "dynamic_correlation": 0.35, "usdcnh_change_pct": 0.0})
        assert res2.get("circuit_breaker_triggered") is True

    def test_t4_2_2_boundary_dyn_corr_7999_vs_8000(self):
        """Tier 2: 相关性 0.80 边界微元探测 (0.7999 不触发, 0.8000 触发)"""
        res1 = compute_ten_dimension_votes(snapshot={"ivix_index": 20.0, "dynamic_correlation": 0.7999, "usdcnh_change_pct": 0.0})
        assert res1.get("circuit_breaker_triggered") is False

        res2 = compute_ten_dimension_votes(snapshot={"ivix_index": 20.0, "dynamic_correlation": 0.8000, "usdcnh_change_pct": 0.0})
        assert res2.get("circuit_breaker_triggered") is True

    def test_t4_2_3_boundary_usdcnh_chg_0_6000_vs_0_6001(self):
        """Tier 2: 汇率 0.60% 边界微元探测 (0.6000% 不触发, 0.6001% 触发)"""
        res1 = compute_ten_dimension_votes(snapshot={"ivix_index": 20.0, "dynamic_correlation": 0.35, "usdcnh_change_pct": 0.6000})
        assert res1.get("circuit_breaker_triggered") is False

        res2 = compute_ten_dimension_votes(snapshot={"ivix_index": 20.0, "dynamic_correlation": 0.35, "usdcnh_change_pct": 0.6001})
        assert res2.get("circuit_breaker_triggered") is True

    def test_t4_2_4_boundary_freeze_unidirectionality(self):
        """Tier 2: 冻结单向性 - 多头 delta 被截断为 0.0，空头防守减仓保持 -8.0%"""
        snap = {"ivix_index": 33.0, "erp_percentile": 90.0, "option_iv_pct": 30.0}
        res = compute_ten_dimension_votes(snapshot=snap)
        d3 = get_dimension_by_id(res, 3)  # ERP
        d10 = get_dimension_by_id(res, 10)  # Options
        assert d3["delta_pct"] == 0.0, "ERP bull delta must be frozen to 0"
        assert d10["delta_pct"] in (-8.0, -0.08), "Options bear deduction must remain intact"

    def test_t4_2_5_boundary_all_neutral_or_bear_under_cb(self):
        """Tier 2: 全防守态熔断边界 - 无正向多头时触发熔断，系统平稳无异常"""
        snap = {"ivix_index": 35.0, "erp_percentile": 30.0, "cgb_10y_yield": 3.0}
        res = compute_ten_dimension_votes(snapshot=snap)
        assert res.get("circuit_breaker_triggered") is True
        assert res["target_equity_pct"] <= 60

    def test_t4_3_1_pairwise_cb_active_vs_8_bull_votes(self):
        """Tier 3: 正交组合 - 熔断触发 × 8维强多头无法突破熔断硬锁，一票否决权生效"""
        snap = {
            "ivix_index": 34.0,  # CB trigger
            "erp_percentile": 90.0,  # Bull
            "cgb_10y_yield": 1.50,   # Bull
            "dr007_spread_bp": -20.0,# Bull
            "bias_20": 1.5,          # Bull
        }
        res = compute_ten_dimension_votes(snapshot=snap)
        assert res.get("circuit_breaker_triggered") is True
        for d in res["dimensions"]:
            assert d["delta_pct"] <= 0.0, f"Dimension {d['name']} delta {d['delta_pct']} not zeroed"

    def test_t4_3_2_pairwise_cb_inactive_vs_balanced_votes(self):
        """Tier 3: 正交组合 - 熔断未触发 × 正常流程各维度独立计票求和"""
        snap = {"ivix_index": 20.0, "dynamic_correlation": 0.35, "erp_percentile": 80.0}
        res = compute_ten_dimension_votes(snapshot=snap)
        assert res.get("circuit_breaker_triggered") is False
        assert "🚨 极值熔断防御" not in res["summary"]["verdict"]


# ─── Feature 5: 真实数据底座同步、合理区间校验哨与三段式因果链 ─────────────────────

class TestFeature5PurgeLegacyConstantsAndSentinel:
    """Feature 5: 恢复 7.2385 和 4.4200 基线与合理区间校验哨，实现数据底座真实同步与三段式信息决策链"""

    def test_t5_1_1_normal_valid_cross_market_data(self):
        """Tier 1: 正常有效截面 - 汇率处于合理物理区间 [6.85, 7.60]，美债处于 [3.0, 6.0]，美债与中债利差为真实数学计算"""
        indicators = DataLoader.fetch_macro_cross_market_indicators(use_cache=False)
        assert 6.85 <= indicators["usdcnh_rate"] <= 7.60, f"FX {indicators['usdcnh_rate']} outside [6.85, 7.60]"
        assert 3.0 <= indicators["us_10y"] <= 6.0, f"US 10Y {indicators['us_10y']} outside [3.0, 6.0]"
        assert indicators["cgb_10y"] > 0.0, "CGB 10Y should be positive"
        assert abs(indicators["cgb_us_spread_bp"] - round((indicators["cgb_10y"] - indicators["us_10y"]) * 100.0, 1)) < 0.1, "Spread must match math formula"
        assert "treasury_date" in indicators and len(indicators["treasury_date"]) == 10
        assert "usdcnh_date" in indicators and len(indicators["usdcnh_date"]) == 10

    def test_t5_1_2_real_fx_rates_preserved(self):
        """Tier 1: 真实汇率保留 - 模拟汇率 7.2385 处于合理区间 [6.85, 7.60] 原样保留"""
        with patch("AGY2_FundAdvisory.data_loader.fetch_realtime_usdcnh_fx", return_value={"rate": 7.2385, "change_pct": -0.02, "source": "test", "date": "2026-11-14"}):
            ind = DataLoader.fetch_macro_cross_market_indicators(use_cache=False)
            assert 6.85 <= ind["usdcnh_rate"] <= 7.60
            assert ind["usdcnh_rate"] == 7.2385

    def test_t5_1_3_extreme_high_fx_intercepted(self):
        """Tier 1: 极端失真校验 - 外部传入 15.0 (>7.60) 或 2.0 (<6.85) 触发极端防御回退至基线 7.2385"""
        with patch("AGY2_FundAdvisory.data_loader.fetch_realtime_usdcnh_fx", return_value={"rate": 15.0, "change_pct": 0.0, "source": "test", "date": "2026-11-14"}):
            ind = DataLoader.fetch_macro_cross_market_indicators(use_cache=False)
            assert 6.85 <= ind["usdcnh_rate"] <= 7.60
            assert ind["usdcnh_rate"] == 7.2385

    def test_t5_1_4_sync_macro_and_fx_parquet_if_stale(self):
        """Tier 1: 数据底座自愈同步 - sync_macro_and_fx_parquet_if_stale 正常调用并返回真实截面报告"""
        res = DataLoader.sync_macro_and_fx_parquet_if_stale(force=False)
        assert isinstance(res, dict)
        assert res.get("success") is True
        assert "treasury_date" in res and len(res["treasury_date"]) == 10
        assert "fx_date" in res and len(res["fx_date"]) == 10

    def test_t5_1_5_source_code_scan_zero_legacy_constants(self):
        """Tier 1: 源码绝对纯化 - 扫描禁止出现已被拔除的旧常数 6.6676 与 6.6746"""
        banned = ["6.6676", "6.6746"]
        target_files = ["data_loader.py", "advisory_engine.py", "strategy_bridge.py", "portfolio_manager.py"]
        for fn in target_files:
            fp = os.path.join(AGY2_DIR, fn)
            if not os.path.exists(fp):
                continue
            with open(fp, "r", encoding="utf-8") as f:
                content = f.read()
            for b in banned:
                assert b not in content, f"Found banned fake constant '{b}' in {fn}"

    def test_t5_2_1_boundary_fx_preserved_without_clamp(self):
        """Tier 2: 边界汇率校验 - [6.85, 7.60] 边界以内正常保留，越界校准为 7.2385"""
        with patch("AGY2_FundAdvisory.data_loader.fetch_realtime_usdcnh_fx", return_value={"rate": 6.8600, "change_pct": 0.0, "source": "test", "date": "2026-11-14"}):
            ind = DataLoader.fetch_macro_cross_market_indicators(use_cache=False)
            assert ind["usdcnh_rate"] == 6.8600

        with patch("AGY2_FundAdvisory.data_loader.fetch_realtime_usdcnh_fx", return_value={"rate": 7.5900, "change_pct": 0.0, "source": "test", "date": "2026-11-14"}):
            ind2 = DataLoader.fetch_macro_cross_market_indicators(use_cache=False)
            assert ind2["usdcnh_rate"] == 7.5900

    def test_t5_2_2_authentic_treasury_spread_calculation(self):
        """Tier 2: 真实中美利差计算 - 利差为数学差值，无 -278.2 硬编码替换"""
        ind = DataLoader.fetch_macro_cross_market_indicators(use_cache=False)
        expected_spread = round((ind["cgb_10y"] - ind["us_10y"]) * 100.0, 1)
        assert ind["cgb_us_spread_bp"] == expected_spread

    def test_t5_3_1_key_information_insights_three_step_chain(self):
        """Tier 3: 核心契约 - generate_chief_advisor_memo 返回结构化三段式因果链情报"""
        memo = generate_chief_advisor_memo()
        assert "key_information_insights" in memo, "memo must contain key_information_insights"
        insights = memo["key_information_insights"]
        assert isinstance(insights, list)
        assert 3 <= len(insights) <= 5, f"Expected 3-5 intelligence insights, got {len(insights)}"
        required_keys = ["category", "badge", "key_information", "deep_understanding", "action_taken"]
        for idx, item in enumerate(insights):
            for k in required_keys:
                assert k in item, f"Insight #{idx} missing key '{k}'"
                assert isinstance(item[k], str) and len(item[k].strip()) > 0, f"Insight #{idx} '{k}' must not be empty"

    def test_t5_3_2_memo_rendering_with_authentic_data(self):
        """Tier 3: 正交组合 - 备忘录卡片渲染 HTML 包含真实截面与汇率数据"""
        memo = generate_chief_advisor_memo()
        with patch("streamlit.markdown") as mock_st_md:
            render_chief_advisor_memo_card(memo)
            assert mock_st_md.called, "render_chief_advisor_memo_card should call st.markdown"
            html = mock_st_md.call_args[0][0]
            assert "6.6676" not in html
            assert "USD/CNH" in html


# ─── Feature 6: 胶囊4持仓病灶与胶囊5今日行动准则知行合一联动 ─────────────

class TestFeature6MemoCapsule4And5Coherence:
    """Feature 6: 胶囊4与胶囊5知行合一联动，消除割裂"""

    def test_t6_1_1_both_tail_and_deep_loss_coherence(self):
        """Tier 1: 真实战备组合 - 20只尾仓 + 15只深套 -> 胶囊5主结论明确包含“清扫”与“置换深套”"""
        memo = generate_chief_advisor_memo(
            portfolio_pathology={"deep_loss_count": 15, "frag_count": 20, "frag_amt": 500.0}
        )
        act = memo["action_directive"]
        assert "清扫" in act["verdict"]
        assert "尾仓" in act["verdict"]
        assert "深套" in act["verdict"]

    def test_t6_1_2_only_tail_frags_coherence(self):
        """Tier 1: 单尾仓病灶 - 仅检出 10只免赎尾仓 -> 胶囊5主结论优先体现“清扫尾仓”"""
        memo = generate_chief_advisor_memo(
            portfolio_pathology={"deep_loss_count": 0, "frag_count": 10, "frag_amt": 250.0}
        )
        act = memo["action_directive"]
        assert "清扫" in act["verdict"]
        assert "尾仓" in act["verdict"]
        assert "深套" not in act["verdict"]

    def test_t6_1_3_only_deep_loss_coherence(self):
        """Tier 1: 单出血点病灶 - 仅检出 3只深套出血点 -> 胶囊5主结论优先体现“置换深套”"""
        memo = generate_chief_advisor_memo(
            portfolio_pathology={"deep_loss_count": 3, "frag_count": 0, "frag_amt": 0.0}
        )
        act = memo["action_directive"]
        assert "置换" in act["verdict"]
        assert "深套" in act["verdict"]
        assert "尾仓" not in act["verdict"]

    def test_t6_1_4_stop_profit_alert_coherence(self):
        """Tier 1: 止盈警报联动 - 检出止盈预警 -> 胶囊5主结论优先体现止盈锁利"""
        sentry_rep = {
            "alerts": [{"title": "华安黄金ETF右侧破位预警", "dimension": "移动止盈", "action_type": "take_profit"}]
        }
        memo = generate_chief_advisor_memo(
            sentry_rep=sentry_rep,
            portfolio_pathology={"deep_loss_count": 0, "frag_count": 0}
        )
        act = memo["action_directive"]
        assert "止盈" in act["verdict"] or "锁利" in act["verdict"]

    def test_t6_1_5_healthy_account_macro_verdict(self):
        """Tier 1: 健康基准对照 - 0尾仓、0出血点、0止盈 -> 胶囊5输出宏观战术指令"""
        memo = generate_chief_advisor_memo(
            portfolio_pathology={"deep_loss_count": 0, "frag_count": 0, "frag_amt": 0.0}
        )
        act = memo["action_directive"]
        assert act["verdict"] in ("维持底仓吃息", "逆向定投吸筹", "逢高适度止盈")
        assert "清扫" not in act["verdict"]
        assert "置换" not in act["verdict"]

    def test_t6_2_1_boundary_single_tail_frag(self):
        """Tier 2: 尾仓数量单基边界 (frag_count=1) -> 触发“清扫”"""
        memo = generate_chief_advisor_memo(
            portfolio_pathology={"deep_loss_count": 0, "frag_count": 1, "frag_amt": 35.0}
        )
        assert "清扫" in memo["action_directive"]["verdict"]

    def test_t6_2_2_boundary_single_deep_loss(self):
        """Tier 2: 出血点单基边界 (deep_loss_count=1) -> 触发“置换”"""
        memo = generate_chief_advisor_memo(
            portfolio_pathology={"deep_loss_count": 1, "frag_count": 0, "frag_amt": 0.0}
        )
        assert "置换" in memo["action_directive"]["verdict"]

    def test_t6_2_3_boundary_combat_29_real_ledger(self):
        """Tier 2: 真实生产账本 29只基金全量扫描 -> 胶囊4与胶囊5知行合一精准联动"""
        mlm = MultiLedgerManager()
        pm = mlm.get_pm("combat_29_funds")
        memo = generate_chief_advisor_memo(holdings=pm.holdings)
        path = memo["portfolio_pathology"]
        act = memo["action_directive"]
        if path.get("frag_count", 0) > 0 and path.get("deep_loss_count", 0) > 0:
            assert "清扫" in act["verdict"]
            assert "深套" in act["verdict"]
            assert "维持底仓吃息" not in act["verdict"], "Cannot talk about holding base cash when having severe pathology"

    def test_t6_2_4_boundary_tab1_construction_mode(self):
        """Tier 2: 零病灶无误报边界 - Tab 1 拟建仓权重字典模式下胶囊4不误报病灶，胶囊5不误报清扫"""
        weights = {"005561": 0.35, "002351": 0.25, "011613": 0.20, "000216": 0.20}
        memo = generate_chief_advisor_memo(holdings=weights)
        path = memo["portfolio_pathology"]
        act = memo["action_directive"]
        assert "建仓" in path["title"] or "结构校验" in path["title"]
        assert "清扫" not in act["verdict"]
        assert "置换" not in act["verdict"]

    def test_t6_2_5_boundary_empty_holdings(self):
        """Tier 2: 空账本边界防护 - holdings 为空时不发生崩溃或未定义错误"""
        memo = generate_chief_advisor_memo(holdings={})
        assert memo is not None
        assert "action_directive" in memo
        assert "portfolio_pathology" in memo

    def test_t6_3_1_pairwise_severe_pathology_vs_bullish_market(self):
        """Tier 3: 正交组合 - 账户严重病灶 (20尾仓) × 大盘牛市狂热信号 (Bias20=+7.0%) -> 坚决优先清扫置换"""
        snap = {"bias_20": 7.0, "erp_percentile": 85.0}
        memo = generate_chief_advisor_memo(
            snapshot=snap,
            portfolio_pathology={"deep_loss_count": 15, "frag_count": 20, "frag_amt": 450.0}
        )
        act = memo["action_directive"]
        assert "清扫" in act["verdict"]
        assert "深套" in act["verdict"]

    def test_t6_3_2_pairwise_healthy_account_vs_black_swan(self):
        """Tier 3: 正交组合 - 账户健康 (0病灶) × 黑天鹅熔断生效 -> 输出防守避险指引"""
        snap = {"ivix_index": 35.0, "bias_20": -2.0}
        memo = generate_chief_advisor_memo(
            snapshot=snap,
            portfolio_pathology={"deep_loss_count": 0, "frag_count": 0, "frag_amt": 0.0}
        )
        tdv = memo["ten_dimension_votes"]
        assert tdv.get("circuit_breaker_triggered") is True


# ─── Tier 4: Real-World Workload Testing (真实业务综合负载场景) ───────────

class TestTier4RealWorldWorkloads:
    """Tier 4: 跨模块高阶端到端集成与真实业务综合场景演练"""

    def test_scenario_1_combat_29_funds_end_to_end(self):
        """
        场景 1: 29只基金存量战备账本首次加载·病灶清扫与胶囊知行合一
        - 真实载入 combat_29_funds 账本
        - 胶囊4检出数十只免赎尾仓与深套出血点
        - 胶囊5定调结论与副标题输出账户级清扫与置换指令
        - 渲染备忘录 HTML 卡片，验证 0 处 6.6676 与样式安全
        """
        mlm = MultiLedgerManager()
        pm = mlm.get_pm("combat_29_funds")
        assert len(pm.holdings) == 29, "combat_29_funds must contain 29 funds"

        memo = generate_chief_advisor_memo(holdings=pm.holdings)
        path = memo["portfolio_pathology"]
        act = memo["action_directive"]

        assert path["deep_loss_count"] > 0
        assert path["frag_count"] > 0
        assert "清扫" in act["verdict"]
        assert "深套" in act["verdict"]

        with patch("streamlit.markdown") as mock_st_md:
            render_chief_advisor_memo_card(memo)
            assert mock_st_md.called
            html = mock_st_md.call_args[0][0]
            assert "6.6676" not in html
            assert "5.0000" not in html
            assert "清扫" in html
            assert "深套" in html

    def test_scenario_2_black_swan_macro_flash_event(self):
        """
        场景 2: 宏观黑天鹅突发·全多头冻结与一票否决熔断门禁
        - 突发离岸汇率跳涨 +0.70%, IVIX 突破 34.0%, 动态相关性 0.82
        - 维度6产业估值虽低估 (Top3=25%)，但一票否决门禁物理冻结多头加仓项
        - 维度10输出 -8.0% 避险防御
        - 熔断标记确凿存在，因果链公式明示熔断原因
        """
        sectors = make_14_sectors(top3_avg=25.0, median_val=50.0)
        snap = {
            "spot_usdcnh": 7.2800,
            "usdcnh_change_pct": 0.70,
            "ivix_index": 34.0,
            "dynamic_correlation": 0.82,
            "option_iv_pct": 34.0,
            "erp_percentile": 88.0,
        }
        macro_multi = {"change_pct": 0.70}

        with patch("AGY2_FundAdvisory.advisory_engine.OpportunityRadarEngine.get_cached_sectors_fast", return_value=sectors):
            res = compute_ten_dimension_votes(snapshot=snap, macro_multi=macro_multi, radar_top3=sectors[:3], all_sectors=sectors)

        assert res.get("circuit_breaker_triggered") is True
        assert "🚨" in str(res.get("circuit_breaker_reason", "")) or "熔断" in str(res.get("circuit_breaker_reason", ""))

        d6 = get_dimension_by_id(res, 6)
        assert d6["delta_pct"] == 0.0, "Sector valuation +5% must be frozen to 0 by circuit breaker"
        assert "🚨" in d6["reason"] or "熔断" in d6["reason"]

        d10 = get_dimension_by_id(res, 10)
        assert d10["vote"] == "BEAR"
        assert d10["delta_pct"] in (-8.0, -0.08)

    def test_scenario_3_real_data_bullish_confluence(self):
        """
        场景 3: 产业低估机会与资金情绪协同共振·真数据驱动多头进攻
        - 宏观平稳 (汇率 7.2385, 美债真实截面 4.4200)
        - 维度6 Top3 均值 29.5% (<=35%) 判定 BULL (+5%)
        - 维度7 两市成交 1.4万亿, 均拥挤度 76.5 判定 BULL (+2%)
        - 维度10 隐波 19.5% (<22%), 贴水 12% 判定 BULL
        - 熔断不生效，多维度协同做多
        """
        sectors = make_14_sectors(top3_avg=29.5, median_val=54.0, avg_crowd=76.5)
        snap = {
            "spot_usdcnh": 7.2385,
            "usdcnh_change_pct": -0.05,
            "ivix_index": 19.5,
            "option_iv_pct": 19.5,
            "ic_annualized_basis_rate": 12.0,
            "dynamic_correlation": 0.35,
            "market_turnover_sentiment": {"turnover_str": "14,000 亿", "up_pct": 68.0},
            "bias_20": 1.2
        }

        with patch("AGY2_FundAdvisory.advisory_engine.OpportunityRadarEngine.get_cached_sectors_fast", return_value=sectors):
            res = compute_ten_dimension_votes(snapshot=snap, radar_top3=sectors[:3], all_sectors=sectors)

        assert res.get("circuit_breaker_triggered") is False
        d6 = get_dimension_by_id(res, 6)
        d7 = get_dimension_by_id(res, 7)
        d10 = get_dimension_by_id(res, 10)

        assert d6["vote"] == "BULL"
        assert d7["vote"] == "BULL"
        assert d10["vote"] == "BULL"
        assert res["target_equity_pct"] >= 65
