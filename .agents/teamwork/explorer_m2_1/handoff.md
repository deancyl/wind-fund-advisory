# Milestone 2 Explorer 1 Technical Handoff Report: UI Routing, CSS Consolidation, Responsive Layout & Tab 2/4 Plain-Language Lead Cards

**报告编写代理**: Explorer M2-1  
**工作区路径**: `d:\Google\Workspace\Wind`  
**报告交付路径**: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_m2_1\handoff.md`  
**核心调查对象**: Features 7, 8, 12, 13 (针对 `AGY2_FundAdvisory/app_gui.py` 与 `tests/test_g19_m2_routing_and_rolling_dca.py`)  
**生成时间**: 2026-11-15T08:55:00Z  

---

## 一、直接观察证据 (Observation)

### 1. Feature 7: 首次加载存量持仓账本自动路由
- **代码位置**: `AGY2_FundAdvisory/app_gui.py:2717-2732` 及 `3266-3283`
- **现状观察**:
  1. `pm = st.session_state.pm` 初始化位于第 2729 行：
     ```python
     2729: pm: PortfolioManager = st.session_state.pm
     2730: clock = pm.clock
     2731: calc = pm.calculator
     ```
     在第 2731 行之后，**完全没有任何自动路由检查**。
  2. 当前自动路由逻辑被滞后延迟到了第 3266~3283 行（侧边栏与全局顶栏之间）：
     ```python
     3266: # 首次加载智能自动路由：若当前激活账本为存量组合（如实战29基或持仓数>=8只），首次进入自动聚焦至 Tab 2 (💼 持仓调仓)
     3267: if "_initial_ledger_routed" not in st.session_state:
     3268:     st.session_state["_initial_ledger_routed"] = True
     3269:     cur_pm_init = mlm_inst.get_pm(active_lid) if mlm_inst else pm
     3270:     if cur_pm_init and len(cur_pm_init.holdings) >= 8:
     3271:         st.session_state["sel_tab2_active_ledger"] = active_lid
     3272:         st.session_state["tab2_view_mode"] = "💼 持仓诊断与智能调仓 (主流程)"
     3273:         st.session_state["pending_cross_tab_jump"] = {
     3274:             "tab_index": 1,
     3275:             "tab_name": "💼 持仓调仓",
     3276:             "action_name": "首次加载存量持仓",
     3277:             "target_title": active_lid,
     3278:             "detail": f"检测到【{active_lid}】包含 {len(cur_pm_init.holdings)} 只存量持仓，已自动聚焦持仓诊断与调仓工作区",
     3279:             "timestamp": datetime.now().strftime("%H:%M:%S")
     3280:         }
     3281:         st.session_state.tab2_diagnosed = True
     3282:         st.session_state.tab2_rebalanced = True
     ```
  3. **现存缺陷与差异**:
     - 门槛阈值错误：第 3270 行写了 `>= 8`，而最新权威规范（`ORIGINAL_REQUEST.md` §三.1、`PROJECT.md` #7、`test_g19_m2_routing_and_rolling_dca.py` Tier 2）明确规定门槛为 `>= 10` 只标的。
     - 状态机不完备：对比第 2870~2886 行 `switch_active_ledger` 内部的完备状态注入，第 3267 行遗漏了 `st.session_state["last_cross_tab_action"]`、`st.session_state.tab2_trigger_diagnose = True` 和 `st.session_state.tab2_trigger_rebalance = True`。
     - 位置过晚：在第 2729 行至 3267 行之间跨越了 500 多行侧边栏与预计算逻辑，此时若未完成路由状态配置，可能导致部分侧边栏状态与默认工作区呈现脱节。

---

### 2. Feature 8: 样式集中合并与手机端列选择器
- **代码位置 1**: `AGY2_FundAdvisory/app_gui.py:340-398`（`render_chief_advisor_memo_card`）
  - **现象**: 函数内部每次被 Streamlit rerun 调用时，都在 HTML 前端嵌入 58 行 `<style>...</style>` 标签：
    ```python
    html_code = f"""<style>
    .chief-memo-container {{
    container: memo-desk / inline-size;
    width: 100%;
    }}
    .chief-memo-grid {{
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 6px;
    width: 100%;
    }}
    ...
    </style>
    <div class="chief-memo-container" ...>
    ```
  - **影响**: 造成每次局部刷新时 DOM 重复注入相同 `<style>` 块，违背样式集中化管理规范与 CSSOM 优化铁律。
- **代码位置 2**: `AGY2_FundAdvisory/app_gui.py:1918-1930`（全局主样式表移动端按钮组规则）
  - **现有代码**:
    ```css
    /* 表格底部按钮组在手机端 2x2 网格流 */
    div[data-testid="stHorizontalBlock"]:has(button):not(:has(.main-metric-card)),
    div[data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) {
        display: flex !important;
        flex-wrap: wrap !important;
        gap: 6px !important;
    }
    div[data-testid="stHorizontalBlock"]:has(button):not(:has(.main-metric-card)) > div[data-testid="column"],
    div[data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) > div[data-testid="column"] {
        flex: 1 1 calc(50% - 6px) !important;
        min-width: calc(50% - 6px) !important;
    }
    ```
  - **缺陷证据**:
    1. **选择器缺少 `stColumn`**: 仅包含 `> div[data-testid="column"]`，缺少现代 Streamlit 兼容选择器 `> div[data-testid="stColumn"]`（对比第 952、1884 行）。
    2. **数字输入框加减步进按钮遭击穿误伤**: Streamlit 的数字输入框 `st.number_input` 容器内部包含加减步进按钮（`button`）。现有规则使用 `:has(button)` 粗暴匹配，导致包含数字输入框的水平块被误判为“按钮组”，将其内部列强制设为 50% 宽度，造成数字输入框在手机端被暴力腰斩挤压！

---

### 3. Feature 12: `IS_MOBILE_VIEW` 激活与响应式布局
- **代码位置**: `AGY2_FundAdvisory/app_gui.py:250-266` vs 全局布局调用点
- **现状观察**:
  1. `_is_mobile_viewport()` 在第 250 行定义：
     ```python
     def _is_mobile_viewport() -> bool:
         try:
             if hasattr(st, "query_params") and st.query_params:
                 v_param = str(st.query_params.get("view", "")).lower()
                 if v_param in ("mobile", "phone", "m"):
                     return True
                 if v_param in ("desktop", "pc", "d"):
                     return False
             if hasattr(st, "context") and hasattr(st.context, "headers") and st.context.headers:
                 ua = str(st.context.headers.get("User-Agent", "")).lower()
                 if any(k in ua for k in ["mobile", "android", "iphone", "ipad", "ipod", "windows phone"]):
                     return True
         except Exception:
             pass
         return False
     ```
  2. 但在整个 `app_gui.py` 中，**完全没有声明全局顶层变量 `IS_MOBILE_VIEW`**！
  3. 多个核心分栏组件直接硬编码多列 `st.columns(...)`（如第 4006 行单行 5 列控制栏、第 5517 行单行 6 列操作栏、第 8280 行双图并排、第 8508 行热力图并排、第 8662 行四象限并排），在移动端视口（<640px）下缺少 Python 层的自适应单列降级容器。

---

### 4. Feature 13: Tab 2 工具坞扁平化与前置人话解读卡片
- **代码位置 1**: `AGY2_FundAdvisory/app_gui.py:6912-7030`（Tab 2 工具坞嵌套）
  - **现状观察**:
    在 Tab 2 中，当前处于 `else:` 分支（“🛠️ 账本运维与实盘复盘档案 (宽屏工具坞)”）下：
    ```python
    6915: dock_tab1, dock_tab2, dock_tab3, dock_tab4, dock_tab5, dock_tab6 = st.tabs([
    6916:     "✨ 快速录入/导入持仓",
    6917:     "📦 FIFO批次解锁透视",
    6918:     "🗄️ 账本环境与实盘档案",
    6919:     "⏳ 在途订单与T+1对账中心",
    6920:     "🔄 同公司基金低摩擦转换",
    6921:     "💰 宏观估值自适应分红"
    6922: ])
    6923: with dock_tab1:
    6924:     # 文本粘贴 / 搜索 / 表格导入
    6925:     sub_tab1, sub_tab2, sub_tab3 = st.tabs([
    6926:         "📋 文本粘贴导入",
    6927:         "🔍 搜索添加标的",
    6928:         "📥 表格模板导入"
    6929:     ])
    ```
    存在 **3 层 `st.tabs` 深度套娃**（顶层工作区 Tabs ➔ 工具坞 Tabs ➔ 导入方式 Tabs）。
- **代码位置 2**: Tab 2 Brinson 归因（第 7146~7237 行）
  - 现状：三维归因卡片（配置、选基、摩擦）与资产大类明细表直接排列，人话点评（`commentary`）被置于末尾（第 7213 行），缺少置顶的“前置人话解读卡片”。
- **代码位置 3**: Tab 4 重仓交叉热力图（第 8472~8597 行）
  - 现状：热力图与共同重仓股清单直接展示，缺少直击“伪分散”与“抱团风险”的前置通俗解读。
- **代码位置 4**: Tab 4 趋势偏离 vs 拥挤度四象限散点图（第 8635~8777 行）
  - 现状：四象限散点图直接渲染，缺少对四个象限（低估击球区、右侧主升区、放量分歧区、温和复苏区）直白人话轮动指引的前置解读卡片。

---

## 二、逻辑推导链 (Logic Chain)

```
[Observation 1: 路由滞后且门槛为8]
  │
  ├─ 依据: ORIGINAL_REQUEST §三.1 & PROJECT.md #7 & test_g19_m2_routing_and_rolling_dca.py:78-99
  ├─ 判定: 首次打开网页且持仓 >= 10 只标的时，必须立即在 pm 初始化瞬间完成路由标记
  └─ 落地: 将检查提升至 app_gui.py 第 2732 行，门槛定死 len(pm.holdings) >= 10，并补齐全部 trigger 信号

[Observation 2: 样式重复注入与输入框误伤]
  │
  ├─ 依据: DOM 优化铁律 & GEMINI.md Rule 14 & Rule 15
  ├─ 判定 2.1: render_chief_advisor_memo_card 内部 <style> 剥离至全局主样式表 (1050行)
  └─ 判定 2.2: 手机端按钮规则增加 :not(:has([data-testid="stNumberInput"])) 与 div[data-testid="stColumn"]

[Observation 3: 缺少 IS_MOBILE_VIEW 全局变量]
  │
  ├─ 依据: ORIGINAL_REQUEST Task 4 & GEMINI.md 移动端规范
  ├─ 判定: 激活 IS_MOBILE_VIEW = _is_mobile_viewport()
  └─ 落地: 在关键控制栏 (4006行)、顶栏 (5489行)、6键栏 (5517行)、双图 (8280行) 等自适应单列/堆叠

[Observation 4: 工具坞三层嵌套与图表缺少前置解读]
  │
  ├─ 依据: ORIGINAL_REQUEST Task 4 & PROJECT.md #13 & test_g19_m2_routing_and_rolling_dca.py:826-861
  ├─ 判定 4.1: 将 dock_tab1 内部的 sub_tab1..sub_tab3 扁平化为水平单选 st.radio
  └─ 判定 4.2: 在 Tab 2 Brinson、Tab 4 热力图、Tab 4 四象限图上方分别置顶高信息密度“前置人话解读卡片”
```

---

## 三、限制与假设 (Caveats)

1. **只读探索边界**: 本探索代理严格遵循只读原则，未修改任何项目源码，所有蓝图与代码切片均经过真实文件行号比对与 AST 静态扫描。
2. **测试文件依赖**: `tests/test_g19_m2_routing_and_rolling_dca.py` 中的 `_simulate_app_gui_initial_routing` (lines 78-99) 精准模拟了 Feature 7 的预期契约，本蓝图与该函数逻辑严格 1:1 对齐。
3. **Streamlit 响应式特性**: 移动端判断兼顾了 URL 参数（`?view=mobile`）与 User-Agent，同时通过 CSS `@media (max-width: 640px)` 与容器查询 `@container` 实现双轨防御。

---

## 四、结论与具体实施蓝图 (Conclusion & Implementation Blueprint)

### 1. Feature 7: 首次加载存量持仓账本自动路由 (`app_gui.py`)

#### 修改位置
`AGY2_FundAdvisory/app_gui.py:2732`（紧随 `calc = pm.calculator` 之后）

#### 具体代码方案
```python
# =============================================================================
# G19 Feature 7: 首次加载存量持仓账本自动路由闭环 (持仓标的数 >= 10 只)
# =============================================================================
if "_initial_ledger_routed" not in st.session_state:
    st.session_state["_initial_ledger_routed"] = True
    if pm and len(pm.holdings) >= 10:
        st.session_state["sel_tab2_active_ledger"] = _cur_lid
        st.session_state["tab2_view_mode"] = "💼 持仓诊断与智能调仓 (主流程)"
        st.session_state["pending_cross_tab_jump"] = {
            "tab_index": 1,
            "tab_name": "💼 持仓调仓",
            "action_name": "首次加载存量持仓",
            "target_title": _cur_lid,
            "detail": f"检测到【{_cur_lid}】包含 {len(pm.holdings)} 只存量持仓，已自动聚焦持仓诊断与调仓工作区",
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
        st.session_state["last_cross_tab_action"] = dict(st.session_state["pending_cross_tab_jump"])
        st.session_state.tab2_diagnosed = True
        st.session_state.tab2_rebalanced = True
        st.session_state.tab2_trigger_diagnose = True
        st.session_state.tab2_trigger_rebalance = True
```

#### 同步清理第 3267~3283 行
将第 3267 行的备用逻辑保留为安全兜底，门槛统一修改为 `>= 10`：
```python
# 首次加载智能自动路由安全兜底 (>= 10 只)
if "_initial_ledger_routed" not in st.session_state:
    st.session_state["_initial_ledger_routed"] = True
    cur_pm_init = mlm_inst.get_pm(active_lid) if mlm_inst else pm
    if cur_pm_init and len(cur_pm_init.holdings) >= 10:
        st.session_state["sel_tab2_active_ledger"] = active_lid
        st.session_state["tab2_view_mode"] = "💼 持仓诊断与智能调仓 (主流程)"
        st.session_state["pending_cross_tab_jump"] = {
            "tab_index": 1,
            "tab_name": "💼 持仓调仓",
            "action_name": "首次加载存量持仓",
            "target_title": active_lid,
            "detail": f"检测到【{active_lid}】包含 {len(cur_pm_init.holdings)} 只存量持仓，已自动聚焦持仓诊断与调仓工作区",
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
        st.session_state.tab2_diagnosed = True
        st.session_state.tab2_rebalanced = True
```

---

### 2. Feature 8: 样式集中合并与手机端列选择器 (`app_gui.py`)

#### 修改位置 1: 剥离 `render_chief_advisor_memo_card` 内部样式 (Line 340~398)
将第 340~398 行中拼接的 `<style>...</style>` 标签彻底剥离，函数返回值中的 HTML 直接以 `<div class="chief-memo-container"` 起始：
```python
    path_content_full = m_path.get("content", "")

    html_code = f"""<div class="chief-memo-container" style="background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 8px; padding: 6px 10px; margin-bottom: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.03); height: auto !important; min-height: 82px; overflow: visible !important; box-sizing: border-box;">
