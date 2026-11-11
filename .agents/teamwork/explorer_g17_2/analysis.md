# G17 世代 UI/UX 深度法证与手机端响应式重构技术探查分析报告

- **探查主体**: UI & Mobile Layout Explorer (G17-2)
- **探查对象**: `AGY2_FundAdvisory/app_gui.py`, `advisory_engine.py`, 手机端截图 `media_1794406255999_c8abd7ad.png`, 审计文件 `agy2_ui_ux_audit_and_fix_plan (6).md`
- **生成日期**: 2026-11-11
- **状态**: 探查完成 (Read-Only Investigation Completed)

---

## 一、 执行摘要 (Executive Summary)

本报告针对 G17 世代用户关于“手机端第 4 个主导航入口被截断、首屏 600 字长文墙纵向堆叠、切换存量账本后停留在新资建仓、表格关键列折叠在右侧不可见及底部 5 个灰色长条堆叠”等严重交互缺陷展开了细致的源码级法证与样式重构设计。

核心法证与设计结论如下：
1. **主导航与顶栏卡片 (CSS 响应式)**：在 `app_gui.py` 第 1275 行与 1632 行中，原代码对顶层 4 个 Tab 锁死为 `grid-template-columns: repeat(4, 1fr) !important;`，且按钮字号为 `16px`、内边距 `10px`。在 `390px` 手机视口下，4 个 Tab 的最小内容宽度达 `414px`，导致第 4 个主 Tab「🔍 穿透工具」被容器截断溢出。设计在 `@media (max-width: 768px)` 下将其重构为 **2×2 双排四宫格**（高度 `40px`、字号 `14px`），同时将顶栏 4 张指标卡设为 **2×2 田字格**，垂直高度缩减 50%。
2. **首屏备忘录与投顾参谋合流 (高密极简)**：消除首屏同时存在「五维全息备忘录大框」与「今日投顾参谋折叠框」的双重堆叠结构，融合为单一的 **「🧭 首席投顾今日裁决台」**。默认直显区高度严格控制在 **≤ 110px**（第一行展示今日核心裁决 + 仓位因果传导公式 + 截面时间；第二行以 5 个紧凑胶囊呈现各维度 ≤20 字的人话结论）。详细文段、Top 3 机会雷达卡与十三维主动风控巡检全量收纳至下方的展开抽屉中。
3. **存量账本自动路由与诊断即刻展开 (状态联动)**：在 `switch_active_ledger`（第 2475 行）中，当检测到目标账本持有存量基金（`len(new_pm.holdings) > 0`）时，自动注入 `pending_cross_tab_jump` 将焦点跳转至 `tab_index: 1`（`💼 持仓调仓`），并同步激活 `tab2_diagnosed = True` 与 `tab2_rebalanced = True`，确保 29 基存量组合在切换后首屏即呈现三阶重塑方案、尾仓清扫卡与诊断详情。
4. **表格核心列优先与底部工具栏紧凑化 (表格优化)**：重排 Tab 0 建仓表、Tab 1 实时持仓表与调仓建议表的列顺序，强制将「基金代码/名称、金额/市值、盈亏率/目标占比、建议操作/实操指引」锁定在前 3~4 列。表格下方堆叠的 4~5 个全宽长条在手机端收拢为 2×2 网格，若流动性折价 `< ¥1.00` 则自动隐藏全 0 冗余大表。

---

## 二、 手机端实测截图法证清查 (Mobile Screenshot Forensics)

对照实测截图 `media_1794406255999_c8abd7ad.png` 与 `agy2_ui_ux_audit_and_fix_plan (6).md`，法证核查结果如下：

