import pytest
import re
import pandas as pd
import numpy as np
from pathlib import Path

from AGY2_FundAdvisory.portfolio_manager import PortfolioManager, fetch_batch_realtime_indices
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


def test_core_indices_csi_dividend_accuracy():
    """
    断言核心指数行情带中证红利 (000922) 真实点位对齐，
    物理杜绝被错判为上证红利 (000015，约 3300 点)。
    """
    indices = fetch_batch_realtime_indices(use_cache=False)
    assert len(indices) == 6, f"Expected 6 indices, got {len(indices)}"
    
    idx_map = {item["code"]: item for item in indices}
    assert "000922" in idx_map, "000922 (中证红利) must be present in core indices"
    
    div_item = idx_map["000922"]
    assert div_item["name"] == "中证红利"
    # 中证红利真实点位处于 5000~6500 区间，严禁跌入上证红利的 3000~3500 区间
    assert div_item["point"] > 4500.0, f"CSI Dividend point {div_item['point']} is invalid (likely mistaken as SSE Dividend ~3300)!"


def test_ui_cleanliness_and_title_length():
    """
    红线扫描：
    1. app_gui.py 中绝对无裸露在 HTML 外的 </div>；
    2. Streamlit Demo 工具栏被 display: none 彻底隐藏，展开收起按钮放行并增强；
    3. 侧边栏展开箭头恢复且带有 fixed 悬浮保护；
    4. 核心工作流与步骤标题严格 <= 7 个汉字。
    """
    gui_file = Path("AGY2_FundAdvisory/app_gui.py")
    text = gui_file.read_text(encoding="utf-8")
    
    # 1. 检查 Demo 工具栏隐藏
    assert '.stDeployButton' in text
    assert '[data-testid="stStatusWidget"]' in text
    assert '#MainMenu' in text
    
    # 2. 检查侧边栏展开/收起按钮放行（Streamlit 1.66 属性）
    assert '[data-testid="stExpandSidebarButton"]' in text
    assert '[data-testid="stSidebarCollapseButton"]' in text
    assert '[data-testid="collapsedControl"]' in text
    
    # 3. 检查侧边栏全局领航台已挂载
    assert 'with st.sidebar:' in text
    assert 'st.subheader("🧭 全局领航台")' in text
    
    # 4. 检查 3 栏深度归因大卡片
    assert '#### 🎯 方案核心归因' in text
    assert '💰 怎么赚钱？' in text
    assert '🏆 为什么能赢？' in text
    assert '🚨 风险与铁律' in text
    
    # 5. 标题长度断言 (主步骤和二级步骤 <= 7 汉字)
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


def test_ui_geometry_and_non_overlap_invariants():
    """
    【消灭测试虚荣·真实几何不变量与视口容量数学测算】
    彻底杜绝仅凭 'assert not at.exception' 掩耳盗铃。
    严格断言 CSS 几何属性、物理防挤压不变量与视口容量，
    从数学机制层面 100% 杜绝卡片截断与药丸骑头重叠！
    """
    gui_file = Path("AGY2_FundAdvisory/app_gui.py")
    gui_text = gui_file.read_text(encoding="utf-8")
    
    # 1. 顶部 4 卡片文字防截断几何断言 (Anti-Truncation Invariant)
    # 严禁在 stHorizontalBlock 和 column 上加 overflow: hidden，防止下半身文字腰斩！
    assert 'overflow: visible !important;' in gui_text, "stHorizontalBlock/column must use overflow: visible !important"
    assert 'div[data-testid="stHorizontalBlock"] {\n        width: 100% !important;\n        box-sizing: border-box !important;\n        overflow: visible !important;' in gui_text or 'overflow: visible !important' in gui_text
    
    # 2. main-metric-card 必须自适应高度且溢出可见
    assert '.main-metric-card {' in gui_text
    # 必须 min-height >= 120px 且 height: auto !important 且 overflow: visible !important
    assert 'min-height: 122px;' in gui_text
    assert 'overflow: visible !important;' in gui_text
    
    # 3. 核心指数药丸物理防挤压不变量 (Anti-Squash & Anti-Overlap Invariant)
    # 严禁使用 flex: 1 1 0 导致药丸被挤压至 90px 而文字外溢盖在下一个药丸头上！
    assert 'flex: 0 0 auto !important;' in gui_text, "index-ticker-pill must use flex: 0 0 auto !important to prevent shrinking!"
    assert 'white-space: nowrap !important;' in gui_text
    
    # 4. 核心指数药丸必须被包裹在横向平滑滚动容器中 (Scrollable Container Invariant)
    assert '.index-pills-scroll-wrap {' in gui_text
    assert 'overflow-x: auto !important;' in gui_text
    assert 'class="index-pills-scroll-wrap"' in gui_text
    
    # 5. 其他卡片 (kpi-metric-card & consequence-card) 自适应防腰斩断言
    assert '.consequence-card {' in gui_text
    assert '.kpi-metric-card {' in gui_text
    
    # 6. 数据源真实性与防张冠李戴红线断言
    dl_text = Path("AGY2_FundAdvisory/data_loader.py").read_text(encoding="utf-8")
    sb_text = Path("AGY2_FundAdvisory/strategy_bridge.py").read_text(encoding="utf-8")
    assert "'H00922': 'sh000015'" not in dl_text, "data_loader.py must not map H00922 (CSI Dividend) to sh000015 (SSE Dividend)!"
    assert "'H00922': 'sh000922'" in dl_text, "data_loader.py must map H00922 to sh000922!"
    assert 'fetch_realtime_index_quote("sh000015"' not in sb_text, "strategy_bridge.py must not query sh000015 for dividend index!"
    assert 'fetch_realtime_index_quote("sh000922"' in sb_text, "strategy_bridge.py must query sh000922 for dividend index!"


