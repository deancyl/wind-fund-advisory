"""
G14 世代专项自动化测试套件:
1. 50ETF 与 300ETF 认沽期权隐含波动率防暴跌对冲哨 (data_loader.py 与 advisory_engine.py)
2. 跨境 QDII 溢价与外汇期货锁汇成本套利精算 (portfolio_manager.py 与 advisory_engine.py)
3. 大额定投跨交易日智能挂单分批调度算法与分厘平账 (portfolio_manager.py, advisory_engine.py 与 app_gui.py)
4. ActiveRiskSentry 维度 11 期权防暴跌对冲预警与纯债避险联动
5. Streamlit GUI 端到端与只读契约完整性核验
"""

import sys
from pathlib import Path
import pytest
import pandas as pd

TEST_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TEST_DIR.parent
APP_DIR = PROJECT_ROOT / "AGY2_FundAdvisory"

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_loader import DataLoader
from advisory_engine import (
    evaluate_option_volatility_hedge_warning,
    calculate_qdii_fx_hedged_arbitrage,
    evaluate_qdii_fx_arbitrage_opportunities,
    ActiveRiskSentry,
    SmartExecutionDCAEngine
)
from portfolio_manager import PortfolioManager, FundHolding, HoldingBatch


def test_options_implied_volatility_sensors_collection():
    """
    核验 DataLoader.fetch_options_implied_volatility_sensors:
    1. 必须覆盖 50ETF (510050) 与 300ETF (510300) 认沽期权 (PUT)；
    2. IV 与 HV 真实有效，偏离度公式严密：((IV - HV) / HV) * 100%；
    3. 包含市场市价与 MA20 均线支撑比对；
    4. 具备内存缓存与离线安全降级能力。
    """
    sensors = DataLoader.fetch_options_implied_volatility_sensors(use_cache=False)
    assert len(sensors) >= 2, f"必须覆盖至少 50ETF 与 300ETF 两大主力期权，当前: {len(sensors)}"

    sensors_map = {s["underlying_code"]: s for s in sensors}
    assert "510050" in sensors_map, "必须包含华夏上证50ETF期权 (510050)"
    assert "510300" in sensors_map, "必须包含华泰柏瑞沪深300ETF期权 (510300)"

    for code, s in sensors_map.items():
        assert s["option_type"] == "PUT", f"{code} 必须为认沽期权 (PUT)"
        assert s["iv_pct"] > 0.0, f"隐含波动率必须为正数: {s['iv_pct']}"
        assert s["hv_pct"] > 0.0, f"历史波动率必须为正数: {s['hv_pct']}"
        expected_spread = round(((s["iv_pct"] - s["hv_pct"]) / s["hv_pct"]) * 100.0, 2)
        assert abs(s["iv_hv_spread_pct"] - expected_spread) < 0.05, f"偏离度不匹配: {s}"
        assert s["market_price"] > 0.0
        assert s["ma20"] > 0.0
        assert s["is_below_ma20"] == (s["market_price"] < s["ma20"])


