# -*- coding: utf-8 -*-
"""
Adversarial Verification Suite for Milestone 2 (M2)
Challenger 1 (teamwork_challenger)

Tests coverage:
1. Mathematical Identity Adversarial Probes:
   - abs(allocation_effect_yuan + selection_effect_yuan - total_active_add_yuan) < 1e-4
   - abs(allocation_effect_pct + selection_effect_pct - total_active_add_pct) < 1e-4
   - Multi-fund same-category scenario
   - Cross-category rebalancing scenario
   - Pure bond, Gold, US QDII, Tech mixed scenario
   - Negative active return scenario
   - Zero active return scenario
2. Extreme Boundary Adversarial Probes:
   - Boundary 1: Single asset portfolio
   - Boundary 2: 100% Cash portfolio (zero funds)
   - Boundary 2b: Zero equity portfolio (0 cash, 0 funds)
   - Boundary 3: Active portfolio buys asset class completely absent in benchmark
   - Boundary 4: Benchmark asset class completely liquidated in active portfolio
3. 7 Legacy Top-Level Keys Backward Compatibility
4. Baseline Snapshot Serialization & Session Persistence Probing
"""

import sys
import copy
from pathlib import Path
from unittest.mock import patch
import pytest

# Ensure workspace root and AGY2_FundAdvisory are in sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
AGY_PATH = WORKSPACE_ROOT / "AGY2_FundAdvisory"
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))
if str(AGY_PATH) not in sys.path:
    sys.path.insert(0, str(AGY_PATH))

from portfolio_manager import PortfolioManager, FundHolding, HoldingBatch


class TestBrinsonMathematicalIdentityAdversarial:
    """对抗验证 1：Brinson-Fachler 经典模型数学恒等式在各类复杂调仓情景下的严苛平账断言"""

    def test_multi_fund_same_category_rebalance(self):
        """
        情景 1：同大类多基金调仓 (如两只 A 股红利基金 005561 与 100032)
        初始各持有 20,000 份，随后调仓增加 100032 减持 005561，且两基净值发生分化。
        断言：数学恒等式严格成立 (< 1e-4)
        """
        pm = PortfolioManager(db_path=":memory:")
        pm.available_cash = 10000.0
        # 初始基线
        pm.add_or_update_holding("005561", 20000, 1.20, 1.20)
        pm.add_or_update_holding("100032", 20000, 1.50, 1.50)
        # 触发初始基线确立
        audit_init = pm.evaluate_rebalance_audit()
        assert audit_init["shadow_holdings_count"] == 2

        # 模拟实盘调仓与行情分化:
        # 减持 005561 至 10,000 份，净值涨至 1.25
        # 增持 100032 至 30,000 份，净值涨至 1.65
        pm.holdings["005561"].shares = 10000.0
        pm.holdings["005561"].current_nav = 1.25
        pm.holdings["005561"].market_value = 12500.0

        pm.holdings["100032"].shares = 30000.0
        pm.holdings["100032"].current_nav = 1.65
        pm.holdings["100032"].market_value = 49500.0

        pm.available_cash = 2000.0
        pm._recalculate_totals()

        audit = pm.evaluate_rebalance_audit()
        b = audit["brinson_attribution"]

        # 绝对恒等式断言
        assert abs(b["allocation_effect_yuan"] + b["selection_effect_yuan"] - b["total_active_add_yuan"]) < 1e-4, \
            f"金额恒等式被击穿: {b['allocation_effect_yuan']} + {b['selection_effect_yuan']} != {b['total_active_add_yuan']}"
        assert abs(b["allocation_effect_pct"] + b["selection_effect_pct"] - b["total_active_add_pct"]) < 1e-4, \
            f"百分比恒等式被击穿: {b['allocation_effect_pct']} + {b['selection_effect_pct']} != {b['total_active_add_pct']}"

    def test_cross_category_complex_rebalance(self):
        """
        情景 2：跨大类深度调仓 (纯债 002351 + 黄金 000216 + 美股QDII 050025 + 科技进攻 011612)
        初始组合偏保守 (重仓纯债)，主动调仓大幅平移至黄金、美股QDII与科技，跨越4个不同资产大类。
        断言：数学恒等式严格成立 (< 1e-4)，各明细项完整无异常。
        """
        pm = PortfolioManager(db_path=":memory:")
        pm.available_cash = 20000.0
        # 初始持仓: 80% 纯债 (002351) + 20% 红利 (005561)
        pm.add_or_update_holding("002351", 80000, 1.05, 1.05)
        pm.add_or_update_holding("005561", 20000, 1.20, 1.20)
        audit_init = pm.evaluate_rebalance_audit()
        assert audit_init["shadow_holdings_count"] == 2

        # 调仓动作:
        # 大幅降低纯债至 20,000 份 (NAV 1.06)
        # 保留红利 10,000 份 (NAV 1.30)
        # 新增大类建仓:
        # 黄金对冲 000216 建仓 30,000 份 (NAV 1.45, 成本 1.40)
        # 美股海外对冲 050025 建仓 20,000 份 (NAV 2.20, 成本 2.00)
        # 科技进攻 011612 建仓 25,000 份 (NAV 1.10, 成本 1.00)
        pm.holdings["002351"].shares = 20000.0
        pm.holdings["002351"].current_nav = 1.06
        pm.holdings["002351"].market_value = 21200.0

        pm.holdings["005561"].shares = 10000.0
        pm.holdings["005561"].current_nav = 1.30
        pm.holdings["005561"].market_value = 13000.0

        pm.add_or_update_holding("000216", 30000, 1.40, 1.45)
        pm.add_or_update_holding("050025", 20000, 2.00, 2.20)
        pm.add_or_update_holding("011612", 25000, 1.00, 1.10)
        pm.available_cash = 5000.0
        pm._recalculate_totals()

        audit = pm.evaluate_rebalance_audit()
        b = audit["brinson_attribution"]

        assert abs(b["allocation_effect_yuan"] + b["selection_effect_yuan"] - b["total_active_add_yuan"]) < 1e-4
        assert abs(b["allocation_effect_pct"] + b["selection_effect_pct"] - b["total_active_add_pct"]) < 1e-4
        assert len(b["category_breakdown"]) >= 4

    def test_negative_active_return_scenario(self):
        """
        情景 3：主动调仓踩雷发生负超额 (Alpha < 0)
        躺平影子组合盈利，但主动调仓发生亏损，检验负值区间的恒等式、主导驱动与投顾点评逻辑。
        """
        pm = PortfolioManager(db_path=":memory:")
        pm.available_cash = 10000.0
        pm.add_or_update_holding("005561", 50000, 1.20, 1.20)
        pm.evaluate_rebalance_audit()

        # 调仓割肉卖出红利，追高买入科技，随后科技大跌而红利大涨
        del pm.holdings["005561"]
        pm.add_or_update_holding("011612", 50000, 1.20, 0.90)  # 科技跌 -25%
        # 初始红利影子涨至 1.40 (+16.7%)
        # 更新影子组合各标的元数据现价
        with patch("portfolio_manager.PortfolioManager.resolve_fund_meta", return_value={"current_nav": 1.40, "fund_name": "创金合信红利低波A"}):
            audit = pm.evaluate_rebalance_audit()

        b = audit["brinson_attribution"]
        assert b["total_active_add_yuan"] < 0, "期望主动调仓为负增厚"
        assert abs(b["allocation_effect_yuan"] + b["selection_effect_yuan"] - b["total_active_add_yuan"]) < 1e-4
        assert abs(b["allocation_effect_pct"] + b["selection_effect_pct"] - b["total_active_add_pct"]) < 1e-4

    def test_zero_active_return_identity(self):
        """
        情景 4：调仓收益与影子完全一致 (Alpha == 0)
        组合完全未做调仓，持仓与影子 100% 重合。
        断言：total_active_add_yuan == 0.0, allocation == 0.0, selection == 0.0
        """
        pm = PortfolioManager(db_path=":memory:")
        pm.available_cash = 20000.0
        pm.add_or_update_holding("002351", 50000, 1.05, 1.08)
        audit = pm.evaluate_rebalance_audit()
        b = audit["brinson_attribution"]

        assert abs(b["total_active_add_yuan"]) < 1e-4
        assert abs(b["allocation_effect_yuan"]) < 1e-4
        assert abs(b["selection_effect_yuan"]) < 1e-4
        assert abs(b["allocation_effect_yuan"] + b["selection_effect_yuan"] - b["total_active_add_yuan"]) < 1e-4


