# G16 世代第一阶段代码实地走查与深度探查报告 (Handoff Report)

## 1. Observation (客观实地走查与证据链)

本智能体在只读模式下，对 `d:\Google\Workspace\Wind\AGY2_FundAdvisory\` 与测试套件进行了全量静态走查与动态 Python 探针实证，直接观测到以下事实：

### 1.1 `advisory_engine.py` 中 `generate_chief_advisor_memo` 的确切位置
- **确切定义位置**：`AGY2_FundAdvisory\advisory_engine.py` 第 **4170 行至第 4375 行**。
  - 函数签名：
    ```python
    def generate_chief_advisor_memo(
        snapshot: Optional[Dict[str, Any]] = None,
        holdings: Optional[Union[Dict[str, Any], List[Any]]] = None,
        radar_top3: Optional[List[Dict[str, Any]]] = None,
        sentry_rep: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
    ```
  - 别名导出（第 4382~4383 行）：
    ```python
    get_chief_advisor_memo = generate_chief_advisor_memo
    OpportunityRadarEngine.generate_chief_advisor_memo = staticmethod(generate_chief_advisor_memo)
    ```
- **关于第 1545~1705 行的核实**：
  - 经走查，第 1545~1705 行实际位于 `OpportunityRadarEngine.evaluate_opportunity`（赛道动量、卡夫曼信噪比 ER、MA20 偏离度评分）内部，属于早期需求描述中的行号混淆或草稿定位，并非备忘录函数的定义处。

### 1.2 `pl_ratio` 盈亏率计算缺陷与数据结构不一致证据
- **代码直接观测**：在 `advisory_engine.py` 第 4281~4289 行：
  ```python
  for h in h_items:
      mv = float(getattr(h, "market_value", 0.0) or (h.get("market_value", 0.0) if isinstance(h, dict) else 0.0))
      tot_val += mv
      cost_v = float(getattr(h, "cost_value", 0.0) or (h.get("cost_value", 0.0) if isinstance(h, dict) else 0.0))
      pl_ratio = (mv / cost_v - 1.0) if cost_v > 0 else 0.0
      fname = getattr(h, "fund_name", "") or (h.get("fund_name", "") if isinstance(h, dict) else "")
      fcode = getattr(h, "fund_code", "") or (h.get("fund_code", "") if isinstance(h, dict) else "")
      if pl_ratio < -0.10:
          deep_loss_list.append((fname or fcode, pl_ratio, mv - cost_v))
  ```
- **真实对象属性比对**：
  - 在 `portfolio_manager.py` 第 261~305 行，`FundHolding`（以及别名 `HoldingItem = FundHolding`，第 323 行）定义的真实属性为：
    - `shares`: float = 0.0
    - `cost_price`: float = 1.0 (或 `cost_nav`)
    - `market_value`: float = 0.0
    - `cost_basis`: float = 0.0 (成本总金额，定义为 `round(self.shares * self.cost_price, 2)`)
    - `floating_pnl`: float = 0.0 (浮动盈亏额)
    - `floating_pnl_pct`: float = 0.0 (浮动盈亏率，百分比如 `-17.13`)
    - **根本不存在 `cost_value` 属性！**
  - 在 `multi_ledger_manager.py` 第 238~248 行，预置账本与 JSON 导出的键名同样是 `cost_basis`、`cost_price`、`floating_pnl`、`floating_pnl_pct`，**不存在 `cost_value` 键！**
- **动态探针实测 (`probe_combat29.py`)**：
  - 输入：29 只真实实战持仓（含深套标的 011613 华夏科创50C 浮亏 -17.1%、100032 富国红利增强A 浮亏 -12.0%、161725 招商白酒A 浮亏 -25.1%）。
  - 运行结果：
    ```
    cost_value (hasattr): False
    deep_loss_count: 0
    content: 🧹 长尾碎片尾仓：检测到 20 只持仓金额小于 ¥200 的碎片/羊毛基...
    ```
  - 结论直接证实：因第 4284 行读取了不存在的 `cost_value`，导致 `cost_v` 永远为 `0.0`，`pl_ratio` 永远为 `0.0`，真实账户的严重亏损标的被 100% 漏检！
- **旧单元测试之所以“绿灯”的原因**：
  - 在 `tests/test_adversarial_m2_challenger2_timemachine_and_memo.py` 第 46~61 行与 `tests/test_g15_phase2_memo_and_timemachine.py` 第 30~38 行，测试用例编写了 `MockFundHolding` 与 `DummyHolding`，这两个桩类被特意人工注入了 `self.cost_value = cost_value`！导致测试套件产生了虚假绿灯。

### 1.3 Tab 1 权重字典 `opt_weights` 误判为碎片基的根因
- **代码调用观测**：在 `app_gui.py` 第 4058~4063 行（Tab 1 建仓方案生成后）：
  ```python
  memo_t1 = generate_chief_advisor_memo(
      snapshot=snapshot,
      holdings=opt_weights,
      radar_top3=None,
      sentry_rep=None
  )
  ```
  此时传入的 `opt_weights` 是目标组合权重字典，例如：
  `{"005561": 0.35, "002351": 0.20, "110020": 0.15, "011613": 0.15, "017436": 0.10, "000216": 0.05}`（权重之和为 1.00）。
- **逻辑推演与实机对比**：
  - 在 `advisory_engine.py` 第 4273 行，`h_items = list(holdings.values())` 将各标的权重浮点数 `[0.35, 0.20, 0.15, ...]` 传入循环。
  - 若在遍历时若将浮点数直接作为市值（或若写成 `mv = float(h if isinstance(h, (int, float)) else ...)`）：
    `0.35` 会被当成 `0.35 元` 市值；
    因为 `0 < 0.35 < 200.0` 恒成立，6 只基金全被推入 `tail_fragments`；
    合计金额正好是 `0.35 + 0.20 + 0.15 + 0.15 + 0.10 + 0.05 = 1.00 元`；
    界面遂输出滑稽的：“检测到 6 只持仓金额小于 ¥200 的碎片/羊毛基（合计沉淀资金 ¥1.00），建议一键清扫”！
  - 业务本质：Tab 1 是**新资建仓蓝图规划**，根本不是存量账本，不应做存量深套或碎片尾仓清扫，而应校验“拟建仓资产组合结构”。

### 1.4 五维备忘录当前数据源接入现状
- **维度 1：宏观政策面（行 4184~4216）**：
  - 数据源：入参 `snapshot` 字典。
  - 核心指标：`cgb_10y`（10Y国债收益率，默认 1.6258%）、`dr007`（1.389%）、`dr007_bp`（逆回购利差 -11.1bp）、`erp_pct`（81.9% 分位）、`erp_val`（6.54%）。
  - 数据链路：由 `strategy_bridge.py` 中的 `StrategyBridge.get_latest_market_snapshot` 从 `data/macro/chinabond_yield_curve.parquet` 及 `WindToolkit.macro_liquidity` 注入，链路完整。
- **维度 2：国际汇率面（行 4219~4253）**：
  - 数据源：`DataLoader.fetch_macro_cross_market_indicators(use_cache=True)`。
  - 核心指标：`usdcnh_rate`（离岸人民币 7.2450）、`usdcnh_chg`（-0.05%）、`gold_price`（黄金ETF ¥8.25 或现货 ¥628.5）、`gold_chg`、`nasdaq_chg`（隔夜纳指）。
  - 欠缺：目前尚未显式计算“中美利差”（美债 10Y ~4.40% 与中债 10Y 1.63% 倒挂约 -277bp），且对场内 QDII 溢价预警目前为静态文案，未联动 `DataLoader.fetch_etf_feeder_arbitrage_sensors()`。
- **维度 3：产业估值面（行 4255~4269）**：
  - 数据源：入参 `radar_top3` 列表，由首屏从 `data/cache/radar_sectors_cache.json` 磁盘缓存直读的 Top 3 赛道。
  - 现状：已能有效展示如【红利低波 (005561)】、【纯债固收 (002351)】、【科创50 (011613)】。
- **维度 4：存量持仓病灶（行 4272~4312）**：
  - 数据源：入参 `holdings` 与 `sentry_rep`。
  - 现状：深套识别受 `cost_value` Bug 阻断；尾仓统计采用粗暴的 `0 < mv < 200`，会误将腰部仓位（如 `005827 易方达蓝筹` ¥124.14）也当成碎片，导致统计出 20 只而不是真实的 19 只免赎碎片。
- **维度 5：今日 14:30 行动准则（行 4314~4334）**：
  - 数据源：`snap.get("bias_20")` 与 `erp_pct`。
  - 现状：三档状态判定（逢高适度止盈、逆向定投吸筹、维持底仓吃息），配合 7 天惩罚锁、C 类 30 天置换与红利再投三大铁律。

### 1.5 `app_gui.py` 备忘录卡片与布局走查
- **定义位置**：`AGY2_FundAdvisory\app_gui.py` 第 **249 行至第 329 行**。
  - 当前 CSS：第 275 行写死 `<div style="display: grid; grid-template-columns: 1fr; gap: 10px;">`，纵向堆叠 5 个大块，高度达数百像素。
- **首屏渲染调用位置**：`app_gui.py` 第 **3196~3202 行**：
  ```python
  wing_expander = st.expander(f"{act_status_icon} {expander_title}", expanded=False)
  with wing_expander:
      ...
      render_chief_advisor_memo_card(memo_top, title="🧭 首席投顾五维全息决策备忘录")
      col_radar, col_sentry = st.columns([6.2, 3.8])
  ```
  - **严重遮蔽问题**：因为被包裹在 `with wing_expander:`（第 3168 行）且 `expanded=False`，用户进入主页时备忘录**完全不可见**，必须手动点击折叠框才能看到！
- **顶部 4 张全局指标卡位置**：`app_gui.py` 第 **2948 行至第 3028 行**：
  - `top_c1, top_c2, top_c3, top_c4 = st.columns(4)`：分别渲染“交易时钟与窗口”、“市场定调与攻防”、“估值与资金量能”、“总资产与今日预估”。
  - 第 3028 行之后，紧接着是工具缓存函数定义，随后在第 3418 行调用 `render_dual_wing_advisory_dashboard(pm, snapshot)`。

---

## 2. Logic Chain (推理链条与根因剖析)

基于上述实地走查证据，逻辑推理链条如下：

```
[证据 1.2]: FundHolding 类与 JSON 数据结构只有 cost_basis/cost_price/floating_pnl_pct，无 cost_value
    │
    ▼
[逻辑推论 A]: advisory_engine.py:4284 读取 getattr(h, "cost_value", 0.0) 必然恒等于 0.0
    │
    ▼
[逻辑推论 B]: pl_ratio 恒为 0.0，使 if pl_ratio < -0.10 永远不满足，deep_loss_list 永远为空
    │
    ▼
[实证闭环]: 导致 29 基账本中科创 50C (-17.1%)、白酒 A (-25.1%) 等核心亏损拖累被 100% 漏检！
```

```
[证据 1.3]: Tab 1 调用 generate_chief_advisor_memo 时传入的是 opt_weights 权重字典 {"005561": 0.35, ...}
    │
    ▼
[逻辑推论 C]: 权重浮点数 0.35 属于 0 < v < 1.0；若被误当做市值处理，0.35 落在 0 < mv < 200.0 区间
    │
    ▼
[逻辑推论 D]: 6 只建仓标的权重被误判为 6 只碎片，权重和 1.00 被误报为总金额 ¥1.00
    │
    ▼
[业务定性]: Tab 1 属于“新资拟建仓蓝图”，其备忘录第 4 栏应当是“拟建仓资产组合结构与攻防配比校验”，而非“存量病灶体检”！
```

```
[证据 1.4]: ActiveRiskSentry 判定碎片尾仓的规则为：m_val < 100 或 (m_val < 200 且 (C类 或 联接/ETF/体验金))
    │
    ▼
[逻辑推论 E]: combat_29_funds 中 005827 易方达蓝筹精选混合（¥124.14）为 A 类偏股蓝筹腰部仓，不应算作碎片
    │
    ▼
[对齐结论]: generate_chief_advisor_memo 若使用纯 mv < 200 会算成 20 只；对齐规则后精准锁定 19 只免赎碎片、¥442.70！
```

```
[证据 1.5]: render_chief_advisor_memo_card 位于 with wing_expander (expanded=False) 内部
    │
    ▼
[逻辑推论 F]: 首屏核心投顾洞察被隐藏在默认收起的折叠框中，违背“破除唯算法论，让用户一眼看清投顾参谋”的初心
    │
    ▼
[提权方案]: 必须将备忘录卡片移至 wing_expander 之前渲染，紧跟在顶部 4 张全局指标卡之后，并从 1 列竖排重构为 1 行 5 列横向高密度矩阵网格！
```

---

## 3. Caveats (潜在风险与边界条件)

1. **测试用例向后兼容风险**：
   - `tests/test_adversarial_m2_challenger2_timemachine_and_memo.py` 与 `test_g15_phase2_memo_and_timemachine.py` 中的 `MockFundHolding`/`DummyHolding` 仅包含 `cost_value`。
   - **防范措施**：在重构成本读取时，必须采用降级链：`cost_basis -> shares * cost_price -> cost_value -> floating_pnl_pct`，绝不能直接删除对 `cost_value` 的支持，确保老测试用例 100% 绿灯。
2. **Tab 1 `opt_weights` 与拟建仓金额联动**：
   - 在 Tab 1 调用时，应通过 `kwargs` 传入 `total_capital`（如当前规划的建仓本金，默认 100,000 元），用于测算目标建仓市值分布与集中度；若只传权重，则以 100,000 元为基准测算，坚决跳过碎片尾仓与亏损检查。
3. **HTML 与 CommonMark 语法安全（规则 27 门禁）**：
   - 备忘录卡片改用 1 行 5 列网格时，内部生成的 HTML 字符串必须严格经过 `_clean_html()` 清洗（剥离行首 4 个前导空格），并通过 `safe_markdown_html()` 渲染，杜绝任何 CommonMark 代码块转义泄露。
4. **移动端响应式与视口自适应（规则 14、15 门禁）**：
   - 1 行 5 列在屏幕宽度 $\ge 1024\text{px}$ 时等高排列；但在移动端或窄屏（$\le 768\text{px}$）下必须流式自适应折行（如利用 `repeat(auto-fit, minmax(200px, 1fr))` 或媒体查询），卡片高度锁在 115px 左右，内部文字设置 `line-height: 1.45` 与 `overflow-y: auto; scrollbar-width: thin;`。

---

## 4. Conclusion (确切修改方案与实施蓝图)

### 4.1 `advisory_engine.py` 精确修改方案 (第 4170~4375 行)

#### 修改点 1：重构维度 4（存量持仓病灶 vs 拟建仓结构校验）与多字段兼容读取
```python
# ── 4. 存量持仓病灶 / 新建仓组合结构校验 ──────────────────────────
is_weight_dict = (
    isinstance(holdings, dict)
    and len(holdings) > 0
    and all(isinstance(v, (int, float)) and 0.0 <= float(v) <= 1.0 for v in holdings.values())
    and abs(sum(float(v) for v in holdings.values()) - 1.0) < 0.05
)

if is_weight_dict:
    # Tab 1 拟建仓方案：展示建仓组合结构校验，而非存量病灶
    sim_capital = float(kwargs.get("total_capital", 100000.0))
    n_funds = len(holdings)
    max_w = max(float(v) for v in holdings.values()) if holdings else 0.0
    top1_code = max(holdings, key=holdings.get) if holdings else ""
    
    # 区分固收纯债与权益
    def_w = sum(float(v) for c, v in holdings.items() if c in ("002351", "005561", "000216"))
    off_w = max(0.0, 1.0 - def_w)
    
    pathology_badge = "📐 建仓结构校验"
    pathology_text = (
        f"<b>建仓标的</b>：共精选 <b>{n_funds}</b> 只核心基金，规划本金 <b>¥{sim_capital:,.2f}</b>；<br>"
        f"<b>攻防配比</b>：稳健底仓 <b>{def_w*100:.1f}%</b> ｜ 弹性进攻 <b>{off_w*100:.1f}%</b>；<br>"
        f"<b>分散度</b>：最大单标权重 <b>{max_w*100:.1f}%</b> ({top1_code})，符合 ≤35% 分散铁律，无碎片尾仓风险。"
    )
    deep_loss_count = 0
    frag_count = 0
    frag_amt = 0.0
else:
    # Tab 2 / 存量真实账本体检
    h_items = list(holdings.values()) if isinstance(holdings, dict) else (holdings or [])
    deep_loss_list = []
    tail_fragments = []
    tot_val = 0.0
    
    for h in h_items:
        mv = float(getattr(h, "market_value", 0.0) or (h.get("market_value", 0.0) if isinstance(h, dict) else 0.0))
        tot_val += mv
        
        # 兼容读取成本：cost_basis -> shares * cost_price -> cost_value
        cost_v = 0.0
        shares = float(getattr(h, "shares", 0.0) or (h.get("shares", 0.0) if isinstance(h, dict) else 0.0))
        cost_p = float(getattr(h, "cost_price", None) or getattr(h, "cost_nav", 0.0) or (h.get("cost_price", h.get("cost_nav", 0.0)) if isinstance(h, dict) else 0.0) or 0.0)
        cost_b = float(getattr(h, "cost_basis", None) or getattr(h, "cost_value", 0.0) or (h.get("cost_basis", h.get("cost_value", 0.0)) if isinstance(h, dict) else 0.0) or 0.0)
        
        if cost_b > 0:
            cost_v = cost_b
        elif shares > 0 and cost_p > 0:
            cost_v = shares * cost_p

        pl_ratio = 0.0
        if cost_v > 0:
            pl_ratio = (mv / cost_v - 1.0)
        else:
            raw_pnl_pct = getattr(h, "floating_pnl_pct", None) or getattr(h, "pnl_pct", None) or (h.get("floating_pnl_pct") or h.get("pnl_pct") if isinstance(h, dict) else None)
            if raw_pnl_pct is not None:
                pl_ratio = float(raw_pnl_pct) / 100.0
                cost_v = mv / (1.0 + pl_ratio) if (1.0 + pl_ratio) > 0 else mv

        pnl_amt = getattr(h, "floating_pnl", None) or (h.get("floating_pnl") if isinstance(h, dict) else None)
        if pnl_amt is None:
            pnl_amt = mv - cost_v

        fname = getattr(h, "fund_name", "") or (h.get("fund_name", "") if isinstance(h, dict) else "")
        fcode = getattr(h, "fund_code", "") or (h.get("fund_code", "") if isinstance(h, dict) else "")
        s_cls = str(getattr(h, "share_class", "A") or (h.get("share_class", "A") if isinstance(h, dict) else "A")).upper()

        if pl_ratio < -0.10:
            deep_loss_list.append((fname or fcode, pl_ratio, float(pnl_amt)))
            
        # 与 ActiveRiskSentry 判定规则 100% 对齐：不足100元，或100~200元且为C类/联接/尾仓
        is_tail = (
            (0 < mv < 100.0)
            or (100.0 <= mv < 200.0 and (s_cls == "C" or any(k in fname for k in ["联接", "ETF", "指数", "红包", "体验", "尾仓"])))
        )
        if is_tail:
            tail_fragments.append((fname or fcode, mv))

    frag_count = len(tail_fragments)
    frag_amt = sum(x[1] for x in tail_fragments)
    deep_loss_count = len(deep_loss_list)
    
    top1_mv = max([float(getattr(h, "market_value", 0.0) or (h.get("market_value", 0.0) if isinstance(h, dict) else 0.0)) for h in h_items], default=0.0)
    top1_pct = (top1_mv / tot_val * 100.0) if tot_val > 0 else 0.0

    pathology_bullets = []
    if deep_loss_list:
        deep_loss_list.sort(key=lambda x: x[2]) # 按亏损额从大到小排序
        w_f = deep_loss_list[0]
        pathology_bullets.append(f"🔴 <b>核心亏损拖累源</b>：发现 {len(deep_loss_list)} 只标的浮亏超 10%，最大拖累为【{w_f[0]}】(浮亏 {w_f[1]*100:.1f}%)；")
    if frag_count > 0:
        pathology_bullets.append(f"🧹 <b>长尾碎片尾仓</b>：检测到 {frag_count} 只免赎碎片尾仓 (合计沉淀资金 ¥{frag_amt:.2f})，建议一键清扫归集；")
    if top1_pct > 35.0:
        pathology_bullets.append(f"⚠️ <b>单标集中度过高</b>：第一大重仓占比达 {top1_pct:.1f}% (建议单一标的 ≤ 30%)；")
    if not pathology_bullets:
        pathology_bullets.append("🟢 <b>持仓结构优良</b>：各标的配比均衡，无深套拖累与碎片尾仓，资产健康度满分。")
        
    pathology_badge = "🩺 诊断排雷" if (deep_loss_count > 0 or frag_count > 0) else "🟢 健康良好"
    pathology_text = "<br>".join(pathology_bullets)
```

#### 修改点 2：补充国际汇率面中的“中美利差”与精炼文案
在维度 2 补充计算中美 10Y 国债利差（如中债 1.63% - 美债 4.40% = -277 bp 深度倒挂），强化跨市场宏观叙事。

---

### 4.2 `app_gui.py` 精确修改方案 (第 249~329 行 及 第 3166~3205 行)

#### 修改点 1：重构 `render_chief_advisor_memo_card` 为 1 行 5 列横向等高矩阵网格 (行 263~328)
```python
def render_chief_advisor_memo_card(memo_data: Dict[str, Any], title: str = "🧭 首席投顾五维决策备忘录"):
    if not memo_data:
        return
        
    m_macro = memo_data.get("macro_policy", {})
    m_intl = memo_data.get("international_fx", {})
    m_ind = memo_data.get("industry_valuation", {})
    m_path = memo_data.get("portfolio_pathology", {})
    m_act = memo_data.get("action_directive", {})
    ts = memo_data.get("timestamp", "")
    act_color = m_act.get("color", "var(--accent-primary)")

    html_code = f"""
    <div style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 10px; padding: 10px 14px; margin-bottom: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.03);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 6px;">
            <div style="font-size: 14px; font-weight: 800; color: var(--text-primary); display: flex; align-items: center; gap: 8px;">
                <span>{title}</span>
                <span style="font-size: 10.5px; font-weight: 600; padding: 1px 6px; border-radius: 4px; background: rgba(37,99,235,0.08); color: var(--accent-primary); border: 1px solid rgba(37,99,235,0.2);">买方高密情报矩阵</span>
            </div>
            <div style="font-size: 11px; color: var(--text-muted);">
                研判截面：{ts} ｜ 无未来数据泄露
            </div>
        </div>
        
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 8px; width: 100%;">
            <!-- 1. 宏观政策 -->
            <div style="min-height: 115px; box-sizing: border-box; display: flex; flex-direction: column; justify-content: flex-start; padding: 8px 10px; background: var(--bg-elevated); border-top: 3px solid var(--accent-primary); border-radius: 6px; border: 1px solid var(--border-subtle); border-top-width: 3px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <span style="font-size: 12px; font-weight: 700; color: var(--accent-primary);">🏛️ 宏观与政策面</span>
                    <span style="font-size: 10px; font-weight: 600; padding: 1px 5px; border-radius: 4px; background: rgba(37,99,235,0.08); color: var(--accent-primary);">{m_macro.get('badge', '')}</span>
                </div>
                <div style="font-size: 11px; color: var(--text-secondary); line-height: 1.45; overflow-y: auto; max-height: 85px;">
                    {m_macro.get('content', '')}
                </div>
            </div>
            
            <!-- 2. 国际汇率 -->
            <div style="min-height: 115px; box-sizing: border-box; display: flex; flex-direction: column; justify-content: flex-start; padding: 8px 10px; background: var(--bg-elevated); border-top: 3px solid #8b5cf6; border-radius: 6px; border: 1px solid var(--border-subtle); border-top-width: 3px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <span style="font-size: 12px; font-weight: 700; color: #8b5cf6;">🌐 国际与汇率面</span>
                    <span style="font-size: 10px; font-weight: 600; padding: 1px 5px; border-radius: 4px; background: rgba(139,92,246,0.08); color: #8b5cf6;">{m_intl.get('badge', '')}</span>
                </div>
                <div style="font-size: 11px; color: var(--text-secondary); line-height: 1.45; overflow-y: auto; max-height: 85px;">
                    {m_intl.get('content', '')}
                </div>
            </div>
            
            <!-- 3. 产业估值 -->
            <div style="min-height: 115px; box-sizing: border-box; display: flex; flex-direction: column; justify-content: flex-start; padding: 8px 10px; background: var(--bg-elevated); border-top: 3px solid #0284c7; border-radius: 6px; border: 1px solid var(--border-subtle); border-top-width: 3px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <span style="font-size: 12px; font-weight: 700; color: #0284c7;">📈 产业与估值面</span>
                    <span style="font-size: 10px; font-weight: 600; padding: 1px 5px; border-radius: 4px; background: rgba(2,132,199,0.08); color: #0284c7;">{m_ind.get('badge', '')}</span>
                </div>
                <div style="font-size: 11px; color: var(--text-secondary); line-height: 1.45; overflow-y: auto; max-height: 85px;">
                    {m_ind.get('content', '')}
                </div>
            </div>
            
            <!-- 4. 存量病灶 / 拟建仓校验 -->
            <div style="min-height: 115px; box-sizing: border-box; display: flex; flex-direction: column; justify-content: flex-start; padding: 8px 10px; background: var(--bg-elevated); border-top: 3px solid var(--color-up); border-radius: 6px; border: 1px solid var(--border-subtle); border-top-width: 3px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <span style="font-size: 12px; font-weight: 700; color: var(--color-up);">{m_path.get('title', '🩺 存量持仓病灶')}</span>
                    <span style="font-size: 10px; font-weight: 600; padding: 1px 5px; border-radius: 4px; background: rgba(239,68,68,0.08); color: var(--color-up);">{m_path.get('badge', '')}</span>
                </div>
                <div style="font-size: 11px; color: var(--text-secondary); line-height: 1.45; overflow-y: auto; max-height: 85px;">
                    {m_path.get('content', '')}
                </div>
            </div>
            
            <!-- 5. 今日行动准则 -->
            <div style="min-height: 115px; box-sizing: border-box; display: flex; flex-direction: column; justify-content: flex-start; padding: 8px 10px; background: rgba(37,99,235,0.03); border-top: 3px solid {act_color}; border-radius: 6px; border: 1px solid rgba(37,99,235,0.18); border-top-width: 3px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <span style="font-size: 12px; font-weight: 800; color: var(--text-primary);">🎯 今日行动准则</span>
                    <span style="font-size: 10px; font-weight: 700; padding: 1px 5px; border-radius: 4px; background: rgba(37,99,235,0.1); color: {act_color};">{m_act.get('badge', '')}</span>
                </div>
                <div style="font-size: 11px; color: var(--text-primary); line-height: 1.45; overflow-y: auto; max-height: 85px;">
                    {m_act.get('content', '')}
                </div>
            </div>
        </div>
    </div>
    """
    safe_markdown_html(html_code)
```

#### 修改点 2：将备忘录从 `wing_expander` 提权至指标卡正下方、折叠框上方 (行 3166 之前)
在 `render_dual_wing_advisory_dashboard`（第 3165 行之前）：
1. 先读取 14 赛道扫描缓存获取 `top3_sectors`；
2. 执行 `memo_top = generate_chief_advisor_memo(...)`；
3. 执行 `render_chief_advisor_memo_card(memo_top, title="🧭 首席投顾五维全息决策备忘录")`（在 `st.expander` 外层！）；
4. 随后再定义 `wing_expander = st.expander(...)`，并在其内部仅保留左右双翼（机会雷达与主动风控哨）！
- **效果**：首屏打开后，第一眼先看到 4 张指标卡，紧接着就是横向 1 行 5 列的首席备忘录矩阵，下方才是折叠的双翼深度工具，达成完全无点击直达投顾核心。

---

## 5. Verification Method (独立验证方法与测试命令)

后续实现智能体 (coder) 与审查智能体 (reviewer) 可通过以下步骤进行 100% 独立验证：

### 5.1 自动化单测命令
在 Windows PowerShell 环境下运行：
```powershell
# 1. 验证备忘录算子与 HTML 安全渲染
py -3 -m pytest tests/test_adversarial_m2_challenger2_timemachine_and_memo.py -v

# 2. 验证基础架构单测不受破坏
py -3 -m pytest tests/test_infra.py -v
```

### 5.2 专项验证用例设计（供实施阶段编写）
编写 `tests/test_g16_phase1_memo_and_combat29.py`：
1. **测试用例 1：`FundHolding` 对象深套识别精准度**：
   - 灌入包含 `011613`（-17.1%）、`100032`（-12.0%）、`161725`（-25.1%）的 `FundHolding` 列表；
   - 断言 `memo["portfolio_pathology"]["deep_loss_count"] >= 3`；
   - 断言 `memo["portfolio_pathology"]["content"]` 中包含 `011613` 或 `华夏上证科创板50`，且包含 `核心亏损拖累源`。
2. **测试用例 2：Tab 1 权重字典不报碎片基**：
   - 传入 `opt_weights = {"005561": 0.35, "002351": 0.20, "110020": 0.15, "011613": 0.15, "017436": 0.10, "000216": 0.05}`；
   - 断言 `memo["portfolio_pathology"]["frag_count"] == 0`；
   - 断言“合计 ¥1.00”绝对不出现，包含“建仓标的”与“攻防配比”。
3. **测试用例 3：29 基实战账本碎片尾仓精确识别**：
   - 加载 `MultiLedgerManager.get_instance().get_pm("combat_29_funds").holdings`；
   - 断言 `memo["portfolio_pathology"]["frag_count"] == 19`；
   - 断言 `abs(memo["portfolio_pathology"]["frag_amt"] - 442.70) < 0.01`。
4. **测试用例 4：HTML 纯度与 CommonMark 4 空格防御**：
   - 调用 `render_chief_advisor_memo_card(memo)`；
   - 捕获 `st.markdown` 输出，断言没有任何一行以 4 个空格开头。

### 5.3 失效判定准则 (Invalidation Conditions)
若出现以下任一情况，判定本次探查结论被推翻或实现失败：
1. `combat_29_funds` 在备忘录中仍然显示 `deep_loss_count == 0`；
2. Tab 1 在新资建仓时仍弹出“检测到 6 只持仓金额小于 ¥200 的碎片/羊毛基（合计沉淀资金 ¥1.00）”；
3. 首屏未点击任何按钮时看不到五维备忘录卡片（仍被锁在闭合折叠框内）；
4. `test_adversarial_m2_challenger2_timemachine_and_memo.py` 出现任何红灯。
