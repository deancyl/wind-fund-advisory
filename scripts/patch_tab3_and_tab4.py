import re
import sys
from pathlib import Path

def patch_app_gui():
    target = Path("AGY2_FundAdvisory/app_gui.py")
    code = target.read_text(encoding="utf-8")

    # 1. Tab 3 Survivor bias warning card and toggle
    tab3_target = '''    # 2018-2026 全周期真实净值推演曲线 (同屏对标自选基准)
    st.markdown("#### 🚀 全周期净值曲线")

    fig_nav = go.Figure()'''

    tab3_replacement = '''    # 2018-2026 全周期真实净值推演曲线 (同屏对标自选基准)
    st.markdown("#### 🚀 全周期净值曲线")

    if choice_kind == "ledger":
        safe_markdown_html("""
        <div style="background: rgba(245, 158, 11, 0.08); border-left: 3px solid var(--accent-primary); padding: 8px 14px; border-radius: 6px; margin-bottom: 12px; font-size: 12px; color: var(--text-primary);">
            <b>⚠️ 当前持仓静态权重历史回溯（含历史后视镜权重效应，非滚动样本外实盘记录）</b><br>
            <span style="color: var(--text-secondary); font-size: 11px; line-height: 1.5;">
                本回测基于当前实盘持仓的静态配置权重，反向穿越回溯至 2018 年并进行每日再平衡推演。因当前持仓中包含了近几年涨幅领先的黄金或跨市场资产，存在已知的历史后视镜权重效应与幸存者偏差，不代表历史上按滚动策略真实运行的样本外业绩。
            </span>
        </div>
        """)
        tgl_compare_oos = st.toggle("🔄 同屏对比【全天候滚动样本外动态策略曲线】(C3 标杆)", value=False, key="tgl_compare_oos_dynamic")
    else:
        tgl_compare_oos = False

    fig_nav = go.Figure()

    if tgl_compare_oos:
        try:
            base_bt = StrategyBridge.get_backtest_nav_for_tier(tier="C3")
            fig_nav.add_trace(go.Scatter(
                x=base_bt['date'],
                y=base_bt['strategy_nav'],
                mode='lines',
                name='全天候滚动样本外动态策略 (C3)',
                line=dict(color='#8b5cf6', width=2.0, dash='dashdot')
            ))
        except Exception as e_oos:
            st.caption(f"（样本外基准加载: {e_oos}）")'''

    if tab3_target in code:
        code = code.replace(tab3_target, tab3_replacement, 1)
        print("Tab 3 patched successfully.")
    else:
        print("Tab 3 target not found or already patched.")

    # 2. Tab 4 top section merger & 6 sub-tabs
    # Locate from `def render_tab4_toolbox_content(pm: PortfolioManager, snapshot: Dict[str, Any]):`
    # down to `box_tab1, box_tab2, box_tab3 = st.tabs([`
    tab4_top_regex = r"def render_tab4_toolbox_content\(pm: PortfolioManager, snapshot: Dict\[str, Any\]\):.*?(?=\s+box_tab1, box_tab2, box_tab3 = st\.tabs\(\[)"
    
    tab4_top_replacement = '''def render_tab4_toolbox_content(pm: PortfolioManager, snapshot: Dict[str, Any]):
    mlm_inst = st.session_state.get("mlm") or (MultiLedgerManager.get_instance() if MultiLedgerManager else None)
    active_lid = st.session_state.get("active_ledger_id", "main_live")
    all_ledgers = mlm_inst.list_ledgers() if mlm_inst else []
    cur_meta = mlm_inst.get_ledger_meta(active_lid) if mlm_inst else {"name": "主实盘账本"}
    cur_pm = mlm_inst.get_pm(active_lid) if mlm_inst else pm

    tb_opts = []
    tb_opt_map = {}
    act_lbl = f"🟢 当前激活账本：【{cur_meta.get('name', '主实盘账本')}】({len(cur_pm.holdings)}只 · ¥{cur_pm.total_equity:,.0f})"
    tb_opts.append(act_lbl)
    tb_opt_map[act_lbl] = ("ledger", active_lid)

    for l in all_ledgers:
        if l["id"] != active_lid:
            try:
                l_pm = mlm_inst.get_pm(l["id"])
                lbl = f"📒 独立账本：【{l['name']}】({len(l_pm.holdings)}只 · ¥{l_pm.total_equity:,.0f})"
                tb_opts.append(lbl)
                tb_opt_map[lbl] = ("ledger", l["id"])
            except Exception:
                pass

    t1_sim_c = st.session_state.get("tab1_sim_cache") or {}
    t1_w = dict(st.session_state.get("selected_backtest_weights") or t1_sim_c.get("optimal_weights", {}))
    has_t1 = bool(t1_w)
    if has_t1:
        lbl_t1 = f"🌱 Tab 1 最新建仓方案 ({len(t1_w)} 只标的)"
        tb_opts.append(lbl_t1)
        tb_opt_map[lbl_t1] = ("plan_t1", t1_w)

    rebal_w = dict(st.session_state.get("selected_secondary_weights") or snapshot.get("target_weights_funds", {}))
    if not rebal_w:
        rebal_w = {"005561": 0.30, "100032": 0.25, "000216": 0.20, "518880": 0.15, "011613": 0.10}
    if snapshot.get("target_weights_funds"):
        lbl_t2 = f"⚖️ Tab 2 拟调仓目标组合 ({len(rebal_w)} 只标的)"
        tb_opts.append(lbl_t2)
        tb_opt_map[lbl_t2] = ("plan_t2", rebal_w)

    col_top_sel, col_top_badges = st.columns([3.8, 6.2])
    with col_top_sel:
        def_tb_obj = st.session_state.get("tab4_selected_target", act_lbl)
        def_tb_idx = tb_opts.index(def_tb_obj) if def_tb_obj in tb_opts else 0
        sel_tb_target = st.selectbox(
            "📂 选择穿透体检组合对象：",
            tb_opts,
            index=def_tb_idx,
            key="sel_tab4_target_type"
        )
        st.session_state.tab4_selected_target = sel_tb_target

    tb_kind, tb_val = tb_opt_map.get(sel_tb_target, ("ledger", active_lid))
    active_examine_holdings = {}
    total_examine_equity = 0.0
    from portfolio_manager import HoldingItem

    if tb_kind == "ledger":
        l_id = tb_val
        t_pm = mlm_inst.get_pm(l_id) if mlm_inst else cur_pm
        m_info = mlm_inst.get_ledger_meta(l_id) if mlm_inst else cur_meta
        if t_pm.holdings:
            active_examine_holdings = dict(t_pm.holdings)
            total_examine_equity = sum(h.market_value for h in t_pm.holdings.values()) + t_pm.available_cash + t_pm.in_transit_cash
        else:
            st.info(f"💡 账本【{m_info.get('name', l_id)}】持仓为空，已自动选用精选基线组合进行全景穿透体检。")
            t1_w_def = {"005561": 0.35, "100032": 0.20, "000216": 0.20, "017436": 0.15, "011613": 0.10}
            base_cap = float(st.session_state.get("plan_capital", 100000.0))
            for fc, w in t1_w_def.items():
                m_val = round(base_cap * w, 2)
                fn = resolve_fund_display_name(fc, t_pm)
                active_examine_holdings[fc] = HoldingItem(fund_code=fc, fund_name=fn, shares=m_val, cost_nav=1.0, current_nav=1.0)
            total_examine_equity = base_cap

    elif tb_kind == "plan_t1":
        t1_w = tb_val
        base_cap = float(st.session_state.get("plan_capital", 100000.0))
        for fc, w in t1_w.items():
            m_val = round(base_cap * w, 2)
            fn = resolve_fund_display_name(fc, cur_pm)
            active_examine_holdings[fc] = HoldingItem(fund_code=fc, fund_name=fn, shares=m_val, cost_nav=1.0, current_nav=1.0)
        total_examine_equity = base_cap

    else: # plan_t2
        rebal_w = tb_val
        base_cap = sum(h.market_value for h in cur_pm.holdings.values()) if cur_pm.holdings else 100000.0
        for fc, w in rebal_w.items():
            m_val = round(base_cap * w, 2)
            fn = resolve_fund_display_name(fc, cur_pm)
            active_examine_holdings[fc] = HoldingItem(fund_code=fc, fund_name=fn, shares=m_val, cost_nav=1.0, current_nav=1.0)
        total_examine_equity = base_cap

    with col_top_badges:
        tb_badges = []
        for fc, h in active_examine_holdings.items():
            w_pct = (h.market_value / total_examine_equity * 100.0) if total_examine_equity > 0 else 0.0
            fcls = pm.classify_fund_asset_class(fc, h.fund_name)
            tb_badges.append(
                f'<span style="display:inline-block; background:var(--bg-elevated); border:1px solid var(--border-subtle); '
                f'border-radius:4px; padding:1px 6px; margin:2px 3px; font-size:11px; color:var(--text-primary); white-space:nowrap;">'
                f'<b>{h.fund_name}</b> <code style="color:var(--text-muted); font-size:10px;">{fc}</code> '
                f'<span style="color:var(--accent-primary); font-weight:700;">{w_pct:.1f}%</span> '
                f'<span style="background:var(--bg-canvas); border-radius:3px; padding:0 3px; font-size:9.5px; color:var(--text-secondary);">{fcls}</span>'
                f'</span>'
            )

        safe_markdown_html(f"""
        <div style="background:var(--bg-surface); border:1px solid var(--border-subtle); border-radius:8px; padding:6px 10px; margin-bottom:8px; box-shadow:var(--shadow-card);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:3px;">
                <span style="font-size:11.5px; font-weight:700; color:var(--text-primary);">📋 成分档案 · 共 {len(active_examine_holdings)} 只标的</span>
                <span style="font-size:11px; color:var(--text-secondary);">折算总资产: <b>¥{total_examine_equity:,.0f}</b></span>
            </div>
            <div style="display:flex; flex-wrap:wrap; align-items:center; max-height:48px; overflow-y:auto; line-height:1.5;">{"".join(tb_badges)}</div>
        </div>
        """)

    # ── 响应首屏主动风险哨联动穿透横幅 ──
    hl_mod = st.session_state.get("tab4_highlight_module")
    if hl_mod:
        hl_title = st.session_state.get("tab4_highlight_title", "主动风险预警")
        hl_code = st.session_state.get("tab4_highlight_fund", "")
        safe_markdown_html(f"""
        <div style="background: rgba(239, 68, 68, 0.08); border-left: 4px solid var(--color-up); padding: 10px 14px; border-radius: 6px; margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: 700; color: var(--color-up); font-size: 13px;">🚨 响应首屏主动风险哨联动证据链：{hl_title}</span>
                <span style="font-size: 11px; color: var(--text-secondary);">标的代码: {hl_code or '全组合'}</span>
            </div>
            <div style="font-size: 11.5px; color: var(--text-primary); margin-top: 4px;">
                系统已为您在下方穿透对应底层持仓与风险证据链。完成排查后，建议返回【💼 持仓调仓】主流程实施调仓处置。
            </div>
        </div>
        """)

    total_cur_equity = total_examine_equity
'''

    if re.search(tab4_top_regex, code, flags=re.DOTALL):
        code = re.sub(tab4_top_regex, tab4_top_replacement, code, count=1, flags=re.DOTALL)
        print("Tab 4 top section patched successfully.")
    else:
        print("Tab 4 top regex did not match.")

    # 3. Tab 4 tab list replacement
    old_tabs_stmt = '''    box_tab1, box_tab2, box_tab3 = st.tabs([
        "📊 资产穿透",
        "💡 A/C算费",
        "📡 ETF溢价"
    ])'''

    new_tabs_stmt = '''    box_tab1, box_tab2, box_tab3, box_tab4, box_tab5, box_tab6 = st.tabs([
        "📊 资产穿透与排雷",
        "🌡️ 14赛道温度计",
        "⚡ 尾盘折溢价套利",
        "🛡️ 期权防暴跌哨",
        "🌐 跨境QDII与锁汇",
        "💡 A/C端选型算费"
    ])'''

    if old_tabs_stmt in code:
        code = code.replace(old_tabs_stmt, new_tabs_stmt, 1)
        print("Tab 4 st.tabs statement replaced successfully.")
    else:
        print("Tab 4 st.tabs statement not found.")

    # 4. Tab 4 bottom modules replacement (old box_tab2 and box_tab3)
    old_bottom_pattern = r"    # A/C 份额盈亏平衡计算器 \(使用 @st\.fragment 实现局部无感刷新\)\s+with box_tab2:.*?with box_tab3:.*?st\.success\(\"✅ 所有核心监控场内 ETF 溢价率均处于正常安全范围 \(<= 0\.8%\)\。\"\)\s+"

    new_bottom_content = '''    # Sub-tab 2: 14 大赛道量化温度计总表
    with box_tab2:
        st.markdown("#### 🌡️ 全市场 14 大赛道量化温度计总表")
        st.caption("📈 14 大赛道真实估值分位、趋势信噪比、20日乖离率与拥挤度全息总表（顺应阅读流向下展开，随时可合上）")
        radar_cache_file = Path(WORKSPACE_ROOT) / "data" / "cache" / "radar_sectors_cache.json"
        sectors_data = []
        if radar_cache_file.exists():
            try:
                with open(radar_cache_file, "r", encoding="utf-8") as f:
                    c_json = json.load(f)
                    sectors_data = c_json.get("sectors", [])
            except Exception:
                pass
        if not sectors_data:
            try:
                from advisory_engine import OpportunityRadarEngine
                radar_engine = OpportunityRadarEngine()
                sectors_data = radar_engine.scan_all_sectors()
            except Exception:
                sectors_data = []
        df_rows = []
        for s in sectors_data:
            f_info = s.get("fund", {})
            df_rows.append({
                "赛道名称": s.get("name", ""),
                "估值分位": f"{s.get('val_percentile', 50.0):.1f}%",
                "趋势信噪比": f"{s.get('er_20', 0.5):.2f}",
                "20日乖离率": f"{s.get('bias_20', 0.0):+.1f}%",
                "拥挤度评分": f"{s.get('s_crowd', 85.0):.1f}",
                "综合得分": f"{s.get('total_score', 50.0):.1f}",
                "状态标签": s.get("tag", "📈 稳健蓄势"),
                "优选基金": f"{f_info.get('name', '')} ({f_info.get('code', '')})",
            })
        if df_rows:
            df_thermometer = pd.DataFrame(df_rows)
            st.dataframe(df_thermometer, use_container_width=True, hide_index=True)
        else:
            st.info("赛道温度计数据暂不可用。")

    # Sub-tab 3: 场内ETF与场外联接 14:45 尾盘折溢价套利感知 + 核心场内 ETF 溢价预警哨
    with box_tab3:
        st.markdown("#### ⚡ 场内ETF与场外联接 14:45 尾盘折溢价套利感知")
        st.caption("🧭 毫秒级监测场内核心 ETF（黄金/沪深300/科创50/芯片/标普500/恒生科技）市价与实时 IOPV。溢价 > +1.0% 提示场外低成本申购，折价 < -1.0% 提示场内折价低吸。")
        try:
            arb_sensors = DataLoader.fetch_etf_feeder_arbitrage_sensors(use_cache=True)
            arb_rows = []
            for item in arb_sensors:
                sig = item.get("signal", "NEUTRAL")
                sig_badge = "🚨 溢价申购联接" if sig == "PREMIUM_BUY_FEEDER" else ("💎 折价场内低吸" if sig == "DISCOUNT_BUY_ETF" else "⚪ 处于平价区间")
                arb_rows.append({
                    "对冲套利对": f"{item.get('name', '')} ({item.get('etf_code')}/{item.get('feeder_code')})",
                    "场内市价": f"{item.get('etf_price', 0.0):.4f}",
                    "参考净值(IOPV)": f"{item.get('etf_iopv', 0.0):.4f}",
                    "折溢价率": f"{item.get('discount_premium_pct', 0.0):+.2f}%",
                    "套利信号": sig_badge,
                    "实操建议": item.get("action_advice", "暂无"),
                })
            if arb_rows:
                df_arb = pd.DataFrame(arb_rows)
                st.dataframe(df_arb, use_container_width=True, hide_index=True)
        except Exception as e_arb:
            st.caption(f"（折溢价套利感知初始化: {e_arb}）")

        st.markdown("---")
        st.markdown("##### 📡 核心场内 ETF 溢价预警哨")
        st.caption("实时监控场内核心 ETF 折溢价率，溢价率 >0.8% 时严格预警防范高位追高回撤风险：")
        etf_alerts = pm.check_etf_premiums()
        if etf_alerts:
            st.warning(f"⚠️ 当前检测到 **{len(etf_alerts)}** 只场内 ETF 溢价率超出 0.8% 风控红线：")
            etf_rows = []
            for ea in etf_alerts:
                etf_rows.append({
                    "ETF代码": ea["code"],
                    "ETF名称": ea["name"],
                    "场内现价(元)": ea["price"],
                    "IOPV估值(元)": ea["iopv"],
                    "溢价率(%)": ea["premium_pct"],
                    "风险等级": "高溢价预警",
                    "操作建议": "溢价率>0.8%已超出安全红线，严禁盲目追高，谨防价格向净值回归造成损失。"
                })
            st.dataframe(pd.DataFrame(etf_rows), use_container_width=True, hide_index=True)
        else:
            st.success("✅ 所有核心监控场内 ETF 溢价率均处于正常安全范围 (<= 0.8%)。")

    # Sub-tab 4: 50ETF与300ETF认沽期权隐含波动率防暴跌哨
    with box_tab4:
        st.markdown("#### 🛡️ 50ETF与300ETF认沽期权隐含波动率防暴跌哨")
        st.caption("🔍 实时监测 50ETF 与 300ETF 近月平值认沽期权 IV 与 20日 HV 偏离度。当 IV 相对 HV 突升超 30% 且跌破 MA20 时输出市场剧烈防暴跌预警，并建议在组合中增加纯债防护仓位。")
        try:
            if "opt_sensors_gui_cache" not in st.session_state:
                st.session_state["opt_sensors_gui_cache"] = DataLoader.fetch_options_implied_volatility_sensors(use_cache=True)
            opt_sensors_gui = st.session_state["opt_sensors_gui_cache"]
            opt_rows = []
            for s in opt_sensors_gui:
                opt_rows.append({
                    "期权标的": f"{s.get('option_symbol')} ({s.get('underlying_code')})",
                    "期权类型": "认沽(PUT)",
                    "隐含波动率(IV)": f"{s.get('iv_pct', 0.0):.2f}%",
                    "历史波动率(HV)": f"{s.get('hv_pct', 0.0):.2f}%",
                    "IV/HV偏离度": f"{s.get('iv_hv_spread_pct', 0.0):+.1f}%",
                    "均线状态": "跌破MA20 ⚠️" if s.get("is_below_ma20") else "站上MA20 🟢",
                    "状态信号": s.get("signal_badge", "🟢 隐波平稳"),
                    "实操建议": s.get("action_advice", ""),
                })
            if opt_rows:
                st.dataframe(pd.DataFrame(opt_rows), use_container_width=True, hide_index=True)
        except Exception as e_opt_gui:
            st.caption(f"（期权波动率哨加载提示: {e_opt_gui}）")

    # Sub-tab 5: 跨境QDII溢价与外汇期货锁汇成本套利精算
    with box_tab5:
        st.markdown("#### 🌐 跨境QDII溢价与外汇期货锁汇成本套利精算")
        st.caption("结合离岸人民币 (USD/CNH) 远期掉期点 (Forward Swap Points) 测算锁汇避险成本，评估跨市场汇率锁汇套利可行性与真实到手收益增厚。")
        try:
            from portfolio_manager import PortfolioManager
            if "qdii_eval_gui_cache" not in st.session_state:
                st.session_state["qdii_eval_gui_cache"] = PortfolioManager.evaluate_all_qdii_fx_arbitrage()
            qdii_eval = st.session_state["qdii_eval_gui_cache"]
            qdii_rows = []
            for q in qdii_eval.get("results", []):
                qdii_rows.append({
                    "标的": f"{q.get('fund_name')} ({q.get('fund_code')})",
                    "资产类别": q.get("asset_category", ""),
                    "跨境溢价率": f"{q.get('qdii_premium_pct', 0.0):+.2f}%",
                    "年化锁汇成本": f"{q.get('annualized_hedging_cost_pct', 0.0):.2f}%",
                    "真实到手增厚": f"{q.get('net_yield_enhancement_bps', 0.0):+.1f} bps",
                    "套利可行性": q.get("signal_badge", ""),
                    "操作建议": q.get("recommendation", ""),
                })
            if qdii_rows:
                st.dataframe(pd.DataFrame(qdii_rows), use_container_width=True, hide_index=True)
        except Exception as e_qdii_gui:
            st.caption(f"（跨境锁汇套利精算加载提示: {e_qdii_gui}）")

    # Sub-tab 6: A/C 份额盈亏平衡计算器 (使用 @st.fragment 实现局部无感刷新)
    with box_tab6:
        st.markdown("#### 💡 A/C 份额费率与盈亏平衡精算")
        _frag_dec = getattr(st, "fragment", lambda f: f)

        @_frag_dec
        def _render_ac_fee_calculator():
            c_ac1, c_ac2, c_ac3, c_ac4 = st.columns(4)
            with c_ac1:
                r_sub = st.number_input("A 类前端申购费率 (折后 %)", value=0.15, step=0.01, key="ac_r_sub")
            with c_ac2:
                r_sales = st.number_input("C 类年化销售服务费率 (%)", value=0.40, step=0.05, key="ac_r_sales")
            with c_ac3:
                v_amt = st.number_input("拟投资金额 (元)", value=50000.0, step=5000.0, key="ac_v_amt")
            with c_ac4:
                v_days = st.number_input("预计持有周期 (天)", value=90, min_value=1, max_value=730, step=5, key="ac_v_days")

            calc = getattr(pm, "calculator", pm)
            calc_res = calc.calculate_break_even_days(
                standard_sub_rate=r_sub / 10.0 / 100.0,
                discount=10.0,
                sales_service_annual_rate=r_sales / 100.0,
                max_days=365,
                target_holding_days=int(v_days),
                investment_amount=float(v_amt)
            )
            st.success(f"⚖️ **精算测算结论**：A 类与 C 类的费率盈亏平衡天数为 **{calc_res['break_even_day']} 天**。")
            if calc_res.get("target_recommendation"):
                st.info(f"🎯 **选型建议**：{calc_res['target_recommendation']['summary']}")

        _render_ac_fee_calculator()
'''

    if re.search(old_bottom_pattern, code, flags=re.DOTALL):
        code = re.sub(old_bottom_pattern, new_bottom_content + "\n", code, count=1, flags=re.DOTALL)
        print("Tab 4 bottom sub-tabs patched successfully.")
    else:
        print("Tab 4 bottom regex did not match.")

    target.write_text(code, encoding="utf-8")
    print("app_gui.py written successfully.")

if __name__ == "__main__":
    patch_app_gui()
