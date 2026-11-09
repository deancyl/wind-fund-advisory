# Dispatch Task: G15 Generation Orchestration

## 2026-11-09T15:02:00Z

Working directory: .agents/teamwork/orchestrator_18/
Reference: .agents/teamwork/ORIGINAL_REQUEST.md

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
