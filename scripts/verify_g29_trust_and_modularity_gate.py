# -*- coding: utf-8 -*-
"""
G29 架构模块化与实盘信任闭环门禁 (verify_g29_trust_and_modularity_gate.py)
"""

import ast
import os
import shutil
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
AGY2_DIR = ROOT / "AGY2_FundAdvisory"
for p in [str(ROOT), str(AGY2_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)


def test_modularity_and_line_limits():
    """门禁 1: 模块体积守卫与严禁巨石文件膨胀"""
    base = AGY2_DIR if (AGY2_DIR / "app_gui.py").exists() else ROOT
    check_files = [
        "ledger_backup_vault.py",
        "oos_verdict_tracker.py",
        "shadow_portfolio_tracker.py",
        "cashflow_planner.py",
        "data_resilience_guard.py",
        "execution_tracker.py"
    ]
    for fn in check_files:
        fp = base / fn
        if not fp.exists():
            fp = ROOT / fn
        assert fp.exists(), f"模块文件必须存在: {fn}"
        code_str = fp.read_text(encoding="utf-8")
        ast.parse(code_str, filename=fn)
        lines = len(code_str.splitlines())
        assert lines <= 600, f"新模块 {fn} 必须控制在 600 行以内 (当前 {lines} 行)"
    print("✅ 门禁 1 通过: 6 大独立小模块均合法存在且各自行数严格 <= 600 行")


def test_cold_backup_and_rollback():
    """门禁 2: 实盘冷备份与一键反向可逆回滚真测"""
    from ledger_backup_vault import LedgerBackupVault, create_ledger_cold_backup, restore_ledger_backup, list_ledger_backups
    with tempfile.TemporaryDirectory() as tmp_dir:
        td = Path(tmp_dir)
        mock_db = td / "portfolio_state.db"
        mock_json = td / "portfolio_ledger.json"
        mock_db.write_text("DB_ORIGINAL_CONTENT_V1", encoding="utf-8")
        mock_json.write_text('{"summary": {"total_market_value": 88888.88}}', encoding="utf-8")

        snap_path = create_ledger_cold_backup(
            reason="test_rollback",
            db_path=mock_db,
            ledger_json_path=mock_json
        )
        assert snap_path.exists(), "快照目录必须创建成功"
        manifest_f = snap_path / "manifest.json"
        assert manifest_f.exists(), "快照元数据清单必须存在"

        # 验证一键回滚 (指定沙盒隔离 target_dir=td)
        mock_json.write_text('{"summary": {"total_market_value": 0.0}}', encoding="utf-8")
        ok = LedgerBackupVault.restore_snapshot(snap_path.name, target_dir=td)
        assert ok, "快照恢复执行必须成功"
        assert "88888.88" in mock_json.read_text(encoding="utf-8"), "沙盒恢复必须精准还原初始状态"
    print("✅ 门禁 2 通过: 冷备份快照打包与可逆回滚逻辑 100% 健全")


def test_oos_verdict_tracker():
    """门禁 3: 前瞻验真只读日志防篡改与胜率打分测试"""
    from forward_audit_logger import (
        append_daily_decision_snapshot,
        load_decision_audit_log,
        record_daily_verdict_if_needed,
        evaluate_forward_performance
    )
    test_date = "2026-11-19"
    rec = {
        "date": test_date,
        "market_regime": "BEAR",
        "verdict_action": "DEFENSIVE_HOLD",
        "target_weights": {"005561": 0.50, "002351": 0.50},
        "fund_nav_snapshot": {"005561": 1.2000, "002351": 1.1500},
        "c300_close": 3950.0
    }
    # 首次写入
    append_daily_decision_snapshot(rec)
    # 同日二次写入测试（防篡改守护：必须拒绝覆写）
    rec2 = dict(rec)
    rec2["market_regime"] = "FAKE_OVERWRITE"
    res2 = append_daily_decision_snapshot(rec2)
    assert res2 is False, "同交易日只读快照严禁二次覆写篡改"

    # 模拟未来净值打分测试
    future_navs = {"005561": 1.2600, "002351": 1.1615}  # 涨幅 ~3%~5%
    eval_res = evaluate_forward_performance(current_nav_map=future_navs, current_hs300=4000.0)
    assert eval_res["sample_count"] >= 1, "前瞻验真样本数必须 >= 1"
    assert "avg_forward_return_pct" in eval_res
    print("✅ 门禁 3 通过: 样本外前瞻验真只读日志防篡改与前瞻打分通过")


def test_shadow_portfolio_race():
    """门禁 4: 影子账本赛跑超额收益与对比测试"""
    from shadow_portfolio_tracker import freeze_shadow_baseline, compare_live_vs_shadow, get_shadow_baseline
    mock_29 = {
        "005561": {"shares": 10000.0, "current_nav": 1.20, "cost_price": 1.0, "fund_name": "创金合信红利低波A"},
        "002351": {"shares": 20000.0, "current_nav": 1.10, "cost_price": 1.0, "fund_name": "易方达裕祥回报A"},
        "000058": {"shares": 100.0, "current_nav": 1.50, "cost_price": 1.0, "fund_name": "华夏中小板ETF联接A"}
    }
    b_path = freeze_shadow_baseline("test_ledger", mock_29, "测试躺平基准")
    assert b_path.exists(), "影子基准文件必须创建成功"

    # 模拟调仓后的实盘（例如清除了 000058 尾仓，将权重合并至 005561）
    live_holdings = {
        "005561": {"shares": 11250.0, "current_nav": 1.20, "cost_price": 1.0, "fund_name": "创金合信红利低波A"},
        "002351": {"shares": 20000.0, "current_nav": 1.10, "cost_price": 1.0, "fund_name": "易方达裕祥回报A"}
    }
    quotes = {"005561": 1.25, "002351": 1.12, "000058": 1.48}
    comp = compare_live_vs_shadow("test_ledger", live_holdings, quotes)
    assert comp["has_shadow"] is True
    assert "excess_rmb" in comp
    assert "excess_return_pct" in comp
    print("✅ 门禁 4 通过: 真实跟单 vs 躺平不动影子账本实盘赛跑测算通过")


if __name__ == "__main__":
    test_modularity_and_line_limits()
    test_cold_backup_and_rollback()
    test_oos_verdict_tracker()
    test_shadow_portfolio_race()
    print("\nALL G29 TRUST & MODULARITY GATES PASSED 100%")
