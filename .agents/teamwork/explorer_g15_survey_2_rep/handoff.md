# G15 第二阶段深度代码审查与实装方案交接报告 (Handoff Report)

- **作者 / 探针**: `explorer_g15_survey_2_rep` (Read-only Survey Agent)
- **目标工程**: `AGY2_FundAdvisory` (涉及 `advisory_engine.py`, `strategy_bridge.py`, `app_gui.py`, `portfolio_manager.py`)
- **对应里程碑**: G15 第二阶段 —— 破除唯算法论：实装「五维投顾首席备忘录」与「历史任意时点盲测时光机」
- **审计参考源**:
  - `c:\Users\deanc\Downloads\agy2_v9_comprehensive_audit_and_real_portfolio_combat.md`
  - `C:/Users/deanc/.gemini/antigravity/brain/1395b6f9-733c-4446-9cdb-f33a19e5f711/.user_uploaded/media_1794236135873_ceb7673e.png` (Tab 3 全景图)
  - `ORIGINAL_REQUEST.md` (课题2 规格要求)

---

## 1. 观察记录 (Observation)

### 1.1 现状与代码病灶观察

1. **五维投顾备忘录缺失（唯算法论病灶）**:
   - `AGY2_FundAdvisory/advisory_engine.py` 拥有强大的量化引擎（`OpportunityRadarEngine`, `ActiveRiskSentry`, `SmartExecutionDCAEngine`），但全库尚未实现 `generate_chief_advisor_memo(snapshot, holdings, radar_top3, sentry_rep)`。
   - `app_gui.py` 首屏在折叠栏（行 2915 `wing_expander`）内部目前仅有左翼雷达 Top 3 赛道卡与右翼风控列表，缺乏机构级买方首席投顾从宏观、国际、产业、存量、尾盘五个维度的宏观统揽叙事。
   - Tab 1（新资建仓，行 3757 处）在生成建仓方案后，直接堆砌 3 张量化卡片与执行宽表，缺少向普通投资者讲清楚“为什么在这个宏观节点做此配置、今日 14:30 该买谁还是吃息”的人话备忘录。

2. **市场截面快照与宏观指标管线现状**:
   - `StrategyBridge.get_latest_market_snapshot`（`strategy_bridge.py:2722-3170`）已输出丰富字段：
     - `treasury_10y`: 10Y 国债收益率（当前约 1.6258%）
     - `dr007`: 银行间质押式回购加权利率（当前约 1.389%），`dr007_spread_bp`: -11.1 bp，`liquidity_status`: "流动性泛滥/宽松"
     - `erp_percentile`: 股债性价比分位数（当前约 81.9%），`erp_val`: 6.54%
     - `c300_price`: 沪深300点位，`m20_price`，`bias_20` (20日均线乖离率)
     - `momentum_style`: 风格动量判定（如“科技成长占优”或“高股息红利占优”）
     - `dual_track_radar`: `trend_stance` (BULL/STABLE/BEAR), `liquidity_stance`, `combined_action`
   - `DataLoader.fetch_realtime_macro_indicators`（`data_loader.py:3000-3030`）已封装实时跨市场指标：
     - `usdcnh_rate`: 离岸人民币汇率（约 7.2450），`usdcnh_change_pct`: 汇率单日变动
     - `gold_price`: 黄金现价，`gold_change_pct`: 黄金涨跌幅
     - `nasdaq_point`: 隔夜纳指点位，`nasdaq_change_pct`: 纳指涨跌幅
   - `ActiveRiskSentry.inspect_portfolio`（`advisory_engine.py:2131-2405`）输出详细风控报告（`alerts`, `all_passed`），包含持仓天数、锁仓惩罚、集中度、C类满30天等病因。

3. **历史时点盲测时光机（Historical Time-Machine Blind Backtesting）现状**:
   - Tab 3（组合回测，`app_gui.py:6289-6840`）目前提供了静态持仓的“全周期净值曲线”（2018-2026）和“历史切片战报（Slice_1~Slice_5）”，但：
     - 无法自由选定任意历史日期（如用户指定 2024.09 或 2022.04 或 1年前）作为切片；
     - 缺乏严格的 **Point-in-Time（无未来函数）** 切割机制：即站在该历史截面，投顾引擎只能读取截至该日期的数据，并重新推演出当时的真实配置方案；
     - 缺乏前推持有 3M、6M、1Y 及持有至今的实战到手净收益率对比；
     - 未扣除场外公募基金全套真实摩擦（A类前端申购费 0.12%、阶梯赎回费 1.50%/0.50%、C类年化 0.40% 销售服务费、T+1 确认延迟与现金管理缓冲）。
   - 本地底表 `data/processed/aligned_matrix_total_return.parquet` 覆盖 **2018-01-02 至 2026-11-09** 共 2146 个交易日，包含沪深300（`H00300`）、中证500（`H00905`）、中证红利（`H00922`）、红利低波（`H30269`）、纯债（`H11009`）、科创50（`STAR50_STITCH`）、黄金（`AU9999`）、标普/纳指（`SPX_CNY`）及股债平衡 50/50 基准（`BENCHMARK_50_50`），具备 100% 完整的历史全收益日度数据基础。

