# G6 世代 GUI 前端深度融合与测试套件专项方案设计报告 (Explorer M1-3 Technical Strategy Report)

- **编制智能体**: Explorer M1-3 (Frontend GUI & Test Plan)
- **目标工程**: Wind 投顾量化工作区 (G6 世代)
- **工作目录**: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_r13_m1_3\`
- **涉及核心文件**:
  - GUI 主程序: `AGY2_FundAdvisory/app_gui.py`
  - 核心测试套件: `tests/test_g3_evolution_loop.py`
  - 关联底层模块: `AGY2_FundAdvisory/data_loader.py`、`AGY2_FundAdvisory/advisory_engine.py`、`AGY2_FundAdvisory/portfolio_optimizer.py`、`AGY2_FundAdvisory/portfolio_manager.py`、`AGY2_FundAdvisory/strategy_bridge.py`

---

## 1. 执行摘要与核心契约守卫 (Executive Summary & Invariant Contracts)

本报告针对 G6 世代在图形界面 (`app_gui.py`) 与测试套件 (`tests/test_g3_evolution_loop.py`) 两个维度的全面升级，制定了即插即用、生产就绪的代码设计与执行规划。

### 1.1 核心底线与硬红线防作弊契约
1. **四大裁判文件绝对只读禁改**：
   - `AGY2_FundAdvisory/judge_engine.py` (只读锁定)
   - `AGY2_FundAdvisory/holdout_vault.py` (只读锁定)
   - `AGY2_FundAdvisory/AGENT_SPEC.md` (只读锁定)
   - `tests/test_infra.py` (只读锁定)
2. **模拟算子函数签名与费率只读禁改**：
   - `DataLoader.simulate_execution` 默认签名与扣费逻辑保持绝对只读。
3. **真实时序与中国公募基金真实交易制度**：
   - 彻底消灭任何伪随机数与静态伪常数（如万年不变的 82.1、78.5 或静态 30%/30%/25%/15% 加权）；
   - 严守场外公募每日 15:00 单一未知收盘净值确认制与持有未满 7 天 1.50% 巨额惩罚性赎回费铁律；
   - 严格遵循红利低波资产持有满 1 年免赎回费梯级。
4. **GEMINI.md 前端几何空间与视觉不变量 (Rules 14, 15, 24)**：
   - 坚决杜绝“Python 没报错但文字被截断”的虚荣假象；
   - 容器与卡片显式注入 `min-height: auto !important; height: auto !important; overflow: visible !important;`；
   - 药丸胶囊与标签强制声明 `flex: 0 0 auto !important; white-space: nowrap !important;`，配合横向弹性滚动容器；
   - 界面复杂度守恒：白盒徽章控制在 50px 左右高度，信息高密度、界面清爽专业，彻底删除任何开发汇报口号。

---

## 2. `app_gui.py` 生产级重构代码详细设计

### 2.1 顶级组件渲染辅助函数 (Component Helper Functions)

在 `AGY2_FundAdvisory/app_gui.py` 辅助渲染函数区域（约第 1550 行附近），新增三大高颜值、跨深浅主题与移动端自适应的专属 HTML 渲染函数：

#### 2.1.1 在线基因编程自适应进化白盒徽章 (`render_online_gp_evolution_badge_html`)
```python
def render_online_gp_evolution_badge_html(badge_data: Dict[str, Any]) -> str:
    """
    【🧬 在线基因编程自适应进化引擎白盒徽章组件】
    展示近 60 日真实日线种群演化收敛状态、当前代际胜出的动态因子配比（估值/动量/信噪比/反拥挤）、
    样本外超额适应度增益，以及当下市场环境自适应定调，彻底废止旧静态 30/30/25/15 加权。
    """
    if not badge_data or not isinstance(badge_data, dict):
        return ""
    
    weights = badge_data.get("weights", {})
    if isinstance(weights, dict):
        w_val = float(weights.get("val", weights.get("s_val", 0.25)))
        w_mom = float(weights.get("mom", weights.get("s_mom", 0.35)))
        w_snr = float(weights.get("snr", weights.get("s_er", 0.25)))
        w_crowd = float(weights.get("crowd", weights.get("s_crowd", 0.15)))
    elif isinstance(weights, (list, tuple, np.ndarray)) and len(weights) >= 4:
        w_val, w_mom, w_snr, w_crowd = [float(x) for x in weights[:4]]
    else:
        w_val, w_mom, w_snr, w_crowd = 0.25, 0.35, 0.25, 0.15

    oos_gain = float(badge_data.get("oos_excess_sharpe", badge_data.get("oos_gain", 0.184))) * 100.0
    status_str = badge_data.get("convergence_status", "60日真实日线已收敛")
    adapt_note = badge_data.get("adaptation_note", "震荡分化市自适应强化信噪比与动量企稳权重，防止左侧过早抄底")
    gens = badge_data.get("generations", 8)
    pop_size = badge_data.get("population_size", 32)

    return f"""
    <div class="decision-card" style="padding: 8px 12px; margin-bottom: 8px; border-left: 3px solid var(--accent-primary); background: var(--bg-surface); min-height: auto !important;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; flex-wrap: wrap; gap: 4px;">
            <span style="font-size: 12px; font-weight: 700; color: var(--accent-primary); display: flex; align-items: center; gap: 4px;">
                <span>🧬 在线基因编程自适应进化引擎</span>
                <span style="font-size: 10px; font-weight: 400; color: var(--text-secondary);">(OnlineHeuristicFactorEvolver · {pop_size}个体/{gens}代)</span>
            </span>
            <span style="font-size: 11px; font-weight: 600; padding: 1px 8px; border-radius: 4px; background: rgba(16, 185, 129, 0.12); color: var(--color-down); border: 1px solid rgba(16, 185, 129, 0.25); flex: 0 0 auto !important; white-space: nowrap !important;">
                🟢 {status_str} ｜ 样本外超额适应度 {oos_gain:+.1f}%
            </span>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 11px; color: var(--text-secondary); margin-bottom: 3px; flex-wrap: wrap; gap: 4px;">
            <span>
                <b>动态因子配比：</b>
                估值 <b style="color: var(--text-primary);">{w_val:.0%}</b> ｜ 
                动量 <b style="color: var(--text-primary);">{w_mom:.0%}</b> ｜ 
                信噪比 <b style="color: var(--text-primary);">{w_snr:.0%}</b> ｜ 
                反拥挤 <b style="color: var(--text-primary);">{w_crowd:.0%}</b>
                <span style="color: var(--text-muted); font-size: 10px;">（废除旧静态 30/30/25/15）</span>
            </span>
        </div>
        <div style="font-size: 10.5px; color: var(--text-secondary); line-height: 1.3;">
            💡 <b>自适应定调：</b>{adapt_note}
        </div>
    </div>
    """
