# Scope: G16 世代系统重构与实战演练

## Architecture
- **Advisory Engine (`AGY2_FundAdvisory/advisory_engine.py`)**:
  - `generate_chief_advisor_memo`: 多字段兼容成本读取 (`cost_basis`, `cost_price * shares`, `cost_value`, `floating_pnl_pct`)，深套亏损识别 (`deep_loss_count >= 3`)，Tab 1 权重字典防护，19 只免赎碎片与 ¥442.70 严格对齐 (M1 DONE)。
- **Web UI & Visualization Layer (`AGY2_FundAdvisory/app_gui.py`)**:
  - 首屏 1 行 5 列横向等高情报矩阵卡 (`render_chief_advisor_memo_card`) 提权至指标卡正下方、折叠框上方 (M1 DONE)。
  - 全局紧凑顶栏：品牌标识与行情角标 + 「📂 当前激活账本」选择器 + 「🖥️ 桌面专业 / 📱 手机盯盘」切换胶囊 (M2)。
  - 手机极简盯盘视图修复：顶部返回/切账本控件 + 五维备忘录摘要 + 19只免赎碎片清扫卡 + 手机长截图真 OCR 切片解析、预览平账与一键入库闭环 (M2)。
  - Tab 2 29基实战三阶手术量化对比面板：联动 `estimate_rebalance_impact` 呈现 29->6 只、盘活 ¥442.70~¥962.57、票息垫提升、回本天数缩短 (M3)。
  - Tab 3 实战回测对比：原始29基 vs 投顾重构6基近1年真规则回测同图双曲线 (M3)。
- **Portfolio & Ledger Layer (`AGY2_FundAdvisory/portfolio_manager.py`, `multi_ledger_manager.py`, `strategy_bridge.py`)**:
  - `portfolio_manager.py`: `parse_smart_text_holdings` 正则前置清洗、直通 `fuzzy_match_fund_by_name`，封堵纯数字搜索 (M2)。
  - `multi_ledger_manager.py`: `combat_29_funds` 幂等挂载与单测目录隔离 (`self.root == WORKSPACE_ROOT`)，持有天数与成本核验 (M3)。
  - `strategy_bridge.py`: `run_historical_time_machine_backtest` 动态再平衡，消除 2024.09 踏空 (M3)。

## Feature Inventory
| # | Feature | Description | Milestone | Source | Status |
|---|---------|-------------|-----------|--------|--------|
| 1 | 修复 memo 成本属性 Bug 并强化真实多源联动 | 修复 advisory_engine.py 读取 cost_value Bug，兼容多字段识别深套标的，防护 Tab 1 权重字典 | M1 | Request §二.1 | DONE |
| 2 | 重构首屏 1行5列横向高密度投顾情报矩阵 | app_gui.py 移出折叠框至指标卡正下方，重构为 1行5列等高网格，自适应折行 | M1 | Request §二.2 | DONE |
| 3 | 首屏全局顶栏账本与视图双控制条 | app_gui.py 顶部插入品牌/角标 + 当前账本选择 + 桌面/手机切换胶囊 | M2 | Request §三.1 | PLANNED |
| 4 | 手机极简盯盘真 OCR 切片解析与一键入库闭环 | 手机视图补齐导航与五维摘要，对接 slice_long_screenshot_for_ocr 与平账预览 | M2 | Request §三.2 | PLANNED |
| 5 | portfolio_manager 模糊匹配链路与数字防截断修复 | parse_smart_text_holdings 接入 fuzzy_match_fund_by_name，前置清洗昨日收益 | M2 | External Audit P0.2 | PLANNED |
| 6 | 29基真实账本幂等挂载与单测隔离保护 | multi_ledger_manager 自动挂载 combat_29_funds，隔离单测 temp_workspace 避免断言失败 | M3 | Request §一.2, §三.3 | PLANNED |
| 7 | Tab 2 29基三步瘦身手术量化对比与联动 | 联动 estimate_rebalance_impact，输出持仓29->6、盘活资金、票息垫提升与回本天数缩短 | M3 | Request §三.3 | PLANNED |
| 8 | Tab 3 近1年真规则回测同图对比与时光机动态调仓 | 原始29基 vs 重构6基真费率回测对比，时光机 2024.09 动态再平衡消除踏空 | M3 | Request §三.3 | PLANNED |
| 9 | 全量自动化单测回归与新增深套识别专项测试 | 运行 test_infra, test_adv_final_closure 等，新增 HoldingItem deep_loss_count>=3 断言 | M4 | Request §五.1 | PLANNED |
| 10 | 物理只读红线审计、服务平滑重启与多模态验收 | 校验4个裁判文件哈希，平滑重启8501端口，/browser 多模态验证 | M4 | Request §四, §五 | PLANNED |
| 11 | 工作区 GEMINI.md/PROGRESS_LOG 沉淀与 G17 纯文本指令输出 | 严格执行防转义门禁，禁止冒号 slashCommand:，输出纯文本 /goal, /boost, /teamwork, /browser | M4 | Request §五.2, §五.3 | PLANNED |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | 投顾备忘录 Bug 修复与首屏 1行5列横向情报矩阵 | Features 1, 2 (advisory_engine.py, app_gui.py) | none | DONE |
| M2 | 全局顶栏控制条、手机模式真 OCR 闭环与模糊匹配主干打通 | Features 3, 4, 5 (app_gui.py, portfolio_manager.py) | M1 | IN_PROGRESS |
| M3 | 29基真实账本实战演练、Tab 2 手术面板与 Tab 3 回测对比 | Features 6, 7, 8 (multi_ledger_manager.py, strategy_bridge.py, app_gui.py) | M1, M2 | PLANNED |
| M4 | 物理红线法证审计、全量单测、服务重启多模态验收与 G17 归档 | Features 9, 10, 11 (tests, git, browser) | M1, M2, M3 | PLANNED |
