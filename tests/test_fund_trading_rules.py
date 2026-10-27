"""
公募基金交易规则与全景费率模块单元测试
"""

from pathlib import Path
import pytest
import pandas as pd
import numpy as np

from src.storage.lakehouse import LakehouseManager
from src.parsers.fund_rules_collector import FundTradingRulesCollector, FundFeeStructure, FundRulesSummary


def test_fund_rules_collector_paths():
    lakehouse = LakehouseManager()
    collector = FundTradingRulesCollector(lakehouse)
    assert collector.rules_path.name == "fund_trading_rules.parquet"


def test_fund_rules_mock_sync(tmp_path):
    lakehouse = LakehouseManager(data_dir=tmp_path)
    lakehouse.master_dir.mkdir(parents=True, exist_ok=True)

    # 构造假数据
    mock_df = pd.DataFrame({
        "symbol": ["000001", "002910", "159915"],
        "wind_code": ["000001.OF", "002910.OF", "159915.SZ"],
        "fund_name": ["华夏成长混合", "易方达丰和债券A", "易方达创业板ETF"],
        "fund_type": ["混合型-偏股", "债券型-混合二级", "指数型-股票"],
        "nav": [1.25, 1.10, 2.30],
        "purchase_status": ["开放申购", "暂停大额申购", "场内买卖"],
        "redemption_status": ["开放赎回", "开放赎回", "场内买卖"],
        "min_purchase_amount": [10.0, 10.0, 100.0],
        "daily_limit_amount": [1e11, 10000.0, 1e11],
        "is_large_amount_limited": [False, True, False],
        "discount_purchase_fee_pct": [0.15, 0.08, 0.00],
        "is_purchase_allowed": [True, True, False],
        "is_redemption_allowed": [True, True, False],
        "est_management_fee": [1.20, 0.30, 0.50],
        "est_custodian_fee": [0.20, 0.10, 0.10],
        "est_sales_service_fee": [0.00, 0.00, 0.00],
        "est_total_operating_fee": [1.40, 0.40, 0.60]
    })
    mock_df.to_parquet(lakehouse.master_dir / "fund_trading_rules.parquet", index=False)

    lakehouse.init_duckdb_views()

    # 测试从 Lakehouse 读取单只基金交易规则
    rule_000001 = lakehouse.get_fund_trading_rule("000001")
    assert rule_000001 is not None
    assert rule_000001["fund_name"] == "华夏成长混合"
    assert rule_000001["purchase_status"] == "开放申购"
    assert rule_000001["est_management_fee"] == 1.20

    rule_002910 = lakehouse.get_fund_trading_rule("002910.OF")
    assert rule_002910 is not None
    assert rule_002910["is_large_amount_limited"] == True
    assert rule_002910["daily_limit_amount"] == 10000.0

    # 测试 DuckDB SQL 统一视图
    res = lakehouse.query_sql("SELECT count(*) as cnt FROM v_fund_trading_rules WHERE is_large_amount_limited=true")
    assert res["cnt"].iloc[0] == 1


def test_fund_fee_structure_dataclass():
    fee = FundFeeStructure(
        fund_code="000001.OF",
        fund_name="华夏成长混合",
        management_fee_pct=1.20,
        custodian_fee_pct=0.20,
        sales_service_fee_pct=0.00,
        total_operating_fee_pct=1.40,
        purchase_status="开放申购",
        redemption_status="开放赎回",
        regular_investment_status="支持",
        min_purchase_amount=10.0,
        min_additional_amount=10.0,
        daily_limit_amount=-1.0,
        min_redemption_shares=1.0,
        purchase_confirm_cycle="T+1",
        redemption_arrive_cycle="T+1",
        subscription_tiers=[
            {"tier": "小于100万元", "fee": "1.50% | 0.15%"},
            {"tier": "大于等于100万元", "fee": "1.20% | 0.12%"}
        ],
        redemption_tiers=[
            {"tier": "小于7天", "fee": "1.50%"},
            {"tier": "大于等于7天", "fee": "0.50%"}
        ]
    )

    assert fee.fund_code == "000001.OF"
    assert fee.management_fee_pct == 1.20
    assert fee.total_operating_fee_pct == 1.40
    assert len(fee.subscription_tiers) == 2
    assert len(fee.redemption_tiers) == 2
    assert fee.redemption_tiers[0]["fee"] == "1.50%"
