# -*- coding: utf-8 -*-
"""
AGY2 全局唯一运行时路径解析器 (Single Runtime Path Resolver)
==========================================================
统一解决源码运行、工作目录切换、Docker 持久化卷挂载、以及 PyInstaller / Tauri Sidecar
冻结打包后的数据目录（可写）、缓存目录、备份目录与只读种子目录寻址问题，消除 CWD 相对路径猜测。
"""

import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 随仓发布的 7 个 100% 公开市场基准种子文件（0 个人隐私数据，~4.9MB）
PUBLIC_SEED_FILES: Tuple[str, ...] = (
    "processed/aligned_matrix_total_return.parquet",
    "processed/market_elite_nav_matrix.parquet",
    "processed/market_elite_meta.parquet",
    "processed/market_elite_sync_status.json",
    "macro/bond_zh_us_rate.parquet",
    "macro/chinabond_yield_curve.parquet",
    "mart/index_valuations.parquet",
)


def get_bundle_root() -> Path:
    """只读代码与内嵌资源根目录（兼容源码运行与 PyInstaller _MEIPASS 冻结模式）。"""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS).resolve()
    return Path(__file__).resolve().parent


def get_workspace_root() -> Path:
    """项目工作区根目录。"""
    here = Path(__file__).resolve().parent
    return here.parent if here.name == "AGY2_FundAdvisory" else here


def get_seed_dir() -> Optional[Path]:
    """
    获取只读公开市场基准种子目录：
    1. 优先读取环境变量 AGY2_SEED_DIR（Docker 官方镜像默认指向 /app/seed_data，防 ./data 空挂载卷遮盖）；
    2. 其次探测 <workspace_root>/seed_data 或 <bundle_root>/seed_data。
    """
    env_seed = os.environ.get("AGY2_SEED_DIR", "").strip()
    if env_seed:
        p = Path(env_seed).expanduser().resolve()
        if p.exists():
            return p
    for cand in (get_workspace_root() / "seed_data", get_bundle_root() / "seed_data"):
        if cand.exists():
            return cand.resolve()
    return None


def get_data_dir() -> Path:
    """
    获取唯一权威可写数据目录：
    1. 优先读取环境变量 AGY2_DATA_DIR（便于容器挂载、测试隔离与客户端自定义）；
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
    """
    解析 data 目录下指定文件路径：
    1. 优先取可写数据目录 get_data_dir()；
    2. 若不存在，按顺序只读回退至 seed_dir (AGY2_SEED_DIR) -> workspace/data -> bundle/data；
    3. 若均不存在，返回 primary 路径供新建写入。
    """
    clean = str(filename or "").replace("\\", "/").lstrip("/")
    if clean.startswith("data/"):
        clean = clean[5:]
    primary = get_data_dir() / clean
    if primary.exists():
        return primary
    seed_dir = get_seed_dir()
    if seed_dir is not None:
        seed_cand = seed_dir / clean
        if seed_cand.exists():
            return seed_cand
    ws_fallback = get_workspace_root() / "data" / clean
    if ws_fallback.exists():
        return ws_fallback
    legacy = get_bundle_root() / "data" / clean
    if legacy.exists():
        return legacy
    return primary


def bootstrap_public_seeds(force: bool = False) -> Dict[str, Any]:
    """
    启动幂等种子自举：
    将公开市场基准种子（PUBLIC_SEED_FILES）按需补齐到可写数据目录 get_data_dir()。
    - 仅当目标缺失（或 force=True）时采用原子复制（.tmp -> os.replace）；
    - 绝不覆盖用户已有更新后的文件，绝不触碰 ledgers/、backups/ 等个人资产数据。
    """
    target_root = get_data_dir()
    candidate_sources: List[Path] = []
    seed_dir = get_seed_dir()
    if seed_dir is not None and seed_dir != target_root:
        candidate_sources.append(seed_dir)
    ws_data = (get_workspace_root() / "data").resolve()
    if ws_data != target_root and ws_data.exists():
        candidate_sources.append(ws_data)
    bundle_data = (get_bundle_root() / "data").resolve()
    if bundle_data != target_root and bundle_data.exists() and bundle_data not in candidate_sources:
        candidate_sources.append(bundle_data)

    copied: List[str] = []
    skipped_existing: List[str] = []
    missing_sources: List[str] = []

    for rel in PUBLIC_SEED_FILES:
        dst = target_root / rel
        if dst.exists() and not force:
            skipped_existing.append(rel)
            continue
        src_found: Optional[Path] = None
        for src_root in candidate_sources:
            cand = src_root / rel
            if cand.is_file() and cand.stat().st_size > 0:
                src_found = cand
                break
        if src_found is None:
            missing_sources.append(rel)
            continue
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            tmp_dst = dst.with_name(f"{dst.name}.seed.tmp")
            shutil.copy2(str(src_found), str(tmp_dst))
            os.replace(str(tmp_dst), str(dst))
            copied.append(rel)
        except Exception:
            missing_sources.append(rel)

    return {
        "target_dir": str(target_root),
        "seed_sources": [str(p) for p in candidate_sources],
        "copied": copied,
        "skipped_existing": skipped_existing,
        "missing_sources": missing_sources,
    }
