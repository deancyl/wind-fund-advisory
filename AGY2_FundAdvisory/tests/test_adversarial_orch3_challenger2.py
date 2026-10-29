"""
Empirical Adversarial Test Suite for De-Mining & Classification (Challenger-2)
Target: portfolio_manager.py
Author: Challenger-2 (Empirical Challenger)
"""

import sys
import copy
import re
import pytest
import pandas as pd
from pathlib import Path
from typing import Dict, Any

TEST_DIR = Path(__file__).resolve().parent
APP_DIR = TEST_DIR.parent
WORKSPACE_ROOT = APP_DIR.parent if APP_DIR.name == "AGY2_FundAdvisory" else APP_DIR

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

# Namespace collision guard
if "src" in sys.modules and hasattr(sys.modules["src"], "__path__"):
    local_src = str(WORKSPACE_ROOT / "src")
    if local_src not in sys.modules["src"].__path__:
        sys.modules["src"].__path__.insert(0, local_src)

from portfolio_manager import (
    PortfolioManager,
    classify_fund_asset_class,
    FUND_LOOK_THROUGH_DATA,
    CORE_STRATEGY_POOL,
    EXTENDED_FUND_CATALOG,
    SECTOR_FUND_SELECTION,
)


@pytest.fixture
def pm(tmp_path):
    """Isolated PortfolioManager instance with temporary DB and ledger"""
    db_file = tmp_path / "test_adv2_state.db"
    json_file = tmp_path / "test_adv2_ledger.json"
    return PortfolioManager(db_path=db_file, ledger_json_path=json_file)


# ==============================================================================
# 1. 4 裁判基建文件完整性审计 (Referee Infrastructure Invariant Audit)
# ==============================================================================

def test_referee_infrastructure_files_integrity():
    """验证 4 个只读裁判基建文件未被篡改且完整存在"""
    referee_files = [
        APP_DIR / "judge_engine.py",
        APP_DIR / "holdout_vault.py",
        APP_DIR / "AGENT_SPEC.md",
        APP_DIR / "tests" / "test_infra.py",
    ]
    for rf in referee_files:
        assert rf.exists(), f"裁判基建文件丢失: {rf}"
        assert rf.stat().st_size > 0, f"裁判基建文件为空: {rf}"


# ==============================================================================
# 2. 三层通用财务排雷对抗性测试 (3-Layer Fundamental De-Mining Verification)
# ==============================================================================