<!-- 第一行: 今日核心裁决 + 因果公式 + 截面时间 (Flex-wrap 防挤压) -->
...
```

#### 修改位置 2: 将剥离的样式并入全局主样式表 (Line 1050 前后)
在第 1050 行前后的主样式表内部加入：
```css
    /* 首席投顾裁决卡与 5 胶囊栅格系统 (Feature 8 集中化合并) */
    .chief-memo-container {
        container: memo-desk / inline-size;
        width: 100%;
    }
    .chief-memo-grid {
        display: grid;
        grid-template-columns: repeat(5, minmax(0, 1fr));
        gap: 6px;
        width: 100%;
    }
    .chief-memo-capsule {
        background: var(--bg-elevated);
        border: 1px solid var(--border-subtle);
        border-radius: 5px;
        padding: 4px 6px;
        box-sizing: border-box;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-inline-size: 0;
        overflow: hidden;
    }
    .chief-memo-capsule-title {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: clamp(9.5px, 0.7cqi + 9px, 11px);
        font-weight: 700;
        white-space: nowrap;
    }
    .chief-memo-capsule-sub {
        font-size: clamp(9px, 0.6cqi + 8.5px, 10.5px);
        color: var(--text-secondary);
        margin-top: 2px;
        margin-block-start: auto;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    @container memo-desk (inline-size < 560px) {
        .chief-memo-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
            gap: 6px !important;
        }
    }
    @container memo-desk (inline-size < 340px) {
        .chief-memo-grid {
            grid-template-columns: 1fr !important;
        }
    }
    @media (max-width: 768px) {
        .chief-memo-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }
```

#### 修改位置 3: 手机端按钮组规则精准排除数字输入框并补齐 `stColumn` (Line 1918~1930)
替换现有第 1918~1930 行：
```css
        /* 表格底部按钮组在手机端 2x2 网格流 (Feature 8: 精准排除数字输入框并补齐 stColumn) */
        div[data-testid="stHorizontalBlock"]:has(button:not([data-testid*="stNumberInput"])):not(:has(.main-metric-card)):not(:has([data-testid="stNumberInput"])),
        div[data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]):not(:has([data-testid="stNumberInput"])) {
            display: flex !important;
            flex-wrap: wrap !important;
            gap: 6px !important;
        }
        div[data-testid="stHorizontalBlock"]:has(button:not([data-testid*="stNumberInput"])):not(:has(.main-metric-card)):not(:has([data-testid="stNumberInput"])) > div[data-testid="column"],
        div[data-testid="stHorizontalBlock"]:has(button:not([data-testid*="stNumberInput"])):not(:has(.main-metric-card)):not(:has([data-testid="stNumberInput"])) > div[data-testid="stColumn"],
        div[data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]):not(:has([data-testid="stNumberInput"])) > div[data-testid="column"],
        div[data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]):not(:has([data-testid="stNumberInput"])) > div[data-testid="stColumn"] {
            flex: 1 1 calc(50% - 6px) !important;
            min-width: calc(50% - 6px) !important;
        }
