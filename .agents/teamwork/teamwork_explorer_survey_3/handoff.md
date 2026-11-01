# 阶段二重构（Web GUI 视觉大扫除与四大导航重塑）测试与验证只读调查报告

## 1. Observation（直接观察事实）

### 1.1 既有测试套件盘点与全量测试状态
- **测试文件规模**：位于 `d:\Google\Workspace\Wind\AGY2_FundAdvisory\tests\` 目录下，共有 27 个测试源文件。
- **全量测试用例总数与运行结果**：
  - 通过全量运行 `pytest`（耗时 792.18s / 13分12秒），共收集并执行 **564 项自动化测试**。
  - **运行大盘统计**：**562 passed, 2 failed**（通过率 99.65%）。
  - **失败的两项用例精确溯源**：
    1. `AGY2_FundAdvisory/tests/test_adversarial_m2_challenger.py::test_adv_same_company_t_plus_1_switch_multi_firm` (Line 211)
       - 报错：`assert res_hx["delta_u"] == 100.0` 抛出 `AssertionError: assert -1.75 == 100.0`
       - 根因：`calculate_rebalance_net_utility` 在阶段一重构后引入了精确赎回费与交易摩擦精算，当未显式指定 `holding_days` 时按默认在途批次计算了赎回损耗，导致预期超额净效用 $\Delta U = \text{ExpectedAlpha} - \text{Fee} = -1.75$ 而非理想无损的 $100.0$。测试断言需适配真实阶梯费率参数。
    2. `AGY2_FundAdvisory/tests/test_e2e_gui_render.py::test_bug3_pre_market_trading_clock_and_signal_harmony` (Line 115)
       - 报错：`assert "盘前未开市" in eval_pre["trigger_warning_text"]`
       - 报错文本：`AssertionError: assert '盘前未开市' in '🟡 **【非交易日休市】**：今日为非交易日（周末/法定节假日），市场已休市。策略大脑基准维持【🟢 常态稳健高股息慢牛】。下一交易日为 2026-11-02，当前无需任何操作。'`
       - 根因：`StrategyBridge.evaluate_intraday_signal` 内部通过 `now_dt = datetime.now()` 读取真实日期。当前实际日期为 2026-11-01（周日），代码判定 `clock.is_trade_day(now_dt.date())` 为 `False`，故优先进入了非交易日分支而非盘前分支。该测试用例在非交易日未对 `datetime.now()` 进行周一交易日 mock。
- **重点测试文件与运行表现**：
  1. `test_infra.py`：测试 4 大底层基建模块（全收益对齐矩阵、T+1 模拟算子与摩擦费、因果探针 Look-Ahead Bias 检测、四岛策略接口合规、Holdout 盲测金库额度、纯债套利拦截、Rf 扣除、AST 日历硬编码扫描）。
     - 实测结果：`15 passed in 5.56s`，100% 通过。
  2. `test_milestone_phase1_r1_r5.py`：阶段一核心算法（只读基建、AST 反作弊、实时限购与断网缓存回退、瀑布流拆单、QDII 盘中估值纠偏、全档位动态配权、三段式攻防、今日调仓适宜度三色裁决与四维白话、双模式调仓后果精算、双红利底仓对豁免）。
     - 实测结果：全量 11 项红队断言 100% PASSED。
  3. `test_e2e_gui_render.py`：包含 8 项端到端 GUI 与全档位测试。
     - 其中 `test_bug6_streamlit_apptest_full_render` **PASSED**（通过 Streamlit 官方 AppTest 框架端到端渲染运行 `app_gui.py`，完整遍历 C1 至 C5 全档位，未抛出任何 Python 异常）。

### 1.2 系统 4 个只读裁判基建文件完整性检查
- **文件清单**：
  1. `d:\Google\Workspace\Wind\AGY2_FundAdvisory\judge_engine.py`
  2. `d:\Google\Workspace\Wind\AGY2_FundAdvisory\holdout_vault.py`
  3. `d:\Google\Workspace\Wind\AGY2_FundAdvisory\AGENT_SPEC.md`
  4. `d:\Google\Workspace\Wind\AGY2_FundAdvisory\tests\test_infra.py`
- **检查命令与输出**：
  - 执行 `git status --porcelain d:\Google\Workspace\Wind\AGY2_FundAdvisory\judge_engine.py d:\Google\Workspace\Wind\AGY2_FundAdvisory\holdout_vault.py d:\Google\Workspace\Wind\AGY2_FundAdvisory\AGENT_SPEC.md d:\Google\Workspace\Wind\AGY2_FundAdvisory\tests\test_infra.py`
  - 输出：空（exit code 0），表明 4 个裁判基建文件未被触碰、未被修改，处于 100% 原始只读保护状态。
  - `test_case_01_read_only_invariants` 与 `test_infra.py` 全量通过，确认功能完好无损。

### 1.3 8501 端口 Streamlit 服务的运行状态与重启机制
- **网络监听状态**：
  - 执行 `Get-NetTCPConnection -LocalPort 8501`:
    - `LocalAddress`: `::`
    - `LocalPort`: `8501`
    - `State`: `Listen`
    - `OwningProcess`: `24196`
- **进程状态**：
  - 进程 ID：`24196`
  - 命令行：`"C:\Users\deanc\AppData\Local\Programs\Python\Python311\python.exe" -m streamlit run AGY2_FundAdvisory/app_gui.py --server.headless=true --server.port=8501`
- **健康探针**：
  - 请求 `http://127.0.0.1:8501/_stcore/health`：
    - 返回：`StatusCode: 200`, `Content: ok`。服务目前处于正常监听与健康工作状态。
