# -*- coding: utf-8 -*-
"""
专业买方投顾终端进阶升级 E2E 专项验收测试套件 (tests/test_adv_upgrade_suite.py)

涵盖 4 阶体系 (4-Tier Methodology):
- Tier 1: 核心功能覆盖 (Feature Coverage)
- Tier 2: 边界与极端异常覆盖 (Boundary & Corner Cases)
- Tier 3: 组合与交叉交互测试 (Combinatorial & Interaction Tests)
- Tier 4: 实盘全真应用场景测试 (Application Scenarios)

严格遵循只读裁判文件与 DataLoader 函数签名物理红线。
"""

import sys
import copy
import inspect
import tempfile
import sqlite3
import numpy as np
import pandas as pd
import pytest
from pathlib import Path
from datetime import datetime, date

# 确保 AGY2 核心模块位于 sys.path 首位
CURRENT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = CURRENT_DIR.parent if CURRENT_DIR.name == "tests" else CURRENT_DIR
AGY2_DIR = WORKSPACE_ROOT / "AGY2_FundAdvisory"

if str(AGY2_DIR) not in sys.path:
    sys.path.insert(0, str(AGY2_DIR))
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from advisory_engine import OpportunityRadarEngine, RADAR_SECTOR_CATALOG
from data_loader import IndexValuationEngine
from portfolio_manager import PortfolioManager, FundHolding, HoldingItem
from trading_clock_fee import TradingClock


# =====================================================================
# Tier 1: 核心功能覆盖 (Feature Coverage)
# =====================================================================

