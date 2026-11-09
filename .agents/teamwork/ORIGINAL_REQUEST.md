# Original User Request

## Initial Request — 2026-11-09T06:50:48Z

启动 G13 世代首屏零阻塞秒开重构、全宽大胶囊主导航视觉提权、清除伪交易按钮与臃肿嵌套及回测曲线打假闭环任务

一、 核心问题定性与安全底线契约
1. 直面五大用户体验与审美灾难：当前版本存在以下五个不可接受的严重缺陷，本轮必须彻底根除：
第一，首屏加载极度缓慢（图1）：render_dual_wing_advisory_dashboard 在折叠框默认关闭的情况下，依然在主线程同步实例化了 2 次 OpportunityRadarEngine，并在未点开的因子进化 Popover 中调用了 get_60d_rolling_nav_and_trajectory（连续循环跑了 12 次遗传算法与 14 次磁盘 Parquet 读取），导致顶部 4 卡渲染完后下方大片白屏卡死数秒。
第二，伪交易按钮误导用户（图2）：本系统是纯投顾参谋与账本分析工具，不承担真实柜台交易功能，但界面上却放了让人看不懂的巨型红按钮「查看锁仓保护」、「一键批量锁定这2只标的调仓下界」、「择机置换」等伪系统控制按钮。
第三，双翼看板极度臃肿（图3）：右侧因为放了「查看锁仓保护」按钮切走了 18% 宽度的空白列；展开后内部塞了市场晨报、文字重叠穿模的牛熊拐点尺、3张赛道卡、右翼6个跳转按钮，以及底部的 4 个深度工具折叠框（14赛道总表、14:45折溢价、期权IV、QDII锁汇）。
第四，回测图文字遮挡且曲线失真（图4）：全周期净值曲线的图例框直接盖住了 2024 至 2026 年的净值曲线；同时底部的纯债指数被画成了毫无波动的直线，红利低波 8 年年化仅 2.35% 严重失真，而主实盘账本曲线因后视镜幸存者偏差呈现出不真实的旱地拔葱直线。
第五，四大核心功能入口极度不显眼（图5）：新资建仓、持仓调仓、组合回测、穿透工具四个最重要的一级入口缩在左上角变成 14px 灰色小字，视觉权重甚至不如底下的二级标题，且进入 Tab 后又重复打印一遍相同的巨型标题。
2. 物理安全红线：严禁修改四个只读裁判文件 judge_engine.py、holdout_vault.py、AGENT_SPEC.md、tests/test_infra.py，严禁修改 DataLoader.simulate_execution 的默认函数签名与默认扣费逻辑。允许并要求同步更新非只读测试文件（如 tests/test_adv_final_closure.py 等）中针对旧按钮或旧布局的断言，确保全量测试 100% 绿灯通过。

二、 第一阶段：针对五大痛点的外科手术级重构（修改 app_gui.py、advisory_engine.py、portfolio_manager.py、strategy_bridge.py）

1. 根治痛点 1（图1）：首屏零阻塞极速秒开（首屏主线程耗时必须小于 150ms）
第一，在 app_gui.py 的 render_dual_wing_advisory_dashboard 中，彻底禁止在首屏默认加载时调用 OpportunityRadarEngine()、evolve_factor_weights()、get_60d_rolling_nav_and_trajectory()、fetch_realtime_market_news_and_catalysts()、fetch_etf_feeder_arbitrage_sensors()、fetch_options_implied_volatility_sensors() 以及 evaluate_all_qdII_fx_arbitrage()！
第二，首屏顶部的投顾提示条仅基于内存中已有的 snapshot 与 pm.holdings 做纯内存毫秒级轻量判断（不发任何网络请求、不跑遗传进化、不读大 Parquet）。
第三，将 OnlineHeuristicFactorEvolver 的 60 日轨迹计算改为缓存在磁盘文件 data/cache/factor_evolution_cache.json 中（有效期 12 小时），严禁在每次渲染时现场循环跑 12 轮遗传进化；只有当用户主动点击展开雷达详情并点击刷新按钮时，才触发重算。

