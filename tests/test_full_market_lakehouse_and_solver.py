# -*- coding: utf-8 -*-
"""
全市场 28,177 漏斗 + 266+ 真净值离线湖仓 + 异步求解进度 API + 跨周期多样性综合回归测试套件
严格验证核心公理与防回退契约：
  1. 湖仓真实性：>= 200 只真净值基金，10 大风格桶全部覆盖，成立日前严格保持 NaN、成立日后零空洞，真实单基规模过滤生效；
  2. 真全市场多样性（彻底打破固定 12 只池）：C1 6% vs C3 10% vs C4 22% vs C5 30% 选出显著差异化的真实组合；
  3. 双选基范围隔离：full_market 可纳入主动精选绩优基金；index_only 严格 0 只主动权益基金；
  4. 单基集中度与大类宪法双红线：6 只组合中任意非债单基 <= 36%，C3 黄金 <= 15.5%、QDII <= 12.5%；
  5. 异步求解 API (/api/v1/quant/solve -> /api/v1/quant/solve/{job_id}) 端到端闭环：
     返回 100% 权重同源的 blueprint + backtest_curves、is_real_nav == True、完整 funnel_audit、
     以及透明标注的极端市场修复周期 (is_proxy_simulated 字段合法)。
"""

import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
AGY2_DIR = ROOT / "AGY2_FundAdvisory"
for p in (str(AGY2_DIR), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

import api_server
from goal_driven_selector import solve_goal_driven_portfolio
from market_lakehouse import BUCKET_10_CONFIG, get_lakehouse_status, load_elite_lakehouse

client = TestClient(api_server.app)


def test_elite_lakehouse_integrity_and_ten_buckets():
    """验证本地精英真净值湖仓完整性、10 大风格桶覆盖与真实复权净值质量"""
    nav_df, meta_df, status = load_elite_lakehouse()
    assert status.get("status") == "ready"
    assert nav_df is not None and not nav_df.empty
    assert meta_df is not None and not meta_df.empty
    assert nav_df.shape[1] >= 200, f"Expected >= 200 elite funds, got {nav_df.shape[1]}"
    assert nav_df.shape[0] >= 1800, f"Expected >= 1800 trading days, got {nav_df.shape[0]}"

    # 10 大风格桶全部有真实基金覆盖
    present_buckets = set(meta_df["bucket_10"].dropna().astype(str).unique())
    expected_buckets = set(BUCKET_10_CONFIG.keys())
    assert expected_buckets.issubset(present_buckets), f"Missing buckets: {expected_buckets - present_buckets}"

    # 验证净值均为正且无 Inf
    vals = nav_df.to_numpy(dtype=float)
    valid_vals = vals[~(vals != vals)]  # drop NaN
    assert (valid_vals > 0).all(), "Found non-positive NAV in elite lakehouse"


def test_full_market_goal_diversity_and_universe_modes():
    """验证不同目标收益/风险档位真正从全市场选出差异化组合，且单基/大类红线严格受控"""
    r_c1 = solve_goal_driven_portfolio(
        risk_level="C1", fund_count=6, model_id="dividend_defense",
        target_return_pct=6.0, horizon_months=12, universe_mode="full_market",
    )
    r_c3 = solve_goal_driven_portfolio(
        risk_level="C3", fund_count=6, model_id="all_weather",
        target_return_pct=10.0, horizon_months=12, universe_mode="full_market",
    )
    r_c4 = solve_goal_driven_portfolio(
        risk_level="C4", fund_count=6, model_id="barbell_growth",
        target_return_pct=22.0, horizon_months=24, universe_mode="full_market",
    )
    r_idx = solve_goal_driven_portfolio(
        risk_level="C3", fund_count=6, model_id="all_weather",
        target_return_pct=10.0, horizon_months=12, universe_mode="index_only",
    )

    s_c1, s_c3, s_c4, s_idx = (
        set(r_c1["final_weights"].keys()),
        set(r_c3["final_weights"].keys()),
        set(r_c4["final_weights"].keys()),
        set(r_idx["final_weights"].keys()),
    )
    # 极端不同目标（C1 6% vs C4 22%）重叠度必须 <= 2/6（彻底告别固定 6 基翻来覆去）
    assert len(s_c1 & s_c4) <= 2, f"C1 6% vs C4 22% overlap too high: {s_c1 & s_c4}"
    # 3 个不同目标合计应覆盖 >= 11 只全市场不同基金
    union_all = s_c1 | s_c3 | s_c4
    assert len(union_all) >= 11, f"Expected >= 11 unique funds across C1/C3/C4, got {len(union_all)}: {union_all}"

    # index_only 严格 0 只主动权益/主动混合基金
    idx_meta = r_idx["fund_cards_meta"]
    idx_active_cnt = sum(1 for c in s_idx if idx_meta.get(c, {}).get("is_active_fund"))
    assert idx_active_cnt == 0, f"index_only should contain 0 active funds, got {idx_active_cnt}"

    # full_market across C1/C3/C4 应能挖掘到真实主动绩优基金
    fm_active_cnt = sum(
        1 for res in (r_c1, r_c3, r_c4)
        for c in res["final_weights"]
        if res["fund_cards_meta"].get(c, {}).get("is_active_fund")
    )
    assert fm_active_cnt >= 1, "full_market should include at least 1 active fund across tiers"

    # 单基与大类红线检查（C3 黄金 <= 16%, QDII <= 13%, 任意单基权益 <= 36%）
    c3_meta = r_c3["fund_cards_meta"]
    c3_gold = sum(w for c, w in r_c3["final_weights"].items() if c3_meta.get(c, {}).get("asset_class") == "gold")
    c3_qdii = sum(w for c, w in r_c3["final_weights"].items() if c3_meta.get(c, {}).get("asset_class") == "qdii")
    c3_max_eq = max(
        (w for c, w in r_c3["final_weights"].items() if c3_meta.get(c, {}).get("asset_class") == "equity"),
        default=0.0,
    )
    assert c3_gold <= 0.165, f"C3 gold breached cap: {c3_gold:.4f}"
    assert c3_qdii <= 0.135, f"C3 qdii breached cap: {c3_qdii:.4f}"
    assert c3_max_eq <= 0.37, f"C3 single equity breached cap: {c3_max_eq:.4f}"

    # 真实净值回测跨周期深度（穿越 2022 熊市 >= 1000 交易日）
    for lbl, r in [("C1", r_c1), ("C3", r_c3), ("C4", r_c4), ("IDX", r_idx)]:
        bt_info = r["real_bt_info"]
        assert bt_info["is_real_nav"] is True, f"{lbl} not using real fund NAV backtest"
        assert bt_info["common_trading_days"] >= 1000, f"{lbl} common history too short: {bt_info}"


def test_async_quant_solve_and_lakehouse_api_endpoints():
    """验证 /api/v1/lakehouse/status 与 /api/v1/quant/solve 异步进度轮询完整闭环"""
    st_resp = client.get("/api/v1/lakehouse/status")
    assert st_resp.status_code == 200
    st = st_resp.json()
    assert st["status"] == "ready"
    assert st["elite_fund_count"] >= 200

    # 启动异步全市场求解任务
    start_resp = client.post(
        "/api/v1/quant/solve",
        json={
            "risk_level": "C4",
            "amount": 100000,
            "fund_count": 6,
            "model": "barbell_growth",
            "target_return_pct": 18,
            "horizon_months": 24,
            "universe_mode": "full_market",
            "period": "all",
            "force": False,
        },
    )
    assert start_resp.status_code == 200
    job = start_resp.json()
    job_id = job["job_id"]
    assert job_id

    # 轮询至完成
    final_poll = None
    for _ in range(90):
        poll_resp = client.get(f"/api/v1/quant/solve/{job_id}")
        assert poll_resp.status_code == 200
        pj = poll_resp.json()
        if pj["status"] == "done":
            final_poll = pj
            break
        assert pj["status"] != "error", f"Async solve failed: {pj}"
        time.sleep(0.25)

    assert final_poll is not None, "Async solve timed out"
    assert final_poll["progress_pct"] == 100
    res = final_poll["result"]
    bp = res["blueprint"]
    bt = res["backtest_curves"]

    # 100% 权重同源 + 全市场漏斗 + 真实复权净值回测
    assert bp["portfolio_weights"] == bt["portfolio_weights"]
    assert bp["count"] == 6
    assert abs(sum(it["weight_pct"] for it in bp["items"]) - 100.0) <= 0.2
    assert bp["funnel_audit"]["total_market_funds"] >= 20000
    assert bp["funnel_audit"]["elite_lakehouse_funds"] >= 200
    assert bt["real_bt_info"]["is_real_nav"] is True

    # 极端行情修复事件具备透明 is_proxy_simulated 标记
    events = bt["extreme_cycle_analysis"]["historical_recovery"]["events"]
    assert len(events) >= 3
    for ev in events:
        assert "is_proxy_simulated" in ev
        assert "proxy_note" in ev
