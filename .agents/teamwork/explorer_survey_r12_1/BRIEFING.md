# BRIEFING — 2026-11-06T17:07:00Z

## Mission
调研单基真实历史波动率与单基乖离率穿透机制，查明现存固定常数回退点、数据湖缓存结构及所有调用链，提出精确的量化计算实现方案。

## 🔒 My Identity
- Archetype: explorer
- Roles: teamwork_explorer
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r12_1\
- Original parent: 71f16351-ac4e-45f7-b8a4-89e38ec8863c
- Milestone: G5-M1-Survey-1

## 🔒 Key Constraints
- Read-only investigation — do NOT implement or modify source code
- Workspace-only /learn invariant: never touch global GEMINI.md
- No pseudo-constants, no pseudo-random numbers
- Four read-only files: judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py must never be edited
- DataLoader.simulate_execution signature and deduction logic must never be edited

## Current Parent
- Conversation ID: 71f16351-ac4e-45f7-b8a4-89e38ec8863c
- Updated: not yet

## Investigation State
- **Explored paths**: `advisory_engine.py` (L1250-1500), `app_gui.py` (L3380-3450, L5220-5340), `data_loader.py`, `portfolio_manager.py`, `data/processed/aligned_matrix_total_return.parquet`, `data/processed/indices/*.parquet`, `data/processed/funds/*.parquet`, `tests/test_g3_evolution_loop.py`.
- **Key findings**: 
  1. 定位了 `calculate_vwap_execution_slippage` 中三档固定常数（L1324 0.18；L1367-1372 0.04/0.14/0.18）；
  2. 查明 `plan_smart_dca` (L1484) 与 `app_gui.py` (L3415, L5235) 均未传递单基真实波动率与单基偏离度；
  3. 查明本地拥有完整四级列式湖仓（单基 parquet、754 个赛道指数 parquet、全收益对齐矩阵），可 100% 离线计算真实波动率与乖离率；
  4. 验证真实数据下纯债波动率 0.68%、黄金 13.86%、红利低波 14.89%、纳指 19.14%、科创50 31.75%，分化显著。
- **Unexplored areas**: 无，所有调查目标均已彻底查清并完成实证检验。

## Key Decisions Made
- 建议在 `advisory_engine.py` 中新增 `get_fund_real_volatility_and_bias` 辅助算子；
- 建议全面改造 `calculate_vwap_execution_slippage` 自适应兜底逻辑，彻底废除 0.04/0.14/0.18；
- 建议改造 `plan_smart_dca` 与 `app_gui.py` 中 2 处前端调用点，实现单基真实量化指标穿透。

## Artifact Index
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r12_1\report.md — 最终综合调研报告
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r12_1\handoff.md — 5段式交接文档
