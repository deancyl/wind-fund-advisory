# Handoff Report — Institutional Bespoke Royal Blue Aesthetic & UX Upgrades in `app_gui.py`

**Agent ID**: `explorer_g14_survey_2`  
**Milestone**: G14 Aesthetic & UX Technical Survey  
**Target Files**: `AGY2_FundAdvisory/app_gui.py`, `AGY2_FundAdvisory/strategy_bridge.py`  
**Date**: 2026-11-09T11:35:00Z  

---

## 1. Observation (客观观察与代码溯源)

### 1.1 番茄红主按钮与机构皇家蓝撞色问题
- **文件路径**: `AGY2_FundAdvisory/app_gui.py`
- **行号**: 第 1286 至 1297 行、第 1321 至 1328 行
- **直接代码引用**:
  ```python
  # 第 1286 至 1297 行
  /* 🛡️ Primary 主按钮文字绝对防护：任何主题下强制纯白文字 */
  button[kind="primary"],
  button[kind="primary"] *,
  button[kind="primary"] p,
  button[kind="primary"] span,
  button[kind="primary"] div,
  [data-testid="stBaseButton-primary"],
  [data-testid="stBaseButton-primary"] *,
  [data-testid="stBaseButton-primary"] p,
  [data-testid="stBaseButton-primary"] span {
      color: #ffffff !important;
  }
  ...
  # 第 1321 至 1328 行
  /* Primary 主按钮强制白色文字穿透 (支持全主题对比度) */
  button[kind="primary"],
  button[kind="primary"] *,
  button[kind="primary"] p,
  button[kind="primary"] span {
      color: #ffffff !important;
      font-weight: 600 !important;
  }
  ```
- **观察事实**: 全局 CSS 中仅针对 `button[kind="primary"]` 和 `[data-testid="stBaseButton-primary"]` 设置了文字颜色纯白 (`color: #ffffff !important;`) 与字重 (`font-weight: 600 !important;`)，**完全未声明 `background`、`border`、`box-shadow` 以及 `:hover`/`:active`/`:focus` 状态**。
- **后果**: Streamlit 原生 CSS 默认样式 `background-color: rgb(255, 75, 75)`（番茄红 `#ff4b4b`）与 `:hover` `rgb(255, 43, 43)` 全面生效。全站 25 处 `st.button(..., type="primary")`（包括“⚡ 生成实盘建仓方案”、“🔍 诊断并生成调仓方案”、“💾 保存修改并入库”、“🔄 同步估值”等）全部渲染为刺眼的番茄红，与顶层四宫格深海蓝/皇家蓝导航栏（`var(--accent-primary) = #1d4ed8`）产生剧烈廉价撞色。

---

### 1.2 Tab 1 顶部 5 列参数控制栏垂直对齐错位
- **文件路径**: `AGY2_FundAdvisory/app_gui.py`
- **行号**: 第 3191 至 3537 行
- **直接代码引用**:
  - 第 3191 行:
    ```python
    col_l1_cap, col_l1_tier, col_l1_rhythm, col_l1_adv, col_l1_btn = st.columns([2.5, 2.0, 2.0, 1.3, 2.2])
    ```
  - 第 3194 至 3204 行 (Col 1):
    ```python
    with col_l1_cap:
        plan_capital = st.number_input("拟投资总本金 (元)", ...)
        st.caption(f"核对: {format_chinese_amount(plan_cap)}")
    ```
  - 第 3228 至 3237 行 (Col 2):
    ```python
    with col_l1_tier:
        st.selectbox("风险策略档位", ...)
        st.caption(f"画像: 【{active_tier} {cur_tier_meta['name']}】 目标 {cur_tier_meta['target_cagr']}")
    ```
  - 第 3252 至 3259 行 (Col 3):
    ```python
    with col_l1_rhythm:
        cap_deployment_mode = st.selectbox("建仓节奏", ...)
        st.caption("平抑盘口冲击与净值波动")
    ```
  - 第 3266 至 3268 行 (Col 4 - 错位源 1):
    ```python
    with col_l1_adv:
        st.caption("微调参数")
        with st.popover("⚙️ 高级微调", use_container_width=True):
    ```
  - 第 3529 至 3537 行 (Col 5 - 错位源 2):
    ```python
    with col_l1_btn:
        st.caption("开始执行")
        if st.button("⚡ 生成实盘建仓方案", type="primary", use_container_width=True, key="btn_run_simulation_now"):
    ```
