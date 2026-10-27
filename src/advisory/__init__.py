"""
智能投顾与报告生成模块：实现投顾策略匹配引擎与结构化投资建议书生成。
"""

from .rules_engine import AdvisoryRulesEngine
from .report_generator import InvestmentReportGenerator

__all__ = ["AdvisoryRulesEngine", "InvestmentReportGenerator"]
