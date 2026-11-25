import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

targets = [ROOT / "app_gui.py", ROOT / "AGY2_FundAdvisory" / "app_gui.py"]

# 1. 移除 span 强覆盖
OLD_SPAN_RULE = """        [data-testid="stSidebar"] h5,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] span {{
            color: #E2E8F0 !important;
        }}"""

NEW_SPAN_RULE = """        [data-testid="stSidebar"] h5,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label {{
            color: #E2E8F0 !important;
        }}"""

# 2. 追加到 </style> 前的终极高优先级 CSS
CSS_APPEND = """
    /* ========================================================================= */
    /* 🏛️ G41 终极视觉精度与对比度修复层（最高层叠优先级，置于 style 最末尾） */
    /* ========================================================================= */
    @media (min-width: 769px) {
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label p,
        [data-testid="stSidebar"] div[role="radiogroup"] label p,
        [data-testid="stSidebar"] [data-testid="stRadioOption"] p {
            color: #CBD5E1 !important;
            opacity: 1 !important;
        }
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover p,
        [data-testid="stSidebar"] div[role="radiogroup"] label:hover p,
        [data-testid="stSidebar"] [data-testid="stRadioOption"]:hover p {
            color: #FFFFFF !important;
        }
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:has(input:checked),
        [data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] {
            background: rgba(194, 150, 72, 0.22) !important;
            border-left: 3px solid #C29648 !important;
        }
        [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:has(input:checked) p,
        [data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] p,
        [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p {
            color: #FFFFFF !important;
            font-weight: 700 !important;
        }

        /* 侧边栏所有普通按钮 & Popover 按钮（外观 / 刷新 / ＋）强制亮白字 + 透明深灰底 */
        [data-testid="stSidebar"] button:not([kind="primary"]),
        [data-testid="stSidebar"] button[data-testid="stPopoverButton"] {
            background-color: rgba(255, 255, 255, 0.08) !important;
            border: 1px solid rgba(255, 255, 255, 0.18) !important;
            color: #F1F5F9 !important;
            border-radius: 7px !important;
            min-height: 32px !important;
            padding: 4px 10px !important;
        }
        [data-testid="stSidebar"] button:not([kind="primary"]) p,
        [data-testid="stSidebar"] button:not([kind="primary"]) span,
        [data-testid="stSidebar"] button[data-testid="stPopoverButton"] p,
        [data-testid="stSidebar"] button[data-testid="stPopoverButton"] span,
        [data-testid="stSidebar"] button[data-testid="stPopoverButton"] svg,
        [data-testid="stSidebar"] button:not([kind="primary"]) svg {
            color: #F1F5F9 !important;
            fill: #CBD5E1 !important;
            font-weight: 500 !important;
        }
        [data-testid="stSidebar"] button:not([kind="primary"]):hover,
        [data-testid="stSidebar"] button[data-testid="stPopoverButton"]:hover {
            background-color: rgba(255, 255, 255, 0.16) !important;
            border-color: rgba(255, 255, 255, 0.32) !important;
        }

        /* 侧边栏账本下拉框：彻底消灭刺眼白框，改为深墨融合质感 + 亮白字 */
        [data-testid="stSidebar"] div[data-baseweb="select"],
        [data-testid="stSidebar"] div[data-baseweb="select"] > div {
            background-color: #182942 !important;
            border: 1px solid rgba(255, 255, 255, 0.18) !important;
            border-radius: 7px !important;
            color: #F8FAFC !important;
            min-height: 34px !important;
        }
        [data-testid="stSidebar"] div[data-baseweb="select"] span,
        [data-testid="stSidebar"] div[data-baseweb="select"] div {
            color: #F8FAFC !important;
            font-size: 12px !important;
        }
        [data-testid="stSidebar"] div[data-baseweb="select"] svg {
            color: #CBD5E1 !important;
            fill: #CBD5E1 !important;
        }

        /* 侧边栏折叠箭头 << 强制亮白可见 */
        [data-testid="stSidebarCollapseButton"] svg {
            color: #CBD5E1 !important;
            fill: #CBD5E1 !important;
        }

        /* 侧边栏防滚动与间距微调（杜绝账本标题被下拉框遮盖） */
        [data-testid="stSidebar"] > div:first-child {
            height: 100vh !important;
            max-height: 100vh !important;
            overflow-y: hidden !important;
        }
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
            gap: 0.38rem !important;
        }
    }

    /* 主区分段胶囊条：改用新版 Streamlit 真实容器 [data-testid="stMain"]（修复 .main 失效） */
    [data-testid="stMain"] div[role="radiogroup"],
    [data-testid="stMain"] [data-testid="stRadioGroup"][aria-orientation="horizontal"] {
        display: inline-flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        background-color: #DCE2EC !important;
        padding: 3px !important;
        border-radius: 8px !important;
        gap: 3px !important;
        width: fit-content !important;
        border: 1px solid #CBD5E1 !important;
    }
    [data-testid="stMain"] div[role="radiogroup"] label,
    [data-testid="stMain"] [data-testid="stRadioOption"] {
        background: transparent !important;
        padding: 5px 14px !important;
        border-radius: 6px !important;
        margin: 0 !important;
        cursor: pointer !important;
    }
    [data-testid="stMain"] div[role="radiogroup"] label p,
    [data-testid="stMain"] [data-testid="stRadioOption"] p {
        color: #475569 !important;
        font-size: 12.5px !important;
        font-weight: 500 !important;
        margin: 0 !important;
    }
    [data-testid="stMain"] div[role="radiogroup"] label:has(input:checked),
    [data-testid="stMain"] [data-testid="stRadioOption"][data-selected="true"] {
        background-color: #FFFFFF !important;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.10) !important;
    }
    [data-testid="stMain"] div[role="radiogroup"] label:has(input:checked) p,
    [data-testid="stMain"] [data-testid="stRadioOption"][data-selected="true"] p {
        color: #1B365D !important;
        font-weight: 700 !important;
    }

    /* 主区顶栏强制单行不折行（让 +录入 / 运维 / 撤回 牢牢贴在右侧同行） */
    @media (min-width: 769px) {
        div[data-testid="stHorizontalBlock"]:has(.topbar-outer-marker) {
            flex-wrap: nowrap !important;
            align-items: center !important;
        }
        div[data-testid="stHorizontalBlock"]:has(.topbar-outer-marker) > div[data-testid="column"]:last-child,
        div[data-testid="stHorizontalBlock"]:has(.topbar-outer-marker) > div[data-testid="stColumn"]:last-child {
            flex: 0 0 290px !important;
            min-width: 270px !important;
            max-width: 310px !important;
            width: 290px !important;
        }
    }
"""
# 注意：在 Python f-string 内部，花括号需要双重 {{ 和 }}
CSS_APPEND_ESCAPED = CSS_APPEND.replace("{", "{{").replace("}", "}}")

