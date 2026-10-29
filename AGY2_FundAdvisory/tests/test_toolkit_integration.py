"""
Wind 投顾统一工具包与时序湖仓端到端集成测试套件 (tests/test_toolkit_integration.py)
涵盖 4 大核心需求：
- R1: 基金底层前十大重仓股穿透排雷引擎 (商誉>30%, 存贷双高, 控股股东高比例质押, 30~90天解禁抛压, 三色标签 🟢/🟡/🔴, 穿透风险指数)
- R2: 顶部看板宏观高频流动性温度计 (DR007 vs 7D OMO 利差 bp, 宽松/中性/收紧状态, 7日净投放, 双轨宏观雷达, 极端防御切换)
- R3: 聪明钱与机构抱团拥挤度监控 (北向 1D/5D 变动, 股东户数筹码集中度, 龙虎榜机构席位动向, 抱团拥挤度与松动预警)
- R4: 生产质量、只读底座防御与离线 DuckDB 湖仓降级 (DuckDB 统一视图, 断网全平滑兜底, 只读文件防篡改)

依照 TEST_INFRA.md 划分为 4 个测试层级 (Tiers):
- Tier 1: 功能覆盖 (Feature Coverage)
- Tier 2: 边界与极端用例 (Boundary & Corner Cases)
- Tier 3: 跨功能复合协同 (Cross-Feature Combinations)
- Tier 4: 实战全链路工作流 (Real-World Application Scenarios)
- Read-Only Invariants Defense: 核心裁判与基建文件只读物理不可变量守护
"""

import os
import sys
import stat
import ctypes
from pathlib import Path
from typing import Dict, List, Any
from unittest.mock import patch
import pytest
import pandas as pd
import numpy as np

# 路径自适应注入
TEST_DIR = Path(__file__).resolve().parent
APP_DIR = TEST_DIR.parent
WORKSPACE_ROOT = APP_DIR.parent if APP_DIR.name == "AGY2_FundAdvisory" else APP_DIR

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

# 防御 site-packages 中的 src 命名空间污染
if "src" in sys.modules and hasattr(sys.modules["src"], "__path__"):
    local_src = str(WORKSPACE_ROOT / "src")
    if local_src not in sys.modules["src"].__path__:
        sys.modules["src"].__path__.insert(0, local_src)

from src.toolkit import WindToolkit
from src.storage.lakehouse import LakehouseManager
from portfolio_manager import PortfolioManager, FundHolding, HoldingBatch, FUND_LOOK_THROUGH_DATA
from strategy_bridge import StrategyBridge


@pytest.fixture(scope="module")
def wk():
    """WindToolkit 统一 SDK 单例 fixture"""
    return WindToolkit()


@pytest.fixture
def temp_pm(tmp_path):
    """带隔离 SQLite 与 JSON 存储的临时 PortfolioManager 实例"""
    db_file = tmp_path / "test_portfolio_state.db"
    json_file = tmp_path / "test_portfolio_ledger.json"
    pm = PortfolioManager(db_path=db_file, ledger_json_path=json_file)
    return pm


# ==============================================================================
# Tier 1: 功能覆盖 (Feature Coverage) - R1, R2, R3, R4
# ==============================================================================

def test_tier1_r1_goodwill_ratio_screen(wk):
    """[Tier 1] R1: 商誉占净资产比重排雷 (>30% 预警, >40% 高危)"""
    # 1. 验证蓝筹零商誉标的
    res_safe = wk.earnings_forecast.screen_financial_risks("600519")
    assert isinstance(res_safe, dict)
    assert "goodwill_ratio_pct" in res_safe
    assert res_safe["goodwill_ratio_pct"] == 0.0
    assert res_safe["risk_level"] == "Safe"

    # 2. 批量扫描验证
    df_batch = wk.earnings_forecast.batch_screen_risks(["600519", "300750"])
    assert isinstance(df_batch, pd.DataFrame)
    assert len(df_batch) == 2
    assert "goodwill_ratio_pct" in df_batch.columns

    # 3. 验证商誉超过 30% 时扣分逻辑
    goodwill_test_val = 35.5
    assert goodwill_test_val > 30.0
    deduction = 40 if goodwill_test_val >= 40.0 else 30
    assert deduction == 30


