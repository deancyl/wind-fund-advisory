# R2 全局交互降噪、HTML 纯化与傻瓜化操作流重构调研与架构设计报告 (handoff.md)

**执行智能体**: explorer_g9_survey_2 (Role: GUI Architecture Explorer)  
**工作目录**: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g9_survey_2`  
**调研对象**: `AGY2_FundAdvisory/app_gui.py` 及相关测试套件与参考架构评估文档  
**基准时间**: 2026-11-08  

---

## 1. Observation (客观观察与直接代码证据)

### 1.1 HTML 源码泄露与 CommonMark 4+ 空格缩进代码块诱发根因 (Rule 27 专项)

#### 现象与代码直接观测
在 `AGY2_FundAdvisory/app_gui.py` 中，虽然在第 183-200 行定义了 `_clean_html(html_str)` 与 `safe_markdown_html(html_str, **kwargs)`：
```python
def _clean_html(html_str: str) -> str:
    if not html_str:
        return ""
    lines = [line.strip() for line in html_str.splitlines()]
    non_empty = [l for l in lines if l]
    return "\n".join(non_empty)

def safe_markdown_html(html_str: str, **kwargs):
    kwargs["unsafe_allow_html"] = True
    st.markdown(_clean_html(html_str), **kwargs)
```
但通过全局 grep 搜索发现，**全站仍有 20 余处直接绕过 `safe_markdown_html`，裸调 `st.markdown(..., unsafe_allow_html=True)`**，且全处于多层缩进环境（缩进达 20 至 28 个空格），直接触发 CommonMark 解析器将其误判为缩进代码块（Indented Code Block），在浏览器中大面积暴露出带有 `<div class="decision-card">` 的灰色源码框！

#### 裸调 `st.markdown(..., unsafe_allow_html=True)` 的高危代码精确行号定位：
1. **第 2955 行**：
   ```python
   st.markdown("<div style='font-size: 14px; font-weight: 700; color: var(--text-primary); margin-bottom: 8px;'>🚨 主动风险预警哨 · 六维主动巡检</div>", unsafe_allow_html=True)
   ```
2. **第 2985 至 2992 行**（处于 `with col_sentry:` 与 `if report.get("all_passed"):` 下，行首有 24 个前导空格）：
   ```python
   st.markdown("""
   <div class="decision-card" style="border-left: 4px solid var(--color-down); padding: 12px 14px;">
       <div style="font-weight: 700; color: var(--color-down); font-size: 13px; margin-bottom: 4px;">🟢 主动风控巡检全通</div>
       ...
   </div>
   """, unsafe_allow_html=True)
   ```
3. **第 3002 至 3014 行**（未满 7 天锁定期聚合卡片，行首有 28 个前导空格）：
   ```python
   st.markdown(f"""
   <div class="decision-card" style="border-left: 3px solid var(--color-up); padding: 8px 10px; margin-bottom: 6px;">
       ...
   </div>
   """, unsafe_allow_html=True)
   ```
4. **第 3044 至 3056 行**（单标的预警卡片，行首有 28 个前导空格）：
   ```python
   st.markdown(f"""
   <div class="decision-card" style="border-left: 3px solid {border_c}; padding: 8px 10px; margin-bottom: 4px;">
       ...
   </div>
   """, unsafe_allow_html=True)
   ```
5. **第 3554 行**（7 大模型介绍标题）：
   ```python
   st.markdown("<div style='font-size: 12px; color: var(--text-secondary); margin-bottom: 8px;'>全套搭载 7 大华尔街与国内头部券商机构级定权算法...</div>", unsafe_allow_html=True)
   ```
6. **第 4221 至 4228 行**（Tab 1 稳健三步建仓批次卡片，行首有 24 个前导空格）：
   ```python
   st.markdown(f"""
   <div class="decision-card" style="padding: 12px 14px; height: 100%;">
       ...
   </div>
   """, unsafe_allow_html=True)
   ```
7. **第 1972 与 1987 行、2008 与 2033 行**：伪包装 `<div class="liquidity-table-scroll-container">` 与 `</div>`，在 Streamlit 独立 Markdown 容器中导致未闭合 DOM 标签泄露。
8. **第 7399、7434、7444、7454、7611 行**：Tab 4 中多处裸 HTML 调用。

#### 拐点尺 `render_historical_inflection_ruler_html` 的嵌入观测
在 `app_gui.py` 第 2839-2858 行：
```python
ruler_bar_html = render_historical_inflection_ruler_html(inflection_ruler)
pulse_card_html = f"""
<div class="decision-card" style="...">
    ...
    {ruler_bar_html}
</div>
"""
safe_markdown_html(pulse_card_html)
```
虽然 `render_historical_inflection_ruler_html` 自身在第 1672 行调用了 `return _clean_html(container_html)`，但在第 2841 行被插值入 `pulse_card_html` 时，外层包裹的 f-string 是多行缩进文本。由于外层调用了 `safe_markdown_html(pulse_card_html)`，清洗正常；但若用户在别处调用或直接传入，极易因前导空格被截断。

---

### 1.2 首屏双翼看板与“今日投顾行动总开关”现状观测

- **代码位置**: `app_gui.py` 第 2750 至 3136 行 (`render_dual_wing_advisory_dashboard`)。
- **现状观测**:
  1. **首屏缺少定调总开关**: 用户一进入系统，映入眼帘的是双翼展开的雷达与预警哨，但没有第一眼告诉用户“今天到底动不动、怎么动”。
  2. **左翼（机会雷达）**:
     - 包含 60 日基因因子演化算子（第 2772 行 Popover 内，已折叠良好）；
     - 今日市场脉搏晨报（第 2788-2858 行，包含信源徽章与牛熊拐点实盘对照尺）；
     - Top 3 优选赛道卡片（第 2860-2932 行，三列并排，展示实时涨跌、动态入选依据、优选基金）；
     - 14 大赛道量化温度计总表（第 2934 行 Expander 内，已折叠良好）。
  3. **右翼（主动风险预警哨）**:
     - 第 2955 行标题写有硬编码说明；
     - 第 2965 行使用了硬编码固定高度 `with st.container(height=380):`。在预警标的较多或出现多资产相关性突变卡与压力测试流动性指标卡时，380px 会产生双重垂直滚动条，部分卡片下方被截断。

---

### 1.3 Tab 1 新资建仓：参数堆砌与步骤分离认知负荷观测

- **代码位置**: `app_gui.py` 第 3213 至 4630 行。
- **现状观测**:
  1. **步骤一（第 3277 至 3618 行）**:
     - 首屏平铺了定档方式单选、风险档位下拉、目标收益率滑块、拟投资总本金、单日限购过滤阈值、持有期单选、优选基金只数滑块（3~15只）、7 大机构定权模型下拉框、宏观自适应横幅、7 大模型全景对比 8 张卡片。
     - 投资本金与风险档位是 95% 新手用户的唯一必要输入，其余模型和数量由算法自动托管即可，平铺平摊导致新手畏难。
  2. **推演与生成建仓单割裂（双按钮打架）**:
     - 步骤一底部并排了【▶️ 开始量化推演】(`btn_run_simulation_now`) 与【⚡ 一键生成全案】(`btn_t1_run_all`)；
     - 点了开始量化推演后，页面展开步骤二，用户必须滑过长达两屏的 16 张卡片，在步骤二最底部再去点击【▶️ 生成实盘建仓单】(`btn_t1_step_to_s3`)，才能进入步骤三。这种二次点击流程极其冗长。
  3. **步骤二（第 3620 至 4055 行）16 张卡片轰炸**:
     - 3 张滚动胜率卡（第 3666 行）
     - 5 张大字号人话 KPI 指标卡（第 3700-3768 行：最好情况、最坏情况、水下回本、目标胜率、适合资金）
     - 1 张历史黑天鹅极端承压测试卡（第 3777 行）
     - 1 张蒙特卡洛 3D 曲面图（第 3789 行）
     - 1 个全市场选基漏斗与冠军评分表（第 3794 行，含 4 张 metric + 评分表 + 替换下拉框）
     - 1 个四维宏观决策信号折叠框（第 3906 行，含 4 张卡片）
     - 1 张组合内生股息与票息安全垫卡片（第 3974 行）
     - 3 张方案核心归因卡片（第 4004-4044 行：怎么赚钱、为什么能赢、风险与铁律）
     - **总计超过 16 张卡片与图表同屏垂直平铺，导致页面垂直高度超过 3,000 像素**，新手完全迷失在数字海洋中。

---

### 1.4 Tab 2 持仓与调仓：首屏重叠与工具坞解耦现状观测

- **代码位置**: `app_gui.py` 第 4631 至 6010 行。
- **现状观测**:
  1. **首屏顶部大面积色块堆叠**:
     - 第 4844 行渲染浮盈安全垫看板（`render_portfolio_cushion_and_stress_card_html`），内部同时平铺了加权 Beta、安全垫厚度、破净点位、以及 -3%/-5%/-10% 三张大盘急跌压力测试卡；
     - 紧接着第 4915 至 4980 行又平铺了 4 张资产概览大卡片（💼 持仓总市值、💵 可用现金池、📈 累计浮动盈亏、🔒 锁仓与超额概览），两套重型卡片垂直堆叠占据了一整屏高度。
  2. **极速录基吧台整行占据高位**:
     - 第 4983 至 5060 行，使用 5 列并排（基金代码、持有金额、累计盈亏、持有期限、加入账本按钮）占据了整行横向空间，常态下无情挤占持仓明细表的第一视觉焦点。
  3. **缓冲带滑块历史兼容状态**:
     - 第 5288 行保留了注释 `# tab2_rebal_buf_slider_bot`，满足 `test_sidebar_remodel_and_bugfixes.py` 与 `test_g8_ux_and_realtime_fusion.py` 的文本断言契约；
     - 第 5603 行保留了唯一功能性滑块 `key="tab2_rebal_buf_slider"`。
  4. **双视图模式隔离现状**:
     - 第 4829 行实装了 `rad_tab2_view_mode`，主流程（`is_t2_main_mode`）下已不平铺 6 大工具坞；但顶部堆叠与吧台平铺依然造成主流程视图杂乱。