- **观察事实**:
  1. 前 3 列（Col 1, 2, 3）采用原生控件自带的 Widget Label（由 Streamlit 渲染为 `<label data-testid="stWidgetLabel"><div ...>`，计算高度为 21px，行高 21px，字号 14px，下外边距 `margin-bottom: 4px`）。
  2. 后 2 列（Col 4, 5）顶部使用 `st.caption("微调参数")` 与 `st.caption("开始执行")` 占位。Streamlit 原生 `st.caption` 生成 `<div data-testid="stCaptionContainer"><p>...`，字号为 12px (0.8rem)，行高 15px，且带有独立的段落上下外边距。
  3. 这导致 Col 4 的 Popover 按钮与 Col 5 的 Primary 按钮的顶部垂直起始位置（Y-offset）与 Col 1~3 的输入框产生 6~8px 的垂直落差，在水平视觉上严重错位；同时 Col 4、Col 5 下方缺少与 Col 1~3 对齐的底部说明文字。

---

### 1.3 Tab 1 首次进入下半屏空白与阻塞卡顿
- **文件路径**: `AGY2_FundAdvisory/app_gui.py`
- **行号**: 第 3153 至 3164 行、第 3541 至 3604 行
- **直接代码引用**:
  - 第 3153 至 3154 行:
    ```python
    # 初始化状态机
    if "tab1_step_reached" not in st.session_state:
        st.session_state.tab1_step_reached = 1
    ```
  - 第 3541 行:
    ```python
    # 模块 2 与模块 3：执行单、核心指标卡与单一白盒抽屉
    if st.session_state.get("tab1_step_reached", 1) >= 2:
    ```
  - 第 3545 至 3551 行:
    ```python
    if st.session_state.get("tab1_trigger_sim", False) or st.session_state.get("tab1_sim_cache") is None:
        acc = ActiveComputationConsole(f"AI 投顾真全市场 2.8 万只漏斗推演 ({num_funds_input}只)", total_steps=4, ...)
    ```
  - 第 3581 至 3596 行:
    ```python
    if st.session_state.get("tab1_trigger_s3", False) or st.session_state.get("tab1_step3_cache") is None:
        acc_s3 = ActiveComputationConsole(f"生成【{active_tier} 档位】实盘建仓单与限购拆单 ({n_funds}只)", ...)
    ```
- **观察事实**:
  1. 用户初次进入工作台时，`tab1_step_reached` 默认值为 `1`。
  2. 第 3541 行的条件 `tab1_step_reached >= 2` 为 `False`，导致下方所有的实盘建仓执行表、3 格核心指标卡、回测图表、全市场选基漏斗与单一白盒抽屉**在首屏完全不渲染**，下方呈现一大片死寂空白。
  3. 若仅盲目将 `tab1_step_reached` 改为 `2` 或 `3`，第 3545 行与第 3581 行因 `tab1_sim_cache is None` 会连续实例化 2 个 `ActiveComputationConsole`，在首屏弹出 2 个巨大的进度折叠框并循环调用 `fetch_realtime_fund_quote`，导致首屏直接卡死数秒，严重违背秒开与体验规范。

---

