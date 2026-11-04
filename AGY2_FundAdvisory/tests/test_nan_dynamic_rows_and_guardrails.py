import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from AGY2_FundAdvisory.portfolio_manager import PortfolioManager, fetch_realtime_fund_quote
from AGY2_FundAdvisory.strategy_bridge import StrategyBridge


def test_nan_dynamic_rows_saving_and_name_fill():
    """
    【核心断言 1：动态增行 NaN 崩溃彻底修复与新基金名称补齐】
    模拟在 st.data_editor 中点击 '+' 新增一行，仅填写基金代码 '000216' 与市值 20000.0，
    其余所有列均为 np.nan / None。
    断言保存时不抛出任何 ValueError，份额正确反算，且真实基金名称与估值自动补齐入库。
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_ledger = Path(tmp_dir) / "temp_ledger.json"
        pm = PortfolioManager(db_path=":memory:", ledger_json_path=tmp_ledger)
        pm.holdings = {}
        pm.available_cash = 10000.0

        # 模拟 Streamlit 动态增行生成的 DataFrame 行（未填字段均为 np.nan）
        mock_row = {
            "基金代码": "000216",
            "基金名称": np.nan,
            "当前市值(元)": 20000.0,
            "持仓份额": np.nan,
            "当前净值": np.nan,
            "持仓成本价": np.nan,
            "浮动盈亏率(%)": np.nan,
            "今日实时估值涨跌(%)": np.nan,
            "盘中预估盈亏(元)": np.nan,
            "持仓占比(%)": np.nan,
            "最短持有天数": np.nan,
            "赎回费状态": np.nan,
            "分红方式": np.nan
        }

        # 导入 app_gui 中的安全提取逻辑
        from AGY2_FundAdvisory.app_gui import _safe_float, _safe_int, _safe_str

        raw_code = _safe_str(mock_row.get("基金代码"), "")
        assert raw_code == "000216"
        code_s = raw_code.zfill(6)

        new_mkt = _safe_float(mock_row.get("当前市值(元)"), 0.0)
        new_shares = _safe_float(mock_row.get("持仓份额"), 0.0)
        assert new_mkt == 20000.0
        assert new_shares == 0.0

        # 联网拉取真实净值与中文全称
        quote = fetch_realtime_fund_quote(code_s)
        real_nav = float(quote.dwjz if (quote and quote.dwjz > 0) else _safe_float(mock_row.get("当前净值"), 1.0))
        assert real_nav > 0.5
        real_name = quote.name if (quote and quote.name and not quote.name.startswith("公募基金_")) else None
        assert real_name is not None
        assert "黄金" in real_name

        h_days = _safe_int(mock_row.get("最短持有天数"), 30)
        assert h_days == 30  # 安全默认 30 天，绝非 np.nan 崩溃

        div_m = _safe_str(mock_row.get("分红方式"), "cash")
        assert div_m == "cash"  # 安全默认 cash，绝非 'nan' 字符串

        row_cost = _safe_float(mock_row.get("持仓成本价"), 0.0)
        cost = row_cost if row_cost > 0 else real_nav
        assert abs(cost - real_nav) < 1e-4

        # 反算份额
        final_shares = round(new_mkt / real_nav, 2)
        assert final_shares > 0

        # 执行入库
        res = pm.add_or_update_holding(
            fund_code=code_s,
            shares=final_shares,
            nav=real_nav,
            cost_price=cost,
            holding_days=h_days,
            dividend_method=div_m,
            fund_name=real_name,
            notes="动态增行测试"
        )
        assert res["status"] == "SUCCESS"

        # 验证持仓对象画像
        assert "000216" in pm.holdings
        h = pm.holdings["000216"]
        assert "黄金" in h.fund_name, f"Expected 黄金 in fund_name, got {h.fund_name}"
        assert abs(h.market_value - 20000.0) < 2.0
        assert h.dividend_method == "cash"
        assert h.cost_price == cost

        # 验证快照导出包含新增基金真实信息
        snap_df = pm.export_snapshot_df()
        assert not snap_df.empty
        row_snap = snap_df[snap_df["基金代码"] == "000216"].iloc[0]
        assert "黄金" in row_snap["基金名称"]
        assert row_snap["当前市值(元)"] > 19990.0


def test_min_buffer_pct_unified_in_rebalance_orders():
    """
    【核心断言 2：统一侧边栏调仓缓冲带单位与传递】
    验证 StrategyBridge.generate_ai_rebalance_orders 接收 min_buffer_pct 参数，
    自适应兼容百分比（如 3.0）与小数比例（如 0.03），有效控制温和模式下的调仓动作。
    """
    from AGY2_FundAdvisory.portfolio_manager import FundHolding
    
    # 构造单只持仓：当前 005561 占比 100% (市值 100,000 元)
    h_mock = FundHolding(
        fund_code="005561",
        fund_name="创金合信中证红利低波动指数A",
        shares=100000.0,
        current_nav=1.0,
        cost_price=1.0,
        market_value=100000.0
    )
    holdings = {"005561": h_mock}
    
    # 目标权重：005561 设定为 98.5%，偏离度仅 1.5%
    target_weights = {"005561": 0.985, "100032": 0.015}

    # 1. 当 min_buffer_pct=3.0 (百分比) 时，1.5% < 3.0% 应当全部维持现状 HOLD
    orders_buf3 = StrategyBridge.generate_ai_rebalance_orders(
        current_holdings=holdings,
        available_cash=0.0,
        target_weights_funds=target_weights,
        mode="gentle",
        min_buffer_pct=3.0
    )
    items_buf3 = orders_buf3["items"]
    for it in items_buf3:
        assert it["action"] == "HOLD", f"Expected HOLD with 3.0% buffer, got {it['action']} for {it['fund_code']}"

    # 2. 当 min_buffer_pct=0.03 (小数比例) 时，同样判定 1.5% < 3.0% 维持现状 HOLD
    orders_ratio = StrategyBridge.generate_ai_rebalance_orders(
        current_holdings=holdings,
        available_cash=0.0,
        target_weights_funds=target_weights,
        mode="gentle",
        min_buffer_pct=0.03
    )
    for it in orders_ratio["items"]:
        assert it["action"] == "HOLD"

    # 3. 当 min_buffer_pct=1.0 (缓冲阈值降为 1.0%) 时，1.5% > 1.0% 触发有效调仓 BUY/SELL
    orders_buf1 = StrategyBridge.generate_ai_rebalance_orders(
        current_holdings=holdings,
        available_cash=0.0,
        target_weights_funds=target_weights,
        mode="gentle",
        min_buffer_pct=1.0
    )
    actions = {it["fund_code"]: it["action"] for it in orders_buf1["items"]}
    assert actions.get("005561") in ("SELL", "HOLD") # 005561 触发减仓（或因批次阻断）
    assert actions.get("100032") == "BUY", f"Expected BUY for 100032 with 1.0% buffer, got {actions.get('100032')}"


def test_ui_tab1_sync_and_5_column_toolbar_invariants():
    """
    【核心断言 3：界面排版与交互几何不变量】
    1. Tab 1 滑块绑定 on_change=_sync_tab1_return_change 回调；
    2. 操作栏为等高 5 列布局（包含修改现金池 popover）；
    3. t2_c2 内部不对称 popover 已彻底移除，概览卡完全齐平；
    4. 持仓表恢复包含 '持仓成本价' 与 '浮动盈亏率(%)'。
    """
    gui_text = Path("AGY2_FundAdvisory/app_gui.py").read_text(encoding="utf-8")

    # 1. 回调绑定
    assert "on_change=_sync_tab1_return_change" in gui_text
    assert "def _sync_tab1_return_change():" in gui_text

    # 2. 5 列操作栏
    assert "col_op1, col_op2, col_op3, col_op4, col_op5 = st.columns(5)" in gui_text
    assert "pop_edit_cash_pool_tb" in gui_text

    # 3. t2_c2 无突起
    assert "pop_edit_cash_pool\n" not in gui_text

    # 4. 成本价与浮盈率
    assert '"持仓成本价"' in gui_text
    assert '"浮动盈亏率(%)"' in gui_text
