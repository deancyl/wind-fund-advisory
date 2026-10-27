"""
全球宏观资产与外部联动数据全量采集器 (GlobalMarketCollector)：
采集并清洗：
1. 海外核心股指 (标普500/纳斯达克/道琼斯/恒生指数/恒生科技/日经225/台湾加权) -> data/global/global_indices.parquet
2. 全球基准汇率 (在岸人民币 USD/CNY、离岸人民币 USD/CNH、美元指数 DXY 及在离岸价差) -> data/global/fx_rates.parquet
3. 核心大宗商品 (COMEX黄金 GC、WTI原油 CL、布伦特原油 OIL、COMEX铜 HG、COMEX白银 SI) -> data/global/commodities.parquet
4. 融合本地 Wind 终端 SpeedData 实时行情流对齐最新价格。
"""

import time
import random
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import requests
import numpy as np
import pandas as pd
from rich.console import Console

from ..storage.lakehouse import LakehouseManager
from .speed_log_parser import WindSpeedLogParser


@dataclass
class GlobalSyncSummary:
    indices_rows: int
    fx_rows: int
    commodities_rows: int
    updated_at: str


class GlobalMarketCollector:
    """全球宏观资产全量采集与实时流对齐引擎"""

    OVERSEAS_INDICES = [
        {"code": "SPX", "name": "标普500", "source": "us", "symbol": ".INX", "wind_symbol": "SPX.GI"},
        {"code": "IXIC", "name": "纳斯达克", "source": "us", "symbol": ".IXIC", "wind_symbol": "IXIC.GI"},
        {"code": "DJI", "name": "道琼斯", "source": "us", "symbol": ".DJI", "wind_symbol": "DJI.GI"},
        {"code": "HSI", "name": "恒生指数", "source": "hk", "symbol": "HSI", "wind_symbol": "HSI.HI"},
        {"code": "HSTECH", "name": "恒生科技", "source": "hk", "symbol": "HSTECH", "wind_symbol": "HSTECH.HI"},
        {"code": "N225", "name": "日经225", "source": "global", "symbol": "日经225指数", "wind_symbol": "N225.GI"},
        {"code": "TWII", "name": "台湾加权", "source": "global", "symbol": "中国台湾加权指数", "wind_symbol": "TWII.TW"}
    ]

    COMMODITY_SYMBOLS = [
        {"code": "GC", "name": "COMEX黄金", "symbol": "GC", "wind_symbol": "GC.CMX"},
        {"code": "CL", "name": "WTI原油", "symbol": "CL", "wind_symbol": "CL.NYM"},
        {"code": "OIL", "name": "布伦特原油", "symbol": "OIL", "wind_symbol": "B.IPE"},
        {"code": "HG", "name": "COMEX高级铜", "symbol": "HG", "wind_symbol": "CA.LME"},
        {"code": "SI", "name": "COMEX白银", "symbol": "SI", "wind_symbol": "SI.CMX"}
    ]

    def __init__(self, lakehouse: Optional[LakehouseManager] = None):
        self.lakehouse = lakehouse or LakehouseManager()
        self.global_dir = self.lakehouse.data_dir / "global"
        self.global_dir.mkdir(parents=True, exist_ok=True)

        self.indices_path = self.global_dir / "global_indices.parquet"
        self.fx_path = self.global_dir / "fx_rates.parquet"
        self.commodities_path = self.global_dir / "commodities.parquet"

        self.speed_parser = WindSpeedLogParser()
        self.console = Console()

    def _sleep_jitter(self, base_delay: float = 1.2):
        jitter = random.uniform(0.3, 0.8)
        time.sleep(base_delay + jitter)

    def _get_speed_realtime_quotes(self) -> Dict[str, Dict[str, Any]]:
        """从本地 Wind SpeedData_*.log 提取最新实时行情"""
        try:
            return self.speed_parser.extract_market_quotes()
        except Exception:
            return {}

    # ------------------------------------------------------------------
    # 1. 全球海外股指 (标普500/纳指/道指/恒生/恒科/日经/台湾)
    # ------------------------------------------------------------------

    def sync_global_indices(self, delay: float = 1.2) -> int:
        """全量同步海外核心股指日 K 线"""
        import akshare as ak

        all_dfs = []
        realtime_map = self._get_speed_realtime_quotes()

        for item in self.OVERSEAS_INDICES:
            code = item["code"]
            name = item["name"]
            source = item["source"]
            sym = item["symbol"]
            wind_sym = item["wind_symbol"]

            self.console.print(f"[cyan]正在同步全球股指: [bold]{name} ({code})[/bold] ...[/cyan]")
            df_item = None

            for attempt in range(1, 4):
                try:
                    if source == "us":
                        df_item = ak.index_us_stock_sina(symbol=sym)
                    elif source == "hk":
                        df_item = ak.stock_hk_index_daily_sina(symbol=sym)
                    elif source == "global":
                        df_item = ak.index_global_hist_sina(symbol=sym)
                    if df_item is not None and not df_item.empty:
                        break
                except Exception as e:
                    backoff = attempt * 2.5
                    self.console.print(f"[yellow]  ! 抓取 {name} 失败 (重试 {attempt}/3): {e}，休眠 {backoff:.1f}s[/yellow]")
                    time.sleep(backoff)

            if df_item is None or df_item.empty:
                self.console.print(f"[red]  × 获取 {name} 失败，跳过[/red]")
                continue

            # 字段标准化
            df_norm = pd.DataFrame()
            date_col = "date" if "date" in df_item.columns else "日期"
            df_norm["date"] = pd.to_datetime(df_item[date_col]).dt.strftime("%Y-%m-%d")
            df_norm["index_code"] = code
            df_norm["index_name"] = name

            for target_col, candidates in [
                ("open", ["open", "开盘价", "今开"]),
                ("high", ["high", "最高价", "最高"]),
                ("low", ["low", "最低价", "最低"]),
                ("close", ["close", "收盘价", "最新价", "收盘"]),
                ("volume", ["volume", "成交量", "成交额"])
            ]:
                found = False
                for c in candidates:
                    if c in df_item.columns:
                        df_norm[target_col] = pd.to_numeric(df_item[c], errors="coerce")
                        found = True
                        break
                if not found:
                    df_norm[target_col] = 0.0

            df_norm = df_norm.sort_values("date").reset_index(drop=True)
            df_norm["daily_return"] = (df_norm["close"].pct_change() * 100.0).fillna(0.0).round(4)

            # 融合本地 Wind 终端实时流对齐最新价
            if wind_sym in realtime_map:
                quote = realtime_map[wind_sym]
                today_str = datetime.now().strftime("%Y-%m-%d")
                rt_price = quote.get("price")
                if rt_price and rt_price > 0:
                    if not df_norm.empty and df_norm.iloc[-1]["date"] == today_str:
                        df_norm.at[df_norm.index[-1], "close"] = rt_price
                    else:
                        prev_close = df_norm.iloc[-1]["close"] if not df_norm.empty else rt_price
                        rt_ret = round((rt_price / prev_close - 1.0) * 100.0, 4) if prev_close > 0 else 0.0
                        new_row = pd.DataFrame([{
                            "date": today_str,
                            "index_code": code,
                            "index_name": name,
                            "open": rt_price,
                            "high": rt_price,
                            "low": rt_price,
                            "close": rt_price,
                            "volume": 0.0,
                            "daily_return": rt_ret
                        }])
                        df_norm = pd.concat([df_norm, new_row], ignore_index=True)

            all_dfs.append(df_norm)
            self._sleep_jitter(delay)

        if not all_dfs:
            return 0

        merged_indices = pd.concat(all_dfs, ignore_index=True)
        merged_indices = merged_indices.drop_duplicates(subset=["index_code", "date"], keep="last")
        merged_indices = merged_indices.sort_values(["index_code", "date"]).reset_index(drop=True)
        merged_indices.to_parquet(self.indices_path, index=False, engine="pyarrow")

        self.console.print(f"[bold green]✓ 全球股指同步完成: 共 {len(merged_indices)} 条日 K 线记录[/bold green]")
        return len(merged_indices)

    # ------------------------------------------------------------------
    # 2. 全球基准汇率 (在岸/离岸/在离岸价差/美元指数 DXY)
    # ------------------------------------------------------------------

    def _fetch_sina_fx_kline(self, symbol: str) -> pd.DataFrame:
        """从新浪外汇历史 K 线接口抓取完整日线"""
        url = f"https://vip.stock.finance.sina.com.cn/forex/api/jsonp.php/var%20_kline=/NewForexService.getDayKLine?symbol={symbol}"
        headers = {"Referer": "https://finance.sina.com.cn"}
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        text = res.text

        match = re.search(r'\("([^"]+)"\)', text)
        if not match:
            return pd.DataFrame()

        data_str = match.group(1).strip()
        lines = data_str.split("|")
        records = []
        for line in lines:
            parts = line.strip().split(",")
            if len(parts) >= 5:
                records.append({
                    "date": parts[0],
                    "open": float(parts[1]),
                    "low": float(parts[2]),
                    "high": float(parts[3]),
                    "close": float(parts[4])
                })
        return pd.DataFrame(records)

    def sync_fx_rates(self, delay: float = 1.2) -> int:
        """全量同步全球基准汇率 (USD/CNY, USD/CNH, DXY) 及在离岸价差"""
        self.console.print("[cyan]正在同步全球外汇时序 (在岸人民币、离岸人民币、美元指数 DXY) ...[/cyan]")

        # 1. 在岸人民币 (USD/CNY)
        df_cny = pd.DataFrame()
        try:
            df_cny = self._fetch_sina_fx_kline("fx_susdcny")
        except Exception as e:
            self.console.print(f"[yellow]  ! 抓取在岸人民币时序失败: {e}[/yellow]")

        self._sleep_jitter(delay)

        # 2. 离岸人民币 (USD/CNH)
        df_cnh = pd.DataFrame()
        try:
            df_cnh = self._fetch_sina_fx_kline("fx_susdcnh")
        except Exception as e:
            self.console.print(f"[yellow]  ! 抓取离岸人民币时序失败: {e}[/yellow]")

        self._sleep_jitter(delay)

        # 3. 美元指数 (DXY)
        df_dxy = pd.DataFrame()
        try:
            df_dxy = self._fetch_sina_fx_kline("DINIW")
        except Exception as e:
            self.console.print(f"[yellow]  ! 抓取美元指数时序失败: {e}[/yellow]")

        if df_cny.empty and df_cnh.empty and df_dxy.empty:
            self.console.print("[red]  × 获取外汇时序失败，跳过[/red]")
            return 0

        # 合并各外汇资产为日度宽表
        df_cny = df_cny.rename(columns={"close": "usd_cny", "open": "usd_cny_open", "high": "usd_cny_high", "low": "usd_cny_low"})
        df_cnh = df_cnh.rename(columns={"close": "usd_cnh", "open": "usd_cnh_open", "high": "usd_cnh_high", "low": "usd_cnh_low"})
        df_dxy = df_dxy.rename(columns={"close": "dxy_close", "open": "dxy_open", "high": "dxy_high", "low": "dxy_low"})

        merged_fx = pd.merge(df_cny[["date", "usd_cny"]], df_cnh[["date", "usd_cnh"]], on="date", how="outer")
        merged_fx = pd.merge(merged_fx, df_dxy[["date", "dxy_close"]], on="date", how="outer")
        merged_fx = merged_fx.sort_values("date").reset_index(drop=True)

        # 前向填充缺失值以对齐非交易日
        merged_fx["usd_cny"] = merged_fx["usd_cny"].ffill()
        merged_fx["usd_cnh"] = merged_fx["usd_cnh"].ffill()
        merged_fx["dxy_close"] = merged_fx["dxy_close"].ffill()

        # 计算在离岸汇率差 (CNH - CNY，正值代表离岸更弱/贬值压力，负值代表离岸升值预期)
        merged_fx["cnh_cny_spread"] = (merged_fx["usd_cnh"] - merged_fx["usd_cny"]).round(5)

        # 计算人民币日收益率（USD/CNY 下跌代表人民币升值，上涨代表贬值）
        merged_fx["usd_cny_return"] = (merged_fx["usd_cny"].pct_change() * 100.0).fillna(0.0).round(4)
        merged_fx["dxy_return"] = (merged_fx["dxy_close"].pct_change() * 100.0).fillna(0.0).round(4)

        # 过滤有效日期区间 (至少从 2015 年开始有完整连续数据)
        merged_fx = merged_fx[merged_fx["date"] >= "2015-01-01"].reset_index(drop=True)
        merged_fx.to_parquet(self.fx_path, index=False, engine="pyarrow")

        self.console.print(f"[bold green]✓ 全球汇率时序同步完成: 共 {len(merged_fx)} 交易日样本[/bold green]")
        return len(merged_fx)

    # ------------------------------------------------------------------
    # 3. 核心大宗商品 (COMEX黄金/美原油/布油/铜/白银)
    # ------------------------------------------------------------------

    def sync_commodities(self, delay: float = 1.2) -> int:
        """全量同步全球大宗商品期货日 K 线"""
        import akshare as ak

        all_dfs = []
        realtime_map = self._get_speed_realtime_quotes()

        for item in self.COMMODITY_SYMBOLS:
            code = item["code"]
            name = item["name"]
            sym = item["symbol"]
            wind_sym = item["wind_symbol"]

            self.console.print(f"[cyan]正在同步大宗商品: [bold]{name} ({code})[/bold] ...[/cyan]")
            df_item = None

            for attempt in range(1, 4):
                try:
                    df_item = ak.futures_foreign_hist(symbol=sym)
                    if df_item is not None and not df_item.empty:
                        break
                except Exception as e:
                    backoff = attempt * 2.5
                    self.console.print(f"[yellow]  ! 抓取 {name} 失败 (重试 {attempt}/3): {e}，休眠 {backoff:.1f}s[/yellow]")
                    time.sleep(backoff)

            if df_item is None or df_item.empty:
                self.console.print(f"[red]  × 获取 {name} 失败，跳过[/red]")
                continue

            df_norm = pd.DataFrame()
            df_norm["date"] = pd.to_datetime(df_item["date"]).dt.strftime("%Y-%m-%d")
            df_norm["commodity_code"] = code
            df_norm["commodity_name"] = name
            df_norm["open"] = pd.to_numeric(df_item.get("open", 0.0), errors="coerce").fillna(0.0)
            df_norm["high"] = pd.to_numeric(df_item.get("high", 0.0), errors="coerce").fillna(0.0)
            df_norm["low"] = pd.to_numeric(df_item.get("low", 0.0), errors="coerce").fillna(0.0)
            df_norm["close"] = pd.to_numeric(df_item.get("close", 0.0), errors="coerce").fillna(0.0)
            df_norm["volume"] = pd.to_numeric(df_item.get("volume", 0.0), errors="coerce").fillna(0.0)

            df_norm = df_norm.sort_values("date").reset_index(drop=True)
            df_norm["daily_return"] = (df_norm["close"].pct_change() * 100.0).fillna(0.0).round(4)

            # 对齐 Wind 实时行情
            if wind_sym in realtime_map:
                quote = realtime_map[wind_sym]
                today_str = datetime.now().strftime("%Y-%m-%d")
                rt_price = quote.get("price")
                if rt_price and rt_price > 0:
                    if not df_norm.empty and df_norm.iloc[-1]["date"] == today_str:
                        df_norm.at[df_norm.index[-1], "close"] = rt_price
                    else:
                        prev_close = df_norm.iloc[-1]["close"] if not df_norm.empty else rt_price
                        rt_ret = round((rt_price / prev_close - 1.0) * 100.0, 4) if prev_close > 0 else 0.0
                        new_row = pd.DataFrame([{
                            "date": today_str,
                            "commodity_code": code,
                            "commodity_name": name,
                            "open": rt_price,
                            "high": rt_price,
                            "low": rt_price,
                            "close": rt_price,
                            "volume": 0.0,
                            "daily_return": rt_ret
                        }])
                        df_norm = pd.concat([df_norm, new_row], ignore_index=True)

            all_dfs.append(df_norm)
            self._sleep_jitter(delay)

        if not all_dfs:
            return 0

        merged_comm = pd.concat(all_dfs, ignore_index=True)
        merged_comm = merged_comm.drop_duplicates(subset=["commodity_code", "date"], keep="last")
        merged_comm = merged_comm.sort_values(["commodity_code", "date"]).reset_index(drop=True)
        merged_comm.to_parquet(self.commodities_path, index=False, engine="pyarrow")

        self.console.print(f"[bold green]✓ 全球大宗商品同步完成: 共 {len(merged_comm)} 条日 K 线记录[/bold green]")
        return len(merged_comm)

    # ------------------------------------------------------------------
    # 一键全量同步与 DuckDB 视图自动更新
    # ------------------------------------------------------------------

    def sync_all_global_data(self, delay: float = 1.2) -> GlobalSyncSummary:
        """一键全量采集所有外部资产并刷新湖仓 DuckDB 视图"""
        indices_rows = self.sync_global_indices(delay=delay)
        fx_rows = self.sync_fx_rates(delay=delay)
        comm_rows = self.sync_commodities(delay=delay)

        self.lakehouse.init_duckdb_views()

        summary = GlobalSyncSummary(
            indices_rows=indices_rows,
            fx_rows=fx_rows,
            commodities_rows=comm_rows,
            updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        return summary
