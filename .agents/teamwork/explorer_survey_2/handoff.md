# Phase 2 核心架构与代码走查报告 (Routing, Styles, Rolling 3Y DCA & OCR Fusion)

**报告编写代理**: Explorer 2 (Teamwork Explorer)  
**工作区路径**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory`  
**报告交付路径**: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_2\handoff.md`  
**调查时间**: 2026-11-15T07:56:00Z  

---

## 一、直接观察证据 (Observation)

### 1. 首次加载存量账本（持仓数 >= 10）自动路由状态机走查
- **代码位置**: `AGY2_FundAdvisory/app_gui.py:2704-2715` vs `AGY2_FundAdvisory/app_gui.py:3252-3269`
- **现状观察**:
  1. `pm = st.session_state.pm` 初始化位于 `app_gui.py` 第 2715 行：
     ```python
     pm: PortfolioManager = st.session_state.pm
     clock = pm.clock
     calc = pm.calculator
     ```
     在第 2715 行初始化后，**完全没有任何自动路由检查**。
  2. 当前的自动路由判断被错误地延迟到了第 3252~3269 行（在顶部全局看板渲染前夕，跨越了 500 多行代码）：
     ```python
     # 首次加载智能自动路由：若当前激活账本为存量组合（如实战29基或持仓数>=8只），首次进入自动聚焦至 Tab 2 (💼 持仓调仓)
     if "_initial_ledger_routed" not in st.session_state:
         st.session_state["_initial_ledger_routed"] = True
         cur_pm_init = mlm_inst.get_pm(active_lid) if mlm_inst else pm
         if cur_pm_init and len(cur_pm_init.holdings) >= 8:
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
  3. **现存缺陷核查**:
     - 阈值不一致：原代码写了 `>= 8`，而最新权威规范与需求明确要求为 `>= 10`。
     - 触发信号缺失：第 3267~3268 行只设置了 `tab2_diagnosed = True` 和 `tab2_rebalanced = True`，遗漏了 `st.session_state.tab2_trigger_diagnose = True`、`st.session_state.tab2_trigger_rebalance = True` 和 `st.session_state["last_cross_tab_action"]`（对比第 2867~2871 行 `switch_active_ledger` 内部的完备状态）。
     - 账本状态实测：实测 `data/ledgers_index.json`，当前激活账本 `active_ledger_id` 为 `main_live`（含 6 只标的），而 `combat_29_funds`（实战存量组合）含 29 只标的。若用户首次以 `combat_29_funds` 启动，或激活账本包含不少于 10 只标的，必须在 `pm` 初始化瞬间立即完成路由，避免后续数百行渲染逻辑采用旧路由上下文。

---

### 2. 首席投顾裁决卡样式合并与手机端列选择器/数字输入框过滤排查
- **代码位置 1**: `AGY2_FundAdvisory/app_gui.py:327-385`（`render_chief_advisor_memo_card`）
  - 现象：函数内部每次执行都在最前部硬编码嵌入 58 行 `<style>...</style>` 标签：
    ```python
    html_code = f"""<style>
    .chief-memo-container {{
    container: memo-desk / inline-size;
    width: 100%;
    }}
    .chief-memo-grid {{
    display: grid;
    ...
    </style>
    <div class="chief-memo-container" ...>
    ```
  - 影响：每次 Streamlit 触发 rerun 重绘（如切换档位、点击按钮、滑块调整），该样式标签都会重复注入 DOM，造成样式冗余解析开销。
- **代码位置 2**: `AGY2_FundAdvisory/app_gui.py:795-1922`（全局主样式表）
  - 现象：全局样式表集中定义在第 795~1922 行。第 327~385 行定义的 `.chief-memo-container`、`.chief-memo-grid`、`.chief-memo-capsule` 等样式尚未合入该全局主样式表。
- **代码位置 3**: `AGY2_FundAdvisory/app_gui.py:1905-1916`（手机端按钮组网格流样式）
  - 现有代码：
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
  - **严重缺陷确认**:
    1. **选择器遗漏 `stColumn`**: 现代 Streamlit 版本在渲染列容器时，部分使用 `div[data-testid="stColumn"]`，部分使用 `div[data-testid="column"]`（例如第 937~938 行已做双重兼容）。此处仅写了 `div[data-testid="column"]`，导致在部分移动端视口下列宽规则未命中。
    2. **数字输入框误伤击穿**: Streamlit 的数字步进组件 `st.number_input` 内部天生包含加减步进按钮（`[data-testid="stNumberInput"] button` 或 `stNumberInputStepUp/StepDown`）。由于规则使用了 `:has(button)` 粗暴匹配，包含数字输入框的水平块会被误判为“按钮组”，将其内部列强制设为 50% 宽度，造成数字输入框在手机端被暴力腰斩挤压！

---

### 3. 近 3 年滚动发车定投盲测胜率实证表技术链路
- **代码位置**: `AGY2_FundAdvisory/strategy_bridge.py:7078-7258` 与 `AGY2_FundAdvisory/app_gui.py:7380-7485`
- **现状观察**:
  1. 目前 `strategy_bridge.py` 仅提供 `run_historical_time_machine_backtest(target_date, tier, capital, ...)`，支持用户输入单个静态日期（如 2024-09-18、2022-04-26）查看该单一时点前推 3M/6M/1Y 的净值与 KPI。
  2. 缺少针对过去 3 年（例如 2023 年至 2026 年）**双月/季度滚动发车**（Rolling Start DCA）的统计聚合模块。
  3. 用户需求明确要求：
     - 在完全切断未来函数（Point-in-Time）前提下；
     - 全额扣除：申购费（A类 0.12% / C类 0%）、阶梯赎回费（未满7天 1.50%、未满30天 0.50%、未满180天阶梯扣费、>=365天 0%）、销售服务费（C类 0.40%/250 逐日计提）、公募托管管理费；
     - 统计持有满 180 天与 365 天的正收益胜率、平均净收益率与相对沪深 300 的超额收益（Alpha）。

---

### 4. 输入审计项深入走查 (Task 1 & Task 2 from agy2 (3).md)

#### 4.1 `calculate_mutual_fund_friction_bill` 假常数走查
- **代码位置**: `AGY2_FundAdvisory/strategy_bridge.py:5926-5930` 及 `5975-5979`
- **代码切片**:
  ```python
  # 第 5926-5930 行 (is_combat_29 分支)
  cagr_val = 14.28
  mdd_all = -17.24
  mdd_1y = -6.68
  recovery_days = 452
  dividend_yield = 2.10

  # 第 5975-5979 行 (动态/其它方案分支)
  cagr_val = 16.85
  mdd_all = -16.76
  mdd_1y = -6.24
  recovery_days = 394
  dividend_yield = 3.42
  ```
- **法证核实**: 此处的 `cagr_val`、`mdd_all`、`mdd_1y`、`recovery_days`、`dividend_yield` 确实直接使用了固定静态假常数，未随传入的 `weights` 动态测算！

#### 4.2 `run_historical_time_machine_backtest` 扣费模型审计
- **代码位置**: `AGY2_FundAdvisory/strategy_bridge.py:7114-7145` 及 `7196-7206`
- **缺陷核实**:
  1. 日度持有成本遗漏公募管理托管费：第 7143 行代码为：
     ```python
     eff_day_ret = 0.95 * day_ret + 0.05 * cash_ret_daily - (0.5 * c_sales_fee_daily)
     ```
     仅扣除了 C 类销售服务费的一半，**完全未计提中国公募基金标准的日度管理费与托管费（行业中枢年化 0.75%，折算日度为 0.0075 / 250.0）**。
  2. 申购费一刀切：第 7115~7116 行写死 `sub_fee_rate = 0.0012`，未按实际组合中 A/C 份额比例动态打折（C 类申购费应为 0.00%）。
  3. 阶梯赎回费未考虑 A/C 份额差异：第 7197~7206 行的 FIFO 赎回费为纯统一阶梯，若标的为 C 类且持有满 30 天，法规划定免赎回费，此处仍对持有 30~180 天收取 0.35%~0.50%。

#### 4.3 `portfolio_manager.py` 截图 OCR 提前 return 与词表缺陷
- **代码位置 1**: `AGY2_FundAdvisory/portfolio_manager.py:1894-1908`
  - 代码切片：
    ```python
    # 1. 尝试以聚合成的完整多行文本直接送入 parse_smart_text_holdings 提取
    raw_lines = [item[2] for item in all_ocr_items]
    aggregated_text = "\n".join(raw_lines)
    parsed_candidates = parse_smart_text_holdings(aggregated_text)
    if parsed_candidates:
        seen = set()
        clean_res = []
        for p in parsed_candidates:
            c = p.get("fund_code")
            if c and c not in seen:
                seen.add(c)
                clean_res.append(p)
        if len(clean_res) >= 1:
            return clean_res

    # 2. 空间块聚类提取分支（针对多栏布局排版）
    blocks = []
    ...
    ```
  - **严重缺陷确认**: 只要 `parse_smart_text_holdings` 识别出 $\ge 1$ 只基金（`len(clean_res) >= 1`），函数就**直接提前 return**，彻底丢弃下方的“空间块聚类提取分支”！如果一张截图包含 15 只基金，但文本通道因版面折行只匹配出 2 只，剩余 13 只就被强行丢弃！必须改为**双通道并集融合 (Dual-Channel Union Fusion)**。
- **代码位置 2**: `AGY2_FundAdvisory/portfolio_manager.py:1403-1410`
  - 现象：在 `parse_smart_text_holdings` 中，过滤基金名称干扰数字的词表仅有少数几个项：
    ```python
    for alias_kw in [
        "科创50", "中证1000", "中证500", "沪深300", "标普500", "30天",
        "红利低波", "中证红利", "裕祥回报", "华安黄金", "黄金ETF", "白酒",
        "集成电路", "动漫游戏", "新能源", "半导体", "纳斯达克100", "纳指",
        "ETF联接", "ETF", "联接", "A类", "C类"
    ]:
        remain_line = remain_line.replace(alias_kw, " ")
    ```
  - 缺陷：缺少大量常见的宽基指数代码与持有期数字（如“中证2000”、“中证800”、“中证A500”、“A500”、“A50”、“创业板50”、“日经225”、“30天持有”、“60天持有”、“90天持有”、“180天持有”、“360天持有”、“1年持有”等）。这会导致“华夏中证A500ETF联接 30天持有”中的“500”和“30”残留，在下方金额正则匹配时被误判为用户的持仓金额！

---

## 二、逻辑推导链 (Logic Chain)

```
[Observation 1]
pm 初始化在 app_gui.py 第 2715 行，而路由逻辑延迟至 3253 行且仅判断 len >= 8
     │
     ├── 逻辑推导 1.1: 首次打开页面加载 29 只基金账本时，主界面在 2715~3253 行期间
     │                 仍然处于未路由状态，甚至可能停留在 Tab 1，且缺少 trigger 标记。
     └── 落地设计 1.2: 将路由检查提前至第 2718 行（pm 初始化后立即执行），
                       判断 len(pm.holdings) >= 10，并同步写入 pending_cross_tab_jump、
                       tab2_view_mode、tab2_diagnosed、tab2_rebalanced、
                       tab2_trigger_diagnose、tab2_trigger_rebalance。

[Observation 2]
render_chief_advisor_memo_card 每次调用均在 HTML 头部拼入 58 行 <style> 标签；
手机端按钮 CSS 规则使用 :has(button) 未排除 number_input 且缺少 stColumn
     │
     ├── 逻辑推导 2.1: 重复样式注入导致 DOM 膨胀与解析抖动；应将样式剪切至全局样式表（第 795 行主样式）。
     └── 逻辑推导 2.2: number_input 内部包含加减按钮，导致包含数字输入的水平块被错误施加 50% 网格；
                       增加 :not(:has([data-testid="stNumberInput"])) 排除，并补充 stColumn 选择器。

[Observation 3]
历史回测仅有时点时光机单点推演，缺少近 3 年滚动发车实证表
     │
     ├── 逻辑推导 3.1: 需在 StrategyBridge 中构建 calculate_rolling_dca_3y_backtest 方法，
     │                 按双月/季度步长采样过去 3 年所有起点，严格切断未来数据生成配置。
     └── 逻辑推导 3.2: 全额扣减 A 类 0.12% 申购费、0.75%/250 公募管理托管费、C 类销售服务费与
                       阶梯赎回费，输出持有 180d、365d 的真实正收益胜率、平均净收益率与超额 Alpha。

[Observation 4]
calculate_mutual_fund_friction_bill 硬编码静态 cagr/mdd/recovery/div 指标；
run_historical_time_machine_backtest 未扣 0.75%/250 托管管理费；
parse_screenshot_ocr_holdings 只要 len>=1 就丢弃空间块聚类；
parse_smart_text_holdings 缺少 A500/2000/30天持有等词表
     │
     ├── 逻辑推导 4.1: 基于 weights 与 load_matrix() 历史序列加权动态精算 CAGR、MDD、恢复天数与股息率。
     ├── 逻辑推导 4.2: 回测循环中扣减 (0.0075 / 250.0) 日度公募底费，并区分 A/C 份额阶梯赎回费。
     ├── 逻辑推导 4.3: OCR 解析改为双通道并集，以 fund_code 聚合去重，优先保留高置信度字段。
     └── 逻辑推导 4.4: 扩充 alias_kw 词表，全面剥离指数与持有期数字，杜绝金额误识别。
```

---

## 三、限制与假设 (Caveats)

1. **只读探索边界**: 本次调研严格保持只读，未对 `app_gui.py`、`strategy_bridge.py`、`portfolio_manager.py` 做出任何写操作。所有代码均在探针脚本与测试环境中完成静态走查与动态探针校验。
2. **测试环境时钟漂移**: `test_portfolio_manager.py` 中有 3 项用例因基准日硬编码为 `2026-10-28` 而当前测试执行日已为 `2026-11-15`，导致天数计算超过 7 天锁定期而断言失败。Worker 在修复时应意识到这是用例中固定日期相对系统时钟漂移所致，业务核心逻辑本身完全正常。
3. **只读裁判文件绝对保护**: `judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py` 严格禁止任何修改。

---

## 四、结论与 Worker 施工蓝图 (Conclusion & Recommendations)

针对 Phase 2 的具体落地，给后续 Worker 代理提供精确到行号的代码实现方案：

### 任务 1：存量持仓账本首次加载自动路由 (`app_gui.py`)
- **修改位置**: `app_gui.py:2715-2720`（紧随 `pm: PortfolioManager = st.session_state.pm` 之后）
- **具体实现方案**:
  ```python
  pm: PortfolioManager = st.session_state.pm
  clock = pm.clock
  calc = pm.calculator

  # ── G19 首次加载存量持仓账本自动路由闭环 (持仓标的数 >= 10 只) ──
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
- **同步清理**: 清理或简化第 3252~3269 行的延迟检查，避免逻辑重复。

---

### 任务 2：样式合并与手机端列选择器/数字输入框修复 (`app_gui.py`)
1. **剥离 `render_chief_advisor_memo_card` 中的 `<style>` 标签**:
   - 在第 327~385 行，删除 `html_code = f"""<style> ... </style>` 中的 `<style>` 块，`html_code` 直接以 `<div class="chief-memo-container" ...>` 开始。
   - 将 `.chief-memo-container`、`.chief-memo-grid`、`.chief-memo-capsule`、`.chief-memo-capsule-title`、`.chief-memo-capsule-sub` 及 `@container memo-desk`、`@media (max-width: 768px)` 完整迁移至第 1050 行前后的全局主样式表中。
2. **修复手机端按钮组网格选择器并排除数字输入框**:
   - 在第 1905~1916 行替换为：
   ```css
   /* 表格底部按钮组在手机端 2x2 网格流 (精准排除数字输入框的加减步进按钮) */
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

