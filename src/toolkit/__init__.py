"""
Wind 投顾终端统一工具包 (Toolkit):
提供面向生产的 Python SDK 与全景投顾能力支持。
"""

from .unified_sdk import WindToolkit
from .user_watchlist import UserWatchlistParser, WatchlistItem
from .financials import FinancialsCollector, FinancialMetricRecord, DividendRecord
from .money_flow import MoneyFlowCollector, SectorMoneyFlowRecord
from .bonds import ChinaBondYieldCollector, YieldCurveSnapshot
from .etf import ETFFlowCollector, ETFFlowRecord

__all__ = [
    "WindToolkit",
    "UserWatchlistParser",
    "WatchlistItem",
    "FinancialsCollector",
    "FinancialMetricRecord",
    "DividendRecord",
    "MoneyFlowCollector",
    "SectorMoneyFlowRecord",
    "ChinaBondYieldCollector",
    "YieldCurveSnapshot",
    "ETFFlowCollector",
    "ETFFlowRecord",
]
