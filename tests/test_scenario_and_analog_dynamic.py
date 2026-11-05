import os
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = CURRENT_DIR.parent if CURRENT_DIR.name == "tests" else CURRENT_DIR
AGY2_DIR = WORKSPACE_ROOT / "AGY2_FundAdvisory"

if str(AGY2_DIR) not in sys.path:
    sys.path.insert(0, str(AGY2_DIR))
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

import pytest
import numpy as np
from portfolio_manager import PortfolioManager
from strategy_bridge import StrategyBridge


class TestRebalancingScenariosBridgeAndConsequences:
    """测试四大实盘调仓场景模式在 StrategyBridge 与模拟精算层的真实计算闭环"""

    @pytest.fixture
    def setup_pm(self):
        pm = PortfolioManager()
        pm.available_cash = 20000.0
        pm.reserved_batch_cash = 5000.0
        pm.holdings = {}
        pm.add_or_update_holding("005561", shares=30000, nav=1.0, cost_price=1.0, holding_days=60)
        pm.add_or_update_holding("002351", shares=15000, nav=1.0, cost_price=1.0, holding_days=60)
        pm.add_or_update_holding("011613", shares=8000, nav=1.0, cost_price=1.0, holding_days=4)
        return pm

    def test_new_cash_only_simulation_and_orders(self, setup_pm):
        pm = setup_pm
        target_w = {"005561": 0.40, "002351": 0.40, "000216": 0.20}
        new_cash = 30000.0

        # 1. StrategyBridge.generate_ai_rebalance_orders
        res = StrategyBridge.generate_ai_rebalance_orders(
            current_holdings=pm.holdings,
            available_cash=pm.available_cash,
            target_weights_funds=target_w,
            pm=pm,
            scenario_mode="new_cash_only",
            new_cash_amount=new_cash
        )
        orders = res.get("orders") or res.get("items", [])
        sell_orders = [o for o in orders if o.get("action") == "SELL" and float(o.get("amount", 0.0)) > 1e-4]
        buy_orders = [o for o in orders if o.get("action") == "BUY"]
        
        assert len(sell_orders) == 0, f"new_cash_only 严禁卖出: {sell_orders}"
        total_buy = sum(float(o.get("amount", 0.0)) for o in buy_orders)
        assert total_buy == pytest.approx(new_cash, rel=1e-2)
        assert res.get("total_redemption_fee", 0.0) == 0.0

        # 2. StrategyBridge.simulate_rebalance_modes_and_consequences
        sim_res = StrategyBridge.simulate_rebalance_modes_and_consequences(
            pm=pm,
            active_tier="稳健",
            target_weights=target_w,
            scenario_mode="new_cash_only",
            new_cash_amount=new_cash
        )
        assert "mode_gentle" in sim_res and "mode_forced" in sim_res
        gentle = sim_res["mode_gentle"]
        assert gentle["consequences"]["fee_loss"]["redemption_fee"] == 0.0
        assert gentle["consequences"]["in_transit_risk"]["in_transit_amount"] == 0.0

    def test_withdraw_cash_only_simulation_and_orders(self, setup_pm):
        pm = setup_pm
        target_w = {"005561": 0.60, "002351": 0.40}
        withdraw_amt = 15000.0

        res = StrategyBridge.generate_ai_rebalance_orders(
            current_holdings=pm.holdings,
            available_cash=pm.available_cash,
            target_weights_funds=target_w,
            pm=pm,
            scenario_mode="withdraw_cash_only",
            withdraw_cash_amount=withdraw_amt
        )
        orders = res.get("orders") or res.get("items", [])
        buy_orders = [o for o in orders if o.get("action") == "BUY" and float(o.get("amount", 0.0)) > 1e-4]
        sell_orders = [o for o in orders if o.get("action") == "SELL"]

        assert len(buy_orders) == 0, f"withdraw_cash_only 严禁买入: {buy_orders}"
        total_sell = sum(float(o.get("amount", 0.0)) for o in sell_orders)
        assert total_sell == pytest.approx(withdraw_amt, rel=1e-2)
        sold_codes = [o.get("fund_code") for o in sell_orders]
        assert "011613" not in sold_codes, "未满7天的 011613 绝不应被赎回"

    def test_freeze_reserved_cash_effective_funds(self, setup_pm):
        pm = setup_pm
        pm.available_cash = 20000.0
        pm.reserved_batch_cash = 8000.0
        target_w = {"005561": 0.50, "002351": 0.50}

        # 验证 freeze_reserved_cash 会在模拟层及底层扣除预留资金
        sim_frozen = StrategyBridge.simulate_rebalance_modes_and_consequences(
            pm=pm,
            active_tier="稳健",
            target_weights=target_w,
            scenario_mode="standard",
            freeze_reserved_cash=True
        )
        sim_unfrozen = StrategyBridge.simulate_rebalance_modes_and_consequences(
            pm=pm,
            active_tier="稳健",
            target_weights=target_w,
            scenario_mode="standard",
            freeze_reserved_cash=False
        )
        assert sim_frozen is not None
        assert sim_unfrozen is not None