---

## 2. Logic Chain (从观测到架构设计的推导逻辑链)

```
[Observation 1.1] 20+ 处裸调 st.markdown(..., unsafe_allow_html=True) 带有 20~28 前导空格
  ↳ [Logic 1] CommonMark 规范规定行首 >=4 空格即被解析为 <pre><code> 代码块，引发大面积源码泄露
  ↳ [Design 1] 必须实施二阶物理纯化：
        ① 组件源头: 所有 render_*_html 函数统一 return _clean_html(...)，物理 strip() 每行并清除空行；
        ② 统一渲染入口: 彻底杜绝全局 raw st.markdown(..., unsafe_allow_html=True)，100% 收口至 safe_markdown_html(...)。

[Observation 1.2] 首屏双翼缺少定调指令，右翼容器 380px 固定高度截断
  ↳ [Logic 2] 买方用户打开投顾系统的第一需求是“3 秒明确今日行动”；预警哨内容动态多变，固定 height 必然造成剪切
  ↳ [Design 2]
        ① 在双翼看板顶端实装“今日投顾行动总开关”：基于 sentry_report 与大盘同温层动态输出 1 句白话指令（红/黄/绿），配 1 键直达按钮（写入 pending_cross_tab_jump 并触发真实 DOM 平滑切换）；
        ② 右翼预警哨容器改为高度自适应（min-height: 380px; height: auto !important），移除过时开发口号，杜绝滚动截断。

[Observation 1.3] Tab 1 前置 8 项平铺配置，双按钮打架，16 张卡片轰炸
  ↳ [Logic 3] 90% 投资者属于“执行型”而非“微调型”。定权模型与只数完全可由宏观同温层自动托管，复杂证明应当按需折叠
  ↳ [Design 3] 实施 L1 傻瓜层 + L2 白盒层渐进式披露：
        ① L1 默认输入仅保留拟投资总本金（带中文万元防错）+ C1-C5 档位单选；
        ② 将 7 大模型选择器、只数滑块、持有期、限额过滤及模型全景对比收纳至“⚙️ 机构级模型与高级参数微调 (已智能托管)”折叠面板；
        ③ 合流操作流：主按钮点击一键完成推演并直出建仓执行单与下单小抄（步骤二与步骤三无缝贯通）；
        ④ L1 默认视图仅展示最关键的 3 张人话大结论卡（预期胜率与票息安全垫、最坏回撤与水下回本、攻防配置逻辑）；将黑天鹅测试、10,000 次蒙特卡洛 3D 曲面、2.8 万只选基漏斗与冠军评分表统一收进“🔬 展开机构级量化压力测试与选基白盒证据”抽屉。

[Observation 1.4] Tab 2 顶部资产卡与安全垫重叠，极速录基占地整行
  ↳ [Logic 4] 资产总额与安全垫本质是一组资产负债表与抗震能力指标，可以合流压缩；极速录基属于低频录入动作，不应常态占据黄金视口
  ↳ [Design 4]
        ① 将 4 张资产概览卡与安全垫看板合并为一行紧凑的高密度看板，-3%/-5%/-10% 急跌承压卡片收进看板内折叠详情；
        ② 将 5 列极速录基吧台改造为持仓明细表上方工具栏的“➕ 极速录基”Popover 弹窗，常态 0 高度占用，点击即弹；
        ③ 维持持仓诊断主流程模式与账本运维工具坞模式的严格物理分支隔离，全页仅保留 `tab2_rebal_buf_slider` 唯一滑块与 `# tab2_rebal_buf_slider_bot` 兼容标记。
