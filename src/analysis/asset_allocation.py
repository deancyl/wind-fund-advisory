"""
大类资产配置优化模块：支持经典资产配置模型（马科维茨均值方差、风险平价）
与财富管理投顾实务标准模型（保守/稳健/平衡/成长/进取五档矩阵）。
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np


@dataclass
class PortfolioWeight:
    asset_category: str
    target_weight_pct: float
    recommended_type: str
    risk_level: str


class AssetAllocationOptimizer:
    """大类资产配置优化器"""

    # 投顾实战基准权重矩阵
    STANDARD_TEMPLATES = {
        "保守型": [
            PortfolioWeight("现金及短融货币", 30.0, "货币基金/同业存单指数基金", "低风险 (R1)"),
            PortfolioWeight("高等级纯债与固收", 60.0, "中长债基金/短债优选", "中低风险 (R2)"),
            PortfolioWeight("对冲及抗通胀黄金", 5.0, "黄金ETF联接/抗通胀资产", "中风险 (R3)"),
            PortfolioWeight("大盘高股息权益", 5.0, "红利低波ETF/沪深300指数增强", "中高风险 (R4)"),
        ],
        "稳健型": [
            PortfolioWeight("流动性现金管理", 15.0, "优质货币/短债增强", "低风险 (R1)"),
            PortfolioWeight("核心稳健固收", 60.0, "利率债/精选信用债基金", "中低风险 (R2)"),
            PortfolioWeight("商品及黄金对冲", 10.0, "黄金ETF/全球多资产", "中风险 (R3)"),
            PortfolioWeight("核心宽基均衡权益", 15.0, "沪深300/公募偏股优选", "中高风险 (R4)"),
        ],
        "平衡型": [
            PortfolioWeight("流动性底仓", 10.0, "短债/现金管理", "低风险 (R1)"),
            PortfolioWeight("稳健压舱固收", 40.0, "二级债基/固收+", "中低风险 (R2)"),
            PortfolioWeight("大宗商品与多元资产", 10.0, "黄金/资源品类基金", "中风险 (R3)"),
            PortfolioWeight("核心成长权益", 40.0, "中证500/行业龙头/精选主动权益", "中高风险 (R4)"),
        ],
        "成长型": [
            PortfolioWeight("日常备付现金", 5.0, "高流动性货币基金", "低风险 (R1)"),
            PortfolioWeight("防守对冲固收", 25.0, "中短债/转债精选", "中低风险 (R2)"),
            PortfolioWeight("商品及替代投资", 10.0, "黄金/全球QDII", "中风险 (R3)"),
            PortfolioWeight("高景气成长权益", 60.0, "科技先锋/高端制造/优质主动权益", "高风险 (R5)"),
        ],
        "进取型": [
            PortfolioWeight("最低流动性备付", 5.0, "货币理财", "低风险 (R1)"),
            PortfolioWeight("动态辅助固收", 10.0, "可转债增强", "中风险 (R3)"),
            PortfolioWeight("多元商品期权", 5.0, "黄金/商品ETF", "中高风险 (R4)"),
            PortfolioWeight("全市场进攻权益", 80.0, "科创50/半导体智选/产业机遇主动权益", "高风险 (R5)"),
        ]
    }

    def get_template_allocation(self, risk_level: str) -> List[PortfolioWeight]:
        """获取对应风险等级的标准配置方案"""
        key = risk_level.strip()
        if key not in self.STANDARD_TEMPLATES:
            key = "平衡型"
        return self.STANDARD_TEMPLATES[key]

    def estimate_portfolio_metrics(
        self,
        weights: List[PortfolioWeight]
    ) -> Dict[str, float]:
        """
        基于资产大类历史长期经验统计，预估组合年化预期收益率与最大回撤
        """
        # 假设长期各资产大类中枢预期收益 (加权评估)
        expected_returns = {
            "现金及短融货币": 2.0, "流动性现金管理": 2.2, "流动性底仓": 2.2, "日常备付现金": 2.0, "最低流动性备付": 2.0,
            "高等级纯债与固收": 3.8, "核心稳健固收": 4.0, "稳健压舱固收": 4.8, "防守对冲固收": 4.5, "动态辅助固收": 5.2,
            "对冲及抗通胀黄金": 6.5, "商品及黄金对冲": 6.5, "大宗商品与多元资产": 7.0, "商品及替代投资": 7.0, "多元商品期权": 7.5,
            "大盘高股息权益": 8.0, "核心宽基均衡权益": 9.0, "核心成长权益": 11.0, "高景气成长权益": 13.5, "全市场进攻权益": 15.0
        }

        # 预期最大回撤中枢
        expected_drawdowns = {
            "现金及短融货币": 0.1, "流动性现金管理": 0.2, "流动性底仓": 0.2, "日常备付现金": 0.1, "最低流动性备付": 0.1,
            "高等级纯债与固收": 1.5, "核心稳健固收": 1.8, "稳健压舱固收": 4.0, "防守对冲固收": 3.5, "动态辅助固收": 5.5,
            "对冲及抗通胀黄金": 8.0, "商品及黄金对冲": 8.0, "大宗商品与多元资产": 10.0, "商品及替代投资": 10.0, "多元商品期权": 12.0,
            "大盘高股息权益": 12.0, "核心宽基均衡权益": 16.0, "核心成长权益": 22.0, "高景气成长权益": 28.0, "全市场进攻权益": 32.0
        }

        port_ret = sum(
            w.target_weight_pct / 100.0 * expected_returns.get(w.asset_category, 5.0)
            for w in weights
        )
        # 资产间低相关性分散回撤 (分散化乘数约为 0.75)
        raw_dd = sum(
            w.target_weight_pct / 100.0 * expected_drawdowns.get(w.asset_category, 10.0)
            for w in weights
        )
        port_dd = raw_dd * 0.75

        return {
            "expected_annual_return_pct": round(port_ret, 2),
            "expected_max_drawdown_pct": round(port_dd, 2)
        }
