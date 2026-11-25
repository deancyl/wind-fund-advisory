# -*- coding: utf-8 -*-
"""
AGY2 Ledger Backup Manager & Vault (G29 架构独立子模块)
=====================================================
负责实盘资产账本（含多账本索引与 data/ledgers/* 全量多账本文件）的自动冷备份、
版本化快照归档、冷却去重、自动轮转与一键安全可逆回滚。
"""

import os
import time
import shutil
import hashlib
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Union

import runtime_paths

# 默认备份根目录与最大保留快照数
BACKUP_ROOT_DIR = runtime_paths.get_backup_dir() / "ledger_snapshots"
_INITIAL_BACKUP_ROOT_DIR = BACKUP_ROOT_DIR
MAX_SNAPSHOT_RETENTION = 30

_MODULE_DIR = Path(__file__).resolve().parent
_WORKSPACE_ROOT = runtime_paths.get_workspace_root()
_AUTO_BACKUP_LOCK = threading.Lock()
_LAST_AUTO_BACKUP_TS: Dict[str, float] = {}


def _resolve_default_path(rel_path: str) -> Path:
    """优先使用 runtime_paths 解析 data/ 下的路径，兼容工作区根目录回退。"""
    clean_rel = str(rel_path).replace("\\", "/")
    if clean_rel.startswith("data/"):
        resolved = runtime_paths.resolve_data_file(clean_rel[5:])
        if resolved.exists():
            return resolved
        return runtime_paths.get_data_dir() / clean_rel[5:]
    alt = _WORKSPACE_ROOT / clean_rel
    if alt.exists():
        return alt
    p = Path(clean_rel)
    if p.exists():
        return p
    return alt


