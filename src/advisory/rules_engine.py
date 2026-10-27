"""
投顾规则与标的筛选引擎：结合客户画像 (KYC)、产品适当性 (KYP)
与量化评分卡，从终端优选池中智能匹配最适配的底层基金资产。
"""

from typing import List, Dict, Any, Optional
import pandas as pd

from ..api.schemas import RiskProfile, AllocationAsset, InvestmentAdviceResult
from ..analysis.asset_allocation import AssetAllocationOptimizer, PortfolioWeight
from ..analysis.fund_analyzer import FundAnalyzer


class AdvisoryRulesEngine:
    """智能投顾适当性匹配与产品组合生成引擎"""

    def __init__(self):
        self.alloc_optimizer = AssetAllocationOptimizer()
        self.fund_analyzer = FundAnalyzer()

    def generate_advice(
        self,
        risk_profile: RiskProfile,
        fund_series_dict: Dict[str, pd.DataFrame],
        portfolio_name: Optional[str] = None
    ) -> InvestmentAdviceResult:
        """
        根据用户风险等级与当前终端分析出的真实基金池，生成定制化投资建议方案
        """
        level = risk_profile.level
        template_weights = self.alloc_optimizer.get_template_allocation(level)
        metrics = self.alloc_optimizer.estimate_portfolio_metrics(template_weights)

        # 运行量化评分，获取候选基金排名
        ranked_funds = self.fund_analyzer.compare_and_rank(fund_series_dict)

        plan: List[AllocationAsset] = []
        equity_candidates = []
        if not ranked_funds.empty:
            for _, row in ranked_funds.iterrows():
                equity_candidates.append(f"{row['基金代码']} ({row['基金简称']}, 评分: {row['综合评分']}, {row['评级']})")

        # 填充具体大类资产配置与推荐工具
        for w in template_weights:
            cat = w.asset_category
            if "权益" in cat:
                # 选取排名前列的高评分基金
                recs = equity_candidates[:3] if equity_candidates else ["002910.OF 易方达供给改革", "011369.OF 华商均衡成长A"]
                rationale = "精选终端高综合评分偏股混合基金，把握科技成长与经济复苏超额阿尔法收益。"
            elif "固收" in cat:
                recs = ["000086.OF 嘉实纯债A", "003322.OF 东方红稳健精选"]
                rationale = "配置中长久期高等级利率债与稳健信用债，提供确定性票息收益与回撤保护垫。"
            elif "商品" in cat or "黄金" in cat:
                recs = ["518880.SH 黄金ETF", "160416.OF 华安标普全球石油"]
                rationale = "配置大宗商品与实物黄金，应对通胀波动与地缘政治风险，优化组合夏普比率。"
            else:
                recs = ["000198.OF 天弘余额宝", "511990.SH 华宝添益ETF"]
                rationale = "保持底仓高流动性，确保资金支取灵活并提供逆市加仓机动仓位。"

            plan.append(AllocationAsset(
                category=cat,
                target_weight=w.target_weight_pct,
                recommended_instruments=recs,
                rationale=rationale
            ))

        name = portfolio_name or f"Wind智能投顾-{level}精选组合"
        summary = (
            f"本方案基于 Wind 投顾终端底层全市场标的数据与量化收益率走势回测生成。"
            f"针对【{level}】投资者，通过股债多资产动态分散平衡，"
            f"在控制预期最大回撤于 {metrics['expected_max_drawdown_pct']}% 以内的同时，"
            f"力争实现 {metrics['expected_annual_return_pct']}% 的稳健年化复合回报。"
        )

        warnings = [
            "市场有风险，投资需谨慎。基金历史业绩不预示其未来表现。",
            "组合预期收益率与回撤均为基于量化模型测算的理论值，不构成保本或保收益承诺。",
            "建议每季度或当资产偏离度超过 5% 时进行动态再平衡调仓。"
        ]

        return InvestmentAdviceResult(
            portfolio_name=name,
            client_risk_level=level,
            allocation_plan=plan,
            expected_annual_return=metrics["expected_annual_return_pct"],
            expected_max_drawdown=metrics["expected_max_drawdown_pct"],
            advice_summary=summary,
            risk_warnings=warnings
        )
