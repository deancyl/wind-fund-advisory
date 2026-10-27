"""
基金深度诊断与评分分析器：基于真实净值走势计算综合雷达评分、抗风险韧性与性价比。
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import pandas as pd

from .metrics import (
    calculate_cumulative_to_daily_returns,
    calculate_annualized_return,
    calculate_annualized_volatility,
    calculate_max_drawdown,
    calculate_sharpe_ratio,
    calculate_calmar_ratio,
)


@dataclass
class FundScoreCard:
    fund_code: str
    fund_name: str
    total_score: float  # 0 - 100
    profitability_score: float  # 盈利能力得分
    risk_adjusted_score: float  # 风险调整收益得分
    defense_score: float  # 回撤防御得分
    cumulative_return: float  # 区间累计收益率 %
    annualized_return: float  # 年化收益率 %
    annualized_volatility: float  # 年化波动率 %
    max_drawdown: float  # 最大回撤 %
    sharpe_ratio: float  # 夏普比率
    calmar_ratio: float  # 卡玛比率
    rating: str  # 评级: 卓越 (5星) / 优异 (4星) / 稳健 (3星) / 观望 (2星) / 谨慎 (1星)


class FundAnalyzer:
    """基金诊断与多维度评分引擎"""

    def analyze_single_fund(self, fund_code: str, df: pd.DataFrame) -> Optional[FundScoreCard]:
        """
        对单只基金的时序数据进行全面量化体检
        df 必须包含 'yield_pct' (累计收益率 %) 与 'date'
        """
        if df.empty or len(df) < 5 or "yield_pct" not in df.columns:
            return None

        fund_name = df["fund_name"].iloc[0] if "fund_name" in df.columns else fund_code
        cum_ret = float(df["yield_pct"].iloc[-1])
        total_days = len(df)

        daily_ret = calculate_cumulative_to_daily_returns(df["yield_pct"])
        ann_ret = calculate_annualized_return(cum_ret, total_days)
        ann_vol = calculate_annualized_volatility(daily_ret)
        max_dd, _, _ = calculate_max_drawdown(df["yield_pct"])
        sharpe = calculate_sharpe_ratio(daily_ret)
        calmar = calculate_calmar_ratio(ann_ret, max_dd)

        # 评分算法 (0-100 归一化)
        # 1. 盈利能力 (年化收益权重): 0-30% 映射到 0-100
        p_score = min(max((ann_ret + 10.0) / 40.0 * 100.0, 0.0), 100.0)

        # 2. 风险调整收益 (Sharpe 权重): Sharpe 0 到 2.5 映射到 0-100
        ra_score = min(max(sharpe / 2.5 * 100.0, 0.0), 100.0)

        # 3. 回撤防御能力: 回撤越小得分越高 (回撤 5% 得 100分，35% 得 0分)
        def_score = min(max((35.0 - max_dd) / 30.0 * 100.0, 0.0), 100.0)

        # 综合加权总分: 收益 35% + 性价比 35% + 防御 30%
        total_score = round(p_score * 0.35 + ra_score * 0.35 + def_score * 0.30, 1)

        # 评定等级
        if total_score >= 85:
            rating = "卓越 (★★★★★)"
        elif total_score >= 70:
            rating = "优异 (★★★★☆)"
        elif total_score >= 55:
            rating = "稳健 (★★★☆☆)"
        elif total_score >= 40:
            rating = "观望 (★★☆☆☆)"
        else:
            rating = "谨慎 (★☆☆☆☆)"

        return FundScoreCard(
            fund_code=fund_code,
            fund_name=fund_name,
            total_score=total_score,
            profitability_score=round(p_score, 1),
            risk_adjusted_score=round(ra_score, 1),
            defense_score=round(def_score, 1),
            cumulative_return=round(cum_ret, 2),
            annualized_return=ann_ret,
            annualized_volatility=ann_vol,
            max_drawdown=max_dd,
            sharpe_ratio=sharpe,
            calmar_ratio=calmar,
            rating=rating
        )

    def compare_and_rank(self, fund_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """批量比对所有基金并输出排序报表"""
        cards = []
        for code, df in fund_dict.items():
            card = self.analyze_single_fund(code, df)
            if card:
                cards.append({
                    "基金代码": card.fund_code,
                    "基金简称": card.fund_name,
                    "综合评分": card.total_score,
                    "评级": card.rating,
                    "区间收益%": card.cumulative_return,
                    "年化收益%": card.annualized_return,
                    "年化波动%": card.annualized_volatility,
                    "最大回撤%": card.max_drawdown,
                    "夏普比率": card.sharpe_ratio,
                    "卡玛比率": card.calmar_ratio,
                })

        if not cards:
            return pd.DataFrame()

        df_rank = pd.DataFrame(cards).sort_values("综合评分", ascending=False).reset_index(drop=True)
        return df_rank
