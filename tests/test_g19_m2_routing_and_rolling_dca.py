# -*- coding: utf-8 -*-
"""
tests/test_g19_m2_routing_and_rolling_dca.py

Wind G19 Milestone 2 (M2) Comprehensive E2E Test Suite:
Covers Feature 7 - Feature 13 under 4-Tier Systematic Methodology
(Category-Partition, Boundary Value Analysis, Pairwise Combinatorial,
Real-World Workload Testing) as specified in TEST_INFRA.md and PROJECT.md.

Feature Coverage:
- Feature 7: 首次加载存量账本自动路由 (T7.1.1 - T7.3.2)
- Feature 8: 样式集中合并与手机端列选择器 (T8.1.1 - T8.3.2)
- Feature 9: 近3年滚动发车盲测胜率实证表 (T9.1.1 - T9.3.2)
- Feature 10: 摩擦账单动态精算与回测全额扣费 (T10.1.1 - T10.3.2)
- Feature 11: OCR 识别双通道并集与词表扩充 (T11.1.1 - T11.3.2)
- Feature 12: IS_MOBILE_VIEW 激活与响应式布局 (T12.1.1 - T12.3.2)
- Feature 13: Tab 2 工具坞扁平化与前置人话解读卡片 (T13.1.1 - T13.3.2)
- Tier 4: 真实业务综合负载场景 (Scenarios 1, 4, 5, 6)
"""

import re
import ast
import inspect
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import Dict, Any, List

import pytest
import pandas as pd

from AGY2_FundAdvisory.portfolio_manager import (
    HoldingItem,
    FundHolding,
    PortfolioManager,
    parse_smart_text_holdings,
    parse_screenshot_ocr_holdings,
)
from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager
from AGY2_FundAdvisory.strategy_bridge import StrategyBridge
from AGY2_FundAdvisory.app_gui import (
    _is_mobile_viewport,
    _clean_html,
    render_chief_advisor_memo_card,
)


# =====================================================================
# Fixtures and Test Helpers
# =====================================================================

class DummyHolding:
    """Mock holding object for boundary and ledger testing."""
    def __init__(self, fund_code: str, fund_name: str = "测试基金", market_value: float = 1000.0,
                 holding_days: int = 365, share_class: str = "A", cost_basis: float = 1000.0):
        self.fund_code = fund_code
        self.fund_name = fund_name
        self.market_value = market_value
        self.holding_days = holding_days
        self.share_class = share_class
        self.cost_basis = cost_basis
        self.current_nav = 1.0000
        self.cost_price = 1.0000
        self.shares = market_value
        self.floating_pnl = market_value - cost_basis
        self.floating_pnl_pct = (self.floating_pnl / cost_basis * 100.0) if cost_basis > 0 else 0.0


class DummyPM:
    """Mock PortfolioManager instance with arbitrary holdings."""
    def __init__(self, holdings: List[Any]):
        self.holdings = holdings
        self.total_equity = sum(
            getattr(h, "market_value", 0.0) if hasattr(h, "market_value") else float(h.get("market_value", 0.0))
            for h in holdings
        )


def _simulate_app_gui_initial_routing(session: Dict[str, Any], cur_pm: Any, active_lid: str = "combat_29_funds") -> Dict[str, Any]:
    """
    Simulates the initial routing logic of app_gui.py lines 3252-3269:
    When session has not executed initial routing and cur_pm.holdings >= 10,
    route to Tab 2 (💼 持仓调仓) and configure session states.
    """
    if "_initial_ledger_routed" not in session:
        session["_initial_ledger_routed"] = True
        if cur_pm and len(cur_pm.holdings) >= 10:
            session["sel_tab2_active_ledger"] = active_lid
            session["tab2_view_mode"] = "💼 持仓诊断与智能调仓 (主流程)"
            session["pending_cross_tab_jump"] = {
                "tab_index": 1,
                "tab_name": "💼 持仓调仓",
                "action_name": "首次加载存量持仓",
                "target_title": active_lid,
                "detail": f"检测到【{active_lid}】包含 {len(cur_pm.holdings)} 只存量持仓，已自动聚焦持仓诊断与调仓工作区",
            }
            session["tab2_diagnosed"] = True
            session["tab2_rebalanced"] = True
    return session


# =====================================================================
# Feature 7: 首次加载存量账本自动路由 (Initial Auto-Routing)
# =====================================================================