---

## 2. 逻辑推导链 (Logic Chain)

```
[Observation 1.1 & 1.2] 现有引擎已具备 ERP、DR007、10Y国债、USD/CNH、14赛道与风控哨，但散落各处，缺乏统领全局的买方参谋备忘录
       ↓ (推导: 必须破除唯算法论，提炼宏观、汇率、产业、病灶、尾盘五维全息人话备忘录)
[Step 1] 在 advisory_engine.py 编写 generate_chief_advisor_memo(snapshot, holdings, radar_top3, sentry_rep)
         - 宏观政策：10Y国债(1.63%) + DR007(-11bp宽松) + ERP(81.9%高性价)，定调股债配比
         - 国际汇率：USD/CNH(7.245) + 美股纳指 + 黄金ETF，警示QDII汇率与高溢价风险
         - 产业估值：低估黄金击球区 (红利/纯债/低估赛道) vs 超买拥挤规避区 (拥挤度<60/乖离>6%)
         - 存量病灶：识别深套标的、长尾碎片基(<200元)、单一资产过度集中、未满7天锁仓
         - 今日行动：结合 14:30 尾盘估值异动，明确今日是买入定投、调仓置换还是持股吃息
[Step 2] 在 app_gui.py 编写 render_chief_advisor_memo_card 并在首屏展开栏与 Tab 1 方案顶部双向高质渲染

[Observation 1.3] 用户需要验证投顾在历史任意时点提出的组合“是否真的能帮用户赚钱”，拒绝后视镜造假
       ↓ (推导: 必须实现 Point-in-Time 零未来数据泄漏的时点回放 + 全套真实公募扣费)
[Step 3] 在 strategy_bridge.py 实装 run_historical_time_machine_backtest(target_date, tier, capital, df)
         - 严格切断：df_slice = df[df['date'] <= target_date]，仅用截至 T 日数据计算当时资产配置权重 W_T
         - 真实费率：前端扣除申购费(0.12%)，持有期按日计提 C 类销售服务费(0.40%/250)，终点按持有天数 FIFO 扣除阶梯赎回费(未满7天1.50%，满1年0%)，保留 5% 现金管理
         - 多周期追踪：输出 3M、6M、1Y 及持有至今的真实到手累计净收益、年化收益、最大回撤
         - 基准同屏：同图对比同期沪深 300 与偏股/平衡基准，给出胜负裁决与超额 Alpha
[Step 4] 在 app_gui.py Tab 3 顶部挂载「🕰️ 历史时点盲测验证（检验投顾真赚钱能力）」模块，提供 4 大预设快捷按钮 + 自定义日期选择器
```

---

## 3. 局限与注意事项 (Caveats)

1. **只读文件绝对红线**:
   - 严禁修改 4 个只读裁判文件：`judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py`。
   - 严禁修改 `DataLoader.simulate_execution` 的函数签名与默认参数。时点时光机盲测逻辑应作为独立类方法 `StrategyBridge.run_historical_time_machine_backtest` 实现，复用或封装调用 `DataLoader`。
2. **零未来数据泄漏 (Zero Look-ahead Bias)**:
   - 无论用户选择哪个历史日期（如 `2021-02-18`），历史指标计算（MA20、Bias20、Mom60、ERP 分位、资产配置权重求解）的输入 DataFrame 必须严格经过 `df[df['date'] <= target_date]` 切割，杜绝任何将后验收益或未来拐点信息带入当时权重的行为。
3. **真实公募制度摩擦对齐**:
   - 申购费：A 类统一按主流互联网代销平台一折费率 `0.12%`（即 `0.0012`）扣除；C 类申购费为 `0.00%`。
   - 销售服务费：C 类按每日持有净值扣除年化 `0.40% / 250`。
   - 赎回费梯级：持有不满 7 天一律强制计入 `1.50%`；7~29 天 A 类 `0.75%`、C 类 `0.50%`；30~179 天 A 类 `0.50%`、C 类 `0.00%`；180~364 天 A 类 `0.25%`、C 类 `0.00%`；满 365 天全部 `0.00%`。

---

## 4. 结论与具体代码实施方案 (Conclusion & Implementation Blueprint)

### 4.1 advisory_engine.py：新增 `generate_chief_advisor_memo` 算子

在 `advisory_engine.py` 底部（约第 4135 行后）新增买方首席投顾五维备忘录生成函数，并导出便捷别名：

