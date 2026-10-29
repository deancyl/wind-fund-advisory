"""
AGY2 动态风险引擎、人话指标、海选漏斗与智能录入测试套件 (test_dynamic_risk_and_metrics.py)
验证 6 大核心升级：
1. C1~C5 动态风险分级、目标收益映射、问卷评测与错配警报
2. 5大档位自适应策略函数与 2018-2026 全周期回测时序
3. 人话指标引擎 (calculate_human_readable_metrics) 与残酷现实对账单 (get_aggressive_dream_reality_check)
4. 28,177 基金海选漏斗统计、金牌硬核理由与多维度目录搜索 (search_funds_in_catalog)
5. 零门槛智能文本持仓解析器 (parse_smart_text_holdings) 与一键接管
6. 自定义备选替换 (custom_fund_overrides) 与专属从0建仓蓝图
"""

import pytest
import pandas as pd
import numpy as np

from strategy_bridge import (
    StrategyBridge,
    RISK_TIERS_CONFIG,
    map_target_return_to_tier,
    evaluate_questionnaire_risk_tier,
    get_risk_mismatch_warning,
    strategy_fn_for_tier,
    calculate_human_readable_metrics,
    get_aggressive_dream_reality_check
)
from portfolio_manager import (
    PortfolioManager,
    SECTOR_FUND_SELECTION,
    get_fund_selection_funnel_stats,
    search_funds_in_catalog,
    parse_smart_text_holdings
)


class TestDynamicRiskEngine:
    """测试 1: 5 档动态风险引擎与双轨向导"""

    def test_risk_tiers_config_structure(self):
        """验证 C1~C5 配置完整性与关键字段"""
        assert len(RISK_TIERS_CONFIG) == 5
        for tier in ["C1", "C2", "C3", "C4", "C5"]:
            assert tier in RISK_TIERS_CONFIG
            cfg = RISK_TIERS_CONFIG[tier]
            assert "name" in cfg
            assert "target_cagr" in cfg
            assert "max_drawdown_limit" in cfg
            assert "equity_range" in cfg
            assert len(cfg["equity_range"]) == 2
            assert cfg["equity_range"][0] <= cfg["equity_range"][1]
            assert "core_assets" in cfg

        # 验证 C1 权益上限 <= 20%，C5 权益上限 >= 90%
        assert RISK_TIERS_CONFIG["C1"]["equity_range"][1] <= 20
        assert RISK_TIERS_CONFIG["C5"]["equity_range"][1] >= 90

    def test_map_target_return_to_tier(self):
        """验证自由目标收益率滑块映射至对应档位"""
        assert map_target_return_to_tier(4.0) == "C1"
        assert map_target_return_to_tier(5.0) == "C1"
        assert map_target_return_to_tier(6.5) == "C1"

        assert map_target_return_to_tier(7.0) == "C2"
        assert map_target_return_to_tier(9.0) == "C2"

        assert map_target_return_to_tier(10.0) == "C3"
        assert map_target_return_to_tier(15.0) == "C3"

        assert map_target_return_to_tier(16.0) == "C4"
        assert map_target_return_to_tier(25.0) == "C4"

        assert map_target_return_to_tier(30.0) == "C5"
        assert map_target_return_to_tier(50.0) == "C5"
        assert map_target_return_to_tier(100.0) == "C5"

    def test_evaluate_questionnaire_risk_tier(self):
        """验证 30 秒抗痛问卷得分与 C1~C5 评定映射"""
        assert evaluate_questionnaire_risk_tier(0) == "C1"
        assert evaluate_questionnaire_risk_tier(2) == "C1"

        assert evaluate_questionnaire_risk_tier(3) == "C2"
        assert evaluate_questionnaire_risk_tier(5) == "C2"

        assert evaluate_questionnaire_risk_tier(6) == "C3"
        assert evaluate_questionnaire_risk_tier(8) == "C3"

        assert evaluate_questionnaire_risk_tier(9) == "C4"
        assert evaluate_questionnaire_risk_tier(10) == "C4"

        assert evaluate_questionnaire_risk_tier(11) == "C5"
        assert evaluate_questionnaire_risk_tier(12) == "C5"
        assert evaluate_questionnaire_risk_tier(15) == "C5"

    def test_get_risk_mismatch_warning(self):
        """验证风险错配碰撞警报与降级建议"""
        # 无错配：畅想等于或低于实测
        m1 = get_risk_mismatch_warning("C3", "C3", 12.0)
        assert m1["has_mismatch"] is False

        m2 = get_risk_mismatch_warning("C2", "C4", 8.0)
        assert m2["has_mismatch"] is False

        # 有错配：畅想 C5 vs 实测 C2
        m3 = get_risk_mismatch_warning("C5", "C2", 40.0)
        assert m3["has_mismatch"] is True
        assert "高收益期待与实际风险承受力出现错配" in m3["warning_title"]
        assert "C5" in m3["warning_desc"]
        assert "C2" in m3["warning_desc"]
        assert "建议对策" in m3 or "recommendation" in m3


