# -*- coding: utf-8 -*-
"""
scripts/test_challenger_r8_m1_empirical.py
Milestone 1 对抗性经验测试套件 (Challenger R8-M1-1)

重点测试维度：
1. 离线/周末/节假日行情回退 (Offline / Weekend / Holiday quote fallback)
   - Mock 网络故障与东财/新浪返回 0.00% 假平盘
   - 验证 fetch_batch_realtime_indices 与 fetch_custom_realtime_indices 成功调用 calc_offline_2day_return
   - 验证全市场走廊标的 0 假平盘 (no flat 0.00% rows)
2. 3 层卡片数据一致性与数学合理性 (3-Layer Card Sanity)
   - 点位正值性、尺度对齐（如黄金 ETF 与 AU9999 避免 -99% 乖离率失真）
   - PE/PB 分位数严格在 [0, 100] 区间
   - 近 20 日累计涨跌幅与 MA20 乖离率在合理区间 ([-50%, +100%])
   - 中证红利点位在合理区间 (5000+，锁死 000922)
3. 裁判文件完整性核验 (Referee Hashes Integrity)
4. UI 细节与自选持久化 (CSS Primary White, Watchlist JSON)
"""

import os
import sys
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# 确保项目根目录在 sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))
if str(WORKSPACE_ROOT / "AGY2_FundAdvisory") not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT / "AGY2_FundAdvisory"))

from AGY2_FundAdvisory.data_loader import (
    calc_offline_2day_return,
    get_index_corridor_metrics,
    fetch_custom_realtime_indices,
    fetch_batch_realtime_indices,
    fetch_or_calc_index_valuations,
    load_custom_watchlist,
    save_custom_watchlist,
    validate_and_fetch_code,
    EXPANDED_INDEX_CATALOG,
    _REALTIME_CORRIDOR_CACHE,
    IndexValuationEngine,
    CUSTOM_WATCHLIST_FILE
)


