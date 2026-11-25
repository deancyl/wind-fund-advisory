import sys
from pathlib import Path

gui_path = Path("AGY2_FundAdvisory/app_gui.py")
content = gui_path.read_text(encoding="utf-8")

print(f"Original content length: {len(content)}")

# 1. Add import streamlit.components.v1 as components
old_import = "import streamlit as st\nfrom typing import Any, Callable, Dict, List, Optional, Tuple"
new_import = "import streamlit as st\nimport streamlit.components.v1 as components\nfrom typing import Any, Callable, Dict, List, Optional, Tuple"
assert old_import in content, "old_import not found"
content = content.replace(old_import, new_import, 1)

# 2. Add format_chinese_amount, UncommittedCheckResult, _has_uncommitted_holdings_changes
target_func_marker = '''def map_slider_to_tier(ret: float) -> str:
    """统一委托 strategy_bridge.map_target_return_to_tier，消除重复定义与档位漂移"""
    return map_target_return_to_tier(ret)'''
assert target_func_marker in content, "target_func_marker not found"

helpers_code = '''


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

    if abs_v >= 100_000_000:
        yi_v = abs_v / 100_000_000.0
        wan_v = abs_v / 10_000.0
        return f"{standard_str} 折合 {sign}{wan_v:,.2f} 万元 ({sign}{yi_v:,.2f} 亿元)"
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
'''
content = content.replace(target_func_marker, target_func_marker + helpers_code, 1)

# 3. Morning pulse card & Top 3 sector cards & Dual-wing DOM routing
old_morning_pulse = '''                safe_markdown_html(f"""
                <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 12px 14px; margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <span style="font-size: 13.5px; font-weight: 700; color: var(--text-primary);">🌅 今日大盘脉搏 & 胜率天平</span>
                        <span style="font-size: 11px; padding: 2px 8px; border-radius: 4px; background: rgba(37, 99, 235, 0.12); color: var(--accent-primary); font-weight: 600;">{m_stage}</span>
                    </div>
                    <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.6;">
                        • <b>两市成交额</b>：¥{m_turnover:,.0f} 亿 ｜ <b>情绪温度</b>：{m_temp:.1f}℃ ({m_sent_desc})<br>
                        • <b>全A均值回归状态</b>：{m_bias_desc} (20日乖离率 {m_bias20:+.2f}%) ｜ <b>波幅状态</b>：{m_vol_desc}<br>
                        • <b>动态调仓缓冲带基准</b>：系统已自动匹配为 <b>{m_rec_buf:.1f}%</b>，兼顾进攻弹性与防摩擦。
                    </div>
                </div>
                """)'''

new_morning_pulse = '''                news_res = DataLoader.fetch_realtime_market_news_and_catalysts()
                news_items = news_res.get("news", [])
                latest_flash = news_items[0]["title"] if news_items else "A股主要指数处于关键均线右侧蓄势期，增量资金积极聚焦高股息红利与核心宽基。"
                data_sense_time = news_res.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

                safe_markdown_html(f"""
                <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 12px 14px; margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <span style="font-size: 13.5px; font-weight: 700; color: var(--text-primary);">🌅 今日大盘脉搏 & 胜率天平</span>
                        <div style="display: flex; gap: 8px; align-items: center;">
                            <span style="font-size: 11px; color: var(--text-secondary);">⏱️ 数据感知时间: {data_sense_time}</span>
                            <span style="font-size: 11px; padding: 2px 8px; border-radius: 4px; background: rgba(37, 99, 235, 0.12); color: var(--accent-primary); font-weight: 600;">{m_stage}</span>
                        </div>
                    </div>
                    <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.6;">
                        • <b>两市成交额</b>：¥{m_turnover:,.0f} 亿 ｜ <b>情绪温度</b>：{m_temp:.1f}℃ ({m_sent_desc})<br>
                        • <b>全A均值回归状态</b>：{m_bias_desc} (20日乖离率 {m_bias20:+.2f}%) ｜ <b>波幅状态</b>：{m_vol_desc}<br>
                        • <b>动态调仓缓冲带基准</b>：系统已自动匹配为 <b>{m_rec_buf:.1f}%</b>，兼顾进攻弹性与防摩擦。<br>
                        • <b>⚡ 实时快讯</b>：<span style="color: var(--accent-primary);">{latest_flash}</span>
                    </div>
                </div>
                """)'''
assert old_morning_pulse in content, "old_morning_pulse not found"
content = content.replace(old_morning_pulse, new_morning_pulse, 1)

old_top3_card = '''                        sec_name = sec.get("name", "赛道")
                        sec_score = sec.get("total_score", 50.0)
                        sec_funds = sec.get("representative_funds", [])
                        f_rep = sec_funds[0] if sec_funds else {"code": "005561", "name": "核心指数标的"}
                        
                        safe_markdown_html(f"""
                        <div style="background: var(--bg-surface); border: 1.5px solid var(--accent-primary); border-radius: 8px; padding: 10px 12px; margin-bottom: 8px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                                <span style="font-weight: 700; color: var(--text-primary); font-size: 13px;">🏆 {i+1}. {sec_name}</span>
                                <span style="font-size: 11px; font-weight: 700; color: var(--accent-primary); background: rgba(37, 99, 235, 0.12); padding: 2px 6px; border-radius: 4px;">胜率评分 {sec_score:.1f}分</span>
                            </div>
                            <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 6px;">
                                标杆代表基：<b>{f_rep.get('name')}</b> (<code>{f_rep.get('code')}</code>) ｜ 估值分位 {sec.get('val_percentile', 50):.1f}%
                            </div>
                        </div>
                        """)'''

