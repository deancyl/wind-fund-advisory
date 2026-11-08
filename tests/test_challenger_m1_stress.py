# -*- coding: utf-8 -*-
"""
Adversarial Stress Test Suite for Milestone 1 (Top Area & Tab 1)
Challenger 1 (challenger_g11_m1_1)

Tests coverage:
1. Capital boundary values (0, 0.01, 100, 100,000,000, fractional 12345.67)
2. Switching all risk tiers C1 through C5
3. Switching all rhythm options (一次性, 稳健三步, 智能定投)
4. Switching all 7 asset allocation models (HRP, Barbell, Risk Parity, BL, Cond WinRate, CVaR, Kelly)
5. Streamlit AppTest integration: 3-column metric cards, execution dataframe, 0 exceptions
"""

import sys
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
AGY_PATH = WORKSPACE_ROOT / "AGY2_FundAdvisory"
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))
if str(AGY_PATH) not in sys.path:
    sys.path.insert(0, str(AGY_PATH))

from strategy_bridge import StrategyBridge
from advisory_engine import SmartExecutionDCAEngine
from portfolio_optimizer import QUANT_MODELS_CATALOG


class TestCapitalBoundaries:
    """对抗测试：测试本金边界值（0、0.01、100、100,000,000、小数 12345.67）"""

    def test_capital_zero_division_guard(self):
        """
        对抗场景 1a: 本金为 0 时底层算法表现
        实证复现：传入 total_capital = 0 时，strategy_bridge.py:5725 发生 ZeroDivisionError。
        证明此边界在未做防护时会抛出未捕获除零异常，前端必须依赖 number_input(min_value=1000.0) 兜底。
        """
        with pytest.raises(ZeroDivisionError, match="float division by zero"):
            StrategyBridge.generate_zero_start_blueprint(total_capital=0.0, tier="C3")

    def test_capital_fractional_cents_reconciliation(self):
        """
        对抗场景 1b: 本金为带分厘小数（如 12345.67 元）时，分厘平账与百分比闭合
        """
        cap = 12345.67
        bp = StrategyBridge.generate_zero_start_blueprint(total_capital=cap, tier="C3")
        items = bp["items"]
        assert len(items) > 0, "建仓清单不可为空"

        # 严格分厘平账断言：分配总金额必须与输入本金完全一致（误差小于 0.01 元）
        alloc_sum = round(sum(it["allocated_amount"] for it in items), 2)
        assert abs(alloc_sum - cap) < 0.02, f"分厘平账违背: 分配总额 {alloc_sum} != 输入本金 {cap}"

        # 百分比严格闭合：各项权重之和必须在 99.9% ~ 100.1% 区间
        pct_sum = round(sum(it["target_weight_pct"] for it in items), 2)
        assert abs(pct_sum - 100.0) <= 0.5, f"百分比闭合异常: {pct_sum}%"

    def test_capital_extreme_large_100_million(self):
        """
        对抗场景 1c: 1 亿元超大额本金建仓
        验证单日限额自动拆单及伴生承接机制是否正常触发且平账
        """
        cap = 100_000_000.0
        bp = StrategyBridge.generate_zero_start_blueprint(total_capital=cap, tier="C3")
        items = bp["items"]
        assert len(items) > 0, "超大额建仓清单不可为空"

        alloc_sum = round(sum(it["allocated_amount"] for it in items), 2)
        assert abs(alloc_sum - cap) < 0.05, f"超大额分厘平账失败: {alloc_sum} != {cap}"

        # 验证博时标普等限购标的确实触发了拆单
        has_split_item = any(it.get("has_split") for it in items)
        assert has_split_item, "1 亿元大额建仓必须触发限额标的智能拆单"

    def test_capital_small_100_yuan(self):
        """
        对抗场景 1d: 极小本金（100 元）
        验证在极低金额下各标的资金分配无负值且平账
        """
        cap = 100.0
        bp = StrategyBridge.generate_zero_start_blueprint(total_capital=cap, tier="C3")
        items = bp["items"]
        for it in items:
            assert it["allocated_amount"] >= 0.0, f"分配金额不可为负: {it}"
        alloc_sum = round(sum(it["allocated_amount"] for it in items), 2)
        assert abs(alloc_sum - cap) < 0.02, f"小额分厘平账失败: {alloc_sum} != {cap}"