2. 根治痛点 2 与痛点 3（图2、图3）：彻底砍除所有伪交易按钮，重构清爽全宽投顾提示栏
第一，彻底删除首屏右上角的红色大按钮「查看锁仓保护 / 查看今日调仓单 / 检视持仓账本」（即删除 col_wing_btn 及其内部的 btn_master_action_switch 按钮），让投顾结论折叠栏占满 100% 全宽，彻底消灭图 3 右侧那条刺眼的空白竖柱！
第二，将投顾结论栏文案从伪系统黑话改为清晰的人话参谋提示（例如：今日投顾参谋：持仓含 2 只未满 7 天标的，赎回需扣 1.5% 惩罚费，调仓算法已自动为您避开卖出 ｜ 点击展开市场机会与持仓体检）。
第三，全面清理双翼看板内部的所有伪操作跳转按钮与臃肿嵌套：
- 删除右翼预警哨中的「一键批量锁定这2只标的调仓下界」按钮，以及每张风险卡片下方的「择机置换」、「平衡赛道敞口」、「穿透到底层」等所有按钮！右翼仅以干净紧凑的无按钮列表形式展示当前触发的 1 至 3 条核心风险提示与应对建议（未满 7 天标的在 Tab 2 调仓算法中默认自动锁定下界，无需用户手动点击锁定）。
- 删除左翼赛道卡片下方的 3 个「+ 入备选池」按钮，在卡片内直接清晰展示优选基金名称与 6 位代码。
- 从首屏双翼折叠框中彻底移出以下 5 个臃肿模块：① 嵌套的「历史三大牛熊拐点实盘对照尺」（消除图3中的文字重叠穿模，将其仅保留在 Tab 1 定投模式中并修复宽度防重叠）、②「查看全市场 14 大赛道量化温度计总表」、③「场内ETF与场外联接 14:45 尾盘折溢价套利感知」、④「50ETF与300ETF认沽期权隐含波动率防暴跌哨」、⑤「跨境QDII溢价与外汇期货锁汇成本套利精算」。将后 4 个深度工具统一归入 Tab 4「穿透工具」的二级子模块中，让首屏双翼折叠框展开后只有干净利落的一排「左翼 Top 3 赛道卡 + 右翼极简风险提示列表」，高度不超过 220px！

3. 根治痛点 5（图5）：重塑 90 分机构级 UI 审美，打造全宽四宫格高对比度主导航栏
第一，用强力 CSS 将顶层四大功能入口（新资建仓、持仓调仓、组合回测、穿透工具）从不起眼的 14px 小字改造为「100% 全宽四等分高对比度分段式大导航栏（Full-Width Segmented Navigation Bar）」：
- 定位顶层主 Tab 容器 `[data-testid="stMainBlockContainer"] > div > div > [data-testid="stTabs"] > [data-baseweb="tab-list"]`，设置 `display: grid !important; grid-template-columns: repeat(4, 1fr) !important; gap: 10px !important; background: var(--bg-elevated) !important; padding: 6px !important; border-radius: 10px !important; border: 1px solid var(--border-subtle) !important; margin-bottom: 14px !important;`。
- 定位顶层主 Tab 按钮，设置 `height: 46px !important; font-size: 16px !important; font-weight: 700 !important; border-radius: 8px !important; justify-content: center !important; background: var(--bg-surface) !important; border: 1px solid var(--border-subtle) !important; box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;`。
- 定位顶层选中态主 Tab 按钮 `button[aria-selected="true"]`，设置 `background: var(--accent-primary) !important; color: #ffffff !important; border-color: var(--accent-primary) !important; box-shadow: 0 4px 12px rgba(29, 78, 216, 0.25) !important;`（同时确保选中态按钮内部所有 span 和 p 文字颜色强制为 `#ffffff !important`）。
- 严格区分一级主导航与 Tab 4 内部的二级子 Tab（二级子 Tab 保持紧凑轻量的下划线样式，绝不与一级大导航混淆）。
第二，彻底删除四个主 Tab 内部开头重复打印的 `st.subheader("🌱 新资建仓")`、`st.subheader("💼 持仓调仓")`、`st.subheader("📈 组合回测")`、`st.subheader("🔍 穿透工具")` 及其下方的废话 caption！在 Tab 4 中，将「选择穿透体检组合对象」与「当前体检组合成分档案」合并为顶栏紧凑的一行摘要，直接把图表呈现给用户。

4. 根治痛点 4（图4）：修复回测图文字遮挡，彻底纠偏失真的基准曲线与后视镜偏差
第一，消灭文字遮挡图形：在 Tab 3 全周期净值曲线的 Plotly 图表布局中，将 legend 移至图表外部上方（设置 `legend=dict(orientation="h", yanchor="bottom", y=1.06, xanchor="left", x=0, bgcolor="rgba(0,0,0,0)")`，并将 `margin=dict(t=75, l=10, r=10, b=10)`），同时将牛熊阶段背景标注文字移至绘图区顶部边缘并调淡字色，确保没有任何一个文字或图例框压在净值曲线上！
第二，修复纯债指数与红利低波基准曲线的严重失真：检查 Tab 3 基准曲线的数据提取逻辑，严禁对纯债指数（H11009）使用起止点线性插值画直线！必须从 `aligned_matrix_total_return.parquet` 中提取真实的日度收盘序列计算归一化累计净值与真实年化收益率（CAGR），确保红利低波（H30269）、沪深300（H00300）、中证综合债（H11009）、黄金（AU9999）、纳指（SPX_CNY）的走势与历史真实全收益行情 100% 吻合。
第三，消除静态持仓回测的后视镜幸存者错觉：当回测目标为「当前实盘账本」时，若账本中包含黄金（000216）或美股纳指（017436）等近几年大涨的跨市场资产，除了在默认对标基准中自动勾选对应的黄金/海外基准供同图客观比对外，必须在图表上方明确标注「当前持仓静态权重历史回溯（含历史后视镜权重效应，非滚动样本外实盘记录）」，并提供一键切换对比「全天候滚动样本外动态策略曲线」，做到实事求是、不忽悠用户。

