#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
scripts/verify_g35_channel_health_gate.py
----------------------------------------
AGY2 G35 专项门禁：
1. 验证 DataSourceHealthRegistry 状态机：
   - 3路GREEN + 3路UNKNOWN (无RED/YELLOW) 时，degraded_count == 0, is_degraded == False, all_passed == True
   - 任意1路进入 YELLOW / RED 时，degraded_count >= 1 且 degraded_names 准确捕获
   - mark_channel_standby 正常置为 STANDBY 且计入 healthy_count，不触发降级
2. 静态扫描断言：
   - data_loader.py 存在 record_channel_ping("usdcnh_fx", ...)
   - strategy_bridge.py 存在 record_channel_ping("macro_rates", ...)
   - portfolio_manager.py 存在 mark_channel_standby("tiantian_fundgz") 与 usdcnh_fx 探测
   - app_gui.py 不含 'st.warning(f"部分行情通道降级'
3. 真实拉取联调断言：
   - StrategyBridge.get_latest_market_snapshot() 真实上报 macro_rates
   - prefetch_batch_fund_quotes() 真实上报 eastmoney_mnf, sina_fu, eastmoney_push2, usdcnh_fx, tiantian_fundgz
   - 验证健康总结中 unknown_count == 0, healthy_count == total_count == 6
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGY2_DIR = ROOT / "AGY2_FundAdvisory"
BASE = AGY2_DIR if (AGY2_DIR / "app_gui.py").exists() else ROOT
for p in [str(ROOT), str(AGY2_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from data_resilience_guard import DataSourceHealthRegistry
from portfolio_manager import prefetch_batch_fund_quotes, clear_realtime_cache
from strategy_bridge import StrategyBridge


def verify_registry_logic():
    print("[G35] 1. 验证 DataSourceHealthRegistry 核心逻辑...")
    DataSourceHealthRegistry.reset()
    s0 = DataSourceHealthRegistry.get_health_summary()
    assert s0["unknown_count"] == 6, f"初始状态应有 6 路 UNKNOWN: {s0}"
    assert s0["degraded_count"] == 0, f"初始状态不应有降级: {s0}"
    assert s0["is_degraded"] is False, f"初始状态不应被标记为降级: {s0}"

    # 模拟 3 路 GREEN，其余 3 路 UNKNOWN（历史假降级场景）
    DataSourceHealthRegistry.record_channel_ping("eastmoney_mnf", ok=True, latency_ms=10.0)
    DataSourceHealthRegistry.record_channel_ping("sina_fu", ok=True, latency_ms=15.0)
    DataSourceHealthRegistry.record_channel_ping("eastmoney_push2", ok=True, latency_ms=20.0)

    s1 = DataSourceHealthRegistry.get_health_summary()
    assert s1["green_count"] == 3
    assert s1["unknown_count"] == 3
    assert s1["yellow_count"] == 0
    assert s1["red_count"] == 0
    assert s1["degraded_count"] == 0, f"仅未探测通道绝不能被判定为降级: {s1}"
    assert s1["is_degraded"] is False, f"未发生失败时 is_degraded 必须为 False: {s1}"
    assert s1["all_passed"] is True, f"已探测通道全绿且0失败时 all_passed 必须为 True: {s1}"

    # 模拟备用通道进入 STANDBY
    DataSourceHealthRegistry.mark_channel_standby("tiantian_fundgz")
    s2 = DataSourceHealthRegistry.get_health_summary()
    assert s2["standby_count"] == 1
    assert s2["healthy_count"] == 4
    assert s2["degraded_count"] == 0
    assert s2["is_degraded"] is False

    # 模拟 1 路发生真实失败进入 YELLOW
    DataSourceHealthRegistry.record_channel_ping("usdcnh_fx", ok=False, latency_ms=2000.0)
    s3 = DataSourceHealthRegistry.get_health_summary()
    assert s3["yellow_count"] == 1
    assert s3["degraded_count"] == 1
    assert s3["is_degraded"] is True
    assert any("人民币" in name or "外盘" in name or "usdcnh_fx" in name for name in s3["degraded_names"])
    assert any("usdcnh_fx" in ch for ch in s3["degraded_channels"])

    # 连续失败进入 RED 熔断
    DataSourceHealthRegistry.record_channel_ping("usdcnh_fx", ok=False, latency_ms=2000.0)
    s4 = DataSourceHealthRegistry.get_health_summary()
    assert s4["red_count"] == 1
    assert s4["degraded_count"] == 1
    assert s4["is_degraded"] is True

    print("  -> 状态机与降级判定逻辑完全正确！")


def verify_static_code_invariants():
    print("[G35] 2. 静态代码红线扫描...")
    dl_txt = (AGY2_DIR / "data_loader.py").read_text(encoding="utf-8")
    sb_txt = (AGY2_DIR / "strategy_bridge.py").read_text(encoding="utf-8")
    pm_txt = (AGY2_DIR / "portfolio_manager.py").read_text(encoding="utf-8")
    gui_txt = (BASE / "app_gui.py").read_text(encoding="utf-8")

    assert 'record_channel_ping("usdcnh_fx"' in dl_txt or 'record_channel_ping("usdcnh_fx"' in pm_txt, (
        "data_loader.py 或 portfolio_manager.py 必须包含 usdcnh_fx 真实健康上报"
    )
    assert 'record_channel_ping("macro_rates"' in sb_txt or 'record_channel_ping("macro_rates"' in dl_txt, (
        "strategy_bridge.py 或 data_loader.py 必须包含 macro_rates 真实健康上报"
    )
    assert 'mark_channel_standby("tiantian_fundgz")' in pm_txt, (
        "portfolio_manager.py 必须在无需补漏时将 tiantian_fundgz 标记为 STANDBY"
    )
    assert 'st.warning(f"部分行情通道降级' not in gui_txt, (
        "app_gui.py 严禁出现未经真实失败核验的 '部分行情通道降级' 黄色横幅！"
    )
    print("  -> 静态代码红线扫描 100% 达标！")


def verify_live_channel_health():
    print("[G35] 3. 真实行情与宏观快照联调验证...")
    DataSourceHealthRegistry.reset()
    clear_realtime_cache()

    snap = StrategyBridge.get_latest_market_snapshot(force_reload=True)
    assert snap is not None, "StrategyBridge snapshot 不应为空"

    quotes = prefetch_batch_fund_quotes(
        ["005561", "100032", "017436", "000216", "002351"],
        force_refresh=True
    )
    assert len(quotes) >= 5, f"预期拉取5只基金行情，实际返回: {len(quotes)}"

    summary = DataSourceHealthRegistry.get_health_summary()
    print("  -> 实际 6 路通道状态:", {k: v["status"] for k, v in summary["channels"].items()})

    assert summary["unknown_count"] == 0, f"6路通道不应再有任何留在 UNKNOWN: {summary['channels']}"
    assert summary["healthy_count"] == summary["total_count"], (
        f"在网络连通下全部通道应为健康 (GREEN 或 STANDBY): {summary}"
    )
    assert summary["degraded_count"] == 0, f"网络正常时不应有降级通道: {summary}"
    assert summary["is_degraded"] is False, f"网络正常时不应触发降级: {summary}"
    assert summary["all_passed"] is True, f"all_passed 必须为 True: {summary}"
    print("  -> 真实 6/6 通道联调验证全量通过！")


if __name__ == "__main__":
    verify_registry_logic()
    verify_static_code_invariants()
    verify_live_channel_health()
    print("\n✅ [SUCCESS] ALL G35 CHANNEL HEALTH INVARIANTS PASSED!")