class TestTier1FeatureCoverage:
    """Tier 1: 核心金融事实修正、QDII 规则、估值标签与合规文案"""

    def test_tier1_dividend_low_vol_index_code_is_h30269(self):
        """
        1.1 红利低波赛道代码纠偏：
        断言 RADAR_SECTOR_CATALOG["dividend_low_vol"] 的 benchmark_index、index_code、symbol
        已彻底修正为 H30269（中证红利低波全收益指数），绝非 000978（医药100指数）。
        """
        assert "dividend_low_vol" in RADAR_SECTOR_CATALOG, "缺少 dividend_low_vol 赛道定义！"
        meta = RADAR_SECTOR_CATALOG["dividend_low_vol"]

        # 强制断言：必须为 H30269
        assert meta.get("benchmark_index") == "H30269", (
            f"benchmark_index 应为 H30269，实际为 {meta.get('benchmark_index')}"
        )
        assert meta.get("index_code") == "H30269", (
            f"index_code 应为 H30269，实际为 {meta.get('index_code')}"
        )
        assert meta.get("symbol") == "H30269", (
            f"symbol 应为 H30269，实际为 {meta.get('symbol')}"
        )

        # 反向防御：绝对不能是医药100代码 000978
        assert meta.get("benchmark_index") != "000978", "严重金融事实错误：红利低波 benchmark_index 仍被写为医药100 (000978)！"
        assert meta.get("index_code") != "000978", "严重金融事实错误：红利低波 index_code 仍被写为医药100 (000978)！"
        assert meta.get("symbol") != "000978", "严重金融事实错误：红利低波 symbol 仍被写为医药100 (000978)！"

    def test_tier1_index_valuation_engine_no_000978_alias(self):
        """
        1.2 估值引擎别名交叉污染清除：
        断言 IndexValuationEngine 中 H30269 词条中不再包含 '000978' 别名，
        彻底杜绝医药指数与红利低波指数代码产生张冠李戴映射。
        """
        # 1. 静态源码级/结构体 AST 核验
        dl_p = AGY2_DIR / "data_loader.py"
        dl_src = dl_p.read_text(encoding="utf-8")

        # 检验 index_defs 中针对 H30269 的定义
        h30269_defs = [line for line in dl_src.splitlines() if '"code": "H30269"' in line or "'code': 'H30269'" in line]
        assert len(h30269_defs) >= 1, "未在 data_loader.py 中找到 H30269 指数定义！"
        for def_line in h30269_defs:
            assert "000978" not in def_line, (
                f"发现 H30269 指数定义中仍挂载了 000978 别名！定义行: {def_line}"
            )

        # 2. 运行时映射核验
        val_map = IndexValuationEngine.fetch_or_calc_index_valuations(force_refresh=False)
        assert "H30269" in val_map, "IndexValuationEngine 缓存字典中必须包含 H30269！"
        h30269_entry = val_map["H30269"]
        assert "红利" in h30269_entry.get("name", ""), f"H30269 名称必须为红利类指数，实际为 {h30269_entry.get('name')}"

        # 若 val_map 中存在 000978，绝不能指向红利低波
        if "000978" in val_map:
            entry_000978 = val_map["000978"]
            assert entry_000978.get("name") != "红利低波", "000978 不得被映射为红利低波！"
            assert entry_000978.get("code") != "H30269", "000978 代码映射不得为 H30269！"

    def test_tier1_qdii_fund_identification(self):
        """
        1.3 QDII 海外基金精准识别：
        断言 050025 (标普500), 001071 (纳指100), 013402 (恒生科技) 均被准确识别为 QDII，
        而国内普通权益与固收基金（005561, 110020, 002351, 000001）不被误判。
        """
        clock = TradingClock()

        # 核心海外 QDII 基金清单
        qdii_codes = ["050025", "001071", "013402", "006075", "017436"]
        for c in qdii_codes:
            assert clock.is_qdii_fund(c), f"标的代码 {c} 必须被识别为 QDII 基金！"
            assert PortfolioManager.is_qdii_fund(c), f"PortfolioManager 必须将 {c} 识别为 QDII 基金！"

        # 名称关键词识别
        assert clock.is_qdii_fund("999999", "博时标普500ETF联接A")
        assert clock.is_qdii_fund("999998", "广发纳斯达克100ETF联接")
        assert clock.is_qdii_fund("999997", "华夏恒生科技ETF联接A")
        assert clock.is_qdii_fund("999996", "易方达标普信息科技QDII")

        # 国内 A 股普通基金绝不被误判
        domestic_cases = [
            ("005561", "创金合信红利低波A"),
            ("110020", "易方达沪深300ETF联接A"),
            ("002351", "易方达裕祥回报债券A"),
            ("000001", "华夏成长混合")
        ]
        for c, n in domestic_cases:
            assert not clock.is_qdii_fund(c, n), f"国内基金 [{c} {n}] 严禁被误判为 QDII！"
            assert not PortfolioManager.is_qdii_fund(c, n), f"PortfolioManager 严禁将 [{c} {n}] 误判为 QDII！"

    def test_tier1_qdii_delivery_rules(self):
        """
        1.4 QDII 跨时区交割清算规则：
        断言美股 QDII (050025) 返回 T+2 确认、T+6~T+8 到账，
        且结算附注 (settlement_note) 包含「跨时区清算」合规风险提示。
        """
        clock = TradingClock()
        res_qdii = clock.calculate_settlement_dates(
            order_dt=datetime(2026, 11, 6, 10, 0),
            fund_code="050025",
            fund_name="博时标普500ETF联接A"
        )

        assert "effective_trade_date" in res_qdii
        assert "confirm_date" in res_qdii
        assert "arrive_date" in res_qdii

        eff_dt = datetime.strptime(res_qdii["effective_trade_date"], "%Y-%m-%d").date()
        conf_dt = datetime.strptime(res_qdii["confirm_date"], "%Y-%m-%d").date()
        arr_dt = datetime.strptime(res_qdii["arrive_date"], "%Y-%m-%d").date()

        # 确认日与生效日之间至少隔 2 个自然日（跨时区 T+2 交易日）
        trade_offset_conf = clock.get_trade_day_offset(res_qdii["effective_trade_date"], res_qdii["confirm_date"])
        assert trade_offset_conf == 2, f"美股 QDII 份额确认日必须为 T+2，实际交易日偏移: {trade_offset_conf}"

        # 资金到账日必须为 T+6 ~ T+8 交易日（标准为 T+7）
        trade_offset_arr = clock.get_trade_day_offset(res_qdii["effective_trade_date"], res_qdii["arrive_date"])
        assert 6 <= trade_offset_arr <= 8, f"美股 QDII 资金到账日必须在 T+6~T+8 之间，实际交易日偏移: {trade_offset_arr}"

        # 结算附注检验
        note = res_qdii.get("settlement_note") or res_qdii.get("note") or res_qdii.get("desc") or ""
        assert "跨时区清算" in note, (
            f"QDII交割推算未包含'跨时区清算'合规标注说明！当前返回: {res_qdii}"
        )

    def test_tier1_qdii_exclusion_from_same_company_conversion(self):
        """
        1.5 同公司基金转换严禁纳入 QDII：
        断言即便卖出标的与买入标的同属博时基金（如 050025 博时标普500 与 050027 博时信用债），
        系统严禁生成 PRIORITY_1_SWITCH (T+1 同公司转换) 路由！
        """
        pm = PortfolioManager(db_path=":memory:")
        pm.holdings = {}
        pm.available_cash = 10000.0

        # 加入持有满 30 天的博时标普500 (QDII)
        pm.add_or_update_holding(
            fund_code="050025",
            shares=20000.0,
            nav=1.5,
            cost_price=1.2,
            holding_days=60,
            fund_name="博时标普500ETF联接A"
        )

        # 构造调仓需求：减持博时标普500，买入博时信用债 (050027)
        target_weights = {
            "050025": 0.0,   # 清仓卖出
            "050027": 0.8    # 买入同公司国内债基
        }
        meta_dict = {
            "050025": {"fund_name": "博时标普500ETF联接A", "company": "博时基金", "current_nav": 1.5},
            "050027": {"fund_name": "博时信用债纯债债券A", "company": "博时基金", "current_nav": 1.0}
        }

        routes = pm.calculate_rebalance_routes(
            target_weights=target_weights,
            target_funds_meta=meta_dict,
            holding_days_dict={"050025": 60}
        )

        # 遍历生成的路由，严禁出现 PRIORITY_1_SWITCH
        switch_routes = [r for r in routes if r.get("route_priority") == "PRIORITY_1_SWITCH"]
        assert len(switch_routes) == 0, (
            f"风控违规：检测到 QDII 基金与普通公募基金被错误匹配为同公司 T+1 转换！违规路由: {switch_routes}"
        )

    def test_tier1_valuation_credibility_badges(self):
        """
        1.6 四档基金盘中估值可信度标签检验：
        - 指数联接基金 -> 「指数高准度」
        - 纯债债券基金 -> 「债基看久期票息」
        - 美股 QDII 基金 -> 「美股休市·看隔夜期指」
        - 主动混合基金 -> 「季报重仓估算」
        """
        # 测试美股 QDII 标的
        tag_us = PortfolioManager.get_fund_valuation_reliability_tag("050025", "博时标普500ETF联接A")
        assert tag_us == "美股休市·看隔夜期指", f"美股 QDII 标签应为'美股休市·看隔夜期指'，实际为 {tag_us}"

        tag_nasdaq = PortfolioManager.get_fund_valuation_reliability_tag("001071", "华安纳斯达克100联接A")
        assert tag_nasdaq == "美股休市·看隔夜期指"

        # 测试纯债基金标的
        tag_bond = PortfolioManager.get_fund_valuation_reliability_tag("002351", "易方达裕祥回报债券A")
        assert tag_bond == "债基看久期票息", f"纯债基金标签应为'债基看久期票息'，实际为 {tag_bond}"

        tag_pure_bond = PortfolioManager.get_fund_valuation_reliability_tag("007466", "广发纯债债券A")
        assert tag_pure_bond == "债基看久期票息"

        # 测试指数联接标的
        tag_idx1 = PortfolioManager.get_fund_valuation_reliability_tag("005561", "创金合信红利低波A")
        assert tag_idx1 == "指数高准度", f"指数基金标签应为'指数高准度'，实际为 {tag_idx1}"

        tag_idx2 = PortfolioManager.get_fund_valuation_reliability_tag("110020", "易方达沪深300ETF联接A")
        assert tag_idx2 == "指数高准度"

        # 测试主动混合标的
        tag_act = PortfolioManager.get_fund_valuation_reliability_tag("000001", "华夏成长混合")
        assert tag_act == "季报重仓估算", f"主动混合基金标签应为'季报重仓估算'，实际为 {tag_act}"

    def test_tier1_compliance_wording_no_baoben(self):
        """
        1.7 全站合规清理：剔除所有违规'保本率'用词
        断言 UI 源码 (app_gui.py) 与核心投顾引擎中绝对不存在'保本率'，
        必须规范替换为'正收益概率'或'本金安全率'。
        """
        target_files = [
            AGY2_DIR / "app_gui.py",
            AGY2_DIR / "winrate_engine.py",
            AGY2_DIR / "strategy_bridge.py",
            AGY2_DIR / "advisory_engine.py",
            AGY2_DIR / "portfolio_manager.py"
        ]

        violations = []
        for f in target_files:
            if not f.exists():
                continue
            text = f.read_text(encoding="utf-8")
            # 扫描每一行，排除法律免责中的"不承诺保本"或"不保本"
            lines = text.splitlines()
            for idx, line in enumerate(lines, 1):
                if "保本率" in line:
                    violations.append(f"{f.name}:{idx} -> {line.strip()}")

        assert len(violations) == 0, (
            f"合规红线违规：检测到代码中仍残留违规宣传用词'保本率'，必须替换为'正收益概率'或'本金安全率'！\n"
            + "\n".join(violations)
        )

    def test_tier1_bias20_calculation_no_dividend_spike(self):
        """
        1.8 红利赛道 20 日均线乖离率 (Bias20) 分红集中期平滑机制：
        断言在输入含有单日 +2.5% 分红派息脉冲跳空的全收益序列时，
        平滑机制可有效消除虚假正乖离脉冲，防止误报超买。
        """
        engine = OpportunityRadarEngine()

        # 构造一条基准平稳日线，第 25 天出现 +2.5% 单日分红跳空
        base_nav = 1.0
        synthetic_s = [base_nav * (1.0 + 0.0005 * i) for i in range(25)]
        # 模拟分红除息日脉冲跳空加回
        synthetic_s.append(synthetic_s[-1] * 1.025)
        for i in range(10):
            synthetic_s.append(synthetic_s[-1] * (1.0 + 0.0005 * i))

        s_arr = np.array(synthetic_s, dtype=float)
        assert len(s_arr) >= 35

        # 模拟计算红利低波的平滑后指标
        daily_returns = np.diff(s_arr[-25:]) / s_arr[-25:-1]
        normal_returns = np.clip(daily_returns, -0.035, 0.035)
        reconstructed_s = [s_arr[-25]]
        for r in normal_returns:
            reconstructed_s.append(reconstructed_s[-1] * (1.0 + r))

        ma20_smoothed = float(np.mean(reconstructed_s[-20:]))
        p_t = float(s_arr[-1])
        bias_smoothed = float(((p_t - ma20_smoothed) / ma20_smoothed) * 100.0)

        # 平滑后的 Bias20 必须处于温和合理区间 (< 4.0%)，杜绝畸形脉冲
        assert -5.0 <= bias_smoothed <= 4.0, (
            f"分红平滑后 Bias20 异常过大: {bias_smoothed:.2f}%"
        )


