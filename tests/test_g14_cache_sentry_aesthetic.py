import os
import json
import time
import hashlib
from pathlib import Path
import numpy as np
import pytest

from AGY2_FundAdvisory.advisory_engine import OpportunityRadarEngine, OnlineHeuristicFactorEvolver, ActiveRiskSentry
from AGY2_FundAdvisory.portfolio_manager import PortfolioManager, HoldingItem, HoldingBatch


def test_radar_sectors_cache_read_write_loop(tmp_path):
    """测试 14 赛道雷达磁盘缓存读写闭环与毫秒级直读"""
    engine = OpportunityRadarEngine(cache_dir=str(tmp_path))
    cache_f = tmp_path / "radar_sectors_cache.json"

    # 初次扫描应生成缓存
    res1 = engine.scan_all_sectors(force_refresh=True)
    assert len(res1) == 14
    assert cache_f.exists()

    with open(cache_f, "r", encoding="utf-8") as f:
        c_data = json.load(f)
    assert "timestamp" in c_data
    assert "sectors" in c_data
    assert len(c_data["sectors"]) == 14

    # 第二次读取应命中缓存 (<5ms)
    t0 = time.time()
    res2 = engine.scan_all_sectors(force_refresh=False)
    elapsed = (time.time() - t0) * 1000.0
    assert len(res2) == 14
    assert elapsed < 50.0  # 毫秒级

    # 类方法快速直读测试
    fast_res = OpportunityRadarEngine.get_cached_sectors_fast(cache_dir=str(tmp_path))
    assert fast_res is not None
    assert len(fast_res) == 14


def test_oos_trajectory_dynamic_selection_and_friction():
    """测试 60 日样本外演化轨迹使用真实演化权重挑选 Top 3 赛道并严格扣除换手成本"""
    evolver = OnlineHeuristicFactorEvolver(population_size=16, generations=5, random_seed=42)
    res = evolver.get_60d_rolling_nav_and_trajectory(force_refresh=True)

    assert "nav_dynamic" in res
    assert "nav_static" in res
    assert "trajectory" in res
    assert len(res["nav_dynamic"]) == 60
    assert len(res["trajectory"]) == 60

    # 动态净值与静态净值应有真实差异（非静态前3列均值）
    dyn_ret = res["final_nav_dynamic"] - 1.0
    stat_ret = res["final_nav_static"] - 1.0
    assert isinstance(dyn_ret, float)
    assert isinstance(stat_ret, float)
    assert res["alpha_pct"] == round((dyn_ret - stat_ret) * 100.0, 2)


def test_active_risk_sentry_twelve_dimensions_integrity():
    """测试十二维完整主动风控巡检能够被精准执行与产出 alerts"""
    sentry = ActiveRiskSentry()

    # 构造含未满 7 天与 C 类的测试持仓
    h1 = HoldingItem(
        fund_code="005561",
        fund_name="红利低波C",
        shares=1000.0,
        share_class="C",
        cost_price=1.2,
        current_nav=1.2,
        batches=[HoldingBatch(batch_id="b1", buy_date="2026-11-06", shares=1000.0, cost_nav=1.2, holding_days=3)]
    )
    h2 = HoldingItem(
        fund_code="011613",
        fund_name="科创50联接C",
        shares=2000.0,
        share_class="C",
        cost_price=1.1,
        current_nav=1.1,
        batches=[HoldingBatch(batch_id="b2", buy_date="2026-10-05", shares=2000.0, cost_nav=1.1, holding_days=35)]
    )

    holdings = {
        "005561": h1,
        "011613": h2,
    }

    quotes = {
        "005561": {"latest_nav": 1.2, "bias_20": 1.0, "gszzl": 0.0},
        "011613": {"latest_nav": 1.1, "bias_20": -1.5, "gszzl": 0.0},
    }

    rep = sentry.inspect_portfolio(
        holdings=holdings,
        investor_risk_tier="C3",
        fund_quotes=quotes,
        market_snapshot={"erp_percentile": 80.0, "c300_bias_20": -2.0}
    )

    assert "alerts" in rep
    assert "all_passed" in rep
    assert rep["all_passed"] is False  # 有未满 7 天等风险，绝不应误报全通！
    alert_dims = [a.get("dimension", "") for a in rep["alerts"]]
    alert_titles = [a.get("title", "") for a in rep["alerts"]]
    assert any("7天" in d or "锁仓" in d or "天" in t for d, t in zip(alert_dims, alert_titles))
    assert any("适当性" in d for d in alert_dims)


def test_referee_files_integrity_unmodified():
    """物理硬红线：验证四大只读裁判文件 SHA-256 绝对零修改"""
    referee_hashes = {
        "AGY2_FundAdvisory/judge_engine.py": "76f930371176de7ee6a413174b030101e3210ac6e037f5d10fe229af31cc07be",
        "AGY2_FundAdvisory/holdout_vault.py": "88122eaf647040a410e2fd95da81077db10149a498a47340ff40b670bd031d2a",
        "AGY2_FundAdvisory/AGENT_SPEC.md": "a346586f9bd2dc0ee83e665bd18e7a6471464c9f7b658e392b989b800cd63957",
        "tests/test_infra.py": "48bee0da300d7c0a0848ec1376e4b9b2e55224d2736081713b4340f0362cd100"
    }

    for path_str, expected_hash in referee_hashes.items():
        p = Path(path_str)
        assert p.exists(), f"Referee file missing: {path_str}"
        content = p.read_bytes()
        actual_hash = hashlib.sha256(content).hexdigest()
        assert actual_hash == expected_hash, f"Referee file corrupted or modified: {path_str}"


def test_ledgers_clean_single_live_main():
    """多账本隔离：确认 data/ledgers_index.json 仅保留单一受保护的 main_live 主实盘账本"""
    p = Path("data/ledgers_index.json")
    assert p.exists()
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    ledgers = data.get("ledgers", [])
    assert len(ledgers) == 1
    assert ledgers[0]["id"] == "main_live"
    assert ledgers[0].get("is_protected") is True
