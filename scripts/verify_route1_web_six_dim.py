import json
import time
import urllib.request
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"


def fetch_json(path: str):
    t0 = time.perf_counter()
    with urllib.request.urlopen(BASE + path, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data, round((time.perf_counter() - t0) * 1000, 1)


def main():
    # ── 维度 1：准确性与数学公理验收（API 级） ──
    for model in ("all_weather", "risk_parity", "dividend_defense", "barbell_growth"):
        for n in (3, 5, 6):
            bp, ms = fetch_json(f"/api/v1/recommend/blueprint?risk_level=C3&amount=50000&fund_count={n}&model={model}")
            items = bp["items"]
            assert len(items) >= n, f"{model} n={n}: got {len(items)}"
            w_sum = round(sum(x["weight_pct"] for x in items), 1)
            amt_sum = round(sum(x["suggested_amount"] for x in items), 1)
            assert abs(w_sum - 100.0) <= 0.2, f"{model} n={n} weight sum {w_sum} != 100"
            assert abs(amt_sum - 50000.0) <= 100.0, f"{model} n={n} amount sum {amt_sum} != 50000"
            for it in items:
                assert it["weight_pct"] > 0 and it["suggested_amount"] > 0, f"Zero weight in {it}"
                assert it.get("quant_reason"), f"Missing quant_reason in {it}"

    sc, sc_ms = fetch_json("/api/v1/charts/scenario_backtest?start_date=2021-02-18&tier=C3")
    assert len(sc.get("dates", [])) > 20, "Scenario backtest dates empty"
    assert sc.get("kpis", {}).get("all") is not None, "Scenario backtest KPI missing"

    div, div_ms = fetch_json("/api/v1/tools/dividend_advice")
    assert div.get("recommended_label"), "Dividend advice empty"

    etf, etf_ms = fetch_json("/api/v1/tools/etf_premiums")
    assert "items" in etf, "ETF premiums response malformed"

    ov, ov_ms = fetch_json("/api/v1/overview")
    assert ov.get("total_equity", 0) > 0, "Overview equity missing"

    # ── 维度 2~6：真实 Chromium 功能 / 视觉 / 操作 / 性能 / 专业性全链路验收 ──
    console_errors = []
    page_errors = []
    failed_reqs = []
    forbidden_jargon = ["二四反转", "二二反弹", "二一见顶", "影子账本赛跑", "四象限击球区", "下单复制小抄"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: page_errors.append(str(e)))
        page.on("response", lambda r: failed_reqs.append((r.status, r.url)) if r.status >= 400 and "favicon" not in r.url else None)

        t_nav = time.perf_counter()
        page.goto(BASE + "/", wait_until="networkidle", timeout=30000)
        load_ms = round((time.perf_counter() - t_nav) * 1000, 1)
        page.wait_for_timeout(1200)

        # 检查顶栏不折行
        nav_btns = page.locator("header nav button").all()
        for b in nav_btns:
            if b.is_visible():
                box = b.bounding_box()
                assert box and box["height"] <= 44, f"Topbar nav button wrapped! height={box}"

        # Page 1 检查 + 切到历史情景回测 + 点 2021-02 核心资产高位
        p1_canvases = page.locator("canvas").count()
        p1_text = page.locator("main").inner_text()
        for bad in forbidden_jargon:
            assert bad not in p1_text, f"Found deprecated jargon on Page 1: {bad}"
        assert "短期偏离与交易拥挤度象限" in p1_text
        assert "全天候动态均衡模型" in p1_text and "风险平价抗跌模型" in p1_text

        page.get_by_role("button", name="历史情景回测").click()
        page.wait_for_timeout(1000)
        page.get_by_role("button", name="2021-02 核心资产高位").click()
        page.wait_for_timeout(1000)
        sc_text = page.locator("main").inner_text()
        assert "持有 1 年" in sc_text and "同期沪深 300" in sc_text, "Scenario backtest KPIs not rendered"

        # Page 2 检查：持仓明细 + 净值对账 + 调仓效果追踪 + 极端行情压力测试 + 导出CSV + 编辑按钮
        page.get_by_role("button", name="我的持仓与体检").first.click()
        page.wait_for_timeout(1800)
        p2_text = page.locator("main").inner_text()
        for bad in forbidden_jargon:
            assert bad not in p2_text, f"Found deprecated jargon on Page 2: {bad}"
        assert "调仓效果追踪（调整前 vs 调整后）" in p2_text
        assert "极端行情压力测试" in p2_text
        assert "导出 CSV" in p2_text
        assert page.locator(".table-wrapper tbody tr").count() == 29
        p2_canvases = page.locator("canvas").count()
        assert p2_canvases >= 2

        # 切换到净值对账
        page.get_by_role("button", name="净值对账").click()
        page.wait_for_timeout(400)
        assert "盘中估算涨跌" in page.locator("main").inner_text()

        # Page 3 检查：调仓参考方案 + 大额限购分批买入计划 + 基金分红方式建议
        page.get_by_role("button", name="调仓参考方案").first.click()
        page.wait_for_timeout(1400)
        p3_text = page.locator("main").inner_text()
        for bad in forbidden_jargon:
            assert bad not in p3_text, f"Found deprecated jargon on Page 3: {bad}"
        assert "大额限购分批买入计划" in p3_text
        assert "基金分红方式建议" in p3_text

        # 专业分析抽屉：自选搜索 + ETF溢价 + A/C费率对比器
        page.get_by_role("button", name="专业分析").first.click()
        page.wait_for_timeout(1200)
        dr_text = page.locator("aside[aria-label='专业量化分析工具箱']").inner_text()
        assert "热门场内 ETF 溢价预警" in dr_text
        assert "A / C 类份额费率对比器" in dr_text
        assert "盈亏平衡点" in dr_text
        page.get_by_role("button", name="关闭专业分析抽屉").click()
        page.wait_for_timeout(200)

        # 导入持仓弹窗
        page.get_by_role("button", name="导入持仓").first.click()
        page.wait_for_timeout(300)
        assert page.locator("dialog[open]").count() == 1
        page.get_by_role("button", name="关闭导入弹窗").click()
        page.wait_for_timeout(200)

        # 移动端 390x844 三大页面零水平溢出验收
        page.set_viewport_size({"width": 390, "height": 844})
        over = {}
        for tab_name in ("今日信号与选基", "我的持仓与体检", "调仓参考方案"):
            page.get_by_role("button", name=tab_name).last.click()
            page.wait_for_timeout(700)
            over[tab_name] = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")

        browser.close()

    print(
        f"LOAD_MS={load_ms} OV_MS={ov_ms} SC_MS={sc_ms} DIV_MS={div_ms} ETF_MS={etf_ms} "
        f"P1_CANVASES={p1_canvases} P2_CANVASES={p2_canvases} MOBILE_OVERFLOW={over}"
    )
    print(f"CONSOLE_ERRORS={len(console_errors)} PAGE_ERRORS={len(page_errors)} FAILED_REQS={len(failed_reqs)}")
    assert len(console_errors) == 0, console_errors
    assert len(page_errors) == 0, page_errors
    assert len(failed_reqs) == 0, failed_reqs
    for k, v in over.items():
        assert v <= 1, f"Mobile overflow on {k}: {v}px"
    print("SIX_DIMENSION_AUDIT_ALL_PASSED")


if __name__ == "__main__":
    main()
