"""
Wind 终端 Speed 实时行情流解析器 (WindSpeedLogParser)：
从 Wind 客户端日志目录 (log/Speed/SpeedData_*.log) 中逆向提取
CDataStore::StoreVolatileData 推送的实时快照与分时行情数据，
包括最新点位 (3)、昨收 (4)、成交额 (59)、涨跌额 (80)、涨跌幅 (81) 与闭市状态 (136)。
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
from typing import Dict, List, Optional, Union

from ..config import WIND_CONFIG


@dataclass
class SpeedQuoteSnapshot:
    """实时行情流快照数据对象"""
    symbol: str
    date: str              # 交易日期 YYYY-MM-DD
    timestamp: str         # 采样时间 YYYY-MM-DD HH:MM:SS.mmm
    latest: float          # 最新现价 / 收盘点位 (Field 3 / 84)
    pre_close: float       # 昨收盘价 (Field 4 / 75)
    amount: float          # 成交金额 (元) (Field 59)
    change: float          # 涨跌额 (Field 80)
    change_pct: float      # 涨跌幅 (%) (由 Field 81 转换百分比)
    status_code: int       # 交易状态码 (Field 136: 2=闭市, 3=交易中)
    raw_fields: Dict[str, str]


class WindSpeedLogParser:
    """Wind Speed 实时行情日志解析引擎"""

    def __init__(self, log_dir: Optional[Union[str, Path]] = None):
        if log_dir:
            self.speed_log_dir = Path(log_dir)
        else:
            wfc_root = WIND_CONFIG.root_dir
            self.speed_log_dir = wfc_root / "log" / "Speed" if wfc_root else Path(r"C:\Wind\Wind.NET.Client\WFC\log\Speed")

    def find_latest_speed_log(self) -> Optional[Path]:
        """寻找最新的 SpeedData_YYYY-MM-DD.log 文件"""
        if not self.speed_log_dir.exists():
            return None
        logs = sorted(self.speed_log_dir.glob("SpeedData_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        return logs[0] if logs else None

    def parse_log_file(self, log_path: Path) -> Dict[str, List[SpeedQuoteSnapshot]]:
        """
        解析单个 SpeedData 日志，提取所有 StoreVolatileData 记录
        """
        if not log_path.exists():
            return {}

        try:
            content = log_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return {}

        # 匹配: 2026.10.27 14:41:01.593 [PID:...-TID:...] [ERROR] CDataStore::StoreVolatileData SYMBOL: [k:v, ...]
        pattern = re.compile(
            r"(\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d{3})?).*?"
            r"StoreVolatileData\s+([A-Za-z0-9\._]+):\s*\[(.*?)\]"
        )

        results: Dict[str, List[SpeedQuoteSnapshot]] = {}

        for time_str, symbol, raw_data in pattern.findall(content):
            clean_sym = symbol.strip().upper()
            field_map: Dict[str, str] = {}
            for item in raw_data.split(","):
                item = item.strip()
                if ":" in item:
                    k, v = item.split(":", 1)
                    field_map[k.strip()] = v.strip()

            # 提取日期 (优先从 Field 1 提取 YYYYMMDD，或从时间戳解析)
            if "1" in field_map and len(field_map["1"]) == 8:
                raw_d = field_map["1"]
                date_str = f"{raw_d[:4]}-{raw_d[4:6]}-{raw_d[6:]}"
            else:
                date_part = time_str.split()[0].replace(".", "-")
                date_str = date_part

            # 字段映射
            latest = float(field_map.get("3") or field_map.get("84") or 0.0)
            pre_close = float(field_map.get("4") or field_map.get("75") or 0.0)
            amount = float(field_map.get("59") or 0.0)
            change = float(field_map.get("80") or (latest - pre_close if pre_close > 0 else 0.0))

            # Field 81 通常是小数形式如 -0.0075 (-0.75%)
            if "81" in field_map:
                try:
                    change_pct = round(float(field_map["81"]) * 100.0, 4)
                except ValueError:
                    change_pct = round((change / pre_close * 100.0) if pre_close > 0 else 0.0, 4)
            else:
                change_pct = round((change / pre_close * 100.0) if pre_close > 0 else 0.0, 4)

            status_code = int(field_map.get("136", "2"))

            snapshot = SpeedQuoteSnapshot(
                symbol=clean_sym,
                date=date_str,
                timestamp=time_str.replace(".", "-"),
                latest=latest,
                pre_close=pre_close,
                amount=amount,
                change=round(change, 4),
                change_pct=change_pct,
                status_code=status_code,
                raw_fields=field_map
            )

            if clean_sym not in results:
                results[clean_sym] = []
            results[clean_sym].append(snapshot)

        return results

    def get_latest_snapshot(self, symbol: str, log_path: Optional[Path] = None) -> Optional[SpeedQuoteSnapshot]:
        """获取指定标的的最新一条实时行情快照"""
        target_log = log_path or self.find_latest_speed_log()
        if not target_log:
            return None

        parsed = self.parse_log_file(target_log)
        clean_sym = symbol.strip().upper()
        if clean_sym in parsed and parsed[clean_sym]:
            # 过滤掉最新价为 0 的纯状态变更行
            valid_snapshots = [s for s in parsed[clean_sym] if s.latest > 0]
            if valid_snapshots:
                return valid_snapshots[-1]
            return parsed[clean_sym][-1]
        return None

    def get_all_latest_snapshots(self, log_path: Optional[Path] = None) -> Dict[str, SpeedQuoteSnapshot]:
        """获取日志中所有监控标的的最新实时行情快照"""
        target_log = log_path or self.find_latest_speed_log()
        if not target_log:
            return {}

        parsed = self.parse_log_file(target_log)
        out = {}
        for sym, snaps in parsed.items():
            valid = [s for s in snaps if s.latest > 0]
            if valid:
                out[sym] = valid[-1]
            elif snaps:
                out[sym] = snaps[-1]
        return out
