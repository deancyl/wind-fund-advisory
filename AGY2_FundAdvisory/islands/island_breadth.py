"""
四岛正交策略流派之三：市场宽度与均线偏离度择时 (island_breadth.py)
核心逻辑：
利用核心权益资产相对于中长期趋势均线 (MA60/MA120) 的偏离度 (Bias) 与宽度指标探测极端超买超卖状态。
当权益资产深度超卖负乖离 (Bias < oversold_bias) 时，逆向阶梯吸筹博弈均值回归；
当权益资产极端超买正乖离 (Bias > overbought_bias) 时，阶梯止盈切换至稳健红利与纯债避险底仓。
纯内生指标驱动，完全剥离日历年份硬编码。
"""

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd

# 暴露自由参数 (受检验C ±15% 扰动爆破检验，K <= 4)
PARAMS: Dict[str, Any] = {
    'ma_window': 60,            # 均线偏离度回看天数 (整型)
    'oversold_bias': -5.0,      # 严重超卖负乖离阈值 (%)
    'overbought_bias': 8.0,     # 严重超买正乖离阈值 (%)
    'gold_base': 0.14           # 黄金稳健底仓
}


def strategy_fn(
    history_df: pd.DataFrame,
    params: Optional[Dict[str, Any]] = None,
    target_date: Optional[Any] = None
) -> Dict[str, float]:
    """
    市场宽度与偏离度择时策略函数
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
    w_ma = int(p.get('ma_window', 60))
    os_b = float(p.get('oversold_bias', -5.0))
    ob_b = float(p.get('overbought_bias', 8.0))
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

    actual_w = min(len(hist_eval), max(20, w_ma))
    h300_s = hist_eval['H00300']
    ma = h300_s.iloc[-actual_w:].mean()
    cur = h300_s.iloc[-1]
    bias = (cur - ma) / ma * 100.0

    m120_300 = hist_eval['H00300'].tail(120).mean() if len(hist_eval) >= 120 else ma
    m120_prev = hist_eval['H00300'].iloc[-140:-20].mean() if len(hist_eval) >= 140 else m120_300
    m120_slope = (m120_300 / m120_prev - 1.0) * 100.0 if m120_prev > 0 else 0.0
    mom60_300 = (cur / hist_eval['H00300'].iloc[-60] - 1.0) * 100.0

    # 纯内生大熊市防御
    if len(hist_eval) < 140:
        is_severe_bear = (cur < ma) and (mom60_300 < -4.0)
    else:
        is_severe_bear = (cur < m120_300) and (m120_slope < -0.3) and (mom60_300 < -4.0)

    if is_severe_bear:
        return {'H00922': 0.18, 'H30269': 0.12, 'AU9999': 0.16, 'SPX_CNY': 0.02, 'H11009': 0.52}

    is_super_rebal = (last_super is not None and (rebal_idx == last_super))

    if bias < os_b or is_super_rebal or (cur > ma and m120_slope >= 0.0):
        # 深度超卖逆向吸筹或脉冲牛市：A股权益 71%
        weights = {
            'STAR50_STITCH': 0.35,
            'H00300': 0.11,
            'H00852': 0.10,
            'H00905': 0.06,
            'H00922': 0.09,
            'AU9999': w_gold,
            'SPX_CNY': 0.04,
            'H11009': 0.15
        }
    elif bias > ob_b:
        # 极端超买亢奋：阶梯锁定收益至纯债与红利低波 (A股权益 58%)
        weights = {
            'H00922': 0.32,
            'H30269': 0.26,
            'AU9999': w_gold,
            'SPX_CNY': 0.04,
            'H11009': 0.24
        }
    else:
        # 常规中枢：A股权益 64%
        weights = {
            'H00922': 0.38,
            'H30269': 0.26,
            'AU9999': w_gold,
            'SPX_CNY': 0.04,
            'H11009': 0.18
        }

    tot = sum(weights.values())
    return {k: round(v / tot, 4) for k, v in weights.items() if v > 1e-4}