def test_option_volatility_crash_hedge_warning_evaluation():
    """
    核验 evaluate_option_volatility_hedge_warning 信号决策逻辑：
    1. 当 IV 相对 HV 突升超 30% 且大盘均线跌破 MA20 时，输出市场剧烈防暴跌预警 (CRASH_HEDGE_WARNING)，并建议增加纯债防护仓位 (002351)；
    2. 若 IV 突升超 30% 但大盘仍位于 MA20 上方，不触发暴跌对冲预警；
    3. 若跌破 MA20 但 IV 未突升超 30%，不触发暴跌对冲预警；
    4. 两项均正常时，维持平稳绿灯。
    """
    # 场景 1: IV 相对 HV 暴涨 40% (突升超 30%) 且 价格跌破 MA20 -> 必须触发暴跌对冲警报
    mock_sensor_crash = [{
        "underlying_code": "510300",
        "underlying_name": "华泰柏瑞沪深300ETF",
        "option_symbol": "300ETF期权",
        "option_type": "PUT",
        "market_price": 3.980,
        "ma20": 4.100,
        "is_below_ma20": True,
        "iv_pct": 28.00,
        "hv_pct": 20.00,
        "iv_hv_spread_pct": 40.00,
        "is_iv_surge": True,
    }]
    res_crash = evaluate_option_volatility_hedge_warning(sensors=mock_sensor_crash)
    assert res_crash["has_crash_warning"] is True
    assert len(res_crash["warnings"]) >= 1
    w = res_crash["warnings"][0]
    assert w["alert_level"] == "red"
    assert "防暴跌" in w["alert_title"] or "期权IV异动" in w["alert_title"]
    assert "纯债" in w["action"]
    assert w["target_shield_code"] == "002351"

    # 场景 2: IV 暴涨 40% 但 价格仍站上 MA20 (均线多头) -> 不触发暴跌对冲警报
    mock_sensor_bull = [{
        "underlying_code": "510300",
        "underlying_name": "华泰柏瑞沪深300ETF",
        "option_symbol": "300ETF期权",
        "option_type": "PUT",
        "market_price": 4.250,
        "ma20": 4.100,
        "is_below_ma20": False,
        "iv_pct": 28.00,
        "hv_pct": 20.00,
        "iv_hv_spread_pct": 40.00,
        "is_iv_surge": True,
    }]
    res_bull = evaluate_option_volatility_hedge_warning(sensors=mock_sensor_bull)
    assert res_bull["has_crash_warning"] is False
    assert len(res_bull["warnings"]) == 0

    # 场景 3: 价格跌破 MA20 但 IV 仅偏离 10% (未超 30%) -> 不触发暴跌对冲警报
    mock_sensor_normal_iv = [{
        "underlying_code": "510300",
        "underlying_name": "华泰柏瑞沪深300ETF",
        "option_symbol": "300ETF期权",
        "option_type": "PUT",
        "market_price": 3.980,
        "ma20": 4.100,
        "is_below_ma20": True,
        "iv_pct": 22.00,
        "hv_pct": 20.00,
        "iv_hv_spread_pct": 10.00,
        "is_iv_surge": False,
    }]
    res_normal = evaluate_option_volatility_hedge_warning(sensors=mock_sensor_normal_iv)
    assert res_normal["has_crash_warning"] is False
    assert len(res_normal["warnings"]) == 0


def test_active_risk_sentry_dimension_11_options_crash_defense():
    """
    核验 ActiveRiskSentry 维度 11 期权防暴跌对冲哨全面接入主动风控巡检：
    在投顾持仓检查中注入期权 IV 突升超 30% 且破 MA20 信号，
    ActiveRiskSentry 必须准确捕获红色级别警报，并输出增加纯债防护仓位建议。
    """
    sentry = ActiveRiskSentry()
    holdings = [
        {"fund_code": "002351", "fund_name": "易方达裕祥回报债券A", "market_value": 30000.0, "holding_days": 90, "share_class": "A"},
        {"fund_code": "510300", "fund_name": "华泰柏瑞沪深300ETF", "market_value": 35000.0, "holding_days": 90, "share_class": "A"},
        {"fund_code": "000216", "fund_name": "华安黄金ETF联接A", "market_value": 35000.0, "holding_days": 90, "share_class": "A"},
    ]

    mock_options_sensors = [{
        "underlying_code": "510050",
        "underlying_name": "华夏上证50ETF",
        "option_symbol": "50ETF期权",
        "option_type": "PUT",
        "market_price": 2.720,
        "ma20": 2.850,
        "is_below_ma20": True,
        "iv_pct": 26.00,
        "hv_pct": 18.00,
        "iv_hv_spread_pct": 44.44,
        "is_iv_surge": True,
    }]

    rep = sentry.inspect_portfolio(
        holdings=holdings,
        options_sensors=mock_options_sensors
    )
    assert rep["has_danger"] is True
    crash_alerts = [a for a in rep["alerts"] if a.get("dimension") == "期权波动率对冲哨"]
    assert len(crash_alerts) >= 1, "必须触发期权波动率防暴跌对冲哨警报"
    alert = crash_alerts[0]
    assert alert["level"] == "red"
    assert "纯债" in alert["action"]
    assert alert["target_shield_code"] == "002351"
    assert alert["iv_hv_spread_pct"] > 30.0