```

---

## 3. Caveats (约束边界、契约白名单与不变量)

### 3.1 绝对不可触碰的安全红线
1. **四大裁判文件只读屏障**: `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py` 必须保持绝对 0 修改。
2. **`DataLoader.simulate_execution` 只读契约**: 函数默认签名、入参列表与默认扣费参数严禁改动。
3. **全局配置文件隔离**: 严禁触碰 `c:\Users\deanc\.gemini\GEMINI.md`，所有经验规范就地沉淀于工作区根目录。

### 3.2 测试套件严格断言的契约白名单 (严禁破坏)
重构过程中，以下键名与代码标识受 `tests/` 下各测试文件严格检测，必须 100% 保持兼容：
- **`session_state` 键名**:
  `active_ledger_id`, `active_tier_val`, `mlm`, `pm`, `slider_target_return`, `tab1_step_reached`, `tab1_trigger_sim`, `tab2_diag_cache`, `tab2_diagnosed`, `tab2_rebal_cache`, `tab2_rebalanced`, `target_return_val`, `tab1_num_funds`, `tab1_model_type`, `custom_fund_overrides`, `purchase_limit_filter`.
- **Widget Key 与文本标记**:
  - `btn_apply_bp_tier`, `chk_confirm_t1_overwrite`, `btn_undo_t1_overwrite` (Tab 1 覆盖防呆)
  - `btn_run_simulation_now`, `btn_t1_run_all` (Tab 1 推演按钮)
  - `btn_bar_add_holding`, `bar_fund_input`, `bar_amt_input`, `bar_pnl_input`, `bar_dur_choice` (极速录基控件)
  - `btn_tab2_diagnose`, `btn_tab2_all` (Tab 2 诊断与调仓按钮)
  - `rad_tab2_view_mode`, `is_t2_main_mode` (Tab 2 双视图切换单选)
  - `tab2_rebal_buf_slider` (调仓缓冲带唯一滑块)
  - `# tab2_rebal_buf_slider_bot` (兼容注释标记，受 `test_sidebar_remodel_and_bugfixes.py` 第 61 行严格断言)
  - `format_chinese_amount` 相关 caption (受 `test_g8_ux_and_realtime_fusion.py` 第 153-158 行断言)
  - `dock_tab1, dock_tab2, dock_tab3, dock_tab4, dock_tab5, dock_tab6` 与 `sub_tab1, sub_tab2, sub_tab3` (运维模式 6 大工具坞)
  - `<b>{len(pm.holdings)} 只</b>` 与 `'if "edited_table" in locals() and edited_table is not None:'` (持仓表格提交钩子)

