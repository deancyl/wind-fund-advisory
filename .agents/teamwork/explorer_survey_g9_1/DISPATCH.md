## 2026-11-07T22:51:37Z

【身份与目录】
你作为团队调查员 (teamwork_explorer)，负责深入调研 G9 世代量化因果律严苛纠偏第一重点模块。
你的工作目录为：d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_g9_1
原始需求文件路径：d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md（必须首先完整阅读该文件）
外部审计参考文档：
- c:\Users\deanc\Downloads\agy2_fundadvisory_quant_capability_audit.md
- c:\Users\deanc\Downloads\agy2.md

【核心调查任务】
重点调查 `AGY2_FundAdvisory/advisory_engine.py` 及相关测试：
1. 根除 OnlineHeuristicFactorEvolver 中的同日未来函数：
   - 检查 `_evaluate_population` 中第 t 日收盘特征 F[t] 选出的 Top 3 赛道权重 P[t] 与第 t+1 日收益率 R[t+1] 的对齐方式。如何严格滞后一期（P[:-1] 对应 R[1:]），绝不乘当天收益？
   - 动态净值序列 `nav_dynamic` 合成时，如何从日度收益中真实扣除双边换手摩擦成本（单边按 10 bps 计提）？
   - 检查夏普比率计算：如何严格扣减 2.0% 年化无风险利率（0.02 / 250.0）？
   - 检查 `get_60d_rolling_nav_and_trajectory`：找出当前使用 `lam = (t + 1) / 60.0` 线性插值伪造四维权重轨迹的代码，设计真实的推进式样本外演化轨迹（Walk-Forward Rolling Trajectory，按每 5 个交易日滚动推进演化，每期用前序数据演化并合成后 5 日样本外净值与权重）。
2. 缺失数据线性假序列消除与跨市场对齐：
   - 检查 `_extract_sector_price_matrix`：如何以 A 股交易日历（H00300 日期序列）为基准索引对 14 大赛道价格进行严格对齐（reindex + ffill），解决美股、港股、黄金与 A 股由于节假日不同直接 column_stack 导致的日期错位？
   - 彻底废除第 235 行 `np.linspace(1.0, 1.05, window_days)` 伪造上涨直线的做法；定位真实缺失时的降级逻辑（收益率置 0 并标记状态）。
   - 检查 `_build_factor_tensor_and_returns`：估值分位得分 `s_val` 如何从 85 天短窗高低改为基于长周期年线去趋势中枢或真实估值缓存？

【产出要求】
完成详细代码定位与改造技术方案，写成自包含手记输出至：
`d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_g9_1\handoff.md`，并在完成时通过 `send_message` 发送通知。


## 2026-11-07T23:03:20Z
**Context**: G9 世代量化因果律严苛纠偏调研 (OnlineHeuristicFactorEvolver & 价格对齐)
**Content**: 请汇报当前调研进展，以及预计何时输出 handoff.md？
**Action**: 请在完成 handoff.md 编写后发送通知。
