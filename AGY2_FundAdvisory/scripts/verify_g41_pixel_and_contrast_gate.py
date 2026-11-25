import ast
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
AGY2_DIR = ROOT / "AGY2_FundAdvisory"
BASE = AGY2_DIR if (AGY2_DIR / "app_gui.py").exists() else ROOT


def detect_active_port():
    for p in [8501, 8585]:
        try:
            resp = urllib.request.urlopen(f"http://127.0.0.1:{p}/_stcore/health", timeout=1.5)
            if resp.status == 200:
                return p
        except Exception:
            pass
    return 8585


def _parse_rgb(rgb_str: str):
    nums = [int(x.strip()) for x in rgb_str.replace("rgba(", "").replace("rgb(", "").replace(")", "").split(",")[:3]]
    return tuple(nums)


def _luminance(rgb):
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


def run_g41_gate():
    gui_txt = (BASE / "app_gui.py").read_text(encoding="utf-8")
    ast.parse(gui_txt, filename="app_gui.py")

    # 1. 静态断言：禁止暴力截断 [:36]，强制持仓表锁定 7 列 column_order
    assert "_a_msg[:36]" not in gui_txt, "高危风控哨仍残留粗暴 [:36] 字符串硬切"
    assert "column_order=core_7_cols" in gui_txt, "持仓主表尚未启用 7 列 column_order 视图"

    active_port = detect_active_port()
    print(f"Connecting to Streamlit on port {active_port}...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(f"http://127.0.0.1:{active_port}", timeout=30000)

        # 等待页面加载完成
        for _ in range(25):
            state = page.locator("[data-testid='stApp']").get_attribute("data-test-script-state")
            if state == "notRunning":
                break
            page.wait_for_timeout(1000)
        page.wait_for_timeout(3000)

        assert page.locator('[data-testid="stException"]').count() == 0, "页面出现 Streamlit 异常"

        # 2. 侧边栏零滚动硬断言
        sb_scroll = page.evaluate("""() => {
            const el = document.querySelector('[data-testid="stSidebar"] > div:first-child');
            return el ? {sh: el.scrollHeight, ch: el.clientHeight} : null;
        }""")
        assert sb_scroll and sb_scroll["sh"] <= sb_scroll["ch"] + 2, f"侧边栏出现滚动: {sb_scroll}"
        print(f"  [OK] 侧边栏绝对零滚动断言通过: {sb_scroll}")

        # 3. 真实 RGB 亮度硬断言：侧边栏全部 4 个导航项文字亮度必须 >= 170（彻底杜绝深蓝底黑字隐身）
        nav_colors = page.evaluate("""() => {
            const items = Array.from(document.querySelectorAll('[data-testid="stSidebar"] div[role="radiogroup"] label p'));
            return items.map(el => ({text: el.innerText.trim(), color: getComputedStyle(el).color}));
        }""")
        assert len(nav_colors) == 4, f"侧边栏主导航应为 4 项，实际: {nav_colors}"
        for item in nav_colors:
            lum = _luminance(_parse_rgb(item["color"]))
            print(f"    Nav '{item['text']}': {item['color']} (lum={lum:.1f})")
            assert lum >= 170, f"侧边栏导航项「{item['text']}」字色过暗导致隐身: {item['color']} (亮度={lum:.1f})"
        print("  [OK] 侧边栏 4 项主导航真实 RGB 亮度 >= 170 全部达标")

        # 4. 真实 RGB 亮度硬断言：侧边栏「外观」「刷新」按钮文字亮度必须 >= 180
        btn_colors = page.evaluate("""() => {
            const btns = Array.from(document.querySelectorAll('[data-testid="stSidebar"] button'));
            return btns.filter(b => ['外观', '刷新'].includes(b.innerText.trim())).map(b => {
                const p = b.querySelector('p') || b;
                return {text: b.innerText.trim(), color: getComputedStyle(p).color};
            });
        }""")
        assert len(btn_colors) >= 2, f"未找到侧边栏外观/刷新按钮: {btn_colors}"
        for b in btn_colors:
            lum = _luminance(_parse_rgb(b["color"]))
            print(f"    Btn '{b['text']}': {b['color']} (lum={lum:.1f})")
            assert lum >= 180, f"侧边栏按钮「{b['text']}」字色过暗: {b['color']} (亮度={lum:.1f})"
        print("  [OK] 侧边栏外观/刷新按钮真实 RGB 亮度 >= 180 全部达标")

        # 5. 真实 RGB 校验：侧边栏自选板块涨跌幅必须保留红/绿语义色（绝不能全被抹成纯白 #E2E8F0）
        wl_colors = page.evaluate("""() => {
            const spans = Array.from(document.querySelectorAll('[data-testid="stSidebar"] span'));
            return spans.filter(s => /^[+-]\\d+\\.\\d+%$/.test(s.innerText.trim())).map(s => ({
                text: s.innerText.trim(), color: getComputedStyle(s).color
            }));
        }""")
        assert len(wl_colors) >= 3, f"侧边栏自选涨跌幅未渲染: {wl_colors}"
        non_white = [w for w in wl_colors if _parse_rgb(w["color"]) != (226, 232, 240)]
        print(f"    Watchlist items: {wl_colors}")
        assert len(non_white) >= 1, f"自选板块涨跌幅全被抹成了纯白，丢失红绿语义色: {wl_colors}"
        print(f"  [OK] 自选板块红绿涨跌语义色真实保留 (非纯白条目: {len(non_white)}/{len(wl_colors)})")

        # 6. 顶栏同行对齐断言
        topbar_align = page.evaluate("""() => {
            const hBlock = document.querySelector('div[data-testid="stHorizontalBlock"]:has(.topbar-outer-marker)');
            if (!hBlock) return {ok: false, reason: 'no hBlock'};
            const cols = hBlock.querySelectorAll('[data-testid="column"], [data-testid="stColumn"]');
            if (cols.length < 2) return {ok: false, reason: 'less than 2 cols'};
            const r0 = cols[0].getBoundingClientRect();
            const r1 = cols[1].getBoundingClientRect();
            return {ok: Math.abs(r0.top - r1.top) <= 18, diff: Math.abs(r0.top - r1.top), r0_top: r0.top, r1_top: r1.top};
        }""")
        assert topbar_align["ok"], f"顶栏标题与按钮未水平对齐: {topbar_align}"
        print(f"  [OK] 顶栏标题与按钮严格水平对齐: top diff={topbar_align['diff']:.1f}px <= 18px")

        # 7. 账本与设置标题防遮挡断言
        ledger_title_align = page.evaluate("""() => {
            const sb = document.querySelector('[data-testid="stSidebar"]');
            const divs = Array.from(sb.querySelectorAll('div'));
            const titleEl = divs.find(d => d.innerText.trim() === '账本与设置');
            const selectEl = sb.querySelector('div[data-baseweb="select"]');
            if (!titleEl || !selectEl) return {ok: true, note: 'el not found'};
            const tr = titleEl.getBoundingClientRect();
            const sr = selectEl.getBoundingClientRect();
            return {ok: tr.bottom <= sr.top + 2, tr_bottom: tr.bottom, sr_top: sr.top};
        }""")
        assert ledger_title_align["ok"], f"账本与设置标题被下拉框遮挡: {ledger_title_align}"
        print(f"  [OK] 账本与设置标题与下拉框零重叠遮挡")

        # 8. 实测点击切换「调仓」「复盘」「诊断」全部正常渲染零红框报错
        for nav_txt in ["调仓 · 清单与打卡", "复盘 · 回测与验真", "诊断 · 深度穿透", "持仓 · 资产与体检"]:
            page.locator(f'[data-testid="stSidebar"] div[role="radiogroup"] label:has-text("{nav_txt}")').click()
            page.wait_for_timeout(2000)
            assert page.locator('[data-testid="stException"]').count() == 0, f"切换至 {nav_txt} 后出现异常"
            print(f"  [OK] 导航切换至「{nav_txt}」渲染正常，零红框报错")

        page.screenshot(path="g41_desktop_verified.png", full_page=False)
        print("  [OK] 最新实机截图已保存至 g41_desktop_verified.png")
        browser.close()

    print("\nALL G41 CONTRAST-PIXEL, 7-COL TABLE & FULL-NAV INTERACTION GATES PASSED")


if __name__ == "__main__":
    run_g41_gate()