# 3. 自选板块 HTML 涨跌幅 !important 与账本与设置防遮挡
OLD_WATCHLIST_HTML = """        st.markdown(f'''<div style="display:flex;justify-content:space-between;align-items:center;padding:2px 8px;margin-bottom:2px;background:rgba(255,255,255,0.04);border-radius:4px;font-size:11px;line-height:22px;">
            <span style="font-weight:500;color:#E2E8F0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:110px;">{_sec.get('name', '')}</span>
            <span style="font-variant-numeric:tabular-nums;color:#64748B;font-size:10px;">{_sec.get('code', '')}</span>
            <span style="font-weight:700;color:{_scol};font-variant-numeric:tabular-nums;">{_ssign}{_spct:.2f}%</span>
        </div>''', unsafe_allow_html=True)

    st.markdown("<hr style='margin:6px 0;border:none;border-top:1px solid rgba(255,255,255,0.08);' />", unsafe_allow_html=True)

    # 3. 底部常驻区：当前激活账本 + 外观/刷新微按钮 (贴底布局)
    st.markdown("<div style='font-size:11px;font-weight:600;color:#94A3B8;margin-bottom:2px;'>账本与设置</div>", unsafe_allow_html=True)"""

NEW_WATCHLIST_HTML = """        st.markdown(f'''<div style="display:flex;justify-content:space-between;align-items:center;padding:3px 8px;margin-bottom:2px;background:rgba(255,255,255,0.05);border-radius:5px;font-size:11.5px;line-height:20px;">
            <span style="font-weight:500;color:#E2E8F0 !important;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:105px;">{_sec.get('name', '')}</span>
            <span style="font-variant-numeric:tabular-nums;color:#94A3B8 !important;font-size:10.5px;">{_sec.get('code', '')}</span>
            <span style="font-weight:700;color:{_scol} !important;font-variant-numeric:tabular-nums;min-width:52px;text-align:right;">{_ssign}{_spct:.2f}%</span>
        </div>''', unsafe_allow_html=True)

    st.markdown("<hr style='margin:6px 0;border:none;border-top:1px solid rgba(255,255,255,0.08);' />", unsafe_allow_html=True)

    # 3. 底部常驻区：当前激活账本 + 外观/刷新微按钮 (贴底布局 · 4px上边距彻底防重叠)
    st.markdown("<div style='font-size:11px;font-weight:600;color:#94A3B8 !important;margin:4px 0 6px 0;line-height:1.4;display:block;'>账本与设置</div>", unsafe_allow_html=True)"""