三、 第二阶段：强制重启服务并调用 /browser 进行实测秒开与五图逐一对比验收

完成上述代码修改后，必须先彻底终止旧的 8501 端口进程并清理缓存，重新启动最新服务，随后调用 /browser 打开 http://localhost:8501 对照本轮的 5 张问题图逐一截图核验：
1. 核验痛点 1（对比图1）：测试页面首次打开与刷新速度，确认首屏零白屏卡顿，1秒内完整渲染出顶部 4 卡、投顾提示条与四大核心 Tab 内容。
2. 核验痛点 2 与 3（对比图2、图3）：确认首屏右上角刺眼的「查看锁仓保护」红按钮与右侧空白列已彻底消失；点击展开投顾提示栏，确认内部不再有 4 个套娃折叠框、不再有「一键批量锁定」等伪交易按钮，牛熊拐点尺无任何文字重叠。
3. 核验痛点 5（对比图5）：确认「新资建仓、持仓调仓、组合回测、穿透工具」四个主入口已呈现为占满全宽、46px 高、高亮醒目的四宫格大胶囊导航栏，且点击切换各 Tab 时内部不再有重复的大标题。
4. 核验痛点 4（对比图4）：切换至「组合回测」，截图确认图例已移至图表外部上方、零遮挡净值曲线，确认纯债指数与红利低波为真实的日度历史波动曲线而非假直线。

四、 第三阶段：全量测试验证、Git 归档与生成 G14 世代指令（严守防转义命令标签门禁）

1. 运行全量自动化测试套件（包含 pytest tests/test_infra.py、tests/test_adv_final_closure.py、tests/test_g3_evolution_loop.py、tests/test_gui_multi_ledger_stress.py），确保 100% 绿灯通过。确认四个只读裁判文件零修改，确认 data/ledgers_index.json 仅保留干净的主实盘账本，清理所有临时脚本。
2. 将 G13 世代首屏零阻塞规范、全宽大胶囊主导航规范与非交易参谋定位准则更新写入当前工作区根目录 GEMINI.md 与 PROGRESS_LOG.md，严禁触碰全局配置文件。
3. 执行 Git 提交与标签同步：运行 git add -A，运行 git commit 记录 G13 开发进程，使用 git tag -a 打上版本标签 v4.3-G13，最后运行 git push origin HEAD 与 git push origin --tags 同步至 GitHub 远端。严格遵守禁令：绝对禁止创建任何 GitHub Release。
4. 在最终报告末尾输出供下一轮直接复制执行的 G14 世代进化指令。
【阻塞性门禁警告：防客户端转义命令标签校验】：
由于客户端输入框在接收提示词时，会将 Markdown 链接形式的命令标签转义为带冒号的内部格式，你在最终报告中输出 G14 指令时，绝对禁止输出带冒号的 slashCommand: 格式！
你输出的 G14 指令中的四个命令标签，必须 100% 严格按照以下字符序列拼接输出（圆括号内使用英文分号）：
- goal 命令必须写为：[/goal](slashCommand;goal)
- boost 命令必须写为：[/boost](slashCommand;boost)
- teamwork 命令必须写为：[/teamwork](slashCommand;teamwork)
- browser 命令必须写为：[/browser](slashCommand;browser)
内审与外审代理在终审时必须执行字符串检索：若最终报告的 G14 指令中出现任何一处冒号形式的 slashCommand:，一律判定门禁失败打回重写！其余正文保持纯文本无特殊排版符号，包含全量测试验证、Git Commit 与 Git Tag 同步（禁止创建 Release）以及继续按上述精确格式生成下一代指令的自举要求。外部审计MD文件供参考：c:\Users\deanc\Downloads\agy2_ui_ux_audit_and_fix_plan (1).md 和 c:\Users\deanc\Downloads\agy2_fundadvisory_5_screenshots_diagnosis_and_fix.md

## Follow-up — 2026-11-09T06:52:10Z

[skip-interview] 任务需求已在首轮 Prompt 中 100% 完整详尽定义，包含五大痛点的外科手术级修复、首屏秒开 (<150ms)、CSS 导航改造、去除伪交易按钮、回测曲线打假、全量测试与 Git 标签。请直接跳过访谈，立即启动执行！


## Follow-up — 2026-11-09T11:19:24Z

启动 G14 世代四大隐蔽代码漏洞封堵、十二维风控缓存直读恢复、回测与样本外轨迹真算法还原及高定机构蓝审美统一闭环任务