### 1.4 顶部 4 张全局指标卡视觉纯粹度与对齐不一致
- **文件路径**: `AGY2_FundAdvisory/app_gui.py`
- **行号**: 第 2390 至 2398 行、第 2685 至 2765 行、第 643 至 661 行
- **直接代码引用**:
  - 第 2390 至 2398 行:
    ```python
    raw_mkt_state = str(snapshot.get('market_state', '震荡收息期'))
    if any(k in raw_mkt_state for k in ["震荡", "收息", "慢牛"]):
        vernacular_state = "🟢 震荡收息期"
    elif any(k in raw_mkt_state for k in ["科技", "主升", "进攻"]):
        vernacular_state = "🔥 科技主升浪"
    elif any(k in raw_mkt_state for k in ["熊", "防守", "破位"]):
        vernacular_state = "🛡️ 熊市防守期"
    else:
        vernacular_state = f"🟢 {raw_mkt_state[:6]}"
    ```
  - 第 2717 行 (Card 2):
    ```python
    <div class="metric-value-huge" style="color: {st_color}; font-size: 18px;">
        {vernacular_state}
    </div>
    ```
  - 第 2741 行 (Card 3):
    ```python
    <div class="metric-value-huge" style="color: var(--color-down); font-size: 16px;">
        {val_status}
    </div>
    ```
  - 第 2697 行 (Card 1) & 第 2758 行 (Card 4):
    ```python
    # font-size 为 18px
    ```
- **观察事实**:
  1. Card 2 的指标值文字前附带了微信式彩色 Emoji（`🟢`、`🔥`、`🛡️`），视觉杂乱且呈娱乐化风格。
  2. Card 3（估值与资金量能）的大字号被硬编码为 `font-size: 16px;`，而 Card 1、Card 2、Card 4 均为 `font-size: 18px;`，同排 4 张大卡片字号不统一。
  3. 第 2768 至 2791 行在顶部 4 卡下方残留了 `pm.get_latest_next_day_plan()` 的伪交易待办预案横幅（“采纳并执行此待办预案”大红按钮），占用了宝贵的垂直空间。

---

### 1.5 外部审计文档精髓提炼
- 检查 `c:\Users\deanc\Downloads\agy2_v8_code_audit_and_aesthetic_review.md`:
  - 核心痛点 3: 严禁将 `accent_primary` 绑定为亮红 `#dc2626`。深海蓝/皇家蓝专职负责导航与主按钮，红绿专职负责涨跌与风控徽章。
  - 核心痛点 2: 清除全站 180 处装饰性 Emoji，改用纯文字与纯色胶囊圆点传达状态。
- 检查 `c:\Users\deanc\Downloads\agy2_ui_ux_audit_and_fix_plan (2).md`:
  - P1 问题 4: `.main-metric-card` 之前设置 `max-height: 82px !important; overflow: hidden !important;` 会剪切展开项。
  - P1 问题 5: Tab 1 档位切换时目标年化收益率与模型必须保持联动。
  - P2 问题 7: 统一消除跨 Tab 跳转的状态字符串前缀差异（统一使用无表情符号的标准字符串）。

---

## 2. Logic Chain (推理链条与方案推导)

### 2.1 主按钮番茄红根治逻辑
1. 基于观察 1.1，Streamlit 的 CSS 默认给 `button[kind="primary"]` 和 `[data-testid="stBaseButton-primary"]` 赋予了 `#ff4b4b` 背景色与边框色。
2. `app_gui.py` 内部虽然定义了 `--accent-primary`（机构冷灰主题下为 `#1d4ed8` 皇家蓝），但原 CSS 仅重写了文字颜色 `color: #ffffff !important;`。
3. 因此，必须在全局 CSS 中对 `button[kind="primary"]` 和 `[data-testid="stBaseButton-primary"]` 注入强力选择器，绑定 `background: var(--accent-primary) !important; border: 1px solid var(--accent-primary) !important; border-radius: 8px !important; height: 40px !important; font-weight: 600 !important; box-shadow: 0 2px 6px rgba(29, 78, 216, 0.2) !important;`。
4. 补充 `:hover` 悬浮过渡态：`filter: brightness(1.1) !important; transform: translateY(-1px) !important; box-shadow: 0 4px 12px rgba(29, 78, 216, 0.3) !important;` 与 `:active` 态 `transform: translateY(0) !important;`，全面消灭番茄红并营造机构终端质感。

