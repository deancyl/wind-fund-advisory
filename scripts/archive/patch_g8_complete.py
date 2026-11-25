import sys
from pathlib import Path

gui_path = Path("AGY2_FundAdvisory/app_gui.py")
content = gui_path.read_text(encoding="utf-8")
print(f"Initial content length: {len(content)}")

# -------------------------------------------------------------
# 1. Add components import
# -------------------------------------------------------------
old_import = "import streamlit as st\nfrom typing import Any, Callable, Dict, List, Optional, Tuple"
new_import = "import streamlit as st\nimport streamlit.components.v1 as components\nfrom typing import Any, Callable, Dict, List, Optional, Tuple"
assert old_import in content, "old_import not found"
content = content.replace(old_import, new_import, 1)

# -------------------------------------------------------------
# 2. Add format_chinese_amount, UncommittedCheckResult, _has_uncommitted_holdings_changes
# -------------------------------------------------------------
marker_func = '''def map_slider_to_tier(ret: float) -> str:
    """统一委托 strategy_bridge.map_target_return_to_tier，消除重复定义与档位漂移"""
    return map_target_return_to_tier(ret)'''
assert marker_func in content, "marker_func not found"

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

    return UncommittedCheckResult(len(changes) > 0, changes)'''

content = content.replace(marker_func, marker_func + helpers_code, 1)

# -------------------------------------------------------------
# 3. Dual-wing Dashboard: Morning Pulse, News Flash, Realtime Top3, Sentry, Cross-Tab Routing
# -------------------------------------------------------------
old_pulse_block = '''                # 今日市场脉搏晨报 (<=80字) 与 历史牛熊拐点对照尺 (紧凑一行式 4 节点)
                turnover_str = "1.2万亿"
                vol_text = "放量活跃"
                try:
                    t_data = data_loader.fetch_market_turnover_and_sentiment()
                    if t_data and "turnover_str" in t_data:
                        turnover_str = t_data.get("turnover_str", turnover_str)
                        vol_text = t_data.get("vol_text", vol_text)
                except Exception:
                    pass

                erp_pct = float(snapshot_dict.get("erp_percentile", 82.0))
                bias_val = float(snapshot_dict.get("c300_bias_20", snapshot_dict.get("bias_20", -2.07)))
                if erp_pct >= 75.0:
                    erp_zone = f"ERP分位{erp_pct:.1f}%处高性价比击球区"
                elif erp_pct <= 30.0:
                    erp_zone = f"ERP分位{erp_pct:.1f}%偏高估宜防守"
                else:
                    erp_zone = f"ERP分位{erp_pct:.1f}%处中性配置区间"

                top_names = [s.get("name", "") for s in top3_sectors[:2] if s.get("name")]
                lead_str = "与".join(top_names) if top_names else "红利低波与大盘蓝筹"
                pulse_brief = f"两市成交{turnover_str}{vol_text}，{erp_zone}；{lead_str}领衔主线。"
                if len(pulse_brief) > 80:
                    pulse_brief = pulse_brief[:79] + "。"

                # 接入历史三大牛熊拐点对照尺 (2021见顶 0.50x、2022恐慌底 1.93x、2024反转底 1.94x、今日实时 1.76x)
                inflection_ruler = StrategyBridge.get_historical_inflection_ruler(
                    current_erp=erp_pct,
                    current_bias=bias_val
                )
                ruler_bar_html = render_historical_inflection_ruler_html(inflection_ruler)

                pulse_card_html = f"""
                <div class="decision-card" style="padding: 8px 12px; margin-bottom: 10px; border-left: 3px solid var(--accent-primary); background: var(--bg-surface);">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 2px;">
                        <span style="font-size: 11px; font-weight: 700; color: var(--accent-primary);">📢 今日市场脉搏晨报</span>
                        <span style="font-size: 10px; color: var(--text-secondary);">全景量化串联 ｜ 历史拐点并列对照</span>
                    </div>
                    <div style="font-size: 11px; color: var(--text-primary); line-height: 1.4; margin-bottom: 4px;">
                        {pulse_brief}
                    </div>
                    {ruler_bar_html}
                </div>
                """
                safe_markdown_html(pulse_card_html)'''

new_pulse_block = '''                # 今日市场脉搏晨报 (<=80字) 与 历史牛熊拐点对照尺 (接入实时资讯与秒级感知时间)
                news_res = DataLoader.fetch_realtime_market_news_and_catalysts()
                news_items = news_res.get("news", [])
                latest_flash = news_items[0]["title"] if news_items else "A股主要指数处于关键均线右侧蓄势期，增量资金积极聚焦高股息红利与核心宽基。"
                data_sense_time = news_res.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

                turnover_str = "1.2万亿"
                vol_text = "放量活跃"
                try:
                    t_data = data_loader.fetch_market_turnover_and_sentiment()
                    if t_data and "turnover_str" in t_data:
                        turnover_str = t_data.get("turnover_str", turnover_str)
                        vol_text = t_data.get("vol_text", vol_text)
                except Exception:
                    pass

                erp_pct = float(snapshot_dict.get("erp_percentile", 82.0))
                bias_val = float(snapshot_dict.get("c300_bias_20", snapshot_dict.get("bias_20", -2.07)))
                if erp_pct >= 75.0:
                    erp_zone = f"ERP分位{erp_pct:.1f}%处高性价比击球区"
                elif erp_pct <= 30.0:
                    erp_zone = f"ERP分位{erp_pct:.1f}%偏高估宜防守"
                else:
                    erp_zone = f"ERP分位{erp_pct:.1f}%处中性配置区间"

                top_names = [s.get("name", "") for s in top3_sectors[:2] if s.get("name")]
                lead_str = "与".join(top_names) if top_names else "红利低波与大盘蓝筹"
                pulse_brief = f"两市成交{turnover_str}{vol_text}，{erp_zone}；{lead_str}领衔主线。"
                if len(pulse_brief) > 80:
                    pulse_brief = pulse_brief[:79] + "。"

                # 接入历史三大牛熊拐点对照尺 (2021见顶 0.50x、2022恐慌底 1.93x、2024反转底 1.94x、今日实时 1.76x)
                inflection_ruler = StrategyBridge.get_historical_inflection_ruler(
                    current_erp=erp_pct,
                    current_bias=bias_val
                )
                ruler_bar_html = render_historical_inflection_ruler_html(inflection_ruler)

                pulse_card_html = f"""
                <div class="decision-card" style="padding: 8px 12px; margin-bottom: 10px; border-left: 3px solid var(--accent-primary); background: var(--bg-surface);">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 2px;">
                        <span style="font-size: 11px; font-weight: 700; color: var(--accent-primary);">📢 今日市场脉搏晨报</span>
                        <div style="display: flex; gap: 8px; align-items: center;">
                            <span style="font-size: 10px; color: var(--text-secondary);">⏱️ 数据感知时间: {data_sense_time}</span>
                            <span style="font-size: 10px; color: var(--text-secondary);">全景量化串联 ｜ 历史拐点并列对照</span>
                        </div>
                    </div>
                    <div style="font-size: 11px; color: var(--text-primary); line-height: 1.4; margin-bottom: 4px;">
                        {pulse_brief}<br>
                        ⚡ 实时快讯: <span style="color: var(--accent-primary);">{latest_flash}</span>
                    </div>
                    {ruler_bar_html}
                </div>
                """
                safe_markdown_html(pulse_card_html)'''

assert old_pulse_block in content, "old_pulse_block not found"
content = content.replace(old_pulse_block, new_pulse_block, 1)

# Top 3 Opportunity Sector cards & "➕ 入备选池" button
old_top3_sectors = '''                cols_top3 = st.columns(3)
                for i, sec in enumerate(top3_sectors):
                    with cols_top3[i]:
                        sec_fund = sec.get("fund", {})
                        tag_color = "var(--color-up)" if "🔥" in sec["tag"] else ("var(--accent-primary)" if "🎯" in sec["tag"] else "var(--color-down)")
                        safe_markdown_html(f"""
                        <div class="decision-card" style="padding: 10px 12px; height: 100%; border-top: 2px solid {tag_color};">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                                <span style="font-size: 13px; font-weight: 700; color: var(--text-primary);">{sec['name']}</span>
                                <span style="font-size: 11px; padding: 1px 6px; border-radius: 4px; background: var(--bg-canvas); color: {tag_color}; border: 1px solid var(--border-subtle);">{sec['tag']}</span>
                            </div>
                            <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 6px;">
                                综合得分: <b style="color: var(--text-primary);">{sec['total_score']}</b> ｜ 估值分位: {sec['val_percentile']:.0f}%
                            </div>
                            <div style="font-size: 12px; font-weight: 600; color: var(--text-primary); margin-bottom: 2px;">
                                优选: {sec_fund.get('name', '')}
                            </div>
                            <div style="font-size: 11px; color: var(--text-secondary);">
                                代码: <code>{sec_fund.get('code', '')}</code>
                            </div>
                        </div>
                        """)
                        if st.button("➕ 入备选池", key=f"btn_add_radar_pool_{sec['sector_id']}", use_container_width=True, type="secondary"):
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
                            st.rerun()'''

new_top3_sectors = '''                cols_top3 = st.columns(3)
                for i, sec in enumerate(top3_sectors):
                    with cols_top3[i]:
                        sec_fund = sec.get("fund", {})
                        tag_color = "var(--color-up)" if "🔥" in sec["tag"] else ("var(--accent-primary)" if "🎯" in sec["tag"] else "var(--color-down)")
                        rt_chg = sec.get("realtime_chg_pct", 0.0)
                        rt_pt = sec.get("realtime_point", 0.0)
                        pt_disp = f" ({rt_pt:.1f}点)" if rt_pt > 0 else ""
                        rt_color = active_co["color_up"] if rt_chg >= 0 else active_co["color_down"]
                        core_logic_txt = sec.get("core_logic", "综合得分靠前")
                        sub_s = sec.get("sub_scores", {})
                        safe_markdown_html(f"""
                        <div class="decision-card" style="padding: 10px 12px; height: 100%; border-top: 2px solid {tag_color};">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                                <span style="font-size: 13px; font-weight: 700; color: var(--text-primary);">{sec['name']}</span>
                                <div style="display: flex; gap: 4px; align-items: center;">
                                    <span style="font-size: 10px; font-weight: 700; color: {rt_color};">实时: {rt_chg:+.2f}%{pt_disp}</span>
                                    <span style="font-size: 11px; padding: 1px 6px; border-radius: 4px; background: var(--bg-canvas); color: {tag_color}; border: 1px solid var(--border-subtle);">{sec['tag']}</span>
                                </div>
                            </div>
                            <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 4px;">
                                综合得分: <b style="color: var(--text-primary);">{sec['total_score']}</b> ｜ 估值分位: {sec['val_percentile']:.0f}% ｜ 动量: {sub_s.get('momentum', 0.0):.0f}分
                            </div>
                            <div style="font-size: 11px; color: var(--text-primary); background: var(--bg-elevated); padding: 3px 6px; border-radius: 4px; margin-bottom: 4px;">
                                💡 <b>入选依据</b>：{core_logic_txt}
                            </div>
                            <div style="font-size: 12px; font-weight: 600; color: var(--text-primary); margin-bottom: 2px;">
                                优选: {sec_fund.get('name', '')}
                            </div>
                            <div style="font-size: 11px; color: var(--text-secondary);">
                                代码: <code>{sec_fund.get('code', '')}</code>
                            </div>
                        </div>
                        """)
                        if st.button("➕ 入备选池", key=f"btn_add_radar_pool_{sec['sector_id']}", use_container_width=True, type="secondary"):
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
                            st.session_state["pending_cross_tab_jump"] = {
                                "tab_index": 0,
                                "tab_name": "🌱 新资建仓",
                                "action_name": "入备选池",
                                "target_title": f"{sec_fund.get('name', fcode)} ({fcode})",
                                "detail": "已自动注入关注池并聚焦至新资建仓配置引擎",
                                "timestamp": datetime.now().strftime("%H:%M:%S")
                            }
                            st.session_state["last_cross_tab_action"] = dict(st.session_state["pending_cross_tab_jump"])
                            st.toast(f"✅ 已将【{sec_fund.get('name')}】一键纳入备选池，正在为您导向新资建仓！")
                            st.rerun()'''

assert old_top3_sectors in content, "old_top3_sectors not found"
content = content.replace(old_top3_sectors, new_top3_sectors, 1)

# Right-wing sentry header & container height & button actions
old_sentry_block = '''            # --- 右翼：主动风险哨 ---
            with col_sentry:
                st.markdown("<div style='font-size: 14px; font-weight: 700; color: var(--text-primary); margin-bottom: 8px;'>🚨 主动风险预警哨 · 六维主动巡检 <span style='font-size: 11px; font-weight: 400; color: var(--text-secondary);'>[主动风险预警哨 · 四维巡检升级版]</span></div>", unsafe_allow_html=True)
                sentry = ActiveRiskSentry()
                _f_metas = {}
                for _c in pm_instance.holdings.keys():
                    try:
                        _f_metas[_c] = data_loader.get_fund_metadata(_c) or {}
                    except Exception:
                        _f_metas[_c] = {}
                report = sentry.inspect_portfolio(pm_instance.holdings, snapshot_dict, fund_metadata=_f_metas)

                with st.container(height=300):'''

new_sentry_block = '''            # --- 右翼：主动风险哨 ---
            with col_sentry:
                st.markdown("<div style='font-size: 14px; font-weight: 700; color: var(--text-primary); margin-bottom: 8px;'>🚨 主动风险预警哨 · 六维主动巡检</div>", unsafe_allow_html=True)
                sentry = ActiveRiskSentry()
                _f_metas = {}
                for _c in pm_instance.holdings.keys():
                    try:
                        _f_metas[_c] = data_loader.get_fund_metadata(_c) or {}
                    except Exception:
                        _f_metas[_c] = {}
                report = sentry.inspect_portfolio(pm_instance.holdings, snapshot_dict, fund_metadata=_f_metas)

                with st.container(height=380):'''

assert old_sentry_block in content, "old_sentry_block not found"
content = content.replace(old_sentry_block, new_sentry_block, 1)

# Sentry buttons: batch lock & individual actions
old_batch_lock_btn = '''                            if st.button(f"🔒 一键批量锁定这 {len(lock_alerts)} 只标的调仓下界", key="btn_batch_lock_all_7d", use_container_width=True, type="primary"):
                                if "tab2_locked_funds" not in st.session_state:
                                    st.session_state.tab2_locked_funds = []
                                for fc in lock_codes:
                                    if fc and fc not in st.session_state.tab2_locked_funds:
                                        st.session_state.tab2_locked_funds.append(fc)
                                st.session_state.tab2_diagnosed = True
                                st.session_state.tab2_rebalanced = True
                                st.session_state.tab2_rebal_cache = None
                                st.session_state.tab2_trigger_diagnose = False
                                st.session_state.tab2_trigger_rebalance = False
                                st.toast(f"🔒 已一键批量锁定 {len(lock_codes)} 只标的持仓下界，已在【💼 持仓调仓】生效！")
                                st.rerun()'''

new_batch_lock_btn = '''                            if st.button(f"🔒 一键批量锁定这 {len(lock_alerts)} 只标的调仓下界", key="btn_batch_lock_all_7d", use_container_width=True, type="primary"):
                                if "tab2_locked_funds" not in st.session_state:
                                    st.session_state.tab2_locked_funds = []
                                for fc in lock_codes:
                                    if fc and fc not in st.session_state.tab2_locked_funds:
                                        st.session_state.tab2_locked_funds.append(fc)
                                st.session_state.tab2_diagnosed = True
                                st.session_state.tab2_rebalanced = True
                                st.session_state.tab2_rebal_cache = None
                                st.session_state.tab2_trigger_diagnose = False
                                st.session_state.tab2_trigger_rebalance = False
                                st.session_state["pending_cross_tab_jump"] = {
                                    "tab_index": 1,
                                    "tab_name": "💼 持仓调仓",
                                    "action_name": "批量锁定",
                                    "target_title": f"批量锁定 {len(lock_codes)} 只标的",
                                    "detail": "已下达持仓下界禁卖风控指令",
                                    "timestamp": datetime.now().strftime("%H:%M:%S")
                                }
                                st.session_state["last_cross_tab_action"] = dict(st.session_state["pending_cross_tab_jump"])
                                st.toast(f"🔒 已一键批量锁定 {len(lock_codes)} 只标的持仓下界，已在【💼 持仓调仓】生效！")
                                st.rerun()'''

assert old_batch_lock_btn in content, "old_batch_lock_btn not found"
content = content.replace(old_batch_lock_btn, new_batch_lock_btn, 1)

# Individual sentry actions
old_indiv_sentry_btns = '''                            col_s_a, col_s_b = st.columns(2)
                            with col_s_a:
                                if st.button(btn_lbl, key=f"btn_sentry_act_{i}_{fcode}_{act_type}", use_container_width=True, type="secondary"):
                                    st.session_state["tab2_view_mode"] = "🎯 持仓诊断与智能调仓 (主流程)"
                                    if act_type == "lock_shares":
                                        if "tab2_locked_funds" not in st.session_state:
                                            st.session_state.tab2_locked_funds = []
                                        if fcode and fcode not in st.session_state.tab2_locked_funds:
                                            st.session_state.tab2_locked_funds.append(fcode)
                                    elif act_type == "take_profit":
                                        st.session_state.tab2_pending_take_profit = {"fund_code": fcode, "ratio": 0.40}
                                    elif act_type == "switch_a_class":
                                        st.session_state.tab2_c_replace = fcode
                                    st.session_state.tab2_diagnosed = True
                                    st.session_state.tab2_rebalanced = True
                                    st.session_state.tab2_rebal_cache = None
                                    st.session_state.tab2_trigger_diagnose = False
                                    st.session_state.tab2_trigger_rebalance = False
                                    st.toast(f"⚡ 已生成针对【{fcode or alert.get('title')}】的处置意图，已就绪于【💼 持仓调仓】！")
                                    st.rerun()
                            with col_s_b:
                                if st.button("🔍 穿透到底层", key=f"btn_sentry_evid_{i}_{fcode}_{act_type}", use_container_width=True):
                                    mod_key = "correlation_mutation" if "相关" in alert.get("title", "") else ("stock_overlap" if "重仓" in alert.get("title", "") else "holding_days_fifo")
                                    st.session_state["tab4_highlight_module"] = mod_key
                                    st.session_state["tab4_highlight_fund"] = fcode
                                    st.session_state["tab4_highlight_title"] = alert.get("title", "")
                                    st.toast(f"🔍 已锁定【{alert.get('title')}】，已在【🔍 穿透工具】高亮展现证据！")
                                    st.rerun()'''

new_indiv_sentry_btns = '''                            col_s_a, col_s_b = st.columns(2)
                            with col_s_a:
                                if st.button(btn_lbl, key=f"btn_sentry_act_{i}_{fcode}_{act_type}", use_container_width=True, type="secondary"):
                                    st.session_state["tab2_view_mode"] = "🎯 持仓诊断与智能调仓 (主流程)"
                                    if act_type in ["lock_shares", "countdown_hold"]:
                                        if "tab2_locked_funds" not in st.session_state:
                                            st.session_state.tab2_locked_funds = []
                                        if fcode and fcode not in st.session_state.tab2_locked_funds:
                                            st.session_state.tab2_locked_funds.append(fcode)
                                    elif act_type in ["take_profit", "deep_loss_rebalance", "rebalance_sector"]:
                                        st.session_state.tab2_pending_take_profit = {"fund_code": fcode, "ratio": 0.40}
                                    elif act_type in ["switch_a_class", "replace_fund"]:
                                        st.session_state.tab2_c_replace = fcode
                                    elif act_type in ["defense_mode", "offense_mode"]:
                                        st.session_state.active_tier_val = "C2" if act_type == "defense_mode" else "C4"

                                    st.session_state.tab2_diagnosed = True
                                    st.session_state.tab2_rebalanced = True
                                    st.session_state.tab2_rebal_cache = None
                                    st.session_state.tab2_trigger_diagnose = False
                                    st.session_state.tab2_trigger_rebalance = False
                                    st.session_state["pending_cross_tab_jump"] = {
                                        "tab_index": 1,
                                        "tab_name": "💼 持仓调仓",
                                        "action_name": f"处置预警:{alert.get('title')}",
                                        "target_title": f"{fname} ({fcode})",
                                        "detail": f"已将主动风控指令注入调仓优化器，执行应对: {btn_lbl}",
                                        "timestamp": datetime.now().strftime("%H:%M:%S")
                                    }
                                    st.session_state["last_cross_tab_action"] = dict(st.session_state["pending_cross_tab_jump"])
                                    st.toast(f"⚡ 已生成针对【{fcode or alert.get('title')}】的处置意图，已就绪于【💼 持仓调仓】！")
                                    st.rerun()
                            with col_s_b:
                                if st.button("🔍 穿透到底层", key=f"btn_sentry_evid_{i}_{fcode}_{act_type}", use_container_width=True):
                                    mod_key = "correlation_mutation" if "相关" in alert.get("title", "") else ("stock_overlap" if "重仓" in alert.get("title", "") else "holding_days_fifo")
                                    st.session_state["tab4_highlight_module"] = mod_key
                                    st.session_state["tab4_highlight_fund"] = fcode
                                    st.session_state["tab4_highlight_title"] = alert.get("title", "")
                                    st.session_state["pending_cross_tab_jump"] = {
                                        "tab_index": 3,
                                        "tab_name": "🔍 穿透工具",
                                        "action_name": "穿透证据",
                                        "target_title": f"{fname} ({fcode})",
                                        "detail": "已锁定底层穿透排雷与重仓股证据链",
                                        "timestamp": datetime.now().strftime("%H:%M:%S")
                                    }
                                    st.session_state["last_cross_tab_action"] = dict(st.session_state["pending_cross_tab_jump"])
                                    st.toast(f"🔍 已锁定【{alert.get('title')}】，已在【🔍 穿透工具】高亮展现证据！")
                                    st.rerun()'''

assert old_indiv_sentry_btns in content, "old_indiv_sentry_btns not found"
content = content.replace(old_indiv_sentry_btns, new_indiv_sentry_btns, 1)

# Post dashboard banner & DOM router
old_post_dashboard = "render_dual_wing_advisory_dashboard(pm, snapshot)\n"
new_post_dashboard = '''render_dual_wing_advisory_dashboard(pm, snapshot)

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
    st.session_state.pop("pending_cross_tab_jump", None)