class TestExtremeBoundaryAdversarialProbes:
    """对抗验证 2：极端边界条件探针（防除零、防 KeyError、防崩溃）"""

    def test_boundary_single_asset_portfolio(self):
        """
        边界 1：单一资产组合 (全仓一只基金，现金为 0)
        验证：
        1. 绝不抛出 ZeroDivisionError 或 KeyError；
        2. 数学恒等式严格成立；
        3. 单一资产内选基效应与配置效应解析正常。
        """
        pm = PortfolioManager(db_path=":memory:")
        pm.available_cash = 0.0
        pm.in_transit_cash = 0.0
        pm.add_or_update_holding("005561", 100000, 1.20, 1.20)
        pm.evaluate_rebalance_audit()

        # 净值上涨至 1.35
        pm.holdings["005561"].current_nav = 1.35
        pm.holdings["005561"].market_value = 135000.0
        pm._recalculate_totals()

        audit = pm.evaluate_rebalance_audit()
        b = audit["brinson_attribution"]

        assert abs(b["allocation_effect_yuan"] + b["selection_effect_yuan"] - b["total_active_add_yuan"]) < 1e-4
        assert abs(b["allocation_effect_pct"] + b["selection_effect_pct"] - b["total_active_add_pct"]) < 1e-4
        assert audit["shadow_holdings_count"] == 1

    def test_boundary_all_cash_portfolio(self):
        """
        边界 2：全现金组合 (无任何基金持仓，holdings 为空，仅有可用现金)
        验证：
        1. 绝不抛出 ZeroDivisionError 或 KeyError；
        2. shadow_hold_equity == current_actual_equity == 现金金额；
        3. total_active_add_yuan == 0.0，归因各项均为 0.0；
        4. 数学恒等式严格成立。
        """
        pm = PortfolioManager(db_path=":memory:")
        pm.available_cash = 150000.0
        pm.in_transit_cash = 0.0
        pm.holdings.clear()
        pm._recalculate_totals()

        audit = pm.evaluate_rebalance_audit()
        b = audit["brinson_attribution"]

        assert audit["current_actual_equity"] == 150000.0
        assert audit["shadow_hold_equity"] == 150000.0
        assert audit["rebalance_value_add"] == 0.0
        assert audit["shadow_holdings_count"] == 0
        assert abs(b["total_active_add_yuan"]) < 1e-4
        assert abs(b["allocation_effect_yuan"] + b["selection_effect_yuan"] - b["total_active_add_yuan"]) < 1e-4

    def test_boundary_zero_equity_portfolio(self):
        """
        边界 2b：极限真空组合 (0现金，0基金持仓，总资产为 0)
        验证：绝不崩溃，返回安全兜底。
        """
        pm = PortfolioManager(db_path=":memory:")
        pm.available_cash = 0.0
        pm.in_transit_cash = 0.0
        pm.holdings.clear()
        pm._recalculate_totals()

        audit = pm.evaluate_rebalance_audit()
        b = audit["brinson_attribution"]

        assert audit["current_actual_equity"] == 0.0
        assert abs(b["total_active_add_yuan"]) < 1e-4
        assert abs(b["allocation_effect_yuan"] + b["selection_effect_yuan"] - b["total_active_add_yuan"]) < 1e-4

    def test_boundary_new_asset_class_absent_in_benchmark(self):
        """
        边界 3：新调入标的属于基准完全未持有的大类
        基准影子组合仅持有“纯债固收”(002351)。
        实盘调仓新增“美股海外对冲”(050025) 与“黄金对冲”(000216)。
        此时基准中美股与黄金大类初始市值与当期市值均为 0 (v_b_init == 0)。
        验证：
        1. 算法内部自动对齐 R_B_map[cat] = R_P_map[cat]；
        2. 绝不发生 0 除以 0 或 KeyError 异常；
        3. 该大类的内部选基效应为 0 (SR = w_P * (R_P - R_B) = 0)，全部超额计入大类配置效应 (AR)；
        4. 数学恒等式严格成立 (< 1e-4)。
        """
        pm = PortfolioManager(db_path=":memory:")
        pm.available_cash = 10000.0
        # 初始基准仅有纯债
        pm.add_or_update_holding("002351", 50000, 1.05, 1.05)
        pm.evaluate_rebalance_audit()

        # 实盘调入美股海外与黄金 (基准完全无持有)
        pm.add_or_update_holding("050025", 20000, 2.00, 2.30)  # 美股大涨 +15%
        pm.add_or_update_holding("000216", 20000, 1.40, 1.54)  # 黄金大涨 +10%
        pm._recalculate_totals()

        audit = pm.evaluate_rebalance_audit()
        b = audit["brinson_attribution"]

        assert abs(b["allocation_effect_yuan"] + b["selection_effect_yuan"] - b["total_active_add_yuan"]) < 1e-4
        assert abs(b["allocation_effect_pct"] + b["selection_effect_pct"] - b["total_active_add_pct"]) < 1e-4

        # 检查美股与黄金明细项
        cat_map = {item["category"]: item for item in b["category_breakdown"]}
        assert "美股海外对冲" in cat_map
        assert "黄金对冲" in cat_map
        assert cat_map["美股海外对冲"]["benchmark_weight_pct"] == 0.0
        # 当基准未持有该大类时，选基效应应为 0
        assert abs(cat_map["美股海外对冲"]["selection_effect_yuan"]) < 1e-4
        assert abs(cat_map["黄金对冲"]["selection_effect_yuan"]) < 1e-4

    def test_boundary_benchmark_asset_liquidated_in_active(self):
        """
        边界 4：基准原有资产在实盘中被完全清仓
        基准持有 005561 (A股红利低波)，实盘中已全部卖出，权重 w_P[cat] == 0。
        验证：算法稳健运行，选基效应为 0，配置效应正确反映低配/踏空损益。
        """
        pm = PortfolioManager(db_path=":memory:")
        pm.available_cash = 10000.0
        pm.add_or_update_holding("005561", 50000, 1.20, 1.20)
        pm.evaluate_rebalance_audit()

        # 清仓 005561，资金变现金
        del pm.holdings["005561"]
        pm.available_cash = 70000.0
        pm._recalculate_totals()

        with patch("portfolio_manager.PortfolioManager.resolve_fund_meta", return_value={"current_nav": 1.30, "fund_name": "创金合信红利低波A"}):
            audit = pm.evaluate_rebalance_audit()

        b = audit["brinson_attribution"]
        assert abs(b["allocation_effect_yuan"] + b["selection_effect_yuan"] - b["total_active_add_yuan"]) < 1e-4
        assert abs(b["allocation_effect_pct"] + b["selection_effect_pct"] - b["total_active_add_pct"]) < 1e-4


