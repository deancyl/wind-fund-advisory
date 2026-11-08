## 2026-11-07T22:51:46Z
【身份与目录】
你作为团队调查员 (teamwork_explorer)，负责深入调研 G9 世代量化风控、雷达重算与信源验真模块。
你的工作目录为：d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_g9_2
原始需求文件路径：d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md（必须首先完整阅读该文件）
外部审计参考文档：
- c:\Users\deanc\Downloads\agy2_fundadvisory_quant_capability_audit.md
- c:\Users\deanc\Downloads\agy2.md

【核心调查任务】
重点调查 `AGY2_FundAdvisory/advisory_engine.py`、`AGY2_FundAdvisory/data_loader.py` 及 `AGY2_FundAdvisory/app_gui.py`：
1. ActiveRiskSentry 真实规模反查与清盘告警：
   - 定位 `ActiveRiskSentry.inspect_portfolio`（约 997 至 1015 行），找出 `else: aum = 2.5` 默认假规模兜底代码；
   - 调查如何主动调用 `DataLoader.get_fund_metadata` 或从 `CORE_STRATEGY_POOL` 与 `EXTENDED_FUND_CATALOG` 穿透反查真实规模；若反查仍无，如何规范标记为“规模待核验”状态并输出告警，彻底杜绝掩盖迷你基清盘风险。
2. 投资者适当性越界预警与盘中异动传导：
   - 调查在 `ActiveRiskSentry.inspect_portfolio` 中新增投资者适当性匹配与组合级止盈止损巡检：结合当前账本设定的风险等级（C1 至 C5），检测实盘持仓的权益资产占比与组合波动率是否越界超配（如 C1 保守型持仓高比例权益或高波科技基金），发出主动预警并提供一键降波纠偏；
   - 调查如何检测当前盘中实时估值异动（单基涨跌超 2% 或组合波动超 1%）对安全垫的实时消耗传导机制。
3. OpportunityRadarEngine 盘中最后一根 K 线真实重算与动态证据链：
   - 定位 `OpportunityRadarEngine.evaluate_sector` 中 `bias_20 = round(bias_20 + chg_pct, 2)` 的代码；设计融合实时涨跌幅时将最新价加入价格序列末尾精确重算 MA20、Bias20、Slope20 与 ER20 的技术方案；
   - 调查动态量化证据链合成器设计：结合真实估值分位、动量斜率、信噪比与反拥挤度得分，动态生成 100% 自洽文案；
   - 调查首屏 Top 3 赛道卡片如何完整披露四维子项得分及 20 日年化波动率与最大回撤风险指标。
4. 快讯信源验真：
   - 检查 `fetch_realtime_market_news_and_catalysts` 与首屏晨报展示，如何明确区分实时联网抓取快讯（标注信源与原始发布时间）与离线本地缓存快照（标注离线缓存与快照时间），根除用 `datetime.now()` 冒充实时抓取时间的问题。

【产出要求】
完成详细代码定位与改造技术方案，写成自包含手记输出至：
`d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_g9_2\handoff.md`，并在完成时通过 `send_message` 发送通知。
