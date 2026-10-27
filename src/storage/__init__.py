"""
存储与湖仓引擎：基于 DuckDB + Parquet 实现本地列式时序存储、Upsert 合并与视图管理。
"""

from .lakehouse import LakehouseManager

__all__ = ["LakehouseManager"]