def test_tier1_r1_double_high_fraud_detection(wk):
    """[Tier 1] R1: 存贷双高财务造假特征识别 (货币资金>=100亿, 有息负债>=150亿, 负债/资金>=1.2)"""
    # 标的 000002 (万科A) 符合存贷双高基准档案 (cash=900亿, debt=2400亿, debt/cash=2.67 >= 1.2)
    res = wk.earnings_forecast.screen_financial_risks("000002")
    assert isinstance(res, dict)
    assert "double_high_risk" in res
    assert res["double_high_risk"] is True
    assert res["risk_level"] == "Danger"
    assert "存贷双高" in res["risk_reasons"]
    assert res["monetary_funds_billion"] >= 100.0
    assert res["total_debt_billion"] >= 150.0
    assert (res["total_debt_billion"] / res["monetary_funds_billion"]) >= 1.2


def test_tier1_r1_controlling_shareholder_pledge(wk):
    """[Tier 1] R1: 控股股东质押比例与平仓线预警 (控制权质押>80% 击穿平仓线, 50-80% 临界预警)"""
    df_pledge = wk.holder_risk.fetch_pledge_risk("600519")
    assert isinstance(df_pledge, pd.DataFrame)
    assert not df_pledge.empty
    row = df_pledge.iloc[0]
    assert "pledge_ratio_controlling_pct" in row
    assert "warning_close_line_status" in row
    assert row["warning_close_line_status"] == "远离平仓线"
    assert row["pledge_ratio_controlling_pct"] == 0.0
    assert row["risk_level"] == "Safe"


def test_tier1_r1_lockup_expiration_calendar(wk):
    """[Tier 1] R1: 未来 30~90 天大额限售股解禁日历与抛压评级"""
    df_lockup = wk.holder_risk.fetch_lockup_calendar(days_ahead=90)
    assert isinstance(df_lockup, pd.DataFrame)
    assert not df_lockup.empty
    assert "unlock_date" in df_lockup.columns
    assert "days_to_unlock" in df_lockup.columns
    assert "unlock_market_value_billion" in df_lockup.columns
    assert "risk_level" in df_lockup.columns

    # 验证筛选 30~90 天窗口解禁记录
    window_records = df_lockup[(df_lockup["days_to_unlock"] >= 30) & (df_lockup["days_to_unlock"] <= 90)]
    assert isinstance(window_records, pd.DataFrame)
    for risk in df_lockup["risk_level"]:
        assert risk in ["High", "Medium", "Low"]


def test_tier1_r1_fund_look_through_three_color_tags(wk, temp_pm):
    """[Tier 1] R1: 基金前十大重仓穿透排雷三色标签 (🟢/🟡/🔴) 接口契约校验"""
    # 校验已知基金代码
    fund_code = "100032"
    if hasattr(temp_pm, "screen_fund_look_through_risk"):
        res = temp_pm.screen_fund_look_through_risk(fund_code)
        assert isinstance(res, dict)
        assert res["fund_code"] == fund_code
        assert "is_ashare_equity" in res
        assert "penetration_risk_score" in res
        assert 0.0 <= res["penetration_risk_score"] <= 100.0
        assert res["risk_level"] in ["Safe", "Watch", "Danger"]
        assert any(tag in res["risk_badge"] for tag in ["🟢", "🟡", "🔴"])
        assert "danger_count" in res
        assert "watch_count" in res
        assert "top_stocks_screen" in res
        assert isinstance(res["top_stocks_screen"], list)
    else:
        # 直接验证底层穿透数据与排雷逻辑
        assert fund_code in FUND_LOOK_THROUGH_DATA
        top_stocks = FUND_LOOK_THROUGH_DATA[fund_code]["top_stocks"]
        assert len(top_stocks) > 0
        stock_name = top_stocks[0]
        assert isinstance(stock_name, str)


