# Wind 投顾量化系统生产级重构勘测报告（R1 & R2）

> **调查员**：Explorer 1  
> **工作区目录**：`d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r6_1\`  
> **调查范围**：R1 攻防红线数据源对齐与核心指数行情条视觉升级、R2 侧边栏全局控盘与风控护栏中枢重塑  
> **勘测基线文件**：`AGY2_FundAdvisory/app_gui.py`、`AGY2_FundAdvisory/strategy_bridge.py`、`AGY2_FundAdvisory/portfolio_manager.py`、`AGY2_FundAdvisory/trading_clock_fee.py`、`AGY2_FundAdvisory/tests/test_deep_remodel_final.py`  
> **调查模式**：严格只读（Read-Only Code & Architecture Exploration）

---

## 执行摘要 (Executive Summary)

本报告针对用户在 `ORIGINAL_REQUEST.md` 中提出的 **R1（2处数据与视觉细节瑕疵修复）** 与 **R2（侧边栏功能化重塑为全局控盘与风控护栏中枢）** 进行了全链路代码穿透与架构勘测。核心结论如下：

1. **R1 攻防红线数据源漂移确证**：
   - 主看板 Card 2 正确读取了 `snapshot["trigger_lines"]`（由 `SchmidtHysteresisBuffer` 结合 MA20 与现价计算出的双向迟滞变盘线，如 `4,190` 与 `3,992`）；
   - 侧边栏（`app_gui.py:626`）目前存在**硬编码粗暴计算** `_c300 * 1.012` 与 `_c300 * 0.985`（算出 `4,102` 与 `3,992`），导致主看板与侧边栏点位**严重不一致（偏差达近 90 点）**；
   - 解决方案已精准定位至两处代码，统一收口至 `snapshot["trigger_lines"]` 单一真实数据源。

2. **R1 核心指数实时行情条视觉层级不足确证**：
   - 现有行情条的点位字号仅为 `13px`（`.index-pill-point`），指数名称仅为 `12px`，涨跌幅徽章仅为 `11px`，在宽屏下呈现为次要信息，缺乏彭博/Wind等专业金融终端的数字压迫感与行情抓眼力；
   - 依据 `GEMINI.md` 准则 14（空间几何不变量）与准则 15（Flexbox 防挤压与横向滚动规范），已精确设计 CSS 提权方案：点位提升至 `15px` 加粗等宽字体（`font-feature-settings: 'tnum'`），名称/徽章提升至 `13px`，胶囊间距扩大至 `8px`，内边距增至 `4px 10px`，确保 0 截断与 0 重叠。

3. **R2 侧边栏功能重塑架构成型**：
   - **全局目标与档位联动器**：将目前滞后于 Tab 1 的状态变量 `active_tier_val` 和 `target_return_val` 前置初始化，在侧边栏提供档位快捷切换/收益率微调，并与 Tab 1 滑块双向同步，同时联动 Tab 2 调仓与 Tab 3 回测；
   - **实盘交易风控护栏**：
     - 单日限购选择器（`["不限 (自动拆单承接)", "过滤日限额 < ¥1,000 标的", "过滤日限额 < ¥5,000 标的"]`）：联动 `fetch_realtime_fund_quota` 与 `_get_sector_alternatives`，在限额过滤开启时，将 `050025`（限额100元）等受限标的自动路由替换为同赛道无限制备选标的（如 `001071` 摩根标普500）；
     - 免折腾调仓缓冲带滑块（`1.0% ~ 5.0%`，默认 `3.0%`）：解开目前在 `app_gui.py` 与 `strategy_bridge.py` 中写死的 `0.03` / `3.0%`，无缝注入 `evaluate_today_rebalance_suitability`、`simulate_rebalance_modes_and_consequences` 与 `generate_rebalance_plan`；
   - **账本环境与快照管理**：将目前堆积在 Tab 2 顶部的 4 个大按钮中的 `🚀 加载演示组合` 与 `↩️ 一键撤销快照` 干净移入侧边栏，与全局刷新、本地湖仓底座日期（2,142 交易日完整跨牛熊）、基准资产概览整合为统一环境管理坞，彻底释放 Tab 2 第一屏人体工学空间。

---

## 第一部分：R1 攻防红线数据源对齐深度勘测

### 1.1 现状与数据流全景追踪

系统中“攻防红线”旨在给出上证/沪深300指数在技术面与动量层面的关键向上突破进攻线（`surge_line`）与向下跌破防守线（`breakdown_line`）。

```
                        【宏观行情与历史湖仓】
                                  │
                                  ▼
      strategy_bridge.py: SchmidtHysteresisBuffer.get_hysteresis_trigger_lines
           (m20_price, c300_price, upper_threshold=1.2, lower_threshold=-1.5)
                                  │
                                  ▼
       snapshot["trigger_lines"] = {"surge_line": ..., "breakdown_line": ...}
       snapshot["surge_line"] = ...
       snapshot["breakdown_line"] = ...
                                  │
                 ┌────────────────┴────────────────┐
                 ▼                                 ▼
      【主看板 Card 2】                    【侧边栏 (原实现)】
    (app_gui.py: 677-679)                  (app_gui.py: 625-627)
    读取 snapshot["trigger_lines"]          ❌ 硬编码计算:
    surge: 4,190 (以MA20为基底)            surge: c300 * 1.012 = 4,102
    breakdown: 3,992                       breakdown: c300 * 0.985 = 3,992
                 │                                 │
                 └───────────────┬─────────────────┘
                                 ▼
                       【严重数据冲突/点位不一致！】