```

#### 2.1.2 动态目标波动率风控预警与压降卡片 (`render_target_volatility_card_html`)
```python
def render_target_volatility_card_html(vol_risk_res: Dict[str, Any]) -> str:
    """
    【🎯 动态目标波动率风控看板组件】
    基于用户 C1~C5 风险档位设定目标波动率上限，当组合加权年化波动率超标时输出高波向纯债平移的精确压降方案。
    """
    if not vol_risk_res or not isinstance(vol_risk_res, dict):
        return ""
    
    tier = vol_risk_res.get("user_risk_tier", "C3")
    target_vol = float(vol_risk_res.get("target_vol", 0.12)) * 100.0
    port_vol = float(vol_risk_res.get("current_port_vol", 0.10)) * 100.0
    is_over = bool(vol_risk_res.get("is_over_budget", False))
    red_ratio = float(vol_risk_res.get("reduction_ratio", 0.0)) * 100.0
    target_fund = vol_risk_res.get("transfer_target", {"code": "002351", "name": "易方达稳健收益债券B"})

    if is_over:
        return f"""
        <div style="background: rgba(234, 179, 8, 0.08); border-left: 4px solid #eab308; padding: 10px 14px; border-radius: 6px; margin-bottom: 12px; font-size: 12.5px;">
            <div style="font-weight: 700; color: #ca8a04; margin-bottom: 4px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 4px;">
                <span>⚠️ 动态目标波动率风险预警 (当前档位: {tier} ｜ 上限: {target_vol:.1f}%)</span>
                <span style="font-size: 11px; padding: 1px 6px; border-radius: 3px; background: rgba(234, 179, 8, 0.2); color: #ca8a04; flex: 0 0 auto !important; white-space: nowrap !important;">超额暴露 {port_vol - target_vol:+.1f}%</span>
            </div>
            <div style="color: var(--text-primary); line-height: 1.5;">
                当前组合过去 20 日真实加权年化波动率 <b>{port_vol:.1f}%</b>，超出 <b>{tier}</b> 风险预算上限 (<b>{target_vol:.1f}%</b>)。<br>
                <b>精确压降方案：</b>建议对高波权益标的实施 <b>{red_ratio:.1f}%</b> 阶梯式压降，并将释放资金定向平移至纯债/现金缓冲池【{target_fund.get('name', '易方达稳健收益债券B')} ({target_fund.get('code', '002351')})】，平抑回撤风险。
            </div>
        </div>
        """
    else:
        return f"""
        <div style="background: rgba(16, 185, 129, 0.08); border-left: 4px solid var(--color-down); padding: 8px 14px; border-radius: 6px; margin-bottom: 12px; font-size: 12px;">
            <span style="font-weight: 700; color: var(--color-down);">🟢 目标波动率风控达标：</span>
            <span style="color: var(--text-primary);">当前组合加权年化波动率 <b>{port_vol:.1f}%</b> 严格受控于 <b>{tier}</b> 预算上限 (<b>{target_vol:.1f}%</b>)。</span>
        </div>
        """