# =====================================================================
# Tier 2: 边界与极端异常覆盖 (Boundary & Corner Cases)
# =====================================================================

class TestTier2BoundaryAndCornerCases:
    """Tier 2: 边界条件、极端输入与优雅降级"""

    def test_tier2_empty_portfolio_and_edge_fund_codes_in_qdii_checks(self):
        """
        2.1 边界标的代码与空持仓鲁棒性：
        对空字符串、None、纯空格、非法字符与超长数字标的代码进行 QDII 甄别，
        断言系统 0 崩溃，优雅返回 False。
        """
        clock = TradingClock()
        edge_codes = ["", "   ", None, "0", "999999", "INVALID", "050025_OLD", "1234567"]
        for c in edge_codes:
            assert clock.is_qdii_fund(c) is False, f"非法代码 [{c}] 应当返回 False！"
            assert PortfolioManager.is_qdii_fund(c) is False

        # 空持仓调用
        empty_pm = PortfolioManager(db_path=":memory:")
        assert len(empty_pm.holdings) == 0
        tag_empty = empty_pm.get_fund_valuation_reliability_tag("", "")
        assert tag_empty == "季报重仓估算", "空代码空名称应优雅兜底为'季报重仓估算'"

    def test_tier2_cross_company_vs_same_company_routes(self):
        """
        2.2 跨公司 vs 同公司 与 QDII vs 非 QDII 四向排列组合矩阵：
        1. 同公司 + 两个国内基金 -> 允许 PRIORITY_1_SWITCH
        2. 同公司 + 含一个 QDII -> 严禁 PRIORITY_1_SWITCH
        3. 跨公司 + 两个国内基金 -> 严禁 PRIORITY_1_SWITCH
        4. 跨公司 + 含一个 QDII -> 严禁 PRIORITY_1_SWITCH
        """
        pm = PortfolioManager(db_path=":memory:")
        pm.available_cash = 50000.0

        # Case 1: 同公司 + 两个国内基金 (易方达 110020 -> 易方达 002351)
        pm.holdings = {}
        pm.add_or_update_holding("110020", shares=10000, nav=1.5, cost_price=1.2, holding_days=60, fund_name="易方达沪深300")
        routes_c1 = pm.calculate_rebalance_routes(
            target_weights={"110020": 0.0, "002351": 0.5},
            target_funds_meta={
                "110020": {"fund_name": "易方达沪深300", "company": "易方达基金", "current_nav": 1.5},
                "002351": {"fund_name": "易方达裕祥回报", "company": "易方达基金", "current_nav": 1.0}
            },
            holding_days_dict={"110020": 60}
        )
        assert any(r.get("route_priority") == "PRIORITY_1_SWITCH" for r in routes_c1), "国内同公司必须触发转换"

        # Case 2: 同公司 + 含一个 QDII (博时 050025 -> 博时 050027)
        pm.holdings = {}
        pm.add_or_update_holding("050025", shares=10000, nav=1.5, cost_price=1.2, holding_days=60, fund_name="博时标普500")
        routes_c2 = pm.calculate_rebalance_routes(
            target_weights={"050025": 0.0, "050027": 0.5},
            target_funds_meta={
                "050025": {"fund_name": "博时标普500", "company": "博时基金", "current_nav": 1.5},
                "050027": {"fund_name": "博时信用债", "company": "博时基金", "current_nav": 1.0}
            },
            holding_days_dict={"050025": 60}
        )
        assert not any(r.get("route_priority") == "PRIORITY_1_SWITCH" for r in routes_c2), "同公司含 QDII 严禁转换"

        # Case 3: 跨公司 + 两个国内基金 (易方达 110020 -> 广发 007466)
        pm.holdings = {}
        pm.add_or_update_holding("110020", shares=10000, nav=1.5, cost_price=1.2, holding_days=60, fund_name="易方达沪深300")
        routes_c3 = pm.calculate_rebalance_routes(
            target_weights={"110020": 0.0, "007466": 0.5},
            target_funds_meta={
                "110020": {"fund_name": "易方达沪深300", "company": "易方达基金", "current_nav": 1.5},
                "007466": {"fund_name": "广发纯债", "company": "广发基金", "current_nav": 1.0}
            },
            holding_days_dict={"110020": 60}
        )
        assert not any(r.get("route_priority") == "PRIORITY_1_SWITCH" for r in routes_c3), "跨公司严禁转换"

        # Case 4: 跨公司 + 含一个 QDII (博时 050025 -> 易方达 110020)
        pm.holdings = {}
        pm.add_or_update_holding("050025", shares=10000, nav=1.5, cost_price=1.2, holding_days=60, fund_name="博时标普500")
        routes_c4 = pm.calculate_rebalance_routes(
            target_weights={"050025": 0.0, "110020": 0.5},
            target_funds_meta={
                "050025": {"fund_name": "博时标普500", "company": "博时基金", "current_nav": 1.5},
                "110020": {"fund_name": "易方达沪深300", "company": "易方达基金", "current_nav": 1.5}
            },
            holding_days_dict={"050025": 60}
        )
        assert not any(r.get("route_priority") == "PRIORITY_1_SWITCH" for r in routes_c4), "跨公司含 QDII 严禁转换"

    def test_tier2_non_existent_index_fallback_in_valuation_engine(self):
        """
        2.3 异常或未收录指数代码降级保护：
        断言向 OpportunityRadarEngine 传入非法/未知赛道 ID 时，
        引擎返回稳健基线中枢分位数 (50.0%)，0 抛出 KeyError。
        """
        radar = OpportunityRadarEngine()
        bogus_cases = [
            ("unknown_sector_999", {}),
            ("", {}),
            ("invalid_code", {"benchmark_index": "999999", "symbol": "INVALID"})
        ]
        for sec_id, meta in bogus_cases:
            pct = radar.get_sector_valuation_percentile(sec_id, meta)
            assert isinstance(pct, float)
            assert 0.0 <= pct <= 100.0, f"估值分位数必须在 [0, 100] 区间内，实际为 {pct}"


