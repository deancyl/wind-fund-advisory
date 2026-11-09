## 2026-11-09T06:56:37Z

You are explorer_g13_survey_2, a teamwork_explorer.
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g13_survey_2\
You MUST read the user's original request file before starting:
d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Also refer to external audit files if helpful:
c:\Users\deanc\Downloads\agy2_ui_ux_audit_and_fix_plan (1).md
c:\Users\deanc\Downloads\agy2_fundadvisory_5_screenshots_diagnosis_and_fix.md

Your mission is technical exploration and concrete plan formulation for Pain Point 2 & 3 and Pain Point 5:
1. Pain Point 2 & 3 (彻底砍除所有伪交易按钮、重构全宽投顾提示栏与移出5大臃肿模块):
   - In `app_gui.py`:
     - Locate `col_wing_btn` and `btn_master_action_switch` ("查看锁仓保护 / 查看今日调仓单 / 检视持仓账本"). Plan to remove them completely and expand the advisory expander to 100% full width (killing the right white space).
     - Formulate the text for the advisory expander: "今日投顾参谋：持仓含 2 只未满 7 天标的，赎回需扣 1.5% 惩罚费，调仓算法已自动为您避开卖出 ｜ 点击展开市场机会与持仓体检".
     - In right-wing sentry: locate "一键批量锁定这2只标的调仓下界" button and per-card buttons ("择机置换", "平衡赛道敞口", "穿透到底层"). Plan their removal, converting the right-wing sentry to a clean buttonless list of 1-3 core risk tips & recommendations.
     - In left-wing sector cards: locate 3 "+ 入备选池" buttons, plan their removal and direct display of fund name & code.
     - In `render_dual_wing_advisory_dashboard`: locate the 5 bloated nested modules:
       ① 历史三大牛熊拐点实盘对照尺: remove from dual-wing dashboard; inspect its usage in Tab 1 smart DCA mode and fix width/layout to prevent text overlap.
       ② 查看全市场 14 大赛道量化温度计总表
       ③ 场内ETF与场外联接 14:45 尾盘折溢价套利感知
       ④ 50ETF与300ETF认沽期权隐含波动率防暴跌哨
       ⑤ 跨境QDII溢价与外汇期货锁汇成本套利精算
       Map out exact plan to migrate ②-⑤ into Tab 4 "穿透工具" secondary sub-tabs.
       Ensure dual-wing expander expanded view contains only "左翼 Top 3 赛道卡 + 右翼极简风险提示列表", with height <= 220px.
2. Pain Point 5 (全宽四宫格大胶囊主导航栏CSS改造 & 删除Tab内重复巨型标题):
   - Inspect main navigation tabs container in `app_gui.py`. Find the CSS styling injection block.
   - Design precise CSS selectors and rules for:
     `[data-testid="stMainBlockContainer"] > div > div > [data-testid="stTabs"] > [data-baseweb="tab-list"]` (grid, 4 cols, 100% width, 10px gap, padding 6px, border-radius 10px, background var(--bg-elevated))
     Top main tab buttons: height 46px, font-size 16px, font-weight 700, border-radius 8px, background var(--bg-surface), border 1px solid var(--border-subtle)
     Active state `button[aria-selected="true"]`: background var(--accent-primary), color #ffffff, box-shadow, span/p text forced #ffffff.
     Ensure Tab 4's secondary sub-tabs are strictly distinguished from primary main tabs.
   - Locate and plan removal of duplicate `st.subheader("🌱 新资建仓")`, `st.subheader("💼 持仓调仓")`, `st.subheader("📈 组合回测")`, `st.subheader("🔍 穿透工具")` and captions.
   - In Tab 4: merge "选择穿透体检组合对象" and "当前体检组合成分档案" into a single compact top summary row.

Hard constraints:
- You are read-only. Do NOT modify source code files.
- Produce your comprehensive report at:
  d:\Google\Workspace\Wind\.agents\teamwork\explorer_g13_survey_2\handoff.md
- Report your findings back via send_message.