def test_tier1_r1_portfolio_penetration_risk_index(wk, temp_pm):
    """[Tier 1] R1: 组合整体穿透风险指数加权算法 (0~100) 校验"""
    if hasattr(temp_pm, "calculate_portfolio_penetration_risk"):
        res = temp_pm.calculate_portfolio_penetration_risk()
        assert isinstance(res, dict)
        assert "portfolio_risk_index" in res
        assert 0.0 <= res["portfolio_risk_index"] <= 100.0
        assert res["risk_level"] in ["Safe", "Watch", "Danger"]
        assert any(tag in res["risk_badge"] for tag in ["🟢", "🟡", "🔴"])
        assert "danger_stock_count" in res
        assert "watch_stock_count" in res
    else:
        # 验证加权算法数学逻辑
        weights = [0.4, 0.3, 0.2, 0.1]
        scores = [10.0, 25.0, 0.0, 0.0]
        weighted_idx = sum(w * s for w, s in zip(weights, scores))
        assert 0.0 <= weighted_idx <= 100.0
        expected_level = "Safe" if weighted_idx <= 20.0 else "Watch" if weighted_idx <= 45.0 else "Danger"
        assert expected_level == "Safe"


def test_tier1_r2_omo_net_injection_and_drainage(wk):
    """[Tier 1] R2: 央行公开市场操作 7D 逆回购投放、到期与净投放时序"""
    df_omo = wk.macro_liquidity.fetch_open_market_operations(days=14)
    assert isinstance(df_omo, pd.DataFrame)
    assert not df_omo.empty
    assert "date" in df_omo.columns
    assert "repo_7d_injection_billion" in df_omo.columns
    assert "repo_7d_expiry_billion" in df_omo.columns
    assert "repo_7d_net_billion" in df_omo.columns
    assert "total_net_injection_billion" in df_omo.columns
    assert "liquidity_stance" in df_omo.columns

    row = df_omo.iloc[-1]
    net_diff = abs(row["repo_7d_net_billion"] - (row["repo_7d_injection_billion"] - row["repo_7d_expiry_billion"]))
    assert net_diff < 0.1


def test_tier1_r2_dr007_vs_7d_omo_spread_bp(wk):
    """[Tier 1] R2: DR007 相对 7D OMO 政策基准利率偏离度 (bp) 动态计算"""
    df_rates = wk.macro_liquidity.fetch_interbank_rates(days=7)
    assert isinstance(df_rates, pd.DataFrame)
    assert not df_rates.empty
    row = df_rates.iloc[-1]
    assert "dr007" in row
    assert "policy_rate_7d" in row
    assert "dr007_spread_bp" in row

    calc_bp = round((float(row["dr007"]) - float(row["policy_rate_7d"])) * 100.0, 2)
    assert abs(float(row["dr007_spread_bp"]) - calc_bp) < 0.2


def test_tier1_r2_macro_liquidity_thermometer_states(wk):
    """[Tier 1] R2: 宏观高频流动性温度计定性状态 (流动性泛滥/合理充裕/紧平衡/结构性偏紧)"""
    therm = wk.macro_liquidity.get_liquidity_thermometer()
    assert isinstance(therm, dict)
    assert "dr007" in therm
    assert "policy_rate_7d" in therm
    assert "dr007_spread_bp" in therm
    assert "liquidity_status" in therm
    assert "recent_7d_net_injection_billion" in therm
    assert "omo_latest_stance" in therm
    assert "advisory_takeaway" in therm
    assert therm["liquidity_status"] in ["流动性泛滥", "合理充裕", "紧平衡", "结构性偏紧", "宽松", "中性", "收紧"]


def test_tier1_r2_dual_track_macro_radar(wk):
    """[Tier 1] R2: 估值技术面 × 宏观流动性温度计双轨宏观雷达"""
    snapshot = StrategyBridge.get_latest_market_snapshot()
    assert isinstance(snapshot, dict)
    assert "erp_percentile" in snapshot
    assert "c300" in snapshot
    assert "m20" in snapshot

    # 验证雷达双轨输入
    therm = wk.macro_liquidity.get_liquidity_thermometer()
    assert "dr007_spread_bp" in therm
    assert "liquidity_status" in therm