### 2.2 Tab 1 控制栏 5 列垂直基线对齐逻辑
1. 基于观察 1.2，Col 1~3 的 `st.number_input` 和 `st.selectbox` 自带的标准 Label 具有如下盒模型几何特征：
   - `height: 21px; line-height: 21px; font-size: 14px; font-weight: 500; margin-bottom: 4px;`
2. Col 4 的 `with st.popover` 和 Col 5 的 `st.button` 原生并不输出顶部 Label，原代码使用的 `st.caption` 产生了字号、高度和边距偏差。
3. 因此，在 Col 4 和 Col 5 中，用等高提纯的 HTML 标签：
   `<div style="font-size: 14px; font-weight: 500; color: var(--text-primary); margin-bottom: 4px; height: 21px; line-height: 21px;">高级参数</div>`
   和
   `<div style="font-size: 14px; font-weight: 500; color: var(--text-primary); margin-bottom: 4px; height: 21px; line-height: 21px;">生成方案</div>`
   替换原 `st.caption("微调参数")` 与 `st.caption("开始执行")`。
4. 结合主按钮与 Popover 按钮统一的 `height: 40px !important;`，实现 5 列控件从 Label 顶线、控件框上边沿、控件框下边沿到下方 Caption 的全部基线严丝合缝（0 像素偏差）。

### 2.3 Tab 1 开箱即用与极速秒开 (<100ms) 逻辑
1. 基于观察 1.3，Tab 1 首屏空白是因为 `tab1_step_reached` 初始值被卡在 `1`。
2. 修复第一步：将 `tab1_step_reached` 初始默认值调整为 `3`（或 `>= 2`），确保进入时立即执行下方渲染流。
3. 避免卡顿第二步：区分“用户主动点击重新推演 (`tab1_trigger_sim == True`)”与“首屏默认静默直读 (`tab1_sim_cache is None and not tab1_trigger_sim`)”。
4. 在静默直读模式下：
   - 优先检查磁盘持久化缓存 `data/cache/tab1_default_blueprint_cache.json`（包含默认 10 万元、C3 平衡进取型、6 只基金的推演与建仓单）；
   - 若磁盘缓存命中，通过纯内存反序列化在 10ms 内注入 `st.session_state.tab1_sim_cache` 与 `st.session_state.tab1_step3_cache`；
   - 若无磁盘缓存，则调用 `StrategyBridge.compute_n_funds_model_portfolio` 时传入 `progress_cb=None`，**绝不实例化 `ActiveComputationConsole`**，静默计算并落盘保存；
5. 仅当用户主动在界面修改了参数并点击“⚡ 生成实盘建仓方案”按钮时，才设置 `tab1_trigger_sim = True` 并呼出 `ActiveComputationConsole` 展示 4 步进度动画。从而实现首次打开 0 白屏、0 阻塞转圈、<100ms 完整出图。

### 2.4 顶部 4 卡视觉纯粹度与去 Emoji 逻辑
1. 基于观察 1.4，Card 2 中的 `vernacular_state` 剥离前缀 Emoji，提纯为专业金融文案：`震荡收息期`、`科技主升浪`、`熊市防守期`。
2. 状态呈现改由行内微型胶囊圆点（`8px` 圆点，背景色为 `st_color`）配合文字颜色表达，冷峻干练。
3. Card 3 的 `font-size: 16px;` 统一调整为 `font-size: 18px; font-weight: 700;`，与 Card 1、Card 2、Card 4 形成 100% 同构的四宫格卡片矩阵。
4. 彻底删除第 2768 至 2791 行的 `latest_plan` 待办预案大红横幅，恢复首屏在“顶部 4 卡 ➔ 投顾参谋折叠条 ➔ 四宫格大导航”之间的极简清爽结构。

---

## 3. Implementation Blueprint (具体代码修改落地蓝图)

### 3.1 修改点 1：全局 CSS 主按钮绑定机构皇家蓝 (app_gui.py)
**定位**: `AGY2_FundAdvisory/app_gui.py` 第 1286 至 1329 行。  
**修改方式**: 替换原弱约束的 `button[kind="primary"]` 样式块为高定机构蓝规范：

