# Original User Request

## Parameters
[skip-interview]
How this run was launched; not part of the task.

## Initial Request — 2026-11-11T14:16:26Z

启动 G17 世代拔除五维备忘录静态假常数、修复手机端主导航与表格截断、压缩文字墙与存量账本自动路由闭环任务

一、 核心病灶定性与安全底线契约
1. 根据最新手机端实测截图（image_dd1fc7.jpg，路径 C:/Users/deanc/.gemini/antigravity/brain/1395b6f9-733c-4446-9cdb-f33a19e5f711/.user_uploaded/media_1794406255999_c8abd7ad.png）与源码法证审查，本轮必须彻底根除以下 6 个不可接受的缺陷：
第一，严厉整顿「用静态假常数糊弄投顾分析」的造假行为：在 advisory_engine.py 第 1549 至 1593 行的 generate_chief_advisor_memo 中，代码竟然使用了 `snap.get("treasury_10y", 1.6258)`、`macro_multi.get("usdcnh_rate", 7.2450)`、`macro_multi.get("gold_price", 628.5)`、`macro_multi.get("nasdaq_change_pct", -0.25)` 等不存在的键名，导致界面上展示的国债、汇率、黄金、纳指数据 100% 退化为写死的静态假常数！必须彻底打通真实数据源，严禁使用硬编码假行情常数！
第二，修复手机端第 4 个主导航入口被截断吞没的 Bug：在窄屏视口下，四宫格主导航栏的「🔍 穿透工具」溢出到了屏幕外侧不可见。必须在 CSS 中针对 `max-width: 640px` 将顶层主导航设为 2x2 双排网格（`grid-template-columns: repeat(2, 1fr) !important`），确保 4 个核心入口在任何手机屏幕上 100% 完整可见！
第三，消除首屏「600字长文墙」与标题挤压变形：image_dd1fc7.jpg 中五维备忘录纵向叠了 5 个巨型文本框，占满两屏高度，且标题栏的「买方参谋体系」被挤成竖排三行。必须将首屏备忘录重构为「紧凑五维信号灯条 + 一句话核心结论（展开看详情）」，并与下方的「今日投顾参谋」合并为单一模块，彻底消灭首屏同质化双折叠框！
第四，修复「切换存量账本后仍停留在新资建仓」的交互割裂 Bug：当用户在顶部下拉框切换至「实战存量组合（29只·¥26,615.10）」等已有持仓的存量账本时，界面必须自动切换聚焦至第二个主工作区「💼 持仓调仓」，直接展示该存量组合的持仓诊断、碎片尾仓清理与调仓方案，绝不能停留在「🌱 新资建仓」展示 10 万元的无关方案误导用户！
第五，修复手机端表格核心列被截断与底部 5 个灰色长条堆叠：在窄屏下优化持仓与建仓表格的列顺序与紧凑度（将「基金名称/代码、金额/占比、盈亏/操作建议」放在最左侧前三列优先展示），并收拢表格下方堆叠的 5 个折叠长条。
2. 物理安全红线：严禁修改四个只读裁判文件 judge_engine.py、holdout_vault.py、AGENT_SPEC.md、tests/test_infra.py，严禁修改 DataLoader.simulate_execution 的默认函数签名与默认扣费逻辑。

二、 第一阶段：拔除静态假常数，实装真数据驱动的「十维全息投顾引擎与因果传导链」（修改 data_loader.py、advisory_engine.py、app_gui.py）

1. 打通真实宏观、利率、汇率、海外与商品日度/实时数据源（修改 data_loader.py 与 advisory_engine.py）
在 data_loader.py 与 advisory_engine.py 的 `generate_chief_advisor_memo` 中：
- 10Y国债收益率与中美利差：直接从 `data/macro/bond_zh_us_rate.parquet` 读取最新交易日的真实 `cn_yield_10y`、`us_yield_10y` 及其近 20 日变动基点（bp）；
- 黄金与全球股市联动：直接从 `data/processed/aligned_matrix_total_return.parquet`、`data/processed/indices/AU9999.SGE.parquet`、`data/global/global_indices.parquet` 或实时行情接口读取真实的黄金价格/涨跌幅、纳指/标普/恒生科技最新涨跌幅與 20 日均线乖离率；
- 离岸人民币汇率（USD/CNH）：优先调用 `DataLoader.fetch_realtime_usdcnh_fx(use_cache=True)` 获取真实 `rate` 与 `change_pct`；
- 编写单元测试断言：在 `generate_chief_advisor_memo` 输出结果中，严禁出现未经验真的静态魔法数字 `628.5` 或 `-0.25%`，每一个指标必须注明真实数据截面日期与来源！

