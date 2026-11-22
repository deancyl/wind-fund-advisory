# -*- coding: utf-8 -*-
"""
AGY2 Data Resilience Guard (G29 数据源健康中心与生命周期黑天鹅安检独立子模块)
=============================================================================
负责关键开放接口的真实探测健康度监控与 RED 熔断告警、激进调仓保护闸门、
大额分红除权防误报（消除假暴跌恐慌）、以及买入前四项硬安检。
严格控制在 350 行以内，杜绝主文件巨石膨胀。
"""

import threading
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple


def _build_default_channels() -> Dict[str, Dict[str, Any]]:
    return {
        "eastmoney_mnf": {
            "name": "东财清算净值与实时估值",
            "status": "UNKNOWN",
            "latency_ms": None,
            "last_success": "",
            "last_checked": "",
            "consecutive_failures": 0,
            "is_critical": True,
        },
        "tiantian_fundgz": {
            "name": "天天基金盘中实时估值",
            "status": "UNKNOWN",
            "latency_ms": None,
            "last_success": "",
            "last_checked": "",
            "consecutive_failures": 0,
            "is_critical": True,
        },
        "sina_fu": {
            "name": "新浪全球与场内ETF网关",
            "status": "UNKNOWN",
            "latency_ms": None,
            "last_success": "",
            "last_checked": "",
            "consecutive_failures": 0,
            "is_critical": False,
        },
        "eastmoney_push2": {
            "name": "东财大盘走廊Push2",
            "status": "UNKNOWN",
            "latency_ms": None,
            "last_success": "",
            "last_checked": "",
            "consecutive_failures": 0,
            "is_critical": False,
        },
        "usdcnh_fx": {
            "name": "离岸人民币与外盘行情",
            "status": "UNKNOWN",
            "latency_ms": None,
            "last_success": "",
            "last_checked": "",
            "consecutive_failures": 0,
            "is_critical": False,
        },
        "macro_rates": {
            "name": "人行DR007与中债收益率",
            "status": "UNKNOWN",
            "latency_ms": None,
            "last_success": "",
            "last_checked": "",
            "consecutive_failures": 0,
            "is_critical": False,
        },
    }


