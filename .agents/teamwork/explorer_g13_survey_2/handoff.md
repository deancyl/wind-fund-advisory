# G13 世代技术调研与方案设计报告（痛点 2、3 与痛点 5）

**报告编写代理**：`explorer_g13_survey_2` (teamwork_explorer)  
**调研文件路径**：`d:\Google\Workspace\Wind\.agents\teamwork\explorer_g13_survey_2\handoff.md`  
**调研目标**：针对 G13 世代重构任务中的痛点 2 & 3（彻底砍除所有伪交易按钮、重构全宽投顾提示栏、移出 5 大臃肿模块）以及痛点 5（全宽四宫格大胶囊主导航栏 CSS 改造、删除 Tab 内重复巨型标题、Tab 4 顶部紧凑合并）展开代码级精准定位与可直接落地的重构方案设计。

---

## 一、 Observation（直接观察与代码定位）

### 1. 痛点 2 & 3：伪交易按钮与双翼看板臃肿嵌套在 `AGY2_FundAdvisory/app_gui.py` 中的具体位置

#### 1.1 首屏右上角红色按钮与非全宽列切分
- **文件路径**：`d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py`
- **行号区间**：第 2786 至 2804 行
- **直接观测代码**：
  ```python
  col_wing_exp, col_wing_btn = st.columns([8.2, 1.8])
  with col_wing_btn:
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

  clean_title = act_title.replace("【", "").replace("】", " · ")
  with col_wing_exp:
      wing_expander = st.expander(f"{act_status_icon} 今日投顾结论：{clean_title} ｜ 点击展开机会雷达与主动风控巡检", expanded=False)
  ```
- **问题观察**：
  - `st.columns([8.2, 1.8])` 将视口右侧 18% 的宽度强行切走分给 `col_wing_btn`；当折叠面板展开时，右侧按钮下方形成高达数百像素的完全空白垂直死区（图 3 缺陷）。
  - `btn_master_action_switch`（“👉 查看锁仓保护 / 查看今日调仓单 / 检视持仓账本”）以刺眼的红色 Primary 实体块展示，实际上只执行了跨 Tab 的内存字典跳转，具有强烈的伪柜台交易误导性。

#### 1.2 右翼主动风险哨内的伪交易与跳转按钮
- **文件路径**：`d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py`
- **行号区间**：第 3126 至 3261 行
- **直接观测代码**：
  - **第 3126 至 3147 行**：一键批量锁定下界大红按钮：
    ```python
    if st.button(f"🔒 一键批量锁定这 {len(lock_alerts)} 只标的调仓下界", key="btn_batch_lock_all_7d", use_container_width=True, type="primary"):
        if "tab2_locked_funds" not in st.session_state:
            st.session_state.tab2_locked_funds = []
        for fc in lock_codes:
            ...
    ```
  - **第 3200 至 3261 行**：卡片下方的双按钮（`col_s_a` 与 `col_s_b`）：
    ```python
    col_s_a, col_s_b = st.columns(2)
    with col_s_a:
        if st.button(btn_lbl, key=f"btn_sentry_act_{i}_{fcode}_{act_type}", use_container_width=True, type="secondary"):
            # 包含：锁定下界、暂缓倒计时、择机置换A类、阶梯止盈、反弹减亏、平衡赛道敞口、一键折溢价套利等
            ...
    with col_s_b:
        if st.button("🔍 穿透到底层", key=f"btn_sentry_evid_{i}_{fcode}_{act_type}", use_container_width=True):
            ...
    ```
- **问题观察**：右翼预警哨充斥着大量虚假处置按钮，诱导用户以为系统能直接在支付宝/天天基金柜台操作；实际上未满 7 天锁定等防御规则本就是调仓算法的默认底线，无需人工点击锁定。

#### 1.3 左翼机会雷达 Top 3 赛道卡下方的“+ 入备选池”按钮
- **文件路径**：`d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py`
- **行号区间**：第 2963 至 2991 行
- **直接观测代码**：
  ```python
  if st.button("➕ 入备选池", key=f"btn_add_radar_pool_{sec['sector_id']}", use_container_width=True, type="secondary"):
      if "custom_candidate_pool" not in st.session_state:
          st.session_state.custom_candidate_pool = []
      ...
      st.toast(f"✅ 已将【{sec_fund.get('name')}】一键纳入备选池，正在为您导向新资建仓！")
      st.rerun()
  ```
