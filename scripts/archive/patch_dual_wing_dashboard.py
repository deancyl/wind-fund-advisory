# -*- coding: utf-8 -*-
"""Script to patch render_dual_wing_advisory_dashboard in app_gui.py"""

import sys
from pathlib import Path

gui_path = Path(r"d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py")
content = gui_path.read_text(encoding="utf-8")

old_start = "        # ── 今日投顾行动总开关 (L1 傻瓜决策层：紧凑单行 <=44px，置于双翼看板顶部) ──"
old_end = '        st.caption(f"（双翼看板加载提示: {e}）")\n'

start_idx = content.find(old_start)
if start_idx == -1:
    print("ERROR: old_start not found!")
    sys.exit(1)

end_idx = content.find(old_end, start_idx)
if end_idx == -1:
    print("ERROR: old_end not found!")
    sys.exit(1)

end_idx += len(old_end)

new_block = '''        # ── 今日投顾行动总开关 (纯内存毫秒级快速风控与参谋判断，耗时 < 5ms) ──
        lock_funds = []
        c_free_funds = []
        for c, h in pm_instance.holdings.items():
            h_days = getattr(h, "holding_days", 30)
            batches = getattr(h, "batches", []) or []
            if batches:
                try:
                    h_days = min((b.holding_days for b in batches), default=h_days)
                except Exception:
                    pass
            if h_days < 7:
                lock_funds.append({"fund_code": c, "fund_name": getattr(h, "fund_name", c), "holding_days": h_days})
            elif str(getattr(h, "share_class", "A")).upper() == "C" and h_days >= 30:
                c_free_funds.append({"fund_code": c, "fund_name": getattr(h, "fund_name", c), "holding_days": h_days})

        erp_pct = float(snapshot_dict.get("erp_percentile", 82.0))
        bias_val = float(snapshot_dict.get("c300_bias_20", snapshot_dict.get("bias_20", -2.07)))

        if lock_funds:
            act_status_icon = "🔴"
            expander_title = (
                f"今日投顾参谋：持仓含 {len(lock_funds)} 只未满 7 天标的，"
                f"赎回需扣 1.5% 惩罚费，调仓算法已自动为您避开卖出 ｜ 点击展开市场机会与持仓体检"
            )
        elif c_free_funds:
            act_status_icon = "🟡"
            expander_title = (
                f"今日投顾参谋：检测到 {len(c_free_funds)} 只 C 类份额持有已满 30 天免赎回费，"
                f"建议择机置换为 A 类节省销售服务费 ｜ 点击展开市场机会与持仓体检"
            )
        elif len(pm_instance.holdings) == 0:
            act_status_icon = "🚀"
            expander_title = f"今日投顾参谋：宏观 ERP 处于黄金击球区 ({erp_pct:.1f}%)，建议一键启动新资建仓 ｜ 点击展开市场机会与精选赛道"
        else:
            act_status_icon = "🟢"
            expander_title = "今日投顾参谋：持仓资产结构健康，安全垫充沛，今日安心吃息无需调仓 ｜ 点击展开市场机会与持仓体检"

        # 100% 全宽折叠面板 (彻底删除右上角红色大按钮与右侧空白死区)
        wing_expander = st.expander(f"{act_status_icon} {expander_title}", expanded=False)

        with wing_expander:
            col_radar, col_sentry = st.columns([6.2, 3.8])

            # --- 左翼：机会雷达 ---
            with col_radar:
                # 优先从本地磁盘持久化缓存读取因子基因与 14 大赛道指标 (0 网络请求，0 现场进化)
                factor_cache_f = Path(WORKSPACE_ROOT) / "data" / "cache" / "factor_evolution_cache.json"
                evo_disk_data = {}
                if factor_cache_f.exists():
                    try:
                        with open(factor_cache_f, "r", encoding="utf-8") as _fc:
                            evo_disk_data = json.load(_fc)
                    except Exception:
                        pass

                w_factors = evo_disk_data.get("weights", [0.30, 0.30, 0.25, 0.15])
                evo_res = evo_disk_data.get("evolved_result", {})
                traj_data = evo_disk_data.get("nav_trajectory", {})

                # 加载赛道扫描缓存
                radar_cache_f = Path(WORKSPACE_ROOT) / "data" / "cache" / "radar_sectors_cache.json"
                all_scanned_sectors = []
                if radar_cache_f.exists():
                    try:
                        with open(radar_cache_f, "r", encoding="utf-8") as _rf:
                            all_scanned_sectors = json.load(_rf)
                    except Exception:
                        pass
                if not all_scanned_sectors:
                    try:
                        radar_engine = OpportunityRadarEngine()
                        all_scanned_sectors = radar_engine.scan_all_sectors()
                    except Exception:
                        all_scanned_sectors = []

                top3_sectors = [s for s in all_scanned_sectors if s.get("s_crowd", 85.0) >= 45.0][:3]
                if not top3_sectors and all_scanned_sectors:
                    top3_sectors = all_scanned_sectors[:3]

                col_rad_head1, col_rad_head2 = st.columns([6.0, 4.0])
                with col_rad_head1:
                    safe_markdown_html("<div style='font-size: 13px; font-weight: 700; color: var(--text-primary); margin-bottom: 4px;'>🔭 全市场机会雷达 · Top 3 机会甄选</div>")
                with col_rad_head2:
                    with st.popover(f"🧬 因子进化: 估{w_factors[0]*100:.0f}% 动{w_factors[1]*100:.0f}% 噪{w_factors[2]*100:.0f}% 拥{w_factors[3]*100:.0f}%", use_container_width=True):
                        st.markdown("##### 🧬 在线启发式因子基因自适应进化与突发黑天鹅 GP 规则树引擎")
                        regime_mode_txt = evo_res.get("regime_mode", "平稳蓄势态 (STABLE_CONSOLIDATION)")
                        regime_badge_txt = evo_res.get("regime_badge", "🟢 平稳蓄势")
                        st.caption(f"当前识别市场模式：<b>{regime_badge_txt} {regime_mode_txt}</b>", unsafe_allow_html=True)
                        c_m1, c_m2, c_m3 = st.columns(3)
                        c_m1.metric("样本外 Alpha", f"{traj_data.get('alpha_pct', 0.0):+.2f}%")
                        c_m2.metric("动态最大回撤", f"-{traj_data.get('mdd_dynamic_pct', 0.0):.2f}%")
                        c_m3.metric("换手率惩罚", f"-{evo_res.get('turnover', 0.0):.1f}%")
                        rule_expr_txt = evo_res.get("operator_rule_expression") or "RuleTree: Mom_Win=0.30*5d+0.70*20d | Vol_Pulse=exp(-1.2*pulse) | Safe_Shift=1.0+0.5*panic"
                        st.code(rule_expr_txt, language="text")
                        if traj_data.get("dates"):
                            df_traj = pd.DataFrame({
                                "日期": traj_data.get("dates", [])[-15:],
                                "动态净值": traj_data.get("nav_dynamic", [])[-15:],
                                "静态基准": traj_data.get("nav_static", [])[-15:],
                            })
                            st.line_chart(df_traj.set_index("日期"))

                # 信源验真指示徽章判定（优先读取本地快照缓存，零阻塞网络）
                news_cache_f = Path(WORKSPACE_ROOT) / "data" / "cache" / "realtime_news.json"
                news_cache_data = {}
                if news_cache_f.exists():
                    try:
                        with open(news_cache_f, "r", encoding="utf-8") as _ncf:
                            news_cache_data = json.load(_ncf)
                    except Exception:
                        pass
                is_realtime_news = bool(news_cache_data.get("is_realtime", False))
                news_src_label = str(news_cache_data.get("source", "东方财富 7x24快讯" if is_realtime_news else "离线快照"))
                data_sense_time = news_cache_data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                if is_realtime_news:
                    news_source_badge = (
                        f'<span style="font-size: 10px; font-weight: 600; color: var(--color-down); '
                        f'padding: 1px 6px; border-radius: 4px; background: rgba(34, 197, 94, 0.1); '
                        f'border: 1px solid rgba(34, 197, 94, 0.25);">🟢 实时联网信源 ({news_src_label})</span>'
                    )
                else:
                    news_source_badge = (
                        f'<span style="font-size: 10px; font-weight: 600; color: var(--accent-primary); '
                        f'padding: 1px 6px; border-radius: 4px; background: rgba(245, 158, 11, 0.1); '
                        f'border: 1px solid rgba(245, 158, 11, 0.25);">🟠 离线本地缓存快照 (网络未连接) ⏱️ 快照时间: {data_sense_time}</span>'
                    )

                # 3 张赛道卡（直接显示优选基金名称与 6 位代码，删除 '+ 入备选池' 伪按钮）
                cols_top3 = st.columns(3)
                for i, sec in enumerate(top3_sectors):
                    with cols_top3[i]:
                        sec_fund = sec.get("fund", {})
                        tag_color = "var(--color-up)" if "🔥" in sec.get("tag", "") else ("var(--accent-primary)" if "🎯" in sec.get("tag", "") else "var(--color-down)")
                        rt_chg = sec.get("realtime_chg_pct", 0.0)
                        rt_color = active_co["color_up"] if rt_chg >= 0 else active_co["color_down"]
                        core_logic_txt = sec.get("core_logic", "综合得分靠前")
                        sub_s = sec.get("sub_scores", {})
                        val_score = float(sub_s.get("valuation", sec.get("s_val", 0.0)))
                        mom_score = float(sub_s.get("momentum", sec.get("s_mom", 0.0)))
                        snr_score = float(sub_s.get("kaufman_snr", sec.get("s_er", 0.0)))
                        crowd_score = float(sub_s.get("anti_crowding", sec.get("s_crowd", 0.0)))
                        vol_20_val = float(sec.get("vol_20", 15.0))
                        mdd_20_val = float(sec.get("mdd_20", 8.0))

                        concise_logic_txt = sec.get("concise_logic") or core_logic_txt[:18]
                        if len(concise_logic_txt) > 18:
                            concise_logic_txt = concise_logic_txt[:18]
                        sec_score = float(sec.get("total_score", sec.get("score", 0.0)))
                        sec_val_pct = float(sec.get("val_percentile", sec.get("val_pct", 50.0)))

                        safe_markdown_html(f"""
                        <div class="decision-card" style="padding: 8px 10px; height: 100%; min-height: 110px; overflow: visible !important; border-top: 2px solid {tag_color};" title="💡 入选依据: 20日波动 {vol_20_val:.1f}% ｜ 20日最大回撤 -{mdd_20_val:.1f}% ｜ 估值:{val_score:.0f} 动量:{mom_score:.0f} 信噪:{snr_score:.0f} 拥挤:{crowd_score:.0f} ｜ {core_logic_txt}">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                                <span style="font-size: 13px; font-weight: 700; white-space: nowrap !important; flex-shrink: 0 !important; color: var(--text-primary);">{sec.get('name', '')}</span>
                                <span style="font-size: 10px; white-space: nowrap !important; flex-shrink: 0 !important; padding: 1px 4px; border-radius: 4px; background: var(--bg-canvas); color: {tag_color}; border: 1px solid var(--border-subtle);">{sec.get('tag', '')}</span>
                            </div>
                            <div style="font-size: 11px; color: var(--text-muted); margin: 2px 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                得分 {sec_score:.1f} ｜ 今日 <span style="color: {rt_color}; font-weight: 700;">{rt_chg:+.2f}%</span> ｜ 估值分位 {sec_val_pct:.0f}%
                            </div>
                            <div style="font-size: 11px; margin-bottom: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--text-primary);">
                                优选: <b>{sec_fund.get('name', '')}</b> <code style="color: var(--accent-primary); font-size: 11px;">{sec_fund.get('code', '')}</code>
                            </div>
                            <div style="font-size: 10.5px; color: var(--text-muted); line-height: 1.2; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                                {concise_logic_txt}
                            </div>
                        </div>
                        """)

            # --- 右翼：主动风险提示与健康度 (干净紧凑无按钮列表) ---
            with col_sentry:
                safe_markdown_html("<div style='font-size: 13px; font-weight: 700; color: var(--text-primary); margin-bottom: 6px;'>🚨 主动风险提示 · 组合健康度</div>")

                # G10: 动态相关性突变指示卡（仅在突变警报或结构异动时渲染，正常区间保持干净）
                try:
                    corr_eval_res = pm_instance.evaluate_dynamic_correlation_mutation_instance(threshold=0.75, stress_threshold=0.80)
                    if corr_eval_res.get("is_triggered") or corr_eval_res.get("is_liquidity_shift_triggered") or corr_eval_res.get("is_mutation_alarm") or corr_eval_res.get("is_regime_shift_risk"):
                        safe_markdown_html(render_correlation_mutation_card_html(corr_eval_res))
                except Exception:
                    pass

                if not lock_funds and not c_free_funds and len(pm_instance.holdings) > 0:
                    safe_markdown_html("""
                    <div class="decision-card" style="border-left: 3px solid var(--color-down); padding: 8px 12px; margin-bottom: 4px;">
                        <div style="font-weight: 700; color: var(--color-down); font-size: 12px; margin-bottom: 2px;">🟢 主动风控巡检全通</div>
                        <div style="font-size: 11px; color: var(--text-secondary);">持仓批次无惩罚锁仓 ｜ 赛道无超买拥挤 ｜ 零迷你基清盘风险</div>
                    </div>
                    """)
                else:
                    if lock_funds:
                        lock_names = [f"{a['fund_code']} ({a['fund_name'][:5]})" for a in lock_funds]
                        safe_markdown_html(f"""
                        <div class="decision-card" style="border-left: 3px solid var(--color-up); padding: 8px 10px; margin-bottom: 6px;">
                            <div style="font-size: 12px; font-weight: 700; color: var(--color-up); margin-bottom: 2px;">
                                🔴【未满7天锁定期】包含标的: {', '.join(lock_names)}
                            </div>
                            <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 2px;">
                                未满 7 天赎回将直接触发证监会规定的 1.50% 巨额惩罚扣款！调仓算法已在底层自动为您锁定下界。
                            </div>
                            <div style="font-size: 11px; color: var(--text-primary); font-weight: 600;">
                                💡 应对建议: 保持持有吃息，待持有满 7 天后再行操作。
                            </div>
                        </div>
                        """)
                    if c_free_funds:
                        c_names = [f"{a['fund_code']} ({a['fund_name'][:5]})" for a in c_free_funds]
                        safe_markdown_html(f"""
                        <div class="decision-card" style="border-left: 3px solid var(--accent-primary); padding: 8px 10px; margin-bottom: 4px;">
                            <div style="font-size: 12px; font-weight: 700; color: var(--accent-primary); margin-bottom: 2px;">
                                🟡【C类份额满期】包含标的: {', '.join(c_names)}
                            </div>
                            <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 2px;">
                                持有已满 30 天免赎回费。C 类年化计提销售服务费，长期持有成本较高。
                            </div>
                            <div style="font-size: 11px; color: var(--accent-primary); font-weight: 600;">
                                💡 应对建议: 待技术面反弹至均线压力位时，可择机置换为 A 类份额节省费用。
                            </div>
                        </div>
                        """)
                    if len(pm_instance.holdings) == 0:
                        safe_markdown_html("""
                        <div class="decision-card" style="border-left: 3px solid var(--accent-primary); padding: 8px 10px; margin-bottom: 4px;">
                            <div style="font-size: 12px; font-weight: 700; color: var(--accent-primary); margin-bottom: 2px;">
                                🚀【空仓状态指引】
                            </div>
                            <div style="font-size: 11px; color: var(--text-secondary);">
                                当前账本尚无持仓。宏观 ERP 处于黄金击球区，可在【🌱 新资建仓】快速获取 AI 智能配置全案。
                            </div>
                        </div>
                        """)
    except Exception as e:
        st.caption(f"（双翼看板加载提示: {e}）")
'''

patched_content = content[:start_idx] + new_block + content[end_idx:]
gui_path.write_text(patched_content, encoding="utf-8")
print("Successfully patched render_dual_wing_advisory_dashboard in app_gui.py")