| 序号 | 缺陷表现 (截图中直接观测) | 源码根因位置 | 业务与体验影响 |
|:---|:---|:---|:---|
| **1** | 主导航栏仅见「🌱 新资建仓」、「💼 持仓调仓」、「📈 组合回测」，第 4 个「🔍 穿透工具」彻底溢出消失 | `app_gui.py:1275` 锁死 `repeat(4, 1fr)`，缺少移动端折行规则 | 手机用户无法触达穿透工具箱，功能完整性断裂 |
| **2** | 顶栏 4 张指标卡垂直串联成 4 个全宽长条 | `app_gui.py:3283` `st.columns(4)` 在 `<768px` 被 Streamlit 单列堆叠 | 霸占约 300px 纵向高度，首屏被空泛指标完全占据 |
| **3** | 五维备忘录 5 个巨型文本框垂直连续排列，占满两屏以上（约 600 字文墙） | `app_gui.py:288-370` `.chief-memo-grid-2x2` 在手机端退化为 1 列 4 框 + 1 顶部框 | 严重认知超载，用户被迫滑动三屏才能看到操作按钮 |
| **4** | 备忘录标题栏的「买方参谋体系」徽章文字被挤压成竖排 3 行 | `app_gui.py:303-311` 标题与徽章使用 `flex: space-between` 未设 `white-space: nowrap` | 汉字折行断裂，排版美观度归零 |
| **5** | 备忘录下方紧接着堆叠了一个同质化的「今日投顾参谋」折叠框 | `app_gui.py:3611` `st.expander` 独立于备忘录存在 | 界面结构同义反复、臃肿混乱 |
| **6** | 切换至「实战存量组合（29只）」后，页面仍停留在 Tab 0 展示 10 万元新资建仓 | `app_gui.py:2475` `switch_active_ledger` 仅改 session 变量未触发跨 Tab 路由 | 存量用户被误导看新资建仓，体验割裂 |
| **7** | 表格首屏仅露出基金代码、名称、份额，买入/调仓金额与操作建议被藏在右侧滚动区 | `app_gui.py:4467, 5952, 6705` 列定义数组未按核心决策优先级排序 | 手机端横向频繁滑动才能看到买卖指令 |
| **8** | 表格下方垂直摞了 4 个操作按钮与 1 个大折叠卡，共 5 个灰色全宽长条 | `app_gui.py:4760, 6133` `st.columns` 按钮组单列堆叠 + 全 0 流动性折价表无条件展开 | 页面底部“长城堆叠”，排版松散凌乱 |

---

## 三、 五大专项重构设计方案与精确代码蓝图

### 1. 专项一：顶层主导航 2×2 网格与 4 全局指标卡田字格重构 (CSS 栅格重写)

#### 1.1 导航栏 2×2 网格 CSS 设计
在 `AGY2_FundAdvisory/app_gui.py` 的全局 `<style>` 中，针对 `@media (max-width: 768px)` 与 `@media (max-width: 640px)`，重写顶层主导航选择器：

```css
/* =========================================================================
   G17: 手机端 (<=768px) 顶层四大主导航 2x2 四宫格双排网格控制 (彻底消灭横向截断)
   ========================================================================= */
@media (max-width: 768px) {
    [data-testid="stMainBlockContainer"] > div > div > [data-testid="stTabs"] > [data-baseweb="tab-list"],
    div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) > [data-baseweb="tab-list"],
    div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) > div[role="tablist"],
    div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) div[role="tablist"],
    div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) [data-baseweb="tab-list"] {
        display: grid !important;
        grid-template-columns: repeat(2, 1fr) !important;
        grid-template-rows: repeat(2, 40px) !important;
        gap: 6px !important;
        padding: 4px !important;
        margin-bottom: 10px !important;
        width: 100% !important;
        box-sizing: border-box !important;
    }

    [data-testid="stMainBlockContainer"] > div > div > [data-testid="stTabs"] > [data-baseweb="tab-list"] button,
    div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) > [data-baseweb="tab-list"] button,
    div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) > div[role="tablist"] button,
    div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) div[role="tablist"] > button,
    div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) div[role="tablist"] > div[role="tab"],
    div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) div[role="tablist"] > [data-testid="stTab"] {
        height: 40px !important;
        min-height: 40px !important;
        font-size: 13.5px !important;
        font-weight: 700 !important;
        padding: 0 4px !important;
        border-radius: 6px !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
}
```