```

### 1.2 差异与硬编码根因分析

#### 主看板 Card 2 计算链路（`app_gui.py:673-679, 744-753`）：
```python
# app_gui.py:677-679
trigger_lines = snapshot.get("trigger_lines") or {}
surge_line = float(trigger_lines.get("surge_line", snapshot.get("surge_line", c300_disp * 1.012)))
breakdown_line = float(trigger_lines.get("breakdown_line", snapshot.get("breakdown_line", c300_disp * 0.985)))

# app_gui.py:750-753
<div class="metric-card-sub" style="display: flex; justify-content: space-between; gap: 4px; color: #475569; font-size: 11px;">
    <span>📈破 {surge_line:,.0f} 进攻</span>
    <span>🛡️跌 {breakdown_line:,.0f} 防守</span>
</div>
```

#### 侧边栏计算链路（`app_gui.py:625-627`）：
```python
# app_gui.py:625-627
_c300 = snapshot.get('c300_price', 4053.0)
st.write(f"**攻防红线**：破 `{_c300*1.012:,.0f}` 进攻 ｜ 跌 `{_c300*0.985:,.0f}` 防守")
```

#### 底层算法机制（`strategy_bridge.py:1331-1365`）：
`SchmidtHysteresisBuffer.get_hysteresis_trigger_lines` 并非简单的现价百分比浮动，而是施密特双稳态触发器：
- `m20_up = m20_price * (1.0 + upper_threshold / 100.0)`
- `surge_line = round(max(m20_up, c300_price * 1.012), 1)`
- `breakdown_line = round(min(m20_down, c300_price * 0.985), 1)`

当沪深300承压于 MA20 之下时（如现价 4053，MA20 处于 4140），施密特突破线必须有效突破 MA20 生命线上方 1.2%（即 `4140 * 1.012 = 4189.7` 点），以杜绝盘中假突破骗线；而侧边栏直接用现价 `4053 * 1.012 = 4101.6` 点，两者足足相差 **88 点**！用户在侧边栏看到破 4,102 即可进攻，但主看板却显示破 4,190 才进攻，造成了严重的决策混乱。

### 1.3 核心修改点与代码级落地方案

在 `AGY2_FundAdvisory/app_gui.py` 中执行 100% 数据源统一：

#### ① 侧边栏修改（替换第 625-627 行）：
```python
# [修改前] app_gui.py:625-627
_c300 = snapshot.get('c300_price', 4053.0)
st.write(f"**攻防红线**：破 `{_c300*1.012:,.0f}` 进攻 ｜ 跌 `{_c300*0.985:,.0f}` 防守")