# 4. 主区顶栏单行右对齐
OLD_TOPBAR_COL = """col_top_title, col_top_actions = st.columns([7.2, 2.8])
with col_top_title:
    safe_markdown_html('<span class="topbar-outer-marker"></span>')
    _cur_page_name = st.session_state.get("desktop_nav_tab", "持仓")
    _active_m = mlm_inst.get_ledger_meta(active_lid) or {}
    _l_tag = "[实盘]" if _active_m.get("type") == "live" else ("[沙盒]" if _active_m.get("type") == "sandbox" else "[家庭]")
    _l_name = str(_active_m.get("name", active_lid))
    _guide_map = {
        "持仓": "查看今日盈亏、核对估值与体检风险",
        "调仓": "照单执行买卖、一键小抄与打卡追踪",
        "复盘": "Point-in-Time 历史时光机与前瞻验真",
        "工具": "资产穿透、行业重叠与全天候体检"
    }
    _cur_guide = _guide_map.get(_cur_page_name, "智能投顾工作台")
    safe_markdown_html(f\"\"\"<div style="display:flex;align-items:center;gap:8px;padding-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
        <span style="font-size:15px;font-weight:700;color:var(--text-primary);">{_cur_page_name}工作台</span>
        <span style="font-size:12px;color:var(--text-muted);">·</span>
        <span style="font-size:12px;color:var(--text-secondary);font-weight:500;">{_l_tag} {_l_name}</span>
        <span style="font-size:11px;color:var(--text-muted);margin-left:4px;">｜ {_cur_guide}</span>
    </div>\"\"\")

with col_top_actions:
    col_pop_in, col_pop_ops, col_pop_rv = st.columns([1.3, 1.3, 1.3])"""

NEW_TOPBAR_COL = """col_top_title, col_top_actions = st.columns([6.2, 3.8])
with col_top_title:
    safe_markdown_html('<span class="topbar-outer-marker"></span>')
    _cur_page_name = st.session_state.get("desktop_nav_tab", "持仓")
    _active_m = mlm_inst.get_ledger_meta(active_lid) or {}
    _l_tag = "[实盘]" if _active_m.get("type") == "live" else ("[沙盒]" if _active_m.get("type") == "sandbox" else "[家庭]")
    _l_name = str(_active_m.get("name", active_lid))
    _guide_map = {
        "持仓": "查看今日盈亏、核对估值与体检风险",
        "调仓": "照单执行买卖、一键小抄与打卡追踪",
        "复盘": "Point-in-Time 历史时光机与前瞻验真",
        "工具": "资产穿透、行业重叠与全天候体检"
    }
    _cur_guide = _guide_map.get(_cur_page_name, "智能投顾工作台")
    safe_markdown_html(f\"\"\"<div style="display:flex;align-items:center;gap:8px;padding-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
        <span style="font-size:15px;font-weight:700;color:var(--text-primary);">{_cur_page_name}工作台</span>
        <span style="font-size:12px;color:var(--text-muted);">·</span>
        <span style="font-size:12px;color:var(--text-secondary);font-weight:500;">{_l_tag} {_l_name}</span>
        <span style="font-size:11px;color:var(--text-muted);margin-left:4px;">｜ {_cur_guide}</span>
    </div>\"\"\")

with col_top_actions:
    col_pop_in, col_pop_ops, col_pop_rv = st.columns([1.2, 1.0, 1.0], gap="small")"""

