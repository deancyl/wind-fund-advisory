# -*- coding: utf-8 -*-
"""
AGY2 基金深度详情与量化分析引擎 (Fund Detail Service)
遵循三级高可用数据管道：
  L1: 并发拉取东方财富/天天基金官方公开接口（历史净值、档案、经理、重仓、公告、费率规则）
  L2: 结合本地量化矩阵实时计算 4 大类 + 8 小类专业指标、历史业绩表、定投收益测算表
  L3: 极端断网时优雅降级本地基金池元数据并显式标记 is_fallback=True
"""

from __future__ import annotations

import datetime as dt
import html
import json
import math
import re
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from domain_models import CORE_STRATEGY_POOL, EXTENDED_FUND_CATALOG, STOCK_NAME_TO_SYMBOL_MAP

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://fundf10.eastmoney.com/",
}

_DETAIL_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_DETAIL_CACHE_LOCK = threading.Lock()
_DETAIL_CACHE_TTL = 600.0  # 10 分钟缓存


def _http_get(url: str, timeout: int = 8) -> str:
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def _strip_html(raw: str) -> str:
    s = re.sub(r"<[^>]+>", "", str(raw or ""))
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def _parse_pingzhongdata(code: str) -> Dict[str, Any]:
    js = _http_get(f"https://fund.eastmoney.com/pingzhongdata/{code}.js", timeout=8)
    out: Dict[str, Any] = {}
    for var in ("Data_netWorthTrend", "Data_ACWorthTrend", "Data_currentFundManager", "Data_assetAllocation"):
        m = re.search(rf"var\s+{var}\s*=\s*(.*?);(?:\s*/\*|\s*var\s|\s*$)", js, re.S)
        if m:
            try:
                out[var] = json.loads(m.group(1))
            except Exception:
                pass
    # 基金名称、申购费率等基础变量
    for k in ("fS_name", "fund_sourceRate", "fund_Rate", "fund_minsg"):
        m = re.search(rf'var\s+{k}\s*=\s*"([^"]*)"', js)
        if m:
            out[k] = m.group(1)
    return out


def _fetch_base_info(code: str) -> Dict[str, Any]:
    raw = _http_get(
        f"https://fundmobapi.eastmoney.com/FundMApi/FundBaseTypeInformation.ashx"
        f"?FCODE={code}&deviceid=Wap&plat=Wap&product=EFund&version=2.0.0"
    )
    d = json.loads(raw)
    return d.get("Datas") or {}


def _fetch_manager_list(code: str) -> List[Dict[str, Any]]:
    raw = _http_get(
        f"https://fundmobapi.eastmoney.com/FundMApi/FundManagerList.ashx"
        f"?FCODE={code}&deviceid=Wap&plat=Wap&product=EFund&version=2.0.0"
    )
    d = json.loads(raw)
    return d.get("Datas") or []


def _fetch_notices(code: str) -> List[Dict[str, Any]]:
    raw = _http_get(
        f"https://fundmobapi.eastmoney.com/FundMApi/FundNoticeList.ashx"
        f"?FCODE={code}&pageIndex=1&pageSize=12&deviceid=Wap&plat=Wap&product=EFund&version=2.0.0"
    )
    d = json.loads(raw)
    items = d.get("Datas") or []
    out = []
    for it in items:
        pub = str(it.get("PUBLISHDATE") or "")[:10]
        nid = str(it.get("ID") or "")
        out.append({
            "id": nid,
            "title": str(it.get("TITLE") or "").strip(),
            "date": pub,
            "category": str(it.get("AUTHOR") or "基金公告").strip(),
            "url": f"https://fundf10.eastmoney.com/jjgg_{code}.html",
        })
    return out