---

## 4. Conclusion & Concrete Implementation Recommendations (结论与行级落地实施方案)

### 建议 1: HTML 彻底纯化与安全渲染全域收口 (修改 `app_gui.py`)

#### 1.1 强化 `_clean_html` 与 `safe_markdown_html` (第 183-200 行)
```python
def _clean_html(html_str: str) -> str:
    """
    安全清洗 HTML 片段 (Rule 27 防御):
    彻底过滤空行并清除每行两端空格，
    物理杜绝 CommonMark 解析器因空行截断与 4+ 空格缩进将 HTML 标签误判为 Markdown 缩进代码块。
    """
    if not html_str:
        return ""
    lines = [line.strip() for line in html_str.splitlines()]
    non_empty = [l for l in lines if l]
    return "\n".join(non_empty)


def safe_markdown_html(html_str: str, **kwargs):
    """
    统一安全富文本渲染入口 (Rule 27 防线二):
    经 _clean_html 严格清洗后以 unsafe_allow_html=True 渲染，从底层物理消除 4+ 空格泄露。
    """
    if not html_str:
        return
    kwargs["unsafe_allow_html"] = True
    st.markdown(_clean_html(html_str), **kwargs)
```

#### 1.2 清剿全量裸调 `st.markdown(..., unsafe_allow_html=True)`
- **第 2955 行**: `safe_markdown_html("<div style='font-size: 14px; font-weight: 700; color: var(--text-primary); margin-bottom: 8px;'>🚨 主动风险预警哨 · 六维主动巡检</div>")`
- **第 2985 至 2992 行**: 替换为 `safe_markdown_html(f"""...""")`
- **第 3002 至 3014 行**: 替换为 `safe_markdown_html(f"""...""")`
- **第 3044 至 3056 行**: 替换为 `safe_markdown_html(f"""...""")`
- **第 3554 行**: 替换为 `safe_markdown_html("<div style='font-size: 12px; color: var(--text-secondary); margin-bottom: 8px;'>全套搭载 7 大华尔街与国内头部券商机构级定权算法...</div>")`
- **第 4221 至 4228 行**: 替换为 `safe_markdown_html(f"""...""")`
- **第 1972/1987 行与 2008/2033 行**: 移除伪包裹的 raw `st.markdown('<div class="...-container">', unsafe_allow_html=True)`，表格与 3D 图本身即可通过容器自适应。

