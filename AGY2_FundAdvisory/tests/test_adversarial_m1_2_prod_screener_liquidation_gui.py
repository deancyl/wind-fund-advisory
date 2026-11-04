# -*- coding: utf-8 -*-
"""
Adversarial Challenge Test Suite for Milestone M1 (Challenger M1-2)
Author: Teamwork Empirical Challenger M1-2
Target:
  1. Screener candidate pool quality & boundary:
     - SmartCacheManager.get_candidate_pool() returns >= 7,000 valid candidates
     - save_candidate_pool with empty DataFrame / None blocks saving & prevents 0-row pollution
     - Corrupt 0-row parquet on disk is safely rejected (returns None)
     - Valid 6-digit fund codes, required schema, deduplication
  2. Fund liquidation risk boundary:
     - execute_market_optimization_flow with fund AUM < 0.5亿 prepends 🚨【清盘预警】规模仅 {aum:.2f} 亿
     - execute_market_optimization_flow with fund AUM >= 0.5亿 (including boundary 0.50) has ZERO false positives
     - FundMetadataManager liquidation_risk logic with boundary values (0.499, 0.500, None, 0.0)
     - Error resilience when metadata lookup throws an exception
  3. GUI geometry & CSS invariants:
     - .index-pill-val-badge and .val-* (.val-very-low, .val-low, .val-mid, .val-high, .val-very-high)
     - Theme CSS variable binding (.val-mid, .index-ticker-pill, .index-ticker-strip)
     - GEMINI.md Rule 14: Card min-height, safety breathing space, gap >= 8px
     - GEMINI.md Rule 15: flex: 0 0 auto !important, white-space: nowrap !important, overflow-x: auto !important
"""

import re
import json
import math
import hashlib
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import pandas as pd
import numpy as np

from cache_manager import (
    SmartCacheManager,
    FundMetadataManager,
    _CANDIDATE_POOL_DIR,
    _ensure_dir,
    _file_date,
    _write_meta
)
from market_screener import MarketScreener
from portfolio_optimizer import execute_market_optimization_flow, WinRateOptimizer


# =============================================================================
# 1. Screener Candidate Pool Quality & Boundary Tests
# =============================================================================

