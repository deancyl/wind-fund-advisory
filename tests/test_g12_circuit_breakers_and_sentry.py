# -*- coding: utf-8 -*-
"""
tests/test_g12_circuit_breakers_and_sentry.py
Milestone 1 专项测试：首屏与风控引擎四大代码断路 Bug 修复验证
1. Bug 1: 相关性突变预警指示卡断路修复与双保险别名键 (is_mutation_alarm / is_regime_shift_risk / is_triggered / is_liquidity_shift_triggered)
2. Bug 2: ActiveRiskSentry inspect_portfolio 参数穿透 (investor_risk_tier & fund_quotes) 激活维度 8 与维度 9
3. Bug 3: 指数与 ETF 联接基金盘中估值校准精度 (_apply_fund_valuation_calibration，0.95 联接仓位系数，季报滞后消除)
4. Bug 4: Tab 1 智能定投组合加权均线乖离率与 ERP 穿透 (compute_portfolio_weighted_bias_and_erp 标的对齐)
"""

import sys
import inspect
from pathlib import Path
from unittest.mock import patch
import pytest
import numpy as np

_CURRENT = Path(__file__).resolve().parent
_WORKSPACE = _CURRENT.parent
_AGY2_DIR = _WORKSPACE / "AGY2_FundAdvisory"
if str(_AGY2_DIR) not in sys.path:
    sys.path.insert(0, str(_AGY2_DIR))
if str(_WORKSPACE) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE))

from AGY2_FundAdvisory.portfolio_manager import (
    PortfolioManager,
    FundQuote,
    INDEX_AND_FEEDER_BENCHMARK_MAP,
    QDII_BENCHMARK_MAP,
    _apply_fund_valuation_calibration,
    _apply_qdii_valuation_correction,
    fetch_realtime_fund_quote,
    clear_realtime_cache,
)
from AGY2_FundAdvisory.advisory_engine import (
    ActiveRiskSentry,
    SmartExecutionDCAEngine,
)
from AGY2_FundAdvisory.app_gui import (
    render_correlation_mutation_card_html,
)


@pytest.fixture(autouse=True)
def reset_cache_before_each():
    clear_realtime_cache()
    yield
    clear_realtime_cache()


# =====================================================================
# 1. Bug 1: 动态相关性突变指示卡门禁与双保险别名字典测试
# =====================================================================

def test_bug1_correlation_mutation_alias_keys():
    """
    验证 PortfolioManager.evaluate_dynamic_correlation_mutation_instance
    同时返回原生键 (is_triggered, is_liquidity_shift_triggered)
    及防撞壁别名键 (is_mutation_alarm, is_regime_shift_risk)。
    """
    pm = PortfolioManager(db_path=":memory:")
    pm.add_or_update_holding("005561", shares=10000.0, nav=1.5, cost_price=1.4)
    pm.add_or_update_holding("011613", shares=20000.0, nav=0.8, cost_price=1.0)
    pm.add_or_update_holding("002351", shares=5000.0, nav=1.1, cost_price=1.1)

    # 1. 模拟突破 0.80 极端突变警戒线 (两项均触发)
    res_stress = pm.evaluate_dynamic_correlation_mutation_instance(
        threshold=0.75,
        stress_threshold=0.80,
        simulated_corr=0.82
    )
    assert res_stress["is_triggered"] is True
    assert res_stress["is_liquidity_shift_triggered"] is True
    assert res_stress["is_mutation_alarm"] is True
    assert res_stress["is_regime_shift_risk"] is True

    # 2. 模拟突破 0.75 普通预警线 (仅 is_triggered 触发)
    res_alert = pm.evaluate_dynamic_correlation_mutation_instance(
        threshold=0.75,
        stress_threshold=0.80,
        simulated_corr=0.76
    )
    assert res_alert["is_triggered"] is True
    assert res_alert["is_liquidity_shift_triggered"] is False
    assert res_alert["is_mutation_alarm"] is True
    assert res_alert["is_regime_shift_risk"] is False

    # 3. 模拟正常状态 0.40 (两项均不触发)
    res_normal = pm.evaluate_dynamic_correlation_mutation_instance(
        threshold=0.75,
        stress_threshold=0.80,
        simulated_corr=0.40
    )
    assert res_normal["is_triggered"] is False
    assert res_normal["is_liquidity_shift_triggered"] is False
    assert res_normal["is_mutation_alarm"] is False
    assert res_normal["is_regime_shift_risk"] is False


