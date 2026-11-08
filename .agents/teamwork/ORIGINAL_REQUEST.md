# Original User Request

## Parameters

[skip-interview]
How this run was launched; not part of the task.

## Initial Request — 2026-11-07T22:44:54Z

启动 G9 世代量化因果律严苛纠偏、防未来函数样本外滚动演化、真数据防幻觉锚定与 Brinson 归因及适当性主动风控闭环任务

一、 核心安全底线与反作弊契约
1. 严禁修改四个只读裁判文件 judge_engine.py、holdout_vault.py、AGENT_SPEC.md、tests/test_infra.py，严禁修改 DataLoader.simulate_execution 的默认函数签名与默认扣费逻辑。
2. 严禁使用伪随机数、线性插值伪序列或静态保底常数伪造金融指标，严禁破坏现有自动化测试套件的兼容性，确保原有与新增测试 100% 通过。
3. 严格遵循 AGENT_SPEC.md 铁律：严禁任何形式的未来函数，T 日收盘生成的信号只能在 T+1 日及之后产生成交收益，计算夏普比率必须强制扣除 2.0% 年化无风险利率。

二、 第一阶段：落地六大金融量化与风控合规审计整改（P0 至 P2 全量闭环）

1. 修复 P0 致命缺陷：根除 OnlineHeuristicFactorEvolver 中的同日收盘价未来函数、样本内过拟合与线性插值伪轨迹（修改 advisory_engine.py）
第一，消除同日未来函数。在 OnlineHeuristicFactorEvolver 的 _evaluate_population 中，第 t 日基于收盘特征 F[t] 选出的 Top 3 赛道权重 P[t]，必须严格滞后一期作用于第 t+1 日的真实收益率 R[t+1]（即 P[:-1] 对应 R[1:]），严禁拿第 t 日收盘选出的权重去乘第 t 日当天的收益率；同时在合成动态净值序列 nav_dynamic 时，必须从日度组合收益率中真实扣除双边换手摩擦成本（单边按 10 bps 计提），而非仅在适应度打分中扣减。
第二，强制扣除 2.0% 年化无风险利率。在 _evaluate_population 计算夏普比率时，严格按照 AGENT_SPEC.md 要求从日均收益率 mean_r 中减去日化无风险利率（0.02 / 250.0），杜绝纯债赛道凭借极低波动率白嫖虚高夏普。
第三，实装真实的推进式样本外演化轨迹（Walk-Forward Rolling Trajectory）。废除 get_60d_rolling_nav_and_trajectory 中使用 lam = (t + 1) / 60.0 人工线性插值伪造四维权重轨迹的做法，改为在历史窗口上按每 5 个交易日滚动推进演化（每个节点仅使用该节点之前的历史数据求解当期最优权重并用于后续 5 日样本外收益合成），真实记录每一期的四维因子权重变化与样本外净值表现。

2. 修复 P0 致命缺陷：消除缺失数据线性牛市假序列、修正跨市场交易日对齐与 85 日短窗估值错配（修改 advisory_engine.py）
第一，在 _extract_sector_price_matrix 中，以 A 股交易日历（H00300 日期序列）为基准索引，将 14 大赛道的价格序列按交易日期严格对齐（使用 reindex 与前向填充 ffill），彻底解决美股、港股、黄金与 A 股因节假日不同直接按尾部条数 column_stack 导致的日期错位问题。
第二，彻底废除 advisory_engine.py 第 235 行缺失数据时使用 np.linspace(1.0, 1.05, window_days) 伪造零回撤单边上涨直线的做法；若某赛道数据经多级回退仍缺失，将其收益率设为 0 并标记数据缺失状态，严禁伪造虚假高夏普序列。
第三，在 _build_factor_tensor_and_returns 中计算估值分位得分 s_val 时，改为基于长周期年线去趋势中枢或真实估值缓存计算，严禁仅用 85 天短窗口价格高低冒充长期估值分位数。

3. 修复 P0 致命缺陷：清除 ActiveRiskSentry 中 2.5 亿元默认假规模兜底，实装真实规模反查与未知状态告警（修改 advisory_engine.py）
在 ActiveRiskSentry.inspect_portfolio（第 997 至 1015 行）中，当传入的 fund_metadata 缺少某基金规模字段时，必须主动调用 DataLoader.get_fund_metadata 或从 CORE_STRATEGY_POOL 与 EXTENDED_FUND_CATALOG 中穿透反查真实规模；若反查后仍无规模数据，必须将其标记为规模待核验状态并输出提示，严禁使用 else: aum = 2.5 静默赋予 2.5 亿元安全规模掩盖迷你基清盘风险。

4. 修复 P1 缺陷：盘中最后一根 K 线真实重算、动态量化证据链生成与快讯信源验真（修改 data_loader.py、advisory_engine.py 与 app_gui.py）
第一，在 OpportunityRadarEngine.evaluate_sector 中，废除 bias_20 = round(bias_20 + chg_pct, 2) 的粗暴算术相加；当融合盘中实时涨跌幅时，将实时最新价更新至价格序列末尾，精确重算盘中实时 MA20、Bias20、Slope20 与考夫曼信噪比 ER20。
第二，实装动态量化证据链合成器。在 evaluate_sector 中，结合该赛道当前的真实估值分位、动量斜率、信噪比与反拥挤度得分，动态生成与量化指标方向 100% 自洽的入选依据文案（例如明确指出估值分位、趋势信噪比及乖离率安全边际），并在首屏 Top 3 赛道卡片中完整披露四维子项得分（估值、动量、信噪比、反拥挤）以及 20 日年化波动率与最大回撤风险指标，实现风险与收益对称展示。
第三，在 fetch_realtime_market_news_and_catalysts 与首屏晨报展示中，明确区分实时联网抓取快讯（标注具体信源名称与原始发布时间）与离线本地缓存快照（标注离线缓存状态与快照保存时间），严禁在离线兜底时用 datetime.now() 冒充实时抓取时间。

5. 修复 P1 与 P2 缺陷：实装投资者适当性越界主动预警、盘中异动传导与调仓复盘 Brinson 归因（修改 portfolio_manager.py、advisory_engine.py 与 app_gui.py）
第一，在 ActiveRiskSentry.inspect_portfolio 中新增投资者适当性匹配与组合级止盈止损巡检维度：结合当前账本设定的风险等级（C1 至 C5），检测实盘持仓的权益资产占比与组合波动率是否越界超配（如 C1 保守型持仓高比例权益或高波科技基金），一旦越界立即发出主动预警并提供一键降波纠偏动作；同时检测当前盘中实时估值异动（单基涨跌超 2% 或组合波动超 1%）对安全垫的实时消耗传导。
第二，在 PortfolioManager.evaluate_rebalance_audit 与 Tab 2 账本运维复盘档案中，实装 Brinson 超额收益归因拆解：将主动调仓净增厚精确拆解为大类资产配置效应（Allocation Effect）、优选基金超额效应（Selection Effect）与交易摩擦及惩罚费规避贡献（Friction Saving），提升买方投顾复盘的专业深度。

三、 第二阶段：强制重启服务并调用 /browser 启动多模态视觉与量化逻辑走查闭环

完成上述代码修改后，必须先彻底终止旧的 8501 端口进程并清理缓存，重新启动最新服务，随后调用 /browser 打开 http://localhost:8501 逐项核查真实渲染画面与数值逻辑：
1. 核查首屏双翼看板：展开基因进化弹窗，确认 60 日样本外滚动净值与演化轨迹真实合理；核查晨报信源状态与 Top 3 赛道卡片的四维完整子项得分、动态量化依据及风险指标；核查右翼预警哨是否包含适当性检验与真实规模排雷。
2. 核查 Tab 1 与 Tab 2：验证主流程与宽屏运维工具坞物理隔离、未保存修改自动保护、大额本金中文数量级提示、覆盖账本二次确认以及运维档案中的 Brinson 三维归因账单。
3. 核查全站亮色、彭博暗黑主题及 640px 移动端视口：确认所有图表、热力图、四象限图与表格零文字重叠、零半截名称、零水平溢出。若在 /browser 截图中发现任何瑕疵，当场修改代码并重新截图确认。

四、 第三阶段：全量测试验证、Git 版本归档与生成 G10 世代指令