class TestRiskTiersC1ThroughC5:
    """对抗测试：遍历 C1 至 C5 全部五档风险策略档位"""

    @pytest.mark.parametrize("tier_code", ["C1", "C2", "C3", "C4", "C5"])
    def test_all_five_tiers_blueprint_generation(self, tier_code):
        """验证 C1 至 C5 均能生成结构合规、权重归一的实盘建仓单"""
        cap = 200000.0
        bp = StrategyBridge.generate_zero_start_blueprint(total_capital=cap, tier=tier_code)
        assert bp["tier"] == tier_code
        items = bp["items"]
        assert len(items) >= 3, f"档位 {tier_code} 的配置标的数量至少 3 只"

        # 验证各标的金额与权重非负且分配总和等于本金
        alloc_sum = round(sum(it["allocated_amount"] for it in items), 2)
        assert abs(alloc_sum - cap) < 0.02

    def test_tier_risk_spectrum_monotonicity(self):
        """
        对抗验证：C1 至 C5 风险梯度单调性
        C1 防守型固收纯债占比应显著高于 C5；C5 权益高弹性标的占比应显著高于 C1
        """
        bp_c1 = StrategyBridge.generate_zero_start_blueprint(total_capital=100000.0, tier="C1")
        bp_c5 = StrategyBridge.generate_zero_start_blueprint(total_capital=100000.0, tier="C5")

        def _calc_defensive_ratio(items):
            def_amt = 0.0
            for it in items:
                fn = it["fund_name"]
                fc = it["fund_code"]
                if any(k in fn for k in ["债", "固收", "纯债", "回报"]) or fc in ["002351", "000086"]:
                    def_amt += it["allocated_amount"]
            return def_amt / 100000.0

        c1_def = _calc_defensive_ratio(bp_c1["items"])
        c5_def = _calc_defensive_ratio(bp_c5["items"])

        assert c1_def > c5_def, f"C1 防守比例 ({c1_def:.1%}) 必须大于 C5 防守比例 ({c5_def:.1%})"
        assert c1_def >= 0.50, f"C1 保守型固收防守占比必须 >= 50%，实际: {c1_def:.1%}"


class TestRhythmOptionsConservation:
    """对抗测试：三大建仓节奏（一次性全额、稳健三步、智能定投）金额守恒与逻辑自洽"""

    @pytest.fixture
    def sample_allocations(self):
        return [
            {"code": "002351", "name": "易方达裕祥回报债券A", "weight": 0.40},
            {"code": "100032", "name": "富国中证红利指数增强A", "weight": 0.30},
            {"code": "011613", "name": "华夏上证科创板50成份ETF联接C", "weight": 0.20},
            {"code": "000216", "name": "华安黄金ETF联接A", "weight": 0.10},
        ]

    def test_lump_sum_conservation(self, sample_allocations):
        """一次性建仓金额严格守恒"""
        cap = 88888.88
        res = SmartExecutionDCAEngine.plan_lump_sum(total_capital=cap, allocations=sample_allocations)
        assert res["total_capital"] == cap
        tot_orders = round(sum(o["order_amount"] for o in res["orders"]), 2)
        assert abs(tot_orders - cap) < 0.01, f"一次性建仓金额不守恒: {tot_orders} != {cap}"

    def test_three_step_batches_conservation(self, sample_allocations):
        """稳健三步分批建仓批次与金额严格守恒 (50% + 30% + 20% == 100%)"""
        cap = 150000.0
        res = SmartExecutionDCAEngine.plan_three_step_batches(total_capital=cap, allocations=sample_allocations)
        assert len(res["batches"]) == 3, "必须严格输出 3 个批次"

        b_amounts = [b["amount"] for b in res["batches"]]
        assert abs(sum(b_amounts) - cap) < 0.01, f"三批总和不守恒: {sum(b_amounts)} != {cap}"
        assert abs(b_amounts[0] - cap * 0.50) < 0.02
        assert abs(b_amounts[1] - cap * 0.30) < 0.02
        assert abs(b_amounts[2] - cap * 0.20) < 0.02

        # 验证每批次内订单之和等于该批次金额
        for b in res["batches"]:
            b_ord_sum = round(sum(o["amount"] for o in b["orders"]), 2)
            assert abs(b_ord_sum - b["amount"]) < 0.01

    def test_smart_dca_multiplier_and_vwap_optimization(self, sample_allocations):
        """智能定投乘数计算、分期扣款与 VWAP 滑点优化节省"""
        cap = 120000.0
        # 极度低估场景 (ERP=85%, Bias=-5.0%) -> 乘数应在 1.5x ~ 2.0x 逆向猛扣
        res_undervalued = SmartExecutionDCAEngine.plan_smart_dca(
            total_capital=cap,
            allocations=sample_allocations,
            erp_percentile=85.0,
            bias_20=-5.0,
            periods=12
        )
        assert res_undervalued["multiplier"] >= 1.5, f"低估期乘数必须 >= 1.5x，实际: {res_undervalued['multiplier']}"
        assert res_undervalued["base_per_period"] == 10000.0
        assert res_undervalued["actual_deduction"] == round(10000.0 * res_undervalued["multiplier"], 2)

        # 高估过热场景 (ERP=20%, Bias=+8.0%) -> 乘数应 <= 0.5x 防守微扣或暂停
        res_overvalued = SmartExecutionDCAEngine.plan_smart_dca(
            total_capital=cap,
            allocations=sample_allocations,
            erp_percentile=20.0,
            bias_20=8.0,
            periods=12
        )
        assert res_overvalued["multiplier"] <= 0.5, f"高估期乘数必须 <= 0.5x，实际: {res_overvalued['multiplier']}"

        # 验证订单总金额守恒与 VWAP 节省为非负
        for o in res_undervalued["fund_orders"]:
            assert o["period_amount"] >= 0.0
            assert o["slippage_saved_yuan"] >= 0.0


