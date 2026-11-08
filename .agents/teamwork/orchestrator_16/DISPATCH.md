# Task Assignment: Project Orchestrator Gen 2 (orchestrator_16)

## Identity
- Archetype: Project Orchestrator (orchestrator_16, generation 2)
- Working directory: `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_16\`
- Parent Agent Conversation ID: `b8ca5e6a-3eb7-49b1-84a9-fa00c4c28e15` (YOUR PARENT — use this ID for all escalation and status reporting)
- Predecessor: `orchestrator_15` (conversation ID: `c6b4ebd0-c5f1-4175-8ba5-3bd0979b970d`)

## Context & Inputs
- Handoff from Predecessor: `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_15\handoff.md`
- Predecessor Briefing: `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_15\BRIEFING.md`
- Predecessor Progress: `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_15\progress.md`
- Predecessor Gate Status: `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_15\GATE_STATUS.md`
- Project Milestone Document: `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_15\PROJECT.md`
- Authoritative User Request: `d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md`

## Completed Milestones
- Phase 0: Survey & Codebase Exploration [DONE]
- Milestone 1: Top Area & Tab 1 Three-Block Refactoring [DONE - Gate PASS]
- Milestone 2: Tab 2 Three-Block Refactoring [DONE - Gate PASS]
- Milestone 3: Test Suite Alignment & Invariant Verification [DONE - Gate PASS]

## Remaining Milestones to Execute
1. **Milestone 4: Service Restart & Browser Visual Inspection**
   - Terminate old 8501 port process cleanly.
   - Launch Streamlit service in silent background mode (`py -3 -m streamlit run AGY2_FundAdvisory/app_gui.py --server.port 8501 --server.headless true`).
   - Probe `http://127.0.0.1:8501/_stcore/health` for HTTP 200.
   - Use `/browser` to visit `http://localhost:8501` and take multi-modal screenshots:
     - Verify first screen (zero scroll) shows top 4 cards (82px) + wing expander + Tab 1 input/plan.
     - Switch to Tab 2 and verify top bar + holdings table in first screen.
     - Verify Light and Dark mode.
     - Verify 640px mobile viewport (no overflow, no clipping).
2. **Milestone 5: Hygiene, Versioning, Victory Audit & G12 Directive Generation**
   - Run full regression suites: `pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py` (ensure 100% green).
   - Ensure clean data files: `data/ledgers_index.json` only tracks `main_live`, clean any temporary scripts (e.g. `scripts/refactor_tab1_modules.py`).
   - Update `GEMINI.md` and `PROGRESS_LOG.md` in workspace root (G11 three-block rules & permanent bracketed slashCommand tag format invariant).
   - Git commit G11 development progress and tag `v4.1-G11` (`git tag -a v4.1-G11 -m "..."`).
   - Push to origin (`git push origin HEAD` and `git push origin --tags`). Zero GitHub releases.
   - Dispatch independent Victory Auditor (`victory_auditor`) to verify all acceptance criteria.
   - Output G12 generation directive with strict bracketed slashCommand tags.


## 2026-11-08T15:00:46Z

启动 G12 世代风控断路纠偏、突发事件基因编程规则树进化、移动止盈逃顶与多源先行指标感知闭环任务

一、 核心安全底线与反作弊契约
1. 严禁修改四个只读裁判文件 judge_engine.py、holdout_vault.py、AGENT_SPEC.md、tests/test_infra.py，严禁修改 DataLoader.simulate_execution 的默认函数签名与默认扣费逻辑。
2. 严禁使用伪随机数、线性插值伪序列或静态保底常数伪造金融指标，夏普比率必须强制扣减 2.0% 年化无风险利率，严格遵循 T 日信号 T+1 日确认交割铁律。
3. 严守三块式极简干练 UI 架构，所有新增专业能力必须无缝融入现有三块式布局与白盒抽屉中，严禁在主界面重新堆砌冗余横幅或卡片。

二、 第一阶段：修复四大代码断路 Bug 并升级真赚钱风控、多源感知与突发事件 GP 进化引擎