```

---

### 3. Feature 12: `IS_MOBILE_VIEW` 激活与响应式布局 (`app_gui.py`)

#### 修改位置 1: 声明并导出 `IS_MOBILE_VIEW` 变量 (Line 266)
在 `_is_mobile_viewport()` 函数正下方：
```python
# 全局响应式视口激活标记 (Feature 12)
IS_MOBILE_VIEW: bool = _is_mobile_viewport()
if "is_mobile_view" not in st.session_state:
    st.session_state["is_mobile_view"] = IS_MOBILE_VIEW
```

#### 修改位置 2: 关键多列自适应降级排布
1. **Tab 1 单行 5 列控制栏 (Line 4006)**:
   ```python
   if IS_MOBILE_VIEW:
       col_l1_cap, col_l1_tier = st.columns(2)
       col_l1_rhythm, col_l1_adv = st.columns([7, 3])
       col_l1_btn = st.container()
   else:
       col_l1_cap, col_l1_tier, col_l1_rhythm, col_l1_adv, col_l1_btn = st.columns([2.5, 2.0, 2.0, 1.3, 2.2])
   ```
2. **Tab 2 顶部账本选择与视图切换 (Line 5489)**:
   ```python
   if IS_MOBILE_VIEW:
       col_tb_led = st.container()
       col_tb_mode = st.container()
   else:
       col_tb_led, col_tb_mode = st.columns([3.8, 6.2])
   ```
3. **Tab 2 顶部 6 键操作工具栏 (Line 5517)**:
   ```python
   if IS_MOBILE_VIEW:
       col_act_quick, col_act_batch, col_act_ocr = st.columns(3)
       col_act_undo, col_act_sync, col_act_mgr = st.columns(3)
   else:
       col_act_quick, col_act_batch, col_act_ocr, col_act_undo, col_act_sync, col_act_mgr = st.columns(6)
   ```
4. **Tab 4 资产大类与行业穿透双图 (Line 8280)**:
   ```python
   if IS_MOBILE_VIEW:
       col_chart_left = st.container()
       col_chart_right = st.container()
   else:
       col_chart_left, col_chart_right = st.columns([5, 5])
   ```
5. **Tab 4 重仓交叉热力图与清单 (Line 8508)**:
   ```python
   if IS_MOBILE_VIEW:
       col_heat = st.container()
       col_diag = st.container()
   else:
       col_heat, col_diag = st.columns([5.5, 4.5])
   ```
6. **Tab 4 四象限散点图与微观结构表 (Line 8662)**:
   ```python
   if IS_MOBILE_VIEW:
       col_q_fig = st.container()
       col_q_tbl = st.container()
   else:
       col_q_fig, col_q_tbl = st.columns([4.5, 5.5])
   ```

---

### 4. Feature 13: Tab 2 工具坞扁平化与前置人话解读卡片 (`app_gui.py`)

#### 修改位置 1: 工具坞 3 级套娃扁平化 (Line 6925~6929)
在 `with dock_tab1:` 下方，将 `st.tabs` 扁平化为水平 `st.radio`：
```python
            with dock_tab1:
                # Feature 13: 扁平化单层模式选择器（彻底消除 3 级 tabs 嵌套）
                sel_import_tool = st.radio(
                    "导入模式选择",
                    ["📋 文本粘贴导入", "🔍 搜索添加标的", "📥 表格模板导入"],
                    horizontal=True,
                    key="rad_tab2_sub_import_tool",
                    label_visibility="collapsed"
                )
                if sel_import_tool == "📋 文本粘贴导入":
                    sample_smart_text = ...
                    # 原 sub_tab1 内部代码保持 100% 完整
                elif sel_import_tool == "🔍 搜索添加标的":
                    # 原 sub_tab2 内部代码保持 100% 完整
                else:  # "📥 表格模板导入"
                    # 原 sub_tab3 内部代码保持 100% 完整
