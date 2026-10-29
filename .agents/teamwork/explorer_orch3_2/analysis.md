# AGY2 智能投顾系统 `app_gui.py` 深度代码与交互规范勘测分析报告

**勘测者**：GUI & Workflow Explorer (`explorer_orch3_2`)  
**勘测日期**：2026-10-30  
**目标工程**：`d:\Google\Workspace\Wind\AGY2_FundAdvisory`  
**核心目标代码**：`app_gui.py`（2,171 行，114,459 字节）及相关测试套件  
**模式**：只读勘测（Read-only Investigation，未修改任何业务或测试文件）

---

## 1. 勘测执行概述与架构现状

`app_gui.py` 是 AGY2 智能投顾工作台的核心前端交互与渲染模块，基于 Streamlit 框架构建，当前包含四大 Tab 工作区：
- **顶部全局状态栏**：调仓网格横幅、申赎时钟(15:00)、7 张主指标卡、实时估值/大盘点位刷新与盯盘预案提醒；
- **Tab 1（首屏默认）：【🧭 AI 投顾大脑与今日操作建议】**：
  - 步骤一：【🎯 定目标 / 测风险】定档向导（模式 A 滑块联动 / 模式 B 问卷测评）；
  - 步骤二：【🧪 现场推演看好坏】5 张大字号人话指标卡、量化归因折叠框、选基漏斗折叠框；
  - 步骤三：【📋 拿方案去执行】从 0 建仓执行单（9 列）与存量调仓执行单（16 列）；
- **Tab 2：【📈 策略历史胜率、净值回测与风控档案】**：2018-2026 实境回测净值曲线、回撤图、仓位面积图、历史相似行情匹配；
- **Tab 3：【💼 我的持仓账本与傻瓜式接管向导】**：4 步接管向导、持仓明细表编辑、全组合 FIFO 批次透视汇总；
- **Tab 4：【🔍 组合穿透诊断、在途对账与 A/C 算费工具箱】**：大类配置横向条形图、行业暴露、重仓股重叠热力图、重仓股穿透排雷大宽表、聪明钱拥挤度、在途对账、A/C 算费、场内 ETF IOPV 溢价监控。

经过对 `app_gui.py` 全局源码逐行审查以及与 `tests/` 目录中既有断言的交叉比对，梳理出 6 大关键勘测领域的现状、缺陷根因及 Agent-3 重构落地路线图。

---

## 2. 静态 `cat_map` 字典现状与统一动态分类器迁移

### 2.1 代码现状与准确定位
在 `app_gui.py` 第 1869 至 1874 行（位于 Tab 4 `box_tab1` “🎯 资产配置大类对比与缺口分析”）：

```python
# app_gui.py:1869-1874
cat_map = {
    "100032": "A股红利高股息", "005561": "A股红利低波", "011612": "科技成长进攻", "011613": "科技成长进攻",
    "016633": "中小盘成长", "016634": "中小盘成长", "161017": "中盘均衡", "001053": "中盘均衡",
    "110020": "核心蓝筹", "007339": "核心蓝筹", "000216": "黄金对冲", "000217": "黄金对冲",
    "002351": "纯债固收", "018757": "纯债固收", "050025": "美股海外对冲", "001071": "美股海外对冲"
}
```

### 2.2 调用点现状
`cat_map` 在 `app_gui.py` 中共有 4 处调用：
1. **行 1877**：`cat = cat_map.get(c, "其他存量资产")`（遍历用户当前持仓 `pm.holdings`）；
2. **行 1881**：`all_cats = sorted(list(set(list(cur_cats.keys()) + [cat_map.get(k, k) for k in snapshot["target_weights_funds"].keys()])))`（汇总当前与目标的所有大类标签）；
3. **行 1888**：`t_pct = round(sum(w for k, w in snapshot["target_weights_funds"].items() if cat_map.get(k, k) == cat) * 100.0, 2)`（计算横向分组柱状图中的模型目标大类占比）；
4. **行 1918**：`t_pct = sum(w for k, w in snapshot["target_weights_funds"].items() if cat_map.get(k, k) == cat) * 100.0`（计算大类资产配置缺口量化分析表中的目标占比）。