一、 核心审计发现与安全底线契约
1. 本轮必须彻底解决代码审查中抓出的四大隐蔽漏洞与四大审美缺陷：
第一，修复假缓存漏洞：app_gui.py 第 1323 行尝试读取 data/cache/radar_sectors_cache.json，但全站没有任何代码写入该文件，导致每次加载依然同步实例化 OpportunityRadarEngine 扫描 14 赛道。
第二，恢复被阉割的十二维主动风控：app_gui.py 第 1425 至 1485 行删掉了 sentry.inspect_portfolio 调用，仅检查未满 7 天和 C 类满 30 天，导致移动止盈、右侧破位、超买拥挤、迷你基清盘、赛道集中度、适当性越界等 10 个核心维度在 UI 上完全失明并误报「主动风控巡检全通」。
第三，修复样本外轨迹偷工减料 Bug：advisory_engine.py 第 487 行在 get_60d_rolling_nav_and_trajectory 中将动态选股写死成了 np.mean(r_day[:3])，根本未使用演化出的 w_opt 权重挑选 Top 3 赛道，且漏扣了双边换手摩擦。
第四，提升机构级高定审美与开箱即用体验：消除 Streamlit 默认番茄红主按钮与皇家蓝导航栏的廉价撞色，修复 Tab 1 顶部 5 列控制栏高低错位，消除 Tab 1 首次打开下半屏空白的问题，清除首屏残留的盯盘待办预案伪交易流。
2. 物理安全红线：严禁修改四个只读裁判文件 judge_engine.py、holdout_vault.py、AGENT_SPEC.md、tests/test_infra.py，严禁修改 DataLoader.simulate_execution 的默认函数签名与默认扣费逻辑。同步维护非只读测试文件确保全量测试 100% 绿灯通过。

二、 第一阶段：封堵四大代码漏洞（修改 advisory_engine.py 与 app_gui.py）

1. 真正落实 14 赛道雷达缓存读写闭环（修改 advisory_engine.py 与 app_gui.py）
在 OpportunityRadarEngine.scan_all_sectors 完成 14 赛道扫描后，自动将结果序列化写入 data/cache/radar_sectors_cache.json（附带 timestamp 字段，默认有效期 4 小时）。在 OpportunityRadarEngine.scan_all_sectors 入口处，若未强制刷新且磁盘缓存未过期，直接毫秒级返回缓存列表，彻底杜绝首屏重复读取十几个 Parquet 文件。

2. 恢复完整十二维主动风控巡检并实现毫秒级缓存直读（修改 advisory_engine.py 与 app_gui.py）
第一，严禁在 app_gui.py 中用简陋的 if lock_funds 和 if c_free_funds 替代 ActiveRiskSentry.inspect_portfolio！
第二，在 app_gui.py 的 render_dual_wing_advisory_dashboard 中，根据当前账本持仓哈希值（holdings_hash：包含各基金代码、份额、最新净值、最小持有天数及当前风险档位 active_tier_val）缓存 sentry.inspect_portfolio 的完整 12 维巡检报告于 st.session_state 与 data/portfolio_watchdog.json 中。只要持仓与档位未变，首屏直接 1ms 读取完整报告！
第三，在双翼看板顶部的折叠栏标题与展开后的右翼列表中，真实渲染 sentry_rep["alerts"] 中的全部红黄牌预警（涵盖未满7天锁仓、临免赎倒计时、C类满30天、右侧破位与高水位移动止盈、超买拥挤、深套诊断、赛道与管理人集中度、迷你基清盘、大盘攻防线、动态相关性突变、适当性越界、盘中异动消耗安全垫、期权IV防暴跌哨），仅当 sentry_rep["all_passed"] 为 True 时才允许展示绿色全通状态。
第四，在左翼面板顶部恢复展示精炼的单行市场脉搏与信源验真徽章（将悬空未使用的 news_source_badge 真正渲染出来，消除死代码），并提供一个紧凑的「刷新雷达与风控」小按钮供用户手动强制重算。

3. 修复 get_60d_rolling_nav_and_trajectory 的样本外动态选股与扣费逻辑（修改 advisory_engine.py）
在 advisory_engine.py 第 475 至 505 行中，彻底废除 np.mean(r_day[:3]) 这种硬编码取前 3 列赛道的错误写法！在每个样本外交易日 d，必须使用截至 d-1 日的历史序列计算 14 赛道的四维特征向量 f_vec，分别用当前切片演化出的动态权重 w_opt 和静态基准权重 self.static_weights 点乘打分，选出真实的动态 Top 3 赛道与静态 Top 3 赛道计算第 d 日平均收益，并严格扣除双边 20 bps 换手摩擦成本（0.0020 * 换手比例），随后重新生成准确的 data/cache/factor_evolution_cache.json。

4. 清理首屏残留的伪交易待办预案横幅（修改 app_gui.py）
删除 app_gui.py 第 1258 至 1276 行渲染 latest_plan（采纳并执行此待办预案 / 提交在途单）的伪交易 UI 代码块，保持首屏在「顶部 4 卡 + 投顾参谋折叠栏 + 四宫格主导航栏」之间干净利落、零杂质。

