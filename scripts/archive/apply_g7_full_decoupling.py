"""
Script: apply_g7_full_decoupling.py
Purpose: 精准实施 G7:
1. 风险预警哨双按钮改造 (col_s_a: btn_sentry_act_ / col_s_b: btn_sentry_evid_)
2. Tab 2 双视图模式解耦 (is_t2_main_mode vs 工具坞独立模式)
"""

from pathlib import Path

GUI_FILE = Path("AGY2_FundAdvisory/app_gui.py")

def main():
    content = GUI_FILE.read_text(encoding="utf-8")
    content_norm = content.replace("\r\n", "\n")

    # -------------------------------------------------------------
    # 1. 风险哨双按钮改造
    # -------------------------------------------------------------
    old_btn_block = """                            if st.button(btn_lbl, key=f"btn_sentry_act_{i}_{fcode}_{act_type}", use_container_width=True, type="secondary"):
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
                                    st.rerun()"""

    new_btn_block = """                            col_s_a, col_s_b = st.columns(2)
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
                                    st.rerun()"""

    if old_btn_block in content_norm:
        content_norm = content_norm.replace(old_btn_block, new_btn_block, 1)
        print("✅ 成功接入首屏预警哨双按钮 (去 Tab 2 处置 vs 去 Tab 4 穿透)！")
    else:
        print("⚠️ 未直接匹配 old_btn_block")

    # -------------------------------------------------------------
    # 2. Tab 2 顶部添加双视图单选切换器
    # -------------------------------------------------------------
    target_sandbox_banner = """            # 沙盒独立环境黄色醒目提示条
            cur_meta = mlm_inst.get_ledger_meta(active_lid) or {}
            if cur_meta.get("type") == "sandbox":
                safe_markdown_html(\"\"\"
                <div style="background: rgba(234, 179, 8, 0.15); border-left: 4px solid #eab308; padding: 10px 14px; border-radius: 6px; margin-top: 6px; margin-bottom: 12px; font-size: 13px; color: var(--text-primary);">
                    🧪 <b>当前为独立沙盒环境，任何调仓与录基演练均隔离存储，绝不影响主实盘</b>
                </div>
                \"\"\")"""

    repl_sandbox_banner = """            # 沙盒独立环境黄色醒目提示条
            cur_meta = mlm_inst.get_ledger_meta(active_lid) or {}
            if cur_meta.get("type") == "sandbox":
                safe_markdown_html(\"\"\"
                <div style="background: rgba(234, 179, 8, 0.15); border-left: 4px solid #eab308; padding: 10px 14px; border-radius: 6px; margin-top: 6px; margin-bottom: 12px; font-size: 13px; color: var(--text-primary);">
                    🧪 <b>当前为独立沙盒环境，任何调仓与录基演练均隔离存储，绝不影响主实盘</b>
                </div>
                \"\"\")

        # ── G7: Tab 2 双视图解耦模式切换器 (主流程聚焦 vs 独立运维工具坞) ──
        tab2_view_mode = st.radio(
            "视图模式切换",
            ["🎯 持仓诊断与智能调仓 (主流程)", "💼 账本运维与实盘复盘档案 (宽屏工具坞)"],
            index=0 if st.session_state.get("tab2_view_mode", "🎯 持仓诊断与智能调仓 (主流程)").startswith("🎯") else 1,
            horizontal=True,
            key="rad_tab2_view_mode",
            label_visibility="collapsed"
        )
        st.session_state["tab2_view_mode"] = tab2_view_mode
        is_t2_main_mode = tab2_view_mode.startswith("🎯")"""

    if target_sandbox_banner in content_norm:
        content_norm = content_norm.replace(target_sandbox_banner, repl_sandbox_banner, 1)
        print("✅ 成功在 Tab 2 顶部植入双视图单选切换器！")
    else:
        print("⚠️ 未直接匹配 target_sandbox_banner")

    # -------------------------------------------------------------
    # 3. 将工具坞与步骤一/二解耦
    # -------------------------------------------------------------
    target_dock_start = """        # ── 第三层：合并底部散落的 3 个折叠框为单一「🛠️ 账本工具坞」──
        has_holdings = len(pm.holdings) > 0
        with st.expander("🛠️ 账本工具坞（快速录入 / FIFO批次透视 / 实盘接管档案）", expanded=(not has_holdings)):"""

    repl_dock_start = """        # ── G7: 工具坞仅在【💼 账本运维与实盘复盘档案】宽屏展示，主流程保持极致聚焦 ──
        has_holdings = len(pm.holdings) > 0
        if is_t2_main_mode:
            st.info("🛠️ 需快速记账、检视 FIFO 批次或对账？请点击上方切换至【💼 账本运维与实盘复盘档案】宽屏工具坞。")
        else:
            st.markdown("### 💼 账本运维与实盘复盘档案 (独立宽屏工具坞)")
            st.caption("提供快速录入、FIFO批次透视、实盘影子档案、T+1对账、同公司转换及宏观分红研判全套工具。")
        with st.expander("🛠️ 账本工具坞（快速录入 / FIFO批次透视 / 实盘接管档案）", expanded=(not is_t2_main_mode or not has_holdings)):"""

    if target_dock_start in content_norm:
        content_norm = content_norm.replace(target_dock_start, repl_dock_start, 1)
        print("✅ 成功配置工具坞视图分支！")
    else:
        print("⚠️ 未直接匹配 target_dock_start")

    # -------------------------------------------------------------
    # 4. 在模式二下跳过步骤二和步骤三 (只在 is_t2_main_mode 下渲染)
    # -------------------------------------------------------------
    target_step2 = """        # ---------------------------------------------------------
        # 步骤二：【🚦 调仓时机裁决】（AI 综合裁决卡 + 四维胶囊）
        # ---------------------------------------------------------
        if st.session_state.get("tab2_diagnosed", False):"""

    repl_step2 = """        # ---------------------------------------------------------
        # 步骤二：【🚦 调仓时机裁决】（AI 综合裁决卡 + 四维胶囊）
        # ---------------------------------------------------------
        if is_t2_main_mode and st.session_state.get("tab2_diagnosed", False):"""

    if target_step2 in content_norm:
        content_norm = content_norm.replace(target_step2, repl_step2, 1)
        print("✅ 成功为步骤二加入 is_t2_main_mode 保护分支！")
    else:
        print("⚠️ 未直接匹配 target_step2")

    target_step3 = """        # ---------------------------------------------------------
        # 步骤三：【⚖️ 调仓方案与执行清单】
        # ---------------------------------------------------------
        if st.session_state.get("tab2_rebalanced", False):"""

    repl_step3 = """        # ---------------------------------------------------------
        # 步骤三：【⚖️ 调仓方案与执行清单】
        # ---------------------------------------------------------
        if is_t2_main_mode and st.session_state.get("tab2_rebalanced", False):"""

    if target_step3 in content_norm:
        content_norm = content_norm.replace(target_step3, repl_step3, 1)
        print("✅ 成功为步骤三加入 is_t2_main_mode 保护分支！")
    else:
        print("⚠️ 未直接匹配 target_step3")

    GUI_FILE.write_text(content_norm, encoding="utf-8")
    print("✨ Tab 2 双视图解耦与首屏三方联动已全量落地！")

if __name__ == "__main__":
    main()