# [修改后] app_gui.py:625-627 (统一读取 snapshot["trigger_lines"]，保证单源同真)
_c300 = float(snapshot.get('c300_price', 4053.0))
_trig = snapshot.get("trigger_lines") or {}
_surge = float(snapshot.get("surge_line", _trig.get("surge_line", _c300 * 1.012)))
_breakdown = float(snapshot.get("breakdown_line", _trig.get("breakdown_line", _c300 * 0.985)))
st.write(f"**攻防红线**：破 `{_surge:,.0f}` 进攻 ｜ 跌 `{_breakdown:,.0f}` 防守")
```

#### ② 主看板 Card 2 读取优化（对齐第 677-679 行）：
确保 Card 2 与侧边栏读取逻辑完全镜像，优先从 `snapshot.get("surge_line")` 与 `snapshot.get("trigger_lines")` 解析，彻底消灭任何歧义。

---

## 第二部分：R1 核心指数实时行情条视觉层级提升深度勘测

### 2.1 现状 DOM 结构与 CSS 规则审计

位于 `app_gui.py:805-833` 的核心市场指数当日实时行情带（Live Index Ticker Strip）由 6 大指数（沪深300、中证500、中证1000、科创50、中证红利、标普500）组成。

#### 当前 CSS（`app_gui.py:303-381`）：
```css
.index-ticker-strip {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 8px;
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 5px 10px;
    margin-top: 4px;
    margin-bottom: 10px;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
    width: 100%;
    box-sizing: border-box;
    overflow: hidden;
}
.index-pills-scroll-wrap {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 8px;
    flex: 1 1 auto;
    min-width: 0;
    overflow-x: auto !important;
    overflow-y: hidden;
    scrollbar-width: thin;
    -webkit-overflow-scrolling: touch;
    padding: 2px 0;
}
.index-ticker-pill {
    display: inline-flex;
    align-items: center;
    justify-content: flex-start;
    gap: 6px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 3px 8px;
    flex: 0 0 auto !important;
    box-sizing: border-box;
    white-space: nowrap !important;
}
.index-pill-name {
    font-size: 12px;
    font-weight: 600;
    color: #334155;
    white-space: nowrap;
}
.index-pill-point {
    font-size: 13px;
    font-weight: 700;
    color: #0f172a;
    white-space: nowrap;
}
.index-pill-chg-up {
    font-size: 11px;
    font-weight: 700;
    color: #dc2626;
    background: #fee2e2;
    padding: 1px 5px;
    border-radius: 4px;
    white-space: nowrap;
}
.index-pill-chg-down {
    font-size: 11px;
    font-weight: 700;
    color: #16a34a;
    background: #dcfce7;
    padding: 1px 5px;
    border-radius: 4px;
    white-space: nowrap;
}
```

### 2.2 视觉痛点与层级不足

1. **点位字号过小（13px）**：点位是行情带最核心的数据资产，13px 与普通正文字号相同，无法形成主视觉焦点；
2. **缺乏等宽数字字体（Tabular Figures）**：普通字体中数字 `1` 较窄、数字 `8` 较宽，实时更新或不同指数并列时数字视觉抖动；
3. **胶囊内边距偏窄（`3px 8px`）**：组件显得紧缩拘谨，各子元素（名称、点位、徽章）间隙只有 6px，未能形成专业大屏终端的舒展排版；
4. **涨跌幅徽章字号偏小（11px）**：对比主卡片与全局标题，11px 徽章辨识度偏低。

### 2.3 GEMINI.md Rules 14 & 15 合规审查

- **Rule 14（空间几何不变量）**：
  - 各子组件相邻间距严格 $\ge 8$px；
  - 胶囊高度与内边距必须预留安全呼吸空间，保证在不同缩放比例下无垂直截断。
- **Rule 15（Flexbox 防挤压与横向滚动）**：
  - `.index-ticker-pill` 必须维持 `flex: 0 0 auto !important; white-space: nowrap !important;`；
  - 外层必须维持专属横向平滑滚动容器 `.index-pills-scroll-wrap`（配置 `overflow-x: auto !important; overflow-y: hidden; scrollbar-width: thin;`）；
  - 绝对严禁用 `overflow: hidden` 代替滚动。

### 2.4 精确 CSS 升级方案

提权后的完整 CSS 建议配置如下：

```css
/* 核心指数行情带容器微调：略微扩充内边距与最小高度 */
.index-ticker-strip {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 10px;
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 6px 12px;
    margin-top: 4px;
    margin-bottom: 10px;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
    width: 100%;
    min-height: 46px;
    box-sizing: border-box;
    overflow: hidden;
}

/* 横向平滑滚动包裹器：间距增至 10px */
.index-pills-scroll-wrap {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 10px;
    flex: 1 1 auto;
    min-width: 0;
    overflow-x: auto !important;
    overflow-y: hidden;
    scrollbar-width: thin;
    -webkit-overflow-scrolling: touch;
    padding: 3px 0;
}

