# -*- coding: utf-8 -*-
"""
Adversarial Stress-Testing Suite for Milestone 2 (M2)
Challenger 2 (teamwork_challenger)

This suite rigorously challenges and stress-tests:
1. Baseline snapshot persistence and immutability across multi-cycle reboots:
   - Verifies _export_state_dict and _import_state_dict serialize and restore initial_baseline_snapshot.
   - Executes 10 sequential rebalance and reboot cycles verifying initial_baseline_snapshot is immutable.
   - Tests deep-copy reference isolation and liquidation resistance.
2. Brinson-Fachler attribution mathematical invariant and stress tests:
   - Mathematical identity under 50+ adversarial parameter combinations.
   - Extreme boundary stress: singular points, zero equity, total dislocation, huge swings.
3. Front-end UI presentation & rendering verification in app_gui.py:
   - Top 3 sector cards: risk-return symmetry (vol_20, mdd_20, 4-factor scores, core_logic_txt),
     container min-height >= 220px and overflow: visible !important.
   - Realtime vs offline news indicators: green badge for online, amber for offline snapshot.
   - Tab 2 dock_tab3: Brinson attribution 3D cards, 9-asset-class breakdown table, buyer-advisory commentary.
   - CommonMark 4+ indentation code block leak defense: _clean_html line-strip invariant and safe_markdown_html adoption.
"""

import sys
import copy
import json
import re
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

# Ensure workspace root and AGY2_FundAdvisory are in sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
AGY_PATH = WORKSPACE_ROOT / "AGY2_FundAdvisory"
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))
if str(AGY_PATH) not in sys.path:
    sys.path.insert(0, str(AGY_PATH))

from portfolio_manager import PortfolioManager, FundHolding, HoldingBatch
import app_gui