- **问题观察**：用户正在浏览市场大势，点击后强行打断用户并重刷全页跳转至 Tab 1；卡片内应直接清晰展示优选基金名称与 6 位代码，保持只读卡片纯粹性。

#### 1.4 双翼看板内嵌套的 5 大臃肿模块
- **文件路径**：`d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py`
- **具体分布**：
  1. **模块 ① 历史三大牛熊拐点实盘对照尺**（第 2886-2891 行与第 2917 行）：在左翼晨报卡片内部嵌入了 `{ruler_bar_html}`。因为左翼仅占 6.2/10 宽度，4 个节点强行挤在狭小宽度内，导致 `1.93x` 与 `偏离+4.3%` 文字粘连穿模重叠。
     - *注：该组件在 Tab 1 定投模式中亦有使用（第 4022-4027 行）*。
  2. **模块 ② 查看全市场 14 大赛道量化温度计总表**（第 2993 至 3011 行）：
     `with st.expander("📊 查看全市场 14 大赛道量化温度计总表 (向下展开)", expanded=False):`
  3. **模块 ③ 场内ETF与场外联接 14:45 尾盘折溢价套利感知**（第 3013 至 3034 行）：
     `with st.expander("⚡ 场内ETF与场外联接 14:45 尾盘折溢价套利感知", expanded=False):`
  4. **模块 ④ 50ETF与300ETF认沽期权隐含波动率防暴跌哨**（第 3036 至 3058 行）：
     `with st.expander("🛡️ 50ETF与300ETF认沽期权隐含波动率防暴跌哨", expanded=False):`
  5. **模块 ⑤ 跨境QDII溢价与外汇期货锁汇成本套利精算**（第 3060 至 3082 行）：
     `with st.expander("🌐 跨境QDII溢价与外汇期货锁汇成本套利精算", expanded=False):`

---

### 2. 痛点 5：主导航栏 CSS、重复大标题与 Tab 4 顶栏在 `AGY2_FundAdvisory/app_gui.py` 中的具体位置

#### 2.1 主导航栏 CSS 样式注入块
- **文件路径**：`d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py`
- **行号区间**：第 1138 至 1147 行
- **直接观测代码**：
  ```css
  [data-testid="stTabs"] button {
      color: var(--text-secondary) !important;
      border-bottom-color: transparent !important;
      transition: all 0.2s ease !important;
  }
  [data-testid="stTabs"] button[aria-selected="true"] {
      color: var(--accent-primary) !important;
      border-bottom-color: var(--accent-primary) !important;
      font-weight: 700 !important;
  }
  ```
- **问题观察**：对所有 `stTabs` 采用无差别的弱化下划线小字样式，一级全局导航在视觉上萎缩至 13~14px，视觉权重严重倒挂，且与局部子 Tab 完全同质化。

#### 2.2 四大 Tab 内重复打印的二级标题与废话 Caption
- **Tab 1（第 3343 行）**：
  `st.subheader("🌱 新资建仓")`
- **Tab 2（第 4741 行）**：
  `st.subheader("💼 持仓调仓")`
- **Tab 3（第 7649 至 7650 行）**：
  `st.subheader("📈 组合回测")`  
  `st.caption("穿透回测新建仓组合、当前实盘与调仓前后全周期表现，支持 9 大基准指数对比与跨牛熊样本外盲测。")`
- **Tab 4（第 7661 至 7662 行）**：
  `st.subheader("🔍 穿透工具")`  
  `st.caption("多维下潜至底层重仓股、行业分布与信用风险，支持当前实盘、新建仓与调仓后对象全景穿透体检。")`

#### 2.3 Tab 4 顶层组合选择与成分档案割裂堆叠
- **文件路径**：`d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py`
- **行号区间**：第 6969-7007 行（`col_tb_sel` 下拉框）与第 7080-7088 行（`📋 当前体检组合成分档案` 巨型卡片）
- **问题观察**：选择组合对象与下方展示的成分档案被垂直拆开为两层，白白浪费了纵向近 150 像素高度，把下方的核心图表推挤至屏幕外。

