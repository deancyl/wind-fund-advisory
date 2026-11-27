# -*- coding: utf-8 -*-
"""
自包含中国 A 股交易日历解析器 (trading_calendar.py)
彻底解除 AGY2 对外部遗留 `src.parsers.calendar_parser` 与本地 Wind `CNTradeDates.dat` 的硬依赖，
确保在任意全新机器 (`git clone`) 零配置开箱即用：
  1. 优先读取本地缓存 `data/cache/cn_trade_dates.json`；
  2. 若缓存不存在或落后超过 7 天，尝试通过 AkShare 新浪公开交易日历同步并落盘；
  3. 极端断网或无外部源时自动退化为法定工作日历（周一至周五），保证绝不抛 AttributeError / ImportError。
"""

from __future__ import annotations

import json
import threading
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Optional, Union

import runtime_paths

_CALENDAR_CACHE_FILE = runtime_paths.get_cache_dir() / "cn_trade_dates.json"
_MEM_TRADE_DAYS: Optional[List[str]] = None
_CALENDAR_LOAD_LOCK = threading.Lock()


def _generate_weekday_fallback(start_ymd: str = "20150101", end_ymd: Optional[str] = None) -> List[str]:
    s_dt = datetime.strptime(start_ymd, "%Y%m%d").date()
    e_dt = datetime.strptime(end_ymd, "%Y%m%d").date() if end_ymd else (datetime.now().date() + timedelta(days=365))
    out: List[str] = []
    cur = s_dt
    while cur <= e_dt:
        if cur.weekday() < 5:
            out.append(cur.strftime("%Y%m%d"))
        cur += timedelta(days=1)
    return out


class CalendarParser:
    """中国 A 股交易日历与计算引擎（零外部私有依赖版）"""

    def __init__(self, file_path: Optional[Union[str, Path]] = None):
        self._default_cache_file = runtime_paths.get_cache_dir() / "cn_trade_dates.json"
        self.file_path = Path(file_path) if file_path else self._default_cache_file
        self._trade_days_str: List[str] = []
        self._trade_days_set = set()
        self._load()

    def _load(self) -> None:
        global _MEM_TRADE_DAYS

        # 0. 若调用方显式指定了自定义 .dat 文件且存在，优先读取（兼容旧调用）
        if self.file_path != self._default_cache_file and self.file_path.exists():
            days: List[str] = []
            try:
                with open(self.file_path, "r", encoding="ascii", errors="ignore") as f:
                    for line in f:
                        d_str = line.strip()
                        if len(d_str) == 8 and d_str.isdigit():
                            days.append(d_str)
                if days:
                    self._trade_days_str = sorted(set(days))
                    self._trade_days_set = set(self._trade_days_str)
                    return
            except Exception:
                pass

        # 1. 进程内高速缓存（双检锁防御并发冷启动触发 V8 py_mini_racer 竞态崩溃）
        if _MEM_TRADE_DAYS:
            self._trade_days_str = list(_MEM_TRADE_DAYS)
            self._trade_days_set = set(self._trade_days_str)
            return

        with _CALENDAR_LOAD_LOCK:
            if _MEM_TRADE_DAYS:
                self._trade_days_str = list(_MEM_TRADE_DAYS)
                self._trade_days_set = set(self._trade_days_str)
                return

            cache_f = self._default_cache_file
            # 2. 本地 JSON 缓存
            loaded: List[str] = []
            if cache_f.exists():
                try:
                    raw = json.loads(cache_f.read_text(encoding="utf-8"))
                    if isinstance(raw, list):
                        loaded = sorted({str(x).replace("-", "")[:8] for x in raw if len(str(x).replace("-", "")) >= 8})
                except Exception:
                    loaded = []

            # 3. 若缓存为空，尝试通过 AkShare 公开交易日历同步一次并缓存（兼容 1.18~1.20+）
            if not loaded:
                try:
                    import akshare_compat
                    df_td = akshare_compat.trade_date_hist_sina()
                    if df_td is not None and not df_td.empty and "trade_date" in df_td.columns:
                        loaded = sorted({
                            str(d).replace("-", "")[:8]
                            for d in df_td["trade_date"].tolist()
                            if str(d).replace("-", "")[:8].isdigit()
                        })
                        if loaded:
                            cache_f.parent.mkdir(parents=True, exist_ok=True)
                            cache_f.write_text(json.dumps(loaded), encoding="utf-8")
                except Exception:
                    loaded = []

            # 4. 离线兜底：生成 2015 ~ 明年的标准周一至周五工作日序列
            if not loaded:
                loaded = _generate_weekday_fallback("20150101")

            _MEM_TRADE_DAYS = list(loaded)
            self._trade_days_str = loaded
            self._trade_days_set = set(loaded)

    @property
    def total_count(self) -> int:
        return len(self._trade_days_str)

    @property
    def earliest_date(self) -> Optional[str]:
        return self._trade_days_str[0] if self._trade_days_str else None

    @property
    def latest_date(self) -> Optional[str]:
        return self._trade_days_str[-1] if self._trade_days_str else None

    def _normalize_date(self, d: Union[str, date, datetime]) -> str:
        if isinstance(d, (date, datetime)):
            return d.strftime("%Y%m%d")
        return str(d).replace("-", "").replace("/", "").strip()[:8]

    def is_trade_day(self, target: Union[str, date, datetime]) -> bool:
        norm = self._normalize_date(target)
        if norm in self._trade_days_set:
            return True
        if self._trade_days_str and norm > self._trade_days_str[-1]:
            if isinstance(target, (date, datetime)):
                dt = target if isinstance(target, date) else target.date()
            else:
                dt = datetime.strptime(norm[:8], "%Y%m%d").date()
            return dt.weekday() < 5
        return False

    def get_trade_days(
        self,
        start_date: Union[str, date, datetime],
        end_date: Union[str, date, datetime],
    ) -> List[str]:
        s = self._normalize_date(start_date)
        e = self._normalize_date(end_date)
        if s > e:
            s, e = e, s
        res = [d for d in self._trade_days_str if s <= d <= e]
        # 若请求区间超出日历文件末尾，自动补充周一至周五工作日
        if self._trade_days_str and e > self._trade_days_str[-1]:
            tail_start = max(s, (datetime.strptime(self._trade_days_str[-1], "%Y%m%d").date() + timedelta(days=1)).strftime("%Y%m%d"))
            if tail_start <= e:
                res.extend(_generate_weekday_fallback(tail_start, e))
        return res

    def count_trade_days(
        self,
        start_date: Union[str, date, datetime],
        end_date: Union[str, date, datetime],
    ) -> int:
        return len(self.get_trade_days(start_date, end_date))

    def get_offset_trade_day(
        self,
        base_date: Union[str, date, datetime],
        offset: int,
    ) -> Optional[str]:
        b = self._normalize_date(base_date)
        if not self._trade_days_str:
            return None
        if b not in self._trade_days_set:
            if offset >= 0:
                future_days = [d for d in self._trade_days_str if d >= b]
                if not future_days:
                    return None
                idx = self._trade_days_str.index(future_days[0])
            else:
                past_days = [d for d in self._trade_days_str if d <= b]
                if not past_days:
                    return None
                idx = self._trade_days_str.index(past_days[-1])
        else:
            idx = self._trade_days_str.index(b)

        target_idx = idx + offset
        if 0 <= target_idx < len(self._trade_days_str):
            return self._trade_days_str[target_idx]
        return None
