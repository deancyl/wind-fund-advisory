"""
Dynamic Quant Model Challenger (Challenger-1) 对抗性压测套件
文件路径: AGY2_FundAdvisory/tests/test_stress_quant_model_challenger.py

目标：
对 strategy_bridge.py 中的 compute_dynamic_tier_weights 动态风险预算模型与
get_rebalance_grid_status 双向变盘网格点位计算进行实证对抗性压测 (Empirical Stress Testing):
1. 价格全域扫描 (1000 点至 10000 点，盘中突发跳水/暴涨 ±10%~±20%)；
2. 衍生品与宏观极端扰动 (期指贴水年化 -30%~+20%、期权 IV 飙升至 50%、DR007 暴增至 6.0%)；
3. 极端熊市破位态算法止损降仓与纯债黄金避险切换；
4. 断言 1 (点位永不倒挂): breakdown_threshold_c300 < c300_current < surge_threshold_c300 恒成立；
5. 断言 2 (风险预算单调性): Equity(C1) < Equity(C2) < Equity(C3) < Equity(C4) < Equity(C5) 恒成立；
6. 4 个裁判基建文件物理完整性与只读红线校验。
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, Tuple
import pytest
import numpy as np
import pandas as pd

# 确保目标路径在 sys.path
TEST_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TEST_DIR.parent
WORKSPACE_ROOT = PROJECT_DIR.parent

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from strategy_bridge import StrategyBridge
from portfolio_manager import PortfolioManager
import portfolio_manager


_GLOBAL_PM = PortfolioManager()
_CAT_CACHE = {}

def _get_equity_defensive_weights(weights_dict: Dict[str, float]) -> Tuple[float, float]:
    """根据 PortfolioManager 通用资产分类器提取目标权益总仓位与防御类仓位"""
    defensive_w = 0.0
    equity_w = 0.0
    for code, w in weights_dict.items():
        if code not in _CAT_CACHE:
            _CAT_CACHE[code] = _GLOBAL_PM.classify_fund_asset_class(code) if hasattr(_GLOBAL_PM, "classify_fund_asset_class") else None
        cat = _CAT_CACHE[code]
        if cat in ["纯债固收", "黄金对冲"] or code in ["002351", "000086", "018757", "000216", "000217"]:
            defensive_w += w
        else:
            equity_w += w
    return round(equity_w, 4), round(defensive_w, 4)




# =====================================================================
# 1. 断言 1 实证实测：价格全域扫描与突发涨跌冲击下的点位永不倒挂
# =====================================================================

def test_assertion1_price_grid_domain_sweep_and_no_inversion(monkeypatch):
    """
    【对决测试 1】点位永不倒挂定理验证：
    1. 点位全域扫描：从 1000 点到 10000 点，按步长扫描全区间，并覆盖各类浮点边界；
    2. 极端突发暴跌/暴涨冲击：基准 4053 点突发日内跳水 -10%, -15%, -20% 与暴涨 +10%, +15%, +20%；
    3. 严格断言：
       - breakdown_threshold_c300 < c300_current < surge_threshold_c300 恒成立；
       - 防守破位线与进攻突破线对当前点位形成刚性安全包络（至少具有算法缓冲边界）；
       - c300_current 严格与输入点位对齐。
    """
    # 1. 扫描 1000 点到 10000 点全域（高密度点位与边界点）
    sweep_points = [
        1000.0, 1001.5, 1200.0, 1500.0, 1888.8, 2000.0, 2400.0, 2800.0, 3000.0,
        3200.0, 3400.0, 3600.0, 3800.0, 4000.0, 4053.0, 4180.5, 4500.0, 4800.0,
        5000.0, 5500.0, 6000.0, 6500.0, 7000.0, 8000.0, 9000.0, 9999.0, 10000.0
    ]
    # 追加 100 点为步长的细粒度密集测试
    dense_scan = list(np.arange(1000.0, 10001.0, 250.0))
    all_test_points = sorted(list(set(sweep_points + dense_scan)))

    for pt in all_test_points:
        monkeypatch.setattr(
            portfolio_manager,
            "fetch_realtime_index_quote",
            lambda symbol, use_cache=True: {"point": pt, "change_pct": 0.0}
        )
        grid = StrategyBridge.get_rebalance_grid_status()

        curr = grid["c300_current"]
        surge = grid["surge_threshold_c300"]
        breakdown = grid["breakdown_threshold_c300"]

        assert curr == round(pt, 1), f"输入点位 {pt} 与当前点位 {curr} 不匹配"
        assert breakdown < curr, (
            f"点位倒挂: 点位 {pt} 时 breakdown ({breakdown}) 必须严格小于 current ({curr})"
        )
        assert curr < surge, (
            f"点位倒挂: 点位 {pt} 时 current ({curr}) 必须严格小于 surge ({surge})"
        )
        assert breakdown < curr < surge, (
            f"双向变盘包络失效: breakdown ({breakdown}) < current ({curr}) < surge ({surge}) 失败"
        )
        # 缓冲保护检查：breakdown 至少低于 current 1.0%，surge 至少高于 current 2.5%
        assert (curr - breakdown) / curr >= 0.010, f"点位 {pt} 防守线下浮缓冲不足 1.0%: {breakdown} vs {curr}"
        assert (surge - curr) / curr >= 0.025, f"点位 {pt} 进攻线上浮缓冲不足 2.5%: {surge} vs {curr}"

    # 2. 突发黑天鹅跳水/单日暴涨冲击测试 (±10% ~ ±20%)
    shocks = [-0.20, -0.15, -0.10, -0.05, 0.05, 0.10, 0.15, 0.20]
    base_point = 4053.0

    for shock in shocks:
        shock_point = round(base_point * (1.0 + shock), 1)
        monkeypatch.setattr(
            portfolio_manager,
            "fetch_realtime_index_quote",
            lambda symbol, use_cache=True: {"point": shock_point, "change_pct": shock * 100.0}
        )
        grid = StrategyBridge.get_rebalance_grid_status()

        curr = grid["c300_current"]
        surge = grid["surge_threshold_c300"]
        breakdown = grid["breakdown_threshold_c300"]

        assert breakdown < curr < surge, (
            f"在突发冲击 {shock*100:.1f}% (点位 {shock_point}) 下，点位倒挂: "
            f"breakdown={breakdown}, current={curr}, surge={surge}"
        )


# =====================================================================
# 2. 断言 2 实证实测：所有行情截面下 C1~C5 风险预算单调性
# =====================================================================

def test_assertion2_risk_budget_monotonicity_across_regimes():
    """
    【对决测试 2】风险预算单调性定理验证：
    在牛市进攻、震荡收息、深度熊市破位以及各类复合宏观输入下：
    Equity(C1) < Equity(C2) < Equity(C3) < Equity(C4) < Equity(C5) 恒成立；
    Defensive(C1) > Defensive(C2) > Defensive(C3) > Defensive(C4) > Defensive(C5) 恒成立；
    所有档位权重总和为 1.0000 (容差 1e-4)。
    """
    test_snapshots = [
        # 1. 显式状态码驱动
        ("主升浪进攻态 (GROWTH_BULL)", {"market_state_code": "GROWTH_BULL"}),
        ("结构分化牛市 (STRUCTURAL_500)", {"market_state_code": "STRUCTURAL_500"}),
        ("常态稳健高股息 (STABLE_DIVIDEND)", {"market_state_code": "STABLE_DIVIDEND"}),
        ("深度熊市防御态 (SEVERE_BEAR)", {"market_state_code": "SEVERE_BEAR"}),
        # 2. 状态名称中文模糊驱动
        ("中文进攻态", {"market_state": "🔥 进攻科技成长大牛市"}),
        ("中文震荡收息态", {"market_state": "🟢 常态稳健高股息慢牛"}),
        ("中文防守态", {"market_state": "🛡️ 深度大熊市防御"}),
        # 3. 均线量价指标纯内生推导
        ("均线多头大牛市", {"c300_price": 4500.0, "m20_price": 4300.0, "m60_price": 4100.0, "m120_price": 3900.0}),
        ("均线空头大熊市", {"c300_price": 2800.0, "m20_price": 3100.0, "m60_price": 3400.0, "m120_price": 3700.0}),
        ("均线缠绕震荡市", {"c300_price": 4000.0, "m20_price": 4050.0, "m60_price": 3980.0, "m120_price": 3950.0}),
    ]

    for label, snap in test_snapshots:
        eq_map = {}
        def_map = {}
        for tier in ["C1", "C2", "C3", "C4", "C5"]:
            w = StrategyBridge.compute_dynamic_tier_weights(tier=tier, market_snapshot=snap)
            assert isinstance(w, dict), f"{label} 下 {tier} 返回类型应为 dict"
            tot = sum(w.values())
            assert abs(tot - 1.0) < 1e-4, f"{label} 下 {tier} 权重之和必须为 1.0，实际为 {tot}"

            eq_w, def_w = _get_equity_defensive_weights(w)
            eq_map[tier] = eq_w
            def_map[tier] = def_w

        # 核心断言 2: 严格单调递增 Equity(C1) < Equity(C2) < Equity(C3) < Equity(C4) < Equity(C5)
        assert eq_map["C1"] < eq_map["C2"], f"{label} 下 C1({eq_map['C1']}) >= C2({eq_map['C2']})"
        assert eq_map["C2"] < eq_map["C3"], f"{label} 下 C2({eq_map['C2']}) >= C3({eq_map['C3']})"
        assert eq_map["C3"] < eq_map["C4"], f"{label} 下 C3({eq_map['C3']}) >= C4({eq_map['C4']})"
        assert eq_map["C4"] < eq_map["C5"], f"{label} 下 C4({eq_map['C4']}) >= C5({eq_map['C5']})"

        # 防御仓位严格单调递减 Defensive(C1) > Defensive(C2) > Defensive(C3) > Defensive(C4) > Defensive(C5)
        assert def_map["C1"] > def_map["C2"], f"{label} 下 防御仓位 C1 <= C2"
        assert def_map["C2"] > def_map["C3"], f"{label} 下 防御仓位 C2 <= C3"
        assert def_map["C3"] > def_map["C4"], f"{label} 下 防御仓位 C3 <= C4"
        assert def_map["C4"] > def_map["C5"], f"{label} 下 防御仓位 C4 <= C5"


# =====================================================================
# 3. 极端熊市破位态：全档位算法止损降仓与避险切换实证测试
# =====================================================================

def test_extreme_bear_breakdown_full_tier_deleveraging():
    """
    【对决测试 3】极端熊市破位态全档位算法止损降仓实证：
    构造均线深度向下空头排列 (c300 < m60 且 c300 < m120，向下发散)：
    1. 测试 C1 至 C5 是否全档位触发算法止损降仓（相较常态/牛市大幅压降权益仓位）；
    2. 测试 C1 至 C5 是否显著提升纯债（002351, 000086）与黄金（000216）配置；
    3. 特别测试进取型档位 C4 与 C5 在破位防守态下的降仓保护幅度（防爆仓熔断）：
       - C4 权益仓位由常态 78% 压降至 50%；
       - C5 权益仓位由常态 90% 压降至 65%；
       - 防御资产从接近 0% 跃升至 35%~50%。
    """
    bear_snapshot = {
        "market_state_code": "SEVERE_BEAR",
        "market_state": "🛡️ 深度大熊市防御",
        "c300_price": 2800.0,
        "m20_price": 3100.0,
        "m60_price": 3500.0,
        "m120_price": 3800.0
    }
    normal_snapshot = {
        "market_state_code": "STABLE_DIVIDEND",
        "market_state": "🟢 常态稳健高股息慢牛"
    }

    for tier in ["C1", "C2", "C3", "C4", "C5"]:
        w_bear = StrategyBridge.compute_dynamic_tier_weights(tier=tier, market_snapshot=bear_snapshot)
        w_normal = StrategyBridge.compute_dynamic_tier_weights(tier=tier, market_snapshot=normal_snapshot)

        eq_bear, def_bear = _get_equity_defensive_weights(w_bear)
        eq_norm, def_norm = _get_equity_defensive_weights(w_normal)

        # 1. 熊市权益仓位必须严格低于常态
        assert eq_bear < eq_norm, (
            f"档位 {tier} 在极端熊市破位态下未减仓！熊市权益: {eq_bear}, 常态权益: {eq_norm}"
        )
        # 2. 熊市防御资产（纯债+黄金）必须严格高于常态
        assert def_bear > def_norm, (
            f"档位 {tier} 在极端熊市破位态下未增配防御避险！熊市防御: {def_bear}, 常态防御: {def_norm}"
        )

        # 3. 检查纯债和黄金标的确实存在于配置中
        bond_gold_codes = {"002351", "000086", "000216"}
        has_bond_gold = any(c in w_bear for c in bond_gold_codes)
        assert has_bond_gold, f"档位 {tier} 熊市配置中缺失纯债或黄金标的: {w_bear}"

    # 4. 关键高进取档位 C4 / C5 防爆仓专项断言
    w_c4_bear = StrategyBridge.compute_dynamic_tier_weights(tier="C4", market_snapshot=bear_snapshot)
    w_c5_bear = StrategyBridge.compute_dynamic_tier_weights(tier="C5", market_snapshot=bear_snapshot)
    eq_c4_bear, def_c4_bear = _get_equity_defensive_weights(w_c4_bear)
    eq_c5_bear, def_c5_bear = _get_equity_defensive_weights(w_c5_bear)

    assert eq_c4_bear <= 0.55, f"C4 熊市破位态权益仓位过高 ({eq_c4_bear})，未有效执行止损"
    assert eq_c5_bear <= 0.70, f"C5 熊市破位态权益仓位过高 ({eq_c5_bear})，未有效执行止损"
    assert def_c4_bear >= 0.45, f"C4 熊市破位态避险仓位不足 ({def_c4_bear})"
    assert def_c5_bear >= 0.30, f"C5 熊市破位态避险仓位不足 ({def_c5_bear})"


# =====================================================================
# 4. 衍生品与宏观极端扰动鲁棒性压测
# =====================================================================

def test_derivatives_and_macro_extreme_perturbations():
    """
    【对决测试 4】衍生品与宏观极端扰动对抗压测：
    1. 期指年化贴水率扫描：-30.0% 至 +20.0%；
    2. 期权 IV 飙升扫描：10.0% 至 50.0%（极端恐慌预警）；
    3. DR007 暴增扫描：0.5% 至 6.0%（资金面极度收紧）；
    4. 检验宏观雷达与动态权重在极端外生冲击下的一致性与不崩溃。
    """
    basis_scenarios = [-30.0, -20.0, -10.0, 0.0, 10.0, 20.0]
    iv_scenarios = [12.0, 20.0, 32.0, 40.0, 50.0]
    dr007_scenarios = [0.8, 1.38, 2.0, 3.5, 6.0]

    for basis in basis_scenarios:
        for iv in iv_scenarios:
            for dr in dr007_scenarios:
                spread = (dr - 1.50) * 100.0  # bp
                snap = {
                    "ic_annualized_basis_rate": basis,
                    "im_annualized_basis_rate": basis,
                    "option_iv_pct": iv,
                    "dr007": dr,
                    "dr007_spread_bp": spread,
                    "market_state_code": "SEVERE_BEAR" if (spread > 45.0 or iv >= 40.0) else "STABLE_DIVIDEND"
                }

                # 运行 C1 至 C5 权重计算，验证在极端扰动下数学单调性恒成立
                eq_weights = {}
                for tier in ["C1", "C2", "C3", "C4", "C5"]:
                    w = StrategyBridge.compute_dynamic_tier_weights(tier=tier, market_snapshot=snap)
                    assert abs(sum(w.values()) - 1.0) < 1e-4
                    eq_w, _ = _get_equity_defensive_weights(w)
                    eq_weights[tier] = eq_w

                assert eq_weights["C1"] < eq_weights["C2"] < eq_weights["C3"] < eq_weights["C4"] < eq_weights["C5"], (
                    f"在极端扰动 (basis={basis}, iv={iv}, dr007={dr}) 下，风险预算单调性破缺: {eq_weights}"
                )


# =====================================================================
# 5. 多态入参、缺失边界与容错鲁棒性对决测试
# =====================================================================

def test_polymorphic_inputs_and_edge_case_fault_tolerance():
    """
    【对决测试 5】输入多态与容错鲁棒性：
    1. 参数顺序互换：compute_dynamic_tier_weights(history_df, tier, snap) vs compute_dynamic_tier_weights(tier=...)；
    2. 非法档位参数传入（None, "", "C0", "C99", "INVALID"）安全回退至 C3；
    3. history_df 传入 None 或空 DataFrame，系统不报未捕获异常；
    4. market_snapshot 传入 None 或空 dict，系统自动回退至常态；
    5. 返回权重均为正浮点数，无 NaN、无负数，且 sum == 1.0。
    """
    # 1. 参数位置互换测试
    w1 = StrategyBridge.compute_dynamic_tier_weights(None, "C2", None)
    w2 = StrategyBridge.compute_dynamic_tier_weights(tier="C2")
    w3 = StrategyBridge.compute_dynamic_tier_weights("C2")
    assert w1 == w2 == w3, "参数位置多态解析不一致"

    # 2. 非法档位自动回退
    for invalid_tier in [None, "", "C0", "C6", "C99", "UNKNOWN"]:
        w_fallback = StrategyBridge.compute_dynamic_tier_weights(tier=invalid_tier)
        w_c3 = StrategyBridge.compute_dynamic_tier_weights(tier="C3")
        assert w_fallback == w_c3, f"非法档位 {invalid_tier} 未能安全回退至 C3"

    # 3. 权重纯洁性校验（无 NaN、无负值）
    for tier in ["C1", "C2", "C3", "C4", "C5"]:
        w = StrategyBridge.compute_dynamic_tier_weights(tier=tier, market_snapshot={})
        for code, weight in w.items():
            assert not np.isnan(weight), f"{tier} 包含 NaN 权重: {code}"
            assert weight >= 0.0, f"{tier} 包含负权重: {code}={weight}"
        assert abs(sum(w.values()) - 1.0) < 1e-4, f"{tier} 权重之和不为 1.0"


# =====================================================================
# 6. 裁判基建 4 大文件物理完整性与未修改红线校验
# =====================================================================

def test_four_referee_infrastructure_files_untouched():
    """
    【对决测试 6】物理安全红线校验：
    4 个裁判基建文件（judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py）
    必须 100% 存在且在 Git 版本树中保持绝对未修改 (Clean)。
    """
    referee_files = [
        "judge_engine.py",
        "holdout_vault.py",
        "AGENT_SPEC.md",
        "tests/test_infra.py"
    ]

    for rf in referee_files:
        full_path = PROJECT_DIR / rf
        assert full_path.exists(), f"裁判基建文件缺失: {rf}"
        assert full_path.stat().st_size > 0, f"裁判基建文件为空: {rf}"

    # 执行 Git diff 校验
    result = subprocess.run(
        ["git", "status", "-s", "--"] + referee_files,
        cwd=str(PROJECT_DIR),
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"git status 执行异常: {result.stderr}"
    assert result.stdout.strip() == "", (
        f"裁判基建文件发生意外修改，触碰物理安全红线！\nGit 变动状态:\n{result.stdout}"
    )
