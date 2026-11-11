# Project: G15 Generation Full-Stack System Upgrade

## Architecture
- **Web UI & Visualization Layer**: `AGY2_FundAdvisory/app_gui.py`
  - 彻底根除 3D 曲面图与因子进化 RuleTree 代码框，转为 2D 危机承压对照表与机制表
  - 修复右翼预警哨红黄牌与详情丢失 Bug，按严重度排序置顶致命风险
  - Tab 2 DataFrame 表头强制中文映射，清除底部重复全宽蓝色按钮，顶部工具栏收纳 6 键矩阵
  - Tab 4 二级导航改造为单行紧凑分段切换器（`st.segmented_control` / horizontal radio）
  - 全站基金名称归一（`017436` 统一为“华安纳斯达克100ETF联接A”，消除 `存量标的_XXXXXX` 与假锁仓）
  - 新增「📱 手机极简盯盘视图 / 🖥️ 桌面专业模式」一键切换开关与三大单列卡片流
- **Chief Advisory & Memo Layer**: `AGY2_FundAdvisory/advisory_engine.py`, `app_gui.py`
  - 实装 `generate_chief_advisor_memo(snapshot, holdings, radar_top3, sentry_rep)`
  - 五维全息决策维度：宏观政策、国际汇率、产业估值、存量病灶、今日明确行动准则（14:30 尾盘决策）
  - 前端实装 `render_chief_advisor_memo_card`，在首屏展开栏与 Tab 1 方案顶部同源双向渲染
- **Blind Backtest & Time Machine Layer**: `AGY2_FundAdvisory/strategy_bridge.py`, `app_gui.py` Tab 3
  - 实装 `run_historical_time_machine_backtest(target_date, tier, capital, df)`
  - 严格切断所选日期之后未来数据（Point-in-Time 零未来函数），重演当时投顾权重
  - 全额扣除公募交易摩擦（0.12% 申购费、日度 0.40% 销售服务费、持有天数阶梯赎回费未满7天 1.50%）
  - 输出 3M、6M、1Y 及持有至今净收益与最大回撤，同图对比同期沪深300与50/50平衡基准
- **Long Screenshot OCR, Tail Cleaner & Combat Ledger Layer**: `portfolio_manager.py`, `multi_ledger_manager.py`
  - 实装 `slice_long_screenshot_for_ocr(image_bytes)`（100% 原始宽度，1000px 切片，150px 重叠）
  - 集成本地离线 `rapidocr_onnxruntime` 与 28,177 基金字典模糊匹配 `fuzzy_match_fund_by_name`
  - 会计恒等式成本反算，修复负收益被 `abs()` 篡改与小额 `<100` 元被丢弃的 P0 Bug
  - 在 `ActiveRiskSentry` 实装第 13 维度「碎片尾仓清理诊断」（<¥200 或 <1.0% 且满免赎期），修复 `<2000` 误杀主力资产缺陷
  - 在 `MultiLedgerManager` 预置「实战存量组合（29只·¥2.66万）」，精确平账至 ¥26,615.10，实装 19 只碎片尾仓清扫、3 大深套源手术方案与调仓前后全周期对比
