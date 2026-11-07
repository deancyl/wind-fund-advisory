import re
from pathlib import Path

gui_path = Path("AGY2_FundAdvisory/app_gui.py")
content = gui_path.read_text(encoding="utf-8")

# 1. Update quick add bar (bar_amt_input) with Chinese amount caption and commit hook
old_quick_add = '''            with col_bar_amt:
                bar_amt_in = st.number_input("持有金额 (元)", value=10000.0, step=1000.0, min_value=100.0, key="bar_amt_input")
            with col_bar_pnl:'''

new_quick_add = '''            with col_bar_amt:
                bar_amt_in = st.number_input("持有金额 (元)", value=10000.0, step=1000.0, min_value=100.0, key="bar_amt_input")
                st.caption(f"🔢 **金额核对**：{format_chinese_amount(bar_amt_in)}")
            with col_bar_pnl:'''

assert old_quick_add in content, "old_quick_add not found"
content = content.replace(old_quick_add, new_quick_add)

old_add_holding_btn = '''                if st.button("➕ 加入账本", type="primary", use_container_width=True, key="btn_bar_add_holding"):
                    raw_in = bar_fund_in.strip()'''

new_add_holding_btn = '''                if st.button("➕ 加入账本", type="primary", use_container_width=True, key="btn_bar_add_holding"):
                    if "tab2_cached_edited_table" in st.session_state and st.session_state.tab2_cached_edited_table is not None:
                        _ch, _ = _has_uncommitted_holdings_changes(st.session_state.tab2_cached_edited_table, pm)
                        if _ch:
                            _commit_edited_holdings_table(st.session_state.tab2_cached_edited_table, pm)
                    raw_in = bar_fund_in.strip()'''

assert old_add_holding_btn in content, "old_add_holding_btn not found"
content = content.replace(old_add_holding_btn, new_add_holding_btn)

# 2. Add warn_placeholder and uncommitted check around st.data_editor
old_data_editor_pre = '''            safe_markdown_html("<div style='height: 4px;'></div>")
            st.caption("实时持仓资产明细（💡 仅需修改/录入 **「基金代码」** 与 **「当前市值(元)」** 或 **「持仓份额」**，保存时后台自动联网补齐真实名称、最新净值与盘中估值，其余指标全自动跳出）：")

            edited_table = st.data_editor('''

new_data_editor_pre = '''            safe_markdown_html("<div style='height: 4px;'></div>")
            st.caption("实时持仓资产明细（💡 仅需修改/录入 **「基金代码」** 与 **「当前市值(元)」** 或 **「持仓份额」**，保存时后台自动联网补齐真实名称、最新净值与盘中估值，其余指标全自动跳出）：")
            warn_placeholder = st.empty()

            edited_table = st.data_editor('''

assert old_data_editor_pre in content, "old_data_editor_pre not found"
content = content.replace(old_data_editor_pre, new_data_editor_pre)

old_data_editor_post = '''                num_rows="dynamic",
                key="main_holdings_editor_tab2"
            )

            # 拉齐操作栏：等高 5 列工具栏（含现金池修改 Popover）'''

new_data_editor_post = '''                num_rows="dynamic",
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

assert old_data_editor_post in content, "old_data_editor_post not found"
content = content.replace(old_data_editor_post, new_data_editor_post)

# 3. Update col_op2 (cash pool edit), col_op3 (sync NAV), col_op5 (delete holding)
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
content = content.replace(old_col_op2, new_col_op2)

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
content = content.replace(old_col_op3, new_col_op3)

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
content = content.replace(old_col_op5, new_col_op5)

# 4. Chinese amount captions in Step 3 for new cash and withdraw cash
old_sc_new_cash = '''                with c_sc_in1:
                    new_cash_val = st.number_input("💵 本次计划新增注入的补仓资金 (元)", value=20000.0, step=1000.0, min_value=100.0, key="num_sc_new_cash")
                with c_sc_in2:'''

new_sc_new_cash = '''                with c_sc_in1:
                    new_cash_val = st.number_input("💵 本次计划新增注入的补仓资金 (元)", value=20000.0, step=1000.0, min_value=100.0, key="num_sc_new_cash")
                    st.caption(f"🔢 **金额核对**：{format_chinese_amount(new_cash_val)}")
                with c_sc_in2:'''

assert old_sc_new_cash in content, "old_sc_new_cash not found"
content = content.replace(old_sc_new_cash, new_sc_new_cash)

old_sc_withdraw_cash = '''                with c_sc_in1:
                    withdraw_cash_val = st.number_input("🏧 本次急需提取现金金额 (元)", value=30000.0, step=1000.0, min_value=100.0, key="num_sc_withdraw_cash")
                with c_sc_in2:'''

new_sc_withdraw_cash = '''                with c_sc_in1:
                    withdraw_cash_val = st.number_input("🏧 本次急需提取现金金额 (元)", value=30000.0, step=1000.0, min_value=100.0, key="num_sc_withdraw_cash")
                    st.caption(f"🔢 **金额核对**：{format_chinese_amount(withdraw_cash_val)}")
                with c_sc_in2:'''

assert old_sc_withdraw_cash in content, "old_sc_withdraw_cash not found"
content = content.replace(old_sc_withdraw_cash, new_sc_withdraw_cash)

gui_path.write_text(content, encoding="utf-8")
print("Successfully applied part 1 edits to app_gui.py")
