## 2026-10-31T14:44:19Z

你是 Agent-1（实时限购与估值纠偏专家），专精实现 Milestone 1 (M1)。
你的工作目录是: d:\Google\Workspace\Wind\.agents\teamwork\worker_agent1_orch4
原始需求文件路径 (必读): d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
项目工程蓝图: d:\Google\Workspace\Wind\PROJECT.md
前序勘测报告 (必读，包含代码行号、实测数据与接口实现细节): d:\Google\Workspace\Wind\.agents\teamwork\explorer_orch4_1\handoff.md
代码项目根目录: d:\Google\Workspace\Wind\AGY2_FundAdvisory

【文件独占写权限】
你独占拥有文件: `AGY2_FundAdvisory/portfolio_manager.py`
严禁修改其他源文件，严禁触碰只读裁判文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）。

【MANDATORY INTEGRITY WARNING】
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

【核心实现任务】
依据 ORIGINAL_REQUEST.md §R2 与 explorer_orch4_1/handoff.md 中的指引，在 `portfolio_manager.py` 中完整落地以下功能：

1. **废除硬编码限额，新增 `fetch_realtime_fund_quota(fund_code: str) -> Dict[str, Any]`**:
   - 彻底清除 `CORE_STRATEGY_POOL`、`resolve_fund_meta`、`generate_zero_start_blueprint` 等各处硬编码的 500 或 1000 常数；
   - 建立高可用三级架构：L1 内存缓存（当日有效） -> L2 本地 SQLite 缓存表（`portfolio_state.db` 中的 `fund_daily_quota_cache` 表，带 `quota_date` 日期戳） -> L3 离线兜底（读取 `data/master/fund_trading_rules.parquet` 真实规则，严禁造假）；
   - 调用 `akshare.fund_purchase_em()` 获取全市场基金当日申购状态（"开放申购"|"限制大额"|"暂停申购"）与 "日累计限定金额"；
   - 统一返回规范字典结构：
     `{"fund_code": code, "status": "开放申购"|"限制大额"|"暂停申购", "daily_limit": float, "is_limited": bool}`
   - 当网络断开或请求异常时，自动安全回退读取最近一次真实缓存（SQLite 或 Parquet 湖仓）。

2. **重写多级瀑布流拆单算法（`generate_zero_start_blueprint` 及调仓拆单）**:
   - 当某赛道首选基金分配金额 `target_amt > quota["daily_limit"]` 时：
     1. 首选基金仅分配 `min(target_amt, quota["daily_limit"])`（若暂停申购则为 0），其 `action_guide` 动态生成为 `f"单日限额¥{int(quota['daily_limit'])}·已拆单"`（严禁写死“限额买500”）；
     2. 剩余金额 `rem_amt` 按该赛道备选基金列表逐只尝试分配，且每一只备选基金必须同样调用 `fetch_realtime_fund_quota(alt_code)` 检查其自身限额；
     3. 若备选基金自身不限购（`daily_limit >= rem_amt`），其 `action_guide` 必须显示为 `"承接超额·不限购正常买"`；若备选基金自身也限购（如限额 1,000 元），则该备选基金最多只分配 1,000 元，扣减后继续寻找下一个备选；
     4. 若全赛道备选均遍历完仍有未分配完的剩余资金，自动在蓝图或条目中生成 `dca_plan`（如：`剩余¥4,500受全市场QDII限额约束，建议分5个交易日定投买入，或暂存货币/黄金底仓`）。

3. **修复 QDII 与跨市场基金盘中估值（`gszzl`）失真与美股前缀 Bug**:
   - 在 `fetch_realtime_index_quote()` 中修复美股指数（如 `gb_inx`）被错误拼接为 `s_shgb_inx` 的 Bug，支持新浪 `https://hq.sinajs.cn/list=gb_inx` 正常解析（`parts[2]` 为涨跌幅）；
   - 在 `fetch_realtime_fund_quote()` 中，对 QDII 标普/纳指及黄金联接基金，同时对比底层基准实时涨跌幅（`sh513500` / `gb_inx` / `sh518880`）。若基金估算涨跌幅 `gszzl` 与基准涨跌幅绝对偏差 `> 1.5%`（如 050025 显示 +0.49% 而 001071 异常显示 -4.92%），自动使用基准实时涨跌幅乘以 0.95 覆盖纠偏，并重新校准 `gsz = round(dwjz * (1.0 + gszzl / 100.0), 4)`，在 quote 中标记 `valuation_corrected: True`。

【验收与验证要求】
- 编写或运行对 `portfolio_manager.py` 的测试（如 `py -3.11 -m pytest tests/test_portfolio_manager.py -v`），确认所有测试通过，无语法错误，无接口破坏。
- 完成后在你的工作目录输出 `handoff.md`，并通过 `send_message` 向父编排者汇报。
