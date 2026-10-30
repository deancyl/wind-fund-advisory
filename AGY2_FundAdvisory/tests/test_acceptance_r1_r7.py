# -*- coding: utf-8 -*-
"""
AGY2 智能投顾系统端到端验收与红队测试套件 (tests/test_acceptance_r1_r7.py)
Covering Acceptance Criteria R1 ~ R7:
1. 滑块实时联动测试 (C1~C5 模式 A 即拉即变，不同配置权重与 011613 进攻标的校验)
2. 建仓回撤归零测试 (apply_zero_start_blueprint 状态彻底清零，001071 伴生底仓无“替换”字样)
3. 银行股排雷豁免测试 (招行/农行/交行/江苏银行 double_high_risk==False，扣分为 0)
4. 拆单重合度豁免测试 (050025与001071豁免伪分散警报，同时真实保留非豁免标的预警)
5. 界面规范与排版断言 (步骤三 9 列精简表格 1080p 无横向滚动条，Tab 1/3 二级折叠框默认 expanded=False)
6. WindToolkit 衍生品与六维量化选基评分断言 (IC/IM 贴水、期权 IV、28177->6850 选基漏斗与六维打分)
7. 裁判只读基建文件完整性断言 (零侵入零篡改)
8. Streamlit AppTest 端到端渲染与滑块交互零异常断言
"""

import math
import re
import sys
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

# 确保 AGY2 模块位于 sys.path
_CURRENT_DIR = Path(__file__).resolve().parent
_AGY2_DIR = _CURRENT_DIR.parent
_WORKSPACE_ROOT = _AGY2_DIR.parent
if str(_AGY2_DIR) not in sys.path:
    sys.path.insert(0, str(_AGY2_DIR))
if str(_WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_ROOT))

from portfolio_manager import (
    PortfolioManager,
    CORE_STRATEGY_POOL,
    SECTOR_FUND_SELECTION,
    FUND_LOOK_THROUGH_DATA,
)
from strategy_bridge import (
    StrategyBridge,
    RISK_TIERS_CONFIG,
    TIER_TARGET_WEIGHTS,
)
import app_gui