- **隔离保证**：选择器带有 `:not([data-testid="stTabContent"] div[data-testid="stTabs"])`，确保绝对不会误伤 Tab 4 内部的二级子 Tab（保持下划线紧凑流式样式）。
- **空间计算**：在 390px 视口下，扣除 24px 页面边距与 6px 间隙，每个按钮分得宽约 177px，足够容纳图标与 4 个汉字（宽约 85px），余量高达 92px，完全杜绝换行与截断。

#### 1.2 顶部 4 张全局指标卡 2×2 田字格设计
在 `@media (max-width: 768px)` 中添加：

```css
/* =========================================================================
   G17: 手机端 (<=768px) 顶栏 4 张指标卡 2x2 双排田字格 (纵向空间压降 50%)
   ========================================================================= */
@media (max-width: 768px) {
    div[data-testid="stHorizontalBlock"]:has(.main-metric-card) {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: wrap !important;
        gap: 6px !important;
    }

    div[data-testid="stHorizontalBlock"]:has(.main-metric-card) > div[data-testid="column"],
    div[data-testid="stHorizontalBlock"]:has(.main-metric-card) > div[data-testid="stColumn"] {
        flex: 1 1 calc(50% - 6px) !important;
        min-width: calc(50% - 6px) !important;
        max-width: calc(50% - 6px) !important;
        width: calc(50% - 6px) !important;
        box-sizing: border-box !important;
    }

    .main-metric-card {
        min-height: 72px !important;
        padding: 6px 8px !important;
        padding-bottom: 8px !important;
        border-radius: 6px !important;
    }

    .main-metric-card .metric-card-title {
        font-size: 11px !important;
        margin-bottom: 2px !important;
    }

    .main-metric-card .metric-value-huge {
        font-size: 15px !important;
        font-weight: 800 !important;
        line-height: 1.2 !important;
    }

    .main-metric-card .metric-card-sub {
        font-size: 10px !important;
        margin-top: 2px !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }
}
```

- **收益**：原来 4 张卡每张约 75px + 10px gap 垂直堆叠共约 340px 高度；改造后两排呈现，总高度约 150px，**首屏纵向净节省约 190px (55.8%)**！

---

### 2. 专项二：重构首屏「🧭 首席投顾今日裁决台」（合流消灭文字墙）

#### 2.1 架构设计：两段式单容器（直显 ≤ 110px + 抽屉展开）
废除当前同时渲染的 `render_chief_advisor_memo_card`（5大长文框）与 `st.expander("今日投顾参谋...")`，合流为 `render_chief_verdict_desk(pm, snapshot, memo_data, top3_sectors, sentry_rep)`。

#### 2.2 第一段：默认常驻直显区（Height ≤ 110px）
- **第一行 (Header & Causal Formula)**：
  - 左：`🧭 首席投顾今日裁决台` + 醒目大胶囊 `🎯 今日裁决：【{action_verdict}】`（如维持底仓吃息、逆向定投吸筹、逢高适度止盈）。
  - 中：**仓位因果传导公式**（单行高密度呈现）：
    `因果链：基准权益 60% + ERP极低估(+10%) + 货币宽松(+5%) - 超买约束(-5%) = 建议 70%`。
  - 右：数据截面时间戳 `截面: {clean_ts}`。
  - **防挤压保障**：容器使用 `display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 6px;`，内部各胶囊强制声明 `white-space: nowrap !important;`，彻底杜绝汉字被挤成竖排！
- **第二行 (5 Compact Capsules)**：
  - 桌面端 1 行 5 列，手机端 2 列流式网格。
  - 每颗胶囊统一结构：`图标 + 维度名称 + 状态徽章 + 20字以内精要结论`：
    1. 🏛️ **宏观政策**：`10Y国债 1.62% 极低分位 ｜ DR007利差 -11bp 资金充沛`
    2. 🌐 **国际汇率**：`USD/CNH 7.2450 波幅可控 ｜ 中美利差 -277bp 倒挂`
    3. 🏭 **产业击球**：`中证红利股息 4.8% 黄金击球区 ｜ 谨防赛道脉冲追高`
    4. 🩺 **持仓病灶**：`0 深套出血点 ｜ 0 碎片尾仓 ｜ 结构健康`（存量账本则显示出血点与尾仓数量）
    5. ⏱️ **14:30尾盘**：`持股吃息 ｜ 未满7天禁卖 ｜ C类择机转A`

