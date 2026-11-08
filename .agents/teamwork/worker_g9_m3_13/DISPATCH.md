## 2026-11-08T07:42:22Z
You are worker_g9_m3_13, a versatile implementation and QA worker.
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\worker_g9_m3_13\

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

MANDATORY INSTRUCTION:
Read the authoritative user request at:
d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
and the scope document at:
d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_13\SCOPE.md

### Strict Constraints:
- NEVER modify the four read-only referee files: `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`.
- NEVER modify `DataLoader.simulate_execution` signature or default fee logic.
- NEVER modify global `c:\Users\deanc\.gemini\GEMINI.md`. All rules and learnings must be recorded in workspace `d:\Google\Workspace\Wind\GEMINI.md` and `PROGRESS_LOG.md`.
- STRICT PROHIBITION: NEVER create any GitHub Release (`gh release create` is forbidden). Only `git tag -a v3.9-G9` and `git push origin HEAD` / `git push origin --tags`.
- Clean up all temporary scripts, ensure `data/ledgers_index.json` only contains the clean main live ledger.

### Your Tasks: Milestone 3 (M3)
1. 8501 端口服务平滑重启与探针核验：
   - 检查并重启 8501 端口服务（使用原生无窗口或后台脱钩方式启动 `py -3 -m streamlit run AGY2_FundAdvisory/app_gui.py --server.port 8501 --server.headless true`）；
   - 验证 `http://127.0.0.1:8501/_stcore/health` 返回 HTTP 200。
2. 多模态视觉验收走查（使用 browser 工具或命令行驱动走查）：
   - 检查 `http://localhost:8501`：
     * 首屏双翼看板最顶端是否高辨识度渲染“今日投顾行动总开关”（大白话指令 + 一键直达按钮）；
     * 首屏“历史三大牛熊拐点实盘对照尺”以及全屏富文本 HTML 是否 100% 纯化渲染，确认零原始 HTML 灰色代码块泄露（Rule 27）；
     * Tab 1 与 Tab 2 默认 L1 视图是否清爽极简、零卡片堆砌；
     * 展开 L2 白盒抽屉时高阶图表、蒙特卡洛、选基漏斗大表是否完整自适应、零截断；
     * 640px 移动端视口下是否平滑横向滚动、零水平溢出破坏。
3. 全量自动化测试回归：
   - 运行全量测试套件：
     `pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py tests/test_challenger_g9_m2_adversarial.py tests/test_g9_causal_brinson_and_suitability.py tests/test_challenger_g9_m2_stress.py`
     确保 100% 绿灯全部通过。
4. 确认四大只读裁判文件与 DataLoader 哈希零修改。
5. 清理临时脚本与测试脏数据，确保 `data/ledgers_index.json` 保持纯净主账本。
6. 更新工作区根目录 `GEMINI.md` 与 `PROGRESS_LOG.md`，沉淀 G9 世代外傻内精渐进式披露、HTML 纯化与因果律成果。
7. Git 提交与版本标签推送：
   - `git add -A`
   - `git commit -m "feat(G9): complete progressive disclosure UI decluttering and quant causality closure"`
   - `git tag -a v3.9-G9 -m "Release v3.9-G9: G9 generation progressive disclosure UI and causal quant closure"`
   - `git push origin HEAD`
   - `git push origin --tags`
   - 严禁创建 GitHub Release！
8. 生成供下一轮直接执行的 G10 纯文本进化指令：
   - 直接以 `/goal /boost /teamwork` 开头；
   - 走查环节包含 `/browser` 调用；
   - 全文保持纯文本干净排版，不使用任何表情符号、星号、反引号、数学公式符号或装饰性分隔线；
   - 包含全量测试验证、Git Commit 与 Git Tag 同步要求。
9. 撰写详尽的交付报告落盘至 `d:\Google\Workspace\Wind\.agents\teamwork\worker_g9_m3_13\handoff.md`，并通过 `send_message` 汇报完成。
