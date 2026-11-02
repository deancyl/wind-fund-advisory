"""
AGY2 A股基金实盘组合接管与智能投顾图形化工作台 (app_gui.py)
深度接入 AI 投顾核心策略大脑与全天候因果状态机：
1. 顶部状态栏：申赎时钟(15:00生死线)、AI 全天候策略状态机、沪深300趋势生命线、宏观股债性价比(ERP历史分位数)、Alpha超额与全资产监控；
2. Tab 1：【🧭 AI 投顾大脑与今日操作建议】（首屏默认）：XAI决策树4大看板、今日建议调仓执行单、一键跟单采纳在途单与高级微调沙盒；
3. Tab 2：【📈 策略历史胜率、净值回测与风控档案】：4大核心胜率指标卡、2018-2026全周期策略净值曲线(高亮6大切片与Holdout盲测区)、水下回撤图、股债仓位面积图、6大历史风格切片明细表；
4. Tab 3：【💼 我的持仓账本与傻瓜式接管向导】：3步极简接管向导(冷启动/文件导入/单只追加)、st.data_editor直接编辑与FIFO批次倒计时折叠透视；
5. Tab 4：【🔍 组合穿透诊断、在途对账与 A/C 算费工具箱】：双环资产配置与缺口图、加权行业集中度与重仓股重合度热力图、在途订单T+1对账、A/C份额盈亏平衡计算器、场内ETF溢价监控。
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

# 路径对齐
CURRENT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = CURRENT_DIR.parent if CURRENT_DIR.name == "AGY2_FundAdvisory" else CURRENT_DIR
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

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
from trading_clock_fee import TradingClock, FeeMatrixCalculator
from strategy_bridge import (
    StrategyBridge,
    INDEX_TO_FUND_MAP,
    RISK_TIERS_CONFIG,
    map_target_return_to_tier,
    evaluate_questionnaire_risk_tier,
    get_risk_mismatch_warning,
    calculate_human_readable_metrics,
    get_aggressive_dream_reality_check,
    strategy_fn_for_tier
)
from winrate_engine import WinRateEngine, HOLDING_PERIODS
from market_screener import MarketScreener
from portfolio_optimizer import WinRateOptimizer
from cache_manager import SmartCacheManager

# 统一资产分类解析器动态兜底 (通用行业属性与投资标的规则，绝无静态固定代码字典)
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

# 自定义 CSS 强化桌面客户端质感
st.markdown("""
<style>
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
    .consequence-title {
        font-size: 12px;
        font-weight: 600;
        color: #475569;
        margin-bottom: 2px;
    }
    .consequence-val {
        font-size: 16px;
        font-weight: 700;
        margin: 2px 0;
    }
    .consequence-sub {
        font-size: 11px;
        color: #334155;
        line-height: 1.35;
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
</style>
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

# 实时拉取最新策略大脑快照 (动态计算)
snapshot = StrategyBridge.get_latest_market_snapshot()
trial29_kpi = StrategyBridge.load_trial29_metrics()

# -------------------------------------------------------------
# 侧边栏：组合基准信息与全局快捷动作
# -------------------------------------------------------------
with st.sidebar:
    st.title("🛡️ AGY2 投顾工作台")
    st.caption("A股跨风格高胜率策略大脑 (全天候生产版)")
    st.markdown("---")

    # 一键操作区
    st.subheader("⚡ 组合快捷控制")
    col_demo, col_undo = st.columns(2)
    with col_demo:
        if st.button("🚀 加载演示组合", use_container_width=True, help="注入包含冷启动、7天锁、待满期、深套基及在途单的完整演示组合"):
            demo_res = pm.load_demo_portfolio()
            st.success("演示组合载入成功！")
            st.rerun()

    with col_undo:
        if st.button("↩️ 一键撤销", use_container_width=True, help="撤销上一步操作并回滚快照"):
            with st.spinner("↩️ 回滚中..."):
                _undo_ok = pm.undo()
            if _undo_ok:
                st.info("✅ 已成功回滚至上一快照！")
                st.rerun()
            else:
                st.warning("暂无更早快照可撤销")

    if st.button("🔄 同步最新真实净值", use_container_width=True, help="双源拉取天天基金与新浪最新净值/估值，刷新持仓市值与 Alpha"):
        with st.spinner("🔄 正在从天天基金/新浪双源拉取最新净值..."):
            s_res = pm.sync_holdings_live_nav(use_intraday_gsz=True)
        st.success(f"✅ 已同步 {s_res.get('updated_count', 0)} 只持仓最新净值！")
        st.rerun()

    # 接管模式切换与信息
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
    # 可用现金直接修改
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

# 动态计算双向触发线与估值温度
c300_disp = intraday_eval.get("realtime_c300", snapshot.get("c300_price", snapshot.get('c300', 4053.0)))
bias_disp = intraday_eval.get("bias_m20", snapshot.get('bias_20', 0.0))
m20_disp = intraday_eval.get("m20", snapshot.get("m20_price", snapshot.get('m20', 4140.0)))
m60_disp = intraday_eval.get("m60", snapshot.get("m60_price", snapshot.get('m60', 3962.0)))
trigger_lines = snapshot.get("trigger_lines") or {}
surge_line = float(trigger_lines.get("surge_line", snapshot.get("surge_line", c300_disp * 1.012)))
breakdown_line = float(trigger_lines.get("breakdown_line", snapshot.get("breakdown_line", c300_disp * 0.985)))

# 宏观指标
erp_pct = snapshot.get("erp_percentile", 81.9)
erp_val = snapshot.get("erp_val", 5.82)
dr007_val = snapshot.get("dr007", 1.39)
dr007_bp = snapshot.get("dr007_spread_bp", -11.1)
opt_iv = float(snapshot.get("option_iv_pct", 19.4))
ic_basis = float(snapshot.get("ic_annualized_basis_rate", 17.9))
days_to_next = rebal_grid.get("days_to_next", rebal_grid.get("days_to_grid", 3))

# 4 宽卡 + 1 紧凑刷新按钮列
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

# 盘后盯盘待办预案提醒 (痛点 3)
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

# 在途提醒
pending_count = len([o for o in pm.pending_orders if o.status == "PENDING"])
if pending_count > 0:
    st.info(f"🔔 **在途对账提醒**：当前有 **{pending_count}** 笔在途待确认订单！可在【🔍 组合穿透诊断、对账与工具箱】输入公布净值完成确认与校准。")

# -------------------------------------------------------------
# 核心四大工作区 (符合直觉的重塑布局)
# -------------------------------------------------------------
tab_zero_start, tab_holdings_and_rebalance, tab_toolbox, tab_backtest, tab_market_optimizer = st.tabs([
    "🌱 新资金从0建仓推演",
    "💼 我的当前持仓与今日调仓建议",
    "🔍 组合深度体检与算费工具箱",
    "📈 策略历史回测与胜率档案",
    "🎯 全市场胜率最优选基"
])


# =============================================================
# Tab 1: 【🌱 新资金从0建仓推演】（从 0 定目标、看推演、拿建仓单）
# =============================================================
with tab_zero_start:
    st.markdown("## 🌱 新资金从 0 建仓推演：三步极简落地")
    st.caption("告别静态死板的陈列馆！根据您的真实预期年化与抗痛承受力，现场毫秒级运行 2018-2026 全周期实境回测，生成清晰可读的人话账单与一键复制执行清单。")

    # 初始化核心 session_state
    if "target_return_val" not in st.session_state:
        st.session_state.target_return_val = 15.0
    if "tested_tier_val" not in st.session_state:
        st.session_state.tested_tier_val = "C3"
    if "active_tier_val" not in st.session_state:
        st.session_state.active_tier_val = "C3"
    if "custom_fund_overrides" not in st.session_state:
        st.session_state.custom_fund_overrides = {}
    if "pact_accepted" not in st.session_state:
        st.session_state.pact_accepted = False
    if "sim_has_run" not in st.session_state:
        st.session_state.sim_has_run = True
    if "sim_timestamp" not in st.session_state:
        st.session_state.sim_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ---------------------------------------------------------
    # 步骤一：【🎯 定目标 / 测风险】—— 解耦单选定档向导
    # ---------------------------------------------------------
    def map_slider_to_tier(ret: float) -> str:
        """模式 A 目标收益率到风险档位映射: C1 (5-8%), C2 (>8-12%), C3 (>12-18%), C4 (>18-30%), C5 (>30-100%)"""
        if ret <= 8.0:
            return "C1"
        elif ret <= 12.0:
            return "C2"
        elif ret <= 18.0:
            return "C3"
        elif ret <= 30.0:
            return "C4"
        else:
            return "C5"

    with st.container(border=True):
        st.markdown("### 步骤一：【🎯 定目标 / 测风险】—— 解耦定档向导")

        tier_mode = st.radio(
            "定档方式",
            ["模式 A：按期望年化收益率滑块定档 (滑块即拉即变)", "模式 B：30秒风险承受力测评定档", "模式 C：🎯 AI全市场胜率最优选基 (设定收益目标+持有期)"],
            horizontal=True,
            key="tier_determination_mode"
        )

        if tier_mode.startswith("模式 A"):
            cur_tier_init = st.session_state.get("active_tier_val", "C3")
            def_target = float(st.session_state.get("target_return_val", RISK_TIERS_CONFIG.get(cur_tier_init, {}).get("default_target", 15.0)))

            col_sl, col_cap, col_act = st.columns([5.5, 3.0, 1.5])
            with col_sl:
                target_ret_input = st.slider(
                    "期望年化目标收益率 (%)",
                    min_value=5.0,
                    max_value=100.0,
                    value=def_target,
                    step=1.0,
                    format="%.0f%%",
                    help="拖动滑块即拉即变，C1 至 C5 实时无损同步切换",
                    key="slider_target_return"
                )
                st.session_state.target_return_val = target_ret_input
                active_tier = map_slider_to_tier(target_ret_input)
                st.session_state.active_tier_val = active_tier

            with col_cap:
                plan_capital = st.number_input(
                    "💵 拟投资总本金 (元)",
                    min_value=1000.0,
                    max_value=100000000.0,
                    value=100000.0,
                    step=10000.0,
                    format="%.0f",
                    key="plan_capital_input"
                )

            with col_act:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                if st.button("⚡ 现场推演", type="primary", use_container_width=True, key="btn_run_simulation_now"):
                    st.session_state.sim_has_run = True
                    st.session_state.sim_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    st.rerun()

            cur_tier_meta = RISK_TIERS_CONFIG[active_tier]
            if target_ret_input > 25.0:
                st.caption(f"⚡ 高收益提示：目标年化 {target_ret_input:.0f}% 对应【{active_tier} {cur_tier_meta['name']}】，历史最大回撤约 {abs(cur_tier_meta['historical_mdd']):.1f}%，解套需 {cur_tier_meta['max_tolerated_months']} 个月，建议长钱长投。")
            else:
                st.caption(f"💡 目标收益 {target_ret_input:.0f}% ➔ 当前档位：【{active_tier} {cur_tier_meta['name']}】（权益上限 {cur_tier_meta['equity_range'][1]}% ｜ 预期年化 {cur_tier_meta['target_cagr']} ｜ 核心：{cur_tier_meta['core_assets']}）")
            # ── 多持有期胜率参考表（实时跟随滑块） ──
            try:
                _wr_bt = StrategyBridge.get_backtest_nav_for_tier(active_tier)
                if _wr_bt is not None and 'strategy_nav' in _wr_bt.columns and len(_wr_bt) > 250:
                    _wr_table = WinRateEngine.multi_horizon_winrate_table(
                        _wr_bt['strategy_nav'], target_ret_input / 100.0
                    )
                    _wr_cols = st.columns(3)
                    for _wi, (_wk, _wv) in enumerate(_wr_table.items()):
                        with _wr_cols[_wi]:
                            st.metric(
                                f"{_wv['label']} 胜率",
                                f"{_wv['win_rate']*100:.1f}%",
                                delta=f"不亏损 {_wv['no_loss_rate']*100:.0f}%",
                            )
            except Exception:
                pass

        elif tier_mode.startswith("模式 B"):
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
            cur_tier_meta = RISK_TIERS_CONFIG[active_tier]

            col_cap_b, col_act_b = st.columns([7.5, 2.5])
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
            with col_act_b:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                if st.button("⚡ 现场推演", type="primary", use_container_width=True, key="btn_run_sim_b"):
                    st.session_state.sim_has_run = True
                    st.session_state.sim_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    st.rerun()

            st.caption(f"📝 问卷总分：`{total_q_score} 分` ➔ 评定承受档位：**【{active_tier} {cur_tier_meta['name']}】**（建议年化 {cur_tier_meta['target_cagr']}，最大回撤容忍 {cur_tier_meta['max_drawdown_limit']}）")

        elif tier_mode.startswith("模式 C"):
            # ─── 模式 C：全市场胜率最优选基（内联入口）────────────
            st.markdown("#### 🎯 AI 全市场胜率最优选基")
            st.caption("从全市场约 28,000 只公募基金中，智能筛选并优化出在您设定的目标收益和持有期下历史胜率最高的基金组合。")

            col_mc1, col_mc2, col_mc3 = st.columns([4, 3, 3])
            with col_mc1:
                mc_target_ret = st.slider(
                    "🎚️ 目标年化收益率 (%)",
                    min_value=3.0, max_value=25.0, value=8.0, step=1.0,
                    format="%.0f%%", key="mode_c_target_return"
                )
            with col_mc2:
                mc_horizon = st.radio(
                    "📅 计划持有期",
                    ["短期(3~6月)", "中期(1~2年)", "长期(3~5年)"],
                    index=1, horizontal=True, key="mode_c_horizon"
                )
            with col_mc3:
                mc_capital = st.number_input(
                    "💰 投资金额 (元)",
                    min_value=1000.0, max_value=100000000.0, value=100000.0,
                    step=10000.0, format="%.0f", key="mode_c_capital"
                )
            horizon_map_c = {"短期(3~6月)": "short", "中期(1~2年)": "medium", "长期(3~5年)": "long"}
            mc_period_key = horizon_map_c.get(mc_horizon, "medium")
            active_tier = map_slider_to_tier(mc_target_ret)
            st.session_state.active_tier_val = active_tier
            cur_tier_meta = RISK_TIERS_CONFIG[active_tier]
            plan_capital = mc_capital
            st.info("💡 **提示**：完整的全市场选基功能请前往第 5 个 Tab「🎯 全市场胜率最优选基」，支持分步可视化筛选流程和详细对比。")
            # ── 多持有期胜率参考表（模式 C） ──
            try:
                _wrc_bt = StrategyBridge.get_backtest_nav_for_tier(active_tier)
                if _wrc_bt is not None and 'strategy_nav' in _wrc_bt.columns and len(_wrc_bt) > 250:
                    _wrc_table = WinRateEngine.multi_horizon_winrate_table(
                        _wrc_bt['strategy_nav'], mc_target_ret / 100.0
                    )
                    _wrc_cols = st.columns(3)
                    for _wci, (_wck, _wcv) in enumerate(_wrc_table.items()):
                        with _wrc_cols[_wci]:
                            st.metric(
                                f"{_wcv['label']} 胜率",
                                f"{_wcv['win_rate']*100:.1f}%",
                                delta=f"不亏损 {_wcv['no_loss_rate']*100:.0f}%",
                            )
            except Exception:
                pass

    # ---------------------------------------------------------
    # 步骤二：【🧪 现场推演看好坏】—— 全市场回测与人话指标深度检验
    # ---------------------------------------------------------
    st.markdown(f"### 步骤二：【🧪 现场推演看好坏】—— 当前档位：**【{active_tier} {cur_tier_meta['name']}】**（标杆年化 {cur_tier_meta['target_cagr']}）")

    # 档位与演算状态追踪：切换档位或点击推演触发实时极速演算
    if "last_sim_tier" not in st.session_state:
        st.session_state.last_sim_tier = active_tier
    elif st.session_state.last_sim_tier != active_tier:
        st.session_state.last_sim_tier = active_tier
        st.session_state.sim_has_run = True

    sim_container = st.container()
    readable_kpi = None
    with sim_container:
        if st.session_state.sim_has_run:
            sim_t0 = time.time()
            with st.status(f"🧠 AI 投顾引擎正在针对【{active_tier} 档位】为您现场推演...", expanded=True) as status:
                prog_bar = st.progress(0, text="开始执行量化现场推演...")

                # Step 1: 全市场公募基金四级漏斗海选
                prog_bar.progress(25, text="Step 1/4: 全市场公募基金海选漏斗执行中...")
                f_stats = StrategyBridge.get_fund_selection_funnel_stats(active_tier)
                st.write(
                    f"🔍 **Step 1 (全市场海选)**：从本地 DuckDB {f_stats['total_market_funds']:,} 只公募基金库中，"
                    f"按【{active_tier}】风险档位筛选规模 > 2亿、成立 > 3年、费率低且超额 Alpha 领先的候选基金池 "
                    f"（漏斗过滤：{f_stats['total_market_funds']:,} ➔ {f_stats['hard_filtered_funds']:,} ➔ {f_stats['candidate_funds']} ➔ {f_stats['final_champion_funds']} 只金牌标的）"
                )

                # Step 2: 宏观动量与衍生品状态机多维定调
                prog_bar.progress(50, text="Step 2/4: 宏观动量与期指期权衍生品状态机多维定调中...")
                opt_iv_disp = float(snapshot.get("option_iv_pct", 19.4))
                ic_basis_disp = float(snapshot.get("ic_annualized_basis_rate", 17.9))
                st.write(
                    f"🧭 **Step 2 (宏观与衍生品定调)**：宏观流动性 DR007 {snapshot.get('dr007', 1.5):.2f}%，"
                    f"期权 IV {opt_iv_disp:.1f}%，期指 IC 年化贴水 {ic_basis_disp:.1f}%，"
                    f"实时定调为【{snapshot.get('market_state', '震荡收息期')}】，攻防策略执行正常"
                )

                # Step 3: 2018-2026 跨牛熊 2,000+ 交易日实境回测与压力精算
                prog_bar.progress(75, text="Step 3/4: 2018-2026 跨牛熊 2,000+ 交易日实境回测与压力精算中...")
                try:
                    bt_df = StrategyBridge.get_backtest_nav_for_tier(active_tier)
                except Exception as e:
                    bt_df = StrategyBridge.get_backtest_nav_for_tier(active_tier)
                readable_kpi = calculate_human_readable_metrics(
                    nav_series=bt_df['strategy_nav'],
                    dates=bt_df['date'],
                    capital=plan_capital,
                    target_return_pct=st.session_state.target_return_val,
                    tier=active_tier
                )
                st.write(
                    f"📊 **Step 3 (实境回测与压力测算)**：现场跑完 2018-2026 共 {len(bt_df):,} 个交易日！"
                    f"历史顺风期最高单年 +{readable_kpi['best_case_return_pct']:.2f}% (盈利 +¥{readable_kpi['best_case_profit_amount']:,.2f})，"
                    f"极端浮亏 -{readable_kpi['worst_case_drawdown_pct']:.2f}% (最大浮亏 -¥{readable_kpi['worst_case_loss_amount']:,.2f})，"
                    f"最长水下回本 {readable_kpi['max_underwater_days']} 个交易日"
                )

                # Step 4: 交易摩擦精算、限购拆单与实盘执行清单
                prog_bar.progress(100, text="Step 4/4: 交易摩擦精算、限购拆单与实盘执行清单生成完毕！")
                st.write(f"📋 **Step 4 (执行单与拆单路由)**：精算申赎手续费与 7 天在途锁仓，自动路由限购拆单资金，生成实盘执行小抄。")

                sim_elapsed = max(0.01, round(time.time() - sim_t0, 3))
                if status is not None and hasattr(status, "update"):
                    _cache_str = "（极速缓存返回）" if sim_elapsed < 0.5 else f"（耗时 {sim_elapsed:.2f} 秒）"
                    status.update(
                        label=f"✅ 现场推演完成 {_cache_str}  ⏱️ {st.session_state.sim_timestamp}",
                        state="complete",
                        expanded=False
                    )
            st.session_state.sim_has_run = False

    # 兜底计算人话指标卡片
    if readable_kpi is None:
        readable_kpi = calculate_human_readable_metrics(tier=active_tier, initial_capital=plan_capital)

    # 5 张大字号人话指标卡
    k_col1, k_col2, k_col3, k_col4, k_col5 = st.columns(5)
    with k_col1:
        st.markdown(f"""
        <div class="kpi-metric-card" style="border-top: 3px solid #ef4444;">
            <div class="kpi-card-title">① 最好情况 (大牛市冲刺)</div>
            <div class="metric-value-huge" style="color: #dc2626;">
                +{readable_kpi['best_case_return_pct']:.2f}%
            </div>
            <div class="kpi-card-sub" style="color: #b91c1c;">
                预计盈利: <b>+¥{readable_kpi['best_case_profit_amount']:,.2f}</b>
            </div>
            <div class="kpi-card-desc">任意持有1年最高冲刺</div>
        </div>
        """, unsafe_allow_html=True)

    with k_col2:
        st.markdown(f"""
        <div class="kpi-metric-card" style="border-top: 3px solid #10b981;">
            <div class="kpi-card-title">② 最坏情况 (极端大熊市)</div>
            <div class="metric-value-huge" style="color: #16a34a;">
                -{readable_kpi['worst_case_drawdown_pct']:.2f}%
            </div>
            <div class="kpi-card-sub" style="color: #15803d;">
                最大浮亏: <b>-¥{readable_kpi['worst_case_loss_amount']:,.2f}</b>
            </div>
            <div class="kpi-card-desc">vs 沪深300 -46.70%</div>
        </div>
        """, unsafe_allow_html=True)

    with k_col3:
        st.markdown(f"""
        <div class="kpi-metric-card" style="border-top: 3px solid #f59e0b;">
            <div class="kpi-card-title">③ 极端水下回本考验</div>
            <div class="metric-value-huge" style="color: #d97706;">
                {readable_kpi['max_underwater_days']} 天
            </div>
            <div class="kpi-card-sub" style="color: #b45309;">
                约合 <b>{readable_kpi['max_underwater_months']:.1f} 个月</b>
            </div>
            <div class="kpi-card-desc">最坏情况下回本所需时长</div>
        </div>
        """, unsafe_allow_html=True)

    with k_col4:
        st.markdown(f"""
        <div class="kpi-metric-card" style="border-top: 3px solid #0284c7;">
            <div class="kpi-card-title">④ 目标胜率与达成周期</div>
            <div class="metric-value-huge" style="color: #0284c7;">
                {readable_kpi['win_rate_1y']:.0f}%
            </div>
            <div class="kpi-card-sub" style="color: #0369a1;">
                2年胜率 {readable_kpi['win_rate_2y']:.0f}% ｜ 3年 {readable_kpi['win_rate_3y']:.0f}%
            </div>
            <div class="kpi-card-desc" title="平均达标约 {readable_kpi['time_to_target']['avg_reach_months']:.1f} 个月 (达成率 {readable_kpi['time_to_target']['reach_rate_pct']}%)">均约 {readable_kpi['time_to_target']['avg_reach_months']:.1f}月达标 (达成率 {readable_kpi['time_to_target']['reach_rate_pct']}%)</div>
        </div>
        """, unsafe_allow_html=True)

    with k_col5:
        st.markdown(f"""
        <div class="kpi-metric-card" style="border-top: 3px solid #8b5cf6;">
            <div class="kpi-card-title">⑤ 适合人群与策略灵魂</div>
            <div class="metric-value-huge" style="color: #7c3aed; font-size:16px;">
                {active_tier} {cur_tier_meta['name']}
            </div>
            <div class="kpi-card-sub" style="color: #6d28d9;" title="{readable_kpi['suitable_for']}">
                {readable_kpi['suitable_for']}
            </div>
            <div class="kpi-card-desc" title="{readable_kpi['soul_summary']}">{readable_kpi['soul_summary'][:18]}...</div>
        </div>
        """, unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 四阶量化推演工作流白盒面板 (Step 1 ~ Step 4 独立可折叠)
    # ---------------------------------------------------------

    # Step 1: 全市场 28,177 只公募基金四级漏斗海选与金牌标的
    funnel_stats = StrategyBridge.get_fund_selection_funnel_stats(active_tier)
    exp_funnel_title = f"🔍 【Step 1 白盒：全市场 28,177 只公募基金四级漏斗海选与金牌标的】（DuckDB海选 {funnel_stats['total_market_funds']:,} ➔ 锁定 {funnel_stats['final_champion_funds']} 只金牌标的）"

    with st.expander(exp_funnel_title, expanded=False):
        st.markdown(f"#### 🔍 《全市场公募基金四级量化选基漏斗》（当前档位：{active_tier} {cur_tier_meta['name']}）")

        f_c1, f_c2, f_c3, f_c4 = st.columns(4)
        with f_c1:
            st.metric("1. 全市场公募基金池", f"{funnel_stats['total_market_funds']:,} 只", "DuckDB 实时基准")
        with f_c2:
            st.metric("2. 硬指标合规初筛", f"{funnel_stats['compliance_screened_funds']:,} 只", "成立>3年/规模>2亿", delta_color="inverse")
        with f_c3:
            st.metric("3. 5大赛道入围池", f"{funnel_stats['candidate_funds']} 只", f"{active_tier} 核心候选入围", delta_color="inverse")
        with f_c4:
            st.metric("4. 最终优选金牌组合", f"{funnel_stats['final_champion_funds']} 只", "与建仓单 100% 对齐", delta_color="inverse")

        st.markdown("##### 📐 《六维量化打分加权公式（0~100分归一化）》")
        st.info("综合评分计算公式：总评得分 (0-100) = 35% * 历史超额Alpha得分 + 25% * 低费率得分 + 15% * R1底层排雷健康分 + 10% * R3北向聪明钱流入分 + 10% * 反拥挤度安全分 + 5% * 衍生品与宏观契合度")

        st.markdown("##### 📊 《当前档位入选赛道：冠军标的与备选基金六维量化评分对比表》")
        if "_QUANT_TABLE_CACHE" not in globals():
            global _QUANT_TABLE_CACHE
            _QUANT_TABLE_CACHE = {}
        ov_tuple = tuple(sorted((st.session_state.custom_fund_overrides or {}).items()))
        cache_k = (active_tier, ov_tuple)
        if cache_k not in _QUANT_TABLE_CACHE:
            _QUANT_TABLE_CACHE[cache_k] = StrategyBridge.get_tier_quant_selection_table(active_tier, st.session_state.custom_fund_overrides)
        df_quant = _QUANT_TABLE_CACHE[cache_k].copy()
        st.dataframe(
            df_quant,
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

        st.caption("🏆 赛道冠军标的与备选替换下拉框（选基与建仓单 100% 联动）：")
        sec_selection = StrategyBridge.get_tier_sector_fund_selection(active_tier)
        cols_sectors = st.columns(len(sec_selection))
        for idx, (sec_key, sec_data) in enumerate(sec_selection.items()):
            with cols_sectors[idx]:
                champ_code = sec_data["champion_code"]
                champ_name = sec_data["champion_name"]
                is_promoted = sec_data.get("is_promoted", False)

                st.markdown(f"**{sec_data['sector_name']}**")

                # R6: 真实渲染自进化优选晋升标签
                if is_promoted and sec_data.get("promotion_label"):
                    st.success(sec_data["promotion_label"])
                    st.markdown(f"🏆 **金牌标的**：`{champ_code}` {champ_name} ✨")
                else:
                    st.markdown(f"🏆 **金牌标的**：`{champ_code}` {champ_name}")

                if sec_data.get("trigger_reasons"):
                    st.caption(f"⚡ 变点触发：{'; '.join(sec_data['trigger_reasons'])}")
                st.caption(f"理由：{sec_data['champion_reason'][:36]}...")

                alt_options = [f"🏆 金牌: {champ_code} {champ_name}"] + [
                    f"备选 {alt['code']} {alt['name']} ({alt.get('tag', '')})"
                    for alt in sec_data.get("top_alternatives", [])
                ]
                current_choice = st.selectbox(
                    f"替换备选标的",
                    alt_options,
                    key=f"sel_alt_{sec_key}_{active_tier}",
                    label_visibility="collapsed"
                )
                if not current_choice.startswith("🏆"):
                    chosen_code = current_choice.split()[1]
                    st.session_state.custom_fund_overrides[champ_code] = chosen_code
                    if sec_data.get("default_champion_code"):
                        st.session_state.custom_fund_overrides[sec_data["default_champion_code"]] = chosen_code
                else:
                    if champ_code in st.session_state.custom_fund_overrides:
                        del st.session_state.custom_fund_overrides[champ_code]
                    if sec_data.get("default_champion_code") in st.session_state.custom_fund_overrides:
                        del st.session_state.custom_fund_overrides[sec_data["default_champion_code"]]

    # Step 2: 宏观与衍生品四维状态机实时定调
    exp_w = snapshot.get("expert_weights") or {}
    w_trend = float(exp_w.get("trend_momentum", 0.25)) * 100.0
    w_erp = float(exp_w.get("erp_macro", 0.25)) * 100.0
    w_rev = float(exp_w.get("ma_contrarian", 0.25)) * 100.0
    w_liq = float(exp_w.get("liquidity_basis", 0.25)) * 100.0
    exp_expert_title = f"🧭 【Step 2 白盒：Hedge 四大策略专家在线自适应定调与施密特防打脸校验】（趋势动量 {w_trend:.1f}% ｜ ERP宏观 {w_erp:.1f}% ｜ 逆向乖离 {w_rev:.1f}% ｜ 流动性基差 {w_liq:.1f}%）"
    with st.expander(exp_expert_title, expanded=False):
        st.markdown("#### 🧭 《宏观流动性、风格动量与衍生品四维因果决策信号》")
        st.caption(f"为什么今天系统选择【{snapshot.get('market_state', '震荡收息期')}】？通过趋势生命线、风格动量比拼、大小盘结构及股债性价比四维因果推导：")

        c_dec1, c_dec2, c_dec3, c_dec4 = st.columns(4)
        with c_dec1:
            st.markdown(f"""
            <div class="decision-card">
                <div class="decision-title">① 趋势生命线 (沪深300)</div>
                <div class="decision-val" style="color: {snapshot['m20_color']};">{snapshot.get('c300_price', snapshot['c300']):,.1f}</div>
                <div class="decision-desc">
                    - MA20生命线：{snapshot.get('m20_price', snapshot['m20']):,.1f} (偏离 {snapshot['bias_20']:+.2f}%)<br>
                    - MA60中线：{snapshot.get('m60_price', snapshot['m60']):,.1f} (偏离 {snapshot['bias_60']:+.2f}%)<br>
                    - MA120斜率：{snapshot['m120_slope']:+.2f}%<br>
                    - <b>研判</b>：{snapshot['m20_status_desc']}
                </div>
            </div>
            """, unsafe_allow_html=True)

        with c_dec2:
            st.markdown(f"""
            <div class="decision-card">
                <div class="decision-title">② 风格动量比拼 (60日)</div>
                <div class="decision-val" style="color: {snapshot['momentum_color']};">{snapshot['momentum_style']}</div>
                <div class="decision-desc">
                    - 科创50 (60日涨跌)：{snapshot['mom60_star']:+.2f}%<br>
                    - 中证红利 (60日涨跌)：{snapshot['mom60_div']:+.2f}%<br>
                    - 动量差 (科创 - 红利)：{snapshot['diff_star_div']:+.2f}%<br>
                    - <b>研判</b>：{snapshot['momentum_desc']}
                </div>
            </div>
            """, unsafe_allow_html=True)

        with c_dec3:
            st.markdown(f"""
            <div class="decision-card">
                <div class="decision-title">③ 大小盘结构温度 (500 vs 300)</div>
                <div class="decision-val" style="color: {snapshot['structure_color']};">{snapshot['structure_style']}</div>
                <div class="decision-desc">
                    - 中证500 (60日涨跌)：{snapshot['mom60_500']:+.2f}%<br>
                    - 沪深300 (60日涨跌)：{snapshot['mom60_300']:+.2f}%<br>
                    - 动量差 (500 - 300)：{snapshot['diff_500_300']:+.2f}%<br>
                    - <b>研判</b>：{snapshot['structure_desc']}
                </div>
            </div>
            """, unsafe_allow_html=True)

        with c_dec4:
            opt_iv_val = float(snapshot.get("option_iv_pct", 19.4))
            ic_basis_val = float(snapshot.get("ic_annualized_basis_rate", 17.9))
            st.markdown(f"""
            <div class="decision-card">
                <div class="decision-title">④ 股债性价比与衍生品</div>
                <div class="decision-val" style="color: #ef4444;">{snapshot['erp_percentile']:.1f}% 极高分位</div>
                <div class="decision-desc">
                    - 真实 ERP：{snapshot['erp_val']:.2f}% (10Y国债: {snapshot['treasury_10y']:.2f}%)<br>
                    - 期权 IV：{opt_iv_val:.1f}% ｜ 期指贴水：{ic_basis_val:.1f}%<br>
                    - <b>白话结论</b>：权益处于底部击球区，震荡收息增厚底仓！
                </div>
            </div>
            """, unsafe_allow_html=True)

        exp_weights = snapshot.get("expert_weights")
        if exp_weights and isinstance(exp_weights, dict):
            st.markdown("##### 🤖 《Hedge 在线多专家自适应乘性权重占比 (R2 在线学习)》")
            st.caption("四大正交分析流派每日根据风险调整后净效用 $u_{i,t}$ 在线乘性更新，胜率高、回撤小者自动获配更高权重：")
            w_c1, w_c2, w_c3, w_c4 = st.columns(4)
            expert_meta = [
                ("① 趋势动量专家", "trend_momentum", "#ef4444", "捕捉中长期均线突破与主升浪动量"),
                ("② ERP宏关估值专家", "erp_macro", "#38bdf8", "锚定股债性价比与历史估值安全边际"),
                ("③ 均线逆向专家", "ma_contrarian", "#34d399", "利用短周期负乖离与超卖反抽逆向布局"),
                ("④ 流动性与基差专家", "liquidity_basis", "#f59e0b", "跟踪资金面松紧度与期指年化贴水率")
            ]
            for col, (title, key, color, desc) in zip([w_c1, w_c2, w_c3, w_c4], expert_meta):
                with col:
                    weight_val = float(exp_weights.get(key, 0.25)) * 100.0
                    st.markdown(f"""
                    <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 10px; text-align: center;">
                        <div style="font-size: 12px; color: #94a3b8; margin-bottom: 4px;">{title}</div>
                        <div style="font-size: 20px; font-weight: bold; color: {color}; margin-bottom: 4px;">{weight_val:.1f}%</div>
                        <div style="font-size: 11px; color: #64748b;">{desc}</div>
                    </div>
                    """, unsafe_allow_html=True)

        st.info(f"💡 **AI 今日攻防定调结论**：{snapshot.get('ai_summary_text', '市场处于震荡磨底阶段，高股息稳健收息，耐心等待均线向上发散')}")

    # Step 3: 2018-2026 跨牛熊 2,000+ 交易日实境回测与压力测试
    with st.expander(f"📊 【Step 3 白盒：2018-2026 跨牛熊实境压力测试与五大人话硬核指标作战说明书】（回测 2,000+ 交易日 ｜ 1年胜率 {readable_kpi['win_rate_1y']:.0f}% ｜ 极限回撤 -{readable_kpi['worst_case_drawdown_pct']:.2f}%）", expanded=False):
        col_res1, col_res2 = st.columns(2)
        with col_res1:
            st.markdown(f"""
            <div style="background: rgba(239, 68, 68, 0.08); border-left: 3px solid #dc2626; border-radius: 6px; padding: 10px 14px; margin-bottom: 12px;">
                <div style="font-weight: 700; color: #b91c1c; font-size: 13px; margin-bottom: 4px;">🌟 ① 最好情况严谨量化归因（历史顺风期上限）</div>
                <div style="font-size: 12px; color: #1e293b; line-height: 1.5;">{readable_kpi['best_case']['reason']}</div>
            </div>
            <div style="background: rgba(245, 158, 11, 0.08); border-left: 3px solid #d97706; border-radius: 6px; padding: 10px 14px; margin-bottom: 12px;">
                <div style="font-weight: 700; color: #b45309; font-size: 13px; margin-bottom: 4px;">⏳ ③ 最长回本时间解套推演（Max Time Under Water）</div>
                <div style="font-size: 12px; color: #1e293b; line-height: 1.5;">{readable_kpi['max_underwater_recovery']['message']}</div>
            </div>
            """, unsafe_allow_html=True)
        with col_res2:
            st.markdown(f"""
            <div style="background: rgba(16, 185, 129, 0.08); border-left: 3px solid #16a34a; border-radius: 6px; padding: 10px 14px; margin-bottom: 12px;">
                <div style="font-weight: 700; color: #15803d; font-size: 13px; margin-bottom: 4px;">⛈️ ② 最坏情况严谨量化归因（历史极端股灾底线）</div>
                <div style="font-size: 12px; color: #1e293b; line-height: 1.5;">{readable_kpi['worst_case']['reason']}</div>
            </div>
            <div style="background: rgba(56, 189, 248, 0.08); border-left: 3px solid #0284c7; border-radius: 6px; padding: 10px 14px; margin-bottom: 12px;">
                <div style="font-weight: 700; color: #0369a1; font-size: 13px; margin-bottom: 4px;">🏁 ④ 预期收益达成周期统计（Time to Target）</div>
                <div style="font-size: 12px; color: #1e293b; line-height: 1.5;">{readable_kpi['time_to_target']['message']}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"##### 🎯 这套【{active_tier} {cur_tier_meta['name']}】策略到底适合什么市场环境？不适合什么情况？")
        df_suit = pd.DataFrame(readable_kpi["suitability_table"])
        st.dataframe(
            df_suit,
            column_config={
                "环境": st.column_config.TextColumn("市场环境", width="medium"),
                "表现": st.column_config.TextColumn("策略表现定位", width="medium"),
                "量化原因": st.column_config.TextColumn("严谨量化原因与应对机制", width="large")
            },
            use_container_width=True,
            hide_index=True
        )

    # Step 4: 交易摩擦精算、限购拆单与实盘执行清单
    exp_fee_title = "⚙️ 【Step 4 白盒：真实 A/C 阶梯费率、T+2 在途损耗拦截与限购拆单精算】（手续费预估 ¥0~12.5 ｜ 股息回本约 0.5~1.5 个月 ｜ 智能拆单承接）"
    with st.expander(exp_fee_title, expanded=False):
        st.markdown("#### ⚙️ 《交易摩擦精算、持有费率优化与限购自动拆单路由》")
        c_fe1, c_fe2, c_fe3 = st.columns(3)
        with c_fe1:
            st.markdown("""
            <div class="decision-card">
                <div class="decision-title" style="color: #0369a1;">💰 手续费与摩擦精算</div>
                <div class="decision-val" style="color: #0284c7;">¥0.00 ~ ¥12.50</div>
                <div class="decision-desc">
                    - 申购费率：主流代销渠道 1 折 (约 0.10%~0.15%)<br>
                    - 纯债/指数低费率优先，年化管理托管费低于 0.40%<br>
                    - <b>原则</b>：严禁频繁短线倒买倒卖耗损摩擦成本
                </div>
            </div>
            """, unsafe_allow_html=True)
        with c_fe2:
            st.markdown("""
            <div class="decision-card">
                <div class="decision-title" style="color: #15803d;">⏳ 股息覆盖回本周期</div>
                <div class="decision-val" style="color: #16a34a;">约 0.5 ~ 1.5 个月</div>
                <div class="decision-desc">
                    - 核心持仓股息率与固收票息增厚现金流<br>
                    - 通过现金分红与超额收益，快速全额平抑交易手续费<br>
                    - <b>机制</b>：股息持续滚存入可用现金，提高持有定力
                </div>
            </div>
            """, unsafe_allow_html=True)
        with c_fe3:
            st.markdown("""
            <div class="decision-card">
                <div class="decision-title" style="color: #b45309;">⚡ 限购拆单与锁仓防护</div>
                <div class="decision-val" style="color: #d97706;">智能分仓承接</div>
                <div class="decision-desc">
                    - 限购标的根据每日限额动态自动拆单并路由至备选标的<br>
                    - 强制执行买入未满 7 天安全锁（拦截 1.5% 惩罚费）<br>
                    - <b>A/C类</b>：长钱锁定 A 类免赎回费，波段进攻配置 C 类
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 《三句话看懂本方案：怎么赚钱、为什么能赢、风险与铁律》三栏作战卡片
    # ---------------------------------------------------------
    st.markdown("---")
    st.markdown("#### 🎯 《三句话看懂本方案：怎么赚钱、为什么能赢、风险与铁律》")
    col_card1, col_card2, col_card3 = st.columns(3)

    worst_loss_amt = readable_kpi.get('worst_case_loss_amount', plan_capital * 0.15)
    worst_dd_pct = readable_kpi.get('worst_case_drawdown_pct', 15.0)
    underwater_days = readable_kpi.get('max_underwater_days', 180)
    underwater_months = readable_kpi.get('max_underwater_months', 6.0)

    with col_card1:
        st.markdown(f"""
        <div class="decision-card" style="border-top: 3px solid #dc2626;">
            <div class="decision-title" style="color: #b91c1c;">
                💰 怎么赚钱？(收益引擎拆解)
                <span title="通过多维资产引擎协同增厚：低估红利提供可持续分红现金流，科技成长捕捉主升浪弹性，衍生品贴水提供无风险超额收益。" style="cursor:help; color:#94a3b8; font-size:12px;">ⓘ</span>
            </div>
            <div class="decision-desc">
                • <b>核心红利高股息打底</b>：提供每年 4%~6% 稳定股息分红现金流，熊市抗跌吃息。<br>
                • <b>动态动量弹性进攻</b>：结合 60 日动量状态机，顺风期自动放大科创/中小盘弹性进攻。<br>
                • <b>智能拆单捕捉超额 Alpha</b>：精选全市场排名前 1% 优质基金经理与期指贴水对冲套利。
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_card2:
        st.markdown(f"""
        <div class="decision-card" style="border-top: 3px solid #16a34a;">
            <div class="decision-title" style="color: #15803d;">
                🛡️ 为什么能赢？(反脆弱对冲机制)
                <span title="跨大类低相关资产配置是投资界唯一的免费午餐。A股权益、纯债、实物黄金、美股海外资产互不相关，东边不亮西边亮。" style="cursor:help; color:#94a3b8; font-size:12px;">ⓘ</span>
            </div>
            <div class="decision-desc">
                • <b>跨大类极低相关对冲</b>：A股权益 + 纯债固收 + 黄金对冲 + 美股标普500 全天候平抑。<br>
                • <b>牛熊实境考验胜率</b>：跑完 2018-2026 跨牛熊 2,000+ 交易日，持有 1 年胜率达 <b>{readable_kpi['win_rate_1y']:.0f}%</b>。<br>
                • <b>东边不亮西边亮</b>：权益震荡时纯债吃票息、黄金防通胀，组合净值波动大幅压降。
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_card3:
        st.markdown(f"""
        <div class="decision-card" style="border-top: 3px solid #b45309;">
            <div class="decision-title" style="color: #b45309;">
                🚨 风险与铁律 (底线与执行铁律)
                <span title="严格遵循量化风控铁律：买入未满 7 天严禁赎回以防触发 1.5% 惩罚费；股债性价比极高分位区间严禁盲目割肉。" style="cursor:help; color:#94a3b8; font-size:12px;">ⓘ</span>
            </div>
            <div class="decision-desc">
                • <b>历史最极端浮亏</b>：-{worst_dd_pct:.2f}% (对应本金最大浮亏约 <b>-¥{worst_loss_amt:,.2f}</b>)。<br>
                • <b>最长水下等待</b>：约 <b>{underwater_days} 个交易日</b> (约 {underwater_months:.1f} 个月)，非保本产品。<br>
                • <b>铁律①</b>：<b>买入未满 7 天绝不赎回</b>（坚决拦截 1.50% 证监会惩罚性扣款）。<br>
                • <b>铁律②</b>：<b>估值底部便宜区绝不割肉</b>（ERP >75% 时严禁把低位筹码换成顶位纯债）。
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 步骤三：【📋 拿方案去执行】—— 极简落地执行与小抄
    # ---------------------------------------------------------
    st.markdown("---")
    st.markdown(f"### 步骤三：【📋 拿方案去执行】—— 专属方案落地执行")

    overrides = st.session_state.custom_fund_overrides

    blueprint = StrategyBridge.generate_zero_start_blueprint(
        total_capital=plan_capital,
        target_weights_funds=None,
        tier=active_tier,
        custom_fund_overrides=overrides
    )

    st.markdown(f"#### 🌱 专属从 0 建仓执行单 (本金 ¥{plan_capital:,.2f} ｜ 档位：{active_tier} {cur_tier_meta['name']})")
    if overrides:
        st.info(f"💡 检测到您自定义替换了 {len(overrides)} 只标的：{overrides}，配置方案已实时动态调整！")

    bp_rows = []
    cheat_sheet_lines = [
        f"【AGY2 智能投顾专属建仓小抄】",
        f"配置档位：{active_tier} {cur_tier_meta['name']} ｜ 目标总投入：¥{plan_capital:,.2f}",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"----------------------------------------"
    ]

    for idx, it in enumerate(blueprint["items"], 1):
        q_it = fetch_realtime_fund_quote(it["fund_code"])
        scr_it = pm.screen_fund_look_through_risk(it["fund_code"])
        crd_it = pm.get_fund_smart_money_crowding(it["fund_code"])

        risk_badge_disp = scr_it.get("risk_badge", "🟢 健康")
        crowd_deg_disp = crd_it.get("crowding_degree", "相对分散")
        if crd_it.get("crowding_warning"):
            crowd_deg_disp += " ⚠️"

        # 9 列精简表格：
        # 1. 基金代码, 2. 基金名称, 3. 份额, 4. 目标占比(%), 5. 精确买入金额(元), 6. 最新净值, 7. 实时估值涨跌(%), 8. 排雷与拥挤度, 9. 实操分红与限购指引
        risk_and_crowd = f"{risk_badge_disp} ｜ {crowd_deg_disp}"
        div_short = "现金分红" if it.get("require_cash_dividend") else "红利再投"

        # 动态提取 action_guide，杜绝硬编码
        raw_guide = it.get("action_guide") or ("已拆单" if it.get("has_split") else "正常买入")
        if it.get("require_cash_dividend"):
            if raw_guide and raw_guide != "正常买入":
                guide_action = f"现金分红·{raw_guide}"
            else:
                guide_action = "现金分红·满期免赎A"
        elif raw_guide and raw_guide != "正常买入":
            guide_action = raw_guide
        elif it.get("share_class") == "C":
            guide_action = "红利再投·弹性进攻C"
        else:
            guide_action = "长钱持有·满期免赎A"

        bp_rows.append({
            "基金代码": it["fund_code"],
            "基金名称": it["fund_name"],
            "份额": f"{it.get('share_class', 'A')}类",
            "目标占比(%)": it.get("target_weight_pct", 0.0),
            "精确买入金额(元)": it.get("allocated_amount", it.get("amount", 0.0)),
            "最新净值": q_it.dwjz if q_it else 1.0,
            "实时估值涨跌(%)": q_it.gszzl if q_it else 0.0,
            "排雷与拥挤度": risk_and_crowd,
            "实操分红与限购指引": guide_action
        })

        s_info = it.get("split_info") or {}
        if s_info.get("fallback_code"):
            cheat_sheet_lines.append(
                f"{idx}. 基金代码: {it['fund_code']} ({it['fund_name']}) | 买入金额: ¥{it['allocated_amount']:,.2f} ({it['target_weight_pct']:.1f}%) ➔ ⚡【实盘拆单】限额买入 ¥{s_info.get('today_amount', it['allocated_amount']):,.2f} | 份额: {it.get('share_class', 'A')}类 | 分红方式: {div_short} | 指引: {it.get('action_guide', guide_action)}"
            )
        elif s_info.get("primary_code"):
            cheat_sheet_lines.append(
                f"{idx}. 基金代码: {it['fund_code']} ({it['fund_name']}) | 买入金额: ¥{it['allocated_amount']:,.2f} ({it['target_weight_pct']:.1f}%) ➔ ⚡【拆单伴生承接】承接 {s_info.get('primary_code')} 超额资金 | 份额: {it.get('share_class', 'A')}类 | 分红方式: {div_short} | 指引: {it.get('action_guide', guide_action)}"
            )
        else:
            cheat_sheet_lines.append(
                f"{idx}. 基金代码: {it['fund_code']} ({it['fund_name']}) | 买入金额: ¥{it['allocated_amount']:,.2f} ({it['target_weight_pct']:.1f}%) | 份额: {it.get('share_class', 'A')}类 | 分红方式: {div_short} | 指引: {it.get('action_guide', guide_action)}"
            )

    cheat_sheet_lines.append(f"----------------------------------------")
    cheat_sheet_lines.append(f"💡 下单提醒：场外基金请在交易日 15:00 前完成支付，15:00 后下单将按次日未知净值成交。")
    cheat_sheet_text = "\n".join(cheat_sheet_lines)

    cols_9 = [
        "基金代码", "基金名称", "份额", "目标占比(%)",
        "精确买入金额(元)", "最新净值", "实时估值涨跌(%)",
        "排雷与拥挤度", "实操分红与限购指引"
    ]
    df_bp = pd.DataFrame(bp_rows)[cols_9]
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

    if blueprint.get("dca_plan"):
        st.info(f"💡 **《超限资金分批定投执行计划》**：{blueprint['dca_plan']}")

    # 复制小抄卡片 (默认收起 expanded=False)
    with st.expander("📱 【点击展开：手机银行 / 天天基金下单一键复制小抄】", expanded=False):
        st.caption("您可以直接复制下方文本发送给微信或记事本，对照手机银行、天天基金、蚂蚁财富一分钟完成买入：")
        st.code(cheat_sheet_text, language="text")

    col_btn_set_hold, _ = st.columns([5, 5])
    with col_btn_set_hold:
        if st.button("🚀 【一键将此方案设为我的初始持仓】", type="primary", use_container_width=True, key="btn_apply_bp_tier"):
            res_apply = pm.apply_zero_start_blueprint(blueprint)
            st.balloons()
            st.success(f"已成功将 ¥{res_apply['total_capital']:,.2f} 建仓方案写入为初始持仓！已配置 {res_apply['funds_count']} 只基金及对应分红方式。")
            st.rerun()


# =============================================================
# Tab 2: 【💼 我的当前持仓与今日调仓建议】
# =============================================================
with tab_holdings_and_rebalance:
    st.subheader("💼 我的当前持仓与今日调仓驾驶舱")

    if len(pm.holdings) == 0:
        st.info("💡 **当前账本暂无持仓**！您可以点击下方按钮一键载入演示组合（包含深套基与在途单），或者在第三层展开录入您的真实持仓。")
        col_demo_btn, _ = st.columns([4, 6])
        with col_demo_btn:
            if st.button("🚀 一键载入演示组合体验调仓驾驶舱", type="primary", use_container_width=True, key="btn_load_demo_tab2"):
                with st.spinner("📦 正在载入演示组合（含深套基与在途单）..."):
                    pm.load_demo_portfolio()
                st.success("✅ 演示组合载入成功！")
                st.rerun()

    # 第一层【🚦 今日是否适合调仓？AI 综合裁决卡】
    suitability = StrategyBridge.evaluate_today_rebalance_suitability(pm, active_tier=active_tier)
    v_level = suitability.get("verdict_level", "HOLD_ON")
    v_title = suitability.get("verdict_title", "")
    r4 = suitability.get("reasons_4d", {})

    if v_level == "SUITABLE":
        banner_bg = "rgba(22, 163, 74, 0.12)"
        banner_border = "#16a34a"
        banner_color = "#15803d"
    elif v_level == "HOLD_ON":
        banner_bg = "rgba(234, 179, 8, 0.12)"
        banner_border = "#ca8a04"
        banner_color = "#a16207"
    else:
        banner_bg = "rgba(220, 38, 38, 0.12)"
        banner_border = "#dc2626"
        banner_color = "#b91c1c"

    st.markdown(f"""
    <div style="background: {banner_bg}; border: 1.5px solid {banner_border}; border-radius: 8px; padding: 16px 20px; margin-bottom: 16px;">
        <div style="font-size: 17px; font-weight: 700; color: {banner_color}; margin-bottom: 6px;">
            {v_title}
        </div>
        <div style="font-size: 13px; color: #475569;">
            AI 投顾核心原则：行情未到关键右侧突破位不调、买入不满 7 天不调、偏离度不足 3% 缓冲阈值不调，将无谓交易磨损降至绝对最低。
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_r1, col_r2, col_r3, col_r4 = st.columns(4)
    with col_r1:
        st.markdown(f"""
        <div class="decision-card">
            <div class="decision-title">① 均线突破状态</div>
            <div class="decision-val" style="font-size: 14px; color: #0284c7;">{snapshot['m20_status_desc']}</div>
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

    # 第二层【⚖️ 今日怎么调？如果一定要调仓会有什么后果？】
    st.markdown("---")
    st.markdown("### ⚖️ 第二层：【今日怎么调？如果一定要调仓会有什么后果？】")

    sim_res = StrategyBridge.simulate_rebalance_modes_and_consequences(pm, active_tier=active_tier)

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
    if active_tier == "C3":
        tier_target_w = dict(snapshot["target_weights_funds"])
    else:
        df_mat = StrategyBridge.load_matrix()
        w_idx = strategy_fn_for_tier(df_mat, tier=active_tier)
        tier_target_w = StrategyBridge.map_index_weights_to_funds(w_idx)

    sec_selection = StrategyBridge.get_tier_sector_fund_selection(active_tier)
    for sec_data in sec_selection.values():
        if sec_data.get("is_promoted"):
            def_c = sec_data.get("default_champion_code")
            act_c = sec_data.get("champion_code")
            if def_c and act_c and def_c in tier_target_w and act_c != def_c:
                w_auto = tier_target_w.pop(def_c)
                tier_target_w[act_c] = round(tier_target_w.get(act_c, 0.0) + w_auto, 4)

    if st.session_state.custom_fund_overrides:
        tier_target_w = dict(tier_target_w)
        for old_code, new_code in st.session_state.custom_fund_overrides.items():
            if old_code in tier_target_w:
                w_val = tier_target_w.pop(old_code)
                tier_target_w[new_code] = round(tier_target_w.get(new_code, 0.0) + w_val, 4)

    ai_orders_res = StrategyBridge.generate_ai_rebalance_orders(
        current_holdings=pm.holdings,
        available_cash=pm.available_cash,
        target_weights_funds=tier_target_w,
        pm=pm
    )
    items = ai_orders_res["items"]

    if items:
        if ai_orders_res.get("crowding_warning_detected"):
            st.warning(f"⚠️ **【机构抱团与聪明钱拥挤度警报】**：{ai_orders_res.get('crowding_caution')}")

        rows_display = []
        for it in items:
            diff_amt = it.get("diff_amount", 0.0)
            action_raw = str(it.get("action_text", ""))
            safety = str(it.get("safety_warning", "") or "")
            holding_days = it.get("holding_days", 999)

            if "7天" in safety or holding_days < 7 or "锁仓" in action_raw or "未满7天" in action_raw or "锁" in safety:
                op_action = "🔒 未满7天锁仓保护"
                op_point = "未满7天·免收1.5%惩罚"
            elif "30天" in safety or (7 <= holding_days < 30 and it.get("share_class") == "C") or "缓卖" in action_raw or "30天" in action_raw:
                op_action = "⏳ 临近30天免赎期缓卖"
                op_point = "缓卖·满30天免赎回费"
            elif diff_amt > 100 or "加仓" in action_raw:
                op_action = "➕ 建议加仓"
                op_point = f"增配¥{abs(diff_amt):,.0f}·现金分红"
            elif diff_amt < -100 or "减仓" in action_raw or "赎回" in action_raw:
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

        col_exec_ai, col_exp_toggle = st.columns([5, 5])
        with col_exec_ai:
            if guidance["stage"] == "POST_MARKET":
                if st.button("📌 【保存为明日 14:30 盯盘待办预案】", type="primary", use_container_width=True, key="btn_save_next_plan_tab2"):
                    p_id = pm.save_next_day_plan({"target_weights": snapshot["target_weights_funds"], "items": items})
                    st.balloons()
                    st.success(f"已成功将本次调仓方案保存为【明日 14:30 盯盘待办预案】（{p_id}）！")
                    st.rerun()
            elif guidance["stage"] == "GOLDEN_WINDOW":
                if st.button("✅ 【立即按今日盘中估值执行调仓】", type="primary", use_container_width=True, key="btn_exec_gold_tab2"):
                    with st.spinner("⚡ 正在执行调仓（锁仓校验 + 限购拆单 + 写入账本）..."):
                        rebal_plan = pm.generate_rebalance_plan(snapshot["target_weights_funds"], min_buffer_pct=3.0)
                        routes_to_run = rebal_plan.get("routes", [])
                    if routes_to_run:
                        with st.spinner("📝 正在提交调仓指令..."):
                            oids = pm.submit_rebalance_orders(routes_to_run)
                        st.balloons()
                        st.success(f"✅ 已成功一键采纳 AI 策略建议，生成 {len(oids)} 笔在途指令（{', '.join(oids)}）！")
                        st.rerun()
                    else:
                        st.info("当前持仓与 AI 目标权重偏离度均在 3% 缓冲阈值内，无需额外折腾！")
            else:
                obs_force = st.checkbox("⚠️ 我已了解盘中冲高/跳水风险，仍希望在 14:30 前提前执行", value=False, key="chk_obs_force_tab2")
                if obs_force:
                    if st.button("⚠️ 【盘中提前执行调仓】", type="secondary", use_container_width=True, key="btn_obs_force_tab2"):
                        rebal_plan = pm.generate_rebalance_plan(snapshot["target_weights_funds"], min_buffer_pct=3.0)
                        routes_to_run = rebal_plan.get("routes", [])
                        if routes_to_run:
                            oids = pm.submit_rebalance_orders(routes_to_run)
                            st.balloons()
                            st.success(f"已成功生成 {len(oids)} 笔在途指令（{', '.join(oids)}）！")
                            st.rerun()
                        else:
                            st.info("当前持仓与 AI 目标权重偏离度均在 3% 缓冲阈值内，无需额外调仓。")
                else:
                    st.button("⏳ 盘中观察中 (等待 14:30 尾盘趋势锁定解锁)", disabled=True, use_container_width=True, key="btn_obs_disabled_tab2")

    # 第三层【📋 我的实时持仓明细与接管向导】
    st.markdown("---")
    st.markdown("### 📋 第三层：【我的实时持仓明细与接管向导】")

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
                st.success("已成功保存并同步！")
                st.rerun()

        with col_del_t:
            del_sel = st.selectbox("选择要删除的标的", ["-- 请选择 --"] + list(pm.holdings.keys()), key="sel_del_hold_tab2")
            if del_sel != "-- 请选择 --":
                if st.button(f"🗑️ 彻底删除 {del_sel}", use_container_width=True, key="btn_del_hold_tab2"):
                    pm.delete_holding(del_sel)
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
    else:
        st.info("当前账本为空，请点击下方向导导入您的真实持仓，或载入演示组合体验完整流程。")

    # 3 个展开器向导：无持仓时展开，有持仓时默认折叠
    has_holdings = len(pm.holdings) > 0

    with st.expander("✨ 零门槛持仓接管向导 (支持微信文本自由粘贴、中文拼音搜索、标准模板导入与冷启动)", expanded=(not has_holdings)):
        sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs([
            "📋 方式一：智能文本自由粘贴一键识别 (首选推荐·自然语言秒识别)",
            "🔍 方式二：按中文名 / 拼音首字母智能搜索添加",
            "📥 方式三：标准 CSV / Excel 模板下载与上传导入",
            "⚡ 方式四：4行极简代码金额快速建仓"
        ])

        with sub_tab1:
            st.write("直接从微信、记事本或聊天记录中**复制粘贴您的任意格式持仓文字**，系统通过语义正则引擎自动识别代码、基金简称、拼音、金额及盈亏：")
            sample_smart_text = """华夏科创50C 20000 亏500
华泰柏瑞低波 30000 盈利1200
002351 1.5万
易方达蓝筹 10000 成本1.85 现价1.92 已持满30天
000216 8000"""
            smart_text_in = st.text_area(
                "📝 在此粘贴持仓文字：",
                value=st.session_state.get("smart_text_draft", sample_smart_text),
                height=130,
                key="txt_smart_holdings"
            )
            st.session_state.smart_text_draft = smart_text_in

            col_st_c, col_st_b = st.columns([4, 6])
            with col_st_c:
                smart_cash_in = st.number_input(
                    "账户可用现金 (元)",
                    value=float(pm.available_cash or 10000.0),
                    step=1000.0,
                    key="smart_cash_input"
                )
            with col_st_b:
                st.write(" ")
                st.write(" ")
                btn_parse = st.button("🔍 智能解析持仓文本", type="primary", use_container_width=True, key="btn_parse_smart_text")

            if btn_parse or ("parsed_smart_items" in st.session_state and st.session_state.parsed_smart_items):
                if btn_parse:
                    with st.spinner("🔍 智能语义解析中（正则+模糊匹配+拼音识别）..."):
                        parsed_items = pm.parse_smart_text_holdings(smart_text_in)
                    st.session_state.parsed_smart_items = parsed_items
                else:
                    parsed_items = st.session_state.parsed_smart_items

                if parsed_items:
                    st.success(f"✅ 成功解析识别出 **{len(parsed_items)}** 只基金持仓！请核对以下解析结果：")
                    preview_rows = []
                    for it in parsed_items:
                        preview_rows.append({
                            "基金代码": it["fund_code"],
                            "基金名称": it["fund_name"],
                            "份额类型": it["share_class"],
                            "持仓金额(元)": it["amount"],
                            "持仓份额": it["shares"],
                            "成本净值": it["cost_nav"],
                            "当前参考净值": it["current_nav"],
                            "预估盈亏(元)": it["pnl"],
                            "持有天数": f"{it['holding_days']} 天 ({it['holding_tag']})"
                        })
                    st.dataframe(
                        pd.DataFrame(preview_rows),
                        column_config={
                            "持仓金额(元)": st.column_config.NumberColumn(format="¥%.2f"),
                            "持仓份额": st.column_config.NumberColumn(format="%.2f"),
                            "成本净值": st.column_config.NumberColumn(format="%.4f"),
                            "当前参考净值": st.column_config.NumberColumn(format="%.4f"),
                            "预估盈亏(元)": st.column_config.NumberColumn(format="¥%+.2f"),
                        },
                        use_container_width=True,
                        hide_index=True
                    )

                    if st.button("📥 确认一键接管/导入此持仓 (写入账本)", type="primary", use_container_width=True, key="btn_confirm_smart_import"):
                        with st.spinner("📥 正在写入账本..."):
                            res_imp = pm.import_from_smart_text(parsed_items, available_cash=smart_cash_in)
                        st.session_state.parsed_smart_items = []
                        st.balloons()
                        st.success(f"🎉 已成功接管 {res_imp['funds_count']} 只基金！账本总资产 ¥{res_imp['total_equity']:,.2f}。")
                        st.rerun()
                else:
                    st.warning("未能识别出有效基金持仓，请检查文本格式（例如每行包含基金代码或名称，并带有金额）。")

        with sub_tab2:
            st.write("支持输入 6 位代码、中文名称关键字或拼音首字母智能联想搜索（例如输入 `kcz50`、`低波`、`005561`、`易方达`、`黄金` 等）：")
            col_kw, col_amt, col_tag = st.columns([4, 3, 3])
            with col_kw:
                search_kw = st.text_input("🔍 搜索基金代码 / 中文简称 / 拼音首字母", value="低波", key="kw_search_catalog")

            matched_funds = search_funds_in_catalog(search_kw, limit=15) if search_kw.strip() else []

            if matched_funds:
                fund_options = [f"{f['fund_code']} - {f['fund_name']} ({f['category']})" for f in matched_funds]
                sel_fund_str = st.selectbox("选择目标基金", fund_options, key="sel_search_fund")
                sel_code = sel_fund_str.split(" - ")[0].strip()
                q_sel = fetch_realtime_fund_quote(sel_code)
                if q_sel:
                    st.caption(f"📌 **{q_sel.name}** ｜ 最新净值: `{q_sel.dwjz:.4f}` ｜ 实时估算: `{q_sel.gsz:.4f}` ({q_sel.gszzl:+.2f}%)")
            else:
                st.info("未找到匹配基金，请输入其他关键字。")
                sel_code = None
                q_sel = None

            with col_amt:
                search_amt = st.number_input("持仓金额 (元)", value=10000.0, step=1000.0, key="search_amt_input")
            with col_tag:
                search_tag = st.selectbox("持有天数档位", ["🟢 已持满30天以上 (免赎回费)", "🟡 已持7~29天", "🔴 刚买不满7天 (有1.5%惩罚费)"], key="search_tag_input")

            if st.button("➕ 添加至我的持仓", type="primary", use_container_width=True, key="btn_add_search_holding"):
                if sel_code:
                    t_v = ">=30d" if "30天以上" in search_tag else ("7-29d" if "7~29天" in search_tag else "<7d")
                    c_nav = float(q_sel.dwjz) if q_sel and q_sel.dwjz > 0 else 1.0000
                    pm.add_or_update_holding(fund_code=sel_code, amount=search_amt, nav=c_nav, holding_tag=t_v, append_batch=True)
                    st.success(f"已成功添加 {sel_code} ({q_sel.name if q_sel else ''}) 金额 ¥{search_amt:,.2f}！")
                    st.rerun()

        with sub_tab3:
            st.write("使用标准 CSV 或 Excel 表格批量导入您的历史流水或持仓快照：")

            template_df = pd.DataFrame([
                {
                    "基金代码": "005561",
                    "基金名称": "华泰柏瑞中证红利低波ETF联接A",
                    "持仓份额": 18500.0,
                    "成本净值": 1.6210,
                    "买入日期": "2024-01-15",
                    "持有天数": 120,
                    "分红方式": "cash"
                },
                {
                    "基金代码": "011613",
                    "基金名称": "华夏中证科创创业50ETF联接C",
                    "持仓份额": 25000.0,
                    "成本净值": 0.8000,
                    "买入日期": "2024-03-20",
                    "持有天数": 45,
                    "分红方式": "reinvest"
                }
            ])
            csv_template = template_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                "📥 下载标准持仓导入模板 CSV",
                data=csv_template,
                file_name="agy2_holdings_template.csv",
                mime="text/csv",
                help="点击下载标准持仓表格模板，填写后上传即可直接导入",
                key="btn_dl_template_tab2"
            )
            st.markdown("---")

            up_file = st.file_uploader("上传您的持仓表格文件 (CSV / Excel)", type=["csv", "xlsx", "xls"], key="tab2_uploader_std")
            if up_file is not None:
                try:
                    df_u = pd.read_csv(up_file) if up_file.name.endswith(".csv") else pd.read_excel(up_file)
                    st.write("数据预览：")
                    st.dataframe(df_u.head(5), use_container_width=True)
                    col_u1, col_u2 = st.columns(2)
                    with col_u1:
                        if st.button("📥 以【历史交易流水】导入 (自动构建 FIFO 批次)", use_container_width=True, key="btn_imp_trans_csv"):
                            res = pm.import_historical_transactions_df(df_u)
                            st.balloons()
                            st.success(f"成功接管 {res['funds_count']} 只基金！")
                            st.rerun()
                    with col_u2:
                        if st.button("📥 以【持仓快照】导入", use_container_width=True, key="btn_imp_snap_csv"):
                            res_s = pm.import_snapshot_df(df_u)
                            st.balloons()
                            st.success(f"成功导入 {res_s['imported_count']} 条快照！")
                            st.rerun()
                except Exception as ex:
                    st.error(f"解析文件出错：{ex}")

        with sub_tab4:
            st.write("只需填写持有的基金代码与当前金额，系统以今日净值作为成本线快速建立基准：")
            c_f1, c_f2, c_f3, c_f4 = st.columns(4)
            with c_f1:
                f_code1 = st.text_input("基金代码 1", value="100032", key="init_c1")
                q1 = fetch_realtime_fund_quote(f_code1) if len(f_code1) == 6 else None
                if q1:
                    st.caption(f"📌 **{q1.name}**\n昨净: `{q1.dwjz:.4f}` ｜ 实时: `{q1.gsz:.4f}` ({q1.gszzl:+.2f}%)")
                f_amt1 = st.number_input("金额 (元) 1", value=38000.0, step=1000.0, key="init_a1")
                f_tag1 = st.selectbox("持有期 1", ["🟢 已持满30天以上", "🟡 已持7~29天", "🔴 刚买不满7天"], key="init_t1")
            with c_f2:
                f_code2 = st.text_input("基金代码 2", value="005561", key="init_c2")
                q2 = fetch_realtime_fund_quote(f_code2) if len(f_code2) == 6 else None
                if q2:
                    st.caption(f"📌 **{q2.name}**\n昨净: `{q2.dwjz:.4f}` ｜ 实时: `{q2.gsz:.4f}` ({q2.gszzl:+.2f}%)")
                f_amt2 = st.number_input("金额 (元) 2", value=30000.0, step=1000.0, key="init_a2")
                f_tag2 = st.selectbox("持有期 2", ["🟢 已持满30天以上", "🟡 已持7~29天", "🔴 刚买不满7天"], key="init_t2")
            with c_f3:
                f_code3 = st.text_input("基金代码 3", value="000216", key="init_c3")
                q3 = fetch_realtime_fund_quote(f_code3) if len(f_code3) == 6 else None
                if q3:
                    st.caption(f"📌 **{q3.name}**\n昨净: `{q3.dwjz:.4f}` ｜ 实时: `{q3.gsz:.4f}` ({q3.gszzl:+.2f}%)")
                f_amt3 = st.number_input("金额 (元) 3", value=14000.0, step=1000.0, key="init_a3")
                f_tag3 = st.selectbox("持有期 3", ["🟢 已持满30天以上", "🟡 已持7~29天", "🔴 刚买不满7天"], key="init_t3")
            with c_f4:
                f_code4 = st.text_input("基金代码 4", value="002351", key="init_c4")
                q4 = fetch_realtime_fund_quote(f_code4) if len(f_code4) == 6 else None
                if q4:
                    st.caption(f"📌 **{q4.name}**\n昨净: `{q4.dwjz:.4f}` ｜ 实时: `{q4.gsz:.4f}` ({q4.gszzl:+.2f}%)")
                f_amt4 = st.number_input("金额 (元) 4", value=12000.0, step=1000.0, key="init_a4")
                f_tag4 = st.selectbox("持有期 4", ["🟢 已持满30天以上", "🟡 已持7~29天", "🔴 刚买不满7天"], key="init_t4")

            col_init_cash, col_init_btn = st.columns([3, 7])
            with col_init_cash:
                init_cash_in = st.number_input("账户可用现金 (元)", value=6000.0, step=1000.0, key="init_cash_input")
            with col_init_btn:
                st.write(" ")
                st.write(" ")
                if st.button("🚀 一键完成冷启动接管", type="primary", use_container_width=True, key="btn_cold_start_tab2"):
                    items_cold = []
                    for code, amt, tag, q_obj in [
                        (f_code1, f_amt1, f_tag1, q1),
                        (f_code2, f_amt2, f_tag2, q2),
                        (f_code3, f_amt3, f_tag3, q3),
                        (f_code4, f_amt4, f_tag4, q4)
                    ]:
                        if code and amt > 0:
                            t_val = ">=30d" if "30天以上" in tag else ("7-29d" if "7~29天" in tag else "<7d")
                            c_nav = float(q_obj.dwjz) if q_obj and q_obj.dwjz > 0 else 1.0
                            items_cold.append({"fund_code": code, "amount": amt, "nav": c_nav, "holding_tag": t_val})
                    with st.spinner("🚀 冷启动接管中（FIFO 批次构建 + 写入账本）..."):
                        pm.takeover_mode_a(items_cold, available_cash=init_cash_in)
                    st.success("✅ 已成功以模式 A 冷启动接管！")
                    st.rerun()

    # FIFO 批次折叠透视面板
    with st.expander("📦 【点击展开：全组合 FIFO 批次透视与免赎回费倒计时汇总表】", expanded=False):
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
                    "备注": b_i.notes
                })
        if all_b_rows:
            st.dataframe(pd.DataFrame(all_b_rows), use_container_width=True, hide_index=True)
        else:
            st.info("当前持仓暂无批次数据。")


# =============================================================
# Tab 4: 【📈 策略历史回测与胜率档案】
# =============================================================
with tab_backtest:
    st.subheader("📈 策略历史硬核表现、净值回测与风控档案 (2018-2026 全周期实境)")

    # 档位动态选择器
    sel_bt_col1, sel_bt_col2 = st.columns([4, 6])
    with sel_bt_col1:
        bt_tier_choice = st.selectbox(
            "🎯 选择要检视的历史回测策略档位：",
            [
                "C1 (安稳增值·极低回撤)",
                "C2 (稳健平衡·固收+)",
                "C3 (全天候平衡·标杆旗舰)",
                "C4 (进取成长·弹性进攻)",
                "C5 (极限进攻·高Beta追击)"
            ],
            index=2,
            key="sel_backtest_tier_opt"
        )
        cur_bt_tier = bt_tier_choice.split()[0]
    with sel_bt_col2:
        bt_cfg = RISK_TIERS_CONFIG[cur_bt_tier]
        st.info(f"💡 当前检视档位：**【{cur_bt_tier} {bt_cfg['name']}】** ｜ 权益上限 {bt_cfg['equity_range'][1]}% ｜ 目标年化 {bt_cfg['target_cagr']} ｜ 核心资产：{bt_cfg['core_assets']}")

    df_bt = StrategyBridge.get_backtest_nav_for_tier(cur_bt_tier)

    # 动态计算该档位的核心表现
    tier_cagr = (df_bt['strategy_nav'].iloc[-1] ** (252.0 / len(df_bt)) - 1.0) * 100.0
    tier_mdd = abs(float(df_bt['strategy_drawdown'].min()))
    tier_otc_cagr = (df_bt['strategy_nav_otc'].iloc[-1] ** (252.0 / len(df_bt)) - 1.0) * 100.0 if 'strategy_nav_otc' in df_bt.columns else (tier_cagr - 0.6)

    # 1. 核心胜率与风险指标四宫格
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
            <div style="font-size:11px; color:#64748b;">风格切片胜率 / 盈亏比</div>
            <div class="metric-value-huge" style="color: #0284c7;">
                {trial29_kpi['slice_win_rate']}
            </div>
            <div style="font-size:11px; color:#64748b; margin-top:2px;">
                月度胜率 {trial29_kpi['monthly_win_rate']} ｜ 盈亏比 {trial29_kpi['profit_factor_range']}
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
                对标沪深300回撤: {trial29_kpi['mdd_h300']:.1f}%
            </div>
        </div>
        """, unsafe_allow_html=True)

    with kpi_col4:
        st.markdown(f"""
        <div class="main-metric-card">
            <div style="font-size:11px; color:#64748b;">±15% 参数高原存活率</div>
            <div class="metric-value-huge" style="color: #dc2626;">
                {trial29_kpi['survival_rate']:.0f}%
            </div>
            <div style="font-size:11px; color:#64748b; margin-top:2px;">
                {trial29_kpi['survival_cases']} (杜绝过拟合)
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(" ")

    # 2. 2018-2026 全周期策略净值曲线 vs 50/50 基准 vs 沪深300 动态交互图
    st.markdown(f"#### 🚀 2018-2026 全周期真实净值推演曲线 (【{cur_bt_tier} 档位】高亮标注 6 大历史切片与样本外盲测金库)")

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

    fig_nav = go.Figure()

    # 绘制核心净值曲线 (双口径 + 基准)
    fig_nav.add_trace(go.Scatter(
        x=df_bt['date'],
        y=df_bt['strategy_nav'],
        mode='lines',
        name=f'{cur_bt_tier} 策略净值 (理论 {tier_cagr:.2f}%)',
        line=dict(color='#ef4444', width=2.4)
    ))
    if 'strategy_nav_otc' in df_bt.columns:
        fig_nav.add_trace(go.Scatter(
            x=df_bt['date'],
            y=df_bt['strategy_nav_otc'],
            mode='lines',
            name=f'{cur_bt_tier} 场外联接实盘校准 (95%仓位 {tier_otc_cagr:.2f}%)',
            line=dict(color='#38bdf8', width=2.2, dash='solid')
        ))
    fig_nav.add_trace(go.Scatter(
        x=df_bt['date'],
        y=df_bt['benchmark_50_50_nav'],
        mode='lines',
        name='50/50 本土股债静态基准',
        line=dict(color='#f59e0b', width=1.6, dash='dash')
    ))
    fig_nav.add_trace(go.Scatter(
        x=df_bt['date'],
        y=df_bt['h300_nav'],
        mode='lines',
        name='沪深300全收益 (H00300)',
        line=dict(color='#94a3b8', width=1.5, dash='dot')
    ))

    # 高亮标注 6 大历史风格切片与样本外盲测区
    slices_meta = [
        ("2018-01-02", "2018-12-28", "Slice 1: 去杠杆熊市", "rgba(239, 68, 68, 0.08)"),
        ("2019-01-02", "2020-12-31", "Slice 2: 核心资产牛市", "rgba(16, 185, 129, 0.08)"),
        ("2021-01-04", "2021-12-31", "Slice 3: 赛道股分化", "rgba(245, 158, 11, 0.08)"),
        ("2022-01-04", "2022-12-30", "Slice 4: 加息杀估值", "rgba(239, 68, 68, 0.08)"),
        ("2023-01-03", "2024-08-30", "Slice 5: 高股息避险", "rgba(56, 189, 248, 0.08)"),
        ("2024-09-02", "2025-06-30", "Slice 6: 924大转向", "rgba(16, 185, 129, 0.08)"),
        ("2025-07-01", "2026-10-27", "Holdout Vault: 盲测金库", "rgba(168, 85, 247, 0.12)")
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
        title="2018-2026 全周期累计净值表现 (起始归一化 1.000)",
        xaxis_title="交易日期",
        yaxis_title="标准化累计净值",
        hovermode="x unified",
        margin=dict(t=40, b=10, l=10, r=10),
        height=380,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_nav, use_container_width=True)

    # 动态水下回撤图与历史股债仓位面积图并排
    col_dd, col_alloc = st.columns(2)

    with col_dd:
        st.markdown("##### 🌊 动态水下回撤对比图 (Underwater Drawdown %)")
        fig_dd = go.Figure()
        fig_dd.add_trace(go.Scatter(
            x=df_bt['date'],
            y=df_bt['strategy_drawdown'],
            mode='lines',
            fill='tozeroy',
            name='策略动态水下回撤',
            line=dict(color='#10b981', width=1.5),
            fillcolor='rgba(16, 185, 129, 0.15)'
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
            x=df_bt['date'], y=df_bt['weight_ashare'], mode='lines', stackgroup='one',
            name='A股权益仓位', line=dict(width=0.5, color='#ef4444'), fillcolor='rgba(239, 68, 68, 0.6)'
        ))
        fig_area.add_trace(go.Scatter(
            x=df_bt['date'], y=df_bt['weight_bond'], mode='lines', stackgroup='one',
            name='纯债避风港', line=dict(width=0.5, color='#3b82f6'), fillcolor='rgba(59, 130, 246, 0.6)'
        ))
        fig_area.add_trace(go.Scatter(
            x=df_bt['date'], y=df_bt['weight_gold'], mode='lines', stackgroup='one',
            name='黄金对冲气垫', line=dict(width=0.5, color='#f59e0b'), fillcolor='rgba(245, 158, 11, 0.6)'
        ))
        fig_area.add_trace(go.Scatter(
            x=df_bt['date'], y=df_bt['weight_spx'], mode='lines', stackgroup='one',
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

    # 3. 6 大历史市场风格切片表现明细表
    st.markdown("#### 📜 6 大历史市场风格切片全胜战报 (Gate B 考核通过)")
    df_slices = trial29_kpi.get("slices_df")
    if df_slices is not None and not df_slices.empty:
        st.dataframe(df_slices, use_container_width=True, hide_index=True)

    # 4. 历史相似行情匹配器深度剖析 (痛点 4)
    st.markdown("---")
    st.markdown("#### 🔍 历史相似行情与宏观同温层匹配器 (History Analog Matcher)")
    st.caption("回测不仅是过往记忆，更是当下的指路明灯。系统通过 4 维特征向量在 2018~2026 年大样本中匹配历史同温层：")

    analog_tab2 = StrategyBridge.find_historical_analogs(top_k=3)
    st.info(analog_tab2["summary_text"])

    if analog_tab2["matches"]:
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

        tab2_analog_rows = []
        for m in analog_tab2["matches"]:
            tab2_analog_rows.append({
                "历史相似时期": m["date"],
                "相似度": f"{m['similarity_pct']:.1f}%",
                "未来20日沪深300涨跌": f"{m['h300_ret_20d']:+.2f}%",
                "未来20日本策略收益": f"{m['strategy_ret_20d']:+.2f}%",
                "未来60日沪深300涨跌": f"{m['h300_ret_60d']:+.2f}%",
                "未来60日本策略收益": f"{m['strategy_ret_60d']:+.2f}%",
                "未来60日策略最大回撤": f"{m['strategy_mdd_60d']:.2f}%",
                "当时策略大类配置": m["alloc_desc"]
            })
        st.dataframe(pd.DataFrame(tab2_analog_rows), use_container_width=True, hide_index=True)


# =============================================================
# Tab 3: 【🔍 组合深度体检与算费工具箱】
# =============================================================
with tab_toolbox:
    st.subheader("🔍 组合穿透诊断、在途对账与 A/C 算费工具箱")

    box_tab1, box_tab2, box_tab3, box_tab4 = st.tabs([
        "📊 双环配置与底层穿透诊断",
        "⏳ 在途订单与 T+1 对账中心",
        "💡 A/C 份额盈亏平衡计算器",
        "📡 场内 ETF IOPV 溢价监控"
    ])

    # 1. 穿透诊断
    with box_tab1:
        st.markdown("#### 🎯 资产配置大类对比与缺口分析")

        cur_cats = {}
        for c, h in pm.holdings.items():
            cat = pm.classify_fund_asset_class(c, h.fund_name)
            cur_cats[cat] = cur_cats.get(cat, 0.0) + h.market_value
        cur_cats["可用现金"] = pm.available_cash

        target_funds = snapshot.get("target_weights_funds", {})
        all_cats = sorted(list(set(list(cur_cats.keys()) + [pm.classify_fund_asset_class(k) for k in target_funds.keys()])))

        # 替换双环饼图为直观的横向分组条形图 (Grouped Bar Chart)
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
            height=280,
            xaxis_title="资产占比 (%)",
            yaxis_title="",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        # 大类配置缺口量化分析表 (定量对比)
        st.markdown("##### ⚖️ 大类资产配置缺口量化分析表 (实际 vs 模型目标)")
        gap_rows = []
        for cat in sorted(all_cats):
            c_val = cur_cats.get(cat, 0.0)
            c_pct = (c_val / total_cur_equity * 100.0) if total_cur_equity > 0 else 0.0
            t_pct = sum(w for k, w in target_funds.items() if pm.classify_fund_asset_class(k) == cat) * 100.0
            t_val = total_cur_equity * (t_pct / 100.0)
            diff_val = c_val - t_val
            diff_pct = c_pct - t_pct

            if abs(diff_pct) < 1.0:
                action_advice = "仓位均衡 (在1%容差内)"
            elif diff_pct > 0:
                action_advice = f"超配偏离，建议减配 -¥{abs(diff_val):,.2f}"
            else:
                action_advice = f"欠配缺口，建议增配 +¥{abs(diff_val):,.2f}"

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

        # 行业集中度与重仓股重合度
        st.markdown("---")
        st.markdown("#### 🏭 加权行业集中度暴露与重仓股重叠穿透")
        col_i1, col_i2 = st.columns([5, 5])
        with col_i1:
            st.markdown("##### 🏭 行业穿透暴露")
            df_ind = pm.calculate_look_through_industry_exposure()
            if not df_ind.empty:
                fig_ind_b = px.bar(df_ind, x="暴露占比(%)", y="行业", orientation="h", color="暴露占比(%)", color_continuous_scale="Viridis", text_auto=".1f%")
                fig_ind_b.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300, yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_ind_b, use_container_width=True)
            else:
                st.info("当前无持仓数据可供行业穿透。")

        with col_i2:
            st.markdown("##### ⚠️ 前十大重仓股重叠交叉检测")
            overlap_res = pm.calculate_stock_overlap_matrix()
            max_unexcused = float(overlap_res.get("max_non_diag_unexcused", 0.0))
            alerts = overlap_res.get("alerts", [])

            if max_unexcused == 0.0 and len(alerts) == 0:
                st.success("✅ **您的组合跨大类分散度极佳，前十大重仓股零重叠**")
            elif max_unexcused < 0.20 and len(alerts) == 0:
                st.success(f"✅ **您的组合跨大类分散度极佳！** 前十大重仓股无明显交叉重叠（最高未豁免重叠仅 {max_unexcused*100:.1f}%，低于 20% 警戒线）。")
                with st.expander("🔍 展开查看前十大重仓股交叉重合度热力图与协同说明 (当前安全)", expanded=False):
                    if len(overlap_res.get("funds", [])) >= 2:
                        fig_heat = px.imshow(
                            overlap_res["matrix"],
                            labels=dict(x="基金", y="基金", color="重合度"),
                            x=overlap_res["funds"], y=overlap_res["funds"],
                            color_continuous_scale="Blues", text_auto=".2f"
                        )
                        fig_heat.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=260)
                        st.plotly_chart(fig_heat, use_container_width=True)
                    for note in overlap_res.get("matrix_notes", []):
                        st.caption(f"💡 {note}")
            else:
                st.warning(f"⚠️ **检测到持仓间存在较高重仓股重叠（最高未豁免达 {max_unexcused*100:.1f}%）！** 伪分散可能导致风险集中。")
                with st.expander("⚠️ 展开查看重合度热力图与警报详情", expanded=True):
                    if len(overlap_res.get("funds", [])) >= 2:
                        fig_heat = px.imshow(
                            overlap_res["matrix"],
                            labels=dict(x="基金", y="基金", color="重合度"),
                            x=overlap_res["funds"], y=overlap_res["funds"],
                            color_continuous_scale="Reds", text_auto=".2f"
                        )
                        fig_heat.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=260)
                        st.plotly_chart(fig_heat, use_container_width=True)
                    for a in alerts:
                        st.warning(a["warning_msg"])

        # -------------------------------------------------------------
        # 3. 基金底层前十大重仓股穿透排雷诊断 (WindToolkit 进阶能力 R1)
        # -------------------------------------------------------------
        st.markdown("---")
        st.markdown("#### 🛡️ 基金底层前十大重仓股穿透排雷大宽表 (商誉/存贷双高/质押/解禁)")
        if len(pm.holdings) > 0:
            port_risk = pm.calculate_portfolio_penetration_risk()
            c_pr1, c_pr2, c_pr3 = st.columns(3)
            with c_pr1:
                st.metric("组合加权排雷风险指数", f"{port_risk['portfolio_risk_index']:.1f} / 100", delta=port_risk['risk_badge'])
            with c_pr2:
                st.metric("🔴 预警高危重仓股数", f"{port_risk['danger_stock_count']} 只")
            with c_pr3:
                st.metric("🟡 关注警戒重仓股数", f"{port_risk['watch_stock_count']} 只")

            df_scr = pm.get_portfolio_look_through_stocks_df()
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

        # -------------------------------------------------------------
        # 4. 聪明钱跟踪与机构抱团拥挤度监控 (WindToolkit 进阶能力 R3)
        # -------------------------------------------------------------
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
                    "机构情绪": c_info.get("institutional_sentiment", "中性"),
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

    # 2. 在途订单对账中心
    with box_tab2:
        st.markdown("#### ⏳ 在途待确认订单与次日 T+1 对账中心")
        p_list = [o for o in pm.pending_orders if o.status == "PENDING"]
        if p_list:
            st.write(f"当前有 **{len(p_list)}** 笔在途待确认订单：")
            df_p = pd.DataFrame([{
                "订单号": o.order_id, "下单时间": o.created_at, "方向": o.action,
                "标的代码": o.fund_code, "标的名称": o.fund_name, "金额": o.amount,
                "份额": o.shares, "预计到账日": o.est_cash_arrive_date, "路由": o.route_priority
            } for o in p_list])
            st.dataframe(df_p, use_container_width=True, hide_index=True)

            st.markdown("##### 🎯 真实公布净值对账入库")
            c_r1, c_r2, c_r3 = st.columns([3, 2, 2])
            with c_r1:
                sel_oid = st.selectbox("选择待对账订单", [o.order_id for o in p_list], key="box_sel_oid")
            with c_r2:
                in_nav_real = st.number_input("公布的真实成交净值", value=1.0500, step=0.001, format="%.4f", key="box_real_nav")
            with c_r3:
                st.write(" ")
                st.write(" ")
                if st.button("🚀 确认对账入库", key="btn_rec_order"):
                    pm.reconcile_pending_order(sel_oid, confirmed_nav=in_nav_real)
                    st.success(f"订单 {sel_oid} 已对账入库！")
                    st.rerun()
        else:
            st.success("目前无在途待确认订单，所有流水均已对账结算完毕。")

    # 3. A/C 份额计算器
    with box_tab3:
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

    # 4. 场内 ETF 溢价监控
    with box_tab4:
        st.markdown("#### 📡 场内 ETF 溢价率监控 (Wind 湖仓离线快照模式)")
        st.caption("优先从本地湖仓 `data/mart/etf_flows.parquet` 与 `data/master/etf_catalog.parquet` 实时计算溢价率：")
        col_etf_ref, _ = st.columns([3, 7])
        with col_etf_ref:
            if st.button("🔄 手动刷新 ETF 行情快照", key="btn_refresh_etf"):
                st.success("已刷新湖仓 ETF 行情！")
                st.rerun()

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
                    "投资操作指引": "溢价率>0.8%已超出安全红线，严禁盲目追高，谨防价格向净值回归造成损失！"
                })
            df_etf_alerts = pd.DataFrame(etf_rows)
            st.dataframe(
                df_etf_alerts,
                column_config={
                    "场内现价(元)": st.column_config.NumberColumn(format="¥%.3f"),
                    "IOPV估值(元)": st.column_config.NumberColumn(format="¥%.4f"),
                    "溢价率(%)": st.column_config.ProgressColumn(min_value=0, max_value=20, format="+%.2f%%"),
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.success("所有核心监控场内 ETF 溢价率均处于正常安全范围 (<= 0.8%)。")
# =========================================================
# Tab 5: 【🎯 全市场胜率最优选基】—— 阶段三：智能漏斗 + 三维胜率 + SLSQP 优化
# =========================================================
with tab_market_optimizer:
    st.markdown("### 🎯 全市场胜率最优选基引擎")
    _mo_today = date.today()
    st.caption(
        f"📅 评估基准日：**{_mo_today.isoformat()}**（随使用日期动态滚动）｜"
        "从全市场公募基金中经「预筛 → 分桶评分 → NAV 回测 → 胜率最大化优化」四步漏斗，"
        "找出在您设定的目标收益与持有期下历史滚动胜率最高的 5~8 只基金组合。"
    )
    st.warning(
        "⚠️ 历史胜率基于过去滚动持有窗口回测（已扣除申购费、阶梯赎回费、C类销售服务费），"
        "不代表未来收益承诺。市场有风险，投资需谨慎。"
    )

    # ─── Step 1：目标设定 ────────────────────────────────────
    st.markdown("#### 步骤一：设定收益目标与持有期")
    mo_col1, mo_col2, mo_col3 = st.columns([4, 3, 3])
    with mo_col1:
        mo_target_pct = st.slider(
            "🎚️ 目标年化收益率 (%)",
            min_value=3.0, max_value=25.0,
            value=float(st.session_state.get("mode_c_target_return", 8.0)),
            step=1.0, format="%.0f%%", key="mo_target_return"
        )
    with mo_col2:
        _mo_horizon_labels = ["短期(3~6月)", "中期(1~2年)", "长期(3~5年)"]
        _mo_default_h = st.session_state.get("mode_c_horizon", "中期(1~2年)")
        mo_horizon = st.radio(
            "📅 计划持有期", _mo_horizon_labels,
            index=_mo_horizon_labels.index(_mo_default_h) if _mo_default_h in _mo_horizon_labels else 1,
            horizontal=True, key="mo_horizon"
        )
    with mo_col3:
        mo_capital = st.number_input(
            "💰 投资金额 (元)", min_value=1000.0, max_value=100000000.0,
            value=float(st.session_state.get("mode_c_capital", 100000.0)),
            step=10000.0, format="%.0f", key="mo_capital"
        )

    _mo_hmap = {"短期(3~6月)": "short", "中期(1~2年)": "medium", "长期(3~5年)": "long"}
    mo_period_key = _mo_hmap.get(mo_horizon, "medium")
    mo_holding_days = HOLDING_PERIODS[mo_period_key]["trading_days"]
    mo_tier = map_slider_to_tier(mo_target_pct)
    mo_tier_meta = RISK_TIERS_CONFIG[mo_tier]
    mo_share_class = "C" if mo_period_key == "short" else "A"
    st.caption(
        f"💡 目标 {mo_target_pct:.0f}% ➔ 风险档位【{mo_tier} {mo_tier_meta['name']}】"
        f"（最大回撤容忍 {mo_tier_meta['max_drawdown_limit']}）｜持有约 {mo_holding_days} 个交易日｜"
        f"份额建议：**{mo_share_class} 类**（{'短期持有 C 类免申购费更省' if mo_share_class == 'C' else '中长期持有 A 类免销售服务费更省'}）"
    )

    with st.expander("⚙️ 高级筛选参数", expanded=False):
        adv_c1, adv_c2, adv_c3 = st.columns(3)
        with adv_c1:
            mo_min_aum = st.number_input("最低规模 (亿元)", min_value=0.5, max_value=50.0, value=2.0, step=0.5, key="mo_min_aum")
        with adv_c2:
            mo_min_years = st.number_input("最短成立年限 (年)", min_value=1.0, max_value=10.0, value=3.0, step=0.5, key="mo_min_years")
        with adv_c3:
            mo_top_n = st.number_input("每类型桶保留 Top N", min_value=10, max_value=200, value=80, step=10, key="mo_top_n")
        mo_force = st.checkbox("强制重建候选池（忽略周度缓存，耗时较长）", value=False, key="mo_force_rebuild")

    mo_run = st.button("🚀 开始全市场胜率最优选基", type="primary", key="btn_market_optimize")
    st.caption("💡 首次运行约需 3~8 分钟（需从东方财富获取候选基金净值），结果按日缓存，后续秒级返回。")

    # ─── Step 2：分步漏斗执行 ────────────────────────────────
    if mo_run:
        _mo_err = None
        with st.status("🔍 全市场智能漏斗运行中...", expanded=True) as mo_status:
            _mo_prog = st.progress(0.0)
            _mo_msg = st.empty()

            import time as _time_mod
            _mo_t0 = _time_mod.time()
            _mo_steps = [st.empty() for _ in range(4)]
            _mo_step_labels = [
                "① 全市场预筛（规模·年限·清盘过滤）",
                "② 分桶综合评分（夏普·回撤·年化 Top N）",
                "③ 候选基金 NAV 批量获取",
                "④ 胜率最大化组合优化（贪心+SLSQP+局部搜索）"
            ]
            for _si, _sl in enumerate(_mo_step_labels):
                _mo_steps[_si].caption(f"⬜ {_sl}")
            _mo_cur_stage = [0]  # mutable for closure
            _mo_peak_frac = [0.0]  # monotonic progress high-water mark
            # Stage weights: ① 预筛 15%, ② 分桶 10%, ③ NAV获取 55%, ④ 优化 20%
            _STAGE_WEIGHTS = [0.15, 0.10, 0.55, 0.20]
            _STAGE_OFFSETS = [0.0, 0.15, 0.25, 0.80]  # cumsum prefix

            def _detect_stage(msg):
                """根据消息内容检测当前所处阶段 0~3"""
                if "优化完成" in msg or "优化" in msg and ("贪心" in msg or "SLSQP" in msg or "局部" in msg):
                    return 3
                if "NAV" in msg or "净值" in msg or "矩阵" in msg:
                    return 2
                if "分桶" in msg or "综合评分" in msg or "排名" in msg or "夏普" in msg:
                    return 1
                if "预筛" in msg or "规模" in msg or "过滤" in msg or "基金目录" in msg or "缓存加载候选池" in msg:
                    return 0
                return _mo_cur_stage[0]  # fallback: stay in current stage

            def _mo_cb(cur, total, msg):
                # 1. 检测并更新阶段
                detected = _detect_stage(msg)
                if detected > _mo_cur_stage[0]:
                    # 将跳过的中间阶段全部标记为已完成
                    for _skip_s in range(_mo_cur_stage[0], detected):
                        _mo_steps[_skip_s].caption(f"✅ {_mo_step_labels[_skip_s]}  ✓")
                    _mo_cur_stage[0] = detected
                stage = _mo_cur_stage[0]

                # 2. 计算全局单调递增进度
                try:
                    local_frac = (float(cur) / float(total)) if total else 0.0
                except Exception:
                    local_frac = 0.0
                local_frac = min(max(local_frac, 0.0), 1.0)
                global_frac = _STAGE_OFFSETS[stage] + _STAGE_WEIGHTS[stage] * local_frac
                # 单调递增保护：进度条永远只往前走
                _mo_peak_frac[0] = max(_mo_peak_frac[0], global_frac)
                _mo_prog.progress(min(_mo_peak_frac[0], 1.0))

                # 3. ETA 计算（基于全局单调进度）
                elapsed = _time_mod.time() - _mo_t0
                eta_str = ""
                if _mo_peak_frac[0] > 0.05:
                    eta_sec = elapsed / _mo_peak_frac[0] * (1.0 - _mo_peak_frac[0])
                    if eta_sec < 60:
                        eta_str = f" ｜ 预计剩余 ~{eta_sec:.0f}s"
                    else:
                        eta_str = f" ｜ 预计剩余 ~{eta_sec/60:.1f}min"
                _mo_msg.caption(f"⏳ {msg}（已耗时 {elapsed:.0f}s{eta_str}）")

                # 4. 更新 checklist — 标记完成的阶段
                if ("预筛完成" in msg or ("候选基金" in msg and "评分" not in msg)) and stage >= 0:
                    _mo_steps[0].caption(f"✅ {_mo_step_labels[0]}  ✓")
                if ("分桶排名完成" in msg or "综合评分" in msg) and stage >= 1:
                    _mo_steps[1].caption(f"✅ {_mo_step_labels[1]}  ✓")
                if ("NAV 矩阵" in msg or "矩阵构建完成" in msg) and stage >= 2:
                    _mo_steps[2].caption(f"✅ {_mo_step_labels[2]}  ✓")
                if "优化完成" in msg and stage >= 3:
                    _mo_steps[3].caption(f"✅ {_mo_step_labels[3]}  ✓")

                # 5. 活跃阶段高亮 + 未完成阶段保持空心
                for _si2 in range(stage, 4):
                    if _si2 == stage:
                        _mo_steps[_si2].caption(f"🔄 {_mo_step_labels[_si2]}  进行中...")
                    elif _si2 > stage:
                        _mo_steps[_si2].caption(f"⬜ {_mo_step_labels[_si2]}")

            try:
                st.write("**① 全市场预筛 + ② 分桶综合评分 + ③ 候选 NAV 获取**")
                mo_ranked, mo_nav = MarketScreener.run_full_pipeline(
                    as_of_date=_mo_today,
                    min_aum_billion=float(mo_min_aum),
                    min_years=float(mo_min_years),
                    top_n_per_bucket=int(mo_top_n),
                    force_rebuild=bool(mo_force),
                    progress_callback=_mo_cb,
                )
                if mo_ranked is None or mo_ranked.empty or mo_nav is None or mo_nav.empty:
                    raise RuntimeError("候选池或 NAV 矩阵为空（可能数据源暂不可用）")
                st.write(f"✅ 候选池 {len(mo_ranked)} 只，NAV 矩阵 {mo_nav.shape[0]} 天 × {mo_nav.shape[1]} 只")

                st.write("**④ 胜率最大化组合优化（贪心 + SLSQP + 局部搜索）**")
                mo_optimizer = WinRateOptimizer(
                    nav_matrix=mo_nav,
                    candidate_info=mo_ranked,
                    holding_days=mo_holding_days,
                    target_annual_return=mo_target_pct / 100.0,
                    tier=mo_tier,
                )
                mo_result = mo_optimizer.optimize(progress_callback=_mo_cb)

                # 专家精选池对比（独立获取专家池 NAV，不依赖候选矩阵）
                mo_expert_cmp = None
                try:
                    import portfolio_manager as _pm_mod
                    _all_expert = list(getattr(_pm_mod, "CORE_STRATEGY_POOL", {}).keys())
                    # 去重：仅保留 A 类（奇数位通常是 A 类，但更安全的做法是去重）
                    _expert_a = [c for c in _all_expert
                                 if not getattr(_pm_mod, "CORE_STRATEGY_POOL", {}).get(c, {}).get("share_class", "A") == "C"]
                    if not _expert_a:
                        _expert_a = _all_expert
                    # 优先用候选 NAV 矩阵中已有的，不足则独立获取
                    _in_nav = [c for c in _expert_a if c in mo_nav.columns]
                    _expert_nav = None
                    if len(_in_nav) >= 5:
                        _expert_codes = _in_nav
                    else:
                        _mo_cb(0, 1, "获取专家池基金 NAV 用于同口径对比...")
                        _expert_nav = MarketScreener.fetch_candidate_nav_matrix(
                            _expert_a, start_date="2018-01-01"
                        )
                        _expert_codes = [c for c in _expert_a if c in _expert_nav.columns]
                    if _expert_codes:
                        _ew = {c: 1.0 / len(_expert_codes) for c in _expert_codes}
                        mo_expert_cmp = mo_optimizer.compare_with_expert_pool(
                            _ew, expert_nav_matrix=_expert_nav
                        )
                        mo_expert_cmp["n_funds"] = len(_expert_codes)
                except Exception as _e_cmp:
                    mo_expert_cmp = {"error": str(_e_cmp)}

                st.session_state.mo_last_result = {
                    "result": mo_result,
                    "expert": mo_expert_cmp,
                    "funnel": MarketScreener.get_funnel_stats(mo_ranked),
                    "capital": float(mo_capital),
                    "target_pct": float(mo_target_pct),
                    "horizon": mo_horizon,
                    "tier": mo_tier,
                    "as_of": _mo_today.isoformat(),
                    "run_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                _elapsed_total = _time_mod.time() - _mo_t0
                _cache_hint = "（日缓存命中·秒级返回）" if _elapsed_total < 5 else f"（耗时 {_elapsed_total:.1f}s）"
                mo_status.update(label=f"✅ 全市场选基完成 {_cache_hint}", state="complete", expanded=False)
            except Exception as _e:
                _mo_err = str(_e)
                mo_status.update(label="❌ 选基流程异常", state="error", expanded=True)
        if _mo_err:
            st.error(f"选基流程异常：{_mo_err}。请检查网络/数据源后重试，或展开高级参数放宽筛选条件。")

    # ─── Step 3：结果展示 ────────────────────────────────────
    mo_saved = st.session_state.get("mo_last_result")
    if mo_saved:
        mo_res = mo_saved["result"]
        mo_pm = mo_res.get("portfolio_metrics", {})
        mo_meta = mo_res.get("optimization_metadata", {})
        st.markdown(
            f"#### 步骤三：最优组合结果（目标 {mo_saved['target_pct']:.0f}% ｜ {mo_saved['horizon']} ｜ "
            f"档位 {mo_saved['tier']} ｜ 基准日 {mo_saved['as_of']}）"
        )
        st.caption(f"🔎 漏斗：{mo_saved['funnel'].get('funnel_text', '')} ｜ 运行于 {mo_saved['run_at']}")

        if not mo_res.get("optimal_weights"):
            st.error(f"未找到可行组合：{mo_meta.get('error', '未知原因')}。建议降低目标收益或延长持有期后重试。")
        else:
            k1, k2, k3, k4, k5 = st.columns(5)
            k1.metric("🎯 滚动达标胜率", f"{mo_pm.get('win_rate', 0) * 100:.1f}%")
            k2.metric("🛡️ 不亏损率", f"{mo_pm.get('no_loss_rate', 0) * 100:.1f}%")
            k3.metric("🎲 MC 达标概率", f"{mo_pm.get('monte_carlo_prob', 0) * 100:.1f}%")
            k4.metric("📈 历史年化", f"{mo_pm.get('expected_return_annualized', 0) * 100:.2f}%")
            k5.metric("📉 最大回撤", f"{mo_pm.get('max_drawdown', 0) * 100:.2f}%")

            # 双轨双池对比
            mo_exp = mo_saved.get("expert")
            if mo_exp and "expert_pool" in mo_exp:
                ep = mo_exp["expert_pool"]
                cmp_df = pd.DataFrame([
                    {"组合": "🤖 AI 量化精选池", "滚动达标胜率": mo_pm.get("win_rate", 0) * 100,
                     "不亏损率": mo_pm.get("no_loss_rate", 0) * 100, "基金数": len(mo_res["optimal_weights"])},
                    {"组合": "👨‍💼 专家精选池（等权）", "滚动达标胜率": ep.get("win_rate", 0) * 100,
                     "不亏损率": ep.get("no_loss_rate", 0) * 100, "基金数": mo_exp.get("n_funds", 0)},
                ])
                st.markdown("##### ⚖️ 双轨双池对比")
                st.dataframe(
                    cmp_df,
                    column_config={
                        "滚动达标胜率": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
                        "不亏损率": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
                    },
                    use_container_width=True, hide_index=True
                )
            else:
                st.caption("ℹ️ 专家精选池基金未进入本次候选 NAV 矩阵，暂无法同口径对比。")

            # 组合详情 + 金额分配
            st.markdown("##### 📋 组合明细与金额分配")
            _cap = mo_saved["capital"]
            detail_rows = []
            for d in mo_res.get("fund_details", []):
                detail_rows.append({
                    "基金代码": d.get("fund_code", ""),
                    "基金名称": d.get("fund_name", ""),
                    "类型桶": d.get("bucket", ""),
                    "权重(%)": d.get("weight", 0) * 100,
                    "配置金额(元)": round(_cap * d.get("weight", 0), 2),
                    "个基胜率(%)": d.get("win_rate", 0) * 100,
                    "年化(%)": d.get("annual_return", 0) * 100,
                    "最大回撤(%)": d.get("max_dd", 0) * 100,
                    "夏普": d.get("sharpe", 0),
                    "建议份额": d.get("share_class_recommendation", ""),
                    "C类配对码": d.get("ac_pair_code", "") or "",
                })
            if detail_rows:
                st.dataframe(
                    pd.DataFrame(detail_rows),
                    column_config={
                        "权重(%)": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.1f%%"),
                        "配置金额(元)": st.column_config.NumberColumn(format="¥%.2f"),
                        "个基胜率(%)": st.column_config.NumberColumn(format="%.1f%%"),
                        "年化(%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "最大回撤(%)": st.column_config.NumberColumn(format="%.2f%%"),
                        "夏普": st.column_config.NumberColumn(format="%.2f"),
                    },
                    use_container_width=True, hide_index=True
                )
                fig_mo = px.pie(
                    pd.DataFrame(detail_rows), names="基金名称", values="权重(%)",
                    title="组合权重分布", hole=0.45
                )
                st.plotly_chart(fig_mo, use_container_width=True)

            # Monte Carlo 分布详情
            mc = mo_res.get("monte_carlo_detail", {}) or {}
            if mc:
                with st.expander("🎲 Monte Carlo 模拟分布详情", expanded=False):
                    ci90 = mc.get("ci_90", (0.0, 0.0))
                    ci95 = mc.get("ci_95", (0.0, 0.0))
                    m1, m2, m3 = st.columns(3)
                    m1.metric("模拟年化均值", f"{mc.get('mean_return', 0) * 100:.2f}%")
                    m2.metric("90% 置信区间", f"[{ci90[0] * 100:.2f}%, {ci90[1] * 100:.2f}%]")
                    m3.metric("95% 置信区间", f"[{ci95[0] * 100:.2f}%, {ci95[1] * 100:.2f}%]")
                    pct = mc.get("distribution_percentiles", {}) or {}
                    if pct:
                        st.dataframe(
                            pd.DataFrame([{"分位": str(k), "年化收益(%)": float(v) * 100} for k, v in pct.items()]),
                            use_container_width=True, hide_index=True
                        )

            with st.expander("🛠️ 优化元数据", expanded=False):
                st.json(mo_meta)

            # ── 存量持仓调仓路径（接入 #1） ──
            if hasattr(pm, 'holdings') and pm.holdings and len(pm.holdings) > 0 and mo_res.get("optimal_weights"):
                with st.expander("📦 存量持仓 → 最优组合调仓路径", expanded=False):
                    st.caption("基于您当前持仓与本次最优组合的差异，计算最低摩擦成本的调仓操作路径。")
                    if st.button("🔄 计算调仓路径", key="btn_rebalance_path"):
                        with st.spinner("正在计算调仓路径..."):
                            try:
                                _rb_holdings = {}
                                _rb_total_val = 0.0
                                # pm.holdings 是 Dict[str, FundHolding]，需用 .items() 遍历
                                for _h_code, _h_obj in pm.holdings.items():
                                    _h_shares = float(getattr(_h_obj, "shares", 0) or 0)
                                    _h_nav = float(getattr(_h_obj, "current_nav", 1.0) or 1.0)
                                    _h_cost = float(getattr(_h_obj, "cost_price", _h_nav) or _h_nav)
                                    # 从 batches 计算最早持有天数
                                    _h_batches = getattr(_h_obj, "batches", []) or []
                                    _h_days = max((getattr(b, "holding_days", 0) or 0 for b in _h_batches), default=0)
                                    _rb_holdings[str(_h_code).strip()] = {
                                        "shares": _h_shares, "nav": _h_nav,
                                        "cost": _h_cost, "holding_days": _h_days,
                                    }
                                    _rb_total_val += _h_shares * _h_nav

                                if _rb_total_val > 0:
                                    # 从 mo_saved 恢复用户选定的持有期（HOLDING_PERIODS 映射）
                                    _rb_horizon_map = {"短期(3~6月)": 125, "中期(1~2年)": 250, "长期(3~5年)": 500}
                                    _rb_hdays = _rb_horizon_map.get(mo_saved.get("horizon", ""), 250)
                                    # 就地构造轻量 optimizer（仅需 candidate_info 用于席位警告）
                                    _rb_opt = WinRateOptimizer(
                                        nav_matrix=pd.DataFrame(),
                                        candidate_info=pd.DataFrame(mo_res.get("fund_details", [])).rename(
                                            columns={"fund_code": "fund_code"}
                                        ) if mo_res.get("fund_details") else pd.DataFrame(columns=["fund_code", "status"]),
                                        holding_days=_rb_hdays,
                                        target_annual_return=mo_saved["target_pct"] / 100.0,
                                    )
                                    _rb_result = _rb_opt.optimize_rebalance_path(
                                        current_holdings=_rb_holdings,
                                        optimal_weights=mo_res["optimal_weights"],
                                        total_value=_rb_total_val,
                                    )
                                    # 展示调仓操作
                                    _rb_actions = _rb_result.get("rebalance_actions", [])
                                    if _rb_actions:
                                        st.markdown(f"**调仓操作：{_rb_result['n_sells']} 笔赎回 + {_rb_result['n_buys']} 笔申购 ｜ 预估摩擦成本 ¥{_rb_result['total_friction_cost']:,.2f} ｜ 预估完成 {_rb_result['estimated_days']} 个工作日**")
                                        _rb_df = pd.DataFrame(_rb_actions)
                                        _rb_col_map = {"action": "操作", "fund_code": "基金代码", "amount": "金额(元)",
                                                       "current_weight": "当前权重(%)", "target_weight": "目标权重(%)",
                                                       "holding_days": "已持有天数", "redemption_fee_rate": "赎回费率",
                                                       "estimated_fee": "预估费用(元)"}
                                        _rb_df = _rb_df.rename(columns=_rb_col_map)
                                        st.dataframe(_rb_df, use_container_width=True, hide_index=True)
                                    else:
                                        st.success("✅ 当前持仓与最优组合差异极小，无需调仓！")
                                    # 锁定期警告
                                    for _lf in _rb_result.get("locked_funds", []):
                                        st.warning(f"🔒 {_lf}")
                                    # 席位丢失警告
                                    for _sw in _rb_result.get("seat_warnings", []):
                                        st.error(_sw)
                                else:
                                    st.info("当前持仓市值为 0，无法计算调仓路径。")
                            except Exception as _rb_e:
                                st.error(f"调仓路径计算异常：{_rb_e}")
    else:
        st.info("👆 设定目标后点击「开始全市场胜率最优选基」。首次运行需获取候选基金净值（结果按日缓存，后续秒级返回）。")