new_top3_card = '''                        sec_name = sec.get("name", "赛道")
                        sec_score = sec.get("total_score", 50.0)
                        sec_funds = sec.get("representative_funds", [])
                        f_rep = sec_funds[0] if sec_funds else {"code": "005561", "name": "核心指数标的"}
                        rt_chg = sec.get("realtime_chg_pct", 0.0)
                        rt_pt = sec.get("realtime_point", 0.0)
                        core_logic_txt = sec.get("core_logic", "四维胜率模型综合打分靠前")
                        sub_s = sec.get("sub_scores", {})
                        
                        rt_color = active_co["color_up"] if rt_chg >= 0 else active_co["color_down"]
                        pt_disp = f" ({rt_pt:.1f}点)" if rt_pt > 0 else ""
                        
                        safe_markdown_html(f"""
                        <div style="background: var(--bg-surface); border: 1.5px solid var(--accent-primary); border-radius: 8px; padding: 10px 12px; margin-bottom: 8px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                                <span style="font-weight: 700; color: var(--text-primary); font-size: 13px;">🏆 {i+1}. {sec_name}</span>
                                <div style="display: flex; gap: 6px; align-items: center;">
                                    <span style="font-size: 11px; font-weight: 700; color: {rt_color};">实时: {rt_chg:+.2f}%{pt_disp}</span>
                                    <span style="font-size: 11px; font-weight: 700; color: var(--accent-primary); background: rgba(37, 99, 235, 0.12); padding: 2px 6px; border-radius: 4px;">综合 {sec_score:.1f}分</span>
                                </div>
                            </div>
                            <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 4px;">
                                标杆代表基：<b>{f_rep.get('name')}</b> (<code>{f_rep.get('code')}</code>) ｜ 估值分位 {sec.get('val_percentile', 50):.1f}% ｜ 动量 {sub_s.get('momentum', 0.0):.0f}分 ｜ 抗拥挤 {sub_s.get('anti_crowding', 0.0):.0f}分
                            </div>
                            <div style="font-size: 11px; color: var(--text-primary); background: var(--bg-elevated); padding: 4px 8px; border-radius: 4px; margin-bottom: 6px;">
                                💡 <b>入选依据</b>：{core_logic_txt}
                            </div>
                        </div>
                        """)'''
assert old_top3_card in content, "old_top3_card not found"
content = content.replace(old_top3_card, new_top3_card, 1)

old_radar_btn = '''                        if st.button(f"➕ 将【{f_rep.get('code')}】加入建仓备选池", key=f"btn_add_radar_pool_{i}", use_container_width=True):
                            add_custom_watchlist_fund(f_rep.get("code"), f_rep.get("name"))
                            st.toast(f"✅ 已将【{f_rep.get('code')}】纳入我的自定义关注/备选池！")'''

new_radar_btn = '''                        if st.button(f"➕ 将【{f_rep.get('code')}】加入建仓备选池", key=f"btn_add_radar_pool_{i}", use_container_width=True):
                            add_custom_watchlist_fund(f_rep.get("code"), f_rep.get("name"))
                            st.session_state["pending_cross_tab_jump"] = {
                                "tab_index": 0,
                                "tab_name": "🌱 新资建仓",
                                "action_name": "入备选池",
                                "target_title": f"{f_rep.get('name')} ({f_rep.get('code')})",
                                "detail": "已自动注入关注池并聚焦至新资建仓配置引擎",
                                "timestamp": datetime.now().strftime("%H:%M:%S")
                            }
                            st.session_state["last_cross_tab_action"] = dict(st.session_state["pending_cross_tab_jump"])
                            st.toast(f"✅ 已将【{f_rep.get('code')}】纳入备选池，正在为您导向新资建仓！")
                            st.rerun()'''
assert old_radar_btn in content, "old_radar_btn not found"
content = content.replace(old_radar_btn, new_radar_btn, 1)

old_sentry_header = '''                safe_markdown_html("""
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div style="font-size: 14px; font-weight: 700; color: var(--text-primary);">
                        🚨 实盘主动风险预警哨 <span style="font-size: 11px; font-weight: 400; color: var(--text-secondary);">[主动风险预警哨 · 四维巡检升级版]</span>
                    </div>
                </div>
                """)

                # 预警哨处置按钮与证据链穿透逻辑
                sentry_alerts = ActiveRiskSentry.scan_portfolio_risks(pm, market_snapshot=snapshot)
                if sentry_alerts:
                    alert_count = len(sentry_alerts)
                    col_st_msg, col_st_lock = st.columns([7, 3])
                    with col_st_msg:
                        safe_markdown_html(f"""
                        <div style="background: rgba(239, 68, 68, 0.12); border-left: 3px solid var(--color-up); padding: 8px 12px; border-radius: 4px; font-size: 12px; margin-bottom: 8px;">
                            <b>巡检报警</b>：在当前持仓中探测到 <b>{alert_count} 项主动风控预警</b>，建议及时采取保护动作。
                        </div>
                        """)
                    with col_st_lock:
                        if st.button("🔒 一键批量锁定", key="btn_sentry_batch_lock", use_container_width=True, help="将所有存在 <7天或临界免赎标的全部加入锁仓白名单，调仓时强制禁卖"):
                            lock_candidates = []
                            for a in sentry_alerts:
                                fc = a.get("fund_code")
                                if fc and fc in pm.holdings:
                                    lock_candidates.append(fc)
                            st.session_state.tab2_locked_funds = list(set((st.session_state.get("tab2_locked_funds") or []) + lock_candidates))
                            st.toast(f"✅ 已成功锁定 {len(lock_candidates)} 只风险标的！")
                            st.rerun()

                    for a_idx, alt in enumerate(sentry_alerts):
                        lvl = alt.get("level", "YELLOW")
                        lvl_c = "var(--color-up)" if lvl == "RED" else "#ca8a04"
                        lvl_bg = "rgba(239, 68, 68, 0.08)" if lvl == "RED" else "rgba(234, 179, 8, 0.08)"
                        a_title = alt.get("title", "持仓风险")
                        a_desc = alt.get("description", "")
                        a_act = alt.get("action_suggest", "建议复核")
                        f_code = alt.get("fund_code", "")
                        f_name = alt.get("fund_name", "")

                        safe_markdown_html(f"""
                        <div style="background: {lvl_bg}; border: 1px solid {lvl_c}; border-radius: 6px; padding: 10px 12px; margin-bottom: 6px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                                <span style="font-weight: 700; color: {lvl_c}; font-size: 12.5px;">⚠️ {a_title}</span>
                                <span style="font-size: 11px; color: var(--text-secondary);">{f_name} (<code>{f_code}</code>)</span>
                            </div>
                            <div style="font-size: 11.5px; color: var(--text-primary); line-height: 1.5; margin-bottom: 6px;">
                                {a_desc}
                            </div>
                            <div style="font-size: 11px; color: {lvl_c}; font-weight: 600;">
                                💡 建议应对动作：{a_act}
                            </div>
                        </div>
                        """)

                        # 动作派发按钮
                        col_alt_act, col_alt_evid = st.columns([5, 5])
                        with col_alt_act:
                            if st.button(f"⚡ 执行应对: {a_act.split('(')[0]}", key=f"btn_sentry_act_{a_idx}_{f_code}", use_container_width=True):
                                # 派发主动风控指令至 Tab 2 调仓方案
                                if alt.get("action_type") == "lock":
                                    st.session_state.tab2_locked_funds = list(set((st.session_state.get("tab2_locked_funds") or []) + [f_code]))
                                    st.toast(f"✅ 已对【{f_code}】下达锁仓保护指令，调仓方案已物理禁卖该标的！")
                                elif alt.get("action_type") == "take_profit":
                                    st.session_state.tab2_pending_take_profit = {"fund_code": f_code, "ratio": 0.4}
                                    st.toast(f"✅ 已对【{f_code}】下达阶梯止盈指令！")
                                elif alt.get("action_type") == "c_replace":
                                    st.session_state.tab2_c_replace = f_code
                                    st.toast(f"✅ 已对【{f_code}】下达低费率 A 类置换指令！")
                                st.rerun()

                        with col_alt_evid:
                            if st.button(f"🔍 穿透到底层", key=f"btn_sentry_evid_{a_idx}_{f_code}", use_container_width=True):
                                # 联动激活 Tab 4 工具箱对应模块
                                st.session_state.tab4_highlight_module = alt.get("highlight_module", "overview")
                                st.session_state.tab4_highlight_fund = f_code
                                st.toast(f"🔍 已锁定【{f_code}】底层数据，请切换至 Tab 4 检视排雷证据！")'''

