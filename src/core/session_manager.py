"""
会话凭证管理模块：负责从终端配置文件、本地 CEF 缓存或内存中提取活体 wind.sessionid，
并提供会话健康探测与自动刷新管理。
"""

import os
import re
import ctypes
from ctypes import wintypes
from typing import Optional, List, Tuple
import requests
import urllib3

from ..config import WIND_CONFIG

urllib3.disable_warnings()


class SessionManager:
    """Wind 终端 SessionID 管理器"""

    def __init__(self, config=WIND_CONFIG):
        self.config = config
        self._cached_session_id: Optional[str] = None
        self._is_validated: bool = False

    def get_session_id(self, force_refresh: bool = False) -> Optional[str]:
        """获取当前有效的 session_id"""
        if self._cached_session_id and not force_refresh and self._is_validated:
            return self._cached_session_id

        # 策略 1: 从 user.config 读取
        self.config.reload()
        config_sid = self.config.current_session_id
        if config_sid and self.validate_session(config_sid):
            self._cached_session_id = config_sid
            self._is_validated = True
            return config_sid

        # 策略 2: 扫描本地 LevelDB 中可能暂存的会话凭证
        leveldb_sid = self._scan_leveldb_session()
        if leveldb_sid and self.validate_session(leveldb_sid):
            self._cached_session_id = leveldb_sid
            self._is_validated = True
            return leveldb_sid

        # 降级：如果未通过云端验证但找到了静态配置的 sessionid，依然暂存供离线或局域网试探
        if config_sid:
            self._cached_session_id = config_sid
            return config_sid

        return None

    def validate_session(self, session_id: str, timeout: float = 3.0) -> bool:
        """测试 session_id 在云端接口是否处于有效授权状态"""
        if not session_id:
            return False

        server = self.config.default_web_server
        url = f"https://{server}/pac-web/api/crm/getUserCompanyInfo"
        headers = {
            "wind.sessionid": session_id,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.5414.120 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
        }

        try:
            resp = requests.get(url, headers=headers, verify=False, timeout=timeout)
            if resp.status_code == 200 and "errorCode" not in resp.text:
                return True
            # 如果返回 {"errorCode": 10011, "message": "SessionId无效或已过期..."} 说明已失效
            return False
        except Exception:
            return False

    def _scan_leveldb_session(self) -> Optional[str]:
        """扫描 CEF Local Storage LevelDB 文件提取潜在的 sessionid"""
        leveldb_dir = self.config.cef_leveldb_dir
        if not leveldb_dir.exists():
            return None

        try:
            for fpath in leveldb_dir.glob("*.ldb"):
                with open(fpath, "rb") as f:
                    content = f.read()
                # 匹配数字型 session 80-95 位
                matches = re.findall(rb"\b\d{75,95}\b", content)
                for m in matches:
                    cand = m.decode("ascii")
                    if self.validate_session(cand, timeout=1.0):
                        return cand
        except Exception:
            pass

        return None