2. 新增「十维投顾投票与仓位因果传导公式」（修改 advisory_engine.py 与 app_gui.py）
在 `generate_chief_advisor_memo` 中，除输出五大维度分析外，新增输出 `ten_dimension_votes`（涵盖：①宏观经济、②货币政策、③股债ERP、④国际联动、⑤外汇锁汇、⑥产业估值、⑦资金情绪、⑧技术信噪比、⑨历史同温层、⑩期权IV与相关性黑天鹅）的量化评分与多空投票汇总，并生成一行清晰的 **「仓位推导因果链」**（例如：`基准权益中枢 60% + ERP极低估溢价(+10%) + 货币宽松(+5%) - 局部赛道超买约束(-5%) = 当前建议权益仓位 70%`），彻底破除“唯算法黑箱论”，让用户直观看到每一个外部信息如何影响最终配比！

三、 第二阶段：重构首屏极简高密度交互与完美手机端响应式体验（修改 app_gui.py）

1. 合并首屏「五维备忘录」与「双翼投顾参谋栏」，消灭 10 层盒子纵向堆叠（修改 app_gui.py）
第一，废除首屏同时存在「五维决策备忘录大框」和「今日投顾参谋折叠框」的双重堆叠设计，将两者融合为一个统一的「🧭 首席投顾今日裁决台」：
- 首屏默认直显部分（总高度严格控制在 110px 以内）：第一行展示醒目的 **「今日核心裁决 + 仓位因果传导公式 + 数据截面时间」**（修复 flex-wrap 防止徽章文字竖排挤压）；第二行以 **5 个紧凑胶囊（桌面端 1行5列，手机端 2列流式网格）** 展示宏观政策、国际汇率、产业击球区、持仓病灶、14:30尾盘指令的 **20字以内极简结论**！
- 点击下方的「🔭 展开十维深度逻辑、Top 3 机会雷达与十三维风控体检详情」时，再平滑展开完整分析文段、3张赛道卡与风控详情列表。

2. 修复手机端（<=640px）主导航截断、指标卡堆叠与表格列溢出（修改 app_gui.py 全局 CSS 与表格配置）
第一，在全局 CSS 的 `@media (max-width: 768px)` 中：
- 将顶层四大功能主导航栏强制设为 **2×2 双排四宫格**：`grid-template-columns: repeat(2, 1fr) !important; gap: 6px !important;`，按钮高度设为 `40px !important; font-size: 14px !important;`，确保「🌱 新资建仓、💼 持仓调仓、📈 组合回测、🔍 穿透工具」四个入口在手机窄屏下 100% 完整显示，绝不出现横向截断！
- 将顶部 4 张全局指标卡在手机窄屏下设为 **2×2 双列紧凑网格**，节省 50% 纵向首屏空间！
第二，优化所有 DataFrame 表格在手机与桌面端的列展示顺序：将最核心的「基金名称(含代码)、持有/建议金额、盈亏率/目标权重、操作裁决」排在最前面，避免关键决策信息被截断在右侧滚动区外。

3. 实现「切换存量账本自动路由至 💼 持仓调仓」的智能交互联动（修改 app_gui.py）
在 `switch_active_ledger(target_ledger_id)` 函数中：当用户切换至包含存量持仓的账本（如 `实战存量组合（29只·¥26,615.10）`）时，自动触发跨 Tab 焦点跳转至 `tab_index: 1`（`💼 持仓调仓`），并自动展开该组合的「🧹 碎片尾仓一键瘦身卡」、「🩺 深套出血点置换处方」与调仓对比方案，让用户切换账本后第一眼看到的就是自己这 29 只基金的实战诊断！

四、 第三阶段：深化课题 2 与课题 3 实战 —— 历史盲测全真扣费账单与长截图多级精准匹配（修改 portfolio_manager.py、strategy_bridge.py、app_gui.py）