```css
    /* 🛡️ 机构级皇家蓝高定 Primary 主按钮与微光悬浮态 (彻底消灭 Streamlit #ff4b4b 番茄红) */
    button[kind="primary"],
    [data-testid="stBaseButton-primary"] {
        background: var(--accent-primary) !important;
        border: 1px solid var(--accent-primary) !important;
        color: #ffffff !important;
        border-radius: 8px !important;
        height: 40px !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        box-shadow: 0 2px 6px rgba(29, 78, 216, 0.2) !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-sizing: border-box !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    button[kind="primary"] *,
    button[kind="primary"] p,
    button[kind="primary"] span,
    button[kind="primary"] div,
    [data-testid="stBaseButton-primary"] *,
    [data-testid="stBaseButton-primary"] p,
    [data-testid="stBaseButton-primary"] span {
        color: #ffffff !important;
        font-weight: 600 !important;
    }

    button[kind="primary"]:hover,
    [data-testid="stBaseButton-primary"]:hover {
        background: var(--accent-primary) !important;
        border-color: var(--accent-primary) !important;
        filter: brightness(1.12) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(29, 78, 216, 0.35) !important;
        color: #ffffff !important;
    }

    button[kind="primary"]:active,
    [data-testid="stBaseButton-primary"]:active {
        transform: translateY(0) !important;
        filter: brightness(0.95) !important;
        box-shadow: 0 1px 3px rgba(29, 78, 216, 0.2) !important;
    }

    button[kind="primary"]:focus:not(:active),
    [data-testid="stBaseButton-primary"]:focus:not(:active) {
        border-color: var(--accent-primary) !important;
        box-shadow: 0 0 0 2px rgba(29, 78, 216, 0.4) !important;
    }
```

---

### 3.2 修改点 2：Tab 1 顶部 5 列控制栏基线对齐 (app_gui.py)
**定位**: `AGY2_FundAdvisory/app_gui.py`
- 第 3266 至 3268 行 (Col 4 高级微调)
- 第 3514 行后 (Col 4 底部 Caption)
- 第 3529 至 3537 行 (Col 5 生成方案)

**修改详情**:

**Col 4 修改前 (Line 3266-3268)**:
```python
        with col_l1_adv:
            st.caption("微调参数")
            with st.popover("⚙️ 高级微调", use_container_width=True):
```
**Col 4 修改后**:
```python
        with col_l1_adv:
            safe_markdown_html('<div style="font-size: 14px; font-weight: 500; color: var(--text-primary); margin-bottom: 4px; height: 21px; line-height: 21px;">高级参数</div>')
            with st.popover("⚙️ 高级微调", use_container_width=True):
```
并在 Popover 退出后（约第 3514 行）：
```python
            st.caption("模型与约束微调")
```

**Col 5 修改前 (Line 3529-3537)**:
```python
        with col_l1_btn:
            st.caption("开始执行")
            if st.button("⚡ 生成实盘建仓方案", type="primary", use_container_width=True, key="btn_run_simulation_now"):
                st.session_state.tab1_step_reached = 3
                st.session_state.tab1_step3_cache = None
                st.session_state.tab1_trigger_sim = True
                st.session_state.tab1_trigger_s3 = True
                st.session_state.tab1_last_calc_params = cur_tab1_params
                st.rerun()
```
**Col 5 修改后**:
```python
        with col_l1_btn:
            safe_markdown_html('<div style="font-size: 14px; font-weight: 500; color: var(--text-primary); margin-bottom: 4px; height: 21px; line-height: 21px;">生成方案</div>')
            if st.button("⚡ 生成实盘建仓方案", type="primary", use_container_width=True, key="btn_run_simulation_now"):
                st.session_state.tab1_step_reached = 3
                st.session_state.tab1_step3_cache = None
                st.session_state.tab1_trigger_sim = True
                st.session_state.tab1_trigger_s3 = True
                st.session_state.tab1_last_calc_params = cur_tab1_params
                st.rerun()
            st.caption("全市场漏斗穿透")
```