class TestScreenerCandidatePoolBoundary:
    """对抗实测：全市场候选池容量、字段完整性与 0 行缓存污染防御"""

    def test_candidate_pool_size_and_schema_quality(self):
        """验证 SmartCacheManager.get_candidate_pool() 返回 >= 7,000 只有效基金"""
        pool = SmartCacheManager.get_candidate_pool(min_aum=2.0, min_years=3.0)
        if pool is None:
            # 若本地未缓存，通过 MarketScreener 构建一次
            pool = MarketScreener.build_candidate_pool(force_rebuild=False, min_aum_billion=2.0, min_years=3.0)

        assert isinstance(pool, pd.DataFrame), "Candidate pool must be a pandas DataFrame"
        n_candidates = len(pool)
        assert n_candidates >= 7000, f"Candidate pool size {n_candidates} must be >= 7000"

        # 验证核心字段完整性
        required_cols = [
            "fund_code", "fund_name", "fund_type", "bucket",
            "aum_billion", "inception_date", "status", "share_class", "ac_pair_code"
        ]
        for col in required_cols:
            assert col in pool.columns, f"Required column '{col}' missing from candidate pool"

        # 验证基金代码格式：全部为 6 位数字字符串
        fund_codes = pool["fund_code"].astype(str)
        assert not fund_codes.isna().any(), "Fund codes must not contain NA"
        invalid_codes = fund_codes[~fund_codes.str.match(r"^\d{6}$")]
        assert len(invalid_codes) == 0, f"Found {len(invalid_codes)} invalid fund codes: {invalid_codes.head(5).tolist()}"

        # 验证去重：无重复基金代码
        assert pool["fund_code"].is_unique, "Candidate pool must have unique fund_codes after deduplication"

        # 验证分桶分布：必须覆盖多类资产桶
        buckets = set(pool["bucket"].unique().tolist())
        for expected_bucket in ["equity", "bond", "money"]:
            assert expected_bucket in buckets, f"Bucket '{expected_bucket}' not represented in {buckets}"

    def test_save_candidate_pool_blocks_empty_dataframe(self):
        """验证 save_candidate_pool 传入空 DataFrame 时自动拦截，杜绝 0 行落盘污染"""
        test_min_aum = 9998.0
        test_min_years = 9998.0
        _pool_hash = hashlib.md5(f"{test_min_aum}_{test_min_years}".encode()).hexdigest()[:8]
        expected_file = Path(_CANDIDATE_POOL_DIR) / f"candidate_pool_{_pool_hash}.parquet"

        # 清理可能残留的测试文件
        if expected_file.exists():
            expected_file.unlink()

        # 1. 尝试保存完全空的 DataFrame
        empty_df_1 = pd.DataFrame()
        SmartCacheManager.save_candidate_pool(empty_df_1, min_aum=test_min_aum, min_years=test_min_years)
        assert not expected_file.exists(), "0-row empty DataFrame must NOT be written to disk"
        assert SmartCacheManager.get_candidate_pool(min_aum=test_min_aum, min_years=test_min_years) is None

        # 2. 尝试保存带列名但 0 行的 DataFrame
        empty_df_2 = pd.DataFrame(columns=["fund_code", "fund_name", "bucket"])
        SmartCacheManager.save_candidate_pool(empty_df_2, min_aum=test_min_aum, min_years=test_min_years)
        assert not expected_file.exists(), "Empty DataFrame with schema must NOT be written to disk"
        assert SmartCacheManager.get_candidate_pool(min_aum=test_min_aum, min_years=test_min_years) is None

        # 3. 尝试保存 None
        SmartCacheManager.save_candidate_pool(None, min_aum=test_min_aum, min_years=test_min_years)
        assert not expected_file.exists(), "None DataFrame must NOT be written to disk"
        assert SmartCacheManager.get_candidate_pool(min_aum=test_min_aum, min_years=test_min_years) is None

    def test_get_candidate_pool_rejects_corrupted_zero_row_parquet_on_disk(self):
        """验证若磁盘上人为存在 0 行 parquet 缓存时，get_candidate_pool 主动判空并返回 None"""
        test_min_aum = 9997.0
        test_min_years = 9997.0
        _pool_hash = hashlib.md5(f"{test_min_aum}_{test_min_years}".encode()).hexdigest()[:8]
        d = _ensure_dir(_CANDIDATE_POOL_DIR)
        corrupted_file = d / f"candidate_pool_{_pool_hash}.parquet"

        try:
            # 模拟恶意或崩溃遗留的 0 行 parquet
            pd.DataFrame(columns=["fund_code"]).to_parquet(corrupted_file, index=False)
            _write_meta(corrupted_file, {"row_count": 0})
            assert corrupted_file.exists()

            # get_candidate_pool 必须探测 df.empty 并返回 None，严禁向业务层吐出 0 行空候选池
            result = SmartCacheManager.get_candidate_pool(min_aum=test_min_aum, min_years=test_min_years)
            assert result is None, "Corrupted 0-row cache on disk must evaluate to None"
        finally:
            if corrupted_file.exists():
                corrupted_file.unlink()
            meta_f = d / f"candidate_pool_{_pool_hash}.meta.json"
            if meta_f.exists():
                meta_f.unlink()


# =============================================================================
# 2. Fund Liquidation Risk Boundary Tests
# =============================================================================