### 2.3 核心缺陷分析
1. **死板硬编码**：静态字典仅穷举了 16 只基金代码，违反反硬编码最高准则；
2. **赛道备选标的被误杀归为“其他存量资产”**：当用户在漏斗中替换为赛道备选金牌（如 `090010 大成红利`、`012643 华泰红利低波C`、`013841 银华集成电路`、`000086 工银纯债`），由于其未在 16 只代码中，被直接归入 `"其他存量资产"`，导致大类对比柱状图中“红利”或“纯债”显示缺口巨大，严重失真；
3. **限购拆单伴生基金分类漂移**：当 `050025` 限购 500 元触发拆单，伴生标的 `001071` 虽在字典中，但若扩展其他伴生标的将再次失真；
4. **用户自定义导入基金全部沦陷**：微信自由粘贴或 CSV 导入的任意优质基金均被归为“其他存量资产”。

### 2.4 平滑迁移建议方案
`portfolio_manager.py`（由 Agent-2 重构）应统一提供大类资产解析方法：
```python
def classify_fund_asset_class(self, fund_code: str) -> str:
    """
    统一资产分类解析器：根据基金名称、跟踪指数、投资类型与底层持仓行业，
    自动将任意基金动态归入：
    ['A股红利高股息', 'A股红利低波', '科技成长进攻', '中小盘成长', '中盘均衡', 
     '核心蓝筹', '纯债固收', '黄金对冲', '美股海外对冲', '其他存量资产']
    """
```
在 `app_gui.py` 中，彻底移除局部 `cat_map` 字典，平滑替换为：
```python
# 迁移后代码：
cur_cats = {}
for c, h in pm.holdings.items():
    cat = pm.classify_fund_asset_class(c)
    cur_cats[cat] = cur_cats.get(cat, 0.0) + h.market_value
cur_cats["可用现金"] = pm.available_cash

target_funds = snapshot["target_weights_funds"]
all_cats = sorted(list(set(list(cur_cats.keys()) + [pm.classify_fund_asset_class(k) for k in target_funds.keys()])))
# 对应 t_pct 计算也直接使用 pm.classify_fund_asset_class(k) == cat
```
此迁移完全无破坏性，且可彻底终结静态分类字典。

---

## 3. 步骤二与【立即现场推演】/切换档位：工作流白盒与演算机制

### 3.1 现状与存在问题
目前在 `app_gui.py` 的步骤二（行 633-875）：
1. **演算进度动画**（行 643-693）：
   - 使用 `st.status(...)` 与 `st.progress` 渲染 4 步进度；
   - **问题**：代码内没有任何微小延迟（`time.sleep`），在本地执行仅耗时 0.12 秒，瞬态闪烁而过，用户完全感知不到“现场推演运算”的专业仪式感与信赖感；
   - **验收标准**：R4 明确要求“整体控制在 1.2 至 1.8 秒舒适节奏的递进演算反馈”。
2. **推演面板组织结构割裂**：
   - 当前 `app_gui.py` 内部结构为：
     - 行 699-769：5 张人话指标卡（最好情况、最坏情况、水下回本、目标胜率、适合人群）；
     - 行 773-810：折叠框 `📊 【点击展开：五大人话硬核指标深度量化归因与回本推演档案】`（`expanded=False`）；
     - 行 817-875：折叠框 `🔍 【点击展开：全市场量化选基透明漏斗与备选替换】`（`expanded=False`）；
     - 行 997-1052：4 张决策卡片（趋势生命线、风格动量、大小盘结构、股债性价比），**但它们居然被放置在步骤三的场景二（存量调仓）内部！**在场景一（从 0 建仓）下用户根本看不到这 4 张核心决策卡片！
     - 行 1106-1145：手续费与回本周期卡片同样仅在场景二出现。
   - **核心矛盾**：推演白盒的 4 大步骤未能形成统一、逻辑递进的面板结构，且场景一与场景二信息严重不对称。

