"""
Script to apply Tab 2 Module 3 refactoring in AGY2_FundAdvisory/app_gui.py.
Follows Workspace-Only rules and Windows PowerShell scripting standards.
"""
import ast
import re
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
TARGET_FILE = WORKSPACE / "AGY2_FundAdvisory" / "app_gui.py"

def main():
    with open(TARGET_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    start_idx = None
    end_idx = None

    for i, line in enumerate(lines):
        if "# 步骤一底部推进按钮" in line and start_idx is None:
            start_idx = i
        if "# ── ⚡ 智能微观执行滑点优化" in line and start_idx is not None and end_idx is None:
            end_idx = i
            break

    assert start_idx is not None, "Could not find start marker"
    assert end_idx is not None, "Could not find end marker"
    print(f"Found block to replace: lines {start_idx + 1} to {end_idx}")

    new_module_3_code = '''            # ── 模块 3：调仓裁决与执行单合流（单一控制栏 + 4格摘要条 + 执行建议单） ──
            # tab2_rebal_buf_slider_bot
            safe_markdown_html("<div style='height: 10px;'></div>")
            col_t2_btn1, col_t2_btn2, col_t2_slider = st.columns([4.2, 2.6, 3.2])
            with col_t2_btn1:
                if st.button("🔍 诊断并生成调仓方案", type="primary", use_container_width=True, key="btn_tab2_diagnose"):
                    st.session_state["tab2_view_mode"] = "🎯 持仓诊断与智能调仓 (主流程)"
                    # 💡 自动拦截并同步表格未保存修改，杜绝丢数
                    if "edited_table" in locals() and edited_table is not None:
                        _commit_edited_holdings_table(edited_table, pm)
                    st.session_state.tab2_diagnosed = True
                    st.session_state.tab2_rebalanced = True
                    st.session_state.tab2_trigger_diagnose = True
                    st.session_state.tab2_trigger_rebalance = True
                    st.rerun()
            with col_t2_btn2:
                if st.button("🚀 一键全速执行", type="secondary", use_container_width=True, key="btn_tab2_all"):
                    st.session_state["tab2_view_mode"] = "🎯 持仓诊断与智能调仓 (主流程)"
                    if "edited_table" in locals() and edited_table is not None:
                        _commit_edited_holdings_table(edited_table, pm)
                    st.session_state.tab2_diagnosed = True
                    st.session_state.tab2_rebalanced = True
                    st.session_state.tab2_trigger_diagnose = True
                    st.session_state.tab2_trigger_rebalance = True
                    st.rerun()
            with col_t2_slider:
                cur_buf_val = float(st.session_state.get("rebalance_buffer_pct", 3.0))
                def _sync_tab2_rebal_buffer_change():
                    st.session_state.rebalance_buffer_pct = float(st.session_state.tab2_rebal_buf_slider)
                    st.session_state.tab2_diag_cache = None
                    st.session_state.tab2_rebal_cache = None

                st.slider(
                    "🛡️ 免折腾调仓缓冲带 (%)",
                    min_value=1.0,
                    max_value=5.0,
                    value=cur_buf_val,
                    step=0.5,
                    format="%.1f%%",
                    key="tab2_rebal_buf_slider",
                    on_change=_sync_tab2_rebal_buffer_change,
                    help="控制调仓裁决与温和调仓过滤的最小偏离阈值。低于此阈值的微小偏离将自动维持现状，杜绝无效换仓摩擦"
                )

            if is_t2_main_mode and (st.session_state.get("tab2_diagnosed", False) or st.session_state.get("tab2_rebalanced", False)):
                st.markdown("---")

                # 🎯 目标组合与场景模式微调（收纳于轻量折叠项，默认自动全托管）
                has_t1_opt = bool(st.session_state.get("tab1_sim_cache") and st.session_state["tab1_sim_cache"].get("optimal_weights"))
                with st.expander("⚙️ 调仓目标组合与场景模式微调（已自动按全天候策略池与温和再平衡托管）", expanded=False):
                    target_pool_options = [
                        "🌱 对齐我在【新资建仓】生成的最新优选组合",
                        "🛡️ 核心指数全天候策略池（按当前档位自动配比）"
                    ]
                    chosen_target_pool = st.radio(
                        "🎯 选择调仓目标组合：",
                        target_pool_options,
                        index=0 if has_t1_opt else 1,
                        horizontal=True,
                        key="rad_tab2_target_pool"
                    )

                    col_sc1, col_sc2 = st.columns([6.5, 3.5])
                    with col_sc1:
                        sel_scenario_name = st.radio(
                            "调仓意图场景：",
                            [
                                "⚖️ 存量标准再平衡 (平衡各大类资产偏离度)",
                                "💵 新资注入免赎补仓 (发工资/定投补仓·零卖出零赎回费)",
                                "🏧 智能低损耗提现 (急需用钱·零买入·阶梯免赎赎回·避开7天惩罚)",
                                "🧹 尾部碎片与C类一键归拢 (清理<3%碎片与满期高费率C类至底仓)"
                            ],
                            index=0,
                            key="rad_tab2_scenario_mode"
                        )
                    with col_sc2:
                        freeze_reserved_chk = st.checkbox(
                            f"🛡️ 冻结分批建仓预留现金 (¥{pm.reserved_batch_cash:,.2f})",
                            value=True,
                            help="开启后，建仓阶段预留用于二期/三期或定投的现金将被严格保护隔离，绝不作为存量现金在调仓中乱花！",
                            key="chk_freeze_reserved_cash"
                        )

                    scenario_key = "standard"
                    new_cash_val = 0.0
                    withdraw_cash_val = 0.0
                    anchor_target_code = "005561"

                    if "新资注入" in sel_scenario_name:
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
                            st.caption("💡 严禁触碰未满 7 天惩罚期标的，优先赎回已满期 C 类或免赎标的，零买入！")
                    elif "碎片" in sel_scenario_name:
                        scenario_key = "sweep_tail_and_c_class"
                        c_sc_in1, c_sc_in2 = st.columns([6, 4])
                        with c_sc_in1:
                            anchor_opts = ["005561 - 创金合信红利低波A", "002351 - 易方达裕祥回报债券A", "000216 - 华安黄金ETF联接A"]
                            sel_anchor = st.selectbox("🎯 回收资金全额归拢买入的压舱石底仓：", anchor_opts, key="sel_sc_anchor")
                            anchor_target_code = sel_anchor.split(" - ")[0]
                        with c_sc_in2:
                            st.caption("💡 一键清理占比 <3% 尾部碎片与满 30 天高费率 C 类，回收资金全额增持底仓！")

                    mode_choice = st.radio(
                        "推演调仓模式：",
                        [f"模式一：温和免伤调仓 (遵循 {cur_buf_val:.1f}% 缓冲与锁定期保护·零惩罚费·首选推荐)", "模式二：强行一步到位调仓 (无视持有期强行全额换仓·核算全额摩擦成本)"],
                        index=0,
                        horizontal=True,
                        key="rad_rebal_mode"
                    )

                if "chosen_target_pool" in locals() and chosen_target_pool.startswith("🌱") and has_t1_opt:
                    tier_target_w = dict(st.session_state["tab1_sim_cache"]["optimal_weights"])
                else:
                    snapshot = StrategyBridge.get_latest_market_snapshot()
                    base_w = StrategyBridge.compute_dynamic_tier_weights(tier=active_tier, market_snapshot=snapshot)
                    overrides = st.session_state.get("custom_fund_overrides", {})
                    tier_target_w = {}
                    for c, w in base_w.items():
                        target_c = overrides.get(c, c)
                        tier_target_w[target_c] = tier_target_w.get(target_c, 0.0) + w

                _cur_buf = float(st.session_state.get("rebalance_buffer_pct", 3.0))

                # 诊断裁决精算
                if st.session_state.get("tab2_trigger_diagnose", False) or st.session_state.get("tab2_diag_cache") is None:
                    suitability = StrategyBridge.evaluate_today_rebalance_suitability(pm, active_tier=active_tier, min_buffer_pct=(_cur_buf / 100.0))
                    st.session_state.tab2_diag_cache = suitability
                    st.session_state.tab2_trigger_diagnose = False
                suitability = st.session_state.get("tab2_diag_cache") or {}

                # 调仓后果模拟精算
                if "scenario_key" not in locals():
                    scenario_key = "standard"
                    new_cash_val = 0.0
                    withdraw_cash_val = 0.0
                    anchor_target_code = "005561"
                    freeze_reserved_chk = True
                    mode_choice = "温和免伤调仓"

                cur_pool_sig = (
                    chosen_target_pool if "chosen_target_pool" in locals() else "default",
                    tuple(sorted(tier_target_w.items())),
                    scenario_key,
                    float(new_cash_val),
                    float(withdraw_cash_val),
                    bool(freeze_reserved_chk),
                    str(anchor_target_code),
                    float(_cur_buf),
                    tuple(sorted(st.session_state.get("tab2_locked_funds") or [])),
                    str(st.session_state.get("tab2_pending_take_profit")),
                    str(st.session_state.get("tab2_c_replace"))
                )
                if st.session_state.get("tab2_last_pool_sig") != cur_pool_sig:
                    st.session_state.tab2_rebal_cache = None
                    st.session_state.tab2_last_pool_sig = cur_pool_sig

                if st.session_state.get("tab2_trigger_rebalance", False) or st.session_state.get("tab2_rebal_cache") is None:
                    sim_res = StrategyBridge.simulate_rebalance_modes_and_consequences(
                        pm,
                        active_tier=active_tier,
                        target_weights=tier_target_w,
                        min_buffer_pct=(_cur_buf / 100.0),
                        locked_funds=st.session_state.get("tab2_locked_funds"),
                        pending_take_profit=st.session_state.get("tab2_pending_take_profit"),
                        c_replace=st.session_state.get("tab2_c_replace"),
                        scenario_mode=scenario_key,
                        new_cash_amount=new_cash_val,
                        withdraw_cash_amount=withdraw_cash_val,
                        freeze_reserved_cash=freeze_reserved_chk,
                        core_anchor_code=anchor_target_code
                    )
                    st.session_state.tab2_rebal_cache = sim_res
                    st.session_state.tab2_trigger_rebalance = False
                sim_res = st.session_state.get("tab2_rebal_cache") or {}

                # 提取 4 格精炼调仓摘要指标
                v_level = suitability.get("verdict_level", "HOLD_ON")
                v_title = suitability.get("verdict_title", "今日维持底仓吃息，无需调仓")
                d_max = suitability.get("d_max", 0.0) * 100.0
                m20_desc = snapshot.get("m20_status_desc", "站上均线")
                v_color = "var(--color-down)" if v_level == "SUITABLE" else ("var(--accent-primary)" if v_level == "HOLD_ON" else "var(--color-up)")

                sel_mode_key = "mode_gentle" if "温和" in mode_choice else "mode_forced"
                cur_sim = sim_res.get(sel_mode_key, sim_res.get("mode_gentle", {}))
                conseq = cur_sim.get("consequences", {})
                fee_loss = conseq.get("fee_loss", {"total_fee": 0.0, "redemption_fee": 0.0, "subscription_fee": 0.0, "penalty_fee_7d": 0.0, "payback_days": 0})
                in_transit = conseq.get("in_transit_risk", {"in_transit_amount": 0.0, "in_transit_pct": 0.0, "lock_days": "0天", "switch_saved_amount": 0.0, "missed_rally_cost_est": 0.0})
                risk_shift = conseq.get("risk_shift", {"vol_before": 0.0, "vol_after": 0.0, "mdd_before": 0.0, "mdd_after": 0.0, "div_yield_before": 0.0, "div_yield_after": 0.0, "equity_after": 0.0})

                pen_badge = f"<span style='color: var(--color-up); font-weight: 600;'>含7天惩罚: ¥{fee_loss.get('penalty_fee_7d', 0):,.2f}</span>" if fee_loss.get('penalty_fee_7d', 0) > 0 else "<span style='color: var(--color-down);'>免收 1.5% 惩罚费</span>"

                # 渲染单行 4 格精炼调仓摘要条
                col_sum1, col_sum2, col_sum3, col_sum4 = st.columns(4)
                with col_sum1:
                    safe_markdown_html(f"""
                    <div class="decision-card" style="padding: 12px 14px; min-height: 100px;">
                        <div class="decision-title" style="font-size: 12px; color: var(--text-secondary); margin-bottom: 2px;">🎯 ① 时机裁决结论</div>
                        <div style="font-size: 15px; font-weight: 700; color: {v_color}; margin: 2px 0;">{v_title}</div>
                        <div style="font-size: 11.5px; color: var(--text-secondary); line-height: 1.4;">
                            偏离度: <b>{d_max:.1f}%</b> (阈值 {_cur_buf:.1f}%)<br>
                            均线突破: <b>{m20_desc}</b> ｜ 申赎窗口: <b>{clock_status.window_type}</b>
                        </div>
                    </div>
                    """)
                with col_sum2:
                    safe_markdown_html(f"""
                    <div class="decision-card" style="padding: 12px 14px; min-height: 100px;">
                        <div class="decision-title" style="font-size: 12px; color: var(--text-secondary); margin-bottom: 2px;">💸 ② 手续费直接损耗</div>
                        <div style="font-size: 15px; font-weight: 700; color: var(--color-up); margin: 2px 0;">¥{fee_loss.get('total_fee', 0.0):,.2f}</div>
                        <div style="font-size: 11.5px; color: var(--text-secondary); line-height: 1.4;">
                            赎回 ¥{fee_loss.get('redemption_fee', 0.0):,.2f} ｜ 申购 ¥{fee_loss.get('subscription_fee', 0.0):,.2f}<br>
                            {pen_badge} ｜ 回本约 <b>{fee_loss.get('payback_days', 0)} 天</b>
                        </div>
                    </div>
                    """)
                with col_sum3:
                    safe_markdown_html(f"""
                    <div class="decision-card" style="padding: 12px 14px; min-height: 100px;">
                        <div class="decision-title" style="font-size: 12px; color: var(--text-secondary); margin-bottom: 2px;">⏳ ③ T+2在途踏空风险</div>
                        <div style="font-size: 15px; font-weight: 700; color: var(--accent-primary); margin: 2px 0;">¥{in_transit.get('in_transit_amount', 0.0):,.2f} ({in_transit.get('in_transit_pct', 0.0):.1f}%)</div>
                        <div style="font-size: 11.5px; color: var(--text-secondary); line-height: 1.4;">
                            资金在途: <b>{in_transit.get('lock_days', '0天')}</b><br>
                            同公司免在途节省: <b>¥{in_transit.get('switch_saved_amount', 0.0):,.2f}</b>
                        </div>
                    </div>
                    """)
                with col_sum4:
                    safe_markdown_html(f"""
                    <div class="decision-card" style="padding: 12px 14px; min-height: 100px;">
                        <div class="decision-title" style="font-size: 12px; color: var(--text-secondary); margin-bottom: 2px;">🛡️ ④ 攻防与回撤变化</div>
                        <div style="font-size: 15px; font-weight: 700; color: var(--text-primary); margin: 2px 0;">波动率 {risk_shift.get('vol_before', 0.0):.1f}% ➔ {risk_shift.get('vol_after', 0.0):.1f}%</div>
                        <div style="font-size: 11.5px; color: var(--text-secondary); line-height: 1.4;">
                            极端回撤: <b>{risk_shift.get('mdd_before', 0.0):.1f}% ➔ {risk_shift.get('mdd_after', 0.0):.1f}%</b><br>
                            股息安全垫: <b>{risk_shift.get('div_yield_before', 0.0):.2f}% ➔ {risk_shift.get('div_yield_after', 0.0):.2f}%</b>
                        </div>
                    </div>
                    """)

                # 生成执行建议单
                rebal_mode_param = "forced" if sel_mode_key == "mode_forced" else "gentle"
                effective_avail_cash = max(0.0, pm.available_cash - getattr(pm, "reserved_batch_cash", 0.0)) if freeze_reserved_chk else pm.available_cash
                ai_orders_res = StrategyBridge.generate_ai_rebalance_orders(
                    current_holdings=pm.holdings,
                    available_cash=effective_avail_cash,
                    target_weights_funds=tier_target_w,
                    pm=pm,
                    mode=rebal_mode_param,
                    min_buffer_pct=_cur_buf,
                    locked_funds=st.session_state.get("tab2_locked_funds"),
                    pending_take_profit=st.session_state.get("tab2_pending_take_profit"),
                    c_replace=st.session_state.get("tab2_c_replace"),
                    scenario_mode=scenario_key,
                    new_cash_amount=new_cash_val,
                    withdraw_cash_amount=withdraw_cash_val,
                    freeze_reserved_cash=freeze_reserved_chk,
                    core_anchor_code=anchor_target_code
                )
                items = ai_orders_res.get("items", [])

                if items:
                    sell_items = [it for it in items if it.get("diff_amount", 0.0) < -100]
                    buy_items = [it for it in items if it.get("diff_amount", 0.0) > 100]
'''
    if not new_module_3_code.endswith("\n"):
        new_module_3_code += "\n"

    new_lines = lines[:start_idx] + [new_module_3_code] + lines[end_idx:]
    new_content = "".join(new_lines)

    # Validate AST
    tree = ast.parse(new_content, filename=str(TARGET_FILE))
    print("AST verification passed!")

    # Check tab2_rebal_buf_slider count
    slider_keys = re.findall(r'key=["\']tab2_rebal_buf_slider["\']', new_content)
    assert len(slider_keys) == 1, f"tab2_rebal_buf_slider expected 1, got {len(slider_keys)}"
    assert "# tab2_rebal_buf_slider_bot" in new_content, "Missing # tab2_rebal_buf_slider_bot"
    print("Slider uniqueness check passed!")

    with open(TARGET_FILE, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Successfully wrote refactored code to app_gui.py")

if __name__ == "__main__":
    main()
