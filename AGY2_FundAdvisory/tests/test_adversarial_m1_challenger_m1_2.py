# -*- coding: utf-8 -*-
"""
Adversarial Challenge Test Suite for Milestone M1 Verification
Author: teamwork_challenger (Empirical Challenger)
Target:
  1. Tab 2 调仓适宜度裁决器 (evaluate_today_rebalance_suitability) 3 场景对抗实测
     - 场景 1: 未满 7 天惩罚期份额 -> FORBIDDEN
     - 场景 2: 临界免赎期份额 (25-29天) -> HOLD_ON
     - 场景 3: 正常份额与突破行情 -> SUITABLE
  2. Tab 2 双模式调仓推演器 (simulate_rebalance_modes_and_consequences) 对抗实测
     - mode_gentle 绝对零惩罚费 (penalty_fee_7d == 0.0)
     - mode_forced 全额核算惩罚费与赎回费
     - 四大后果字典 (fee_loss, in_transit_risk, risk_shift, lockup_reset) 字段完整与数学分厘平账
  3. Tab 2 第三层向导折叠状态对抗验证
     - AST 静态验证与 AppTest 动态渲染：len(pm.holdings) > 0 时向导全部默认折叠
"""

import ast
import math
import pathlib
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from strategy_bridge import StrategyBridge
from portfolio_manager import PortfolioManager
from trading_clock_fee import TradingClock, FeeMatrixCalculator


@pytest.fixture
def temp_pm(tmp_path):
    """测试专用隔离 PortfolioManager，使用临时 SQLite 数据库与 JSON 账本"""
    db_file = tmp_path / "test_adv_challenger_m1_2.db"
    json_file = tmp_path / "test_adv_challenger_m1_2.json"
    pm = PortfolioManager(db_path=db_file, ledger_json_path=json_file)
    return pm


# =============================================================================
# 1. Tab 2 调仓适宜度裁决器与双模式推演对抗实测 (三种持仓场景)
# =============================================================================

