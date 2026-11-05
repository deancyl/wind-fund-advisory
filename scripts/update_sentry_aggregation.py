# -*- coding: utf-8 -*-
from pathlib import Path

p = Path("AGY2_FundAdvisory/app_gui.py")
content = p.read_text(encoding="utf-8")

old_sentry_block = '''                if report.get("all_passed"):
                    st.markdown("""
                    <div class="decision-card" style="border-left: 4px solid var(--color-down); padding: 12px 14px;">
                        <div style="font-weight: 700; color: var(--color-down); font-size: 13px; margin-bottom: 4px;">🟢 主动风控巡检全通</div>
                        <div style="font-size: 11px; color: var(--text-secondary); line-height: 1.6;">
                            持仓批次无惩罚锁仓 ｜ 赛道无超买拥挤 ｜ 零迷你基清盘风险 ｜ 大盘运行于安全区间
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    alerts_to_show = report.get("alerts", [])[:4]
                    for i, alert in enumerate(alerts_to_show):
                        border_c = "var(--color-up)" if alert["level"] == "red" else ("var(--color-down)" if alert["level"] == "green_notice" else "var(--accent-primary)")
                        badge_icon = "🔴" if alert["level"] == "red" else ("🟢" if alert["level"] == "green_notice" else "🟡")
                        st.markdown(f"""
                        <div class="decision-card" style="border-left: 3px solid {border_c}; padding: 8px 10px; margin-bottom: 4px;">
                            <div style="font-size: 12px; font-weight: 700; color: var(--text-primary); margin-bottom: 2px;">
                                {badge_icon} {alert['title']}
                            </div>
                            <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 2px;">
                                {alert['desc']}
                            </div>
                            <div style="font-size: 11px; color: {border_c}; font-weight: 600;">
                                💡 建议: {alert['action']}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                        act_type = alert.get("action_type")
                        fcode = alert.get("fund_code", "")
                        fname = alert.get("fund_name", fcode)

                        if act_type == "lock_shares":
                            btn_lbl = f"🔒 锁定【{fcode or '未满7天标的'}】调仓下界"
                        elif act_type == "countdown_hold":
                            btn_lbl = f"⏳ 暂缓【{fcode}】调仓倒计时"
                        elif act_type == "switch_a_class":
                            btn_lbl = f"🔄 择机置换【{fcode}】为A类"
                        elif act_type == "take_profit":
                            btn_lbl = f"📉 生成【{fcode or '超买标的'}】阶梯止盈单"
                        elif act_type == "deep_loss_rebalance":
                            btn_lbl = f"💼 查看【{fcode}】反弹减亏诊断"
                        elif act_type == "rebalance_sector":
                            btn_lbl = "⚖️ 平衡赛道敞口"
                        elif act_type == "replace_fund":
                            btn_lbl = f"🚨 置换【{fcode}】为标杆公募"
                        elif act_type == "defense_mode":
                            btn_lbl = "🛡️ 启动防守预案"
                        elif act_type == "offense_mode":
                            btn_lbl = "🚀 查看进攻主线"
                        else:
                            btn_lbl = "⚡ 立即处置"

                        if st.button(btn_lbl, key=f"btn_sentry_act_{i}_{fcode}_{act_type}", use_container_width=True, type="secondary"):
                            if act_type == "lock_shares":
                                if "tab2_locked_funds" not in st.session_state:
                                    st.session_state.tab2_locked_funds = []
                                if fcode and fcode not in st.session_state.tab2_locked_funds:
                                    st.session_state.tab2_locked_funds.append(fcode)
                                st.session_state.tab2_diagnosed = True
                                st.session_state.tab2_rebalanced = True
                                st.session_state.tab2_rebal_cache = None
                                st.session_state.tab2_trigger_diagnose = False
                                st.session_state.tab2_trigger_rebalance = False
                                st.toast(f"🔒 已锁定标的【{fcode}】持仓下界，已在【💼 持仓调仓】生成调仓保护单！")
                                st.rerun()
                            elif act_type == "take_profit":
                                st.session_state.tab2_pending_take_profit = {"fund_code": fcode, "ratio": 0.40}
                                st.session_state.tab2_diagnosed = True
                                st.session_state.tab2_rebalanced = True
                                st.session_state.tab2_rebal_cache = None
                                st.session_state.tab2_trigger_diagnose = False
                                st.session_state.tab2_trigger_rebalance = False
                                st.toast(f"📉 已生成【{fcode}】阶梯止盈单（建议减持40%），已在【💼 持仓调仓】更新调仓方案！")
                                st.rerun()
                            elif act_type == "deep_loss_rebalance":
                                st.session_state.tab2_diagnosed = True
                                st.session_state.tab2_rebalanced = True
                                st.session_state.tab2_rebal_cache = None
                                st.session_state.tab2_trigger_diagnose = False
                                st.session_state.tab2_trigger_rebalance = False
                                st.toast(f"💼 正在为深套标的【{fcode}】生成反弹抽均线阶梯减亏诊断，已在【💼 持仓调仓】就绪！")
                                st.rerun()
                            elif act_type == "countdown_hold":
                                st.session_state.tab2_diagnosed = True
                                st.session_state.tab2_rebalanced = True
                                st.session_state.tab2_rebal_cache = None
                                st.toast(f"⏳ 已为【{fcode}】设置免赎倒计时保护，建议持有满 30 天后再行操作")
                                st.rerun()
                            elif act_type == "switch_a_class":
                                st.session_state.tab2_c_replace = fcode
                                st.session_state.tab2_diagnosed = True
                                st.session_state.tab2_rebalanced = True
                                st.session_state.tab2_rebal_cache = None
                                st.session_state.tab2_trigger_diagnose = False
                                st.session_state.tab2_trigger_rebalance = False
                                st.toast(f"🔄 已激活【{fcode}】C类零费率置换指令，已在【💼 持仓调仓】更新！")
                                st.rerun()
                            else:
                                st.session_state.tab2_diagnosed = True
                                st.session_state.tab2_rebalanced = True
                                st.session_state.tab2_rebal_cache = None
                                st.session_state.tab2_trigger_diagnose = False
                                st.session_state.tab2_trigger_rebalance = False
                                st.toast(f"⚡ 请前往【💼 持仓调仓】Tab 查看针对【{fcode}】的调仓建议")
                                st.rerun()'''

