"""
配置模块：负责 Wind 投顾终端 (WFC) 路径探测、核心配置读取与全局参数维护。
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
import xml.etree.ElementTree as ET
import re


class WindConfig:
    """Wind 终端配置与路径管理单例类"""

    def __init__(self, custom_root: Optional[str] = None):
        self.root_dir: Path = self._discover_root(custom_root)
        self.bin_dir: Path = self.root_dir / "bin"
        self.etc_dir: Path = self.root_dir / "etc"
        self.tmp_dir: Path = self.root_dir / "tmp"
        self.users_dir: Path = self.root_dir / "users"
        self.upgrade_dir: Path = self.root_dir / "upgrade"
        
        # 本地关键离线文件路径
        self.code_cache_path: Path = self.tmp_dir / "FreqUsedCodeFile.codecache"
        self.sysgrp_dat_path: Path = self.tmp_dir / "sysgrp.dat"
        self.sector_index_cache_path: Path = self.tmp_dir / "sectorindex.cache"
        self.trade_dates_path: Path = self.tmp_dir / "CWboxTool" / "runimage.s6" / "etc" / "base" / "CNTradeDates.dat"
        self.ah_stock_path: Path = self.tmp_dir / "CWboxTool" / "runimage.s6" / "etc" / "base" / "AhStockList.dat"
        self.related_symbols_path: Path = self.tmp_dir / "CWboxTool" / "runimage.s6" / "etc" / "base" / "RelatedSymbols.dat"
        
        # Chromium CEF 缓存路径
        self.cef_cache_dir: Path = self.tmp_dir / "WFTWebkit109Cache1" / "Cache" / "Cache_Data"
        self.cef_leveldb_dir: Path = self.tmp_dir / "WFTWebkit109Cache1" / "Local Storage" / "leveldb"
        self.cef_cookies_path: Path = self.tmp_dir / "WFTWebkit109Cache1" / "Network" / "Cookies"
        
        # 32位 WindPy 原生组件
        self.windpy_dll_path: Path = self.bin_dir / "WindPy.dll"
        self.windpy_py_path: Path = self.bin_dir / "WindPy.py"

        # 终端网络与服务器配置
        self.default_web_server: str = "114.80.154.45"
        self.default_sky_server: str = "114.80.154.36"
        self.default_sky_port: int = 443
        
        # 读取配置
        self.user_config_path: Path = self.etc_dir / "user.config"
        self._parsed_user_info: Dict[str, Any] = {}
        self._load_user_config()

    def _discover_root(self, custom_root: Optional[str] = None) -> Path:
        """自动推断 Wind 投顾客户端主目录"""
        if custom_root and os.path.isdir(custom_root):
            return Path(custom_root)

        candidates = [
            r"C:\Wind\Wind.NET.Client\WFC",
            r"D:\Wind\Wind.NET.Client\WFC",
            r"C:\WIND\WIND.NET.CLIENT\WFC",
            r"D:\WIND\WIND.NET.CLIENT\WFC",
            r"C:\Wind\Wind.NET.Client\WindNET",
            r"D:\Wind\Wind.NET.Client\WindNET",
        ]

        for cand in candidates:
            if os.path.isdir(cand) and os.path.exists(os.path.join(cand, "bin", "wmain.exe")):
                return Path(cand)

        # 默认回退
        return Path(candidates[0])

    def _load_user_config(self) -> None:
        """解析 user.config (GB18030/GB2312 编码)"""
        if not self.user_config_path.exists():
            return

        try:
            with open(self.user_config_path, "r", encoding="gb18030", errors="ignore") as f:
                content = f.read()

            session_match = re.search(r'sessionid="([^"]+)"', content)
            server_match = re.search(r'eagleCServer="([^"]+)"', content)
            login_match = re.search(r'loginName="([^"]+)"', content)
            email_match = re.search(r'userEmail="([^"]+)"', content)
            company_match = re.search(r'companyName="([^"]+)"', content)

            if session_match:
                self._parsed_user_info["sessionid"] = session_match.group(1)
            if server_match:
                self._parsed_user_info["server"] = server_match.group(1)
                self.default_web_server = server_match.group(1)
            if login_match:
                self._parsed_user_info["login_name"] = login_match.group(1)
            if email_match:
                self._parsed_user_info["email"] = email_match.group(1)
            if company_match:
                self._parsed_user_info["company"] = company_match.group(1)
        except Exception:
            pass

    @property
    def current_session_id(self) -> Optional[str]:
        """获取当前配置中记录的 sessionid"""
        return self._parsed_user_info.get("sessionid")

    @property
    def current_user(self) -> Optional[str]:
        """获取当前用户登录名"""
        return self._parsed_user_info.get("login_name")

    def reload(self) -> None:
        """重新载入配置"""
        self._load_user_config()


# 全局单例
WIND_CONFIG = WindConfig()