1. 修复首屏与风控引擎的 4 处代码断路 Bug（修改 app_gui.py 与 advisory_engine.py）
第一，修复右翼相关性突变预警卡假死 Bug。在 app_gui.py 第 1480 行附近，将错误的键名判断 corr_eval_res.get("is_mutation_alarm") or corr_eval_res.get("is_regime_shift_risk") 修正为底层真实返回的键名 corr_eval_res.get("is_triggered") or corr_eval_res.get("is_liquidity_shift_triggered")，确保相关性突破 0.75 或 0.80 时能真实渲染预警卡。
第二，修复首屏 inspect_portfolio 漏传参数导致维度 8 与维度 9 失效的 Bug。在 app_gui.py 调用 sentry.inspect_portfolio 的所有位置（含第 1281 行附近），必须显式传入 investor_risk_tier=st.session_state.get("active_tier_val", "C3")，并将当前持仓基金的实时估值字典 fund_quotes 注入 snapshot_dict，使投资者适当性越界预警（维度 8）和盘中异动安全垫实时消耗传导（维度 9）在首屏真实生效。
第三，校准指数与 ETF 联接基金的盘中实时估值精度。在 portfolio_manager.py 的 fetch_realtime_fund_quote 与盘中预估盈亏计算中，若持仓标的为指数基金或 ETF 联接基金，优先结合其对应基准指数或场内 ETF 的实时涨跌幅（联接基金乘以 0.95 仓位系数）校准 gszzl，消除季报滞后重仓股带来的估算偏差。
第四，修正 Tab 1 智能定投乘数的标的对齐。在 app_gui.py 调用 SmartExecutionDCAEngine.plan_smart_dca 时，结合所选建仓组合内各基金自身真实的加权 MA20 乖离率与 ERP 分位计算当期定投乘数，而非仅用沪深 300 单一指数替代。

2. 实装高点回落移动止盈（Trailing Stop-Profit）与右侧破位逃顶机制（修改 advisory_engine.py）
在 ActiveRiskSentry.inspect_portfolio 的维度 4 中，解决原逻辑仅在 bias_20 大于 5% 时才提示止盈、一旦大阴线跌破均线反而停止提示导致坐过山车的缺陷：
第一，新增右侧趋势破位止盈：当持仓标的累计浮盈大于等于 10%，且最新净值或盘中实时估值跌破 20 日均线（bias_20 小于 0）且均线斜率转负或单日急跌超 1.5 倍日均波幅时，立即触发红色右侧破位锁利预警，提示果断兑现 50% 浮盈仓位防止利润回吐。
第二，新增高水位浮盈回撤保护：基于持仓标的近 60 日净值最高点测算浮盈回吐幅度，当盈利丰厚标的从阶段最高点回撤超过阈值时，主动发出移动止盈提醒。

3. 扩充多源实时先行指标与本地日线缺口自动增量补齐（修改 data_loader.py 与 advisory_engine.py）
第一，实装本地日线底座轻量级增量自愈。当检测到本地指数或赛道日线 parquet 最新日期落后于当前最新已收盘交易日时，自动通过实时/历史日 K 线接口拉取缺失的最近交易日收盘价并拼接到序列中，消除均线与波动率计算的日期断层。
第二，扩充多维实时市场感知渠道。在 data_loader.py 中新增采集并计算：① 14 大赛道核心场内 ETF 的盘中实时量能放量比（Volume Surge Ratio）与折溢价率；② 宏观跨市场先行指标（10 年期国债收益率最新水位、黄金与海外纳指隔夜/盘中联动信号）；③ 聚合多条过滤后的 A 股核心财经快讯，量化计算今日全市场多空情绪温度得分（0 至 100 分），在首屏双翼看板的晨报折叠区清晰呈现。

4. 升级应对突发黑天鹅事件的在线基因编程（GP）与启发式规则树引擎（修改 advisory_engine.py 与 app_gui.py）
将 OnlineHeuristicFactorEvolver 从单纯的静态历史 4 维线性权重搜索，升级为实时感知盘中突发异动的混合启发式基因编程引擎：
第一，实时截面注入：在 _extract_sector_price_matrix 与 _build_factor_tensor_and_returns 中，支持将今日盘中实时最新价格融合至序列末端，使基因演化能够立即感知今日盘中的突发暴涨、暴跌或波动率激增。
第二，非线性突发事件规则基因编码：将染色体扩展为 7 维基因向量，除估值、动量、信噪比、反拥挤 4 维权重外，新增编码 3 个启发式事件应对算子基因：① 自适应动量窗口基因（在 5 日敏锐捕捉与 20 日稳健趋势间动态加权）、② 波动率脉冲惩罚基因（当某赛道近 5 日波动率除以 60 日波动率突破演化阈值时自动指数级衰减其得分）、③ 突发急跌避险切换算子（当全市场盘中突发宽幅下挫时自动提升纯债与黄金压舱石得分权重）。
第三，在双翼看板的 🧬 因子进化 Popover 中，新增展示当前启发式 GP 引擎识别到的市场突发状态模式（如平稳蓄势态、波动率脉冲态、左侧恐慌错杀态）以及自动演化生成的最优应对算子规则表达式。

