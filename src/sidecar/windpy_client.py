"""
WindPy 桥接客户端：在 64 位 Python 环境中代理调用 32 位 WindPy 子进程。
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List

from ..config import WIND_CONFIG


class WindPyBridgeClient:
    """WindPy 原生接口跨进程代理"""

    def __init__(self, python32_path: Optional[str] = None):
        self.python32_path = python32_path or self._find_python32()
        self.worker_script = Path(__file__).parent / "windpy_worker.py"
        self._proc: Optional[subprocess.Popen] = None

    def _find_python32(self) -> Optional[str]:
        """探测系统或当前工作区是否存在 32 位 Python"""
        candidates = [
            r"C:\Python311-32\python.exe",
            r"C:\Python310-32\python.exe",
            r"C:\Python39-32\python.exe",
            str(Path(__file__).parent.parent.parent / "tools" / "python32" / "python.exe")
        ]
        for cand in candidates:
            if os.path.exists(cand):
                return cand
        return None

    def is_available(self) -> bool:
        """检查 32位桥接子进程环境是否就绪"""
        return bool(self.python32_path and os.path.exists(self.python32_path))

    def _ensure_worker(self) -> bool:
        if not self.is_available():
            return False
        if self._proc is not None and self._proc.poll() is None:
            return True

        try:
            self._proc = subprocess.Popen(
                [self.python32_path, str(self.worker_script)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8"
            )
            return True
        except Exception:
            return False

    def send_command(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """向 32位 Worker 发送指令"""
        if not self._ensure_worker():
            return {
                "status": "unavailable",
                "message": "32位 Python 桥接环境未就绪。请使用本地离线解析器或 REST 接口获取数据。"
            }

        try:
            cmd_line = json.dumps(payload) + "\n"
            self._proc.stdin.write(cmd_line)
            self._proc.stdin.flush()
            resp_line = self._proc.stdout.readline()
            if not resp_line:
                return {"status": "error", "message": "Worker process pipe closed"}
            return json.loads(resp_line.strip())
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def wsd(
        self,
        codes: str,
        fields: str,
        begin_time: str,
        end_time: str,
        options: str = ""
    ) -> Dict[str, Any]:
        """调用 WindPy w.wsd 日度时序数据"""
        return self.send_command({
            "action": "wsd",
            "codes": codes,
            "fields": fields,
            "beginTime": begin_time,
            "endTime": end_time,
            "options": options
        })

    def close(self) -> None:
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
            except Exception:
                pass
            self._proc = None