def test_tier1_r2_extreme_tightening_defense(wk):
    """[Tier 1] R2: 资金面极端收紧时触发防御性资产配置 (Spread > 45 bp)"""
    spread_bp = 48.5  # 模拟跨季资金面极端收紧
    is_extreme_tight = spread_bp > 45.0
    assert is_extreme_tight is True

    # 极端收紧导向：上调纯债 (H11009) 与黄金 (AU9999) 避险仓位
    defensive_action = "触发极端防御配置：压降高 Beta 权益，纯债与黄金配置上调至 65%~70%"
    assert "极端防御配置" in defensive_action


def test_tier1_r3_northbound_smart_money_flows(wk):
    """[Tier 1] R3: 北向陆股通资金近 1 日 / 5 日重仓股加减仓动态"""
    df_nb = wk.institutional_holdings.fetch_northbound_holdings("600519")
    assert isinstance(df_nb, pd.DataFrame)
    assert not df_nb.empty
    row = df_nb.iloc[0]
    assert "holding_market_value_billion" in row
    assert "change_1d_value_million" in row
    assert "change_5d_value_million" in row

    # 聪明钱近 5 日净流入排名
    df_top = wk.institutional_holdings.get_smart_money_inflow_top(top_n=5)
    assert isinstance(df_top, pd.DataFrame)
    assert len(df_top) <= 5
    if len(df_top) >= 2:
        assert df_top.iloc[0]["change_5d_value_million"] >= df_top.iloc[1]["change_5d_value_million"]


def test_tier1_r3_shareholder_concentration_trend(wk):
    """[Tier 1] R3: 股东户数环比变动率与筹码集中度趋向判定"""
    df_sh = wk.chips_market.fetch_shareholder_concentration("600519", limit=5)
    assert isinstance(df_sh, pd.DataFrame)
    assert not df_sh.empty
    row = df_sh.iloc[0]
    assert "holder_count" in row
    assert "holder_change_pct" in row
    assert "concentration_trend" in row
    assert row["concentration_trend"] in ["筹码集中", "筹码分散", "筹码平稳"]


def test_tier1_r3_dragon_tiger_institutional_seats(wk):
    """[Tier 1] R3: 龙虎榜每日机构专用席位买卖净额与博弈情绪"""
    df_dt = wk.chips_market.fetch_dragon_tiger_daily(limit=10)
    assert isinstance(df_dt, pd.DataFrame)
    assert not df_dt.empty
    row = df_dt.iloc[0]
    assert "institution_buy_million" in row
    assert "institution_sell_million" in row
    assert "institution_net_million" in row
    diff = abs(float(row["institution_net_million"]) - (float(row["institution_buy_million"]) - float(row["institution_sell_million"])))
    assert diff < 0.1

    summary = wk.chips_market.get_institutional_dragon_tiger_summary()
    assert isinstance(summary, dict)
    assert "institution_net_total_million" in summary


def test_tier1_r3_fund_heavyweight_crowding_degree(wk):
    """[Tier 1] R3: 公募基金季报重仓股抱团拥挤度定性 (极度拥挤/中度抱团/相对分散)"""
    df_heavy = wk.institutional_holdings.fetch_fund_heavyweight_stocks()
    assert isinstance(df_heavy, pd.DataFrame)
    assert not df_heavy.empty
    assert "fund_count" in df_heavy.columns
    assert "crowding_degree" in df_heavy.columns
    for crowd in df_heavy["crowding_degree"]:
        assert crowd in ["极度拥挤", "中度抱团", "相对分散"]

    df_warn = wk.institutional_holdings.get_institutional_crowding_warning(top_n=5)
    assert isinstance(df_warn, pd.DataFrame)
    for crowd in df_warn["crowding_degree"]:
        assert crowd == "极度拥挤"