- **Physical Safety Redline Layer**:
  - `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`（物理只读红线，严禁修改）
  - `DataLoader.simulate_execution` 默认签名与默认扣费逻辑绝对锁定
  - G16 指令命令标签防转义门禁（绝对禁止带冒号 `slashCommand:` 格式，严格输出纯文本形式 `/goal`, `/boost`, `/teamwork`, `/browser`）

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | 彻底砍除 3D 曲面图与 RuleTree 代码框 | 将 render_monte_carlo_3d_chart 替换为 2D 危机承压对照表；RuleTree 替换为 2D 参数机制表 | M1 | Survey 1 |
| 2 | 修复右翼主动风控红黄牌与详情丢失 | al_lvl in ("red", "CRITICAL") -> 🔴, "desc" 详情提取与严重度排序 | M1 | Survey 1 |
| 3 | Tab 2 DataFrame 表头汉化与按钮收纳 | 映射汉化微观执行表头；删除底部重复全宽蓝色按钮；顶部工具栏收纳 6 键矩阵 | M1 | Survey 1 |
| 4 | Tab 4 单行分段导航与全站基金名称归一 | 6 模块改为单行 st.segmented_control；统一 017436 为“华安纳斯达克100ETF联接A”并修复新买假锁仓 | M1 | Survey 1 |
| 5 | 「📱 手机极简盯盘视图 / 🖥️ 桌面专业模式」 | 侧边栏/顶栏模式开关；手机模式单列呈现总资产、14:30 操作指令、核心红黄牌与截图上传入口 | M1 | Survey 1 |
| 6 | 五维全息投顾首席备忘录算子 | advisory_engine.py 新增 generate_chief_advisor_memo，包含宏观、汇率、产业、病灶、尾盘五维 | M2 | Survey 2 |
| 7 | 备忘录前端同源卡片渲染 | app_gui.py 实装 render_chief_advisor_memo_card，首屏与 Tab 1 顶部双向渲染 | M2 | Survey 2 |
| 8 | 历史任意时点盲测时光机引擎 | strategy_bridge.py 实装 run_historical_time_machine_backtest，严格零未来数据泄漏与全公募扣费 | M2 | Survey 2 |
| 9 | Tab 3 顶部时光机模块界面与同图对比 | 4 大预设快捷按钮 + 自定义日期；4 周期指标卡与 Plotly 无遮挡走势对比图 | M2 | Survey 2 |
| 10 | 手机长截图高清切片算法 | slice_long_screenshot_for_ocr 100% 原始宽度不压缩，1000px 切片，150px 垂直重叠 | M3 | Survey 3 |
| 11 | 本地离线 OCR 与基金字典模糊匹配 | rapidocr_onnxruntime 本地推理；基于 28,177 基金字典模糊匹配 6 位代码并反算成本修复负收益 abs Bug | M3 | Survey 3 |
| 12 | Tab 2 截图导入交互弹窗与预览编辑表 | 支持手机长图上传、自动切片识别、st.data_editor 预览核对与一键写入账本 | M3 | Survey 3 |
| 13 | 碎片尾仓/羊毛基一键诊断与免赎清理器 | ActiveRiskSentry 新增第 13 维诊断；Tab 2 醒目建议卡支持零费率清扫归集至核心底仓 | M3 | Survey 3 |
| 14 | 预置用户真实 29 只基金实战组合账本 | MultiLedgerManager 预置 combat_29_funds，精确平账至 ¥26,615.10，天数 400 天 | M3 | Survey 3 |
| 15 | 29 基实战账本全套体检方案展示 | 19 只碎片尾仓清扫方案、3 大深套源（-¥936.78）手术方案、调仓优化前后全周期对比 | M3 | Survey 3 |
| 16 | 物理红线校验与全量自动化测试套件回归 | 校验 4 只读文件哈希；新增 OCR、备忘录、时光机、29 基账本单元测试，100% 绿灯通过 | M4 | Survey 1,2,3 |
| 17 | 8501 端口平滑重启与 /browser 页面走查 | 终止旧进程，启动最新服务，/browser 逐页截图核验各模块排版与功能 | M4 | ORIGINAL_REQUEST |
| 18 | Git 标签推送与分号锁定 G16 世代指令 | 更新 GEMINI.md/PROGRESS_LOG.md，git tag v4.5-G15 并 push，输出严格纯文本无冒号 G16 指令 | M4 | ORIGINAL_REQUEST |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | 根治 5 处 UI/UX 缺陷与代码对齐 Bug，砍除 3D 曲面图与 RuleTree 代码框 | Features 1-5: 3D/RuleTree 移除, 右翼预警对接, Tab 2 表头与按钮重构, Tab 4 分段导航与 017436 名称归一, 手机极简视图 | none | DONE |
| M2 | 实装五维全息投顾首席备忘录与历史任意时点盲测时光机验证器 | Features 6-9: generate_chief_advisor_memo 算子, render_chief_advisor_memo_card, run_historical_time_machine_backtest, Tab 3 时光机前端 | M1 | DONE |
| M3 | 实装手机长截图高清切片识别导入、碎片尾仓免赎清理器与 29 基真实存量账本 | Features 10-15: slice_long_screenshot_for_ocr, 本地 RapidOCR 识别, 截图导入弹窗, 碎片尾仓清理诊断, 预置 combat_29_funds 账本与体检 | M1, M2 | DONE |
| M4 | 物理红线校验、全量测试回归、服务平滑重启、/browser 页面走查验收与 G16 指令 | Features 16-18: 物理红线校验, 针对性测试与全量回归, 8501 平滑重启, /browser 走查, Git tag v4.5-G15, 纯文本无冒号 G16 指令 | M1, M2, M3 | DONE |

