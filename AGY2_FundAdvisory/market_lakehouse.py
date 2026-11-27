# -*- coding: utf-8 -*-
"""
AGY2 全市场 28,177 只离线精英真实复权净值湖仓与防封禁同步引擎 (market_lakehouse.py)
核心能力：
  1. 纯本地 5 表联合海选（28,177 目录 + 20,659 业绩快照 + 18,566 机构评级 + 36,660 经理履历 + 27,884 交易规则），
     按 10 大风格桶均衡初筛约 360~400 只跨全品类高流动性合规候选（彻底打破 12 只固定池）；
  2. 防封禁静态 CDN 建库（pingzhongdata/{code}.js，1 只基金 = 1 次 GET，2 并发 + 随机抖动 + 断点续传 + 403/429 熔断）：
     - 从 Data_netWorthTrend.equityReturn 累乘构造【真实红利再投资复权净值】（根治 ACWorthTrend 分红失真）；
     - 同步解析官方单基净资产规模 Data_fluctuationScale（根治经理总规模误放迷你基）；
     - 统一对齐至 A 股交易日轴并 ffill(limit=5) 处理 QDII T+2 时区差；
  3. 极轻防封禁盘后增量日更（FundMNFInfo 50 只/批，360 只仅 8 次 HTTP 请求，< 2 秒，按官方 NAVCHGRT 累乘复权）；
  4. 5 张全市场基础表周/月低频整表刷新（全套 < 10 次请求，内置冷却锁防重复）；
  5. 支持 Wind 离线导出的标准 CSV/Parquet 一键合入同一湖仓契约。
"""

from __future__ import annotations

import datetime
import json
import random
import re
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

import runtime_paths

WORKSPACE_ROOT = runtime_paths.get_workspace_root()
PROCESSED_DIR = runtime_paths.get_data_dir() / "processed"
CACHE_ELITE_DIR = runtime_paths.get_cache_dir() / "elite_nav"
ELITE_NAV_MATRIX_PATH = runtime_paths.resolve_data_file("processed/market_elite_nav_matrix.parquet")
ELITE_META_PATH = runtime_paths.resolve_data_file("processed/market_elite_meta.parquet")
ELITE_STATUS_PATH = runtime_paths.resolve_data_file("processed/market_elite_sync_status.json")


def _read_elite_nav_path() -> Path:
    return runtime_paths.resolve_data_file("processed/market_elite_nav_matrix.parquet")


def _read_elite_meta_path() -> Path:
    return runtime_paths.resolve_data_file("processed/market_elite_meta.parquet")


def _read_elite_status_path() -> Path:
    return runtime_paths.resolve_data_file("processed/market_elite_sync_status.json")


def _write_processed_path(filename: str) -> Path:
    p = runtime_paths.get_data_dir() / "processed" / filename
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

# 12 大资产风格桶中文名、宪法资产大类映射与默认均衡配额（含中短债安全垫、港股离岸与综合商品隔离）
BUCKET_10_CONFIG: Dict[str, Dict[str, Any]] = {
    "short_bond": {
        "label": "中短债现金垫",
        "asset_class": "bond",
        "quota": 24,
        "is_active": False,
        "is_index_eligible": True,
        "min_scale_yi": 3.0,
    },
    "pure_bond": {
        "label": "纯债固收",
        "asset_class": "bond",
        "quota": 40,
        "is_active": False,
        "is_index_eligible": True,
        "min_scale_yi": 2.0,
    },
    "fixed_income_plus": {
        "label": "固收+二级债",
        "asset_class": "bond",
        "quota": 36,
        "is_active": True,
        "is_index_eligible": False,
        "min_scale_yi": 3.0,
    },
    "dividend_value": {
        "label": "红利低波价值",
        "asset_class": "equity",
        "quota": 30,
        "is_active": False,
        "is_index_eligible": True,
        "min_scale_yi": 2.0,
    },
    "broad_index": {
        "label": "A股核心宽基",
        "asset_class": "equity",
        "quota": 32,
        "is_active": False,
        "is_index_eligible": True,
        "min_scale_yi": 2.0,
    },
    "quant_mid_small": {
        "label": "量化与中小盘指增",
        "asset_class": "equity",
        "quota": 34,
        "is_active": False,
        "is_index_eligible": True,
        "min_scale_yi": 2.0,
    },
    "sector_theme_index": {
        "label": "行业主题指数",
        "asset_class": "equity",
        "quota": 32,
        "is_active": False,
        "is_index_eligible": True,
        "min_scale_yi": 2.0,
    },
    "hk_offshore": {
        "label": "港股与沪港深",
        "asset_class": "hk_equity",
        "quota": 20,
        "is_active": False,
        "is_index_eligible": True,
        "min_scale_yi": 2.0,
    },
    "active_balanced_equity": {
        "label": "主动绩优均衡",
        "asset_class": "equity",
        "quota": 50,
        "is_active": True,
        "is_index_eligible": False,
        "min_scale_yi": 5.0,
    },
    "active_sector_growth": {
        "label": "主动科技与行业成长",
        "asset_class": "equity",
        "quota": 40,
        "is_active": True,
        "is_index_eligible": False,
        "min_scale_yi": 5.0,
    },
    "overseas_qdii": {
        "label": "海外QDII跨市场",
        "asset_class": "qdii",
        "quota": 26,
        "is_active": False,
        "is_index_eligible": True,
        "min_scale_yi": 2.0,
    },
    "commodity_gold": {
        "label": "纯黄金避险",
        "asset_class": "gold",
        "quota": 16,
        "is_active": False,
        "is_index_eligible": True,
        "min_scale_yi": 2.0,
    },
    "other_commodity": {
        "label": "能源与综合商品",
        "asset_class": "commodity",
        "quota": 8,
        "is_active": True,
        "is_index_eligible": False,
        "min_scale_yi": 3.0,
    },
}

# 核心标杆种子代码（100% 场外开放式、零锁定期、零场内 ETF：已剔除 1 年锁定期 000086 与场内 ETF 510300）
_ANCHOR_SEED_CODES = [
    "002351", "006210", "006668", "006772", "005561", "100032",
    "000216", "000218", "050025", "110020", "017436", "270023",
    "011612", "000478", "004194", "090010", "002610", "001071", "161017",
]

# 定向补强标杆（高流动性大厂开放中短债 + 真实高限额开申大厂全球 QDII）
_DEFAULT_TOPUP_CODES = [
    # 12 只高流动性大厂开放中短债（零锁定期、日限额 >= 10 万、费率 <= 0.40%）
    "006668", "006772", "007901", "007319", "004155", "008505",
    "008686", "016717", "008448", "015530", "013520", "008820",
    # 6 只真实非中国高限额开申大厂场外全球/美股 QDII（零中概、零 REITs）
    "270023", "012920", "012060", "005698", "100055", "000614",
]

# 锁定期/封闭/后端/外币份额/滚动运作全量黑名单正则（覆盖阿拉伯与中文数字）
LOCKUP_NAME_PATTERN = re.compile(
    r"后端|定开|定期开放|封闭|持有期|个月持有|天持有|年持有|滚动持有|天滚动|个月滚动|滚动运作"
)
_FX_SHARE_PATTERN = re.compile(r"美元|现汇|现钞|港币|欧元")
# 纯场内 ETF 代码段（特别注意：519xxx 是上交所场外开放式基金代码段，绝不可误杀！）
_EXCHANGE_ONLY_PREFIXES = ("510", "511", "512", "513", "515", "516", "517", "518", "159", "560", "561", "562", "563", "588")

_LAKEHOUSE_MEM_LOCK = threading.Lock()
_LAKEHOUSE_MEM_CACHE: Dict[str, Any] = {"mtime": 0.0, "nav": None, "meta": None}


