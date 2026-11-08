启动 G10 世代多资产相关性压力突变防御、极端流动性冲击动态滑点补偿与大额账本穿透式蒙特卡洛压力测试闭环任务。

Working directory: d:\Google\Workspace\Wind
Integrity mode: development

## Reference Materials
- 核心代码路径：
  - Streamlit GUI 主程序：`AGY2_FundAdvisory/app_gui.py` (端口 8501)
  - 投顾决策与相关性模块：`advisory_engine.py`
  - 组合管理与压力测试：`portfolio_manager.py`
  - 数据加载与执行模拟：`data_loader.py`
  - 裁判防作弊基线：`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`
- 基线版本与状态：v3.9-G9 (commit ba4cda9)，59 项现有自动化测试套件 100% 通过。

## Verification Resources
- 工作区现有 59 项全量自动化测试套件与 4 个只读裁判文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）。
- 测试套件中针对多资产相关性突变预警、流动性冲击折价及蒙特卡洛压力测试新增的专项自动化测试用例。
- 本地 Streamlit 服务端点与健康探针（`http://127.0.0.1:8501/_stcore/health`），配合 `/browser` 工具进行多模态视觉走查。

## Requirements

### R1. 核心安全底线与反作弊契约
- 严禁修改四个只读裁判文件：`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`。
- 严禁修改 `DataLoader.simulate_execution` 的默认函数签名与默认扣费逻辑。
- 严禁使用伪随机数、线性插值伪序列或静态保底常数伪造金融指标；严格遵循 `AGENT_SPEC.md` 铁律，严禁任何形式的未来函数。
- 夏普比率计算必须强制扣减 2.0% 年化无风险利率。
- 严禁触碰全局配置文件 `c:\Users\deanc\.gemini\GEMINI.md`，所有经验规范必须写入当前工作区根目录 `GEMINI.md` 与 `PROGRESS_LOG.md`。

### R2. 相关性压力突变预警与跨资产流动性平移预案
- 在 `advisory_engine.py` 与 `portfolio_manager.py` 中升级相关性压力突变预警机制。
- 当大盘指数急跌时，动态测算红利低波与高 Beta 权益板块的下行协方差突变；若相关系数跳升至 0.80 以上，自动启动跨资产流动性平移预案。
- 流动性平移预案须将高估值与高波标的定向减仓，平移至纯债与实物黄金联接资产。

### R3. 场外公募基金微观执行冲击与底层流动性折价惩罚
- 在 `data_loader.py` 与 `advisory_engine.py` 中升级微观执行冲击模型。
- 针对场外公募基金，结合基金管理人季报披露的前五大重仓股日均成交额与基金规模比例，真实精算大额赎回对底层资产的流动性折价惩罚，杜绝使用单一线性换算。

### R4. 穿透式多周期蒙特卡洛压力测试
- 在 `portfolio_manager.py` 中实装多周期穿透式蒙特卡洛压力测试。
- 基于块重采样（Block Bootstrap），结合投资者风险等级 C1 至 C5，自动输出当前组合在 2008 年金融危机、2015 年流动性踩踏及 2024 年初小盘股流动性危机三大极端情景下的最大回撤预测与流动性变现天数。

### R5. 本地服务平滑重启与多模态视觉走查闭环
- 代码修改完成后，彻底终止旧 8501 端口进程，平滑启动最新服务并核验 `http://127.0.0.1:8501/_stcore/health`。
- 调用 `/browser` 打开 `http://localhost:8501` 逐项核查真实渲染画面与数值逻辑：
  - 核查首屏双翼看板：验证多资产相关性突变预警指示卡与压力测试流动性指标；
  - 核查 Tab 1 与 Tab 2：验证大额订单流动性折价明细表与蒙特卡洛压力测试三维分布图；
  - 核查亮色、暗黑主题及 640px 移动端视口，确认图表、文字与表格零截断、零水平溢出。

### R6. 全量自动化测试验证、Git 版本归档与 G11 指令自举
- 运行全量自动化测试套件，并在测试套件中新增针对多资产相关性突变预警、流动性冲击折价及蒙特卡洛压力测试的专项测试，确保原有与新增测试 100% 绿灯通过。
- 确认四大只读裁判文件零修改；确认数据目录仅保留主实盘账本。
- 将 G10 世代整改成果更新写入工作区根目录 `GEMINI.md` 与 `PROGRESS_LOG.md`。
- 执行 Git 提交与标签同步：运行 `git add -A`，运行 `git commit` 记录 G10 世代开发进程，使用 `git tag -a` 打上版本标签 `v3.10-G10`，运行 `git push origin HEAD` 与 `git push origin --tags` 同步至远端；严禁创建任何 GitHub Release。
- 最终必须通过独立的胜利审计（Victory Audit）确认。
- 在最终报告末尾，基于走查体验输出一段供下一轮直接复制执行的 G11 世代进化指令（保持纯文本干净排版，不使用任何表情符号、星号、反引号、数学公式符号或装饰性分隔线，包含 `/browser` 走查、全量测试与 Git 标签同步自举要求）。

## Acceptance Criteria

### 核心安全底线与防作弊验证
- [ ] 四大只读裁判文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）哈希值未发生变动，零修改。
- [ ] `DataLoader.simulate_execution` 默认函数签名与默认扣费逻辑保持只读。
- [ ] 所有金融指标计算无伪随机数、线性插值伪序列或静态保底常数，无未来函数；夏普比率计算扣减 2.0% 年化无风险利率。
- [ ] 全局配置文件 `c:\Users\deanc\.gemini\GEMINI.md` 零修改；整改成果沉淀于工作区根目录 `GEMINI.md` 与 `PROGRESS_LOG.md`。

### 金融量化与流动性风控核心
- [ ] `advisory_engine.py` 与 `portfolio_manager.py` 成功实装相关性压力突变预警：大盘急跌且红利低波与高Beta权益板块下行相关系数 > 0.80 时，确定性触发流动性平移预案，将高估值高波标的平移至纯债与实物黄金联接资产。
- [ ] `data_loader.py` 与 `advisory_engine.py` 成功实装基于季报前五大重仓股日均成交额与基金规模比例的微观执行冲击折价模型，非单一线性换算。
- [ ] `portfolio_manager.py` 成功实装块重采样蒙特卡洛压力测试，针对 C1 至 C5 风险等级输出 2008、2015、2024 年初三大极端情景的最大回撤预测与流动性变现天数。

### 服务平滑重启与 UI 视觉走查
- [ ] 旧 8501 端口服务彻底终止，新服务平滑启动且 `http://127.0.0.1:8501/_stcore/health` 返回正常。
- [ ] 首屏双翼看板正常显示多资产相关性突变预警指示卡与压力测试流动性指标。
- [ ] Tab 1 与 Tab 2 正常渲染大额订单流动性折价明细表与蒙特卡洛压力测试三维分布图。
- [ ] 在亮色、暗黑主题以及 640px 移动端视口下，图表、文字与表格零截断、零水平溢出。

### 自动化测试、版本归档与 G11 自举
- [ ] 全量自动化测试（含原有 59 项及新增针对相关性突变预警、流动性冲击折价、蒙特卡洛压力测试的专项测试）100% 通过。
- [ ] 数据目录仅保留主实盘账本。
- [ ] 本地 Git 提交完成并成功创建 `v3.10-G10` 注释标签，代码与标签推送至远端 `origin`；无任何 GitHub Release 创建。
- [ ] 独立胜利审计（Victory Audit）通过确认。
- [ ] 报告末尾输出无表情符号、无星号、无反引号、无数学公式符号、无装饰性分隔线的纯文本 G11 世代进化指令。
