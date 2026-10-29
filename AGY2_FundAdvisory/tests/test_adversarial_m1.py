"""
Milestone 1 Empirical Adversarial Stress & Verification Harness
File: AGY2_FundAdvisory/tests/test_adversarial_m1.py
Author: Challenger 1 (challenger_m1_1)
"""

import sys
import os
import copy
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

# Setup paths
APP_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = APP_DIR.parent if APP_DIR.name == "AGY2_FundAdvisory" else APP_DIR
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from portfolio_manager import (
    PortfolioManager,
    FundHolding,
    HoldingBatch,
    FUND_LOOK_THROUGH_DATA,
    resolve_stock_symbol
)


# ==============================================================================
# 1. 接口契约严苛断言 (Strict Interface Contract Assertions)
# ==============================================================================

def test_contract_screen_fund_equity():
    """验证权益基金 screen_fund_look_through_risk 返回数据结构与类型绝对符合契约"""
    pm = PortfolioManager(db_path=":memory:")
    res = pm.screen_fund_look_through_risk("100032")

    # 顶层契约字段校验
    required_keys = {
        "fund_code": str,
        "fund_name": str,
        "is_ashare_equity": bool,
        "penetration_risk_score": float,
        "risk_level": str,
        "risk_badge": str,
        "danger_count": int,
        "watch_count": int,
        "top_stocks_screen": list,
        "diagnosis_summary": str
    }
    for k, t in required_keys.items():
        assert k in res, f"Missing key in screen_fund_look_through_risk: {k}"
        assert isinstance(res[k], t), f"Key {k} type mismatch: expected {t}, got {type(res[k])}"

    assert res["fund_code"] == "100032"
    assert res["is_ashare_equity"] is True
    assert 0.0 <= res["penetration_risk_score"] <= 100.0
    assert res["risk_level"] in ["Safe", "Watch", "Danger"]
    assert res["risk_badge"] in ["🟢 健康", "🟡 关注", "🔴 预警"]
    assert res["danger_count"] >= 0
    assert res["watch_count"] >= 0
    assert len(res["top_stocks_screen"]) > 0

    # 股票层级契约字段校验
    stock_required_keys = {
        "symbol": str,
        "stock_name": str,
        "name": str,
        "goodwill_ratio_pct": (int, float),
        "double_high_risk": bool,
        "pledge_ratio_controlling_pct": (int, float),
        "warning_close_line_status": str,
        "unlock_market_value_billion": (int, float),
        "fcf_billion": (int, float),
        "stock_score": (int, float),
        "risk_score": (int, float),
        "risk_level": str,
        "risk_badge": str,
        "risk_reasons": list,
        "deductions_detail": list
    }
    for stock in res["top_stocks_screen"]:
        for sk, st in stock_required_keys.items():
            assert sk in stock, f"Stock item missing key: {sk}"
            assert isinstance(stock[sk], st), f"Stock key {sk} type mismatch: expected {st}, got {type(stock[sk])}"
        assert 0.0 <= stock["stock_score"] <= 100.0
        assert 0.0 <= stock["risk_score"] <= 100.0
        assert stock["risk_level"] in ["Safe", "Watch", "Danger"]
        assert stock["risk_badge"] in ["🟢 健康", "🟡 关注", "🔴 预警"]


def test_contract_calculate_portfolio_penetration_risk():
    """验证组合整体 calculate_portfolio_penetration_risk 返回数据结构与类型绝对符合契约"""
    pm = PortfolioManager(db_path=":memory:")
    pm.takeover_mode_a([
        {"fund_code": "100032", "amount": 60000.0, "nav": 1.0},
        {"fund_code": "002351", "amount": 40000.0, "nav": 1.0}
    ], available_cash=5000.0)

    res = pm.calculate_portfolio_penetration_risk()
    required_keys = {
        "portfolio_risk_index": float,
        "risk_level": str,
        "risk_badge": str,
        "danger_stock_count": int,
        "watch_stock_count": int,
        "high_risk_reasons": list,
        "funds_breakdown": list
    }
    for k, t in required_keys.items():
        assert k in res, f"Missing key in calculate_portfolio_penetration_risk: {k}"
        assert isinstance(res[k], t), f"Key {k} type mismatch: expected {t}, got {type(res[k])}"

    assert 0.0 <= res["portfolio_risk_index"] <= 100.0
    assert res["risk_level"] in ["Safe", "Watch", "Danger"]
    assert res["risk_badge"] in ["🟢 健康", "🟡 关注", "🔴 预警"]
    assert res["danger_stock_count"] >= 0
    assert res["watch_stock_count"] >= 0
    assert len(res["funds_breakdown"]) == 2

    # Breakdown item checks
    for b in res["funds_breakdown"]:
        assert "fund_code" in b
        assert "weight_pct" in b
        assert "is_ashare_equity" in b
        assert "penetration_risk_score" in b
        assert "diagnosis_summary" in b


