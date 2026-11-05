# Handoff Report: R2 UI/UX 信息架构重塑与视觉呈现深度调研

**Working Directory**: `d:\Google\Workspace\Wind\.agents\teamwork\teamwork_explorer_prod_3`  
**Target Milestone**: R2 — UI/UX Information Architecture & Visual Redesign in `app_gui.py`  
**Investigator**: Teamwork Explorer 3  
**Date**: 2026-11-03  

---

## 1. Observation (客观观察与直接代码依据)

### 1.1 侧边栏强行隐藏与 CSS 注入现状
- **代码位置**: `AGY2_FundAdvisory/app_gui.py:186-210`
```python
186: st.set_page_config(
187:     page_title="AGY2 智能投顾与实盘组合接管工作台",
188:     page_icon="🧭",
189:     layout="wide",
190:     initial_sidebar_state="collapsed"
191: )
192: 
193: # 自定义 CSS 强化桌面客户端质感（含彻底隐藏 Stop / Deploy / 汉堡菜单）
194: st.markdown("""
195: <style>
196:     /* 彻底隐藏侧边栏与展开控制箭头，实现 100% 满宽沉浸式体验 */
197:     [data-testid="stSidebar"], [data-testid="collapsedControl"], section[data-testid="stSidebar"] {
198:         display: none !important;
199:         visibility: hidden !important;
200:         width: 0 !important;
201:     }
202:     header[data-testid="stHeader"], [data-testid="stHeader"], .stAppHeader {
203:         visibility: hidden !important;
204:         display: none !important;
205:         height: 0 !important;
206:     }
207:     [data-testid="stToolbar"], .stDeployButton, [data-testid="stStatusWidget"], #MainMenu, footer, [data-testid="stHeaderActionElements"] {
208:         visibility: hidden !important;
209:         display: none !important;
210:     }
```
- **观察结论**:
  - `[data-testid="stSidebar"], [data-testid="collapsedControl"], section[data-testid="stSidebar"]` 设定了 `display: none !important;`，彻底从 DOM 视觉上消灭了侧边栏及展开箭头。
  - `header[data-testid="stHeader"]` 设置了 `display: none !important; height: 0 !important;`。在现代 Streamlit 中，侧边栏折叠按钮（`collapsedControl`）挂载于顶部 header 区域。如果将 header 设为 `display: none`，则折叠状态下的侧边栏展开箭头将无法点击展开。
  - 全文搜索 `st.sidebar` 发现 `app_gui.py` 中当前完全没有 `with st.sidebar:` 结构。

### 1.2 顶部 6 大核心指数行情带排版现状
- **代码位置**: `AGY2_FundAdvisory/app_gui.py:636-676` 与 CSS `app_gui.py:226-271`
```python
639: live_indices_list = fetch_batch_realtime_indices(use_cache=True)
640: pill_html_parts = []
641: for idx_item in live_indices_list:
642:     c_pct = idx_item["change_pct"]
643:     c_cls = "index-pill-chg-up" if c_pct > 0 else ("index-pill-chg-down" if c_pct < 0 else "")
644:     c_sign = "+" if c_pct > 0 else ""
645:     pill_html_parts.append(f"""
646:         <div class="index-ticker-pill">
647:             <span class="index-pill-name">{idx_item['name']}</span>
648:             <span class="index-pill-point">{idx_item['point']:,.2f}</span>
649:             <span class="{c_cls}">{c_sign}{c_pct:.2f}%</span>
650:         </div>
651:     """)
652: 
653: ticker_inner_html = "\n".join(pill_html_parts)
654: strip_col_ticker, strip_col_btn = st.columns([8.2, 1.8])
655: 
656: with strip_col_ticker:
657:     safe_markdown_html(f"""
658:     <div class="index-ticker-strip">
659:         <span style="font-size: 13px; font-weight: 700; color: #1e293b; display: flex; align-items: center; gap: 4px; flex-shrink: 0;">
660:             📊 核心指数实时行情
661:         </span>
662:         {ticker_inner_html}
663:     </div>
664:     """)
665: 
666: with strip_col_btn:
667:     safe_markdown_html("<div style='height: 8px;'></div>")
668:     if st.button("🔄 刷新实时行情与估值", ...):
```
- **CSS 观察**:
```css
    .index-ticker-strip {
        display: flex;
        flex-direction: row;
        align-items: center;
        gap: 8px;
        ...
        overflow-x: auto;
        white-space: nowrap;
        width: 100%;
    }
    .index-ticker-pill {
        display: inline-flex;
        ...
        flex: 1 1 0;
        min-width: 120px;
    }
```
- **问题观察**:
  1. 行情带右侧被 `strip_col_btn = st.columns([8.2, 1.8])` 的刷新按钮挤压了 18% 宽度；
  2. 行情带内包含占位约为 140px 的文本标题 `📊 核心指数实时行情`；
  3. 6 只标的胶囊设置了 `min-width: 120px; gap: 8px;`，总宽度要求至少 `140 + 6 * 120 + 5 * 8 = 900px`。当侧边栏展开后，屏幕剩余宽度 82% 往往不足 900px，必然触发 `overflow-x: auto` 横向滚动条或导致后部指数被截断。