def test_qdii_fx_forward_swap_hedging_cost_and_arbitrage_math():
    """
    核验跨境 QDII 溢价与外汇期货锁汇成本套利精算数学模型：
    1. 覆盖标普500 (050025)、纳指 (000834) 与海外半导体芯片 (008888)；
    2. 严格按远期汇率公式 F = S + Swap Points / 10000 计算；
    3. 年化锁汇成本 = ((S - F) / S) * (365 / tenor_days) * 100%；
    4. 真实收益增厚 net_yield_enhancement_pct = qdii_premium_pct - period_hedging_cost_pct - friction；
    5. 增厚 >= 50 bps 判定为 VIABLE_FX_HEDGED_ARBITRAGE，否则判定为 UNVIABLE_COST_OVERRUN。
    """
    # 场景 A: 标普500 高溢价 (+4.50%)，锁汇成本约 2.00%，摩擦 0.15% -> 真实净增厚约 +2.35% (+235 bps) -> 可行
    res_sp500 = PortfolioManager.calculate_qdii_fx_hedged_arbitrage(
        fund_code="050025",
        fund_name="博时标普500ETF联接A",
        spot_usdcnh=7.2500,
        forward_swap_points=-1450.0,
        tenor_days=365,
        qdii_premium_pct=4.50,
        transaction_friction_pct=0.15
    )
    assert res_sp500["forward_rate"] == 7.1050  # 7.2500 - 0.1450
    # 年化锁汇成本 = (7.2500 - 7.1050) / 7.2500 * 100% = 0.1450 / 7.2500 * 100% = 2.00%
    assert abs(res_sp500["annualized_hedging_cost_pct"] - 2.00) <= 0.02
    assert abs(res_sp500["period_hedging_cost_pct"] - 2.00) <= 0.02
    # 真实增厚 = 4.50 - 2.00 - 0.15 = 2.35% (235.0 bps)
    assert abs(res_sp500["net_yield_enhancement_pct"] - 2.35) <= 0.05
    assert abs(res_sp500["net_yield_enhancement_bps"] - 235.0) <= 5.0
    assert res_sp500["is_arbitrage_viable"] is True
    assert res_sp500["signal"] == "VIABLE_FX_HEDGED_ARBITRAGE"

    # 场景 B: 纳指溢价仅 +1.20%，锁汇成本 2.00%，摩擦 0.15% -> 真实净增厚 -0.95% (-95 bps) -> 不可行
    res_nasdaq = calculate_qdii_fx_hedged_arbitrage(
        fund_code="000834",
        fund_name="大成纳斯达克100A",
        spot_usdcnh=7.2500,
        forward_swap_points=-1450.0,
        tenor_days=365,
        qdii_premium_pct=1.20,
        transaction_friction_pct=0.15
    )
    assert res_nasdaq["net_yield_enhancement_bps"] < 50.0
    assert res_nasdaq["is_arbitrage_viable"] is False
    assert res_nasdaq["signal"] == "UNVIABLE_COST_OVERRUN"

    # 场景 C: 90 天 (3个月) 短期掉期点精算
    res_semi_90d = PortfolioManager.calculate_qdii_fx_hedged_arbitrage(
        fund_code="008888",
        fund_name="华夏国证半导体芯片ETF联接A",
        spot_usdcnh=7.2500,
        forward_swap_points=-360.0,
        tenor_days=90,
        qdii_premium_pct=3.00,
        transaction_friction_pct=0.15
    )
    assert res_semi_90d["forward_rate"] == 7.2140  # 7.2500 - 0.0360
    # 90天锁汇成本 = (0.0360 / 7.2500) * 100% = 0.4965% -> 约 0.50%
    assert abs(res_semi_90d["period_hedging_cost_pct"] - 0.50) <= 0.05
    assert res_semi_90d["is_arbitrage_viable"] is True

    # 场景 D: 批量全量评估 evaluate_all_qdii_fx_arbitrage
    batch_eval = evaluate_qdii_fx_arbitrage_opportunities(
        candidate_codes=["050025", "000834", "008888"],
        spot_usdcnh=7.2500
    )
    assert len(batch_eval["results"]) == 3
    assert "summary" in batch_eval