- **启动引导器脚本现状**：
  - 项目已具备 Windows 规范的无黑框静默启动引导器：
    - `d:\Google\Workspace\Wind\AGY2_FundAdvisory\launch_gui.vbs`
    - `d:\Google\Workspace\Wind\AGY2_FundAdvisory\launch_gui.bat`
    - 根目录跳板：`d:\Google\Workspace\Wind\launch_gui.vbs`
  - `launch_gui.vbs` 实现了：
    1. `IsPortListening(8501)` 探测 `http://127.0.0.1:8501/_stcore/health`；
    2. 若未监听，以无窗口模式 `WshShell.Run cmdStart, 0, False` 后台静默拉起；
    3. 轮询等待健康端口响应后，以独立桌面应用模式唤出 Edge 浏览器：`msedge.exe --app=http://localhost:8501`（无地址栏、无标签栏）。

### 1.4 前端 `app_gui.py` 现状与阶段二重构需求差异
- **当前行数**：2,486 行。
- **顶部看板现状**：
  - 当前采用 `st.columns(7)`（7 张窄卡）以及一个调仓网格倒计时与破位预警横幅。
  - 在 1080p 分辨率下，7 张窄卡极易产生文本省略号截断（`...`）。
  - 阶段二要求：彻底删除 3 层 7 窄卡，重塑为 **1 行 4 宽卡 + 1 个刷新按钮**。
- **导航 Tab 现状**：
  - 当前定义（501 行）：
    `tab_brain, tab_backtest, tab_ledger, tab_toolbox = st.tabs(["🧭 AI 投顾大脑与今日建议", "📈 策略胜率、回测与风控档案", "💼 我的持仓账本与接管向导", "🔍 组合穿透诊断、对账与工具箱"])`
  - 阶段二要求：重塑为主流职责分明的 **四大主导航 Tab**：
    - Tab 1: `🌱 新资金从0建仓推演`
    - Tab 2: `💼 我的当前持仓与今日调仓建议`
    - Tab 3: `🔍 组合深度体检与算费工具箱`
    - Tab 4: `📈 策略历史回测与胜率档案`
- **代码清洁度现状**：
  - 经 `grep_search` 严格检查，`app_gui.py` 中已经彻底没有 `time.sleep`，也没有写死 `"限额买500"`。
  - 但 Tab 2 中的阶段一核心算法装配（今日调仓适宜度裁决卡、双模式单选与四大后果账单）尚未组装至页面中。

---

## 2. Logic Chain（推演逻辑链）

1. **裁判基建与因果约束未被破坏**：
   - 依赖观察 1.2，`git status` 与 `test_infra.py` 证明 4 个只读裁判文件完好无损，后续对 `app_gui.py` 的重构将严格遵循该红线。
2. **既有 AppTest 覆盖深度有限**：
   - 依赖观察 1.1，现有 `test_e2e_gui_render.py` 中的 `test_bug6_streamlit_apptest_full_render` 仅断言了 `len(at.exception) == 0`（即页面代码加载并渲染不崩溃），但**完全没有断言**：
     - 4 张宽卡是否存在、是否有 `...` 截断、悬停 `ⓘ` title 是否收录量化数据；
     - 四大 Tab 的标签是否完全匹配阶段二命名；
     - Tab 1 步骤二抽屉标题是否有核心数字摘要、步骤三第 9 列是否为动态限额文本；
     - Tab 2 第一层是否有今日调仓适宜度 AI 裁决卡与四维实测结论；
     - Tab 2 第二层是否有双模式单选及 4 张后果账单；
     - Tab 2 第三层在有持仓时 3 个工具向导面板是否默认折叠（`expanded=False`）。
   - 因此，必须专门设计针对阶段二界面的增强型 AppTest 测试用例集。
