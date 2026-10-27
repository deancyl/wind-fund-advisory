"""
CEF 缓存解析器：从终端 Chromium 磁盘缓存与 LevelDB 提取最近加载的公募基金净值走势、
评级、图表及实时资讯。
"""

import os
import gzip
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import pandas as pd

from ..config import WIND_CONFIG


class CEFCacheParser:
    """Chromium 浏览器缓存与本地持久化数据解析器"""

    def __init__(self, cache_dir: Optional[Union[str, Path]] = None):
        self.cache_dir = Path(cache_dir) if cache_dir else WIND_CONFIG.cef_cache_dir

    def extract_fund_yield_charts(self) -> Dict[str, pd.DataFrame]:
        """
        提取缓存中保存的所有公募基金净值与累计收益率时序数据。
        返回字典: { "基金代码": DataFrame(date, yield_pct, fund_name) }
        """
        fund_series = {}
        if not self.cache_dir.exists():
            return fund_series

        for fpath in self.cache_dir.glob("f_*"):
            try:
                with open(fpath, "rb") as f:
                    data = f.read()

                # 判断是否包含 {"data":
                idx = data.find(b'{"data":')
                if idx == -1:
                    continue

                end = data.rfind(b"}")
                if end <= idx:
                    continue

                json_raw = data[idx:end + 1].decode("utf-8", errors="ignore")
                parsed = json.loads(json_raw)

                raw_data = parsed.get("data")
                if not isinstance(raw_data, dict):
                    continue

                # 遍历基金标的
                for fund_code, series_list in raw_data.items():
                    if not isinstance(series_list, list) or not series_list:
                        continue

                    info = series_list[0]
                    fund_name = info.get("name", "")
                    pts = info.get("data", [])

                    if not pts:
                        continue

                    records = []
                    for pt in pts:
                        # x: 毫秒时间戳, y: 累计收益率%
                        ts = pt.get("x")
                        y_val = pt.get("y")
                        if ts is not None and y_val is not None:
                            d_str = pd.to_datetime(ts, unit="ms").strftime("%Y-%m-%d")
                            records.append({
                                "date": d_str,
                                "yield_pct": float(y_val),
                                "fund_code": fund_code,
                                "fund_name": fund_name
                            })

                    if records:
                        df = pd.DataFrame(records).sort_values("date").reset_index(drop=True)
                        fund_series[fund_code] = df
            except Exception:
                continue

        return fund_series

    def extract_cached_news(self, limit: int = 50) -> List[Dict[str, Any]]:
        """提取缓存中的金融研报与要闻快讯"""
        news_list = []
        if not self.cache_dir.exists():
            return news_list

        for fpath in self.cache_dir.glob("f_*"):
            try:
                with open(fpath, "rb") as f:
                    data = f.read()

                if b"news.windin.com" in data or b"snap.windin.com" in data:
                    idx = data.find(b'{"data":')
                    if idx != -1:
                        end = data.rfind(b"}")
                        raw = data[idx:end + 1].decode("utf-8", errors="ignore")
                        parsed = json.loads(raw)
                        data_inner = parsed.get("data")
                        if isinstance(data_inner, str):
                            data_inner = json.loads(data_inner)
                        docs = data_inner.get("response", {}).get("result", {}).get("docs", [])
                        for doc in docs:
                            news_list.append({
                                "date": doc.get("date", [""])[0],
                                "title": doc.get("title", [""])[0],
                                "source": doc.get("sourcename", ["Wind"])[0],
                                "windcodes": doc.get("windcode", []),
                            })
                            if len(news_list) >= limit:
                                return news_list
            except Exception:
                continue

        return news_list
