"""阶段三增量测试：全市场胜率最优选基引擎（winrate_engine / market_screener / portfolio_optimizer / cache_manager）"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from winrate_engine import WinRateEngine, HOLDING_PERIODS, _get_redemption_fee  # noqa: E402
from market_screener import MarketScreener, BUCKET_MAP, _assign_bucket  # noqa: E402
from portfolio_optimizer import WinRateOptimizer, DEFAULT_CONSTRAINTS  # noqa: E402
import cache_manager  # noqa: E402
from cache_manager import SmartCacheManager  # noqa: E402


def _synthetic_nav(n=1500, annual=0.10, vol=0.08, seed=0):
    rng = np.random.default_rng(seed)
    mu = (1 + annual) ** (1 / 250) - 1
    rets = rng.normal(mu, vol / np.sqrt(250), n)
    idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=n)
    return pd.Series(np.cumprod(1 + rets), index=idx)


# ─── WinRateEngine ─────────────────────────────────────────────

def test_steady_growth_high_winrate():
    nav = _synthetic_nav(annual=0.10, vol=0.03)
    r = WinRateEngine.rolling_target_winrate(nav, 500, 0.08)
    assert r["win_rate"] > 0.5
    assert r["no_loss_rate"] >= r["win_rate"]
    assert r["total_windows"] == len(nav) - 500


def test_losing_fund_low_winrate():
    nav = _synthetic_nav(annual=-0.10, vol=0.03, seed=1)
    r = WinRateEngine.rolling_target_winrate(nav, 250, 0.05)
    assert r["win_rate"] < 0.1


def test_insufficient_data_returns_zero():
    nav = _synthetic_nav(n=300)
    r = WinRateEngine.rolling_target_winrate(nav, HOLDING_PERIODS["long"]["trading_days"], 0.08)
    assert r["win_rate"] == 0.0 and r["total_windows"] == 0


def test_nan_and_flat_nav_does_not_crash():
    nav = _synthetic_nav(n=600)
    nav.iloc[100:110] = np.nan
    r = WinRateEngine.rolling_target_winrate(nav.dropna(), 125, 0.05)
    assert 0.0 <= r["win_rate"] <= 1.0
    flat = pd.Series(np.ones(600))
    r2 = WinRateEngine.rolling_target_winrate(flat, 125, 0.05)
    assert r2["win_rate"] == 0.0  # 摩擦成本下平盘不可能达标


def test_friction_costs():
    # 7 天内惩罚性赎回费 1.5%
    assert _get_redemption_fee(3, "A") == pytest.approx(0.015)
    # 平盘持有 100 天：A 类扣申购费+赎回费，必为负
    a = WinRateEngine.compute_friction_adjusted_return(1.0, 1.0, 100, "A")
    c = WinRateEngine.compute_friction_adjusted_return(1.0, 1.0, 100, "C")
    assert a < 0 and c < 0
    # 长期持有（3年）：C 类累计销售服务费应高于 A 类一次性申购费
    a_long = WinRateEngine.compute_friction_adjusted_return(1.0, 1.5, 1100, "A")
    c_long = WinRateEngine.compute_friction_adjusted_return(1.0, 1.5, 1100, "C")
    assert a_long > c_long
    assert WinRateEngine.compute_friction_adjusted_return(0.0, 1.0, 100) == 0.0


def test_monte_carlo_distribution_sane():
    nav = _synthetic_nav(annual=0.10, vol=0.10, seed=3)
    mc = WinRateEngine.monte_carlo_simulation(nav, 250, 0.08, n_paths=2000)
    # 目标 8% > 0：达标路径必为不亏损路径的子集
    assert 0.0 <= mc["prob_reach_target"] <= mc["prob_no_loss"] <= 1.0
    assert 0.0 < mc["prob_reach_target"] < 1.0  # 波动 10% 下不应退化为 0/1
    lo90, hi90 = mc["ci_90"]
    lo95, hi95 = mc["ci_95"]
    assert lo95 <= lo90 <= mc["median_return"] <= hi90 <= hi95
    # 同 seed 结果可复现
    mc2 = WinRateEngine.monte_carlo_simulation(nav, 250, 0.08, n_paths=2000)
    assert mc["prob_reach_target"] == mc2["prob_reach_target"]


# ─── MarketScreener ────────────────────────────────────────────

def test_bucket_map_covers_catalog_types():
    cat_path = MarketScreener.CATALOG_PATH
    if not Path(cat_path).exists():
        pytest.skip("fund_catalog.parquet 不存在")
    types = pd.read_parquet(cat_path)["fund_type"].dropna().unique()
    uncovered = [t for t in types if _assign_bucket(t) == "other"]
    print("未覆盖 fund_type:", uncovered)
    cat = pd.read_parquet(cat_path)
    share_other = cat["fund_type"].map(_assign_bucket).eq("other").mean()
    assert share_other < 0.05, f"归入 other 的基金占比过高: {share_other:.2%} {uncovered}"


def test_bucket_map_no_duplicate_types():
    all_types = [t for ts in BUCKET_MAP.values() for t in ts]
    assert len(all_types) == len(set(all_types))


def test_ac_dedup_keeps_a_and_records_c_pair():
    df = pd.DataFrame({
        "fund_code": ["000001", "000002", "000003", "000004"],
        "fund_name": ["易方达稳健混合A", "易方达稳健混合C", "某某纯债C", "独立股票"],
    })
    df["share_class"] = df["fund_name"].apply(MarketScreener._detect_share_class)
    df["ac_pair_code"] = ""
    out = MarketScreener._deduplicate_ac_classes(df)
    codes = set(out["fund_code"])
    assert "000001" in codes and "000002" not in codes
    assert out.loc[out["fund_code"] == "000001", "ac_pair_code"].iloc[0] == "000002"
    assert {"000003", "000004"} <= codes  # 无配对的 C 类与独立基金保留


# ─── WinRateOptimizer ──────────────────────────────────────────

@pytest.fixture(scope="module")
def opt_result():
    buckets = ["equity", "bond", "overseas", "commodity", "fof"]
    navs, info = {}, []
    for i in range(12):
        code = f"9{i:05d}"
        b = buckets[i % len(buckets)]
        navs[code] = _synthetic_nav(n=900, annual=0.04 + 0.01 * i, vol=0.04 + 0.01 * (i % 4), seed=100 + i)
        info.append({"fund_code": code, "fund_name": f"测试基金{i}", "bucket": b, "ac_pair_code": ""})
    nav_df = pd.DataFrame(navs)
    opt = WinRateOptimizer(nav_df, pd.DataFrame(info), holding_days=125, target_annual_return=0.06, tier="C4")
    return opt.optimize(), pd.DataFrame(info)


def test_optimizer_constraints(opt_result):
    res, info = opt_result
    w = res["optimal_weights"]
    assert w, f"优化器未出解: {res.get('optimization_metadata')}"
    lo, hi = DEFAULT_CONSTRAINTS["n_funds_range"]
    assert lo <= len(w) <= hi
    assert sum(w.values()) == pytest.approx(1.0, abs=1e-3)
    for v in w.values():
        assert DEFAULT_CONSTRAINTS["min_single_weight"] - 1e-3 <= v <= DEFAULT_CONSTRAINTS["max_single_weight"] + 1e-3
    bmap = dict(zip(info["fund_code"], info["bucket"]))
    exp = {}
    for c, v in w.items():
        exp[bmap[c]] = exp.get(bmap[c], 0) + v
    assert max(exp.values()) <= DEFAULT_CONSTRAINTS["max_sector_exposure"] + 1e-3


def test_optimizer_result_fields(opt_result):
    res, _ = opt_result
    pm = res["portfolio_metrics"]
    for k in ("win_rate", "no_loss_rate", "monte_carlo_prob"):
        assert 0.0 <= pm[k] <= 1.0
    assert res["fund_details"] and all(d["share_class_recommendation"] == "C" for d in res["fund_details"])


def test_optimizer_empty_input():
    opt = WinRateOptimizer(pd.DataFrame(), pd.DataFrame({"fund_code": []}), 125, 0.06)
    res = opt.optimize()
    assert res["optimal_weights"] == {} and "error" in res["optimization_metadata"]


# ─── SmartCacheManager ─────────────────────────────────────────

def test_cache_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_manager, "CACHE_BASE", tmp_path)
    key = "pytest_phase3_key"
    SmartCacheManager.save_winrate_cache(key, {"win_rate": np.float64(0.75), "n": np.int64(3)})
    got = SmartCacheManager.get_winrate_cache(key)
    assert got is not None and got["win_rate"] == pytest.approx(0.75) and got["n"] == 3
    assert SmartCacheManager.get_winrate_cache("nonexistent_key_xyz") is None


def test_cache_pool_param_isolation_and_as_of_date(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_manager, "CACHE_BASE", tmp_path)
    df1 = pd.DataFrame({"fund_code": ["000001"], "aum_billion": [5.0]})
    SmartCacheManager.save_candidate_pool(df1, min_aum=2.0, min_years=3.0)
    assert SmartCacheManager.get_candidate_pool(min_aum=2.0, min_years=3.0) is not None
    assert SmartCacheManager.get_candidate_pool(min_aum=10.0, min_years=3.0) is None
    k1 = SmartCacheManager.make_optimizer_key(250, 0.08, "C3", 50, as_of_date="2026-11-01")
    k2 = SmartCacheManager.make_optimizer_key(250, 0.08, "C3", 50, as_of_date="2026-11-02")
    assert k1 != k2


def test_rebalance_orders_mode_gentle_vs_forced_and_7d_redline():
    from strategy_bridge import StrategyBridge
    from portfolio_manager import FundHolding, HoldingBatch
    # 偏离 2%（<3% 缓冲区）：gentle 应 HOLD，forced 应触发调仓；但 <7 天批次一律不可卖
    h_mature = FundHolding(
        fund_code="100032", fund_name="富国中证红利指数增强A",
        shares=52000.0, current_nav=1.0, market_value=52000.0,
        batches=[HoldingBatch(batch_id="b1", buy_date="2026-09-01", shares=52000.0, cost_nav=1.0, fee=0.0, holding_days=60)],
    )
    h_locked = FundHolding(
        fund_code="000216", fund_name="华安黄金易ETF联接A",
        shares=48000.0, current_nav=1.0, market_value=48000.0,
        batches=[HoldingBatch(batch_id="b2", buy_date="2026-10-30", shares=48000.0, cost_nav=1.0, fee=0.0, holding_days=3)],
    )
    holdings = {"100032": h_mature, "000216": h_locked}
    targets = {"100032": 0.50, "000216": 0.45}  # 100032 偏离 -2%，000216 偏离 -3% 且未满7天
    res_gentle = StrategyBridge.generate_ai_rebalance_orders(holdings, 0.0, targets, mode="gentle")
    res_forced = StrategyBridge.generate_ai_rebalance_orders(holdings, 0.0, targets, mode="forced")
    map_g = {it["fund_code"]: it for it in res_gentle["items"]}
    map_f = {it["fund_code"]: it for it in res_forced["items"]}
    assert map_g["100032"]["action"] == "HOLD"
    assert map_f["100032"]["action"] == "SELL"
    # 7天惩罚费红线：即便 forced 模式，未满7天份额也严禁触发卖出
    assert map_f["000216"]["action"] == "HOLD"


def test_conditional_winrate_bottom_vs_top():
    """验证高斯核条件胜率在底部估值区与顶部亢奋区的反追高表现"""
    n = 1000
    t = np.linspace(0, 4 * np.pi, n)
    trend = 0.0001 * np.arange(n)
    cycle = 0.20 * np.sin(t)
    nav_series = pd.Series(
        1.0 + trend + cycle,
        index=pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=n)
    )
    hf = WinRateEngine.compute_historical_feature_matrix(nav_series, 125)
    vol_m = float(hf[:, 3].mean())

    bottom_snapshot = {
        "erp_percentile": 85.0,
        "bias20": -0.2,
        "mom60": -6.0,
        "ewma_vol": vol_m,
        "dr007_spread": -0.4,
    }
    top_snapshot = {
        "erp_percentile": 15.0,
        "bias20": 0.2,
        "mom60": 5.0,
        "ewma_vol": vol_m,
        "dr007_spread": 0.4,
    }

    res_bottom = WinRateEngine.rolling_target_winrate(
        nav_series, holding_days=125, target_annual_return=0.08, market_snapshot=bottom_snapshot
    )
    res_top = WinRateEngine.rolling_target_winrate(
        nav_series, holding_days=125, target_annual_return=0.08, market_snapshot=top_snapshot
    )

    c_wr_bottom = res_bottom.get("conditional_win_rate", res_bottom["win_rate"])
    c_wr_top = res_top.get("conditional_win_rate", res_top["win_rate"])

    # 底部高 ERP 负 Bias 的条件胜率必须显著高于顶部追高区
    assert c_wr_bottom > c_wr_top
    assert "kernel_weights" in res_bottom
    assert "unconditional_win_rate" in res_bottom


def test_optimize_rebalance_path_with_mixed_batches_protects_locked():
    """验证含 60天+2天 批次的持仓在调仓优化中绝不卖出 <7天 批次"""
    opt = WinRateOptimizer(
        nav_matrix=pd.DataFrame(),
        candidate_info=pd.DataFrame([{"fund_code": "005561", "status": "正常"}]),
        holding_days=250,
        target_annual_return=0.10,
    )
    # 持仓包含 10,000 份，其中 6,000 份为 60 天老批次，4,000 份为 2 天在途新批次
    current_holdings = {
        "005561": {
            "shares": 10000.0,
            "nav": 1.5,
            "cost": 1.5,
            "holding_days": 2,  # min batch holding days
            "penalty_free_shares": 6000.0,  # 仅 6,000 份免惩罚
        }
    }
    total_val = 10000.0 * 1.5  # 15,000 元
    # 目标权重为 0（需要全额清仓）
    optimal_weights = {"005561": 0.0}

    res = opt.optimize_rebalance_path(
        current_holdings=current_holdings,
        optimal_weights=optimal_weights,
        total_value=total_val,
    )

    actions = res["rebalance_actions"]
    assert len(actions) == 1
    act = actions[0]
    assert act["action"] == "SELL"
    # 必须只卖出 6,000 份安全份额，金额为 9,000 元
    assert act["shares"] == 6000.0
    assert act["amount"] == 9000.0
    # 赎回费率严禁按 2 天 (1.5%) 计算，必须按 >=7 天计算
    assert act["redemption_fee_rate"] < 0.015
    assert "安全份额" in act.get("note", "")

    # 全量 <7 天极端情况：免惩罚份额为 0，必须直接锁仓拦截
    current_holdings_zero_free = {
        "005561": {
            "shares": 4000.0,
            "nav": 1.5,
            "cost": 1.5,
            "holding_days": 2,
            "penalty_free_shares": 0.0,
        }
    }
    res_zero = opt.optimize_rebalance_path(
        current_holdings=current_holdings_zero_free,
        optimal_weights=optimal_weights,
        total_value=6000.0,
    )
    assert len(res_zero["rebalance_actions"]) == 0
    assert len(res_zero["locked_funds"]) == 1
    assert "惩罚期" in res_zero["locked_funds"][0]


def test_one_click_market_optimization_flow_structure():
    """验证全市场选基一次点击调度流程产出完整字段（含 order_sheet 与 rebalance_path）"""
    from portfolio_optimizer import execute_market_optimization_flow
    from unittest.mock import patch
    import portfolio_manager

    buckets = ["equity", "bond", "overseas", "commodity", "fof"]
    navs, info = {}, []
    for i in range(5):
        code = f"8{i:05d}"
        b = buckets[i % len(buckets)]
        navs[code] = _synthetic_nav(n=600, annual=0.06 + 0.01 * i, vol=0.05, seed=200 + i)
        info.append({"fund_code": code, "fund_name": f"全市场测试{i}", "bucket": b, "ac_pair_code": ""})


    fake_ranked = pd.DataFrame(info)
    fake_nav = pd.DataFrame(navs)

    with patch.object(MarketScreener, "run_full_pipeline", return_value=(fake_ranked, fake_nav)), \
         patch.object(MarketScreener, "fetch_candidate_nav_matrix", return_value=fake_nav), \
         patch.object(portfolio_manager, "fetch_realtime_fund_quota", return_value={"status": "开放", "daily_limit": 10000.0, "is_limited": True}):
        flow_res = execute_market_optimization_flow(
            target_pct=8.0,
            horizon_label="中期(1~2年)",
            capital=100000.0,
            progress_cb=lambda c, t, m: None,
        )

        assert "result" in flow_res
        assert "order_sheet" in flow_res
        assert "rebalance_path" in flow_res
        assert flow_res["result"]["optimal_weights"]
        sheet = flow_res["order_sheet"]
        assert len(sheet) == len(flow_res["result"]["optimal_weights"])
        for row in sheet:
            assert "今日可买(元)" in row
            assert "执行建议" in row





def test_optimize_rebalance_path_partial_lock_and_c_class_fee():
    """验证部分批次安全卖出锁仓提示与 C 类份额 30 天免赎回费率"""
    opt = WinRateOptimizer(
        nav_matrix=pd.DataFrame(),
        candidate_info=pd.DataFrame([{"fund_code": "005561", "status": "正常"}, {"fund_code": "008682", "status": "正常"}]),
        holding_days=250,
        target_annual_return=0.10,
    )
    current_holdings = {
        "005561": {
            "shares": 10000.0,
            "nav": 1.5,
            "cost": 1.5,
            "holding_days": 2,
            "safe_holding_days": 60,
            "penalty_free_shares": 6000.0,
            "share_class": "A",
        },
        "008682": {
            "shares": 5000.0,
            "nav": 1.0,
            "cost": 1.0,
            "holding_days": 35,
            "safe_holding_days": 35,
            "penalty_free_shares": 5000.0,
            "share_class": "C",
        }
    }
    total_val = 10000.0 * 1.5 + 5000.0 * 1.0  # 20,000 元
    optimal_weights = {"005561": 0.0, "008682": 0.0}

    res = opt.optimize_rebalance_path(
        current_holdings=current_holdings,
        optimal_weights=optimal_weights,
        total_value=total_val,
    )

    action_map = {a["fund_code"]: a for a in res["rebalance_actions"]}
    # A 类 60 天安全份额费率应为 0.25% (0.0025)
    assert abs(action_map["005561"]["redemption_fee_rate"] - 0.0025) < 1e-4
    # C 类 35 天免赎份额费率应为 0.0
    assert abs(action_map["008682"]["redemption_fee_rate"] - 0.0) < 1e-4
    # 005561 未满 7 天锁定份额应进入 locked_funds 预警
    assert any("005561" in lf and "保护锁仓" in lf for lf in res["locked_funds"])


def test_one_click_market_optimization_flow_all_suspended_edge_case():
    """验证全市场入选基金全部暂停申购（日限额为0）极端流动性场景下安全防御"""
    from portfolio_optimizer import execute_market_optimization_flow
    from unittest.mock import patch
    import portfolio_manager

    buckets = ["equity", "bond", "overseas", "commodity", "fof"]
    navs, info = {}, []
    for i in range(5):
        code = f"9{i:05d}"
        b = buckets[i]
        navs[code] = _synthetic_nav(n=600, annual=0.07 + 0.01 * i, vol=0.04, seed=500 + i)
        info.append({"fund_code": code, "fund_name": f"限购测试{i}", "bucket": b, "ac_pair_code": ""})

    fake_ranked = pd.DataFrame(info)
    fake_nav = pd.DataFrame(navs)

    with patch.object(MarketScreener, "run_full_pipeline", return_value=(fake_ranked, fake_nav)), \
         patch.object(MarketScreener, "fetch_candidate_nav_matrix", return_value=fake_nav), \
         patch.object(portfolio_manager, "fetch_realtime_fund_quota", return_value={"status": "暂停申购", "daily_limit": 0.0, "is_limited": True}):
        flow_res = execute_market_optimization_flow(
            target_pct=8.0,
            horizon_label="中期(1~2年)",
            capital=50000.0,
            progress_cb=lambda c, t, m: None,
        )

        sheet = flow_res["order_sheet"]
        assert len(sheet) == len(flow_res["result"]["optimal_weights"])
        assert len(sheet) >= 3
        for row in sheet:
            assert row["所需交易日"] is None
            assert row["今日可买(元)"] == 0.0
            assert "暂停申购" in row["执行建议"]