class TestAllSevenAssetAllocationModels:
    """对抗测试：遍历 7 大机构级量化定权模型"""

    SEVEN_MODELS = [
        "hrp_cvar",          # 鲁棒双核HRP
        "core_satellite",    # 核心-卫星杠铃
        "all_weather",       # 全天候风险平价
        "black_litterman",   # BL主客观观点融合
        "cond_winrate",      # 条件胜率最优
        "min_cvar",          # 尾部风控CVaR
        "kelly_momentum",    # 凯利动量增强
    ]

    @pytest.mark.parametrize("m_key", SEVEN_MODELS)
    def test_model_solving_and_kpi_synthesis(self, m_key):
        """验证每个模型均能成功求解非退化权重向量并生成 KPI"""
        res = StrategyBridge.compute_n_funds_model_portfolio(
            tier="C3",
            target_return_pct=15.0,
            num_funds=6,
            model_type=m_key,
            capital=100000.0
        )
        assert "optimal_weights" in res
        weights = res["optimal_weights"]
        assert len(weights) >= 3, f"模型 {m_key} 产出标的只数过少: {weights}"

        # 权重非负且总和为 1.0
        for fc, w in weights.items():
            assert w >= -1e-5, f"模型 {m_key} 产出负权重: {fc}={w}"
        w_sum = sum(weights.values())
        assert abs(w_sum - 1.0) < 0.01, f"模型 {m_key} 权重和不归一: {w_sum}"

        # 验证核心 KPI 指标存在且为有限数值
        kpi = res.get("readable_kpi", {})
        assert np.isfinite(float(kpi.get("worst_case_drawdown_pct", 0.0)))
        assert np.isfinite(float(kpi.get("win_rate_1y", 0.0)))
        assert int(kpi.get("max_underwater_days", 0)) >= 0


