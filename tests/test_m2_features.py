# -*- coding: utf-8 -*-
"""
Unit tests for Milestone 2 (M2) features:
1. portfolio_manager.py parse_smart_text_holdings fuzzy matching & regex cleaning
2. portfolio_manager.py parse_screenshot_ocr_holdings & parse_long_screenshot_holdings alias
3. app_gui.py global top bar (desktop & mobile)
4. app_gui.py mobile simple view 5 cards & OCR commit pipeline
"""
import pytest
import re
from AGY2_FundAdvisory.portfolio_manager import (
    PortfolioManager,
    parse_smart_text_holdings,
    fuzzy_match_fund_by_name,
    parse_screenshot_ocr_holdings,
    parse_long_screenshot_holdings,
)


def test_fuzzy_match_fund_by_name_ac_and_aliases():
    """验证模糊匹配器对 29 只实战存量组合及核心池别名的精确匹配与 A/C 区分"""
    # 华安黄金 A vs C
    res_gold_c = fuzzy_match_fund_by_name("华安黄金ETF联接C (395.73元)")
    assert res_gold_c["fund_code"] == "000217"
    assert res_gold_c["share_class"] == "C"

    res_gold_a = fuzzy_match_fund_by_name("华安黄金ETF联接A")
    assert res_gold_a["fund_code"] == "000216"
    assert res_gold_a["share_class"] == "A"

    # 南方中证新能源 C
    res_new_energy = fuzzy_match_fund_by_name("南方中证新能源ETF联接C")
    assert res_new_energy["fund_code"] == "012832"
    assert res_new_energy["share_class"] == "C"

    # 华夏科创50 C vs A
    res_kc50_c = fuzzy_match_fund_by_name("华夏科创50C 20000 亏500")
    assert res_kc50_c["fund_code"] == "011613"
    assert res_kc50_c["share_class"] == "C"

    res_kc50_a = fuzzy_match_fund_by_name("华夏科创50A 20000")
    assert res_kc50_a["fund_code"] == "011612"
    assert res_kc50_a["share_class"] == "A"

    # 短别名
    assert fuzzy_match_fund_by_name("纯债")["fund_code"] == "002351"
    assert fuzzy_match_fund_by_name("易方达裕祥")["fund_code"] == "002351"
    assert fuzzy_match_fund_by_name("招商白酒")["fund_code"] == "161725"


def test_parse_smart_text_holdings_fuzzy_match_and_regex_cleaning():
    """验证 parse_smart_text_holdings 彻底打通 fuzzy_match_fund_by_name 并前置清洗昨日收益"""
    # 1. 华安黄金 C 类不退化为 A 类
    res1 = parse_smart_text_holdings("华安黄金ETF联接C (395.73元)")
    assert len(res1) == 1
    assert res1[0]["fund_code"] == "000217"
    assert res1[0]["share_class"] == "C"
    assert abs(res1[0]["market_value"] - 395.73) < 0.01

    # 2. 南方中证新能源 C 不被错搜为 100032，且昨日收益 +0.05 不破坏市值与盈亏
    text_ocr_sim = "南方中证新能源ETF联接C \n 昨日收益 +0.05  34.50 \n 持有收益 -15.50  持有金额"
    res2 = parse_smart_text_holdings(text_ocr_sim)
    assert len(res2) == 1
    assert res2[0]["fund_code"] == "012832"
    assert res2[0]["share_class"] == "C"
    assert abs(res2[0]["market_value"] - 34.50) < 0.01
    assert abs(res2[0]["floating_pnl"] - (-15.50)) < 0.01
    assert abs(res2[0]["cost_basis"] - 50.00) < 0.01

    # 3. 华夏科创50C
    res3 = parse_smart_text_holdings("华夏科创50C 20000 亏500")
    assert len(res3) == 1
    assert res3[0]["fund_code"] == "011613"
    assert res3[0]["share_class"] == "C"
    assert abs(res3[0]["market_value"] - 20000.0) < 0.01
    assert abs(res3[0]["floating_pnl"] - (-500.0)) < 0.01


def test_parse_screenshot_ocr_and_long_screenshot_alias():
    """验证 parse_screenshot_ocr_holdings 与 parse_long_screenshot_holdings 别名均存在且挂载在 PortfolioManager"""
    pm = PortfolioManager()
    assert hasattr(pm, "parse_screenshot_ocr_holdings")
    assert hasattr(pm, "parse_long_screenshot_holdings")
    assert callable(pm.parse_screenshot_ocr_holdings)
    assert callable(pm.parse_long_screenshot_holdings)
    assert parse_long_screenshot_holdings is parse_screenshot_ocr_holdings

    # 空输入安全回退
    assert pm.parse_screenshot_ocr_holdings(b"") == []
    assert pm.parse_long_screenshot_holdings(b"") == []