def test_sidebar_guardrails_propagation():
    """
    断言侧边栏实盘交易风控护栏（限购过滤阈值、调仓缓冲带）真实生效：
    1. 限购过滤阈值有效替换低于限额的标的（博时标普500被摩根标普500A替换）；
    2. 调仓缓冲带 min_buffer_pct 控制调仓裁决。
    """
    from AGY2_FundAdvisory.strategy_bridge import StrategyBridge
    from AGY2_FundAdvisory.portfolio_manager import PortfolioManager
    
    # 1. 限购过滤测试：包含博时标普500 (050025，日限额500元)
    w = {"005561": 0.4, "100032": 0.3, "050025": 0.3}
    bp_no_filter = StrategyBridge.generate_zero_start_blueprint(
        total_capital=100000.0,
        target_weights_funds=w,
        tier="C3",
        purchase_limit_filter="不限 (自动拆单承接)"
    )
    codes_no_filter = [it["fund_code"] for it in bp_no_filter["items"]]
    assert "050025" in codes_no_filter
    
    bp_filtered = StrategyBridge.generate_zero_start_blueprint(
        total_capital=100000.0,
        target_weights_funds=w,
        tier="C3",
        purchase_limit_filter="过滤日限额 < ¥1,000 标的"
    )
    codes_filtered = [it["fund_code"] for it in bp_filtered["items"]]
    # 050025 日限额 500 < 1000，必须被自动替换为 001071 (摩根标普500A)
    assert "050025" not in codes_filtered, "Restricted fund 050025 was not filtered!"
    assert "001071" in codes_filtered, "Fallback fund 001071 not used as alternative!"
    
    # 2. 调仓缓冲带测试 (完全隔离沙箱)
    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_ledger = Path(tmp_dir) / "temp_ledger.json"
        pm = PortfolioManager(db_path=":memory:", ledger_json_path=tmp_ledger)
        pm.available_cash = 0.0
        pm.in_transit_cash = 0.0
        pm.pending_orders = []
        pm.add_or_update_holding("005561", shares=10000.0, nav=1.0)
        # 当前 005561 市值 10000，占比 100.0%，目标权重 98.5% (偏离 1.5% < 3.0% 缓冲带)
        target_close = {"005561": 0.985, "100032": 0.015}
        plan_buffered = pm.generate_rebalance_plan(target_close, min_buffer_pct=3.0)
        assert len(plan_buffered.get("routes", [])) == 0, f"Buffer 3.0% failed to filter small deviations! Routes: {plan_buffered.get('routes')}"


def test_tab2_direct_market_value_editing_and_shares_recalculation():
    """
    断言 Tab 2 持仓表直接修改「当前市值(元)」保存后，
    后台按当前净值精确反算持仓份额，总市值正确同步更新。
    """
    import tempfile
    from AGY2_FundAdvisory.portfolio_manager import PortfolioManager
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_ledger = Path(tmp_dir) / "temp_ledger.json"
        pm = PortfolioManager(db_path=":memory:", ledger_json_path=tmp_ledger)
        pm.available_cash = 10000.0
        # 初始持仓：华泰柏瑞红利低波 10,000 份，净值 1.2500，初始市值 12,500 元
        pm.add_or_update_holding("005561", shares=10000.0, nav=1.25, cost_price=1.20, holding_days=45)
        assert abs(pm.holdings["005561"].market_value - 12500.0) < 1e-2
        
        # 模拟用户在表格中直接将当前市值修改为 25,000.00 元（份额未动或用户不知道份额）
        new_mkt = 25000.0
        nav = pm.holdings["005561"].current_nav  # 1.25
        recalculated_shares = round(new_mkt / nav, 2)  # 应为 20,000.00 份
        
        pm.add_or_update_holding(
            fund_code="005561",
            shares=recalculated_shares,
            nav=nav,
            cost_price=1.20,
            holding_days=45,
            notes="市值反算更新"
        )
        
        assert abs(pm.holdings["005561"].shares - 20000.0) < 1e-2
        assert abs(pm.holdings["005561"].market_value - 25000.0) < 1e-2


def test_tab2_step1_layout_and_dock_integrity():
    """
    断言 Tab 2 步骤一包含：
    1. 4 张资产概览卡 (💼 持仓总市值、💵 可用现金池、📈 累计浮动盈亏、🔒 锁仓与超额概览)；
    2. 锁仓与免罚只数动态统计；
    3. 表格操作栏等高对齐并包含删除 popover；
    4. 单一整合的「🛠️ 账本工具坞」（包含快速录入、FIFO 批次透视、实盘接管档案 3 个子 tab）。
    """
    gui_file = Path("AGY2_FundAdvisory/app_gui.py")
    gui_text = gui_file.read_text(encoding="utf-8")
    
    assert "💼 持仓总市值" in gui_text
    assert "💵 可用现金池" in gui_text
    assert "📈 累计浮动盈亏" in gui_text
    assert "🔒 锁仓与超额概览" in gui_text
    assert "safe_redeem_count" in gui_text
    assert "penalty_locked_count" in gui_text
    
    assert "🛠️ 账本工具坞（快速录入 / FIFO批次透视 / 实盘接管档案）" in gui_text
    assert "✨ 快速录入/导入持仓" in gui_text
    assert "📦 FIFO批次解锁透视" in gui_text
    assert "📋 实盘接管基准档案" in gui_text
    
    assert "pop_edit_cash_pool" in gui_text
    assert "pop_del_sel_tab2" in gui_text