三、 第二阶段：高定机构级审美打磨与开箱即用体验升级（修改 app_gui.py）

1. 根治主按钮番茄红撞色，统一高定机构蓝视觉体系
在 app_gui.py 的全局 CSS 中，为所有 Primary 主按钮（`button[kind="primary"], [data-testid="stBaseButton-primary"]`）显式绑定主题品牌色：`background: var(--accent-primary) !important; border: 1px solid var(--accent-primary) !important; color: #ffffff !important; border-radius: 8px !important; height: 40px !important; font-weight: 600 !important; box-shadow: 0 2px 6px rgba(29, 78, 216, 0.2) !important; transition: all 0.2s ease !important;`，并在 hover 态设置微亮过渡与上浮感，彻底消灭 Streamlit 原生刺眼的 `#ff4b4b` 番茄红按钮！

2. 修复 Tab 1 顶部 5 列控制栏垂直对齐错位
在 Tab 1 的 5 列参数控制栏（col_l1_cap, col_l1_tier, col_l1_rhythm, col_l1_adv, col_l1_btn）中，将第 4 列和第 5 列顶部的 `st.caption("微调参数")` 与 `st.caption("开始执行")` 替换为与原生 Widget Label 完全等高（24px 行高、相同字号与 margin-bottom）的 HTML 标签 `<div style="font-size: 14px; font-weight: 500; color: var(--text-primary); margin-bottom: 4px; height: 21px; line-height: 21px;">高级参数</div>` 与 `<div style="font-size: 14px; font-weight: 500; color: var(--text-primary); margin-bottom: 4px; height: 21px; line-height: 21px;">生成方案</div>`，确保 5 列输入框与按钮处于同一条水平基线上，严丝合缝！

3. 实现 Tab 1 开箱即用（消灭首次打开下半屏大片空白）
将 Tab 1 的默认状态改进为「开箱即用」：当用户首次进入且缓存为空时，使用高速缓存直接静默生成默认参数（10万元、C3平衡型）的建仓方案与核心 3 格指标条（不弹冗长的进度条遮挡视线，耗时控制在 100ms 内），让用户一打开软件就能直接看到完整的建仓执行表与风险收益指标；只有当用户主动修改参数并点击「生成实盘建仓方案」按钮时，才触发重新推演。

4. 统一顶部 4 张全局指标卡的视觉纯粹度
去掉顶部第 2 张卡片大标题文字前的绿球/火苗 Emoji（如将 `🟢 震荡收息期` 改为纯文字 `震荡收息期`，用文字颜色和左侧微胶囊圆点传达状态），使顶部 4 张全局卡片的字体、字号（18px 粗体）、行距与内边距 100% 呼应统一。

四、 第三阶段：强制重启服务并调用 /browser 进行实测与高定审美验收

完成上述代码修改后，必须先彻底终止旧的 8501 端口进程并清理旧缓存，重新启动最新服务，随后调用 /browser 打开 http://localhost:8501 逐项截图验证：
1. 验证首屏秒开与开箱即用：确认打开页面 1 秒内无白屏直接渲染出顶部 4 卡、投顾参谋栏、全宽四宫格皇家蓝大导航栏、以及 Tab 1 完整的 5 列对齐控制栏与默认建仓方案大表！
2. 验证按钮配色与水平对齐：肉眼确认 Tab 1 右侧的「生成实盘建仓方案」按钮已变为高级机构蓝（不再是刺眼的番茄红），且与左侧 3 个输入框水平完全对齐。
3. 验证双翼看板十二维风控与缓存：展开投顾参谋栏，确认左翼脉搏徽章与 Top 3 赛道卡正常显示，右翼能真实反映完整的十二维主动风控结果；检查磁盘确认 data/cache/radar_sectors_cache.json 与 data/cache/factor_evolution_cache.json 均已真实生成落盘。
4. 切换检查「持仓调仓」、「组合回测」、「穿透工具」及暗黑主题、640px 移动端视口，确认回测曲线真实无遮挡、全站视觉具备 90 分以上的高级金融终端质感。

五、 第四阶段：全量测试验证、Git 归档与生成 G15 世代指令（严守防转义命令标签门禁）