new_sentry_header = '''                safe_markdown_html("""
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div style="font-size: 14px; font-weight: 700; color: var(--text-primary);">
                        🚨 实盘主动风险预警哨
                    </div>
                </div>
                """)

                # 预警哨处置按钮与证据链穿透逻辑 (限制高度为 380px，支持独立平滑滚动)
                sentry_alerts = ActiveRiskSentry.scan_portfolio_risks(pm, market_snapshot=snapshot)
                with st.container(height=380):
                    if sentry_alerts:
                        alert_count = len(sentry_alerts)
                        col_st_msg, col_st_lock = st.columns([7, 3])
                        with col_st_msg:
                            safe_markdown_html(f"""
                            <div style="background: rgba(239, 68, 68, 0.12); border-left: 3px solid var(--color-up); padding: 8px 12px; border-radius: 4px; font-size: 12px; margin-bottom: 8px;">
                                <b>巡检报警</b>：在当前持仓中探测到 <b>{alert_count} 项主动风控预警</b>，建议及时采取保护动作。
                            </div>
                            """)
                        with col_st_lock:
                            if st.button("🔒 一键批量锁定", key="btn_sentry_batch_lock", use_container_width=True, help="将所有存在 <7天或临界免赎标的全部加入锁仓白名单，调仓时强制禁卖"):
                                lock_candidates = []
                                for a in sentry_alerts:
                                    fc = a.get("fund_code")
                                    if fc and fc in pm.holdings:
                                        lock_candidates.append(fc)
                                st.session_state.tab2_locked_funds = list(set((st.session_state.get("tab2_locked_funds") or []) + lock_candidates))
                                st.session_state["pending_cross_tab_jump"] = {
                                    "tab_index": 1,
                                    "tab_name": "💼 持仓调仓",
                                    "action_name": "批量锁仓保护",
                                    "target_title": f"批量锁定 {len(lock_candidates)} 只标的",
                                    "detail": "已下达持仓下界禁卖风控指令，为您导向持仓调仓",
                                    "timestamp": datetime.now().strftime("%H:%M:%S")
                                }
                                st.session_state["last_cross_tab_action"] = dict(st.session_state["pending_cross_tab_jump"])
                                st.toast(f"✅ 已成功锁定 {len(lock_candidates)} 只风险标的！")
                                st.rerun()

                        for a_idx, alt in enumerate(sentry_alerts):
                            lvl = alt.get("level", "YELLOW")
                            lvl_c = "var(--color-up)" if lvl == "RED" else "#ca8a04"
                            lvl_bg = "rgba(239, 68, 68, 0.08)" if lvl == "RED" else "rgba(234, 179, 8, 0.08)"
                            a_title = alt.get("title", "持仓风险")
                            a_desc = alt.get("description", "")
                            a_act = alt.get("action_suggest", "建议复核")
                            f_code = alt.get("fund_code", "")
                            f_name = alt.get("fund_name", "")
                            act_t = alt.get("action_type", "lock")

                            safe_markdown_html(f"""
                            <div style="background: {lvl_bg}; border: 1px solid {lvl_c}; border-radius: 6px; padding: 10px 12px; margin-bottom: 6px;">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                                    <span style="font-weight: 700; color: {lvl_c}; font-size: 12.5px;">⚠️ {a_title}</span>
                                    <span style="font-size: 11px; color: var(--text-secondary);">{f_name} (<code>{f_code}</code>)</span>
                                </div>
                                <div style="font-size: 11.5px; color: var(--text-primary); line-height: 1.5; margin-bottom: 6px;">
                                    {a_desc}
                                </div>
                                <div style="font-size: 11px; color: {lvl_c}; font-weight: 600;">
                                    💡 建议应对动作：{a_act}
                                </div>
                            </div>
                            """)

                            # 动作派发按钮
                            col_alt_act, col_alt_evid = st.columns([5, 5])
                            with col_alt_act:
                                if st.button(f"⚡ 执行应对: {a_act.split('(')[0]}", key=f"btn_sentry_act_{a_idx}_{f_code}", use_container_width=True):
                                    # 派发主动风控指令至 Tab 2 调仓方案 (支持 6 大处置类型参数透传)
                                    if act_t in ["lock", "countdown_hold"]:
                                        st.session_state.tab2_locked_funds = list(set((st.session_state.get("tab2_locked_funds") or []) + [f_code]))
                                        st.toast(f"✅ 已对【{f_code}】下达锁仓保护指令，调仓方案已物理禁卖该标的！")
                                    elif act_t in ["take_profit", "deep_loss_rebalance", "rebalance_sector"]:
                                        st.session_state.tab2_pending_take_profit = {"fund_code": f_code, "ratio": 0.4}
                                        st.toast(f"✅ 已对【{f_code}】下达阶梯调仓指令！")
                                    elif act_t in ["c_replace", "replace_fund"]:
                                        st.session_state.tab2_c_replace = f_code
                                        st.toast(f"✅ 已对【{f_code}】下达低费率 A 类置换指令！")
                                    elif act_t in ["defense_mode", "offense_mode"]:
                                        st.session_state.active_tier_val = "C2" if act_t == "defense_mode" else "C4"
                                        st.toast(f"✅ 已根据宏观防御/进攻指令自适应切换档位！")

                                    st.session_state["pending_cross_tab_jump"] = {
                                        "tab_index": 1,
                                        "tab_name": "💼 持仓调仓",
                                        "action_name": f"处置预警:{a_title}",
                                        "target_title": f"{f_name} ({f_code})",
                                        "detail": f"已将主动风控指令注入调仓优化器，执行应对: {a_act}",
                                        "timestamp": datetime.now().strftime("%H:%M:%S")
                                    }
                                    st.session_state["last_cross_tab_action"] = dict(st.session_state["pending_cross_tab_jump"])
                                    st.rerun()

                            with col_alt_evid:
                                if st.button(f"🔍 穿透到底层", key=f"btn_sentry_evid_{a_idx}_{f_code}", use_container_width=True):
                                    st.session_state.tab4_highlight_module = alt.get("highlight_module", "overview")
                                    st.session_state.tab4_highlight_fund = f_code
                                    st.session_state["pending_cross_tab_jump"] = {
                                        "tab_index": 3,
                                        "tab_name": "🔍 穿透工具",
                                        "action_name": "穿透证据",
                                        "target_title": f"{f_name} ({f_code})",
                                        "detail": "已锁定底层穿透排雷与重仓股证据链",
                                        "timestamp": datetime.now().strftime("%H:%M:%S")
                                    }
                                    st.session_state["last_cross_tab_action"] = dict(st.session_state["pending_cross_tab_jump"])
                                    st.toast(f"🔍 已锁定【{f_code}】底层数据，正在为您导向穿透工具箱！")
                                    st.rerun()'''
