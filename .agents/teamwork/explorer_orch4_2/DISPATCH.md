## 2026-10-31T14:29:53Z

你是 explorer_orch4_2 (Dynamic Weights Algorithm Explorer)。
你的工作目录是: d:\Google\Workspace\Wind\.agents\teamwork\explorer_orch4_2
原始需求文件路径 (必读): d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
代码项目根目录: d:\Google\Workspace\Wind\AGY2_FundAdvisory

【核心任务】
针对阶段一重构需求中的 R3（清除静态权重劫持与打通三段式攻防闭环），对 AGY2_FundAdvisory/strategy_bridge.py 与 data_loader.py 进行深度只读勘测分析，为后续 Agent-2 的实现提供准确的证据链、代码行号、数学模型与实施方案：

1. 必须首先阅读 d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md，掌握全部任务背景与安全红线（严禁修改只读裁判文件，严禁让 C3 档位绕过动态权重计算函数等）。
2. 勘测静态权重劫持与动态配权现状：
   - 检查 `generate_zero_start_blueprint()` 与 `get_latest_market_snapshot()` 以及 `strategy_bridge.py` 中是否存在对 C3 或其他档位硬编码常数（如 `0.38 / 0.30 / 0.14 / 0.12 / 0.06`）直接返回的逻辑？记录具体行号与上下文。
   - 检查 `compute_dynamic_tier_weights()` 当前实现：它是如何结合目标波动率预算、Hedge 四大专家实时权重与 EWMA 波动率倒数的？
3. 勘测三段式攻防闭环现状与嵌入方案：
   - 三段式逻辑应如何无缝嵌入 `compute_dynamic_tier_weights()`：
     1) 左侧极值超卖吸筹：当 `erp_percentile >= 75.0` 且沪深300或科创50的 20 日均线乖离率 `bias_20 <= -4.5%`（极度超卖）时，自动从纯债仓位中划拨 `10% ~ 15%` 仓位逆向增配高弹性宽基（011613 / 001053），在底部左侧吃反弹。如何获取 erp_percentile 与 bias_20？纯债与高弹性宽基代码在代码中如何对应？
     2) 右侧施密特迟滞防打脸：维持 `[-1.5%, +1.2%]` 均线迟滞缓冲带，在震荡噪音期锁定仓位不折腾。当前状态机是如何维持迟滞状态的？
     3) 右侧极端超买阶梯止盈：当进攻标的出现 `bias_20 >= +6.5%`（短期暴涨严重超买）或触发 `crowding_warning == True`（极度拥挤且聪明钱流出）时，不等跌破均线，主动将高波动成长仓位削减 `30% ~ 35%` 并落袋转入纯债（002351）与红利低波（005561），锁住牛市脉冲利润。
4. 勘测回测与实盘算子中的阶梯赎回费对齐：
   - 检查目前在哪些文件和函数中计算赎回费？
   - 真实 7天/30天/180天 阶梯赎回费（7天内 1.5% 惩罚性费率，7-30天 0.5% 或 0.75%，30-180天 0.5% 或 0%，180天以上 0%）当前是如何定义的，是否存在不一致？
5. 注意事项：你是只读探索者，严禁修改任何代码。将勘测分析、代码定位、计算公式与详细实施方案写入你的工作目录下的 handoff.md，完成后通过 send_message 向父编排者汇报。