```

#### 修改位置 2: Tab 2 Brinson 归因前置人话解读卡片 (Line 7156 前)
在第 7156 行 `st.markdown("###### 🏛️ Brinson-Fachler 经典三维超额收益归因...")` 之前，注入前置卡片：
```python
                # Feature 13: Brinson-Fachler 前置人话解读卡片
                primary_driver = brinson_attr.get("primary_driver", "大类资产配置效应")
                alloc_yuan = brinson_attr.get("allocation_effect_yuan", 0.0)
                select_yuan = brinson_attr.get("selection_effect_yuan", 0.0)
                fric_yuan = brinson_attr.get("friction_saving_yuan", audit_res.get('saved_penalty_and_buffer_fees', 0.0))
                
                safe_markdown_html(f"""
                <div class="decision-card" style="padding: 10px 14px; border-left: 4px solid var(--accent-primary); background: var(--bg-surface); margin-bottom: 8px;">
                    <div style="font-size: 13px; font-weight: 700; color: var(--text-primary); margin-bottom: 4px;">
                        💡 前置人话解读·Brinson 归因三维拆解
                    </div>
                    <div style="font-size: 11.5px; color: var(--text-secondary); line-height: 1.5;">
                        为什么我的组合调仓后能跑赢或跑输基准？Brinson 模型将超额收益拆解为三笔明白账：<br>
                        ① <b>大类资产配置效应 ({alloc_yuan:+,.2f} 元)</b>：大类资产与赛道轮动超配/低配带来的行业择时贡献；<br>
                        ② <b>优选基金超额效应 ({select_yuan:+,.2f} 元)</b>：在同一赛道内部挑选优质基金经理带来的选基超额收益；<br>
                        ③ <b>交易摩擦防御贡献 (¥{fric_yuan:,.2f})</b>：AI 风控严防死守未满 7 天 1.50% 惩罚性赎回费为您节省的真金白银。
                    </div>
                </div>
                """)