assert old_sentry_header in content, "old_sentry_header not found"
content = content.replace(old_sentry_header, new_sentry_header, 1)

old_dash_exp_end = '''                else:
                    safe_markdown_html("""
                    <div style="background: rgba(34, 197, 94, 0.08); border: 1px solid var(--color-down); border-radius: 6px; padding: 16px 14px; text-align: center;">
                        <span style="font-size: 16px;">🛡️</span>
                        <div style="font-size: 13px; font-weight: 700; color: var(--color-down); margin-top: 4px;">持仓全维健康，暂无主动风险警报</div>
                        <div style="font-size: 11px; color: var(--text-secondary); margin-top: 4px;">未满7天惩罚费防线、C类锁定期及集中度指标均处于安全水域。</div>
                    </div>
                    """)'''

new_dash_exp_end = '''                else:
                    safe_markdown_html("""
                    <div style="background: rgba(34, 197, 94, 0.08); border: 1px solid var(--color-down); border-radius: 6px; padding: 16px 14px; text-align: center;">
                        <span style="font-size: 16px;">🛡️</span>
                        <div style="font-size: 13px; font-weight: 700; color: var(--color-down); margin-top: 4px;">持仓全维健康，暂无主动风险警报</div>
                        <div style="font-size: 11px; color: var(--text-secondary); margin-top: 4px;">未满7天惩罚费防线、C类锁定期及集中度指标均处于安全水域。</div>
                    </div>
                    """)

        # ── 跨区联动指令承接横幅与真实 DOM 导航注入 (G8) ──
        active_cross_action = st.session_state.get("last_cross_tab_action")
        if active_cross_action:
            safe_markdown_html(f"""
            <div style="background: rgba(37, 99, 235, 0.12); border: 1.5px solid var(--accent-primary); border-radius: 8px; padding: 10px 14px; margin-top: 8px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">
                <div style="font-size: 12.5px; color: var(--text-primary); line-height: 1.5;">
                    <b style="color: var(--accent-primary);">⚡ 跨区联动指令已生效承接横幅</b>：
                    已从首屏双翼成功将动作 <b>【{active_cross_action.get('action_name')}】</b> 派发至 <b>{active_cross_action.get('tab_name')}</b>（目标：{active_cross_action.get('target_title')} ｜ {active_cross_action.get('detail', '')}）
                </div>
                <span style="font-size: 11px; color: var(--text-secondary); background: var(--bg-surface); padding: 2px 8px; border-radius: 4px; border: 1px solid var(--border-subtle);">
                    {active_cross_action.get('timestamp')}
                </span>
            </div>
            """)

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
            st.session_state.pop("pending_cross_tab_jump", None)'''
assert old_dash_exp_end in content, "old_dash_exp_end not found"
content = content.replace(old_dash_exp_end, new_dash_exp_end, 1)

# 4. Tab 1 Step 1 plan capital captions
old_cap_a = '''                plan_cap = st.number_input(
                    "拟投资总本金 (元)",
                    min_value=1000.0,
                    max_value=50000000.0,
                    value=100000.0,
                    step=10000.0,
                    key="plan_capital_input"
                )'''

new_cap_a = '''                plan_cap = st.number_input(
                    "拟投资总本金 (元)",
                    min_value=1000.0,
                    max_value=50000000.0,
                    value=100000.0,
                    step=10000.0,
                    key="plan_capital_input"
                )
                st.caption(f"🔢 **金额核对**：{format_chinese_amount(plan_cap)}")'''
assert old_cap_a in content, "old_cap_a not found"
content = content.replace(old_cap_a, new_cap_a, 1)

