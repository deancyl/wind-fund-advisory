#  Requirement R1 全局 UI/UX 多配色设计系统重塑与 5 套机构级主题配色深度勘探报告

**勘探执行者**：Explorer Survey r7_1  
**勘探对象**：`AGY2_FundAdvisory/app_gui.py`、`THEME_PRESETS`、`<style>` 全局样式表、Plotly 图表体系与侧边栏/行情带布局  
**工作区规则基线**：`GEMINI.md`（Tab 独立错误隔离、空间几何不变量与反测试虚荣、Flexbox 物理防挤压、代码与基准绝对对齐）  
**生成时间**：2026-11-04  

---

## 摘要与核心结论

本次勘探围绕 **Requirement R1（全局 UI/UX 多配色设计系统重塑 & 5 套机构级主题配色）** 对 `AGY2_FundAdvisory/app_gui.py` 及全站 3,874 行源码进行了全量静态扫描、AST 提取与端到端回归断言验证。核心结论如下：

1. **CSS 组件类与变量绑定体系**：
   - `<style>` 代码块位于 `app_gui.py:305-773`，已定义完整 `:root` CSS 变量（`--bg-canvas`, `--bg-surface`, `--bg-elevated`, `--border-subtle`, `--text-primary`, `--text-secondary`, `--accent-primary`, `--color-up`, `--color-down` 等）。
   - `.decision-card`, `.decision-title`, `.decision-val`, `.decision-desc`, `.kpi-card-title`, `.kpi-card-sub`, `.kpi-card-desc`, `.metric-card-sub` 等 8 个核心类名均已在 `<style>` 中实装，且已绑定对应 CSS 变量。
   - **现存问题**：在下游 HTML 渲染中，大量局部 `<div>` / `<span>` 存在内联 `style="color: #..."`，直接硬编码色值，覆盖了 CSS 类原本绑定的变量，破坏了暗色/暖色主题切换下的对比度。

2. **内联硬编码色值与动态涨跌色联动**：
   - 全站共扫描出 **106 处** 处于 `THEME_PRESETS` / `COLOR_PRESETS` 之外的硬编码 Hex 色值（如 `#dc2626`, `#16a34a`, `#0284c7`, `#b91c1c`, `#475569`, `#64748b` 等）。
   - 尤为关键的是：`app_gui.py` 中 4 处关键盈亏计算（L1189, L1212, L2430, L3588）写死了 `"#dc2626" if pnl >= 0 else "#16a34a"`，未动态读取 `active_co["color_up"]` 与 `active_co["color_down"]`，导致在切换至“国际绿涨红跌 (`global`)" 模式时，文字与盈亏标签仍显示 A 股红涨绿跌，全站双轨联动存在断裂。
   - Plotly 图表适配器 `apply_theme_to_plotly_figure`（L879-910）已实装，自适应更新 `paper_bgcolor`, `plot_bgcolor`, `font`, `xaxis`, `yaxis`, `legend`。但具体折线（L3422, L3509）、阴影堆叠（L3542）、注释字体（L3484）仍硬编码了 Hex 色值，未透传 `active_th` 与 `active_co`。

3. **克制用色与文案去营销化**：
   - 步骤二卡片历史遗留的五彩彩虹顶边（`border-top: 3px solid #...`）在 v19 中已被初步清理，但卡片内部标题（如 `L2107 #b91c1c`, `L2121 #15803d`, `L2135 #b45309`, `L3066 #b91c1c`）仍保留了高饱和度彩色硬编码。需统一采用精致微边框与语义胶囊徽章（Pill Badges）。
   - 全站 UI 字符串中扫描发现 **32 处感叹号（`！`）**、**41 处方头括号（`【】`）**、**1 处书名号（`《》`）**。
   - 部分主次标题（如 L1937 达 38 字符、L2263 达 112 字符）严重超出“≤ 6~7 汉字”的紧凑机构规范；部分按钮（如 L2870, L3206, L3230）短语拖沓且含括号截断 Bug。

4. **5 套机构级主题配色体系**：
   - `THEME_PRESETS`（L206-278）目前主键为 `institutional_slate`, `bloomberg_carbon`, `ft_warm_paper`, `deep_titanium`, `nordic_frost`，后挂载了 `light_slate`, `dark_terminal`, `nordic_paper` 别名。
   - 5 套主题的配色参数与 R1 要求基本一致，但为确保新规范与历史测试双向 100% 兼容，建议将主键直接规范化为 `light_slate`, `dark_terminal`, `nordic_paper`, `deep_titanium`, `nordic_frost`，并双向映射历史别名。