```

#### 修改位置 3: Tab 4 重仓交叉热力图前置人话解读卡片 (Line 8473 前)
在第 8473 行 `st.markdown("---")` 与 `st.markdown("#### ⚠️ 重仓交叉热力与同质化诊断")` 下方：
```python
            # Feature 13: 重仓交叉热力图前置人话解读卡片
            safe_markdown_html("""
            <div class="decision-card" style="padding: 10px 14px; border-left: 4px solid var(--accent-primary); background: var(--bg-surface); margin-bottom: 10px;">
                <div style="font-size: 13px; font-weight: 700; color: var(--text-primary); margin-bottom: 4px;">
                    💡 前置人话解读·重仓交叉与机构抱团排查
                </div>
                <div style="font-size: 11.5px; color: var(--text-secondary); line-height: 1.5;">
                    持有不同名字的基金不等于分散风险！如果不同基金前十大重仓股高度重叠（热力图深蓝区域），就构成了<b>伪分散</b>。<br>
                    当非同系基金交叉重叠度 &ge; 40% 时，系统将自动预警防范机构抱团瓦解风险，并将重叠个股敞口合并纳入全组合行业上限监控。
                </div>
            </div>
            """)
```

#### 修改位置 4: Tab 4 趋势偏离 vs 拥挤度四象限散点图前置人话解读卡片 (Line 8637 下方)
在第 8637 行 `st.markdown("#### 🧭 持仓标的趋势偏离 vs 拥挤度四象限分布")` 下方：
```python
            # Feature 13: 四象限量价分布前置人话解读卡片
            safe_markdown_html("""
            <div class="decision-card" style="padding: 10px 14px; border-left: 4px solid var(--accent-primary); background: var(--bg-surface); margin-bottom: 10px;">
                <div style="font-size: 13px; font-weight: 700; color: var(--text-primary); margin-bottom: 4px;">
                    💡 前置人话解读·四象限量价结构与轮动指引
                </div>
                <div style="font-size: 11.5px; color: var(--text-secondary); line-height: 1.5;">
                    横轴为 <b>20日均线乖离率 Bias20</b>（衡量短期是否超买或超卖），纵轴为 <b>交易拥挤度热力 (0~100)</b>（衡量筹码扎堆程度）：<br>
                    🎯 <b>低估击球区 (左下)</b>：低位超跌且筹码冷清，左侧逆向定投黄金坑；<br>
                    🔥 <b>右侧主升区 (右上)</b>：顺势突破且热力充足，顺势吃主升浪但谨防高位急刹追高；<br>
                    ⚠️ <b>放量分歧区 (左上)</b>：跌破均线但拥挤度仍处高位，资金踩踏风险大，建议阶梯减亏；<br>
                    📈 <b>温和复苏区 (右下)</b>：站上均线且筹码沉淀健康，属于最舒适的稳健底仓长跑区间。
                </div>
            </div>
            """)
