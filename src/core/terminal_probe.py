"""
终端探针模块：毫秒级探测 Wind 投顾终端主进程 (wmain.exe)、外壳代理 (WBox.exe)
以及 CEF 浏览器集群 (wbrowser.exe) 的活跃状态、内存占用与网络监听端口。
"""

import os
from dataclasses import dataclass
from typing import List, Optional, Dict
import psutil

from ..config import WIND_CONFIG


@dataclass
class ProcessInfo:
    pid: int
    name: str
    exe_path: str
    memory_mb: float
    cpu_percent: float
    status: str
    create_time: float


@dataclass
class TerminalStatus:
    is_running: bool
    wmain_proc: Optional[ProcessInfo]
    wbox_proc: Optional[ProcessInfo]
    wbrowser_procs: List[ProcessInfo]
    total_memory_mb: float
    active_tcp_connections: int
    is_ready_for_data: bool


class TerminalProbe:
    """Wind 终端探针诊断器"""

    def __init__(self, config=WIND_CONFIG):
        self.config = config

    def detect_status(self) -> TerminalStatus:
        """全面探测 Wind 终端当前进程树与网络状态"""
        wmain = None
        wbox = None
        wbrowsers = []
        total_mem = 0.0
        tcp_conns = 0

        target_names = {
            "wmain.exe": "wmain",
            "wbox.exe": "wbox",
            "wbrowser.exe": "wbrowser",
            "windupdate.run": "update",
            "windupdate.exe": "update"
        }

        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe', 'memory_info', 'cpu_percent', 'create_time', 'status']):
                try:
                    pname = proc.info['name'].lower()
                    if pname in target_names:
                        # 确保路径属于我们配置的 Wind 目录
                        exe = proc.info.get('exe') or ""
                        if str(self.config.root_dir).lower() not in exe.lower() and not exe == "":
                            continue

                        mem_mb = (proc.info['memory_info'].rss / (1024 * 1024)) if proc.info['memory_info'] else 0.0
                        total_mem += mem_mb

                        p_info = ProcessInfo(
                            pid=proc.info['pid'],
                            name=proc.info['name'],
                            exe_path=exe,
                            memory_mb=round(mem_mb, 2),
                            cpu_percent=proc.info.get('cpu_percent') or 0.0,
                            status=proc.info.get('status') or "unknown",
                            create_time=proc.info.get('create_time') or 0.0
                        )

                        if pname == "wmain.exe":
                            wmain = p_info
                        elif pname == "wbox.exe":
                            wbox = p_info
                        elif pname == "wbrowser.exe":
                            wbrowsers.append(p_info)

                        # 统计连接数
                        try:
                            if hasattr(proc, 'net_connections'):
                                conns = proc.net_connections(kind='tcp')
                            else:
                                conns = proc.connections(kind='tcp')
                            tcp_conns += len(conns)
                        except (psutil.AccessDenied, psutil.NoSuchProcess, Exception):
                            pass
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass

        is_running = (wmain is not None or wbox is not None)
        is_ready = bool(wmain and len(wbrowsers) > 0)

        return TerminalStatus(
            is_running=is_running,
            wmain_proc=wmain,
            wbox_proc=wbox,
            wbrowser_procs=wbrowsers,
            total_memory_mb=round(total_mem, 2),
            active_tcp_connections=tcp_conns,
            is_ready_for_data=is_ready
        )

    def is_online(self) -> bool:
        """简捷在线判定"""
        status = self.detect_status()
        return status.is_running