1. 运行全量自动化测试套件（包含 pytest tests/test_infra.py、tests/test_adv_final_closure.py、tests/test_g3_evolution_loop.py、tests/test_gui_multi_ledger_stress.py），并在测试套件中新增针对基因演化防未来函数因果探针、夏普扣减无风险利率、缺失规模反查、投资者适当性越界预警及 Brinson 归因的专项测试，确保 100% 通过。确认四个只读裁判文件零修改，确认 data/ledgers_index.json 仅保留干净的主实盘账本，清理所有临时脚本。
2. 将 G9 世代量化审计整改成果更新写入项目根目录 GEMINI.md 与 PROGRESS_LOG.md，严禁触碰全局配置文件。
3. 执行 Git 提交与标签同步：运行 git add -A，运行 git commit 记录 G9 世代开发进程，使用 git tag -a 打上版本标签 v3.9-G9，最后运行 git push origin HEAD 与 git push origin --tags 同步至 GitHub 远端。严格遵守禁令：绝对禁止创建任何 GitHub Release。
4. 在最终报告末尾，基于你在本轮真实体验和 /browser 视觉走查中发现的下一个最能提升系统量化实战胜率、极端风险预判或交互体验的痛点，输出一段供下一轮直接复制执行的 G10 世代进化指令。你输出的 G10 指令必须满足以下要求：
第一，直接以 /goal /boost /teamwork 开头，并在走查环节包含 /browser 调用；
第二，全文保持纯文本干净排版，不要使用任何表情符号、星号、反引号、数学公式符号或装饰性分隔线；
第三，严禁脱离中国公募基金实盘制度编造伪概念，严禁只写后端不接前端；
第四，包含全量测试验证、Git Commit 与 Git Tag 同步（禁止创建 Release）以及继续生成下一代 G11 指令的自举要求。

外部审计参考文件：
- c:\Users\deanc\Downloads\agy2_fundadvisory_quant_capability_audit.md
- c:\Users\deanc\Downloads\agy2.md

## Follow-up — 2026-11-07T22:46:06Z

[skip-interview] 用户需求与契约规则已在初始 Prompt 中完整定义，请跳过访谈环节，直接批准任务提示词并全速启动执行。


## Approved Task Prompt — 2026-11-08T03:14:40Z

启动 G10 世代多资产相关性压力突变防御、极端流动性冲击动态滑点补偿与大额账本穿透式蒙特卡洛压力测试闭环任务。

Working directory: d:\Google\Workspace\Wind
Integrity mode: development

## Reference Materials
- 核心代码路径：
  - Streamlit GUI 主程序：`AGY2_FundAdvisory/app_gui.py` (端口 8501)
  - 投顾决策与相关性模块：`advisory_engine.py`
  - 组合管理与压力测试：`portfolio_manager.py`
  - 数据加载与执行模拟：`data_loader.py`
  - 裁判防作弊基线：`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`
- 基线版本与状态：v3.9-G9 (commit ba4cda9)，59 项现有自动化测试套件 100% 通过。

## Verification Resources
- 工作区现有 59 项全量自动化测试套件与 4 个只读裁判文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）。
- 测试套件中针对多资产相关性突变预警、流动性冲击折价及蒙特卡洛压力测试新增的专项自动化测试用例。
- 本地 Streamlit 服务端点与健康探针（`http://127.0.0.1:8501/_stcore/health`），配合 `/browser` 工具进行多模态视觉走查。

## Requirements

### R1. 核心安全底线与反作弊契约
- 严禁修改四个只读裁判文件：`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`。
- 严禁修改 `DataLoader.simulate_execution` 的默认函数签名与默认扣费逻辑。
- 严禁使用伪随机数、线性插值伪序列或静态保底常数伪造金融指标；严格遵循 `AGENT_SPEC.md` 铁律，严禁任何形式的未来函数。
- 夏普比率计算必须强制扣减 2.0% 年化无风险利率。
- 严禁触碰全局配置文件 `c:\Users\deanc\.gemini\GEMINI.md`，所有经验规范必须写入当前工作区根目录 `GEMINI.md` 与 `PROGRESS_LOG.md`。

### R2. 相关性压力突变预警与跨资产流动性平移预案
- 在 `advisory_engine.py` 与 `portfolio_manager.py` 中升级相关性压力突变预警机制。
- 当大盘指数急跌时，动态测算红利低波与高 Beta 权益板块的下行协方差突变；若相关系数跳升至 0.80 以上，自动启动跨资产流动性平移预案。
- 流动性平移预案须将高估值与高波标的定向减仓，平移至纯债与实物黄金联接资产。

### R3. 场外公募基金微观执行冲击与底层流动性折价惩罚
- 在 `data_loader.py` 与 `advisory_engine.py` 中升级微观执行冲击模型。
- 针对场外公募基金，结合基金管理人季报披露的前五大重仓股日均成交额与基金规模比例，真实精算大额赎回对底层资产的流动性折价惩罚，杜绝使用单一线性换算。

### R4. 穿透式多周期蒙特卡洛压力测试
- 在 `portfolio_manager.py` 中实装多周期穿透式蒙特卡洛压力测试。
- 基于块重采样（Block Bootstrap），结合投资者风险等级 C1 至 C5，自动输出当前组合在 2008 年金融危机、2015 年流动性踩踏及 2024 年初小盘股流动性危机三大极端情景下的最大回撤预测与流动性变现天数。

### R5. 本地服务平滑重启与多模态视觉走查闭环
- 代码修改完成后，彻底终止旧 8501 端口进程，平滑启动最新服务并核验 `http://127.0.0.1:8501/_stcore/health`。
- 调用 `/browser` 打开 `http://localhost:8501` 逐项核查真实渲染画面与数值逻辑：
  - 核查首屏双翼看板：验证多资产相关性突变预警指示卡与压力测试流动性指标；
  - 核查 Tab 1 与 Tab 2：验证大额订单流动性折价明细表与蒙特卡洛压力测试三维分布图；
  - 核查亮色、暗黑主题及 640px 移动端视口，确认图表、文字与表格零截断、零水平溢出。

### R6. 全量自动化测试验证、Git 版本归档与 G11 指令自举
- 运行全量自动化测试套件，并在测试套件中新增针对多资产相关性突变预警、流动性冲击折价及蒙特卡洛压力测试的专项测试，确保原有与新增测试 100% 绿灯通过。
- 确认四大只读裁判文件零修改；确认数据目录仅保留主实盘账本。
- 将 G10 世代整改成果更新写入工作区根目录 `GEMINI.md` 与 `PROGRESS_LOG.md`。
- 执行 Git 提交与标签同步：运行 `git add -A`，运行 `git commit` 记录 G10 世代开发进程，使用 `git tag -a` 打上版本标签 `v3.10-G10`，运行 `git push origin HEAD` 与 `git push origin --tags` 同步至远端；严禁创建任何 GitHub Release。
- 最终必须通过独立的胜利审计（Victory Audit）确认。
- 在最终报告末尾，基于走查体验输出一段供下一轮直接复制执行的 G11 世代进化指令（保持纯文本干净排版，不使用任何表情符号、星号、反引号、数学公式符号或装饰性分隔线，包含 `/browser` 走查、全量测试与 Git 标签同步自举要求）。

## Acceptance Criteria

### 核心安全底线与防作弊验证
- [ ] 四大只读裁判文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）哈希值未发生变动，零修改。
- [ ] `DataLoader.simulate_execution` 默认函数签名与默认扣费逻辑保持只读。
- [ ] 所有金融指标计算无伪随机数、线性插值伪序列或静态保底常数，无未来函数；夏普比率计算扣减 2.0% 年化无风险利率。
- [ ] 全局配置文件 `c:\Users\deanc\.gemini\GEMINI.md` 零修改；整改成果沉淀于工作区根目录 `GEMINI.md` 与 `PROGRESS_LOG.md`。

### 金融量化与流动性风控核心
- [ ] `advisory_engine.py` 与 `portfolio_manager.py` 成功实装相关性压力突变预警：大盘急跌且红利低波与高Beta权益板块下行相关系数 > 0.80 时，确定性触发流动性平移预案，将高估值高波标的平移至纯债与实物黄金联接资产。
- [ ] `data_loader.py` 与 `advisory_engine.py` 成功实装基于季报前五大重仓股日均成交额与基金规模比例的微观执行冲击折价模型，非单一线性换算。
- [ ] `portfolio_manager.py` 成功实装块重采样蒙特卡洛压力测试，针对 C1 至 C5 风险等级输出 2008、2015、2024 年初三大极端情景的最大回撤预测与流动性变现天数。

### 服务平滑重启与 UI 视觉走查
- [ ] 旧 8501 端口服务彻底终止，新服务平滑启动且 `http://127.0.0.1:8501/_stcore/health` 返回正常。
- [ ] 首屏双翼看板正常显示多资产相关性突变预警指示卡与压力测试流动性指标。
- [ ] Tab 1 与 Tab 2 正常渲染大额订单流动性折价明细表与蒙特卡洛压力测试三维分布图。
- [ ] 在亮色、暗黑主题以及 640px 移动端视口下，图表、文字与表格零截断、零水平溢出。