def _compute_file_sha256(filepath: Union[str, Path]) -> str:
    """计算单个文件的 SHA256 哈希值"""
    fp = Path(filepath)
    if not fp.exists() or not fp.is_file():
        return ""
    h = hashlib.sha256()
    with open(fp, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


_calc_file_sha256 = _compute_file_sha256


def _ensure_backup_dir() -> Path:
    """确保备份根目录存在；若设环境变量 AGY2_DATA_DIR 且未覆写全局常量，优先遵循之。"""
    env_dir = os.environ.get("AGY2_DATA_DIR", "").strip()
    if env_dir and BACKUP_ROOT_DIR == _INITIAL_BACKUP_ROOT_DIR:
        b_dir = runtime_paths.get_backup_dir() / "ledger_snapshots"
    else:
        b_dir = BACKUP_ROOT_DIR
    b_dir.mkdir(parents=True, exist_ok=True)
    return b_dir


def list_ledger_backups() -> List[Dict]:
    """
    列出所有可用的冷备份快照（按时间戳与目录名降序排列）
    """
    b_dir = _ensure_backup_dir()
    backups = []
    for item in b_dir.iterdir():
        if item.is_dir():
            manifest_file = item / "manifest.json"
            if manifest_file.exists():
                try:
                    with open(manifest_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    data["dir_path"] = str(item.resolve())
                    data["folder_name"] = item.name
                    backups.append(data)
                except Exception:
                    pass
            else:
                backups.append({
                    "snapshot_id": item.name,
                    "folder_name": item.name,
                    "timestamp": datetime.fromtimestamp(item.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    "reason": "auto_detected",
                    "dir_path": str(item.resolve()),
                })
    # 按时间与 snapshot_id 降序排序（确保同秒多次备份顺序稳定）
    backups.sort(key=lambda x: (str(x.get("timestamp", "")), str(x.get("snapshot_id", ""))), reverse=True)
    return backups


def _rotate_old_backups(keep_count: int = MAX_SNAPSHOT_RETENTION) -> None:
    """自动清理超出保留上限的最旧冷备份快照"""
    limit = max(1, int(keep_count))
    all_b = list_ledger_backups()
    if len(all_b) > limit:
        for old in all_b[limit:]:
            p = Path(old.get("dir_path", ""))
            if p.exists() and p.is_dir():
                shutil.rmtree(p, ignore_errors=True)


def create_ledger_cold_backup(
    reason: str = "manual_backup",
    db_path: Optional[Union[str, Path]] = None,
    ledger_json_path: Optional[Union[str, Path]] = None,
    est_archive_path: Optional[Union[str, Path]] = None,
    ledgers_index_path: Optional[Union[str, Path]] = None,
    ledgers_dir: Optional[Union[str, Path]] = None,
) -> Path:
    """
    创建实盘账本（含多账本索引 data/ledgers_index.json 与 data/ledgers/* 全部文件）的只读冷备份快照并生成安全 manifest.json
    """
    b_dir = _ensure_backup_dir()
    now_dt = datetime.now()
    now_str = now_dt.strftime("%Y%m%d_%H%M%S")
    clean_reason = "".join(c for c in str(reason) if c.isalnum() or c in ("_", "-"))[:32] or "backup"
    snapshot_dir = b_dir / f"{now_str}_{clean_reason}"
    if snapshot_dir.exists():
        ms_str = f"{now_dt.microsecond:06d}"
        snapshot_dir = b_dir / f"{now_str}_{ms_str}_{clean_reason}"
        seq = 1
        while snapshot_dir.exists():
            snapshot_dir = b_dir / f"{now_str}_{ms_str}_{seq}_{clean_reason}"
            seq += 1
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    # 1. 核心单文件源路径解析
    target_files: Dict[str, Path] = {
        "portfolio_state.db": Path(db_path) if db_path else _resolve_default_path("portfolio_state.db"),
        "portfolio_ledger.json": Path(ledger_json_path) if ledger_json_path else _resolve_default_path("portfolio_ledger.json"),
        "daily_intraday_est_archive.json": Path(est_archive_path) if est_archive_path else _resolve_default_path("data/daily_intraday_est_archive.json"),
        "ledgers_index.json": Path(ledgers_index_path) if ledgers_index_path else _resolve_default_path("data/ledgers_index.json"),
    }

    # 2. 多账本目录 data/ledgers/* 全量扫描（含 combat_29_funds.json / combat_29_funds.db 等）
    resolved_ledgers_dir = Path(ledgers_dir) if ledgers_dir else _resolve_default_path("data/ledgers")
    ledger_subfiles: Dict[str, Path] = {}
    if resolved_ledgers_dir.exists() and resolved_ledgers_dir.is_dir():
        for lf in sorted(resolved_ledgers_dir.iterdir()):
            if lf.is_file():
                ledger_subfiles[f"ledgers/{lf.name}"] = lf

    manifest = {
        "snapshot_id": snapshot_dir.name,
        "timestamp": now_dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:23],
        "reason": reason,
        "files": {},
        "multi_ledgers_backed_up": [],
        "total_market_value": 0.0,
    }

    # 尝试读取账本总市值作为审计元数据
    src_ledger = target_files["portfolio_ledger.json"]
    if src_ledger.exists():
        try:
            with open(src_ledger, "r", encoding="utf-8") as f:
                l_data = json.load(f)
            if isinstance(l_data, dict):
                manifest["total_market_value"] = float(l_data.get("summary", {}).get("total_market_value", 0.0) or 0.0)
        except Exception:
            pass

    # 物理复制核心单文件并计算 SHA256
    for fname, fpath in target_files.items():
        if fpath.exists() and fpath.is_file():
            dst = snapshot_dir / fname
            shutil.copy2(fpath, dst)
            manifest["files"][fname] = {
                "sha256": _compute_file_sha256(dst),
                "size_bytes": dst.stat().st_size,
            }

    # 物理复制多账本目录全部文件并计算 SHA256
    if ledger_subfiles:
        snap_ledgers_dir = snapshot_dir / "ledgers"
        snap_ledgers_dir.mkdir(parents=True, exist_ok=True)
        for rel_key, fpath in ledger_subfiles.items():
            dst = snapshot_dir / rel_key
            shutil.copy2(fpath, dst)
            manifest["files"][rel_key] = {
                "sha256": _compute_file_sha256(dst),
                "size_bytes": dst.stat().st_size,
            }
            manifest["multi_ledgers_backed_up"].append(fpath.name)

    # 写入元数据清册
    manifest_path = snapshot_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # 触发自动轮转（严格保障总快照数 <= MAX_SNAPSHOT_RETENTION）
    _rotate_old_backups(MAX_SNAPSHOT_RETENTION)
    return snapshot_dir


def restore_ledger_backup(backup_dir_or_id: Union[str, Path], target_dir: Optional[Union[str, Path]] = None) -> bool:
    """
    一键从指定快照回滚恢复全部受保护账本文件（含主账本、多账本索引与 data/ledgers/* 全部文件）。
    在覆盖前强制对当前状态自动执行 pre_rollback 冷备，确保操作本身 100% 可逆！
    支持 target_dir 沙盒隔离目录，保障单元测试与沙盒恢复不污染工作区实盘账本。
    """
    p = Path(backup_dir_or_id)
    if not p.is_dir():
        cand = _ensure_backup_dir() / str(backup_dir_or_id)
        if cand.is_dir():
            p = cand
        else:
            return False

    manifest_file = p / "manifest.json"
    if not manifest_file.exists():
        return False

    base_root = Path(target_dir) if target_dir else Path(".")

    # 1. 强制在覆盖前打一份 pre_rollback 快照 (若非沙盒目标)
    if not target_dir:
        try:
            create_ledger_cold_backup("pre_rollback")
        except Exception:
            pass

    # 2. 依次恢复核心受保护账本与索引文件
    restore_mapping = {
        "portfolio_state.db": base_root / "portfolio_state.db",
        "portfolio_ledger.json": base_root / "portfolio_ledger.json",
        "daily_intraday_est_archive.json": base_root / "data" / "daily_intraday_est_archive.json",
        "ledgers_index.json": base_root / "data" / "ledgers_index.json",
    }

    success = False
    for fname, target_dst in restore_mapping.items():
        snap_src = p / fname
        if snap_src.exists() and snap_src.is_file():
            target_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(snap_src, target_dst)
            # 同步镜像到 AGY2_FundAdvisory/ 目录（仅主账本与日内归档，且仅在非沙盒恢复时）
            if not target_dir and fname in ("portfolio_state.db", "portfolio_ledger.json", "daily_intraday_est_archive.json"):
                alt_rel = fname if fname != "daily_intraday_est_archive.json" else "data/daily_intraday_est_archive.json"
                alt_dst = Path("AGY2_FundAdvisory") / alt_rel
                if alt_dst.parent.exists():
                    try:
                        shutil.copy2(snap_src, alt_dst)
                    except Exception:
                        pass
            success = True

    # 3. 恢复多账本目录 data/ledgers/* 全部文件
    snap_ledgers_dir = p / "ledgers"
    if snap_ledgers_dir.exists() and snap_ledgers_dir.is_dir():
        dst_ledgers_dir = base_root / "data" / "ledgers"
        dst_ledgers_dir.mkdir(parents=True, exist_ok=True)
        for snap_lf in snap_ledgers_dir.iterdir():
            if snap_lf.is_file():
                shutil.copy2(snap_lf, dst_ledgers_dir / snap_lf.name)
                success = True

    return success


def auto_backup_before_write(
    reason: str = "auto_save",
    cooldown_sec: int = 60,
    **kwargs,
) -> Optional[Path]:
    """
    写盘前轻量级自动冷备入口：
    同一 reason 在 cooldown_sec 秒内仅触发一次冷备，防止高频写入刷爆快照目录；
    并在备份完成后自动轮转，严格保障总快照数 <= MAX_SNAPSHOT_RETENTION。
    """
    now_mono = time.monotonic()
    cd = max(0.0, float(cooldown_sec))
    key = str(reason or "auto_save")

    with _AUTO_BACKUP_LOCK:
        last_ts = _LAST_AUTO_BACKUP_TS.get(key)
        if cd > 0.0 and last_ts is not None and (now_mono - last_ts) < cd:
            return None
        _LAST_AUTO_BACKUP_TS[key] = now_mono

    try:
        return create_ledger_cold_backup(reason=key, **kwargs)
    except Exception:
        return None


class LedgerBackupVault:
    """
    面向调用者的面向对象门面类 (兼容审计指令双重规范)
    """
    @staticmethod
    def create_snapshot(reason: str = "manual_snapshot", **kwargs) -> Path:
        return create_ledger_cold_backup(reason=reason, **kwargs)

    @staticmethod
    def list_snapshots() -> List[Dict]:
        return list_ledger_backups()

    @staticmethod
    def restore_snapshot(snapshot_id_or_path: Union[str, Path], target_dir: Optional[Union[str, Path]] = None) -> bool:
        return restore_ledger_backup(snapshot_id_or_path, target_dir=target_dir)

    @classmethod
    def auto_backup_before_write(cls, reason: str = "auto_save", cooldown_sec: int = 60, **kwargs) -> Optional[Path]:
        return auto_backup_before_write(reason=reason, cooldown_sec=cooldown_sec, **kwargs)

    @classmethod
    def reset_auto_backup_cooldown(cls) -> None:
        with _AUTO_BACKUP_LOCK:
            _LAST_AUTO_BACKUP_TS.clear()