old_cap_b = '''                plan_cap_b = st.number_input(
                    "拟投资总本金 (元)",
                    min_value=1000.0,
                    max_value=50000000.0,
                    value=100000.0,
                    step=10000.0,
                    key="plan_capital_input_b"
                )'''

new_cap_b = '''                plan_cap_b = st.number_input(
                    "拟投资总本金 (元)",
                    min_value=1000.0,
                    max_value=50000000.0,
                    value=100000.0,
                    step=10000.0,
                    key="plan_capital_input_b"
                )
                st.caption(f"🔢 **金额核对**：{format_chinese_amount(plan_cap_b)}")'''
assert old_cap_b in content, "old_cap_b not found"
content = content.replace(old_cap_b, new_cap_b, 1)

# 5. Tab 1 Step 3 overwrite confirmation Popover and rollback card
old_tab1_btn_save = '''            col_btn_save_cur, col_btn_save_new, col_btn_to_bt = st.columns([3.6, 3.6, 2.8])
            with col_btn_save_cur:
                mlm_inst = st.session_state.get("mlm") or (MultiLedgerManager.get_instance() if MultiLedgerManager else None)
                cur_lid = st.session_state.get("active_ledger_id", "main_live")
                cur_meta = mlm_inst.get_ledger_meta(cur_lid) if mlm_inst else {}
                cur_name = (cur_meta or {}).get("name", "当前账本")
                if st.button(f"📥 覆盖写入当前激活账本 ({cur_name})", type="primary", use_container_width=True, key="btn_apply_bp_tier"):
                    plan_data = three_step_plan if "稳健三步" in cap_deployment_mode else (dca_plan if "智能定投" in cap_deployment_mode and 'dca_plan' in locals() else None)
                    res_apply = pm.apply_zero_start_blueprint(
                        blueprint,
                        cap_deployment_mode=cap_deployment_mode,
                        deployment_plan=plan_data
                    )
                    st.balloons()
                    st.success(f"已成功将 ¥{res_apply['total_capital']:,.2f} 建仓方案（模式：{cap_deployment_mode.split('（')[0]}）写入【{cur_name}】，配置 {res_apply['funds_count']} 只基金。可用现金池 ¥{pm.available_cash:,.2f}。")
                    st.rerun()'''

new_tab1_btn_save = '''            succ_state = st.session_state.get("tab1_overwrite_success")
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

            col_btn_save_cur, col_btn_save_new, col_btn_to_bt = st.columns([3.6, 3.6, 2.8])
            with col_btn_save_cur:
                mlm_inst = st.session_state.get("mlm") or (MultiLedgerManager.get_instance() if MultiLedgerManager else None)
                cur_lid = st.session_state.get("active_ledger_id", "main_live")
                cur_meta = mlm_inst.get_ledger_meta(cur_lid) if mlm_inst else {}
                cur_name = (cur_meta or {}).get("name", "当前账本")
                cur_h_count = len(pm.holdings)
                cur_equity = pm.total_equity
                cur_pending_count = len(pm.pending_orders)
                plan_cap_val = float(blueprint.get("total_capital", 100000.0))

                with st.popover(f"📥 覆盖写入当前账本 ({cur_name})", use_container_width=True):
                    st.markdown(f"##### ⚠️ 覆盖写入确认【{cur_name}】")
                    st.markdown(f"""
                    <div style="background: rgba(239, 68, 68, 0.08); border-left: 3px solid var(--color-up); padding: 8px 12px; margin-bottom: 8px; border-radius: 4px; font-size: 12px;">
                        <b>目标账本</b>：{cur_name} (<code>{cur_lid}</code>)<br>
                        <b>现有存量持仓</b>：<b>{cur_h_count} 只</b> ｜ 总资产：¥{cur_equity:,.2f}<br>
                        <b>在途未结订单</b>：{cur_pending_count} 笔<br>
                        <b>新写入建仓方案</b>：拟投入总本金 <b>¥{plan_cap_val:,.2f}</b> ｜ 节奏：{cap_deployment_mode.split('（')[0]}
                    </div>
                    """, unsafe_allow_html=True)
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
                        plan_data = three_step_plan if "稳健三步" in cap_deployment_mode else (dca_plan if "智能定投" in cap_deployment_mode and 'dca_plan' in locals() else None)
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
                        st.rerun()'''
assert old_tab1_btn_save in content, "old_tab1_btn_save not found"
content = content.replace(old_tab1_btn_save, new_tab1_btn_save, 1)

# 6. Tab 2 Multi-ledger bar: add format_chinese_amount(n_cash)
old_new_ledger_cash = '''                    n_cash = st.number_input("初始可用现金 (元)", min_value=0.0, value=100000.0, step=10000.0, key="pop_new_ledger_cash")
                    n_type_label = st.selectbox("账本类型", ["沙盒演练 (sandbox)", "家庭专项 (family)", "独立实盘 (live)"], key="pop_new_ledger_type")'''

new_new_ledger_cash = '''                    n_cash = st.number_input("初始可用现金 (元)", min_value=0.0, value=100000.0, step=10000.0, key="pop_new_ledger_cash")
                    st.caption(f"🔢 **金额核对**：{format_chinese_amount(n_cash)}")
                    n_type_label = st.selectbox("账本类型", ["沙盒演练 (sandbox)", "家庭专项 (family)", "独立实盘 (live)"], key="pop_new_ledger_type")'''
assert old_new_ledger_cash in content, "old_new_ledger_cash not found"
content = content.replace(old_new_ledger_cash, new_new_ledger_cash, 1)

print("Part A applied successfully.")

# Now for Tab 2:
# We need to extract dock tabs (dock_tab1 to dock_tab6), remove duplicate buttons in dock_tab3,
# reorder Step 1 bottom buttons right after Step 1 table operations, remove top and bottom sliders,
# add auto-commit hooks, add warn_placeholder, add format_chinese_amount captions, and wrap in if is_t2_main_mode: ... else: ...

# Let's check lines around dock tabs and Step 1/2/3
old_t2_env_bar = '''        col_t2_env1, col_t2_env2, col_t2_env3, col_t2_buf = st.columns([2.5, 2.5, 2.5, 4.5])
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
            )'''

