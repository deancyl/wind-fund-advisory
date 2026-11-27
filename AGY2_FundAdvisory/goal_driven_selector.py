# -*- coding: utf-8 -*-
"""
AGY2 全市场 28,177 只离线精英净值湖仓驱动 · 目标量化选基、真实净值回测与偏差诊断引擎 (goal_driven_selector.py)
核心架构（彻底打破 12 只固定池，在线 0 爬虫真全市场海选）：
  1. 优先加载本地 350~400 只跨 10 大风格桶的真实红利再投资复权净值湖仓 (market_lakehouse.py)；
     支持两种选基范围切换：
       - full_market : 全市场海选（主动绩优均衡/行业成长 + 固收+ + 纯债 + 红利 + 宽基 + 量化指增 + QDII + 黄金商品）
       - index_only  : 仅指数/宽基/纯债/黄金低费透明池（防主动经理风格漂移）
  2. 目标驱动动态初筛（彻底告别固定骨架！）：
     - 结合【目标收益 + 持有周期 + C1~C5 + 配置模型】，全湖仓扫描条件胜率 / 夏普 / 卡玛 / 最大回撤 / 正收益概率，
     - 按动态风格桶配额 + Pairwise 相关性去冗余 (|corr| <= 0.82) 精选 28~36 只高度契合本次目标的真实入围候选；
     - 执行历史深度门禁（>= max(500, holding_days + 160) 交易日），根治 .dropna() 截断雪崩；
  3. 真正调用 WinRateOptimizer 在 28~36 只真实入围候选上运行双核求解（ERC/HRP/Core-Satellite/条件胜率 SLSQP/CVaR/半凯利）
     + 局部搜索换基 + 70/30 OOS 验证 + 官方类型宪法护栏 + 真实协方差 PCR 风险贡献度分解；
  4. 仅对终选的 N 只基金并发拉取 10 维详情多因子微调（±10% 有界），并用这 N 只基金自身的真实复权净值合成主回测曲线
     （build_real_nav_portfolio_backtest，绝不将新基金静默退化成沪深 300 指数替身！）；
  5. 输出透明漏斗统计（28,177 -> 合规初筛 -> 精英真净值库 -> 入围寻优 -> N 只终选）、资金配权归因与目标 vs 回测偏差归因。
"""

from __future__ import annotations

import math
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from fund_detail_service import get_fund_full_detail
from market_lakehouse import (
    BUCKET_10_CONFIG,
    classify_fund_bucket_10,
    is_index_style_fund,
    is_lockup_or_banned_fund,
    load_elite_lakehouse,
    _merge_latest_trading_rules_into_meta,
)
from portfolio_optimizer import (
    MAX_DRAWDOWN_BY_TIER,
    WinRateOptimizer,
    apply_asset_class_constitutional_limits,
    calculate_portfolio_risk_contributions,
    recommend_model_for_regime,
)
from strategy_bridge import StrategyBridge, map_target_return_to_tier
from winrate_engine import WinRateEngine

_TIER_ORDER = {"C1": 1, "C2": 2, "C3": 3, "C4": 4, "C5": 5}
_TIER_MAX_REALISTIC_CAGR = {"C1": 6.0, "C2": 9.5, "C3": 14.0, "C4": 20.0, "C5": 28.0}

# 兜底池（仅在极端无精英湖仓文件的裸测环境下触发；100% 场外开放式，零锁定期、零场内 ETF）
_QUANT_OPTIMIZER_POOL: List[Dict[str, Any]] = [
    {"code": "007915", "name": "财通资管鸿福短债A", "bucket": "short_bond", "bucket_label": "中短债现金垫", "asset_class": "bond", "index_col": "H11009", "risk_level": 1, "share_class": "A", "role": "低久期现金垫"},
    {"code": "006210", "name": "广发景华纯债债券A", "bucket": "pure_bond", "bucket_label": "中长纯债固收", "asset_class": "bond", "index_col": "H11009", "risk_level": 1, "share_class": "A", "role": "纯债压舱石"},
    {"code": "002351", "name": "易方达裕祥回报债券A", "bucket": "fixed_income_plus", "bucket_label": "固收+二级债", "asset_class": "bond", "index_col": "H11009", "risk_level": 1, "share_class": "A", "role": "固收增强垫"},
    {"code": "005561", "name": "创金合信中证红利低波动指数A", "bucket": "dividend_value", "bucket_label": "红利低波价值", "asset_class": "equity", "index_col": "H30269", "risk_level": 2, "share_class": "A", "role": "红利低波主锚"},
    {"code": "100032", "name": "富国中证红利指数增强A", "bucket": "dividend_value", "bucket_label": "红利低波价值", "asset_class": "equity", "index_col": "H00922", "risk_level": 2, "share_class": "A", "role": "红利增强底仓"},
    {"code": "000216", "name": "华安易富黄金ETF联接A", "bucket": "commodity_gold", "bucket_label": "纯黄金避险对冲", "asset_class": "gold", "index_col": "AU9999", "risk_level": 2, "share_class": "A", "role": "黄金避险气垫"},
    {"code": "110020", "name": "易方达沪深300ETF联接A", "bucket": "broad_index", "bucket_label": "A股核心宽基", "asset_class": "equity", "index_col": "H00300", "risk_level": 3, "share_class": "A", "role": "A股核心宽基"},
    {"code": "000614", "name": "华安德国(DAX)联接(QDII)A", "bucket": "overseas_qdii", "bucket_label": "海外QDII跨市场", "asset_class": "qdii", "index_col": "SPX_CNY", "risk_level": 3, "share_class": "A", "role": "海外宽基对冲"},
    {"code": "000478", "name": "建信中证500指数增强A", "bucket": "quant_mid_small", "bucket_label": "量化与中小盘指增", "asset_class": "equity", "index_col": "H00905", "risk_level": 3, "share_class": "A", "role": "中盘量化增强"},
    {"code": "270023", "name": "广发全球精选股票(QDII)人民币A", "bucket": "overseas_qdii", "bucket_label": "海外QDII跨市场", "asset_class": "qdii", "index_col": "SPX_CNY", "risk_level": 4, "share_class": "A", "role": "全球权益对冲"},
    {"code": "004194", "name": "招商中证1000指数增强A", "bucket": "quant_mid_small", "bucket_label": "量化与中小盘指增", "asset_class": "equity", "index_col": "H00852", "risk_level": 4, "share_class": "A", "role": "小盘量化增强"},
    {"code": "011612", "name": "华夏上证科创板50成份ETF联接A", "bucket": "sector_theme_index", "bucket_label": "行业主题指数", "asset_class": "equity", "index_col": "STAR50_STITCH", "risk_level": 5, "share_class": "A", "role": "硬核科技进攻"},
]
_POOL_BY_CODE: Dict[str, Dict[str, Any]] = {x["code"]: x for x in _QUANT_OPTIMIZER_POOL}

# 13 大风格桶对应早期（成立前）参考指数列（仅用于 2018 极端历史事件的明文参考测算，绝不污染主净值）
_BUCKET_PROXY_INDEX_COL: Dict[str, str] = {
    "short_bond": "H11009",
    "pure_bond": "H11009",
    "fixed_income_plus": "BENCHMARK_30_70",
    "dividend_value": "H30269",
    "broad_index": "H00300",
    "quant_mid_small": "H00905",
    "sector_theme_index": "STAR50_STITCH",
    "active_balanced_equity": "H00300",
    "active_sector_growth": "STAR50_STITCH",
    "overseas_qdii": "SPX_CNY",
    "hk_offshore": "H00300",
    "commodity_gold": "AU9999",
    "other_commodity": "AU9999",
}

_UI_MODEL_TO_SOLVER: Dict[str, Dict[str, str]] = {
    "all_weather": {
        "primary": "all_weather",
        "secondary": "conditional_winrate",
        "algo_label": "全天候 ERC 等风险贡献 SLSQP + 同温层条件胜率双核求解",
        "math_summary": "在 Ledoit-Wolf 去噪协方差矩阵上求解各资产边际风险贡献均衡 (ERC)，并融合 5 维宏观高斯核条件胜率 SLSQP 规划，在档位回撤上限内最大化目标达成率。",
    },
    "risk_parity": {
        "primary": "hrp_robust",
        "secondary": "cvar_tail",
        "algo_label": "HRP 层次风险平价聚类 + Rockafellar-Uryasev 95% CVaR 尾部极小化",
        "math_summary": "通过相关性距离树做层次聚类与递归二分逆方差分配 (De Prado HRP)，再叠加 95% CVaR 极值下行损失约束，优先压低极端熊市的最大浮亏与修复天数。",
    },
    "dividend_defense": {
        "primary": "core_satellite",
        "secondary": "cvar_tail",
        "algo_label": "核心-卫星逆波动杠铃 + 高股息低波与 CVaR 尾部约束",
        "math_summary": "70%~85% 资金锚定纯债、固收+、红利价值与黄金防御核心（按逆波动配权），剩余卫星仓按夏普与达标胜率精选，严控回撤并兼顾复利稳健。",
    },
    "barbell_growth": {
        "primary": "conditional_winrate",
        "secondary": "kelly_momentum",
        "algo_label": "同温层条件胜率 SLSQP + 半凯利复利动量杠铃求解",
        "math_summary": "在档位大类宪法风控护栏下，一端锁定纯债/黄金底线，另一端采用 5 维宏观同温层 SLSQP 条件胜率优化与半凯利对数复利倾斜，放大中长期向上弹性。",
    },
}

_SOLVER_CACHE: Dict[Tuple[Any, ...], Tuple[float, Dict[str, Any]]] = {}
_SOLVER_CACHE_LOCK = threading.Lock()
_SOLVER_CACHE_TTL_SEC = 1800.0

_SCAN_CACHE: Dict[Tuple[Any, ...], Tuple[float, pd.DataFrame]] = {}
_SCAN_CACHE_LOCK = threading.Lock()

_WF_OOS_CACHE: Dict[Tuple[Any, ...], Tuple[float, Dict[str, Any]]] = {}
_WF_OOS_CACHE_LOCK = threading.Lock()

SURVIVORSHIP_BIAS_DISCLAIMER = (
    "说明：样本外盲测已严格执行 70/30 隔离与历史时间切点 Walk-Forward（杜绝选基与配权阶段的未来信息泄露），"
    "但现存基金历史净值池天然存在轻度幸存者偏差（历史上已清盘基金未在现存池中）；历史表现不等于未来收益承诺，请结合前瞻实盘审计日志持续校验。"
)


def clear_goal_solver_cache() -> None:
    """清空求解器、全市场扫描与 Walk-Forward 缓存（盘后增量日更或单元测试后调用）。"""
    with _SOLVER_CACHE_LOCK:
        _SOLVER_CACHE.clear()
    with _SCAN_CACHE_LOCK:
        _SCAN_CACHE.clear()
    with _WF_OOS_CACHE_LOCK:
        _WF_OOS_CACHE.clear()


def classify_style_cluster(code: str, meta: Optional[Dict[str, Any]] = None) -> str:
    """
    细粒度风格簇分类器（防单赛道/单风格假分散抱团）：
    将每只基金映射至 12 类真实风险暴露簇，确保组合不在 AI/通信/芯片或红利/银行等单一风险因子上过度集中。
    """
    m = meta or {}
    b10 = str(m.get("bucket_10") or m.get("bucket") or "").strip()
    fn = str(m.get("fund_name") or m.get("name") or "")
    ac = str(m.get("asset_class") or "").lower().strip()

    if b10 == "short_bond" or any(k in fn for k in ("中短债", "超短债", "短债", "短融", "同业存单")):
        return "short_bond"
    if b10 == "pure_bond" or (ac == "bond" and b10 != "fixed_income_plus"):
        return "pure_bond"
    if b10 == "fixed_income_plus":
        return "fixed_income_plus"
    if b10 == "commodity_gold" or ac == "gold":
        return "gold"
    if b10 == "other_commodity" or ac == "commodity":
        return "other_commodity"
    if b10 == "overseas_qdii" or ac == "qdii":
        return "global_qdii"
    if b10 == "hk_offshore" or ac == "hk_equity":
        return "hk_offshore"

    if any(
        k in fn
        for k in (
            "人工智能", "AI", "通信", "芯片", "半导体", "算力", "科技", "科创",
            "创业板", "计算机", "软件", "电子", "TMT", "信息技术", "数字经济",
            "机器人", "光模块", "物联网", "大数据", "云计算", "智能制造",
        )
    ):
        return "ai_semi_tech"

    if b10 == "dividend_value" or any(
        k in fn for k in ("红利", "股息", "低波", "银行", "价值", "煤炭", "公用事业", "央企", "国企")
    ):
        return "dividend_bank"

    if b10 == "broad_index":
        return "cn_broad"

    if b10 == "quant_mid_small" or any(
        k in fn for k in ("中证500", "中证1000", "中证2000", "小盘", "微盘", "量化", "国证2000")
    ):
        return "cn_mid_small"

    if b10 == "sector_theme_index" or any(
        k in fn
        for k in (
            "医药", "医疗", "生物", "创新药", "消费", "白酒", "食品", "新能源",
            "光伏", "军工", "有色", "化工", "券商", "金融", "传媒", "汽车", "地产",
        )
    ):
        return "other_sector"

    return "other_active"


def _parse_num(val: Any, default: float = 0.0) -> float:
    if isinstance(val, (int, float)):
        return float(val)
    m = re.search(r"-?\d+(?:\.\d+)?", str(val or ""))
    return float(m.group(0)) if m else default


def _normalize_weights_4dp(weights: Dict[str, float]) -> Dict[str, float]:
    cleaned = [(str(k), max(0.0, float(v))) for k, v in weights.items() if float(v) > 1e-6]
    cleaned.sort(key=lambda x: x[1], reverse=True)
    tot = sum(w for _, w in cleaned) or 1.0
    out: Dict[str, float] = {}
    acc = 0.0
    for idx, (c, w) in enumerate(cleaned):
        if idx == len(cleaned) - 1:
            out[c] = round(max(0.0, 1.0 - acc), 4)
        else:
            nw = round(w / tot, 4)
            out[c] = nw
            acc += nw
    return out


