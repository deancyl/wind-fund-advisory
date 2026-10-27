"""
数据模型定义：公募基金概览、收益走势、客户风险画像与投顾建议结构体。
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class FundYieldPoint(BaseModel):
    date: str
    yield_pct: float


class FundOverview(BaseModel):
    wind_code: str
    name: str
    fund_type: Optional[str] = "混合型"
    annualized_yield_1y: Optional[float] = None
    annualized_yield_3y: Optional[float] = None
    max_drawdown_1y: Optional[float] = None
    sharpe_ratio_1y: Optional[float] = None
    fund_manager: Optional[str] = None
    asset_scale_billion: Optional[float] = None


class RiskProfile(BaseModel):
    level: str = Field(description="风险等级: 保守型/稳健型/平衡型/成长型/进取型")
    horizon_months: int = Field(default=12, description="投资期限 (月)")
    target_annual_return: Optional[float] = Field(default=8.0, description="目标年化收益率 %")
    max_acceptable_loss: Optional[float] = Field(default=10.0, description="最大可承受亏损 %")


class AllocationAsset(BaseModel):
    category: str
    target_weight: float
    recommended_instruments: List[str]
    rationale: str


class InvestmentAdviceResult(BaseModel):
    portfolio_name: str
    client_risk_level: str
    allocation_plan: List[AllocationAsset]
    expected_annual_return: float
    expected_max_drawdown: float
    advice_summary: str
    risk_warnings: List[str]
