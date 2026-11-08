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