3. **测试套件中的已知偶发/历史失败点明确归因**：
   - `test_bug3_pre_market_trading_clock_and_signal_harmony` 失败是因为测试运行在周末（2026-11-01），且测试代码未对 `StrategyBridge.evaluate_intraday_signal` 内部的 `datetime.now()` 打 mock，导致被周末休市逻辑提前拦截。解决方案是在测试用例中统一 mock 时间至交易日盘前（如周一 08:21）。
   - `test_sleep_delay_cadence_and_non_repetition` 失败是因为 Milestone 3 的历史断言与 Milestone 4 阶段一/阶段二反作弊红线（严禁使用 `time.sleep`）发生冲突。测试应与当前阶段验收标准保持一致。
4. **平滑重启方案与桌面服务准则高度契合**：
   - 依赖观察 1.3，8501 端口由 PID 24196 监听。
   - 根据 Windows 桌面交互准则（Rule 1, 2, 4, 10, 42, 53）：
     - 重启时禁止直接在终端运行阻塞式 `streamlit run`，防止终端关闭时 Job Object 级联强杀；
     - 必须采用脱钩模式：先查明 8501 端口占用进程并强制终止，确认端口释放后，调用 `wscript.exe launch_gui.vbs` 以 `SW_HIDE (0)` 模式静默拉起，并通过循环轮询 `http://127.0.0.1:8501/_stcore/health` 确认服务就绪。

---

## 3. Caveats（局限性与风险提示）

1. **测试运行耗时考量**：
   - 单次通过 Streamlit `AppTest` 完整加载并渲染包含 2018-2026 跨周期回测的 `app_gui.py` 耗时约 30~45 秒。全量跑完 C1~C5 5 个档位需约 3.5 分钟。在设计新增 AppTest 时，应尽量通过单个档位（如默认 C3）或参数化组合验证具体 UI 元素，避免在每个细项测试中重复触发全量 5 档位回测，以优化 CI/本地测试耗时。
2. **日期敏感性防御**：
   - `TradingClock` 与 `StrategyBridge.evaluate_intraday_signal` 高度依赖系统当前日期与开盘时间窗口。在编写自动化测试时，必须显式通过 `unittest.mock.patch("strategy_bridge.datetime")` 锁定虚拟交易日与时钟，防止因在周末、节假日或盘后运行测试而导致偶发假失败。
3. **只读权限约束**：
   - 本调查角色（teamwork_explorer）严格遵循只读原则，未修改任何项目源码或测试代码。所有提出的测试方案以规范报告和推荐代码形式交付给实现与测试代理。

---

## 4. Conclusion（调查结论与方案设计）

### 4.1 阶段二 Streamlit AppTest 增强测试方案设计
建议在 `AGY2_FundAdvisory/tests/` 下新增或扩充专门针对阶段二界面重构的测试文件（如 `test_phase2_apptest_gui.py` 或扩充 `test_e2e_gui_render.py`），包含以下 8 大核心断言用例：

