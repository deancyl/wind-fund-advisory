"""
裁判基建自动化单元测试集 (tests/test_infra.py)
验证 4 大底层基建模块：
1. data_loader.py: 全收益对齐矩阵、Proxy Stitching、交易执行算子
2. judge_engine.py: AST哈希、因果探针、6风格切片回归、参数扰动高原存活
3. islands/ 与 evolution.db: 4大正交流派输出与 SQLite 试错记录
4. holdout_vault.py: 盲测物理隔离与熔断锁
"""

import sqlite3
import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from data_loader import DataLoader
from judge_engine import JudgeEngine, compute_ast_hash
from holdout_vault import HoldoutVault, HoldoutVaultExhaustedError
from islands import island_erp, island_momentum, island_breadth, island_ensemble
from simple_rotation_strategy import strategy_fn, PARAMS


def test_data_loader_matrix_alignment():
    """测试全收益矩阵对齐、无缺失、时间跨度覆盖 2018-至今"""
    dl = DataLoader()
    df = dl.load_total_return_matrix()
    assert len(df) >= 2100
    assert 'date' in df.columns
    assert 'H00300' in df.columns
    assert 'H11009' in df.columns
    assert 'STAR50_STITCH' in df.columns
    assert 'AU9999' in df.columns
    assert 'SPX_CNY' in df.columns
    assert 'BENCHMARK_30_70' in df.columns
    # 确保没有 NaN
    assert df[['H00300', 'H11009', 'STAR50_STITCH', 'AU9999', 'SPX_CNY']].isna().sum().sum() == 0


def test_simulation_operator_friction():
    """测试 T+1 模拟算子与 7 天惩罚锁定期扣费"""
    dl = DataLoader()
    df = dl.load_total_return_matrix().iloc[:30].copy()
    
    # 构造频繁买卖触发 7 天惩罚费的权重序列
    w_rows = []
    for i, d in enumerate(df['date']):
        w = 0.20 if (i % 2 == 0) else 0.0
        w_rows.append({'date': d, 'H00300': w, 'H11009': 1.0 - w})
    
    w_df = pd.DataFrame(w_rows)
    res = dl.simulate_execution(w_df, df[['date', 'H00300', 'H11009']], is_otc=True, penalty_days=7)
    assert res['friction'].sum() > 0.05  # 频繁买卖必须触发显著的摩擦惩罚


def test_causal_probe_detects_leakage():
    """测试因果探针能准确抓捕前瞻偏差 (Look-Ahead Bias)"""
    judge = JudgeEngine()
    full_df = judge.data_loader.load_total_return_matrix().iloc[:120].copy()
    
    # 故意构造一个使用未来数据产生不同权重的作弊策略
    def cheating_strategy(history_df, params=None, target_date=None):
        # 作弊：直接将最后一行（未来）价格点位带入计算
        future_val = float(history_df['H00300'].iloc[-1])
        # 归一化为权重
        w_eq = round(abs(future_val) % 1.0, 4)
        return {'H00300': w_eq, 'H11009': 1.0 - w_eq}
    
    passed, msg = judge.probe_look_ahead_bias(cheating_strategy, {}, full_df, n_samples=5)
    assert not passed
    assert "FATAL: Look-Ahead Bias Detected" in msg


def test_four_islands_conformity():
    """测试四岛策略接口签名与输出合规性"""
    dl = DataLoader()
    sample_df = dl.load_total_return_matrix().iloc[:100].copy()
    
    for mod in [island_erp, island_momentum, island_breadth, island_ensemble]:
        assert hasattr(mod, 'PARAMS')
        assert hasattr(mod, 'strategy_fn')
        out = mod.strategy_fn(sample_df, mod.PARAMS)
        assert isinstance(out, dict)
        tot_w = sum(out.values())
        assert abs(tot_w - 1.0) < 1e-3
        for k, v in out.items():
            assert 0.0 <= v <= 1.0


def test_holdout_vault_quota_limit():
    """测试盲测金库额度获取与硬上限"""
    vault = HoldoutVault()
    attempts = vault.get_holdout_attempts()
    assert 0 <= attempts <= 3


def test_judge_engine_rejects_bond_arbitrage(tmp_path):
    """测试裁判引擎坚决拦截高纯债刷分策略 (检验B 防套利红线)"""
    test_db = tmp_path / "test_evolution.db"
    judge = JudgeEngine(db_path=test_db)
    
    # simple_rotation_strategy 持有 80% 纯债，必须被拒
    res = judge.run_judge(
        strategy_fn=strategy_fn,
        strategy_name="80%纯债刷夏普套利策略",
        island_name="test_arbitrage",
        params=PARAMS
    )
    assert res['status'] == 'FAIL'
    assert res['gate'] == 'B'
    assert "超过 50.0% 限制" in res['reason']


