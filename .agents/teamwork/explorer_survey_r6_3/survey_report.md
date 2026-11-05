# Wind 智能投顾系统生产级重塑 —— 测试基线、增量用例、安全红线与服务运维调研报告

**调研人**：Explorer 3 (survey_r6_3)  
**工作区目录**：`d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r6_3\`  
**关联任务**：针对 R1~R5 需求执行测试套件基线分析、增量针对性测试 (Delta Test) 设计规范、物理安全只读裁判文件 SHA256 固化审计、以及 8501 端口 Streamlit 服务的平滑重启与健康检查方案。  
**日期**：2026-11-03  

---

## 目录
1. [既有测试基线与套件深度分析](#1-既有测试基线与套件深度分析)
2. [增量测试（Delta Test）精准设计规范](#2-增量测试delta-test精准设计规范)
3. [物理安全红线与只读裁判文件审计基线](#3-物理安全红线与只读裁判文件审计基线)
4. [服务平滑重启与健康检查方案 (SOP)](#4-服务平滑重启与健康检查方案-sop)
5. [结论与执行建议](#5-结论与执行建议)

---

## 1. 既有测试基线与套件深度分析

### 1.1 运行环境与 Pytest 配置
- **Python 运行时**：Python 3.11.9 (`C:\Users\deanc\AppData\Local\Programs\Python\Python311\python.exe`)
- **Pytest 框架版本**：pytest-9.1.1 (包含插件: `anyio-4.13.0`, `asyncio-1.4.0`, `cov-7.1.0`)
- **配置文件**：`d:\Google\Workspace\Wind\pyproject.toml`
  ```toml
  [tool.pytest.ini_options]
  testpaths = ["tests"]
  python_files = ["test_*.py"]
  python_classes = ["Test*"]
  python_functions = ["test_*"]
  ```
  *注意*：由于 `pyproject.toml` 默认声明 `testpaths = ["tests"]`，若需针对 `AGY2_FundAdvisory/tests/` 内的模块执行测试，必须在命令行中显式指定路径，如：
  `py -3 -m pytest AGY2_FundAdvisory/tests/test_deep_remodel_final.py -v`。

### 1.2 核心基线测试验证结果
本次调研对既有两大核心验收测试套件进行了实证无损执行（只读）：

1. **`AGY2_FundAdvisory/tests/test_deep_remodel_final.py`**（**7 passed in 81.73s**）
   - `test_quant_models_weight_differentiation`: 断言四大机构级模型 (HRP-CVaR, Cond-WinRate, Min-CVaR, Kelly-Momentum) 在 6 只与 12 只基金配置下均具有显著梯队倾角，标准差 > 0.005，物理杜绝 1/N 等权退化坍缩。
   - `test_blueprint_cash_conservation_and_percentage_closure`: 验证零起步建仓清单在各资金规模 (5万、10万、33.33万) 下分厘严格平账 (`allocated_sum == total_capital`)、百分比严格闭合 (`weight_pct_sum == 100.0`)、伴生承接标的无重复。
   - `test_winrate_dual_gauge_and_sample_capacity`: 断言胜率引擎输出当下相似条件胜率与全历史胜率双口径对照，滚动窗口期数 > 500。
   - `test_core_indices_csi_dividend_accuracy`: 断言核心指数行情带中证红利 (`000922`) 真实点位对齐，点位 > 4500 点，物理杜绝与上证红利 (`sh000015` 约 3300 点) 张冠李戴。
   - `test_ui_cleanliness_and_title_length`: 扫描 `app_gui.py`，断言无裸露在 HTML 外的 `</div>`，Streamlit 默认 Demo 工具栏被 `display: none` 隐藏，侧边栏展开箭头放行，核心步骤标题字符数严格 <= 7 个汉字。
   - `test_apptest_gui_headless_execution`: 调用 Streamlit 官方 `AppTest.from_file(..., default_timeout=30)` 进行端到端无头执行，断言 `assert not at.exception`。
   - `test_ui_geometry_and_non_overlap_invariants`: 【消灭测试虚荣·空间几何不变量】断言卡片 `overflow: visible !important;`，`min-height: 122px;`，行情药丸 `flex: 0 0 auto !important;` 且外层包裹 `.index-pills-scroll-wrap` 横向平滑滚动容器，数据源映射绝对真实。

2. **`AGY2_FundAdvisory/tests/test_tab_boundaries_and_rebalance.py`**（**5 passed in 47.79s**）
   - `test_generate_ai_rebalance_orders_signatures_and_modes`: 验证调仓生成函数签名支持 `mode` 与 `**kwargs`，验证 gentle (3%缓冲免折腾) 与 forced (一步到位) 模式以及 7 天惩罚期锁仓阻断。
   - `test_winrate_engine_multi_horizon_winrate_table_signature`: 验证胜率表支持 `market_snapshot` 与 `**kwargs` 动态透传。
   - `test_tab2_signature_fallback_logic`: 验证 TypeError 自动降级兼容机制。
   - `test_ast_tab_error_boundaries_isolation`: AST 静态扫描断言 4 个主 Tab（`tab_zero_start`, `tab_holdings_and_rebalance`, `tab_backtest`, `tab_toolbox`）均具备独立顶级 `try...except` 错误隔离。
   - `test_streamlit_apptest_zero_exceptions`: AppTest 渲染断言 0 个未捕获异常、0 个错误横幅、至少 4 个 Tab 容器。

### 1.3 Streamlit AppTest 测试模式精粹
在本工程中，Streamlit 测试统一基于 `streamlit.testing.v1.AppTest` 实现无头仿真：
- **初始化模式**：
  ```python
  from streamlit.testing.v1 import AppTest
  at = AppTest.from_file("AGY2_FundAdvisory/app_gui.py", default_timeout=120)
  ```
- **会话预设与状态模拟**：
  通过 `at.session_state` 预先注入参数（如 `at.session_state.active_tier_val = "C3"`、`at.session_state.target_return_val = 15.0`）。
- **组件交互驱动**：
  - 侧边栏控件：`at.sidebar.selectbox[0].select(...)`，`at.sidebar.slider[0].set_value(...)`。
  - 按钮点击：`at.button[0].click().run()`。
- **双重健康断言**：
  - 未捕获异常拦截：`assert len(at.exception) == 0, f"AppTest 运行异常: {[e.value for e in at.exception]}"`
  - 页面错误横幅拦截：`assert len(at.error) == 0, f"AppTest 页面错误横幅: {[e.value for e in at.error]}"`
- **超时与性能防线**：
  由于全量选基计算涉及 2.8 万只基金漏斗初筛与 2141 天矩阵拟合，AppTest 必须配足 `default_timeout=90~150`，或使用 session_state 缓存机制短路耗时运算。

---

## 2. 增量测试（Delta Test）精准设计规范

根据 `ORIGINAL_REQUEST.md` 的 R1~R5 需求，在交付前严禁盲目重跑全量 40+ 测试套件，必须编写并执行专职的增量针对性测试套件（建议命名为 `AGY2_FundAdvisory/tests/test_delta_remodel_r6.py`）。该套件聚焦于 4 大关键子场景：

### 2.1 侧边栏风控参数：单日限购过滤选择器开启时备选标的自动替换
- **需求背景**：
  侧边栏实盘风控护栏提供单日限购过滤选择器：
  `["不限 (自动拆单承接)", "过滤日限额 < ¥1,000 标的", "过滤日限额 < ¥5,000 标的"]`。
  - 当设为“不限 (自动拆单承接)”时，维持原有多级拆单逻辑（如 `050025` 限额 500 元，多余部分拆单至 `001071`）；
  - 当开启“过滤日限额 < ¥1,000 标的”时，`050025`（限额 500 元 < 1000 元）必须被过滤，Tab 1 选基 (`compute_n_funds_model_portfolio`) 与建仓单 (`generate_zero_start_blueprint`) 自动将其替换为同赛道不限购/大额限额备选标的（如 `001071` 摩根标普500，或 `017436` 华宝纳斯达克）；
  - 当开启“过滤日限额 < ¥5,000 标的”时，限额 < 5000 元的标的同样被替换。
- **Delta 用例设计与断言**：
  ```python
  def test_delta_quota_filter_logic_and_blueprint_replacement():
      """
      用例 2.1a: 验证开启日限购过滤后，低于限额标的被同赛道备选替换，且现金分厘平账。
      """
      # 场景 1: 不限购过滤 (threshold = 0)
      bp_unlimited = StrategyBridge.generate_zero_start_blueprint(
          total_capital=100000.0,
          tier="C3",
          quota_filter_threshold=0.0  # 或 daily_quota_filter="不限 (自动拆单承接)"
      )
      # 验证 050025 存在，且产生限额拆单伴生
      codes_unlimited = [it["fund_code"] for it in bp_unlimited["items"]]
      assert "050025" in codes_unlimited, "不限过滤时应允许 050025 入选并拆单"

      # 场景 2: 过滤 < 1000 标的 (threshold = 1000.0)
      bp_filtered_1k = StrategyBridge.generate_zero_start_blueprint(
          total_capital=100000.0,
          tier="C3",
          quota_filter_threshold=1000.0
      )
      codes_filtered = [it["fund_code"] for it in bp_filtered_1k["items"]]
      # 050025 日限额 500 < 1000，必须被完全替换
      assert "050025" not in codes_filtered, "开启 <1000 过滤后，050025 (限额500) 必须被完全替换！"
      # 必须由同赛道备选标的 (如 001071 或 017436) 承接
      assert any(c in codes_filtered for c in ["001071", "017436"]), "必须替换为同赛道海外对冲备选标的"

      # 场景 3: 严格守死平账与百分比闭合红线
      alloc_sum = sum(it["allocated_amount"] for it in bp_filtered_1k["items"])
      assert abs(alloc_sum - 100000.0) < 1e-2, f"平账误差: {alloc_sum} != 100000.0"
      weight_sum = sum(it["target_weight_pct"] for it in bp_filtered_1k["items"])
      assert abs(weight_sum - 100.0) < 1e-4, f"权重百分比未闭合: {weight_sum} != 100.0"
  ```

### 2.2 侧边栏调仓缓冲带滑块参数（`min_buffer_pct`）正确传递与裁决测试
- **业务机制**：
  侧边栏实盘风控护栏提供 `min_buffer_pct` 滑块（1.0% ~ 5.0%，默认 3.0%），存入 `st.session_state.min_buffer_pct`。
  Tab 2 调仓时机裁决与 `pm.generate_rebalance_plan(..., min_buffer_pct=buffer_pct)` 必须读取该动态参数，而非硬编码 3.0%。
- **Delta 用例设计与断言**：
  ```python
  def test_delta_sidebar_rebalance_buffer_slider_passthrough():
      """
      用例 2.2a: 验证 min_buffer_pct 参数精准控制调仓偏离过滤裁决。
      """
      pm = PortfolioManager()
      # 构造持仓使得某标的偏离度为 2.5% (当前权重 22.5%, 目标权重 20.0%, 偏离 2.5%)
      pm.available_cash = 0.0
      pm.holdings = {
          "100032": FundHolding(
              fund_code="100032", fund_name="富国中证红利指数增强A", share_class="A",
              shares=22500.0, current_nav=1.0, market_value=22500.0,
              batches=[HoldingBatch(batch_id="b1", buy_date="2026-08-01", shares=22500.0, cost_nav=1.0, fee=0.0, holding_days=90)]
          ),
          "002351": FundHolding(
              fund_code="002351", fund_name="易方达裕祥回报债券A", share_class="A",
              shares=77500.0, current_nav=1.0, market_value=77500.0,
              batches=[HoldingBatch(batch_id="b2", buy_date="2026-08-01", shares=77500.0, cost_nav=1.0, fee=0.0, holding_days=90)]
          ),
      }
      pm._recalculate_totals()
      target_w = {"100032": 0.20, "002351": 0.80}

      # 当缓冲带设为 3.0% 时: 偏离度 2.5% < 3.0%，判定为保持现状免操作 (HOLD)
      plan_3pct = pm.generate_rebalance_plan(target_weights=target_w, min_buffer_pct=3.0)
      order_100032_3p = next((it for it in plan_3pct["items"] if it["fund_code"] == "100032"), None)
      assert order_100032_3p["action"] == "HOLD", "偏离 2.5% 在 3.0% 缓冲带内应为 HOLD"
      assert "免操作" in order_100032_3p["action_text"]

      # 当缓冲带降低为 2.0% 时: 偏离度 2.5% >= 2.0%，触发有效减仓调仓 (SELL)
      plan_2pct = pm.generate_rebalance_plan(target_weights=target_w, min_buffer_pct=2.0)
      order_100032_2p = next((it for it in plan_2pct["items"] if it["fund_code"] == "100032"), None)
      assert order_100032_2p["action"] == "SELL", "偏离 2.5% 超出 2.0% 缓冲带应触发调仓"
  ```

### 2.3 Tab 2 持仓账本直接修改当前市值并保存，持仓份额反算与双向同步测试
- **业务机制**：
  - 解除 `st.data_editor` 对 `"当前市值(元)"` 的 `disabled` 锁定。
  - 用户双击表格修改“当前市值”为 `new_mv` 并点击保存时，后台根据 `new_shares = round(new_mv / current_nav, 4)` 精确反算持仓份额。
  - 若用户修改了“持仓份额”为 `new_shares`，则根据 `new_mv = round(new_shares * current_nav, 2)` 更新市值。
  - 自动更新组合总市值与仓位占比，保持分厘平账。
  - 持仓表格列精简为 10 列以内，持有天数与赎回费状态合并为一列直观展示。
- **Delta 用例设计与断言**：
  ```python
  def test_delta_holdings_table_market_value_reverse_calc():
      """
      用例 2.3a: 验证修改市值反算份额、修改份额同步市值、以及表格列精简 <= 10 列。
      """
      pm = PortfolioManager()
      # 初始状态: 份额 10,000，净值 1.2500，初始市值 12,500.0
      pm.add_or_update_holding(
          fund_code="005561", shares=10000.0, nav=1.2500, cost_price=1.2000,
          holding_days=45, dividend_method="cash"
      )
      h = pm.holdings["005561"]
      assert abs(h.market_value - 12500.0) < 1e-2

      # 1. 模拟在表格中直接修改当前市值为 15,000.0 元并保存
      # 后台反算逻辑: shares = round(15000.0 / 1.2500, 4) = 12000.0
      new_mv = 15000.0
      calc_shares = round(new_mv / h.current_nav, 4)
      pm.add_or_update_holding(
          fund_code="005561", shares=calc_shares, nav=h.current_nav, cost_price=h.cost_price,
          holding_days=45, dividend_method="cash"
      )
      assert abs(pm.holdings["005561"].shares - 12000.0) < 1e-4, "修改市值 15000 元后份额应反算为 12000"
      assert abs(pm.holdings["005561"].market_value - 15000.0) < 1e-2, "市值应同步更新为 15000 元"

      # 2. 模拟修改份额为 8,000 份并保存
      new_shares_2 = 8000.0
      calc_mv_2 = round(new_shares_2 * h.current_nav, 2)
      pm.add_or_update_holding(
          fund_code="005561", shares=new_shares_2, nav=h.current_nav, cost_price=h.cost_price,
          holding_days=45, dividend_method="cash"
      )
      assert abs(pm.holdings["005561"].shares - 8000.0) < 1e-4
      assert abs(pm.holdings["005561"].market_value - 10000.0) < 1e-2

      # 3. 验证导出的持仓表格列数精简至 10 列以内
      df_disp = pm.export_snapshot_df()
      # 目标列结构包含: 基金代码、基金名称、份额类型、持仓份额、当前净值、当前市值(元)、持仓占比(%)、持仓成本价、浮动盈亏率(%)、持有天数与赎回费状态
      assert len(df_disp.columns) <= 10, f"表格列数 {len(df_disp.columns)} 超过 10 列限制！当前列: {list(df_disp.columns)}"
      assert "当前市值(元)" in df_disp.columns
      assert "持有天数与赎回费状态" in df_disp.columns or "赎回费安全状态" in df_disp.columns
  ```

### 2.4 4 个 Tab 交互零异常（AppTest 端到端覆盖）
- **业务机制**：
  在 Streamlit `AppTest` 框架下，端到端执行全流程仿真，确保新增的侧边栏风控护栏、Tab 2 概览卡与工具坞不破坏原有渲染生态，断言 `len(at.exception) == 0` 与 `len(at.error) == 0`。
- **Delta 用例设计与断言**：
  ```python
  def test_delta_apptest_four_tabs_zero_exception():
      """
      用例 2.4a: 端到端 AppTest 4 个 Tab 交互渲染零异常。
      """
      from streamlit.testing.v1 import AppTest
      gui_path = Path("AGY2_FundAdvisory/app_gui.py").resolve()
      at = AppTest.from_file(str(gui_path), default_timeout=120)

      # 预设会话状态
      at.session_state.active_tier_val = "C3"
      at.session_state.target_return_val = 15.0
      at.session_state.min_buffer_pct = 3.0
      at.session_state.quota_filter_threshold = 0.0

      at.run()
      assert len(at.exception) == 0, f"首屏渲染抛出异常: {[e.value for e in at.exception]}"
      assert len(at.error) == 0, f"首屏存在错误横幅: {[e.value for e in at.error]}"
      assert len(at.tabs) >= 4, f"必须渲染 4 个主 Tab，实际: {len(at.tabs)}"

      # 静态几何不变量断言 (GEMINI.md Rule 14 & Rule 15)
      gui_text = gui_path.read_text(encoding="utf-8")
      assert 'overflow: visible !important;' in gui_text, "主看板卡片必须 overflow: visible !important"
      assert 'flex: 0 0 auto !important;' in gui_text, "指数药丸必须 flex: 0 0 auto 物理防压扁"
      assert 'overflow-x: auto !important;' in gui_text, "指数条必须配置横向滚动容器"
  ```

---

## 3. 物理安全红线与只读裁判文件审计基线

为落实项目“严禁触碰裁判模块与盲测隔离层”的最高物理安全红线，本次调研对 4 大裁判基建文件进行了物理存在定位与初始 SHA256 哈希值固化测算。

### 3.1 裁判文件审计基准对照表

| 序号 | 裁判文件标识 | 物理绝对路径 | 文件大小 (Bytes) | 初始 SHA256 校验哈希 (Baseline) | 审计性质 |
|:---:|:---|:---|:---:|:---|:---:|
| 1 | **`judge_engine.py`** | `D:\Google\Workspace\Wind\AGY2_FundAdvisory\judge_engine.py` | 13,018 | `76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF31CC07BE` | 🔒 只读裁判核心 |
| 2 | **`holdout_vault.py`** | `D:\Google\Workspace\Wind\AGY2_FundAdvisory\holdout_vault.py` | 10,729 | `88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670BD031D2A` | 🔒 盲测金库隔离 |
| 3 | **`AGENT_SPEC.md`** | `D:\Google\Workspace\Wind\AGY2_FundAdvisory\AGENT_SPEC.md` | 17,204 | `A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B800CD63957` | 🔒 智能体规范红线 |
| 4 | **`test_infra.py` (AGY2)** | `D:\Google\Workspace\Wind\AGY2_FundAdvisory\tests\test_infra.py` | 10,524 | `B8D781BE8135BE05CF61E62E4B534E359985AD880F27FFB61228A33DF6B02A6A` | 🔒 裁判测试套件 |
| 5 | **`test_infra.py` (根目录)**| `D:\Google\Workspace\Wind\tests\test_infra.py` | 10,184 | `48BEE0DA300D7C0A0848EC1376E4B9B2E55224D2736081713B4340F0362CD100` | 🔒 根目录测试镜像 |

*注：经严格扫描，项目根目录下不存在 `judge_engine.py`、`holdout_vault.py` 或 `AGENT_SPEC.md`，它们仅唯一位于 `AGY2_FundAdvisory/` 目录下；根目录下的 `tests/test_infra.py` 为入口跳转镜像。在后续任何 Worker 修改、Reviewer 审核及交付前核验阶段，上述哈希值必须 100% 保持一致，任何单字节变化均触发违规阻断。*

---

## 4. 服务平滑重启与健康检查方案 (SOP)

### 4.1 现有服务常驻架构分析
工程现有 Streamlit 桌面服务托管方案遵循 Windows 原生无黑框与单实例规范：
- **无窗口静默启动器**：`AGY2_FundAdvisory/start_silent_service.vbs`
  - 使用 Windows 原生 VBScript：`Set WshShell = CreateObject("WScript.Shell")`
  - 采用无窗口标志脱钩运行：`WshShell.Run cmdStart, 0, False`（`0 = SW_HIDE`，杜绝终端黑框）。
  - 启动命令行：`"C:\Users\deanc\AppData\Local\Programs\Python\Python311\python.exe" -m streamlit run app_gui.py --server.headless=true --server.port=8501`。
- **自愈引导器**：`AGY2_FundAdvisory/launch_gui.vbs`
  - 内置探测函数 `IsPortListening(8501)`，调用 `MSXML2.ServerXMLHTTP.6.0` 请求 `http://127.0.0.1:8501/_stcore/health`。
  - 未就绪时静默拉起后台服务并循环轮询 15 秒；就绪后以独立应用窗口呼出：`msedge.exe --app=http://localhost:8501`。

