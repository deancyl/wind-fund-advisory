"""
单只公募基金全历史日净值时序拉取器 (FundNAVFetcher)：
基于 akshare 接口拉取基金自创设首日至今的完整单位净值 (NAV) 与累计净值时序，
计算日收益率与累计复权收益，并写入 processed/funds/{symbol}.parquet 本地列式湖仓。
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import numpy as np
import pandas as pd

from ..storage.lakehouse import LakehouseManager


@dataclass
class FundNAVSummary:
    """基金历史净值拉取摘要"""
    symbol: str
    fund_name: str
    total_nav_days: int
    start_date: str
    end_date: str
    latest_unit_nav: float
    latest_cum_nav: float
    latest_daily_return: float
    all_time_high_nav: float
    parquet_path: str


class FundNAVFetcher:
    """单只基金净值拉取与时序处理引擎"""

    def __init__(self, lakehouse: Optional[LakehouseManager] = None):
        self.lakehouse = lakehouse or LakehouseManager()

    @staticmethod
    def normalize_code(symbol: str) -> str:
        """格式化为 6 位纯数字，如 '000001'"""
        clean = symbol.strip().upper()
        if "." in clean:
            clean = clean.split(".")[0]
        return clean.zfill(6)

    def fetch_fund_nav(self, symbol: str, fund_name: Optional[str] = None) -> FundNAVSummary:
        """
        拉取单只基金的全量单位净值与累计净值历史时序
        """
        code = self.normalize_code(symbol)
        std_sym = f"{code}.OF"

        import akshare as ak

        # 1. 获取单位净值走势
        try:
            df_unit = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
        except Exception as e:
            raise RuntimeError(f"获取基金 {code} 单位净值走势失败: {e}")

        if df_unit is None or df_unit.empty:
            raise RuntimeError(f"基金 {code} 单位净值数据为空")

        df_unit["date"] = pd.to_datetime(df_unit["净值日期"]).dt.strftime("%Y-%m-%d")
        df_unit["unit_nav"] = df_unit["单位净值"].astype(float)
        df_unit["daily_return"] = df_unit["日增长率"].astype(float) if "日增长率" in df_unit.columns else 0.0

        # 2. 尝试获取累计净值走势并对齐
        try:
            df_cum = ak.fund_open_fund_info_em(symbol=code, indicator="累计净值走势")
            if df_cum is not None and not df_cum.empty:
                df_cum["date"] = pd.to_datetime(df_cum["净值日期"]).dt.strftime("%Y-%m-%d")
                df_cum["cum_nav"] = df_cum["累计净值"].astype(float)
                df_merged = pd.merge(df_unit[["date", "unit_nav", "daily_return"]], df_cum[["date", "cum_nav"]], on="date", how="left")
                df_merged["cum_nav"] = df_merged["cum_nav"].ffill().bfill()
            else:
                df_merged = df_unit[["date", "unit_nav", "daily_return"]].copy()
                df_merged["cum_nav"] = df_merged["unit_nav"]
        except Exception:
            df_merged = df_unit[["date", "unit_nav", "daily_return"]].copy()
            df_merged["cum_nav"] = df_merged["unit_nav"]

        # 3. 补充标准字段
        df_merged = df_merged.sort_values("date").reset_index(drop=True)
        df_merged["symbol"] = std_sym
        name = fund_name or f"公募基金_{code}"
        df_merged["fund_name"] = name

        # 累计收益率 yield_pct (以成立首日为基准)
        base_nav = float(df_merged["cum_nav"].iloc[0])
        if base_nav > 0:
            df_merged["yield_pct"] = (((df_merged["cum_nav"] / base_nav) - 1.0) * 100.0).round(4)
        else:
            df_merged["yield_pct"] = 0.0

        # 4. 落盘至 processed/funds/{symbol}.parquet
        p_path = self.lakehouse.upsert_fund_series(std_sym, df_merged)

        # 5. 刷新视图
        self.lakehouse.init_duckdb_views()

        latest_row = df_merged.iloc[-1]
        return FundNAVSummary(
            symbol=std_sym,
            fund_name=name,
            total_nav_days=len(df_merged),
            start_date=str(df_merged["date"].iloc[0]),
            end_date=str(df_merged["date"].iloc[-1]),
            latest_unit_nav=float(latest_row["unit_nav"]),
            latest_cum_nav=float(latest_row["cum_nav"]),
            latest_daily_return=float(latest_row["daily_return"]),
            all_time_high_nav=float(df_merged["cum_nav"].max()),
            parquet_path=str(p_path)
        )
