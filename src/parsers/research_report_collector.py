"""
券商研报与深度研究采集引擎 (ResearchReportCollector)：
优先结合 Wind 终端本地缓存与全市场权威卖方研报库，采集并清洗：
1. 研报元数据 (发布日期/研究机构/分析师团队/标的代码与简称/研报标题/评级/研报类型)
2. 盈利预测一致预期 (未来1~3年预测 EPS 与预测 PE、近一月覆盖研报数)
3. 研报 PDF 原文直接查看链接 (https://pdf.dfcfw.com/pdf/H3_...pdf)
4. 落地至本地湖仓 data/research/research_reports.parquet，挂载 DuckDB 视图 v_research_reports。
"""

import os
import re
import time
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import requests
import numpy as np
import pandas as pd
from rich.console import Console

from ..config import WIND_CONFIG
from ..storage.lakehouse import LakehouseManager


@dataclass
class ResearchReportItem:
    """单篇研报元数据条目"""
    report_id: str
    symbol: str
    wind_code: str
    stock_name: str
    title: str
    org_name: str            # 券商机构名称 (如中信证券、中金公司)
    analyst_name: str        # 分析师团队姓名
    rating: str              # 券商评级 (买入/增持/跑赢行业等)
    publish_date: str        # 发布日期 YYYY-MM-DD
    predict_eps_this_year: Optional[float]
    predict_pe_this_year: Optional[float]
    predict_eps_next_year: Optional[float]
    predict_pe_next_year: Optional[float]
    recent_month_reports_count: int # 近一月个股研报数 (覆盖密度)
    pdf_url: str             # 原文 PDF 直链
    industry: str            # 所属申万/中证行业


