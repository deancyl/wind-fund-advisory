# Orchestrator Soft Handoff — orchestrator_18 to Successor (orchestrator_19)

- **Generation**: G15 Generation Project Orchestrator (gen0 -> gen1)
- **Predecessor**: `orchestrator_17`
- **Current Orchestrator**: `orchestrator_18`
- **Original Parent**: `30ed7372-8052-4cae-b2d2-ff77f2af8c6e` (Parent passthrough: Successor must report to this ID)
- **Timestamp**: 2026-11-09T18:28:30Z
- **Type**: Soft Handoff (Succession Triggered: cumulative spawn count = 17 >= 16, all 17 subagents completed)

---

## 1. Milestone State

| # | Name | Scope | Dependencies | Status | Output / Gate Result |
|---|------|-------|-------------|--------|---------------------|
| M0 | 全景勘探 (Survey Phase) | 3 大勘探探针并行覆盖 M1/M2/M3 | none | DONE | 3 份详尽方案与代码蓝图落盘 |
| M1 | 根治 5 处 UI/UX 缺陷与代码对齐 Bug，砍除 3D 曲面图与 RuleTree 代码框 | 3D图替换为2D危机表、Sentry红黄牌修复、Tab 2表头汉化与按钮收纳、Tab 4单行导航与017436归一、手机极简盯盘视图 | none | DONE | Gate 1 PASS (33 项测试全绿，2 Reviewers APPROVE, 2 Challengers APPROVE, Forensic Auditor CLEAN) |
| M2 | 实装五维全息投顾首席备忘录与历史任意时点盲测时光机验证器 | generate_chief_advisor_memo 算子、render_chief_advisor_memo_card 首屏与 Tab 1 顶部双向挂载、run_historical_time_machine_backtest (Point-in-Time 零未来数据切片 + 全额公募扣费)、Tab 3 顶部时光机模块 | M1 | DONE | Gate 2 PASS (65+ 项测试全绿，2 Reviewers APPROVE, 2 Challengers APPROVE, Forensic Auditor CLEAN) |
| M3 | 实装手机长截图高清切片识别导入、碎片尾仓免赎清理器与 29 基真实存量账本 | slice_long_screenshot_for_ocr 100% 原始宽度高清切片、本地 RapidOCR、Tab 2 截图导入交互弹窗、ActiveRiskSentry 碎片清理第 13 维、MultiLedgerManager 预置 combat_29_funds (¥26,615.10) 实战体检 | M1, M2 | PLANNED | 方案与原型已在 `explorer_g15_survey_3/handoff.md` 就绪，接续即可派发 Worker 3 实施 |
| M4 | 物理红线校验、全量测试回归、服务平滑重启、/browser 页面走查验收与 G16 指令 | 4 只读文件哈希验证、全量自动化测试、8501 端口平滑重启、/browser 走查截图、git tag v4.5-G15 推送、严格纯文本无冒号 G16 指令输出 | M1, M2, M3 | PLANNED | 待 M3 完成后实施终审交付 |

---

## 2. Active Subagents
- **Active subagents**: None (All 17 subagents have completed and delivered reports).
- **Spawn Count**: 17 / 16 (Succession Threshold reached).

---

## 3. Pending Decisions & Key Constraints
1. **物理安全绝对红线**:
   - 严禁触碰或修改 4 个系统只读裁判基建文件：`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`（SHA256 绝对一致）。
   - 严禁修改 `DataLoader.simulate_execution` 默认函数签名与默认扣费逻辑。
2. **法医审计一票否决权**:
   - 任何阶段 Forensic Auditor 报告 INTEGRITY VIOLATION 则该阶段无条件打回，绝不姑息。
3. **G16 标签防转义门禁**:
   - 终审报告输出 G16 指令时，绝对禁止输出带冒号的 `slashCommand:` 格式，四个命令标签必须严格输出为纯文本形式：`/goal`、`/boost`、`/teamwork`、`/browser`。

---

## 4. Remaining Work (Concrete Next Steps for Successor)

### Step 1: 派发 Milestone 3 执行工兵 (Worker 3)
接续执行 Milestone 3（全部代码已在 `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g15_survey_3\handoff.md` 中完整编写），派发 `worker_m3`：
1. `AGY2_FundAdvisory/portfolio_manager.py`:
   - 实装 `slice_long_screenshot_for_ocr(image_bytes)`：100% 原始宽度不压缩，每段高度 1000px，上下保留 150px 垂直重叠带。
   - 集成本地离线 `rapidocr_onnxruntime` 与 28,177 基金字典模糊匹配 `fuzzy_match_fund_by_name(raw_name)`。
   - 修复会计恒等式反算成本 P0 漏洞：剔除 `gain_val = abs(...)`，保留真实收益正负号，修复 `<100` 元被错误丢弃的问题。
2. `AGY2_FundAdvisory/app_gui.py`:
   - 在 Tab 2 顶部工具栏实装「📸 截图导入持仓」popover 弹窗，支持手机截图上传、切片 OCR、`st.data_editor` 预览核对与一键写入账本。
   - 在 Tab 2 渲染醒目的「🧹 碎片尾仓一键瘦身建议卡」，支持一键清扫归集至核心底仓。
3. `AGY2_FundAdvisory/advisory_engine.py`:
   - 在 `ActiveRiskSentry.inspect_portfolio` 实装第 13 维「碎片尾仓清理诊断」（识别持仓金额小于 ¥200 或占比小于 1.0% 且满免赎期的标的）。
4. `AGY2_FundAdvisory/multi_ledger_manager.py`:
   - 预置名为「实战存量组合（29只·¥2.66万）」的真实账本（`combat_29_funds`，精确平账至 ¥26,615.10，持有天数 400 天）。
   - 在 Tab 2 支持一键切换至该账本，展示 19 只碎片尾仓清扫方案、3 大深套源（-¥936.78）手术方案与全周期对比。
5. 编写针对性测试套件 `tests/test_g15_phase3_ocr_and_combat29.py` 并运行回归测试。
6. 执行 Milestone 3 门禁独立核验（Reviewer, Challenger, Auditor）并签署 Gate 3 PASS。

### Step 2: 实施 Milestone 4 交付验收
1. 校验 4 只读裁判文件 SHA256 哈希；
2. 运行全量测试套件确保 100% 绿灯；
3. 彻底终止旧 8501 端口进程，重启最新服务；
4. 调用 `/browser` 打开 `http://localhost:8501` 逐页截图核验各模块排版与功能；
5. 更新根目录 `GEMINI.md` 与 `PROGRESS_LOG.md`，执行 git commit 与 `git tag -a v4.5-G15` 并 push 到远端（严禁创建 Release）；
6. 输出供下一轮直接复制执行的纯文本无冒号 G16 世代指令。

---

## 5. Key Artifact Index
- `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md` — 原始需求规范
- `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_18\PROJECT.md` — 全局架构与特性清单
- `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_18\BRIEFING.md` — 编排器持久记忆
- `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_18\progress.md` — 进度日志
- `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_18\GATE_STATUS.md` — 门禁记录 (Gate 1 & Gate 2 已 PASS)
- `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g15_survey_3\handoff.md` — Milestone 3 完整代码实施蓝图
