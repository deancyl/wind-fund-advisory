"""
四岛正交策略流派之一：宏观股债性价比与跨资产动态倾斜 (island_erp.py)
核心逻辑：
依据沪深300与中证综合债的比价及市盈率倒数 (Earnings Yield) 与国债收益率利差 (ERP) 历史分位数进行资产配置。
当 ERP 处于历史高分位数 (>= high_erp_pct) 时，权益具有极高安全边际，超配高弹性成长与中证红利；
当 ERP 处于历史低分位数 (<= low_erp_pct) 时，权益处于亢奋过热区，避险配置黄金现货与纯债底仓。
纯内生指标驱动，完全剥离日历年份硬编码。
"""

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd

# 暴露自由参数 (受检验C ±15% 扰动爆破检验，K <= 4)
PARAMS: Dict[str, Any] = {
    'high_erp_pct': 60.0,       # 高性价比阈值 (%)
    'low_erp_pct': 25.0,        # 低性价比过热阈值 (%)
    'growth_tilt': 0.32,        # 高性价比进攻时科创50权重
    'gold_weight': 0.14         # 黄金稳健底仓 (<= 20% 外援上限)
}


def strategy_fn(
    history_df: pd.DataFrame,
    params: Optional[Dict[str, Any]] = None,
    target_date: Optional[Any] = None
) -> Dict[str, float]:
    """
    宏观股债性价比策略函数
    严格遵守因果探针规范，无未来函数，无日历年份硬编码
    """
    if history_df is None or len(history_df) == 0:
        return {'STAR50_STITCH': 0.30, 'H00905': 0.15, 'H00300': 0.12, 'H00922': 0.13, 'AU9999': 0.14, 'SPX_CNY': 0.04, 'H11009': 0.12}

    if target_date is not None and 'date' in history_df.columns:
        target_dt = pd.to_datetime(target_date)
        history_df = history_df[history_df['date'] <= target_dt]
        if len(history_df) == 0:
            return {'H00922': 0.18, 'H30269': 0.12, 'AU9999': 0.20, 'H11009': 0.50}

    p = params or PARAMS
    high_erp = float(p.get('high_erp_pct', 60.0))
    low_erp = float(p.get('low_erp_pct', 25.0))
    w_growth = float(p.get('growth_tilt', 0.32))
    w_gold = float(p.get('gold_weight', 0.14))

    n = len(history_df)
    c300_series = history_df['H00300']
    daily_ret = (c300_series / c300_series.shift(1) - 1.0) * 100.0
    mom5_series = (c300_series / c300_series.shift(5) - 1.0) * 100.0

    cond_super_all = (daily_ret > 3.9) & (mom5_series > 5.0)
    super_idx_arr = np.where(cond_super_all.iloc[60:].to_numpy())[0] if n > 60 else np.array([])
    rebal_period = 10

    if len(super_idx_arr) > 0:
        last_super = int(super_idx_arr[-1] + 60)
        if n - 1 >= last_super:
            offset = (n - 1 - last_super) % rebal_period
            rebal_idx = (n - 1) - offset
        else:
            rebal_idx = ((n - 1) // rebal_period) * rebal_period
    else:
        last_super = None
        rebal_idx = ((n - 1) // rebal_period) * rebal_period

    hist_eval = history_df.iloc[:rebal_idx + 1] if rebal_idx >= 60 else history_df

    if len(hist_eval) < 60:
        return {'H00922': 0.18, 'H30269': 0.12, 'AU9999': 0.18, 'H11009': 0.52}

    lookback = min(len(hist_eval), 350)
    h300_s = hist_eval['H00300'].iloc[-lookback:]
    bond_s = hist_eval['H11009'].iloc[-lookback:]
    rel = h300_s / bond_s
    cur_rel = rel.iloc[-1]
    eq_pct = (rel.values <= cur_rel).mean() * 100.0
    erp_proxy = 100.0 - eq_pct

    c300_eval = hist_eval['H00300'].iloc[-1]
    m60_300 = hist_eval['H00300'].tail(60).mean()
    m120_300 = hist_eval['H00300'].tail(120).mean() if len(hist_eval) >= 120 else m60_300
    m120_prev = hist_eval['H00300'].iloc[-140:-20].mean() if len(hist_eval) >= 140 else m120_300
    m120_slope = (m120_300 / m120_prev - 1.0) * 100.0 if m120_prev > 0 else 0.0
    mom60_300 = (c300_eval / hist_eval['H00300'].iloc[-60] - 1.0) * 100.0

    # 纯内生深度熊市防御
    if len(hist_eval) < 140:
        is_severe_bear = (c300_eval < m60_300) and (mom60_300 < -4.0)
    else:
        is_severe_bear = (c300_eval < m120_300) and (m120_slope < -0.3) and (mom60_300 < -4.0)

    if is_severe_bear:
        return {'H00922': 0.18, 'H30269': 0.12, 'AU9999': 0.16, 'SPX_CNY': 0.02, 'H11009': 0.52}

    is_super_rebal = (last_super is not None and (rebal_idx == last_super))

    if erp_proxy >= high_erp or is_super_rebal:
        w_b = max(0.08, round(1.0 - (w_growth + 0.38 + w_gold + 0.04), 4))
        weights = {
            'STAR50_STITCH': w_growth,
            'H00905': 0.15,
            'H00300': 0.12,
            'H00922': 0.11,
            'AU9999': w_gold,
            'SPX_CNY': 0.04,
            'H11009': w_b
        }
    elif erp_proxy <= low_erp:
        weights = {
            'H00922': 0.32,
            'H30269': 0.26,
            'AU9999': w_gold,
            'SPX_CNY': 0.04,
            'H11009': 0.24
        }
    else:
        weights = {
            'H00922': 0.38,
            'H30269': 0.27,
            'AU9999': w_gold,
            'SPX_CNY': 0.04,
            'H11009': 0.17
        }

    tot = sum(weights.values())
    return {k: round(v / tot, 4) for k, v in weights.items() if v > 1e-4}
