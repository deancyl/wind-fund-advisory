"""
Wind 投顾终端统一 Python 工具包 (WindToolkit SDK):
提供面向生产的统一、全景投顾量化与终端数据访问接口：
- watchlist: 投顾自选资产、历史调阅流与工作台配置探索
- financials: 上市公司/基金 F10 财务指标、杜邦分析与分红送配
- money_flow: 申万/万得行业板块主力资金流向与订单拆解
- bonds: 中债国债收益率曲线、期限利差与信用利差
- etf: 场内 ETF 份额规模与估算资金流动追踪
- lakehouse: DuckDB + Parquet 本地统一湖仓与即席 SQL 查询
- terminal: Wind 客户端进程探针、Session 鉴权与配置管理
- speed_stream: 终端 Speed 实时行情快照逆向提取流
"""

from typing import Dict, List, Optional, Any, Union
import pandas as pd
from rich.console import Console

from .user_watchlist import UserWatchlistParser
from .financials import FinancialsCollector
from .money_flow import MoneyFlowCollector
from .bonds import ChinaBondYieldCollector
from .etf import ETFFlowCollector
from ..storage.lakehouse import LakehouseManager
from ..config import WIND_CONFIG, WindConfig
from ..core.session_manager import SessionManager
from ..core.terminal_probe import TerminalProbe
from ..parsers.speed_log_parser import WindSpeedLogParser
from ..parsers.master_dict_parser import MasterDictParser
from ..parsers.research_report_collector import ResearchReportCollector
from ..analysis.between_the_lines_analyzer import BetweenTheLinesAnalyzer
from ..analysis.market_temperature import MarketTemperatureAnalyzer
from ..analysis.portfolio_analyzer import PortfolioAnalyzer