#### 2.3 第二段：可平滑展开之深度白盒抽屉
- 折叠标签：`st.expander("🔭 展开十维深度逻辑、Top 3 机会雷达与十三维风控体检详情", expanded=False)`
- 展开后展示：
  - **模块 A：五维全息深度分析文段与十维投票看板**（宏观政策、国际汇率、产业击球、病灶排查、行动指令的完整分析文字，以及十维模型投票得分明细）。
  - **模块 B：左右双翼看板**：
    - 左翼：`🔭 全市场机会雷达 · Top 3 机会甄选`（包含 3 张赛道卡与因子进化参数）。
    - 右翼：`🚨 主动风险预警哨 · 十二维/十三维主动风控巡检`（包含持仓全部主动风险哨卡）。

#### 2.4 测试兼容契约保障
在 `tests/test_adversarial_m2_challenger2_timemachine_and_memo.py` 中有如下测试断言：
1. `render_chief_advisor_memo_card(None)` 与 `render_chief_advisor_memo_card({})` 绝不调用 `st.markdown`。
2. 正常调用时，生成的 HTML 每一行严禁出现 4 个前导空格（防 CommonMark 代码块转义）。
3. 必须容忍缺失部分键名的字典（`partial_memo`）。

**设计实施方案**：
在 `app_gui.py` 中保留 `def render_chief_advisor_memo_card(memo_data: Dict[str, Any], title: str = ...)` 函数名与完整参数签名，在内部直接调用重构后的新样式生成器，并经由 `safe_markdown_html(_clean_html(...))` 输出，100% 保持向后兼容与测试绿灯。

---

### 3. 专项三：存量账本切换自动跨 Tab 路由至「💼 持仓调仓」

#### 3.1 现状与病灶
在 `app_gui.py` 第 2475 至 2515 行的 `switch_active_ledger(target_ledger_id)` 中：
```python
# 现存逻辑缺陷 (Line 2508-2514):
st.session_state.tab2_diag_cache = None
st.session_state.tab2_rebal_cache = None
st.session_state.tab2_diagnosed = False
st.session_state.tab2_rebalanced = False
st.session_state.tab2_trigger_diagnose = False
st.session_state.tab2_trigger_rebalance = False
st.rerun()
```
此时 `pending_cross_tab_jump` 为空，Streamlit 在 rerun 后默认渲染第 1 个 Tab（`tab_zero_start` 即 Tab 0「🌱 新资建仓」）。导致无论切换到 29 基实战账本还是其他存量账本，用户都会停留在 Tab 0，并看到 10 万元的建仓模型方案！

#### 3.2 路由闭环设计
当目标账本含有持仓（`len(new_pm.holdings) > 0`）时，在 `switch_active_ledger` 内部注入跨 Tab 跳转指令：

```python
# ── G17 优化：存量账本自动路由至 💼 持仓调仓 并自动激活实战诊断 ──
if len(new_pm.holdings) > 0:
    st.session_state["tab2_view_mode"] = "💼 持仓诊断与智能调仓 (主流程)"
    st.session_state["pending_cross_tab_jump"] = {
        "tab_index": 1,
        "tab_name": "💼 持仓调仓",
        "action_name": "切换账本",
        "target_title": meta.get("name", target_ledger_id),
        "detail": f"已切换至存量持仓账本（共 {len(new_pm.holdings)} 只标的），自动聚焦持仓诊断与调仓工作区",
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }
    st.session_state["last_cross_tab_action"] = dict(st.session_state["pending_cross_tab_jump"])
    # 自动激活诊断与调仓，免除用户二次点击 "🔍 诊断持仓并生成今日调仓方案"
    st.session_state.tab2_diagnosed = True
    st.session_state.tab2_rebalanced = True
    st.session_state.tab2_trigger_diagnose = True
    st.session_state.tab2_trigger_rebalance = True
else:
    # 空账本重置状态，停留在新资建仓
    st.session_state.tab2_diagnosed = False
    st.session_state.tab2_rebalanced = False
    st.session_state.tab2_trigger_diagnose = False
    st.session_state.tab2_trigger_rebalance = False
```

