# -*- coding: utf-8 -*-
"""
Adversarial Verification Script for Milestone 1 (Features 4, 5, 6)
Reviewer: R8-M1-2
"""
import sys
import os
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "AGY2_FundAdvisory"))

from AGY2_FundAdvisory.data_loader import (
    EXPANDED_INDEX_CATALOG,
    INDEX_CATALOG_38,
    load_custom_watchlist,
    save_custom_watchlist,
    validate_and_fetch_code,
    calc_offline_2day_return,
    fetch_custom_realtime_indices,
    CUSTOM_WATCHLIST_FILE,
    PERSISTENT_CACHE_DIR,
)

def test_1_expanded_index_catalog():
    print("--- Test 1: EXPANDED_INDEX_CATALOG Verification ---")
    catalog = EXPANDED_INDEX_CATALOG
    assert len(catalog) >= 38, f"Expected >= 38 items, got {len(catalog)}"
    print(f"[PASS] Total items in catalog: {len(catalog)} (>= 38)")

    # Sector coverage
    sectors = {v.get("sector") for v in catalog.values()}
    print(f"[INFO] Distinct sectors ({len(sectors)}): {sectors}")
    assert len(sectors) >= 12, f"Expected >= 12 sectors, got {len(sectors)}"
    print(f"[PASS] Sector count {len(sectors)} >= 12")

    # Rule 16 Invariant: CSI Dividend strictly 000922, never 000015
    assert "000922" in catalog, "000922 (CSI Dividend) must be in catalog"
    csi_div = catalog["000922"]
    assert csi_div["name"] == "中证红利", f"000922 name must be 中证红利, got {csi_div['name']}"
    assert csi_div["code"] == "000922", f"000922 code mismatch"
    assert csi_div["fb_point"] > 5000, f"000922 point should be in 5000~6500 range, got {csi_div['fb_point']}"
    print(f"[PASS] 000922 is 中证红利 with point {csi_div['fb_point']}")

    if "000015" in catalog:
        sse_div = catalog["000015"]
        assert sse_div["name"] == "上证红利", f"000015 must be 上证红利, got {sse_div['name']}"
        assert sse_div["code"] == "000015"
        print(f"[PASS] 000015 is 上证红利 (strictly distinct from 中证红利)")

    # Schema integrity for all items
    required_keys = {"code", "name", "secid", "sym", "pinyin", "sector", "asset_type", "fb_point", "fb_chg"}
    for code, item in catalog.items():
        missing = required_keys - set(item.keys())
        assert not missing, f"Item {code} missing keys: {missing}"
        assert item["code"] == code, f"Key {code} != item code {item['code']}"
        assert len(item["name"]) > 0, f"Item {code} empty name"
        assert item["fb_point"] > 0, f"Item {code} invalid point {item['fb_point']}"
    print(f"[PASS] All {len(catalog)} catalog items satisfy required schema integrity")


def test_2_validate_and_fetch_code():
    print("\n--- Test 2: validate_and_fetch_code Adversarial Stress ---")
    # Non-digit inputs or length > 6 inputs
    invalid_inputs = ["1234567", "abcdef", "00030a", "------", "None", "!@#$%^"]
    for inp in invalid_inputs:
        res = validate_and_fetch_code(inp)
        assert res is None, f"Expected None for invalid input {repr(inp)}, got {res}"
    print("[PASS] All non-digit or >6 length inputs correctly returned None")

    # Shorter digit inputs are padded with zfill(6) by design in data_loader (e.g. '123' -> '000123')
    res_short = validate_and_fetch_code("123")
    print(f"[OBSERVATION] '123' padded via zfill(6) to '000123': {res_short['name'] if res_short else None}")


    # Space handling with valid code
    res_spaced = validate_and_fetch_code("  510300  ")
    assert res_spaced is not None, "Padded valid code '  510300  ' should be stripped and accepted"
    assert res_spaced["code"] == "510300"
    print(f"[PASS] Spaced input '  510300  ' parsed: {res_spaced['name']} ({res_spaced['code']})")

    # Valid known ETF code
    res_etf = validate_and_fetch_code("510300")
    assert res_etf is not None, "510300 should be valid"
    assert "300" in res_etf["name"] or "沪深" in res_etf["name"]
    assert res_etf["fb_point"] > 0
    print(f"[PASS] 510300 validated: {res_etf['name']}, point={res_etf['fb_point']}")

    # Non-existent 6 digit code
    res_fake = validate_and_fetch_code("999999")
    assert res_fake is None, f"Non-existent code 999999 should return None, got {res_fake}"
    print("[PASS] Non-existent code 999999 correctly returned None")


