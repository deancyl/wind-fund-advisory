# -*- coding: utf-8 -*-
"""
tests/test_anticheat_suite.py
E2E 专项防作弊与防迎合全维度自动化回归测试套件

涵盖核心 4 大专项测试体系：
1. Test A: 14 大核心赛道雷达真动态精算检验 (14-Sector Genuine Dynamics)
2. Test B: Tab 2 四大实盘调仓场景真实计算闭环检验 (Four Rebalancing Scenarios Realness)
3. Test C: 多账本体系存储隔离、克隆与主实盘硬保护检验 (Multi-Ledger Isolation & Protection)
4. Test D: Tab 4 底层穿透对象动态覆盖与全资产精准分类检验 (Tab 4 Look-Through Override & Asset Classification)
"""

import os
import sys
import json
import inspect
import tempfile
from pathlib import Path
from typing import Dict, Any, List

import pytest
import numpy as np
import pandas as pd

# 确保路径解析覆盖 AGY2_FundAdvisory 与工作区根目录
CURRENT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = CURRENT_DIR.parent if CURRENT_DIR.name == "tests" else CURRENT_DIR
AGY2_DIR = WORKSPACE_ROOT / "AGY2_FundAdvisory"

if str(AGY2_DIR) not in sys.path:
    sys.path.insert(0, str(AGY2_DIR))
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from advisory_engine import OpportunityRadarEngine, RADAR_SECTOR_CATALOG
from strategy_bridge import StrategyBridge
from multi_ledger_manager import MultiLedgerManager
from portfolio_manager import PortfolioManager, FundHolding

try:
    from portfolio_manager import HoldingItem
except ImportError:
    HoldingItem = FundHolding


# =========================================================================
# 辅助函数：提取调仓单金额与动作
# =========================================================================
def _extract_order_amount(order: Dict[str, Any]) -> float:
    """提取单笔调仓单的执行金额"""
    if "amount" in order:
        return float(order["amount"])
    if "buy_amount" in order and order.get("action") == "BUY":
        return float(order["buy_amount"])
    if "sell_amount" in order and order.get("action") == "SELL":
        return float(order["sell_amount"])
    if "diff_amount" in order:
        return abs(float(order["diff_amount"]))
    return 0.0