### 任务 3：近 3 年滚动发车定投盲测胜率实证表 (`strategy_bridge.py` & `app_gui.py`)
1. **在 `strategy_bridge.py` 新增 `calculate_rolling_dca_3y_backtest` 类方法**:
   - 算法流程：
     1. 获取历史矩阵 `df = cls.load_matrix()`，以最新日期为基准回溯 3 年（如 750 个交易日）。
     2. 以双月（约每 42 个交易日）或季度（约每 63 个交易日）为步长采样起点 $T_i$。
     3. 对每个起点 $T_i$：以 $t \le T_i$ 切片运行当时的策略权重；向后推演 180 天与 365 天窗口。
     4. 全额扣费：
        - 前端申购费：按 A 类 0.12% 扣减（C 类 0%）；
        - 日度持有成本：扣除公募管理托管费 $(0.0075 / 250.0)$ 与 C 类销售服务费 $(0.0040 / 250.0)$；
        - 到期阶梯赎回费：180 天 A 类按 0.10% 扣除（C 类 0%），365 天按 0.00% 免除。
     5. 同期对比沪深 300 涨跌幅。
     6. 输出聚合胜率卡片与表格：
        - 180 天持有期：胜率 (Net Win Rate %)、超额胜率 (Alpha Win Rate %)、平均净收益率、平均沪深300收益率、平均超额收益率、最大回撤均值。
        - 365 天持有期：同上统计指标。