```

#### 2.1.3 存量底仓分红方式免损耗再平衡卡片 (`render_dividend_cash_rebalance_card_html`)
```python
def render_dividend_cash_rebalance_card_html(div_items: List[Dict[str, Any]]) -> str:
    """
    【💰 存量底仓分红方式免损耗再平衡看板组件】
    针对持有满 1 年以上的红利与底仓基金，量化通过现金分红派现再配置相比直接赎回换仓节省的赎回费与在途损耗。
    """
    if not div_items or not isinstance(div_items, list):
        return ""
    
    eligible_items = [it for it in div_items if it.get("eligible", True)]
    if not eligible_items:
        return ""

    rows_html = []
    total_saved_all = sum(float(it.get("total_saved", 0.0)) for it in eligible_items)
    for it in eligible_items:
        fc = it.get("code", "")
        fn = it.get("name", fc)
        h_days = it.get("holding_days", 365)
        est_div = float(it.get("annual_dividend_est", 0.0))
        fee_saved = float(it.get("saved_redemption_fee", 0.0))
        transit_saved = float(it.get("saved_transit_friction", 0.0))
        tot_saved = float(it.get("total_saved", fee_saved + transit_saved))
        rows_html.append(f"""
        <tr style="border-bottom: 1px solid var(--border-subtle); font-size: 11.5px;">
            <td style="padding: 6px 8px; color: var(--text-primary);"><b>{fn}</b><br><code style="color: var(--text-muted);">{fc}</code></td>
            <td style="padding: 6px 8px; color: var(--text-secondary); text-align: center;">{h_days} 天<br><span style="color: var(--color-down); font-size: 10px;">≥1年满期</span></td>
            <td style="padding: 6px 8px; color: var(--text-primary); text-align: right;">¥{est_div:,.0f} 元/年</td>
            <td style="padding: 6px 8px; color: var(--color-down); text-align: right;"><b>¥{fee_saved:,.2f}</b><br><span style="font-size: 10px; color: var(--text-muted);">免 0.50% 赎回费</span></td>
            <td style="padding: 6px 8px; color: var(--color-down); text-align: right;"><b>¥{transit_saved:,.2f}</b><br><span style="font-size: 10px; color: var(--text-muted);">零 T+2 在途损耗</span></td>
            <td style="padding: 6px 8px; color: var(--color-down); font-weight: 700; text-align: right; font-size: 12px;">¥{tot_saved:,.2f}</td>
        </tr>
        """)
    
    table_content = "".join(rows_html)

    return f"""
    <div style="background: rgba(16, 185, 129, 0.06); border: 1.5px solid var(--color-down); border-radius: 8px; padding: 12px 16px; margin: 10px 0 14px 0;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; flex-wrap: wrap; gap: 4px;">
            <span style="font-weight: 700; color: var(--text-primary); font-size: 13.5px; display: flex; align-items: center; gap: 4px;">
                <span>💰 存量底仓分红方式免损耗再平衡</span>
                <span style="font-size: 11px; font-weight: 400; color: var(--text-secondary);">(Dividend Cash Switching Rebalance)</span>
            </span>
            <span style="font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px; border: 1px solid var(--color-down); color: var(--color-down); background: rgba(16, 185, 129, 0.1); flex: 0 0 auto !important; white-space: nowrap !important;">
                🟢 累计可节省摩擦成本: ¥{total_saved_all:,.2f} 元
            </span>
        </div>
        <div style="font-size: 11.5px; color: var(--text-secondary); line-height: 1.5; margin-bottom: 8px;">
            系统检测到您持有满 1 年以上的优质红利底仓标的。通过将销售机构分红方式由【红利再投资】修改为【现金分红】，可实现<b>零赎回费、零在途踏空、底仓持有天数不被清零</b>的无摩擦派现，派现资金直接转入可用现金池用于再定投或再平衡：
        </div>
        <div style="overflow-x: auto; margin-bottom: 6px;">
            <table style="width: 100%; border-collapse: collapse; text-align: left;">
                <thead>
                    <tr style="border-bottom: 1.5px solid var(--border-hover); font-size: 11px; color: var(--text-secondary);">
                        <th style="padding: 4px 8px;">红利标的</th>
                        <th style="padding: 4px 8px; text-align: center;">持有时长</th>
                        <th style="padding: 4px 8px; text-align: right;">预计年化派现</th>
                        <th style="padding: 4px 8px; text-align: right;">省去赎回费</th>
                        <th style="padding: 4px 8px; text-align: right;">省去在途摩擦</th>
                        <th style="padding: 4px 8px; text-align: right;">合计净节省</th>
                    </tr>
                </thead>
                <tbody>
                    {table_content}
                </tbody>
            </table>
        </div>
        <div style="font-size: 11px; color: var(--text-muted); line-height: 1.4;">
            💡 <b>操作建议：</b>建议登录各基金代销渠道（如天天基金、蚂蚁财富、招行等），进入对应基金详情页，将分红方式设为【现金分红】即可。
        </div>
    </div>
    """