def _fetch_top_stocks(code: str) -> Tuple[str, List[Dict[str, Any]]]:
    js = _http_get(f"https://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code={code}&topline=10")
    # 提取最新季度报告期
    q_m = re.search(r"(\d{4}年\d季度股票投资明细)", js)
    quarter_label = q_m.group(1) if q_m else "最新季报重仓明细"
    # 提取第一个 tbody 的前 10 行
    tb_m = re.search(r"<tbody[^>]*>(.*?)</tbody>", js, re.S)
    if not tb_m:
        return quarter_label, []
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", tb_m.group(1), re.S)
    stocks: List[Dict[str, Any]] = []
    for tr in rows[:10]:
        tds = [_strip_html(td) for td in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(tds) >= 7:
            # 标准列：序号 | 股票代码 | 股票名称 | 最新价 | 涨跌幅 | 相关资讯 | 占净值比例 | 持股数(万股) | 持仓市值(万元)
            s_code = tds[1]
            s_name = tds[2]
            pct_str = next((x for x in tds[5:] if "%" in x), "0%")
            try:
                pct_val = float(pct_str.replace("%", "").strip())
            except Exception:
                pct_val = 0.0
            stocks.append({
                "stock_code": s_code,
                "stock_name": s_name,
                "weight_pct": round(pct_val, 2),
                "shares_wan": tds[-2] if len(tds) >= 8 else "",
                "value_wan": tds[-1] if len(tds) >= 9 else "",
            })
    return quarter_label, stocks


def _fetch_fees_and_profile(code: str) -> Dict[str, Any]:
    """解析天天基金费率与基金档案页（管理费/托管费/销售服务费/阶梯赎回费/托管行/基准）。"""
    res: Dict[str, Any] = {
        "management_fee": "",
        "custody_fee": "",
        "sales_service_fee": "",
        "redemption_tiers": [],
        "purchase_tiers": [],
        "full_name": "",
        "custodian": "",
        "benchmark": "",
        "tracking_target": "",
        "operation_mode": "契约型开放式",
    }
    try:
        fl_html = _http_get(f"https://fundf10.eastmoney.com/jjfl_{code}.html", timeout=8)
        m_mgmt = re.search(r"管理费率</td><td[^>]*>(.*?)</td>", fl_html, re.S)
        m_cust = re.search(r"托管费率</td><td[^>]*>(.*?)</td>", fl_html, re.S)
        m_sale = re.search(r"销售服务费率</td><td[^>]*>(.*?)</td>", fl_html, re.S)
        if m_mgmt:
            res["management_fee"] = _strip_html(m_mgmt.group(1))
        if m_cust:
            res["custody_fee"] = _strip_html(m_cust.group(1))
        if m_sale:
            res["sales_service_fee"] = _strip_html(m_sale.group(1))

        # 解析赎回费率阶梯表
        red_sec = re.search(r"赎回费率(.*?)</table>", fl_html, re.S)
        if red_sec:
            for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", red_sec.group(1), re.S)[1:8]:
                tds = [_strip_html(td) for td in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
                if len(tds) >= 2:
                    res["redemption_tiers"].append({"condition": tds[-2] if len(tds) >= 3 else tds[0], "rate": tds[-1]})

        # 解析申购费率阶梯表
        pur_sec = re.search(r"申购费率（前端）(.*?)</table>", fl_html, re.S)
        if pur_sec:
            for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", pur_sec.group(1), re.S)[1:6]:
                tds = [_strip_html(td) for td in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
                if len(tds) >= 2:
                    res["purchase_tiers"].append({"condition": tds[0], "rate": tds[-1]})
    except Exception:
        pass

    try:
        gk_html = _http_get(f"https://fundf10.eastmoney.com/jbgk_{code}.html", timeout=8)
        for key, pat in (
            ("full_name", r"基金全称</th><td[^>]*>(.*?)</td>"),
            ("custodian", r"基金托管人</th><td[^>]*>(.*?)</td>"),
            ("benchmark", r"业绩比较基准</th><td[^>]*>(.*?)</td>"),
            ("tracking_target", r"跟踪标的</th><td[^>]*>(.*?)</td>"),
            ("operation_mode", r"基金类型</th><td[^>]*>(.*?)</td>"),
        ):
            m = re.search(pat, gk_html, re.S)
            if m:
                val = _strip_html(m.group(1))
                if val and val != "---":
                    res[key] = val
    except Exception:
        pass

    return res


def _build_nav_series(pz: Dict[str, Any]) -> Tuple[List[str], List[float], List[float], List[float], List[str]]:
    raw_nav = pz.get("Data_netWorthTrend") or []
    raw_ac = pz.get("Data_ACWorthTrend") or []
    ac_map: Dict[int, float] = {}
    for pair in raw_ac:
        if isinstance(pair, list) and len(pair) >= 2 and pair[1] is not None:
            ac_map[int(pair[0])] = float(pair[1])

    dates: List[str] = []
    unit_navs: List[float] = []
    ac_navs: List[float] = []
    day_rets: List[float] = []
    dividends: List[str] = []

    for pt in raw_nav:
        if not isinstance(pt, dict) or pt.get("y") is None:
            continue
        ts_ms = int(pt.get("x", 0))
        d_str = dt.datetime.fromtimestamp(ts_ms / 1000.0).strftime("%Y-%m-%d")
        u_val = float(pt["y"])
        ac_val = float(ac_map.get(ts_ms, u_val))
        eq_ret = float(pt.get("equityReturn") or 0.0)
        dates.append(d_str)
        unit_navs.append(round(u_val, 4))
        ac_navs.append(round(ac_val, 4))
        day_rets.append(round(eq_ret, 2))
        dividends.append(str(pt.get("unitMoney") or ""))
    return dates, unit_navs, ac_navs, day_rets, dividends


def _load_hs300_map() -> Dict[str, float]:
    try:
        from strategy_bridge import StrategyBridge
        df = StrategyBridge.load_matrix()
        if df is not None and not df.empty and "H00300" in df.columns:
            col_d = df["date"].astype(str).str.slice(0, 10) if "date" in df.columns else df.index.astype(str).str.slice(0, 10)
            vals = df["H00300"].astype(float).ffill().bfill()
            return dict(zip(col_d.tolist(), vals.tolist()))
    except Exception:
        pass
    return {}


def _compute_analytics_and_perf(
    dates: List[str],
    ac_navs: List[float],
    hs300_map: Dict[str, float],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if len(dates) < 10:
        return [], {}

    arr = np.array(ac_navs, dtype=float)
    arr = np.where(arr <= 0, np.nan, arr)
    # 前向填充
    for i in range(1, len(arr)):
        if np.isnan(arr[i]):
            arr[i] = arr[i - 1]
    if np.isnan(arr[0]):
        arr[0] = 1.0

    # 对齐同期沪深 300 基准序列
    bm_list: List[float] = []
    last_bm = 1.0
    for d in dates:
        v = hs300_map.get(d)
        if v is not None and v > 0:
            last_bm = v
        bm_list.append(last_bm)
    bm_arr = np.array(bm_list, dtype=float)
    has_bm = float(np.std(bm_arr)) > 1e-6

    # 1. 历史业绩表格
    n = len(dates)
    cur_year = dates[-1][:4]
    ytd_idx = next((i for i, d in enumerate(dates) if d.startswith(cur_year)), max(0, n - 1))
    windows = [
        ("近 1 周", max(0, n - 6)),
        ("近 1 月", max(0, n - 22)),
        ("近 3 月", max(0, n - 64)),
        ("近 6 月", max(0, n - 127)),
        ("近 1 年", max(0, n - 252)),
        ("近 2 年", max(0, n - 504)),
        ("近 3 年", max(0, n - 756)),
        ("今年以来", ytd_idx),
        ("成立以来", 0),
    ]
    perf_rows: List[Dict[str, Any]] = []
    for label, idx in windows:
        if idx >= n - 1 and label != "今年以来":
            continue
        if label in ("近 1 年", "近 2 年", "近 3 年"):
            need = {"近 1 年": 200, "近 2 年": 420, "近 3 年": 650}[label]
            if n < need:
                continue
        f_ret = round((arr[-1] / arr[idx] - 1.0) * 100.0, 2) if arr[idx] > 0 else 0.0
        b_ret = round((bm_arr[-1] / bm_arr[idx] - 1.0) * 100.0, 2) if (has_bm and bm_arr[idx] > 0) else None
        ex_ret = round(f_ret - b_ret, 2) if b_ret is not None else None
        perf_rows.append({
            "period": label,
            "fund_return_pct": f_ret,
            "benchmark_return_pct": b_ret,
            "excess_return_pct": ex_ret,
        })

    # 2. 量化分析指标（取近 3 年或全量，最多 756 个交易日）
    w_len = min(n, 756)
    f_w = arr[-w_len:]
    b_w = bm_arr[-w_len:]
    f_dr = np.diff(f_w) / np.where(f_w[:-1] > 0, f_w[:-1], 1.0)
    b_dr = np.diff(b_w) / np.where(b_w[:-1] > 0, b_w[:-1], 1.0)

    # 收益能力：净值新高率 & 超额收益
    running_max = np.maximum.accumulate(f_w)
    new_high_rate = round(float(np.mean(f_w >= running_max * 0.9999) * 100.0), 2)
    f_cum = (f_w[-1] / f_w[0] - 1.0) * 100.0 if f_w[0] > 0 else 0.0
    b_cum = (b_w[-1] / b_w[0] - 1.0) * 100.0 if (has_bm and b_w[0] > 0) else 0.0
    excess_cum = round(f_cum - b_cum, 2)
    ann_ret = ((f_w[-1] / f_w[0]) ** (252.0 / max(w_len, 1)) - 1.0) * 100.0 if f_w[0] > 0 else 0.0

    # 风险控制：最大回撤 & 年化波动率
    dd_arr = (f_w / running_max - 1.0) * 100.0
    max_dd = round(abs(float(np.min(dd_arr))), 2)
    ann_vol = round(float(np.std(f_dr) * math.sqrt(252.0) * 100.0), 2) if len(f_dr) > 2 else 0.0

    # 跟踪能力：跟踪误差 & 信息比率
    active_dr = f_dr - b_dr if has_bm else f_dr
    te_ann = round(float(np.std(active_dr) * math.sqrt(252.0) * 100.0), 2) if len(active_dr) > 2 else 0.0
    active_ann = float(np.mean(active_dr) * 252.0 * 100.0) if len(active_dr) > 2 else 0.0
    info_ratio = round(active_ann / te_ann, 2) if te_ann > 0.1 else 0.0

    # 性价比：夏普比率 & 卡玛比率
    rf = 2.0
    sharpe = round((ann_ret - rf) / ann_vol, 2) if ann_vol > 0.1 else 0.0
    calmar = round(ann_ret / max_dd, 2) if max_dd > 0.1 else 0.0

    # 四大类综合能力评分 (0~100，基于客观数学映射)
    score_downside = int(round(np.clip(100.0 - max_dd * 2.2, 20.0, 96.0)))
    score_vol = int(round(np.clip(100.0 - ann_vol * 2.5, 20.0, 96.0)))
    score_ratio = int(round(np.clip(55.0 + sharpe * 25.0 + calmar * 12.0, 20.0, 96.0)))
    score_te = int(round(np.clip(95.0 - te_ann * 2.0, 25.0, 95.0)))

    def _grade(s: int) -> str:
        return "优秀" if s >= 78 else ("良好" if s >= 60 else ("中等" if s >= 45 else "偏弱"))

    analytics = {
        "window_days": w_len,
        "window_label": f"近 {round(w_len / 252.0, 1)} 年（{w_len} 个交易日）" if w_len >= 200 else f"近 {w_len} 个交易日",
        "categories": [
            {"key": "cost_perf", "name": "跟踪性价比", "score": score_ratio, "grade": _grade(score_ratio), "desc": f"夏普 {sharpe:.2f} · 卡玛 {calmar:.2f}"},
            {"key": "downside", "name": "抗下跌能力", "score": score_downside, "grade": _grade(score_downside), "desc": f"区间最大回撤 -{max_dd:.2f}%"},
            {"key": "volatility", "name": "抗波动能力", "score": score_vol, "grade": _grade(score_vol), "desc": f"年化波动率 {ann_vol:.2f}%"},
            {"key": "tracking", "name": "跟踪误差控制", "score": score_te, "grade": _grade(score_te), "desc": f"相对沪深300跟踪误差 {te_ann:.2f}%"},
        ],
        "sub_metrics": {
            "return_ability": [
                {"name": "净值新高率", "value": f"{new_high_rate:.2f}%", "hint": "区间内创历史新高的交易日占比，越高代表趋势越流畅"},
                {"name": "区间超额收益", "value": f"{excess_cum:+.2f}%", "hint": "相对同期沪深 300 基准的累计超额回报"},
            ],
            "risk_control": [
                {"name": "最大回撤", "value": f"-{max_dd:.2f}%", "hint": "区间内从高点到低点的最大跌幅"},
                {"name": "年化波动率", "value": f"{ann_vol:.2f}%", "hint": "衡量净值日常波动剧烈程度，越低越平稳"},
            ],
            "tracking_ability": [
                {"name": "信息比率 (IR)", "value": f"{info_ratio:.2f}", "hint": "单位主动风险带来的超额收益，正值越高越优"},
                {"name": "年化跟踪误差", "value": f"{te_ann:.2f}%", "hint": "相对基准日收益偏离的年化标准差"},
            ],
            "cost_performance": [
                {"name": "夏普比率 (Sharpe)", "value": f"{sharpe:.2f}", "hint": "扣除 2% 无风险利率后，每承受 1 份波动获得的超额回报"},
                {"name": "卡玛比率 (Calmar)", "value": f"{calmar:.2f}", "hint": "年化收益 / 最大回撤，衡量回撤修复性价比"},
            ],
        },
    }
    return perf_rows, analytics


def compute_dca_simulation(dates: List[str], unit_navs: List[float], monthly_amount: float = 1000.0) -> List[Dict[str, Any]]:
    """基于真实历史单位净值，按每月首个交易日定投测算近 1/2/3/5 年定投收益。"""
    if len(dates) < 30 or monthly_amount <= 0:
        return []
    amt = float(monthly_amount)
    last_nav = float(unit_navs[-1])
    if last_nav <= 0:
        return []

    rows: List[Dict[str, Any]] = []
    for label, years, need_days in (("近 1 年", 1, 220), ("近 2 年", 2, 440), ("近 3 年", 3, 660), ("近 5 年", 5, 1100)):
        if len(dates) < need_days:
            continue
        sub_d = dates[-min(len(dates), years * 252):]
        sub_n = unit_navs[-min(len(unit_navs), years * 252):]
        seen_ym = set()
        total_shares = 0.0
        periods = 0
        for d, nv in zip(sub_d, sub_n):
            ym = d[:7]
            if ym not in seen_ym and nv > 0:
                seen_ym.add(ym)
                total_shares += amt / nv
                periods += 1
        if periods < 3:
            continue
        invested = round(periods * amt, 2)
        final_val = round(total_shares * last_nav, 2)
        profit = round(final_val - invested, 2)
        ret_pct = round((profit / invested) * 100.0, 2) if invested > 0 else 0.0
        # 近似定投年化收益率（资金平均占用约为总期限的一半）
        eff_years = max(0.5, (periods / 12.0) * 0.55)
        ann_pct = round((((final_val / invested) ** (1.0 / eff_years)) - 1.0) * 100.0, 2) if final_val > 0 and invested > 0 else 0.0
        rows.append({
            "period": label,
            "periods": periods,
            "monthly_amount": round(amt, 2),
            "total_invested": invested,
            "final_value": final_val,
            "profit": profit,
            "return_pct": ret_pct,
            "annualized_pct": ann_pct,
        })
    return rows


def _infer_industry_distribution(code: str, top_stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """优先使用本地穿透行业映射汇总重仓股行业分布，保证真实可解释。"""
    try:
        from lookthrough_analyzer import FUND_LOOK_THROUGH_DATA
        lt = FUND_LOOK_THROUGH_DATA.get(code)
        if lt and isinstance(lt.get("industries"), dict):
            return [
                {"industry": k, "weight_pct": round(float(v) * 100.0 if float(v) <= 1.0 else float(v), 2)}
                for k, v in sorted(lt["industries"].items(), key=lambda x: -float(x[1]))[:8]
            ]
    except Exception:
        pass
    # 若无预置穿透，按重仓股代码前缀与名称做基础板块归类
    if not top_stocks:
        return []
    buckets: Dict[str, float] = {}
    kw_map = [
        ("银行", "银行"), ("保险", "非银金融"), ("证券", "非银金融"),
        ("电力", "公用事业"), ("能源", "煤炭与能源"), ("煤", "煤炭与能源"), ("石油", "石油石化"),
        ("半导体", "半导体与电子"), ("芯", "半导体与电子"), ("微", "半导体与电子"),
        ("酒", "食品饮料"), ("药", "医药生物"), ("医", "医药生物"),
        ("汽车", "汽车与制造"), ("电池", "电力设备"), ("通信", "通信"), ("移动", "通信"),
    ]
    for st in top_stocks:
        nm = st.get("stock_name", "")
        w = float(st.get("weight_pct", 0.0) or 0.0)
        cat = "其他核心行业"
        for kw, ind in kw_map:
            if kw in nm:
                cat = ind
                break
        buckets[cat] = buckets.get(cat, 0.0) + w
    return [{"industry": k, "weight_pct": round(v, 2)} for k, v in sorted(buckets.items(), key=lambda x: -x[1])[:8]]


def get_fund_full_detail(fund_code: str, dca_monthly: float = 1000.0) -> Dict[str, Any]:
    code = str(fund_code or "").strip().zfill(6)
    now = time.time()
    cached_base: Optional[Dict[str, Any]] = None
    with _DETAIL_CACHE_LOCK:
        hit = _DETAIL_CACHE.get(code)
        if hit and (now - hit[0]) < _DETAIL_CACHE_TTL:
            cached_base = hit[1]

    if cached_base is None:
        is_fallback = False
        pz: Dict[str, Any] = {}
        base_info: Dict[str, Any] = {}
        mgr_list: List[Dict[str, Any]] = []
        notices: List[Dict[str, Any]] = []
        quarter_label = "最新季报重仓明细"
        top_stocks: List[Dict[str, Any]] = []
        fees_prof: Dict[str, Any] = {}

        with ThreadPoolExecutor(max_workers=6) as pool:
            f_pz = pool.submit(_parse_pingzhongdata, code)
            f_base = pool.submit(_fetch_base_info, code)
            f_mgr = pool.submit(_fetch_manager_list, code)
            f_not = pool.submit(_fetch_notices, code)
            f_stk = pool.submit(_fetch_top_stocks, code)
            f_fee = pool.submit(_fetch_fees_and_profile, code)

            for fn, target in (
                (f_pz, "pz"), (f_base, "base"), (f_mgr, "mgr"),
                (f_not, "not"), (f_stk, "stk"), (f_fee, "fee"),
            ):
                try:
                    val = fn.result(timeout=9.0)
                    if target == "pz":
                        pz = val or {}
                    elif target == "base":
                        base_info = val or {}
                    elif target == "mgr":
                        mgr_list = val or []
                    elif target == "not":
                        notices = val or []
                    elif target == "stk":
                        quarter_label, top_stocks = val
                    elif target == "fee":
                        fees_prof = val or {}
                except Exception:
                    pass

        dates, unit_navs, ac_navs, day_rets, dividends = _build_nav_series(pz)
        if not dates:
            is_fallback = True

        hs300_map = _load_hs300_map()
        perf_rows, analytics = _compute_analytics_and_perf(dates, ac_navs, hs300_map)

        # 抽样曲线用于业绩走势 & 单位净值图（保留全量最近 360 点，同时保留完整原始数组用于定投测算）
        n_pts = len(dates)
        step = max(1, n_pts // 320)
        idx_l = list(range(0, n_pts, step))
        if idx_l and idx_l[-1] != n_pts - 1:
            idx_l.append(n_pts - 1)

        chart_dates = [dates[i] for i in idx_l]
        chart_unit_nav = [unit_navs[i] for i in idx_l]
        chart_ac_nav = [ac_navs[i] for i in idx_l]
        # 累计收益率曲线 (%)
        base_ac = ac_navs[idx_l[0]] if idx_l and ac_navs[idx_l[0]] > 0 else 1.0
        chart_cum_ret = [round((ac_navs[i] / base_ac - 1.0) * 100.0, 2) for i in idx_l]

        # 最近 30 条历史净值表
        recent_nav_rows = []
        for i in range(n_pts - 1, max(-1, n_pts - 31), -1):
            recent_nav_rows.append({
                "date": dates[i],
                "unit_nav": unit_navs[i],
                "ac_nav": ac_navs[i],
                "daily_return_pct": day_rets[i],
                "dividend": dividends[i],
            })

        # 资产配置（股票/债券/现金占比）
        asset_alloc: List[Dict[str, Any]] = []
        raw_aa = pz.get("Data_assetAllocation") or {}
        if isinstance(raw_aa, dict) and raw_aa.get("series"):
            for s in raw_aa["series"]:
                vals = s.get("data") or []
                latest_v = next((v for v in reversed(vals) if v is not None), None)
                if latest_v is not None:
                    asset_alloc.append({"name": str(s.get("name", "")), "pct": round(float(latest_v), 2)})

        # 基金经理（现任 + 历任）
        cur_mgr_bio: Dict[str, Dict[str, Any]] = {}
        for cm in (pz.get("Data_currentFundManager") or []):
            if isinstance(cm, dict) and cm.get("name"):
                cur_mgr_bio[str(cm["name"])] = {
                    "work_time": str(cm.get("workTime") or ""),
                    "fund_size": str(cm.get("fundSize") or ""),
                    "star": int(cm.get("star") or 0),
                }

        managers: List[Dict[str, Any]] = []
        for m in mgr_list:
            m_name = str(m.get("MGRNAME") or "").strip()
            end_d = str(m.get("LEMPDATE") or "").strip()
            is_current = (end_d == "" or end_d == "--")
            bio = cur_mgr_bio.get(m_name.split(",")[0], {})
            managers.append({
                "name": m_name,
                "start_date": str(m.get("FEMPDATE") or ""),
                "end_date": "至今" if is_current else end_d,
                "is_current": is_current,
                "days": int(float(m.get("DAYS") or 0)),
                "return_pct": round(float(m.get("PENAVGROWTH") or 0.0), 2) if m.get("PENAVGROWTH") not in (None, "") else None,
                "work_time": bio.get("work_time", ""),
                "fund_size": bio.get("fund_size", ""),
            })

        pool_m = CORE_STRATEGY_POOL.get(code) or EXTENDED_FUND_CATALOG.get(code) or {}
        short_name = str(base_info.get("SHORTNAME") or pz.get("fS_name") or pool_m.get("fund_name") or f"基金 {code}")
        risk_map = {"1": "R1 低风险", "2": "R2 中低风险", "3": "R3 中风险", "4": "R4 中高风险", "5": "R5 高风险"}
        r_lvl = risk_map.get(str(base_info.get("RISKLEVEL") or ""), "R3 中风险")
        end_nav_yi = None
        try:
            if base_info.get("ENDNAV"):
                end_nav_yi = round(float(base_info["ENDNAV"]) / 1e8, 2)
        except Exception:
            pass

        cached_base = {
            "fund_code": code,
            "fund_name": short_name,
            "is_fallback": is_fallback,
            "latest_nav": float(base_info.get("DWJZ") or (unit_navs[-1] if unit_navs else 0.0)),
            "latest_ac_nav": float(base_info.get("LJJZ") or (ac_navs[-1] if ac_navs else 0.0)),
            "nav_date": str(base_info.get("FSRQ") or (dates[-1] if dates else "")),
            "daily_return_pct": float(base_info.get("RZDF") or (day_rets[-1] if day_rets else 0.0)),
            "fund_type": str(base_info.get("FTYPE") or pool_m.get("asset_class") or "公募基金"),
            "risk_level": r_lvl,
            "charts": {
                "dates": chart_dates,
                "unit_nav": chart_unit_nav,
                "ac_nav": chart_ac_nav,
                "cum_return_pct": chart_cum_ret,
            },
            "_raw_dates": dates,
            "_raw_unit_navs": unit_navs,
            "historical_performance": perf_rows,
            "historical_nav": recent_nav_rows,
            "analytics": analytics,
            "managers": managers,
            "holdings_distribution": {
                "quarter_label": quarter_label,
                "asset_allocation": asset_alloc,
                "industry_distribution": _infer_industry_distribution(code, top_stocks),
                "top_stocks": top_stocks,
            },
            "profile": {
                "full_name": fees_prof.get("full_name") or short_name,
                "short_name": short_name,
                "fund_code": code,
                "fund_type": str(base_info.get("FTYPE") or fees_prof.get("operation_mode") or "公募基金"),
                "establish_date": str(base_info.get("ISSBDATE") or "--"),
                "scale_yi": end_nav_yi,
                "company": str(base_info.get("JJGS") or "--"),
                "custodian": fees_prof.get("custodian") or "--",
                "benchmark": fees_prof.get("benchmark") or "--",
                "tracking_target": fees_prof.get("tracking_target") or "--",
                "risk_level": r_lvl,
            },
            "notices": notices,
            "product_summary": {
                "operation_mode": fees_prof.get("operation_mode") or str(base_info.get("FTYPE") or "契约型开放式"),
                "risk_level": r_lvl,
                "invest_scope": str(base_info.get("FUNDINVEST") or "详见官方招募说明书与产品资料概要"),
                "dividend_policy": str(base_info.get("FUNDBONUS") or "支持现金分红与红利再投资（免申购费）"),
                "official_summary_url": f"https://fundf10.eastmoney.com/jbgk_{code}.html",
            },
            "trading_rules": {
                "purchase_status": str(base_info.get("SGZT") or "开放申购"),
                "redemption_status": str(base_info.get("SHZT") or "开放赎回"),
                "min_purchase": str(base_info.get("MINSG") or pz.get("fund_minsg") or "10元"),
                "min_dca": str(base_info.get("MINDT") or "10元"),
                "source_rate": str(base_info.get("SOURCERATE") or pz.get("fund_sourceRate") or "--"),
                "discount_rate": str(base_info.get("RATE") or pz.get("fund_Rate") or "--"),
                "management_fee": fees_prof.get("management_fee") or "--",
                "custody_fee": fees_prof.get("custody_fee") or "--",
                "sales_service_fee": fees_prof.get("sales_service_fee") or "0.00% (每年)",
                "purchase_tiers": fees_prof.get("purchase_tiers") or [],
                "redemption_tiers": fees_prof.get("redemption_tiers") or [],
                "settlement_note": "T 日 15:00 前申购/赎回按当日净值确认，A股基金一般 T+1 确认份额，QDII 海外基金一般 T+2 确认份额；持有不足 7 天赎回将收取 1.50% 惩罚性赎回费。",
            },
        }
        with _DETAIL_CACHE_LOCK:
            _DETAIL_CACHE[code] = (now, cached_base)

    # 动态按用户自定义每月定投金额实时计算定投测算表（零网络开销）
    dca_rows = compute_dca_simulation(
        cached_base.get("_raw_dates") or [],
        cached_base.get("_raw_unit_navs") or [],
        monthly_amount=max(100.0, float(dca_monthly or 1000.0)),
    )
    out = {k: v for k, v in cached_base.items() if not k.startswith("_raw_")}
    out["dca_simulation"] = dca_rows
    out["dca_monthly"] = round(max(100.0, float(dca_monthly or 1000.0)), 2)
    return out
