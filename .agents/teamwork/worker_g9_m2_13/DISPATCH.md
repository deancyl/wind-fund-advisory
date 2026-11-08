## 2026-11-08T06:36:44Z
You are worker_g9_m2_13, a versatile implementation and QA worker.
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\worker_g9_m2_13\

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

MANDATORY INSTRUCTION:
You MUST read the authoritative user request at:
d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
and the scope document at:
d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_13\SCOPE.md
Also study the comprehensive survey and line-by-line recommendations from explorer_g9_survey_2 at:
d:\Google\Workspace\Wind\.agents\teamwork\explorer_g9_survey_2\handoff.md
And reference files:
- c:\Users\deanc\Downloads\agy2_fundadvisory_ui_architecture_evaluation.md
- c:\Users\deanc\Downloads\agy2_app_gui.md

### Exclusive Write Ownership:
You own `d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py` exclusively.
You may also create or update test files under `tests/` if needed to add G9 UI tests.
STRICT PROHIBITION:
- NEVER modify the four read-only referee files: `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`.
- NEVER modify `DataLoader.simulate_execution` signature or default fee logic.
- NEVER modify global `c:\Users\deanc\.gemini\GEMINI.md`.

### Your Task: Milestone 2 (M2) — GUI 交互降噪、HTML 纯化与傻瓜化操作流重构 (app_gui.py)
1. 彻底修复大屏裸露 HTML 代码块缺陷（Rule 27）：
   - 首屏“全市场优选赛道 · Top 3 优选自选”下方，“历史三大牛熊拐点实盘对照尺”（render_historical_inflection_ruler_html）以及全站所有富文本 HTML 组件，强制使用 `_clean_html(...)` 剥离每行首尾空格与空行。
   - 清理全站 20 余处直接绕过 safe_markdown_html 的裸调 `st.markdown(..., unsafe_allow_html=True)`（如第 2955、2985-2992、3002-3014、3044-3056、3554、4221-4228 等），全部收口至 `safe_markdown_html`，彻底杜绝 CommonMark 4+ 空格缩进导致的原始 HTML 源码泄露，确保全屏零代码泄露。
2. 首屏双翼看板瘦身与今日一句话傻瓜行动总开关：
   - 在双翼看板展开容器顶端提炼渲染一条高辨识度的“今日投顾行动总开关”：基于 ActiveRiskSentry 预警与持仓状态，用一句大白话告诉用户今天到底要不要操作（例如 🟢 今日建议：按兵不动安心吃息 或 🟡 今日建议：14:30 尾盘有 1 项免赎置换机会 或 🔴 锁定防御 或 🚀 空仓建仓），并配上一键直达对应工作区的按钮（结合 pending_cross_tab_jump 平滑跳转）。
   - 双翼看板左翼默认仅展示精炼市场脉搏与 Top 3 优选赛道卡片（展示今日实时涨跌、动态量化推荐依据与优选基金代码）；14 大赛道温度计总表与基因进化 60 日轨迹图保持在折叠框或 Popover 内按需查看。
   - 右翼预警哨容器高度自适应（`min-height: 380px; height: auto !important`），移除开发口号尾缀，杜绝容器固定 380px 造成的双重滚动条与文字截断。
3. Tab 1 新资建仓：参数 AI 智能托管与一键直出全案：
   - 简化步骤一前置输入：在 L1 默认层，用户只需设定“拟投资总本金”（带中文万元防错核对）与“期望目标收益/风险档位”（C1 至 C5 单选），系统根据当前宏观同温层自动托管匹配最优量化定权模型（如鲁棒双核 HRP）、优选基金只数（默认 6 只）、持有期与限购过滤。
   - 在旁边提供“⚙️ 机构级模型与参数微调（已智能托管）”折叠面板，点开即可自由调整 7 大定权模型、3 至 15 只基金数量与风险测评问卷。
   - 推演与生成建仓单合流提速：主操作按钮默认一键完成量化推演并直接展示底部的实盘建仓执行单与一键复制下单小抄，免去用户先点步骤二再滑到底部点步骤三的二次点击（保留测试依赖的按钮 key 兼容）。
   - 收敛步骤二的 16 张卡片轰炸：在 L1 默认层，仅并排展示最核心的 3 张人话结论大卡（预期达标胜率与年化票息安全垫、最坏回撤金额与最长水下回本天数、攻防仓位分配逻辑）；将历史三大黑天鹅承压卡片、10,000 次蒙特卡洛块重采样 CVaR 面板、2.8 万只六维选基漏斗评分表统一收进带关键指标摘要标题的“🔬 展开机构级量化压力测试与选基白盒证据”折叠面板中，让页面垂直长度缩短 60%。
4. Tab 2 持仓调仓：首屏极致降噪与极速录基弹窗化：
   - 合并顶部概览卡与安全垫看板：将 4 张资产概览卡与浮盈安全垫破净临界点浓缩为紧凑的顶栏看板，将 -3%、-5%、-10% 三级大盘急跌承压卡片收进看板内的可展开详情中，消除首屏大面积色块堆叠。
   - 将原本占据整行的 5 列极速录基吧台改造为持仓明细表上方工具栏中的“➕ 极速录基”Popover 弹出框（保留 bar_fund_input, bar_amt_input, bar_pnl_input, bar_dur_choice, btn_bar_add_holding 控件 key），平时完全不占用垂直高度，点击即弹、录完即合。
   - 严格落实双视图物理隔离：在“持仓诊断与智能调仓”主模式下，绝不渲染底部的账本工具坞；仅当切换至“账本运维与实盘复盘档案”模式时，才在主画布平铺展示粘贴导入、FIFO 批次透视、实盘净值与 Brinson 复盘账单、T+1 对账及同公司转换模块。清理全页重复出现的免折腾缓冲带滑块（全页仅保留 `tab2_rebal_buf_slider` 唯一滑块与 `# tab2_rebal_buf_slider_bot` 兼容注释）。
5. 保证测试套件 100% 兼容：
   - 必须保留现有测试依赖的关键 session_state 键名与函数入口：
     `active_ledger_id`, `active_tier_val`, `mlm`, `pm`, `slider_target_return`, `tab1_step_reached`, `tab1_trigger_sim`, `tab2_diag_cache`, `tab2_diagnosed`, `tab2_rebal_cache`, `tab2_rebalanced`, `target_return_val`, `tab1_num_funds`, `tab1_model_type`, `custom_fund_overrides`, `purchase_limit_filter`.
   - 运行测试套件验证：
     `pytest tests/test_infra.py`
     `pytest tests/test_sidebar_remodel_and_bugfixes.py`
     `pytest tests/test_g8_ux_and_realtime_fusion.py`
     `pytest tests/test_gui_multi_ledger_stress.py`
     `pytest tests/test_challenger_g9_m2_adversarial.py`
     `pytest tests/test_g9_causal_brinson_and_suitability.py`