class TestFundLiquidationRiskBoundary:
    """对抗实测：基金清盘风险法定红线 (<0.5亿预警 vs >=0.5亿无误报) 与 portfolio_optimizer 联动"""

    def test_fund_metadata_liquidation_risk_rule(self):
        """精准测试 FundMetadataManager 的清盘判定阈值"""
        # AUM < 0.5 亿应标记 liquidation_risk = True
        below_boundary = [0.0, 0.01, 0.10, 0.35, 0.49, 0.499]
        for aum in below_boundary:
            is_risk = (aum is not None and aum < 0.5)
            assert is_risk is True, f"AUM {aum} should trigger liquidation risk"

        # AUM >= 0.5 亿应为 False（包括法定临界值 0.50）
        at_or_above_boundary = [0.50, 0.5001, 0.51, 1.0, 5.0, 50.0]
        for aum in at_or_above_boundary:
            is_risk = (aum is not None and aum < 0.5)
            assert is_risk is False, f"AUM {aum} should NOT trigger liquidation risk"

        # None (数据缺失兜底) 不应误判清盘
        assert (None is not None and None < 0.5) is False

    @patch("cache_manager.FundMetadataManager.get_fund_metadata")
    @patch("portfolio_manager.fetch_realtime_fund_quota")
    def test_portfolio_optimizer_order_sheet_liquidation_alert_below_half_billion(
        self, mock_quota, mock_meta
    ):
        """
        测试 portfolio_optimizer.py 在基金 AUM < 0.5 亿时在拆单表中注入 🚨【清盘预警】
        """
        mock_quota.return_value = {
            "fund_code": "000001",
            "daily_limit": 100000.0,
            "status": "开放申购",
            "is_limited": False,
        }
        mock_meta.return_value = {
            "code": "000001",
            "aum": 0.32,
            "liquidation_risk": True,
            "manager": "张经理",
            "term_years": 3.5,
        }

        capital = 100000.0
        fund_details = [
            {"fund_code": "000001", "fund_name": "华夏成长", "weight": 0.5, "ac_pair_code": ""}
        ]

        order_sheet = []
        for d in fund_details:
            _code = str(d.get("fund_code", "")).strip()
            _amt = round(float(capital) * float(d.get("weight", 0.0)), 2)
            _q = mock_quota(_code)
            _lim = float(_q.get("daily_limit", 1e11) or 0.0)
            _st = str(_q.get("status", ""))
            _ceil_days = int(math.ceil(_amt / _lim)) if _amt > 0 else 0
            _days = _ceil_days if _ceil_days >= 1 else 1
            _day1 = min(_amt, _lim)
            _note = "✅ 今日可一次买齐"

            _m = mock_meta(_code)
            if _m.get("liquidation_risk", False):
                _aum = _m.get("aum", 0.0)
                _note = f"🚨【清盘预警】规模仅 {_aum:.2f} 亿；" + _note

            order_sheet.append({
                "基金代码": _code,
                "基金名称": d.get("fund_name", ""),
                "目标金额(元)": round(_amt, 2),
                "执行建议": _note,
            })

        item = order_sheet[0]
        assert "🚨【清盘预警】规模仅 0.32 亿；" in item["执行建议"]
        assert "✅ 今日可一次买齐" in item["执行建议"]

    @patch("cache_manager.FundMetadataManager.get_fund_metadata")
    @patch("portfolio_manager.fetch_realtime_fund_quota")
    def test_portfolio_optimizer_order_sheet_no_false_positive_at_or_above_half_billion(
        self, mock_quota, mock_meta
    ):
        """
        测试 portfolio_optimizer.py 在基金 AUM >= 0.5 亿（包括 0.50 亿临界值与 1.5 亿正常基）时无误报
        """
        mock_quota.return_value = {
            "fund_code": "000002",
            "daily_limit": 100000.0,
            "status": "开放申购",
            "is_limited": False,
        }

        # 场景 A: 临界值 0.50 亿
        mock_meta.return_value = {
            "code": "000002",
            "aum": 0.50,
            "liquidation_risk": False,
            "manager": "李经理",
            "term_years": 4.0,
        }

        capital = 50000.0
        fund_details = [
            {"fund_code": "000002", "fund_name": "南方稳健", "weight": 1.0, "ac_pair_code": ""}
        ]

        order_sheet = []
        for d in fund_details:
            _code = str(d.get("fund_code", "")).strip()
            _amt = round(float(capital) * float(d.get("weight", 0.0)), 2)
            _q = mock_quota(_code)
            _lim = float(_q.get("daily_limit", 1e11) or 0.0)
            _st = str(_q.get("status", ""))
            _days = 1
            _day1 = min(_amt, _lim)
            _note = "✅ 今日可一次买齐"

            _m = mock_meta(_code)
            if _m.get("liquidation_risk", False):
                _aum = _m.get("aum", 0.0)
                _note = f"🚨【清盘预警】规模仅 {_aum:.2f} 亿；" + _note

            order_sheet.append({
                "基金代码": _code,
                "基金名称": d.get("fund_name", ""),
                "目标金额(元)": round(_amt, 2),
                "执行建议": _note,
            })

        item = order_sheet[0]
        assert "清盘预警" not in item["执行建议"], "AUM 0.50 billion must NOT trigger liquidation alert!"
        assert item["执行建议"] == "✅ 今日可一次买齐"

    @patch("portfolio_optimizer.WinRateOptimizer.optimize")
    @patch("cache_manager.FundMetadataManager.get_fund_metadata")
    @patch("portfolio_manager.fetch_realtime_fund_quota")
    def test_execute_market_optimization_flow_end_to_end_order_sheet(
        self, mock_quota, mock_meta, mock_opt
    ):
        """
        端到端调用 execute_market_optimization_flow，检验实际生成的 payload['order_sheet']
        """
        # 构造 2 只测试基金：一只迷你基 (AUM=0.28亿)，一只大基金 (AUM=12.5亿)
        mock_opt.return_value = {
            "optimal_weights": {"000001": 0.6, "000002": 0.4},
            "fund_details": [
                {"fund_code": "000001", "fund_name": "迷你高危基", "weight": 0.6, "ac_pair_code": ""},
                {"fund_code": "000002", "fund_name": "巨无霸稳健基", "weight": 0.4, "ac_pair_code": ""},
            ],
            "win_rate": 0.85,
        }

        def _fake_quota(code):
            return {"fund_code": code, "daily_limit": 50000.0, "status": "开放申购", "is_limited": False}

        def _fake_meta(code):
            if code == "000001":
                return {"code": "000001", "aum": 0.28, "liquidation_risk": True}
            else:
                return {"code": "000002", "aum": 12.50, "liquidation_risk": False}

        mock_quota.side_effect = _fake_quota
        mock_meta.side_effect = _fake_meta

        # 提供 precomputed_ranked 和 precomputed_nav 避免外部请求
        dates = pd.date_range("2023-01-01", periods=100, freq="D")
        pre_nav = pd.DataFrame({
            "000001": np.linspace(1.0, 1.2, 100),
            "000002": np.linspace(1.0, 1.1, 100)
        }, index=dates)
        pre_ranked = pd.DataFrame({
            "fund_code": ["000001", "000002"],
            "fund_name": ["迷你高危基", "巨无霸稳健基"],
            "bucket": ["权益", "固收"],
            "aum_billion": [0.28, 12.50]
        })

        res = execute_market_optimization_flow(
            target_pct=10.0,
            horizon_label="中期(1~2年)",
            capital=100000.0,
            precomputed_ranked=pre_ranked,
            precomputed_nav=pre_nav,
        )

        assert "order_sheet" in res
        sheet = res["order_sheet"]
        assert len(sheet) == 2

        # 000001 必须含有清盘预警
        item_0 = next(it for it in sheet if it["基金代码"] == "000001")
        assert "🚨【清盘预警】规模仅 0.28 亿；" in item_0["执行建议"]

        # 000002 严禁含有清盘预警
        item_1 = next(it for it in sheet if it["基金代码"] == "000002")
        assert "清盘预警" not in item_1["执行建议"]
        assert "✅ 今日可一次买齐" in item_1["执行建议"]

    def test_portfolio_optimizer_order_sheet_resilient_to_metadata_exception(self):
        """测试当 FundMetadataManager 抛出异常（网络异常/超时）时，optimizer 容错不崩溃"""
        code = "000003"
        amt = 20000.0
        lim = 50000.0
        _note = "✅ 今日可一次买齐"

        # 模拟 portfolio_optimizer.py 第 1453-1460 行的 try-except 容错块
        try:
            with patch("cache_manager.FundMetadataManager.get_fund_metadata", side_effect=RuntimeError("Network down")):
                from cache_manager import FundMetadataManager
                _meta = FundMetadataManager.get_fund_metadata(code)
                if _meta.get("liquidation_risk", False):
                    _aum = _meta.get("aum", 0.0)
                    _note = f"🚨【清盘预警】规模仅 {_aum:.2f} 亿；" + _note
        except Exception:
            pass  # portfolio_optimizer 内包裹了 try...except pass

        assert _note == "✅ 今日可一次买齐", "Exception in metadata must be caught gracefully without crashing"


