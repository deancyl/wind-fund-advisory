# -*- coding: utf-8 -*-
"""
Adversarial Verification Suite for G16 Generation Milestone 2 (M2):
"全局紧凑顶栏、手机极简盯盘 5 张卡片流与真 OCR 切片平账闭环"

Tested by Challenger: `challenger_m2_2`
Role: Empirical Challenger (Critic / Specialist)

Test Dimensions:
1. Topbar bidirectional sync & ledger selector across desktop and mobile modes.
2. Mobile simple view 5-card stream rendering with combat_29_funds.
3. Card 3 tail fragment sweep button click & session state mutation.
4. Card 5 long screenshot upload, rapid OCR preview, and commit replace/append buttons.
5. Error boundary stress-testing on corrupted image input.
6. Robustness testing of parse_smart_text_holdings against adversarial numeric strings.
7. Performance isolation via st.stop() in mobile mode.
"""

import pytest
import re
from pathlib import Path
from unittest.mock import patch, MagicMock
from streamlit.testing.v1 import AppTest

from AGY2_FundAdvisory.portfolio_manager import (
    PortfolioManager,
    parse_smart_text_holdings,
    fuzzy_match_fund_by_name,
    parse_screenshot_ocr_holdings,
    parse_long_screenshot_holdings,
)
from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager


APP_PATH = str((Path(__file__).parent.parent / "AGY2_FundAdvisory" / "app_gui.py").resolve())


def test_topbar_bidirectional_sync_desktop_and_mobile():
    """
    对抗性核验 1：
    验证桌面模式与手机模式下全局顶栏的渲染完整性：
    1. 品牌与角标 HTML 存在
    2. 账本下拉框列出所有可用账本（必须同时包含 'main_live' 与 'combat_29_funds'）
    3. 模式切换控件存在
    """
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    assert not at.exception, f"Desktop run exception: {at.exception}"

    # 1. 顶栏品牌与角标
    brand_rendered = any("AGY2 智投量化终端" in m.value for m in at.markdown)
    assert brand_rendered, "未在首屏 Markdown/HTML 中检测到顶栏品牌标识 '🧭 AGY2 智投量化终端'"

    # 2. 账本下拉框及其选项
    topbar_ledger_sb = [s for s in at.selectbox if "topbar_ledger_select" in (s.key or "")]
    assert len(topbar_ledger_sb) >= 1, "未在顶栏检测到账本切换下拉选择框 (topbar_ledger_select)"
    sb = topbar_ledger_sb[0]
    options = list(sb.options)
    assert any("主实盘账本" in opt for opt in options), f"'主实盘账本' 不在账本选项中: {options}"
    assert any("实战存量组合" in opt or "29只" in opt for opt in options), f"'combat_29_funds' 不在账本选项中: {options}"

    # 3. 切换至手机模式核验（顶栏与侧边栏双向联动同步）
    at.session_state["app_view_layout_mode"] = "📱 手机极简盯盘"
    at.session_state["sb_view_layout_radio"] = "📱 手机极简盯盘"
    at.run()
    assert not at.exception, f"Mobile run exception: {at.exception}"

    topbar_ledger_sb_mob = [s for s in at.selectbox if "topbar_ledger_select" in (s.key or "")]
    assert len(topbar_ledger_sb_mob) >= 1, "手机模式下顶栏账本切换下拉框缺失"
    mob_subheaders = [s.value for s in at.subheader]
    assert "📱 手机极简盯盘" in mob_subheaders, f"手机极简盯盘子标题未渲染: {mob_subheaders}"