def _enforce_exact_fund_bounds(
    weights: Dict[str, float],
    required_codes: List[str],
    meta_map: Optional[Dict[str, Dict[str, Any]]] = None,
    tier: str = "C3",
    min_floor: float = 0.04,
    model_id: str = "all_weather",
) -> Dict[str, float]:
    """
    盒式约束迭代水填投影（Box-Constrained Simplex Projection）：
    严格保障每只入选基金同时满足 min_floor <= w_i <= cap_i、单风格簇不超硬上限且总和精确为 1.0000，
    彻底杜绝单一主题/风格（如 AI 芯片 67% 或红利银行 54%）过度集中抱团风险。
    """
    n = len(required_codes)
    if n == 0:
        return {}
    tier_u = str(tier or "C3").upper().strip()
    m_u = str(model_id or "all_weather").lower().strip()
    class_caps_by_tier = {
        "C1": {"qdii": 0.06, "gold": 0.10, "hk_equity": 0.08, "commodity": 0.05, "bond": 0.50, "equity": 0.22},
        "C2": {"qdii": 0.10, "gold": 0.12, "hk_equity": 0.12, "commodity": 0.06, "bond": 0.42, "equity": 0.28},
        "C3": {"qdii": 0.15, "gold": 0.15, "hk_equity": 0.15, "commodity": 0.08, "bond": 0.30, "equity": 0.28},
        "C4": {"qdii": 0.15, "gold": 0.12, "hk_equity": 0.15, "commodity": 0.08, "bond": 0.18, "equity": 0.32},
        "C5": {"qdii": 0.15, "gold": 0.10, "hk_equity": 0.15, "commodity": 0.08, "bond": 0.12, "equity": 0.34},
    }.get(tier_u, {"qdii": 0.15, "gold": 0.15, "hk_equity": 0.15, "commodity": 0.08, "bond": 0.30, "equity": 0.28})
    # C 档固收/债券总占比最低底线（只要组合里入选了债基）
    bond_total_floor_by_tier = {"C1": 0.48, "C2": 0.35, "C3": 0.20, "C4": 0.10, "C5": 0.05}
    eq_single_cap = 0.42 if n <= 3 else (0.34 if n <= 4 else class_caps_by_tier["equity"])

    ac_counts: Dict[str, int] = {}
    cluster_counts: Dict[str, int] = {}
    code_clusters: Dict[str, str] = {}
    for c in required_codes:
        m = (meta_map or {}).get(c) or {}
        ac = str(m.get("asset_class", "equity")).lower()
        cl = classify_style_cluster(c, m)
        code_clusters[c] = cl
        ac_counts[ac] = ac_counts.get(ac, 0) + 1
        cluster_counts[cl] = cluster_counts.get(cl, 0) + 1

    bond_cnt = ac_counts.get("bond", 0)
    per_bond_floor = min_floor
    if bond_cnt > 0 and n >= 4:
        target_bond_floor = bond_total_floor_by_tier.get(tier_u, 0.20)
        per_bond_floor = max(min_floor, min(class_caps_by_tier["bond"] - 0.02, round(target_bond_floor / bond_cnt, 4)))

    floors: Dict[str, float] = {}
    caps: Dict[str, float] = {}
    for c in required_codes:
        m = (meta_map or {}).get(c) or {}
        ac = str(m.get("asset_class", "equity")).lower()
        cl = code_clusters[c]
        cl_cnt = max(cluster_counts.get(cl, 1), 1)
        if ac == "qdii" or cl == "global_qdii":
            c_cap = class_caps_by_tier["qdii"] / max(ac_counts.get("qdii", 1), 1)
            c_flr = min_floor
        elif ac == "gold" or cl == "gold":
            c_cap = class_caps_by_tier["gold"] / max(ac_counts.get("gold", 1), 1)
            c_flr = min_floor
        elif ac == "hk_equity" or cl == "hk_offshore":
            c_cap = class_caps_by_tier["hk_equity"] / max(cluster_counts.get("hk_offshore", 1), 1)
            c_flr = min_floor
        elif ac == "commodity" or cl == "other_commodity":
            c_cap = class_caps_by_tier["commodity"] / max(cluster_counts.get("other_commodity", 1), 1)
            c_flr = min_floor
        elif ac == "bond" or cl in ("short_bond", "pure_bond", "fixed_income_plus"):
            c_cap = class_caps_by_tier["bond"]
            c_flr = per_bond_floor
        else:
            # 非债风格簇合计硬上限：默认 <= 34%（确保4dp后 <= 35%），红利防御/杠铃成长放宽至 44%
            if cl == "dividend_bank" and m_u == "dividend_defense":
                cl_total_cap = 0.44
            elif cl == "ai_semi_tech" and m_u == "barbell_growth":
                cl_total_cap = 0.44
            else:
                cl_total_cap = 0.34 if tier_u != "C1" else 0.25
            c_cap = min(eq_single_cap, cl_total_cap / cl_cnt) if cl_cnt >= 2 else min(eq_single_cap, cl_total_cap)
            c_flr = min_floor
        floors[c] = c_flr
        caps[c] = max(c_flr + 0.01, c_cap)

    # 保证 sum(floors) <= 0.96 且 sum(caps) >= 1.02，防止极端少量基金下无可行解
    tot_flr = sum(floors.values())
    if tot_flr > 0.96:
        scale_dn = 0.92 / max(tot_flr, 1e-6)
        floors = {c: max(0.02, v * scale_dn) for c, v in floors.items()}
    tot_cap = sum(caps.values())
    if tot_cap < 1.02:
        scale_up = 1.05 / max(tot_cap, 1e-6)
        caps = {c: min(0.85, max(floors[c] + 0.01, v * scale_up)) for c, v in caps.items()}

    w = {c: max(floors[c], float(weights.get(c, 1.0 / n))) for c in required_codes}
    tot = sum(w.values()) or 1.0
    w = {c: v / tot for c, v in w.items()}

    for _ in range(35):
        excess = 0.0
        deficit = 0.0
        free_up: List[str] = []
        free_dn: List[str] = []
        for c in required_codes:
            if w[c] > caps[c] + 1e-9:
                excess += w[c] - caps[c]
                w[c] = caps[c]
            elif w[c] < floors[c] - 1e-9:
                deficit += floors[c] - w[c]
                w[c] = floors[c]
            else:
                if w[c] < caps[c] - 1e-6:
                    free_up.append(c)
                if w[c] > floors[c] + 1e-6:
                    free_dn.append(c)
        net = excess - deficit
        if abs(net) < 1e-7:
            break
        if net > 0 and free_up:
            room = sum(caps[c] - w[c] for c in free_up)
            if room > 1e-9:
                for c in free_up:
                    w[c] += net * ((caps[c] - w[c]) / room)
        elif net < 0 and free_dn:
            room = sum(w[c] - floors[c] for c in free_dn)
            if room > 1e-9:
                for c in free_dn:
                    w[c] += net * ((w[c] - floors[c]) / room)
        else:
            break

    return _normalize_weights_4dp(w)


def _enforce_exact_fund_floor(
    weights: Dict[str, float],
    required_codes: List[str],
    min_floor: float = 0.03,
) -> Dict[str, float]:
    return _enforce_exact_fund_bounds(weights, required_codes, meta_map=None, tier="C3", min_floor=min_floor)


def _extract_fund_factor_profile(code: str, detail: Dict[str, Any], tier: str, req_cagr: float) -> Dict[str, Any]:
    """从基金详情真数据中提取多因子量化特征并按目标风格动态打分 (0~100)。"""
    analytics = detail.get("analytics") or {}
    cats = {c.get("key"): c for c in (analytics.get("categories") or []) if isinstance(c, dict)}
    sub = analytics.get("sub_metrics") or {}

    def _sub_val(grp: str, name_kw: str, default: float = 0.0) -> float:
        for it in (sub.get(grp) or []):
            if name_kw in str(it.get("name", "")):
                return _parse_num(it.get("value"), default)
        return default

    sharpe = _sub_val("cost_performance", "夏普", 0.5)
    calmar = _sub_val("cost_performance", "卡玛", 0.4)
    max_dd = abs(_sub_val("risk_control", "最大回撤", 15.0))
    ann_vol = abs(_sub_val("risk_control", "波动率", 14.0))
    new_high = _sub_val("return_ability", "新高率", 10.0)
    excess = _sub_val("return_ability", "超额", 0.0)
    ir = _sub_val("tracking_ability", "信息比率", 0.0)
    te = _sub_val("tracking_ability", "跟踪误差", 10.0)

    prof = detail.get("profile") or {}
    scale_yi = prof.get("scale_yi")
    rules = detail.get("trading_rules") or {}
    total_fee_pct = (
        _parse_num(rules.get("management_fee"), 0.5)
        + _parse_num(rules.get("custody_fee"), 0.1)
        + _parse_num(rules.get("sales_service_fee"), 0.0)
    )
    mgrs = detail.get("managers") or []
    cur_mgr_days = max((int(m.get("days", 0) or 0) for m in mgrs if m.get("is_current")), default=365)

    s_ratio = float((cats.get("cost_perf") or {}).get("score", 62))
    s_down = float((cats.get("downside") or {}).get("score", 62))
    s_vol = float((cats.get("volatility") or {}).get("score", 62))
    s_track = float((cats.get("tracking") or {}).get("score", 62))

    fund_bonus = 0.0
    if scale_yi is not None:
        if float(scale_yi) >= 5.0:
            fund_bonus += 3.0
        elif float(scale_yi) < 1.0:
            fund_bonus -= 5.0
    if total_fee_pct <= 0.65:
        fund_bonus += 3.0
    elif total_fee_pct >= 1.5:
        fund_bonus -= 4.0
    if cur_mgr_days >= 730:
        fund_bonus += 2.0

    if req_cagr <= 6.5 or tier in ("C1", "C2"):
        composite = 0.35 * s_down + 0.25 * s_vol + 0.25 * s_ratio + 0.15 * s_track + fund_bonus
        style_note = "低波抗跌优先"
    elif req_cagr >= 13.0 or tier in ("C4", "C5"):
        s_ret = float(np.clip(55.0 + new_high * 1.1 + excess * 0.6, 25.0, 96.0))
        composite = 0.35 * s_ret + 0.30 * s_ratio + 0.20 * s_down + 0.15 * s_track + fund_bonus
        style_note = "弹性与性价比优先"
    else:
        composite = 0.30 * s_ratio + 0.28 * s_down + 0.22 * s_vol + 0.20 * s_track + fund_bonus
        style_note = "风险收益均衡"

    score = int(round(float(np.clip(composite, 30.0, 98.0))))
    return {
        "fund_code": code,
        "quant_score": score,
        "style_note": style_note,
        "sharpe": round(sharpe, 2),
        "calmar": round(calmar, 2),
        "max_dd_pct": round(max_dd, 2),
        "ann_vol_pct": round(ann_vol, 2),
        "new_high_rate_pct": round(new_high, 2),
        "excess_pct": round(excess, 2),
        "info_ratio": round(ir, 2),
        "tracking_error_pct": round(te, 2),
        "total_fee_pct": round(total_fee_pct, 2),
        "scale_yi": scale_yi,
        "mgr_days": cur_mgr_days,
    }


def score_and_tilt_weights_with_details(
    base_weights: Dict[str, float],
    tier: str,
    req_cagr: float,
    metrics_df: Optional[pd.DataFrame] = None,
    equity_tilt_pct: float = 0.0,
) -> Tuple[Dict[str, float], Dict[str, Dict[str, Any]]]:
    """仅对最终选出的 N 只基金并发拉取详情多因子打分并执行 ±10% 有界倾斜，二次投影宪法护栏。"""
    codes = list(base_weights.keys())
    if not codes:
        return {}, {}

    profiles: Dict[str, Dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=min(4, len(codes))) as pool:
        futs = {pool.submit(get_fund_full_detail, c, 1000.0): c for c in codes}
        for fut, c in futs.items():
            try:
                det = fut.result(timeout=6.0) or {}
                profiles[c] = _extract_fund_factor_profile(c, det, tier, req_cagr)
            except Exception:
                profiles[c] = {
                    "fund_code": c,
                    "quant_score": 66,
                    "style_note": "湖仓基准评分",
                    "sharpe": 0.5,
                    "calmar": 0.4,
                    "max_dd_pct": 12.0,
                    "ann_vol_pct": 12.0,
                    "new_high_rate_pct": 10.0,
                    "excess_pct": 0.0,
                    "info_ratio": 0.0,
                    "tracking_error_pct": 10.0,
                    "total_fee_pct": 0.6,
                    "scale_yi": None,
                    "mgr_days": 730,
                }

    avg_score = sum(p["quant_score"] for p in profiles.values()) / max(len(profiles), 1)
    tilted: Dict[str, float] = {}
    for c, w in base_weights.items():
        sc = profiles[c]["quant_score"]
        mult = float(np.clip(1.0 + (sc - avg_score) * 0.005, 0.90, 1.10))
        tilted[c] = float(w) * mult

    try:
        guarded = apply_asset_class_constitutional_limits(
            tilted, tier=tier, metrics_df=metrics_df, equity_tilt_pct=equity_tilt_pct
        )
    except Exception:
        guarded = tilted

    return _normalize_weights_4dp(guarded), profiles


def _apply_investment_quota_filter(
    df: pd.DataFrame,
    investment_amount: float = 50000.0,
    n_funds: int = 6,
) -> pd.DataFrame:
    """
    拟投金额驱动的限购硬过滤 + 两级优雅降级（毫秒级，运行在扫描缓存之后）：
      - 预估单基买入额 est_buy = investment_amount / max(n_funds, 3)；
      - 若单日限购额度 < est_buy / 10（即 > 10 个交易日仍买不完），默认移出候选池；
      - 优雅降级：若某关键低相关桶（如 overseas_qdii / commodity_gold）过滤后变空，
        则保留该桶内已开申且限额最高（>= 100元）的标的并打标 quota_relaxed=True，交由上层输出拆单提示，绝不无解报错。
    """
    if df.empty:
        return df.copy()
    out = df.copy()
    out["quota_relaxed"] = False
    cap = max(1000.0, float(investment_amount or 50000.0))
    est_buy = cap / max(int(n_funds or 6), 3)
    min_daily_limit = est_buy / 10.0

    keep_parts: List[pd.DataFrame] = []
    for b10, grp in out.groupby("bucket_10", sort=False):
        ok_grp = grp[grp["daily_limit_amount"].astype(float) >= min_daily_limit]
        if len(ok_grp) >= 2 or (b10 not in ("overseas_qdii", "commodity_gold", "short_bond", "pure_bond") and len(ok_grp) >= 1):
            keep_parts.append(ok_grp)
        elif len(ok_grp) == 1 and b10 in ("overseas_qdii", "commodity_gold", "short_bond", "pure_bond"):
            keep_parts.append(ok_grp)
        else:
            # 桶内全部受限购约束：两级降级第 1 级 -> 保留日限额 >= 100 元的开申标的并显式标记 quota_relaxed
            relaxed = grp[grp["daily_limit_amount"].astype(float) >= 100.0].sort_values(
                "daily_limit_amount", ascending=False
            ).copy()
            if not relaxed.empty:
                relaxed["quota_relaxed"] = True
                keep_parts.append(relaxed)
    if not keep_parts:
        return out
    return pd.concat(keep_parts, ignore_index=True)


def _scan_lakehouse_universe_metrics(
    nav_df: pd.DataFrame,
    meta_df: pd.DataFrame,
    holding_days: int,
    req_cagr_dec: float,
    universe_mode: str,
    market_snapshot: Optional[Dict[str, Any]] = None,
    investment_amount: float = 50000.0,
    n_funds: int = 6,
) -> pd.DataFrame:
    """
    对本地全市场精英湖仓执行全量指标扫描（基础扫描带当日缓存 + 实时合并交易规则 + 拟投金额限购过滤）：
    100% 剔除锁定期、场内 ETF、暂停申购标的，并统一复用 market_lakehouse.is_index_style_fund 单源口径。
    """
    today_s = time.strftime("%Y-%m-%d")
    scan_key = (today_s, universe_mode, int(holding_days), round(req_cagr_dec, 3), int(nav_df.shape[1]))
    base_df: Optional[pd.DataFrame] = None
    with _SCAN_CACHE_LOCK:
        hit = _SCAN_CACHE.get(scan_key)
        if hit and (time.time() - hit[0]) < 1800.0:
            base_df = hit[1].copy()

    if base_df is None:
        # 历史深度门禁（消除熊底新发基金的建仓时机偏差，确保穿越 2022 熊市与 2024 反转完整周期！）
        strict_min_days = max(1150, int(holding_days) + 250)
        fallback_min_days = max(720, int(holding_days) + 150)

        # 实时合入最新 fund_trading_rules.parquet，确保暂停申购与单日限额 100% 现势
        eligible = _merge_latest_trading_rules_into_meta(meta_df.copy())

        # 单源硬校准：统一调用 market_lakehouse 分类器、锁定期/场内禁令与指数身份判定
        keep_mask: List[bool] = []
        cal_buckets: List[str] = []
        cal_asset_classes: List[str] = []
        cal_bucket_labels: List[str] = []
        cal_is_idx: List[bool] = []
        cal_is_act: List[bool] = []

        for _, mrow in eligible.iterrows():
            code = str(mrow.get("fund_code", "")).strip().zfill(6)
            fn = str(mrow.get("fund_name", ""))
            ft = str(mrow.get("fund_type", ""))
            ps = str(mrow.get("purchase_status", "开放申购"))
            is_allow = bool(mrow.get("is_purchase_allowed", True))
            fee = float(mrow.get("est_total_operating_fee", 0.65) or 0.65)

            if (not is_allow) or ("暂停" in ps) or ("封闭" in ps) or is_lockup_or_banned_fund(fn, code, ps):
                keep_mask.append(False)
                cal_buckets.append("EXCLUDE")
                cal_asset_classes.append("equity")
                cal_bucket_labels.append("")
                cal_is_idx.append(False)
                cal_is_act.append(True)
                continue

            b10 = classify_fund_bucket_10(ft, fn, code, ps)
            if b10.startswith("EXCLUDE"):
                keep_mask.append(False)
                cal_buckets.append(b10)
                cal_asset_classes.append("equity")
                cal_bucket_labels.append("")
                cal_is_idx.append(False)
                cal_is_act.append(True)
                continue

            b_cfg = BUCKET_10_CONFIG.get(b10, {})
            is_idx = is_index_style_fund(ft, fn, b10, operating_fee=fee)
            keep_mask.append(True)
            cal_buckets.append(b10)
            cal_asset_classes.append(str(b_cfg.get("asset_class", mrow.get("asset_class", "equity"))))
            cal_bucket_labels.append(str(b_cfg.get("label", mrow.get("bucket_label", "核心配置"))))
            cal_is_idx.append(bool(is_idx))
            cal_is_act.append(not bool(is_idx))

        eligible["bucket_10"] = cal_buckets
        eligible["asset_class"] = cal_asset_classes
        eligible["bucket_label"] = cal_bucket_labels
        eligible["is_index_eligible"] = cal_is_idx
        eligible["is_active_fund"] = cal_is_act
        eligible = eligible[keep_mask].copy()

        if universe_mode == "index_only":
            eligible = eligible[eligible["is_index_eligible"].astype(bool)].copy()

        # 检查每个风格桶满足严格 1150 交易日门槛的基金数，仅当桶内不足 5 只时对该桶放宽至 fallback_min_days
        bucket_strict_counts: Dict[str, int] = {}
        for _, mrow in eligible.iterrows():
            c = str(mrow["fund_code"])
            if c in nav_df.columns and int(nav_df[c].notna().sum()) >= strict_min_days:
                b = str(mrow.get("bucket_10", "active_balanced_equity"))
                bucket_strict_counts[b] = bucket_strict_counts.get(b, 0) + 1

        rows: List[Dict[str, Any]] = []
        fair_eval_days = 1200
        for _, mrow in eligible.iterrows():
            c = str(mrow["fund_code"])
            if c not in nav_df.columns:
                continue
            s = nav_df[c].dropna()
            b10 = str(mrow.get("bucket_10", "active_balanced_equity"))
            req_min = strict_min_days if bucket_strict_counts.get(b10, 0) >= 5 else fallback_min_days
            # 对刚定向补强的新标杆短债/海外允许最低 360 交易日兜底（仅当该桶连 fallback 都不够 3 只时）
            if len(s) < req_min:
                if b10 in ("short_bond", "overseas_qdii") and len(s) >= 360 and bucket_strict_counts.get(b10, 0) < 3:
                    pass
                else:
                    continue
            s_eval = s.tail(fair_eval_days) if len(s) > fair_eval_days else s
            arr = s_eval.to_numpy(dtype=np.float64)
            rets = arr[1:] / np.maximum(arr[:-1], 1e-8) - 1.0
            n_eval = len(arr)
            years = max(n_eval / 250.0, 0.5)
            tot_ret = arr[-1] / max(arr[0], 1e-8) - 1.0
            ann_ret = (1.0 + tot_ret) ** (1.0 / years) - 1.0 if tot_ret > -0.99 else -0.99
            ann_vol = float(np.std(rets, ddof=1) * np.sqrt(250.0)) if len(rets) > 2 else 0.15
            sharpe = (ann_ret - 0.02) / max(ann_vol, 1e-6)
            cmax = np.maximum.accumulate(arr)
            max_dd = float(np.min((arr - cmax) / np.maximum(cmax, 1e-8)))  # negative
            calmar = ann_ret / max(abs(max_dd), 0.01)

            wr = WinRateEngine.rolling_target_winrate(
                s_eval,
                holding_days=holding_days,
                target_annual_return=req_cagr_dec,
                include_friction=True,
                market_snapshot=market_snapshot,
            )
            rows.append({
                "fund_code": c,
                "fund_name": str(mrow.get("fund_name", c)),
                "fund_type": str(mrow.get("fund_type", "")),
                "bucket": b10,
                "bucket_10": b10,
                "bucket_label": str(mrow.get("bucket_label", "核心配置")),
                "asset_class": str(mrow.get("asset_class", "equity")),
                "is_active_fund": bool(mrow.get("is_active_fund", False)),
                "is_index_eligible": bool(mrow.get("is_index_eligible", False)),
                "real_scale_yi": _safe_float(mrow.get("real_scale_yi"), 0.0) or None,
                "max_star": _safe_float(mrow.get("max_star"), 0.0),
                "five_star_cnt": _safe_float(mrow.get("five_star_cnt"), 0.0),
                "mgr_career_days": _safe_float(mrow.get("mgr_career_days"), 730.0),
                "est_total_operating_fee": _safe_float(mrow.get("est_total_operating_fee"), 0.8),
                "daily_limit_amount": _safe_float(mrow.get("daily_limit_amount"), 1e10),
                "purchase_status": str(mrow.get("purchase_status", "开放申购")),
                "is_purchase_allowed": bool(mrow.get("is_purchase_allowed", True)),
                "inception_date": str(mrow.get("inception_date", ""))[:10],
                "valid_days": int(len(s)),
                "annual_return": float(ann_ret),
                "volatility": float(ann_vol),
                "sharpe": float(sharpe),
                "max_dd": float(max_dd),
                "calmar": float(calmar),
                "win_rate": float(wr.get("conditional_win_rate", wr.get("win_rate", 0.0))),
                "conditional_win_rate": float(wr.get("conditional_win_rate", wr.get("win_rate", 0.0))),
                "unconditional_win_rate": float(wr.get("unconditional_win_rate", wr.get("win_rate", 0.0))),
                "no_loss_rate": float(wr.get("no_loss_rate", 0.0)),
                "cvar_95": float(wr.get("cvar_95_annualized", -0.10)),
            })

        base_df = pd.DataFrame(rows)
        with _SCAN_CACHE_LOCK:
            _SCAN_CACHE[scan_key] = (time.time(), base_df.copy())

    return _apply_investment_quota_filter(base_df, investment_amount=investment_amount, n_funds=n_funds)


