## 2026-11-09T09:17:58Z
You are worker_g13_m4, a teamwork_worker.
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\worker_g13_m4\
You MUST read the user's original request file before starting:
d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Also read:
d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_1\PROJECT.md
d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_1\handoff.md
d:\Google\Workspace\Wind\.agents\teamwork\worker_g13_m3\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. Integrity violations WILL be detected and your work WILL be rejected.

PHYSICAL SAFETY RED LINES:
- NEVER touch or modify the 4 strictly read-only files:
  `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py` (and `AGY2_FundAdvisory/tests/test_infra.py`).
- `DataLoader.simulate_execution` default signature and default fee deduction logic MUST remain 100% intact.
- STRICT INVARIANT: Absolutely NO GitHub Release creation (`gh release create` is strictly forbidden).
- WORKSPACE-ONLY /LEARN INVARIANT: NEVER touch global `c:\Users\deanc\.gemini\GEMINI.md`. All rules must be written to workspace root `d:\Google\Workspace\Wind\GEMINI.md` and `PROGRESS_LOG.md`.

YOUR SCOPE & WRITE OWNERSHIP (Milestone 4: 8501 服务平滑重启、浏览器实机核验、工作区规范沉淀、Git 标签归档与 G14 世代指令准备):
Files you own:
- `scripts/restart_service.py` (or helper verification scripts in `scripts/`)
- `d:\Google\Workspace\Wind\GEMINI.md` (append-only in workspace root)
- `d:\Google\Workspace\Wind\PROGRESS_LOG.md` (append-only in workspace root)
- Screenshots in `data/screenshots/` (if generated)

DETAILED TASKS:
1. 平滑重启 8501 服务并探针核验:
   - 安全终止占用 8501 端口的旧进程（优先检查是否为 LISTENING 状态）。
   - 在后台无窗口托管模式下拉起最新服务：例如运行 `py -3 scripts/restart_service.py`。
   - 探针核验：确保 `http://localhost:8501` 返回 HTTP 200，确认服务健康存活。
2. 浏览器实机 5 图对照核验:
   - 对 `http://localhost:8501` 进行实测，对照原始用户需求的 5 张问题图逐一核验并抓取关键渲染数据/截图：
     - 痛点 1（图 1）：首屏极速秒开（<150ms），顶部 4 张卡片与全宽投顾提示栏瞬间渲染完毕，零白屏阻塞。
     - 痛点 2 与 3（图 2、图 3）：首屏右上角刺眼大红按钮 `👉 查看锁仓保护` 彻底消失，右侧空白列消除，折叠栏 100% 满宽；展开高度 <= 220px，仅含左翼 Top 3 赛道卡与右翼极简无按钮文字风险提示；5 大深度工具已完全迁出。
     - 痛点 5（图 5）：全宽四等分 46px 大胶囊主导航生效，深海蓝选中态，纯白字体，严格隔离子 Tab；四大 Tab 内部删除重复巨型标题；Tab 4 顶栏合并为紧凑单行。
     - 痛点 4（图 4）：Tab 3 组合回测净值曲线 Plotly 图例移至图表外部上方 (`y=1.06`, transparent)，零遮挡曲线；牛熊标注淡化；纯债指数为 `H11009` 真实日度全收益曲线；实盘账本挂载后视镜 disclaimer 与 C3 动态策略对照开关。
3. 工作区经验规范沉淀 (Workspace-Only Invariant):
   - 将 G13 世代总结的核心防御规则（首屏零阻塞秒开磁盘缓存、UI 伪交易按钮消除与参谋定位、全宽大胶囊 CSS 隔离、回测曲线打假与真实全收益基准对齐、测试沙盒数据物理隔离）写入工作区根目录 `d:\Google\Workspace\Wind\GEMINI.md` 与 `PROGRESS_LOG.md`。
   - 严禁修改或触碰全局 `c:\Users\deanc\.gemini\GEMINI.md`。
4. Git 提交与打标同步:
   - 执行 `git add -A`
   - 执行 `git commit -m "feat: G13 generation UI/UX overhaul, cache & backtest de-biasing closure"`
   - 执行 `git tag -a v4.3-G13 -m "Release v4.3-G13"`
   - 执行 `git push origin HEAD` 与 `git push origin --tags`
   - 严禁创建任何 GitHub Release！
5. 交付完整的 handoff.md 报告:
   - 写入: `d:\Google\Workspace\Wind\.agents\teamwork\worker_g13_m4\handoff.md`
   - 包含五段式内容（事实、逻辑链、声明、结论、复核方法），并在文末附带严格符合分号规范 `[/cmd](slashCommand;cmd)` 的 G14 世代指令（绝不能包含冒号 `slashCommand:`）。
   - 通过 `send_message` 通知 parent。
