# -*- coding: utf-8 -*-
"""
AGY2_FundAdvisory/tests/test_challenger_r8_m1_2_stress.py
Empirical Challenger R8-M1-2 Adversarial Stress Testing Suite

Verification Dimensions:
1. Rule 16 Invariant & Catalog Integrity:
   - CSI Dividend is strictly '000922' with point in 5000~6500 range, rejecting '000015'
   - EXPANDED_INDEX_CATALOG contains at least 38 valid entries across >= 12 sectors
   - validate_and_fetch_code with edge-case invalid codes and valid 6-digit codes
2. Offline Fallback & Weekend Flat Scale Consistency:
   - Off-market / offline fallback must NOT inject 12189.99 (H00922 total return) into 000922 price point
   - Weekend flat fallback must NOT inject spot gold +40.33 yuan change into 8-yuan 518880 ETF
3. Watchlist Cold-Start & Corruption Resistance:
   - Missing, empty, or corrupted JSON falls back safely to default symbols without unhandled exception
   - Save & reload round-trip strictly preserves selection order and custom added entries
4. AppTest Geometry & Visual Integrity:
   - Streamlit AppTest verifies .val-very-low, .val-very_low, .val-very-high, .val-very_high in DOM
   - button[kind="primary"] styles enforce #ffffff !important
   - Sidebar layout collision and overflow resistance
5. Referee hash baseline check
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from streamlit.testing.v1 import AppTest

CURRENT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = CURRENT_DIR.parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))
if str(CURRENT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR.parent))

from AGY2_FundAdvisory import data_loader
from AGY2_FundAdvisory.data_loader import (
    EXPANDED_INDEX_CATALOG,
    INDEX_CATALOG_38,
    load_custom_watchlist,
    save_custom_watchlist,
    validate_and_fetch_code,
    calc_offline_2day_return,
    fetch_custom_realtime_indices,
    fetch_batch_realtime_indices,
    get_index_corridor_metrics,
    fetch_or_calc_index_valuations
)

GUI_FILE = str(CURRENT_DIR.parent / "app_gui.py")


# ==============================================================================
# Suite 1: Rule 16 Invariant & Catalog Integrity
# ==============================================================================

class TestRule16AndCatalogIntegrity:
    """对抗性检验 1: Rule 16 基准真实性红线与 38+ 目录完整性"""

    def test_csi_dividend_000922_rule16_invariant(self):
        """
        Rule 16 铁律：
        1. 中证红利必须且仅允许映射为 000922，严禁偷换为上证红利 000015；
        2. 点位必须处于 5000~6500 点合理区间，严禁展示 3200~3300 点（000015 点位）。
        """
        # 1. 目录中映射断言
        assert "000922" in EXPANDED_INDEX_CATALOG, "EXPANDED_INDEX_CATALOG 必须包含 000922"
        zzhl_meta = EXPANDED_INDEX_CATALOG["000922"]
        assert zzhl_meta["name"] == "中证红利", f"000922 名称必须为 '中证红利', 实际为 {zzhl_meta['name']}"
        assert zzhl_meta["secid"] == "1.000922"

        # 000015 绝不能是中证红利
        if "000015" in EXPANDED_INDEX_CATALOG:
            szhl_meta = EXPANDED_INDEX_CATALOG["000015"]
            assert szhl_meta["name"] != "中证红利", "000015 严禁命名为 '中证红利'"
            assert szhl_meta["name"] == "上证红利"

        # 2. 估值分位字典中的基准映射断言
        val_map = fetch_or_calc_index_valuations(force_refresh=False)
        assert "000922" in val_map, "val_map 必须包含 000922 (中证红利)"
        assert val_map["000922"]["name"] == "中证红利"

        # 3. 实时点位合理性范围核验 (5000 ~ 6500)
        corridor_items = fetch_custom_realtime_indices(["000922"], use_cache=False)
        assert len(corridor_items) == 1
        item_922 = corridor_items[0]
        assert item_922["code"] == "000922"
        pt_922 = float(item_922["point"])
        assert 5000.0 <= pt_922 <= 6500.0, f"000922 中证红利点位 {pt_922} 超出 5000~6500 范围，疑似误用 000015!"

        # 对照验证 000015 的点位在 3200~3400 区间，验证二者具备显著差异
        if "000015" in EXPANDED_INDEX_CATALOG:
            fb_15 = EXPANDED_INDEX_CATALOG["000015"]["fb_point"]
            assert 2800.0 <= fb_15 <= 3600.0, "000015 上证红利点位应在 3200 左右"
            assert abs(pt_922 - fb_15) > 1500.0, "000922 与 000015 点位差必须 > 1500 点以明确区分"

    def test_expanded_index_catalog_coverage_and_sectors(self):
        """
        验证全市场指数目录至少包含 38 只有效标的，且横跨 >= 12 个行业与资产板块
        """
        assert len(EXPANDED_INDEX_CATALOG) >= 38, f"Catalog entries {len(EXPANDED_INDEX_CATALOG)} < 38"
        assert len(INDEX_CATALOG_38) >= 38

        sectors = set()
        required_keys = {"code", "name", "secid", "sym", "pinyin", "sector", "asset_type", "fb_point", "fb_chg"}

        for code, meta in EXPANDED_INDEX_CATALOG.items():
            assert required_keys.issubset(meta.keys()), f"Code {code} missing required keys: {required_keys - meta.keys()}"
            assert len(code) == 6 or code.startswith("H"), f"Invalid code format: {code}"
            assert meta["fb_point"] > 0, f"Code {code} fb_point must be positive"
            assert isinstance(meta["fb_chg"], (int, float))
            sectors.add(meta["sector"])

        assert len(sectors) >= 12, f"Catalog sectors count {len(sectors)} < 12! Found: {sectors}"
        # 验证核心大类板块存在
        expected_major_sectors = {"宽基核心", "红利高股息", "科技精选", "医药生物", "消费核心", "金融大盘", "绿色能源", "国防军工", "港股海外", "美股跨境"}
        assert expected_major_sectors.issubset(sectors), f"Missing major sectors: {expected_major_sectors - sectors}"

    def test_validate_and_fetch_code_adversarial_inputs(self):
        """
        针对 validate_and_fetch_code 的输入边界与对抗性测试：
        1. 非数字与特殊字符
        2. 截断与超长字符串
        3. 不存在的 6 位代码
        4. 有效 6 位代码
        """
        invalid_inputs = [
            "abcdef",       # 纯字母
            "12a456",       # 混合字母
            "1234567",      # 7 位超长
            "!@#$%^",       # 特殊符号
            "   ",          # 空白
            None,           # None
        ]
        for inv in invalid_inputs:
            res = validate_and_fetch_code(inv)
            assert res is None, f"Input '{inv}' should return None, but got {res}"

        # 6 位全 9 或全 0 不存在的标的代码测试
        res_999999 = validate_and_fetch_code("999999")
        assert res_999999 is None, f"Code 999999 should return None, got {res_999999}"

        res_000000 = validate_and_fetch_code("000000")
        assert res_000000 is None, f"Code 000000 should return None, got {res_000000}"

        # 有效已知 6 位代码
        valid_res = validate_and_fetch_code("510300")
        if valid_res is not None:
            assert valid_res["code"] == "510300"
            assert "name" in valid_res and len(valid_res["name"]) > 0
            assert valid_res["fb_point"] > 0
            assert "secid" in valid_res
            assert "sym" in valid_res


# ==============================================================================
# Suite 2: Offline Fallback & Scale Consistency (Stress Failures Detected)
# ==============================================================================

class TestOfflineFallbackAndScaleConsistency:
    """对抗性检验 2: 离线回退与非交易时段点位/涨跌额量纲一致性"""

    def test_calc_offline_2day_return_csi_dividend_scale_invariant(self):
        """
        【压力测试】离线双日收盘价对 000922 的点位返回必须在 5000~6500 区间，
        严禁把 H00922 全收益指数点位 12189.99 误作 000922 价格点位返回。
        """
        offline_res = calc_offline_2day_return("000922")
        assert offline_res is not None
        off_pt, off_chg, off_pct = offline_res
        assert 5000.0 <= off_pt <= 6500.0, (
            f"Rule 16 违反: 离线计算 000922 点位返回 {off_pt}，严重脱离 5000~6500 基线区间！"
            f"原因: 误将 H00922 全收益指数点位作为 000922 价格指数点位返回！"
        )

    def test_fetch_custom_realtime_indices_offline_rule16_invariant(self):
        """
        【压力测试】在网络不可用（断网）场景下，fetch_custom_realtime_indices 必须遵守 Rule 16，
        000922 呈现点位必须处于 5000~6500，严禁向前端返回 12189.99 点。
        """
        with patch("urllib.request.urlopen", side_effect=Exception("Network simulated offline")):
            res = fetch_custom_realtime_indices(["000922"], use_cache=False)
            assert len(res) == 1
            pt = res[0]["point"]
            assert 5000.0 <= pt <= 6500.0, (
                f"Rule 16 严重违例: 断网降级下 000922 点位为 {pt}，超出 5000~6500 区间！"
            )

    def test_weekend_flat_etf_change_amount_proportionality(self):
        """
        【压力测试】非交易时段返回 0.00% 假平盘时，离线注入涨跌幅后，
        涨跌额 (change) 必须与点位 (point) 严格匹配 (change ≈ point * change_pct / 100)，
        严禁把 AU9999 现货黄金 +40.33 元的绝对涨跌额直接塞入 8.43 元的 518880 ETF 中。
        """
        payload = json.dumps({
            "data": {
                "diff": [
                    {"f12": "518880", "f14": "黄金ETF", "f2": 8434, "f3": 0, "f4": 0}
                ]
            }
        }).encode("utf-8")

        fake_resp = MagicMock()
        fake_resp.read.return_value = payload
        fake_resp.__enter__.return_value = fake_resp

        with patch("urllib.request.urlopen", return_value=fake_resp):
            res = fetch_custom_realtime_indices(["518880"], use_cache=False)
            assert len(res) == 1
            pt = res[0]["point"]
            chg = res[0]["change"]
            chg_pct = res[0]["change_pct"]

            # 验证涨跌额与点位量纲比例匹配
            expected_chg = round(pt * (chg_pct / 100.0), 3)
            assert abs(chg - expected_chg) < 0.05, (
                f"量纲严重错乱: 8.43元 ETF 的涨跌额被赋值为 {chg} 元 (理论应为 {expected_chg} 元)！"
                f"原因: 直接透传了现货指数 AU9999 的绝对涨跌额 off_chg，未按 ETF 点位折算！"
            )


# ==============================================================================
# Suite 3: Watchlist Cold-Start & Corruption Resistance
# ==============================================================================

class TestWatchlistColdStartAndCorruptionResistance:
    """对抗性检验 3: 自选走廊缓存冷启动与抗损坏韧性测试"""

    def test_missing_file_cold_start_fallback(self, tmp_path):
        """测试 custom_watchlist.json 不存在时的冷启动自愈能力"""
        fake_file = tmp_path / "custom_watchlist.json"
        assert not fake_file.exists()

        with patch.object(data_loader, "CUSTOM_WATCHLIST_FILE", fake_file), \
             patch.object(data_loader, "PERSISTENT_CACHE_DIR", tmp_path):
            data = load_custom_watchlist()
            assert isinstance(data, dict)
            assert "selected_codes" in data or "selected_symbols" in data
            codes = data.get("selected_codes") or data.get("selected_symbols")
            assert len(codes) >= 6
            assert "000922" in codes, "默认列表必须包含 000922 (中证红利)"
            assert "000300" in codes
            # 验证冷启动自动写盘自愈
            assert fake_file.exists()

    def test_empty_file_corruption_fallback(self, tmp_path):
        """测试 custom_watchlist.json 为 0 字节空文件时的抗崩溃能力"""
        fake_file = tmp_path / "custom_watchlist.json"
        fake_file.write_text("", encoding="utf-8")
        assert fake_file.stat().st_size == 0

        with patch.object(data_loader, "CUSTOM_WATCHLIST_FILE", fake_file), \
             patch.object(data_loader, "PERSISTENT_CACHE_DIR", tmp_path):
            data = load_custom_watchlist()
            assert isinstance(data, dict)
            codes = data.get("selected_codes") or data.get("selected_symbols")
            assert len(codes) >= 6
            assert "000922" in codes

    def test_corrupted_json_syntax_fallback(self, tmp_path):
        """测试 JSON 语法严重损坏（未闭合、乱码、非 dict 结构）时的韧性"""
        fake_file = tmp_path / "custom_watchlist.json"

        corrupted_payloads = [
            "{ corrupted: json [ 123 ",           # 语法错误
            "[1, 2, 3, 4, 5]",                     # JSON 数组而非字典
            '"just a bare string"',                # JSON 裸字符串
            "null",                                # JSON null
            "123456789"                            # JSON 数字
        ]

        for payload in corrupted_payloads:
            fake_file.write_text(payload, encoding="utf-8")
            with patch.object(data_loader, "CUSTOM_WATCHLIST_FILE", fake_file), \
                 patch.object(data_loader, "PERSISTENT_CACHE_DIR", tmp_path):
                data = load_custom_watchlist()
                assert isinstance(data, dict), f"Failed on payload: {payload}"
                codes = data.get("selected_codes") or data.get("selected_symbols")
                assert isinstance(codes, list)
                assert len(codes) >= 6
                assert "000922" in codes

    def test_save_and_reload_round_trip_preserves_order_and_custom_items(self, tmp_path):
        """测试保存与重载的往返一致性：保持用户自定义选择顺序与接入标的"""
        fake_file = tmp_path / "custom_watchlist.json"

        custom_order = ["518880", "000922", "000852", "000688", "510300"]
        custom_added_item = {
            "code": "510300",
            "name": "300ETF",
            "secid": "1.510300",
            "sym": "s_sh510300",
            "pinyin": "300etf",
            "sector": "自选标的",
            "asset_type": "etf",
            "fb_point": 4.185,
            "fb_chg": 0.32
        }

        test_payload = {
            "version": "1.0",
            "display_limit": 5,
            "display_count": 5,
            "selected_codes": list(custom_order),
            "custom_items": {"510300": custom_added_item},
            "custom_added": [custom_added_item]
        }

        with patch.object(data_loader, "CUSTOM_WATCHLIST_FILE", fake_file), \
             patch.object(data_loader, "PERSISTENT_CACHE_DIR", tmp_path):
            ok = save_custom_watchlist(test_payload)
            assert ok is True
            assert fake_file.exists()

            loaded = load_custom_watchlist()
            assert isinstance(loaded, dict)
            # 严格验证选择顺序
            assert loaded["selected_codes"] == custom_order, "选股顺序未被严格保持!"
            assert loaded["selected_symbols"] == custom_order
            # 严格验证展示上限
            assert loaded["display_limit"] == 5
            assert loaded["display_count"] == 5
            # 严格验证自定义项
            assert "510300" in loaded["custom_items"]
            assert loaded["custom_items"]["510300"]["name"] == "300ETF"


# ==============================================================================
# Suite 4: AppTest Geometry & Visual Integrity
# ==============================================================================

class TestAppTestGeometryAndVisualIntegrity:
    """对抗性检验 4: AppTest 渲染几何约束与视觉样式完整性"""

    def test_css_val_badge_classes_present_in_dom(self):
        """
        验证 app_gui.py 中 CSS 样式表完整支持：
        .val-very-low, .val-very_low 与 .val-very-high, .val-very_high 并集选择器
        """
        with open(GUI_FILE, "r", encoding="utf-8") as f:
            gui_text = f.read()

        # 并集选择器断言
        assert ".val-very-low, .val-very_low" in gui_text or \
               (".val-very-low" in gui_text and ".val-very_low" in gui_text), \
               "CSS must support both .val-very-low and .val-very_low"

        assert ".val-very-high, .val-very_high" in gui_text or \
               (".val-very-high" in gui_text and ".val-very_high" in gui_text), \
               "CSS must support both .val-very-high and .val-very_high"

        # 检查是否包含 10b981 (极低估绿色) 与 ef4444 (过热红色)
        assert "#10b981" in gui_text
        assert "#ef4444" in gui_text

    def test_primary_button_white_text_enforcement(self):
        """
        验证 button[kind="primary"] 全局强制白字规范 (#ffffff !important)，
        彻底杜绝深色文字不可读。
        """
        with open(GUI_FILE, "r", encoding="utf-8") as f:
            gui_text = f.read()

        assert 'button[kind="primary"]' in gui_text
        assert "color: #ffffff !important" in gui_text

    def test_sidebar_card_geometry_invariants(self):
        """
        Rule 14 & Rule 15 几何不变量断言：
        1. .sidebar-index-card 必须配置 min-height 与 overflow: visible !important;
        2. .sidebar-index-badge 必须配置 flex: 0 0 auto !important 与 white-space: nowrap !important 防压扁;
        3. 行情走廊不能盲目配置 overflow: hidden 截断文字。
        """
        with open(GUI_FILE, "r", encoding="utf-8") as f:
            gui_text = f.read()

        # Rule 14: 卡片安全呼吸与展开
        assert "min-height: 80px" in gui_text or "min-height:" in gui_text
        assert "overflow: visible !important" in gui_text

        # Rule 15: 胶囊物理防压扁
        assert "flex: 0 0 auto !important" in gui_text
        assert "white-space: nowrap !important" in gui_text

    def test_streamlit_apptest_zero_exception_and_sidebar_rendering(self):
        """
        Streamlit AppTest 真实端到端无异常执行：
        1. 侧边栏与四大 Tab 渲染无异常 (assert not at.exception);
        2. 0 error 警告 (assert len(at.error) == 0);
        3. 侧边栏核心组件成功挂载。
        """
        at = AppTest.from_file(GUI_FILE, default_timeout=40)
        at.run()

        assert not at.exception, f"AppTest threw exception: {at.exception}"
        assert len(at.error) == 0, f"AppTest reported errors: {[e.value for e in at.error]}"

        # 验证侧边栏标题与核心走廊挂载
        subheaders = [s.value for s in at.sidebar.subheader]
        assert any("全局领航台" in s for s in subheaders), f"Sidebar subheader missing: {subheaders}"


# ==============================================================================
# Suite 5: Referee Hash Check
# ==============================================================================

class TestRefereeHashCompliance:
    """对抗性检验 5: 物理只读裁判文件 SHA256 哈希完整性"""

    def test_referee_hashes_strictly_intact(self):
        """运行 scripts/verify_referee_hashes.py 确保 4 大裁判文件 0 篡改"""
        script_path = WORKSPACE_ROOT / "scripts" / "verify_referee_hashes.py"
        assert script_path.exists(), "verify_referee_hashes.py must exist"

        res = subprocess.run(
            ["py", "-3", str(script_path)],
            capture_output=True,
            text=True
        )
        assert res.returncode == 0, f"Referee hash verification failed with output:\n{res.stdout}\n{res.stderr}"
        assert "ALL 4 READONLY REFEREE FILES ARE INTACT AND UNMODIFIED." in res.stdout