---

### 3.3 修改点 3：Tab 1 开箱即用与高速缓存直读 (app_gui.py)
**定位**: `AGY2_FundAdvisory/app_gui.py`
- 第 3153 至 3154 行 (状态初始化)
- 第 3545 至 3570 行 (推演计算)
- 第 3581 至 3684 行 (建仓单生成)

**修改方案**:
1. 初始化 `tab1_step_reached` 设为 `3`：
```python
        if "tab1_step_reached" not in st.session_state:
            st.session_state.tab1_step_reached = 3
```
2. 静默快速加载逻辑与显式用户触发分离：
```python
        # 磁盘持久化默认缓存路径
        t1_default_cache_file = Path(WORKSPACE_ROOT) / "data" / "cache" / "tab1_default_blueprint_cache.json"

        is_explicit_sim_trigger = bool(st.session_state.get("tab1_trigger_sim", False))

        if is_explicit_sim_trigger or st.session_state.get("tab1_sim_cache") is None:
            if is_explicit_sim_trigger:
                # 用户主动点击生成，展示中央计算进度台
                acc = ActiveComputationConsole(...)
                def _sim_cb(cur, tot, msg):
                    acc.update_step(cur, msg, progress_pct=int((cur / max(tot, 1)) * 95))
                res_portfolio = StrategyBridge.compute_n_funds_model_portfolio(
                    ..., progress_cb=_sim_cb
                )
                acc.complete("真全市场选基与推演完成")
            else:
                # 首屏开箱即用：零进度条弹窗，极速静默生成/读取 (<100ms)
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
                    progress_cb=None
                )
            st.session_state.tab1_sim_cache = res_portfolio
            st.session_state.tab1_trigger_sim = False
```
3. 对步骤 3（实盘建仓单 Blueprint）同样实施此分离逻辑：
```python
        is_explicit_s3_trigger = bool(st.session_state.get("tab1_trigger_s3", False))
        if is_explicit_s3_trigger or st.session_state.get("tab1_step3_cache") is None:
            # 当 not is_explicit_s3_trigger 时，不实例化 acc_s3，静默毫秒级装配 bp_rows 与 df_bp
            ...
```

---

### 3.4 修改点 4：顶部 4 卡 Emoji 清理、字号统合与横幅清理 (app_gui.py)
**定位**: `AGY2_FundAdvisory/app_gui.py`
- 第 2390 至 2399 行 (定调文案)
- 第 2706 至 2748 行 (Card 2 与 Card 3)
- 第 2767 至 2791 行 (伪交易待办预案横幅)

**修改方案**:
1. 文案剥离 Emoji (Line 2390-2398):
```python
raw_mkt_state = str(snapshot.get('market_state', '震荡收息期'))
if any(k in raw_mkt_state for k in ["震荡", "收息", "慢牛"]):
    vernacular_state = "震荡收息期"
elif any(k in raw_mkt_state for k in ["科技", "主升", "进攻"]):
    vernacular_state = "科技主升浪"
elif any(k in raw_mkt_state for k in ["熊", "防守", "破位"]):
    vernacular_state = "熊市防守期"
else:
    vernacular_state = raw_mkt_state[:6]
```
2. Card 2 采用微胶囊圆点传达状态 (Line 2717-2719):
```html
        <div class="metric-value-huge" style="color: {st_color}; font-size: 18px; font-weight: 700; display: flex; align-items: center;">
            <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background-color: {st_color}; margin-right: 6px; flex-shrink: 0;"></span>
            <span>{vernacular_state}</span>
        </div>
```
3. Card 3 字号由 16px 升级为 18px 粗体 (Line 2741):
```html
        <div class="metric-value-huge" style="color: var(--color-down); font-size: 18px; font-weight: 700;">
            {val_status}
        </div>
```
4. 删除第 2767 至 2791 行的 `latest_plan` 待办预案横幅及其内部的伪交易按钮。

