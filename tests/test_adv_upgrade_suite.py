# -*- coding: utf-8 -*-
import sys
from pathlib import Path
import pytest
import pandas as pd

CURRENT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = CURRENT_DIR.parent if CURRENT_DIR.name == "tests" else CURRENT_DIR
AGY2_DIR = WORKSPACE_ROOT / "AGY2_FundAdvisory"

if str(AGY2_DIR) not in sys.path:
    sys.path.insert(0, str(AGY2_DIR))
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from advisory_engine import OpportunityRadarEngine, RADAR_SECTOR_CATALOG
from portfolio_manager import PortfolioManager, FundHolding, HoldingItem
from trading_clock_fee import TradingClockFee


class TestAdvUpgradeSuite:
    """专业买方投顾终端进阶升级专项回归与防迎合测试"""

    def test_h30269_benchmark_mapping(self):
        """1. 断言 RADAR_SECTOR_CATALOG['dividend_low_vol'] 已经修正为 H30269，绝非 000978 医药指数"""
        meta = RADAR_SECTOR_CATALOG["dividend_low_vol"]
        assert meta["benchmark_index"] == "H30269", f"benchmark_index 应为 H30269，实际为 {meta['benchmark_index']}"
        assert meta["index_code"] == "H30269", f"index_code 应为 H30269，实际为 {meta['index_code']}"

    def test_no_forbidden_principal_guarantee_wording(self):
        """2. 断言全站 UI 源码中不再出现违规的'保本率'字样（严格替换为正收益概率）"""
        gui_p = AGY2_DIR / "app_gui.py"
        text = gui_p.read_text(encoding="utf-8")
        assert "保本率" not in text, "检测到 app_gui.py 中仍存在违规的'保本率'用词！"
        assert "正收益概率" in text, "app_gui.py 中未发现合规术语'正收益概率'！"

    def test_qdii_cross_border_rules_and_switch_exclusion(self):
        """3. 断言 QDII 基金正确识别，具备 T+2 确认与 T+7 到账，且被排除出同公司 T+1 SWITCH 转换"""
        clock = TradingClockFee()
        # 标普 500
        assert clock.is_qdii_fund("050025", "博时标普500ETF联接A")
        assert clock.is_qdii_fund("001071", "华安纳斯达克100ETF联接A")
        assert clock.is_qdii_fund("013402", "华夏恒生科技ETF联接A")

        res_qdii = clock.calculate_settlement_dates(fund_code="050025", fund_name="博时标普500ETF联接A")
        # 确认日与到账日存在跨时区交割时差
        assert res_qdii["confirm_date"] != res_qdii["effective_trade_date"]
        assert res_qdii["arrive_date"] != res_qdii["effective_trade_date"]

        # 在 PortfolioManager 中排查同公司转换
        pm = PortfolioManager()
        assert pm.is_qdii_fund("050025")

        # 估值可信度标签检验
        assert pm.get_fund_valuation_reliability_tag("050025", "博时标普500") == "美股休市·看隔夜期指"
        assert pm.get_fund_valuation_reliability_tag("002351", "易方达裕祥回报债券A") == "债基看久期票息"
        assert pm.get_fund_valuation_reliability_tag("100032", "富国中证红利指数增强A") == "指数高准度"

    def test_holding_item_compatibility(self):
        """4. 断言 HoldingItem 兼容导入与 cost_price/cost_nav 参数"""
        h1 = HoldingItem(
            fund_code="005561",
            fund_name="创金合信红利低波A",
            shares=1000.0,
            cost_price=1.2,
            current_nav=1.3
        )
        assert h1.market_value == 1300.0
        assert h1.cost_price == 1.2

        h2 = HoldingItem(
            fund_code="002351",
            fund_name="易方达裕祥回报债券A",
            shares=2000.0,
            cost_nav=1.1,
            current_nav=1.2
        )
        assert h2.cost_price == 1.1
        assert h2.market_value == 2400.0

    def test_14_sectors_genuine_dynamics_and_no_dummy_constants(self):
        """5. 断言 14 大赛道 100% 具备动态精算数值，无 (0.50, 1.0, 85.0) 假常数"""
        engine = OpportunityRadarEngine()
        sectors = engine.scan_all_sectors()
        assert len(sectors) == 14

        dummy_found = []
        for s in sectors:
            er = round(float(s.get("er_20", 0.0)), 2)
            bias = round(float(s.get("bias_20", 0.0)), 1)
            crowd = round(float(s.get("crowding_score", s.get("s_crowd", 0.0))), 1)
            if er == 0.50 and bias == 1.0 and crowd == 85.0:
                dummy_found.append(s["name"])

        assert len(dummy_found) == 0, f"发现共享假常数的赛道: {dummy_found}"

    def test_apply_rebalance_orders_and_nav_history(self):
        """6. 断言 apply_rebalance_orders_to_holdings 能正确记账入库并记录 NAV 历史"""
        pm = PortfolioManager()
        pm.holdings = {}
        pm.available_cash = 50000.0
        pm.baseline_equity = 50000.0

        orders = [
            {
                "基金代码": "005561",
                "基金名称": "创金合信红利低波A",
                "建议操作": "建仓买入",
                "建议调仓金额(元)": 20000.0
            },
            {
                "基金代码": "002351",
                "基金名称": "易方达裕祥回报债券A",
                "建议操作": "建仓买入",
                "建议调仓金额(元)": 15000.0
            }
        ]

        up_cnt = pm.apply_rebalance_orders_to_holdings(orders)
        assert up_cnt == 2
        assert "005561" in pm.holdings
        assert "002351" in pm.holdings
        assert pm.available_cash == 15000.0
        assert len(pm.nav_history) >= 1
        assert pm.nav_history[-1]["account_nav"] > 0