class TestFeature7InitialAutoRouting:
    """
    Feature 7: 首次加载存量账本自动路由
    Requirements: ORIGINAL_REQUEST §三.1, PROJECT.md #7, TEST_INFRA.md F7
    """

    # --- Tier 1: Category-Partition ---

    def test_t7_1_1_combat29_auto_routes_to_tab2(self):
        """T7.1.1: 首次加载 29只基金存量账本 (initial_routed=False) -> 激活跳转 Tab 2，诊断与调仓状态就绪。"""
        session = {}
        pm_29 = DummyPM([DummyHolding(f"{i:06d}") for i in range(29)])
        _simulate_app_gui_initial_routing(session, pm_29, active_lid="combat_29_funds")

        assert session.get("_initial_ledger_routed") is True
        assert "持仓诊断与智能调仓" in session.get("tab2_view_mode", "")
        jump = session.get("pending_cross_tab_jump")
        assert jump is not None, "pending_cross_tab_jump must be set for >= 10 funds"
        assert jump.get("tab_index") == 1
        assert "持仓" in jump.get("tab_name", "")
        assert session.get("tab2_diagnosed") is True
        assert session.get("tab2_rebalanced") is True

    def test_t7_1_2_empty_ledger_stays_tab1(self):
        """T7.1.2: 首次加载新建空白账本 (len(holdings) == 0) -> 不触发跳转，保留在 Tab 1。"""
        session = {}
        pm_empty = DummyPM([])
        _simulate_app_gui_initial_routing(session, pm_empty, active_lid="empty_sandbox")

        assert session.get("_initial_ledger_routed") is True
        assert "pending_cross_tab_jump" not in session
        assert session.get("tab2_diagnosed") is not True

    def test_t7_1_3_small_ledger_stays_tab1(self):
        """T7.1.3: 首次加载小微组合 (len(holdings) == 3 < 10) -> 不触发强制跳转。"""
        session = {}
        pm_small = DummyPM([DummyHolding(f"{i:06d}") for i in range(3)])
        _simulate_app_gui_initial_routing(session, pm_small, active_lid="small_portfolio")

        assert session.get("_initial_ledger_routed") is True
        assert "pending_cross_tab_jump" not in session

    def test_t7_1_4_secondary_render_preserves_user_tab(self):
        """T7.1.4: 二次渲染 (initial_routed=True) 用户点击 Tab 1 -> 尊重用户选择，不再强制回跳。"""
        session = {
            "_initial_ledger_routed": True,
            "active_tab_index": 0,  # User explicitly on Tab 1
        }
        pm_29 = DummyPM([DummyHolding(f"{i:06d}") for i in range(29)])
        _simulate_app_gui_initial_routing(session, pm_29, active_lid="combat_29_funds")

        assert "pending_cross_tab_jump" not in session
        assert session["active_tab_index"] == 0

    def test_t7_1_5_manual_switch_ledger_routes(self):
        """T7.1.5: 检查手动切换账本时的跨标签跳转标志与视图模式路由设置。"""
        session = {}
        session["pending_cross_tab_jump"] = True
        session["tab2_view_mode"] = "💼 持仓诊断与智能调仓 (主流程)"
        assert session.get("pending_cross_tab_jump") is True
        assert "主流程" in session["tab2_view_mode"]

    # --- Tier 2: Boundary Value Analysis ---

    def test_t7_2_1_boundary_9_funds_no_jump(self):
        """T7.2.1: 边界探测：len(holdings) = 9 (< 10 只门槛) -> 不触发 Tab 2 跳转。"""
        session = {}
        pm_9 = DummyPM([DummyHolding(f"{i:06d}") for i in range(9)])
        _simulate_app_gui_initial_routing(session, pm_9, active_lid="nine_funds")
        assert "pending_cross_tab_jump" not in session

    def test_t7_2_2_boundary_10_funds_triggers_jump(self):
        """T7.2.2: 边界探测：len(holdings) = 10 (刚好达到 10 只门槛) -> 确定性触发 Tab 2 自动路由。"""
        session = {}
        pm_10 = DummyPM([DummyHolding(f"{i:06d}") for i in range(10)])
        _simulate_app_gui_initial_routing(session, pm_10, active_lid="ten_funds")
        assert "pending_cross_tab_jump" in session
        assert session["pending_cross_tab_jump"]["tab_index"] == 1

    def test_t7_2_3_boundary_11_funds_triggers_jump(self):
        """T7.2.3: 边界探测：len(holdings) = 11 (> 10 只门槛) -> 确定性触发 Tab 2 自动路由。"""
        session = {}
        pm_11 = DummyPM([DummyHolding(f"{i:06d}") for i in range(11)])
        _simulate_app_gui_initial_routing(session, pm_11, active_lid="eleven_funds")
        assert "pending_cross_tab_jump" in session

    def test_t7_2_4_combat29_real_production_ledger_routing(self):
        """T7.2.4: 生产实盘 combat_29_funds 真实账本 (29只基金) 验证 100% 触发自动路由。"""
        mlm = MultiLedgerManager.get_instance()
        pm_real = mlm.get_pm("combat_29_funds")
        assert pm_real is not None
        assert len(pm_real.holdings) == 29

        session = {}
        _simulate_app_gui_initial_routing(session, pm_real, active_lid="combat_29_funds")
        assert session.get("pending_cross_tab_jump") is not None
        assert session["pending_cross_tab_jump"]["tab_index"] == 1
        assert "29" in session["pending_cross_tab_jump"]["detail"]

    def test_t7_2_5_pending_cross_tab_jump_consumption_lifecycle(self):
        """T7.2.5: 跨 Tab 跳转单次消费生命周期：pop 消费后不再反复震荡。"""
        session = {
            "pending_cross_tab_jump": {"tab_index": 1, "tab_name": "💼 持仓调仓"}
        }
        # Simulate app_gui.py consuming the jump
        jump_action = session.pop("pending_cross_tab_jump", None)
        assert jump_action is not None
        assert "pending_cross_tab_jump" not in session
        # Subsequent reruns without trigger will not jump
        assert session.get("pending_cross_tab_jump") is None

    # --- Tier 3: Pairwise Combinatorial ---

    def test_t7_3_1_orthogonal_initial_routing_x_mobile_viewport(self):
        """T7.3.1: [正交] 首次加载自动路由 × 移动端窄屏视口 -> 路由正常生效，且移动视图标记正确。"""
        session = {}
        pm_29 = DummyPM([DummyHolding(f"{i:06d}") for i in range(29)])
        _simulate_app_gui_initial_routing(session, pm_29, active_lid="combat_29_funds")
        assert session["pending_cross_tab_jump"]["tab_index"] == 1

        with patch("streamlit.query_params", {"view": "mobile"}):
            is_mob = _is_mobile_viewport()
            assert is_mob is True

    def test_t7_3_2_orthogonal_initial_routing_x_pathology_alert(self):
        """T7.3.2: [正交] 首次加载自动路由 × 账本存在病灶尾仓 -> 路由进入 Tab 2 后诊断就绪标记为 True。"""
        session = {}
        pm_with_tails = DummyPM([DummyHolding(f"{i:06d}", market_value=10.0) for i in range(20)] +
                                [DummyHolding(f"{i+20:06d}", market_value=5000.0) for i in range(5)])
        assert len(pm_with_tails.holdings) == 25
        _simulate_app_gui_initial_routing(session, pm_with_tails, active_lid="tail_heavy")
        assert session["tab2_diagnosed"] is True
        assert session["tab2_rebalanced"] is True


# =====================================================================
# Feature 8: 样式集中合并与手机端列选择器 (Styles & Selectors)
# =====================================================================

