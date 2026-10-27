"""
本地湖仓管理引擎 (LakehouseManager)：
基于 DuckDB + Parquet 构建高性能本地时序湖仓，
提供标的独立 Parquet 写入、窗口重叠增量合并 (Upsert)、基准指数管理及 DuckDB SQL 统一查询视图。
"""

import os
from pathlib import Path
from typing import List, Optional, Union, Dict, Any
import pandas as pd
import duckdb

from ..config import WIND_CONFIG


class LakehouseManager:
    """工作区本地湖仓存储与 DuckDB 交互管理器"""

    def __init__(self, data_dir: Optional[Union[str, Path]] = None):
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = Path(__file__).parent.parent.parent / "data"

        self.processed_dir = self.data_dir / "processed"
        self.funds_dir = self.processed_dir / "funds"
        self.indices_dir = self.processed_dir / "indices"
        self.mart_dir = self.data_dir / "mart"
        self.raw_dir = self.data_dir / "raw"
        self.master_dir = self.data_dir / "master"
        self.macro_dir = self.data_dir / "macro"
        self.global_dir = self.data_dir / "global"
        self.research_dir = self.data_dir / "research"
        self.db_path = self.data_dir / "storage.duckdb"

        # 确保基础目录存在
        for p in [self.funds_dir, self.indices_dir, self.mart_dir, self.raw_dir, self.master_dir, self.macro_dir, self.global_dir, self.research_dir]:
            p.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------
    # 基金时序数据管理 (Per-Symbol Parquet)
    # -------------------------------------------------------------

    def get_fund_file_path(self, symbol: str) -> Path:
        clean_sym = symbol.strip().upper()
        return self.funds_dir / f"{clean_sym}.parquet"

    def upsert_fund_series(
        self,
        symbol: str,
        new_df: pd.DataFrame,
        overlap_window_days: int = 10
    ) -> Path:
        """
        向 processed/funds/{symbol}.parquet 执行窗口重叠增量合并 (Upsert)。
        1. 若原文件存在，读取现有记录并与 new_df 以 'date' 主键进行合并覆盖；
        2. 自动校验并衍生 daily_return (%) 与 net_value_est；
        3. 按时间升序排序并原子落盘。
        """
        clean_sym = symbol.strip().upper()
        target_path = self.get_fund_file_path(clean_sym)

        if new_df.empty:
            return target_path

        df_in = new_df.copy()
        if "date" not in df_in.columns or "yield_pct" not in df_in.columns:
            raise ValueError("new_df 必须包含 'date' 与 'yield_pct' 核心列")

        # 格式化日期为 YYYY-MM-DD
        df_in["date"] = pd.to_datetime(df_in["date"]).dt.strftime("%Y-%m-%d")
        df_in["symbol"] = clean_sym
        if "fund_name" not in df_in.columns:
            df_in["fund_name"] = clean_sym

        if target_path.exists():
            try:
                exist_df = pd.read_parquet(target_path)
                exist_df["date"] = pd.to_datetime(exist_df["date"]).dt.strftime("%Y-%m-%d")
                # 合并策略：使用 new_df 的重叠数据覆盖旧数据，其余保留
                merged = pd.concat([exist_df, df_in], ignore_index=True)
                merged = merged.drop_duplicates(subset=["date"], keep="last")
            except Exception:
                merged = df_in
        else:
            merged = df_in

        # 重新排序并补充派生字段
        merged = merged.sort_values("date").reset_index(drop=True)
        merged["yield_pct"] = merged["yield_pct"].astype(float)
        
        # 估算复权净值
        merged["net_value_est"] = (1.0 + merged["yield_pct"] / 100.0).round(4)

        # 逐日收益率 daily_return %
        merged["daily_return"] = (merged["net_value_est"].pct_change() * 100.0).fillna(0.0).round(4)

        # 统一写入 Parquet
        merged.to_parquet(target_path, index=False, engine="pyarrow")
        return target_path

    def get_fund_series(self, symbol: str) -> Optional[pd.DataFrame]:
        """读取指定基金的完整历史时序 DataFrame"""
        path = self.get_fund_file_path(symbol)
        if not path.exists():
            return None
        return pd.read_parquet(path)

    def list_funds(self) -> List[str]:
        """列出本地已沉淀的所有基金代码"""
        return [f.stem for f in self.funds_dir.glob("*.parquet")]

    def get_fund_trading_rule(self, symbol: str) -> Optional[Dict[str, Any]]:
        """从主表获取单只基金的交易规则与基准费率"""
        rules_path = self.master_dir / "fund_trading_rules.parquet"
        if not rules_path.exists():
            return None
        import re
        clean_code = re.sub(r"[^\d]", "", symbol).zfill(6)
        df_rules = pd.read_parquet(rules_path)
        matched = df_rules[df_rules["symbol"] == clean_code]
        if matched.empty:
            return None
        return matched.iloc[0].to_dict()

    def get_stock_reports(self, symbol: Optional[str] = None, limit: int = 50) -> pd.DataFrame:
        """从湖仓检索卖方研报库 (支持个股代码/全市场)"""
        reports_path = self.research_dir / "research_reports.parquet"
        if not reports_path.exists():
            return pd.DataFrame()
        try:
            df = pd.read_parquet(reports_path)
            if symbol:
                import re
                clean_code = re.sub(r"[^\d]", "", symbol).zfill(6)
                matched = df[(df["symbol"] == clean_code) | (df["wind_code"].str.contains(clean_code, na=False))]
                return matched.head(limit).reset_index(drop=True)
            return df.head(limit).reset_index(drop=True)
        except Exception:
            return pd.DataFrame()

    # -------------------------------------------------------------
    # 基准指数管理 (processed/indices/{code}.parquet)
    # -------------------------------------------------------------

    def get_index_file_path(self, index_code: str) -> Path:
        clean_code = index_code.strip().upper()
        return self.indices_dir / f"{clean_code}.parquet"

    def upsert_index_series(self, index_code: str, df: pd.DataFrame) -> Path:
        """写入或更新基准指数时序"""
        clean_code = index_code.strip().upper()
        target_path = self.get_index_file_path(clean_code)

        df_in = df.copy()
        df_in["date"] = pd.to_datetime(df_in["date"]).dt.strftime("%Y-%m-%d")
        df_in["index_code"] = clean_code

        if target_path.exists():
            try:
                exist_df = pd.read_parquet(target_path)
                exist_df["date"] = pd.to_datetime(exist_df["date"]).dt.strftime("%Y-%m-%d")
                merged = pd.concat([exist_df, df_in], ignore_index=True)
                merged = merged.drop_duplicates(subset=["date"], keep="last")
            except Exception:
                merged = df_in
        else:
            merged = df_in

        merged = merged.sort_values("date").reset_index(drop=True)
        if "close" in merged.columns and "daily_return" not in merged.columns:
            merged["daily_return"] = (merged["close"].pct_change() * 100.0).fillna(0.0).round(4)

        merged.to_parquet(target_path, index=False, engine="pyarrow")
        return target_path

    def get_index_series(self, index_code: str) -> Optional[pd.DataFrame]:
        """获取基准指数时序"""
        path = self.get_index_file_path(index_code)
        if not path.exists():
            return None
        return pd.read_parquet(path)

    # -------------------------------------------------------------
    # 指标集市保存 (mart/)
    # -------------------------------------------------------------

    def save_mart_dataframe(self, table_name: str, df: pd.DataFrame) -> Path:
        """保存分析指标集市宽表至 data/mart/{table_name}.parquet"""
        target_path = self.mart_dir / f"{table_name}.parquet"
        df.to_parquet(target_path, index=False, engine="pyarrow")
        return target_path

    def get_mart_dataframe(self, table_name: str) -> Optional[pd.DataFrame]:
        """读取分析集市数据"""
        target_path = self.mart_dir / f"{table_name}.parquet"
        if not target_path.exists():
            return None
        return pd.read_parquet(target_path)

    # -------------------------------------------------------------
    # 扩展投顾数据集管理 (自选、F10财务、分红、行业资金流、中债曲线、ETF流动)
    # -------------------------------------------------------------

    def upsert_user_watchlist(self, df: pd.DataFrame) -> Path:
        """保存用户自选与工作台监控标的"""
        target_path = self.master_dir / "user_watchlist.parquet"
        df.to_parquet(target_path, index=False, engine="pyarrow")
        return target_path

    def get_user_watchlist(self) -> Optional[pd.DataFrame]:
        """读取用户自选与工作台监控标的"""
        target_path = self.master_dir / "user_watchlist.parquet"
        if not target_path.exists():
            return None
        return pd.read_parquet(target_path)

    def upsert_stock_financials(self, symbol: str, df: pd.DataFrame) -> Path:
        """增量合并股票/基金 F10 财务指标宽表至 mart/stock_financials.parquet"""
        target_path = self.mart_dir / "stock_financials.parquet"
        if df.empty:
            return target_path
        df_in = df.copy()
        if target_path.exists():
            try:
                exist_df = pd.read_parquet(target_path)
                merged = pd.concat([exist_df, df_in], ignore_index=True)
                merged = merged.drop_duplicates(subset=["symbol", "report_date"], keep="last")
            except Exception:
                merged = df_in
        else:
            merged = df_in
        merged = merged.sort_values(["symbol", "report_date"], ascending=[True, False]).reset_index(drop=True)
        merged.to_parquet(target_path, index=False, engine="pyarrow")
        return target_path

    def get_stock_financials(self, symbol: Optional[str] = None) -> Optional[pd.DataFrame]:
        """读取 F10 财务核心指标"""
        target_path = self.mart_dir / "stock_financials.parquet"
        if not target_path.exists():
            return None
        df = pd.read_parquet(target_path)
        if symbol:
            import re
            clean_code = re.sub(r"[^\d]", "", symbol).zfill(6)
            matched = df[df["symbol"].str.contains(clean_code, na=False)]
            return matched.reset_index(drop=True)
        return df

    def upsert_stock_dividends(self, symbol: str, df: pd.DataFrame) -> Path:
        """增量合并历史分红送配与股息率记录至 mart/stock_dividends.parquet"""
        target_path = self.mart_dir / "stock_dividends.parquet"
        if df.empty:
            return target_path
        df_in = df.copy()
        if target_path.exists():
            try:
                exist_df = pd.read_parquet(target_path)
                merged = pd.concat([exist_df, df_in], ignore_index=True)
                merged = merged.drop_duplicates(subset=["symbol", "report_date", "plan_desc"], keep="last")
            except Exception:
                merged = df_in
        else:
            merged = df_in
        merged = merged.sort_values(["symbol", "report_date"], ascending=[True, False]).reset_index(drop=True)
        merged.to_parquet(target_path, index=False, engine="pyarrow")
        return target_path

    def get_stock_dividends(self, symbol: Optional[str] = None) -> Optional[pd.DataFrame]:
        """读取历史分红送配记录"""
        target_path = self.mart_dir / "stock_dividends.parquet"
        if not target_path.exists():
            return None
        df = pd.read_parquet(target_path)
        if symbol:
            import re
            clean_code = re.sub(r"[^\d]", "", symbol).zfill(6)
            matched = df[df["symbol"].str.contains(clean_code, na=False)]
            return matched.reset_index(drop=True)
        return df

    def upsert_sector_money_flow(self, df: pd.DataFrame) -> Path:
        """保存行业板块主力资金流向至 mart/sector_money_flow.parquet"""
        target_path = self.mart_dir / "sector_money_flow.parquet"
        df.to_parquet(target_path, index=False, engine="pyarrow")
        return target_path

    def get_sector_money_flow(self) -> Optional[pd.DataFrame]:
        """读取行业板块主力资金流向"""
        target_path = self.mart_dir / "sector_money_flow.parquet"
        if not target_path.exists():
            return None
        return pd.read_parquet(target_path)

    def upsert_chinabond_yield_curve(self, df: pd.DataFrame) -> Path:
        """保存中债国债与信用债收益率曲线至 macro/chinabond_yield_curve.parquet"""
        target_path = self.macro_dir / "chinabond_yield_curve.parquet"
        if df.empty:
            return target_path
        df_in = df.copy()
        if target_path.exists():
            try:
                exist_df = pd.read_parquet(target_path)
                merged = pd.concat([exist_df, df_in], ignore_index=True)
                merged = merged.drop_duplicates(subset=["date", "curve_name"], keep="last")
            except Exception:
                merged = df_in
        else:
            merged = df_in
        merged = merged.sort_values("date").reset_index(drop=True)
        merged.to_parquet(target_path, index=False, engine="pyarrow")
        return target_path

    def get_chinabond_yield_curve(self) -> Optional[pd.DataFrame]:
        """读取中债收益率曲线"""
        target_path = self.macro_dir / "chinabond_yield_curve.parquet"
        if not target_path.exists():
            return None
        return pd.read_parquet(target_path)

    def upsert_etf_flows(self, df: pd.DataFrame) -> Path:
        """保存 ETF 份额与资金流动数据至 mart/etf_flows.parquet"""
        target_path = self.mart_dir / "etf_flows.parquet"
        df.to_parquet(target_path, index=False, engine="pyarrow")
        return target_path

    def get_etf_flows(self) -> Optional[pd.DataFrame]:
        """读取 ETF 份额与资金流动数据"""
        target_path = self.mart_dir / "etf_flows.parquet"
        if not target_path.exists():
            return None
        return pd.read_parquet(target_path)

    # -------------------------------------------------------------
    # DuckDB 视图与统一 SQL 查询引擎
    # -------------------------------------------------------------

    def init_duckdb_views(self) -> None:
        """
        在 storage.duckdb 中注册统一 SQL 视图：
        - v_funds: 自动通配扫描所有 processed/funds/*.parquet
        - v_indices: 自动通配扫描所有 processed/indices/*.parquet
        - v_scorecards: 挂载 mart/fund_scorecards.parquet (若存在)
        - v_winrate: 挂载 mart/strategy_winrate.parquet (若存在)
        """
        conn = duckdb.connect(str(self.db_path))
        try:
            self._register_views_on_connection(conn)
        finally:
            conn.close()

    def _register_views_on_connection(self, conn: duckdb.DuckDBPyConnection) -> None:
        """在指定的 DuckDB 连接上统一注册全量湖仓 SQL 视图"""
        # 1. v_funds 视图 (通配扫描所有 processed/funds/*.parquet)
        fund_parquets = list(self.funds_dir.glob("*.parquet"))
        if fund_parquets:
            pattern = str(self.funds_dir / "*.parquet").replace("\\", "/")
            conn.execute(f"CREATE OR REPLACE VIEW v_funds AS SELECT * FROM read_parquet('{pattern}', union_by_name=true)")

        # 2. v_indices 视图 (通配扫描所有 processed/indices/*.parquet)
        index_parquets = list(self.indices_dir.glob("*.parquet"))
        if index_parquets:
            pattern = str(self.indices_dir / "*.parquet").replace("\\", "/")
            conn.execute(f"CREATE OR REPLACE VIEW v_indices AS SELECT * FROM read_parquet('{pattern}', union_by_name=true)")

        # 3. 基础集市与主表视图映射
        view_mappings = [
            ("v_scorecards", self.mart_dir / "fund_scorecards.parquet"),
            ("v_winrate", self.mart_dir / "strategy_winrate.parquet"),
            ("v_fund_catalog", self.master_dir / "fund_catalog.parquet"),
            ("v_fund_snapshot", self.mart_dir / "fund_performance_snapshot.parquet"),
            ("v_fund_ratings", self.mart_dir / "fund_ratings.parquet"),
            ("v_fund_managers", self.master_dir / "fund_managers.parquet"),
            ("v_etfs", self.master_dir / "etf_catalog.parquet"),
            ("v_macro_rates", self.macro_dir / "bond_zh_us_rate.parquet"),
            ("v_margin_trading", self.macro_dir / "margin_trading.parquet"),
            ("v_macro_money", self.macro_dir / "money_supply.parquet"),
            ("v_macro_pmi", self.macro_dir / "pmi.parquet"),
            ("v_index_valuations", self.mart_dir / "index_valuations.parquet"),
            ("v_market_temperature", self.mart_dir / "market_temperature.parquet"),
            ("v_global_indices", self.global_dir / "global_indices.parquet"),
            ("v_global_fx", self.global_dir / "fx_rates.parquet"),
            ("v_global_commodities", self.global_dir / "commodities.parquet"),
            ("v_global_linkage", self.mart_dir / "global_linkage_metrics.parquet"),
            ("v_fund_trading_rules", self.master_dir / "fund_trading_rules.parquet"),
            ("v_research_reports", self.research_dir / "research_reports.parquet"),
            ("v_user_watchlist", self.master_dir / "user_watchlist.parquet"),
            ("v_stock_financials", self.mart_dir / "stock_financials.parquet"),
            ("v_stock_dividends", self.mart_dir / "stock_dividends.parquet"),
            ("v_sector_money_flow", self.mart_dir / "sector_money_flow.parquet"),
            ("v_chinabond_yield_curve", self.macro_dir / "chinabond_yield_curve.parquet"),
            ("v_etf_flows", self.mart_dir / "etf_flows.parquet"),
        ]

        for view_name, p in view_mappings:
            if p.exists():
                pattern = str(p).replace("\\", "/")
                conn.execute(f"CREATE OR REPLACE VIEW {view_name} AS SELECT * FROM read_parquet('{pattern}')")

    def query_sql(self, sql: str) -> pd.DataFrame:
        """使用 DuckDB 对湖仓数据执行即席 SQL 查询 (具备并发只读与多进程独占锁自愈兜底)"""
        import time
        try:
            self.init_duckdb_views()
        except Exception:
            pass

        # 优先以 read_only=True 连接，支持多进程无锁并发读取
        for attempt in range(3):
            try:
                conn = duckdb.connect(str(self.db_path), read_only=True)
                try:
                    return conn.execute(sql).df()
                finally:
                    conn.close()
            except Exception as e:
                if attempt < 2 and "Cannot open file" in str(e):
                    time.sleep(0.15)
                    continue
                # 独占锁异常时，无缝内存视图降级兜底 (注册全量视图，绝不漏缺任何表)
                mem_conn = duckdb.connect(":memory:")
                try:
                    self._register_views_on_connection(mem_conn)
                    return mem_conn.execute(sql).df()
                finally:
                    mem_conn.close()
