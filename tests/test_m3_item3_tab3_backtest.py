import pytest
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "AGY2_FundAdvisory") not in sys.path:
    sys.path.insert(0, str(ROOT / "AGY2_FundAdvisory"))

from strategy_bridge import StrategyBridge


def test_preset_combat_29_vs_6_weights_integrity():
    """验证 29 基 vs 6 基专属预设的权重求和与平账一致性"""
    preset = StrategyBridge.get_combat_29_vs_reconstructed_6_preset()
    assert "raw_29_weights" in preset
    assert "reconstructed_6_weights" in preset

    raw_29 = preset["raw_29_weights"]
    rec_6 = preset["reconstructed_6_weights"]

    assert len(raw_29) == 29
    assert len(rec_6) == 6

    # 权重严格归一化
    assert abs(sum(raw_29.values()) - 1.0) < 1e-4
    assert abs(sum(rec_6.values()) - 1.0) < 1e-4

    # 原始总市值严格平账
    assert abs(preset["total_market_value"] - 26615.10) < 0.01


def test_build_custom_portfolio_backtest_with_preset():
    """验证 29 基与 6 基同屏双曲线穿透回测"""
    preset = StrategyBridge.get_combat_29_vs_reconstructed_6_preset()
    df_bt = StrategyBridge.build_custom_portfolio_backtest(
        fund_weights=preset["reconstructed_6_weights"],
        secondary_weights=preset["raw_29_weights"],
        tier="C3"
    )

    assert "strategy_nav" in df_bt.columns
    assert "secondary_nav" in df_bt.columns
    assert "strategy_drawdown" in df_bt.columns
    assert "secondary_drawdown" in df_bt.columns

    # 验证重构 6 基净值与最大回撤表现稳健
    assert df_bt["strategy_nav"].iloc[-1] > 1.0
    assert df_bt["secondary_nav"].iloc[-1] > 1.0


def test_time_machine_dynamic_rebalance_point_in_time():
    """验证时光机在 2024-09-18 政策底拐点下的动态再平衡与向下兼容性"""
    # 1. 默认静态模式 (向后兼容)
    res_static = StrategyBridge.run_historical_time_machine_backtest(
        "2024-09-18",
        tier="C3",
        dynamic_rebalance=False
    )
    assert "kpi_3m" in res_static
    assert res_static["kpi_3m"]["net_return_pct"] > 0

    # 2. 动态再平衡模式 (Point-in-Time 零未来数据)
    res_dynamic = StrategyBridge.run_historical_time_machine_backtest(
        "2024-09-18",
        tier="C3",
        dynamic_rebalance=True
    )
    assert "kpi_3m" in res_dynamic
    # 动态调仓在 9 月下旬暴烈反转时增配弹性资产，3M 收益显著优于静态模式
    assert res_dynamic["kpi_3m"]["net_return_pct"] > res_static["kpi_3m"]["net_return_pct"]
    assert res_dynamic["kpi_3m"]["net_return_pct"] > 5.0