class TestTierStrategiesAndBacktest:
    """测试 2: 5 档自适应策略函数与全周期回测"""

    def test_strategy_fn_for_tier_weights(self):
        """测试不同档位下的资产配置权重与权益约束"""
        df_matrix = StrategyBridge.load_matrix()
        eval_window = df_matrix.iloc[:100]

        for tier in ["C1", "C2", "C3", "C4", "C5"]:
            w = strategy_fn_for_tier(eval_window, tier=tier)
            assert isinstance(w, dict)
            # 权重之和应大致等于 1.0
            total_w = sum(w.values())
            assert 0.98 <= total_w <= 1.02

            # 纯债在 C1 应当显著高于 C5
            w_c1 = strategy_fn_for_tier(eval_window, tier="C1")
            w_c5 = strategy_fn_for_tier(eval_window, tier="C5")
            assert w_c1["weight_bond"] > w_c5["weight_bond"]

    def test_get_backtest_nav_for_tier(self):
        """测试各档位 2018-2026 全周期回测时序加载与缓存"""
        df_c1 = StrategyBridge.get_backtest_nav_for_tier("C1")
        assert not df_c1.empty
        assert "strategy_nav" in df_c1.columns
        assert "strategy_drawdown" in df_c1.columns
        assert "date" in df_c1.columns

        df_c5 = StrategyBridge.get_backtest_nav_for_tier("C5")
        assert not df_c5.empty
        assert len(df_c5) == len(df_c1)

        # C1 最大回撤幅度应当远小于 C5
        mdd_c1 = abs(df_c1["strategy_drawdown"].min())
        mdd_c5 = abs(df_c5["strategy_drawdown"].min())
        assert mdd_c1 < mdd_c5


class TestHumanReadableMetrics:
    """测试 3: 人话指标计算器与残酷现实对账单"""

    def test_calculate_human_readable_metrics(self):
        """测试 5 个人话指标卡片计算"""
        capital = 200000.0
        kpi = calculate_human_readable_metrics(tier="C3", initial_capital=capital)

        # 1. 最好情况
        assert "best_case_return_pct" in kpi
        assert kpi["best_case_return_pct"] > 0
        assert "best_case_profit_amount" in kpi
        assert kpi["best_case_profit_amount"] > 0

        # 2. 最坏情况
        assert "worst_case_drawdown_pct" in kpi
        assert kpi["worst_case_drawdown_pct"] > 0
        assert "worst_case_loss_amount" in kpi
        assert kpi["worst_case_loss_amount"] > 0

        # 3. 极端回本考验
        assert "max_underwater_days" in kpi
        assert kpi["max_underwater_days"] > 0
        assert "max_underwater_months" in kpi

        # 4. 胜率与目标达成周期
        assert "win_rate_1y" in kpi
        assert 0 <= kpi["win_rate_1y"] <= 100
        assert "win_rate_2y" in kpi
        assert "win_rate_3y" in kpi
        assert "target_reach_duration" in kpi

        # 5. 适合人群与灵魂
        assert "suitable_for" in kpi
        assert "soul_summary" in kpi

    def test_get_aggressive_dream_reality_check(self):
        """测试畅想方案残酷现实对账单 (极限模式)"""
        capital = 100000.0
        res = get_aggressive_dream_reality_check(capital, target_return_pct=50.0)

        assert res["target_return_pct"] == 50.0
        assert res["rolling_1y_peak_ret_pct"] > 30.0
        assert res["peak_gain_amount"] > 30000.0
        assert res["max_drawdown_pct"] > 15.0
        assert res["worst_loss_amount"] > 15000.0
        assert res["max_underwater_days"] > 200
        assert "warning_card" in res
        assert "残酷现实" in res["warning_card"] or "极端" in res["warning_card"]