1. 运行全量自动化测试套件（包含 pytest tests/test_infra.py、tests/test_adv_final_closure.py、tests/test_g3_evolution_loop.py、tests/test_gui_multi_ledger_stress.py），并新增针对 radar_sectors_cache.json 真实落盘、get_60d_rolling_nav_and_trajectory 动态权重选股与扣费、以及首屏十二维风控完整性的单元测试，确保 100% 绿灯通过。确认四个只读裁判文件零修改，确认 data/ledgers_index.json 仅保留主实盘账本，清理所有临时脚本。
2. 将 G14 世代漏洞封堵与高定机构审美规范写入当前工作区根目录 GEMINI.md 与 PROGRESS_LOG.md，严禁触碰全局配置文件。
3. 执行 Git 提交与标签同步：运行 git add -A，运行 git commit 记录 G14 开发进程，使用 git tag -a 打上版本标签 v4.4-G14，最后运行 git push origin HEAD 与 git push origin --tags 同步至 GitHub 远端。严格遵守禁令：绝对禁止创建任何 GitHub Release。
4. 在最终报告末尾输出供下一轮直接复制执行的 G15 世代进化指令。
【阻塞性门禁警告：防客户端转义命令标签校验】：
由于客户端输入框在接收提示词时，会将 Markdown 链接形式的命令标签转义为带冒号的内部格式，你在最终报告中输出 G15 指令时，绝对禁止输出带冒号的 slashCommand: 格式！
你输出的 G15 指令中的四个命令标签，必须 100% 严格按照以下字符序列拼接输出（圆括号内使用英文分号）：
- goal 命令必须写为：[/goal](slashCommand;goal)
- boost 命令必须写为：[/boost](slashCommand;boost)
- teamwork 命令必须写为：[/teamwork](slashCommand;teamwork)
- browser 命令必须写为：[/browser](slashCommand;browser)
内审与外审代理在终审时必须执行字符串检索：若最终报告的 G15 指令中出现任何一处冒号形式的 slashCommand:，一律判定门禁失败打回重写！其余正文保持纯文本无特殊排版符号，包含全量测试验证、Git Commit 与 Git Tag 同步（禁止创建 Release）以及继续按上述精确格式生成下一代指令的自举要求。外部参考审计MD文件：c:\Users\deanc\Downloads\agy2_v8_code_audit_and_aesthetic_review.md 和 c:\Users\deanc\Downloads\agy2_ui_ux_audit_and_fix_plan (2).md

## Follow-up — 2026-11-09T11:20:39Z

[skip-interview] 需求已在首轮 Prompt 中 100% 完整详尽定义，四大代码漏洞与四大审美缺陷均已给出精准定位与修复方案，包含全量测试与 Git 标签要求。请直接跳过访谈，立即启动执行！

## Follow-up — 2026-11-09T14:56:17Z

启动 G15 世代长截图高清切片识别导入、真实29基存量账本实战诊断、破除唯算法论五维投顾备忘录、历史时点盲测时光机与砍除3D炫技图闭环任务

一、 核心产品理念纠偏与安全底线契约
1. 贯彻「拒绝技术炫技、一切服务于真实用户决策与赚钱」的全局准则：
第一，彻底砍除无用的炫技图表：立即从 Tab 1 和 Tab 2 中删除「蒙特卡洛极端承压 3D 分布曲面图」（render_monte_carlo_3d_chart），删除因子进化弹窗中晦涩的 RuleTree 代码框，凡是普通投资者无法 3 秒看懂的炫技元素一律转化为直白的人话结论与二维直观对照表。
第二，破除「唯算法论」：智能投顾绝不能只扔出冷冰冰的权重数字。必须在首屏与方案区实装「五维全息投顾首席备忘录」，从宏观政策、国际与汇率、产业估值、资金情绪、黑天鹅底线五个维度，用通俗专业的人话向用户讲清楚「现在市场发生了什么 -> 为什么这么配 -> 潜在风险点在哪里」。
第三，物理安全红线：严禁修改四个只读裁判文件 judge_engine.py、holdout_vault.py、AGENT_SPEC.md、tests/test_infra.py，严禁修改 DataLoader.simulate_execution 的默认函数签名与默认扣费逻辑。同步维护更新非只读测试文件确保 100% 绿灯通过。

二、 第一阶段：修复课题 1 抓出的 5 处 UI/UX 与代码对齐 Bug（修改 app_gui.py 与 portfolio_manager.py）

1. 修复右翼预警哨红牌变黄牌与详情丢失的严重对接 Bug（修改 app_gui.py 第 1310 至 1500 行）
在 render_dual_wing_advisory_dashboard 中，兼容 ActiveRiskSentry.inspect_portfolio 返回的真实字段格式：将判断条件修正为 `al_lvl in ("red", "CRITICAL")` 显示红色图标 `🔴` 与红色左边框，`al_lvl in ("yellow", "WARNING")` 显示黄色图标 `🟡`；将详情文本提取修正为 `alert.get("desc") or alert.get("detail") or alert.get("message", "")`，将建议提取修正为 `alert.get("action") or alert.get("suggested_action", "")`，确保十二维风控的红黄牌颜色与详细病因 100% 完整显示。

2. 修复 Tab 2 英文裸露表头与底部重复大按钮（修改 app_gui.py）
第一，在 Tab 2 调仓方案的「微观执行与尾盘净值锚定拆单计划」DataFrame 展示前，将英文列名 `phase, label, vol_ratio, slice_amount, strategy` 强制映射汉化为 `执行阶段, 窗口类型, 分配比例, 建议挂单金额(元), 微观执行策略`。
第二，清理 Tab 2 表格下方与底部的冗余按钮：将持仓表下方的「极速录基、批量文本导入、截图识别导入、历史撤销」统一收纳进顶部工具栏，删除调仓单最底部重复的第二个全宽蓝色覆盖按钮，仅保留一行清晰的操作栏（采纳并写入当前账本 ｜ 复制下单小抄 ｜ 送入回测对比）。

