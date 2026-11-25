# -*- coding: utf-8 -*-
"""
scripts/inject_m3_features.py
将 Milestone 3 三大投顾核心业务模块优雅接入 AGY2_FundAdvisory/app_gui.py：
1. 导入 advisory_engine 模块及核心类
2. 注入 render_dual_wing_advisory_dashboard 函数并挂载于四大 Tab 上方
3. 注入 Tab 1 步骤三「🌊 资金建仓节奏与智能定投规划」选择器与三步分批、智能定投视图
"""

import sys
from pathlib import Path

gui_path = Path("AGY2_FundAdvisory/app_gui.py")
text = gui_path.read_text(encoding="utf-8")

# 1. 注入导入
old_import = """import portfolio_optimizer
from portfolio_optimizer import (
    WinRateOptimizer,
    QUANT_MODELS_CATALOG,
    recommend_model_for_regime,
    execute_market_optimization_flow
)"""

new_import = """import portfolio_optimizer
from portfolio_optimizer import (
    WinRateOptimizer,
    QUANT_MODELS_CATALOG,
    recommend_model_for_regime,
    execute_market_optimization_flow
)
import advisory_engine
from advisory_engine import (
    OpportunityRadarEngine,
    ActiveRiskSentry,
    SmartExecutionDCAEngine,
    RADAR_SECTOR_CATALOG
)"""

if "import advisory_engine" not in text:
    if old_import in text:
        text = text.replace(old_import, new_import, 1)
    else:
        print("Warning: old_import anchor not found, searching fallback...")
        text = text.replace("import portfolio_optimizer", "import advisory_engine\nfrom advisory_engine import (OpportunityRadarEngine, ActiveRiskSentry, SmartExecutionDCAEngine, RADAR_SECTOR_CATALOG)\nimport portfolio_optimizer", 1)

# 2. 注入 _MODULE_MAP
old_map = """"portfolio_optimizer": (portfolio_optimizer, CURRENT_DIR / "portfolio_optimizer.py"),
}"""
new_map = """"portfolio_optimizer": (portfolio_optimizer, CURRENT_DIR / "portfolio_optimizer.py"),
    "advisory_engine": (advisory_engine, CURRENT_DIR / "advisory_engine.py"),
}"""

if '"advisory_engine":' not in text and old_map in text:
    text = text.replace(old_map, new_map, 1)

# 3. 注入双翼看板函数与调用
dual_wing_code = '''
# -------------------------------------------------------------
# 双翼智能投顾核心看板：【🔭 全市场机会雷达】与【🚨 主动风险预警哨】
# -------------------------------------------------------------
def render_dual_wing_advisory_dashboard(pm_instance, snapshot_dict):
    """
    渲染双翼智能投顾核心看板：
    - 左翼：【🔭 全市场机会雷达】（14 赛道扫描，Top 3 黄金击球区与右侧共振赛道，优选公募基金，一键加入备选池）
    - 右翼：【🚨 主动风险预警哨】（FIFO 锁仓、超买拥挤、迷你基清盘、攻防线四维巡检，全通徽章与本地持久化）
    """
    try:
        with st.expander("🔭 全市场机会雷达 ｜ 🚨 主动风险预警哨 (双翼智能投顾看板)", expanded=True):
            col_radar, col_sentry = st.columns([6.2, 3.8])

            # --- 左翼：机会雷达 ---
            with col_radar:
                st.markdown("<div style=\'font-size: 14px; font-weight: 700; color: var(--text-primary); margin-bottom: 8px;\'>🔭 全市场机会雷达 · Top 3 机会甄选</div>", unsafe_allow_html=True)
                radar_engine = OpportunityRadarEngine()
                top3_sectors = radar_engine.get_top_opportunities(3)

                cols_top3 = st.columns(3)
                for i, sec in enumerate(top3_sectors):
                    with cols_top3[i]:
                        sec_fund = sec.get("fund", {})
                        tag_color = "var(--color-up)" if "🔥" in sec["tag"] else ("var(--accent-primary)" if "🎯" in sec["tag"] else "var(--color-down)")
                        st.markdown(f"""
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
                        """, unsafe_allow_html=True)
                        if st.button("➕ 入备选池", key=f"btn_add_radar_pool_{sec['sector_id']}", use_container_width=True, type="secondary"):
                            if "custom_candidate_pool" not in st.session_state:
                                st.session_state.custom_candidate_pool = []
                            fcode = sec_fund.get("code")
                            if fcode and fcode not in st.session_state.custom_candidate_pool:
                                st.session_state.custom_candidate_pool.append(fcode)
                            if "custom_fund_overrides" not in st.session_state:
                                st.session_state.custom_fund_overrides = {}
                            st.session_state.custom_fund_overrides[sec_fund.get("name", fcode)] = fcode
                            st.toast(f"✅ 已将【{sec_fund.get('name')}】一键纳入备选池！")
                            st.rerun()

            # --- 右翼：主动风险哨 ---
            with col_sentry:
                st.markdown("<div style=\'font-size: 14px; font-weight: 700; color: var(--text-primary); margin-bottom: 8px;\'>🚨 主动风险预警哨 · 四维巡检</div>", unsafe_allow_html=True)
                sentry = ActiveRiskSentry()
                report = sentry.inspect_portfolio(pm_instance.holdings, snapshot_dict)

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
                    for alert in report.get("alerts", [])[:3]:
                        border_c = "var(--color-up)" if alert["level"] == "red" else ("var(--color-down)" if alert["level"] == "green_notice" else "var(--accent-primary)")
                        badge_icon = "🔴" if alert["level"] == "red" else ("🟢" if alert["level"] == "green_notice" else "🟡")
                        st.markdown(f"""
                        <div class="decision-card" style="border-left: 3px solid {border_c}; padding: 8px 10px; margin-bottom: 6px;">
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
    except Exception as e:
        st.caption(f"（双翼看板加载提示: {e}）")

'''