def is_lockup_or_banned_fund(
    fund_name: str,
    fund_code: str = "",
    purchase_status: str = "",
) -> bool:
    """
    判定标的是否触发中国场外开放式买基硬禁用红线：
      1. 锁定期 / 持有期 / 滚动运作 / 定期开放 / 封闭 / 后端收费；
      2. 纯场内交易 ETF（非场外联接、非 LOF 场外申购，防止无券商账户用户买不进去）；
      3. 美元/港币/欧元外币现汇份额。
    """
    fn = str(fund_name or "").strip()
    fc = str(fund_code or "").strip().zfill(6) if str(fund_code or "").strip().isdigit() else str(fund_code or "").strip()
    ps = str(purchase_status or "").strip()

    if LOCKUP_NAME_PATTERN.search(fn):
        return True
    if _FX_SHARE_PATTERN.search(fn):
        return True
    if "场内交易" in ps:
        return True
    if fc and fc.startswith(_EXCHANGE_ONLY_PREFIXES) and ("联接" not in fn) and ("LOF" not in fn.upper()):
        return True
    return False


def classify_fund_bucket_10(
    fund_type: str,
    fund_name: str,
    fund_code: str = "",
    purchase_status: str = "",
) -> str:
    """
    结合官方 fund_type、基金名称、代码与申购渠道精准归入 12 大风格桶：
      - 强制拦截货币/理财与纯场内 ETF；
      - 严格隔离纯黄金联接 vs 油气商品 FOF / 周期有色金属股票基；
      - 严格隔离真海外 QDII vs 标普冠名 A 股红利 / 中概互联 / 香港银行 / 美国 REITs；
      - 拆分中短债现金垫 (short_bond) 与中长纯债 (pure_bond)。
    """
    ft = str(fund_type or "").strip()
    fn = str(fund_name or "").strip()
    fc = str(fund_code or "").strip().zfill(6) if str(fund_code or "").strip().isdigit() else str(fund_code or "").strip()
    ps = str(purchase_status or "").strip()

    if "货币" in ft or "理财" in ft or "货币" in fn:
        return "EXCLUDE_MONEY"
    if "场内交易" in ps or (fc and fc.startswith(_EXCHANGE_ONLY_PREFIXES) and ("联接" not in fn) and ("LOF" not in fn.upper())):
        return "EXCLUDE_EXCHANGE_ONLY"

    # 1. 纯黄金避险槽位：严禁混入油气 FOF、有色金属股票基、黄金股/矿业股
    has_gold_kw = any(k in fn for k in ("黄金", "上海金", "AU9999"))
    has_non_bullion_kw = any(k in fn for k in ("矿", "股", "有色", "油", "通胀", "农业", "资源", "FOF", "商品", "精选"))
    if has_gold_kw and (not has_non_bullion_kw) and ("股票" not in ft) and ("混合" not in ft):
        return "commodity_gold"

    # 2. 非纯金商品 / 油气 / 抗通胀 / REITs 独立隔离，绝不占黄金或海外股票宽基槽位
    if (
        "REIT" in ft.upper()
        or "REIT" in fn.upper()
        or "商品" in ft
        or any(k in fn for k in ("抗通胀", "原油", "石油", "豆粕", "能源化工", "天然资源", "房地产指数", "美国房地产"))
    ):
        return "other_commodity"

    # 3. 标普/道琼斯冠名的纯国内 A 股指数（如 008163 标普红利低波50、501029 标普中国A股红利）：强制不判海外！
    is_domestic_sp_index = (
        any(k in fn for k in ("标普中国", "标普A股", "中国A股"))
        or ("标普红利" in fn and "美国" not in fn and "QDII" not in ft.upper() and "QDII" not in fn.upper())
    )

    # 4. 中概互联与港股离岸隔离（中概/港股与 A 股高度正相关，不得冒充欧美海外对冲！）
    is_china_internet = any(k in fn for k in ("中概", "海外中国互联", "海外互联", "中国互联网"))
    is_hk_market = any(k in fn for k in ("香港", "恒生", "港股", "H股"))
    if is_china_internet:
        return "hk_offshore"
    if is_hk_market and not any(k in fn for k in ("沪港深红利", "港股通红利")):
        return "hk_offshore"
    if ("沪港深" in fn) and any(k in fn for k in ("红利", "高股息")):
        return "dividend_value"

    # 5. 真正非中国的海外/美股/全球 QDII
    if (not is_domestic_sp_index) and (
        "QDII" in ft.upper()
        or "海外" in ft
        or any(k in fn for k in ("标普500", "纳斯达克", "纳指", "道琼斯", "美股", "日经", "德国", "法国", "越南", "印度", "亚太", "欧洲", "全球", "美国"))
    ):
        return "overseas_qdii"

    # 6. 短债现金垫 vs 中长纯债 vs 固收+二级债
    if "债券" in ft or "固收" in ft:
        if any(k in ft for k in ("混合", "偏债", "可转债")) or "FOF" in ft.upper():
            return "fixed_income_plus"
        if ("中短债" in ft) or any(k in fn for k in ("短债", "超短债", "中短债", "短融", "同业存单")):
            return "short_bond"
        if any(k in ft for k in ("长债", "利率债", "信用债", "纯债", "指数型-固收")):
            return "pure_bond"
        return "pure_bond"

    if any(k in ft for k in ("混合型-偏债", "混合型-绝对收益")) or "FOF" in ft.upper():
        return "fixed_income_plus"

    # 7. 红利低波价值
    if any(k in fn for k in ("红利", "高股息", "自由现金流")):
        return "dividend_value"

    # 8. 指数型 / ETF 联接 / 指增（有色金属股票 ETF 明确归入行业主题指数，不再进黄金！）
    if "指数型" in ft or "ETF" in fn.upper() or "增强" in fn or "联接" in fn:
        if any(k in fn for k in ("芯片", "半导体", "医药", "医疗", "军工", "银行", "证券", "白酒", "消费", "光伏", "新能源", "人工智能", "AI", "通信", "算力", "游戏", "传媒", "有色", "煤炭", "电力", "创新药", "机器人", "汽车", "畜牧", "一带一路", "黄金股")):
            return "sector_theme_index"
        if any(k in fn for k in ("中证500", "中证1000", "中证2000", "国证2000", "创业板", "科创", "小盘", "增强")):
            return "quant_mid_small"
        if any(k in fn for k in ("沪深300", "上证50", "中证A50", "A500", "中证100", "央企")):
            return "broad_index"
        return "sector_theme_index"

    # 9. 主动行业成长 vs 主动均衡权益
    if any(k in fn for k in ("科技", "芯片", "半导体", "人工智能", "AI", "算力", "医药", "医疗", "消费", "新能源", "光伏", "军工", "制造", "机器人", "电子", "计算机", "创新药", "数字")):
        return "active_sector_growth"
    return "active_balanced_equity"


def is_index_style_fund(
    fund_type: str,
    fund_name: str,
    bucket_10: str,
    operating_fee: float = 0.6,
) -> bool:
    """
    严格判定是否符合「低费指数核心池 (index_only)」口径：
      - 绝不允许 FOF、主动偏股/混合、非纯金高费商品基混入；
      - 运作总费率必须 <= 0.85%；
      - 仅放行纯债/中短债、纯黄金联接、以及被动宽基/红利/行业/海外/港股指数与低费标准指增。
    """
    ft = str(fund_type or "")
    fn = str(fund_name or "")
    try:
        fee_v = float(operating_fee) if operating_fee is not None and pd.notna(operating_fee) else 0.6
    except Exception:
        fee_v = 0.6

    if bucket_10 in ("other_commodity", "fixed_income_plus", "active_balanced_equity", "active_sector_growth", "EXCLUDE_MONEY", "EXCLUDE_EXCHANGE_ONLY"):
        return False
    if "FOF" in ft.upper() or "FOF" in fn.upper() or "混合" in ft or "混合" in fn:
        return False
    if fee_v > 0.85:
        return False
    if bucket_10 in ("short_bond", "pure_bond", "commodity_gold", "broad_index", "quant_mid_small", "sector_theme_index"):
        return True
    if "指数" in ft or "ETF" in fn.upper() or "指数" in fn or "联接" in fn:
        return True
    return False


_is_index_style_fund = is_index_style_fund