### 自动化测试、版本归档与 G11 自举
- [ ] 全量自动化测试（含原有 59 项及新增针对相关性突变预警、流动性冲击折价、蒙特卡洛压力测试的专项测试）100% 通过。
- [ ] 数据目录仅保留主实盘账本。
- [ ] 本地 Git 提交完成并成功创建 `v3.10-G10` 注释标签，代码与标签推送至远端 `origin`；无任何 GitHub Release 创建。
- [ ] 独立胜利审计（Victory Audit）通过确认。
- [ ] 报告末尾输出无表情符号、无星号、无反引号、无数学公式符号、无装饰性分隔线的纯文本 G11 世代进化指令。

## Approved Task Prompt — 2026-11-08T05:43:52Z

启动 G9 世代外傻内精渐进式披露交互降噪重构与底层量化因果律严苛纠偏闭环任务，在坚守底层量化模型与风控规则的前提下，重构 Streamlit GUI 为 L1 傻瓜操作层 + L2 机构白盒层并彻底修复 HTML 源码泄露，纠偏因子演化中的未来函数、无风险利率扣除、假序列等问题，完成视觉验收与全量单测归档。

Working directory: d:\Google\Workspace\Wind
Integrity mode: development

## Reference Materials
- 核心代码路径：
  - Streamlit GUI 主程序：`AGY2_FundAdvisory/app_gui.py` (端口 8501)
  - 投顾决策引擎：`advisory_engine.py`
  - 组合管理与风险监控：`portfolio_manager.py`
  - 数据加载与回测执行：`data_loader.py`
  - 四大只读裁判文件：`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`
- 审计参考文档：
  - `c:\Users\deanc\Downloads\agy2_fundadvisory_ui_architecture_evaluation.md`
  - `c:\Users\deanc\Downloads\agy2_app_gui.md`

## Verification Resources
- 自动化测试套件：`pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py` 及针对 G9 交互降噪与量化纠偏新增的专项测试用例。
- 本地 Streamlit 服务端点与健康探针（`http://127.0.0.1:8501/_stcore/health`），配合 `/browser` 工具进行多模态视觉走查。
- 参考审计文档：`c:\Users\deanc\Downloads\agy2_fundadvisory_ui_architecture_evaluation.md` 与 `c:\Users\deanc\Downloads\agy2_app_gui.md`。

## Requirements

### R1. 核心设计哲学、安全底线契约与只读约束
- 实行“外傻内精”原则（L1 傻瓜操作层 + L2 机构白盒层）：绝不阉割任何底层专业量化模型与风控规则，L1 默认视图坚持结论先行、AI 自动托管最优参数、一步直达交易清单；将复杂的参数微调、蒙特卡洛 10,000 次分布、历史黑天鹅明细与选基漏斗大表收纳进 L2 专业白盒折叠抽屉中，做到新手 3 秒无脑跟单、专家一键下钻看透底层证据。
- 严禁修改四个只读裁判文件：`judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py`。
- 严禁修改 `DataLoader.simulate_execution` 的默认函数签名与默认扣费逻辑。
- 严禁破坏现有 50+ 项自动化测试套件的兼容性（保留现有测试依赖的关键 `session_state` 键名与函数入口），确保原有测试与新增测试 100% 绿灯通过。
- 严禁触碰全局配置文件 `c:\Users\deanc\.gemini\GEMINI.md`，所有经验规范必须写入当前工作区根目录 `GEMINI.md` 与 `PROGRESS_LOG.md`。

### R2. 全局交互降噪、HTML 纯化与傻瓜化操作流重构（修改 app_gui.py）
- 彻底修复大屏裸露 HTML 代码块缺陷（Rule 27）：在首屏“全市场优选赛道 · Top 3 优选自选”下方，“历史三大牛熊拐点实盘对照尺”（`render_historical_inflection_ruler_html`）及所有富文本 HTML 组件，强制使用 `_clean_html(...)` 剥离每行首尾空格与空行，并通过统一入口 `safe_markdown_html(...)` 渲染，彻底杜绝 CommonMark 4+ 空格缩进导致的原始 HTML 源码大面积泄露，实现全屏零代码泄露。
- 首屏双翼看板瘦身与今日一句话傻瓜行动总开关：
  - 在双翼看板最上方提炼渲染一条高辨识度的“今日投顾行动总开关”：用一句大白话告诉用户今天到底要不要操作（例如“🟢 今日建议：按兵不动安心吃息”或“🟡 今日建议：14:30 尾盘有 1 项免赎置换机会”），并配上一键直达对应工作区的按钮。
  - 双翼看板左翼默认仅展示精炼市场脉搏与 Top 3 优选赛道卡片（展示今日实时涨跌、动态量化推荐依据与优选基金代码）；将 14 大赛道温度计总表与基因进化 60 日轨迹图保持在折叠框或 Popover 内按需查看。右翼预警哨移除开发口号尾缀，容器高度自适应无截断。
- Tab 1 新资建仓：参数 AI 智能托管与一键直出全案：
  - 简化步骤一前置输入：在 L1 默认层，用户只需设定拟投资总本金（带中文万元防错核对）与期望目标收益/风险档位（C1 至 C5），系统根据当前宏观同温层自动托管匹配最优量化定权模型（如鲁棒双核 HRP）、优选基金只数（默认 6 只）、持有期与限购过滤；并在旁边提供一个精致的“⚙️ 机构级模型与参数微调（已智能托管）”折叠面板，点开即可自由调整 7 大定权模型、3 至 15 只基金数量与风险测评问卷。
  - 推演与生成建仓单合流提速：主操作按钮默认一键完成量化推演并直接展示底部的实盘建仓执行单与一键复制下单小抄，免去用户先点步骤二再滑到底部点步骤三的二次点击。
  - 收敛步骤二的 16 张卡片轰炸：在 L1 默认层，仅并排展示最核心的 3 张人话结论大卡（预期达标胜率与年化票息安全垫、最坏回撤金额与最长水下回本天数、攻防仓位分配逻辑）；将历史三大黑天鹅承压卡片、10,000 次蒙特卡洛块重采样 CVaR 面板、2.8 万只六维选基漏斗评分表统一收进带关键指标摘要标题的“🔬 展开机构级量化压力测试与选基白盒证据”折叠面板中，让页面垂直长度缩短 60%。
- Tab 2 持仓调仓：首屏极致降噪与极速录基弹窗化：
  - 合并顶部概览卡与安全垫看板：将 4 张资产概览卡与浮盈安全垫破净临界点浓缩为紧凑的顶栏看板，将 -3%、-5%、-10% 三级大盘急跌承压卡片收进看板内的可展开详情中，消除首屏大面积色块堆叠。
  - 将原本占据整行的 5 列极速录基吧台改造为持仓明细表上方工具栏中的“➕ 极速录基”Popover 弹出框，平时完全不占用垂直高度，点击即弹、录完即合。
  - 严格落实双视图物理隔离：在“持仓诊断与智能调仓”主模式下，绝不渲染底部的账本工具坞；仅当切换至“账本运维与实盘复盘档案”模式时，才在主画布平铺展示粘贴导入、FIFO 批次透视、实盘净值与 Brinson 复盘账单、T+1 对账及同公司转换模块。清理全页重复出现的免折腾缓冲带滑块（全页仅保留一处）。

### R3. 底层量化因果律与数据真实性严苛纠偏（修改 advisory_engine.py、portfolio_manager.py 与 data_loader.py）
- 根除 `OnlineHeuristicFactorEvolver` 中的同日未来函数、夏普未扣无风险利率与伪造轨迹：
  - 在 `_evaluate_population` 中，第 t 日基于收盘特征 $F[t]$ 选出的赛道权重 $P[t]$，必须严格滞后一期作用于第 t+1 日的真实收益率 $R[t+1]$（即 $P[:-1]$ 对应 $R[1:]$），并在合成动态净值序列 `nav_dynamic` 时从日度收益率中真实扣除单边 10 bps 的换手摩擦成本。
  - 计算夏普比率时，严格遵照 `AGENT_SPEC.md` 从日均收益中扣除 2.0% 年化无风险利率（`0.02 / 250.0`）。
  - 废除 `get_60d_rolling_nav_and_trajectory` 中的 `lam` 人工线性插值公式，改为按每 5 个交易日推进式样本外滚动演化（Walk-Forward），真实记录各期四维权重与样本外净值。