2. **在 `app_gui.py` Tab 3 历史盲测区域呈现**:
   - 在第 7480 行附近（时点时光机图表下方），调用该函数并渲染“近三年滚动发车定投胜率实证表（Point-in-Time 零未来函数·全真交易摩擦）”。

---

### 任务 4：输入审计项修复 (Task 1 & Task 2)
1. **`calculate_mutual_fund_friction_bill` 动态指标精算 (`strategy_bridge.py:5926-5980`)**:
   - 移除写死的 `cagr_val=16.85, mdd_all=-16.76, mdd_1y=-6.24, recovery_days=394, dividend_yield=3.42`；
   - 股息率：利用已有的 `dividend_yield_map` 按照权重加权求和；
   - CAGR 与 MDD：利用 `df = cls.load_matrix()` 与资产收益率序列对 `weights` 加权计算组合日收益率，动态精算近 1 年最大回撤 `mdd_1y`、全周期最大回撤 `mdd_all`、年化复合收益率 `cagr_val` 与水下恢复天数 `recovery_days`。
2. **`run_historical_time_machine_backtest` 扣费补全 (`strategy_bridge.py:7143`)**:
   - 在日度循环中增加：`mgmt_custody_fee_daily = 0.0075 / 250.0`；
   - 更新日净收益率计算公式：
     ```python
     eff_day_ret = 0.95 * day_ret + 0.05 * cash_ret_daily - (c_ratio * c_sales_fee_daily) - mgmt_custody_fee_daily
     ```
   - 在赎回费与申购费中考虑 A/C 份额比例加权。