class DataSourceHealthRegistry:
    """关键开放接口真实健康度与熔断注册表（初始未探测标记 UNKNOWN，探测后动态更新 GREEN/YELLOW/RED）"""
    _LOCK = threading.Lock()
    _RED_FAILURE_THRESHOLD = 2
    _HEALTH_RECORDS: Dict[str, Dict[str, Any]] = _build_default_channels()

    @classmethod
    def reset(cls) -> None:
        """重置健康注册表为初始未探测状态（供测试隔离使用）。"""
        with cls._LOCK:
            cls._HEALTH_RECORDS = _build_default_channels()

    @classmethod
    def record_channel_ping(
        cls,
        channel_key: str,
        success: Optional[bool] = None,
        latency_ms: float = 100.0,
        *,
        ok: Optional[bool] = None,
    ) -> None:
        """记录单次真实网络探测结果；连续失败达到阈值自动进入 RED 熔断态。"""
        is_ok = bool(ok) if ok is not None else bool(success)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lat = round(max(0.0, float(latency_ms or 0.0)), 1)

        with cls._LOCK:
            if channel_key not in cls._HEALTH_RECORDS:
                cls._HEALTH_RECORDS[channel_key] = {
                    "name": channel_key,
                    "status": "UNKNOWN",
                    "latency_ms": None,
                    "last_success": "",
                    "last_checked": "",
                    "consecutive_failures": 0,
                    "is_critical": channel_key in ("eastmoney_mnf", "tiantian_fundgz"),
                }
            rec = cls._HEALTH_RECORDS[channel_key]
            rec["latency_ms"] = lat
            rec["last_checked"] = now_str
            if is_ok:
                rec["consecutive_failures"] = 0
                rec["status"] = "GREEN"
                rec["last_success"] = now_str
            else:
                fails = int(rec.get("consecutive_failures", 0)) + 1
                rec["consecutive_failures"] = fails
                rec["status"] = "RED" if fails >= cls._RED_FAILURE_THRESHOLD else "YELLOW"

    @classmethod
    def should_pause_aggressive_rebalance(cls) -> Tuple[bool, str]:
        """
        激进调仓熔断闸门：
        当关键估值/净值主源（eastmoney_mnf，或主源未就绪且 tiantian_fundgz 熔断，或 >=2 路通道 RED 熔断）
        处于 RED 熔断态时返回 (True, 原因)，防止基于断网/失真估值做出激进调仓。
        """
        with cls._LOCK:
            recs = {k: dict(v) for k, v in cls._HEALTH_RECORDS.items()}

        em_status = recs.get("eastmoney_mnf", {}).get("status", "UNKNOWN")
        tt_status = recs.get("tiantian_fundgz", {}).get("status", "UNKNOWN")
        red_channels = [
            f"{v.get('name', k)}({k})"
            for k, v in recs.items()
            if v.get("status") == "RED"
        ]

        if em_status == "RED":
            return (
                True,
                f"关键估值/净值主源【东财清算净值与实时估值(eastmoney_mnf)】已触发 RED 熔断，暂停激进调仓以防失真交易。",
            )
        if tt_status == "RED" and em_status != "GREEN":
            return (
                True,
                f"关键实时估值源【天天基金盘中实时估值(tiantian_fundgz)】已触发 RED 熔断且主源尚未确认健康，建议暂停激进调仓。",
            )
        if len(red_channels) >= 2:
            return (
                True,
                f"多路行情通道触发 RED 熔断（{', '.join(red_channels)}），已启用离线保护并暂停激进调仓。",
            )
        return (False, "")

    @classmethod
    def get_health_summary(cls) -> Dict[str, Any]:
        with cls._LOCK:
            channels_copy = {k: dict(v) for k, v in cls._HEALTH_RECORDS.items()}

        green_cnt = sum(1 for v in channels_copy.values() if v["status"] == "GREEN")
        yellow_cnt = sum(1 for v in channels_copy.values() if v["status"] == "YELLOW")
        red_cnt = sum(1 for v in channels_copy.values() if v["status"] == "RED")
        unknown_cnt = sum(1 for v in channels_copy.values() if v["status"] == "UNKNOWN")
        total_cnt = len(channels_copy)
        probed_cnt = total_cnt - unknown_cnt
        all_passed = (probed_cnt > 0 and red_cnt == 0 and yellow_cnt == 0 and green_cnt == total_cnt)

        if red_cnt > 0:
            badge = "🔴 核心行情源熔断告警·已启用离线湖仓保护"
        elif yellow_cnt > 0:
            badge = "🟡 部分行情接口降级运行中"
        elif green_cnt == total_cnt and total_cnt > 0:
            badge = "🟢 全部行情接口健康在线"
        elif green_cnt > 0:
            badge = f"🟢 已探测 {green_cnt}/{total_cnt} 路行情接口健康在线"
        else:
            badge = "⚪ 行情接口待首次探测"

        pause_flag, pause_reason = cls.should_pause_aggressive_rebalance()

        return {
            "all_passed": all_passed,
            "badge": badge,
            "green_count": green_cnt,
            "yellow_count": yellow_cnt,
            "red_count": red_cnt,
            "unknown_count": unknown_cnt,
            "probed_count": probed_cnt,
            "total_count": total_cnt,
            "pause_aggressive_rebalance": pause_flag,
            "pause_reason": pause_reason,
            "channels": channels_copy,
        }