- 跨市场交易日严格对齐、清除假序列与 2.5 亿假规模兜底：
  - 在 `_extract_sector_price_matrix` 中以 A 股交易日历为基准索引对齐 14 大赛道价格序列，彻底废除缺失数据时使用 `np.linspace(1.0, 1.05, window_days)` 伪造单边上涨直线的做法。
  - 在 `ActiveRiskSentry.inspect_portfolio` 中，当 `fund_metadata` 缺少规模字段时，主动穿透 `DataLoader` 与基金目录反查真实规模，废除 `else: aum = 2.5` 的静默假规模兜底。
  - 在 `evaluate_sector` 中将盘中实时涨跌幅更新至价格序列末尾重算真实的 MA20、Bias20、Slope20 与 ER20，动态生成与指标方向 100% 一致的量化入选依据；在 `ActiveRiskSentry` 中新增投资者适当性越界预警（检测实盘持仓是否超出 C1 至 C5 风险上限），并在 `evaluate_rebalance_audit` 中实装 Brinson 三维超额归因（配置效应、选基效应、摩擦节省）。

### R4. 多模态视觉验收、全量单测与 Git 归档闭环
- 彻底重启 8501 端口服务并清理缓存，调用 `/browser` 打开 `http://localhost:8501` 以挑剔的新手与专业买方双视角走查：确认首屏一眼看懂今日行动总开关；确认“历史三大牛熊拐点实盘对照尺”及全屏无裸露 HTML 源码块泄露；确认 Tab 1 与 Tab 2 默认视图清爽傻瓜、无卡片堆砌；展开 L2 专业折叠面板时所有高阶图表、蒙特卡洛、热力图与四象限散点图完整清晰、零文字重叠、640px 窄屏零水平溢出。
- 运行全量自动化测试套件（包含 `pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py`）并补充 G9 专项断言，确保 100% 绿灯通过。
- 确认四个只读裁判文件零修改，确认 `data/ledgers_index.json` 仅保留干净的主实盘账本，清理所有临时脚本。
- 更新项目根目录 `GEMINI.md` 与 `PROGRESS_LOG.md`，执行 `git add -A`、`git commit`、`git tag -a v3.9-G9` 并推送至 GitHub 远端（严禁创建任何 GitHub Release）。
- 最终必须通过独立的胜利审计（Victory Audit）确认。
- 在报告末尾输出一段供下一轮直接复制执行的 G10 世代进化指令（直接以 `/goal /boost /teamwork` 开头，包含 `/browser` 调用，保持纯文本无特殊符号排版，包含全量测试与 Git Tag 同步要求）。

## Acceptance Criteria

### 核心安全底线与防作弊验证
- [ ] 四大只读裁判文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）哈希值未发生变动，零修改。
- [ ] `DataLoader.simulate_execution` 默认函数签名与默认扣费逻辑保持只读。
- [ ] 全局配置文件 `c:\Users\deanc\.gemini\GEMINI.md` 零修改；所有经验规范沉淀于工作区根目录 `GEMINI.md` 与 `PROGRESS_LOG.md`。
- [ ] 现有测试依赖的关键 `session_state` 键名与函数入口完整保留，原有 50+ 项自动化测试用例全部兼容通过。

### UI 交互降噪、HTML 纯化与傻瓜化操作流（L1 + L2）
- [ ] 首屏“历史三大牛熊拐点实盘对照尺”及其他富文本 HTML 组件完成纯化，Streamlit 界面彻底消除裸露 HTML 源代码块，全屏零代码泄露。
- [ ] 首屏双翼看板顶部成功渲染高辨识度的“今日投顾行动总开关”，用一句大白话明确提示今日行动并支持一键跳转对应工作区。
- [ ] 双翼看板左翼默认仅展示市场脉搏与 Top 3 优选赛道卡片，14 大赛道温度计总表与 60 日轨迹图收纳进折叠框/Popover；右翼预警哨移除开发口号尾缀且容器高度自适应无截断。
- [ ] Tab 1 默认视图仅暴露本金输入与 C1-C5 风险档位，模型定权与参数实现 AI 智能托管；提供折叠面板支持专家自由调参。
- [ ] Tab 1 量化推演与建仓单生成合流为一键触发，直接展示实盘建仓执行单与一键复制下单小抄。
- [ ] Tab 1 步骤二默认仅展示 3 张核心人话结论卡；历史三大黑天鹅、10,000 次蒙特卡洛及选基漏斗大表收进折叠抽屉，垂直长度缩短 60%。
- [ ] Tab 2 顶部资产概览与安全垫看板合并为紧凑顶栏看板，-3%/-5%/-10% 急跌承压收进折叠详情，消除首屏大面积色块堆叠。
- [ ] Tab 2 极速录基改造为持仓明细表工具栏中的“➕ 极速录基”Popover 弹窗，常态下零垂直高度占用。
- [ ] Tab 2 严格落实双视图物理隔离：持仓诊断与智能调仓主模式下不渲染账本工具坞，切换至运维模式平铺展示；全页免折腾缓冲带滑块全局仅保留一处。

### 底层量化因果律与数据真实性
- [ ] `OnlineHeuristicFactorEvolver._evaluate_population` 中 $P[t]$ 严格滞后一期作用于 $R[t+1]$（$P[:-1]$ 对应 $R[1:]$），合成净值序列扣减单边 10 bps 换手摩擦成本。
- [ ] 计算夏普比率时，严格从日均收益中扣除 2.0% 年化无风险利率（`0.02 / 250.0`）。
- [ ] `get_60d_rolling_nav_and_trajectory` 废除 `lam` 线性插值，改为每 5 个交易日推进式 Walk-Forward 滚动演化，真实记录权重与净值。
- [ ] `_extract_sector_price_matrix` 以 A 股交易日历基准索引对齐，彻底清除 `np.linspace` 伪造序列。
- [ ] `ActiveRiskSentry.inspect_portfolio` 缺少规模时穿透反查真实规模，彻底废除 `aum = 2.5` 假规模兜底。
- [ ] `evaluate_sector` 将实时涨跌幅追加至末尾重算 MA20、Bias20、Slope20 与 ER20，指标与依据 100% 自洽；`ActiveRiskSentry` 实现 C1-C5 越界预警；`evaluate_rebalance_audit` 实现 Brinson 三维超额归因。

### 视觉走查、自动化测试与版本自举
- [ ] 彻底重启 8501 端口服务并清理缓存，`/browser` 多模态走查通过：确认首屏一眼看懂今日行动总开关、无裸露 HTML 源码泄露、Tab 1 与 Tab 2 默认视图清爽傻瓜、L2 折叠面板展开所有高阶图表完整无截断重叠、640px 窄屏无水平溢出。
- [ ] 全量自动化测试（包含 `pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py` 及新增 G9 专项断言）100% 绿灯通过。
- [ ] `data/ledgers_index.json` 仅保留干净的主实盘账本，清理所有临时脚本。
- [ ] Git 提交完成并创建附注标签 `v3.9-G9`，推送至远端 `origin`；无任何 GitHub Release 创建。
- [ ] 独立胜利审计（Victory Audit）确认通过。
- [ ] 报告末尾输出以 `/goal /boost /teamwork` 开头的纯文本 G10 进化指令（无表情符号、无特殊排版符号），包含 `/browser` 走查、全量测试与 Git Tag 同步要求。

## Follow-up — 2026-11-08T06:30:53Z

启动 G9 世代外傻内精渐进式披露交互降噪重构與底层量化因果律严苛纠偏闭环任务

一、 核心设计哲学与安全底线契约
1. 外傻内精原则（L1 傻瓜操作层 + L2 机构白盒层）：绝不阉割任何底层专业量化模型与风控规则，但必须彻底改變将所有参数与 16 张卡片全部平铺在首屏的杂乱做法。在 L1 默认视图中，坚持结论先行、AI 自动托管最优参数、一步直达交易清单；将复杂的参数微调、蒙特卡洛 10,000 次分布、历史黑天鹅明细与选基漏斗大表收纳进 L2 专业白盒折叠抽屉中，做到新手 3 秒无脑跟单、专家一键下钻看透底层证据。
2. 严禁修改四个只读裁判文件 judge_engine.py、holdout_vault.py、AGENT_SPEC.md、tests/test_infra.py，严禁修改 DataLoader.simulate_execution 的默认函数签名与默认扣费逻辑。
3. 严禁破坏现有 50+ 项自动化测试套件的兼容性（保留现有测试依赖的关键 session_state 键名与函数入口），确保原有测试与新增测试 100% 绿灯通过。

二、 第一阶段：全局交互降噪与傻瓜化操作流重构（修改 app_gui.py）

