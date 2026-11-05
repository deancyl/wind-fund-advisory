# Handoff Report — Explorer 3 (survey_r6_3)

**Working Directory**: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r6_3\`  
**Target Recipient**: Orchestrator (`4b9235fc-5501-4c70-bc98-8ac4f7ce5f18`)  
**Mission Role**: Explorer 3 (R4, R5, Test Baselines, Delta Test Design, Referee Audit, Safe Service Restart)  

---

## 1. Observation (直观观测事实)

1. **测试框架配置与执行命令**：
   - 文件 `pyproject.toml` (第 26-30 行) 声明：
     ```toml
     [tool.pytest.ini_options]
     testpaths = ["tests"]
     python_files = ["test_*.py"]
     python_classes = ["Test*"]
     python_functions = ["test_*"]
     ```
   - 既有测试基线执行命令：`py -3 -m pytest AGY2_FundAdvisory/tests/test_deep_remodel_final.py -v`。
   - 实际运行结果：7 项测试全部通过（`test_quant_models_weight_differentiation`, `test_blueprint_cash_conservation_and_percentage_closure`, `test_winrate_dual_gauge_and_sample_capacity`, `test_core_indices_csi_dividend_accuracy`, `test_ui_cleanliness_and_title_length`, `test_apptest_gui_headless_execution`, `test_ui_geometry_and_non_overlap_invariants`），耗时 81.73 秒。
   - 另一套核心测试 `AGY2_FundAdvisory/tests/test_tab_boundaries_and_rebalance.py` 运行结果：5 项全部通过（耗时 47.79 秒），证实 Tab 顶层 try-except 隔离、AppTest 0 异常与签名弹性。

2. **当前业务代码现状观测**：
   - **攻防红线点位不一致（R1 瑕疵）**：
     在 `AGY2_FundAdvisory/app_gui.py:625-626` 侧边栏中硬编码计算：
     ```python
     _c300 = snapshot.get('c300_price', 4053.0)
     st.write(f"**攻防红线**：破 `{_c300*1.012:,.0f}` 进攻 ｜ 跌 `{_c300*0.985:,.0f}` 防守")
     ```
     而主看板顶部卡片（第 677-679 行）读取自策略快照：
     ```python
     trigger_lines = snapshot.get("trigger_lines") or {}
     surge_line = float(trigger_lines.get("surge_line", snapshot.get("surge_line", c300_disp * 1.012)))
     breakdown_line = float(trigger_lines.get("breakdown_line", snapshot.get("breakdown_line", c300_disp * 0.985)))
     ```
   - **指数药丸样式层级偏小（R1 瑕疵）**：
     在 `AGY2_FundAdvisory/app_gui.py:352-381`：
     `.index-pill-name { font-size: 12px; }`，`.index-pill-point { font-size: 13px; }`，`.index-pill-chg-* { font-size: 11px; }`。低于 R1 要求的 15~16px 与 13px。
   - **调仓缓冲带硬编码（R2 需重构）**：
     在 `AGY2_FundAdvisory/app_gui.py:2340, 2357`：
     `min_buffer_pct=(0.0 if sel_mode_key == "mode_forced" else 3.0)`，硬编码 3.0，未支持侧边栏滑块传参。
   - **单日限购过滤缺失同赛道替换（R2 需重构）**：
     在 `AGY2_FundAdvisory/portfolio_manager.py:3380-3445` 中，当金额超过限额时仅执行限购拆单（primary fund + alternative 溢出），未提供当用户选择“过滤日限额 < ¥1,000 / < ¥5,000”时直接由备选基金（如 `001071`）全额替换限购标的（`050025`）的过滤模式。
   - **持仓表格市值锁定与列冗余（R3 需重构）**：
     在 `AGY2_FundAdvisory/app_gui.py:1874`：
     `disabled=["当前市值(元)", "持仓占比(%)", ...]` 锁定了当前市值不可编辑；保存时（第 1888-1895 行）仅读取 `持仓份额`，未做“修改市值反算份额”；且 `export_snapshot_df()` 输出了 19 列，超出 10 列人体工学阈值。

3. **4 大裁判基建文件绝对路径与 SHA256 初始哈希**：
   通过 PowerShell `Get-FileHash -Algorithm SHA256` 测算：
   - `D:\Google\Workspace\Wind\AGY2_FundAdvisory\judge_engine.py`:
     `76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF31CC07BE`
   - `D:\Google\Workspace\Wind\AGY2_FundAdvisory\holdout_vault.py`:
     `88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670BD031D2A`
   - `D:\Google\Workspace\Wind\AGY2_FundAdvisory\AGENT_SPEC.md`:
     `A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B800CD63957`
   - `D:\Google\Workspace\Wind\AGY2_FundAdvisory\tests\test_infra.py`:
     `B8D781BE8135BE05CF61E62E4B534E359985AD880F27FFB61228A33DF6B02A6A`
   - `D:\Google\Workspace\Wind\tests\test_infra.py`:
     `48BEE0DA300D7C0A0848EC1376E4B9B2E55224D2736081713B4340F0362CD100`

4. **8501 端口服务托管与探针机制**：
   - `AGY2_FundAdvisory/start_silent_service.vbs` 与 `launch_gui.vbs` 采用 Windows 原生 VBScript `WshShell.Run cmdStart, 0, False` 实现脱钩无窗口后台常驻托管。
   - Streamlit 原生提供 `http://127.0.0.1:8501/_stcore/health` 探针，返回 HTTP 200 与 `ok`。
   - 当前 8501 端口未处于监听状态，未发生端口碰撞。