- **DOM 响应链路**：`app_gui.py` 第 3846 行现成的真实 DOM 注入脚本会立即截获 `pending_cross_tab_jump`，向父窗口派发 `tabs[1].click()` 并触发 `scrollIntoView`。
- **业务收益**：用户在顶部下拉框选中「实战存量组合（29只·¥26,615.10）」后，页面即刻平滑跳转至 Tab 1，且 29 只基金的三阶手术方案（清扫 19 只免赎尾仓、科创50 C转A、全天候压舱石）全部展开，所见即所得。

---

### 4. 专项四：表格核心决策列优先与手机端防横向吞没

#### 4.1 Tab 0 新资建仓表 (`df_display`) 列重构
- **原列序**（第 4467 行）：
  `["基金代码", "基金名称", "份额", "目标占比(%)", "风险贡献(PCR %)", "精确买入金额(元)", "最新净值", "实时估值涨跌(%)", "排雷与拥挤度", "实操分红与限购指引"]`
  - 核心缺陷：“精确买入金额”排在第 6 列，“实操分红与限购指引”排在第 10 列，手机端全被挤出右侧。
- **G17 优先列序**：
  ```python
  cols_prioritized_t0 = [
      "基金代码", "基金名称", "精确买入金额(元)", "目标占比(%)",
      "实操分红与限购指引", "份额", "最新净值", "实时估值涨跌(%)",
      "风险贡献(PCR %)", "排雷与拥挤度"
  ]
  ```
  - **效果**：手机端一屏立见「代码、名称、买入金额、目标占比、实操指引」，无需任何横向滑动即可完成跟单。

#### 4.2 Tab 1 实时持仓明细表 (`df_table`) 列重构
- **原列序**（第 5952 行）：
  `["基金代码", "基金名称", "当前市值(元)", "持仓份额", "当前净值", "持仓成本价", "累计盈亏(元)", "浮动盈亏率(%)", "调仓意愿", "今日实时估值涨跌(%)", "盘中预估盈亏(元)", "持仓占比(%)", "最短持有天数", "赎回费状态", "分红方式"]`
  - 核心缺陷：“浮动盈亏率”在第 8 列，“调仓意愿”在第 9 列，“赎回费状态”在第 14 列。
- **G17 优先列序**：
  ```python
  cols_prioritized_holdings = [
      "基金代码", "基金名称", "当前市值(元)", "浮动盈亏率(%)",
      "累计盈亏(元)", "调仓意愿", "赎回费状态", "持仓占比(%)",
      "今日实时估值涨跌(%)", "盘中预估盈亏(元)", "持仓份额",
      "当前净值", "持仓成本价", "最短持有天数", "分红方式"
  ]
  ```
  - **效果**：前 4 列直击核心「代码、名称、市值、盈亏率」，紧接着展示「意愿、赎回费状态」。

#### 4.3 Tab 1 调仓建议执行表 (`df_orders_tbl`) 列重构
- **原列序**（第 6705 行）：
  `["基金代码", "基金名称", "份额", "当前市值(元)", "目标占比(%)", "实时估值涨跌(%)", "建议调仓金额(元)", "建议操作", "尾盘微观优化(bps)", "实操要点"]`
  - 核心缺陷：“建议操作”排在第 8 列，“建议调仓金额”排在第 7 列。
- **G17 优先列序**：
  ```python
  rebal_cols_prioritized = [
      "基金代码", "基金名称", "建议操作", "建议调仓金额(元)",
      "当前市值(元)", "目标占比(%)", "实时估值涨跌(%)",
      "份额", "尾盘微观优化(bps)", "实操要点"
  ]
  ```
  - **效果**：前 4 列直接告诉用户「标的 + 建议操作(买/卖/清) + 调仓金额」，指令直达眼球。