### 1.3 四大量化模型表格与六维打分展示现状
- **代码位置**: `AGY2_FundAdvisory/app_gui.py:964-974` 及 `1160-1175`
```python
964: with st.expander("🔍 【点击展开】：四大机构级量化模型特性与适用场景全景对比", expanded=False):
965:     model_table_rows = []
966:     for m_k, m_info in QUANT_MODELS_CATALOG.items():
967:         model_table_rows.append({
968:             "模型名称": m_info["name"],
969:             "机构评级标签": m_info["badge"],
970:             "数学与量化原理": m_info["principle"],
971:             "核心优势": m_info["advantage"],
972:             "最适用市场环境": m_info["suitable_when"]
973:         })
974:     st.dataframe(pd.DataFrame(model_table_rows), use_container_width=True, hide_index=True)
```
```python
1160: st.markdown("##### 📐 《六维量化打分加权公式（0~100分归一化）》")
1161: st.info("综合评分计算公式：总评得分 (0-100) = 35% * 历史超额Alpha得分 + 25% * 低费率得分 + 15% * R1底层排雷健康分 + 10% * R3北向聪明钱流入分 + 10% * 反拥挤度安全分 + 5% * 衍生品与宏观契合度")
```
- **问题观察**:
  - 模型说明使用 `st.dataframe` 展示长文本列（如“数学与量化原理”、“核心优势”），在 Streamlit 表格中长文本单行折叠截断，用户必须双击单元格才能看到内容；
  - 评分公式仅有一句静态 `st.info` 文本，未披露各个维度的 0~100 分判定规则与扣分标准。

### 1.4 「方案核心逻辑（三句话看懂本方案）」排版现状
- **代码位置**: `AGY2_FundAdvisory/app_gui.py:1303-1353`
```python
1304: st.markdown("#### 🎯 《三句话看懂本方案：怎么赚钱、为什么能赢、风险与铁律》")
1305: col_card1, col_card2, col_card3, col_card4 = st.columns(4)
1306: with col_card1:
        # 💰 ① 怎么赚钱？(纯静态文案)
1318: with col_card2:
        # 🏆 ② 为什么能赢？(纯静态文案)
1330: with col_card3:
        # 🚨 ③ 风险与底线 (仅带 worst_case_drawdown_pct 与 max_underwater_days)
1342: with col_card4:
        # ⚖️ ④ 执行铁律 (纯静态文案)
```
- **问题观察**:
  - 当前分为 4 列，导致每张卡片极窄（每张卡片宽度仅约 23%），文字纵向拉长；
  - 卡片 1、卡片 2 和卡片 4 全部为硬编码静态套话，并未动态读取当前推演组合中真实的防守类（纯债/红利）与进攻类比例、未点名最大权重标的，也未代入当前选取的量化模型特性。