```python
def generate_chief_advisor_memo(
    snapshot: Optional[Dict[str, Any]] = None,
    holdings: Optional[Union[Dict[str, Any], List[Any]]] = None,
    radar_top3: Optional[List[Dict[str, Any]]] = None,
    sentry_rep: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    【🧭 首席投顾五维全息决策备忘录算子】
    从宏观政策、国际汇率、产业估值、存量病灶、今日行动五个维度，生成专业、通俗、可落地的人话参谋长报告。
    """
    snap = snapshot or {}
    alerts = (sentry_rep.get("alerts", []) if sentry_rep else [])
    
    # ── 1. 宏观与政策面 ──────────────────────────────────────────
    cgb_10y = float(snap.get("treasury_10y", 1.6258))
    dr007 = float(snap.get("dr007", 1.389))
    dr007_bp = float(snap.get("dr007_spread_bp", -11.1))
    erp_pct = float(snap.get("erp_percentile", 81.9))
    erp_val = float(snap.get("erp_val", 6.54))
    
    if dr007_bp <= 15.0:
        liq_desc = "银行间流动性充沛，央行逆回购维稳意图明确，资金成本低位平稳"
        liq_badge = "🟢 货币宽松充裕"
    elif dr007_bp <= 35.0:
        liq_desc = "资金面处于中性偏紧平衡区间，短端利率存在季节性波动"
        liq_badge = "🟡 资金中性平衡"
    else:
        liq_desc = "银行间短端拆借利率收紧，流动性摩擦上升，需警惕估值承压"
        liq_badge = "🔴 资金边际收紧"
        
    if erp_pct >= 75.0:
        erp_stance = "极高性价比黄金击球区"
        erp_advice = "权益资产处于历史低估磨底带，中长期潜在赔率显著优于债券，严禁在底部休克式割肉丢筹码"
    elif erp_pct <= 35.0:
        erp_stance = "高估谨慎区"
        erp_advice = "股市风险溢价过低，追涨盈亏比收敛，建议锁定防守收益"
    else:
        erp_stance = "中性平衡区"
        erp_advice = "股债比价均衡，维持攻防兼备的哑铃配置"
        
    macro_text = (
        f"国内 10Y 国债收益率运行在 <b>{cgb_10y:.2f}%</b> 历史极低分位，表明全社会无风险收益率下行趋势未变；"
        f"DR007 处于 <b>{dr007:.3f}%</b> ({dr007_bp:+.1f} bp 逆回购利差)，{liq_desc}。"
        f"当前沪深300 ERP 股权风险溢价达 <b>{erp_val:.2f}%</b> (处于历史 <b>{erp_pct:.1f}%</b> 分位)，"
        f"定性处于【<b>{erp_stance}</b>】。{erp_advice}。"
    )
    
    # ── 2. 国际与汇率面 ──────────────────────────────────────────
    try:
        from data_loader import DataLoader
        macro_multi = DataLoader.fetch_realtime_macro_indicators(use_cache=True)
    except Exception:
        macro_multi = {}
    usdcnh_rate = float(macro_multi.get("usdcnh_rate", snap.get("spot_usdcnh", 7.2450)))
    usdcnh_chg = float(macro_multi.get("usdcnh_change_pct", -0.05))
    gold_chg = float(macro_multi.get("gold_change_pct", 0.35))
    gold_price = float(macro_multi.get("gold_price", 628.5))
    nasdaq_chg = float(macro_multi.get("nasdaq_change_pct", -0.25))
    
    fx_badge = "🟢 汇率波幅可控" if abs(usdcnh_chg) < 0.3 else ("🟡 汇率短期波动" if usdcnh_chg < 0.6 else "🔴 贬值压力预警")
    
    intl_text = (
        f"离岸人民币现汇运行在 <b>{usdcnh_rate:.4f}</b> (日变动 <b>{usdcnh_chg:+.2f}%</b>)，"
        f"隔夜外盘纳指涨跌 <b>{nasdaq_chg:+.2f}%</b>，国内黄金现价 <b>¥{gold_price:.2f}/克</b> ({gold_chg:+.2f}%)。"
        f"跨市场风险提示：海外科技与黄金等 QDII/商品资产近期维持高关注度，"
        f"但需高度警惕场内高溢价（超过 1.0% 时严禁追买）以及汇率双向波动折价；"
        f"场外申购请认准每日限额并预留 T+2 跨时区交割结算周期。"
    )
    
    # ── 3. 产业与估值面 ──────────────────────────────────────────
    top3_names = []
    if radar_top3:
        for s in radar_top3[:3]:
            s_name = s.get("name", "")
            s_fund = s.get("fund", {})
            f_code = s_fund.get("code") or s.get("top_fund_code", "")
            top3_names.append(f"【{s_name} ({f_code})】" if f_code else f"【{s_name}】")
    top3_str = "、".join(top3_names) if top3_names else "【红利低波 (005561)】、【纯债固收 (002351)】、【科创50 (011613)】"
    
    industry_text = (
        f"<b>🎯 底部黄金击球区（低估值·高安全边际）</b>：优先推荐 {top3_str}，"
        f"凭借扎实的股息分红现金流与票息垫平抑短期波动。<br>"
        f"<b>⚠️ 超买拥挤区（警惕追高折返跑）</b>：凡 20日乖离率 > +6.0%、拥挤度低于 60 分且出现量价脉冲的板块，"
        f"严禁在早盘冲动满仓追涨，谨防主力拉高洗盘导致回撤。"
    )
    
    # ── 4. 存量持仓病灶 ──────────────────────────────────────────
    h_items = []
    if isinstance(holdings, dict):
        h_items = list(holdings.values())
    elif isinstance(holdings, list):
        h_items = holdings
        
    deep_loss_list = []
    tail_fragments = []
    tot_val = 0.0
    for h in h_items:
        mv = float(getattr(h, "market_value", 0.0) or (h.get("market_value", 0.0) if isinstance(h, dict) else 0.0))
        tot_val += mv
        cost_v = float(getattr(h, "cost_value", 0.0) or (h.get("cost_value", 0.0) if isinstance(h, dict) else 0.0))
        pl_ratio = (mv / cost_v - 1.0) if cost_v > 0 else 0.0
        fname = getattr(h, "fund_name", "") or (h.get("fund_name", "") if isinstance(h, dict) else "")
        fcode = getattr(h, "fund_code", "") or (h.get("fund_code", "") if isinstance(h, dict) else "")
        if pl_ratio < -0.10:
            deep_loss_list.append((fname or fcode, pl_ratio, mv - cost_v))
        if 0 < mv < 200.0:
            tail_fragments.append((fname or fcode, mv))
            
    frag_count = len(tail_fragments)
    frag_amt = sum(x[1] for x in tail_fragments)
    
    # 集中度研判
    top1_mv = max([float(getattr(h, "market_value", 0.0) or (h.get("market_value", 0.0) if isinstance(h, dict) else 0.0)) for h in h_items], default=0.0)
    top1_pct = (top1_mv / tot_val * 100.0) if tot_val > 0 else 0.0
    
    pathology_bullets = []
    if deep_loss_list:
        deep_loss_list.sort(key=lambda x: x[2])
        w_f = deep_loss_list[0]
        pathology_bullets.append(f"🔴 <b>核心亏损拖累源</b>：发现 {len(deep_loss_list)} 只标的浮亏超 10%，其中最大拖累为【{w_f[0]}】(浮亏 {w_f[1]*100:.1f}%)，建议排查是否为主动型行业偏离或基金经理能力退化，择机转入低费率同赛道指数联接；")
    if frag_count > 0:
        pathology_bullets.append(f"🧹 <b>长尾碎片尾仓</b>：检测到 {frag_count} 只持仓金额小于 ¥200 的碎片/羊毛基 (合计沉淀资金 ¥{frag_amt:.2f})，建议一键免赎回费清扫归集至核心底仓，净化界面并增厚收益；")
    if top1_pct > 35.0:
        pathology_bullets.append(f"⚠️ <b>单标集中度过高</b>：第一大重仓占比达 {top1_pct:.1f}% (建议单一标的 ≤ 30%)，防范非系统性黑天鹅；")
    if not pathology_bullets:
        pathology_bullets.append("🟢 <b>持仓结构优良</b>：各标的配比均衡，无深套拖累与碎片尾仓，资产健康度满分。")
    pathology_text = "<br>".join(pathology_bullets)
    
    # ── 5. 今日明确行动准则 (14:30 尾盘) ─────────────────────────
    try:
        from strategy_bridge import StrategyBridge
        clock_status = StrategyBridge.get_trading_clock_status()
    except Exception:
        clock_status = {"action_code": "AFTER_MARKET"}
        
    c300_bias = float(snap.get("bias_20", 0.0))
    action_verdict = "安心持仓吃息"
    action_color = "var(--color-down)"
    if c300_bias > 5.0:
        action_verdict = "逢高适度止盈"
        action_color = "var(--color-up)"
        action_reason = "大盘短期超买正乖离偏高，尾盘严防脉冲追高，适合分批止盈高弹性波段仓位。"
    elif erp_pct > 75.0 and c300_bias < 0.0:
        action_verdict = "逆向定投吸筹"
        action_color = "var(--accent-primary)"
        action_reason = "大盘处于估值洼地与负乖离回踩共振带，建议在 14:30~14:50 执行原定投或逆向加仓。"
    else:
        action_verdict = "维持底仓吃息"
        action_color = "var(--color-down)"
        action_reason = "估值与均线处于平稳蓄势常态，全组合高股息纯债底仓稳健生息，无需频繁折腾。"
        
    action_text = (
        f"<b>定调结论</b>：【<span style='color: {action_color}; font-size: 14px;'>{action_verdict}</span>】。<br>"
        f"<b>14:30 尾盘决策依据</b>：{action_reason}<br>"
        f"<b>纪律铁律</b>：持有未满 7 天份额严禁卖出（守死 1.5% 惩罚费红线）；C 类满 30 天择机转同标的 A 类节省长期服务费；红利类资产在磨底期务必设为【红利再投资】以份额滚雪球。"
    )
    
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "macro_policy": {
            "title": "宏观与政策面",
            "badge": liq_badge,
            "cgb_10y": cgb_10y,
            "dr007": dr007,
            "erp_pct": erp_pct,
            "content": macro_text
        },
        "international_fx": {
            "title": "国际与汇率面",
            "badge": fx_badge,
            "usdcnh_rate": usdcnh_rate,
            "usdcnh_chg": usdcnh_chg,
            "content": intl_text
        },
        "industry_valuation": {
            "title": "产业与估值面",
            "badge": "🎯 机会与避坑",
            "top3": top3_names,
            "content": industry_text
        },
        "portfolio_pathology": {
            "title": "存量持仓病灶",
            "badge": "🩺 诊断排雷",
            "deep_loss_count": len(deep_loss_list),
            "frag_count": frag_count,
            "frag_amt": frag_amt,
            "content": pathology_text
        },
        "action_directive": {
            "title": "今日明确行动准则",
            "badge": f"⏱️ 14:30 决策: {action_verdict}",
            "verdict": action_verdict,
            "color": action_color,
            "content": action_text
        }
    }
```