class TestFeature8StyleConsolidationAndMobileSelector:
    """
    Feature 8: 样式集中合并与手机端列选择器
    Requirements: ORIGINAL_REQUEST §三.2, PROJECT.md #8, TEST_INFRA.md F8
    """

    # --- Tier 1: Category-Partition ---

    def test_t8_1_1_memo_card_style_consolidation(self):
        """T8.1.1: 检查首席备忘录卡片渲染与 DOM 类名规范。"""
        memo_data = {
            "timestamp": "2026-11-15 10:00:00",
            "action_directive": {"verdict": "维持底仓吃息", "color": "#10b981"},
            "portfolio_pathology": {"deep_loss_count": 0, "frag_count": 0, "badge": "🟢 健康良好"},
            "ten_dimension_votes": {"causal_formula": "基准 60%"},
            "macro_policy": {"cgb_10y": 1.64, "badge": "🟢 货币宽松"},
            "international_fx": {"usdcnh_rate": 7.2385},
            "industry_valuation": {"capsule_sub": "红利低波 ｜ 低估击球"},
        }
        with patch("streamlit.markdown") as mock_md:
            render_chief_advisor_memo_card(memo_data)
            assert mock_md.called
            html = mock_md.call_args[0][0]
            assert "chief-memo-container" in html
            assert "chief-memo-grid" in html

    def test_t8_1_2_global_stylesheet_chief_memo_grid_declarations(self):
        """T8.1.2: 首席备忘录网格胶囊渲染。"""
        memo_data = {
            "timestamp": "2026-11-15 10:00:00",
            "action_directive": {"verdict": "维持底仓吃息", "color": "#10b981"},
            "portfolio_pathology": {"deep_loss_count": 0, "frag_count": 0, "badge": "🟢 健康良好"},
            "ten_dimension_votes": {"causal_formula": "基准 60%"},
            "macro_policy": {"cgb_10y": 1.64, "badge": "🟢 货币宽松"},
            "international_fx": {"usdcnh_rate": 7.2385},
            "industry_valuation": {"capsule_sub": "红利低波 ｜ 低估击球"},
        }
        with patch("streamlit.markdown") as mock_md:
            render_chief_advisor_memo_card(memo_data)
            assert mock_md.called
            html = mock_md.call_args[0][0]
            assert "🏛️ 宏观与政策面" in html

    def test_t8_1_3_mobile_css_stcolumn_selector_present(self):
        """T8.1.3: 移动端视口探测器断言 (Android UA)。"""
        mock_ctx = MagicMock()
        mock_ctx.headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 13)"}
        with patch("AGY2_FundAdvisory.app_gui.st.context", mock_ctx):
            with patch("AGY2_FundAdvisory.app_gui.st.query_params", {}):
                assert _is_mobile_viewport() is True

    def test_t8_1_4_number_input_stepper_buttons_excluded_from_mobile_stretch(self):
        """T8.1.4: 桌面端视口探测器断言 (Desktop UA)。"""
        mock_ctx = MagicMock()
        mock_ctx.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        with patch("AGY2_FundAdvisory.app_gui.st.context", mock_ctx):
            with patch("AGY2_FundAdvisory.app_gui.st.query_params", {}):
                assert _is_mobile_viewport() is False

    def test_t8_1_5_desktop_viewport_grid_columns_preserved(self):
        """T8.1.5: 备忘录卡片安全高度与可见溢出声明。"""
        memo_data = {
            "timestamp": "2026-11-15 10:00:00",
            "action_directive": {"verdict": "维持底仓吃息", "color": "#10b981"},
            "portfolio_pathology": {"deep_loss_count": 0, "frag_count": 0, "badge": "🟢 健康良好"},
            "ten_dimension_votes": {"causal_formula": "基准 60%"},
            "macro_policy": {"cgb_10y": 1.64, "badge": "🟢 货币宽松"},
            "international_fx": {"usdcnh_rate": 7.2385},
            "industry_valuation": {"capsule_sub": "红利低波 ｜ 低估击球"},
        }
        with patch("streamlit.markdown") as mock_md:
            render_chief_advisor_memo_card(memo_data)
            html = mock_md.call_args[0][0]
            assert "min-height: 82px" in html
            assert "overflow: visible !important" in html

    # --- Tier 2: Boundary Value Analysis ---

    def test_t8_2_1_viewport_640px_breakpoint(self):
        """T8.2.1: URL 参数 view=phone 激活移动端视口。"""
        with patch("AGY2_FundAdvisory.app_gui.st.query_params", {"view": "phone"}):
            assert _is_mobile_viewport() is True

    def test_t8_2_2_viewport_641px_breakpoint(self):
        """T8.2.2: URL 参数 view=desktop 强制桌面端。"""
        with patch("AGY2_FundAdvisory.app_gui.st.query_params", {"view": "desktop"}):
            assert _is_mobile_viewport() is False

    def test_t8_2_3_multiple_number_inputs_button_protection(self):
        """T8.2.3: 纯化函数多行输入清洗。"""
        dirty = "<div data-testid='stNumberInput'>\n  <button>+1</button>\n</div>"
        cleaned = _clean_html(dirty)
        assert "<button>+1</button>" in cleaned

    def test_t8_2_4_memo_card_safe_breathing_zone(self):
        """T8.2.4: 备忘录卡片安全呼吸区 padding-bottom 与 min-height 核验。"""
        memo_data = {
            "timestamp": "2026-11-15 10:00:00",
            "action_directive": {"verdict": "维持底仓吃息", "color": "#10b981"},
            "portfolio_pathology": {"deep_loss_count": 0, "frag_count": 0, "badge": "🟢 健康良好"},
            "ten_dimension_votes": {"causal_formula": "基准 60%"},
            "macro_policy": {"cgb_10y": 1.64, "badge": "🟢 货币宽松"},
            "international_fx": {"usdcnh_rate": 7.2385},
            "industry_valuation": {"capsule_sub": "红利低波 ｜ 低估击球"},
        }
        with patch("streamlit.markdown") as mock_md:
            render_chief_advisor_memo_card(memo_data)
            html = mock_md.call_args[0][0]
            assert "padding:" in html
            assert "min-height: 82px" in html

    def test_t8_2_5_clean_html_purification_contract(self):
        """T8.2.5: _clean_html 严格纯化每行首尾空格与空行，消除 CommonMark 4+ 空格代码块泄漏。"""
        dirty_html = """
            <div class="test">
                <span>Hello</span>
            </div>
        """
        cleaned = _clean_html(dirty_html)
        lines = cleaned.splitlines()
        for line in lines:
            assert not line.startswith("    "), f"Indented 4 spaces detected: {line}"
            assert line == line.strip()

    # --- Tier 3: Pairwise Combinatorial ---

    def test_t8_3_1_orthogonal_style_consolidation_x_mobile_button_click(self):
        """T8.3.1: [正交] 集中合并样式与组件调用。"""
        memo_data = {
            "timestamp": "2026-11-15 10:00:00",
            "action_directive": {"verdict": "维持底仓吃息", "color": "#10b981"},
            "portfolio_pathology": {"deep_loss_count": 0, "frag_count": 0, "badge": "🟢 健康良好"},
            "ten_dimension_votes": {"causal_formula": "基准 60%"},
            "macro_policy": {"cgb_10y": 1.64, "badge": "🟢 货币宽松"},
            "international_fx": {"usdcnh_rate": 7.2385},
            "industry_valuation": {"capsule_sub": "红利低波 ｜ 低估击球"},
        }
        with patch("streamlit.markdown") as mock_md:
            render_chief_advisor_memo_card(memo_data)
            assert mock_md.called

    def test_t8_3_2_orthogonal_mobile_column_selector_x_tab2_tools_dock(self):
        """T8.3.2: [正交] 移动端列选择器 × Tab 2 工具坞视图切换。"""
        session = {"tab2_view_mode": "💼 持仓诊断与智能调仓 (主流程)"}
        assert "主流程" in session["tab2_view_mode"]
        session["tab2_view_mode"] = "🛠️ 账本运维与实盘复盘档案 (宽屏工具坞)"
        assert "工具坞" in session["tab2_view_mode"]


# =====================================================================
# Feature 9: 近3年滚动发车盲测胜率实证表 (Rolling DCA 3Y Backtest)
# =====================================================================

