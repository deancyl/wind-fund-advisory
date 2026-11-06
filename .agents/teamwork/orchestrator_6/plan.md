# Project Plan: 终极专业度与工程闭环校准

## Architecture
- **Quant Core Layer (`portfolio_manager.py`, `strategy_bridge.py`)**:
  - `classify_fund_asset_class`: 消除死代码，升级本体方法，全基金池映射 9 大标准资产大类（纯债固收、黄金对冲、美股海外对冲、A股红利低波、A股红利高股息、科技成长进攻、中小盘成长、中盘均衡、核心蓝筹），杜绝“其他权益资产”。
  - `calculate_portfolio_yield_cushion`: 真实底层资产收益率基准加权计算，输出加权年化率、年化金额、月均金额及现金分红预估。
  - `evaluate_rebalance_audit`: 初始躺平影子组合 vs 实盘当前总资产，动态计算调仓主动管理净增厚及规避的费率损耗。
- **GUI & View Layer (`AGY2_FundAdvisory/app_gui.py`)**:
  - 热重载 `FundHolding, HoldingItem` 显式导入补齐，杜绝 Tab 4 缓存 `NameError`。
  - Tab 2 一键全案优先自动提交编辑表格。
  - Tab 2 工具坞同公司基金低摩擦转换排除 QDII 海外基金，添加交割提示条；Tab 1 & Tab 2 提供精确估值与交割类型标注。
  - 侧边栏行情源健康度徽座（实时源 vs 本地离线快照）。
  - Tab 4 A/C 算费工具使用 `@st.fragment` 局部刷新，侧边栏零 `@st.fragment` 引用。
- **Verification & Safety Layer**:
  - 4 大裁判文件 SHA256 锁定校验。
  - 自动化回归套件与 3 大专项测试全票通过。
  - 8501 端口服务平滑重启与 HTTP 200 探针。

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | 热重载导入补齐与一键全案自动保存 | app_gui.py 补全 FundHolding/HoldingItem 导入；一键全案先 commit 表格 | M2 | R1 |
| 2 | 全基金池 9 大标准大类对齐 | portfolio_manager.py 与 app_gui.py 对齐本体分类器，9 大类映射，测试覆盖 | M1 | R2 |
| 3 | QDII 跨时区交割与同公司转换隔离 | 同公司转换排除 QDII 并提示；Tab 1/2 添加交割估值提示 | M2 | R3 |
| 4 | 组合年度股息与票息安全垫精算引擎 | StrategyBridge 实装真实数学计算，Tab 1 步骤二 & Tab 2 步骤一渲染 | M1 & M2 | R4 |
| 5 | 实盘调仓复盘 vs 影子组合账单 | pm.evaluate_rebalance_audit 真实数学计算，Tab 2 档案子页 3 列卡片渲染 | M1 & M2 | R5 |
| 6 | 数据源健康徽座与 @st.fragment 局部刷新 | 侧边栏行情源状态；Tab 4 A/C 算费局部刷新 | M2 | R6 |
| 7 | 物理红线与三阶专项及全量测试 | 裁判文件零改动；3 大专项测试 + pytest + AppTest + 8501 探针 | M3 | R7 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M0 | 全局代码勘测与技术方案细化 | 3 位 Explorer 分工勘测量化核心、GUI 现有逻辑与测试基线 | none | DONE |
| M1 | 量化策略与组合管理核心升级 | R2 (分类器升级), R4 (股息安全垫引擎), R5 (影子组合调仓复盘) | M0 | DONE |
| M2 | GUI 工程化打通与交互渲染升级 | R1 (热重载&自动保存), R3 (QDII 隔离&标注), R4-UI, R5-UI, R6 (行情徽座&局部刷新) | M1 | DONE |
| M3 | 端到端专项测试、裁判红线法证审计与服务重启 | R7 (3 大专项测试, pytest 全通, AppTest 4-Tab 0 异常, 8501 服务平滑重启, 法证审计) | M1, M2 | DONE |