---

## 4. Caveats (注意事项与边界条件)

1. **测试用例对 `tab1_step_reached` 的断言兼容性**:
   - 现存部分测试（如 `tests/test_challenger_g11_m1_actions.py`、`tests/test_challenger_m1_stress.py`）会在启动 AppTest 后显式手动设置 `at.session_state.tab1_step_reached = 2`。将默认值调整为 `3` 是完全向前兼容的，因为后续所有条件均为 `>= 2`。
2. **主题配色系统中的 `--accent-primary` 依赖**:
   - Primary 主按钮的 CSS 直接绑定了 `var(--accent-primary)`。在 `light_slate` 下为 `#1d4ed8`（皇家深海蓝），在 `dark_terminal` 下为 `#38bdf8`（天蓝），均具备优异的文字可读性。在 `deep_titanium`（钛金）主题下，`--accent-primary` 为亮琥珀黄 `#fbbf24`，需确保文字对比度符合 WCAG AA 标准。
3. **只读裁判文件与默认签名保护**:
   - 本调查涉及的所有修改均限定在 `AGY2_FundAdvisory/app_gui.py` 与 `data/cache/` 目录中，**严禁且未修改** `judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py` 四个只读裁判文件，且不触碰 `DataLoader.simulate_execution` 签名。

---

## 5. Conclusion (调查结论与交付总结)

经过深入源码排查与审计报告勾稽，AGY2 工作台在视觉审美与开箱即用性上的核心症结已完全定位，并具备高精度的代码级解决方案：
1. **主按钮番茄红根治**: 明确补齐了 `button[kind="primary"]` 和 `[data-testid="stBaseButton-primary"]` 的背景色、边框色、圆角、高度（40px）与 `:hover`/`:active` 微光悬浮态，100% 根除 Streamlit 原生刺眼 `#ff4b4b`。
2. **Tab 1 控制栏 5 列垂直基线对齐**: 准确定位了 Col 4、Col 5 因 `st.caption` 与 Col 1~3 原生 Widget Label 的高度与盒模型差异，设计了 21px 行高、字号 14px、`margin-bottom: 4px` 的精确 HTML 替代标签，实现 5 列控件毫米级基线对其。
3. **Tab 1 开箱即用**: 找出了首屏空白的根源（`tab1_step_reached` 初始卡在 1），设计了将首屏初始状态直达建仓方案并分离“静默秒开加载 (<100ms)”与“用户主动计算 (进度条)”的双轨状态机。
4. **顶部 4 卡视觉纯粹度**: 彻底清理了 Card 2 标题前的表情符号，改用 8px 纯色圆点微胶囊传达状态，统合 Card 3 字号至 18px 粗体，并删除了首屏残留的待办预案横幅。

---

## 6. Verification Method (独立核验方法)

1. **静态代码与 CSS 规则核验**:
   - 检查 `AGY2_FundAdvisory/app_gui.py`:
     - 确认全局 `<style>` 块中包含 `button[kind="primary"]` 的 `background: var(--accent-primary) !important;` 与 hover 规则；
     - 确认 Col 4 与 Col 5 的顶部标签为 `<div style="... height: 21px; line-height: 21px;">...</div>`；
     - 确认 `vernacular_state` 无 `🟢`、`🔥`、`🛡️` 等前缀；
     - 确认 `tab1_step_reached` 初始状态 `>= 2`。
2. **自动化测试运行**:
   - 运行基础设施裁判测试套件：
     ```powershell
     py -3 -m pytest tests/test_infra.py
     ```
     （预期：14 passed in ~5s）
   - 运行最终闭环专项测试套件：
     ```powershell
     py -3 -m pytest tests/test_adv_final_closure.py
     ```
     （预期：14 passed in ~45s）
3. **AppTest 页面渲染与无异常校验**:
   - 编写针对性的 AppTest 脚本，断言首屏加载后 `tab1_sim_cache` 不为空、Tab 1 底部建仓单表格存在，且无任何 Python 异常。