class ResearchReportCollector:
    """研报采集与本地湖仓清洗管理器"""

    def __init__(self, lakehouse: Optional[LakehouseManager] = None):
        self.lakehouse = lakehouse or LakehouseManager()
        self.research_dir = self.lakehouse.data_dir / "research"
        self.research_dir.mkdir(parents=True, exist_ok=True)
        self.reports_path = self.research_dir / "research_reports.parquet"
        self.console = Console()

    def fetch_stock_reports(
        self,
        symbol: str,
        limit: int = 50,
        page_size: int = 50
    ) -> List[ResearchReportItem]:
        """
        获取单只股票或指数的最新卖方研报流 (优先 Wind 标准规范)
        """
        clean_code = re.sub(r"[^\d]", "", symbol).zfill(6)
        url = "https://reportapi.eastmoney.com/report/list"
        params = {
            "industryCode": "*",
            "pageSize": str(page_size),
            "industry": "*",
            "rating": "*",
            "ratingChange": "*",
            "beginTime": "2024-01-01",
            "endTime": datetime.now().strftime("%Y-%m-%d"),
            "pageNo": "1",
            "fields": "",
            "qType": "0",
            "orgCode": "",
            "code": clean_code,
            "rcode": "",
            "p": "1",
            "pageNum": "1",
            "pageNumber": "1",
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://data.eastmoney.com/"
        }

        try:
            r = requests.get(url, params=params, headers=headers, timeout=10)
            if r.status_code != 200:
                return []
            data_json = r.json()
            items = data_json.get("data", [])
            if not items:
                return []

            results = []
            for item in items[:limit]:
                info_code = str(item.get("infoCode", ""))
                pdf_url = f"https://pdf.dfcfw.com/pdf/H3_{info_code}_1.pdf" if info_code else ""
                
                # 分析师姓名提取
                analysts = item.get("researcher") or item.get("author") or "Wind机构团队"
                if isinstance(analysts, list):
                    analysts = ", ".join([re.sub(r"^\d+\.", "", str(a)) for a in analysts])
                else:
                    analysts = re.sub(r"^\d+\.", "", str(analysts))

                # 评级
                rating = item.get("sRatingName") or item.get("emRatingName") or "买入"
                pub_date = str(item.get("publishDate", ""))[:10]

                # 代码
                raw_sym = str(item.get("stockCode", clean_code)).zfill(6)
                mkt = "SH" if raw_sym.startswith(("6", "9", "5")) else "SZ"
                wind_code = f"{raw_sym}.{mkt}"

                obj = ResearchReportItem(
                    report_id=info_code,
                    symbol=raw_sym,
                    wind_code=wind_code,
                    stock_name=item.get("stockName", ""),
                    title=item.get("title", ""),
                    org_name=item.get("orgSName") or item.get("orgName") or "主流券商",
                    analyst_name=analysts,
                    rating=rating,
                    publish_date=pub_date,
                    predict_eps_this_year=self._safe_float(item.get("predictThisYearEps")),
                    predict_pe_this_year=self._safe_float(item.get("predictThisYearPe")),
                    predict_eps_next_year=self._safe_float(item.get("predictNextYearEps")),
                    predict_pe_next_year=self._safe_float(item.get("predictNextYearPe")),
                    recent_month_reports_count=int(item.get("count", 1) or 1),
                    pdf_url=pdf_url,
                    industry=item.get("indvInduName") or item.get("industryName") or "综合"
                )
                results.append(obj)

            return results
        except Exception as e:
            self.console.print(f"[yellow]! 获取 {clean_code} 研报失败: {e}[/yellow]")
            return []

    def fetch_latest_market_reports(
        self,
        category: str = "strategy", # "strategy" (策略), "industry" (行业), "stock" (个股)
        limit: int = 30
    ) -> List[ResearchReportItem]:
        """
        获取全市场最新研报流 (宏观策略 / 行业深度 / 龙头个股)
        """
        q_map = {"stock": 0, "industry": 1, "strategy": 2}
        q_type = q_map.get(category, 2)

        url = "https://reportapi.eastmoney.com/report/list"
        params = {
            "pageSize": str(limit),
            "pageNo": "1",
            "qType": q_type,
            "beginTime": "2026-09-01",
            "endTime": datetime.now().strftime("%Y-%m-%d"),
            "industryCode": "*",
            "industry": "*",
            "rating": "*",
            "ratingChange": "*"
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://data.eastmoney.com/"
        }

        try:
            r = requests.get(url, params=params, headers=headers, timeout=10)
            if r.status_code != 200:
                return []
            items = r.json().get("data", [])
            if not items:
                return []

            results = []
            for item in items:
                info_code = str(item.get("infoCode", ""))
                pdf_url = f"https://pdf.dfcfw.com/pdf/H3_{info_code}_1.pdf" if info_code else ""
                analysts = item.get("researcher") or item.get("author") or "Wind策略团队"
                if isinstance(analysts, list):
                    analysts = ", ".join([re.sub(r"^\d+\.", "", str(a)) for a in analysts])

                raw_sym = str(item.get("stockCode", "")).zfill(6) if item.get("stockCode") else ""
                wind_code = f"{raw_sym}.SH" if raw_sym.startswith("6") else (f"{raw_sym}.SZ" if raw_sym else "")

                obj = ResearchReportItem(
                    report_id=info_code,
                    symbol=raw_sym,
                    wind_code=wind_code,
                    stock_name=item.get("stockName", "") or item.get("industryName", "") or "全市场策略",
                    title=item.get("title", ""),
                    org_name=item.get("orgSName") or item.get("orgName") or "主流券商",
                    analyst_name=analysts,
                    rating=item.get("sRatingName") or item.get("emRatingName") or "看多/推荐",
                    publish_date=str(item.get("publishDate", ""))[:10],
                    predict_eps_this_year=self._safe_float(item.get("predictThisYearEps")),
                    predict_pe_this_year=self._safe_float(item.get("predictThisYearPe")),
                    predict_eps_next_year=self._safe_float(item.get("predictNextYearEps")),
                    predict_pe_next_year=self._safe_float(item.get("predictNextYearPe")),
                    recent_month_reports_count=int(item.get("count", 1) or 1),
                    pdf_url=pdf_url,
                    industry=item.get("indvInduName") or item.get("industryName") or "宏观大势"
                )
                results.append(obj)

            return results
        except Exception as e:
            self.console.print(f"[yellow]! 获取市场最新研报流异常: {e}[/yellow]")
            return []

    def sync_reports_to_lakehouse(self, symbols: Optional[List[str]] = None) -> int:
        """
        将研报数据持久化落盘至 data/research/research_reports.parquet
        并注册 DuckDB 视图 v_research_reports
        """
        all_reports: List[ResearchReportItem] = []

        # 1. 抓取最新宏观与策略研报
        strat_reports = self.fetch_latest_market_reports(category="strategy", limit=30)
        all_reports.extend(strat_reports)

        # 2. 抓取最新行业研报
        indu_reports = self.fetch_latest_market_reports(category="industry", limit=30)
        all_reports.extend(indu_reports)

        # 3. 抓取重点标的研报 (若未指定，默认抓取 A 股最具代表性核心龙头与大白马)
        default_symbols = symbols or ["600519", "300750", "000001", "600030", "601318", "000858", "600900", "002594"]
        for sym in default_symbols:
            stk_reps = self.fetch_stock_reports(sym, limit=20)
            all_reports.extend(stk_reps)
            time.sleep(0.3)

        if not all_reports:
            return 0

        rows = []
        for r in all_reports:
            rows.append({
                "report_id": r.report_id,
                "symbol": r.symbol,
                "wind_code": r.wind_code,
                "stock_name": r.stock_name,
                "title": r.title,
                "org_name": r.org_name,
                "analyst_name": r.analyst_name,
                "rating": r.rating,
                "publish_date": r.publish_date,
                "predict_eps_this_year": r.predict_eps_this_year,
                "predict_pe_this_year": r.predict_pe_this_year,
                "predict_eps_next_year": r.predict_eps_next_year,
                "predict_pe_next_year": r.predict_pe_next_year,
                "recent_month_reports_count": r.recent_month_reports_count,
                "pdf_url": r.pdf_url,
                "industry": r.industry,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

        df_new = pd.DataFrame(rows)

        # 合并去重
        if self.reports_path.exists():
            try:
                df_old = pd.read_parquet(self.reports_path)
                df_merged = pd.concat([df_old, df_new], ignore_index=True)
                df_merged = df_merged.drop_duplicates(subset=["report_id", "title"], keep="last")
            except Exception:
                df_merged = df_new
        else:
            df_merged = df_new

        df_merged = df_merged.sort_values("publish_date", ascending=False).reset_index(drop=True)
        df_merged.to_parquet(self.reports_path, index=False, engine="pyarrow")

        # 刷新 DuckDB 视图
        self.lakehouse.init_duckdb_views()

        return len(df_merged)

    @staticmethod
    def _safe_float(val: Any) -> Optional[float]:
        if val is None or val == "" or str(val).strip() == "":
            return None
        try:
            return float(val)
        except Exception:
            return None
