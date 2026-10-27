"""
量化分析与投研模型模块：涵盖业绩基准指标、基金多维诊断评分与资产配置优化算法。
"""

from .metrics import (
    calculate_annualized_return,
    calculate_annualized_volatility,
    calculate_max_drawdown,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_calmar_ratio,
    calculate_alpha_beta
)
from .fund_analyzer import FundAnalyzer, FundScoreCard
from .asset_allocation import AssetAllocationOptimizer, PortfolioWeight

__all__ = [
    "calculate_annualized_return",
    "calculate_annualized_volatility",
    "calculate_max_drawdown",
    "calculate_sharpe_ratio",
    "calculate_sortino_ratio",
    "calculate_calmar_ratio",
    "calculate_alpha_beta",
    "FundAnalyzer",
    "FundScoreCard",
    "AssetAllocationOptimizer",
    "PortfolioWeight"
]