### 3.2 四阶量化推演白盒重构结构（R4 规范）
步骤二必须重塑为 4 个清晰独立、可自由展开/收起的推演白盒步骤面板：

| 步骤面板 | 核心展示内容 | 默认展开状态 | 关联数据源与交互组件 |
|---|---|---|---|
| **Step 1：全市场 28,177 只公募基金四级漏斗海选与金牌标的** | - 四级淘汰流指标（28,177 ➔ 6,850 ➔ 20 ➔ 5 只）<br>- 六维加权评分公式展示<br>- 《冠军标的 vs 同赛道备选六维量化评分对比表》<br>- 赛道金牌与备选替换下拉框（选基与建仓单 100% 联动） | 默认收起 (`expanded=False`) | `StrategyBridge.get_fund_selection_funnel_stats()`<br>`StrategyBridge.get_tier_quant_selection_table()`<br>`sel_alt_{sec_key}_{active_tier}` |
| **Step 2：宏观与衍生品四维状态机实时定调** | - 4 张决策信号卡片（① 趋势生命线、② 风格动量比拼、③ 大小盘结构温度、④ 宏观股债性价比与衍生品贴水/IV）<br>- 通俗白话研判结论（为什么今天系统选择进攻、震荡收息或防守） | 默认收起 (`expanded=False`) | `snapshot['m20_status_desc']`<br>`snapshot['momentum_desc']`<br>`snapshot['structure_desc']`<br>`snapshot['erp_percentile']` / `opt_iv` / `ic_basis` |
| **Step 3：2018-2026 跨牛熊 2,000+ 交易日实境回测与压力测试** | - 5 大高清晰人话指标卡（最好情况、最坏情况、极端回本、目标胜率、适合人群）<br>- 五大人话硬核指标深度量化归因<br>- 策略适合市场环境表现定位表 | 默认展开或收起 | `calculate_human_readable_metrics()`<br>`readable_kpi['suitability_table']` |
| **Step 4：交易摩擦精算、限购拆单与实盘执行清单** | - 手续费精算（预计调仓手续费 ¥X）<br>- 预计股息覆盖回本周期（X 个月内通过高股息分红平抑成本）<br>- 限购拆单路由逻辑（050025 限额 500 元 + 伴生 001071 承接） | 默认收起 (`expanded=False`) | `FeeMatrixCalculator`<br>`estimate_rebalance_impact()`<br>`split_info` |

### 3.3 现场推演节奏控制实现要点
在 `app_gui.py` 中：
```python
if st.session_state.sim_has_run:
    with st.status(f"🧠 AI 投顾引擎正在针对【{active_tier} 档位】为您现场推演...", expanded=True) as status:
        prog = st.progress(0, text="启动四阶量化推演引擎...")
        
        # Step 1
        time.sleep(0.35)
        prog.progress(25, text="Step 1/4: 全市场公募基金四级漏斗海选与金牌标的匹配...")
        
        # Step 2
        time.sleep(0.35)
        prog.progress(50, text="Step 2/4: 宏观动量与期指期权衍生品状态机多维定调...")
        
        # Step 3
        time.sleep(0.40)
        prog.progress(75, text="Step 3/4: 2018-2026 跨牛熊 2,000+ 交易日实境回测与压力精算...")
        
        # Step 4
        time.sleep(0.35)
        prog.progress(100, text="Step 4/4: 交易摩擦精算、限购拆单与实盘执行清单生成完毕！")
        
        status.update(label=f"✅ 现场推演成功（耗时 1.45 秒，数据基准时间：{st.session_state.sim_timestamp}）", state="complete", expanded=False)
```
总耗时严格控制在 `1.45 秒`（落在 `1.2 ~ 1.8 秒` 验收区间内）。

---

## 4. 顶部 7 张核心卡片现状与零截断 / ⓘ 悬停布局方案