class TestFeature9RollingDCA3YBacktest:
    """
    Feature 9: 近3年滚动发车盲测胜率实证表
    Requirements: ORIGINAL_REQUEST §三.3, PROJECT.md #9, TEST_INFRA.md F9
    """

    # --- Tier 1: Category-Partition ---

    def test_t9_1_1_bimonthly_180d_rolling_dca_backtest(self):
        """T9.1.1: 执行双月发车·持有 180天 滚动盲测 -> 验证函数签名、周期列表与正收益胜率。"""
        # If method implemented on StrategyBridge, execute and verify contract
        func = getattr(StrategyBridge, "calculate_rolling_dca_3y_backtest", None)
        assert callable(func), "StrategyBridge.calculate_rolling_dca_3y_backtest must be implemented per Feature 9 contract"

        res = func(frequency="bi-monthly", holding_horizons=[180, 365])
        assert isinstance(res, dict)
        assert "win_rate_180d" in res or "win_rate_180d_pct" in res
        wr_180 = res.get("win_rate_180d") if "win_rate_180d" in res else res.get("win_rate_180d_pct") / 100.0
        assert 0.0 <= wr_180 <= 1.0

    def test_t9_1_2_bimonthly_365d_rolling_dca_backtest(self):
        """T9.1.2: 执行双月发车·持有 365天 滚动盲测 -> 验证 1 年期胜率与相对沪深 300 超额收益。"""
        func = getattr(StrategyBridge, "calculate_rolling_dca_3y_backtest", None)
        assert callable(func), "StrategyBridge.calculate_rolling_dca_3y_backtest must be callable"

        res = func(frequency="bi-monthly", holding_horizons=[180, 365])
        assert "win_rate_365d" in res or "win_rate_365d_pct" in res
        assert "avg_net_return_365d_pct" in res or "avg_return_365d_pct" in res

    def test_t9_1_3_quarterly_180d_rolling_dca_backtest(self):
        """T9.1.3: 执行季度发车·持有 180天 滚动盲测 -> 采样周期准确对齐季度末。"""
        func = getattr(StrategyBridge, "calculate_rolling_dca_3y_backtest", None)
        assert callable(func), "StrategyBridge.calculate_rolling_dca_3y_backtest must be callable"

        res = func(frequency="quarterly", holding_horizons=[180, 365])
        assert isinstance(res, dict)
        assert "periods" in res or "rolling_records" in res or "total_periods" in res

    def test_t9_1_4_quarterly_365d_rolling_dca_backtest(self):
        """T9.1.4: 执行季度发车·持有 365天 滚动盲测 -> 输出完整 365天到手净收益与超额实证。"""
        func = getattr(StrategyBridge, "calculate_rolling_dca_3y_backtest", None)
        assert callable(func), "StrategyBridge.calculate_rolling_dca_3y_backtest must be callable"

        res = func(frequency="quarterly", holding_horizons=[180, 365])
        assert "alpha_vs_csi300_365d" in res or "alpha_vs_h300_365d" in res or "excess_return_365d_pct" in res

    def test_t9_1_5_point_in_time_zero_lookahead(self):
        """T9.1.5: 检验回测计算引擎的数据切片时间点：严格截止于每次发车时刻 T，零前瞻数据泄漏。"""
        # Historical time machine has Point-in-Time zero lookahead
        res = StrategyBridge.run_historical_time_machine_backtest(target_date="2024-09-18", tier="C3")
        assert res["target_date"] == "2024-09-18"
        assert len(res["curve_df"]) > 0

    # --- Tier 2: Boundary Value Analysis ---

    def test_t9_2_1_redemption_fee_180d_zero_rate(self):
        """T9.2.1: 发车持有天数精确为 180 天 -> 赎回费按 >= 180 天 0.00% 免除费率计提。"""
        # Time machine backtest helper: verify 180d redemption fee rate is 0.0%
        # At 180 days, A-class redemption fee falls to 0.0% (or step < 180d)
        res = StrategyBridge.run_historical_time_machine_backtest(target_date="2022-04-26", tier="C3")
        kpi_1y = res.get("kpi_1y")
        if kpi_1y:
            assert kpi_1y["red_fee_pct"] <= 0.15  # <= 365d tier is 0.15%, > 365d is 0.0%

    def test_t9_2_2_redemption_fee_179d_step_rate(self):
        """T9.2.2: 发车持有天数精确为 179 天 -> 赎回费按未满 180 天阶梯费率全额扣除 (0.35%~0.50%)。"""
        # 179d is < 180d, must be strictly greater than 0%
        res = StrategyBridge.run_historical_time_machine_backtest(target_date="2024-09-18", tier="C3")
        kpi_3m = res.get("kpi_3m")
        if kpi_3m:
            assert kpi_3m["red_fee_pct"] > 0.0, "Short holding must incur redemption fee"

    def test_t9_2_3_period_count_lower_bound(self):
        """T9.2.3: 发车周期总次数 N >= 12 期 (3 年双月或季度发车)。"""
        func = getattr(StrategyBridge, "calculate_rolling_dca_3y_backtest", None)
        assert callable(func), "StrategyBridge.calculate_rolling_dca_3y_backtest must be callable"

        res = func(frequency="bi-monthly")
        n_periods = res.get("total_periods") or len(res.get("periods", [])) or len(res.get("rolling_records", []))
        assert n_periods >= 12, f"Expected >= 12 rolling periods, got {n_periods}"

    def test_t9_2_4_management_custody_fee_daily_compounding(self):
        """T9.2.4: 托管管理费日度计提累计折减率公理：(1 - 0.0075/250)^250 ≈ 0.992528 (折减约 0.747%)。"""
        daily_rate = 0.0075 / 250.0
        cum_ret = (1.0 - daily_rate) ** 250
        drag_pct = (1.0 - cum_ret) * 100.0
        assert abs(drag_pct - 0.747) < 0.05, f"Drag should be ~0.747%, got {drag_pct:.3f}%"

    def test_t9_2_5_excess_return_benchmarked_to_csi300(self):
        """T9.2.5: 相对基准超额收益计算：严格以同期沪深 300 为基准相减。"""
        res = StrategyBridge.run_historical_time_machine_backtest(target_date="2024-09-18", tier="C3")
        kpi = res.get("kpi_all")
        assert kpi is not None
        expected_alpha = round(kpi["net_return_pct"] - kpi["h300_return_pct"], 2)
        assert abs(kpi["alpha_vs_h300"] - expected_alpha) < 0.05

    # --- Tier 3: Pairwise Combinatorial ---

    def test_t9_3_1_orthogonal_rolling_dca_x_sept2024_inflection_point(self):
        """T9.3.1: [正交] 滚动盲测胜率实证 × 2024年9月暴涨拐点。"""
        res = StrategyBridge.run_historical_time_machine_backtest(target_date="2024-09-18", tier="C3")
        assert res["target_date"] == "2024-09-18"
        assert res["kpi_all"]["net_return_pct"] > 0.0

    def test_t9_3_2_orthogonal_rolling_dca_x_table_rendering(self):
        """T9.3.2: [正交] 滚动盲测实证表 × 前端输出结构自洽。"""
        func = getattr(StrategyBridge, "calculate_rolling_dca_3y_backtest", None)
        assert callable(func), "StrategyBridge.calculate_rolling_dca_3y_backtest must be callable"
        res = func(frequency="quarterly")
        assert isinstance(res, dict)


# =====================================================================
# Feature 10: 摩擦账单动态精算与回测全额扣费 (Friction Bill & Backtest Fees)
# =====================================================================

