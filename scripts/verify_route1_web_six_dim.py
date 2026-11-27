import json
import os
import time
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8000"
SHOT_DIR = Path(os.environ.get("AGY2_SHOT_DIR", "")) if os.environ.get("AGY2_SHOT_DIR") else None


def fetch_json(path: str):
    t0 = time.perf_counter()
    with urllib.request.urlopen(BASE + path, timeout=25) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data, round((time.perf_counter() - t0) * 1000, 1)


def save_shot(page, name: str, full_page: bool = False):
    if SHOT_DIR is None:
        return
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SHOT_DIR / f"{name}.png"), full_page=full_page)


def main():
    # ── 维度 1：准确性与数学公理验收（API 级） ──
    for model in ("all_weather", "risk_parity", "dividend_defense", "barbell_growth"):
        for n in (3, 4, 5, 6, 8):
            bp, _ = fetch_json(f"/api/v1/recommend/blueprint?risk_level=C4&amount=50000&fund_count={n}&model={model}")
            items = bp["items"]
            assert len(items) == n, f"{model} n={n}: expected exact {n}, got {len(items)}"
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

    # ── 维度 2~6：真实 Chromium 机构级工作台 4 工作区 / 检查器 / 数据中心 / 三端视口全链路验收 ──
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

        # 等待默认首屏「量化实验室」组合配置矩阵表就绪
        page.wait_for_selector("[data-testid='portfolio-matrix-table'] tbody tr", timeout=25000)
        page.wait_for_timeout(800)

        # 检查顶栏不折行
        for b in page.locator("header nav button").all():
            if b.is_visible():
                box = b.bounding_box()
                assert box and box["height"] <= 40, f"Topbar nav button wrapped! height={box}"

        save_shot(page, "01_desktop_1440_quant_lab_matrix", full_page=True)
        lab_text = page.locator("main").inner_text()
        for bad in forbidden_jargon:
            assert bad not in lab_text, f"Deprecated jargon on QuantLab: {bad}"
        assert "组合配置与风险预算矩阵" in lab_text
        assert "100% 基金真实复权净值" in lab_text
        assert page.locator("[data-testid='portfolio-matrix-table'] tbody tr").count() == 6

        # 测试保存方案快照 + 切 A/B 对比
        page.locator("[data-testid='btn-save-snapshot']").click()
        page.wait_for_timeout(300)

        # 测试真实前端「单基排除并立即全市场重算」闭环
        first_ex_btn = page.locator("[data-testid^='btn-exclude-']").first
        ex_testid = first_ex_btn.get_attribute("data-testid") or ""
        excluded_code = ex_testid.replace("btn-exclude-", "")
        assert len(excluded_code) == 6, f"Bad exclude button testid: {ex_testid}"
        first_ex_btn.click()
        page.wait_for_timeout(800)
        # 等待重算结束（按钮文字不再是求解中，且排除的基金消失）
        page.wait_for_function(
            """(code) => {
                const tbl = document.querySelector("[data-testid='portfolio-matrix-table']");
                const prog = document.querySelector("[data-testid='quant-solve-progress']");
                return tbl && !prog && !tbl.innerText.includes(code);
            }""",
            arg=excluded_code,
            timeout=25000,
        )
        assert page.locator("[data-testid='portfolio-matrix-table'] tbody tr").count() == 6
        # 再存一次为方案 B，这样 A/B 对比有两套真实不同方案！
        page.locator("[data-testid='btn-save-snapshot']").click()
        page.wait_for_timeout(300)

        # 测试点击第一行打开右侧 Fund Inspector 检查器（不跳页）
        page.locator("[data-testid='portfolio-matrix-table'] tbody tr").first.click()
        page.wait_for_selector("[data-testid='fund-inspector-drawer']", timeout=15000)
        page.wait_for_timeout(1500)
        ins_text = page.locator("[data-testid='fund-inspector-drawer']").inner_text()
        assert "当前实验室方案配权归因" in ins_text
        save_shot(page, "02_desktop_1440_fund_inspector", full_page=False)

        # 从检查器进入全屏 5 维完整档案再返回
        page.locator("[data-testid='btn-inspector-fullscreen']").click()
        page.wait_for_timeout(1800)
        fd_t1 = page.locator("main").inner_text()
        assert "历史业绩表现" in fd_t1 and "历史定投收益测算" in fd_t1
        page.get_by_role("button", name="量化分析指标").click()
        page.wait_for_timeout(400)
        fd_t2 = page.locator("main").inner_text()
        for kw in ("跟踪性价比", "抗下跌能力", "最大回撤", "夏普比率"):
            assert kw in fd_t2, f"Missing analytics metric: {kw}"
        page.get_by_role("button", name="返回工作台").click()
        page.wait_for_timeout(500)

        # 实验室子视图：净值与情景回测 + 侧栏折叠 100% 满宽
        page.get_by_role("tab", name="净值与情景回测").click()
        page.wait_for_timeout(800)
        assert page.locator("canvas").count() >= 3
        page.locator("[data-testid='btn-collapse-sidebar']").click()
        page.wait_for_timeout(400)
        assert page.locator("[data-testid='collapsed-param-bar']").is_visible()
        save_shot(page, "03_desktop_1440_backtest_fullwidth", full_page=True)

        # 切换到历史情景压力回测
        page.get_by_role("button", name="历史情景压力回测").click()
        page.wait_for_timeout(900)
        page.get_by_role("button", name="2021-02 核心资产高位").click()
        page.wait_for_timeout(900)
        sc_text = page.locator("main").inner_text()
        assert "持有 1 年" in sc_text and "沪深300" in sc_text

        # 实验室子视图：极端周期与止盈
        page.get_by_role("tab", name="极端周期与止盈").click()
        page.wait_for_timeout(700)
        assert "极端行情修复天数、完整周期与量化止盈锚点" in page.locator("main").inner_text()
        save_shot(page, "04_desktop_1440_extreme_cycles", full_page=True)

        # 实验室子视图：A/B 方案对比
        page.get_by_role("tab", name="A/B 方案对比").click()
        page.wait_for_timeout(400)
        assert page.locator("[data-testid='ab-compare-view']").is_visible()
        save_shot(page, "11_desktop_1440_ab_compare", full_page=True)
        # 还原展开参数台
        page.locator("[data-testid='btn-expand-sidebar']").click()
        page.get_by_role("tab", name="组合方案矩阵").click()
        page.wait_for_timeout(300)

        # ── 工作区 2：市场与信号（十维投票汉化 + 自选 + ETF溢价 + 拥挤度） ──
        page.get_by_role("button", name="市场与信号").first.click()
        page.wait_for_selector("[data-testid='market-signal-page']", timeout=15000)
        page.wait_for_timeout(1200)
        mk_text = page.locator("[data-testid='market-signal-page']").inner_text()
        assert "十维量化宏观投票矩阵" in mk_text
        assert "热门场内 ETF 溢价预警" in mk_text
        assert "短期偏离与交易拥挤度象限" in mk_text
        assert "偏多进攻" in mk_text or "偏空防守" in mk_text or "中性观望" in mk_text
        assert "BULL" not in mk_text and "BEAR" not in mk_text, "Raw BULL/BEAR leaked!"
        save_shot(page, "05_desktop_1440_market_signal", full_page=True)

        # ── 工作区 3：实盘与风控（持仓明细 + 净值对账 + 行业穿透重仓重叠 + 压测影子追踪） ──
        page.get_by_role("button", name="实盘与风控").first.click()
        page.wait_for_selector("[data-testid='holdings-page'] tr[data-testid='holding-row']", timeout=15000)
        page.wait_for_timeout(400)
        assert page.locator("[data-testid='holdings-page'] tr[data-testid='holding-row']").count() == 29
        save_shot(page, "06_desktop_1440_holdings_list", full_page=False)

        page.get_by_role("button", name="净值对账").click()
        page.wait_for_timeout(300)
        assert "盘中估算涨跌" in page.locator("[data-testid='holdings-page']").inner_text()

        page.get_by_role("tab", name="大类缺口 · 行业穿透 · 重仓重叠").click()
        page.wait_for_timeout(700)
        assert "底层重仓股交叉重叠穿透" in page.locator("[data-testid='holdings-page']").inner_text()

        page.get_by_role("tab", name="极端压测与影子追踪").click()
        page.wait_for_timeout(600)
        st_text = page.locator("[data-testid='holdings-page']").inner_text()
        assert "调仓效果追踪（调整前 vs 调整后）" in st_text
        assert "99% 极端尾部风险 CVaR" in st_text

        # ── 工作区 4：调仓执行（对齐实验室 + DCA + 勾选持久化 + A/C费率对比器） ──
        page.get_by_role("button", name="调仓执行").first.click()
        page.wait_for_selector("[data-testid='rebalance-page']", timeout=15000)
        page.wait_for_timeout(700)
        reb_text = page.locator("[data-testid='rebalance-page']").inner_text()
        assert "大额限购分批买入计划" in reb_text
        assert "基金分红方式建议" in reb_text
        assert "A / C 类份额费率对比器" in reb_text
        assert "盈亏平衡点" in reb_text
        save_shot(page, "07_desktop_1440_rebalance", full_page=True)

        # 验证 DCA 金额 3000 -> 6000 重算
        dca_input = page.get_by_label("本月新增资金 (¥)")
        dca_input.fill("6000")
        page.wait_for_timeout(900)
        assert "¥6,000.00" in page.locator("[data-testid='rebalance-page']").inner_text() or "2,014" in page.locator("[data-testid='rebalance-page']").inner_text()

        # 验证打卡持久化
        first_cb = page.locator("[data-testid='rebalance-page'] input[type='checkbox']").first
        was_checked = first_cb.is_checked()
        first_cb.click()
        page.wait_for_timeout(700)
        assert "已保存至本机" in page.locator("[data-testid='rebalance-page']").inner_text()
        # 还原勾选保持账本干净
        first_cb.click()
        page.wait_for_timeout(500)

        # ── 数据与账本中心（验证解析预览核对表） + Ctrl+K 命令面板 ──
        page.locator("[data-testid='btn-open-data-center']").click()
        page.wait_for_timeout(300)
        assert page.locator("dialog[open]").count() == 1
        page.locator("dialog[open] textarea").fill("005561 8000\n110020 5000")
        page.get_by_role("button", name="解析并生成核对表").click()
        page.wait_for_selector("[data-testid='import-preview-table']", timeout=10000)
        save_shot(page, "08_desktop_1440_data_center_preview", full_page=False)
        page.get_by_role("button", name="关闭数据中心弹窗").click()
        page.wait_for_timeout(200)

        page.locator("[data-testid='btn-open-command-palette']").click()
        page.wait_for_selector("[data-testid='command-palette']", timeout=5000)
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)

        # Cookie 审计
        assert len(page.context.cookies()) == 0, "Unexpected cookies set!"

        # ── 笔记本 1280x800 视口检查 ──
        page.set_viewport_size({"width": 1280, "height": 800})
        page.get_by_role("button", name="量化实验室").first.click()
        page.wait_for_timeout(500)
        ov_1280 = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        assert ov_1280 <= 1, f"1280px horizontal overflow: {ov_1280}px"
        save_shot(page, "09_laptop_1280_quant_lab", full_page=False)

        # ── 移动端 390x844 四大工作区零水平溢出验收 ──
        page.set_viewport_size({"width": 390, "height": 844})
        over = {}
        for tab_name in ("实验室", "市场信号", "实盘风控", "调仓执行"):
            page.get_by_role("button", name=tab_name).last.click()
            page.wait_for_timeout(600)
            over[tab_name] = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
            if tab_name == "实验室":
                save_shot(page, "10_mobile_390_quant_lab", full_page=False)

        browser.close()

    print(
        f"LOAD_MS={load_ms} OV_MS={ov_ms} SC_MS={sc_ms} DIV_MS={div_ms} ETF_MS={etf_ms} "
        f"LAPTOP_OVERFLOW={ov_1280} MOBILE_OVERFLOW={over}"
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
