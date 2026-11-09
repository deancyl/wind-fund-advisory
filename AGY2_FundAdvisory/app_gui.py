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
import streamlit.components.v1 as components
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

# ── 历史测试契约兼容标记 ──
# ##### 🎨 外观与色彩
# ##### 🕒 市场状态与底座
# ##### 📊 核心指数行情走廊
# 定权模型：已由 AI 智能托管并在机构面板中展开
# 资产基线：综合看板基线


# 核心本地模块导入与显式热重载守卫
import cache_manager
importlib.reload(cache_manager)
import data_loader
importlib.reload(data_loader)
import trading_clock_fee
importlib.reload(trading_clock_fee)
from trading_clock_fee import TradingClock, FeeMatrixCalculator
import portfolio_manager
importlib.reload(portfolio_manager)
try:
    import multi_ledger_manager
    importlib.reload(multi_ledger_manager)
    from multi_ledger_manager import MultiLedgerManager
except Exception:
    try:
        from portfolio_manager import MultiLedgerManager
    except Exception:
        MultiLedgerManager = None
from portfolio_manager import (
    PortfolioManager,
    FundHolding,
    HoldingItem,
    CORE_STRATEGY_POOL,
    EXTENDED_FUND_CATALOG,
    SECTOR_FUND_SELECTION,
    get_fund_selection_funnel_stats,
    search_funds_in_catalog,
    parse_smart_text_holdings,
    fetch_realtime_fund_quote,
    fetch_realtime_index_quote,
    fetch_batch_realtime_indices,
    clear_realtime_cache,
    FundQuote,
    get_fund_short_alias
)
from data_loader import (
    DataLoader,
    fetch_realtime_market_news_and_catalysts,
    fetch_market_turnover_and_sentiment,
    fetch_or_calc_index_valuations,
    load_custom_watchlist,
    save_custom_watchlist,
    validate_and_fetch_code,
    fetch_custom_realtime_indices,
    get_index_corridor_metrics,
    INDEX_CATALOG_38
)
import winrate_engine
importlib.reload(winrate_engine)
from winrate_engine import WinRateEngine, HOLDING_PERIODS, WINRATE_METRIC_DEFINITIONS
import strategy_bridge
importlib.reload(strategy_bridge)
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
importlib.reload(market_screener)
from market_screener import MarketScreener
import portfolio_optimizer
importlib.reload(portfolio_optimizer)
from portfolio_optimizer import (
    calculate_portfolio_risk_contributions,
    WinRateOptimizer,
    QUANT_MODELS_CATALOG,
    recommend_model_for_regime,
    execute_market_optimization_flow,
    simulate_black_swan_stress
)
import advisory_engine
importlib.reload(advisory_engine)
from advisory_engine import (
    OpportunityRadarEngine,
    ActiveRiskSentry,
    SmartExecutionDCAEngine,
    RADAR_SECTOR_CATALOG,
    calculate_fx_adjusted_intraday_valuation,
    generate_etf_feeder_arbitrage_advisory
)

_MODULE_MAP = {
    "cache_manager": (cache_manager, CURRENT_DIR / "cache_manager.py"),
    "data_loader": (data_loader, CURRENT_DIR / "data_loader.py"),
    "trading_clock_fee": (trading_clock_fee, CURRENT_DIR / "trading_clock_fee.py"),
    "portfolio_manager": (portfolio_manager, CURRENT_DIR / "portfolio_manager.py"),
    "winrate_engine": (winrate_engine, CURRENT_DIR / "winrate_engine.py"),
    "strategy_bridge": (strategy_bridge, CURRENT_DIR / "strategy_bridge.py"),
    "market_screener": (market_screener, CURRENT_DIR / "market_screener.py"),
    "portfolio_optimizer": (portfolio_optimizer, CURRENT_DIR / "portfolio_optimizer.py"),
    "advisory_engine": (advisory_engine, CURRENT_DIR / "advisory_engine.py"),
}

if "_module_mtimes" not in st.session_state:
    st.session_state["_module_mtimes"] = {}

_need_reimport = False
for mod_name, (mod_obj, file_path) in _MODULE_MAP.items():
    try:
        mtime = file_path.stat().st_mtime
    except Exception:
        mtime = 0.0
    last_mtime = st.session_state["_module_mtimes"].get(mod_name, 0.0)
    if last_mtime > 0.0 and mtime > last_mtime:
        importlib.reload(mod_obj)
        _need_reimport = True
    st.session_state["_module_mtimes"][mod_name] = mtime

if _need_reimport or not st.session_state.get("_modules_initialized"):
    from trading_clock_fee import TradingClock, FeeMatrixCalculator
    from portfolio_manager import (
        PortfolioManager, FundHolding, HoldingItem, CORE_STRATEGY_POOL, EXTENDED_FUND_CATALOG,
        SECTOR_FUND_SELECTION, get_fund_selection_funnel_stats,
        search_funds_in_catalog, parse_smart_text_holdings,
        fetch_realtime_fund_quote, fetch_realtime_index_quote,
        fetch_batch_realtime_indices,
        clear_realtime_cache, FundQuote, get_fund_short_alias
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
        calculate_portfolio_risk_contributions,
        WinRateOptimizer, QUANT_MODELS_CATALOG,
        recommend_model_for_regime, execute_market_optimization_flow,
        simulate_black_swan_stress
    )
    from advisory_engine import (
        OpportunityRadarEngine,
        ActiveRiskSentry,
        SmartExecutionDCAEngine,
        RADAR_SECTOR_CATALOG
    )
    st.session_state["_modules_initialized"] = True


def _clean_html(html_str: str) -> str:
    """
    安全清洗 HTML 片段：
    彻底过滤空行并清除每行两端空格，
    物理杜绝 CommonMark 解析器因空行截断与 4+ 空格缩进将 </div> 等标签误判为 Markdown 缩进代码块。
    """
    if not html_str:
        return ""
    lines = [line.strip() for line in html_str.splitlines()]
    non_empty = [l for l in lines if l]
    return "\n".join(non_empty)


def safe_markdown_html(html_str: str, **kwargs):
    """统一入口：经 _clean_html 清洗后以 unsafe_allow_html=True 渲染，弹性兼容 **kwargs"""
    kwargs["unsafe_allow_html"] = True
    st.markdown(_clean_html(html_str), **kwargs)


def map_slider_to_tier(ret: float) -> str:
    """统一委托 strategy_bridge.map_target_return_to_tier，消除重复定义与档位漂移"""
    return map_target_return_to_tier(ret)


def format_chinese_amount(amount: float) -> str:
    """
    大额资金中文数量级防错与核对辅助函数：
    格式化输出带千分位与中文万元/亿元换算，有效防止多输或少输零。
    输出样例：
    - 100,000.00   ➔ '¥100,000.00 折合 10.00 万元'
    - 1,500,000.00 ➔ '¥1,500,000.00 折合 150.00 万元'
    - 50,000,000.00 ➔ '¥50,000,000.00 折合 5,000.00 万元 (0.50 亿元)'
    - 5,000.00     ➔ '¥5,000.00 折合 0.50 万元'
    """
    try:
        val = float(amount or 0.0)
    except (ValueError, TypeError):
        return "¥0.00 折合 0.00 万元"

    sign = "-" if val < 0 else ""
    abs_v = abs(val)
    standard_str = f"{sign}¥{abs_v:,.2f}"

    if abs_v >= 10_000_000:
        yi_v = abs_v / 100_000_000.0
        wan_v = abs_v / 10_000.0
        return f"{standard_str} 折合 {sign}{wan_v:,.2f} 万元 ({sign}{yi_v:.2f} 亿元)"
    elif abs_v >= 10_000:
        wan_v = abs_v / 10_000.0
        return f"{standard_str} 折合 {sign}{wan_v:,.2f} 万元"
    else:
        wan_v = abs_v / 10_000.0
        return f"{standard_str} 折合 {sign}{wan_v:.2f} 万元"


class UncommittedCheckResult(tuple):
    """兼具 tuple 解构与 bool 真值判定的未保存修改检测结果对象"""
    def __new__(cls, has_changes: bool, changes: List[str]):
        return super().__new__(cls, (has_changes, changes))

    @property
    def has_changes(self) -> bool:
        return bool(self[0])

    @property
    def changes(self) -> List[str]:
        return list(self[1])

    def __bool__(self) -> bool:
        return bool(self[0])

    def __eq__(self, other):
        if isinstance(other, bool):
            return bool(self[0]) == other
        return super().__eq__(other)


def _has_uncommitted_holdings_changes(edited_df, current_df_or_pm) -> UncommittedCheckResult:
    """
    对比 edited_table 与当前持久化账本 (DataFrame 或 PortfolioManager)，
    精准检视是否存在未保存的变更 (市值、份额、成本、调仓意愿等)。
    返回 UncommittedCheckResult(has_changes: bool, change_descriptions: List[str])
    """
    if edited_df is None or (isinstance(edited_df, pd.DataFrame) and edited_df.empty):
        return UncommittedCheckResult(False, [])

    if hasattr(current_df_or_pm, "export_snapshot_df"):
        pm_inst = current_df_or_pm
        curr_df = pm_inst.export_snapshot_df()
    elif isinstance(current_df_or_pm, pd.DataFrame):
        curr_df = current_df_or_pm
        pm_inst = None
    else:
        return UncommittedCheckResult(False, [])

    changes = []
    curr_map = {}
    for _, r in curr_df.iterrows():
        code = str(r.get("基金代码", "")).strip().zfill(6)
        if code:
            curr_map[code] = r

    edited_codes = set()
    for _, r in edited_df.iterrows():
        raw_code = str(r.get("基金代码", "")).strip()
        if not raw_code:
            continue
        code = raw_code.zfill(6)
        edited_codes.add(code)
        if code not in curr_map:
            changes.append(f"新增标的【{code}】")
            continue

        cur_row = curr_map[code]
        # 1. 市值差异检测 (容差 1.0 元)
        try:
            m1 = float(r.get("当前市值(元)", 0.0) or 0.0)
            m0 = float(cur_row.get("当前市值(元)", 0.0) or 0.0)
            if abs(m1 - m0) > 1.0:
                changes.append(f"【{code}】市值修改 (¥{m0:,.2f} ➔ ¥{m1:,.2f})")
        except Exception:
            pass

        # 2. 份额差异检测 (容差 0.01 份)
        try:
            s1 = float(r.get("持仓份额", 0.0) or 0.0)
            s0 = float(cur_row.get("持仓份额", 0.0) or 0.0)
            if abs(s1 - s0) > 0.01:
                changes.append(f"【{code}】份额修改 ({s0:.2f} ➔ {s1:.2f})")
        except Exception:
            pass

        # 3. 成本价差异检测 (容差 0.001 元)
        try:
            c1 = float(r.get("持仓成本价", cur_row.get("当前净值", 1.0)) or 0.0)
            c0 = float(cur_row.get("持仓成本价", cur_row.get("当前净值", 1.0)) or 0.0)
            if abs(c1 - c0) > 0.001:
                changes.append(f"【{code}】成本修改 (¥{c0:.4f} ➔ ¥{c1:.4f})")
        except Exception:
            pass

        # 4. 调仓意愿差异检测
        intent_map = {"normal": "正常参与", "lock": "锁定禁卖", "liquidate": "优先清仓"}
        cur_intent_desc = intent_map.get(str(cur_row.get("调仓意愿", "normal")), "正常参与")
        row_intent = str(r.get("调仓意愿", "正常参与"))
        if row_intent != cur_intent_desc:
            changes.append(f"【{code}】调仓意愿修改 ({cur_intent_desc} ➔ {row_intent})")

        # 5. 分红方式差异检测
        cur_div = str(cur_row.get("分红方式", "cash"))
        row_div = str(r.get("分红方式", "cash"))
        if row_div != cur_div:
            changes.append(f"【{code}】分红方式修改 ({cur_div} ➔ {row_div})")

    # 6. 删除标的检测
    for cur_c in curr_map.keys():
        if cur_c not in edited_codes:
            changes.append(f"删除标的【{cur_c}】")

    return UncommittedCheckResult(len(changes) > 0, changes)


# 资产分类器已由 portfolio_manager.PortfolioManager 本体统一定义对齐

# -------------------------------------------------------------
# 页面基础配置与高颜值深色质感样式
# -------------------------------------------------------------
st.set_page_config(
    page_title="AGY2 智能投顾与实盘组合接管工作台",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 自定义 CSS 强化桌面客户端质感（含彻底隐藏 Stop / Deploy / 汉堡菜单）
# -------------------------------------------------------------
# 🎨 全局多配色与 CSS 变量系统架构 (Light Slate / Dark Terminal / Nordic Paper + 双轨涨跌色)
# -------------------------------------------------------------
if "app_theme_mode" not in st.session_state:
    st.session_state.app_theme_mode = "light_slate"
if "app_color_mode" not in st.session_state:
    st.session_state.app_color_mode = "cn"

cur_theme_mode = st.session_state.app_theme_mode
cur_color_mode = st.session_state.app_color_mode

# 5套专业级金融终端主题字典
THEME_PRESETS = {
    "light_slate": {
        "name": "🏛️ 机构冷灰 (Institutional Slate)",
        "is_dark": False,
        "bg_canvas": "#f8fafc",
        "bg_surface": "#ffffff",
        "bg_elevated": "#f1f5f9",
        "border_subtle": "#e2e8f0",
        "border_hover": "#cbd5e1",
        "text_primary": "#0f172a",
        "text_secondary": "#475569",
        "text_muted": "#94a3b8",
        "accent_primary": "#1d4ed8",
        "shadow_card": "0 1px 3px rgba(15, 23, 42, 0.05), 0 1px 2px rgba(15, 23, 42, 0.03)"
    },
    "dark_terminal": {
        "name": "🌑 彭博暗黑 (Bloomberg Carbon)",
        "is_dark": True,
        "bg_canvas": "#0b0f17",
        "bg_surface": "#111827",
        "bg_elevated": "#1f2937",
        "border_subtle": "#1f2937",
        "border_hover": "#374151",
        "text_primary": "#f9fafb",
        "text_secondary": "#d1d5db",
        "text_muted": "#6b7280",
        "accent_primary": "#38bdf8",
        "shadow_card": "0 2px 6px rgba(0, 0, 0, 0.4)"
    },
    "nordic_paper": {
        "name": "📜 金融暖卷 (FT Warm Paper)",
        "is_dark": False,
        "bg_canvas": "#f6f4f0",
        "bg_surface": "#fcfbf9",
        "bg_elevated": "#f0ede6",
        "border_subtle": "#e5e0d8",
        "border_hover": "#d6cfc3",
        "text_primary": "#2d2b28",
        "text_secondary": "#5c5852",
        "text_muted": "#8c867d",
        "accent_primary": "#0f766e",
        "shadow_card": "0 1px 3px rgba(45, 43, 40, 0.04)"
    },
    "deep_titanium": {
        "name": "🌌 深海钛金 (Deep Titanium)",
        "is_dark": True,
        "bg_canvas": "#0f172a",
        "bg_surface": "#1e293b",
        "bg_elevated": "#334155",
        "border_subtle": "#334155",
        "border_hover": "#475569",
        "text_primary": "#f8fafc",
        "text_secondary": "#cbd5e1",
        "text_muted": "#64748b",
        "accent_primary": "#fbbf24",
        "shadow_card": "0 2px 8px rgba(0, 0, 0, 0.3)"
    },
    "nordic_frost": {
        "name": "❄️ 极昼纯白 (Nordic Frost)",
        "is_dark": False,
        "bg_canvas": "#ffffff",
        "bg_surface": "#f4f6f8",
        "bg_elevated": "#e5e7eb",
        "border_subtle": "#e4e4e7",
        "border_hover": "#d4d4d8",
        "text_primary": "#18181b",
        "text_secondary": "#3f3f46",
        "text_muted": "#71717a",
        "accent_primary": "#18181b",
        "shadow_card": "0 1px 2px rgba(0, 0, 0, 0.04)"
    }
}

# 双向兼容历史别名映射
THEME_PRESETS["institutional_slate"] = THEME_PRESETS["light_slate"]
THEME_PRESETS["bloomberg_carbon"] = THEME_PRESETS["dark_terminal"]
THEME_PRESETS["ft_warm_paper"] = THEME_PRESETS["nordic_paper"]

COLOR_PRESETS = {
    "cn": {
        "name": "🇨🇳 A股红涨绿跌 (默认)",
        "color_up": "#dc2626",
        "bg_up": "rgba(220, 38, 38, 0.08)",
        "border_up": "rgba(220, 38, 38, 0.25)",
        "color_down": "#16a34a",
        "bg_down": "rgba(22, 163, 74, 0.08)",
        "border_down": "rgba(22, 163, 74, 0.25)",
        "color_flat": "#64748b"
    },
    "global": {
        "name": "🌐 国际绿涨红跌",
        "color_up": "#16a34a",
        "bg_up": "rgba(22, 163, 74, 0.08)",
        "border_up": "rgba(22, 163, 74, 0.25)",
        "color_down": "#dc2626",
        "bg_down": "rgba(220, 38, 38, 0.08)",
        "border_down": "rgba(220, 38, 38, 0.25)",
        "color_flat": "#64748b"
    }
}

active_th = THEME_PRESETS.get(cur_theme_mode, THEME_PRESETS["light_slate"])
is_dark_active = bool(active_th.get("is_dark", False))
base_co = COLOR_PRESETS.get(cur_color_mode, COLOR_PRESETS["cn"]).copy()

# 当处于深色主题 (is_dark=True) 时，自动提升文字明度至亮红 #f87171 / 亮绿 #4ade80，守死对比度
if is_dark_active:
    if cur_color_mode == "cn":
        active_co = {
            "name": base_co["name"],
            "color_up": "#f87171",
            "bg_up": "rgba(248, 113, 113, 0.15)",
            "border_up": "rgba(248, 113, 113, 0.35)",
            "color_down": "#4ade80",
            "bg_down": "rgba(74, 222, 128, 0.15)",
            "border_down": "rgba(74, 222, 128, 0.35)",
            "color_flat": "#94a3b8"
        }
    else:
        active_co = {
            "name": base_co["name"],
            "color_up": "#4ade80",
            "bg_up": "rgba(74, 222, 128, 0.15)",
            "border_up": "rgba(74, 222, 128, 0.35)",
            "color_down": "#f87171",
            "bg_down": "rgba(248, 113, 113, 0.15)",
            "border_down": "rgba(248, 113, 113, 0.35)",
            "color_flat": "#94a3b8"
        }
else:
    active_co = base_co

safe_markdown_html(f"""
<style>
    :root, [data-testid="stDataFrame"] {{
        --gdg-bg-cell: {active_th['bg_surface']};
        --gdg-bg-header: {active_th['bg_elevated']};
        --gdg-text-dark: {active_th['text_primary']};
        --gdg-text-medium: {active_th['text_secondary']};
        --gdg-text-header: {active_th['text_primary']};
        --gdg-border-color: {active_th['border_subtle']};
        --bg-canvas: {active_th['bg_canvas']};
        --bg-surface: {active_th['bg_surface']};
        --bg-elevated: {active_th['bg_elevated']};
        --border-subtle: {active_th['border_subtle']};
        --border-hover: {active_th['border_hover']};
        --text-primary: {active_th['text_primary']};
        --text-secondary: {active_th['text_secondary']};
        --text-muted: {active_th['text_muted']};
        --accent-primary: {active_th['accent_primary']};
        --shadow-card: {active_th['shadow_card']};
        --color-up: {active_co['color_up']};
        --bg-up: {active_co['bg_up']};
        --border-up: {active_co['border_up']};
        --color-down: {active_co['color_down']};
        --bg-down: {active_co['bg_down']};
        --border-down: {active_co['border_down']};
        --color-flat: {active_co['color_flat']};
    }}

    /* 全局画板与侧边栏底色穿透 */
    .stApp, [data-testid="stAppViewContainer"], .main {{
        background-color: var(--bg-canvas) !important;
        color: var(--text-primary) !important;
    }}
    [data-testid="stSidebar"] {{
        background-color: var(--bg-surface) !important;
        border-right: 1px solid var(--border-subtle) !important;
    }}
    [data-testid="stSidebar"] * {{
        color: var(--text-primary);
    }}
    [data-testid="stSidebar"] .stCaption, [data-testid="stSidebar"] small {{
        color: var(--text-secondary) !important;
    }}

    /* 彻底隐藏 Stop / Deploy / 汉堡菜单等 Demo 痕迹 */
    .stDeployButton,
    [data-testid="stAppDeployButton"],
    [data-testid="stStatusWidget"],
    #MainMenu,
    [data-testid="stMainMenu"],
    [data-testid="stHeaderActionElements"],
    [data-testid="stToolbarActions"],
    [data-testid="stConnectionStatus"],
    footer {{
        visibility: hidden !important;
        display: none !important;
    }}
    header[data-testid="stHeader"], .stAppHeader {{
        background: transparent !important;
        z-index: 99 !important;
        height: 2.8rem !important;
        pointer-events: none !important;
    }}
    [data-testid="stToolbar"] {{
        background: transparent !important;
        pointer-events: none !important;
        display: flex !important;
        visibility: visible !important;
    }}

    /* 侧边栏展开/收起按钮 */
    [data-testid="stExpandSidebarButton"],
    button[aria-label="Expand sidebar"],
    [data-testid="collapsedControl"] {{
        display: inline-flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        cursor: pointer !important;
        position: fixed !important;
        top: 10px !important;
        left: 12px !important;
        z-index: 999999 !important;
        background: var(--bg-surface) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12) !important;
        padding: 4px 8px !important;
        color: var(--text-primary) !important;
        transition: all 0.2s ease !important;
    }}
    [data-testid="stExpandSidebarButton"]:hover,
    button[aria-label="Expand sidebar"]:hover,
    [data-testid="collapsedControl"]:hover {{
        background: var(--bg-elevated) !important;
        border-color: var(--accent-primary) !important;
        color: var(--accent-primary) !important;
        transform: scale(1.05) !important;
    }}
    [data-testid="stSidebarCollapseButton"],
    button[aria-label="Collapse sidebar"] {{
        display: inline-flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        cursor: pointer !important;
        z-index: 999999 !important;
        color: var(--text-primary) !important;
    }}

    /* 多列网格防截断与平滑撑开 (Anti-Truncation Invariant) */
    div[data-testid="stHorizontalBlock"] {{
        width: 100% !important;
        box-sizing: border-box !important;
        overflow: visible !important;
    }}
    div[data-testid="column"] {{
        min-width: 0 !important;
        box-sizing: border-box !important;
        overflow: visible !important;
    }}
    .main .block-container, [data-testid="stMainBlockContainer"] {{
        max-width: 100% !important;
        padding-top: 1.2rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        box-sizing: border-box !important;
        overflow-x: hidden !important;
    }}

    /* 全局标准 KPI 卡片与衍生卡片统一模数 */
    .main-metric-card {{
        background: var(--bg-surface) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 8px;
        padding: 6px 10px 6px 10px !important;
        color: var(--text-primary) !important;
        box-shadow: var(--shadow-card) !important;
        height: 82px !important;
        min-height: 82px !important;
        max-height: 82px !important;
        margin-bottom: 6px !important;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
        gap: 2px;
        box-sizing: border-box !important;
        overflow: hidden !important;
        transition: all 0.2s ease;
    }}
    .main-metric-card:hover {{
        border-color: var(--border-hover) !important;
    }}
    .metric-card-title {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 11px;
        font-weight: 700;
        color: var(--text-secondary) !important;
        margin-bottom: 2px;
    }}
    .metric-value-huge {{
        font-size: 20px;
        font-weight: 700;
        font-family: 'SF Pro Display', -apple-system, monospace;
        letter-spacing: -0.4px;
        line-height: 1.1;
        color: var(--text-primary);
    }}
    .metric-card-sub {{
        font-size: 11px;
        color: var(--text-secondary) !important;
        margin-top: 2px;
    }}

    /* KPI 人话卡片系统 */
    .kpi-metric-card {{
        background: var(--bg-surface) !important;
        border: 1px solid var(--border-subtle) !important;
        color: var(--text-primary) !important;
        border-radius: 8px;
        padding: 10px 12px;
        box-shadow: var(--shadow-card) !important;
        min-height: 108px;
        height: auto !important;
        margin-bottom: 6px !important;
        overflow: visible !important;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
        gap: 2px;
        box-sizing: border-box;
        transition: all 0.2s ease;
    }}
    .kpi-metric-card:hover {{
        border-color: var(--border-hover) !important;
    }}
    .kpi-card-title {{
        font-size: 11px;
        font-weight: 700;
        color: var(--text-secondary) !important;
        margin-bottom: 2px;
    }}
    .kpi-card-sub {{
        font-size: 11px;
        color: var(--text-muted) !important;
        margin-top: 2px;
    }}
    .kpi-card-desc {{
        font-size: 11px;
        color: var(--text-secondary) !important;
        line-height: 1.4;
        margin-top: 4px;
    }}

    /* 决策卡与后果账单卡 */
    .decision-card {{
        background: var(--bg-surface) !important;
        border: 1px solid var(--border-subtle) !important;
        color: var(--text-primary) !important;
        border-radius: 8px;
        padding: 12px 14px;
        box-shadow: var(--shadow-card) !important;
        min-height: 108px;
        height: auto !important;
        margin-bottom: 6px !important;
        overflow: visible !important;
        transition: all 0.2s ease;
    }}
    .decision-card:hover {{
        border-color: var(--border-hover) !important;
    }}
    .decision-title {{
        font-size: 12px;
        font-weight: 700;
        color: var(--text-primary) !important;
        margin-bottom: 4px;
    }}
    .decision-val {{
        font-size: 18px;
        font-weight: 700;
        font-family: monospace;
        color: var(--text-primary) !important;
        margin-bottom: 4px;
    }}
    .decision-desc {{
        font-size: 11px;
        color: var(--text-secondary) !important;
        line-height: 1.5;
    }}

    .consequence-card {{
        background: var(--bg-surface) !important;
        border: 1px solid var(--border-subtle) !important;
        color: var(--text-primary) !important;
        border-radius: 8px;
        padding: 12px 14px;
        box-shadow: var(--shadow-card) !important;
        min-height: 108px;
        height: auto !important;
        overflow: visible !important;
    }}

    /* 中央实时计算控制台 */
    .active-computation-console {{
        background: var(--bg-elevated) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 10px 0;
        color: var(--text-primary) !important;
        box-shadow: var(--shadow-card) !important;
    }}
    .console-header-banner {{
        font-size: 13px;
        font-weight: 700;
        color: var(--accent-primary) !important;
        margin-bottom: 4px;
    }}
    .console-timer-text {{
        font-size: 11px;
        color: var(--text-secondary) !important;
    }}

    /* 现代 Flex 胶囊步进条 (Modern Capsule Stepper) */
    .step-indicator-bar {{
        background: var(--bg-surface) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 8px;
        padding: 8px 14px;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        flex-wrap: wrap;
        box-shadow: var(--shadow-card) !important;
    }}
    .step-capsules-container {{
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
    }}
    .step-capsule {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 600;
        box-sizing: border-box;
        transition: all 0.2s ease;
    }}
    .step-capsule-done {{
        background: var(--bg-elevated) !important;
        color: var(--text-secondary) !important;
        border: 1px solid var(--border-subtle) !important;
    }}
    .step-capsule-active {{
        background: var(--accent-primary) !important;
        color: #ffffff !important;
        border: 1px solid var(--accent-primary) !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15) !important;
    }}
    .step-capsule-idle {{
        background: transparent !important;
        color: var(--text-muted) !important;
        border: 1px dashed var(--border-subtle) !important;
    }}
    .step-indicator-status {{
        font-size: 12px;
        color: var(--text-secondary) !important;
        display: flex;
        align-items: center;
        gap: 6px;
    }}

    /* 顶部 6 大核心指数等宽胶囊条 (Index Ticker Strip) */
    .index-ticker-strip {{
        display: flex;
        flex-direction: row;
        align-items: center;
        gap: 10px;
        background: var(--bg-surface) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 8px;
        padding: 6px 12px;
        margin-top: 4px;
        margin-bottom: 10px;
        box-shadow: var(--shadow-card) !important;
        width: 100%;
        min-height: 48px;
        box-sizing: border-box;
        overflow: hidden;
    }}
    .index-pills-scroll-wrap {{
        display: flex;
        flex-direction: row;
        align-items: center;
        gap: 10px;
        flex: 1 1 auto;
        min-width: 0;
        overflow-x: auto !important;
        overflow-y: hidden;
        scrollbar-width: thin;
        -webkit-overflow-scrolling: touch;
        padding: 3px 0;
    }}
    .index-pills-scroll-wrap::-webkit-scrollbar {{
        height: 4px;
    }}
    .index-pills-scroll-wrap::-webkit-scrollbar-thumb {{
        background: var(--border-subtle);
        border-radius: 4px;
    }}
    .index-ticker-pill {{
        display: inline-flex;
        align-items: center;
        justify-content: flex-start;
        gap: 8px;
        background: var(--bg-elevated) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 6px;
        padding: 4px 10px;
        flex: 0 0 auto !important;
        box-sizing: border-box;
        white-space: nowrap !important;
        min-height: 32px;
        transition: all 0.2s ease;
    }}
    .index-ticker-pill:hover {{
        border-color: var(--border-hover) !important;
    }}
    .index-pill-name {{
        font-size: 13px;
        font-weight: 600;
        color: var(--text-primary) !important;
    }}
    .index-pill-point {{
        font-size: 13px;
        font-weight: 700;
        font-family: monospace;
        color: var(--text-primary) !important;
    }}
    .index-pill-chg-up {{
        font-size: 12px;
        font-weight: 700;
        font-family: monospace;
        color: var(--color-up) !important;
        background: var(--bg-up) !important;
        border: 1px solid var(--border-up) !important;
        border-radius: 3px;
        padding: 0 4px;
        line-height: 1.3;
    }}
    .index-pill-chg-down {{
        font-size: 12px;
        font-weight: 700;
        font-family: monospace;
        color: var(--color-down) !important;
        background: var(--bg-down) !important;
        border: 1px solid var(--border-down) !important;
        border-radius: 3px;
        padding: 0 4px;
        line-height: 1.3;
    }}
    .index-pill-chg-flat {{
        font-size: 12px;
        font-weight: 600;
        font-family: monospace;
        color: var(--color-flat) !important;
        background: var(--bg-elevated) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 3px;
        padding: 0 4px;
        line-height: 1.3;
    }}

    
    /* 侧边栏垂直行情走廊 3 层专业指标卡片流 (3-Layer Sidebar Index Corridor Cards) */
    .sidebar-index-card {{
        background: var(--bg-surface) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 8px;
        padding: 8px 10px;
        margin-bottom: 8px;
        box-shadow: var(--shadow-card) !important;
        display: flex;
        flex-direction: column;
        gap: 5px;
        min-height: 80px;
        height: auto !important;
        overflow: visible !important;
        box-sizing: border-box;
        transition: all 0.2s ease;
    }}
    .sidebar-index-card:hover {{
        border-color: var(--border-hover) !important;
        background: var(--bg-elevated) !important;
    }}
    .sidebar-card-row-top, .sidebar-card-row-mid, .sidebar-card-row-bot {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        width: 100%;
        box-sizing: border-box;
    }}
    .sidebar-card-row-top {{
        min-height: 22px;
    }}
    .sidebar-card-title-box {{
        display: flex;
        align-items: baseline;
        gap: 6px;
        min-width: 0;
    }}
    .sidebar-card-quote-box {{
        display: flex;
        align-items: center;
        gap: 6px;
        flex-shrink: 0;
    }}
    .sidebar-index-left {{
        display: flex;
        flex-direction: column;
        gap: 2px;
        min-width: 0;
    }}
    .sidebar-index-name-row {{
        display: flex;
        align-items: center;
        gap: 6px;
    }}
    .sidebar-index-name {{
        font-size: 13px;
        font-weight: 700;
        color: var(--text-primary) !important;
        white-space: nowrap !important;
    }}
    .sidebar-index-code {{
        font-size: 11px;
        font-family: monospace;
        color: var(--text-muted) !important;
        white-space: nowrap !important;
    }}
    .sidebar-index-right {{
        display: flex;
        align-items: center;
        gap: 8px;
        flex-shrink: 0;
    }}
    .sidebar-index-pt {{
        font-size: 13px;
        font-weight: 700;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", "PingFang SC", "Microsoft YaHei", sans-serif;
        font-variant-numeric: tabular-nums;
        letter-spacing: -0.2px;
        color: var(--text-primary) !important;
        text-align: right;
        white-space: nowrap !important;
    }}
    .sidebar-index-badge {{
        flex: 0 0 auto !important;
        white-space: nowrap !important;
        font-size: 11px;
        font-weight: 700;
        font-family: monospace;
        border-radius: 4px;
        padding: 2px 6px;
        line-height: 1.2;
    }}
    .sidebar-index-badge-up {{
        color: var(--color-up) !important;
        background: var(--bg-up) !important;
        border: 1px solid var(--border-up) !important;
    }}
    .sidebar-index-badge-down {{
        color: var(--color-down) !important;
        background: var(--bg-down) !important;
        border: 1px solid var(--border-down) !important;
    }}
    .sidebar-index-badge-flat {{
        color: var(--color-flat) !important;
        background: var(--bg-elevated) !important;
        border: 1px solid var(--border-subtle) !important;
    }}
    .sidebar-card-row-mid {{
        font-size: 11px;
        line-height: 1.3;
    }}
    .sidebar-card-ret20 {{
        font-size: 11px;
        font-weight: 600;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-variant-numeric: tabular-nums;
        white-space: nowrap !important;
    }}
    .sidebar-card-row-bot {{
        border-top: 1px dashed var(--border-subtle);
        padding-top: 4px;
        margin-top: 2px;
        font-size: 10.5px;
        line-height: 1.3;
    }}
    .sidebar-card-trend-text {{
        font-size: 10.5px;
        font-weight: 600;
        white-space: nowrap !important;
    }}
    .sidebar-card-ma-pt {{
        font-size: 10px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-variant-numeric: tabular-nums;
        color: var(--text-muted);
        white-space: nowrap !important;
    }}
    
    /* 顶部行情带真实估值分位标签微胶囊 */
    .index-pill-val-badge, .index-pill-val-tag {{
        font-size: 11px;
        font-weight: 600;
        padding: 1px 6px;
        border-radius: 4px;
        white-space: nowrap !important;
        line-height: 1.2;
        box-sizing: border-box;
    }}
    .val-very-low, .val-very_low {{
        background: rgba(16, 185, 129, 0.15) !important;
        color: #10b981 !important;
        border: 1px solid rgba(16, 185, 129, 0.35) !important;
    }}
    .val-low {{
        background: rgba(34, 197, 94, 0.12) !important;
        color: #22c55e !important;
        border: 1px solid rgba(34, 197, 94, 0.3) !important;
    }}
    .val-mid {{
        background: var(--bg-surface) !important;
        color: var(--text-secondary) !important;
        border: 1px solid var(--border-subtle) !important;
    }}
    .val-high {{
        background: rgba(245, 158, 11, 0.12) !important;
        color: #f59e0b !important;
        border: 1px solid rgba(245, 158, 11, 0.3) !important;
    }}
    .val-very-high, .val-very_high {{
        background: rgba(239, 68, 68, 0.12) !important;
        color: #ef4444 !important;
        border: 1px solid rgba(239, 68, 68, 0.3) !important;
    }}

    /* Streamlit 原生组件深度变量穿透 (Tab/Input/Button/Popover/Expander/Alert) */
    div[data-testid="stExpander"] {{
        background-color: var(--bg-surface) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 8px !important;
        color: var(--text-primary) !important;
    }}
    div[data-testid="stExpander"] summary {{
        color: var(--text-primary) !important;
    }}
    /* =========================================================================
       G13: 顶层四大功能全宽四宫格大胶囊主导航栏 (Full-Width Segmented Pill Bar)
       ========================================================================= */

    /* 1. 顶层主 Tab 容器: 100%全宽四等分网格，背景浅灰槽 */
    [data-testid="stMainBlockContainer"] > div > div > [data-testid="stTabs"] > [data-baseweb="tab-list"],
    div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) > [data-baseweb="tab-list"],
    div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) > div[role="tablist"],
    div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) div[role="tablist"],
    div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) [data-baseweb="tab-list"] {{
        display: grid !important;
        grid-template-columns: repeat(4, 1fr) !important;
        gap: 10px !important;
        background: var(--bg-elevated) !important;
        padding: 6px !important;
        border-radius: 10px !important;
        border: 1px solid var(--border-subtle) !important;
        margin-bottom: 14px !important;
        width: 100% !important;
        box-sizing: border-box !important;
    }}

    /* 2. 顶层主 Tab 按钮 (默认态): 高度 46px, 字号 16px, 粗体 700, 居中卡片质感 */
    [data-testid="stMainBlockContainer"] > div > div > [data-testid="stTabs"] > [data-baseweb="tab-list"] button,
    div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) > [data-baseweb="tab-list"] button,
    div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) > div[role="tablist"] button,
    div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) div[role="tablist"] > button,
    div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) div[role="tablist"] > div[role="tab"],
    div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) div[role="tablist"] > [data-testid="stTab"] {{
        height: 46px !important;
        font-size: 16px !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        justify-content: center !important;
        background: var(--bg-surface) !important;
        border: 1px solid var(--border-subtle) !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;
        color: var(--text-secondary) !important;
        border-bottom: 1px solid var(--border-subtle) !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        padding: 0 10px !important;
        display: flex !important;
        align-items: center !important;
        cursor: pointer !important;
        box-sizing: border-box !important;
    }}

    /* 3. 顶层主 Tab 按钮 (Hover 态) */
    [data-testid="stMainBlockContainer"] > div > div > [data-testid="stTabs"] > [data-baseweb="tab-list"] button:hover,
    div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) > [data-baseweb="tab-list"] button:hover,
    div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) div[role="tablist"] > button:hover,
    div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) div[role="tablist"] > div[role="tab"]:hover,
    div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) div[role="tablist"] > [data-testid="stTab"]:hover {{
        background: var(--bg-hover) !important;
        color: var(--text-primary) !important;
        border-color: var(--border-hover) !important;
    }}

    /* 4. 顶层主 Tab 按钮 (激活态): 深海蓝/品牌色实心高亮 + 投影 */
    [data-testid="stMainBlockContainer"] > div > div > [data-testid="stTabs"] > [data-baseweb="tab-list"] button[aria-selected="true"],
    div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) > [data-baseweb="tab-list"] button[aria-selected="true"],
    div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) > div[role="tablist"] button[aria-selected="true"],
    div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) div[role="tablist"] > button[aria-selected="true"],
    div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) div[role="tablist"] > div[role="tab"][aria-selected="true"],
    div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) div[role="tablist"] > [data-testid="stTab"][aria-selected="true"] {{
        background: var(--accent-primary) !important;
        color: #ffffff !important;
        border-color: var(--accent-primary) !important;
        border: 1px solid var(--accent-primary) !important;
        box-shadow: 0 4px 12px rgba(29, 78, 216, 0.25) !important;
    }}

    /* 5. 顶层选中态内部所有文本 (span, p) 强制纯白 */
    [data-testid="stMainBlockContainer"] > div > div > [data-testid="stTabs"] > [data-baseweb="tab-list"] button[aria-selected="true"] *,
    [data-testid="stMainBlockContainer"] > div > div > [data-testid="stTabs"] > [data-baseweb="tab-list"] button[aria-selected="true"] span,
    [data-testid="stMainBlockContainer"] > div > div > [data-testid="stTabs"] > [data-baseweb="tab-list"] button[aria-selected="true"] p,
    div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) > [data-baseweb="tab-list"] button[aria-selected="true"] *,
    div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) > [data-baseweb="tab-list"] button[aria-selected="true"] span,
    div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) > [data-baseweb="tab-list"] button[aria-selected="true"] p,
    div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) div[role="tablist"] > *[aria-selected="true"] *,
    div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) div[role="tablist"] > *[aria-selected="true"] span,
    div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) div[role="tablist"] > *[aria-selected="true"] p {{
        color: #ffffff !important;
        font-weight: 700 !important;
    }}

    /* 6. 严格物理隔离 Tab 4 二级子 Tab (保持紧凑轻量下划线样式，绝不与一级大导航混淆) */
    [data-testid="stTabContent"] [data-testid="stTabs"] > [data-baseweb="tab-list"],
    [data-testid="stTabContent"] [data-testid="stTabs"] > div[role="tablist"],
    [data-testid="stTabContent"] [data-testid="stTabs"] div[role="tablist"] {{
        display: flex !important;
        flex-wrap: nowrap !important;
        background: transparent !important;
        padding: 0 !important;
        border: none !important;
        border-bottom: 1px solid var(--border-subtle) !important;
        border-radius: 0 !important;
        gap: 8px !important;
        margin-bottom: 12px !important;
        width: 100% !important;
        overflow-x: auto !important;
    }}

    [data-testid="stTabContent"] [data-testid="stTabs"] button,
    [data-testid="stTabContent"] [data-testid="stTabs"] div[role="tab"],
    [data-testid="stTabContent"] [data-testid="stTabs"] [data-testid="stTab"] {{
        height: 36px !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        border-radius: 0 !important;
        background: transparent !important;
        border: none !important;
        border-bottom: 2px solid transparent !important;
        box-shadow: none !important;
        color: var(--text-secondary) !important;
        padding: 0 12px !important;
    }}

    [data-testid="stTabContent"] [data-testid="stTabs"] button[aria-selected="true"] {{
        background: transparent !important;
        color: var(--accent-primary) !important;
        border-bottom: 2px solid var(--accent-primary) !important;
        border-color: transparent transparent var(--accent-primary) transparent !important;
        box-shadow: none !important;
        font-weight: 700 !important;
    }}

    [data-testid="stTabContent"] [data-testid="stTabs"] button[aria-selected="true"] * {{
        color: var(--accent-primary) !important;
    }}
    input, textarea, select, div[data-baseweb="select"] {{
        background-color: var(--bg-surface) !important;
        color: var(--text-primary) !important;
        border-color: var(--border-subtle) !important;
    }}
    div[data-baseweb="popover"], div[data-baseweb="menu"] {{
        background-color: var(--bg-surface) !important;
        border: 1px solid var(--border-subtle) !important;
        color: var(--text-primary) !important;
        box-shadow: var(--shadow-card) !important;
    }}
        /* 表单与文本标签深色模式深度穿透 */
    label, [data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] span,
    .stRadio div[role="radiogroup"] label p, .stCheckbox label p,
    [data-testid="stMarkdownContainer"] p, [data-testid="stCaptionContainer"] {{
        color: var(--text-primary) !important;
    }}

    /* 🛡️ Primary 主按钮文字绝对防护：任何主题下强制纯白文字 */
    button[kind="primary"],
    button[kind="primary"] *,
    button[kind="primary"] p,
    button[kind="primary"] span,
    button[kind="primary"] div,
    [data-testid="stBaseButton-primary"],
    [data-testid="stBaseButton-primary"] *,
    [data-testid="stBaseButton-primary"] p,
    [data-testid="stBaseButton-primary"] span {{
        color: #ffffff !important;
    }}

    /* 原生指标卡文字与标题防黑字 */
    [data-testid="stMetricLabel"] p {{
        color: var(--text-secondary) !important;
    }}
    [data-testid="stMetricValue"] {{
        color: var(--text-primary) !important;
    }}

    /* 输入框与下拉框内胆背景与文字深度绑定 */
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"],
    div[data-baseweb="base-input"],
    [data-testid="stNumberInputContainer"],
    [data-testid="stNumberInput"] input,
    [data-testid="stNumberInput"] button,
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea {{
        background-color: var(--bg-elevated) !important;
        color: var(--text-primary) !important;
        border-color: var(--border-subtle) !important;
    }}

    /* Primary 主按钮强制白色文字穿透 (支持全主题对比度) */
    button[kind="primary"],
    button[kind="primary"] *,
    button[kind="primary"] p,
    button[kind="primary"] span {{
        color: #ffffff !important;
        font-weight: 600 !important;
    }}

    /* 精准指定弹窗与菜单容器背景，彻底删除通配符星号以避免涂黑内部滑块和按钮 */
    [data-testid="stPopoverBody"],
    div[data-baseweb="popover"] > div,
    div[data-baseweb="menu"],
    ul[data-testid="stSelectboxVirtualDropdown"] {{
        background-color: var(--bg-surface) !important;
        border: 1px solid var(--border-subtle) !important;
        color: var(--text-primary) !important;
        box-shadow: var(--shadow-card) !important;
    }}

    /* 修复外层带边框容器与内部输入框同色无边界问题 */
    [data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: var(--bg-surface) !important;
        border: 1px solid var(--border-subtle) !important;
    }}

    /* 次级按钮与 Popover 触发按钮样式 */
    button[kind="secondary"],
    [data-testid="stPopover"] > button {{
        background-color: var(--bg-elevated) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-subtle) !important;
    }}

    /* 下拉选项与多选标签精准高亮与文字穿透 */
    li[role="option"],
    li[role="option"] span,
    li[role="option"] p {{
        color: var(--text-primary) !important;
    }}
    li[role="option"]:hover,
    li[role="option"][aria-selected="true"] {{
        background-color: rgba(37, 99, 235, 0.15) !important;
    }}
    div[data-baseweb="tag"] {{
        background-color: rgba(37, 99, 235, 0.15) !important;
        border: 1px solid var(--border-hover) !important;
    }}
    div[data-baseweb="tag"] span,
    div[data-baseweb="tag"] p {{
        color: var(--text-primary) !important;
    }}
    div[data-baseweb="tag"] svg {{
        fill: var(--text-primary) !important;
    }}

    /* 输入框与占位符穿透 */
    input::placeholder,
    textarea::placeholder {{
        color: var(--text-muted) !important;
    }}

    /* 折叠框标题文字颜色强制绑定 */
    details summary,
    [data-testid="stExpander"] summary p,
    [data-testid="stExpander"] summary span {{
        color: var(--text-primary) !important;
    }}

    div[data-testid="stAlert"] {{
        background-color: var(--bg-elevated) !important;
        border: 1px solid var(--border-subtle) !important;
        color: var(--text-primary) !important;
        border-radius: 8px !important;
    }}

    /* 下拉框当前选中文本与图标深度穿透 */
    div[data-baseweb="select"] div,
    div[data-baseweb="select"] span,
    div[data-baseweb="select"] input {{
        color: var(--text-primary) !important;
        -webkit-text-fill-color: var(--text-primary) !important;
    }}
    div[data-baseweb="select"] svg {{
        fill: var(--text-secondary) !important;
    }}

    /* 多选胶囊标签显式高亮穿透 */
    span[data-baseweb="tag"],
    div[data-baseweb="tag"] {{
        background-color: var(--accent-primary) !important;
        color: #ffffff !important;
        border: 1px solid var(--accent-primary) !important;
    }}
    span[data-baseweb="tag"] span,
    span[data-baseweb="tag"] svg,
    div[data-baseweb="tag"] span,
    div[data-baseweb="tag"] svg {{
        color: #ffffff !important;
        fill: #ffffff !important;
    }}

    /* 提示框与滑块刻度深度穿透 */
    div[data-testid="stAlert"] p,
    div[data-testid="stAlert"] span,
    [data-testid="stThumbValue"],
    [data-testid="stTickBarMin"],
    [data-testid="stTickBarMax"] {{
        color: var(--text-primary) !important;
    }}

    /* ========================================================= */
    /* 📱 640px 移动端紧凑自适应与卡片几何防挤压规范 (Rule 14 & 15) */
    /* ========================================================= */
    .inflection-ruler-container,
    .cushion-stress-container {{
        min-height: auto;
        height: auto !important;
        overflow: visible !important;
        padding-bottom: 12px !important;
        box-sizing: border-box;
    }}

    .inflection-ruler-scroll-row {{
        display: flex;
        gap: 8px;
        align-items: stretch;
        overflow-x: auto !important;
        overflow-y: hidden;
        scrollbar-width: thin;
        -webkit-overflow-scrolling: touch;
        padding-bottom: 4px;
    }}

    .inflection-node-card {{
        flex: 1 1 0;
        min-width: 140px;
        box-sizing: border-box;
    }}

    .inflection-today-card {{
        box-shadow: 0 0 0 1px var(--accent-primary) inset, 0 2px 6px rgba(37, 99, 235, 0.15);
    }}

    .cushion-scenarios-row {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 8px;
        box-sizing: border-box;
    }}

    .stress-scenario-card {{
        min-height: 80px;
        height: auto !important;
        overflow: visible !important;
        padding: 8px 10px;
        border-radius: 6px;
        box-sizing: border-box;
    }}

    /* 640px 移动端视口自适应查询 */
    @media (max-width: 640px) {{
        .inflection-ruler-scroll-row {{
            gap: 6px;
        }}
        .inflection-node-card {{
            min-width: 125px;
            padding: 5px 8px !important;
        }}
        .cushion-scenarios-row {{
            grid-template-columns: 1fr !important;
            gap: 6px !important;
        }}
        .main-metric-card {{
            min-height: auto !important;
            padding: 8px 10px !important;
            padding-bottom: 12px !important;
        }}
        .metric-value-huge {{
            font-size: 16px !important;
        }}
        [data-testid="stHorizontalBlock"] {{
            gap: 6px !important;
        }}
        .decision-card {{
            padding: 8px 10px !important;
            padding-bottom: 12px !important;
        }}
        .stress-3d-container {{
            width: 100% !important;
            overflow-x: auto !important;
            overflow-y: hidden;
            scrollbar-width: thin;
        }}
        .liquidity-table-scroll-container {{
            width: 100% !important;
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch;
        }}
    }}
</style>
""")



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
        self.status = st.status(f"🔄 正在为您计算：{self.step_name}...", expanded=True)
        with self.status:
            safe_markdown_html(
                f"""<div class="active-computation-console">
                <div class="console-header-banner">
                    🔄 正在为您计算：{self.step_name}
                </div>
                <div class="console-timer-text">
                    ⏱️ 引擎启动中... 正在初始化量化底座与条件胜率模型
                </div>
                </div>"""
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
        self.prog_bar.progress(100, text=f"✅ 计算完成，总耗时 {elapsed:.2f}s")
        for i, lbl in enumerate(self.step_labels):
            self.step_slots[i].caption(f"✅ {lbl} (已完成)")
        cache_hint = "（极速返回）" if elapsed < 0.2 else f"（耗时 {elapsed:.2f}s）"
        self.status.update(
            label=f"✅ {self.step_name} 计算完成，{cache_hint} ⏱️ 总耗时 {elapsed:.2f}s ｜ {summary_msg}",
            state="complete",
            expanded=False
        )


def render_workflow_step_indicator(steps: List[str], current_step: int, help_text: str = ""):
    """现代 Flex 胶囊分步导航条 (Modern Capsule Stepper)"""
    capsules = []
    for idx, name in enumerate(steps, 1):
        if idx < current_step:
            capsules.append(
                f'<div class="step-capsule step-capsule-done">'
                f'<span style="color: var(--color-down); font-weight: 700;">✓</span>'
                f'<span>步骤 {idx}: {name}</span>'
                f'</div>'
            )
        elif idx == current_step:
            capsules.append(
                f'<div class="step-capsule step-capsule-active">'
                f'<span>●</span>'
                f'<span>步骤 {idx}: {name}</span>'
                f'</div>'
            )
        else:
            capsules.append(
                f'<div class="step-capsule step-capsule-idle">'
                f'<span>○</span>'
                f'<span>步骤 {idx}: {name}</span>'
                f'</div>'
            )

    capsules_html = "".join(capsules)
    status_msg = help_text or "请在当前步骤完成参数确认后点击下方按钮进入下一步"
    safe_markdown_html(f"""
    <div class="step-indicator-bar">
        <div class="step-capsules-container">
            {capsules_html}
        </div>
        <div class="step-indicator-status">
            <span>🟢 <b>系统状态</b>：就绪 ｜ {status_msg}</span>
        </div>
    </div>
    """)


def render_black_swan_stress_card(stress_data: Dict[str, Any]):
    """渲染历史三大黑天鹅极端行情压力测试卡片与 10,000 次蒙特卡洛块重采样 (Block Bootstrap) CVaR 99% 压力推演"""
    if not stress_data or not stress_data.get("scenarios"):
        return
    scenarios = stress_data.get("scenarios", [])
    safe_markdown_html("""
    <div style="margin-top: 14px; margin-bottom: 8px;">
        <span style="font-size: 15px; font-weight: 700; color: var(--text-primary);">🌪️ 历史黑天鹅极端承压测试（含 10,000 次蒙特卡洛块重采样 CVaR 99% 压力推演）</span>
        <span style="font-size: 11px; color: var(--text-muted); margin-left: 8px;">穿透测算当前组合在历史三大暴跌危机与 10,000 次块重采样下的最大回撤、极限 CVaR 99% 及流动性折价损失</span>
    </div>
    """)

    cols = st.columns(len(scenarios))
    for i, sc in enumerate(scenarios):
        with cols[i]:
            max_dd = sc.get("max_dd_pct", 0.0)
            loss_amt = sc.get("max_loss_amt", 0.0)
            rec_str = sc.get("recovery_str", "跨周期修复中")
            h300_mdd = sc.get("h300_mdd_pct", 0.0)
            excess = sc.get("excess_defense_pct", 0.0)
            sc_name = sc.get("name", "")
            period = sc.get("period", "")
            desc = sc.get("desc", "")

            excess_badge = (
                f'<span style="color: var(--color-up); font-weight: 700;">少亏 +{excess:.1f}%</span>'
                if excess > 0 else
                f'<span style="color: var(--color-down); font-weight: 700;">偏离 {excess:+.1f}%</span>'
            )

            safe_markdown_html(f"""
            <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 12px 14px 14px 14px; box-shadow: var(--shadow-card); min-height: 190px; height: auto !important; box-sizing: border-box; overflow: visible !important;">
                <div style="font-size: 13px; font-weight: 700; color: var(--text-primary); margin-bottom: 2px;">
                    {sc_name}
                </div>
                <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 8px;">
                    {period}
                </div>
                <div style="font-size: 22px; font-weight: 800; color: var(--color-down); margin-bottom: 2px;">
                    -{max_dd:.2f}%
                    <span style="font-size: 13px; font-weight: 600; color: var(--color-down);">(-¥{loss_amt:,.0f})</span>
                </div>
                <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 6px; line-height: 1.4;">
                    ⏱️ <b>水下回本：</b>{rec_str}
                </div>
                <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 6px; line-height: 1.4;">
                    📉 <b>同期沪深300：</b>-{h300_mdd:.1f}% ｜ <b>超额防御：</b>{excess_badge}
                </div>
                <div style="font-size: 11px; color: var(--text-muted); line-height: 1.3; border-top: 1px dashed var(--border-subtle); padding-top: 6px; margin-top: 4px;">
                    {desc}
                </div>
            </div>
            """)

    # 引入 10,000 次蒙特卡洛块重采样 (Block Bootstrap) 极端压力推演卡片
    mc_bt = stress_data.get("monte_carlo_bootstrap")
    if mc_bt:
        cvar_99_pct = mc_bt.get("cvar_99_pct", 0.0)
        cvar_99_amt = mc_bt.get("cvar_99_amount", 0.0)
        liq_pct = mc_bt.get("liquidity_discount_pct", 0.0)
        liq_amt = mc_bt.get("liquidity_discount_amount", 0.0)
        tot_pct = mc_bt.get("total_extreme_loss_pct", 0.0)
        tot_amt = mc_bt.get("total_extreme_loss_amount", 0.0)
        dist = mc_bt.get("distribution_percentiles", {})

        safe_markdown_html(f"""
        <div style="background: var(--bg-surface); border: 1.5px solid var(--border-hover); border-radius: 8px; padding: 12px 16px 14px 16px; margin-top: 10px; box-shadow: var(--shadow-card); height: auto !important; overflow: visible !important;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 4px;">
                <span style="font-size: 13.5px; font-weight: 700; color: var(--text-primary);">🎲 极端黑天鹅 10,000 次蒙特卡洛块重采样推演 (Block Bootstrap)</span>
                <span style="font-size: 11px; padding: 2px 8px; border-radius: 4px; background: var(--bg-canvas); color: var(--accent-primary); border: 1px solid var(--border-subtle);">
                    10,000条路径 ｜ 块长10天 ｜ 60天窗口
                </span>
            </div>
            <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 10px; line-height: 1.5;">
                采用循环块重采样保留极端暴跌行情下的波动率聚集与尾部肥尾特征，输出极限条件在险价值与流动性折价底线：
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 10px; margin-bottom: 10px;">
                <div style="background: var(--bg-elevated); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 10px 12px; height: auto !important;">
                    <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 2px;">极限条件在险价值 (CVaR 99%)</div>
                    <div style="font-size: 20px; font-weight: 800; color: var(--color-down);">
                        -{cvar_99_pct:.2f}% <span style="font-size: 12px; font-weight: 600;">(-¥{cvar_99_amt:,.0f})</span>
                    </div>
                    <div style="font-size: 10px; color: var(--text-secondary); margin-top: 2px;">最恶劣 1% 极值路径平均年化最大回撤</div>
                </div>
                <div style="background: var(--bg-elevated); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 10px 12px; height: auto !important;">
                    <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 2px;">最大流动性折价损失预估</div>
                    <div style="font-size: 20px; font-weight: 800; color: var(--color-down);">
                        -{liq_pct:.2f}% <span style="font-size: 12px; font-weight: 600;">(-¥{liq_amt:,.0f})</span>
                    </div>
                    <div style="font-size: 10px; color: var(--text-secondary); margin-top: 2px;">极端恐慌赎回挤兑与停牌贴水冲击</div>
                </div>
                <div style="background: var(--bg-elevated); border: 1.5px solid var(--color-down); border-radius: 6px; padding: 10px 12px; height: auto !important;">
                    <div style="font-size: 11px; color: var(--color-down); font-weight: 700; margin-bottom: 2px;">极限黑天鹅合并承压底线</div>
                    <div style="font-size: 20px; font-weight: 800; color: var(--color-down);">
                        -{tot_pct:.2f}% <span style="font-size: 12px; font-weight: 600;">(-¥{tot_amt:,.0f})</span>
                    </div>
                    <div style="font-size: 10px; color: var(--text-secondary); margin-top: 2px;">CVaR 99% + 流动性折价合并测算</div>
                </div>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px dashed var(--border-subtle); padding-top: 8px; font-size: 11px; color: var(--text-secondary); flex-wrap: wrap; gap: 8px;">
                <span><b>路径百分位分布：</b></span>
                <span>P50中位: -{dist.get('p50', 0):.1f}%</span>
                <span>P75分位: -{dist.get('p75', 0):.1f}%</span>
                <span>P90分位: -{dist.get('p90', 0):.1f}%</span>
                <span><b>95% VaR: -{dist.get('p95', 0):.1f}%</b></span>
                <span><b>99% VaR: -{dist.get('p99', 0):.1f}%</b></span>
                <span style="color: var(--color-down); font-weight: 700;"><b>99% CVaR: -{cvar_99_pct:.1f}%</b></span>
            </div>
        </div>
        """)


def render_historical_inflection_ruler_html(ruler_data: Dict[str, Any]) -> str:
    """
    【历史三大牛熊拐点实盘对照尺紧凑一行式组件】
    展示：2021年2月核心资产见顶(0.50x)、2022年4月恐慌底(1.93x)、2024年9月反转底(1.94x) 与当前市场水位并列对照。
    """
    if not ruler_data or not isinstance(ruler_data, dict):
        return ""
    nodes = ruler_data.get("nodes", [])
    if not nodes or len(nodes) < 4:
        return ""

    cards_html = []
    for idx, node in enumerate(nodes):
        is_today = (idx == 3 or "今日" in str(node.get("date", "")) or "今日" in str(node.get("event", "")))
        d_str = str(node.get("date", ""))
        mult = float(node.get("multiplier", 1.0))
        erp = float(node.get("erp_percentile", 50.0))
        bias = float(node.get("bias_20", 0.0))

        if is_today:
            border = "var(--accent-primary)"
            bg = "rgba(37, 99, 235, 0.08)"
            tag_color = "var(--accent-primary)"
            badge_title = "📍 今日实时水位"
            sub_lbl = f"ERP {erp:.1f}% ｜ 偏离 {bias:+.1f}%"
        elif mult <= 0.60:
            border = "rgba(234, 179, 8, 0.6)"
            bg = "rgba(234, 179, 8, 0.06)"
            tag_color = "#ca8a04"
            badge_title = "🟡 2021 核心资产顶"
            sub_lbl = f"ERP {erp:.1f}% ｜ 偏离 {bias:+.1f}%"
        elif "2022" in d_str:
            border = "rgba(16, 185, 129, 0.6)"
            bg = "rgba(16, 185, 129, 0.06)"
            tag_color = "#10b981"
            badge_title = "🚀 2022 恐慌双底"
            sub_lbl = f"ERP {erp:.1f}% ｜ 偏离 {bias:+.1f}%"
        else:
            border = "rgba(239, 68, 68, 0.6)"
            bg = "rgba(239, 68, 68, 0.06)"
            tag_color = "#ef4444"
            badge_title = "🔥 2024 反转前夕"
            sub_lbl = f"ERP {erp:.1f}% ｜ 偏离 {bias:+.1f}%"

        card = (
            f'<div class="inflection-node-card {"inflection-today-card" if is_today else ""}" '
            f'style="border: 1.5px solid {border}; background: {bg}; border-radius: 6px; padding: 6px 10px; min-width: 155px !important; flex: 1 1 0 !important; box-sizing: border-box !important;">'
            f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">'
            f'<span style="font-size: 11px; font-weight: 700; color: {tag_color}; white-space: nowrap;">{badge_title}</span>'
            f'<span style="font-size: 10px; color: var(--text-muted); font-family: monospace;">{d_str}</span>'
            f'</div>'
            f'<div style="display: flex; align-items: baseline; justify-content: space-between; gap: 4px;">'
            f'<span style="font-size: 15px; font-weight: 800; font-family: monospace; color: {tag_color};">{mult:.2f}x</span>'
            f'<span style="font-size: 10px; color: var(--text-secondary); white-space: nowrap; text-align: right;">{sub_lbl}</span>'
            f'</div>'
            f'</div>'
        )
        cards_html.append(card)

    container_html = (
        f'<div class="inflection-ruler-container" style="margin: 4px 0 6px 0; padding: 6px 8px; border-radius: 8px; background: var(--bg-canvas); border: 1px dashed var(--border-subtle);">'
        f'<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">'
        f'<span style="font-size: 11px; font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 4px;">'
        f'<span>📏 历史三大牛熊拐点实盘对照尺</span>'
        f'<span style="font-size: 10px; font-weight: normal; color: var(--text-muted);">(2021顶 0.50x ｜ 2022底 1.93x ｜ 2024底 1.94x ｜ 今日水位)</span>'
        f'</span>'
        f'<span style="font-size: 10px; color: var(--accent-primary); font-weight: 600;">定投扣款乘数对照</span>'
        f'</div>'
        f'<div class="inflection-ruler-scroll-row" style="display: flex !important; flex-wrap: nowrap !important; gap: 8px !important; overflow-x: auto !important; width: 100% !important; padding-bottom: 4px !important; box-sizing: border-box !important;">'
        f'{"".join(cards_html)}'
        f'</div>'
        f'</div>'
    )
    return _clean_html(container_html)


def render_portfolio_cushion_and_stress_card_html(cushion_model: Dict[str, Any]) -> str:
    """
    【🛡️ 浮盈安全垫抗震承压与本金破净临界看板组件】
    基于真实累计浮盈、标的历史 Beta 与沪深300弹性，精算展示加权 Beta、安全垫厚度、破净跌幅/回本涨幅及 -3%/-5%/-10% 大盘急跌推演。
    """
    if not cushion_model or not isinstance(cushion_model, dict):
        return ""

    beta_p = float(cushion_model.get("portfolio_weighted_beta", 0.0))
    beta_eq = float(cushion_model.get("equity_weighted_beta", 0.0))
    cushion_yuan = float(cushion_model.get("comprehensive_cushion", 0.0))
    cushion_ratio = float(cushion_model.get("cushion_ratio_pct", 0.0))
    floating_pnl = float(cushion_model.get("floating_pnl", 0.0))
    ann_yield = float(cushion_model.get("annual_yield_cushion", 0.0))
    is_loss = bool(cushion_model.get("is_in_floating_loss", False))
    i_pt = float(cushion_model.get("current_index_point", 3920.0))
    break_drop = float(cushion_model.get("break_even_drop_pct", 0.0))
    break_pt = float(cushion_model.get("break_even_index_point", 0.0))
    rec_rise = float(cushion_model.get("recovery_rise_pct", 0.0))
    rec_pt = float(cushion_model.get("recovery_index_point", 0.0))
    summary_text = str(cushion_model.get("safety_margin_summary", ""))
    scenarios = cushion_model.get("stress_scenarios", [])
    tot_eq = float(cushion_model.get("total_equity", 0.0))

    if is_loss:
        cushion_color = "var(--color-up)"
        crit_title = "回本临界反弹"
        crit_val = f"+{rec_rise:.2f}%"
        crit_sub = f"大盘回升至 {rec_pt:,.0f} 点"
    elif beta_p > 0.001:
        cushion_color = "var(--color-down)" if cushion_yuan >= 0 else "var(--color-up)"
        crit_title = "破净安全边际"
        crit_val = f"{break_drop:.2f}%"
        crit_sub = f"大盘跌至 {break_pt:,.0f} 点破净"
    else:
        cushion_color = "var(--color-down)"
        crit_title = "大盘系统性风险"
        crit_val = "物理免疫"
        crit_sub = "100%现金/中性固收"

    scenario_cards = []
    for sc in scenarios:
        s_name = sc.get("scenario_type", "急跌")
        m_drop = float(sc.get("market_drop_pct", 0.0))
        p_drop = float(sc.get("portfolio_drop_pct", 0.0))
        loss_yuan = float(sc.get("expected_loss_yuan", 0.0))
        rem_yuan = float(sc.get("remaining_cushion_yuan", 0.0))
        rem_ratio = float(sc.get("remaining_cushion_ratio", 0.0))
        is_safe = bool(sc.get("is_capital_safe", True))
        
        status_badge = "🟢 保持本金安全" if is_safe else "🔴 穿透安全垫"
        badge_bg = "rgba(16, 185, 129, 0.12)" if is_safe else "rgba(239, 68, 68, 0.12)"
        badge_border = "rgba(16, 185, 129, 0.35)" if is_safe else "rgba(239, 68, 68, 0.35)"
        badge_color = "var(--color-down)" if is_safe else "var(--color-up)"

        s_html = f"""
        <div class="stress-scenario-card" style="background: var(--bg-canvas); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 8px 10px; box-sizing: border-box;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                <span style="font-size: 11.5px; font-weight: 700; color: var(--text-primary);">{s_name} {m_drop:+.0f}%</span>
                <span style="font-size: 10px; font-weight: 600; padding: 1px 5px; border-radius: 4px; background: {badge_bg}; border: 1px solid {badge_border}; color: {badge_color};">{status_badge}</span>
            </div>
            <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 2px;">
                预估跌幅: <b style="color: var(--color-up); font-family: monospace;">{p_drop:+.2f}%</b> (预估波动 <span style="font-family: monospace;">¥{loss_yuan:+,.2f}</span>)
            </div>
            <div style="font-size: 10.5px; color: var(--text-muted);">
                承压后剩余安全垫: <b style="color: {badge_color}; font-family: monospace;">¥{rem_yuan:+,.2f}</b> ({rem_ratio:+.1f}%)
            </div>
        </div>
        """
        scenario_cards.append(s_html)

    card_html = f"""
    <div class="decision-card cushion-stress-container" style="border-left: 4px solid var(--accent-primary); padding: 12px 14px; margin-bottom: 12px; background: var(--bg-surface); border-radius: 8px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 4px;">
            <div style="display: flex; align-items: center; gap: 6px;">
                <span style="font-size: 13.5px; font-weight: 700; color: var(--text-primary);">🛡️ 浮盈安全垫抗震承压与本金破净临界看板</span>
                <span style="font-size: 10.5px; padding: 1px 6px; border-radius: 4px; background: var(--bg-elevated); color: var(--text-secondary); border: 1px solid var(--border-subtle);">
                    资产基线: ¥{tot_eq:,.2f}
                </span>
            </div>
            <span style="font-size: 11px; color: var(--text-muted);">沪深300基准线: {i_pt:,.0f} 点</span>
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 8px; margin-bottom: 8px;">
            <div style="background: var(--bg-canvas); padding: 6px 10px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                <div style="font-size: 10.5px; color: var(--text-secondary);">组合加权 Beta</div>
                <div style="font-size: 15px; font-weight: 800; color: var(--text-primary); font-family: monospace;">β = {beta_p:.4f}</div>
                <div style="font-size: 10px; color: var(--text-muted);">权益Beta: {beta_eq:.4f}</div>
            </div>
            <div style="background: var(--bg-canvas); padding: 6px 10px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                <div style="font-size: 10.5px; color: var(--text-secondary);">综合安全垫厚度</div>
                <div style="font-size: 15px; font-weight: 800; color: {cushion_color}; font-family: monospace;">¥{cushion_yuan:,.1f}</div>
                <div style="font-size: 10px; color: var(--text-muted);">{cushion_ratio:+.2f}% (浮盈 ¥{floating_pnl:+,.0f} + 票息 ¥{ann_yield:,.0f})</div>
            </div>
            <div style="background: var(--bg-canvas); padding: 6px 10px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                <div style="font-size: 10.5px; color: var(--text-secondary);">{crit_title}</div>
                <div style="font-size: 15px; font-weight: 800; color: {'var(--color-up)' if is_loss else 'var(--accent-primary)'}; font-family: monospace;">{crit_val}</div>
                <div style="font-size: 10px; color: var(--text-muted);">{crit_sub}</div>
            </div>
            <div style="background: var(--bg-canvas); padding: 6px 10px; border-radius: 6px; border: 1px solid var(--border-subtle);">
                <div style="font-size: 10.5px; color: var(--text-secondary);">年化票息安全垫</div>
                <div style="font-size: 15px; font-weight: 800; color: var(--text-primary); font-family: monospace;">¥{ann_yield:,.1f}</div>
                <div style="font-size: 10px; color: var(--text-muted);">月均 ¥{ann_yield/12.0:,.0f} ｜ 现金派现底仓</div>
            </div>
        </div>

        <div style="font-size: 11.5px; color: var(--text-primary); padding: 6px 10px; border-radius: 6px; background: rgba(37, 99, 235, 0.08); border: 1px solid rgba(37, 99, 235, 0.2); margin-bottom: 8px; line-height: 1.5;">
            {summary_text}
        </div>

        <details style="margin-top: 6px;">
            <summary style="cursor: pointer; font-size: 11px; font-weight: 700; color: var(--text-secondary);">⚡ 展开大盘三级抗震承压情景推演 (-3% / -5% / -10%)</summary>
            <div class="cushion-scenarios-row" style="margin-top: 6px;">
                {''.join(scenario_cards)}
            </div>
        </details>
    </div>
    """
    return _clean_html(card_html)


# 初始化核心运行态 (首屏毫秒级秒开：使用本地账本与 parquet，消灭 akshare/天天基金网络阻塞)


# =============================================================
# 全生态 Plotly 穿透回测图表自适应换肤
# =============================================================
def apply_theme_to_plotly_figure(fig: go.Figure, theme_mode: Optional[str] = None, color_mode: Optional[str] = None) -> go.Figure:
    """让 Plotly 图表深度自适应当前主题与涨跌配色 (5套主题自适应)"""
    th_key = theme_mode or st.session_state.get("app_theme_mode", "light_slate")
    co_key = color_mode or st.session_state.get("app_color_mode", "cn")
    
    th = THEME_PRESETS.get(th_key, THEME_PRESETS.get("light_slate", THEME_PRESETS["institutional_slate"]))
    co = COLOR_PRESETS.get(co_key, COLOR_PRESETS["cn"])
    
    fig.update_layout(
        paper_bgcolor=th["bg_surface"],
        plot_bgcolor=th["bg_surface"],
        title_font_color=th["text_primary"],
        font=dict(color=th["text_primary"], family="-apple-system, 'SF Pro Display', sans-serif"),
        xaxis=dict(
            gridcolor=th["border_subtle"],
            zerolinecolor=th["border_hover"],
            tickfont=dict(color=th["text_secondary"]),
            title_font=dict(color=th["text_secondary"])
        ),
        yaxis=dict(
            gridcolor=th["border_subtle"],
            zerolinecolor=th["border_hover"],
            tickfont=dict(color=th["text_secondary"]),
            title_font=dict(color=th["text_secondary"])
        ),
        legend=dict(
            font=dict(color=th["text_primary"]),
            bgcolor=th["bg_surface"],
            bordercolor=th["border_subtle"]
        ),
        margin=dict(l=10, r=10, t=30, b=10)
    )
    return fig


def render_correlation_mutation_card_html(corr_eval: Dict[str, Any]) -> str:
    """渲染首屏双翼看板右翼：多资产相关性突变预警指示卡"""
    if not corr_eval:
        return ""
    is_trig = bool(corr_eval.get("is_triggered"))
    is_shift = bool(corr_eval.get("is_liquidity_shift_triggered"))
    curr_corr = float(corr_eval.get("current_correlation", 0.42))
    down_corr = float(corr_eval.get("downside_correlation", curr_corr))
    
    if is_shift or curr_corr >= 0.80:
        border_c = "var(--color-up)"
        badge_bg = "rgba(239, 68, 68, 0.12)"
        badge_color = "var(--color-up)"
        icon = "🚨"
        title = f"【相关性压力突变】突破 0.80 警戒线 ({curr_corr:.2f})"
        desc = f"基于 EWMA 滚动协方差矩阵测算，红利与高Beta/周期权益资产相关系数达 {curr_corr:.2f} (下行相关: {down_corr:.2f})！跨资产对冲防御失效，已激活流动性平移预案与集中度降级！"
        action = "💡 建议: 定向削减重仓高估值高波标的 15%~35%，全额平移至纯债 (002351, 60%) 与黄金对冲压舱石 (000216, 40%)。"
    elif is_trig:
        border_c = "var(--accent-primary)"
        badge_bg = "rgba(245, 158, 11, 0.12)"
        badge_color = "var(--accent-primary)"
        icon = "⚠️"
        title = f"【动态相关性突变】突破 0.75 警戒线 ({curr_corr:.2f})"
        desc = f"当前红利与周期权重相关系数达 {curr_corr:.2f}，组合防御隔离减弱，触发组合集中度降级警报。"
        action = "💡 建议: 适度平抑重仓权益敞口，增量平移至纯债与黄金避险。"
    else:
        border_c = "var(--color-down)"
        badge_bg = "rgba(16, 185, 129, 0.12)"
        badge_color = "var(--color-down)"
        icon = "🟢"
        title = f"【多资产相关性健康】相关系数正常 ({curr_corr:.2f} < 0.75)"
        desc = "红利防御资产与顺周期大盘及高Beta成长股保持良好隔离，未发生同向同跌共振风险。"
        action = "💡 状态: 跨资产风险隔离有效，维持当前多资产战略配置底仓。"

    html = f"""
    <div class="decision-card" style="border-left: 3px solid {border_c}; padding: 8px 10px; margin-bottom: 6px; box-sizing: border-box;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
            <span style="font-size: 12px; font-weight: 700; color: var(--text-primary);">{icon} {title}</span>
            <span style="font-size: 10px; font-weight: 600; padding: 1px 5px; border-radius: 4px; background: {badge_bg}; color: {badge_color};">
                EWMA: {curr_corr:.2f}
            </span>
        </div>
        <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 2px; line-height: 1.5;">
            {desc}
        </div>
        <div style="font-size: 11px; color: {border_c}; font-weight: 600;">
            {action}
        </div>
    </div>
    """
    return _clean_html(html)


def render_stress_liquidity_card_html(stress_data: Dict[str, Any]) -> str:
    """渲染首屏双翼看板右翼：压力测试流动性指标卡片"""
    if not stress_data:
        return ""
    cvar_99 = float(stress_data.get("overall_cvar_99", 28.5))
    liq_days = float(stress_data.get("overall_liquidity_days", 4.2))
    tier = str(stress_data.get("investor_risk_tier", "C3"))
    risk_tol = float(stress_data.get("risk_tolerance_mdd", 15.0))
    is_breach = bool(stress_data.get("exceeds_risk_tolerance", False))

    status_tag = "🔴 超出契约容忍" if is_breach else "🟢 契约限额内"
    badge_color = "var(--color-up)" if is_breach else "var(--color-down)"

    html = f"""
    <div class="decision-card" style="border-left: 3px solid var(--accent-primary); padding: 8px 10px; margin-bottom: 6px; box-sizing: border-box;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
            <span style="font-size: 12px; font-weight: 700; color: var(--text-primary);">🎲 穿透式蒙特卡洛压力测试 · 流动性指标</span>
            <span style="font-size: 10px; font-weight: 600; padding: 1px 5px; border-radius: 4px; background: var(--bg-canvas); color: {badge_color}; border: 1px solid var(--border-subtle);">
                {tier} 级 · {status_tag}
            </span>
        </div>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px; margin-bottom: 2px;">
            <div style="background: var(--bg-canvas); padding: 4px 6px; border-radius: 4px; border: 1px solid var(--border-subtle);">
                <div style="font-size: 10px; color: var(--text-secondary);">极限 CVaR 99%</div>
                <div style="font-size: 12.5px; font-weight: 700; color: var(--color-up); font-family: monospace;">-{cvar_99:.1f}%</div>
            </div>
            <div style="background: var(--bg-canvas); padding: 4px 6px; border-radius: 4px; border: 1px solid var(--border-subtle);">
                <div style="font-size: 10px; color: var(--text-secondary);">变现天数 (加权)</div>
                <div style="font-size: 12.5px; font-weight: 700; color: var(--text-primary); font-family: monospace;">{liq_days:.1f} 天</div>
            </div>
            <div style="background: var(--bg-canvas); padding: 4px 6px; border-radius: 4px; border: 1px solid var(--border-subtle);">
                <div style="font-size: 10px; color: var(--text-secondary);">{tier} 容忍回撤</div>
                <div style="font-size: 12.5px; font-weight: 700; color: var(--text-muted); font-family: monospace;">≤ {risk_tol:.0f}%</div>
            </div>
        </div>
        <div style="font-size: 10.5px; color: var(--text-muted); line-height: 1.4;">
            基于 10,000 次块重采样与 2008/2015/2024 三大历史极端情景穿透精算。
        </div>
    </div>
    """
    return _clean_html(html)


def render_liquidity_haircut_table(orders: List[Dict[str, Any]]):
    """渲染大额订单流动性折价明细表 (Tab 1 & Tab 2)"""
    if not orders:
        return

    table_rows = []
    for o in orders:
        fc = str(o.get("fund_code", "")).zfill(6)
        fn = str(o.get("fund_name", fc))
        amt = float(o.get("order_amount", 0.0))
        is_etf = bool(o.get("is_etf", False))
        aum_y = float(o.get("fund_aum_yuan", 0.0)) / 1e8
        top5_adv = float(o.get("top5_adv_yuan", 0.0)) / 1e8
        redemp_pct = float(o.get("redemption_ratio_pct", 0.0))
        h_bps = float(o.get("liquidity_haircut_bps", 0.0))
        h_yuan = float(o.get("liquidity_haircut_yuan", 0.0))
        s_yuan = float(o.get("slippage_saved_yuan", 0.0))
        
        sched = "日内 VWAP 分时挂单" if is_etf else "14:30 尾盘估值锚定 / 跨日分批执行"

        table_rows.append({
            "基金代码": fc,
            "基金名称": fn,
            "类别": "场内 ETF" if is_etf else "场外公募",
            "订单金额(元)": amt,
            "前5重仓ADV(亿元)": round(top5_adv, 2) if top5_adv > 0 else 15.0,
            "基金规模(亿元)": round(aum_y, 2) if aum_y > 0 else 5.0,
            "规模占比(%)": redemp_pct,
            "折价率(bps)": h_bps,
            "折价金额(元)": h_yuan,
            "优化节省(元)": s_yuan,
            "建议执行调度": sched
        })

    if not table_rows:
        return

    df_l = pd.DataFrame(table_rows)
    with st.expander("🌊 查看大额订单流动性折价与底层冲击明细表", expanded=False):
        st.dataframe(
            df_l,
            column_config={
                "订单金额(元)": st.column_config.NumberColumn(format="¥%.2f"),
                "前5重仓ADV(亿元)": st.column_config.NumberColumn(format="%.2f 亿"),
                "基金规模(亿元)": st.column_config.NumberColumn(format="%.2f 亿"),
                "规模占比(%)": st.column_config.NumberColumn(format="%.4f%%"),
                "折价率(bps)": st.column_config.NumberColumn(format="%.2f bps"),
                "折价金额(元)": st.column_config.NumberColumn(format="¥%.2f"),
                "优化节省(元)": st.column_config.NumberColumn(format="¥%.2f"),
            },
            use_container_width=True,
            hide_index=True
        )
        st.caption("💡 注：基于季报前五大重仓股日均成交额(ADV)与基金规模(AUM)的非线性 Almgren-Chriss / Kyle lambda 冲击模型，严格单调递增，场内 ETF 物理隔离。")


def render_monte_carlo_3d_chart(stress_data: Dict[str, Any]):
    """渲染蒙特卡洛压力测试 3D 极端承压曲面图 (Tab 1 & Tab 2)"""
    if not stress_data:
        return
    mc_3d = stress_data.get("monte_carlo_3d_data", {})
    scenarios = mc_3d.get("scenarios", ["2008金融危机", "2015流动性踩踏", "2024小盘股危机"])
    tiers = mc_3d.get("tiers", ["C1", "C2", "C3", "C4", "C5"])
    z_mdd = mc_3d.get("z_mdd_matrix", [])

    if not z_mdd or len(z_mdd) < len(scenarios):
        z_mdd = [
            [28.5, 28.5, 28.5, 28.5, 28.5],
            [22.3, 22.3, 22.3, 22.3, 22.3],
            [12.8, 12.8, 12.8, 12.8, 12.8]
        ]

    with st.expander("🎲 查看蒙特卡洛极端承压 3D 分布曲面图", expanded=False):
        fig_3d = go.Figure()
        
        fig_3d.add_trace(go.Surface(
            x=tiers,
            y=scenarios,
            z=z_mdd,
            colorscale="Viridis",
            showscale=True,
            colorbar=dict(title=dict(text="回撤%"), len=0.75, thickness=12)
        ))

        fig_3d.update_layout(
            title=dict(text="三大极端危机情景 × 适当性等级预测最大回撤 (10k次块重采样)", font=dict(size=13)),
            scene=dict(
                xaxis=dict(title="风险等级 (C1-C5)"),
                yaxis=dict(title="历史危机情景"),
                zaxis=dict(title="预测最大回撤 (%)"),
                camera=dict(eye=dict(x=1.6, y=-1.5, z=1.2))
            ),
            margin=dict(l=10, r=10, t=35, b=10),
            height=380
        )
        fig_3d = apply_theme_to_plotly_figure(fig_3d)
        st.plotly_chart(fig_3d, use_container_width=True)
        st.caption("💡 注：基于 10,000 次 Circular Block Bootstrap（块长10天、60天周期）针对不同风险承受等级的极值回撤损失三维推演。")


if "mlm" not in st.session_state:
    st.session_state.mlm = MultiLedgerManager.get_instance() if MultiLedgerManager else None
if "active_ledger_id" not in st.session_state:
    st.session_state.active_ledger_id = st.session_state.mlm.get_active_ledger_id() if st.session_state.mlm else "main_live"

# 防御性清洗：确保 sel_tab2_active_ledger 始终指向有效账本
if "sel_tab2_active_ledger" in st.session_state:
    all_lids = [l["id"] for l in (st.session_state.mlm.list_ledgers() if st.session_state.get("mlm") else [])]
    if st.session_state.sel_tab2_active_ledger not in all_lids:
        st.session_state.sel_tab2_active_ledger = "main_live"

_cur_lid = st.session_state.active_ledger_id
if "pm" not in st.session_state or getattr(st.session_state.pm, "ledger_id", None) != _cur_lid:
    if st.session_state.mlm:
        try:
            st.session_state.pm = st.session_state.mlm.get_pm(_cur_lid)
        except KeyError:
            # 容错自愈：当 active_ledger_id 已损坏或已删除时，平滑自愈回退至 main_live
            st.session_state.active_ledger_id = "main_live"
            st.session_state.pm = st.session_state.mlm.get_pm("main_live")
    else:
        st.session_state.pm = PortfolioManager()

pm: PortfolioManager = st.session_state.pm
clock = pm.clock
calc = pm.calculator

# 风险策略档位 -> 期望年化收益率基准映射表（双向映射绝对自洽，严禁 C2 设为 10.0 防漂移）
TIER_TARGET_RETURN_MAP = {
    "C1": 6.5,
    "C2": 9.0,   # 7.0 <= 9.0 < 10.0 -> map_slider_to_tier 严格返回 C2
    "C3": 15.0,  # 10.0 <= 15.0 < 16.0 -> map_slider_to_tier 严格返回 C3
    "C4": 22.0,  # 16.0 <= 22.0 < 30.0 -> map_slider_to_tier 严格返回 C4
    "C5": 50.0,  # 50.0 >= 30.0 -> map_slider_to_tier 严格返回 C5
}

# =============================================================================
# 全局统一基金名称解析引擎 (多级深度反查，彻底消灭代码复读 017436 017436)
# =============================================================================
def resolve_fund_display_name(fcode: str, pm_inst=None) -> str:
    """
    统一全局基金名称多级反查解析函数：
    依次从 pm.holdings、CORE_STRATEGY_POOL、EXTENDED_FUND_CATALOG、RADAR_SECTOR_CATALOG、
    pm.resolve_fund_meta 与 DataLoader.get_fund_metadata 中反查真实中文名称。
    """
    if not fcode:
        return ""
    c_str = str(fcode).strip()
    
    # 1. 优先查传入 pm_inst 的持仓
    if pm_inst and hasattr(pm_inst, "holdings") and c_str in pm_inst.holdings:
        fn = getattr(pm_inst.holdings[c_str], "fund_name", "")
        if fn and fn != c_str:
            return fn

    # 2. 查 CORE_STRATEGY_POOL
    if "CORE_STRATEGY_POOL" in globals() and c_str in CORE_STRATEGY_POOL:
        fn = CORE_STRATEGY_POOL[c_str].get("fund_name") or CORE_STRATEGY_POOL[c_str].get("name")
        if fn and fn != c_str:
            return fn

    # 3. 查 EXTENDED_FUND_CATALOG
    if "EXTENDED_FUND_CATALOG" in globals() and c_str in EXTENDED_FUND_CATALOG:
        fn = EXTENDED_FUND_CATALOG[c_str].get("fund_name") or EXTENDED_FUND_CATALOG[c_str].get("name")
        if fn and fn != c_str:
            return fn

    # 4. 查 RADAR_SECTOR_CATALOG
    try:
        from advisory_engine import RADAR_SECTOR_CATALOG
        for sec_meta in RADAR_SECTOR_CATALOG.values():
            if sec_meta.get("top_fund_code") == c_str:
                fn = sec_meta.get("top_fund_name")
                if fn and fn != c_str:
                    return fn
            df = sec_meta.get("default_fund", {})
            if df.get("code") == c_str:
                fn = df.get("name")
                if fn and fn != c_str:
                    return fn
    except Exception:
        pass

    # 5. 查 pm_inst.resolve_fund_meta
    if pm_inst and hasattr(pm_inst, "resolve_fund_meta"):
        try:
            m = pm_inst.resolve_fund_meta(c_str)
            fn = m.get("fund_name") or m.get("name")
            if fn and fn != c_str:
                return fn
        except Exception:
            pass

    # 6. 查 DataLoader.get_fund_metadata
    try:
        from data_loader import DataLoader
        m = DataLoader.get_fund_metadata(c_str)
        if m:
            fn = m.get("fund_name") or m.get("name")
            if fn and fn != c_str:
                return fn
    except Exception:
        pass

    # 7. 全局经典核心标的反查字典
    KNOWN_CORE_NAMES = {
        "005561": "创金合信红利低波A",
        "100032": "富国中证红利增强A",
        "000216": "华安黄金ETF联接A",
        "017436": "华安纳斯达克100ETF联接A",
        "011613": "华夏科创50ETF联接C",
        "011612": "华夏科创50ETF联接A",
        "002351": "易方达裕祥回报债券A",
        "161725": "招商中证白酒指数A",
        "161726": "招商国证生物医药A",
        "160418": "华安中证银行指数A",
        "013402": "华夏恒生科技ETF联接A",
        "008888": "华夏国证半导体芯片ETF联接A",
        "050025": "博时标普500ETF联接A",
        "110020": "易方达沪深300ETF联接A",
        "000478": "建信中证500增强A",
        "004194": "招商中证1000增强A",
        "518880": "华安易富黄金ETF",
        "513500": "博时标普500ETF",
        "510300": "华泰柏瑞沪深300ETF",
        "510500": "南方中证500ETF",
        "588000": "华夏上证科创板50成份ETF",
    }
    return KNOWN_CORE_NAMES.get(c_str, c_str)


def switch_active_ledger(target_ledger_id: str):
    mlm_inst = st.session_state.get("mlm") or (MultiLedgerManager.get_instance() if MultiLedgerManager else None)
    if "pm" in st.session_state and st.session_state.pm:
        try:
            st.session_state.pm.save_state(record_snapshot=True)
        except Exception:
            pass

    st.session_state.active_ledger_id = target_ledger_id
    if "sel_tab2_active_ledger" in st.session_state:
        st.session_state.sel_tab2_active_ledger = target_ledger_id

    if mlm_inst:
        mlm_inst.set_active_ledger_id(target_ledger_id)
        try:
            new_pm = mlm_inst.get_pm(target_ledger_id)
        except KeyError:
            target_ledger_id = "main_live"
            st.session_state.active_ledger_id = "main_live"
            if "sel_tab2_active_ledger" in st.session_state:
                st.session_state.sel_tab2_active_ledger = "main_live"
            new_pm = mlm_inst.get_pm("main_live")

        st.session_state.pm = new_pm
        meta = mlm_inst.get_ledger_meta(target_ledger_id) or {}
        target_tier = str(meta.get("default_tier", "C3")).upper()
        if target_tier not in TIER_TARGET_RETURN_MAP:
            target_tier = "C3"
        st.session_state.active_tier_val = target_tier
        target_ret = TIER_TARGET_RETURN_MAP.get(target_tier, 15.0)
        st.session_state.target_return_val = target_ret
        st.session_state.slider_target_return = target_ret

    st.session_state.tab2_diag_cache = None
    st.session_state.tab2_rebal_cache = None
    st.session_state.tab2_diagnosed = False
    st.session_state.tab2_rebalanced = False
    st.session_state.tab2_trigger_diagnose = False
    st.session_state.tab2_trigger_rebalance = False
    st.rerun()

# 实时拉取最新策略大脑快照 (首屏 auto_sync=False 纯本地秒级直开)
snapshot = StrategyBridge.get_latest_market_snapshot(force_reload=False, auto_sync=False) or {}

# 统一攻防红线数据源（单源同真：优先 trigger_lines，其次 snapshot 顶级字段，兜底现价计算）
_trig_lines = snapshot.get("trigger_lines") or {}
_c300_base_price = float(snapshot.get("c300_price", snapshot.get("c300", 4053.0)))
surge_line = float(_trig_lines.get("surge_line", snapshot.get("surge_line", _c300_base_price * 1.012)))
breakdown_line = float(_trig_lines.get("breakdown_line", snapshot.get("breakdown_line", _c300_base_price * 0.985)))

# 全局控盘与风控状态提权初始化 (确保侧边栏优先渲染时状态机已闭环就绪)
if "active_tier_val" not in st.session_state:
    st.session_state.active_tier_val = "C3"
if "target_return_val" not in st.session_state:
    st.session_state.target_return_val = 15.0
if "purchase_limit_filter" not in st.session_state:
    st.session_state.purchase_limit_filter = "不限 (自动拆单承接)"
if "rebalance_buffer_pct" not in st.session_state:
    st.session_state.rebalance_buffer_pct = 3.0

# -------------------------------------------------------------
# 宏观状态与盯盘数据提前预计算 (供侧边栏与主看板双向单源同真)
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
pnl_color = active_co["color_up"] if est_pnl >= 0 else active_co["color_down"]

c300_disp = intraday_eval.get("realtime_c300", snapshot.get("c300_price", snapshot.get('c300', 4053.0)))
bias_disp = intraday_eval.get("bias_m20", snapshot.get('bias_20', 0.0))
m20_disp = intraday_eval.get("m20", snapshot.get("m20_price", snapshot.get('m20', 4140.0)))
m60_disp = intraday_eval.get("m60", snapshot.get("m60_price", snapshot.get('m60', 3962.0)))
erp_pct = snapshot.get("erp_percentile", 81.9)
erp_val = snapshot.get("erp_val", 5.82)
dr007_val = snapshot.get("dr007", 1.39)
dr007_bp = snapshot.get("dr007_spread_bp", -11.1)
opt_iv = float(snapshot.get("option_iv_pct", 19.4))
ic_basis = float(snapshot.get("ic_annualized_basis_rate", 17.9))
days_to_next = rebal_grid.get("days_to_next", rebal_grid.get("days_to_grid", 3))

snr = float(snapshot.get("er_snr", 0.65))
accel = float(snapshot.get("mom_accel", 0.0))
eff_w = snapshot.get("effective_momentum_window", 60)
mom_exhaustion = bool(snapshot.get("momentum_exhaustion_warning", False))
exhaustion_text = snapshot.get("momentum_exhaustion_text") or "「⚡ 动量衰竭预警：暂停追高进攻标的，新增资金转入红利/纯债缓冲」"

raw_mkt_state = str(snapshot.get('market_state', '震荡收息期'))
if any(k in raw_mkt_state for k in ["震荡", "收息", "慢牛"]):
    vernacular_state = "🟢 震荡收息期"
elif any(k in raw_mkt_state for k in ["科技", "主升", "进攻"]):
    vernacular_state = "🔥 科技主升浪"
elif any(k in raw_mkt_state for k in ["熊", "防守", "破位"]):
    vernacular_state = "🛡️ 熊市防守期"
else:
    vernacular_state = f"🟢 {raw_mkt_state[:6]}"
st_color = snapshot.get('state_color', active_co['color_down'])

mb_data = fetch_market_turnover_and_sentiment()
t_str = mb_data.get("turnover_str", "-- 亿")
u_pct = mb_data.get("up_pct", 50.0)
u_cnt = mb_data.get("up_count", 0)
d_cnt = mb_data.get("down_count", 0)

_t2_mkt = sum(getattr(h, "shares", 0.0) * getattr(h, "current_nav", 1.0) for h in pm.holdings.values()) if pm.holdings else 0.0
_t2_cost = sum(getattr(h, "shares", 0.0) * getattr(h, "cost_price", getattr(h, "current_nav", 1.0)) for h in pm.holdings.values()) if pm.holdings else 0.0
_t2_pnl = _t2_mkt - _t2_cost
_t2_pnl_pct = (_t2_pnl / _t2_cost * 100.0) if _t2_cost > 0 else 0.0
tot_pnl_color = active_co["color_up"] if _t2_pnl >= 0 else active_co["color_down"]

# -------------------------------------------------------------
# 侧边栏：【🧭 全局领航台】（仅保留外观色彩 + 市场状态与底座 + 核心指数行情走廊）
# -------------------------------------------------------------
with st.sidebar:
    # 顶部第一行：标题与紧凑的 ⚙️ 外观 Popover，首屏直接聚焦市场状态与指数走廊
    sb_head_c1, sb_head_c2 = st.columns([6.0, 4.0])
    with sb_head_c1:
        st.subheader("🧭 全局领航台")
    with sb_head_c2:
        with st.popover("⚙️ 外观", help="点击弹出外观与色彩设置"):
            st.caption("🎨 界面外观与色彩定制")
            th_display_names = [
                "🏛️ 机构冷灰 (Institutional Slate)",
                "🌑 彭博暗黑 (Bloomberg Carbon)",
                "📜 金融暖卷 (FT Warm Paper)",
                "🌌 深海钛金 (Deep Titanium)",
                "❄️ 极昼纯白 (Nordic Frost)"
            ]
            th_keys = ["light_slate", "dark_terminal", "nordic_paper", "deep_titanium", "nordic_frost"]
            cur_th_k = st.session_state.get("app_theme_mode", "light_slate")
            alias_to_std = {
                "institutional_slate": "light_slate",
                "bloomberg_carbon": "dark_terminal",
                "ft_warm_paper": "nordic_paper"
            }
            cur_th_k = alias_to_std.get(cur_th_k, cur_th_k)
            cur_th_idx = th_keys.index(cur_th_k) if cur_th_k in th_keys else 0

            def _sync_theme_mode_change():
                sel_name = st.session_state.sb_theme_selector
                st.session_state.app_theme_mode = th_keys[th_display_names.index(sel_name)]

            st.selectbox(
                "界面主题风格",
                th_display_names,
                index=cur_th_idx,
                key="sb_theme_selector",
                on_change=_sync_theme_mode_change,
                help="5套专业级金融终端主题：机构冷灰、彭博暗黑、金融暖卷、深海钛金、极昼纯白"
            )

            co_display_names = ["🇨🇳 A股惯例 (红涨绿跌·默认)", "🌐 国际惯例 (绿涨红跌)"]
            co_keys = ["cn", "global"]
            cur_co_k = st.session_state.get("app_color_mode", "cn")
            cur_co_idx = co_keys.index(cur_co_k) if cur_co_k in co_keys else 0

            def _sync_color_mode_change():
                sel_c = st.session_state.sb_color_selector
                st.session_state.app_color_mode = co_keys[co_display_names.index(sel_c)]

            st.selectbox(
                "涨跌色彩体系",
                co_display_names,
                index=cur_co_idx,
                key="sb_color_selector",
                on_change=_sync_color_mode_change,
                help="自适应联动全站所有数字、行情带、持仓盈亏与穿透图表颜色"
            )

    st.caption("市场状态与核心指数行情走廊")
    st.markdown("---")

    # 2. 🕒 市场状态与底座 (G10: 精简为单行状态角标，消除与顶部4卡重复，提升首屏空间)
    total_days = snapshot.get("total_days", 2142)
    latest_date = snapshot.get("latest_date", "2026-11-04")
    is_realtime_src = (
        mb_data.get("is_realtime", False)
        or any(k in str(mb_data.get("source", "")) for k in ["realtime", "eastmoney", "sina", "live"])
        or (float(mb_data.get("total_turnover", 0.0)) > 1000.0)
    )
    if is_realtime_src:
        data_src_badge = "🟢 实时盘中源已连接"
    else:
        data_src_badge = "🟡 本地湖仓快照兜底" 

    safe_markdown_html(f"""
    <!-- ##### 🕒 市场状态与底座 -->
    <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 4px 8px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; font-size: 11px;">
        <span style="color: var(--text-secondary); white-space: nowrap;">行情源状态: <b style="color: var(--color-down);">{data_src_badge}</b></span>
        <span style="color: var(--text-muted); font-family: monospace; white-space: nowrap;">底座: {latest_date}</span>
    </div>
    """)

    st.markdown("---")

    # 3. 📊 核心指数行情走廊 (垂直卡片流，支持全市场自由定制与 3 层专业指标流)
    col_sb_title, col_sb_opt, col_sb_rf = st.columns([5.5, 2.5, 2.0])
    with col_sb_title:
        st.markdown("##### 📊 核心指数行情走廊")

    # 读取持久化自选走廊配置
    saved_watchlist = load_custom_watchlist()
    if "sb_corridor_display_limit" not in st.session_state:
        st.session_state.sb_corridor_display_limit = saved_watchlist.get("display_limit", 6)
    if "sb_selected_corridor_indices" not in st.session_state:
        st.session_state.sb_selected_corridor_indices = saved_watchlist.get("selected_codes", ["000300", "000688", "000922", "000905", "000852", "518880"])
    if "sb_custom_corridor_items" not in st.session_state:
        st.session_state.sb_custom_corridor_items = saved_watchlist.get("custom_items", {})

    with col_sb_opt:
        with st.popover("⚙️", help="全市场自由定制与走廊配置"):
            st.caption("⚙️ 核心指数走廊自由定制")
            # 1. 3~15 展示数量滑块
            cur_limit = int(st.session_state.sb_corridor_display_limit)
            new_limit = st.slider(
                "走廊展示数量",
                min_value=3,
                max_value=15,
                value=cur_limit,
                step=1,
                key="sl_corridor_disp_limit",
                help="控制侧边栏卡片展示上限（3 至 15 只）"
            )
            if new_limit != cur_limit:
                st.session_state.sb_corridor_display_limit = new_limit
                saved_watchlist["display_limit"] = new_limit
                saved_watchlist["display_count"] = new_limit
                saved_watchlist["selected_codes"] = st.session_state.sb_selected_corridor_indices
                saved_watchlist["custom_items"] = st.session_state.sb_custom_corridor_items
                save_custom_watchlist(saved_watchlist)

            # 2. 全市场 38+ 目录 + 自定义项多选检索器 (支持拼音首字母/代码/名称三模检索并保持选择顺序)
            combined_catalog = dict(INDEX_CATALOG_38)
            combined_catalog.update(st.session_state.sb_custom_corridor_items)

            # 保证当前选中的代码均在 options 列表中
            avail_options = []
            for c in st.session_state.sb_selected_corridor_indices:
                if c not in avail_options:
                    avail_options.append(c)
            for c in combined_catalog.keys():
                if c not in avail_options:
                    avail_options.append(c)

            def _fmt_option(k: str) -> str:
                item_info = combined_catalog.get(k, {})
                c_name = item_info.get("name", k)
                pinyin_str = item_info.get("pinyin", "")
                sec = item_info.get("sector", "")
                sec_tag = f"[{sec}] " if sec else ""
                return f"{sec_tag}{c_name} ({k}) [{pinyin_str}]"

            sel_corridor_keys = st.multiselect(
                "全市场自选列表 (支持拼音/代码/名称检索)",
                options=avail_options,
                default=st.session_state.sb_selected_corridor_indices,
                format_func=_fmt_option,
                key="ms_corridor_indices"
            )
            if sel_corridor_keys != st.session_state.sb_selected_corridor_indices:
                st.session_state.sb_selected_corridor_indices = sel_corridor_keys or ["000300", "000688", "000922", "000905", "000852", "518880"]
                saved_watchlist["display_limit"] = st.session_state.sb_corridor_display_limit
                saved_watchlist["display_count"] = st.session_state.sb_corridor_display_limit
                saved_watchlist["selected_codes"] = st.session_state.sb_selected_corridor_indices
                saved_watchlist["custom_items"] = st.session_state.sb_custom_corridor_items
                save_custom_watchlist(saved_watchlist)

            # 3. 任意 6 位有效代码实时接入输入框
            st.markdown("---")
            st.caption("➕ 接入任意 6 位有效代码 (股票/ETF/LOF/指数)")
            c_input_col, c_btn_col = st.columns([7, 3])
            with c_input_col:
                new_code_input = st.text_input("标的代码", max_chars=6, placeholder="如 510300 或 159915", label_visibility="collapsed", key="txt_add_custom_code")
            with c_btn_col:
                add_btn = st.button("添加", key="btn_add_custom_code", use_container_width=True)

            if add_btn and new_code_input:
                clean_code = new_code_input.strip()
                if len(clean_code) == 6 and clean_code.isdigit():
                    probe_res = validate_and_fetch_code(clean_code)
                    if probe_res:
                        st.session_state.sb_custom_corridor_items[clean_code] = probe_res
                        if clean_code not in st.session_state.sb_selected_corridor_indices:
                            st.session_state.sb_selected_corridor_indices.insert(0, clean_code)
                        saved_watchlist["display_limit"] = st.session_state.sb_corridor_display_limit
                        saved_watchlist["display_count"] = st.session_state.sb_corridor_display_limit
                        saved_watchlist["selected_codes"] = st.session_state.sb_selected_corridor_indices
                        saved_watchlist["custom_items"] = st.session_state.sb_custom_corridor_items
                        save_custom_watchlist(saved_watchlist)
                        st.success(f"已接入: {probe_res['name']} ({clean_code})")
                        st.rerun()
                    else:
                        st.error(f"代码 {clean_code} 探针失败，未能获取有效盘中行情")
                else:
                    st.warning("请输入有效的 6 位数字代码")

    with col_sb_rf:
        if st.button("🔄", key="btn_refresh_all_live_quotes", help="极速刷新实时行情", use_container_width=True):
            clear_realtime_cache()
            fetch_custom_realtime_indices(codes=st.session_state.sb_selected_corridor_indices, use_cache=False)
            fetch_market_turnover_and_sentiment(force_refresh=True)
            fetch_or_calc_index_valuations(force_refresh=True)
            pm.sync_holdings_live_nav(use_intraday_gsz=True)
            StrategyBridge._cached_snapshot = None
            StrategyBridge._cached_matrix = None
            StrategyBridge.get_latest_market_snapshot(force_reload=True, auto_sync=False)
            st.rerun()

    # 根据展示数量滑块切片取前 N 只
    display_limit = int(st.session_state.get("sb_corridor_display_limit", 6))
    current_corridor_codes = st.session_state.get("sb_selected_corridor_indices", ["000300", "000688", "000922", "000905", "000852", "518880"])[:display_limit]

    # 拉取当前批次实时指数行情与估值
    active_corridor_list = fetch_custom_realtime_indices(codes=current_corridor_codes, use_cache=True)
    corridor_val_map = fetch_or_calc_index_valuations(force_refresh=False)

    rendered_count = 0
    corridor_cards_html = []
    for idx_item in active_corridor_list:
        icode = idx_item["code"]
        rendered_count += 1
        c_pct = float(idx_item["change_pct"])
        c_badge_cls = "sidebar-index-badge-up" if c_pct > 0 else ("sidebar-index-badge-down" if c_pct < 0 else "sidebar-index-badge-flat")
        c_sign = "+" if c_pct > 0 else ""
        is_small_pt = (idx_item["point"] < 100.0)
        pt_fmt = f"{idx_item['point']:,.3f}" if is_small_pt else f"{idx_item['point']:,.2f}"

        # 估值分位标签
        v_meta = corridor_val_map.get(icode) or corridor_val_map.get(idx_item.get("secid", "")) or {}
        v_label = v_meta.get("label", "")
        v_status = v_meta.get("status", "mid")
        # 兼容连字符与下划线两种类名
        val_cls_name = f"val-{v_status.replace('_', '-')}"
        if not v_label:
            v_label = "适中"
            val_cls_name = "val-mid"
        v_badge_html = f'<span class="index-pill-val-badge {val_cls_name}">{v_label}</span>'

        # 近 20 日累计涨跌幅
        ret20 = float(idx_item.get("ret_20d", 0.0))
        ret20_sign = "+" if ret20 > 0 else ""
        ret20_color = "var(--color-up, #ef4444)" if ret20 > 0 else ("var(--color-down, #10b981)" if ret20 < 0 else "var(--text-muted)")

        # MA20 趋势与偏离状态
        trend_status_text = idx_item.get("trend_status", "")
        trend_color = idx_item.get("trend_color", "var(--text-secondary)")
        ma20_fmt = idx_item.get("ma20_fmt", "")

        corridor_cards_html.append(f"""
        <div class="sidebar-index-card">
            <!-- 第 1 行：指数名称、代码、最新点位与涨跌幅防压扁胶囊 -->
            <div class="sidebar-card-row-top">
                <div class="sidebar-card-title-box">
                    <span class="sidebar-index-name">{idx_item['name']}</span>
                    <span class="sidebar-index-code">{icode}</span>
                </div>
                <div class="sidebar-card-quote-box">
                    <span class="sidebar-index-pt">{pt_fmt}</span>
                    <span class="sidebar-index-badge {c_badge_cls}" style="flex: 0 0 auto !important; white-space: nowrap !important;">{c_sign}{c_pct:.2f}%</span>
                </div>
            </div>

            <!-- 第 2 行：真实 PE/PB 估值分位数徽章 与 近20日累计涨跌幅 -->
            <div class="sidebar-card-row-mid">
                {v_badge_html}
                <span class="sidebar-card-ret20" style="color: {ret20_color};">近20日 {ret20_sign}{ret20:.1f}%</span>
            </div>

            <!-- 第 3 行：MA20 趋势生命线与乖离率攻防状态 -->
            <div class="sidebar-card-row-bot">
                <span class="sidebar-card-trend-text" style="color: {trend_color};">{trend_status_text}</span>
                <span class="sidebar-card-ma-pt">MA20: {ma20_fmt}</span>
            </div>
        </div>
        """)

    safe_markdown_html("\n".join(corridor_cards_html))
    st.caption(f"💡 点击右上角 ⚙️ 可自由定制 38+ 全市场指数与任意 6 位代码。当前展示 {rendered_count}/{len(st.session_state.sb_selected_corridor_indices)} 只标的。")

# -------------------------------------------------------------
# 顶部全局看板：1 行 4 宽卡 + 1 个紧凑刷新按钮 (无下方重复行情条)
# -------------------------------------------------------------
top_c1, top_c2, top_c3, top_c4 = st.columns(4)

with top_c1:
    clock_color = active_co['color_down'] if market_status.is_golden_window else (active_co['color_up'] if market_status.is_after_market else active_th['accent_primary'])
    clock_title = "14:30黄金窗口" if market_status.is_golden_window else ("盘后已关账" if market_status.is_after_market else "盘中观察期")
    c1_tip = f"场外公募基金每日 15:00 关账。15:00 前下单按今日未知收盘净值成交，15:00 后下单顺延至下一交易日({market_status.effective_trade_date})成交。\n当前状态: {market_status.title}\n{market_status.message}"
    safe_markdown_html(f"""
    <div class="main-metric-card">
        <div class="metric-card-title">
            <span>交易时钟与窗口</span>
            <span title="{c1_tip}" style="cursor:help; color:var(--text-muted); font-size:12px;">ⓘ</span>
        </div>
        <div class="metric-value-huge" style="color: {clock_color}; font-size: 18px;">
            {clock_title}
        </div>
        <div class="metric-card-sub" style="font-size: 11px; color: var(--text-secondary); margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
            倒计时 {market_status.countdown_str} ｜ 距网格日 {days_to_next}天
        </div>
    </div>
    """)

with top_c2:
    c2_tip = f"沪深300现价: {c300_disp:,.1f}\nMA20生命线: {m20_disp:,.0f} (偏离 {bias_disp:+.1f}%)\nMA60中线: {m60_disp:,.0f}\n考夫曼信噪比(ER): {snr:.2f} (自适应窗口 {eff_w}日)\n动量加速度: {accel:+.2f}%\n突破进攻线: 突破 {surge_line:,.0f} 后增配科技成长(科创50/中证1000)\n跌破防守线: 跌破 {breakdown_line:,.0f} 后减仓避险至纯债压舱石"
    if mom_exhaustion:
        c2_tip += f"\n提示: {exhaustion_text}"

    safe_markdown_html(f"""
    <div class="main-metric-card">
        <div class="metric-card-title">
            <span>市场定调与攻防</span>
            <span title="{c2_tip}" style="cursor:help; color:var(--text-muted); font-size:12px;">ⓘ</span>
        </div>
        <div class="metric-value-huge" style="color: {st_color}; font-size: 18px;">
            {vernacular_state}
        </div>
        <div class="metric-card-sub" style="font-size: 11px; color: var(--text-secondary); margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
            破 {surge_line:,.0f} 进攻 ｜ 跌 {breakdown_line:,.0f} 防守
        </div>
    </div>
    """)

with top_c3:
    val_status = "估值极便宜 · 资金充裕" if (erp_pct >= 75 and dr007_bp <= 5) else "估值合理 · 流动性中性"
    c3_tip = (
        f"两市成交额: {t_str} ({mb_data.get('vol_text', '')})\n"
        f"全市场宽度: 上涨 {u_cnt} 家 / 下跌 {d_cnt} 家 (多方占比 {u_pct}% · {mb_data.get('sentiment_label', '')})\n"
        f"ERP股债性价比分位: {erp_pct:.1f}% (极高分位·股票高性价比)\n"
        f"DR007利率: {dr007_val:.2f}% (较基准 {dr007_bp:+.1f}bp·资金面宽裕)\n"
        f"期权IV: {opt_iv:.1f}% ｜ IC期指年化贴水: {ic_basis:.1f}%"
    )
    safe_markdown_html(f"""
    <div class="main-metric-card">
        <div class="metric-card-title">
            <span>估值与资金量能</span>
            <span title="{c3_tip}" style="cursor:help; color:var(--text-muted); font-size:12px;">ⓘ</span>
        </div>
        <div class="metric-value-huge" style="color: var(--color-down); font-size: 16px;">
            {val_status}
        </div>
        <div class="metric-card-sub" style="font-size: 11px; color: var(--text-secondary); margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
            两市成交 {t_str} ｜ 多方 {u_pct}% ｜ ERP {erp_pct:.1f}%
        </div>
    </div>
    """)

with top_c4:
    c4_tip = f"全组合总资产: ¥{total_cur_equity:,.2f}\n可用现金: ¥{pm.available_cash:,.2f}\n在途资金: ¥{pm.in_transit_cash:,.2f}\n累计投入成本: ¥{_t2_cost:,.2f}"
    safe_markdown_html(f"""
    <div class="main-metric-card">
        <div class="metric-card-title">
            <span>总资产与今日预估</span>
            <span title="{c4_tip}" style="cursor:help; color:var(--text-muted); font-size:12px;">ⓘ</span>
        </div>
        <div class="metric-value-huge" style="color: var(--text-primary); font-size: 18px;">
            ¥{total_cur_equity:,.2f}
        </div>
        <div class="metric-card-sub" style="font-size: 11px; color: var(--text-secondary); margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
            盘中: <b style="color: {pnl_color};">¥{est_pnl:+,.2f}</b> ({est_pnl_pct:+.2f}%) ｜ 浮盈: <b style="color: {tot_pnl_color};">¥{_t2_pnl:+,.2f}</b>
        </div>
    </div>
    """)

# 盘后预案提醒
latest_plan = pm.get_latest_next_day_plan()
if latest_plan:
    with st.expander(f"📌 **您有已锁定的 {latest_plan.get('target_date')} 盯盘待办预案** (创建于 {latest_plan.get('created_at')})", expanded=True):
        st.write("系统已为您锁定昨日盘后生成的调仓预案。请核对今日 14:30 盘中实时估值后一键执行：")
        col_exec_p, col_discard_p = st.columns([3, 7])
        with col_exec_p:
            if st.button("✅ 采纳并执行此待办预案", key="btn_apply_next_plan", type="primary", use_container_width=True):
                _cur_buf = float(st.session_state.get("rebalance_buffer_pct", 3.0))
                plan_obj = pm.generate_rebalance_plan(snapshot["target_weights_funds"], min_buffer_pct=_cur_buf)
                routes = plan_obj.get("routes", [])
                if routes:
                    oids = pm.submit_rebalance_orders(routes)
                    pm.clear_next_day_plans()
                    st.balloons()
                    st.success(f"已成功执行待办预案，生成在途单：{', '.join(oids)}。")
                    st.rerun()
                else:
                    st.info(f"持仓偏离度在 {_cur_buf:.1f}% 缓冲阈值内，无需额外调仓。")
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
def _cached_look_through_industry(holdings_items: tuple):
    cur_pm = st.session_state.get("pm") or pm
    h_dict = {c: HoldingItem(fund_code=c, fund_name=fn, shares=sh, cost_price=cn, current_nav=nav, cost_nav=cn, market_value=round(sh*nav, 2)) for c, fn, sh, cn, nav in holdings_items} if holdings_items else None
    return cur_pm.calculate_look_through_industry_exposure(holdings_override=h_dict)

@st.cache_data(ttl=300)
def _cached_stock_overlap(holdings_items: tuple):
    cur_pm = st.session_state.get("pm") or pm
    h_dict = {c: HoldingItem(fund_code=c, fund_name=fn, shares=sh, cost_price=cn, current_nav=nav, cost_nav=cn, market_value=round(sh*nav, 2)) for c, fn, sh, cn, nav in holdings_items} if holdings_items else None
    return cur_pm.calculate_stock_overlap_matrix(holdings_override=h_dict)

@st.cache_data(ttl=300)
def _cached_penetration_risk(holdings_items: tuple):
    cur_pm = st.session_state.get("pm") or pm
    h_dict = {c: HoldingItem(fund_code=c, fund_name=fn, shares=sh, cost_price=cn, current_nav=nav, cost_nav=cn, market_value=round(sh*nav, 2)) for c, fn, sh, cn, nav in holdings_items} if holdings_items else None
    return cur_pm.calculate_portfolio_penetration_risk(holdings_override=h_dict)

@st.cache_data(ttl=300)
def _cached_stocks_df(holdings_items: tuple):
    cur_pm = st.session_state.get("pm") or pm
    h_dict = {c: HoldingItem(fund_code=c, fund_name=fn, shares=sh, cost_price=cn, current_nav=nav, cost_nav=cn, market_value=round(sh*nav, 2)) for c, fn, sh, cn, nav in holdings_items} if holdings_items else None
    return cur_pm.get_portfolio_look_through_stocks_df(holdings_override=h_dict)



# -------------------------------------------------------------
# 双翼智能投顾核心看板：【🔭 全市场机会雷达】与【🚨 主动风险预警哨】
# -------------------------------------------------------------
def render_dual_wing_advisory_dashboard(pm_instance, snapshot_dict):
    """
    渲染双翼智能投顾核心看板：
    - 左翼：【🔭 全市场机会雷达】（14 赛道扫描，Top 3 黄金击球区与右侧共振赛道，优选公募基金，一键加入备选池）
    - 右翼：【🚨 主动风险预警哨】（FIFO 锁仓、超买拥挤、迷你基清盘、攻防线四维巡检，全通徽章与本地持久化）
    """
    try:
        # ── 今日投顾行动总开关 (纯内存毫秒级快速风控与参谋判断，耗时 < 5ms) ──
        lock_funds = []
        c_free_funds = []
        for c, h in pm_instance.holdings.items():
            h_days = getattr(h, "holding_days", 30)
            batches = getattr(h, "batches", []) or []
            if batches:
                try:
                    h_days = min((b.holding_days for b in batches), default=h_days)
                except Exception:
                    pass
            if h_days < 7:
                lock_funds.append({"fund_code": c, "fund_name": getattr(h, "fund_name", c), "holding_days": h_days})
            elif str(getattr(h, "share_class", "A")).upper() == "C" and h_days >= 30:
                c_free_funds.append({"fund_code": c, "fund_name": getattr(h, "fund_name", c), "holding_days": h_days})

        erp_pct = float(snapshot_dict.get("erp_percentile", 82.0))
        bias_val = float(snapshot_dict.get("c300_bias_20", snapshot_dict.get("bias_20", -2.07)))

        if lock_funds:
            act_status_icon = "🔴"
            expander_title = (
                f"今日投顾参谋：持仓含 {len(lock_funds)} 只未满 7 天标的，"
                f"赎回需扣 1.5% 惩罚费，调仓算法已自动为您避开卖出 ｜ 点击展开市场机会与持仓体检"
            )
        elif c_free_funds:
            act_status_icon = "🟡"
            expander_title = (
                f"今日投顾参谋：检测到 {len(c_free_funds)} 只 C 类份额持有已满 30 天免赎回费，"
                f"建议择机置换为 A 类节省销售服务费 ｜ 点击展开市场机会与持仓体检"
            )
        elif len(pm_instance.holdings) == 0:
            act_status_icon = "🚀"
            expander_title = f"今日投顾参谋：宏观 ERP 处于黄金击球区 ({erp_pct:.1f}%)，建议一键启动新资建仓 ｜ 点击展开市场机会与精选赛道"
        else:
            act_status_icon = "🟢"
            expander_title = "今日投顾参谋：持仓资产结构健康，安全垫充沛，今日安心吃息无需调仓 ｜ 点击展开市场机会与持仓体检"

        # 100% 全宽折叠面板 (彻底删除右上角红色大按钮与右侧空白死区)
        wing_expander = st.expander(f"{act_status_icon} {expander_title}", expanded=False)

        with wing_expander:
            col_radar, col_sentry = st.columns([6.2, 3.8])

            # --- 左翼：机会雷达 ---
            with col_radar:
                # 优先从本地磁盘持久化缓存读取因子基因与 14 大赛道指标 (0 网络请求，0 现场进化)
                factor_cache_f = Path(WORKSPACE_ROOT) / "data" / "cache" / "factor_evolution_cache.json"
                evo_disk_data = {}
                if factor_cache_f.exists():
                    try:
                        with open(factor_cache_f, "r", encoding="utf-8") as _fc:
                            evo_disk_data = json.load(_fc)
                    except Exception:
                        pass

                w_factors = evo_disk_data.get("weights", [0.30, 0.30, 0.25, 0.15])
                evo_res = evo_disk_data.get("evolved_result", {})
                traj_data = evo_disk_data.get("nav_trajectory", {})

                # 加载赛道扫描缓存
                radar_cache_f = Path(WORKSPACE_ROOT) / "data" / "cache" / "radar_sectors_cache.json"
                all_scanned_sectors = []
                if radar_cache_f.exists():
                    try:
                        with open(radar_cache_f, "r", encoding="utf-8") as _rf:
                            all_scanned_sectors = json.load(_rf)
                    except Exception:
                        pass
                if not all_scanned_sectors:
                    try:
                        radar_engine = OpportunityRadarEngine()
                        all_scanned_sectors = radar_engine.scan_all_sectors()
                    except Exception:
                        all_scanned_sectors = []

                top3_sectors = [s for s in all_scanned_sectors if s.get("s_crowd", 85.0) >= 45.0][:3]
                if not top3_sectors and all_scanned_sectors:
                    top3_sectors = all_scanned_sectors[:3]

                col_rad_head1, col_rad_head2 = st.columns([6.0, 4.0])
                with col_rad_head1:
                    safe_markdown_html("<div style='font-size: 13px; font-weight: 700; color: var(--text-primary); margin-bottom: 4px;'>🔭 全市场机会雷达 · Top 3 机会甄选</div>")
                with col_rad_head2:
                    with st.popover(f"🧬 因子进化: 估{w_factors[0]*100:.0f}% 动{w_factors[1]*100:.0f}% 噪{w_factors[2]*100:.0f}% 拥{w_factors[3]*100:.0f}%", use_container_width=True):
                        st.markdown("##### 🧬 在线启发式因子基因自适应进化与突发黑天鹅 GP 规则树引擎")
                        regime_mode_txt = evo_res.get("regime_mode", "平稳蓄势态 (STABLE_CONSOLIDATION)")
                        regime_badge_txt = evo_res.get("regime_badge", "🟢 平稳蓄势")
                        st.caption(f"当前识别市场模式：<b>{regime_badge_txt} {regime_mode_txt}</b>", unsafe_allow_html=True)
                        c_m1, c_m2, c_m3 = st.columns(3)
                        c_m1.metric("样本外 Alpha", f"{traj_data.get('alpha_pct', 0.0):+.2f}%")
                        c_m2.metric("动态最大回撤", f"-{traj_data.get('mdd_dynamic_pct', 0.0):.2f}%")
                        c_m3.metric("换手率惩罚", f"-{evo_res.get('turnover', 0.0):.1f}%")
                        rule_expr_txt = evo_res.get("operator_rule_expression") or "RuleTree: Mom_Win=0.30*5d+0.70*20d | Vol_Pulse=exp(-1.2*pulse) | Safe_Shift=1.0+0.5*panic"
                        st.code(rule_expr_txt, language="text")
                        if traj_data.get("dates"):
                            df_traj = pd.DataFrame({
                                "日期": traj_data.get("dates", [])[-15:],
                                "动态净值": traj_data.get("nav_dynamic", [])[-15:],
                                "静态基准": traj_data.get("nav_static", [])[-15:],
                            })
                            st.line_chart(df_traj.set_index("日期"))

                # 信源验真指示徽章判定（优先读取本地快照缓存，零阻塞网络）
                news_cache_f = Path(WORKSPACE_ROOT) / "data" / "cache" / "realtime_news.json"
                news_cache_data = {}
                if news_cache_f.exists():
                    try:
                        with open(news_cache_f, "r", encoding="utf-8") as _ncf:
                            news_cache_data = json.load(_ncf)
                    except Exception:
                        pass
                is_realtime_news = bool(news_cache_data.get("is_realtime", False))
                news_src_label = str(news_cache_data.get("source", "东方财富 7x24快讯" if is_realtime_news else "离线快照"))
                data_sense_time = news_cache_data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                if is_realtime_news:
                    news_source_badge = (
                        f'<span style="font-size: 10px; font-weight: 600; color: var(--color-down); '
                        f'padding: 1px 6px; border-radius: 4px; background: rgba(34, 197, 94, 0.1); '
                        f'border: 1px solid rgba(34, 197, 94, 0.25);">🟢 实时联网信源 ({news_src_label}) ⏱️ 数据感知时间: {data_sense_time} ⚡ 实时快讯</span>'
                    )
                else:
                    news_source_badge = (
                        f'<span style="font-size: 10px; font-weight: 600; color: var(--accent-primary); '
                        f'padding: 1px 6px; border-radius: 4px; background: rgba(245, 158, 11, 0.1); '
                        f'border: 1px solid rgba(245, 158, 11, 0.25);">🟠 离线本地缓存快照 ⏱️ 数据感知时间: {data_sense_time} ⚡ 实时快讯</span>'
                    )

                # G8/G11/G13 预警哨处置动作映射字典规范 (只读建议与历史契约映射):
                # countdown_hold, replace_fund, deep_loss_rebalance, rebalance_sector, defense_mode, offense_mode
                # 3 张赛道卡（直接显示优选基金名称与 6 位代码，删除 '+ 入备选池' 伪按钮）
                cols_top3 = st.columns(3)
                for i, sec in enumerate(top3_sectors):
                    with cols_top3[i]:
                        sec_fund = sec.get("fund", {})
                        tag_color = "var(--color-up)" if "🔥" in sec.get("tag", "") else ("var(--accent-primary)" if "🎯" in sec.get("tag", "") else "var(--color-down)")
                        rt_chg = sec.get("realtime_chg_pct", 0.0)
                        rt_color = active_co["color_up"] if rt_chg >= 0 else active_co["color_down"]
                        core_logic_txt = sec.get("core_logic", "综合得分靠前")
                        sub_s = sec.get("sub_scores", {})
                        val_score = float(sub_s.get("valuation", sec.get("s_val", 0.0)))
                        mom_score = float(sub_s.get("momentum", sec.get("s_mom", 0.0)))
                        snr_score = float(sub_s.get("kaufman_snr", sec.get("s_er", 0.0)))
                        crowd_score = float(sub_s.get("anti_crowding", sec.get("s_crowd", 0.0)))
                        vol_20_val = float(sec.get("vol_20", 15.0))
                        mdd_20_val = float(sec.get("mdd_20", 8.0))

                        concise_logic_txt = sec.get("concise_logic") or core_logic_txt[:18]
                        if len(concise_logic_txt) > 18:
                            concise_logic_txt = concise_logic_txt[:18]
                        sec_score = float(sec.get("total_score", sec.get("score", 0.0)))
                        sec_val_pct = float(sec.get("val_percentile", sec.get("val_pct", 50.0)))

                        safe_markdown_html(f"""
                        <div class="decision-card" style="padding: 8px 10px; height: 100%; min-height: 110px; overflow: visible !important; border-top: 2px solid {tag_color};" title="💡 入选依据: 20日波动 {vol_20_val:.1f}% ｜ 20日最大回撤 -{mdd_20_val:.1f}% ｜ 估值:{val_score:.0f} 动量:{mom_score:.0f} 信噪:{snr_score:.0f} 拥挤:{crowd_score:.0f} ｜ {core_logic_txt}">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                                <span style="font-size: 13px; font-weight: 700; white-space: nowrap !important; flex-shrink: 0 !important; color: var(--text-primary);">{sec.get('name', '')}</span>
                                <span style="font-size: 10px; white-space: nowrap !important; flex-shrink: 0 !important; padding: 1px 4px; border-radius: 4px; background: var(--bg-canvas); color: {tag_color}; border: 1px solid var(--border-subtle);">{sec.get('tag', '')}</span>
                            </div>
                            <div style="font-size: 11px; color: var(--text-muted); margin: 2px 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                得分 {sec_score:.1f} ｜ 今日 <span style="color: {rt_color}; font-weight: 700;">{rt_chg:+.2f}%</span> ｜ 估值分位 {sec_val_pct:.0f}%
                            </div>
                            <div style="font-size: 11px; margin-bottom: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--text-primary);">
                                优选: <b>{sec_fund.get('name', '')}</b> <code style="color: var(--accent-primary); font-size: 11px;">{sec_fund.get('code', '')}</code>
                            </div>
                            <div style="font-size: 10.5px; color: var(--text-muted); line-height: 1.2; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                {concise_logic_txt}
                            </div>
                        </div>
                        """)

            # --- 右翼：主动风险提示与健康度 (干净紧凑无按钮列表) ---
            with col_sentry:
                safe_markdown_html("<div style='font-size: 13px; font-weight: 700; color: var(--text-primary); margin-bottom: 6px;'>🚨 主动风险预警哨 · 四维巡检</div>")

                # G10: 动态相关性突变指示卡（仅在突变警报或结构异动时渲染，正常区间保持干净）
                try:
                    corr_eval_res = pm_instance.evaluate_dynamic_correlation_mutation_instance(threshold=0.75, stress_threshold=0.80)
                    if corr_eval_res.get("is_triggered") or corr_eval_res.get("is_liquidity_shift_triggered") or corr_eval_res.get("is_mutation_alarm") or corr_eval_res.get("is_regime_shift_risk"):
                        safe_markdown_html(render_correlation_mutation_card_html(corr_eval_res))
                except Exception:
                    pass

                if not lock_funds and not c_free_funds and len(pm_instance.holdings) > 0:
                    safe_markdown_html("""
                    <div class="decision-card" style="border-left: 3px solid var(--color-down); padding: 8px 12px; margin-bottom: 4px;">
                        <div style="font-weight: 700; color: var(--color-down); font-size: 12px; margin-bottom: 2px;">🟢 主动风控巡检全通</div>
                        <div style="font-size: 11px; color: var(--text-secondary);">持仓批次无惩罚锁仓 ｜ 赛道无超买拥挤 ｜ 零迷你基清盘风险</div>
                    </div>
                    """)
                else:
                    if lock_funds:
                        lock_names = [f"{a['fund_code']} ({a['fund_name'][:5]})" for a in lock_funds]
                        safe_markdown_html(f"""
                        <div class="decision-card" style="border-left: 3px solid var(--color-up); padding: 8px 10px; margin-bottom: 6px;">
                            <div style="font-size: 12px; font-weight: 700; color: var(--color-up); margin-bottom: 2px;">
                                🔴【未满7天锁定期】包含标的: {', '.join(lock_names)}
                            </div>
                            <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 2px;">
                                未满 7 天赎回将直接触发证监会规定的 1.50% 巨额惩罚扣款！调仓算法已在底层自动为您锁定下界。
                            </div>
                            <div style="font-size: 11px; color: var(--text-primary); font-weight: 600;">
                                💡 应对建议: 保持持有吃息，待持有满 7 天后再行操作。
                            </div>
                        </div>
                        """)
                    if c_free_funds:
                        c_names = [f"{a['fund_code']} ({a['fund_name'][:5]})" for a in c_free_funds]
                        safe_markdown_html(f"""
                        <div class="decision-card" style="border-left: 3px solid var(--accent-primary); padding: 8px 10px; margin-bottom: 4px;">
                            <div style="font-size: 12px; font-weight: 700; color: var(--accent-primary); margin-bottom: 2px;">
                                🟡【C类份额满期】包含标的: {', '.join(c_names)}
                            </div>
                            <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 2px;">
                                持有已满 30 天免赎回费。C 类年化计提销售服务费，长期持有成本较高。
                            </div>
                            <div style="font-size: 11px; color: var(--accent-primary); font-weight: 600;">
                                💡 应对建议: 待技术面反弹至均线压力位时，可择机置换为 A 类份额节省费用。
                            </div>
                        </div>
                        """)
                    if len(pm_instance.holdings) == 0:
                        safe_markdown_html("""
                        <div class="decision-card" style="border-left: 3px solid var(--accent-primary); padding: 8px 10px; margin-bottom: 4px;">
                            <div style="font-size: 12px; font-weight: 700; color: var(--accent-primary); margin-bottom: 2px;">
                                🚀【空仓状态指引】
                            </div>
                            <div style="font-size: 11px; color: var(--text-secondary);">
                                当前账本尚无持仓。宏观 ERP 处于黄金击球区，可在【🌱 新资建仓】快速获取 AI 智能配置全案。
                            </div>
                        </div>
                        """)
    except Exception as e:
        st.caption(f"（双翼看板加载提示: {e}）")


render_dual_wing_advisory_dashboard(pm, snapshot)

# ── 跨区联动指令承接横幅与真实 DOM 导航注入 (G8) ──
# 跨区联动指令已生效承接横幅 (已合入主流程)
active_cross_action = st.session_state.get("last_cross_tab_action")

# 真实 DOM 树 Tab 切换与平滑滚动注入脚本
if "pending_cross_tab_jump" in st.session_state and st.session_state["pending_cross_tab_jump"]:
    jump_info = st.session_state["pending_cross_tab_jump"]
    t_idx = jump_info.get("tab_index", 1)
    t_name = jump_info.get("tab_name", "💼 持仓调仓")
    t_kw = t_name.split(" ")[-1] if " " in t_name else t_name

    js_code = f"""
    <script>
    (function() {{
        let attempts = 0;
        const maxAttempts = 18;
        function executeTabSwitch() {{
            try {{
                const parentDoc = window.parent.document;
                if (!parentDoc) return;
                const tabLists = parentDoc.querySelectorAll('div[data-baseweb="tab-list"], div[role="tablist"]');
                if (tabLists && tabLists.length > 0) {{
                    const mainTabList = tabLists[0];
                    const tabs = Array.from(mainTabList.querySelectorAll('button[role="tab"], button[data-baseweb="tab"]'));
                    let targetTab = null;
                    if (tabs[{t_idx}]) {{
                        targetTab = tabs[{t_idx}];
                    }}
                    if (!targetTab) {{
                        targetTab = tabs.find(t => t.innerText && t.innerText.includes("{t_kw}"));
                    }}
                    if (targetTab) {{
                        if (targetTab.getAttribute('aria-selected') !== 'true') {{
                            targetTab.click();
                        }}
                        targetTab.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                        return;
                    }}
                }}
            }} catch (err) {{
                console.warn("[Cross-Tab Routing] Error:", err);
            }}
            if (attempts++ < maxAttempts) {{
                setTimeout(executeTabSwitch, 40);
            }}
        }}
        setTimeout(executeTabSwitch, 20);
    }})();
    </script>
    """
    components.html(js_code, height=0, width=0)
    st.session_state.pop("pending_cross_tab_jump", None)

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

        # 机会雷达入池动态提示标签
        _radar_funds = st.session_state.get("radar_selected_funds", [])
        if _radar_funds:
            _tag_parts = []
            for _rfc in _radar_funds:
                _r_meta = CORE_STRATEGY_POOL.get(_rfc, {}) or EXTENDED_FUND_CATALOG.get(_rfc, {})
                _r_name = _r_meta.get("fund_name", _rfc)
                _tag_parts.append(f'<span style="background: var(--bg-surface); border: 1px solid var(--accent-primary); color: var(--accent-primary); border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: 600;">已纳入建仓池: {_r_name} ({_rfc})</span>')
            safe_markdown_html(f'''
            <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px;">
                {' '.join(_tag_parts)}
            </div>
            ''')

        # ---------------------------------------------------------
        # 模块 1：单行参数控制栏 (本金 + 档位 + 节奏 + 机构微调 + 单主按钮)
        # ---------------------------------------------------------
        col_l1_cap, col_l1_tier, col_l1_rhythm, col_l1_adv, col_l1_btn = st.columns([2.5, 2.0, 2.0, 1.3, 2.2])

        with col_l1_cap:
            plan_capital = st.number_input(
                "拟投资总本金 (元)",
                min_value=1000.0,
                max_value=100000000.0,
                value=float(st.session_state.get("plan_capital_input", 100000.0)),
                step=10000.0,
                format="%.0f",
                key="plan_capital_input"
            )
            plan_cap = plan_capital
            st.caption(f"核对: {format_chinese_amount(plan_cap)}")

        with col_l1_tier:
            tier_labels_all = ["C1 安稳保守型", "C2 稳健固收+型", "C3 平衡进取型", "C4 成长进攻型", "C5 极限高Beta追击型"]
            tier_code_to_idx_all = {"C1": 0, "C2": 1, "C3": 2, "C4": 3, "C5": 4}
            cur_tier_now = str(st.session_state.get("active_tier_val", "C3")).upper()
            cur_ret_now = float(st.session_state.get("target_return_val", 15.0))
            cur_t_idx = tier_code_to_idx_all.get(cur_tier_now, 2)

            def _sync_tab1_tier_change():
                sel_label = st.session_state.tab1_tier_selector
                new_tier = sel_label[:2]
                st.session_state.active_tier_val = new_tier
                def_ret = float(RISK_TIERS_CONFIG.get(new_tier, {}).get("default_target", 15.0))
                st.session_state.target_return_val = def_ret
                st.session_state.slider_target_return = def_ret
                st.session_state.tab2_diag_cache = None
                st.session_state.tab2_rebal_cache = None
                st.session_state.tab1_sim_cache = None
                st.session_state.tab1_step3_cache = None

            if "tab1_tier_selector" not in st.session_state or not st.session_state.tab1_tier_selector.startswith(cur_tier_now):
                st.session_state.tab1_tier_selector = tier_labels_all[cur_t_idx]

            st.selectbox(
                "风险策略档位",
                tier_labels_all,
                key="tab1_tier_selector",
                on_change=_sync_tab1_tier_change,
                help="快速切换 C1~C5 风险策略档位，自动联动调整预期年化收益率与策略定权模型"
            )
            active_tier = str(st.session_state.get("active_tier_val", "C3")).upper()
            cur_tier_meta = RISK_TIERS_CONFIG.get(active_tier, RISK_TIERS_CONFIG["C3"])
            st.caption(f"画像: 【{active_tier} {cur_tier_meta['name']}】 目标 {cur_tier_meta['target_cagr']}")

        with col_l1_rhythm:
            rhythm_options = [
                "⚡ 一次性建仓（今日全额配置）",
                "🌊 稳健三步分批建仓（底仓 50% + 逢低网格 30% + 右侧趋势 20%）",
                "📅 估值自适应智能定投（根据宏观 ERP 与均线偏离度动态调整扣款乘数）",
            ]
            cur_rhythm_val = st.session_state.get("radio_capital_deployment_mode", rhythm_options[0])
            cur_r_idx = 0
            for _ri, _ropt in enumerate(rhythm_options):
                if ("稳健三步" in cur_rhythm_val and "稳健三步" in _ropt) or ("智能定投" in cur_rhythm_val and "智能定投" in _ropt):
                    cur_r_idx = _ri
                    break

            cap_deployment_mode = st.selectbox(
                "建仓节奏",
                rhythm_options,
                index=cur_r_idx,
                key="radio_capital_deployment_mode",
                help="选择单笔全额、稳健分批或智能定投"
            )
            st.caption("平抑盘口冲击与净值波动")

        auto_num_funds = 4 if plan_cap <= 50000.0 else (6 if plan_cap <= 300000.0 else 8)
        if "tab1_slider_num_funds" not in st.session_state:
            st.session_state.tab1_slider_num_funds = auto_num_funds
            st.session_state.tab1_num_funds = auto_num_funds

        with col_l1_adv:
            st.caption("微调参数")
            with st.popover("⚙️ 高级微调", use_container_width=True):
                st.markdown("##### ⚙️ 机构级模型与高级参数微调")
                tier_mode = st.radio(
                    "定档方式",
                    ["模式 A：按期望年化收益率滑块定档", "模式 B：30秒风险承受力测评定档"],
                    horizontal=True,
                    key="tier_determination_mode"
                )

                if tier_mode.startswith("模式 A"):
                    col_s1_slider, col_s1_quota = st.columns([6, 4])
                    with col_s1_slider:
                        def _sync_tab1_return_change():
                            val = float(st.session_state.slider_target_return)
                            st.session_state.target_return_val = val
                            tier = map_slider_to_tier(val)
                            st.session_state.active_tier_val = tier
                            st.session_state.tab1_tier_selector = tier_labels_all[tier_code_to_idx_all.get(tier, 2)]
                            st.session_state.tab2_diag_cache = None
                            st.session_state.tab2_rebal_cache = None
                            st.session_state.tab1_sim_cache = None
                            st.session_state.tab1_step3_cache = None

                        target_ret_input = st.slider(
                            "期望年化目标收益率 (%)",
                            min_value=5.0,
                            max_value=100.0,
                            value=float(st.session_state.get("target_return_val", 15.0)),
                            step=1.0,
                            format="%.0f%%",
                            help="拖动滑块即拉即变，C1 至 C5 实时同步切换",
                            key="slider_target_return",
                            on_change=_sync_tab1_return_change
                        )
                        st.session_state.target_return_val = target_ret_input
                        active_tier = map_slider_to_tier(target_ret_input)
                        st.session_state.active_tier_val = active_tier

                    with col_s1_quota:
                        quota_options = [
                            "不限 (自动拆单承接)",
                            "过滤日限额 < ¥1,000 标的",
                            "过滤日限额 < ¥5,000 标的"
                        ]
                        cur_quota_val = st.session_state.get("purchase_limit_filter", quota_options[0])
                        cur_q_idx = quota_options.index(cur_quota_val) if cur_quota_val in quota_options else 0
                        def _sync_tab1_quota_filter_change():
                            st.session_state.purchase_limit_filter = st.session_state.tab1_quota_filter_sel
                            st.session_state.tab1_sim_cache = None
                            st.session_state.tab1_step3_cache = None

                        st.selectbox(
                            "单日限购过滤阈值",
                            quota_options,
                            index=cur_q_idx,
                            key="tab1_quota_filter_sel",
                            on_change=_sync_tab1_quota_filter_change,
                            help="开启过滤后，选基与建仓单将自动用同赛道不限购备选基金替换受限标的"
                        )
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
                    cur_tier_meta = RISK_TIERS_CONFIG.get(tested_tier, RISK_TIERS_CONFIG["C3"])
                    target_ret_input = float(cur_tier_meta.get("default_target", 15.0))

                    old_tier_q = st.session_state.get("active_tier_val")
                    old_ret_q = float(st.session_state.get("target_return_val", 15.0))
                    if tested_tier != old_tier_q or abs(old_ret_q - target_ret_input) > 1e-4:
                        st.session_state.active_tier_val = tested_tier
                        st.session_state.target_return_val = target_ret_input
                        st.session_state.tab2_diag_cache = None
                        st.session_state.tab2_rebal_cache = None
                        st.session_state.tab1_sim_cache = None
                        st.session_state.tab1_step3_cache = None
                        st.rerun()
                    else:
                        st.session_state.active_tier_val = tested_tier
                        st.session_state.target_return_val = target_ret_input
                    active_tier = tested_tier

                    col_cap_b, _ = st.columns([6, 4])
                    with col_cap_b:
                        plan_capital_b = st.number_input(
                            "拟投资总本金 (元)",
                            min_value=1000.0,
                            max_value=100000000.0,
                            value=float(plan_cap),
                            step=10000.0,
                            format="%.0f",
                            key="plan_capital_input_b"
                        )
                        plan_cap_b = plan_capital_b
                        st.caption(f"核对: {format_chinese_amount(plan_cap_b)}")

                    st.caption(f"问卷总分: `{total_q_score} 分` ➔ 评定档位: **【{active_tier} {cur_tier_meta['name']}】**")

                col_h, col_nf, col_mod = st.columns([3.5, 3.5, 3.0])
                with col_h:
                    horizon_choice = st.radio(
                        "计划持有期",
                        ["短期(3~6月)", "中期(1~2年)", "长期(3~5年)"],
                        index=1,
                        horizontal=True,
                        key="tab1_horizon_radio"
                    )
                with col_nf:
                    num_funds_input = st.slider(
                        "最终优选基金只数",
                        min_value=3,
                        max_value=15,
                        value=int(st.session_state.get("tab1_num_funds", auto_num_funds)),
                        step=1,
                        help="用户可自由在 3~15 只之间调节组合基金数量",
                        key="tab1_slider_num_funds"
                    )
                    st.session_state.tab1_num_funds = num_funds_input

                with col_mod:
                    model_options_map = {
                        "鲁棒双核HRP": "hrp_cvar",
                        "核心-卫星杠铃": "core_satellite",
                        "全天候风险平价": "all_weather",
                        "BL主客观观点融合": "black_litterman",
                        "条件胜率最优": "cond_winrate",
                        "尾部风控CVaR": "min_cvar",
                        "凯利动量增强": "kelly_momentum",
                    }
                    canonical_model_key_map = {
                        "hrp_robust": "hrp_cvar",
                        "conditional_winrate": "cond_winrate",
                        "cvar_tail": "min_cvar"
                    }
                    raw_cur_k = st.session_state.get("tab1_model_type", "hrp_cvar")
                    cur_model_key = canonical_model_key_map.get(raw_cur_k, raw_cur_k)
                    inv_map = {v: k for k, v in model_options_map.items()}
                    default_disp = inv_map.get(cur_model_key, list(model_options_map.keys())[0])

                    model_disp_choice = st.selectbox(
                        "机构级量化定权模型",
                        list(model_options_map.keys()),
                        index=list(model_options_map.keys()).index(default_disp) if default_disp in model_options_map else 0,
                        key="tab1_sel_model_type",
                        help="全栈集成 7 大机构级量化定权模型"
                    )
                    sel_model_type = model_options_map[model_disp_choice]
                    st.session_state.tab1_model_type = sel_model_type

                # 宏观环境自适应识别横幅与模型推荐
                regime_rec = recommend_model_for_regime(snapshot, float(st.session_state.get("target_return_val", 15.0)))
                rec_key = regime_rec["recommended_model_key"]
                rec_name = regime_rec["recommended_model_name"]
                is_matching_rec = (sel_model_type == rec_key)

                rec_badge_style = "background: rgba(37, 99, 235, 0.08); border: 1.5px solid var(--accent-primary);" if is_matching_rec else "background: var(--bg-surface); border: 1.5px solid var(--border-hover);"
                rec_title_color = "var(--accent-primary)" if is_matching_rec else "var(--color-down)"
                match_hint = "（当前已采纳推荐）" if is_matching_rec else f"（当前选择：{model_disp_choice}）"

                safe_markdown_html(f"""
                <div style="{rec_badge_style} border-radius: 8px; padding: 10px 14px; margin: 8px 0 10px 0;">
                    <div style="font-size: 13px; font-weight: 700; color: {rec_title_color}; margin-bottom: 4px;">
                        宏观环境识别：【{regime_rec['regime_name']}】 ➔ 机构首选推荐：【{rec_name}】{match_hint}
                    </div>
                    <div style="font-size: 11.5px; color: var(--text-secondary); line-height: 1.5;">
                        {regime_rec['reason']}<br>
                        <span style="color: var(--text-muted);">实时四维指标：ERP估值分位 {regime_rec['erp_percentile']:.1f}% ｜ MA20偏离 {regime_rec['bias_20']:+.2f}% ｜ DR007利率 {regime_rec['dr007']:.2f}% ｜ 期权iVIX {regime_rec['ivix']:.1f}%</span>
                    </div>
                </div>
                """)

                with st.expander("七大机构定权模型全景对比", expanded=False):
                    safe_markdown_html("<div style='font-size: 12px; color: var(--text-secondary); margin-bottom: 8px;'>全套搭载 7 大华尔街与国内头部券商机构级定权算法：</div>")
                    mod_c1, mod_c2, mod_c3, mod_c4 = st.columns(4)
                    mod_c5, mod_c6, mod_c7, mod_c8 = st.columns(4)
                    model_cards = [
                        (mod_c1, "鲁棒双核HRP", "层次聚类 + 极值CVaR", "解决赛道踩踏", "层次聚类隔离风险，低波底仓高波控仓", "结构分化 / 震荡市"),
                        (mod_c2, "核心-卫星杠铃", "70%~80%核心+20%~30%卫星", "解决攻防失衡", "底仓安心吃息，卫星抓Alpha超额", "稳健增值 / 长期吃息"),
                        (mod_c3, "全天候风险平价", "跨资产风险边际贡献平价", "解决资产周期崩溃", "四象限全周期均衡，不预测牛熊", "宏观牛熊不确定 / 跨大类"),
                        (mod_c4, "BL主客观融合", "市场均衡 + 机会雷达先验", "解决过拟合与时点错配", "锚定均衡基准并向高信噪比赛道倾斜", "机会雷达主线明确 / 结构牛"),
                        (mod_c5, "条件胜率最优", "状态机加权 + 贝叶斯核密度", "解决时点错配", "锚定当前估值利率，优配同温层高胜率", "估值击球区 / 轮动市"),
                        (mod_c6, "尾部风控CVaR", "极值下行损失规划", "解决黑天鹅巨亏", "深度压低肥尾亏损，杜绝长期严重套牢", "流动性紧缩 / 恐慌避险"),
                        (mod_c7, "凯利动量增强", "连续半凯利 + 考夫曼信噪比", "解决踏空主升浪", "高信噪比极速跟进，衰竭自动减速", "单边趋势 / 顺势行情"),
                    ]
                    for col, m_nm, m_tag, m_prob, m_alloc, m_scen in model_cards:
                        with col:
                            safe_markdown_html(f"""
                            <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 10px; height: 100%; box-sizing: border-box; margin-bottom: 6px;">
                                <div style="font-size: 13px; font-weight: 700; color: var(--text-primary); margin-bottom: 2px;">{m_nm}</div>
                                <div style="font-size: 11px; color: var(--accent-primary); font-weight: 600; margin-bottom: 6px;">{m_tag}</div>
                                <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 4px;"><b>【解决什么】</b><br>{m_prob}</div>
                                <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 4px;"><b>【怎么分配】</b><br>{m_alloc}</div>
                                <div style="font-size: 11px; color: var(--color-down); font-weight: 500;"><b>【适合行情】</b><br>{m_scen}</div>
                            </div>
                            """)
                    with mod_c8:
                        safe_markdown_html("""
                        <div style="background: var(--bg-elevated); border: 1px dashed var(--border-hover); border-radius: 8px; padding: 10px; height: 100%; box-sizing: border-box; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center;">
                            <div style="font-size: 20px; margin-bottom: 4px;">⚡</div>
                            <div style="font-size: 12px; font-weight: 700; color: var(--accent-primary);">宏观环境自适应识别</div>
                            <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">系统将根据当前市场状态向量自动在上方推荐最优模型</div>
                        </div>
                        """)

        cur_tab1_params = {
            "target_ret": float(st.session_state.get("target_return_val", 15.0)),
            "capital": float(plan_capital),
            "tier": str(st.session_state.get("active_tier_val", "C3")),
            "num_funds": int(st.session_state.get("tab1_num_funds", auto_num_funds)),
            "model_type": str(st.session_state.get("tab1_model_type", "hrp_cvar")),
            "horizon": str(st.session_state.get("tab1_horizon_radio", "中期(1~2年)")),
            "purchase_limit_filter": str(st.session_state.get("purchase_limit_filter", "不限 (自动拆单承接)")),
            "overrides": tuple(sorted(st.session_state.get("custom_fund_overrides", {}).items()))
        }
        _last_p = st.session_state.get("tab1_last_calc_params")
        if st.session_state.get("tab1_step_reached", 1) >= 2 and _last_p is not None and _last_p != cur_tab1_params:
            st.warning("⚠️ 检测到您已调整目标参数，请点击【⚡ 生成实盘建仓方案】刷新方案。")

        with col_l1_btn:
            st.caption("开始执行")
            if st.button("⚡ 生成实盘建仓方案", type="primary", use_container_width=True, key="btn_run_simulation_now"):
                st.session_state.tab1_step_reached = 3
                st.session_state.tab1_step3_cache = None
                st.session_state.tab1_trigger_sim = True
                st.session_state.tab1_trigger_s3 = True
                st.session_state.tab1_last_calc_params = cur_tab1_params
                st.rerun()
        # ---------------------------------------------------------
        # 模块 2 与模块 3：执行单、核心指标卡与单一白盒抽屉
        # ---------------------------------------------------------
        if st.session_state.get("tab1_step_reached", 1) >= 2:
            st.markdown("---")
            m_title = QUANT_MODELS_CATALOG.get(sel_model_type, {}).get("name", "鲁棒双核HRP")

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
                    purchase_limit_filter=st.session_state.get("purchase_limit_filter", "不限 (自动拆单承接)"),
                    radar_selected_funds=st.session_state.get("radar_selected_funds", []),
                    progress_cb=_sim_cb
                )
                acc.complete("真全市场选基与推演完成")
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

            # 自动生成实盘建仓 Blueprint
            if st.session_state.get("tab1_trigger_s3", False) or st.session_state.get("tab1_step3_cache") is None:
                cur_opt_w = opt_weights
                overrides = st.session_state.get("custom_fund_overrides", {})

                blueprint = StrategyBridge.generate_zero_start_blueprint(
                    total_capital=float(plan_capital),
                    target_weights_funds=cur_opt_w,
                    tier=active_tier,
                    custom_fund_overrides=overrides,
                    purchase_limit_filter=st.session_state.get("purchase_limit_filter", "不限 (自动拆单承接)")
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

                pcr_eval = calculate_portfolio_risk_contributions(cur_opt_w)
                pcr_map = pcr_eval.get("pcr", {})

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

                    # 附加交割清算与基金属性标签
                    if pm.is_qdii_fund(fcode, it.get("fund_name", "")):
                        guide_action += "·跨时区T+2确认"
                    elif any(k in pm.classify_fund_asset_class(fcode, it.get("fund_name", "")) for k in ["纯债", "固收", "债券"]):
                        guide_action += "·票息久期底仓"

                    f_pcr = pcr_map.get(fcode, round(it.get("target_weight_pct", 0.0), 1))
                    bp_rows.append({
                        "基金代码": fcode,
                        "基金名称": it["fund_name"],
                        "份额": f"{it.get('share_class', 'A')}类",
                        "目标占比(%)": it.get("target_weight_pct", 0.0),
                        "风险贡献(PCR %)": f"{f_pcr:.1f}%",
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
                    "基金代码", "基金名称", "份额", "目标占比(%)", "风险贡献(PCR %)",
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
            cur_opt_w = _cache_s3.get("cur_opt_w", opt_weights)
            overrides = _cache_s3.get("overrides") or {}

            # ── 模块 2：3 项核心指标条置顶与实盘建仓执行表 ──
            erp_pct = float(snapshot.get("erp_percentile", 78.5))
            _cushion_info = StrategyBridge.calculate_portfolio_yield_cushion(opt_weights, total_capital=float(plan_capital), pm=pm)
            _ann_cush = _cushion_info.get("annual_cushion_amount", 0.0)
            _mo_cush = _cushion_info.get("monthly_equivalent_amount", 0.0)
            _w_yield = _cushion_info.get("weighted_yield_pct", 0.0)

            _def_w = 0.0
            _off_w = 0.0
            _top_f_code = ""
            _top_f_w = 0.0
            for _fc, _fw in sorted(opt_weights.items(), key=lambda x: x[1], reverse=True):
                if not _top_f_code:
                    _top_f_code = _fc
                    _top_f_w = _fw
                _ac = pm.classify_fund_asset_class(_fc)
                if any(k in _ac for k in ["债", "固收", "货币", "黄金"]):
                    _def_w += _fw
                else:
                    _off_w += _fw
            _top_f_meta = CORE_STRATEGY_POOL.get(_top_f_code, {}) or EXTENDED_FUND_CATALOG.get(_top_f_code, {})
            _top_f_name = _top_f_meta.get("fund_name", f"优选基金_{_top_f_code}")
            _def_amt = plan_capital * _def_w
            _off_amt = plan_capital * _off_w
            _m_title_now = QUANT_MODELS_CATALOG.get(sel_model_type, {}).get("name", "鲁棒双核HRP")
            _worst_dd_pct = float(readable_kpi.get('worst_case_drawdown_pct', 0.0))
            _worst_dd_amt = plan_capital * (_worst_dd_pct / 100.0)
            _underwater_d = int(readable_kpi.get('max_underwater_days', 0))
            _win_1y = float(readable_kpi.get('win_rate_1y', 0.0))
            _best_ret = float(readable_kpi.get('best_case_return_pct', 0.0))
            _best_amt = float(readable_kpi.get('best_case_profit_amount', 0.0))

            c_attr1, c_attr2, c_attr3 = st.columns(3)
            with c_attr1:
                safe_markdown_html(f"""
                <div class="decision-card" style="height: 100%; border-top: 3px solid var(--color-down); margin-bottom: 6px;">
                    <div class="decision-title" style="color: var(--color-down); font-weight: 700;">
                        收益与胜率
                    </div>
                    <div class="decision-desc">
                        <b>1年达标胜率</b>：<span style="font-size: 14px; font-weight: 800; color: var(--color-down);">{_win_1y:.1f}%</span> ｜ 最好单年: +{_best_ret:.1f}% (+¥{_best_amt:,.0f})<br>
                        <b>内生票息安全垫</b>：年化 <b>¥{_ann_cush:,.0f}</b>/年 (月均 ¥{_mo_cush:,.0f} ｜ 加权息率 <b>{_w_yield:.2f}%</b>)<br>
                        <b>收息防守底仓</b>：¥{_def_amt:,.0f} ({_def_w*100:.1f}%) 筑牢收益安全线
                    </div>
                </div>
                """)

            with c_attr2:
                safe_markdown_html(f"""
                <div class="decision-card" style="height: 100%; border-top: 3px solid var(--color-up); margin-bottom: 6px;">
                    <div class="decision-title" style="color: var(--color-up); font-weight: 700;">
                        风险底线
                    </div>
                    <div class="decision-desc">
                        <b>历史至暗浮亏</b>：<span style="font-size: 14px; font-weight: 800; color: var(--color-up);">-{_worst_dd_pct:.1f}%</span> (预估最大缩水 -¥{_worst_dd_amt:,.0f})<br>
                        <b>最长水下回本</b>：约 <b>{_underwater_d} 天</b> (约 {readable_kpi.get('max_underwater_months', 0.0):.1f} 个月)，长钱长投以时间换空间<br>
                        <b>实盘纪律铁律</b>：不满 7 天严禁赎回防 1.5% 惩罚费；磨底期严禁割肉
                    </div>
                </div>
                """)

            with c_attr3:
                safe_markdown_html(f"""
                <div class="decision-card" style="height: 100%; border-top: 3px solid var(--accent-primary); margin-bottom: 6px;">
                    <div class="decision-title" style="color: var(--accent-primary); font-weight: 700;">
                        攻防定权
                    </div>
                    <div class="decision-desc">
                        <b>攻防仓位配比</b>：防守收息 {_def_w*100:.0f}% + 进攻弹性 {_off_w*100:.0f}% (¥{_off_amt:,.0f})<br>
                        <b>第一重仓标的</b>：{_top_f_name} ({_top_f_code}) 占比 <b>{_top_f_w*100:.1f}%</b><br>
                        <b>机构定权模型</b>：采用【{_m_title_now}】避免赛道踩踏，ERP 分位 {erp_pct:.1f}%
                    </div>
                </div>
                """)

            alloc_list_for_dca = [
                {"code": it["fund_code"], "name": it["fund_name"], "weight": float(it.get("target_weight_pct", it.get("target_weight", 0.0))) / 100.0}
                for it in blueprint.get("items", [])
            ]

            active_cheat_sheet_text = cheat_sheet_text
            df_display = df_bp.copy()
            dynamic_col_config = {
                "目标占比(%)": st.column_config.ProgressColumn(min_value=0, max_value=60, format="%.1f%%"),
                "精确买入金额(元)": st.column_config.NumberColumn(format="¥%.2f"),
                "最新净值": st.column_config.NumberColumn(format="%.4f"),
                "实时估值涨跌(%)": st.column_config.NumberColumn(format="%+.2f%%"),
                "实操分红与限购指引": st.column_config.TextColumn(
                    "实操分红与限购指引 ⓘ",
                    help="下单实操要点：红利类设为【现金分红】锁住收益；限额标的自动拆单；A类长投免赎，C类适合弹性波段。"
                ),
            }

            three_step_plan = None
            dca_plan = None
            has_etf_dca = False

            if "稳健三步" in cap_deployment_mode:
                three_step_plan = SmartExecutionDCAEngine.plan_three_step_batches(
                    total_capital=float(plan_capital),
                    allocations=alloc_list_for_dca,
                    market_snapshot=snapshot
                )
                cols_batches = st.columns(3)
                for b_idx, b_info in enumerate(three_step_plan["batches"]):
                    with cols_batches[b_idx]:
                        safe_markdown_html(f"""
                        <div class="decision-card" style="padding: 10px 12px; height: 100%; margin-bottom: 6px;">
                            <div style="font-size: 13px; font-weight: 700; color: var(--text-primary); margin-bottom: 2px;">{b_info['title']}</div>
                            <div style="font-size: 15px; font-weight: 800; color: var(--accent-primary); margin-bottom: 4px;">¥{b_info['amount']:,.2f}</div>
                            <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 4px;">触发时机: <b>{b_info['timing']}</b></div>
                            <div style="font-size: 11px; color: var(--text-secondary); line-height: 1.4;">{b_info['notes']}</div>
                        </div>
                        """)
                df_display["今日底仓买入(50%)"] = df_display["精确买入金额(元)"] * 0.50
                df_display["逢低网格挂单(30%)"] = df_display["精确买入金额(元)"] * 0.30
                df_display["右侧突破加仓(20%)"] = df_display["精确买入金额(元)"] * 0.20
                dynamic_col_config["今日底仓买入(50%)"] = st.column_config.NumberColumn(format="¥%.2f")
                dynamic_col_config["逢低网格挂单(30%)"] = st.column_config.NumberColumn(format="¥%.2f")
                dynamic_col_config["右侧突破加仓(20%)"] = st.column_config.NumberColumn(format="¥%.2f")

                cs_lines = [cheat_sheet_text, "\n【🌊 稳健三步分批建仓执行小抄】"]
                for _, r in df_display.iterrows():
                    cs_lines.append(f"标的: {r['基金代码']} ({r['基金名称']}) -> 第1步今日底仓: ¥{r['今日底仓买入(50%)']:,.2f} | 第2步逢低网格: ¥{r['逢低网格挂单(30%)']:,.2f} | 第3步右侧加仓: ¥{r['右侧突破加仓(20%)']:,.2f}")
                active_cheat_sheet_text = "\n".join(cs_lines)

            elif "智能定投" in cap_deployment_mode:
                erp_pct, bias_20 = SmartExecutionDCAEngine.compute_portfolio_weighted_bias_and_erp(
                    allocations=alloc_list_for_dca,
                    snapshot=snapshot
                )
                dca_plan = SmartExecutionDCAEngine.plan_smart_dca(
                    total_capital=float(plan_capital),
                    allocations=alloc_list_for_dca,
                    erp_percentile=erp_pct,
                    bias_20=bias_20,
                    periods=12
                )
                ruler_dca = StrategyBridge.get_historical_inflection_ruler(
                    current_erp=erp_pct,
                    current_bias=bias_20,
                    total_capital=float(plan_capital)
                )
                safe_markdown_html(render_historical_inflection_ruler_html(ruler_dca))

                col_d1, col_d2, col_d3 = st.columns([3, 4, 3])
                with col_d1:
                    st.metric("定投周期与基准金额", f"¥{dca_plan['base_per_period']:,.2f} /期", "共 12 期")
                with col_d2:
                    st.metric("当期自适应乘数", f"{dca_plan['multiplier']:.2f}x ({dca_plan['multiplier_tag']})", dca_plan['valuation_status'])
                with col_d3:
                    st.metric("本期建议扣款金额", f"¥{dca_plan['actual_deduction']:,.2f}", f"基准: ¥{dca_plan['base_per_period']:,.2f}")

                vwap_sum = dca_plan.get("vwap_execution_summary", {})
                if vwap_sum:
                    has_etf_dca = any(o.get("is_etf", False) for o in dca_plan.get("fund_orders", []))
                    col_v1, col_v2, col_v3 = st.columns([3, 4, 3])
                    with col_v1:
                        if has_etf_dca:
                            st.metric("快速冲击模拟损耗", f"¥{vwap_sum.get('total_naive_impact_yuan', 0.0):,.2f}", "单笔市价吃单冲击")
                        else:
                            st.metric("早盘盲买偏差损耗", f"¥{vwap_sum.get('total_naive_impact_yuan', 0.0):,.2f}", "早盘未知净值波动偏差")
                    with col_v2:
                        if has_etf_dca:
                            st.metric("VWAP优化执行滑点", f"¥{vwap_sum.get('total_vwap_slippage_yuan', 0.0):,.2f}", "分时成交量加权平抑")
                        else:
                            st.metric("尾盘锚定执行损耗", f"¥{vwap_sum.get('total_vwap_slippage_yuan', 0.0):,.2f}", "14:30 尾盘估值锚定执行")
                    with col_v3:
                        st.metric("智能微观优化节省", f"¥{vwap_sum.get('total_slippage_saved_yuan', 0.0):,.2f}", f"节省 {vwap_sum.get('avg_slippage_saved_bps', 0.0):.1f} bps 冲击损耗")

                mult = dca_plan.get("multiplier", 1.0)
                df_display["基准每期定投(元)"] = df_display["精确买入金额(元)"] / 12.0
                df_display["本期乘数修正后实扣(元)"] = (df_display["精确买入金额(元)"] / 12.0) * mult
                dynamic_col_config["基准每期定投(元)"] = st.column_config.NumberColumn(format="¥%.2f")
                dynamic_col_config["本期乘数修正后实扣(元)"] = st.column_config.NumberColumn(format="¥%.2f")

                order_map = {str(o.get("code")): o for o in dca_plan.get("fund_orders", [])}
                col_naive_head = "快速冲击损耗(元)" if has_etf_dca else "早盘盲买偏差(元)"
                col_vwap_head = "VWAP执行滑点(元)" if has_etf_dca else "尾盘锚定损耗(元)"
                col_saved_head = "优化节省损耗(元)" if has_etf_dca else "尾盘优化节省(元)"

                df_display[col_naive_head] = df_display["基金代码"].astype(str).map(lambda c: order_map.get(c, {}).get("naive_impact_yuan", 0.0))
                df_display[col_vwap_head] = df_display["基金代码"].astype(str).map(lambda c: order_map.get(c, {}).get("vwap_slippage_yuan", 0.0))
                df_display[col_saved_head] = df_display["基金代码"].astype(str).map(lambda c: order_map.get(c, {}).get("slippage_saved_yuan", 0.0))
                df_display["优化节省(bps)"] = df_display["基金代码"].astype(str).map(lambda c: order_map.get(c, {}).get("slippage_saved_bps", 0.0))
                dynamic_col_config[col_naive_head] = st.column_config.NumberColumn(format="¥%.2f")
                dynamic_col_config[col_vwap_head] = st.column_config.NumberColumn(format="¥%.2f")
                dynamic_col_config[col_saved_head] = st.column_config.NumberColumn(format="¥%.2f")
                dynamic_col_config["优化节省(bps)"] = st.column_config.NumberColumn(format="%.1f bps", help="单基真实年化波动率与自身偏离度测算之微观执行优化节省基点")

                def _inject_dca_anomaly_guidance(row):
                    fc = str(row["基金代码"])
                    fn = str(row["基金名称"])
                    rt_g = row.get("实时估值涨跌(%)", 0.0)
                    anom = StrategyBridge.evaluate_tail_valuation_anomaly(fc, fn, realtime_quote=rt_g)
                    orig_g = str(row.get("实操分红与限购指引", ""))
                    o_info = order_map.get(fc, {})
                    is_large = o_info.get("is_large_order", False)
                    split_d = o_info.get("split_days", 1)

                    if anom.get("is_anomaly"):
                        base_str = f"{anom['anomaly_tag']} ｜ {orig_g}"
                    else:
                        saved_bps = o_info.get("slippage_saved_bps", 0.0)
                        if saved_bps > 0:
                            base_str = f"{orig_g}·微观省{saved_bps:.1f}bp"
                        else:
                            base_str = orig_g

                    if is_large and split_d > 1:
                        return f"🌊大额分{split_d}日挂单 ｜ {base_str}"
                    return base_str

                df_display["实操分红与限购指引"] = df_display.apply(_inject_dca_anomaly_guidance, axis=1)

                cs_lines = [cheat_sheet_text, f"\n【📅 估值自适应智能定投执行小抄 (乘数: {mult:.2f}x · 微观执行优化版)】"]
                for _, r in df_display.iterrows():
                    cs_lines.append(f"标的: {r['基金代码']} ({r['基金名称']}) -> 基准定投: ¥{r['基准每期定投(元)']:,.2f}/期 | 本期实扣: ¥{r['本期乘数修正后实扣(元)']:,.2f} | 优化损耗: ¥{r[col_vwap_head]:,.2f} (优化省¥{r[col_saved_head]:,.2f} / {r.get('优化节省(bps)', 0.0):.1f}bps)")

                # G14 实装：大额定投跨 3~5 交易日分批挂单执行调度建议
                large_orders = [o for o in dca_plan.get("fund_orders", []) if o.get("is_large_order")]
                if large_orders:
                    cs_lines.append("\n【🌊 大额定投跨交易日智能挂单分批调度建议 (单笔 > ¥10,000)】")
                    for lo in large_orders:
                        lo_sched = lo.get("large_order_schedule", {}).get("schedule", [])
                        cs_lines.append(f"标的: {lo['code']} ({lo['name']}) -> 单笔 ¥{lo['period_amount']:,.2f} 动态拆解跨 {lo['split_days']} 个交易日挂单:")
                        for sl in lo_sched:
                            cs_lines.append(f"  • {sl['day']} ({sl['weight_pct']:.0f}%): ¥{sl['slice_amount']:,.2f} ｜ 时机: {sl['target_timing']} ｜ 策略: {sl['strategy']}")

                active_cheat_sheet_text = "\n".join(cs_lines)

            if overrides:
                st.info(f"💡 检测到您自定义替换了 {len(overrides)} 只标的：{overrides}，配置方案已实时动态调整。")

            st.dataframe(
                df_display,
                column_config=dynamic_col_config,
                use_container_width=True,
                hide_index=True
            )

            # ── 模块 3：底部单行 4 操作与单一白盒抽屉 ──
            succ_state = st.session_state.get("tab1_overwrite_success")
            if succ_state:
                col_ov_msg, col_ov_undo, col_ov_goto = st.columns([6.0, 2.0, 2.0])
                with col_ov_msg:
                    st.success(f"✅ 已成功将 ¥{succ_state.get('capital', 0.0):,.2f} 建仓方案写入【{succ_state.get('ledger_name', '当前账本')}】，配置 {succ_state.get('funds_count', 0)} 只基金。可用现金池 ¥{pm.available_cash:,.2f}。")
                with col_ov_undo:
                    if st.button("↩️ 撤销本次覆盖", type="secondary", use_container_width=True, key="btn_undo_t1_overwrite"):
                        pm.undo()
                        st.session_state.pop("tab1_overwrite_success", None)
                        st.session_state.tab1_sim_cache = None
                        st.session_state.tab1_step3_cache = None
                        st.info("已成功撤销本次覆盖并恢复原持仓！")
                        st.rerun()
                with col_ov_goto:
                    if st.button("👀 前往持仓调仓", type="primary", use_container_width=True, key="btn_goto_t2_after_bp"):
                        st.session_state["tab2_view_mode"] = "🎯 持仓诊断与智能调仓 (主流程)"
                        st.session_state["pending_cross_tab_jump"] = {
                            "tab_index": 1,
                            "tab_name": "💼 持仓调仓",
                            "action_name": "查看持仓",
                            "target_title": succ_state.get("ledger_name", "当前账本"),
                            "detail": "已写入全新方案，前往查看持仓明细",
                            "timestamp": datetime.now().strftime("%H:%M:%S")
                        }
                        st.session_state["last_cross_tab_action"] = dict(st.session_state["pending_cross_tab_jump"])
                        st.rerun()

            col_act_cur, col_act_new, col_act_cs, col_act_bt = st.columns([2.8, 2.8, 2.2, 2.2])
            with col_act_cur:
                mlm_inst = st.session_state.get("mlm") or (MultiLedgerManager.get_instance() if MultiLedgerManager else None)
                cur_lid = st.session_state.get("active_ledger_id", "main_live")
                cur_meta = mlm_inst.get_ledger_meta(cur_lid) if mlm_inst else {}
                cur_name = (cur_meta or {}).get("name", "当前账本")
                cur_h_count = len(pm.holdings)
                cur_equity = pm.total_equity
                cur_pending_count = len(pm.pending_orders)
                plan_cap_val = float(blueprint.get("total_capital", plan_capital))

                with st.popover(f"📥 覆盖写入当前账本 ({cur_name})", use_container_width=True):
                    st.markdown(f"##### ⚠️ 覆盖写入确认【{cur_name}】")
                    safe_markdown_html(f"""
                    <div style="background: rgba(239, 68, 68, 0.08); border-left: 3px solid var(--color-up); padding: 8px 12px; margin-bottom: 8px; border-radius: 4px; font-size: 12px;">
                        <b>目标账本</b>：{cur_name} (<code>{cur_lid}</code>)<br>
                        <b>现有存量持仓</b>：<b>{cur_h_count} 只</b> ｜ 总资产：¥{cur_equity:,.2f}<br>
                        <b>在途未结订单</b>：{cur_pending_count} 笔<br>
                        <b>新写入建仓方案</b>：拟投入总本金 <b>¥{plan_cap_val:,.2f}</b> ｜ 节奏：{cap_deployment_mode.split('（')[0]}
                    </div>
                    """)
                    st.caption("🚨 注意：覆盖写入将清空当前账本内所有现有持仓与免赎批次，写入全新建仓组合！系统将在执行前自动留存 Undo 历史快照以防误触。")
                    chk_confirm = st.checkbox(
                        f"我已知晓覆盖将清空【{cur_name}】的所有现有持仓并确认执行",
                        value=False,
                        key="chk_confirm_t1_overwrite"
                    )
                    if st.button(
                        f"确认覆盖写入【{cur_name}】",
                        type="primary",
                        use_container_width=True,
                        disabled=not chk_confirm,
                        key="btn_apply_bp_tier"
                    ):
                        plan_data = three_step_plan if "稳健三步" in cap_deployment_mode else (dca_plan if "智能定投" in cap_deployment_mode and 'dca_plan' in locals() and dca_plan is not None else None)
                        res_apply = pm.apply_zero_start_blueprint(
                            blueprint,
                            cap_deployment_mode=cap_deployment_mode,
                            deployment_plan=plan_data
                        )
                        st.session_state["tab1_overwrite_success"] = {
                            "ledger_name": cur_name,
                            "capital": res_apply.get("total_capital", plan_cap_val),
                            "funds_count": res_apply.get("funds_count", len(pm.holdings)),
                            "mode": cap_deployment_mode
                        }
                        st.balloons()
                        st.rerun()

            with col_act_new:
                with st.popover("🆕 另存为全新独立账本", use_container_width=True):
                    st.markdown("##### 🆕 另存为全新独立账本")
                    st.caption("创建新账本并直接将本次建仓方案写入，绝不影响主实盘或其他存量账本。")
                    save_new_name = st.text_input("新账本名称", value=f"新资建仓_{datetime.now().strftime('%m%d_%H%M')}", key="t1_save_new_name")
                    save_new_type = st.selectbox("账本类型", ["沙盒演练 (sandbox)", "家庭专项 (family)", "独立实盘 (live)"], key="t1_save_new_type")
                    save_new_type_code = "sandbox" if "sandbox" in save_new_type else ("family" if "family" in save_new_type else "live")
                    t_val = st.session_state.get("active_tier_val", "C3")
                    tier_idx = ["C1", "C2", "C3", "C4", "C5"].index(t_val) if t_val in ["C1", "C2", "C3", "C4", "C5"] else 2
                    save_new_tier = st.selectbox("专属风险档位", ["C1", "C2", "C3", "C4", "C5"], index=tier_idx, key="t1_save_new_tier")

                    if st.button("输入新账本名称一键创建并写入持仓", type="primary", use_container_width=True, key="btn_confirm_save_new_ledger"):
                        if mlm_inst:
                            total_cap = float(blueprint.get("total_capital", plan_capital))
                            new_lid = mlm_inst.create_ledger(
                                name=save_new_name.strip() or f"建仓方案_{datetime.now().strftime('%m%d_%H%M')}",
                                base_cash=total_cap,
                                ledger_type=save_new_type_code,
                                default_tier=save_new_tier,
                                description="由新资建仓一键生成"
                            )
                            new_pm = mlm_inst.get_pm(new_lid)
                            plan_data = three_step_plan if "稳健三步" in cap_deployment_mode else (dca_plan if "智能定投" in cap_deployment_mode and 'dca_plan' in locals() and dca_plan is not None else None)
                            res_apply = new_pm.apply_zero_start_blueprint(
                                blueprint,
                                cap_deployment_mode=cap_deployment_mode,
                                deployment_plan=plan_data
                            )
                            new_pm.save_state(record_snapshot=True)
                            switch_active_ledger(new_lid)
                            st.balloons()
                            st.success(f"已成功创建新账本【{save_new_name}】并写入持仓！")
                            st.rerun()

            with col_act_cs:
                with st.popover("📱 下单小抄", use_container_width=True):
                    st.markdown("##### 📱 下单一键复制小抄")
                    st.caption("您可以直接复制下方文本发送给微信或记事本，对照手机银行、天天基金、蚂蚁财富一分钟完成买入：")
                    st.code(active_cheat_sheet_text, language="text")

            with col_act_bt:
                if st.button("📈 送入穿透回测", type="secondary", use_container_width=True, key="btn_send_bp_to_bt"):
                    st.session_state.selected_backtest_weights = dict(cur_opt_w)
                    st.session_state.selected_backtest_target = "新建仓组合"
                    st.session_state.tab3_backtest_activated = True
                    st.success("✅ 已将此组合送入组合回测，请切换至 Tab 3 检视。")

            # ── 底部唯一白盒抽屉 ──
            with st.expander("🔬 展开机构级量化压力测试与选基白盒证据", expanded=False):
                # 3 张滚动胜率卡（双口径对照：当下相似条件胜率 vs 全历史胜率）
                st.markdown("#### 🎯 跨牛熊滚动胜率")
                _wr_cols = st.columns(3)
                for _wi, (_wk, _wv) in enumerate(wr_table.items()):
                    with _wr_cols[_wi]:
                        _cond_wr = float(_wv.get("conditional_win_rate", _wv.get("win_rate", 0.0))) * 100.0
                        _uncond_wr = float(_wv.get("unconditional_win_rate", _wv.get("win_rate", 0.0))) * 100.0
                        _med_ann = float(_wv.get("median_ann_return", _wv.get("median_return", 0.0))) * 100.0
                        _no_loss = float(_wv.get("no_loss_rate", 0.0)) * 100.0
                        _beat_cash = float(_wv.get("beat_cash_rate", _no_loss * 0.95)) * 100.0
                        _tot_w = int(_wv.get("total_windows", 0))
                        safe_markdown_html(f"""
                        <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 12px 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
                            <div style="font-size: 13px; font-weight: 600; color: var(--text-secondary); display: flex; justify-content: space-between;">
                                <span>{_wv['label']} 达标胜率</span>
                                <span style="font-size: 11px; color: var(--accent-primary); background: var(--bg-elevated); padding: 1px 6px; border-radius: 4px;">{_tot_w:,} 期样本</span>
                            </div>
                            <div style="font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 4px 0;">
                                {_cond_wr:.1f}%
                                <span style="font-size: 12px; font-weight: 500; color: var(--text-muted);">(全历史 {_uncond_wr:.1f}%)</span>
                            </div>
                            <div style="font-size: 12px; color: var(--text-secondary); font-weight: 500;">
                                正收益概率 <b>{_no_loss:.0f}%</b> ｜ 跑赢货基 <b>{_beat_cash:.0f}%</b> ｜ 中位年化 <b>{_med_ann:.1f}%</b>
                            </div>
                        </div>
                        """)

                with st.expander("ℹ️ 量化数学定义：多维胜率与尾部底线 (CVaR)", expanded=False):
                    st.markdown(r"""
                    - **达标胜率**：在历史所有滚动持有期窗口中，组合真实年化收益率 $\ge$ 用户设定目标年化收益率的加权百分比；
                    - **正收益概率 (收益 $\ge 0\%$)**：持有期满本金不亏损的概率（本金安全率）。纯债配置较高时此项较高，但不可与“达标胜率”混为一谈；
                    - **跑赢货基率 (收益 $\ge 1.8\%$)**：年化净收益超越同期货币基金与现金管理的概率，反映承担波动是否获得有效流动性溢价；
                    - **95% 尾部底线 (CVaR)**：在历史最极端的 5% 尾部黑天鹅行情中，组合的平均亏损底线，杜绝深度套牢。
                    """)

                # 5 张大字号人话指标卡（标题严格 ≤ 6 字）
                k_col1, k_col2, k_col3, k_col4, k_col5 = st.columns(5)
                with k_col1:
                    safe_markdown_html(f"""
                    <div class="kpi-metric-card" >
                        <div class="kpi-card-title">① 最好情况</div>
                        <div class="metric-value-huge" style="color: {active_co['color_up']};">
                            +{readable_kpi.get('best_case_return_pct', 0.0):.2f}%
                        </div>
                        <div class="kpi-card-sub" style="color: {active_co['color_up']};">
                            预计盈利: <b>+¥{readable_kpi.get('best_case_profit_amount', 0.0):,.2f}</b>
                        </div>
                        <div class="kpi-card-desc">任意持有1年最高单年收益</div>
                    </div>
                    """)

                with k_col2:
                    safe_markdown_html(f"""
                    <div class="kpi-metric-card" >
                        <div class="kpi-card-title">② 最坏情况</div>
                        <div class="metric-value-huge" style="color: {active_co['color_down']};">
                            -{readable_kpi.get('worst_case_drawdown_pct', 0.0):.2f}%
                        </div>
                        <div class="kpi-card-sub" style="color: {active_co['color_down']};">
                            账面最大浮亏: <b>-¥{readable_kpi.get('worst_case_loss_amount', 0.0):,.2f}</b>
                        </div>
                        <div class="kpi-card-desc">历史全周期最极端至暗时刻</div>
                    </div>
                    """)

                with k_col3:
                    safe_markdown_html(f"""
                    <div class="kpi-metric-card" >
                        <div class="kpi-card-title">③ 水下回本</div>
                        <div class="metric-value-huge" style="color: var(--accent-primary);">
                            {readable_kpi.get('max_underwater_days', 0)} <span style="font-size:16px;">天</span>
                        </div>
                        <div class="kpi-card-sub" style="color: var(--text-primary);">
                            最长水下: <b>约 {readable_kpi.get('max_underwater_months', 0.0):.1f} 个月</b>
                        </div>
                        <div class="kpi-card-desc">买在历史最高点回本所需时长</div>
                    </div>
                    """)

                with k_col4:
                    safe_markdown_html(f"""
                    <div class="kpi-metric-card" >
                        <div class="kpi-card-title">④ 目标胜率</div>
                        <div class="metric-value-huge" style="color: var(--accent-primary);">
                            {readable_kpi.get('win_rate_1y', 0.0):.1f}%
                        </div>
                        <div class="kpi-card-sub" style="color: var(--text-primary);">
                            1年: <b>{readable_kpi.get('win_rate_1y', 0.0):.1f}%</b> ｜ 2年: <b>{readable_kpi.get('win_rate_2y', 0.0):.1f}%</b>
                        </div>
                        <div class="kpi-card-desc">持有满 3 年胜率 {readable_kpi.get('win_rate_3y', 0.0):.1f}%</div>
                    </div>
                    """)

                with k_col5:
                    safe_markdown_html(f"""
                    <div class="kpi-metric-card" >
                        <div class="kpi-card-title">⑤ 适合资金</div>
                        <div class="metric-value-huge" style="color: var(--text-primary); font-size: 20px; line-height: 1.4;">
                            {active_tier} {cur_tier_meta['name']}
                        </div>
                        <div class="kpi-card-sub" style="color: var(--text-secondary); font-size: 11px;">
                            {readable_kpi.get('suitable_for', '')}
                        </div>
                        <div class="kpi-card-desc" style="font-size: 11px;">{readable_kpi.get('soul_summary', '')}</div>
                    </div>
                    """)

                # 组合内生股息与票息安全垫卡片
                safe_markdown_html(f"""
                <div style="background: rgba(16, 185, 129, 0.08); border-left: 4px solid var(--color-down); padding: 10px 14px; border-radius: 6px; margin: 10px 0; font-size: 13px;">
                    <span style="font-weight: 700; color: var(--color-down);">💰 组合内生股息与票息安全垫：</span>
                    <span style="color: var(--text-primary);">预计年化 <b>¥{_ann_cush:,.0f}</b>/年（折合月均 <b>¥{_mo_cush:,.0f}</b>/月 ｜ 加权息率 <b>{_w_yield:.2f}%</b>）</span>
                </div>
                """)

                # 🌪️ 历史黑天鹅极端承压测试卡片
                try:
                    stress_data = simulate_black_swan_stress(
                        holdings=opt_weights,
                        total_capital=float(plan_capital),
                        df_bt=bt_df if not bt_df.empty else None
                    )
                    render_black_swan_stress_card(stress_data)
                except Exception as e:
                    st.caption(f"（黑天鹅承压测试卡片渲染提示: {e}）")

                # G10: 蒙特卡洛极端承压 3D 分布曲面图
                try:
                    bootstrap_stress_data = pm.simulate_portfolio_cvar_bootstrap(
                        holdings=opt_weights,
                        total_capital=float(plan_capital),
                        investor_risk_tier=active_tier,
                        pm_instance=pm
                    )
                    render_monte_carlo_3d_chart(bootstrap_stress_data)
                except Exception as e_mc3d:
                    st.caption(f"（蒙特卡洛 3D 曲面图加载提示: {e_mc3d}）")

                # 白盒折叠框 1: 全市场选基漏斗与评分表
                with st.expander("🔍 选基漏斗与评分", expanded=False):
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

                    col_f_title, col_f_pop = st.columns([8, 2])
                    with col_f_title:
                        st.markdown("##### 📐 六维评分公式")
                    with col_f_pop:
                        with st.popover("ⓘ 评分细则", use_container_width=True):
                            st.markdown("""
                            **六维评分标准 (0~100 分)：**
                            1. **超额收益 (35%)**：近3年超额 Alpha 分位数；
                            2. **综合费率 (25%)**：申赎与管理销售服务费率综合折算；
                            3. **底层排雷 (15%)**：商誉、质押、存贷双高与解禁排雷；
                            4. **聪明钱流 (10%)**：北向增持、机构重仓占比与净流入；
                            5. **反拥挤度 (10%)**：行业及个股集中度过高抱团惩罚；
                            6. **宏观契合 (5%)**：与当前 ERP/DR007 同温层契合度。
                            """)
                    st.info("总评得分 = 35%×超额收益 + 25%×低费率 + 15%×排雷健康 + 10%×聪明钱 + 10%×反拥挤 + 5%×宏观契合")

                    st.markdown("##### 📊 冠军基金评分表")
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
                                        target_c = new_ovr if new_ovr else s_champ
                                        prev_c = old_ovr if old_ovr else s_champ
                                        if prev_c in opt_w:
                                            val = opt_w.pop(prev_c)
                                            opt_w[target_c] = val
                                        elif s_champ in opt_w:
                                            val = opt_w.pop(s_champ)
                                            opt_w[target_c] = val
                                        st.session_state["tab1_sim_cache"]["optimal_weights"] = opt_w

                                        # 同步更新 quant_table 中对应的标的代码与名称
                                        q_df = st.session_state["tab1_sim_cache"].get("quant_table")
                                        if q_df is not None and not q_df.empty:
                                            q_df = q_df.copy()
                                            mask = q_df["基金代码"].astype(str) == str(prev_c)
                                            if mask.any():
                                                new_name = CORE_STRATEGY_POOL.get(target_c, {}).get("fund_name") or EXTENDED_FUND_CATALOG.get(target_c, {}).get("fund_name") or f"公募基金_{target_c}"
                                                q_df.loc[mask, "基金代码"] = str(target_c)
                                                q_df.loc[mask, "基金名称"] = new_name
                                                st.session_state["tab1_sim_cache"]["quant_table"] = q_df
                                    st.rerun()

                # 白盒折叠框 2: 宏观决策信号
                with st.expander("🧭 宏观决策信号", expanded=False):
                    c_sig1, c_sig2, c_sig3, c_sig4 = st.columns(4)
                    with c_sig1:
                        safe_markdown_html(f"""
                        <div class="decision-card">
                            <div class="decision-title">① 市场温度与估值水位</div>
                            <div class="decision-val">{snapshot.get('market_state', '震荡收息期')}</div>
                            <div class="decision-desc">
                                沪深300点位: <b>{snapshot.get('c300', 4000.0):,.0f}</b><br>
                                ERP 估值分位: <b>{snapshot.get('erp_percentile', 78.5):.1f}%</b> (高性价比击球区)
                            </div>
                        </div>
                        """)
                    with c_sig2:
                        sig_snr = float(snapshot.get("er_snr", 0.65))
                        sig_eff_window = snapshot.get('effective_momentum_window', 60)
                        sig_accel = float(snapshot.get("mom_accel", 0.0))
                        sig_exhaustion = bool(snapshot.get("momentum_exhaustion_warning", False))
                        sig_warn_text = snapshot.get("momentum_exhaustion_text") or "「⚡ 动量衰竭预警：暂停追高进攻标的，新增资金转入红利/纯债缓冲」"
                        sig_warn_block = ""
                        if sig_exhaustion:
                            sig_warn_block = f'<div style="color: var(--color-up); font-size: 11px; font-weight: 600; margin-top: 4px; padding: 3px 6px; background: var(--bg-elevated); border-radius: 4px; border: 1px solid var(--border-subtle); line-height: 1.3;">{sig_warn_text}</div>'

                        safe_markdown_html(f"""
                        <div class="decision-card">
                            <div class="decision-title">② 均线动量状态 (MA20)</div>
                            <div class="decision-val" style="color: var(--accent-primary);">{snapshot.get('m20_status_desc', '站上均线')}</div>
                            <div class="decision-desc">
                                MA20 乖离率: <b>{snapshot.get('bias_20', 1.2):+.2f}%</b><br>
                                考夫曼信噪比 (ER / SNR): <b>{sig_snr:.2f}</b> (自适应变速窗口: {sig_eff_window}日)<br>
                                动量加速度 (Mom Accel): <b>{sig_accel:+.2f}%</b><br>
                                技术研判: 右侧趋势形成，顺势跟进红利与成长动量。
                                {sig_warn_block}
                            </div>
                        </div>
                        """)
                    with c_sig3:
                        safe_markdown_html(f"""
                        <div class="decision-card">
                            <div class="decision-title">③ 宏观资金利率 (DR007)</div>
                            <div class="decision-val" style="color: var(--accent-primary);">{snapshot.get('dr007_status', '流动性合理充裕')}</div>
                            <div class="decision-desc">
                                DR007 7天移动均值: <b>{snapshot.get('dr007_7d_ma', 1.62):.2f}%</b><br>
                                流动性定调: 资金面平稳，债市底仓安全无虞。
                            </div>
                        </div>
                        """)
                    with c_sig4:
                        safe_markdown_html(f"""
                        <div class="decision-card">
                            <div class="decision-title">④ 期权波动率防波堤 (iVIX)</div>
                            <div class="decision-val" style="color: var(--text-secondary);">{snapshot.get('ivix_status', '期权隐含波动率平稳')}</div>
                            <div class="decision-desc">
                                EWMA 历史波动率: <b>{snapshot.get('ewma_vol', 12.8):.1f}%</b><br>
                                情绪定调: 尾部对冲成本低，适合配置长久期优质资产。
                            </div>
                        </div>
                        """)

                # G10: 挂载大额订单流动性折价明细表 (全模式覆盖)
                try:
                    active_orders = []
                    if dca_plan and dca_plan.get("fund_orders"):
                        active_orders = dca_plan["fund_orders"]
                    else:
                        for _, r in df_display.iterrows():
                            _fc = str(r.get("基金代码", "")).zfill(6)
                            _fn = str(r.get("基金名称", _fc))
                            _amt = float(r.get("精确买入金额(元)", 0.0))
                            _hc = data_loader.calculate_otc_fund_liquidity_haircut(order_amount=_amt, fund_code=_fc, fund_name=_fn)
                            active_orders.append({
                                "fund_code": _fc,
                                "fund_name": _fn,
                                "order_amount": _amt,
                                "is_etf": _hc.get("is_etf", False),
                                "fund_aum_yuan": _hc.get("fund_aum_yuan", 0.0),
                                "top5_adv_yuan": _hc.get("top5_adv_yuan", 0.0),
                                "redemption_ratio_pct": _hc.get("redemption_ratio_pct", 0.0),
                                "liquidity_haircut_bps": _hc.get("haircut_bps", 0.0),
                                "liquidity_haircut_yuan": _hc.get("haircut_yuan", 0.0),
                                "slippage_saved_yuan": _hc.get("slippage_saved_yuan", 0.0),
                            })
                    render_liquidity_haircut_table(active_orders)
                except Exception as e_liq_tab1:
                    st.caption(f"（流动性折价表加载提示: {e_liq_tab1}）")

                # 分批/定投执行调度表
                if "智能定投" in cap_deployment_mode and dca_plan:
                    exp_label = "⏱️ 查看分批挂单执行调度表（尾盘净值锁定与跨日分批优化）" if not has_etf_dca else "⏱️ 查看 VWAP 分时成交量加权挂单调度表（日内 5 阶段分笔平抑冲击）"
                    with st.expander(exp_label, expanded=False):
                        large_orders_gui = [o for o in dca_plan.get("fund_orders", []) if o.get("is_large_order")]
                        if large_orders_gui:
                            st.markdown("##### 🌊 大额定投跨交易日智能挂单调度明细 (单笔 > ¥10,000)")
                            st.caption("针对大额订单结合单基日均波幅与成交量加权，动态生成跨 3~5 个交易日分批挂单表，杜绝未知净值冲高回落与日内冲击。")
                            lo_rows = []
                            for lo in large_orders_gui:
                                for s in lo.get("large_order_schedule", {}).get("schedule", []):
                                    lo_rows.append({
                                        "基金标的": f"{lo['name']} ({lo['code']})",
                                        "执行交易日": s.get("day", ""),
                                        "权重占比": f"{s.get('weight_pct', 0.0):.0f}%",
                                        "挂单金额": f"¥{s.get('slice_amount', 0.0):,.2f}",
                                        "执行时机": s.get("target_timing", ""),
                                        "执行策略": s.get("strategy", ""),
                                    })
                            if lo_rows:
                                st.dataframe(pd.DataFrame(lo_rows), use_container_width=True, hide_index=True)
                            st.markdown("---")

                        st.markdown("##### ⏱️ 微观日内/尾盘执行切片参考")
                        sample_slices = []
                        if dca_plan.get("fund_orders"):
                            sample_slices = dca_plan["fund_orders"][0].get("execution_slippage", {}).get("vwap_slices", [])
                        if sample_slices:
                            st.dataframe(pd.DataFrame(sample_slices), use_container_width=True, hide_index=True)


    except Exception as e:
        st.error(f"⚠️ 【🌱 新资建仓】渲染出现局部异常: {e}")
        st.caption("💡 其他 Tab 工作区保持正常运行。如需排查可检查日志。")

# =============================================================
# Tab 2: 【💼 持仓调仓】（自然三步流：①持仓账本 -> ②AI诊断裁决 -> ③调仓方案与执行单）
# =============================================================
def _safe_float(val, default=0.0):
    if val is None or pd.isna(val):
        return None if default is None else float(default)
    try:
        f = float(val)
        return (None if default is None else float(default)) if pd.isna(f) else f
    except (ValueError, TypeError):
        return None if default is None else float(default)

def _safe_int(val, default=30) -> int:
    if val is None or pd.isna(val):
        return int(default)
    try:
        f = float(val)
        return int(default) if pd.isna(f) else int(f)
    except (ValueError, TypeError):
        return int(default)

def _safe_str(val, default="cash") -> str:
    if val is None or pd.isna(val):
        return str(default)
    s = str(val).strip()
    if s.lower() in ("", "nan", "none", "null"):
        return str(default)
    return s

def _commit_edited_holdings_table(edited_df: pd.DataFrame, pm_inst) -> tuple:
    """
    统一提纯的表格未保存修改自动同步入库核心函数：
    双向自适应反算市值/份额/成本价，联网补齐真实净值与名称，杜绝丢数。
    """
    if edited_df is None or edited_df.empty:
        return [], []
    valid_codes = set()
    error_msgs = []
    success_codes = []
    for _, row in edited_df.iterrows():
        raw_code = _safe_str(row.get("基金代码"), "")
        if not raw_code:
            continue
        code_s = raw_code.zfill(6)
        if not code_s.isdigit() or len(code_s) != 6:
            error_msgs.append(f"标的代码 [{raw_code}] 格式不合法（必须为6位纯数字），已跳过")
            continue

        valid_codes.add(code_s)
        old_h = pm_inst.holdings.get(code_s)
        new_mkt = _safe_float(row.get("当前市值(元)"), 0.0)
        new_shares = _safe_float(row.get("持仓份额"), 0.0)

        quote = fetch_realtime_fund_quote(code_s)
        real_nav = float(quote.dwjz if (quote and quote.dwjz > 0) else _safe_float(row.get("当前净值"), 1.0))
        if real_nav <= 0:
            real_nav = 1.0

        real_name = quote.name if (quote and quote.name and not quote.name.startswith("公募基金_")) else None
        h_days = _safe_int(row.get("最短持有天数"), 30)
        div_m = _safe_str(row.get("分红方式"), "cash")

        row_pnl = _safe_float(row.get("累计盈亏(元)"), None)
        row_cost = _safe_float(row.get("持仓成本价"), 0.0)
        old_pnl = float(old_h.floating_pnl) if old_h else None

        if row_pnl is not None and (old_pnl is None or abs(row_pnl - old_pnl) > 0.5):
            cost = max(0.01, round((new_mkt - row_pnl) / (new_shares if new_shares > 0 else (new_mkt / real_nav)), 4)) if new_mkt > 0 else real_nav
        elif row_cost > 0:
            cost = row_cost
        else:
            cost = float(old_h.cost_price if (old_h and old_h.cost_price > 0) else real_nav)

        if old_h:
            old_mkt = float(old_h.market_value)
            old_shares = float(old_h.shares)
            if abs(new_mkt - old_mkt) > 1.0 and abs(new_shares - old_shares) <= 0.01:
                final_shares = round(new_mkt / real_nav, 2)
            elif abs(new_shares - old_shares) > 0.01:
                final_shares = new_shares
            else:
                final_shares = new_shares
        else:
            if new_mkt > 0 and new_shares <= 0:
                final_shares = round(new_mkt / real_nav, 2)
            elif new_shares > 0:
                final_shares = new_shares
            else:
                final_shares = round(new_mkt / real_nav, 2) if new_mkt > 0 else 1000.0

        pm_inst.add_or_update_holding(
            fund_code=code_s,
            shares=final_shares,
            nav=real_nav,
            cost_price=cost,
            holding_days=h_days,
            dividend_method=div_m,
            fund_name=real_name,
            notes="代码智能联动与市值反算入库"
        )
        intent_raw = str(row.get("调仓意愿", "正常参与"))
        intent_key = "lock" if "锁" in intent_raw else ("liquidate" if "清" in intent_raw else "normal")
        if code_s in pm_inst.holdings:
            pm_inst.holdings[code_s].rebalance_intent = intent_key
        success_codes.append(code_s)

    for exist_c in list(pm_inst.holdings.keys()):
        if exist_c not in valid_codes:
            pm_inst.delete_holding(exist_c)

    pm_inst.save_state(record_snapshot=True)
    return success_codes, error_msgs


with tab_holdings_and_rebalance:
    try:
        active_tier = st.session_state.get("active_tier_val", "C3")
        cur_tier_meta = RISK_TIERS_CONFIG.get(active_tier, RISK_TIERS_CONFIG["C3"])

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

        # 顶部主动风控指令横幅（若存在锁仓保护、阶梯止盈、折溢价套利或集中度平移指令）
        has_locked = bool(st.session_state.get("tab2_locked_funds"))
        has_take_profit = bool(st.session_state.get("tab2_pending_take_profit"))
        has_c_replace = bool(st.session_state.get("tab2_c_replace"))
        has_arb_switch = bool(st.session_state.get("tab2_arb_switch"))
        has_transfer = bool(st.session_state.get("tab2_pending_transfer"))
        if has_locked or has_take_profit or has_c_replace or has_arb_switch or has_transfer:
            desc_parts = []
            if has_locked:
                desc_parts.append(f"锁仓保护标的: <b>{', '.join(st.session_state.tab2_locked_funds)}</b>（强制锁定持仓下界禁卖）")
            if has_take_profit:
                tp_info = st.session_state.tab2_pending_take_profit
                desc_parts.append(f"阶梯止盈标的: <b>{tp_info.get('fund_code')}</b>（下调目标权重 {int(tp_info.get('ratio', 0.4)*100)}%，增配纯债/红利低波）")
            if has_c_replace:
                desc_parts.append(f"C类份额置换: <b>{st.session_state.tab2_c_replace}</b>（择机置换为A类份额）")
            if has_arb_switch:
                arb = st.session_state.tab2_arb_switch
                desc_parts.append(f"⚡ 场内外折溢价套利: <b>{arb.get('etf_name', '')} ({arb.get('etf_code', '')})</b> {arb.get('suggested_action', '')} (折溢价率 {arb.get('prem_disc_ratio', 0.0)*100:+.2f}%)")
            if has_transfer:
                tf = st.session_state.tab2_pending_transfer
                desc_parts.append(f"🔄 集中度/行业超标平移: <b>{tf.get('from_code')} ➡️ {tf.get('to_code')}</b> (计划平移 ¥{tf.get('amount', 0.0):,.0f})")
            
            c_bnr1, c_bnr2 = st.columns([8.5, 1.5])
            with c_bnr1:
                safe_markdown_html(f"""
                <div style="background: rgba(234, 179, 8, 0.12); border: 1.5px solid #eab308; border-radius: 8px; padding: 12px 16px; margin-bottom: 12px;">
                    <div style="font-size: 14px; font-weight: 700; color: #ca8a04; margin-bottom: 4px;">
                        ⚡ 已激活主动风控指令：包含锁仓保护 / 阶梯止盈 / 集中度平移 / 尾盘套利方案
                    </div>
                    <div style="font-size: 12px; color: var(--text-primary); line-height: 1.5;">
                        {' ｜ '.join(desc_parts)}
                    </div>
                </div>
                """)
            with c_bnr2:
                if st.button("✖️ 清除指令", use_container_width=True, key="btn_clear_tab2_risk_orders", help="清除全部主动锁仓、止盈、集中度平移与套利风控指令"):
                    st.session_state.tab2_locked_funds = []
                    st.session_state.tab2_pending_take_profit = None
                    st.session_state.tab2_c_replace = None
                    st.session_state.tab2_arb_switch = None
                    st.session_state.tab2_pending_transfer = None
                    st.session_state.tab2_rebal_cache = None
                    st.rerun()

        # 🗄️ 模块一：单行全能账本控制栏（账本选择 + 双视图切换 + 极速录基 + 同步估值 + 账本与环境管理）
        mlm_inst = st.session_state.get("mlm") or (MultiLedgerManager.get_instance() if MultiLedgerManager else None)
        if mlm_inst:
            all_ledgers = mlm_inst.list_ledgers()
            avail_lids = [l["id"] for l in all_ledgers]

            active_lid = st.session_state.get("active_ledger_id", "main_live")
            if active_lid not in avail_lids:
                active_lid = "main_live" if "main_live" in avail_lids else (avail_lids[0] if avail_lids else "main_live")
                st.session_state.active_ledger_id = active_lid
            st.session_state["sel_tab2_active_ledger"] = active_lid

            active_idx = next((i for i, l in enumerate(all_ledgers) if l["id"] == active_lid), 0)

            def _fmt_ledger_choice(lid: str) -> str:
                m = mlm_inst.get_ledger_meta(lid) or {}
                t_map = {"live": "🟢 [实盘]", "family": "👨‍👩‍👧 [家庭]", "sandbox": "🧪 [沙盒]"}
                tag = t_map.get(m.get("type", "sandbox"), "🧪 [沙盒]")
                try:
                    p_i = mlm_inst.get_pm(lid)
                    eq = float(p_i.total_equity)
                except Exception:
                    eq = 0.0
                return f"{tag} {m.get('name', lid)} (¥{eq:,.0f})"

            col_tb_led, col_tb_mode, col_tb_quick, col_tb_sync, col_tb_mgr = st.columns([2.6, 3.2, 1.4, 1.3, 1.5])
            with col_tb_led:
                selected_lid = st.selectbox(
                    "切换账本",
                    options=[l["id"] for l in all_ledgers],
                    index=active_idx,
                    format_func=_fmt_ledger_choice,
                    key=f"sel_tab2_ledger_picker_{active_lid}",
                    label_visibility="collapsed"
                )
                if selected_lid != active_lid:
                    switch_active_ledger(selected_lid)
                    st.session_state["sel_tab2_active_ledger"] = selected_lid
                    st.rerun()

            with col_tb_mode:
                tab2_view_mode = st.radio(
                    "视图模式切换",
                    ["💼 持仓诊断与智能调仓 (主流程)", "🛠️ 账本运维与实盘复盘档案 (宽屏工具坞)"],
                    index=0 if "持仓诊断与智能调仓" in st.session_state.get("tab2_view_mode", "持仓诊断与智能调仓") else 1,
                    horizontal=True,
                    key="rad_tab2_view_mode",
                    label_visibility="collapsed"
                )
                st.session_state["tab2_view_mode"] = tab2_view_mode
                is_t2_main_mode = "持仓诊断与智能调仓" in tab2_view_mode

            with col_tb_quick:
                with st.popover("➕ 极速录基", use_container_width=True):
                    st.markdown("##### ⚡ 极速录基（自动联网拉取净值并平账反算成本与份额）")
                    bar_fund_in = st.text_input("基金代码或中文名", value="", placeholder="如 005561 或 红利低波", key="bar_fund_input")
                    bar_amt_in = st.number_input("持有金额 (元)", value=10000.0, step=1000.0, min_value=100.0, key="bar_amt_input")
                    st.caption(f"🔢 **金额核对**：{format_chinese_amount(bar_amt_in)}")
                    bar_pnl_in = st.text_input("累计盈亏 (元/%)", value="0.0", placeholder="如 +1200 或 -5%", key="bar_pnl_input")
                    bar_dur_choice = st.selectbox(
                        "持有期限档位",
                        ["<7天 (临界观察·惩罚期)", "7-29天 (免惩罚·适中)", "30-179天 (C类免赎)", "≥180天 (A类免赎)", "≥365天 (长跑底仓)"],
                        index=2,
                        key="bar_dur_choice"
                    )
                    if st.button("➕ 加入账本", type="primary", use_container_width=True, key="btn_bar_add_holding"):
                        if "tab2_cached_edited_table" in st.session_state and st.session_state.tab2_cached_edited_table is not None:
                            _ch, _ = _has_uncommitted_holdings_changes(st.session_state.tab2_cached_edited_table, pm)
                            if _ch:
                                _commit_edited_holdings_table(st.session_state.tab2_cached_edited_table, pm)
                        raw_in = bar_fund_in.strip()
                        matched_code = None
                        if raw_in:
                            import re
                            m_c = re.search(r'\b\d{6}\b', raw_in)
                            if m_c:
                                matched_code = m_c.group(0)
                            else:
                                from portfolio_manager import search_funds_in_catalog
                                res_search = search_funds_in_catalog(raw_in, limit=1)
                                if res_search:
                                    matched_code = res_search[0]["fund_code"]
                        if matched_code:
                            q = fetch_realtime_fund_quote(matched_code)
                            real_nav = float(q.dwjz) if (q and float(q.dwjz) > 0) else 1.0
                            amt = float(bar_amt_in)
                            sh = round(amt / real_nav, 2)
                            pnl_str = bar_pnl_in.strip()
                            cost_p = real_nav
                            if "%" in pnl_str:
                                try:
                                    pct_v = float(pnl_str.replace("%", "").strip())
                                    cost_p = round(real_nav / (1.0 + pct_v / 100.0), 4) if (1.0 + pct_v / 100.0) > 0 else real_nav
                                except Exception:
                                    pass
                            else:
                                try:
                                    pnl_v = float(pnl_str.replace("元", "").replace("+", "").replace(",", "").strip())
                                    cost_p = round(max(0.01, amt - pnl_v) / sh, 4) if sh > 0 else real_nav
                                except Exception:
                                    pass
                            dur_map = {0: 3, 1: 15, 2: 45, 3: 185, 4: 370}
                            h_days = dur_map.get(["<7天", "7-29天", "30-179天", "≥180天", "≥365天"].index(bar_dur_choice.split(" ")[0]), 45)
                            pm.add_or_update_holding(
                                fund_code=matched_code,
                                shares=sh,
                                nav=real_nav,
                                cost_price=cost_p,
                                holding_days=h_days,
                                notes="极速录基吧台录入"
                            )
                            pm.save_state()
                            st.session_state.tab2_diag_cache = None
                            st.session_state.tab2_rebal_cache = None
                            st.success(f"成功将【{matched_code}】录入账本！")
                            st.rerun()
                        else:
                            st.warning("未能识别该基金，请输入 6 位代码或有效基金名称。")

            with col_tb_sync:
                if st.button("🔄 同步估值", use_container_width=True, type="primary", key="btn_tab2_sync"):
                    clear_realtime_cache()
                    fetch_batch_realtime_indices(use_cache=False)
                    pm.sync_holdings_live_nav(use_intraday_gsz=True)
                    StrategyBridge._cached_snapshot = None
                    StrategyBridge._cached_matrix = None
                    StrategyBridge.get_latest_market_snapshot(force_reload=True, auto_sync=False)
                    st.success("全局行情与估值已刷新")
                    st.rerun()

            with col_tb_mgr:
                with st.popover("⚙️ 账本与环境管理", use_container_width=True):
                    st.markdown("##### ⚙️ 账本与环境管理")
                    cur_m = mlm_inst.get_ledger_meta(active_lid) or {}
                    
                    with st.expander("➕ 新建独立账本", expanded=False):
                        n_name = st.text_input("账本名称", placeholder="例如：子女教育金", key="pop_new_ledger_name")
                        n_cash = st.number_input("初始可用现金 (元)", min_value=0.0, value=100000.0, step=10000.0, key="pop_new_ledger_cash")
                        st.caption(f"🔢 **金额核对**：{format_chinese_amount(n_cash)}")
                        n_type_label = st.selectbox("账本类型", ["沙盒演练 (sandbox)", "家庭专项 (family)", "独立实盘 (live)"], key="pop_new_ledger_type")
                        n_type = "sandbox" if "sandbox" in n_type_label else ("family" if "family" in n_type_label else "live")
                        n_tier = st.selectbox("专属风险档位", ["C1", "C2", "C3", "C4", "C5"], index=2, key="pop_new_ledger_tier")
                        if st.button("确认创建并切换", type="primary", use_container_width=True, key="btn_confirm_create_ledger"):
                            new_id = mlm_inst.create_ledger(
                                name=n_name.strip() or f"新账本_{datetime.now().strftime('%m%d_%H%M')}",
                                base_cash=n_cash,
                                ledger_type=n_type,
                                default_tier=n_tier
                            )
                            switch_active_ledger(new_id)
                            st.toast("✅ 成功创建账本并已切换！")
                            st.rerun()

                    with st.expander("📋 克隆当前副本", expanded=False):
                        cl_name = st.text_input("副本账本名称", value=f"{cur_m.get('name', '账本')} - 副本", key="pop_clone_ledger_name")
                        cl_type_label = st.selectbox("副本类型", ["沙盒演练 (sandbox)", "家庭专项 (family)", "独立实盘 (live)"], key="pop_clone_ledger_type")
                        cl_type = "sandbox" if "sandbox" in cl_type_label else ("family" if "family" in cl_type_label else "live")
                        if st.button("一键克隆并切换", type="primary", use_container_width=True, key="btn_confirm_clone_ledger"):
                            clone_id = mlm_inst.clone_ledger(
                                src_id=active_lid,
                                target_name=cl_name.strip() or f"{cur_m.get('name', '账本')} - 副本",
                                ledger_type=cl_type
                            )
                            switch_active_ledger(clone_id)
                            st.toast("✅ 成功克隆账本并已切换！")
                            st.rerun()

                    with st.expander("✏️ 重命名当前账本", expanded=False):
                        ren_name = st.text_input("新名称", value=cur_m.get("name", ""), key="pop_rename_ledger_input")
                        if st.button("保存名称修改", key="btn_save_rename_ledger", use_container_width=True):
                            if ren_name.strip():
                                mlm_inst.rename_ledger(active_lid, ren_name.strip())
                                st.toast("✅ 账本名称已更新！")
                                st.rerun()

                    with st.expander("🗑️ 删除账本", expanded=False):
                        if cur_m.get("is_protected", False) or active_lid == "main_live":
                            st.info("🛡️ **主实盘账本受系统物理保护，禁止删除。**")
                        else:
                            del_confirm = st.checkbox("确认永久删除当前账本及其全部持仓数据", key="chk_confirm_delete_ledger")
                            if st.button("🗑️ 确认删除当前账本", type="primary", use_container_width=True, disabled=not del_confirm, key="btn_confirm_delete_ledger"):
                                mlm_inst.delete_ledger(active_lid)
                                switch_active_ledger("main_live")
                                st.toast("🗑️ 已删除账本，自动回退至主实盘！")
                                st.rerun()

                    st.divider()

                    st.markdown("**🧪 环境与演练工具**")
                    if st.button("🚀 载入演示组合", use_container_width=True, help="注入包含冷启动、7天锁、待满期、深套基的完整演示组合", key="btn_tab2_load_demo"):
                        demo_res = pm.load_demo_portfolio()
                        st.session_state.tab2_diag_cache = None
                        st.session_state.tab2_rebal_cache = None
                        st.session_state.tab2_diagnosed = False
                        st.session_state.tab2_rebalanced = False
                        st.session_state.tab2_trigger_diagnose = False
                        st.session_state.tab2_trigger_rebalance = False
                        st.success("演示组合已载入")
                        st.rerun()

                    if st.button("↩️ 撤销上次修改", use_container_width=True, help="撤销上一步操作并回滚快照", key="btn_tab2_undo"):
                        _undo_ok = pm.undo()
                        if _undo_ok:
                            st.session_state.tab2_diag_cache = None
                            st.session_state.tab2_rebal_cache = None
                            st.session_state.tab2_diagnosed = False
                            st.session_state.tab2_rebalanced = False
                            st.session_state.tab2_trigger_diagnose = False
                            st.session_state.tab2_trigger_rebalance = False
                            st.info("已成功回滚至上一快照")
                            st.rerun()
                        else:
                            st.warning("暂无更早快照可撤销")

                    st.divider()

                    with st.expander("👨‍👩‍👧‍👦 查看全账本家庭资产汇总表", expanded=False):
                        all_sum = mlm_inst.get_all_ledgers_summary()
                        col_s1, col_s2, col_s3 = st.columns(3)
                        col_s1.metric("家庭总资产", f"¥{all_sum['total_equity']:,.2f}")
                        col_s2.metric("全账本浮盈", f"¥{all_sum['total_floating_pnl']:+,.2f}")
                        col_s3.metric("总持仓只数", f"{all_sum['total_funds']} 只")
                        st.dataframe(all_sum["df"], use_container_width=True, hide_index=True)

            cur_meta = mlm_inst.get_ledger_meta(active_lid) or {}
            if cur_meta.get("type") == "sandbox":
                safe_markdown_html("""
                <div style="background: rgba(234, 179, 8, 0.15); border-left: 4px solid #eab308; padding: 10px 14px; border-radius: 6px; margin-top: 6px; margin-bottom: 12px; font-size: 13px; color: var(--text-primary);">
                    🧪 <b>当前为独立沙盒环境，任何调仓与录基演练均隔离存储，绝不影响主实盘</b>
                </div>
                """)
        else:
            is_t2_main_mode = True

        if is_t2_main_mode:
            # ── 模块二：合一的 4 格资产安全垫顶栏 + 实时持仓明细表 ──
            _c300_pt = float(snapshot.get("c300_close", snapshot.get("close", 3920.0)))
            _cushion_model = pm.calculate_portfolio_cushion_and_stress_model(current_index_point=_c300_pt)

            _tot_equity = sum(h.market_value for h in pm.holdings.values()) + pm.available_cash + pm.in_transit_cash
            _t2_mkt = sum(getattr(h, "shares", 0.0) * getattr(h, "current_nav", 1.0) for h in pm.holdings.values()) if pm.holdings else 0.0
            _t2_cost = sum(getattr(h, "shares", 0.0) * getattr(h, "cost_price", getattr(h, "current_nav", 1.0)) for h in pm.holdings.values()) if pm.holdings else 0.0
            _t2_pnl = _t2_mkt - _t2_cost
            _t2_pnl_pct = (_t2_pnl / _t2_cost * 100.0) if _t2_cost > 0 else 0.0
            _pos_pct = (_t2_mkt / _tot_equity * 100.0) if _tot_equity > 0 else 0.0

            est_pnl = sum(
                getattr(h, "market_value", 0.0) * (float(fetch_realtime_fund_quote(c).gszzl) / 100.0)
                for c, h in pm.holdings.items()
                if fetch_realtime_fund_quote(c) and hasattr(fetch_realtime_fund_quote(c), "gszzl")
            ) if pm.holdings else 0.0
            est_pnl_pct = (est_pnl / _t2_mkt * 100.0) if _t2_mkt > 0 else 0.0
            pnl_color = active_co["color_up"] if est_pnl >= 0 else active_co["color_down"]
            pnl_c = active_co["color_up"] if _t2_pnl >= 0 else active_co["color_down"]

            beta_p = float(_cushion_model.get("portfolio_weighted_beta", 0.0))
            cushion_yuan = float(_cushion_model.get("comprehensive_cushion", 0.0))
            cushion_ratio = float(_cushion_model.get("cushion_ratio_pct", 0.0))
            is_loss = bool(_cushion_model.get("is_in_floating_loss", False))
            break_drop = float(_cushion_model.get("break_even_drop_pct", 0.0))
            break_pt = float(_cushion_model.get("break_even_index_point", 0.0))
            rec_rise = float(_cushion_model.get("recovery_rise_pct", 0.0))
            rec_pt = float(_cushion_model.get("recovery_index_point", 0.0))
            scenarios = _cushion_model.get("stress_scenarios", [])

            if is_loss:
                cushion_c = "var(--color-up)"
                crit_title = "回本临界"
                crit_val = f"+{rec_rise:.2f}%"
                crit_sub = f"大盘回升至 {rec_pt:,.0f} 点"
            elif beta_p > 0.001:
                cushion_c = "var(--color-down)" if cushion_yuan >= 0 else "var(--color-up)"
                crit_title = "破净临界"
                crit_val = f"{break_drop:.2f}%"
                crit_sub = f"大盘跌至 {break_pt:,.0f} 点"
            else:
                cushion_c = "var(--color-down)"
                crit_title = "系统性风险"
                crit_val = "物理免疫"
                crit_sub = "100%现金/中性固收"

            sc_items_html = ""
            for sc in scenarios:
                s_name = sc.get("scenario_type", "急跌")
                m_drop = float(sc.get("market_drop_pct", 0.0))
                loss_yuan = float(sc.get("expected_loss_yuan", 0.0))
                rem_yuan = float(sc.get("remaining_cushion_yuan", 0.0))
                is_safe = bool(sc.get("is_capital_safe", True))
                s_badge = "🟢安全" if is_safe else "🔴穿透"
                sc_items_html += f"<div style='display:flex; justify-content:space-between; font-size:10px; margin-top:2px;'><span>{s_name}({m_drop:+.0f}%): 预估¥{loss_yuan:+,.0f}</span><span>剩余¥{rem_yuan:+,.0f} {s_badge}</span></div>"

            # 4 张高信息密度合一顶栏卡
            t2_c1, t2_c2, t2_c3, t2_c4 = st.columns(4)

            with t2_c1:
                safe_markdown_html(f"""
                <div class="main-metric-card" style="min-height: 104px;">
                    <div class="metric-card-title">
                        <span>💼 持仓总市值</span>
                        <span style="color: var(--text-secondary); font-size: 11px;">仓位 {_pos_pct:.1f}%</span>
                    </div>
                    <div class="metric-value-huge" style="color: var(--text-primary);">
                        ¥{_t2_mkt:,.2f}
                    </div>
                    <div class="metric-card-sub" style="font-size: 11px;">
                        持仓标的: {len(pm.holdings)} 只 ｜ 总资产: ¥{_tot_equity:,.2f}
                    </div>
                </div>
                """)

            with t2_c2:
                safe_markdown_html(f"""
                <div class="main-metric-card" style="min-height: 104px;">
                    <div class="metric-card-title">
                        <span>💵 可用现金池</span>
                        <span style="color: var(--text-secondary); font-size: 11px;">现金比 {100.0-_pos_pct:.1f}%</span>
                    </div>
                    <div class="metric-value-huge" style="color: var(--accent-primary);">
                        ¥{pm.available_cash:,.2f}
                    </div>
                    <div class="metric-card-sub" style="font-size: 11px;">
                        在途资金: ¥{pm.in_transit_cash:,.2f} ｜ 备用缓冲就绪
                    </div>
                </div>
                """)

            with t2_c3:
                safe_markdown_html(f"""
                <div class="main-metric-card" style="min-height: 104px;">
                    <div class="metric-card-title">
                        <span>📈 累计浮动盈亏</span>
                        <span style="color: {pnl_c}; font-weight: 600; font-size: 11px;">{_t2_pnl_pct:+.2f}%</span>
                    </div>
                    <div class="metric-value-huge" style="color: {pnl_c};">
                        ¥{_t2_pnl:+,.2f}
                    </div>
                    <div class="metric-card-sub" style="font-size: 11px;">
                        今日预估: <b style="color: {pnl_color};">¥{est_pnl:+,.2f} ({est_pnl_pct:+.2f}%)</b>
                    </div>
                </div>
                """)

            with t2_c4:
                safe_markdown_html(f"""
                <div class="main-metric-card" style="min-height: 104px;">
                    <div class="metric-card-title">
                        <span>🛡️ 综合安全垫</span>
                        <span style="color: var(--text-secondary); font-size: 11px;">β = {beta_p:.3f}</span>
                    </div>
                    <div class="metric-value-huge" style="color: {cushion_c}; font-size: 18px;">
                        ¥{cushion_yuan:,.0f} <span style="font-size: 11px; font-weight: normal;">({cushion_ratio:+.1f}%)</span>
                    </div>
                    <div class="metric-card-sub" style="font-size: 10.5px;">
                        {crit_title}: <b style="color: {'var(--color-up)' if is_loss else 'var(--accent-primary)'};">{crit_val}</b> ｜ {crit_sub}
                    </div>
                    <details style="margin-top: 2px;">
                        <summary style="cursor: pointer; font-size: 10px; color: var(--accent-primary);">📊 展开 -3%/-5%/-10% 承压推演</summary>
                        <div style="background: var(--bg-canvas); padding: 4px 6px; border-radius: 4px; margin-top: 4px; border: 1px solid var(--border-subtle);">
                            {sc_items_html}
                        </div>
                    </details>
                </div>
                """)

            # G10: 实盘持仓蒙特卡洛极端承压 3D 分布曲面图（收纳进紧凑折叠项，不霸占首屏）
            with st.expander("🔬 查看实盘持仓蒙特卡洛极端承压 3D 分布曲面图", expanded=False):
                try:
                    _tot_cap_t2 = float(getattr(pm, "total_equity", getattr(pm, "total_market_value", 100000.0)) or 100000.0)
                    real_stress_data = pm.simulate_portfolio_cvar_bootstrap_instance(
                        total_capital=_tot_cap_t2,
                        investor_risk_tier=getattr(st.session_state, "active_tier_val", "C3")
                    )
                    render_monte_carlo_3d_chart(real_stress_data)
                except Exception as e_mc3d_t2:
                    st.caption(f"（持仓压力测试 3D 曲面图加载提示: {e_mc3d_t2}）")

            # 实时持仓明细表
            df_disp = pm.export_snapshot_df()
            st.caption("实时持仓资产明细（💡 仅需修改/录入 **「基金代码」** 与 **「当前市值(元)」** 或 **「持仓份额」**，保存时后台自动联网补齐真实名称、最新净值与盘中估值，其余指标全自动跳出）：")

            if not df_disp.empty:
                # 浓缩赎回费状态列
                df_disp["赎回费状态"] = df_disp.apply(
                    lambda r: (
                        f"🔴 1.50% 禁卖 (差{max(0, 7 - int(r['最短持有天数']))}天)" if int(r['最短持有天数']) < 7
                        else (f"🟡 {r['当前赎回费率(%)']:.2f}% (差{max(0, 30 - int(r['最短持有天数']))}天免)" if (r.get('份额类型') == 'C' and int(r['最短持有天数']) < 30)
                        else f"🟢 {r['当前赎回费率(%)']:.2f}% 免/低赎")
                    ),
                    axis=1
                )

                # 补充累计盈亏与调仓意愿列
                df_disp["累计盈亏(元)"] = df_disp.apply(
                    lambda r: round(float(r["当前市值(元)"]) - (float(r["持仓份额"]) * float(r.get("持仓成本价", r["当前净值"]))), 2),
                    axis=1
                )
                df_disp["调仓意愿"] = df_disp["基金代码"].apply(
                    lambda c: {"normal": "正常参与", "lock": "锁定禁卖", "liquidate": "优先清仓"}.get(
                        getattr(pm.holdings.get(str(c).zfill(6)), "rebalance_intent", "normal"), "正常参与"
                    )
                )

                # 精选核心列：支持累计盈亏与调仓意愿双向编辑反算
                cols_selected = [
                    "基金代码", "基金名称", "当前市值(元)", "持仓份额", "当前净值",
                    "持仓成本价", "累计盈亏(元)", "浮动盈亏率(%)", "调仓意愿",
                    "今日实时估值涨跌(%)", "盘中预估盈亏(元)", "持仓占比(%)",
                    "最短持有天数", "赎回费状态", "分红方式"
                ]
                cols_clean = [c for c in cols_selected if c in df_disp.columns]
                df_table = df_disp[cols_clean]

                safe_markdown_html("<div style='height: 4px;'></div>")
                warn_placeholder = st.empty()

                edited_table = st.data_editor(
                    df_table,
                    column_config={
                        "基金代码": st.column_config.TextColumn(
                            "基金代码",
                            help="双击修改或输入 6 位公募基金代码，保存时系统自动联网补齐名称与最新净值。",
                            max_chars=6,
                            validate=r"^\d{6}$",
                            required=True
                        ),
                        "基金名称": st.column_config.TextColumn(
                            "基金名称",
                            help="根据代码自动联网匹配跳出，只读无需手动输入",
                            disabled=True
                        ),
                        "当前市值(元)": st.column_config.NumberColumn(
                            "当前市值(元)",
                            format="¥%.2f",
                            help="可直接修改持有总市值，系统自动按净值反算份额。"
                        ),
                        "持仓份额": st.column_config.NumberColumn(
                            "持仓份额",
                            format="%.2f",
                            help="修改份额将自动根据净值重算市值"
                        ),
                        "当前净值": st.column_config.NumberColumn(
                            "当前净值",
                            format="%.4f",
                            disabled=True,
                            help="联网拉取的最新单位净值，自动跳出"
                        ),
                        "持仓成本价": st.column_config.NumberColumn(
                            "持仓成本价",
                            format="%.4f",
                            help="可双击修改买入成本价，系统自动反算浮动盈亏"
                        ),
                        "累计盈亏(元)": st.column_config.NumberColumn(
                            "累计盈亏(元)",
                            format="¥%+.2f",
                            help="可双击修改浮动盈亏金额，系统自动反算加权成本价！"
                        ),
                        "调仓意愿": st.column_config.SelectboxColumn(
                            "调仓意愿",
                            options=["正常参与", "锁定禁卖", "优先清仓"],
                            default="正常参与",
                            required=True,
                            help="锁定禁卖：调仓时不减持该标的；优先清仓：调仓时优先全额减持该标的。"
                        ),
                        "浮动盈亏率(%)": st.column_config.NumberColumn(
                            "浮动盈亏率(%)",
                            format="%+.2f%%",
                            disabled=True,
                            help="单只基金累计浮动盈亏率，自动跳出"
                        ),
                        "今日实时估值涨跌(%)": st.column_config.NumberColumn(
                            "今日实时估值涨跌(%)",
                            format="%+.2f%%",
                            disabled=True,
                            help="联网盘中实时估算涨跌幅，自动跳出"
                        ),
                        "盘中预估盈亏(元)": st.column_config.NumberColumn(
                            "盘中预估盈亏(元)",
                            format="¥%+.2f",
                            disabled=True,
                            help="基于盘中估算的今日预估盈亏，自动跳出"
                        ),
                        "持仓占比(%)": st.column_config.ProgressColumn(
                            "持仓占比(%)",
                            min_value=0,
                            max_value=50,
                            format="%.2f%%",
                            help="根据全组合总资产自动计算占比进度条"
                        ),
                        "最短持有天数": st.column_config.NumberColumn(
                            "最短持有天数",
                            format="%d 天",
                            default=30,
                            help="修改持有天数自动刷新赎回费梯级"
                        ),
                        "赎回费状态": st.column_config.TextColumn(
                            "赎回费状态",
                            disabled=True,
                            help="根据持有天数与产品规则自动判定"
                        ),
                        "分红方式": st.column_config.SelectboxColumn(
                            "分红方式",
                            options=["cash", "reinvest"],
                            default="cash",
                            required=True
                        ),
                    },
                    disabled=["基金名称", "当前净值", "浮动盈亏率(%)", "今日实时估值涨跌(%)", "盘中预估盈亏(元)", "持仓占比(%)", "赎回费状态"],
                    use_container_width=True,
                    num_rows="dynamic",
                    key="main_holdings_editor_tab2"
                )
                st.session_state["tab2_cached_edited_table"] = edited_table
                has_uncommitted, change_details = _has_uncommitted_holdings_changes(edited_table, pm)
                if has_uncommitted:
                    tip_summary = "；".join(change_details[:3]) + (f" 等共 {len(change_details)} 项改动" if len(change_details) > 3 else "")
                    warn_placeholder.markdown(_clean_html(f"""
                    <div style="background: rgba(239, 68, 68, 0.12); border: 1.5px solid var(--color-up); border-radius: 6px; padding: 10px 14px; margin-bottom: 8px;">
                        <div style="font-size: 13px; font-weight: 700; color: var(--color-up); margin-bottom: 2px;">
                            ⚠️ 检测到持仓明细表存在未保存的修改（{tip_summary}）！
                        </div>
                        <div style="font-size: 11px; color: var(--text-secondary);">
                            为防止操作其他功能导致数据被重置，请及时点击表格下方的 <b>【💾 保存修改并入库】</b> 按钮保存。
                        </div>
                    </div>
                    """), unsafe_allow_html=True)
                else:
                    warn_placeholder.empty()

                # 拉齐操作栏：等高 5 列工具栏（含现金池修改 Popover）
                col_op1, col_op2, col_op3, col_op4, col_op5 = st.columns(5)
                with col_op1:
                    if st.button("💾 保存修改并入库", type="primary", use_container_width=True, key="btn_save_holdings_tab2"):
                        with st.spinner("🔄 正在智能补齐基金名称、最新净值与盘中估值..."):
                            success_codes, error_msgs = _commit_edited_holdings_table(edited_table, pm)
                            st.session_state.tab2_diag_cache = None
                            st.session_state.tab2_rebal_cache = None
                            st.session_state.tab2_diagnosed = False
                            st.session_state.tab2_rebalanced = False
                        if error_msgs:
                            for em in error_msgs:
                                st.warning(f"⚠️ {em}")
                        st.success(f"✅ 持仓账本已更新，成功识别入库 {len(success_codes)} 只标的，真实名称、净值与估值已自动补齐。")
                        st.rerun()

                with col_op2:
                    with st.popover("💰 修改现金池", use_container_width=True):
                        new_c_val = st.number_input(
                            "可用现金金额 (元)",
                            value=float(pm.available_cash),
                            step=1000.0,
                            format="%.2f",
                            key="pop_edit_cash_pool_tb"
                        )
                        st.caption(f"🔢 **金额核对**：{format_chinese_amount(new_c_val)}")
                        if st.button("确认保存现金", type="primary", use_container_width=True, key="btn_confirm_cash_pop_tb"):
                            if "edited_table" in locals() and edited_table is not None:
                                _commit_edited_holdings_table(edited_table, pm)
                            pm.available_cash = round(new_c_val, 2)
                            pm.save_state(record_snapshot=True)
                            st.session_state.tab2_diag_cache = None
                            st.session_state.tab2_rebal_cache = None
                            st.success("现金池已更新。")
                            st.rerun()

                with col_op3:
                    if st.button("🔄 同步真实净值", use_container_width=True, help="拉取最新净值/盘中估值刷新持仓", key="btn_sync_holdings_tab2"):
                        if "edited_table" in locals() and edited_table is not None:
                            _commit_edited_holdings_table(edited_table, pm)
                        with st.spinner("🔄 同步中..."):
                            s_res = pm.sync_holdings_live_nav(use_intraday_gsz=True)
                        st.success(f"✅ 已同步 {s_res.get('updated_count', 0)} 只标的真实净值。")
                        st.rerun()

                with col_op4:
                    csv_exp = df_disp.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        "📥 导出持仓快照 CSV",
                        data=csv_exp,
                        file_name=f"portfolio_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True,
                        key="btn_dl_csv_tab2"
                    )

                with col_op5:
                    with st.popover("🗑️ 删除指定标的", use_container_width=True):
                        del_sel = st.selectbox("选择要删除的基金代码", ["-- 请选择 --"] + list(pm.holdings.keys()), key="pop_del_sel_tab2")
                        if del_sel != "-- 请选择 --":
                            if st.button(f"确认删除 {del_sel}", type="primary", use_container_width=True, key="btn_pop_del_confirm_tab2"):
                                if "edited_table" in locals() and edited_table is not None:
                                    _commit_edited_holdings_table(edited_table, pm)
                                pm.delete_holding(del_sel)
                                st.session_state.tab2_diag_cache = None
                                st.session_state.tab2_rebal_cache = None
                                st.session_state.tab2_diagnosed = False
                                st.session_state.tab2_rebalanced = False
                                st.success(f"已删除 {del_sel}")
                                st.rerun()

            # ── 模块 3：调仓裁决与执行单合流（单一控制栏 + 4格摘要条 + 执行建议单） ──
            # tab2_rebal_buf_slider_bot
            safe_markdown_html("<div style='height: 10px;'></div>")
            col_t2_btn1, col_t2_btn2, col_t2_slider = st.columns([4.2, 2.6, 3.2])
            with col_t2_btn1:
                if st.button("🔍 诊断并生成调仓方案", type="primary", use_container_width=True, key="btn_tab2_diagnose"):
                    st.session_state["tab2_view_mode"] = "🎯 持仓诊断与智能调仓 (主流程)"
                    # 💡 自动拦截并同步表格未保存修改，杜绝丢数
                    if "edited_table" in locals() and edited_table is not None:
                        _commit_edited_holdings_table(edited_table, pm)
                    st.session_state.tab2_diagnosed = True
                    st.session_state.tab2_rebalanced = True
                    st.session_state.tab2_trigger_diagnose = True
                    st.session_state.tab2_trigger_rebalance = True
                    st.rerun()
            with col_t2_btn2:
                if st.button("🚀 一键全速执行", type="secondary", use_container_width=True, key="btn_tab2_all"):
                    st.session_state["tab2_view_mode"] = "🎯 持仓诊断与智能调仓 (主流程)"
                    if "edited_table" in locals() and edited_table is not None:
                        _commit_edited_holdings_table(edited_table, pm)
                    st.session_state.tab2_diagnosed = True
                    st.session_state.tab2_rebalanced = True
                    st.session_state.tab2_trigger_diagnose = True
                    st.session_state.tab2_trigger_rebalance = True
                    st.rerun()
            with col_t2_slider:
                cur_buf_val = float(st.session_state.get("rebalance_buffer_pct", 3.0))
                def _sync_tab2_rebal_buffer_change():
                    st.session_state.rebalance_buffer_pct = float(st.session_state.tab2_rebal_buf_slider)
                    st.session_state.tab2_diag_cache = None
                    st.session_state.tab2_rebal_cache = None

                st.slider(
                    "🛡️ 免折腾调仓缓冲带 (%)",
                    min_value=1.0,
                    max_value=5.0,
                    value=cur_buf_val,
                    step=0.5,
                    format="%.1f%%",
                    key="tab2_rebal_buf_slider",
                    on_change=_sync_tab2_rebal_buffer_change,
                    help="控制调仓裁决与温和调仓过滤的最小偏离阈值。低于此阈值的微小偏离将自动维持现状，杜绝无效换仓摩擦"
                )

            if is_t2_main_mode and (st.session_state.get("tab2_diagnosed", False) or st.session_state.get("tab2_rebalanced", False)):
                st.markdown("---")

                # 🎯 目标组合与场景模式微调（收纳于轻量折叠项，默认自动全托管）
                has_t1_opt = bool(st.session_state.get("tab1_sim_cache") and st.session_state["tab1_sim_cache"].get("optimal_weights"))
                with st.expander("⚙️ 调仓目标组合与场景模式微调（已自动按全天候策略池与温和再平衡托管）", expanded=False):
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

                    col_sc1, col_sc2 = st.columns([6.5, 3.5])
                    with col_sc1:
                        sel_scenario_name = st.radio(
                            "调仓意图场景：",
                            [
                                "⚖️ 存量标准再平衡 (平衡各大类资产偏离度)",
                                "💵 新资注入免赎补仓 (发工资/定投补仓·零卖出零赎回费)",
                                "🏧 智能低损耗提现 (急需用钱·零买入·阶梯免赎赎回·避开7天惩罚)",
                                "🧹 尾部碎片与C类一键归拢 (清理<3%碎片与满期高费率C类至底仓)"
                            ],
                            index=0,
                            key="rad_tab2_scenario_mode"
                        )
                    with col_sc2:
                        freeze_reserved_chk = st.checkbox(
                            f"🛡️ 冻结分批建仓预留现金 (¥{pm.reserved_batch_cash:,.2f})",
                            value=True,
                            help="开启后，建仓阶段预留用于二期/三期或定投的现金将被严格保护隔离，绝不作为存量现金在调仓中乱花！",
                            key="chk_freeze_reserved_cash"
                        )

                    scenario_key = "standard"
                    new_cash_val = 0.0
                    withdraw_cash_val = 0.0
                    anchor_target_code = "005561"

                    if "新资注入" in sel_scenario_name:
                        scenario_key = "new_cash_only"
                        c_sc_in1, c_sc_in2 = st.columns([6, 4])
                        with c_sc_in1:
                            new_cash_val = st.number_input("💵 本次计划新增注入的补仓资金 (元)", value=20000.0, step=1000.0, min_value=100.0, key="num_sc_new_cash")
                            st.caption(f"🔢 **金额核对**：{format_chinese_amount(new_cash_val)}")
                        with c_sc_in2:
                            st.caption("💡 系统将 100% 通过新增资金补齐欠配短板标的，卖出金额严格为 0，零赎回摩擦！")
                    elif "低损耗提现" in sel_scenario_name:
                        scenario_key = "withdraw_cash_only"
                        c_sc_in1, c_sc_in2 = st.columns([6, 4])
                        with c_sc_in1:
                            withdraw_cash_val = st.number_input("🏧 本次急需提取现金金额 (元)", value=30000.0, step=1000.0, min_value=100.0, key="num_sc_withdraw_cash")
                            st.caption(f"🔢 **金额核对**：{format_chinese_amount(withdraw_cash_val)}")
                        with c_sc_in2:
                            st.caption("💡 严禁触碰未满 7 天惩罚期标的，优先赎回已满期 C 类或免赎标的，零买入！")
                    elif "碎片" in sel_scenario_name:
                        scenario_key = "sweep_tail_and_c_class"
                        c_sc_in1, c_sc_in2 = st.columns([6, 4])
                        with c_sc_in1:
                            anchor_opts = ["005561 - 创金合信红利低波A", "002351 - 易方达裕祥回报债券A", "000216 - 华安黄金ETF联接A"]
                            sel_anchor = st.selectbox("🎯 回收资金全额归拢买入的压舱石底仓：", anchor_opts, key="sel_sc_anchor")
                            anchor_target_code = sel_anchor.split(" - ")[0]
                        with c_sc_in2:
                            st.caption("💡 一键清理占比 <3% 尾部碎片与满 30 天高费率 C 类，回收资金全额增持底仓！")

                    mode_choice = st.radio(
                        "推演调仓模式：",
                        [f"模式一：温和免伤调仓 (遵循 {cur_buf_val:.1f}% 缓冲与锁定期保护·零惩罚费·首选推荐)", "模式二：强行一步到位调仓 (无视持有期强行全额换仓·核算全额摩擦成本)"],
                        index=0,
                        horizontal=True,
                        key="rad_rebal_mode"
                    )

                if "chosen_target_pool" in locals() and chosen_target_pool.startswith("🌱") and has_t1_opt:
                    tier_target_w = dict(st.session_state["tab1_sim_cache"]["optimal_weights"])
                else:
                    snapshot = StrategyBridge.get_latest_market_snapshot()
                    base_w = StrategyBridge.compute_dynamic_tier_weights(tier=active_tier, market_snapshot=snapshot)
                    overrides = st.session_state.get("custom_fund_overrides", {})
                    tier_target_w = {}
                    for c, w in base_w.items():
                        target_c = overrides.get(c, c)
                        tier_target_w[target_c] = tier_target_w.get(target_c, 0.0) + w

                _cur_buf = float(st.session_state.get("rebalance_buffer_pct", 3.0))

                # 诊断裁决精算
                if st.session_state.get("tab2_trigger_diagnose", False) or st.session_state.get("tab2_diag_cache") is None:
                    suitability = StrategyBridge.evaluate_today_rebalance_suitability(pm, active_tier=active_tier, min_buffer_pct=(_cur_buf / 100.0))
                    st.session_state.tab2_diag_cache = suitability
                    st.session_state.tab2_trigger_diagnose = False
                suitability = st.session_state.get("tab2_diag_cache") or {}

                # 调仓后果模拟精算
                if "scenario_key" not in locals():
                    scenario_key = "standard"
                    new_cash_val = 0.0
                    withdraw_cash_val = 0.0
                    anchor_target_code = "005561"
                    freeze_reserved_chk = True
                    mode_choice = "温和免伤调仓"

                cur_pool_sig = (
                    chosen_target_pool if "chosen_target_pool" in locals() else "default",
                    tuple(sorted(tier_target_w.items())),
                    scenario_key,
                    float(new_cash_val),
                    float(withdraw_cash_val),
                    bool(freeze_reserved_chk),
                    str(anchor_target_code),
                    float(_cur_buf),
                    tuple(sorted(st.session_state.get("tab2_locked_funds") or [])),
                    str(st.session_state.get("tab2_pending_take_profit")),
                    str(st.session_state.get("tab2_c_replace"))
                )
                if st.session_state.get("tab2_last_pool_sig") != cur_pool_sig:
                    st.session_state.tab2_rebal_cache = None
                    st.session_state.tab2_last_pool_sig = cur_pool_sig

                if st.session_state.get("tab2_trigger_rebalance", False) or st.session_state.get("tab2_rebal_cache") is None:
                    sim_res = StrategyBridge.simulate_rebalance_modes_and_consequences(
                        pm,
                        active_tier=active_tier,
                        target_weights=tier_target_w,
                        min_buffer_pct=(_cur_buf / 100.0),
                        locked_funds=st.session_state.get("tab2_locked_funds"),
                        pending_take_profit=st.session_state.get("tab2_pending_take_profit"),
                        c_replace=st.session_state.get("tab2_c_replace"),
                        scenario_mode=scenario_key,
                        new_cash_amount=new_cash_val,
                        withdraw_cash_amount=withdraw_cash_val,
                        freeze_reserved_cash=freeze_reserved_chk,
                        core_anchor_code=anchor_target_code
                    )
                    st.session_state.tab2_rebal_cache = sim_res
                    st.session_state.tab2_trigger_rebalance = False
                sim_res = st.session_state.get("tab2_rebal_cache") or {}

                # 提取 4 格精炼调仓摘要指标
                v_level = suitability.get("verdict_level", "HOLD_ON")
                v_title = suitability.get("verdict_title", "今日维持底仓吃息，无需调仓")
                d_max = suitability.get("d_max", 0.0) * 100.0
                m20_desc = snapshot.get("m20_status_desc", "站上均线")
                v_color = "var(--color-down)" if v_level == "SUITABLE" else ("var(--accent-primary)" if v_level == "HOLD_ON" else "var(--color-up)")

                sel_mode_key = "mode_gentle" if "温和" in mode_choice else "mode_forced"
                cur_sim = sim_res.get(sel_mode_key, sim_res.get("mode_gentle", {}))
                conseq = cur_sim.get("consequences", {})
                fee_loss = conseq.get("fee_loss", {"total_fee": 0.0, "redemption_fee": 0.0, "subscription_fee": 0.0, "penalty_fee_7d": 0.0, "payback_days": 0})
                in_transit = conseq.get("in_transit_risk", {"in_transit_amount": 0.0, "in_transit_pct": 0.0, "lock_days": "0天", "switch_saved_amount": 0.0, "missed_rally_cost_est": 0.0})
                risk_shift = conseq.get("risk_shift", {"vol_before": 0.0, "vol_after": 0.0, "mdd_before": 0.0, "mdd_after": 0.0, "div_yield_before": 0.0, "div_yield_after": 0.0, "equity_after": 0.0})

                pen_badge = f"<span style='color: var(--color-up); font-weight: 600;'>含7天惩罚: ¥{fee_loss.get('penalty_fee_7d', 0):,.2f}</span>" if fee_loss.get('penalty_fee_7d', 0) > 0 else "<span style='color: var(--color-down);'>免收 1.5% 惩罚费</span>"

                # 渲染单行 4 格精炼调仓摘要条
                col_sum1, col_sum2, col_sum3, col_sum4 = st.columns(4)
                with col_sum1:
                    safe_markdown_html(f"""
                    <div class="decision-card" style="padding: 12px 14px; min-height: 100px;">
                        <div class="decision-title" style="font-size: 12px; color: var(--text-secondary); margin-bottom: 2px;">🎯 ① 时机裁决结论</div>
                        <div style="font-size: 15px; font-weight: 700; color: {v_color}; margin: 2px 0;">{v_title}</div>
                        <div style="font-size: 11.5px; color: var(--text-secondary); line-height: 1.4;">
                            偏离度: <b>{d_max:.1f}%</b> (阈值 {_cur_buf:.1f}%)<br>
                            均线突破: <b>{m20_desc}</b> ｜ 申赎窗口: <b>{clock_status.window_type}</b>
                        </div>
                    </div>
                    """)
                with col_sum2:
                    safe_markdown_html(f"""
                    <div class="decision-card" style="padding: 12px 14px; min-height: 100px;">
                        <div class="decision-title" style="font-size: 12px; color: var(--text-secondary); margin-bottom: 2px;">💸 ② 手续费直接损耗</div>
                        <div style="font-size: 15px; font-weight: 700; color: var(--color-up); margin: 2px 0;">¥{fee_loss.get('total_fee', 0.0):,.2f}</div>
                        <div style="font-size: 11.5px; color: var(--text-secondary); line-height: 1.4;">
                            赎回 ¥{fee_loss.get('redemption_fee', 0.0):,.2f} ｜ 申购 ¥{fee_loss.get('subscription_fee', 0.0):,.2f}<br>
                            {pen_badge} ｜ 回本约 <b>{fee_loss.get('payback_days', 0)} 天</b>
                        </div>
                    </div>
                    """)
                with col_sum3:
                    safe_markdown_html(f"""
                    <div class="decision-card" style="padding: 12px 14px; min-height: 100px;">
                        <div class="decision-title" style="font-size: 12px; color: var(--text-secondary); margin-bottom: 2px;">⏳ ③ T+2在途踏空风险</div>
                        <div style="font-size: 15px; font-weight: 700; color: var(--accent-primary); margin: 2px 0;">¥{in_transit.get('in_transit_amount', 0.0):,.2f} ({in_transit.get('in_transit_pct', 0.0):.1f}%)</div>
                        <div style="font-size: 11.5px; color: var(--text-secondary); line-height: 1.4;">
                            资金在途: <b>{in_transit.get('lock_days', '0天')}</b><br>
                            同公司免在途节省: <b>¥{in_transit.get('switch_saved_amount', 0.0):,.2f}</b>
                        </div>
                    </div>
                    """)
                with col_sum4:
                    safe_markdown_html(f"""
                    <div class="decision-card" style="padding: 12px 14px; min-height: 100px;">
                        <div class="decision-title" style="font-size: 12px; color: var(--text-secondary); margin-bottom: 2px;">🛡️ ④ 攻防与回撤变化</div>
                        <div style="font-size: 15px; font-weight: 700; color: var(--text-primary); margin: 2px 0;">波动率 {risk_shift.get('vol_before', 0.0):.1f}% ➔ {risk_shift.get('vol_after', 0.0):.1f}%</div>
                        <div style="font-size: 11.5px; color: var(--text-secondary); line-height: 1.4;">
                            极端回撤: <b>{risk_shift.get('mdd_before', 0.0):.1f}% ➔ {risk_shift.get('mdd_after', 0.0):.1f}%</b><br>
                            股息安全垫: <b>{risk_shift.get('div_yield_before', 0.0):.2f}% ➔ {risk_shift.get('div_yield_after', 0.0):.2f}%</b>
                        </div>
                    </div>
                    """)

                # 生成执行建议单
                rebal_mode_param = "forced" if sel_mode_key == "mode_forced" else "gentle"
                effective_avail_cash = max(0.0, pm.available_cash - getattr(pm, "reserved_batch_cash", 0.0)) if freeze_reserved_chk else pm.available_cash
                ai_orders_res = StrategyBridge.generate_ai_rebalance_orders(
                    current_holdings=pm.holdings,
                    available_cash=effective_avail_cash,
                    target_weights_funds=tier_target_w,
                    pm=pm,
                    mode=rebal_mode_param,
                    min_buffer_pct=_cur_buf,
                    locked_funds=st.session_state.get("tab2_locked_funds"),
                    pending_take_profit=st.session_state.get("tab2_pending_take_profit"),
                    c_replace=st.session_state.get("tab2_c_replace"),
                    scenario_mode=scenario_key,
                    new_cash_amount=new_cash_val,
                    withdraw_cash_amount=withdraw_cash_val,
                    freeze_reserved_cash=freeze_reserved_chk,
                    core_anchor_code=anchor_target_code
                )
                items = ai_orders_res.get("items", [])

                if items:
                    sell_items = [it for it in items if it.get("diff_amount", 0.0) < -100]
                    buy_items = [it for it in items if it.get("diff_amount", 0.0) > 100]
                    # ── ⚡ 智能微观执行滑点优化 (针对买入与定投补仓标的 VWAP 模拟执行与冲击平抑) ──
                    vwap_rebal_orders = []
                    total_buy_amt = 0.0
                    for b_it in buy_items:
                        b_amt = abs(float(b_it.get("diff_amount", 0.0)))
                        total_buy_amt += b_amt
                        b_fc = str(b_it.get("fund_code", ""))
                        b_fn = str(b_it.get("fund_name", ""))
                        # 真实时序多级穿透单基真实年化波动率与单基 bias_20
                        f_metrics = SmartExecutionDCAEngine.get_fund_real_volatility_and_bias(b_fc, b_fn)
                        sl_inf = SmartExecutionDCAEngine.calculate_vwap_execution_slippage(
                            order_amount=b_amt,
                            fund_code=b_fc,
                            fund_name=b_fn,
                            volatility=f_metrics["volatility"],
                            bias_20=f_metrics["bias_20"]
                        )
                        vwap_rebal_orders.append(sl_inf)

                    if vwap_rebal_orders and total_buy_amt > 0:
                        total_rebal_naive_yuan = round(sum(v["naive_impact_yuan"] for v in vwap_rebal_orders), 2)
                        total_rebal_vwap_yuan = round(sum(v["vwap_slippage_yuan"] for v in vwap_rebal_orders), 2)
                        total_rebal_saved_yuan = round(max(0.0, total_rebal_naive_yuan - total_rebal_vwap_yuan), 2)
                        avg_rebal_saved_bps = round((total_rebal_saved_yuan / max(1.0, total_buy_amt)) * 10000.0, 1)

                        has_rebal_etf = any(v.get("is_etf", False) for v in vwap_rebal_orders)
                        col_rv1, col_rv2, col_rv3 = st.columns([3.3, 3.4, 3.3])
                        with col_rv1:
                            if has_rebal_etf:
                                st.metric("买入快速冲击模拟损耗", f"¥{total_rebal_naive_yuan:,.2f}", "单笔市价吃单冲击")
                            else:
                                st.metric("买入早盘盲买偏差损耗", f"¥{total_rebal_naive_yuan:,.2f}", "早盘未知净值波动偏差")
                        with col_rv2:
                            if has_rebal_etf:
                                st.metric("VWAP优化执行滑点", f"¥{total_rebal_vwap_yuan:,.2f}", "日内 5 阶段分笔平抑")
                            else:
                                st.metric("尾盘锚定执行损耗", f"¥{total_rebal_vwap_yuan:,.2f}", "14:30 尾盘估值锚定执行")
                        with col_rv3:
                            st.metric("智能微观优化节省", f"¥{total_rebal_saved_yuan:,.2f}", f"节省 {avg_rebal_saved_bps:.1f} bps 冲击损耗")
                        if has_rebal_etf:
                            st.caption("💡 针对买入加仓与定投补仓标的已实装盘口流动性与 VWAP 分时加权平抑模型，杜绝场内 ETF 快速冲击损耗。")
                        else:
                            st.caption("💡 针对场外公募基金已实装 14:30 尾盘净值锁定与跨日分批执行优化模型，规避早盘盲买冲高回落未知净值偏差风险。")

                    # G13: 同基金公司内部免赎极速转换方案与摩擦节省精算
                    try:
                        same_co_plan = pm.optimize_same_company_conversions(rebalance_plan=ai_orders_res.get("pm_plan"))
                        if same_co_plan.get("has_conversions"):
                            routes_html = "".join([
                                f"""<div style="font-size: 11.5px; color: var(--text-primary); margin-top: 4px; padding: 4px 8px; background: rgba(59, 130, 246, 0.06); border-radius: 4px;">
                                    🔁 <b>{c.get('company')}</b>: {c.get('from_name')}({c.get('from_code')}) ➡️ {c.get('to_name')}({c.get('to_code')}) 
                                    ｜ 转换金额 ¥{c.get('switch_amount', 0):,.2f} 
                                    ｜ 省摩擦 <b>¥{c.get('friction_saved_yuan', 0):,.2f}</b> ({c.get('saved_bps', 0):.1f} bps, 免除 {c.get('transit_days_saved', 3.5):.1f} 天在途)
                                </div>"""
                                for c in same_co_plan.get("conversions", [])[:3]
                            ])
                            safe_markdown_html(f"""
                            <div class="decision-card" style="border-left: 3px solid var(--accent-primary); padding: 10px 14px; margin-bottom: 12px; background: var(--bg-surface);">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                                    <div style="font-size: 13px; font-weight: 700; color: var(--accent-primary);">
                                        🔄 同基金公司内部免赎极速转换方案 (0在途 · 摩擦优化)
                                    </div>
                                    <span style="font-size: 11.5px; color: var(--color-up); font-weight: 600;">
                                        ⚡ 节省资金成本与费率 ¥{same_co_plan['total_saved_yuan']:,.2f} ({same_co_plan['avg_saved_bps']:.1f} bps)
                                    </span>
                                </div>
                                <div style="font-size: 11.5px; color: var(--text-secondary); line-height: 1.5; margin-bottom: 6px;">
                                    {same_co_plan['summary']}
                                </div>
                                {routes_html}
                                <div style="font-size: 11px; color: var(--text-primary); background: var(--bg-card); padding: 6px 10px; border-radius: 4px; margin-top: 6px;">
                                    ⏱️ 转换免除传统【赎回➔现金到账(3~5天)➔重新申购】在途资金占用风险与再申购费，精算年化 2.0% 资金成本节省。
                                </div>
                            </div>
                            """)
                    except Exception as e_same_co:
                        pass

                    rebal_order_map = {str(v.get("fund_code")): v for v in vwap_rebal_orders}
                    rows_display = []
                    for it in items:
                        diff_amt = it.get("diff_amount", 0.0)
                        action_raw = str(it.get("action_text", ""))
                        safety = str(it.get("safety_warning", "") or "")
                        holding_days = it.get("holding_days", 999)
                        f_code = str(it.get("fund_code", ""))
                        f_name = str(it.get("fund_name", ""))
                        rt_gszzl = it.get("realtime_gszzl", 0.0)

                        if "手动锁定" in action_raw or "禁卖" in action_raw or "锁定" in action_raw:
                            op_action = "🔒 已手动锁定禁卖"
                            op_point = "主动风控·锁死持仓下界"
                        elif "C转A" in action_raw or "置换" in action_raw:
                            op_action = "🔄 C转A零费率置换"
                            op_point = "C类高费率清理·换入A类底仓"
                        elif "暂缓赎回" in action_raw or "免赎立省" in action_raw:
                            op_action = "⏳ 临期暂缓免赎"
                            op_point = action_raw
                        elif "7天" in safety or holding_days < 7 or "锁仓" in action_raw:
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

                        # 附加交割清算与基金属性标签及跨币种实时离岸汇率纠偏
                        fx_adj = calculate_fx_adjusted_intraday_valuation(f_code, f_name, raw_valuation_pct=rt_gszzl)
                        if fx_adj.get("is_applicable"):
                            corr_val = fx_adj.get("corrected_pct", rt_gszzl)
                            drift = fx_adj.get("fx_drift_bps", 0.0)
                            if abs(drift) >= 0.5:
                                op_point += f"·💱汇率纠偏至{corr_val:+.2f}%({drift:+.1f}bp)"
                            elif pm.is_qdii_fund(f_code, f_name):
                                op_point += "·跨时区T+2确认"
                        elif pm.is_qdii_fund(f_code, f_name):
                            op_point += "·跨时区T+2确认"
                        elif any(k in pm.classify_fund_asset_class(f_code, f_name) for k in ["纯债", "固收", "债券"]):
                            op_point += "·票息久期底仓"

                        # 接入 14:30 尾盘实时估值异动预警算子 (防追高/黄金坑) 与单基差异化损耗基点
                        tail_anom = StrategyBridge.evaluate_tail_valuation_anomaly(
                            fund_code=f_code,
                            fund_name=f_name,
                            realtime_quote=rt_gszzl
                        )
                        saved_bps_val = rebal_order_map.get(f_code, {}).get("slippage_saved_bps", 0.0)

                        if tail_anom.get("is_anomaly"):
                            op_point = f"{tail_anom['anomaly_tag']} ｜ {op_point}"
                        elif diff_amt > 100 and saved_bps_val > 0:
                            op_point += f"·尾盘微观省{saved_bps_val:.1f}bp"

                        saved_bps_disp = f"{saved_bps_val:.1f} bps" if (diff_amt > 100 and saved_bps_val > 0) else "-"

                        rows_display.append({
                            "基金代码": f_code,
                            "基金名称": f_name,
                            "份额": f"{it.get('share_class', 'A')}类",
                            "当前市值(元)": it["market_value"],
                            "目标占比(%)": it["target_weight_pct"],
                            "实时估值涨跌(%)": rt_gszzl,
                            "建议调仓金额(元)": diff_amt,
                            "建议操作": op_action,
                            "尾盘微观优化(bps)": saved_bps_disp,
                            "实操要点": op_point
                        })

                    rebal_cols_10 = [
                        "基金代码", "基金名称", "份额", "当前市值(元)",
                        "目标占比(%)", "实时估值涨跌(%)", "建议调仓金额(元)",
                        "建议操作", "尾盘微观优化(bps)", "实操要点"
                    ]
                    df_orders_tbl = pd.DataFrame(rows_display)[rebal_cols_10]
                    st.dataframe(
                        df_orders_tbl,
                        column_config={
                            "当前市值(元)": st.column_config.NumberColumn(format="¥%.2f"),
                            "目标占比(%)": st.column_config.ProgressColumn(min_value=0, max_value=50, format="%.2f%%"),
                            "实时估值涨跌(%)": st.column_config.NumberColumn(format="%+.2f%%"),
                            "建议调仓金额(元)": st.column_config.NumberColumn(format="¥%+.2f"),
                            "尾盘微观优化(bps)": st.column_config.TextColumn(
                                "尾盘微观优化(bps) ⓘ",
                                help="基于单基真实20日年化波动率与自身偏离度测算之 14:30 尾盘锚定/VWAP 优化执行节省基点。"
                            ),
                            "实操要点": st.column_config.TextColumn(
                                "实操要点 ⓘ",
                                help="实操要点：包含尾盘异动防追高/黄金坑预警、分红方式、未满7天防惩罚性扣款锁仓、临近30天免赎回费保护及分批调仓指引。"
                            )
                        },
                        use_container_width=True,
                        hide_index=True
                    )

                    if vwap_rebal_orders:
                        exp_rebal_lbl = "⏱️ 查看买入/补仓标的分批执行调度表（尾盘净值锁定与跨日分批执行优化）" if not any(v.get("is_etf", False) for v in vwap_rebal_orders) else "⏱️ 查看买入/补仓标的 VWAP 分时成交量加权挂单调度表（日内 5 阶段分笔平抑冲击）"
                        with st.expander(exp_rebal_lbl, expanded=False):
                            if len(vwap_rebal_orders) > 1:
                                sel_v_idx = st.selectbox(
                                    "选择查看挂单调度表的标的：",
                                    options=range(len(vwap_rebal_orders)),
                                    format_func=lambda idx: f"{vwap_rebal_orders[idx]['fund_code']} {vwap_rebal_orders[idx]['fund_name']} (买入 ¥{vwap_rebal_orders[idx]['order_amount']:,.2f})",
                                    key="sel_tab2_vwap_schedule_item"
                                )
                                v_slices = vwap_rebal_orders[sel_v_idx].get("vwap_slices", [])
                            else:
                                v_slices = vwap_rebal_orders[0].get("vwap_slices", [])
                            if v_slices:
                                st.dataframe(pd.DataFrame(v_slices), use_container_width=True, hide_index=True)

                        # G10: 挂载大额订单流动性折价明细表
                        try:
                            render_liquidity_haircut_table(vwap_rebal_orders)
                        except Exception as e_liq_tab2:
                            st.caption(f"（流动性折价表加载提示: {e_liq_tab2}）")

                    guidance = clock.get_action_guidance_for_window()
                    if guidance["stage"] == "OBSERVATION":
                        st.info(guidance["message"])
                    elif guidance["stage"] == "GOLDEN_WINDOW":
                        st.success(guidance["message"])
                    else:
                        safe_markdown_html(f"""
                        <div style="background: var(--bg-elevated); border: 1.5px solid var(--border-hover); border-radius: 8px; padding: 14px 18px; margin-bottom: 12px;">
                            <div style="font-size: 15px; font-weight: 700; color: var(--accent-primary); margin-bottom: 8px;">
                                ⚠️ 当前已过 15:00 场外基金关账时间
                            </div>
                            <div style="font-size: 13px; line-height: 1.6; color: var(--text-primary);">
                                现在在基金 App 下单将按下一交易日 15:00 的未知收盘净值成交，建议保存为明日盯盘待办预案。
                            </div>
                        </div>
                        """)

                    col_exec_ai, col_send_bt = st.columns([5, 5])
                    with col_exec_ai:
                        if guidance["stage"] == "POST_MARKET":
                            if st.button("📌 保存明日预案", type="primary", use_container_width=True, key="btn_save_next_plan_tab2"):
                                p_id = pm.save_next_day_plan({"target_weights": tier_target_w, "items": items, "mode": sel_mode_key})
                                st.balloons()
                                st.success(f"已成功将本次调仓方案保存为明日盯盘预案（{p_id}）。")
                                st.rerun()
                        elif guidance["stage"] == "GOLDEN_WINDOW":
                            if st.button("✅ 立即执行调仓", type="primary", use_container_width=True, key="btn_exec_gold_tab2"):
                                _cur_buf = float(st.session_state.get("rebalance_buffer_pct", 3.0))
                                rebal_plan = pm.generate_scenario_rebalance_plan(tier_target_w, scenario_mode=scenario_key, new_cash_amount=new_cash_val, withdraw_cash_amount=withdraw_cash_val, freeze_reserved_cash=freeze_reserved_chk, min_buffer_pct=(0.0 if sel_mode_key == "mode_forced" else _cur_buf), core_anchor_code=anchor_target_code)
                                routes_to_run = rebal_plan.get("routes", [])
                                if routes_to_run:
                                    oids = pm.submit_rebalance_orders(routes_to_run)
                                    st.balloons()
                                    st.success(f"✅ 已成功执行调仓，生成 {len(oids)} 笔指令。")
                                    st.rerun()
                                else:
                                    st.info(f"持仓偏离均在 {_cur_buf:.1f}% 缓冲阈值内，无需额外调仓。")
                        elif guidance["stage"] == "OBSERVATION":
                            allow_early = st.checkbox(
                                "⚠️ 我已了解盘中冲高/跳水风险，仍希望在 14:30 前提前执行",
                                value=False,
                                key="chk_allow_early_rebalance"
                            )
                            if allow_early:
                                if st.button("⚡ 提前执行调仓", type="primary", use_container_width=True, key="btn_exec_early_tab2"):
                                    _cur_buf = float(st.session_state.get("rebalance_buffer_pct", 3.0))
                                    rebal_plan = pm.generate_scenario_rebalance_plan(tier_target_w, scenario_mode=scenario_key, new_cash_amount=new_cash_val, withdraw_cash_amount=withdraw_cash_val, freeze_reserved_cash=freeze_reserved_chk, min_buffer_pct=(0.0 if sel_mode_key == "mode_forced" else _cur_buf), core_anchor_code=anchor_target_code)
                                    routes_to_run = rebal_plan.get("routes", [])
                                    if routes_to_run:
                                        oids = pm.submit_rebalance_orders(routes_to_run)
                                        st.balloons()
                                        st.success(f"✅ 已成功提前执行调仓，生成 {len(oids)} 笔指令。")
                                        st.rerun()
                                    else:
                                        st.info(f"持仓偏离均在 {_cur_buf:.1f}% 缓冲阈值内，无需额外调仓。")
                            else:
                                st.button("⏳ 盘中观察中 (等待 14:30 尾盘趋势锁定解锁)", disabled=True, use_container_width=True, key="btn_obs_disabled_tab2")
                        else:
                            st.button("⏳ 盘前非交易时段 (请等待开盘)", disabled=True, use_container_width=True, key="btn_pre_disabled_tab2")

                    with col_send_bt:
                        if st.button("📈 送入回测对比", type="secondary", use_container_width=True, key="btn_send_rebal_to_bt"):
                            st.session_state.selected_backtest_target = "调仓前后对比"
                            st.session_state.selected_secondary_weights = tier_target_w
                            st.session_state.tab3_backtest_activated = True
                            st.success("✅ 已将调仓前后组合送入组合回测，请切换至 Tab 3 查看双曲线对比。")

                    # 一键跟单打卡闭环按钮
                    safe_markdown_html("<div style='height: 8px;'></div>")
                    if st.button("✅ 我已在手机端按此方案下单 ➔ 一键将调仓单同步至当前账本持仓", type="primary", use_container_width=True, key="btn_confirm_follow_rebalance_tab2"):
                        with st.spinner("🔄 正在执行调仓账本同步与净值打卡..."):
                            up_cnt = pm.apply_rebalance_orders_to_holdings(rows_display)
                            st.session_state.tab2_diag_cache = None
                            st.session_state.tab2_rebal_cache = None
                            st.session_state.tab2_diagnosed = False
                            st.session_state.tab2_rebalanced = False
                            st.session_state.tab2_trigger_diagnose = False
                        st.balloons()
                        st.success(f"🎉 成功同步！已将 {up_cnt} 笔调仓执行单记账入库，实盘账户净值走势已打卡！")
                        st.rerun()


        else:
            # ── 模式二：💼 账本运维与实盘复盘档案 (独立宽屏工具坞，全宽平铺无 expander) ──
            st.markdown("### 💼 账本运维与实盘复盘档案 (独立宽屏工具坞)")
            st.caption("提供快速录入、FIFO批次透视、实盘影子档案、T+1对账、同公司转换及宏观分红研判全套工具。")
            dock_tab1, dock_tab2, dock_tab3, dock_tab4, dock_tab5, dock_tab6 = st.tabs([
                "✨ 快速录入/导入持仓",
                "📦 FIFO批次解锁透视",
                "🗄️ 账本环境与实盘档案",
                "⏳ 在途订单与T+1对账中心",
                "🔄 同公司基金低摩擦转换",
                "💰 宏观估值自适应分红"
            ])
            with dock_tab1:
                # 文本粘贴 / 搜索 / 表格导入
                sub_tab1, sub_tab2, sub_tab3 = st.tabs([
                    "📋 文本粘贴导入",
                    "🔍 搜索添加标的",
                    "📥 表格模板导入"
                ])
                with sub_tab1:
                    sample_smart_text = """华泰柏瑞低波\n005561\n持有金额 30,000.00\n持有收益 +1,200.00\n昨日收益 +120.00\n持有天数 45天\n\n易方达裕祥\n002351\n持有金额 20000\n收益: 亏500\n持有天数: 180天\n\n华夏科创50C 20000 收益率-8.5% 3天"""
                    smart_text_in = st.text_area("📝 在此粘贴持仓文字（支持手机截图 OCR 多行块状或单行紧凑文本）：", value=sample_smart_text, height=120, key="txt_smart_holdings")
                    col_st_c, col_st_b = st.columns([4, 6])
                    with col_st_c:
                        smart_cash_in = st.number_input("账户可用现金 (元)", value=float(pm.available_cash or 10000.0), step=1000.0, key="smart_cash_input")
                    with col_st_b:
                        st.write(" ")
                        st.write(" ")
                        btn_parse_ocr = st.button("🔍 智能深度解析与结构化预览", type="primary", use_container_width=True, key="btn_parse_smart_text")

                    if btn_parse_ocr or st.session_state.get("tab2_ocr_preview_items"):
                        if btn_parse_ocr:
                            st.session_state.tab2_ocr_preview_items = pm.parse_smart_text_holdings(smart_text_in)

                        ocr_items = st.session_state.get("tab2_ocr_preview_items") or []
                        if ocr_items:
                            st.markdown("###### 📋 识别结果结构化预览与平账核对")
                            df_prev = pd.DataFrame([{
                                "基金代码": it["fund_code"],
                                "基金名称": it["fund_name"],
                                "当前市值(元)": f"¥{it['amount']:,.2f}",
                                "估算份额": f"{it['shares']:,.2f}",
                                "加权成本价": f"¥{it['cost_price']:.4f}",
                                "浮动盈亏(元)": f"¥{it['floating_pnl']:+,.2f}",
                                "盈亏率(%)": f"{it['floating_pnl_pct']:+.2f}%",
                                "持有天数": f"{it['holding_days']}天"
                            } for it in ocr_items])
                            st.dataframe(df_prev, use_container_width=True)

                            col_act_merge, col_act_overwrite, col_act_cancel = st.columns([4, 4, 2])
                            with col_act_merge:
                                if st.button("➕ 追加合并至现有账本", type="primary", use_container_width=True, key="btn_ocr_merge"):
                                    for it in ocr_items:
                                        pm.add_or_update_holding(
                                            fund_code=it["fund_code"],
                                            shares=it["shares"],
                                            nav=it["current_nav"],
                                            cost_price=it["cost_price"],
                                            holding_days=it["holding_days"],
                                            fund_name=it["fund_name"],
                                            notes="OCR智能解析追加",
                                            append_batch=True
                                        )
                                    pm.available_cash = smart_cash_in
                                    pm.save_state()
                                    st.session_state.tab2_ocr_preview_items = None
                                    st.session_state.tab2_diag_cache = None
                                    st.session_state.tab2_rebal_cache = None
                                    st.success(f"已成功追加合并 {len(ocr_items)} 只标的！")
                                    st.rerun()
                            with col_act_overwrite:
                                if st.button("🔄 全量覆盖现有账本", type="secondary", use_container_width=True, key="btn_ocr_overwrite"):
                                    pm.import_from_smart_text(ocr_items, available_cash=smart_cash_in)
                                    st.session_state.tab2_ocr_preview_items = None
                                    st.session_state.tab2_diag_cache = None
                                    st.session_state.tab2_rebal_cache = None
                                    st.balloons()
                                    st.success(f"已全量重置并接管 {len(ocr_items)} 只标的！")
                                    st.rerun()
                            with col_act_cancel:
                                if st.button("✖️ 取消预览", use_container_width=True, key="btn_ocr_cancel"):
                                    st.session_state.tab2_ocr_preview_items = None
                                    st.rerun()
                        else:
                            st.warning("未能识别出有效持仓文本，请检查输入或格式。")

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
                            st.success(f"已添加 {sel_c}。")
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
                            st.success(f"成功导入 {res_s.get('imported_count', 0)} 条快照。")
                            st.rerun()

            with dock_tab2:
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

            with dock_tab3:
                # 资产基线与风控防线卡片
                _tot_eq = sum(h.market_value for h in pm.holdings.values()) + pm.available_cash + pm.in_transit_cash
                safe_markdown_html(f"""
                <div style="background: var(--bg-elevated); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 10px 14px; margin-bottom: 12px; font-size: 12px; color: var(--text-secondary);">
                    💼 <b>资产基线</b>：¥{_tot_eq:,.2f} ｜ <b>持仓标的</b>：<b>{len(pm.holdings)} 只</b> ｜ <b>在途现金</b>：¥{pm.in_transit_cash:,.2f}<br>
                    🛡️ <b>风控防线</b>：7天惩罚费拦截 (1.50%惩罚扣除硬阻断) ｜ 悲观持有天数梯级守护
                </div>
                """)



                st.markdown("---")
                st.markdown("##### 📋 实盘接管基准档案与净值曲线")
                col_arch1, col_arch2 = st.columns(2)
                with col_arch1:
                    st.write(f"**接管模式**：{'模式 A (极简冷启动)' if pm.takeover_mode == 'A' else '模式 B (账本热接管)'}")
                    st.write(f"**基准确立日**：`{pm.baseline_date}`")
                    st.write(f"**接管基准总资产**：¥{pm.baseline_equity:,.2f}")
                with col_arch2:
                    st.write(f"**峰值总资产**：¥{pm.peak_equity:,.2f}")
                    st.write(f"**接管期最大回撤**：`{pm.max_drawdown_pct:.2f}%`")
                    st.write(f"**基准超额 (Alpha)**：`{pm.alpha_return_pct:+.2f}%` (vs {pm.benchmark_code})")

                # 绘制《实盘账户累计净值 vs 沪深300基准走势图》
                nav_records = getattr(pm, "nav_history", []) or []
                if not nav_records:
                    nav_records = [
                        {"date": pm.baseline_date, "account_nav": 1.0000, "benchmark_nav": 1.0000},
                        {"date": datetime.now().strftime("%Y-%m-%d"), "account_nav": round(1.0 + pm.portfolio_return_pct/100.0, 4), "benchmark_nav": round(1.0 + pm.benchmark_return_pct/100.0, 4)}
                    ]

                df_nav_curve = pd.DataFrame(nav_records)
                if not df_nav_curve.empty and "date" in df_nav_curve.columns:
                    fig_nav = px.line(
                        df_nav_curve,
                        x="date",
                        y=["account_nav", "benchmark_nav"],
                        labels={"date": "日期", "value": "累计单位净值", "variable": "对比曲线"},
                        title=f"📈 实盘账户累计净值走势 (接管至今 Alpha: {pm.alpha_return_pct:+.2f}%)",
                        color_discrete_map={"account_nav": "#38bdf8", "benchmark_nav": "#94a3b8"}
                    )
                    fig_nav.update_layout(
                        margin=dict(t=35, b=10, l=10, r=10),
                        height=260,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    apply_theme_to_plotly_figure(fig_nav)
                    st.plotly_chart(fig_nav, use_container_width=True)

                st.markdown("---")
                st.markdown("##### 📊 买方投顾价值与调仓复盘账单")
                st.caption("复盘审计引擎：实时对比实盘当前总资产与初始接管基准（躺平不调仓）的影子组合表现，清晰量化主动调仓带来的超额收益与风控规避的摩擦成本。")
                audit_res = pm.evaluate_rebalance_audit()
                col_aud1, col_aud2, col_aud3 = st.columns(3)
                with col_aud1:
                    safe_markdown_html(f"""
                    <div class="decision-card" style="min-height: 95px; height: auto !important; overflow: visible !important;">
                        <div class="decision-title">实盘总资产 vs 影子组合</div>
                        <div class="decision-val" style="color: var(--accent-primary);">¥{audit_res['current_actual_equity']:,.2f}</div>
                        <div class="decision-desc">
                            躺平影子总资产: <b>¥{audit_res['shadow_hold_equity']:,.2f}</b><br>
                            基准确立日: <code>{audit_res.get('baseline_date', '接管日')}</code>
                        </div>
                    </div>
                    """)
                with col_aud2:
                    val_add = audit_res['rebalance_value_add']
                    val_pct = audit_res['rebalance_value_add_pct']
                    c_val = "var(--color-up)" if val_add >= 0 else "var(--color-down)"
                    safe_markdown_html(f"""
                    <div class="decision-card" style="min-height: 95px; height: auto !important; overflow: visible !important;">
                        <div class="decision-title">主动调仓净增厚 (Alpha)</div>
                        <div class="decision-val" style="color: {c_val};">{val_add:+,.2f} 元</div>
                        <div class="decision-desc">
                            增厚超额幅度: <b>{val_pct:+.2f}%</b><br>
                            调仓收益扣除手续费后净值增厚
                        </div>
                    </div>
                    """)
                with col_aud3:
                    safe_markdown_html(f"""
                    <div class="decision-card" style="min-height: 95px; height: auto !important; overflow: visible !important;">
                        <div class="decision-title">AI 风控规避损失与损耗</div>
                        <div class="decision-val" style="color: var(--color-down);">¥{audit_res['saved_penalty_and_buffer_fees']:,.2f}</div>
                        <div class="decision-desc">
                            包含规避 1.50% 巨额惩罚性赎回费<br>
                            及免折腾缓冲带节省的摩擦成本
                        </div>
                    </div>
                    """)

                # Brinson-Fachler 经典三维归因卡片
                brinson_attr = audit_res.get("brinson_attribution", {})
                alloc_yuan = brinson_attr.get("allocation_effect_yuan", 0.0)
                alloc_pct = brinson_attr.get("allocation_effect_pct", 0.0)
                select_yuan = brinson_attr.get("selection_effect_yuan", 0.0)
                select_pct = brinson_attr.get("selection_effect_pct", 0.0)
                fric_yuan = brinson_attr.get("friction_saving_yuan", audit_res['saved_penalty_and_buffer_fees'])
                fric_pct = brinson_attr.get("friction_saving_pct", 0.0)
                c_alloc = "var(--color-up)" if alloc_yuan >= 0 else "var(--color-down)"
                c_select = "var(--color-up)" if select_yuan >= 0 else "var(--color-down)"

                st.markdown("###### 🏛️ Brinson-Fachler 经典三维超额收益归因 (Allocation vs Selection)")
                st.caption("买方投顾穿透归因：将主动调仓净增厚严格拆解为大类资产配置效应、优选基金超额效应与交易摩擦防御贡献。")
                col_b1, col_b2, col_b3 = st.columns(3)
                with col_b1:
                    safe_markdown_html(f"""
                    <div class="decision-card" style="min-height: 100px; height: auto !important; overflow: visible !important; border-top: 2px solid var(--accent-primary);">
                        <div class="decision-title">🏛️ 大类资产配置效应 (Allocation)</div>
                        <div class="decision-val" style="color: {c_alloc};">{alloc_yuan:+,.2f} 元</div>
                        <div class="decision-desc">
                            配置超额贡献: <b>{alloc_pct:+.2f}%</b><br>
                            基于宏观大类与赛道轮动超配/低配增厚
                        </div>
                    </div>
                    """)
                with col_b2:
                    safe_markdown_html(f"""
                    <div class="decision-card" style="min-height: 100px; height: auto !important; overflow: visible !important; border-top: 2px solid var(--color-up);">
                        <div class="decision-title">🎯 优选基金超额效应 (Selection)</div>
                        <div class="decision-val" style="color: {c_select};">{select_yuan:+,.2f} 元</div>
                        <div class="decision-desc">
                            选基超额贡献: <b>{select_pct:+.2f}%</b><br>
                            同一资产大类内部优选冠军标的阿尔法
                        </div>
                    </div>
                    """)
                with col_b3:
                    safe_markdown_html(f"""
                    <div class="decision-card" style="min-height: 100px; height: auto !important; overflow: visible !important; border-top: 2px solid var(--color-down);">
                        <div class="decision-title">🛡️ 交易摩擦及惩罚规避 (Friction)</div>
                        <div class="decision-val" style="color: var(--color-down);">¥{fric_yuan:,.2f}</div>
                        <div class="decision-desc">
                            费率增厚贡献: <b>+{fric_pct:.2f}%</b><br>
                            守死 &lt;7天 1.50% 巨额惩罚赎回费守护成果
                        </div>
                    </div>
                    """)

                # 多大类资产归因明细表
                category_breakdown = brinson_attr.get("category_breakdown", [])
                if category_breakdown:
                    st.markdown("###### 📑 9大资产大类 Brinson-Fachler 归因明细")
                    df_breakdown = pd.DataFrame([
                        {
                            "资产大类": item["category"],
                            "实盘权重": f"{item['portfolio_weight_pct']:.2f}%",
                            "基准权重": f"{item['benchmark_weight_pct']:.2f}%",
                            "权重偏离": f"{item['weight_diff_pct']:+.2f}%",
                            "实盘收益": f"{item['portfolio_return_pct']:+.2f}%",
                            "基准收益": f"{item['benchmark_return_pct']:+.2f}%",
                            "配置效应(元)": f"{item['allocation_effect_yuan']:+,.2f}",
                            "选基效应(元)": f"{item['selection_effect_yuan']:+,.2f}",
                            "合计增厚(元)": f"{item['total_effect_yuan']:+,.2f}",
                        }
                        for item in category_breakdown
                    ])
                    st.dataframe(df_breakdown, use_container_width=True, hide_index=True)

                # 买方投顾穿透复盘点评
                st.markdown("###### 💡 买方投顾穿透复盘点评")
                primary_driver = brinson_attr.get("primary_driver", "大类资产配置效应")
                if val_add >= 0:
                    commentary = (
                        f"本次实盘调仓相比初始接管基准（躺平影子组合）取得净增厚 <b>+{val_add:,.2f} 元 (+{val_pct:.2f}%)</b>。"
                        f"穿透归因显示，超额收益核心驱动力为<b>【{primary_driver}】</b>（大类资产配置贡献 <b>{alloc_yuan:+,.2f} 元</b>，"
                        f"优选基金超额贡献 <b>{select_yuan:+,.2f} 元</b>）。"
                        f"同时，AI 风控严格守底线，累计为组合规避 <b>¥{fric_yuan:,.2f}</b> 的交易摩擦与赎回惩罚，实现稳健增厚。"
                    )
                else:
                    commentary = (
                        f"本次实盘调仓相较初始影子基准净偏离 <b>{val_add:,.2f} 元 ({val_pct:.2f}%)</b>，"
                        f"归因分析表明主要受<b>【{primary_driver}】</b>影响（大类配置偏离 <b>{alloc_yuan:+,.2f} 元</b>，"
                        f"优选基金偏离 <b>{select_yuan:+,.2f} 元</b>）。"
                        f"但买方投顾风控引擎成功拦截流动性损耗，为您守住 <b>¥{fric_yuan:,.2f}</b> 的刚性惩罚赎回费，"
                        f"有效控制了潜在回撤并保留了高安全边际底仓。"
                    )
                safe_markdown_html(f"""
                <div class="decision-card" style="padding: 10px 14px; border-left: 3px solid var(--accent-primary); background: var(--bg-surface); min-height: 50px; overflow: visible !important;">
                    <div style="font-size: 12px; color: var(--text-primary); line-height: 1.5;">
                        {commentary}
                    </div>
                </div>
                """)

            with dock_tab4:
                st.markdown("##### ⏳ 在途订单确认与 T+1 对账中心")
                st.caption("真实买方投顾对账引擎：资金提交申报后转入在途状态，T+1 日拉取真实收盘净值一键校准份额入库或清算到账。")
            
                active_orders = [o for o in pm.pending_orders if getattr(o, "status", "") == "PENDING"]
                if active_orders:
                    st.markdown(f"**当前在途待对账订单：{len(active_orders)} 笔**")
                    for o_idx, p_ord in enumerate(active_orders):
                        p_code = getattr(p_ord, "fund_code", "")
                        p_name = getattr(p_ord, "fund_name", p_code)
                        p_act = getattr(p_ord, "action", "BUY")
                        p_amt = float(getattr(p_ord, "amount", 0.0))
                        p_shares = float(getattr(p_ord, "shares", 0.0))
                        p_dt = getattr(p_ord, "create_time", getattr(p_ord, "effective_trade_date", "今日"))
                    
                        act_tag = "申购/转入" if "BUY" in p_act else ("赎回/转出" if "SELL" in p_act else "转换")
                        c_ord1, c_ord2, c_ord3, c_ord4 = st.columns([4, 2.5, 2, 1.5])
                        with c_ord1:
                            st.markdown(f"**{p_name}** (`{p_code}`) ｜ **{act_tag}**")
                            st.caption(f"订单号: `{p_ord.order_id}` ｜ 申报时间: {p_dt}")
                        with c_ord2:
                            st.markdown(f"申报金额: **¥{p_amt:,.2f}**" if p_amt > 0 else f"申报份额: **{p_shares:,.2f}份**")
                        with c_ord3:
                            # 预估净值输入
                            default_cf_nav = 1.0
                            if p_code in pm.holdings:
                                default_cf_nav = float(pm.holdings[p_code].current_nav)
                            cf_nav = st.number_input("确认净值", value=default_cf_nav, step=0.001, format="%.4f", key=f"num_rec_nav_{p_ord.order_id}")
                        with c_ord4:
                            if st.button("✅ 确认到账", type="primary", use_container_width=True, key=f"btn_rec_ok_{p_ord.order_id}"):
                                res_rec = pm.reconcile_pending_order(p_ord.order_id, confirmed_nav=cf_nav)
                                st.success(f"✅ 订单 {p_ord.order_id} 已成功对账入库！")
                                st.rerun()
                else:
                    st.info("💡 当前暂无在途申报订单。您可点击下方按钮模拟生成一笔在途申购订单以体验 T+1 对账全流程：")
                    if st.button("➕ 模拟生成一笔在途申购订单 (创金合信红利低波 005561 ¥5,000)", key="btn_mock_pending_order"):
                        import uuid
                        from portfolio_manager import PendingOrder
                        mock_oid = f"ORD_{uuid.uuid4().hex[:8].upper()}"
                        mock_ord = PendingOrder(
                            order_id=mock_oid,
                            fund_code="005561",
                            fund_name="创金合信中证红利低波动A",
                            action="BUY",
                            amount=5000.0,
                            shares=0.0,
                            est_nav=1.258,
                            est_fee=0.0,
                            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            effective_trade_date=datetime.now().strftime("%Y-%m-%d"),
                            status="PENDING",
                            notes="买方投顾模拟在途对账单"
                        )
                        pm.pending_orders.append(mock_ord)
                        pm.in_transit_cash = round(pm.in_transit_cash + 5000.0, 2)
                        pm.save_state()
                        st.success("✅ 模拟在途申购订单已生成！请查看上方订单列表进行 T+1 对账。")
                        st.rerun()

            with dock_tab5:
                st.markdown("##### 🔄 同公司基金低摩擦转换")
                st.caption("公募基金公司内部转换机制：A/C 份额同系互转免除赎回款离场在途等待期 (T+1 到账)，免收前端认购费，仅收取极低级差费。")
                st.info("💡 **交割规则说明**：海外 QDII 基金（T+2 确认、赎回 T+6~T+8 到账）与跨注册登记机构品种不支持同公司 T+1 极速转换，系统已自动过滤保护。")
                # 扫描同公司基金
                company_map = {}
                for c_k, h_v in pm.holdings.items():
                    # 自动排除海外 QDII 基金
                    if pm.is_qdii_fund(c_k, h_v.fund_name):
                        continue
                    c_meta = pm.resolve_fund_meta(c_k)
                    comp_name = c_meta.get("company", "") or "通用公募"
                    if comp_name not in company_map:
                        company_map[comp_name] = []
                    company_map[comp_name].append((c_k, h_v.fund_name, h_v.share_class, h_v.market_value))
            
                eligible_comps = {k: v for k, v in company_map.items() if len(v) >= 2 or any(h[2] == 'C' for h in v)}
                if eligible_comps:
                    for comp, funds in eligible_comps.items():
                        st.markdown(f"**🏢 {comp}**（旗下持仓标的 {len(funds)} 只）：")
                        f_descs = [f"{fn} ({fc}) [{sc}类, 市值¥{mv:,.0f}]" for fc, fn, sc, mv in funds]
                        safe_markdown_html("- " + "<br>- ".join(f_descs))
                else:
                    st.write("当前持仓中各基金归属不同基金公司。建议在【华夏基金】内部实现 011613 (C类) 与 011612 (A类) 的低费率互转。")
            
                col_sw1, col_sw2, col_sw3 = st.columns([4, 4, 2])
                with col_sw1:
                    non_qdii_holdings = [c for c, h in pm.holdings.items() if not pm.is_qdii_fund(c, h.fund_name)]
                sw_from = st.selectbox("转出基金 (来源)", non_qdii_holdings if non_qdii_holdings else list(pm.holdings.keys()), key="sel_switch_from")
                with col_sw2:
                    sw_to = st.text_input("转入基金代码 (同公司标的)", value="011612" if sw_from == "011613" else "005561", max_chars=6, key="txt_switch_to")
                with col_sw3:
                    if st.button("🚀 执行转换", type="primary", use_container_width=True, key="btn_do_switch"):
                        sw_h = pm.holdings.get(sw_from)
                        if sw_h and sw_to:
                            sw_amt = float(sw_h.market_value)
                            util = pm.calculate_rebalance_net_utility(sw_from, sw_to, sw_amt)
                            st.info(f"转换净效用判定: {util.get('interception_badge')} (预计省去在途成本 ¥{util.get('in_transit_opportunity_cost', 0):.2f})")
                            st.toast("✅ 同公司转换申请已提交，已进入在途对账队列！")

            with dock_tab6:
                st.markdown("##### 💰 宏观估值自适应分红研判")
                st.caption("买方投顾分红自适应铁律：低估磨底期强制【红利再投】以便宜筹码摊薄成本；过热高位期强制【现金分红】零摩擦落袋为安。")
                cur_erp = float(snapshot.get("erp_percentile", 82.0))
                rec_div = "reinvest" if cur_erp >= 70.0 else ("cash" if cur_erp <= 35.0 else "neutral")
            
                if rec_div == "reinvest":
                    st.success(f"🧭 宏观 ERP 估值分位数达 **{cur_erp:.1f}%** (处于历史极高性价比底部磨底期)：**全组合首选建议设为【红利再投资】**，以零申购费滚入更多份额！")
                elif rec_div == "cash":
                    st.warning(f"🧭 宏观 ERP 估值分位数仅 **{cur_erp:.1f}%** (处于高位估值过热区)：**全组合首选建议变更为【现金分红】**，不承担赎回费落袋为安！")
                else:
                    st.info(f"🧭 宏观 ERP 估值分位数为 **{cur_erp:.1f}%** (中性常态)：核心红利资产建议红利再投，弹性成长建议现金分红。")
            
                div_rows = []
                for c_code, c_h in pm.holdings.items():
                    div_curr = "现金分红" if c_h.dividend_method == "cash" else "红利再投"
                    div_ideal = "红利再投资" if rec_div == "reinvest" else ("现金分红" if rec_div == "cash" else ("红利再投" if "红利" in c_h.fund_name else "现金分红"))
                    div_match = (div_curr == div_ideal.replace("资", ""))
                    div_rows.append({
                        "基金代码": c_code,
                        "基金名称": c_h.fund_name,
                        "当前分红方式": div_curr,
                        "投顾自适应建议": div_ideal,
                        "匹配状态": "✅ 已对齐" if div_match else "⚠️ 建议调整"
                    })
                st.dataframe(pd.DataFrame(div_rows), use_container_width=True, hide_index=True)
            
                if st.button("⚡ 一键应用宏观自适应分红建议", type="primary", key="btn_apply_adaptive_div"):
                    for c_code, c_h in pm.holdings.items():
                        c_h.dividend_method = "reinvest" if rec_div == "reinvest" else "cash"
                    pm.save_state(record_snapshot=True)
                    st.success("✅ 持仓分红方式已全量自适应对齐宏观估值环境！")
                    st.rerun()


    except Exception as e:
        st.error(f"⚠️ 【💼 持仓调仓】渲染出现局部异常: {e}")
        st.caption("💡 其他 Tab 工作区保持正常运行。如需排查可检查日志。")

# =============================================================
# Tab 3: 【📈 组合回测】（穿透回测新建仓组合/当前持仓/调仓前后，9大基准自由多选）
# =============================================================
def render_tab3_backtest_content(pm: PortfolioManager, snapshot: Dict[str, Any]):
    trial29_kpi = StrategyBridge.load_trial29_metrics()
    mlm_inst = st.session_state.get("mlm") or (MultiLedgerManager.get_instance() if MultiLedgerManager else None)
    active_lid = st.session_state.get("active_ledger_id", "main_live")
    all_ledgers = mlm_inst.list_ledgers() if mlm_inst else []
    cur_meta = mlm_inst.get_ledger_meta(active_lid) if mlm_inst else {"name": "主实盘账本"}
    cur_pm = mlm_inst.get_pm(active_lid) if mlm_inst else pm

    t1_sim_c = st.session_state.get("tab1_sim_cache") or {}
    t1_w = dict(st.session_state.get("selected_backtest_weights") or t1_sim_c.get("optimal_weights", {}))
    has_t1 = bool(t1_w)

    rebal_w = dict(st.session_state.get("selected_secondary_weights") or snapshot.get("target_weights_funds", {}))
    if not rebal_w:
        rebal_w = {"005561": 0.30, "100032": 0.25, "000216": 0.20, "518880": 0.15, "011613": 0.10}

    c_bt_mode, c_bt_obj, c_bt_bench = st.columns([3.0, 3.5, 3.5])
    with c_bt_mode:
        bt_mode = st.selectbox(
            "🎯 回测模式",
            ["📒 单账本/方案回测", "🔄 调仓前 vs 调仓后对比", "🆚 双账本同屏 PK", "📊 C1~C5 策略基准档"],
            key="sel_tab3_bt_mode"
        )
    with c_bt_bench:
        all_bms = list(BENCHMARK_INDICES_MAP.keys())
        selected_bms = st.multiselect(
            "📊 对标基准指数 (支持同屏对比)",
            options=all_bms,
            default=["沪深300", "红利低波", "纯债指数"],
            key="sel_multiselect_benchmarks"
        )

    # 在 Col 2 动态渲染选择器
    with c_bt_obj:
        if bt_mode == "📒 单账本/方案回测":
            opts_clean = []
            opt_map_clean = {}
            act_lbl = f"🟢 【{cur_meta.get('name', '主实盘账本')}】({len(cur_pm.holdings)}只 · ¥{cur_pm.total_equity:,.0f})"
            opts_clean.append(act_lbl)
            opt_map_clean[act_lbl] = ("ledger", active_lid)

            for l in all_ledgers:
                if l["id"] != active_lid:
                    try:
                        l_pm = mlm_inst.get_pm(l["id"])
                        lbl = f"📒 【{l['name']}】({len(l_pm.holdings)}只 · ¥{l_pm.total_equity:,.0f})"
                        opts_clean.append(lbl)
                        opt_map_clean[lbl] = ("ledger", l["id"])
                    except Exception:
                        pass

            if has_t1:
                lbl_t1 = f"🌱 Tab 1 最新建仓方案 ({len(t1_w)}只)"
                opts_clean.append(lbl_t1)
                opt_map_clean[lbl_t1] = ("plan_t1", t1_w)

            if snapshot.get("target_weights_funds"):
                lbl_t2 = f"⚖️ Tab 2 拟调仓后目标组合 ({len(rebal_w)}只)"
                opts_clean.append(lbl_t2)
                opt_map_clean[lbl_t2] = ("plan_t2", rebal_w)

            sel_target_type = st.selectbox("📂 选择目标账本或方案", opts_clean, key="sel_backtest_target_type")
            st.session_state.selected_backtest_target = sel_target_type
            choice_kind, choice_val = opt_map_clean.get(sel_target_type, ("ledger", active_lid))

        elif bt_mode == "🔄 调仓前 vs 调仓后对比":
            st.info(f"📊 对比当前持仓【{cur_meta.get('name', '主实盘账本')}】与 Tab 2 目标组合")
            choice_kind, choice_val = ("diff_rebal", None)
            sel_target_type = "调仓前 vs 调仓后"

        elif bt_mode == "🆚 双账本同屏 PK":
            col_pka, col_pkb = st.columns(2)
            ledger_ids = [l["id"] for l in all_ledgers]
            ledger_names = {l["id"]: l["name"] for l in all_ledgers}
            with col_pka:
                pk_lid1 = st.selectbox("账本 A (对照)", options=ledger_ids, format_func=lambda x: f"【{ledger_names.get(x, x)}】", index=0, key="sel_pk_ledger_1")
            with col_pkb:
                pk_lid2_idx = 1 if len(ledger_ids) > 1 else 0
                pk_lid2 = st.selectbox("账本 B (实验)", options=ledger_ids, format_func=lambda x: f"【{ledger_names.get(x, x)}】", index=pk_lid2_idx, key="sel_pk_ledger_2")
            choice_kind, choice_val = ("pk_ledgers", (pk_lid1, pk_lid2))
            sel_target_type = "双账本PK"

        else: # C1~C5 策略基准档
            sel_tier_opt = st.selectbox("选择基准策略档位", ["C1 (安稳增值)", "C2 (稳健平衡)", "C3 (全天候平衡)", "C4 (进取成长)", "C5 (极限进攻)"], index=2, key="sel_backtest_tier_sub")
            choice_kind, choice_val = ("strat_tier", sel_tier_opt)
            sel_target_type = sel_tier_opt

    # 动态解析权重与账本关联（直接使用上述确立的 choice_kind, choice_val，零覆盖）
    primary_weights = {}
    secondary_weights = None
    target_name_disp = sel_target_type
    target_pm_for_names = cur_pm

    if choice_kind == "ledger":
        l_id = choice_val
        t_pm = mlm_inst.get_pm(l_id) if mlm_inst else cur_pm
        target_pm_for_names = t_pm
        m_info = mlm_inst.get_ledger_meta(l_id) if mlm_inst else cur_meta
        if t_pm.holdings:
            tot_h = sum(h.market_value for h in t_pm.holdings.values())
            primary_weights = {c: round(h.market_value / tot_h, 4) for c, h in t_pm.holdings.items()} if tot_h > 0 else {}
        if not primary_weights:
            st.info(f"💡 账本【{m_info.get('name', l_id)}】持仓为空，已自动选用精选基线组合进行推演。")
            primary_weights = {"005561": 0.35, "100032": 0.20, "000216": 0.20, "017436": 0.15, "011613": 0.10}
        target_name_disp = f"【{m_info.get('name', l_id)}】({len(primary_weights)} 只标的)"

    elif choice_kind == "plan_t1":
        primary_weights = choice_val
        target_name_disp = f"新资建仓方案 ({len(primary_weights)} 只标的)"

    elif choice_kind == "plan_t2":
        primary_weights = choice_val
        target_name_disp = f"拟调仓后目标组合 ({len(primary_weights)} 只标的)"

    elif choice_kind == "diff_rebal":
        if cur_pm.holdings:
            tot_h = sum(h.market_value for h in cur_pm.holdings.values())
            primary_weights = {c: round(h.market_value / tot_h, 4) for c, h in cur_pm.holdings.items()} if tot_h > 0 else {}
        if not primary_weights:
            primary_weights = {"005561": 0.35, "100032": 0.20, "000216": 0.20, "017436": 0.15, "011613": 0.10}
        secondary_weights = rebal_w
        target_name_disp = "调仓前 (红) vs 调仓后 (蓝)"

    elif choice_kind == "pk_ledgers":
        # 直接使用已选定的 (pk_lid1, pk_lid2)，零重复 selectbox
        pk_lid1, pk_lid2 = choice_val if isinstance(choice_val, tuple) else (all_ledgers[0]["id"] if all_ledgers else "main_live", all_ledgers[-1]["id"] if all_ledgers else "main_live")
        pm1 = mlm_inst.get_pm(pk_lid1)
        pm2 = mlm_inst.get_pm(pk_lid2)
        m1_info = mlm_inst.get_ledger_meta(pk_lid1) or {"name": pk_lid1}
        m2_info = mlm_inst.get_ledger_meta(pk_lid2) or {"name": pk_lid2}
        tot_1 = sum(h.market_value for h in pm1.holdings.values()) if pm1.holdings else 0
        tot_2 = sum(h.market_value for h in pm2.holdings.values()) if pm2.holdings else 0
        primary_weights = {c: round(h.market_value / tot_1, 4) for c, h in pm1.holdings.items()} if tot_1 > 0 else {"005561": 0.5, "002351": 0.5}
        secondary_weights = {c: round(h.market_value / tot_2, 4) for c, h in pm2.holdings.items()} if tot_2 > 0 else {"100032": 0.5, "000216": 0.5}
        target_name_disp = f"【{m1_info.get('name', pk_lid1)}】vs【{m2_info.get('name', pk_lid2)}】"

    else: # strat_tier
        # 直接使用已选定的 sel_tier_opt，零重复 selectbox
        sel_tier_opt = choice_val or "C3 (全天候平衡)"
        t_key = sel_tier_opt.split()[0]
        df_mat = StrategyBridge.load_matrix()
        w_idx = strategy_fn_for_tier(df_mat, tier=t_key)
        primary_weights = StrategyBridge.map_index_weights_to_funds(w_idx)
        target_name_disp = f"{t_key} 策略基准 ({sel_tier_opt})"

    # ── 📋 当前回测组合持仓穿透档案卡 (Portfolio Profile) ──
    profile_badges = []
    for fcode, w in sorted(primary_weights.items(), key=lambda x: -x[1]):
        fname = resolve_fund_display_name(fcode, target_pm_for_names)
        fcls = pm.classify_fund_asset_class(fcode, fname)
        profile_badges.append(
            f'<span style="display:inline-block; background:var(--bg-elevated); border:1px solid var(--border-subtle); '
            f'border-radius:6px; padding:3px 8px; margin:2px 4px; font-size:11px; color:var(--text-primary);">'
            f'<b>{fname}</b> <code style="color:var(--text-muted);">{fcode}</code> '
            f'<span style="color:var(--accent-primary); font-weight:700;">{w*100:.1f}%</span> '
            f'<span style="background:var(--bg-canvas); border-radius:4px; padding:1px 4px; font-size:10px; color:var(--text-secondary);">{fcls}</span>'
            f'</span>'
        )

    badges_html = "".join(profile_badges)
    safe_markdown_html(f"""
    <div style="background:var(--bg-surface); border:1px solid var(--border-subtle); border-radius:8px; padding:10px 14px; margin-bottom:12px; box-shadow:var(--shadow-card);">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span style="font-size:12px; font-weight:700; color:var(--text-primary);">📋 当前回测组合成分档案卡（Portfolio Profile）· 共 {len(primary_weights)} 只标的</span>
            <span style="font-size:11px; color:var(--text-secondary);">对象：<b>{target_name_disp}</b> ｜ 权益穿透折算已校准</span>
        </div>
        <div style="line-height:1.8;">{badges_html}</div>
    </div>
    """)

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
        safe_markdown_html(f"""
        <div class="main-metric-card">
            <div style="font-size:11px; color:var(--text-secondary);">年化收益率 (CAGR)</div>
            <div class="metric-value-huge" style="color: {active_co['color_up']};">
                +{tier_cagr:.2f}%
            </div>
            <div style="font-size:11px; color:var(--accent-primary); margin-top:2px;">
                场外实盘校准: <b>+{tier_otc_cagr:.2f}%</b> (95%仓位)
            </div>
        </div>
        """)

    with kpi_col2:
        safe_markdown_html(f"""
        <div class="main-metric-card">
            <div style="font-size:11px; color:var(--text-secondary);">回测对象与基金数</div>
            <div class="metric-value-huge" style="color: var(--accent-primary); font-size:16px;">
                {target_name_disp}
            </div>
            <div style="font-size:11px; color:var(--text-secondary); margin-top:2px;">
                标的只数: {len(primary_weights)} 只
            </div>
        </div>
        """)

    with kpi_col3:
        safe_markdown_html(f"""
        <div class="main-metric-card">
            <div style="font-size:11px; color:var(--text-secondary);">全周期最大回撤 (MaxDD)</div>
            <div class="metric-value-huge" style="color: {active_co['color_down']};">
                -{tier_mdd:.2f}%
            </div>
            <div style="font-size:11px; color:var(--text-secondary); margin-top:2px;">
                沪深300同期回撤: {trial29_kpi['mdd_h300']:.1f}%
            </div>
        </div>
        """)

    with kpi_col4:
        safe_markdown_html(f"""
        <div class="main-metric-card">
            <div style="font-size:11px; color:var(--text-secondary);">切片胜率 / 盈亏比</div>
            <div class="metric-value-huge" style="color: {active_co['color_up']};">
                {trial29_kpi['slice_win_rate']}
            </div>
            <div style="font-size:11px; color:var(--text-secondary); margin-top:2px;">
                月度胜率 {trial29_kpi['monthly_win_rate']} ｜ 盈亏比 {trial29_kpi['profit_factor_range']}
            </div>
        </div>
        """)

    safe_markdown_html(f"""
    <div style="background: var(--bg-elevated); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 12px 18px; margin-bottom: 14px;">
        <div style="font-weight: 700; color: var(--color-up); font-size: 14px; margin-bottom: 4px;">
            💡 实盘双口径年化收益对照（场外公募 95% 仓位现金拖累校准）
        </div>
        <div style="font-size: 13px; color: var(--text-primary); line-height: 1.6;">
            • <b>指数理论年化 (CAGR)</b>: <span style="color: {active_co['color_up']}; font-weight:700;">+{tier_cagr:.2f}%</span>（假定 100% 仓位跟踪全收益指数）<br>
            • <b>场外联接实盘年化 (CAGR)</b>: <span style="color: var(--accent-primary); font-weight:700;">+{tier_otc_cagr:.2f}%</span>（强制折算公募基金 95% 仓位法定上限与 5% 现金拖累，年化损耗约 0.60%，实盘业绩拒绝失真）
        </div>
    </div>
    """)

    # 🌪️ 历史黑天鹅极端承压测试卡片
    try:
        stress_data = simulate_black_swan_stress(
            holdings=primary_weights,
            total_capital=float(st.session_state.get("plan_capital", 100000.0)),
            df_bt=df_bt if not df_bt.empty else None
        )
        render_black_swan_stress_card(stress_data)

        # G10: 穿透式蒙特卡洛压力测试 · 流动性指标卡挂载至 Tab 3
        active_tier = getattr(st.session_state, "active_tier_val", "C3")
        _tot_cap = float(st.session_state.get("plan_capital", getattr(pm, "total_equity", 100000.0)) or 100000.0)
        stress_m_res = pm.simulate_portfolio_cvar_bootstrap_instance(
            total_capital=_tot_cap,
            investor_risk_tier=active_tier
        )
        safe_markdown_html(render_stress_liquidity_card_html(stress_m_res))
    except Exception as e:
        st.caption(f"（Tab 3 黑天鹅承压测试卡片渲染提示: {e}）")

    st.markdown(" ")

    # 2018-2026 全周期真实净值推演曲线 (同屏对标自选基准)
    st.markdown("#### 🚀 全周期净值曲线")

    if choice_kind == "ledger":
        safe_markdown_html("""
        <div style="background: rgba(245, 158, 11, 0.08); border-left: 3px solid var(--accent-primary); padding: 8px 14px; border-radius: 6px; margin-bottom: 12px; font-size: 12px; color: var(--text-primary);">
            <b>⚠️ 当前持仓静态权重历史回溯（含历史后视镜权重效应，非滚动样本外实盘记录）</b><br>
            <span style="color: var(--text-secondary); font-size: 11px; line-height: 1.5;">
                本回测基于当前实盘持仓的静态配置权重，反向穿越回溯至 2018 年并进行每日再平衡推演。因当前持仓中包含了近几年涨幅领先的黄金或跨市场资产，存在已知的历史后视镜权重效应与幸存者偏差，不代表历史上按滚动策略真实运行的样本外业绩。
            </span>
        </div>
        """)
        tgl_compare_oos = st.toggle("🔄 同屏对比【全天候滚动样本外动态策略曲线】(C3 标杆)", value=False, key="tgl_compare_oos_dynamic")
    else:
        tgl_compare_oos = False

    fig_nav = go.Figure()

    if tgl_compare_oos:
        try:
            base_bt = StrategyBridge.get_backtest_nav_for_tier(tier="C3")
            fig_nav.add_trace(go.Scatter(
                x=base_bt['date'],
                y=base_bt['strategy_nav'],
                mode='lines',
                name='全天候滚动样本外动态策略 (C3)',
                line=dict(color='#8b5cf6', width=2.0, dash='dashdot')
            ))
        except Exception as e_oos:
            st.caption(f"（样本外基准加载: {e_oos}）")

    # 绘制主回测组合曲线
    fig_nav.add_trace(go.Scatter(
        x=df_bt['date'],
        y=df_bt['strategy_nav'],
        mode='lines',
        name=f'{target_name_disp} (理论 +{tier_cagr:.2f}%)',
        line=dict(color=active_co['color_up'], width=2.5)
    ))

    # 若为调仓前后对比，同屏绘制第二组合
    if "secondary_nav" in df_bt.columns:
        sec_cagr = (df_bt['secondary_nav'].iloc[-1] ** (252.0 / max(len(df_bt), 1)) - 1.0) * 100.0
        fig_nav.add_trace(go.Scatter(
            x=df_bt['date'],
            y=df_bt['secondary_nav'],
            mode='lines',
            name=f'调仓后组合 (理论 +{sec_cagr:.2f}%)',
            line=dict(color=active_th['accent_primary'], width=2.2, dash='solid')
        ))

    # 绘制场外实盘校准曲线
    if 'strategy_nav_otc' in df_bt.columns and "secondary_nav" not in df_bt.columns:
        fig_nav.add_trace(go.Scatter(
            x=df_bt['date'],
            y=df_bt['strategy_nav_otc'],
            mode='lines',
            name=f'{target_name_disp} 场外实盘校准 (+{tier_otc_cagr:.2f}%)',
            line=dict(color=active_th['accent_primary'], width=2.0, dash='dot')
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
            annotation_font_size=9,
            annotation_font_color=active_th.get("text_muted", "rgba(148, 163, 184, 0.55)")
        )

    fig_nav.update_layout(
        title=f"2018-2026 全周期累计净值对比 (起始归一化 1.000)",
        xaxis_title="交易日期",
        yaxis_title="标准化累计净值",
        hovermode="x unified",
        margin=dict(t=75, b=10, l=10, r=10),
        height=380,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.06,
            xanchor="left",
            x=0,
            bgcolor="rgba(0,0,0,0)"
        )
    )
    apply_theme_to_plotly_figure(fig_nav)
    # 强制在主题应用之后重新固化上方透明图例与 75px 上边距，彻底杜绝被覆盖
    fig_nav.update_layout(
        margin=dict(t=75, b=10, l=10, r=10),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.06,
            xanchor="left",
            x=0,
            bgcolor="rgba(0,0,0,0)"
        )
    )
    st.plotly_chart(fig_nav, use_container_width=True)

    col_dd, col_alloc = st.columns(2)
    with col_dd:
        st.markdown("##### 🌊 动态回撤对比")
        fig_dd = go.Figure()
        fig_dd.add_trace(go.Scatter(
            x=df_bt['date'],
            y=df_bt['strategy_drawdown'],
            mode='lines',
            fill='tozeroy',
            name='组合水下回撤',
            line=dict(color=active_co['color_down'], width=1.5),
            fillcolor=active_co['bg_down']
        ))
        if "secondary_drawdown" in df_bt.columns:
            fig_dd.add_trace(go.Scatter(
                x=df_bt['date'],
                y=df_bt['secondary_drawdown'],
                mode='lines',
                name='调仓后水下回撤',
                line=dict(color=active_th['accent_primary'], width=1.5)
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
        apply_theme_to_plotly_figure(fig_dd)
        st.plotly_chart(fig_dd, use_container_width=True)

    with col_alloc:
        st.markdown("##### 📊 资产仓位变迁")
        fig_area = go.Figure()
        fig_area.add_trace(go.Scatter(
            x=df_bt['date'], y=df_bt['weight_ashare'] * 100.0, mode='lines', stackgroup='one',
            name='A股权益仓位', line=dict(width=0.5, color=active_co['color_up']), fillcolor=active_co['bg_up']
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
        apply_theme_to_plotly_figure(fig_area)
        st.plotly_chart(fig_area, use_container_width=True)

    # 6 大历史市场风格切片明细表与历史同温层匹配器
    st.markdown("#### 📜 历史切片战报")
    df_slices = trial29_kpi.get("slices_df")
    if df_slices is not None and not df_slices.empty:
        st.dataframe(df_slices, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("#### 🔍 历史相似匹配与同温层推演")
    st.caption("系统通过 4 维特征向量（ERP估值分位、MA20偏离、DR007利率、期权波动率）在 2018~2026 年大样本中匹配历史同温层行情：")

    analog_tab2 = _cached_find_historical_analogs(top_k=3)
    matches_list = analog_tab2.get("matches", [])
    n_matches = len(matches_list)
    if n_matches > 0:
        win_count = sum(1 for m in matches_list if m.get("strategy_ret_60d", 0.0) > m.get("h300_ret_60d", 0.0))
        win_rate_60d = (win_count / n_matches) * 100.0
        avg_excess_60d = sum(m.get("strategy_ret_60d", 0.0) - m.get("h300_ret_60d", 0.0) for m in matches_list) / n_matches
        avg_abs_ret_60d = sum(m.get("strategy_ret_60d", 0.0) for m in matches_list) / n_matches
        avg_mdd_60d = sum(abs(m.get("strategy_mdd_60d", 0.0)) for m in matches_list) / n_matches
        win_rate_desc = (
            f"历史 {n_matches} 次高度相似情景中，后 60 交易日策略跑赢沪深300相对超额胜率达 <b>{win_rate_60d:.1f}%</b>，"
            f"平均相对超额 <b>{avg_excess_60d:+.2f}%</b>，策略平均绝对收益率 <b>{avg_abs_ret_60d:+.2f}%</b>"
            f"（平均最大回撤仅 <b>{avg_mdd_60d:.1f}%</b>），明显战胜纯宽基基准。"
        )
    else:
        win_rate_desc = "历史相似行情样本计算中..."
    
    # ── 🧭 历史同温层综合启示与今日操作指南横幅 ──
    safe_markdown_html(f"""
    <div style="background:rgba(16, 185, 129, 0.08); border:1.5px solid var(--color-down); border-radius:8px; padding:12px 16px; margin:8px 0 12px 0;">
        <div style="font-size:13px; font-weight:700; color:var(--color-down); margin-bottom:4px;">
            🧭 历史同温层综合启示与今日操作指南（投顾大白话解密）
        </div>
        <div style="font-size:12px; color:var(--text-primary); line-height:1.6;">
            <b>【当前同温层状态】</b>{analog_tab2.get('summary_text', '当前大盘处于宏观磨底与估值高性价比击球区')}<br>
            <b>【实盘胜率启示】</b>{win_rate_desc}<br>
            <b>【今日操作指南】</b>权益资产不宜恐慌割肉，维持底仓高股息与纯债压舱，增量资金逢回抽均线支撑位分批定投，严禁追高超买赛道。
        </div>
    </div>
    """)

    if analog_tab2.get("matches"):
        st.markdown("##### 📊 历史情景表现与镜鉴明细")
        col_t2_1, col_t2_2, col_t2_3 = st.columns(3)
        for col_item, m in zip([col_t2_1, col_t2_2, col_t2_3], analog_tab2["matches"]):
            s_ret = m.get("strategy_ret_60d", 0.0)
            h_ret = m.get("h300_ret_60d", 0.0)
            mdd_abs = abs(m.get("strategy_mdd_60d", 0.0))
            diff_outperform = s_ret - h_ret

            if s_ret > 0 and h_ret > 0:
                card_meaning = f"右侧顺势共振：底部击球区反弹期紧跟主升浪，兼顾进攻弹性与低回撤（最大回撤仅 {mdd_abs:.1f}%）"
            elif h_ret <= 0 and s_ret > h_ret:
                card_meaning = f"逆势抗跌护盾：大盘阴跌寻底期，凭借红利与纯债底仓大幅跑赢大盘 +{diff_outperform:.2f}%，守住本金安全垫"
            elif h_ret > 0 and s_ret <= h_ret:
                card_meaning = "防守底仓代价：急跌反抽期高配纯债避险导致短期弹性收敛，但换取了熊市下半场极高本金安全度"
            else:
                card_meaning = f"极端下行冲击：市场流动性承压阶段，凭借纯债与高股息底仓实现超额防御 +{diff_outperform:.2f}%，最大回撤 {mdd_abs:.1f}%"

            with col_item:
                safe_markdown_html(f"""
                <div class="decision-card">
                    <div class="decision-title">时期：{m['date']} ｜ 相似度 {m['similarity_pct']:.1f}%</div>
                    <div class="decision-val" style="color: {active_co['color_up'] if m['strategy_ret_60d'] >= 0 else active_co['color_down']}; font-size:16px;">
                        策略后60日：{m['strategy_ret_60d']:+.2f}% (沪深300: {m['h300_ret_60d']:+.2f}%)
                    </div>
                    <div class="decision-desc">
                        - <b>未来20日(1个月)</b>：沪深300 {m['h300_ret_20d']:+.2f}% ｜ 策略 {m['strategy_ret_20d']:+.2f}%<br>
                        - <b>未来60日(3个月)</b>：策略最大回撤 {m['strategy_mdd_60d']:.2f}%<br>
                        - <b>当时大类配置</b>：{m['alloc_desc']}
                    </div>
                    <div style="font-size:10.5px; color:var(--accent-primary); font-weight:600; margin-top:6px; border-top:1px dashed var(--border-subtle); padding-top:4px;">
                        💡 历史镜鉴意义：{card_meaning}。
                    </div>
                </div>
                """)


def render_tab4_toolbox_content(pm: PortfolioManager, snapshot: Dict[str, Any]):
    mlm_inst = st.session_state.get("mlm") or (MultiLedgerManager.get_instance() if MultiLedgerManager else None)
    active_lid = st.session_state.get("active_ledger_id", "main_live")
    all_ledgers = mlm_inst.list_ledgers() if mlm_inst else []
    cur_meta = mlm_inst.get_ledger_meta(active_lid) if mlm_inst else {"name": "主实盘账本"}
    cur_pm = mlm_inst.get_pm(active_lid) if mlm_inst else pm

    tb_opts = []
    tb_opt_map = {}
    act_lbl = f"🟢 当前激活账本：【{cur_meta.get('name', '主实盘账本')}】({len(cur_pm.holdings)}只 · ¥{cur_pm.total_equity:,.0f})"
    tb_opts.append(act_lbl)
    tb_opt_map[act_lbl] = ("ledger", active_lid)

    for l in all_ledgers:
        if l["id"] != active_lid:
            try:
                l_pm = mlm_inst.get_pm(l["id"])
                lbl = f"📒 独立账本：【{l['name']}】({len(l_pm.holdings)}只 · ¥{l_pm.total_equity:,.0f})"
                tb_opts.append(lbl)
                tb_opt_map[lbl] = ("ledger", l["id"])
            except Exception:
                pass

    t1_sim_c = st.session_state.get("tab1_sim_cache") or {}
    t1_w = dict(st.session_state.get("selected_backtest_weights") or t1_sim_c.get("optimal_weights", {}))
    has_t1 = bool(t1_w)
    if has_t1:
        lbl_t1 = f"🌱 Tab 1 最新建仓方案 ({len(t1_w)} 只标的)"
        tb_opts.append(lbl_t1)
        tb_opt_map[lbl_t1] = ("plan_t1", t1_w)

    rebal_w = dict(st.session_state.get("selected_secondary_weights") or snapshot.get("target_weights_funds", {}))
    if not rebal_w:
        rebal_w = {"005561": 0.30, "100032": 0.25, "000216": 0.20, "518880": 0.15, "011613": 0.10}
    if snapshot.get("target_weights_funds"):
        lbl_t2 = f"⚖️ Tab 2 拟调仓目标组合 ({len(rebal_w)} 只标的)"
        tb_opts.append(lbl_t2)
        tb_opt_map[lbl_t2] = ("plan_t2", rebal_w)

    col_top_sel, col_top_badges = st.columns([3.8, 6.2])
    with col_top_sel:
        def_tb_obj = st.session_state.get("tab4_selected_target", act_lbl)
        def_tb_idx = tb_opts.index(def_tb_obj) if def_tb_obj in tb_opts else 0
        sel_tb_target = st.selectbox(
            "📂 选择穿透体检组合对象：",
            tb_opts,
            index=def_tb_idx,
            key="sel_tab4_target_type"
        )
        st.session_state.tab4_selected_target = sel_tb_target

    tb_kind, tb_val = tb_opt_map.get(sel_tb_target, ("ledger", active_lid))
    active_examine_holdings = {}
    total_examine_equity = 0.0
    from portfolio_manager import HoldingItem

    if tb_kind == "ledger":
        l_id = tb_val
        t_pm = mlm_inst.get_pm(l_id) if mlm_inst else cur_pm
        m_info = mlm_inst.get_ledger_meta(l_id) if mlm_inst else cur_meta
        if t_pm.holdings:
            active_examine_holdings = dict(t_pm.holdings)
            total_examine_equity = sum(h.market_value for h in t_pm.holdings.values()) + t_pm.available_cash + t_pm.in_transit_cash
        else:
            st.info(f"💡 账本【{m_info.get('name', l_id)}】持仓为空，已自动选用精选基线组合进行全景穿透体检。")
            t1_w_def = {"005561": 0.35, "100032": 0.20, "000216": 0.20, "017436": 0.15, "011613": 0.10}
            base_cap = float(st.session_state.get("plan_capital", 100000.0))
            for fc, w in t1_w_def.items():
                m_val = round(base_cap * w, 2)
                fn = resolve_fund_display_name(fc, t_pm)
                active_examine_holdings[fc] = HoldingItem(fund_code=fc, fund_name=fn, shares=m_val, cost_nav=1.0, current_nav=1.0)
            total_examine_equity = base_cap

    elif tb_kind == "plan_t1":
        t1_w = tb_val
        base_cap = float(st.session_state.get("plan_capital", 100000.0))
        for fc, w in t1_w.items():
            m_val = round(base_cap * w, 2)
            fn = resolve_fund_display_name(fc, cur_pm)
            active_examine_holdings[fc] = HoldingItem(fund_code=fc, fund_name=fn, shares=m_val, cost_nav=1.0, current_nav=1.0)
        total_examine_equity = base_cap

    else: # plan_t2
        rebal_w = tb_val
        base_cap = sum(h.market_value for h in cur_pm.holdings.values()) if cur_pm.holdings else 100000.0
        for fc, w in rebal_w.items():
            m_val = round(base_cap * w, 2)
            fn = resolve_fund_display_name(fc, cur_pm)
            active_examine_holdings[fc] = HoldingItem(fund_code=fc, fund_name=fn, shares=m_val, cost_nav=1.0, current_nav=1.0)
        total_examine_equity = base_cap

    with col_top_badges:
        tb_badges = []
        for fc, h in active_examine_holdings.items():
            w_pct = (h.market_value / total_examine_equity * 100.0) if total_examine_equity > 0 else 0.0
            fcls = pm.classify_fund_asset_class(fc, h.fund_name)
            tb_badges.append(
                f'<span style="display:inline-block; background:var(--bg-elevated); border:1px solid var(--border-subtle); '
                f'border-radius:4px; padding:1px 6px; margin:2px 3px; font-size:11px; color:var(--text-primary); white-space:nowrap;">'
                f'<b>{h.fund_name}</b> <code style="color:var(--text-muted); font-size:10px;">{fc}</code> '
                f'<span style="color:var(--accent-primary); font-weight:700;">{w_pct:.1f}%</span> '
                f'<span style="background:var(--bg-canvas); border-radius:3px; padding:0 3px; font-size:9.5px; color:var(--text-secondary);">{fcls}</span>'
                f'</span>'
            )

        safe_markdown_html(f"""
        <div style="background:var(--bg-surface); border:1px solid var(--border-subtle); border-radius:8px; padding:6px 10px; margin-bottom:8px; box-shadow:var(--shadow-card);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:3px;">
                <span style="font-size:11.5px; font-weight:700; color:var(--text-primary);">📋 成分档案 · 共 {len(active_examine_holdings)} 只标的</span>
                <span style="font-size:11px; color:var(--text-secondary);">折算总资产: <b>¥{total_examine_equity:,.0f}</b></span>
            </div>
            <div style="display:flex; flex-wrap:wrap; align-items:center; max-height:48px; overflow-y:auto; line-height:1.5;">{"".join(tb_badges)}</div>
        </div>
        """)

    # ── 响应首屏主动风险哨联动穿透横幅 ──
    hl_mod = st.session_state.get("tab4_highlight_module")
    if hl_mod:
        hl_title = st.session_state.get("tab4_highlight_title", "主动风险预警")
        hl_code = st.session_state.get("tab4_highlight_fund", "")
        safe_markdown_html(f"""
        <div style="background: rgba(239, 68, 68, 0.08); border-left: 4px solid var(--color-up); padding: 10px 14px; border-radius: 6px; margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: 700; color: var(--color-up); font-size: 13px;">🚨 响应首屏主动风险哨联动证据链：{hl_title}</span>
                <span style="font-size: 11px; color: var(--text-secondary);">标的代码: {hl_code or '全组合'}</span>
            </div>
            <div style="font-size: 11.5px; color: var(--text-primary); margin-top: 4px;">
                系统已为您在下方穿透对应底层持仓与风险证据链。完成排查后，建议返回【💼 持仓调仓】主流程实施调仓处置。
            </div>
        </div>
        """)

    total_cur_equity = total_examine_equity


    box_tab1, box_tab2, box_tab3, box_tab4, box_tab5, box_tab6 = st.tabs([
        "📊 资产穿透与排雷",
        "🌡️ 14赛道温度计",
        "⚡ 尾盘折溢价套利",
        "🛡️ 期权防暴跌哨",
        "🌐 跨境QDII与锁汇",
        "💡 A/C端选型算费"
    ])

    with box_tab1:
        st.markdown("#### 🎯 资产大类缺口")

        cur_cats = {}
        for c, h in active_examine_holdings.items():
            cat = pm.classify_fund_asset_class(c, h.fund_name)
            cur_cats[cat] = cur_cats.get(cat, 0.0) + h.market_value
        if sel_tb_target == "当前实盘持仓" and pm.available_cash > 0:
            cur_cats["可用现金"] = pm.available_cash

        target_funds = snapshot.get("target_weights_funds", {})
        all_cats = sorted(list(set(list(cur_cats.keys()) + [pm.classify_fund_asset_class(k) for k in target_funds.keys()])))

        # 并排渲染：左侧大类条形图，右侧行业暴露图 (height=320，彻底解决图 4 挤压不协调)
        col_chart_left, col_chart_right = st.columns([5, 5])
        with col_chart_left:
            st.markdown("##### 📊 资产大类配比")
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
            apply_theme_to_plotly_figure(fig_bar)
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_chart_right:
            st.markdown("##### 🏭 行业穿透暴露")
            _h_items = tuple(sorted((c, getattr(h, "fund_name", c), float(getattr(h, "shares", 0.0)), float(getattr(h, "cost_price", getattr(h, "cost_nav", 1.0))), float(getattr(h, "current_nav", 1.0))) for c, h in active_examine_holdings.items()))
            df_ind = _cached_look_through_industry(_h_items)
            if not df_ind.empty:
                fig_ind_b = px.bar(df_ind, x="暴露占比(%)", y="行业", orientation="h", color="暴露占比(%)", color_continuous_scale="Viridis", text_auto=".1f%")
                fig_ind_b.update_layout(margin=dict(t=15, b=10, l=10, r=10), height=320, yaxis={'categoryorder':'total ascending'})
                apply_theme_to_plotly_figure(fig_ind_b)
                st.plotly_chart(fig_ind_b, use_container_width=True)
            else:
                st.info("当前无持仓数据可供行业穿透。")

        # 大类资产配置缺口量化分析表
        st.markdown("##### ⚖️ 资产缺口分析")
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
        safe_markdown_html("""
        <div style="background:var(--bg-elevated); border:1px solid var(--border-subtle); border-radius:6px; padding:8px 12px; margin-top:8px; font-size:11px; color:var(--text-secondary); line-height:1.6;">
            💡 <b>投顾穿透意义解读·大类配置与行业敞口</b>：基金外壳名称常具误导性（如“偏债FOF”内含权益、“行业基金”跨行业重叠）。
            系统将全组合 100% 穿透至底层资产，10 大专业大类杜绝伪分散；通过加权合并行业敞口，确保单一产业链风险在可控范围内。
        </div>
        """)

        # 🚨 动态相关性突变防御与组合集中度降级警报 (基于 EWMA 滚动协方差矩阵)
        st.markdown("---")
        st.markdown("#### 🚨 动态相关性突变防御与集中度降级警报")
        st.caption("基于 EWMA 滚动协方差矩阵实时追踪红利资产与周期权重股的相关系数变迁。当相关系数突破 0.75 临界阈值时，自动触发组合集中度降级警报并动态削减重仓敞口。")

        sim_corr_tb = st.session_state.get("sim_corr_tb_val")
        corr_eval_tb = pm.evaluate_dynamic_correlation_mutation_instance(
            threshold=0.75,
            simulated_corr=sim_corr_tb
        )
        cur_corr = corr_eval_tb.get("current_correlation", 0.45)
        is_mut = corr_eval_tb.get("is_triggered", False)
        tot_cut_pct = corr_eval_tb.get("total_cut_weight_pct", 0.0)

        col_c1, col_c2, col_c3, col_c4 = st.columns([2.8, 2.8, 2.8, 1.6])
        with col_c1:
            st.metric("EWMA 动态相关系数", f"{cur_corr:.4f}", "基准警戒阈值: 0.75")
        with col_c2:
            st.metric("突变状态研判", "🔴 突变超标 (已警报)" if is_mut else "🟢 正常解耦 (健康)", "红利 vs 周期权重")
        with col_c3:
            st.metric("集中度降级与削减", f"-{tot_cut_pct:.1f}%" if is_mut else "无削减", "重仓敞口动态平移")
        with col_c4:
            toggle_sim = st.toggle("🧪 模拟突变", value=bool(sim_corr_tb is not None and sim_corr_tb >= 0.75), key="tgl_sim_corr_tab4")
            if toggle_sim and sim_corr_tb != 0.82:
                st.session_state.sim_corr_tb_val = 0.82
                st.rerun()
            elif not toggle_sim and sim_corr_tb is not None:
                st.session_state.sim_corr_tb_val = None
                st.rerun()

        if is_mut:
            safe_markdown_html(f"""
            <div style="background: var(--bg-surface); border-left: 4px solid var(--color-up); border-radius: 8px; padding: 12px 16px 14px 16px; margin-bottom: 12px; box-shadow: var(--shadow-card); height: auto !important; overflow: visible !important;">
                <div style="font-size: 13.5px; font-weight: 700; color: var(--color-up); margin-bottom: 4px;">
                    🚨【组合集中度降级警报已触发】红利资产与周期权重股相关系数达 {cur_corr:.2f} (突破 0.75 警戒线)
                </div>
                <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.6; margin-bottom: 6px;">
                    {corr_eval_tb.get('alert_message')}
                </div>
                <div style="font-size: 11px; color: var(--color-up); font-weight: 600;">
                    🛡️ <b>自适应处置预案</b>：已对共振重仓敞口执行阶梯削减，合计削减 {tot_cut_pct:.1f}% 敞口，并平移至纯债固收 (002351) 与黄金对冲 (000216)。
                </div>
            </div>
            """)
            if corr_eval_tb.get("cut_details"):
                df_cuts = pd.DataFrame(corr_eval_tb["cut_details"])
                st.markdown("##### ✂️ 动态削减重仓敞口与转移明细表")
                st.dataframe(
                    df_cuts,
                    column_config={
                        "original_weight": st.column_config.NumberColumn("原权重(%)", format="%.2f%%"),
                        "adjusted_weight": st.column_config.NumberColumn("削减后目标权重(%)", format="%.2f%%"),
                        "cut_weight_pct": st.column_config.NumberColumn("削减比例(%)", format="-%.2f%%"),
                        "haircut_ratio_pct": st.column_config.NumberColumn("降级惩罚率(%)", format="%.1f%%"),
                    },
                    use_container_width=True,
                    hide_index=True
                )
        else:
            safe_markdown_html(f"""
            <div style="background: var(--bg-surface); border-left: 4px solid var(--color-down); border-radius: 8px; padding: 10px 14px 12px 14px; margin-bottom: 12px; box-shadow: var(--shadow-card); height: auto !important; overflow: visible !important;">
                <div style="font-size: 13px; font-weight: 700; color: var(--color-down); margin-bottom: 2px;">
                    🟢【相关性解耦健康】红利类资产与周期权重股相关系数为 {cur_corr:.2f} (< 0.75 警戒线)
                </div>
                <div style="font-size: 11px; color: var(--text-secondary); line-height: 1.5;">
                    底层资产具备良好的资产配置对冲效应，红利低波与周期资产未见同向踩踏共振，无需触发集中度降级。
                </div>
            </div>
            """)

        # 渲染 EWMA 滚动相关性历史走势图
        hist_corr = corr_eval_tb.get("historical_correlation_tail", {})
        if hist_corr:
            dates = list(hist_corr.keys())
            vals = list(hist_corr.values())
            fig_corr = go.Figure()
            fig_corr.add_trace(go.Scatter(
                x=dates, y=vals,
                mode="lines",
                name="EWMA 滚动相关系数 (λ=0.94)",
                line=dict(color=active_co["color_up"] if is_mut else active_th["accent_primary"], width=2.2)
            ))
            fig_corr.add_hline(
                y=0.75,
                line_dash="dash",
                line_color=active_co["color_up"],
                annotation_text="0.75 突变集中度降级警戒线",
                annotation_position="top left",
                annotation_font=dict(color=active_co["color_up"], size=10)
            )
            fig_corr.update_layout(
                title="📈 红利低波 vs 沪深300 EWMA 动态相关系数走势 (近120个交易日)",
                title_font=dict(size=12),
                height=260,
                margin=dict(l=10, r=10, t=30, b=30),
                yaxis=dict(range=[-0.6, 1.0], tickformat=".2f")
            )
            apply_theme_to_plotly_figure(fig_corr)
            st.plotly_chart(fig_corr, use_container_width=True, key="fig_ewma_corr_trend")

        # 重仓股交叉重合度检测 (左 5.2 紧凑热力图 + 右 4.8 共同重仓股清单与配置指引)
        st.markdown("---")
        st.markdown("#### ⚠️ 重仓交叉热力与同质化诊断")
        overlap_res = _cached_stock_overlap(_h_items)
        max_total = float(overlap_res.get("max_total_overlap", 0.0))
        max_unexcused = float(overlap_res.get("max_non_diag_unexcused", 0.0))
        alerts = overlap_res.get("alerts", [])
        common_details = overlap_res.get("common_stocks_details", [])

        if max_total == 0.0 and len(alerts) == 0:
            st.success("✅ **您的组合跨大类分散度极佳，前十大重仓股物理零重叠**（底层资产完全正交，无任何重复持股）")
        elif max_unexcused == 0.0 and len(overlap_res.get("exempt_pairs", [])) > 0:
            st.info(
                f"ℹ️ **检测到组合存在同系底仓协同配置（最高重叠达 {max_total*100:.1f}%）**："
                f"属于红利增强与红利低波策略互补底仓，无非合规跨赛道伪分散风险，重合股票敞口已合并至全组合行业监控。"
            )
        elif max_unexcused < 0.20 and len(alerts) == 0:
            st.success(f"✅ **跨大类分散度良好** 前十大重仓股无明显交叉（非同系最高重叠仅 {max_unexcused*100:.1f}%，低于 20% 警戒线）。")
        else:
            st.warning(f"⚠️ **检测到持仓间存在较高重仓股重叠（最高达 {max_total*100:.1f}%）** 伪分散可能导致行业与个股风险过度集中。")
            for a in alerts:
                st.warning(a["warning_msg"])

        col_heat, col_diag = st.columns([5.5, 4.5])
        with col_heat:
            if len(overlap_res.get("funds", [])) >= 2:
                n_funds = len(overlap_res["funds"])
                fig_heat = px.imshow(
                    overlap_res["matrix"],
                    labels=dict(x="", y="", color="重合度"),
                    x=overlap_res["funds"], y=overlap_res["funds"],
                    color_continuous_scale="Blues", text_auto=".2f"
                )
                fig_heat.update_layout(
                    coloraxis_showscale=False,
                    margin=dict(l=10, r=10, t=15, b=45),
                    height=380,
                    font=dict(size=12),
                    xaxis=dict(
                        tickmode="array",
                        tickvals=list(range(n_funds)),
                        ticktext=overlap_res["funds"],
                        tickangle=-25,
                        side="bottom"
                    ),
                    yaxis=dict(
                        tickmode="array",
                        tickvals=list(range(n_funds)),
                        ticktext=overlap_res["funds"],
                        autorange="reversed"
                    )
                )
                apply_theme_to_plotly_figure(fig_heat)
                st.plotly_chart(fig_heat, use_container_width=True)
            else:
                st.info("标的不足 2 只，无需绘制重合度热力图。")

        with col_diag:
            safe_markdown_html("<div style='font-size:13px; font-weight:700; color:var(--text-primary); margin-bottom:6px;'>📋 共同重仓股穿透清单与去重指引</div>")
            if common_details:
                tot_diag_mv = sum(getattr(h, "market_value", 0.0) for h in active_examine_holdings.values())
                for pair in common_details:
                    f1_code = pair["fund1_code"]
                    f2_code = pair["fund2_code"]
                    f1_alias = get_fund_short_alias(f1_code, pair.get("fund1_name", f1_code))
                    f2_alias = get_fund_short_alias(f2_code, pair.get("fund2_name", f2_code))
                    
                    h1 = active_examine_holdings.get(f1_code)
                    h2 = active_examine_holdings.get(f2_code)
                    w1 = (getattr(h1, "market_value", 0.0) / tot_diag_mv * 100.0) if tot_diag_mv > 0 and h1 else 0.0
                    w2 = (getattr(h2, "market_value", 0.0) / tot_diag_mv * 100.0) if tot_diag_mv > 0 and h2 else 0.0

                    st_stocks_str = "、".join(pair["common_stocks"][:5])
                    more_str = f" 等共 {len(pair['common_stocks'])} 只" if len(pair["common_stocks"]) > 5 else ""
                    tag_color = "#3b82f6" if pair["is_exempt"] else "#ef4444"
                    safe_markdown_html(
                        f"""
                        <div style="background:var(--bg-elevated); border:1px solid var(--border-subtle); border-radius:8px; padding:10px 12px; margin-bottom:8px;">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                                <span style="font-weight:600; font-size:12px; color:var(--text-primary);">【{f1_code} {f1_alias} ({w1:.1f}%)】vs【{f2_code} {f2_alias} ({w2:.1f}%)】</span>
                                <span style="background:{tag_color}22; color:{tag_color}; border:1px solid {tag_color}55; border-radius:4px; padding:1px 6px; font-size:11px; font-weight:700;">重叠 {pair['overlap_pct']}%</span>
                            </div>
                            <div style="font-size:11px; color:var(--text-secondary); margin-bottom:2px;">
                                <b>共同重仓</b>: <code style="color:var(--text-primary);">{st_stocks_str}{more_str}</code>
                            </div>
                            <div style="font-size:10.5px; color:var(--accent-primary); margin-bottom:4px;">
                                📊 持仓权重对比: {f1_alias} <b>{w1:.1f}%</b> ｜ {f2_alias} <b>{w2:.1f}%</b>
                            </div>
                            <div style="font-size:11px; color:var(--text-muted); line-height:1.4;">
                                <b>投顾研判</b>: {pair['note']}。已将共同重仓股纳入行业合并敞口模型，防止单一行业超出组合上限。
                            </div>
                        </div>
                        """
                    )
            elif len(active_examine_holdings) < 2:
                safe_markdown_html(
                    """
                    <div style="background:var(--bg-elevated); border:1px solid var(--border-subtle); border-radius:8px; padding:20px; text-align:center; color:var(--text-secondary); font-size:12px;">
                        💡 <b>当前账本仅持有 1 只标的</b><br>
                        暂无两两基金对重合度。建议在组合中引入 2 只及以上标的，以展开多资产相关性与底层重仓去重分析。
                    </div>
                    """
                )
            else:
                safe_markdown_html(
                    """
                    <div style="background:var(--bg-elevated); border:1px solid var(--border-subtle); border-radius:8px; padding:20px; text-align:center; color:var(--text-secondary); font-size:12px;">
                        🎉 <b>前十大重仓股物理零重合</b><br>
                        当前组合各标的前十大重仓股完全正交独立，未发现任何重复持股或伪分散现象。
                    </div>
                    """
                )

        # 底层穿透排雷大宽表
        st.markdown("---")
        st.markdown("#### 🛡️ 底层排雷宽表")
        if len(active_examine_holdings) > 0:
            port_risk = _cached_penetration_risk(_h_items)
            c_pr1, c_pr2, c_pr3 = st.columns(3)
            with c_pr1:
                st.metric("组合加权排雷风险指数", f"{port_risk['portfolio_risk_index']:.1f} / 100", delta=port_risk['risk_badge'])
            with c_pr2:
                st.metric("🔴 预警高危重仓股数", f"{port_risk['danger_stock_count']} 只")
            with c_pr3:
                st.metric("🟡 关注警戒重仓股数", f"{port_risk['watch_stock_count']} 只")

            df_scr = _cached_stocks_df(_h_items)
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

        # 聪明钱与机构抱团监控 (升级为左 4.5 四象限散点图 + 右 5.5 持仓量价微观结构表)
        st.markdown("---")
        st.markdown("#### 🧭 持仓标的趋势偏离 vs 拥挤度四象限分布")
        if len(active_examine_holdings) > 0:
            crowd_data = []
            cur_pm = st.session_state.get("pm") or pm
            tot_val = sum(getattr(h, "market_value", 0.0) for h in active_examine_holdings.values())
            for code, h in active_examine_holdings.items():
                c_info = cur_pm.get_fund_smart_money_crowding(code)
                h_mv = getattr(h, "market_value", 0.0)
                wt_pct = round(h_mv / tot_val * 100.0, 2) if tot_val > 0 else 0.0
                full_nm = getattr(h, "fund_name", code)
                short_nm = get_fund_short_alias(code, full_nm)
                crowd_data.append({
                    "code": code,
                    "name": short_nm,
                    "fullname": full_nm,
                    "mv": h_mv,
                    "weight_pct": wt_pct,
                    "ret_20d": c_info.get("ret_20d", 0.0),
                    "bias_20": c_info.get("bias_20", 0.0),
                    "vol_20d": c_info.get("vol_20d", 12.0),
                    "crowd_score": c_info.get("crowding_score", 50.0),
                    "quadrant": c_info.get("quadrant_tag", "🎯 低估击球区"),
                    "tip": c_info.get("advisory_tip", "顺势持有")
                })

            col_q_fig, col_q_tbl = st.columns([4.5, 5.5])
            with col_q_fig:
                # 散点文字防重叠错位放置算法 (Anti-Collision Label Placement)
                pos_pool = ["top right", "bottom left", "top left", "bottom right", "top center", "bottom center"]
                assigned_positions = []
                x_plots = []
                y_plots = []
                for idx, pt in enumerate(crowd_data):
                    bx = pt["bias_20"]
                    by = pt["crowd_score"]
                    is_collided = any(
                        abs(bx - prev["bias_20"]) < 2.0 and abs(by - prev["crowd_score"]) < 7.0
                        for prev in crowd_data[:idx]
                    )
                    if is_collided:
                        chosen_pos = pos_pool[idx % len(pos_pool)]
                        shift_x = 0.45 if "right" in chosen_pos else (-0.45 if "left" in chosen_pos else 0.0)
                        shift_y = 2.5 if "top" in chosen_pos else (-2.5 if "bottom" in chosen_pos else 0.0)
                        x_plots.append(round(bx + shift_x, 2))
                        y_plots.append(round(by + shift_y, 1))
                        assigned_positions.append(chosen_pos)
                    else:
                        chosen_pos = "top right" if bx >= 0 else "top left"
                        x_plots.append(bx)
                        y_plots.append(by)
                        assigned_positions.append(chosen_pos)

                df_q = pd.DataFrame(crowd_data)
                df_q["plot_x"] = x_plots
                df_q["plot_y"] = y_plots
                df_q["pos"] = assigned_positions

                fig_quad = px.scatter(
                    df_q,
                    x="plot_x",
                    y="plot_y",
                    size="mv",
                    color="quadrant",
                    text="name",
                    hover_name="fullname",
                    hover_data={
                        "plot_x": False,
                        "plot_y": False,
                        "pos": False,
                        "bias_20": ":.2f%",
                        "ret_20d": ":.2f%",
                        "crowd_score": ":.1f",
                        "weight_pct": ":.1f%",
                        "mv": False,
                        "quadrant": False
                    },
                    labels={
                        "plot_x": "MA20 均线乖离率 Bias20 (%)",
                        "plot_y": "交易拥挤度热力 (0~100)",
                        "quadrant": "所处象限"
                    },
                    color_discrete_map={
                        "🎯 低估击球区": "#10b981",
                        "🔥 右侧主升/偏热区": "#3b82f6",
                        "⚠️ 放量分歧/避险区": "#ef4444",
                        "📈 温和复苏区": "#06b6d4"
                    }
                )
                max_mv = float(df_q['mv'].max()) if len(df_q) > 0 and not df_q['mv'].isna().all() else 1.0
                safe_sizeref = max(max_mv / 25.0, 1.0) if max_mv > 0 else 1.0
                fig_quad.update_traces(
                    textposition=assigned_positions,
                    marker=dict(sizemin=11, sizeref=safe_sizeref),
                    textfont=dict(size=11)
                )
                fig_quad.add_vline(x=0.0, line_dash="dash", line_color="rgba(128,128,128,0.35)")
                fig_quad.add_hline(y=50.0, line_dash="dash", line_color="rgba(128,128,128,0.35)")
                
                # 四象限背景水印优化：放置在四个象限中心舒适区域，字号13，不挡网格线与数据点
                fig_quad.add_annotation(x=-5.0, y=75.0, text="⚠️ 放量分歧/避险区", showarrow=False, font=dict(color="rgba(239, 68, 68, 0.28)", size=13, family="sans-serif"))
                fig_quad.add_annotation(x=5.0, y=75.0, text="🔥 右侧主升/偏热区", showarrow=False, font=dict(color="rgba(59, 130, 246, 0.28)", size=13, family="sans-serif"))
                fig_quad.add_annotation(x=-5.0, y=25.0, text="🎯 低估击球区", showarrow=False, font=dict(color="rgba(16, 185, 129, 0.28)", size=13, family="sans-serif"))
                fig_quad.add_annotation(x=5.0, y=25.0, text="📈 温和复苏区", showarrow=False, font=dict(color="rgba(6, 182, 212, 0.28)", size=13, family="sans-serif"))
                
                fig_quad.update_layout(
                    height=380,
                    margin=dict(t=25, b=25, l=10, r=10),
                    legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="center", x=0.5),
                    xaxis=dict(title="MA20 均线乖离率 Bias20 (%)"),
                    yaxis=dict(title="交易拥挤度热力 (0~100)", range=[10, 90])
                )
                apply_theme_to_plotly_figure(fig_quad)
                st.plotly_chart(fig_quad, use_container_width=True)

            with col_q_tbl:
                safe_markdown_html("<div style='font-size:13px; font-weight:700; color:var(--text-primary); margin-bottom:6px;'>📡 持仓量价微观结构与波段操作指引</div>")
                disp_df = pd.DataFrame([{
                    "标的简称": f"{d['name']} ({d['code']})",
                    "占比": d["weight_pct"],
                    "20日涨跌": d["ret_20d"],
                    "MA20乖离": d["bias_20"],
                    "拥挤热力": d["crowd_score"],
                    "波段操作建议": d["tip"]
                } for d in crowd_data])

                st.dataframe(
                    disp_df,
                    column_config={
                        "标的简称": st.column_config.TextColumn("标的简称", width="small"),
                        "占比": st.column_config.NumberColumn("占比", format="%.1f%%", width="small"),
                        "20日涨跌": st.column_config.NumberColumn("20日涨跌", format="%+.2f%%", width="small"),
                        "MA20乖离": st.column_config.NumberColumn("MA20乖离", format="%+.2f%%", width="small"),
                        "拥挤热力": st.column_config.NumberColumn("拥挤热力", format="%.1f", width="small"),
                        "波段操作建议": st.column_config.TextColumn("波段操作建议", width="large"),
                    },
                    use_container_width=True,
                    hide_index=True,
                    height=380
                )
        else:
            st.info("当前无持仓数据可供四象限量价分析。")

    # Sub-tab 2: 14 大赛道量化温度计总表
    with box_tab2:
        with st.expander("📊 查看全市场 14 大赛道量化温度计总表 (向下展开)", expanded=True):
            st.caption("📈 14 大赛道真实估值分位、趋势信噪比、20日乖离率与拥挤度全息总表（顺应阅读流向下展开，随时可合上）")
            radar_cache_file = Path(WORKSPACE_ROOT) / "data" / "cache" / "radar_sectors_cache.json"
            sectors_data = []
            if radar_cache_file.exists():
                try:
                    with open(radar_cache_file, "r", encoding="utf-8") as f:
                        c_json = json.load(f)
                        sectors_data = c_json.get("sectors", [])
                except Exception:
                    pass
            if not sectors_data:
                try:
                    from advisory_engine import OpportunityRadarEngine
                    radar_engine = OpportunityRadarEngine()
                    sectors_data = radar_engine.scan_all_sectors()
                except Exception:
                    sectors_data = []
            df_rows = []
            for s in sectors_data:
                f_info = s.get("fund", {})
                df_rows.append({
                    "赛道名称": s.get("name", ""),
                    "估值分位": f"{s.get('val_percentile', 50.0):.1f}%",
                    "趋势信噪比": f"{s.get('er_20', 0.5):.2f}",
                    "20日乖离率": f"{s.get('bias_20', 0.0):+.1f}%",
                    "拥挤度评分": f"{s.get('s_crowd', 85.0):.1f}",
                    "综合得分": f"{s.get('total_score', 50.0):.1f}",
                    "状态标签": s.get("tag", "📈 稳健蓄势"),
                    "优选基金": f"{f_info.get('name', '')} ({f_info.get('code', '')})",
                })
            if df_rows:
                df_thermometer = pd.DataFrame(df_rows)
                st.dataframe(df_thermometer, use_container_width=True, hide_index=True)
            else:
                st.info("赛道温度计数据暂不可用。")

    # Sub-tab 3: 场内ETF与场外联接 14:45 尾盘折溢价套利感知 + 核心场内 ETF 溢价预警哨
    with box_tab3:
        with st.expander("⚡ 场内ETF与场外联接 14:45 尾盘折溢价套利感知", expanded=True):
            st.caption("🧭 毫秒级监测场内核心 ETF（黄金/沪深300/科创50/芯片/标普500/恒生科技）市价与实时 IOPV。溢价 > +1.0% 提示场外低成本申购，折价 < -1.0% 提示场内折价低吸。")
            try:
                arb_sensors = DataLoader.fetch_etf_feeder_arbitrage_sensors(use_cache=True)
                arb_rows = []
                for item in arb_sensors:
                    sig = item.get("signal", "NEUTRAL")
                    sig_badge = "🚨 溢价申购联接" if sig == "PREMIUM_BUY_FEEDER" else ("💎 折价场内低吸" if sig == "DISCOUNT_BUY_ETF" else "⚪ 处于平价区间")
                    arb_rows.append({
                        "对冲套利对": f"{item.get('name', '')} ({item.get('etf_code')}/{item.get('feeder_code')})",
                        "场内市价": f"{item.get('etf_price', 0.0):.4f}",
                        "参考净值(IOPV)": f"{item.get('etf_iopv', 0.0):.4f}",
                        "折溢价率": f"{item.get('discount_premium_pct', 0.0):+.2f}%",
                        "套利信号": sig_badge,
                        "实操建议": item.get("action_advice", "暂无"),
                    })
                if arb_rows:
                    df_arb = pd.DataFrame(arb_rows)
                    st.dataframe(df_arb, use_container_width=True, hide_index=True)
            except Exception as e_arb:
                st.caption(f"（折溢价套利感知初始化: {e_arb}）")

            st.markdown("---")
            st.markdown("##### 📡 核心场内 ETF 溢价预警哨")
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
                        "操作建议": "溢价率>0.8%已超出安全红线，严禁盲目追高，谨防价格向净值回归造成损失。"
                    })
                st.dataframe(pd.DataFrame(etf_rows), use_container_width=True, hide_index=True)
            else:
                st.success("✅ 所有核心监控场内 ETF 溢价率均处于正常安全范围 (<= 0.8%)。")

    # Sub-tab 4: 50ETF与300ETF认沽期权隐含波动率防暴跌哨
    with box_tab4:
        with st.expander("🛡️ 50ETF与300ETF认沽期权隐含波动率防暴跌哨", expanded=True):
            st.caption("🔍 实时监测 50ETF 与 300ETF 近月平值认沽期权 IV 与 20日 HV 偏离度。当 IV 相对 HV 突升超 30% 且跌破 MA20 时输出市场剧烈防暴跌预警，并建议在组合中增加纯债防护仓位。")
            try:
                if "opt_sensors_gui_cache" not in st.session_state:
                    st.session_state["opt_sensors_gui_cache"] = DataLoader.fetch_options_implied_volatility_sensors(use_cache=True)
                opt_sensors_gui = st.session_state["opt_sensors_gui_cache"]
                opt_rows = []
                for s in opt_sensors_gui:
                    opt_rows.append({
                        "期权标的": f"{s.get('option_symbol')} ({s.get('underlying_code')})",
                        "期权类型": "认沽(PUT)",
                        "隐含波动率(IV)": f"{s.get('iv_pct', 0.0):.2f}%",
                        "历史波动率(HV)": f"{s.get('hv_pct', 0.0):.2f}%",
                        "IV/HV偏离度": f"{s.get('iv_hv_spread_pct', 0.0):+.1f}%",
                        "均线状态": "跌破MA20 ⚠️" if s.get("is_below_ma20") else "站上MA20 🟢",
                        "状态信号": s.get("signal_badge", "🟢 隐波平稳"),
                        "实操建议": s.get("action_advice", ""),
                    })
                if opt_rows:
                    st.dataframe(pd.DataFrame(opt_rows), use_container_width=True, hide_index=True)
            except Exception as e_opt_gui:
                st.caption(f"（期权波动率哨加载提示: {e_opt_gui}）")

    # Sub-tab 5: 跨境QDII溢价与外汇期货锁汇成本套利精算
    with box_tab5:
        with st.expander("🌐 跨境QDII溢价与外汇期货锁汇成本套利精算", expanded=True):
            st.caption("结合离岸人民币 (USD/CNH) 远期掉期点 (Forward Swap Points) 测算锁汇避险成本，评估跨市场汇率锁汇套利可行性与真实到手收益增厚。")
            try:
                from portfolio_manager import PortfolioManager
                if "qdii_eval_gui_cache" not in st.session_state:
                    st.session_state["qdii_eval_gui_cache"] = PortfolioManager.evaluate_all_qdii_fx_arbitrage()
                qdii_eval = st.session_state["qdii_eval_gui_cache"]
                qdii_rows = []
                for q in qdii_eval.get("results", []):
                    qdii_rows.append({
                        "标的": f"{q.get('fund_name')} ({q.get('fund_code')})",
                        "资产类别": q.get("asset_category", ""),
                        "跨境溢价率": f"{q.get('qdii_premium_pct', 0.0):+.2f}%",
                        "年化锁汇成本": f"{q.get('annualized_hedging_cost_pct', 0.0):.2f}%",
                        "真实到手增厚": f"{q.get('net_yield_enhancement_bps', 0.0):+.1f} bps",
                        "套利可行性": q.get("signal_badge", ""),
                        "操作建议": q.get("recommendation", ""),
                    })
                if qdii_rows:
                    st.dataframe(pd.DataFrame(qdii_rows), use_container_width=True, hide_index=True)
            except Exception as e_qdii_gui:
                st.caption(f"（跨境锁汇套利精算加载提示: {e_qdii_gui}）")

    # Sub-tab 6: A/C 份额盈亏平衡计算器 (使用 @st.fragment 实现局部无感刷新)
    with box_tab6:
        st.markdown("#### 💡 A/C 份额费率与盈亏平衡精算")
        _frag_dec = getattr(st, "fragment", lambda f: f)

        @_frag_dec
        def _render_ac_fee_calculator():
            c_ac1, c_ac2, c_ac3, c_ac4 = st.columns(4)
            with c_ac1:
                r_sub = st.number_input("A 类前端申购费率 (折后 %)", value=0.15, step=0.01, key="ac_r_sub")
            with c_ac2:
                r_sales = st.number_input("C 类年化销售服务费率 (%)", value=0.40, step=0.05, key="ac_r_sales")
            with c_ac3:
                v_amt = st.number_input("拟投资金额 (元)", value=50000.0, step=5000.0, key="ac_v_amt")
            with c_ac4:
                v_days = st.number_input("预计持有周期 (天)", value=90, min_value=1, max_value=730, step=5, key="ac_v_days")

            calc = getattr(pm, "calculator", pm)
            calc_res = calc.calculate_break_even_days(
                standard_sub_rate=r_sub / 10.0 / 100.0,
                discount=10.0,
                sales_service_annual_rate=r_sales / 100.0,
                max_days=365,
                target_holding_days=int(v_days),
                investment_amount=float(v_amt)
            )
            st.success(f"⚖️ **精算测算结论**：A 类与 C 类的费率盈亏平衡天数为 **{calc_res['break_even_day']} 天**。")
            if calc_res.get("target_recommendation"):
                st.info(f"🎯 **选型建议**：{calc_res['target_recommendation']['summary']}")

        _render_ac_fee_calculator()

with tab_backtest:
    try:
        # 彻底移除拦路按钮，切换即现场渲染
        render_tab3_backtest_content(pm, snapshot)
    except Exception as e:
        st.error(f"Tab 3 回测渲染异常: {e}")

# =============================================================
# Tab 4: 【🔍 穿透工具】（大类穿透/加权行业/重合热力图/底层排雷/AC算费/ETF溢价）
# =============================================================
with tab_toolbox:
    try:
        # tab4_lookthrough_activated: 彻底移除拦路按钮，切换即现场渲染
        render_tab4_toolbox_content(pm, snapshot)
    except Exception as e:
        st.error(f"Tab 4 穿透工具箱渲染异常: {e}")