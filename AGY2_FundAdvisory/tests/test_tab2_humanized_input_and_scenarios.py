import pytest
import numpy as np
from pathlib import Path
from AGY2_FundAdvisory.portfolio_manager import (
    PortfolioManager,
    FundHolding,
    parse_smart_text_holdings
)

class TestTab2HumanizedInputAndScenarios:
    """Tab 2 人性化持仓录入、四向反算与四大实盘调仓意图场景全量测试"""

    def setup_method(self):
        self.pm = PortfolioManager(db_path=":memory:")

    def test_ocr_and_compact_smart_text_parsing(self):
        """测试 1：手机截图 OCR 跨行块状文本与单行紧凑文本精准解析"""
        ocr_multiline = """
        华泰柏瑞低波
        005561
        持有金额 30,000.00
        持有收益 +1,200.00
        昨日收益 +120.00
        持有天数 45天

        易方达裕祥
        002351
        持有金额 20000
        收益: 亏500
        持有天数: 180天

        华夏科创50C 20000 收益率-8.5% 3天
        """
        parsed = parse_smart_text_holdings(ocr_multiline)
        assert len(parsed) == 3

        # 标的 1：005561
        p1 = parsed[0]
        assert p1["fund_code"] == "005561"
        assert p1["amount"] == 30000.0
        assert p1["floating_pnl"] == 1200.0
        assert p1["holding_days"] == 45
        assert p1["cost_price"] < p1["current_nav"] # 浮盈，成本低于现价

        # 标的 2：002351
        p2 = parsed[1]
        assert p2["fund_code"] == "002351"
        assert p2["amount"] == 20000.0
        assert p2["floating_pnl"] == -500.0
        assert p2["holding_days"] == 180
        assert p2["cost_price"] > p2["current_nav"] # 浮亏，成本高于现价

        # 标的 3：011613
        p3 = parsed[2]
        assert p3["fund_code"] == "011613"
        assert p3["amount"] == 20000.0
        assert p3["floating_pnl_pct"] == -8.5
        assert p3["holding_days"] == 3

    def test_rebalance_intent_lock_and_liquidate(self):
        """测试 2：调仓意愿 (锁定禁卖 / 优先清仓) 物理生效"""
        # 录入两只基金
        self.pm.add_or_update_holding("005561", shares=10000, nav=1.2, cost_price=1.0, holding_days=45)
        self.pm.add_or_update_holding("002351", shares=10000, nav=1.1, cost_price=1.0, holding_days=45)

        # 正常情况下若目标权重大幅下调会卖出
        target_w = {"005561": 0.1, "002351": 0.9}

        # 标的 005561 设置为锁定禁卖 (lock)
        self.pm.holdings["005561"].rebalance_intent = "lock"
        plan = self.pm.generate_rebalance_plan(target_w, min_buffer_pct=0.0)

        # 验证 005561 绝对不出现在卖出列表中
        sell_codes = [s["fund_code"] for s in plan.get("sell_actions", [])]
        assert "005561" not in sell_codes

        # 标的 002351 设置为优先清仓 (liquidate)
        self.pm.holdings["002351"].rebalance_intent = "liquidate"
        plan_liq = self.pm.generate_rebalance_plan({"005561": 0.5, "002351": 0.5}, min_buffer_pct=0.0)
        sell_codes_liq = [s["fund_code"] for s in plan_liq.get("sell_actions", [])]
        assert "002351" in sell_codes_liq

    def test_scenario_new_cash_only(self):
        """测试 3：场景 2 - 新资注入免赎补仓 (零卖出零赎回费，精准补齐短板)"""
        self.pm.add_or_update_holding("005561", shares=10000, nav=1.0, cost_price=1.0, holding_days=45) # 10000元
        self.pm.add_or_update_holding("002351", shares=5000, nav=1.0, cost_price=1.0, holding_days=45)  # 5000元 (欠配)

        target_w = {"005561": 0.5, "002351": 0.5}
        new_cash = 5000.0

        plan = self.pm.generate_scenario_rebalance_plan(
            target_weights=target_w,
            scenario_mode="new_cash_only",
            new_cash_amount=new_cash
        )

        assert plan["scenario_mode"] == "new_cash_only"
        assert len(plan["sell_actions"]) == 0
        assert plan["total_sell_amount"] == 0.0
        assert plan["total_redemption_fee"] == 0.0
        assert plan["total_buy_amount"] == 5000.0
        # 绝大部分资金应当分配给欠配的 002351
        buy_map = {b["fund_code"]: b["amount"] for b in plan["buy_actions"]}
        assert "002351" in buy_map
        assert buy_map["002351"] >= 4500.0

    def test_scenario_withdraw_cash_only_safety_barrier(self):
        """测试 4：场景 3 - 智能低损耗提现 (零买入，避开<7天惩罚费)"""
        # 录入：一只不满7天(带1.5%惩罚)，一只满45天免赎
        self.pm.add_or_update_holding("011613", shares=10000, nav=1.0, cost_price=1.0, holding_days=3) # 10000元 (<7d)
        self.pm.add_or_update_holding("005561", shares=20000, nav=1.0, cost_price=1.0, holding_days=45) # 20000元 (>=30d)

        plan = self.pm.generate_scenario_rebalance_plan(
            target_weights={"011613": 0.5, "005561": 0.5},
            scenario_mode="withdraw_cash_only",
            withdraw_cash_amount=10000.0
        )

        assert plan["scenario_mode"] == "withdraw_cash_only"
        assert len(plan["buy_actions"]) == 0
        assert plan["total_buy_amount"] == 0.0
        assert plan["total_sell_amount"] >= 9900.0

        # 物理铁律：011613 处于 <7天 绝对不卖出！
        sell_codes = [s["fund_code"] for s in plan["sell_actions"]]
        assert "011613" not in sell_codes
        assert "005561" in sell_codes

    def test_scenario_sweep_tail_and_c_class(self):
        """测试 5：场景 4 - 尾部碎片与C类一键归拢至核心底仓"""
        # 录入：小额碎片标的 500 元 + 满期C类 5000 元 + 压舱石底仓 005561
        self.pm.add_or_update_holding("005561", shares=50000, nav=1.0, cost_price=1.0, holding_days=60) # 50000元 底仓
        self.pm.add_or_update_holding("001053", shares=500, nav=1.0, cost_price=1.0, holding_days=35)   # 500元 尾部碎片 (<3%)
        self.pm.add_or_update_holding("008682", shares=5000, nav=1.0, cost_price=1.0, holding_days=35)  # 5000元 满30天C类

        plan = self.pm.generate_scenario_rebalance_plan(
            target_weights={"005561": 1.0},
            scenario_mode="sweep_tail_and_c_class",
            core_anchor_code="005561"
        )

        assert plan["scenario_mode"] == "sweep_tail_and_c_class"
        # 卖出列表中包含碎片 001053 与 C类 008682，不包含底仓 005561
        sell_codes = [s["fund_code"] for s in plan["sell_actions"]]
        assert "001053" in sell_codes
        assert "008682" in sell_codes
        assert "005561" not in sell_codes

        # 买入列表只有 1 个：归拢至 005561
        assert len(plan["buy_actions"]) == 1
        assert plan["buy_actions"][0]["fund_code"] == "005561"
        assert plan["buy_actions"][0]["amount"] >= 5400.0

    def test_reserved_batch_cash_persistence_and_isolation(self):
        """测试 6：分批建仓预留现金隔离与持久化"""
        self.pm.reserved_batch_cash = 50000.0
        self.pm.available_cash = 60000.0

        state = self.pm._export_state_dict()
        assert "reserved_batch_cash" in state
        assert state["reserved_batch_cash"] == 50000.0

        pm2 = PortfolioManager(db_path=":memory:")
        pm2._import_state_dict(state)
        assert pm2.reserved_batch_cash == 50000.0
        assert pm2.available_cash == 60000.0