### 1.5 全站标题字数审计（超过 7 个汉字）
通过脚本 `audit_titles_detailed.py` 全量扫描，发现共 38 处标题/折叠框标题超过 7 个汉字：
1. `L680`: `📌 **您有已锁定的【{latest_plan.get('target_date')} 盯盘待办预案】** (创建于 {latest_plan.get('created_at')})` (15汉字)
2. `L791`: `### 步骤一：设定目标风险` (9汉字)
3. `L964`: `🔍 【点击展开】：四大机构级量化模型特性与适用场景全景对比` (24汉字)
4. `L1014`: `### 步骤二：现场推演评估` (9汉字)
5. `L1051`: `#### 🎯 2018-2026 全周期跨牛熊滚动持有胜率 (同温层状态机条件加权)` (22汉字)
6. `L1064`: `ℹ️ 【量化数学定义】：为什么需要同时看达标胜率、保本率、跑赢货基率与 95% CVaR？` (27汉字)
7. `L1145`: `🔍 【点击展开白盒推演详情】：全市场选基漏斗与赛道冠军打分表` (25汉字)
8. `L1160`: `##### 📐 《六维量化打分加权公式（0~100分归一化）》` (14汉字)
9. `L1163`: `##### 📊 《当前档位入选标的：{_champ_s} 只冠军基金六维量化评分明细表》` (22汉字)
10. `L1244`: `🧭 【点击展开白盒推演详情】：宏观流动性、风格动量与衍生品四维因果决策信号` (31汉字)
11. `L1249`: `① 市场温度与估值水位` (9汉字)
12. `L1294`: `④ 期权波动率防波堤 (iVIX)` (8汉字)
13. `L1304`: `#### 🎯 《三句话看懂本方案：怎么赚钱、为什么能赢、风险与铁律》` (22汉字)
14. `L1369`: `### 步骤三：生成实盘建仓` (9汉字)
15. `L1492`: `📱 【点击展开：手机银行 / 天天基金下单一键复制小抄】` (20汉字)
16. `L1555`: `### 步骤一：当前持仓账本` (9汉字)
17. `L1612`: `📋 实盘接管档案（接管基准、峰值资产、最大回撤与 Alpha）` (19汉字)
18. `L1772`: `📦 【点击展开：全组合 FIFO 批次透视与免赎回费倒计时】` (19汉字)
19. `L1816`: `### 步骤二：调仓时机裁决` (9汉字)
20. `L1898`: `### 步骤三：调仓方案执行` (9汉字)
21. `L1969`: `#### 🧾 《本次调仓四大真实后果量化账单》` (14汉字)
22. `L1998`: `🛡️ ③ 组合攻防与回撤变化` (9汉字)
23. `L2012`: `🔄 ④ 持有期清零重算后果` (9汉字)
24. `L2317`: `#### 🚀 2018-2026 全周期真实净值推演曲线 (对标 {len(selected_bms)} 只自选基准指数)` (20汉字)
25. `L2405`: `##### 🌊 动态水下回撤对比图 (Underwater Drawdown %)` (9汉字)
26. `L2441`: `##### 📊 历史大类资产仓位变迁面积图 (Stacked Area %)` (13汉字)
27. `L2470`: `#### 📜 6 大历史市场风格切片全胜战报 (Gate B 考核通过)` (17汉字)
28. `L2476`: `#### 🔍 历史相似行情与宏观同温层匹配器 (History Analog Matcher)` (15汉字)
29. `L2483`: `##### 📊 当时发生了什么 & 策略表现如何？` (13汉字)
30. `L2525`: `##### 📊 资产大类实际占比 vs 目标占比` (12汉字)
31. `L2555`: `##### 🏭 加权行业穿透暴露` (8汉字)
32. `L2566`: `##### ⚖️ 大类资产配置缺口量化分析表 (实际 vs 模型目标)` (19汉字)
33. `L2604`: `#### ⚠️ 前十大重仓股重叠交叉检测与热力图` (16汉字)
34. `L2630`: `#### 🛡️ 基金底层前十大重仓股穿透排雷大宽表 (商誉/存贷双高/质押/解禁)` (27汉字)
35. `L2667`: `#### 📡 聪明钱跟踪与机构抱团拥挤度监控 (北向资金/股东户数/龙虎榜)` (26汉字)
36. `L2697`: `#### 💡 A/C 份额全周期费率盈亏平衡计算器` (14汉字)
37. `L2722`: `#### 📡 场内 ETF 溢价率监控 (Wind 湖仓离线快照模式)` (15汉字)
38. `L582, L604, L621`: `🧭 市场定调与攻防线` (8汉字), `🌡️ 估值与资金面温度` (8汉字), `💰 我的总资产与今日预估` (10汉字)

---

## 2. Logic Chain (推理链条与架构推演)

