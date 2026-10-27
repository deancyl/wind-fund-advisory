"""
量化分析与投研模型模块：涵盖业绩基准指标、基金多维诊断评分、资产配置与投资策略多维胜率分析器。
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
from .benchmark import BenchmarkManager
from .winrate_analyzer import WinRateAnalyzer, StrategyWinRateResult, PeriodWinRate, DCAWinRate
from .market_temperature import MarketTemperatureAnalyzer, MarketTemperatureReport
from .global_linkage_analyzer import GlobalLinkageAnalyzer, GlobalLinkageMetrics
from .between_the_lines_analyzer import BetweenTheLinesAnalyzer, BetweenTheLinesResult
from .portfolio_analyzer import (
    PortfolioAnalyzer,
    PortfolioAsset,
    PortfolioMetrics,
    DiversificationMetrics,
    AttributionItem,
    OptimizationProposal,
    PortfolioAnalysisResult,
    PortfolioDataLoader
)

from .quarterly_backtest_model import (
    QuarterlyBacktestEngine,
    QuarterlyStepRecord,
    RollingWinRate,
    RegimePerformance,
    StrategyBacktestSummary
)

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
    "PortfolioWeight",
    "BenchmarkManager",
    "WinRateAnalyzer",
    "StrategyWinRateResult",
    "PeriodWinRate",
    "DCAWinRate",
    "MarketTemperatureAnalyzer",
    "MarketTemperatureReport",
    "GlobalLinkageAnalyzer",
    "GlobalLinkageMetrics",
    "BetweenTheLinesAnalyzer",
    "BetweenTheLinesResult",
    "PortfolioAnalyzer",
    "PortfolioAsset",
    "PortfolioMetrics",
    "DiversificationMetrics",
    "AttributionItem",
    "OptimizationProposal",
    "PortfolioAnalysisResult",
    "PortfolioDataLoader",
    "QuarterlyBacktestEngine",
    "QuarterlyStepRecord",
    "RollingWinRate",
    "RegimePerformance",
    "StrategyBacktestSummary"
]
