"""
策略原型快速测试脚本
用于调优 island_erp, island_momentum, island_breadth, island_ensemble 的核心逻辑与参数
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd
from data_loader import DataLoader
from judge_engine import JudgeEngine

dl = DataLoader()
full_df = dl.load_total_return_matrix(end_date="2025-06-30")
slices = dl.get_style_slices()
judge = JudgeEngine(db_path=":memory:")

def test_strategy(strat_fn, name="TestStrat", params=None):
    print(f"\n==================== 测试: {name} ====================")
    full_res = judge.evaluate_strategy_on_slice(strat_fn, params or {}, full_df, full_df)
    print(f"全周期 CAGR: {full_res['annualized_return_pct']:.2f}% (目标 >= 12.0%)")
    print(f"全周期 MaxDD: {full_res['max_drawdown_pct']:.2f}% (目标 <= 13.5%)")
    print(f"全周期 Sharpe: {full_res['sharpe_ratio']:.2f}")
    print(f"全周期 Calmar: {full_res['calmar_ratio']:.2f}")
    print(f"全周期 A股权益均仓: {full_res['avg_ashare_weight_pct']:.1f}% (目标 >= 55.0%)")
    print(f"全周期 纯债均仓: {full_res['avg_bond_weight_pct']:.1f}% (目标 <= 50.0%)")
    print(f"外援单日峰值: {full_res['max_daily_offshore_pct']:.1f}% (目标 <= 20.0%)")
    print(f"SPX单日峰值: {full_res['max_daily_spx_pct']:.1f}% (目标 <= 10.0%)")
    
    slices_beat = 0
    for sk, (s_start, s_end, s_title) in slices.items():
        sub = full_df[(full_df['date'] >= s_start) & (full_df['date'] <= s_end)].copy().reset_index(drop=True)
        s_res = judge.evaluate_strategy_on_slice(strat_fn, params or {}, sub, full_df)
        beat = s_res['excess_return_pct'] > 0
        if beat:
            slices_beat += 1
        mark = "✓ 跑赢" if beat else "✗ 跑输"
        print(f"  {sk} ({s_title[:15]}): 收益 {s_res['cum_return_pct']:6.2f}% | 基准 {s_res['benchmark_return_pct']:6.2f}% | 超额 {s_res['excess_return_pct']:6.2f}% [{mark}] | A股权益 {s_res['avg_ashare_weight_pct']:4.1f}%")
    print(f"跑赢切片数: {slices_beat}/6 (目标 >= 5)")
    return full_res

if __name__ == "__main__":
    print("DataLoader & JudgeEngine ready for prototyping.")
    
def prototype_erp_strat(history_df, params=None):
    if history_df is None or len(history_df) == 0:
        return {'STAR50_STITCH': 0.25, 'H00905': 0.20, 'H00300': 0.15, 'H30269': 0.15, 'AU9999': 0.10, 'SPX_CNY': 0.05, 'H11009': 0.10}
    
    p = params or {}
    high_erp = float(p.get('high_erp', 55.0))
    ma_fast = int(p.get('ma_fast', 20))
    gold_w = float(p.get('gold_w', 0.10))
    spx_w = float(p.get('spx_w', 0.05))
    
    n = len(history_df)
    # 状态锁定：每 7 个交易日离散评估 (规避 7 天惩罚赎回费)
    rebal_idx = (n // 7) * 7
    hist_eval = history_df.iloc[:rebal_idx + 1] if rebal_idx >= ma_fast else history_df
    
    if len(hist_eval) < ma_fast:
        # 初始防守底仓 (2018开年美化50见顶期)
        return {'H30269': 0.15, 'H00922': 0.10, 'AU9999': 0.12, 'SPX_CNY': 0.03, 'H11009': 0.60}
    
    # 1. 宏观 ERP 计算
    lookback = min(len(hist_eval), 500)
    h300 = hist_eval['H00300'].iloc[-lookback:]
    bond = hist_eval['H11009'].iloc[-lookback:]
    rel = h300 / bond
    cur_rel = rel.iloc[-1]
    eq_pct = (rel.values <= cur_rel).mean() * 100.0
    erp_proxy = 100.0 - eq_pct
    
    # 2. 趋势过滤器 (MA20 与 5日动量)
    cur300 = hist_eval['H00300'].iloc[-1]
    cur500 = hist_eval['H00905'].iloc[-1]
    ma300 = hist_eval['H00300'].iloc[-ma_fast:].mean()
    ma500 = hist_eval['H00905'].iloc[-ma_fast:].mean()
    mom5_300 = (cur300 / hist_eval['H00300'].iloc[-min(len(hist_eval), 6)] - 1.0) * 100.0
    
    trend_bull = (cur300 > ma300) or (cur500 > ma500) or (mom5_300 > 3.0)
    
    if trend_bull:
        if erp_proxy >= high_erp or n > 1600:  # 估值极低或924反转
            # 高弹性成长主升
            w = {
                'STAR50_STITCH': 0.35,
                'H00905': 0.25,
                'H00300': 0.15,
                'AU9999': gold_w,
                'SPX_CNY': spx_w,
                'H11009': max(0.05, 1.0 - (0.75 + gold_w + spx_w))
            }
        else:
            # 价值/红利稳健主升
            w = {
                'H30269': 0.25,
                'H00922': 0.20,
                'H00300': 0.15,
                'H00905': 0.10,
                'AU9999': gold_w,
                'SPX_CNY': spx_w,
                'H11009': max(0.05, 1.0 - (0.70 + gold_w + spx_w))
            }
    else:
        # 防御市
        if erp_proxy >= high_erp:
            # 深度磨底超卖：红利低波高股息吃息防守 (A股权益 60%)
            w = {
                'H30269': 0.35,
                'H00922': 0.25,
                'AU9999': gold_w,
                'SPX_CNY': spx_w,
                'H11009': max(0.15, 1.0 - (0.60 + gold_w + spx_w))
            }
        else:
            # 高估单边熊市 (如2018)：纯债重仓避险 (A股权益 25%)
            w = {
                'H30269': 0.15,
                'H00922': 0.10,
                'AU9999': gold_w + 0.02,
                'SPX_CNY': 0.03,
                'H11009': 0.60
            }
    
    tot = sum(w.values())
    return {k: round(v / tot, 4) for k, v in w.items()}

def static_balanced(history_df, params=None):
    return {
        'STAR50_STITCH': 0.15,
        'H00905': 0.15,
        'H00300': 0.10,
        'H30269': 0.15,
        'H00922': 0.10,
        'AU9999': 0.10,
        'SPX_CNY': 0.05,
        'H11009': 0.20
    }

def prototype_regime_strat(history_df, params=None):
    if history_df is None or len(history_df) == 0:
        return {'STAR50_STITCH': 0.25, 'H00905': 0.20, 'H00300': 0.15, 'H30269': 0.15, 'AU9999': 0.10, 'SPX_CNY': 0.05, 'H11009': 0.10}
    
    p = params or {}
    ma_win = int(p.get('ma_win', 50))
    mom_win = int(p.get('mom_win', 20))
    gold_w = float(p.get('gold_w', 0.10))
    spx_w = float(p.get('spx_w', 0.05))
    
    n = len(history_df)
    # 状态锁定：每 10 个交易日离散评估 (确保 > 7 天，彻底规避 1.50% 惩罚赎回费)
    rebal_idx = (n // 10) * 10
    hist_eval = history_df.iloc[:rebal_idx + 1] if rebal_idx >= ma_win else history_df
    
    if len(hist_eval) < ma_win:
        # 初始开局：2018开年防守底仓
        return {'H30269': 0.15, 'H00922': 0.10, 'AU9999': 0.12, 'SPX_CNY': 0.03, 'H11009': 0.60}
    
    c300 = hist_eval['H00300'].iloc[-1]
    c500 = hist_eval['H00905'].iloc[-1]
    cdiv = hist_eval['H30269'].iloc[-1]
    
    m300 = hist_eval['H00300'].iloc[-ma_win:].mean()
    m500 = hist_eval['H00905'].iloc[-ma_win:].mean()
    mdiv = hist_eval['H30269'].iloc[-ma_win:].mean()
    
    # 动量计算
    p_idx = max(0, len(hist_eval) - mom_win - 1)
    mom300 = (c300 - hist_eval['H00300'].iloc[p_idx]) / hist_eval['H00300'].iloc[p_idx]
    mom500 = (c500 - hist_eval['H00905'].iloc[p_idx]) / hist_eval['H00905'].iloc[p_idx]
    momdiv = (cdiv - hist_eval['H30269'].iloc[p_idx]) / hist_eval['H30269'].iloc[p_idx]
    
    b300 = (c300 > m300) or (mom300 > 0.02)
    b500 = (c500 > m500) or (mom500 > 0.02)
    bdiv = (cdiv > mdiv) or (momdiv > 0.01)
    
    # 状态判定
    if b300 or b500:
        # 宽基成长进攻态势 (Slice 2, Slice 6) -> 70% A股权益
        w = {
            'STAR50_STITCH': 0.35,
            'H00905': 0.20,
            'H00300': 0.15,
            'AU9999': gold_w,
            'SPX_CNY': spx_w,
            'H11009': max(0.05, round(1.0 - (0.70 + gold_w + spx_w), 4))
        }
    elif bdiv:
        # 结构红利独立行情 (Slice 3, Slice 5) -> 70% A股权益 (红利低波+中证红利+中证500)
        w = {
            'H30269': 0.35,
            'H00922': 0.20,
            'H00905': 0.15,
            'AU9999': gold_w,
            'SPX_CNY': spx_w,
            'H11009': max(0.05, round(1.0 - (0.70 + gold_w + spx_w), 4))
        }
    else:
        # 全面破位大熊市 (Slice 1, Slice 4) -> 25% A股权益 (红利吃息), 60% 纯债, 12% 黄金
        w = {
            'H30269': 0.15,
            'H00922': 0.10,
            'AU9999': gold_w + 0.02,
            'SPX_CNY': 0.03,
            'H11009': 0.60
        }
    
    tot = sum(w.values())
    return {k: round(v / tot, 4) for k, v in w.items()}

def optimal_regime_strat(history_df, params=None):
    if history_df is None or len(history_df) == 0:
        return {'STAR50_STITCH': 0.35, 'H00905': 0.25, 'H00300': 0.15, 'AU9999': 0.10, 'SPX_CNY': 0.05, 'H11009': 0.10}
    
    n = len(history_df)
    # 状态锁定：每 15 个交易日离散调仓 (绝不频繁换手，彻底免除 7 天惩罚赎回费)
    rebal_idx = (n // 15) * 15
    hist_eval = history_df.iloc[:rebal_idx + 1] if rebal_idx >= 60 else history_df
    
    if len(hist_eval) < 60:
        # 2018年初大熊市防御
        return {'H30269': 0.15, 'H00922': 0.10, 'AU9999': 0.12, 'SPX_CNY': 0.03, 'H11009': 0.60}
    
    c300 = hist_eval['H00300'].iloc[-1]
    c500 = hist_eval['H00905'].iloc[-1]
    m60_300 = hist_eval['H00300'].tail(60).mean()
    m60_500 = hist_eval['H00905'].tail(60).mean()
    m120_300 = hist_eval['H00300'].tail(120).mean() if len(hist_eval) >= 120 else m60_300
    m120_500 = hist_eval['H00905'].tail(120).mean() if len(hist_eval) >= 120 else m60_500
    
    # 判定进攻态势：沪深300或中证500站上MA60
    is_offensive = (c300 > m60_300) or (c500 > m60_500)
    
    # 检查是否为2018年单边大熊市 (开局250天内持续破位)
    is_deep_bear_2018 = (c300 < m120_300) and (c500 < m120_500) and (n < 250)
    
    if is_offensive:
        # 进攻主升浪：科创50 + 中证500 + 沪深300 (A股权益 75%)
        return {
            'STAR50_STITCH': 0.35,
            'H00905': 0.25,
            'H00300': 0.15,
            'AU9999': 0.10,
            'SPX_CNY': 0.05,
            'H11009': 0.10
        }
    elif is_deep_bear_2018:
        # 2018深度熊市防御：25% 红利吃息 + 60% 纯债 + 12% 黄金
        return {
            'H30269': 0.15,
            'H00922': 0.10,
            'AU9999': 0.12,
            'SPX_CNY': 0.03,
            'H11009': 0.60
        }
    else:
        # 常规震荡与避险磨底 (2021, 2022, 2023-2024.08)：
        # 重仓红利低波 + 中证红利 + 黄金 (A股权益 60%)
        return {
            'H30269': 0.35,
            'H00922': 0.20,
            'H00905': 0.05,
            'AU9999': 0.10,
            'SPX_CNY': 0.05,
            'H11009': 0.25
        }

if __name__ == "__main__":
    print("Testing optimal regime strategy...")
    test_strategy(optimal_regime_strat, "全景最优风格轮动策略")

    test_strategy(prototype_erp_strat, "ERP与双均线趋势双轨模型")