def run_tests():
    total_tests = 0
    passed_tests = 0
    failures = []

    def assert_test(condition, desc):
        nonlocal total_tests, passed_tests
        total_tests += 1
        if condition:
            passed_tests += 1
            print(f"  [PASS] {desc}")
        else:
            failures.append(desc)
            print(f"  [FAIL] {desc}")

    print("======================================================================")
    print("CHALLENGER R8-M1-1: ADVERSARIAL STRESS TEST SUITE")
    print("======================================================================")

    # --------------------------------------------------------------------------
    # 维度 1: 离线 / 周末 / 节假日行情回退 (Offline / Weekend Fallback)
    # --------------------------------------------------------------------------
    print("\n--- DIMENSION 1: Offline / Weekend / Holiday Quote Fallback ---")

    # 1.1 直接测试 calc_offline_2day_return 对核心指数与 ETF 的返回有效性
    core_codes = ["000300", "000688", "000922", "000905", "000852", "518880"]
    for code in core_codes:
        res = calc_offline_2day_return(code)
        assert_test(res is not None, f"calc_offline_2day_return('{code}') returns valid tuple")
        if res:
            pt, chg, chg_pct = res
            assert_test(pt > 0, f"calc_offline_2day_return('{code}') pt={pt} > 0")
            assert_test(abs(chg_pct) > 0.001, f"calc_offline_2day_return('{code}') chg_pct={chg_pct:.2f}% != 0.00% (no fake flat)")
            # 校验中证红利点位合理性
            if code == "000922":
                assert_test(4000 <= pt <= 7000, f"CSI Dividend 000922 pt={pt} in [4000, 7000] range (Rule 16)")

    # 1.2 模拟东财与新浪全面网络断网 / 超时故障 (Mock Network Down)
    _REALTIME_CORRIDOR_CACHE.clear()
    with patch("urllib.request.urlopen", side_effect=TimeoutError("Network unreachable")):
        batch_res = fetch_batch_realtime_indices(use_cache=False)
        assert_test(len(batch_res) == 6, f"Network down: fetch_batch_realtime_indices returns 6 items (got {len(batch_res)})")
        for item in batch_res:
            c = item["code"]
            pt = item["point"]
            pct = item["change_pct"]
            assert_test(pt > 0, f"Network down: {c} {item['name']} pt={pt} > 0")
            assert_test(abs(pct) > 0.001, f"Network down: {c} {item['name']} pct={pct:+.2f}% is non-zero (fallback active)")

    # 1.3 模拟东财接口返回 0.00% 假平盘 (Mock Weekend Flat 0.00% Response)
    # 东财接口在周末或休市时可能返回 f3 = 0 (change_pct = 0.00%)
    _REALTIME_CORRIDOR_CACHE.clear()
    mock_eastmoney_zero = {
        "data": {
            "diff": [
                {"f12": "000300", "f14": "沪深300", "f2": 411800, "f3": 0, "f4": 0},
                {"f12": "000688", "f14": "科创50", "f2": 130500, "f3": 0, "f4": 0},
                {"f12": "000922", "f14": "中证红利", "f2": 551100, "f3": 0, "f4": 0},
                {"f12": "000905", "f14": "中证500", "f2": 677000, "f3": 0, "f4": 0},
                {"f12": "000852", "f14": "中证1000", "f2": 666400, "f3": 0, "f4": 0},
                {"f12": "518880", "f14": "黄金ETF", "f2": 8450, "f3": 0, "f4": 0}
            ]
        }
    }
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_eastmoney_zero).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        batch_flat_tested = fetch_batch_realtime_indices(use_cache=False)
        assert_test(len(batch_flat_tested) == 6, "Weekend flat mock: batch returned 6 items")
        zero_pct_count = 0
        for item in batch_flat_tested:
            c = item["code"]
            pct = item["change_pct"]
            if abs(pct) < 1e-4:
                zero_pct_count += 1
            assert_test(abs(pct) > 0.001, f"Weekend flat mock: {c} {item['name']} auto-replaced with offline return {pct:+.2f}%")
        assert_test(zero_pct_count == 0, "Weekend flat mock: 0 items have flat 0.00% rows")

    # 1.4 全量 38+ 只目录标的离线回退压力测试 (All 38 Items Stress Test)
    _REALTIME_CORRIDOR_CACHE.clear()
    all_codes = list(EXPANDED_INDEX_CATALOG.keys())
    assert_test(len(all_codes) >= 30, f"EXPANDED_INDEX_CATALOG contains >= 30 items (found {len(all_codes)})")

    with patch("urllib.request.urlopen", side_effect=TimeoutError("Network offline")):
        all_res = fetch_custom_realtime_indices(codes=all_codes, use_cache=False)
        assert_test(len(all_res) == len(all_codes), f"Offline all 38: returned {len(all_res)}/{len(all_codes)} items")
        all_zero_count = 0
        for item in all_res:
            c = item["code"]
            pt = item["point"]
            pct = item["change_pct"]
            if abs(pct) < 1e-4:
                all_zero_count += 1
            if pt <= 0:
                print(f"    WARNING: {c} {item['name']} pt <= 0: {pt}")
        assert_test(all_zero_count == 0, f"Offline all 38: ZERO items have 0.00% flat return (zero count = {all_zero_count})")

    # --------------------------------------------------------------------------
    # 维度 2: 3 层卡片数据一致性与数学合理性 (3-Layer Card Sanity)
    # --------------------------------------------------------------------------
    print("\n--- DIMENSION 2: 3-Layer Card Consistency & Mathematical Sanity ---")

    # 2.1 行 1：点位正值性与 Flexbox 防压扁
    for item in batch_res:
        pt = item["point"]
        assert_test(pt > 0, f"Card Row 1: {item['code']} point {pt} is strictly positive")
        assert_test(item["change"] != 0, f"Card Row 1: {item['code']} change {item['change']} != 0")

    # 2.2 行 2：真实 PE/PB 估值分位数与近 20 日累计收益率
    val_map = fetch_or_calc_index_valuations(force_refresh=True)
    assert_test(isinstance(val_map, dict) and len(val_map) > 0, "Index valuation map successfully retrieved")

    for code in ["000300", "000905", "000852", "000922", "000688"]:
        item_v = val_map.get(code)
        assert_test(item_v is not None, f"Card Row 2: {code} has valuation entry")
        if item_v:
            pe = item_v.get("pe_ttm")
            pct = item_v.get("percentile")
            status = item_v.get("status")
            label = item_v.get("label")
            assert_test(pe is not None and 5.0 <= pe <= 150.0, f"Card Row 2: {code} PE-TTM={pe} in [5.0, 150.0]")
            assert_test(pct is not None and 0.0 <= pct <= 100.0, f"Card Row 2: {code} Percentile={pct}% in [0, 100]")
            assert_test(status in ["very_low", "low", "mid", "high", "very_high"], f"Card Row 2: {code} status='{status}' valid")
            assert_test(bool(label), f"Card Row 2: {code} label='{label}' non-empty")

    # 黄金与大宗避险 (无PE)
    gold_v = val_map.get("518880")
    assert_test(gold_v is not None, "Gold 518880 entry exists in valuation map")
    if gold_v:
        assert_test(gold_v["pe_ttm"] is None, "Gold 518880 pe_ttm is None (Commodity)")
        assert_test("大宗避险" in gold_v["label"], "Gold 518880 label denotes commodity hedge")

    # 2.3 行 3：MA20 趋势与 Bias20 尺度对齐测试 (防止 -99% 乖离率失真)
    # 测试黄金 ETF 518880 (现价 ~8.45) 与底层指数 AU9999 (~1440点) 的尺度自适应
    gold_metrics = get_index_corridor_metrics("518880", latest_pt=8.45)
    assert_test(gold_metrics["ma20"] > 0, f"Gold MA20={gold_metrics['ma20']} > 0")
    # 乖离率必须在 [-30%, +30%] 正常区间，绝不能是 -99%
    assert_test(-30.0 <= gold_metrics["bias_20"] <= 30.0, f"Gold Bias20={gold_metrics['bias_20']:.2f}% scale aligned (not -99%)")
    assert_test(-50.0 <= gold_metrics["ret_20d"] <= 50.0, f"Gold Ret20D={gold_metrics['ret_20d']:.2f}% in sane range")
    assert_test("🟢" in gold_metrics["trend_status"] or "🛡️" in gold_metrics["trend_status"], f"Gold trend status '{gold_metrics['trend_status']}' valid")

    # 测试各大宽基指数的 MA20 趋势与偏离
    for code in ["000300", "000905", "000852", "000922", "000688"]:
        m = get_index_corridor_metrics(code)
        assert_test(m["ma20"] > 0, f"MA20 for {code}: {m['ma20']} > 0")
        assert_test(-40.0 <= m["bias_20"] <= 40.0, f"Bias20 for {code}: {m['bias_20']:.2f}% in sane [-40%, +40%] bound")
        assert_test(-50.0 <= m["ret_20d"] <= 50.0, f"Ret20D for {code}: {m['ret_20d']:.2f}% in sane [-50%, +50%] bound")

    # 2.4 边界鲁棒性 (Edge Cases & Zero Division Defense)
    m_edge_zero = get_index_corridor_metrics("000300", latest_pt=0.0)
    assert_test(m_edge_zero["bias_20"] is not None, "Edge case latest_pt=0.0 handled without ZeroDivisionError")
    m_edge_none = get_index_corridor_metrics("000300", latest_pt=None)
    assert_test(m_edge_none["bias_20"] is not None, "Edge case latest_pt=None handled gracefully")
    m_edge_unknown = get_index_corridor_metrics("999999", latest_pt=100.0)
    assert_test(m_edge_unknown["ma20"] > 0, "Unknown code 999999 falls back to baseline formula")

    # --------------------------------------------------------------------------
    # 维度 3: 裁判文件哈希基线审计 (Referee Integrity)
    # --------------------------------------------------------------------------
    print("\n--- DIMENSION 3: Referee Files Hash Audit ---")
    import hashlib
    referee_files = {
        "AGY2_FundAdvisory/judge_engine.py": "AGY2_FundAdvisory/judge_engine.py",
        "AGY2_FundAdvisory/holdout_vault.py": "AGY2_FundAdvisory/holdout_vault.py",
        "AGY2_FundAdvisory/AGENT_SPEC.md": "AGY2_FundAdvisory/AGENT_SPEC.md",
        "tests/test_infra.py": "tests/test_infra.py"
    }
    # 运行 verify_referee_hashes.py
    import subprocess
    cmd_res = subprocess.run([sys.executable, "scripts/verify_referee_hashes.py"], capture_output=True, text=True)
    assert_test(cmd_res.returncode == 0, "scripts/verify_referee_hashes.py exited with 0")
    assert_test("ALL 4 READONLY REFEREE FILES ARE INTACT AND UNMODIFIED" in cmd_res.stdout, "Referee hashes stdout confirms all intact")

    # --------------------------------------------------------------------------
    # 维度 4: 自选走廊持久化与 UI 细节 (Watchlist & UI Details)
    # --------------------------------------------------------------------------
    print("\n--- DIMENSION 4: Custom Watchlist & UI Details ---")
    wl = load_custom_watchlist()
    assert_test(isinstance(wl, dict), "load_custom_watchlist returns dict")
    assert_test("000922" in wl["selected_codes"], "CSI Dividend 000922 present in default selected_codes")
    assert_test(3 <= wl.get("display_limit", 6) <= 15, "Watchlist display_limit in [3, 15]")

    # 自选探针测试 (validate_and_fetch_code)
    # 测试无效输入
    assert_test(validate_and_fetch_code("abc") is None, "validate_and_fetch_code('abc') returns None")
    assert_test(validate_and_fetch_code("12345") is None, "validate_and_fetch_code('12345') returns None")
    # 测试有效代码 510300
    res_510300 = validate_and_fetch_code("510300")
    assert_test(res_510300 is not None and res_510300["code"] == "510300", "validate_and_fetch_code('510300') succeeded")

    # 检查 app_gui.py 中 CSS 修复
    gui_path = WORKSPACE_ROOT / "AGY2_FundAdvisory" / "app_gui.py"
    with open(gui_path, "r", encoding="utf-8") as f:
        gui_src = f.read()

    assert_test('.val-very-low, .val-very_low' in gui_src, "CSS contains .val-very-low, .val-very_low union selector")
    assert_test('.val-very-high, .val-very_high' in gui_src, "CSS contains .val-very-high, .val-very_high union selector")
    assert_test('button[kind="primary"] *' in gui_src, "CSS contains button[kind=\"primary\"] * selector")
    assert_test('#ffffff !important' in gui_src, "CSS enforces #ffffff !important for primary button")
    assert_test('flex: 0 0 auto !important; white-space: nowrap !important;' in gui_src, "CSS enforces Rule 15 Flexbox anti-squash on corridor badges")

    # --------------------------------------------------------------------------
    # 总结与统计
    # --------------------------------------------------------------------------
    print("\n======================================================================")
    print(f"STRESS TEST SUMMARY: {passed_tests}/{total_tests} PASSED")
    if failures:
        print(f"FAILED TESTS ({len(failures)}):")
        for f in failures:
            print(f"  - {f}")
        return False
    else:
        print("ALL ADVERSARIAL STRESS TESTS PASSED SUCCESSFULLY! ZERO DEFECTS FOUND.")
        return True


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