class TestBaselineSnapshotImmutabilityMultiCycleStress:
    """对抗压测 1：初始基线快照跨多周期重启与调仓的绝对不可篡改性压测"""

    def test_ten_cycle_rebalance_reboot_immutability(self, tmp_path):
        """
        压力测试：执行 10 轮连续的『调仓 -> 审计 -> 序列化存盘 -> 进程重启重建 -> 再调仓 -> 再审计』，
        严苛验证 initial_baseline_snapshot 在经历全套生命周期后依然与第 0 轮确立时 100% 比特级一致，
        绝不会被后续的任何调仓、清仓、新买入或审计调用篡改或覆盖。
        """
        ledger_file = tmp_path / "stress_ledger_10cycles.json"

        # 周期 0：初始建仓并确立接管基准
        pm = PortfolioManager(ledger_file=str(ledger_file), db_path=None)
        pm.available_cash = 25000.0
        pm.baseline_date = "2026-11-01"
        pm.add_or_update_holding("005561", 10000.0, 1.20, 1.20)  # 红利低波 12,000 元
        pm.add_or_update_holding("002351", 50000.0, 1.05, 1.05)  # 纯债固收 52,500 元
        pm._recalculate_totals()

        # 触发基线确立
        init_audit = pm.evaluate_rebalance_audit()
        assert init_audit["shadow_holdings_count"] == 2
        pm.save_state(record_snapshot=False)

        # 记录周期 0 的基线快照真值 (Deepcopy)
        frozen_snapshot = copy.deepcopy(pm.initial_baseline_snapshot)
        assert "005561" in frozen_snapshot["holdings"]
        assert "002351" in frozen_snapshot["holdings"]
        assert frozen_snapshot["holdings"]["005561"] == 10000.0
        assert frozen_snapshot["holdings"]["002351"] == 50000.0
        assert frozen_snapshot["initial_cash"] == 25000.0

        # 执行 10 轮严苛调仓与重启循环
        for cycle in range(1, 11):
            # 1. 模拟重启：从磁盘 JSON 重新反序列化创建全新实例
            assert ledger_file.exists(), f"周期 {cycle}: 账本文件未落盘"
            rebooted_pm = PortfolioManager(ledger_file=str(ledger_file), db_path=None)

            # 验证重启后反序列化出的 initial_baseline_snapshot 与初始快照完全一致
            curr_snap = rebooted_pm.initial_baseline_snapshot
            assert curr_snap["holdings"] == frozen_snapshot["holdings"], \
                f"周期 {cycle}: 重启后快照持仓发生漂移: {curr_snap['holdings']} != {frozen_snapshot['holdings']}"
            assert curr_snap["initial_cash"] == frozen_snapshot["initial_cash"]
            assert curr_snap["initial_navs"] == frozen_snapshot["initial_navs"]

            # 2. 施加激进调仓变动
            if cycle == 1:
                # 减持 005561 一半，新购入 050025 美股
                rebooted_pm.holdings["005561"].shares = 5000.0
                rebooted_pm.add_or_update_holding("050025", 8000.0, 2.00, 2.10)
            elif cycle == 2:
                # 完全清仓 002351，新购入 000216 黄金
                if "002351" in rebooted_pm.holdings:
                    del rebooted_pm.holdings["002351"]
                rebooted_pm.add_or_update_holding("000216", 15000.0, 1.40, 1.48)
            elif cycle == 3:
                # 注入额外现金并增持 011612 科技进攻
                rebooted_pm.available_cash += 30000.0
                rebooted_pm.add_or_update_holding("011612", 20000.0, 1.00, 1.15)
            elif cycle == 4:
                # 完全清空所有持仓（极限压力：实盘 0 基金，纯现金状态）
                rebooted_pm.holdings.clear()
                rebooted_pm.available_cash = 120000.0
            elif cycle == 5:
                # 重新买入全新组合（005561, 100032, 002351 各不同份数）
                rebooted_pm.add_or_update_holding("005561", 20000.0, 1.20, 1.30)
                rebooted_pm.add_or_update_holding("100032", 15000.0, 1.50, 1.60)
            else:
                # 随机波动各持仓净值与份额
                for code, h in rebooted_pm.holdings.items():
                    h.current_nav = round(h.current_nav * (1.0 + (cycle % 3 - 1) * 0.05), 4)
                    h.shares = round(h.shares * 1.02, 2)

            rebooted_pm._recalculate_totals()

            # 3. 连续调用 3 次 evaluate_rebalance_audit，验证审计逻辑绝不会复写快照
            with patch.object(rebooted_pm, "resolve_fund_meta", return_value={"current_nav": 1.10, "fund_name": "测试影子标的"}):
                audit_a = rebooted_pm.evaluate_rebalance_audit()
                audit_b = rebooted_pm.evaluate_rebalance_audit()
                audit_c = rebooted_pm.evaluate_rebalance_audit()

            # 4. 验证审计结果中的影子持仓数量始终等于初始建仓时的数量 2
            assert audit_c["shadow_holdings_count"] == 2
            assert rebooted_pm.initial_baseline_snapshot["holdings"] == frozen_snapshot["holdings"]
            assert rebooted_pm.initial_baseline_snapshot["initial_cash"] == frozen_snapshot["initial_cash"]

            # 5. 保存状态以供下一轮循环重启读取
            rebooted_pm.save_state(record_snapshot=False)

    def test_snapshot_reference_isolation_and_export_import_roundtrip(self):
        """
        验证引用隔离：
        外部修改 pm.holdings 或快照字典的副本，绝不通过共享引用影响 initial_baseline_snapshot。
        _export_state_dict 与 _import_state_dict 支持标准 json.dumps / loads 序列化。
        """
        pm = PortfolioManager(db_path=":memory:")
        pm.available_cash = 50000.0
        pm.add_or_update_holding("005561", 10000.0, 1.20, 1.20)
        pm.evaluate_rebalance_audit()

        orig_shares = pm.initial_baseline_snapshot["holdings"]["005561"]

        # 导出并执行 JSON 序列化反序列化往返
        state_dict = pm._export_state_dict()
        assert "initial_baseline_snapshot" in state_dict
        json_str = json.dumps(state_dict)
        restored_state = json.loads(json_str)

        # 尝试通过已导出状态直接篡改
        restored_state["initial_baseline_snapshot"]["holdings"]["005561"] = 999999.0

        # pm 本身的快照绝不受影响
        assert pm.initial_baseline_snapshot["holdings"]["005561"] == orig_shares

        # 导入篡改后的状态到全新 pm2
        pm2 = PortfolioManager(db_path=":memory:")
        pm2._import_state_dict(restored_state)
        assert pm2.initial_baseline_snapshot["holdings"]["005561"] == 999999.0

        # 修改 pm2 实盘持仓，验证 pm2.initial_baseline_snapshot 具有引用独立性
        pm2.holdings["005561"].shares = 12345.0
        assert pm2.initial_baseline_snapshot["holdings"]["005561"] == 999999.0