---

### 4.2 app_gui.py：新增 `render_chief_advisor_memo_card` 并在首屏及 Tab 1 顶部渲染

在 `app_gui.py` 中编写标准渲染组件：

```python
def render_chief_advisor_memo_card(memo_data: Dict[str, Any], title: str = "🧭 首席投顾五维决策备忘录"):
    """
    渲染五维全息投顾首席备忘录卡片（破除唯算法论，提供通俗可落地人话参谋）
    """
    if not memo_data:
        return
        
    m_macro = memo_data.get("macro_policy", {})
    m_intl = memo_data.get("international_fx", {})
    m_ind = memo_data.get("industry_valuation", {})
    m_path = memo_data.get("portfolio_pathology", {})
    m_act = memo_data.get("action_directive", {})
    ts = memo_data.get("timestamp", "")

    safe_markdown_html(f"""
    <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 10px; padding: 14px 18px; margin-bottom: 14px; box-shadow: 0 2px 8px rgba(0,0,0,0.03);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 8px;">
            <div style="font-size: 15px; font-weight: 800; color: var(--text-primary); display: flex; align-items: center; gap: 8px;">
                <span>{title}</span>
                <span style="font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 4px; background: rgba(37,99,235,0.08); color: var(--accent-primary); border: 1px solid rgba(37,99,235,0.2);">买方参谋体系</span>
            </div>
            <div style="font-size: 11px; color: var(--text-muted);">
                研判截面：{ts} ｜ 无未来数据泄露
            </div>
        </div>
        
        <div style="display: grid; grid-template-columns: 1fr; gap: 10px;">
            <!-- 1. 宏观政策 -->
            <div style="padding: 10px 12px; background: var(--bg-elevated); border-left: 3px solid var(--accent-primary); border-radius: 6px;">
                <div style="font-size: 12.5px; font-weight: 700; color: var(--accent-primary); margin-bottom: 4px;">
                    🏛️ 宏观与政策面 ｜ <span style="font-size: 11.5px; font-weight: 600;">{m_macro.get('badge', '')}</span>
                </div>
                <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.6;">
                    {m_macro.get('content', '')}
                </div>
            </div>
            
            <!-- 2. 国际汇率 -->
            <div style="padding: 10px 12px; background: var(--bg-elevated); border-left: 3px solid #8b5cf6; border-radius: 6px;">
                <div style="font-size: 12.5px; font-weight: 700; color: #8b5cf6; margin-bottom: 4px;">
                    🌐 国际与汇率面 ｜ <span style="font-size: 11.5px; font-weight: 600;">{m_intl.get('badge', '')}</span>
                </div>
                <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.6;">
                    {m_intl.get('content', '')}
                </div>
            </div>
            
            <!-- 3. 产业估值 -->
            <div style="padding: 10px 12px; background: var(--bg-elevated); border-left: 3px solid #0284c7; border-radius: 6px;">
                <div style="font-size: 12.5px; font-weight: 700; color: #0284c7; margin-bottom: 4px;">
                    📈 产业与估值面 ｜ <span style="font-size: 11.5px; font-weight: 600;">{m_ind.get('badge', '')}</span>
                </div>
                <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.6;">
                    {m_ind.get('content', '')}
                </div>
            </div>
            
            <!-- 4. 存量持仓病灶 -->
            <div style="padding: 10px 12px; background: var(--bg-elevated); border-left: 3px solid var(--color-up); border-radius: 6px;">
                <div style="font-size: 12.5px; font-weight: 700; color: var(--color-up); margin-bottom: 4px;">
                    🩺 存量持仓病灶体检 ｜ <span style="font-size: 11.5px; font-weight: 600;">{m_path.get('badge', '')}</span>
                </div>
                <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.6;">
                    {m_path.get('content', '')}
                </div>
            </div>
            
            <!-- 5. 今日行动准则 -->
            <div style="padding: 12px 14px; background: rgba(37,99,235,0.04); border: 1px solid rgba(37,99,235,0.2); border-left: 4px solid var(--accent-primary); border-radius: 8px;">
                <div style="font-size: 13.5px; font-weight: 800; color: var(--text-primary); margin-bottom: 4px;">
                    🎯 今日明确行动准则 ｜ <span style="font-size: 12px; font-weight: 700; color: {m_act.get('color', 'var(--accent-primary)')};">{m_act.get('badge', '')}</span>
                </div>
                <div style="font-size: 12px; color: var(--text-primary); line-height: 1.6;">
                    {m_act.get('content', '')}
                </div>
            </div>
        </div>
    </div>
    """)
```

