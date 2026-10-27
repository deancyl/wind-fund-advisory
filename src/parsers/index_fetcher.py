"""
指数全量时序拉取与实时流融合引擎 (IndexDataFetcher)：
通过多源机制（akshare 官方历史全量日K线 + Wind Speed 实时行情快照流），
实现大盘核心指数（如上证指数 000001.SH、沪深300 000300.SH 等）从创设首日至当日常态化拉取、
时序清洗、收益率衍生并持久化至 DuckDB + Parquet 本地湖仓。
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any
import numpy as np
import pandas as pd

from ..storage.lakehouse import LakehouseManager
from .speed_log_parser import WindSpeedLogParser, SpeedQuoteSnapshot


@dataclass
class IndexPullSummary:
    """指数拉取与入库结果摘要"""
    symbol: str
    name: str
    total_bars: int
    start_date: str
    end_date: str
    latest_close: float
    latest_change: float
    latest_change_pct: float
    all_time_high: float
    all_time_low: float
    parquet_path: str
    wind_live_synced: bool


class IndexDataFetcher:
    """指数数据拉取与时序湖仓沉淀引擎"""

    # 常见指数代码转换规则
    INDEX_NAME_MAP = {
        "000001.SH": "上证综合指数",
        "000300.SH": "沪深300指数",
        "000905.SH": "中证500指数",
        "000852.SH": "中证1000指数",
        "000688.SH": "上证科创板50成份指数",
        "399001.SZ": "深证成份指数",
        "399006.SZ": "创业板指数",
        "899050.BJ": "北证50成份指数"
    }

    def __init__(
        self,
        lakehouse: Optional[LakehouseManager] = None,
        speed_parser: Optional[WindSpeedLogParser] = None,
        catalog: Optional[Any] = None
    ):
        self.lakehouse = lakehouse or LakehouseManager()
        self.speed_parser = speed_parser or WindSpeedLogParser()
        self._catalog = catalog

    @staticmethod
    def normalize_symbol(symbol: str) -> str:
        """格式化为标准 Wind 风格代码，如 000001.SH"""
        clean = symbol.strip().upper()
        if "." in clean:
            return clean
        if clean.startswith("SH") or clean.startswith("SZ") or clean.startswith("BJ"):
            return f"{clean[2:]}.{clean[:2]}"
        if clean.startswith("6") or clean.startswith("000001") or clean.startswith("000"):
            return f"{clean}.SH"
        if clean.startswith("3") or clean.startswith("0"):
            return f"{clean}.SZ"
        if clean.startswith("8") or clean.startswith("4"):
            return f"{clean}.BJ"
        return f"{clean}.SH"

    @staticmethod
    def to_akshare_symbol(symbol: str) -> str:
        """转换为 akshare 需要的 symbol，如 sh000001"""
        clean = symbol.strip().upper()
        if "." in clean:
            code, market = clean.split(".", 1)
            return f"{market.lower()}{code}"
        if clean.startswith("SH") or clean.startswith("SZ") or clean.startswith("BJ"):
            return clean.lower()
        if clean.startswith("6") or clean.startswith("000001"):
            return f"sh{clean}"
        return f"sz{clean}"

    def fetch_index_kline(self, symbol: str) -> pd.DataFrame:
        """
        通过 akshare 获取指数全量历史日K线
        """
        ak_sym = self.to_akshare_symbol(symbol)
        try:
            import akshare as ak
            df = ak.stock_zh_index_daily(symbol=ak_sym)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            # 若公网请求失败，尝试从本地缓存或湖仓已有数据加载
            existing = self.lakehouse.get_index_series(self.normalize_symbol(symbol))
            if existing is not None and not existing.empty:
                return existing
            raise RuntimeError(f"拉取指数 {symbol} ({ak_sym}) 历史日K线失败: {e}")

        raise RuntimeError(f"未能获取到指数 {symbol} 的历史数据")

    def pull_and_sync_index(self, symbol: str = "000001.SH") -> IndexPullSummary:
        """
        拉取指数全量历史数据，融合 Wind 终端 Speed 实时行情快照，计算衍生指标并写入湖仓
        """
        std_sym = self.normalize_symbol(symbol)
        if self._catalog:
            index_name = self._catalog.get_name(std_sym)
        else:
            index_name = self.INDEX_NAME_MAP.get(std_sym, f"指数_{std_sym}")

        # 1. 获取历史全量日K线
        raw_df = self.fetch_index_kline(std_sym)
        df = raw_df.copy()

        # 确保基础列存在与格式化
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        df = df.sort_values("date").reset_index(drop=True)

        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                df[col] = df[col].astype(float)

        if "amount" not in df.columns:
            # 若无成交额，基于量价估算
            df["amount"] = (df["close"] * df["volume"]).round(2)
        else:
            df["amount"] = df["amount"].astype(float)

        # 2. 探测 Wind 终端最新 Speed 实时快照
        live_snapshot = self.speed_parser.get_latest_snapshot(std_sym)
        wind_live_synced = False

        if live_snapshot and live_snapshot.latest > 0:
            live_date = live_snapshot.date
            last_hist_date = df["date"].iloc[-1]

            if live_date > last_hist_date:
                # 历史数据尚未包含今日，基于 Wind 实时行情追加最新日K条目
                new_row = {
                    "date": live_date,
                    "open": live_snapshot.pre_close if live_snapshot.pre_close > 0 else live_snapshot.latest,
                    "high": max(live_snapshot.latest, live_snapshot.pre_close),
                    "low": min(live_snapshot.latest, live_snapshot.pre_close),
                    "close": live_snapshot.latest,
                    "volume": float(live_snapshot.raw_fields.get("58", 0.0)),
                    "amount": live_snapshot.amount if live_snapshot.amount > 0 else 0.0
                }
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                wind_live_synced = True
            elif live_date == last_hist_date:
                # 今日已在历史数据中，使用 Wind 官方最新确立收盘与成交额更新
                idx = len(df) - 1
                df.at[idx, "close"] = live_snapshot.latest
                if live_snapshot.amount > 0:
                    df.at[idx, "amount"] = live_snapshot.amount
                wind_live_synced = True

        # 3. 补充衍生指标
        df["index_code"] = std_sym
        df["index_name"] = index_name

        # 昨收盘价 pre_close
        df["pre_close"] = df["close"].shift(1)
        if len(df) > 0 and pd.isna(df.loc[0, "pre_close"]):
            df.loc[0, "pre_close"] = df.loc[0, "open"]

        # 涨跌额与涨跌幅 (%)
        df["change"] = (df["close"] - df["pre_close"]).round(4)
        df["change_pct"] = ((df["change"] / df["pre_close"]) * 100.0).round(4)
        df.loc[0, "change_pct"] = 0.0

        # 日度收益率 daily_return (%)
        df["daily_return"] = df["change_pct"]

        # 累计收益率 yield_pct (%) (以起始日收盘价为基准 100%)
        base_close = float(df["close"].iloc[0])
        df["yield_pct"] = (((df["close"] / base_close) - 1.0) * 100.0).round(4)

        # 4. 写入本地 Parquet 湖仓 (processed/indices/{index_code}.parquet)
        parquet_path = self.lakehouse.upsert_index_series(std_sym, df)

        # 5. 刷新 DuckDB 视图
        self.lakehouse.init_duckdb_views()

        # 6. 生成摘要报告
        latest_row = df.iloc[-1]
        summary = IndexPullSummary(
            symbol=std_sym,
            name=index_name,
            total_bars=len(df),
            start_date=str(df["date"].iloc[0]),
            end_date=str(df["date"].iloc[-1]),
            latest_close=float(latest_row["close"]),
            latest_change=float(latest_row["change"]),
            latest_change_pct=float(latest_row["change_pct"]),
            all_time_high=float(df["high"].max() if "high" in df.columns else df["close"].max()),
            all_time_low=float(df["low"].min() if "low" in df.columns else df["close"].min()),
            parquet_path=str(parquet_path),
            wind_live_synced=wind_live_synced
        )

        return summary
