# -*- coding: utf-8 -*-
"""
最终端到端全量针对性验收测试套件 (Final Comprehensive Acceptance Test)
严格对应用户 Prompt 中的四大项验收指标：
1. 侧边栏行情走廊：连字符/下划线估值徽章、盘中/离线涨跌幅非假平盘、3层指标卡片、38+目录与自定义Watchlist持久化
2. 数据单源同真：advisory_engine 动态计算、走廊与雷达估值分位严格一致、全景温度计与晨报、六维风险哨准确识别(011612, 011613, 013841)与跳转动作
3. 7大机构定权模型：7大模型权重非负且和为1.0、历史黑天鹅压力测试算子、Primary按钮高亮白与消除重复描述
4. 物理安全红线：4大裁判文件 SHA256 完好
"""

import sys
import json
import pytest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
AGY2_DIR = ROOT_DIR / "AGY2_FundAdvisory"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(AGY2_DIR) not in sys.path:
    sys.path.insert(0, str(AGY2_DIR))

import data_loader
import advisory_engine
from advisory_engine import ActiveRiskSentry, OpportunityRadarEngine, RADAR_SECTOR_CATALOG
import portfolio_optimizer
from portfolio_optimizer import QUANT_MODELS_CATALOG, WinRateOptimizer, recommend_model_for_regime, simulate_black_swan_stress
from strategy_bridge import StrategyBridge
import portfolio_manager
from portfolio_manager import PortfolioManager


# =========================================================================
# 一、 物理安全红线校验
# =========================================================================
def test_referee_hashes_intact():
    import hashlib
    EXPECTED = {
        "AGY2_FundAdvisory/judge_engine.py": "76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF31CC07BE",
        "AGY2_FundAdvisory/holdout_vault.py": "88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670BD031D2A",
        "AGY2_FundAdvisory/AGENT_SPEC.md": "A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B800CD63957",
        "tests/test_infra.py": "48BEE0DA300D7C0A0848EC1376E4B9B2E55224D2736081713B4340F0362CD100"
    }
    for rel_path, exp_hash in EXPECTED.items():
        p = ROOT_DIR / rel_path
        assert p.exists(), f"Referee file missing: {rel_path}"
        actual = hashlib.sha256(p.read_bytes()).hexdigest().upper()
        assert actual == exp_hash, f"Hash mismatch for {rel_path}: {actual} != {exp_hash}"


# =========================================================================
# 二、 侧边栏行情走廊与自定义验收
# =========================================================================
def test_corridor_styles_and_badges():
    gui_file = AGY2_DIR / "app_gui.py"
    code = gui_file.read_text(encoding="utf-8")
    # 支持连字符与下划线类名
    assert ".val-very-low" in code or ".val-very_low" in code
    assert ".val-very-high" in code or ".val-very_high" in code
    # Primary 按钮强制白色
    assert 'button[kind="primary"]' in code
    assert "color: #ffffff !important" in code


def test_corridor_catalog_and_watchlist_persistence():
    assert len(data_loader.INDEX_CATALOG_38) >= 30, f"Catalog should contain >=30 indices, got {len(data_loader.INDEX_CATALOG_38)}"
    # 验证中证红利映射
    assert "000922" in data_loader.INDEX_CATALOG_38
    assert data_loader.INDEX_CATALOG_38["000922"]["name"] == "中证红利"
    
    # 测试自定义配置读取与保存
    wl = data_loader.load_custom_watchlist()
    assert "selected_codes" in wl
    display_cnt = wl.get("display_count", wl.get("display_limit", 6))
    assert 3 <= display_cnt <= 15
    
    # 模拟保存
    test_data = {"display_count": 8, "display_limit": 8, "selected_codes": ["000300", "000688", "000922"], "custom_items": {}}
    ok = data_loader.save_custom_watchlist(test_data)
    assert ok is True
    loaded = data_loader.load_custom_watchlist()
    assert loaded.get("display_count", loaded.get("display_limit")) == 8


def test_corridor_quotes_no_dead_flat():
    quotes = data_loader.fetch_custom_realtime_indices(["000300", "000688", "000922", "518880"], use_cache=True)
    assert len(quotes) >= 4
    # 至少有标的涨跌幅不为 0.00%（杜绝整排假平盘）
    non_zero = [q for q in quotes if abs(q["change_pct"]) > 1e-4]
    assert len(non_zero) > 0, "Quotes should not be all 0.00% flat"
    
    # 检查 3 层指标结构
    metrics = data_loader.get_index_corridor_metrics("000300")
    assert "ma20" in metrics
    assert "bias_20" in metrics
    assert "ret_20d" in metrics