### 4.1 布局与样式现状
`app_gui.py` 第 288-378 行定义了顶部 7 列卡片：
```python
status_col1, status_col2, status_col3, status_col4, status_col_liq, status_col5, status_col6 = st.columns(7)
```
CSS 样式定义于第 68-100 行：
- 卡片容器：`.main-metric-card { min-height: 94px; height: 94px; padding: 10px 12px; }`
- 标题：`.metric-card-title { font-size: 13px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }`
- 主数值：`.metric-value-huge { font-size: 19px; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }`
- 副标题：`.metric-card-sub { font-size: 11px; color: #64748b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }`

### 4.2 截断痛点深度剖析
1. **宽度受限**：在标准 1080p 屏幕（1920x1080）下，侧边栏展开时主内容区宽度约为 1350px，7 等分后每个卡片可用宽度仅约 175~185px（扣除 column gap）；
2. **文本溢出**：
   - 卡片 2（AI 策略大脑）：主数值展示如 `🟢 震荡收息期`（含图标 8 个字），以 19px 字体加上 12px 左右 padding，宽度超过 170px，极易在尾部出现省略号 `🟢 震荡收息...`；
   - 卡片 3（沪深300实时）：主数值 `{c300_disp:,.1f} ({bias_disp:+.1f}%)`（如 `4,053.2 (+0.5%)`）易截断；
   - 卡片 4（股债性价比）：副标题 `10Y国债: 1.82% | ERP: 5.65%` 经常截断；
   - 卡片 5（宏观流动性）：副标题 `DR007: 1.50% | 偏离: +0.0bp` 紧凑度不足。
3. **专业黑话缺乏悬停解释**：ERP、DR007、期权 IV、IC 贴水等指标对普通用户如读天书，缺乏通俗解读。

### 4.3 零截断与 ⓘ 悬停重塑方案
1. **主数值字体降噪自适应**：
   - 将 `.metric-value-huge` 的字体从 `19px` 优化为 `clamp(14px, 1.1vw, 16px)` 或统一定义为 `16px`；
   - 适当压缩内边距：`padding: 8px 10px;`；
2. **通俗白话主结论 + ⓘ 悬停原理解析**：
   - 将专业术语收纳于 HTML tooltip 或 CSS 悬停气泡中；
   - 示例卡片实现代码模版：
   ```html
   <!-- 卡片 2: AI 策略大脑 -->
   <div class="main-metric-card">
       <div class="metric-card-title">
           AI 策略大脑 
           <span title="全天候因果状态机：综合大盘趋势均线、风格动量与宏观流动性，自动识别市场所处攻防周期。" style="cursor:help; color:#94a3b8; font-size:12px;">ⓘ</span>
       </div>
       <div class="metric-value-huge" style="color: {snapshot['state_color']}; font-size: 15px;">
           {snapshot['market_state']}
       </div>
       <div class="metric-card-sub">持续 {snapshot['state_streak']} 天 ｜ 纪律防御</div>
   </div>

   <!-- 卡片 4: 股债性价比 -->
   <div class="main-metric-card">
       <div class="metric-card-title">
           股债性价比 
           <span title="股债性价比(ERP)=股票收益率-国债收益率。当前>75%极高分位代表股市处于历史便宜击球区，债券拥挤，严禁盲目割肉。" style="cursor:help; color:#94a3b8; font-size:12px;">ⓘ</span>
       </div>
       <div class="metric-value-huge" style="color: #16a34a; font-size: 15px;">
           {snapshot['erp_percentile']:.1f}% 极高分位
       </div>
       <div class="metric-card-sub">股市极便宜 ｜ 债市高拥挤</div>
   </div>
   ```
3. **保证单行完整显示无省略号**：状态名称锁定为 7 个字符以内（`🟢 震荡收息期`、`🔥 科技主升浪`、`📈 结构分化期`、`🛡️ 熊市防守期`），彻底杜绝省略号截断。

---

