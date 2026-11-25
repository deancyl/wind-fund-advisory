"""
Script: apply_g7_gui_refactor.py
Purpose: 精准实施 G7 架构解耦与交互闭环:
1. 首屏机会雷达白盒进化徽章与 60 日微图
2. 首屏主动风险预警哨双按钮 (去 Tab 2 调仓 vs 去 Tab 4 穿透)
3. Tab 2 双视图模式解耦 (主流程 vs 运维工具坞)
4. Tab 4 顶部联动高亮横幅
"""

from pathlib import Path

GUI_FILE = Path("AGY2_FundAdvisory/app_gui.py")

def main():
    content = GUI_FILE.read_text(encoding="utf-8")
    orig_len = len(content)

    # -------------------------------------------------------------
    # 1. 首屏机会雷达白盒进化徽章与 60 日微图
    # -------------------------------------------------------------
    target_rad_head = """            # --- 左翼：机会雷达 ---
            with col_radar:
                st.markdown("<div style='font-size: 14px; font-weight: 700; color: var(--text-primary); margin-bottom: 8px;'>🔭 全市场机会雷达 · Top 3 机会甄选</div>", unsafe_allow_html=True)
                radar_engine = OpportunityRadarEngine()
                all_scanned_sectors = radar_engine.scan_all_sectors()
                top3_sectors = [s for s in all_scanned_sectors if s.get("s_crowd", 85.0) >= 45.0][:3]"""

    replacement_rad_head = """            # --- 左翼：机会雷达 ---
            with col_radar:
                radar_engine = OpportunityRadarEngine()
                all_scanned_sectors = radar_engine.scan_all_sectors()
                top3_sectors = [s for s in all_scanned_sectors if s.get("s_crowd", 85.0) >= 45.0][:3]
                w_factors = getattr(radar_engine, "factor_weights", [0.30, 0.30, 0.25, 0.15])
                evo_res = getattr(radar_engine, "evolved_result", {})

                col_rad_head1, col_rad_head2 = st.columns([6.0, 4.0])
                with col_rad_head1:
                    safe_markdown_html("<div style='font-size: 14px; font-weight: 700; color: var(--text-primary); margin-bottom: 4px;'>🔭 全市场机会雷达 · Top 3 机会甄选</div>")
                with col_rad_head2:
                    with st.popover(f"🧬 因子进化: 估{w_factors[0]*100:.0f}% 动{w_factors[1]*100:.0f}% 噪{w_factors[2]*100:.0f}% 拥{w_factors[3]*100:.0f}%", use_container_width=True):
                        st.markdown("##### 🧬 在线启发式因子基因自适应进化算子")
                        st.caption("基于 14 大赛道真实 60 日收益与特征张量，纯 NumPy 向量化演化，严格约束换手率与回撤。")
                        traj_data = radar_engine.evolver.get_60d_rolling_nav_and_trajectory()
                        c_m1, c_m2, c_m3 = st.columns(3)
                        c_m1.metric("超额 Alpha", f"{traj_data.get('alpha_pct', 0.0):+.2f}%")
                        c_m2.metric("最大回撤", f"-{traj_data.get('mdd_dynamic_pct', 0.0):.2f}%")
                        c_m3.metric("换手率惩罚", f"-{evo_res.get('turnover', 0.0):.1f}%")
                        df_traj = pd.DataFrame({
                            "日期": traj_data.get("dates", [])[-15:],
                            "动态净值": traj_data.get("nav_dynamic", [])[-15:],
                            "静态基准": traj_data.get("nav_static", [])[-15:],
                        })
                        st.line_chart(df_traj.set_index("日期"))"""

    target_rad_norm = target_rad_head.replace("\r\n", "\n")
    repl_rad_norm = replacement_rad_head.replace("\r\n", "\n")
    content_norm = content.replace("\r\n", "\n")

    if target_rad_norm in content_norm:
        content_norm = content_norm.replace(target_rad_norm, repl_rad_norm, 1)
        print("✅ 成功嵌入机会雷达白盒进化徽章与 60 日微图！")
    else:
        print("⚠️ 未直接匹配 target_rad_head")

    # -------------------------------------------------------------
    # 2. 首屏主动风险预警哨双按钮 (去 Tab 2 调仓 vs 去 Tab 4 穿透)
    # -------------------------------------------------------------
    target_sentry_btns = """                            if st.button(btn_lbl, key=f"btn_sentry_act_{i}_{fcode}_{act_type}", use_container_width=True, type="secondary"):
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
                                    st.toast(f"💼 已定位【{fcode}】深度回撤减亏方案，已在【💼 持仓调仓】就绪！")
                                    st.rerun()
                                else:
                                    st.session_state.tab2_diagnosed = True
                                    st.session_state.tab2_rebalanced = True
                                    st.session_state.tab2_rebal_cache = None
                                    st.session_state.tab2_trigger_diagnose = False
                                    st.session_state.tab2_trigger_rebalance = False
                                    st.toast(f"⚡ 已激活处置意图，请在【💼 持仓调仓】检视执行清单！")
                                    st.rerun()"""

    replacement_sentry_btns = """                            col_s_a, col_s_b = st.columns(2)
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
                                    st.session_state.tab2_diagnosed = True
                                    st.session_state.tab2_rebalanced = True
                                    st.session_state.tab2_rebal_cache = None
                                    st.session_state.tab2_trigger_diagnose = False
                                    st.session_state.tab2_trigger_rebalance = False
                                    st.toast(f"🔒 已生成针对【{fcode or alert.get('title')}】的处置意图，已在【💼 持仓调仓】就绪！")
                                    st.rerun()
                            with col_s_b:
                                if st.button("🔍 穿透到底层", key=f"btn_sentry_evid_{i}_{fcode}_{act_type}", use_container_width=True):
                                    mod_key = "correlation_mutation" if "相关" in alert.get("title", "") else ("stock_overlap" if "重仓" in alert.get("title", "") else "holding_days_fifo")
                                    st.session_state["tab4_highlight_module"] = mod_key
                                    st.session_state["tab4_highlight_fund"] = fcode
                                    st.session_state["tab4_highlight_title"] = alert.get("title", "")
                                    st.toast(f"🔍 已锁定【{alert.get('title')}】，已在【🔍 穿透工具】高亮展现证据！")
                                    st.rerun()"""

    target_sentry_norm = target_sentry_btns.replace("\r\n", "\n")
    repl_sentry_norm = replacement_sentry_btns.replace("\r\n", "\n")

    if target_sentry_norm in content_norm:
        content_norm = content_norm.replace(target_sentry_norm, repl_sentry_norm, 1)
        print("✅ 成功接入首屏主动风险哨联动双按钮 (去 Tab 2 处置 vs 去 Tab 4 穿透)！")
    else:
        print("⚠️ 未直接匹配 target_sentry_btns")

    # -------------------------------------------------------------
    # 3. Tab 4 顶部联动高亮横幅
    # -------------------------------------------------------------
    target_tab4_hl = """    tb_kind, tb_val = option_key_map_tb.get(sel_tb_target, ("ledger", active_lid))"""
    replacement_tab4_hl = """    # ── 响应首屏主动风险哨联动穿透横幅 ──
    hl_mod = st.session_state.get("tab4_highlight_module")
    if hl_mod:
        hl_title = st.session_state.get("tab4_highlight_title", "主动风险预警")
        hl_code = st.session_state.get("tab4_highlight_fund", "")
        safe_markdown_html(f\"\"\"
        <div style="background: rgba(239, 68, 68, 0.08); border-left: 4px solid var(--color-up); padding: 10px 14px; border-radius: 6px; margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: 700; color: var(--color-up); font-size: 13px;">🚨 响应首屏主动风险哨联动证据链：{hl_title}</span>
                <span style="font-size: 11px; color: var(--text-secondary);">标的代码: {hl_code or '全组合'}</span>
            </div>
            <div style="font-size: 11.5px; color: var(--text-primary); margin-top: 4px;">
                系统已为您在下方穿透对应底层持仓与风险证据链。完成排查后，建议返回【💼 持仓调仓】主流程实施调仓处置。
            </div>
        </div>
        \"\"\")

    tb_kind, tb_val = option_key_map_tb.get(sel_tb_target, ("ledger", active_lid))"""

    target_tab4_norm = target_tab4_hl.replace("\r\n", "\n")
    repl_tab4_norm = replacement_tab4_hl.replace("\r\n", "\n")

    if target_tab4_norm in content_norm:
        content_norm = content_norm.replace(target_tab4_norm, repl_tab4_norm, 1)
        print("✅ 成功接入 Tab 4 顶部联动高亮响应横幅！")
    else:
        print("⚠️ 未直接匹配 target_tab4_hl")

    # 写回文件
    GUI_FILE.write_text(content_norm, encoding="utf-8")
    print("✨ apply_g7_gui_refactor.py 基础交互部分注入完毕！")

if __name__ == "__main__":
    main()
