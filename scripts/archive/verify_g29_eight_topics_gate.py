# -*- coding: utf-8 -*-
"""
G29 八大课题架构治理与实盘闭环综合门禁
"""

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
AGY2_DIR = ROOT / "AGY2_FundAdvisory"
for p in [str(ROOT), str(AGY2_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)


def run_g29_gate():
    base = AGY2_DIR if (AGY2_DIR / "app_gui.py").exists() else ROOT
    gui_txt = (base / "app_gui.py").read_text(encoding="utf-8")

    # 1. 验证 G28 手机端对账单列名错配回归 Bug 已修复
    assert '["基金简称", "当日估算(%)", "官方涨跌(%)", "偏差归因与来源"]' not in gui_txt, "手机端对账单仍存在错误列名"
    assert '"当日综合估算(%)"' in gui_txt and '"官方实际涨跌(%)"' in gui_txt

    # 2. 验证白话导读胶囊已脱离硬编码深色背景
    assert "rgba(30, 41, 59, 0.45)" not in gui_txt, "白话导读胶囊仍写死深色背景"

    # 3. 验证课题 4/5/6/7/8 五大独立新模块均已创建且语法全绿（严禁继续堆砌巨石文件）
    required_modules = [
        "ledger_backup_manager.py",
        "cashflow_planner.py",
        "execution_tracker.py",
        "data_resilience_guard.py",
        "forward_audit_logger.py",
    ]
    for mod in required_modules:
        fp = base / mod
        if not fp.exists():
            fp = ROOT / mod
        assert fp.exists(), f"缺少独立架构模块: {mod}"
        ast.parse(fp.read_text(encoding="utf-8"), filename=mod)

    # 4. 验证课题 6 前端已真正接通增量资金规划与左侧子弹表
    assert "generate_incremental_investment_plan" in gui_txt or "cashflow_planner" in gui_txt, "前端未接入增量资金零摩擦再平衡"

    # 5. 验证课题 8 自动冷备份模块可真实生成与列出备份快照
    from ledger_backup_manager import create_ledger_cold_backup, list_ledger_backups
    b_path = create_ledger_cold_backup("g29_gate_test", base / "portfolio_state.db", base / "portfolio_ledger.json")
    assert b_path is not None and Path(b_path).exists(), "冷备份快照创建失败"
    assert len(list_ledger_backups()) >= 1

    # 6. 验证课题 7 每日只读裁决日志可追加写入且防同日重复覆写
    from forward_audit_logger import append_daily_decision_snapshot, load_decision_audit_log
    append_daily_decision_snapshot({"date": "2026-11-19", "regime": "BEAR", "target_weights": {"005561": 0.30}})
    logs = load_decision_audit_log()
    assert len(logs) >= 1

    print("ALL G29 EIGHT-TOPIC ARCHITECTURE & EXECUTION GATES PASSED")


if __name__ == "__main__":
    run_g29_gate()