## 5. 步骤三《建仓/调仓执行单》与存量调仓单表格现状（9 列与无横向滚动条）

### 5.1 场景一：从 0 开始建仓执行单（行 915-968）
#### 现状审查：
1. **列数现状**：当前已定义为 9 列（第 952-956 行显式定义了 `cols_9`）：
   ```python
   cols_9 = [
       "基金代码", "基金名称", "份额", "目标占比(%)",
       "精确买入金额(元)", "最新净值", "实时估值涨跌(%)",
       "排雷与拥挤度", "实操分红与限购指引"
   ]
   ```
2. **测试强约束**：`tests/test_acceptance_r1_r7.py` 第 320 行使用正则强行断言源码中必须存在 `cols_9 = [...]` 且列表元素必须严格等于这 9 个字符串！
3. **存在问题**：
   - 最后一列“实操分红与限购指引”在行 920 生成的内容为：
     `【核心资产】分红: 现金分红 ｜ 额度: 正常 ｜ 长钱持有免赎回费更划算`（长达 35+ 字）；
   - 在 9 列表格中，该单元格文字换行混乱或导致列宽拥挤。
#### 重构方案：
- 严格保留源码中的 `cols_9` 变量名与 9 个字段名（保障 `test_acceptance_r1_r7.py` 100% 通过）；
- 将最后一列单元格文本提炼为 **15 字以内的紧凑核心动作指令**：
  - 示例 1（红利类）：`现金分红·满期免赎A`（10字）
  - 示例 2（拆单标的）：`现金分红·限额买500`（11字）
  - 示例 3（成长进攻）：`红利再投·弹性进攻C`（10字）
- 在 `st.dataframe` 的 `column_config` 中，配置表头 ⓘ 悬停指引：
  ```python
  column_config={
      "实操分红与限购指引": st.column_config.TextColumn(
          "实操分红与限购指引 ⓘ",
          help="下单实操要点：包含分红方式（高股息强制现金分红）、限额拆单路由与A/C份额长短期持有费率最优解。"
      ),
      ...
  }
  ```

### 5.2 场景二：存量持仓诊断与调仓执行单（行 1167-1205）
#### 现状审查：
当前存量调仓表格有多达 **16 列**：
```python
# app_gui.py:1172-1189
rows_display.append({
    "基金代码", "基金名称", "份额类型", "今日实时估值涨跌(%)", 
    "盘中预估盈亏(元)", "当前市值(元)", "当前占比(%)", "AI目标占比(%)", 
    "调整偏差(%)", "建议调仓金额(元)", "抱团拥挤度", "建议操作", 
    "预计手续费(元)", "执行路由", "A/C类与现金分红指引", "安全锁/风控提示"
})
```
#### 核心缺陷：
在 1080p 屏幕下必然出现巨大的横向滚动条，用户需要左右反复拖拽滚动条才能看全信息，体验极差。
#### 9 列极简精简重塑方案：
严格合并、精炼至 9 列，消除横向滚动条，并引入醒目图标直接指示调仓动作：
```python
rebal_cols_9 = [
    "基金代码", "基金名称", "份额", "当前市值(元)", 
    "目标占比(%)", "实时估值涨跌(%)", "建议调仓金额(元)", 
    "建议操作", "下单实操要点"
]
```
各字段精简与图标规范：
1. **基金代码**：6 位代码；
2. **基金名称**：精简简称；
3. **份额**：A类 / C类；
4. **当前市值(元)**：数字格式化；
5. **目标占比(%)**：ProgressColumn 进度条展示；
6. **实时估值涨跌(%)**：红绿涨跌着色；
7. **建议调仓金额(元)**：加仓为正、减仓为负；
8. **建议操作（醒目图标）**：
   - `➕ 建议加仓`：偏离度欠配且无风控拦截；
   - `➖ 建议减仓`：超配偏离且满期可卖；
   - `🔒 未满7天锁仓保护`：买入未满 7 天严禁赎回（拦截 1.5% 惩罚费）；
   - `⏳ 临近30天免赎期缓卖`：持有 7~29 天建议等待满 30 天免赎回费；
   - `✅ 维持持有`：偏离在 3% 容差内；
