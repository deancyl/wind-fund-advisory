# BRIEFING — 2026-11-08T03:27:30Z

## Mission
深入调研 advisory_engine.py 与 portfolio_manager.py 中关于需求 R2（相关性压力突变预警与跨资产流动性平移预案）的现状与实现路径，输出精准调查报告。

## 🔒 My Identity
- Archetype: teamwork_explorer
- Roles: Codebase Survey Explorer
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_g10_1
- Original parent: 22f2ddb7-c220-44ca-b889-a5c0901cc3b3
- Milestone: Survey & Investigation for Requirement R2

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- 严禁修改任何业务源码
- 遵守工作区 GEMINI.md 铁律，尤其是 Rule 17（相关性突变防御与平移）、Rule 21（EWMA 相关性对齐）
- 报告必须包含具体文件名、行号、数据结构与落地建议

## Current Parent
- Conversation ID: 22f2ddb7-c220-44ca-b889-a5c0901cc3b3
- Updated: 2026-11-08T03:27:30Z

## Investigation State
- **Explored paths**:
  - `AGY2_FundAdvisory/advisory_engine.py`: lines 26-230, 272-300, 768-800, 1378-2035, 2201-2345, 2700-2920
  - `AGY2_FundAdvisory/portfolio_manager.py`: lines 5176-5300, 6335-6450, 7120-7165, 8329-8560
  - `AGY2_FundAdvisory/data_loader.py`: lines 930-1065
  - `tests/test_g3_evolution_loop.py`: lines 30-120
  - `tests/test_g9_causal_brinson_and_suitability.py`: lines 1-60, 200-260
  - `tests/test_adv_final_closure.py`: lines 1-60
  - `tests/test_infra.py`: lines 1-50
- **Key findings**:
  1. 相关性测算当前仅存在于 `portfolio_manager.py`（`compute_ewma_correlation` 和 `evaluate_dynamic_correlation_mutation`），`advisory_engine.py` 内部暂无独立的 `calculate_dynamic_correlation_matrix`，仅在 `ActiveRiskSentry.inspect_portfolio` (line 1841) 被动调用。
  2. 现存相关性测算为无条件的红利与沪深300相关性，缺少“大盘急跌场景”（如沪深300破防守线、单日/累计急跌）以及“红利低波与高Beta权益板块（科创50、中证1000、半导体）”的下行半协方差/下行相关性测算。
  3. 现存削减逻辑仅削减 `is_div` 和 `is_cyc`，未将“科技成长进攻”等高估值高波标的纳入减仓范围（属于重大逻辑漏斗）。
  4. 现有测试套件强断言 `res_mutation["status"] == "MUTATION_ALERT"` 与 `alert["action_type"] == "correlation_mutation_defense"` 以及文案必须包含“集中度降级”，扩展 0.80 阈值及流动性平移预案时必须保持向后兼容。
- **Unexplored areas**: None for R2.

## Key Decisions Made
- 详细整理 5 大调研维度的现存代码切片、差距分析、测试断言红线与落地实施方案，输出结构化 `handoff.md`。

## Artifact Index
- DISPATCH.md — 任务指派记录
- BRIEFING.md — 工作记忆
- progress.md — 心跳与进度记录
- handoff.md — R2 深入调研报告