def _shortlist_goal_driven_candidates(
    scanned_df: pd.DataFrame,
    nav_df: pd.DataFrame,
    tier: str,
    model_id: str,
    req_cagr_pct: float,
    n_funds: int,
    universe_mode: str,
) -> Tuple[List[str], pd.DataFrame]:
    """
    目标驱动全市场动态初筛 + Pairwise 相关性去冗余（|corr| <= 0.82）：
    根据 (tier, model_id, req_cagr_pct, universe_mode) 动态计算 10 大风格桶配额与目标适配分，
    从全市场 300+ 只真实净值湖仓中精选 28~36 只高度差异化候选送入 WinRateOptimizer。
    """
    if scanned_df.empty:
        return [], scanned_df

    df = scanned_df.copy()
    max_dd_cap = MAX_DRAWDOWN_BY_TIER.get(tier, 0.18)

    def _norm(s: pd.Series) -> pd.Series:
        lo, hi = float(s.min()), float(s.max())
        if hi - lo < 1e-9:
            return pd.Series(0.5, index=s.index)
        return ((s - lo) / (hi - lo)).clip(0.0, 1.0)

    s_sh = _norm(df["sharpe"].clip(-1.0, 3.0))
    s_cal = _norm(df["calmar"].clip(-0.5, 4.0))
    s_lowdd = 1.0 - _norm(df["max_dd"].abs().clip(0.0, 0.60))
    s_cwr = df["conditional_win_rate"].clip(0.0, 1.0)
    s_nlr = df["no_loss_rate"].clip(0.0, 1.0)
    s_star = (df["max_star"].clip(0.0, 5.0) / 5.0) * 0.6 + (df["five_star_cnt"].clip(0.0, 4.0) / 4.0) * 0.4
    s_fee = 1.0 - _norm(df["est_total_operating_fee"].clip(0.1, 2.5))
    # 目标收益契合度（惩罚远低于目标的平庸标的，也惩罚回撤超档位容忍上限 2.2 倍的过山车基）
    req_dec = req_cagr_pct / 100.0
    ret_gap = (df["annual_return"] - req_dec).clip(-0.20, 0.25)
    s_ret_fit = _norm(ret_gap)
    dd_penalty = np.where(df["max_dd"].abs() > max_dd_cap * 2.1, 0.18, 0.0)

    if req_cagr_pct <= 7.0 or tier == "C1":
        df["_goal_rank"] = 0.35 * s_nlr + 0.25 * s_lowdd + 0.22 * s_sh + 0.10 * s_cwr + 0.08 * s_fee - dd_penalty
    elif req_cagr_pct >= 15.0 or tier in ("C4", "C5"):
        df["_goal_rank"] = 0.36 * s_cwr + 0.26 * s_ret_fit + 0.18 * s_cal + 0.12 * s_sh + 0.08 * s_star - dd_penalty
    else:
        df["_goal_rank"] = 0.32 * s_cwr + 0.24 * s_sh + 0.18 * s_cal + 0.14 * s_nlr + 0.07 * s_star + 0.05 * s_fee - dd_penalty

    # 按模型特征做风格微调
    if model_id == "risk_parity":
        df["_goal_rank"] += 0.10 * s_lowdd + 0.06 * s_sh
    elif model_id == "dividend_defense":
        df["_goal_rank"] += np.where(df["bucket_10"].isin(["dividend_value", "short_bond", "pure_bond", "fixed_income_plus", "commodity_gold"]), 0.12, 0.0)
    elif model_id == "barbell_growth":
        df["_goal_rank"] += np.where(df["bucket_10"].isin(["short_bond", "pure_bond", "commodity_gold", "active_sector_growth", "quant_mid_small", "sector_theme_index", "overseas_qdii"]), 0.10, 0.0)

    # 动态 12 桶入围配额（总计 ~36 只，显式纳入 short_bond 中短债与 hk_offshore 港股），随目标收益与档位显著变化
    if req_cagr_pct <= 7.0 or tier == "C1":
        quotas = {
            "short_bond": 6, "pure_bond": 6, "fixed_income_plus": 6, "dividend_value": 5, "commodity_gold": 4,
            "broad_index": 3, "overseas_qdii": 3, "hk_offshore": 1, "active_balanced_equity": 2,
        }
    elif req_cagr_pct <= 10.5 or tier == "C2":
        quotas = {
            "short_bond": 4, "pure_bond": 4, "fixed_income_plus": 5, "dividend_value": 5, "active_balanced_equity": 5,
            "broad_index": 4, "commodity_gold": 3, "overseas_qdii": 3, "hk_offshore": 2, "quant_mid_small": 2,
        }
    elif req_cagr_pct >= 15.0 or tier in ("C4", "C5"):
        quotas = {
            "active_sector_growth": 6, "active_balanced_equity": 6, "quant_mid_small": 6,
            "sector_theme_index": 5, "overseas_qdii": 4, "dividend_value": 3, "hk_offshore": 2,
            "commodity_gold": 2, "short_bond": 2, "pure_bond": 2, "fixed_income_plus": 2,
        }
    else:
        quotas = {
            "short_bond": 3, "pure_bond": 3, "fixed_income_plus": 4, "dividend_value": 4, "broad_index": 4,
            "quant_mid_small": 4, "active_balanced_equity": 5, "active_sector_growth": 3,
            "sector_theme_index": 2, "overseas_qdii": 3, "hk_offshore": 2, "commodity_gold": 3,
        }

    # 仅指数模式：将主动桶配额无缝转移到低费指数/宽基/红利/QDII/短债/纯债桶（零 other_commodity）
    if universe_mode == "index_only":
        fip_q = quotas.get("fixed_income_plus", 0)
        quotas = {
            "short_bond": quotas.get("short_bond", 3) + (fip_q + 1) // 2,
            "pure_bond": quotas.get("pure_bond", 3) + fip_q // 2,
            "dividend_value": quotas.get("dividend_value", 4) + 2,
            "broad_index": quotas.get("broad_index", 4) + quotas.get("active_balanced_equity", 0) // 2,
            "quant_mid_small": quotas.get("quant_mid_small", 4) + (quotas.get("active_balanced_equity", 0) + 1) // 2,
            "sector_theme_index": quotas.get("sector_theme_index", 3) + quotas.get("active_sector_growth", 0),
            "overseas_qdii": quotas.get("overseas_qdii", 3),
            "hk_offshore": quotas.get("hk_offshore", 2),
            "commodity_gold": quotas.get("commodity_gold", 3),
        }

    # 预计算日收益率供 Pairwise 相关性去冗余
    ret_cache: Dict[str, pd.Series] = {}

    def _get_ret(c: str) -> pd.Series:
        if c not in ret_cache:
            ret_cache[c] = nav_df[c].dropna().pct_change().dropna()
        return ret_cache[c]

    def _is_too_correlated(code: str, existing: List[str], thresh: float = 0.82) -> bool:
        if not existing:
            return False
        r1 = _get_ret(code)
        for ex in existing:
            r2 = _get_ret(ex)
            idx = r1.index.intersection(r2.index)
            if len(idx) < 120:
                continue
            v1, v2 = r1.loc[idx].values, r2.loc[idx].values
            if np.std(v1) < 1e-8 or np.std(v2) < 1e-8:
                continue
            corr = float(np.corrcoef(v1, v2)[0, 1])
            if np.isfinite(corr) and abs(corr) > thresh:
                return True
        return False

    shortlisted: List[str] = []
    shortlist_set: set = set()

    for b10, q in quotas.items():
        if q <= 0:
            continue
        sub = df[df["bucket_10"] == b10].sort_values("_goal_rank", ascending=False)
        picked_in_bucket: List[str] = []
        for _, row in sub.iterrows():
            c = str(row["fund_code"])
            if c in shortlist_set:
                continue
            # 同桶内强去冗余（防止 3 只几乎重合的沪深 300 或 3 只高度相似的债券基占满名额）
            corr_th = 0.88 if b10 in ("short_bond", "pure_bond", "commodity_gold") else 0.82
            if _is_too_correlated(c, picked_in_bucket, thresh=corr_th):
                continue
            picked_in_bucket.append(c)
            shortlisted.append(c)
            shortlist_set.add(c)
            if len(picked_in_bucket) >= q:
                break

    # 若不足 max(24, n_funds * 3)，按全局 _goal_rank 补足
    target_min = max(24, n_funds * 3)
    if len(shortlisted) < target_min:
        for _, row in df.sort_values("_goal_rank", ascending=False).iterrows():
            c = str(row["fund_code"])
            if c in shortlist_set:
                continue
            if _is_too_correlated(c, shortlisted, thresh=0.86):
                continue
            shortlisted.append(c)
            shortlist_set.add(c)
            if len(shortlisted) >= target_min:
                break

    sub_meta = df[df["fund_code"].isin(shortlisted)].copy()
    return shortlisted, sub_meta


def build_real_nav_portfolio_backtest(
    fund_weights: Dict[str, float],
    elite_nav: Optional[pd.DataFrame],
    meta_map: Dict[str, Dict[str, Any]],
    tier: str = "C3",
    target_return_pct: float = 10.0,
) -> Tuple[pd.DataFrame, Optional[pd.DataFrame], Dict[str, Any]]:
    """
    100% 真实复权净值组合回测引擎（彻底消灭静默用沪深 300 替身的问题！）：
      - primary df_bt：严格在全部入选基金【共同拥有的真实历史复权净值区间】上按实际日收益率加权合成，
        同步对齐沪深 300、红利低波、纯债指数基准曲线；
      - proxy_early_df：仅当组合共同真实起点晚于 2018-02-01 时，按每只基金的 10 桶基准指数生成早期参考序列，
        专供极端事件卡片对 2018 熊市做明文标注的参考测算，绝不污染主回测净值。
    """
    df_mat = StrategyBridge.load_matrix()
    df_mat = df_mat.copy()
    df_mat["dt"] = pd.to_datetime(df_mat["date"]).dt.normalize()
    df_mat_idx = df_mat.set_index("dt")

    valid_codes = [c for c in fund_weights if elite_nav is not None and c in elite_nav.columns and float(fund_weights[c]) > 1e-6]
    if elite_nav is None or len(valid_codes) < len([c for c, w in fund_weights.items() if float(w) > 1e-6]):
        # 若个别代码不在精英湖仓（例如旧测试或调仓对比里的存量旧基），回退到 StrategyBridge
        bt_fb = StrategyBridge.build_custom_portfolio_backtest(
            fund_weights=fund_weights, tier=tier, target_return_pct=target_return_pct
        )
        return bt_fb, None, {"is_real_nav": False, "common_start_date": str(bt_fb["date"].iloc[0])[:10] if not bt_fb.empty else ""}

    sub_nav = elite_nav[valid_codes].dropna(how="any")
    if len(sub_nav) < 60:
        bt_fb = StrategyBridge.build_custom_portfolio_backtest(
            fund_weights=fund_weights, tier=tier, target_return_pct=target_return_pct
        )
        return bt_fb, None, {"is_real_nav": False, "common_start_date": str(bt_fb["date"].iloc[0])[:10] if not bt_fb.empty else ""}

    tot_w = sum(float(fund_weights[c]) for c in valid_codes) or 1.0
    w_vec = np.array([float(fund_weights[c]) / tot_w for c in valid_codes], dtype=np.float64)

    # 真实日收益率合成（每日再平衡保持真实目标配比，严格零未来函数）
    ret_mat = sub_nav.pct_change().fillna(0.0).to_numpy(dtype=np.float64)
    port_ret = ret_mat @ w_vec
    port_ret[0] = 0.0
    p_nav = np.cumprod(1.0 + port_ret)
    p_cmax = np.maximum.accumulate(p_nav)
    p_dd = (p_nav - p_cmax) / np.maximum(p_cmax, 1e-8) * 100.0

    # 95% 实盘仓位 + 5% 现金缓冲与年化 0.20% 调仓摩擦校准
    cash_d = 0.018 / 250.0
    otc_ret = 0.95 * port_ret + 0.05 * cash_d - (0.0020 / 250.0)
    otc_ret[0] = 0.0
    otc_nav = np.cumprod(1.0 + otc_ret)
    otc_cmax = np.maximum.accumulate(otc_nav)
    otc_dd = (otc_nav - otc_cmax) / np.maximum(otc_cmax, 1e-8) * 100.0

    dates_idx = sub_nav.index
    n_days = len(dates_idx)

    # 大类资产占比
    w_eq = w_bd = w_gd = w_qd = 0.0
    for c, w in zip(valid_codes, w_vec):
        ac = str((meta_map.get(c) or {}).get("asset_class", "equity")).lower()
        if ac == "bond":
            w_bd += float(w)
        elif ac == "gold":
            w_gd += float(w)
        elif ac == "qdii":
            w_qd += float(w)
        else:
            w_eq += float(w)

    def _align_bm(col_name: str) -> np.ndarray:
        if col_name not in df_mat_idx.columns:
            return np.ones(n_days, dtype=np.float64)
        s_bm = df_mat_idx[col_name].astype(float).reindex(dates_idx).ffill().bfill()
        v = s_bm.to_numpy(dtype=np.float64)
        return v / max(float(v[0]), 1e-8)

    h300_nav = _align_bm("H00300")
    h300_cmax = np.maximum.accumulate(h300_nav)
    h300_dd = (h300_nav - h300_cmax) / np.maximum(h300_cmax, 1e-8) * 100.0

    out_df = pd.DataFrame({
        "date": [d.strftime("%Y-%m-%d") for d in dates_idx],
        "strategy_nav": p_nav,
        "strategy_nav_otc": otc_nav,
        "h300_nav": h300_nav,
        "bm_nav_沪深300": h300_nav,
        "bm_nav_红利低波": _align_bm("H30269"),
        "bm_nav_纯债指数": _align_bm("H11009"),
        "strategy_drawdown": p_dd,
        "strategy_otc_drawdown": otc_dd,
        "h300_drawdown": h300_dd,
        "weight_ashare": np.full(n_days, w_eq),
        "weight_bond": np.full(n_days, w_bd),
        "weight_gold": np.full(n_days, w_gd),
        "weight_spx": np.full(n_days, w_qd),
    })

    common_start_str = str(out_df["date"].iloc[0])[:10]

    # 若共同真实存续期晚于 2018-02-01，单独构造 2018 参考基准序列（仅用于早期熊市事件的明文参考）
    proxy_early_df: Optional[pd.DataFrame] = None
    if common_start_str > "2018-02-01":
        n_m = len(df_mat)
        p_ret_e = np.zeros(n_m, dtype=np.float64)
        for c, w in zip(valid_codes, w_vec):
            b10 = str((meta_map.get(c) or {}).get("bucket_10", "active_balanced_equity"))
            col = _BUCKET_PROXY_INDEX_COL.get(b10, "H00300")
            if col not in df_mat.columns:
                col = "H00300"
            s_arr = df_mat[col].astype(float).ffill().bfill().to_numpy(dtype=np.float64)
            r_arr = np.zeros(n_m, dtype=np.float64)
            r_arr[1:] = s_arr[1:] / np.maximum(s_arr[:-1], 1e-8) - 1.0
            p_ret_e += float(w) * r_arr
        pe_nav = np.cumprod(1.0 + (0.95 * p_ret_e + 0.05 * cash_d))
        h300_e = df_mat["H00300"].astype(float).to_numpy(dtype=np.float64)
        h300_e = h300_e / max(float(h300_e[0]), 1e-8)
        proxy_early_df = pd.DataFrame({
            "date": [str(d)[:10] for d in df_mat["date"].tolist()],
            "strategy_nav": pe_nav,
            "strategy_nav_otc": pe_nav,
            "h300_nav": h300_e,
        })

    bt_info = {
        "is_real_nav": True,
        "common_start_date": common_start_str,
        "common_end_date": str(out_df["date"].iloc[-1])[:10],
        "common_trading_days": int(n_days),
        "has_early_proxy_reference": proxy_early_df is not None,
    }
    return out_df, proxy_early_df, bt_info


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        v = float(val)
        return v if math.isfinite(v) else default
    except Exception:
        return default