9. **下单实操要点**：15 字以内指令（例如 `现金分红·T+1路由`、`反弹均线阶梯减亏`），表头附带 ⓘ 悬停详细说明。

---

## 6. 《三句话看懂本方案》三栏作战卡片方案

### 6.1 现状审查
检索全工程源码，目前《三句话看懂本方案》在现有 `app_gui.py` 中尚未实现，为本次架构升级必须新增的关键交互。

### 6.2 建议新增位置
最佳位置为：**步骤二推演白盒之后、步骤三执行单之前**。  
此位置逻辑顺畅：用户刚刚查看完推演结论与回测指标，在进入具体的建仓/调仓明细表之前，通过这 3 栏作战卡片建立对方案底层逻辑、制胜机制与风控底线的深度认知与定力。

### 6.3 三栏卡片结构设计与文案规范

```
┌──────────────────────────────┬──────────────────────────────┬──────────────────────────────┐
│  💰 怎么赚钱？(收益引擎)      │  🛡️ 为什么能赢？(反脆弱对冲)  │  🚨 风险与铁律 (底线与铁律)   │
├──────────────────────────────┼──────────────────────────────┼──────────────────────────────┤
│ • 核心红利高股息打底 (稳现金流)│ • 跨大类极低相关资产对冲     │ • 历史最坏浮亏：-X.X% (-¥X)  │
│ • 动量增强捕捉科创成长弹性   │ • A股权益 + 纯债 + 黄金 + 标普│ • 最长解套等待：X 个月       │
│ • 智能拆单捕获超额 Alpha      │ • 真正全天候，东边不亮西边亮 │ • 铁律①：买入未满7天绝不赎回 │
│                             │                              │ • 铁律②：估值底部便宜区不割肉│
└──────────────────────────────┴──────────────────────────────┴──────────────────────────────┘
```

卡片 HTML / Streamlit 容器建议：
- 使用 `st.columns(3)` 布局；
- 卡片采用清新白底、细灰色边框（`border: 1px solid #cbd5e1; border-radius: 8px; background: #ffffff;`），卡片标题配备 ⓘ 悬停原理解释；
- 数值（最坏浮亏金额、解套天数）完全根据当前所选档位 `active_tier` 与拟投资金 `plan_capital` 动态计算填充，杜绝写死。

---

## 7. Streamlit AppTest 测试用例现状与断言兼容图谱

经对 `tests/` 全量测试文件审查，涉及 `app_gui.py` 的测试用例及断言清单如下：

### 7.1 `tests/test_acceptance_r1_r7.py`
| 测试方法 | 断言内容 | 重构兼容要求 |
|---|---|---|
| `test_gui_step3_table_columns_and_drawer_defaults` | 1. 源码中显式匹配 `cols_9 = [...]` 且元素严格为 9 个指定列名<br>2. 源码包含 `"排雷与拥挤度"` 与 `"实操分红与限购指引"`<br>3. 4 个折叠框默认 `expanded=False`（五大人话指标、选基漏斗、一键复制小抄、FIFO批次透视） | 必须保留 `cols_9` 变量名与原 9 列名称定义；4 个指定标题的 expander 必须保留且保持 `expanded=False` |
| `test_e2e_streamlit_slider_linkage_mode_a` | 使用 `AppTest.from_file(str(app_path), default_timeout=45)` 模拟运行：<br>- 模式 A 下切换收益率 6.0% ➔ 断言 `active_tier_val == 'C1'`<br>- 切换 25.0% ➔ 断言 `active_tier_val == 'C4'`<br>- 切换 60.0% ➔ 断言 `active_tier_val == 'C5'`<br>- 断言 `len(at.exception) == 0` | 模式 A 下滑块键名 `slider_target_return` 与 session_state 键值必须保持连续兼容；运行全程不能抛出任何异常 |

