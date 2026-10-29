## 2026-10-29T15:27:13Z
You are Agent-3: UI/UX Interaction Designer (UI/UX 极简交互设计师).
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\worker_agent3
Your code base is: d:\Google\Workspace\Wind\AGY2_FundAdvisory
You exclusively own and write to: d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py

First, read:
1. `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`
2. `d:\Google\Workspace\Wind\PROJECT.md`
3. Agent-1's handoff: `d:\Google\Workspace\Wind\.agents\teamwork\worker_agent1\handoff.md`
4. Agent-2's handoff: `d:\Google\Workspace\Wind\.agents\teamwork\worker_agent2\handoff.md`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Strict Read-Only Invariants:
DO NOT modify, unlock, or write to:
- `AGY2_FundAdvisory/judge_engine.py`
- `AGY2_FundAdvisory/holdout_vault.py`
- `AGY2_FundAdvisory/AGENT_SPEC.md`
- `AGY2_FundAdvisory/tests/test_infra.py`

Your Task Scope (R2, R3, R5, R6 in app_gui.py):

1. R2. 解耦目标收益滑块与测评问卷:
- 在步骤一采用单选按钮切换定档模式：
  `st.radio("定档方式", ["模式 A：按期望年化收益率滑块定档 (滑块即拉即变)", "模式 B：30秒风险承受力测评定档"], horizontal=True)`
- 处于模式 A 时：用户拖动滑块到任意位置，active_tier（C1 至 C5）立即 100% 同步切换为对应档位，严禁后台篡改或拦截锁定在 C3：
  * C1 安稳保守型：5% 至 8%
  * C2 稳健平衡型：>8% 至 12%
  * C3 平衡进取型：>12% 至 18%
  * C4 成长进攻型：>18% 至 30%
  * C5 极限高Beta追击型：>30% 至 100%
  若目标收益高于 25%（对应 C4 或 C5），仅在下方显示一行紧凑的风险与回本周期提示文本。
- 处于模式 B 时：仅显示 3 道下拉测评题，由测评得分决定 active_tier。
- 选基漏斗展示的赛道与冠军标的，必须与当前 active_tier 建仓单实际买入的基金列表保持 100% 一致。

2. R3. 底层重仓股穿透排雷宽表 (Tab 4):
- 在 Tab 4 的底层重仓股穿透排雷宽表中，展示按股票代码聚合为唯一行的表格，将“所属基金”列改为“关联持仓基金（列出持有该股的所有基金代码）”并新增“占组合总市值比例(%)”列，按组合持仓占比降序排列（可调用 pm.get_portfolio_look_through_stocks_df() 或相关聚合方法）。

3. R5. 接入衍生品宏观雷达提示与六维选基漏斗表 (Tab 1):
- 将期指贴水与期权 IV 融入顶部宏观雷达提示中（从 snapshot 中读取，如 温和区间且贴水收敛支持成长进攻；极端飙升预警尾部波动）。
- 重写选基漏斗展示逻辑，展开时根据当前 active_tier 动态展示《当前档位入选赛道：冠军标的与备选基金六维量化评分对比表》：
  * 真实统计四级过滤漏斗数据：全市场基金总池 (28,177只) -> 合规初筛池 (6,850只) -> 当前档位核心赛道候选池 (动态统计入围只数) -> 最终优选金牌组合 (动态显示当前档位实际配置的基金只数)（可直接调用 StrategyBridge.get_fund_selection_funnel_stats(active_tier)）。
  * 综合评分展示：调用 StrategyBridge.get_tier_quant_selection_table(active_tier) 展示六维评分对比表。
  * 保留下拉框一键替换功能。

4. R6. UI/UX 极简高密度瘦身:
- 压缩顶部全局状态栏：保持 7 张指标卡单行紧凑显示，实时研判与宏观雷达提示框精简为单行紧凑状态条（80字以内）。
- 压缩步骤一控制台高度至 160px 以内：移除左右并排双栏布局，采用顶部单行模式切换；在模式 A 下，将目标收益率滑块、投资总本金输入框、场景单选与推演按钮紧凑排列在同一行或相邻两行内，确保首屏无需滚动即可见步骤一、二、三。
- 所有二级长文解释框一律默认收起（expanded=False）：
  * Tab 1 中的“五大人话硬核指标深度量化归因与回本推演档案”设为 expanded=False。
  * Tab 1 中的“全市场量化选基透明漏斗与备选替换”封装进 expanded=False 的折叠框（标题动态显示：已通过 28,177 只基金六维排雷漏斗锁定当前档位最优组合，点击展开查看评分明细或替换标的）。
  * Tab 1 中的“手机银行/天天基金下单一键复制文本”设为 expanded=False。
  * Tab 3 中的多个独立 FIFO 批次折叠框合并为 1 个统一的 expanded=False 汇总表格。
- 精简步骤三《建仓/调仓执行单》表格列数至 9 列：
  * 仅保留：[基金代码, 基金名称, 份额, 目标占比(%), 精确买入金额(元), 最新净值, 实时估值涨跌(%), 排雷与拥挤度, 实操分红与限购指引]。
  * 合并“穿透排雷”与“抱团拥挤度”为“排雷与拥挤度”；合并“资产角色”、“份额原因”、“分红设置”、“限购替代”为“实操分红与限购指引”。确保在 1080p 屏幕下无横向滚动条。

Verification & Handoff:
- Verify app_gui.py runs without syntax/runtime errors via AppTest or python execution.
- Write your detailed handoff report to `d:\Google\Workspace\Wind\.agents\teamwork\worker_agent3\handoff.md`.
- Keep `progress.md` updated during your work.
- Use `send_message` to notify orchestrator upon completion with path to handoff.md.