def _build_dynamic_fund_plain_why(code: str, meta: Dict[str, Any], fp: Dict[str, Any]) -> Tuple[str, str]:
    """为全市场任意入选基金动态生成专业且通俗的角色标签与入选简介。"""
    b_label = str(meta.get("bucket_label") or "核心配置")
    f_type = str(meta.get("fund_type") or "")
    scale_raw = meta.get("real_scale_yi")
    if scale_raw is None or (isinstance(scale_raw, float) and not math.isfinite(scale_raw)):
        scale_raw = fp.get("scale_yi")
    scale = _safe_float(scale_raw, 0.0)
    stars = int(round(_safe_float(meta.get("max_star"), 0.0)))
    mgr_yrs = round(_safe_float(meta.get("mgr_career_days"), 730.0) / 365.0, 1)
    fee = _safe_float(meta.get("est_total_operating_fee"), 0.0) or _safe_float(fp.get("total_fee_pct"), 0.6)
    parts = [f"所属【{b_label}】"]
    if f_type:
        parts.append(f"类型 {f_type}")
    if scale > 0:
        parts.append(f"单基规模 {scale:.1f} 亿")
    if stars >= 4:
        parts.append(f"机构 {stars} 星评级")
    if meta.get("is_active_fund"):
        parts.append(f"经理从业 {mgr_yrs:.1f} 年")
    parts.append(f"年运作费率约 {fee:.2f}%")
    return b_label, "，".join(parts) + "。"


def _normalize_code_list(codes: Optional[List[str]]) -> List[str]:
    out: List[str] = []
    if not codes:
        return out
    for raw in codes:
        s = str(raw or "").strip()
        if not s:
            continue
        if s.isdigit():
            s = s.zfill(6)
        if s not in out:
            out.append(s)
    return sorted(out)


def _evaluate_true_walk_forward_oos(
    nav_df: Optional[pd.DataFrame],
    meta_df: Optional[pd.DataFrame],
    tier: str,
    model_id: str,
    n_funds: int,
    holding_days: int,
    req_cagr_dec: float,
    universe_mode: str,
    strict_70_30_pct: float = 0.0,
) -> Dict[str, Any]:
    """
    真实多切点时间截断 Walk-Forward 样本外盲测（毫秒级向量化，严格零未来信息泄露）：
    在历史时间切点 cutoff 处彻底屏蔽所有未来净值，仅凭 <= cutoff 的历史表现选基定权并过宪法与风格簇上限，
    然后在完全未见过的未来 (cutoff, cutoff + eval_hd] 窗口实测到手收益（含申购费与调仓摩擦）与真实最大回撤。
    """
    fallback = {
        "method": "strict_70_30_and_walk_forward",
        "strict_70_30_oos_winrate_pct": round(float(strict_70_30_pct), 1),
        "wf_oos_winrate_pct": round(float(strict_70_30_pct), 1),
        "wf_oos_positive_rate_pct": 0.0,
        "wf_avg_return_pct": 0.0,
        "wf_worst_mdd_pct": 0.0,
        "splits": [],
        "note": SURVIVORSHIP_BIAS_DISCLAIMER,
    }
    if nav_df is None or meta_df is None or nav_df.empty or meta_df.empty:
        return fallback

    latest_dt = str(nav_df.index[-1])[:10]
    wf_key = (
        tier,
        model_id,
        int(n_funds),
        int(holding_days),
        round(float(req_cagr_dec), 3),
        universe_mode,
        int(nav_df.shape[1]),
        latest_dt,
    )
    with _WF_OOS_CACHE_LOCK:
        hit = _WF_OOS_CACHE.get(wf_key)
        if hit and (time.time() - hit[0]) < 3600.0:
            cached = dict(hit[1])
            cached["strict_70_30_oos_winrate_pct"] = round(float(strict_70_30_pct), 1)
            return cached

    try:
        all_dates = nav_df.index.sort_values()
        n_total = len(all_dates)
        eval_hd = max(63, min(int(holding_days), 252))
        if n_total < eval_hd + 360:
            return fallback

        # 2~3 个严格递进的历史盲测切点（每个切点前 >= 360 交易日训练，后 == eval_hd 交易日盲测）
        raw_cutoffs = [
            n_total - eval_hd - 360,
            n_total - eval_hd - 180,
            n_total - eval_hd - 1,
        ]
        cutoffs = [idx for idx in raw_cutoffs if idx >= 360 and (idx + eval_hd) < n_total]
        if not cutoffs:
            cutoffs = [max(360, n_total - eval_hd - 1)]

        # 元数据快速字典（仅取符合 universe_mode 且非锁定期/非场内的标的）
        m_df = meta_df.copy()
        if universe_mode == "index_only" and "is_index_eligible" in m_df.columns:
            m_df = m_df[m_df["is_index_eligible"].astype(bool)]
        meta_lookup: Dict[str, Dict[str, Any]] = {}
        for _, r in m_df.iterrows():
            c = str(r.get("fund_code", "")).strip().zfill(6)
            if c not in nav_df.columns:
                continue
            fn = str(r.get("fund_name", ""))
            ps = str(r.get("purchase_status", "开放申购"))
            if is_lockup_or_banned_fund(fn, c, ps):
                continue
            meta_lookup[c] = r.to_dict()

        if len(meta_lookup) < n_funds:
            return fallback

        elig_codes = list(meta_lookup.keys())
        nav_sorted = nav_df.loc[all_dates, elig_codes]
        splits_out: List[Dict[str, Any]] = []
        sub_fee = 0.0012
        cash_d = 0.018 / 250.0
        rebal_d = 0.0020 / 250.0

        for cut_idx in cutoffs:
            train_slice = nav_sorted.iloc[: cut_idx + 1]
            future_slice = nav_sorted.iloc[cut_idx : cut_idx + eval_hd + 1]
            if len(future_slice) < 30:
                continue

            # 仅用 <= cutoff 的数据对每只候选基金打分（零未来函数！）
            cand_scores: List[Tuple[str, float, float, str, str]] = []
            for c in elig_codes:
                s_tr = train_slice[c].dropna()
                if len(s_tr) < 320:
                    continue
                arr = s_tr.tail(756).to_numpy(dtype=np.float64)
                if len(arr) < 200 or arr[0] <= 0:
                    continue
                rets = arr[1:] / np.maximum(arr[:-1], 1e-8) - 1.0
                yrs = max(len(arr) / 250.0, 0.5)
                ann_r = (arr[-1] / arr[0]) ** (1.0 / yrs) - 1.0
                vol = float(np.std(rets, ddof=1) * np.sqrt(250.0)) if len(rets) > 2 else 0.15
                sh = (ann_r - 0.02) / max(vol, 1e-4)
                cmax = np.maximum.accumulate(arr)
                mdd = abs(float(np.min((arr - cmax) / np.maximum(cmax, 1e-8))))
                cal = ann_r / max(mdd, 0.01)
                if tier in ("C1", "C2"):
                    sc = 0.45 * sh + 0.35 * cal - 1.8 * mdd
                elif tier in ("C4", "C5"):
                    sc = 0.45 * sh + 0.35 * ann_r + 0.20 * cal - 0.5 * mdd
                else:
                    sc = 0.45 * sh + 0.30 * cal + 0.25 * ann_r - 1.0 * mdd
                m_i = meta_lookup[c]
                b10 = str(m_i.get("bucket_10", "broad_index"))
                cl = classify_style_cluster(c, m_i)
                cand_scores.append((c, float(sc), max(vol, 0.015), b10, cl))

            if len(cand_scores) < n_funds:
                continue
            cand_scores.sort(key=lambda x: x[1], reverse=True)

            # 按大类与风格簇分散盲选 n_funds 只（纯历史信息）
            picked: List[Tuple[str, float, float, str, str]] = []
            picked_set = set()
            cluster_cnt: Dict[str, int] = {}

            def _pick_first(pred: Callable[[Tuple[str, float, float, str, str]], bool]) -> None:
                for item in cand_scores:
                    c, _, _, _, cl = item
                    if c in picked_set:
                        continue
                    if pred(item):
                        picked.append(item)
                        picked_set.add(c)
                        cluster_cnt[cl] = cluster_cnt.get(cl, 0) + 1
                        return

            if tier in ("C1", "C2"):
                _pick_first(lambda x: x[3] == "short_bond")
            if tier in ("C1", "C2", "C3"):
                if not any(meta_lookup[x[0]].get("asset_class") == "bond" for x in picked):
                    _pick_first(lambda x: meta_lookup[x[0]].get("asset_class") == "bond")
            if model_id == "all_weather" and tier in ("C2", "C3", "C4"):
                _pick_first(lambda x: x[3] == "commodity_gold")
                _pick_first(lambda x: x[3] == "overseas_qdii")
            for item in cand_scores:
                if len(picked) >= n_funds:
                    break
                c, _, _, b10, cl = item
                if c in picked_set:
                    continue
                max_cl = 1 if cl in ("gold", "global_qdii", "hk_offshore", "other_commodity") else 2
                if tier in ("C3", "C4", "C5") and b10 in ("short_bond", "pure_bond"):
                    if sum(1 for x in picked if x[3] in ("short_bond", "pure_bond")) >= 1:
                        continue
                if cluster_cnt.get(cl, 0) >= max_cl:
                    continue
                picked.append(item)
                picked_set.add(c)
                cluster_cnt[cl] = cluster_cnt.get(cl, 0) + 1

            picked_codes = [x[0] for x in picked[:n_funds]]
            if len(picked_codes) < 3:
                continue

            # 仅用训练期逆波动配权并过档位宪法与风格上限
            inv_vol = {x[0]: 1.0 / max(x[2], 0.015) for x in picked[:n_funds]}
            p_meta = {c: meta_lookup[c] for c in picked_codes}
            p_cand_df = pd.DataFrame([meta_lookup[c] for c in picked_codes])
            w_guard = apply_asset_class_constitutional_limits(inv_vol, tier=tier, metrics_df=p_cand_df, equity_tilt_pct=0.0)
            w_final = _enforce_exact_fund_bounds(
                w_guard, picked_codes, meta_map=p_meta, tier=tier, min_floor=0.04, model_id=model_id
            )

            # 在完全未见过的未来区间 future_slice 上盲测实盘净值
            f_sub = future_slice[picked_codes].ffill().bfill()
            if len(f_sub) < 20 or f_sub.isna().any().any():
                continue
            w_vec = np.array([float(w_final.get(c, 0.0)) for c in picked_codes], dtype=np.float64)
            w_vec = w_vec / max(float(np.sum(w_vec)), 1e-8)
            f_rets = f_sub.pct_change().fillna(0.0).to_numpy(dtype=np.float64)
            p_ret = f_rets @ w_vec
            p_ret[0] = 0.0
            otc_r = 0.95 * p_ret + 0.05 * cash_d - rebal_d
            otc_r[0] = 0.0
            nav_path = (1.0 - sub_fee) * np.cumprod(1.0 + otc_r)
            realized_ret = float(nav_path[-1] - 1.0)
            yrs_f = max((len(nav_path) - 1) / 250.0, 0.25)
            realized_ann = float((1.0 + realized_ret) ** (1.0 / yrs_f) - 1.0) if realized_ret > -0.99 else -0.99
            cmax_f = np.maximum.accumulate(nav_path)
            realized_mdd = float(np.min((nav_path - cmax_f) / np.maximum(cmax_f, 1e-8)))

            splits_out.append({
                "train_cutoff": str(all_dates[cut_idx])[:10],
                "test_start": str(f_sub.index[0])[:10],
                "test_end": str(f_sub.index[-1])[:10],
                "test_days": int(len(f_sub) - 1),
                "realized_return_pct": round(realized_ret * 100.0, 2),
                "realized_ann_return_pct": round(realized_ann * 100.0, 2),
                "realized_mdd_pct": round(realized_mdd * 100.0, 2),
                "positive": bool(realized_ret > 0.0),
                "hit_target": bool(realized_ann >= req_cagr_dec),
                "selected_codes": picked_codes,
            })

        if not splits_out:
            return fallback

        wf_hit_pct = round(sum(1 for s in splits_out if s["hit_target"]) / len(splits_out) * 100.0, 1)
        wf_pos_pct = round(sum(1 for s in splits_out if s["positive"]) / len(splits_out) * 100.0, 1)
        wf_avg_ret = round(float(np.mean([s["realized_return_pct"] for s in splits_out])), 2)
        wf_worst_mdd = round(float(np.min([s["realized_mdd_pct"] for s in splits_out])), 2)

        res = {
            "method": "strict_70_30_and_walk_forward",
            "strict_70_30_oos_winrate_pct": round(float(strict_70_30_pct), 1),
            "wf_oos_winrate_pct": wf_hit_pct,
            "wf_oos_positive_rate_pct": wf_pos_pct,
            "wf_avg_return_pct": wf_avg_ret,
            "wf_worst_mdd_pct": wf_worst_mdd,
            "splits": splits_out,
            "note": SURVIVORSHIP_BIAS_DISCLAIMER,
        }
        with _WF_OOS_CACHE_LOCK:
            _WF_OOS_CACHE[wf_key] = (time.time(), dict(res))
        return res
    except Exception:
        return fallback