三、 第二阶段：强制重启服务并调用 /browser 启动多模态视觉与实盘仿真走查闭环

完成上述代码修改后，必须先彻底终止旧的 8501 端口进程并清理缓存，重新启动最新服务，随后调用 /browser 打开 http://localhost:8501 逐页核查：
1. 核查三块式极简布局是否保持完美：确认首屏无需滚动即可直接操作四大主工作区 Tab，确认无任何重复按钮、套娃横幅或断字换行。
2. 核查新增专业内核展示：展开双翼看板与 🧬 因子进化弹窗，确认突发状态识别、启发式规则表达式、多源先行指标与情绪温度真实渲染；确认右翼预警哨已能正确响应适当性越界、移动止盈与盘中异动传导。
3. 核查 1920x1080 桌面端与 640px 移动端视口在亮色及彭博暗黑主题下的视觉表现，确保零文字重叠、零水平溢出。

四、 第三阶段：全量测试验证、Git 归档与生成 G13 世代指令（防转义锁死命令标签格式）

1. 运行全量自动化测试套件（包含 pytest tests/test_infra.py、tests/test_adv_final_closure.py、tests/test_g3_evolution_loop.py、tests/test_gui_multi_ledger_stress.py），并在测试套件中新增针对移动止盈破位预警、首屏适当性与盘中异动参数穿透、突发事件 GP 7 维规则演化的专项测试，确保 100% 绿灯通过。确认四个只读裁判文件零修改，确认 data/ledgers_index.json 仅保留主实盘账本，清理所有临时脚本。
2. 将 G12 世代经验规范更新写入当前工作区根目录 GEMINI.md 与 PROGRESS_LOG.md，严禁触碰全局配置文件。
3. 执行 Git 提交与标签同步：运行 git add -A，运行 git commit 记录 G12 开发进程，使用 git tag -a 打上版本标签 v4.2-G12，最后运行 git push origin HEAD 与 git push origin --tags 同步至 GitHub 远端。严格遵守禁令：绝对禁止创建任何 GitHub Release。
4. 在最终报告末尾输出供下一轮直接复制执行的 G13 世代进化指令。
【极其重要的防客户端转义门禁警告】：
注意！由于客户端输入框在向你传递提示词时，会自动将 Markdown 链接形式的命令标签转义显示为类似 左方括号+slashCommand:+斜杠+命令名+右方括号 的内部格式，你在最终报告中输出 G13 指令时，绝对禁止照抄这种带冒号的内部转义格式！
你输出的 G13 指令中的四个命令标签，必须 100% 严格按照以下字符序列拼接输出（中间用英文分号而非冒号）：
- goal 命令必须输出为：左方括号 + /goal + 右方括号 + 左圆括号 + slashCommand;goal + 右圆括号，即 [/goal](slashCommand;goal)
- boost 命令必须输出为：左方括号 + /boost + 右方括号 + 左圆括号 + slashCommand;boost + 右圆括号，即 [/boost](slashCommand;boost)
- teamwork 命令必须输出为：左方括号 + /teamwork + 右方括号 + 左圆括号 + slashCommand;teamwork + 右圆括号，即 [/teamwork](slashCommand;teamwork)
- browser 命令必须输出为：左方括号 + /browser + 右方括号 + 左圆括号 + slashCommand;browser + 右圆括号，即 [/browser](slashCommand;browser)
内审与外审代理在终审时必须检查最终报告文本：凡是报告末尾的 G13 指令中出现了带冒号的 slashCommand: 字样，一律判定格式违规打回重写！其余正文保持纯文本无特殊符号排版，包含全量测试验证、Git Commit 与 Git Tag 同步（禁止创建 Release）以及继续按上述精确格式生成下一代指令的自举要求。 除此以外，严格参考审计文件：c:\Users\deanc\Downloads\agy2 (1).md 以及 c:\Users\deanc\Downloads\agy2_fundadvisory_deep_code_diagnosis.md
