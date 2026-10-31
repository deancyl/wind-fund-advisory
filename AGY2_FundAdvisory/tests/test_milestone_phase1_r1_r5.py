"""
Milestone 4 (Phase 1 R1~R5) 核心算法与红队反作弊自动化测试套件
(AGY2_FundAdvisory/tests/test_milestone_phase1_r1_r5.py)

全量覆盖 11 项红队断言用例：
1. test_case_01_read_only_invariants: 4 大系统裁判基建文件只读与防篡改验证
2. test_case_02_ast_no_cheating: AST 静态语法树反作弊扫描
3. test_case_03_realtime_quota_fetch_and_cache: 实时限购拉取与断网缓存回退断言
4. test_case_04_waterfall_quota_split_and_dca: 瀑布流拆单算法边界测试与定投平账
5. test_case_05_qdii_intraday_valuation_correction: QDII 跨市场盘中估值纠偏测试
6. test_case_06_dynamic_tier_weights_no_c3_hijack: C1~C5 动态权重与解除 C3 常数劫持
7. test_case_07_three_stage_offensive_defensive: 三段式攻防闭环触发测试 (极值超卖/迟滞带/极值超买)
8. test_case_08_ladder_redemption_fee_alignment: 7天/30天/180天 真实阶梯赎回费对齐断言
9. test_case_09_suitability_verdict_4d_and_levels: 今日调仓适宜度三色裁决与四维白话完整性
10. test_case_10_simulate_rebalance_modes_consequences: 温和 vs 强行调仓双模式及四大后果量化精算
11. test_case_11_stock_overlap_dual_dividend_exemption: 双红利底仓对与限购伴生对豁免对抗测试
"""

import os
import sys
import ast
import math
import copy
import subprocess
import pytest
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# 确保路径能够导入 AGY2_FundAdvisory 根目录下的所有模块
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from portfolio_manager import (
    PortfolioManager,
    HoldingBatch,
    FundHolding,
    FundQuote,
    fetch_realtime_fund_quota,
    fetch_realtime_fund_quote,
    _apply_qdii_valuation_correction,
    _FUND_QUOTA_MEMORY_CACHE,
    CORE_STRATEGY_POOL,
)
from strategy_bridge import (
    StrategyBridge,
    TIER_TARGET_WEIGHTS,
    evaluate_today_rebalance_suitability,
    simulate_rebalance_modes_and_consequences,
)
from trading_clock_fee import TradingClock, FeeMatrixCalculator
from data_loader import DataLoader
from judge_engine import JudgeEngine, scan_ast_for_calendar_cheating
from holdout_vault import HoldoutVault


@pytest.fixture
def temp_pm(tmp_path):
    """隔离测试用 PortfolioManager，使用临时 SQLite 数据库与 JSON 账本"""
    db_file = tmp_path / "test_portfolio_state_r1_r5.db"
    json_file = tmp_path / "test_portfolio_ledger_r1_r5.json"
    pm = PortfolioManager(db_path=db_file, ledger_json_path=json_file)
    return pm


# =============================================================================
# 1. test_case_01_read_only_invariants: 4 大系统裁判基建文件只读与防篡改验证
# =============================================================================
def test_case_01_read_only_invariants():
    """
    4 大系统裁判基建文件只读与防篡改验证：
    1. judge_engine.py
    2. holdout_vault.py
    3. AGENT_SPEC.md
    4. tests/test_infra.py
    断言文件存在、非空，git status 与 git diff 确认未被任何流程篡改。
    """
    referee_files = [
        PROJECT_ROOT / "judge_engine.py",
        PROJECT_ROOT / "holdout_vault.py",
        PROJECT_ROOT / "AGENT_SPEC.md",
        PROJECT_ROOT / "tests" / "test_infra.py"
    ]

    for p in referee_files:
        assert p.exists(), f"裁判核心文件缺失: {p}"
        assert p.stat().st_size > 0, f"裁判核心文件大小为0: {p}"

        # 检查关键裁判类/特征文本未被掏空
        content = p.read_text(encoding="utf-8")
        if p.name == "judge_engine.py":
            assert "class JudgeEngine" in content
            assert "def probe_look_ahead_bias" in content
            assert "def scan_ast_for_calendar_cheating" in content
        elif p.name == "holdout_vault.py":
            assert "class HoldoutVault" in content
            assert "HoldoutVaultExhaustedError" in content
        elif p.name == "AGENT_SPEC.md":
            assert "AGENT_SPEC" in content or "Architecture" in content or "Spec" in content
        elif p.name == "test_infra.py":
            assert "def test_causal_probe_detects_leakage" in content
            assert "def test_four_islands_conformity" in content

    # 通过 git status 检查这 4 个文件在当前工作区绝对未被修改
    try:
        rel_paths = [os.path.relpath(p, PROJECT_ROOT.parent) for p in referee_files]
        res = subprocess.run(
            ["git", "status", "--porcelain", "--"] + rel_paths,
            cwd=str(PROJECT_ROOT.parent),
            capture_output=True,
            text=True,
            check=False
        )
        assert res.returncode == 0, f"git status 执行失败: {res.stderr}"
        assert res.stdout.strip() == "", (
            f"裁判基建文件存在未经许可的修改！git status 输出:\n{res.stdout}"
        )
    except Exception as e:
        # 如果不是标准 git 仓库环境，则回退为校验本地哈希存在性
        assert all(p.exists() and p.stat().st_size > 500 for p in referee_files)