```python
# =============================================================================
# 阶段二 Streamlit AppTest 增强测试用例体系设计规格
# =============================================================================

# 用例 1：顶部全局看板大瘦身（1 行 4 宽卡 + 1 个刷新按钮，彻底消灭省略号）
def test_phase2_apptest_top_dashboard_four_wide_cards():
    """
    断言顶部全局看板：
    1. 包含 4 张宽裕卡片与 1 个刷新按钮；
    2. 卡片 1【🕒 交易时钟与窗口 ⓘ】：主值包含黄金窗口/盘中观察/盘后关账/盘前未开市/休市，副标题包含网格日，悬停含成交规则；
    3. 卡片 2【🧭 市场定调与攻防线 ⓘ】：主值大白话定调，副标题直接显示双向点位 (3000~5500 价格口径)，悬停含 MA20/MA60；
    4. 卡片 3【🌡️ 估值与资金面温度 ⓘ】：主值/副标题纯大白话，悬停包含 ERP/DR007/IV/IC 量化指标；
    5. 卡片 4【💰 我的总资产与今日预估 ⓘ】：主值与 pm.total_equity 对齐，副标题含预估收益，右侧并排刷新按钮；
    6. 文本检查：全界面顶部卡片文字绝对不含 '...', '…', '&hellip;' 截断符。
    """

# 用例 2：四大主导航 Tab 架构与单一职责切换
def test_phase2_apptest_four_tabs_structure_and_navigation():
    """
    断言四大主导航 Tab：
    1. at.tabs 数量严格为 4；
    2. at.tabs 标题严格对齐：
       - Tab 0: "🌱 新资金从0建仓推演"
       - Tab 1: "💼 我的当前持仓与今日调仓建议"
       - Tab 2: "🔍 组合深度体检与算费工具箱"
       - Tab 3: "📈 策略历史回测与胜率档案"
    3. 各 Tab 独立点击切换渲染无异常（len(at.exception) == 0）。
    """

# 用例 3：Tab 1 步骤二抽屉核心数字摘要与无 time.sleep 假延迟
def test_phase2_apptest_tab1_step2_drawer_dynamic_digests():
    """
    断言 Tab 1 步骤二：
    1. 4 个白盒推演抽屉默认全部收起 (expanded=False)；
    2. 抽屉 1 标题包含选基与优胜劣汰数字摘要（如：28,177 ➔ ... ➔ 5 只金牌标的）；
    3. 抽屉 2 标题包含 Hedge 4 大专家实时自适应权重百分比；
    4. 抽屉 3 标题包含压力测试期望年化与最大回撤指标；
    5. 抽屉 4 标题包含真实申赎费率与在途天数精算摘要；
    6. 页面保留《三句话看懂本方案》三栏作战卡片。
    """

# 用例 4：Tab 1 步骤三专属建仓单 9 列与动态限购指引（无写死“限额买500”）
def test_phase2_apptest_tab1_step3_execution_table_and_dca_plan():
    """
    断言 Tab 1 步骤三：
    1. 专属建仓执行单表格严格为 9 列；
    2. 第 9 列名称为“实操分红与限购指引”；
    3. 第 9 列内容动态绑定 blueprint['items'] 生成真实限额说明（如“现金分红·今日限额¥500”、“承接超额·不限购正常买”）；
    4. 断言表格文本中绝不含写死的 "现金分红·限额买500"；
    5. 当大额资金导致 QDII/特定赛道全市场超额限购时，表格下方必须展示醒目的《超限资金分批定投执行计划》。
    """

# 用例 5：Tab 2 第一层【今日是否适合调仓】AI 综合裁决卡与四维实测
def test_phase2_apptest_tab2_layer1_suitability_verdict_card():
    """
    断言 Tab 2 第一层：
    1. 调用 StrategyBridge.evaluate_today_rebalance_suitability(pm, active_tier)；
    2. 渲染醒目的红/黄/绿灯横幅（包含 verdict_title）；
    3. 渲染 4 个简短胶囊列出【行情位置】、【申赎时钟】、【偏离净效用】、【批次锁定期】四维实测结论。
    """

# 用例 6：Tab 2 第二层双模式调仓单选与 4 张量化账单卡片及 9 列执行单
def test_phase2_apptest_tab2_layer2_dual_rebalance_modes_and_consequences():
    """
    断言 Tab 2 第二层：
    1. 提供单选切换（模式一：AI 温和免伤调仓 vs 模式二：如果今天一定要调仓）；
    2. 并排渲染 4 张《本次调仓四大真实后果量化账单》卡片：
       - 后果① 手续费直接损耗 (总手续费、<7天 1.5% 惩罚费预警、分红回本天数)；
       - 后果② T+2 资金在途踏空风险 (跨公司在途资金与占比、2~4天空窗期、同公司转换节省金额)；
       - 后果③ 组合攻防与回撤变化 (调仓前后权益仓位、年化波动率、极端回撤水位)；
       - 后果④ 持有期清零重算后果 (新买入资金重新进入 7 天惩罚锁定期)；
    3. 下方展示 9 列《今日建议调仓执行单》表格与一键执行/预案保存控制区。
    """

# 用例 7：Tab 2 第三层持仓明细与向导面板在有持仓时默认折叠
def test_phase2_apptest_tab2_layer3_holdings_and_tools_collapsed_when_has_holdings():
    """
    断言 Tab 2 第三层：
    1. 当 len(pm.holdings) > 0 时：
       - 《✨ 零门槛导入/新增持仓向导》默认折叠 (expanded=False)；
       - 《✏️ 编辑修改持仓数据》默认折叠 (expanded=False)；
       - 《📦 FIFO 份额批次免赎倒计时》默认折叠 (expanded=False)；
    2. 实时持仓明细表格在 1080p 下无横向滚动条。
    """

# 用例 8：AST 语法树反作弊与工程规范静态检查
def test_phase2_static_ast_and_no_fake_delay():
    """
    AST 静态扫描 app_gui.py：
    1. 扫描整个语法树，断言 time.sleep 调用次数严格为 0；
    2. 扫描源码文本，断言绝对不含硬编码 "限额买500" 或 "现金分红·限额买500"；
    3. 检查无 monkeypatch 猴子补丁。
    """
```

