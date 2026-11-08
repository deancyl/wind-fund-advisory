# G9 世代实施路线图 (Plan)

## 目标
落地 G9 世代量化因果律严苛纠偏、防未来函数样本外滚动演化、真数据防幻觉锚定与 Brinson 归因及适当性主动风控闭环。

## 阶段规划
### Phase 0: 深度勘测与架构映射 (Survey & Architecture Mapping)
- 派发 3 位 Explorer 分别深入勘测：
  1. `explorer_g9_survey_1`: `OnlineHeuristicFactorEvolver` 消除未来函数、换手摩擦扣减、夏普无风险利率扣减、Walk-Forward 5日滚动演化轨迹、交易日对齐与估值去趋势中枢；
  2. `explorer_g9_survey_2`: `ActiveRiskSentry` 真实规模穿透与告警、`OpportunityRadarEngine` 最后一根 K 线真实重算、动态量化证据链合成器、快讯信源联网与离线缓存明确标识；
  3. `explorer_g9_survey_3`: `PortfolioManager` Brinson 三维超额收益归因拆解、投资者适当性 (C1-C5) 越界主动预警及一键降波、测试用例现状与裁判文件哈希基线。
- 汇总 3 份勘测报告，更新 `PROJECT.md`。

### Phase 1: 里程碑 1 (M1) — 量化因果律严苛纠偏与真数据底座实装
- 调度 Worker 执行核心量化算法修复；
- 调度 Reviewers (2位) 与 Challengers (2位) 独立核查因果性与数值精度；
- 调度 Forensic Auditor (teamwork_auditor) 执行无未来函数与零伪常数法证；
- 门禁通过后标记 M1 DONE。

### Phase 2: 里程碑 2 (M2) — 投资者适当性风控、异动传导、Brinson 归因与 UI 深度闭环
- 调度 Worker 落地 ActiveRiskSentry 适当性预警、盘中异动安全垫传导、Brinson 归因前后端联动、快讯信源验真；
- 调度 Reviewers, Challengers, Auditor 核查；
- 门禁通过后标记 M2 DONE。

### Phase 3: 里程碑 3 (M3) — 全量回归、服务重启、走查与 Git 归档
- 调度 Worker 补充全量针对性测试套件，执行全量 pytest 回归；
- 终止 8501 端口旧进程，启动新服务，验证 HTTP 200；
- 多模态视觉与交互走查确认；
- 更新 GEMINI.md 与 PROGRESS_LOG.md；
- Git Commit, Tag v3.9-G9, Git Push (严禁 Release)；
- 生成 G10 指令并交接给 Sentinel/Parent。