1. 首屏双翼看板瘦身与今日一句话傻瓜行动总开关
第一，在首屏双翼看板最上方，提炼渲染一条高辨识度的 今日投顾行动总开关：直接用一句大白话告诉用户今天到底要不要操作（例如 🟢 今日建议：按兵不动安心吃息 或 🟡 今日建议：14:30 尾盘有 1 项免赎置换机会），并配上一键直达对应工作区的按钮。
第二，双翼看板左翼默认仅展示精炼市场脉搏与 Top 3 优选赛道卡片（卡片内展示今日实时涨跌、动态量化推荐依据与优选基金代码）；将 14 大赛道温度计总表与基因进化 60 日轨迹图保持在折叠框或 Popover 内按需查看。右翼预警哨移除开发口号尾缀，容器高度自适应無截断。

2. Tab 1 新资建仓：参数 AI 智能托管与一键直出全案
第一，简化步骤一前置输入。在 L1 默认层，用户只需设定 拟投资总本金（带中文万元防错核对）与 期望目标收益/风险档位（C1 至 C5），系统根据当前宏观同温层自动托管匹配最优量化定权模型（如鲁棒双核 HRP）、优选基金只数（默认 6 只）、持有期与限购过滤，并在旁边提供一个精致的 ⚙️ 机构级模型与参数微调（已智能托管）折叠面板，点开即可自由调整 7 大定权模型、3 至 15 只基金数量与风险测评问卷。
第二，将 推演 与 生成建仓单 合流提速。主操作按钮默认一键完成量化推演并直接展示底部的实盘建仓执行单与一键复制下单小抄，免去用户先点步骤二再滑到底部点步骤三的二次点击。
第三，收敛步骤二的 16 张卡片轰炸。在 L1 默认层，仅并排展示最核心的 3 张人话结论大卡（预期达标胜率与年化票息安全垫、最坏回撤金额与最长水下回本天数、攻防仓位分配逻辑）；将 历史三大黑天鹅承压卡片、10,000 次蒙特卡洛块重采样 CVaR 面板、2.8 万只六维选基漏斗评分表 统一收进一个带关键指标摘要标题的 🔬 展开机构级量化压力测试与选基白盒证据 折叠面板中，让页面垂直长度缩短 60%。

3. Tab 2 持仓调仓：首屏极致降噪与极速录基弹窗化
第一，合并顶部概览卡与安全垫看板。将 4 张资产概览卡与浮盈安全垫破净临界点浓缩为紧凑的顶栏看板，将 -3%、-5%、-10% 三级大盘急跌承压卡片收进看板内的可展开详情中，消除首屏大面积色块堆叠。
第二，将原本占据整行的 5 列 极速录基吧台 改造为持仓明细表上方工具栏中的 ➕ 极速录基 Popover 弹出框，平时完全不占用垂直高度，点击即弹、录完即合。
第三，严格落实双视图物理隔离：在 持仓诊断与智能调仓 主模式下，绝不渲染底部的 账本工具坞；仅当切换至 账本运维与实盘复盘档案 模式时，才在主画布平铺展示粘贴导入、FIFO 批次透视、实盘净值与 Brinson 复盘账单、T+1 对账及同公司转换模块。清理全页重复出现的免折腾缓冲带滑块（全页仅保留一处）。

三、 第二阶段：底层量化因果律与数据真实性严苛纠偏（修改 advisory_engine.py、portfolio_manager.py 与 data_loader.py）

1. 根除 OnlineHeuristicFactorEvolver 中的同日未来函数、夏普未扣无风险利率与伪造轨迹
第一，在 _evaluate_population 中，第 t 日基于收盘特征 F[t] 选出的赛道权重 P[t]，必须严格滞后一期作用于第 t+1 日的真实收益率 R[t+1]（即 P[:-1] 对应 R[1:]），并在合成动态净值序列 nav_dynamic 时从日度收益率中真实扣除单边 10 bps 的换手摩擦成本。
第二，计算夏普比率时，严格遵照 AGENT_SPEC.md 从日均收益中扣除 2.0% 年化无风险利率（0.02 / 250.0）。
第三，废除 get_60d_rolling_nav_and_trajectory 中的 lam 人工线性插值公式，改为按每 5 个交易日推进式样本外滚动演化（Walk-Forward），真实记录各期四维权重与样本外净值。

2. 跨市场交易日严格对齐、清除假序列与 2.5 亿假规模兜底
第一，在 _extract_sector_price_matrix 中以 A 股交易日历为基准索引对齐 14 大赛道价格序列，彻底废除缺失数据时使用 np.linspace(1.0, 1.05, window_days) 伪造单边上涨直线的做法。
第二，在 ActiveRiskSentry.inspect_portfolio 中，当 fund_metadata 缺少规模字段时，主动穿透 DataLoader 与基金目录反查真实规模，废除 else: aum = 2.5 的静默假规模兜底。
第三，在 evaluate_sector 中将盘中实时涨跌幅更新至价格序列末尾重算真实的 MA20、Bias20、Slope20 与 ER20，动态生成与指标方向 100% 一致的量化入选依据；在 ActiveRiskSentry 中新增投资者适当性越界预警（检测实盘持仓是否超出 C1 至 C5 风险上限），并在 evaluate_rebalance_audit 中实装 Brinson 三维超额归因（配置效应、选基效应、摩擦节省）。

四、 第三阶段：调用 /browser 多模态视觉验收、全量单测与 Git 归档

1. 彻底重启 8501 端口服务并清理缓存，调用 /browser 打开 http://localhost:8501 以挑剔的新手与专业买方双视角走查：确认首屏一眼看懂今日行动总开关，确认 Tab 1 与 Tab 2 默认视图清爽傻瓜、无卡片堆砌，展开 L2 专业折叠面板时所有高阶图表、蒙特卡洛、热力图与四象限散点图完整清晰、零文字重叠、640px 窄屏零水平溢出。
2. 运行全量自动化测试套件（包含 pytest tests/test_infra.py、tests/test_adv_final_closure.py、tests/test_g3_evolution_loop.py、tests/test_gui_multi_ledger_stress.py）并补充 G9 专项断言，确保 100% 通过。确认四个只读裁判文件零修改，确认 data/ledgers_index.json 仅保留干净的主实盘账本，清理所有临时脚本。
3. 更新项目根目录 GEMINI.md 与 PROGRESS_LOG.md，执行 git add -A、git commit、git tag -a v3.9-G9 并推送至 GitHub 远端（严禁创建任何 GitHub Release）。
4. 在报告末尾输出一段供下一轮直接复制执行的 G10 世代进化指令，直接以 /goal /boost /teamwork 开头，包含 /browser 调用，保持纯文本无特殊符号排版，包含全量测试与 Git Tag 同步要求。

【关键参考审计文件】：
- c:\Users\deanc\Downloads\agy2_fundadvisory_ui_architecture_evaluation.md
- c:\Users\deanc\Downloads\agy2_app_gui.md

【前序关键上下文与最新实盘缺陷】：
1. 刚刚用户在提问中附带了实盘大屏全景截图（media_1794062108221_0279d081.jpg），在首屏“全市场优选赛道 · Top 3 优选自选”下方，“历史三大牛熊拐点实盘对照尺”（render_historical_inflection_ruler_html）在 Streamlit 中直接裸露泄露成了大面积原始 HTML 源代码块（CommonMark 4+ 空格缩进代码块缺陷导致）。团队必须严格按照 Rule 27 彻底修复该裸露 HTML 代码块缺陷，确保 HTML 安全纯化渲染，且全屏无代码泄露。
2. 上一轮中 `worker_g9_m1_12` 已经完成了 Milestone 1 的量化因果律代码及测试（`FundHolding.holding_days` setter 补齐，R3 因果律滞后一期、换手摩擦扣除、夏普扣 2% Rf、5日 Walk-Forward、A 股日历对齐、真实规模反查及适当性与 Brinson 归因，38 项测试已 100% 绿灯）。
3. 当前工作区 `AGY2_FundAdvisory/app_gui.py` 已包含部分前端重构基础，请团队在此基础上无缝接续，完成 L1/L2 交互降噪、HTML 纯化、服务重启、/browser 走查、全量测试回归与独立胜利审计闭环。

## Follow-up — 2026-11-08T09:05:13Z

启动 G10 世代像素级视觉减法手术、消灭断字换行与重复卡片、财经快讯白名单过滤及首屏主工作区提权闭环任务