# 5. 红黑榜 2 字精炼短标
OLD_MOVERS_HTML = """        cols = st.columns(2)
        with cols[0]:
            if gainers:
                g_str = " ".join([f"<span style='color:#DC2626;background:rgba(220,38,38,0.08);padding:2px 6px;border-radius:4px;font-size:11px;font-weight:600;white-space:nowrap;'>▲ {x['name'][:4]} {x['chg']:+.2f}%</span>" for x in gainers[:3]])
                safe_markdown_html(f"<div style='margin-bottom:6px;display:flex;align-items:center;white-space:nowrap;overflow:hidden;gap:6px;'><span style='font-size:11.5px;font-weight:700;color:var(--text-secondary);flex-shrink:0;'>今日贡献 Top:</span><div style='display:flex;gap:4px;overflow:hidden;'>{g_str}</div></div>")
        with cols[1]:
            if losers:
                l_str = " ".join([f"<span style='color:#15803D;background:rgba(21,128,61,0.08);padding:2px 6px;border-radius:4px;font-size:11px;font-weight:600;white-space:nowrap;'>▼ {x['name'][:4]} {x['chg']:+.2f}%</span>" for x in losers[:3]])
                safe_markdown_html(f"<div style='margin-bottom:6px;display:flex;align-items:center;justify-content:flex-end;white-space:nowrap;overflow:hidden;gap:6px;'><span style='font-size:11.5px;font-weight:700;color:var(--text-secondary);flex-shrink:0;'>领跌拖累:</span><div style='display:flex;gap:4px;overflow:hidden;'>{l_str}</div></div>")"""

NEW_MOVERS_HTML = """        cols = st.columns(2)
        with cols[0]:
            if gainers:
                g_str = " ".join([f"<span style='color:#DC2626;background:rgba(220,38,38,0.08);padding:2px 6px;border-radius:4px;font-size:11px;font-weight:600;white-space:nowrap;'>▲ {x['name'][:4]} {x['chg']:+.2f}%</span>" for x in gainers[:3]])
                safe_markdown_html(f"<div style='margin-bottom:6px;display:flex;align-items:center;white-space:nowrap;overflow:hidden;gap:6px;'><span style='font-size:11.5px;font-weight:700;color:var(--text-secondary);flex-shrink:0;'>领涨:</span><div style='display:flex;gap:4px;overflow:hidden;'>{g_str}</div></div>")
        with cols[1]:
            if losers:
                l_str = " ".join([f"<span style='color:#15803D;background:rgba(21,128,61,0.08);padding:2px 6px;border-radius:4px;font-size:11px;font-weight:600;white-space:nowrap;'>▼ {x['name'][:4]} {x['chg']:+.2f}%</span>" for x in losers[:3]])
                safe_markdown_html(f"<div style='margin-bottom:6px;display:flex;align-items:center;justify-content:flex-end;white-space:nowrap;overflow:hidden;gap:6px;'><span style='font-size:11.5px;font-weight:700;color:var(--text-secondary);flex-shrink:0;'>领跌:</span><div style='display:flex;gap:4px;overflow:hidden;'>{l_str}</div></div>")"""

# 6. 持仓主表 7 列黄金视图与废话 caption 删除 + 底部紧凑 4 列
OLD_TABLE_BLOCK = """                if sub_hold_view == "持仓明细":
                    _render_daily_movers_strip(pm)
                    nav_status_tip = "已收盘公布官方净值与实际涨跌" if is_official_nav_holdings else "盘中实时估值双轨对账中"
                    st.caption(f"实时持仓资产明细（{nav_status_tip}，支持直接编辑代码与金额，保存时后台自动联网补齐净值与指标）：")
                    if not df_disp.empty:
                        clean_df_disp = df_disp.loc[:, ~df_disp.columns.duplicated(keep="last")]
                        edited_table = st.data_editor(
                            clean_df_disp,
                            column_config={
                                "基金代码": st.column_config.TextColumn(max_chars=6, required=True),
                                "基金名称": st.column_config.TextColumn(disabled=True),
                                "当前市值(元)": st.column_config.NumberColumn(format="¥%.2f", min_value=0.0),
                                "当前赎回费率(%)": st.column_config.NumberColumn(format="%.2f%%", disabled=True),
                                "赎回费状态": st.column_config.TextColumn(disabled=True),
                                "累计盈亏(元)": st.column_config.NumberColumn(format="¥%+.2f", disabled=True),
                                "浮动盈亏率(%)": st.column_config.NumberColumn(format="%+.2f%%", disabled=True),
                                "当日估算(%)": st.column_config.TextColumn("当日估算(%)", disabled=True),
                                "官方涨跌(对比)": st.column_config.TextColumn("官方涨跌(对比)", disabled=True),
                                col_holdings_chg: st.column_config.NumberColumn(
                                    col_holdings_chg,
                                    help="官方公布净值后为当日官方实际涨跌(%)；盘中时段为盘中实时估值(%)。",
                                    format="%+.2f%%",
                                    disabled=True
                                ),
                            },
                            use_container_width=True,
                            hide_index=True,
                            num_rows="dynamic",
                            key="main_holdings_editor_tab2"
                        )
                    col_op1, col_op2, col_op3 = st.columns([4, 3, 3])"""

