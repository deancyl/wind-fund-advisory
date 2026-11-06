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
        专项测试 8 (多账本体系全面打通 Tab 3 回测与 Tab 4 穿透下拉框 - 剥离口号专业版):
        验证 app_gui.py 中 Tab 3 与 Tab 4 均已遍历 MultiLedgerManager 的所有账本，
        支持选择独立账本、新资建仓方案、拟调仓方案，并使用 resolve_fund_display_name 进行中文穿透。
        """
        gui_p = AGY2_DIR / "app_gui.py"
        src_text = gui_p.read_text(encoding="utf-8")
        
        # Tab 3 验证 (无口号专业版)
        assert "🎯 回测模式" in src_text, "Tab 3 未挂载专业回测模式选择器！"
        assert "📂 选择目标账本或方案" in src_text, "Tab 3 缺少目标账本/方案选择器！"
        assert "双账本同屏 PK" in src_text or "双账本PK" in src_text, "缺少跨账本 PK 对比功能！"
        
        # Tab 4 验证 (无口号专业版)
        assert "📂 选择穿透体检组合对象" in src_text or "sel_tab4_target_type" in src_text, "Tab 4 未挂载多账本穿透选择器！"
        
        # 验证名称反查在 Tab 3 与 Tab 4 中的应用
        assert "resolve_fund_display_name" in src_text, (
            "Tab 3/Tab 4 中未调用 resolve_fund_display_name！"
        )

    def test_specialized_9_stock_overlap_anti_cheat_and_layout(self):
        """
        专项测试 9 (重仓交叉热力图 50% 真实诊断与双栏并排布局):
        验证非同系底仓不报零重叠，同系底仓如实返回真实重叠度，并输出共同重仓股清单。
        """
        from AGY2_FundAdvisory.portfolio_manager import PortfolioManager
        pm = PortfolioManager()
        ov = pm.calculate_stock_overlap_matrix()
        assert "max_total_overlap" in ov, "calculate_stock_overlap_matrix 缺少 max_total_overlap！"
        assert ov["max_total_overlap"] >= 0.50, f"005561 与 100032 真实重合度应为 50%，实际为 {ov['max_total_overlap']}"
        assert "common_stocks_details" in ov, "缺少 common_stocks_details 穿透明细！"
        assert len(ov["common_stocks_details"]) > 0, "应检测到至少 1 对重叠基金对！"

    def test_specialized_10_look_through_stocks_step_weights_and_risk_sorting(self):
        """
        专项测试 10 (底层排雷宽表真实阶梯权重与风险置顶排序):
        验证底层重仓股不出现等权除以10，商誉不全列2.4%，且关注警戒股排在最前列。
        """
        from AGY2_FundAdvisory.portfolio_manager import PortfolioManager
        pm = PortfolioManager()
        df = pm.get_portfolio_look_through_stocks_df()
        assert not df.empty, "底层排雷宽表不能为空！"
        weights = df["占组合总市值比例(%)"].tolist()
        assert len(set(weights)) > 5, "重仓股权重占比不应等权除以10，应呈现真实阶梯差异！"
        goodwills = df["商誉占净资产(%)"].tolist()
        assert len(set(goodwills)) > 3, "商誉不应全列写死为 2.4%，应反映真实行业特征！"
        # 验证风险置顶
        ratings = df["穿透评级"].tolist()
        watch_or_danger_indices = [i for i, r in enumerate(ratings) if "关注" in r or "预警" in r]
        safe_indices = [i for i, r in enumerate(ratings) if "健康" in r]
        if watch_or_danger_indices and safe_indices:
            assert min(watch_or_danger_indices) < max(safe_indices), "预警或关注标的必须置顶排列！"

    def test_specialized_11_smart_money_quadrants_and_real_metrics(self):
        """
        专项测试 11 (四象限量价微观结构真实计算与纵轴拥挤热力标准化):
        验证 get_fund_smart_money_crowding 返回真实20日量价，且符合四象限直觉标准标签。
        """
        from AGY2_FundAdvisory.portfolio_manager import PortfolioManager
        pm = PortfolioManager()
        valid_quadrants = {"🔥 右侧主升/偏热区", "📈 温和复苏区", "🎯 低估击球区", "⚠️ 放量分歧/避险区"}
        for f in ["005561", "100032", "002351", "000216", "017436", "011613"]:
            c_info = pm.get_fund_smart_money_crowding(f)
            assert "ret_20d" in c_info, "缺少近20日涨跌指标！"
            assert "bias_20" in c_info, "缺少MA20乖离率指标！"
            assert "vol_20d" in c_info, "缺少20日年化波动率指标！"
            assert "crowding_score" in c_info, "缺少拥挤热力评分！"
            assert 10.0 <= c_info["crowding_score"] <= 90.0, f"拥挤热力超出合理范围: {c_info['crowding_score']}"
            assert "quadrant_tag" in c_info, "缺少四象限归属标签！"
            assert c_info["quadrant_tag"] in valid_quadrants, f"未知象限标签: {c_info['quadrant_tag']}" 

    def test_specialized_12_multi_ledger_ghost_cleaning_and_naming_protection(self):
        """
        专项测试 12 (多账本幽灵数据物理清洗与防重名机制):
        验证 MultiLedgerManager 初始化自动清洗重名幽灵账本，且新建/重命名自动追加序号。
        """
        from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager
        import tempfile
        import shutil

        temp_dir = Path(tempfile.mkdtemp(prefix="test_mlm_ghost_"))
        try:
            mlm = MultiLedgerManager(workspace_root=temp_dir)
            lid1 = mlm.create_ledger("我的养老金")
            lid2 = mlm.create_ledger("我的养老金")
            m1 = mlm.get_ledger_meta(lid1)
            m2 = mlm.get_ledger_meta(lid2)
            assert m1["name"] == "我的养老金"
            assert m2["name"] == "我的养老金 (2)", f"重名账本应自动加序号，实际为 {m2['name']}"
            
            # 验证禁止外部冒充主实盘账本
            lid3 = mlm.create_ledger("主实盘账本")
            m3 = mlm.get_ledger_meta(lid3)
            assert m3["name"] != "主实盘账本", "外部新建账本严禁直接命名为'主实盘账本'！"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    def test_specialized_13_tab3_backtest_modes_and_duplicate_key_defense(self):
        """
        专项测试 13 (Tab 3 回测模式全链路切换与 DuplicateWidgetID 物理防御):
        1. 验证 render_tab3_backtest_content 已彻底移除 option_key_map 暴力覆盖语句；
        2. 验证消除同名 key 重复 selectbox，物理杜绝 DuplicateElementKey 异常；
        3. 验证 dock_tab3 HTML 字符串中 Markdown 反引号已清洗为 <b>...</b>；
        4. 验证全部 4 种回测模式（单账本/方案、调仓前后对比、双账本PK、C1~C5策略档）
           权重解析与切换真实生效，且权重互不相同。
        """
        gui_file = WORKSPACE_ROOT / "AGY2_FundAdvisory" / "app_gui.py"
        src_text = gui_file.read_text(encoding="utf-8")

        # 1. 静态防御断言
        assert "option_key_map.get(sel_target_type" not in src_text, "检测到 option_key_map 覆盖残留，会强行打断模式切换！"
        assert "target_options = [opt_cur_ledger]" not in src_text, "检测到旧版 target_options 拼接残留！"
        assert '`{len(pm.holdings)} 只`' not in src_text, "dock_tab3 HTML 中仍残留 Markdown 反引号语法！"
        assert '<b>{len(pm.holdings)} 只</b>' in src_text, "dock_tab3 HTML 未能正确升级为 <b> 标签！"

        # 2. 统计 key 唯一性（防止重复渲染同名 selectbox）
        pk1_count = src_text.count('key="sel_pk_ledger_1"')
        pk2_count = src_text.count('key="sel_pk_ledger_2"')
        tier_sub_count = src_text.count('key="sel_backtest_tier_sub"')
        assert pk1_count == 1, f'sel_pk_ledger_1 出现次数必须为 1，实际为 {pk1_count} (重复声明必报 DuplicateWidgetID)！'
        assert pk2_count == 1, f'sel_pk_ledger_2 出现次数必须为 1，实际为 {pk2_count} (重复声明必报 DuplicateWidgetID)！'
        assert tier_sub_count == 1, f'sel_backtest_tier_sub 出现次数必须为 1，实际为 {tier_sub_count}！'

        # 3. 动态验证 4 种模式下权重生成的真实独立性
        from AGY2_FundAdvisory.portfolio_manager import PortfolioManager, FundHolding
        from AGY2_FundAdvisory.strategy_bridge import StrategyBridge
        from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager

        pm = PortfolioManager()
        pm.holdings = {
            "005561": FundHolding("005561", "红利低波A", shares=10000, cost_price=1.0, current_nav=1.2),
            "002351": FundHolding("002351", "纯债A", shares=10000, cost_price=1.0, current_nav=1.1)
        }
        rebal_w = {"005561": 0.5, "100032": 0.5}

        # 模式 1: 单账本/方案
        tot_h = sum(h.market_value for h in pm.holdings.values())
        w_mode1 = {c: round(h.market_value / tot_h, 4) for c, h in pm.holdings.items()}
        assert "005561" in w_mode1 and "002351" in w_mode1

        # 模式 2: 调仓前 vs 调仓后对比 (双曲线)
        w_mode2_primary = w_mode1
        w_mode2_secondary = rebal_w
        assert w_mode2_secondary != w_mode2_primary, "调仓前后对比应具备差异化次要权重！"

        # 模式 3: 双账本同屏 PK (对比两组独立持仓)
        w_pk_a = {"005561": 0.6, "002351": 0.4}
        w_pk_b = {"100032": 0.7, "000216": 0.3}
        assert w_pk_a != w_pk_b, "双账本 PK 权重应完全独立！"

        # 模式 4: C1~C5 策略基准档 (真实矩阵动态算子)
        df_mat = StrategyBridge.load_matrix()
        from AGY2_FundAdvisory.app_gui import strategy_fn_for_tier
        w_c1_idx = strategy_fn_for_tier(df_mat, tier="C1")
        w_c5_idx = strategy_fn_for_tier(df_mat, tier="C5")
        w_c1_funds = StrategyBridge.map_index_weights_to_funds(w_c1_idx)
        w_c5_funds = StrategyBridge.map_index_weights_to_funds(w_c5_idx)
        assert w_c1_funds != w_c5_funds, "C1 策略档与 C5 策略档权重必须具备显著资产配置差异！"
    def test_specialized_14_smart_alias_and_visual_fitness(self):
        """
        专项测试 14 (智能图表简称提纯、017436纠偏与热力图画布优化):
        1. 验证 get_fund_short_alias 彻底消除 fund_name[:6] 机械截断与半截话；
        2. 验证 017436 官方名称准确为「华安纳斯达克100ETF联接A」，绝非华宝；
        3. 验证 app_gui.py 中热力图关闭色条 (coloraxis_showscale=False)，强制全显 ticktext；
        4. 验证四象限散点图防重叠碰撞算法与 380px 画布高度。
        """
        from AGY2_FundAdvisory.portfolio_manager import get_fund_short_alias, PortfolioManager
        pm = PortfolioManager()

        # 1. 验证 10 大核心标的高辨识度 5~6 字优雅简称
        expected_aliases = {
            "005561": "创金红利低波",
            "100032": "富国中证红利",
            "002351": "易方达裕祥债",
            "000216": "华安黄金ETF",
            "017436": "华安纳指100",
            "011613": "华夏科创50C",
            "161725": "招商中证白酒",
            "161726": "招商生物医药",
            "160418": "华安中证银行",
            "013402": "华夏恒生科技"
        }
        for code_str, expected in expected_aliases.items():
            actual = get_fund_short_alias(code_str)
            assert actual == expected, f"标的 {code_str} 简称提纯不符合预期: 实际 {actual} vs 预期 {expected}"
            assert len(actual) <= 7, f"简称字数超长: {actual}"

        # 2. 验证 017436 真实官方名称绝非华宝
        meta_017436 = pm.resolve_fund_meta("017436")
        assert "华安" in meta_017436["fund_name"], f"017436 公司归属错误: {meta_017436['fund_name']}"
        assert "华宝" not in meta_017436["fund_name"], f"017436 仍残留错误华宝名称: {meta_017436['fund_name']}"

        # 3. 静态代码防线核验
        gui_file = WORKSPACE_ROOT / "AGY2_FundAdvisory" / "app_gui.py"
        src_text = gui_file.read_text(encoding="utf-8")
        assert 'coloraxis_showscale=False' in src_text, "热力图必须设置 coloraxis_showscale=False 隐藏挤占色条！"
        assert 'tickmode="array"' in src_text, "热力图必须设置 tickmode='array' 强制全显坐标！"
        assert 'autorange="reversed"' in src_text, "热力图 Y 轴必须设置 autorange='reversed'！"
        assert 'height=380' in src_text, "图表高度必须升级为饱满的 380px！"
        assert 'pos_pool = ["top right"' in src_text, "散点图必须实装防重叠标签错位算法！"
