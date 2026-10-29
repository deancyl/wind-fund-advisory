## 2026-10-29T14:44:16Z
[Message] timestamp=2026-10-29T14:44:16Z sender=1e00e836-4cfb-404e-a729-f97fbfd899ba priority=MESSAGE_PRIORITY_HIGH content=You are Agent-1: Ledger & Risk Control Expert (账本与风控修复专家).
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\worker_agent1
Your code base is: d:\Google\Workspace\Wind\AGY2_FundAdvisory
You exclusively own and write to: d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py

First, read:
1. `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`
2. `d:\Google\Workspace\Wind\PROJECT.md`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Strict Read-Only Invariants:
DO NOT modify, unlock, or write to:
- `AGY2_FundAdvisory/judge_engine.py`
- `AGY2_FundAdvisory/holdout_vault.py`
- `AGY2_FundAdvisory/AGENT_SPEC.md`
- `AGY2_FundAdvisory/tests/test_infra.py`

Your Task Scope (R1, R3, R4 in portfolio_manager.py):

1. R1. 修复账户账本峰值回撤状态污染与伴生标的标签:
- 在 portfolio_manager.py 的 apply_zero_start_blueprint()、takeover_mode_a()、takeover_mode_b() 及 import_from_smart_text() 中，重置持仓时清理旧组合残留的 self.peak_equity 与 self.max_drawdown_pct 等指标。
- 在上述所有建仓与接管函数末尾（全部持仓批次写入并调用 _recalculate_totals() 之后），强制重置账户基准与回撤状态：
```python
self.baseline_equity = self.total_equity
self.peak_equity = self.total_equity
self.max_drawdown_pct = 0.0
self.portfolio_return_pct = 0.0
self.benchmark_return_pct = 0.0
self.alpha_return_pct = 0.0
```
- 将所有赛道冠军标的与官方限购拆单伴生标的（如 001071 摩根标普500、090010 大成中证红利、000086 工银纯债、013841 银华集成电路等）全部纳入核心策略池（is_core_strategy = True），严禁将推荐买入的拆单备选基金标记为“待替换”或 transition_tag 包含“替换”。

2. R3. 金融股存贷双高排雷豁免与底层重仓股去重合并:
- 在 portfolio_manager.py 的 screen_fund_look_through_risk() 中增加金融行业豁免规则：凡股票名称包含“银行”、“证券”、“保险”、“金融”、“农商”或代码属于银行及非银金融行业的个股，存贷双高排查直接标记为“金融业豁免（正常）”，double_high_risk 设为 False，风险扣分记为 0（不扣分，不作为风险预警项）。
- 在底层重仓股穿透排雷宽表的数据准备中（如 get_portfolio_look_through_stocks 或生成持仓股宽表的方法），按股票代码聚合为唯一行，将“所属基金”列改为“关联持仓基金（列出持有该股的所有基金代码）”，并新增“占组合总市值比例(%)”列，按组合持仓占比降序排列。

3. R4. 限购拆单前后表格一致性与同源份额重合度误报豁免:
- 在 generate_zero_start_blueprint() 生成建仓列表时，一旦某只基金分配金额超过 daily_limit（如 050025 分配 6,000 元大于限额 500 元），直接在返回的 blueprint["items"] 列表中拆分为两行独立记录（第一行：050025 买入 500 元；第二行：001071 摩根标普500A 买入 5,500 元），使建仓表格、复制文本与持仓账本完全一致。
- 在 calculate_stock_overlap_matrix() 中内置同源指数与限购拆单豁免组（如 {"050025", "001071"}、{"011612", "011613"}、{"100032", "008682"}、{"000216", "000217"} 等）。凡属于限购拆单伴生组合或同一指数的 A/C 份额，一律豁免伪分散报警，并在矩阵说明中标注“合规限购分仓/同源份额”。

Verification & Handoff:
- Run tests on portfolio_manager (e.g. `pytest tests/test_portfolio_manager.py` or existing tests) to verify your modifications compile and pass.
- Write your detailed handoff report to `d:\Google\Workspace\Wind\.agents\teamwork\worker_agent1\handoff.md`.
- Keep `progress.md` updated during your work.
- Use `send_message` to notify orchestrator upon completion with path to handoff.md.