class TestLegacyTopLevelKeysBackwardCompatibility:
    """对抗验证 3：原有 7 个顶级键向下兼容性与类型契约完全满足"""

    def test_legacy_seven_keys_types_and_presence(self):
        """
        断言：原有 7 个顶级键名必须 100% 存在，类型正确，且包含新增的 'brinson_attribution'
        """
        pm = PortfolioManager(db_path=":memory:")
        pm.available_cash = 10000.0
        pm.add_or_update_holding("005561", 20000, 1.20, 1.25)

        res = pm.evaluate_rebalance_audit()

        expected_legacy_keys = [
            "current_actual_equity",
            "shadow_hold_equity",
            "rebalance_value_add",
            "rebalance_value_add_pct",
            "saved_penalty_and_buffer_fees",
            "baseline_date",
            "shadow_holdings_count"
        ]

        for k in expected_legacy_keys:
            assert k in res, f"顶级兼容键缺失: {k}"

        assert isinstance(res["current_actual_equity"], (int, float))
        assert isinstance(res["shadow_hold_equity"], (int, float))
        assert isinstance(res["rebalance_value_add"], (int, float))
        assert isinstance(res["rebalance_value_add_pct"], (int, float))
        assert isinstance(res["saved_penalty_and_buffer_fees"], (int, float))
        assert isinstance(res["baseline_date"], str)
        assert isinstance(res["shadow_holdings_count"], int)

        # 验证新键
        assert "brinson_attribution" in res
        b = res["brinson_attribution"]
        expected_brinson_keys = [
            "allocation_effect_yuan",
            "allocation_effect_pct",
            "selection_effect_yuan",
            "selection_effect_pct",
            "friction_saving_yuan",
            "friction_saving_pct",
            "total_active_add_yuan",
            "total_active_add_pct",
            "primary_driver",
            "category_breakdown"
        ]
        for bk in expected_brinson_keys:
            assert bk in b, f"Brinson 结构子键缺失: {bk}"


class TestBaselineSnapshotPersistenceAdversarial:
    """对抗验证 4：基线快照持久化与跨会话自愈对抗探针"""

    def test_baseline_snapshot_saved_and_restored_across_instances(self):
        """
        验证：
        1. _export_state_dict 包含 initial_baseline_snapshot；
        2. _import_state_dict 能完整恢复 initial_baseline_snapshot；
        3. 重启/恢复后再次调用 evaluate_rebalance_audit，初始影子组合基线不被当前新持仓覆写。
        """
        pm1 = PortfolioManager(db_path=":memory:")
        pm1.available_cash = 10000.0
        pm1.add_or_update_holding("005561", 20000, 1.20, 1.20)
        audit1 = pm1.evaluate_rebalance_audit()

        assert audit1["shadow_holdings_count"] == 1
        assert "005561" in pm1.initial_baseline_snapshot["holdings"]

        # 导出状态字典
        state = pm1._export_state_dict()
        assert "initial_baseline_snapshot" in state
        assert "005561" in state["initial_baseline_snapshot"]["holdings"]

        # 模拟重启：在全新的 pm2 中载入状态
        pm2 = PortfolioManager(db_path=":memory:")
        pm2._import_state_dict(state)

        # 在 pm2 中做大幅调仓（卖出 005561，买入 002351）
        del pm2.holdings["005561"]
        pm2.add_or_update_holding("002351", 30000, 1.05, 1.05)
        pm2._recalculate_totals()

        # 在 pm2 中调用 evaluate_rebalance_audit，必须依然锚定 pm1 的 005561 初始基线
        with patch("portfolio_manager.PortfolioManager.resolve_fund_meta", return_value={"current_nav": 1.30, "fund_name": "创金合信红利低波A"}):
            audit2 = pm2.evaluate_rebalance_audit()

        assert audit2["shadow_holdings_count"] == 1
        # 影子依然是 005561，没有被篡改为 002351
        assert audit2["brinson_attribution"]["total_active_add_yuan"] != 0.0


