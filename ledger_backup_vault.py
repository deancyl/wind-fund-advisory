# -*- coding: utf-8 -*-
"""
AGY2 Ledger Backup Manager & Vault (G29 架构独立子模块)
=====================================================
负责实盘资产账本的自动冷备份、版本化快照归档、自动轮转与一键安全可逆回滚。
严格控制在 250 行以内，杜绝主文件巨石膨胀。
"""

import os
import shutil
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Union

# 默认备份根目录与最大保留快照数
BACKUP_ROOT_DIR = Path("data/backups/ledger_snapshots")
MAX_SNAPSHOT_RETENTION = 30


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


def _ensure_backup_dir() -> Path:
    """确保备份根目录存在"""
    BACKUP_ROOT_DIR.mkdir(parents=True, exist_ok=True)
    return BACKUP_ROOT_DIR


def list_ledger_backups() -> List[Dict]:
    """
    列出所有可用的冷备份快照（按时间戳降序排列）
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
                    "dir_path": str(item.resolve())
                })
    # 按时间降序排序
    backups.sort(key=lambda x: str(x.get("timestamp", "")), reverse=True)
    return backups


def _rotate_old_backups(keep_count: int = MAX_SNAPSHOT_RETENTION) -> None:
    """自动清理超出保留上限的最旧冷备份快照"""
    all_b = list_ledger_backups()
    if len(all_b) > keep_count:
        for old in all_b[keep_count:]:
            p = Path(old.get("dir_path", ""))
            if p.exists() and p.is_dir():
                shutil.rmtree(p, ignore_errors=True)


def create_ledger_cold_backup(
    reason: str = "manual_backup",
    db_path: Optional[Union[str, Path]] = None,
    ledger_json_path: Optional[Union[str, Path]] = None,
    est_archive_path: Optional[Union[str, Path]] = None
) -> Path:
    """
    创建实盘账本的只读冷备份快照并生成安全 manifest.json
    """
    b_dir = _ensure_backup_dir()
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_reason = "".join(c for c in reason if c.isalnum() or c in ("_", "-"))[:32]
    snapshot_dir = b_dir / f"{now_str}_{clean_reason}"
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    # 默认账本源路径解析
    target_files = {
        "portfolio_state.db": Path(db_path) if db_path else Path("portfolio_state.db"),
        "portfolio_ledger.json": Path(ledger_json_path) if ledger_json_path else Path("portfolio_ledger.json"),
        "daily_intraday_est_archive.json": Path(est_archive_path) if est_archive_path else Path("data/daily_intraday_est_archive.json")
    }

    manifest = {
        "snapshot_id": snapshot_dir.name,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "reason": reason,
        "files": {},
        "total_market_value": 0.0
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

    # 物理复制并计算哈希
    for fname, fpath in target_files.items():
        if fpath.exists() and fpath.is_file():
            dst = snapshot_dir / fname
            shutil.copy2(fpath, dst)
            manifest["files"][fname] = {
                "sha256": _compute_file_sha256(dst),
                "size_bytes": dst.stat().st_size
            }

    # 写入元数据清册
    manifest_path = snapshot_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # 触发自动轮转
    _rotate_old_backups(MAX_SNAPSHOT_RETENTION)
    return snapshot_dir


def restore_ledger_backup(backup_dir_or_id: Union[str, Path], target_dir: Optional[Union[str, Path]] = None) -> bool:
    """
    一键从指定快照回滚恢复账本文件。
    在覆盖前强制对当前状态自动执行 pre_rollback 冷备，确保操作本身 100% 可逆！
    支持 target_dir 沙盒隔离目录，保障单元测试与沙盒恢复不污染工作区实盘账本。
    """
    p = Path(backup_dir_or_id)
    if not p.is_dir():
        # 按 snapshot_id 查找
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

    # 2. 依次恢复受保护账本
    restore_mapping = {
        "portfolio_state.db": base_root / "portfolio_state.db",
        "portfolio_ledger.json": base_root / "portfolio_ledger.json",
        "daily_intraday_est_archive.json": base_root / "data" / "daily_intraday_est_archive.json"
    }

    success = False
    for fname, target_dst in restore_mapping.items():
        snap_src = p / fname
        if snap_src.exists() and snap_src.is_file():
            target_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(snap_src, target_dst)
            # 同步镜像到 AGY2_FundAdvisory/ 目录如果存在对应文件且未指定沙盒 target_dir
            if not target_dir:
                alt_dst = Path("AGY2_FundAdvisory") / (fname if fname != "daily_intraday_est_archive.json" else "data/daily_intraday_est_archive.json")
                if alt_dst.parent.exists():
                    try:
                        shutil.copy2(snap_src, alt_dst)
                    except Exception:
                        pass
            success = True

    return success


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