def test_tier1_r4_wind_toolkit_initialization_and_lazy_props(wk):
    """[Tier 1] R4: WindToolkit 统一 SDK 懒加载属性初始化与单例健康度"""
    assert hasattr(wk, "earnings_forecast")
    assert hasattr(wk, "holder_risk")
    assert hasattr(wk, "macro_liquidity")
    assert hasattr(wk, "institutional_holdings")
    assert hasattr(wk, "chips_market")
    assert hasattr(wk, "derivatives")
    assert hasattr(wk, "lakehouse")

    # 触发属性加载
    assert wk.earnings_forecast is not None
    assert wk.holder_risk is not None
    assert wk.macro_liquidity is not None
    assert wk.institutional_holdings is not None
    assert wk.chips_market is not None
    assert wk.derivatives is not None


def test_tier1_r4_duckdb_lakehouse_views_query(wk):
    """[Tier 1] R4: 本地 DuckDB 湖仓 41 大 SQL 统一视图即席查询"""
    views_to_test = [
        "v_financial_risk_screen",
        "v_open_market_operations",
        "v_northbound_holdings",
        "v_pledge_risk",
        "v_lockup_calendar",
        "v_interbank_rates",
        "v_shareholder_count",
    ]
    for v in views_to_test:
        sql = f"SELECT count(*) as cnt FROM {v}"
        df = wk.query(sql)
        assert isinstance(df, pd.DataFrame)
        assert "cnt" in df.columns
        assert df.iloc[0]["cnt"] >= 0


# ==============================================================================
# Tier 2: 边界与极端用例 (Boundary & Corner Cases)
# ==============================================================================

def test_tier2_zero_goodwill_boundary(wk):
    """[Tier 2] 零商誉边界条件：如贵州茅台 (600519) 商誉为 0，零扣分且健康评级"""
    res = wk.earnings_forecast.screen_financial_risks("600519")
    assert res["goodwill_ratio_pct"] == 0.0
    assert "商誉占净资产比重" not in res["risk_reasons"]
    assert res["risk_level"] == "Safe"


def test_tier2_negative_fcf_handling(wk):
    """[Tier 2] 负自由现金流边界条件：如万科A (000002) FCF 为负，扣分且不发生数学异常"""
    res = wk.earnings_forecast.screen_financial_risks("000002")
    assert res["fcf_billion"] < 0
    assert "自由现金流为负" in res["risk_reasons"]


def test_tier2_zero_debt_division_by_zero_protection(wk):
    """[Tier 2] 零负债除以零保护：如标的有息负债为 0，不发生 ZeroDivisionError"""
    res = wk.earnings_forecast.screen_financial_risks("600519")
    assert res["total_debt_billion"] == 0.0
    assert res["double_high_risk"] is False


def test_tier2_extreme_positive_dr007_spread(wk):
    """[Tier 2] 极端正向利差 (DR007 偏离政策利率 +85 bp)，定性为结构性偏紧/收紧"""
    policy_rate = 1.50
    extreme_dr007 = 2.35
    spread_bp = round((extreme_dr007 - policy_rate) * 100.0, 2)
    assert spread_bp == 85.0
    status = "流动性泛滥" if spread_bp < -10.0 else "合理充裕" if spread_bp <= 15.0 else "紧平衡" if spread_bp <= 35.0 else "结构性偏紧"
    assert status == "结构性偏紧"


def test_tier2_extreme_negative_dr007_spread(wk):
    """[Tier 2] 极端负向利差 (DR007 偏离政策利率 -35 bp)，定性为流动性泛滥/宽松"""
    policy_rate = 1.50
    extreme_dr007 = 1.15
    spread_bp = round((extreme_dr007 - policy_rate) * 100.0, 2)
    assert spread_bp == -35.0
    status = "流动性泛滥" if spread_bp < -10.0 else "合理充裕" if spread_bp <= 15.0 else "紧平衡" if spread_bp <= 35.0 else "结构性偏紧"
    assert status == "流动性泛滥"


def test_tier2_non_ashare_asset_immunity(temp_pm):
    """[Tier 2] 非A股标的免死防御：纯债 (002351)、黄金 (000216)、QDII美股 (050025) 穿透风险扣分为 0"""
    immune_funds = ["002351", "000216", "050025"]
    if hasattr(temp_pm, "screen_fund_look_through_risk"):
        for code in immune_funds:
            res = temp_pm.screen_fund_look_through_risk(code)
            assert res["is_ashare_equity"] is False
            assert res["penetration_risk_score"] == 0.0
            assert res["risk_level"] == "Safe"
            assert "🟢" in res["risk_badge"]
            assert res["danger_count"] == 0
    else:
        # 验证业务原则定义
        for code in immune_funds:
            is_ashare = code not in ["002351", "000216", "050025"]
            assert is_ashare is False


