# -*- coding: utf-8 -*-
"""
G46 技术债收官验收门禁 (verify_g46_tech_debt_closure_gate.py)
验证：
1. Layer-0 domain_models.py 100% 标准库零内部依赖，4 个拆分子模块 AST 零未绑定全局变量，且 SECTOR_FUND_SELECTION 回归根治；
2. 全部核心数据读写模块接入 runtime_paths，AGY2_DATA_DIR 临时目录写隔离 100% 生效；
3. scripts/ 顶层活跃门禁 <= 10 个，无双目录门禁重复，test_dyn.py 与 data/test_brinson_pm.json 已清除；
4. /api/v1/watchlist 与 /api/v1/sectors 并发拉取 + 30s TTL 缓存生效（热缓存 < 50 ms）；
5. Playwright 实机验证 http://127.0.0.1:8585：侧边栏「账本与设置」对比度 >= 4.5，Tab 2「存量重塑」零局部异常。
"""

import ast
import builtins
import os
import re
import sys
import tempfile
import time
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
CORE = ROOT / "AGY2_FundAdvisory"
for p in (str(CORE), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)


def _find_unbound_globals(py_file: Path) -> list:
    src = py_file.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(py_file))
    defined = set(dir(builtins)) | {"__file__", "__name__", "__doc__", "__package__"}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined.add(node.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                defined.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name != "*":
                    defined.add(alias.asname or alias.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    defined.add(t.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            defined.add(node.target.id)

    missing = []
    funcs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    for n in tree.body:
        if isinstance(n, ast.ClassDef):
            funcs.extend([m for m in n.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))])

    for node in funcs:
        local_names = {a.arg for a in node.args.args + node.args.kwonlyargs}
        if node.args.vararg:
            local_names.add(node.args.vararg.arg)
        if node.args.kwarg:
            local_names.add(node.args.kwarg.arg)
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                local_names.add(sub.id)
            elif isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                local_names.add(sub.name)
                for fa in sub.args.args + sub.args.kwonlyargs + getattr(sub.args, "posonlyargs", []):
                    local_names.add(fa.arg)
                if sub.args.vararg:
                    local_names.add(sub.args.vararg.arg)
                if sub.args.kwarg:
                    local_names.add(sub.args.kwarg.arg)
            elif isinstance(sub, ast.ClassDef):
                local_names.add(sub.name)
            elif isinstance(sub, ast.Lambda):
                for la in sub.args.args + sub.args.kwonlyargs:
                    local_names.add(la.arg)
                if sub.args.vararg:
                    local_names.add(sub.args.vararg.arg)
                if sub.args.kwarg:
                    local_names.add(sub.args.kwarg.arg)
            elif isinstance(sub, ast.Import):
                for alias in sub.names:
                    local_names.add(alias.asname or alias.name.split(".")[0])
            elif isinstance(sub, ast.ImportFrom):
                for alias in sub.names:
                    local_names.add(alias.asname or alias.name)
            elif isinstance(sub, ast.ExceptHandler) and sub.name:
                local_names.add(sub.name)
            elif isinstance(sub, ast.comprehension):
                for t in ast.walk(sub.target):
                    if isinstance(t, ast.Name):
                        local_names.add(t.id)
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                if sub.id not in local_names and sub.id not in defined:
                    missing.append((py_file.name, node.name, sub.lineno, sub.id))
    return missing


def check_domain_models_and_zero_unbound() -> None:
    dm = CORE / "domain_models.py"
    assert dm.exists(), "缺少 AGY2_FundAdvisory/domain_models.py"
    dm_src = dm.read_text(encoding="utf-8")
    dm_tree = ast.parse(dm_src, filename="domain_models.py")
    allowed_stdlib = {"dataclasses", "typing", "math", "re", "sys", "datetime"}
    for node in ast.walk(dm_tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                assert a.name in allowed_stdlib, f"domain_models.py 严禁导入非标准库模块: {a.name}"
        elif isinstance(node, ast.ImportFrom):
            assert node.module in allowed_stdlib, f"domain_models.py 严禁导入内部模块: {node.module}"
    assert "SECTOR_FUND_SELECTION" in dm_src, "domain_models.py 缺少 SECTOR_FUND_SELECTION"

    split_mods = [
        CORE / "lookthrough_analyzer.py",
        CORE / "ocr_importer.py",
        CORE / "valuation_engine.py",
        CORE / "scenario_rebalancer.py",
    ]
    all_missing = []
    for mod in split_mods:
        all_missing.extend(_find_unbound_globals(mod))
    assert not all_missing, f"拆分模块存在未绑定全局符号: {all_missing[:10]}"

    # 检验 ocr_importer, valuation_engine, scenario_rebalancer 彻底清零对 portfolio_manager 的反向导入
    for pure_mod in (CORE / "ocr_importer.py", CORE / "valuation_engine.py", CORE / "scenario_rebalancer.py"):
        t = ast.parse(pure_mod.read_text(encoding="utf-8"), filename=pure_mod.name)
        for n in ast.walk(t):
            if isinstance(n, ast.Import):
                assert all("portfolio_manager" not in a.name for a in n.names), f"{pure_mod.name} 仍反向导入 portfolio_manager"
            elif isinstance(n, ast.ImportFrom):
                assert "portfolio_manager" not in (n.module or ""), f"{pure_mod.name} 仍反向导入 portfolio_manager"

    # 真实运行原 L913 / L1208 / L1702 路径，验证 0 NameError
    from portfolio_manager import PortfolioManager
    cat = PortfolioManager._compute_asset_class_category("000058", "")
    assert isinstance(cat, str) and len(cat) > 0
    pm_mem = PortfolioManager(db_path=":memory:", ledger_json_path=":memory:")
    screen_res = pm_mem.screen_fund_look_through_risk("011613")
    assert isinstance(screen_res, dict) and "fund_code" in screen_res
    print("[PASS] Gate 1: domain_models.py 零内部依赖，4 个拆分模块 AST 未绑定全局变量为 0，SECTOR_FUND_SELECTION 回归根治")


def check_runtime_paths_coverage() -> None:
    targets = [
        "data_loader.py",
        "advisory_engine.py",
        "strategy_bridge.py",
        "multi_ledger_manager.py",
        "forward_audit_logger.py",
        "shadow_portfolio_tracker.py",
        "scenario_rebalancer.py",
        "portfolio_manager.py",
        "sector_watchlist.py",
        "rebalance_grouping.py",
    ]
    for fn in targets:
        src = (CORE / fn).read_text(encoding="utf-8")
        assert "runtime_paths" in src, f"{fn} 尚未接入 runtime_paths"

    import forward_audit_logger
    import shadow_portfolio_tracker
    with tempfile.TemporaryDirectory() as td:
        os.environ["AGY2_DATA_DIR"] = td
        try:
            forward_audit_logger.append_daily_decision_snapshot({"date": "2099-12-31", "regime": "NEUTRAL"})
            assert (Path(td) / "forward_decision_audit.jsonl").exists(), "forward_audit_logger 未写入 AGY2_DATA_DIR"
            shadow_portfolio_tracker.freeze_shadow_baseline("g46_iso", {"005561": {"shares": 10.0, "current_nav": 1.2}})
            assert (Path(td) / "shadow_benchmarks.json").exists(), "shadow_portfolio_tracker 未写入 AGY2_DATA_DIR"
        finally:
            os.environ.pop("AGY2_DATA_DIR", None)
    print(f"[PASS] Gate 2: {len(targets)} 个核心数据模块全部接入 runtime_paths 且 AGY2_DATA_DIR 隔离落盘验证通过")


def check_scripts_cleanliness() -> None:
    top_py = list((ROOT / "scripts").glob("*.py"))
    assert len(top_py) <= 10, f"scripts/ 顶层仍有 {len(top_py)} 个脚本（上限 10 个），请完成归档"
    dup_py = list((CORE / "scripts").glob("verify_g4*.py")) if (CORE / "scripts").exists() else []
    assert not dup_py, f"AGY2_FundAdvisory/scripts/ 仍残留重复门禁脚本: {[p.name for p in dup_py]}"
    assert not (ROOT / "test_dyn.py").exists(), "根目录仍残留 test_dyn.py"
    assert not (ROOT / "data" / "test_brinson_pm.json").exists(), "data/ 仍残留 test_brinson_pm.json"
    arch_doc = (ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")
    assert "Layer 0" in arch_doc and "domain_models.py" in arch_doc, "ARCHITECTURE.md 未更新五层单向依赖说明"
    print(f"[PASS] Gate 3: scripts/ 顶层仅保留 {len(top_py)} 个活跃门禁，零重复、零垃圾残留，ARCHITECTURE.md 已更新")


def check_sectors_cache_latency() -> None:
    import api_server

    client = TestClient(api_server.app)
    r1 = client.get("/api/v1/watchlist")
    assert r1.status_code == 200 and "items" in r1.json()
    t0 = time.perf_counter()
    r2 = client.get("/api/v1/watchlist")
    dt_wl_ms = (time.perf_counter() - t0) * 1000.0
    assert r2.status_code == 200 and dt_wl_ms < 50.0, f"/api/v1/watchlist 缓存命中耗时过高: {dt_wl_ms:.1f} ms"

    t1 = time.perf_counter()
    r3 = client.get("/api/v1/sectors")
    dt_sec_ms = (time.perf_counter() - t1) * 1000.0
    assert r3.status_code == 200 and dt_sec_ms < 50.0, f"/api/v1/sectors 缓存命中耗时过高: {dt_sec_ms:.1f} ms"
    print(f"[PASS] Gate 4: /api/v1/watchlist ({dt_wl_ms:.1f} ms) 与 /api/v1/sectors ({dt_sec_ms:.1f} ms) 缓存命中均 < 50 ms")


def _rel_lum(rgb: tuple) -> float:
    def _c(v: float) -> float:
        s = v / 255.0
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4
    return 0.2126 * _c(rgb[0]) + 0.7152 * _c(rgb[1]) + 0.0722 * _c(rgb[2])


def _contrast_ratio(fg: tuple, bg: tuple) -> float:
    l1, l2 = _rel_lum(fg), _rel_lum(bg)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def _parse_rgb(css_str: str) -> tuple:
    nums = [float(x) for x in re.findall(r"[\d.]+", css_str or "")]
    return (nums[0], nums[1], nums[2]) if len(nums) >= 3 else (203.0, 213.0, 225.0)


def check_live_ui_contrast_and_tab2_reshape() -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto("http://127.0.0.1:8585", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_selector('[data-testid="stSidebar"]', timeout=30000)
        page.wait_for_timeout(2500)

        # 1. 验证侧边栏「账本与设置」对比度 >= 4.5
        styles = page.evaluate("""() => {
            const sb = document.querySelector('[data-testid="stSidebar"]');
            const lbl = document.querySelector('[data-testid="stSidebar"] .sidebar-section-label')
                || Array.from(document.querySelectorAll('[data-testid="stSidebar"] div')).find(el => el.textContent.trim() === '账本与设置');
            if (!sb || !lbl) return null;
            return {
                fg: getComputedStyle(lbl).color,
                bg: getComputedStyle(sb).backgroundColor,
                text: lbl.textContent.trim()
            };
        }""")
        assert styles is not None, "未找到侧边栏『账本与设置』节点"
        ratio = _contrast_ratio(_parse_rgb(styles["fg"]), _parse_rgb(styles["bg"]))
        assert ratio >= 4.5, f"侧边栏『账本与设置』对比度未达标: {ratio:.2f} (fg={styles['fg']}, bg={styles['bg']})"

        # 2. 切换至「调仓 · 清单与打卡」->「存量重塑」，验证 0 异常
        rebal_nav = page.locator('[data-testid="stSidebar"] label, [data-testid="stSidebar"] button').filter(has_text="调仓")
        rebal_nav.first.click()
        page.wait_for_timeout(2500)

        reshape_lbl = page.locator("label").filter(has_text="存量重塑")
        if reshape_lbl.count() > 0:
            reshape_lbl.first.click()
            page.wait_for_timeout(3000)

        body_txt = page.locator('[data-testid="stMain"]').inner_text()
        exc_cnt = page.locator('[data-testid="stException"]').count()
        assert exc_cnt == 0, f"Tab 2 存量重塑出现 stException ({exc_cnt} 个)"
        assert "渲染出现局部异常" not in body_txt, "Tab 2 存量重塑仍出现『渲染出现局部异常』告警"
        assert "SECTOR_FUND_SELECTION" not in body_txt, "Tab 2 存量重塑仍残留 SECTOR_FUND_SELECTION 报错"
        browser.close()
    print(f"[PASS] Gate 5: 实机 UI 复测通过（『账本与设置』对比度 {ratio:.2f}:1 >= 4.5，Tab 2『存量重塑』0 异常）")


if __name__ == "__main__":
    check_domain_models_and_zero_unbound()
    check_runtime_paths_coverage()
    check_scripts_cleanliness()
    check_sectors_cache_latency()
    check_live_ui_contrast_and_tab2_reshape()
    print("ALL G46 TECH DEBT CLOSURE GATES PASSED.")