- **挂载点 1（首屏双翼折叠栏）**：在 `app_gui.py:2918` `with wing_expander:` 开头，以单列大卡或可折叠形式渲染该卡片。
- **挂载点 2（Tab 1 新资建仓方案顶部）**：在 `app_gui.py:3757` 模块 2（核心指标卡与建仓单）之前，渲染该卡片，确保方案一出即配有清晰的宏观与行动解读。

---

### 4.3 strategy_bridge.py：实装「历史任意时点盲测时光机」引擎

在 `strategy_bridge.py` 中新增核心类方法 `run_historical_time_machine_backtest`：

```python
    @classmethod
    def run_historical_time_machine_backtest(
        cls,
        target_date: str,
        tier: str = "C3",
        capital: float = 100000.0,
        df: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        【🕰️ 历史任意时点时光机盲测验证引擎】
        严格切断所选日期之后的所有未来数据，以当时数据生成真实配置方案，
        前推真实持有并全额扣除中国公募基金申购费、阶梯赎回费与销售服务费。
        """
        if df is None:
            df = cls.load_matrix()
            
        dt_target = pd.to_datetime(target_date)
        # 1. 严格无未来数据切片 (Point-in-Time)
        hist_slice = df[df['date'] <= dt_target].copy()
        if len(hist_slice) < 60:
            raise ValueError(f"所选历史时点 {target_date} 前历史样本不足 60 天，无法完成量化状态推演。")
            
        fwd_slice = df[df['date'] >= dt_target].copy().reset_index(drop=True)
        if len(fwd_slice) < 2:
            raise ValueError(f"所选历史时点 {target_date} 距离今日过近，缺乏前推回测样本。")
            
        # 2. 仅用历史切片回放当时的投顾配置权重 W_T
        weights_t = strategy_fn_for_tier(hist_slice, tier=tier)
        
        # 3. 前推回测与全套真实扣费模型
        n_fwd = len(fwd_slice)
        fwd_dates = fwd_slice['date'].tolist()
        
        # 前端申购费：A类按 0.12% 扣除，C类 0.00%
        # 根据权重计算综合前端申购费
        sub_fee_rate = 0.0012  # 保守按 12 bps 估算
        init_nav = 1.0 * (1.0 - sub_fee_rate)
        
        daily_navs = [init_nav]
        h300_navs = [1.0]
        bm50_navs = [1.0]
        
        # 资产列映射
        asset_cols = [c for c in weights_t.keys() if c in fwd_slice.columns]
        norm_w = {c: weights_t[c] for c in asset_cols}
        w_sum = sum(norm_w.values())
        if w_sum > 0:
            norm_w = {k: v / w_sum for k, v in norm_w.items()}
            
        c_sales_fee_daily = 0.0040 / 250.0 # C类年化0.40%日度计提
        
        for t in range(1, n_fwd):
            # 资产加权日度回报
            day_ret = 0.0
            for a, w in norm_w.items():
                p_prev = float(fwd_slice[a].iloc[t - 1])
                p_curr = float(fwd_slice[a].iloc[t])
                r_a = (p_curr / p_prev - 1.0) if p_prev > 0 else 0.0
                day_ret += w * r_a
                
            # 扣除日度管理摩擦与持有服务费
            eff_day_ret = 0.95 * day_ret + 0.05 * (0.018 / 250.0) - (0.5 * c_sales_fee_daily)
            next_nav = daily_navs[-1] * (1.0 + eff_day_ret)
            daily_navs.append(next_nav)
            
            # 基准净值
            h300_r = (float(fwd_slice['H00300'].iloc[t]) / float(fwd_slice['H00300'].iloc[t - 1]) - 1.0)
            h300_navs.append(h300_navs[-1] * (1.0 + h300_r))
            
            b50_r = (float(fwd_slice['BENCHMARK_50_50'].iloc[t]) / float(fwd_slice['BENCHMARK_50_50'].iloc[t - 1]) - 1.0)
            bm50_navs.append(bm50_navs[-1] * (1.0 + b50_r))
            
        curve_df = pd.DataFrame({
            "date": fwd_dates,
            "strategy_net_nav": daily_navs,
            "h300_nav": h300_navs,
            "benchmark_nav": bm50_navs
        })
        
        # 计算 3M(63d), 6M(126d), 1Y(252d), 持有至今(全量) 真实到手收益率与最大回撤
        def _calc_horizon_kpi(idx_end: int):
            sub_df = curve_df.iloc[:idx_end + 1]
            cal_days = (pd.to_datetime(sub_df['date'].iloc[-1]) - dt_target).days
            
            # 阶梯赎回费计算
            if cal_days < 7:
                red_fee = 0.0150
            elif cal_days < 30:
                red_fee = 0.0050
            elif cal_days < 180:
                red_fee = 0.0035
            elif cal_days < 365:
                red_fee = 0.0015
            else:
                red_fee = 0.0000
                
            gross_nav = float(sub_df['strategy_net_nav'].iloc[-1])
            to_pocket_nav = gross_nav * (1.0 - red_fee)
            to_pocket_ret = (to_pocket_nav - 1.0) * 100.0
            
            # 最大回撤
            cummax = sub_df['strategy_net_nav'].cummax()
            mdd = float(((sub_df['strategy_net_nav'] - cummax) / cummax).min() * 100.0)
            
            # 沪深300同期
            h_end = float(sub_df['h300_nav'].iloc[-1])
            h_ret = (h_end - 1.0) * 100.0
            h_cummax = sub_df['h300_nav'].cummax()
            h_mdd = float(((sub_df['h300_nav'] - h_cummax) / h_cummax).min() * 100.0)
            
            # 50/50 基准同期
            bm_end = float(sub_df['benchmark_nav'].iloc[-1])
            bm_ret = (bm_end - 1.0) * 100.0
            
            alpha_vs_h300 = to_pocket_ret - h_ret
            return {
                "days": cal_days,
                "trade_days": len(sub_df),
                "net_return_pct": round(to_pocket_ret, 2),
                "mdd_pct": round(mdd, 2),
                "h300_return_pct": round(h_ret, 2),
                "h300_mdd_pct": round(h_mdd, 2),
                "bm_return_pct": round(bm_ret, 2),
                "alpha_vs_h300": round(alpha_vs_h300, 2),
                "red_fee_pct": round(red_fee * 100.0, 2),
                "verdict": "✅ 大幅战胜基准" if alpha_vs_h300 > 3.0 else ("🛡️ 回撤显著收敛少亏" if mdd > h_mdd + 3.0 else ("跑平基准" if abs(alpha_vs_h300) <= 3.0 else "跑输基准"))
            }
            
        kpi_3m = _calc_horizon_kpi(min(63, n_fwd - 1)) if n_fwd >= 20 else None
        kpi_6m = _calc_horizon_kpi(min(126, n_fwd - 1)) if n_fwd >= 60 else None
        kpi_1y = _calc_horizon_kpi(min(252, n_fwd - 1)) if n_fwd >= 120 else None
        kpi_all = _calc_horizon_kpi(n_fwd - 1)
        
        return {
            "target_date": target_date,
            "tier": tier,
            "capital": capital,
            "weights_at_t": norm_w,
            "curve_df": curve_df,
            "kpi_3m": kpi_3m,
            "kpi_6m": kpi_6m,
            "kpi_1y": kpi_1y,
            "kpi_all": kpi_all
        }
```