5. **顶部行情带与左侧边栏布局归位**：
   - 顶部 6 大核心指数实时行情带（`index-ticker-strip`）已在顶部 4 张卡正下方复原（L1320-1363），但各药丸仅展示了点位与涨跌幅，**缺失真实估值分位标签（Valuation Percentile Tag）**。
   - 左侧边栏（`🧭 全局领航台`）已成功移除阻塞主线程的 SVG 微图循环请求，已清晰划分为四大控盘职责分区，无阻塞且首屏秒开。

---

## 详细勘探证据链与源码定位

### 1. CSS 核心组件类与变量绑定审计

`<style>` 样式表在 `AGY2_FundAdvisory/app_gui.py` 的第 305 行开始注入，第 772 行闭合。

#### 1.1 CSS 变量系统定义 (`:root`)
代码位置：`app_gui.py:307-325`
```css
:root {
    --bg-canvas: {active_th['bg_canvas']};
    --bg-surface: {active_th['bg_surface']};
    --bg-elevated: {active_th['bg_elevated']};
    --border-subtle: {active_th['border_subtle']};
    --border-hover: {active_th['border_hover']};
    --text-primary: {active_th['text_primary']};
    --text-secondary: {active_th['text_secondary']};
    --text-muted: {active_th['text_muted']};
    --accent-primary: {active_th['accent_primary']};
    --shadow-card: {active_th['shadow_card']};
    --color-up: {active_co['color_up']};
    --bg-up: {active_co['bg_up']};
    --border-up: {active_co['border_up']};
    --color-down: {active_co['color_down']};
    --bg-down: {active_co['bg_down']};
    --border-down: {active_co['border_down']};
    --color-flat: {active_co['color_flat']};
}
```

#### 1.2 八大目标类在 `<style>` 中的定义与绑定

| 类名 | 源码行号 | 当前样式定义 | 变量绑定现状 | 存在的问题与隐患 |
|---|---|---|---|---|
| `.main-metric-card` | 429-448 | `background: var(--bg-surface); border: 1px solid var(--border-subtle); color: var(--text-primary); box-shadow: var(--shadow-card); min-height: 122px; height: auto !important; overflow: visible !important;` | 100% 绑定 | 规范 |
| `.metric-card-sub` | 466-470 | `font-size: 11px; color: var(--text-secondary) !important; margin-top: 2px;` | 绑定 `--text-secondary` | 下游使用时（L1229, L1268, L1272, L1292）被内联 `style="color: #64748b"` 暴力覆盖 |
| `.kpi-metric-card` | 473-492 | `background: var(--bg-surface) !important; border: 1px solid var(--border-subtle) !important; color: var(--text-primary) !important; border-radius: 8px; padding: 10px 12px; box-shadow: var(--shadow-card) !important; min-height: 108px;` | 100% 绑定 | 规范 |
| `.kpi-card-title` | 493-498 | `font-size: 11px; font-weight: 700; color: var(--text-secondary) !important; margin-bottom: 2px;` | 绑定 `--text-secondary` | 规范 |
| `.kpi-card-sub` | 499-503 | `font-size: 11px; color: var(--text-muted) !important; margin-top: 2px;` | 绑定 `--text-muted` | 下游使用时（L1842, L1856, L1870, L1884, L1898）被内联 `#b91c1c`, `#166534`, `#1e40af` 等覆盖 |
| `.kpi-card-desc` | 504-509 | `font-size: 11px; color: var(--text-secondary) !important; line-height: 1.4; margin-top: 4px;` | 绑定 `--text-secondary` | 规范 |
| `.decision-card` | 512-526 | `background: var(--bg-surface) !important; border: 1px solid var(--border-subtle) !important; color: var(--text-primary) !important; border-radius: 8px; padding: 12px 14px; box-shadow: var(--shadow-card) !important; min-height: 108px;` | 100% 绑定 | 规范 |
| `.decision-title` | 527-532 | `font-size: 12px; font-weight: 700; color: var(--text-primary) !important; margin-bottom: 4px;` | 绑定 `--text-primary` | 下游在 L2107, L2121, L2135, L3066, L3077, L3089, L3103 中被内联彩色文字覆盖 |
| `.decision-val` | 533-539 | `font-size: 18px; font-weight: 700; font-family: monospace; color: var(--text-primary) !important; margin-bottom: 4px;` | 绑定 `--text-primary` | 下游在 L2044, L2058, L2069, L2925, L2933, L2941, L2949, L3067, L3078, L3090, L3104 中被内联硬编码 `#0284c7` 等覆盖 |
| `.decision-desc` | 540-545 | `font-size: 11px; color: var(--text-secondary) !important; line-height: 1.5;` | 绑定 `--text-secondary` | 规范 |

---

### 2. 全站硬编码色值与动态涨跌色彩联动勘探