def solve_goal_driven_portfolio(
    risk_level: str = "C3",
    fund_count: int = 6,
    model_id: str = "all_weather",
    target_return_pct: float = 10.0,
    horizon_months: int = 12,
    universe_mode: str = "full_market",
    market_snapshot: Optional[Dict[str, Any]] = None,
    force_recompute: bool = False,
    progress_cb: Optional[Callable[[int, str], None]] = None,
    exclude_codes: Optional[List[str]] = None,
    include_codes: Optional[List[str]] = None,
    investment_amount: float = 50000.0,
) -> Dict[str, Any]:
    """
    全站唯一单源 · 全市场目标驱动真量化求解引擎（v2.2.0 中国场外基金止血硬化版）：
    28,177 全市场漏斗 -> 100% 场外开放式零锁定期真净值湖仓 -> 拟投金额限购硬过滤 + 相关性去冗余
    -> WinRateOptimizer 严格前 70% 训练与盲测 OOS -> 风格防抱团 + 全天候四资产两级降级 -> 详情微调 + 真实回测与多切点 Walk-Forward。
    """
    tier = str(risk_level or "C3").upper().strip()
    if tier not in _TIER_ORDER:
        tier = "C3"
    m_id = str(model_id or "all_weather").strip().lower()
    if m_id not in _UI_MODEL_TO_SOLVER:
        m_id = "all_weather"
    u_mode = str(universe_mode or "full_market").strip().lower()
    if u_mode not in ("full_market", "index_only"):
        u_mode = "full_market"
    n_funds = max(3, min(8, int(fund_count or 6)))
    t_ret = max(2.0, min(60.0, float(target_return_pct or 10.0)))
    h_mon = max(3, min(60, int(horizon_months or 12)))
    cap_amt = max(1000.0, float(investment_amount or 50000.0))

    norm_include = _normalize_code_list(include_codes)
    norm_exclude = [c for c in _normalize_code_list(exclude_codes) if c not in norm_include]
    constraint_warnings: List[str] = []
    if len(norm_include) > n_funds:
        constraint_warnings.append(
            f"锁定基金数量（{len(norm_include)} 只）超出组合只数上限（{n_funds} 只），已按代码顺序保留前 {n_funds} 只锁定标的。"
        )
        norm_include = norm_include[:n_funds]

    cache_key = (
        tier,
        m_id,
        n_funds,
        round(t_ret, 1),
        h_mon,
        u_mode,
        tuple(norm_exclude),
        tuple(norm_include),
        round(cap_amt, -2),
    )
    now_ts = time.time()
    if not force_recompute:
        with _SOLVER_CACHE_LOCK:
            hit = _SOLVER_CACHE.get(cache_key)
            if hit and (now_ts - hit[0]) < _SOLVER_CACHE_TTL_SEC:
                if progress_cb:
                    progress_cb(100, "命中当日同参量化求解缓存")
                res_copy = dict(hit[1])
                res_copy["solver_audit"] = {**res_copy.get("solver_audit", {}), "from_cache": True}
                return res_copy

    t0 = time.monotonic()
    if progress_cb:
        progress_cb(10, "步骤 1/4：加载全市场 28,177 只漏斗与本地真实复权净值湖仓...")

    snap = market_snapshot if market_snapshot is not None else StrategyBridge.get_latest_market_snapshot(force_reload=False)
    holding_days = max(63, min(756, int(round(h_mon * 21))))
    req_cagr_pct = round((((1.0 + t_ret / 100.0) ** (12.0 / h_mon)) - 1.0) * 100.0, 2)
    req_cagr_dec = max(0.02, min(0.60, req_cagr_pct / 100.0))

    eq_tilt = float((snap or {}).get("equity_tilt_pct", 0.0) or 0.0)
    if eq_tilt == 0.0:
        try:
            from advisory_engine import compute_ten_dimension_votes
            tdv = compute_ten_dimension_votes(snapshot=snap, tier=tier)
            eq_tilt = float(tdv.get("equity_tilt_pct", 0.0) or 0.0)
        except Exception:
            eq_tilt = 0.0

    # 1. 优先加载本地真实复权净值湖仓
    elite_nav, elite_meta, lakehouse_status = load_elite_lakehouse()
    use_full_lakehouse = (
        elite_nav is not None
        and elite_meta is not None
        and not elite_nav.empty
        and elite_nav.shape[1] >= 25
    )

    solver_spec = _UI_MODEL_TO_SOLVER[m_id]
    meta_map: Dict[str, Dict[str, Any]] = {}
    funnel_audit: Dict[str, Any] = {}
    strict_70_30_oos_pct: float = 0.0
    eff_include: List[str] = []

    if use_full_lakehouse:
        if progress_cb:
            progress_cb(32, f"步骤 2/4：扫描本地 {elite_nav.shape[1]} 只场外开放净值并执行限购过滤与相关性去冗余...")

        scanned_df = _scan_lakehouse_universe_metrics(
            nav_df=elite_nav,
            meta_df=elite_meta,
            holding_days=holding_days,
            req_cagr_dec=req_cagr_dec,
            universe_mode=u_mode,
            market_snapshot=snap,
            investment_amount=cap_amt,
            n_funds=n_funds,
        )

        # 前置校验锁定基金（兼容仅指数池自动剥离主动基 + 湖仓覆盖核验）
        if norm_include:
            meta_lookup = {str(r["fund_code"]): r.to_dict() for _, r in elite_meta.iterrows()} if elite_meta is not None else {}
            scanned_code_set = set(scanned_df["fund_code"].astype(str).tolist())
            for inc_c in norm_include:
                m_row = meta_lookup.get(inc_c)
                if m_row is None or inc_c not in elite_nav.columns:
                    constraint_warnings.append(f"锁定标的 {inc_c} 不在本地真净值湖仓中，已自动跳过该锁定约束。")
                    continue
                if u_mode == "index_only" and not is_index_style_fund(
                    str(m_row.get("fund_type", "")),
                    str(m_row.get("fund_name", "")),
                    str(m_row.get("bucket_10", "")),
                    operating_fee=float(m_row.get("est_total_operating_fee", 0.65) or 0.65),
                ):
                    constraint_warnings.append(
                        f"已切换至「低费指数核心池」，自动解除主动基金 {m_row.get('fund_name', inc_c)} ({inc_c}) 的锁定约束。"
                    )
                    continue
                if inc_c not in scanned_code_set:
                    constraint_warnings.append(
                        f"锁定标的 {m_row.get('fund_name', inc_c)} ({inc_c}) 历史深度或限购未达默认门禁，已放宽约束强制保留参与优化。"
                    )
                    s_col = elite_nav[inc_c].dropna()
                    if len(s_col) >= 120:
                        rets_i = s_col.pct_change().dropna()
                        ann_v = float(rets_i.std() * np.sqrt(252)) if len(rets_i) > 2 else 0.15
                        ann_r = float((s_col.iloc[-1] / max(float(s_col.iloc[0]), 1e-8)) ** (252.0 / len(s_col)) - 1.0)
                        cmax_i = s_col.cummax()
                        mdd_i = float(((s_col - cmax_i) / np.maximum(cmax_i, 1e-8)).min())
                        extra_row = dict(m_row)
                        extra_row.update({
                            "fund_code": inc_c,
                            "fund_name": str(m_row.get("fund_name", inc_c)),
                            "bucket": str(m_row.get("bucket_10", "broad_index")),
                            "bucket_10": str(m_row.get("bucket_10", "broad_index")),
                            "bucket_label": str(m_row.get("bucket_label", "核心配置")),
                            "asset_class": str(m_row.get("asset_class", "equity")),
                            "is_active_fund": bool(m_row.get("is_active_fund", False)),
                            "annual_return": ann_r,
                            "volatility": ann_v,
                            "sharpe": (ann_r - 0.02) / max(ann_v, 1e-4),
                            "max_dd": mdd_i,
                            "calmar": ann_r / max(abs(mdd_i), 0.02),
                            "win_rate": 0.5,
                            "conditional_win_rate": 0.5,
                            "unconditional_win_rate": 0.5,
                            "no_loss_rate": 0.65,
                            "valid_days": int(len(s_col)),
                            "quota_relaxed": True,
                            "_goal_rank": 99.0,
                        })
                        scanned_df = pd.concat([scanned_df, pd.DataFrame([extra_row])], ignore_index=True)
                    else:
                        continue
                eff_include.append(inc_c)

        # 应用黑名单排除（保障至少保留 n_funds 只可选标的防无解崩溃）
        if norm_exclude:
            filtered_df = scanned_df[~scanned_df["fund_code"].isin(norm_exclude)].copy()
            if len(filtered_df) >= n_funds:
                scanned_df = filtered_df
            else:
                constraint_warnings.append(
                    f"排除基金过多导致可用池不足 {n_funds} 只，系统已放宽部分排除约束以保障组合可行解。"
                )

        shortlisted_codes, sub_meta = _shortlist_goal_driven_candidates(
            scanned_df=scanned_df,
            nav_df=elite_nav,
            tier=tier,
            model_id=m_id,
            req_cagr_pct=req_cagr_pct,
            n_funds=n_funds,
            universe_mode=u_mode,
        )
        # 强制确保所有有效锁定标的都在 shortlisted_codes 与 sub_meta 中
        existing_sub_codes = set(sub_meta["fund_code"].astype(str).tolist())
        extra_inc_rows = []
        for inc_c in eff_include:
            if inc_c not in shortlisted_codes and inc_c in scanned_df["fund_code"].values:
                shortlisted_codes.insert(0, inc_c)
            if inc_c not in existing_sub_codes:
                m_sub = scanned_df[scanned_df["fund_code"] == inc_c].copy()
                if not m_sub.empty:
                    m_sub["_goal_rank"] = 99.0
                    extra_inc_rows.append(m_sub)
        if extra_inc_rows:
            sub_meta = pd.concat([sub_meta, *extra_inc_rows], ignore_index=True)

        # 防止个别晚成立基金过度截断共同区间，但严格保护短债/纯债/黄金/真海外每个关键防御桶最后 2 只代表不被清空
        min_common = max(1000, holding_days + 200)
        code_to_b10 = {str(r["fund_code"]): str(r.get("bucket_10", "")) for _, r in sub_meta.iterrows()}
        protected_buckets = {"short_bond", "pure_bond", "commodity_gold", "overseas_qdii"}
        cand_mat = elite_nav[shortlisted_codes].copy()
        while len(shortlisted_codes) > max(n_funds + 6, 16):
            common_len = len(cand_mat.dropna(how="any"))
            if common_len >= min_common:
                break
            b_counts: Dict[str, int] = {}
            for c in shortlisted_codes:
                b = code_to_b10.get(c, "")
                b_counts[b] = b_counts.get(b, 0) + 1
            removable = [
                c for c in shortlisted_codes
                if c not in eff_include
                and (code_to_b10.get(c, "") not in protected_buckets or b_counts.get(code_to_b10.get(c, ""), 0) > 2 or common_len < 420)
            ]
            if not removable:
                break
            youngest = max(removable, key=lambda c: cand_mat[c].first_valid_index() or pd.Timestamp("2099-01-01"))
            shortlisted_codes.remove(youngest)
            cand_mat = elite_nav[shortlisted_codes].copy()

        sub_nav_mat = cand_mat.dropna(how="any")
        sub_cand_df = sub_meta[sub_meta["fund_code"].isin(shortlisted_codes)].copy().reset_index(drop=True)
        sub_row_map: Dict[str, Dict[str, Any]] = {str(r["fund_code"]): r.to_dict() for _, r in sub_cand_df.iterrows()}

        if progress_cb:
            progress_cb(58, f"步骤 3/4：从 {len(shortlisted_codes)} 只入围真基金中运行【{solver_spec['algo_label']}】与严格 70/30 OOS 寻优...")

        # 真正调用 WinRateOptimizer.optimize()（严格在前 70% train_nav 上拟合，后 30% val_nav 零泄露盲测！）
        opt_primary = WinRateOptimizer(
            nav_matrix=sub_nav_mat,
            candidate_info=sub_cand_df,
            holding_days=holding_days,
            target_annual_return=req_cagr_dec,
            tier=tier,
            market_snapshot=snap,
            target_num_funds=n_funds,
            model_type=solver_spec["primary"],
        )
        opt_res_pri = opt_primary.optimize()
        strict_70_30_oos_pct = round(
            float((opt_res_pri.get("portfolio_metrics") or {}).get("oos_win_rate", 0.0)) * 100.0, 1
        )
        w_pri_raw = dict(opt_res_pri.get("optimal_weights") or {})
        selected_codes = [c for c in list(w_pri_raw.keys()) if c not in norm_exclude][:n_funds]

        # 强制合入全部有效锁定标的（优先替换权重最小的非锁定标的）
        for inc_c in eff_include:
            if inc_c not in selected_codes:
                if len(selected_codes) < n_funds:
                    selected_codes.append(inc_c)
                else:
                    non_locked = [c for c in selected_codes if c not in eff_include]
                    if non_locked:
                        drop_c = min(non_locked, key=lambda c: float(w_pri_raw.get(c, 0.0)))
                        selected_codes = [c for c in selected_codes if c != drop_c] + [inc_c]

        # 若极端约束导致只数不足 n_funds，按 _goal_rank 补齐多样化标的
        if len(selected_codes) < n_funds:
            for c in sub_cand_df.sort_values("_goal_rank", ascending=False)["fund_code"].tolist():
                if c not in selected_codes and c not in norm_exclude:
                    selected_codes.append(c)
                if len(selected_codes) >= n_funds:
                    break

        # ── 结构化分散与防抱团护栏（绝不替换用户锁定基金） ──
        def _row_of(code: str) -> Dict[str, Any]:
            return sub_row_map.get(code) or {}

        def _cluster_of(code: str) -> str:
            return classify_style_cluster(code, _row_of(code))

        # 护栏 1：C1/C2 优先保障至少 1 只中短债现金垫（对抗 1.59% 低利率久期反弹风险）
        if tier in ("C1", "C2") and len(selected_codes) >= 3:
            if not any(_row_of(c).get("bucket_10") == "short_bond" for c in selected_codes):
                sb_cands = [
                    c for c in sub_cand_df[sub_cand_df["bucket_10"] == "short_bond"].sort_values("_goal_rank", ascending=False)["fund_code"].tolist()
                    if c not in selected_codes and c not in norm_exclude
                ]
                if sb_cands:
                    # 优先替换多余的中长纯债，否则替换权重最低的非锁定基
                    dup_pb = [c for c in selected_codes if c not in eff_include and _row_of(c).get("bucket_10") == "pure_bond"]
                    pool_drop = dup_pb if dup_pb else [c for c in selected_codes if c not in eff_include]
                    if pool_drop:
                        drop_c = min(pool_drop, key=lambda c: float(w_pri_raw.get(c, 0.0)))
                        selected_codes = [c for c in selected_codes if c != drop_c] + [sb_cands[0]]

        # 护栏 2：C1~C3 保障至少 1 只债基压舱
        if tier in ("C1", "C2", "C3") and len(selected_codes) >= 3:
            if not any(_row_of(c).get("asset_class") == "bond" for c in selected_codes):
                bond_cands = [
                    c for c in sub_cand_df[sub_cand_df["asset_class"] == "bond"].sort_values("_goal_rank", ascending=False)["fund_code"].tolist()
                    if c not in norm_exclude and c not in selected_codes
                ]
                non_locked = [c for c in selected_codes if c not in eff_include]
                if bond_cands and non_locked:
                    min_c = min(non_locked, key=lambda c: float(w_pri_raw.get(c, 0.0)))
                    selected_codes = [c for c in selected_codes if c != min_c] + [bond_cands[0]]

        # 护栏 3：C3~C5 且 n_funds <= 6 时同质纯债（short_bond + pure_bond）最多占 1 席，释放槽位给真分散
        if tier in ("C3", "C4", "C5") and n_funds <= 6:
            pure_bonds = [c for c in selected_codes if _row_of(c).get("bucket_10") in ("short_bond", "pure_bond")]
            while len(pure_bonds) > 1:
                droppable = [c for c in pure_bonds if c not in eff_include]
                if not droppable:
                    break
                cur_clusters = {_cluster_of(c) for c in selected_codes}
                rep_cands = [
                    c for c in sub_cand_df[~sub_cand_df["bucket_10"].isin(["short_bond", "pure_bond"])].sort_values("_goal_rank", ascending=False)["fund_code"].tolist()
                    if c not in selected_codes and c not in norm_exclude and _cluster_of(c) not in cur_clusters
                ]
                if not rep_cands:
                    break
                drop_c = min(droppable, key=lambda c: float(w_pri_raw.get(c, 0.0)))
                selected_codes = [c for c in selected_codes if c != drop_c] + [rep_cands[0]]
                pure_bonds = [c for c in selected_codes if _row_of(c).get("bucket_10") in ("short_bond", "pure_bond")]

        # 护栏 4：C2~C5 最低权益只数保障
        min_eq_req = 3 if (tier in ("C4", "C5") and n_funds >= 5) else (2 if (tier in ("C2", "C3", "C4", "C5") and n_funds >= 4) else 1)
        cur_eq_codes = [c for c in selected_codes if _row_of(c).get("asset_class") == "equity"]
        if len(cur_eq_codes) < min_eq_req:
            eq_cands = [
                c for c in sub_cand_df[sub_cand_df["asset_class"] == "equity"].sort_values("_goal_rank", ascending=False)["fund_code"].tolist()
                if c not in selected_codes and c not in norm_exclude
            ]
            for eq_c in eq_cands:
                if len(cur_eq_codes) >= min_eq_req:
                    break
                non_eq = [c for c in selected_codes if _row_of(c).get("asset_class") != "equity" and c not in eff_include]
                if not non_eq:
                    break
                ac_cnts: Dict[str, int] = {}
                for c in non_eq:
                    a = str(_row_of(c).get("asset_class", ""))
                    ac_cnts[a] = ac_cnts.get(a, 0) + 1
                dup_non_eq = [c for c in non_eq if ac_cnts.get(str(_row_of(c).get("asset_class", "")), 0) >= 2]
                pool_drop = dup_non_eq if dup_non_eq else non_eq
                drop_c = min(pool_drop, key=lambda c: float(w_pri_raw.get(c, 0.0)))
                selected_codes = [c for c in selected_codes if c != drop_c] + [eq_c]
                cur_eq_codes.append(eq_c)

        # 护栏 5：全天候四资产真分散保底（C2~C4 且 n_funds >= 4：权益 + 债 + 纯黄金 + 真海外，海外停申时两级优雅降级）
        if m_id == "all_weather" and tier in ("C2", "C3", "C4") and n_funds >= 4:
            def _pick_replaceable_for_diversifier(keep_buckets: set) -> Optional[str]:
                cl_cnts: Dict[str, int] = {}
                for c in selected_codes:
                    cl = _cluster_of(c)
                    cl_cnts[cl] = cl_cnts.get(cl, 0) + 1
                eq_cnt_now = sum(1 for c in selected_codes if _row_of(c).get("asset_class") == "equity")
                bd_cnt_now = sum(1 for c in selected_codes if _row_of(c).get("asset_class") == "bond")
                candidates_drop = []
                for c in selected_codes:
                    if c in eff_include or _row_of(c).get("bucket_10") in keep_buckets:
                        continue
                    ac = _row_of(c).get("asset_class")
                    if ac == "bond" and bd_cnt_now <= 1:
                        continue
                    if ac == "equity" and eq_cnt_now <= min_eq_req:
                        continue
                    candidates_drop.append(c)
                if not candidates_drop:
                    return None
                # 优先替换同风格簇重复的基金
                dup_cl = [c for c in candidates_drop if cl_cnts.get(_cluster_of(c), 0) >= 2]
                pool = dup_cl if dup_cl else candidates_drop
                return min(pool, key=lambda c: float(w_pri_raw.get(c, 0.0)))

            # 5a. 纯黄金避险槽位
            if not any(_row_of(c).get("bucket_10") == "commodity_gold" for c in selected_codes):
                gold_cands = [
                    c for c in sub_cand_df[sub_cand_df["bucket_10"] == "commodity_gold"].sort_values("_goal_rank", ascending=False)["fund_code"].tolist()
                    if c not in selected_codes and c not in norm_exclude
                ]
                if gold_cands:
                    drop_c = _pick_replaceable_for_diversifier({"commodity_gold", "overseas_qdii"})
                    if drop_c:
                        selected_codes = [c for c in selected_codes if c != drop_c] + [gold_cands[0]]

            # 5b. 真海外 QDII 跨市场槽位（含两级优雅降级）
            if not any(_row_of(c).get("bucket_10") == "overseas_qdii" for c in selected_codes):
                qdii_cands = [
                    c for c in sub_cand_df[sub_cand_df["bucket_10"] == "overseas_qdii"].sort_values("_goal_rank", ascending=False)["fund_code"].tolist()
                    if c not in selected_codes and c not in norm_exclude
                ]
                if qdii_cands:
                    drop_c = _pick_replaceable_for_diversifier({"commodity_gold", "overseas_qdii"})
                    if drop_c:
                        selected_codes = [c for c in selected_codes if c != drop_c] + [qdii_cands[0]]
                else:
                    # 第 2 级优雅降级：当前选基池无开放申购的真海外 QDII，透明说明并优先由黄金/港股通/债承接
                    constraint_warnings.append(
                        "当前场外开放申购的纯海外 QDII 指数受外汇额度收紧普遍限购或暂停，全天候避险分散权重已自动平滑承接至不限购纯黄金、港股与债券底仓（绝不掺杂假海外标的）。"
                    )

        # 护栏 6：非债风格簇去抱团换基（同簇最多 2 只；gold/global_qdii/hk_offshore/other_commodity 最多 1 只）
        for _ in range(n_funds):
            cl_members: Dict[str, List[str]] = {}
            for c in selected_codes:
                cl = _cluster_of(c)
                if cl in ("short_bond", "pure_bond", "fixed_income_plus"):
                    continue
                cl_members.setdefault(cl, []).append(c)
            over_cl = None
            for cl, members in cl_members.items():
                max_m = 1 if (cl in ("gold", "global_qdii", "hk_offshore", "other_commodity") and n_funds <= 6) else 2
                if len(members) > max_m:
                    over_cl = (cl, members)
                    break
            if not over_cl:
                break
            cl_name, members = over_cl
            droppable = [c for c in members if c not in eff_include]
            if not droppable:
                break
            drop_c = min(droppable, key=lambda c: float(w_pri_raw.get(c, 0.0)))
            drop_ac = str(_row_of(drop_c).get("asset_class", "equity"))
            used_clusters = {_cluster_of(c) for c in selected_codes}
            # 寻找未出现过的风格簇中排名最高且不破坏权益底线的替代基金
            rep_pool = sub_cand_df.sort_values("_goal_rank", ascending=False)["fund_code"].tolist()
            rep_c = None
            for cand_c in rep_pool:
                if cand_c in selected_codes or cand_c in norm_exclude:
                    continue
                cand_cl = _cluster_of(cand_c)
                if cand_cl in used_clusters or cand_cl == cl_name:
                    continue
                if cand_cl in ("short_bond", "pure_bond") and tier in ("C3", "C4", "C5") and n_funds <= 6:
                    continue
                if drop_ac == "equity" and _row_of(cand_c).get("asset_class") != "equity":
                    continue
                rep_c = cand_c
                break
            if not rep_c:
                break
            selected_codes = [c for c in selected_codes if c != drop_c] + [rep_c]

        # 检查锁定基金与当前 C 档大类宪法红线的潜在张力，给出清晰量化提示
        if eff_include:
            inc_meta = sub_cand_df[sub_cand_df["fund_code"].isin(eff_include)]
            inc_eq_cnt = int((inc_meta["asset_class"] == "equity").sum())
            inc_qdii_cnt = int((inc_meta["asset_class"] == "qdii").sum())
            if tier in ("C1", "C2") and inc_eq_cnt >= 2:
                constraint_warnings.append(
                    f"在 {tier} 保守档位下锁定了 {inc_eq_cnt} 只权益基金，系统已严格按 {tier} 权益大类上限自动压低单只配权以守住回撤底线。"
                )
            if inc_qdii_cnt >= 2:
                constraint_warnings.append(
                    f"同时锁定了 {inc_qdii_cnt} 只海外 QDII 基金，系统已按 {tier} 海外上限平分其配置权重以防跨境汇率/溢价风险过度集中。"
                )

        # 在最终入选的 N 只真基金上运行双核权重融合（主核 + 目标条件胜率/CVaR/半凯利副核）
        sel_nav_mat = sub_nav_mat[selected_codes].dropna(how="any")
        sel_cand_df = sub_cand_df[sub_cand_df["fund_code"].isin(selected_codes)].copy().reset_index(drop=True)

        w_pri = opt_primary._optimize_by_model_type(selected_codes, sel_nav_mat, None) or {c: 1.0 / len(selected_codes) for c in selected_codes}
        opt_sec = WinRateOptimizer(
            nav_matrix=sel_nav_mat,
            candidate_info=sel_cand_df,
            holding_days=holding_days,
            target_annual_return=req_cagr_dec,
            tier=tier,
            market_snapshot=snap,
            target_num_funds=len(selected_codes),
            model_type=solver_spec["secondary"],
        )
        opt_sec._individual_metrics = sel_cand_df.copy()
        w_sec = opt_sec._optimize_by_model_type(selected_codes, sel_nav_mat, None) or w_pri

        sec_alpha = 0.40 if m_id in ("all_weather", "barbell_growth") else 0.30
        if req_cagr_pct >= 12.0:
            sec_alpha = min(0.50, sec_alpha + 0.08)
        blended_raw = {
            c: (1.0 - sec_alpha) * float(w_pri.get(c, 0.0)) + sec_alpha * float(w_sec.get(c, 0.0))
            for c in selected_codes
        }

        for _, mr in sel_cand_df.iterrows():
            meta_map[str(mr["fund_code"])] = mr.to_dict()

        min_floor = max(0.04, round(0.24 / max(len(selected_codes), 3), 3))
        guarded_solver = apply_asset_class_constitutional_limits(
            blended_raw, tier=tier, metrics_df=sel_cand_df, equity_tilt_pct=eq_tilt
        )
        solver_weights = _enforce_exact_fund_bounds(
            guarded_solver, selected_codes, meta_map=meta_map, tier=tier, min_floor=min_floor, model_id=m_id
        )

        l_funnel = lakehouse_status.get("funnel_stats") or {}
        funnel_audit = {
            "universe_mode": u_mode,
            "universe_label": "全市场含主动量化海选（主动+指增+债+QDII+黄金）" if u_mode == "full_market" else "低费指数核心池（宽基+红利+纯债/短债+黄金+海外）",
            "total_market_funds": int(l_funnel.get("total_market_funds", 28177)),
            "compliant_screened_funds": int(l_funnel.get("compliant_screened_funds", 12528)),
            "elite_lakehouse_funds": int(elite_nav.shape[1]),
            "eligible_depth_funds": int(len(scanned_df)),
            "shortlisted_candidates": int(len(shortlisted_codes)),
            "final_selected_funds": int(len(selected_codes)),
            "lakehouse_latest_date": str(lakehouse_status.get("latest_date", "")),
        }
        history_days_used = int(len(sel_nav_mat))
        history_range_str = f"{str(sel_nav_mat.index[0])[:10]} ~ {str(sel_nav_mat.index[-1])[:10]}"
        metrics_for_tilt = sel_cand_df
        ret_df_for_pcr = sel_nav_mat.pct_change().dropna()
        oos_nav_source = sel_nav_mat
    else:
        # 裸环境兜底（仅当本地尚未建湖仓时安全退回 12 只场外开放池）
        df_mat = StrategyBridge.load_matrix()
        dates = pd.to_datetime(df_mat["date"])
        n_d = len(df_mat)
        rng = np.random.RandomState(42)
        nav_d = {}
        cand_rows = []
        for item in _QUANT_OPTIMIZER_POOL:
            col = item["index_col"] if item["index_col"] in df_mat.columns else "H00300"
            s = df_mat[col].astype(float).ffill().bfill().to_numpy(dtype=np.float64)
            r = np.zeros(n_d, dtype=np.float64)
            r[1:] = s[1:] / np.maximum(s[:-1], 1e-8) - 1.0
            eps = rng.normal(0.0, 0.00012, size=n_d)
            eps[0] = 0.0
            nav_d[item["code"]] = np.cumprod(1.0 + r + eps)
            cand_rows.append({
                "fund_code": item["code"],
                "fund_name": item["name"],
                "bucket": item["bucket"],
                "bucket_10": item["bucket"],
                "bucket_label": item["bucket_label"],
                "asset_class": item["asset_class"],
                "is_active_fund": False,
                "is_index_eligible": True,
                "daily_limit_amount": 1e10,
                "purchase_status": "开放申购",
                "quota_relaxed": False,
            })
            meta_map[item["code"]] = cand_rows[-1]
        sub_nav_mat = pd.DataFrame(nav_d, index=dates)
        sub_cand_df = pd.DataFrame(cand_rows)
        selected_codes = [x["code"] for x in _QUANT_OPTIMIZER_POOL[:n_funds]]
        sel_nav_mat = sub_nav_mat[selected_codes]
        sel_cand_df = sub_cand_df[sub_cand_df["fund_code"].isin(selected_codes)].copy()
        opt_primary = WinRateOptimizer(
            nav_matrix=sel_nav_mat,
            candidate_info=sel_cand_df,
            holding_days=holding_days,
            target_annual_return=req_cagr_dec,
            tier=tier,
            market_snapshot=snap,
            target_num_funds=n_funds,
            model_type=solver_spec["primary"],
        )
        opt_res_fb = opt_primary.optimize()
        strict_70_30_oos_pct = round(
            float((opt_res_fb.get("portfolio_metrics") or {}).get("oos_win_rate", 0.0)) * 100.0, 1
        )
        w_pri = dict(opt_res_fb.get("optimal_weights") or {c: 1.0 / n_funds for c in selected_codes})
        min_floor = max(0.04, round(0.24 / max(n_funds, 3), 3))
        solver_weights = _enforce_exact_fund_bounds(
            apply_asset_class_constitutional_limits(w_pri, tier=tier, metrics_df=sel_cand_df, equity_tilt_pct=eq_tilt),
            selected_codes,
            meta_map=meta_map,
            tier=tier,
            min_floor=min_floor,
            model_id=m_id,
        )
        funnel_audit = {
            "universe_mode": u_mode,
            "universe_label": "兜底核心场外池（本地全市场净值湖仓待建库）",
            "total_market_funds": 28177,
            "compliant_screened_funds": 12,
            "elite_lakehouse_funds": 12,
            "eligible_depth_funds": 12,
            "shortlisted_candidates": 12,
            "final_selected_funds": n_funds,
            "lakehouse_latest_date": str(df_mat["date"].iloc[-1])[:10],
        }
        history_days_used = int(len(sel_nav_mat))
        history_range_str = f"{str(sel_nav_mat.index[0])[:10]} ~ {str(sel_nav_mat.index[-1])[:10]}"
        metrics_for_tilt = sel_cand_df
        ret_df_for_pcr = sel_nav_mat.pct_change().dropna()
        oos_nav_source = sel_nav_mat

    # 4. 仅对终选的 N 只基金拉取详情 10 维多因子打分并有界微调
    if progress_cb:
        progress_cb(80, f"步骤 4/4：融合终选 {len(selected_codes)} 只基金 10 维详情多因子、真实净值回测与多切点 Walk-Forward 盲测...")

    raw_final_weights, factor_profiles = score_and_tilt_weights_with_details(
        solver_weights,
        tier=tier,
        req_cagr=req_cagr_pct,
        metrics_df=metrics_for_tilt,
        equity_tilt_pct=eq_tilt,
    )
    min_floor = max(0.04, round(0.24 / max(len(selected_codes), 3), 3))
    final_weights = _enforce_exact_fund_bounds(
        raw_final_weights, selected_codes, meta_map=meta_map, tier=tier, min_floor=min_floor, model_id=m_id
    )

    # 拟投金额限购拆单明文提示（凡单日限额需要 > 10 个交易日买完或触发放宽者，清晰提示分批日定投天数）
    for c, w_f in final_weights.items():
        m_i = meta_map.get(c) or {}
        lim = float(m_i.get("daily_limit_amount", 1e10) or 1e10)
        alloc_amt = cap_amt * float(w_f)
        if lim < 1e8 and lim > 0 and (alloc_amt / lim > 10.0 or bool(m_i.get("quota_relaxed", False))):
            days_need = max(1, int(math.ceil(alloc_amt / lim)))
            fn_c = str(m_i.get("fund_name") or c)
            constraint_warnings.append(
                f"限购拆单提示：「{fn_c} ({c})」单日限购 ¥{lim:,.0f}，按拟投 ¥{cap_amt:,.0f} 配比（约 ¥{alloc_amt:,.0f}）需分约 {days_need} 个交易日日定投买入，建议开启分批定投或酌情微调单基占比。"
            )

    # 5. 真实协方差 PCR 风险贡献度分解（sum == 100.0%）
    pcr_info = calculate_portfolio_risk_contributions(final_weights, returns_df=ret_df_for_pcr)
    pcr_map = pcr_info.get("pcr", {})

    # 6. 100% 真实复权净值组合回测 + 双万次蒙特卡洛目标达成评估
    real_bt_df, proxy_early_df, real_bt_info = build_real_nav_portfolio_backtest(
        fund_weights=final_weights,
        elite_nav=elite_nav if use_full_lakehouse else None,
        meta_map=meta_map,
        tier=tier,
        target_return_pct=req_cagr_pct,
    )
    goal_eval = evaluate_goal_achievement(
        final_weights,
        target_return_pct=t_ret,
        horizon_months=h_mon,
        tier=tier,
        market_snapshot=snap,
        df_bt_override=real_bt_df,
    )

    # 真实严格 70/30 盲测 OOS + 多切点时间截断 Walk-Forward 校验（彻底消灭事后切尾 30% 的伪 OOS！）
    walk_forward_audit = _evaluate_true_walk_forward_oos(
        nav_df=elite_nav if use_full_lakehouse else sub_nav_mat,
        meta_df=elite_meta if use_full_lakehouse else sub_cand_df,
        tier=tier,
        model_id=m_id,
        n_funds=n_funds,
        holding_days=holding_days,
        req_cagr_dec=req_cagr_dec,
        universe_mode=u_mode,
        strict_70_30_pct=strict_70_30_oos_pct,
    )
    oos_winrate_pct = round(float(strict_70_30_oos_pct), 1)

    # 7. 构建每只入选基金透明配权归因与白话介绍
    allocation_breakdown: Dict[str, Dict[str, Any]] = {}
    fund_cards_meta: Dict[str, Dict[str, Any]] = {}
    for c, final_w in final_weights.items():
        base_w = float(solver_weights.get(c, final_w))
        delta_pct = round((final_w - base_w) * 100.0, 2)
        pcr_pct = round(float(pcr_map.get(c, final_w * 100.0)), 1)
        fp = factor_profiles.get(c) or {}
        m_info = meta_map.get(c) or _POOL_BY_CODE.get(c) or {}
        role_txt, plain_why = _build_dynamic_fund_plain_why(c, m_info, fp)
        fund_cards_meta[c] = {
            "fund_name": str(m_info.get("fund_name") or m_info.get("name") or c),
            "role": role_txt,
            "why": plain_why,
            "bucket_10": str(m_info.get("bucket_10") or m_info.get("bucket") or ""),
            "bucket_label": str(m_info.get("bucket_label") or role_txt),
            "style_cluster": classify_style_cluster(c, m_info),
            "asset_class": str(m_info.get("asset_class") or "equity"),
            "is_active_fund": bool(m_info.get("is_active_fund", False)),
            "real_scale_yi": _safe_float(m_info.get("real_scale_yi"), 0.0) or _safe_float(fp.get("scale_yi"), 0.0) or None,
            "max_star": _safe_float(m_info.get("max_star"), 0.0),
            "daily_limit": _safe_float(m_info.get("daily_limit_amount"), 1e10),
            "purchase_status": str(m_info.get("purchase_status") or "开放申购"),
            "est_total_operating_fee": _safe_float(m_info.get("est_total_operating_fee"), 0.0) or _safe_float(fp.get("total_fee_pct"), 0.6),
            "quota_relaxed": bool(m_info.get("quota_relaxed", False)),
            "inception_date": str(m_info.get("inception_date", ""))[:10],
        }
        tilt_desc = (
            f"多因子高分({fp.get('quant_score', 65)}分)上调 {delta_pct:+.1f}%"
            if delta_pct > 0.15
            else (
                f"多因子相对偏弱({fp.get('quant_score', 65)}分)微调 {delta_pct:+.1f}%"
                if delta_pct < -0.15
                else f"多因子({fp.get('quant_score', 65)}分)校验维持均衡"
            )
        )
        allocation_breakdown[c] = {
            "fund_code": c,
            "bucket": str(m_info.get("bucket_label") or "核心配置"),
            "solver_weight_pct": round(base_w * 100.0, 1),
            "factor_tilt_delta_pct": round(delta_pct, 1),
            "final_weight_pct": round(final_w * 100.0, 1),
            "risk_contribution_pcr_pct": pcr_pct,
            "tilt_reason": tilt_desc,
            "allocation_formula_text": (
                f"量化求解初始权重 {base_w * 100.0:.1f}% → {tilt_desc} → 最终占比 {final_w * 100.0:.1f}%"
                f"（组合风险贡献 PCR {pcr_pct:.1f}%）"
            ),
        }

    class_weights: Dict[str, float] = {}
    for c, w in final_weights.items():
        b_lbl = fund_cards_meta[c]["bucket_label"]
        class_weights[b_lbl] = round(class_weights.get(b_lbl, 0.0) + w * 100.0, 1)

    regime_rec = recommend_model_for_regime(snap, req_cagr_pct)
    elapsed_ms = int(round((time.monotonic() - t0) * 1000.0))

    solver_audit = {
        "engine_version": "AGY2-FullMarketQuant-v2.2.0",
        "universe_mode": u_mode,
        "lakehouse_enabled": bool(use_full_lakehouse),
        "solver_algorithm": solver_spec["algo_label"],
        "math_summary": solver_spec["math_summary"],
        "candidates_screened": funnel_audit["shortlisted_candidates"],
        "history_trading_days": history_days_used,
        "history_range": history_range_str,
        "real_nav_common_start": real_bt_info.get("common_start_date", ""),
        "is_real_nav_backtest": bool(real_bt_info.get("is_real_nav", False)),
        "holding_days": holding_days,
        "target_annual_return_pct": req_cagr_pct,
        "tier_max_drawdown_cap_pct": round(MAX_DRAWDOWN_BY_TIER.get(tier, 0.18) * 100.0, 1),
        "ten_dim_equity_tilt_pct": round(eq_tilt * 100.0, 1),
        "oos_method": "strict_70_30_and_walk_forward",
        "oos_conditional_win_rate_pct": oos_winrate_pct,
        "wf_oos_positive_rate_pct": walk_forward_audit.get("wf_oos_positive_rate_pct", 0.0),
        "wf_avg_return_pct": walk_forward_audit.get("wf_avg_return_pct", 0.0),
        "wf_worst_mdd_pct": walk_forward_audit.get("wf_worst_mdd_pct", 0.0),
        "survivorship_bias_disclaimer": SURVIVORSHIP_BIAS_DISCLAIMER,
        "monte_carlo_paths": 10000,
        "monte_carlo_prob_pct": goal_eval.get("monte_carlo_prob_pct", 0.0),
        "portfolio_vol_annual_pct": pcr_info.get("portfolio_vol_annual", 0.0),
        "max_risk_pcr_pct": pcr_info.get("max_risk_pcr", 0.0),
        "risk_budget_verdict": pcr_info.get("risk_budget_warning", ""),
        "regime_detected": regime_rec.get("regime_name", ""),
        "regime_recommended_model": regime_rec.get("recommended_model_name", ""),
        "compute_ms": elapsed_ms,
        "from_cache": False,
        "exclude_count": len(norm_exclude),
        "include_count": len(eff_include),
        "investment_amount": cap_amt,
    }

    constraint_audit = {
        "exclude_codes": norm_exclude,
        "include_codes": eff_include,
        "requested_include_codes": norm_include,
        "warnings": constraint_warnings,
    }

    allocation_logic_summary = {
        "headline": (
            f"从全市场 {funnel_audit['total_market_funds']:,} 只基金经场外合规/零锁定期/限购漏斗与 {funnel_audit['elite_lakehouse_funds']} 只真实复权净值湖仓海选，"
            f"在 {tier} 回撤约束（≤{solver_audit['tier_max_drawdown_cap_pct']:.0f}%）与「{h_mon} 个月 +{t_ret:.0f}%」目标下，"
            f"通过【{solver_spec['algo_label']}】与严格 70/30 样本外盲测从 {funnel_audit['shortlisted_candidates']} 只去冗余候选中精选出 {len(final_weights)} 只最优组合。"
        ),
        "steps": [
            f"① 全市场场外漏斗：{funnel_audit['total_market_funds']:,} 只全市场 → 剔除场内 ETF、锁定期与暂停申购 → {funnel_audit['elite_lakehouse_funds']} 只本地真实复权净值湖仓（{funnel_audit['universe_label']}）。",
            f"② 拟投限购过滤与去冗余：按拟投 ¥{cap_amt:,.0f} 核验单日申购上限，剔除相关性 >0.82 同质标的，动态锁定 {funnel_audit['shortlisted_candidates']} 只高匹配候选。",
            f"③ 严格 70/30 OOS 与多切点 Walk-Forward 盲测：{solver_spec['math_summary']}（严格 70/30 OOS 胜率 {oos_winrate_pct:.1f}%，Walk-Forward 正收益比例 {walk_forward_audit.get('wf_oos_positive_rate_pct', 0.0):.0f}%）。",
            f"④ 风格防抱团与多因子微调：硬控单风格簇不过度集中并结合 10 维详情指标在 ±10% 内微调，组合年化波动 {pcr_info.get('portfolio_vol_annual', 0.0):.1f}%，单基最大风险贡献 PCR {pcr_info.get('max_risk_pcr', 0.0):.1f}%（总和 100.0%）。",
        ],
        "class_weights_pct": class_weights,
    }

    if progress_cb:
        progress_cb(100, "全市场量化求解完成")

    result = {
        "tier": tier,
        "model_id": m_id,
        "universe_mode": u_mode,
        "fund_count": len(final_weights),
        "target_return_pct": t_ret,
        "horizon_months": h_mon,
        "required_cagr_pct": req_cagr_pct,
        "solver_weights": solver_weights,
        "final_weights": final_weights,
        "factor_profiles": factor_profiles,
        "fund_cards_meta": fund_cards_meta,
        "allocation_breakdown": allocation_breakdown,
        "allocation_logic_summary": allocation_logic_summary,
        "funnel_audit": funnel_audit,
        "pcr_info": pcr_info,
        "goal_analysis": goal_eval,
        "solver_audit": solver_audit,
        "walk_forward_audit": walk_forward_audit,
        "constraint_audit": constraint_audit,
        "real_bt_df": real_bt_df,
        "proxy_early_df": proxy_early_df,
        "real_bt_info": real_bt_info,
    }

    with _SOLVER_CACHE_LOCK:
        _SOLVER_CACHE[cache_key] = (time.time(), result)
    return result