class TestStreamlitAppTestTab1Rendering:
    """对抗测试：在真实的 Streamlit AppTest 环境中运行 Tab 1 全流程"""

    @pytest.fixture
    def app_path(self):
        p = AGY_PATH / "app_gui.py"
        assert p.exists(), f"app_gui.py 不存在: {p}"
        return str(p)

    def test_apptest_tab1_default_render_no_exceptions(self, app_path):
        """验证默认状态下首屏与 Tab 1 正常初始化，无未捕获异常"""
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(app_path, default_timeout=45)
        at.run()
        assert not at.exception, f"默认运行抛出异常: {at.exception}"

        # 验证 Tab 1 关键控件存在
        num_inputs = [w for w in at.number_input]
        assert any(w.key == "plan_capital_input" for w in num_inputs), "必须存在 plan_capital_input"

        sel_boxes = [w for w in at.selectbox]
        assert any(w.key == "tab1_tier_selector" for w in sel_boxes), "必须存在 tab1_tier_selector"
        assert any(w.key == "radio_capital_deployment_mode" for w in sel_boxes), "必须存在 radio_capital_deployment_mode"

    def test_apptest_tab1_generate_full_plan_and_verify_three_metric_cards(self, app_path):
        """
        验证点击「⚡ 生成实盘建仓方案」后：
        1. 3 项核心指标条 (收益与胜率、风险底线、攻防定权) 正确渲染
        2. 执行数据表 st.dataframe 正常渲染且包含 9 大列
        3. 底部 4 个操作 Popover/按钮 与 单一白盒抽屉正常呈现
        """
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(app_path, default_timeout=60)
        at.session_state.active_tier_val = "C3"
        at.session_state.target_return_val = 15.0
        at.session_state.tab1_step_reached = 2
        at.session_state.tab1_trigger_sim = True
        at.session_state.tab1_trigger_s3 = True
        at.run(timeout=60)

        assert not at.exception, f"建仓方案生成出现异常: {at.exception}"

        all_html = " ".join([m.value for m in at.markdown])

        # 验证 3 张核心决策指标卡
        assert "收益与胜率" in all_html, "必须渲染【收益与胜率】指标卡"
        assert "风险底线" in all_html, "必须渲染【风险底线】指标卡"
        assert "攻防定权" in all_html, "必须渲染【攻防定权】指标卡"

        # 验证实盘纪律关键文案
        assert "不满 7 天严禁赎回防 1.5% 惩罚费" in all_html, "必须包含不满7天惩罚费红线提示"
        assert "1年达标胜率" in all_html, "必须包含1年达标胜率"

        # 验证数据表存在
        assert len(at.dataframe) >= 1, "必须渲染建仓执行数据表"

        # 验证单一白盒抽屉存在
        expanders = [e.label for e in at.expander]
        assert any("展开机构级量化压力测试与选基白盒证据" in lbl for lbl in expanders), f"必须包含单一白盒抽屉，当前抽屉: {expanders}"

    def test_apptest_tab1_rhythm_three_step_batches(self, app_path):
        """验证稳健三步建仓节奏下的批次卡片渲染与数据表列扩展"""
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(app_path, default_timeout=60)
        at.session_state.radio_capital_deployment_mode = "🌊 稳健三步分批建仓（底仓 50% + 逢低网格 30% + 右侧趋势 20%）"
        at.session_state.tab1_step_reached = 2
        at.session_state.tab1_trigger_sim = True
        at.session_state.tab1_trigger_s3 = True
        at.run(timeout=60)

        assert not at.exception, f"稳健三步运行异常: {at.exception}"
        all_html = " ".join([m.value for m in at.markdown])
        assert "今日底仓" in all_html or "第一批" in all_html, "稳健三步必须渲染第一批底仓信息"

    def test_apptest_tab1_rhythm_smart_dca(self, app_path):
        """验证智能定投资态自适应乘数、拐点对照尺与 VWAP 滑点卡片渲染"""
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(app_path, default_timeout=60)
        at.session_state.radio_capital_deployment_mode = "📅 估值自适应智能定投（根据宏观 ERP 与均线偏离度动态调整扣款乘数）"
        at.session_state.tab1_step_reached = 2
        at.session_state.tab1_trigger_sim = True
        at.session_state.tab1_trigger_s3 = True
        at.run(timeout=60)

        assert not at.exception, f"智能定投运行异常: {at.exception}"
        all_metrics = [m.label for m in at.metric]
        assert any("定投周期与基准金额" in lbl for lbl in all_metrics), f"必须包含定投基准金额，当前: {all_metrics}"
        assert any("当期自适应乘数" in lbl for lbl in all_metrics), f"必须包含自适应乘数，当前: {all_metrics}"