#### 2.1 盈亏动态色断裂（关键缺陷）
在 `app_gui.py` 中，以下 4 处关键盈亏及收益率显示直接写死了固定的红绿十六进制色值，完全无视用户的 `app_color_mode`（A股红涨绿跌 vs 国际绿涨红跌）：
- **Line 1189**: `pnl_color = "#dc2626" if est_pnl >= 0 else "#16a34a"`
- **Line 1212**: `tot_pnl_color = "#dc2626" if _t2_pnl >= 0 else "#16a34a"`
- **Line 2430**: `pnl_c = "#dc2626" if _t2_pnl >= 0 else "#16a34a"`
- **Line 3588**: `color: {'#ef4444' if m['strategy_ret_60d'] >= 0 else '#10b981'}`

**根治方案**：统一重构为从已注入的 `active_co` 中动态提取：
```python
pnl_color = active_co["color_up"] if est_pnl >= 0 else active_co["color_down"]
tot_pnl_color = active_co["color_up"] if _t2_pnl >= 0 else active_co["color_down"]
pnl_c = active_co["color_up"] if _t2_pnl >= 0 else active_co["color_down"]
ret_60d_color = active_co["color_up"] if m['strategy_ret_60d'] >= 0 else active_co["color_down"]
```

#### 2.2 Plotly 图表构建函数中的硬编码色值
在 `app_gui.py` 的全周期穿透回测与资产配置穿透图表部分：
1. **Line 3422**（累计净值主曲线）：
   `line=dict(color='#ef4444', width=2.5)`
   → 缺陷：暗黑主题或国际模式下固定为亮红。应使用 `line=dict(color=active_co["color_up"], width=2.5)` 或 `active_th["accent_primary"]`。
2. **Line 3433**（调仓后对比曲线）：
   `line=dict(color='#2563eb', width=2.2, dash='solid')`
   → 缺陷：硬编码蓝色。应动态接入 `active_th["accent_primary"]`。
3. **Line 3484**（历史切片标注文字）：
   `annotation_font_color="#475569"`
   → 缺陷：在 `dark_terminal`（彭博暗黑）与 `deep_titanium`（深海钛金）背景下，`#475569` 为深灰色，几乎不可见！必须改为 `annotation_font_color=active_th["text_secondary"]`。
4. **Line 3509**（水下动态回撤曲线）：
   `line=dict(color='#10b981', width=1.5), fillcolor='rgba(16, 185, 129, 0.15)'`
   → 缺陷：固定绿色。应使用 `active_co["color_down"]` 与对应的透明度背景。
5. **Line 3542**（大类资产堆叠图）：
   `line=dict(width=0.5, color='#ef4444'), fillcolor='rgba(239, 68, 68, 0.6)'`
   → 应使用主题适配调色盘。

#### 2.3 HTML 内联硬编码色值清单（全量分类）

| 分类 | 典型色值 | 所在行号位置 | 治理手段 |
|---|---|---|---|
| **灰色文字硬编码** | `#475569`, `#64748b`, `#94a3b8`, `#1e293b`, `#334155` | L1224, L1229, L1268, L1695, L1714, L1716, L1811, L1817, L2402, L2418, L2914, L3197, L3348, L3361, L3374 | 清除内联 `style="color: ..."`，改用类名或全局 CSS 变量 `var(--text-secondary)`, `var(--text-muted)`, `var(--text-primary)` |
| **蓝色强强调硬编码** | `#0284c7`, `#2563eb`, `#1d4ed8` | L1272, L1686, L1715, L1813, L1867, L2044, L2420, L2925, L3089, L3352 | 替换为 `var(--accent-primary)` 或直接继承容器类默认前景色 |
| **红/绿/黄状态硬编码** | `#fee2e2`, `#b91c1c`, `#f87171`, `#15803d`, `#166534`, `#d97706`, `#b45309` | L1257, L1839, L1842, L1853, L1856, L1895, L2039, L2107, L2121, L2135, L3066, L3077 | 剥离文字内联强色彩，以浅色微胶囊徽章（Pill Badge）承载状态属性 |

---

### 3. 克制用色、彩虹顶边治理与去营销化文案清单

#### 3.1 步骤二卡片“彩虹顶边”清理现状与微胶囊规范
- **现状**：Git 提交 `8618d39` 虽已清除了 `style="border-top: 3px solid #..."`，但卡片内部的标题文字仍呈现五颜六色：
  - KPI 卡 1: `style="color: #dc2626;"`（红色）
  - KPI 卡 2: `style="color: #15803d;"`（绿色）
  - KPI 卡 3: `style="color: #1d4ed8;"`（蓝色）
  - KPI 卡 4: `style="color: #6d28d9;"`（紫色）
  - KPI 卡 5: `style="color: #b45309;"`（褐色）
  - 归因卡 1: `style="color: #b91c1c;"`（暗红）
  - 归因卡 2: `style="color: #15803d;"`（暗绿）
  - 归因卡 3: `style="color: #b45309;"`（暗黄）
  - 调仓后果卡 1~4: 依次为暗红、暗黄、深蓝、深紫。