# ==============================================================================
# 2. 非 A 股权益资产免疫机制实证 (Non-Equity Asset Immunity Verification)
# ==============================================================================

@pytest.mark.parametrize("code,desc", [
    ("002351", "纯债固收"),
    ("000216", "黄金ETF联接"),
    ("050025", "标普500全球QDII")
])
def test_non_ashare_immunity_mechanism(code, desc):
    """实证非 A 股资产免受 A 股财务与质押口径误伤"""
    pm = PortfolioManager(db_path=":memory:")
    res = pm.screen_fund_look_through_risk(code)
    assert res["is_ashare_equity"] is False, f"{code} ({desc}) should be non-ashare"
    assert res["penetration_risk_score"] == 0.0, f"{code} risk score must be 0.0"
    assert res["risk_level"] == "Safe"
    assert res["risk_badge"] == "🟢 健康"
    assert res["danger_count"] == 0
    assert res["watch_count"] == 0
    assert "非A股权益" in res["diagnosis_summary"] or "免疫" in res["diagnosis_summary"]


def test_custom_non_ashare_fund_name_heuristic():
    """启发式测试：未收录在静态集合但名称带'纯债'/'黄金'的自定义外部基金"""
    pm = PortfolioManager(db_path=":memory:")
    # 模拟外部基金
    FUND_LOOK_THROUGH_DATA["888001"] = {
        "fund_name": "国泰惠丰纯债债券C",
        "top_stocks": ["21国债01", "进出2001", "特国2401"]
    }
    res = pm.screen_fund_look_through_risk("888001")
    assert res["is_ashare_equity"] is False
    assert res["penetration_risk_score"] == 0.0
    assert res["risk_level"] == "Safe"
    assert res["risk_badge"] == "🟢 健康"


# ==============================================================================
# 3. 组合穿透风险四大配置场景实证 (4 Portfolio Configurations Stress Test)
# ==============================================================================

def test_scenario_empty_portfolio():
    """场景 1: 空组合 (Empty Portfolio) — 零除异常防御"""
    pm = PortfolioManager(db_path=":memory:")
    pm.holdings = {}
    pm.available_cash = 0.0

    res = pm.calculate_portfolio_penetration_risk()
    assert res["portfolio_risk_index"] == 0.0
    assert res["risk_level"] == "Safe"
    assert res["risk_badge"] == "🟢 健康"
    assert res["danger_stock_count"] == 0
    assert res["watch_stock_count"] == 0
    assert res["high_risk_reasons"] == []
    assert res["funds_breakdown"] == []


def test_scenario_cash_only_portfolio():
    """场景 1b: 纯现金组合 (Cash Only, 100,000 cash, 0 fund holdings)"""
    pm = PortfolioManager(db_path=":memory:")
    pm.holdings = {}
    pm.available_cash = 100000.0

    res = pm.calculate_portfolio_penetration_risk()
    assert res["portfolio_risk_index"] == 0.0
    assert res["risk_level"] == "Safe"
    assert res["risk_badge"] == "🟢 健康"
    assert len(res["funds_breakdown"]) == 0