def test_mobile_five_cards_rendering_combat29():
    """
    对抗性核验 2：
    在 combat_29_funds 激活且切换至手机极简盯盘时，
    验证 5 张卡片完整无损渲染，且内容准确反映 29 基真实特征：
    - 卡片 1：总资产与浮盈
    - 卡片 2：五维备忘录摘要
    - 卡片 3：19 只碎片尾仓清扫建议及一键按钮
    - 卡片 4：14:30 尾盘指令与下单口令小抄
    - 卡片 5：长截图上传组件
    """
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.session_state["app_view_layout_mode"] = "📱 手机极简盯盘"
    at.session_state["active_ledger_id"] = "combat_29_funds"
    at.run()
    assert not at.exception, f"Combat 29 mobile run exception: {at.exception}"

    all_md_text = "\n".join(m.value for m in at.markdown)

    # a) 卡片 1：总资产卡
    assert "📱 账户总资产" in all_md_text, "卡片 1 总资产标识缺失"
    assert "今日预估" in all_md_text, "卡片 1 今日预估缺失"
    assert "累计浮盈" in all_md_text, "卡片 1 累计浮盈缺失"

    # b) 卡片 2：五维备忘录摘要
    assert "🧭 首席投顾五维决策备忘录" in all_md_text, "卡片 2 五维备忘录摘要缺失"
    assert "投顾人话结论" in all_md_text, "卡片 2 投顾人话结论缺失"

    # c) 卡片 3：碎片尾仓卡与一键清扫按钮
    assert "🧹 碎片尾仓一键瘦身建议卡" in all_md_text, "卡片 3 碎片尾仓建议卡缺失"
    sweep_btn = [b for b in at.button if b.key == "btn_mob_sweep_tails"]
    assert len(sweep_btn) == 1, "卡片 3 '🧹 一键模拟/清扫碎片尾仓归拢至纯债 (002351)' 按钮缺失"

    # d) 卡片 4：14:30 尾盘指令与可复制小抄
    assert "⏱️ 14:30 尾盘操作指令" in all_md_text, "卡片 4 14:30 尾盘操作指令标题缺失"
    assert len(at.code) >= 1, "卡片 4 缺少 st.code 小抄代码块"
    code_content = at.code[0].value
    assert "【AGY2 智投量化 14:30 下单小抄】" in code_content, f"小抄口令格式不符: {code_content}"
    assert "002351" in code_content, "小抄口令中未包含核心纯债代码 002351"

    # e) 卡片 5：手机长截图智能切片识别
    assert "📸 手机持仓长截图智能切片识别" in all_md_text, "卡片 5 截图标题缺失"
    uploaders = [f for f in at.file_uploader if f.key == "mob_uploader_feed"]
    assert len(uploaders) == 1, "卡片 5 文件上传组件 mob_uploader_feed 缺失"
    assert "正在研发中" not in all_md_text, "检测到敷衍用户的假功能文本"


def test_mobile_card3_sweep_tails_action_state_mutation():
    """
    对抗性核验 3：
    模拟用户点击手机卡片 3 的 'btn_mob_sweep_tails' 按钮，
    验证状态机正确设置 Tab 2 预案参数，并给出明确反馈。
    """
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.session_state["app_view_layout_mode"] = "📱 手机极简盯盘"
    at.session_state["active_ledger_id"] = "combat_29_funds"
    at.run()

    sweep_btn = next(b for b in at.button if b.key == "btn_mob_sweep_tails")
    sweep_btn.click().run()
    assert not at.exception, f"Click sweep tails exception: {at.exception}"

    # 验证 session_state 正确变异
    assert at.session_state.get("tab2_rebalanced") is True
    assert at.session_state.get("tab2_diagnosed") is True
    assert at.session_state.get("tab2_trigger_rebalance") is True
    assert "002351" in at.session_state.get("sel_sc_anchor", "")
    assert "🧹 尾部碎片" in at.session_state.get("rad_tab2_scenario_mode", "")

    # 验证界面反馈
    success_vals = [s.value for s in at.success]
    assert any("已成功启动清扫归拢预案" in val for val in success_vals), f"成功提示未见: {success_vals}"


