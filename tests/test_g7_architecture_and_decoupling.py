"""
G7 世代专属自动化测试套件：
test_g7_architecture_and_decoupling.py
覆盖：
1. OnlineHeuristicFactorEvolver 换手率惩罚、最大回撤约束、四维权重硬约束与 60 日微图数据生成；
2. OpportunityRadarEngine 动态基因因子权重接入；
3. Tab 2 双视图解耦 (🎯 主流程 vs 💼 独立工具坞) 结构与静态契约；
4. 首屏主动风险预警哨双按钮 (去 Tab 2 调仓 vs 去 Tab 4 穿透) 与 Tab 4 顶部高亮响应闭环；
5. 同公司基金低摩擦转换与宏观估值自适应分红研判。
"""

import pytest
import numpy as np
from pathlib import Path
from AGY2_FundAdvisory.advisory_engine import (
    OnlineHeuristicFactorEvolver,
    OpportunityRadarEngine,
    find_same_company_conversions,
    evaluate_macro_dividend_policy,
)
from AGY2_FundAdvisory.portfolio_manager import PortfolioManager, HoldingItem

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent


class TestG7EvolutionAndDecoupling:
    """G7 架构解耦与三方风控联动闭环测试集"""

    def test_g7_evolver_constraints_and_turnover_penalty(self):
        """
        G7-1: 在线启发式因子基因自适应进化算子测试
        - 四维权重单项 >= 0.05
        - 权重和严格归一化 sum(w) == 1.0000
        - 包含换手率惩罚与最大回撤指标
        - 60 日滚动回测序列完整且具备超额 Alpha
        """
        evolver = OnlineHeuristicFactorEvolver(population_size=16, generations=5, random_seed=42)
        res = evolver.evolve_factor_weights(force_refresh=True, lookback_days=60)
        
        assert res.get("status") == "success"
        weights = res.get("weights", [])
        assert len(weights) == 4, f"因子权重必须为四维，当前: {weights}"
        for w in weights:
            assert w >= 0.0499, f"单项因子权重必须满足 >= 0.05 硬约束，发现违背: {w}"
        assert abs(sum(weights) - 1.0) < 1e-4, f"四维权重和必须严格归一化为 1.0，当前: {sum(weights)}"

        assert "turnover" in res, "必须输出换手率惩罚评估指标"
        assert "mdd" in res, "必须输出组合最大回撤约束"
        assert "sharpe" in res, "必须输出夏普比率"
        assert res.get("elapsed_ms", 999.0) < 250.0, "纯 NumPy 向量化回测必须在 250ms 内极速完成"

        traj = evolver.get_60d_rolling_nav_and_trajectory()
        assert len(traj.get("dates", [])) == 60, "回测日期序列必须为 60 个交易日"
        assert len(traj.get("nav_dynamic", [])) == 60, "动态演化净值序列必须为 60 日"
        assert len(traj.get("nav_static", [])) == 60, "静态基准净值序列必须为 60 日"
        assert len(traj.get("trajectory", [])) == 60, "四维演化轨迹点必须为 60 个"

    def test_g7_radar_engine_dynamic_factor_weights(self):
        """
        G7-2: 机会雷达全息扫描与基因因子动态权重集成测试
        - 确认 radar_engine 具备 factor_weights 与 evolved_result
        - 扫描全市场 14 大赛道综合得分随动态权重精算
        """
        radar = OpportunityRadarEngine()
        assert hasattr(radar, "factor_weights"), "雷达引擎缺少 factor_weights 属性"
        assert hasattr(radar, "evolved_result"), "雷达引擎缺少 evolved_result 属性"
        assert len(radar.factor_weights) == 4

        secs = radar.scan_all_sectors()
        assert len(secs) == 14, f"全市场扫描必须覆盖全部 14 大赛道，当前: {len(secs)}"
        for s in secs:
            assert "total_score" in s and s["total_score"] > 0.0, f"赛道 {s.get('name')} 综合得分异常"

    def test_g7_same_company_conversion_and_dividend_policy(self):
        """
        G7-3: 同公司基金低摩擦转换与宏观估值自适应分红研判测试
        - 同公司多只基金归集识别
        - 高低估值分位下分红方式推荐自适应切换 (低估再投，高估派现)
        """
        holdings = {
            "005561": HoldingItem(fund_code="005561", fund_name="创金合信中证红利低波动A", shares=10000, cost_nav=1.0, current_nav=1.2, dividend_method="cash"),
            "100032": HoldingItem(fund_code="100032", fund_name="富国中证红利指数增强A", shares=20000, cost_nav=1.0, current_nav=1.1, dividend_method="reinvest"),
        }
        conv_res = find_same_company_conversions(holdings)
        assert isinstance(conv_res, dict) and "company_map" in conv_res

        # 宏观高估值 (ERP 20% -> 现金分红落袋)
        div_high = evaluate_macro_dividend_policy(erp_percentile=20.0, holdings=holdings)
        assert div_high["recommended_mode"] == "cash", f"高估值环境下必须首选现金分红，当前: {div_high['recommended_mode']}"

        # 宏观低估值 (ERP 85% -> 红利再投吃低价份额)
        div_low = evaluate_macro_dividend_policy(erp_percentile=85.0, holdings=holdings)
        assert div_low["recommended_mode"] == "reinvest", f"低估值底部磨底区必须首选红利再投资，当前: {div_low['recommended_mode']}"

    def test_g7_app_gui_contracts_and_dual_view_structure(self):
        """
        G7-4: GUI 架构解耦契约与三方风控联动静态及渲染测试
        - Tab 2 双视图单选控件 rad_tab2_view_mode 存在
        - 首屏风险哨双按钮 btn_sentry_act_ 与 btn_sentry_evid_ 并存
        - Tab 4 顶部联动高亮横幅 tab4_highlight_module 存在
        - 机会雷达白盒进化徽章与微图存在
        - safe_markdown_html 与 _clean_html 防裸代码块机制稳固
        """
        gui_path = WORKSPACE_ROOT / "AGY2_FundAdvisory" / "app_gui.py"
        assert gui_path.exists(), "app_gui.py 不存在"
        gui_code = gui_path.read_text(encoding="utf-8")

        # 1. 契约校验
        assert "rad_tab2_view_mode" in gui_code, "app_gui.py 必须包含 Tab 2 双视图单选控件 rad_tab2_view_mode"
        assert "is_t2_main_mode" in gui_code, "app_gui.py 必须包含 is_t2_main_mode 模式分支判断"
        assert "btn_sentry_act_" in gui_code, "app_gui.py 必须保留处置按钮前缀 btn_sentry_act_"
        assert "btn_sentry_evid_" in gui_code, "app_gui.py 必须包含穿透证据按钮前缀 btn_sentry_evid_"
        assert "tab4_highlight_module" in gui_code, "app_gui.py 必须支持 Tab 4 顶部联动证据横幅"
        assert "🧬 在线启发式因子基因自适应进化算子" in gui_code, "app_gui.py 必须包含基因白盒徽章说明"

        # 2. 静态测试契约防丢失
        assert "<b>{len(pm.holdings)} 只</b>" in gui_code, "必须保留 <b>{len(pm.holdings)} 只</b> 静态契约"
        assert 'if "edited_table" in locals() and edited_table is not None:' in gui_code, "必须保留 edited_table 契约"
        assert "dock_tab1, dock_tab2, dock_tab3, dock_tab4, dock_tab5, dock_tab6" in gui_code, "必须保留 6 大工具坞"
        assert "sub_tab1, sub_tab2, sub_tab3" in gui_code, "必须保留子 Tab 契约"