def test_scenario_liquidated_zero_mv_holdings():
    """场景 1c: 存在已被清仓（市值=0）的沉淀记录"""
    pm = PortfolioManager(db_path=":memory:")
    pm.takeover_mode_a([
        {"fund_code": "100032", "amount": 50000.0, "nav": 1.0}
    ], available_cash=0.0)
    # 模拟清仓 100032
    pm.holdings["100032"].shares = 0.0
    pm.holdings["100032"].market_value = 0.0

    res = pm.calculate_portfolio_penetration_risk()
    assert res["portfolio_risk_index"] == 0.0
    assert res["risk_level"] == "Safe"
    assert len(res["funds_breakdown"]) == 0


def test_scenario_single_fund_equity():
    """场景 2: 单一权益基金 (100% 100032)"""
    pm = PortfolioManager(db_path=":memory:")
    pm.takeover_mode_a([
        {"fund_code": "100032", "amount": 88000.0, "nav": 1.0}
    ], available_cash=12000.0)

    res = pm.calculate_portfolio_penetration_risk()
    fund_res = pm.screen_fund_look_through_risk("100032")
    assert res["portfolio_risk_index"] == fund_res["penetration_risk_score"]
    assert res["risk_level"] == fund_res["risk_level"]
    assert res["risk_badge"] == fund_res["risk_badge"]
    assert len(res["funds_breakdown"]) == 1
    assert res["funds_breakdown"][0]["weight_pct"] == 100.0


def test_scenario_single_fund_bond():
    """场景 2b: 单一纯债基金 (100% 002351)"""
    pm = PortfolioManager(db_path=":memory:")
    pm.takeover_mode_a([
        {"fund_code": "002351", "amount": 100000.0, "nav": 1.0}
    ], available_cash=0.0)

    res = pm.calculate_portfolio_penetration_risk()
    assert res["portfolio_risk_index"] == 0.0
    assert res["risk_level"] == "Safe"
    assert res["risk_badge"] == "🟢 健康"
    assert res["funds_breakdown"][0]["is_ashare_equity"] is False


def test_scenario_multi_fund_balanced():
    """场景 3: 多基金均衡组合 (50% 100032 + 50% 002351)"""
    pm = PortfolioManager(db_path=":memory:")
    pm.takeover_mode_a([
        {"fund_code": "100032", "amount": 50000.0, "nav": 1.0},
        {"fund_code": "002351", "amount": 50000.0, "nav": 1.0}
    ], available_cash=0.0)

    res = pm.calculate_portfolio_penetration_risk()
    fund_res = pm.screen_fund_look_through_risk("100032")
    expected_risk = round(fund_res["penetration_risk_score"] * 0.5, 2)
    assert res["portfolio_risk_index"] == expected_risk
    assert res["risk_level"] == "Safe"
    assert res["risk_badge"] == "🟢 健康"
    weights = [b["weight_pct"] for b in res["funds_breakdown"]]
    assert weights == [50.0, 50.0]


def test_scenario_100pct_high_risk_configuration():
    """场景 4: 100% 高危风险组合 (Danger Stock Count >= 2, 强制触发 🔴 预警)"""
    pm = PortfolioManager(db_path=":memory:")

    # 构造两个高危基金
    FUND_LOOK_THROUGH_DATA["999901"] = {
        "fund_name": "极度高危财务造假测试基A",
        "top_stocks": ["万科A", "ST三房", "ST雪发"]
    }
    FUND_LOOK_THROUGH_DATA["999902"] = {
        "fund_name": "极度高危限售解禁测试基B",
        "top_stocks": ["中芯国际", "海光信息", "寒武纪"]
    }

    pm.takeover_mode_a([
        {"fund_code": "999901", "amount": 50000.0, "nav": 1.0},
        {"fund_code": "999902", "amount": 50000.0, "nav": 1.0}
    ], available_cash=0.0)

    res = pm.calculate_portfolio_penetration_risk()
    assert res["risk_level"] == "Danger"
    assert res["risk_badge"] == "🔴 预警"
    assert res["danger_stock_count"] >= 2
    assert len(res["high_risk_reasons"]) >= 2
    # 确认包含万科A与中芯国际
    reasons_text = " ".join(res["high_risk_reasons"])
    assert "万科A" in reasons_text
    assert "中芯国际" in reasons_text


# ==============================================================================
# 4. 去重与边界压力实证 (Deduplication & Edge Cases)
# ==============================================================================

