"""
全市场证券代码主字典解析器：从 Wind 本地 41MB FreqUsedCodeFile.codecache
提取全部 A 股股票、公募基金、核心指数的代码、名称、拼音缩写及英文标识。
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Union
import pandas as pd

from ..config import WIND_CONFIG


@dataclass
class SecurityRecord:
    symbol: str
    name: str
    pinyin: str
    english_name: str
    asset_class: str
    market: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "pinyin": self.pinyin,
            "english_name": self.english_name,
            "asset_class": self.asset_class,
            "market": self.market,
        }


class MasterDictParser:
    """Wind 全市场证券与标的代码解析器"""

    def __init__(self, file_path: Optional[Union[str, Path]] = None):
        self.file_path = Path(file_path) if file_path else WIND_CONFIG.code_cache_path
        self._records: Dict[str, SecurityRecord] = {}
        self._loaded: bool = False

    def load(self, max_records: Optional[int] = None) -> int:
        """加载并解析 codecache 文件"""
        if not self.file_path.exists():
            return 0

        self._records.clear()
        with open(self.file_path, "rb") as f:
            data = f.read()

        # FreqUsedCodeFile.codecache 是 UTF-16LE 编码
        text = data.decode("utf-16le", errors="ignore")

        # 匹配标准标的格式: [6位代码].[2位后缀]\x00[名称]\x00[拼音]\x00[英文名]\x00
        pattern = re.compile(r"([0-9]{6}\.[A-Z]{2})\x00([^\x00]+)\x00([^\x00]+)\x00([^\x00]+)\x00")
        matches = pattern.finditer(text)

        count = 0
        for m in matches:
            symbol, name, pinyin, en_name = m.group(1), m.group(2).strip(), m.group(3).strip(), m.group(4).strip()
            
            # 分类与市场识别
            suffix = symbol.split(".")[-1]
            code = symbol.split(".")[0]
            if suffix == "OF":
                asset_class = "fund"
            elif suffix == "SH":
                if code.startswith("000"):
                    asset_class = "index"
                elif code.startswith(("51", "56", "58")) or "ETF" in name.upper():
                    asset_class = "etf"
                elif code.startswith(("01", "11", "12", "13", "14")) or any(k in name for k in ["转债", "国债", "企债"]):
                    asset_class = "bond"
                elif code.startswith("50"):
                    asset_class = "fund"
                else:
                    asset_class = "stock"
            elif suffix == "SZ":
                if code.startswith("399"):
                    asset_class = "index"
                elif code.startswith("15") or "ETF" in name.upper():
                    asset_class = "etf"
                elif code.startswith(("10", "11", "12", "13", "14")) or any(k in name for k in ["转债", "国债", "企债"]):
                    asset_class = "bond"
                elif code.startswith(("16", "18")):
                    asset_class = "fund"
                else:
                    asset_class = "stock"
            elif suffix == "BJ":
                if code.startswith("899"):
                    asset_class = "index"
                else:
                    asset_class = "stock"
            elif suffix in ("CSI", "CNI", "WI", "GI"):
                asset_class = "index"
            elif suffix in ("CFE", "SHF", "CZC", "DCE", "INE"):
                asset_class = "futures"
            elif suffix == "HK":
                asset_class = "hk_stock"
            else:
                asset_class = "other"

            record = SecurityRecord(
                symbol=symbol,
                name=name,
                pinyin=pinyin,
                english_name=en_name,
                asset_class=asset_class,
                market=suffix
            )
            self._records[symbol] = record
            count += 1
            if max_records and count >= max_records:
                break

        self._loaded = True
        return count

    @property
    def total_count(self) -> int:
        if not self._loaded:
            self.load()
        return len(self._records)

    def get(self, symbol: str) -> Optional[SecurityRecord]:
        """按代码精准查询"""
        if not self._loaded:
            self.load()
        return self._records.get(symbol.upper().strip())

    def search(
        self,
        query: str,
        asset_class: Optional[str] = None,
        limit: int = 20
    ) -> List[SecurityRecord]:
        """多字段模糊检索 (支持代码、中文简称、拼音首字母)"""
        if not self._loaded:
            self.load()

        q = query.strip().upper()
        results = []

        for record in self._records.values():
            if asset_class and record.asset_class != asset_class:
                continue

            if (q in record.symbol or
                q in record.name or
                q in record.pinyin.upper() or
                q in record.english_name.upper()):
                results.append(record)
                if len(results) >= limit:
                    break

        return results

    def to_dataframe(self, asset_class: Optional[str] = None) -> pd.DataFrame:
        """导出为 Pandas DataFrame"""
        if not self._loaded:
            self.load()

        data = [
            r.to_dict() for r in self._records.values()
            if not asset_class or r.asset_class == asset_class
        ]
        return pd.DataFrame(data)

    def export_csv(self, output_path: Union[str, Path], asset_class: Optional[str] = None) -> str:
        """一键导出为 CSV 格式"""
        df = self.to_dataframe(asset_class=asset_class)
        dest = Path(output_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(dest, index=False, encoding="utf-8-sig")
        return str(dest)
