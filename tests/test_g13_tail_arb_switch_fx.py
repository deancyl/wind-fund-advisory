"""
G13 世代专项自动化测试套件:
1. 场内 ETF 与场外联接基金 14:45 尾盘折溢价套利感知 (data_loader.py 与 advisory_engine.py)
2. 同基金公司内部免赎极速转换策略与摩擦节省精算 (portfolio_manager.py 与 app_gui.py)
3. QDII 与跨市场资产的实时离岸汇率 (USD/CNH) 波动穿透纠偏 (data_loader.py 与 advisory_engine.py)
4. ActiveRiskSentry 维度 10 同类基金管理人集中度与高波科技类行业暴露上限巡检 (advisory_engine.py)
5. GUI 静态契约与防作弊只读文件完整性核验
"""

import sys
import inspect
from pathlib import Path
import pytest

TEST_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TEST_DIR.parent
APP_DIR = PROJECT_ROOT / "AGY2_FundAdvisory"

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_loader import DataLoader
from advisory_engine import (
    calculate_fx_adjusted_intraday_valuation,
    generate_etf_feeder_arbitrage_advisory,
    ActiveRiskSentry
)
from portfolio_manager import PortfolioManager, FundHolding, HoldingBatch


def test_etf_feeder_arbitrage_sensors_and_thresholds():
    """
    核验场内 ETF 与场外联接 14:45 尾盘折溢价套利感知引擎：
    1. 覆盖黄金、沪深300、科创50、芯片、标普500、恒生科技等核心 ETF/联接对；
    2. 折溢价率公式真实准确：((price - iopv) / iopv) * 100%；
    3. 溢价 > +1.0% 输出 PREMIUM_BUY_FEEDER；
    4. 折价 < -1.0% 输出 DISCOUNT_BUY_ETF；
    5. 平价区间 [-1.0%, +1.0%] 输出 NEUTRAL。
    """
    sensors = DataLoader.fetch_etf_feeder_arbitrage_sensors(use_cache=False)
    assert len(sensors) >= 6, f"核心 ETF 套利对至少覆盖 6 组，当前: {len(sensors)}"

    pairs_found = {s["etf_code"]: s for s in sensors}
    assert "518880" in pairs_found, "必须覆盖华安黄金ETF (518880)"
    assert "510300" in pairs_found, "必须覆盖华泰柏瑞沪深300ETF (510300)"
    assert "588000" in pairs_found, "必须覆盖华夏科创50ETF (588000)"
    assert "512760" in pairs_found, "必须覆盖国泰半导体芯片ETF (512760)"

    for s in sensors:
        price = s["etf_price"]
        iopv = s["etf_iopv"]
        expected_diff = round(((price - iopv) / iopv) * 100.0, 2)
        assert abs(s["discount_premium_pct"] - expected_diff) < 0.05, f"折溢价率不匹配: {s}"

        if s["discount_premium_pct"] > 1.0:
            assert s["signal"] == "PREMIUM_BUY_FEEDER"
            assert "场外" in s["action_advice"] or "联接" in s["action_advice"]
        elif s["discount_premium_pct"] < -1.0:
            assert s["signal"] == "DISCOUNT_BUY_ETF"
            assert "场内" in s["action_advice"]
        else:
            assert s["signal"] == "NEUTRAL"


def test_etf_feeder_arbitrage_advisory_generation():
    """
    核验 advisory_engine.generate_etf_feeder_arbitrage_advisory:
    持有联接基金且场内深折价时，提示场内低吸置换；
    持有场内 ETF 且场内高溢价时，提示场外平价申购套利。
    """
    mock_sensor_discount = [{
        "name": "科创50",
        "etf_code": "588000",
        "etf_name": "华夏科创50ETF",
        "feeder_code": "011612",
        "feeder_name": "华夏科创50联接A",
        "etf_price": 0.980,
        "etf_iopv": 1.000,
        "discount_premium_pct": -2.00,
        "signal": "DISCOUNT_BUY_ETF",
        "action_advice": "场内深度折价 -2.00%，建议卖出场外联接并在场内以折价低吸华夏科创50ETF (588000)。"
    }]

    adv_res = generate_etf_feeder_arbitrage_advisory(
        current_holdings={"011612": {"market_value": 50000.0, "fund_name": "华夏科创50联接A"}},
        arbitrage_sensors=mock_sensor_discount
    )
    assert adv_res["has_arbitrage_opportunity"] is True
    assert len(adv_res["proposals"]) >= 1
    prop = adv_res["proposals"][0]
    assert prop["arbitrage_type"] == "DISCOUNT_BUY_ETF"
    assert prop["expected_spread_bps"] == 200.0