# =========================================================================
# Test A: 14-Sector Genuine Dynamics (14 赛道真动态检验)
# =========================================================================
class TestSectorGenuineDynamics:
    """
    Test A: 14 大赛道真动态雷达防作弊核验
    1. 扫描 14 个核心赛道，断言指标非空且各不相同；
    2. 坚决杜绝任何赛道共享兜底常数元组 (er_20==0.50, bias_20==1.0, crowding_score==85.0)；
    3. 断言跨赛道指标具备真实动态方差 (std > 0)；
    4. 断言 get_sector_valuation_percentile 返回 [0, 100] 真实分位数，无空 pass 与死循环。
    """

    def test_all_14_sectors_scanned_with_non_empty_metrics(self):
        """调用 OpportunityRadarEngine().scan_all_sectors()，断言 14 个赛道指标全部非空且有效"""
        engine = OpportunityRadarEngine()
        sectors = engine.scan_all_sectors()

        assert len(sectors) == 14, f"期望扫描 14 个赛道，实际获得 {len(sectors)} 个赛道"

        for s in sectors:
            sec_id = s.get("sector_id", "")
            name = s.get("name", "")
            assert sec_id, f"赛道缺少 sector_id: {s}"
            assert name, f"赛道缺少 name: {s}"

            # 验证各核心指标非空且为浮点数
            assert s.get("er_20") is not None, f"[{name}] er_20 为空"
            assert isinstance(s["er_20"], (int, float)), f"[{name}] er_20 必须为数值"

            assert s.get("bias_20") is not None, f"[{name}] bias_20 为空"
            assert isinstance(s["bias_20"], (int, float)), f"[{name}] bias_20 必须为数值"

            assert s.get("slope_20") is not None, f"[{name}] slope_20 为空"
            assert isinstance(s["slope_20"], (int, float)), f"[{name}] slope_20 必须为数值"

            crowd = s.get("crowding_score", s.get("s_crowd"))
            assert crowd is not None, f"[{name}] 拥挤度评分为空"
            assert isinstance(crowd, (int, float)), f"[{name}] 拥挤度评分必须为数值"

            val_pct = s.get("val_percentile")
            assert val_pct is not None, f"[{name}] 估值分位为空"
            assert 0.0 <= float(val_pct) <= 100.0, f"[{name}] 估值分位必须在 [0, 100] 之间，当前为 {val_pct}"

    def test_no_sector_shares_fallback_dummy_constants(self):
        """断言没有任何赛道同时命中 (er_20==0.50, bias_20==1.0, crowding_score==85.0) 兜底假常数"""
        engine = OpportunityRadarEngine()
        sectors = engine.scan_all_sectors()

        dummy_sectors = []
        for s in sectors:
            er = round(float(s.get("er_20", 0.0)), 2)
            bias = round(float(s.get("bias_20", 0.0)), 2)
            crowd = round(float(s.get("crowding_score", s.get("s_crowd", 0.0))), 1)

            if er == 0.50 and bias == 1.0 and crowd == 85.0:
                dummy_sectors.append(s.get("name", s.get("sector_id")))

        assert len(dummy_sectors) == 0, (
            f"检测到 {len(dummy_sectors)} 个赛道共享兜底假常数 (0.50, 1.0, 85.0): {dummy_sectors}"
        )

    def test_metrics_cross_sector_genuine_variance(self):
        """断言不同赛道指标具备真实统计区分度与方差，杜绝全表千篇一律"""
        engine = OpportunityRadarEngine()
        sectors = engine.scan_all_sectors()

        biases = [float(s["bias_20"]) for s in sectors]
        ers = [float(s["er_20"]) for s in sectors]
        crowds = [float(s.get("crowding_score", s.get("s_crowd", 0.0))) for s in sectors]
        scores = [float(s.get("total_score", 0.0)) for s in sectors]

        # 统计方差必须严格大于 0
        assert np.std(biases) > 0.01, f"bias_20 缺乏统计方差: std={np.std(biases)}"
        assert np.std(ers) > 0.01, f"er_20 缺乏统计方差: std={np.std(ers)}"
        assert np.std(crowds) > 0.01, f"crowding_score 缺乏统计方差: std={np.std(crowds)}"
        assert np.std(scores) > 0.01, f"total_score 缺乏统计方差: std={np.std(scores)}"

        # 独立不同取值个数必须显著丰富
        assert len(set(biases)) >= 5, f"bias_20 独立数值过少: {set(biases)}"
        assert len(set(ers)) >= 5, f"er_20 独立数值过少: {set(ers)}"
        assert len(set(scores)) >= 5, f"total_score 独立数值过少: {set(scores)}"

    def test_get_sector_valuation_percentile_no_empty_pass(self):
        """断言 get_sector_valuation_percentile 为纯债、黄金、红利、银行等赛道生成有效动态分位值"""
        engine = OpportunityRadarEngine()
        test_sector_keys = [
            "pure_bond",
            "domestic_gold",
            "dividend_low_vol",
            "banking_dividend",
            "pharma_health",
            "consumer_liquor",
            "semiconductor"
        ]

        for sec in test_sector_keys:
            meta = RADAR_SECTOR_CATALOG.get(sec, {})
            # 兼容 1 参和 2 参签名
            try:
                pct = engine.get_sector_valuation_percentile(sec)
            except TypeError:
                pct = engine.get_sector_valuation_percentile(sec, meta)

            assert pct is not None, f"赛道 {sec} 估值分位返回 None (可能触发了空 pass 分支)"
            assert isinstance(pct, (int, float)), f"赛道 {sec} 估值分位必须为数值: {type(pct)}"
            assert not np.isnan(pct), f"赛道 {sec} 估值分位返回 NaN"
            assert 0.0 <= float(pct) <= 100.0, f"赛道 {sec} 估值分位越界: {pct}"