---

## 2. Logic Chain (推导逻辑链条)

1. **测试剪枝与交付提效推理**：
   - 观测 1 显示全量运行 `test_deep_remodel_final.py` 需 81.7 秒，`test_tab_boundaries_and_rebalance.py` 需 47.8 秒。若盲目重跑全库数十个测试将耗时数十分钟。
   - 根据 GEMINI.md Rule 6 与 user_global Rule 13，必须落实“三阶轻量核验”：专职增量针对性测试 (Delta Test) + 关键红线扫描 + 服务存活探针，由新建的 `test_delta_remodel_r6.py` 承接本次 R1~R3 的新特性验收。

2. **Delta 增量测试用例设计推理**：
   - 根据观测 2，限购过滤阈值影响建仓单中的标的选取。因此用例必须覆盖：阈值=0 (保留 050025 并拆单) vs 阈值=1000 (自动由备选 001071/017436 替换 050025)，并断言平账分厘不差。
   - 根据观测 2，调仓缓冲带目前硬编码 3.0。若侧边栏调节为 2.0% 或 4.0%，对处于 2.5% 偏离度的标的裁决会从 `HOLD` 翻转为 `SELL`。因此设计两组偏离度边界用例断言其准确传递。
   - 根据观测 2，表格解除 disabled 后，若用户输入新市值 15000，当前净值 1.25，后台必须将份额反算为 12000，且修改份额时反向更新市值。列数从 19 列浓缩至 <= 10 列。
   - 结合观测 1 的 AppTest 规范，必须编写端到端无头执行测试，遍历 4 个 Tab 断言 `len(at.exception) == 0`。

3. **物理安全审计基线确立推理**：
   - 根据观测 3，已全量固化 4 大裁判文件的绝对路径与 SHA256 哈希。任何 Worker 在实施 R1~R3 代码改动时，只要该 4 文件哈希发生变化，立即判定为违规，实现司法级安全审计。

4. **平滑重启方案推理**：
   - 结合观测 4 与 GEMINI.md Rule 12，重启 Streamlit 前必须先用 `netstat -ano | findstr 8501` 甄别是 `LISTENING` 还是 `ESTABLISHED`；若为 LISTENING 则精准根据 PID 关闭旧服务，再通过 `start_silent_service.vbs` 原生无窗口拉起，最后通过 `/_stcore/health` 探针轮询确认 HTTP 200，杜绝终端黑框与端口碰撞崩溃。

---

## 3. Caveats (审计边界与局限说明)

1. **网络与缓存环境**：测试用例在拉取天天基金或东方财富行情时可能产生 InsecureRequestWarning，但不影响测试通过；断网环境下依赖本地 L3 Parquet 湖仓与 SQLite 兜底。
2. **AppTest 内存消耗**：Streamlit AppTest 在同一 Python 进程中多次连续运行可能占用较多内存，推荐每次以独立子进程执行（`py -3 -m pytest <test_file>`）。
3. **只读约束**：本 Explorer 严格遵循只读约束，未对任何项目源文件和裁判文件进行修改。

---

## 4. Conclusion (调研结论)

1. **测试基线完好**：现有基线测试 100% 绿灯，系统核心模型、平账、胜率与 UI 不变量稳固。
2. **Delta Test 规范就绪**：为 Worker 和 Reviewer 提供了包含 4 大模块的具体测试用例代码模板与断言设计，可直接作为 `AGY2_FundAdvisory/tests/test_delta_remodel_r6.py` 的实现指导。
3. **裁判哈希锚定**：5 处物理文件 SHA256 哈希已固化入档，任何修改将被审计即刻拦截。
4. **运维 SOP 闭环**：确立了基于非破坏性探针 + VBScript 静默常驻 + `/_stcore/health` HTTP 200 的平滑重启方案。

---

## 5. Verification Method (独立复核与验证方法)

1. **既有测试基线验证命令**：
   ```powershell
   py -3 -m pytest AGY2_FundAdvisory/tests/test_deep_remodel_final.py -v
   ```
   *预期结果*：7 passed in ~80s。

2. **裁判文件哈希基线复核命令**：
   ```powershell
   powershell -NoProfile -Command "Get-FileHash -Path 'AGY2_FundAdvisory\judge_engine.py', 'AGY2_FundAdvisory\holdout_vault.py', 'AGY2_FundAdvisory\AGENT_SPEC.md', 'AGY2_FundAdvisory\tests\test_infra.py', 'tests\test_infra.py' -Algorithm SHA256 | Select-Object Hash, Path | Format-List"
   ```
   *预期结果*：哈希值与第 3 节表格完全一致。

3. **调研报告产物审查**：
   检查 `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r6_3\survey_report.md`。