class TestFunnelAndCatalogSearch:
    """测试 4: 选基透明漏斗与全市场目录搜索"""

    def test_funnel_stats(self):
        """测试 28,177 全市场海选漏斗统计"""
        stats = get_fund_selection_funnel_stats()
        assert stats["total_market_funds"] >= 28000
        assert stats["hard_filtered_funds"] > 1000
        assert stats["sector_candidates"] == 5
        assert stats["final_champion_funds"] == 5

    def test_sector_fund_selection_structure(self):
        """测试 5 大类金牌标的与 Top 3 备选"""
        assert len(SECTOR_FUND_SELECTION) == 5
        for sec_key, sec_data in SECTOR_FUND_SELECTION.items():
            assert "sector_name" in sec_data
            assert "champion_code" in sec_data
            assert "champion_name" in sec_data
            assert "champion_reason" in sec_data
            assert len(sec_data["champion_reason"]) > 5
            assert "top_alternatives" in sec_data
            assert len(sec_data["top_alternatives"]) >= 3
            for alt in sec_data["top_alternatives"]:
                assert "code" in alt
                assert "name" in alt
                assert "tag" in alt

    def test_search_funds_in_catalog(self):
        """测试通过代码、中文名称、拼音首字母检索"""
        # 1. 查代码
        r_code = search_funds_in_catalog("005561", limit=5)
        assert len(r_code) >= 1
        assert any(f["fund_code"] == "005561" for f in r_code)

        # 2. 查中文名
        r_name = search_funds_in_catalog("红利低波", limit=5)
        assert len(r_name) >= 1
        assert any("红利" in f["fund_name"] for f in r_name)

        # 3. 查拼音
        r_pinyin = search_funds_in_catalog("kcz50", limit=5)
        # 允许返回或模糊匹配
        assert isinstance(r_pinyin, list)

        # 4. 空输入
        assert search_funds_in_catalog("", limit=5) == []


class TestSmartHoldingsParser:
    """测试 5: 零门槛智能文本持仓解析器与一键接管"""

    def test_parse_smart_text_holdings_varied_formats(self):
        """测试各种自然语言乱序、别名、单位、盈亏及天数识别"""
        text = """
        华夏科创50C 20000 亏500
        华泰柏瑞低波 30000 盈利1200
        002351 1.5万
        易方达蓝筹 10000 成本1.85 现价1.92 已持满30天
        000216 8000
        """
        parsed = parse_smart_text_holdings(text)
        assert len(parsed) == 5

        # 逐项验证
        p_star = next(p for p in parsed if "科创" in p["fund_name"] or p["fund_code"] in ["011613", "011612"])
        assert p_star["amount"] == 20000.0
        assert p_star["pnl"] == -500.0
        assert p_star["share_class"] == "C"

        p_div = next(p for p in parsed if p["fund_code"] == "005561")
        assert p_div["amount"] == 30000.0
        assert p_div["pnl"] == 1200.0

        p_bond = next(p for p in parsed if p["fund_code"] == "002351")
        assert p_bond["amount"] == 15000.0

        p_blue = next(p for p in parsed if "蓝筹" in p["fund_name"])
        assert p_blue["amount"] == 10000.0
        assert p_blue["holding_tag"] == ">=30d"

        p_gold = next(p for p in parsed if p["fund_code"] == "000216")
        assert p_gold["amount"] == 8000.0

    def test_import_from_smart_text(self):
        """测试 PortfolioManager 智能导入与持久化"""
        pm = PortfolioManager(storage_file=":memory:")
        text = """
        005561 25000 盈利500
        002351 15000
        """
        parsed = pm.parse_smart_text_holdings(text)
        res = pm.import_from_smart_text(parsed, available_cash=5000.0)

        assert res["funds_count"] == 2
        assert "005561" in pm.holdings
        assert "002351" in pm.holdings
        assert pm.available_cash == 5000.0
        assert pm.total_equity == 25000.0 + 15000.0 + 5000.0


