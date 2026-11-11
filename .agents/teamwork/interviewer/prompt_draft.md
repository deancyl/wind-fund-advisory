启动 G16 世代五维投顾备忘录首屏横向矩阵提权、修复持仓成本属性Bug、手机端真OCR闭环与29基真实存量账本首屏实战演练任务。

Working directory: d:\Google\Workspace\Wind
Integrity mode: [OPEN: 团队行为限制模式]

参考外部审计文件：
- c:\Users\deanc\Downloads\agy2_ui_ux_audit_and_fix_plan (4).md
- c:\Users\deanc\Downloads\agy2_v10_comprehensive_audit_and_combat_review.md

## Requirements

### R1. 修复代码 Bug 并升级首屏「十维感知·五维横向投顾情报矩阵」
- 修复 `advisory_engine.py` (第 1545 至 1705 行) 中 `generate_chief_advisor_memo` 浮亏漏检 Bug：在遍历 holdings 计算单只基金盈亏率 `pl_ratio` 时，优先检查 `cost_price`（若大于 0 则 `cost_v = shares * cost_price`），否则若有 `floating_pnl_pct` 或 `pnl_pct`，则 `pl_ratio = float(pnl_pct) / 100.0`，同时兼容 `cost_nav * shares`，彻底修复因读取不存在的 `cost_value` 导致 `deep_loss_list` 永远为空的严重 Bug。
- 备忘录注入真实十维量化因果逻辑：宏观与政策面（10Y 国债收益率、DR007 利差、沪深300 ERP 分位）、国际与汇率面（USD/CNH 汇率、中美利差、黄金纳指联动及 QDII 溢价率警戒）、产业与估值面（Top 3 低估赛道及需规避高拥挤赛道）、存量持仓病灶（浮亏 >10% 出血点标的及金额、单只 <¥200 免赎碎片尾仓数量与可回收总额、单赛道集中度预警）、今日 14:30 明确行动准则（结合时钟、乖离率与锁定期给出尾盘操作结论）。
- 重构 `app_gui.py` 中的 `render_chief_advisor_memo_card` 为首屏直显的 1 行 5 列横向高密度情报矩阵卡：移出折叠框，置于顶部 4 张全局指标卡正下方、双翼折叠栏上方，采用等高响应式横向网格（`grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px;`），子卡片高度约 115px，带鲜明色标与核心结论胶囊，移动端自适应折行。

### R2. 首屏顶栏账本与模式切换、手机端真 OCR 闭环与 29 基真实存量组合实战
- 首屏顶栏新增「当前实战账本快捷切换 + 桌面/手机视图一键切换」控制条：在页面最顶部增加紧凑全局顶栏，包含系统品牌标识、行情源状态角标、「📂 当前激活账本」下拉选择框（支持直接切换 `实战存量组合（29只·¥2.66万）` 与 `主实盘账本`）及「🖥️ 桌面专业 / 📱 手机盯盘」一键切换胶囊。
- 手机极简盯盘模式打通真 OCR 切片导入与尾仓一键清扫：顶部提供账本切换与切回桌面模式按钮；展示五维极简摘要与尾仓一键清扫卡；用户上传长截图时，直接调用 `pm.parse_long_screenshot_holdings(mob_img.getvalue())` 执行切片识别与模糊匹配，展示预览表、反推本金与「一键覆盖/合并写入当前账本」按钮，严禁再用切回桌面的空话提示打发用户。
- 强化 29 基真实存量组合（¥26,615.10）实战演练与对比：`MultiLedgerManager` 启动时幂等挂载 29 只基金真实存量组合（总市值 ¥26,615.10，累计亏损 -¥953.40，投入本金 ¥27,568.50，前 7 大主力仓、腰部仓及 19 只碎片尾仓全部持有 > 365 天）；Tab 2 提供一键「🧹 执行三步瘦身重构模拟」面板，量化展示重构前后持仓数量、盘活资金、票息垫提升与回本天数缩短；Tab 3 增加「实战存量组合：原始29基 vs 投顾重构6基」近 1 年真规则（含全部真实费率、限购与 T+1）回测对比曲线。