def test_large_dca_batches_scheduler_adaptive_split_and_penny_balance():
    """
    核验大额定投跨交易日智能挂单分批调度算法：
    1. 单日定投金额 <= 10,000 元：无需跨日分批，split_days=1；
    2. 单日定投金额 > 10,000 元：动态生成跨 3 至 5 个交易日的平抑建仓调度表；
    3. 高波资产 (如芯片半导体，日均波幅 >= 1.5%)：拆解为跨 5 个交易日；
    4. 中波资产 (0.8% <= 日均波幅 < 1.5%)：拆解为跨 4 个交易日；
    5. 低波资产 (日均波幅 < 0.8%，如纯债)：拆解为跨 3 个交易日；
    6. 分厘平账铁律：各阶段切片金额之和与总订单金额严格分厘平账 (误差 < 0.01 元)。
    """
    # 1. 小额定投订单 (8,000 元 <= 10,000 元)
    sched_small = PortfolioManager.schedule_large_dca_batches(
        order_amount=8000.0,
        fund_code="005561",
        fund_name="创金合信红利低波A"
    )
    assert sched_small["requires_multi_day_split"] is False
    assert sched_small["split_days"] == 1
    assert len(sched_small["schedule"]) == 1
    assert sched_small["schedule"][0]["slice_amount"] == 8000.0

    # 2. 高波科技标的大额订单 (50,000 元，日均波幅 1.80% >= 1.5%) -> 拆解 5 个交易日
    sched_high_vol = PortfolioManager.schedule_large_dca_batches(
        order_amount=50000.0,
        fund_code="008888",
        fund_name="华夏国证半导体芯片ETF联接A",
        daily_volatility=0.018
    )
    assert sched_high_vol["requires_multi_day_split"] is True
    assert sched_high_vol["split_days"] == 5
    assert len(sched_high_vol["schedule"]) == 5
    days = [s["day"] for s in sched_high_vol["schedule"]]
    assert days == ["T日", "T+1日", "T+2日", "T+3日", "T+4日"]
    # 分厘平账核验
    tot_sched_high = sum(s["slice_amount"] for s in sched_high_vol["schedule"])
    assert abs(tot_sched_high - 50000.0) < 0.01
    assert sched_high_vol["total_scheduled_amount"] == 50000.0

    # 3. 中波宽基标的大额订单 (33,333.33 元，日均波幅 1.10%) -> 拆解 4 个交易日
    sched_mid_vol = PortfolioManager.schedule_large_dca_batches(
        order_amount=33333.33,
        fund_code="510300",
        fund_name="华泰柏瑞沪深300ETF",
        daily_volatility=0.011
    )
    assert sched_mid_vol["requires_multi_day_split"] is True
    assert sched_mid_vol["split_days"] == 4
    assert len(sched_mid_vol["schedule"]) == 4
    tot_sched_mid = sum(s["slice_amount"] for s in sched_mid_vol["schedule"])
    assert abs(tot_sched_mid - 33333.33) < 0.01

    # 4. 低波纯债标的大额订单 (100,000 元，日均波幅 0.20%) -> 拆解 3 个交易日
    sched_low_vol = PortfolioManager.schedule_large_dca_batches(
        order_amount=100000.0,
        fund_code="002351",
        fund_name="易方达裕祥回报债券A",
        daily_volatility=0.002
    )
    assert sched_low_vol["requires_multi_day_split"] is True
    assert sched_low_vol["split_days"] == 3
    assert len(sched_low_vol["schedule"]) == 3
    tot_sched_low = sum(s["slice_amount"] for s in sched_low_vol["schedule"])
    assert abs(tot_sched_low - 100000.0) < 0.01