/* 核心指数胶囊：内边距增至 4px 10px，间距增至 8px，刚性防挤压 */
.index-ticker-pill {
    display: inline-flex;
    align-items: center;
    justify-content: flex-start;
    gap: 8px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 4px 10px;
    flex: 0 0 auto !important;
    box-sizing: border-box;
    white-space: nowrap !important;
    min-height: 32px;
}

/* 指数名称：提权至 13px，字重 600 */
.index-pill-name {
    font-size: 13px;
    font-weight: 600;
    color: #334155;
    white-space: nowrap;
}

/* 指数点位：提权至 15px 加粗等宽字体，等宽数字特性 */
.index-pill-point {
    font-size: 15px;
    font-weight: 700;
    color: #0f172a;
    font-family: 'SF Pro Text', 'Roboto Mono', 'Consolas', 'Menlo', 'Monaco', monospace;
    font-feature-settings: 'tnum';
    letter-spacing: -0.3px;
    white-space: nowrap;
}

/* 涨跌幅徽章 (上涨)：提权至 13px，加粗等宽，微扩内边距 */
.index-pill-chg-up {
    font-size: 13px;
    font-weight: 700;
    color: #dc2626;
    background: #fee2e2;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'Consolas', 'Menlo', monospace, sans-serif;
    font-feature-settings: 'tnum';
    white-space: nowrap;
}

/* 涨跌幅徽章 (下跌)：提权至 13px，加粗等宽，微扩内边距 */
.index-pill-chg-down {
    font-size: 13px;
    font-weight: 700;
    color: #16a34a;
    background: #dcfce7;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'Consolas', 'Menlo', monospace, sans-serif;
    font-feature-settings: 'tnum';
    white-space: nowrap;
}
```

### 2.5 跨屏幕视口容量测算

- 单个胶囊宽度测算：
  - 名称（4个汉字如“中证红利”约 52px）+ 间距（8px）+ 点位（`5,689.20` 8字符约 68px）+ 间距（8px）+ 徽章（`+1.23%` 约 50px）+ 内边距（20px）+ 边框（2px）$\approx 208\text{px}$；
  - 6 个胶囊总宽度：$208 \times 6 + 10 \times 5 \approx 1,298\text{px}$；
  - 加上左侧“📊 核心指数”标题（约 85px）与右侧间距 $\approx 1,400\text{px}$。
- 视口适配情况：
  - **1920px 桌面宽屏**：除去 Streamlit 侧边栏（300px）与内容主边距，主内容区宽度约为 1200px~1400px，行情条全宽舒展展开；
  - **1366px / 1440px 笔记本视口**：内容区约 950px~1050px，`.index-pills-scroll-wrap` 自动启动原生平滑横向滚动，用户可通过鼠标滚轮或触控板无缝浏览，由于 `flex: 0 0 auto !important`，胶囊文字绝对不折行、绝对不骑头重叠、绝对不截断；
  - 完全满足 GEMINI.md Rules 14 & 15。

---

## 第三部分：R2 侧边栏功能化重塑深度勘测

### 3.1 现状与架构痛点

当前侧边栏（`app_gui.py:610-658`）被定位为静态展示卡片，存在以下核心短板：
1. **纯读无写、无法控盘**：仅以静态文本打印 `_act_t` 和 `_act_r`，用户无法直接在侧边栏调节目标参数；
2. **初始化时序颠倒**：`active_tier_val` 与 `target_return_val` 直到第 910 行（Tab 1 内部）才进行默认值初始化；侧边栏在第 613 行执行时只能使用 `st.session_state.get(..., fallback)` 盲猜；
3. **风控参数完全缺失**：单日限购过滤阈值无全局控制入口；调仓缓冲带（`min_buffer_pct`）写死在各个业务函数内部；
4. **环境操作割裂**：`🚀 加载演示组合` 和 `↩️ 一键撤销快照` 摆放在 Tab 2 内部，占据宝贵首屏垂直视口；而全局刷新却单独摆在侧边栏最下方。

### 3.2 模块一：🎯 全局目标与档位联动器 (Global Target Sync)

#### 3.2.1 状态机时序治理
将 `active_tier_val` 与 `target_return_val` 提权至侧边栏挂载之前（`app_gui.py:600-607` 区域）：
```python
if "active_tier_val" not in st.session_state:
    st.session_state.active_tier_val = "C3"