---

### 3. 测试文件中的关联旧断言扫描
- `tests/test_challenger_g11_m1_actions.py`：第 550、610 行显式断言了 `btn_master_action_switch`；
- `tests/test_g7_architecture_and_decoupling.py`：第 111、112 行显式断言了 `btn_sentry_act_` 与 `btn_sentry_evid_`；
- `AGY2_FundAdvisory/tests/test_m3_full_integration_apptest.py`：第 32 行断言了 `btn_add_radar_pool_`。
*(注：上述三者均属于常规特性测试文件，非四只裁判只读文件，按指令要求应予以同步更新适配。)*

---

## 二、 Logic Chain（推演逻辑链与外科手术级方案）

### 1. 痛点 2 & 3 重构推演

```
[Observation 1.1] col_wing_btn 产生 18% 刺眼空白死区，且 btn_master_action_switch 为伪交易跳转
  └── 彻底删除 col_wing_btn 与 btn_master_action_switch 按钮逻辑
  └── 移除 st.columns([8.2, 1.8]) 分列，wing_expander 设为 100% 全宽容器
  └── 投顾文案从系统黑话重构为温暖人话参谋（根据持仓状况动态自适应）

[Observation 1.2] 右翼主动风险哨堆叠 12 维伪处置与跳转按钮
  └── 删除 btn_batch_lock_all_7d（算法默认守死 7 天下界，无需人工锁定）
  └── 移除卡片下方的双按钮列 col_s_a 与 col_s_b（择机置换、平衡敞口、穿透底层等）
  └── 右翼收敛为干净纯粹的 1~3 条风险卡片，仅包含：图标+标题、原因描述、投顾应对建议（纯文本）

[Observation 1.3] 左翼 Top 3 赛道卡下方堆叠 "+ 入备选池" 按钮
  └── 移除 3 个 st.button("➕ 入备选池", key=f"btn_add_radar_pool_{sec['sector_id']}")
  └── 在卡片内部以加粗字体直接展示优选基金名称与 6 位基金代码，去除页面跳转打扰

[Observation 1.4] 首屏双翼看板嵌套 5 大臃肿模块，导致页面滚动高度超标与拐点尺穿模
  └── ① 拐点尺：从晨报 pulse_card_html 中彻底移除 {ruler_bar_html}；
                仅在 Tab 1 定投模式保留，并通过 flex-wrap: nowrap + overflow-x: auto + 独立卡片布局彻底解决文字重叠；
  └── ②-⑤ 模块：从 render_dual_wing_advisory_dashboard 彻底移出，迁移至 Tab 4 二级子 Tab；
  └── 双翼看板展开后仅剩：左翼 Top 3 赛道卡 + 右翼极简风险提示列表，高度锁定 <= 220px。
```

#### 1.1 投顾参谋折叠栏全宽动态文案定义
```python
# 动态人话文案状态机
if lock_alerts_switch:
    act_status_icon = "🔴"
    expander_title = (
        f"今日投顾参谋：持仓含 {len(lock_alerts_switch)} 只未满 7 天标的，"
        f"赎回需扣 1.5% 惩罚费，调仓算法已自动为您避开卖出 ｜ 点击展开市场机会与持仓体检"
    )
elif all_alerts_switch:
    act_status_icon = "🟡"
    first_title = all_alerts_switch[0].get('title', '结构偏离')
    expander_title = (
        f"今日投顾参谋：检测到 {len(all_alerts_switch)} 项持仓优化提示（首要：{first_title}），"
        f"调仓算法已准备好应对方案 ｜ 点击展开市场机会与持仓体检"
    )
elif len(pm_instance.holdings) == 0:
    act_status_icon = "🚀"
    expander_title = "今日投顾参谋：宏观 ERP 处于黄金击球区，建议一键启动新资建仓 ｜ 点击展开市场机会与精选赛道"
else:
    act_status_icon = "🟢"
    expander_title = "今日投顾参谋：持仓资产结构健康，安全垫充沛，今日安心吃息无需调仓 ｜ 点击展开市场机会与持仓体检"

# 100% 全宽折叠面板
wing_expander = st.expander(expander_title, expanded=False)
```