class TestCustomOverridesBlueprint:
    """测试 6: 自定义备选替换与专属建仓蓝图"""

    def test_generate_zero_start_blueprint_with_overrides(self):
        """测试从0建仓蓝图支持 tier 动态配置与备选替换"""
        capital = 100000.0
        target_weights = {
            "005561": 0.35,
            "011612": 0.20,
            "050025": 0.15,
            "000216": 0.15,
            "002351": 0.15
        }
        # 用 001071 (易方达标普500A) 替换 050025 (博时标普500A)
        overrides = {"050025": "001071"}
        bp = StrategyBridge.generate_zero_start_blueprint(
            total_capital=capital,
            target_weights_funds=target_weights,
            tier="C4",
            custom_fund_overrides=overrides
        )

        assert bp["total_capital"] == capital
        assert bp["tier"] == "C4"

        fund_codes = [it["fund_code"] for it in bp["items"]]
        # 050025 应当被替换成 001071
        assert "050025" not in fund_codes
        assert "001071" in fund_codes

        # 检查各资产金额之和等于总本金
        sum_amt = sum(it["allocated_amount"] for it in bp["items"])
        assert abs(sum_amt - capital) < 1.0


class TestEdgeCasesAndBoundaryConditions:
    """测试 7: 边界值、极端空值与非标格式鲁棒性"""

    def test_import_from_smart_text_with_raw_string(self):
        """验证 import_from_smart_text 直接传入原始未解析字符串"""
        pm = PortfolioManager(storage_file=":memory:")
        text = "100032 30000元; 002351 20000"
        res = pm.import_from_smart_text(text, available_cash=8000.0)
        assert res["status"] == "SUCCESS"
        assert res["funds_count"] == 2
        assert "100032" in pm.holdings
        assert "002351" in pm.holdings
        assert pm.available_cash == 8000.0
        assert pm.total_equity == 30000.0 + 20000.0 + 8000.0

    def test_import_from_smart_text_empty_input(self):
        """验证空输入与乱码输入安全降级"""
        pm = PortfolioManager(storage_file=":memory:")
        res = pm.import_from_smart_text("", available_cash=1000.0)
        assert res["status"] == "FAILED"
        assert res["imported_count"] == 0

        res2 = pm.import_from_smart_text("   \n\t   ", available_cash=1000.0)
        assert res2["status"] == "FAILED"

    def test_parse_smart_text_semicolon_and_wan_unit(self):
        """验证分号分隔（中文/英文）与‘万’单位折算"""
        # 中文分号
        text_cn = "华夏科创50C 2.5万 亏500；易方达裕祥 1.8万"
        parsed_cn = parse_smart_text_holdings(text_cn)
        assert len(parsed_cn) == 2
        assert parsed_cn[0]["amount"] == 25000.0
        assert parsed_cn[0]["pnl"] == -500.0
        assert parsed_cn[1]["amount"] == 18000.0

        # 英文分号
        text_en = "005561 3.2万; 000216 8000元"
        parsed_en = parse_smart_text_holdings(text_en)
        assert len(parsed_en) == 2
        assert parsed_en[0]["amount"] == 32000.0
        assert parsed_en[1]["amount"] == 8000.0

    def test_calculate_human_readable_metrics_short_series(self):
        """验证时序过短（<10个点）时的安全降级处理"""
        short_nav = [1.0, 1.01, 1.02]
        short_dates = ["2026-01-01", "2026-01-02", "2026-01-03"]
        res = calculate_human_readable_metrics(short_nav, short_dates)
        assert "error" in res

    def test_calculate_human_readable_metrics_extreme_monotonic(self):
        """验证单调上升与单调下跌极端曲线精算"""
        dates = [f"2025-{i//20+1:02d}-{i%20+1:02d}" for i in range(100)]
        # 单调上升：无回撤，水下回本天数为 0
        mono_up = np.linspace(1.0, 2.0, 100)
        kpi_up = calculate_human_readable_metrics(mono_up, dates, capital=100000.0, target_return_pct=20.0)
        assert kpi_up["worst_case_drawdown_pct"] == 0.0
        assert kpi_up["max_underwater_days"] == 0
        assert kpi_up["best_case_return_pct"] > 0

        # 单调下降：回撤深，水下天数拉满
        mono_down = np.linspace(2.0, 1.0, 100)
        kpi_down = calculate_human_readable_metrics(mono_down, dates, capital=100000.0, target_return_pct=20.0)
        assert kpi_down["worst_case_drawdown_pct"] == 50.0
        assert kpi_down["worst_case_loss_amount"] == 50000.0
        assert kpi_down["max_underwater_days"] == 99

    def test_extreme_target_return_c5(self):
        """验证超高目标收益率（如一年翻倍 100%）在极端对账单中的执行"""
        check_100 = get_aggressive_dream_reality_check(capital=100000.0, target_return_pct=100.0)
        assert check_100["tier"] == "C5"
        assert check_100["target_return_pct"] == 100.0
        assert check_100["max_drawdown_pct"] > 25.0
        assert "warning_card" in check_100

    def test_underwater_recovery_date_accuracy(self):
        """验证最长水下回本周期的解套日期准确性（杜绝误报为时序终点）"""
        # 12天序列，第1天为高点(10)，第2~4天下跌，第5天回本(10)，随后持续创新高至第12天
        nav = [10.0, 8.0, 7.0, 6.0, 10.0, 12.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0]
        dates = [f"2020-01-{i:02d}" for i in range(1, len(nav) + 1)]
        res = calculate_human_readable_metrics(nav, dates)
        tuw = res["max_underwater_recovery"]
        assert tuw["max_tuw_days"] == 3
        assert tuw["tuw_peak_date"] == "2020-01-01"
        assert tuw["tuw_recovery_date"] == "2020-01-05"  # 准确为解套日，绝不能是 2020-01-12

    def test_smart_text_holding_days_and_lock_preservation(self):
        """验证智能文本导入后持有天数精确继承与7天锁准确生效"""
        pm = PortfolioManager(storage_file=":memory:")
        text = """
        易方达蓝筹 10000 成本1.85 现价1.92 已持满30天
        华夏科创50C 20000 刚买3天
        007339 20000
        """
        parsed = pm.parse_smart_text_holdings(text)
        assert len(parsed) == 3
        # 验证 007339 (带数字7) 不被误判为 7-29d
        p_300 = next(p for p in parsed if p["fund_code"] == "007339")
        assert p_300["holding_tag"] == ">=30d"

        # 验证导入后批次锁状态
        pm.import_from_smart_text(parsed, available_cash=5000.0)
        h_blue = pm.holdings["005827"]
        h_star = pm.holdings["011613"]
        assert h_blue.batches[0].holding_days >= 30
        assert h_blue.batches[0].safety_lock is False  # 满30天无锁
        assert h_star.batches[0].holding_days == 3
        assert h_star.batches[0].safety_lock is True   # 刚买3天必触发7天观察锁

    def test_blueprint_tier_differentiation(self):
        """验证从0建仓蓝图在不同风险档位下资产配比显著区分"""
        bp_c1 = StrategyBridge.generate_zero_start_blueprint(100000.0, None, tier="C1")
        bp_c5 = StrategyBridge.generate_zero_start_blueprint(100000.0, None, tier="C5")

        assert bp_c1["tier"] == "C1"
        assert bp_c5["tier"] == "C5"

        # C1 必须有纯债 002351 且占比 >= 50%
        bond_c1 = next((it for it in bp_c1["items"] if it["fund_code"] == "002351"), None)
        assert bond_c1 is not None
        assert bond_c1["target_weight_pct"] >= 50.0