class TestThreeLayerFundamentalDeMining:
    """
    三层通用基本面排雷引擎对抗性检验：
    Layer 1: 金融机构业态识别与零扣分豁免
    Layer 2: 重资产硬科技晶圆与公用事业能源现金流健康校验 (CFO > 0)
    Layer 3: 真造假与暴雷企业高息高存且现金流恶化 (CFO < 0) 坚决扣40分红灯
    """

    def test_layer1_edge_financial_institutions_exemption(self, pm):
        """
        构造/测试边缘金融机构（农商行、民营券商、合资险资、小额信托、期货）：
        验证无需股票代码白名单，自动识别申万金融业态并豁免存贷双高（扣0分，double_high_risk=False）
        """
        edge_financial_stocks = [
            "渝农商行",
            "常熟农商银行",
            "张家港农商银行",
            "江南农商行",
            "华林证券",
            "东方财富证券",
            "国金证券",
            "中邮人寿保险",
            "安联人寿保险",
            "中意人寿保险",
            "陕国投信托",
            "平安信托",
            "华润信托",
            "南华期货",
            "永安期货",
            "东海期货",
            "虚构民营商业银行",
            "虚构合资人寿保险",
            "虚构产业信托投资",
        ]

        dummy_fund_code = "990001"
        FUND_LOOK_THROUGH_DATA[dummy_fund_code] = {
            "top_stocks": edge_financial_stocks,
            "fund_name": "测试边缘金融机构穿透基金",
        }

        res = pm.screen_fund_look_through_risk(dummy_fund_code)
        assert res["is_ashare_equity"] is True
        screen_items = res["top_stocks_screen"]
        assert len(screen_items) == len(edge_financial_stocks)

        for s in screen_items:
            assert s["double_high_risk"] is False, (
                f"金融机构 {s['stock_name']} 未能免除存贷双高风险！"
            )
            assert "金融业豁免" in s["double_high_status"], (
                f"金融机构 {s['stock_name']} 状态不是金融业豁免: {s['double_high_status']}"
            )
            assert s["double_high_exempt"] is True
            # 扣分项中绝不能包含存贷双高
            deduct_names = [d[0] for d in s["deductions_detail"]]
            assert "存贷双高造假特征" not in deduct_names, (
                f"金融机构 {s['stock_name']} 被错误扣除存贷双高分！"
            )

    def test_layer1_shenwan_financial_industry_by_code(self, pm):
        """
        测试通过申万金融行业（银行Ⅱ、证券Ⅱ、保险Ⅱ、非银金融）识别并豁免，无硬编码白名单
        """
        stock_name = "标的_金融业态"
        dummy_fund = "990002"
        FUND_LOOK_THROUGH_DATA[dummy_fund] = {
            "top_stocks": [stock_name],
            "fund_name": "测试申万行业识别基金",
        }

        # 模拟 toolkit 返回银行/证券/保险行业
        mock_fin = {
            "symbol": "600999.SH",
            "stock_name": stock_name,
            "industry": "银行Ⅱ",
            "double_high_risk": True,
            "monetary_funds_billion": 500.0,
            "total_debt_billion": 1200.0,
            "goodwill_ratio_pct": 0.0,
            "fcf_billion": 50.0,
        }
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(pm.toolkit.earnings_forecast, "screen_financial_risks", lambda s: mock_fin)
            res = pm.screen_fund_look_through_risk(dummy_fund)
            item = res["top_stocks_screen"][0]
            assert item["double_high_risk"] is False
            assert "金融业豁免" in item["double_high_status"]
            assert item["stock_score"] == 100.0

    def test_layer2_heavy_asset_strategic_tech_healthy_cfo(self, pm):
        """
        测试重资产硬科技晶圆/公用事业能源标的：
        在经营现金流健康 (CFO > 0) 时，正确判定为“重资产正常经营/现金流健康”，豁免存贷双高
        """
        tech_and_energy_stocks = [
            ("中芯国际", "晶圆制造/半导体"),
            ("华虹公司", "晶圆代工/集成电路"),
            ("长江电力", "电力能源/公用事业"),
            ("中国核电", "电力能源/高端装备"),
            ("北方华创", "半导体设备"),
            ("天合光能", "光伏能源/石化"),
        ]

        dummy_fund = "990003"
        FUND_LOOK_THROUGH_DATA[dummy_fund] = {
            "top_stocks": [s[0] for s in tech_and_energy_stocks],
            "fund_name": "测试硬科技与公用事业重资产基金",
        }

        # 模拟：账面货币资金高且负债高 (raw_double_high=True)，但经营现金流健康 (CFO > 0)
        def mock_screen_fin(sym):
            name = pm.resolve_stock_symbol(sym) or sym
            return {
                "symbol": sym,
                "stock_name": name,
                "double_high_risk": True,
                "monetary_funds_billion": 200.0,
                "total_debt_billion": 350.0,
                "goodwill_ratio_pct": 1.5,
                "fcf_billion": 20.0,
            }

        class MockHealthyConn:
            def execute(self, sql, params=()):
                class MockDF:
                    empty = False
                    iloc = [{"ocf_per_share": 1.85, "industry": "半导体"}]
                    def df(self):
                        return pd.DataFrame([{"ocf_per_share": 1.85, "industry": "半导体"}])
                return MockDF()

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(pm.toolkit.earnings_forecast, "screen_financial_risks", mock_screen_fin)
            import unittest.mock as mock
            with mock.patch("duckdb.connect", return_value=MockHealthyConn()):
                res = pm.screen_fund_look_through_risk(dummy_fund)
                for item in res["top_stocks_screen"]:
                    assert item["double_high_risk"] is False, (
                        f"健康现金流硬科技企业 {item['stock_name']} 应豁免存贷双高！"
                    )
                    assert item["double_high_status"] == "重资产正常经营/现金流健康"
                    assert item["double_high_exempt"] is True

    def test_layer2_heavy_asset_tech_deteriorated_cfo_gets_penalized(self, pm):
        """
        对抗性反向检验：若重资产硬科技/公用事业标的经营现金流恶化 (CFO <= 0 或负数)，
        严禁盲目豁免，必须判定为存贷双高预警并扣除 40 分！
        """
        dummy_fund = "990004"
        FUND_LOOK_THROUGH_DATA[dummy_fund] = {
            "top_stocks": ["虚构恶化半导体晶圆厂"],
            "fund_name": "测试恶化科技企业",
        }

        mock_deteriorated_fin = {
            "symbol": "688999.SH",
            "stock_name": "虚构恶化半导体晶圆厂",
            "industry": "半导体",
            "double_high_risk": True,
            "monetary_funds_billion": 300.0,
            "total_debt_billion": 600.0,
            "goodwill_ratio_pct": 2.0,
            "fcf_billion": -50.0,
        }

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(pm.toolkit.earnings_forecast, "screen_financial_risks", lambda s: mock_deteriorated_fin)
            res = pm.screen_fund_look_through_risk(dummy_fund)
            item = res["top_stocks_screen"][0]
            assert item["double_high_risk"] is True, "CFO恶化的硬科技企业不应被豁免！"
            assert item["double_high_status"] == "存贷双高预警"
            assert item["stock_score"] <= 60.0
            deduct_names = [d[0] for d in item["deductions_detail"]]
            assert "存贷双高造假特征" in deduct_names
            # 存贷双高扣分必须恰好为 40 分
            for d in item["deductions_detail"]:
                if d[0] == "存贷双高造假特征":
                    assert d[1] == 40.0

    def test_layer3_true_financial_fraud_vanke_a_trigger_danger(self, pm):
        """
        测试真财务造假与暴雷特征企业（账面高额现金但有息负债高企，且自由现金流持续恶化 CFO < 0，如万科A）：
        检验是否坚决识别为存贷双高高危亮红灯（扣 40 分，评级 Danger 🔴 预警）
        """
        dummy_fund = "990005"
        FUND_LOOK_THROUGH_DATA[dummy_fund] = {
            "top_stocks": ["万科A"],
            "fund_name": "测试暴雷地产基金",
        }

        res = pm.screen_fund_look_through_risk(dummy_fund)
        item = res["top_stocks_screen"][0]

        assert item["stock_name"] == "万科A"
        assert item["double_high_risk"] is True, "万科A必须亮起存贷双高红灯！"
        assert item["double_high_status"] == "存贷双高预警"
        assert item["double_high_exempt"] is False

        # 检查扣分项
        deduct_dict = {d[0]: d[1] for d in item["deductions_detail"]}
        assert "存贷双高造假特征" in deduct_dict
        assert deduct_dict["存贷双高造假特征"] == 40.0
        assert "自由现金流为负" in deduct_dict
        assert deduct_dict["自由现金流为负"] == 10.0

        # 总得分应为 50.0 分，处于 Danger 🔴 预警
        assert item["stock_score"] == 50.0
        assert item["risk_level"] == "Danger"
        assert "🔴" in item["risk_badge"]

        # 组合层面也应反映出预警
        assert res["danger_count"] == 1
        assert res["risk_level"] == "Danger"

    def test_real_world_smic_de_mining_empirical_audit(self, pm):
        """
        实证审计：排查真实生产组合 (011612 / 011613 华夏科创50) 底层核心重仓股中芯国际 (688981.SH)
        在当前未 mock 状态下的真实排雷判定。
        若判定为存贷双高预警 (40分)，说明数据库缺少 ocf_per_share 导致 cfo_healthy 假阴性，
        未能联动 fcf_billion > 0 兜底。
        """
        res = pm.screen_fund_look_through_risk("011612")
        smic_matches = [s for s in res["top_stocks_screen"] if "中芯国际" in s["stock_name"]]
        assert len(smic_matches) > 0
        smic = smic_matches[0]
        # 记录真实状态：中芯国际在现有代码中是否被存贷双高误杀
        # 这里记录真实表现作为实证发现，供分析报告审查
        is_falsely_alerted = (smic["double_high_risk"] is True and smic["double_high_status"] == "存贷双高预警")
        if is_falsely_alerted:
            pytest.fail(
                f"实证缺陷发现: 华夏科创50重仓股 [中芯国际] 账面自由现金流健康 (fcf_billion=65.47 > 0)，"
                f"但因 v_stock_financials 缺失 ocf_per_share 且 portfolio_manager.py:3967 未联动 fcf_billion > 0，"
                f"被误判为 '存贷双高预警' 并扣除 40 分！"
            )