3. 修复 Tab 4 二级导航按钮堆叠与统一全站基金名称（修改 app_gui.py 与 portfolio_manager.py）
第一，将 Tab 4 穿透工具内部的 6 个二级模块入口改为单行紧凑分段切换（或干净的水平单行 Tab），消除两排大按钮与顶层四宫格主导航栏的视觉冲突。
第二，统一全站基金标准名称：排查并修正 `017436` 等标在不同字典中名称不一致的问题（统一为标准名称），确保全站单源同真。

4. 新增「📱 手机极简盯盘视图」一键切换开关（修改 app_gui.py）
在顶部或侧边栏醒目位置提供「📱 手机极简模式 / 🖥️ 桌面专业模式」切换开关。开启手机极简模式时，自动隐藏复杂的宽表与多维矩阵，以单列大字号卡片流聚焦展示：① 今日总资产与预估盈亏、② 14:30 尾盘关键操作指令、③ 持仓红黄牌风险提醒与截图导入入口。

三、 第二阶段：课题 2 落地 —— 破除唯算法论，实装「五维投顾首席备忘录」与「历史任意时点盲测时光机」（修改 advisory_engine.py、strategy_bridge.py、app_gui.py）

1. 实装「五维全息投顾首席备忘录」（修改 advisory_engine.py 与 app_gui.py）
在 advisory_engine.py 中新增 `generate_chief_advisor_memo(snapshot, holdings, radar_top3, sentry_rep)` 函数，并在首屏投顾参谋栏展开区及 Tab 1 方案顶部渲染一张结构清晰的「🧭 首席投顾五维决策备忘录」卡片，直观呈现：
- 宏观与政策面：基于 10Y 国债收益率、DR007 与 ERP 分位，解读当前国内货币环境与股债性价比定调；
- 国际与汇率面：基于 USD/CNH 离岸人民币汇率、美股与黄金联动信号，提示跨境 QDII 与黄金资产的汇率及溢价风险；
- 产业与估值面：指明当前处于底部黄金击球区的低估赛道与处于超买拥挤区需规避的赛道；
- 存量持仓病灶：一针见血指出当前账户的核心拖累源（如深套标的、碎片尾仓或赛道过度集中）；
- 今日明确行动准则：摒弃情绪干扰，给出今日 14:30 尾盘「该买谁、该卖谁、还是按兵不动吃息」的明确理由。

2. 实装「🕰️ 历史任意时点时光机盲测验证器」（修改 strategy_bridge.py 与 app_gui.py Tab 3）
在 Tab 3「组合回测」顶部新增「🕰️ 历史时点盲测验证（检验投顾真赚钱能力）」模块：
- 支持用户选择任意历史起点日期（预设快捷按钮：1年前今日、2024.09底部反转前、2022.04恐慌底、2021.02核心资产见顶日，或任意自定义日期）；
- 严格切断所选日期之后的一切未来数据，重演当时投顾引擎生成的配置方案，并全额计入真实申购费、阶梯赎回费、销售服务费、QDII 限购拆单及 T+1 确认延迟，输出持有 3 个月、6 个月、1 年及持有至今的真实到手净收益、最大回撤，并与同期沪深 300 及偏股基金基准同图对比，用真实历史截面铁证检验策略成色。

四、 第三阶段：课题 3 落地 —— 实装「📸 手机长截图高清切片识别导入引擎」、「🧹 碎片尾仓清理器」并预置用户真实 29 基实战账本（修改 portfolio_manager.py、multi_ledger_manager.py、app_gui.py）

1. 实装「📸 手机持仓超长截图无损切片 OCR/多模态导入引擎」（修改 portfolio_manager.py 与 app_gui.py Tab 2）
解决手机滚动长截图（宽高比 1:10 以上）直接整体识别或压缩导致文字模糊的痛点：
- 在 Tab 2 顶部工具栏实装「📸 截图导入持仓」弹窗，支持上传 PNG/JPG 手机持仓截图（兼容招行、支付宝、天天基金、且慢等主流 App 界面）；
- 编写长图自适应无损横向切片算法 `slice_long_screenshot_for_ocr(image_bytes)`：保持原始图片 100% 宽度不压缩，按每段高度 1000px、上下重叠 150px 自动切分为高清图块；
- 结合本地 OCR 引擎（支持 RapidOCR / PaddleOCR / EasyOCR / Windows OCR 或多模态解析兜底）与全市场基金名称模糊匹配器 `fuzzy_match_fund_by_name(raw_name)`（支持去除省略号与后缀模糊匹配 6 位代码），自动提取每行的「基金名称、持有金额、昨日收益、持有收益」，并根据 `投入成本 = 持有金额 - 持有收益` 自动算出精确持仓成本价与份额，生成可核对编辑的导入预览表，一键写入账本！