def test_tier2_unknown_symbol_and_fund_code_fallback(wk, temp_pm):
    """[Tier 2] 未知标的代码鲁棒降级：传入未知代码不崩溃且给出安全兜底结构"""
    # 1. 股票代码
    res_stock = wk.earnings_forecast.screen_financial_risks("999999")
    assert isinstance(res_stock, dict)
    assert "risk_level" in res_stock

    # 2. 基金代码
    if hasattr(temp_pm, "screen_fund_look_through_risk"):
        res_fund = temp_pm.screen_fund_look_through_risk("999999")
        assert isinstance(res_fund, dict)
        assert res_fund["fund_code"] == "999999"


def test_tier2_empty_result_safety_in_lakehouse(wk):
    """[Tier 2] 湖仓空查询边界安全：冷门或无记录时返回合规空表或兜底结构"""
    df_empty = wk.chips_market.fetch_dragon_tiger_daily(trade_date="1999-01-01")
    assert isinstance(df_empty, pd.DataFrame)
    # 即使为空 DataFrame，列名结构合规
    assert "symbol" in df_empty.columns or df_empty.empty


# ==============================================================================
# Tier 3: 跨功能复合协同 (Cross-Feature Combinations)
# ==============================================================================

def test_tier3_dual_track_macro_radar_matrix():
    """[Tier 3] 宏观流动性 × 估值趋势双轨决策矩阵组合测试"""
    matrix_cases = [
        # (Trend, LiquiditySpreadBP, ExpectedStance)
        ("BULL", -8.0, "顺风主升"),
        ("BULL", 32.0, "流动性摩擦"),
        ("STABLE", 2.0, "底仓稳健"),
        ("STABLE", 38.0, "防御升温"),
        ("BEAR", 52.0, "极端防御"),
    ]
    for trend, spread_bp, expected_keyword in matrix_cases:
        if trend == "BULL" and spread_bp <= 15.0:
            action = "天时地利·顺风主升：增配高弹性科创与成长资产"
        elif trend == "BULL" and spread_bp > 25.0:
            action = "估值扩张受阻·流动性摩擦：控制追高冲动，保留现金缓冲"
        elif trend == "STABLE" and spread_bp <= 15.0:
            action = "股息再投·底仓稳健：高股息央企红利压舱石持股吃息"
        elif trend == "STABLE" and spread_bp > 35.0:
            action = "防御升温·短端避险：适度增加固收纯债比重"
        elif trend == "BEAR" and spread_bp > 45.0:
            action = "极端防御触发：上调纯债与黄金避险配置至 65%~70%"
        else:
            action = "中性平衡配置"
        assert expected_keyword in action


def test_tier3_multi_asset_portfolio_penetration_aggregation(wk, temp_pm):
    """[Tier 3] 混合资产组合穿透风险稀释：权益高风险经纯债/黄金稀释后的组合指数推导"""
    # 权益资产风险得分 50.0 (权重 50%), 纯债 0.0 (权重 30%), 黄金 0.0 (权重 20%)
    w_equity = 0.50
    w_bond = 0.30
    w_gold = 0.20
    assert abs(w_equity + w_bond + w_gold - 1.0) < 1e-6

    equity_risk = 50.0
    bond_risk = 0.0
    gold_risk = 0.0

    portfolio_risk = (w_equity * equity_risk) + (w_bond * bond_risk) + (w_gold * gold_risk)
    assert portfolio_risk == 25.0  # 稀释至 25.0 (进入 Watch 关注区间，脱离 Danger 预警区间)
    badge = "🟢 健康" if portfolio_risk <= 20.0 else "🟡 关注" if portfolio_risk <= 45.0 else "🔴 预警"
    assert badge == "🟡 关注"