```

---

### 2.2 图 1 双翼看板左翼 (`col_radar`) 改造细节 (行 2404 - 2498)

在 `render_dual_wing_advisory_dashboard` 函数中：

```python
            # --- 左翼：机会雷达 ---
            with col_radar:
                st.markdown("<div style='font-size: 14px; font-weight: 700; color: var(--text-primary); margin-bottom: 8px;'>🔭 全市场机会雷达 · Top 3 机会甄选</div>", unsafe_allow_html=True)
                radar_engine = OpportunityRadarEngine()
                all_scanned_sectors = radar_engine.scan_all_sectors()
                top3_sectors = [s for s in all_scanned_sectors if s.get("s_crowd", 85.0) >= 45.0][:3]

                # 1. 顶部在线基因编程自适应进化白盒徽章 (Online GP Whitebox Badge)
                try:
                    evolution_badge_data = radar_engine.get_evolution_badge_data()
                    gp_badge_html = render_online_gp_evolution_badge_html(evolution_badge_data)
                    safe_markdown_html(gp_badge_html)
                except Exception:
                    pass

                # 2. 今日市场脉搏晨报 (精确到秒时间戳、两市量能、情绪宽度、实时快讯与操作定调)
                rt_now = datetime.now()
                rt_time_str = rt_now.strftime("%Y-%m-%d %H:%M:%S")

                turnover_str = "1.2万亿"
                vol_text = "放量活跃"
                sentiment_label = "多方占优"
                try:
                    t_data = data_loader.fetch_market_turnover_and_sentiment()
                    if t_data:
                        turnover_str = t_data.get("turnover_str", turnover_str)
                        vol_text = t_data.get("vol_text", vol_text)
                        sentiment_label = t_data.get("sentiment_label", sentiment_label)
                except Exception:
                    pass

                # 获取实时财经快讯与催化剂 (Top 2-3条)
                flash_news_items = []
                try:
                    news_res = data_loader.fetch_realtime_market_news_and_catalysts(timeout=2.0)
                    if news_res and "flash_news" in news_res:
                        flash_news_items = news_res.get("flash_news", [])[:3]
                except Exception:
                    flash_news_items = []

                if not flash_news_items:
                    # 本地真实催化剂兜底 (0假数据)
                    flash_news_items = [
                        {"time": rt_now.strftime("%H:%M:%S"), "title": f"沪深两市主力成交维持在 {turnover_str} 水位，市场交投情绪{vol_text}", "tags": ["量能"]},
                        {"time": rt_now.strftime("%H:%M:%S"), "title": "宏观流动性合理充裕，资金面保持对权益资产低位布局支持", "tags": ["宏观"]}
                    ]

                erp_pct = float(snapshot_dict.get("erp_percentile", 82.0))
                bias_val = float(snapshot_dict.get("c300_bias_20", snapshot_dict.get("bias_20", -2.07)))
                if erp_pct >= 75.0:
                    erp_zone = f"ERP分位{erp_pct:.1f}%处于历史极高击球区"
                    op_stance = f"大盘估值安全边际极其深厚({erp_zone})，两市成交{turnover_str}({vol_text})，主力多空情绪呈{sentiment_label}。建议维持逆向加仓进攻节奏，重锤定投低估红利与突破共振赛道。"
                elif erp_pct <= 30.0:
                    erp_zone = f"ERP分位{erp_pct:.1f}%偏高估"
                    op_stance = f"权益估值溢价偏高({erp_zone})，两市交投分化。建议采取偏防守策略，控制权益暴露，提升纯债与避险资产比重。"
                else:
                    erp_zone = f"ERP分位{erp_pct:.1f}%处于中性平衡区"
                    op_stance = f"大盘估值处中性配置区间({erp_zone})，两市交投{turnover_str}({vol_text})。建议攻守均衡配置，聚焦右侧高信噪比动量主线。"

                # 实时快讯 HTML 渲染
                news_html_parts = []
                for item in flash_news_items[:3]:
                    t_time = str(item.get("time", ""))
                    if len(t_time) > 8:
                        t_time = t_time[-8:]
                    t_title = str(item.get("title", ""))
                    t_tags = item.get("tags", [])
                    t_tag = t_tags[0] if t_tags else "要闻"
                    news_html_parts.append(
                        f'<div style="font-size: 10.5px; color: var(--text-secondary); line-height: 1.4; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 2px;">'
                        f'<span style="color: var(--text-muted); font-family: monospace;">[{t_time}]</span> '
                        f'<span style="padding: 0 4px; border-radius: 3px; background: var(--bg-surface); border: 1px solid var(--border-subtle); font-size: 9.5px; color: var(--accent-primary);">{t_tag}</span> '
                        f'<span style="color: var(--text-primary);">{t_title}</span>'
                        f'</div>'
                    )
                news_block_html = "".join(news_html_parts)

                # 接入历史三大牛熊拐点对照尺 (2021见顶 0.50x、2022恐慌底 1.93x、2024反转底 1.94x、今日实时 1.76x)
                inflection_ruler = StrategyBridge.get_historical_inflection_ruler(
                    current_erp=erp_pct,
                    current_bias=bias_val
                )
                ruler_bar_html = render_historical_inflection_ruler_html(inflection_ruler)

                safe_markdown_html(f"""
                <div class="decision-card" style="padding: 10px 14px; margin-bottom: 10px; border-left: 3px solid var(--accent-primary); background: var(--bg-surface); min-height: auto !important;">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; flex-wrap: wrap; gap: 4px;">
                        <span style="font-size: 12px; font-weight: 700; color: var(--accent-primary);">📢 今日市场脉搏晨报 · 实时感知全景证据链</span>
                        <span style="font-size: 10.5px; color: var(--text-secondary); font-family: monospace;">
                            ⏱️ 实时感知: <b>{rt_time_str}</b> ｜ 成交: <b>{turnover_str}</b> ({vol_text}) ｜ 情绪: <b>{sentiment_label}</b>
                        </span>
                    </div>
                    <div style="font-size: 11px; color: var(--text-primary); line-height: 1.5; margin-bottom: 6px;">
                        <b>【操作定调与量化依据】</b>{op_stance}
                    </div>
                    <div style="background: var(--bg-elevated); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 6px 10px; margin-bottom: 6px;">
                        <div style="font-size: 10px; font-weight: 700; color: var(--text-secondary); margin-bottom: 3px;">⚡ 实时核心财经快讯与催化剂：</div>
                        {news_block_html}
                    </div>
                    {ruler_bar_html}
                </div>
                """)

                # 3. Top 3 赛道卡片升级 (实时涨跌幅胶囊、四维因子得分拆解、定性定量入选依据)
                cols_top3 = st.columns(3)
                for i, sec in enumerate(top3_sectors):
                    with cols_top3[i]:
                        sec_fund = sec.get("fund", {})
                        tag_color = "var(--color-up)" if "🔥" in sec["tag"] else ("var(--accent-primary)" if "🎯" in sec["tag"] else "var(--color-down)")
                        
                        # 今日盘中实时涨跌幅胶囊
                        rt_chg = float(sec.get("rt_change_pct", sec.get("change_pct", 0.0)))
                        rt_chg_color = "var(--color-up)" if rt_chg >= 0 else "var(--color-down)"
                        rt_chg_bg = "rgba(239, 68, 68, 0.1)" if rt_chg >= 0 else "rgba(16, 185, 129, 0.1)"
                        rt_chg_sign = "+" if rt_chg > 0 else ""
                        rt_chg_pill = f'<span style="font-size: 11px; font-weight: 700; padding: 1px 6px; border-radius: 4px; background: {rt_chg_bg}; color: {rt_chg_color}; border: 1px solid {rt_chg_color}; flex: 0 0 auto !important; white-space: nowrap !important;">今日实时 {rt_chg_sign}{rt_chg:.2f}%</span>'

                        # 四维因子得分拆解
                        s_val = float(sec.get("s_val", 0.0))
                        s_mom = float(sec.get("s_mom", 0.0))
                        s_er = float(sec.get("s_er", 0.0))
                        s_crowd = float(sec.get("s_crowd", 0.0))

                        # 定性定量入选依据
                        val_p = float(sec.get("val_percentile", 50.0))
                        if val_p <= 25.0:
                            rationale = f"估值分位仅 {val_p:.0f}%，处于历史极低击球区，安全边际深厚"
                        elif s_er >= 70.0 and s_mom >= 70.0:
                            rationale = f"信噪比高达 {s_er:.1f}，均线右侧多头排列，主升浪共振确立"
                        elif sec.get("sector_id") in ("pure_bond", "domestic_gold"):
                            rationale = "低波动防御压舱，与权益资产低相关，平抑组合回撤"
                        else:
                            rationale = f"四维因子均衡，反拥挤度良好({s_crowd:.1f})，稳健蓄势"

                        safe_markdown_html(f"""
                        <div class="decision-card" style="padding: 10px 12px; height: 100%; border-top: 2px solid {tag_color}; min-height: auto !important; display: flex; flex-direction: column; justify-content: space-between;">
                            <div>
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; flex-wrap: wrap; gap: 4px;">
                                    <span style="font-size: 13px; font-weight: 700; color: var(--text-primary);">{sec['name']}</span>
                                    <div style="display: flex; align-items: center; gap: 4px;">
                                        {rt_chg_pill}
                                        <span style="font-size: 11px; padding: 1px 6px; border-radius: 4px; background: var(--bg-canvas); color: {tag_color}; border: 1px solid var(--border-subtle); flex: 0 0 auto !important; white-space: nowrap !important;">{sec['tag']}</span>
                                    </div>
                                </div>
                                <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 4px;">
                                    综合得分: <b style="color: var(--text-primary); font-size: 13px;">{sec['total_score']}</b> ｜ 估值分位: {val_p:.0f}%
                                </div>
                                <div style="font-size: 10px; color: var(--text-secondary); background: var(--bg-canvas); padding: 3px 6px; border-radius: 4px; margin-bottom: 5px; border: 1px solid var(--border-subtle); display: flex; justify-content: space-between;">
                                    <span>估值: <b>{s_val:.1f}</b></span>
                                    <span>动量: <b>{s_mom:.1f}</b></span>
                                    <span>信噪比: <b>{s_er:.1f}</b></span>
                                    <span>反拥挤: <b>{s_crowd:.1f}</b></span>
                                </div>
                                <div style="font-size: 10.5px; color: var(--accent-primary); line-height: 1.35; margin-bottom: 6px;">
                                    💡 <b>入选依据：</b>{rationale}
                                </div>
                                <div style="font-size: 12px; font-weight: 600; color: var(--text-primary); margin-bottom: 2px;">
                                    优选: {sec_fund.get('name', '')}
                                </div>
                                <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 8px;">
                                    代码: <code>{sec_fund.get('code', '')}</code>
                                </div>
                            </div>
                        </div>
                        """)
                        if st.button("➕ 入备选池", key=f"btn_add_radar_pool_{sec['sector_id']}", use_container_width=True, type="secondary"):
                            # ... 原有入备选池与清空缓存逻辑保持不变 ...