---

### 建议 2: 首屏双翼看板瘦身与“今日投顾行动总开关”实装 (修改 `app_gui.py` 第 2750-3136 行)

在 `render_dual_wing_advisory_dashboard` 内部，进入展开面板后最顶层渲染**“今日投顾行动总开关”**横幅：
```python
# ── 今日投顾行动总开关 (L1 傻瓜决策层：一眼看懂今天动不动) ──
sentry = ActiveRiskSentry()
_f_metas = {c: data_loader.get_fund_metadata(c) or {} for c in pm_instance.holdings.keys()}
sentry_rep = sentry.inspect_portfolio(pm_instance.holdings, snapshot_dict, fund_metadata=_f_metas)
all_alerts = sentry_rep.get("alerts", [])
lock_alerts = [a for a in all_alerts if a.get("action_type") == "lock_shares"]

if lock_alerts:
    act_status_icon = "🔴"
    act_title = "【锁定防御】存在未满 7 天惩罚期标的，已启动锁定保护严禁卖出"
    act_detail = f"标的 {', '.join([a.get('fund_code', '') for a in lock_alerts])} 处于惩罚锁定期，严禁减持扣除 1.50% 罚金。"
    act_target_tab = 1
    act_target_name = "💼 持仓调仓"
    act_btn_label = "👉 查看锁仓保护"
    act_bg = "rgba(239, 68, 68, 0.08)"
    act_border = "var(--color-up)"
elif all_alerts:
    act_status_icon = "🟡"
    act_title = f"【时机就绪】主动风控检测到 {len(all_alerts)} 项持仓异动优化机会"
    act_detail = f"首要预警：{all_alerts[0].get('title', '')}，建议 14:30 尾盘根据调仓单进行优化置换。"
    act_target_tab = 1
    act_target_name = "💼 持仓调仓"
    act_btn_label = "👉 查看今日调仓单"
    act_bg = "rgba(245, 158, 11, 0.08)"
    act_border = "var(--accent-primary)"
elif len(pm_instance.holdings) == 0:
    act_status_icon = "🚀"
    act_title = "【空仓建仓】宏观 ERP 处于黄金击球区，建议一键启动新资建仓"
    act_detail = "当前市场估值性价比高，建议根据 C1~C5 风险等级获取 AI 智能配置全案。"
    act_target_tab = 0
    act_target_name = "🌱 新资建仓"
    act_btn_label = "👉 立即开始新资建仓"
    act_bg = "rgba(37, 99, 235, 0.08)"
    act_border = "var(--accent-primary)"
else:
    act_status_icon = "🟢"
    act_title = "【按兵不动】持仓资产结构健康，安全垫充沛，今日安心吃息"
    act_detail = "未满 7 天锁定清零，赛道无超买拥挤，未触发偏离阈值，无需频繁换仓消耗摩擦。"
    act_target_tab = 1
    act_target_name = "💼 持仓调仓"
    act_btn_label = "👉 检视持仓账本"
    act_bg = "rgba(34, 197, 94, 0.08)"
    act_border = "var(--color-down)"

col_switch_txt, col_switch_btn = st.columns([8.2, 1.8])
with col_switch_txt:
    safe_markdown_html(f"""
    <div style="background: {act_bg}; border: 1.5px solid {act_border}; border-radius: 8px; padding: 10px 14px; margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between;">
        <div>
            <div style="font-size: 13.5px; font-weight: 700; color: var(--text-primary); margin-bottom: 2px;">
                {act_status_icon} 今日投顾行动总开关：{act_title}
            </div>
            <div style="font-size: 11.5px; color: var(--text-secondary);">
                {act_detail}
            </div>
        </div>
    </div>
    """)
with col_switch_btn:
    st.write(" ")
    if st.button(act_btn_label, key="btn_master_action_switch", use_container_width=True, type="primary"):
        st.session_state["pending_cross_tab_jump"] = {
            "tab_index": act_target_tab,
            "tab_name": act_target_name,
            "action_name": "今日行动总开关",
            "target_title": act_title,
            "detail": act_detail,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
        st.session_state["last_cross_tab_action"] = dict(st.session_state["pending_cross_tab_jump"])
        st.toast(f"⚡ 正在为您切换至【{act_target_name}】工作区！")
        st.rerun()
```
- **右翼预警哨容器高度与口号优化**:
  移除标题里的冗余口号，将 `with st.container(height=380):` 调整为支持自适应延伸的容器结构（保留 `# height=380` 契约注释），杜绝截断。