def build_local_five_table_screened_candidates(
    target_total: int = 360,
    require_3y: bool = True,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    第 1 层：纯本地 5 张全市场真表联合海选（0 网络请求，< 150ms），
    输出均衡覆盖 10 大资产风格桶的约 target_total 只全市场精英候选名单及完整漏斗统计。
    """
    cat_p = runtime_paths.resolve_data_file("master/fund_catalog.parquet")
    perf_p = runtime_paths.resolve_data_file("mart/fund_performance_snapshot.parquet")
    rat_p = runtime_paths.resolve_data_file("mart/fund_ratings.parquet")
    mgr_p = runtime_paths.resolve_data_file("master/fund_managers.parquet")
    rul_p = runtime_paths.resolve_data_file("master/fund_trading_rules.parquet")

    if not cat_p.exists():
        raise FileNotFoundError(f"缺少全市场基金目录表: {cat_p}")

    cat = pd.read_parquet(cat_p)
    total_market = len(cat)
    cat["fund_code"] = cat["symbol"].astype(str).str.strip().str.zfill(6)
    df = cat[["fund_code", "fund_name", "fund_type"]].drop_duplicates(subset=["fund_code"]).copy()

    if perf_p.exists():
        perf = pd.read_parquet(perf_p)
        perf["fund_code"] = perf["symbol"].astype(str).str.strip().str.zfill(6)
        p_cols = [c for c in ("fund_code", "nav_date", "return_3m", "return_6m", "return_1y", "return_2y", "return_3y", "return_ytd") if c in perf.columns]
        df = df.merge(perf[p_cols].drop_duplicates(subset=["fund_code"]), on="fund_code", how="left")

    if rat_p.exists():
        rat = pd.read_parquet(rat_p)
        rat["fund_code"] = rat["symbol"].astype(str).str.strip().str.zfill(6)
        for rc in ("5星评级家数", "rating_sh", "rating_zs", "rating_ja", "rating_morningstar"):
            if rc in rat.columns:
                rat[rc] = pd.to_numeric(rat[rc], errors="coerce").fillna(0.0)
        rat["five_star_cnt"] = rat.get("5星评级家数", pd.Series(0.0, index=rat.index))
        rat["max_star"] = rat[[c for c in ("rating_sh", "rating_zs", "rating_ja", "rating_morningstar") if c in rat.columns]].max(axis=1)
        r_keep = ["fund_code", "five_star_cnt", "max_star"]
        if "company" in rat.columns:
            r_keep.append("company")
        df = df.merge(rat[r_keep].drop_duplicates(subset=["fund_code"]), on="fund_code", how="left")
    else:
        df["five_star_cnt"] = 0.0
        df["max_star"] = 0.0

    if mgr_p.exists():
        mgr = pd.read_parquet(mgr_p)
        mgr["fund_code"] = mgr["fund_code"].astype(str).str.strip().str.zfill(6)
        mgr_agg = mgr.groupby("fund_code").agg(
            mgr_total_aum_yi=("aum_billion", "max"),
            mgr_career_days=("career_days", "max"),
            mgr_best_return_pct=("best_return_pct", "max"),
        ).reset_index()
        df = df.merge(mgr_agg, on="fund_code", how="left")
    else:
        df["mgr_total_aum_yi"] = np.nan
        df["mgr_career_days"] = np.nan
        df["mgr_best_return_pct"] = np.nan

    if rul_p.exists():
        rul = pd.read_parquet(rul_p)
        rul["fund_code"] = rul["symbol"].astype(str).str.strip().str.zfill(6)
        rul_cols = [c for c in ("fund_code", "is_purchase_allowed", "daily_limit_amount", "est_total_operating_fee", "purchase_status") if c in rul.columns]
        df = df.merge(rul[rul_cols].drop_duplicates(subset=["fund_code"]), on="fund_code", how="left")
    else:
        df["is_purchase_allowed"] = True
        df["daily_limit_amount"] = 1e10
        df["est_total_operating_fee"] = 0.8
        df["purchase_status"] = "开放申购"

    # 12 大风格桶分类 & 100% 场外开放式硬清洗
    df["bucket_10"] = [
        classify_fund_bucket_10(ft, fn, fc, ps)
        for ft, fn, fc, ps in zip(df["fund_type"], df["fund_name"], df["fund_code"], df.get("purchase_status", ""))
    ]
    df = df[~df["bucket_10"].isin(["EXCLUDE_MONEY", "EXCLUDE_EXCHANGE_ONLY"])].copy()

    # A/C 去重（保留 A 类主份额；全量封禁锁定期/滚动持有/外币/纯场内 ETF，种子池亦不得绕过！）
    fn_s = df["fund_name"].astype(str).str.strip()
    is_banned = pd.Series(
        [
            is_lockup_or_banned_fund(fn, fc, ps)
            for fn, fc, ps in zip(df["fund_name"], df["fund_code"], df.get("purchase_status", ""))
        ],
        index=df.index,
    )
    is_non_a = fn_s.str.endswith(("C", "C类", "E", "E类", "B", "B类", "I", "I类", "D", "D类", "H"))
    is_anchor = df["fund_code"].isin(_ANCHOR_SEED_CODES)

    # 开放申购且单日限额 >= 1000（避免暂停申购或 100 元超小限购买不进去）
    open_buy = df["is_purchase_allowed"].fillna(True).astype(bool) & (
        pd.to_numeric(df["daily_limit_amount"], errors="coerce").fillna(1e9) >= 1000.0
    )
    has_3y = df["return_3y"].notna() if ("return_3y" in df.columns and require_3y) else pd.Series(True, index=df.index)

    # 合规初筛池（锁定期/场内禁令对所有标的包括种子池严格生效）
    compliant_mask = (~is_banned) & (~is_non_a | is_anchor) & (open_buy | is_anchor) & (has_3y | is_anchor)
    compliant = df[compliant_mask].copy()
    compliant_count = len(compliant)

    # 同一基金基础名去重（防同类同名重复入围）
    compliant["_base_name"] = (
        compliant["fund_name"]
        .astype(str)
        .str.replace(r"(A类|C类|A|C|\(QDII\)|\(LOF\)|\(FOF\)|发起式|联接)$", "", regex=True)
        .str.strip()
    )

    # 跨周期稳健综合初筛分（3Y + 2Y + 1Y 均衡 + 机构评级 + 经理任期 + 低费率，杜绝单年追高）
    for col in ("return_1y", "return_2y", "return_3y", "return_6m"):
        if col not in compliant.columns:
            compliant[col] = 0.0
        compliant[col] = pd.to_numeric(compliant[col], errors="coerce")
    compliant["five_star_cnt"] = pd.to_numeric(compliant["five_star_cnt"], errors="coerce").fillna(0.0)
    compliant["max_star"] = pd.to_numeric(compliant["max_star"], errors="coerce").fillna(0.0)
    compliant["mgr_career_days"] = pd.to_numeric(compliant["mgr_career_days"], errors="coerce").fillna(365.0)
    compliant["mgr_total_aum_yi"] = pd.to_numeric(compliant["mgr_total_aum_yi"], errors="coerce").fillna(2.0)
    compliant["est_total_operating_fee"] = pd.to_numeric(compliant["est_total_operating_fee"], errors="coerce").fillna(0.8)

    scale_factor = float(target_total) / max(sum(cfg["quota"] for cfg in BUCKET_10_CONFIG.values()), 1)
    selected_parts: List[pd.DataFrame] = []
    seen_codes: set = set()
    seen_bases: set = set()

    # 先保底写入核心标杆种子
    anchors_df = compliant[compliant["fund_code"].isin(_ANCHOR_SEED_CODES)].copy()
    anchors_df["screen_score"] = 99.0
    for _, row in anchors_df.iterrows():
        c = row["fund_code"]
        if c not in seen_codes:
            seen_codes.add(c)
            seen_bases.add(row["_base_name"])
    selected_parts.append(anchors_df)

    # 按 10 大风格桶强制配额均衡抽取
    for b_key, cfg in BUCKET_10_CONFIG.items():
        grp = compliant[compliant["bucket_10"] == b_key].copy()
        if grp.empty:
            continue
        quota = max(12, int(round(cfg["quota"] * scale_factor)))

        # 主动型基金额外施加硬门槛：经理任职 >= 2 年 & 4/5 星评级优先 & 经理在管规模 >= 5 亿（入库后再按真实单基规模二次核验）
        if cfg["is_active"]:
            strict_grp = grp[(grp["mgr_career_days"] >= 730) & (grp["max_star"] >= 4.0) & (grp["mgr_total_aum_yi"] >= 5.0)]
            if len(strict_grp) >= quota:
                grp = strict_grp.copy()
            else:
                # 若极少数桶略不足，用任职 >= 1.5 年补充
                soft_grp = grp[(grp["mgr_career_days"] >= 540) & (grp["mgr_total_aum_yi"] >= 2.0)]
                if len(soft_grp) >= min(quota, 15):
                    grp = soft_grp.copy()

        def _pct_rank(s: pd.Series) -> pd.Series:
            return s.rank(pct=True, na_option="bottom").fillna(0.5)

        r3 = _pct_rank(grp["return_3y"])
        r2 = _pct_rank(grp["return_2y"])
        r1 = _pct_rank(grp["return_1y"])
        # 跨周期一致性奖励：避免单年暴涨暴跌的“过山车基”
        consistency = 1.0 - (r3 - r1).abs()
        star_s = np.clip((grp["max_star"] / 5.0) * 0.6 + np.minimum(grp["five_star_cnt"], 4.0) / 4.0 * 0.4, 0.0, 1.0)
        tenure_s = np.clip(grp["mgr_career_days"] / 2500.0, 0.0, 1.0)
        fee_s = 1.0 - _pct_rank(grp["est_total_operating_fee"])

        if cfg["is_active"]:
            grp["screen_score"] = (
                0.28 * r3 + 0.18 * r2 + 0.12 * r1 + 0.12 * consistency + 0.15 * star_s + 0.10 * tenure_s + 0.05 * fee_s
            ) * 100.0
        else:
            # 指数/纯债/黄金/QDII 更重视低费率、长期稳健、大厂规模与评级
            aum_s = _pct_rank(grp["mgr_total_aum_yi"])
            grp["screen_score"] = (
                0.25 * r3 + 0.15 * r2 + 0.10 * r1 + 0.15 * consistency + 0.15 * fee_s + 0.10 * star_s + 0.10 * aum_s
            ) * 100.0

        grp = grp.sort_values("screen_score", ascending=False)
        picked_rows = []
        already_in_bucket = int((anchors_df["bucket_10"] == b_key).sum())
        need = max(0, quota - already_in_bucket)
        for _, row in grp.iterrows():
            if len(picked_rows) >= need:
                break
            c = row["fund_code"]
            bn = row["_base_name"]
            if c in seen_codes or bn in seen_bases:
                continue
            seen_codes.add(c)
            seen_bases.add(bn)
            picked_rows.append(row)
        if picked_rows:
            selected_parts.append(pd.DataFrame(picked_rows))

    elite_df = pd.concat(selected_parts, ignore_index=True)
    elite_df = elite_df.drop_duplicates(subset=["fund_code"]).reset_index(drop=True)
    elite_df["bucket_label"] = elite_df["bucket_10"].map(lambda k: BUCKET_10_CONFIG.get(k, {}).get("label", "核心配置"))
    elite_df["asset_class"] = elite_df["bucket_10"].map(lambda k: BUCKET_10_CONFIG.get(k, {}).get("asset_class", "equity"))
    elite_df["is_active_fund"] = elite_df["bucket_10"].map(lambda k: bool(BUCKET_10_CONFIG.get(k, {}).get("is_active", False)))
    elite_df["is_index_eligible"] = [
        is_index_style_fund(ft, fn, b10, fee)
        for ft, fn, b10, fee in zip(
            elite_df["fund_type"],
            elite_df["fund_name"],
            elite_df["bucket_10"],
            elite_df.get("est_total_operating_fee", 0.6),
        )
    ]
    elite_df = elite_df.drop(columns=["_base_name"], errors="ignore")

    funnel_stats = {
        "total_market_funds": int(total_market),
        "compliant_screened_funds": int(compliant_count),
        "elite_candidate_count": int(len(elite_df)),
        "bucket_counts": {str(k): int(v) for k, v in elite_df["bucket_10"].value_counts().items()},
    }
    return elite_df, funnel_stats


def _fetch_pingzhongdata_adjusted_nav(code: str, timeout: int = 10) -> Dict[str, Any]:
    """
    通过东财静态 CDN `pingzhongdata/{code}.js` 单次请求提取：
      1. 真实红利再投资复权净值序列（基于 Data_netWorthTrend.equityReturn 累乘，绝不使用未复权 ACWorthTrend）；
      2. 官方最新季报真实单基净资产规模（Data_fluctuationScale，单位：亿元）；
      3. 成立首日与最新净值日期。
    """
    url = f"https://fund.eastmoney.com/pingzhongdata/{code}.js"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://fundf10.eastmoney.com/",
        },
    )
    raw = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", errors="ignore")

    # 1. 解析 Data_netWorthTrend 并构造真实复权净值
    m_nw = re.search(r"var Data_netWorthTrend\s*=\s*(\[.*?\]);", raw, re.S)
    if not m_nw:
        raise ValueError(f"{code}: missing Data_netWorthTrend")
    nw_list = json.loads(m_nw.group(1))
    if not nw_list or len(nw_list) < 30:
        raise ValueError(f"{code}: insufficient nav history ({len(nw_list)})")

    dates: List[pd.Timestamp] = []
    unit_navs: List[float] = []
    eq_rets: List[float] = []
    for item in nw_list:
        ts_ms = item.get("x")
        y_val = item.get("y")
        if ts_ms is None or y_val is None:
            continue
        dt = pd.to_datetime(int(ts_ms), unit="ms", utc=True).tz_convert("Asia/Shanghai").tz_localize(None).normalize()
        dates.append(dt)
        unit_navs.append(float(y_val))
        er = item.get("equityReturn")
        try:
            er_f = float(er) if er not in (None, "", "--") else np.nan
        except Exception:
            er_f = np.nan
        eq_rets.append(er_f)

    if len(dates) < 30:
        raise ValueError(f"{code}: insufficient parsed dates ({len(dates)})")

    df_s = pd.DataFrame({"date": dates, "unit_nav": unit_navs, "eq_ret": eq_rets})
    df_s = df_s.drop_duplicates(subset=["date"], keep="last").sort_values("date").reset_index(drop=True)

    # 逐日复权涨跌幅（缺失项用单位净值日变化安全兜底，且做 [-20%, +25%] 异常保护防坏点）
    fallback_ret = df_s["unit_nav"].pct_change().fillna(0.0) * 100.0
    clean_ret_pct = df_s["eq_ret"].combine_first(fallback_ret).fillna(0.0).clip(-22.0, 28.0)
    clean_ret_pct.iloc[0] = 0.0
    adj_nav = np.cumprod(1.0 + clean_ret_pct.to_numpy(dtype=np.float64) / 100.0)
    df_s["adj_nav"] = adj_nav

    # 2. 解析真实单基金净资产规模 Data_fluctuationScale（单位：亿元）
    real_scale_yi: Optional[float] = None
    m_sc = re.search(r"var Data_fluctuationScale\s*=\s*(\{.*?\});", raw, re.S)
    if m_sc:
        try:
            sc_obj = json.loads(m_sc.group(1))
            ser = sc_obj.get("series") or []
            if ser:
                last_y = ser[-1].get("y")
                if last_y is not None:
                    real_scale_yi = round(float(last_y), 2)
        except Exception:
            real_scale_yi = None

    return {
        "fund_code": code,
        "df": df_s[["date", "adj_nav", "unit_nav"]],
        "real_scale_yi": real_scale_yi,
        "inception_date": str(df_s["date"].iloc[0])[:10],
        "latest_nav_date": str(df_s["date"].iloc[-1])[:10],
        "nav_rows": int(len(df_s)),
    }


def sync_elite_nav_lakehouse(
    target_total: int = 360,
    workers: int = 2,
    jitter_range: Tuple[float, float] = (0.25, 0.55),
    resume: bool = True,
    force_refetch: bool = False,
    start_date: str = "2018-01-01",
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
) -> Dict[str, Any]:
    """
    第 2 层：防封禁离线建库（静态 CDN 单次请求 + 2 并发随机抖动 + 单基断点续传 + 403/429 熔断退避）。
    构建并落盘：
      - data/processed/market_elite_nav_matrix.parquet（A 股交易日轴对齐的真实复权净值矩阵）
      - data/processed/market_elite_meta.parquet（含真实单基规模、官方类型、10 桶标签、评级、经理、费率）
      - data/processed/market_elite_sync_status.json（湖仓状态元数据）
    """
    t0 = time.monotonic()
    CACHE_ELITE_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    cand_df, funnel_stats = build_local_five_table_screened_candidates(target_total=target_total, require_3y=True)
    codes = cand_df["fund_code"].tolist()
    total = len(codes)

    meta_cache_path = CACHE_ELITE_DIR / "_scale_meta_cache.json"
    scale_cache: Dict[str, Dict[str, Any]] = {}
    if meta_cache_path.exists():
        try:
            scale_cache = json.loads(meta_cache_path.read_text(encoding="utf-8"))
        except Exception:
            scale_cache = {}

    to_fetch: List[str] = []
    cached_hits = 0
    for c in codes:
        fp = CACHE_ELITE_DIR / f"{c}.parquet"
        if resume and (not force_refetch) and fp.exists() and c in scale_cache:
            cached_hits += 1
        else:
            to_fetch.append(c)

    if progress_cb:
        progress_cb(cached_hits, total, f"命中断点续传缓存 {cached_hits}/{total} 只，待礼貌采集 {len(to_fetch)} 只...")

    # 防封禁熔断器状态
    cb_lock = threading.Lock()
    state = {"consecutive_blocks": 0, "aborted": False, "fetched": 0, "failed": 0}

    def _polite_worker(code: str) -> Optional[Dict[str, Any]]:
        with cb_lock:
            if state["aborted"]:
                return None
        # 随机抖动降低 QPS 峰值
        time.sleep(random.uniform(jitter_range[0], jitter_range[1]))
        for attempt in range(2):
            with cb_lock:
                if state["aborted"]:
                    return None
            try:
                res = _fetch_pingzhongdata_adjusted_nav(code, timeout=10)
                with cb_lock:
                    state["consecutive_blocks"] = 0
                return res
            except urllib.error.HTTPError as he:
                if he.code in (403, 429):
                    with cb_lock:
                        state["consecutive_blocks"] += 1
                        if state["consecutive_blocks"] >= 3:
                            state["aborted"] = True
                            return None
                    time.sleep(3.0 * (attempt + 1))
                else:
                    return None
            except Exception:
                if attempt == 0:
                    time.sleep(0.8)
                else:
                    return None
        return None

    done_count = cached_hits
    if to_fetch:
        with ThreadPoolExecutor(max_workers=max(1, min(3, int(workers)))) as pool:
            futs = {pool.submit(_polite_worker, c): c for c in to_fetch}
            for fut in as_completed(futs):
                code = futs[fut]
                res = None
                try:
                    res = fut.result()
                except Exception:
                    res = None
                done_count += 1
                if res is not None:
                    try:
                        res["df"].to_parquet(CACHE_ELITE_DIR / f"{code}.parquet", index=False)
                        scale_cache[code] = {
                            "real_scale_yi": res["real_scale_yi"],
                            "inception_date": res["inception_date"],
                            "latest_nav_date": res["latest_nav_date"],
                            "nav_rows": res["nav_rows"],
                        }
                        state["fetched"] += 1
                    except Exception:
                        state["failed"] += 1
                else:
                    state["failed"] += 1

                if done_count % 25 == 0 or done_count == total:
                    try:
                        meta_cache_path.write_text(json.dumps(scale_cache, ensure_ascii=False, indent=2), encoding="utf-8")
                    except Exception:
                        pass
                    if progress_cb:
                        progress_cb(done_count, total, f"已同步 {done_count}/{total} 只（新增 {state['fetched']}，失败 {state['failed']}）")

        try:
            meta_cache_path.write_text(json.dumps(scale_cache, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    # 3. 汇总构建对齐后的真实复权净值矩阵（统一对齐至 A 股交易日轴并 ffill(limit=5) 处理 QDII T+2 滞后）
    return _assemble_lakehouse_parquet(
        cand_df=cand_df,
        scale_cache=scale_cache,
        funnel_stats=funnel_stats,
        start_date=start_date,
        elapsed_sec=round(time.monotonic() - t0, 2),
        aborted_by_circuit_breaker=state["aborted"],
        fetched_new=state["fetched"],
        failed_count=state["failed"],
    )


def _assemble_lakehouse_parquet(
    cand_df: pd.DataFrame,
    scale_cache: Dict[str, Dict[str, Any]],
    funnel_stats: Dict[str, Any],
    start_date: str = "2018-01-01",
    elapsed_sec: float = 0.0,
    aborted_by_circuit_breaker: bool = False,
    fetched_new: int = 0,
    failed_count: int = 0,
) -> Dict[str, Any]:
    """将单基断点缓存组装为对齐的统一 Parquet 湖仓，并落实真实单基规模过滤（主动 ≥5 亿 / 被动 ≥2 亿）。"""
    # 读取 A 股官方交易日轴（以 aligned_matrix_total_return.parquet 为主干，再并入最新交易日）
    ref_dates: List[pd.Timestamp] = []
    mat_p = PROCESSED_DIR / "aligned_matrix_total_return.parquet"
    if mat_p.exists():
        try:
            ref_df = pd.read_parquet(mat_p, columns=["date"])
            ref_dates = pd.to_datetime(ref_df["date"]).dt.normalize().tolist()
        except Exception:
            ref_dates = []

    series_map: Dict[str, pd.Series] = {}
    meta_rows: List[Dict[str, Any]] = []
    start_ts = pd.Timestamp(start_date)
    all_dates_set = set(ref_dates)

    for _, row in cand_df.iterrows():
        code = str(row["fund_code"])
        fp = CACHE_ELITE_DIR / f"{code}.parquet"
        if not fp.exists():
            continue
        try:
            df_f = pd.read_parquet(fp)
            if df_f.empty or "date" not in df_f.columns or "adj_nav" not in df_f.columns:
                continue
            df_f["date"] = pd.to_datetime(df_f["date"]).dt.normalize()
            df_f = df_f[df_f["date"] >= start_ts].drop_duplicates(subset=["date"], keep="last").sort_values("date")
            if len(df_f) < 480:  # 至少约 2 年有效交易日历史
                continue
        except Exception:
            continue

        sc_info = scale_cache.get(code) or {}
        real_scale = sc_info.get("real_scale_yi")
        b10 = str(row["bucket_10"])
        fn_str = str(row.get("fund_name", ""))
        is_anchor = code in _ANCHOR_SEED_CODES
        min_scale = float(BUCKET_10_CONFIG.get(b10, {}).get("min_scale_yi", 2.0))
        if "发起" in fn_str:
            min_scale = max(min_scale, 5.0)

        # 落实真实单基规模硬门槛（排除百亿经理挂名下的迷你基与发起式清盘雷！核心标杆种子放行）
        if (not is_anchor) and (real_scale is not None) and float(real_scale) < min_scale:
            continue

        s = df_f.set_index("date")["adj_nav"].astype(float)
        # 归一化起点为 1.0（保留真实收益比例与每只基金真实的起始 NaN，不提前填充未成立日期！）
        if float(s.iloc[0]) > 0:
            s = s / float(s.iloc[0])
        series_map[code] = s
        all_dates_set.update(s.index.tolist())

        rec = row.to_dict()
        rec["real_scale_yi"] = real_scale
        rec["inception_date"] = sc_info.get("inception_date", str(df_f["date"].iloc[0])[:10])
        rec["latest_nav_date"] = sc_info.get("latest_nav_date", str(df_f["date"].iloc[-1])[:10])
        rec["valid_trading_days"] = int(len(df_f))
        rec["data_source"] = "eastmoney_pingzhongdata_adj"
        meta_rows.append(rec)

    if not series_map:
        raise RuntimeError("未能组装有效基金净值矩阵，请检查网络连接或断点缓存目录")

    # 仅保留真实有交易的日期（过滤周末）
    cal_index = pd.DatetimeIndex(sorted(d for d in all_dates_set if d >= start_ts and d.weekday() < 5))
    aligned_cols: Dict[str, pd.Series] = {}
    for code, s in series_map.items():
        reindexed = s.reindex(cal_index)
        # 只在基金真实成立日之后做最多 5 个交易日 ffill（解决 QDII T+2 与节假日错位），成立日前严格保持 NaN！
        first_valid = reindexed.first_valid_index()
        if first_valid is not None:
            reindexed.loc[first_valid:] = reindexed.loc[first_valid:].ffill(limit=5)
        aligned_cols[code] = reindexed
    nav_mat = pd.DataFrame(aligned_cols, index=cal_index)

    nav_out = _write_processed_path("market_elite_nav_matrix.parquet")
    meta_out = _write_processed_path("market_elite_meta.parquet")
    status_out = _write_processed_path("market_elite_sync_status.json")

    nav_mat.index.name = "date"
    nav_mat.to_parquet(nav_out)

    meta_df = pd.DataFrame(meta_rows).drop_duplicates(subset=["fund_code"]).reset_index(drop=True)
    meta_df.to_parquet(meta_out, index=False)

    status = {
        "status": "ready",
        "synced_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "latest_date": str(nav_mat.index[-1])[:10],
        "start_date": str(nav_mat.index[0])[:10],
        "trading_days": int(len(nav_mat)),
        "elite_fund_count": int(len(meta_df)),
        "active_fund_count": int(meta_df["is_active_fund"].sum()) if "is_active_fund" in meta_df.columns else 0,
        "index_eligible_count": int(meta_df["is_index_eligible"].sum()) if "is_index_eligible" in meta_df.columns else 0,
        "bucket_counts": {str(k): int(v) for k, v in meta_df["bucket_10"].value_counts().items()},
        "funnel_stats": {
            **funnel_stats,
            "elite_lakehouse_funds": int(len(meta_df)),
        },
        "fetched_new": int(fetched_new),
        "failed_count": int(failed_count),
        "aborted_by_circuit_breaker": bool(aborted_by_circuit_breaker),
        "elapsed_sec": elapsed_sec,
        "daily_sync_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    status_out.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")

    # 失效内存缓存
    with _LAKEHOUSE_MEM_LOCK:
        _LAKEHOUSE_MEM_CACHE["mtime"] = 0.0
        _LAKEHOUSE_MEM_CACHE["nav"] = None
        _LAKEHOUSE_MEM_CACHE["meta"] = None

    return status


def incremental_daily_sync(cooldown_minutes: int = 30) -> Dict[str, Any]:
    """
    防封禁盘后增量日更（360 只仅需 7~8 次 FundMNFInfo 批量 HTTP 请求，< 2 秒）：
    基于官方披露的 PDATE 与 NAVCHGRT 累乘复权追加最新交易日，绝不触发封禁、绝不引入分红伪回撤。
    """
    nav_in = _read_elite_nav_path()
    meta_in = _read_elite_meta_path()
    if not nav_in.exists() or not meta_in.exists():
        return {"status": "not_initialized", "message": "精英净值湖仓尚未初始化，请先运行首次建库脚本。"}

    status_old = get_lakehouse_status()
    last_sync_s = status_old.get("daily_sync_at")
    if last_sync_s and cooldown_minutes > 0:
        try:
            last_dt = datetime.datetime.strptime(last_sync_s, "%Y-%m-%d %H:%M:%S")
            if (datetime.datetime.now() - last_dt).total_seconds() < cooldown_minutes * 60:
                return {
                    "status": "cooldown",
                    "message": f"距离上次日更不足 {cooldown_minutes} 分钟，已沿用最新湖仓快照（{status_old.get('latest_date')}）。",
                    "lakehouse": status_old,
                }
        except Exception:
            pass

    t0 = time.monotonic()
    nav_mat = pd.read_parquet(nav_in)
    meta_df = pd.read_parquet(meta_in)
    codes = [str(c) for c in nav_mat.columns]

    updates_by_date: Dict[pd.Timestamp, Dict[str, float]] = {}
    batch_size = 50
    requests_sent = 0

    for i in range(0, len(codes), batch_size):
        batch = codes[i : i + batch_size]
        url = (
            "https://fundmobapi.eastmoney.com/FundMNewApi/FundMNFInfo"
            f"?pageIndex=1&pageSize={batch_size + 10}&plat=Android&appType=ttjj&product=EFund&Version=1&deviceid=agy2"
            f"&Fcodes={','.join(batch)}"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            raw = urllib.request.urlopen(req, timeout=8).read().decode("utf-8", errors="ignore")
            requests_sent += 1
            datas = (json.loads(raw) or {}).get("Datas") or []
            for d in datas:
                fc = str(d.get("FCODE") or "").strip().zfill(6)
                pdate = str(d.get("PDATE") or "").strip()[:10]
                chg_raw = d.get("NAVCHGRT")
                if not fc or fc not in nav_mat.columns or len(pdate) != 10 or chg_raw in (None, "", "--"):
                    continue
                try:
                    dt = pd.Timestamp(pdate).normalize()
                    chg_pct = float(chg_raw)
                except Exception:
                    continue
                if -22.0 <= chg_pct <= 28.0:
                    updates_by_date.setdefault(dt, {})[fc] = chg_pct
        except Exception:
            continue
        time.sleep(0.15)

    appended_days = 0
    updated_cells = 0
    last_existing = pd.Timestamp(nav_mat.index[-1]).normalize()
    for dt in sorted(updates_by_date.keys()):
        if dt <= last_existing:
            continue
        prev_row = nav_mat.iloc[-1].copy()
        new_row = prev_row.copy()
        for fc, chg_pct in updates_by_date[dt].items():
            prev_val = prev_row.get(fc)
            if pd.notna(prev_val) and float(prev_val) > 0:
                new_row[fc] = float(prev_val) * (1.0 + chg_pct / 100.0)
                updated_cells += 1
        nav_mat.loc[dt] = new_row
        appended_days += 1

    if appended_days > 0:
        nav_mat = nav_mat.sort_index()
        nav_mat.to_parquet(_write_processed_path("market_elite_nav_matrix.parquet"))
        with _LAKEHOUSE_MEM_LOCK:
            _LAKEHOUSE_MEM_CACHE["mtime"] = 0.0

    status_old["latest_date"] = str(nav_mat.index[-1])[:10]
    status_old["trading_days"] = int(len(nav_mat))
    status_old["daily_sync_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status_old["last_daily_requests"] = requests_sent
    status_old["last_daily_appended_days"] = appended_days
    _write_processed_path("market_elite_sync_status.json").write_text(
        json.dumps(status_old, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return {
        "status": "ok",
        "requests_sent": requests_sent,
        "appended_days": appended_days,
        "updated_cells": updated_cells,
        "elapsed_ms": int(round((time.monotonic() - t0) * 1000)),
        "lakehouse": status_old,
    }


def load_elite_lakehouse() -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], Dict[str, Any]]:
    """高速内存缓存读取本地全市场精英复权净值矩阵与元数据表（< 5ms 热读，全面响应 AGY2_DATA_DIR / AGY2_SEED_DIR）。"""
    nav_p = _read_elite_nav_path()
    meta_p = _read_elite_meta_path()
    if not nav_p.exists() or not meta_p.exists():
        return None, None, {"status": "not_initialized"}

    cache_key = f"{nav_p}|{meta_p}"
    mtime = nav_p.stat().st_mtime + meta_p.stat().st_mtime
    with _LAKEHOUSE_MEM_LOCK:
        if (
            _LAKEHOUSE_MEM_CACHE["nav"] is not None
            and _LAKEHOUSE_MEM_CACHE.get("key") == cache_key
            and abs(_LAKEHOUSE_MEM_CACHE["mtime"] - mtime) < 1e-6
        ):
            return _LAKEHOUSE_MEM_CACHE["nav"], _LAKEHOUSE_MEM_CACHE["meta"], get_lakehouse_status()

    nav_df = pd.read_parquet(nav_p)
    nav_df.index = pd.to_datetime(nav_df.index)
    meta_df = pd.read_parquet(meta_p)
    meta_df["fund_code"] = meta_df["fund_code"].astype(str).str.strip().str.zfill(6)

    with _LAKEHOUSE_MEM_LOCK:
        _LAKEHOUSE_MEM_CACHE["key"] = cache_key
        _LAKEHOUSE_MEM_CACHE["mtime"] = mtime
        _LAKEHOUSE_MEM_CACHE["nav"] = nav_df
        _LAKEHOUSE_MEM_CACHE["meta"] = meta_df

    return nav_df, meta_df, get_lakehouse_status()


def get_lakehouse_status() -> Dict[str, Any]:
    status_p = _read_elite_status_path()
    if status_p.exists():
        try:
            return json.loads(status_p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"status": "not_initialized", "elite_fund_count": 0}


def import_wind_nav_file(input_path: Path) -> Dict[str, Any]:
    """
    Wind 离线导数可选导入适配器：
    接受长表 CSV/Parquet（列：date, fund_code, adj_nav [, real_scale_yi]）或宽表（index=date, columns=fund_code），
    标准化合入本地 market_elite_nav_matrix.parquet，零强依赖 WindPy 运行时。
    """
    p = Path(input_path)
    if not p.exists():
        raise FileNotFoundError(f"Wind 导出文件不存在: {p}")
    df_in = pd.read_parquet(p) if p.suffix.lower() == ".parquet" else pd.read_csv(p)
    if {"date", "fund_code", "adj_nav"}.issubset(df_in.columns):
        df_in["date"] = pd.to_datetime(df_in["date"]).dt.normalize()
        df_in["fund_code"] = df_in["fund_code"].astype(str).str.replace(".OF", "", regex=False).str.strip().str.zfill(6)
        wide = df_in.pivot_table(index="date", columns="fund_code", values="adj_nav", aggfunc="last").sort_index()
    else:
        date_col = "date" if "date" in df_in.columns else df_in.columns[0]
        df_in[date_col] = pd.to_datetime(df_in[date_col]).dt.normalize()
        wide = df_in.set_index(date_col).sort_index()
        wide.columns = [str(c).replace(".OF", "").strip().zfill(6) for c in wide.columns]

    # 归一化各列起点为 1.0 并合入现有精英矩阵
    for c in wide.columns:
        s = pd.to_numeric(wide[c], errors="coerce")
        fv = s.first_valid_index()
        if fv is not None and float(s.loc[fv]) > 0:
            s.loc[fv:] = s.loc[fv:].ffill(limit=5) / float(s.loc[fv])
        wide[c] = s

    nav_in = _read_elite_nav_path()
    if nav_in.exists():
        old = pd.read_parquet(nav_in)
        old.index = pd.to_datetime(old.index)
        merged = old.combine_first(wide)
        for c in wide.columns:
            merged[c] = wide[c].combine_first(merged[c]) if c in merged.columns else wide[c]
    else:
        merged = wide

    merged = merged.sort_index()
    merged.to_parquet(_write_processed_path("market_elite_nav_matrix.parquet"))
    with _LAKEHOUSE_MEM_LOCK:
        _LAKEHOUSE_MEM_CACHE["mtime"] = 0.0
    return {"status": "imported", "imported_funds": int(wide.shape[1]), "total_lakehouse_funds": int(merged.shape[1]), "rows": int(len(merged))}


def _merge_latest_trading_rules_into_meta(meta_df: pd.DataFrame) -> pd.DataFrame:
    """将本地最新 master/fund_trading_rules.parquet 的申购状态、单日限额与费率合入湖仓元数据。"""
    rul_p = runtime_paths.resolve_data_file("master/fund_trading_rules.parquet")
    if not rul_p.exists():
        return meta_df
    try:
        rul = pd.read_parquet(rul_p)
        rul["fund_code"] = rul["symbol"].astype(str).str.strip().str.zfill(6)
        keep_cols = [
            c for c in ("fund_code", "is_purchase_allowed", "daily_limit_amount", "est_total_operating_fee", "purchase_status")
            if c in rul.columns
        ]
        rul_sub = rul[keep_cols].drop_duplicates(subset=["fund_code"]).set_index("fund_code")
        out = meta_df.copy()
        out["fund_code"] = out["fund_code"].astype(str).str.strip().str.zfill(6)
        for col in keep_cols:
            if col == "fund_code":
                continue
            mapped = out["fund_code"].map(rul_sub[col])
            if col in out.columns:
                out[col] = mapped.combine_first(out[col])
            else:
                out[col] = mapped
        return out
    except Exception:
        return meta_df


def reclassify_and_clean_existing_lakehouse(prune_mini_sponsor: bool = False) -> Dict[str, Any]:
    """
    原位重分类并净化已有本地真净值湖仓（0 全量重爬，< 0.5 秒）：
      1. 合入最新 master/fund_trading_rules.parquet 的申购状态、单日限额与费率；
      2. 全量重跑 classify_fund_bucket_10 / is_index_style_fund（消灭假海外、假黄金、高费油气 FOF 进指数池）；
      3. 物理清除全部锁定期/滚动持有/外币份额/纯场内 ETF 列（从 nav_matrix 与 meta 同步移除）；
      4. 同步更新 market_elite_sync_status.json 并失效内存缓存。
    """
    nav_in = _read_elite_nav_path()
    meta_in = _read_elite_meta_path()
    if not nav_in.exists() or not meta_in.exists():
        return {"status": "not_initialized", "removed_count": 0, "remaining_count": 0}

    nav_df = pd.read_parquet(nav_in)
    nav_df.index = pd.to_datetime(nav_df.index)
    meta_df = pd.read_parquet(meta_in)
    meta_df["fund_code"] = meta_df["fund_code"].astype(str).str.strip().str.zfill(6)
    meta_df = _merge_latest_trading_rules_into_meta(meta_df)

    removed_codes: List[str] = []
    keep_rows: List[Dict[str, Any]] = []
    for _, row in meta_df.iterrows():
        rec = row.to_dict()
        fc = str(rec.get("fund_code", "")).strip().zfill(6)
        fn = str(rec.get("fund_name", "")).strip()
        ft = str(rec.get("fund_type", "")).strip()
        ps = str(rec.get("purchase_status", "")).strip()
        fee = rec.get("est_total_operating_fee", 0.6)
        try:
            fee_f = float(fee) if fee is not None and pd.notna(fee) else 0.6
        except Exception:
            fee_f = 0.6

        if fc not in nav_df.columns:
            removed_codes.append(fc)
            continue
        if is_lockup_or_banned_fund(fn, fc, ps):
            removed_codes.append(fc)
            continue

        b10 = classify_fund_bucket_10(ft, fn, fc, ps)
        if b10 in ("EXCLUDE_MONEY", "EXCLUDE_EXCHANGE_ONLY"):
            removed_codes.append(fc)
            continue

        if prune_mini_sponsor and ("发起" in fn) and (fc not in _ANCHOR_SEED_CODES):
            sc = rec.get("real_scale_yi")
            if sc is not None and pd.notna(sc) and float(sc) < 5.0:
                removed_codes.append(fc)
                continue

        cfg = BUCKET_10_CONFIG.get(b10, {})
        rec["bucket_10"] = b10
        rec["bucket_label"] = str(cfg.get("label", "核心配置"))
        rec["asset_class"] = str(cfg.get("asset_class", "equity"))
        rec["is_active_fund"] = bool(cfg.get("is_active", False)) or (b10 == "overseas_qdii" and not is_index_style_fund(ft, fn, b10, fee_f))
        rec["is_index_eligible"] = bool(is_index_style_fund(ft, fn, b10, fee_f))
        keep_rows.append(rec)

    clean_meta = pd.DataFrame(keep_rows).drop_duplicates(subset=["fund_code"]).reset_index(drop=True)
    keep_codes = [c for c in clean_meta["fund_code"].tolist() if c in nav_df.columns]
    clean_nav = nav_df[keep_codes].sort_index()
    clean_nav.index.name = "date"

    clean_nav.to_parquet(_write_processed_path("market_elite_nav_matrix.parquet"))
    clean_meta.to_parquet(_write_processed_path("market_elite_meta.parquet"), index=False)

    status_old = get_lakehouse_status()
    status_old["status"] = "ready"
    status_old["latest_date"] = str(clean_nav.index[-1])[:10] if len(clean_nav) else ""
    status_old["start_date"] = str(clean_nav.index[0])[:10] if len(clean_nav) else ""
    status_old["trading_days"] = int(len(clean_nav))
    status_old["elite_fund_count"] = int(len(clean_meta))
    status_old["active_fund_count"] = int(clean_meta["is_active_fund"].sum()) if "is_active_fund" in clean_meta.columns else 0
    status_old["index_eligible_count"] = int(clean_meta["is_index_eligible"].sum()) if "is_index_eligible" in clean_meta.columns else 0
    status_old["bucket_counts"] = {str(k): int(v) for k, v in clean_meta["bucket_10"].value_counts().items()}
    status_old["reclassified_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _write_processed_path("market_elite_sync_status.json").write_text(
        json.dumps(status_old, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    with _LAKEHOUSE_MEM_LOCK:
        _LAKEHOUSE_MEM_CACHE["mtime"] = 0.0
        _LAKEHOUSE_MEM_CACHE["nav"] = None
        _LAKEHOUSE_MEM_CACHE["meta"] = None

    return {
        "status": "cleaned",
        "removed_count": len(removed_codes),
        "removed_codes": removed_codes,
        "remaining_count": int(len(clean_meta)),
        "bucket_counts": status_old["bucket_counts"],
    }


def topup_targeted_lakehouse_funds(
    extra_codes: Optional[List[str]] = None,
    workers: int = 3,
    min_days: int = 360,
) -> Dict[str, Any]:
    """
    轻量定向补强本地精英湖仓（默认补齐 ~12 只高流动性大厂开放中短债 + ~6 只高限额开申大厂全球 QDII，耗时 < 8 秒）：
    通过静态 CDN pingzhongdata 拉取红利再投资复权净值并合入现有矩阵，随后自动执行一次原位重分类清洗。
    """
    nav_in = _read_elite_nav_path()
    meta_in = _read_elite_meta_path()
    if not nav_in.exists() or not meta_in.exists():
        return {"status": "not_initialized", "added": []}

    nav_df = pd.read_parquet(nav_in)
    nav_df.index = pd.to_datetime(nav_df.index)
    meta_df = pd.read_parquet(meta_in)
    meta_df["fund_code"] = meta_df["fund_code"].astype(str).str.strip().str.zfill(6)
    existing = set(nav_df.columns.astype(str).tolist())

    targets = [str(c).strip().zfill(6) for c in (extra_codes or _DEFAULT_TOPUP_CODES)]
    to_fetch = [c for c in dict.fromkeys(targets) if c not in existing]
    if not to_fetch:
        clean_res = reclassify_and_clean_existing_lakehouse()
        return {"status": "ok", "added": [], "failed": [], "clean": clean_res}

    # 从全市场目录表和规则表查静态元数据
    cat_map: Dict[str, Dict[str, Any]] = {}
    cat_p = runtime_paths.resolve_data_file("master/fund_catalog.parquet")
    if cat_p.exists():
        cat = pd.read_parquet(cat_p)
        cat["fund_code"] = cat["symbol"].astype(str).str.strip().str.zfill(6)
        cat_map = {r["fund_code"]: r.to_dict() for _, r in cat.drop_duplicates("fund_code").iterrows()}

    rul_map: Dict[str, Dict[str, Any]] = {}
    rul_p = runtime_paths.resolve_data_file("master/fund_trading_rules.parquet")
    if rul_p.exists():
        rul = pd.read_parquet(rul_p)
        rul["fund_code"] = rul["symbol"].astype(str).str.strip().str.zfill(6)
        rul_map = {r["fund_code"]: r.to_dict() for _, r in rul.drop_duplicates("fund_code").iterrows()}

    added_codes: List[str] = []
    failed_codes: List[str] = []
    new_meta_rows: List[Dict[str, Any]] = []
    cal_index = nav_df.index

    def _fetch_one(code: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        time.sleep(random.uniform(0.15, 0.35))
        try:
            return code, _fetch_pingzhongdata_adjusted_nav(code, timeout=10)
        except Exception:
            return code, None

    with ThreadPoolExecutor(max_workers=max(1, min(3, int(workers)))) as pool:
        results = list(pool.map(_fetch_one, to_fetch))

    for code, res in results:
        if res is None:
            failed_codes.append(code)
            continue
        df_f = res["df"]
        if len(df_f) < min_days:
            failed_codes.append(code)
            continue
        c_info = cat_map.get(code) or {}
        r_info = rul_map.get(code) or {}
        fn = str(r_info.get("fund_name") or c_info.get("fund_name") or code)
        ft = str(r_info.get("fund_type") or c_info.get("fund_type") or "")
        ps = str(r_info.get("purchase_status") or "开放申购")
        if is_lockup_or_banned_fund(fn, code, ps):
            failed_codes.append(code)
            continue

        s = df_f.set_index("date")["adj_nav"].astype(float)
        s = s[s.index >= cal_index[0]]
        if len(s) < min_days or float(s.iloc[0]) <= 0:
            failed_codes.append(code)
            continue
        s = s / float(s.iloc[0])
        reindexed = s.reindex(cal_index)
        fv = reindexed.first_valid_index()
        if fv is not None:
            reindexed.loc[fv:] = reindexed.loc[fv:].ffill(limit=5)
        nav_df[code] = reindexed

        fee_v = float(r_info.get("est_total_operating_fee") if pd.notna(r_info.get("est_total_operating_fee")) else 0.4)
        b10 = classify_fund_bucket_10(ft, fn, code, ps)
        cfg = BUCKET_10_CONFIG.get(b10, {})
        new_meta_rows.append({
            "fund_code": code,
            "fund_name": fn,
            "fund_type": ft,
            "bucket_10": b10,
            "bucket_label": str(cfg.get("label", "核心配置")),
            "asset_class": str(cfg.get("asset_class", "bond")),
            "is_active_fund": bool(cfg.get("is_active", False)),
            "is_index_eligible": bool(is_index_style_fund(ft, fn, b10, fee_v)),
            "is_purchase_allowed": bool(r_info.get("is_purchase_allowed", True)),
            "daily_limit_amount": float(r_info.get("daily_limit_amount") if pd.notna(r_info.get("daily_limit_amount")) else 1e10),
            "est_total_operating_fee": fee_v,
            "purchase_status": ps,
            "real_scale_yi": res.get("real_scale_yi"),
            "inception_date": res.get("inception_date", ""),
            "latest_nav_date": res.get("latest_nav_date", ""),
            "valid_trading_days": int(len(df_f)),
            "data_source": "eastmoney_pingzhongdata_adj",
        })
        added_codes.append(code)

    if new_meta_rows:
        meta_df = pd.concat([meta_df, pd.DataFrame(new_meta_rows)], ignore_index=True).drop_duplicates(subset=["fund_code"], keep="last")
        nav_df.index.name = "date"
        nav_df.to_parquet(_write_processed_path("market_elite_nav_matrix.parquet"))
        meta_df.to_parquet(_write_processed_path("market_elite_meta.parquet"), index=False)

    clean_res = reclassify_and_clean_existing_lakehouse()
    return {"status": "ok", "added": added_codes, "failed": failed_codes, "clean": clean_res}
