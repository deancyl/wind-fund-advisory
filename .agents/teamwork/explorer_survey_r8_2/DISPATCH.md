## 2026-11-05T01:37:42Z

You are Explorer Survey R8-2.
Your working directory is d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r8_2\.
Read the original user request at: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md.
Also review the project rules at: d:\Google\Workspace\Wind\GEMINI.md.

YOUR FOCUS: Requirement R2 - 数据同源单源同真与双翼看板升级（全景机会雷达 + 六维主动风险预警哨）
1. 数据同源（Single Source of Truth）：
   - 深度调查 advisory_engine.py 中 RADAR_SECTOR_CATALOG 的现状：哪些地方硬编码了静态 base_val_pct、er_20、bias_20、slope_20。
   - 调查 data_loader.py 的 IndexValuationEngine 与本地行情矩阵（如 data/aligned_matrix_total_return.parquet）：如何实时计算 14 大赛道的真实 PE/PB 分位数、20 日考夫曼信噪比 ER、MA20 乖离率与动量斜率。
   - 分析如何彻底废弃静态硬编码，让侧边栏走廊与双翼看板展示的估值分位数 100% 同源一致。
2. 升级左翼全市场机会雷达：
   - 调查左翼看板渲染逻辑：现有 Top 3 机会卡片展示机制。
   - 调查如何设计可展开的全市场 14 大赛道量化温度计总表（展示赛道名称、估值分位、趋势信噪比、20日乖离率、拥挤度评分、综合得分、状态标签与优选基金）。
   - 调查双翼看板顶部 <=80 字今日市场脉搏晨报的生成逻辑（自动串联两市成交额变化、ERP 分位、领涨主线与低估击球区解读）。
3. 补齐右翼六维主动风险预警哨与一键处置：
   - 调查 ActiveRiskSentry.inspect_portfolio 的现有实现，定位缺失的预警维度。
   - 梳理 6 大维度的检测逻辑与触发阈值：
     1. 维度1（未满 7 天惩罚锁仓红牌）：持有天数 < 7 天（如 011612），严禁赎回防 1.50% 惩罚费；
     2. 维度2（临近免赎期倒计时黄牌保护）：A/C 类持有 4 至 6 天（差 1 至 3 天满 7 天），或 C 类持有 23 至 29 天（差 1 至 7 天满 30 天免赎回费，如 011613），主动提醒再等几天省下赎回费；
     3. 维度3（C 类满 30 天零费率置换提醒）：持有 >= 30 天的 C 类份额提醒赎回费已归零，长期持有建议择机置换为低费率 A 类；
     4. 维度4（个基阶梯止盈与深套诊断）：进攻型基金浮盈 >= +15% 且赛道 Bias20 > +5%（或估值分位 > 75%）触发阶梯止盈建议（赎回 30%~50% 锁定利润转入纯债/红利）；浮亏 <= -12% 结合赛道估值分位给出摊薄或调仓诊断（如 013841）；
     5. 维度5（组合赛道集中度与重仓股重叠预警）：单一细分赛道持仓占比 > 35% 或重仓股重叠度过高发出集中度预警；
     6. 维度6（基金本体清盘线与大盘攻防线预警）：排查规模 < 0.5 亿元迷你基及沪深300跌破防守线/突破进攻线信号。
   - 调查每条预警卡片下方交互式快捷动作按钮的实现方案（支持一键跳转 Tab 2 调仓并自动锁定未满 7 天标的或生成阶梯止盈减仓单）。
4. 约束与红线：
   - 严禁修改裁判文件（judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py）。
   - 作为只读 Explorer，绝对不要修改或编写任何源码，只需深入探索与输出分析报告。