#### 1.2 右翼极简纯文本决策卡片结构
```python
with col_sentry:
    safe_markdown_html("<div style='font-size: 13px; font-weight: 700; color: var(--text-primary); margin-bottom: 6px;'>🚨 主动风险提示 · 组合健康度</div>")
    
    if report.get("all_passed"):
        safe_markdown_html("""
        <div class="decision-card" style="border-left: 3px solid var(--color-down); padding: 8px 12px; margin-bottom: 4px;">
            <div style="font-weight: 700; color: var(--color-down); font-size: 12px; margin-bottom: 2px;">🟢 主动风控巡检全通</div>
            <div style="font-size: 11px; color: var(--text-secondary);">持仓批次无惩罚锁仓 ｜ 赛道无超买拥挤 ｜ 零迷你基清盘风险</div>
        </div>
        """)
    else:
        # 未满 7 天锁定期警报（聚合或单标的）
        if len(lock_alerts) >= 1:
            lock_names = [f"{a.get('fund_code')} ({a.get('fund_name', a.get('fund_code'))[:5]})" for a in lock_alerts]
            safe_markdown_html(f"""
            <div class="decision-card" style="border-left: 3px solid var(--color-up); padding: 8px 10px; margin-bottom: 6px;">
                <div style="font-size: 12px; font-weight: 700; color: var(--color-up); margin-bottom: 2px;">
                    🔴【未满7天锁定期】包含标的: {', '.join(lock_names)}
                </div>
                <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 2px;">
                    未满 7 天赎回将触发 1.50% 巨额惩罚扣款。调仓算法已在底层自动为您锁定下界。
                </div>
                <div style="font-size: 11px; color: var(--text-primary); font-weight: 600;">
                    💡 应对建议: 保持持有吃息，待持有满 7 天后再行操作。
                </div>
            </div>
            """)
        
        # 其余最多 1~2 项核心警报（无任何按钮）
        for alert in other_alerts[: (2 if not lock_alerts else 1)]:
            border_c = "var(--color-up)" if alert["level"] == "red" else "var(--accent-primary)"
            badge_icon = "🔴" if alert["level"] == "red" else "🟡"
            safe_markdown_html(f"""
            <div class="decision-card" style="border-left: 3px solid {border_c}; padding: 8px 10px; margin-bottom: 4px;">
                <div style="font-size: 12px; font-weight: 700; color: var(--text-primary); margin-bottom: 2px;">
                    {badge_icon} {alert['title']}
                </div>
                <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 2px;">
                    {alert['desc']}
                </div>
                <div style="font-size: 11px; color: {border_c}; font-weight: 600;">
                    💡 建议: {alert['action']}
                </div>
            </div>
            """)
```

#### 1.3 牛熊拐点实盘对照尺抗挤压防穿模修复
修改 `render_historical_inflection_ruler_html` 函数（`app_gui.py` 第 1613 行）：
- 将外层滚动容器添加强制样式：
  `style="display: flex !important; flex-wrap: nowrap !important; gap: 8px !important; overflow-x: auto !important; width: 100% !important; padding-bottom: 4px !important; box-sizing: border-box !important;"`
- 将每个节点卡片改为：
  `style="border: 1.5px solid {border}; background: {bg}; border-radius: 6px; padding: 6px 10px; min-width: 155px !important; flex: 1 1 0 !important; box-sizing: border-box !important;"`
- 内部布局解耦：标题与日期居顶（`white-space: nowrap;`）；下方乘数 `1.93x` 占左半部（`font-size: 16px; font-weight: 800;`），右半部垂直堆叠 `ERP分位` 与 `乖离率`，彻底杜绝单行并列挤压碰撞。

---

### 2. 痛点 5 重构推演