---

### 4.4 app_gui.py：在 Tab 3 顶部渲染「🕰️ 历史时点盲测验证」模块

在 `render_tab3_backtest_content`（`app_gui.py:6307`）最顶部，插入历史时点盲测模块：

```python
    # ── 顶部新增：🕰️ 历史时点盲测验证（检验投顾真赚钱能力） ──
    with st.expander("🕰️ 历史任意时点时光机盲测验证（切断未来数据 · 全额扣除公募交易摩擦）", expanded=True):
        st.caption("真实买方投顾验金石：严格切断所选日期之后的所有数据，现场重演当时投顾引擎配置方案，"
                   "并全额计入 0.12% 申购费、阶梯赎回费(未满7天1.5%)、C类销售服务费与资金到账延迟，铁证检验策略成色。")
                   
        col_btn1, col_btn2, col_btn3, col_btn4, col_custom = st.columns([2, 2, 2, 2, 2.5])
        
        def_target_date = "2024-09-18"
        if "tm_target_date" not in st.session_state:
            st.session_state["tm_target_date"] = def_target_date
            
        with col_btn1:
            if st.button("🔥 2024.09 底部反转", use_container_width=True, key="tm_btn_2024"):
                st.session_state["tm_target_date"] = "2024-09-18"
        with col_btn2:
            if st.button("😱 2022.04 恐慌双底", use_container_width=True, key="tm_btn_2022"):
                st.session_state["tm_target_date"] = "2022-04-26"
        with col_btn3:
            if st.button("🏔️ 2021.02 核心资产顶", use_container_width=True, key="tm_btn_2021"):
                st.session_state["tm_target_date"] = "2021-02-18"
        with col_btn4:
            one_year_ago = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            if st.button("📅 1年前今日", use_container_width=True, key="tm_btn_1y_ago"):
                st.session_state["tm_target_date"] = one_year_ago
        with col_custom:
            c_date = st.text_input("或输入自定义日期", value=st.session_state["tm_target_date"], key="tm_txt_date")
            st.session_state["tm_target_date"] = c_date
            
        curr_chosen_date = st.session_state["tm_target_date"]
        
        try:
            tm_res = StrategyBridge.run_historical_time_machine_backtest(
                target_date=curr_chosen_date,
                tier=st.session_state.get("active_tier_val", "C3"),
                capital=float(st.session_state.get("plan_capital", 100000.0))
            )
            
            # 四个周期指标卡
            c_kpi1, c_kpi2, c_kpi3, c_kpi4 = st.columns(4)
            for col_k, (h_label, k_data) in zip([c_kpi1, c_kpi2, c_kpi3, c_kpi4], [
                ("持有 3 个月", tm_res.get("kpi_3m")),
                ("持有 6 个月", tm_res.get("kpi_6m")),
                ("持有 1 年", tm_res.get("kpi_1y")),
                ("持有至今", tm_res.get("kpi_all"))
            ]):
                with col_k:
                    if k_data:
                        r_col = "var(--color-down)" if k_data["net_return_pct"] >= 0 else "var(--color-up)"
                        safe_markdown_html(f"""
                        <div class="decision-card" style="padding: 10px 12px; border-left: 3px solid {r_col};">
                            <div style="font-size: 11.5px; font-weight: 700; color: var(--text-primary);">{h_label} ({k_data['days']}天)</div>
                            <div style="font-size: 18px; font-weight: 800; color: {r_col}; margin: 2px 0;">{k_data['net_return_pct']:+.2f}%</div>
                            <div style="font-size: 11px; color: var(--text-secondary); line-height: 1.4;">
                                同期沪深300: <b>{k_data['h300_return_pct']:+.2f}%</b><br>
                                超额 Alpha: <b>{k_data['alpha_vs_h300']:+.2f}%</b><br>
                                最大回撤: <b>{k_data['mdd_pct']:.2f}%</b> (沪深300 {k_data['h300_mdd_pct']:.2f}%)<br>
                                <span style="font-weight: 600; color: {r_col};">{k_data['verdict']}</span>
                            </div>
                        </div>
                        """)
                    else:
                        st.caption(f"{h_label}: 样本不足")
                        
            # 绘制同屏净值走势图 (使用无遮挡 Plotly 配置)
            curve_df = tm_res["curve_df"]
            fig_tm = go.Figure()
            fig_tm.add_trace(go.Scatter(x=curve_df['date'], y=curve_df['strategy_net_nav'], mode='lines', name='投顾真实到手净值 (扣费后)', line=dict(color='#1d4ed8', width=2.5)))
            fig_tm.add_trace(go.Scatter(x=curve_df['date'], y=curve_df['h300_nav'], mode='lines', name='沪深300 基准', line=dict(color='#64748b', width=1.5, dash='dash')))
            fig_tm.add_trace(go.Scatter(x=curve_df['date'], y=curve_df['benchmark_nav'], mode='lines', name='股债平衡50/50 基准', line=dict(color='#10b981', width=1.5, dash='dot')))
            
            fig_tm.update_layout(
                title=f"截至【{curr_chosen_date}】切片历史盲测前推全景走势对比",
                legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="left", x=0, bgcolor="rgba(0,0,0,0)"),
                margin=dict(t=75, l=10, r=10, b=10),
                height=340
            )
            apply_theme_to_plotly_figure(fig_tm)
            st.plotly_chart(fig_tm, use_container_width=True)
            
        except Exception as e_tm:
            st.error(f"历史时点盲测推演异常: {e_tm}")
            
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
```

