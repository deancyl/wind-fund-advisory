# Worker Task Assignment: Milestone 3 全量测试回归、文档沉淀与 Git 归档

## 目标
扩展 `tests/test_g3_evolution_loop.py` 专项测试，运行全量自动化测试套件确保 100% 通过；核查 4 大裁判文件零修改；更新 `GEMINI.md` 与 `PROGRESS_LOG.md`；执行 Git commit 与打标签 `v3.5-G5` 并推送远端（严禁创建 Release）；验证 8501 端口服务存活。

## 独占拥有的文件（Write Ownership）
- `tests/test_g3_evolution_loop.py`
- `GEMINI.md` (当前工作区根目录)
- `PROGRESS_LOG.md`
- `data/ledgers_index.json` (确保仅保留干净的主实盘账本)

## 严禁修改的文件（Strict Read-Only）
- `judge_engine.py`
- `holdout_vault.py`
- `AGENT_SPEC.md`
- `tests/test_infra.py`
- `DataLoader.simulate_execution` 默认签名与扣费逻辑
- 绝对禁止创建任何 GitHub Release！
- 规则沉淀隔离铁律：严禁修改全局 `c:\Users\deanc\.gemini\GEMINI.md`！

## 实施要求与规范
1. **测试套件扩充 (`tests/test_g3_evolution_loop.py`)**：
   - 新增 `test_g5_1_single_fund_real_volatility_penetration`：测试消除 0.04/0.14/0.18 常数，5 万元申购下纯债 (002351) < 红利 (005561) < 科技 (011613) 节省基点严格单调递增，且基点与单基真实波动率严格对齐；
   - 新增 `test_g5_2_historical_inflection_ruler`：测试 4 节点结构（2021=0.5x, 2022=1.93x, 2024=1.94x, 今日=1.76x）及其在前端与策略桥接中的返回值有效性；
   - 新增 `test_g5_3_cushion_break_even_stress_model`：测试组合加权 Beta、综合安全垫厚度、破净安全边际 $R_{m,\text{break}}$ 与浮亏回本反弹 $R_{m,\text{recover}}$、3 档压力测试推演及全现金物理免疫；
   - 新增 `test_g5_4_tail_valuation_anomaly_alerts`：测试盘中真实估值 `gszzl` 在大涨 > 1.5 sigma_day 且正乖离时触发 `ANTI_CHASING`，急跌 > 1.5 sigma_day 且负乖离时触发 `GOLDEN_PIT`。
2. **运行全量自动化测试套件**：
   - 运行 `py -3 -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py`，确保 100% 通过（预计 50+ 项用例全绿）；
   - 确认四大裁判文件绝对零字符修改：`git diff --exit-code judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py`；
   - 确认 `data/ledgers_index.json` 仅保留干净的主实盘账本，清理工作区内的临时脚手架脚本。
3. **服务健康探测**：
   - 检查 8501 端口服务存活状态（`curl.exe -I http://127.0.0.1:8501/_stcore/health` 返回 HTTP 200）。若未运行或需重载，平滑确保其健康运行。
4. **文档沉淀与经验固化**：
   - 将 G5 世代单基真实波动率穿透、历史三大拐点实盘对照、浮盈安全垫破净临界推演与 14:30 尾盘估值异动防御闭环的核心准则追加写入当前工作区根目录的 `GEMINI.md`；
   - 将 G5 详细交付记录追加写入 `PROGRESS_LOG.md`。
5. **Git 归档与版本标签同步**：
   - `git add -A`
   - `git commit -m "feat(g5): implement single-fund volatility penetration, historical inflection ruler, cushion break-even model, and 14:30 anomaly watchdog"`
   - `git tag -a v3.5-G5 -m "Release v3.5-G5: Single-Fund Volatility Penetration, Inflection Ruler, PnL Cushion & Tail Anomaly Watchdog"`
   - `git push origin HEAD` 与 `git push origin --tags`
   - **绝对禁止调用 `gh release create` 或创建任何 Release**！
6. 产出详尽的 `handoff.md`，并在完成后通过 send_message 向 orchestrator 汇报。

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.


## 2026-11-06T18:01:18Z
[Message] timestamp=2026-11-06T18:01:18Z sender=71f16351-ac4e-45f7-b8a4-89e38ec8863c priority=MESSAGE_PRIORITY_HIGH content=你是一个专业测试与工程交付专家（teamwork_worker）。
你的专属工作目录是：d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r12_m3\
上级调度员 ID: 71f16351-ac4e-45f7-b8a4-89e38ec8863c

【必须阅读的基准文档】
- 原始需求：d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- 项目架构与契约：d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_7\PROJECT.md
- 任务派发规范：d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r12_m3\DISPATCH.md
- M1 交付物：d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r12_m1\handoff.md
- M2 交付物：d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r12_m2\handoff.md

【独占写权限文件】
- tests/test_g3_evolution_loop.py
- GEMINI.md (当前工作区根目录)
- PROGRESS_LOG.md
- data/ledgers_index.json (确保仅保留干净的主实盘账本)

【只读禁改红线】
- judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py 严禁做任何修改！
- DataLoader.simulate_execution 默认函数签名与扣费逻辑严禁修改！
- 绝对禁止创建任何 GitHub Release！
- 严禁向全局 c:\Users\deanc\.gemini\GEMINI.md 溢出，必须且仅允许写入当前工作区根目录的 GEMINI.md！

【MANDATORY INTEGRITY WARNING】
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

【核心实施任务】
1. 在 tests/test_g3_evolution_loop.py 中新增针对单基差异化波动率损耗、历史拐点对照尺渲染、浮盈安全垫破净临界点、14:30 尾盘估值异动预警的 4 组专项测试用例；
2. 运行全量自动化测试套件：
   py -3 -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py
   确保 100% 通过；
3. 校验四大裁判文件 git diff 为空；确保 data/ledgers_index.json 仅保留干净的主实盘账本，清理临时脚本；
4. 探针验证 8501 端口服务存活（curl.exe -I http://127.0.0.1:8501/_stcore/health 返回 HTTP 200）；
5. 将 G5 进化成果与准则写入当前工作区根目录的 GEMINI.md 与 PROGRESS_LOG.md；
6. 执行 git add -A，git commit，git tag -a v3.5-G5，git push origin HEAD 与 git push origin --tags（禁止创建 Release）；
7. 产出详尽的 handoff.md 并在完成后使用 send_message 向 71f16351-ac4e-45f7-b8a4-89e38ec8863c 汇报。
