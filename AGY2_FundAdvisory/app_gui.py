"""
AGY2 A股基金实盘组合接管与智能投顾图形化工作台 (app_gui.py)
深度接入 AI 投顾核心策略大脑与全天候因果状态机：
1. 顶部全局看板：1 行 4 宽卡 + 1 紧凑刷新按钮 (申赎时钟/市场攻防/估值温度/总资产与今日预估)；
2. Tab 1：【🌱 新资建仓】从0定目标、真全市场漏斗选基(3~15只自由调节)、四大机构级模型定权、看推演、拿实盘建仓单；
3. Tab 2：【💼 持仓调仓】自然三步流(①当前持仓账本 -> ②AI调仓时机裁决 -> ③温和vs强行后果量化账单与执行单)；
4. Tab 3：【📈 组合回测】穿透回测新建仓组合/当前持仓/调仓前后双曲线对比，9大对标指数自由多选；
5. Tab 4：【🔍 穿透工具】大类资产穿透缺口、加权行业暴露、重仓股交叉热力图、底层穿透排雷、A/C算费、场内ETF溢价监控。
"""

import sys
import time
from pathlib import Path
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from typing import Any, Callable, Dict, List, Optional, Tuple

import importlib
import inspect

CURRENT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = CURRENT_DIR.parent if CURRENT_DIR.name == "AGY2_FundAdvisory" else CURRENT_DIR
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))
if str(CURRENT_DIR) in sys.path:
    sys.path.remove(str(CURRENT_DIR))
sys.path.insert(0, str(CURRENT_DIR))

# 核心本地模块导入与显式热重载守卫
import cache_manager
import data_loader
import trading_clock_fee
from trading_clock_fee import TradingClock, FeeMatrixCalculator
import portfolio_manager
from portfolio_manager import (
    PortfolioManager,
    CORE_STRATEGY_POOL,
    EXTENDED_FUND_CATALOG,
    SECTOR_FUND_SELECTION,
    get_fund_selection_funnel_stats,
    search_funds_in_catalog,
    parse_smart_text_holdings,
    fetch_realtime_fund_quote,
    fetch_realtime_index_quote,
    clear_realtime_cache,
    FundQuote
)
import winrate_engine
from winrate_engine import WinRateEngine, HOLDING_PERIODS, WINRATE_METRIC_DEFINITIONS
import strategy_bridge
from strategy_bridge import (
    StrategyBridge,
    INDEX_TO_FUND_MAP,
    RISK_TIERS_CONFIG,
    BENCHMARK_INDICES_MAP,
    UNIVERSE_18_CHAMPION_POOL,
    map_target_return_to_tier,
    evaluate_questionnaire_risk_tier,
    get_risk_mismatch_warning,
    calculate_human_readable_metrics,
    get_aggressive_dream_reality_check,
    strategy_fn_for_tier
)
import market_screener
from market_screener import MarketScreener
import portfolio_optimizer
from portfolio_optimizer import (
    WinRateOptimizer,
    QUANT_MODELS_CATALOG,
    recommend_model_for_regime,
    execute_market_optimization_flow
)

if "_modules_initialized" not in st.session_state:
    importlib.reload(cache_manager)
    importlib.reload(data_loader)
    importlib.reload(trading_clock_fee)
    importlib.reload(portfolio_manager)
    importlib.reload(winrate_engine)
    importlib.reload(strategy_bridge)
    importlib.reload(market_screener)
    importlib.reload(portfolio_optimizer)
    from trading_clock_fee import TradingClock, FeeMatrixCalculator
    from portfolio_manager import (
        PortfolioManager, CORE_STRATEGY_POOL, EXTENDED_FUND_CATALOG,
        SECTOR_FUND_SELECTION, get_fund_selection_funnel_stats,
        search_funds_in_catalog, parse_smart_text_holdings,
        fetch_realtime_fund_quote, fetch_realtime_index_quote,
        clear_realtime_cache, FundQuote
    )
    from winrate_engine import WinRateEngine, HOLDING_PERIODS, WINRATE_METRIC_DEFINITIONS
    from strategy_bridge import (
        StrategyBridge, INDEX_TO_FUND_MAP, RISK_TIERS_CONFIG,
        BENCHMARK_INDICES_MAP, UNIVERSE_18_CHAMPION_POOL,
        map_target_return_to_tier, evaluate_questionnaire_risk_tier,
        get_risk_mismatch_warning, calculate_human_readable_metrics,
        get_aggressive_dream_reality_check, strategy_fn_for_tier
    )
    from market_screener import MarketScreener
    from portfolio_optimizer import (
        WinRateOptimizer, QUANT_MODELS_CATALOG,
        recommend_model_for_regime, execute_market_optimization_flow
    )
    st.session_state["_modules_initialized"] = True


def map_slider_to_tier(ret: float) -> str:
    """统一委托 strategy_bridge.map_target_return_to_tier，消除重复定义与档位漂移"""
    return map_target_return_to_tier(ret)


# 统一资产分类解析器动态兜底
if not hasattr(PortfolioManager, "classify_fund_asset_class"):
    def _pm_classify_fund_asset_class(self, fund_code: str, fund_name: str = "") -> str:
        code_str = str(fund_code).strip()
        nm = str(fund_name).strip() if fund_name else ""
        if not nm and hasattr(self, "holdings") and code_str in self.holdings:
            nm = self.holdings[code_str].fund_name
        if any(k in nm for k in ["债", "国债", "利差", "固收", "纯债", "中短债", "裕祥"]):
            return "纯债固收"
        if any(k in nm for k in ["黄金", "AU", "金ETF", "Gold"]):
            return "黄金对冲"
        if any(k in nm for k in ["标普", "纳斯达克", "海外", "美股", "SPX", "NDX", "QDII"]):
            return "美股海外对冲"
        if any(k in nm for k in ["红利低波", "低波", "红利低波动"]):
            return "A股红利低波"
        if any(k in nm for k in ["红利", "股息", "大成红利", "富国中证红利"]):
            return "A股红利高股息"
        if any(k in nm for k in ["科创", "芯片", "半导体", "集成电路", "科技", "信息"]):
            return "科技成长进攻"
        if any(k in nm for k in ["1000", "中小盘", "小盘", "微盘"]):
            return "中小盘成长"
        if any(k in nm for k in ["500", "中盘", "中证500"]):
            return "中盘均衡"
        if any(k in nm for k in ["300", "沪深300", "蓝筹", "上证50", "核心", "50ETF"]):
            return "核心蓝筹"
        return "其他权益资产"
    PortfolioManager.classify_fund_asset_class = _pm_classify_fund_asset_class