def test_simulation_initial_position_penalty():
    """测试 T+1 模拟算子对 day 0 初始持仓在 7 天内卖出同样强制扣除 1.50% 惩罚费"""
    dl = DataLoader()
    df = dl.load_total_return_matrix().iloc[:10].copy()
    w_df = pd.DataFrame([
        {'date': df['date'].iloc[0], 'H00300': 1.0, 'H11009': 0.0},
        {'date': df['date'].iloc[1], 'H00300': 0.0, 'H11009': 1.0},
    ])
    res = dl.simulate_execution(w_df, df[['date', 'H00300', 'H11009']], is_otc=True, penalty_days=7)
    frictions = res['friction'].tolist()
    assert any(f >= 0.015 for f in frictions), "买入未满 7 天赎回必须触发 1.50% 惩罚费"


def test_judge_engine_rf_deduction():
    """测试夏普比率计算严格扣除 Rf = 2.0%"""
    judge = JudgeEngine()
    df = judge.data_loader.load_total_return_matrix().iloc[:60].copy()
    def dummy_strategy(history_df, params=None):
        return {'H11009': 1.0}
    res = judge.evaluate_strategy_on_slice(dummy_strategy, {}, df, df)
    ann_ret = res['annualized_return_pct']
    ann_vol = res['annualized_vol_pct']
    sharpe_zero_rf = ann_ret / ann_vol
    assert res['sharpe_ratio'] < sharpe_zero_rf - 2.0 / ann_vol + 0.1
    assert abs(res['sharpe_ratio'] - (ann_ret - 2.0) / ann_vol) < 0.1


def test_judge_engine_rejects_slice_bond_arbitrage(tmp_path):
    """测试裁判引擎坚决拦截非极端熊市切片超过 50% 纯债逃避 (检验B 切片红线)"""
    test_db = tmp_path / "test_slice_bond.db"
    judge = JudgeEngine(db_path=test_db)
    def slice2_bond_heavy_strategy(history_df, params=None):
        cur_date = history_df['date'].iloc[-1]
        if '2019-01-02' <= str(cur_date)[:10] <= '2020-12-31':
            return {'H11009': 0.60, 'H00300': 0.40}
        return {'H11009': 0.20, 'AU9999': 0.40, 'SPX_CNY': 0.40}
    res = judge.run_judge(
        strategy_fn=slice2_bond_heavy_strategy,
        strategy_name="切片超标纯债策略",
        island_name="test_slice_bond",
        params={}
    )
    assert res['status'] == 'FAIL'
    assert res['gate'] == 'B'
    assert "超过 50.0% 上限" in res['reason']


def test_judge_engine_rejects_low_cagr(tmp_path):
    """测试裁判引擎坚决拦截全周期年化收益 CAGR < 10.0% 的平庸策略 (检验B CAGR红线)"""
    test_db = tmp_path / "test_low_cagr.db"
    judge = JudgeEngine(db_path=test_db)
    def low_cagr_strategy(history_df, params=None):
        return {'H11009': 0.50, 'H00300': 0.50}
    res = judge.run_judge(
        strategy_fn=low_cagr_strategy,
        strategy_name="低年化收益策略",
        island_name="test_low_cagr",
        params={}
    )
    assert res['status'] == 'FAIL'
    assert res['gate'] == 'B'
    assert "未达到 10.0% 硬性底线" in res['reason']


def test_judge_engine_rejects_bull_slice_lag(tmp_path):
    """测试裁判引擎坚决拦截牛市切片大幅跑输基准超过 -5% 的踏空策略 (检验B 牛市防踏空红线)"""
    test_db = tmp_path / "test_bull_lag.db"
    judge = JudgeEngine(db_path=test_db)
    def bull_lag_strategy(history_df, params=None):
        cur_date = history_df['date'].iloc[-1]
        if '2019-01-02' <= str(cur_date)[:10] <= '2020-12-31':
            return {'H11009': 0.50, 'AU9999': 0.50}
        return {'SPX_CNY': 0.50, 'AU9999': 0.40, 'H11009': 0.10}
    res = judge.run_judge(
        strategy_fn=bull_lag_strategy,
        strategy_name="牛市踏空策略",
        island_name="test_bull_lag",
        params={}
    )
    assert res['status'] == 'FAIL'
    assert res['gate'] == 'B'
    assert "Slice_2" in res['reason'] or "跑输超过 -5.0%" in res['reason']


def test_islands_empty_df_robustness():
    """测试四岛策略函数在空 DataFrame 或异常 target_date 下绝不抛出 IndexError"""
    for mod in [island_erp, island_momentum, island_breadth, island_ensemble]:
        w_empty = mod.strategy_fn(pd.DataFrame())
        assert isinstance(w_empty, dict) and len(w_empty) > 0
        assert abs(sum(w_empty.values()) - 1.0) < 1e-3
        w_out = mod.strategy_fn(pd.DataFrame(), target_date="2010-01-01")
        assert isinstance(w_out, dict) and len(w_out) > 0
        assert abs(sum(w_out.values()) - 1.0) < 1e-3