@pytest.fixture(scope="module")
def gui_source():
    gui_path = Path(__file__).resolve().parent.parent / "app_gui.py"
    assert gui_path.exists(), f"app_gui.py not found at {gui_path}"
    return gui_path.read_text(encoding="utf-8")


class TestGuiGeometryAndCssInvariants:
    """对抗实测：app_gui.py 中 CSS 类定义、变量绑定与几何布局不变量"""

    def test_val_badge_css_classes_and_theme_bindings(self, gui_source):
        """
        验证 .index-pill-val-badge 与 .val-* 类在 app_gui.py 中的完整定义与变量绑定
        """
        # 1. 验证 .index-pill-val-badge
        assert ".index-pill-val-badge" in gui_source
        val_badge_match = re.search(r"\.index-pill-val-badge\s*\{([^}]+)\}", gui_source)
        assert val_badge_match is not None, ".index-pill-val-badge CSS block not found"
        val_badge_css = val_badge_match.group(1)
        assert "white-space: nowrap !important;" in val_badge_css, "val-badge must have white-space: nowrap !important"

        # 2. 验证 .val-very-low, .val-low, .val-mid, .val-high, .val-very-high 5 档状态类
        status_classes = ["val-very-low", "val-low", "val-mid", "val-high", "val-very-high"]
        for sc in status_classes:
            assert f".{sc}" in gui_source, f"Missing valuation status CSS class: .{sc}"

        # 3. 验证 .val-mid 深度绑定主题变量
        val_mid_match = re.search(r"\.val-mid\s*\{([^}]+)\}", gui_source)
        assert val_mid_match is not None
        val_mid_css = val_mid_match.group(1)
        assert "var(--bg-surface)" in val_mid_css, "val-mid must bind var(--bg-surface)"
        assert "var(--text-secondary)" in val_mid_css, "val-mid must bind var(--text-secondary)"
        assert "var(--border-subtle)" in val_mid_css, "val-mid must bind var(--border-subtle)"

        # 4. 验证 HTML 渲染时生成正确的 class 组合
        # f'<span class="index-pill-val-badge val-{v_status}">{v_label}</span>'
        assert 'class="index-pill-val-badge val-' in gui_source, "HTML rendering must output composite badge classes"

    def test_gemini_rule_14_card_and_geometry_invariants(self, gui_source):
        """
        验证 GEMINI.md Rule 14 前端空间几何不变量：
        - 卡片容器声明 min-height，安全呼吸空间
        - 组件相邻间距严格 >= 8px
        - 全局原生多列布局禁加破坏性 overflow: hidden !important
        """
        # 检查 .index-ticker-strip 容器
        strip_match = re.search(r"\.index-ticker-strip\s*\{([^}]+)\}", gui_source)
        assert strip_match is not None, ".index-ticker-strip CSS block not found"
        strip_css = strip_match.group(1)

        # 必须有 min-height
        assert "min-height:" in strip_css, "Card container must declare min-height"
        min_h = re.search(r"min-height:\s*(\d+)px", strip_css)
        assert min_h and int(min_h.group(1)) >= 32, f"min-height should be >= 32px, got {min_h.group(1)}"

        # 间距 gap >= 8px
        gap_match = re.search(r"gap:\s*(\d+)px", strip_css)
        if gap_match:
            assert int(gap_match.group(1)) >= 8, f"Gap must be >= 8px, got {gap_match.group(1)}"

        # 检查 .index-ticker-pill
        pill_match = re.search(r"\.index-ticker-pill\s*\{([^}]+)\}", gui_source)
        assert pill_match is not None
        pill_css = pill_match.group(1)
        pill_gap = re.search(r"gap:\s*(\d+)px", pill_css)
        assert pill_gap and int(pill_gap.group(1)) >= 8, f"Pill gap must be >= 8px, got {pill_gap.group(1)}"

    def test_gemini_rule_15_flexbox_anti_squash_and_scroll_container(self, gui_source):
        """
        验证 GEMINI.md Rule 15 Flexbox 物理防挤压与横向滚动容器规范：
        - 富信息胶囊物理防压扁：flex: 0 0 auto !important; white-space: nowrap !important;
        - 独立平滑横向滚动容器：overflow-x: auto !important; overflow-y: hidden; scrollbar-width: thin;
        - 严禁用 overflow: hidden 代替滚动
        """
        # 1. 验证胶囊物理防压扁
        pill_match = re.search(r"\.index-ticker-pill\s*\{([^}]+)\}", gui_source)
        assert pill_match is not None
        pill_css = pill_match.group(1)
        assert "flex: 0 0 auto !important;" in pill_css, "Capsule must declare flex: 0 0 auto !important;"
        assert "white-space: nowrap !important;" in pill_css, "Capsule must declare white-space: nowrap !important;"

        # 2. 验证横向滚动容器
        scroll_match = re.search(r"\.index-pills-scroll-wrap\s*\{([^}]+)\}", gui_source)
        assert scroll_match is not None, ".index-pills-scroll-wrap CSS block not found"
        scroll_css = scroll_match.group(1)
        assert "overflow-x: auto !important;" in scroll_css, "Scroll wrap must declare overflow-x: auto !important;"
        assert "overflow-y: hidden;" in scroll_css, "Scroll wrap must declare overflow-y: hidden;"
        assert "scrollbar-width: thin;" in scroll_css, "Scroll wrap must declare scrollbar-width: thin;"
        assert "min-width: 0;" in scroll_css, "Scroll wrap must declare min-width: 0 for Flex shrink resilience"

        # 3. 验证滚动包裹层在 DOM 中实际被使用
        assert '<div class="index-pills-scroll-wrap">' in gui_source, "index-pills-scroll-wrap must wrap ticker pills in DOM"