## Interface Contracts
### M1 ↔ M2: Advisory Dashboard Container & Theme Contract
- **File**: `AGY2_FundAdvisory/app_gui.py` & `advisory_engine.py`
- **Contract**:
  - `generate_chief_advisor_memo` 返回结构包含 5 大顶级键：`macro_policy`, `international_fx`, `industry_valuation`, `portfolio_pathology`, `action_directive`；
  - `render_chief_advisor_memo_card` 接收 memo 字典并在首屏与 Tab 1 顶部同源渲染。

### M1 ↔ M3: Mobile View & Tab 2 Toolbar Contract
- **File**: `AGY2_FundAdvisory/app_gui.py` & `portfolio_manager.py`
- **Contract**:
  - Tab 2 顶部工具栏包含 `📸 截图导入` popover 入口，调用 `parse_screenshot_ocr_holdings`；
  - 手机极简视图读取 `pm.holdings` 与 `sentry_rep` 紧凑渲染总资产、14:30 指令与红黄牌。

### M2 ↔ M3: ActiveRiskSentry Tail Cleaner & Pathology Interface
- **File**: `AGY2_FundAdvisory/advisory_engine.py`
- **Contract**:
  - `ActiveRiskSentry.inspect_portfolio` 第 13 维返回 `dimension == "碎片尾仓清理"`，包含 `action_type == "sweep_tail_funds"`, `recoverable_cash`, `tail_codes`；
  - `generate_chief_advisor_memo` 读取 `sentry_rep` 并将碎片尾仓统计反映于 `portfolio_pathology` 维度。

### M3 ↔ M4: Combat Ledger Exact Accounting & Test Contracts
- **File**: `AGY2_FundAdvisory/multi_ledger_manager.py` & `tests/`
- **Contract**:
  - `MultiLedgerManager.get_instance().get_pm("combat_29_funds")` 总市值严格等于 `26615.10`（误差 `< 0.05` 元），持仓只数严格等于 29 只；
  - 4 个只读裁判文件 SHA256 绝对一致，`tests/test_infra.py` 100% 绿灯。

## Code Layout
- `AGY2_FundAdvisory/`
  - `app_gui.py`: UI 视图与设计系统 (M1, M2, M3, M4)
  - `advisory_engine.py`: 五维备忘录、主动风控哨第 13 维度 (M1, M2, M3)
  - `strategy_bridge.py`: 历史时点盲测时光机引擎、标的名称池补齐 (M1, M2)
  - `portfolio_manager.py`: 长截图切片、模糊匹配、成本反算修正、3D表替代 (M1, M3)
  - `multi_ledger_manager.py`: combat_29_funds 账本预置与管理 (M3)
  - `data_loader.py`: 物理签名锁定 (只读保护)
- `tests/`:
  - `test_infra.py`: 只读物理裁判（严禁修改）
  - `test_adv_final_closure.py`: 既有回归测试（非只读断言微调）
  - `test_g15_phase2_memo_and_timemachine.py`: M2 增量测试
  - `test_g15_phase3_ocr_and_combat29.py`: M3 增量测试