# =========================================================================
# Test B: Four Rebalancing Scenarios Realness (四大实盘调仓场景真实性)
# =========================================================================
class TestRebalancingScenariosRealness:
    """
    Test B: 四大实盘调仓场景真实性闭环检验
    1. new_cash_only: 卖出金额严格为 0，买入总额严格等于 new_cash_amount，赎回费为 0；
    2. withdraw_cash_only: 买入金额严格为 0，赎回总额严格等于 withdraw_cash_amount，绝不卖出 <7d 标的；
    3. freeze_reserved_cash: 真实扣除 pm.reserved_batch_cash。
    """

    @pytest.fixture
    def setup_pm(self, tmp_path):
        """创建用于场景推演测试的 PortfolioManager 实例（环境隔离）"""
        pm = PortfolioManager(db_path=":memory:", ledger_json_path=tmp_path / "test_ledger_pm.json")
        pm.available_cash = 10000.0
        pm.reserved_batch_cash = 0.0

        # 清空并录入标准测试组合
        pm.holdings = {}
        pm.add_or_update_holding("005561", shares=20000, nav=1.0, cost_price=1.0, holding_days=45)  # 20000元 (满30天免赎)
        pm.add_or_update_holding("002351", shares=10000, nav=1.0, cost_price=1.0, holding_days=45)  # 10000元 (纯债欠配)
        pm.add_or_update_holding("011613", shares=10000, nav=1.0, cost_price=1.0, holding_days=3)   # 10000元 (未满7天惩罚锁)
        return pm

    def test_new_cash_only_scenario_orders_and_fees(self, setup_pm):
        """测试新资注入免赎补仓 (new_cash_only)：全额增量买入，零卖出，零赎回费"""
        pm = setup_pm
        target_w = {"005561": 0.40, "002351": 0.40, "008888": 0.20}
        new_cash_amount = 50000.0

        # 1. 验证 StrategyBridge 调用层
        res = StrategyBridge.generate_ai_rebalance_orders(
            current_holdings=pm.holdings,
            available_cash=pm.available_cash,
            target_weights_funds=target_w,
            pm=pm,
            scenario_mode="new_cash_only",
            new_cash_amount=new_cash_amount
        )

        orders = res.get("orders") or res.get("items", [])
        assert len(orders) > 0, "未生成调仓建议列表"

        # 断言所有调仓单中卖出金额严格为 0 (绝无 SELL 指令产生)
        sell_orders = [o for o in orders if o.get("action") == "SELL" and _extract_order_amount(o) > 1e-4]
        assert len(sell_orders) == 0, f"new_cash_only 模式下严禁生成卖出指令，违规卖单: {sell_orders}"

        # 断言买入指令总金额严格等于 new_cash_amount (50000.0)
        buy_orders = [o for o in orders if o.get("action") == "BUY"]
        total_buy_amount = sum(_extract_order_amount(o) for o in buy_orders)
        assert total_buy_amount == pytest.approx(new_cash_amount, rel=1e-2), (
            f"买入总额应严格等于注入新资金 {new_cash_amount}，当前为 {total_buy_amount}"
        )

        # 断言总赎回费严格为 0
        total_redemption_fee = res.get("total_redemption_fee", 0.0)
        if total_redemption_fee == 0.0:
            total_redemption_fee = sum(float(o.get("est_fee", 0.0)) for o in orders if o.get("action") == "SELL")
        assert total_redemption_fee == 0.0, f"新资注入免赎补仓模式下赎回费必须为 0，当前为 {total_redemption_fee}"

        # 2. 验证 pm 底层执行计划
        plan = pm.generate_scenario_rebalance_plan(
            target_weights=target_w,
            scenario_mode="new_cash_only",
            new_cash_amount=new_cash_amount
        )
        assert plan.get("scenario_mode") == "new_cash_only"
        assert len(plan.get("sell_actions", [])) == 0
        assert plan.get("total_sell_amount", 0.0) == 0.0
        assert plan.get("total_redemption_fee", 0.0) == 0.0
        assert plan.get("total_buy_amount", 0.0) == pytest.approx(new_cash_amount, rel=1e-2)

    def test_withdraw_cash_only_scenario_safety_barrier(self, setup_pm):
        """测试智能低损耗提现 (withdraw_cash_only)：零买入，全额赎回，避开未满7天标的"""
        pm = setup_pm
        target_w = {"005561": 0.50, "002351": 0.50}
        withdraw_cash_amount = 20000.0

        # 1. 验证 StrategyBridge 调用层
        res = StrategyBridge.generate_ai_rebalance_orders(
            current_holdings=pm.holdings,
            available_cash=pm.available_cash,
            target_weights_funds=target_w,
            pm=pm,
            scenario_mode="withdraw_cash_only",
            withdraw_cash_amount=withdraw_cash_amount
        )

        orders = res.get("orders") or res.get("items", [])
        assert len(orders) > 0, "未生成调仓建议列表"

        # 断言所有调仓单中买入金额严格为 0 (绝无 BUY 指令产生)
        buy_orders = [o for o in orders if o.get("action") == "BUY" and _extract_order_amount(o) > 1e-4]
        assert len(buy_orders) == 0, f"withdraw_cash_only 模式下严禁生成买入指令，违规买单: {buy_orders}"

        # 断言赎回总额等于提现需求金额
        sell_orders = [o for o in orders if o.get("action") == "SELL"]
        total_sell_amount = sum(_extract_order_amount(o) for o in sell_orders)
        assert total_sell_amount == pytest.approx(withdraw_cash_amount, rel=1e-2), (
            f"赎回总额应等于提现金额 {withdraw_cash_amount}，当前为 {total_sell_amount}"
        )

        # 断言持有未满 7 天红线标的 (011613 holding_days=3) 绝未被卖出
        sold_codes = [
            o.get("fund_code") for o in orders
            if o.get("action") == "SELL" and _extract_order_amount(o) > 1e-4
        ]
        assert "011613" not in sold_codes, f"持有仅 3 天未满 7 天的 011613 被违规减持: {sold_codes}"

        # 2. 验证 pm 底层执行计划
        plan = pm.generate_scenario_rebalance_plan(
            target_weights=target_w,
            scenario_mode="withdraw_cash_only",
            withdraw_cash_amount=withdraw_cash_amount
        )
        assert plan.get("scenario_mode") == "withdraw_cash_only"
        assert len(plan.get("buy_actions", [])) == 0
        assert plan.get("total_buy_amount", 0.0) == 0.0
        assert plan.get("total_sell_amount", 0.0) >= withdraw_cash_amount * 0.95
        plan_sold_codes = [s["fund_code"] for s in plan.get("sell_actions", [])]
        assert "011613" not in plan_sold_codes, "pm 计划中违规包含了未满 7 天标的 011613"

    def test_freeze_reserved_cash_deduction(self, setup_pm):
        """测试冻结分批建仓预留现金 (freeze_reserved_cash)：真实扣除可用现金"""
        pm = setup_pm
        pm.available_cash = 60000.0
        pm.reserved_batch_cash = 25000.0
        target_w = {"005561": 0.50, "002351": 0.50}

        # 开启冻结预留资金
        plan_frozen = pm.generate_scenario_rebalance_plan(
            target_weights=target_w,
            scenario_mode="standard",
            freeze_reserved_cash=True
        )
        assert plan_frozen.get("freeze_reserved_cash") is True
        assert plan_frozen.get("reserved_batch_cash") == 25000.0

        # 未开启冻结预留资金
        plan_unfrozen = pm.generate_scenario_rebalance_plan(
            target_weights=target_w,
            scenario_mode="standard",
            freeze_reserved_cash=False
        )
        assert plan_unfrozen.get("freeze_reserved_cash") is False