2. 实装「🧹 碎片尾仓/羊毛基一键诊断与免赎清理建议器」（修改 advisory_engine.py 与 app_gui.py Tab 2）
在 ActiveRiskSentry 与 Tab 2 诊断中新增「碎片尾仓清理诊断」：
- 自动扫描识别持仓金额小于 ¥200（或占比小于 1.0%）且持有满免赎期的碎片基金/红包羊毛基；
- 在 Tab 2 生成醒目的「🧹 碎片尾仓一键瘦身建议卡」，列出所有碎片基数量、可零费率无损回收的资金总额，支持一键在账本中模拟清理并归集至核心底仓。

3. 预置用户真实的 29 只基金（¥26,615.10）实战组合账本并完成全套实战体检
在 MultiLedgerManager 中内置或更新一个名为「实战存量组合（29只·¥2.66万）」的真实账本（严格还原用户截图中的 29 笔持仓结构：前 7 大核心仓位 5681.55元、5279.05元、4536.85元、4101.71元、2432.90元[-332.54]、2072.52元[-428.48]、1023.71元，3 只腰部仓 524.24元[-175.76]、395.73元、124.14元，以及后 19 只 89.60元至 0.59元的真实碎片尾仓，设置持有天数大于 365 天），支持在 Tab 2 账本下拉框中一键切换至该真实组合，直接展示针对该组合的：
① 19 只碎片尾仓（¥442.70）免赎回费一键清扫归并方案；
② 第 5、6、8 号深套亏损源（合计浮亏 -¥936.78）的去弱留强置换与网格回本测算；
③ 调仓优化前后的全周期净值与回撤对比。

五、 第四阶段：强制重启服务并调用 /browser 走查验收与生成 G16 指令

1. 彻底终止旧 8501 端口进程，启动最新服务，调用 /browser 打开 http://localhost:8501 逐页截图验证：
- 确认右翼预警哨红黄牌颜色正常、详情文字完整显示，确认 3D 曲面图已彻底移除，确认 Tab 2 英文表头已全部汉化且无重复大按钮；
- 确认「五维投顾首席备忘录」、「历史时点盲测时光机」、「📸 截图导入持仓」与「实战存量组合（29只·¥2.66万）」账本切换、碎片尾仓清理建议均真实可用且排版优雅。
2. 运行全量测试套件确保 100% 绿灯通过，更新项目根目录 GEMINI.md 与 PROGRESS_LOG.md，执行 git add、git commit、git tag -a v4.5-G15 并推送到远端（严禁创建 GitHub Release）。
3. 在最终报告末尾输出供下一轮直接复制执行的 G16 世代进化指令。
【阻塞性门禁警告：防客户端转义命令标签校验】：
由于客户端输入框会将命令标签转义为带冒号的内部格式，你在最终报告中输出 G16 指令时，绝对禁止输出带冒号的 slashCommand: 格式！四个命令标签必须 100% 严格按以下字符序列输出（圆括号内使用英文分号）：
- /goal
- /boost
- /teamwork
- /browser
内审与外审代理在终审时必须检查字符串：若出现任何冒号形式的 slashCommand:，一律打回重写！其余正文保持纯文本无特殊符号排版。

【附加参考审计文档与上传文件】：
参考审计报告：
- c:\Users\deanc\Downloads\agy2_v9_comprehensive_audit_and_real_portfolio_combat.md
- c:\Users\deanc\Downloads\agy2_ui_ux_audit_and_fix_plan (3).md
用户上传截图文件路径：
- Tab 1 全屏：C:/Users/deanc/.gemini/antigravity/brain/1395b6f9-733c-4446-9cdb-f33a19e5f711/.user_uploaded/media_1794236135870_70406a4d.png
- Tab 2 全屏：C:/Users/deanc/.gemini/antigravity/brain/1395b6f9-733c-4446-9cdb-f33a19e5f711/.user_uploaded/media_1794236135871_867d8f62.png
- Tab 3 全屏：C:/Users/deanc/.gemini/antigravity/brain/1395b6f9-733c-4446-9cdb-f33a19e5f711/.user_uploaded/media_1794236135873_ceb7673e.png
- Tab 4 全屏：C:/Users/deanc/.gemini/antigravity/brain/1395b6f9-733c-4446-9cdb-f33a19e5f711/.user_uploaded/media_1794236135874_90d104f5.png
- 用户 29 只真实基金手机超长截图：C:/Users/deanc/.gemini/antigravity/brain/1395b6f9-733c-4446-9cdb-f33a19e5f711/.user_uploaded/media_1794236135877_65af68f3.jpg

## Follow-up — 2026-11-09T14:59:30Z

[skip-interview] 用户已提供全套完备的实施方案与代码级指引，请直接开始执行 G15 世代任务，无需额外访谈，立即推进第一阶段至第四阶段的所有工作。
