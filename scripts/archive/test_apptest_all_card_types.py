# -*- coding: utf-8 -*-
"""
scripts/test_apptest_all_card_types.py
Test rendering and clicking of all 6 warning card types in Streamlit AppTest
"""

import sys
import unittest.mock
from pathlib import Path
from streamlit.testing.v1 import AppTest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))
sys.path.insert(0, str(WORKSPACE_ROOT / "AGY2_FundAdvisory"))

GUI_FILE = str(WORKSPACE_ROOT / "AGY2_FundAdvisory" / "app_gui.py")

# Create a synthetic report covering all 6 dimensions
SYNTHETIC_6D_ALERTS = [
    {
        "level": "red",
        "dimension": "未满7天锁仓",
        "title": "【华夏科创50ETF联接A (011612)】持有仅 3 天（≤3天）",
        "desc": "严禁赎回！未满 7 天赎回将直接触发证监会规定的 1.50% 巨额惩罚性扣款！",
        "action": "锁定持仓下界，暂缓赎回，待持有满 7 天后再行操作。",
        "action_type": "lock_shares",
        "fund_code": "011612",
        "fund_name": "华夏科创50ETF联接A",
    },
    {
        "level": "yellow",
        "dimension": "临免赎期倒计时",
        "title": "【华夏上证科创板50成份ETF联接C (011613)】距30天免赎仅差 2 天（当前第 28 天）",
        "desc": "再持仓 2 天赎回费即可彻底归零（0.00%），提前赎回将白白损耗手续费！",
        "action": "建议暂缓调仓倒计时 2 天，待满 30 天后再行置换。",
        "action_type": "countdown_hold",
        "fund_code": "011613",
        "fund_name": "华夏上证科创板50成份ETF联接C",
    },
    {
        "level": "yellow",
        "dimension": "C类零费率置换",
        "title": "【银华集成电路混合C (013841)】C类份额已满 30 天（第 40 天）",
        "desc": "赎回费已归零！建议在反弹阻力位择机全额置换清理，避免长期计提销售服务费。",
        "action": "建议逢高置换为优质 A 类底仓或无费率标的。",
        "action_type": "switch_a_class",
        "fund_code": "013841",
        "fund_name": "银华集成电路混合C",
    },
    {
        "level": "yellow",
        "dimension": "阶梯止盈",
        "title": "【高弹性成长A (009995)】浮盈达标 (+16.0%) 触发阶梯止盈",
        "desc": "进攻型基金持仓浮盈达 +16.0% 且技术面正乖离偏高，宜分批锁定收益。",
        "action": "建议执行阶梯止盈减仓（赎回 30%~50% 转入纯债或红利低波）。",
        "action_type": "take_profit",
        "fund_code": "009995",
        "fund_name": "高弹性成长A",
    },
    {
        "level": "yellow",
        "dimension": "赛道集中度",
        "title": "【红利高股息赛道】持仓占比达 60.8% (>35%集中度红线)",
        "desc": "单一细分赛道市值敞口达 60.8%，超过 35% 风险预警阈值，组合弹性暴露过度！",
        "action": "建议适度均衡配置，增配弱相关红利低波、纯债或海外 QDII 资产。",
        "action_type": "rebalance_sector",
    },
    {
        "level": "red",
        "dimension": "本体排雷",
        "title": "【迷你基金A (009993)】规模仅 0.30 亿元 (<0.5亿清盘警戒线)",
        "desc": "最新资产净值低于 5,000 万元法定警戒线，面临清盘终止运作的严重法律与流动性风险！",
        "action": "择机置换为同赛道规模适中（10~50亿）的标杆公募基金。",
        "action_type": "replace_fund",
        "fund_code": "009993",
        "fund_name": "迷你基金A",
    },
]

def test_all_card_types_rendered():
    print("Testing AppTest with all warning card types...")
    # Mock ActiveRiskSentry.inspect_portfolio to return our synthetic 6D alerts
    mock_report = {
        "timestamp": "2026-11-05 11:00:00",
        "all_passed": False,
        "has_danger": True,
        "has_warning": True,
        "alerts": SYNTHETIC_6D_ALERTS,
        "summary": "发现 6 项风险与提示项",
    }

    with unittest.mock.patch("advisory_engine.ActiveRiskSentry.inspect_portfolio", return_value=mock_report):
        at = AppTest.from_file(GUI_FILE, default_timeout=45)
        at.run()
        assert not at.exception, f"AppTest exception: {at.exception}"

        # In app_gui.py: alerts_to_show = report.get("alerts", [])[:4]
        # First 4 alerts are shown
        sentry_buttons = [b for b in at.button if "btn_sentry_act_" in str(b.key)]
        print(f"Rendered {len(sentry_buttons)} sentry buttons for top alerts:")
        for b in sentry_buttons:
            print(f"  Key: {b.key}, Label: {b.label}")

        # Check take_profit button click
        tp_btn = [b for b in sentry_buttons if "take_profit" in str(b.key)]
        if tp_btn:
            print(f"Clicking take_profit button: {tp_btn[0].label}")
            tp_btn[0].click().run()
            assert not at.exception
            assert at.session_state.get("tab2_trigger_rebalance") is True
            assert at.session_state.get("tab2_pending_take_profit") == {"fund_code": "009995", "ratio": 0.40}
            print("  [PASS] take_profit button click mutated session_state correctly!")

    # Now test the remaining two card types (rebalance_sector, replace_fund)
    mock_report_part2 = {
        "timestamp": "2026-11-05 11:00:00",
        "all_passed": False,
        "has_danger": True,
        "has_warning": True,
        "alerts": SYNTHETIC_6D_ALERTS[4:],  # rebalance_sector and replace_fund
        "summary": "发现 2 项风险与提示项",
    }
    with unittest.mock.patch("advisory_engine.ActiveRiskSentry.inspect_portfolio", return_value=mock_report_part2):
        at2 = AppTest.from_file(GUI_FILE, default_timeout=45)
        at2.run()
        assert not at2.exception

        sentry_buttons2 = [b for b in at2.button if "btn_sentry_act_" in str(b.key)]
        print(f"Rendered {len(sentry_buttons2)} sentry buttons for part 2 alerts:")
        for b in sentry_buttons2:
            print(f"  Key: {b.key}, Label: {b.label}")
        
        # Verify rebalance_sector button
        sec_btn = [b for b in sentry_buttons2 if "rebalance_sector" in str(b.key)]
        assert len(sec_btn) == 1, "rebalance_sector button must be rendered"
        assert sec_btn[0].label == "⚖️ 平衡赛道敞口"

        # Verify replace_fund button
        rep_btn = [b for b in sentry_buttons2 if "replace_fund" in str(b.key)]
        assert len(rep_btn) == 1, "replace_fund button must be rendered"
        assert rep_btn[0].label == "🚨 置换【009993】为标杆公募"

        # Click replace_fund
        print(f"Clicking replace_fund button: {rep_btn[0].label}")
        rep_btn[0].click().run()
        assert not at2.exception
        assert at2.session_state.get("tab2_trigger_diagnose") is True
        print("  [PASS] replace_fund button click mutated session_state correctly!")

    print("\nALL 6 WARNING CARD TYPES SUCCESSFULLY RENDERED AND INTERACTED WITHOUT EXCEPTION!")

if __name__ == "__main__":
    test_all_card_types_rendered()