### 2.1 侧边栏「🧭 全局领航台」的设计推理
1. **解耦原则**: 侧边栏绝对不承载局限于某个 Tab 内的业务操作按钮（如“加载演示组合”、“确认推演”、“生成建仓单”等应留在 Tab 1 与 Tab 2 内部）。
2. **领航定位**: 侧边栏作为全局常驻信息窗，应当跨 Tab 汇聚四大全局核心状态：
   - **模块 ① 实时市场状态与数据底座健康度**:
     - 展示当前市场定调（如“🟢 震荡收息期”或“🔥 科技主升浪”）；
     - 四维宏观核心状态（ERP 估值分位、DR007 利率、MA20 偏离度、期权 iVIX）；
     - 数据湖仓状态：28,177 只全市场基金底池正常、2018-2026 长周期回测矩阵就绪、实时行情缓存新鲜。
   - **模块 ②【🌱 新资建仓】当前推演方案快照**:
     - 动态读取 `st.session_state.get("tab1_sim_cache")`；
     - 若未推演，展示当前设定目标（本金 ¥50,000 / C3 平衡型 / 6只优选标的）；
     - 若已推演，展示：优选模型（如“鲁棒双核HRP”）、1年期达标胜率、防守 vs 进攻配比、最大浮亏与预计回本周期。
   - **模块 ③【💼 实盘持仓】账本核心快照**:
     - 动态读取 `pm.holdings` 与 `pm.available_cash`；
     - 若无持仓，提示“当前账本现金 ¥{available_cash}，请至 Tab 2 载入或录入”；
     - 若有持仓，展示：总资产净值、持仓只数、持仓累计浮盈（含百分比）、今日盘中预估浮盈、以及 FIFO 批次免惩罚费状态（如“全部满期免赎”或“有 X 笔 7 天锁定”）。
   - **模块 ④ 全局行情一键刷新入口**:
     - 放置按钮 `st.button("🔄 全局行情刷新", key="sidebar_btn_global_refresh", use_container_width=True, type="primary")`；
     - 执行 `clear_realtime_cache()`、`fetch_batch_realtime_indices(use_cache=False)`、`pm.sync_holdings_live_nav()` 与快照重载，并显示刷新时点。
3. **CSS 调整方案**:
   - 移除 `display: none !important;` 对 `[data-testid="stSidebar"]` 和 `[data-testid="collapsedControl"]` 的约束；
   - 保持隐藏原生部署按钮、汉堡菜单等开发外挂：
     `[data-testid="stToolbar"], .stDeployButton, [data-testid="stStatusWidget"], #MainMenu, footer { display: none !important; }`；
   - 将 `initial_sidebar_state` 设为 `"expanded"`（或自动）。

### 2.2 顶部 6 大核心指数行情带的单行全宽重构推理
1. **消除挤压**: 刷新按钮已经集成在侧边栏模块 ④，顶部行情带不再需要拆分为 `[8.2, 1.8]` 两列，直接享受 100% 容器全宽。
2. **网格布局**: 改用 CSS Grid `display: grid; grid-template-columns: repeat(6, 1fr); gap: 8px; width: 100%;`。
3. **标签层级与字号优化**:
   - 6 只指数（沪深300、科创50、中证红利、中证500、中证1000、黄金ETF）各自独立占用一列；
   - 名称使用 12px 粗体；点位使用 12px 纯黑高对比；涨跌幅使用胶囊色块标签（红涨：`background: #fee2e2; color: #dc2626;`；绿跌：`background: #dcfce7; color: #16a34a;`）；
   - 在 1200px~1920px 屏幕以及侧边栏展开后，每格宽度达到 150px~220px，完全单行呈现，彻底告别横向滚动与截断。

### 2.3 四大模型卡片化与六维打分 Popover 的交互设计推理
1. **去学术化与卡片网格**:
   - 废弃 `st.dataframe`，采用 2 行 2 列的卡片网格；
   - 卡片划分为三大直观维度：
     - **【它解决什么问题】**: 简述痛点（如“摆脱后视镜追高，解决赛道单点押注爆雷”）；
     - **【怎么分配资金】**: 简述机制（如“层次风险平价树状聚类 + 95% CVaR 尾部约束”）；
     - **【适合什么行情】**: 简述环境（如“震荡磨底、赛道轮动、全天候底仓”）；
   - 文本自适应折行，搭配徽章与边框。
2. **六维打分细则 Popover**:
   - 使用 `st.popover("ⓘ 评分细则")` 挂载在六维打分公式右侧；
   - 弹窗内详细披露 6 维打分（超额收益35%、低费率25%、底层排雷15%、聪明钱10%、反拥挤10%、宏观契合5%）的满分依据、基准分与扣分细则。

### 2.4 「方案核心逻辑」100% 动态数据同源推理
1. **从 4 列改为 3 栏宽卡片**:
   - 💰 怎么赚钱（绿色系边框）
   - 🏆 为什么能赢（蓝色系边框）
   - 🚨 风险与铁律（橙红色系边框）
2. **100% 动态数据读取与计算**:
   - 从 `_cache_entry["optimal_weights"]` 与 `UNIVERSE_18_CHAMPION_POOL` 汇聚真实资产分类：
     - 防守收息类（纯债、固收+、红利价值、黄金）权重总和与金额；
     - 弹性进攻类（宽基、成长、科技、QDII）权重总和与金额；
   - 点名第一权重标的：`max(opt_weights.items(), key=lambda x: x[1])` 的基金名称、权重与投资金额；
   - 代入当前选择模型：读取 `QUANT_MODELS_CATALOG[sel_model_type]["name"]` 及其核心优势；
   - 代入真实本金损失计算：`worst_loss = plan_capital * (worst_dd_pct / 100.0)`，代入最长水下天数 `max_underwater_days`；
   - 每一句话均由真实变量拼接，坚决杜绝任何固定占位符或静态套话。