def test_mobile_card5_ocr_upload_preview_and_interactive_commit():
    """
    对抗性核验 4：
    端到端测试手机端长截图上传 -> 识别预览 -> 覆盖/追加按钮交互：
    1. 上传图片后触发 RapidOCR 解析并展示预览 DataFrame
    2. 校验一键覆盖 (btn_mob_ocr_commit_replace) 与追加合并 (btn_mob_ocr_commit_append) 交互按钮
    3. 校验点击追加合并时调动底层 import_from_smart_text 且无抛错
    """
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.session_state["app_view_layout_mode"] = "📱 手机极简盯盘"
    at.run()

    fu = next(f for f in at.file_uploader if f.key == "mob_uploader_feed")

    mock_parsed_holdings = [
        {
            "fund_code": "000217",
            "fund_name": "华安黄金ETF联接C",
            "market_value": 395.73,
            "floating_pnl": 5.20,
            "cost_basis": 390.53,
            "share_class": "C",
            "holding_days": 365,
            "current_nav": 1.50
        },
        {
            "fund_code": "012832",
            "fund_name": "南方中证新能源ETF联接C",
            "market_value": 34.50,
            "floating_pnl": -15.50,
            "cost_basis": 50.00,
            "share_class": "C",
            "holding_days": 365,
            "current_nav": 0.85
        }
    ]

    # 上传模拟图片
    with patch("AGY2_FundAdvisory.portfolio_manager.PortfolioManager.parse_screenshot_ocr_holdings", return_value=mock_parsed_holdings):
        fu.upload("mobile_mock_screenshot.png", b"fake_png_header_and_data", "image/png").run()

    assert not at.exception, f"OCR upload exception: {at.exception}"

    # 验证识别结果概览
    success_vals = [s.value for s in at.success]
    assert any("成功识别 2 只基金" in val for val in success_vals), f"未见识别成功提示: {success_vals}"

    # 验证数据编辑表格存在
    assert len(at.dataframe) >= 1, "未见 OCR 预览可编辑表格 (st.data_editor/dataframe)"

    # 验证操作按钮
    btn_replace = [b for b in at.button if b.key == "btn_mob_ocr_commit_replace"]
    btn_append = [b for b in at.button if b.key == "btn_mob_ocr_commit_append"]
    assert len(btn_replace) == 1, "缺少 'btn_mob_ocr_commit_replace' 覆盖入库按钮"
    assert len(btn_append) == 1, "缺少 'btn_mob_ocr_commit_append' 追加合并按钮"

    # 点击追加合并按钮，保护 save_state 避免污染本地测试数据
    with patch("AGY2_FundAdvisory.portfolio_manager.PortfolioManager.save_state"):
        with patch("AGY2_FundAdvisory.portfolio_manager.PortfolioManager.import_from_smart_text") as mock_import:
            btn_append[0].click().run()
            assert not at.exception, f"Click append button exception: {at.exception}"
            assert mock_import.called, "点击追加合并按钮后未调用 pm.import_from_smart_text"
            # 校验调用参数：replace_existing 必须为 False
            call_kwargs = mock_import.call_args[1] if mock_import.call_args[1] else {}
            call_args = mock_import.call_args[0] if mock_import.call_args[0] else []
            replace_arg = call_kwargs.get("replace_existing", call_args[2] if len(call_args) > 2 else None)
            assert replace_arg is False, f"追加合并应当传入 replace_existing=False, 实际为 {replace_arg}"


def test_mobile_card5_corrupted_image_error_boundary():
    """
    对抗性核验 5：
    当用户上传损坏或非法的图片字节时，OCR 抛出内部异常，
    系统应由 try...except 优雅兜底，在界面输出 st.error 告警，
    绝对不可引发未捕获崩溃或白屏！
    """
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.session_state["app_view_layout_mode"] = "📱 手机极简盯盘"
    at.run()

    fu = next(f for f in at.file_uploader if f.key == "mob_uploader_feed")

    # 模拟 OCR 引擎抛出底层异常
    with patch("AGY2_FundAdvisory.portfolio_manager.PortfolioManager.parse_screenshot_ocr_holdings", side_effect=RuntimeError("Corrupted ONNX image tensor")):
        fu.upload("bad_file.png", b"corrupted_garbage_bytes", "image/png").run()

    assert not at.exception, f"损坏图片引发了未捕获异常: {at.exception}"
    error_vals = [e.value for e in at.error]
    assert any("截图解析异常" in val and "Corrupted ONNX image tensor" in val for val in error_vals), \
        f"未按预期优雅展示错误边界提示: {error_vals}"


