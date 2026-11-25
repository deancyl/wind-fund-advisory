# -*- coding: utf-8 -*-
"""
AGY2 Forward Audit Logger & OOS Verdict Tracker (G29 样本外前瞻验真独立子模块)
=============================================================================
负责每日投资裁决只读快照的冻结归档、防篡改保护与样本外真实未来收益/胜率打分。
严禁在缺失净值或缺失基准点位时伪造 1.25% / 3950.0 等虚假收益数字。
严格控制在 350 行以内，杜绝巨石文件膨胀。
"""

import os
import json
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Any, Optional
from runtime_paths import get_data_dir

_DEFAULT_PRIMARY_LOG_PATH = get_data_dir() / "forward_decision_audit.jsonl"
_DEFAULT_SECONDARY_LOG_PATH = get_data_dir() / "oos_verdict_ledger.jsonl"
PRIMARY_LOG_PATH = _DEFAULT_PRIMARY_LOG_PATH
SECONDARY_LOG_PATH = _DEFAULT_SECONDARY_LOG_PATH

HORIZON_BUCKETS = ("<30天观察期", "30天验真", "90天验真", "180天+验真")


def _resolve_primary_log() -> Path:
    return PRIMARY_LOG_PATH if PRIMARY_LOG_PATH != _DEFAULT_PRIMARY_LOG_PATH else (get_data_dir() / "forward_decision_audit.jsonl")


def _resolve_secondary_log() -> Path:
    return SECONDARY_LOG_PATH if SECONDARY_LOG_PATH != _DEFAULT_SECONDARY_LOG_PATH else (get_data_dir() / "oos_verdict_ledger.jsonl")


def _ensure_data_dir() -> None:
    _resolve_primary_log().parent.mkdir(parents=True, exist_ok=True)


def _classify_horizon_bucket(days_elapsed: int) -> str:
    if days_elapsed < 30:
        return "<30天观察期"
    if days_elapsed < 90:
        return "30天验真"
    if days_elapsed < 180:
        return "90天验真"
    return "180天+验真"


def _extract_numeric_nav(val: Any) -> Optional[float]:
    if val is None or val == "":
        return None
    if isinstance(val, (int, float)):
        f = float(val)
        return f if f > 0.0 else None
    if isinstance(val, dict):
        for k in ("official_nav", "gsz", "dwjz", "current_nav", "nav"):
            v = val.get(k)
            if v is not None and v != "":
                try:
                    f = float(v)
                    if f > 0.0:
                        return f
                except (TypeError, ValueError):
                    pass
        return None
    for k in ("official_nav", "gsz", "dwjz", "current_nav", "nav"):
        v = getattr(val, k, None)
        if v is not None and v != "":
            try:
                f = float(v)
                if f > 0.0:
                    return f
            except (TypeError, ValueError):
                pass
    return None


def load_decision_audit_log(filepath: Optional[Path] = None) -> List[Dict[str, Any]]:
    """加载历史已冻结的每日裁决快照列表"""
    p_log, s_log = _resolve_primary_log(), _resolve_secondary_log()
    target = filepath or p_log
    if not target.exists():
        if filepath is None and s_log.exists():
            target = s_log
        else:
            return []
    records = []
    try:
        with open(target, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if line_str:
                    records.append(json.loads(line_str))
    except Exception:
        pass
    return records


def append_daily_decision_snapshot(record: Dict[str, Any]) -> bool:
    """
    以只读追加模式写入当日投资裁决快照。
    严格执行同日不可篡改规则：同交易日仅写入 1 条原始快照，禁止事后修改覆盖！
    """
    _ensure_data_dir()
    t_date = str(record.get("date") or record.get("trade_date") or datetime.now().strftime("%Y-%m-%d"))

    # 查重：若当日已有记录，原样保护退出
    existing = load_decision_audit_log(_resolve_primary_log())
    for r in existing:
        r_d = str(r.get("date") or r.get("trade_date") or "")
        if r_d == t_date:
            return False

    clean_rec = {
        "date": t_date,
        "trade_date": t_date,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "market_regime": str(record.get("regime") or record.get("market_regime") or "NEUTRAL"),
        "verdict_action": str(record.get("verdict_action") or record.get("action") or "HOLD"),
        "target_weights": dict(record.get("target_weights") or {}),
        "fund_nav_snapshot": dict(record.get("fund_nav_snapshot") or {}),
        "c300_close": float(record.get("c300_close") or record.get("hs300_point") or 0.0),
        "hs300_point": float(record.get("c300_close") or record.get("hs300_point") or 0.0),
        "data_health_status": record.get("data_health_status", {"all_passed": True}),
    }

    for p in [_resolve_primary_log(), _resolve_secondary_log()]:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(clean_rec, ensure_ascii=False) + "\n")
    return True