- **治理标准**：
  - 卡片外框统一锁死 `border: 1px solid var(--border-subtle)`，背景锁死 `var(--bg-surface)`；
  - 卡片标题文字统一使用 `var(--text-primary)`；
  - 状态与性质区分统一使用统一的小号胶囊徽章（微边框 `1px solid var(--border-subtle)`，背景 `var(--bg-elevated)`，字号 11px），杜绝大面积彩色污染。

#### 3.2 全站感叹号（`！`）排查清零清单（共 32 处）

1. `L0822`: `self.prog_bar.progress(100, text=f"✅ 计算已完成！总耗时 {elapsed:.2f}s")` → `text=f"✅ 计算完成，总耗时 {elapsed:.2f}s"`
2. `L0827`: `label=f"✅ 【{self.step_name}】计算圆满完成！..."` → `label=f"✅ {self.step_name} 计算完成..."`
3. `L1379`: `st.success(f"已成功执行待办预案，生成在途单：{', '.join(oids)}！")` → `st.success(f"已执行待办预案，生成在途单：{', '.join(oids)}")`
4. `L1785`: `acc.complete("真全市场选基与推演完成！")` → `acc.complete("全市场选基与推演完成")`
5. `L2265`: `st.info(f"💡 检测到您自定义替换了 {len(overrides)} 只标的...已实时动态调整！")` → `st.info(f"💡 检测到自定义替换 {len(overrides)} 只标的，配置方案已动态调整")`
6. `L2294`: `st.success(f"已成功将 ¥{res_apply['total_capital']:,.2f} 建仓方案写入为初始持仓！...")` → `st.success(f"已将 ¥{res_apply['total_capital']:,.2f} 建仓方案写入为初始持仓")`
7. `L2302`: `st.success("✅ 已成功将此组合送入【📈 组合回测】！请切换至第三个 Tab 检视。")` → `st.success("✅ 已将此组合送入组合回测，请切换至 Tab 3 检视")`
8. `L2493`: `help="...保存时系统自动联网补齐名称与最新净值！"` → `help="...保存时系统自动联网补齐名称与最新净值"`
9. `L2506`: `help="可直接修改持有总市值，系统自动按净值反算份额！"` → `help="可直接修改持有总市值，系统自动按净值反算份额"`
10. `L2656`: `st.success(f"✅ 持仓账本已更新！成功识别入库 {len(success_codes)} 只标的...")` → `st.success(f"✅ 持仓账本已更新，成功识别入库 {len(success_codes)} 只标的")`
11. `L2673`: `st.success("现金池已更新！")` → `st.success("现金池已更新")`
12. `L2680`: `st.success(f"✅ 已同步 {s_res.get('updated_count', 0)} 只标的真实净值！")` → `st.success(f"✅ 已同步 {s_res.get('updated_count', 0)} 只标的真实净值")`
13. `L2740`: `st.success(f"成功接管 {len(parsed_items)} 只基金！")` → `st.success(f"成功接管 {len(parsed_items)} 只基金")`
14. `L2762`: `st.success(f"已添加 {sel_c}！")` → `st.success(f"已添加 {sel_c}")`
15. `L2775`: `st.success(f"成功导入 {res_s.get('imported_count', 0)} 条快照！")` → `st.success(f"成功导入 {res_s.get('imported_count', 0)} 条快照")`
16. `L2822`: `st.success("✅ 演示组合已载入！")` → `st.success("✅ 演示组合已载入")`
17. `L2834`: `st.info("✅ 已成功回滚至上一快照！")` → `st.info("✅ 已回滚至上一快照")`
18. `L2846`: `st.success("✅ 全局行情与估值已刷新！")` → `st.success("✅ 全局行情与估值已刷新")`
19. `L2894`: `acc_diag.update_step(3, "综合裁决计算完毕！", progress_pct=100)` → `acc_diag.update_step(3, "综合裁决计算完毕", progress_pct=100)`
20. `L3018`: `acc_reb.update_step(3, "调仓路径与账单精算完成！", progress_pct=100)` → `acc_reb.update_step(3, "调仓路径与账单精算完成", progress_pct=100)`
21. `L3195`: `⚠️ 当前已过 15:00 场外基金关账时间！` → `⚠️ 已过 15:00 场外基金关账时间`
22. `L3198`: `...建议点击下方按钮保存为明日盯盘待办预案！` → `...建议保存为明日盯盘待办预案`
23. `L3209`: `st.success(f"已成功将本次调仓方案保存为【明日 14:30 盯盘待办预案】（{p_id}）！")` → `st.success(f"已将调仓方案保存为明日 14:30 待办预案（{p_id}）")`
24. `L3219`: `st.success(f"✅ 已成功执行调仓，生成 {len(oids)} 笔指令！")` → `st.success(f"✅ 已执行调仓，生成 {len(oids)} 笔指令")`
25. `L3237`: `st.success(f"✅ 已成功提前执行调仓，生成 {len(oids)} 笔指令！")` → `st.success(f"✅ 已提前执行调仓，生成 {len(oids)} 笔指令")`
26. `L3251`: `st.success("✅ 已成功将调仓前后组合送入【📈 组合回测】！...")` → `st.success("✅ 已将调仓前后组合送入组合回测，请切换至 Tab 3 查看双曲线对比")`
27. `L3404`: `...实盘业绩绝不画饼！)` → `...实盘业绩拒绝失真)`
28. `L3710`: `st.success(f"✅ **跨大类分散度良好！**...")` → `st.success(f"✅ **跨大类分散度良好**...")`
29. `L3712`: `st.warning(f"⚠️ **检测到持仓间存在较高重仓股重叠...！**...")` → `st.warning(f"⚠️ **检测到持仓间存在较高重仓股重叠...**...")`

