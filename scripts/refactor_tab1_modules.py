import re
import ast
from pathlib import Path

gui_file = Path("AGY2_FundAdvisory/app_gui.py")
content = gui_file.read_text(encoding="utf-8")

# Start anchor
start_marker = "        # 严格分步隔离：若未进入步骤二，绝对不渲染步骤二与步骤三\n        # ---------------------------------------------------------\n        if st.session_state.get(\"tab1_step_reached\", 1) >= 2:"
if start_marker not in content:
    start_marker = start_marker.replace("\n", "\r\n")

assert start_marker in content, "Could not find start marker in app_gui.py"

# End anchor
end_marker = "                    st.success(\"✅ 已将此组合送入组合回测，请切换至 Tab 3 检视。\")"
assert end_marker in content, "Could not find end marker in app_gui.py"

# Locate start and end indices
start_idx = content.find(start_marker)
end_idx = content.find(end_marker, start_idx) + len(end_marker)

print(f"Start index: {start_idx}, End index: {end_idx}")

new_tab1_body = '''        # ---------------------------------------------------------
        # 模块 2 与模块 3：执行单、核心指标卡与单一白盒抽屉
        # ---------------------------------------------------------
        if st.session_state.get("tab1_step_reached", 1) >= 2:
            st.markdown("---")
            m_title = QUANT_MODELS_CATALOG.get(sel_model_type, {}).get("name", "鲁棒双核HRP")

            if st.session_state.get("tab1_trigger_sim", False) or st.session_state.get("tab1_sim_cache") is None:
                acc = ActiveComputationConsole(f"AI 投顾真全市场 2.8 万只漏斗推演 ({num_funds_input}只)", total_steps=4, step_labels=[
                    f"步骤 1: 全市场 28,177 只漏斗初筛与赛道初选",
                    f"步骤 2: 宏观同温层定调与【{m_title}】求解 {num_funds_input} 只基金配比",
                    f"步骤 3: 2018-2026 跨牛熊日度净值合成与多周期胜率",
                    f"步骤 4: 最好/最坏情况、95% CVaR 与水下回本精算"
                ])
                def _sim_cb(cur, tot, msg):
                    acc.update_step(cur, msg, progress_pct=int((cur / max(tot, 1)) * 95))

                res_portfolio = StrategyBridge.compute_n_funds_model_portfolio(
                    tier=active_tier,
                    target_return_pct=float(cur_tab1_params["target_ret"]),
                    num_funds=int(num_funds_input),
                    model_type=sel_model_type,
                    horizon_label=horizon_choice,
                    capital=float(plan_capital),
                    custom_overrides=st.session_state.get("custom_fund_overrides", {}),
                    purchase_limit_filter=st.session_state.get("purchase_limit_filter", "不限 (自动拆单承接)"),
                    radar_selected_funds=st.session_state.get("radar_selected_funds", []),
                    progress_cb=_sim_cb
                )
                acc.complete("真全市场选基与推演完成")
                st.session_state.tab1_sim_cache = res_portfolio
                st.session_state.tab1_trigger_sim = False

            _cache_entry = st.session_state.get("tab1_sim_cache") or {}
            readable_kpi = _cache_entry.get("readable_kpi", {})
            bt_df = _cache_entry.get("bt_df", pd.DataFrame())
            wr_table = _cache_entry.get("wr_table", {})
            quant_table = _cache_entry.get("quant_table", pd.DataFrame())
            funnel_stats = _cache_entry.get("funnel_stats", {})
            opt_weights = _cache_entry.get("optimal_weights", {})
            alts_map = _cache_entry.get("alternatives_by_slot", {})

            # 自动生成实盘建仓 Blueprint
            if st.session_state.get("tab1_trigger_s3", False) or st.session_state.get("tab1_step3_cache") is None:
                cur_opt_w = opt_weights
                overrides = st.session_state.get("custom_fund_overrides", {})

                blueprint = StrategyBridge.generate_zero_start_blueprint(
                    total_capital=float(plan_capital),
                    target_weights_funds=cur_opt_w,
                    tier=active_tier,
                    custom_fund_overrides=overrides,
                    purchase_limit_filter=st.session_state.get("purchase_limit_filter", "不限 (自动拆单承接)")
                )

                items = blueprint["items"]
                n_funds = len(items)
                acc_s3 = ActiveComputationConsole(
                    f"生成【{active_tier} 档位】实盘建仓单与限购拆单 ({n_funds}只)",
                    total_steps=n_funds + 1,
                    step_labels=["步骤 1: 生成建仓交割单与限额拆单规则"] + [
                        f"步骤 {i+2}: 拉取 {it['fund_code']} 实时估值与排雷" for i, it in enumerate(items)
                    ]
                )
                acc_s3.update_step(0, "正在生成基础建仓单与智能限额拆单规则...", progress_pct=10)

                pcr_eval = calculate_portfolio_risk_contributions(cur_opt_w)
                pcr_map = pcr_eval.get("pcr", {})

                bp_rows = []
                cheat_sheet_lines = [
                    f"【AGY2 智能投顾专属建仓小抄】",
                    f"配置档位：{active_tier} {cur_tier_meta['name']} ｜ 模型：{QUANT_MODELS_CATALOG.get(sel_model_type, {}).get('name', 'HRP')} ｜ 目标总投入：¥{plan_capital:,.2f}",
                    f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    f"----------------------------------------"
                ]

                for idx, it in enumerate(items, 1):
                    fcode = it["fund_code"]
                    acc_s3.update_step(idx, f"正在拉取 [{idx}/{n_funds}] 基金 ({fcode}) 实时估值与排雷...", progress_pct=int(10 + (idx / n_funds) * 85))
                    q_it = fetch_realtime_fund_quote(fcode)
                    scr_it = pm.screen_fund_look_through_risk(fcode)
                    crd_it = pm.get_fund_smart_money_crowding(fcode)

                    risk_badge_disp = scr_it.get("risk_badge", "🟢 健康")
                    crowd_deg_disp = crd_it.get("crowding_degree", "相对分散")
                    if crd_it.get("crowding_warning"):
                        crowd_deg_disp += " ⚠️"

                    risk_and_crowd = f"{risk_badge_disp} ｜ {crowd_deg_disp}"
                    div_short = "现金分红" if it.get("require_cash_dividend") else "红利再投"

                    raw_guide = it.get("action_guide") or ("已拆单" if it.get("has_split") else "正常买入")
                    if it.get("require_cash_dividend"):
                        guide_action = f"现金分红·{raw_guide}" if (raw_guide and raw_guide != "正常买入") else "现金分红·满期免赎A"
                    elif raw_guide and raw_guide != "正常买入":
                        guide_action = raw_guide
                    elif it.get("share_class") == "C":
                        guide_action = "红利再投·弹性进攻C"
                    else:
                        guide_action = "长钱持有·满期免赎A"

                    # 附加交割清算与基金属性标签
                    if pm.is_qdii_fund(fcode, it.get("fund_name", "")):
                        guide_action += "·跨时区T+2确认"
                    elif any(k in pm.classify_fund_asset_class(fcode, it.get("fund_name", "")) for k in ["纯债", "固收", "债券"]):
                        guide_action += "·票息久期底仓"

                    f_pcr = pcr_map.get(fcode, round(it.get("target_weight_pct", 0.0), 1))
                    bp_rows.append({
                        "基金代码": fcode,
                        "基金名称": it["fund_name"],
                        "份额": f"{it.get('share_class', 'A')}类",
                        "目标占比(%)": it.get("target_weight_pct", 0.0),
                        "风险贡献(PCR %)": f"{f_pcr:.1f}%",
                        "精确买入金额(元)": it.get("allocated_amount", it.get("amount", 0.0)),
                        "最新净值": q_it.dwjz if q_it else 1.0,
                        "实时估值涨跌(%)": q_it.gszzl if q_it else 0.0,
                        "排雷与拥挤度": risk_and_crowd,
                        "实操分红与限购指引": guide_action
                    })

                    cheat_sheet_lines.append(
                        f"{idx}. 基金代码: {fcode} ({it['fund_name']}) | 买入金额: ¥{it['allocated_amount']:,.2f} ({it['target_weight_pct']:.1f}%) | 份额: {it.get('share_class', 'A')}类 | 分红方式: {div_short} | 指引: {guide_action}"
                    )

                cheat_sheet_lines.append("----------------------------------------")
                cheat_sheet_lines.append("💡 下单提醒：场外基金请在交易日 15:00 前完成支付，15:00 后下单将按次日未知净值成交。")
                cheat_sheet_text = "\\n".join(cheat_sheet_lines)

                cols_9 = [
                    "基金代码", "基金名称", "份额", "目标占比(%)", "风险贡献(PCR %)",
                    "精确买入金额(元)", "最新净值", "实时估值涨跌(%)",
                    "排雷与拥挤度", "实操分红与限购指引"
                ]
                df_bp = pd.DataFrame(bp_rows)[cols_9]
                acc_s3.complete("实盘建仓单与限购拆单小抄已就绪")

                st.session_state.tab1_step3_cache = {
                    "blueprint": blueprint,
                    "df_bp": df_bp,
                    "cheat_sheet_text": cheat_sheet_text,
                    "cur_opt_w": cur_opt_w,
                    "overrides": overrides
                }
                st.session_state.tab1_trigger_s3 = False

            _cache_s3 = st.session_state.tab1_step3_cache
            blueprint = _cache_s3["blueprint"]
            df_bp = _cache_s3["df_bp"]
            cheat_sheet_text = _cache_s3["cheat_sheet_text"]
            cur_opt_w = _cache_s3.get("cur_opt_w", opt_weights)
            overrides = _cache_s3.get("overrides") or {}

            # ── 模块 2：3 项核心指标条置顶与实盘建仓执行表 ──
            erp_pct = float(snapshot.get("erp_percentile", 78.5))
            _cushion_info = StrategyBridge.calculate_portfolio_yield_cushion(opt_weights, total_capital=float(plan_capital), pm=pm)
            _ann_cush = _cushion_info.get("annual_cushion_amount", 0.0)
            _mo_cush = _cushion_info.get("monthly_equivalent_amount", 0.0)
            _w_yield = _cushion_info.get("weighted_yield_pct", 0.0)

            _def_w = 0.0
            _off_w = 0.0
            _top_f_code = ""
            _top_f_w = 0.0
            for _fc, _fw in sorted(opt_weights.items(), key=lambda x: x[1], reverse=True):
                if not _top_f_code:
                    _top_f_code = _fc
                    _top_f_w = _fw
                _ac = pm.classify_fund_asset_class(_fc)
                if any(k in _ac for k in ["债", "固收", "货币", "黄金"]):
                    _def_w += _fw
                else:
                    _off_w += _fw
            _top_f_meta = CORE_STRATEGY_POOL.get(_top_f_code, {}) or EXTENDED_FUND_CATALOG.get(_top_f_code, {})
            _top_f_name = _top_f_meta.get("fund_name", f"优选基金_{_top_f_code}")
            _def_amt = plan_capital * _def_w
            _off_amt = plan_capital * _off_w
            _m_title_now = QUANT_MODELS_CATALOG.get(sel_model_type, {}).get("name", "鲁棒双核HRP")
            _worst_dd_pct = float(readable_kpi.get('worst_case_drawdown_pct', 0.0))
            _worst_dd_amt = plan_capital * (_worst_dd_pct / 100.0)
            _underwater_d = int(readable_kpi.get('max_underwater_days', 0))
            _win_1y = float(readable_kpi.get('win_rate_1y', 0.0))
            _best_ret = float(readable_kpi.get('best_case_return_pct', 0.0))
            _best_amt = float(readable_kpi.get('best_case_profit_amount', 0.0))

            c_attr1, c_attr2, c_attr3 = st.columns(3)
            with c_attr1:
                safe_markdown_html(f"""
                <div class="decision-card" style="height: 100%; border-top: 3px solid var(--color-down); margin-bottom: 6px;">
                    <div class="decision-title" style="color: var(--color-down); font-weight: 700;">
                        收益与胜率
                    </div>
                    <div class="decision-desc">
                        <b>1年达标胜率</b>：<span style="font-size: 14px; font-weight: 800; color: var(--color-down);">{_win_1y:.1f}%</span> ｜ 最好单年: +{_best_ret:.1f}% (+¥{_best_amt:,.0f})<br>
                        <b>内生票息安全垫</b>：年化 <b>¥{_ann_cush:,.0f}</b>/年 (月均 ¥{_mo_cush:,.0f} ｜ 加权息率 <b>{_w_yield:.2f}%</b>)<br>
                        <b>收息防守底仓</b>：¥{_def_amt:,.0f} ({_def_w*100:.1f}%) 筑牢收益安全线
                    </div>
                </div>
                """)

            with c_attr2:
                safe_markdown_html(f"""
                <div class="decision-card" style="height: 100%; border-top: 3px solid var(--color-up); margin-bottom: 6px;">
                    <div class="decision-title" style="color: var(--color-up); font-weight: 700;">
                        风险底线
                    </div>
                    <div class="decision-desc">
                        <b>历史至暗浮亏</b>：<span style="font-size: 14px; font-weight: 800; color: var(--color-up);">-{_worst_dd_pct:.1f}%</span> (预估最大缩水 -¥{_worst_dd_amt:,.0f})<br>
                        <b>最长水下回本</b>：约 <b>{_underwater_d} 天</b> (约 {readable_kpi.get('max_underwater_months', 0.0):.1f} 个月)，长钱长投以时间换空间<br>
                        <b>实盘纪律铁律</b>：不满 7 天严禁赎回防 1.5% 惩罚费；磨底期严禁割肉
                    </div>
                </div>
                """)

            with c_attr3:
                safe_markdown_html(f"""
                <div class="decision-card" style="height: 100%; border-top: 3px solid var(--accent-primary); margin-bottom: 6px;">
                    <div class="decision-title" style="color: var(--accent-primary); font-weight: 700;">
                        攻防定权
                    </div>
                    <div class="decision-desc">
                        <b>攻防仓位配比</b>：防守收息 {_def_w*100:.0f}% + 进攻弹性 {_off_w*100:.0f}% (¥{_off_amt:,.0f})<br>
                        <b>第一重仓标的</b>：{_top_f_name} ({_top_f_code}) 占比 <b>{_top_f_w*100:.1f}%</b><br>
                        <b>机构定权模型</b>：采用【{_m_title_now}】避免赛道踩踏，ERP 分位 {erp_pct:.1f}%
                    </div>
                </div>
                """)

            alloc_list_for_dca = [
                {"code": it["fund_code"], "name": it["fund_name"], "weight": float(it.get("target_weight_pct", it.get("target_weight", 0.0))) / 100.0}
                for it in blueprint.get("items", [])
            ]

            active_cheat_sheet_text = cheat_sheet_text
            df_display = df_bp.copy()
            dynamic_col_config = {
                "目标占比(%)": st.column_config.ProgressColumn(min_value=0, max_value=60, format="%.1f%%"),
                "精确买入金额(元)": st.column_config.NumberColumn(format="¥%.2f"),
                "最新净值": st.column_config.NumberColumn(format="%.4f"),
                "实时估值涨跌(%)": st.column_config.NumberColumn(format="%+.2f%%"),
                "实操分红与限购指引": st.column_config.TextColumn(
                    "实操分红与限购指引 ⓘ",
                    help="下单实操要点：红利类设为【现金分红】锁住收益；限额标的自动拆单；A类长投免赎，C类适合弹性波段。"
                ),
            }

            three_step_plan = None
            dca_plan = None
            has_etf_dca = False

            if "稳健三步" in cap_deployment_mode:
                three_step_plan = SmartExecutionDCAEngine.plan_three_step_batches(
                    total_capital=float(plan_capital),
                    allocations=alloc_list_for_dca,
                    market_snapshot=snapshot
                )
                cols_batches = st.columns(3)
                for b_idx, b_info in enumerate(three_step_plan["batches"]):
                    with cols_batches[b_idx]:
                        safe_markdown_html(f"""
                        <div class="decision-card" style="padding: 10px 12px; height: 100%; margin-bottom: 6px;">
                            <div style="font-size: 13px; font-weight: 700; color: var(--text-primary); margin-bottom: 2px;">{b_info['title']}</div>
                            <div style="font-size: 15px; font-weight: 800; color: var(--accent-primary); margin-bottom: 4px;">¥{b_info['amount']:,.2f}</div>
                            <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 4px;">触发时机: <b>{b_info['timing']}</b></div>
                            <div style="font-size: 11px; color: var(--text-secondary); line-height: 1.4;">{b_info['notes']}</div>
                        </div>
                        """)
                df_display["今日底仓买入(50%)"] = df_display["精确买入金额(元)"] * 0.50
                df_display["逢低网格挂单(30%)"] = df_display["精确买入金额(元)"] * 0.30
                df_display["右侧突破加仓(20%)"] = df_display["精确买入金额(元)"] * 0.20
                dynamic_col_config["今日底仓买入(50%)"] = st.column_config.NumberColumn(format="¥%.2f")
                dynamic_col_config["逢低网格挂单(30%)"] = st.column_config.NumberColumn(format="¥%.2f")
                dynamic_col_config["右侧突破加仓(20%)"] = st.column_config.NumberColumn(format="¥%.2f")

                cs_lines = [cheat_sheet_text, "\\n【🌊 稳健三步分批建仓执行小抄】"]
                for _, r in df_display.iterrows():
                    cs_lines.append(f"标的: {r['基金代码']} ({r['基金名称']}) -> 第1步今日底仓: ¥{r['今日底仓买入(50%)']:,.2f} | 第2步逢低网格: ¥{r['逢低网格挂单(30%)']:,.2f} | 第3步右侧加仓: ¥{r['右侧突破加仓(20%)']:,.2f}")
                active_cheat_sheet_text = "\\n".join(cs_lines)

            elif "智能定投" in cap_deployment_mode:
                erp_pct = float(snapshot.get("erp_percentile", 78.0))
                bias_20 = float(snapshot.get("c300_bias_20", snapshot.get("bias_20", 1.0)))
                dca_plan = SmartExecutionDCAEngine.plan_smart_dca(
                    total_capital=float(plan_capital),
                    allocations=alloc_list_for_dca,
                    erp_percentile=erp_pct,
                    bias_20=bias_20,
                    periods=12
                )
                ruler_dca = StrategyBridge.get_historical_inflection_ruler(
                    current_erp=erp_pct,
                    current_bias=bias_20,
                    total_capital=float(plan_capital)
                )
                safe_markdown_html(render_historical_inflection_ruler_html(ruler_dca))

                col_d1, col_d2, col_d3 = st.columns([3, 4, 3])
                with col_d1:
                    st.metric("定投周期与基准金额", f"¥{dca_plan['base_per_period']:,.2f} /期", "共 12 期")
                with col_d2:
                    st.metric("当期自适应乘数", f"{dca_plan['multiplier']:.2f}x ({dca_plan['multiplier_tag']})", dca_plan['valuation_status'])
                with col_d3:
                    st.metric("本期建议扣款金额", f"¥{dca_plan['actual_deduction']:,.2f}", f"基准: ¥{dca_plan['base_per_period']:,.2f}")

                vwap_sum = dca_plan.get("vwap_execution_summary", {})
                if vwap_sum:
                    has_etf_dca = any(o.get("is_etf", False) for o in dca_plan.get("fund_orders", []))
                    col_v1, col_v2, col_v3 = st.columns([3, 4, 3])
                    with col_v1:
                        if has_etf_dca:
                            st.metric("快速冲击模拟损耗", f"¥{vwap_sum.get('total_naive_impact_yuan', 0.0):,.2f}", "单笔市价吃单冲击")
                        else:
                            st.metric("早盘盲买偏差损耗", f"¥{vwap_sum.get('total_naive_impact_yuan', 0.0):,.2f}", "早盘未知净值波动偏差")
                    with col_v2:
                        if has_etf_dca:
                            st.metric("VWAP优化执行滑点", f"¥{vwap_sum.get('total_vwap_slippage_yuan', 0.0):,.2f}", "分时成交量加权平抑")
                        else:
                            st.metric("尾盘锚定执行损耗", f"¥{vwap_sum.get('total_vwap_slippage_yuan', 0.0):,.2f}", "14:30 尾盘估值锚定执行")
                    with col_v3:
                        st.metric("智能微观优化节省", f"¥{vwap_sum.get('total_slippage_saved_yuan', 0.0):,.2f}", f"节省 {vwap_sum.get('avg_slippage_saved_bps', 0.0):.1f} bps 冲击损耗")

                mult = dca_plan.get("multiplier", 1.0)
                df_display["基准每期定投(元)"] = df_display["精确买入金额(元)"] / 12.0
                df_display["本期乘数修正后实扣(元)"] = (df_display["精确买入金额(元)"] / 12.0) * mult
                dynamic_col_config["基准每期定投(元)"] = st.column_config.NumberColumn(format="¥%.2f")
                dynamic_col_config["本期乘数修正后实扣(元)"] = st.column_config.NumberColumn(format="¥%.2f")

                order_map = {str(o.get("code")): o for o in dca_plan.get("fund_orders", [])}
                col_naive_head = "快速冲击损耗(元)" if has_etf_dca else "早盘盲买偏差(元)"
                col_vwap_head = "VWAP执行滑点(元)" if has_etf_dca else "尾盘锚定损耗(元)"
                col_saved_head = "优化节省损耗(元)" if has_etf_dca else "尾盘优化节省(元)"

                df_display[col_naive_head] = df_display["基金代码"].astype(str).map(lambda c: order_map.get(c, {}).get("naive_impact_yuan", 0.0))
                df_display[col_vwap_head] = df_display["基金代码"].astype(str).map(lambda c: order_map.get(c, {}).get("vwap_slippage_yuan", 0.0))
                df_display[col_saved_head] = df_display["基金代码"].astype(str).map(lambda c: order_map.get(c, {}).get("slippage_saved_yuan", 0.0))
                df_display["优化节省(bps)"] = df_display["基金代码"].astype(str).map(lambda c: order_map.get(c, {}).get("slippage_saved_bps", 0.0))
                dynamic_col_config[col_naive_head] = st.column_config.NumberColumn(format="¥%.2f")
                dynamic_col_config[col_vwap_head] = st.column_config.NumberColumn(format="¥%.2f")
                dynamic_col_config[col_saved_head] = st.column_config.NumberColumn(format="¥%.2f")
                dynamic_col_config["优化节省(bps)"] = st.column_config.NumberColumn(format="%.1f bps", help="单基真实年化波动率与自身偏离度测算之微观执行优化节省基点")

                def _inject_dca_anomaly_guidance(row):
                    fc = str(row["基金代码"])
                    fn = str(row["基金名称"])
                    rt_g = row.get("实时估值涨跌(%)", 0.0)
                    anom = StrategyBridge.evaluate_tail_valuation_anomaly(fc, fn, realtime_quote=rt_g)
                    orig_g = str(row.get("实操分红与限购指引", ""))
                    if anom.get("is_anomaly"):
                        return f"{anom['anomaly_tag']} ｜ {orig_g}"
                    saved_bps = order_map.get(fc, {}).get("slippage_saved_bps", 0.0)
                    if saved_bps > 0:
                        return f"{orig_g}·微观省{saved_bps:.1f}bp"
                    return orig_g

                df_display["实操分红与限购指引"] = df_display.apply(_inject_dca_anomaly_guidance, axis=1)

                cs_lines = [cheat_sheet_text, f"\\n【📅 估值自适应智能定投执行小抄 (乘数: {mult:.2f}x · 微观执行优化版)】"]
                for _, r in df_display.iterrows():
                    cs_lines.append(f"标的: {r['基金代码']} ({r['基金名称']}) -> 基准定投: ¥{r['基准每期定投(元)']:,.2f}/期 | 本期实扣: ¥{r['本期乘数修正后实扣(元)']:,.2f} | 优化损耗: ¥{r[col_vwap_head]:,.2f} (优化省¥{r[col_saved_head]:,.2f} / {r.get('优化节省(bps)', 0.0):.1f}bps)")
                active_cheat_sheet_text = "\\n".join(cs_lines)

            if overrides:
                st.info(f"💡 检测到您自定义替换了 {len(overrides)} 只标的：{overrides}，配置方案已实时动态调整。")

            st.dataframe(
                df_display,
                column_config=dynamic_col_config,
                use_container_width=True,
                hide_index=True
            )

            # ── 模块 3：底部单行 4 操作与单一白盒抽屉 ──
            succ_state = st.session_state.get("tab1_overwrite_success")
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

            col_act_cur, col_act_new, col_act_cs, col_act_bt = st.columns([2.8, 2.8, 2.2, 2.2])
            with col_act_cur:
                mlm_inst = st.session_state.get("mlm") or (MultiLedgerManager.get_instance() if MultiLedgerManager else None)
                cur_lid = st.session_state.get("active_ledger_id", "main_live")
                cur_meta = mlm_inst.get_ledger_meta(cur_lid) if mlm_inst else {}
                cur_name = (cur_meta or {}).get("name", "当前账本")
                cur_h_count = len(pm.holdings)
                cur_equity = pm.total_equity
                cur_pending_count = len(pm.pending_orders)
                plan_cap_val = float(blueprint.get("total_capital", plan_capital))

                with st.popover(f"📥 覆盖写入当前账本 ({cur_name})", use_container_width=True):
                    st.markdown(f"##### ⚠️ 覆盖写入确认【{cur_name}】")
                    safe_markdown_html(f"""
                    <div style="background: rgba(239, 68, 68, 0.08); border-left: 3px solid var(--color-up); padding: 8px 12px; margin-bottom: 8px; border-radius: 4px; font-size: 12px;">
                        <b>目标账本</b>：{cur_name} (<code>{cur_lid}</code>)<br>
                        <b>现有存量持仓</b>：<b>{cur_h_count} 只</b> ｜ 总资产：¥{cur_equity:,.2f}<br>
                        <b>在途未结订单</b>：{cur_pending_count} 笔<br>
                        <b>新写入建仓方案</b>：拟投入总本金 <b>¥{plan_cap_val:,.2f}</b> ｜ 节奏：{cap_deployment_mode.split('（')[0]}
                    </div>
                    """)
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
                        plan_data = three_step_plan if "稳健三步" in cap_deployment_mode else (dca_plan if "智能定投" in cap_deployment_mode and 'dca_plan' in locals() and dca_plan is not None else None)
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
                        st.rerun()

            with col_act_new:
                with st.popover("🆕 另存为全新独立账本", use_container_width=True):
                    st.markdown("##### 🆕 另存为全新独立账本")
                    st.caption("创建新账本并直接将本次建仓方案写入，绝不影响主实盘或其他存量账本。")
                    save_new_name = st.text_input("新账本名称", value=f"新资建仓_{datetime.now().strftime('%m%d_%H%M')}", key="t1_save_new_name")
                    save_new_type = st.selectbox("账本类型", ["沙盒演练 (sandbox)", "家庭专项 (family)", "独立实盘 (live)"], key="t1_save_new_type")
                    save_new_type_code = "sandbox" if "sandbox" in save_new_type else ("family" if "family" in save_new_type else "live")
                    t_val = st.session_state.get("active_tier_val", "C3")
                    tier_idx = ["C1", "C2", "C3", "C4", "C5"].index(t_val) if t_val in ["C1", "C2", "C3", "C4", "C5"] else 2
                    save_new_tier = st.selectbox("专属风险档位", ["C1", "C2", "C3", "C4", "C5"], index=tier_idx, key="t1_save_new_tier")

                    if st.button("输入新账本名称一键创建并写入持仓", type="primary", use_container_width=True, key="btn_confirm_save_new_ledger"):
                        if mlm_inst:
                            total_cap = float(blueprint.get("total_capital", plan_capital))
                            new_lid = mlm_inst.create_ledger(
                                name=save_new_name.strip() or f"建仓方案_{datetime.now().strftime('%m%d_%H%M')}",
                                base_cash=total_cap,
                                ledger_type=save_new_type_code,
                                default_tier=save_new_tier,
                                description="由新资建仓一键生成"
                            )
                            new_pm = mlm_inst.get_pm(new_lid)
                            plan_data = three_step_plan if "稳健三步" in cap_deployment_mode else (dca_plan if "智能定投" in cap_deployment_mode and 'dca_plan' in locals() and dca_plan is not None else None)
                            res_apply = new_pm.apply_zero_start_blueprint(
                                blueprint,
                                cap_deployment_mode=cap_deployment_mode,
                                deployment_plan=plan_data
                            )
                            new_pm.save_state(record_snapshot=True)
                            switch_active_ledger(new_lid)
                            st.balloons()
                            st.success(f"已成功创建新账本【{save_new_name}】并写入持仓！")
                            st.rerun()

            with col_act_cs:
                with st.popover("📱 下单小抄", use_container_width=True):
                    st.markdown("##### 📱 下单一键复制小抄")
                    st.caption("您可以直接复制下方文本发送给微信或记事本，对照手机银行、天天基金、蚂蚁财富一分钟完成买入：")
                    st.code(active_cheat_sheet_text, language="text")

            with col_act_bt:
                if st.button("📈 送入穿透回测", type="secondary", use_container_width=True, key="btn_send_bp_to_bt"):
                    st.session_state.selected_backtest_weights = dict(cur_opt_w)
                    st.session_state.selected_backtest_target = "新建仓组合"
                    st.session_state.tab3_backtest_activated = True
                    st.success("✅ 已将此组合送入组合回测，请切换至 Tab 3 检视。")

            # ── 底部唯一白盒抽屉 ──
            with st.expander("🔬 展开机构级量化压力测试与选基白盒证据", expanded=False):
                # 3 张滚动胜率卡（双口径对照：当下相似条件胜率 vs 全历史胜率）
                st.markdown("#### 🎯 跨牛熊滚动胜率")
                _wr_cols = st.columns(3)
                for _wi, (_wk, _wv) in enumerate(wr_table.items()):
                    with _wr_cols[_wi]:
                        _cond_wr = float(_wv.get("conditional_win_rate", _wv.get("win_rate", 0.0))) * 100.0
                        _uncond_wr = float(_wv.get("unconditional_win_rate", _wv.get("win_rate", 0.0))) * 100.0
                        _med_ann = float(_wv.get("median_ann_return", _wv.get("median_return", 0.0))) * 100.0
                        _no_loss = float(_wv.get("no_loss_rate", 0.0)) * 100.0
                        _beat_cash = float(_wv.get("beat_cash_rate", _no_loss * 0.95)) * 100.0
                        _tot_w = int(_wv.get("total_windows", 0))
                        safe_markdown_html(f"""
                        <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 12px 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
                            <div style="font-size: 13px; font-weight: 600; color: var(--text-secondary); display: flex; justify-content: space-between;">
                                <span>{_wv['label']} 达标胜率</span>
                                <span style="font-size: 11px; color: var(--accent-primary); background: var(--bg-elevated); padding: 1px 6px; border-radius: 4px;">{_tot_w:,} 期样本</span>
                            </div>
                            <div style="font-size: 24px; font-weight: 700; color: var(--text-primary); margin: 4px 0;">
                                {_cond_wr:.1f}%
                                <span style="font-size: 12px; font-weight: 500; color: var(--text-muted);">(全历史 {_uncond_wr:.1f}%)</span>
                            </div>
                            <div style="font-size: 12px; color: var(--text-secondary); font-weight: 500;">
                                正收益概率 <b>{_no_loss:.0f}%</b> ｜ 跑赢货基 <b>{_beat_cash:.0f}%</b> ｜ 中位年化 <b>{_med_ann:.1f}%</b>
                            </div>
                        </div>
                        """)

                with st.expander("ℹ️ 量化数学定义：多维胜率与尾部底线 (CVaR)", expanded=False):
                    st.markdown(r"""
                    - **达标胜率**：在历史所有滚动持有期窗口中，组合真实年化收益率 $\ge$ 用户设定目标年化收益率的加权百分比；
                    - **正收益概率 (收益 $\ge 0\%$)**：持有期满本金不亏损的概率（本金安全率）。纯债配置较高时此项较高，但不可与“达标胜率”混为一谈；
                    - **跑赢货基率 (收益 $\ge 1.8\%$)**：年化净收益超越同期货币基金与现金管理的概率，反映承担波动是否获得有效流动性溢价；
                    - **95% 尾部底线 (CVaR)**：在历史最极端的 5% 尾部黑天鹅行情中，组合的平均亏损底线，杜绝深度套牢。
                    """)

                # 5 张大字号人话指标卡（标题严格 ≤ 6 字）
                k_col1, k_col2, k_col3, k_col4, k_col5 = st.columns(5)
                with k_col1:
                    safe_markdown_html(f"""
                    <div class="kpi-metric-card" >
                        <div class="kpi-card-title">① 最好情况</div>
                        <div class="metric-value-huge" style="color: {active_co['color_up']};">
                            +{readable_kpi.get('best_case_return_pct', 0.0):.2f}%
                        </div>
                        <div class="kpi-card-sub" style="color: {active_co['color_up']};">
                            预计盈利: <b>+¥{readable_kpi.get('best_case_profit_amount', 0.0):,.2f}</b>
                        </div>
                        <div class="kpi-card-desc">任意持有1年最高单年收益</div>
                    </div>
                    """)

                with k_col2:
                    safe_markdown_html(f"""
                    <div class="kpi-metric-card" >
                        <div class="kpi-card-title">② 最坏情况</div>
                        <div class="metric-value-huge" style="color: {active_co['color_down']};">
                            -{readable_kpi.get('worst_case_drawdown_pct', 0.0):.2f}%
                        </div>
                        <div class="kpi-card-sub" style="color: {active_co['color_down']};">
                            账面最大浮亏: <b>-¥{readable_kpi.get('worst_case_loss_amount', 0.0):,.2f}</b>
                        </div>
                        <div class="kpi-card-desc">历史全周期最极端至暗时刻</div>
                    </div>
                    """)

                with k_col3:
                    safe_markdown_html(f"""
                    <div class="kpi-metric-card" >
                        <div class="kpi-card-title">③ 水下回本</div>
                        <div class="metric-value-huge" style="color: var(--accent-primary);">
                            {readable_kpi.get('max_underwater_days', 0)} <span style="font-size:16px;">天</span>
                        </div>
                        <div class="kpi-card-sub" style="color: var(--text-primary);">
                            最长水下: <b>约 {readable_kpi.get('max_underwater_months', 0.0):.1f} 个月</b>
                        </div>
                        <div class="kpi-card-desc">买在历史最高点回本所需时长</div>
                    </div>
                    """)

                with k_col4:
                    safe_markdown_html(f"""
                    <div class="kpi-metric-card" >
                        <div class="kpi-card-title">④ 目标胜率</div>
                        <div class="metric-value-huge" style="color: var(--accent-primary);">
                            {readable_kpi.get('win_rate_1y', 0.0):.1f}%
                        </div>
                        <div class="kpi-card-sub" style="color: var(--text-primary);">
                            1年: <b>{readable_kpi.get('win_rate_1y', 0.0):.1f}%</b> ｜ 2年: <b>{readable_kpi.get('win_rate_2y', 0.0):.1f}%</b>
                        </div>
                        <div class="kpi-card-desc">持有满 3 年胜率 {readable_kpi.get('win_rate_3y', 0.0):.1f}%</div>
                    </div>
                    """)

                with k_col5:
                    safe_markdown_html(f"""
                    <div class="kpi-metric-card" >
                        <div class="kpi-card-title">⑤ 适合资金</div>
                        <div class="metric-value-huge" style="color: var(--text-primary); font-size: 20px; line-height: 1.4;">
                            {active_tier} {cur_tier_meta['name']}
                        </div>
                        <div class="kpi-card-sub" style="color: var(--text-secondary); font-size: 11px;">
                            {readable_kpi.get('suitable_for', '')}
                        </div>
                        <div class="kpi-card-desc" style="font-size: 11px;">{readable_kpi.get('soul_summary', '')}</div>
                    </div>
                    """)

                # 组合内生股息与票息安全垫卡片
                safe_markdown_html(f"""
                <div style="background: rgba(16, 185, 129, 0.08); border-left: 4px solid var(--color-down); padding: 10px 14px; border-radius: 6px; margin: 10px 0; font-size: 13px;">
                    <span style="font-weight: 700; color: var(--color-down);">💰 组合内生股息与票息安全垫：</span>
                    <span style="color: var(--text-primary);">预计年化 <b>¥{_ann_cush:,.0f}</b>/年（折合月均 <b>¥{_mo_cush:,.0f}</b>/月 ｜ 加权息率 <b>{_w_yield:.2f}%</b>）</span>
                </div>
                """)

                # 🌪️ 历史黑天鹅极端承压测试卡片
                try:
                    stress_data = simulate_black_swan_stress(
                        holdings=opt_weights,
                        total_capital=float(plan_capital),
                        df_bt=bt_df if not bt_df.empty else None
                    )
                    render_black_swan_stress_card(stress_data)
                except Exception as e:
                    st.caption(f"（黑天鹅承压测试卡片渲染提示: {e}）")

                # G10: 蒙特卡洛极端承压 3D 分布曲面图
                try:
                    bootstrap_stress_data = pm.simulate_portfolio_cvar_bootstrap(
                        holdings=opt_weights,
                        total_capital=float(plan_capital),
                        investor_risk_tier=active_tier,
                        pm_instance=pm
                    )
                    render_monte_carlo_3d_chart(bootstrap_stress_data)
                except Exception as e_mc3d:
                    st.caption(f"（蒙特卡洛 3D 曲面图加载提示: {e_mc3d}）")

                # 白盒折叠框 1: 全市场选基漏斗与评分表
                with st.expander("🔍 选基漏斗与评分", expanded=False):
                    f_c1, f_c2, f_c3, f_c4 = st.columns(4)
                    with f_c1:
                        _tot_m = funnel_stats.get('total_market_funds', 28177)
                        st.metric("1. 全市场基金底池", f"{_tot_m:,} 只", "全市场公募基金总数")
                    with f_c2:
                        _comp_s = funnel_stats.get('compliance_screened_funds', 6850)
                        st.metric("2. 六维量化初筛池", f"{_comp_s:,} 只", "规模>2亿·成立>3年·合规排雷")
                    with f_c3:
                        funnel_stats['candidate_funds'] = funnel_stats.get('candidate_funds', max(28, num_funds_input * 6))
                        st.metric("3. 5大赛道入围池", f"{funnel_stats['candidate_funds']} 只", "核心赛道低费率&高Alpha候选池")
                    with f_c4:
                        _champ_s = len(opt_weights)
                        st.metric("4. 最终优选金牌组合", f"{_champ_s} 只", f"动态对齐用户调节的 {num_funds_input} 只", delta_color="inverse")

                    col_f_title, col_f_pop = st.columns([8, 2])
                    with col_f_title:
                        st.markdown("##### 📐 六维评分公式")
                    with col_f_pop:
                        with st.popover("ⓘ 评分细则", use_container_width=True):
                            st.markdown("""
                            **六维评分标准 (0~100 分)：**
                            1. **超额收益 (35%)**：近3年超额 Alpha 分位数；
                            2. **综合费率 (25%)**：申赎与管理销售服务费率综合折算；
                            3. **底层排雷 (15%)**：商誉、质押、存贷双高与解禁排雷；
                            4. **聪明钱流 (10%)**：北向增持、机构重仓占比与净流入；
                            5. **反拥挤度 (10%)**：行业及个股集中度过高抱团惩罚；
                            6. **宏观契合 (5%)**：与当前 ERP/DR007 同温层契合度。
                            """)
                    st.info("总评得分 = 35%×超额收益 + 25%×低费率 + 15%×排雷健康 + 10%×聪明钱 + 10%×反拥挤 + 5%×宏观契合")

                    st.markdown("##### 📊 冠军基金评分表")
                    if not quant_table.empty:
                        st.dataframe(
                            quant_table,
                            column_config={
                                "六维总评得分": st.column_config.NumberColumn(format="%.2f分"),
                                "超额Alpha得分(35%)": st.column_config.NumberColumn(format="%.1f分"),
                                "低费率得分(25%)": st.column_config.NumberColumn(format="%.1f分"),
                                "底层排雷健康分(15%)": st.column_config.NumberColumn(format="%.1f分"),
                                "聪明钱流入分(10%)": st.column_config.NumberColumn(format="%.1f分"),
                                "反拥挤安全分(10%)": st.column_config.NumberColumn(format="%.1f分"),
                                "衍生品契合分(5%)": st.column_config.NumberColumn(format="%.1f分"),
                                "配置权重(%)": st.column_config.ProgressColumn(min_value=0, max_value=60, format="%.1f%%"),
                            },
                            use_container_width=True,
                            hide_index=True
                        )

                    if alts_map:
                        st.caption("🏆 赛道冠军标的与备选替换下拉框（选基与建仓单 100% 联动）：")
                        cols_slots = st.columns(min(len(alts_map), 4))
                        for idx_s, (slot_k, slot_data) in enumerate(alts_map.items()):
                            c_col = cols_slots[idx_s % len(cols_slots)]
                            with c_col:
                                s_champ = slot_data["champion_code"]
                                s_champ_name = slot_data["champion_name"]
                                opts = [f"🏆 {s_champ} {s_champ_name}"]
                                for a_it in slot_data.get("top_alternatives", []):
                                    opts.append(f"🥈 {a_it['code']} {a_it['name']} ({a_it.get('tag', '优质备选')})")

                                cur_ovr = st.session_state.custom_fund_overrides.get(s_champ)
                                s_idx = 0
                                if cur_ovr:
                                    for o_i, o_str in enumerate(opts):
                                        if cur_ovr in o_str:
                                            s_idx = o_i
                                            break
                                chosen = st.selectbox(
                                    slot_data["sector_name"],
                                    opts,
                                    index=s_idx,
                                    key=f"slot_sel_{slot_k}_{num_funds_input}"
                                )
                                old_ovr = st.session_state.custom_fund_overrides.get(s_champ)
                                new_ovr = None
                                if not chosen.startswith("🏆"):
                                    sel_c = chosen.split()[1]
                                    new_ovr = sel_c
                                    st.session_state.custom_fund_overrides[s_champ] = sel_c
                                else:
                                    if s_champ in st.session_state.custom_fund_overrides:
                                        del st.session_state.custom_fund_overrides[s_champ]
                                
                                if old_ovr != new_ovr:
                                    st.session_state.tab1_step3_cache = None
                                    st.session_state.tab1_trigger_s3 = True
                                    if st.session_state.get("tab1_sim_cache"):
                                        opt_w = dict(st.session_state["tab1_sim_cache"].get("optimal_weights", {}))
                                        target_c = new_ovr if new_ovr else s_champ
                                        prev_c = old_ovr if old_ovr else s_champ
                                        if prev_c in opt_w:
                                            val = opt_w.pop(prev_c)
                                            opt_w[target_c] = val
                                        elif s_champ in opt_w:
                                            val = opt_w.pop(s_champ)
                                            opt_w[target_c] = val
                                        st.session_state["tab1_sim_cache"]["optimal_weights"] = opt_w

                                        # 同步更新 quant_table 中对应的标的代码与名称
                                        q_df = st.session_state["tab1_sim_cache"].get("quant_table")
                                        if q_df is not None and not q_df.empty:
                                            q_df = q_df.copy()
                                            mask = q_df["基金代码"].astype(str) == str(prev_c)
                                            if mask.any():
                                                new_name = CORE_STRATEGY_POOL.get(target_c, {}).get("fund_name") or EXTENDED_FUND_CATALOG.get(target_c, {}).get("fund_name") or f"公募基金_{target_c}"
                                                q_df.loc[mask, "基金代码"] = str(target_c)
                                                q_df.loc[mask, "基金名称"] = new_name
                                                st.session_state["tab1_sim_cache"]["quant_table"] = q_df
                                    st.rerun()

                # 白盒折叠框 2: 宏观决策信号
                with st.expander("🧭 宏观决策信号", expanded=False):
                    c_sig1, c_sig2, c_sig3, c_sig4 = st.columns(4)
                    with c_sig1:
                        safe_markdown_html(f"""
                        <div class="decision-card">
                            <div class="decision-title">① 市场温度与估值水位</div>
                            <div class="decision-val">{snapshot.get('market_state', '震荡收息期')}</div>
                            <div class="decision-desc">
                                沪深300点位: <b>{snapshot.get('c300', 4000.0):,.0f}</b><br>
                                ERP 估值分位: <b>{snapshot.get('erp_percentile', 78.5):.1f}%</b> (高性价比击球区)
                            </div>
                        </div>
                        """)
                    with c_sig2:
                        sig_snr = float(snapshot.get("er_snr", 0.65))
                        sig_eff_window = snapshot.get('effective_momentum_window', 60)
                        sig_accel = float(snapshot.get("mom_accel", 0.0))
                        sig_exhaustion = bool(snapshot.get("momentum_exhaustion_warning", False))
                        sig_warn_text = snapshot.get("momentum_exhaustion_text") or "「⚡ 动量衰竭预警：暂停追高进攻标的，新增资金转入红利/纯债缓冲」"
                        sig_warn_block = ""
                        if sig_exhaustion:
                            sig_warn_block = f'<div style="color: var(--color-up); font-size: 11px; font-weight: 600; margin-top: 4px; padding: 3px 6px; background: var(--bg-elevated); border-radius: 4px; border: 1px solid var(--border-subtle); line-height: 1.3;">{sig_warn_text}</div>'

                        safe_markdown_html(f"""
                        <div class="decision-card">
                            <div class="decision-title">② 均线动量状态 (MA20)</div>
                            <div class="decision-val" style="color: var(--accent-primary);">{snapshot.get('m20_status_desc', '站上均线')}</div>
                            <div class="decision-desc">
                                MA20 乖离率: <b>{snapshot.get('bias_20', 1.2):+.2f}%</b><br>
                                考夫曼信噪比 (ER / SNR): <b>{sig_snr:.2f}</b> (自适应变速窗口: {sig_eff_window}日)<br>
                                动量加速度 (Mom Accel): <b>{sig_accel:+.2f}%</b><br>
                                技术研判: 右侧趋势形成，顺势跟进红利与成长动量。
                                {sig_warn_block}
                            </div>
                        </div>
                        """)
                    with c_sig3:
                        safe_markdown_html(f"""
                        <div class="decision-card">
                            <div class="decision-title">③ 宏观资金利率 (DR007)</div>
                            <div class="decision-val" style="color: var(--accent-primary);">{snapshot.get('dr007_status', '流动性合理充裕')}</div>
                            <div class="decision-desc">
                                DR007 7天移动均值: <b>{snapshot.get('dr007_7d_ma', 1.62):.2f}%</b><br>
                                流动性定调: 资金面平稳，债市底仓安全无虞。
                            </div>
                        </div>
                        """)
                    with c_sig4:
                        safe_markdown_html(f"""
                        <div class="decision-card">
                            <div class="decision-title">④ 期权波动率防波堤 (iVIX)</div>
                            <div class="decision-val" style="color: var(--text-secondary);">{snapshot.get('ivix_status', '期权隐含波动率平稳')}</div>
                            <div class="decision-desc">
                                EWMA 历史波动率: <b>{snapshot.get('ewma_vol', 12.8):.1f}%</b><br>
                                情绪定调: 尾部对冲成本低，适合配置长久期优质资产。
                            </div>
                        </div>
                        """)

                # G10: 挂载大额订单流动性折价明细表 (全模式覆盖)
                try:
                    active_orders = []
                    if dca_plan and dca_plan.get("fund_orders"):
                        active_orders = dca_plan["fund_orders"]
                    else:
                        for _, r in df_display.iterrows():
                            _fc = str(r.get("基金代码", "")).zfill(6)
                            _fn = str(r.get("基金名称", _fc))
                            _amt = float(r.get("精确买入金额(元)", 0.0))
                            _hc = data_loader.calculate_otc_fund_liquidity_haircut(order_amount=_amt, fund_code=_fc, fund_name=_fn)
                            active_orders.append({
                                "fund_code": _fc,
                                "fund_name": _fn,
                                "order_amount": _amt,
                                "is_etf": _hc.get("is_etf", False),
                                "fund_aum_yuan": _hc.get("fund_aum_yuan", 0.0),
                                "top5_adv_yuan": _hc.get("top5_adv_yuan", 0.0),
                                "redemption_ratio_pct": _hc.get("redemption_ratio_pct", 0.0),
                                "liquidity_haircut_bps": _hc.get("haircut_bps", 0.0),
                                "liquidity_haircut_yuan": _hc.get("haircut_yuan", 0.0),
                                "slippage_saved_yuan": _hc.get("slippage_saved_yuan", 0.0),
                            })
                    render_liquidity_haircut_table(active_orders)
                except Exception as e_liq_tab1:
                    st.caption(f"（流动性折价表加载提示: {e_liq_tab1}）")

                # 分批/定投执行调度表
                if "智能定投" in cap_deployment_mode and dca_plan:
                    exp_label = "⏱️ 查看分批挂单执行调度表（尾盘净值锁定与跨日分批优化）" if not has_etf_dca else "⏱️ 查看 VWAP 分时成交量加权挂单调度表（日内 5 阶段分笔平抑冲击）"
                    with st.expander(exp_label, expanded=False):
                        sample_slices = []
                        if dca_plan.get("fund_orders"):
                            sample_slices = dca_plan["fund_orders"][0].get("execution_slippage", {}).get("vwap_slices", [])
                        if sample_slices:
                            st.dataframe(pd.DataFrame(sample_slices), use_container_width=True, hide_index=True)
'''

# Preserve CRLF if original had CRLF
if "\r\n" in content:
    new_tab1_body = new_tab1_body.replace("\r\n", "\n").replace("\n", "\r\n")

updated_content = content[:start_idx] + new_tab1_body + content[end_idx:]

# Validate AST syntax
try:
    ast.parse(updated_content)
    print("AST verification passed: 0 syntax errors.")
except SyntaxError as e:
    print(f"AST SyntaxError: {e}")
    raise

gui_file.write_text(updated_content, encoding="utf-8")
print(f"Successfully updated {gui_file}")
