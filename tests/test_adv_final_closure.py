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


    def test_specialized_5_ledgers_clean_and_main_live_intact(self):
        """
        专项测试 5 (账本目录纯净度与主实盘示范持仓完整性校验):
        1. 验证 data/ledgers_index.json 中无历史测试遗留的垃圾沙盒账本；
        2. 验证 portfolio_ledger.json 主实盘完好存在，包含至少 6 只核心优质示范基金且总资产达到基准 ¥100,000。
        """
        index_file = WORKSPACE_ROOT / "data" / "ledgers_index.json"
        assert index_file.exists(), "ledgers_index.json 不存在！"
        import json
        idx_data = json.loads(index_file.read_text(encoding="utf-8"))
        ledgers = idx_data.get("ledgers", [])
        
        # 严禁残留 sandbox_202611... 等历史残留垃圾账本
        junk_ledgers = [l["id"] for l in ledgers if l["id"].startswith("sandbox_202")]
        assert len(junk_ledgers) == 0, f"发现未清理的测试垃圾沙盒账本: {junk_ledgers}"
        
        # 验证 main_live 存在且受保护
        main_meta = next((l for l in ledgers if l["id"] == "main_live"), None)
        assert main_meta is not None, "缺少 main_live 主实盘账本登记！"
        
        # 验证 portfolio_ledger.json
        main_ledger_file = WORKSPACE_ROOT / "portfolio_ledger.json"
        assert main_ledger_file.exists(), "portfolio_ledger.json 缺失！"
        m_data = json.loads(main_ledger_file.read_text(encoding="utf-8"))
        assert m_data.get("total_equity", 0.0) >= 90000.0, f"主实盘总资产不足 9 万: {m_data.get('total_equity')}"
        holdings = m_data.get("holdings", [])
        h_codes = [h.get("fund_code") for h in holdings]
        for must_code in ["005561", "100032", "000216", "017436", "011613"]:
            assert must_code in h_codes, f"主实盘示范持仓缺少核心标的 {must_code}！"

    def test_specialized_6_resolve_fund_display_name_accuracy(self):
        """
        专项测试 6 (全局基金名称反查解析准确性，消灭代码复读 017436 017436):
        验证 resolve_fund_display_name 对 005561, 100032, 000216, 017436, 011613, 002351 等
        均能准确反查出真实中文基金名称，绝不返回原代码。
        """
        from app_gui import resolve_fund_display_name
        
        test_keywords = {
            "005561": ["创金合信", "红利"],
            "100032": ["富国", "红利"],
            "000216": ["华安", "黄金"],
            "017436": ["纳斯达克"],
            "011613": ["科创"],
            "002351": ["裕祥"],
            "518880": ["黄金"],
            "050025": ["标普"],
        }
        for code, kws in test_keywords.items():
            resolved = resolve_fund_display_name(code)
            assert resolved != code, f"代码 {code} 反查失败，返回了重复代码！"
            for kw in kws:
                assert kw in resolved, f"代码 {code} 反查结果 '{resolved}' 缺少关键字 '{kw}'！"

    def test_specialized_7_realtime_market_source_detection(self):
        """
        专项测试 7 (行情源状态实时判定修复校验):
        验证 DataLoader.fetch_market_turnover_and_sentiment 返回的结构带有 realtime 标识或东财实时源，
        且 app_gui.py 中有严密的 is_realtime_src 多重判定逻辑，杜绝误报离线兜底。
        """
        from data_loader import DataLoader
        res = DataLoader.fetch_market_turnover_and_sentiment()
        assert isinstance(res, dict)
        src = res.get("source", "")
        is_rt = res.get("is_realtime", False)
        # 只要联网能够拿到东财实时源，或者返回标记为 realtime
        assert is_rt is True or "realtime" in src.lower() or "eastmoney" in src.lower(), (
            f"fetch_market_turnover_and_sentiment 返回源非实时: source={src}, is_realtime={is_rt}"
        )
        
        gui_p = AGY2_DIR / "app_gui.py"
        src_text = gui_p.read_text(encoding="utf-8")
        assert "is_realtime_src" in src_text, "app_gui.py 缺少 is_realtime_src 判定变量！"
        assert "🟢 实时盘中源已连接" in src_text, "app_gui.py 缺少实时盘中源正常徽章！"

    def test_specialized_8_multi_ledger_wireup_tab3_and_tab4(self):
        """
        专项测试 8 (多账本体系全面打通 Tab 3 回测与 Tab 4 穿透下拉框):
        验证 app_gui.py 中 Tab 3 与 Tab 4 均已遍历 MultiLedgerManager 的所有账本，
        支持选择独立账本、新资建仓方案、拟调仓方案，并使用 resolve_fund_display_name 进行中文穿透。
        """
        gui_p = AGY2_DIR / "app_gui.py"
        src_text = gui_p.read_text(encoding="utf-8")
        
        # Tab 3 验证
        assert "选择回测对象 (已全面打通多账本体系)" in src_text, "Tab 3 未挂载多账本回测选择器！"
        assert "💼 当前激活账本" in src_text, "缺少当前激活账本置顶选项！"
        assert "跨账本双组合同屏 PK 对比" in src_text, "缺少跨账本 PK 对比功能！"
        
        # Tab 4 验证
        assert "选择当前穿透体检的组合对象 (已全面打通多账本体系)" in src_text, "Tab 4 未挂载多账本穿透选择器！"
        
        # 验证名称反查在 Tab 3 与 Tab 4 中的应用
        assert "resolve_fund_display_name(fc, t_pm)" in src_text or "resolve_fund_display_name(fcode, target_pm_for_names)" in src_text, (
            "Tab 3/Tab 4 中未调用 resolve_fund_display_name！"
        )