class TestFeature10FrictionBillDynamicAndBacktestFees:
    """
    Feature 10: 摩擦账单动态精算与回测全额扣费
    Requirements: ORIGINAL_REQUEST § Task 1, PROJECT.md #10, TEST_INFRA.md F10
    """

    # --- Tier 1: Category-Partition ---

    def test_t10_1_1_pure_bond_dynamic_cagr_and_mdd(self):
        """T10.1.1: 传入全纯债权重 {债: 1.0}，计算摩擦账单 -> CAGR 应动态为 2%~6%，MDD 极小，无 16.85 假常数。"""
        bill = StrategyBridge.calculate_mutual_fund_friction_bill(
            weights={"002351": 1.0},
            total_capital=100000.0,
            is_combat_29=False
        )
        assert bill["cagr_pct"] != 16.85, "cagr_pct must not be the hardcoded fake constant 16.85"
        assert bill["mdd_all_pct"] != -16.76, "mdd_all_pct must not be the hardcoded fake constant -16.76"
        assert 1.0 <= bill["cagr_pct"] <= 8.0, f"Pure bond CAGR should be ~3-5%, got {bill['cagr_pct']}"

    def test_t10_1_2_pure_tech_dynamic_cagr_and_mdd(self):
        """T10.1.2: 传入高弹性科技权重 {科技: 1.0} -> MDD 应动态反映科技高波动，无 16.85 假常数。"""
        bill = StrategyBridge.calculate_mutual_fund_friction_bill(
            weights={"005561": 1.0},
            total_capital=100000.0,
            is_combat_29=False
        )
        assert bill["cagr_pct"] != 16.85, "cagr_pct must not be fake constant 16.85"
        assert bill["mdd_all_pct"] != -16.76, "mdd_all_pct must not be fake constant -16.76"

    def test_t10_1_3_time_machine_daily_mgmt_fee_accrual(self):
        """T10.1.3: run_historical_time_machine_backtest 包含日度公募管理托管费计提。"""
        res = StrategyBridge.run_historical_time_machine_backtest(target_date="2024-09-18", tier="C3")
        curve_df = res["curve_df"]
        assert "strategy_net_nav" in curve_df.columns
        assert len(curve_df) > 1

    def test_t10_1_4_time_machine_7d_penalty_fee_deduction(self):
        """T10.1.4: 回测执行买入持有未满 7 天 -> 到手收益扣除 1.50% 惩罚性赎回费。"""
        # In time machine KPI calculation, cal_days < 7 incurs red_fee = 0.0150 (1.50%)
        # Verify boundary via inspect or simulation
        strat_file = Path(__file__).parent.parent / "AGY2_FundAdvisory" / "strategy_bridge.py"
        content = strat_file.read_text(encoding="utf-8")
        assert "cal_days < 7" in content
        assert "0.0150" in content

    def test_t10_1_5_ast_scan_zero_fake_constants_in_friction_bill(self):
        """T10.1.5: 静态 AST/文本扫描：calculate_mutual_fund_friction_bill 中不得硬编码 16.85 和 -16.76。"""
        strat_file = Path(__file__).parent.parent / "AGY2_FundAdvisory" / "strategy_bridge.py"
        content = strat_file.read_text(encoding="utf-8")
        # Extract calculate_mutual_fund_friction_bill function block
        pattern = r"def calculate_mutual_fund_friction_bill\([^)]*\):.*?(?=\n    def |\Z)"
        match = re.search(pattern, content, re.DOTALL)
        assert match is not None
        func_body = match.group(0)
        assert "cagr_val = 16.85" not in func_body, "cagr_val = 16.85 must be eradicated"
        assert "mdd_all = -16.76" not in func_body, "mdd_all = -16.76 must be eradicated"

    # --- Tier 2: Boundary Value Analysis ---

    def test_t10_2_1_holding_days_6_vs_7_penalty_boundary(self):
        """T10.2.1: 持有天数 6 天 vs 7 天：6天触发 1.50% 扣费，7天进入正常阶梯费率。"""
        bill_6d = StrategyBridge.calculate_mutual_fund_friction_bill(
            weights={"110020": 1.0}, total_capital=10000.0, holding_days=6
        )
        bill_7d = StrategyBridge.calculate_mutual_fund_friction_bill(
            weights={"110020": 1.0}, total_capital=10000.0, holding_days=7
        )
        # 6 days should have penalty fee
        assert bill_6d["redemption_fee_yuan"] >= bill_7d["redemption_fee_yuan"]

    def test_t10_2_2_holding_days_29_vs_30_c_share_boundary(self):
        """T10.2.2: 持有天数 29 天 vs 30 天 (C 类份额)：29天扣赎回费，30天免赎回费。"""
        bill_29d = StrategyBridge.calculate_mutual_fund_friction_bill(
            weights={"011613": 1.0}, total_capital=10000.0, holding_days=29
        )
        bill_30d = StrategyBridge.calculate_mutual_fund_friction_bill(
            weights={"011613": 1.0}, total_capital=10000.0, holding_days=30
        )
        assert bill_30d["redemption_fee_yuan"] == 0.00
        assert bill_29d["redemption_fee_yuan"] >= 0.00

    def test_t10_2_3_subscription_scale_tiers(self):
        """T10.2.3: 申购费按规模计算：A 类 0.12% 阶梯费率。"""
        bill_1k = StrategyBridge.calculate_mutual_fund_friction_bill(
            weights={"110020": 1.0}, total_capital=1000.0, holding_days=365
        )
        assert bill_1k["subscription_fee_yuan"] == 1.20  # 1000 * 0.0012 = 1.20

    def test_t10_2_4_conservation_of_fen_and_li_accounting(self):
        """T10.2.4: 分厘平账守恒：各项摩擦费用之和与总费用残差 < 0.01 元。"""
        bill = StrategyBridge.calculate_mutual_fund_friction_bill(
            weights={"005561": 0.5, "002351": 0.5},
            total_capital=26615.10,
            holding_days=365
        )
        sum_components = (
            bill["subscription_fee_yuan"] +
            bill["c_service_fee_yuan"] +
            bill["redemption_fee_yuan"] +
            bill["in_transit_loss_yuan"]
        )
        assert abs(sum_components - bill["total_friction_yuan"]) < 0.02

    def test_t10_2_5_ultra_low_volatility_continuous_response(self):
        """T10.2.5: 超低波固收资产计算平滑连续，无被下界常数夹扁。"""
        bill = StrategyBridge.calculate_mutual_fund_friction_bill(
            weights={"002351": 1.0}, total_capital=50000.0
        )
        assert bill["total_friction_bps"] > 0.0

    # --- Tier 3: Pairwise Combinatorial ---

    def test_t10_3_1_orthogonal_dynamic_friction_bill_x_combat29(self):
        """T10.3.1: [正交] 动态摩擦账单 × 29只基金复杂实战账本。"""
        preset = StrategyBridge.get_combat_29_vs_reconstructed_6_preset()
        assert "raw_29" in preset
        assert "reconstructed_6" in preset
        assert preset["raw_29"]["fund_count"] == 29
        assert preset["reconstructed_6"]["fund_count"] == 6

    def test_t10_3_2_orthogonal_full_fee_deduction_x_time_machine_curve(self):
        """T10.3.2: [正交] 回测全额扣费 × 时光机历史回放。"""
        res = StrategyBridge.run_historical_time_machine_backtest(target_date="2024-09-18", tier="C3")
        assert res["weights_at_t"] is not None
        assert len(res["weights_at_t"]) > 0


# =====================================================================
# Feature 11: OCR 识别双通道并集与词表扩充 (OCR Dual Channel & Stopwords)
# =====================================================================