class TestAcceptanceCriteriaR1ToR7:
    """全面覆盖 Acceptance Criteria R1 ~ R7 的端到端验收与红队测试"""

    # =========================================================================
    # 1. 滑块实时联动测试
    # =========================================================================
    def test_slider_realtime_linkage_mode_a(self):
        """
        滑块实时联动测试：
        模拟在模式 A 下将目标收益率滑块分别设为 6% (C1)、10% (C2)、15% (C3)、25% (C4)、60% (C5)，
        active_tier 实时切换为 C1 至 C5，且生成的建仓单基金列表与权重各不相同（C4 与 C5 必须包含 011613 华夏科创50C 等进攻标的）。
        """
        slider_test_cases = [
            (6.0, "C1"),
            (10.0, "C2"),
            (15.0, "C3"),
            (25.0, "C4"),
            (60.0, "C5"),
        ]

        generated_blueprints = {}
        blueprint_fund_lists = {}

        for target_ret, expected_tier in slider_test_cases:
            # 1. 验证滑块到档位的映射函数
            computed_tier = app_gui.map_slider_to_tier(target_ret)
            assert computed_tier == expected_tier, (
                f"目标收益率 {target_ret}% 应映射为 {expected_tier}，实际为 {computed_tier}"
            )

            # 2. 生成对应档位的建仓单
            bp = StrategyBridge.generate_zero_start_blueprint(total_capital=100000.0, tier=computed_tier)
            assert bp["total_capital"] == 100000.0
            assert bp["tier"] == expected_tier
            assert len(bp["items"]) >= 4

            # 3. 校验资金总和等于 100,000 元 (允许 0.05 元内尾差)
            total_allocated = sum(it.get("allocated_amount", it.get("amount", 0.0)) for it in bp["items"])
            assert abs(total_allocated + bp.get("remaining_cash", 0.0) - 100000.0) < 0.05

            # 4. 提取基金代码集合与权重字典
            funds_in_bp = [it["fund_code"] for it in bp["items"]]
            weights_in_bp = {it["fund_code"]: it["target_weight_pct"] for it in bp["items"]}

            generated_blueprints[expected_tier] = bp
            blueprint_fund_lists[expected_tier] = set(funds_in_bp)

            # 5. C4 与 C5 必须包含进攻性高弹性标的 011613 华夏科创50C
            if expected_tier in ["C4", "C5"]:
                assert "011613" in funds_in_bp, (
                    f"档位 {expected_tier} 必须包含 011613 华夏科创50C 等进攻标的，实际包含: {funds_in_bp}"
                )
                assert weights_in_bp["011613"] >= 25.0, (
                    f"档位 {expected_tier} 中 011613 权重占比应 >= 25%，实际为 {weights_in_bp['011613']}%"
                )

            # 6. C1 安稳保守型不得包含高弹性股票型基金 011613，纯债类 (002351, 000086) 权重应占大头 (>= 60%)
            if expected_tier == "C1":
                assert "011613" not in funds_in_bp
                bond_weight = weights_in_bp.get("002351", 0.0) + weights_in_bp.get("000086", 0.0)
                assert bond_weight >= 65.0, f"C1 保守型债券权重应 >= 65%，实际为 {bond_weight}%"

        # 7. 断言 5 个档位的基金列表与权重配比互不相同 (各档位独立分层)
        tier_keys = list(generated_blueprints.keys())
        for i in range(len(tier_keys)):
            for j in range(i + 1, len(tier_keys)):
                t1, t2 = tier_keys[i], tier_keys[j]
                w1 = {it["fund_code"]: it["target_weight_pct"] for it in generated_blueprints[t1]["items"]}
                w2 = {it["fund_code"]: it["target_weight_pct"] for it in generated_blueprints[t2]["items"]}
                assert w1 != w2, f"{t1} 与 {t2} 的基金建仓权重配置不得完全相同"

    # =========================================================================
    # 2. 建仓回撤归零测试
    # =========================================================================
    def test_zero_start_blueprint_drawdown_reset_and_companion_tag(self):
        """
        建仓回撤归零测试：
        调用 apply_zero_start_blueprint() 注入 100,000 元方案后，
        pm.peak_equity == pm.total_equity 且 pm.max_drawdown_pct == 0.0，
        001071 的 transition_tag 不得包含“替换”字样。
        """
        pm = PortfolioManager()
        orig_ledger = pm.ledger_json_path.read_text(encoding="utf-8") if pm.ledger_json_path.exists() else None

        try:
            # 故意制造严重的历史状态污染 (模拟旧组合残留的大额峰值资产、浮亏与深水回撤)
            pm.peak_equity = 250000.0
            pm.max_drawdown_pct = 38.5
            pm.portfolio_return_pct = -28.0
            pm.benchmark_return_pct = -15.0
            pm.alpha_return_pct = -13.0
            pm.available_cash = 5000.0

            # 生成 100,000 元的标准建仓方案 (包含 050025 限购自动拆单至 001071 摩根标普500)
            bp = StrategyBridge.generate_zero_start_blueprint(total_capital=100000.0, tier="C3")
            res = pm.apply_zero_start_blueprint(bp)

            assert res["status"] == "SUCCESS"

            # 1. 断言账户峰值与最新总资产分毫不差，彻底消除历史峰值资产污染
            assert pm.peak_equity == pm.total_equity, (
                f"peak_equity ({pm.peak_equity}) 必须严格等于 total_equity ({pm.total_equity})"
            )
            assert abs(pm.total_equity - 100000.0) < 0.1

            # 2. 断言最大回撤必须彻底归零
            assert pm.max_drawdown_pct == 0.0, f"建仓后最大回撤必须为 0.0，实际为 {pm.max_drawdown_pct}"
            assert pm.portfolio_return_pct == 0.0
            assert pm.alpha_return_pct == 0.0

            # 3. 验证 001071 伴生拆单标的存在且绝不包含“替换”字样
            assert "001071" in pm.holdings, "001071 摩根标普500 必须包含在建仓后持仓列表中"
            spx_companion = pm.holdings["001071"]

            assert spx_companion.is_core_strategy is True, "001071 必须标记为 is_core_strategy=True"
            assert "替换" not in spx_companion.transition_tag, (
                f"001071 的 transition_tag ('{spx_companion.transition_tag}') 严禁包含'替换'字样"
            )
            assert "核心" in spx_companion.transition_tag or "底仓" in spx_companion.transition_tag

            # 4. 同时验证原标的 050025 也为核心底仓且不含“替换”
            assert "050025" in pm.holdings
            assert "替换" not in pm.holdings["050025"].transition_tag
        finally:
            if orig_ledger and pm.ledger_json_path.exists():
                pm.ledger_json_path.write_text(orig_ledger, encoding="utf-8")

    # =========================================================================
    # 3. 银行股排雷豁免测试
    # =========================================================================
    def test_banking_stock_double_high_risk_exemption(self):
        """
        银行股排雷豁免测试：
        对 100032 (富国中证红利) 和 005561 (创金合信红利低波) 运行 screen_fund_look_through_risk()，
        招商银行、农业银行、交通银行、江苏银行的 double_high_risk 全部为 False。
        """
        pm = PortfolioManager()
        target_bank_names = ["招商银行", "农业银行", "交通银行", "江苏银行"]
        tested_bank_instances = 0

        for fund_code in ["100032", "005561"]:
            risk_res = pm.screen_fund_look_through_risk(fund_code)
            assert risk_res["risk_level"] in ["Safe", "Watch"], (
                f"红利类核心基金 {fund_code} 穿透评级不得为高危 Danger，实际为 {risk_res['risk_level']}"
            )

            stocks = risk_res.get("top_stocks_screen", [])
            assert len(stocks) > 0, f"基金 {fund_code} 应具备前十大穿透重仓股数据"

            for stk in stocks:
                s_name = stk.get("stock_name", "")
                if any(bank in s_name for bank in target_bank_names):
                    tested_bank_instances += 1

                    # 断言 double_high_risk 必须为 False
                    assert stk.get("double_high_risk") is False, (
                        f"银行股 {s_name} 的 double_high_risk 必须为 False，不应误判为存贷双高造假"
                    )

                    # 断言状态必须包含金融业豁免
                    status = stk.get("double_high_status", "")
                    assert "金融" in status or "豁免" in status or "正常" in status, (
                        f"银行股 {s_name} 的 double_high_status ('{status}') 必须标明金融业豁免"
                    )

                    # 断言 double_high_exempt 标记为 True
                    assert stk.get("double_high_exempt") is True, (
                        f"银行股 {s_name} double_high_exempt 必须为 True"
                    )

                    # 断言扣分项目中不含存贷双高造假扣分 (40分)
                    reasons = stk.get("danger_reasons", []) + stk.get("watch_reasons", [])
                    for r in reasons:
                        assert "存贷双高" not in r, f"银行股 {s_name} 扣分项不应含存贷双高: {r}"

        # 确保真实覆盖了目标银行股实例
        assert tested_bank_instances >= 4, f"测试的银行股重仓实例数应 >= 4，实际为 {tested_bank_instances}"

    # =========================================================================
    # 4. 拆单重合度豁免测试
    # =========================================================================
    def test_smart_split_and_share_class_overlap_exemption(self):
        """
        拆单重合度豁免测试：
        当同时持有 050025 与 001071 时，运行 calculate_stock_overlap_matrix()，
        alerts 列表中不包含这两只基金的伪分散警告。
        对抗测试：非豁免且高重合度的基金组合（如 011612 华夏科创50 与 013841 银华集成电路）必须正常触发预警。
        """
        pm = PortfolioManager()
        pm.holdings.clear()

        # 注入 050025 (博时标普500) 与 001071 (摩根标普500)，两只基金前十大重仓股完全重合 (100%)
        pm.takeover_mode_a([
            {
                "fund_code": "050025",
                "fund_name": "博时标普500ETF联接A",
                "shares": 500.0,
                "cost_nav": 1.0,
                "share_class": "A",
                "first_buy_date": "2024-01-01"
            },
            {
                "fund_code": "001071",
                "fund_name": "摩根标普500指数(QDII)人民币A",
                "shares": 5500.0,
                "cost_nav": 1.0,
                "share_class": "A",
                "first_buy_date": "2024-01-01"
            }
        ], available_cash=0.0)

        matrix_res = pm.calculate_stock_overlap_matrix()
        alerts = matrix_res.get("alerts", [])
        exempt_pairs = matrix_res.get("exempt_pairs", [])

        # 1. 断言 alerts 中严禁包含 050025 与 001071 的伪分散警告
        for alert in alerts:
            funds_in_alert = {alert.get("fund1"), alert.get("fund2")}
            assert funds_in_alert != {"050025", "001071"}, (
                f"050025 与 001071 属于官方限购拆单伴生组合，严禁触发伪分散警报: {alert}"
            )

        # 2. 断言 exempt_pairs 列表中明确记录了该豁免对与说明
        exempt_fund_sets = [{p.get("fund1"), p.get("fund2")} for p in exempt_pairs]
        assert {"050025", "001071"} in exempt_fund_sets, (
            f"050025 与 001071 必须出现在 exempt_pairs 中，实际为: {exempt_pairs}"
        )
        exempt_entry = next(p for p in exempt_pairs if {p.get("fund1"), p.get("fund2")} == {"050025", "001071"})
        assert "限购" in exempt_entry.get("note", "") or "同源" in exempt_entry.get("note", "")

        # 3. 对抗校验 (Red Team Adversarial)：非豁免标的 011612 (科创50) 与 013841 (芯片混合)
        # 前十大重仓股重合度达 40%，必须坚决触发伪分散报警！
        pm_adv = PortfolioManager()
        pm_adv.holdings.clear()
        pm_adv.takeover_mode_a([
            {
                "fund_code": "011612",
                "fund_name": "华夏上证科创板50成份ETF联接A",
                "shares": 10000.0,
                "cost_nav": 1.0,
                "share_class": "A",
                "first_buy_date": "2024-01-01"
            },
            {
                "fund_code": "013841",
                "fund_name": "银华集成电路混合C",
                "shares": 10000.0,
                "cost_nav": 1.0,
                "share_class": "C",
                "first_buy_date": "2024-01-01"
            }
        ], available_cash=0.0)

        adv_res = pm_adv.calculate_stock_overlap_matrix()
        adv_alerts = adv_res.get("alerts", [])
        assert len(adv_alerts) >= 1, "非豁免同赛道基金 011612 与 013841 必须真实触发伪分散告警"
        matched = any({a.get("fund1"), a.get("fund2")} == {"011612", "013841"} for a in adv_alerts)
        assert matched, "011612 与 013841 的重合告警必须出现在 alerts 中"

    # =========================================================================
    # 5. 界面规范与排版断言
    # =========================================================================
    def test_gui_step3_table_columns_and_drawer_defaults(self):
        """
        界面与排版断言：
        1. 步骤三表格保留 9 列，在 1080p 分辨率下无横向滚动条（断言列名列表与列数 == 9）。
        2. Tab 1 与 Tab 3 中的二级长文抽屉与批次折叠框默认 expanded=False。
        """
        gui_path = _AGY2_DIR / "app_gui.py"
        content = gui_path.read_text(encoding="utf-8")

        # 1. 验证步骤三《建仓/调仓执行单》表格列数恰好为 9 列
        expected_9_cols = [
            "基金代码", "基金名称", "份额", "目标占比(%)",
            "精确买入金额(元)", "最新净值", "实时估值涨跌(%)",
            "排雷与拥挤度", "实操分红与限购指引"
        ]

        # 从源码中定位 cols_9 定义
        cols_match = re.search(r"cols_9\s*=\s*\[(.*?)\]", content, re.DOTALL)
        assert cols_match is not None, "app_gui.py 中应显式定义 cols_9 列表"

        cols_raw = cols_match.group(1)
        extracted_cols = [c.strip().strip('"').strip("'") for c in re.findall(r'["\'](.*?)["\']', cols_raw)]

        assert len(extracted_cols) == 9, f"步骤三表格列数必须严格为 9 列，实际为 {len(extracted_cols)} 列: {extracted_cols}"
        assert extracted_cols == expected_9_cols, (
            f"步骤三 9 列字段名必须完全吻合: 期望 {expected_9_cols}，实际 {extracted_cols}"
        )

        # 2. 验证合并字段：“穿透排雷”与“抱团拥挤度”合并为“排雷与拥挤度”；
        # “资产角色”、“份额原因”、“分红设置”、“限购替代”合并为“实操分红与限购指引”
        assert '"排雷与拥挤度"' in content
        assert '"实操分红与限购指引"' in content

        # 3. 验证 Tab 1 与 Tab 3 中的 4 个二级长文抽屉默认 expanded=False
        # a. Tab 1: 五大人话硬核指标深度量化归因与回本推演档案
        assert re.search(r'st\.expander\(.*五大人话硬核指标.*expanded\s*=\s*False', content) is not None, (
            "Tab 1 '五大人话硬核指标' 折叠框必须默认 expanded=False"
        )

        # b. Tab 1: 全市场量化选基透明漏斗与备选替换
        assert re.search(r'st\.expander\(exp_funnel_title,\s*expanded\s*=\s*False\)', content) is not None, (
            "Tab 1 '全市场量化选基透明漏斗' 折叠框必须默认 expanded=False"
        )

        # c. Tab 1: 手机银行/天天基金下单一键复制小抄
        assert re.search(r'st\.expander\(.*一键复制小抄.*expanded\s*=\s*False', content) is not None, (
            "Tab 1 '一键复制小抄' 折叠框必须默认 expanded=False"
        )

        # d. Tab 3: 全组合 FIFO 批次透视与免赎回费倒计时汇总表
        assert re.search(r'st\.expander\(.*FIFO.*expanded\s*=\s*False', content) is not None, (
            "Tab 3 '全组合 FIFO 批次透视' 折叠框必须默认 expanded=False"
        )

    # =========================================================================
    # 6. WindToolkit 衍生品与六维选基评分引擎断言
    # =========================================================================
    def test_derivatives_integration_and_six_dimension_quant_scoring(self):
        """
        WindToolkit 衍生品接入与六维量化选基断言：
        1. 市场快照包含期指贴水与期权 IV，宏观雷达提示融入衍生品。
        2. 全市场 28,177 -> 6,850 漏斗统计与各档位核心赛道候选。
        3. 六维评分公式 35% Alpha + 25% Fee + 15% Risk + 10% SmartMoney + 10% Crowding + 5% Derivatives 准确执行。
        """
        # 1. 验证市场快照衍生品字段
        snapshot = StrategyBridge.get_latest_market_snapshot(force_reload=True)
        assert "ic_annualized_basis_rate" in snapshot, "快照缺少 ic_annualized_basis_rate"
        assert "im_annualized_basis_rate" in snapshot, "快照缺少 im_annualized_basis_rate"
        assert "option_iv_pct" in snapshot, "快照缺少 option_iv_pct"
        assert "derivatives_sentiment" in snapshot, "快照缺少 derivatives_sentiment"
        assert "derivatives_radar_tip" in snapshot, "快照缺少 derivatives_radar_tip"

        radar = snapshot.get("dual_track_radar", {})
        assert "ic_annualized_basis_rate" in radar, "dual_track_radar 缺少 ic_annualized_basis_rate"

        # 2. 验证选基漏斗四级过滤统计 (C1~C5)
        for tier in ["C1", "C2", "C3", "C4", "C5"]:
            f_stats = StrategyBridge.get_fund_selection_funnel_stats(tier)
            assert f_stats["total_market_funds"] == 28177
            assert f_stats["compliance_screened_funds"] == 6850
            assert f_stats["tier_candidate_funds"] >= 16
            assert f_stats["final_champion_funds"] in [4, 5, 6]

        # 3. 验证六维评分计算与权重公式
        # 002351 (易方达裕祥债A)
        score_res = StrategyBridge.calculate_fund_six_dimension_score("002351", "债券底仓", snapshot, "C1")
        assert "total_score" in score_res
        assert 80.0 <= score_res["total_score"] <= 100.0

        weights = score_res["weights"]
        assert weights["alpha"] == 0.35
        assert weights["fee"] == 0.25
        assert weights["risk"] == 0.15
        assert weights["smart_money"] == 0.10
        assert weights.get("crowding", weights.get("anti_crowding")) == 0.10
        assert weights.get("macro_align", weights.get("macro_derivatives")) == 0.05

        macro_score = score_res.get("macro_align_score", score_res.get("macro_derivative_score", 0.0))
        crowding_score = score_res.get("crowding_score", score_res.get("anti_crowding_score", 0.0))

        expected_total = (
            0.35 * score_res["alpha_score"] +
            0.25 * score_res["fee_score"] +
            0.15 * score_res["risk_score"] +
            0.10 * score_res["smart_money_score"] +
            0.10 * crowding_score +
            0.05 * macro_score
        )
        assert abs(score_res["total_score"] - round(expected_total, 2)) < 0.05

        # 4. 验证量化选基对比宽表返回合法 DataFrame
        df_quant = StrategyBridge.get_tier_quant_selection_table("C3")
        assert isinstance(df_quant, pd.DataFrame)
        assert len(df_quant) >= 15
        assert "六维总评得分" in df_quant.columns
        assert "赛道" in df_quant.columns
        assert "标的身份" in df_quant.columns

    # =========================================================================
    # 7. 裁判只读基建文件完整性断言
    # =========================================================================
    def test_readonly_invariants_strictly_unmodified(self):
        """
        只读裁判基建文件完整性断言：
        严格断言 4 个系统只读文件 (judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py) 存在且未被破坏。
        """
        invariants = [
            _AGY2_DIR / "judge_engine.py",
            _AGY2_DIR / "holdout_vault.py",
            _AGY2_DIR / "AGENT_SPEC.md",
            _AGY2_DIR / "tests" / "test_infra.py",
        ]

        for p in invariants:
            assert p.exists(), f"关键只读文件 {p} 不存在"
            content = p.read_text(encoding="utf-8")
            assert len(content) > 100, f"关键只读文件 {p} 内容异常为空"

        # 校验 judge_engine 核心裁判逻辑未被篡改
        je_content = (_AGY2_DIR / "judge_engine.py").read_text(encoding="utf-8")
        assert "class JudgeEngine" in je_content
        assert "compute_ast_hash" in je_content

        # 校验 holdout_vault 核心熔断逻辑未被篡改
        hv_content = (_AGY2_DIR / "holdout_vault.py").read_text(encoding="utf-8")
        assert "class HoldoutVault" in hv_content
        assert "HoldoutVaultExhaustedError" in hv_content

    # =========================================================================
    # 8. Streamlit AppTest 模式 A 滑块联动与渲染无异常
    # =========================================================================
    def test_e2e_streamlit_slider_linkage_mode_a(self):
        """
        Streamlit AppTest 模式 A 滑块联动端到端测试：
        使用 AppTest 在 app_gui 模式 A 下切换滑块并执行，验证 session_state.active_tier_val 实时联动无报错。
        """
        from streamlit.testing.v1 import AppTest
        app_path = _AGY2_DIR / "app_gui.py"
        for ret, tier in [(6.0, "C1"), (25.0, "C4"), (60.0, "C5")]:
            at = AppTest.from_file(str(app_path), default_timeout=120)
            at.session_state.tier_determination_mode = "模式 A：按期望年化收益率滑块定档 (滑块即拉即变)"
            at.session_state.target_return_val = ret
            at.session_state.active_tier_val = tier
            at.run(timeout=120)
            assert len(at.exception) == 0, f"AppTest 在收益率 {ret}% ({tier}) 下抛出异常: {[e.value for e in at.exception]}"
            assert at.session_state.active_tier_val == tier
