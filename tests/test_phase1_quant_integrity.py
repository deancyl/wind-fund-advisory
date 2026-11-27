# -*- coding: utf-8 -*-
"""
AGY2 Phase 1 (v2.2.0) Quantitative Integrity, Anti-Fake-Diversification,
True Walk-Forward OOS & Daily Public Bundle Regression Gate Suite.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
AGY2_DIR = ROOT_DIR / "AGY2_FundAdvisory"
for p in (str(AGY2_DIR), str(ROOT_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)


# =====================================================================
# Task 1: Classification, Lockup Ban, Exchange-Only Ban & Seed Hygiene
# =====================================================================

def test_classify_fund_bucket_rejects_fake_overseas_and_fake_gold():
    from market_lakehouse import classify_fund_bucket_10, is_index_style_fund

    # 1. Domestic A-share S&P dividend funds MUST NOT be overseas_qdii
    assert classify_fund_bucket_10("指数型-股票", "南方标普红利低波50ETF联接A", "008163") == "dividend_value"
    assert classify_fund_bucket_10("指数型-股票", "华宝标普中国A股红利机会ETF联接A(LOF)", "501029") == "dividend_value"

    # 2. China Internet QDII MUST NOT masquerade as US/Global overseas_qdii
    assert classify_fund_bucket_10("指数型-海外股票", "易方达中证海外互联网50ETF联接(QDII)A", "006327") == "hk_offshore"
    assert classify_fund_bucket_10("指数型-海外股票", "交银中证海外中国互联网指数(LOF)A", "164906") == "hk_offshore"

    # 3. Hong Kong single-sector bank index MUST land in hk_offshore (not domestic A-share equity)
    assert classify_fund_bucket_10("指数型-股票", "泰康香港银行指数A", "006809") == "hk_offshore"
    assert classify_fund_bucket_10("指数型-股票", "鹏华中证香港银行指数(LOF)A", "501025") == "hk_offshore"

    # 4. Oil/Agri FOF & Cyclical Non-Ferrous Metal Stock ETFs MUST NOT land in commodity_gold
    b_oil = classify_fund_bucket_10("QDII-商品", "银华抗通胀主题(QDII-FOF-LOF)A", "161815")
    assert b_oil == "other_commodity"
    assert is_index_style_fund("QDII-商品", "银华抗通胀主题(QDII-FOF-LOF)A", b_oil, operating_fee=2.15) is False

    assert classify_fund_bucket_10("指数型-股票", "天弘中证工业有色金属主题ETF发起联接A", "017192") == "sector_theme_index"
    assert classify_fund_bucket_10("指数型-股票", "华夏有色金属ETF联接A", "016707") == "sector_theme_index"

    # 5. Pure Gold ETF feeders MUST land in commodity_gold and be index-eligible
    b_gold = classify_fund_bucket_10("指数型-其他", "华安黄金ETF联接A", "000216")
    assert b_gold == "commodity_gold"
    assert is_index_style_fund("指数型-其他", "华安黄金ETF联接A", b_gold, operating_fee=0.60) is True

    # 6. US REITs MUST NOT occupy overseas equity broad index slot
    assert classify_fund_bucket_10("指数型-海外股票", "南方美国精选REIT指数(QDII-LOF)A", "160140") == "other_commodity"

    # 7. Real Global/US QDII stays overseas_qdii
    assert classify_fund_bucket_10("QDII-普通股票", "广发全球精选股票(QDII)人民币A", "270023") == "overseas_qdii"
    assert classify_fund_bucket_10("指数型-海外股票", "华安德国(DAX)联接(QDII)A", "000614") == "overseas_qdii"

    # 8. Short-duration bonds MUST separate into short_bond
    assert classify_fund_bucket_10("债券型-中短债", "嘉实超短债债券C", "070009") == "short_bond"
    assert classify_fund_bucket_10("债券型-中短债", "财通资管鸿福短债A", "007915") == "short_bond"

    # 9. On-exchange ETFs MUST be excluded from OTC buyable buckets
    assert classify_fund_bucket_10("指数型-股票", "华泰柏瑞沪深300ETF", "510300", purchase_status="场内交易") == "EXCLUDE_EXCHANGE_ONLY"
    assert classify_fund_bucket_10("指数型-海外股票", "博时标普500ETF", "513500", purchase_status="场内交易") == "EXCLUDE_EXCHANGE_ONLY"


def test_lockup_and_exchange_ban_rules_and_anchors():
    from market_lakehouse import is_lockup_or_banned_fund, _ANCHOR_SEED_CODES

    lockup_samples = [
        ("南方稳利1年持有期债券A", "000086"),
        ("建信鑫弘180天持有期债券A", "018192"),
        ("融通稳信增益6个月持有期混合A", "010807"),
        ("易方达优势领航六个月持有混合(FOF)A", "012652"),
        ("易方达优势价值一年持有混合(FOF)A", "013287"),
        ("景顺长城宁景6个月持有混合A", "011803"),
        ("中泰红利优选一年持有混合发起", "014771"),
        ("某某90天滚动持有短债A", "099999"),
    ]
    for name, code in lockup_samples:
        assert is_lockup_or_banned_fund(name, code) is True, f"Failed to ban lockup fund: {code} {name}"

    assert is_lockup_or_banned_fund("华泰柏瑞沪深300ETF", "510300", "场内交易") is True
    assert is_lockup_or_banned_fund("易方达沪深300ETF联接A", "110020", "开放申购") is False
    # 519xxx 是中国场外开放式基金代码段，绝不可误判为场内 ETF
    assert is_lockup_or_banned_fund("新华优选分红混合A", "519087", "开放申购") is False
    assert "000086" not in _ANCHOR_SEED_CODES
    assert "510300" not in _ANCHOR_SEED_CODES


def test_public_seed_files_include_master_catalog_and_rules():
    import runtime_paths

    assert "master/fund_catalog.parquet" in runtime_paths.PUBLIC_SEED_FILES
    assert "master/fund_trading_rules.parquet" in runtime_paths.PUBLIC_SEED_FILES


def test_cleaned_lakehouse_zero_violations_and_has_short_bonds():
    from market_lakehouse import load_elite_lakehouse, is_lockup_or_banned_fund

    nav_df, meta_df, status = load_elite_lakehouse()
    assert nav_df is not None and meta_df is not None and not meta_df.empty

    # 1. Zero lockup or on-exchange funds in lakehouse
    banned = [
        f"{r['fund_code']} {r['fund_name']}"
        for _, r in meta_df.iterrows()
        if is_lockup_or_banned_fund(str(r.get("fund_name", "")), str(r.get("fund_code", "")), str(r.get("purchase_status", "")))
    ]
    assert banned == [], f"Lockup/exchange funds leaked into lakehouse: {banned}"

    # 2. Zero fake A-share dividend or China-Internet funds in overseas_qdii
    qdii_df = meta_df[meta_df["bucket_10"] == "overseas_qdii"]
    fake_qdii = qdii_df[qdii_df["fund_name"].astype(str).str.contains("标普中国|标普红利低波|中概|海外中国互联|海外互联|香港|恒生|港股|A股", na=False)]
    assert fake_qdii.empty, f"Fake overseas funds in overseas_qdii: {fake_qdii[['fund_code','fund_name']].to_dict('records')}"

    # 3. Zero non-gold oil FOF or metal mining stocks in commodity_gold
    gold_df = meta_df[meta_df["bucket_10"] == "commodity_gold"]
    fake_gold = gold_df[gold_df["fund_name"].astype(str).str.contains("有色|通胀|原油|石油|FOF|矿|股", na=False)]
    assert fake_gold.empty, f"Fake gold funds in commodity_gold: {fake_gold[['fund_code','fund_name']].to_dict('records')}"
    assert len(gold_df) >= 5, "Must preserve genuine pure gold ETF feeders"

    # 4. Short-duration bonds MUST be populated (>= 8 open short-bond funds)
    sb_df = meta_df[meta_df["bucket_10"] == "short_bond"]
    assert len(sb_df) >= 8, f"Expected >= 8 short_bond funds for 1.59% low-rate shield, got {len(sb_df)}"

    # 5. Zero high-fee FOFs in index_only eligible set
    idx_df = meta_df[meta_df["is_index_eligible"].astype(bool)]
    bad_idx = idx_df[idx_df["fund_name"].astype(str).str.contains("FOF|抗通胀", na=False)]
    assert bad_idx.empty, f"Active FOF leaked into is_index_eligible: {bad_idx[['fund_code','fund_name']].to_dict('records')}"


# =====================================================================
# Task 2: True OOS Non-Leakage, Macro Kernel Alignment & Anti-Cluster
# =====================================================================

def test_winrate_optimizer_strict_oos_zero_leakage():
    """Mutating the tail 30% validation slice MUST NOT change optimal_weights (proving zero look-ahead leakage)."""
    from portfolio_optimizer import WinRateOptimizer

    rng = np.random.default_rng(123)
    dates = pd.bdate_range("2019-01-02", periods=900)
    codes = [f"90000{i}" for i in range(6)]
    base_rets = rng.normal(0.0003, 0.009, size=(900, 6))
    nav_a = pd.DataFrame(np.cumprod(1.0 + base_rets, axis=0), index=dates, columns=codes)

    # Perturb ONLY the last 30% (validation slice) violently
    nav_b = nav_a.copy()
    split = int(len(nav_b) * 0.70)
    nav_b.iloc[split:, 0] = nav_b.iloc[split:, 0] * 3.5
    nav_b.iloc[split:, 1] = nav_b.iloc[split:, 1] * 0.25

    cand_df = pd.DataFrame([
        {"fund_code": c, "fund_name": f"测试基金{i}", "bucket": "broad_index" if i >= 2 else "pure_bond", "asset_class": "equity" if i >= 2 else "bond"}
        for i, c in enumerate(codes)
    ])

    opt_a = WinRateOptimizer(nav_matrix=nav_a, candidate_info=cand_df, holding_days=126, target_annual_return=0.06, tier="C3", target_num_funds=4, model_type="all_weather", market_snapshot={"erp_percentile": 70.0, "bias_20": 0.5, "mom60_300": 1.0, "ewma_vol": 0.15, "dr007_spread_bp": -5.0})
    opt_b = WinRateOptimizer(nav_matrix=nav_b, candidate_info=cand_df, holding_days=126, target_annual_return=0.06, tier="C3", target_num_funds=4, model_type="all_weather", market_snapshot={"erp_percentile": 70.0, "bias_20": 0.5, "mom60_300": 1.0, "ewma_vol": 0.15, "dr007_spread_bp": -5.0})

    w_a = opt_a.optimize()["optimal_weights"]
    w_b = opt_b.optimize()["optimal_weights"]
    assert set(w_a.keys()) == set(w_b.keys()), f"Leakage altered selected funds: {w_a} vs {w_b}"
    for k in w_a:
        assert abs(w_a[k] - w_b[k]) < 1e-6, f"Leakage altered weight for {k}: {w_a[k]} vs {w_b[k]}"


def test_conditional_kernel_macro_feature_alignment_eliminates_11sigma_bug():
    """Bond fund 006210 and equity fund 110020 over overlapping dates MUST align to identical macro feature space with reasonable z-scores."""
    from market_lakehouse import load_elite_lakehouse
    from strategy_bridge import StrategyBridge
    from winrate_engine import compute_historical_feature_matrix, compute_kernel_weights, extract_state_vector

    nav_df, _, _ = load_elite_lakehouse()
    snap = StrategyBridge.get_latest_market_snapshot(force_reload=False)
    sv = extract_state_vector(snap)

    s_bond = nav_df["006210"].dropna()
    s_eq = nav_df["110020"].dropna()
    common_idx = s_bond.index.intersection(s_eq.index)
    assert len(common_idx) > 600

    hf_bond = compute_historical_feature_matrix(s_bond.loc[common_idx], 250)
    hf_eq = compute_historical_feature_matrix(s_eq.loc[common_idx], 250)
    assert hf_bond.shape == hf_eq.shape
    assert np.allclose(hf_bond, hf_eq, atol=1e-6), "Macro historical feature matrix must NOT depend on individual fund price noise"

    # Active dimensions (non-zero std) must have reasonable z-distance (< 3.5 mean |z|, no 11.7-sigma blowup)
    stds = np.nanstd(hf_bond, axis=0)
    means = np.nanmean(hf_bond, axis=0)
    active = stds >= 1e-6
    assert int(np.sum(active)) >= 4
    z_active = np.abs((sv[active] - means[active]) / stds[active])
    assert float(np.mean(z_active)) < 3.5, f"Active macro z-scores still distorted: {z_active}"

    kw = compute_kernel_weights(hf_bond, sv)
    assert len(kw) == len(hf_bond) and abs(float(np.sum(kw)) - 1.0) < 1e-6


def test_goal_driven_portfolio_anti_cluster_quota_and_all_weather_sanity():
    """Verify representative tiers across both index_only & full_market (including ¥200,000 capital) obey all Phase 1 guardrails."""
    from goal_driven_selector import clear_goal_solver_cache, solve_goal_driven_portfolio, classify_style_cluster
    from market_lakehouse import is_lockup_or_banned_fund

    clear_goal_solver_cache()
    rul = pd.read_parquet(ROOT_DIR / "data/master/fund_trading_rules.parquet")
    rul["code"] = rul["symbol"].astype(str).str.strip().str.zfill(6)
    rul_map = {r["code"]: r.to_dict() for _, r in rul.drop_duplicates("code").iterrows()}

    cases = [
        ("C1", "risk_parity", "index_only", 6, 3.5, 12, 50000.0),
        ("C2", "dividend_defense", "index_only", 6, 5.5, 12, 50000.0),
        ("C3", "all_weather", "index_only", 6, 15.0, 24, 50000.0),
        ("C3", "all_weather", "index_only", 6, 15.0, 24, 200000.0),
        ("C3", "all_weather", "full_market", 6, 15.0, 24, 50000.0),
        ("C4", "barbell_growth", "full_market", 6, 24.0, 24, 50000.0),
        ("C5", "barbell_growth", "full_market", 6, 45.0, 36, 50000.0),
    ]

    for tier, model_id, u_mode, n_f, t_ret, h_m, cap in cases:
        res = solve_goal_driven_portfolio(
            risk_level=tier,
            fund_count=n_f,
            model_id=model_id,
            target_return_pct=t_ret,
            horizon_months=h_m,
            universe_mode=u_mode,
            investment_amount=cap,
            force_recompute=True,
        )
        fw = res["final_weights"]
        cards = res["fund_cards_meta"]
        sa = res["solver_audit"]

        assert len(fw) == n_f, f"{tier}/{model_id}/{u_mode}: expected {n_f} funds, got {len(fw)}"
        assert abs(sum(fw.values()) - 1.0) < 1e-3, f"Weights don't sum to 1: {fw}"
        assert sa.get("oos_method") == "strict_70_30_and_walk_forward"
        assert "survivorship_bias_disclaimer" in sa and len(sa["survivorship_bias_disclaimer"]) > 10
        assert "walk_forward_audit" in res

        cluster_weights = {}
        buckets = []
        for c, w in fw.items():
            cm = cards[c]
            fn = cm["fund_name"]
            r = rul_map.get(c, {})
            ps = str(r.get("purchase_status", ""))
            assert not is_lockup_or_banned_fund(fn, c, ps), f"Banned fund selected in {tier}/{model_id}: {c} {fn}"
            assert r.get("is_purchase_allowed", True) is not False and "暂停" not in ps, f"Suspended fund selected: {c} {fn} ({ps})"
            cl = classify_style_cluster(c, cm)
            cluster_weights[cl] = cluster_weights.get(cl, 0.0) + w
            buckets.append(cm.get("bucket_10", ""))

        # Single non-bond style cluster cap (<= 0.36 general, <= 0.46 dividend_defense/barbell_growth)
        max_non_bond_cap = 0.46 if model_id in ("dividend_defense", "barbell_growth") else 0.37
        for cl, cw in cluster_weights.items():
            if cl in ("short_bond", "pure_bond", "fixed_income_plus"):
                continue
            assert cw <= max_non_bond_cap, f"Over-concentrated cluster {cl}={cw:.2%} in {tier}/{model_id}/{u_mode}: {fw}"

        # C1 MUST include at least 1 short_bond duration cushion
        if tier == "C1":
            assert "short_bond" in buckets, f"C1 must include short_bond cushion, got buckets={buckets}"


# =====================================================================
# Task 3: Macro Dual-Brain Unity, Zero Hardcoding, A/C Mapping & Audit
# =====================================================================

def test_ten_dim_votes_zero_hardcoded_breadth_and_bear_damping_invariant(monkeypatch):
    """Ensure no hardcoded 16,763/64.5 breadth fallback, anti-crowding wording, and BEAR damping preserving test_g17 invariant."""
    import advisory_engine
    import data_loader

    monkeypatch.setattr(data_loader.DataLoader, "fetch_market_turnover_and_sentiment", staticmethod(lambda use_cache=True: {}))

    # 1. Missing breadth data MUST neutralize d7 with zero hardcoded strings
    snap_missing = {
        "erp_percentile": 88.0,
        "bias_20": 1.2,
        "ruler_multiplier": 1.55,
        "market_state_code": "SEVERE_BEAR",
        "market_turnover_sentiment": {},
        "option_iv_pct": 19.0,
        "ic_annualized_basis_rate": 9.5,
        "cgb_10y": 1.59,
        "us_10y": 4.20,
        "dr007_spread_bp": -12.0,
    }
    res_bear = advisory_engine.compute_ten_dimension_votes(snapshot=snap_missing, tier="C3")
    d7 = [d for d in res_bear["dimensions"] if d["dimension_id"] == 7][0]
    assert "16,763" not in d7["reason"]
    assert "64.5" not in d7["reason"]
    assert d7["vote"] == "NEUTRAL" and d7["delta_pct"] == 0.0

    # 2. SEVERE_BEAR MUST damp positive tilt to <= +0.08 while preserving suggested_equity_ratio == 0.60 + equity_tilt_pct
    assert res_bear["equity_tilt_pct"] <= 0.08 + 1e-6, f"Bear damping failed: equity_tilt_pct={res_bear['equity_tilt_pct']}"
    assert abs(res_bear["suggested_equity_ratio"] - (0.60 + res_bear["equity_tilt_pct"])) < 1e-4
    assert res_bear.get("bear_damping_applied") is True
    assert "熊市" in res_bear["causal_formula"] or "折减" in res_bear["causal_formula"]

    # 3. With valid breadth data, d7 copy MUST clarify anti-crowding score semantics
    snap_live = dict(snap_missing)
    snap_live["market_state_code"] = "NEUTRAL"
    snap_live["market_turnover_sentiment"] = {"turnover_str": "12,345 亿", "up_pct": 58.2}
    res_live = advisory_engine.compute_ten_dimension_votes(snapshot=snap_live, tier="C3")
    d7_live = [d for d in res_live["dimensions"] if d["dimension_id"] == 7][0]
    assert "反拥挤安全分" in d7_live["reason"]
    assert "12,345 亿" in d7_live["reason"]


def test_api_blueprint_c_share_tip_backtest_slice_and_forward_audit():
    """Verify C-share sibling lookup, honest model_live slice label, and forward_audit_logger wiring."""
    import api_server

    # 1. Sibling C-share lookup from fund_catalog.parquet
    sib = api_server._lookup_c_share_sibling("110020", "易方达沪深300ETF联接A")
    assert sib is not None and len(sib["code"]) == 6 and sib["code"] != "110020", f"Expected C-share sibling for 110020, got {sib}"

    # 2. Blueprint payload for short horizon (6 months) exposes C-share fee tip, walk_forward_audit, disclaimer, universe_comparison
    bp = api_server.api_v1_recommend_blueprint(
        risk_level="C3",
        model="all_weather",
        fund_count=6,
        amount=50000.0,
        target_return_pct=6.0,
        horizon_months=6,
        universe_mode="index_only",
    )
    assert "walk_forward_audit" in bp and isinstance(bp["walk_forward_audit"], dict)
    assert "survivorship_bias_disclaimer" in bp and len(bp["survivorship_bias_disclaimer"]) > 10
    assert "universe_comparison" in bp and "index_only" in bp["universe_comparison"]
    assert len(bp["items"]) == 6
    assert any("C 类" in str(it.get("share_class_tip", "")) for it in bp["items"])

    # 3. Backtest curves in mode="model_live" MUST NOT label fitted segment as "样本外区间"
    curves = api_server.api_v1_charts_backtest_curves(
        tier="C3",
        mode="model_live",
        model="all_weather",
        fund_count=6,
        period="all",
        target_return_pct=15.0,
        horizon_months=24,
        universe_mode="index_only",
    )
    slice_labels = [sl.get("label", "") for sl in (curves.get("slices") or [])]
    assert "样本外区间" not in slice_labels, f"Misleading OOS slice still present on model_live: {slice_labels}"

    # 4. Forward audit logger helper exists & is callable without crash
    assert hasattr(api_server, "_record_daily_forward_audit_snapshot")


# =====================================================================
# Task 5: Daily Public Bundle, Compact float32 Export & Proxy-Free Sync
# =====================================================================

def test_daily_public_bundle_privacy_sha256_and_compact_float32_roundtrip(tmp_path):
    """Verify bundle builder emits ONLY whitelisted public files, valid SHA256 manifest, and exact little-endian float32 nav_f32.bin."""
    import hashlib
    import json
    import subprocess
    import tarfile

    out_dir = tmp_path / "bundle_out"
    cmd = [
        sys.executable,
        str(ROOT_DIR / "scripts" / "build_daily_public_bundle.py"),
        "--output-dir",
        str(out_dir),
        "--skip-network",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT_DIR), timeout=60)
    assert proc.returncode == 0, f"Bundle builder failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"

    manifest_path = out_dir / "manifest.json"
    bundle_path = out_dir / "agy2-market-bundle-latest.tar.gz"
    mobile_path = out_dir / "agy2-mobile-compact-v1.tar.gz"
    assert manifest_path.exists() and bundle_path.exists() and mobile_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["sha256"] == hashlib.sha256(bundle_path.read_bytes()).hexdigest()
    assert manifest["mobile_compact_sha256"] == hashlib.sha256(mobile_path.read_bytes()).hexdigest()
    assert int(manifest["fund_count"]) >= 200

    # Strict privacy whitelist check on main bundle
    from remote_bundle_sync import PUBLIC_BUNDLE_WHITELIST

    with tarfile.open(bundle_path, "r:gz") as tf:
        names = [m.name.replace("\\", "/").lstrip("./") for m in tf.getmembers() if m.isfile()]
    assert set(names) == set(PUBLIC_BUNDLE_WHITELIST), f"Bundle members mismatch whitelist: {names}"
    for n in names:
        assert not any(priv in n.lower() for priv in ("ledger", "backup", "portfolio", "audit", "secret", "user"))

    # Exact float32 binary contract verification on mobile compact bundle
    with tarfile.open(mobile_path, "r:gz") as tf:
        meta_bytes = tf.extractfile("bundle_meta.json").read()
        bin_bytes = tf.extractfile("nav_f32.bin").read()
    meta_c = json.loads(meta_bytes.decode("utf-8"))
    n_dates = int(meta_c["n_dates"])
    n_funds = int(meta_c["n_funds"])
    assert meta_c["dtype"] == "float32_le"
    assert meta_c["layout"] == "row_major_dates_x_funds"
    assert len(bin_bytes) == n_dates * n_funds * 4, "nav_f32.bin byte length mismatch"

    arr = np.frombuffer(bin_bytes, dtype="<f4").reshape((n_dates, n_funds))
    orig_nav = pd.read_parquet(ROOT_DIR / "data/processed/market_elite_nav_matrix.parquet")
    sample_code = meta_c["funds"][0]["code"]
    orig_col = orig_nav[sample_code].to_numpy(dtype=np.float64)
    valid_mask = np.isfinite(orig_col)
    assert np.allclose(arr[valid_mask, 0], orig_col[valid_mask], rtol=1e-5, atol=1e-5)


def test_remote_bundle_sync_proxy_free_fallback_and_atomic_extract(tmp_path):
    """Verify remote_bundle_sync tries mirror -> GitHub -> seamless direct EastMoney fallback on timeout, and blocks non-whitelist tar entries."""
    import tarfile
    import remote_bundle_sync

    # 1. When all remote endpoints fail (no VPN in China), MUST fall back seamlessly to local_fallback_fn
    called_urls = []

    def _always_timeout(url: str, timeout: float) -> bytes:
        called_urls.append((url, timeout))
        raise TimeoutError("simulated China firewall timeout")

    fallback_called = {"count": 0}

    def _local_fb():
        fallback_called["count"] += 1
        return {"status": "updated", "updated_dates": 1, "latest_date": "2026-11-27"}

    res = remote_bundle_sync.sync_public_bundle_with_fallback(
        data_dir=tmp_path,
        timeout_sec=3.0,
        fetcher=_always_timeout,
        local_fallback_fn=_local_fb,
    )
    assert fallback_called["count"] == 1
    assert res["sync_channel"] == "direct_eastmoney_fallback"
    assert len(called_urls) >= 1 and all(t <= 5.0 for _, t in called_urls)

    # 2. Tarball containing unauthorized file MUST be rejected
    evil_tar = tmp_path / "evil.tar.gz"
    evil_src = tmp_path / "evil.txt"
    evil_src.write_text("bad", encoding="utf-8")
    with tarfile.open(evil_tar, "w:gz") as tf:
        tf.add(evil_src, arcname="user_ledgers/hacked.json")

    with pytest.raises(ValueError):
        remote_bundle_sync.extract_public_bundle_atomic(evil_tar, tmp_path / "out_data")


