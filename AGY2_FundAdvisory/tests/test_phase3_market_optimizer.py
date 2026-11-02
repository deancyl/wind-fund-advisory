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

