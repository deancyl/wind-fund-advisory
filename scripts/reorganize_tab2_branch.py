import re
from pathlib import Path

gui_path = Path("AGY2_FundAdvisory/app_gui.py")
content = gui_path.read_text(encoding="utf-8")

# Let's inspect where dock tabs start and end
dock_start_marker = "# ── G7: 工具坞仅在【💼 账本运维与实盘复盘档案】宽屏展示，主流程保持极致聚焦 ──"
step1_bot_marker = "# 步骤一底部推进按钮与缓冲带微调 (方便诊断调仓时机前直接调节)"
step2_marker = "# ---------------------------------------------------------\n        # 步骤二：【🚦 调仓时机裁决】（AI 综合裁决卡 + 四维胶囊）"
tab2_end_marker = "    except Exception as e:\n        st.error(f\"⚠️ 【💼 持仓调仓】渲染出现局部异常: {e}\")"

assert dock_start_marker in content, "dock_start_marker not found"
assert step1_bot_marker in content, "step1_bot_marker not found"
assert step2_marker in content, "step2_marker not found"
assert tab2_end_marker in content, "tab2_end_marker not found"

# 1. Extract the dock tabs block
# The dock block starts at dock_start_marker and ends right before step1_bot_marker
p_dock_start = content.index(dock_start_marker)
p_step1_bot = content.index(step1_bot_marker)
dock_block = content[p_dock_start:p_step1_bot]

# Now let's extract dock_tabs content from dock_block
# Inside dock_block:
# with st.expander("🛠️ 账本工具坞（快速录入 / FIFO批次透视 / 实盘接管档案）", expanded=(not is_t2_main_mode or not has_holdings)):
#     dock_tab1, ...
# We want to unindent the expander contents by 4 spaces and remove the expander header!
expander_marker = 'with st.expander("🛠️ 账本工具坞（快速录入 / FIFO批次透视 / 实盘接管档案）", expanded=(not is_t2_main_mode or not has_holdings)):'
assert expander_marker in dock_block, "expander_marker not found in dock_block"

# Split at expander_marker
p_exp = dock_block.index(expander_marker)
inside_expander = dock_block[p_exp + len(expander_marker):]

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

assert old_dock3_buttons in inside_expander, "old_dock3_buttons not found in inside_expander"
inside_expander = inside_expander.replace(old_dock3_buttons, "")

# Unindent inside_expander by 4 spaces
unindented_dock_lines = []
for line in inside_expander.split("\n"):
    if line.startswith("            "):
        unindented_dock_lines.append("        " + line[12:])
    elif line.startswith("        "):
        unindented_dock_lines.append(line)
    elif line.strip() == "":
        unindented_dock_lines.append("")
    else:
        unindented_dock_lines.append(line)

new_dock_block = '''        else:
            # ── 模式二：💼 账本运维与实盘复盘档案 (独立宽屏工具坞，全宽平铺) ──
            st.markdown("### 💼 账本运维与实盘复盘档案 (独立宽屏工具坞)")
            st.caption("提供快速录入、FIFO批次透视、实盘影子档案、T+1对账、同公司转换及宏观分红研判全套工具。")
''' + "\n".join(unindented_dock_lines)

# 2. In main mode:
# Remove top slider from col_t2_env1, col_t2_env2, col_t2_env3, col_t2_buf
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
content = content.replace(old_env_cols, new_env_cols)

# 3. Update Step 1 bottom buttons: remove slider, add auto-heal
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

new_step1_bot = '''        # 步骤一底部推进按钮 (已移除冗余滑块，保留兼容注释)
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
                st.rerun()'''

assert old_step1_bot in content, "old_step1_bot not found"
content = content.replace(old_step1_bot, new_step1_bot)

# 4. Now, let's remove the old dock block between holdings table and step 1 bot buttons,
# and replace it with just the st.info line!
old_dock_area = content[content.index(dock_start_marker):content.index("# 步骤一底部推进按钮 (已移除冗余滑块，保留兼容注释)")]
replacement_info = '''        # ── 模式一提示：导向工具坞 ──
        st.info("🛠️ 需快速记账、检视 FIFO 批次或对账？请点击上方切换至【💼 账本运维与实盘复盘档案】宽屏工具坞。")

'''
content = content.replace(old_dock_area, replacement_info)

# 5. Wrap Step 1 in if is_t2_main_mode:, and place new_dock_block at the end of Tab 2!
# Let's see where is_t2_main_mode starts:
# Look for:
# is_t2_main_mode = tab2_view_mode.startswith("🎯")
# # 🛡️ 浮盈安全垫抗震承压与本金破净临界看板 (重构升级原静态纯文字横幅)
target_start = '''        is_t2_main_mode = tab2_view_mode.startswith("🎯")

        # 🛡️ 浮盈安全垫抗震承压与本金破净临界看板 (重构升级原静态纯文字横幅)'''

# We change this to:
# is_t2_main_mode = tab2_view_mode.startswith("🎯")
# if is_t2_main_mode:
#     # 🛡️ 浮盈安全垫抗震承压与本金破净临界看板 (重构升级原静态纯文字横幅)
# AND then at the end of Tab 2 (right before except Exception as e:):
# we append new_dock_block!
# Wait! If we put `if is_t2_main_mode:` and indent the lines, or can we do:
# if not is_t2_main_mode:
#     [render dock tabs]
# else:
#     [render Step 1, Step 2, Step 3]
# Or:
# if is_t2_main_mode:
#     [render Step 1, Step 2, Step 3]
# else:
#     [render dock tabs]
'''
Let's see: if is_t2_main_mode:
Lines from `# 🛡️ 浮盈安全垫` down to before `except Exception as e:` get indented by 4 spaces.
Let's verify!
'''
p_t2_start = content.index("        # 🛡️ 浮盈安全垫抗震承压与本金破净临界看板 (重构升级原静态纯文字横幅)")
p_t2_end = content.index("    except Exception as e:\n        st.error(f\"⚠️ 【💼 持仓调仓】渲染出现局部异常: {e}\")")

step123_content = content[p_t2_start:p_t2_end]

indented_step123_lines = []
for line in step123_content.split("\n"):
    if line.strip():
        indented_step123_lines.append("    " + line)
    else:
        indented_step123_lines.append("")

indented_step123 = "\n".join(indented_step123_lines)

full_tab2_replacement = f'''        if is_t2_main_mode:
{indented_step123}
{new_dock_block}
'''

content = content[:p_t2_start] + full_tab2_replacement + content[p_t2_end:]

gui_path.write_text(content, encoding="utf-8")
print("Successfully restructured Tab 2 dual view physical branch isolation!")
