# Forensic Auditor Task Assignment: G5 世代独立法证审计

## 目标
对 G5 世代交付物执行严格的独立司法级法证审计，核查反作弊契约、只读裁判文件写保护、量化算法真实性、中国公募基金交易规则合规性、UI 复杂度守恒及 Git 归档禁令。

## 审计核查清单
1. **裁判文件只读硬红线核查**：
   - 检查 `judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py`（以及 `AGY2_FundAdvisory/` 下同名文件）是否绝对零修改；
   - 检查 `DataLoader.simulate_execution` 的默认函数签名与扣费逻辑是否保持原始。
2. **量化指标真实性与反作弊核查**：
   - 检查 `calculate_vwap_execution_slippage` 是否彻底消除了 `0.04/0.14/0.18` 及 `else 0.18` 固定常数；
   - 检查是否确实通过 `get_fund_real_volatility_and_bias` 从本地时序（parquet/indices/matrix）真实计算 20 日年化波动率与自身 MA20 乖离率；
   - 检查 14:30 尾盘估值异动是否基于真实盘中估值 `gszzl` 与真实日均波幅 `sigma_day`，严禁伪造早盘历史分时快照；
   - 检查单基历史 Beta 与组合加权 Beta、安全垫破净/回本模型是否基于 CAPM 协方差公式与真实账本数据。
3. **中国公募基金真实交易制度合规性核查**：
   - 严格遵循场外基金 15:00 单一未知净值确认制；
   - 严格遵循未满 7 天 1.50% 惩罚性赎回费与 FIFO 批次保护。
4. **前端界面复杂度守恒与移动端排版核查**：
   - 检查 `app_gui.py` 是否接入了历史三大拐点对照尺（首屏/Tab 1）、安全垫抗震承压看板（Tab 2）与尾盘异动标签；
   - 检查在增加新组件的同时是否精简了冗余文案（复杂度守恒）；
   - 检查是否具备 640px 移动端 CSS 自适应与 Tab 独立错误边界。
5. **工作区隔离与 Git 归档禁令核查**：
   - 检查全局 `c:\Users\deanc\.gemini\GEMINI.md` 是否零触碰；
   - 检查当前工作区根目录 `GEMINI.md` 与 `PROGRESS_LOG.md` 是否已正确沉淀 G5 经验；
   - 检查是否打上了 `v3.5-G5` 标签并推送远端；
   - 检查是否严格遵守禁令：**绝对未创建任何 GitHub Release**。
6. **全量自动化测试与服务健康核查**：
   - 独立运行全量测试套件（50 项用例），验证是否 100% 通过；
   - 探测 8501 端口服务存活状态（HTTP 200）。

## 裁决输出规范
在 `.agents/teamwork/auditor_prod_r12/handoff.md` 中输出详尽法医证据链与终审裁决：
- 若全部合规，给出明确裁决：`Verdict: CLEAN (or VICTORY CONFIRMED)`；
- 若发现任何作弊、伪造数据或红线越界，必须给出明确裁决：`Verdict: INTEGRITY VIOLATION`，并列出确凿证据。
完成后使用 send_message 向 orchestrator (ID: 71f16351-ac4e-45f7-b8a4-89e38ec8863c) 汇报。


## 2026-11-06T18:21:02Z
[Message] timestamp=2026-11-06T18:21:02Z sender=71f16351-ac4e-45f7-b8a4-89e38ec8863c priority=MESSAGE_PRIORITY_HIGH content=你是一个最高级别的法证审计员（teamwork_auditor）。
你的专属工作目录是：d:\Google\Workspace\Wind\.agents\teamwork\auditor_prod_r12\
上级调度员 ID: 71f16351-ac4e-45f7-b8a4-89e38ec8863c

【必须阅读的基准文档】
- 原始需求：d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- 项目架构与契约：d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_7\PROJECT.md
- 审计派发规范：d:\Google\Workspace\Wind\.agents\teamwork\auditor_prod_r12\DISPATCH.md
- 前期交付报告：
  - M1: d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r12_m1\handoff.md
  - M2: d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r12_m2\handoff.md
  - M3: d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r12_m3\handoff.md

【核心审计使命】
1. 绝对严查只读裁判文件（judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py）是否零修改，DataLoader.simulate_execution 默认签名与扣费逻辑是否保持原始；
2. 绝对严查代码中是否杜绝了伪随机数、假常数（0.04/0.14/0.18 及 else 0.18 是否彻底消除），是否基于本地真实 parquet 序列计算单基真实年化波动率与自身 bias_20；
3. 绝对严查 14:30 尾盘估值异动是否基于真实盘中估值 gszzl 与真实日均波幅 sigma_day，绝对杜绝伪造早盘分时快照；
4. 绝对严查是否严格遵循中国公募基金 15:00 唯一未知收盘价与未满 7 天 1.50% 惩罚性费率；
5. 绝对严查 app_gui.py 是否接入了历史三大拐点对照尺与安全垫抗震承压看板，是否遵循界面复杂度守恒（精简冗余文案），是否具备 640px 移动端 CSS 自适应与 Tab 独立错误边界；
6. 绝对严查全局 c:\Users\deanc\.gemini\GEMINI.md 是否零触碰，所有经验是否沉淀于工作区根目录 GEMINI.md；
7. 绝对严查是否打上 v3.5-G5 标签，是否严格遵守禁令“绝对禁止创建任何 GitHub Release”；
8. 独立运行全量测试套件（pytest 50 项用例）与 8501 端口服务存活探针（HTTP 200）。

【裁决要求】
在 d:\Google\Workspace\Wind\.agents\teamwork\auditor_prod_r12\handoff.md 中给出包含完整证据链的裁决报告。若全部合规，给出 Verdict: CLEAN；若有作弊或红线越界，给出一票否决 Verdict: INTEGRITY VIOLATION。完成后通过 send_message 向 71f16351-ac4e-45f7-b8a4-89e38ec8863c 汇报。注意：审计员严禁修改被审计源代码。
