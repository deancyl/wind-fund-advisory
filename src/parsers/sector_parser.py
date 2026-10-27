"""
板块分类树解析器：解析 Wind sysgrp.dat 文件，提取官方板块分类体系
（如全部A股、上证A股、申万/万得行业分类等）。
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Union

from ..config import WIND_CONFIG


@dataclass
class SectorNode:
    code: str
    name: str
    english_name: str
    parent_code: Optional[str] = None
    level: int = 1


class SectorParser:
    """Wind 行业与板块分类解析器"""

    def __init__(self, file_path: Optional[Union[str, Path]] = None):
        self.file_path = Path(file_path) if file_path else WIND_CONFIG.sysgrp_dat_path
        self._sectors: Dict[str, SectorNode] = {}
        self._loaded: bool = False

    def load(self) -> int:
        """从 sysgrp.dat 读取板块节点"""
        if not self.file_path.exists():
            return 0

        self._sectors.clear()
        with open(self.file_path, "rb") as f:
            data = f.read()

        # sysgrp.dat 编码同样为 UTF-16LE
        text = data.decode("utf-16le", errors="ignore")

        # 匹配板块代码结构：字母开头 + 15位标识符
        pattern = re.compile(r"([a-z0-9]{16})\x00([^\x00]+)\x00([^\x00]+)\x00")
        matches = pattern.finditer(text)

        for m in matches:
            code = m.group(1)
            name = m.group(2).strip()
            en_name = m.group(3).strip()

            if name and not name.isdigit():
                node = SectorNode(code=code, name=name, english_name=en_name)
                self._sectors[code] = node

        self._loaded = True
        return len(self._sectors)

    @property
    def total_count(self) -> int:
        if not self._loaded:
            self.load()
        return len(self._sectors)

    def find_by_name(self, keyword: str) -> List[SectorNode]:
        """按板块名称检索"""
        if not self._loaded:
            self.load()

        kw = keyword.strip().lower()
        return [
            node for node in self._sectors.values()
            if kw in node.name.lower() or kw in node.english_name.lower()
        ]

    def get(self, code: str) -> Optional[SectorNode]:
        """按代码精准获取板块"""
        if not self._loaded:
            self.load()
        return self._sectors.get(code)
