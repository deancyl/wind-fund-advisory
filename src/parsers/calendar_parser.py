"""
中国交易日历解析器：读取 Wind 官方 CNTradeDates.dat 完整交易日序列，
提供交易日判定、区间交易日查询、交易日偏移推算与统计功能。
"""

from datetime import datetime, date
from typing import List, Optional, Union
from pathlib import Path

from ..config import WIND_CONFIG


class CalendarParser:
    """中国 A 股交易日历与计算引擎"""

    def __init__(self, file_path: Optional[Union[str, Path]] = None):
        self.file_path = Path(file_path) if file_path else WIND_CONFIG.trade_dates_path
        self._trade_days_str: List[str] = []
        self._trade_days_set = set()
        self._load()

    def _load(self) -> None:
        """加载交易日序列"""
        if not self.file_path.exists():
            return

        with open(self.file_path, "r", encoding="ascii", errors="ignore") as f:
            for line in f:
                d_str = line.strip()
                if len(d_str) == 8 and d_str.isdigit():
                    self._trade_days_str.append(d_str)

        self._trade_days_set = set(self._trade_days_str)

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
        return d.replace("-", "").replace("/", "").strip()

    def is_trade_day(self, target: Union[str, date, datetime]) -> bool:
        """判定目标日期是否为交易日"""
        norm = self._normalize_date(target)
        return norm in self._trade_days_set

    def get_trade_days(
        self,
        start_date: Union[str, date, datetime],
        end_date: Union[str, date, datetime]
    ) -> List[str]:
        """获取指定闭区间内的所有交易日列表 [YYYYMMDD]"""
        s = self._normalize_date(start_date)
        e = self._normalize_date(end_date)
        if s > e:
            s, e = e, s

        return [d for d in self._trade_days_str if s <= d <= e]

    def count_trade_days(
        self,
        start_date: Union[str, date, datetime],
        end_date: Union[str, date, datetime]
    ) -> int:
        """统计区间内的有效交易日总数"""
        return len(self.get_trade_days(start_date, end_date))

    def get_offset_trade_day(
        self,
        base_date: Union[str, date, datetime],
        offset: int
    ) -> Optional[str]:
        """
        以基准日为起点，推算偏移 N 个交易日的具体日期。
        offset > 0 向未来推算；offset < 0 向过去推算。
        """
        b = self._normalize_date(base_date)
        if b not in self._trade_days_set:
            # 如果基准日非交易日，寻找其后或其前最近的交易日
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