def test_bug1_app_gui_correlation_gate_source_and_render():
    """
    验证 app_gui.py 中的相关性卡片渲染门禁与 HTML 渲染输出
    """
    gui_file = _AGY2_DIR / "app_gui.py"
    gui_code = gui_file.read_text(encoding="utf-8")

    # 确保门禁包含 is_triggered 或 is_liquidity_shift_triggered
    assert 'corr_eval_res.get("is_triggered")' in gui_code
    assert 'corr_eval_res.get("is_liquidity_shift_triggered")' in gui_code

    # 验证渲染函数在触发时输出有效 HTML
    mock_triggered_res = {
        "is_triggered": True,
        "is_liquidity_shift_triggered": True,
        "current_correlation": 0.82,
        "downside_correlation": 0.85,
        "threshold": 0.75,
        "stress_threshold": 0.80,
        "status": "MUTATION_ALERT",
        "alert_level": "red",
        "original_weights": {"005561": 0.5, "011613": 0.5},
        "adjusted_weights": {"005561": 0.3, "011613": 0.3, "002351": 0.4},
        "cut_details": [{"code": "011613", "name": "华夏科创50", "orig_w": 50.0, "new_w": 30.0, "cut_pct": 20.0}],
        "total_cut_weight_pct": 40.0,
        "alert_title": "【极端预警】相关系数达 0.82",
        "alert_message": "触发流动性平移预案",
        "action": "定向削减高估值高波资产",
        "action_type": "correlation_mutation_defense",
        "action_plan": "LIQUIDITY_SHIFT_TO_BOND_AND_GOLD"
    }
    card_html = render_correlation_mutation_card_html(mock_triggered_res)
    assert card_html != ""
    assert "相关性" in card_html or "突变" in card_html or "0.82" in card_html


# =====================================================================
# 2. Bug 2: sentry.inspect_portfolio 投资者适当性与盘中异动安全垫传导
# =====================================================================

def test_bug2_sentry_dimension_8_suitability():
    """
    验证 ActiveRiskSentry 维度 8 (投资者适当性匹配与止损巡检):
    当传入 investor_risk_tier 时，检测实盘持仓权益比是否越界。
    C1 安稳保守型最高权益上限仅 20%。如果实盘配置 80% 权益标的，必须触发警告。
    """
    sentry = ActiveRiskSentry()

    # 构建高权益持仓：80% 科技成长股 (013841) + 20% 纯债 (002351)
    high_equity_holdings = {
        "013841": {
            "code": "013841",
            "name": "天弘中证芯片产业ETF联接C",
            "market_value": 80000.0,
            "shares": 80000.0,
            "cost_nav": 1.0,
            "current_nav": 1.0,
            "pnl_pct": 0.0,
            "category": "权益类"
        },
        "002351": {
            "code": "002351",
            "name": "招商产业债A",
            "market_value": 20000.0,
            "shares": 20000.0,
            "cost_nav": 1.0,
            "current_nav": 1.0,
            "pnl_pct": 0.0,
            "category": "固收类"
        }
    }

    # 1. C1 保守型账户：权益资产占比 80% 远超 C1 的 20% 上限，必须产生告警
    rep_c1 = sentry.inspect_portfolio(
        holdings=high_equity_holdings,
        snapshot={},
        investor_risk_tier="C1"
    )
    alerts_c1 = rep_c1.get("alerts", [])
    suitability_alerts_c1 = [a for a in alerts_c1 if "适当性" in str(a.get("dimension", "")) or "适当性" in str(a.get("title", "")) or "权益" in str(a.get("title", ""))]
    assert len(suitability_alerts_c1) >= 1, "C1 保守型账户超配 80% 权益资产必须触发适当性预警"
    desc_c1 = suitability_alerts_c1[0].get("desc", "")
    assert "80.0%" in desc_c1 or "超配" in desc_c1 or "超标" in desc_c1

    # 2. C5 极限进攻型账户：权益资产上限可达 95%，80% 属于合规区间，不应触发适当性超配预警
    rep_c5 = sentry.inspect_portfolio(
        holdings=high_equity_holdings,
        snapshot={},
        investor_risk_tier="C5"
    )
    alerts_c5 = rep_c5.get("alerts", [])
    suitability_alerts_c5 = [a for a in alerts_c5 if "适当性" in str(a.get("dimension", "")) or "适当性" in str(a.get("title", ""))]
    assert len(suitability_alerts_c5) == 0, "C5 进攻型账户 80% 权益不应触发适当性超配告警"


