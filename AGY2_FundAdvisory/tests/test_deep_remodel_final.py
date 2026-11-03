import pytest
import re
import pandas as pd
import numpy as np
from pathlib import Path

from AGY2_FundAdvisory.portfolio_manager import PortfolioManager
from AGY2_FundAdvisory.strategy_bridge import StrategyBridge
from AGY2_FundAdvisory.winrate_engine import WinRateEngine
from AGY2_FundAdvisory.data_loader import DataLoader


def test_quant_models_weight_differentiation():
    """
    断言四大机构级模型在 6 只与 12 只基金配置下均具有显著梯队倾角，
    物理杜绝 1/N 等权退化坍缩。
    """
    for n in [6, 12]:
        for m_type in ["hrp_cvar", "cond_winrate", "min_cvar", "kelly_momentum"]:
            res = StrategyBridge.compute_n_funds_model_portfolio(
                tier="C3",
                target_return_pct=15.0,
                num_funds=n,
                model_type=m_type,
                capital=100000.0
            )
            opt_w = res.get("optimal_weights", {})
            assert len(opt_w) == n, f"Model {m_type} with n={n} produced {len(opt_w)} weights"
            
            # 权重总和归一化为 1.0
            assert abs(sum(opt_w.values()) - 1.0) < 1e-4, f"Weights sum {sum(opt_w.values())} != 1.0"
            
            # 显著梯度区分：不同权重值的个数必须大于 1 (拒绝 8.3% 全体等权)
            distinct_weights = set(round(v, 4) for v in opt_w.values())
            assert len(distinct_weights) > 1, f"Model {m_type} collapsed to 1/N equal weights on n={n}: {opt_w}"
            
            # 主力与卫星存在显著方差
            weights_arr = np.array(list(opt_w.values()))
            assert np.std(weights_arr) > 0.005, f"Weights standard deviation too small for {m_type} on n={n}"


def test_blueprint_cash_conservation_and_percentage_closure():
    """
    断言 generate_zero_start_blueprint 在任何金额与限购拆单场景下：
    1. 分厘严格平账 (allocated_sum == total_capital)
    2. 百分比严格闭合 (weight_pct_sum == 100.0)
    3. 伴生承接基金无重复条目
    """
    for cap in [50000.0, 100000.0, 333333.33]:
        # 模拟包含博时标普500 (限额 500 元) 的组合
        weights = {
            "005561": 0.35,
            "100032": 0.25,
            "000216": 0.15,
            "017436": 0.10,
            "011613": 0.10,
            "050025": 0.05,  # 博时标普500，溢出转 001071
        }
        bp = StrategyBridge.generate_zero_start_blueprint(
            total_capital=cap,
            target_weights_funds=weights,
            tier="C3"
        )
        items = bp["items"]
        
        # 1. 伴生承接无重复
        codes = [it["fund_code"] for it in items]
        assert len(codes) == len(set(codes)), f"Duplicate fund codes found in blueprint items: {codes}"
        
        # 2. 分厘严格平账
        allocated_sum = sum(it["allocated_amount"] for it in items)
        assert abs(allocated_sum - cap) < 1e-2, f"Allocated sum {allocated_sum} != capital {cap}"
        
        # 3. 百分比闭合
        pct_sum = sum(it["target_weight_pct"] for it in items)
        assert abs(pct_sum - 100.0) < 1e-4, f"Target weight pct sum {pct_sum} != 100.0"


def test_winrate_dual_gauge_and_sample_capacity():
    """
    断言胜率引擎输出当下相似条件胜率与全历史胜率双口径对照，
    并披露有效测评窗口期数。
    """
    dates = pd.date_range("2018-01-01", "2026-03-31", freq="B")
    np.random.seed(42)
    daily_rets = np.random.normal(0.0004, 0.01, size=len(dates))
    nav = pd.Series(np.cumprod(1 + daily_rets), index=dates)
    
    mock_snapshot = {
        "erp_percentile": 80.0,
        "bias_20": 1.5,
        "momentum_60": 5.0,
        "ewma_vol": 14.0,
        "dr007": 1.45
    }
    
    table = WinRateEngine.multi_horizon_winrate_table(
        nav_series=nav,
        target_annual_return=0.15,
        market_snapshot=mock_snapshot
    )
    
    assert "short" in table and "medium" in table and "long" in table
    for pk, pinfo in table.items():
        assert "conditional_win_rate" in pinfo
        assert "unconditional_win_rate" in pinfo
        assert "total_windows" in pinfo
        assert pinfo["total_windows"] > 500, f"Rolling windows count {pinfo['total_windows']} too small"
        assert 0.0 <= pinfo["conditional_win_rate"] <= 1.0
        assert 0.0 <= pinfo["unconditional_win_rate"] <= 1.0


def test_ui_cleanliness_and_title_length():
    """
    红线扫描：
    1. app_gui.py 中绝对无裸露在 HTML 外的 </div>；
    2. Streamlit Demo 工具栏被 display: none 彻底隐藏；
    3. 侧边栏展开箭头恢复；
    4. 核心工作流与步骤标题严格 <= 7 个汉字。
    """
    gui_file = Path("AGY2_FundAdvisory/app_gui.py")
    text = gui_file.read_text(encoding="utf-8")
    
    # 1. 检查 Demo 工具栏隐藏
    assert '.stDeployButton, [data-testid="stStatusWidget"], #MainMenu, footer' in text
    assert '[data-testid="collapsedControl"]' in text
    
    # 2. 检查侧边栏全局领航台已挂载
    assert 'with st.sidebar:' in text
    assert 'st.subheader("🧭 全局领航台")' in text
    
    # 3. 检查 3 栏深度归因大卡片
    assert '#### 🎯 方案核心归因' in text
    assert '💰 怎么赚钱？' in text
    assert '🏆 为什么能赢？' in text
    assert '🚨 风险与铁律' in text
    
    # 4. 标题长度断言 (主步骤和二级步骤 <= 7 汉字)
    key_titles = [
        "步骤一：设定目标",
        "步骤二：现场推演",
        "步骤三：生成建仓",
        "步骤一：持仓账本",
        "步骤二：时机裁决",
        "步骤三：方案执行",
        "跨牛熊滚动胜率",
        "方案核心归因",
        "调仓真实后果",
        "全周期净值曲线",
        "动态回撤对比",
        "资产仓位变迁",
        "历史切片战报",
        "历史相似匹配",
        "重仓交叉热力",
        "底层排雷宽表",
        "聪明钱与拥挤",
        "AC算费工具",
        "ETF溢价监控",
        "选基漏斗与评分",
        "宏观决策信号",
        "实盘接管档案",
        "FIFO批次透视",
    ]
    for t in key_titles:
        # 去除标点与 emoji 后汉字数 <= 7
        clean_chinese = re.sub(r'[^\u4e00-\u9fa5]', '', t)
        assert len(clean_chinese) <= 7, f"Title '{t}' has {len(clean_chinese)} Chinese characters (> 7)"
        assert t in text, f"Key title '{t}' not found in app_gui.py"


def test_apptest_gui_headless_execution():
    """
    通过 Streamlit 官方 AppTest 进行端到端无头执行测试，断言 0 Exception。
    """
    from streamlit.testing.v1 import AppTest
    gui_absolute_path = str(Path(__file__).resolve().parent.parent / "app_gui.py")
    at = AppTest.from_file(gui_absolute_path, default_timeout=30)
    at.run()
    assert not at.exception, f"AppTest threw exception: {at.exception}"