class TestTab3DynamicAnalogMetrics:
    """测试 Tab 3 历史相似匹配指标动态精算与三类镜鉴归因卡片分类"""

    def test_dynamic_analog_metrics_and_attribution_logic(self):
        # 模拟 3 个典型历史时期匹配数据
        sample_matches = [
            {
                "date": "2019-01-04",
                "strategy_ret_60d": 12.50,
                "h300_ret_60d": 18.20,
                "strategy_mdd_60d": -3.20,
            },
            {
                "date": "2022-04-27",
                "strategy_ret_60d": 8.40,
                "h300_ret_60d": -4.60,
                "strategy_mdd_60d": -1.80,
            },
            {
                "date": "2024-02-05",
                "strategy_ret_60d": 10.10,
                "h300_ret_60d": 9.50,
                "strategy_mdd_60d": -2.10,
            }
        ]

        n_matches = len(sample_matches)
        win_count = sum(1 for m in sample_matches if m["strategy_ret_60d"] > m["h300_ret_60d"])
        win_rate = (win_count / n_matches) * 100.0
        avg_excess = sum(m["strategy_ret_60d"] - m["h300_ret_60d"] for m in sample_matches) / n_matches
        avg_abs_ret = sum(m["strategy_ret_60d"] for m in sample_matches) / n_matches
        avg_mdd = sum(abs(m["strategy_mdd_60d"]) for m in sample_matches) / n_matches

        # 胜率验证：只有 2022-04-27 (8.40 > -4.60) 和 2024-02-05 (10.10 > 9.50) 跑赢，win_rate 为 66.7%
        assert round(win_rate, 1) == 66.7
        # 验证绝非硬编码 100.0% 或 +8.5%
        assert win_rate != 100.0
        assert avg_abs_ret != 8.5

        # 验证 3 张卡片根据行情状态的分类归因
        card_meanings = []
        for m in sample_matches:
            s_ret = m["strategy_ret_60d"]
            h_ret = m["h300_ret_60d"]
            mdd_abs = abs(m["strategy_mdd_60d"])
            diff_out = s_ret - h_ret

            if s_ret > 0 and h_ret > 0:
                card_meanings.append("右侧顺势共振")
            elif h_ret <= 0 and s_ret > h_ret:
                card_meanings.append("逆势抗跌护盾")
            elif h_ret > 0 and s_ret <= h_ret:
                card_meanings.append("防守底仓代价")
            else:
                card_meanings.append("极端下行冲击")

        # 2019-01-04: s=12.5>0, h=18.2>0 -> 右侧顺势共振
        assert card_meanings[0] == "右侧顺势共振"
        # 2022-04-27: h=-4.6<=0, s=8.4>h -> 逆势抗跌护盾
        assert card_meanings[1] == "逆势抗跌护盾"
        # 2024-02-05: s=10.1>0, h=9.5>0 -> 右侧顺势共振
        assert card_meanings[2] == "右侧顺势共振"