def evaluate_goal_achievement(
    fund_weights: Dict[str, float],
    target_return_pct: float,
    horizon_months: int,
    tier: str = "C3",
    market_snapshot: Optional[Dict[str, Any]] = None,
    df_bt_override: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    在真实复权历史净值序列上执行三维达标检验：
      1. 区间任意日触及目标止盈率 + 持有期末滚动达标统计；
      2. 5 维宏观同温层高斯核条件胜率（含真实申赎费率摩擦，来自 WinRateEngine）；
      3. 10,000 次 Circular Block Bootstrap + Student-t 蒙特卡洛前瞻达标概率。
    """
    t_ret = float(target_return_pct)
    h_mon = max(3, min(60, int(horizon_months or 12)))
    req_cagr = round((((1.0 + t_ret / 100.0) ** (12.0 / h_mon)) - 1.0) * 100.0, 2) if t_ret > -90 else 0.0
    suggested_tier = map_target_return_to_tier(max(0.0, req_cagr))
    tier_clean = str(tier or "C3").upper().strip()
    if tier_clean not in _TIER_ORDER:
        tier_clean = "C3"

    has_collision = _TIER_ORDER[suggested_tier] > _TIER_ORDER[tier_clean]
    max_realistic = _TIER_MAX_REALISTIC_CAGR[tier_clean]
    if has_collision:
        collision_msg = (
            f"目标冲突提醒：在 {h_mon} 个月内赚取 +{t_ret:.1f}% 折合年化 +{req_cagr:.1f}%，"
            f"超出 {tier_clean} 档位常规年化能力区间（约 ≤{max_realistic:.1f}%），"
            f"通常需要 {suggested_tier} 档位风险承受力，或建议将持有周期拉长 / 目标适当下调。"
        )
    else:
        collision_msg = (
            f"目标与风险匹配：在 {h_mon} 个月内目标收益 +{t_ret:.1f}%（折合年化 +{req_cagr:.1f}%），"
            f"与当前 {tier_clean} 风险承受力相容。"
        )

    hit_rate_pct = 0.0
    end_hit_rate_pct = 0.0
    cond_wr_pct = 0.0
    mc_prob_pct = 0.0
    no_loss_rate_pct = 0.0
    median_ret_pct = 0.0
    worst_ret_pct = 0.0
    best_ret_pct = 0.0
    avg_reach_months: Optional[float] = None
    windows_tested = 0

    try:
        snap = market_snapshot if market_snapshot is not None else StrategyBridge.get_latest_market_snapshot(force_reload=False)
        df_bt = df_bt_override if (df_bt_override is not None and not df_bt_override.empty) else StrategyBridge.build_custom_portfolio_backtest(
            fund_weights=fund_weights,
            secondary_weights=None,
            tier=tier_clean,
            target_return_pct=max(3.0, min(30.0, req_cagr)),
        )
        if df_bt is not None and not df_bt.empty:
            col = "strategy_nav_otc" if "strategy_nav_otc" in df_bt.columns else "strategy_nav"
            nav_series = df_bt[col].astype(float).ffill().bfill()
            navs = nav_series.values
            win_days = max(21, int(round(h_mon * 21)))
            if len(navs) > win_days + 5:
                step = 5
                rets = []
                touch_hits = 0
                end_hits = 0
                reach_days_list = []
                target_ratio = 1.0 + t_ret / 100.0
                for i in range(0, len(navs) - win_days, step):
                    base = navs[i]
                    if base <= 0:
                        continue
                    seg = navs[i : i + win_days + 1] / base
                    end_r = (seg[-1] - 1.0) * 100.0
                    rets.append(end_r)
                    if seg[-1] >= target_ratio:
                        end_hits += 1
                    reached_idx = np.where(seg >= target_ratio)[0]
                    if len(reached_idx) > 0:
                        touch_hits += 1
                        reach_days_list.append(int(reached_idx[0]))
                if rets:
                    windows_tested = len(rets)
                    hit_rate_pct = round(touch_hits / windows_tested * 100.0, 1)
                    end_hit_rate_pct = round(end_hits / windows_tested * 100.0, 1)
                    median_ret_pct = round(float(np.median(rets)), 2)
                    worst_ret_pct = round(float(np.percentile(rets, 5)), 2)
                    best_ret_pct = round(float(np.percentile(rets, 95)), 2)
                    if reach_days_list:
                        avg_reach_months = round(float(np.mean(reach_days_list)) / 21.0, 1)

                wr_kernel = WinRateEngine.rolling_target_winrate(
                    nav_series,
                    holding_days=win_days,
                    target_annual_return=req_cagr / 100.0,
                    include_friction=True,
                    market_snapshot=snap,
                )
                cond_wr_pct = round(float(wr_kernel.get("conditional_win_rate", 0.0)) * 100.0, 1)
                no_loss_rate_pct = round(float(wr_kernel.get("no_loss_rate", 0.0)) * 100.0, 1)

                mc_res = WinRateEngine.monte_carlo_winrate(
                    nav_series,
                    holding_days=win_days,
                    target_annual_return=req_cagr / 100.0,
                    n_paths=10000,
                    block_size=10,
                    include_friction=True,
                    seed=42,
                )
                mc_prob_pct = round(float(mc_res.get("prob_reach_target", 0.0)) * 100.0, 1)
    except Exception:
        pass

    eff_prob = 0.45 * hit_rate_pct + 0.30 * cond_wr_pct + 0.25 * mc_prob_pct if mc_prob_pct > 0 else hit_rate_pct
    if eff_prob >= 68.0 and not has_collision:
        feasibility = "高可行性"
        feasibility_level = "high"
    elif eff_prob >= 42.0:
        feasibility = "中等可行性"
        feasibility_level = "medium"
    else:
        feasibility = "偏激进 / 建议调参"
        feasibility_level = "low"

    if req_cagr <= 6.0:
        rec_model = "risk_parity"
    elif req_cagr <= 9.5:
        rec_model = "dividend_defense"
    elif req_cagr <= 14.0:
        rec_model = "all_weather"
    else:
        rec_model = "barbell_growth"

    return {
        "target_return_pct": round(t_ret, 1),
        "horizon_months": h_mon,
        "required_cagr_pct": req_cagr,
        "current_tier": tier_clean,
        "suggested_tier": suggested_tier,
        "has_collision": has_collision,
        "collision_message": collision_msg,
        "recommended_model": rec_model,
        "feasibility": feasibility,
        "feasibility_level": feasibility_level,
        "historical_hit_rate_pct": hit_rate_pct,
        "end_of_period_hit_rate_pct": end_hit_rate_pct,
        "conditional_win_rate_pct": cond_wr_pct,
        "monte_carlo_prob_pct": mc_prob_pct,
        "no_loss_rate_pct": no_loss_rate_pct,
        "windows_tested": windows_tested,
        "median_return_pct": median_ret_pct,
        "p05_worst_return_pct": worst_ret_pct,
        "p95_best_return_pct": best_ret_pct,
        "avg_reach_months": avg_reach_months,
    }


def reconcile_goal_vs_backtest(
    goal_analysis: Dict[str, Any],
    backtest_metrics: Dict[str, Any],
    period_key: str,
    period_label: str,
    tier: str,
    model_name: str,
    solver_audit: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """显式对比「用户目标收益」vs「当前回测窗口实际表现」，量化差异并动态输出 3 条真实数据理由。"""
    t_ret = float(goal_analysis.get("target_return_pct", 10.0))
    h_mon = int(goal_analysis.get("horizon_months", 12))
    req_cagr = float(goal_analysis.get("required_cagr_pct", t_ret))
    cond_wr = float(goal_analysis.get("conditional_win_rate_pct", 0.0))
    hit_rate = float(goal_analysis.get("historical_hit_rate_pct", 0.0))
    mc_prob = float(goal_analysis.get("monte_carlo_prob_pct", 0.0))
    no_loss = float(goal_analysis.get("no_loss_rate_pct", 0.0))
    med_ret = float(goal_analysis.get("median_return_pct", 0.0))
    windows = int(goal_analysis.get("windows_tested", 0))
    suggested_tier = str(goal_analysis.get("suggested_tier", tier))

    bt_ret = float(backtest_metrics.get("period_return_pct", 0.0))
    bt_ann = backtest_metrics.get("annualized_return_pct")
    h300_ret = float(backtest_metrics.get("hs300_return_pct", 0.0))
    excess_ret = float(backtest_metrics.get("excess_return_pct", 0.0))
    mdd = abs(float(backtest_metrics.get("max_drawdown_pct", 0.0)))
    h300_mdd = abs(float(backtest_metrics.get("hs300_mdd_pct", 0.0)))
    sharpe = float(backtest_metrics.get("sharpe_ratio", 0.0))
    tdays = int(backtest_metrics.get("trading_days", 252))
    saved_dd = round(max(0.0, h300_mdd - mdd), 2)
    tier_cap = float((solver_audit or {}).get("tier_max_drawdown_cap_pct", MAX_DRAWDOWN_BY_TIER.get(tier, 0.18) * 100.0))

    period_months_map = {"3m": 3.0, "6m": 6.0, "1y": 12.0, "2y": 24.0, "all": max(tdays / 21.0, 24.0)}
    p_mon = period_months_map.get(period_key, 12.0)

    if bt_ann is not None and period_key in ("1y", "2y", "all"):
        comparable_bt = float(bt_ann)
        comparable_goal = req_cagr
        compare_metric_label = "折合年化收益"
    else:
        comparable_bt = bt_ret
        comparable_goal = round((((1.0 + req_cagr / 100.0) ** (p_mon / 12.0)) - 1.0) * 100.0, 2)
        compare_metric_label = f"{period_label}进度目标"

    gap_pct = round(comparable_bt - comparable_goal, 2)

    if abs(gap_pct) <= 2.5:
        status = "aligned"
        badge = "基本吻合"
        headline = (
            f"当前方案在「{period_label}」{compare_metric_label}为 {comparable_bt:+.2f}%，"
            f"与您的目标口径（{comparable_goal:+.2f}%）偏差仅 {gap_pct:+.2f}%，处于高度一致区间。"
        )
    elif gap_pct < -2.5:
        status = "backtest_below_goal"
        badge = "回测低于目标 · 已归因"
        headline = (
            f"「{period_label}」实测 {compare_metric_label}（{comparable_bt:+.2f}%）低于您的目标口径（{comparable_goal:+.2f}%），"
            f"存在 {gap_pct:+.2f}% 出入——但这并非模型失效，而是风控红线与单一窗口周期波动的必然权衡。"
        )
    else:
        status = "backtest_above_goal"
        badge = "回测高于目标 · 提示均值回归"
        headline = (
            f"「{period_label}」实测 {compare_metric_label}（{comparable_bt:+.2f}%）高于您的目标口径（{comparable_goal:+.2f}%）达 {gap_pct:+.2f}%，"
            f"说明该阶段顺风弹性充分，但请勿将单段顺风业绩线性外推，保持目标止盈纪律更重要。"
        )

    reasons: List[Dict[str, str]] = []
    if period_key in ("3m", "6m") or abs(p_mon - h_mon) >= 6:
        reasons.append({
            "title": "统计窗口与目标持有期错位",
            "detail": (
                f"当前回测切片仅展示「{period_label}」（{tdays} 交易日，同期沪深 300 为 {h300_ret:+.2f}%），"
                f"而您设定的是「{h_mon} 个月 +{t_ret:.1f}%」的跨阶段目标。单一短期窗口受市场情绪脉冲影响极大，"
                f"不能等同于真实历史 {windows} 个滚动起点的整体分布（中位收益 {med_ret:+.2f}%）。"
            ),
        })
    else:
        reasons.append({
            "title": "单一历史切片 vs 全周期滚动概率分布",
            "detail": (
                f"「{period_label}」仅代表截至今日的一条历史路径（同期沪深 300 为 {h300_ret:+.2f}%，本方案超额 {excess_ret:+.2f}%）；"
                f"而全市场优化器面向的是 {windows} 个真实历史滚动起点与 10,000 条蒙特卡洛路径的综合达标胜率。"
            ),
        })

    if gap_pct < -2.5:
        reasons.append({
            "title": f"{tier} 档位回撤红线硬约束优先于“纸面收益”",
            "detail": (
                f"求解器严格执行 {tier} 档位最大回撤警戒线（≤{tier_cap:.0f}%）与大类宪法配比，拒绝通过单押高波动赛道去硬凑短期收益。"
                f"实测该区间组合最大回撤仅 -{mdd:.2f}%（较沪深 300 的 -{h300_mdd:.2f}% 少跌 {saved_dd:.2f} 个百分点），"
                f"用适度让渡极端单边弹性换取“跌得浅、拿得住”。"
            ),
        })
    else:
        reasons.append({
            "title": "风险调整性价比与抗跌护城河并重",
            "detail": (
                f"在取得 {bt_ret:+.2f}% 真实净值区间收益的同时，组合最大回撤被控制在 -{mdd:.2f}%（较沪深 300 少跌 {saved_dd:.2f} 个百分点），"
                f"夏普比率达 {sharpe:.2f}，证明收益来源于跨品类风险分散与优中选优，而非单押单一风口。"
            ),
        })

    why_still_recommend = (
        f"① 全市场跨周期胜率最优解：在 {tier} 风险约束内，【{model_name}】从全市场真实净值湖仓优化换基后，真实滚动 {h_mon} 个月触达目标率达 {hit_rate:.1f}%、"
        f"当下宏观同温层条件胜率 {cond_wr:.1f}%、10,000 次蒙特卡洛前瞻达标概率 {mc_prob:.1f}%、正收益概率 {no_loss:.1f}%；"
        f"② 避免过拟合后视镜：如果强行按“最近 {period_label} 涨得最好的基金”倒推配置，极易高位追进上一阶段热门赛道，反而大幅拉低未来 {h_mon} 个月真实胜率。"
    )
    if gap_pct < -2.5 and _TIER_ORDER.get(suggested_tier, 3) > _TIER_ORDER.get(tier, 3):
        why_still_recommend += (
            f" 若您希望进一步向年化 +{req_cagr:.1f}% 靠拢，建议将持有周期拉长至 {min(36, h_mon + 12)} 个月，"
            f"或在能承受更大波动的前提下将风险档位上调至 {suggested_tier}。"
        )
    elif gap_pct < -2.5:
        why_still_recommend += (
            f" 若您希望进一步提升达成年化 +{req_cagr:.1f}% 的胜率，建议将持有周期拉长至 {min(36, h_mon + 12)} 个月，"
            f"以时间换取跨周期均值回归空间。"
        )
    reasons.append({
        "title": "为何存在出入仍建议坚持本配置",
        "detail": why_still_recommend,
    })

    return {
        "status": status,
        "badge": badge,
        "headline": headline,
        "compare_metric_label": compare_metric_label,
        "goal_comparable_pct": round(comparable_goal, 2),
        "backtest_comparable_pct": round(comparable_bt, 2),
        "gap_pct": gap_pct,
        "goal_target_return_pct": round(t_ret, 1),
        "goal_horizon_months": h_mon,
        "goal_required_cagr_pct": round(req_cagr, 2),
        "backtest_period_label": period_label,
        "backtest_period_return_pct": round(bt_ret, 2),
        "reasons": reasons,
        "why_still_recommend": why_still_recommend,
    }


def simulate_portfolio_scenario_backtest(
    solved_bundle: Dict[str, Any],
    start_date: str = "2024-09-18",
    dynamic_rebalance: bool = True,
) -> Dict[str, Any]:
    """
    与当前全市场求解方案 100% 联动的历史任意起点情景回测引擎（严格零未来函数 + 真实全扣费）：
      - 当所选起点 >= 组合共同成立日时，100% 在本地精英湖仓的入选基金自身真实复权净值上逐日重演
        （支持按月检查 3% 偏离阈值执行真实漂移再平衡 vs 买入持有不调仓，扣除前端申购费与 FIFO 阶梯赎回费）；
      - 当所选起点早于部分入选基金成立日（如 2021-02-18）时，早期段透明衔接同风格桶基准参考序列，
        到达共同成立日后无缝切换为 100% 基金真实复权净值，并显式返回 used_proxy_early=True 与 proxy_note。
    """
    clean_date = str(start_date or "2024-09-18").strip()[:10]
    dt_target = pd.to_datetime(clean_date)

    final_weights: Dict[str, float] = dict(solved_bundle.get("final_weights") or {})
    real_bt_df: Optional[pd.DataFrame] = solved_bundle.get("real_bt_df")
    proxy_early_df: Optional[pd.DataFrame] = solved_bundle.get("proxy_early_df")
    real_bt_info: Dict[str, Any] = dict(solved_bundle.get("real_bt_info") or {})
    common_start_str = str(real_bt_info.get("common_start_date") or "")

    df_mat = StrategyBridge.load_matrix().copy()
    df_mat["dt"] = pd.to_datetime(df_mat["date"]).dt.normalize()
    df_mat_idx = df_mat.set_index("dt")

    elite_nav, _, _ = load_elite_lakehouse()
    valid_codes = [
        c for c, w in final_weights.items()
        if float(w) > 1e-6 and elite_nav is not None and c in elite_nav.columns
    ]

    used_proxy_early = False
    proxy_note = ""

    sub_fee_rate = 0.0012  # A 类 1 折申购费 12 bps
    cash_ret_daily = 0.018 / 250.0
    rebal_fee_extra = 0.0020 / 250.0

    # 情形 1：起点落入入选基金共同真实复权净值区间内 -> 100% 真实单基复权净值逐日模拟（含漂移/月频再平衡）
    if (
        valid_codes
        and len(valid_codes) == len([c for c, w in final_weights.items() if float(w) > 1e-6])
        and common_start_str
        and clean_date >= common_start_str
    ):
        sub_nav = elite_nav[valid_codes].dropna(how="any")
        sub_nav = sub_nav[sub_nav.index >= dt_target]
        if len(sub_nav) >= 2:
            tot_w = sum(float(final_weights[c]) for c in valid_codes) or 1.0
            tgt_w = np.array([float(final_weights[c]) / tot_w for c in valid_codes], dtype=np.float64)
            arr_nav = sub_nav.to_numpy(dtype=np.float64)
            n_fwd = len(arr_nav)
            fwd_dates_idx = sub_nav.index
            fwd_dates = [d.strftime("%Y-%m-%d") for d in fwd_dates_idx]

            init_nav = 1.0 * (1.0 - sub_fee_rate)
            # 95% 权益/基金实盘仓位 + 5% 现金缓冲
            fund_vals = init_nav * 0.95 * tgt_w
            cash_val = init_nav * 0.05
            daily_navs = [init_nav]

            for t in range(1, n_fwd):
                step_ratio = arr_nav[t] / np.maximum(arr_nav[t - 1], 1e-8)
                fund_vals = fund_vals * step_ratio
                cash_val = cash_val * (1.0 + cash_ret_daily)
                tot_v = float(np.sum(fund_vals) + cash_val)

                if dynamic_rebalance and (t % 20 == 0) and tot_v > 0:
                    cur_w = fund_vals / max(float(np.sum(fund_vals)), 1e-8)
                    max_drift = float(np.max(np.abs(cur_w - tgt_w)))
                    if max_drift > 0.03:
                        turnover = float(np.sum(np.abs(cur_w - tgt_w))) / 2.0
                        cal_days = (fwd_dates_idx[t] - fwd_dates_idx[0]).days
                        red_rate = 0.0050 if cal_days < 180 else (0.0015 if cal_days < 365 else 0.0)
                        friction = turnover * (0.5 * red_rate + sub_fee_rate)
                        tot_v *= (1.0 - friction)
                        fund_vals = tot_v * 0.95 * tgt_w
                        cash_val = tot_v * 0.05

                daily_navs.append(tot_v)

            curve_series = pd.Series(daily_navs, index=fwd_dates_idx)
        else:
            curve_series = None
    else:
        curve_series = None

    # 情形 2：起点早于共同成立日（或无完整湖仓切片），拼接 proxy_early_df + real_bt_df，明文标注
    if curve_series is None:
        if real_bt_df is None or real_bt_df.empty:
            return {"status": "empty", "dates": [], "kpis": {}}

        col_r = "strategy_nav_otc" if "strategy_nav_otc" in real_bt_df.columns else "strategy_nav"
        s_real = pd.Series(
            real_bt_df[col_r].astype(float).to_numpy(dtype=np.float64),
            index=pd.to_datetime(real_bt_df["date"]).dt.normalize(),
        )

        if proxy_early_df is not None and not proxy_early_df.empty and str(proxy_early_df["date"].iloc[0])[:10] <= clean_date:
            col_p = "strategy_nav_otc" if "strategy_nav_otc" in proxy_early_df.columns else "strategy_nav"
            s_proxy = pd.Series(
                proxy_early_df[col_p].astype(float).to_numpy(dtype=np.float64),
                index=pd.to_datetime(proxy_early_df["date"]).dt.normalize(),
            )
            real_first_dt = s_real.index[0]
            if dt_target < real_first_dt:
                early_part = s_proxy[(s_proxy.index >= dt_target) & (s_proxy.index < real_first_dt)]
                if len(early_part) >= 1:
                    early_rets = early_part.pct_change().fillna(0.0)
                    real_rets = s_real.pct_change().fillna(0.0)
                    # 衔接点收益率按同风格指数当日涨跌过渡，避免跳变
                    comb_rets = pd.concat([early_rets, real_rets])
                    comb_rets = comb_rets[~comb_rets.index.duplicated(keep="last")].sort_index()
                    comb_rets.iloc[0] = 0.0
                    adj_rets = comb_rets.to_numpy(dtype=np.float64)
                    if not dynamic_rebalance:
                        adj_rets = adj_rets + rebal_fee_extra * 0.5
                    nav_arr = (1.0 - sub_fee_rate) * np.cumprod(1.0 + adj_rets)
                    curve_series = pd.Series(nav_arr, index=comb_rets.index)
                    used_proxy_early = True
                    proxy_note = (
                        f"所选起点 {clean_date} 早于本方案基金共同成立日（{real_first_dt.strftime('%Y-%m-%d')}）："
                        f"早期段（{clean_date} ~ {real_first_dt.strftime('%Y-%m-%d')}）按 10 大风格桶基准指数衔接测算，"
                        f"自 {real_first_dt.strftime('%Y-%m-%d')} 起 100% 切换为终选基金真实复权净值。"
                    )

        if curve_series is None:
            s_cut = s_real[s_real.index >= dt_target]
            if len(s_cut) < 2:
                s_cut = s_real.tail(max(20, min(len(s_real), 63)))
            r_cut = s_cut.pct_change().fillna(0.0).to_numpy(dtype=np.float64)
            r_cut[0] = 0.0
            nav_arr = (1.0 - sub_fee_rate) * np.cumprod(1.0 + r_cut)
            curve_series = pd.Series(nav_arr, index=s_cut.index)

    dates_idx = curve_series.index
    n_fwd = len(dates_idx)
    fwd_dates = [d.strftime("%Y-%m-%d") for d in dates_idx]
    actual_start_dt = dates_idx[0]

    def _align_bench(col_name: str) -> np.ndarray:
        if col_name not in df_mat_idx.columns:
            return np.ones(n_fwd, dtype=np.float64)
        s_b = df_mat_idx[col_name].astype(float).reindex(dates_idx).ffill().bfill()
        v = s_b.to_numpy(dtype=np.float64)
        return v / max(float(v[0]), 1e-8)

    h300_arr = _align_bench("H00300")
    if "BENCHMARK_50_50" in df_mat_idx.columns:
        bm50_arr = _align_bench("BENCHMARK_50_50")
    else:
        h11_arr = _align_bench("H11009")
        bm50_arr = 0.5 * h300_arr + 0.5 * h11_arr

    curve_df = pd.DataFrame({
        "date": fwd_dates,
        "strategy_net_nav": curve_series.to_numpy(dtype=np.float64),
        "h300_nav": h300_arr,
        "benchmark_nav": bm50_arr,
    })

    def _calc_horizon_kpi(idx_end: int) -> Dict[str, Any]:
        sub_df = curve_df.iloc[: idx_end + 1]
        cal_days = max(1, (pd.to_datetime(sub_df["date"].iloc[-1]) - actual_start_dt).days)
        if cal_days < 7:
            red_fee = 0.0150
        elif cal_days < 30:
            red_fee = 0.0050
        elif cal_days < 180:
            red_fee = 0.0035
        elif cal_days < 365:
            red_fee = 0.0015
        else:
            red_fee = 0.0000

        gross_nav = float(sub_df["strategy_net_nav"].iloc[-1])
        to_pocket_ret = (gross_nav * (1.0 - red_fee) - 1.0) * 100.0
        cmax = sub_df["strategy_net_nav"].cummax()
        mdd = float(((sub_df["strategy_net_nav"] - cmax) / np.maximum(cmax, 1e-8)).min() * 100.0)

        h_ret = (float(sub_df["h300_nav"].iloc[-1]) - 1.0) * 100.0
        h_cmax = sub_df["h300_nav"].cummax()
        h_mdd = float(((sub_df["h300_nav"] - h_cmax) / np.maximum(h_cmax, 1e-8)).min() * 100.0)

        bm_ret = (float(sub_df["benchmark_nav"].iloc[-1]) - 1.0) * 100.0
        alpha = to_pocket_ret - h_ret
        verdict = (
            "大幅战胜基准" if alpha > 3.0 else ("回撤显著收敛" if mdd > h_mdd + 3.0 else ("跑平基准" if abs(alpha) <= 3.0 else "阶段跑输基准"))
        )
        return {
            "days": cal_days,
            "trade_days": len(sub_df),
            "net_return_pct": round(to_pocket_ret, 2),
            "mdd_pct": round(mdd, 2),
            "h300_return_pct": round(h_ret, 2),
            "h300_mdd_pct": round(h_mdd, 2),
            "bm_return_pct": round(bm_ret, 2),
            "alpha_vs_h300": round(alpha, 2),
            "red_fee_pct": round(red_fee * 100.0, 2),
            "verdict": verdict,
        }

    kpi_3m = _calc_horizon_kpi(min(63, n_fwd - 1)) if n_fwd >= 20 else None
    kpi_6m = _calc_horizon_kpi(min(126, n_fwd - 1)) if n_fwd >= 60 else None
    kpi_1y = _calc_horizon_kpi(min(252, n_fwd - 1)) if n_fwd >= 120 else None
    kpi_all = _calc_horizon_kpi(n_fwd - 1) if n_fwd >= 2 else None

    return {
        "status": "ready",
        "target_date": fwd_dates[0] if fwd_dates else clean_date,
        "used_proxy_early": used_proxy_early,
        "proxy_note": proxy_note,
        "portfolio_weights": final_weights,
        "curve_df": curve_df,
        "kpi_3m": kpi_3m,
        "kpi_6m": kpi_6m,
        "kpi_1y": kpi_1y,
        "kpi_all": kpi_all,
    }
