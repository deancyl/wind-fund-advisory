# -*- coding: utf-8 -*-
"""
自选板块持久化与多市场统一行情路由器（支持场内 ETF、宽基/行业指数、场外基金）。
"""
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

import runtime_paths
CURRENT_DIR = runtime_paths.get_bundle_root()
WORKSPACE_ROOT = runtime_paths.get_workspace_root()
_DEFAULT_WATCHLIST_FILE = runtime_paths.get_data_dir() / "custom_sector_watchlist.json"
WATCHLIST_FILE = _DEFAULT_WATCHLIST_FILE
ALT_WATCHLIST_FILE = CURRENT_DIR / "data" / "custom_sector_watchlist.json"

def _active_watchlist_file() -> Path:
    return WATCHLIST_FILE if WATCHLIST_FILE != _DEFAULT_WATCHLIST_FILE else (runtime_paths.get_data_dir() / "custom_sector_watchlist.json")

DEFAULT_SECTORS: List[Dict[str, str]] = [
    {"code": "161725", "name": "中证白酒", "asset_type": "fund"},
    {"code": "512480", "name": "半导体ETF", "asset_type": "etf"},
    {"code": "513180", "name": "恒生科技ETF", "asset_type": "etf"},
    {"code": "005561", "name": "红利低波", "asset_type": "fund"},
    {"code": "511260", "name": "十年国债ETF", "asset_type": "etf"},
]


def infer_asset_type(code: str, name: str = "") -> str:
    c = str(code).strip().upper()
    if c.startswith(("H", "SH", "SZ", "GB_", "399", "000300", "000688", "000922", "000905", "000852")):
        return "index"
    if c.startswith(("51", "56", "58", "159")) or ("ETF" in str(name).upper() and "联接" not in str(name)):
        return "etf"
    return "fund"


def load_sector_watchlist() -> List[Dict[str, str]]:
    targets = [_active_watchlist_file()]
    if not os.environ.get("AGY2_DATA_DIR", "").strip():
        targets.append(ALT_WATCHLIST_FILE)
    for target in targets:
        if target and target.exists():
            try:
                data = json.loads(target.read_text(encoding="utf-8"))
                if isinstance(data, list) and data:
                    return data
            except Exception:
                pass
    return [dict(x) for x in DEFAULT_SECTORS]


def save_sector_watchlist(items: List[Dict[str, str]]) -> None:
    content = json.dumps(items, ensure_ascii=False, indent=2)
    targets = [_active_watchlist_file()]
    if not os.environ.get("AGY2_DATA_DIR", "").strip():
        targets.append(ALT_WATCHLIST_FILE)
    for target in targets:
        if target:
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            except Exception:
                pass


def add_sector_item(code: str, name: str) -> List[Dict[str, str]]:
    items = load_sector_watchlist()
    clean_c = str(code).strip()
    if clean_c and not any(x["code"] == clean_c for x in items):
        items.append({
            "code": clean_c,
            "name": str(name).strip()[:12],
            "asset_type": infer_asset_type(clean_c, name)
        })
        save_sector_watchlist(items)
    return items


def remove_sector_item(code: str) -> List[Dict[str, str]]:
    clean_c = str(code).strip()
    items = [x for x in load_sector_watchlist() if x.get("code") != clean_c]
    save_sector_watchlist(items)
    return items


def reset_sector_watchlist() -> List[Dict[str, str]]:
    items = [dict(x) for x in DEFAULT_SECTORS]
    save_sector_watchlist(items)
    return items


def fetch_sector_change_pct(item: Dict[str, str]) -> float:
    try:
        from portfolio_manager import fetch_realtime_index_quote, fetch_realtime_fund_quote
    except ImportError:
        for p in [str(WORKSPACE_ROOT), str(WORKSPACE_ROOT / "AGY2_FundAdvisory")]:
            if p not in sys.path:
                sys.path.insert(0, p)
        from portfolio_manager import fetch_realtime_index_quote, fetch_realtime_fund_quote

    code = str(item.get("code", "")).strip()
    atype = item.get("asset_type") or infer_asset_type(code, item.get("name", ""))
    try:
        if atype in ("etf", "index"):
            q = fetch_realtime_index_quote(code, use_cache=True) or {}
            if isinstance(q, dict):
                return round(float(q.get("change_pct", 0.0) or 0.0), 2)
            return round(float(getattr(q, "change_pct", 0.0) or 0.0), 2)
        q_f = fetch_realtime_fund_quote(code, use_cache=True)
        if q_f:
            if isinstance(q_f, dict):
                if q_f.get("is_official_nav", False):
                    val = q_f.get("official_chg_pct")
                    if val is not None:
                        return round(float(val), 2)
                val = q_f.get("est_gszzl") or q_f.get("gszzl") or q_f.get("official_chg_pct") or 0.0
                return round(float(val), 2)
            else:
                if getattr(q_f, "is_official_nav", False):
                    val = getattr(q_f, "official_chg_pct", None)
                    if val is not None:
                        return round(float(val), 2)
                val = getattr(q_f, "est_gszzl", None) or getattr(q_f, "gszzl", 0.0) or getattr(q_f, "official_chg_pct", 0.0) or 0.0
                return round(float(val), 2)
        return 0.0
    except Exception:
        return 0.0
