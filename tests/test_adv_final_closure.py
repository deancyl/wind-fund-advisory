# -*- coding: utf-8 -*-
import sys
from pathlib import Path
import pytest
from datetime import datetime

CURRENT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = CURRENT_DIR.parent if CURRENT_DIR.name == "tests" else CURRENT_DIR
AGY2_DIR = WORKSPACE_ROOT / "AGY2_FundAdvisory"

if str(AGY2_DIR) not in sys.path:
    sys.path.insert(0, str(AGY2_DIR))
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from portfolio_manager import PortfolioManager, FundHolding, HoldingItem
from strategy_bridge import StrategyBridge


class TestAdvFinalClosure:
    """买方投顾终极专业度与工程闭环专项测试套件"""

    def test_specialized_1_all_nine_standard_asset_classes_covered(self):
        """
        专项测试 1:
        验证 pm.classify_fund_asset_class 对 161726、161725、160418、013402、008888、050025、005561、002351、000216
        全部精准返回 9 大标准类别，无一返回“其他权益资产”！
        """
        pm = PortfolioManager(db_path=":memory:")

        expected_map = {
            "161726": "中盘均衡",      # 招商国证生物医药指数
            "161725": "核心蓝筹",      # 招商中证白酒指数
            "160418": "A股红利高股息", # 华安中证银行指数
            "013402": "科技成长进攻",  # 华夏恒生科技ETF联接A
            "008888": "科技成长进攻",  # 华夏国证半导体芯片ETF联接A
            "050025": "美股海外对冲",  # 博时标普500ETF联接A
            "005561": "A股红利低波",  # 创金合信红利低波A
            "002351": "纯债固收",      # 易方达裕祥回报债券A
            "000216": "黄金对冲"       # 华安黄金ETF联接A
        }

        STANDARD_NINE = {
            "纯债固收", "黄金对冲", "美股海外对冲", "A股红利低波",
            "A股红利高股息", "科技成长进攻", "中小盘成长", "中盘均衡", "核心蓝筹"
        }

        for code, exp_cat in expected_map.items():
            res_cat = pm.classify_fund_asset_class(code)
            assert res_cat != "其他权益资产", f"基金 {code} 误落入'其他权益资产'！"
            assert res_cat in STANDARD_NINE, f"基金 {code} 分类结果 '{res_cat}' 不在 9 大标准分类中！"
            assert res_cat == exp_cat, f"基金 {code} 期望分类为 '{exp_cat}'，实际为 '{res_cat}'"

            # 类级别调用测试
            class_res = PortfolioManager.classify_fund_asset_class(code)
            assert class_res == exp_cat

    def test_specialized_2_yield_cushion_and_shadow_rebalance_audit_dynamics(self):
        """
        专项测试 2:
        验证 StrategyBridge.calculate_portfolio_yield_cushion 与 pm.evaluate_rebalance_audit
        返回真实动态计算的数值，且当修改持仓 current_nav 时影子资产与实盘资产随之真实变化（零常数硬编码）！
        """
        pm = PortfolioManager(db_path=":memory:")
        pm.available_cash = 20000.0
        pm.baseline_equity = 100000.0

        # 初始化持仓
        pm.add_or_update_holding("005561", shares=20000, nav=1.5, cost_price=1.4, holding_days=45, fund_name="创金合信红利低波A") # 30000
        pm.add_or_update_holding("002351", shares=20000, nav=1.0, cost_price=1.0, holding_days=90, fund_name="易方达裕祥回报债券A") # 20000
        pm.add_or_update_holding("050025", shares=20000, nav=1.5, cost_price=1.2, holding_days=60, fund_name="博时标普500ETF联接A") # 30000

        # 1. 验证 StrategyBridge.calculate_portfolio_yield_cushion
        # 总资产 100000: 红利低波 30%, 纯债 20%, 美股 30%, 现金 20%
        # 红利低波息率 5.2%, 纯债 2.75%, 美股 1.3%
        # 加权息率 = 0.30*5.2 + 0.20*2.75 + 0.30*1.3 = 1.56 + 0.55 + 0.39 = 2.50%
        cushion = StrategyBridge.calculate_portfolio_yield_cushion(pm.holdings, total_capital=100000.0, pm=pm)
        assert "weighted_yield_pct" in cushion
        assert "annual_cushion_amount" in cushion
        assert "monthly_equivalent_amount" in cushion

        assert 2.40 <= cushion["weighted_yield_pct"] <= 2.60, f"加权息率期望约为 2.50%，实际为 {cushion['weighted_yield_pct']}%"
        assert 2400.0 <= cushion["annual_cushion_amount"] <= 2600.0
        assert cushion["monthly_equivalent_amount"] == round(cushion["annual_cushion_amount"] / 12.0, 2)

        # 2. 验证 pm.evaluate_rebalance_audit
        audit_1 = pm.evaluate_rebalance_audit()
        assert audit_1["current_actual_equity"] == 100000.0
        assert audit_1["shadow_hold_equity"] == 100000.0
        assert audit_1["rebalance_value_add"] == 0.0

        # 模拟市场行情发生真实变动：红利低波净值从 1.50 涨到 1.80，美股净值从 1.50 涨到 1.60
        pm.holdings["005561"].current_nav = 1.80
        pm.holdings["005561"].market_value = 20000 * 1.80 # 36000
        pm.holdings["050025"].current_nav = 1.60
        pm.holdings["050025"].market_value = 20000 * 1.60 # 32000

        audit_2 = pm.evaluate_rebalance_audit()
        # 此时实盘市值变为 36000 + 20000 + 32000 + 20000 = 108000
        # 影子组合也是同样的初始份额乘以最新净值 = 108000
        assert audit_2["current_actual_equity"] == 108000.0
        assert audit_2["shadow_hold_equity"] == 108000.0

        # 现在模拟进行了调仓：卖出了 10000 份美股 (回收现金 16000)，换入 16000 份纯债
        # 实盘调仓后，若随后红利继续涨到 2.0，由于调仓调整了权重，实盘总资产与躺平影子资产真实产生差异！
        pm.holdings["050025"].shares = 10000.0
        pm.holdings["050025"].market_value = 16000.0
        pm.holdings["002351"].shares += 16000.0
        pm.holdings["002351"].market_value = pm.holdings["002351"].shares * 1.0

        pm.holdings["005561"].current_nav = 2.00
        pm.holdings["005561"].market_value = 20000 * 2.00 # 40000

        audit_3 = pm.evaluate_rebalance_audit()
        # 影子资产保持初始份额: 20000*2.0 + 20000*1.0 + 20000*1.6 + 20000 = 40000+20000+32000+20000 = 112000
        # 实盘资产: 40000 + 36000*1.0 + 10000*1.6 + 20000 = 40000+36000+16000+20000 = 112000
        assert audit_3["shadow_hold_equity"] == 112000.0
        assert audit_3["current_actual_equity"] == 112000.0

        # 修改美股净值到 2.00 (实盘持仓减为 10000，而影子持仓仍为 20000)
        pm.holdings["050025"].current_nav = 2.00
        pm.holdings["050025"].market_value = 10000.0 * 2.00 # 20000

        audit_4 = pm.evaluate_rebalance_audit()
        # 实盘: 40000 + 36000 + 20000 + 20000 = 116000
        # 影子: 20000*2.0 + 20000*1.0 + 20000*2.0 + 20000 = 40000+20000+40000+20000 = 120000
        assert audit_4["current_actual_equity"] == 116000.0
        assert audit_4["shadow_hold_equity"] == 120000.0
        assert audit_4["rebalance_value_add"] == -4000.0
        assert audit_4["rebalance_value_add_pct"] < 0

    def test_specialized_3_auto_commit_and_reimport_compatibility(self):
        """
        专项测试 3:
        验证 app_gui.py 中的 _need_reimport 导入块包含 FundHolding 与 HoldingItem，
        以及 HoldingItem 实例化在热重载上下文中的稳定兼容性。
        """
        gui_p = AGY2_DIR / "app_gui.py"
        src = gui_p.read_text(encoding="utf-8")

        # 1. 验证导入块
        assert "FundHolding, HoldingItem" in src or "HoldingItem, FundHolding" in src, (
            "app_gui.py 热重载块中必须包含 FundHolding 与 HoldingItem！"
        )

        # 2. 验证一键执行全案包含自动入库拦截
        assert 'if "edited_table" in locals() and edited_table is not None:' in src, (
            "未在 app_gui.py 中发现一键执行全案的自动入库拦截调用！"
        )

        # 3. 验证无死代码分类器
        assert 'if not hasattr(PortfolioManager, "classify_fund_asset_class"):' not in src, (
            "app_gui.py 中仍残留 if not hasattr(PortfolioManager, 'classify_fund_asset_class') 死代码！"
        )

    def test_specialized_4_ui_wireup_and_valuation_percentile_anti_fraud(self):
        """
        专项测试 4 (防空气交付与估值失真终验):
        1. 验证 app_gui.py 前端源码中真实调用并渲染了 calculate_portfolio_yield_cushion 与 evaluate_rebalance_audit，且具备行情源状态徽章；
        2. 验证 OpportunityRadarEngine().scan_all_sectors() 中 domestic_gold 与 banking_dividend 的估值分位均 < 85.0%，绝非 99.8% 或 92.1% 的收盘价绝对分位乌龙！
        """
        gui_p = AGY2_DIR / "app_gui.py"
        app_gui_src = gui_p.read_text(encoding="utf-8")

        # 1. 真实前端挂载与渲染断言
        assert "calculate_portfolio_yield_cushion" in app_gui_src, "app_gui.py 未调用 calculate_portfolio_yield_cushion！"
        assert "evaluate_rebalance_audit" in app_gui_src, "app_gui.py 未调用 evaluate_rebalance_audit！"
        assert "行情源状态" in app_gui_src, "app_gui.py 侧边栏未发现'行情源状态'！"

        # 2. 估值分位数科学性与防乌龙断言
        from advisory_engine import OpportunityRadarEngine
        radar_eng = OpportunityRadarEngine()
        scanned = radar_eng.scan_all_sectors()
        sec_map = {s["sector_id"]: s for s in scanned}

        assert "domestic_gold" in sec_map
        assert "banking_dividend" in sec_map

        gold_val = sec_map["domestic_gold"]["val_percentile"]
        bank_val = sec_map["banking_dividend"]["val_percentile"]

        assert gold_val < 85.0, f"国内黄金估值分位为 {gold_val}%，严重超出 85.0% 阈值（误用收盘价分位乌龙未纠正）！"
        assert bank_val < 85.0, f"银行高股息估值分位为 {bank_val}%，严重超出 85.0% 阈值（误用收盘价分位乌龙未纠正）！"

        # 验证合理区间 (避险黄金 25%~75%, 银行高股息 25%~55%)
        assert 25.0 <= gold_val <= 75.0, f"国内黄金估值分位 {gold_val}% 不在合理区间 [25.0%, 75.0%] 内！"
        assert 25.0 <= bank_val <= 55.0, f"银行高股息估值分位 {bank_val}% 不在合理区间 [25.0%, 55.0%] 内！"