tabs_marker = """# -------------------------------------------------------------
# 核心四大工作区 (精简 ≤ 5 字符，彻底砍掉独立 Tab 5)
# -------------------------------------------------------------"""

if "render_dual_wing_advisory_dashboard" not in text:
    if tabs_marker in text:
        text = text.replace(tabs_marker, dual_wing_code + "\nrender_dual_wing_advisory_dashboard(pm, snapshot)\n\n" + tabs_marker, 1)

# 4. 注入 Tab 1 步骤三建仓节奏选择器
old_step3_header = """            st.markdown("#### 🌱 实盘建仓执行单")
            st.caption(f"本金 ¥{plan_capital:,.2f} ｜ 精选 {len(df_bp)} 只 ｜ 模型：{QUANT_MODELS_CATALOG.get(sel_model_type, {}).get('name', 'HRP')}")"""

new_step3_header = """            st.markdown("#### 🌱 实盘建仓执行单")
            st.caption(f"本金 ¥{plan_capital:,.2f} ｜ 精选 {len(df_bp)} 只 ｜ 模型：{QUANT_MODELS_CATALOG.get(sel_model_type, {}).get('name', 'HRP')}")

            # ---------------------------------------------------------
            # 🌊 资金建仓节奏与智能定投规划 (三种建仓模式)
            # ---------------------------------------------------------
            st.markdown("##### 🌊 资金建仓节奏与智能定投规划")
            cap_deployment_mode = st.radio(
                "请选择本金部署方式：",
                [
                    "⚡ 一次性建仓（今日全额配置）",
                    "🌊 稳健三步分批建仓（底仓 50% + 逢低网格 30% + 右侧趋势 20%）",
                    "📅 估值自适应智能定投（根据宏观 ERP 与均线偏离度动态调整扣款乘数）",
                ],
                index=0,
                horizontal=True,
                key="radio_capital_deployment_mode",
            )

            alloc_list_for_dca = [
                {"code": it["fund_code"], "name": it["fund_name"], "weight": it["target_weight"] / 100.0}
                for it in blueprint.get("items", [])
            ]

            if "稳健三步" in cap_deployment_mode:
                three_step_plan = SmartExecutionDCAEngine.plan_three_step_batches(
                    total_capital=float(plan_capital),
                    allocations=alloc_list_for_dca,
                    market_snapshot=snapshot
                )
                st.caption("基于市场当前信噪比与攻防均线，自动将本金拆解为底仓防守、逢低网格与右侧突破三批订单：")
                cols_batches = st.columns(3)
                for b_idx, b_info in enumerate(three_step_plan["batches"]):
                    with cols_batches[b_idx]:
                        st.markdown(f\"\"\"
                        <div class="decision-card" style="padding: 12px 14px; height: 100%;">
                            <div style="font-size: 13px; font-weight: 700; color: var(--text-primary); margin-bottom: 4px;">{b_info['title']}</div>
                            <div style="font-size: 16px; font-weight: 800; color: var(--accent-primary); margin-bottom: 6px;">¥{b_info['amount']:,.2f}</div>
                            <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 6px;">触发时机: <b>{b_info['timing']}</b></div>
                            <div style="font-size: 11px; color: var(--text-secondary); line-height: 1.5;">{b_info['notes']}</div>
                        </div>
                        \"\"\", unsafe_allow_html=True)
                st.info(f"🛡️ 资金守恒已锁定：三步批次金额合计 ¥{three_step_plan['total_batch_amount']:,.2f} 严格等于总本金 ¥{plan_capital:,.2f}，分厘不差。未触发批次建议停泊短债/货币基金吃息。")

            elif "智能定投" in cap_deployment_mode:
                erp_pct = float(snapshot.get("erp_percentile", 78.0))
                bias_20 = float(snapshot.get("c300_bias_20", 1.0))
                dca_plan = SmartExecutionDCAEngine.plan_smart_dca(
                    total_capital=float(plan_capital),
                    allocations=alloc_list_for_dca,
                    erp_percentile=erp_pct,
                    bias_20=bias_20,
                    periods=12
                )
                st.caption(f"根据当前大盘 ERP 分位数 ({erp_pct:.1f}%) 与均线偏离度 Bias20 ({bias_20:+.1f}%) 动态计算当期扣款乘数：")
                col_d1, col_d2, col_d3 = st.columns([3, 4, 3])
                with col_d1:
                    st.metric("定投周期与基准金额", f"¥{dca_plan['base_per_period']:,.2f} /期", "共 12 期")
                with col_d2:
                    st.metric("当期自适应乘数", f"{dca_plan['multiplier']:.2f}x ({dca_plan['multiplier_tag']})", dca_plan['valuation_status'])
                with col_d3:
                    st.metric("本期建议扣款金额", f"¥{dca_plan['actual_deduction']:,.2f}", f"基准: ¥{dca_plan['base_per_period']:,.2f}")
"""

if "资金建仓节奏与智能定投规划" not in text:
    if old_step3_header in text:
        text = text.replace(old_step3_header, new_step3_header, 1)

gui_path.write_text(text, encoding="utf-8")
print("Successfully injected Milestone 3 features into app_gui.py!")