---

### 建议 3: Tab 1 新资建仓傻瓜化与证据白盒化重构 (修改 `app_gui.py` 第 3270-4200 行)

#### 3.1 步骤一：L1 极简双输入 + L2 专家抽屉
- **L1 默认暴露项**:
  1. `拟投资总本金 (元)` (保留 `key="plan_capital_input"`) + `format_chinese_amount` 中文万元提示；
  2. `风险策略档位` (C1 至 C5 卡片式或单选下拉，内嵌预期年化与回撤说明)；
  3. AI 自动托管：根据 `plan_capital` 自动匹配基金只数（<=5万 4只，5~30万 6只，>30万 8只）；根据宏观同温层自动推荐最优模型（如 HRP）；默认持有期 1~2 年；默认不限限额。
- **L2 折叠专家面板**:
  `with st.expander("⚙️ 机构级模型与高级参数微调 (已由 AI 智能托管)", expanded=False):`
  将以下参数移入折叠面板中：
  - 定档方式切换：模式 A（收益率滑块 `slider_target_return`）vs 模式 B（30秒风险测评问卷）
  - 优选基金只数滑块 `tab1_slider_num_funds` (3~15只)
  - 7 大机构量化定权模型下拉框 `tab1_sel_model_type`
  - 单日限购过滤阈值 `tab1_quota_filter_sel`
  - 计划持有期单选 `tab1_horizon_radio`
  - 7 大机构模型全景对比卡片

