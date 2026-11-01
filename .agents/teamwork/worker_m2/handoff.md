# Milestone 2 交付报告 (Handoff Report)

## 1. Observation
- **裁判与基建文件只读红线检查**：
  未修改、未触碰只读裁判基建文件：`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py` 均处于原始状态，哈希完全一致。
- **新建 AppTest 测试套件**：
  在 `AGY2_FundAdvisory/tests/test_phase2_apptest_gui.py` 中完整实现了阶段二重构的 8 大断言用例：
  1. `test_phase2_apptest_top_dashboard_four_wide_cards`：验证顶部 1 行 4 宽卡 + 1 紧凑刷新按钮、主副标题、`ⓘ` 悬停提示完整、无 `...` 截断符；
  2. `test_phase2_apptest_four_tabs_structure_and_navigation`：验证四大主导航 Tab 标题严格对齐且独立切换渲染无异常；
  3. `test_phase2_apptest_tab1_step2_drawer_dynamic_digests`：验证 Tab 1 步骤二 4 白盒抽屉全部默认收起（`expanded=False`）且标题含动态数字摘要，保留 5 张结果卡与《三句话看懂本方案》；
  4. `test_phase2_apptest_tab1_step3_execution_table_and_dca_plan`：验证步骤三 9 列精简表格保留 `cols_9`，第 9 列动态绑定真实 `action_guide`，绝对无写死“限额买500”，大额超限场景展示《超限资金分批定投执行计划》；
  5. `test_phase2_apptest_tab2_layer1_suitability_verdict_card`：验证 Tab 2 第一层调用 `evaluate_today_rebalance_suitability` 渲染三色横幅与四维胶囊；
  6. `test_phase2_apptest_tab2_layer2_dual_rebalance_modes_and_consequences`：验证 Tab 2 第二层单选切换温和与强行模式，渲染 4 张量化后果账单卡片与 9 列执行单；
  7. `test_phase2_apptest_tab2_layer3_holdings_and_tools_collapsed_when_has_holdings`：验证 Tab 2 第三层有持仓时 3 个工具面板默认折叠收起；
  8. `test_phase2_static_ast_and_no_fake_delay`：AST 语法树扫描，验证 0 处 sleep、0 处假延时、0 处硬编码 500、0 处 monkeypatch。
  单测运行结果：`8 passed in 84.31s`。
- **历史测试失败点诊断与修复**：
  1. `tests/test_e2e_gui_render.py` 行 115 `test_bug3_pre_market_trading_clock_and_signal_harmony`：修复周末运行休市逻辑导致的假失败，增加 `patch("strategy_bridge.datetime")` mock 为交易日周一早间 `dt_821`（2026-10-26 08:21）；
  2. `tests/test_e2e_gui_render.py` 行 220 `test_bug6_streamlit_apptest_full_render`：AppTest 单次冷启动耗时接近 45s，5 次循环导致 `RuntimeError: AppTest script run timed out after 45(s)`。重构为复用 `at` 实例并设置 `default_timeout=120`，测试验证通过；
  3. `tests/test_adversarial_m3_challenger2.py`：对齐阶段二标准，移除旧有 sleep 预期断言改为断言 0 处 sleep；更新 AST 解析支持 `ast.JoinedStr`；断言 4 宽卡 + 1 刷新按钮；
  4. `tests/test_architecture_m3.py` 行 400 `test_gui_step3_table_9_cols_and_no_truncation`：精准定位 9 列建仓单（匹配包含 `"精确买入金额(元)"` 与 `"实操分红与限购指引"`），避免误匹配持仓表格；同时调整 `default_timeout=120` 避免全量回测冷启动超时；
  5. `tests/test_ui_and_logic_refinements.py`：对齐阶段二组件文案与 widget key（`tier_determination_mode` 与 `🕒 交易时钟与窗口`）。
- **全量 pytest 套件运行结果**：
  执行命令：`cd AGY2_FundAdvisory; py -3.11 -m pytest tests -c none -q`
  输出结果：`589 passed, 1547 warnings in 1160.59s (0:19:20)`，退出码 `0`，通过率 100%。