def test_realtime_usdcnh_fx_and_qdii_valuation_correction():
    """
    核验实时离岸人民币 (USD/CNH) 汇率采集与 QDII/黄金/半导体资产盘中估值纠偏引擎：
    1. DataLoader.fetch_realtime_usdcnh_fx 返回 rate > 6.0 且包含 change_pct；
    2. 美股 QDII、黄金、全球半导体依据复合收益率公式严密纠偏：
       (1 + r_asset) * (1 + r_fx) - 1；
    3. 纯境内债券/A股不涉外标的自动免疫汇率波动。
    """
    fx_info = DataLoader.fetch_realtime_usdcnh_fx(use_cache=False)
    assert fx_info["rate"] > 6.0, f"汇率点位异常: {fx_info['rate']}"
    assert "change_pct" in fx_info

    macro_ind = DataLoader.fetch_macro_cross_market_indicators()
    assert "usdcnh_rate" in macro_ind
    assert "usdcnh_summary" in macro_ind
    assert "USD/CNH" in macro_ind["usdcnh_summary"] or "离岸人民币" in macro_ind["usdcnh_summary"]

    # 1. 模拟美股 QDII (050025 标普500) 原币估值 +1.00%，USD/CNH 升值 +0.50%
    qdii_res = calculate_fx_adjusted_intraday_valuation(
        fund_code="050025",
        fund_name="博时标普500ETF联接A",
        raw_valuation_pct=1.00,
        usdcnh_change_pct=0.50
    )
    assert qdii_res["is_applicable"] is True
    # (1 + 0.01) * (1 + 0.005) - 1 = 1.01505 - 1 = +1.505% -> round 1.51%
    assert abs(qdii_res["corrected_pct"] - 1.51) <= 0.02
    assert qdii_res["fx_drift_bps"] > 0

    # 2. 模拟黄金 (000216 华安黄金联接)
    gold_res = calculate_fx_adjusted_intraday_valuation(
        fund_code="000216",
        fund_name="华安黄金ETF联接A",
        raw_valuation_pct=0.80,
        usdcnh_change_pct=-0.40
    )
    assert gold_res["is_applicable"] is True
    # (1 + 0.008) * (1 - 0.004) - 1 = 1.003968 - 1 = +0.40%
    assert abs(gold_res["corrected_pct"] - 0.40) <= 0.02
    assert gold_res["fx_drift_bps"] < 0

    # 3. 普通纯债基金 (002351 易方达裕祥回报债券A)
    bond_res = calculate_fx_adjusted_intraday_valuation(
        fund_code="002351",
        fund_name="易方达裕祥回报债券A",
        raw_valuation_pct=0.05,
        usdcnh_change_pct=0.50
    )
    assert bond_res["is_applicable"] is False
    assert bond_res["corrected_pct"] == 0.05
    assert bond_res["fx_drift_bps"] == 0.0