---

### 5. 专项五：收拢表格下方堆叠的 5 个灰色全宽长条

#### 5.1 病灶核查
1. **Tab 0 底部操作栏**（第 4760 行）：
   `col_act_cur, col_act_new, col_act_cs, col_act_bt = st.columns([2.8, 2.8, 2.2, 2.2])`
   在移动端被转为 4 个 100% 宽度的垂直长按钮（`覆盖当前账本`、`另存为新账本`、`下单小抄`、`送入穿透回测`）。
2. **大额流动性冲击折价表**（第 5200 行 / 2217 行）：
   小额订单（如总资产 2.66 万或 10 万）合计折价均为 `¥0.00`，依然渲染了一整个折叠框且内部带有 10 列全 0 的空表。

#### 5.2 紧凑化工程蓝图
1. **多列按钮在手机端强制 2×2 / 3×2 网格流**：
   在全局 CSS 的 `@media (max-width: 768px)` 中添加通用规约：
   ```css
   @media (max-width: 768px) {
       /* 针对包含操作按钮或 popover 的横向块，设为双列流式排布 */
       div[data-testid="stHorizontalBlock"]:has(button),
       div[data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) {
           display: flex !important;
           flex-wrap: wrap !important;
           gap: 6px !important;
       }
       div[data-testid="stHorizontalBlock"]:has(button) > div[data-testid="column"],
       div[data-testid="stHorizontalBlock"]:has([data-testid="stPopover"]) > div[data-testid="column"] {
           flex: 1 1 calc(50% - 6px) !important;
           min-width: calc(50% - 6px) !important;
       }
   }
   ```
2. **全 0 流动性折价表条件免显**：
   修改 `app_gui.py` 第 2217 行的 `render_liquidity_haircut_table`：
   ```python
   def render_liquidity_haircut_table(orders: List[Dict[str, Any]]):
       if not orders:
           return
       # 计算总折价损耗
       tot_haircut_yuan = sum(float(o.get("liquidity_haircut_yuan", 0.0)) for o in orders)
       if tot_haircut_yuan < 1.0:
           # 小额免冲击：仅输出 1 行轻量提示，彻底消灭全 0 大表
           st.caption("💧 当前调仓金额均在场外公募免冲击阈值内（流动性折价损耗 ¥0.00，执行零额外滑点）")
           return
       # 大额订单再渲染 expander 与大表
       ...
   ```

---

## 四、 关键文件修改点与代码行号索引表 (Code Reference Index)

| 目标文件 | 行号区间 | 当前代码机制 | G17 建议改造方案 |
|:---|:---|:---|:---|
| `AGY2_FundAdvisory/app_gui.py` | 1268-1284 | `grid-template-columns: repeat(4, 1fr) !important;` (未做移动端适配) | 保留桌面端样式，在下方媒体查询注入手机端 2x2 网格 |
| `AGY2_FundAdvisory/app_gui.py` | 1632-1670 | `@media (max-width: 640px)` 缺少主导航与顶栏卡片控制 | 增加顶层导航 2x2 网格 (`repeat(2, 1fr)`) 与指标卡 2x2 网格 (`calc(50% - 6px)`) |
| `AGY2_FundAdvisory/app_gui.py` | 268-373 | `render_chief_advisor_memo_card` 渲染 5 块巨型长文卡片 | 重构为 ≤110px 紧凑直显面板 (第一行结论+因果链，第二行 5 胶囊) + 抽屉展开 |
| `AGY2_FundAdvisory/app_gui.py` | 3597-3615 | 备忘录直显 + 独立 `wing_expander` 双重堆叠 | 合并为统一的「🧭 首席投顾今日裁决台」单一模块 |
| `AGY2_FundAdvisory/app_gui.py` | 2475-2515 | `switch_active_ledger` 仅改 session 变量未做导航跳转 | 新增 `if len(new_pm.holdings) > 0` 注入 `pending_cross_tab_jump` 与诊断激活标记 |
| `AGY2_FundAdvisory/app_gui.py` | 4467-4472 | `cols_9` 买入金额在第 6 列，实操要点在第 10 列 | 调整列序为「代码、名称、买入金额、目标占比、实操指引、份额、净值...」 |
| `AGY2_FundAdvisory/app_gui.py` | 5952-5959 | `cols_selected` 盈亏率在第 8 列，调仓意愿在第 9 列 | 调整列序为「代码、名称、当前市值、浮动盈亏率、累计盈亏、调仓意愿...」 |
| `AGY2_FundAdvisory/app_gui.py` | 6705-6710 | `rebal_cols_10` 建议调仓金额在第 7 列，操作在第 8 列 | 调整列序为「代码、名称、建议操作、建议调仓金额、当前市值、目标占比...」 |
| `AGY2_FundAdvisory/app_gui.py` | 2217-2255 | `render_liquidity_haircut_table` 无条件渲染全 0 表格 | 增加 `if tot_haircut_yuan < 1.0` 仅展示一行小字，免显冗余大表 |