def record_daily_verdict_if_needed(
    regime: str = "NEUTRAL",
    target_weights: Optional[Dict[str, float]] = None,
    fund_nav_map: Optional[Dict[str, float]] = None,
    hs300_point: float = 0.0,
    action_summary: str = "NORMAL",
) -> bool:
    """
    每日静默调用的快照冻结接口（耗时 < 5ms，无网络阻塞）
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    rec = {
        "date": today_str,
        "regime": regime,
        "verdict_action": action_summary,
        "target_weights": target_weights or {},
        "fund_nav_snapshot": fund_nav_map or {},
        "hs300_point": hs300_point,
        "data_health_status": {"verified": True},
    }
    return append_daily_decision_snapshot(rec)


def evaluate_forward_performance(
    current_nav_map: Optional[Dict[str, float]] = None,
    current_hs300: Optional[float] = None,
    as_of_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    遍历历史冻结日志，以当前真实市场真值核算样本外前瞻胜率、超额收益与分窗口统计。
    严禁缺净值时伪造 +1.25%，严禁未传 current_hs300 时伪造 3950.0 假超额。
    """
    logs = load_decision_audit_log()
    c_navs = current_nav_map or {}
    c_hs: Optional[float] = None
    if current_hs300 is not None:
        try:
            _chs = float(current_hs300)
            if _chs > 100.0:
                c_hs = _chs
        except (TypeError, ValueError):
            c_hs = None

    ref_date: date
    if as_of_date:
        try:
            ref_date = datetime.strptime(str(as_of_date)[:10], "%Y-%m-%d").date()
        except Exception:
            ref_date = datetime.now().date()
    else:
        ref_date = datetime.now().date()

    eval_records: List[Dict[str, Any]] = []
    bucket_acc: Dict[str, Dict[str, Any]] = {
        b: {"total": 0, "eval": 0, "bm_cnt": 0, "alpha_cnt": 0, "win": 0, "pnl": 0.0, "bm": 0.0, "exc": 0.0}
        for b in HORIZON_BUCKETS
    }

    evaluated_cnt = 0
    bm_evaluated_cnt = 0
    alpha_evaluated_cnt = 0
    pending_cnt = 0
    win_cnt = 0
    pnl_sum = 0.0
    bm_sum = 0.0
    excess_sum = 0.0

    for item in logs:
        rec_d = str(item.get("date") or item.get("trade_date") or "")
        try:
            rec_dt = datetime.strptime(rec_d[:10], "%Y-%m-%d").date()
            days_elapsed = max(0, (ref_date - rec_dt).days)
        except Exception:
            days_elapsed = 0
        horizon_bucket = _classify_horizon_bucket(days_elapsed)
        b_stat = bucket_acc[horizon_bucket]
        b_stat["total"] += 1

        weights = item.get("target_weights") or {}
        base_navs = item.get("fund_nav_snapshot") or {}
        base_hs = float(item.get("c300_close", 0.0) or item.get("hs300_point", 0.0) or 0.0)

        # 1. 实算组合前瞻收益（严禁缺净值时伪造 1.25%）
        w_pnl = 0.0
        w_total = 0.0
        for code, w in weights.items():
            init_n = _extract_numeric_nav(base_navs.get(code))
            curr_n = _extract_numeric_nav(c_navs.get(code))
            if init_n is not None and curr_n is not None and init_n > 0.0:
                ret = (curr_n - init_n) / init_n * 100.0
                w_val = float(w)
                w_pnl += ret * w_val
                w_total += w_val

        port_ret: Optional[float]
        if w_total > 0.01:
            port_ret = round(w_pnl / w_total, 2)
            evaluated_cnt += 1
            pnl_sum += port_ret
            b_stat["eval"] += 1
            b_stat["pnl"] += port_ret
        else:
            port_ret = None
            pending_cnt += 1

        # 2. 实算同期沪深300基准收益（严禁未传入 current_hs300 时伪造 3950.0 / 0.50%）
        bm_ret: Optional[float] = None
        if c_hs is not None and base_hs > 100.0:
            bm_ret = round((c_hs - base_hs) / base_hs * 100.0, 2)
            bm_evaluated_cnt += 1
            bm_sum += bm_ret
            b_stat["bm_cnt"] += 1
            b_stat["bm"] += bm_ret

        # 3. 实算超额 Alpha 与胜负裁定
        excess: Optional[float] = None
        is_win: Optional[bool] = None
        if port_ret is None:
            eval_status = "PENDING_NAV"
        elif bm_ret is None:
            eval_status = "PENDING_BENCHMARK"
        else:
            eval_status = "EVALUATED"
            excess = round(port_ret - bm_ret, 2)
            is_win = excess >= 0.0
            alpha_evaluated_cnt += 1
            excess_sum += excess
            b_stat["alpha_cnt"] += 1
            b_stat["exc"] += excess
            if is_win:
                win_cnt += 1
                b_stat["win"] += 1

        eval_records.append({
            "裁决日期": rec_d,
            "市场定调": item.get("market_regime", "NEUTRAL"),
            "已过天数": days_elapsed,
            "验真窗口": horizon_bucket,
            "前瞻收益(%)": f"{port_ret:+.2f}%" if port_ret is not None else "待补净值",
            "同期沪深300(%)": f"{bm_ret:+.2f}%" if bm_ret is not None else "待补基准",
            "超额Alpha(%)": f"{excess:+.2f}%" if excess is not None else "--",
            "胜负裁定": ("🟢 胜" if is_win else "🔴 负") if is_win is not None else "⏳ 待验真",
            "date": rec_d,
            "days_elapsed": days_elapsed,
            "horizon_bucket": horizon_bucket,
            "eval_status": eval_status,
            "portfolio_return_pct": port_ret,
            "benchmark_return_pct": bm_ret,
            "excess_alpha_pct": excess,
        })

    horizon_stats: Dict[str, Dict[str, Any]] = {}
    for b_name, st in bucket_acc.items():
        horizon_stats[b_name] = {
            "sample_count": st["total"],
            "evaluated_count": st["eval"],
            "pending_count": st["total"] - st["eval"],
            "avg_forward_return_pct": round(st["pnl"] / st["eval"], 2) if st["eval"] > 0 else None,
            "avg_hs300_return_pct": round(st["bm"] / st["bm_cnt"], 2) if st["bm_cnt"] > 0 else None,
            "excess_alpha_pct": round(st["exc"] / st["alpha_cnt"], 2) if st["alpha_cnt"] > 0 else None,
            "win_rate_pct": round(st["win"] / st["alpha_cnt"] * 100.0, 1) if st["alpha_cnt"] > 0 else None,
        }

    cnt = len(logs)
    avg_fwd = round(pnl_sum / evaluated_cnt, 2) if evaluated_cnt > 0 else 0.0
    avg_bm = round(bm_sum / bm_evaluated_cnt, 2) if bm_evaluated_cnt > 0 else 0.0
    excess_alpha = round(excess_sum / alpha_evaluated_cnt, 2) if alpha_evaluated_cnt > 0 else 0.0
    win_rate = round(win_cnt / alpha_evaluated_cnt * 100.0, 1) if alpha_evaluated_cnt > 0 else 0.0

    if cnt == 0:
        overall_status = "EMPTY"
        summary_str = "💡 尚未积累历史样本外快照，系统已开启每日 15:00 只读裁决冻结，未来真实行情将逐日在此打分验真。"
    elif evaluated_cnt == 0:
        overall_status = "PENDING_NAV"
        summary_str = f"已冻结 {cnt} 期裁决快照（待补基金净值/行情 {pending_cnt} 期），缺失净值期间严禁虚报前瞻收益。"
    elif alpha_evaluated_cnt == 0:
        overall_status = "PENDING_BENCHMARK"
        summary_str = f"已实算 {evaluated_cnt}/{cnt} 期前瞻收益（均值 {avg_fwd:+.2f}%），尚未传入最新沪深300点位，暂不计算基准超额。"
    else:
        overall_status = "EVALUATED"
        summary_str = (
            f"已累计追踪 {cnt} 期样本外实盘裁决（可验真 {alpha_evaluated_cnt} 期 / 待验真 {cnt - alpha_evaluated_cnt} 期），"
            f"平均前瞻收益 {avg_fwd:+.2f}%，相对沪深300超额 Alpha {excess_alpha:+.2f}%，胜率 {win_rate:.1f}%。"
        )

    return {
        "sample_count": cnt,
        "evaluated_count": evaluated_cnt,
        "alpha_evaluated_count": alpha_evaluated_cnt,
        "pending_count": pending_cnt,
        "eval_status": overall_status,
        "portfolio_return_pct": avg_fwd if evaluated_cnt > 0 else None,
        "avg_forward_return_pct": avg_fwd,
        "avg_hs300_return_pct": avg_bm,
        "excess_alpha_pct": excess_alpha,
        "win_rate_pct": win_rate,
        "horizon_stats": horizon_stats,
        "status_summary": summary_str,
        "eval_records": eval_records,
    }


class OOSVerdictTracker:
    """面向对象的 OOS 前瞻验真追踪器 (双重兼容门面)"""
    @staticmethod
    def append_snapshot(record: Dict[str, Any]) -> bool:
        return append_daily_decision_snapshot(record)

    @staticmethod
    def record_if_needed(**kwargs) -> bool:
        return record_daily_verdict_if_needed(**kwargs)

    @staticmethod
    def load_logs() -> List[Dict[str, Any]]:
        return load_decision_audit_log()

    @staticmethod
    def evaluate(nav_map: Optional[Dict[str, float]] = None, hs300: Optional[float] = None) -> Dict[str, Any]:
        return evaluate_forward_performance(nav_map, hs300)