def test_3_persistence_and_cold_start():
    print("\n--- Test 3: Watchlist Persistence & Cold-Start Resilience ---")
    backup_file = PERSISTENT_CACHE_DIR / "custom_watchlist.json.bak_test"
    orig_existed = CUSTOM_WATCHLIST_FILE.exists()
    if orig_existed:
        shutil.copyfile(CUSTOM_WATCHLIST_FILE, backup_file)

    try:
        # Case A: Missing file cold start
        if CUSTOM_WATCHLIST_FILE.exists():
            CUSTOM_WATCHLIST_FILE.unlink()
        wl_cold = load_custom_watchlist()
        assert isinstance(wl_cold, dict)
        assert wl_cold.get("display_limit") == 6
        assert "000922" in wl_cold.get("selected_codes", [])
        assert CUSTOM_WATCHLIST_FILE.exists(), "Cold start should write default watchlist to disk"
        print("[PASS] Cold start successfully generated default watchlist and saved to disk")

        # Case B: Corrupted JSON file
        with open(CUSTOM_WATCHLIST_FILE, "w", encoding="utf-8") as f:
            f.write("{ invalid json corrupted content ...")
        wl_corrupt = load_custom_watchlist()
        assert isinstance(wl_corrupt, dict)
        assert wl_corrupt.get("display_limit") == 6
        assert "000922" in wl_corrupt.get("selected_codes", [])
        print("[PASS] Corrupted JSON cleanly fell back to default watchlist without raising exception")

        # Case C: Backward compatibility fields normalization
        partial_data = {
            "selected_symbols": ["000300", "000922"],
            "display_count": 8
        }
        with open(CUSTOM_WATCHLIST_FILE, "w", encoding="utf-8") as f:
            json.dump(partial_data, f)
        wl_norm = load_custom_watchlist()
        assert wl_norm["selected_codes"] == ["000300", "000922"]
        assert wl_norm["display_limit"] == 8
        print("[PASS] Backward compatibility field normalization (selected_symbols/display_count) verified")

        # Case D: Atomic save operation
        test_save = {
            "display_limit": 10,
            "selected_codes": ["000300", "000688", "000922", "518880"],
            "custom_items": {"510300": {"code": "510300", "name": "300ETF"}}
        }
        ok = save_custom_watchlist(test_save)
        assert ok is True
        wl_read = load_custom_watchlist()
        assert wl_read["display_limit"] == 10
        assert wl_read["display_count"] == 10
        assert wl_read["selected_codes"] == ["000300", "000688", "000922", "518880"]
        assert wl_read["selected_symbols"] == ["000300", "000688", "000922", "518880"]
        assert "510300" in wl_read["custom_items"]
        print("[PASS] Atomic save_custom_watchlist succeeded and read back correctly")

    finally:
        # Restore original file
        if orig_existed and backup_file.exists():
            shutil.copyfile(backup_file, CUSTOM_WATCHLIST_FILE)
            backup_file.unlink()
            print("[INFO] Original custom_watchlist.json restored")


def test_4_ui_details_in_gui_file():
    print("\n--- Test 4: UI Details in app_gui.py ---")
    gui_path = ROOT / "AGY2_FundAdvisory" / "app_gui.py"
    with open(gui_path, "r", encoding="utf-8") as f:
        gui_code = f.read()

    # Primary button CSS
    css_target = 'button[kind="primary"] *'
    assert css_target in gui_code, f"Missing '{css_target}' in app_gui.py CSS"
    assert '#ffffff !important' in gui_code, "Missing '#ffffff !important' in app_gui.py CSS"
    print("[PASS] Primary button white text CSS selector and color verified")

    # Tab 1 Step 1 text deduplication
    assert "<b>资产锚点：</b>" in gui_code
    assert "<b>权益中枢：</b>" in gui_code
    assert "<b>回撤上限：</b>" in gui_code
    # Verify no second "资产锚点" in caption below
    tab1_s1_idx = gui_code.find("<b>资产锚点：</b>")
    tab1_s1_snippet = gui_code[tab1_s1_idx:tab1_s1_idx + 800]
    second_anchor = tab1_s1_snippet.find("资产锚点", len("<b>资产锚点：</b>"))
    assert second_anchor == -1, "Found duplicate '资产锚点' in Tab 1 Step 1 area"
    print("[PASS] Tab 1 Step 1 card contains clean anchor info with zero duplicated anchor text")


def test_5_sidebar_dialog_controls():
    print("\n--- Test 5: Sidebar Settings Modal Popover Dialog ---")
    gui_path = ROOT / "AGY2_FundAdvisory" / "app_gui.py"
    with open(gui_path, "r", encoding="utf-8") as f:
        gui_code = f.read()

    # Popover exists
    assert 'with st.popover("⚙️"' in gui_code or 'with st.popover("⚙️' in gui_code
    print("[PASS] Popover settings dialog exists")

    # Slider min_value=3, max_value=15
    assert 'min_value=3' in gui_code
    assert 'max_value=15' in gui_code
    print("[PASS] Slider bounds [3, 15] verified")

    # Multiselect with search format func
    assert 'st.multiselect(' in gui_code
    assert '_fmt_option' in gui_code
    print("[PASS] Multiselect with pinyin/code/name search format func verified")

    # 6-digit input and validation
    assert 'txt_add_custom_code' in gui_code
    assert 'validate_and_fetch_code' in gui_code
    assert 'btn_add_custom_code' in gui_code
    print("[PASS] 6-digit code text input, add button, and validation verified")


if __name__ == "__main__":
    test_1_expanded_index_catalog()
    test_2_validate_and_fetch_code()
    test_3_persistence_and_cold_start()
    test_4_ui_details_in_gui_file()
    test_5_sidebar_dialog_controls()
    print("\n================ ALL REVIEW TESTS PASSED ================")