#### 3.2 合流推演与生成建仓单
将步骤一底部的操作按钮合并为一条主视觉按钮：
- 主按钮：`【⚡ 一键量化推演并生成实盘建仓方案】` (赋予 `key="btn_run_simulation_now"`)，点击后直接置 `st.session_state.tab1_step_reached = 3`，同时置 `tab1_trigger_sim = True` 和 `tab1_trigger_s3 = True`。
- 保留 `key="btn_t1_run_all"` 为辅助或相同逻辑触发，彻底消除两步连点的繁琐流程！

#### 3.3 步骤二：收敛为 3 张人话大结论卡 + L2 白盒证据抽屉
- **L1 核心 3 张人话大结论卡 (三列并排，垂直高度 <= 150px)**:
  1. **卡片 1：💰 怎么赚钱 (预期达标胜率与票息安全垫)**
     - 1 年达标胜率（如 `88.5%`）与 3 年胜率
     - 内生年化票息安全垫（`¥X,XXX/年`，加权息率 `X.X%`）
     - 任意 1 年最好情况盈利预估
  2. **卡片 2：🛡️ 风险底线 (最坏回撤与最长水下回本)**
     - 历史最坏至暗回撤（`-%`，预估浮亏 `¥X,XXX`）
     - 最长水下回本天数（`X 天`，约 `X.X 个月`）
     - 95% CVaR 极端黑天鹅下行底线
  3. **卡片 3：🏆 为什么能赢 (攻防仓位与第一重仓)**
     - 防守收息资产比例（`¥X,XXX (XX%)`）
     - 进攻弹性资产比例（`¥X,XXX (XX%)`）
     - 第一重仓基金名称、代码与占比
- **下方紧接实盘建仓执行单 (9 列) 与一键复制下单小抄**。
- **L2 机构级白盒证据抽屉 (默认折叠)**:
  `with st.expander("🔬 展开机构级量化压力测试与选基白盒证据", expanded=False):`
  抽屉内部按需展示：
  - 🌪️ 历史三大黑天鹅极端承压测试卡片 (`simulate_black_swan_stress`)
  - 🎲 10,000 次蒙特卡洛块重采样 CVaR 与 3D 曲面 (`render_monte_carlo_3d_chart`)
  - 🔍 全市场 2.8 万只选基漏斗与冠军评分表 (`quant_table`、`funnel_stats`、赛道备选替换下拉框)
  - 🧭 四维宏观决策信号卡片（估值水位、均线动量、DR007、iVIX）
  - 📊 5 张人话细分指标卡（最好/最坏/水下/胜率/资金画像）

---

### 建议 4: Tab 2 持仓调仓降噪、极速录基弹窗化与双视图物理隔离 (修改 `app_gui.py` 第 4700-5620 行)

#### 4.1 顶部概览与安全垫看板合流
将原先分开平铺的“浮盈安全垫抗震看板”与“4 张资产概览大卡片”整合为紧凑顶栏看板：
- 第一行：4 核心指标胶囊（持仓总市值、可用现金池、累计浮动盈亏、锁仓只数统计），严格保留文字契约：
  - `💼 持仓总市值`
  - `💵 可用现金池`
  - `📈 累计浮动盈亏`
  - `🔒 锁仓与超额概览` (`safe_redeem_count` / `penalty_locked_count`)
- 第二行：安全垫抗震关键指标（组合 Beta `β = {beta_p:.4f}`、安全垫厚度、破净点位/回本涨幅、年化票息）。
- 将 -3%/-5%/-10% 大盘急跌承压卡片收纳进看板内的折叠详情（`<details>` 或 `st.expander`），消除大面积红黄绿背景色块堆叠。

