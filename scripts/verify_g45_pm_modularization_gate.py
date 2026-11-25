# -*- coding: utf-8 -*-
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGY2 = ROOT / "AGY2_FundAdvisory" if ROOT.name != "AGY2_FundAdvisory" else ROOT
for p in (str(AGY2), str(ROOT.parent if ROOT.name == "AGY2_FundAdvisory" else ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)


def _check_no_duplicate_top_defs(py_path: Path) -> None:
    tree = ast.parse(py_path.read_text(encoding="utf-8"), filename=py_path.name)
    seen = {}
    dups = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name in seen:
                dups.append((node.name, seen[node.name], node.lineno))
            else:
                seen[node.name] = node.lineno
    assert not dups, f"{py_path.name} 存在重复顶层定义: {dups}"


def main() -> None:
    new_mods = [
        "ocr_importer.py",
        "valuation_engine.py",
        "lookthrough_analyzer.py",
        "scenario_rebalancer.py",
    ]
    for fn in new_mods:
        p = AGY2 / fn
        assert p.exists(), f"缺少拆分子模块: {fn}"
        _check_no_duplicate_top_defs(p)

    pm_path = AGY2 / "portfolio_manager.py"
    pm_lines = len(pm_path.read_text(encoding="utf-8").splitlines())
    assert pm_lines <= 4500, f"portfolio_manager.py 瘦身未达标: 当前 {pm_lines} 行 (要求 <= 4500)"
    _check_no_duplicate_top_defs(pm_path)

    # 向下兼容外观导入与缓存对象同引用验证
    import portfolio_manager as pm_mod
    import valuation_engine as ve_mod

    for sym in (
        "PortfolioManager",
        "FundQuote",
        "prefetch_batch_fund_quotes",
        "fetch_realtime_fund_quote",
        "fetch_realtime_index_quote",
        "parse_smart_text_holdings",
        "parse_screenshot_ocr_holdings",
        "fuzzy_match_fund_by_name",
        "clear_realtime_cache",
    ):
        assert hasattr(pm_mod, sym), f"portfolio_manager 缺少兼容导出: {sym}"
    assert pm_mod._REALTIME_QUOTE_CACHE is ve_mod._REALTIME_QUOTE_CACHE, "缓存对象未共享同一引用"
    assert pm_mod._TODAY_EST_ARCHIVE is ve_mod._TODAY_EST_ARCHIVE, "日内定格存档未共享同一引用"

    # 实例方法继承验证
    for m in (
        "calculate_look_through_industry_exposure",
        "screen_fund_look_through_risk",
        "generate_scenario_rebalance_plan",
    ):
        assert hasattr(pm_mod.PortfolioManager, m), f"PortfolioManager 缺少实例方法: {m}"

    print(f"ALL G45 MODULARIZATION GATES PASSED (portfolio_manager.py = {pm_lines} lines)")


if __name__ == "__main__":
    main()