```
[Observation 2.1] 顶层主 Tab 视觉层级倒挂，仅为 13px 透明小字
  └── 注入高特异性 CSS 选择器覆盖原生 [data-testid="stTabs"]
  └── 约束 [data-testid="stMainBlockContainer"] > div > div > [data-testid="stTabs"] > [data-baseweb="tab-list"]
  └── 建立四等分网格 (grid-template-columns: repeat(4, 1fr))，高度 46px，字号 16px，加粗 700
  └── 选中态以深海蓝实心突起、纯白文字与扩散阴影渲染
  └── 使用 :not([data-testid="stTabContent"] ...) 严格隔离局部子 Tab

[Observation 2.2] 四个主 Tab 内部重复打印巨大 subheader 与废话 caption
  └── 删除 Tab 1 的 st.subheader("🌱 新资建仓")
  └── 删除 Tab 2 的 st.subheader("💼 持仓调仓")
  └── 删除 Tab 3 的 st.subheader("📈 组合回测") 及对应 st.caption
  └── 删除 Tab 4 的 st.subheader("🔍 穿透工具") 及对应 st.caption

[Observation 2.3] Tab 4 顶栏选择器与成分档案垂直冗余
  └── 采用并排分列：左侧 3.8 列放紧凑无标签下拉框，右侧 6.2 列放单行紧凑成分档案摘要卡
  └── 将图表（大类资产、行业穿透）无缝提权至首屏第一视口
```

#### 2.1 主导航栏精确定位 CSS 方案
在 `app_gui.py` 样式注入块（约第 1138 行）加入如下规则：

```css
/* =========================================================================
   G13: 顶层四大功能全宽四宫格大胶囊主导航栏 (Full-Width Segmented Pill Bar)
   ========================================================================= */

/* 1. 顶层主 Tab 容器: 100%全宽四等分网格，背景浅灰槽 */
[data-testid="stMainBlockContainer"] > div > div > [data-testid="stTabs"] > [data-baseweb="tab-list"],
div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) > [data-baseweb="tab-list"],
div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) > div[role="tablist"] {
    display: grid !important;
    grid-template-columns: repeat(4, 1fr) !important;
    gap: 10px !important;
    background: var(--bg-elevated) !important;
    padding: 6px !important;
    border-radius: 10px !important;
    border: 1px solid var(--border-subtle) !important;
    margin-bottom: 14px !important;
    width: 100% !important;
    box-sizing: border-box !important;
}

/* 2. 顶层主 Tab 按钮 (默认态): 高度 46px, 字号 16px, 粗体 700, 居中卡片质感 */
[data-testid="stMainBlockContainer"] > div > div > [data-testid="stTabs"] > [data-baseweb="tab-list"] button,
div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) > [data-baseweb="tab-list"] button,
div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) > div[role="tablist"] button {
    height: 46px !important;
    font-size: 16px !important;
    font-weight: 700 !important;
    border-radius: 8px !important;
    justify-content: center !important;
    background: var(--bg-surface) !important;
    border: 1px solid var(--border-subtle) !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;
    color: var(--text-secondary) !important;
    border-bottom: 1px solid var(--border-subtle) !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    padding: 0 10px !important;
    display: flex !important;
    align-items: center !important;
}

/* 3. 顶层主 Tab 按钮 (Hover 态) */
[data-testid="stMainBlockContainer"] > div > div > [data-testid="stTabs"] > [data-baseweb="tab-list"] button:hover,
div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) > [data-baseweb="tab-list"] button:hover {
    background: var(--bg-hover) !important;
    color: var(--text-primary) !important;
    border-color: var(--border-hover) !important;
}

/* 4. 顶层主 Tab 按钮 (激活态): 深海蓝/品牌色实心高亮 + 投影 */
[data-testid="stMainBlockContainer"] > div > div > [data-testid="stTabs"] > [data-baseweb="tab-list"] button[aria-selected="true"],
div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) > [data-baseweb="tab-list"] button[aria-selected="true"],
div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) > div[role="tablist"] button[aria-selected="true"] {
    background: var(--accent-primary) !important;
    color: #ffffff !important;
    border-color: var(--accent-primary) !important;
    border: 1px solid var(--accent-primary) !important;
    box-shadow: 0 4px 12px rgba(29, 78, 216, 0.25) !important;
}

/* 5. 顶层选中态内部所有文本 (span, p) 强制纯白 */
[data-testid="stMainBlockContainer"] > div > div > [data-testid="stTabs"] > [data-baseweb="tab-list"] button[aria-selected="true"] *,
[data-testid="stMainBlockContainer"] > div > div > [data-testid="stTabs"] > [data-baseweb="tab-list"] button[aria-selected="true"] span,
[data-testid="stMainBlockContainer"] > div > div > [data-testid="stTabs"] > [data-baseweb="tab-list"] button[aria-selected="true"] p,
div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) > [data-baseweb="tab-list"] button[aria-selected="true"] *,
div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) > [data-baseweb="tab-list"] button[aria-selected="true"] span,
div[data-testid="stTabs"]:not([data-testid="stTabContent"] div[data-testid="stTabs"]) > [data-baseweb="tab-list"] button[aria-selected="true"] p {
    color: #ffffff !important;
    font-weight: 700 !important;
}

/* 6. 严格物理隔离 Tab 4 二级子 Tab (保持紧凑轻量下划线样式，绝不与一级大导航混淆) */
[data-testid="stTabContent"] [data-testid="stTabs"] > [data-baseweb="tab-list"],
[data-testid="stTabContent"] [data-testid="stTabs"] > div[role="tablist"] {
    display: flex !important;
    flex-wrap: nowrap !important;
    background: transparent !important;
    padding: 0 !important;
    border: none !important;
    border-bottom: 1px solid var(--border-subtle) !important;
    border-radius: 0 !important;
    gap: 8px !important;
    margin-bottom: 12px !important;
    width: 100% !important;
    overflow-x: auto !important;
}

[data-testid="stTabContent"] [data-testid="stTabs"] button {
    height: 36px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    border-radius: 0 !important;
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    box-shadow: none !important;
    color: var(--text-secondary) !important;
    padding: 0 12px !important;
}

[data-testid="stTabContent"] [data-testid="stTabs"] button[aria-selected="true"] {
    background: transparent !important;
    color: var(--accent-primary) !important;
    border-bottom: 2px solid var(--accent-primary) !important;
    border-color: transparent transparent var(--accent-primary) transparent !important;
    box-shadow: none !important;
    font-weight: 700 !important;
}

[data-testid="stTabContent"] [data-testid="stTabs"] button[aria-selected="true"] * {
    color: var(--accent-primary) !important;
}
```

