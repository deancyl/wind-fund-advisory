# -*- coding: utf-8 -*-
import inspect
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT.parent if ROOT.name == "AGY2_FundAdvisory" else ROOT
AGY2 = REPO / "AGY2_FundAdvisory"
for p in (str(AGY2), str(REPO)):
    if p not in sys.path:
        sys.path.insert(0, p)


def main() -> None:
    # 1. 消除 11 文件双镜像：根目录转发入口 <= 25 行
    mirrored = (
        "api_server.py",
        "app_gui.py",
        "strategy_bridge.py",
        "cashflow_planner.py",
        "data_resilience_guard.py",
        "execution_tracker.py",
        "forward_audit_logger.py",
        "ledger_backup_vault.py",
        "rebalance_grouping.py",
        "sector_watchlist.py",
        "shadow_portfolio_tracker.py",
    )
    for fn in mirrored:
        root_f = REPO / fn
        if root_f.exists() and root_f.resolve() != (AGY2 / fn).resolve():
            n = len(root_f.read_text(encoding="utf-8").splitlines())
            assert n <= 25, f"根目录 {fn} 仍为大文件镜像 ({n} 行)，未改为薄转发入口"

    # 2. 清除 4 处 Mock 假数据 + 并发锁 + 同步 OCR + 合并 /sectors 重复实现
    api_src = (AGY2 / "api_server.py").read_text(encoding="utf-8")
    for bad in ('"equity": 0.65', '"max_overlap_pct": 0.76', '"2018年单边阴跌": -0.165', '"annualized_return_pct": 14.8'):
        assert bad not in api_src, f"api_server.py 仍残留 Mock 假数据: {bad}"
    assert "_LEDGER_WRITE_LOCK" in api_src, "缺少并发写锁 _LEDGER_WRITE_LOCK"
    assert "def api_v1_import_ocr(" in api_src, "api_v1_import_ocr 必须为同步 def"

    import api_server
    assert not inspect.iscoroutinefunction(api_server.api_v1_import_ocr), "api_v1_import_ocr 仍为阻塞 async def"

    # 3. 4 个接口 + /api/v1/watchlist 真实返回 200
    from fastapi.testclient import TestClient
    client = TestClient(api_server.app)
    for sv in ("exposure", "overlap", "stress_test", "ten_dim_votes"):
        r = client.get(f"/api/v1/diagnose/{sv}")
        assert r.status_code == 200, f"/api/v1/diagnose/{sv} HTTP {r.status_code}: {r.text}"
        assert r.json().get("subview") == sv
    r_bt = client.get("/api/v1/backtest/summary")
    assert r_bt.status_code == 200 and r_bt.json().get("source") == "evolution_db_trial29_and_forward_audit"
    r_wl = client.get("/api/v1/watchlist")
    assert r_wl.status_code == 200 and "items" in r_wl.json()

    # 4. 跨平台依赖清单合规
    req_api = (REPO / "requirements-api.txt").read_text(encoding="utf-8").lower()
    for banned in ("pywin32", "pefile", "streamlit", "playwright"):
        assert banned not in req_api, f"requirements-api.txt 包含违禁依赖: {banned}"
    for must in ("fastapi", "uvicorn", "pandas", "duckdb"):
        assert must in req_api, f"requirements-api.txt 缺少核心依赖: {must}"
    assert (REPO / "requirements-dev.txt").exists(), "缺少 requirements-dev.txt"

    # 5. runtime_paths 环境变量隔离实测
    import runtime_paths
    with tempfile.TemporaryDirectory() as td:
        os.environ["AGY2_DATA_DIR"] = td
        try:
            assert runtime_paths.get_data_dir() == Path(td).resolve()
        finally:
            os.environ.pop("AGY2_DATA_DIR", None)

    # 6. 活跃门禁脚本无失效引用 & 架构导览/契约存在
    _stale_target = "ui_daily_" + "brief.py"
    for sp in (REPO / "scripts").glob("verify_g*.py"):
        assert _stale_target not in sp.read_text(encoding="utf-8", errors="ignore"), f"活跃脚本仍引用已删文件: {sp.name}"
    assert (REPO / "ARCHITECTURE.md").exists(), "缺少 ARCHITECTURE.md"
    assert (REPO / "pytest.ini").exists(), "缺少 pytest.ini"
    assert (AGY2 / "docs" / "openapi_v1.json").exists(), "缺少 AGY2_FundAdvisory/docs/openapi_v1.json"
    print("ALL G44 DEBT FOUNDATION GATES PASSED")


if __name__ == "__main__":
    main()