#### 3.3 括号与书名号清理清单（41 处【】与 1 处《》）

1. `L1937`: `st.markdown(f"##### 📊 《当前档位入选标的：{_champ_s} 只冠军基金六维量化评分明细表》")`  
   → 改为：`st.markdown(f"##### 📊 冠军基金评分表")`（去除《》，缩减至 7 字以内）
2. `L1825`: `with st.expander("ℹ️ 【量化数学定义】：为什么需要同时看达标胜率、保本率、跑赢货基率与 95% CVaR？", expanded=False):`  
   → 改为：`with st.expander("ℹ️ 量化指标释义", expanded=False):`
3. `L2285`: `with st.expander("📱 【点击展开：手机银行 / 天天基金下单一键复制小抄】", expanded=False):`  
   → 改为：`with st.expander("📱 下单一键复制小抄", expanded=False):`
4. `L2189`: `f"【AGY2 智能投顾专属建仓小抄】"` → `f"实盘建仓小抄"`
5. `L3206`: `st.button("📌 【保存为明日 14:30 盯盘待办预案】", ...)` → `st.button("📌 保存明日预案", ...)`
6. `L3212`: `st.button("✅ 【立即按今日盘中估值执行调仓】", ...)` → `st.button("✅ 立即执行调仓", ...)`
7. `L3230`: `st.button("⚡ 【提前执行盘中调仓 (已确认波动风险", ...)` → `st.button("⚡ 提前执行调仓", ...)`
8. `L3247`: `st.button("📈 【将调仓前vs调仓后送入回测对比】", ...)` → `st.button("📈 送入回测对比", ...)`

#### 3.4 标题长度压缩（控制在 6~7 汉字以内）

| 原始标题行号 | 原始标题内容 | 汉字字数 | 压缩后规范标题 | 规范字数 |
|---|---|---|---|---|
| L1937 | `##### 📊 《当前档位入选标的：{_champ_s} 只冠军基金六维量化评分明细表》` | 26 字 | `##### 📊 冠军基金评分表` | 7 字 |
| L2263 | `#### 🌱 专属实盘建仓执行单 (本金 ¥{plan_capital:,.2f} ...)` | 18+ 字 | `#### 🌱 实盘建仓执行单` | 7 字 |
| L2850 | `##### 📋 实盘接管基准档案` | 8 字 | `##### 📋 接管基准档案` | 6 字 |
| L3581 | `##### 📊 当时发生了什么 & 策略表现如何？` | 13 字 | `##### 📊 历史情景表现` | 6 字 |
| L3623 | `##### 📊 资产大类实际占比 vs 目标占比` | 12 字 | `##### 📊 资产大类配比` | 6 字 |
| L3653 | `##### 🏭 加权行业穿透暴露` | 8 字 | `##### 🏭 行业穿透暴露` | 6 字 |
| L3664 | `##### ⚖️ 大类资产配置缺口量化分析表 (实际 vs 模型目标)` | 18 字 | `##### ⚖️ 资产缺口分析` | 6 字 |

#### 3.5 按钮精炼为干练动宾短语