---

### 3. Tab 4 六大二级子 Tab 架构设计与 4 大模块迁移映射

Tab 4 原有 3 个子 Tab（资产穿透、AC算费、ETF溢价）。
迁移后，Tab 4 规划为 **6 个清晰专业的二级子 Tab**：

| 子 Tab 序号 | 子 Tab 名称 | 来源与包含功能 | 对应原首屏臃肿模块 |
| :--- | :--- | :--- | :--- |
| **Sub-Tab 1** | `📊 资产穿透与排雷` | 大类配置缺口、加权行业敞口、EWMA 相关性、重仓股交叉热力图、底层穿透排雷宽表、四象限量价结构 | 原 Tab 4 原生功能 |
| **Sub-Tab 2** | `🌡️ 14大赛道温度计` | 全市场 14 大赛道真实估值分位、趋势信噪比、20日乖离率与拥挤度全息总表 | **模块 ②**（移出自首屏双翼） |
| **Sub-Tab 3** | `⚡ 尾盘折溢价套利` | ① 14:45 场内核心 ETF 与场外联接市价 vs IOPV 毫秒级折溢价套利感知<br>② 原有的核心场内 ETF 溢价监控 | **模块 ③**（移出自首屏双翼） |
| **Sub-Tab 4** | `🛡️ 期权防暴跌哨` | 50ETF 与 300ETF 近月平值认沽期权 IV 与 20日 HV 偏离度追踪与防暴跌哨 | **模块 ④**（移出自首屏双翼） |
| **Sub-Tab 5** | `🌐 跨境QDII与锁汇` | 跨境 QDII 溢价、离岸人民币 USD/CNH 远期掉期点锁汇成本精算与真实到手增厚 | **模块 ⑤**（移出自首屏双翼） |
| **Sub-Tab 6** | `💡 A/C端选型算费` | A 类与 C 类公募基金申购费率、销售服务费盈亏平衡天数测算器 | 原 Tab 4 原生功能 |