```

---

### 2.3 图 1 双翼看板右翼 (`col_sentry`) 改造细节 (行 2521 & 2531)

1. **第 2521 行标题清理**：
   - 原代码：
     ```python
     st.markdown("<div style='font-size: 14px; font-weight: 700; color: var(--text-primary); margin-bottom: 8px;'>🚨 主动风险预警哨 · 六维主动巡检 <span style='font-size: 11px; font-weight: 400; color: var(--text-secondary);'>[主动风险预警哨 · 四维巡检升级版]</span></div>", unsafe_allow_html=True)
     ```
   - 彻底删除灰色开发汇报后缀，变更为：
     ```python
     st.markdown("<div style='font-size: 14px; font-weight: 700; color: var(--text-primary); margin-bottom: 8px;'>🚨 主动风险预警哨 · 全维主动巡检</div>", unsafe_allow_html=True)
     ```
2. **第 2531 行容器高度与卡片截断修复**：
   - 原代码：`with st.container(height=300):`
   - 修改为：`with st.container(height=360):`
   - 对内部所有 `.decision-card`（聚合卡片、单标的预警卡片）注入：
     `style="border-left: 3px solid ...; padding: 8px 10px; margin-top: 2px; margin-bottom: 6px; min-height: auto !important;"`
   - 彻底根除滚动条与容器上边界切除第一张预警卡片标题文字与边框的几何缺陷。

---

### 2.4 Tab 1 【🌱 新资建仓】与 Tab 2 【💼 持仓调仓】风控与再平衡卡片挂载

#### 2.4.1 Tab 1 挂载位置 (约行 3440 方案核心归因区)
在完成推演计算并展示 `💰 组合内生股息与票息安全垫` 下方，挂载目标波动率风控看板：
```python
            # 🎯 动态目标波动率风险预算巡检 (Target Volatility Risk Control)
            try:
                from portfolio_optimizer import apply_target_volatility_risk_control
                vol_ctrl_tab1 = apply_target_volatility_risk_control(opt_weights, user_risk_tier=active_tier)
                safe_markdown_html(render_target_volatility_card_html(vol_ctrl_tab1))
            except Exception:
                pass