一、 核心审美准则与安全底线契约
1. 极简干练铁律（做减法而非做加法）：当前界面存在严重的卡片堆砌、文字断行（如消费白酒被拆成消费白和酒两行）、信息重复（侧边栏与顶部4卡重复、行动总开关与右翼红框重复、右翼塞入-36.1%错误蒙特卡洛卡）以及主工作区Tab被挤出首屏之外的问题。本轮的核心任务是做减法、对齐留白、统一字号层级，确保打开首屏无需滚动即可直接看到并操作四大核心工作区 Tab。
2. 严禁修改四个只读裁判文件 judge_engine.py、holdout_vault.py、AGENT_SPEC.md、tests/test_infra.py，严禁修改 DataLoader.simulate_execution 的默认函数签名与默认扣费逻辑。
3. 若 tests/test_adv_final_closure.py 或 tests/test_g3_evolution_loop.py 中的旧界面文本断言阻碍了本次界面精简（例如强制要求首屏渲染冗余长文或重复卡片），请同步更新这些非只读测试文件中的界面文本断言，确保全量测试 100% 绿灯通过。

二、 第一阶段：对首屏与双翼看板执行六项像素级外科减法手术（修改 app_gui.py、advisory_engine.py 与 data_loader.py）

1. 根治 Top 3 赛道卡片的断字换行灾难与长文堆砌（修改 app_gui.py 与 advisory_engine.py）
第一，消灭标题与标签断行。在渲染 Top 3 优选赛道卡片时，卡片第一行左侧仅放置赛道名称（设置 font-size: 14px; font-weight: 700; white-space: nowrap; flex-shrink: 0），右侧仅放置单枚状态标签（设置 white-space: nowrap; flex-shrink: 0），严禁在标题行塞入实时涨跌幅与点位括号，彻底杜绝消费白酒断成消费白和酒、医药医疗断成医药医和疗、黄金击球区断成黄金击球和区的排版事故。
第二，精简卡片内部层级为干练的 3 行结构。第 1 行为赛道名称与状态标签；第 2 行为单行核心指标（格式：得分 92.4 ｜ 今日 -1.75% ｜ 估值分位 5%）；第 3 行为优选基金名称与代码（格式：优选: 招商中证白酒A 161725）及简洁的一句话逻辑（严格控制在 18 个汉字以内，废除长篇累牍的【量化因果链】灰色大文本框，将详细四维子项分与20日波动回撤收纳进鼠标悬停 title 提示或下方 14 赛道总表中）。
第三，修正 advisory_engine.py 中 _synthesize_quantitative_evidence 的自相矛盾逻辑：当考夫曼信噪比 er_20 小于 0.35（处于高频震荡）时，严禁同时输出右侧共振稳步上行等矛盾表述；当斜率上行但信噪比偏低时，准确表述为底部震荡筑底、均线初现企稳。

2. 清理右翼主动风险预警哨的冗余塞入项与错误 CVaR 卡片（修改 app_gui.py 与 portfolio_manager.py）
第一，从右翼预警哨容器中彻底移除 render_stress_liquidity_card_html（穿透式蒙特卡洛压力测试 -36.1% 卡片，该指标属于 Tab 3 范畴且右翼算出的 -36.1% 与 Tab 3 的 -12.0% 严重冲突，同步校准 portfolio_manager.py 中 simulate_portfolio_cvar_bootstrap_instance 的日度波动缩放系数使其与 Tab 3 口径严格一致）。
第二，当多资产相关性处于正常区间（未突破 0.75 警戒线）时，严禁在右翼渲染占地方的绿色【多资产相关性健康】大卡片；右翼仅展示真正触发了红黄牌的待办风险项（最多展示最紧急的 2 项，排版紧凑对齐），若无风险则仅展示一行清爽的绿色全通状态条。
第三，消除今日投顾行动总开关与右翼预警哨的重复按钮。将今日投顾行动总开关精简为双翼看板顶部一条高度不超过 44px 的极简状态栏（左侧一句话结论，右侧内联紧凑按钮，修复按钮上下悬空错位问题）。

3. 消除侧边栏与顶部 4 宽卡的 100% 重复内容（修改 app_gui.py）
顶部已有 4 张全局指标宽卡展示交易时钟、市场定调、两市成交与总资产，因此将侧边栏中完全重复的 市场状态与底座 大框精简为一行紧凑的数据源状态与底座交易日角标，把侧边栏首屏空间直接让给核心指数行情走廊，消除左右两侧文字复读。

4. 严装实时财经快讯的 A 股金融相关性白名单过滤器（修改 data_loader.py）
在 DataLoader.fetch_realtime_market_news_and_catalysts 中，对抓取到的 7x24 小时快讯标题实施严格的金融白名单过滤：仅保留包含 A股、沪深、指数、央行、利率、降准、降息、LPR、社融、PMI、证监会、公募、基金、ETF、红利、科创、半导体、芯片、医药、消费、银行、黄金、美股、纳指、国债、分红、净值、主力、北向、研报、估值、流动性 等财经关键词的快讯；强制拉黑过滤包含 无人机、拦截、联军、导弹、武装、袭击、交火、赛事、娱乐 等无关军事与社会新闻（彻底杜绝出现沙特联军拦截无人机这类离谱快讯）。若过滤后无匹配快讯，则输出基于当日真实量能与指数表现的精炼市场综述。

5. 首屏纵向高度压缩与四大工作区 Tab 提权（修改 app_gui.py）
第一，将顶部 4 张全局指标卡的 padding 与 min-height 压缩至 88px（去掉多余的次要小字行，每张卡仅保留标题、核心大数字、一行关键副标）。
第二，将双翼智能投顾看板（全市场机会雷达与主动风险预警哨）默认设为精简折叠态或紧凑高度模式，并在其正上方直接呈现今日一句话投顾结论与核心四大工作区 Tab 导航栏（🌱 新资建仓、💼 持仓调仓、📈 组合回测、🔍 穿透工具），确保用户在 1920x1080 标准桌面分辨率下打开页面时，无需滚动鼠标滚轮，第一屏就能同时看到顶部全局看板、今日行动结论以及下方主工作区 Tab 的核心内容。

6. 统一 Tab 1 与 Tab 2 的极简干练卡片规范（修改 app_gui.py）
检查 Tab 1 与 Tab 2 的所有卡片：统一圆角为 8px、边框为 1px solid var(--border-subtle)、统一内边距与字号层级（主标题 15px、卡片标题 13px、核心数字 20px、辅助说明 11.5px），清除多余的 Emoji 堆砌与五颜六色的高饱和背景色块，打造真正像彭博与招行私行工作台一样克制、专业、干练的视觉质感。

三、 第二阶段：强制重启服务并调用 /browser 进行严苛的视觉美感与排版走查

完成上述代码修改后，必须先彻底终止旧的 8501 端口进程并清理缓存，重新启动最新服务，随后调用 /browser 打开 http://localhost:8501 逐页截图审查：
1. 肉眼死磕首屏截图：确认消费白酒、医药医疗、纯债固收等所有赛道名称与状态标签 100% 单行完整显示、零断字换行；确认沙特无人机等无关快讯已彻底消失；确认右翼不再出现重复的蒙特卡洛 -36.1% 卡片与冗余绿卡；确认首屏在不滚动的情况下已能清晰看到四大工作区 Tab。
2. 逐一点击检查 Tab 1、Tab 2、Tab 3、Tab 4 及 640px 移动端视口：确认亮色与暗色主题下排版干练、留白呼吸感良好、零文字重叠、零水平溢出。若在 /browser 截图中发现任何一处换行错位或视觉杂乱，必须当场修改 CSS 与布局代码并重新截图确认。

四、 第三阶段：全量测试验证、Git 版本归档与生成 G11 世代指令

1. 运行全量自动化测试套件（包含 pytest tests/test_infra.py、tests/test_adv_final_closure.py、tests/test_g3_evolution_loop.py、tests/test_gui_multi_ledger_stress.py），确保 100% 绿灯通过。确认四个只读裁判文件零修改，确认 data/ledgers_index.json 仅保留干净的主实盘账本，清理所有临时脚本。
2. 将 G10 世代极简干练视觉重构与快讯白名单过滤规范更新写入项目根目录 GEMINI.md 与 PROGRESS_LOG.md，严禁触碰全局配置文件。
3. 执行 Git 提交与标签同步：运行 git add -A，运行 git commit 记录 G10 开发进程，使用 git tag -a 打上版本标签 v4.0-G10，最后运行 git push origin HEAD 与 git push origin --tags 同步至 GitHub 远端。严格遵守禁令：绝对禁止创建任何 GitHub Release。
4. 在最终报告末尾，基于你在本轮真实体验和 /browser 视觉走查中发现的下一个最能提升系统专业质感、实盘胜率或交互丝滑度的改进点，输出一段供下一轮直接复制执行的 G11 世代进化指令。你输出的 G11 指令必须满足以下要求：
第一，直接以 /goal /boost /teamwork 开头，并在走查环节包含 /browser 调用；
第二，全文保持纯文本干净排版，不要使用任何表情符号、星号、反引号、数学公式符号或装饰性分隔线；
第三，严守界面极简克制原则，严禁无脑堆砌新卡片，严禁脱离中国公募基金实盘制度；
第四，包含全量测试验证、Git Commit 与 Git Tag 同步（禁止创建 Release）以及继续生成下一代 G12 指令的自举要求。