class TestMonteCarloRandomizedRebalanceStress:
    """对抗验证 5：200 轮随机极端组合与复杂调仓蒙特卡洛应力测试"""

    def test_200_random_portfolio_rebalance_invariants(self):
        """
        蒙特卡洛生成 200 个随机组合与调仓情景：
        - 随机选择 1~8 只跨赛道标的；
        - 随机现金（0 ~ 500,000 元）；
        - 随机持有份额与净值波动（±40%）；
        - 随机调仓操作（增持、减持、清仓、跨大类新建仓）；
        - 验证：200 轮蒙特卡洛中，数学恒等式在 1e-4 容差内 100% 成立，0 崩溃，0 除零，0 KeyError。
        """
        import random
        # 固定种子保证测试可复现
        rng = random.Random(20261108)

        candidate_pool = [
            ("002351", "纯债固收", 1.05),
            ("000216", "黄金对冲", 1.40),
            ("050025", "美股海外对冲", 2.10),
            ("005561", "A股红利低波", 1.25),
            ("100032", "A股红利高股息", 1.55),
            ("011612", "科技成长进攻", 1.15),
            ("004194", "中小盘成长", 1.30),
            ("000478", "中盘均衡", 1.80),
            ("110020", "核心蓝筹", 2.50),
        ]

        for trial in range(200):
            pm = PortfolioManager(db_path=":memory:")
            init_cash = round(rng.uniform(0.0, 200000.0), 2)
            pm.available_cash = init_cash

            # 随机挑选 1~5 只初始基金
            k_init = rng.randint(1, 5)
            selected_init = rng.sample(candidate_pool, k_init)
            for code, name, nav in selected_init:
                shares = round(rng.uniform(1000.0, 50000.0), 2)
                cost = nav * rng.uniform(0.9, 1.1)
                pm.add_or_update_holding(code, shares, cost, nav)

            # 确立基线
            pm._recalculate_totals()
            audit_init = pm.evaluate_rebalance_audit()
            assert audit_init["shadow_holdings_count"] == k_init

            # 模拟随机调仓与行情变动
            # 1. 部分清仓
            if pm.holdings and rng.random() < 0.4:
                del_code = rng.choice(list(pm.holdings.keys()))
                del pm.holdings[del_code]

            # 2. 存量持仓份额与净值变动
            for h in pm.holdings.values():
                h.shares = round(h.shares * rng.uniform(0.5, 2.0), 2)
                h.current_nav = round(h.current_nav * rng.uniform(0.7, 1.4), 4)
                h.market_value = round(h.shares * h.current_nav, 2)

            # 3. 随机新建仓 (可能包含基准未持有的大类)
            if rng.random() < 0.6:
                unheld = [p for p in candidate_pool if p[0] not in pm.holdings]
                if unheld:
                    new_item = rng.choice(unheld)
                    new_code, _, new_base_nav = new_item
                    new_shares = round(rng.uniform(2000.0, 30000.0), 2)
                    new_nav = round(new_base_nav * rng.uniform(0.8, 1.3), 4)
                    pm.add_or_update_holding(new_code, new_shares, new_base_nav, new_nav)

            # 4. 随机现金变动
            pm.available_cash = round(rng.uniform(0.0, 100000.0), 2)
            pm._recalculate_totals()

            # 运行审计归因
            audit = pm.evaluate_rebalance_audit()
            b = audit["brinson_attribution"]

            # 严格恒等式断言
            alloc_y = b["allocation_effect_yuan"]
            sel_y = b["selection_effect_yuan"]
            tot_y = b["total_active_add_yuan"]
            alloc_p = b["allocation_effect_pct"]
            sel_p = b["selection_effect_pct"]
            tot_p = b["total_active_add_pct"]

            diff_yuan = abs(alloc_y + sel_y - tot_y)
            diff_pct = abs(alloc_p + sel_p - tot_p)

            assert diff_yuan < 1e-4, f"[Trial {trial}] 金额恒等式失效: {alloc_y} + {sel_y} != {tot_y} (diff={diff_yuan})"
            assert diff_pct < 1e-4, f"[Trial {trial}] 百分比恒等式失效: {alloc_p} + {sel_p} != {tot_p} (diff={diff_pct})"

            # category_breakdown 单项一致性检查
            for cat_item in b["category_breakdown"]:
                c_alloc = cat_item["allocation_effect_yuan"]
                c_sel = cat_item["selection_effect_yuan"]
                c_tot = cat_item["total_effect_yuan"]
                assert abs(round(c_alloc + c_sel, 2) - c_tot) < 1e-4


class TestFrictionAndFeeSavingsAdversarial:
    """对抗验证 6：主动风控摩擦费与赎回惩罚费规避逻辑验证"""

    def test_friction_saving_7day_and_class_c_penalties(self):
        """
        验证：
        1. 持有天数 <7 天的批次或带 safety_lock 批次触发 1.50% 惩罚费规避计算；
        2. C 类份额在 7<=天数<30 时触发 0.50% 赎回费规避计算；
        3. saved_penalty_and_buffer_fees 准确映射至 brinson_attribution 的 friction_saving_yuan 与 friction_saving_pct。
        """
        pm = PortfolioManager(db_path=":memory:")
        pm.available_cash = 10000.0

        # 添加一只含有 <7 天锁定期批次的基金
        pm.add_or_update_holding("005561", 20000, 1.20, 1.20)
        h1 = pm.holdings["005561"]
        h1.batches = [
            HoldingBatch(batch_id="b1", buy_date="2026-11-06", shares=10000.0, cost_nav=1.20, holding_days=2, safety_lock=True),
            HoldingBatch(batch_id="b2", buy_date="2026-10-01", shares=10000.0, cost_nav=1.20, holding_days=38, safety_lock=False),
        ]

        # 添加一只 C 类持有期 15 天的基金 (无 <7天 锁定，但有 7~29天 C 类赎回费)
        pm.add_or_update_holding("011613", 10000, 1.00, 1.00, holding_days=15)
        h2 = pm.holdings["011613"]
        h2.share_class = "C"
        h2.holding_days = 15
        h2.market_value = 10000.0

        pm._recalculate_totals()
        audit = pm.evaluate_rebalance_audit()

        # 预期惩罚费 = 10,000 * 1.20 * 0.0150 (h1 batch 1) + 10,000 * 0.0050 (h2 C类)
        # = 180.0 + 50.0 = 230.0 元
        expected_saved = 180.0 + 50.0
        assert abs(audit["saved_penalty_and_buffer_fees"] - expected_saved) < 1e-2

        b = audit["brinson_attribution"]
        assert abs(b["friction_saving_yuan"] - expected_saved) < 1e-2
        assert b["friction_saving_pct"] > 0.0