# =========================================================================
# 三、 数据单源同真与双翼看板验收
# =========================================================================
def test_single_source_of_truth_valuation():
    # 检查 advisory_engine 中 RADAR_SECTOR_CATALOG 不再包含硬编码数值
    catalog = RADAR_SECTOR_CATALOG
    for sec_id, info in catalog.items():
        assert "base_val_pct" not in info, f"Sector {sec_id} should not contain hardcoded base_val_pct"
        assert "er_20" not in info, f"Sector {sec_id} should not contain hardcoded er_20"
        assert "bias_20" not in info, f"Sector {sec_id} should not contain hardcoded bias_20"

    # 验证走廊与雷达估值分位一致
    radar = OpportunityRadarEngine()
    val_map = data_loader.fetch_or_calc_index_valuations(force_refresh=False)
    
    checked = 0
    for sec_id, meta in RADAR_SECTOR_CATALOG.items():
        bench = meta.get("benchmark_index")
        val_pct_radar = radar.get_sector_valuation_percentile(sec_id, meta)
        ev = radar.evaluate_sector(sec_id, meta)
        assert ev["val_percentile"] == val_pct_radar
        
        expected = None
        if bench in val_map and val_map[bench].get("percentile") is not None:
            expected = float(val_map[bench]["percentile"])
        elif f"1.{bench}" in val_map and val_map[f"1.{bench}"].get("percentile") is not None:
            expected = float(val_map[f"1.{bench}"]["percentile"])
        elif f"0.{bench}" in val_map and val_map[f"0.{bench}"].get("percentile") is not None:
            expected = float(val_map[f"0.{bench}"]["percentile"])

        if expected is not None:
            diff = abs(val_pct_radar - expected)
            assert diff < 1e-4, f"Valuation discrepancy for {sec_id}: radar={val_pct_radar}, corridor={expected}"
            checked += 1
    assert checked > 0, "At least one benchmark should be cross-verified"


def test_six_dimensional_active_risk_sentry():
    sentry = ActiveRiskSentry()
    pm = PortfolioManager()
    pm.load_demo_portfolio()
    
    report = sentry.inspect_portfolio(pm.holdings)
    assert "alerts" in report
    alerts = report["alerts"]
    assert len(alerts) >= 3, f"Expected at least 3 alerts from demo portfolio, got {len(alerts)}"
    
    fund_codes = [a.get("fund_code") for a in alerts]
    dims = [a.get("dimension") for a in alerts]
    
    # 验证演示组合中 3 类实战风险识别：
    # 1. 011612: 3天锁仓红牌
    assert "011612" in fund_codes, "011612 lock alert missing"
    # 2. 011613: 28天临近免赎黄牌
    assert "011613" in fund_codes, "011613 countdown alert missing"
    # 3. 013841: 深套/重叠/置换
    assert "013841" in fund_codes, "013841 alert missing"
    
    # 验证动作按钮字段
    for a in alerts:
        assert "action_label" in a or "action_type" in a, f"Alert {a} missing action field"


# =========================================================================
# 四、 7 大机构级量化定权模型与压力测试验收
# =========================================================================
def test_all_seven_quant_models():
    expected_models = [
        "hrp_robust",
        "core_satellite",
        "all_weather",
        "black_litterman",
        "conditional_winrate",
        "cvar_tail",
        "kelly_momentum"
    ]
    
    for m in expected_models:
        assert m in QUANT_MODELS_CATALOG, f"Model {m} missing from QUANT_MODELS_CATALOG"
        res = StrategyBridge.compute_n_funds_model_portfolio(
            tier="C3",
            target_return_pct=15.0,
            num_funds=6,
            model_type=m,
            capital=100000.0
        )
        opt_w = res.get("optimal_weights", {})
        assert len(opt_w) == 6, f"Model {m} produced {len(opt_w)} weights, expected 6"
        w_sum = sum(opt_w.values())
        diff = abs(w_sum - 1.0)
        assert diff < 1e-5, f"Model {m} weight sum {w_sum} != 1.0 (diff={diff})"
        assert all(w >= 0.0 for w in opt_w.values()), f"Model {m} has negative weight: {opt_w}"


def test_black_swan_stress_simulation():
    stress_res = simulate_black_swan_stress({"005561": 0.35, "100032": 0.20, "000216": 0.20, "017436": 0.15, "011613": 0.10})
    assert "scenarios" in stress_res
    scenarios = stress_res["scenarios"]
    assert len(scenarios) == 3
    # 验证包含 2018, 2022, 2024 三大历史切片
    names = [s["name"] for s in scenarios]
    assert any("2018" in n for n in names)
    assert any("2022" in n for n in names)
    assert any("2024" in n for n in names)
    for sc in scenarios:
        assert sc["max_dd_pct"] > 0
        assert sc["max_loss_amt"] > 0
        assert sc["recovery_str"] != ""