- **8501 端口服务平滑重启与健康探针**：
  - 端口清理与脱钩托管：检查 8501 端口并以常驻守护模式启动，禁留可见终端黑框（cmd/powershell 控制台）；
  - 进程信息：PID `41764`，状态 `Listen`，本地端口 `8501`；
  - 健康探针轮询响应：
    - `http://127.0.0.1:8501/_stcore/health` 响应：`Status Code: 200`, `Response: ok`；
    - `http://127.0.0.1:8501/` 根路径响应：`Root HTTP Status: 200`, `HTML length: 6467` 字节。

---

## 2. Logic Chain
1. **阶段二重构与测试规格对齐**：
   `worker_m1_gen2` 完成了 `app_gui.py` 4 导航 Tab、顶部 1 行 4 宽卡 + 1 刷新按钮、步骤二 4 抽屉收起与步骤三 9 列精简表格的重构。`survey_3/handoff.md` 规划的 8 大断言用例针对上述规格设计。`test_phase2_apptest_gui.py` 使用 Streamlit AppTest 真实加载并断言元素树，结合 AST 静态扫描确认代码中无假延时和死锁。
2. **偶发失败根因与修复推导**：
   - 周末运行 `test_e2e_gui_render.py` 时，`evaluate_intraday_signal` 真实检测当前系统时间为周日休市，导致预期盘前交易窗口的断言假失败。通过 `unittest.mock.patch` 固定交易日早间时间戳彻底隔离真实环境时间干扰；
   - AppTest 框架冷启动需加载跨牛熊 2,000+ 交易日数据，在单核或多测并发下耗时约 40~65s。历史测试中配置的 45s/60s 超时阈值过窄，提升至 120s 并在档位切换时复用已初始化的 AppTest 实例，大幅提升了测试稳定性和执行效率；
   - 步骤三表格断言失败系由于历史测试用 `if "基金代码" in cols and ("精确买入金额(元)" in cols or "目标占比(%)" in cols)` 匹配表格，而持仓表格恰好包含 `目标占比(%)`，导致先行匹配错误表格。改用严格双关键列交集后完全消除歧义。
3. **服务守护合规性**：
   遵循 Windows 桌面交互准则（Rule 1, 2, 4, 10, 42, 53），以无窗口脱钩方式运行，消除黑框残留，并通过 `/_stcore/health` 探针确认就绪，实现了服务热重启。

---

## 3. Caveats
- `InsecureRequestWarning` 警告（1547 条）：系由于抓取天天基金或东方财富盘中实时估值接口时未校验 SSL 证书，属于量化爬虫基建已知警告，不影响任何业务逻辑与单测判定。
- Streamlit 元素树渲染时间：全量套件运行（589 项）耗时约 19 分钟，因包含多个跨牛熊回测的大型 AppTest，单次全量回归建议预留充足超时。

---

## 4. Conclusion
Milestone 2 核心交付任务全部高质量完成：
1. `AGY2_FundAdvisory/tests/test_phase2_apptest_gui.py` 8 大测试用例全部落地并通过；
2. 历史陈旧与偶发测试用例全部修复对齐；
3. 全量测试套件 589 项测试 **100% PASS**（589 passed, 0 failed, 退出码 0）；
4. 8501 端口 Streamlit 工作台平滑重启完成，PID 41764 监听正常，`/_stcore/health` 响应 HTTP 200 OK，界面渲染完整无黑框。

---

## 5. Verification Method
1. **独立复验阶段二 AppTest 套件**：
   ```powershell
   cd AGY2_FundAdvisory
   py -3.11 -m pytest tests/test_phase2_apptest_gui.py -c none -v
   ```
   *预期结果*：8 passed in ~85s。
2. **独立复验全量测试套件**：
   ```powershell
   cd AGY2_FundAdvisory
   py -3.11 -m pytest tests -c none -q
   ```
   *预期结果*：589 passed, 0 failed。
3. **独立复验 8501 服务与健康探针**：
   ```powershell
   Get-NetTCPConnection -LocalPort 8501 | Select-Object LocalAddress, LocalPort, State, OwningProcess
   py -3.11 -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health').read().decode())"
   ```
   *预期结果*：状态为 `Listen`，PID 为 `41764`，输出 `ok`。