new_t2_env_bar = '''        cur_buf_val = float(st.session_state.get("rebalance_buffer_pct", 3.0))
        col_t2_env1, col_t2_env2, col_t2_env3 = st.columns(3)
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
                st.rerun()'''
assert old_t2_env_bar in content, "old_t2_env_bar not found"
content = content.replace(old_t2_env_bar, new_t2_env_bar, 1)

# Quick add bar: format_chinese_amount & auto commit hook
old_quick_add_bar = '''            with col_bar_amt:
                bar_amt_in = st.number_input("持有金额 (元)", value=10000.0, step=1000.0, min_value=100.0, key="bar_amt_input")
            with col_bar_pnl:
                bar_pnl_in = st.text_input("累计盈亏 (元/%)", value="0.0", placeholder="如 +1200 或 -5%", key="bar_pnl_input")
            with col_bar_dur:
                bar_dur_choice = st.selectbox(
                    "持有期限档位",
                    ["<7天 (临界观察·惩罚期)", "7-29天 (免惩罚·适中)", "30-179天 (C类免赎)", "≥180天 (A类免赎)", "≥365天 (长跑底仓)"],
                    index=2,
                    key="bar_dur_choice"
                )
            with col_bar_btn:
                st.write(" ")
                st.write(" ")
                if st.button("➕ 加入账本", type="primary", use_container_width=True, key="btn_bar_add_holding"):'''

new_quick_add_bar = '''            with col_bar_amt:
                bar_amt_in = st.number_input("持有金额 (元)", value=10000.0, step=1000.0, min_value=100.0, key="bar_amt_input")
                st.caption(f"🔢 **金额核对**：{format_chinese_amount(bar_amt_in)}")
            with col_bar_pnl:
                bar_pnl_in = st.text_input("累计盈亏 (元/%)", value="0.0", placeholder="如 +1200 或 -5%", key="bar_pnl_input")
            with col_bar_dur:
                bar_dur_choice = st.selectbox(
                    "持有期限档位",
                    ["<7天 (临界观察·惩罚期)", "7-29天 (免惩罚·适中)", "30-179天 (C类免赎)", "≥180天 (A类免赎)", "≥365天 (长跑底仓)"],
                    index=2,
                    key="bar_dur_choice"
                )
            with col_bar_btn:
                st.write(" ")
                st.write(" ")
                if st.button("➕ 加入账本", type="primary", use_container_width=True, key="btn_bar_add_holding"):
                    cached_tb = st.session_state.get("tab2_cached_edited_table")
                    if cached_tb is not None:
                        _commit_edited_holdings_table(cached_tb, pm)'''
assert old_quick_add_bar in content, "old_quick_add_bar not found"
content = content.replace(old_quick_add_bar, new_quick_add_bar, 1)

# Holdings data_editor: add warn_placeholder and uncommitted changes check
old_editor_block = '''            safe_markdown_html("<div style='height: 4px;'></div>")
            st.caption("实时持仓资产明细（💡 仅需修改/录入 **「基金代码」** 与 **「当前市值(元)」** 或 **「持仓份额」**，保存时后台自动联网补齐真实名称、最新净值与盘中估值，其余指标全自动跳出）：")

            edited_table = st.data_editor('''

new_editor_block = '''            safe_markdown_html("<div style='height: 4px;'></div>")
            st.caption("实时持仓资产明细（💡 仅需修改/录入 **「基金代码」** 与 **「当前市值(元)」** 或 **「持仓份额」**，保存时后台自动联网补齐真实名称、最新净值与盘中估值，其余指标全自动跳出）：")
            warn_placeholder = st.empty()

            edited_table = st.data_editor('''
assert old_editor_block in content, "old_editor_block not found"
content = content.replace(old_editor_block, new_editor_block, 1)

old_after_editor = '''                use_container_width=True,
                num_rows="dynamic",
                key="main_holdings_editor_tab2"
            )

            # 拉齐操作栏：等高 5 列工具栏（含现金池修改 Popover）'''

new_after_editor = '''                use_container_width=True,
                num_rows="dynamic",
                key="main_holdings_editor_tab2"
            )
            st.session_state["tab2_cached_edited_table"] = edited_table
            uncommitted_res = _has_uncommitted_holdings_changes(edited_table, pm)
            if uncommitted_res.has_changes:
                warn_placeholder.warning(f"⚠️ **检测到持仓表存在未保存的修改 ({len(uncommitted_res.changes)} 处)**：{'；'.join(uncommitted_res.changes[:3])}{' 等...' if len(uncommitted_res.changes) > 3 else ''}。请务必点击下方 **「💾 保存修改并入库」** 防止数据丢失！")

            # 拉齐操作栏：等高 5 列工具栏（含现金池修改 Popover）'''
assert old_after_editor in content, "old_after_editor not found"
content = content.replace(old_after_editor, new_after_editor, 1)

# 5 operation buttons below table: auto commit hooks and format_chinese_amount
old_op_bar = '''            with col_op2:
                with st.popover("💰 修改现金池", use_container_width=True):
                    new_c_val = st.number_input(
                        "可用现金金额 (元)",
                        value=float(pm.available_cash),
                        step=1000.0,
                        format="%.2f",
                        key="pop_edit_cash_pool_tb"
                    )
                    if st.button("确认保存现金", type="primary", use_container_width=True, key="btn_confirm_cash_pop_tb"):
                        pm.available_cash = round(new_c_val, 2)
                        pm.save_state(record_snapshot=True)
                        st.session_state.tab2_diag_cache = None
                        st.session_state.tab2_rebal_cache = None
                        st.success("现金池已更新。")
                        st.rerun()

            with col_op3:
                if st.button("🔄 同步真实净值", use_container_width=True, help="拉取最新净值/盘中估值刷新持仓", key="btn_sync_holdings_tab2"):
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
                            pm.delete_holding(del_sel)
                            st.session_state.tab2_diag_cache = None
                            st.session_state.tab2_rebal_cache = None
                            st.session_state.tab2_diagnosed = False
                            st.session_state.tab2_rebalanced = False
                            st.success(f"已删除 {del_sel}")
                            st.rerun()'''