def test_bug2_sentry_dimension_9_intraday_cushion_transmission():
    """
    验证 ActiveRiskSentry 维度 9 (盘中实时估值异动与安全垫实时消耗传导):
    当 snapshot 注入持仓基金的 fund_quotes 且出现单基盘中跌幅 >= 2% 或组合整体下挫消耗安全垫时触发告警。
    """
    sentry = ActiveRiskSentry()

    holdings = {
        "013841": {
            "code": "013841",
            "name": "天弘中证芯片产业ETF联接C",
            "market_value": 50000.0,
            "shares": 50000.0,
            "cost_nav": 1.0,
            "current_nav": 1.1,
            "pnl_pct": 10.0,  # 浮盈安全垫约为 4545 元
            "category": "权益类"
        }
    }

    # 模拟盘中芯片大跌 -3.2%
    snapshot_with_quotes = {
        "fund_quotes": {
            "013841": FundQuote(
                name="天弘中证芯片产业ETF联接C",
                dwjz=1.1000,
                gsz=1.0648,
                gszzl=-3.20,
                gztime="2026-11-08 14:30",
                fund_code="013841"
            )
        },
        "cushion_yuan": 4545.0
    }

    rep = sentry.inspect_portfolio(
        holdings=holdings,
        snapshot=snapshot_with_quotes,
        investor_risk_tier="C3"
    )
    alerts = rep.get("alerts", [])
    d9_alerts = [a for a in alerts if "安全垫" in str(a.get("dimension", "")) or "盘中" in str(a.get("dimension", "")) or "安全垫" in str(a.get("title", ""))]
    assert len(d9_alerts) >= 1, "盘中单基暴跌 -3.2% 且消耗安全垫必须触发维度 9 预警"
    desc_d9 = d9_alerts[0].get("desc", "")
    assert "013841" in desc_d9 or "芯片" in desc_d9 or "安全垫" in desc_d9


def test_bug2_app_gui_source_code_penetration():
    """
    验证 app_gui.py 中已完整植入 investor_risk_tier 与 fund_quotes 的注入逻辑。
    """
    gui_file = _AGY2_DIR / "app_gui.py"
    gui_code = gui_file.read_text(encoding="utf-8")

    assert '_augmented_snapshot["fund_quotes"] = _f_quotes' in gui_code
    assert 'investor_risk_tier=_cur_tier' in gui_code


# =====================================================================
# 3. Bug 3: 指数与 ETF 联接基金盘中估值校准精度
# =====================================================================

def test_bug3_feeder_fund_095_calibration():
    """
    验证 ETF 联接基金（如 011613 华夏科创50联接）校准：
    锚定场内科创50 ETF (sh588000)，乘以 0.95 法规仓位系数进行纠偏。
    若场内 ETF 变动 -2.00%，联接基金校准后 gszzl 应为 -1.90% (-2.00 * 0.95)。
    """
    mock_index_quote = {
        "name": "科创50ETF",
        "point": 1.050,
        "change": -0.021,
        "change_pct": -2.00,
        "time_str": "14:30",
        "date_str": "2026-11-08"
    }

    q_in = FundQuote(
        name="华夏恒生科技/科创50ETF联接A",
        dwjz=1.0000,
        gsz=1.0000,
        gszzl=0.0,  # 天天基金盘中未更新或严重滞后为 0.0
        gztime="2026-11-08 14:30",
        fund_code="011613",
        valuation_corrected=False
    )

    with patch("AGY2_FundAdvisory.portfolio_manager.fetch_realtime_index_quote", return_value=mock_index_quote):
        q_out = _apply_fund_valuation_calibration(q_in)

    assert q_out.valuation_corrected is True
    # 验证 0.95 仓位系数折算: -2.00 * 0.95 = -1.90
    assert q_out.gszzl == -1.90
    assert q_out.gsz == round(1.0000 * (1.0 - 1.90 / 100.0), 4)
    assert "基准纠偏" in q_out.gztime


def test_bug3_pure_index_fund_100_calibration():
    """
    验证纯指数基金（如 100032 富国中证红利指数增强A）校准：
    锚定场内基准 (sh515080)，按 1.0 仓位系数进行全额映射校准。
    若基准上涨 +1.50%，纯指数基金校准后 gszzl 应为 +1.50%。
    """
    mock_index_quote = {
        "name": "中证红利ETF",
        "point": 1.250,
        "change": 0.018,
        "change_pct": 1.50,
        "time_str": "14:30",
        "date_str": "2026-11-08"
    }

    q_in = FundQuote(
        name="富国中证红利指数增强A",
        dwjz=1.0820,
        gsz=1.0820,
        gszzl=0.0,
        gztime="2026-11-08 14:30",
        fund_code="100032",
        valuation_corrected=False
    )

    with patch("AGY2_FundAdvisory.portfolio_manager.fetch_realtime_index_quote", return_value=mock_index_quote):
        q_out = _apply_fund_valuation_calibration(q_in)

    assert q_out.valuation_corrected is True
    assert q_out.gszzl == 1.50
    assert q_out.gsz == round(1.0820 * (1.0 + 1.50 / 100.0), 4)
    assert "基准纠偏" in q_out.gztime