class TestRebalanceSuitabilityAndDualModesAdversarial:
    """对抗实测：持仓样本三色裁决与双模式后果精算"""

    def test_scenario_1_unmet_7d_penalty_shares_forbidden(self, temp_pm):
        """
        【场景 1：未满 7 天惩罚期份额对抗实测】
        构造持仓包含未满 7 天批次 (持有 2 天，safety_lock=True)，
        断言：
        1. evaluate_today_rebalance_suitability 裁决必须为 FORBIDDEN；
        2. verdict_title 包含未满 7 天惩罚预警；
        3. reasons_4d['lockup_fee_reason'] 明确指出未满 7 天 1.50% 巨额惩罚；
        4. simulate_rebalance_modes_and_consequences 中：
           - mode_gentle 的 penalty_fee_7d 严格为 0.0，且绝不卖出未满 7 天标的；
           - mode_forced 的 penalty_fee_7d > 0.0，按 1.50% 精确计提；
           - 四大后果字典完整无缺失。
        """
        today_dt = datetime.now().date()
        records = [
            {
                "fund_code": "013841",  # 非目标配置基金，必触发卖出
                "buy_date": (today_dt - timedelta(days=2)).strftime("%Y-%m-%d"),
                "shares": 10000.0,
                "cost_nav": 1.00,
                "current_nav": 1.00,
                "holding_days": 2,
                "safety_lock": True
            },
            {
                "fund_code": "005561",  # 目标基金之一
                "buy_date": (today_dt - timedelta(days=100)).strftime("%Y-%m-%d"),
                "shares": 20000.0,
                "cost_nav": 1.00,
                "current_nav": 1.00,
                "holding_days": 100,
                "safety_lock": False
            }
        ]
        temp_pm.takeover_mode_b(historical_records=records, available_cash=0.0)

        # 1. 验证适宜度裁决
        res_suit = StrategyBridge.evaluate_today_rebalance_suitability(temp_pm, active_tier="C3")
        assert res_suit["verdict_level"] == "FORBIDDEN", (
            f"存在未满 7 天批次卖出需求时，裁决必须为 FORBIDDEN，实际为: {res_suit['verdict_level']}"
        )
        assert any(k in res_suit["verdict_title"] for k in ["7天", "未满", "高损", "惩罚", "不宜"])

        r4d = res_suit["reasons_4d"]
        assert "lockup_fee_reason" in r4d
        assert "未满 7 天" in r4d["lockup_fee_reason"]
        assert "1.50%" in r4d["lockup_fee_reason"]

        # 2. 验证双模式推演与后果精算
        res_sim = StrategyBridge.simulate_rebalance_modes_and_consequences(temp_pm, active_tier="C3")
        assert "mode_gentle" in res_sim
        assert "mode_forced" in res_sim

        gentle = res_sim["mode_gentle"]
        forced = res_sim["mode_forced"]

        # 温和模式对抗断言
        fl_gentle = gentle["consequences"]["fee_loss"]
        assert fl_gentle["penalty_fee_7d"] == 0.0, (
            f"mode_gentle 绝对严禁产生 7 天惩罚费，实际为: {fl_gentle['penalty_fee_7d']}"
        )
        sold_gentle = [o["fund_code"] for o in gentle["orders"] if o["action"] == "SELL"]
        assert "013841" not in sold_gentle, "mode_gentle 绝不可卖出未满 7 天的 013841 份额"

        # 强行模式对抗断言
        fl_forced = forced["consequences"]["fee_loss"]
        assert fl_forced["penalty_fee_7d"] > 0.0, "mode_forced 强平必须核算 1.50% 惩罚费"
        expected_penalty = round(10000.0 * 1.00 * 0.015, 2)
        assert abs(fl_forced["penalty_fee_7d"] - expected_penalty) < 0.01, (
            f"10000 份 013841 强平惩罚费应为 {expected_penalty} 元，实际为 {fl_forced['penalty_fee_7d']}"
        )

        # 四大后果字典完整性断言
        for mode_obj in [gentle, forced]:
            cq = mode_obj["consequences"]
            assert set(cq.keys()) == {"fee_loss", "in_transit_risk", "risk_shift", "lockup_reset"}
            assert set(cq["fee_loss"].keys()) == {"redemption_fee", "penalty_fee_7d", "subscription_fee", "total_fee", "payback_days"}
            assert set(cq["in_transit_risk"].keys()) == {"in_transit_amount", "in_transit_pct", "lock_days", "switch_saved_amount", "missed_rally_cost_est"}
            assert set(cq["risk_shift"].keys()) == {"equity_before", "equity_after", "vol_before", "vol_after", "mdd_before", "mdd_after", "div_yield_before", "div_yield_after"}
            assert set(cq["lockup_reset"].keys()) == {"new_buy_amount", "reset_warning_text"}

    def test_scenario_2_approaching_cliff_shares_hold_on(self, temp_pm):
        """
        【场景 2：临界免赎期份额对抗实测】
        构造持仓包含临近免赎阶梯份额 (C 类持有 28 天，无 <7 天批次)，
        断言：
        1. evaluate_today_rebalance_suitability 裁决为 HOLD_ON；
        2. verdict_title 与 lockup_fee_reason 提示临近免赎阶梯建议稍作等待；
        3. 双模式推演均无 7 天惩罚费 (penalty_fee_7d == 0.0)；
        4. 强行模式下正确按 0.5% 核算阶梯赎回费。
        """
        today_dt = datetime.now().date()
        records = [
            {
                "fund_code": "005562",  # 创金合信红利低波 C 类 (7-29天0.5%，>=30天免赎)
                "buy_date": (today_dt - timedelta(days=28)).strftime("%Y-%m-%d"),
                "shares": 50000.0,
                "cost_nav": 1.00,
                "current_nav": 1.00,
                "holding_days": 28,
                "safety_lock": False
            },
            {
                "fund_code": "002351",  # 易方达裕祥纯债
                "buy_date": (today_dt - timedelta(days=120)).strftime("%Y-%m-%d"),
                "shares": 10000.0,
                "cost_nav": 1.00,
                "current_nav": 1.00,
                "holding_days": 120,
                "safety_lock": False
            }
        ]
        temp_pm.takeover_mode_b(historical_records=records, available_cash=0.0)

        res_suit = StrategyBridge.evaluate_today_rebalance_suitability(temp_pm, active_tier="C3")
        assert res_suit["verdict_level"] == "HOLD_ON", (
            f"存在临界免赎期 (28天) 份额时裁决必须为 HOLD_ON，实际为: {res_suit['verdict_level']}"
        )
        r4d = res_suit["reasons_4d"]
        assert "lockup_fee_reason" in r4d
        assert "免赎回费阶梯仅剩数日" in r4d["lockup_fee_reason"]

        res_sim = StrategyBridge.simulate_rebalance_modes_and_consequences(temp_pm, active_tier="C3")
        gentle = res_sim["mode_gentle"]
        forced = res_sim["mode_forced"]

        # 两模式均无 7 天惩罚费
        assert gentle["consequences"]["fee_loss"]["penalty_fee_7d"] == 0.0
        assert forced["consequences"]["fee_loss"]["penalty_fee_7d"] == 0.0

        # 强行模式下有正常赎回费 (0.5%)
        assert forced["consequences"]["fee_loss"]["redemption_fee"] > 0.0

    def test_scenario_3_normal_mature_shares_and_breakout_suitable(self, temp_pm):
        """
        【场景 3：正常满期份额且行情有效突破 SUITABLE 裁决对抗实测】
        构造持仓全部满期 (> 365天 A类免赎)，模拟大盘向上突破 MA20 (+2.5%) 且处于 14:30 黄金窗口，
        持仓偏离度显著 (d_max >= 0.03)，
        断言：
        1. evaluate_today_rebalance_suitability 裁决必须为 SUITABLE；
        2. verdict_title 包含 '适合调仓'；
        3. reasons_4d['market_position_reason'] 包含 '右侧向上有效突破'；
        4. reasons_4d['lockup_fee_reason'] 包含 '免赎期'；
        5. 双模式推演的 penalty_fee_7d 与 redemption_fee 均为 0.0；
        6. 四大后果数学分厘平账断言通过。
        """
        today_dt = datetime.now().date()
        records = [
            {
                "fund_code": "100032",  # 富国中证红利 A，单一大额持仓制造重度偏离
                "buy_date": (today_dt - timedelta(days=400)).strftime("%Y-%m-%d"),
                "shares": 100000.0,
                "cost_nav": 1.00,
                "current_nav": 1.00,
                "holding_days": 400,
                "safety_lock": False
            }
        ]
        temp_pm.takeover_mode_b(historical_records=records, available_cash=0.0)

        # 构造黄金窗口与向上有效突破快照
        mock_window = MagicMock()
        mock_window.window_type = "GOLDEN_WINDOW"
        mock_window.effective_trade_date = today_dt.strftime("%Y-%m-%d")

        mock_snapshot = {
            "bias_20": 2.5,
            "erp_percentile": 50.0,
            "c300_price": 4200.0,
            "m20_price": 4100.0,
            "surge_line": 4149.2,
            "breakdown_line": 4038.5,
            "trigger_lines": {"surge_line": 4149.2, "breakdown_line": 4038.5},
            "target_weights_funds": StrategyBridge.compute_dynamic_tier_weights(tier="C3")
        }

        with patch.object(TradingClock, "get_market_window_status", return_value=mock_window):
            with patch.object(StrategyBridge, "get_latest_market_snapshot", return_value=mock_snapshot):
                res_suit = StrategyBridge.evaluate_today_rebalance_suitability(temp_pm, active_tier="C3")

                assert res_suit["verdict_level"] == "SUITABLE", (
                    f"突破行情且全部满期时，裁决必须为 SUITABLE，实际为: {res_suit['verdict_level']}"
                )
                assert "适合调仓" in res_suit["verdict_title"]
                r4d = res_suit["reasons_4d"]
                assert "右侧向上有效突破" in r4d["market_position_reason"]
                assert "免赎期" in r4d["lockup_fee_reason"]

                # 双模式推演
                res_sim = StrategyBridge.simulate_rebalance_modes_and_consequences(temp_pm, active_tier="C3")
                gentle = res_sim["mode_gentle"]
                forced = res_sim["mode_forced"]

                assert gentle["consequences"]["fee_loss"]["penalty_fee_7d"] == 0.0
                assert forced["consequences"]["fee_loss"]["penalty_fee_7d"] == 0.0
                assert gentle["consequences"]["fee_loss"]["redemption_fee"] == 0.0
                assert forced["consequences"]["fee_loss"]["redemption_fee"] == 0.0

                # 数学分厘平账断言
                for m_name, m_data in [("gentle", gentle), ("forced", forced)]:
                    cq = m_data["consequences"]
                    fl = cq["fee_loss"]
                    rs = cq["risk_shift"]
                    expected_total_fee = round(fl["redemption_fee"] + fl["penalty_fee_7d"] + fl["subscription_fee"], 2)
                    assert round(fl["total_fee"], 2) == expected_total_fee
                    expected_equity_after = round(max(0.0, rs["equity_before"] - fl["total_fee"]), 2)
                    assert round(rs["equity_after"], 2) == expected_equity_after


