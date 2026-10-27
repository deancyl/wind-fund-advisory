"""
宏观经济、利率中枢、两融杠杆与指数估值全量采集器 (MarketDataCollector)：
采集并清洗：
1. 中美基准国债收益率与利差曲线 (2Y/5Y/10Y/30Y) -> data/macro/bond_zh_us_rate.parquet
2. 全市场两融余额与维持担保比例时序 -> data/macro/margin_trading.parquet
3. 货币供应量 M2/M1 剪刀差与官方制造业 PMI -> data/macro/money_supply.parquet, pmi.parquet
4. 核心宽基指数 (沪深300/上证50/中证500/中证1000/创业板50等) 历史 PE/PB 估值时序 -> data/mart/index_valuations.parquet
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import numpy as np
import pandas as pd
from rich.console import Console

from ..storage.lakehouse import LakehouseManager


@dataclass
class MarketSyncSummary:
    rates_rows: int
    margin_rows: int
    m2_rows: int
    pmi_rows: int
    valuation_rows: int
    updated_at: str


class MarketDataCollector:
    """宏观利率、资金杠杆与市场估值采集引擎"""

    VALUATION_INDICES = [
        ("沪深300", "000300.SH"),
        ("上证50", "000016.SH"),
        ("中证500", "000905.SH"),
        ("中证1000", "000852.SH"),
        ("创业板50", "399673.SZ"),
        ("中证800", "000906.SH"),
        ("上证红利", "000015.SH"),
        ("深证100", "399330.SZ")
    ]

    def __init__(self, lakehouse: Optional[LakehouseManager] = None):
        self.lakehouse = lakehouse or LakehouseManager()
        self.macro_dir = self.lakehouse.data_dir / "macro"
        self.mart_dir = self.lakehouse.mart_dir
        self.macro_dir.mkdir(parents=True, exist_ok=True)

        self.rates_path = self.macro_dir / "bond_zh_us_rate.parquet"
        self.margin_path = self.macro_dir / "margin_trading.parquet"
        self.m2_path = self.macro_dir / "money_supply.parquet"
        self.pmi_path = self.macro_dir / "pmi.parquet"
        self.valuation_path = self.mart_dir / "index_valuations.parquet"

    def sync_macro_rates(self) -> int:
        """采集中国与美国各期限国债收益率及中美利差"""
        import akshare as ak
        df = ak.bond_zh_us_rate()
        if df is None or df.empty:
            return 0

        df_out = pd.DataFrame()
        df_out["date"] = pd.to_datetime(df["日期"]).dt.strftime("%Y-%m-%d")

        # 中国国债收益率 (%)
        if "中国国债收益率2年" in df.columns:
            df_out["cn_yield_2y"] = df["中国国债收益率2年"].astype(float)
        if "中国国债收益率5年" in df.columns:
            df_out["cn_yield_5y"] = df["中国国债收益率5年"].astype(float)
        if "中国国债收益率10年" in df.columns:
            df_out["cn_yield_10y"] = df["中国国债收益率10年"].astype(float)
        if "中国国债收益率30年" in df.columns:
            df_out["cn_yield_30y"] = df["中国国债收益率30年"].astype(float)
        if "中国国债收益率10年-2年" in df.columns:
            df_out["cn_inversion_10_2y"] = df["中国国债收益率10年-2年"].astype(float)

        # 美国国债收益率 (%)
        if "美国国债收益率2年" in df.columns:
            df_out["us_yield_2y"] = df["美国国债收益率2年"].astype(float)
        if "美国国债收益率5年" in df.columns:
            df_out["us_yield_5y"] = df["美国国债收益率5年"].astype(float)
        if "美国国债收益率10年" in df.columns:
            df_out["us_yield_10y"] = df["美国国债收益率10年"].astype(float)
        if "美国国债收益率30年" in df.columns:
            df_out["us_yield_30y"] = df["美国国债收益率30年"].astype(float)
        if "美国国债收益率10年-2年" in df.columns:
            df_out["us_inversion_10_2y"] = df["美国国债收益率10年-2年"].astype(float)

        # 计算中美10年期国债利差 (CN - US)
        if "cn_yield_10y" in df_out.columns and "us_yield_10y" in df_out.columns:
            df_out["cn_us_spread_10y"] = (df_out["cn_yield_10y"] - df_out["us_yield_10y"]).round(4)

        df_out = df_out.sort_values("date").reset_index(drop=True)
        df_out.to_parquet(self.rates_path, index=False, engine="pyarrow")
        return len(df_out)

    def sync_margin_trading(self) -> int:
        """采集全市场两融杠杆余额与平均维持担保比例"""
        import akshare as ak
        df = ak.stock_margin_account_info()
        if df is None or df.empty:
            return 0

        df_out = pd.DataFrame()
        df_out["date"] = pd.to_datetime(df["日期"]).dt.strftime("%Y-%m-%d")

        col_map = {
            "融资余额": "margin_buy_balance",
            "融券余额": "margin_sell_balance",
            "担保物总价值": "collateral_value",
            "平均维持担保比例": "guarantee_ratio"
        }
        for k, v in col_map.items():
            if k in df.columns:
                df_out[v] = df[k].astype(float)

        if "margin_buy_balance" in df_out.columns and "margin_sell_balance" in df_out.columns:
            df_out["total_margin_balance"] = (df_out["margin_buy_balance"] + df_out["margin_sell_balance"]).round(2)

        df_out = df_out.sort_values("date").reset_index(drop=True)
        df_out.to_parquet(self.margin_path, index=False, engine="pyarrow")
        return len(df_out)

    def sync_macro_liquidity(self) -> Dict[str, int]:
        """采集 M2/M1 货币剪刀差与官方制造业 PMI"""
        import akshare as ak

        # 1. 货币供应量 M2 / M1
        df_m2 = ak.macro_china_money_supply()
        m2_len = 0
        if df_m2 is not None and not df_m2.empty:
            df_m2_out = pd.DataFrame()
            # 格式化日期 如 '2024.08' -> '2024-08'
            df_m2_out["month"] = df_m2["月份"].astype(str).str.replace("年", "-").str.replace("月份", "").str.strip()
            if "货币和准货币(M2)-数量(亿元)" in df_m2.columns:
                df_m2_out["m2_amount"] = df_m2["货币和准货币(M2)-数量(亿元)"].astype(float)
            if "货币和准货币(M2)-同比增长" in df_m2.columns:
                df_m2_out["m2_yoy"] = df_m2["货币和准货币(M2)-同比增长"].astype(float)
            if "货币(M1)-数量(亿元)" in df_m2.columns:
                df_m2_out["m1_amount"] = df_m2["货币(M1)-数量(亿元)"].astype(float)
            if "货币(M1)-同比增长" in df_m2.columns:
                df_m2_out["m1_yoy"] = df_m2["货币(M1)-同比增长"].astype(float)

            # M1 - M2 剪刀差 (%)
            if "m1_yoy" in df_m2_out.columns and "m2_yoy" in df_m2_out.columns:
                df_m2_out["m1_m2_scissors"] = (df_m2_out["m1_yoy"] - df_m2_out["m2_yoy"]).round(2)

            df_m2_out = df_m2_out.sort_values("month").reset_index(drop=True)
            df_m2_out.to_parquet(self.m2_path, index=False, engine="pyarrow")
            m2_len = len(df_m2_out)

        # 2. 制造业 PMI
        df_pmi = ak.macro_china_pmi()
        pmi_len = 0
        if df_pmi is not None and not df_pmi.empty:
            df_pmi_out = pd.DataFrame()
            df_pmi_out["month"] = df_pmi["月份"].astype(str).str.replace("年", "-").str.replace("月份", "").str.strip()
            if "制造业-指数" in df_pmi.columns:
                df_pmi_out["pmi_manufacturing"] = df_pmi["制造业-指数"].astype(float)
            if "非制造业-指数" in df_pmi.columns:
                df_pmi_out["pmi_non_manufacturing"] = df_pmi["非制造业-指数"].astype(float)

            df_pmi_out = df_pmi_out.sort_values("month").reset_index(drop=True)
            df_pmi_out.to_parquet(self.pmi_path, index=False, engine="pyarrow")
            pmi_len = len(df_pmi_out)

        return {"m2_rows": m2_len, "pmi_rows": pmi_len}

    def sync_index_valuations(self) -> int:
        """采集各大核心指数 PE-TTM 与 PB 历史估值时序"""
        import akshare as ak

        all_records = []
        for name, code in self.VALUATION_INDICES:
            try:
                df_pe = ak.stock_index_pe_lg(symbol=name)
                df_pb = ak.stock_index_pb_lg(symbol=name)
                if df_pe is None or df_pe.empty:
                    continue

                df_pe["date"] = pd.to_datetime(df_pe["日期"]).dt.strftime("%Y-%m-%d")
                df_pb["date"] = pd.to_datetime(df_pb["日期"]).dt.strftime("%Y-%m-%d")

                pe_sub = df_pe[["date", "指数", "滚动市盈率", "滚动市盈率中位数"]].copy()
                pe_sub.rename(columns={
                    "指数": "close",
                    "滚动市盈率": "pe_ttm",
                    "滚动市盈率中位数": "pe_median"
                }, inplace=True)

                pb_sub = df_pb[["date", "市净率", "市净率中位数"]].copy()
                pb_sub.rename(columns={
                    "市净率": "pb",
                    "市净率中位数": "pb_median"
                }, inplace=True)

                merged = pd.merge(pe_sub, pb_sub, on="date", how="left")
                merged["index_code"] = code
                merged["index_name"] = name
                all_records.append(merged)
            except Exception:
                continue

        if not all_records:
            return 0

        df_val = pd.concat(all_records, ignore_index=True)
        df_val["pe_ttm"] = df_val["pe_ttm"].astype(float)
        df_val["pb"] = df_val["pb"].astype(float)
        df_val = df_val.sort_values(["index_code", "date"]).reset_index(drop=True)
        df_val.to_parquet(self.valuation_path, index=False, engine="pyarrow")
        return len(df_val)

    def sync_all_market_data(self) -> MarketSyncSummary:
        """一键全量采集所有宏观利率、资金杠杆与估值数据入湖"""
        console = Console()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        console.print("[cyan]1/4 正在采集中国与美国基准国债收益率曲线 (9,000+ 条日时序)...[/cyan]")
        r_rows = self.sync_macro_rates()
        console.print(f"[green]✓ 中美利率与利差完成落盘: {r_rows:,} 条日度样本[/green]")

        console.print("[cyan]2/4 正在采集全市场两融杠杆余额与维持担保比例 (3,400+ 条时序)...[/cyan]")
        m_rows = self.sync_margin_trading()
        console.print(f"[green]✓ 两融杠杆资金数据完成落盘: {m_rows:,} 条日度样本[/green]")

        console.print("[cyan]3/4 正在采集宏观货币流动性 M2/M1 剪刀差与官方 PMI...[/cyan]")
        liq = self.sync_macro_liquidity()
        console.print(f"[green]✓ 货币与景气度完成落盘: M2 {liq['m2_rows']} 月, PMI {liq['pmi_rows']} 月[/green]")

        console.print("[cyan]4/4 正在采集核心宽基指数 (沪深300/上证50/中证500等) 历史 PE/PB 估值...[/cyan]")
        v_rows = self.sync_index_valuations()
        console.print(f"[green]✓ 核心指数历史估值完成落盘: {v_rows:,} 条估值条目[/green]")

        # 刷新视图
        self.lakehouse.init_duckdb_views()

        return MarketSyncSummary(
            rates_rows=r_rows,
            margin_rows=m_rows,
            m2_rows=liq["m2_rows"],
            pmi_rows=liq["pmi_rows"],
            valuation_rows=v_rows,
            updated_at=now_str
        )