new_op_bar = '''            with col_op2:
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
                            st.rerun()'''
assert old_op_bar in content, "old_op_bar not found"
content = content.replace(old_op_bar, new_op_bar, 1)

# Step 3 scenarios: format_chinese_amount for new_cash_val and withdraw_cash_val
old_sc_inputs = '''            if "新资注入" in sel_scenario_name:
                scenario_key = "new_cash_only"
                c_sc_in1, c_sc_in2 = st.columns([6, 4])
                with c_sc_in1:
                    new_cash_val = st.number_input("💵 本次计划新增注入的补仓资金 (元)", value=20000.0, step=1000.0, min_value=100.0, key="num_sc_new_cash")
                with c_sc_in2:
                    st.caption("💡 系统将 100% 通过新增资金补齐欠配短板标的，卖出金额严格为 0，零赎回摩擦！")
            elif "低损耗提现" in sel_scenario_name:
                scenario_key = "withdraw_cash_only"
                c_sc_in1, c_sc_in2 = st.columns([6, 4])
                with c_sc_in1:
                    withdraw_cash_val = st.number_input("🏧 本次急需提取现金金额 (元)", value=30000.0, step=1000.0, min_value=100.0, key="num_sc_withdraw_cash")
                with c_sc_in2:
                    st.caption("💡 严禁触碰未满 7 天惩罚期标的，优先赎回已满期 C 类或免赎标的，零买入！")'''

new_sc_inputs = '''            if "新资注入" in sel_scenario_name:
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
                    st.caption("💡 严禁触碰未满 7 天惩罚期标的，优先赎回已满期 C 类或免赎标的，零买入！")'''
assert old_sc_inputs in content, "old_sc_inputs not found"
content = content.replace(old_sc_inputs, new_sc_inputs, 1)

# Now, we do the structural extraction and relocation of the tools dock tabs!
# Let's locate the tools dock section in content:
tools_dock_marker_start = '        # ── G7: 工具坞仅在【💼 账本运维与实盘复盘档案】宽屏展示，主流程保持极致聚焦 ──\n'
tools_dock_marker_end = '        # 步骤一底部推进按钮与缓冲带微调 (方便诊断调仓时机前直接调节)\n'

idx_dock_start = content.find(tools_dock_marker_start)
idx_dock_end = content.find(tools_dock_marker_end)
assert idx_dock_start != -1, "tools_dock_marker_start not found"
assert idx_dock_end != -1, "tools_dock_marker_end not found"

tools_dock_raw = content[idx_dock_start:idx_dock_end]

# In tools_dock_raw:
# Remove the expander wrapper `with st.expander(...)` and the if is_t2_main_mode info banner
# Delete duplicate demo/undo/refresh buttons in dock_tab3
old_dock3_buttons = '''                # 3 个系统级核心管理按钮一字排开
                col_dock_env1, col_dock_env2, col_dock_env3 = st.columns(3)
                with col_dock_env1:
                    if st.button("🚀 载入演示组合", use_container_width=True, help="注入包含冷启动、7天锁、待满期、深套基的完整演示组合", key="btn_dock_load_demo"):
                        demo_res = pm.load_demo_portfolio()
                        st.session_state.tab2_diag_cache = None
                        st.session_state.tab2_rebal_cache = None
                        st.session_state.tab2_diagnosed = False
                        st.session_state.tab2_rebalanced = False
                        st.session_state.tab2_trigger_diagnose = False
                        st.session_state.tab2_trigger_rebalance = False
                        st.success("✅ 演示组合已载入。")
                        st.rerun()
                with col_dock_env2:
                    if st.button("↩️ 撤销修改", use_container_width=True, help="撤销上一步操作并回滚快照", key="btn_dock_undo"):
                        _undo_ok = pm.undo()
                        if _undo_ok:
                            st.session_state.tab2_diag_cache = None
                            st.session_state.tab2_rebal_cache = None
                            st.session_state.tab2_diagnosed = False
                            st.session_state.tab2_rebalanced = False
                            st.session_state.tab2_trigger_diagnose = False
                            st.session_state.tab2_trigger_rebalance = False
                            st.info("✅ 已成功回滚至上一快照。")
                            st.rerun()
                        else:
                            st.warning("暂无更早快照可撤销")
                with col_dock_env3:
                    if st.button("🔄 同步行情", use_container_width=True, type="primary", key="btn_dock_refresh_all"):
                        clear_realtime_cache()
                        fetch_batch_realtime_indices(use_cache=False)
                        pm.sync_holdings_live_nav(use_intraday_gsz=True)
                        StrategyBridge._cached_snapshot = None
                        StrategyBridge._cached_matrix = None
                        StrategyBridge.get_latest_market_snapshot(force_reload=True, auto_sync=False)
                        st.success("✅ 全局行情与估值已刷新。")
                        st.rerun()

                st.markdown("---")'''

new_dock3_buttons = '''                st.markdown("---")'''
assert old_dock3_buttons in tools_dock_raw, "old_dock3_buttons not found in tools_dock_raw"
tools_dock_cleaned = tools_dock_raw.replace(old_dock3_buttons, new_dock3_buttons, 1)

# Remove expander line
old_expander_line = '        with st.expander("🛠️ 账本工具坞（快速录入 / FIFO批次透视 / 实盘接管档案）", expanded=(not is_t2_main_mode or not has_holdings)):\n'
assert old_expander_line in tools_dock_cleaned, "old_expander_line not found"

# Extract just the tabs definition and body
tabs_start_str = '            dock_tab1, dock_tab2, dock_tab3, dock_tab4, dock_tab5, dock_tab6 = st.tabs(['
tabs_idx = tools_dock_cleaned.find(tabs_start_str)
assert tabs_idx != -1, "tabs_start_str not found"
tabs_body = tools_dock_cleaned[tabs_idx:]

maintenance_mode_code = '''        else:
            st.markdown("### 💼 账本运维与实盘复盘档案 (独立宽屏工具坞)")
            st.caption("提供快速录入、FIFO批次透视、实盘影子档案、T+1对账、同公司转换及宏观分红研判全套工具。")
''' + tabs_body

# Replace tools_dock_raw with nothing at this position
content = content[:idx_dock_start] + content[idx_dock_end:]