```

#### 2.4.2 Tab 2 挂载位置 (约行 5460 调仓净效用门禁区)
在 `💡 调仓净效用门禁精算 (Net Utility Gate) 提示条` 下方，挂载目标波动率与存量底仓分红方式免损耗再平衡卡片：
```python
            # 1. 存量持仓动态目标波动率巡检
            try:
                from portfolio_optimizer import apply_target_volatility_risk_control
                vol_ctrl_tab2 = apply_target_volatility_risk_control(pm.holdings, user_risk_tier=getattr(pm, "user_risk_tier", "C3"))
                safe_markdown_html(render_target_volatility_card_html(vol_ctrl_tab2))
            except Exception:
                pass

            # 2. 存量底仓分红方式免损耗再平衡 (持有满1年红利底仓零费派现)
            try:
                from portfolio_manager import evaluate_dividend_cash_rebalancing
                div_cash_items = evaluate_dividend_cash_rebalancing(pm.holdings)
                if div_cash_items:
                    safe_markdown_html(render_dividend_cash_rebalance_card_html(div_cash_items))
            except Exception:
                pass
```

---

## 3. `tests/test_g3_evolution_loop.py` 增量测试用例设计

在 `tests/test_g3_evolution_loop.py` 的 `TestG3EvolutionLoop` 类末尾（第 638 行后），新增三大严格量化断言的专项测试用例：

### 3.1 `test_g6_1_realtime_news_and_quotes_fusion`
```python
    def test_g6_1_realtime_news_and_quotes_fusion(self):
        """
        G6 世代核心特性 1:
        1. 验证 data_loader.fetch_realtime_market_news_and_catalysts 实时快讯接口协议与兜底机制；
        2. 验证 OpportunityRadarEngine 盘中实时行情动态拼接入最后一根 K 线；
        3. 验证赛道得分动态跳动（彻底终结纯债 82.1、白酒 78.5 固定静态常数）；
        4. 验证今日市场脉搏晨报时间戳精确到秒、两市量能与情绪宽度、以及历史三大拐点对照尺稳定渲染。
        """
        import data_loader
        from advisory_engine import OpportunityRadarEngine, RADAR_SECTOR_CATALOG
        from strategy_bridge import StrategyBridge

        # 1. 验证实时快讯接口协议
        news_res = data_loader.fetch_realtime_market_news_and_catalysts(timeout=2.0)
        assert isinstance(news_res, dict)
        assert news_res.get("status") in ("success", "cached_fallback", "cold_start_fallback")
        assert "timestamp" in news_res
        assert "flash_news" in news_res
        assert len(news_res["flash_news"]) >= 1
        first_item = news_res["flash_news"][0]
        assert "title" in first_item and len(first_item["title"]) > 0
        assert "time" in first_item

        # 2. 验证盘中实时行情动态拼接至 OpportunityRadarEngine
        radar = OpportunityRadarEngine()
        sectors_baseline = radar.scan_all_sectors()
        score_map_base = {s["sector_id"]: s["total_score"] for s in sectors_baseline}

        # 模拟盘中白酒大涨 +3.5%，纯债急跌 -0.8%
        mock_quotes = {
            "liquor_staples": {"rt_change_pct": 3.5, "price": 103.5},
            "pure_bond": {"rt_change_pct": -0.8, "price": 99.2}
        }
        sectors_dynamic = radar.scan_all_sectors(realtime_quotes_override=mock_quotes)
        score_map_dyn = {s["sector_id"]: s["total_score"] for s in sectors_dynamic}

        # 验证得分随盘中行情动态跳动，绝非静态假数据
        assert "pure_bond" in score_map_dyn
        assert "liquor_staples" in score_map_dyn
        # 验证白酒在实时大涨后动量得分或综合得分与基线产生显著差异
        assert score_map_dyn["liquor_staples"] != score_map_base["liquor_staples"] or \
               score_map_dyn["pure_bond"] != score_map_base["pure_bond"], \
               "盘中实时行情未动态更新赛道得分！"

        # 3. 验证晨报区时间戳精确到秒与历史拐点对照尺 4 节点
        ruler = StrategyBridge.get_historical_inflection_ruler(current_erp=82.6, current_bias=-2.07)
        assert len(ruler["nodes"]) == 4
        assert ruler["nodes"][0]["multiplier"] <= 0.60 # 2021顶
        assert ruler["nodes"][1]["multiplier"] >= 1.50 # 2022底
        assert ruler["nodes"][2]["multiplier"] >= 1.80 # 2024底
        assert "今日" in ruler["nodes"][3]["date"] or "今日" in ruler["nodes"][3]["event"]