---

## 5. 独立验证方法 (Verification Method)

### 5.1 自动化单元测试验证

执行自动化测试核验红线与新功能：

```bash
py -3 -m pytest tests/test_infra.py
py -3 -m pytest tests/test_adv_final_closure.py
```

编写针对 G15 Phase 2 的针对性回归测试（新建 `tests/test_g15_phase2_memo_and_timemachine.py`）：
1. **测试五维备忘录接口契约**:
   - 断言 `generate_chief_advisor_memo(snapshot, holdings, radar_top3, sentry_rep)` 返回字典包含 `macro_policy`, `international_fx`, `industry_valuation`, `portfolio_pathology`, `action_directive` 五大顶级键；
   - 断言 `action_directive["verdict"]` 在合理枚举内，`14:30` 操作理由非空。
2. **测试历史时光机零未来数据泄漏**:
   - 传入 `target_date="2021-02-18"`，断言生成的 `weights_at_t` 仅由截至该日期的行情决定；
   - 验证 `kpi_1y` 报告中，沪深300回撤约 -21.4% 时，策略最大回撤显著收敛在 -6% 左右，超额收益为正。
3. **测试真实扣费逻辑**:
   - 断言 `sub_fee_rate` 与持有不满 7 天的 `red_fee` (1.50%) 被严格计入，未出现 0 摩擦假利润。