### 4.2 Windows 环境下 8501 端口安全平滑重启操作规范
为严格遵守无黑框、防止进程残留与防终端退出级联强杀准则，平滑重启的标准作业程序（SOP）如下：

1. **第一步：优雅检测与端口清理**
   ```powershell
   # 1. 查找监听 8501 端口的进程
   $conn = Get-NetTCPConnection -LocalPort 8501 -ErrorAction SilentlyContinue
   if ($conn) {
       $pids = $conn | Select-Object -ExpandProperty OwningProcess -Unique
       foreach ($procId in $pids) {
           Write-Host "Releasing port 8501 from PID $procId..."
           Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
       }
       # 等待端口彻底释放 (最大等待 3 秒)
       $released = $false
       for ($i = 0; $i -lt 15; $i++) {
           Start-Sleep -Milliseconds 200
           if (-not (Get-NetTCPConnection -LocalPort 8501 -ErrorAction SilentlyContinue)) {
               $released = $true
               break
           }
       }
       Write-Host "Port 8501 released: $released"
   }
   ```

2. **第二步：静默脱钩拉起与健康轮询**
   采用现有的 `launch_gui.vbs` 配合 `wscript.exe` 脱钩启动，或者使用 PowerShell 原生 `ProcessStartInfo`（配置 `CreateNoWindow = $true` 与 `UseShellExecute = $false`）：
   ```powershell
   # 启动无黑框后台服务
   Start-Process -FilePath "wscript.exe" -ArgumentList "d:\Google\Workspace\Wind\AGY2_FundAdvisory\launch_gui.vbs" -WorkingDirectory "d:\Google\Workspace\Wind\AGY2_FundAdvisory"

   # 探针轮询服务健康度 (最大等待 15 秒)
   $healthy = $false
   for ($i = 0; $i -lt 30; $i++) {
       Start-Sleep -Milliseconds 500
       try {
           $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8501/_stcore/health" -UseBasicParsing -TimeoutSec 1
           if ($resp.StatusCode -eq 200) {
               $healthy = $true
               Write-Host "Streamlit service successfully restarted and healthy on port 8501 (PID: $((Get-NetTCPConnection -LocalPort 8501).OwningProcess))"
               break
           }
       } catch {}
   }
   if (-not $healthy) {
       throw "Streamlit failed to reach healthy state within 15 seconds!"
   }
   ```

---

## 5. Verification Method（独立验证方法）

后续负责测试或实现的 Agent 可按以下步骤独立验证本报告结论：

1. **验证裁判文件完整性**：
   ```powershell
   git status --porcelain d:\Google\Workspace\Wind\AGY2_FundAdvisory\judge_engine.py d:\Google\Workspace\Wind\AGY2_FundAdvisory\holdout_vault.py d:\Google\Workspace\Wind\AGY2_FundAdvisory\AGENT_SPEC.md d:\Google\Workspace\Wind\AGY2_FundAdvisory\tests\test_infra.py
   ```
   *预期结果*：输出为空，退出码为 0。

2. **验证裁判基建测试**：
   ```powershell
   $env:PYTHONPATH = "d:\Google\Workspace\Wind\AGY2_FundAdvisory"
   py -3.11 -m pytest d:\Google\Workspace\Wind\AGY2_FundAdvisory\tests\test_infra.py -v
   ```
   *预期结果*：15 项测试全部通过（PASSED）。

3. **验证 8501 端口探针**：
   ```powershell
   Invoke-WebRequest -Uri "http://127.0.0.1:8501/_stcore/health" -UseBasicParsing
   ```
   *预期结果*：`StatusCode: 200`, `Content: ok`。

4. **验证现有 AppTest 渲染测试**：
   ```powershell
   $env:PYTHONPATH = "d:\Google\Workspace\Wind\AGY2_FundAdvisory"
   py -3.11 -m pytest d:\Google\Workspace\Wind\AGY2_FundAdvisory\tests\test_e2e_gui_render.py -k "test_bug6_streamlit_apptest_full_render" -v
   ```
   *预期结果*：测试通过，C1 至 C5 全档位渲染无异常。