# ==============================================================================
# 3. 统一资产分类解析器对抗性测试 (Unified Asset Classifier Verification)
# ==============================================================================

class TestUnifiedAssetClassClassifier:
    """
    统一资产分类解析器 classify_fund_asset_class 对抗性压测：
    - 精准映射 9 大标准大类
    - 未知兜底为其他权益资产，严禁输出已废弃的“其他存量资产”
    - 类方法 / 实例方法 / 模块函数三态调用幂等性
    - A/C 同源拆单份额大类归属绝对一致
    """

    CANONICAL_9_CATEGORIES = {
        "纯债固收",
        "黄金对冲",
        "美股海外对冲",
        "A股红利高股息",
        "A股红利低波",
        "科技成长进攻",
        "中小盘成长",
        "中盘均衡",
        "核心蓝筹",
    }

    def test_canonical_9_categories_exhaustive(self, pm):
        """全面覆盖 9 大核心标准大类的标的映射"""
        test_cases = [
            # 1. 纯债固收
            ("002351", "易方达裕祥回报债券A", "纯债固收"),
            ("000086", "工银纯债债券A", "纯债固收"),
            ("003075", "国泰利享中短债A", "纯债固收"),
            ("000009", "易方达天天理财货币A", "纯债固收"),
            ("999101", "某某稳益信用债C", "纯债固收"),
            # 2. 黄金对冲
            ("000216", "华安黄金易ETF联接A", "黄金对冲"),
            ("000217", "华安黄金易ETF联接C", "黄金对冲"),
            ("159934", "易方达黄金ETF", "黄金对冲"),
            ("007983", "汇添富黄金及贵金属", "黄金对冲"),
            ("999102", "博时上海金ETF联接A", "黄金对冲"),
            # 3. 美股海外对冲
            ("050025", "博时标普500ETF联接A", "美股海外对冲"),
            ("001071", "摩根标普500指数A", "美股海外对冲"),
            ("160213", "国泰纳斯达克100", "美股海外对冲"),
            ("164906", "交银中证海外中国互联网", "美股海外对冲"),
            ("006327", "易方达恒生中国企业", "美股海外对冲"),
            ("000614", "华安德国30(DAX)ETF联接", "美股海外对冲"),
            ("000688", "华安日经225ETF联接", "美股海外对冲"),
            # 4. A股红利高股息
            ("100032", "富国中证红利指数增强A", "A股红利高股息"),
            ("008682", "富国中证红利指数增强C", "A股红利高股息"),
            ("090010", "大成中证红利指数A", "A股红利高股息"),
            ("999103", "万家红利成长混合A", "A股红利高股息"),
            # 5. A股红利低波
            ("005561", "创金合信红利低波动A", "A股红利低波"),
            ("005562", "创金合信红利低波动C", "A股红利低波"),
            ("007466", "华泰柏瑞中证红利低波动ETF联接A", "A股红利低波"),
            ("006450", "招商中证红利低波动ETF联接A", "A股红利低波"),
            # 6. 科技成长进攻
            ("011612", "华夏科创50ETF联接A", "科技成长进攻"),
            ("011613", "华夏科创50ETF联接C", "科技成长进攻"),
            ("013841", "银华集成电路混合C", "科技成长进攻"),
            ("007339", "易方达中证人工智能ETF联接A", "科技成长进攻"),
            ("001618", "天弘中证计算机主题ETF联接A", "科技成长进攻"),
            ("012414", "招商中证半导体产业ETF联接A", "科技成长进攻"),
            # 7. 中小盘成长
            ("016634", "富国中证1000ETF联接C", "中小盘成长"),
            ("018043", "易方达国证2000ETF联接A", "中小盘成长"),
            ("161022", "富国中证小盘指数", "中小盘成长"),
            ("002190", "农银汇理创业板", "中小盘成长"),
            # 8. 中盘均衡
            ("001053", "华夏中证500ETF联接C", "中盘均衡"),
            ("160119", "南方中证500ETF联接A", "中盘均衡"),
            ("012722", "招商中证A500ETF联接A", "中盘均衡"),
            ("022444", "华夏中证A500ETF联接A", "中盘均衡"),
            # 9. 核心蓝筹
            ("110003", "易方达上证50指数A", "核心蓝筹"),
            ("160706", "嘉实沪深300ETF联接A", "核心蓝筹"),
            ("000051", "华夏沪深300ETF联接A", "核心蓝筹"),
            ("001594", "天弘上证50ETF联接A", "核心蓝筹"),
        ]

        for code, name, expected_cat in test_cases:
            actual_cat = pm.classify_fund_asset_class(code, name)
            assert actual_cat == expected_cat, (
                f"基金 [{code} {name}] 归类错误: 期望 '{expected_cat}', 实际得到 '{actual_cat}'"
            )
            assert actual_cat in self.CANONICAL_9_CATEGORIES

    def test_sp_china_a_dividend_edge_case(self, pm):
        """
        对抗性边缘测试：标普中国A股红利机会指数基金 (501029 华宝标普中国A股红利机会)
        属于纯正的 A 股红利高股息资产，检验解析器是否被 '标普' 关键词误导识别为 '美股海外对冲'。
        """
        cat = pm.classify_fund_asset_class("501029", "华宝标普中国A股红利机会")
        if cat == "美股海外对冲":
            pytest.fail(
                "实证缺陷发现: 501029 [华宝标普中国A股红利机会] 为纯正 A 股高股息红利基金，"
                "但因匹配顺序中 '标普' 优先于 '红利' 且未排除 'A股/中国A股'，被错误归类为 '美股海外对冲'！"
            )
        assert cat == "A股红利高股息"

    def test_unclassified_fallback_and_no_deprecated_asset_class(self, pm):
        """
        测试边缘未入围基金（医药/消费/新能源/未知代码/空输入）：
        必须兜底为 '其他权益资产'，绝对严禁出现已废弃的 '其他存量资产'
        """
        edge_cases = [
            ("003095", "中欧医疗健康混合A"),
            ("000248", "汇添富消费行业混合"),
            ("001632", "天弘中证新能源汽车"),
            ("999999", "未知神秘基金"),
            ("888888", None),
            (None, "未知多因子量化选股基金"),
            ("", ""),
            (None, None),
        ]

        for code, name in edge_cases:
            res = pm.classify_fund_asset_class(code, name)
            assert res == "其他权益资产", (
                f"输入 [{code}, {name}] 未能兜底为 '其他权益资产', 而是得到 '{res}'"
            )
            assert res != "其他存量资产", "严重违规：输出了已废弃的 '其他存量资产'！"

    def test_polymorphic_invocations_consistency(self, pm):
        """测试多态调用形式一致性（实例方法、类方法、模块函数）"""
        test_codes = ["002351", "000216", "050025", "100032", "005561", "011613", "016634", "001053", "110003", "999999"]
        for c in test_codes:
            cat_inst = pm.classify_fund_asset_class(c)
            cat_cls = PortfolioManager.classify_fund_asset_class(c)
            cat_mod = classify_fund_asset_class(c)
            assert cat_inst == cat_cls == cat_mod, (
                f"调用形式输出不一致: inst={cat_inst}, cls={cat_cls}, mod={cat_mod} for code {c}"
            )

    def test_companion_split_shares_identical_classification(self, pm):
        """测试 A/C 同源拆单伴生份额必须具有 100% 相同的大类归属"""
        pairs = [
            ("050025", "001071", "美股海外对冲"),
            ("100032", "008682", "A股红利高股息"),
            ("005561", "005562", "A股红利低波"),
            ("011612", "011613", "科技成长进攻"),
            ("000216", "000217", "黄金对冲"),
        ]
        for c1, c2, expected_cat in pairs:
            cat1 = pm.classify_fund_asset_class(c1)
            cat2 = pm.classify_fund_asset_class(c2)
            assert cat1 == cat2 == expected_cat, (
                f"同源份额归类不一致: {c1}->{cat1}, {c2}->{cat2}, 期望={expected_cat}"
            )


# ==============================================================================
# 4. 高频批量与极端入参压力测试 (High-Throughput & Boundary Stress Testing)
# ==============================================================================

def test_batch_classification_throughput_cached(pm):
    """
    压力测试：对已入库/核心池基金批量执行 1,000 次分类解析，验证内存响应能力 (耗时 < 100ms)
    """
    import time
    pool = ["002351", "000216", "050025", "100032", "005561", "011613", "016634", "001053", "110020"]
    t0 = time.perf_counter()
    for i in range(1000):
        c = pool[i % len(pool)]
        pm.classify_fund_asset_class(c)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert elapsed_ms < 100.0, f"核心池1000次资产归类耗时过长: {elapsed_ms:.1f}ms (阈值 100ms)"