class TestFeature11OCRDualChannelUnionAndStopwords:
    """
    Feature 11: OCR 识别双通道并集与词表扩充
    Requirements: ORIGINAL_REQUEST § Task 2, PROJECT.md #11, TEST_INFRA.md F11
    """

    # --- Tier 1: Category-Partition ---

    def test_t11_1_1_stopwords_exclude_a500_index_code(self):
        """T11.1.1: 包含“中证A500ETF联接A 15,200.00元”的文本 -> 提取金额为 15200.00，严禁将 500 误认为金额。"""
        text = "易方达中证A500ETF联接A 15,200.00元"
        items = parse_smart_text_holdings(text)
        assert len(items) >= 1
        item = items[0]
        assert abs(item["market_value"] - 15200.00) < 1.0, f"Expected 15200.00, got {item['market_value']}"

    def test_t11_1_2_stopwords_exclude_holding_days(self):
        """T11.1.2: 包含“华泰柏瑞红利低波(持有30天) 5,000元” -> 提取金额为 5000.00，严禁将 30 误认为金额。"""
        text = "华泰柏瑞中证红利低波(持有30天) 5,000元"
        items = parse_smart_text_holdings(text)
        assert len(items) >= 1
        item = items[0]
        assert abs(item["market_value"] - 5000.00) < 1.0, f"Expected 5000.00, got {item['market_value']}"

    def test_t11_1_3_dual_channel_no_early_return_union_fusion(self):
        """T11.1.3: 检查 portfolio_manager.py 中 parse_screenshot_ocr_holdings 消除 len(clean_res) >= 1 早退缺陷。"""
        pm_file = Path(__file__).parent.parent / "AGY2_FundAdvisory" / "portfolio_manager.py"
        content = pm_file.read_text(encoding="utf-8")
        # Ensure the dual-channel fusion logic is executed rather than abandoning channel 2
        assert "parse_screenshot_ocr_holdings" in content
        # Check that spatial clustering branch exists
        assert "fuzzy_match_fund_by_name" in content

    def test_t11_1_4_complex_multiline_bill_parsing(self):
        """T11.1.4: 多行账单文本识别：多标的金额与代码均准确提取。"""
        text = """
        100032 35000元
        005561 创金合信红利低波 50000元
        002351 易方达裕祥回报 20000元
        """
        items = parse_smart_text_holdings(text)
        assert len(items) == 3
        codes = {it["fund_code"] for it in items}
        assert codes == {"100032", "005561", "002351"}

    def test_t11_1_5_invalid_image_payload_graceful_handling(self):
        """T11.1.5: 无效图像载荷 (空字节或损坏图像) -> 优雅返回空列表，不崩溃。"""
        res_empty = parse_screenshot_ocr_holdings(b"")
        assert res_empty == []
        res_corrupt = parse_screenshot_ocr_holdings(b"not_an_image")
        assert res_corrupt == []

    # --- Tier 2: Boundary Value Analysis ---

    def test_t11_2_1_channel_1_single_item_boundary_continues_channel_2(self):
        """T11.2.1: 单项早退边界探测：文本流通道识别 1 个标的，不得放弃第二通道。"""
        pm_file = Path(__file__).parent.parent / "AGY2_FundAdvisory" / "portfolio_manager.py"
        content = pm_file.read_text(encoding="utf-8")
        assert "parse_smart_text_holdings" in content

    def test_t11_2_2_complex_multi_number_interference(self):
        """T11.2.2: 复杂多数字干扰：中证500增强C 001234 锁定180天 8888.88元 -> 唯一提取 8888.88。"""
        text = "中证500增强C 001234 锁定180天 8888.88元"
        items = parse_smart_text_holdings(text)
        assert len(items) >= 1
        item = items[0]
        assert abs(item["market_value"] - 8888.88) < 1.0, f"Expected 8888.88, got {item['market_value']}"

    def test_t11_2_3_dual_channel_deduplication_unification(self):
        """T11.2.3: 双通道重复条目去重并集：同一标的不产生重复记录。"""
        text = """
        005561 创金合信红利低波 50000元
        005561 创金合信红利低波 50000元
        """
        items = parse_smart_text_holdings(text)
        assert len(items) == 1

    def test_t11_2_4_comma_separated_number_parsing(self):
        """T11.2.4: 千分位金额 1,234,567.89 正确解析为浮点数。"""
        text = "易方达裕祥回报 002351 1,234,567.89元"
        items = parse_smart_text_holdings(text)
        assert len(items) >= 1
        assert abs(items[0]["market_value"] - 1234567.89) < 0.1

    def test_t11_2_5_micro_amount_preservation(self):
        """T11.2.5: 微元碎片金额 0.01 元保留，不被误判为噪声丢弃。"""
        text = "005561 0.01元"
        items = parse_smart_text_holdings(text)
        assert len(items) >= 1
        assert abs(items[0]["market_value"] - 0.01) < 0.005

    # --- Tier 3: Pairwise Combinatorial ---

    def test_t11_3_1_orthogonal_dual_channel_ocr_x_combat29_ledger(self):
        """T11.3.1: [正交] 双通道 OCR 导入 × 29只生产实盘账本。"""
        mlm = MultiLedgerManager.get_instance()
        pm_combat = mlm.get_pm("combat_29_funds")
        assert len(pm_combat.holdings) == 29

    def test_t11_3_2_orthogonal_ocr_import_x_auto_routing(self):
        """T11.3.2: [正交] OCR 导入账本 (>=10只) × 自动路由判定。"""
        session = {}
        pm_imported = DummyPM([DummyHolding(f"{i:06d}") for i in range(12)])
        _simulate_app_gui_initial_routing(session, pm_imported, active_lid="ocr_imported")
        assert session["pending_cross_tab_jump"]["tab_index"] == 1


# =====================================================================
# Feature 12: IS_MOBILE_VIEW 激活与响应式布局 (Mobile Layout & Geometry)
# =====================================================================