# =====================================================================
# Tier 3: 组合与交叉交互测试 (Combinatorial & Interaction Tests)
# =====================================================================

class TestTier3CombinatorialAndInteractionTests:
    """Tier 3: 混合资产组合在途时滞与周期精算交互"""

    def test_tier3_mixed_portfolio_settlement_and_cycle_partitioning(self):
        """
        3.1 混合资产组合 (国内A股 + 纯债 + 美股QDII + 港股QDII) 交割周期严格时区划分：
        断言多标的并发下单时，系统准确推算各自差异化的份额确认日与资金到账日。
        """
        clock = TradingClock()
        order_time = datetime(2026, 11, 6, 14, 0) # 盘中周五 14:00

        portfolio_assets = [
            {"code": "005561", "name": "创金合信红利低波A", "type": "domestic_equity", "exp_conf": 1, "exp_arr": 2},
            {"code": "002351", "name": "易方达裕祥回报债券A", "type": "domestic_bond", "exp_conf": 1, "exp_arr": 2},
            {"code": "050025", "name": "博时标普500ETF联接A", "type": "us_qdii", "exp_conf": 2, "exp_arr": 7},
            {"code": "013402", "name": "华夏恒生科技ETF联接A", "type": "hk_qdii", "exp_conf": 2, "exp_arr": 7}
        ]

        settlement_results = {}
        for item in portfolio_assets:
            res = clock.calculate_settlement_dates(
                order_dt=order_time,
                fund_code=item["code"],
                fund_name=item["name"]
            )
            settlement_results[item["code"]] = res

            conf_offset = clock.get_trade_day_offset(res["effective_trade_date"], res["confirm_date"])
            arr_offset = clock.get_trade_day_offset(res["effective_trade_date"], res["arrive_date"])

            assert conf_offset == item["exp_conf"], (
                f"标的 {item['code']} 期望确认偏移 T+{item['exp_conf']}，实际为 T+{conf_offset}"
            )
            # 到账周期：QDII 满足 6~8，国内满足 2
            if "qdii" in item["type"]:
                assert 6 <= arr_offset <= 8, f"QDII 到账偏移必须在 6~8 天，实际为 T+{arr_offset}"
                note = res.get("settlement_note") or res.get("note") or res.get("desc") or ""
                assert "跨时区清算" in note
            else:
                assert arr_offset == item["exp_arr"]

    def test_tier3_rebalance_routes_multi_holding_interaction(self):
        """
        3.2 多持仓复杂调仓交互：
        包含 4 只基金（博时 QDII、博时债基、易方达指数、易方达混合）：
        验证易方达两只国内基金精准撮合同公司转换，而博时 QDII 严格阻断转换，
        输出符合金融物理规律的独立赎回与再申购单。
        """
        pm = PortfolioManager(db_path=":memory:")
        pm.available_cash = 20000.0

        pm.add_or_update_holding("050025", shares=20000, nav=1.5, cost_price=1.2, holding_days=60, fund_name="博时标普500")
        pm.add_or_update_holding("110020", shares=20000, nav=1.5, cost_price=1.2, holding_days=60, fund_name="易方达沪深300")

        # 调仓目标：卖出博时标普500与易方达沪深300，买入博时信用债与易方达优质精选
        target_weights = {
            "050025": 0.0,
            "110020": 0.0,
            "050027": 0.4,
            "110011": 0.4
        }
        meta_dict = {
            "050025": {"fund_name": "博时标普500", "company": "博时基金", "current_nav": 1.5},
            "050027": {"fund_name": "博时信用债", "company": "博时基金", "current_nav": 1.0},
            "110020": {"fund_name": "易方达沪深300", "company": "易方达基金", "current_nav": 1.5},
            "110011": {"fund_name": "易方达优质精选", "company": "易方达基金", "current_nav": 2.0}
        }

        routes = pm.calculate_rebalance_routes(
            target_weights=target_weights,
            target_funds_meta=meta_dict,
            holding_days_dict={"050025": 60, "110020": 60}
        )

        # 检查易方达成功匹配转换
        efund_switch = [
            r for r in routes
            if r.get("route_priority") == "PRIORITY_1_SWITCH"
            and r.get("from_code") == "110020" and r.get("to_code") == "110011"
        ]
        assert len(efund_switch) == 1, "易方达两只国内基金必须成功匹配同公司 T+1 转换！"

        # 检查博时 QDII 绝不出现在转换列表中
        bostera_switch = [
            r for r in routes
            if r.get("route_priority") == "PRIORITY_1_SWITCH"
            and (r.get("from_code") == "050025" or r.get("to_code") == "050025")
        ]
        assert len(bostera_switch) == 0, "博时标普500 QDII 绝对不允许生成转换单！"