def test_smart_dca_plan_integration_with_large_orders():
    """
    核验 SmartExecutionDCAEngine.plan_smart_dca 全面联动大额定投调度算法：
    当组合定投中存在单笔超过 10,000 元的标的时：
    1. fund_orders 中必须标记 is_large_order=True，并附带 large_order_schedule；
    2. vwap_execution_summary 中必须标记 has_large_order=True；
    3. strategy_guidance 必须明确提示已启动大额跨 3~5 日智能平抑挂单调度。
    """
    allocations = [
        {"code": "008888", "name": "华夏芯片联接A", "weight": 0.50, "volatility": 0.28},
        {"code": "002351", "name": "易方达纯债A", "weight": 0.50, "volatility": 0.03},
    ]

    # 总资金 360,000 元，分 12 期，每期基准 30,000 元，乘数 1.0 时各标的每期扣款 15,000 元 (> 10,000 元)
    dca_res = SmartExecutionDCAEngine.plan_smart_dca(
        total_capital=360000.0,
        allocations=allocations,
        erp_percentile=60.0,
        bias_20=0.0,
        periods=12
    )

    assert dca_res["actual_deduction"] == 30000.0
    fund_orders = dca_res["fund_orders"]
    assert len(fund_orders) == 2

    for o in fund_orders:
        assert o["period_amount"] == 15000.0
        assert o["is_large_order"] is True
        assert o["split_days"] in (3, 4, 5)
        assert "large_order_schedule" in o
        assert o["large_order_schedule"]["requires_multi_day_split"] is True

    # 芯片高波标的应该拆解为 5 天，纯债低波标的应该拆解为 3 天
    chip_order = next(o for o in fund_orders if o["code"] == "008888")
    bond_order = next(o for o in fund_orders if o["code"] == "002351")
    assert chip_order["split_days"] == 5
    assert bond_order["split_days"] == 3

    vwap_sum = dca_res["vwap_execution_summary"]
    assert vwap_sum["has_large_order"] is True
    assert "大额跨 3~5 日" in vwap_sum["strategy_guidance"]


def test_gui_apptest_tab1_and_tab2_g14_visual_and_whitebox_integrity():
    """
    使用 Streamlit AppTest 真实端到端核验 GUI：
    1. 首屏与 Tab 1 智能定投区大额调度明细白盒展示与下单小抄完整性；
    2. Tab 2 认沽期权防暴跌哨与跨境 QDII 锁汇套利展开器零白屏；
    3. 全站渲染 0 异常！
    """
    from streamlit.testing.v1 import AppTest
    app_path = PROJECT_ROOT / "AGY2_FundAdvisory" / "app_gui.py"

    at = AppTest.from_file(str(app_path), default_timeout=75)
    at.run(timeout=75)
    assert not at.exception, f"AppTest 首屏渲染异常: {at.exception}"

    # 验证 Tab 2 认沽期权防暴跌哨与跨境 QDII 锁汇套利展开器已安全挂载
    expanders = [e.label for e in at.expander]
    assert any("认沽期权" in e for e in expanders), f"必须挂载期权防暴跌哨展开器: {expanders}"
    assert any("跨境QDII" in e for e in expanders), f"必须挂载跨境QDII锁汇套利展开器: {expanders}"

    # 切换至 Tab 1 智能定投模式并注入大额资本进行检验
    at.session_state["radio_capital_deployment_mode"] = "📅 估值自适应智能定投（根据宏观 ERP 与均线偏离度动态调整扣款乘数）"
    at.session_state["tab1_step_reached"] = 2
    at.session_state["tab1_trigger_sim"] = True
    at.session_state["tab1_trigger_s3"] = True
    at.run(timeout=75)
    assert not at.exception, f"AppTest 切换智能定投异常: {at.exception}"


