# Dispatch Task: G14 Generation Orchestration

## 2026-11-09T11:23:29Z

Working directory: .agents/teamwork/orchestrator_17/
Reference: .agents/teamwork/ORIGINAL_REQUEST.md

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