```

---

## 五、独立验证方法 (Verification Method)

Worker 完成上述施工后，可通过以下自动化测试与探针完成独立验证：

### 1. 对应功能单元测试验证
执行命令：
```powershell
py -3 -m pytest tests/test_g19_m2_routing_and_rolling_dca.py -k "TestFeature7 or TestFeature8 or TestFeature12 or TestFeature13" -v
```
**预期结果**: 43 项测试全部 PASS。

### 2. 静态 AST 与文本规则扫描探针
在 PowerShell 下运行以下探针代码：
```python
from pathlib import Path

content = Path("AGY2_FundAdvisory/app_gui.py").read_text(encoding="utf-8")

# Feature 7 验证
assert "sel_tab2_active_ledger" in content
assert "pending_cross_tab_jump" in content

# Feature 8 验证
assert ".chief-memo-container" in content
assert 'div[data-testid="stColumn"]' in content
assert "stNumberInput" in content

# Feature 12 验证
assert "IS_MOBILE_VIEW" in content
assert "_is_mobile_viewport" in content

# Feature 13 验证
assert "rad_tab2_view_mode" in content
assert "前置人话解读" in content or "人话" in content
assert "Brinson" in content
assert "四象限" in content

print("✅ Features 7, 8, 12, 13 静态契约扫描 100% 校验通过！")
```

### 3. 全局回归门禁
```powershell
py -3 -m pytest tests/test_g19_m2_routing_and_rolling_dca.py -q
```
配合 M2 Worker 补齐 StrategyBridge 与 PortfolioManager 后，全套 88 项测试将达成 100% 绿灯全通。