NEW_TABLE_BLOCK = """                if sub_hold_view == "持仓明细":
                    _render_daily_movers_strip(pm)
                    if not df_disp.empty:
                        clean_df_disp = df_disp.loc[:, ~df_disp.columns.duplicated(keep="last")].copy()
                        # 仅保留纯净今日涨跌数值列，剥离冗长的估算来源括号说明（来源细节统一在「估值对账」查看）
                        if col_holdings_chg in clean_df_disp.columns:
                            clean_df_disp["今日涨跌(%)"] = pd.to_numeric(clean_df_disp[col_holdings_chg], errors="coerce").fillna(0.0)
                        elif "今日实时估值涨跌(%)" in clean_df_disp.columns:
                            clean_df_disp["今日涨跌(%)"] = pd.to_numeric(clean_df_disp["今日实时估值涨跌(%)"], errors="coerce").fillna(0.0)
                        else:
                            clean_df_disp["今日涨跌(%)"] = 0.0

                        core_7_cols = [
                            c for c in [
                                "基金代码", "基金名称", "当前市值(元)", "今日涨跌(%)",
                                "浮动盈亏率(%)", "最短持有天数", "赎回费状态"
                            ]
                            if c in clean_df_disp.columns
                        ]
                        edited_table = st.data_editor(
                            clean_df_disp,
                            column_order=core_7_cols,
                            column_config={
                                "基金代码": st.column_config.TextColumn("代码", width="small", max_chars=6, required=True),
                                "基金名称": st.column_config.TextColumn("基金名称", width="medium", disabled=True),
                                "当前市值(元)": st.column_config.NumberColumn("当前市值", format="¥%.2f", min_value=0.0),
                                "今日涨跌(%)": st.column_config.NumberColumn("今日涨跌", format="%+.2f%%", disabled=True),
                                "浮动盈亏率(%)": st.column_config.NumberColumn("累计盈亏", format="%+.2f%%", disabled=True),
                                "最短持有天数": st.column_config.NumberColumn("持有天数", format="%d天", disabled=True),
                                "赎回费状态": st.column_config.TextColumn("赎回状态", disabled=True),
                            },
                            use_container_width=True,
                            hide_index=True,
                            num_rows="dynamic",
                            key="main_holdings_editor_tab2"
                        )
                    col_op1, col_op2, col_op3, _col_op_blank = st.columns([1.4, 1.2, 1.4, 6.0])"""