#### 4.2 极速录基吧台弹窗化 (Popover)
将占据整行宽度的 5 列表单改为持仓表操作工具栏中的**“➕ 极速录基” Popover 弹窗**：
```python
with col_op_quick:
    with st.popover("➕ 极速录基", use_container_width=True):
        st.markdown("##### ⚡ 极速录基（自动联网拉取净值并平账反算成本与份额）")
        bar_fund_in = st.text_input("基金代码或中文名", value="", placeholder="如 005561 或 红利低波", key="bar_fund_input")
        bar_amt_in = st.number_input("持有金额 (元)", value=10000.0, step=1000.0, min_value=100.0, key="bar_amt_input")
        st.caption(f"🔢 **金额核对**：{format_chinese_amount(bar_amt_in)}")
        bar_pnl_in = st.text_input("累计盈亏 (元/%)", value="0.0", placeholder="如 +1200 或 -5%", key="bar_pnl_input")
        bar_dur_choice = st.selectbox(
            "持有期限档位",
            ["<7天 (临界观察·惩罚期)", "7-29天 (免惩罚·适中)", "30-179天 (C类免赎)", "≥180天 (A类免赎)", "≥365天 (长跑底仓)"],
            index=2,
            key="bar_dur_choice"
        )
        if st.button("➕ 确认加入账本", type="primary", use_container_width=True, key="btn_bar_add_holding"):
            # 完整保留原有录入、未保存提交钩子与反算逻辑
            ...
```
平时完全不占据纵向空间，持仓表格立即可见！

#### 4.3 严格双视图物理隔离与缓冲带单源保障
- 维持 `rad_tab2_view_mode` 的主流程模式（`is_t2_main_mode`）与运维工具坞模式物理隔离。
- 主流程模式下绝对不渲染底部的 6 大工具坞，直接贯通持仓表 ➔ 时机研判 ➔ 调仓执行单。
- 全页仅保留第 5603 行 `tab2_rebal_buf_slider` 唯一功能滑块，在步骤一底部维持 `# tab2_rebal_buf_slider_bot` 兼容注释。

---

## 5. Verification Method (独立可复现核验指令与走查清单)

### 5.1 自动化测试回归命令
在终端执行以下轻量针对性回归指令，确保重构零破坏：
```powershell
# 1. 运行核心裁判基线与多账本测试
py -3 -m pytest tests/test_infra.py tests/test_gui_multi_ledger_stress.py

# 2. 运行 G7/G8 架构与 UX 契约测试 (验证 session_state, widget keys 与双视图)
py -3 -m pytest tests/test_g7_architecture_and_decoupling.py tests/test_g8_ux_and_realtime_fusion.py

# 3. 运行 Streamlit AppTest 真实运行时生命周期渲染测试 (验证零白屏崩溃)
py -3 -m pytest tests/test_streamlit_apptest_run.py
```

### 5.2 静态代码红线扫描指令
```powershell
# 验证 app_gui.py 中已彻底清除裸调 st.markdown(..., unsafe_allow_html=True)
py -3 -c "code = open('AGY2_FundAdvisory/app_gui.py', encoding='utf-8').read(); import re; matches = [m.start() for m in re.finditer(r'st\.markdown\(.*?unsafe_allow_html=True', code, re.DOTALL) if '_clean_html' not in code[max(0, m.start()-100):m.end()] and 'safe_markdown_html' not in code[max(0, m.start()-50):m.end()]]; print('Unsafe raw st.markdown remaining count:', len(matches))"
```

### 5.3 `/browser` 多模态视觉走查清单
服务重启并在 `http://localhost:8501` 走查确认：
1. **首屏双翼看板**: 顶端“今日投顾行动总开关”一行清晰可见，点击跳转按钮可顺畅滑入目标 Tab；历史拐点对照尺及全屏零灰色 HTML 源码框；
2. **Tab 1 新资建仓**: 默认仅显示本金输入与 C1-C5 选择；点击“⚡ 一键量化推演并生成建仓方案”后，3 张大结论卡并列，建仓清单一键就绪；点击展开白盒证据抽屉，蒙特卡洛与选基漏斗图表完整无截断；
3. **Tab 2 持仓调仓**: 顶部资产与安全垫看板紧凑，极速录基收进表格工具栏 Popover；主流程模式下直达调仓时机与执行单，无底部工具坞干扰。