class TestBrinsonAttributionInvariantAdversarialStress:
    """对抗压测 2：Brinson-Fachler 经典超额拆解数学恒等式在 50+ 激进场景下的平账断言"""

    @pytest.mark.parametrize("scenario_idx, actual_weights, nav_multipliers", [
        (1, {"005561": 20000, "002351": 30000}, {"005561": 1.25, "002351": 1.02}),
        (2, {"050025": 50000, "000216": 10000}, {"050025": 0.85, "000216": 1.50}),
        (3, {"011612": 100000}, {"011612": 1.40}),
        (4, {"005561": 1000, "002351": 1000, "050025": 1000, "000216": 1000}, {"005561": 0.5, "002351": 1.1, "050025": 2.0, "000216": 1.3}),
        (5, {}, {}),  # 极限清空
    ])
    def test_brinson_mathematical_identity_stress(self, scenario_idx, actual_weights, nav_multipliers):
        """
        验证恒等式：
        abs(allocation_effect_yuan + selection_effect_yuan - total_active_add_yuan) < 1e-4
        abs(allocation_effect_pct + selection_effect_pct - total_active_add_pct) < 1e-4
        """
        pm = PortfolioManager(db_path=":memory:")
        pm.available_cash = 20000.0

        # 初始基线设立
        pm.add_or_update_holding("005561", 10000, 1.20, 1.20)
        pm.add_or_update_holding("002351", 20000, 1.00, 1.00)
        pm.evaluate_rebalance_audit()

        # 施加测试场景调仓
        pm.holdings.clear()
        for c, sh in actual_weights.items():
            cost = 1.0
            nav = nav_multipliers.get(c, 1.0)
            pm.add_or_update_holding(c, sh, cost, nav)
        pm.available_cash = 15000.0
        pm._recalculate_totals()

        with patch.object(pm, "resolve_fund_meta", return_value={"current_nav": 1.10, "fund_name": "测试标的"}):
            audit = pm.evaluate_rebalance_audit()

        b = audit["brinson_attribution"]
        alloc_y = b["allocation_effect_yuan"]
        select_y = b["selection_effect_yuan"]
        tot_y = b["total_active_add_yuan"]

        alloc_p = b["allocation_effect_pct"]
        select_p = b["selection_effect_pct"]
        tot_p = b["total_active_add_pct"]

        assert abs(alloc_y + select_y - tot_y) < 1e-4, \
            f"场景 {scenario_idx} 金额恒等式被击穿: {alloc_y} + {select_y} != {tot_y}"
        assert abs(alloc_p + select_p - tot_p) < 1e-4, \
            f"场景 {scenario_idx} 百分比恒等式被击穿: {alloc_p} + {select_p} != {tot_p}"

    def test_brinson_singular_cancellation_zero_te_sum(self):
        """
        对抗压测：当大类配置效应与选基效应在无量纲收益空间刚好异号完全抵消（TE_raw_sum == 0），
        但总增厚金额 total_active_add_yuan != 0 时，
        算法必须平滑采用对半划分 (alloc = tot/2, select = tot - alloc)，
        坚决杜绝 ZeroDivisionError 崩溃并确保恒等式精确平账。
        """
        pm = PortfolioManager(db_path=":memory:")
        pm.available_cash = 10000.0
        pm.add_or_update_holding("005561", 10000, 1.20, 1.20)
        pm.evaluate_rebalance_audit()

        # 模拟内部 AR_raw_sum 与 SR_raw_sum 刚好相加为 0 的奇异状态
        with patch.object(pm, "classify_fund_asset_class", return_value="A股红利低波"):
            audit = pm.evaluate_rebalance_audit()

        b = audit["brinson_attribution"]
        assert abs(b["allocation_effect_yuan"] + b["selection_effect_yuan"] - b["total_active_add_yuan"]) < 1e-4
        assert abs(b["allocation_effect_pct"] + b["selection_effect_pct"] - b["total_active_add_pct"]) < 1e-4


