# -*- coding: utf-8 -*-
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import minimize

WORKSPACE_ROOT = Path("d:/Google/Workspace/Wind")
sys.path.insert(0, str(WORKSPACE_ROOT))
sys.path.insert(0, str(WORKSPACE_ROOT / "AGY2_FundAdvisory"))

from strategy_bridge import StrategyBridge
from data_loader import denoise_covariance_matrix

def _normalize_weights_strict(weights):
    cleaned = {k: max(0.0, float(v)) for k, v in weights.items() if np.isfinite(v)}
    tot = sum(cleaned.values())
    if tot <= 1e-12:
        n = max(1, len(weights))
        return {k: round(1.0 / n, 6) for k in weights}
    normed = {k: float(v) / tot for k, v in cleaned.items()}
    keys = list(normed.keys())
    if keys:
        diff = 1.0 - sum(normed.values())
        normed[keys[0]] += diff
    return normed

def solve_core_satellite(codes, nav_df, tier="C3", min_w=0.04, max_w=0.40):
    n = len(codes)
    if n <= 1:
        return {codes[0]: 1.0} if n == 1 else {}
    ret_df = nav_df[codes].pct_change().dropna()
    vols = ret_df.std().values * np.sqrt(250.0)
    vol_map = {c: max(float(v), 0.01) for c, v in zip(codes, vols)}
    
    # 模拟核心代码与卫星代码
    core_buckets = {"pure_bond", "fixed_income_plus", "dividend_value", "gold", "bond", "dividend"}
    sorted_by_vol = sorted(codes, key=lambda c: vol_map.get(c, 0.1))
    split_pt = max(1, len(codes) // 2)
    core_codes = sorted_by_vol[:split_pt]
    sat_codes = sorted_by_vol[split_pt:]

    tier_core_map = {"C1": 0.85, "C2": 0.80, "C3": 0.75, "C4": 0.70, "C5": 0.65}
    w_core_target = tier_core_map.get(str(tier).upper(), 0.75)
    w_sat_target = 1.0 - w_core_target

    inv_vols_core = {c: 1.0 / vol_map[c] for c in core_codes}
    sum_inv = sum(inv_vols_core.values())
    core_weights = {c: (inv_vols_core[c] / sum_inv) * w_core_target for c in core_codes}

    # 卫星仓：夏普/动量倾斜
    ann_ret = (nav_df[sat_codes].iloc[-1] / nav_df[sat_codes].iloc[0]) ** (250.0 / len(nav_df)) - 1.0
    sat_scores = {c: max(0.1, float(ann_ret[c]) / max(vol_map[c], 0.01) + 1.0) for c in sat_codes}
    sum_sat = sum(sat_scores.values())
    sat_weights = {c: (sat_scores[c] / sum_sat) * w_sat_target for c in sat_codes}

    combined = {**core_weights, **sat_weights}
    w_arr = np.array([combined.get(c, 1.0 / n) for c in codes], dtype=float)
    for _ in range(5):
        w_arr = np.clip(w_arr, min_w, max_w)
        s = np.sum(w_arr)
        if s > 0:
            w_arr /= s
    res = {c: float(w) for c, w in zip(codes, w_arr)}
    return _normalize_weights_strict(res)

def solve_all_weather(codes, nav_df, min_w=0.04, max_w=0.40):
    n = len(codes)
    if n <= 1:
        return {codes[0]: 1.0} if n == 1 else {}
    ret_df = nav_df[codes].pct_change().dropna()
    cov = ret_df.cov().values * 250.0
    cov = denoise_covariance_matrix(cov, n_obs=len(ret_df), shrink_alpha=0.15)
    vols = np.sqrt(np.maximum(np.diag(cov), 1e-8))
    
    inv_v = 1.0 / vols
    x0 = inv_v / np.sum(inv_v)
    bounds = [(min_w, max_w)] * n
    
    def erc_obj(w):
        w = np.asarray(w, dtype=np.float64)
        sigma_w = cov @ w
        trc = w * sigma_w
        diffs = trc[:, None] - trc[None, :]
        return float(np.sum(diffs ** 2)) * 1e4

    cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    try:
        res = minimize(erc_obj, x0, method="SLSQP", bounds=bounds, constraints=cons, options={"maxiter": 150, "ftol": 1e-8})
        w_opt = res.x if (res.success or res.fun < erc_obj(x0)) else x0
    except Exception:
        w_opt = x0
    w_opt = np.clip(w_opt, min_w, max_w)
    w_opt /= np.sum(w_opt)
    return _normalize_weights_strict({c: float(w) for c, w in zip(codes, w_opt)})

def solve_black_litterman(codes, nav_df, min_w=0.04, max_w=0.40):
    n = len(codes)
    if n <= 1:
        return {codes[0]: 1.0} if n == 1 else {}
    ret_df = nav_df[codes].pct_change().dropna()
    cov = ret_df.cov().values * 250.0
    cov = denoise_covariance_matrix(cov, n_obs=len(ret_df), shrink_alpha=0.15)
    vols = np.sqrt(np.maximum(np.diag(cov), 1e-8))
    
    risk_aversion = 2.5
    w_eq = 1.0 / (vols ** 2)
    w_eq /= np.sum(w_eq)
    pi = risk_aversion * (cov @ w_eq)
    
    tau = 0.05
    # 计算年化收益与夏普比
    ann_ret = (nav_df[codes].iloc[-1] / nav_df[codes].iloc[0]) ** (250.0 / len(nav_df)) - 1.0
    sharpes = np.array([float(ann_ret[c]) / max(vols[i], 0.01) for i, c in enumerate(codes)])
    mean_sh = np.mean(sharpes)
    P = np.eye(n)
    tilt = 0.04 * np.tanh(sharpes - mean_sh)
    Q = pi + tilt
    omega = np.diag(np.diag(P @ (tau * cov) @ P.T)) + 1e-5 * np.eye(n)
    
    tau_cov_inv = np.linalg.pinv(tau * cov)
    omega_inv = np.linalg.pinv(omega)
    post_cov_inv = tau_cov_inv + P.T @ omega_inv @ P
    post_cov = np.linalg.pinv(post_cov_inv)
    er_post = post_cov @ (tau_cov_inv @ pi + P.T @ omega_inv @ Q)

    bounds = [(min_w, max_w)] * n
    def bl_obj(w):
        w = np.asarray(w, dtype=np.float64)
        port_ret = np.dot(w, er_post)
        port_var = w @ cov @ w
        return -(port_ret - 0.5 * risk_aversion * port_var)
        
    cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    try:
        res = minimize(bl_obj, w_eq, method="SLSQP", bounds=bounds, constraints=cons, options={"maxiter": 150, "ftol": 1e-8})
        w_opt = res.x if res.success else w_eq
    except Exception:
        w_opt = w_eq
    w_opt = np.clip(w_opt, min_w, max_w)
    w_opt /= np.sum(w_opt)
    return _normalize_weights_strict({c: float(w) for c, w in zip(codes, w_opt)})

if __name__ == "__main__":
    df_mat = StrategyBridge.load_matrix()
    test_codes = ["H00300", "H00905", "H00922", "930609", "H11009", "AU9999"]
    nav_df = df_mat[test_codes].copy()
    
    cs = solve_core_satellite(test_codes, nav_df)
    print("Core-Satellite:", cs, "Sum:", sum(cs.values()), "Std:", np.std(list(cs.values())))
    assert abs(sum(cs.values()) - 1.0) < 1e-6
    assert np.std(list(cs.values())) > 0.005

    aw = solve_all_weather(test_codes, nav_df)
    print("All-Weather:", aw, "Sum:", sum(aw.values()), "Std:", np.std(list(aw.values())))
    assert abs(sum(aw.values()) - 1.0) < 1e-6
    assert np.std(list(aw.values())) > 0.005

    bl = solve_black_litterman(test_codes, nav_df)
    print("Black-Litterman:", bl, "Sum:", sum(bl.values()), "Std:", np.std(list(bl.values())))
    assert abs(sum(bl.values()) - 1.0) < 1e-6
    assert np.std(list(bl.values())) > 0.005

    print("ALL THREE NEW SOLVERS PASSED MATHEMATICAL INTEGRITY INVARIANTS!")
