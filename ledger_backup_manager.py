# -*- coding: utf-8 -*-
"""
AGY2 Ledger Backup Manager (Thin Facade for Backward Compatibility)
===================================================================
所有冷备份与安全回滚核心实现已统一收敛至 ledger_backup_vault.py，
本文件作为兼容薄代理，杜绝双份代码维护冗余。
"""

try:
    from ledger_backup_vault import (
        LedgerBackupVault,
        create_ledger_cold_backup,
        list_ledger_backups,
        restore_ledger_backup,
        _ensure_backup_dir,
        _calc_file_sha256,
        _compute_file_sha256,
    )
except Exception:
    from AGY2_FundAdvisory.ledger_backup_vault import (
        LedgerBackupVault,
        create_ledger_cold_backup,
        list_ledger_backups,
        restore_ledger_backup,
        _ensure_backup_dir,
        _calc_file_sha256,
        _compute_file_sha256,
    )

__all__ = [
    "LedgerBackupVault",
    "create_ledger_cold_backup",
    "list_ledger_backups",
    "restore_ledger_backup",
    "_ensure_backup_dir",
    "_calc_file_sha256",
    "_compute_file_sha256",
]