def test_deduplication_across_overlapping_funds():
    """实证多个基金交叉持有相同高危重仓股时，不重复统计标的数"""
    pm = PortfolioManager(db_path=":memory:")

    # 基金 1 和 基金 2 均重仓 万科A (Danger)
    FUND_LOOK_THROUGH_DATA["999903"] = {
        "fund_name": "万科重仓测试基1",
        "top_stocks": ["万科A", "贵州茅台"]
    }
    FUND_LOOK_THROUGH_DATA["999904"] = {
        "fund_name": "万科重仓测试基2",
        "top_stocks": ["万科A", "招商银行"]
    }

    pm.takeover_mode_a([
        {"fund_code": "999903", "amount": 50000.0, "nav": 1.0},
        {"fund_code": "999904", "amount": 50000.0, "nav": 1.0}
    ], available_cash=0.0)

    res = pm.calculate_portfolio_penetration_risk()
    # 万科A 虽在两只基金中均出现，但在全组合中应去重为 1 只 Danger 股票
    assert res["danger_stock_count"] == 1
    # 当 danger_stock_count == 1 时，评级应为 Watch 🟡
    assert res["risk_level"] == "Watch"
    assert res["risk_badge"] == "🟡 关注"


def test_unknown_stock_and_graceful_handling():
    """实证未知股票/无财报数据的异常代码不引发崩溃"""
    pm = PortfolioManager(db_path=":memory:")
    FUND_LOOK_THROUGH_DATA["999905"] = {
        "fund_name": "未知标的测试基",
        "top_stocks": ["未知火星公司XYZ", "999999", "   "]
    }

    res = pm.screen_fund_look_through_risk("999905")
    assert isinstance(res, dict)
    assert res["fund_code"] == "999905"
    assert len(res["top_stocks_screen"]) == 3
    # 默认评分不崩溃
    for s in res["top_stocks_screen"]:
        assert 0.0 <= s["stock_score"] <= 100.0


def test_cache_immutability():
    """实证返回对象被外部修改时，底层缓存不被污染 (deepcopy 防御)"""
    pm = PortfolioManager(db_path=":memory:")
    res1 = pm.screen_fund_look_through_risk("100032")
    orig_name = res1["top_stocks_screen"][0]["stock_name"]

    # 外部恶意篡改返回字典
    res1["top_stocks_screen"][0]["stock_name"] = "MALICIOUS_OVERWRITE"
    res1["top_stocks_screen"][0]["stock_score"] = -999.0

    # 第二次获取
    res2 = pm.screen_fund_look_through_risk("100032")
    assert res2["top_stocks_screen"][0]["stock_name"] == orig_name
    assert res2["top_stocks_screen"][0]["stock_score"] >= 0.0


def test_performance_benchmark():
    """压测组合穿透计算性能：验证在线单次响应稳健，且离线/湖仓缓存模式下达毫秒级响应"""
    import time
    from unittest.mock import patch
    pm = PortfolioManager(db_path=":memory:")
    pm.takeover_mode_a([
        {"fund_code": "100032", "amount": 40000.0, "nav": 1.0},
        {"fund_code": "011613", "amount": 30000.0, "nav": 1.0},
        {"fund_code": "002351", "amount": 30000.0, "nav": 1.0}
    ], available_cash=0.0)

    # 1. 验证离线/湖仓纯本地模式：30 次均值应低于 50ms
    with patch("requests.get", side_effect=Exception("Offline")):
        t0 = time.perf_counter()
        for _ in range(30):
            _ = pm.calculate_portfolio_penetration_risk()
        elapsed_offline = time.perf_counter() - t0
        avg_offline_ms = (elapsed_offline / 30) * 1000
        assert avg_offline_ms < 50.0, f"Offline execution too slow: {avg_offline_ms:.2f} ms"

    # 2. 验证在线模式单次组合穿透延时处于合理可用区间 (< 2000ms)
    t1 = time.perf_counter()
    _ = pm.calculate_portfolio_penetration_risk()
    online_ms = (time.perf_counter() - t1) * 1000
    assert online_ms < 2000.0, f"Online execution too slow: {online_ms:.2f} ms"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
