"""
G15 Phase 3 单元与集成测试套件：
1. 手机长截图高清切片无损分割 (slice_long_screenshot_for_ocr)
2. 全市场 28,177 基金字典模糊匹配 (fuzzy_match_fund_by_name)
3. ActiveRiskSentry 维度 13 碎片尾仓清理预警器
4. combat_29_funds 存量实战账本分厘平账 (29基·¥26,615.10·400天满期免赎)
5. 会计恒等式与负收益符号保真 (无 abs 篡改，小额尾仓不丢弃)
"""

import io
import pytest
from PIL import Image
from AGY2_FundAdvisory.portfolio_manager import (
    slice_long_screenshot_for_ocr,
    fuzzy_match_fund_by_name,
    parse_smart_text_holdings,
    parse_batch_fund_text_input,
    PortfolioManager,
)
from AGY2_FundAdvisory.advisory_engine import ActiveRiskSentry
from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager


def test_slice_long_screenshot_for_ocr_dimensions_and_overlap():
    """测试长截图切片：保持 100% 原始宽度，纵向 1000px 切片，150px 垂直重叠"""
    # 创建 1080x2500 模拟长截图
    img = Image.new("RGB", (1080, 2500), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_bytes = buf.getvalue()

    slices = slice_long_screenshot_for_ocr(img_bytes, target_height=1000, overlap=150)
    assert len(slices) == 3, f"Expected 3 slices, got {len(slices)}"

    # 验证每一切片宽度保持 1080px (100% 原始宽度无形变压缩)
    for i, (sl_img, y_off) in enumerate(slices):
        assert sl_img.size[0] == 1080, f"Slice {i} width should be 1080, got {sl_img.size[0]}"

    # 验证 y_offset 与高度
    assert slices[0][1] == 0
    assert slices[0][0].size[1] == 1000

    assert slices[1][1] == 850
    assert slices[1][0].size[1] == 1000

    assert slices[2][1] == 1700
    assert slices[2][0].size[1] == 800

    # 验证重叠度: 切片0与切片1在 y=850~1000 重叠 150px
    assert (slices[0][1] + slices[0][0].size[1]) - slices[1][1] == 150


def test_fuzzy_match_fund_by_name_accuracy():
    """测试模糊匹配器：剥离省略号及份额类别，准确定位 6 位基金代码"""
    cases = [
        ("创金合信中证红利...", "005561"),
        ("易方达沪深300ETF联接A", "110020"),
        ("华夏上证科创板50成份ETF联接C", "011613"),
        ("富国中证红利指数增强A", "100032"),
        ("招商中证白酒指数(LOF)A", "161725"),
        ("华安纳斯达克100ETF联接A", "017436"),
        ("易方达裕祥回报债券A", "002351"),
        ("博时标普500ETF联接A", "050025"),
        ("易方达蓝筹精选混合", "005827"),
    ]
    for raw_name, expected_code in cases:
        res = fuzzy_match_fund_by_name(raw_name)
        assert res.get("fund_code") == expected_code, f"Failed for {raw_name}: got {res}"


def test_activerisksentry_dimension_13_tail_cleaner():
    """测试 ActiveRiskSentry 维度 13 碎片尾仓清理预警"""
    sentry = ActiveRiskSentry()

    # 1. 含有单只满期尾仓的测试组合
    test_holdings = [
        {"fund_code": "001551", "fund_name": "天弘中证500C", "market_value": 50.0, "holding_days": 400, "share_class": "C"},
        {"fund_code": "005561", "fund_name": "创金合信红利低波A", "market_value": 50000.0, "holding_days": 400, "share_class": "A"},
    ]
    rep = sentry.inspect_portfolio(test_holdings)
    tail_alerts = [a for a in rep["alerts"] if a.get("dimension") == "碎片尾仓清理"]
    assert len(tail_alerts) == 1
    assert tail_alerts[0]["action_type"] == "sweep_tail_funds"
    assert tail_alerts[0]["tail_count"] == 1
    assert abs(tail_alerts[0]["recoverable_cash"] - 50.0) < 1e-4

    # 2. 纯核心底仓组合（无碎片）
    clean_holdings = [
        {"fund_code": "005561", "fund_name": "创金合信红利低波A", "market_value": 50000.0, "holding_days": 400, "share_class": "A"},
        {"fund_code": "110020", "fund_name": "易方达沪深300A", "market_value": 40000.0, "holding_days": 400, "share_class": "A"},
    ]
    clean_rep = sentry.inspect_portfolio(clean_holdings)
    clean_tail_alerts = [a for a in clean_rep["alerts"] if a.get("dimension") == "碎片尾仓清理"]
    assert len(clean_tail_alerts) == 0


def test_combat_29_funds_ledger_exact_accounting():
    """测试 combat_29_funds 实战账本：严格 29 只基金，总市值严格平账至 ¥26,615.10，400天满期免赎"""
    mlm = MultiLedgerManager.get_instance()
    meta = mlm.get_ledger_meta("combat_29_funds")
    assert meta is not None, "combat_29_funds metadata must be registered"
    assert meta.get("default_tier") == "C3"

    pm = mlm.get_pm("combat_29_funds")
    assert len(pm.holdings) == 29, f"Expected 29 holdings, got {len(pm.holdings)}"
    assert abs(pm.total_market_value - 26615.10) < 0.05, f"Market value {pm.total_market_value} != 26615.10"

    # 验证持有天数全部 >= 365天 (成立满1年以上，零赎回费免赎)
    for code, h in pm.holdings.items():
        assert len(h.batches) >= 1
        for b in h.batches:
            assert b.holding_days >= 365, f"Fund {code} batch holding days {b.holding_days} < 365"

    # 验证 ActiveRiskSentry 巡检准确识别 19 只碎片尾仓与 ¥442.70 回收资金
    sentry = ActiveRiskSentry()
    rep = sentry.inspect_portfolio(pm.holdings)
    tail_alerts = [a for a in rep["alerts"] if a.get("dimension") == "碎片尾仓清理"]
    assert len(tail_alerts) == 1, "Must trigger 碎片尾仓清理"
    alert = tail_alerts[0]
    assert alert["tail_count"] == 19, f"Expected 19 tail funds, got {alert['tail_count']}"
    assert abs(alert["recoverable_cash"] - 442.70) < 0.05, f"Expected 442.70 cash, got {alert['recoverable_cash']}"

    # 腰部持仓 (005827 124.14元, 161725 524.24元, 000217 395.73元) 严禁被误判为碎片尾仓
    tail_codes = alert["tail_codes"]
    assert "005827" not in tail_codes, "005827 is waist fund, must not be in tail_codes"
    assert "161725" not in tail_codes, "161725 is waist fund, must not be in tail_codes"
    assert "000217" not in tail_codes, "000217 is waist fund, must not be in tail_codes"

    # 验证一键清理场景调仓：零赎回费归拢至 002351
    plan = pm.generate_scenario_rebalance_plan({}, scenario_mode="sweep_tail_and_c_class", core_anchor_code="002351")
    assert len(plan["sell_actions"]) == 19, f"Expected 19 sell actions, got {len(plan['sell_actions'])}"
    assert abs(plan["total_sell_amount"] - 442.70) < 0.05, f"Expected 442.70 sell amount, got {plan['total_sell_amount']}"
    assert plan["total_redemption_fee"] == 0.0, f"Expected 0.0 redemption fee, got {plan['total_redemption_fee']}"


def test_accounting_identity_and_negative_sign_preservation():
    """测试文本与OCR提取时的会计恒等式与负收益保真 (无 abs 篡改，小额尾仓不丢弃)"""
    sample_text = """
    易方达裕祥回报债券A (002351) 持有金额 4101.71 持有收益 -48.89
    天弘中证500C (001551) 持有金额 0.59 持有收益 -0.15
    创金合信中证红利低波指数A (005561) 持有金额 5681.55 持有收益 +112.88
    """
    items = parse_smart_text_holdings(sample_text)
    assert len(items) == 3

    # 检查负收益保真
    f_002351 = next(it for it in items if it["fund_code"] == "002351")
    assert f_002351["floating_pnl"] == -48.89, f"Expected negative pnl -48.89, got {f_002351['floating_pnl']}"
    assert abs(f_002351["cost_basis"] - (4101.71 - (-48.89))) < 0.05

    # 检查微小尾仓 (0.59元) 不被丢弃
    f_001551 = next(it for it in items if it["fund_code"] == "001551")
    assert f_001551["market_value"] == 0.59, f"Expected 0.59 market value, got {f_001551['market_value']}"
    assert f_001551["floating_pnl"] == -0.15

    # 检查别名一致性
    alias_items = parse_batch_fund_text_input(sample_text)
    assert len(alias_items) == len(items)