【参考审计文件路径】：
- c:\Users\deanc\Downloads\agy2_app_gui (1).md
- c:\Users\deanc\Downloads\agy2_fundadvisory_goal_verification_and_ui_critique.md

【当前工作区基线】：
1. master 分支最新 Commit 为 34950f8，附注标签为 v3.9-G9，已通过 103 项全量测试 100% 绿灯。
2. 四大裁判文件哈希与 DataLoader.simulate_execution 保持严格只读锁定。
3. 全局配置文件 c:\Users\deanc\.gemini\GEMINI.md 严禁触碰，经验规则写入当前工作区 GEMINI.md 与 PROGRESS_LOG.md。
4. 8501 端口服务当前处于运行状态，修改后需平滑重启、清理缓存并核验健康探针。
5. 最终必须通过独立的胜利审计（Victory Audit）确认。


## Approved Task Prompt — 2026-11-08T11:57:10Z

启动 G11 世代三块式极简干练架构重构、砍除套娃横幅与双胞胎按钮、录基弹窗化及自举命令标签格式锁死闭环任务，对 Streamlit GUI 进行彻底的减法重构，使各主页面严格收敛为「顶部单行控制栏 + 中部核心数据表 + 底部单抽屉白盒证据」的三块式干练结构，完成严苛的视觉走查、测试验证、Git 归档与下一代 G12 指令生成。

Working directory: d:\Google\Workspace\Wind
Integrity mode: development

## Reference Materials
- 核心代码路径：
  - Streamlit GUI 主程序：`AGY2_FundAdvisory/app_gui.py` (端口 8501)
  - 四大只读裁判文件：`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`
  - 数据与回测：`DataLoader.simulate_execution`
- 参考审计文件：
  - `c:\Users\deanc\Downloads\agy2_fundadvisory_ultra_minimalist_spec.md`
  - `c:\Users\deanc\Downloads\agy2_app_gui (2).md`

## Verification Resources
- 自动化测试套件：`pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py`。
- 本地 8501 端口 Streamlit 服务端点与健康探针（`http://127.0.0.1:8501/_stcore/health`），配合 `/browser` 工具进行亮色/暗色及 640px 移动端视口的多模态视觉走查。
- 独立胜利审计（Victory Audit）确认。

## Requirements

### R1. 核心极简美学准则、安全底线契约与只读约束
- 三块式极简铁律：彻底重构 Streamlit GUI 界面（`app_gui.py`），使每个页面严格收敛为「顶部单行控制栏 + 中部核心数据表 + 底部单抽屉白盒证据」的三块式干练结构，并将全站装饰性 Emoji 削减 70% 以上。
- 严禁修改四个只读裁判文件：`judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py`。
- 严禁修改 `DataLoader.simulate_execution` 的默认函数签名与默认扣费逻辑。
- 解除旧 UI 测试对界面瘦身的绑架：允许并要求同步更新 `tests/test_adv_final_closure.py`、`tests/test_g3_evolution_loop.py`、`tests/test_gui_multi_ledger_stress.py` 中检查旧冗余按钮或旧文案的断言（或者在代码中仅保留不占空间的兼容钩子），绝不允许为了迎合旧单测而在界面上保留重复按钮和冗余横幅。
- 全局配置文件 `c:\Users\deanc\.gemini\GEMINI.md` 严禁触碰，所有经验规范必须写入当前工作区根目录 `GEMINI.md` 与 `PROGRESS_LOG.md`。

### R2. 四大区域彻底瘦身与三块式重构（修改 app_gui.py）
- 首屏顶栏二合一（砍掉多重横幅堆叠）：
  - 保留顶部 4 张紧凑全局指标卡（高度锁死在 82px，去除杂乱图标与多余副标）。
  - 删除独立的“今日投顾行动总开关”横幅与“跨区联动指令已生效承接”横幅，直接将今日一句话行动结论合并作为双翼看板折叠框的动态标题（例如：`今日投顾结论：持仓存在 2 只未满 7 天禁卖标的，建议尾盘锁定保护 ｜ 点击展开机会雷达与主动风控巡检`），折叠框右侧仅并排放置一个紧凑的快捷跳转按钮，使四大主工作区 Tab 上方仅有「4张全局卡 + 1条折叠导航栏」，首屏直接进入主工作区。
- Tab 1 新资建仓（从 12 个视觉块收敛至 3 个干练模块）：
  - 彻底删除 Tab 1 的 `render_workflow_step_indicator` 步骤胶囊条、删除副标题 caption、删除灰色的 AI 智能托管说明框、删除第二个重复的“一键生成全案”按钮（原 `col_s1_step` 与 `col_s1_all` 两个按钮代码完全重复，只保留唯一主按钮）。
  - 重构模块 1（单行参数控制栏）：在一个紧凑容器内单行并排展示拟投资总本金、风险策略档位（C1 至 C5）、建仓节奏选择（一次性/三步分批/智能定投）、高级模型与参数微调 Popover 按钮、以及唯一的“生成实盘建仓方案”主按钮。
  - 重构模块 2（建仓执行表置顶与三项核心指标条）：点击生成后，删除步骤二与步骤三分段大标题、删除中间多余的“重新生成建仓单”按钮、删除独立占地方的资产风险贡献度 PCR 横幅（表格内已有 PCR 列）与底部冗长的 `summary_advice` 蓝框；在实盘建仓执行表正上方，仅用一行紧凑的 3 栏高对比度指标条展示（1年达标胜率与年化票息安全垫、历史极限回撤与最长回本天数、攻防仓位配比与定权模型），指标条正下方紧贴展示实盘建仓执行单 DataFrame 大表，让用户一眼看到买哪只基金、买多少元。
  - 重构模块 3（底部动作栏与单一白盒抽屉）：建仓表正下方单行排列“覆盖写入当前账本（Popover二次确认）”、“另存为新账本（Popover）”、“下单小抄（Popover）”、“送入回测”；最底部仅保留唯一一个折叠框“展开机构级量化压力测试与选基白盒证据”（内含滚动胜率、黑天鹅与蒙特卡洛承压、选基漏斗与分批挂单调度表）。
- Tab 2 持仓调仓（消除双看板叠床架屋，极速录基进 Popover，首屏直达持仓表）：
  - 彻底删除 Tab 2 的 `render_workflow_step_indicator` 步骤胶囊条与副标题 caption。
  - 重构模块 1（单行全能账本工具栏）：一行内紧凑排列账本切换下拉框、主流程与运维档案模式切换、极速录基 Popover 按钮（将原本霸占整行空间的 5 列极速录基吧台完整移入此 Popover 弹窗内，平时零占高）、全局同步估值按钮、以及账本与环境管理 Popover 按钮（将新建账本、克隆副本、重命名、删除、载入演示组合、撤销上次修改全部收纳进该管理弹窗内，彻底删除主界面上散落的演示组合与撤销按钮行）。
  - 重构模块 2（合一的 4 格资产安全垫顶栏 + 持仓明细大表）：彻底删除原本上下重复的两套 4 宫格（浮盈安全垫看板里的 4 格与下方的持仓总市值/可用现金/累计浮盈/锁仓概览 4 卡），合二为一仅保留一排 4 格干练的资产与安全垫顶栏（①持仓总市值与仓位占比、②可用现金池与在途资金、③累计浮盈与今日预估涨跌、④综合安全垫厚度与沪深300破净临界点，点击可展开查看 -3%/-5%/-10% 三级压力推演）；在顶栏正下方零间距直接展示可编辑的实时持仓资产明细表，确保首屏无需滚动即可直接查看和编辑全部持仓。
  - 重构模块 3（干练调仓裁决与执行单）：持仓表下方仅保留“诊断并生成调仓方案”按钮与免折腾缓冲带滑块；点击后将时机裁决与调仓后果浓缩为一行紧凑的 4 格摘要条（时机裁决结论、手续费损耗、T+2在途风险、波动与回撤变化），正下方紧贴展示调仓建议执行表与一键同步跟单按钮，彻底删除冗长的重复说教提示框。