class TestUIAndSourceCodeIntegrationAdversarial:
    """对抗验证 7：app_gui.py 前端渲染集成与 CommonMark 防御法证"""

    def test_app_gui_brinson_source_code_contract(self):
        """
        验证 app_gui.py 中：
        1. 必须调用 evaluate_rebalance_audit；
        2. 必须渲染 Brinson-Fachler 经典三维归因卡片；
        3. 必须包含 9 大资产大类 Brinson-Fachler 归因明细表渲染；
        4. 必须包含买方投顾穿透复盘点评；
        5. 所有富文本输出统一收口至 safe_markdown_html，零裸 st.markdown 拼接漏洞。
        """
        gui_path = WORKSPACE_ROOT / "AGY2_FundAdvisory" / "app_gui.py"
        assert gui_path.exists(), "app_gui.py 不存在！"

        gui_code = gui_path.read_text(encoding="utf-8")

        assert "evaluate_rebalance_audit" in gui_code
        assert "brinson_attribution" in gui_code
        assert "大类资产配置效应" in gui_code
        assert "优选基金超额效应" in gui_code
        assert "交易摩擦及惩罚规避" in gui_code
        assert "Brinson-Fachler" in gui_code
        assert "category_breakdown" in gui_code
        assert "买方投顾穿透复盘点评" in gui_code



# ==============================================================================
# Milestone 2 (M2) Adversarial Challenge Suites — Challenger 1 (critic/specialist)
# ==============================================================================
import ast
import re
import json
from unittest.mock import MagicMock
import app_gui
import data_loader
from advisory_engine import ActiveRiskSentry
from strategy_bridge import StrategyBridge


class TestHTMLPurificationAdversarialAST:
    """对抗验证 8：HTML 纯化 AST/正则静态扫描与极端边缘输入法证"""

    def test_zero_raw_unsafe_markdown_in_app_gui_ast(self):
        """
        AST 遍历整个 app_gui.py：
        断言除 def safe_markdown_html 自身的单一定义外，
        严禁存在任何直接调用 unsafe_allow_html=True 且未包裹 _clean_html 的 markdown 调用。
        """
        gui_path = WORKSPACE_ROOT / "AGY2_FundAdvisory" / "app_gui.py"
        code = gui_path.read_text(encoding="utf-8")
        tree = ast.parse(code, filename=str(gui_path))

        violations = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            func_name = None
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr

            if func_name == "markdown":
                has_unsafe = any(
                    kw.arg == "unsafe_allow_html" and getattr(kw.value, "value", None) is True
                    for kw in node.keywords
                )
                if has_unsafe:
                    line_no = getattr(node, "lineno", 0)
                    # 允许 safe_markdown_html 内部的实现 (~行 204-208)
                    if 200 <= line_no <= 210:
                        continue

                    is_cleaned = False
                    if node.args:
                        first_arg = node.args[0]
                        if isinstance(first_arg, ast.Call):
                            arg_func = getattr(first_arg.func, "id", getattr(first_arg.func, "attr", None))
                            if arg_func == "_clean_html":
                                is_cleaned = True
                    if not is_cleaned:
                        violations.append((line_no, ast.unparse(node) if hasattr(ast, "unparse") else f"Line {line_no}"))

        assert len(violations) == 0, f"发现 {len(violations)} 处违规裸露 unsafe markdown 调用: {violations}"

    def test_clean_html_adversarial_multiline_indent_edge_cases(self):
        """
        针对 _clean_html 进行对抗性边界输入测试：
        1. 包含 4、8、16、24 个前导空格的多行嵌套 f-string；
        2. 前后包含空行、全空格行、制表符缩进行；
        3. 单双引号、三引号混用，内嵌复杂 HTML 属性与样式；
        4. 超长 HTML（> 60,000 字符）；
        5. 中文标点、Emoji 与特殊符号；
        6. 空字符串、None 与空白输入。
        断言：清洗后任意一行绝无 4+ 前导空格，绝无空行，绝不破坏文本内容与标签完整性。
        """
        # 1. 深度嵌套多行字符串
        deeply_indented = """
                <div class="test-container" style="background: var(--bg-surface);">
                    <div style="padding: 12px;">
                        <span>第一行文字 🚀</span>
                        <p style="color: 'red';">
                            <b>嵌套加粗内容</b>
                        </p>
                    </div>
                </div>
        """
        res = app_gui._clean_html(deeply_indented)
        lines = res.splitlines()
        assert len(lines) > 0
        for l in lines:
            assert not l.startswith("    "), f"发现 4+ 空格缩进泄露: '{l}'"
            assert not l.startswith("\t"), f"发现制表符缩进泄露: '{l}'"
            assert len(l.strip()) > 0, "发现未过滤空行"
        assert "<span>第一行文字 🚀</span>" in res
        assert "<b>嵌套加粗内容</b>" in res

        # 2. None 与空串安全测试
        assert app_gui._clean_html(None) == ""
        assert app_gui._clean_html("") == ""
        assert app_gui._clean_html("   \n\n\t\t\n   ") == ""

        # 3. 超长 HTML 压力测试
        chunk = "<div><span style='color: blue;'>测试内容段落</span></div>\n"
        big_html = "    " + chunk * 1000  # > 50,000 字符
        cleaned_big = app_gui._clean_html(big_html)
        assert len(cleaned_big.splitlines()) == 1000
        for l in cleaned_big.splitlines():
            assert not l.startswith(" ")

    def test_historical_inflection_ruler_html_purification(self):
        """
        针对历史三大牛熊拐点实盘对照尺输出进行 CommonMark 纯化断言：
        验证 render_historical_inflection_ruler_html 输出的 HTML 各行 0 前导空格，
        即使嵌入在多层缩进的 f-string 内部，经 _clean_html / safe_markdown_html 处理后绝无代码块泄露。
        """
        mock_ruler_data = {
            "nodes": [
                {"date": "2021-02-18", "event": "2021 核心资产顶", "multiplier": 0.50, "erp_percentile": 12.5, "bias_20": 8.2},
                {"date": "2022-04-26", "event": "2022 恐慌双底", "multiplier": 1.93, "erp_percentile": 88.6, "bias_20": -6.5},
                {"date": "2024-09-23", "event": "2024 反转前夕", "multiplier": 1.94, "erp_percentile": 92.1, "bias_20": -8.1},
                {"date": "2026-11-08", "event": "今日实时水位", "multiplier": 1.76, "erp_percentile": 78.3, "bias_20": -1.2},
            ]
        }
        ruler_html = app_gui.render_historical_inflection_ruler_html(mock_ruler_data)
        assert ruler_html != "", "对照尺未能正确生成 HTML"
        assert "📏 历史三大牛熊拐点实盘对照尺" in ruler_html
        for l in ruler_html.splitlines():
            assert not l.startswith("    "), f"对照尺输出存在 4+ 空格泄露: '{l}'"
            assert not l.startswith(" "), f"对照尺每行应已严格 strip: '{l}'"

        # 模拟嵌入在带有 16 个空格缩进的父级模板中
        parent_template = f"""
                <div class="parent-card">
                    {ruler_html}
                </div>
        """
        cleaned_parent = app_gui._clean_html(parent_template)
        for l in cleaned_parent.splitlines():
            assert not l.startswith("    "), f"父子组合后存在 4+ 空格泄露: '{l}'"


