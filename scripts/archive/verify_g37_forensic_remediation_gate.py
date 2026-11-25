# -*- coding: utf-8 -*-
import ast
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main():
    print("=== G37 法证缺陷修复零 Mock 验收门禁 ===")

    # 1. api_server.py 中段 __main__ 阻断检查：只允许存在 1 个 __main__ 且位于最后 40 行内
    api_src = (ROOT / "api_server.py").read_text(encoding="utf-8")
    api_lines = api_src.splitlines()
    main_lines = [i + 1 for i, l in enumerate(api_lines) if '__name__ == "__main__"' in l or "__name__ == '__main__'" in l]
    assert len(main_lines) == 1, f"api_server.py 必须仅有 1 个 __main__ 入口，当前: {main_lines}"
    assert main_lines[0] >= len(api_lines) - 45, f"__main__ 入口不能位于文件中段: line {main_lines[0]}/{len(api_lines)}"
    print(f"  [OK] 门禁 1: api_server.py 唯一 __main__ 入口位于末尾第 {main_lines[0]} 行")

    # 2. 真实子进程启动 api_server.py，零 Mock 验证后半段核心路由全部 200 且零 HTML 污染
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "api_server.py"), "--host", "127.0.0.1", "--port", "18099"],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        ready = False
        for _ in range(30):
            try:
                with urllib.request.urlopen("http://127.0.0.1:18099/api/health", timeout=1.0) as r:
                    if r.status == 200:
                        ready = True
                        break
            except Exception:
                time.sleep(0.3)
        assert ready, "api_server.py 真实子进程启动超时"

        for ep in [
            "/api/v1/overview",
            "/api/v1/holdings",
            "/api/v1/holdings/movers",
            "/api/v1/rebalance",
            "/api/v1/alerts/push",
            "/api/v1/review/forward_audit",
            "/api/v1/diagnose/risk_check",
        ]:
            with urllib.request.urlopen(f"http://127.0.0.1:18099{ep}", timeout=15.0) as r:
                assert r.status == 200, f"{ep} 返回非 200: {r.status}"
                txt = r.read().decode("utf-8")
                assert "<div" not in txt and "<span" not in txt, f"{ep} 响应存在 HTML 污染"
                json.loads(txt)
        print("  [OK] 门禁 2: api_server.py 真实子进程 7 组核心 v1 路由全部 HTTP 200 且纯净 JSON")
    finally:
        proc.terminate()
        proc.wait(timeout=5)

    # 3. docs/openapi_v1.json 存在且包含全部 v1 路径
    oa_path = ROOT / "docs" / "openapi_v1.json"
    assert oa_path.exists(), "缺少 docs/openapi_v1.json"
    oa = json.loads(oa_path.read_text(encoding="utf-8"))
    for p in ["/api/v1/overview", "/api/v1/holdings/movers", "/api/v1/alerts/push", "/api/v1/review/{subview}"]:
        assert p in oa.get("paths", {}), f"OpenAPI 缺少路径: {p}"
    print("  [OK] 门禁 3: docs/openapi_v1.json 完整有效")

    # 4. 工具页分段真实传参检查 + 废弃死文件清理检查 + 黑天鹅安全拦截接线检查
    gui_src = (ROOT / "app_gui.py").read_text(encoding="utf-8")
    assert "active_subview=tb_view" in gui_src, "Tab 4 工具页未将 tb_view 传入 render_tab4_toolbox_content"
    assert "诊断持仓并生成今日调仓方案" not in gui_src, "app_gui.py 仍残留旧按钮名提示"
    for dead_f in ["ui_simple_mode.py", "oos_verdict_tracker.py", "ledger_backup_manager.py"]:
        assert not (ROOT / dead_f).exists(), f"冗余死文件未清理: {dead_f}"

    sb_src = (ROOT / "strategy_bridge.py").read_text(encoding="utf-8")
    assert "inspect_buy_candidate_safety" in sb_src, "strategy_bridge.py 尚未接线买前安全红线拦截"
    print("  [OK] 门禁 4: 真单屏分流、买前安检接线与冗余死文件清理全部通过")

    # 5. AST 编译与 8 字以上长按钮归零复核
    for pyf in ROOT.glob("*.py"):
        ast.parse(pyf.read_text(encoding="utf-8"), filename=pyf.name)
    btns = re.findall(r'st\.button\(\s*["\']([^"\']+)["\']', gui_src)
    long_btns = [b for b in btns if len(re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]', '', b)) > 6]
    assert not long_btns, f"仍存在超 6 字长按钮: {long_btns}"
    print("  [OK] 门禁 5: 全库 AST 零语法错误且超长按钮 0 命中")
    print("ALL G37 FORENSIC REMEDIATION GATES PASSED")


if __name__ == "__main__":
    main()