### 2.5 全站标题精简规范（≤ 7 个汉字）推理
精简原则：保留主谓关键概念，剔除口语化短语（如“点击展开”、“白盒推演详情”、“全周期跨牛熊”等），统一压缩至 7 字以内。

---

## 3. Caveats (风险警示与潜在影响)

### 3.1 历史单测对旧文案与旧侧边栏行为的硬编码依赖
- **直接发现**:
  - `AGY2_FundAdvisory/tests/test_ui_final_polish.py` 第 27-33 行中存在旧单测：
    ```python
    def test_sidebar_completely_removed_and_css_hidden():
        assert "with st.sidebar:" not in gui_text
        assert '[data-testid="stSidebar"]' in gui_text
        assert '[data-testid="collapsedControl"]' in gui_text
    ```
    该测试为上一轮重构遗留，强制断言了“必须彻底移除 with st.sidebar 且 CSS 强隐藏”。当本次恢复侧边栏并引入 `with st.sidebar:` 时，该单测必然失败。
  - `AGY2_FundAdvisory/tests/test_adversarial_m3_challenger2.py` 第 198 行：
    ```python
    assert "🎯 《三句话看懂本方案：怎么赚钱、为什么能赢、风险与铁律》" in gui_content
    ```
  - `AGY2_FundAdvisory/tests/test_phase2_apptest_gui.py` 第 213 行：
    ```python
    assert "三句话看懂本方案" in all_md
    ```
  - `AGY2_FundAdvisory/tests/test_adversarial_m3_challenger2_interactive.py` 第 175 与 193 行：
    ```python
    assert "### 步骤三：生成实盘建仓" in all_md_before
    assert "### 步骤二：现场推演评估" in all_md_after
    ```
  - `AGY2_FundAdvisory/tests/test_interactive_continuity.py` 第 117 行：
    ```python
    btn_demo = at.sidebar.button[0] # 加载演示组合
    ```
    该测试此前已失败（因旧代码将演示按钮移入 Tab 2），而当前 R2 明确规范：侧边栏不放置任何局部操作按钮。
