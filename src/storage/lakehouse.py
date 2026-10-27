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
        self.db_path = self.data_dir / "storage.duckdb"

        # 确保基础目录存在
        for p in [self.funds_dir, self.indices_dir, self.mart_dir, self.raw_dir, self.master_dir, self.macro_dir]:
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

        # 1. v_funds 视图
        fund_parquets = list(self.funds_dir.glob("*.parquet"))
        if fund_parquets:
            pattern = str(self.funds_dir / "*.parquet").replace("\\", "/")
            conn.execute(f"CREATE OR REPLACE VIEW v_funds AS SELECT * FROM read_parquet('{pattern}', union_by_name=true)")

        # 2. v_indices 视图
        index_parquets = list(self.indices_dir.glob("*.parquet"))
        if index_parquets:
            pattern = str(self.indices_dir / "*.parquet").replace("\\", "/")
            conn.execute(f"CREATE OR REPLACE VIEW v_indices AS SELECT * FROM read_parquet('{pattern}', union_by_name=true)")

        # 3. v_scorecards 视图
        sc_path = self.mart_dir / "fund_scorecards.parquet"
        if sc_path.exists():
            pattern = str(sc_path).replace("\\", "/")
            conn.execute(f"CREATE OR REPLACE VIEW v_scorecards AS SELECT * FROM read_parquet('{pattern}')")

        # 4. v_winrate 视图
        wr_path = self.mart_dir / "strategy_winrate.parquet"
        if wr_path.exists():
            pattern = str(wr_path).replace("\\", "/")
            conn.execute(f"CREATE OR REPLACE VIEW v_winrate AS SELECT * FROM read_parquet('{pattern}')")

        # 5. 全市场基金全景大宽表视图
        cat_path = self.master_dir / "fund_catalog.parquet"
        if cat_path.exists():
            pattern = str(cat_path).replace("\\", "/")
            conn.execute(f"CREATE OR REPLACE VIEW v_fund_catalog AS SELECT * FROM read_parquet('{pattern}')")

        snap_path = self.mart_dir / "fund_performance_snapshot.parquet"
        if snap_path.exists():
            pattern = str(snap_path).replace("\\", "/")
            conn.execute(f"CREATE OR REPLACE VIEW v_fund_snapshot AS SELECT * FROM read_parquet('{pattern}')")

        rating_path = self.mart_dir / "fund_ratings.parquet"
        if rating_path.exists():
            pattern = str(rating_path).replace("\\", "/")
            conn.execute(f"CREATE OR REPLACE VIEW v_fund_ratings AS SELECT * FROM read_parquet('{pattern}')")

        mgr_path = self.master_dir / "fund_managers.parquet"
        if mgr_path.exists():
            pattern = str(mgr_path).replace("\\", "/")
            conn.execute(f"CREATE OR REPLACE VIEW v_fund_managers AS SELECT * FROM read_parquet('{pattern}')")

        etf_path = self.master_dir / "etf_catalog.parquet"
        if etf_path.exists():
            pattern = str(etf_path).replace("\\", "/")
            conn.execute(f"CREATE OR REPLACE VIEW v_etfs AS SELECT * FROM read_parquet('{pattern}')")

        # 6. 宏观利率与流动性视图
        rate_path = self.macro_dir / "bond_zh_us_rate.parquet"
        if rate_path.exists():
            pattern = str(rate_path).replace("\\", "/")
            conn.execute(f"CREATE OR REPLACE VIEW v_macro_rates AS SELECT * FROM read_parquet('{pattern}')")

        margin_path = self.macro_dir / "margin_trading.parquet"
        if margin_path.exists():
            pattern = str(margin_path).replace("\\", "/")
            conn.execute(f"CREATE OR REPLACE VIEW v_margin_trading AS SELECT * FROM read_parquet('{pattern}')")

        money_path = self.macro_dir / "money_supply.parquet"
        if money_path.exists():
            pattern = str(money_path).replace("\\", "/")
            conn.execute(f"CREATE OR REPLACE VIEW v_macro_money AS SELECT * FROM read_parquet('{pattern}')")

        pmi_path = self.macro_dir / "pmi.parquet"
        if pmi_path.exists():
            pattern = str(pmi_path).replace("\\", "/")
            conn.execute(f"CREATE OR REPLACE VIEW v_macro_pmi AS SELECT * FROM read_parquet('{pattern}')")

        # 7. 市场估值与温度计视图
        val_path = self.mart_dir / "index_valuations.parquet"
        if val_path.exists():
            pattern = str(val_path).replace("\\", "/")
            conn.execute(f"CREATE OR REPLACE VIEW v_index_valuations AS SELECT * FROM read_parquet('{pattern}')")

        temp_path = self.mart_dir / "market_temperature.parquet"
        if temp_path.exists():
            pattern = str(temp_path).replace("\\", "/")
            conn.execute(f"CREATE OR REPLACE VIEW v_market_temperature AS SELECT * FROM read_parquet('{pattern}')")

        conn.close()

    def query_sql(self, sql: str) -> pd.DataFrame:
        """使用 DuckDB 对湖仓数据执行即席 SQL 查询"""
        self.init_duckdb_views()
        conn = duckdb.connect(str(self.db_path))
        try:
            df = conn.execute(sql).df()
            return df
        finally:
            conn.close()