def test_parse_smart_text_holdings_adversarial_variations():
    """
    对抗性核验 6：
    极限压测 parse_smart_text_holdings 对昨日收益正则剥离与混淆数字代码的抗干扰能力：
    1. 文本含多处 '昨日收益 +0.05' 与 '05' 不被误切为 005561
    2. 文本含 '100032' 纯数字与 '富国中证红利'
    3. 负数收益 '-123.45' 与正数金额 '4,567.89' 格式
    4. 带有特殊干扰符号换行
    """
    # 场景 A: 混杂昨日收益、带有正负号与千分位逗号
    sample_a = """
    华安黄金ETF联接C
    昨日收益: +0.05 元
    持有金额: 1,234.56
    持有收益: -67.89
    """
    res_a = parse_smart_text_holdings(sample_a)
    assert len(res_a) == 1
    assert res_a[0]["fund_code"] == "000217"
    assert res_a[0]["share_class"] == "C"
    assert abs(res_a[0]["market_value"] - 1234.56) < 0.01
    assert abs(res_a[0]["floating_pnl"] - (-67.89)) < 0.01

    # 场景 B: 6位纯数字代码与切词防误命中
    sample_b = """
    005561 创金合信红利低波A
    昨日盈亏 -12.30  50000.00
    持有收益 +2340.00
    """
    res_b = parse_smart_text_holdings(sample_b)
    assert len(res_b) == 1
    assert res_b[0]["fund_code"] == "005561"
    assert abs(res_b[0]["market_value"] - 50000.0) < 0.01

    # 场景 C: 只有别名，无数字代码
    sample_c = "招商白酒 3000 亏200"
    res_c = parse_smart_text_holdings(sample_c)
    assert len(res_c) == 1
    assert res_c[0]["fund_code"] == "161725"
    assert abs(res_c[0]["market_value"] - 3000.0) < 0.01
    assert abs(res_c[0]["floating_pnl"] - (-200.0)) < 0.01

    # 场景 D: 纯噪音与非法输入安全兜底
    assert parse_smart_text_holdings("") == []
    assert parse_smart_text_holdings("   \n\t  ") == []
    assert parse_smart_text_holdings("没有任何基金信息的一段纯汉字随笔") == []


def test_mobile_performance_isolation_via_st_stop():
    """
    对抗性核验 7：
    验证手机极简盯盘视图确实通过 st.stop() 进行了性能隔离，
    在手机模式下绝不执行桌面模式的 20+ 个重量级 Tab 2/Tab 3/回测组件。
    """
    at_desk = AppTest.from_file(APP_PATH, default_timeout=30)
    at_desk.run()

    at_mob = AppTest.from_file(APP_PATH, default_timeout=30)
    at_mob.session_state["app_view_layout_mode"] = "📱 手机极简盯盘"
    at_mob.run()

    # 手机模式下的 selectbox 与 slider 数量应当远少于桌面模式
    desk_sb_count = len(at_desk.selectbox)
    mob_sb_count = len(at_mob.selectbox)
    assert mob_sb_count < desk_sb_count, f"手机模式组件未剪枝: mob={mob_sb_count}, desk={desk_sb_count}"

    # 桌面模式包含 Tab 导航标签，手机模式直接截断不加载主选项卡
    assert len(at_desk.tabs) > 0, "桌面模式应包含 Tab 选项卡"
    assert len(at_mob.tabs) == 0, "手机模式经 st.stop() 截断后不应包含桌面 Tab 选项卡"