- 视觉降噪与机构级排版打磨（修改 app_gui.py 全局 CSS）：
  - 大幅削减正文、表头与卡片标题中无意义的 Emoji 图标（削减 70% 以上），依靠字重（600/700）、字号梯度（大数字 18px、标题 13px、正文 12px）与留白建立秩序感。
  - 减小全局容器间距：将 `block-container` 的 `padding-top` 降至 1.2rem，卡片 `margin-bottom` 统一收紧至 6px，消除松散空洞感。

### R3. 服务平滑重启与 /browser 多模态首屏信息密度严苛走查
- 彻底终止旧 8501 端口进程并清理缓存，重新启动最新服务。
- 调用 `/browser` 打开 `http://localhost:8501` 逐页截图审查：
  - 检验首屏高度与干练度：确认打开网页第一屏（无需滚动）不仅能看到顶部 4 卡和一句话结论折叠条，还能直接看到下方 Tab 1 的完整输入栏与建仓执行表，或切换至 Tab 2 时第一屏直接完整看到合一后的 4 格顶栏与持仓明细大表。
  - 检验冗余清除情况：肉眼确认 Tab 1 和 Tab 2 的步骤胶囊条已消失、双胞胎按钮已合并为单个按钮、Tab 2 的两套 4 宫格已合二为一、5 列极速录基吧台已收进 Popover 弹窗。
  - 检验亮色、暗色主题及 640px 移动端视口：确认全站排版干净利落、无断字换行、无文字重叠、无水平溢出。若在 `/browser` 截图中发现任何一处仍然显得啰嗦或拥挤，当场继续做减法修改代码并重新截图确认。

### R4. 全量测试验证、Git 归档与 G12 自举命令标签格式锁死
- 运行全量自动化测试套件（包含 `pytest tests/test_infra.py`、`tests/test_adv_final_closure.py`、`tests/test_g3_evolution_loop.py`、`tests/test_gui_multi_ledger_stress.py`），确保 100% 绿灯通过；确认四个只读裁判文件零修改，确认 `data/ledgers_index.json` 仅保留干净的主实盘账本，清理所有临时脚本。
- 经验沉淀与永久强制准则写入：将 G11 世代三块式极简架构规范更新写入项目根目录 `GEMINI.md` 与 `PROGRESS_LOG.md`，严禁触碰全局配置文件；同时在项目根目录 `GEMINI.md` 中写入一条永久强制准则：任何世代在最终报告末尾生成下一代进化指令时，所有斜杠命令必须严格写成完整的带方括号与圆括号命令标签形式，即 `[slashCommand:/goal]`、`[slashCommand:/boost]`、`[slashCommand:/teamwork]`、`[slashCommand:/browser]`，绝对禁止简写为裸露的 `/goal`、`/boost`、`/teamwork` 或 `/browser`。
- 执行 Git 提交与标签同步：运行 `git add -A`，运行 `git commit` 记录 G11 开发进程，使用 `git tag -a` 打上版本标签 `v4.1-G11`，最后运行 `git push origin HEAD` 与 `git push origin --tags` 同步至 GitHub 远端；严格遵守禁令：绝对禁止创建任何 GitHub Release。
- 胜利审计与 G12 世代进化指令输出：必须通过独立的胜利审计（Victory Audit）确认；在最终报告末尾基于本轮真实体验和 `/browser` 走查发现输出 G12 指令，必须满足以下硬性格式要求（内审与外审阻塞性门禁）：
  - 命令标签强制完整格式：指令开头必须严格逐字输出为 `[slashCommand:/goal] [slashCommand:/boost] [slashCommand:/teamwork]`，在走查环节必须严格逐字输出为 `[slashCommand:/browser]`，绝对禁止简写。
  - 除上述四个命令标签外，指令其余正文保持纯文本干净排版，不要使用任何表情符号、星号、反引号、数学公式符号或装饰性分隔线。
  - 严守三块式极简克制原则，严禁回退或重新堆砌卡片。
  - 包含全量测试验证、Git Commit 与 Git Tag 同步（禁止创建 Release）以及继续按相同完整 slashCommand 标签格式生成下一代 G13 指令的自举要求。

## Acceptance Criteria

### 核心安全底线与防作弊验证
- [ ] 四大只读裁判文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）哈希值未发生变动，零修改。
- [ ] `DataLoader.simulate_execution` 默认函数签名与默认扣费逻辑保持只读。
- [ ] 全局配置文件 `c:\Users\deanc\.gemini\GEMINI.md` 零修改；所有经验规范沉淀于工作区根目录 `GEMINI.md` 与 `PROGRESS_LOG.md`。
- [ ] 同步更新 `tests/test_adv_final_closure.py`、`tests/test_g3_evolution_loop.py`、`tests/test_gui_multi_ledger_stress.py` 中过时的冗余按钮与文案断言，全量自动化测试用例 100% 绿灯通过。
- [ ] `data/ledgers_index.json` 仅保留干净的主实盘账本，无临时脚本残留。

### 三块式极简重构与视觉降噪（app_gui.py）
- [ ] 全站装饰性 Emoji 削减 70% 以上，`block-container` 的 `padding-top` 设为 1.2rem，卡片 `margin-bottom` 设为 6px。
- [ ] 首屏顶栏二合一：删除独立的今日投顾行动总开关横幅与跨区联动承接横幅，今日一句话行动结论合入双翼看板折叠框动态标题，右侧并排放置紧凑快捷跳转按钮，主工作区上方仅保留 4 张 82px 全局指标卡与 1 条折叠导航栏。
- [ ] Tab 1 步骤胶囊条、caption、灰框说明、重复的“一键生成全案”按钮彻底删除。
- [ ] Tab 1 模块 1 紧凑单行并排展示总本金、C1-C5 风险档位、建仓节奏、高级模型微调 Popover 按钮及唯一的“生成实盘建仓方案”主按钮。
- [ ] Tab 1 模块 2 移除步骤二与步骤三标题、重新生成按钮、PCR 横幅及 summary_advice 蓝框；实盘建仓表正上方仅保留 3 栏指标条，下方紧贴实盘建仓执行单大表。
- [ ] Tab 1 模块 3 下方单行排列 4 个动作 Popover/按钮，底部仅保留单一量化压测与选基白盒折叠抽屉。
- [ ] Tab 2 步骤胶囊条与 caption 彻底删除。
- [ ] Tab 2 模块 1 单行并排账本切换下拉框、主流程/运维切换、极速录基 Popover、同步估值按钮、账本与环境管理 Popover（整合新建/克隆/重命名/删除/演示组合/撤销）。
- [ ] Tab 2 模块 2 删除原本上下两套 4 宫格，合二为一仅保留一排 4 格资产安全垫顶栏，正下方零间距直接展示可编辑实时持仓明细大表。
- [ ] Tab 2 模块 3 调仓时机与后果浓缩为一行 4 格摘要条，正下方紧贴展示调仓建议执行表与一键同步跟单按钮。

### /browser 视觉走查与多模态验收
- [ ] 重启 8501 端口服务并清理缓存，`/browser` 多模态走查确认：首屏无需滚动即可完整看到顶部 4 卡 + 一句话折叠条 + Tab 1 完整输入栏与建仓表（或 Tab 2 顶栏与持仓明细表）。
- [ ] 肉眼走查确认无步骤胶囊条、无双胞胎按钮、Tab 2 仅一套 4 宫格顶栏、5 列录基吧台已完全收纳进 Popover 弹窗。
- [ ] 亮色、暗色主题及 640px 移动端视口排版干净利落，无断字换行、无文字重叠、无水平溢出。

### 版本归档、胜利审计与 G12 自举标签锁死
- [ ] 项目根目录 `GEMINI.md` 与 `PROGRESS_LOG.md` 完整沉淀 G11 规范，且根目录 `GEMINI.md` 包含全世代斜杠命令必须使用完整方圆括号标签形式的永久强制准则。
- [ ] `git add -A`、`git commit` 提交，附注标签 `git tag -a v4.1-G11`，推送到 `origin`（无任何 GitHub Release 创建）。
- [ ] 独立胜利审计（Victory Audit）确认通过。
- [ ] 最终报告末尾输出符合严格格式要求的 G12 世代指令：开头逐字包含 `[slashCommand:/goal] [slashCommand:/boost] [slashCommand:/teamwork]`，走查环节逐字包含 `[slashCommand:/browser]`，除命令标签外保持纯文本无特殊排版符号，包含三块式极简原则、全量测试、Git Tag 同步及自举生成 G13 要求。


## Follow-up — 2026-11-08T14:57:27Z

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