def test_app_gui_source_code_integrity():
    """静态 AST / 正则核验 app_gui.py 中全局顶栏与手机模式 5 大卡片实装完整性"""
    with open("AGY2_FundAdvisory/app_gui.py", "r", encoding="utf-8") as f:
        src = f.read()

    # 1. 全局顶栏控制条
    assert "topbar_ledger_select_" in src
    assert "seg_topbar_view_mode" in src or "rad_topbar_view_mode" in src
    assert "🧭 AGY2 智投量化终端" in src
    assert "switch_active_ledger" in src

    # 2. 手机极简盯盘模式 5 张卡片
    assert 'st.session_state.get("app_view_layout_mode") == "📱 手机极简盯盘"' in src
    assert "📱 账户总资产" in src  # 卡片 1
    assert "🧭 首席投顾五维决策备忘录" in src  # 卡片 2
    assert "btn_mob_sweep_tails" in src  # 卡片 3
    assert "is_tail = (0 < mv_h < 100.0) or (100.0 <= mv_h < 200.0 and (s_cls == \"C\" or any(k in fname for k in [\"联接\", \"ETF\", \"指数\", \"红包\", \"体验\", \"尾仓\", \"碎片\"])))" in src
    assert "is_fee_free = (s_cls == \"C\" and min_d >= 30) or (s_cls != \"C\" and min_d >= 365)" in src
    assert "⏱️ 14:30 尾盘操作指令" in src  # 卡片 4
    assert "【AGY2 智投量化 14:30 下单小抄】" in src  # 卡片 4 小抄
    assert "btn_mob_ocr_commit_replace" in src  # 卡片 5
    assert "btn_mob_ocr_commit_append" in src  # 卡片 5
    assert "pm.parse_screenshot_ocr_holdings" in src  # 卡片 5 当场解析


def test_mobile_tail_sweep_rule_and_combat29_alignment():
    """
    验证手机模式 Card 3/Card 4 尾仓清扫判定规则与 advisory_engine 完全对齐：
    1. 在 combat_29_funds 真实实战账本下，扫出的免赎碎片尾仓数量严格为 19；
    2. 总金额严格等于 442.70；
    3. 005827 易方达蓝筹精选混合（A类，浮亏）被安全保留，绝不在清扫列表中。
    """
    from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager
    pm = MultiLedgerManager.get_instance().get_pm("combat_29_funds")

    tail_items = []
    if pm.holdings:
        for fc, h in pm.holdings.items():
            mv_h = getattr(h, "shares", 0.0) * getattr(h, "current_nav", 1.0)
            s_cls = getattr(h, "share_class", "A")
            fname = getattr(h, "fund_name", fc)
            min_d = min((getattr(b, "holding_days", 30) for b in getattr(h, "batches", [])), default=getattr(h, "holding_days", 30))
            is_tail = (0 < mv_h < 100.0) or (100.0 <= mv_h < 200.0 and (s_cls == "C" or any(k in fname for k in ["联接", "ETF", "指数", "红包", "体验", "尾仓", "碎片"])))
            is_fee_free = (s_cls == "C" and min_d >= 30) or (s_cls != "C" and min_d >= 365)
            if is_tail and is_fee_free:
                tail_items.append((fc, fname, mv_h, min_d))

    assert len(tail_items) == 19
    total_cash = sum(x[2] for x in tail_items)
    assert abs(total_cash - 442.70) < 0.01
    tail_codes = [x[0] for x in tail_items]
    assert "005827" not in tail_codes


def test_app_gui_streamlit_apptest_rendering():
    """使用 streamlit.testing.v1.AppTest 验证桌面与手机视图无异常渲染"""
    from streamlit.testing.v1 import AppTest
    from pathlib import Path

    app_path = (Path(__file__).parent.parent / "AGY2_FundAdvisory" / "app_gui.py").resolve()
    at = AppTest.from_file(str(app_path), default_timeout=30)
    # 测试桌面模式初始化
    at.run()
    assert not at.exception, f"Desktop mode exception: {at.exception}"

    # 切换为手机极简盯盘模式
    at.session_state["app_view_layout_mode"] = "📱 手机极简盯盘"
    at.run()
    assert not at.exception, f"Mobile mode exception: {at.exception}"