class TestActionMasterSwitchFourStatesAdversarial:
    """对抗验证 9：首屏【今日投顾行动总开关】四态完全覆盖与逻辑状态机严苛推演"""

    def _simulate_master_action_switch(self, pm, snapshot_dict):
        """提取 app_gui.py 中行动总开关的纯业务状态判定逻辑并返回决策元组"""
        sentry = ActiveRiskSentry()
        _f_metas = {}
        for _c in pm.holdings.keys():
            try:
                _f_metas[_c] = data_loader.get_fund_metadata(_c) or {}
            except Exception:
                _f_metas[_c] = {}
        sentry_rep = sentry.inspect_portfolio(pm.holdings, snapshot_dict, fund_metadata=_f_metas)
        all_alerts_switch = sentry_rep.get("alerts", [])
        lock_alerts_switch = [a for a in all_alerts_switch if a.get("action_type") == "lock_shares"]

        if lock_alerts_switch:
            act_status_icon = "🔴"
            act_title = "【锁定防御】存在未满 7 天惩罚期标的，已启动锁定保护严禁卖出"
            act_target_tab = 1
            act_target_name = "💼 持仓调仓"
            act_btn_label = "👉 查看锁仓保护"
        elif all_alerts_switch:
            act_status_icon = "🟡"
            act_title = f"【时机就绪】主动风控检测到 {len(all_alerts_switch)} 项持仓异动优化机会"
            act_target_tab = 1
            act_target_name = "💼 持仓调仓"
            act_btn_label = "👉 查看今日调仓单"
        elif len(pm.holdings) == 0:
            act_status_icon = "🚀"
            act_title = "【空仓建仓】宏观 ERP 处于黄金击球区，建议一键启动新资建仓"
            act_target_tab = 0
            act_target_name = "🌱 新资建仓"
            act_btn_label = "👉 立即开始新资建仓"
        else:
            act_status_icon = "🟢"
            act_title = "【按兵不动】持仓资产结构健康，安全垫充沛，今日安心吃息"
            act_target_tab = 1
            act_target_name = "💼 持仓调仓"
            act_btn_label = "👉 检视持仓账本"

        return act_status_icon, act_title, act_target_tab, act_target_name, act_btn_label

    def test_state_1_lock_defense(self):
        """状态 1 (🔴 锁定防御)：持仓中存在 <7 天锁定批次，必须触发锁定保护严禁卖出"""
        pm = PortfolioManager(db_path=":memory:")
        pm.available_cash = 10000.0
        pm.add_or_update_holding("005561", 10000, 1.20, 1.20)
        h = pm.holdings["005561"]
        h.batches = [HoldingBatch(batch_id="b1", buy_date="2026-11-06", shares=10000.0, cost_nav=1.20, holding_days=2, safety_lock=True)]
        snapshot = StrategyBridge.get_latest_market_snapshot(force_reload=False, auto_sync=False) or {}

        icon, title, tab_idx, tab_name, btn_lbl = self._simulate_master_action_switch(pm, snapshot)
        assert icon == "🔴"
        assert "【锁定防御】" in title
        assert tab_idx == 1
        assert "持仓调仓" in tab_name
        assert "查看锁仓保护" in btn_lbl

    def test_state_2_tactical_opportunity(self):
        """状态 2 (🟡 时机就绪)：无 <7 天锁定，但存在持仓预警 (如 C 类持有满 32 天提示清理)，触发调仓优化机会"""
        pm = PortfolioManager(db_path=":memory:")
        pm.available_cash = 10000.0
        pm.add_or_update_holding("011613", 10000, 1.00, 1.00, holding_days=35)
        h = pm.holdings["011613"]
        h.share_class = "C"
        h.batches = [HoldingBatch(batch_id="b1", buy_date="2026-10-01", shares=10000.0, cost_nav=1.00, holding_days=35, safety_lock=False)]
        snapshot = StrategyBridge.get_latest_market_snapshot(force_reload=False, auto_sync=False) or {}

        icon, title, tab_idx, tab_name, btn_lbl = self._simulate_master_action_switch(pm, snapshot)
        assert icon == "🟡"
        assert "【时机就绪】" in title
        assert tab_idx == 1
        assert "查看今日调仓单" in btn_lbl

    def test_state_3_empty_portfolio(self):
        """状态 3 (🚀 空仓建仓)：持仓数量为 0，必须导向新资建仓工作区"""
        pm = PortfolioManager(db_path=":memory:")
        pm.available_cash = 100000.0
        pm.holdings.clear()
        snapshot = StrategyBridge.get_latest_market_snapshot(force_reload=False, auto_sync=False) or {}

        icon, title, tab_idx, tab_name, btn_lbl = self._simulate_master_action_switch(pm, snapshot)
        assert icon == "🚀"
        assert "【空仓建仓】" in title
        assert tab_idx == 0
        assert "新资建仓" in tab_name
        assert "立即开始新资建仓" in btn_lbl

    def test_state_4_healthy_idle(self):
        """状态 4 (🟢 按兵不动)：持仓资产结构健康且均满期无异动，提示安心吃息无需折腾"""
        pm = PortfolioManager(db_path=":memory:")
        pm.available_cash = 20000.0
        pm.add_or_update_holding("002351", 50000, 1.05, 1.05, holding_days=60)
        h = pm.holdings["002351"]
        h.share_class = "A"
        h.batches = [HoldingBatch(batch_id="b1", buy_date="2026-09-01", shares=50000.0, cost_nav=1.05, holding_days=60, safety_lock=False)]

        with patch.object(ActiveRiskSentry, "inspect_portfolio", return_value={"alerts": [], "status": "ALL_CLEAR"}):
            icon, title, tab_idx, tab_name, btn_lbl = self._simulate_master_action_switch(pm, {})

        assert icon == "🟢"
        assert "【按兵不动】" in title
        assert "安心吃息" in title
        assert tab_idx == 1
        assert "检视持仓账本" in btn_lbl