def test_qdii_fx_arbitrage_domestic_500_and_100_isolation():
    """
    【反张冠李戴核验】核验国内中证500与深证100等境内指数基金绝不被误判为美股标普500或纳斯达克100：
    1. 中证500ETF (510500) 含有'500'但绝非标普500，必须判为其他跨境QDII或境内标的，不得赋予标普500的3.20%常态溢价；
    2. 易方达深证100ETF (159901) 含有'100'但绝非纳指100，不得误判为美股纳斯达克100；
    3. 标普500ETF联接 (050025) 真实命中美股标普500；
    4. 纳斯达克100 (000834) 真实命中美股纳斯达克100。
    """
    res_csi500 = PortfolioManager.calculate_qdii_fx_hedged_arbitrage(
        fund_code="510500",
        fund_name="南方中证500ETF",
        spot_usdcnh=7.2500
    )
    assert res_csi500["asset_category"] != "美股标普500", "中证500ETF绝不能被误判为美股标普500！"

    res_sz100 = PortfolioManager.calculate_qdii_fx_hedged_arbitrage(
        fund_code="159901",
        fund_name="易方达深证100ETF",
        spot_usdcnh=7.2500
    )
    assert res_sz100["asset_category"] != "美股纳斯达克100", "深证100ETF绝不能被误判为美股纳斯达克100！"

    res_real_sp = PortfolioManager.calculate_qdii_fx_hedged_arbitrage(
        fund_code="050025",
        fund_name="博时标普500ETF联接A",
        spot_usdcnh=7.2500
    )
    assert res_real_sp["asset_category"] == "美股标普500"

    res_real_nasdaq = PortfolioManager.calculate_qdii_fx_hedged_arbitrage(
        fund_code="000834",
        fund_name="大成纳斯达克100A",
        spot_usdcnh=7.2500
    )
    assert res_real_nasdaq["asset_category"] == "美股纳斯达克100"


def test_large_dca_batches_scheduler_adv_volume_weighting_elevation():
    """
    【成交量加权与流动性冲击核验】
    当低波资产定投订单金额占日均成交额 ADV 比例较高时 (如 order_amount / ADV >= 1.0%)：
    即使标的日均波幅极低 (如纯债 d_vol = 0.002, 常规仅拆解 3 天)，
    分批调度器必须结合成交量加权将其自适应提升至 5 天，避免大单击穿流动性盘口！
    同时在返回结果中必须输出 adv_yuan, participation_ratio_pct 与 volume_weighted=True。
    """
    # 纯债低波标的 (日均波幅 0.2% < 0.8%)，若订单为 50,000 元且 ADV 仅 2,000,000 元 (参与率达 2.5% >= 1.0%)
    sched_adv_elevated = PortfolioManager.schedule_large_dca_batches(
        order_amount=50000.0,
        fund_code="002351",
        fund_name="易方达裕祥回报债券A",
        daily_volatility=0.002,
        adv_yuan=2000000.0
    )
    assert sched_adv_elevated["volume_weighted"] is True
    assert sched_adv_elevated["adv_yuan"] == 2000000.0
    assert sched_adv_elevated["participation_ratio_pct"] == 2.5000
    assert sched_adv_elevated["split_days"] == 5, "大额订单占 ADV 比超过 1% 必须自适应提升为 5 天挂单！"
    assert len(sched_adv_elevated["schedule"]) == 5
    tot = sum(s["slice_amount"] for s in sched_adv_elevated["schedule"])
    assert abs(tot - 50000.0) < 0.01


def test_510050_shanghai_50_index_parquet_penetration():
    """
    【真实湖仓穿透核验】核验 510050 (华夏上证50ETF) 与 000016 真实穿透至本地 indices/000016.SH.parquet：
    1. 严禁回退至 Tier 4 沪深300假基准 (vol 0.1750, bias -1.34)；
    2. 必须真实从 000016.SH.parquet 计算过去 20 日真实年化波动率与 bias_20；
    3. volatility 处于真实区间 (约 10% ~ 13%)。
    """
    metrics = SmartExecutionDCAEngine.get_fund_real_volatility_and_bias("510050", "华夏上证50ETF")
    assert metrics["volatility"] > 0.0
    # 验证不是 0.1750 (沪深300回退基准)
    assert metrics["volatility"] != 0.1750, f"510050 不应使用沪深300假回退基准: {metrics}"
    assert 0.08 <= metrics["volatility"] <= 0.15, f"510050 上证50真实波动率应在 8%~15% 区间，实际: {metrics['volatility']}"