### 4.2 GEMINI.md Rule 12 & user_global Rule 12 遵从规范
重构交付后平滑重启 8501 端口服务时，必须严格执行以下三道防御：
1. **非破坏性探针先行**：
   严禁盲目执行 `taskkill /f /im python.exe` 或 `taskkill /f /im streamlit.exe`，严防误杀其他 Python 任务或 Windows 系统出站进程。
2. **连接状态甄别（区分 LISTENING vs ESTABLISHED）**：
   执行 `netstat -ano | findstr 8501`：
   - 若状态为 `LISTENING`：说明是正在监听的 Web 服务。获取其 PID，核验其进程所属（如确认命令行包含 `app_gui.py`），方可对其单进程进行优雅关闭。
   - 若状态为 `ESTABLISHED` 或 `TIME_WAIT`：说明是 Windows 客户端出站随机分配的高位端口瞬态碰撞，**严禁 kill 对应进程**，必须采用 1~2s 缓冲重试或递增端口启动。

### 4.3 平滑重启与健康检查标准操作脚本 (SOP)
为保证在 Windows 命令行下的幂等性与跨环境稳定性（遵循 user_global Rule 14 脚本化准则），建议通过以下 Python 脚本完成平滑重启与健康探测：

```python
# scripts/safe_restart_service.py
import sys
import time
import subprocess
import urllib.request
from pathlib import Path

WORKSPACE = Path(r"D:\Google\Workspace\Wind")
AGY2_DIR = WORKSPACE / "AGY2_FundAdvisory"
HEALTH_URL = "http://127.0.0.1:8501/_stcore/health"

def inspect_port_8501():
    """非破坏性探测 8501 端口占用情况"""
    try:
        output = subprocess.check_output("netstat -ano", shell=True, text=True)
        listening_pids = []
        for line in output.splitlines():
            if ":8501" in line and "LISTENING" in line:
                parts = line.strip().split()
                pid = int(parts[-1])
                listening_pids.append(pid)
        return listening_pids
    except Exception as e:
        print(f"探针扫描异常: {e}")
        return []

def safe_stop_old_service():
    """甄别后精准优雅关闭旧 streamlit 实例"""
    pids = inspect_port_8501()
    for pid in pids:
        try:
            # 校验进程命令行确保确为 app_gui.py
            cmd_info = subprocess.check_output(f'powershell -NoProfile -Command "(Get-CimInstance Win32_Process -Filter \\"ProcessId = {pid}\\").CommandLine"', shell=True, text=True)
            if "app_gui.py" in cmd_info or "streamlit" in cmd_info:
                print(f"正在精准关闭旧 Streamlit 服务实例 (PID={pid})...")
                subprocess.run(f"powershell -NoProfile -Command Stop-Process -Id {pid} -Force", shell=True)
                time.sleep(1.5)
        except Exception as e:
            print(f"关闭 PID {pid} 失败: {e}")

def start_silent_service():
    """利用 VBScript 无窗口静默拉起"""
    vbs_path = AGY2_DIR / "start_silent_service.vbs"
    print(f"正在通过 {vbs_path} 静默启动 Streamlit...")
    subprocess.run(f'wscript.exe "{vbs_path}"', shell=True)

def verify_health_probe(max_retries=15):
    """HTTP 健康探测 (/_stcore/health)"""
    print(f"正在执行健康探测: {HEALTH_URL} ...")
    for i in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(HEALTH_URL, headers={"User-Agent": "Probe/1.0"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    body = resp.read().decode("utf-8").strip()
                    print(f"✅ 服务健康探针通过！(第 {i} 次探测成功，HTTP 200, 响应: '{body}')")
                    return True
        except Exception:
            time.sleep(1.0)
    print("❌ 健康探针超时未响应！")
    return False

if __name__ == "__main__":
    safe_stop_old_service()
    start_silent_service()
    if not verify_health_probe():
        sys.exit(1)
    print("🚀 Streamlit 服务平滑重启完成且健康运行！")
```

---

## 5. 结论与执行建议

1. **测试基线完备**：既有 `test_deep_remodel_final.py`（7 用例）与 `test_tab_boundaries_and_rebalance.py`（5 用例）已 100% 全绿通过，为重构提供了坚实的回归参照底座。
2. **Delta 增量测试靶向明确**：测试责任下沉，必须新建 `test_delta_remodel_r6.py` 覆盖单日限购过滤自动替换、调仓缓冲带传递裁决、持仓市值反算份额、以及 4-Tab 交互 0 异常。交付前仅跑该 Delta 测试套件与 `test_deep_remodel_final.py`，杜绝重复重跑全库。
3. **物理安全基线已锚定**：4 个裁判文件初始 SHA256 已在此全面固化，后续阶段执行严禁修改此 4 文件。
4. **运维重启脚本就绪**：严格遵守 GEMINI.md Rule 12，采用先探测、非破坏甄别、VBScript 静默托管、以及 `/_stcore/health` HTTP 200 探针的标准流程平滑交付。