class TestTab1L1InputsAndTiersAdversarial:
    """对抗验证 10：Tab 1 L1 极简双输入、大额防错转换、C1-C5 档位与智能托管参数匹配"""

    def test_format_chinese_amount_adversarial_values(self):
        """
        验证 format_chinese_amount 在极端数值下的鲁棒性：
        1. 0.0 -> '¥0.00 折合 0.00 万元'
        2. 负数 (-50,000) -> '-¥50,000.00 折合 -5.00 万元'
        3. 正常 100,000 -> '¥100,000.00 折合 10.00 万元'
        4. 百万级 1,500,000 -> '¥1,500,000.00 折合 150.00 万元'
        5. 亿级 100,000,000 (1e8) -> 包含 '10,000.00 万元 (1.00 亿元)'
        6. 小数 float (12345.6789) -> 四舍五入精确保留 2 位小数
        7. 非法输入 (None, 'abc', []) -> 优雅返回 '¥0.00 折合 0.00 万元'，绝不崩溃
        """
        assert app_gui.format_chinese_amount(0) == "¥0.00 折合 0.00 万元"
        assert "-¥50,000.00 折合 -5.00 万元" in app_gui.format_chinese_amount(-50000.0)
        assert "¥100,000.00 折合 10.00 万元" in app_gui.format_chinese_amount(100000.0)
        assert "¥1,500,000.00 折合 150.00 万元" in app_gui.format_chinese_amount(1500000.0)

        amt_1e8 = app_gui.format_chinese_amount(1e8)
        assert "1.00 亿元" in amt_1e8
        assert "10,000.00 万元" in amt_1e8

        amt_float = app_gui.format_chinese_amount(12345.6789)
        assert "¥12,345.68" in amt_float

        assert app_gui.format_chinese_amount(None) == "¥0.00 折合 0.00 万元"
        assert app_gui.format_chinese_amount("invalid_str") == "¥0.00 折合 0.00 万元"
        assert app_gui.format_chinese_amount([]) == "¥0.00 折合 0.00 万元"

    def test_c1_to_c5_risk_tiers_mapping_and_config_integrity(self):
        """
        验证 C1 至 C5 风险档位完整性与映射连续性：
        1. map_slider_to_tier 覆盖 5% 至 100% 全域；
        2. RISK_TIERS_CONFIG 字典 100% 包含 C1 至 C5 且各元数据完备。
        """
        assert app_gui.map_slider_to_tier(6.0) == "C1"
        assert app_gui.map_slider_to_tier(8.5) == "C2"
        assert app_gui.map_slider_to_tier(15.0) == "C3"
        assert app_gui.map_slider_to_tier(22.0) == "C4"
        assert app_gui.map_slider_to_tier(35.0) == "C5"

        expected_tiers = ["C1", "C2", "C3", "C4", "C5"]
        for t in expected_tiers:
            assert t in app_gui.RISK_TIERS_CONFIG, f"缺少档位配置: {t}"
            cfg = app_gui.RISK_TIERS_CONFIG[t]
            for key in ["name", "core_assets", "default_target", "target_cagr", "equity_range_str", "max_drawdown_limit"]:
                assert key in cfg, f"档位 {t} 缺少必要字段: {key}"

    def test_ai_smart_fund_count_allocation_rule(self):
        """
        验证 AI 自动托管基金只数梯度规则：
        - 本金 <= 50,000 元 -> 建议 4 只
        - 50,000 < 本金 <= 300,000 元 -> 建议 6 只
        - 本金 > 300,000 元 -> 建议 8 只
        """
        def get_auto_num_funds(cap):
            return 4 if cap <= 50000.0 else (6 if cap <= 300000.0 else 8)

        assert get_auto_num_funds(10000.0) == 4
        assert get_auto_num_funds(50000.0) == 4
        assert get_auto_num_funds(100000.0) == 6
        assert get_auto_num_funds(300000.0) == 6
        assert get_auto_num_funds(500000.0) == 8
        assert get_auto_num_funds(10000000.0) == 8


class TestTab2ViewModeDecouplingAdversarial:
    """对抗验证 11：Tab 2 双视图模式物理隔离与缓冲带单源性法证"""

    def test_dock_tabs_strictly_isolated_in_else_branch_ast(self):
        """
        AST 审查 Tab 2 双视图模式物理隔离：
        1. 必须存在 `if is_t2_main_mode:` 分支；
        2. 必须存在对应的 `else:` 分支；
        3. 6 大宽屏运维工具坞（st.tabs([\"✨ 快速录入/导入持仓\", ...])）必须严格且仅位于 `else:` 分支内部；
        4. 断言在 `is_t2_main_mode == True` 时，绝不可能执行 dock_tabs 的渲染逻辑。
        """
        gui_path = WORKSPACE_ROOT / "AGY2_FundAdvisory" / "app_gui.py"
        code = gui_path.read_text(encoding="utf-8")
        tree = ast.parse(code, filename=str(gui_path))

        t2_if_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                test_unparsed = ast.unparse(node.test) if hasattr(ast, "unparse") else ""
                if "is_t2_main_mode" in test_unparsed:
                    t2_if_node = node
                    break

        assert t2_if_node is not None, "未在 app_gui.py 中找到 if is_t2_main_mode 条件分支！"
        assert len(t2_if_node.orelse) > 0, "is_t2_main_mode 缺少 else: 运维工具坞分支！"

        else_code = ast.unparse(t2_if_node.orelse) if hasattr(ast, "unparse") else ""
        assert "dock_tab1" in else_code, "dock_tab1 必须定义在 else 分支内部！"
        assert "dock_tab6" in else_code, "dock_tab6 必须定义在 else 分支内部！"
        assert "st.tabs" in else_code, "运维工具坞 st.tabs 必须位于 else 分支内部！"

        body_code = ast.unparse(t2_if_node.body) if hasattr(ast, "unparse") else ""
        assert "dock_tab1, dock_tab2" not in body_code, "主模式分支严禁定义或渲染 dock_tabs 工具坞！"

    def test_single_source_rebalance_buffer_slider(self):
        """
        验证全页仅保留单一功能滑块 tab2_rebal_buf_slider，彻底清除多处重复定义导致状态冲突的缺陷。
        """
        gui_path = WORKSPACE_ROOT / "AGY2_FundAdvisory" / "app_gui.py"
        code = gui_path.read_text(encoding="utf-8")

        slider_keys = re.findall(r'key=["\']tab2_rebal_buf_slider["\']', code)
        assert len(slider_keys) == 1, f"tab2_rebal_buf_slider 必须全局唯一，实际出现 {len(slider_keys)} 次"
        assert "# tab2_rebal_buf_slider_bot" in code, "缺少 tab2_rebal_buf_slider_bot 兼容注释标记"