new_sentry_block = '''                with st.container(height=300):
                    if report.get("all_passed"):
                        st.markdown("""
                        <div class="decision-card" style="border-left: 4px solid var(--color-down); padding: 12px 14px;">
                            <div style="font-weight: 700; color: var(--color-down); font-size: 13px; margin-bottom: 4px;">🟢 主动风控巡检全通</div>
                            <div style="font-size: 11px; color: var(--text-secondary); line-height: 1.6;">
                                持仓批次无惩罚锁仓 ｜ 赛道无超买拥挤 ｜ 零迷你基清盘风险 ｜ 大盘运行于安全区间
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        all_alerts = report.get("alerts", [])
                        lock_alerts = [a for a in all_alerts if a.get("action_type") == "lock_shares"]
                        other_alerts = [a for a in all_alerts if a.get("action_type") != "lock_shares"]

                        # 1. 若同属未满 7 天惩罚锁仓标的 >= 2 只，行内聚合折叠为单张紧凑聚合卡片
                        if len(lock_alerts) >= 2:
                            lock_codes = [a.get("fund_code", "") for a in lock_alerts if a.get("fund_code")]
                            lock_names = [f"{a.get('fund_code')} ({a.get('fund_name', a.get('fund_code'))[:5]})" for a in lock_alerts]
                            st.markdown(f"""
                            <div class="decision-card" style="border-left: 3px solid var(--color-up); padding: 8px 10px; margin-bottom: 6px;">
                                <div style="font-size: 12px; font-weight: 700; color: var(--text-primary); margin-bottom: 2px;">
                                    🔴【未满7天锁定期硬阻断】共 {len(lock_alerts)} 只标的持有未满7天
                                </div>
                                <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 2px;">
                                    包含标的: {', '.join(lock_names)}。未满 7 天赎回将直接触发证监会规定的 1.50% 巨额惩罚性扣款！
                                </div>
                                <div style="font-size: 11px; color: var(--color-up); font-weight: 600;">
                                    💡 建议: 一键锁定持仓下界，严禁盲目减持，待各标的持有满 7 天后再行操作。
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            if st.button(f"🔒 一键批量锁定这 {len(lock_alerts)} 只标的调仓下界", key="btn_batch_lock_all_7d", use_container_width=True, type="primary"):
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
                                st.rerun()
                        elif len(lock_alerts) == 1:
                            other_alerts = lock_alerts + other_alerts

                        # 2. 渲染其他单标的预警
                        for i, alert in enumerate(other_alerts[:3]):
                            border_c = "var(--color-up)" if alert["level"] == "red" else ("var(--color-down)" if alert["level"] == "green_notice" else "var(--accent-primary)")
                            badge_icon = "🔴" if alert["level"] == "red" else ("🟢" if alert["level"] == "green_notice" else "🟡")
                            st.markdown(f"""
                            <div class="decision-card" style="border-left: 3px solid {border_c}; padding: 8px 10px; margin-bottom: 4px;">
                                <div style="font-size: 12px; font-weight: 700; color: var(--text-primary); margin-bottom: 2px;">
                                    {badge_icon} {alert['title']}
                                </div>
                                <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 2px;">
                                    {alert['desc']}
                                </div>
                                <div style="font-size: 11px; color: {border_c}; font-weight: 600;">
                                    💡 建议: {alert['action']}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

                            act_type = alert.get("action_type")
                            fcode = alert.get("fund_code", "")
                            fname = alert.get("fund_name", fcode)

                            if act_type == "lock_shares":
                                btn_lbl = f"🔒 锁定【{fcode or '未满7天标的'}】调仓下界"
                            elif act_type == "countdown_hold":
                                btn_lbl = f"⏳ 暂缓【{fcode}】调仓倒计时"
                            elif act_type == "switch_a_class":
                                btn_lbl = f"🔄 择机置换【{fcode}】为A类"
                            elif act_type == "take_profit":
                                btn_lbl = f"📉 生成【{fcode or '超买标的'}】阶梯止盈单"
                            elif act_type == "deep_loss_rebalance":
                                btn_lbl = f"💼 查看【{fcode}】反弹减亏诊断"
                            elif act_type == "rebalance_sector":
                                btn_lbl = "⚖️ 平衡赛道敞口"
                            elif act_type == "replace_fund":
                                btn_lbl = f"🚨 置换【{fcode}】为标杆公募"
                            elif act_type == "defense_mode":
                                btn_lbl = "🛡️ 启动防守预案"
                            elif act_type == "offense_mode":
                                btn_lbl = "🚀 查看进攻主线"
                            else:
                                btn_lbl = "⚡ 立即处置"

                            if st.button(btn_lbl, key=f"btn_sentry_act_{i}_{fcode}_{act_type}", use_container_width=True, type="secondary"):
                                if act_type == "lock_shares":
                                    if "tab2_locked_funds" not in st.session_state:
                                        st.session_state.tab2_locked_funds = []
                                    if fcode and fcode not in st.session_state.tab2_locked_funds:
                                        st.session_state.tab2_locked_funds.append(fcode)
                                    st.session_state.tab2_diagnosed = True
                                    st.session_state.tab2_rebalanced = True
                                    st.session_state.tab2_rebal_cache = None
                                    st.session_state.tab2_trigger_diagnose = False
                                    st.session_state.tab2_trigger_rebalance = False
                                    st.toast(f"🔒 已锁定标的【{fcode}】持仓下界，已在【💼 持仓调仓】生成调仓保护单！")
                                    st.rerun()
                                elif act_type == "take_profit":
                                    st.session_state.tab2_pending_take_profit = {"fund_code": fcode, "ratio": 0.40}
                                    st.session_state.tab2_diagnosed = True
                                    st.session_state.tab2_rebalanced = True
                                    st.session_state.tab2_rebal_cache = None
                                    st.session_state.tab2_trigger_diagnose = False
                                    st.session_state.tab2_trigger_rebalance = False
                                    st.toast(f"📉 已生成【{fcode}】阶梯止盈单（建议减持40%），已在【💼 持仓调仓】更新调仓方案！")
                                    st.rerun()
                                elif act_type == "deep_loss_rebalance":
                                    st.session_state.tab2_diagnosed = True
                                    st.session_state.tab2_rebalanced = True
                                    st.session_state.tab2_rebal_cache = None
                                    st.session_state.tab2_trigger_diagnose = False
                                    st.session_state.tab2_trigger_rebalance = False
                                    st.toast(f"💼 正在为深套标的【{fcode}】生成反弹抽均线阶梯减亏诊断，已在【💼 持仓调仓】就绪！")
                                    st.rerun()
                                elif act_type == "countdown_hold":
                                    st.session_state.tab2_diagnosed = True
                                    st.session_state.tab2_rebalanced = True
                                    st.session_state.tab2_rebal_cache = None
                                    st.toast(f"⏳ 已为【{fcode}】设置免赎倒计时保护，建议持有满 30 天后再行操作")
                                    st.rerun()
                                elif act_type == "switch_a_class":
                                    st.session_state.tab2_c_replace = fcode
                                    st.session_state.tab2_diagnosed = True
                                    st.session_state.tab2_rebalanced = True
                                    st.session_state.tab2_rebal_cache = None
                                    st.session_state.tab2_trigger_diagnose = False
                                    st.session_state.tab2_trigger_rebalance = False
                                    st.toast(f"🔄 已激活【{fcode}】C类零费率置换指令，已在【💼 持仓调仓】更新！")
                                    st.rerun()
                                else:
                                    st.session_state.tab2_diagnosed = True
                                    st.session_state.tab2_rebalanced = True
                                    st.session_state.tab2_rebal_cache = None
                                    st.session_state.tab2_trigger_diagnose = False
                                    st.session_state.tab2_trigger_rebalance = False
                                    st.toast(f"⚡ 请前往【💼 持仓调仓】Tab 查看针对【{fcode}】的调仓建议")
                                    st.rerun()'''

if old_sentry_block in content:
    content = content.replace(old_sentry_block, new_sentry_block, 1)
    p.write_text(content, encoding="utf-8")
    print("Successfully replaced sentry with aggregation and height=300 container!")
else:
    print("FAILED to find old sentry block!")