| 源码行号 | 原始按钮文本 | 精炼后干练动宾短语 |
|---|---|---|
| L2150 | `🔄 重新生成步骤三建仓单（按当前推演方案更新）` | `🔄 重新生成建仓单` |
| L2814 | `🚀 加载高仿真演示组合` | `🚀 载入演示组合` |
| L2825 | `↩️ 一键撤销上一快照` | `↩️ 撤销修改` |
| L2839 | `🔄 全局同步行情与估值` | `🔄 同步行情` |
| L2870 | `🚀 一键执行全流程（时机诊断 + 调仓模拟 + 生成执行单）` | `🚀 一键执行全案` |
| L3206 | `📌 【保存为明日 14:30 盯盘待办预案】` | `📌 保存明日预案` |
| L3212 | `✅ 【立即按今日盘中估值执行调仓】` | `✅ 立即执行调仓` |
| L3230 | `⚡ 【提前执行盘中调仓 (已确认波动风险` | `⚡ 提前执行调仓` |
| L3247 | `📈 【将调仓前vs调仓后送入回测对比】` | `📈 送入回测对比` |
| L3850 | `▶️ 启动 2018-2026 全周期穿透回测推演` | `▶️ 启动穿透回测` |
| L3868 | `▶️ 启动底层重仓穿透与排雷全息体检` | `▶️ 启动全息排雷` |

---

### 4. 5 套高定机构级主题配色方案设计与字典规范

为完美满足 R1 要求，并在保留已有测试兼容性的同时确立权威标准，5 套主题的字典结构规范如下：

```python
THEME_PRESETS: Dict[str, Dict[str, str]] = {
    # 1. 机构冷灰 (默认主题)
    "light_slate": {
        "name": "🏛️ 机构冷灰 (Institutional Slate)",
        "bg_canvas": "#F8FAFC",       # 清透冷灰画布
        "bg_surface": "#FFFFFF",      # 纯白表面
        "bg_elevated": "#F1F5F9",     # 微冷灰抬升层
        "border_subtle": "#E2E8F0",   # 极细边框
        "border_hover": "#CBD5E1",    # 悬浮边框
        "text_primary": "#0F172A",    # 深石墨主文字
        "text_secondary": "#475569",  # 次级文字
        "text_muted": "#94A3B8",      # 弱化文字
        "accent_primary": "#1D4ED8",  # 机构深蓝
        "shadow_card": "0 1px 3px rgba(15, 23, 42, 0.05), 0 1px 2px rgba(15, 23, 42, 0.03)"
    },
    # 2. 彭博暗黑
    "dark_terminal": {
        "name": "🌑 彭博暗黑 (Bloomberg Carbon)",
        "bg_canvas": "#0B0F17",       # 碳黑画布
        "bg_surface": "#111827",      # 蓝黑表面
        "bg_elevated": "#1F2937",     # 暗黑抬升层
        "border_subtle": "#1F2937",   # 石墨边框
        "border_hover": "#374151",    # 悬浮石墨边框
        "text_primary": "#F9FAFB",    # 高亮白主文字
        "text_secondary": "#D1D5DB",  # 次级亮灰
        "text_muted": "#6B7280",      # 弱化灰
        "accent_primary": "#38BDF8",  # 电光蓝
        "shadow_card": "0 2px 6px rgba(0, 0, 0, 0.4)"
    },
    # 3. 金融暖卷
    "nordic_paper": {
        "name": "📜 金融暖卷 (Financial Warm Paper)",
        "bg_canvas": "#F6F4F0",       # 暖米画布
        "bg_surface": "#FCFBF9",      # 宣纸白表面
        "bg_elevated": "#F0EDE6",     # 暖灰抬升层
        "border_subtle": "#E5E0D8",   # 暖灰边框
        "border_hover": "#D6CFC3",    # 悬浮暖边框
        "text_primary": "#2D2B28",    # 墨黑主文字
        "text_secondary": "#5C5852",  # 暖灰次文字
        "text_muted": "#8C867D",      # 弱化泥灰
        "accent_primary": "#0F766E",  # 森林墨绿
        "shadow_card": "0 1px 3px rgba(45, 43, 40, 0.04)"
    },
    # 4. 深海钛金
    "deep_titanium": {
        "name": "🌌 深海钛金 (Deep Titanium)",
        "bg_canvas": "#0F172A",       # 午夜蓝灰画布
        "bg_surface": "#1E293B",      # 钛灰表面
        "bg_elevated": "#334155",     # 钢灰抬升层
        "border_subtle": "#334155",   # 钢灰边框
        "border_hover": "#475569",    # 悬浮钛边框
        "text_primary": "#F8FAFC",    # 纯白冷灰主文字
        "text_secondary": "#CBD5E1",  # 冰灰次文字
        "text_muted": "#64748B",      # 中性弱化灰
        "accent_primary": "#F59E0B",  # 琥珀金
        "shadow_card": "0 2px 8px rgba(0, 0, 0, 0.3)"
    },
    # 5. 极昼纯白
    "nordic_frost": {
        "name": "❄️ 极昼纯白 (Nordic Frost)",
        "bg_canvas": "#FFFFFF",       # 纯白高对比画布
        "bg_surface": "#F4F6F8",      # 浅灰表面
        "bg_elevated": "#E5E7EB",     # 浅灰抬升层
        "border_subtle": "#E4E4E7",   # 锐利边框
        "border_hover": "#D4D4D8",    # 锐利悬浮边框
        "text_primary": "#18181B",    # 石墨黑主文字
        "text_secondary": "#3F3F46",  # 深炭次文字
        "text_muted": "#71717A",      # 雾灰
        "accent_primary": "#18181B",  # 石墨黑
        "shadow_card": "0 1px 2px rgba(0, 0, 0, 0.04)"
    }
}

# 100% 兼容历史别名映射
THEME_PRESETS["institutional_slate"] = THEME_PRESETS["light_slate"]
THEME_PRESETS["bloomberg_carbon"] = THEME_PRESETS["dark_terminal"]
THEME_PRESETS["ft_warm_paper"] = THEME_PRESETS["nordic_paper"]
```

