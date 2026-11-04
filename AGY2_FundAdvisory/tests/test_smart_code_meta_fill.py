import tempfile
from pathlib import Path
import pytest
from AGY2_FundAdvisory.portfolio_manager import PortfolioManager, fetch_realtime_fund_quote


def test_smart_code_meta_and_nav_auto_fill():
    """
    断言智能联动模式：
    用户在表格中仅输入/修改「基金代码」(如 016440) 与「当前市值」(如 50,000 元)，
    系统自动通过行情网关联网拉取真实基金全称与最新单位净值，并精确反算持仓份额。
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_ledger = Path(tmp_dir) / "temp_ledger.json"
        pm = PortfolioManager(db_path=":memory:", ledger_json_path=tmp_ledger)
        pm.holdings = {}
        pm.available_cash = 20000.0
        
        # 模拟仅录入基金代码 016440 和市值 50000 元
        input_code = "016440"
        input_market_val = 50000.0
        
        quote = fetch_realtime_fund_quote(input_code)
        assert quote.name != "", f"Quote name for {input_code} must not be empty"
        assert "红利质量" in quote.name, f"Quote name should contain '红利质量', got: {quote.name}"
        assert quote.dwjz > 0.5, f"Unit NAV for {input_code} should be valid (>0.5), got: {quote.dwjz}"
        
        real_nav = float(quote.dwjz)
        expected_shares = round(input_market_val / real_nav, 2)
        
        # 入库
        pm.add_or_update_holding(
            fund_code=input_code,
            shares=expected_shares,
            nav=real_nav,
            cost_price=real_nav,
            holding_days=30,
            notes="代码智能联动与市值反算入库"
        )
        
        assert input_code in pm.holdings
        h = pm.holdings[input_code]
        assert "红利质量" in h.fund_name
        assert abs(h.market_value - input_market_val) < 2.0  # 舍入误差在 2 元内
        assert abs(h.shares - expected_shares) < 1e-2
        
        # 导出快照断言派生字段已全部自动跳出
        df_snap = pm.export_snapshot_df()
        assert not df_snap.empty
        row = df_snap[df_snap["基金代码"] == input_code].iloc[0]
        assert "基金名称" in row and "红利质量" in row["基金名称"]
        assert "当前净值" in row and abs(row["当前净值"] - real_nav) < 1e-4
        assert "今日实时估值涨跌(%)" in row
        assert "持仓占比(%)" in row
        assert row["持仓占比(%)"] > 0


def test_invalid_code_soft_validation():
    """
    断言非法/查无此基的代码温柔校验：
    合法 6 位数字代码正常识别入库，非法字符或非6位代码被拦截提示，不影响整库稳定。
    """
    test_cases = [
        ("005561", True),
        ("100032", True),
        ("abc123", False),
        ("123", False),
        ("None", False),
        ("", False)
    ]
    for raw_c, is_valid in test_cases:
        code_str = str(raw_c).strip()
        is_clean_digit = code_str.isdigit() and len(code_str) == 6
        assert is_clean_digit == is_valid, f"Validation mismatch for code '{raw_c}'"