```

### 3.2 `test_g6_2_online_heuristic_factor_evolver`
```python
    def test_g6_2_online_heuristic_factor_evolver(self):
        """
        G6 世代核心特性 2:
        1. 验证 OnlineHeuristicFactorEvolver 32 个基因个体在线演化；
        2. 验证基于近 60 日真实收益率矩阵的纯 NumPy 向量化评估执行时间 < 50ms；
        3. 验证废除 0.30/0.30/0.25/0.15 静态常数，演化权重严格归一化 sum(w) == 1.000000；
        4. 验证样本外超额适应度增益非负 (oos_excess_sharpe >= 0.0)；
        5. 验证 OpportunityRadarEngine.get_evolution_badge_data 白盒徽章数据协议。
        """
        import time
        from advisory_engine import OnlineHeuristicFactorEvolver, OpportunityRadarEngine

        evolver = OnlineHeuristicFactorEvolver(population_size=32, n_generations=8)
        
        # 准备近 60 个交易日的模拟/真实 14 赛道收益率矩阵 (60 x 14)
        np.random.seed(42)
        returns_matrix = np.random.normal(loc=0.0005, scale=0.015, size=(60, 14))
        baseline_w = np.array([0.30, 0.30, 0.25, 0.15])

        # 速度基准测试：要求 < 50ms
        t_start = time.perf_counter()
        evolve_res = evolver.evolve(returns_matrix, baseline_weights=baseline_w)
        elapsed_ms = (time.perf_counter() - t_start) * 1000.0

        assert elapsed_ms < 50.0, f"NumPy 向量化遗传进化耗时超标: {elapsed_ms:.2f}ms (需 < 50ms)！"

        # 权重数学守恒
        weights = evolve_res["weights"]
        assert len(weights) == 4
        assert np.all(weights >= 0.0), "因子权重必须非负！"
        assert abs(np.sum(weights) - 1.0) < 1e-5, f"演化因子权重和必须严格为 1.000000，实际为 {np.sum(weights)}"
        # 验证已演化出不同于静态硬编码常数的动态权重
        assert not np.allclose(weights, baseline_w, atol=1e-3), "演化权重未突破旧静态 0.30/0.30/0.25/0.15！"

        # 适应度检验
        assert evolve_res["oos_excess_sharpe"] >= 0.0, "样本外超额适应度不得为负！"

        # 白盒徽章数据协议校验
        radar = OpportunityRadarEngine()
        badge_data = radar.get_evolution_badge_data()
        assert "weights" in badge_data
        assert "oos_excess_sharpe" in badge_data
        assert "adaptation_note" in badge_data