3. **`parse_screenshot_ocr_holdings` 双通道并集融合 (`portfolio_manager.py:1894-1925`)**:
   - 删除 `if len(clean_res) >= 1: return clean_res`；
   - 提取 `results_smart = clean_res`；
   - 继续运行“空间块聚类分支”得到 `results_block = structured_holdings`；
   - 执行双通道并集融合：以 `fund_code` 为主键，合并两者结果（优先补充未被文本通道识别到的尾仓或复杂多栏标的）。
4. **`parse_smart_text_holdings` 扩充词表 (`portfolio_manager.py:1403-1410`)**:
   - 扩充 `alias_kw` 列表，加入宽基指数与持有期数字：
     ```python
     for alias_kw in [
         "中证2000", "中证1000", "中证800", "中证500", "沪深300", "中证A500", "A500", "A50",
         "科创50", "创业板50", "标普500", "富时100", "日经225", "纳斯达克100", "纳指",
         "30天持有", "60天持有", "90天持有", "180天持有", "360天持有", "365天持有",
         "1年持有", "2年持有", "3年持有", "6个月持有", "3个月持有", "12个月持有",
         "30天", "60天", "90天", "180天", "365天", "1年", "2年", "3年", "6个月", "3个月",
         "红利低波", "中证红利", "裕祥回报", "华安黄金", "黄金ETF", "白酒",
         "集成电路", "动漫游戏", "新能源", "半导体",
         "ETF联接", "ETF", "联接", "A类", "C类"
     ]:
         remain_line = remain_line.replace(alias_kw, " ")
     ```

---

## 五、独立验证方法 (Verification Method)

Worker 实施完成后，可通过以下命令进行客观、独立验证：

1. **单元测试回归验证**:
   ```powershell
   py -3 -m pytest AGY2_FundAdvisory/tests/test_strategy_bridge.py -q
   ```
   预期：11 passed 且 100% 绿灯。

2. **动态精算与扣费逻辑验证**:
   在 Python 终端中执行验证脚本：
   ```python
   from AGY2_FundAdvisory.strategy_bridge import StrategyBridge
   bill = StrategyBridge.calculate_mutual_fund_friction_bill({"005561": 0.5, "110020": 0.5})
   assert bill["cagr_pct"] != 16.85  # 确认非硬编码
   assert bill["dividend_yield_pct"] > 0
   ```

3. **双视口与自动路由核验 (使用 /browser)**:
   - 启动 Streamlit 服务：`streamlit run AGY2_FundAdvisory/app_gui.py`；
   - 访问 `http://localhost:8501`；
   - 验证：首次打开且当前账本为 29 只基金时，自动聚焦至“💼 持仓调仓”工作区，展示诊断与清扫建议；
   - 切换手机视口（640px）：核验所有数字输入框正常呈现，未被压缩至 50% 网格。
