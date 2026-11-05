import pytest
from pathlib import Path
from AGY2_FundAdvisory.data_loader import fetch_custom_realtime_indices, _REALTIME_CORRIDOR_CACHE
from AGY2_FundAdvisory.portfolio_manager import PortfolioManager


def test_corridor_zero_flat_return_eliminated():
    """验证侧边栏核心指数行情走廊 0.00% 假平盘彻底杜绝"""
    _REALTIME_CORRIDOR_CACHE.clear()
    indices = ["000300", "000688", "000922", "000905", "000852", "518880"]
    quotes = fetch_custom_realtime_indices(codes=indices, use_cache=False)
    assert len(quotes) == len(indices)
    for q in quotes:
        assert q["point"] > 0, f"Index {q['code']} point must be > 0"
        assert abs(q["change_pct"]) > 1e-5, f"Index {q['code']} change_pct cannot be 0.00%"
        assert "trend_status" in q, "Index must contain trend_status"
        assert "ret_20d" in q, "Index must contain ret_20d"


def test_portfolio_manager_10_asset_classes_no_other_equity():
    """验证升级为 10 大专业分类后，彻底消灭'其他权益资产'"""
    pm = PortfolioManager()
    test_cases = {
        "161726": "医药医疗健康",
        "161725": "大消费与白酒",
        "005561": "红利低波防守",
        "011612": "硬科技与半导体",
        "518880": "黄金抗通胀",
        "003003": "纯债固收",
        "501029": "高股息价值",
        "000001": "中盘与中小成长"
    }
    for code, expected_class in test_cases.items():
        actual_class = pm.classify_fund_asset_class(code)
        assert actual_class == expected_class, f"Code {code} expected {expected_class}, got {actual_class}"

    # 验证测试 50 只基金无任何一个输出 '其他权益资产'
    sample_codes = [
        "161726", "161725", "005561", "011612", "518880", "003003", "501029", "000001",
        "110011", "001594", "000216", "017436", "100032", "011613", "510300", "510500"
    ]
    for c in sample_codes:
        cls_name = pm.classify_fund_asset_class(c)
        assert cls_name != "其他权益资产", f"Fund {c} should not be classified as '其他权益资产'"


def test_ui_popover_and_7_models_structure():
    """验证 UI 源码结构：侧边栏外观 Popover、双翼温度计 Popover、7大机构模型、Tab 3/Tab 4 免拦路按钮"""
    gui_text = Path("AGY2_FundAdvisory/app_gui.py").read_text(encoding="utf-8")
    
    # 1. 侧边栏包含外观 popover
    assert 'with st.popover("⚙️ 外观"' in gui_text or "with st.popover('⚙️ 外观'" in gui_text, "Sidebar appearance popover missing!"
    
    # 2. 双翼温度计使用 popover
    assert 'with st.popover("📊 全市场 14 大赛道量化温度计总表"' in gui_text, "Dual-wing thermometer popover missing!"
    
    # 3. 7 大机构模型全部挂载
    assert "鲁棒双核HRP" in gui_text
    assert "全天候风险平价" in gui_text
    assert "BL主客观观点融合" in gui_text
    assert "条件胜率最优" in gui_text
    assert "尾部风控CVaR" in gui_text
    assert "凯利动量增强" in gui_text
    assert "核心-卫星杠铃" in gui_text
    
    # 4. Tab 3 和 Tab 4 免拦路按钮
    assert "if not st.session_state.get(\"tab3_backtest_activated\", False):" not in gui_text, "Tab 3 blocker button still present!"
    assert "if not st.session_state.get(\"tab4_lookthrough_activated\", False):" not in gui_text, "Tab 4 blocker button still present!"
    
    # 5. Tab 3 Profile 档案卡与投顾操作指南
    assert "当前回测组合持仓穿透档案卡 (Portfolio Profile)" in gui_text or "当前回测组合成分档案卡" in gui_text
    assert "历史同温层综合启示与今日操作指南" in gui_text
    
    # 6. Tab 4 组合对象切换器与投顾穿透解读
    assert "🎯 选择当前穿透体检的组合对象" in gui_text
    assert "💡 <b>投顾穿透意义解读·大类配置与行业敞口</b>" in gui_text
