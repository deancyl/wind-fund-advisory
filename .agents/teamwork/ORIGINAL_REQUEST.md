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