def detect_dividend_or_split_false_alarm(
    prev_unit_nav: float,
    curr_unit_nav: float,
    prev_accum_nav: Optional[float] = None,
    curr_accum_nav: Optional[float] = None,
) -> Dict[str, Any]:
    """
    大额分红除权防误报：
    当单位净值跌超 3.0%，但累计净值变动在 ±1.0% 以内时，准确识别为“分红除权/份额折算”，
    自动拦截“假暴跌”与“深套止损”误报！
    """
    if prev_unit_nav <= 0.001 or curr_unit_nav <= 0.001:
        return {"is_dividend_ex": False, "is_safe": True}

    unit_chg_pct = (curr_unit_nav - prev_unit_nav) / prev_unit_nav * 100.0
    accum_chg_pct = 0.0
    has_accum = (prev_accum_nav is not None and curr_accum_nav is not None and prev_accum_nav > 0.001)

    if has_accum:
        accum_chg_pct = (curr_accum_nav - prev_accum_nav) / prev_accum_nav * 100.0

    # 判定逻辑：单位净值跌超 -3% 且累计净值未出现同步暴跌
    if unit_chg_pct <= -3.0 and has_accum and abs(accum_chg_pct) <= 1.0:
        return {
            "is_dividend_ex": True,
            "unit_chg_pct": round(unit_chg_pct, 2),
            "accum_chg_pct": round(accum_chg_pct, 2),
            "alert_tag": "🎉 大额分红除权（非实盘暴跌）",
            "action_advice": "基金除权现金已派发或转为再投资份额，资产总值未损，严禁割肉止损。",
        }

    return {"is_dividend_ex": False, "unit_chg_pct": round(unit_chg_pct, 2)}


def inspect_buy_candidate_safety(
    fund_code: str,
    fund_name: str = "",
    is_suspended: bool = False,
    daily_limit: float = 1e8,
    aum_million: float = 100.0,
    manager_departure_days: Optional[int] = None,
    fallback_code: str = "005561",
) -> Dict[str, Any]:
    """
    买入前四项硬安检：
    1. 是否处于暂停申购状态；
    2. 单日限额是否为 0；
    3. 基金最新规模是否低于 5,000 万清盘警戒线；
    4. 近 30 天是否发生核心基金经理离任。
    任一红线触发，自动拦截并输出 fallback 替代标的。
    """
    reasons = []
    if is_suspended:
        reasons.append("标的当前处于【暂停申购】状态")
    if daily_limit <= 0.0:
        reasons.append("标的当前【单日申购限额为 0 元】")
    if aum_million > 0 and aum_million < 50.0:
        reasons.append(f"基金规模仅 {aum_million:.1f} 百万元，触及【5,000万清盘警戒线】")
    if manager_departure_days is not None and manager_departure_days <= 30:
        reasons.append(f"近 {manager_departure_days} 天发生【核心基金经理离任】风险")

    if reasons:
        return {
            "is_cleared": False,
            "fund_code": fund_code,
            "fund_name": fund_name,
            "safety_verdict": "🚨 触发买前安全红线，已拦截执行",
            "blocking_reasons": reasons,
            "fallback_code": fallback_code,
            "action": f"建议暂停申购该标的，平移至备选标的 {fallback_code}",
        }

    return {
        "is_cleared": True,
        "fund_code": fund_code,
        "fund_name": fund_name,
        "safety_verdict": "🟢 通过四项前置安全体检",
        "blocking_reasons": [],
    }


class DataResilienceGuard:
    """面向对象的数据韧性与生命周期防护门面"""
    @staticmethod
    def health_summary() -> Dict[str, Any]:
        return DataSourceHealthRegistry.get_health_summary()

    @staticmethod
    def ping_channel(channel: str, success: Optional[bool] = None, latency: float = 100.0, *, ok: Optional[bool] = None) -> None:
        DataSourceHealthRegistry.record_channel_ping(channel, success=success, latency_ms=latency, ok=ok)

    @staticmethod
    def should_pause_aggressive_rebalance() -> Tuple[bool, str]:
        return DataSourceHealthRegistry.should_pause_aggressive_rebalance()

    @staticmethod
    def check_dividend(prev_u: float, curr_u: float, prev_a: Optional[float] = None, curr_a: Optional[float] = None) -> Dict[str, Any]:
        return detect_dividend_or_split_false_alarm(prev_u, curr_u, prev_a, curr_a)

    @staticmethod
    def pre_buy_inspect(code: str, **kwargs) -> Dict[str, Any]:
        return inspect_buy_candidate_safety(code, **kwargs)