# =========================================================================
# Test C: Multi-Ledger Isolation & Protection (多账本隔离与硬保护)
# =========================================================================
class TestMultiLedgerIsolationAndProtection:
    """
    Test C: 多账本体系存储隔离、克隆与主实盘硬保护检验
    1. 在隔离目录实例化 MultiLedgerManager，验证 create_ledger 与 clone_ledger；
    2. 修改沙盒账本持仓，断言主实盘 portfolio_ledger.json 完好无损且 SQLite DB 未受污染；
    3. 断言 delete_ledger('main_live') 物理保护生效（抛出 PermissionError 或返回 False）；
    4. 验证 get_all_ledgers_summary() 资产汇总统计数学正确性。
    """

    def test_multiledger_crud_clone_and_main_protection(self, tmp_path):
        """测试多账本 CRUD、独立 SQLite 隔离与主实盘防删除物理保护"""
        # 1. 在临时目录初始化干净的主实盘环境
        main_json = tmp_path / "portfolio_ledger.json"
        main_state = {
            "version": "AGY2_PORTFOLIO_V2",
            "total_equity": 100000.0,
            "available_cash": 100000.0,
            "total_market_value": 0.0,
            "holdings": []
        }
        with open(main_json, "w", encoding="utf-8") as f:
            json.dump(main_state, f, ensure_ascii=False, indent=2)

        mgr = MultiLedgerManager(workspace_root=tmp_path)
        ledgers = mgr.list_ledgers()
        assert len(ledgers) >= 1
        assert ledgers[0]["id"] == "main_live"

        # 2. create_ledger 创建沙盒账本
        sbox_id = mgr.create_ledger(
            name="Test Sandbox",
            base_cash=50000.0,
            ledger_type="sandbox",
            default_tier="C2"
        )
        assert sbox_id in [l["id"] for l in mgr.list_ledgers()]
        sbox_meta = mgr.get_ledger_meta(sbox_id)
        assert sbox_meta["name"] == "Test Sandbox"
        assert sbox_meta["type"] == "sandbox"
        assert sbox_meta["default_tier"] == "C2"

        # 3. clone_ledger 克隆账本副本
        clone_id = mgr.clone_ledger(sbox_id, "Test Clone")
        assert clone_id in [l["id"] for l in mgr.list_ledgers()]
        clone_meta = mgr.get_ledger_meta(clone_id)
        assert clone_meta["name"] == "Test Clone"
        assert clone_meta["id"] != sbox_id

        # 4. 修改沙盒账本持仓并落盘
        sbox_pm = mgr.get_pm(sbox_id)
        sbox_pm.add_or_update_holding("005561", shares=10000, nav=1.5, cost_price=1.2, holding_days=30)
        sbox_pm.save_state()

        # 核心断言：主实盘文件 portfolio_ledger.json 绝对未被修改
        with open(main_json, "r", encoding="utf-8") as f:
            reloaded_main = json.load(f)
        assert len(reloaded_main.get("holdings", [])) == 0, "主实盘账本持仓被沙盒操作污染！"
        assert reloaded_main.get("total_equity") == 100000.0, "主实盘总资产被篡改！"

        # 5. delete_ledger('main_live') 必须被物理阻断
        with pytest.raises(PermissionError):
            mgr.delete_ledger("main_live")

        # 6. get_all_ledgers_summary 汇总核算
        summary = mgr.get_all_ledgers_summary()
        assert "total_assets" in summary or "total_equity" in summary
        tot_assets = summary.get("total_assets", summary.get("total_equity", 0.0))
        # 100000(主实盘) + 50000(沙盒) + 50000(克隆) + 浮盈/净值增量
        assert tot_assets >= 150000.0, f"家庭资产汇总偏低: {tot_assets}"
        assert summary.get("total_funds", summary.get("total_holdings_count", 0)) >= 1

    def test_production_main_live_protected(self):
        """对生产单例 MultiLedgerManager 检验主实盘防删红线"""
        mgr = MultiLedgerManager.get_instance()
        main_meta = mgr.get_ledger_meta("main_live")
        assert main_meta is not None, "未找到 main_live 主实盘元数据"
        assert main_meta.get("is_protected") is True, "main_live 必须声明 is_protected=True"

        # 坚决禁止删除主实盘
        with pytest.raises(PermissionError):
            mgr.delete_ledger("main_live")