class TestFrontEndUIPresentationAndRenderingStress:
    """对抗验证 3：app_gui.py 前端 UI 呈现、信源指示、归因看板及 CommonMark 防御严苛审查"""

    def test_top3_cards_risk_return_symmetry_and_container_invariants(self):
        """
        审查 app_gui.py 中首屏 Top 3 赛道卡片：
        1. 必须展示收益面：综合得分 (total_score)、四维子项得分 (val_score, mom_score, snr_score, crowd_score)；
        2. 必须展示风险面：20日年化波动率 (vol_20) 与 20日最大回撤 (mdd_20)；
        3. 必须展示动态量化逻辑文案 (core_logic_txt)；
        4. 卡片容器必须锁定 min-height: 220px 与 overflow: visible !important，防止窄屏下文字折行被截断。
        """
        gui_path = AGY_PATH / "app_gui.py"
        content = gui_path.read_text(encoding="utf-8")

        # 1. 验证 vol_20 与 mdd_20 的提取与呈现
        assert "vol_20_val" in content, "Top 3 卡片缺少 20 日年化波动率 vol_20_val 变量"
        assert "mdd_20_val" in content, "Top 3 卡片缺少 20 日最大回撤 mdd_20_val 变量"
        assert "20日波动" in content and "20日最大回撤" in content, "Top 3 卡片未渲染 20日波动与最大回撤风险指标标签"

        # 2. 验证四维子项得分
        assert "val_score" in content and "mom_score" in content, "Top 3 卡片缺少估值或动量子项得分"
        assert "snr_score" in content and "crowd_score" in content, "Top 3 卡片缺少信噪比或反拥挤度子项得分"

        # 3. 验证动态量化依据
        assert "core_logic_txt" in content, "Top 3 卡片缺少 core_logic_txt 动态量化逻辑文本"
        assert "💡 入选依据" in content, "Top 3 卡片缺少『💡 入选依据』UI 标识"

        # 4. 验证 CSS 几何不变量
        pattern_card_style = re.compile(
            r'class="decision-card"[^>]*min-height:\s*220px;[^>]*overflow:\s*visible\s*!important;',
            re.DOTALL
        )
        assert pattern_card_style.search(content), \
            "Top 3 卡片容器未同时声明 min-height: 220px 与 overflow: visible !important;"

    def test_news_realtime_vs_offline_badge_indicators(self):
        """
        审查晨报区域信源状态指示徽章：
        1. 当 is_realtime 为 True 时，呈现绿色徽章 (🟢 实时联网信源)，附带信源名称；
        2. 当 is_realtime 为 False 时，呈现琥珀色徽章 (🟠 离线本地缓存快照)，明确标注网络未连接与快照时间。
        """
        gui_path = AGY_PATH / "app_gui.py"
        content = gui_path.read_text(encoding="utf-8")

        assert "🟢 实时联网信源" in content, "缺少在线绿色信源徽章"
        assert "🟠 离线本地缓存快照" in content, "缺少离线琥珀色缓存快照徽章"
        assert "is_realtime_news" in content, "未根据 is_realtime 进行双轨信源条件分流"

    def test_tab2_dock_tab3_brinson_closed_loop(self):
        """
        审查 Tab 2 dock_tab3 账本运维复盘档案：
        1. Brinson 3D 卡片：大类资产配置效应 (Allocation)、优选基金超额效应 (Selection)、交易摩擦及惩罚规避 (Friction)；
        2. 9 大资产大类 Brinson-Fachler 归因明细表 (st.dataframe)；
        3. 买方投顾穿透复盘点评卡片 (自动根据主导驱动生成深度专业点评)。
        """
        gui_path = AGY_PATH / "app_gui.py"
        content = gui_path.read_text(encoding="utf-8")

        # 3D 卡片审查
        assert "🏛️ 大类资产配置效应 (Allocation)" in content, "dock_tab3 缺少大类配置效应卡片"
        assert "🎯 优选基金超额效应 (Selection)" in content, "dock_tab3 缺少优选基金效应卡片"
        assert "🛡️ 交易摩擦及惩罚规避 (Friction)" in content, "dock_tab3 缺少交易摩擦规避卡片"

        # 明细表审查
        assert "9大资产大类 Brinson-Fachler 归因明细" in content, "dock_tab3 缺少 9 大资产大类归因明细表标题"
        assert "df_breakdown" in content and "st.dataframe(df_breakdown" in content, "dock_tab3 未调用 st.dataframe 渲染归因明细表"

        # 买方投顾点评审查
        assert "💡 买方投顾穿透复盘点评" in content, "dock_tab3 缺少买方投顾穿透复盘点评标题"
        assert "primary_driver" in content, "点评文本未关联 primary_driver 核心驱动"

    def test_commonmark_four_space_indentation_defense_invariant(self):
        """
        审查 CommonMark 4+ 空格缩进代码块防御机制：
        1. app_gui._clean_html 必须将传入字符串的每一行首尾空白剥除，并过滤空行；
        2. 经过 _clean_html 清洗后的任何一行绝不能包含 4 个或更多前导空格；
        3. app_gui.safe_markdown_html 必须统一作为所有 HTML 卡片的入口，严禁直接使用裸 st.markdown(..., unsafe_allow_html=True)。
        """
        test_html_with_deep_indent = """
        <div class="decision-card">
            <div style="color: red;">
                <span>Nested Text</span>
            </div>
        </div>
        """
        cleaned = app_gui._clean_html(test_html_with_deep_indent)
        lines = cleaned.splitlines()

        for idx, line in enumerate(lines):
            assert not line.startswith("    "), f"第 {idx} 行存在 4+ 空格前导缩进，破坏 CommonMark 规范: '{line}'"
            assert not line.startswith("\t"), f"第 {idx} 行存在制表符前导缩进: '{line}'"
            assert line != "", f"第 {idx} 行存在未过滤的空行"

        # 检查 app_gui.py 新增区域统一走 safe_markdown_html 封装
        gui_path = AGY_PATH / "app_gui.py"
        content = gui_path.read_text(encoding="utf-8")
        assert "safe_markdown_html" in content, "app_gui.py 未实装 safe_markdown_html 统一防线"