### R3. 多模态与浏览器实盘级验收
- 终止旧 8501 端口进程并清理缓存，重新启动服务，调用 `/browser` 访问 `http://localhost:8501` 逐项截图核验：首屏 1 行 5 列横向决策备忘录直显、切换 29 基账本时病灶与尾仓识别、Tab 2 尾仓清扫与深套诊断、Tab 3 近 1 年重构回测图、以及手机极简模式下的账本切换与长截图真 OCR 解析预览。

### R4. 自动化测试、Git 归档与 G17 指令生成门禁
- 物理安全红线：严禁修改四个只读裁判文件（`judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py`），严禁修改 `DataLoader.simulate_execution` 的默认函数签名与默认扣费逻辑。
- 全量自动化测试：运行 `pytest tests/test_infra.py`、`tests/test_adv_final_closure.py`、`tests/test_g3_evolution_loop.py`、`tests/test_gui_multi_ledger_stress.py` 并新增针对 `generate_chief_advisor_memo` 对 `HoldingItem` 深套识别准确性（断言 `deep_loss_count >= 3`）的专项单测，确保 100% 通过。
- 更新根目录 `GEMINI.md` 与 `PROGRESS_LOG.md`，执行 git commit 与 tag `v4.6-G16` 并推送远端（严禁创建 GitHub Release）。
- 最终报告末尾输出 G17 世代进化指令，严格遵守防转义门禁：严禁输出带冒号的 `slashCommand:` 格式，四个命令标签必须严格输出为 `/goal`、`/boost`、`/teamwork`、`/browser`。

## Acceptance Criteria

### 核心代码修复与算法联动
- [ ] `advisory_engine.py` 修复属性名 Bug，兼容 `cost_price * shares`、`cost_nav * shares`、`floating_pnl_pct` 与 `pnl_pct`，`deep_loss_list` 准确识别出浮亏超 10% 的基金。
- [ ] `generate_chief_advisor_memo` 五维度完整接入宏观政策、国际汇率、产业估值、存量病灶、14:30 行动准则的十维量化数据。
- [ ] 专项单测验证 `generate_chief_advisor_memo` 对包含深套标的的持仓列表断言 `deep_loss_count >= 3` 成功通过。

### UI 交互与首屏体验
- [ ] 首屏无需点击展开即可在指标卡下方直显 1 行 5 列等高横向高密度情报矩阵卡（网格布局 `grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px;`），子卡片高度约为 115px。
- [ ] 页面最顶层常驻顶栏，包含「📂 当前激活账本」下拉框与「🖥️ 桌面专业 / 📱 手机盯盘」切换胶囊，可无障碍直接切换。
- [ ] 手机极简盯盘模式下，`st.file_uploader` 上传长截图后直接调用 `pm.parse_long_screenshot_holdings` 呈现解析预览与一键写入按钮，无假提示。

### 29 基真实账本与重构演练
- [ ] `MultiLedgerManager` 自动幂等挂载 29 基真实存量账本（市值 ¥26,615.10，投入本金 ¥27,568.50，累计收益 -¥953.40），且单测与 UI 均正常可用。
- [ ] Tab 2 提供该组合的三步瘦身重构对比面板（持仓数 29->6、盘活零费率尾仓资金、票息垫与回本期对比）。
- [ ] Tab 3 提供该组合原始 29 基 vs 投顾重构 6 基在真规则约束下的近 1 年净值与回撤对比图。

### 验证与红线
- [ ] 四个只读裁判文件零改动，`DataLoader.simulate_execution` 签名与逻辑零改动。
- [ ] 全量回归测试套件 100% 绿灯通过。
- [ ] `/browser` 浏览器核验截图覆盖首屏横向矩阵、29基账本演练、手机模式真 OCR 流程。
- [ ] G17 世代指令中绝对无 `slashCommand:` 冒号形式，四个标签为 `/goal`、`/boost`、`/teamwork`、`/browser`。
