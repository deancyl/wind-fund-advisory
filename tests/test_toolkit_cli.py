"""
单元测试：Wind 命令行 CLI 新增子命令测试
"""

import pytest
import subprocess
import sys


def test_cli_watchlist():
    res = subprocess.run([sys.executable, "wind_cli.py", "watchlist"], capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0
    assert "Wind 投顾终端工作台与用户会话画像" in res.stdout
    assert "投顾自选与高频盯盘核心标的" in res.stdout


def test_cli_f10():
    res = subprocess.run([sys.executable, "wind_cli.py", "f10", "600519", "--limit", "2"], capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0
    assert "F10 历期财务核心指标宽表" in res.stdout
    assert "杜邦三因子分析透视" in res.stdout


def test_cli_dividends():
    res = subprocess.run([sys.executable, "wind_cli.py", "dividends", "600519", "--limit", "2"], capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0
    assert "历史分红送配与除权除息流水" in res.stdout


def test_cli_money_flow():
    res = subprocess.run([sys.executable, "wind_cli.py", "money-flow", "--top", "3"], capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0
    assert "行业板块主力净流入" in res.stdout


def test_cli_yield_curve():
    res = subprocess.run([sys.executable, "wind_cli.py", "yield-curve"], capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0
    assert "中债国债各期限收益率基准曲线" in res.stdout
    assert "10Y - 1Y 国债基准期限利差" in res.stdout


def test_cli_etf_flow():
    res = subprocess.run([sys.executable, "wind_cli.py", "etf-flow", "--top", "3"], capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0
    assert "ETF 资金净流入申购榜" in res.stdout
    assert "ETF 各大类资产资金流动聚类看板" in res.stdout


def test_cli_sync_toolkit():
    res = subprocess.run([sys.executable, "wind_cli.py", "sync-toolkit"], capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0
    assert "WindToolkit 数据集同步落盘报告" in res.stdout