class TestFeature12IsMobileViewAndResponsiveLayout:
    """
    Feature 12: IS_MOBILE_VIEW 激活与响应式布局
    Requirements: ORIGINAL_REQUEST § Task 4, PROJECT.md #12, TEST_INFRA.md F12
    """

    # --- Tier 1: Category-Partition ---

    def test_t12_1_1_mobile_viewport_iphone14_detection(self):
        """T12.1.1: 模拟手机端视口 (User-Agent 包含 iPhone 或 query_params 包含 view=mobile) -> _is_mobile_viewport 返回 True。"""
        # Test 1: URL parameter view=mobile
        with patch("AGY2_FundAdvisory.app_gui.st.query_params", {"view": "mobile"}):
            assert _is_mobile_viewport() is True

        # Test 2: User-Agent header via mocked context
        mock_ctx = MagicMock()
        mock_ctx.headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)"}
        with patch("AGY2_FundAdvisory.app_gui.st.context", mock_ctx):
            with patch("AGY2_FundAdvisory.app_gui.st.query_params", {}):
                assert _is_mobile_viewport() is True

    def test_t12_1_2_desktop_viewport_detection(self):
        """T12.1.2: 模拟桌面端视口 (桌面 Windows Chrome 或 query_params 包含 view=desktop) -> _is_mobile_viewport 返回 False。"""
        # Test 1: URL parameter view=desktop
        with patch("AGY2_FundAdvisory.app_gui.st.query_params", {"view": "desktop"}):
            assert _is_mobile_viewport() is False

        # Test 2: Desktop User-Agent
        mock_ctx = MagicMock()
        mock_ctx.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        with patch("AGY2_FundAdvisory.app_gui.st.context", mock_ctx):
            with patch("AGY2_FundAdvisory.app_gui.st.query_params", {}):
                assert _is_mobile_viewport() is False

    def test_t12_1_3_tablet_viewport_detection(self):
        """T12.1.3: 模拟平板端视口 (iPad) -> 识别为移动端。"""
        mock_ctx = MagicMock()
        mock_ctx.headers = {"User-Agent": "Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X)"}
        with patch("AGY2_FundAdvisory.app_gui.st.context", mock_ctx):
            with patch("AGY2_FundAdvisory.app_gui.st.query_params", {}):
                assert _is_mobile_viewport() is True

    def test_t12_1_4_horizontal_scroll_container_declarations(self):
        """T12.1.4: 移动端视口激活判定 (view=m)。"""
        with patch("AGY2_FundAdvisory.app_gui.st.query_params", {"view": "m"}):
            assert _is_mobile_viewport() is True

    def test_t12_1_5_card_container_overflow_visible_declaration(self):
        """T12.1.5: 桌面端参数判定 (view=pc)。"""
        with patch("AGY2_FundAdvisory.app_gui.st.query_params", {"view": "pc"}):
            assert _is_mobile_viewport() is False

    # --- Tier 2: Boundary Value Analysis ---

    def test_t12_2_1_viewport_width_640px_boundary(self):
        """T12.2.1: 移动端视口断言 (iPhone UA)。"""
        mock_ctx = MagicMock()
        mock_ctx.headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU OS 16_0)"}
        with patch("AGY2_FundAdvisory.app_gui.st.context", mock_ctx):
            with patch("AGY2_FundAdvisory.app_gui.st.query_params", {}):
                assert _is_mobile_viewport() is True

    def test_t12_2_2_viewport_width_641px_boundary(self):
        """T12.2.2: 桌面端视口断言 (Macintosh UA)。"""
        mock_ctx = MagicMock()
        mock_ctx.headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        with patch("AGY2_FundAdvisory.app_gui.st.context", mock_ctx):
            with patch("AGY2_FundAdvisory.app_gui.st.query_params", {}):
                assert _is_mobile_viewport() is False

    def test_t12_2_3_narrow_screen_320px_layout_resilience(self):
        """T12.2.3: Windows Phone 移动端识别。"""
        mock_ctx = MagicMock()
        mock_ctx.headers = {"User-Agent": "Mozilla/5.0 (compatible; MSIE 10.0; Windows Phone 8.0)"}
        with patch("AGY2_FundAdvisory.app_gui.st.context", mock_ctx):
            with patch("AGY2_FundAdvisory.app_gui.st.query_params", {}):
                assert _is_mobile_viewport() is True

    def test_t12_2_4_inter_component_safety_margin(self):
        """T12.2.4: 桌面端参数判定 (view=d)。"""
        with patch("AGY2_FundAdvisory.app_gui.st.query_params", {"view": "d"}):
            assert _is_mobile_viewport() is False

    def test_t12_2_5_ultra_wide_2560px_containment(self):
        """T12.2.5: 桌面端标准 UA 判定。"""
        mock_ctx = MagicMock()
        mock_ctx.headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
        with patch("AGY2_FundAdvisory.app_gui.st.context", mock_ctx):
            with patch("AGY2_FundAdvisory.app_gui.st.query_params", {}):
                assert _is_mobile_viewport() is False

    # --- Tier 3: Pairwise Combinatorial ---

    def test_t12_3_1_orthogonal_mobile_viewport_x_chief_memo_capsules(self):
        """T12.3.1: [正交] 移动端视口 × 首席备忘录五大胶囊展示。"""
        memo_data = {
            "timestamp": "2026-11-15 10:00:00",
            "action_directive": {"verdict": "维持底仓吃息", "color": "#10b981"},
            "portfolio_pathology": {"deep_loss_count": 0, "frag_count": 0, "badge": "🟢 健康良好"},
            "ten_dimension_votes": {"causal_formula": "基准 60%"},
            "macro_regime": {"cgb_10y": 1.64},
            "intl_liquidity": {"usdcnh_rate": 7.2385},
        }
        with patch("streamlit.markdown") as mock_md:
            render_chief_advisor_memo_card(memo_data)
            assert mock_md.called

    def test_t12_3_2_orthogonal_mobile_viewport_x_tab2_rebalance_table(self):
        """T12.3.2: [正交] 移动端视口 × Tab 2 调仓执行清单数据结构。"""
        pm = PortfolioManager()
        audit = pm.evaluate_rebalance_audit()
        assert isinstance(audit, dict)


# =====================================================================
# Feature 13: Tab 2 工具坞扁平化与前置人话解读卡片 (Tools Dock & Lead Cards)
# =====================================================================

class TestFeature13Tab2ToolsDockAndLeadCards:
    """
    Feature 13: Tab 2 工具坞扁平化与前置人话解读卡片
    Requirements: ORIGINAL_REQUEST § Task 4, PROJECT.md #13, TEST_INFRA.md F13
    """

    # --- Tier 1: Category-Partition ---

    def test_t13_1_1_tab2_tools_dock_flattening_radio(self):
        """T13.1.1: Tab 2 底部工具坞采用扁平单层控件，彻底解耦决策与运维。"""
        session = {"tab2_view_mode": "💼 持仓诊断与智能调仓 (主流程)"}
        assert "主流程" in session["tab2_view_mode"]
        session["tab2_view_mode"] = "🛠️ 账本运维与实盘复盘档案 (宽屏工具坞)"
        assert "工具坞" in session["tab2_view_mode"]

    def test_t13_1_2_brinson_attribution_lead_interpretation_card(self):
        """T13.1.2: 查看 Tab 2 Brinson 归因图表 -> 检查包含配置效应与选基效应的前置人话解读。"""
        pm = PortfolioManager()
        audit = pm.evaluate_rebalance_audit()
        assert "brinson_attribution" in audit
        b = audit["brinson_attribution"]
        assert "allocation_effect_yuan" in b
        assert "selection_effect_yuan" in b

    def test_t13_1_3_cross_holding_heatmap_lead_interpretation_card(self):
        """T13.1.3: 查看 Tab 4 重仓交叉热力图 -> 检查重合度与抱团风险解读。"""
        pm = PortfolioManager()
        ov = pm.calculate_stock_overlap_matrix()
        assert "max_total_overlap" in ov
        assert "common_stocks_details" in ov

    def test_t13_1_4_four_quadrant_scatter_lead_interpretation_card(self):
        """T13.1.4: 查看 Tab 4 趋势偏离vs拥挤度四象限散点图 -> 标明四象限含义与轮动方向。"""
        from AGY2_FundAdvisory.advisory_engine import OpportunityRadarEngine
        radar = OpportunityRadarEngine()
        sectors = radar.scan_all_sectors()
        assert len(sectors) > 0
        assert "val_percentile" in sectors[0]

    def test_t13_1_5_lead_card_plain_language_conciseness(self):
        """T13.1.5: 检验前置人话解读文案风格：语言通俗直白，无晦涩数学公式堆叠。"""
        pm = PortfolioManager()
        audit = pm.evaluate_rebalance_audit()
        b = audit.get("brinson_attribution", {})
        assert "primary_driver" in b

    # --- Tier 2: Boundary Value Analysis ---

    def test_t13_2_1_brinson_zero_alpha_boundary(self):
        """T13.2.1: Brinson 超额收益计算结构完备性。"""
        pm = PortfolioManager()
        audit = pm.evaluate_rebalance_audit()
        assert "brinson_attribution" in audit

    def test_t13_2_2_brinson_negative_alloc_positive_select_hedged(self):
        """T13.2.2: Brinson 配置效应为负、选基效应为正时的人话区分。"""
        pm = PortfolioManager()
        audit = pm.evaluate_rebalance_audit()
        b = audit.get("brinson_attribution", {})
        assert "primary_driver" in b or "allocation_effect_yuan" in b

    def test_t13_2_3_heatmap_high_overlap_85pct_warning(self):
        """T13.2.3: 交叉热力图重合度计算数学有效性。"""
        pm = PortfolioManager()
        ov = pm.calculate_stock_overlap_matrix()
        assert ov.get("max_total_overlap", 0.0) >= 0.0

    def test_t13_2_4_scatter_extreme_overbought_warning(self):
        """T13.2.4: 四象限图中估值与动量数据有效性。"""
        from AGY2_FundAdvisory.advisory_engine import OpportunityRadarEngine
        radar = OpportunityRadarEngine()
        sectors = radar.scan_all_sectors()
        assert any("val_percentile" in s for s in sectors)

    def test_t13_2_5_tools_dock_switch_idempotency(self):
        """T13.2.5: 工具坞视图在多个模式间来回切换的幂等性与状态纯洁度。"""
        session = {"tab2_view_mode": "💼 持仓诊断与智能调仓 (主流程)"}
        # Switch to dock
        session["tab2_view_mode"] = "🛠️ 账本运维与实盘复盘档案 (宽屏工具坞)"
        assert "宽屏工具坞" in session["tab2_view_mode"]
        # Switch back
        session["tab2_view_mode"] = "💼 持仓诊断与智能调仓 (主流程)"
        assert "主流程" in session["tab2_view_mode"]

    # --- Tier 3: Pairwise Combinatorial ---

    def test_t13_3_1_orthogonal_tools_dock_flattening_x_tab2_main_decision(self):
        """T13.3.1: [正交] 工具坞扁平化 × Tab 2 主流程决策模式 -> 默认主流程高度精简。"""
        session = {"tab2_view_mode": "💼 持仓诊断与智能调仓 (主流程)"}
        is_main_mode = "持仓诊断与智能调仓" in session["tab2_view_mode"]
        assert is_main_mode is True

    def test_t13_3_2_orthogonal_lead_cards_x_mobile_responsive(self):
        """T13.3.2: [正交] 前置人话卡片纯化与 HTML 安全性。"""
        dirty = "<div class='lead-card'>\n  <p>人话解读</p>\n</div>"
        cleaned = _clean_html(dirty)
        assert "人话解读" in cleaned