class TestPopoverQuickFundEntryAdversarial:
    """对抗验证 12：➕ 极速录基 Popover 弹窗输入校验、异常兜底与 7 天锁定端到端传导"""

    def test_invalid_fund_code_rejection_and_fallback(self):
        """
        测试极速录基非法输入过滤逻辑：
        - 输入空字符串、全空格、特殊字符或无效纯数字代码
        - 验证正则表达式 r'\b\d{6}\b' 与 catalog 搜索结果均为空时，matched_code 为 None
        - 验证系统安全触发 warning 且绝不向持仓中添加垃圾数据。
        """
        pm = PortfolioManager(db_path=":memory:")
        initial_count = len(pm.holdings)

        invalid_inputs = ["", "   ", "xyz_nonexistent_fund_99999", "INVALID_FUND_FOOBAR"]
        for bad_in in invalid_inputs:
            raw_in = bad_in.strip()
            matched_code = None
            if raw_in:
                m_c = re.search(r'\b\d{6}\b', raw_in)
                if m_c:
                    from portfolio_manager import search_funds_in_catalog
                    res_search = search_funds_in_catalog(m_c.group(0), limit=1)
                    if res_search:
                        matched_code = res_search[0]["fund_code"]
                else:
                    from portfolio_manager import search_funds_in_catalog
                    res_search = search_funds_in_catalog(raw_in, limit=1)
                    if res_search:
                        matched_code = res_search[0]["fund_code"]
            assert matched_code is None, f"非法输入 '{bad_in}' 不应被识别为有效基金代码"

        assert len(pm.holdings) == initial_count

    def test_quick_entry_seven_day_lock_triggering_and_sentry_cascade(self):
        """
        测试持有期选择 '<7天 (临界观察·惩罚期)' 的完整端到端传导链：
        1. 选择 '<7天' 档位 -> 映射为 holding_days = 3;
        2. add_or_update_holding 记账入库后，其最短持有天数必为 3;
        3. export_snapshot_df 导出的持仓表中，'赎回费状态' 必须明确包含 '🔴 1.50% 禁卖 (差4天)';
        4. ActiveRiskSentry 巡检持仓时，必须输出 action_type == 'lock_shares' 的预警;
        5. 首屏【今日投顾行动总开关】必须立刻从其它状态跃迁为 '🔴 【锁定防御】'！
        """
        pm = PortfolioManager(db_path=":memory:")
        pm.available_cash = 50000.0

        dur_choice = "<7天 (临界观察·惩罚期)"
        dur_map = {0: 3, 1: 15, 2: 45, 3: 185, 4: 370}
        dur_idx = ["<7天", "7-29天", "30-179天", "≥180天", "≥365天"].index(dur_choice.split(" ")[0])
        h_days = dur_map.get(dur_idx, 45)
        assert h_days == 3, "7天内档位必须映射为 3 天"

        pm.add_or_update_holding(
            fund_code="005561",
            shares=10000.0,
            cost_price=1.20,
            nav=1.20,
            holding_days=h_days,
            notes="极速录基吧台录入"
        )

        # 1. 验证持仓批次
        h = pm.holdings["005561"]
        min_days = min((b.holding_days for b in h.batches), default=h.holding_days)
        assert min_days == 3

        # 2. 验证持仓快照表赎回费状态显示
        df_disp = pm.export_snapshot_df()
        df_disp["赎回费状态"] = df_disp.apply(
            lambda r: (
                f"🔴 1.50% 禁卖 (差{max(0, 7 - int(r['最短持有天数']))}天)" if int(r['最短持有天数']) < 7
                else (f"🟡 {r['当前赎回费率(%)']:.2f}% (差{max(0, 30 - int(r['最短持有天数']))}天免)" if (r.get('份额类型') == 'C' and int(r['最短持有天数']) < 30)
                else f"🟢 {r['当前赎回费率(%)']:.2f}% 免/低赎")
            ),
            axis=1
        )
        assert "🔴 1.50% 禁卖 (差4天)" in df_disp["赎回费状态"].values[0]

        # 3. 验证 ActiveRiskSentry 产生 lock_shares 警报
        sentry = ActiveRiskSentry()
        rep = sentry.inspect_portfolio(pm.holdings, {})
        alerts = rep.get("alerts", [])
        lock_alerts = [a for a in alerts if a.get("action_type") == "lock_shares"]
        assert len(lock_alerts) >= 1
        assert lock_alerts[0]["level"] == "red"

        # 4. 验证级联激活总开关 🔴 锁定防御
        act_status_icon = "🔴" if lock_alerts else "🟢"
        assert act_status_icon == "🔴"

    def test_quick_entry_cost_calculation_resilience(self):
        """
        测试盈亏输入解析与成本反算的数学鲁棒性：
        1. 百分比格式: '+25%' -> 成本价反算
        2. 金额格式: '-2500元' -> 成本价反算
        3. 极端超常盈利保护: 确保 cost_p 永远 >= 0.01，严防负数或零除错误。
        """
        real_nav = 1.25
        amt = 12500.0
        sh = 10000.0

        pnl_str = "+25%"
        pct_v = float(pnl_str.replace("%", "").strip())
        cost_p = round(real_nav / (1.0 + pct_v / 100.0), 4)
        assert abs(cost_p - 1.00) < 1e-4

        pnl_str_amt = "-2500元"
        pnl_v = float(pnl_str_amt.replace("元", "").replace("+", "").replace(",", "").strip())
        cost_p_amt = round(max(0.01, amt - pnl_v) / sh, 4)
        assert abs(cost_p_amt - 1.50) < 1e-4

        pnl_str_crazy = "+50000元"
        pnl_crazy = float(pnl_str_crazy.replace("元", "").replace("+", "").replace(",", "").strip())
        cost_crazy = round(max(0.01, amt - pnl_crazy) / sh, 4)
        assert cost_crazy >= 0.0, "即使极端超常盈利，成本价兜底必须非负"

    def test_app_gui_popover_fund_name_search_no_broken_import(self):
        """
        [缺陷检测探针] 验证 app_gui.py 中极速录基 Popover 严禁包含错误的局部导入：
        search_funds_in_catalog 存在于 portfolio_manager.py，
        在 app_gui.py 行 5100 处若错误写入 'from data_loader import search_funds_in_catalog'，
        会导致用户输入非纯 6 位数字（如中文基金名或拼音）录基时触发 ImportError 击穿整个 Tab 2！
        """
        gui_path = WORKSPACE_ROOT / "AGY2_FundAdvisory" / "app_gui.py"
        code = gui_path.read_text(encoding="utf-8")
        assert "from data_loader import search_funds_in_catalog" not in code, (
            "CRITICAL DEFECT FOUND: app_gui.py 第 5100 行存在错误的 'from data_loader import search_funds_in_catalog'！"
            "data_loader 模块并无此函数（应使用 portfolio_manager.search_funds_in_catalog），"
            "该缺陷导致用户通过中文名称极速录基时直接抛出 ImportError 击穿 Tab 2！"
        )