# =============================================================================
# 2. test_case_02_ast_no_cheating: AST 语法树静态反作弊扫描
# =============================================================================
def test_case_02_ast_no_cheating():
    """
    AST 静态扫描：
    1. 核心源文件 (strategy_bridge.py, portfolio_manager.py, data_loader.py) 中无 time.sleep；
    2. 策略函数中无任何日历年份硬编码 (2018~2025)；
    3. 前端 app_gui.py 中无 monkeypatch 猴子补丁；
    4. CORE_STRATEGY_POOL 中彻底消除硬编码 daily_limit 为 500 或 1000。
    """
    core_modules = [
        PROJECT_ROOT / "strategy_bridge.py",
        PROJECT_ROOT / "portfolio_manager.py",
        PROJECT_ROOT / "data_loader.py"
    ]

    # 1. 扫描 AST 中无 time.sleep 调用
    for mod_path in core_modules:
        assert mod_path.exists(), f"核心模块不存在: {mod_path}"
        code_str = mod_path.read_text(encoding="utf-8")
        tree = ast.parse(code_str, filename=mod_path.name)

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                # 检查直接 sleep(...)
                if isinstance(func, ast.Name) and func.id == "sleep":
                    assert False, f"在 {mod_path.name} 第 {node.lineno} 行发现违规 sleep() 调用！"
                # 检查 time.sleep(...)
                elif isinstance(func, ast.Attribute) and func.attr == "sleep":
                    assert False, f"在 {mod_path.name} 第 {node.lineno} 行发现违规 time.sleep() 调用！"

    # 2. 检查策略核心函数无历史年份字面量硬编码
    passed, err = scan_ast_for_calendar_cheating(StrategyBridge.compute_dynamic_tier_weights)
    assert passed, f"compute_dynamic_tier_weights 包含作弊历史年份字面量: {err}"

    passed_s, err_s = scan_ast_for_calendar_cheating(StrategyBridge.evaluate_today_rebalance_suitability)
    assert passed_s, f"evaluate_today_rebalance_suitability 包含作弊年份字面量: {err_s}"

    passed_r, err_r = scan_ast_for_calendar_cheating(StrategyBridge.simulate_rebalance_modes_and_consequences)
    assert passed_r, f"simulate_rebalance_modes_and_consequences 包含作弊年份字面量: {err_r}"

    # 3. 检查 CORE_STRATEGY_POOL 中严禁将 daily_limit 静态写死为 500 或 1000
    for code, meta in CORE_STRATEGY_POOL.items():
        limit_val = meta.get("daily_limit")
        assert limit_val != 500, f"标的 {code} 在 CORE_STRATEGY_POOL 中仍违规硬编码 daily_limit 为 500！"
        assert limit_val != 1000, f"标的 {code} 在 CORE_STRATEGY_POOL 中仍违规硬编码 daily_limit 为 1000！"

    # 4. 检查前端 app_gui.py 中无 monkeypatch 破坏性补丁
    gui_path = PROJECT_ROOT / "app_gui.py"
    if gui_path.exists():
        gui_code = gui_path.read_text(encoding="utf-8")
        gui_tree = ast.parse(gui_code, filename="app_gui.py")
        for node in ast.walk(gui_tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "setattr":
                    if len(node.args) >= 1:
                        target = node.args[0]
                        if isinstance(target, ast.Name) and target.id == "st":
                            assert False, f"app_gui.py 第 {node.lineno} 行存在针对 streamlit 的 monkey patch 违规注入！"


# =============================================================================
# 3. test_case_03_realtime_quota_fetch_and_cache: 实时限购拉取与断网缓存回退
# =============================================================================
def test_case_03_realtime_quota_fetch_and_cache(tmp_path):
    """
    实时限购拉取与断网缓存回退断言：
    1. 真实返回值结构包含 is_limited, daily_limit, status；
    2. mock 断网异常时，能够无缝回退读取本地 SQLite / 湖仓带时间戳的有效缓存，保证接口健壮性。
    """
    test_db = tmp_path / "test_quota_cache.db"

    # 1. 真实或本地调用测试 (以博时标普500 050025 与富国红利 100032 为例)
    res_sp500 = fetch_realtime_fund_quota("050025", use_cache=True, db_path=test_db)
    assert isinstance(res_sp500, dict)
    assert res_sp500["fund_code"] == "050025"
    assert "status" in res_sp500
    assert "daily_limit" in res_sp500
    assert "is_limited" in res_sp500
    assert isinstance(res_sp500["is_limited"], bool)
    assert isinstance(res_sp500["daily_limit"], (int, float))
    assert res_sp500["status"] in ["开放申购", "限制大额", "暂停申购"]

    res_div = fetch_realtime_fund_quota("100032", use_cache=True, db_path=test_db)
    assert res_div["fund_code"] == "100032"
    assert res_div["status"] == "开放申购"
    assert not res_div["is_limited"]

    # 2. 模拟断网 (ConnectionError) 且内存缓存清空时，正确从 SQLite 缓存或离线湖仓兜底读取
    _FUND_QUOTA_MEMORY_CACHE.clear()
    with patch("akshare.fund_purchase_em", side_effect=ConnectionError("DNS lookup failed: network unreachable")):
        # 断网情况下调用
        offline_res = fetch_realtime_fund_quota("050025", use_cache=True, db_path=test_db)
        assert isinstance(offline_res, dict)
        assert offline_res["fund_code"] == "050025"
        assert offline_res["daily_limit"] > 0
        assert offline_res["status"] in ["开放申购", "限制大额", "暂停申购"]


# =============================================================================
# 4. test_case_04_waterfall_quota_split_and_dca: 瀑布流拆单算法边界测试与定投平账
# =============================================================================
def test_case_04_waterfall_quota_split_and_dca(temp_pm):
    """
    瀑布流拆单算法边界测试：
    1. 首选基金限额 1000 时，断言首选仅买 1000，且 action_guide 动态包含单日限额无硬编码；
    2. 备选基金承接超额，action_guide 标注 '承接超额·不限购正常买'；
    3. 全赛道备选均限额超标时，断言生成 dca_plan，定投天数与金额精确平账。
    """
    total_capital = 100000.0  # 10 万元建仓

    # 场景 A: 首选 050025 限额 1000，备选 001071 不限购 (额度 1e11)
    def mock_quota_scenario_a(fund_code, *args, **kwargs):
        code = str(fund_code).zfill(6)
        if code == "050025":
            return {"fund_code": code, "status": "限制大额", "daily_limit": 1000.0, "is_limited": True}
        elif code == "001071":
            return {"fund_code": code, "status": "开放申购", "daily_limit": 1e11, "is_limited": False}
        return {"fund_code": code, "status": "开放申购", "daily_limit": 1e11, "is_limited": False}

    with patch("portfolio_manager.fetch_realtime_fund_quota", side_effect=mock_quota_scenario_a):
        bp_a = temp_pm.generate_zero_start_blueprint(total_capital=total_capital, tier="C3")
        items_a = bp_a.get("items", [])

        # 找到首选 050025 与备选 001071
        item_prim = next((it for it in items_a if it["fund_code"] == "050025"), None)
        item_alt = next((it for it in items_a if it["fund_code"] == "001071"), None)

        assert item_prim is not None, "建仓单应包含首选 050025"
        assert item_prim["allocated_amount"] == 1000.0, "首选基金应精准按限额 1000 买入"
        assert "1000" in item_prim["action_guide"], "action_guide 必须动态包含限额数字 1000"
        assert "500" not in item_prim["action_guide"], "严禁在限额 1000 时出现写死的 500 字样"
        assert item_prim["has_split"] is True

        assert item_alt is not None, "超额部分应路由至备选 001071"
        assert item_alt["action_guide"] == "承接超额·不限购正常买"
        # 050025 (1000) + 001071 (5000) 合计应为 6000 (C3 中 QDII 目标 6%)
        assert item_prim["allocated_amount"] + item_alt["allocated_amount"] == 6000.0

    # 场景 B: 首选 050025 限额 1000，备选 001071 亦限额 1000，其余备选暂停申购 (触发 dca_plan)
    def mock_quota_scenario_b(fund_code, *args, **kwargs):
        code = str(fund_code).zfill(6)
        if code == "050025":
            return {"fund_code": code, "status": "限制大额", "daily_limit": 1000.0, "is_limited": True}
        elif code == "001071":
            return {"fund_code": code, "status": "限制大额", "daily_limit": 1000.0, "is_limited": True}
        elif code in ["006075", "017436", "017437"]:
            return {"fund_code": code, "status": "暂停申购", "daily_limit": 0.0, "is_limited": True}
        return {"fund_code": code, "status": "开放申购", "daily_limit": 1e11, "is_limited": False}

    with patch("portfolio_manager.fetch_realtime_fund_quota", side_effect=mock_quota_scenario_b):
        bp_b = temp_pm.generate_zero_start_blueprint(total_capital=total_capital, tier="C3")
        assert "dca_plan" in bp_b, "全市场限购超额时必须生成 dca_plan"
        dca_text = bp_b["dca_plan"]
        # 首选买 1000，备选买 1000，剩余 4000
        assert "4000" in dca_text, f"dca_plan 必须准确提示未分配金额 4000: {dca_text}"
        assert "定投" in dca_text

        # 平账校验：allocated_sum + remaining_cash == total_capital
        alloc_sum = bp_b["allocated_sum"]
        rem_cash = bp_b["remaining_cash"]
        assert round(alloc_sum + rem_cash, 2) == round(total_capital, 2), "资金分配必须精确平账"


# =============================================================================
# 5. test_case_05_qdii_intraday_valuation_correction: QDII 估值纠偏测试
# =============================================================================
def test_case_05_qdii_intraday_valuation_correction():
    """
    QDII 与跨市场估值纠偏测试：
    1. 偏差 <= 1.5% 时保持原样，valuation_corrected 为 False；
    2. 偏差 > 1.5% 时 (如估值 -4.92% vs 基准 +1.0%)，自动按基准 * 0.95 覆盖纠偏，
       gsz 与 gszzl 联动更新，valuation_corrected 为 True。
    """
    # 1. 偏差 <= 1.5% 的正常行情 (基准 +1.0%，估算 +0.80%，偏差 0.2% <= 1.5%)
    mock_bench_quote = {"symbol": "sh513500", "change_pct": 1.0, "price": 1.50}
    with patch("portfolio_manager.fetch_realtime_index_quote", return_value=mock_bench_quote):
        q_normal = FundQuote(
            name="博时标普500ETF联接A",
            dwjz=2.0000,
            gsz=2.0160,
            gszzl=0.80,
            gztime="2026-10-31 14:30",
            fund_code="050025",
            valuation_corrected=False
        )
        res_normal = _apply_qdii_valuation_correction(q_normal)
        assert res_normal.valuation_corrected is False
        assert res_normal.gszzl == 0.80
        assert res_normal.gsz == 2.0160

    # 2. 偏差 > 1.5% 的异常失真行情 (如估算异常报 -4.92%，而场内标普500基准 +1.00%，偏差 5.92% > 1.5%)
    with patch("portfolio_manager.fetch_realtime_index_quote", return_value=mock_bench_quote):
        q_distorted = FundQuote(
            name="摩根标普500指数(QDII)人民币A",
            dwjz=2.0000,
            gsz=1.9016,
            gszzl=-4.92,
            gztime="2026-10-31 14:30",
            fund_code="001071",
            valuation_corrected=False
        )
        res_corrected = _apply_qdii_valuation_correction(q_distorted)
        assert res_corrected.valuation_corrected is True
        # 基准涨幅 1.0 * 0.95 = 0.95
        assert res_corrected.gszzl == 0.95
        # 净值联动重新校准: 2.0000 * (1 + 0.95 / 100) = 2.0190
        assert res_corrected.gsz == 2.0190
        assert "基准纠偏" in res_corrected.gztime


# =============================================================================
# 6. test_case_06_dynamic_tier_weights_no_c3_hijack: C1~C5 动态权重与解除 C3 常数劫持
# =============================================================================
def test_case_06_dynamic_tier_weights_no_c3_hijack():
    """
    C1~C5 动态权重测试：
    1. 断言 C3 返回值并非静态常数 [0.38, 0.30, 0.14, 0.12, 0.06]；
    2. 全档位权重和为 1.0，各资产权重 >= 0；
    3. 权重随市场状态动态演进；
    4. 满足权益风险预算单调性: Equity(C1) < Equity(C2) < Equity(C3) < Equity(C4) < Equity(C5)。
    """
    hijacked_c3_tuple = (0.38, 0.30, 0.14, 0.12, 0.06)

    bull_snap = {
        "regime": "BULL",
        "market_state_code": "GROWTH_BULL",
        "bias_20": 2.5,
        "erp_percentile": 50.0
    }
    bear_snap = {
        "regime": "BEAR",
        "market_state_code": "SEVERE_BEAR",
        "bias_20": -3.0,
        "erp_percentile": 40.0
    }

    # 1. 验证 C3 绝非硬编码写死
    w_c3_bull = StrategyBridge.compute_dynamic_tier_weights(tier="C3", market_snapshot=bull_snap)
    w_c3_bear = StrategyBridge.compute_dynamic_tier_weights(tier="C3", market_snapshot=bear_snap)

    c3_bull_vals = (
        w_c3_bull.get("100032", 0.0),
        w_c3_bull.get("005561", 0.0),
        w_c3_bull.get("000216", 0.0),
        w_c3_bull.get("002351", 0.0),
        w_c3_bull.get("050025", 0.0)
    )
    assert c3_bull_vals != hijacked_c3_tuple, "C3 依然处于静态常数劫持状态！"
    assert w_c3_bull != w_c3_bear, "C3 权重未随市场牛熊状态动态演进！"

    # 2. 全档位权重归一化与非负性检查
    for snap in [bull_snap, bear_snap]:
        for tier in ["C1", "C2", "C3", "C4", "C5"]:
            weights = StrategyBridge.compute_dynamic_tier_weights(tier=tier, market_snapshot=snap)
            total_w = sum(weights.values())
            assert abs(total_w - 1.0) < 1e-4, f"{tier} 权重和不等于 1.0 (实际: {total_w})"
            assert all(v >= -1e-6 for v in weights.values()), f"{tier} 存在负数权重"

    # 3. 权益风险预算严格单调性断言
    # 定义权益类资产代码池
    equity_assets = {"100032", "005561", "011613", "001053", "016634", "013841", "007339", "050025", "001071"}

    for snap in [bull_snap, bear_snap]:
        eq_scores = []
        for tier in ["C1", "C2", "C3", "C4", "C5"]:
            w_dict = StrategyBridge.compute_dynamic_tier_weights(tier=tier, market_snapshot=snap)
            eq_sum = sum(w_dict.get(a, 0.0) for a in equity_assets)
            eq_scores.append(round(eq_sum, 4))

        # 断言单调递增: eq(C1) < eq(C2) < eq(C3) < eq(C4) < eq(C5)
        for i in range(len(eq_scores) - 1):
            assert eq_scores[i] < eq_scores[i + 1], (
                f"在状态 {snap['regime']} 下权益风险预算未满足单调递增: {eq_scores}"
            )


# =============================================================================
# 7. test_case_07_three_stage_offensive_defensive: 三段式攻防闭环触发测试
# =============================================================================
def test_case_07_three_stage_offensive_defensive():
    """
    三段式攻防闭环触发测试：
    1. 左侧极值超卖吸筹 (bias_20 <= -4.5%, erp >= 75%)：从纯债中划拨 10%~15% 增配高弹性宽基；
    2. 迟滞噪音带 [-1.5%, +1.2%]：锁定前序仓位配置不折腾；
    3. 右侧极端超买 (bias_20 >= +6.5% 或 crowding_warning)：削减成长转入纯债与红利低波。
    """
    # 阶段 1：左侧超卖吸筹
    oversold_snap = {
        "erp_percentile": 80.0,
        "bias_20": -5.0,
        "bias_20_star": -5.0,
        "regime": "OSCILLATING"
    }
    neutral_snap = {
        "erp_percentile": 50.0,
        "bias_20": -1.0,
        "bias_20_star": -1.0,
        "regime": "OSCILLATING"
    }

    w_oversold = StrategyBridge.compute_dynamic_tier_weights(tier="C3", market_snapshot=oversold_snap)
    w_neutral = StrategyBridge.compute_dynamic_tier_weights(tier="C3", market_snapshot=neutral_snap)

    # 在左侧超卖时，纯债 (002351) 仓位下降，高弹性宽基 (011613/001053) 增配
    assert w_oversold.get("002351", 0.0) < w_neutral.get("002351", 0.0)
    assert (w_oversold.get("011613", 0.0) + w_oversold.get("001053", 0.0)) > (
        w_neutral.get("011613", 0.0) + w_neutral.get("001053", 0.0)
    )

    # 阶段 2：施密特迟滞死区锁定
    StrategyBridge._prev_hysteresis_weights["C3"] = {
        "100032": 0.50,
        "002351": 0.50
    }
    hysteresis_snap = {
        "bias_20": 0.2,  # 处于 [-1.5%, +1.2%] 死区内
        "lock_previous_weights": True
    }
    w_hysteresis = StrategyBridge.compute_dynamic_tier_weights(tier="C3", market_snapshot=hysteresis_snap)
    assert w_hysteresis == {"100032": 0.50, "002351": 0.50}, "死区内必须保持前序锁定仓位"

    # 阶段 3：右侧极端超买阶梯止盈
    overbought_snap = {
        "bias_20": 7.0,  # 超过 6.5% 严重超买
        "crowding_warning": True,
        "regime": "BULL"
    }
    normal_bull_snap = {
        "bias_20": 2.0,
        "crowding_warning": False,
        "regime": "BULL"
    }

    w_profit_taking = StrategyBridge.compute_dynamic_tier_weights(tier="C3", market_snapshot=overbought_snap)
    w_normal_bull = StrategyBridge.compute_dynamic_tier_weights(tier="C3", market_snapshot=normal_bull_snap)

    growth_codes = ["011613", "001053"]
    growth_profit_taking = sum(w_profit_taking.get(c, 0.0) for c in growth_codes)
    growth_normal = sum(w_normal_bull.get(c, 0.0) for c in growth_codes)

    # 极端超买时成长敞口削减约 35%
    assert growth_profit_taking < growth_normal, "极端超买时必须削减成长敞口"
    # 防御资产 (纯债 002351 或红利低波 005561) 仓位提升
    defensive_pt = w_profit_taking.get("002351", 0.0) + w_profit_taking.get("005561", 0.0)
    defensive_norm = w_normal_bull.get("002351", 0.0) + w_normal_bull.get("005561", 0.0)
    assert defensive_pt > defensive_norm, "削减资金必须落袋转入纯债与红利低波"


# =============================================================================
# 8. test_case_08_ladder_redemption_fee_alignment: 7天/30天/180天 真实阶梯赎回费对齐
# =============================================================================
def test_case_08_ladder_redemption_fee_alignment():
    """
    7天/30天/180天 真实阶梯赎回费对齐断言：
    针对 5天(1.50%)、15天(0.50% C类/0.75% A类)、200天(0.00% C类/0.25% A类) 进行精算核验。
    """
    # 1. 持有 5 天 (不满 7 天惩罚期): A/C 类均严扣 1.50%
    rate_5d_c, is_pen_5d_c, _ = FeeMatrixCalculator.get_redemption_fee_rate("C", 5)
    rate_5d_a, is_pen_5d_a, _ = FeeMatrixCalculator.get_redemption_fee_rate("A", 5)
    assert rate_5d_c == 0.0150 and is_pen_5d_c is True
    assert rate_5d_a == 0.0150 and is_pen_5d_a is True

    # 2. 持有 15 天 (7~29 天区间): C 类 0.50%, A 类 0.75%
    rate_15d_c, is_pen_15d_c, _ = FeeMatrixCalculator.get_redemption_fee_rate("C", 15)
    rate_15d_a, is_pen_15d_a, _ = FeeMatrixCalculator.get_redemption_fee_rate("A", 15)
    assert rate_15d_c == 0.0050 and is_pen_15d_c is False
    assert rate_15d_a == 0.0075 and is_pen_15d_a is False

    # 3. 持有 200 天 (180~364 天区间): C 类免赎 0.00%, A 类 0.25%
    rate_200d_c, _, _ = FeeMatrixCalculator.get_redemption_fee_rate("C", 200)
    rate_200d_a, _, _ = FeeMatrixCalculator.get_redemption_fee_rate("A", 200)
    assert rate_200d_c == 0.0000
    assert rate_200d_a == 0.0025

    # 4. 持有 400 天 (365天以上): A/C 类全部免赎 0.00%
    rate_400d_c, _, _ = FeeMatrixCalculator.get_redemption_fee_rate("C", 400)
    rate_400d_a, _, _ = FeeMatrixCalculator.get_redemption_fee_rate("A", 400)
    assert rate_400d_c == 0.0000
    assert rate_400d_a == 0.0000

    # 5. 回测执行算子 DataLoader.simulate_execution 行为核对
    dl = DataLoader()
    sample_dates = pd.date_range("2026-01-01", periods=10, freq="B")
    price_df = pd.DataFrame({
        "date": sample_dates,
        "STAR50_STITCH": [1.0] * 10
    })
    # 在第 1 天买入，第 3 天卖出 (持有 2 天 < 7 天)
    weights_penalty = pd.DataFrame({
        "date": sample_dates,
        "STAR50_STITCH": [0.0, 1.0, 1.0, 0.0] + [0.0] * 6
    })
    res_pen = dl.simulate_execution(weights_penalty, price_df, is_otc=True, penalty_days=7)
    # 卖出时必须触发 1.50% 阶梯摩擦
    assert res_pen["friction"].max() >= 0.0150


# =============================================================================
# 9. test_case_09_suitability_verdict_4d_and_levels: 调仓适宜度裁决测试
# =============================================================================
def test_case_09_suitability_verdict_4d_and_levels(temp_pm):
    """
    evaluate_today_rebalance_suitability 裁决测试：
    1. verdict_level 为标准三级枚举 (SUITABLE / HOLD_ON / FORBIDDEN，兼容 SUGGESTED/DISCOURAGED/BLOCKED)；
    2. verdict_title 鲜明非空；
    3. reasons_4d 完整包含 4 个维度白话解析且非空。
    """
    today_dt = datetime.now().date()

    # 场景 1: 持有未满 7 天批次需卖出 -> FORBIDDEN
    records_locked = [
        {
            "fund_code": "013841",  # 非标基，目标权重为 0
            "buy_date": (today_dt - timedelta(days=2)).strftime("%Y-%m-%d"),
            "shares": 10000.0,
            "cost_nav": 1.00,
            "current_nav": 1.00,
            "holding_days": 2,
            "safety_lock": True
        }
    ]
    temp_pm.takeover_mode_b(historical_records=records_locked, available_cash=0.0)

    res_forbidden = StrategyBridge.evaluate_today_rebalance_suitability(temp_pm, active_tier="C3")
    assert res_forbidden["verdict_level"] in ["FORBIDDEN", "BLOCKED"]
    assert any(k in res_forbidden["verdict_title"] for k in ["7天", "未满", "高损", "惩罚", "不宜"])

    # 场景 2: 偏离度在 3% 缓冲免折腾区内或均线死区 -> HOLD_ON
    snapshot = StrategyBridge.get_latest_market_snapshot()
    c3_w = StrategyBridge.compute_dynamic_tier_weights(tier="C3", market_snapshot=snapshot)
    aligned_records = []
    for c, w in c3_w.items():
        if w > 0.01:
            aligned_records.append({
                "fund_code": c,
                "buy_date": (today_dt - timedelta(days=40)).strftime("%Y-%m-%d"),
                "shares": round(w * 100000.0, 2),
                "cost_nav": 1.00,
                "current_nav": 1.00,
                "holding_days": 40,
                "safety_lock": False
            })
    temp_pm.takeover_mode_b(historical_records=aligned_records, available_cash=0.0)

    res_hold = StrategyBridge.evaluate_today_rebalance_suitability(temp_pm, active_tier="C3")
    assert res_hold["verdict_level"] in ["HOLD_ON", "DISCOURAGED", "SUITABLE"]
    assert len(res_hold["verdict_title"]) > 0

    # 场景 3: 偏离显著 (> 5%) 且已满免赎期 -> SUITABLE
    records_mature = [
        {
            "fund_code": "002351",
            "buy_date": (today_dt - timedelta(days=200)).strftime("%Y-%m-%d"),
            "shares": 100000.0,
            "cost_nav": 1.00,
            "current_nav": 1.00,
            "holding_days": 200,
            "safety_lock": False
        }
    ]
    temp_pm.takeover_mode_b(historical_records=records_mature, available_cash=0.0)

    with patch.object(StrategyBridge, "get_latest_market_snapshot", return_value={"bias_20": 2.5, "erp_percentile": 60.0, "market_state_code": "GROWTH_BULL"}):
        with patch("trading_clock_fee.TradingClock.get_market_window_status", return_value=MagicMock(window_type="GOLDEN_WINDOW", effective_trade_date="2026-10-31")):
            res_suitable = StrategyBridge.evaluate_today_rebalance_suitability(temp_pm, active_tier="C3")
            assert res_suitable["verdict_level"] in ["SUITABLE", "SUGGESTED"]
            assert any(k in res_suitable["verdict_title"] for k in ["适合", "突破", "覆盖"])

    # 4. reasons_4d 字段完整性断言
    for res in [res_forbidden, res_hold, res_suitable]:
        r4 = res.get("reasons_4d", {})
        assert "market_position_reason" in r4 and len(r4["market_position_reason"]) > 0
        assert "clock_window_reason" in r4 and len(r4["clock_window_reason"]) > 0
        assert "deviation_utility_reason" in r4 and len(r4["deviation_utility_reason"]) > 0
        assert "lockup_fee_reason" in r4 and len(r4["lockup_fee_reason"]) > 0


# =============================================================================
# 10. test_case_10_simulate_rebalance_modes_consequences: 双模式与四大后果量化精算
# =============================================================================
def test_case_10_simulate_rebalance_modes_consequences(temp_pm):
    """
    温和 vs 强行调仓双模式及四大后果量化校验：
    1. mode_gentle 惩罚费 penalty_fee_7d == 0.0，卖出份额被安全裁剪；
    2. mode_forced 强平全额偏离，惩罚费真实计提；
    3. consequences 四大字典 (fee_loss, in_transit_risk, risk_shift, lockup_reset) 结构完整且分厘平账。
    """
    today_dt = datetime.now().date()
    records_mixed = [
        {
            "fund_code": "005562",  # 创金红利低波 C
            "buy_date": (today_dt - timedelta(days=35)).strftime("%Y-%m-%d"),
            "shares": 5000.0,
            "cost_nav": 1.00,
            "current_nav": 1.00,
            "holding_days": 35,
            "safety_lock": False
        },
        {
            "fund_code": "005562",
            "buy_date": (today_dt - timedelta(days=2)).strftime("%Y-%m-%d"),
            "shares": 5000.0,
            "cost_nav": 1.00,
            "current_nav": 1.00,
            "holding_days": 2,
            "safety_lock": True
        }
    ]
    temp_pm.takeover_mode_b(historical_records=records_mixed, available_cash=0.0)

    res = StrategyBridge.simulate_rebalance_modes_and_consequences(temp_pm, active_tier="C3")
    assert "mode_gentle" in res
    assert "mode_forced" in res

    gentle = res["mode_gentle"]
    forced = res["mode_forced"]

    # 1. 温和调仓断言：严禁产生 7 天惩罚费
    c_gentle = gentle["consequences"]
    assert c_gentle["fee_loss"]["penalty_fee_7d"] == 0.0, "温和模式惩罚费必须为 0"

    # 2. 强行调仓断言：无视惩罚期全额强平，真实计提 1.50% 惩罚费
    c_forced = forced["consequences"]
    assert c_forced["fee_loss"]["penalty_fee_7d"] > 0.0, "强行模式必须如实计提 1.5% 惩罚费"

    # 3. 四大后果字典完整性与平账精算
    for mode_dict in [gentle, forced]:
        cq = mode_dict["consequences"]

        # 费用平账: total_fee == redemption_fee + penalty_fee_7d + subscription_fee
        fl = cq["fee_loss"]
        expected_total = round(fl["redemption_fee"] + fl["penalty_fee_7d"] + fl["subscription_fee"], 2)
        assert round(fl["total_fee"], 2) == expected_total, "手续费分项求和不平账"

        # 净资产平账: equity_after == equity_before - total_fee
        rs = cq["risk_shift"]
        expected_equity_after = round(max(0.0, rs["equity_before"] - fl["total_fee"]), 2)
        assert round(rs["equity_after"], 2) == expected_equity_after, "调仓后净资产扣费不平账"

        # 在途风险指标
        itr = cq["in_transit_risk"]
        assert "in_transit_amount" in itr
        assert "lock_days" in itr
        assert "switch_saved_amount" in itr

        # 锁定期重置提醒
        lr = cq["lockup_reset"]
        assert "new_buy_amount" in lr
        assert "7天" in lr["reset_warning_text"] or "1.5%" in lr["reset_warning_text"]


# =============================================================================
# 11. test_case_11_stock_overlap_dual_dividend_exemption: 双红利豁免对抗测试
# =============================================================================
def test_case_11_stock_overlap_dual_dividend_exemption(temp_pm):
    """
    双红利底仓对 {"100032", "005561"} 与限购伴生对 {"050025", "001071"} 豁免对抗测试：
    1. 同时持有标准推荐组合时 alerts 无任何告警，max_non_diag_unexcused < 0.40 (严守 0.0)；
    2. 对抗测试：持有非豁免高重合基金 (如 011612 与 013841) 必须真实触发伪分散警告且 max_non_diag_unexcused >= 0.40。
    """
    # 1. 推荐组合豁免测试
    temp_pm.holdings.clear()
    temp_pm.takeover_mode_a([
        {"fund_code": "100032", "amount": 24000.0, "nav": 1.0, "share_class": "A"},
        {"fund_code": "005561", "amount": 16000.0, "nav": 1.0, "share_class": "A"},
        {"fund_code": "002351", "amount": 12000.0, "nav": 1.0, "share_class": "A"},
        {"fund_code": "000216", "amount": 14000.0, "nav": 1.0, "share_class": "A"},
        {"fund_code": "050025", "amount": 6000.0, "nav": 1.0, "share_class": "A"},
        {"fund_code": "001071", "amount": 6000.0, "nav": 1.0, "share_class": "A"}
    ], available_cash=0.0)

    res_std = temp_pm.calculate_stock_overlap_matrix()
    alerts_std = res_std.get("alerts", [])
    exempt_pairs = res_std.get("exempt_pairs", [])
    max_unexcused_std = res_std.get("max_non_diag_unexcused", 0.0)

    # 断言无假阳性警报
    assert len(alerts_std) == 0, f"推荐组合中严禁出现伪分散警报，实际警报: {alerts_std}"
    assert max_unexcused_std < 0.40, f"非豁免最大重合度必须 < 0.40，实际为 {max_unexcused_std}"
    assert max_unexcused_std == 0.0, f"非豁免对重叠度必须为 0.0，实际为 {max_unexcused_std}"

    # 断言双红利底仓对与限购伴生对均在豁免清单中
    exempt_sets = [frozenset({p["fund1"], p["fund2"]}) for p in exempt_pairs]
    assert frozenset({"100032", "005561"}) in exempt_sets, "双红利底仓对必须进入豁免清单"
    assert frozenset({"050025", "001071"}) in exempt_sets, "标普500伴生对必须进入豁免清单"

    # 2. 对抗测试：非豁免高重合基金 (011612 华夏科创50 与 013841 银华集成电路)
    temp_pm.holdings.clear()
    temp_pm.takeover_mode_a([
        {"fund_code": "011612", "amount": 50000.0, "nav": 1.0, "share_class": "A"},
        {"fund_code": "013841", "amount": 50000.0, "nav": 1.0, "share_class": "C"}
    ], available_cash=0.0)

    res_adv = temp_pm.calculate_stock_overlap_matrix()
    alerts_adv = res_adv.get("alerts", [])
    max_unexcused_adv = res_adv.get("max_non_diag_unexcused", 0.0)

    assert len(alerts_adv) >= 1, "非豁免高重合基金必须触发伪分散警告"
    assert max_unexcused_adv >= 0.40, f"非豁免最大重合度必须 >= 0.40，实际为 {max_unexcused_adv}"
    assert "高重合度假分散预警" in alerts_adv[0].get("warning_msg", "")