- **解决对策**:
  - `test_ui_final_polish.py`、`test_adversarial_m3_challenger2.py`、`test_phase2_apptest_gui.py` 及 `test_adversarial_m3_challenger2_interactive.py` 不属于只读受限文件（只读文件为 `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）。
  - 在落地实施 R2 代码修改时，必须同步将这些测试中的文本断言更新为符合 R2 规范的新标题与新组件结构（例如断言 `🎯 方案核心逻辑`，断言侧边栏恢复显示等）。

---

## 4. Conclusion (结论与具体实施方案)

### 4.1 核心成果汇总与方案设计表

| 重构模块 | 现状痛点 | 重构后实施设计 (落地规格) |
|---|---|---|
| **侧边栏** | CSS `display:none` 物理抹杀，交互割裂 | 恢复 `stSidebar`，重塑为「🧭 全局领航台」，内置 4 大全局模块（市场底座、建仓快照、持仓快照、全局刷新），0 局部操作按钮 |
| **核心指数带** | 被刷新按钮挤压 18% 宽度，易折行截断 | 独占 100% 容器宽度，6 列 CSS Grid 等分，胶囊标签红涨绿跌，单行完整无截断 |
| **四大模型说明** | `st.dataframe` 表格单行截断 | 2×2 自适应折行网格卡片，直观展现【解决什么问题】、【怎么分配资金】、【适合什么行情】 |
| **六维打分明细** | 静态单行 info，缺乏评分标准 | 标题右侧挂载 `st.popover("ⓘ 评分细则")`，详尽披露 6 维度 0-100 分及扣分细则 |
| **方案核心逻辑** | 4 列窄卡片，充斥静态套话 | 改为 3 栏宽卡片（💰 怎么赚钱 / 🏆 为什么能赢 / 🚨 风险与铁律），100% 动态读取当前推演组合资产配比、点名最高权重基金、计算真实回撤金额 |
| **全站标题规范** | 38 处标题超 7 汉字 | 全量重写为 $\le 7$ 汉字干练标题，剔除空洞套话 |

### 4.2 全站超长标题精简对照表 (全部严格 $\le 7$ 汉字)

| 原行号/位置 | 原标题 (超长) | 推荐替换标题 (严格 $\le 7$ 汉字) | 汉字数 |
|---|---|---|---|
| L582 卡片标题 | <span>🧭 市场定调与攻防线</span> | <span>🧭 市场攻防定调</span> | 6 |
| L604 卡片标题 | <span>🌡️ 估值与资金面温度</span> | <span>🌡️ 估值资金温度</span> | 6 |
| L621 卡片标题 | <span>💰 我的总资产与今日预估</span> | <span>💰 资产今日预估</span> | 6 |
| L680 折叠框 | 📌 您有已锁定的【... 盯盘待办预案】 | 📌 锁定盯盘预案 | 6 |
| L791 步骤一 | ### 步骤一：设定目标风险 | ### 步骤一：目标设定 | 6 |
| L964 折叠框 | 🔍 【点击展开】：四大机构级量化模型特性与适用场景全景对比 | 🔍 四大模型对比 | 6 |
| L1014 步骤二 | ### 步骤二：现场推演评估 | ### 步骤二：现场推演 | 6 |
| L1051 胜率看板 | #### 🎯 2018-2026 全周期跨牛熊滚动持有胜率 (同温层状态机条件加权) | #### 🎯 跨牛熊胜率 | 5 |
| L1064 折叠框 | ℹ️ 【量化数学定义】：为什么需要同时看达标胜率、保本率、跑赢货基率与 95% CVaR？ | ℹ️ 胜率指标定义 | 6 |
| L1145 折叠框 | 🔍 【点击展开白盒推演详情】：全市场选基漏斗与赛道冠军打分表 | 🔍 选基漏斗打分 | 6 |
| L1160 公式标题 | ##### 📐 《六维量化打分加权公式（0~100分归一化）》 | ##### 📐 六维打分公式 | 6 |
| L1163 评分明细 | ##### 📊 《当前档位入选标的：{_champ_s} 只冠军基金六维量化评分明细表》 | ##### 📊 冠军评分明细 | 6 |
| L1244 折叠框 | 🧭 【点击展开白盒推演详情】：宏观流动性、风格动量与衍生品四维因果决策信号 | 🧭 宏观决策信号 | 6 |
| L1249 卡片标题 | ① 市场温度与估值水位 | ① 估值水位温度 | 6 |
| L1294 卡片标题 | ④ 期权波动率防波堤 (iVIX) | ④ 波动率防波堤 | 6 |
| L1304 归因标题 | #### 🎯 《三句话看懂本方案：怎么赚钱、为什么能赢、风险与铁律》 | #### 🎯 方案核心逻辑 | 6 |
| L1369 步骤三 | ### 步骤三：生成实盘建仓 | ### 步骤三：生成建仓 | 6 |
| L1492 折叠框 | 📱 【点击展开：手机银行 / 天天基金下单一键复制小抄】 | 📱 下单复制小抄 | 6 |
| L1555 步骤一 | ### 步骤一：当前持仓账本 | ### 步骤一：持仓账本 | 6 |
| L1612 折叠框 | 📋 实盘接管档案（接管基准、峰值资产、最大回撤与 Alpha） | 📋 实盘接管档案 | 6 |
| L1772 折叠框 | 📦 【点击展开：全组合 FIFO 批次透视与免赎回费倒计时】 | 📦 批次与免赎期 | 6 |
| L1816 步骤二 | ### 步骤二：调仓时机裁决 | ### 步骤二：时机裁决 | 6 |
| L1898 步骤三 | ### 步骤三：调仓方案执行 | ### 步骤三：方案执行 | 6 |
| L1969 后果账单 | #### 🧾 《本次调仓四大真实后果量化账单》 | #### 🧾 调仓后果账单 | 6 |
| L1998 卡片标题 | 🛡️ ③ 组合攻防与回撤变化 | 🛡️ ③ 攻防回撤变化 | 6 |
| L2012 卡片标题 | 🔄 ④ 持有期清零重算后果 | 🔄 ④ 持有清零后果 | 6 |
| L2317 曲线标题 | #### 🚀 2018-2026 全周期真实净值推演曲线 (对标 {len(selected_bms)} 只自选基准指数) | #### 🚀 净值推演曲线 | 6 |
| L2405 水下回撤 | ##### 🌊 动态水下回撤对比图 (Underwater Drawdown %) | ##### 🌊 动态水下回撤 | 6 |
| L2441 仓位变迁 | ##### 📊 历史大类资产仓位变迁面积图 (Stacked Area %) | ##### 📊 仓位变迁图 | 5 |
| L2470 风格切片 | #### 📜 6 大历史市场风格切片全胜战报 (Gate B 考核通过) | #### 📜 历史风格切片 | 6 |
| L2476 同温层匹配 | #### 🔍 历史相似行情与宏观同温层匹配器 (History Analog Matcher) | #### 🔍 相似行情匹配 | 6 |
| L2483 表现回顾 | ##### 📊 当时发生了什么 & 策略表现如何？ | ##### 📊 当时表现回顾 | 6 |
| L2525 资产占比 | ##### 📊 资产大类实际占比 vs 目标占比 | ##### 📊 资产大类占比 | 6 |
| L2555 行业穿透 | ##### 🏭 加权行业穿透暴露 | ##### 🏭 行业穿透暴露 | 6 |
| L2566 缺口分析 | ##### ⚖️ 大类资产配置缺口量化分析表 (实际 vs 模型目标) | ##### ⚖️ 资产缺口分析 | 6 |
| L2604 交叉热力 | #### ⚠️ 前十大重仓股重叠交叉检测与热力图 | #### ⚠️ 重仓交叉热力 | 6 |
| L2630 排雷宽表 | #### 🛡️ 基金底层前十大重仓股穿透排雷大宽表 (商誉/存贷双高/质押/解禁) | #### 🛡️ 重仓穿透排雷 | 6 |
| L2667 聪明钱监控 | #### 📡 聪明钱跟踪与机构抱团拥挤度监控 (北向资金/股东户数/龙虎榜) | #### 📡 聪明钱与拥挤 | 6 |
| L2697 费率计算 | #### 💡 A/C 份额全周期费率盈亏平衡计算器 | #### 💡 份额费率计算 | 6 |
| L2722 溢价监控 | #### 📡 场内 ETF 溢价率监控 (Wind 湖仓离线快照模式) | #### 📡 场内溢价监控 | 6 |

### 4.3 实施代码原型设计

#### (1) 侧边栏与 CSS 修改原型 (`app_gui.py`)
```python
# 1. 恢复侧边栏
st.set_page_config(
    page_title="AGY2 智能投顾与实盘组合接管工作台",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. 精简 CSS，移除 [data-testid="stSidebar"] 与 [data-testid="collapsedControl"] 的 display:none
st.markdown("""
<style>
    /* 仅保留隐藏顶部无关的部署按钮与工具条 */
    [data-testid="stToolbar"], .stDeployButton, [data-testid="stStatusWidget"], #MainMenu, footer, [data-testid="stHeaderActionElements"] {
        visibility: hidden !important;
        display: none !important;
    }
    /* 保证展开控制按钮正常渲染 */
    [data-testid="collapsedControl"] {
        display: flex !important;
        visibility: visible !important;
    }
    section[data-testid="stSidebar"] {
        background-color: #f8fafc;
        border-right: 1px solid #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)

# 3. 渲染「🧭 全局领航台」
with st.sidebar:
    st.markdown("### 🧭 全局领航台")
    st.caption("全局跨 Tab 运行中枢")

    # 模块 ① 实时市场状态与数据底座健康度
    st.markdown("##### 🌐 市场与数据状态")
    st.info(f"市场定调：{vernacular_state}\n\n四维宏观：ERP {erp_pct:.1f}% ｜ MA20偏离 {bias_disp:+.1f}%\n\n数据湖仓：28,177 只公募底池就绪")

    # 模块 ②【🌱 新资建仓】当前推演方案快照
    st.markdown("##### 🌱 新资建仓快照")
    sim_c = st.session_state.get("tab1_sim_cache")
    if sim_c:
        w_dict = sim_c.get("optimal_weights", {})
        m_type = sim_c.get("model_type", "hrp_cvar")
        m_name = QUANT_MODELS_CATALOG.get(m_type, {}).get("name", "鲁棒双核HRP")
        st.success(f"已生成方案：{len(w_dict)} 只精选标的\n\n定权模型：{m_name}\n\n投资本金：¥{plan_capital:,.0f}")
    else:
        st.caption("尚未生成现场推演，可在 Tab 1 开启配置。")

    # 模块 ③【💼 实盘持仓】账本核心快照
    st.markdown("##### 💼 实盘持仓快照")
    if len(pm.holdings) > 0:
        st.metric("总资产", f"¥{total_cur_equity:,.2f}", delta=f"持仓浮盈 ¥{_t2_pnl:+,.2f}")
        st.caption(f"持仓标的: {len(pm.holdings)} 只 ｜ 可用现金: ¥{pm.available_cash:,.0f}")
    else:
        st.caption(f"当前账本无持仓（可用现金: ¥{pm.available_cash:,.0f}）")

    # 模块 ④ 全局行情一键刷新入口
    st.markdown("##### 🔄 全局行情刷新")
    if st.button("🔄 一键刷新全局行情", key="sidebar_btn_global_refresh", use_container_width=True, type="primary"):
        clear_realtime_cache()
        fetch_batch_realtime_indices(use_cache=False)
        pm.sync_holdings_live_nav(use_intraday_gsz=True)
        StrategyBridge._cached_snapshot = None
        StrategyBridge._cached_matrix = None
        StrategyBridge.get_latest_market_snapshot(force_reload=True, auto_sync=False)
        st.rerun()
    st.caption(f"🕒 刷新时点: {datetime.now().strftime('%H:%M:%S')}")
```

#### (2) 6 大核心指数行情带单行全宽原型 (`app_gui.py`)
```html
<style>
.index-ticker-strip {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 8px;
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 8px 12px;
    margin-top: 8px;
    margin-bottom: 12px;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
    width: 100%;
    box-sizing: border-box;
}
.index-ticker-pill {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 4px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 4px 8px;
    box-sizing: border-box;
    min-width: 0;
}
.index-pill-name { font-weight: 600; color: #334155; font-size: 12px; white-space: nowrap; }
.index-pill-point { font-weight: 700; color: #0f172a; font-size: 12px; white-space: nowrap; }
.index-pill-chg-up { font-weight: 700; color: #dc2626; background: #fee2e2; border-radius: 4px; padding: 1px 4px; font-size: 11px; white-space: nowrap; }
.index-pill-chg-down { font-weight: 700; color: #16a34a; background: #dcfce7; border-radius: 4px; padding: 1px 4px; font-size: 11px; white-space: nowrap; }
</style>
```

#### (3) 方案核心逻辑 3 栏深度归因大卡片 100% 动态数据计算原型
```python
# 动态提取真实推演数据
opt_w = _cache_entry.get("optimal_weights", {})
pool_map = {it["code"]: it for it in UNIVERSE_18_CHAMPION_POOL}
capital_val = float(plan_capital)

defensive_buckets = {"纯债固收", "固收增强", "红利价值", "黄金商品"}
defensive_weight = sum(fw for fc, fw in opt_w.items() if pool_map.get(fc, {}).get("bucket") in defensive_buckets)
tot_w = sum(opt_w.values()) or 1.0
defensive_pct = (defensive_weight / tot_w) * 100.0
elastic_pct = 100.0 - defensive_pct

defensive_amt = capital_val * (defensive_pct / 100.0)
elastic_amt = capital_val * (elastic_pct / 100.0)

top_code, top_w = max(opt_w.items(), key=lambda x: x[1]) if opt_w else ("", 0.0)
top_name = pool_map.get(top_code, {}).get("name", f"优选标的({top_code})")
top_amt = capital_val * top_w

m_meta = QUANT_MODELS_CATALOG.get(sel_model_type, {})
m_name = m_meta.get("name", "鲁棒双核HRP")
m_adv = m_meta.get("advantage", "")

worst_dd_pct = float(readable_kpi.get('worst_case_drawdown_pct', 0.0))
worst_loss_amt = capital_val * (worst_dd_pct / 100.0)
max_underwater = int(readable_kpi.get('max_underwater_days', 0))
cvar_95_val = float(readable_kpi.get('cvar_95_pct', 0.0))
```

---

## 5. Verification Method (验证方法与独立核验命令)

### 5.1 标题字数与静态红线核验
在工作区根目录下执行：
```powershell
py -3.11 .agents/teamwork/teamwork_explorer_prod_3/audit_titles_detailed.py
```
**合格判定条件**: 输出中超长标题（`> 7` 汉字）计数归零。

### 5.2 侧边栏与交互无异常验证
运行现有 AppTest 套件：
```powershell
py -3.11 -m pytest AGY2_FundAdvisory/tests/test_e2e_gui_render.py -v
py -3.11 -m pytest AGY2_FundAdvisory/tests/test_phase2_apptest_gui.py -v
```
**合格判定条件**:
- 首屏渲染 `len(at.exception) == 0`；
- 侧边栏包含 4 个核心模块且包含刷新按钮；
- 4 个 Tab 交互切换 0 异常。

### 5.3 失效条件 (Invalidation Conditions)
1. 若 `test_ui_final_polish.py` 的历史遗留断言 `assert "with st.sidebar:" not in gui_text` 未被更新，会导致自动化测试套件报错中断；
2. 若 `[data-testid="collapsedControl"]` 未在 CSS 中正确恢复可见性，可能导致用户在手动收起侧边栏后无法再次点击展开。
