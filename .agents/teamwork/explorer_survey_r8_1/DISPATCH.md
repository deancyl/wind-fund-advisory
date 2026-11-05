# Dispatch: Explorer Survey R8-1
Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r8_1\
Original Request: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Target: R1 - 侧边栏核心指数行情走廊与全市场自由定制

## 2026-11-05T01:37:33Z
You are Explorer Survey R8-1.
Your working directory is d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r8_1\.
Read the original user request at: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md.
Also review the project rules at: d:\Google\Workspace\Wind\GEMINI.md.

YOUR FOCUS: Requirement R1 - 升级侧边栏核心指数行情走廊与全市场自由定制
1. 样式与实时点位获取：
   - 调查 app_gui.py 中的样式表，核实 .val-very-low, .val-very_low 与 .val-very-high, .val-very_high 类名定义及使用位置。
   - 调查 fetch_custom_realtime_indices 与 fetch_batch_realtime_indices 在 data_loader.py / app_gui.py / advisory_engine.py 中的实现：如何使用东财/新浪批量实时接口获取真实盘中点位、涨跌额与涨跌幅；非交易时段如何基于本地最新两个交易日收盘价（如 data/aligned_matrix_total_return.parquet 或本地缓存）计算真实涨跌幅，杜绝整排 0.00% 假平盘。
2. 丰富卡片 3 层专业指标：
   - 调查每张侧边栏指数卡片的渲染逻辑（HTML / CSS / DOM 结构）：
     - 第一行：指数名称、代码、最新点位与涨跌幅胶囊（遵循 Flexbox 物理防压扁规则，禁止折行）；
     - 第二行：真实 PE/PB 历史分位数标签与近 20 日涨跌幅；
     - 第三行：均线趋势状态（如：站上 MA20 偏离 +1.5% 或跌破 MA20 防守）。
   - 检查对应的数据指标来源与计算函数。
3. 全市场指数/ETF 自由定制：
   - 调查现有内置指数列表，规划扩充至 30 只以上（覆盖宽基、红利、科技、医药、消费、金融、新能源、军工、港股、美股、黄金、国债等），明确标准代码与名称映射（遵循基准代码真实性铁律，如中证红利 000922 严禁混淆为上证红利 000015）。
   - 调查侧边栏右上角设置弹窗交互机制：展示数量滑块（3 至 15 只）、全市场多选检索列表（支持名称/代码/拼音首字母检索，按勾选顺序排列）、任意 6 位代码实时接入输入框（校验真实名称与行情并加入走廊）。
   - 调查自选配置持久化文件 data/cache/custom_watchlist.json 的结构与读写逻辑。
4. 约束与红线：
   - 严禁修改裁判文件（judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py）。
   - 作为只读 Explorer，绝对不要修改或编写任何源码，只需深入探索与输出分析报告。

Write your detailed findings to d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r8_1\analysis.md and write a standard handoff report to d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r8_1\handoff.md. When finished, send a message to the orchestrator.
