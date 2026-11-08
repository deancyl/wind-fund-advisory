# Original User Request

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