1. 升级长截图识别的「名称前缀 + 昨日涨跌幅交叉验真匹配器」（修改 portfolio_manager.py）
在 `fuzzy_match_fund_by_name` 与 `parse_long_screenshot_holdings` 中，针对手机截图基金名称常带省略号（`...`）的问题，新增 **「名称关键词 + 昨日收益率（yesterday_pnl / (market_value - yesterday_pnl)）双因子交叉锁定」** 逻辑，并支持用户在导入预览表中直接搜索修改任意存疑标的，确保 28,177 只全市场基金精准匹配。

2. 升级 Tab 3「🕰️ 历史时点盲测验证」与「29基存量组合重构回测」的真实扣费明細账单（修改 strategy_bridge.py 与 app_gui.py Tab 3）
在 Tab 3 的历史盲测与 29 基组合重构对比中，新增展示「🧾 中国公募交易规则全真摩擦扣减明细栏」（明确列出回测期内累计扣除的申购费、赎回费、C类销售服务费、T+1/T+2在途资金损耗及限购拆单次数），用最严苛的实盘规则验证重构后组合相比原始 29 基组合在「净赚金额增厚、最大回撤压降、回本天数缩短」上的真实优势。

五、 第四阶段：强制重启服务并调用 /browser 在桌面端与手机端双视口截图验收

1. 彻底终止旧 8501 端口进程，启动最新服务，调用 /browser 打开 http://localhost:8501 分别在 **1920x1080 桌面视口** 与 **390x844 手机视口** 下截图严格核验：
- 手机视口核验（直接对比本轮问题图 image_dd1fc7.jpg）：确认 4 个主导航 Tab 呈 2x2 网格完整显示（「🔍 穿透工具」绝不被截断）、确认首屏不再有 600 字长文墙、确认徽章文字无竖排挤压、确认切换到 29 基账本后自动进入「💼 持仓调仓」展示 29 基实战诊断！
- 数据真实性核验：确认五维备忘录中的国债、汇率、黄金、外盘涨跌幅全部来自真实数据源，彻底消灭 `628.5`、`-0.25%` 等写死常数！
2. 运行全量测试套件确保 100% 绿灯通过，更新 GEMINI.md 与 PROGRESS_LOG.md，执行 git add -A、git commit、git tag -a v4.7-G17 并推送到远端（严禁创建 GitHub Release）。
3. 在最终报告末尾输出供下一轮直接复制执行的 G18 世代进化指令。
【阻塞性门禁警告：防客户端转义命令标签校验】：
由于客户端输入框会将命令标签转义为带冒号的内部格式，你在最终报告中输出 G18 指令时，绝对禁止输出带冒号的 slashCommand: 格式！四个命令标签必须 100% 严格按以下字符序列输出（圆括号内使用英文分号）：
- /goal
- /boost
- /teamwork
- /browser
内审与外审代理在终审时必须检查字符串：若出现任何冒号形式的 slashCommand:，一律打回重写！其余正文保持纯文本无特殊符号排版。MD审计文件参考：c:\Users\deanc\Downloads\agy2_ui_ux_audit_and_fix_plan (6).md


## Follow-up — 2026-11-11T15:04:24Z

【用户最新实测问题修复通知】：
用户刚刚在网页端点击「生成【C3 档位】实盘建仓单与限购拆单」时触发了局部报错：
"Cannot serialize the return value (of type tuple) in _cached_fund_quote_and_screening(). st.cache_data uses pickle to serialize the function's return value..."
根因是 app_gui.py 中动态 importlib.reload(portfolio_manager) 导致 FundQuote 类在内存中被重载，st.cache_data 无法通过 pickle 序列化。
已将 app_gui.py 中的：
@st.cache_data(ttl=600, show_spinner=False)
def _cached_fund_quote_and_screening(fcode: str):
成功改为：
@st.cache_resource(ttl=600, show_spinner=False)
def _cached_fund_quote_and_screening(fcode: str):
并同时修复了 portfolio_manager.py 中 search_funds_in_catalog 与 slice_long_screenshot_for_ocr 的缩进。
请在接下来的代码修改与整合中保持此项修复，并继续推进 G17 其余任务！