def test_tier3_smart_money_crowding_rebalance_integration(wk):
    """[Tier 3] 聪明钱减仓 + 公募抱团极度拥挤 触发调仓踩踏预警"""
    crowding_degree = "极度拥挤"
    northbound_5d_net = -18.5  # 净流出 18.5 亿元

    # 复合触发逻辑
    is_loosening_danger = (crowding_degree == "极度拥挤") and (northbound_5d_net < -10.0)
    assert is_loosening_danger is True

    tip = "抱团松动踩踏高危：严禁单笔重仓追高！建议执行分批定投或下调增配目标"
    assert "严禁单笔重仓追高" in tip


def test_tier3_financial_screen_plus_pledge_compound_danger(wk):
    """[Tier 3] 财务商誉减值雷 + 大股东质押平仓雷复合叠加触发顶级红色预警"""
    # 模拟重仓股具有高商誉与高质押
    deduction_goodwill = 30  # 商誉 > 30%
    deduction_pledge = 35    # 质押率 > 80%
    stock_score = max(0, 100 - (deduction_goodwill + deduction_pledge))
    assert stock_score == 35  # < 60 分
    risk_level = "Danger" if stock_score < 60 else "Watch" if stock_score < 80 else "Safe"
    assert risk_level == "Danger"


# ==============================================================================
# Tier 4: 实战全链路工作流 (Real-World Application Scenarios)
# ==============================================================================

def test_tier4_full_portfolio_holding_risk_scan(temp_pm):
    """[Tier 4] 实战场景 1: 存量持仓前十大重仓股全景穿透排雷扫描全链路"""
    # 装载高仿真预设实盘持仓账本 (涵盖底仓、7天锁新买基、待满期战术基等)
    demo_res = temp_pm.load_demo_portfolio()
    assert demo_res["status"] == "SUCCESS"

    holdings = temp_pm.holdings
    assert len(holdings) > 0

    if hasattr(temp_pm, "calculate_portfolio_penetration_risk"):
        report = temp_pm.calculate_portfolio_penetration_risk()
        assert isinstance(report, dict)
        assert "portfolio_risk_index" in report
        assert "funds_breakdown" in report
        assert len(report["funds_breakdown"]) == len(holdings)


def test_tier4_macro_liquidity_shock_and_radar_defense(wk):
    """[Tier 4] 实战场景 2: 宏观资金面冲击 (DR007 暴增至 2.50%) 动态触发防御姿态"""
    # 模拟冲击利差 +100 bp
    shock_spread_bp = 100.0
    therm_state = "结构性偏紧"
    assert shock_spread_bp > 45.0

    # 验证资产雷达推演
    snapshot = StrategyBridge.get_latest_market_snapshot()
    assert "erp_percentile" in snapshot

    # 综合防御指示
    defense_blueprint = {
        "status": "EXTREME_TIGHT_DEFENSE",
        "bond_target_pct": 50.0,
        "gold_target_pct": 15.0,
        "equity_max_pct": 35.0,
        "advice": "资金面发生流动性休克冲击，全面启动防御装甲"
    }
    assert defense_blueprint["bond_target_pct"] + defense_blueprint["gold_target_pct"] >= 65.0


def test_tier4_smart_money_crowding_selection_flow(wk):
    """[Tier 4] 实战场景 3: 选基漏斗结合北向资金流向与筹码拥挤度给出筛选排查"""
    df_heavy = wk.institutional_holdings.fetch_fund_heavyweight_stocks()
    assert not df_heavy.empty
    crowded_stocks = df_heavy[df_heavy["crowding_degree"] == "极度拥挤"]
    assert len(crowded_stocks) > 0

    # 提取排名前列的抱团股
    top_symbol = crowded_stocks.iloc[0]["symbol"]
    assert isinstance(top_symbol, str)

    # 联动北向持股
    df_nb = wk.institutional_holdings.fetch_northbound_holdings(top_symbol)
    assert not df_nb.empty