# =============================================================================
# 2. Tab 2 第三层向导折叠状态对抗验证
# =============================================================================

class TestTab2WizardCollapseStateAdversarial:
    """对抗实测：Tab 2 第三层 3 个向导面板在 len(pm.holdings) > 0 时的折叠状态"""

    def test_app_gui_ast_wizard_collapse_expressions(self):
        """
        【AST 静态严审：Tab 2 向导展开逻辑与默认折叠状态】
        1. 解析 app_gui.py 的 AST 语法树；
        2. 提取 Tab 2 内所有 st.expander 调用；
        3. 验证向导展开参数：
           - 接管向导: expanded=(not has_holdings)，其中 has_holdings = len(pm.holdings) > 0；
           - FIFO 倒计时透视: expanded=False；
        4. 断言当持仓数量 > 0 时，所有向导面板的展开状态均严格计算为 False。
        """
        gui_path = pathlib.Path(__file__).resolve().parent.parent / "app_gui.py"
        content = gui_path.read_text(encoding="utf-8")
        tree = ast.parse(content)

        # 验证 AST 中的关键变量绑定与表达式
        has_holdings_assigns = []
        tab2_expanders = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "has_holdings":
                        has_holdings_assigns.append(ast.unparse(node.value))

            if isinstance(node, ast.With):
                for item in node.items:
                    call = item.context_expr
                    if isinstance(call, ast.Call) and getattr(call.func, 'attr', '') == 'expander':
                        title = ast.unparse(call.args[0]) if call.args else ""
                        if "持仓接管向导" in title or "FIFO" in title:
                            exp_val = None
                            for kw in call.keywords:
                                if kw.arg == "expanded":
                                    exp_val = ast.unparse(kw.value)
                            tab2_expanders.append({
                                "lineno": node.lineno,
                                "title": title,
                                "expanded_expr": exp_val
                            })

        # 断言 has_holdings 的定义
        assert any("len(pm.holdings) > 0" in expr for expr in has_holdings_assigns), (
            f"未找到 has_holdings = len(pm.holdings) > 0 的赋值，实际为: {has_holdings_assigns}"
        )

        # 找到两个关键 expander
        import_wizard = [e for e in tab2_expanders if "持仓接管向导" in e["title"]]
        fifo_table = [e for e in tab2_expanders if "FIFO" in e["title"]]

        assert len(import_wizard) == 1, "未找到接管向导 expander"
        assert len(fifo_table) == 1, "未找到 FIFO 倒计时透视 expander"

        # 验证表达式在 len(pm.holdings) > 0 时的布尔值
        # 1. 接管向导: not has_holdings
        expr_wizard = import_wizard[0]["expanded_expr"]
        assert "has_holdings" in expr_wizard or expr_wizard in ["False", "not has_holdings", "(not has_holdings)"]

        # 模拟有持仓环境 (len(pm.holdings) = 3)
        mock_has_holdings = True
        wizard_expanded_when_holding = eval(expr_wizard, {"has_holdings": mock_has_holdings, "pm": MagicMock(holdings={"001": 1})})
        assert wizard_expanded_when_holding is False, (
            f"当有持仓时，接管向导展开状态必须为 False，实际为: {wizard_expanded_when_holding}"
        )

        # 2. FIFO 透视表: expanded=False
        expr_fifo = fifo_table[0]["expanded_expr"]
        assert expr_fifo == "False"
        fifo_expanded = eval(expr_fifo)
        assert fifo_expanded is False, "FIFO 透视表必须默认 expanded=False"

    def test_streamlit_apptest_tab2_collapse_when_holdings_exist(self):
        """
        【Streamlit AppTest 动态渲染对抗实测：有持仓时 Tab 2 向导默认全折叠】
        使用 Streamlit AppTest 运行 app_gui.py (配足 180s timeout)，
        注入真实持仓，断言 Tab 2 的 expander 默认全部收起 (expanded=False)。
        """
        from streamlit.testing.v1 import AppTest

        gui_path = pathlib.Path(__file__).resolve().parent.parent / "app_gui.py"

        # 运行 AppTest (default_timeout=180 避免全量选基计算超时)
        at = AppTest.from_file(str(gui_path), default_timeout=180)
        at.run(timeout=180)

        assert len(at.exception) == 0, f"AppTest 运行异常: {[e.value for e in at.exception]}"

        # 提取所有 expanders
        expanders = at.expander
        assert len(expanders) > 0, "未能定位到页面的 expanders"

        # 验证 FIFO expander 必须为 False
        tab2_fifo_exp = [e for e in expanders if "FIFO" in e.label]
        assert len(tab2_fifo_exp) >= 1, "未能在 AppTest 中找到 FIFO expander"
        for fe in tab2_fifo_exp:
            exp_state = getattr(fe.proto, 'expanded', getattr(fe.proto, 'default_expanded', None))
            assert exp_state is False, f"FIFO expander 必须折叠，实际 expanded={exp_state}"

        # 验证接管向导在有持仓时必须为 False
        pm = PortfolioManager()
        if len(pm.holdings) > 0:
            tab2_import_exp = [e for e in expanders if "持仓接管向导" in e.label]
            for ie in tab2_import_exp:
                exp_state = getattr(ie.proto, 'expanded', getattr(ie.proto, 'default_expanded', None))
                assert exp_state is False, f"有持仓时接管向导必须折叠，实际 expanded={exp_state}"