if "target_return_val" not in st.session_state:
    st.session_state.target_return_val = 15.0
```

#### 3.2.2 侧边栏交互组件与双向同步拓扑
在侧边栏提供清晰快捷的档位切换与目标收益率控制：
- 方案选择：提供 `st.selectbox` 或 `st.radio` 进行 **C1~C5 快速切换**（附带默认年化收益率，如 `C1: 6.5%`, `C2: 10.0%`, `C3: 15.0%`, `C4: 20.0%`, `C5: 30.0%`），同时支持滑动期望年化收益率（5%~100%）；
- **双向联动逻辑**：
  - 当用户在侧边栏更改档位或收益率时：
    1. 赋值 `st.session_state.active_tier_val = new_tier`
    2. 赋值 `st.session_state.target_return_val = new_ret`
    3. 同步写入 `st.session_state.slider_target_return = new_ret`（使 Tab 1 内部滑块组件状态同步更新，防止组件 state 漂移）
    4. 清空 Tab 2 诊断与调仓缓存：`st.session_state.tab2_diag_cache = None`、`st.session_state.tab2_rebal_cache = None`
  - 当用户在 Tab 1 内部拉动滑块时：
    Tab 1 的 `slider_target_return` 同样更新 `st.session_state.target_return_val` 与 `active_tier_val`，侧边栏在下一次刷新时自动同步呈现；
  - **跨 Tab 观察响应**：
    - Tab 2（持仓调仓）：因诊断缓存被清除，自动以新档位的动态基准权重（`StrategyBridge.compute_dynamic_tier_weights(tier=active_tier)`）重新进行时机裁决与温和/强行调仓推演；
    - Tab 3（回测底座）：Tab 3 每次直接读取 `st.session_state.get("active_tier_val", "C3")` 和 `st.session_state.get("target_return_val", 15.0)`（`app_gui.py:2459-2460`），侧边栏切换档位后，Tab 3 曲线与 KPI 即时刷新。

### 3.3 模块二：🛡️ 实盘交易风控护栏 (Global Execution Guardrails)

#### 3.3.1 单日限购过滤阈值（Single-Day Purchase Limit Filter）
- **UI 选择器**：
  ```python
  quota_filter_options = [
      "不限 (自动拆单承接)",
      "过滤日限额 < ¥1,000 标的",
      "过滤日限额 < ¥5,000 标的"
  ]
  selected_quota_filter = st.selectbox(
      "🛡️ 单日限购过滤阈值",
      quota_filter_options,
      index=0,
      help="开启过滤后，选基与建仓单将自动用同赛道不限购备选基金替换受限标的",
      key="sb_purchase_limit_filter"
  )
  ```
- **量化引擎中的真实映射与替代机制**：
  - 通过 `fetch_realtime_fund_quota(code)` 取得基金的当日真实限额：
    - `050025`（博时标普500ETF联接A）：状态为 `暂停申购 / 限制大额`，`daily_limit = 100.0`；
    - `018757`（睿远稳益增强30天持有C）：`daily_limit = 0.01`；
    - `001071`（摩根标普500指数A）：状态为 `开放申购`，`daily_limit = 1e11`（不限购）；
    - `002351`（易方达裕祥回报债券A）：状态为 `开放申购`，`daily_limit = 1e11`；
  - 通过 `_get_sector_alternatives(code)` 获取有序备选列表：
    - `050025` 的备选为 `['001071', '006075', '017436']`；
    - `018757` 的备选为 `['002351', '018756', '000086']`；
  - **生效链路**：
    1. 在 Tab 1 选基 (`compute_n_funds_model_portfolio`) 中：若阈值生效（如 1000 元），初筛或优化器选出 050025 时，检测其 `daily_limit (100) < 1000`，自动将其重定向为同赛道的 `001071`，并赋予对应赛道权重；
    2. 在 Tab 1 建仓单 (`generate_zero_start_blueprint`) 中：若开启过滤，直接将受限标的完整替换为备选标的，不再进行拆单，保证单据清爽利落、大额资金一次性顺畅买入；
    3. 若选择“不限 (自动拆单承接)”：保持原有的瀑布流拆单算法（首期买入 100 元，超额部分由 001071 承接）。

#### 3.3.2 免折腾调仓缓冲带（Rebalance Buffer Slider）
- **UI 滑块**：
  ```python
  rebal_buffer_pct = st.slider(
      "🛡️ 免折腾调仓缓冲带 (%)",
      min_value=1.0,
      max_value=5.0,
      value=float(st.session_state.get("rebalance_buffer_pct", 3.0)),
      step=0.5,
      format="%.1f%%",
      help="控制 Tab 2 调仓裁决与温和调仓过滤的最小偏离阈值。低于此阈值的微小偏离将自动维持现状，杜绝无效换仓摩擦",
      key="sb_rebalance_buffer"
  )
  st.session_state.rebalance_buffer_pct = rebal_buffer_pct
  ```
- **核心业务函数参数解耦**：
  - 查明硬编码位置：
    1. `strategy_bridge.py:5888, 5916`（`evaluate_today_rebalance_suitability`）：写死了 `d_max < 0.03`。需修改为接收 `min_buffer_pct=3.0`，判定 `d_max < (min_buffer_pct / 100.0)`；
    2. `strategy_bridge.py:6028`（`simulate_rebalance_modes_and_consequences`）：写死了 `min_buffer = 0.03 if is_gentle else 0.0`。需修改为 `min_buffer = (float(min_buffer_pct) / 100.0) if is_gentle else 0.0`；
    3. `app_gui.py:2340, 2357`：写死了 `min_buffer_pct=(0.0 if sel_mode_key == "mode_forced" else 3.0)`。需修改为读取 `float(st.session_state.get("rebalance_buffer_pct", 3.0))`；
    4. 前端提示文案：将 `app_gui.py:2067` 的固定文案“偏离度不足 3% 缓冲阈值不调”动态更新为 `f"偏离度不足 {rebal_buffer_pct:.1f}% 缓冲阈值不调"`。

### 3.4 模块三：🗄️ 账本环境与快照管理 (Environment & Snapshot Management)

#### 3.4.1 迁移收拢与降噪
将原先位于 Tab 2 顶部（`app_gui.py:1777-1800`）的两个高频环境按钮无损迁移至侧边栏：
```python
st.markdown("##### 🗄️ 账本环境与快照管理")
col_env1, col_env2 = st.columns(2)
with col_env1:
    if st.button("🚀 加载演示组合", use_container_width=True, help="注入包含冷启动、7天锁、待满期、深套基的完整演示组合", key="btn_sb_load_demo"):
        demo_res = pm.load_demo_portfolio()
        st.session_state.tab2_diag_cache = None
        st.session_state.tab2_rebal_cache = None
        st.session_state.tab2_diagnosed = False
        st.session_state.tab2_rebalanced = False
        st.success("✅ 演示组合已载入！")
        st.rerun()

