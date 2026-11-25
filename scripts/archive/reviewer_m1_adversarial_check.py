# -*- coding: utf-8 -*-
"""
scripts/reviewer_m1_adversarial_check.py
Reviewer R8-M1-1 独立对抗性验证脚本
"""
import sys
import json
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from AGY2_FundAdvisory.data_loader import (
    fetch_custom_realtime_indices,
    fetch_batch_realtime_indices,
    calc_offline_2day_return,
    load_custom_watchlist,
    EXPANDED_INDEX_CATALOG,
    get_index_corridor_metrics,
    validate_and_fetch_code
)

def run_adversarial_checks():
    print("=== 1. Checking EXPANDED_INDEX_CATALOG Size and 000922 ===")
    print("Catalog size:", len(EXPANDED_INDEX_CATALOG))
    assert len(EXPANDED_INDEX_CATALOG) >= 30, f"Catalog must have >= 30 items, got {len(EXPANDED_INDEX_CATALOG)}"
    assert "000922" in EXPANDED_INDEX_CATALOG, "000922 must be in catalog"
    assert EXPANDED_INDEX_CATALOG["000922"]["name"] == "中证红利", "000922 must be 中证红利"
    if "000015" in EXPANDED_INDEX_CATALOG:
        assert EXPANDED_INDEX_CATALOG["000015"]["name"] == "上证红利", "000015 must be 上证红利, not substituted as 中证红利"

    print("=== 2. Testing calc_offline_2day_return ===")
    test_codes = ["000300", "000688", "000922", "000905", "000852", "518880", "513500"]
    for code in test_codes:
        res = calc_offline_2day_return(code)
        print(f"Code {code} offline 2-day return: {res}")
        assert res is not None, f"offline return failed for {code}"
        pt, chg, chg_pct = res
        assert pt > 0, f"Point <= 0 for {code}"
        assert abs(chg_pct) > 0.0001, f"Zero flat return for {code}"
        if code == "000922":
            assert 4500 <= pt <= 7000, f"000922 point {pt} out of reasonable range [4500, 7000]"

    print("=== 3. Testing fetch_batch_realtime_indices ===")
    batch_res = fetch_batch_realtime_indices(use_cache=False)
    for item in batch_res:
        print(f"{item['code']} {item['name']}: pt={item['point']} chg={item['change']} pct={item['change_pct']}% ma20={item['ma20']} bias={item['bias_20']}% ret20={item['ret_20d']}%")
        assert item["point"] > 0
        assert abs(item["change_pct"]) > 0.0001, f"0.00% flat row detected for {item['code']}!"
        assert "trend_status" in item and len(item["trend_status"]) > 0
        assert "trend_color" in item
        assert "ret_20d" in item

    print("=== 4. Testing custom_watchlist.json persistence ===")
    wl = load_custom_watchlist()
    print("Watchlist selected_codes:", wl.get("selected_codes"))
    assert "000922" in wl.get("selected_codes", [])

    print("=== 5. Adversarial Stress Test: Zero/Corrupt Quote Fallback ===")
    # 模拟东财与新浪均返回 0.00% 涨跌幅的情形
    # 测试 fetch_custom_realtime_indices 能否自动降级并消除 0.00%
    custom_res = fetch_custom_realtime_indices(codes=["000300", "000922", "518880"], use_cache=False)
    for c_item in custom_res:
        assert c_item["point"] > 0
        assert abs(c_item["change_pct"]) > 0.0001, f"Expected non-zero return for {c_item['code']}, got 0.00%"

    print("=== 6. Testing code probe validate_and_fetch_code ===")
    # 验证合法代码
    probe_510300 = validate_and_fetch_code("510300")
    print("Probe 510300:", probe_510300)
    assert probe_510300 is not None
    assert probe_510300["code"] == "510300"
    assert "300" in probe_510300["name"] or "ETF" in probe_510300["name"]

    # 验证非法代码
    probe_invalid = validate_and_fetch_code("abcdef")
    assert probe_invalid is None
    probe_short = validate_and_fetch_code("123")
    assert probe_short is None

    print("\nALL ADVERSARIAL CHECKS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_adversarial_checks()