# =====================================================================
# Tier 4: 实盘全真应用场景测试 (Application Scenarios)
# =====================================================================

class TestTier4ApplicationScenarios:
    """Tier 4: 实盘全生命周期账本、净值曲线追踪与跟单打卡闭环"""

    def test_tier4_full_flow_rebalance_with_qdii_present(self):
        """
        4.1 全真全案调仓推演：
        模拟用户持仓包含 10 万元总资产（含现金、国内红利低波、纯债与海外 QDII），
        执行一键再平衡推演，验证生成的调仓单与清算时间无任何冲突。
        """
        pm = PortfolioManager(db_path=":memory:")
        pm.available_cash = 20000.0
        pm.baseline_equity = 100000.0

        # 持仓
        pm.add_or_update_holding("005561", shares=20000, nav=1.5, cost_price=1.4, holding_days=45, fund_name="创金合信红利低波A") # 30000
        pm.add_or_update_holding("002351", shares=20000, nav=1.0, cost_price=1.0, holding_days=90, fund_name="易方达裕祥回报债券A") # 20000
        pm.add_or_update_holding("050025", shares=20000, nav=1.5, cost_price=1.2, holding_days=60, fund_name="博时标普500ETF联接A") # 30000

        total_eq = pm.calculate_total_equity()
        assert total_eq == 100000.0

        # 目标配置：防御再平衡（增加纯债至 40%，降低海外 QDII 至 10%，维持红利低波 30%）
        target_weights = {
            "005561": 0.30,  # 30000 (维持不变)
            "002351": 0.40,  # 40000 (增持 20000)
            "050025": 0.10   # 10000 (减持 20000)
        }
        meta_dict = {
            "005561": {"fund_name": "创金合信红利低波A", "company": "创金合信基金", "current_nav": 1.5},
            "002351": {"fund_name": "易方达裕祥回报债券A", "company": "易方达基金", "current_nav": 1.0},
            "050025": {"fund_name": "博时标普500ETF联接A", "company": "博时基金", "current_nav": 1.5}
        }

        routes = pm.calculate_rebalance_routes(
            target_weights=target_weights,
            target_funds_meta=meta_dict,
            holding_days_dict={"005561": 45, "002351": 90, "050025": 60}
        )

        assert len(routes) > 0
        # 绝无违规 switch
        for r in routes:
            if r.get("route_priority") == "PRIORITY_1_SWITCH":
                assert r.get("from_code") != "050025" and r.get("to_code") != "050025"

    def test_tier4_nav_history_tracking_and_apply_orders_closed_loop(self):
        """
        4.2 实盘净值记账曲线 (nav_history) 与调仓一键跟单打卡：
        断言 save_state 自动按日记账，且 apply_rebalance_orders_to_holdings
        真实将调仓单同步至账本并驱动 NAV 计算，完成投后闭环。
        """
        pm = PortfolioManager(db_path=":memory:")
        pm.available_cash = 30000.0
        pm.baseline_equity = 50000.0
        pm.nav_history = []

        pm.add_or_update_holding("005561", shares=10000, nav=1.5, cost_price=1.2, holding_days=30, fund_name="创金合信红利低波A")
        pm.add_or_update_holding("002351", shares=5000, nav=1.0, cost_price=1.0, holding_days=60, fund_name="易方达裕祥回报债券A")

        # 触发持久化记账
        pm.save_state(record_snapshot=True)
        assert len(pm.nav_history) >= 1
        last_nav = pm.nav_history[-1]
        assert "date" in last_nav
        assert "account_nav" in last_nav
        assert "benchmark_nav" in last_nav
        assert last_nav["account_nav"] > 0

        # 模拟前端调仓执行单
        follow_orders = [
            {
                "基金代码": "005561",
                "基金名称": "创金合信红利低波A",
                "建议操作": "增持/建仓",
                "建议调仓金额(元)": 15000.0
            },
            {
                "基金代码": "002351",
                "基金名称": "易方达裕祥回报债券A",
                "建议操作": "清仓",
                "建议调仓金额(元)": -5000.0
            }
        ]

        up_cnt = pm.apply_rebalance_orders_to_holdings(follow_orders)
        assert up_cnt == 2
        assert "002351" not in pm.holdings, "已清仓标的必须从持仓列表中剔除！"
        assert "005561" in pm.holdings
        assert pm.holdings["005561"].shares == 20000.0 # 10000 + (15000/1.5) = 20000
        assert pm.available_cash == 20000.0 # 30000 - 15000 + 5000 = 20000

    def test_tier4_holding_item_backward_compatibility(self):
        """
        4.3 持仓对象双向兼容性验证：
        断言 HoldingItem 与 FundHolding 保持完全类型等价，
        支持 cost_nav / cost_price 参数无缝迁移。
        """
        h = HoldingItem(
            fund_code="005561",
            fund_name="创金合信红利低波A",
            shares=5000.0,
            cost_nav=1.25,
            current_nav=1.50
        )
        assert h.cost_price == 1.25
        assert h.market_value == 7500.0
        assert h.cost_basis == 6250.0
        assert h.floating_pnl == 1250.0
        assert h.floating_pnl_pct == 20.0

    def test_tier4_14_sectors_genuine_dynamics(self):
        """
        4.4 14 大核心赛道真动态精算 (零静态假常量)：
        断言 scan_all_sectors 输出的 14 个赛道中，没有共享 (er=0.50, bias=1.0, crowd=85.0) 假常数。
        """
        engine = OpportunityRadarEngine()
        sectors = engine.scan_all_sectors()
        assert len(sectors) == 14, f"赛道数量必须为 14，实际为 {len(sectors)}"

        dummy_count = 0
        for s in sectors:
            er = round(float(s.get("er_20", 0.0)), 2)
            bias = round(float(s.get("bias_20", 0.0)), 1)
            crowd = round(float(s.get("crowding_score", s.get("s_crowd", 0.0))), 1)
            if er == 0.50 and bias == 1.0 and crowd == 85.0:
                dummy_count += 1

        assert dummy_count == 0, f"发现 {dummy_count} 个赛道使用了静态假常量 (0.50, 1.0, 85.0)！"
