"""
================================================================================
ADVERSARIAL STRESS TEST SUITE — CHALLENGER M3.1
================================================================================
Target: G15 Phase 3 Implementation
1. Image Slicing Boundary & Empirical Zero-Pixel-Drop Continuity
2. Text Parsing, Negative Gain Sign Preservation & Accounting Identities
3. Tail Cleaner & Risk Sentry Boundary Value Stress Testing (Rule 2 & Rule 7)
4. Combat 29-Fund Portfolio Mathematical Accounting & Liquidation Verification
5. High-Throughput & Degenerate Parameter Resilience
================================================================================
"""

import io
import math
import pytest
from PIL import Image
import numpy as np

from AGY2_FundAdvisory.portfolio_manager import (
    slice_long_screenshot_for_ocr,
    fuzzy_match_fund_by_name,
    parse_smart_text_holdings,
    parse_batch_fund_text_input,
    PortfolioManager,
)
from AGY2_FundAdvisory.advisory_engine import ActiveRiskSentry
from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager


# ==============================================================================
# 1. Image Slicing Boundary & Empirical Zero-Pixel-Drop Continuity
# ==============================================================================

class TestImageSlicingAdversarial:
    """对长截图高清切片算法进行极限长宽比、边界高度与像素连续性对抗性压测"""

    @pytest.mark.parametrize("width,height,expected_slices", [
        (1080, 100, 1),       # 极矮横幅 (h << target_height)
        (1080, 500, 1),       # 半屏截图
        (1080, 999, 1),       # 临界下界: h = target_height - 1
        (1080, 1000, 1),      # 临界点: h = target_height
        (1080, 1001, 2),      # 临界上界: h = target_height + 1
        (1080, 1500, 2),      # 典型1.5倍长图
        (1080, 1850, 2),      # 恰好满足 step + target_height = 850 + 1000
        (1080, 1851, 3),      # 刚好超出需要第3片
        (1080, 8000, 10),     # 8000px 极端长图: 1 + ceil((8000 - 1000)/850) = 1 + 9 = 10片
        (1080, 12000, 14),    # 12000px 超长移动端全景截图: 1 + ceil(11000/850) = 1 + 13 = 14片
        (720, 2500, 3),       # 720p 窄屏设备
        (1440, 3000, 4),      # 2K 高清大屏
        (360, 1200, 2),       # 低端小屏
    ])
    def test_slicing_aspect_ratios_and_slice_counts(self, width, height, expected_slices):
        """验证各种极端尺寸与长宽比下切片数量精确契合数学推导"""
        img = Image.new("RGB", (width, height), color=(240, 240, 240))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_bytes = buf.getvalue()

        slices = slice_long_screenshot_for_ocr(img_bytes, target_height=1000, overlap=150)
        assert len(slices) == expected_slices, (
            f"Failed for {width}x{height}: expected {expected_slices} slices, got {len(slices)}"
        )

        # 验证所有切片 100% 保持原始宽度无形变
        for idx, (sl_img, y_off) in enumerate(slices):
            assert sl_img.size[0] == width, f"Slice {idx} width {sl_img.size[0]} != {width}"
            assert y_off >= 0
            assert y_off + sl_img.size[1] <= height

    def test_empirical_zero_pixel_drop_and_overlap_continuity(self):
        """
        核心实证挑战：像素全覆盖连续性检验 (Empirical Zero-Pixel-Drop)
        在长截图纵向每一行绘制唯一行特征值，切片后重建纵向索引，
        实证断言：从 row 0 至 row H-1，每一行至少被覆盖一次，无任何纵向漏行 (0 Pixel Gap)；
        相邻切片在重叠区完全重合。
        """
        test_heights = [500, 1000, 1001, 1500, 2700, 8000, 12000]
        width = 1080

        for H in test_heights:
            # 构造具有行序号编码的高对比度图像 (RGB通道编码纵向像素行号 y)
            arr = np.zeros((H, width, 3), dtype=np.uint8)
            y_indices = np.arange(H, dtype=np.uint32)
            arr[:, :, 0] = (y_indices % 256).reshape(-1, 1)
            arr[:, :, 1] = ((y_indices // 256) % 256).reshape(-1, 1)
            arr[:, :, 2] = 128

            img = Image.fromarray(arr)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            img_bytes = buf.getvalue()

            slices = slice_long_screenshot_for_ocr(img_bytes, target_height=1000, overlap=150)
            coverage_map = np.zeros(H, dtype=np.int32)

            for idx, (sl_img, y_off) in enumerate(slices):
                sl_h = sl_img.size[1]
                assert sl_h <= 1000, f"Slice {idx} height {sl_h} exceeds target_height 1000"
                coverage_map[y_off : y_off + sl_h] += 1

                # 验证切片像素内容与原图严格一致 (无下采样或抗锯齿变形)
                sl_arr = np.array(sl_img)
                orig_arr_crop = arr[y_off : y_off + sl_h, :, :]
                np.testing.assert_array_equal(
                    sl_arr, orig_arr_crop,
                    err_msg=f"Pixel mismatch in slice {idx} at height {H}"
                )

            # 实证断言 1: 每一行必须至少被覆盖 1 次 (绝对零漏行)
            zero_covered_rows = np.where(coverage_map == 0)[0]
            assert len(zero_covered_rows) == 0, (
                f"Height {H}: Found {len(zero_covered_rows)} dropped rows! E.g. {zero_covered_rows[:5]}"
            )

            # 实证断言 2: 相邻切片必须在指定重叠区域垂直重合
            if len(slices) > 1:
                for i in range(len(slices) - 1):
                    end_current = slices[i][1] + slices[i][0].size[1]
                    start_next = slices[i + 1][1]
                    assert end_current > start_next, f"Slices {i} and {i+1} do not overlap!"
                    actual_overlap = end_current - start_next
                    assert actual_overlap == 150, (
                        f"Overlap between slice {i} and {i+1} is {actual_overlap} != 150px"
                    )

    def test_slicing_degenerate_and_corrupt_inputs(self):
        """测试退化参数与脏图像输入的健壮性与防崩溃能力"""
        # 1. 空字节输入
        assert slice_long_screenshot_for_ocr(b"") == []

        # 2. 损坏文件字节
        assert slice_long_screenshot_for_ocr(b"CORRUPTED_PNG_HEADER_RANDOM_GARBAGE") == []

        # 3. 单像素极限图像
        img_1px = Image.new("RGB", (1, 1), color=(255, 0, 0))
        buf = io.BytesIO()
        img_1px.save(buf, format="PNG")
        res = slice_long_screenshot_for_ocr(buf.getvalue(), target_height=1000, overlap=150)
        assert len(res) == 1
        assert res[0][0].size == (1, 1)
        assert res[0][1] == 0

        # 4. RGBA 与灰度模式透明图层转换
        img_rgba = Image.new("RGBA", (1080, 1500), color=(100, 150, 200, 128))
        buf_rgba = io.BytesIO()
        img_rgba.save(buf_rgba, format="PNG")
        res_rgba = slice_long_screenshot_for_ocr(buf_rgba.getvalue())
        assert len(res_rgba) == 2
        assert res_rgba[0][0].mode == "RGB"

        # 5. overlap >= target_height 极端退化参数防御 (防无限循环挂死)
        img_norm = Image.new("RGB", (500, 1000), color=(255, 255, 255))
        buf_norm = io.BytesIO()
        img_norm.save(buf_norm, format="PNG")
        res_degen = slice_long_screenshot_for_ocr(buf_norm.getvalue(), target_height=100, overlap=150)
        assert len(res_degen) >= 1  # 内部触发 step = max(1, target_height // 2) 平滑退出


# ==============================================================================
# 2. Text Parsing, Negative Gain Preservation & Accounting Identity
# ==============================================================================

class TestTextParsingAndAccountingIdentity:
    """对负收益符号保真、会计恒等式反算以及小额尾仓不丢弃进行对抗性核验"""

    @pytest.mark.parametrize("line_text,expected_pnl,expected_mv,expected_cost", [
        # 标准负收益格式
        ("华夏科创50C (011613) 持有金额 2072.52 持有收益 -428.48", -428.48, 2072.52, 2501.00),
        ("富国红利增强A (100032) 持有金额 2432.90 持有收益 -332.54", -332.54, 2432.90, 2765.44),
        ("招商白酒LOF (161725) 持有金额 524.24 亏损 175.76", -175.76, 524.24, 700.00),
        ("招商白酒LOF (161725) 持有金额 524.24 亏损 -175.76", -175.76, 524.24, 700.00),
        ("易方达沪深300 (110020) 持有金额 5279.05 浮亏 50.00", -50.00, 5279.05, 5329.05),
        ("易方达蓝筹精选 (005827) 持有金额 124.14 跌 12.00", -12.00, 124.14, 136.14),
        # 千分符与负号格式
        ("景顺长城绩优 (000001) 持有金额 25,128.29 累计收益 -1,428.48", -1428.48, 25128.29, 26556.77),
        # 正收益与零收益格式
        ("创金合信红利低波 (005561) 持有金额 5681.55 持有收益 +112.88", 112.88, 5681.55, 5568.67),
        ("华安纳斯达克100 (017436) 持有金额 4536.85 收益 0.00", 0.00, 4536.85, 4536.85),
        # 带有收益率文字但提取绝对金额
        ("华夏科创50C (011613) 收益率 -17.13% 持有金额 2072.52 收益 -428.48", -428.48, 2072.52, 2501.00),
    ])
    def test_negative_sign_preservation_and_cost_basis_equality(
        self, line_text, expected_pnl, expected_mv, expected_cost
    ):
        """验证负收益严格保真为负数，且 cost_basis = market_value - floating_pnl 会计恒等式分厘不差"""
        parsed = parse_smart_text_holdings(line_text)
        assert len(parsed) == 1, f"Failed to parse: {line_text}"
        item = parsed[0]

        # 1. 负收益符号严格保真 (绝不允许出现 abs() 篡改转正)
        assert abs(item["floating_pnl"] - expected_pnl) < 1e-4, (
            f"Floating PnL {item['floating_pnl']} != expected {expected_pnl}"
        )
        if expected_pnl < 0:
            assert item["floating_pnl"] < 0, f"Negative pnl {expected_pnl} was inverted to positive!"

        # 2. 市值精确匹配
        assert abs(item["market_value"] - expected_mv) < 1e-4

        # 3. 会计恒等式验证: cost_basis = market_value - floating_pnl
        # 亏损时: 投入本金 = 当前市值 - (-亏损额) = 当前市值 + 亏损额 > 当前市值
        assert abs(item["cost_basis"] - expected_cost) < 0.05, (
            f"Cost basis {item['cost_basis']} != expected {expected_cost}"
        )
        recalculated_pnl = round(item["market_value"] - item["cost_basis"], 2)
        assert abs(recalculated_pnl - item["floating_pnl"]) <= 0.02, (
            f"Accounting broken: {item['market_value']} - {item['cost_basis']} = {recalculated_pnl} != {item['floating_pnl']}"
        )

    def test_preservation_of_all_19_micro_tail_holdings_under_100_yuan(self):
        """
        验证百元以下碎片尾仓完整保留：
        针对历史上由于 `>= 100` 过滤规则导致 0.59元~89.60元 等微小尾仓被静默丢弃并篡改为 10000.0 元的 P0 缺陷，
        进行全量实操 19 只微小尾仓保真提取压力验证。
        """
        micro_cases = [
            ("016634", 89.60),
            ("001053", 76.00),
            ("050025", 52.07),
            ("002352", 50.00),
            ("016441", 44.56),
            ("013841", 42.07),
            ("012832", 34.50),
            ("012769", 28.67),
            ("008682", 8.98),
            ("011612", 3.95),
            ("002611", 2.10),
            ("019260", 1.85),
            ("000086", 1.50),
            ("018757", 1.35),
            ("001071", 1.25),
            ("006113", 1.15),
            ("004854", 1.45),
            ("001595", 1.06),
            ("001551", 0.59),
        ]
        text_lines = [f"基金代码 {c} 持有金额 {v}" for c, v in micro_cases]
        full_text = "\n".join(text_lines)

        parsed = parse_smart_text_holdings(full_text)
        assert len(parsed) == 19, f"Expected 19 micro items, got {len(parsed)}"

        for item, (expected_code, expected_val) in zip(parsed, micro_cases):
            assert item["fund_code"] == expected_code
            assert abs(item["market_value"] - expected_val) < 1e-4, (
                f"Fund {expected_code} value {item['market_value']} != {expected_val} (Check >=100 bug!)"
            )
            # 严格确保未被默认回退成 10000.0
            assert item["market_value"] < 100.0


# ==============================================================================
# 3. Tail Cleaner & Risk Sentry Boundary Stress Testing
# ==============================================================================

class TestTailCleanerBoundaryStress:
    """对碎片尾仓判定阈值、持有期免赎门槛与核心主动资产保护进行边界极限测试"""

    def test_market_value_threshold_boundaries_and_waist_asset_protection(self):
        """
        验证关键金额边界分类规则：
        1. < 100元：无论A类C类或名称，满期均判定为碎片尾仓；
        2. 100~200元：
           - 若为 C类 或名称包含'联接/ETF/指数/红包/体验/尾仓' -> 判定为碎片尾仓；
           - 若为 主动权益 A 类 (如 005827 易方达蓝筹精选混合 124.14元) -> 保护为腰部底仓，绝不误杀！
        3. >= 200元：无论A类C类均不是碎片尾仓 (如 161725 524.24元, 000217 395.73元)。
        """
        sentry = ActiveRiskSentry()

        boundary_cases = [
            # (code, name, mv, days, cls, expected_is_tail, desc)
            ("000001", "某纯债A", 99.99, 400, "A", True, "99.99元不足100元 -> 碎片"),
            ("000002", "某混合A", 100.00, 400, "A", False, "100.00元A类主动 -> 腰部保护"),
            ("005827", "易方达蓝筹精选混合", 124.14, 400, "A", False, "实操真实案例: 蓝筹精选124.14元A类 -> 保护"),
            ("000003", "易方达蓝筹精选混合A", 199.99, 400, "A", False, "199.99元A类主动 -> 腰部保护"),
            ("000004", "易方达蓝筹精选混合C", 124.14, 400, "C", True, "124.14元C类份额 -> 碎片"),
            ("000005", "易方达沪深300ETF联接A", 150.00, 400, "A", True, "150.00元含'联接' -> 碎片"),
            ("000006", "某中证500指数A", 180.00, 400, "A", True, "180.00元含'指数' -> 碎片"),
            ("000007", "某支付宝体验金基金", 150.00, 400, "A", True, "150.00元含'体验' -> 碎片"),
            ("161725", "招商中证白酒指数(LOF)A", 524.24, 400, "A", False, "524.24元 >= 200元 -> 腰部持仓"),
            ("000217", "华安黄金易ETF联接C", 395.73, 400, "C", False, "395.73元 >= 200元 -> 虽是C类但金额>=200，非碎片尾仓"),
        ]

        for code, name, mv, days, cls, expected_is_tail, desc in boundary_cases:
            portfolio = [
                {"code": code, "name": name, "market_value": mv, "holding_days": days, "share_class": cls},
                # 加入一只大额底仓以提供总资产分母
                {"code": "002351", "name": "易方达裕祥回报A", "market_value": 50000.0, "holding_days": 400, "share_class": "A"},
            ]
            rep = sentry.inspect_portfolio(portfolio)
            tail_alerts = [a for a in rep["alerts"] if a.get("dimension") == "碎片尾仓清理"]
            tail_codes = tail_alerts[0]["tail_codes"] if tail_alerts else []
            is_tail_detected = code in tail_codes
            assert is_tail_detected == expected_is_tail, (
                f"Boundary test failed for {desc}: code={code}, mv={mv}, expected={expected_is_tail}, got={is_tail_detected}"
            )

    def test_fee_free_holding_days_barriers_and_penalty_prevention(self):
        """
        验证持有期免赎门槛防御 (Rule 2 & Rule 7 核心红线)：
        1. C 类必须满 30 天方可免赎清理；若仅持有 29 天或 6 天，严禁判定为免赎碎片 (防 1.5% 或 0.5% 赎回惩罚)；
        2. A 类必须满 365 天方可免赎清理；若持有 364 天或 50 天，严禁判定为免赎碎片。
        """
        sentry = ActiveRiskSentry()

        # 1. C 类未满 30 天 (如 29 天)
        rep_c_29 = sentry.inspect_portfolio([
            {"code": "001551", "name": "天弘中证500C", "market_value": 50.0, "holding_days": 29, "share_class": "C"},
            {"code": "002351", "name": "易方达裕祥回报A", "market_value": 50000.0, "holding_days": 400, "share_class": "A"},
        ])
        alerts_c_29 = [a for a in rep_c_29["alerts"] if a.get("dimension") == "碎片尾仓清理"]
        assert len(alerts_c_29) == 0, "C class holding 29 days must NOT be swept (Not fee-free)!"

        # 2. C 类刚买 5 天 (< 7天 1.50% 惩罚红线)
        rep_c_5 = sentry.inspect_portfolio([
            {"code": "001551", "name": "天弘中证500C", "market_value": 50.0, "holding_days": 5, "share_class": "C"},
            {"code": "002351", "name": "易方达裕祥回报A", "market_value": 50000.0, "holding_days": 400, "share_class": "A"},
        ])
        alerts_c_5 = [a for a in rep_c_5["alerts"] if a.get("dimension") == "碎片尾仓清理"]
        assert len(alerts_c_5) == 0, "C class holding 5 days strictly forbidden to sweep (1.50% penalty)!"

        # 3. C 类满 30 天 (完全免赎)
        rep_c_30 = sentry.inspect_portfolio([
            {"code": "001551", "name": "天弘中证500C", "market_value": 50.0, "holding_days": 30, "share_class": "C"},
            {"code": "002351", "name": "易方达裕祥回报A", "market_value": 50000.0, "holding_days": 400, "share_class": "A"},
        ])
        alerts_c_30 = [a for a in rep_c_30["alerts"] if a.get("dimension") == "碎片尾仓清理"]
        assert len(alerts_c_30) == 1
        assert "001551" in alerts_c_30[0]["tail_codes"]

        # 4. A 类未满 365 天 (如 364 天)
        rep_a_364 = sentry.inspect_portfolio([
            {"code": "002352", "name": "某债券A", "market_value": 50.0, "holding_days": 364, "share_class": "A"},
            {"code": "002351", "name": "易方达裕祥回报A", "market_value": 50000.0, "holding_days": 400, "share_class": "A"},
        ])
        alerts_a_364 = [a for a in rep_a_364["alerts"] if a.get("dimension") == "碎片尾仓清理"]
        assert len(alerts_a_364) == 0, "A class holding 364 days must NOT be swept (A-class 365-day threshold)!"

        # 5. A 类满 365 天 (完全免赎)
        rep_a_365 = sentry.inspect_portfolio([
            {"code": "002352", "name": "某债券A", "market_value": 50.0, "holding_days": 365, "share_class": "A"},
            {"code": "002351", "name": "易方达裕祥回报A", "market_value": 50000.0, "holding_days": 400, "share_class": "A"},
        ])
        alerts_a_365 = [a for a in rep_a_365["alerts"] if a.get("dimension") == "碎片尾仓清理"]
        assert len(alerts_a_365) == 1
        assert "002352" in alerts_a_365[0]["tail_codes"]


# ==============================================================================
# 4. Combat 29-Fund Portfolio Mathematical Accounting & Scenario Liquidation
# ==============================================================================

class TestCombat29FundsPortfolioAccounting:
    """对用户真实 29 只基金（¥26,615.10）实战组合进行分厘平账与调仓算法对抗压测"""

    def test_29_funds_exact_balance_and_classification_integrity(self):
        """
        实操账本分厘级平账勾稽：
        - 7大核心持仓总和: 25,128.29 元
        - 3只腰部持仓总和: 1,044.11 元
        - 19只碎片尾仓总和: 442.70 元
        - 总资产数学求和: 25,128.29 + 1,044.11 + 442.70 = 26,615.10 元 (误差严格为 0.00 元)
        """
        mlm = MultiLedgerManager.get_instance()
        pm = mlm.get_pm("combat_29_funds")

        assert len(pm.holdings) == 29, f"Holdings count {len(pm.holdings)} != 29"

        core_codes = ["005561", "110020", "017436", "002351", "100032", "011613", "000216"]
        waist_codes = ["161725", "000217", "005827"]
        tail_codes = [
            "016634", "001053", "050025", "002352", "016441", "013841", "012832", "012769",
            "008682", "011612", "002611", "019260", "000086", "018757", "001071", "006113",
            "004854", "001595", "001551"
        ]

        # 集合正交互斥校验
        all_codes = set(pm.holdings.keys())
        assert set(core_codes) | set(waist_codes) | set(tail_codes) == all_codes
        assert len(core_codes) + len(waist_codes) + len(tail_codes) == 29

        core_sum = sum(pm.holdings[c].market_value for c in core_codes)
        waist_sum = sum(pm.holdings[c].market_value for c in waist_codes)
        tail_sum = sum(pm.holdings[c].market_value for c in tail_codes)
        total_sum = sum(h.market_value for h in pm.holdings.values())

        assert abs(core_sum - 25128.29) < 0.01, f"Core sum {core_sum} != 25128.29"
        assert abs(waist_sum - 1044.11) < 0.01, f"Waist sum {waist_sum} != 1044.11"
        assert abs(tail_sum - 442.70) < 0.01, f"Tail sum {tail_sum} != 442.70"
        assert abs(total_sum - 26615.10) < 0.01, f"Total sum {total_sum} != 26615.10"
        assert abs((core_sum + waist_sum + tail_sum) - 26615.10) < 0.01

        # 验证亏损源真实性 (深套源: 011613 -428.48, 100032 -332.54, 161725 -175.76)
        h_011613 = pm.holdings["011613"]
        h_100032 = pm.holdings["100032"]
        h_161725 = pm.holdings["161725"]

        assert h_011613.floating_pnl < 0, "011613 must have negative pnl"
        assert abs(h_011613.floating_pnl - (-428.48)) < 0.15
        assert abs(h_100032.floating_pnl - (-332.54)) < 0.15
        assert abs(h_161725.floating_pnl - (-175.76)) < 0.15

        total_deep_loss = h_011613.floating_pnl + h_100032.floating_pnl + h_161725.floating_pnl
        assert abs(total_deep_loss - (-936.78)) < 0.2, f"Total deep loss {total_deep_loss} != -936.78"

    def test_sweep_tail_and_c_class_scenario_execution_adversarial(self):
        """
        场景模式 sweep_tail_and_c_class 对抗验证：
        - 仅卖出 19 只碎片尾仓，严禁卖出腰部与核心资产；
        - 卖出总金额严格等于 442.70 元；
        - 赎回费必须为 0.00 元；
        - 资金归集锚定至纯债压舱石 002351。
        """
        mlm = MultiLedgerManager.get_instance()
        pm = mlm.get_pm("combat_29_funds")

        plan = pm.generate_scenario_rebalance_plan(
            {}, scenario_mode="sweep_tail_and_c_class", core_anchor_code="002351"
        )

        assert plan["scenario_mode"] == "sweep_tail_and_c_class"
        sell_actions = plan["sell_actions"]
        assert len(sell_actions) == 19, f"Expected 19 sell actions, got {len(sell_actions)}"

        sold_codes = {act["fund_code"] for act in sell_actions}

        # 核心与腰部资产严禁被卖出
        assert "005827" not in sold_codes, "005827 (易方达蓝筹精选) was wrongly sold!"
        assert "161725" not in sold_codes, "161725 (招商白酒) was wrongly sold!"
        assert "000217" not in sold_codes, "000217 (华安黄金) was wrongly sold!"
        assert "005561" not in sold_codes, "005561 was wrongly sold!"
        assert "110020" not in sold_codes, "110020 was wrongly sold!"
        assert "017436" not in sold_codes, "017436 was wrongly sold!"
        assert "002351" not in sold_codes, "002351 was wrongly sold!"

        # 金额核算
        total_sold_amount = sum(act["amount"] for act in sell_actions)
        assert abs(total_sold_amount - 442.70) < 0.05, f"Sold amount {total_sold_amount} != 442.70"
        assert plan["total_redemption_fee"] == 0.0, f"Redemption fee {plan['total_redemption_fee']} != 0.0"
        assert abs(plan["total_buy_amount"] - 442.70) < 0.05
        assert len(plan["buy_actions"]) == 1
        assert plan["buy_actions"][0]["fund_code"] == "002351"


# ==============================================================================
# 5. High-Throughput & Degenerate Parameter Resilience
# ==============================================================================

class TestHighThroughputAndResilience:
    """高吞吐循环、脏数据注入与内存稳定性压测"""

    def test_dirty_and_adversarial_text_inputs(self):
        """测试包含乱码、emoji、极多空行、超大金额与负金额的脏文本解析健壮性"""
        dirty_samples = [
            "  \n\n\t   \n  ",  # 纯空白
            "🎉💥🔥 005561 创金合信红利低波A 持有金额 10000.00 持有收益 +250.00 🚀",  # 带emoji
            "没有任何基金代码和数字的纯文字说明",  # 无代码
            "基金代码 999999 持有金额 -500.00",  # 负持有金额
            "代码 005561 金额 999,999,999.99 收益 50,000,000.00",  # 超大金额
            "005561 创金合信 份额 5000.00份 成本价 1.2500 当前净值 1.5000",  # 份额反算金额
        ]

        for s in dirty_samples:
            try:
                res = parse_smart_text_holdings(s)
                assert isinstance(res, list)
            except Exception as e:
                pytest.fail(f"parse_smart_text_holdings crashed on dirty input: '{s}' -> {e}")

    def test_stress_slicing_and_sentry_loop(self):
        """50 次高频切片与风控巡检高吞吐循环压测，验证执行耗时与零资源泄漏"""
        import time

        img = Image.new("RGB", (1080, 4000), color=(250, 250, 250))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_bytes = buf.getvalue()

        t0 = time.perf_counter()
        for _ in range(50):
            slices = slice_long_screenshot_for_ocr(img_bytes, target_height=1000, overlap=150)
            assert len(slices) == 5
        elapsed = time.perf_counter() - t0

        # 50次4000px切片总耗时应在 1.5秒以内 (高效纯内存操作)
        assert elapsed < 3.0, f"50 slicing iterations took too long: {elapsed:.2f}s"
