"""
单元测试：Wind 命令行 CLI 新增子命令测试
"""

import pytest
import subprocess
import sys
import json


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


def test_cli_forecast():
    # 1. 列表模式
    res1 = subprocess.run([sys.executable, "wind_cli.py", "forecast", "--limit", "3"], capture_output=True, text=True, encoding="utf-8")
    assert res1.returncode == 0
    assert "上市公司业绩预告与业绩快报全景" in res1.stdout

    # 2. 财务排雷扫描模式
    res2 = subprocess.run([sys.executable, "wind_cli.py", "forecast", "600519", "--screen"], capture_output=True, text=True, encoding="utf-8")
    assert res2.returncode == 0
    assert "财务高危排雷与自由现金流诊断" in res2.stdout

    # 3. JSON 模式
    res3 = subprocess.run([sys.executable, "wind_cli.py", "forecast", "600519", "--screen", "--json"], capture_output=True, text=True, encoding="utf-8")
    assert res3.returncode == 0
    data = json.loads(res3.stdout)
    assert data["symbol"] == "600519.SH"
    assert "risk_level" in data

    # 4. 缺省代码时触发基准标的财务排雷
    res4 = subprocess.run([sys.executable, "wind_cli.py", "forecast", "--screen"], capture_output=True, text=True, encoding="utf-8")
    assert res4.returncode == 0
    assert "财务高危排雷与自由现金流诊断" in res4.stdout


def test_cli_chips():
    # 1. 龙虎榜
    res1 = subprocess.run([sys.executable, "wind_cli.py", "chips", "dragon-tiger", "--top", "3"], capture_output=True, text=True, encoding="utf-8")
    assert res1.returncode == 0
    assert "龙虎榜每日席位追踪与机构博弈" in res1.stdout

    # 2. 大宗交易
    res2 = subprocess.run([sys.executable, "wind_cli.py", "chips", "block-trade", "--top", "3"], capture_output=True, text=True, encoding="utf-8")
    assert res2.returncode == 0
    assert "大宗交易每日流水与溢折价博弈" in res2.stdout

    # 3. 股东户数
    res3 = subprocess.run([sys.executable, "wind_cli.py", "chips", "concentration", "--code", "600519", "--top", "3"], capture_output=True, text=True, encoding="utf-8")
    assert res3.returncode == 0
    assert "股东户数时序与筹码集中度" in res3.stdout

    # 4. JSON 模式
    res4 = subprocess.run([sys.executable, "wind_cli.py", "chips", "dragon-tiger", "--top", "2", "--json"], capture_output=True, text=True, encoding="utf-8")
    assert res4.returncode == 0
    data = json.loads(res4.stdout)
    assert isinstance(data, list)


def test_cli_holder_risk():
    # 1. 解禁日历
    res1 = subprocess.run([sys.executable, "wind_cli.py", "holder-risk", "lockup", "--top", "3"], capture_output=True, text=True, encoding="utf-8")
    assert res1.returncode == 0
    assert "限售股解禁日历与流通抛压测算" in res1.stdout

    # 2. 质押监测
    res2 = subprocess.run([sys.executable, "wind_cli.py", "holder-risk", "pledge", "--code", "600519"], capture_output=True, text=True, encoding="utf-8")
    assert res2.returncode == 0
    assert "大股东股权质押比例与平仓线预警监测" in res2.stdout

    # 3. 增减持回购
    res3 = subprocess.run([sys.executable, "wind_cli.py", "holder-risk", "trading", "--top", "3"], capture_output=True, text=True, encoding="utf-8")
    assert res3.returncode == 0
    assert "董监高/大股东增减持与公司股份回购流水" in res3.stdout


def test_cli_smart_money():
    # 1. 北向资金
    res1 = subprocess.run([sys.executable, "wind_cli.py", "smart-money", "northbound", "--top", "3"], capture_output=True, text=True, encoding="utf-8")
    assert res1.returncode == 0
    assert "北向资金 (陆股通/聪明钱) 个股持仓" in res1.stdout

    # 2. 公募重仓
    res2 = subprocess.run([sys.executable, "wind_cli.py", "smart-money", "fund-heavy", "--top", "3"], capture_output=True, text=True, encoding="utf-8")
    assert res2.returncode == 0
    assert "公募基金季报" in res2.stdout


def test_cli_derivatives():
    # 1. 期货基差
    res1 = subprocess.run([sys.executable, "wind_cli.py", "derivatives", "basis"], capture_output=True, text=True, encoding="utf-8")
    assert res1.returncode == 0
    assert "股指期货基差与年化贴水率全景监控" in res1.stdout

    # 2. 期权波动率
    res2 = subprocess.run([sys.executable, "wind_cli.py", "derivatives", "volatility"], capture_output=True, text=True, encoding="utf-8")
    assert res2.returncode == 0
    assert "主流 ETF 期权隐含波动率" in res2.stdout

    # 3. 套利评估 JSON
    res3 = subprocess.run([sys.executable, "wind_cli.py", "derivatives", "arbitrage", "--json"], capture_output=True, text=True, encoding="utf-8")
    assert res3.returncode == 0
    data = json.loads(res3.stdout)
    assert isinstance(data, list)


def test_cli_liquidity():
    # 1. 温度计
    res1 = subprocess.run([sys.executable, "wind_cli.py", "liquidity", "thermometer"], capture_output=True, text=True, encoding="utf-8")
    assert res1.returncode == 0
    assert "宏观高频资金面温度计与央行政策利差研判" in res1.stdout

    # 2. OMO 流水
    res2 = subprocess.run([sys.executable, "wind_cli.py", "liquidity", "omo", "--days", "5"], capture_output=True, text=True, encoding="utf-8")
    assert res2.returncode == 0
    assert "央行公开市场操作 (OMO)" in res2.stdout

    # 3. 银行间利率
    res3 = subprocess.run([sys.executable, "wind_cli.py", "liquidity", "interbank", "--days", "5"], capture_output=True, text=True, encoding="utf-8")
    assert res3.returncode == 0
    assert "银行间质押式回购与 SHIBOR 利率" in res3.stdout


def test_cli_sync_toolkit():
    res = subprocess.run([sys.executable, "wind_cli.py", "sync-toolkit"], capture_output=True, text=True, encoding="utf-8")
    assert res.returncode == 0
    assert "WindToolkit 数据集同步落盘报告" in res.stdout