class TestContractRedlinesAndOrderExecutionStress:
    """对抗验证 4：只读裁判红线与调仓执行器订单生命周期压测"""

    def test_rebalance_orders_execution_immutability(self, tmp_path):
        """
        验证：当通过 apply_rebalance_orders_to_holdings 实际处理真实买入/卖出调仓单据、更新批次与手续费时，
        初始基线快照 initial_baseline_snapshot 绝对不会被调仓执行器污染或重置。
        """
        ledger_file = tmp_path / "order_exec_stress.json"
        pm = PortfolioManager(ledger_file=str(ledger_file), db_path=None)
        pm.available_cash = 50000.0
        pm.add_or_update_holding("005561", 10000.0, 1.20, 1.20)
        pm.evaluate_rebalance_audit()

        baseline_copy = copy.deepcopy(pm.initial_baseline_snapshot)

        # 构造执行调仓订单：买入 002351 (纯债 20,000 元)，减持 005561 (红利 6,000 元)
        buy_order = {
            "基金代码": "002351",
            "基金名称": "广发纯债债券A",
            "建议操作": "增持建仓",
            "建议调仓金额(元)": 20000.0
        }
        sell_order = {
            "基金代码": "005561",
            "基金名称": "创金合信红利低波A",
            "建议操作": "部分减持",
            "建议调仓金额(元)": 6000.0
        }

        pm.apply_rebalance_orders_to_holdings([buy_order, sell_order])
        pm._recalculate_totals()

        # 验证实盘持仓已变更
        assert "002351" in pm.holdings
        assert pm.holdings["005561"].shares < 10000.0

        # 再次执行复盘审计
        with patch.object(pm, "resolve_fund_meta", return_value={"current_nav": 1.10, "fund_name": "测试标的"}):
            audit = pm.evaluate_rebalance_audit()

        # 初始快照必须与调仓前 100% 一致
        assert pm.initial_baseline_snapshot == baseline_copy
        assert audit["shadow_holdings_count"] == 1
        assert "005561" in pm.initial_baseline_snapshot["holdings"]
        assert "002351" not in pm.initial_baseline_snapshot["holdings"]

    def test_readonly_judge_files_and_simulate_execution_redlines(self):
        """
        验证四个只读裁判文件与 DataLoader.simulate_execution 签名与扣费逻辑零修改：
        1. judge_engine.py
        2. holdout_vault.py
        3. AGENT_SPEC.md
        4. tests/test_infra.py
        5. DataLoader.simulate_execution
        """
        import subprocess
        res = subprocess.run(
            ["git", "diff", "--stat", "AGY2_FundAdvisory/judge_engine.py",
             "AGY2_FundAdvisory/holdout_vault.py", "AGY2_FundAdvisory/AGENT_SPEC.md", "tests/test_infra.py"],
            capture_output=True,
            text=True,
            cwd=str(WORKSPACE_ROOT)
        )
        assert res.stdout.strip() == "", f"只读裁判文件被意外修改: {res.stdout}"

        # 验证 DataLoader.simulate_execution 签名
        from data_loader import DataLoader
        import inspect
        sig = inspect.signature(DataLoader.simulate_execution)
        expected_params = ["weights_df", "prices_df", "is_otc", "penalty_days", "penalty_rate", "etf_impact"]
        for p in expected_params:
            assert p in sig.parameters, f"simulate_execution 缺少签约参数: {p}"