class WindToolkit:
    """
    Wind 投顾终端一体化生产级 SDK 入口。
    
    使用范式:
        from src.toolkit import WindToolkit
        
        wk = WindToolkit()
        
        # 1. 自选与工作台探索
        df_fav = wk.watchlist.build_consolidated_watchlist()
        
        # 2. F10 财务与分红
        df_fin = wk.financials.fetch_stock_financials("600519")
        dupont = wk.financials.get_dupont_analysis("600519")
        df_div = wk.financials.fetch_dividends("600519")
        
        # 3. 行业板块资金流向
        df_flow = wk.money_flow.get_top_inflow_sectors(top_n=10)
        
        # 4. 中债收益率曲线与利差
        curve = wk.bonds.get_latest_yield_curve()
        spreads = wk.bonds.get_term_spreads_analysis()
        
        # 5. ETF 份额与资金流动
        df_etf = wk.etf.get_top_inflow_etfs(top_n=10)
        
        # 6. 本地湖仓即席 SQL 查询
        df_res = wk.query("SELECT * FROM v_sector_money_flow LIMIT 5")
    """

    def __init__(
        self,
        config: Optional[WindConfig] = None,
        lakehouse: Optional[LakehouseManager] = None
    ):
        self.config = config or WIND_CONFIG
        self.lakehouse = lakehouse or LakehouseManager()

        # 核心扩展工具模块 (懒加载 / 单例化)
        self._watchlist: Optional[UserWatchlistParser] = None
        self._financials: Optional[FinancialsCollector] = None
        self._money_flow: Optional[MoneyFlowCollector] = None
        self._bonds: Optional[ChinaBondYieldCollector] = None
        self._etf: Optional[ETFFlowCollector] = None

        # 基础底层服务
        self.terminal_probe = TerminalProbe(self.config)
        self.session_mgr = SessionManager(self.config)
        self.speed_parser = WindSpeedLogParser(self.config.root_dir / "log" / "Speed" if self.config.root_dir else None)
        self.master_dict = MasterDictParser(self.config.code_cache_path)
        self.reports_collector = ResearchReportCollector(lakehouse=self.lakehouse)

    @property
    def watchlist(self) -> UserWatchlistParser:
        if self._watchlist is None:
            self._watchlist = UserWatchlistParser(
                users_dir=self.config.users_dir,
                lakehouse=self.lakehouse,
                master_dict=self.master_dict
            )
        return self._watchlist

    @property
    def financials(self) -> FinancialsCollector:
        if self._financials is None:
            self._financials = FinancialsCollector(lakehouse=self.lakehouse)
        return self._financials

    @property
    def money_flow(self) -> MoneyFlowCollector:
        if self._money_flow is None:
            self._money_flow = MoneyFlowCollector(lakehouse=self.lakehouse)
        return self._money_flow

    @property
    def bonds(self) -> ChinaBondYieldCollector:
        if self._bonds is None:
            self._bonds = ChinaBondYieldCollector(lakehouse=self.lakehouse)
        return self._bonds

    @property
    def etf(self) -> ETFFlowCollector:
        if self._etf is None:
            self._etf = ETFFlowCollector(lakehouse=self.lakehouse)
        return self._etf

    def query(self, sql: str) -> pd.DataFrame:
        """使用 DuckDB 对湖仓执行即席 SQL 查询"""
        return self.lakehouse.query_sql(sql)

    def sync_all(self, force: bool = False) -> Dict[str, int]:
        """
        一键批量增量同步全量扩展数据集入湖：
        1. 用户自选与工作台标的
        2. 核心标的 F10 财务与分红
        3. 行业板块主力资金流向
        4. 中债收益率曲线与利差
        5. ETF 份额与资金流动
        """
        console = Console()
        console.print("[cyan]🚀 开始执行 Wind 扩展投顾数据集全量增量入湖...[/cyan]")
        results = {}

        # 1. 自选
        try:
            n_wl = self.watchlist.sync_to_lakehouse()
            results["user_watchlist"] = n_wl
            console.print(f"[green]✓ 自选与工作台监控标的落盘: {n_wl} 条记录[/green]")
        except Exception as e:
            results["user_watchlist"] = 0
            console.print(f"[yellow]! 自选数据同步异常: {e}[/yellow]")

        # 2. 行业资金流
        try:
            n_mf = self.money_flow.sync_to_lakehouse()
            results["sector_money_flow"] = n_mf
            console.print(f"[green]✓ 行业板块资金流向落盘: {n_mf} 个行业[/green]")
        except Exception as e:
            results["sector_money_flow"] = 0
            console.print(f"[yellow]! 行业资金流同步异常: {e}[/yellow]")

        # 3. 中债曲线
        try:
            n_bd = self.bonds.sync_to_lakehouse()
            results["chinabond_yield_curve"] = n_bd
            console.print(f"[green]✓ 中债收益率曲线落盘: {n_bd} 个交易日时序[/green]")
        except Exception as e:
            results["chinabond_yield_curve"] = 0
            console.print(f"[yellow]! 中债曲线同步异常: {e}[/yellow]")

        # 4. ETF 份额与资金流
        try:
            n_etf = self.etf.sync_to_lakehouse()
            results["etf_flows"] = n_etf
            console.print(f"[green]✓ ETF 份额与资金流动落盘: {n_etf} 只 ETF[/green]")
        except Exception as e:
            results["etf_flows"] = 0
            console.print(f"[yellow]! ETF 资金流同步异常: {e}[/yellow]")

        # 5. 核心标的财务与分红
        try:
            # 针对自选池中的前 5 只股票进行精准同步
            wl_df = self.watchlist.build_consolidated_watchlist()
            target_codes = []
            if not wl_df.empty:
                stocks = wl_df[wl_df["asset_class"].isin(["stock", "other"])]
                target_codes = stocks["symbol"].tolist()[:6]
            if not target_codes:
                target_codes = ["600519", "601318", "000858", "300750"]
            n_fin = self.financials.sync_financials_to_lakehouse(target_codes)
            results["stock_financials"] = n_fin
            console.print(f"[green]✓ 核心标的 F10 财务与分红落盘: {n_fin} 只龙头标的[/green]")
        except Exception as e:
            results["stock_financials"] = 0
            console.print(f"[yellow]! 财务与分红同步异常: {e}[/yellow]")

        # 刷新 DuckDB 视图
        try:
            self.lakehouse.init_duckdb_views()
            console.print("[bold green]✓ 湖仓全量视图初始化完成，支持 DuckDB 即席高速查询！[/bold green]")
        except Exception as e:
            console.print(f"[yellow]! DuckDB 视图初始化提示: {e}[/yellow]")

        return results

    def get_terminal_status(self) -> Dict[str, Any]:
        """获取终端运行状态、活动进程与登录投顾画像"""
        status = self.terminal_probe.detect_status()
        user_info = self.config._parsed_user_info
        advisor = self.watchlist.get_advisor_profile()

        # 优先使用实名档案中的投顾姓名
        login_name = advisor.get("name") or user_info.get("login_name", "本地投顾")
        if advisor.get("en_name"):
            display_user = f"{login_name} ({advisor['en_name']})"
        else:
            display_user = login_name

        return {
            "wfc_root": str(self.config.root_dir),
            "is_running": status.is_running,
            "wmain_pid": status.wmain_proc.pid if status.wmain_proc else None,
            "wbox_pid": status.wbox_proc.pid if status.wbox_proc else None,
            "total_memory_mb": status.total_memory_mb,
            "session_id": self.session_mgr.get_session_id(),
            "user": display_user,
            "advisor_name": advisor.get("name", ""),
            "advisor_en_name": advisor.get("en_name", ""),
            "advisor_phone": advisor.get("phone", ""),
            "advisor_mail": advisor.get("mail", ""),
            "advisor_wdid": advisor.get("wdid", ""),
            "company": user_info.get("company", "机构自营"),
            "server": self.config.default_web_server,
            "active_user_dir": str(self.watchlist._get_active_user_dir() or "")
        }
