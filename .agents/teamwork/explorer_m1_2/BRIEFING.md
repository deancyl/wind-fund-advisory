# BRIEFING — 2026-11-15T08:09:20Z

## Mission
Investigate Feature 5 for Milestone 1: 拔除 6.6676 与 5.0000 兜底常数并增加合理性校验哨 (USCNH汇率与美债收益率合理性校验及基线校准)，产出详尽且直接可落地的 Worker 实施方案与 handoff 报告。

## 🔒 My Identity
- Archetype: explorer
- Roles: Read-only investigation: analyze problems, synthesize findings, produce structured reports
- Working directory: d:\Google\Workspace\Wind
- State folder: d:\Google\Workspace\Wind\.agents\teamwork\explorer_m1_2
- Original parent: a29ecba0-a4ab-4a58-a8c7-4276082800c0
- Milestone: M1: 十维真实投票与汇率校验及胶囊联动

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- 严禁修改物理安全红线：DO NOT modify judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py
- 严禁修改 DataLoader.simulate_execution default signature & default fee logic
- 请使用中文回复所有消息
- .agents/teamwork/ holds only agent metadata

## Current Parent
- Conversation ID: a29ecba0-a4ab-4a58-a8c7-4276082800c0
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `AGY2_FundAdvisory/data_loader.py` (L2585-L2665, L3020-L3240)
  - `AGY2_FundAdvisory/advisory_engine.py` (L4195-L4205, L4550-L4575)
  - `AGY2_FundAdvisory/app_gui.py` (L300-L305)
  - `AGY2_FundAdvisory/strategy_bridge.py` (L2860-L2895)
  - `AGY2_FundAdvisory/portfolio_manager.py` (L7730-L7740)
  - `data/global/fx_rates.parquet` & `data/macro/bond_zh_us_rate.parquet`
  - `tests/test_g13_tail_arb_switch_fx.py` & `tests/test_g17_advisory_real_data_and_ten_dimension.py`
  - Sina live API probe `https://hq.sinajs.cn/list=fx_susdcnh`
- **Key findings**:
  1. 确认全工作区 15 处硬编码常数点位（11 处 6.6676，4 处 5.0000）。
  2. 现场探测发现新浪行情源当前返回 `6.6746`（模拟沙盒冻结点位），且本地外汇湖仓末行也为 `6.6676`，本地美债湖仓末行为 `5.00`。
  3. 若仅修改默认变量而不设置**合理性校验哨**（`6.85 <= rate <= 7.60`，`3.0 <= us_10y <= 6.5` 且非 `5.0000`），实时抓取和湖仓读取都会再次引入失真假常数。
  4. 当汇率超出 `[6.85, 7.60]` 时，必须强制校准为 `7.2385`；美债校准为 `4.42%`，中美利差精算为 `1.6376 - 4.42 = -2.7824%`，严格校准为 `-278.2 bp`。
  5. 物理裁判安全底线 100% 遵守，零修改。
- **Unexplored areas**: 无，所有调查目标均已彻底查清闭环。

## Key Decisions Made
- 制定 5 个核心文件的精确改造方案（前置拦截 + 后置校验哨双层防护）
- 建议 Worker 在修改 5 个 Python 文件的同时，可一并平滑更新本地湖仓末行，确保端到端彻底纯化

## Artifact Index
- DISPATCH.md — 任务派发记录
- BRIEFING.md — 当前上下文与状态
- progress.md — 心跳与进展
- handoff.md — 最终 5 部分分析报告