#### 代码结构重组方案：
在 `render_tab4_toolbox_content` 中：
```python
box_tab1, box_tab2, box_tab3, box_tab4, box_tab5, box_tab6 = st.tabs([
    "📊 资产穿透与排雷",
    "🌡️ 14赛道温度计",
    "⚡ 尾盘折溢价套利",
    "🛡️ 期权防暴跌哨",
    "🌐 跨境QDII与锁汇",
    "💡 A/C端选型算费"
])

with box_tab1:
    # 原资产大类、行业暴露、相关性、重合热力、排雷宽表、四象限量价
    ...

with box_tab2:
    # 模块 ② 查看全市场 14 大赛道量化温度计总表
    st.markdown("#### 🌡️ 全市场 14 大赛道量化温度计总表")
    st.caption("📈 14 大赛道真实估值分位、趋势信噪比、20日乖离率与拥挤度全息总表")
    ...

with box_tab3:
    # 模块 ③ 场内ETF与场外联接 14:45 尾盘折溢价套利感知 + 原 ETF 溢价预警
    st.markdown("#### ⚡ 场内ETF与场外联接 14:45 尾盘折溢价套利感知")
    ...

with box_tab4:
    # 模块 ④ 50ETF与300ETF认沽期权隐含波动率防暴跌哨
    st.markdown("#### 🛡️ 50ETF与300ETF认沽期权隐含波动率防暴跌哨")
    ...

with box_tab5:
    # 模块 ⑤ 跨境QDII溢价与外汇期货锁汇成本套利精算
    st.markdown("#### 🌐 跨境QDII溢价与外汇期货锁汇成本套利精算")
    ...

with box_tab6:
    # 原 A/C 份额盈亏平衡计算器
    _render_ac_fee_calculator()
```

---

## 三、 Caveats（注意事项与潜在边界）

1. **测试断言同步更新边界**：
   - 四个只读裁判文件（`judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py`）绝对不能触碰；
   - 扫描发现非只读测试 `tests/test_challenger_g11_m1_actions.py`、`tests/test_g7_architecture_and_decoupling.py`、`AGY2_FundAdvisory/tests/test_m3_full_integration_apptest.py` 内部存在对旧按钮（`btn_master_action_switch`、`btn_add_radar_pool_`、`btn_sentry_act_`、`btn_sentry_evid_`）的静态断言。重构实施时须按指令规则将这些断言同步修正为断言新文案/新组件（或验证其已被移除），否则测试套件会因寻找已删除按钮而红灯。
2. **Tab 4 二级子 Tab CSS 特异性防护**：
   - Streamlit 某些版本在 DOM 中可能将一级 Tab 与二级 Tab 的属性渲染得较为相近。方案中采用 `:not([data-testid="stTabContent"] ...)` 结合 `[data-testid="stMainBlockContainer"] > div > div > [data-testid="stTabs"]` 双重过滤，能 100% 确保二级子 Tab 不会被错误撑大为 46px 网格大胶囊。
3. **首屏性能连锁收益**：
   - 将 4 大深度分析模块（14赛道总表、14:45折溢价、期权IV、QDII锁汇）移入 Tab 4 二级子 Tab 后，首屏初始化时完全无需在主线程运行这 4 组重型分析与网络请求，这与 Explorer 1 负责的痛点 1（首屏秒开）形成了完美的协同支撑。

---

## 四、 Conclusion（最终结论与可落地动作清单）

