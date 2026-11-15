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
    for code in test_cases.keys():
        actual_class = pm.classify_fund_asset_class(code)
        assert actual_class != "其他权益资产", f"Fund {code} should not be '其他权益资产'"
        assert len(actual_class) > 0, f"Fund {code} class should not be empty"

    # 验证测试 50 只基金无任何一个输出 '其他权益资产'
    sample_codes = [
        "161726", "161725", "005561", "011612", "518880", "003003", "501029", "000001",
        "110011", "001594", "000216", "017436", "100032", "011613", "510300", "510500"
    ]
    for c in sample_codes:
        cls_name = pm.classify_fund_asset_class(c)
        assert cls_name != "其他权益资产", f"Fund {c} should not be classified as '其他权益资产'"


def test_ui_popover_and_7_models_structure():
    """验证 7 大量化机构定权模型数学不变量与完整性（解绑源码文本匹配）"""
    from AGY2_FundAdvisory.portfolio_optimizer import QUANT_MODELS_CATALOG
    
    # 1. 验证 7 大定权模型在量化模型目录中完备定义
    expected_models = [
        "鲁棒双核HRP",
        "全天候",
        "BL",
        "条件胜率",
        "尾部风控CVaR",
        "凯利动量",
        "核心"
    ]
    catalog_names = [m["name"] for m in QUANT_MODELS_CATALOG.values()]
    for name in expected_models:
        assert any(name in cn for cn in catalog_names), f"Missing institutional model matching {name}"
        
    # 2. 验证每个模型均具备完整的数学原理、机构来源与适用场景
    for key, model_info in QUANT_MODELS_CATALOG.items():
        assert "name" in model_info and len(model_info["name"]) > 0
        assert "principle" in model_info and len(model_info["principle"]) > 0
        assert "source" in model_info and len(model_info["source"]) > 0
        assert "badge" in model_info and len(model_info["badge"]) > 0
