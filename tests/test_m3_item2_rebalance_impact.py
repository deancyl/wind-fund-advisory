import pytest
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "AGY2_FundAdvisory") not in sys.path:
    sys.path.insert(0, str(ROOT / "AGY2_FundAdvisory"))

from strategy_bridge import StrategyBridge
from multi_ledger_manager import MultiLedgerManager


def test_combat_29_rebalance_prescription_structure():
    """验证针对 29 基实战账本的三步重构调仓处方数据结构完整性"""
    rx = StrategyBridge.get_combat_29_rebalance_prescription()
    assert "step1_tail_cleanup" in rx
    assert "step2_deep_loss_surgery" in rx
    assert "step3_core_reconstruction" in rx
    assert "metrics_comparison" in rx

    # 步骤一：19 只碎片尾仓清扫
    step1 = rx["step1_tail_cleanup"]
    assert step1["count"] == 19
    assert step1["amount"] == 442.70
    assert step1["fee"] == 0.00

    # 步骤二：三大深套亏损源手术
    step2 = rx["step2_deep_loss_surgery"]
    assert len(step2["items"]) == 3
    assert step2["total_loss"] == -936.78
    codes = [it["code"] for it in step2["items"]]
    assert "011613" in codes
    assert "100032" in codes
    assert "161725" in codes

    # 步骤三：6 只核心全天候压舱石
    step3 = rx["step3_core_reconstruction"]
    assert len(step3["funds"]) == 6

    # 四维量化对比指标
    metrics = rx["metrics_comparison"]
    assert metrics["fund_count"]["before"] == 29
    assert metrics["fund_count"]["after"] == 6
    assert metrics["revitalized_cash"]["min"] == 442.70
    assert metrics["revitalized_cash"]["max"] == 962.57


def test_estimate_rebalance_impact_combat_29():
    """验证 estimate_rebalance_impact 对 29 基账本的真实影响预估输出"""
    mlm = MultiLedgerManager.get_instance()
    pm = mlm.get_pm("combat_29_funds")

    preset = StrategyBridge.get_combat_29_vs_reconstructed_6_preset()
    target_weights = preset["reconstructed_6_weights"]

    impact = StrategyBridge.estimate_rebalance_impact(
        current_holdings=pm.holdings,
        target_weights_funds=target_weights,
        total_equity=pm.total_equity,
        rebalance_items=[]
    )

    assert impact["fund_count_before"] == 29
    assert impact["fund_count_after"] == 6
    assert impact["revitalized_cash_min"] == 442.70
    assert impact["revitalized_cash_max"] == 962.57
    assert impact["total_fee"] == 0.00
    assert impact["payback_days"] == 0
    assert impact["payback_desc"] == "即时零损耗"
    assert impact["vol_diff"] <= 0.0  # 重构后波动率明显收敛或下降
