"""
公募基金全市场代码字典与全景宏观集市构建器 (FundCatalogManager)：
一键抓取并清洗全市场约 28,000+ 只公募基金主档案、
20,000+ 只开放式基金全周期业绩排行榜、
18,000+ 只基金权威评级 (晨星/济安/招商/上证)、
36,000+ 条基金经理任职履历与在管规模、
1,700+ 只场内 ETF 基金名录，
落盘至 DuckDB + Parquet 本地湖仓 master 与 mart 体系。
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import pandas as pd
from rich.console import Console

from ..storage.lakehouse import LakehouseManager


@dataclass
class FundCatalogSummary:
    """基金全景档案同步结果摘要"""
    total_funds: int
    ranked_funds: int
    rated_funds: int
    total_managers: int
    total_etfs: int
    updated_at: str
    catalog_path: str
    rank_path: str
    ratings_path: str
    managers_path: str
    etf_path: str


class FundCatalogManager:
    """公募基金全景数据库同步与集市管理器"""

    def __init__(self, lakehouse: Optional[LakehouseManager] = None):
        self.lakehouse = lakehouse or LakehouseManager()
        self.master_dir = self.lakehouse.master_dir
        self.mart_dir = self.lakehouse.mart_dir

        self.catalog_path = self.master_dir / "fund_catalog.parquet"
        self.rank_path = self.mart_dir / "fund_performance_snapshot.parquet"
        self.ratings_path = self.mart_dir / "fund_ratings.parquet"
        self.managers_path = self.master_dir / "fund_managers.parquet"
        self.etf_path = self.master_dir / "etf_catalog.parquet"

    def sync_all_catalog_tables(self, force: bool = False) -> FundCatalogSummary:
        """
        拉取并沉淀全市场五大基金全景数据宽表
        """
        console = Console()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        import akshare as ak

        # 1. 全市场基金主代码字典 (fund_name_em)
        console.print("[cyan]1/5 正在拉取全市场公募基金主代码档案库 (约 28,000+ 只)...[/cyan]")
        df_catalog = ak.fund_name_em()
        df_catalog.rename(columns={
            "基金代码": "symbol",
            "拼音缩写": "pinyin_abbr",
            "基金简称": "fund_name",
            "基金类型": "fund_type",
            "拼音全称": "pinyin_full"
        }, inplace=True)
        # 标准化 6 位代码
        df_catalog["symbol"] = df_catalog["symbol"].astype(str).str.zfill(6)
        # 添加标准后缀标识
        df_catalog["std_symbol"] = df_catalog["symbol"] + ".OF"
        df_catalog.to_parquet(self.catalog_path, index=False, engine="pyarrow")
        console.print(f"[green]✓ 基金主代码库完成落盘: {len(df_catalog):,} 只标的[/green]")

        # 2. 全市场基金最新净值与全周期业绩排行榜 (fund_open_fund_rank_em)
        console.print("[cyan]2/5 正在拉取开放式基金全周期业绩排行与最新快照 (约 20,000+ 只)...[/cyan]")
        df_rank = ak.fund_open_fund_rank_em(symbol="全部")
        df_rank.rename(columns={
            "基金代码": "symbol",
            "基金简称": "fund_name",
            "日期": "nav_date",
            "单位净值": "unit_nav",
            "累计净值": "cum_nav",
            "日增长率": "daily_return",
            "近1周": "return_1w",
            "近1月": "return_1m",
            "近3月": "return_3m",
            "近6月": "return_6m",
            "近1年": "return_1y",
            "近2年": "return_2y",
            "近3年": "return_3y",
            "今年来": "return_ytd",
            "成立来": "return_since_inception",
            "手续费": "purchase_fee"
        }, inplace=True)
        df_rank["symbol"] = df_rank["symbol"].astype(str).str.zfill(6)
        df_rank["std_symbol"] = df_rank["symbol"] + ".OF"
        df_rank.to_parquet(self.rank_path, index=False, engine="pyarrow")
        console.print(f"[green]✓ 业绩排行快照完成落盘: {len(df_rank):,} 只标的[/green]")

        # 3. 全市场基金多机构权威综合评级 (fund_rating_all)
        console.print("[cyan]3/5 正在拉取晨星、济安金信、招商、上证权威评级 (约 18,000+ 只)...[/cyan]")
        try:
            df_rating = ak.fund_rating_all()
            df_rating.rename(columns={
                "代码": "symbol",
                "简称": "fund_name",
                "基金经理": "fund_manager",
                "基金公司": "company",
                "上海证券": "rating_sh",
                "招商证券": "rating_zs",
                "济安金信": "rating_ja",
                "晨星评级": "rating_morningstar",
                "手续费": "fee",
                "类型": "type"
            }, inplace=True)
            df_rating["symbol"] = df_rating["symbol"].astype(str).str.zfill(6)
            df_rating["std_symbol"] = df_rating["symbol"] + ".OF"
            df_rating.to_parquet(self.ratings_path, index=False, engine="pyarrow")
            console.print(f"[green]✓ 权威综合评级完成落盘: {len(df_rating):,} 只标的[/green]")
            rated_count = len(df_rating)
        except Exception as e:
            console.print(f"[yellow]! 评级数据拉取异常: {e}[/yellow]")
            rated_count = 0

        # 4. 全市场基金经理任职履历与在管规模 (fund_manager_em)
        console.print("[cyan]4/5 正在拉取全国公募基金经理履历与在管资产档案 (约 36,000+ 条记录)...[/cyan]")
        try:
            df_mgr = ak.fund_manager_em()
            df_mgr.rename(columns={
                "姓名": "manager_name",
                "所属公司": "company",
                "现任基金代码": "fund_code",
                "现任基金": "fund_name",
                "累计从业时间": "career_days",
                "现任基金资产总规模": "aum_billion",
                "现任基金最佳回报": "best_return_pct"
            }, inplace=True)
            df_mgr["fund_code"] = df_mgr["fund_code"].astype(str).str.zfill(6)
            df_mgr["std_symbol"] = df_mgr["fund_code"] + ".OF"
            df_mgr.to_parquet(self.managers_path, index=False, engine="pyarrow")
            console.print(f"[green]✓ 基金经理全景档案完成落盘: {len(df_mgr):,} 条履历映射[/green]")
            mgr_count = len(df_mgr)
        except Exception as e:
            console.print(f"[yellow]! 基金经理档案拉取异常: {e}[/yellow]")
            mgr_count = 0

        # 5. 场内 ETF 基金名录 (fund_etf_category_sina)
        console.print("[cyan]5/5 正在拉取全市场场内 ETF 基金名录与实时行情 (约 1,700+ 只)...[/cyan]")
        try:
            df_etf = ak.fund_etf_category_sina(symbol="ETF基金")
            df_etf.rename(columns={
                "代码": "ak_symbol",
                "名称": "etf_name",
                "最新价": "price",
                "涨跌额": "change",
                "涨跌幅": "change_pct",
                "成交量": "volume",
                "成交额": "amount"
            }, inplace=True)
            df_etf.to_parquet(self.etf_path, index=False, engine="pyarrow")
            console.print(f"[green]✓ 场内 ETF 档案完成落盘: {len(df_etf):,} 只标的[/green]")
            etf_count = len(df_etf)
        except Exception as e:
            console.print(f"[yellow]! 场内 ETF 名录拉取异常: {e}[/yellow]")
            etf_count = 0

        # 6. 刷新 DuckDB 视图
        self.lakehouse.init_duckdb_views()

        return FundCatalogSummary(
            total_funds=len(df_catalog),
            ranked_funds=len(df_rank),
            rated_funds=rated_count,
            total_managers=mgr_count,
            total_etfs=etf_count,
            updated_at=now_str,
            catalog_path=str(self.catalog_path),
            rank_path=str(self.rank_path),
            ratings_path=str(self.ratings_path),
            managers_path=str(self.managers_path),
            etf_path=str(self.etf_path)
        )