def test_same_company_conversion_optimizer_and_friction_savings():
    """
    核验同基金公司内部免赎极速转换优化器与资金摩擦节省精算：
    1. 识别相同基金公司（易方达、华夏、广发等）之间的卖出转买入路由；
    2. 精算免除 3.5 天在途闲置资金成本 (年化 2.0% 无风险利率) 与再申购费 (0.12%)；
    3. 数学模型分厘平账并计算 saved_bps。
    """
    pm = PortfolioManager()
    pm.available_cash = 1000.0

    # 构建易方达同公司旗下两只产品：减仓易方达中小盘/消费，增配易方达裕祥回报纯债
    pm.holdings = {
        "110011": FundHolding(
            fund_code="110011",
            fund_name="易方达中小盘混合",
            shares=10000.0,
            cost_nav=2.0,
            current_nav=2.0,
            market_value=20000.0,
            share_class="A",
            company="易方达基金",
            batches=[HoldingBatch("b1", "2025-01-01", 10000.0, 2.0, holding_days=180)]
        ),
        "002351": FundHolding(
            fund_code="002351",
            fund_name="易方达裕祥回报债券A",
            shares=2000.0,
            cost_nav=1.5,
            current_nav=1.5,
            market_value=3000.0,
            share_class="A",
            company="易方达基金",
            batches=[HoldingBatch("b2", "2025-06-01", 2000.0, 1.5, holding_days=90)]
        )
    }
    pm._recalculate_totals()

    # 目标：易方达裕祥回报权重提升，易方达中小盘权重归零
    target_weights = {
        "002351": 0.85,
        "110011": 0.0
    }

    conv_res = pm.optimize_same_company_conversions(target_weights=target_weights)
    assert conv_res["has_conversions"] is True, "必须成功匹配易方达同公司内部转换"
    assert len(conv_res["conversions"]) >= 1

    c_item = conv_res["conversions"][0]
    assert c_item["from_code"] == "110011"
    assert c_item["to_code"] == "002351"
    assert "易方达" in c_item["company"]

    switch_amt = c_item["switch_amount"]
    assert switch_amt > 0

    # 验证免除费用与资金成本精算
    exp_repurchase_fee = round(switch_amt * 0.0012, 2)
    exp_cap_cost = round(switch_amt * 0.02 * (3.5 / 365.0), 2)
    exp_tot_saved = round(exp_repurchase_fee + exp_cap_cost, 2)
    exp_bps = round(exp_tot_saved / switch_amt * 10000.0, 2)

    assert abs(c_item["saved_repurchase_fee"] - exp_repurchase_fee) <= 0.02
    assert abs(c_item["saved_capital_cost"] - exp_cap_cost) <= 0.02
    assert abs(c_item["total_saved_yuan"] - exp_tot_saved) <= 0.02
    assert abs(c_item["saved_bps"] - exp_bps) <= 0.05
    assert conv_res["total_saved_yuan"] == exp_tot_saved


