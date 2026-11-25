# -*- coding: utf-8 -*-
"""
AGY2 全局唯一运行时路径解析器 (Single Runtime Path Resolver)
==========================================================
统一解决源码运行、工作目录切换、以及 PyInstaller / Tauri Sidecar 冻结打包后的
数据目录（可写）、缓存目录、备份目录与只读资源目录寻址问题，消除 CWD 相对路径猜测。
"""

import os
import sys
from pathlib import Path


def get_bundle_root() -> Path:
    """只读代码与内嵌资源根目录（兼容源码运行与 PyInstaller _MEIPASS 冻结模式）。"""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS).resolve()
    return Path(__file__).resolve().parent


def get_workspace_root() -> Path:
    """项目工作区根目录。"""
    here = Path(__file__).resolve().parent
    return here.parent if here.name == "AGY2_FundAdvisory" else here


def get_data_dir() -> Path:
    """
    获取唯一权威可写数据目录：
    1. 优先读取环境变量 AGY2_DATA_DIR（便于测试隔离与客户端自定义）；
    2. 冻结打包模式落盘至用户本地应用数据目录（LOCALAPPDATA / .local/share）；
    3. 源码开发模式固定落盘至 <workspace_root>/data，杜绝受 os.getcwd() 漂移影响。
    """
    env_dir = os.environ.get("AGY2_DATA_DIR", "").strip()
    if env_dir:
        p = Path(env_dir).expanduser().resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p
    if getattr(sys, "frozen", False):
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share"))
        p = (base / "AGY2_FundAdvisory" / "data").resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p
    p = (get_workspace_root() / "data").resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_cache_dir() -> Path:
    """获取统一缓存目录 (<data_dir>/cache)。"""
    p = get_data_dir() / "cache"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_backup_dir() -> Path:
    """获取统一备份目录 (<data_dir>/backups)。"""
    p = get_data_dir() / "backups"
    p.mkdir(parents=True, exist_ok=True)
    return p


def resolve_data_file(filename: str) -> Path:
    """解析 data 目录下指定文件路径：优先取 get_data_dir()，只读回退至工作区/内嵌包 data/，新建写入落盘至 get_data_dir()。"""
    clean = str(filename or "").replace("\\", "/").lstrip("/")
    if clean.startswith("data/"):
        clean = clean[5:]
    primary = get_data_dir() / clean
    if primary.exists():
        return primary
    ws_fallback = get_workspace_root() / "data" / clean
    if ws_fallback.exists():
        return ws_fallback
    legacy = get_bundle_root() / "data" / clean
    if legacy.exists():
        return legacy
    return primary
