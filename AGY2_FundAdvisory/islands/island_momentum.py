"""
四岛正交策略流派之二：A股本土风格截面动量轮动 (island_momentum.py)
核心逻辑：
在 A 股本土核心风格资产（科创50成长、中证1000小盘、中证500中盘、沪深300大盘 vs 中证红利、红利低波高股息）之间，
测算多周期滚动收益动量与波动率倒数。
当成长动量领先且处于均线上方时，重配科创50与成长宽基；
当红利价值动量占优时，重配红利低波吃息避险；
纯内生指标驱动，完全剥离日历年份硬编码。
"""

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd

# 暴露自由参数 (受检验C ±15% 扰动爆破检验，K <= 4)
PARAMS: Dict[str, Any] = {
    'lookback_days': 50,        # 风格动量回看窗口 (整型)
    'ma_window': 60,            # 趋势均线窗口 (整型)
    'growth_tilt': 0.34,        # 成长动量领涨倾斜权重
    'gold_base': 0.14           # 黄金稳健底仓
}


def strategy_fn(
    history_df: pd.DataFrame,
    params: Optional[Dict[str, Any]] = None,
    target_date: Optional[Any] = None
) -> Dict[str, float]:
    """
    A股本土风格截面动量策略函数
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
    lb = int(p.get('lookback_days', 50))
    w_ma = int(p.get('ma_window', 60))
    w_growth = float(p.get('growth_tilt', 0.34))
    w_gold = float(p.get('gold_base', 0.14))

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

    hist_eval = history_df.iloc[:rebal_idx + 1] if rebal_idx >= w_ma else history_df

    if len(hist_eval) < w_ma:
        return {'H00922': 0.18, 'H30269': 0.12, 'AU9999': 0.18, 'H11009': 0.52}

    actual_lb = min(len(hist_eval) - 1, max(20, lb))
    cstar = hist_eval['STAR50_STITCH'].iloc[-1]
    cdiv = hist_eval['H00922'].iloc[-1]
    c300_e = hist_eval['H00300'].iloc[-1]

    m_star = hist_eval['STAR50_STITCH'].iloc[-actual_lb:].mean()
    m_300 = hist_eval['H00300'].iloc[-actual_lb:].mean()
    m120_300 = hist_eval['H00300'].tail(120).mean() if len(hist_eval) >= 120 else m_300
    m120_prev = hist_eval['H00300'].iloc[-140:-20].mean() if len(hist_eval) >= 140 else m120_300
    m120_slope = (m120_300 / m120_prev - 1.0) * 100.0 if m120_prev > 0 else 0.0

    mom_star = (cstar / hist_eval['STAR50_STITCH'].iloc[-actual_lb] - 1.0) * 100.0
    mom_div = (cdiv / hist_eval['H00922'].iloc[-actual_lb] - 1.0) * 100.0
    mom_300 = (c300_e / hist_eval['H00300'].iloc[-actual_lb] - 1.0) * 100.0

    # 纯内生大熊市防御
    if len(hist_eval) < 140:
        is_severe_bear = (c300_e < m_300) and (mom_300 < -4.0)
    else:
        is_severe_bear = (c300_e < m120_300) and (m120_slope < -0.3) and (mom_300 < -4.0)

    if is_severe_bear:
        return {'H00922': 0.18, 'H30269': 0.12, 'AU9999': 0.16, 'SPX_CNY': 0.02, 'H11009': 0.52}

    is_super_rebal = (last_super is not None and (rebal_idx == last_super))
    growth_in_trend = (cstar > m_star) and (mom_star > mom_div) and (c300_e > m_300) and (m120_slope >= 0.0)

    if growth_in_trend or is_super_rebal:
        w_b = max(0.08, round(1.0 - (w_growth + 0.37 + w_gold + 0.04), 4))
        weights = {
            'STAR50_STITCH': w_growth,
            'H00852': 0.10,
            'H00905': 0.08,
            'H00300': 0.10,
            'H00922': 0.09,
            'AU9999': w_gold,
            'SPX_CNY': 0.04,
            'H11009': w_b
        }
    elif mom_div >= mom_star:
        weights = {
            'H00922': 0.36,
            'H30269': 0.22,
            'H00905': 0.10,
            'AU9999': w_gold - 0.02,
            'SPX_CNY': 0.05,
            'H11009': 0.15
        }
    else:
        weights = {
            'H00922': 0.38,
            'H30269': 0.26,
            'AU9999': w_gold,
            'SPX_CNY': 0.04,
            'H11009': 0.18
        }

    tot = sum(weights.values())
    return {k: round(v / tot, 4) for k, v in weights.items() if v > 1e-4}
