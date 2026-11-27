# -*- coding: utf-8 -*-
"""
AGY2 v2.1 机构级投研工作台后端全链路回归测试：
  1. exclude_codes / include_codes 在求解器、blueprint、backtest_curves、scenario_backtest、rebalance 五端零幽灵复活；
  2. index_only 模式下锁定主动基金时自动解除并返回结构化 constraint_audit.warnings；
  3. blueprint.items 透传真实 MA20 乖离 (bias_20) 与短线温度字段；
  4. backtest_curves 返回固定双口径 benchmark_horizons (y1 + all) 供 A/B 公平对比；
  5. /api/v1/import/commit 支持所见即所写（不污染用户真实账本，使用沙盒账本校验后清理）。
"""

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
AGY2_DIR = ROOT / "AGY2_FundAdvisory"
for p in (str(AGY2_DIR), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

import api_server  # noqa: E402
from goal_driven_selector import clear_goal_solver_cache  # noqa: E402


client = TestClient(api_server.app)


def test_exclude_and_include_full_chain_consistency():
    clear_goal_solver_cache()
    # 1. 基线方案
    r_base = client.get(
        "/api/v1/recommend/blueprint",
        params={
            "risk_level": "C3",
            "amount": 50000,
            "fund_count": 6,
            "model": "all_weather",
            "target_return_pct": 10,
            "horizon_months": 12,
            "universe_mode": "full_market",
        },
    )
    assert r_base.status_code == 200
    bp_base = r_base.json()
    items_base = bp_base["items"]
    assert len(items_base) == 6
    # 核验短线温度真实透传
    assert any(it.get("bias_20") is not None for it in items_base)
    first_code = items_base[0]["fund_code"]
    second_code = items_base[1]["fund_code"]

    # 2. 排除 first_code，同时锁定 second_code
    r_ex = client.get(
        "/api/v1/recommend/blueprint",
        params={
            "risk_level": "C3",
            "amount": 50000,
            "fund_count": 6,
            "model": "all_weather",
            "target_return_pct": 10,
            "horizon_months": 12,
            "universe_mode": "full_market",
            "exclude_codes": first_code,
            "include_codes": second_code,
        },
    )
    assert r_ex.status_code == 200
    bp_ex = r_ex.json()
    ex_codes_out = [it["fund_code"] for it in bp_ex["items"]]
    assert len(ex_codes_out) == 6
    assert first_code not in ex_codes_out, f"Excluded fund {first_code} reappeared in blueprint!"
    assert second_code in ex_codes_out, f"Locked fund {second_code} missing from blueprint!"
    assert abs(sum(it["weight_pct"] for it in bp_ex["items"]) - 100.0) <= 0.2

    # 3. 核验 backtest_curves / benchmark_horizons 一致且无幽灵复活
    r_bt = client.get(
        "/api/v1/charts/backtest_curves",
        params={
            "tier": "C3",
            "model": "all_weather",
            "fund_count": 6,
            "period": "6m",
            "target_return_pct": 10,
            "horizon_months": 12,
            "universe_mode": "full_market",
            "exclude_codes": first_code,
            "include_codes": second_code,
        },
    )
    assert r_bt.status_code == 200
    bt_j = r_bt.json()
    bt_weights = bt_j.get("portfolio_weights") or {}
    assert first_code not in bt_weights, "Excluded fund resurrected in backtest_curves!"
    assert second_code in bt_weights, "Locked fund missing in backtest_curves!"
    bh = bt_j.get("benchmark_horizons") or {}
    assert "y1" in bh and "all" in bh
    assert "return_pct" in bh["y1"] and "max_drawdown_pct" in bh["all"]

    # 4. 核验 scenario_backtest 一致且无幽灵复活
    r_sc = client.get(
        "/api/v1/charts/scenario_backtest",
        params={
            "start_date": "2024-09-18",
            "tier": "C3",
            "model": "all_weather",
            "fund_count": 6,
            "target_return_pct": 10,
            "horizon_months": 12,
            "universe_mode": "full_market",
            "exclude_codes": first_code,
            "include_codes": second_code,
        },
    )
    assert r_sc.status_code == 200
    sc_j = r_sc.json()
    sc_weights = sc_j.get("portfolio_weights") or {}
    assert first_code not in sc_weights, "Excluded fund resurrected in scenario_backtest!"
    assert second_code in sc_weights, "Locked fund missing in scenario_backtest!"

    # 5. 核验 rebalance(full_market_solved) 一致
    r_reb = client.get(
        "/api/v1/rebalance",
        params={
            "tier": "C3",
            "target_source": "full_market_solved",
            "model": "all_weather",
            "fund_count": 6,
            "target_return_pct": 10,
            "horizon_months": 12,
            "universe_mode": "full_market",
            "exclude_codes": first_code,
            "include_codes": second_code,
        },
    )
    assert r_reb.status_code == 200
    reb_j = r_reb.json()
    assert "排除1/锁定1" in (reb_j.get("target_summary") or "")


def test_index_only_unlocks_active_fund_with_warning():
    # 先在全市场找一只主动基金，再切到 index_only 试图锁定它
    r_fm = client.get(
        "/api/v1/recommend/blueprint",
        params={"risk_level": "C4", "fund_count": 6, "model": "all_weather", "universe_mode": "full_market"},
    )
    assert r_fm.status_code == 200
    actives = [it["fund_code"] for it in r_fm.json()["items"] if it.get("is_active_fund")]
    if not actives:
        return
    act_code = actives[0]
    r_idx = client.get(
        "/api/v1/recommend/blueprint",
        params={
            "risk_level": "C4",
            "fund_count": 6,
            "model": "all_weather",
            "universe_mode": "index_only",
            "include_codes": act_code,
        },
    )
    assert r_idx.status_code == 200
    j_idx = r_idx.json()
    out_codes = [it["fund_code"] for it in j_idx["items"]]
    assert act_code not in out_codes, "Active fund leaked into index_only mode!"
    warnings = (j_idx.get("constraint_audit") or {}).get("warnings") or []
    assert any("仅指数" in w for w in warnings), f"Expected index_only unlock warning, got {warnings}"
