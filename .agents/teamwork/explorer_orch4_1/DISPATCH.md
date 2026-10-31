## 2026-10-31T14:29:43Z
[Message] timestamp=2026-10-31T14:29:43Z sender=d536f3b8-ee96-41ed-9fa9-cbd10993bb6a priority=MESSAGE_PRIORITY_HIGH content=你是 explorer_orch4_1 (Quota and Valuation Explorer)。
你的工作目录是: d:\Google\Workspace\Wind\.agents\teamwork\explorer_orch4_1
原始需求文件路径 (必读): d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
代码项目根目录: d:\Google\Workspace\Wind\AGY2_FundAdvisory

【核心任务】
针对阶段一重构需求中的 R2（废除硬编码限额，实现实时限购获取与多级瀑布流拆单及 QDII 盘中估值纠偏），对 AGY2_FundAdvisory/portfolio_manager.py 及相关数据接口进行深度只读勘测分析，为后续 Agent-1 的实现提供准确的证据链、代码行号、数据结构契约与实施方案：

1. 必须首先阅读 d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md，掌握全部任务背景与安全红线（严禁修改只读裁判文件，严禁使用 time.sleep 伪造耗时，严禁硬编码 daily_limit 为 500 或 1000 等）。
2. 勘测 portfolio_manager.py 中的限额处理现状：
   - 目前在哪些位置存在硬编码 500 或 1000（如 generate_zero_start_blueprint、调仓建议等）？
   - 目前是否有 fetch_realtime_fund_quota 函数？如果没有，应如何设计其签名与返回字典：
     `{"fund_code": code, "status": "开放申购"|"限制大额"|"暂停申购", "daily_limit": float, "is_limited": bool}`
   - 如何通过 `akshare.fund_purchase_em()` 获取全市场基金当日申购状态与日累计限定金额？其字段名称是什么？断网时如何从本地 SQLite/Parquet 带日期戳缓存回退？
   - 多级瀑布流拆单算法逻辑应如何重构：
     * 首选基金分配 min(target_amt, quota["daily_limit"])，action_guide 动态生成为 `f"单日限额¥{int(quota['daily_limit'])}·已拆单"`；
     * 剩余金额 rem_amt 遍历备选基金分配，每只备选基金也检查 quota；
     * 若备选不限购则显示 `承接超额·不限购正常买`，若也限购则最多分配其限额，若全市场仍有剩余金额未分配，如何生成 `dca_plan`？
3. 勘测 fetch_realtime_fund_quote() 与 QDII 估值纠偏现状：
   - 目前 fetch_realtime_fund_quote 是如何获取基金估值 gszzl 的？
   - 对 QDII 标普/纳指及黄金联接基金，目前如何对比底层基准实时涨跌幅（`sh513500` / `gb_inx` / `sh518880`）？
   - 估算涨跌幅 gszzl 与基准实时涨跌幅绝对偏差 > 1.5% 时，如何使用基准实时涨跌幅 * 0.95 覆盖纠偏？
4. 注意事项：你是只读探索者，严禁修改任何代码。将勘测分析、代码定位、伪代码与接口设计详细写入你的工作目录下的 handoff.md，完成后通过 send_message 向父编排者汇报。