def test_bug3_active_bond_fund_unaffected():
    """
    验证非指数/非联接纯债标的（如 002351 招商产业债A）绝不误触发指数校准
    """
    q_bond = FundQuote(
        name="招商产业债A",
        dwjz=1.5000,
        gsz=1.5000,
        gszzl=0.02,
        gztime="2026-11-08 14:30",
        fund_code="002351",
        valuation_corrected=False
    )
    q_out = _apply_fund_valuation_calibration(q_bond)
    assert q_out.valuation_corrected is False
    assert q_out.gszzl == 0.02


def test_bug3_qdii_boundary_backward_compatibility():
    """
    验证对既有 QDII 边界测试契约的 100% 兼容性：
    标普500 (050025) 偏差 <= 1.5% 不触发，偏差 > 1.5% 触发纠偏。
    """
    mock_bench = {"symbol": "sh513500", "change_pct": 0.0, "price": 1.50}

    with patch("AGY2_FundAdvisory.portfolio_manager.fetch_realtime_index_quote", return_value=mock_bench):
        # 偏差 1.50% (不触发)
        q_exact = FundQuote(
            name="博时标普500ETF联接A",
            dwjz=2.0000,
            gsz=2.0300,
            gszzl=1.50,
            gztime="2026-11-08 14:30",
            fund_code="050025",
            valuation_corrected=False
        )
        res_exact = _apply_fund_valuation_calibration(q_exact)
        assert res_exact.valuation_corrected is False

        # 偏差 1.5001% (严格触发)
        q_over = FundQuote(
            name="博时标普500ETF联接A",
            dwjz=2.0000,
            gsz=2.0301,
            gszzl=1.5001,
            gztime="2026-11-08 14:30",
            fund_code="050025",
            valuation_corrected=False
        )
        res_over = _apply_fund_valuation_calibration(q_over)
        assert res_over.valuation_corrected is True
        assert res_over.gszzl == 0.0


# =====================================================================
# 4. Bug 4: 智能定投组合加权均线乖离率与 ERP 穿透
# =====================================================================

def test_bug4_compute_portfolio_weighted_bias_and_erp():
    """
    验证 SmartExecutionDCAEngine.compute_portfolio_weighted_bias_and_erp
    准确计算持仓篮子各标的的加权乖离率与 ERP 分位数。
    """
    # 场景 1: 空建仓列表回退至宏观指标
    erp_empty, bias_empty = SmartExecutionDCAEngine.compute_portfolio_weighted_bias_and_erp(
        allocations=[],
        snapshot={"erp_percentile": 75.0, "c300_bias_20": 2.5}
    )
    assert erp_empty == 75.0
    assert bias_empty == 2.5

    # 场景 2: 50% 科创50 (高波超买 bias=+4.0%) + 50% 红利低波 (防御超卖 bias=-2.0%)
    allocations = [
        {"code": "011613", "name": "华夏科创50联接", "weight": 0.5, "bias_20": 4.0},
        {"code": "005561", "name": "易方达红利低波联接A", "weight": 0.5, "bias_20": -2.0}
    ]
    erp_w, bias_w = SmartExecutionDCAEngine.compute_portfolio_weighted_bias_and_erp(
        allocations=allocations,
        snapshot={"erp_percentile": 70.0}
    )
    # 期望加权 bias = 0.5 * 4.0 + 0.5 * (-2.0) = 1.00
    assert bias_w == 1.00
    # 科创50 ERP: 70 - 4.0 * 1.5 = 64.0; 红利低波 ERP: 70 - (-2.0) * 1.5 = 73.0; 加权 ERP = 68.5
    assert erp_w == 68.50

    # 场景 3: 100% 纯债资产对齐宏观中性 ERP
    alloc_bond = [{"code": "002351", "name": "招商产业债A", "weight": 1.0, "bias_20": 0.1}]
    erp_bond, bias_bond = SmartExecutionDCAEngine.compute_portfolio_weighted_bias_and_erp(
        allocations=alloc_bond,
        snapshot={"erp_percentile": 78.0}
    )
    assert erp_bond == 78.0
    assert bias_bond == 0.1


def test_bug4_app_gui_smart_dca_wiring():
    """
    验证 app_gui.py 中智能定投模式下已调用 compute_portfolio_weighted_bias_and_erp
    """
    gui_file = _AGY2_DIR / "app_gui.py"
    gui_code = gui_file.read_text(encoding="utf-8")
    assert 'SmartExecutionDCAEngine.compute_portfolio_weighted_bias_and_erp(' in gui_code