with col_env2:
    if st.button("↩️ 一键撤销快照", use_container_width=True, help="撤销上一步操作并回滚账本", key="btn_sb_undo"):
        _undo_ok = pm.undo()
        if _undo_ok:
            st.session_state.tab2_diag_cache = None
            st.session_state.tab2_rebal_cache = None
            st.session_state.tab2_diagnosed = False
            st.session_state.tab2_rebalanced = False
            st.info("✅ 已回滚至上一快照！")
            st.rerun()
        else:
            st.warning("暂无快照可撤销")

if st.button("🔄 全局同步行情与估值", use_container_width=True, type="primary", key="btn_sb_refresh_all"):
    clear_realtime_cache()
    fetch_batch_realtime_indices(use_cache=False)
    pm.sync_holdings_live_nav(use_intraday_gsz=True)
    StrategyBridge._cached_snapshot = None
    StrategyBridge._cached_matrix = None
    StrategyBridge.get_latest_market_snapshot(force_reload=True, auto_sync=False)
    st.success("✅ 全局行情与估值已刷新！")
    st.rerun()
```

#### 3.4.2 本地数据底座与元数据披露
在侧边栏底部展示轻量级系统健康度摘要：
```python
_mat_date = snapshot.get('latest_date', '2026-11-03')
st.caption(f"📊 **本地湖仓最新日**：`{_mat_date}`（2,142 交易日）\n"
           f"💼 **当前资产基线**：¥{_tot_eq:,.2f} ｜ **持仓**：`{len(pm.holdings)} 只`\n"
           f"🛡️ **风控防线**：7天惩罚费拦截 ｜ 悲观天数防线")