---

## 五、 独立验证方法与回归测试方案 (Verification Method)

在实施代理完成代码落地后，建议通过以下自动化用例与视觉断言进行多维核验：

### 1. 自动化回归测试
```powershell
# 1. 核心裁判与基线测试 (必须 100% 通过)
cmd /c "set PYTHONPATH=D:\Google\Workspace\Wind\AGY2_FundAdvisory;D:\Google\Workspace\Wind && py -3 -m pytest AGY2_FundAdvisory\tests\test_infra.py"

# 2. 备忘录与时光机对抗测试 (验证 CommonMark 4 空格与备忘录渲染健壮性)
cmd /c "set PYTHONPATH=D:\Google\Workspace\Wind\AGY2_FundAdvisory;D:\Google\Workspace\Wind && py -3 -m pytest tests\test_adversarial_m2_challenger2_timemachine_and_memo.py"
```

### 2. 双视口视觉审查检查清单 (/browser http://localhost:8501)
1. **手机视口 (390x844)**：
   - 导航栏验证：确认顶层四大 Tab 呈现整齐的 2×2 网格（第一排「🌱 新资建仓」「💼 持仓调仓」，第二排「📈 组合回测」「🔍 穿透工具」），每个按钮完整清晰，「🔍 穿透工具」100% 露出且绝不发生截断或水平溢出。
   - 顶栏 4 指标卡：确认呈现 2×2 田字格，两排整齐排列，纵向高度缩减至 ~150px。
   - 首席投顾裁决台：确认首屏直显部分总高度严格 ≤ 110px，无 600 字文本框堆叠；第一行因果链公式与裁决徽章文字绝不出现纵向竖排断裂；第二行 5 颗胶囊整齐可读。
   - 账本切换跳转验证：在顶部账本下拉框选择「实战存量组合（29只·¥26,615.10）」，确认网页自动跨 Tab 跳转至「💼 持仓调仓」，且实战组合诊断（19只免赎尾仓清扫卡、三阶手术方案）立即展开呈现在首屏视野中。
   - 表格排版：检查 Tab 0、Tab 1 实时持仓与调仓表，确认首屏视野直接可见「基金名称、金额、盈亏率/占比、操作建议」，无需频繁横向拖动。
2. **桌面视口 (1920x1080)**：
   - 导航栏验证：确认顶层四大 Tab 保持一行四列全宽四宫格大胶囊质感（`repeat(4, 1fr)`）。
   - 首席投顾裁决台：第一行因果链横向展开，第二行 5 颗胶囊横向 1 行 5 列整齐排开；点击展开抽屉后平滑展开左右双翼看板，图表无错位。

---
本报告由 Explorer G17-2 全面实测与法证分析生成，所有代码引用与行号已与当前工作区 `app_gui.py` 严格校验对齐，可供后续 Implementer 代理直接落地。
