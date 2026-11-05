# -*- coding: utf-8 -*-
"""
scripts/remodel_app_gui.py
重构 app_gui.py：
1. 侧边栏专注：外观色彩 + 市场状态与底座 + 核心指数行情走廊（完美复刻用户效果截图）
2. 彻底移除侧边栏中的全局目标联动、交易风控护栏、账本环境管理
3. 移除主界面顶部的横向 index-ticker-strip
4. Tab 1 步骤一归位：风险策略档位下拉框、期望年化收益率滑块、单日限购过滤、策略锚点卡片
5. Tab 2 步骤一归位：资产基线与风控横幅、快捷按钮（演示组合/撤销/同步）、免折腾调仓缓冲带滑块
6. 修复 5 大隐藏 Bug：
   - KeyError: target_weight 修复（安全提取 target_weight_pct / target_weight）
   - snapshot.get("bias_20") 防 None
   - 分批/定投表格真实展示具体批次/扣款金额
   - 机会雷达入备选池清空缓存并传参 radar_selected_funds
   - 清除 1845, 1864, 1866, 1867, 3017 等残留硬编码暗色 Hex
"""

import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
GUI_FILE = WORKSPACE_ROOT / "AGY2_FundAdvisory" / "app_gui.py"

def main():
    with open(GUI_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    print(f"Original app_gui.py lines: {len(content.splitlines())}")

    # =========================================================================
    # 1. CSS 补充：侧边栏垂直行情走廊卡片样式
    # =========================================================================
    sidebar_card_css = """
    /* 侧边栏垂直行情走廊卡片流 (Sidebar Index Corridor Cards) */
    .sidebar-index-card {{
        background: var(--bg-surface) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 8px;
        padding: 9px 12px;
        margin-bottom: 8px;
        box-shadow: var(--shadow-card) !important;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        transition: all 0.2s ease;
        box-sizing: border-box;
    }}
    .sidebar-index-card:hover {{
        border-color: var(--border-hover) !important;
        background: var(--bg-elevated) !important;
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
        white-space: nowrap;
    }}
    .sidebar-index-code {{
        font-size: 11px;
        font-family: monospace;
        color: var(--text-muted) !important;
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
        font-family: monospace;
        color: var(--text-primary) !important;
        text-align: right;
    }}
    .sidebar-index-badge {{
        font-size: 11px;
        font-weight: 700;
        font-family: monospace;
        border-radius: 4px;
        padding: 2px 6px;
        line-height: 1.2;
        white-space: nowrap;
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
    """

    if ".sidebar-index-card" not in content:
        content = content.replace("/* 顶部行情带真实估值分位标签微胶囊 */", sidebar_card_css + "\n    /* 顶部行情带真实估值分位标签微胶囊 */")

    # =========================================================================
    # 2. 宏观数据提前计算 + 侧边栏完全重塑 + 移除主界面横向行情条
    # =========================================================================
    # 查找定位点：
    # 起点: snapshot = StrategyBridge.get_latest_market_snapshot...
    # 侧边栏: with st.sidebar:
    # 顶部全局看板: # ------------------------------------------------------------- \n # 顶部全局看板：1 行 4 宽卡
    # 结束点: 盘后预案提醒 (latest_plan = pm.get_latest_next_day_plan())

    start_anchor = "# 统一攻防红线数据源（单源同真：优先 trigger_lines，其次 snapshot 顶级字段，兜底现价计算）"
    end_anchor = "# 盘后预案提醒"

    if start_anchor not in content or end_anchor not in content:
        raise ValueError(f"Could not locate start or end anchor in app_gui.py")

    before_part = content[:content.find(start_anchor)]
    after_part = content[content.find(end_anchor):]

    remodelled_sidebar_and_top = """# 统一攻防红线数据源（单源同真：优先 trigger_lines，其次 snapshot 顶级字段，兜底现价计算）
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
    st.subheader("🧭 全局领航台")
    st.caption("市场状态与核心指数行情走廊")
    st.markdown("---")

    # 1. 🎨 外观与色彩 (5 大高定主题 + 2 套涨跌模式)
    st.markdown("##### 🎨 外观与色彩")

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

    st.markdown("---")

    # 2. 🕒 市场状态与底座
    st.markdown("##### 🕒 市场状态与底座")
    clock_color = active_co['color_down'] if market_status.is_golden_window else (active_co['color_up'] if market_status.is_after_market else active_th['accent_primary'])
    clock_title = "🟢 14:30黄金窗口" if market_status.is_golden_window else ("🟡 盘后已关账" if market_status.is_after_market else "🔵 盘中观察期")
    total_days = snapshot.get("total_days", 2142)
    latest_date = snapshot.get("latest_date", "2026-11-04")

    safe_markdown_html(f\"\"\"
    <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 10px 12px; margin-bottom: 8px; box-shadow: var(--shadow-card);">
        <div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 5px;">
            <span style="color: var(--text-secondary);">交易时钟</span>
            <span style="color: {clock_color}; font-weight: 700;">{clock_title}（倒计时 {market_status.countdown_str}）</span>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 5px;">
            <span style="color: var(--text-secondary);">市场定调</span>
            <span style="color: {st_color}; font-weight: 700;">{vernacular_state} ｜ 信噪比: {snr:.2f}</span>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 5px;">
            <span style="color: var(--text-secondary);">攻防红线</span>
            <span style="color: var(--accent-primary); font-weight: 600;">破 {surge_line:,.0f} 进攻 ｜ 跌 {breakdown_line:,.0f} 防守</span>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 6px;">
            <span style="color: var(--text-secondary);">湖仓底座</span>
            <span style="color: var(--text-muted); font-family: monospace;">{latest_date}（{total_days:,} 交易日跨牛熊）</span>
        </div>
        <div style="border-top: 1px dashed var(--border-subtle); padding-top: 6px; margin-top: 4px;">
            <div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 3px;">
                <span style="color: var(--text-secondary);">两市成交: <b style="color: var(--text-primary);">{t_str}</b></span>
                <span style="color: var(--text-secondary);">多方占比: <b style="color: var(--color-up);">{u_pct}%</b></span>
            </div>
            <div style="width: 100%; height: 4px; background: var(--bg-down); border-radius: 2px; overflow: hidden; display: flex;">
                <div style="width: {u_pct}%; height: 100%; background: var(--color-up);"></div>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 10px; color: var(--text-muted); margin-top: 3px;">
                <span>涨 {u_cnt} 家</span>
                <span>平 {mb_data.get('flat_count', 0)} 家</span>
                <span>跌 {d_cnt} 家</span>
            </div>
        </div>
    </div>
    \"\"\")

    st.markdown("---")

    # 3. 📊 核心指数行情走廊 (垂直卡片流，完美复刻截图交互)
    col_sb_title, col_sb_opt, col_sb_rf = st.columns([5.5, 2.5, 2.0])
    with col_sb_title:
        st.markdown("##### 📊 核心指数行情走廊")
    with col_sb_opt:
        with st.popover("⚙️", help="增删指数与切换风格预设"):
            st.caption("行情走廊指数配置")
            all_avail_indices = {
                "000300": "沪深300",
                "000688": "科创50",
                "000922": "中证红利",
                "000905": "中证500",
                "000852": "中证1000",
                "518880": "黄金ETF",
                "399006": "创业板指",
                "000016": "上证50",
                "HKTECH": "恒生科技",
                "NDX": "纳斯达克100"
            }
            default_keys = ["000300", "000688", "000922", "000905", "000852", "518880"]
            if "sb_selected_corridor_indices" not in st.session_state:
                st.session_state.sb_selected_corridor_indices = default_keys
            sel_corridor_keys = st.multiselect(
                "显示标的",
                options=list(all_avail_indices.keys()),
                default=st.session_state.sb_selected_corridor_indices,
                format_func=lambda k: f"{all_avail_indices.get(k, k)} ({k})",
                key="ms_corridor_indices"
            )
            st.session_state.sb_selected_corridor_indices = sel_corridor_keys or default_keys

    with col_sb_rf:
        if st.button("🔄", key="btn_refresh_all_live_quotes", help="极速刷新实时行情", use_container_width=True):
            clear_realtime_cache()
            fetch_batch_realtime_indices(use_cache=False)
            fetch_market_turnover_and_sentiment(force_refresh=True)
            fetch_or_calc_index_valuations(force_refresh=True)
            pm.sync_holdings_live_nav(use_intraday_gsz=True)
            StrategyBridge._cached_snapshot = None
            StrategyBridge._cached_matrix = None
            StrategyBridge.get_latest_market_snapshot(force_reload=True, auto_sync=False)
            st.rerun()

    # 拉取当前批次实时指数行情与估值
    active_corridor_list = fetch_batch_realtime_indices(use_cache=True)
    corridor_val_map = fetch_or_calc_index_valuations(force_refresh=False)
    target_idx_codes = set(st.session_state.get("sb_selected_corridor_indices", ["000300", "000688", "000922", "000905", "000852", "518880"]))

    rendered_count = 0
    corridor_cards_html = []
    for idx_item in active_corridor_list:
        icode = idx_item["code"]
        if icode not in target_idx_codes:
            continue
        rendered_count += 1
        c_pct = idx_item["change_pct"]
        c_badge_cls = "sidebar-index-badge-up" if c_pct > 0 else ("sidebar-index-badge-down" if c_pct < 0 else "sidebar-index-badge-flat")
        c_sign = "+" if c_pct > 0 else ""
        pt_fmt = f"{idx_item['point']:,.3f}" if (icode == '518880') else f"{idx_item['point']:,.2f}"
        v_meta = corridor_val_map.get(icode) or corridor_val_map.get(idx_item.get("secid", "")) or {}
        v_label = v_meta.get("label", "")
        v_status = v_meta.get("status", "mid")
        v_badge_html = f'<span class="index-pill-val-badge val-{v_status}" style="font-size: 10px; margin-left: 4px;">{v_label}</span>' if v_label else ''

        corridor_cards_html.append(f\"\"\"
        <div class="sidebar-index-card">
            <div class="sidebar-index-left">
                <div class="sidebar-index-name-row">
                    <span class="sidebar-index-name">{idx_item['name']}</span>
                    {v_badge_html}
                </div>
                <span class="sidebar-index-code">{icode}</span>
            </div>
            <div class="sidebar-index-right">
                <span class="sidebar-index-pt">{pt_fmt}</span>
                <span class="sidebar-index-badge {c_badge_cls}">{c_sign}{c_pct:.2f}%</span>
            </div>
        </div>
        \"\"\")

    safe_markdown_html("\\n".join(corridor_cards_html))
    st.caption(f"💡 点击右上角 ⚙️ 可自由增删全市场指数。共展示 {rendered_count} 只标的。")

# -------------------------------------------------------------
# 顶部全局看板：1 行 4 宽卡 + 1 个紧凑刷新按钮 (无下方重复行情条)
# -------------------------------------------------------------
top_c1, top_c2, top_c3, top_c4 = st.columns(4)

with top_c1:
    clock_color = active_co['color_down'] if market_status.is_golden_window else (active_co['color_up'] if market_status.is_after_market else active_th['accent_primary'])
    clock_title = "🟢 14:30黄金窗口" if market_status.is_golden_window else ("🟡 盘后已关账" if market_status.is_after_market else "🔵 盘中观察期")
    c1_tip = f"场外公募基金每日 15:00 关账。15:00 前下单按今日未知收盘净值成交，15:00 后下单顺延至下一交易日({market_status.effective_trade_date})成交。\\n当前状态: {market_status.title}\\n{market_status.message}"
    safe_markdown_html(f\"\"\"
    <div class="main-metric-card">
        <div class="metric-card-title">
            <span>🕒 交易时钟与窗口</span>
            <span title="{c1_tip}" style="cursor:help; color:var(--text-muted); font-size:12px;">ⓘ</span>
        </div>
        <div class="metric-value-huge" style="color: {clock_color};">
            {clock_title}
        </div>
        <div class="metric-card-sub" style="font-size: 11px; color: var(--text-secondary); margin-top: 2px;">
            倒计时 {market_status.countdown_str} ｜ 距网格日 {days_to_next}天
        </div>
    </div>
    \"\"\")

with top_c2:
    c2_tip = f"沪深300现价: {c300_disp:,.1f}\\nMA20生命线: {m20_disp:,.0f} (偏离 {bias_disp:+.1f}%)\\nMA60中线: {m60_disp:,.0f}\\n考夫曼信噪比(ER): {snr:.2f} (自适应窗口 {eff_w}日)\\n动量加速度: {accel:+.2f}%\\n突破进攻线: 突破 {surge_line:,.0f} 后增配科技成长(科创50/中证1000)\\n跌破防守线: 跌破 {breakdown_line:,.0f} 后减仓避险至纯债压舱石"

    exhaustion_badge = ""
    if mom_exhaustion:
        exhaustion_badge = f'<div style="background-color: var(--bg-elevated); color: var(--color-up); font-size: 11px; font-weight: 600; padding: 2px 6px; border-radius: 4px; margin-top: 2px; border: 1px solid var(--border-subtle); line-height: 1.2;">{exhaustion_text}</div>'

    safe_markdown_html(f\"\"\"
    <div class="main-metric-card">
        <div class="metric-card-title">
            <span>🧭 市场定调与攻防线</span>
            <span title="{c2_tip}" style="cursor:help; color:var(--text-muted); font-size:12px;">ⓘ</span>
        </div>
        <div class="metric-value-huge" style="color: {st_color};">
            {vernacular_state}
        </div>
        <div class="metric-card-sub" style="display: flex; justify-content: space-between; gap: 4px; color: var(--text-secondary); font-size: 11px;">
            <span>📈破 {surge_line:,.0f} 进攻</span>
            <span>🛡️跌 {breakdown_line:,.0f} 防守</span>
        </div>
        <div class="metric-card-sub" style="display: flex; justify-content: space-between; gap: 4px; color: var(--accent-primary); font-weight: 500; font-size: 11px;">
            <span>📡信噪比 {snr:.2f}</span>
            <span>⚡加速度 {accel:+.1f}%</span>
        </div>
        {exhaustion_badge}
    </div>
    \"\"\")

with top_c3:
    val_status = "估值极便宜 · 资金充裕" if (erp_pct >= 75 and dr007_bp <= 5) else "估值合理 · 流动性中性"
    c3_tip = (
        f"两市成交额: {t_str} ({mb_data.get('vol_text', '')})\\n"
        f"全市场宽度: 上涨 {u_cnt} 家 / 下跌 {d_cnt} 家 (多方占比 {u_pct}% · {mb_data.get('sentiment_label', '')})\\n"
        f"ERP股债性价比分位: {erp_pct:.1f}% (极高分位·股票高性价比)\\n"
        f"DR007利率: {dr007_val:.2f}% (较基准 {dr007_bp:+.1f}bp·资金面宽裕)\\n"
        f"期权IV: {opt_iv:.1f}% ｜ IC期指年化贴水: {ic_basis:.1f}%"
    )
    safe_markdown_html(f\"\"\"
    <div class="main-metric-card">
        <div class="metric-card-title">
            <span>🌡️ 估值与资金量能</span>
            <span title="{c3_tip}" style="cursor:help; color:var(--text-muted); font-size:12px;">ⓘ</span>
        </div>
        <div class="metric-value-huge" style="color: var(--color-down); font-size: 16px;">
            {val_status}
        </div>
        <div class="metric-card-sub" style="display: flex; justify-content: space-between; gap: 4px; font-size: 11px; color: var(--text-secondary); margin-top: 2px;">
            <span>两市成交: <b style="color: var(--text-primary);">{t_str}</b></span>
            <span>多方占比: <b style="color: var(--color-up);">{u_pct}%</b></span>
        </div>
    </div>
    \"\"\")

with top_c4:
    c4_tip = f"全组合总资产: ¥{total_cur_equity:,.2f}\\n可用现金: ¥{pm.available_cash:,.2f}\\n在途资金: ¥{pm.in_transit_cash:,.2f}\\n累计投入成本: ¥{_t2_cost:,.2f}"
    safe_markdown_html(f\"\"\"
    <div class="main-metric-card">
        <div class="metric-card-title">
            <span>💰 总资产与今日预估</span>
            <span title="{c4_tip}" style="cursor:help; color:var(--text-muted); font-size:12px;">ⓘ</span>
        </div>
        <div class="metric-value-huge" style="color: var(--text-primary);">
            ¥{total_cur_equity:,.2f}
        </div>
        <div class="metric-card-sub" style="display: flex; justify-content: space-between; gap: 4px; font-size: 11px;">
            <span>盘中预估: <b style="color: {pnl_color};">¥{est_pnl:+,.2f}</b></span>
            <span>涨跌: <b style="color: {pnl_color};">{est_pnl_pct:+.2f}%</b></span>
        </div>
        <div class="metric-card-sub" style="display: flex; justify-content: space-between; gap: 4px; font-size: 11px;">
            <span>持仓浮盈: <b style="color: {tot_pnl_color};">¥{_t2_pnl:+,.2f}</b></span>
            <span>现金: <b>¥{pm.available_cash:,.0f}</b></span>
        </div>
    </div>
    \"\"\")

"""

    content = before_part + remodelled_sidebar_and_top + after_part

    # =========================================================================
    # 3. 机会雷达：点击入备选池联动
    # =========================================================================
    radar_old = """                        if st.button("➕ 入备选池", key=f"btn_add_radar_pool_{sec['sector_id']}", use_container_width=True, type="secondary"):
                            if "custom_candidate_pool" not in st.session_state:
                                st.session_state.custom_candidate_pool = []
                            fcode = sec_fund.get("code")
                            if fcode and fcode not in st.session_state.custom_candidate_pool:
                                st.session_state.custom_candidate_pool.append(fcode)
                            if "custom_fund_overrides" not in st.session_state:
                                st.session_state.custom_fund_overrides = {}
                            st.session_state.custom_fund_overrides[sec_fund.get("name", fcode)] = fcode
                            st.toast(f"✅ 已将【{sec_fund.get('name')}】一键纳入备选池！")
                            st.rerun()"""

    radar_new = """                        if st.button("➕ 入备选池", key=f"btn_add_radar_pool_{sec['sector_id']}", use_container_width=True, type="secondary"):
                            if "custom_candidate_pool" not in st.session_state:
                                st.session_state.custom_candidate_pool = []
                            if "radar_selected_funds" not in st.session_state:
                                st.session_state.radar_selected_funds = []
                            fcode = sec_fund.get("code")
                            if fcode and fcode not in st.session_state.custom_candidate_pool:
                                st.session_state.custom_candidate_pool.append(fcode)
                            if fcode and fcode not in st.session_state.radar_selected_funds:
                                st.session_state.radar_selected_funds.append(fcode)
                            if "custom_fund_overrides" not in st.session_state:
                                st.session_state.custom_fund_overrides = {}
                            st.session_state.custom_fund_overrides[sec_fund.get("name", fcode)] = fcode
                            # 物理清空下游推演与交割单缓存以强制重新计算
                            st.session_state.tab1_sim_cache = None
                            st.session_state.tab1_step3_cache = None
                            st.session_state.tab1_trigger_sim = True
                            st.toast(f"✅ 已将【{sec_fund.get('name')}】一键纳入备选池，正在为您重新定权！")
                            st.rerun()"""

    if radar_old in content:
        content = content.replace(radar_old, radar_new)
        print("Updated radar pool button logic.")

    # =========================================================================
    # 4. Tab 1 步骤一：模式 A 增加【风险策略档位】选择与双向联动 + 策略锚点卡片
    # =========================================================================
    tab1_s1_old = """            if tier_mode.startswith("模式 A"):
                col_s1_left, col_s1_right = st.columns([6, 4])
                with col_s1_left:
                    def _sync_tab1_return_change():
                        val = float(st.session_state.slider_target_return)
                        st.session_state.target_return_val = val
                        tier = map_slider_to_tier(val)
                        st.session_state.active_tier_val = tier
                        st.session_state.sb_target_return_slider = val
                        tier_labels_all = ["C1 安稳保守型", "C2 稳健固收+型", "C3 平衡进取型", "C4 成长进攻型", "C5 极限高Beta追击型"]
                        tier_code_to_idx_all = {"C1": 0, "C2": 1, "C3": 2, "C4": 3, "C5": 4}
                        st.session_state.sb_tier_selector = tier_labels_all[tier_code_to_idx_all.get(tier, 2)]
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
                        "🛡️ 单日限购过滤阈值",
                        quota_options,
                        index=cur_q_idx,
                        key="tab1_quota_filter_sel",
                        on_change=_sync_tab1_quota_filter_change,
                        help="开启过滤后，选基与建仓单将自动用同赛道不限购备选基金替换受限标的"
                    )

                cur_tier_meta = RISK_TIERS_CONFIG.get(active_tier, RISK_TIERS_CONFIG["C3"])
                if target_ret_input > 25.0:
                    st.caption(f"⚡ 高收益提示：目标年化 {target_ret_input:.0f}% 对应【{active_tier} {cur_tier_meta['name']}】，历史最大回撤约 {abs(cur_tier_meta['historical_mdd']):.1f}%，解套需 {cur_tier_meta['max_tolerated_months']} 个月，建议长钱长投。")
                else:
                    st.caption(f"💡 目标收益 {target_ret_input:.0f}% ➔ 当前档位：【{active_tier} {cur_tier_meta['name']}】（权益上限 {cur_tier_meta['equity_range'][1]}% ｜ 预期年化 {cur_tier_meta['target_cagr']} ｜ 核心：{cur_tier_meta['core_assets']}）")"""

    tab1_s1_new = """            if tier_mode.startswith("模式 A"):
                tier_labels_all = ["C1 安稳保守型", "C2 稳健固收+型", "C3 平衡进取型", "C4 成长进攻型", "C5 极限高Beta追击型"]
                tier_code_to_idx_all = {"C1": 0, "C2": 1, "C3": 2, "C4": 3, "C5": 4}
                cur_tier_now = str(st.session_state.get("active_tier_val", "C3")).upper()
                cur_ret_now = float(st.session_state.get("target_return_val", 15.0))
                cur_t_idx = tier_code_to_idx_all.get(cur_tier_now, 2)

                col_s1_tier, col_s1_slider, col_s1_right = st.columns([3.5, 3.5, 3.0])

                with col_s1_tier:
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
                        "🛡️ 单日限购过滤阈值",
                        quota_options,
                        index=cur_q_idx,
                        key="tab1_quota_filter_sel",
                        on_change=_sync_tab1_quota_filter_change,
                        help="开启过滤后，选基与建仓单将自动用同赛道不限购备选基金替换受限标的"
                    )

                cur_tier_meta = RISK_TIERS_CONFIG.get(active_tier, RISK_TIERS_CONFIG["C3"])
                _num_f = int(st.session_state.get("tab1_num_funds", 6))
                _m_type = st.session_state.get("tab1_model_type", "hrp_cvar")
                _m_name = QUANT_MODELS_CATALOG.get(_m_type, {}).get("name", "鲁棒双核HRP")

                safe_markdown_html(f\"\"\"
                <div style="background: var(--bg-elevated); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 8px 12px; margin-top: 8px; margin-bottom: 8px; font-size: 11px; line-height: 1.5; color: var(--text-secondary);">
                    <div><b>定权模型：</b>{_m_name}（{_num_f}只优选配置）</div>
                    <div><b>资产锚点：</b>{cur_tier_meta['core_assets']}</div>
                    <div><b>权益中枢：</b>{cur_tier_meta['equity_range_str']} ｜ <b>回撤上限：</b>{cur_tier_meta['max_drawdown_limit']}</div>
                </div>
                \"\"\")

                if target_ret_input > 25.0:
                    st.caption(f"⚡ 高收益提示：目标年化 {target_ret_input:.0f}% 对应【{active_tier} {cur_tier_meta['name']}】，历史最大回撤约 {abs(cur_tier_meta['historical_mdd']):.1f}%，解套需 {cur_tier_meta['max_tolerated_months']} 个月，建议长钱长投。")
                else:
                    st.caption(f"💡 目标收益 {target_ret_input:.0f}% ➔ 当前档位：【{active_tier} {cur_tier_meta['name']}】（权益上限 {cur_tier_meta['equity_range'][1]}% ｜ 预期年化 {cur_tier_meta['target_cagr']} ｜ 核心：{cur_tier_meta['core_assets']}）")"""

    if tab1_s1_old in content:
        content = content.replace(tab1_s1_old, tab1_s1_new)
        print("Updated Tab 1 Step 1 controls and anchor card.")

    # =========================================================================
    # 5. compute_n_funds_model_portfolio 传入 radar_selected_funds
    # =========================================================================
    model_call_old = """                res_portfolio = StrategyBridge.compute_n_funds_model_portfolio(
                    tier=active_tier,
                    target_return_pct=float(cur_tab1_params["target_ret"]),
                    num_funds=int(num_funds_input),
                    model_type=sel_model_type,
                    horizon_label=horizon_choice,
                    capital=float(plan_capital),
                    custom_overrides=st.session_state.get("custom_fund_overrides", {}),
                    purchase_limit_filter=st.session_state.get("purchase_limit_filter", "不限 (自动拆单承接)"),
                    progress_cb=_sim_cb
                )"""

    model_call_new = """                res_portfolio = StrategyBridge.compute_n_funds_model_portfolio(
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
                )"""

    if model_call_old in content:
        content = content.replace(model_call_old, model_call_new)
        print("Updated compute_n_funds_model_portfolio with radar_selected_funds.")

    # =========================================================================
    # 6. Tab 1 步骤三：KeyError: target_weight 修复与分批/定投表格真实数值联动
    # =========================================================================
    s3_key_old = """            alloc_list_for_dca = [
                {"code": it["fund_code"], "name": it["fund_name"], "weight": it["target_weight"] / 100.0}
                for it in blueprint.get("items", [])
            ]"""

    s3_key_new = """            alloc_list_for_dca = [
                {"code": it["fund_code"], "name": it["fund_name"], "weight": float(it.get("target_weight_pct", it.get("target_weight", 0.0))) / 100.0}
                for it in blueprint.get("items", [])
            ]"""

    if s3_key_old in content:
        content = content.replace(s3_key_old, s3_key_new)
        print("Fixed KeyError: target_weight in alloc_list_for_dca.")

    bias_old = """                erp_pct = float(snapshot.get("erp_percentile", 78.0))
                bias_20 = float(snapshot.get("c300_bias_20", 1.0))"""

    bias_new = """                erp_pct = float(snapshot.get("erp_percentile", 78.0))
                bias_20 = float(snapshot.get("c300_bias_20", snapshot.get("bias_20", 1.0)))"""

    if bias_old in content:
        content = content.replace(bias_old, bias_new)
        print("Updated bias_20 fallback in smart dca.")

    # 表格增加分批建仓与定投金额联动
    table_render_old = """            st.dataframe(
                df_bp,
                use_container_width=True,
                hide_index=True
            )"""

    table_render_new = """            # 联动分批与智能定投展示差异化执行金额
            df_display = df_bp.copy()
            if "稳健三步" in cap_deployment_mode:
                df_display["第1批底仓(50%)"] = (df_display["精确买入金额(元)"] * 0.50).map("¥{:,.2f}".format)
                df_display["第2批逢低(30%)"] = (df_display["精确买入金额(元)"] * 0.30).map("¥{:,.2f}".format)
                df_display["第3批突破(20%)"] = (df_display["精确买入金额(元)"] * 0.20).map("¥{:,.2f}".format)
            elif "智能定投" in cap_deployment_mode and 'dca_plan' in locals():
                mult = dca_plan.get("multiplier", 1.0)
                df_display["每期基准(12期)"] = (df_display["精确买入金额(元)"] / 12.0).map("¥{:,.2f}".format)
                df_display["当期自适应扣款"] = (df_display["精确买入金额(元)"] / 12.0 * mult).map("¥{:,.2f}".format)

            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True
            )"""

    if table_render_old in content:
        content = content.replace(table_render_old, table_render_new)
        print("Enhanced blueprint dataframe with batch / dca columns.")

    # =========================================================================
    # 7. Tab 2 步骤一：归位【账本环境管理】横幅与快捷按钮 + 【免折腾调仓缓冲带】
    # =========================================================================
    tab2_s1_header_old = """        # ---------------------------------------------------------
        # 步骤一：当前持仓账本
        # ---------------------------------------------------------
        st.markdown("### 步骤一：持仓账本")

        # ── 第一层：4 张高信息密度资产概览卡（移除上方冗余全宽按钮）──"""

    tab2_s1_header_new = """        # ---------------------------------------------------------
        # 步骤一：当前持仓账本
        # ---------------------------------------------------------
        st.markdown("### 步骤一：持仓账本")

        # 🗄️ 账本环境管理与风控横幅（归位于此，彻底消除侧边栏重复）
        _tot_base_eq = sum(h.market_value for h in pm.holdings.values()) + pm.available_cash + pm.in_transit_cash
        _mat_date_str = snapshot.get('latest_date', '2026-11-04')
        safe_markdown_html(f\"\"\"
        <div style="background: var(--bg-elevated); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 10px 14px; margin-bottom: 10px; font-size: 12px; line-height: 1.5; color: var(--text-secondary);">
            💼 <b>资产基线：</b>¥{_tot_base_eq:,.2f} ｜ <b>持仓标的：</b>{len(pm.holdings)} 只 ｜ <b>底座：</b>{_mat_date_str} ｜ <b>在途现金：</b>¥{pm.in_transit_cash:,.2f}<br>
            🛡️ <b>风控防线</b>：7天惩罚费拦截 (1.50%惩罚扣除硬阻断) ｜ 悲观持有天数梯级守护
        </div>
        \"\"\")

        col_t2_env1, col_t2_env2, col_t2_env3, col_t2_buf = st.columns([2.5, 2.5, 2.5, 4.5])
        with col_t2_env1:
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

        with col_t2_env2:
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

        with col_t2_env3:
            if st.button("🔄 全局同步估值", use_container_width=True, type="primary", key="btn_tab2_sync"):
                clear_realtime_cache()
                fetch_batch_realtime_indices(use_cache=False)
                pm.sync_holdings_live_nav(use_intraday_gsz=True)
                StrategyBridge._cached_snapshot = None
                StrategyBridge._cached_matrix = None
                StrategyBridge.get_latest_market_snapshot(force_reload=True, auto_sync=False)
                st.success("全局行情与估值已刷新")
                st.rerun()

        with col_t2_buf:
            def _sync_t2_buffer_change():
                st.session_state.rebalance_buffer_pct = float(st.session_state.tab2_rebal_buffer_slider)
                st.session_state.tab2_diag_cache = None
                st.session_state.tab2_rebal_cache = None

            cur_buf_val = float(st.session_state.get("rebalance_buffer_pct", 3.0))
            if "tab2_rebal_buffer_slider" not in st.session_state or abs(float(st.session_state.tab2_rebal_buffer_slider) - cur_buf_val) > 1e-4:
                st.session_state.tab2_rebal_buffer_slider = cur_buf_val

            st.slider(
                "🛡️ 免折腾调仓缓冲带 (%)",
                min_value=1.0,
                max_value=5.0,
                step=0.5,
                format="%.1f%%",
                key="tab2_rebal_buffer_slider",
                on_change=_sync_t2_buffer_change,
                help="控制 Tab 2 调仓裁决与温和调仓过滤的最小偏离阈值。低于此阈值的微小偏离将自动维持现状，杜绝无效换仓摩擦"
            )

        # ── 第一层：4 张高信息密度资产概览卡（移除上方冗余全宽按钮）──"""

    if tab2_s1_header_old in content:
        content = content.replace(tab2_s1_header_old, tab2_s1_header_new)
        print("Added Ledger Management and Buffer slider to Tab 2 Step 1.")

    # =========================================================================
    # 8. 清除硬编码暗色 Hex 颜色
    # =========================================================================
    content = content.replace("color: #334155;", "color: var(--text-secondary);")
    content = content.replace("color: #1e293b;", "color: var(--text-primary);")
    content = content.replace("color: #475569;", "color: var(--text-secondary);")

    # 写回文件
    with open(GUI_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Successfully updated {GUI_FILE}. Final lines: {len(content.splitlines())}")

if __name__ == "__main__":
    main()