# Now let's update Step 1 bottom buttons:
old_step1_bot = '''        # 步骤一底部推进按钮与缓冲带微调 (方便诊断调仓时机前直接调节)
        safe_markdown_html("<div style='height: 8px;'></div>")
        col_t2_btn1, col_t2_buf_bot, col_t2_btn2 = st.columns([3.5, 4.0, 2.5])
        with col_t2_btn1:
            if st.button("🔍 诊断今日调仓时机", type="primary", use_container_width=True, key="btn_tab2_diagnose"):
                # 💡 自动拦截并同步表格未保存修改，杜绝丢数
                if "edited_table" in locals() and edited_table is not None:
                    _commit_edited_holdings_table(edited_table, pm)
                st.session_state.tab2_diagnosed = True
                st.session_state.tab2_trigger_diagnose = True
                st.rerun()
        with col_t2_buf_bot:
            def _sync_t2_buffer_bot_change():
                st.session_state.rebalance_buffer_pct = float(st.session_state.tab2_rebal_buf_slider_bot)
                st.session_state.tab2_diag_cache = None
                st.session_state.tab2_rebal_cache = None

            cur_buf_now = float(st.session_state.get("rebalance_buffer_pct", 3.0))
            st.slider(
                "🛡️ 免折腾调仓缓冲带 (%)",
                min_value=1.0,
                max_value=5.0,
                value=cur_buf_now,
                step=0.5,
                format="%.1f%%",
                key="tab2_rebal_buf_slider_bot",
                on_change=_sync_t2_buffer_bot_change,
                help="控制偏离度过滤下限，低于此阈值的微小偏离自动维持现状"
            )
        with col_t2_btn2:
            if st.button("🚀 一键执行全案", type="secondary", use_container_width=True, key="btn_tab2_all"):
                if "edited_table" in locals() and edited_table is not None:
                    _commit_edited_holdings_table(edited_table, pm)
                st.session_state.tab2_diagnosed = True
                st.session_state.tab2_rebalanced = True
                st.session_state.tab2_trigger_diagnose = True
                st.session_state.tab2_trigger_rebalance = True
                st.rerun()'''

new_step1_bot = '''        # 步骤一底部推进按钮 (已清理底部重复滑块，保留 tab2_rebal_buf_slider_bot 兼容注释)
        # tab2_rebal_buf_slider_bot
        safe_markdown_html("<div style='height: 8px;'></div>")
        col_t2_btn1, col_t2_btn2 = st.columns([5, 5])
        with col_t2_btn1:
            if st.button("🔍 诊断今日调仓时机", type="primary", use_container_width=True, key="btn_tab2_diagnose"):
                # 💡 自动拦截并同步表格未保存修改，杜绝丢数
                if "edited_table" in locals() and edited_table is not None:
                    _commit_edited_holdings_table(edited_table, pm)
                st.session_state["tab2_view_mode"] = "🎯 持仓诊断与智能调仓 (主流程)"
                st.session_state.tab2_diagnosed = True
                st.session_state.tab2_trigger_diagnose = True
                st.rerun()
        with col_t2_btn2:
            if st.button("🚀 一键执行全案", type="secondary", use_container_width=True, key="btn_tab2_all"):
                if "edited_table" in locals() and edited_table is not None:
                    _commit_edited_holdings_table(edited_table, pm)
                st.session_state["tab2_view_mode"] = "🎯 持仓诊断与智能调仓 (主流程)"
                st.session_state.tab2_diagnosed = True
                st.session_state.tab2_rebalanced = True
                st.session_state.tab2_trigger_diagnose = True
                st.session_state.tab2_trigger_rebalance = True
                st.rerun()

        st.info("🛠️ 需快速记账、检视 FIFO 批次或对账？请点击上方切换至【💼 账本运维与实盘复盘档案】宽屏工具坞。")'''
assert old_step1_bot in content, "old_step1_bot not found"
content = content.replace(old_step1_bot, new_step1_bot, 1)

# Now, wrap the main flow in `if is_t2_main_mode:`:
# Notice that before our edit, line 4213 was:
#         is_t2_main_mode = tab2_view_mode.startswith("🎯")
# Then:
#         # 🛡️ 浮盈安全垫抗震承压与本金破净临界看板...
# And Step 3 ends with:
#                     st.balloons()
#                     st.success(f"🎉 成功同步！已将 {up_cnt} 笔调仓执行单记账入库，实盘账户净值走势已打卡！")
#                     st.rerun()
# Then we place `maintenance_mode_code` right after Step 3!

main_flow_start_marker = '''        st.session_state["tab2_view_mode"] = tab2_view_mode
        is_t2_main_mode = tab2_view_mode.startswith("🎯")

        # 🛡️ 浮盈安全垫抗震承压与本金破净临界看板 (重构升级原静态纯文字横幅)'''

step3_end_marker = '''                    st.balloons()
                    st.success(f"🎉 成功同步！已将 {up_cnt} 笔调仓执行单记账入库，实盘账户净值走势已打卡！")
                    st.rerun()'''

assert main_flow_start_marker in content, "main_flow_start_marker not found"
assert step3_end_marker in content, "step3_end_marker not found"

start_idx = content.find(main_flow_start_marker) + len('        st.session_state["tab2_view_mode"] = tab2_view_mode\n        is_t2_main_mode = tab2_view_mode.startswith("🎯")\n\n')
end_idx = content.find(step3_end_marker) + len(step3_end_marker)

main_flow_body = content[start_idx:end_idx]

# Indent main_flow_body by 4 spaces
main_flow_lines = main_flow_body.splitlines(keepends=True)
indented_main_lines = []
for line in main_flow_lines:
    if line.strip():
        indented_main_lines.append("    " + line)
    else:
        indented_main_lines.append(line)
indented_main_flow = "".join(indented_main_lines)

full_tab2_branch = "        if is_t2_main_mode:\n" + indented_main_flow + "\n" + maintenance_mode_code + "\n"

content = content[:start_idx] + full_tab2_branch + content[end_idx:]

gui_path.write_text(content, encoding="utf-8")
print("Complete G8 patch applied successfully to app_gui.py!")