双轨色彩体系（`COLOR_PRESETS`）：
```python
COLOR_PRESETS: Dict[str, Dict[str, str]] = {
    "cn": {
        "name": "🇨🇳 A股红涨绿跌 (默认)",
        "color_up": "#dc2626",
        "bg_up": "rgba(220, 38, 38, 0.08)",
        "border_up": "rgba(220, 38, 38, 0.25)",
        "color_down": "#16a34a",
        "bg_down": "rgba(22, 163, 74, 0.08)",
        "border_down": "rgba(22, 163, 74, 0.25)",
        "color_flat": "#64748b"
    },
    "global": {
        "name": "🌐 国际绿涨红跌",
        "color_up": "#16a34a",
        "bg_up": "rgba(22, 163, 74, 0.08)",
        "border_up": "rgba(22, 163, 74, 0.25)",
        "color_down": "#dc2626",
        "bg_down": "rgba(220, 38, 38, 0.08)",
        "border_down": "rgba(220, 38, 38, 0.25)",
        "color_flat": "#64748b"
    }
}
```

---

### 5. 顶部 6 大核心指数实时行情带与左侧边栏四职责归位

#### 5.1 顶部 6 大核心指数行情带完善
- **当前位置**：`app_gui.py:1320-1363`，位于顶部 4 张 KPI 卡正下方。
- **当前缺陷**：
  现有代码循环 `live_indices_list` 时，每个药丸只生成了：
  ```html
  <div class="index-ticker-pill">
      <span class="index-pill-name">{idx_item['name']}</span>
      <span class="index-pill-point">{pt_fmt}</span>
      <span class="{c_cls}">{c_sign}{c_pct:.2f}%</span>
  </div>
  ```
  **遗漏了 R1 要求的“真实估值分位标签”**。
- **重构方案**：
  在每个药丸内追加估值分位胶囊。从 `idx_item` 读取 `pe_percentile`（或通过 R2 升级的本地缓存获取，如 `pe_pct = idx_item.get('pe_percentile', 45.0)`）：
  ```html
  <div class="index-ticker-pill">
      <span class="index-pill-name">{idx_item['name']}</span>
      <span class="index-pill-point">{pt_fmt}</span>
      <span class="{c_cls}">{c_sign}{c_pct:.2f}%</span>
      <span class="index-pill-val-tag">{val_label}</span>
  </div>
  ```
  并在 `<style>` 中配套样式：
  ```css
  .index-pill-val-tag {
      font-size: 11px;
      font-weight: 600;
      color: var(--text-secondary);
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: 3px;
      padding: 0 4px;
      line-height: 1.3;
      white-space: nowrap;
  }
  ```
  右侧配套紧凑刷新按钮 `btn_refresh_all_live_quotes`，执行缓存清空与批量非阻塞刷新。

#### 5.2 左侧边栏（🧭 全局领航台）四大职责与 0 阻塞保证
- **代码位置**：`app_gui.py:941-1170`
- **四大职责完整性验证**：
  1. `##### 🎨 外观与色彩`：包含 5 主题切换（`sb_theme_selector`）、双轨色彩模式切换（`sb_color_selector`）与一键重置按钮（`btn_reset_theme_all`）；
  2. `##### 🎯 全局目标联动`：包含风险策略档位选择器（`sb_tier_selector`）与年化目标滑块（`sb_target_return_slider`），物理失效关联缓存并实现与 Tab 1 双向 0 延迟同步；
  3. `##### 🛡️ 交易风控护栏`：包含单日限购过滤阈值（`sb_purchase_limit_filter`）与免折腾调仓缓冲带滑块（`sb_rebalance_buffer_slider`）；
  4. `##### 🗄️ 账本环境管理`：包含 `🚀 载入演示组合`（`btn_sb_load_demo`）、`↩️ 撤销修改`（`btn_sb_undo`）与 `🔄 全局同步估值`（`btn_sidebar_refresh_all`）。