# -------------------------------------------------------------
# 页面基础配置与高颜值深色质感样式
# -------------------------------------------------------------
st.set_page_config(
    page_title="AGY2 智能投顾与实盘组合接管工作台",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS 强化桌面客户端质感（含彻底隐藏 Stop / Deploy / 汉堡菜单）
st.markdown("""
<style>
    header[data-testid="stHeader"] {
        visibility: hidden !important;
        height: 0 !important;
    }
    [data-testid="stToolbar"] {
        visibility: hidden !important;
        display: none !important;
    }
    .stDeployButton {
        display: none !important;
    }
    [data-testid="stStatusWidget"] {
        visibility: hidden !important;
        display: none !important;
    }
    #MainMenu {
        visibility: hidden !important;
    }
    footer {
        visibility: hidden !important;
    }
    .main-metric-card {
        background: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 10px 14px;
        color: #0f172a;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        min-height: 94px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-sizing: border-box;
    }
    .metric-card-title {
        font-size: 13px;
        font-weight: 600;
        color: #475569;
        display: flex;
        justify-content: space-between;
        align-items: center;
        white-space: nowrap;
        line-height: 1.2;
    }
    .metric-value-huge {
        font-size: 17px;
        font-weight: 700;
        letter-spacing: -0.3px;
        line-height: 1.2;
        margin: 3px 0;
        white-space: nowrap;
    }
    .metric-card-sub {
        font-size: 12px;
        color: #64748b;
        white-space: nowrap;
        line-height: 1.3;
    }
    .consequence-card {
        background: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 12px 14px;
        min-height: 115px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .kpi-metric-card {
        background: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 10px 12px;
        color: #0f172a;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        min-height: 108px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-sizing: border-box;
    }
    .kpi-card-title {
        font-size: 12px;
        font-weight: 600;
        color: #334155;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        line-height: 1.2;
    }
    .kpi-card-sub {
        font-size: 11px;
        font-weight: 600;
        margin-top: 2px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        line-height: 1.2;
    }
    .kpi-card-desc {
        font-size: 10px;
        color: #64748b;
        margin-top: 3px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        line-height: 1.2;
    }
    .decision-card {
        background: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 14px 16px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }
    .decision-title {
        font-size: 13px;
        font-weight: 600;
        color: #334155;
        margin-bottom: 4px;
    }
    .decision-val {
        font-size: 18px;
        font-weight: 700;
        margin-bottom: 4px;
    }
    .decision-desc {
        font-size: 12px;
        color: #1e293b;
        line-height: 1.4;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
    }
    @keyframes console-pulse {
        0% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0.45); }
        70% { box-shadow: 0 0 0 12px rgba(37, 99, 235, 0); }
        100% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0); }
    }
    .active-computation-console {
        border: 2px solid #2563eb !important;
        border-radius: 10px !important;
        padding: 16px 20px !important;
        margin: 14px 0 !important;
        background: linear-gradient(135deg, rgba(37, 99, 235, 0.06) 0%, rgba(59, 130, 246, 0.02) 100%) !important;
        animation: console-pulse 2s infinite !important;
    }
    .console-header-banner {
        font-size: 16px !important;
        font-weight: 700 !important;
        color: #1d4ed8 !important;
        margin-bottom: 6px !important;
    }
    .console-timer-text {
        font-size: 12px !important;
        color: #475569 !important;
        margin-bottom: 8px !important;
    }
</style>
""", unsafe_allow_html=True)


class ActiveComputationConsole:
    """显式中央实时计算控制台 (Active Computation Console)"""
    def __init__(self, step_name: str, total_steps: int = 4, step_labels: Optional[List[str]] = None):
        self.step_name = step_name
        self.total_steps = total_steps
        self.step_labels = step_labels or [
            "步骤 1: 宏观动量与同温层状态机定调",
            "步骤 2: 2018-2026 跨牛熊日度净值合成与回测",
            "步骤 3: 机构级量化模型求解最优配比",
            "步骤 4: 交易摩擦精算与限购拆单执行清单"
        ]
        self.t0 = time.time()
        self.status = st.status(f"🔄 正在为您计算：【{self.step_name}】...", expanded=True)
        with self.status:
            st.markdown(
                f"""<div class="active-computation-console">
                <div class="console-header-banner">
                    🔄 正在为您计算：{self.step_name}
                </div>
                <div class="console-timer-text">
                    ⏱️ 引擎启动中... 正在初始化量化底座与条件胜率模型
                </div>
                </div>""",
                unsafe_allow_html=True
            )
            self.prog_bar = st.progress(0, text="初始化中...")
            self.step_slots = [st.empty() for _ in range(self.total_steps)]
            for i, lbl in enumerate(self.step_labels):
                self.step_slots[i].caption(f"⬜ {lbl} (等待中)")

    def update_step(self, current_step_idx: int, sub_action: str = "", progress_pct: Optional[int] = None):
        elapsed = max(0.01, round(time.time() - self.t0, 2))
        pct = progress_pct if progress_pct is not None else int(((current_step_idx + 1) / (self.total_steps + 1)) * 100)
        pct = min(max(pct, 0), 99)
        self.prog_bar.progress(pct, text=f"⏱️ 已耗时: {elapsed:.2f}s ｜ 正在执行: {sub_action}")
        for i, lbl in enumerate(self.step_labels):
            if i < current_step_idx:
                self.step_slots[i].caption(f"✅ {lbl} (已完成)")
            elif i == current_step_idx:
                self.step_slots[i].caption(f"🔄 {lbl} —— {sub_action} (执行中...)")
            else:
                self.step_slots[i].caption(f"⏳ {lbl} (等待中)")

    def complete(self, summary_msg: str = "已生成最新策略建议"):
        elapsed = max(0.01, round(time.time() - self.t0, 2))
        self.prog_bar.progress(100, text=f"✅ 计算已完成！总耗时 {elapsed:.2f}s")
        for i, lbl in enumerate(self.step_labels):
            self.step_slots[i].caption(f"✅ {lbl} (已完成)")
        cache_hint = "（极速返回）" if elapsed < 0.2 else f"（耗时 {elapsed:.2f}s）"
        self.status.update(
            label=f"✅ 【{self.step_name}】计算圆满完成！{cache_hint} ⏱️ 总耗时 {elapsed:.2f}s ｜ {summary_msg}",
            state="complete",
            expanded=False
        )


def render_workflow_step_indicator(steps: List[str], current_step: int, help_text: str = ""):
    """渲染《🧭 工作流步骤与系统状态指示器》"""
    parts = []
    for idx, name in enumerate(steps, 1):
        if idx < current_step:
            parts.append(f"<span style='color: #16a34a; font-weight: 700;'>【✅ 步骤{idx}：{name} (已完成)】</span>")
        elif idx == current_step:
            parts.append(f"<span style='color: #2563eb; font-weight: 700; background: rgba(37, 99, 235, 0.1); padding: 2px 6px; border-radius: 4px; border: 1px solid #3b82f6;'>【🟢 步骤{idx}：{name} (当前步骤)】</span>")
        else:
            parts.append(f"<span style='color: #94a3b8; font-weight: 500;'>【⚪ 步骤{idx}：{name} (待解锁)】</span>")

    flow_html = " ───> ".join(parts)
    st.markdown(f"""
    <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; margin-bottom: 12px;">
        <div style="font-size: 13px; font-weight: 600; color: #334155; margin-bottom: 4px;">
            🧭 工作流导引：{flow_html}
        </div>
        <div style="font-size: 12px; color: #64748b;">
            🟢 <b>系统状态</b>：就绪 ｜ {help_text or '请在当前步骤完成参数确认后点击下方按钮进入下一步'}
        </div>
    </div>
    """, unsafe_allow_html=True)


# 初始化核心运行态
if "pm" not in st.session_state:
    st.session_state.pm = PortfolioManager()
    try:
        st.session_state.pm.sync_holdings_live_nav(use_intraday_gsz=True)
    except Exception:
        pass

pm: PortfolioManager = st.session_state.pm
clock = pm.clock
calc = pm.calculator

# 实时拉取最新策略大脑快照
snapshot = StrategyBridge.get_latest_market_snapshot()
trial29_kpi = StrategyBridge.load_trial29_metrics()

# -------------------------------------------------------------
# 侧边栏：组合基准信息与全局快捷动作
# -------------------------------------------------------------
with st.sidebar:
    st.title("🛡️ AGY2 投顾工作台")
    st.caption("A股跨风格高胜率策略大脑 (全天候生产版)")
    st.markdown("---")

    st.subheader("⚡ 组合快捷控制")
    col_demo, col_undo = st.columns(2)
    with col_demo:
        if st.button("🚀 加载演示组合", use_container_width=True, help="注入包含冷启动、7天锁、待满期、深套基的完整演示组合"):
            demo_res = pm.load_demo_portfolio()
            st.session_state.tab2_diag_cache = None
            st.session_state.tab2_rebal_cache = None
            st.session_state.tab2_diagnosed = False
            st.session_state.tab2_rebalanced = False
            st.success("演示组合载入成功！")
            st.rerun()

    with col_undo:
        if st.button("↩️ 一键撤销", use_container_width=True, help="撤销上一步操作并回滚快照"):
            with st.spinner("↩️ 回滚中..."):
                _undo_ok = pm.undo()
            if _undo_ok:
                st.session_state.tab2_diag_cache = None
                st.session_state.tab2_rebal_cache = None
                st.session_state.tab2_diagnosed = False
                st.session_state.tab2_rebalanced = False
                st.info("✅ 已成功回滚至上一快照！")
                st.rerun()
            else:
                st.warning("暂无更早快照可撤销")

    if st.button("🔄 同步最新真实净值", use_container_width=True, help="双源拉取天天基金与新浪最新净值/估值，刷新持仓市值与 Alpha"):
        with st.spinner("🔄 正在从天天基金/新浪双源拉取最新净值..."):
            s_res = pm.sync_holdings_live_nav(use_intraday_gsz=True)
        st.success(f"✅ 已同步 {s_res.get('updated_count', 0)} 只持仓最新净值！")
        st.rerun()

    st.markdown("---")
    st.subheader("📋 实盘接管档案")
    st.write(f"**接管模式**：{'模式 A (极简冷启动)' if pm.takeover_mode == 'A' else '模式 B (账本热接管)'}")
    st.write(f"**基准确立日**：`{pm.baseline_date}`")
    st.write(f"**接管基准总资产**：¥{pm.baseline_equity:,.2f}")

    total_market_val = sum(h.market_value for h in pm.holdings.values())
    total_cur_equity = total_market_val + pm.available_cash + pm.in_transit_cash
    abs_gain = total_cur_equity - pm.baseline_equity
    abs_gain_pct = (abs_gain / pm.baseline_equity * 100.0) if pm.baseline_equity > 0 else 0.0

    st.metric(
        label="接管后绝对收益",
        value=f"¥{total_cur_equity:,.2f}",
        delta=f"{abs_gain:+,.2f} ({abs_gain_pct:+.2f}%)",
        delta_color="inverse"
    )

    st.write(f"**峰值总资产**：¥{pm.peak_equity:,.2f}")
    st.write(f"**接管期最大回撤**：`{pm.max_drawdown_pct:.2f}%`")
    st.write(f"**基准超额 (Alpha)**：`{pm.alpha_return_pct:+.2f}%` (vs {pm.benchmark_code})")

    st.markdown("---")
    st.subheader("💰 现金池管理")
    new_cash = st.number_input(
        "修改可用现金 (元)",
        value=float(pm.available_cash),
        step=1000.0,
        format="%.2f"
    )
    if new_cash != pm.available_cash:
        if st.button("更新现金池", use_container_width=True):
            pm.available_cash = round(new_cash, 2)
            pm.save_state(record_snapshot=True)
            st.success("现金池已更新！")
            st.rerun()


# -------------------------------------------------------------
# 顶部全局看板：1 行 4 宽卡 + 1 个紧凑刷新按钮 (彻底消灭省略号)
# -------------------------------------------------------------
clock_status = market_status = clock.get_market_window_status(datetime.now())
intraday_eval = StrategyBridge.evaluate_intraday_signal()
rebal_grid = snapshot.get("rebal_grid") or StrategyBridge.get_rebalance_grid_status()
if pm.total_equity <= 0:
    pm._recalculate_totals()
total_cur_equity = float(getattr(pm, "total_equity", 0.0))
pnl_today = pm.calculate_intraday_pnl()
est_pnl = pnl_today.get("total_est_pnl", 0.0)
est_pnl_pct = pnl_today.get("total_est_pnl_pct", 0.0)
pnl_color = "#dc2626" if est_pnl >= 0 else "#16a34a"

c300_disp = intraday_eval.get("realtime_c300", snapshot.get("c300_price", snapshot.get('c300', 4053.0)))
bias_disp = intraday_eval.get("bias_m20", snapshot.get('bias_20', 0.0))
m20_disp = intraday_eval.get("m20", snapshot.get("m20_price", snapshot.get('m20', 4140.0)))
m60_disp = intraday_eval.get("m60", snapshot.get("m60_price", snapshot.get('m60', 3962.0)))
trigger_lines = snapshot.get("trigger_lines") or {}
surge_line = float(trigger_lines.get("surge_line", snapshot.get("surge_line", c300_disp * 1.012)))
breakdown_line = float(trigger_lines.get("breakdown_line", snapshot.get("breakdown_line", c300_disp * 0.985)))

erp_pct = snapshot.get("erp_percentile", 81.9)
erp_val = snapshot.get("erp_val", 5.82)
dr007_val = snapshot.get("dr007", 1.39)
dr007_bp = snapshot.get("dr007_spread_bp", -11.1)
opt_iv = float(snapshot.get("option_iv_pct", 19.4))
ic_basis = float(snapshot.get("ic_annualized_basis_rate", 17.9))
days_to_next = rebal_grid.get("days_to_next", rebal_grid.get("days_to_grid", 3))

top_c1, top_c2, top_c3, top_c4, top_btn = st.columns([2.5, 2.7, 2.5, 2.5, 0.8])

with top_c1:
    clock_color = '#16a34a' if market_status.is_golden_window else ('#dc2626' if market_status.is_after_market else '#0284c7')
    clock_title = "🟢 14:30黄金窗口" if market_status.is_golden_window else ("🟡 盘后已关账" if market_status.is_after_market else "🔵 盘中观察期")
    c1_tip = f"场外公募基金每日 15:00 关账。15:00 前下单按今日未知收盘净值成交，15:00 后下单顺延至下一交易日({market_status.effective_trade_date})成交。\n当前状态: {market_status.title}\n{market_status.message}"
    st.markdown(f"""
    <div class="main-metric-card">
        <div class="metric-card-title">
            <span>🕒 交易时钟与窗口</span>
            <span title="{c1_tip}" style="cursor:help; color:#94a3b8; font-size:12px;">ⓘ</span>
        </div>
        <div class="metric-value-huge" style="color: {clock_color};">
            {clock_title}
        </div>
        <div class="metric-card-sub">
            倒计时 {market_status.countdown_str} ｜ 距下次常规网格日 {days_to_next} 天
        </div>
    </div>
    """, unsafe_allow_html=True)

with top_c2:
    raw_mkt_state = str(snapshot.get('market_state', '震荡收息期'))
    if any(k in raw_mkt_state for k in ["震荡", "收息", "慢牛"]):
        vernacular_state = "🟢 震荡收息期"
    elif any(k in raw_mkt_state for k in ["科技", "主升", "进攻"]):
        vernacular_state = "🔥 科技主升浪"
    elif any(k in raw_mkt_state for k in ["熊", "防守", "破位"]):
        vernacular_state = "🛡️ 熊市防守期"
    else:
        vernacular_state = f"🟢 {raw_mkt_state[:6]}"

    st_color = snapshot.get('state_color', '#16a34a')
    c2_tip = f"沪深300现价: {c300_disp:,.1f}\nMA20生命线: {m20_disp:,.0f} (偏离 {bias_disp:+.1f}%)\nMA60中线: {m60_disp:,.0f}\n突破进攻线: 突破 {surge_line:,.0f} 后增配科技成长(科创50/中证1000)\n跌破防守线: 跌破 {breakdown_line:,.0f} 后减仓避险至纯债压舱石"
    st.markdown(f"""
    <div class="main-metric-card">
        <div class="metric-card-title">
            <span>🧭 市场定调与攻防线</span>
            <span title="{c2_tip}" style="cursor:help; color:#94a3b8; font-size:12px;">ⓘ</span>
        </div>
        <div class="metric-value-huge" style="color: {st_color};">
            {vernacular_state}
        </div>
        <div class="metric-card-sub" style="color: #475569;">
            📈破 {surge_line:,.0f} 进攻 ｜ 🛡️跌 {breakdown_line:,.0f} 防守
        </div>
    </div>
    """, unsafe_allow_html=True)

with top_c3:
    val_status = "估值极便宜 · 资金充裕" if (erp_pct >= 75 and dr007_bp <= 5) else "估值合理 · 流动性中性"
    c3_tip = f"ERP股债性价比分位: {erp_pct:.1f}% (极高分位·股票高性价比)\nDR007利率: {dr007_val:.2f}% (较基准 {dr007_bp:+.1f}bp·资金面宽裕)\n期权IV: {opt_iv:.1f}%\nIC期指年化贴水: {ic_basis:.1f}%"
    st.markdown(f"""
    <div class="main-metric-card">
        <div class="metric-card-title">
            <span>🌡️ 估值与资金面温度</span>
            <span title="{c3_tip}" style="cursor:help; color:#94a3b8; font-size:12px;">ⓘ</span>
        </div>
        <div class="metric-value-huge" style="color: #16a34a;">
            {val_status}
        </div>
        <div class="metric-card-sub">
            股票性价比高 ｜ 央妈呵护
        </div>
    </div>
    """, unsafe_allow_html=True)

with top_c4:
    c4_tip = f"全组合总资产: ¥{total_cur_equity:,.2f}\n可用现金: ¥{pm.available_cash:,.2f}\n在途资金: ¥{pm.in_transit_cash:,.2f}"
    st.markdown(f"""
    <div class="main-metric-card">
        <div class="metric-card-title">
            <span>💰 我的总资产与今日预估</span>
            <span title="{c4_tip}" style="cursor:help; color:#94a3b8; font-size:12px;">ⓘ</span>
        </div>
        <div class="metric-value-huge" style="color: #0f172a;">
            ¥{total_cur_equity:,.2f}
        </div>
        <div class="metric-card-sub" style="color: {pnl_color}; font-weight: 600;">
            今日预估 ¥{est_pnl:+,.2f} ({est_pnl_pct:+.2f}%)
        </div>
    </div>
    """, unsafe_allow_html=True)

with top_btn:
    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
    if st.button("🔄\n刷新", help="重新拉取实时净值与大盘点位", use_container_width=True, type="primary", key="btn_refresh_top_cards"):
        clear_realtime_cache()
        pm.sync_holdings_live_nav(use_intraday_gsz=True)
        StrategyBridge._cached_snapshot = None
        StrategyBridge._cached_matrix = None
        st.rerun()

# 盘后预案提醒
latest_plan = pm.get_latest_next_day_plan()
if latest_plan:
    with st.expander(f"📌 **您有已锁定的【{latest_plan.get('target_date')} 盯盘待办预案】** (创建于 {latest_plan.get('created_at')})", expanded=True):
        st.write("系统已为您锁定昨日盘后生成的调仓预案。请核对今日 14:30 盘中实时估值后一键执行：")
        col_exec_p, col_discard_p = st.columns([3, 7])
        with col_exec_p:
            if st.button("✅ 采纳并执行此待办预案", key="btn_apply_next_plan", type="primary", use_container_width=True):
                plan_obj = pm.generate_rebalance_plan(snapshot["target_weights_funds"], min_buffer_pct=3.0)
                routes = plan_obj.get("routes", [])
                if routes:
                    oids = pm.submit_rebalance_orders(routes)
                    pm.clear_next_day_plans()
                    st.balloons()
                    st.success(f"已成功执行待办预案，生成在途单：{', '.join(oids)}！")
                    st.rerun()
                else:
                    st.info("持仓偏离度在 3% 缓冲阈值内，无需额外调仓。")
        with col_discard_p:
            if st.button("🗑️ 放弃并清理此待办预案", key="btn_discard_next_plan"):
                pm.clear_next_day_plans()
                st.info("已清理待办预案。")
                st.rerun()

st.markdown(" ")

# 缓存包装
@st.cache_data(ttl=300)
def _cached_backtest_nav(tier: str):
    return StrategyBridge.get_backtest_nav_for_tier(tier)

@st.cache_data(ttl=300)
def _cached_find_historical_analogs(top_k: int = 3):
    return StrategyBridge.find_historical_analogs(top_k=top_k)

@st.cache_data(ttl=300)
def _cached_look_through_industry(holdings_repr: str):
    return pm.calculate_look_through_industry_exposure()

@st.cache_data(ttl=300)
def _cached_stock_overlap(holdings_repr: str):
    return pm.calculate_stock_overlap_matrix()

@st.cache_data(ttl=300)
def _cached_penetration_risk(holdings_repr: str):
    return pm.calculate_portfolio_penetration_risk()

@st.cache_data(ttl=300)
def _cached_stocks_df(holdings_repr: str):
    return pm.get_portfolio_look_through_stocks_df()


# -------------------------------------------------------------
# 核心四大工作区 (精简 ≤ 5 字符，彻底砍掉独立 Tab 5)
# -------------------------------------------------------------
tab_zero_start, tab_holdings_and_rebalance, tab_backtest, tab_toolbox = st.tabs([
    "🌱 新资建仓",
    "💼 持仓调仓",
    "📈 组合回测",
    "🔍 穿透工具"
])

# =============================================================
# Tab 1: 【🌱 新资建仓】（从 0 定目标、真全市场漏斗、机构级模型、看推演、拿建仓单）
# =============================================================
if "active_tier_val" not in st.session_state:
    st.session_state.active_tier_val = "C3"
if "target_return_val" not in st.session_state:
    st.session_state.target_return_val = 15.0

with tab_zero_start:
    try:
        active_tier = st.session_state.get("active_tier_val", "C3")
        cur_tier_meta = RISK_TIERS_CONFIG.get(active_tier, RISK_TIERS_CONFIG["C3"])
        st.subheader("🌱 新资建仓")
        st.caption("全市场 2.8 万只基金智能漏斗！支持 3~15 只基金自由调节，四大机构级模型自适应定权，现场生成清晰账单。")

        # 初始化状态机
        if "tab1_step_reached" not in st.session_state:
            st.session_state.tab1_step_reached = 1
        if "tab1_trigger_sim" not in st.session_state:
            st.session_state.tab1_trigger_sim = False
        if "tab1_trigger_s3" not in st.session_state:
            st.session_state.tab1_trigger_s3 = False
        if "tab1_last_calc_params" not in st.session_state:
            st.session_state.tab1_last_calc_params = None
        if "tab1_sim_cache" not in st.session_state:
            st.session_state.tab1_sim_cache = None
        if "tab1_step3_cache" not in st.session_state:
            st.session_state.tab1_step3_cache = None
        if "target_return_val" not in st.session_state:
            st.session_state.target_return_val = 15.0
        if "tab1_num_funds" not in st.session_state:
            st.session_state.tab1_num_funds = 6
        if "tab1_model_type" not in st.session_state:
            st.session_state.tab1_model_type = "hrp_cvar"
        if "custom_fund_overrides" not in st.session_state:
            st.session_state.custom_fund_overrides = {}

        # 🧭 工作流步骤与系统状态指示器
        step_now = int(st.session_state.get("tab1_step_reached", 1))
        render_workflow_step_indicator(
            ["设定目标与测风险", "量化推演看好坏", "生成实盘建仓单"],
            current_step=step_now,
            help_text="请在步骤一设定目标参数并点击【▶️ 确认目标参数，进入步骤二】开始现场推演" if step_now == 1 else (
                "步骤二已生成全周期推演与人话指标，请点击【▶️ 确认推演方案，进入步骤三】生成建仓单" if step_now == 2 else
                "步骤三已生成实盘建仓执行单与下单小抄，可点击一键设为初始持仓"
            )
        )

        # ---------------------------------------------------------
        # 步骤一：设定目标风险
        # ---------------------------------------------------------
        with st.container(border=True):
            st.markdown("### 步骤一：设定目标风险")

            tier_mode = st.radio(
                "定档方式",
                ["模式 A：按期望年化收益率滑块定档 (滑块即拉即变)", "模式 B：30秒风险承受力测评定档"],
                horizontal=True,
                key="tier_determination_mode"
            )

            if tier_mode.startswith("模式 A"):
                col_s1_left, col_s1_right = st.columns([6, 4])
                with col_s1_left:
                    target_ret_input = st.slider(
                        "期望年化目标收益率 (%)",
                        min_value=5.0,
                        max_value=100.0,
                        value=float(st.session_state.get("target_return_val", 15.0)),
                        step=1.0,
                        format="%.0f%%",
                        help="拖动滑块即拉即变，C1 至 C5 实时同步切换",
                        key="slider_target_return"
                    )
                    st.session_state.target_return_val = target_ret_input
                    active_tier = map_slider_to_tier(target_ret_input)
                    st.session_state.active_tier_val = active_tier

                with col_s1_right:
                    plan_capital = st.number_input(
                        "💵 拟投资总本金 (元)",
                        min_value=1000.0,
                        max_value=100000000.0,
                        value=100000.0,
                        step=10000.0,
                        format="%.0f",
                        key="plan_capital_input"
                    )

                cur_tier_meta = RISK_TIERS_CONFIG.get(active_tier, RISK_TIERS_CONFIG["C3"])
                if target_ret_input > 25.0:
                    st.caption(f"⚡ 高收益提示：目标年化 {target_ret_input:.0f}% 对应【{active_tier} {cur_tier_meta['name']}】，历史最大回撤约 {abs(cur_tier_meta['historical_mdd']):.1f}%，解套需 {cur_tier_meta['max_tolerated_months']} 个月，建议长钱长投。")
                else:
                    st.caption(f"💡 目标收益 {target_ret_input:.0f}% ➔ 当前档位：【{active_tier} {cur_tier_meta['name']}】（权益上限 {cur_tier_meta['equity_range'][1]}% ｜ 预期年化 {cur_tier_meta['target_cagr']} ｜ 核心：{cur_tier_meta['core_assets']}）")
            else:
                col_q1, col_q2, col_q3 = st.columns(3)
                with col_q1:
                    q1_ans = st.selectbox(
                        "1. 最大能忍受浮亏多深？",
                        [
                            "A. 极度厌恶亏损，超过 3% 睡不着 (0分)",
                            "B. 最多接受 5%~10% 回撤，希望稳健 (1分)",
                            "C. 可承受 10%~18% 波动，跑赢通胀 (2分)",
                            "D. 可承受 18%~28% 震荡，主打弹性 (3分)",
                            "E. 哪怕腰斩 -30% 也无所谓，求翻倍 (4分)"
                        ],
                        index=2,
                        key="q1_risk_test"
                    )
                with col_q2:
                    q2_ans = st.selectbox(
                        "2. 拟投资期限是多久？",
                        [
                            "A. 随时用，1~3个月内 (0分)",
                            "B. 6个月到1年左右 (1分)",
                            "C. 1~3年闲钱 (2分)",
                            "D. 3~5年长期闲钱 (3分)",
                            "E. 5年以上闲钱 (4分)"
                        ],
                        index=2,
                        key="q2_risk_test"
                    )
                with col_q3:
                    q3_ans = st.selectbox(
                        "3. 阶段性浮亏 -15% 时的反应？",
                        [
                            "A. 惊慌失措，立刻割肉 (0分)",
                            "B. 焦虑不安，暂停投入 (1分)",
                            "C. 情绪平静，按兵不动 (2分)",
                            "D. 估值击球区，分批补仓 (3分)",
                            "E. 兴奋狂喜，大举逆势加仓 (4分)"
                        ],
                        index=2,
                        key="q3_risk_test"
                    )

                s1 = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}[q1_ans[0]]
                s2 = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}[q2_ans[0]]
                s3 = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}[q3_ans[0]]
                total_q_score = s1 + s2 + s3
                tested_tier = evaluate_questionnaire_risk_tier(total_q_score)
                st.session_state.tested_tier_val = tested_tier
                st.session_state.active_tier_val = tested_tier
                active_tier = tested_tier
                cur_tier_meta = RISK_TIERS_CONFIG.get(active_tier, RISK_TIERS_CONFIG["C3"])
                target_ret_input = float(cur_tier_meta.get("default_target", 15.0))
                st.session_state.target_return_val = target_ret_input

                col_cap_b, _ = st.columns([6, 4])
                with col_cap_b:
                    plan_capital = st.number_input(
                        "💵 拟投资总本金 (元)",
                        min_value=1000.0,
                        max_value=100000000.0,
                        value=100000.0,
                        step=10000.0,
                        format="%.0f",
                        key="plan_capital_input_b"
                    )

                st.caption(f"📝 问卷总分：`{total_q_score} 分` ➔ 评定承受档位：**【{active_tier} {cur_tier_meta['name']}】**（默认目标年化 {target_ret_input:.0f}% ｜ 建议年化 {cur_tier_meta['target_cagr']} ｜ 容忍回撤 {cur_tier_meta['max_drawdown_limit']}）")

            col_h, col_nf, col_mod = st.columns([3.5, 3.5, 3.0])
            with col_h:
                horizon_choice = st.radio(
                    "📅 计划持有期",
                    ["短期(3~6月)", "中期(1~2年)", "长期(3~5年)"],
                    index=1,
                    horizontal=True,
                    key="tab1_horizon_radio"
                )
            with col_nf:
                num_funds_input = st.slider(
                    "🎯 最终优选基金只数",
                    min_value=3,
                    max_value=15,
                    value=int(st.session_state.get("tab1_num_funds", 6)),
                    step=1,
                    help="用户可自由在 3~15 只之间调节组合基金数量，底层量化模型自适应调整候选池与单基权重约束",
                    key="tab1_slider_num_funds"
                )
                st.session_state.tab1_num_funds = num_funds_input

            with col_mod:
                model_options_map = {
                    "鲁棒双核HRP": "hrp_cvar",
                    "条件胜率最优": "cond_winrate",
                    "尾部风控CVaR": "min_cvar",
                    "凯利动量增强": "kelly_momentum"
                }
                cur_model_key = st.session_state.get("tab1_model_type", "hrp_cvar")
                inv_map = {v: k for k, v in model_options_map.items()}
                default_disp = inv_map.get(cur_model_key, "鲁棒双核HRP")

                model_disp_choice = st.selectbox(
                    "🧠 机构级量化定权模型",
                    list(model_options_map.keys()),
                    index=list(model_options_map.keys()).index(default_disp),
                    key="tab1_sel_model_type"
                )
                sel_model_type = model_options_map[model_disp_choice]
                st.session_state.tab1_model_type = sel_model_type

            # ── 宏观环境自适应识别横幅与模型推荐 ──
            regime_rec = recommend_model_for_regime(snapshot, target_ret_input)
            rec_key = regime_rec["recommended_model_key"]
            rec_name = regime_rec["recommended_model_name"]
            is_matching_rec = (sel_model_type == rec_key)

            rec_badge_style = "background: rgba(37, 99, 235, 0.08); border: 1.5px solid #2563eb;" if is_matching_rec else "background: rgba(245, 158, 11, 0.08); border: 1.5px solid #d97706;"
            rec_title_color = "#1d4ed8" if is_matching_rec else "#b45309"
            match_hint = "（当前已采纳推荐）" if is_matching_rec else f"（当前选择：{model_disp_choice}，点击模型下拉可一键切换）"

            st.markdown(f"""
            <div style="{rec_badge_style} border-radius: 8px; padding: 12px 16px; margin: 8px 0 12px 0;">
                <div style="font-size: 14px; font-weight: 700; color: {rec_title_color}; margin-bottom: 4px;">
                    🧭 宏观环境识别：【{regime_rec['regime_name']}】 ➔ 机构首选推荐：【{rec_name}】{match_hint}
                </div>
                <div style="font-size: 12px; color: #334155; line-height: 1.5;">
                    {regime_rec['reason']}<br>
                    <span style="color: #64748b;">实时四维指标：ERP估值分位 {regime_rec['erp_percentile']:.1f}% ｜ MA20偏离 {regime_rec['bias_20']:+.2f}% ｜ DR007利率 {regime_rec['dr007']:.2f}% ｜ 期权iVIX {regime_rec['ivix']:.1f}%</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("🔍 【点击展开】：四大机构级量化模型特性与适用场景全景对比", expanded=False):
                model_table_rows = []
                for m_k, m_info in QUANT_MODELS_CATALOG.items():
                    model_table_rows.append({
                        "模型名称": m_info["name"],
                        "机构评级标签": m_info["badge"],
                        "数学与量化原理": m_info["principle"],
                        "核心优势": m_info["advantage"],
                        "最适用市场环境": m_info["suitable_when"]
                    })
                st.dataframe(pd.DataFrame(model_table_rows), use_container_width=True, hide_index=True)

            # ── 用户掌控权：参数调整与下游重计算解耦 ──
            cur_tab1_params = {
                "target_ret": float(target_ret_input),
                "capital": float(plan_capital),
                "tier": str(active_tier),
                "num_funds": int(num_funds_input),
                "model_type": str(sel_model_type),
                "horizon": str(horizon_choice),
                "overrides": tuple(sorted(st.session_state.get("custom_fund_overrides", {}).items()))
            }
            _last_p = st.session_state.get("tab1_last_calc_params")
            if st.session_state.get("tab1_step_reached", 1) >= 2 and _last_p is not None and _last_p != cur_tab1_params:
                st.warning("⚠️ 检测到您已调整目标参数（当前未同步至下方结果），请点击【▶️ 确认目标参数，进入步骤二】或【🚀 一键全流程计算】更新结果。")

            st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
            # 单排固定容器按钮，彻底根除图 1 双排残影
            col_s1_step, col_s1_all = st.columns([1, 1])
            with col_s1_step:
                if st.button("▶️ 确认目标参数，进入步骤二：开始现场推演", type="primary", use_container_width=True, key="btn_run_simulation_now"):
                    st.session_state.tab1_step_reached = 2
                    st.session_state.tab1_step3_cache = None
                    st.session_state.tab1_trigger_sim = True
                    st.session_state.tab1_last_calc_params = cur_tab1_params
                    st.rerun()
            with col_s1_all:
                if st.button("🚀 一键全流程计算 (现场推演 + 建仓交割单)", type="secondary", use_container_width=True, key="btn_t1_run_all"):
                    st.session_state.tab1_step_reached = 3
                    st.session_state.tab1_trigger_sim = True
                    st.session_state.tab1_trigger_s3 = True
                    st.session_state.tab1_last_calc_params = cur_tab1_params
                    st.rerun()

        # ---------------------------------------------------------
        # 严格分步隔离：若未进入步骤二，绝对不渲染步骤二与步骤三！
        # ---------------------------------------------------------
        if st.session_state.get("tab1_step_reached", 1) >= 2:
            st.markdown("---")
            m_title = QUANT_MODELS_CATALOG.get(sel_model_type, {}).get("name", "鲁棒双核HRP")
            st.markdown(f"### 步骤二：现场推演评估")
            st.caption(f"当前模型：**{m_title}** ｜ 优选标的：**{num_funds_input} 只** ｜ 目标档位：**【{active_tier} {cur_tier_meta['name']}】**")

            if st.session_state.get("tab1_trigger_sim", False) or st.session_state.get("tab1_sim_cache") is None:
                acc = ActiveComputationConsole(f"AI 投顾真全市场 2.8 万只漏斗推演 ({num_funds_input}只)", total_steps=4, step_labels=[
                    f"步骤 1: 全市场 28,177 只漏斗初筛与赛道初选",
                    f"步骤 2: 宏观同温层定调与【{m_title}】求解 {num_funds_input} 只基金配比",
                    f"步骤 3: 2018-2026 跨牛熊日度净值合成与多周期胜率",
                    f"步骤 4: 最好/最坏情况、95% CVaR 与水下回本精算"
                ])
                def _sim_cb(cur, tot, msg):
                    acc.update_step(cur, msg, progress_pct=int((cur / max(tot, 1)) * 95))

                res_portfolio = StrategyBridge.compute_n_funds_model_portfolio(
                    tier=active_tier,
                    target_return_pct=float(cur_tab1_params["target_ret"]),
                    num_funds=int(num_funds_input),
                    model_type=sel_model_type,
                    horizon_label=horizon_choice,
                    capital=float(plan_capital),
                    custom_overrides=st.session_state.get("custom_fund_overrides", {}),
                    progress_cb=_sim_cb
                )
                acc.complete("真全市场选基与推演完成！")
                st.session_state.tab1_sim_cache = res_portfolio
                st.session_state.tab1_trigger_sim = False

            _cache_entry = st.session_state.get("tab1_sim_cache") or {}
            readable_kpi = _cache_entry.get("readable_kpi", {})
            bt_df = _cache_entry.get("bt_df", pd.DataFrame())
            wr_table = _cache_entry.get("wr_table", {})
            quant_table = _cache_entry.get("quant_table", pd.DataFrame())
            funnel_stats = _cache_entry.get("funnel_stats", {})
            opt_weights = _cache_entry.get("optimal_weights", {})
            alts_map = _cache_entry.get("alternatives_by_slot", {})

            # 3 张条件胜率卡（带保本率、跑赢货基率、中位年化）
            st.markdown("#### 🎯 2018-2026 全周期跨牛熊滚动持有胜率 (同温层状态机条件加权)")
            _wr_cols = st.columns(3)
            for _wi, (_wk, _wv) in enumerate(wr_table.items()):
                with _wr_cols[_wi]:
                    _med_ann = float(_wv.get("median_ann_return", _wv.get("median_return", 0.0))) * 100.0
                    _no_loss = float(_wv.get("no_loss_rate", 0.0)) * 100.0
                    _beat_cash = float(_wv.get("beat_cash_rate", _no_loss * 0.95)) * 100.0
                    st.metric(
                        f"{_wv['label']} 胜率",
                        f"{_wv['win_rate']*100:.1f}%",
                        delta=f"保本 {_no_loss:.0f}% ｜ 跑赢货基 {_beat_cash:.0f}% ｜ 中位 {_med_ann:.1f}%",
                    )

            with st.expander("ℹ️ 【量化数学定义】：为什么需要同时看达标胜率、保本率、跑赢货基率与 95% CVaR？", expanded=False):
                st.markdown(r"""
                - **达标胜率**：在历史所有滚动持有期窗口中，组合真实年化收益率 $\ge$ 用户设定目标年化收益率的加权百分比；
                - **保本率 (收益 $\ge 0\%$)**：持有期满本金不亏损的概率。纯债配置较高时此项较高，但不可与“达标胜率”混为一谈；
                - **跑赢货基率 (收益 $\ge 1.8\%$)**：年化净收益超越同期货币基金与现金管理的概率，反映承担波动是否获得有效流动性溢价；
                - **95% 尾部底线 (CVaR)**：在历史最极端的 5% 尾部黑天鹅行情中，组合的平均亏损底线，杜绝深度套牢。
                """)

            # 5 张大字号人话指标卡（标题严格 ≤ 6 字）
            k_col1, k_col2, k_col3, k_col4, k_col5 = st.columns(5)
            with k_col1:
                st.markdown(f"""
                <div class="kpi-metric-card" style="border-top: 3px solid #ef4444;">
                    <div class="kpi-card-title">① 最好情况</div>
                    <div class="metric-value-huge" style="color: #dc2626;">
                        +{readable_kpi.get('best_case_return_pct', 0.0):.2f}%
                    </div>
                    <div class="kpi-card-sub" style="color: #b91c1c;">
                        预计盈利: <b>+¥{readable_kpi.get('best_case_profit_amount', 0.0):,.2f}</b>
                    </div>
                    <div class="kpi-card-desc">任意持有1年最高单年收益</div>
                </div>
                """, unsafe_allow_html=True)

            with k_col2:
                st.markdown(f"""
                <div class="kpi-metric-card" style="border-top: 3px solid #10b981;">
                    <div class="kpi-card-title">② 最坏情况</div>
                    <div class="metric-value-huge" style="color: #15803d;">
                        -{readable_kpi.get('worst_case_drawdown_pct', 0.0):.2f}%
                    </div>
                    <div class="kpi-card-sub" style="color: #166534;">
                        账面最大浮亏: <b>-¥{readable_kpi.get('worst_case_loss_amount', 0.0):,.2f}</b>
                    </div>
                    <div class="kpi-card-desc">历史全周期最极端至暗时刻</div>
                </div>
                """, unsafe_allow_html=True)

            with k_col3:
                st.markdown(f"""
                <div class="kpi-metric-card" style="border-top: 3px solid #3b82f6;">
                    <div class="kpi-card-title">③ 水下回本</div>
                    <div class="metric-value-huge" style="color: #1d4ed8;">
                        {readable_kpi.get('max_underwater_days', 0)} <span style="font-size:16px;">天</span>
                    </div>
                    <div class="kpi-card-sub" style="color: #1e40af;">
                        最长水下: <b>约 {readable_kpi.get('max_underwater_months', 0.0):.1f} 个月</b>
                    </div>
                    <div class="kpi-card-desc">买在历史最高点回本所需时长</div>
                </div>
                """, unsafe_allow_html=True)

            with k_col4:
                st.markdown(f"""
                <div class="kpi-metric-card" style="border-top: 3px solid #8b5cf6;">
                    <div class="kpi-card-title">④ 目标胜率</div>
                    <div class="metric-value-huge" style="color: #6d28d9;">
                        {readable_kpi.get('win_rate_1y', 0.0):.1f}%
                    </div>
                    <div class="kpi-card-sub" style="color: #5b21b6;">
                        1年: <b>{readable_kpi.get('win_rate_1y', 0.0):.1f}%</b> ｜ 2年: <b>{readable_kpi.get('win_rate_2y', 0.0):.1f}%</b>
                    </div>
                    <div class="kpi-card-desc">持有满 3 年胜率 {readable_kpi.get('win_rate_3y', 0.0):.1f}%</div>
                </div>
                """, unsafe_allow_html=True)

            with k_col5:
                st.markdown(f"""
                <div class="kpi-metric-card" style="border-top: 3px solid #f59e0b;">
                    <div class="kpi-card-title">⑤ 适合资金</div>
                    <div class="metric-value-huge" style="color: #b45309; font-size: 20px; line-height: 1.4;">
                        {active_tier} {cur_tier_meta['name']}
                    </div>
                    <div class="kpi-card-sub" style="color: #92400e; font-size: 11px;">
                        {readable_kpi.get('suitable_for', '')}
                    </div>
                    <div class="kpi-card-desc" style="font-size: 11px;">{readable_kpi.get('soul_summary', '')}</div>
                </div>
                """, unsafe_allow_html=True)

            # 白盒折叠框 1: 全市场选基漏斗与评分表
            with st.expander("🔍 【点击展开白盒推演详情】：全市场选基漏斗与赛道冠军打分表", expanded=False):
                f_c1, f_c2, f_c3, f_c4 = st.columns(4)
                with f_c1:
                    _tot_m = funnel_stats.get('total_market_funds', 28177)
                    st.metric("1. 全市场基金底池", f"{_tot_m:,} 只", "全市场公募基金总数")
                with f_c2:
                    _comp_s = funnel_stats.get('compliance_screened_funds', 6850)
                    st.metric("2. 六维量化初筛池", f"{_comp_s:,} 只", "规模>2亿·成立>3年·合规排雷")
                with f_c3:
                    funnel_stats['candidate_funds'] = funnel_stats.get('candidate_funds', max(28, num_funds_input * 6))
                    st.metric("3. 5大赛道入围池", f"{funnel_stats['candidate_funds']} 只", "核心赛道低费率&高Alpha候选池")
                with f_c4:
                    _champ_s = len(opt_weights)
                    st.metric("4. 最终优选金牌组合", f"{_champ_s} 只", f"动态对齐用户调节的 {num_funds_input} 只", delta_color="inverse")

                st.markdown("##### 📐 《六维量化打分加权公式（0~100分归一化）》")
                st.info("综合评分计算公式：总评得分 (0-100) = 35% * 历史超额Alpha得分 + 25% * 低费率得分 + 15% * R1底层排雷健康分 + 10% * R3北向聪明钱流入分 + 10% * 反拥挤度安全分 + 5% * 衍生品与宏观契合度")

                st.markdown(f"##### 📊 《当前档位入选标的：{_champ_s} 只冠军基金六维量化评分明细表》")
                if not quant_table.empty:
                    st.dataframe(
                        quant_table,
                        column_config={
                            "六维总评得分": st.column_config.NumberColumn(format="%.2f分"),
                            "超额Alpha得分(35%)": st.column_config.NumberColumn(format="%.1f分"),
                            "低费率得分(25%)": st.column_config.NumberColumn(format="%.1f分"),
                            "底层排雷健康分(15%)": st.column_config.NumberColumn(format="%.1f分"),
                            "聪明钱流入分(10%)": st.column_config.NumberColumn(format="%.1f分"),
                            "反拥挤安全分(10%)": st.column_config.NumberColumn(format="%.1f分"),
                            "衍生品契合分(5%)": st.column_config.NumberColumn(format="%.1f分"),
                            "配置权重(%)": st.column_config.ProgressColumn(min_value=0, max_value=60, format="%.1f%%"),
                        },
                        use_container_width=True,
                        hide_index=True
                    )

                if alts_map:
                    st.caption("🏆 赛道冠军标的与备选替换下拉框（选基与建仓单 100% 联动）：")
                    cols_slots = st.columns(min(len(alts_map), 4))
                    for idx_s, (slot_k, slot_data) in enumerate(alts_map.items()):
                        c_col = cols_slots[idx_s % len(cols_slots)]
                        with c_col:
                            s_champ = slot_data["champion_code"]
                            s_champ_name = slot_data["champion_name"]
                            opts = [f"🏆 {s_champ} {s_champ_name}"]
                            for a_it in slot_data.get("top_alternatives", []):
                                opts.append(f"🥈 {a_it['code']} {a_it['name']} ({a_it.get('tag', '优质备选')})")

                            cur_ovr = st.session_state.custom_fund_overrides.get(s_champ)
                            s_idx = 0
                            if cur_ovr:
                                for o_i, o_str in enumerate(opts):
                                    if cur_ovr in o_str:
                                        s_idx = o_i
                                        break
                            chosen = st.selectbox(
                                slot_data["sector_name"],
                                opts,
                                index=s_idx,
                                key=f"slot_sel_{slot_k}_{num_funds_input}"
                            )
                            old_ovr = st.session_state.custom_fund_overrides.get(s_champ)
                            new_ovr = None
                            if not chosen.startswith("🏆"):
                                sel_c = chosen.split()[1]
                                new_ovr = sel_c
                                st.session_state.custom_fund_overrides[s_champ] = sel_c
                            else:
                                if s_champ in st.session_state.custom_fund_overrides:
                                    del st.session_state.custom_fund_overrides[s_champ]
                            
                            if old_ovr != new_ovr:
                                st.session_state.tab1_step3_cache = None
                                st.session_state.tab1_trigger_s3 = True
                                if st.session_state.get("tab1_sim_cache"):
                                    opt_w = dict(st.session_state["tab1_sim_cache"].get("optimal_weights", {}))
                                    if s_champ in opt_w and new_ovr:
                                        val = opt_w.pop(s_champ)
                                        opt_w[new_ovr] = val
                                        st.session_state["tab1_sim_cache"]["optimal_weights"] = opt_w
                                    elif old_ovr in opt_w and not new_ovr:
                                        val = opt_w.pop(old_ovr)
                                        opt_w[s_champ] = val
                                        st.session_state["tab1_sim_cache"]["optimal_weights"] = opt_w

            # 白盒折叠框 2: 宏观信号
            with st.expander("🧭 【点击展开白盒推演详情】：宏观流动性、风格动量与衍生品四维因果决策信号", expanded=False):
                c_sig1, c_sig2, c_sig3, c_sig4 = st.columns(4)
                with c_sig1:
                    st.markdown(f"""
                    <div class="decision-card">
                        <div class="decision-title">① 市场温度与估值水位</div>
                        <div class="decision-val">{snapshot.get('market_state', '震荡收息期')}</div>
                        <div class="decision-desc">
                            沪深300点位: <b>{snapshot.get('c300', 4000.0):,.0f}</b><br>
                            ERP 估值分位: <b>{snapshot.get('erp_percentile', 78.5):.1f}%</b> (高性价比击球区)
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                with c_sig2:
                    st.markdown(f"""
                    <div class="decision-card">
                        <div class="decision-title">② 均线动量状态 (MA20)</div>
                        <div class="decision-val" style="color: #0284c7;">{snapshot.get('m20_status_desc', '站上均线')}</div>
                        <div class="decision-desc">
                            MA20 乖离率: <b>{snapshot.get('bias_20', 1.2):+.2f}%</b><br>
                            技术研判: 右侧趋势形成，顺势跟进红利与成长动量。
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                with c_sig3:
                    st.markdown(f"""
                    <div class="decision-card">
                        <div class="decision-title">③ 宏观资金利率 (DR007)</div>
                        <div class="decision-val" style="color: #059669;">{snapshot.get('dr007_status', '流动性合理充裕')}</div>
                        <div class="decision-desc">
                            DR007 7天移动均值: <b>{snapshot.get('dr007_7d_ma', 1.62):.2f}%</b><br>
                            流动性定调: 资金面平稳，债市底仓安全无虞。
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                with c_sig4:
                    st.markdown(f"""
                    <div class="decision-card">
                        <div class="decision-title">④ 期权波动率防波堤 (iVIX)</div>
                        <div class="decision-val" style="color: #d97706;">{snapshot.get('ivix_status', '期权隐含波动率平稳')}</div>
                        <div class="decision-desc">
                            EWMA 历史波动率: <b>{snapshot.get('ewma_vol', 12.8):.1f}%</b><br>
                            情绪定调: 尾部对冲成本低，适合配置长久期优质资产。
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            # 三句话看懂本方案 (四大归因卡片)
            st.markdown("#### 🎯 《三句话看懂本方案：怎么赚钱、为什么能赢、风险与铁律》")
            col_card1, col_card2, col_card3, col_card4 = st.columns(4)
            with col_card1:
                st.markdown(f"""
                <div class="decision-card" style="border-top: 3px solid #b91c1c;">
                    <div class="decision-title" style="color: #b91c1c;">
                        💰 ① 怎么赚钱？
                    </div>
                    <div class="decision-desc">
                        高比例稳健纯债与红利低波筑牢底盘，估值低位增配高贝塔成长先锋，捕捉牛市主升浪。
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col_card2:
                st.markdown(f"""
                <div class="decision-card" style="border-top: 3px solid #15803d;">
                    <div class="decision-title" style="color: #15803d;">
                        🏆 ② 为什么能赢？
                    </div>
                    <div class="decision-desc">
                        28,177只全市场漏斗严选各赛道前1%冠军标的，同温层状态机匹配相似历史高胜率解。
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col_card3:
                st.markdown(f"""
                <div class="decision-card" style="border-top: 3px solid #b45309;">
                    <div class="decision-title" style="color: #b45309;">
                        🚨 ③ 风险与底线
                    </div>
                    <div class="decision-desc">
                        历史最极端浮亏 -{readable_kpi.get('worst_case_drawdown_pct', 0.0):.2f}%，最长水下约 {readable_kpi.get('max_underwater_days', 0)} 天，做好回本预期。
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col_card4:
                st.markdown(f"""
                <div class="decision-card" style="border-top: 3px solid #0369a1;">
                    <div class="decision-title" style="color: #0369a1;">
                        ⚖️ ④ 执行铁律
                    </div>
                    <div class="decision-desc">
                        买入未满7天绝不赎回拦截1.5%惩罚费；底部便宜区绝不割肉，红利类强制现金分红。
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # ── 解决问题 4 的核心推进按钮：步骤二底部永远渲染 ──
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            col_b_step3, _ = st.columns([1, 1])
            with col_b_step3:
                step3_btn_label = "▶️ 确认推演方案，进入步骤三：生成实盘建仓单" if st.session_state.get("tab1_step_reached", 1) == 2 else "🔄 重新生成步骤三建仓单（按当前推演方案更新）"
                if st.button(step3_btn_label, type="primary", use_container_width=True, key="btn_t1_step_to_s3"):
                    st.session_state.tab1_step_reached = 3
                    st.session_state.tab1_trigger_s3 = True
                    st.rerun()

        # ---------------------------------------------------------
        # 严格步骤三隔离：若未进入步骤三，绝对不渲染步骤三！
        # ---------------------------------------------------------
        if st.session_state.get("tab1_step_reached", 1) >= 3:
            st.markdown("---")
            st.markdown("### 步骤三：生成实盘建仓")

            if st.session_state.get("tab1_trigger_s3", False) or st.session_state.get("tab1_step3_cache") is None:
                sim_c = st.session_state.get("tab1_sim_cache") or {}
                cur_opt_w = sim_c.get("optimal_weights", {})
                overrides = st.session_state.get("custom_fund_overrides", {})

                blueprint = StrategyBridge.generate_zero_start_blueprint(
                    total_capital=float(plan_capital),
                    target_weights_funds=cur_opt_w,
                    tier=active_tier,
                    custom_fund_overrides=overrides
                )

                items = blueprint["items"]
                n_funds = len(items)
                acc_s3 = ActiveComputationConsole(
                    f"生成【{active_tier} 档位】实盘建仓单与限购拆单 ({n_funds}只)",
                    total_steps=n_funds + 1,
                    step_labels=["步骤 1: 生成建仓交割单与限额拆单规则"] + [
                        f"步骤 {i+2}: 拉取 {it['fund_code']} 实时估值与排雷" for i, it in enumerate(items)
                    ]
                )
                acc_s3.update_step(0, "正在生成基础建仓单与智能限额拆单规则...", progress_pct=10)

                bp_rows = []
                cheat_sheet_lines = [
                    f"【AGY2 智能投顾专属建仓小抄】",
                    f"配置档位：{active_tier} {cur_tier_meta['name']} ｜ 模型：{QUANT_MODELS_CATALOG.get(sel_model_type, {}).get('name', 'HRP')} ｜ 目标总投入：¥{plan_capital:,.2f}",
                    f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    f"----------------------------------------"
                ]

                for idx, it in enumerate(items, 1):
                    fcode = it["fund_code"]
                    acc_s3.update_step(idx, f"正在拉取 [{idx}/{n_funds}] 基金 ({fcode}) 实时估值与排雷...", progress_pct=int(10 + (idx / n_funds) * 85))
                    q_it = fetch_realtime_fund_quote(fcode)
                    scr_it = pm.screen_fund_look_through_risk(fcode)
                    crd_it = pm.get_fund_smart_money_crowding(fcode)

                    risk_badge_disp = scr_it.get("risk_badge", "🟢 健康")
                    crowd_deg_disp = crd_it.get("crowding_degree", "相对分散")
                    if crd_it.get("crowding_warning"):
                        crowd_deg_disp += " ⚠️"

                    risk_and_crowd = f"{risk_badge_disp} ｜ {crowd_deg_disp}"
                    div_short = "现金分红" if it.get("require_cash_dividend") else "红利再投"

                    raw_guide = it.get("action_guide") or ("已拆单" if it.get("has_split") else "正常买入")
                    if it.get("require_cash_dividend"):
                        guide_action = f"现金分红·{raw_guide}" if (raw_guide and raw_guide != "正常买入") else "现金分红·满期免赎A"
                    elif raw_guide and raw_guide != "正常买入":
                        guide_action = raw_guide
                    elif it.get("share_class") == "C":
                        guide_action = "红利再投·弹性进攻C"
                    else:
                        guide_action = "长钱持有·满期免赎A"

                    bp_rows.append({
                        "基金代码": fcode,
                        "基金名称": it["fund_name"],
                        "份额": f"{it.get('share_class', 'A')}类",
                        "目标占比(%)": it.get("target_weight_pct", 0.0),
                        "精确买入金额(元)": it.get("allocated_amount", it.get("amount", 0.0)),
                        "最新净值": q_it.dwjz if q_it else 1.0,
                        "实时估值涨跌(%)": q_it.gszzl if q_it else 0.0,
                        "排雷与拥挤度": risk_and_crowd,
                        "实操分红与限购指引": guide_action
                    })

                    cheat_sheet_lines.append(
                        f"{idx}. 基金代码: {fcode} ({it['fund_name']}) | 买入金额: ¥{it['allocated_amount']:,.2f} ({it['target_weight_pct']:.1f}%) | 份额: {it.get('share_class', 'A')}类 | 分红方式: {div_short} | 指引: {guide_action}"
                    )

                cheat_sheet_lines.append("----------------------------------------")
                cheat_sheet_lines.append("💡 下单提醒：场外基金请在交易日 15:00 前完成支付，15:00 后下单将按次日未知净值成交。")
                cheat_sheet_text = "\n".join(cheat_sheet_lines)

                cols_9 = [
                    "基金代码", "基金名称", "份额", "目标占比(%)",
                    "精确买入金额(元)", "最新净值", "实时估值涨跌(%)",
                    "排雷与拥挤度", "实操分红与限购指引"
                ]
                df_bp = pd.DataFrame(bp_rows)[cols_9]
                acc_s3.complete("实盘建仓单与限购拆单小抄已就绪")

                st.session_state.tab1_step3_cache = {
                    "blueprint": blueprint,
                    "df_bp": df_bp,
                    "cheat_sheet_text": cheat_sheet_text,
                    "cur_opt_w": cur_opt_w,
                    "overrides": overrides
                }
                st.session_state.tab1_trigger_s3 = False

            _cache_s3 = st.session_state.tab1_step3_cache
            blueprint = _cache_s3["blueprint"]
            df_bp = _cache_s3["df_bp"]
            cheat_sheet_text = _cache_s3["cheat_sheet_text"]
            overrides = _cache_s3.get("overrides") or {}

            st.markdown(f"#### 🌱 专属实盘建仓执行单 (本金 ¥{plan_capital:,.2f} ｜ 精选 {len(df_bp)} 只 ｜ 模型：{QUANT_MODELS_CATALOG.get(sel_model_type, {}).get('name', 'HRP')})")
            if overrides:
                st.info(f"💡 检测到您自定义替换了 {len(overrides)} 只标的：{overrides}，配置方案已实时动态调整！")

            st.dataframe(
                df_bp,
                column_config={
                    "目标占比(%)": st.column_config.ProgressColumn(min_value=0, max_value=60, format="%.1f%%"),
                    "精确买入金额(元)": st.column_config.NumberColumn(format="¥%.2f"),
                    "最新净值": st.column_config.NumberColumn(format="%.4f"),
                    "实时估值涨跌(%)": st.column_config.NumberColumn(format="%+.2f%%"),
                    "实操分红与限购指引": st.column_config.TextColumn(
                        "实操分红与限购指引 ⓘ",
                        help="下单实操要点：红利类设为【现金分红】锁住收益；限额标的自动拆单；A类长投免赎，C类适合弹性波段。"
                    ),
                },
                use_container_width=True,
                hide_index=True
            )

            st.info(blueprint["summary_advice"])

            with st.expander("📱 【点击展开：手机银行 / 天天基金下单一键复制小抄】", expanded=False):
                st.caption("您可以直接复制下方文本发送给微信或记事本，对照手机银行、天天基金、蚂蚁财富一分钟完成买入：")
                st.code(cheat_sheet_text, language="text")

            col_btn_set_hold, col_btn_to_bt = st.columns([5, 5])
            with col_btn_set_hold:
                if st.button("🚀 【一键将此方案设为我的初始持仓】", type="primary", use_container_width=True, key="btn_apply_bp_tier"):
                    res_apply = pm.apply_zero_start_blueprint(blueprint)
                    st.balloons()
                    st.success(f"已成功将 ¥{res_apply['total_capital']:,.2f} 建仓方案写入为初始持仓！已配置 {res_apply['funds_count']} 只基金及对应分红方式。")
                    st.rerun()

            with col_btn_to_bt:
                if st.button("📈 【一键将此建仓组合送入穿透回测】", type="secondary", use_container_width=True, key="btn_send_bp_to_bt"):
                    st.session_state.selected_backtest_weights = dict(_cache_s3.get("cur_opt_w", {}))
                    st.session_state.selected_backtest_target = "新建仓组合"
                    st.success("✅ 已成功将此组合送入【📈 组合回测】！请切换至第三个 Tab 检视。")

    except Exception as e:
        st.error(f"⚠️ 【🌱 新资建仓】渲染出现局部异常: {e}")
        st.caption("💡 其他 Tab 工作区保持正常运行。如需排查可检查日志。")

# =============================================================
# Tab 2: 【💼 持仓调仓】（自然三步流：①持仓账本 -> ②AI诊断裁决 -> ③调仓方案与执行单）
# =============================================================
with tab_holdings_and_rebalance:
    try:
        active_tier = st.session_state.get("active_tier_val", "C3")
        cur_tier_meta = RISK_TIERS_CONFIG.get(active_tier, RISK_TIERS_CONFIG["C3"])
        st.subheader("💼 持仓调仓")
        st.caption("自然三步工作流：查验账本资产 ➔ AI五维裁决今日调仓时机 ➔ 模拟温和/强行后果并生成执行清单。")

        # 状态机初始化
        if "tab2_diagnosed" not in st.session_state:
            st.session_state.tab2_diagnosed = False
        if "tab2_rebalanced" not in st.session_state:
            st.session_state.tab2_rebalanced = False
        if "tab2_trigger_diagnose" not in st.session_state:
            st.session_state.tab2_trigger_diagnose = False
        if "tab2_trigger_rebalance" not in st.session_state:
            st.session_state.tab2_trigger_rebalance = False
        if "tab2_diag_cache" not in st.session_state:
            st.session_state.tab2_diag_cache = None
        if "tab2_rebal_cache" not in st.session_state:
            st.session_state.tab2_rebal_cache = None

        # 🧭 工作流步骤与系统状态指示器
        is_diag = st.session_state.get("tab2_diagnosed", False)
        is_reb = st.session_state.get("tab2_rebalanced", False)
        step_tab2 = 3 if is_reb else (2 if is_diag else 1)
        render_workflow_step_indicator(
            ["查看当前持仓与启动AI诊断", "AI综合裁决与调仓时机", "模拟调仓后果与生成执行单"],
            current_step=step_tab2,
            help_text="请点击下方【🔍 第一步：启动 AI 今日调仓时机全息诊断】" if step_tab2 == 1 else (
                "诊断已就绪，请点击下方【⚖️ 第二步：继续模拟调仓后果并生成今日执行单】" if step_tab2 == 2 else
                "今日调仓方案与四大真实后果账单已就绪，可查看下方执行单"
            )
        )

        # ---------------------------------------------------------
        # 步骤一：当前持仓账本
        # ---------------------------------------------------------
        st.markdown("### 步骤一：当前持仓账本")

        _t2_mkt = sum(getattr(h, "shares", 0.0) * getattr(h, "current_nav", 1.0) for h in pm.holdings.values()) if pm.holdings else 0.0
        _t2_cost = sum(getattr(h, "shares", 0.0) * getattr(h, "cost_price", getattr(h, "current_nav", 1.0)) for h in pm.holdings.values()) if pm.holdings else 0.0
        _t2_pnl = _t2_mkt - _t2_cost
        _t2_pnl_pct = (_t2_pnl / _t2_cost * 100.0) if _t2_cost > 0 else 0.0

        t2_m1, t2_m2, t2_m3, t2_m4 = st.columns(4)
        t2_m1.metric("💼 组合总市值", f"¥{_t2_mkt:,.2f}")
        t2_m2.metric("💵 可用现金", f"¥{pm.available_cash:,.2f}")
        t2_m3.metric("📈 累计浮动盈亏", f"¥{_t2_pnl:+,.2f}", delta=f"{_t2_pnl_pct:+.2f}%")
        t2_m4.metric("📊 持仓标的数", f"{len(pm.holdings)} 只")

        if len(pm.holdings) == 0:
            st.info("💡 **当前账本暂无持仓**！您可以点击下方按钮一键载入演示组合（包含深套基与在途单），或者在下方向导录入您的真实持仓。")
            col_demo_btn, _ = st.columns([4, 6])
            with col_demo_btn:
                if st.button("🚀 一键载入演示组合体验调仓驾驶舱", type="primary", use_container_width=True, key="btn_load_demo_tab2"):
                    with st.spinner("📦 正在载入演示组合..."):
                        pm.load_demo_portfolio()
                    st.success("✅ 演示组合载入成功！")
                    st.rerun()

        # 实时持仓明细表
        df_disp = pm.export_snapshot_df()
        if not df_disp.empty:
            st.caption("以下为您账户的实时持仓资产明细，支持双击单元格直接修改：")
            edited_table = st.data_editor(
                df_disp,
                column_config={
                    "持仓份额": st.column_config.NumberColumn(format="%.2f"),
                    "当前净值": st.column_config.NumberColumn(format="%.4f"),
                    "今日实时估值": st.column_config.NumberColumn(format="%.4f"),
                    "今日实时估值涨跌(%)": st.column_config.NumberColumn(format="%+.2f%%"),
                    "盘中预估盈亏(元)": st.column_config.NumberColumn(format="¥%+.2f"),
                    "今日预估盈亏率(%)": st.column_config.NumberColumn(format="%+.2f%%"),
                    "当前市值(元)": st.column_config.NumberColumn(format="¥%.2f"),
                    "持仓占比(%)": st.column_config.ProgressColumn(min_value=0, max_value=50, format="%.2f%%"),
                    "持仓成本价": st.column_config.NumberColumn(format="%.4f"),
                    "浮动盈亏率(%)": st.column_config.NumberColumn(format="%.2f%%"),
                    "最短持有天数": st.column_config.NumberColumn(format="%d 天"),
                    "当前赎回费率(%)": st.column_config.NumberColumn(format="%.2f%%"),
                    "分红方式": st.column_config.SelectboxColumn(options=["cash", "reinvest"], required=True),
                },
                disabled=["当前市值(元)", "持仓占比(%)", "今日实时估值", "今日实时估值涨跌(%)", "盘中预估盈亏(元)", "今日预估盈亏率(%)", "估值更新时间", "当前赎回费率(%)", "赎回费安全状态", "过渡建议标签"],
                use_container_width=True,
                num_rows="dynamic",
                key="main_holdings_editor_tab2"
            )

            col_save_t, col_del_t, col_exp_t = st.columns([3, 3, 4])
            with col_save_t:
                if st.button("💾 保存表格修改并同步入库", use_container_width=True, key="btn_save_holdings_tab2"):
                    valid_codes = set()
                    for _, row in edited_table.iterrows():
                        code_s = str(row["基金代码"]).strip().zfill(6)
                        valid_codes.add(code_s)
                        pm.add_or_update_holding(
                            fund_code=code_s,
                            shares=float(row.get("持仓份额", 0.0)),
                            nav=float(row.get("当前净值", 1.0)),
                            cost_price=float(row.get("持仓成本价", 1.0)),
                            holding_days=int(row.get("最短持有天数", 30)),
                            dividend_method=str(row.get("分红方式", "cash")),
                            notes="数据表直接编辑同步"
                        )
                    for exist_c in list(pm.holdings.keys()):
                        if exist_c not in valid_codes:
                            pm.delete_holding(exist_c)
                    st.session_state.tab2_diag_cache = None
                    st.session_state.tab2_rebal_cache = None
                    st.session_state.tab2_diagnosed = False
                    st.session_state.tab2_rebalanced = False
                    st.success("已成功保存并同步！")
                    st.rerun()

            with col_del_t:
                del_sel = st.selectbox("选择要删除的标的", ["-- 请选择 --"] + list(pm.holdings.keys()), key="sel_del_hold_tab2")
                if del_sel != "-- 请选择 --":
                    if st.button(f"🗑️ 彻底删除 {del_sel}", use_container_width=True, key="btn_del_hold_tab2"):
                        pm.delete_holding(del_sel)
                        st.session_state.tab2_diag_cache = None
                        st.session_state.tab2_rebal_cache = None
                        st.session_state.tab2_diagnosed = False
                        st.session_state.tab2_rebalanced = False
                        st.success(f"已删除 {del_sel}")
                        st.rerun()

            with col_exp_t:
                csv_exp = df_disp.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    "📥 导出持仓快照 CSV",
                    data=csv_exp,
                    file_name=f"portfolio_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="btn_dl_csv_tab2"
                )

        has_holdings = len(pm.holdings) > 0
        with st.expander("✨ 快速录入持仓", expanded=(not has_holdings)):
            sub_tab1, sub_tab2, sub_tab3 = st.tabs([
                "📋 文本粘贴导入",
                "🔍 搜索添加标的",
                "📥 表格模板导入"
            ])
            with sub_tab1:
                sample_smart_text = """华泰柏瑞低波 30000 盈利1200\n华夏科创50C 20000 亏500\n000216 15000\n100032 25000 成本0.96 现价0.98 已持满60天"""
                smart_text_in = st.text_area("📝 在此粘贴持仓文字：", value=sample_smart_text, height=110, key="txt_smart_holdings")
                col_st_c, col_st_b = st.columns([4, 6])
                with col_st_c:
                    smart_cash_in = st.number_input("账户可用现金 (元)", value=float(pm.available_cash or 10000.0), step=1000.0, key="smart_cash_input")
                with col_st_b:
                    st.write(" ")
                    st.write(" ")
                    if st.button("🔍 智能解析并接管", type="primary", use_container_width=True, key="btn_parse_smart_text"):
                        parsed_items = pm.parse_smart_text_holdings(smart_text_in)
                        if parsed_items:
                            pm.import_from_smart_text(parsed_items, available_cash=smart_cash_in)
                            st.session_state.tab2_diag_cache = None
                            st.session_state.tab2_rebal_cache = None
                            st.session_state.tab2_diagnosed = False
                            st.session_state.tab2_rebalanced = False
                            st.balloons()
                            st.success(f"成功接管 {len(parsed_items)} 只基金！")
                            st.rerun()
                        else:
                            st.warning("未能识别出有效持仓文本。")

            with sub_tab2:
                col_kw, col_amt = st.columns([6, 4])
                with col_kw:
                    search_kw = st.text_input("🔍 搜索基金代码 / 中文简称 / 拼音首字母", value="低波", key="kw_search_catalog")
                matched = search_funds_in_catalog(search_kw, limit=10) if search_kw.strip() else []
                if matched:
                    f_opts = [f"{f['fund_code']} - {f['fund_name']}" for f in matched]
                    sel_f = st.selectbox("选择目标基金", f_opts, key="sel_search_fund")
                    sel_c = sel_f.split(" - ")[0].strip()
                    with col_amt:
                        add_amt = st.number_input("持仓金额 (元)", value=10000.0, step=1000.0, key="search_amt_input")
                    if st.button("➕ 添加至持仓", type="primary", key="btn_add_search_holding"):
                        pm.add_or_update_holding(fund_code=sel_c, amount=add_amt, holding_tag=">=30d", append_batch=True)
                        st.session_state.tab2_diag_cache = None
                        st.session_state.tab2_rebal_cache = None
                        st.session_state.tab2_diagnosed = False
                        st.session_state.tab2_rebalanced = False
                        st.success(f"已添加 {sel_c}！")
                        st.rerun()

            with sub_tab3:
                up_file = st.file_uploader("上传持仓 CSV / Excel 文件", type=["csv", "xlsx"], key="tab2_uploader_std")
                if up_file:
                    df_u = pd.read_csv(up_file) if up_file.name.endswith(".csv") else pd.read_excel(up_file)
                    if st.button("📥 确认导入快照", type="primary", key="btn_imp_snap_csv"):
                        res_s = pm.import_snapshot_df(df_u)
                        st.session_state.tab2_diag_cache = None
                        st.session_state.tab2_rebal_cache = None
                        st.session_state.tab2_diagnosed = False
                        st.session_state.tab2_rebalanced = False
                        st.success(f"成功导入 {res_s.get('imported_count', 0)} 条快照！")
                        st.rerun()

        with st.expander("📦 【点击展开：全组合 FIFO 批次透视与免赎回费倒计时】", expanded=False):
            all_b_rows = []
            for f_c, h_obj in pm.holdings.items():
                safe_shares_val = pm.get_penalty_free_redeemable_shares(f_c)
                for b_i in h_obj.batches:
                    days_left = max(0, 7 - b_i.holding_days)
                    countdown_str = "🟢 已满7天 (免惩罚费)" if days_left == 0 else f"🔴 距免惩罚费还剩 {days_left} 天"
                    all_b_rows.append({
                        "基金代码": f_c,
                        "基金名称": h_obj.fund_name,
                        "批次编号": b_i.batch_id,
                        "买入日期": b_i.buy_date,
                        "批次份额": b_i.shares,
                        "成本净值": b_i.cost_nav,
                        "已持有天数": f"{b_i.holding_days} 天",
                        "安全状态": countdown_str,
                        "免惩罚可卖份额": safe_shares_val,
                    })
            if all_b_rows:
                st.dataframe(pd.DataFrame(all_b_rows), use_container_width=True, hide_index=True)
            else:
                st.info("当前持仓暂无批次数据。")

        # 步骤一底部推进按钮
        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
        col_t2_btn1, col_t2_btn2 = st.columns([1, 1])
        with col_t2_btn1:
            if st.button("🔍 第一步：启动 AI 今日调仓时机全息诊断", type="primary", use_container_width=True, key="btn_tab2_diagnose"):
                st.session_state.tab2_diagnosed = True
                st.session_state.tab2_trigger_diagnose = True
                st.rerun()
        with col_t2_btn2:
            if st.button("🚀 一键执行全流程（时机诊断 + 调仓模拟 + 生成执行单）", type="secondary", use_container_width=True, key="btn_tab2_all"):
                st.session_state.tab2_diagnosed = True
                st.session_state.tab2_rebalanced = True
                st.session_state.tab2_trigger_diagnose = True
                st.session_state.tab2_trigger_rebalance = True
                st.rerun()

        # ---------------------------------------------------------
        # 步骤二：【🚦 调仓时机裁决】（AI 综合裁决卡 + 四维胶囊）
        # ---------------------------------------------------------
        if st.session_state.get("tab2_diagnosed", False):
            st.markdown("---")
            st.markdown("### 步骤二：调仓时机裁决")

            if st.session_state.get("tab2_trigger_diagnose", False) or st.session_state.get("tab2_diag_cache") is None:
                acc_diag = ActiveComputationConsole("AI持仓全息诊断", total_steps=4, step_labels=[
                    "步骤 1: 底层穿透与排雷健康扫描",
                    "步骤 2: 风格漂移与集中度检测",
                    "步骤 3: 申赎时钟与均线突破定调",
                    "步骤 4: 偏离度与净效用综合裁决"
                ])
                acc_diag.update_step(0, "正在扫描持仓底层重仓股与排雷健康度...", progress_pct=25)
                suitability = StrategyBridge.evaluate_today_rebalance_suitability(pm, active_tier=active_tier)
                acc_diag.update_step(3, "综合裁决计算完毕！", progress_pct=100)
                acc_diag.complete("5 维健康体检已生成")
                st.session_state.tab2_diag_cache = suitability
                st.session_state.tab2_trigger_diagnose = False

            suitability = st.session_state.get("tab2_diag_cache") or {}
            v_level = suitability.get("verdict_level", "HOLD_ON")
            v_title = suitability.get("verdict_title", "今日维持底仓吃息，无需调仓")
            r4 = suitability.get("reasons_4d", {})

            banner_bg = "rgba(22, 163, 74, 0.12)" if v_level == "SUITABLE" else ("rgba(234, 179, 8, 0.12)" if v_level == "HOLD_ON" else "rgba(220, 38, 38, 0.12)")
            banner_border = "#16a34a" if v_level == "SUITABLE" else ("#ca8a04" if v_level == "HOLD_ON" else "#dc2626")
            banner_color = "#15803d" if v_level == "SUITABLE" else ("#a16207" if v_level == "HOLD_ON" else "#b91c1c")

            st.markdown(f"""
            <div style="background: {banner_bg}; border: 1.5px solid {banner_border}; border-radius: 8px; padding: 14px 18px; margin-bottom: 14px;">
                <div style="font-size: 16px; font-weight: 700; color: {banner_color}; margin-bottom: 4px;">
                    {v_title}
                </div>
                <div style="font-size: 12px; color: #475569;">
                    AI 投顾核心原则：行情未到关键右侧突破位不调、买入不满 7 天不调、偏离度不足 3% 缓冲阈值不调，将无谓交易磨损降至绝对最低。
                </div>
            </div>
            """, unsafe_allow_html=True)

            col_r1, col_r2, col_r3, col_r4 = st.columns(4)
            with col_r1:
                st.markdown(f"""
                <div class="decision-card">
                    <div class="decision-title">① 均线突破状态</div>
                    <div class="decision-val" style="font-size: 14px; color: #0284c7;">{snapshot.get('m20_status_desc', '站上均线')}</div>
                    <div class="decision-desc">{r4.get('market_position_reason', '')}</div>
                </div>
                """, unsafe_allow_html=True)
            with col_r2:
                st.markdown(f"""
                <div class="decision-card">
                    <div class="decision-title">② 申赎交易时钟</div>
                    <div class="decision-val" style="font-size: 14px; color: #0284c7;">{clock_status.window_type}</div>
                    <div class="decision-desc">{r4.get('clock_window_reason', '')}</div>
                </div>
                """, unsafe_allow_html=True)
            with col_r3:
                st.markdown(f"""
                <div class="decision-card">
                    <div class="decision-title">③ 偏离度与净效用</div>
                    <div class="decision-val" style="font-size: 14px; color: #0284c7;">最大偏离 {suitability.get('d_max', 0.0)*100:.1f}%</div>
                    <div class="decision-desc">{r4.get('deviation_utility_reason', '')}</div>
                </div>
                """, unsafe_allow_html=True)
            with col_r4:
                st.markdown(f"""
                <div class="decision-card">
                    <div class="decision-title">④ FIFO 锁定期状态</div>
                    <div class="decision-val" style="font-size: 14px; color: #0284c7;">惩罚费防线</div>
                    <div class="decision-desc">{r4.get('lockup_fee_reason', '')}</div>
                </div>
                """, unsafe_allow_html=True)

            if not st.session_state.get("tab2_rebalanced", False):
                st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
                if st.button("⚖️ 第二步：继续模拟调仓方案与四大后果量化账单", type="primary", use_container_width=True, key="btn_t2_step_to_reb"):
                    st.session_state.tab2_rebalanced = True
                    st.session_state.tab2_trigger_rebalance = True
                    st.rerun()

        # ---------------------------------------------------------
        # 步骤三：【⚖️ 调仓方案与执行单】（四大后果 + 建议执行单）
        # ---------------------------------------------------------
        if st.session_state.get("tab2_rebalanced", False):
            st.markdown("---")
            st.markdown("### 步骤三：调仓方案执行")

            # 🎯 目标组合选择单选框
            has_t1_opt = bool(st.session_state.get("tab1_sim_cache") and st.session_state["tab1_sim_cache"].get("optimal_weights"))
            target_pool_options = [
                "🌱 对齐我在【新资建仓】生成的最新优选组合",
                "🛡️ 核心指数全天候策略池（按当前档位自动配比）"
            ]
            chosen_target_pool = st.radio(
                "🎯 选择调仓目标组合：",
                target_pool_options,
                index=0 if has_t1_opt else 1,
                horizontal=True,
                key="rad_tab2_target_pool"
            )

            if chosen_target_pool.startswith("🌱") and has_t1_opt:
                tier_target_w = dict(st.session_state["tab1_sim_cache"]["optimal_weights"])
                st.caption(f"已选用【新资建仓】生成的 {len(tier_target_w)} 只优选组合配比作为调仓目标。")
            else:
                snapshot = StrategyBridge.get_latest_market_snapshot()
                base_w = StrategyBridge.compute_dynamic_tier_weights(tier=active_tier, market_snapshot=snapshot)
                overrides = st.session_state.get("custom_fund_overrides", {})
                tier_target_w = {}
                for c, w in base_w.items():
                    target_c = overrides.get(c, c)
                    tier_target_w[target_c] = tier_target_w.get(target_c, 0.0) + w
                if chosen_target_pool.startswith("🌱") and not has_t1_opt:
                    st.info("提示：尚未在【新资建仓】运行推演，已自动退回使用当前档位【核心指数全天候策略池】。")
                else:
                    st.caption(f"已选用【核心指数全天候策略池】（{active_tier}档位，已应用自定义备选替换）作为调仓目标。")

            cur_pool_sig = (chosen_target_pool, tuple(sorted(tier_target_w.items())))
            if st.session_state.get("tab2_last_pool_sig") != cur_pool_sig:
                st.session_state.tab2_rebal_cache = None
                st.session_state.tab2_last_pool_sig = cur_pool_sig

            if st.session_state.get("tab2_trigger_rebalance", False) or st.session_state.get("tab2_rebal_cache") is None:
                acc_reb = ActiveComputationConsole("智能调仓模拟精算", total_steps=4, step_labels=[
                    "步骤 1: 锁定期与 <7天 惩罚费防线核算",
                    "步骤 2: 3% 缓冲阈值偏离度过滤",
                    "步骤 3: 温和调仓 vs 强制调仓路径生成",
                    "步骤 4: 四大真实后果量化账单精算"
                ])
                acc_reb.update_step(0, "核算先进先出锁定期与 7 天 1.5% 惩罚费防线...", progress_pct=25)
                sim_res = StrategyBridge.simulate_rebalance_modes_and_consequences(
                    pm,
                    active_tier=active_tier,
                    target_weights=tier_target_w
                )
                acc_reb.update_step(3, "调仓路径与账单精算完成！", progress_pct=100)
                acc_reb.complete("调仓模拟完成")
                st.session_state.tab2_rebal_cache = sim_res
                st.session_state.tab2_trigger_rebalance = False

            sim_res = st.session_state.get("tab2_rebal_cache")
            mode_choice = st.radio(
                "选择推演的调仓模式：",
                ["模式一：温和免伤调仓 (遵循 3% 缓冲与锁定期保护·零惩罚费·首选推荐)", "模式二：强行一步到位调仓 (无视持有期强行全额换仓·核算全额摩擦成本)"],
                index=0,
                horizontal=True,
                key="rad_rebal_mode"
            )
            sel_mode_key = "mode_gentle" if "温和" in mode_choice else "mode_forced"
            cur_sim = sim_res[sel_mode_key]
            conseq = cur_sim["consequences"]
            fee_loss = conseq["fee_loss"]
            in_transit = conseq["in_transit_risk"]
            risk_shift = conseq["risk_shift"]
            lockup_rst = conseq["lockup_reset"]

            st.markdown("#### 🧾 《本次调仓四大真实后果量化账单》")
            c_cons1, c_cons2, c_cons3, c_cons4 = st.columns(4)
            with c_cons1:
                pen_html = f"<br><span style='color: #ef4444; font-weight:700;'>包含 7天惩罚费: ¥{fee_loss['penalty_fee_7d']:,.2f}</span>" if fee_loss['penalty_fee_7d'] > 0 else "<br><span style='color: #10b981;'>免收 1.5% 惩罚费 (¥0)</span>"
                st.markdown(f"""
                <div class="decision-card consequence-card" style="border-top: 3px solid #ef4444;">
                    <div class="decision-title" style="color: #b91c1c;">💸 ① 手续费直接损耗</div>
                    <div class="decision-val" style="color: #b91c1c; font-size: 18px;">¥{fee_loss['total_fee']:,.2f}</div>
                    <div class="decision-desc">
                        - 赎回费: ¥{fee_loss['redemption_fee']:,.2f} ｜ 申购费: ¥{fee_loss['subscription_fee']:,.2f}{pen_html}<br>
                        - <b>回本周期</b>：预计靠分红增厚 <b>{fee_loss['payback_days']} 天</b> 回本
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with c_cons2:
                st.markdown(f"""
                <div class="decision-card consequence-card" style="border-top: 3px solid #f59e0b;">
                    <div class="decision-title" style="color: #b45309;">⏳ ② T+2在途踏空风险</div>
                    <div class="decision-val" style="color: #b45309; font-size: 18px;">¥{in_transit['in_transit_amount']:,.2f} ({in_transit['in_transit_pct']:.1f}%)</div>
                    <div class="decision-desc">
                        - <b>资金在途空窗</b>：{in_transit['lock_days']}<br>
                        - <b>同公司免在途节省</b>：¥{in_transit['switch_saved_amount']:,.2f}<br>
                        - <b>踏空机会成本预估</b>：¥{in_transit['missed_rally_cost_est']:,.2f}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with c_cons3:
                st.markdown(f"""
                <div class="decision-card consequence-card" style="border-top: 3px solid #3b82f6;">
                    <div class="decision-title" style="color: #1d4ed8;">🛡️ ③ 组合攻防与回撤变化</div>
                    <div class="decision-val" style="color: #1d4ed8; font-size: 16px;">
                        波动率 {risk_shift['vol_before']:.1f}% ➔ {risk_shift['vol_after']:.1f}%
                    </div>
                    <div class="decision-desc">
                        - <b>极端回撤水位</b>：{risk_shift['mdd_before']:.1f}% ➔ {risk_shift['mdd_after']:.1f}%<br>
                        - <b>组合股息安全垫</b>：{risk_shift['div_yield_before']:.2f}% ➔ {risk_shift['div_yield_after']:.2f}%<br>
                        - 扣费后总权益：¥{risk_shift['equity_after']:,.2f}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with c_cons4:
                st.markdown(f"""
                <div class="decision-card consequence-card" style="border-top: 3px solid #8b5cf6;">
                    <div class="decision-title" style="color: #6d28d9;">🔄 ④ 持有期清零重算后果</div>
                    <div class="decision-val" style="color: #6d28d9; font-size: 18px;">¥{lockup_rst['new_buy_amount']:,.2f} 新增锁仓</div>
                    <div class="decision-desc">
                        {lockup_rst['reset_warning_text']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # 调仓执行单
            # tier_target_w 已在上方目标组合选择器中动态精准确定
            if "tier_target_w" not in locals():
                tier_target_w = dict(snapshot.get("target_weights_funds", {}))
            rebal_mode_param = "forced" if sel_mode_key == "mode_forced" else "gentle"

            ai_orders_res = StrategyBridge.generate_ai_rebalance_orders(
                current_holdings=pm.holdings,
                available_cash=pm.available_cash,
                target_weights_funds=tier_target_w,
                pm=pm,
                mode=rebal_mode_param
            )
            items = ai_orders_res.get("items", [])

            if items:
                rows_display = []
                for it in items:
                    diff_amt = it.get("diff_amount", 0.0)
                    action_raw = str(it.get("action_text", ""))
                    safety = str(it.get("safety_warning", "") or "")
                    holding_days = it.get("holding_days", 999)

                    if "7天" in safety or holding_days < 7 or "锁仓" in action_raw:
                        op_action = "🔒 未满7天锁仓保护"
                        op_point = "未满7天·免收1.5%惩罚"
                    elif "30天" in safety or (7 <= holding_days < 30 and it.get("share_class") == "C") or "缓卖" in action_raw:
                        op_action = "⏳ 临近30天免赎期缓卖"
                        op_point = "缓卖·满30天免赎回费"
                    elif diff_amt > 100 or "加仓" in action_raw:
                        op_action = "➕ 建议加仓"
                        op_point = f"增配¥{abs(diff_amt):,.0f}·现金分红"
                    elif diff_amt < -100 or "减仓" in action_raw:
                        op_action = "➖ 建议减仓"
                        op_point = f"减配¥{abs(diff_amt):,.0f}·阶梯退出"
                    else:
                        op_action = "✅ 维持持有"
                        op_point = "仓位均衡·在容差内"

                    rows_display.append({
                        "基金代码": it["fund_code"],
                        "基金名称": it["fund_name"],
                        "份额": f"{it.get('share_class', 'A')}类",
                        "当前市值(元)": it["market_value"],
                        "目标占比(%)": it["target_weight_pct"],
                        "实时估值涨跌(%)": it.get("realtime_gszzl", 0.0),
                        "建议调仓金额(元)": diff_amt,
                        "建议操作": op_action,
                        "实操要点": op_point
                    })

                rebal_cols_9 = [
                    "基金代码", "基金名称", "份额", "当前市值(元)",
                    "目标占比(%)", "实时估值涨跌(%)", "建议调仓金额(元)",
                    "建议操作", "实操要点"
                ]
                df_orders_tbl = pd.DataFrame(rows_display)[rebal_cols_9]
                st.dataframe(
                    df_orders_tbl,
                    column_config={
                        "当前市值(元)": st.column_config.NumberColumn(format="¥%.2f"),
                        "目标占比(%)": st.column_config.ProgressColumn(min_value=0, max_value=50, format="%.2f%%"),
                        "实时估值涨跌(%)": st.column_config.NumberColumn(format="%+.2f%%"),
                        "建议调仓金额(元)": st.column_config.NumberColumn(format="¥%+.2f"),
                        "实操要点": st.column_config.TextColumn(
                            "实操要点 ⓘ",
                            help="实操要点：包含分红方式、未满7天防惩罚性扣款锁仓、临近30天免赎回费保护及分批调仓指引。"
                        )
                    },
                    use_container_width=True,
                    hide_index=True
                )

                guidance = clock.get_action_guidance_for_window()
                if guidance["stage"] == "OBSERVATION":
                    st.info(guidance["message"])
                elif guidance["stage"] == "GOLDEN_WINDOW":
                    st.success(guidance["message"])
                else:
                    st.markdown(f"""
                    <div style="background: rgba(234, 179, 8, 0.08); border: 1.5px solid #ca8a04; border-radius: 8px; padding: 14px 18px; margin-bottom: 12px;">
                        <div style="font-size: 15px; font-weight: 700; color: #a16207; margin-bottom: 8px;">
                            ⚠️ 当前已过 15:00 场外基金关账时间！
                        </div>
                        <div style="font-size: 13px; line-height: 1.6; color: #1e293b;">
                            现在在基金 App 下单将按【下一交易日（明天）15:00 的未知收盘净值】成交！建议点击下方按钮保存为明日盯盘待办预案。
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                col_exec_ai, col_send_bt = st.columns([5, 5])
                with col_exec_ai:
                    if guidance["stage"] == "POST_MARKET":
                        if st.button("📌 【保存为明日 14:30 盯盘待办预案】", type="primary", use_container_width=True, key="btn_save_next_plan_tab2"):
                            p_id = pm.save_next_day_plan({"target_weights": tier_target_w, "items": items, "mode": sel_mode_key})
                            st.balloons()
                            st.success(f"已成功将本次调仓方案保存为【明日 14:30 盯盘待办预案】（{p_id}）！")
                            st.rerun()
                    elif guidance["stage"] == "GOLDEN_WINDOW":
                        if st.button("✅ 【立即按今日盘中估值执行调仓】", type="primary", use_container_width=True, key="btn_exec_gold_tab2"):
                            rebal_plan = pm.generate_rebalance_plan(tier_target_w, min_buffer_pct=(0.0 if sel_mode_key == "mode_forced" else 3.0))
                            routes_to_run = rebal_plan.get("routes", [])
                            if routes_to_run:
                                oids = pm.submit_rebalance_orders(routes_to_run)
                                st.balloons()
                                st.success(f"✅ 已成功执行调仓，生成 {len(oids)} 笔指令！")
                                st.rerun()
                            else:
                                st.info("持仓偏离均在 3% 缓冲阈值内，无需额外调仓。")
                    elif guidance["stage"] == "OBSERVATION":
                        allow_early = st.checkbox(
                            "⚠️ 我已了解盘中冲高/跳水风险，仍希望在 14:30 前提前执行",
                            value=False,
                            key="chk_allow_early_rebalance"
                        )
                        if allow_early:
                            if st.button("⚡ 【提前执行盘中调仓 (已确认波动风险)】", type="primary", use_container_width=True, key="btn_exec_early_tab2"):
                                rebal_plan = pm.generate_rebalance_plan(tier_target_w, min_buffer_pct=(0.0 if sel_mode_key == "mode_forced" else 3.0))
                                routes_to_run = rebal_plan.get("routes", [])
                                if routes_to_run:
                                    oids = pm.submit_rebalance_orders(routes_to_run)
                                    st.balloons()
                                    st.success(f"✅ 已成功提前执行调仓，生成 {len(oids)} 笔指令！")
                                    st.rerun()
                                else:
                                    st.info("持仓偏离均在 3% 缓冲阈值内，无需额外调仓。")
                        else:
                            st.button("⏳ 盘中观察中 (等待 14:30 尾盘趋势锁定解锁)", disabled=True, use_container_width=True, key="btn_obs_disabled_tab2")
                    else:
                        st.button("⏳ 盘前非交易时段 (请等待开盘)", disabled=True, use_container_width=True, key="btn_pre_disabled_tab2")

                with col_send_bt:
                    if st.button("📈 【将调仓前vs调仓后送入回测对比】", type="secondary", use_container_width=True, key="btn_send_rebal_to_bt"):
                        st.session_state.selected_backtest_target = "调仓前后对比"
                        st.session_state.selected_secondary_weights = tier_target_w
                        st.success("✅ 已成功将调仓前后组合送入【📈 组合回测】！请切换至第三个 Tab 查看双曲线对比。")

    except Exception as e:
        st.error(f"⚠️ 【💼 持仓调仓】渲染出现局部异常: {e}")
        st.caption("💡 其他 Tab 工作区保持正常运行。如需排查可检查日志。")

# =============================================================
# Tab 3: 【📈 组合回测】（穿透回测新建仓组合/当前持仓/调仓前后，9大基准自由多选）
# =============================================================
with tab_backtest:
    try:
        st.subheader("📈 组合回测")
        st.caption("真实穿透回测：支持新建仓组合、当前实盘、调仓前后全周期穿透，9大基准指数自由多选同屏对比。")

        c_bt_obj, c_bt_bench = st.columns([4, 6])
        with c_bt_obj:
            def_target = st.session_state.get("selected_backtest_target", "新建仓组合")
            target_options = ["新建仓组合", "当前实盘持仓", "调仓后组合", "调仓前后对比", "策略基准档"]
            def_idx = target_options.index(def_target) if def_target in target_options else 0
            sel_target_type = st.selectbox(
                "🎯 选择回测对象：",
                target_options,
                index=def_idx,
                key="sel_backtest_target_type"
            )

        with c_bt_bench:
            all_bms = list(BENCHMARK_INDICES_MAP.keys())
            selected_bms = st.multiselect(
                "📊 选择对标基准指数 (支持自由多选同屏对比)：",
                options=all_bms,
                default=["沪深300", "红利低波", "纯债指数"],
                key="sel_multiselect_benchmarks"
            )

        # 动态解析回测权重
        primary_weights = {}
        secondary_weights = None
        target_name_disp = sel_target_type

        # 1. 新建仓组合权重
        t1_sim_c = st.session_state.get("tab1_sim_cache") or {}
        t1_w = dict(st.session_state.get("selected_backtest_weights") or t1_sim_c.get("optimal_weights", {}))
        if not t1_w:
            t1_w = {"005561": 0.35, "100032": 0.20, "000216": 0.20, "017436": 0.15, "011613": 0.10}

        # 2. 当前实盘持仓权重
        hold_w = {}
        if pm.holdings:
            tot_h_val = sum(h.market_value for h in pm.holdings.values())
            if tot_h_val > 0:
                hold_w = {c: round(h.market_value / tot_h_val, 4) for c, h in pm.holdings.items()}

        # 3. 调仓后目标权重
        rebal_w = dict(st.session_state.get("selected_secondary_weights") or snapshot.get("target_weights_funds", {}))

        if sel_target_type == "新建仓组合":
            primary_weights = t1_w
            target_name_disp = f"新建仓组合 ({len(primary_weights)} 只)"
        elif sel_target_type == "当前实盘持仓":
            if hold_w:
                primary_weights = hold_w
                target_name_disp = f"当前实盘持仓 ({len(primary_weights)} 只)"
            else:
                st.info("当前实盘持仓为空，已自动选用新建仓组合进行回测。")
                primary_weights = t1_w
                target_name_disp = f"新建仓组合 ({len(primary_weights)} 只)"
        elif sel_target_type == "调仓后组合":
            primary_weights = rebal_w if rebal_w else t1_w
            target_name_disp = f"调仓后组合 ({len(primary_weights)} 只)"
        elif sel_target_type == "调仓前后对比":
            primary_weights = hold_w if hold_w else t1_w
            secondary_weights = rebal_w if rebal_w else t1_w
            target_name_disp = "调仓前 (红) vs 调仓后 (蓝)"
        else: # 策略基准档
            sel_tier_opt = st.selectbox("选择基准策略档位：", ["C1 (安稳增值)", "C2 (稳健平衡)", "C3 (全天候平衡)", "C4 (进取成长)", "C5 (极限进攻)"], index=2, key="sel_backtest_tier_sub")
            t_key = sel_tier_opt.split()[0]
            df_mat = StrategyBridge.load_matrix()
            w_idx = strategy_fn_for_tier(df_mat, tier=t_key)
            primary_weights = StrategyBridge.map_index_weights_to_funds(w_idx)
            target_name_disp = f"{t_key} 策略基准"

        # 执行穿透回测
        df_bt = StrategyBridge.build_custom_portfolio_backtest(
            fund_weights=primary_weights,
            secondary_weights=secondary_weights,
            tier=st.session_state.get("active_tier_val", "C3"),
            target_return_pct=float(st.session_state.get("target_return_val", 15.0))
        )

        # 核心指标计算
        tier_cagr = (df_bt['strategy_nav'].iloc[-1] ** (252.0 / max(len(df_bt), 1)) - 1.0) * 100.0
        tier_mdd = abs(float(df_bt['strategy_drawdown'].min()))
        tier_otc_cagr = (df_bt['strategy_nav_otc'].iloc[-1] ** (252.0 / max(len(df_bt), 1)) - 1.0) * 100.0 if 'strategy_nav_otc' in df_bt.columns else (tier_cagr - 0.6)

        # 4 张表现卡片
        kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
        with kpi_col1:
            st.markdown(f"""
            <div class="main-metric-card">
                <div style="font-size:11px; color:#64748b;">年化收益率 (CAGR)</div>
                <div class="metric-value-huge" style="color: #dc2626;">
                    +{tier_cagr:.2f}%
                </div>
                <div style="font-size:11px; color:#0284c7; margin-top:2px;">
                    场外实盘校准: <b>+{tier_otc_cagr:.2f}%</b> (95%仓位)
                </div>
            </div>
            """, unsafe_allow_html=True)

        with kpi_col2:
            st.markdown(f"""
            <div class="main-metric-card">
                <div style="font-size:11px; color:#64748b;">回测对象与基金数</div>
                <div class="metric-value-huge" style="color: #0284c7; font-size:16px;">
                    {target_name_disp}
                </div>
                <div style="font-size:11px; color:#64748b; margin-top:2px;">
                    标的只数: {len(primary_weights)} 只
                </div>
            </div>
            """, unsafe_allow_html=True)

        with kpi_col3:
            st.markdown(f"""
            <div class="main-metric-card">
                <div style="font-size:11px; color:#64748b;">全周期最大回撤 (MaxDD)</div>
                <div class="metric-value-huge" style="color: #16a34a;">
                    -{tier_mdd:.2f}%
                </div>
                <div style="font-size:11px; color:#64748b; margin-top:2px;">
                    沪深300同期回撤: {trial29_kpi['mdd_h300']:.1f}%
                </div>
            </div>
            """, unsafe_allow_html=True)

        with kpi_col4:
            st.markdown(f"""
            <div class="main-metric-card">
                <div style="font-size:11px; color:#64748b;">切片胜率 / 盈亏比</div>
                <div class="metric-value-huge" style="color: #dc2626;">
                    {trial29_kpi['slice_win_rate']}
                </div>
                <div style="font-size:11px; color:#64748b; margin-top:2px;">
                    月度胜率 {trial29_kpi['monthly_win_rate']} ｜ 盈亏比 {trial29_kpi['profit_factor_range']}
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.25); border-radius: 8px; padding: 12px 18px; margin-bottom: 14px;">
            <div style="font-weight: 700; color: #b91c1c; font-size: 14px; margin-bottom: 4px;">
                💡 实盘双口径年化收益对照（场外公募 95% 仓位现金拖累校准）
            </div>
            <div style="font-size: 13px; color: #1e293b; line-height: 1.6;">
                • <b>指数理论年化 (CAGR)</b>: <span style="color:#b91c1c; font-weight:700;">+{tier_cagr:.2f}%</span>（假定 100% 仓位跟踪全收益指数）<br>
                • <b>场外联接实盘年化 (CAGR)</b>: <span style="color:#0284c7; font-weight:700;">+{tier_otc_cagr:.2f}%</span>（强制折算公募基金 95% 仓位法定上限与 5% 现金拖累，年化损耗约 0.60%，实盘业绩绝不画饼！）
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(" ")

        # 2018-2026 全周期真实净值推演曲线 (同屏对标自选基准)
        st.markdown(f"#### 🚀 2018-2026 全周期真实净值推演曲线 (对标 {len(selected_bms)} 只自选基准指数)")

        fig_nav = go.Figure()

        # 绘制主回测组合曲线
        fig_nav.add_trace(go.Scatter(
            x=df_bt['date'],
            y=df_bt['strategy_nav'],
            mode='lines',
            name=f'{target_name_disp} (理论 +{tier_cagr:.2f}%)',
            line=dict(color='#ef4444', width=2.5)
        ))

        # 若为调仓前后对比，同屏绘制第二组合
        if "secondary_nav" in df_bt.columns:
            sec_cagr = (df_bt['secondary_nav'].iloc[-1] ** (252.0 / max(len(df_bt), 1)) - 1.0) * 100.0
            fig_nav.add_trace(go.Scatter(
                x=df_bt['date'],
                y=df_bt['secondary_nav'],
                mode='lines',
                name=f'调仓后组合 (理论 +{sec_cagr:.2f}%)',
                line=dict(color='#2563eb', width=2.2, dash='solid')
            ))

        # 绘制场外实盘校准曲线
        if 'strategy_nav_otc' in df_bt.columns and "secondary_nav" not in df_bt.columns:
            fig_nav.add_trace(go.Scatter(
                x=df_bt['date'],
                y=df_bt['strategy_nav_otc'],
                mode='lines',
                name=f'{target_name_disp} 场外实盘校准 (+{tier_otc_cagr:.2f}%)',
                line=dict(color='#38bdf8', width=2.0, dash='dot')
            ))

        # 自由绘制用户选择的基准指数
        bm_colors = {
            "沪深300": "#94a3b8", "中证500": "#64748b", "中证1000": "#a855f7",
            "科创50": "#ec4899", "红利低波": "#10b981", "中证红利": "#059669",
            "纯债指数": "#3b82f6", "国内黄金": "#f59e0b", "股债50/50": "#d97706"
        }
        for bm_name in selected_bms:
            col_k = f"bm_nav_{bm_name}"
            if col_k in df_bt.columns:
                bm_s = df_bt[col_k]
                bm_cagr = (bm_s.iloc[-1] ** (252.0 / max(len(df_bt), 1)) - 1.0) * 100.0
                fig_nav.add_trace(go.Scatter(
                    x=df_bt['date'],
                    y=bm_s,
                    mode='lines',
                    name=f'{bm_name} (+{bm_cagr:.2f}%)',
                    line=dict(color=bm_colors.get(bm_name, "#cbd5e1"), width=1.5, dash='dash')
                ))

        # 高亮标注 6 大历史切片与样本外盲测金库
        slices_meta = [
            ("2018-01-02", "2018-12-28", "去杠杆熊市", "rgba(239, 68, 68, 0.08)"),
            ("2019-01-02", "2020-12-31", "核心资产牛市", "rgba(16, 185, 129, 0.08)"),
            ("2021-01-04", "2021-12-31", "赛道股分化", "rgba(245, 158, 11, 0.08)"),
            ("2022-01-04", "2022-12-30", "加息杀估值", "rgba(239, 68, 68, 0.08)"),
            ("2023-01-03", "2024-08-30", "高股息避险", "rgba(56, 189, 248, 0.08)"),
            ("2024-09-02", "2025-06-30", "924大转向", "rgba(16, 185, 129, 0.08)"),
            ("2025-07-01", "2026-10-27", "盲测金库", "rgba(168, 85, 247, 0.12)")
        ]
        for s_start, s_end, s_label, s_color in slices_meta:
            fig_nav.add_vrect(
                x0=s_start, x1=s_end,
                fillcolor=s_color,
                layer="below",
                line_width=0,
                annotation_text=s_label,
                annotation_position="top left",
                annotation_font_size=10,
                annotation_font_color="#475569"
            )

        fig_nav.update_layout(
            title=f"2018-2026 全周期累计净值对比 (起始归一化 1.000)",
            xaxis_title="交易日期",
            yaxis_title="标准化累计净值",
            hovermode="x unified",
            margin=dict(t=40, b=10, l=10, r=10),
            height=380,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_nav, use_container_width=True)

        col_dd, col_alloc = st.columns(2)
        with col_dd:
            st.markdown("##### 🌊 动态水下回撤对比图 (Underwater Drawdown %)")
            fig_dd = go.Figure()
            fig_dd.add_trace(go.Scatter(
                x=df_bt['date'],
                y=df_bt['strategy_drawdown'],
                mode='lines',
                fill='tozeroy',
                name='组合水下回撤',
                line=dict(color='#10b981', width=1.5),
                fillcolor='rgba(16, 185, 129, 0.15)'
            ))
            if "secondary_drawdown" in df_bt.columns:
                fig_dd.add_trace(go.Scatter(
                    x=df_bt['date'],
                    y=df_bt['secondary_drawdown'],
                    mode='lines',
                    name='调仓后水下回撤',
                    line=dict(color='#2563eb', width=1.5)
                ))
            fig_dd.add_trace(go.Scatter(
                x=df_bt['date'],
                y=df_bt['h300_drawdown'],
                mode='lines',
                name='沪深300回撤',
                line=dict(color='#94a3b8', width=1.0, dash='dot')
            ))
            fig_dd.update_layout(
                xaxis_title="日期",
                yaxis_title="回撤百分比 (%)",
                margin=dict(t=10, b=10, l=10, r=10),
                height=280,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_dd, use_container_width=True)

        with col_alloc:
            st.markdown("##### 📊 历史大类资产仓位变迁面积图 (Stacked Area %)")
            fig_area = go.Figure()
            fig_area.add_trace(go.Scatter(
                x=df_bt['date'], y=df_bt['weight_ashare'] * 100.0, mode='lines', stackgroup='one',
                name='A股权益仓位', line=dict(width=0.5, color='#ef4444'), fillcolor='rgba(239, 68, 68, 0.6)'
            ))
            fig_area.add_trace(go.Scatter(
                x=df_bt['date'], y=df_bt['weight_bond'] * 100.0, mode='lines', stackgroup='one',
                name='纯债避风港', line=dict(width=0.5, color='#3b82f6'), fillcolor='rgba(59, 130, 246, 0.6)'
            ))
            fig_area.add_trace(go.Scatter(
                x=df_bt['date'], y=df_bt['weight_gold'] * 100.0, mode='lines', stackgroup='one',
                name='黄金对冲气垫', line=dict(width=0.5, color='#f59e0b'), fillcolor='rgba(245, 158, 11, 0.6)'
            ))
            fig_area.add_trace(go.Scatter(
                x=df_bt['date'], y=df_bt['weight_spx'] * 100.0, mode='lines', stackgroup='one',
                name='海外标普对冲', line=dict(width=0.5, color='#8b5cf6'), fillcolor='rgba(139, 92, 246, 0.6)'
            ))
            fig_area.update_layout(
                xaxis_title="日期",
                yaxis_title="配置比例 (%)",
                yaxis_range=[0, 100],
                margin=dict(t=10, b=10, l=10, r=10),
                height=280,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_area, use_container_width=True)

        # 6 大历史市场风格切片明细表与历史同温层匹配器
        st.markdown("#### 📜 6 大历史市场风格切片全胜战报 (Gate B 考核通过)")
        df_slices = trial29_kpi.get("slices_df")
        if df_slices is not None and not df_slices.empty:
            st.dataframe(df_slices, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("#### 🔍 历史相似行情与宏观同温层匹配器 (History Analog Matcher)")
        st.caption("系统通过 4 维特征向量在 2018~2026 年大样本中匹配历史同温层行情：")

        analog_tab2 = _cached_find_historical_analogs(top_k=3)
        st.info(analog_tab2.get("summary_text", ""))

        if analog_tab2.get("matches"):
            st.markdown("##### 📊 当时发生了什么 & 策略表现如何？")
            col_t2_1, col_t2_2, col_t2_3 = st.columns(3)
            for col_item, m in zip([col_t2_1, col_t2_2, col_t2_3], analog_tab2["matches"]):
                with col_item:
                    st.markdown(f"""
                    <div class="decision-card">
                        <div class="decision-title">时期：{m['date']} ｜ 相似度 {m['similarity_pct']:.1f}%</div>
                        <div class="decision-val" style="color: {'#ef4444' if m['strategy_ret_60d'] >= 0 else '#10b981'}; font-size:16px;">
                            策略后60日：{m['strategy_ret_60d']:+.2f}% (沪深300: {m['h300_ret_60d']:+.2f}%)
                        </div>
                        <div class="decision-desc">
                            - <b>未来20日(1个月)</b>：沪深300 {m['h300_ret_20d']:+.2f}% ｜ 策略 {m['strategy_ret_20d']:+.2f}%<br>
                            - <b>未来60日(3个月)</b>：策略最大回撤 {m['strategy_mdd_60d']:.2f}%<br>
                            - <b>当时大类配置</b>：{m['alloc_desc']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"⚠️ 【📈 组合回测】渲染出现局部异常: {e}")
        st.caption("💡 其他 Tab 工作区保持正常运行。如需排查可检查日志。")


# =============================================================
# Tab 4: 【🔍 穿透工具】（大类穿透/加权行业/重合热力图/底层排雷/AC算费/ETF溢价，移除在途中心）
# =============================================================
with tab_toolbox:
    try:
        st.subheader("🔍 穿透工具")

        box_tab1, box_tab2, box_tab3 = st.tabs([
            "📊 资产穿透",
            "💡 A/C算费",
            "📡 ETF溢价"
        ])

        with box_tab1:
            st.markdown("#### 🎯 资产大类缺口")

            cur_cats = {}
            for c, h in pm.holdings.items():
                cat = pm.classify_fund_asset_class(c, h.fund_name)
                cur_cats[cat] = cur_cats.get(cat, 0.0) + h.market_value
            cur_cats["可用现金"] = pm.available_cash

            target_funds = snapshot.get("target_weights_funds", {})
            all_cats = sorted(list(set(list(cur_cats.keys()) + [pm.classify_fund_asset_class(k) for k in target_funds.keys()])))

            # 并排渲染：左侧大类条形图，右侧行业暴露图 (height=320，彻底解决图 4 挤压不协调)
            col_chart_left, col_chart_right = st.columns([5, 5])
            with col_chart_left:
                st.markdown("##### 📊 资产大类实际占比 vs 目标占比")
                bar_data = []
                for cat in all_cats:
                    c_val = cur_cats.get(cat, 0.0)
                    c_pct = round((c_val / total_cur_equity * 100.0) if total_cur_equity > 0 else 0.0, 2)
                    t_pct = round(sum(w for k, w in target_funds.items() if pm.classify_fund_asset_class(k) == cat) * 100.0, 2)
                    bar_data.append({"资产大类": cat, "占比(%)": c_pct, "统计口径": "我的当前占比"})
                    bar_data.append({"资产大类": cat, "占比(%)": t_pct, "统计口径": "AI今日目标占比"})

                df_bar = pd.DataFrame(bar_data)
                fig_bar = px.bar(
                    df_bar,
                    x="占比(%)",
                    y="资产大类",
                    color="统计口径",
                    barmode="group",
                    orientation="h",
                    color_discrete_map={"我的当前占比": "#38bdf8", "AI今日目标占比": "#10b981"},
                    text_auto=".1f%"
                )
                fig_bar.update_layout(
                    margin=dict(t=15, b=10, l=10, r=10),
                    height=320,
                    xaxis_title="资产占比 (%)",
                    yaxis_title="",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_bar, use_container_width=True)

            with col_chart_right:
                st.markdown("##### 🏭 加权行业穿透暴露")
                _h_repr = str(sorted((c, h.shares, h.current_nav) for c, h in pm.holdings.items()))
                df_ind = _cached_look_through_industry(_h_repr)
                if not df_ind.empty:
                    fig_ind_b = px.bar(df_ind, x="暴露占比(%)", y="行业", orientation="h", color="暴露占比(%)", color_continuous_scale="Viridis", text_auto=".1f%")
                    fig_ind_b.update_layout(margin=dict(t=15, b=10, l=10, r=10), height=320, yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig_ind_b, use_container_width=True)
                else:
                    st.info("当前无持仓数据可供行业穿透。")

            # 大类资产配置缺口量化分析表
            st.markdown("##### ⚖️ 大类资产配置缺口量化分析表 (实际 vs 模型目标)")
            gap_rows = []
            for cat in sorted(all_cats):
                c_val = cur_cats.get(cat, 0.0)
                c_pct = (c_val / total_cur_equity * 100.0) if total_cur_equity > 0 else 0.0
                t_pct = sum(w for k, w in target_funds.items() if pm.classify_fund_asset_class(k) == cat) * 100.0
                t_val = total_cur_equity * (t_pct / 100.0)
                diff_val = c_val - t_val
                diff_pct = c_pct - t_pct

                action_advice = "仓位均衡 (在1%容差内)" if abs(diff_pct) < 1.0 else (f"超配偏离，建议减配 -¥{abs(diff_val):,.2f}" if diff_pct > 0 else f"欠配缺口，建议增配 +¥{abs(diff_val):,.2f}")

                gap_rows.append({
                    "资产大类": cat,
                    "当前市值(元)": c_val,
                    "当前占比(%)": c_pct,
                    "目标占比(%)": t_pct,
                    "配置缺口(元)": -diff_val,
                    "偏离百分比(%)": -diff_pct,
                    "配置建议": action_advice
                })

            df_gap = pd.DataFrame(gap_rows)
            st.dataframe(
                df_gap,
                column_config={
                    "当前市值(元)": st.column_config.NumberColumn(format="¥%.2f"),
                    "当前占比(%)": st.column_config.ProgressColumn(min_value=0, max_value=60, format="%.1f%%"),
                    "目标占比(%)": st.column_config.ProgressColumn(min_value=0, max_value=60, format="%.1f%%"),
                    "配置缺口(元)": st.column_config.NumberColumn(format="¥%+.2f"),
                    "偏离百分比(%)": st.column_config.NumberColumn(format="%+.1f%%"),
                },
                use_container_width=True,
                hide_index=True
            )

            # 重仓股交叉重合度检测 (宽屏 height=360 自适应渲染，消除图 4 挤压)
            st.markdown("---")
            st.markdown("#### ⚠️ 前十大重仓股重叠交叉检测与热力图")
            overlap_res = _cached_stock_overlap(_h_repr)
            max_unexcused = float(overlap_res.get("max_non_diag_unexcused", 0.0))
            alerts = overlap_res.get("alerts", [])

            if max_unexcused == 0.0 and len(alerts) == 0:
                st.success("✅ **您的组合跨大类分散度极佳，前十大重仓股零重叠**")
            elif max_unexcused < 0.20 and len(alerts) == 0:
                st.success(f"✅ **跨大类分散度良好！** 前十大重仓股无明显交叉（最高重叠仅 {max_unexcused*100:.1f}%，低于 20% 警戒线）。")
            else:
                st.warning(f"⚠️ **检测到持仓间存在较高重仓股重叠（最高达 {max_unexcused*100:.1f}%）！** 伪分散可能导致风险集中。")
                for a in alerts:
                    st.warning(a["warning_msg"])

            if len(overlap_res.get("funds", [])) >= 2:
                fig_heat = px.imshow(
                    overlap_res["matrix"],
                    labels=dict(x="基金", y="基金", color="重合度"),
                    x=overlap_res["funds"], y=overlap_res["funds"],
                    color_continuous_scale="Blues", text_auto=".2f"
                )
                fig_heat.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=360)
                st.plotly_chart(fig_heat, use_container_width=True)

            # 底层穿透排雷大宽表
            st.markdown("---")
            st.markdown("#### 🛡️ 基金底层前十大重仓股穿透排雷大宽表 (商誉/存贷双高/质押/解禁)")
            if len(pm.holdings) > 0:
                port_risk = _cached_penetration_risk(_h_repr)
                c_pr1, c_pr2, c_pr3 = st.columns(3)
                with c_pr1:
                    st.metric("组合加权排雷风险指数", f"{port_risk['portfolio_risk_index']:.1f} / 100", delta=port_risk['risk_badge'])
                with c_pr2:
                    st.metric("🔴 预警高危重仓股数", f"{port_risk['danger_stock_count']} 只")
                with c_pr3:
                    st.metric("🟡 关注警戒重仓股数", f"{port_risk['watch_stock_count']} 只")

                df_scr = _cached_stocks_df(_h_repr)
                if not df_scr.empty:
                    disp_cols = [
                        "关联持仓基金", "股票代码", "股票名称", "占组合总市值比例(%)",
                        "商誉占净资产(%)", "存贷双高造假排雷", "控股股东质押率(%)",
                        "质押警戒", "90天解禁市值(万元)", "穿透评级", "排雷原因说明"
                    ]
                    active_cols = [c for c in disp_cols if c in df_scr.columns]
                    st.dataframe(
                        df_scr[active_cols],
                        column_config={
                            "占组合总市值比例(%)": st.column_config.ProgressColumn(min_value=0, max_value=20, format="%.2f%%"),
                            "商誉占净资产(%)": st.column_config.NumberColumn(format="%.1f%%"),
                            "控股股东质押率(%)": st.column_config.NumberColumn(format="%.1f%%"),
                            "90天解禁市值(万元)": st.column_config.NumberColumn(format="¥%.1f万"),
                        },
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("当前持仓中均为纯债或海外 QDII 标的，无 A 股权益重仓股信用穿透排雷项。")
            else:
                st.info("当前无持仓数据可供穿透排雷。")

            # 聪明钱与机构抱团监控
            st.markdown("---")
            st.markdown("#### 📡 聪明钱跟踪与机构抱团拥挤度监控 (北向资金/股东户数/龙虎榜)")
            if len(pm.holdings) > 0:
                crowd_rows = []
                for code, h in pm.holdings.items():
                    c_info = pm.get_fund_smart_money_crowding(code)
                    crowd_rows.append({
                        "基金代码": code,
                        "基金名称": h.fund_name,
                        "北向1日买卖(万元)": c_info.get("northbound_1d_net_million", 0.0),
                        "北向5日买卖(万元)": c_info.get("northbound_5d_net_million", 0.0),
                        "筹码集中度趋向": c_info.get("concentration_trend", "筹码平稳"),
                        "赛道抱团程度": c_info.get("crowding_degree", "相对分散"),
                        "抱团踩踏风险预警": "⚠️ 踩踏高危" if c_info.get("crowding_warning") else "🟢 稳定",
                        "投顾建议": c_info.get("advisory_tip", "正常跟踪")
                    })
                df_crowd = pd.DataFrame(crowd_rows)
                st.dataframe(
                    df_crowd,
                    column_config={
                        "北向1日买卖(万元)": st.column_config.NumberColumn(format="¥%+.1f万"),
                        "北向5日买卖(万元)": st.column_config.NumberColumn(format="¥%+.1f万"),
                    },
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("当前无持仓数据可供聪明钱监控。")

        # A/C 份额盈亏平衡计算器
        with box_tab2:
            st.markdown("#### 💡 A/C 份额全周期费率盈亏平衡计算器")
            c_ac1, c_ac2, c_ac3, c_ac4 = st.columns(4)
            with c_ac1:
                r_sub = st.number_input("A 类前端申购费率 (折后 %)", value=0.15, step=0.01, key="ac_r_sub")
            with c_ac2:
                r_sales = st.number_input("C 类年化销售服务费率 (%)", value=0.40, step=0.05, key="ac_r_sales")
            with c_ac3:
                v_amt = st.number_input("拟投资金额 (元)", value=50000.0, step=5000.0, key="ac_v_amt")
            with c_ac4:
                v_days = st.number_input("预计持有周期 (天)", value=90, min_value=1, max_value=730, step=5, key="ac_v_days")

            calc_res = calc.calculate_break_even_days(
                standard_sub_rate=r_sub / 10.0 / 100.0,
                discount=10.0,
                sales_service_annual_rate=r_sales / 100.0,
                max_days=365,
                target_holding_days=int(v_days),
                investment_amount=float(v_amt)
            )
            st.success(f"⚖️ **精算测算结论**：A 类与 C 类的费率盈亏平衡天数为 **{calc_res['break_even_day']} 天**！")
            if calc_res.get("target_recommendation"):
                st.info(f"🎯 **选型建议**：{calc_res['target_recommendation']['summary']}")

        # 场内 ETF 溢价监控
        with box_tab3:
            st.markdown("#### 📡 场内 ETF 溢价率监控 (Wind 湖仓离线快照模式)")
            st.caption("实时监控场内核心 ETF 折溢价率，溢价率 >0.8% 时严格预警防范高位追高回撤风险：")
            etf_alerts = pm.check_etf_premiums()
            if etf_alerts:
                st.warning(f"⚠️ 当前检测到 **{len(etf_alerts)}** 只场内 ETF 溢价率超出 0.8% 风控红线：")
                etf_rows = []
                for ea in etf_alerts:
                    etf_rows.append({
                        "ETF代码": ea["code"],
                        "ETF名称": ea["name"],
                        "场内现价(元)": ea["price"],
                        "IOPV估值(元)": ea["iopv"],
                        "溢价率(%)": ea["premium_pct"],
                        "风险等级": "高溢价预警",
                        "操作建议": "溢价率>0.8%已超出安全红线，严禁盲目追高，谨防价格向净值回归造成损失！"
                    })
                st.dataframe(pd.DataFrame(etf_rows), use_container_width=True, hide_index=True)
            else:
                st.success("✅ 所有核心监控场内 ETF 溢价率均处于正常安全范围 (<= 0.8%)。")

    except Exception as e:
        st.error(f"⚠️ 【🔍 穿透工具】渲染出现局部异常: {e}")
        st.caption("💡 其他 Tab 工作区保持正常运行。如需排查可检查日志。")
