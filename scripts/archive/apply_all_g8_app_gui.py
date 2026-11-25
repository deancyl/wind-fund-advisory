import re
from pathlib import Path

gui_path = Path("AGY2_FundAdvisory/app_gui.py")
content = gui_path.read_text(encoding="utf-8")

# 1. Add import streamlit.components.v1 as components
old_import = "import streamlit as st\nfrom typing import Any, Callable, Dict, List, Optional, Tuple"
new_import = "import streamlit as st\nimport streamlit.components.v1 as components\nfrom typing import Any, Callable, Dict, List, Optional, Tuple"
assert old_import in content, "old_import not found"
content = content.replace(old_import, new_import)

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

content = content.replace(target_func_marker, target_func_marker + helpers_code)

# 3. Morning pulse card & Top 3 sector cards & Dual-wing DOM routing
# Let's check morning pulse card around lines 2590-2640 in original
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
content = content.replace(old_morning_pulse, new_morning_pulse)

# Top 3 sector card enhancement
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
content = content.replace(old_top3_card, new_top3_card)

# Radar add to watchlist button navigation
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
content = content.replace(old_radar_btn, new_radar_btn)

# Right-wing sentry header cleanup & container height
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
                                    # 派发主动风控指令至 Tab 2 调仓方案
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
content = content.replace(old_sentry_header, new_sentry_header)

# Inject DOM script & Cross-tab banner at bottom of dashboard expander
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
content = content.replace(old_dash_exp_end, new_dash_exp_end)

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
content = content.replace(old_cap_a, new_cap_a)

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
content = content.replace(old_cap_b, new_cap_b)

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
content = content.replace(old_tab1_btn_save, new_tab1_btn_save)

# 6. Tab 2 Multi-ledger bar: add format_chinese_amount(n_cash)
old_new_ledger_cash = '''                    n_cash = st.number_input("初始可用现金 (元)", min_value=0.0, value=100000.0, step=10000.0, key="pop_new_ledger_cash")
                    n_type_label = st.selectbox("账本类型", ["沙盒演练 (sandbox)", "家庭专项 (family)", "独立实盘 (live)"], key="pop_new_ledger_type")'''

new_new_ledger_cash = '''                    n_cash = st.number_input("初始可用现金 (元)", min_value=0.0, value=100000.0, step=10000.0, key="pop_new_ledger_cash")
                    st.caption(f"🔢 **金额核对**：{format_chinese_amount(n_cash)}")
                    n_type_label = st.selectbox("账本类型", ["沙盒演练 (sandbox)", "家庭专项 (family)", "独立实盘 (live)"], key="pop_new_ledger_type")'''

assert old_new_ledger_cash in content, "old_new_ledger_cash not found"
content = content.replace(old_new_ledger_cash, new_new_ledger_cash)

gui_path.write_text(content, encoding="utf-8")
print("Successfully applied part A of all G8 app_gui changes!")