# 7. 右栏高危风控哨零硬切 + 今日操作路线纯净圆点
OLD_RIGHT_RAIL = """                # 高危风控哨 Top 3
                _s_alerts = _sentry_scan.get("alerts", []) if isinstance(_sentry_scan, dict) else []
                if _s_alerts:
                    safe_markdown_html(\"\"\"<div style="font-size:13px;font-weight:700;color:var(--text-primary);margin:14px 0 6px 0;">高危风控哨</div>\"\"\")
                    for _alt in _s_alerts[:3]:
                        _a_lvl = _alt.get("level", "yellow")
                        _a_dot = "#DC2626" if _a_lvl == "red" else ("#F59E0B" if _a_lvl == "yellow" else "#1D4ED8")
                        _a_msg = _alt.get("title") or _alt.get("message", "")
                        safe_markdown_html(f\"\"\"
                        <div style="background:#FFFFFF;border:1px solid #E5E9F0;border-radius:8px;padding:8px 10px;margin-bottom:6px;font-size:11px;line-height:1.4;">
                            <span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:{_a_dot};margin-right:6px;"></span>
                            <b>{_alt.get('dimension', '风控')}</b>: {_a_msg[:36]}
                        </div>
                        \"\"\")

                # 参数微调 (折叠)
                with st.expander("参数微调", expanded=False):
                    _cur_buf_val = float(st.session_state.get("rebalance_buffer_pct", 3.0))
                    def _sync_tab2_rebal_buffer_change():
                        st.session_state.rebalance_buffer_pct = float(st.session_state.tab2_rebal_buf_slider)
                        st.session_state.tab2_diag_cache = None
                        st.session_state.tab2_rebal_cache = None
                    st.slider(
                        "免折腾缓冲带(%)",
                        min_value=1.0,
                        max_value=5.0,
                        value=_cur_buf_val,
                        step=0.5,
                        format="%.1f%%",
                        key="tab2_rebal_buf_slider",
                        on_change=_sync_tab2_rebal_buffer_change,
                        help="控制调仓裁决与温和调仓过滤的最小偏离阈值。低于此阈值的微小偏离将自动维持现状，杜绝无效换仓摩擦"
                    )

                # 今日操作路线（3步）导流闭环卡（填补右栏留白并指引用户行动）
                safe_markdown_html(\"\"\"
                <div style="background:#FFFFFF;border:1px solid #DCE3ED;border-radius:10px;padding:12px 14px;margin-top:10px;box-shadow:0 1px 3px rgba(15,23,42,0.04);">
                    <div style="font-size:12px;font-weight:700;color:#0F172A;margin-bottom:8px;">今日操作路线（3步）</div>
                    <div style="font-size:11.5px;color:#15803D;margin-bottom:6px;display:flex;align-items:center;gap:6px;">
                        <span>✅</span><span>1. 同步最新持仓与实时双轨估值</span>
                    </div>
                    <div style="font-size:11.5px;color:#C29648;font-weight:600;margin-bottom:6px;display:flex;align-items:center;gap:6px;">
                        <span>⚡</span><span>2. 查看风控哨与三阶重塑方案（当前）</span>
                    </div>
                    <div style="font-size:11.5px;color:#64748B;display:flex;align-items:center;gap:6px;">
                        <span>⏳</span><span>3. 前往调仓页执行打卡与小抄复制</span>
                    </div>
                </div>
                \"\"\")"""