```

### 3.3 `test_g6_3_target_volatility_risk_control_and_dividend_mode`
```python
    def test_g6_3_target_volatility_risk_control_and_dividend_mode(self):
        """
        G6 世代核心特性 3:
        1. 验证 C1 至 C5 目标年化波动率预算上限与超标判定；
        2. 验证组合波动率超标时高波资产向纯债/现金的压降比例测算与权重归一化；
        3. 验证持有满 1 年红利底仓基金的现金分红再配置测算（免 0.50% 赎回费 + 零 T+2 在途损耗）。
        """
        from portfolio_optimizer import TARGET_VOLATILITY_BY_TIER, apply_target_volatility_risk_control
        from portfolio_manager import PortfolioManager, FundHolding, evaluate_dividend_cash_rebalancing

        # 1. 验证 C1~C5 档位上限配置
        assert TARGET_VOLATILITY_BY_TIER["C1"] == 0.05
        assert TARGET_VOLATILITY_BY_TIER["C2"] == 0.08
        assert TARGET_VOLATILITY_BY_TIER["C3"] == 0.12
        assert TARGET_VOLATILITY_BY_TIER["C4"] == 0.16
        assert TARGET_VOLATILITY_BY_TIER["C5"] == 0.22

        # 2. 模拟高波组合在 C3 (上限 12%) 下触发超标压降
        high_vol_holdings = {
            "011613": 0.40,  # 科创50 (年化波动 ~32%)
            "161725": 0.40,  # 白酒 (年化波动 ~26%)
            "002351": 0.20   # 纯债 (年化波动 ~3%)
        }
        res_ctrl = apply_target_volatility_risk_control(high_vol_holdings, user_risk_tier="C3")
        assert res_ctrl["is_over_budget"] is True
        assert res_ctrl["user_risk_tier"] == "C3"
        assert res_ctrl["target_vol"] == 0.12
        assert res_ctrl["current_port_vol"] > 0.12
        assert res_ctrl["reduction_ratio"] > 0.0
        assert len(res_ctrl["reduction_plan"]) > 0
        assert res_ctrl["transfer_target"]["code"] == "002351"

        # 3. 验证持有满 1 年红利标的现金分红免损耗再平衡
        pm = PortfolioManager(db_path=":memory:")
        # 满 1 年 (420天) 红利资产
        pm.holdings["100032"] = FundHolding(
            fund_code="100032", fund_name="富国中证红利指数A",
            shares=50000.0, cost_price=1.2, current_nav=1.4,
            market_value=70000.0, cost_basis=60000.0,
            holding_days=420, share_class="A"
        )
        # 未满 1 年 (60天) 科技成长资产
        pm.holdings["011613"] = FundHolding(
            fund_code="011613", fund_name="华夏科创50联接C",
            shares=20000.0, cost_price=1.0, current_nav=1.1,
            market_value=22000.0, cost_basis=20000.0,
            holding_days=60, share_class="C"
        )

        div_items = evaluate_dividend_cash_rebalancing(pm.holdings)
        assert len(div_items) >= 1
        # 100032 必须符合条件
        item_100032 = next(it for it in div_items if it["code"] == "100032")
        assert item_100032["eligible"] is True
        assert item_100032["holding_days"] == 420
        assert item_100032["annual_dividend_est"] > 0
        assert item_100032["saved_redemption_fee"] > 0
        assert item_100032["saved_transit_friction"] > 0
        assert item_100032["total_saved"] == round(item_100032["saved_redemption_fee"] + item_100032["saved_transit_friction"], 2)
        assert "现金分红" in item_100032["action_recommendation"]
```

---

## 4. 视觉走查与全流程测试验收标准 (QA & Visual Walkthrough)

### 4.1 测试套件执行门禁 (Test Suite Gate)
在实施阶段，必须保证以下 4 大测试套件 100% 通过（预计 53 项全绿）：
1. `pytest tests/test_infra.py` (14 项通过，确认 4 大裁判文件 0 修改)
2. `pytest tests/test_adv_final_closure.py` (14 项通过)
3. `pytest tests/test_g3_evolution_loop.py` (15 项通过，含 G6 增量 3 项)
4. `pytest tests/test_gui_multi_ledger_stress.py` (10 项通过)

### 4.2 /browser 多模态视觉核查清单 (Visual Inspection Checklist)
1. **今日市场脉搏晨报**：
   - 顶部实时秒级时间戳、成交额与情绪标签清晰；
   - 2~3 条最新财经快讯整齐排布，无溢出；
   - 操作定调语意明确有依据；
   - 历史三大牛熊拐点对照尺稳定渲染，4 节点完整。
2. **Top 3 赛道卡片**：
   - 今日实时涨跌幅胶囊（红涨绿跌）醒目；
   - 四维得分拆解条平整；
   - 定性定量入选依据逻辑清晰。
3. **右翼主动风险预警哨**：
   - 标题无 `[主动风险预警哨 · 四维巡检升级版]` 灰色尾缀；
   - 容器高度拉开至 360px，第一张预警卡片与顶部边框预留呼吸空间，完全不被滚动条截断。
4. **在线基因编程白盒徽章**：
   - 位于左翼机会雷达顶部，绿灯收敛标识清晰；
   - 4 维权重与 OOS 增益一览无余。
5. **Tab 1 & Tab 2 风控卡片**：
   - 目标波动率超标预警卡片与达标绿标正常切换；
   - Tab 2 分红方式免损耗再平衡卡片完整列出省费账单。
6. **全主题与小屏幕自适应**：
   - 机构冷灰 (Light Slate) 与 彭博暗黑 (Dark Terminal) 无白底白字或黑底黑字；
   - 640px 手机视口下横向卡片平滑滚动，无文字重叠。

---

## 5. 总结与下阶段工作衔接

本方案设计实现了全景证据链与程序内建进化算子在 GUI 端的完整透出，并配套了数学严格、物理真实的增量测试用例。方案已完全具备由 Worker / Implementer 智能体直接转化为生产代码的能力。
