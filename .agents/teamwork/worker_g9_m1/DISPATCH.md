## 2026-11-07T23:05:45Z
【身份与工作目录】
你作为负责核心实现的专业技术工人 (teamwork_worker)。
你的工作目录为：d:\Google\Workspace\Wind\.agents\teamwork\worker_g9_m1
原始需求文件路径：d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md（必须首先完整阅读该文件）
项目规划文件：d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_10\PROJECT.md
前序勘测员的详细设计与代码替换蓝图：
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_g9_1\handoff.md
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_g9_2\handoff.md

【文件独占写权限】
你独占拥有以下两个文件的修改权限：
1. d:\Google\Workspace\Wind\AGY2_FundAdvisory\advisory_engine.py
2. d:\Google\Workspace\Wind\AGY2_FundAdvisory\data_loader.py
严禁修改其他非你拥有的文件，特别是四个物理只读裁判文件（judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py）以及全局 C:\Users\deanc\.gemini\GEMINI.md！严禁修改 DataLoader.simulate_execution 的函数签名与默认扣费逻辑！

【MANDATORY INTEGRITY WARNING】
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

【核心实施任务】
请对照 explorer_survey_g9_1\handoff.md 与 explorer_survey_g9_2\handoff.md 中的精确代码方案，实现 Milestone 1 全部功能：

1. 修复 OnlineHeuristicFactorEvolver 致命缺陷（advisory_engine.py）：
   - 消除同日未来函数：在 _evaluate_population 中，第 t 日基于收盘特征 F[t] 选出的 Top 3 赛道权重 P[t]，必须严格滞后一期作用于第 t+1 日的真实收益率 R[t+1]（即 P[:-1] 对应 R[1:]），严禁拿第 t 日收盘选出的权重乘第 t 日当天的收益率；
   - 真实扣除双边换手摩擦成本：合成动态净值序列 nav 与适应度打分时，必须从日度组合收益率中真实扣除双边换手摩擦成本（单边按 10 bps 计提，即 0.0020 * daily_to）；
   - 强制扣除 2.0% 年化无风险利率：计算夏普比率时，严格按照 AGENT_SPEC.md 要求从日均收益率 mean_r 中减去日化无风险利率（0.02 / 250.0），杜绝纯债白嫖高夏普；
   - 实装真实的推进式样本外演化轨迹（Walk-Forward Rolling Trajectory）：废除 get_60d_rolling_nav_and_trajectory 中使用 lam = (t + 1) / 60.0 人工线性插值伪造四维权重轨迹的做法，改为在历史窗口上按每 5 个交易日滚动推进演化（共 12 个切片，每个节点仅使用该节点之前的历史数据求解当期最优权重并用于后续 5 日样本外收益合成），真实记录每一期的四维因子权重变化与样本外净值表现。

2. 价格矩阵对齐、假序列消除与估值中枢化（advisory_engine.py）：
   - 在 _extract_sector_price_matrix 中，以 A 股交易日历（H00300 日期序列）为基准索引，将 14 大赛道的价格序列按交易日期严格对齐（使用 reindex 与前向填充 ffill），彻底解决美股、港股、黄金与 A 股由于节假日不同直接按尾部条数 column_stack 导致的日期错位问题；
   - 彻底废除缺失数据时使用 np.linspace(1.0, 1.05, window_days) 伪造零回撤单边上涨直线的做法；若某赛道数据经多级回退仍缺失，将其收益率设为 0（置常数 1.0）并标记数据缺失状态，严禁伪造虚假高夏普序列；
   - 在 _build_factor_tensor_and_returns 中计算估值分位得分 s_val 时，改为基于长周期年线去趋势中枢或真实估值缓存计算，严禁仅用 85 天短窗口价格高低冒充长期估值分位数。

3. ActiveRiskSentry 真实规模反查、投资者适当性预警与异动传导（advisory_engine.py）：
   - 清除 2.5 亿元默认假规模兜底：在 inspect_portfolio 中，当传入的 fund_metadata 缺少某基金规模字段时，主动调用 DataLoader.get_fund_metadata 或从 CORE_STRATEGY_POOL 与 EXTENDED_FUND_CATALOG 中穿透反查真实规模；若反查后仍无规模数据，必须将其标记为“规模待核验”状态（aum_status="PENDING_VERIFICATION", action_type="replace_fund"）并输出黄色提示，严禁使用 else: aum = 2.5 静默赋予 2.5 亿元安全规模掩盖迷你基清盘风险；
   - 新增投资者适当性匹配与组合级止盈止损巡检：结合当前账本设定的风险等级（C1 至 C5，支持传参 investor_risk_tier），检测实盘持仓的权益资产占比与组合波动率是否越界超配（如 C1 保守型持仓高比例权益或高波科技基金），一旦越界立即发出主动预警并提供一键降波纠偏动作；
   - 检测当前盘中实时估值异动（单基涨跌超 2% 或组合波动超 1%）对安全垫的实时消耗传导（计算实时消耗金额与比例）。

4. OpportunityRadarEngine 盘中末端真实重算与动态证据链（advisory_engine.py）：
   - 在 evaluate_sector 中，废除 bias_20 = round(bias_20 + chg_pct, 2) 的粗暴算术相加；当融合盘中实时涨跌幅时，将实时最新价更新至价格序列末尾，精确重算盘中实时 MA20、Bias20、Slope20、考夫曼信噪比 ER20、20日年化波动率与20日最大回撤；
   - 实装动态量化证据链合成器：在 evaluate_sector 中，结合该赛道当前的真实估值分位、动量斜率、信噪比与反拥挤度得分，动态生成与量化指标方向 100% 自洽的入选依据文案，并随字典返回 vol_20 与 mdd_20。

5. 快讯信源真伪双轨隔离（data_loader.py）：
   - 在 fetch_realtime_market_news_and_catalysts 中，明确区分实时联网抓取快讯（标注具体信源名称与原始发布时间，is_realtime=True）与离线本地缓存快照（标注离线缓存状态与快照保存时间，is_realtime=False），严禁在离线兜底时用 datetime.now() 冒充实时抓取时间。

【验证与交付要求】
1. 实现完成后，运行单元测试：
   py -3 -m pytest tests/test_infra.py tests/test_g7_architecture_and_decoupling.py tests/test_adv_final_closure.py -v
2. 确保所有修改通过相关测试，且四大裁判文件零修改。
3. 撰写详细自包含的 handoff.md 并通过 send_message 通知编排器。

## 2026-11-07T23:16:04Z
**Context**: Milestone 1 核心算法实现实施进度查询 (worker_g9_m1)
**Content**: 安全定时器已触发（距离派发已过 10 分钟）。请汇报当前任务完成进度：各项算法修改（未来函数滞后、换手摩擦、夏普扣Rf、Walk-Forward轨迹、日历对齐、规模反查、适当性预警、K线重算、快讯验真）是否已完成？测试是否已通过？预计还需要多长时间产出 handoff.md？
**Action**: 请在收到本消息后汇报简要状态，并在完成全部修改与测试后输出 handoff.md 并发送通知。