NEW_RIGHT_RAIL = """                # 高危风控哨 Top 3（结构化 2 行卡片 · 零暴力截断）
                _s_alerts = _sentry_scan.get("alerts", []) if isinstance(_sentry_scan, dict) else []
                if _s_alerts:
                    safe_markdown_html(\"\"\"<div style="font-size:13px;font-weight:700;color:var(--text-primary);margin:14px 0 6px 0;">高危风控哨</div>\"\"\")
                    for _alt in _s_alerts[:3]:
                        _a_lvl = _alt.get("level", "yellow")
                        _a_dot = "#C81E1E" if _a_lvl == "red" else ("#D97706" if _a_lvl == "yellow" else "#1B3A6B")
                        _raw_title = str(_alt.get("title") or _alt.get("dimension") or "风控提醒")
                        _clean_title = _raw_title.replace("【", "").replace("】", "")
                        _raw_sug = str(_alt.get("suggestion") or _alt.get("advice") or _alt.get("message") or "请前往调仓页核查处理")
                        safe_markdown_html(f\"\"\"
                        <div style="background:#FFFFFF;border:1px solid #DCE3ED;border-radius:8px;padding:8px 10px;margin-bottom:6px;box-shadow:0 1px 2px rgba(15,23,42,0.03);">
                            <div style="display:flex;align-items:center;gap:6px;font-size:12px;font-weight:700;color:#0F172A;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                                <span style="flex-shrink:0;width:6px;height:6px;border-radius:50%;background:{_a_dot};"></span>
                                <span style="overflow:hidden;text-overflow:ellipsis;">{_clean_title}</span>
                            </div>
                            <div style="font-size:11px;color:#64748B;margin-top:3px;padding-left:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                                {_raw_sug}
                            </div>
                        </div>
                        \"\"\")

                # 参数微调 (折叠)
                with st.expander("参数微调", expanded=False):
                    _cur_buf_val = float(st.session_state.get("rebalance_buffer_pct", 3.0))
                    def _sync_tab2_rebal_buffer_change():
                        st.session_state.rebalance_buffer_pct = float(st.session_state.tab2_rebal_buf_slider)
                        st.session_state.tab2_diag_cache = None
                        st.session_state.tab2_rebal_cache = None
                    st.slider(
                        "免折腾缓冲带(%)",
                        min_value=1.0,
                        max_value=5.0,
                        value=_cur_buf_val,
                        step=0.5,
                        format="%.1f%%",
                        key="tab2_rebal_buf_slider",
                        on_change=_sync_tab2_rebal_buffer_change,
                        help="控制调仓裁决与温和调仓过滤的最小偏离阈值。低于此阈值的微小偏离将自动维持现状，杜绝无效换仓摩擦"
                    )

                # 今日操作路线（3步）导流闭环卡（优雅 6px 纯净状态圆点 · 填补右栏留白并指引用户行动）
                safe_markdown_html(\"\"\"
                <div style="background:#FFFFFF;border:1px solid #DCE3ED;border-radius:10px;padding:12px 14px;margin-top:10px;box-shadow:0 1px 3px rgba(15,23,42,0.04);">
                    <div style="font-size:12px;font-weight:700;color:#0F172A;margin-bottom:8px;">今日操作路线（3步）</div>
                    <div style="font-size:11.5px;color:#15803D;margin-bottom:6px;display:flex;align-items:center;gap:8px;">
                        <span style="width:6px;height:6px;border-radius:50%;background:#15803D;flex-shrink:0;"></span><span>1. 同步最新持仓与实时双轨估值</span>
                    </div>
                    <div style="font-size:11.5px;color:#C29648;font-weight:600;margin-bottom:6px;display:flex;align-items:center;gap:8px;">
                        <span style="width:6px;height:6px;border-radius:50%;background:#C29648;flex-shrink:0;"></span><span>2. 查看风控哨与三阶重塑方案（当前）</span>
                    </div>
                    <div style="font-size:11.5px;color:#64748B;display:flex;align-items:center;gap:8px;">
                        <span style="width:6px;height:6px;border-radius:50%;background:#94A3B8;flex-shrink:0;"></span><span>3. 前往调仓页执行打卡与小抄复制</span>
                    </div>
                </div>
                \"\"\")"""

for target in targets:
    if not target.exists():
        continue
    content = target.read_text(encoding="utf-8")
    
    # 1. 替换 span 规则
    assert OLD_SPAN_RULE in content, f"OLD_SPAN_RULE not found in {target}"
    content = content.replace(OLD_SPAN_RULE, NEW_SPAN_RULE)
    
    # 2. 追加终极 CSS 到 </style> 前
    assert "</style>\n\"\"\")" in content, f"</style> anchor not found in {target}"
    content = content.replace("</style>\n\"\"\")", CSS_APPEND_ESCAPED + "\n</style>\n\"\"\")")
    
    # 3. 替换自选板块 HTML
    assert OLD_WATCHLIST_HTML in content, f"OLD_WATCHLIST_HTML not found in {target}"
    content = content.replace(OLD_WATCHLIST_HTML, NEW_WATCHLIST_HTML)
    
    # 4. 替换顶栏列宽
    assert OLD_TOPBAR_COL in content, f"OLD_TOPBAR_COL not found in {target}"
    content = content.replace(OLD_TOPBAR_COL, NEW_TOPBAR_COL)
    
    # 5. 替换红黑榜 2 字短标
    assert OLD_MOVERS_HTML in content, f"OLD_MOVERS_HTML not found in {target}"
    content = content.replace(OLD_MOVERS_HTML, NEW_MOVERS_HTML)
    
    # 6. 替换持仓主表 7 列黄金视图
    assert OLD_TABLE_BLOCK in content, f"OLD_TABLE_BLOCK not found in {target}"
    content = content.replace(OLD_TABLE_BLOCK, NEW_TABLE_BLOCK)
    
    # 7. 替换右栏风控哨与今日操作路线
    assert OLD_RIGHT_RAIL in content, f"OLD_RIGHT_RAIL not found in {target}"
    content = content.replace(OLD_RIGHT_RAIL, NEW_RIGHT_RAIL)
    
    # AST 语法解析
    ast.parse(content, filename=str(target))
    target.write_text(content, encoding="utf-8")
    print(f"[OK] Successfully patched all 7 G41 UI/UX defects in {target}")