```

---

## 第四部分：增量针对性测试套件 (Delta Test Suite) 设计

为严格遵守 `GEMINI.md` 准则 6（敏捷交付与分层测试精准剪枝规范）与准则 13（分层测试精准剪枝与防虚荣重复），本次勘测规划了 6 项针对 R1 与 R2 变更的增量测试（Delta Test），可直接补充至 `test_deep_remodel_final.py` 或独立的 `test_remodel_r1_r2_delta.py` 中：

| 测试用例函数名 | 验证对象 | 核心断言内容 |
|---|---|---|
| `test_r1_trigger_lines_single_source_of_truth` | R1 攻防红线一致性 | 1. 验证 `app_gui.py` 侧边栏与 Card 2 点位均严格等于 `snapshot["trigger_lines"]`；<br>2. 验证严禁存在 `c300 * 1.012` 的独立硬编码孤岛。 |
| `test_r1_core_indices_pill_css_typography` | R1 行情条 CSS 规范 | 1. 验证 `.index-pill-point` 具备 `15px` 或 `16px`、加粗 `font-weight: 700`、等宽 `monospace` 与 `font-feature-settings: 'tnum'`；<br>2. 验证名称与徽章字号为 `13px`；<br>3. 验证 `.index-ticker-pill` 保持 `flex: 0 0 auto !important;`。 |
| `test_r2_sidebar_global_target_sync` | R2 全局目标双向联动 | 1. 在 session_state 中修改 `active_tier_val` 为 `C4`，断言 Tab 2 与 Tab 3 自动以 C4 策略基准计算；<br>2. 验证侧边栏变量与 Tab 1 内部滑块 key 互不冲突且状态闭合。 |
| `test_r2_purchase_limit_guardrail_replacement` | R2 限购过滤与备选替换 | 1. 模拟开启 `过滤日限额 < ¥1,000 标的`；<br>2. 验证限额仅 100 元的 `050025` 在选基与建仓单中被 100% 自动替换为同赛道备选 `001071`；<br>3. 验证分厘严格平账且无拆单伪分散。 |
| `test_r2_rebalance_buffer_parameter_passing` | R2 调仓缓冲带动态传递 | 1. 传入 `min_buffer_pct = 4.0`，验证偏离度在 3.5% 的标的被成功裁决为 Hold；<br>2. 传入 `min_buffer_pct = 1.5`，验证偏离度在 2.0% 的标的被成功裁决为 Actionable。 |
| `test_r2_sidebar_environment_operations` | R2 侧边栏演示与撤销 | 1. 验证通过侧边栏加载演示组合能够正常重置持仓与 Alpha；<br>2. 验证撤销功能可无损回滚至上一快照。 |

---

## 第五部分：实施协同与风险防范

### 5.1 与 Explorer 2 (Tab 2 重构) 的解耦协同边界
- **边界划分**：
  - Explorer 1 (本工单) 负责：侧边栏重塑（接管演示组合、撤销、全局刷新、全局档位、风控护栏）、顶部核心指数行情条 CSS 视觉提权、攻防红线同源；
  - Explorer 2 负责：Tab 2 内部「步骤一：持仓账本」4 张高密度资产卡重排、可编辑表格精简列数与当前市值反算份额、底部「🛠️ 账本工具坞」整合；
- **交接契约**：
  - 侧边栏顺利接管 `🚀 加载演示组合` 与 `↩️ 一键撤销快照` 之后，Tab 2 第一行直接由 `col_t2_kpi1, col_t2_kpi2, col_t2_kpi3, col_t2_kpi4` 开始渲染，无需再保留冗余的全宽按钮行。

### 5.2 物理安全红线复核
- 严格遵循只读约束，严禁触碰裁判文件：
  - `judge_engine.py` (只读)
  - `holdout_vault.py` (只读)
  - `AGENT_SPEC.md` (只读)
  - `tests/test_infra.py` (只读)

---

## 结论

本次勘测已彻底查清 R1 的 2 处数据/视觉瑕疵与 R2 侧边栏重塑的全部工程细节与代码坐标。技术方案清晰、修改点精准、前后兼容性完备，可直接指导下一步的无缝实施与验证交付。