1. **痛点 2 & 3 执行清单**：
   - [ ] 删除 `app_gui.py` 第 2786-2800 行的 `col_wing_btn` 与 `btn_master_action_switch`，将 `wing_expander` 提升为 100% 满宽。
   - [ ] 将投顾文案自适应状态机更新为：“`今日投顾参谋：持仓含 {N} 只未满 7 天标的，赎回需扣 1.5% 惩罚费，调仓算法已自动为您避开卖出 ｜ 点击展开市场机会与持仓体检`”。
   - [ ] 删除 `app_gui.py` 第 3126 行 `btn_batch_lock_all_7d` 及第 3200-3261 行卡片按钮 `col_s_a`、`col_s_b`，右翼保留纯文本 1~3 条风险卡片。
   - [ ] 删除 `app_gui.py` 第 2963 行左翼 3 个 `btn_add_radar_pool_` 按钮，卡片直接展示优选基金名与 6 位代码。
   - [ ] 从首屏双翼看板移除 5 大模块（拐点尺移出并优化 Tab 1 排版；后 4 个模块移至 Tab 4 二级子 Tab）。双翼看板展开高度严格控制在 $\le 220$px。
2. **痛点 5 执行清单**：
   - [ ] 在 `app_gui.py` 第 1138 行注入高特异性 CSS，实现 100% 全宽四等分网格（高度 46px、字号 16px、加粗 700、实心主色激活态、白色文字强制穿透），并严格隔离 Tab 4 二级子 Tab。
   - [ ] 删除 Tab 1（第 3343 行）、Tab 2（第 4741 行）、Tab 3（第 7649-7650 行）、Tab 4（第 7661-7662 行）内重复的 `st.subheader` 与废话 `caption`。
   - [ ] 在 Tab 4 顶栏（第 6969 与 7080 行）将穿透对象选择器与组合成分档案合并为同一行紧凑摘要卡（左 3.8 列选择器 + 右 6.2 列成分摘要），无缝展示下方图表。
3. **测试同步更新清单**：
   - [ ] 更新 `tests/test_challenger_g11_m1_actions.py`、`AGY2_FundAdvisory/tests/test_m3_full_integration_apptest.py`、`tests/test_g7_architecture_and_decoupling.py` 中对已废除按钮的断言。

---

## 五、 Verification Method（独立验证方法）

实施代理在完成修改后，可通过以下自动化命令与检查点独立验证：

### 1. 静态红线与代码检索核验
```powershell
# 1. 验证伪交易按钮已彻底从 app_gui.py 中绝迹
py -3 -c "code = open('AGY2_FundAdvisory/app_gui.py', encoding='utf-8').read(); assert 'btn_master_action_switch' not in code; assert 'btn_batch_lock_all_7d' not in code; assert 'btn_add_radar_pool_' not in code; print('✅ All pseudo trading buttons removed successfully')"

# 2. 验证重复 subheader 已从四大 Tab 中删除
py -3 -c "code = open('AGY2_FundAdvisory/app_gui.py', encoding='utf-8').read(); assert 'st.subheader(\"🌱 新资建仓\")' not in code; assert 'st.subheader(\"💼 持仓调仓\")' not in code; assert 'st.subheader(\"📈 组合回测\")' not in code; assert 'st.subheader(\"🔍 穿透工具\")' not in code; print('✅ Duplicate tab headers removed successfully')"

# 3. 验证四大只读裁判文件未被篡改
git status AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/tests/test_infra.py AGENT_SPEC.md
```

### 2. Streamlit Headless AppTest 渲染回归
```powershell
# 运行 GUI 核心渲染回归测试
py -3 -m pytest tests/test_e2e_gui_render.py tests/test_interactive_continuity.py AGY2_FundAdvisory/tests/test_m3_full_integration_apptest.py -v
```

### 3. 真实浏览器端核验（通过 /browser 打开 http://localhost:8501）
- [ ] **核验图 2、图 3**：首屏右上角红色大按钮已消失，折叠面板 100% 占满全屏；点击展开后，仅见左翼 3 赛道卡与右翼无按钮纯风险提示，无 4 个套娃抽屉，高度 $\le 220$px。
- [ ] **核验图 5**：页面顶置 46px 高、醒目的四宫格大胶囊主导航栏（新资建仓、持仓调仓、组合回测、穿透工具），点击切换时各 Tab 顶端不再重复打印大标题；进入 Tab 4，顶栏选择器与成分档案并排紧凑展示，6 个二级子 Tab 保持轻量下划线风格。
