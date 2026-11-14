# Original User Request

## Initial Request — 2026-11-14T08:56:36Z

针对 Wind 投顾系统启动 G18 世代生产环境迭代：修复首屏裁决台手机端高度溢出重叠、打通十维投票与定权优化器知行合一闭环、校准汇率与美债真实最新数据、实装存量账本首屏自动路由，并升级截图导入双因子匹配引擎与完成端到端双视口实测验收。

Integrity mode: development
The team must NOT: 严禁修改四个只读裁判文件 judge_engine.py、holdout_vault.py、AGENT_SPEC.md、tests/test_infra.py；严禁修改 DataLoader.simulate_execution 的默认函数签名与默认扣费逻辑；绝对禁止输出带冒号的 slashCommand: 格式；严禁创建 GitHub Release。

## Requirements

### R1. 第一阶段：修复 UI 溢出重叠与首次加载智能路由（app_gui.py）
- 在 `render_chief_advisor_memo_card`（约第 309 行）中移除 `.chief-memo-container` 的 `max-height: 120px;`，改为 `height: auto !important; min-height: 82px; overflow: visible !important;`；在 `@media (max-width: 768px)` 中为 `.chief-memo-capsule` 增加合理的内边距与折行保护，确保手机端 2 列网格绝不溢出外框、不遮挡下方组件。
- 在第 1111 行手机端 CSS 选择器中补齐 `> div[data-testid="stColumn"]`，排除 `stNumberInput` 内部加减按钮，防止数字输入框被错误切分。
- 将首屏「🧭 首席投顾今日裁决台」与下方的「双翼投顾参谋折叠栏」在视觉上无缝合体，消除多余空白与重复文字提示。
- 在 app_gui.py 会话首次初始化时（`if "_initial_ledger_routed" not in st.session_state:`），检测若当前激活账本为实战存量组合（或标的数 >= 10 只），自动路由聚焦至「💼 持仓调仓」工作区（设置 `st.session_state["pending_cross_tab_jump"] = {"tab_index": 1, "tab_name": "💼 持仓调仓"}`），默认展开持仓体检、19 只碎片尾仓一键清扫卡与调仓对比方案。

### R2. 第二阶段：打通「十维投顾投票 -> 组合定权优化器」知行合一闭环与真数据校准（data_loader.py, advisory_engine.py, portfolio_optimizer.py, strategy_bridge.py）
- 检查 `DataLoader.fetch_macro_cross_market_indicators` 与 `advisory_engine.py`：修正 `fx_rates.parquet` 或实时汇率接口读取逻辑，彻底替换 `6.6676` 旧汇率兜底值，确保 `usdcnh_rate` 反映真实最新离岸人民币汇率；修正 `bond_zh_us_rate.parquet` 最新非空行提取逻辑，确保 `cn_yield_10y` 与 `us_yield_10y` 均为真实最新交易日数据，杜绝 `5.0000` 硬编码整数字面量。
- 在 `execute_market_optimization_flow` 与 `StrategyBridge` 生成目标权重时，实时调用 `compute_ten_dimension_votes` 获取 `equity_tilt_pct`（动态权益倾斜度），将当前风险档位（C1~C5）的基准权益配比结合十维动态倾斜项在档位安全契约边界内动态浮动，并在方案结果字典中显式记录 `ten_dim_adjusted_equity_pct` 与调整原因，使今日裁决台推导公式与下方建仓/调仓表中的实际配比 100% 严丝合缝对应。

