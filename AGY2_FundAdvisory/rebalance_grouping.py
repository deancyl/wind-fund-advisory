# -*- coding: utf-8 -*-
"""
纯 Python 调仓意图分组与当日下单打卡持久化模块（严禁依赖第三方UI框架）。
同时被 Streamlit 前端与 FastAPI 跨端后端 api_server.py 共同复用。
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

import runtime_paths
_DEFAULT_CHECKLIST_FILE = runtime_paths.get_data_dir() / "daily_execution_checklist.json"
CHECKLIST_FILE = _DEFAULT_CHECKLIST_FILE

def _active_checklist_file() -> Path:
    return CHECKLIST_FILE if CHECKLIST_FILE != _DEFAULT_CHECKLIST_FILE else (runtime_paths.get_data_dir() / "daily_execution_checklist.json")


class IntentGroup(list):
    """意图分组容器：兼容列表迭代与字典键值读取。"""
    def __init__(self, items: List[Dict[str, Any]], title: str = "", summary_text: str = "", **kwargs):
        super().__init__(items)
        self.title = str(title)
        self.summary_text = str(summary_text)
        self.items = list(items)
        self.meta = dict(kwargs)

    @property
    def count(self) -> int:
        return len(self)

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, str):
            if key == "items": return self.items
            if key == "count": return len(self)
            if key == "title": return self.title
            if key == "summary_text": return self.summary_text
            if key in self.meta: return self.meta[key]
            raise KeyError(key)
        return super().__getitem__(key)

    def get(self, key: str, default: Any = None) -> Any:
        return self[key] if key in ("items", "count", "title", "summary_text") else self.meta.get(key, default)

    def __contains__(self, item: Any) -> bool:
        return True if (isinstance(item, str) and (item in ("items", "count", "title", "summary_text") or item in self.meta)) else super().__contains__(item)

    def keys(self) -> List[str]:
        return ["title", "count", "summary_text", "items"] + list(self.meta.keys())


def group_rebalance_orders_by_intent(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """按操作意图聚合，保证 100% 项数与金额守恒；title 禁止携带任何图标。"""
    tail_items, c_items, core_items, hold_items = [], [], [], []
    for it in items:
        code = str(it.get("fund_code", "") or it.get("code", "")).strip()
        act = str(it.get("action", "") or it.get("direction", "")).upper()
        act_text = str(it.get("action_text", "") or "")
        notes = str(it.get("notes", "") or it.get("reason", ""))
        amt = float(it.get("diff_amount") or it.get("amount") or 0.0)
        mv = float(it.get("market_value") if it.get("market_value") is not None else abs(amt))

        is_c = bool(
            it.get("is_c_replace") or "C转A" in act_text or "C转A" in notes or "C转A" in act
            or (code in ("011612", "011613", "013841") and ("置换" in act_text or "置换" in notes))
        )
        if is_c:
            c_items.append(it)
            continue

        is_hold = bool(
            act == "HOLD" or "维持" in act_text or "维持" in act or "HOLD" in act_text
            or (abs(amt) < 1e-4 and "清仓" not in act_text and not it.get("is_tail"))
        )
        if is_hold:
            hold_items.append(it)
            continue

        is_tail = bool(
            it.get("is_tail") or "清仓" in act_text or "扫尾" in act_text or "归拢" in act_text or "归拢" in notes
            or (("SELL" in act or "减仓" in act) and mv < 200.0)
        )
        if is_tail:
            tail_items.append(it)
            continue

        core_items.append(it)

    tot_tail_cash = sum(abs(float(x.get("diff_amount") or x.get("amount") or x.get("market_value") or 0.0)) for x in tail_items)
    c_sell_cnt = sum(1 for x in c_items if float(x.get("diff_amount") or x.get("amount") or 0.0) < 0)
    c_pair_cnt = c_sell_cnt if c_sell_cnt > 0 else (len(c_items) // 2)

    tail_grp = IntentGroup(
        tail_items,
        title=f"清理尾仓 ({len(tail_items)}只)",
        summary_text=f"清扫 {len(tail_items)} 只免赎碎片尾仓，回收 ¥{tot_tail_cash:,.2f}" if tail_items else "无尾仓",
        total_recovered_cash=round(tot_tail_cash, 2)
    )
    c_grp = IntentGroup(
        c_items,
        title=f"C转A省费 ({c_pair_cnt}组)",
        summary_text=f"将 {c_pair_cnt} 只满30天免赎 C 类置换为 A 类，年省销售服务费约 0.40%" if c_items else "无C转A项",
        saved_fee_pct_annually=0.40,
        c_sell_count=c_pair_cnt
    )
    core_grp = IntentGroup(core_items, title=f"核心调仓 ({len(core_items)}只)", summary_text=f"核心持仓再平衡 ({len(core_items)} 只)" if core_items else "核心持仓平衡")
    hold_grp = IntentGroup(hold_items, title=f"维持持仓 ({len(hold_items)}只)", summary_text=f"{len(hold_items)} 只处于缓冲带内，免折腾")

    is_all_hold = (len(tail_items) == 0 and len(c_items) == 0 and len(core_items) == 0)
    return {
        "tail_sweep": tail_grp, "c_replace": c_grp, "core_trades": core_grp, "buffer_hold": hold_grp,
        "tail_items": tail_items, "c_items": c_items, "core_items": core_items, "hold_items": hold_items,
        "tail_total_cash": round(tot_tail_cash, 2), "total_count": len(items), "is_empty": (len(items) == 0 or is_all_hold)
    }


def load_daily_checkin(date_str: str = "") -> Dict[str, Any]:
    """读取指定交易日的下单打卡状态。"""
    day = date_str or datetime.now().strftime("%Y-%m-%d")
    chk_f = _active_checklist_file()
    if not chk_f.exists():
        return {"date": day, "checked_codes": {}}
    try:
        data = json.loads(chk_f.read_text(encoding="utf-8"))
        return data.get(day, {"date": day, "checked_codes": {}})
    except Exception:
        return {"date": day, "checked_codes": {}}


def save_daily_checkin(fund_code: str, action: str, amount: float, checked: bool, date_str: str = "", **kwargs) -> Dict[str, Any]:
    """保存或更新某只基金的下单打卡状态。"""
    if not date_str and "target_date_str" in kwargs:
        date_str = str(kwargs["target_date_str"] or "")
    day = date_str or datetime.now().strftime("%Y-%m-%d")
    chk_f = _active_checklist_file()
    chk_f.parent.mkdir(parents=True, exist_ok=True)
    all_data = {}
    if chk_f.exists():
        try:
            all_data = json.loads(chk_f.read_text(encoding="utf-8"))
        except Exception:
            all_data = {}
    bucket = all_data.get(day, {"date": day, "checked_codes": {}})
    if "checked_codes" not in bucket:
        bucket["checked_codes"] = {}

    if checked:
        bucket["checked_codes"][str(fund_code)] = {
            "action": str(action),
            "amount": round(float(amount), 2),
            "checked_at": datetime.now().strftime("%H:%M:%S")
        }
    else:
        bucket["checked_codes"].pop(str(fund_code), None)
    all_data[day] = bucket
    # 仅保留最近 30 天记录
    keep_days = sorted(all_data.keys())[-30:]
    all_data = {k: all_data[k] for k in keep_days}
    chk_f.write_text(json.dumps(all_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return bucket