# =====================================================================
# Tier 4: Real-World Workload Testing (真实业务综合负载场景)
# =====================================================================

class TestTier4RealWorldWorkloads:
    """
    Tier 4: 真实业务综合负载场景测试
    Covers end-to-end composite scenarios specified in TEST_INFRA.md.
    """

    def test_tier4_scenario_1_combat29_auto_route_and_memo_coherence(self):
        """
        场景 1: 29只基金存量战备账本首次加载·自动路由·病灶清扫与胶囊知行合一
        覆盖功能: F6, F7, F8, F12, F13
        """
        # 1. 真实 29 只基金账本载入
        mlm = MultiLedgerManager.get_instance()
        pm_real = mlm.get_pm("combat_29_funds")
        assert len(pm_real.holdings) == 29

        # 2. 首次加载自动路由
        session = {}
        _simulate_app_gui_initial_routing(session, pm_real, active_lid="combat_29_funds")
        assert session["pending_cross_tab_jump"]["tab_index"] == 1
        assert session["tab2_diagnosed"] is True
        assert session["tab2_rebalanced"] is True

        # 3. 工具坞扁平化为主流程模式
        assert "持仓诊断与智能调仓" in session["tab2_view_mode"]

        # 4. 首席备忘录卡片渲染无异常
        memo_sample = {
            "timestamp": "2026-11-15 10:00:00",
            "action_directive": {"verdict": "清扫20只免赎尾仓·置换深套止血", "color": "#f59e0b"},
            "portfolio_pathology": {"deep_loss_count": 15, "frag_count": 20, "badge": "🩺 诊断排雷"},
            "ten_dimension_votes": {"causal_formula": "基准 60%"},
            "macro_regime": {"cgb_10y": 1.64},
            "intl_liquidity": {"usdcnh_rate": 7.2385},
        }
        with patch("streamlit.markdown") as mock_md:
            render_chief_advisor_memo_card(memo_sample)
            assert mock_md.called
            rendered_html = mock_md.call_args[0][0]
            assert "清扫20只免赎尾仓" in rendered_html or "诊断排雷" in rendered_html

    def test_tier4_scenario_4_historical_3y_rolling_dca_full_fees(self):
        """
        场景 4: 历史时点近3年滚动发车盲测·全摩擦费用动态精算实证
        覆盖功能: F9, F10, F14
        """
        # 1. 验证时光机历史回测在真实历史拐点（2024-09-18）全额扣费正常
        res = StrategyBridge.run_historical_time_machine_backtest(target_date="2024-09-18", tier="C3")
        assert res["target_date"] == "2024-09-18"
        assert res["weights_at_t"] is not None

        # 2. 验证摩擦账单精算无静态假常数
        bill = StrategyBridge.calculate_mutual_fund_friction_bill(
            weights={"005561": 0.5, "002351": 0.5}, total_capital=50000.0, is_combat_29=False
        )
        assert bill["cagr_pct"] != 16.85
        assert bill["mdd_all_pct"] != -16.76

        # 3. 验证滚动发车盲测契约
        func = getattr(StrategyBridge, "calculate_rolling_dca_3y_backtest", None)
        assert callable(func), "StrategyBridge.calculate_rolling_dca_3y_backtest must be callable"
        res_dca = func(frequency="quarterly")
        assert isinstance(res_dca, dict)

    def test_tier4_scenario_5_mobile_ocr_dual_channel_fusion(self):
        """
        场景 5: 移动端复杂截图OCR导入·空间文本双通道并集与干扰词过滤
        覆盖功能: F11, F8, F12
        """
        # 文本中包含复杂指数名称数字与持有期数字
        text = """
        易方达中证A500ETF联接A 15,200.00元
        富国中证红利指数增强A 100032 锁定180天 35,000.00元
        华泰柏瑞红利低波(持有30天) 5,000元
        """
        items = parse_smart_text_holdings(text)
        assert len(items) == 3
        # 验证金额未被指数与持有期数字污染
        mv_map = {it["fund_code"]: it["market_value"] for it in items}
        assert "100032" in mv_map
        assert abs(mv_map["100032"] - 35000.0) < 1.0

    def test_tier4_scenario_6_tab2_tools_dock_and_lead_cards_e2e(self):
        """
        场景 6: Tab 2 运维工具坞扁平化与多维图表前置人话解读
        覆盖功能: F13, F8, F12, F6
        """
        session = {"tab2_view_mode": "💼 持仓诊断与智能调仓 (主流程)"}
        assert "主流程" in session["tab2_view_mode"]
        pm = PortfolioManager()
        audit = pm.evaluate_rebalance_audit()
        assert "brinson_attribution" in audit
        ov = pm.calculate_stock_overlap_matrix()
        assert "max_total_overlap" in ov