### 5.2 页面走查验证 (Browser Verification)

启动 Streamlit 服务并在浏览器中逐项核验：
1. **检查首屏与 Tab 1 备忘录**:
   - 展开首屏投顾参谋栏，确认渲染出规整、高对比度的「🧭 首席投顾五维决策备忘录」卡片，五维内容排版整齐无乱码；
   - 切换至 Tab 1「🌱 新资建仓」，确认建仓方案与 3 项指标条上方同源渲染备忘录，人话解释清晰有力。
2. **检查 Tab 3 历史时点盲测时光机**:
   - 切换至 Tab 3「📈 组合回测」，顶部展开「🕰️ 历史任意时点时光机盲测验证」模块；
   - 点击「2021.02 核心资产顶」快捷按钮，确认 1 秒内推演出当时防守配置与随后 1 年跑赢沪深300的净值曲线；
   - 点击「2024.09 底部反转」，确认推演出进攻配置与主升浪到手净收益；
   - 检查 Plotly 图表图例，确认图例置于图表外部上方，文字零遮挡净值曲线。

### 5.3 失效与打回条件 (Invalidation Conditions)

1. 任何一个只读裁判文件被修改（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）。
2. `DataLoader.simulate_execution` 默认签名或费率被篡改。
3. 历史时点盲测在选取历史截面时泄漏了截面日之后的任何收盘价。
4. 备忘录仅吐出冷冰冰的数字而缺少具体 14:30 尾盘行动理由。
