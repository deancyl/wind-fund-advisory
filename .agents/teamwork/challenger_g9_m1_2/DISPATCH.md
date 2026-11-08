## 2026-11-07T23:36:02Z

【身份与目录】
你作为团队对抗验证员 2 (teamwork_challenger)。
工作目录：d:\Google\Workspace\Wind\.agents\teamwork\challenger_g9_m1_2
原始需求：d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md（必须首先完整阅读）
项目规划：d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_10\PROJECT.md
工人交付报告：d:\Google\Workspace\Wind\.agents\teamwork\worker_g9_m1\handoff.md

【核心对抗任务】
编写独立探针与对抗验证代码，验证 ActiveRiskSentry、Radar 与快讯：
1. **规模反查与清盘告警对抗探针**：
   - 构造持有一只全市场真实迷你基金（或规模为 0.35 亿元的标的，且不传 `fund_metadata`），调用 `sentry.inspect_portfolio`，断言返回包含清盘警戒告警；
   - 构造一只未知代码 `999999`，断言返回包含“规模待核验”黄色告警，绝对未被赋予 2.5 亿元通过；
2. **适当性越界与盘中异动对抗探针**：
   - 设定账本档位为 `C1`，持仓配置 60% 科技成长标的（如 013841），断言 `inspect_portfolio` 抛出 `【投资者适当性越界】` 红色预警并提供一键降波建议；
   - 传入盘中估值异动 `gszzl = -3.5%`，断言预警哨输出 `【盘中异动预警】实时消耗安全垫`；
3. **雷达末端重算与信源验真对抗探针**：
   - 传入盘中涨跌幅 `+5.0%`，断言 `evaluate_sector` 输出的 `bias_20`、`slope_20`、`er_20` 是由重算序列产生，且 `bias_20 != old_bias + 5.0`；
   - 模拟网络断开，调用 `DataLoader.fetch_realtime_market_news_and_catalysts`，断言返回字典的 `is_realtime` 为 `False`，`source` 包含“离线”字样，且 `timestamp` 绝不等于当前的系统秒数；
4. 给出对抗裁决：**APPROVE** 或 **REQUEST_CHANGES**，写入 handoff.md 并通过 send_message 发送。
