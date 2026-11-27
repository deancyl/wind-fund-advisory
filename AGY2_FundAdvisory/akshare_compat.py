# -*- coding: utf-8 -*-
"""
AGY2 AkShare 跨版本兼容层 (akshare_compat.py)
=============================================
统一兼容 AkShare 1.14~1.19（旧接口名）与 AkShare >= 1.20.41~1.20.70+（大规模更名后接口名），
避免新部署环境安装新版 AkShare 时因函数更名触发 AttributeError 崩溃。

覆盖的全部 7 处跨版本接口映射：
1. index_hist_csindex            <- stock_zh_index_hist_csindex   (1.20.44)
2. index_value_csindex           <- stock_zh_index_value_csindex  (1.20.44)
3. index_zh_daily_em             <- stock_zh_index_daily_em       (1.20.44)
4. index_zh_spot_em              <- stock_zh_index_spot_em        (1.20.44)
5. calendar_trade_date_hist_sina <- tool_trade_date_hist_sina     (1.20.45)
6. bond_zh_us_yield_em           <- bond_zh_us_rate               (1.20.41)
7. fund_open_fund_info_em        <- (单基历史净值，替代无参 fund_open_nav_em / 旧 fund_open_fund_daily_em)
"""

from __future__ import annotations

import threading
from typing import Any, Callable, Iterable, Optional, Sequence

import pandas as pd

# AkShare 内部部分接口（如 Sina 交易日历/解密脚本）依赖 py_mini_racer (V8 PartitionAlloc)，
# 多线程首次并发初始化 V8 会触发 C++ FATAL Check failed: !IsConfigurablePoolInitialized() 直接杀进程；
# 通过进程级可重入锁串行化保护，彻底消除多线程并发冷启动崩溃。
_AKSHARE_V8_LOCK = threading.RLock()


def _get_ak(ak_module: Any = None) -> Any:
    if ak_module is not None:
        return ak_module
    import akshare as ak  # type: ignore

    return ak


def _resolve_callable(ak: Any, names: Sequence[str]) -> Callable[..., Any]:
    """按优先级解析首个可用可调用对象；兼容 AkShare 1.20+ 自定义 __getattr__ 抛 AttributeError。"""
    last_err: Optional[Exception] = None
    for name in names:
        try:
            fn = getattr(ak, name)
            if callable(fn):
                return fn
        except AttributeError as exc:
            last_err = exc
            continue
    if last_err is not None:
        raise last_err
    raise AttributeError(f"AkShare 中未找到兼容接口: {', '.join(names)}")


def index_hist_csindex(
    symbol: str,
    start_date: str = "20180101",
    end_date: str = "20500101",
    ak_module: Any = None,
) -> pd.DataFrame:
    with _AKSHARE_V8_LOCK:
        ak = _get_ak(ak_module)
        fn = _resolve_callable(ak, ("index_hist_csindex", "stock_zh_index_hist_csindex"))
        return fn(symbol=symbol, start_date=start_date, end_date=end_date)


def index_value_csindex(symbol: str, ak_module: Any = None) -> pd.DataFrame:
    with _AKSHARE_V8_LOCK:
        ak = _get_ak(ak_module)
        fn = _resolve_callable(ak, ("index_value_csindex", "stock_zh_index_value_csindex"))
        return fn(symbol=symbol)


def index_daily_em(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    ak_module: Any = None,
) -> pd.DataFrame:
    with _AKSHARE_V8_LOCK:
        ak = _get_ak(ak_module)
        fn = _resolve_callable(ak, ("index_zh_daily_em", "stock_zh_index_daily_em"))
        kwargs = {"symbol": symbol}
        if start_date:
            kwargs["start_date"] = start_date
        if end_date:
            kwargs["end_date"] = end_date
        return fn(**kwargs)


def index_spot_em(symbol: str = "沪深重要指数", ak_module: Any = None) -> pd.DataFrame:
    with _AKSHARE_V8_LOCK:
        ak = _get_ak(ak_module)
        fn = _resolve_callable(ak, ("index_zh_spot_em", "stock_zh_index_spot_em"))
        try:
            return fn(symbol=symbol)
        except TypeError:
            return fn()


def trade_date_hist_sina(ak_module: Any = None) -> pd.DataFrame:
    with _AKSHARE_V8_LOCK:
        ak = _get_ak(ak_module)
        fn = _resolve_callable(ak, ("calendar_trade_date_hist_sina", "tool_trade_date_hist_sina"))
        return fn()


def bond_zh_us_yield(start_date: str = "19901219", ak_module: Any = None) -> pd.DataFrame:
    with _AKSHARE_V8_LOCK:
        ak = _get_ak(ak_module)
        fn = _resolve_callable(ak, ("bond_zh_us_yield_em", "bond_zh_us_rate"))
        try:
            return fn(start_date=start_date)
        except TypeError:
            return fn()


def open_fund_nav_history(
    code: str,
    start_date: Optional[str] = None,
    ak_module: Any = None,
) -> pd.DataFrame:
    """
    获取单只开放式公募基金历史单位净值序列（兼容 AkShare 1.18 & 1.20+）：
    优先调用 fund_open_fund_info_em(symbol=code, indicator="单位净值走势")，
    按 start_date 过滤并返回原始 DataFrame。
    """
    ak = _get_ak(ak_module)
    clean_code = str(code or "").strip().zfill(6)
    df: Optional[pd.DataFrame] = None
    try:
        fn_info = _resolve_callable(ak, ("fund_open_fund_info_em",))
        try:
            df = fn_info(symbol=clean_code, indicator="单位净值走势")
        except TypeError:
            df = fn_info(fund=clean_code, indicator="单位净值走势")
    except Exception:
        fn_legacy = _resolve_callable(ak, ("fund_open_fund_daily_em",))
        if start_date:
            df = fn_legacy(fund=clean_code, start_date=str(start_date).replace("-", ""))
        else:
            df = fn_legacy(fund=clean_code)

    if df is not None and not df.empty and start_date:
        date_col = next((c for c in df.columns if "日期" in str(c) or "date" in str(c).lower()), None)
        if date_col is not None:
            dt_series = pd.to_datetime(df[date_col], errors="coerce")
            cutoff = pd.to_datetime(str(start_date), errors="coerce")
            if pd.notna(cutoff):
                df = df.loc[dt_series >= cutoff].copy()
    return df if df is not None else pd.DataFrame()


def etf_hist_em(
    symbol: str,
    start_date: str = "20180101",
    end_date: str = "20500101",
    adjust: str = "qfq",
    ak_module: Any = None,
) -> pd.DataFrame:
    ak = _get_ak(ak_module)
    fn = _resolve_callable(ak, ("fund_etf_hist_em",))
    return fn(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust=adjust)


def spot_hist_sge(symbol: str = "Au99.99", ak_module: Any = None) -> pd.DataFrame:
    ak = _get_ak(ak_module)
    fn = _resolve_callable(ak, ("spot_hist_sge",))
    return fn(symbol=symbol)
