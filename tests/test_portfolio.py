"""
投资组合分析与现代资产配置引擎单元测试套件
验证多资产时序加载、加权回测仿真、风险收益指标、相关性矩阵、风险归因及现代优化求解器。
"""

import numpy as np
import pandas as pd
import pytest

from src.analysis.portfolio_analyzer import (
    PortfolioAnalyzer,
    PortfolioDataLoader,
    PortfolioAsset,
    PortfolioMetrics,
    PortfolioAnalysisResult
)
from src.advisory.portfolio_report import PortfolioReportGenerator


@pytest.fixture
def sample_weights():
    return {
        "000300.SH": 0.40,
        "000905.SH": 0.20,
        "CBA00101.CS": 0.40
    }


def test_data_loader_metadata():
    loader = PortfolioDataLoader()
    name, cat = loader.resolve_asset_metadata("000300.SH")
    assert "沪深300" in name
    assert "权益" in cat

    name_bond, cat_bond = loader.resolve_asset_metadata("CBA00101.CS")
    assert "中债" in name_bond
    assert "纯债" in cat_bond


def test_portfolio_backtest_quarterly(sample_weights):
    analyzer = PortfolioAnalyzer()
    res = analyzer.analyze_portfolio(
        weights_map=sample_weights,
        benchmark_code="000300.SH",
        rebalance_freq="quarterly",
        start_date="2020-01-01",
        end_date="2026-10-26"
    )

    assert isinstance(res, PortfolioAnalysisResult)
    assert len(res.assets) == 3
    assert res.metrics.trading_days > 200

    # 验证指标合理性
    m = res.metrics
    assert m.annualized_volatility_pct > 0
    assert 0 <= m.max_drawdown_pct <= 100
    assert m.var_95_pct >= 0
    assert m.cvar_95_pct >= m.var_95_pct - 0.5  # CVaR 尾部亏损应大于等于 VaR

    # 验证资产分散化效益 (加入固收后分散化比率应大于 1.0)
    assert res.diversification.diversification_ratio >= 1.0
    assert res.diversification.portfolio_vol_pct <= res.diversification.weighted_asset_vol_pct + 0.1


def test_portfolio_rebalance_modes(sample_weights):
    analyzer = PortfolioAnalyzer()

    # 测试无再平衡 (买入持有)
    res_none = analyzer.analyze_portfolio(
        weights_map=sample_weights,
        benchmark_code="000300.SH",
        rebalance_freq="none",
        start_date="2023-01-01",
        end_date="2026-10-26"
    )

    # 测试月度再平衡
    res_monthly = analyzer.analyze_portfolio(
        weights_map=sample_weights,
        benchmark_code="000300.SH",
        rebalance_freq="monthly",
        start_date="2023-01-01",
        end_date="2026-10-26"
    )

    assert res_none.history_df is not None
    assert res_monthly.history_df is not None
    assert len(res_none.history_df) == len(res_monthly.history_df)


def test_risk_attribution(sample_weights):
    analyzer = PortfolioAnalyzer()
    res = analyzer.analyze_portfolio(
        weights_map=sample_weights,
        start_date="2022-01-01",
        end_date="2026-10-26"
    )

    attr = res.attribution
    assert len(attr) == 3

    # 验证风险贡献占比 (PCR) 之和应约等于 100%
    total_pcr = sum(item.risk_contribution_pct for item in attr)
    assert pytest.approx(total_pcr, abs=2.0) == 100.0


def test_portfolio_optimization(sample_weights):
    analyzer = PortfolioAnalyzer()
    res = analyzer.analyze_portfolio(
        weights_map=sample_weights,
        start_date="2022-01-01",
        end_date="2026-10-26"
    )

    proposals = res.optimization_proposals
    assert len(proposals) >= 2  # 至少产生最大夏普与最小方差

    for prop in proposals:
        w_sum = sum(prop.weights.values())
        assert pytest.approx(w_sum, abs=0.01) == 1.0
        assert prop.expected_annual_vol_pct > 0
        assert prop.expected_sharpe_ratio is not None


def test_portfolio_report_generator(sample_weights, tmp_path):
    analyzer = PortfolioAnalyzer()
    res = analyzer.analyze_portfolio(
        weights_map=sample_weights,
        start_date="2024-01-01",
        end_date="2026-10-26"
    )

    reporter = PortfolioReportGenerator()
    md = reporter.generate_markdown(res)
    assert "# 定制多元投资组合" in md
    assert "核心风险与收益量化指标矩阵" in md
    assert "资产间皮尔逊相关系数矩阵" in md

    # 保存研报测试
    file_path = reporter.save_report_to_disk(res, reports_dir=tmp_path)
    assert file_path.exists()
    assert file_path.stat().st_size > 500

    # ASCII 走势图测试
    chart = PortfolioReportGenerator.render_ascii_chart(res.history_df, height=8, width=40)
    assert "走势图例" in chart
    assert "┌" in chart