def test_active_risk_sentry_dimension_10_manager_and_tech_limits():
    """
    核验 ActiveRiskSentry 维度 10 同类基金管理人集中度与高波科技类行业暴露上限监控：
    1. 单一基金公司（如华夏基金）持仓市值穿透占比 > 35% 时触发黄色预警并给出平衡平移方案；
    2. 高波科技成长行业（半导体芯片、科创50等）暴露占比 > 35% 时触发黄色预警并给出平移方案；
    3. 均衡配置时巡检全通，不虚假报警。
    """
    sentry = ActiveRiskSentry()

    # 场景 A: 华夏基金旗下产品过载，占比达 60%
    holdings_manager_heavy = [
        {"fund_code": "011612", "fund_name": "华夏科创50联接A", "market_value": 30000.0, "holding_days": 60, "share_class": "A"},
        {"fund_code": "008888", "fund_name": "华夏半导体芯片ETF联接A", "market_value": 30000.0, "holding_days": 60, "share_class": "A"},
        {"fund_code": "002351", "fund_name": "易方达裕祥回报债券A", "market_value": 40000.0, "holding_days": 90, "share_class": "A"},
    ]
    rep_manager = sentry.inspect_portfolio(holdings_manager_heavy)
    manager_alerts = [a for a in rep_manager.get("alerts", []) if a.get("action_type") == "rebalance_manager_concentration"]
    assert len(manager_alerts) >= 1, "华夏基金占比 60% > 35%，必须触发管理人集中度预警"
    assert "华夏" in manager_alerts[0]["desc"]
    assert manager_alerts[0]["level"] == "yellow"

    # 场景 B: 高波科技行业暴露达 60%
    sector_alerts = [a for a in rep_manager.get("alerts", []) if a.get("action_type") == "rebalance_sector_exposure"]
    assert len(sector_alerts) >= 1, "半导体与科创50合计 60% > 35%，必须触发高波科技敞口预警"
    assert "科技" in sector_alerts[0]["title"] or "半导体" in sector_alerts[0]["desc"]

    # 场景 C: 均衡配置，各基金公司占比 25% < 35%，单一行业 < 35%
    holdings_balanced = [
        {"fund_code": "002351", "fund_name": "易方达裕祥回报债券A", "market_value": 25000.0, "holding_days": 90, "share_class": "A"},
        {"fund_code": "510300", "fund_name": "华泰柏瑞沪深300ETF", "market_value": 25000.0, "holding_days": 90, "share_class": "A"},
        {"fund_code": "000216", "fund_name": "华安黄金ETF联接A", "market_value": 25000.0, "holding_days": 90, "share_class": "A"},
        {"fund_code": "005561", "fund_name": "广发创业板ETF联接A", "market_value": 25000.0, "holding_days": 90, "share_class": "A"},
    ]
    rep_balanced = sentry.inspect_portfolio(holdings_balanced)
    dim10_alerts = [a for a in rep_balanced.get("alerts", []) if a.get("action_type") in ("rebalance_manager_concentration", "rebalance_sector_exposure")]
    assert len(dim10_alerts) == 0, f"均衡配置下维度 10 不应误报，实际预警: {dim10_alerts}"