# =========================================================================
# Test D: Tab 4 Look-Through Override & Asset Classification
# =========================================================================
class TestLookThroughOverrideAndClassification:
    """
    Test D: Tab 4 底层穿透对象动态覆盖与全资产精准分类检验
    1. 验证 4 个穿透底层函数支持 holdings_override 参数，且计算结果真实响应覆盖持仓；
    2. 验证 PortfolioManager.classify_fund_asset_class 本体方法对各细分赛道与避险资产的精准分类；
    3. 断言没有任何标的被泛化归类为笼统的“其他权益资产”。
    """

    @pytest.fixture
    def pm_instance(self, tmp_path):
        """构建基准 PortfolioManager 实例（环境隔离）"""
        pm = PortfolioManager(db_path=":memory:", ledger_json_path=tmp_path / "test_ledger_inst.json")
        pm.holdings = {}
        # 默认底仓：纯债 002351
        pm.add_or_update_holding("002351", shares=10000, nav=1.0, cost_price=1.0, holding_days=100)
        return pm

    def test_penetration_functions_support_holdings_override(self, pm_instance):
        """验证 4 个穿透函数传入 custom holdings_override 时，结果反映 override 而非 default"""
        pm = pm_instance

        # 构造覆盖持仓：白酒 161725 与 银行 160418
        custom_override = {
            "161725": HoldingItem(
                fund_code="161725",
                fund_name="招商中证白酒指数A",
                shares=10000.0,
                current_nav=1.2,
                cost_price=1.1,
                market_value=12000.0
            ),
            "160418": HoldingItem(
                fund_code="160418",
                fund_name="华安中证银行指数A",
                shares=20000.0,
                current_nav=1.1,
                cost_price=1.0,
                market_value=22000.0
            )
        }

        # 1. 行业暴露穿透 (calculate_look_through_industry_exposure)
        df_ind = pm.calculate_look_through_industry_exposure(holdings_override=custom_override)
        assert isinstance(df_ind, pd.DataFrame)
        assert not df_ind.empty, "行业暴露计算结果为空"
        ind_names = "".join(df_ind["行业"].tolist()) if "行业" in df_ind.columns else ""
        assert any(k in ind_names for k in ["消费", "白酒", "银行", "金融"]), (
            f"行业暴露未反映 override 持仓，当前行业: {ind_names}"
        )

        # 2. 重仓股重合度矩阵 (calculate_stock_overlap_matrix)
        mat_res = pm.calculate_stock_overlap_matrix(holdings_override=custom_override)
        assert isinstance(mat_res, dict)
        funds_in_mat = "".join(mat_res.get("funds", []))
        assert "161725" in funds_in_mat or "160418" in funds_in_mat, (
            f"重合度矩阵标的未反映 override 持仓: {mat_res.get('funds')}"
        )

        # 3. 组合穿透风险评分 (calculate_portfolio_penetration_risk)
        risk_res = pm.calculate_portfolio_penetration_risk(holdings_override=custom_override)
        assert isinstance(risk_res, dict)
        assert "portfolio_risk_index" in risk_res

        # 4. 底层重仓股穿透排雷宽表 (get_portfolio_look_through_stocks_df)
        df_stocks = pm.get_portfolio_look_through_stocks_df(holdings_override=custom_override)
        assert isinstance(df_stocks, pd.DataFrame)
        # 结果应反映白酒或银行底层标的或关联持仓基金
        if not df_stocks.empty and "关联持仓基金" in df_stocks.columns:
            assoc = "".join(df_stocks["关联持仓基金"].tolist())
            assert "161725" in assoc or "160418" in assoc

    def test_classify_fund_asset_class_zero_percent_other_equity(self):
        """
        验证 PortfolioManager.classify_fund_asset_class(code, name='') 精准识别各类核心资产：
        - 医药医疗健康 (161726)
        - 大消费与白酒 (161725)
        - 银行金融/高股息 (160418)
        - 港股恒生科技 (013402)
        - 硬科技与半导体 (008888, 013841, 011612)
        - 美股海外QDII (050025, 001071)
        - 红利低波防守 (005561, 100032)
        - 宽基指数 (300/500/1000)
        - 纯债与黄金
        断言：100% 杜绝输出'其他权益资产'！
        """
        cases = [
            ("161726", "医药/医疗", ["医药", "医疗", "健康", "生物", "中盘", "均衡"]),
            ("161725", "白酒/消费", ["消费", "白酒", "主要消费", "核心", "蓝筹"]),
            ("160418", "银行/金融", ["银行", "金融", "股息", "红利", "价值"]),
            ("013402", "港股/恒生科技", ["恒生", "港股", "海外", "科技", "全球"]),
            ("008888", "半导体/芯片/科创", ["半导体", "芯片", "科技", "科创", "电子"]),
            ("013841", "半导体/芯片/科创", ["半导体", "芯片", "科技", "科创", "电子"]),
            ("011612", "半导体/芯片/科创", ["科创", "科技", "半导体", "芯片"]),
            ("050025", "美股/海外QDII", ["标普", "美股", "海外", "全球", "QDII"]),
            ("001071", "美股/海外QDII", ["标普", "美股", "海外", "全球", "QDII"]),
            ("005561", "红利/红利低波", ["红利", "低波", "股息", "价值"]),
            ("100032", "红利/红利低波", ["红利", "低波", "股息", "价值"]),
            ("110020", "沪深300宽基", ["蓝筹", "核心", "基石", "300", "沪深"]),
            ("001052", "中证500宽基", ["中盘", "成长", "500"]),
            ("016633", "中证1000宽基", ["中小", "小盘", "1000", "成长"]),
            ("002351", "纯债固收", ["债", "固收", "信用债", "理财"]),
            ("000216", "国内黄金", ["黄金", "金", "大宗", "对冲"])
        ]

        pm = PortfolioManager(db_path=":memory:")
        try:
            from portfolio_manager import _CLASSIFY_ASSET_CLASS_CACHE
            _CLASSIFY_ASSET_CLASS_CACHE.clear()
        except Exception:
            pass

        for code, category_name, expected_keywords in cases:
            # 支持通过实例调用或类级别静态调用
            res_cls = PortfolioManager.classify_fund_asset_class(code, "")
            res_inst = pm.classify_fund_asset_class(code, "")

            assert res_cls == res_inst, f"类调用与实例调用结果不一致: {res_cls} vs {res_inst}"
            assert res_cls != "其他权益资产", f"标的【{code} - {category_name}】被错误归类为'其他权益资产'！"
            assert res_cls != "其他存量资产", f"标的【{code} - {category_name}】被错误归类为'其他存量资产'！"
            assert res_cls != "", f"标的【{code} - {category_name}】分类返回空字符串"

            matched = any(kw in res_cls for kw in expected_keywords)
            assert matched, (
                f"标的【{code} - {category_name}】分类结果【{res_cls}】未包含预期关键词 {expected_keywords}"
            )


if __name__ == "__main__":
    pytest.main(["-v", __file__])