### 7.2 `tests/test_e2e_gui_render.py`
| 测试方法 | 断言内容 | 重构兼容要求 |
|---|---|---|
| `test_bug1_strategy_fn_for_tier_imported_in_app_gui` | `assert hasattr(app_gui, "strategy_fn_for_tier")` | `app_gui.py` 必须保留顶层导入 `strategy_fn_for_tier` |
| `test_bug6_streamlit_apptest_full_render` | 循环 C1 至 C5 全档位，使用 `AppTest` 完整跑通 `app_gui.py` 全部顶层代码，断言 `len(at.exception) == 0` | 任何档位渲染下，所有函数调用、DataFrame 构造、Plotly 图表构造绝不能发生 KeyError / ValueError / NameError |

### 7.3 `tests/test_ui_and_logic_refinements.py`
| 测试方法 | 断言内容 | 重构兼容要求 |
|---|---|---|
| `test_visual_contrast_and_card_colors_in_app_gui` | 1. 归因卡片标题包含高对比度色值 `#b91c1c`, `#15803d`, `#b45309`, `#0369a1`<br>2. 正文绝不允许出现 `color: #cbd5e1`<br>3. 包含 `style="font-size:11px; color:#64748b;"`<br>4. 包含 `color: #a16207;` 且不含 `#fef08a`<br>5. `.decision-card` 具有 `background: #ffffff;`<br>6. 调仓网格横幅为白底卡片且包含 `📅 <b>调仓网格倒计时</b>`<br>7. 漏斗 Step 3 展示 `st.metric("3. 5大赛道入围池", f"{funnel_stats['candidate_funds']} 只"` | 保留上述 CSS 类定义与色值声明，不得回退为暗黑背景或低对比度浅灰文本 |
| `test_first_screen_step1_compaction` | 1. 步骤一使用 `with st.container(border=True):`<br>2. 包含组件键名 `gui_scenario_mode_v2`<br>3. 包含本金输入键名 `plan_capital_input`<br>4. 包含按钮键名 `btn_run_simulation_now` | 步骤一容器必须维持 `st.container(border=True)`，上述 3 个核心组件的 key 保持不变 |

---

## 8. Agent-3 重构落地执行清单 (Actionable Checklist)

根据本次勘测结论，为 Agent-3 提供清晰的极简重构指引：

1. **分类器迁移**：
   - 彻底删除第 1869-1874 行的 `cat_map` 字典；
   - 将 4 处调用替换为 `pm.classify_fund_asset_class(code)`；
2. **四阶推演白盒重构**：
   - 在步骤二中组织 4 个独立面板（Step 1 漏斗海选与 PK 明细替换、Step 2 四维决策信号人话定调、Step 3 实境回测与五大人话指标、Step 4 交易摩擦与限购拆单）；
   - 点击【⚡ 现场推演】添加 `time.sleep(0.35)` 阶梯，将演算反馈稳定控制在 1.2~1.8 秒之间；
3. **顶部 7 张卡片防截断与 ⓘ 悬停**：
   - 主数值字体微调至 15~16px，标题与副标题引入通俗词汇，将专业黑话收进 `title="..."` 悬停提示；
4. **表格 9 列与字数控制**：
   - 建仓表格：保持 `cols_9` 列表声明不变，最后一列文本精简至 15 字以内，表头添加 ⓘ 悬停；
   - 存量调仓表格：从 16 列大宽表重构为 9 列以内，操作列添加醒目图标（`➕ 建议加仓`、`➖ 建议减仓`、`🔒 未满7天锁仓保护`、`⏳ 临近30天免赎期缓卖`）；
5. **增补《三句话看懂本方案》**：
   - 在步骤二与步骤三之间新增三栏作战卡片（收益引擎、反脆弱对冲、底线与铁律）；
6. **全量回归保障**：
   - 严格保护既有 AppTest 与排版正则断言（`cols_9`、`expanded=False`、组件 key、对比度色值），确保 100% 通过既有测试套件。