def test_anti_cheat_contract_and_readonly_files_integrity():
    """
    反作弊契约与只读裁判文件硬约束：
    1. 严禁修改 judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py；
    2. 严禁修改 DataLoader.simulate_execution 的默认签名与默认扣费逻辑；
    3. data/ledgers_index.json 仅保留主实盘账本 (main_live)。
    """
    import subprocess
    diff_res = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True
    )
    modified_files = [f.strip().replace("\\", "/") for f in diff_res.stdout.strip().splitlines() if f.strip()]

    FORBIDDEN_FILES = [
        "judge_engine.py",
        "holdout_vault.py",
        "AGENT_SPEC.md",
        "tests/test_infra.py"
    ]
    for forbidden in FORBIDDEN_FILES:
        assert not any(forbidden in mf for mf in modified_files), f"只读裁判文件绝对禁止修改: {forbidden}"

    # 核验 DataLoader.simulate_execution 默认签名
    sig = inspect.signature(DataLoader.simulate_execution)
    params = list(sig.parameters.keys())
    expected_params = ['weights_df', 'prices_df', 'is_otc', 'penalty_days', 'penalty_rate', 'etf_impact']
    assert params == expected_params, f"simulate_execution signature mismatch! Got {params}"
    assert sig.parameters['penalty_days'].default == 7
    assert sig.parameters['penalty_rate'].default == 0.015
    assert sig.parameters['etf_impact'].default == 0.001
    assert sig.parameters['is_otc'].default is True

    # 核验 data/ledgers_index.json 仅保留主账本
    import json
    ledgers_index_file = PROJECT_ROOT / "data" / "ledgers_index.json"
    if ledgers_index_file.exists():
        with open(ledgers_index_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        ledgers = data.get("ledgers", [])
        assert len(ledgers) == 1, f"ledgers_index.json 必须仅保留 1 个主实盘账本，当前: {len(ledgers)}"
        lid = ledgers[0].get("id") or ledgers[0].get("ledger_id")
        assert lid == "main_live", f"主账本 ID 必须为 main_live: {ledgers[0]}"


def test_resolve_fund_meta_dual_invocation_and_company_normalization():
    """
    核验 PortfolioManager.resolve_fund_meta 双模式调用与同公司后缀归一化：
    1. 支持类方法调用 PortfolioManager.resolve_fund_meta(code)；
    2. 支持实例方法调用 pm.resolve_fund_meta(code)；
    3. PortfolioManager.is_same_company 正确归一化公司名称后缀。
    """
    pm = PortfolioManager()
    meta_class = PortfolioManager.resolve_fund_meta("011612")
    meta_inst = pm.resolve_fund_meta("011612")

    assert meta_class["code"] == "011612"
    assert "华夏" in meta_class["company"]
    assert meta_inst["code"] == "011612"
    assert meta_inst["company"] == meta_class["company"]

    # 归一化测试
    assert PortfolioManager.is_same_company("华夏", "华夏基金") is True
    assert PortfolioManager.is_same_company("易方达基金管理有限公司", "易方达") is True
    assert PortfolioManager.is_same_company("广发基金", "广发") is True
    assert PortfolioManager.is_same_company("华夏", "易方达") is False
    assert PortfolioManager.is_same_company("", "华夏") is False


def test_arbitrage_advisory_result_dict_protocol_and_in_operator():
    """
    核验 ArbitrageAdvisoryResult 支持字典协议与 'in' 成员运算符：
    1. 'has_arbitrage_opportunity' in res 为 True；
    2. 'proposals' in res 为 True；
    3. 不存在的 key 返回 False；
    4. 兼具列表与字典双向访问能力。
    """
    mock_sensor = [{
        "name": "黄金",
        "etf_code": "518880",
        "etf_name": "华安黄金ETF",
        "feeder_code": "000216",
        "feeder_name": "华安黄金ETF联接A",
        "etf_price": 5.50,
        "etf_iopv": 5.40,
        "discount_premium_pct": 1.85,
        "signal": "PREMIUM_BUY_FEEDER",
        "action_advice": "场内高溢价 +1.85%，建议在场外申购华安黄金ETF联接A (000216)。"
    }]
    res = generate_etf_feeder_arbitrage_advisory(
        current_holdings={"518880": {"market_value": 20000.0, "fund_name": "华安黄金ETF"}},
        arbitrage_sensors=mock_sensor
    )
    # 测试 'in' 运算符
    assert "has_arbitrage_opportunity" in res, "必须支持 'in' 检查 has_arbitrage_opportunity"
    assert "proposals" in res, "必须支持 'in' 检查 proposals"
    assert "invalid_key_xyz" not in res, "未定义键必须返回 False"
    assert res["has_arbitrage_opportunity"] is True
    assert len(res) == 1
    assert res[0]["etf_code"] == "518880"


def test_active_risk_sentry_company_resolution_without_keyword_in_name():
    """
    核验即使基金名称不包含基金公司字眼，ActiveRiskSentry 也能通过 resolve_fund_meta 
    准确识别基金所属公司，并触发集中度预警与填充完整的 fund_code 和 transfer 建议：
    """
    sentry = ActiveRiskSentry()
    holdings_no_keyword_names = [
        {"fund_code": "011612", "fund_name": "科创50ETF联接A", "market_value": 45000.0, "holding_days": 60, "share_class": "A"},
        {"fund_code": "008888", "fund_name": "半导体芯片ETF联接A", "market_value": 45000.0, "holding_days": 60, "share_class": "A"},
        {"fund_code": "002351", "fund_name": "裕祥回报债券A", "market_value": 10000.0, "holding_days": 90, "share_class": "A"},
    ]
    rep = sentry.inspect_portfolio(holdings_no_keyword_names)
    mgr_alerts = [a for a in rep.get("alerts", []) if a.get("action_type") == "rebalance_manager_concentration"]
    assert len(mgr_alerts) >= 1, "011612与008888均属于华夏，合计90%，必须穿透代码成功报警"
    alert = mgr_alerts[0]
    assert alert["fund_code"] in ("011612", "008888"), f"预警中的 fund_code 必须填充具体代码，不能为 '': {alert}"
    assert alert["target_shield_code"] == "002351"
    assert alert["excess_amount"] > 0
    assert alert["take_profit_ratio"] > 0

