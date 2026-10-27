"""
大盘估值温度计与股债性价比 (ERP) 综合测算引擎 (MarketTemperatureAnalyzer)：
根据沪深300滚动市盈率 (PE-TTM) 倒数与中国10年期国债收益率，
精确计算全历史股债性价比 (Equity Risk Premium, ERP)、PE/PB 历史分位数、
两融担保比例安全垫与大盘综合估值温度评分 (0~100 分)，
输出量化大类资产配置 (股/债/金) 仓位调优建议。
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import numpy as np
import pandas as pd

from ..storage.lakehouse import LakehouseManager


@dataclass
class MarketTemperatureReport:
    """大盘市场温度计评估报告"""
    eval_date: str
    hs300_close: float
    hs300_pe: float
    hs300_pe_percentile: float  # 0~100%
    hs300_pb: float
    hs300_pb_percentile: float  # 0~100%
    cn_10y_treasury_yield: float
    erp_value: float            # 股债性价比 (%)
    erp_percentile: float       # ERP历史分位 (%)
    margin_guarantee_ratio: float # 维持担保比例 (%)
    valuation_status: str       # 极度低估 / 偏低估 / 估值合理 / 偏高估 / 极度泡沫
    market_temperature_score: float # 0~100 分 (温度越低越便宜，温度越高越过热)
    suggested_equity_ratio: int     # 建议股票仓位比例 (%)
    suggested_bond_ratio: int       # 建议纯债仓位比例 (%)
    suggested_gold_ratio: int       # 建议黄金对冲比例 (%)
    action_advice: str              # 投顾行动建议


class MarketTemperatureAnalyzer:
    """大盘综合温度计与量化大类资产配置引擎"""

    def __init__(self, lakehouse: Optional[LakehouseManager] = None):
        self.lakehouse = lakehouse or LakehouseManager()
        self.mart_dir = self.lakehouse.mart_dir
        self.macro_dir = self.lakehouse.data_dir / "macro"
        self.output_parquet = self.mart_dir / "market_temperature.parquet"

    def evaluate(self) -> Optional[MarketTemperatureReport]:
        """
        全面评估当前大盘估值温度与股债性价比
        """
        val_path = self.mart_dir / "index_valuations.parquet"
        rates_path = self.macro_dir / "bond_zh_us_rate.parquet"
        margin_path = self.macro_dir / "margin_trading.parquet"

        if not val_path.exists() or not rates_path.exists():
            return None

        df_val = pd.read_parquet(val_path)
        df_rates = pd.read_parquet(rates_path)

        # 筛选沪深300时序
        df_300 = df_val[df_val["index_code"] == "000300.SH"].sort_values("date").reset_index(drop=True)
        if df_300.empty:
            return None

        # 1. 提取最新沪深300估值
        latest_val = df_300.iloc[-1]
        eval_date = str(latest_val["date"])
        hs300_close = float(latest_val["close"])
        hs300_pe = float(latest_val["pe_ttm"])
        hs300_pb = float(latest_val["pb"])

        # 计算 PE 和 PB 的全历史分位数 (0% ~ 100%)
        pe_series = df_300["pe_ttm"].dropna().values
        pb_series = df_300["pb"].dropna().values
        pe_pct = round(float((pe_series < hs300_pe).mean() * 100.0), 1)
        pb_pct = round(float((pb_series < hs300_pb).mean() * 100.0), 1)

        # 2. 提取最新中国10年期国债收益率
        df_rates = df_rates.sort_values("date").reset_index(drop=True)
        latest_rate_row = df_rates.iloc[-1]
        cn_10y = float(latest_rate_row.get("cn_yield_10y", 2.15))

        # 3. 测算股债性价比 (ERP)
        # ERP = (1 / PE) * 100% - 10Y_Yield
        earnings_yield = (1.0 / hs300_pe * 100.0) if hs300_pe > 0 else 0.0
        current_erp = round(earnings_yield - cn_10y, 2)

        # 对齐历史 ERP 分位数 (计算历史沪深300与国债的利差分布)
        merged_erp = pd.merge(df_300[["date", "pe_ttm"]], df_rates[["date", "cn_yield_10y"]], on="date", how="inner")
        if not merged_erp.empty:
            hist_erps = (1.0 / merged_erp["pe_ttm"].values * 100.0) - merged_erp["cn_yield_10y"].values
            erp_pct = round(float((hist_erps < current_erp).mean() * 100.0), 1)
        else:
            erp_pct = 70.0

        # 4. 提取两融维持担保比例
        guarantee_ratio = 250.0
        if margin_path.exists():
            df_margin = pd.read_parquet(margin_path)
            if not df_margin.empty and "guarantee_ratio" in df_margin.columns:
                guarantee_ratio = round(float(df_margin["guarantee_ratio"].iloc[-1]), 1)

        # 5. 综合计算大盘估值温度计分数 (0 ~ 100 分)
        # 温度定义：分数越高代表市场越过热/泡沫，分数越低代表市场越冰点/便宜
        # 权重: PE分位数 (50%) + PB分位数 (30%) + (100 - ERP分位数) (20%)
        temperature_score = round(0.50 * pe_pct + 0.30 * pb_pct + 0.20 * (100.0 - erp_pct), 1)

        # 状态判定与资产配置建议
        if temperature_score < 20.0:
            status = "历史极度低估 (冰点黄金底)"
            stock_ratio = 80
            bond_ratio = 15
            gold_ratio = 5
            advice = "市场处于全历史罕见底部，ERP性价比突破极值。建议权益类资产超配至 80%，以宽基与高弹性成长为主，耐心持有享受均值回归。"
        elif temperature_score < 40.0:
            status = "估值显著偏低 (较高性价比)"
            stock_ratio = 70
            bond_ratio = 20
            gold_ratio = 10
            advice = "大盘整体具备较优安全垫，处于战略配置中轴下方。建议保持 70% 积极股票权益仓位，重点配置沪深300及高股息红利。"
        elif temperature_score <= 60.0:
            status = "估值合理中枢 (均衡配置)"
            stock_ratio = 50
            bond_ratio = 40
            gold_ratio = 10
            advice = "估值位于历史中位水准，市场处于结构性震荡阶段。建议股债均衡配置 (50% 权益 + 40% 固收 + 10% 黄金)，防范行业分化波动。"
        elif temperature_score <= 80.0:
            status = "估值偏高 (适度防御)"
            stock_ratio = 35
            bond_ratio = 50
            gold_ratio = 15
            advice = "估值分位已进入历史中高区间，短期情绪较为亢奋。建议权益仓位降至 35%，加大中短债与纯债防守比例，增配黄金对冲。"
        else:
            status = "历史极度泡沫 (高危过热区)"
            stock_ratio = 15
            bond_ratio = 65
            gold_ratio = 20
            advice = "市场估值处于历史 80% 以上极度高估水位，ERP性价比严重透支。坚决大幅减持权益资产，防守保本，锁利并等待估值回踩。"

        report = MarketTemperatureReport(
            eval_date=eval_date,
            hs300_close=hs300_close,
            hs300_pe=round(hs300_pe, 2),
            hs300_pe_percentile=pe_pct,
            hs300_pb=round(hs300_pb, 2),
            hs300_pb_percentile=pb_pct,
            cn_10y_treasury_yield=round(cn_10y, 2),
            erp_value=current_erp,
            erp_percentile=erp_pct,
            margin_guarantee_ratio=guarantee_ratio,
            valuation_status=status,
            market_temperature_score=temperature_score,
            suggested_equity_ratio=stock_ratio,
            suggested_bond_ratio=bond_ratio,
            suggested_gold_ratio=gold_ratio,
            action_advice=advice
        )

        # 落盘到集市表
        df_mart = pd.DataFrame([{
            "eval_date": report.eval_date,
            "hs300_close": report.hs300_close,
            "hs300_pe": report.hs300_pe,
            "pe_percentile": report.hs300_pe_percentile,
            "hs300_pb": report.hs300_pb,
            "pb_percentile": report.hs300_pb_percentile,
            "cn_10y_yield": report.cn_10y_treasury_yield,
            "erp": report.erp_value,
            "erp_percentile": report.erp_percentile,
            "guarantee_ratio": report.margin_guarantee_ratio,
            "market_temperature": report.market_temperature_score,
            "valuation_status": report.valuation_status,
            "equity_ratio": report.suggested_equity_ratio,
            "bond_ratio": report.suggested_bond_ratio,
            "gold_ratio": report.suggested_gold_ratio,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }])
        df_mart.to_parquet(self.output_parquet, index=False, engine="pyarrow")
        self.lakehouse.init_duckdb_views()

        return report