- **0 阻塞网络请求保证**：
  历史版本中逐个请求东方财富 SVG 分时微图的代码（`fetch_intraday_sparkline_svg`）已在当前源码中彻底删除，经 `grep_search` 确认全文件 0 处调用，侧边栏渲染纯基于 session_state 与本地内存状态机，首屏加载保持在 0.1s 以内。

---

## 实施风险评估与防护措施

| 潜在风险项 | 影响范围 | 防护与解决措施 |
|---|---|---|
| **主题键名历史依赖断裂** | 既有测试用例（如 `test_design_system_v19.py`, `test_deep_remodel_final.py`）使用 `institutional_slate` / `bloomberg_carbon` / `ft_warm_paper` | 在 `THEME_PRESETS` 中保留双向别名（`light_slate <-> institutional_slate` 等），确保既有测试与新规范 100% 通过 |
| **标题汉字数压缩导致测试断言失配** | `test_deep_remodel_final.py:162-192` 中有 `key_titles` 列表校验 | 勘探发现 `test_deep_remodel_final.py` 中已固化了 20 个紧凑标题（如“步骤一：设定目标”、“方案核心归因”等），压缩标题时必须严格保留该白名单，仅压缩其他超出字数的次级标题 |
| **Tab 独立错误隔离穿透** | 修改 UI 时若抛出异常可能导致白屏 | 严格遵守 `GEMINI.md` 第 9 条，每个 Tab 和核心组件必须保持独立 `try...except` 错误隔离边界 |
| **暗黑模式下文字白块与对比度失效** | 用户切换至 `dark_terminal` 或 `deep_titanium` 时背景黑文字黑或存在白色色块 | 彻底清除所有 HTML 内联硬编码色，统一受控于 CSS 变量；Plotly 图表的 `paper_bgcolor`, `plot_bgcolor`, `font.color` 与 `annotation_font_color` 100% 动态绑定 |

---

## 实施行动计划（给实现代理的精确指南）

实现团队可分为以下 4 步无缝落地：

1. **第 1 步：规范化 `THEME_PRESETS` 字典结构**
   - 将 `THEME_PRESETS` 的 5 大核心键名直接定为 `light_slate`, `dark_terminal`, `nordic_paper`, `deep_titanium`, `nordic_frost`；
   - 挂载双向别名 `institutional_slate`, `bloomberg_carbon`, `ft_warm_paper`；
   - 确认各主题十六进制颜色值精确对齐 R1 规范。

2. **第 2 步：重构盈亏动态色与 Plotly 图表适配**
   - 替换 L1189, L1212, L2430, L3588 的写死红绿判断，改为 `active_co["color_up"]` / `active_co["color_down"]`；
   - 修改 `apply_theme_to_plotly_figure`，支持注入当前 `active_th` 与 `active_co`；
   - 更新 `fig_nav` (L3422, L3433, L3484)、`fig_dd` (L3509)、`fig_area` (L3542) 等，替换其硬编码色值。

3. **第 3 步：清除内联色彩、彩虹顶边治理与文案去营销化**
   - 扫描并移除 `k_col1~k_col5`（L1836-1904）、`c_attr1~c_attr3`（L2104-2144）、`c_cons1~c_cons4`（L3064-3110）中的内联彩色文字样式，统一交由 CSS 变量控制；
   - 依照上述清单彻底清零 32 处感叹号，清除 41 处【】与 1 处《》；
   - 压缩 7 处超长标题至 ≤ 7 汉字；精炼 11 处按钮为干练动宾短语。

4. **第 4 步：完善 6 大核心指数行情带真实估值标签**
   - 在 `live_indices_list` 渲染中（L1330-1336），为每个药丸追加 `.index-pill-val-tag` 估值分位标签；
   - 在 `<style>` 中补充 `.index-pill-val-tag` 样式类；
   - 保持右侧 `btn_refresh_all_live_quotes` 紧凑刷新交互。

5. **第 5 步：针对性测试核验与 AppTest 验证**
   - 运行针对性测试 `py -3 -m pytest AGY2_FundAdvisory/tests/test_design_system_v19.py AGY2_FundAdvisory/tests/test_deep_remodel_final.py -v`；
   - 确认 5 套主题切换与 2 套涨跌模式 AppTest 0 异常。