'''

assert old_post_dashboard in content, "old_post_dashboard not found"
content = content.replace(old_post_dashboard, new_post_dashboard, 1)

# -------------------------------------------------------------
# 4. Tab 1 Capital Captions
# -------------------------------------------------------------
old_cap_a = '''                    plan_capital = st.number_input(
                        "💵 拟投资总本金 (元)",
                        min_value=1000.0,
                        max_value=100000000.0,
                        value=100000.0,
                        step=10000.0,
                        format="%.0f",
                        key="plan_capital_input"
                    )'''

new_cap_a = '''                    plan_capital = st.number_input(
                        "💵 拟投资总本金 (元)",
                        min_value=1000.0,
                        max_value=100000000.0,
                        value=100000.0,
                        step=10000.0,
                        format="%.0f",
                        key="plan_capital_input"
                    )
                    plan_cap = plan_capital
                    st.caption(f"🔢 **金额核对**：{format_chinese_amount(plan_cap)}")'''

assert old_cap_a in content, "old_cap_a not found"
content = content.replace(old_cap_a, new_cap_a, 1)

old_cap_b = '''                    plan_capital = st.number_input(
                        "💵 拟投资总本金 (元)",
                        min_value=1000.0,
                        max_value=100000000.0,
                        value=100000.0,
                        step=10000.0,
                        format="%.0f",
                        key="plan_capital_input_b"
                    )'''

new_cap_b = '''                    plan_capital = st.number_input(
                        "💵 拟投资总本金 (元)",
                        min_value=1000.0,
                        max_value=100000000.0,
                        value=100000.0,
                        step=10000.0,
                        format="%.0f",
                        key="plan_capital_input_b"
                    )
                    plan_cap_b = plan_capital
                    st.caption(f"🔢 **金额核对**：{format_chinese_amount(plan_cap_b)}")'''

assert old_cap_b in content, "old_cap_b not found"
content = content.replace(old_cap_b, new_cap_b, 1)

# -------------------------------------------------------------
# 5. Tab 1 Step 3 Overwrite Popover + Undo
# -------------------------------------------------------------
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

# -------------------------------------------------------------
# 6. Tab 2 Multi-ledger new ledger cash caption
# -------------------------------------------------------------
old_new_ledger_cash = '''                    n_cash = st.number_input("初始可用现金 (元)", min_value=0.0, value=100000.0, step=10000.0, key="pop_new_ledger_cash")'''
new_new_ledger_cash = '''                    n_cash = st.number_input("初始可用现金 (元)", min_value=0.0, value=100000.0, step=10000.0, key="pop_new_ledger_cash")
                    st.caption(f"🔢 **金额核对**：{format_chinese_amount(n_cash)}")'''

assert old_new_ledger_cash in content, "old_new_ledger_cash not found"
content = content.replace(old_new_ledger_cash, new_new_ledger_cash, 1)

# -------------------------------------------------------------
# 7. Tab 2 Quick add bar: format_chinese_amount & uncommitted check hook
# -------------------------------------------------------------
old_quick_add = '''            with col_bar_amt:
                bar_amt_in = st.number_input("持有金额 (元)", value=10000.0, step=1000.0, min_value=100.0, key="bar_amt_input")
            with col_bar_pnl:'''

new_quick_add = '''            with col_bar_amt:
                bar_amt_in = st.number_input("持有金额 (元)", value=10000.0, step=1000.0, min_value=100.0, key="bar_amt_input")
                st.caption(f"🔢 **金额核对**：{format_chinese_amount(bar_amt_in)}")
            with col_bar_pnl:'''

assert old_quick_add in content, "old_quick_add not found"
content = content.replace(old_quick_add, new_quick_add, 1)

old_add_btn = '''            with col_bar_btn:
                st.write(" ")
                st.write(" ")
                if st.button("➕ 加入账本", type="primary", use_container_width=True, key="btn_bar_add_holding"):
                    raw_in = bar_fund_in.strip()'''

new_add_btn = '''            with col_bar_btn:
                st.write(" ")
                st.write(" ")
                if st.button("➕ 加入账本", type="primary", use_container_width=True, key="btn_bar_add_holding"):
                    if "tab2_cached_edited_table" in st.session_state and st.session_state.tab2_cached_edited_table is not None:
                        _ch, _ = _has_uncommitted_holdings_changes(st.session_state.tab2_cached_edited_table, pm)
                        if _ch:
                            _commit_edited_holdings_table(st.session_state.tab2_cached_edited_table, pm)
                    raw_in = bar_fund_in.strip()'''

assert old_add_btn in content, "old_add_btn not found"
content = content.replace(old_add_btn, new_add_btn, 1)

# -------------------------------------------------------------
# 8. Holdings data_editor: warn_placeholder, uncommitted check, and 5 operation buttons
# -------------------------------------------------------------
old_editor_pre = '''            safe_markdown_html("<div style='height: 4px;'></div>")
            st.caption("实时持仓资产明细（💡 仅需修改/录入 **「基金代码」** 与 **「当前市值(元)」** 或 **「持仓份额」**，保存时后台自动联网补齐真实名称、最新净值与盘中估值，其余指标全自动跳出）：")

            edited_table = st.data_editor('''

new_editor_pre = '''            safe_markdown_html("<div style='height: 4px;'></div>")
            st.caption("实时持仓资产明细（💡 仅需修改/录入 **「基金代码」** 与 **「当前市值(元)」** 或 **「持仓份额」**，保存时后台自动联网补齐真实名称、最新净值与盘中估值，其余指标全自动跳出）：")
            warn_placeholder = st.empty()

            edited_table = st.data_editor('''

assert old_editor_pre in content, "old_editor_pre not found"
content = content.replace(old_editor_pre, new_editor_pre, 1)

old_editor_post = '''                num_rows="dynamic",
                key="main_holdings_editor_tab2"
            )

            # 拉齐操作栏：等高 5 列工具栏（含现金池修改 Popover）'''

new_editor_post = '''                num_rows="dynamic",
                key="main_holdings_editor_tab2"
            )
            st.session_state["tab2_cached_edited_table"] = edited_table
            has_uncommitted, change_details = _has_uncommitted_holdings_changes(edited_table, pm)
            if has_uncommitted:
                tip_summary = "；".join(change_details[:3]) + (f" 等共 {len(change_details)} 项改动" if len(change_details) > 3 else "")
                warn_placeholder.markdown(f"""
                <div style="background: rgba(239, 68, 68, 0.12); border: 1.5px solid var(--color-up); border-radius: 6px; padding: 10px 14px; margin-bottom: 8px;">
                    <div style="font-size: 13px; font-weight: 700; color: var(--color-up); margin-bottom: 2px;">
                        ⚠️ 检测到持仓明细表存在未保存的修改（{tip_summary}）！
                    </div>
                    <div style="font-size: 11px; color: var(--text-secondary);">
                        为防止操作其他功能导致数据被重置，请及时点击表格下方的 <b>【💾 保存修改并入库】</b> 按钮保存。
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                warn_placeholder.empty()

            # 拉齐操作栏：等高 5 列工具栏（含现金池修改 Popover）'''

assert old_editor_post in content, "old_editor_post not found"
content = content.replace(old_editor_post, new_editor_post, 1)

# 5 op buttons: col_op2, col_op3, col_op5
old_col_op2 = '''            with col_op2:
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
                        st.rerun()'''

new_col_op2 = '''            with col_op2:
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
                        st.rerun()'''

assert old_col_op2 in content, "old_col_op2 not found"
content = content.replace(old_col_op2, new_col_op2, 1)

old_col_op3 = '''            with col_op3:
                if st.button("🔄 同步真实净值", use_container_width=True, help="拉取最新净值/盘中估值刷新持仓", key="btn_sync_holdings_tab2"):
                    with st.spinner("🔄 同步中..."):
                        s_res = pm.sync_holdings_live_nav(use_intraday_gsz=True)
                    st.success(f"✅ 已同步 {s_res.get('updated_count', 0)} 只标的真实净值。")
                    st.rerun()'''

new_col_op3 = '''            with col_op3:
                if st.button("🔄 同步真实净值", use_container_width=True, help="拉取最新净值/盘中估值刷新持仓", key="btn_sync_holdings_tab2"):
                    if "edited_table" in locals() and edited_table is not None:
                        _commit_edited_holdings_table(edited_table, pm)
                    with st.spinner("🔄 同步中..."):
                        s_res = pm.sync_holdings_live_nav(use_intraday_gsz=True)
                    st.success(f"✅ 已同步 {s_res.get('updated_count', 0)} 只标的真实净值。")
                    st.rerun()'''

assert old_col_op3 in content, "old_col_op3 not found"
content = content.replace(old_col_op3, new_col_op3, 1)

old_col_op5 = '''                    if del_sel != "-- 请选择 --":
                        if st.button(f"确认删除 {del_sel}", type="primary", use_container_width=True, key="btn_pop_del_confirm_tab2"):
                            pm.delete_holding(del_sel)
                            st.session_state.tab2_diag_cache = None
                            st.session_state.tab2_rebal_cache = None
                            st.session_state.tab2_diagnosed = False
                            st.session_state.tab2_rebalanced = False
                            st.success(f"已删除 {del_sel}")
                            st.rerun()'''

new_col_op5 = '''                    if del_sel != "-- 请选择 --":
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

assert old_col_op5 in content, "old_col_op5 not found"
content = content.replace(old_col_op5, new_col_op5, 1)

# -------------------------------------------------------------
# 9. Step 3 Scenarios: format_chinese_amount
# -------------------------------------------------------------
old_sc_new_cash = '''                with c_sc_in1:
                    new_cash_val = st.number_input("💵 本次计划新增注入的补仓资金 (元)", value=20000.0, step=1000.0, min_value=100.0, key="num_sc_new_cash")
                with c_sc_in2:'''

new_sc_new_cash = '''                with c_sc_in1:
                    new_cash_val = st.number_input("💵 本次计划新增注入的补仓资金 (元)", value=20000.0, step=1000.0, min_value=100.0, key="num_sc_new_cash")
                    st.caption(f"🔢 **金额核对**：{format_chinese_amount(new_cash_val)}")
                with c_sc_in2:'''

assert old_sc_new_cash in content, "old_sc_new_cash not found"
content = content.replace(old_sc_new_cash, new_sc_new_cash, 1)

old_sc_withdraw_cash = '''                with c_sc_in1:
                    withdraw_cash_val = st.number_input("🏧 本次急需提取现金金额 (元)", value=30000.0, step=1000.0, min_value=100.0, key="num_sc_withdraw_cash")
                with c_sc_in2:'''

new_sc_withdraw_cash = '''                with c_sc_in1:
                    withdraw_cash_val = st.number_input("🏧 本次急需提取现金金额 (元)", value=30000.0, step=1000.0, min_value=100.0, key="num_sc_withdraw_cash")
                    st.caption(f"🔢 **金额核对**：{format_chinese_amount(withdraw_cash_val)}")
                with c_sc_in2:'''

assert old_sc_withdraw_cash in content, "old_sc_withdraw_cash not found"
content = content.replace(old_sc_withdraw_cash, new_sc_withdraw_cash, 1)

# -------------------------------------------------------------
# 10. Clean duplicate slider from Tab 2 top (col_t2_buf)
# -------------------------------------------------------------
old_env_cols = '''        col_t2_env1, col_t2_env2, col_t2_env3, col_t2_buf = st.columns([2.5, 2.5, 2.5, 4.5])
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

new_env_cols = '''        col_t2_env1, col_t2_env2, col_t2_env3 = st.columns(3)
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

assert old_env_cols in content, "old_env_cols not found"
content = content.replace(old_env_cols, new_env_cols, 1)

# -------------------------------------------------------------
# 11. Tab 2 Step 1 bottom buttons: remove duplicate slider, keep comment, auto-commit & auto-heal
# -------------------------------------------------------------
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
        col_t2_btn1, col_t2_btn2 = st.columns([6, 4])
        with col_t2_btn1:
            if st.button("🔍 诊断今日调仓时机", type="primary", use_container_width=True, key="btn_tab2_diagnose"):
                st.session_state["tab2_view_mode"] = "🎯 持仓诊断与智能调仓 (主流程)"
                # 💡 自动拦截并同步表格未保存修改，杜绝丢数
                if "edited_table" in locals() and edited_table is not None:
                    _commit_edited_holdings_table(edited_table, pm)
                st.session_state.tab2_diagnosed = True
                st.session_state.tab2_trigger_diagnose = True
                st.rerun()
        with col_t2_btn2:
            if st.button("🚀 一键执行全案", type="secondary", use_container_width=True, key="btn_tab2_all"):
                st.session_state["tab2_view_mode"] = "🎯 持仓诊断与智能调仓 (主流程)"
                if "edited_table" in locals() and edited_table is not None:
                    _commit_edited_holdings_table(edited_table, pm)
                st.session_state.tab2_diagnosed = True
                st.session_state.tab2_rebalanced = True
                st.session_state.tab2_trigger_diagnose = True
                st.session_state.tab2_trigger_rebalance = True
                st.rerun()

        st.info("🛠️ 需快速记账、检视 FIFO 批次或对账？请点击上方切换至【💼 账本运维与实盘复盘档案】宽屏工具坞。")'''

assert old_step1_bot in content, "old_step1_bot not found"
content = content.replace(old_step1_bot, new_step1_bot, 1)

# -------------------------------------------------------------
# 12. Structural extraction of Tool Dock and True Physical Branch Isolation
# -------------------------------------------------------------
dock_start_marker = "        # ── G7: 工具坞仅在【💼 账本运维与实盘复盘档案】宽屏展示，主流程保持极致聚焦 ──"
step1_bot_marker = "        # 步骤一底部推进按钮 (已清理底部重复滑块，保留 tab2_rebal_buf_slider_bot 兼容注释)"
tab2_end_marker = "    except Exception as e:\n        st.error(f\"⚠️ 【💼 持仓调仓】渲染出现局部异常: {e}\")"

assert dock_start_marker in content, "dock_start_marker not found"
assert step1_bot_marker in content, "step1_bot_marker not found"
assert tab2_end_marker in content, "tab2_end_marker not found"

p_dock_start = content.index(dock_start_marker)
p_step1_bot = content.index(step1_bot_marker)
dock_block = content[p_dock_start:p_step1_bot]

# In dock_block, find the tabs block
tabs_start_str = 'dock_tab1, dock_tab2, dock_tab3, dock_tab4, dock_tab5, dock_tab6 = st.tabs(['
assert tabs_start_str in dock_block, "tabs_start_str not found in dock_block"
idx_tabs = dock_block.index(tabs_start_str)

# From tabs start to end of dock_block:
inside_tabs = dock_block[idx_tabs:]

# Remove duplicate buttons in dock_tab3
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
                        st.rerun()'''

assert old_dock3_buttons in inside_tabs, "old_dock3_buttons not found in inside_tabs"
inside_tabs = inside_tabs.replace(old_dock3_buttons, "")

# Unindent inside_tabs by 4 spaces
unindented_dock_lines = []
for line in inside_tabs.split("\n"):
    if line.startswith("            "):
        unindented_dock_lines.append("        " + line[12:])
    elif line.startswith("        "):
        unindented_dock_lines.append(line)
    elif line.strip() == "":
        unindented_dock_lines.append("")
    else:
        unindented_dock_lines.append(line)

new_dock_block = '''        else:
            # ── 模式二：💼 账本运维与实盘复盘档案 (独立宽屏工具坞，全宽平铺无 expander) ──
            st.markdown("### 💼 账本运维与实盘复盘档案 (独立宽屏工具坞)")
            st.caption("提供快速录入、FIFO批次透视、实盘影子档案、T+1对账、同公司转换及宏观分红研判全套工具。")
        ''' + "\n".join(unindented_dock_lines).lstrip()

# Remove the dock block from its original position between holdings table and step 1 bot buttons
content = content[:p_dock_start] + content[p_step1_bot:]

# Now wrap the main flow in `if is_t2_main_mode:` and append `new_dock_block` right before `tab2_end_marker`
main_flow_start = "        # 🛡️ 浮盈安全垫抗震承压与本金破净临界看板 (重构升级原静态纯文字横幅)"
assert main_flow_start in content, "main_flow_start not found"
p_main_start = content.index(main_flow_start)
p_main_end = content.index(tab2_end_marker)

main_flow_code = content[p_main_start:p_main_end]

indented_main_flow_lines = []
for line in main_flow_code.split("\n"):
    if line.strip():
        indented_main_flow_lines.append("    " + line)
    else:
        indented_main_flow_lines.append("")

indented_main_flow = "\n".join(indented_main_flow_lines)

full_tab2_replacement = f'''        if is_t2_main_mode:
{indented_main_flow}
{new_dock_block}
'''

content = content[:p_main_start] + full_tab2_replacement + content[p_main_end:]

gui_path.write_text(content, encoding="utf-8")
print(f"Patched content length: {len(content)}")
print("Successfully applied G8 complete patch to app_gui.py!")
