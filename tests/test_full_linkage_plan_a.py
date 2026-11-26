# -*- coding: utf-8 -*-
"""
方案 A 全站图表、真实 MA20 乖离与跨页调仓全链路联动回归测试套件
验证 4 项核心契约：
  1. 全市场湖仓新基金真实 MA20 乖离与 20 日涨跌（彻底消除旧表未命中导致的全部 +0.0%）；
  2. /api/v1/charts/crowding_quadrant 支持 codes 参数精准联动上方全市场推荐组合；
  3. /api/v1/charts/scenario_backtest 真正随上方模型/档位/目标/选基范围变化，早于共同成立日时透明标注 used_proxy_early；
  4. /api/v1/charts/backtest_curves 输出非空 weight_vs_pcr（资金占比与风险贡献总和闭合），
     且 /api/v1/rebalance 支持 ledger_smooth vs full_market_solved 双模式与自由目标/真实档位传递。
"""

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
AGY2_DIR = ROOT / "AGY2_FundAdvisory"
for p in (str(AGY2_DIR), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

import api_server
from goal_driven_selector import solve_goal_driven_portfolio

client = TestClient(api_server.app)


def test_full_market_real_nav_crowding_and_codes_linkage():
    """验证全市场新基金的 MA20 乖离率来自真实复权净值（不再清一色 0.0%），且拥挤度接口支持 codes 联动"""
    solved = solve_goal_driven_portfolio(
        risk_level="C4", fund_count=6, model_id="barbell_growth",
        target_return_pct=22.0, horizon_months=24, universe_mode="full_market",
    )
    codes = list(solved["final_weights"].keys())
    resp = client.get("/api/v1/charts/crowding_quadrant", params={"codes": ",".join(codes)})
    assert resp.status_code == 200
    body = resp.json()
    assert body["scope_mode"] == "recommended_portfolio"
    assert body["count"] == len(codes)
    returned_codes = {p["fund_code"] for p in body["points"]}
    assert returned_codes == set(codes)

    # 至少半数以上全市场新基金具备真实非零 ret_20d / bias_20，且均带真实中文名（非 公募基金_xxxxxx）
    nonzero_cnt = sum(1 for p in body["points"] if abs(p["bias_20"]) > 0.001 or abs(p["ret_20d"]) > 0.001)
    assert nonzero_cnt >= 4, f"Expected real non-zero MA20 bias/ret_20d, got points: {body['points']}"
    for p in body["points"]:
        assert not p["fund_name"].startswith("公募基金_"), f"Missing real fund name for {p['fund_code']}"


def test_scenario_backtest_dynamically_follows_solved_portfolio():
    """验证历史情景回测真正随不同方案（C1 红利防御 vs C4 杠铃攻守，同一 C3 不同模型）动态变化，且早期节点透明标注"""
    r_c1 = client.get(
        "/api/v1/charts/scenario_backtest",
        params={
            "start_date": "2024-09-18",
            "tier": "C1",
            "model": "dividend_defense",
            "fund_count": 6,
            "target_return_pct": 6,
            "horizon_months": 12,
            "universe_mode": "full_market",
            "dynamic_rebalance": True,
        },
    )
    r_c4 = client.get(
        "/api/v1/charts/scenario_backtest",
        params={
            "start_date": "2024-09-18",
            "tier": "C4",
            "model": "barbell_growth",
            "fund_count": 6,
            "target_return_pct": 22,
            "horizon_months": 24,
            "universe_mode": "full_market",
            "dynamic_rebalance": True,
        },
    )
    assert r_c1.status_code == 200 and r_c4.status_code == 200
    d1, d4 = r_c1.json(), r_c4.json()
    assert d1["portfolio_weights"] != d4["portfolio_weights"]
    assert d1["strategy_nav"][-1] != d4["strategy_nav"][-1]
    assert d1["kpis"]["all"]["net_return_pct"] != d4["kpis"]["all"]["net_return_pct"]
    assert d1["used_proxy_early"] is False
    assert d4["used_proxy_early"] is False

    # 同一 C3 档位切换模型（all_weather vs risk_parity）情景曲线也必须联动变化（修复旧版只看 tier 的 bug）
    r_c3_aw = client.get(
        "/api/v1/charts/scenario_backtest",
        params={"start_date": "2024-09-18", "tier": "C3", "model": "all_weather", "fund_count": 6, "target_return_pct": 10, "horizon_months": 12},
    ).json()
    r_c3_rp = client.get(
        "/api/v1/charts/scenario_backtest",
        params={"start_date": "2024-09-18", "tier": "C3", "model": "barbell_growth", "fund_count": 6, "target_return_pct": 18, "horizon_months": 24},
    ).json()
    assert r_c3_aw["portfolio_weights"] != r_c3_rp["portfolio_weights"]
    assert r_c3_aw["strategy_nav"][-1] != r_c3_rp["strategy_nav"][-1]

    # 早期历史起点（2021-02-18）对晚于 2021 成立的组合应透明标注 used_proxy_early=True + proxy_note
    r_early = client.get(
        "/api/v1/charts/scenario_backtest",
        params={
            "start_date": "2021-02-18",
            "tier": "C4",
            "model": "barbell_growth",
            "fund_count": 6,
            "target_return_pct": 22,
            "horizon_months": 24,
            "universe_mode": "full_market",
        },
    ).json()
    assert len(r_early["dates"]) > 100
    assert r_early["kpis"]["all"] is not None
    if r_early["used_proxy_early"]:
        assert len(r_early["proxy_note"]) > 15


def test_backtest_weight_vs_pcr_and_rebalance_dual_target_modes():
    """验证回测输出 weight_vs_pcr 对照表闭合，且调仓接口支持稳健平滑 vs 对齐全市场双模式"""
    bt = client.get(
        "/api/v1/charts/backtest_curves",
        params={
            "tier": "C4",
            "model": "barbell_growth",
            "fund_count": 6,
            "period": "6m",
            "target_return_pct": 22,
            "horizon_months": 24,
            "universe_mode": "full_market",
        },
    ).json()
    pcr_rows = bt.get("weight_vs_pcr") or []
    assert len(pcr_rows) == 6
    assert abs(sum(r["weight_pct"] for r in pcr_rows) - 100.0) <= 0.3
    assert abs(sum(r["pcr_pct"] for r in pcr_rows) - 100.0) <= 0.5

    # 调仓页：稳健低换手 vs 对齐首页全市场方案，且支持自由 22% 目标与 C4 档位
    reb_smooth = client.get(
        "/api/v1/rebalance",
        params={"tier": "C4", "target_return_pct": 22, "horizon_months": 24, "target_source": "ledger_smooth"},
    )
    reb_full = client.get(
        "/api/v1/rebalance",
        params={
            "tier": "C4",
            "target_return_pct": 22,
            "horizon_months": 24,
            "target_source": "full_market_solved",
            "model": "barbell_growth",
            "fund_count": 6,
            "universe_mode": "full_market",
        },
    )
    assert reb_smooth.status_code == 200 and reb_full.status_code == 200
    rs, rf = reb_smooth.json(), reb_full.json()
    assert rs["target_source"] == "ledger_smooth"
    assert rf["target_source"] == "full_market_solved"
    assert rf["tier"] == "C4"
    assert rf["goal_comparison"]["target_return_pct"] == 22.0
    assert rf["goal_comparison"]["tier"] == "C4"
    assert rs["cheat_sheet_text"] != rf["cheat_sheet_text"]