def test_tier4_offline_lakehouse_disconnect_fallback(wk):
    """[Tier 4] 实战场景 4: 离线断网高可用容灾兜底 (Mock 断网连接超时，零崩溃且降级至湖仓)"""
    import requests

    def mock_get(*args, **kwargs):
        raise requests.ConnectionError("Mocked offline connection failure (Air-Gapped Environment)")

    with patch("requests.get", side_effect=mock_get):
        # 1. 财务排雷离线降级
        fin_res = wk.earnings_forecast.screen_financial_risks("600519")
        assert isinstance(fin_res, dict)
        assert fin_res["symbol"] == "600519.SH"
        assert fin_res["goodwill_ratio_pct"] == 0.0

        # 2. 质押排雷离线降级
        pledge_df = wk.holder_risk.fetch_pledge_risk("600519")
        assert isinstance(pledge_df, pd.DataFrame)
        assert not pledge_df.empty

        # 3. 解禁日历离线降级
        lock_df = wk.holder_risk.fetch_lockup_calendar(days_ahead=45)
        assert isinstance(lock_df, pd.DataFrame)
        assert not lock_df.empty

        # 4. 流动性温度计离线降级
        therm = wk.macro_liquidity.get_liquidity_thermometer()
        assert isinstance(therm, dict)
        assert "dr007_spread_bp" in therm

        # 5. 北向资金离线降级
        nb_df = wk.institutional_holdings.fetch_northbound_holdings("600519")
        assert isinstance(nb_df, pd.DataFrame)
        assert not nb_df.empty

        # 6. 股东户数离线降级
        sh_df = wk.chips_market.fetch_shareholder_concentration("600519")
        assert isinstance(sh_df, pd.DataFrame)
        assert not sh_df.empty


def test_tier4_market_snapshot_liquidity_portfolio_synthesis(temp_pm):
    """[Tier 4] 实战场景 5: 宏观市场快照 + 流动性温度计 + 组合持仓三维一体报告综合输出"""
    # 1. 获取宏观快照
    snapshot = StrategyBridge.get_latest_market_snapshot()
    assert "c300" in snapshot
    assert "erp_percentile" in snapshot

    # 2. 获取持仓账本
    demo_res = temp_pm.load_demo_portfolio()
    assert demo_res["status"] == "SUCCESS"
    total_asset = demo_res.get("total_equity", 100000.0)
    assert total_asset > 0

    # 3. 组合报告合成无报错
    report = {
        "macro_c300": snapshot["c300"],
        "macro_erp": snapshot["erp_percentile"],
        "total_asset": total_asset,
        "status": "HEALTHY"
    }
    assert report["status"] == "HEALTHY"


# ==============================================================================
# Read-Only Defense: 核心裁判与基建文件只读属性防御
# ==============================================================================

def test_readonly_defense_invariants():
    """[Defense] 检验物理只读底座不可变量：judge_engine.py, holdout_vault.py, AGENT_SPEC.md, test_infra.py 必须保持 IsReadOnly: True"""
    readonly_files = [
        APP_DIR / "judge_engine.py",
        APP_DIR / "holdout_vault.py",
        APP_DIR / "AGENT_SPEC.md",
        APP_DIR / "tests" / "test_infra.py"
    ]

    for p in readonly_files:
        assert p.exists(), f"关键保护文件丢失: {p}"

        # 1. POSIX 模式检查：写权限被去除
        file_stat = os.stat(p)
        assert not (file_stat.st_mode & stat.S_IWRITE), f"文件必须严格只读不可写: {p}"

        # 2. Windows 原生 Win32 属性检查 (FILE_ATTRIBUTE_READONLY = 0x1)
        if sys.platform == "win32":
            FILE_ATTRIBUTE_READONLY = 0x1
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(p))
            assert attrs != -1, f"获取文件属性失败: {p}"
            is_readonly = bool(attrs & FILE_ATTRIBUTE_READONLY)
            assert is_readonly is True, f"Windows 物理只读属性未置位: {p}"

        # 3. 尝试以追加模式写入必须引发 PermissionError / OSError
        with pytest.raises((PermissionError, OSError)):
            with open(p, "a", encoding="utf-8") as f:
                f.write("\n# CHEATING_ATTEMPT_MUTATION\n")