### R3. 第三阶段：强化截图导入「OCR文字 + 昨日收益率数学指纹」双因子精准匹配引擎（portfolio_manager.py, app_gui.py）
- 在 `portfolio_manager.py` 的 `parse_long_screenshot_holdings` 与 `fuzzy_match_fund_by_name` 中实装「昨日净值涨跌幅数学指纹交叉验真算子」：从截图中提取出某行基金的持有金额 $M$ 与昨日收益 $dM$ 时，自动计算该基金昨日隐含收益率 $r_{imp} = dM / (M - dM)$。
- 综合「OCR 识别出的名称关键词相似度（权重 60%）+ 本地基金净值库最新交易日涨跌幅与 $r_{imp}$ 接近度（误差 < 0.05%，权重 40%）」联合打分排序锁定 6 位基金代码，并在导入预览表中向用户展示「匹配置信度」与「隐含昨日涨跌幅核验结果」。
- 若截图中未能提取出昨日收益金额 $dM$ 或分母 $(M - dM) \le 0$，自动回退为 100% 依赖 OCR 文字关键词相似度进行匹配，并在导入预览表中明确标记“无收益率指纹”。

### R4. 第四阶段：物理安全红线、测试验收与交付约束
- 严禁修改 judge_engine.py、holdout_vault.py、AGENT_SPEC.md、tests/test_infra.py 四个只读文件；严禁修改 DataLoader.simulate_execution 的默认函数签名与默认扣费逻辑。
- 彻底终止旧 8501 端口进程，启动最新服务，调用 /browser 分别在 1920x1080 桌面视口与 390x844 手机视口下完成实测截图核验：核验手机视口下 `.chief-memo-container` 高度自适应撑开、零重叠、零溢出；核验汇率与美债数据已更新为真实最新截面（无 `6.6676`/`5.0000`）；核验切换到 29 基存量组合或首次加载该账本时自动进入「💼 持仓调仓」展示诊断与清扫卡。
- 运行全量自动化测试套件确保 100% 绿灯通过。更新 GEMINI.md 与 PROGRESS_LOG.md，执行 git add -A、git commit、git tag -a v4.8-G18 并推送到远端（严禁创建 GitHub Release）。
- 在最终报告末尾输出供下一轮直接复制执行的 G19 进化指令，命令标签严禁带冒号（必须为 /goal, /boost, /teamwork, /browser 纯文本字符序列）。

## Acceptance Criteria

### UI 自适应与智能路由
- [ ] 手机端视口（390x844）下 `.chief-memo-container` 自适应撑开，5 颗胶囊与下方组件零重叠、零溢出。
- [ ] 首次加载或切换至 29 基存量组合时，页面自动路由聚焦至「💼 持仓调仓」工作区并展开体检与清扫卡。
- [ ] 首屏「🧭 首席投顾今日裁决台」与下方的「双翼投顾参谋折叠栏」在视觉上无缝合体，无多余空白间隙。

### 宏观数据真实性与十维知行合一闭环
- [ ] 宏观汇率与美债收益率反映真实最新截面，代码中无 `6.6676` 与 `5.0000` 失真兜底值。
- [ ] `compute_ten_dimension_votes` 的输出真实传导至组合优化器与方案生成，在 C1~C5 档位边界内调节权益配比，方案字典包含 `ten_dim_adjusted_equity_pct`。

### OCR 收益率指纹双因子匹配
- [ ] 截图导入引擎包含 $r_{imp} = dM / (M - dM)$ 收益率指纹计算，并按 60% 文字 + 40% 净值涨跌幅联合打分。
- [ ] 缺失收益率指纹或分母非正时，平滑回退为 100% 文字匹配，并在预览表格中展示匹配置信度与核验结果。

### 验收与合规交付
- [ ] 四个只读文件（judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py）未被修改，DataLoader.simulate_execution 签名与扣费逻辑保持原样。
- [ ] 全量自动化测试套件运行并通过率 100%。
- [ ] /browser 在 1920x1080 与 390x844 双视口截图通过验收。
- [ ] git tag `v4.8-G18` 已创建并推送到远端，无 GitHub Release 创建。
- [ ] 最终报告末尾包含合规格式的 G19 指令，标签为 /goal, /boost, /teamwork, /browser（严禁带冒号转义）。
