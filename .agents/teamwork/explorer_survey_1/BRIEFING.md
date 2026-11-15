# BRIEFING — 2026-11-15T07:54:30Z

## Mission
【Survey Mission: Voting & Macro Explorer】
只读深入走查 G19 世代 Phase 1 需求：
1. `compute_ten_dimension_votes` in `advisory_engine.py` (维度6、7、10真数据驱动与输入审计熔断门禁)；
2. 拔除 6.6676 (USD/CNH) 与 5.0000 (US 10Y) 兜底常数与跨市场合理性校验；
3. 首屏第四颗胶囊（存量持仓病灶）与第五颗胶囊（今日行动准则）强联动与实战清扫指令；
4. 结合 agy2 (3).md Task 3 输入审计项（维度6动态产业理由，熔断门禁 ivix>=32.0 或 dyn_corr>=0.80 或 usdcnh_chg>0.60%）。
产出包含确切代码行号、真实数据流溯源与具体 Worker 修改方案的 handoff.md 交付报告。

## 🔒 My Identity
- Archetype: explorer
- Roles: investigation, synthesis
- Working directory: d:\Google\Workspace\Wind
- State folder: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_1
- Original parent: 2b4a5c42-da01-49e9-b9b9-7a42b49250ea
- Milestone: G19 Phase 1 Technical Survey & Mapping Completed

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- 严禁修改任何业务代码（只在自己的 state folder 中写入报告与状态文件）
- 严禁修改四个只读裁判文件 judge_engine.py、holdout_vault.py、AGENT_SPEC.md、tests/test_infra.py
- 严禁修改 DataLoader.simulate_execution 的默认函数签名与默认扣费逻辑
- 严禁修改全局 GEMINI.md
- 输出遵守中文规则与 5-Component Handoff Protocol

## Current Parent
- Conversation ID: 2b4a5c42-da01-49e9-b9b9-7a42b49250ea
- Updated: 2026-11-15T07:54:30Z

## Investigation State
- **Explored paths**:
  - `AGY2_FundAdvisory\advisory_engine.py`: 行 4170–4458 (`compute_ten_dimension_votes`), 行 4460–4850 (`generate_chief_advisor_memo`), 行 46–100 (`RADAR_SECTOR_CATALOG`), 行 1690–1740 (`scan_all_sectors`), 行 2730–2760 (`evaluate_dynamic_correlation_mutation`)
  - `AGY2_FundAdvisory\app_gui.py`: 行 268–459 (`render_chief_advisor_memo_card`), 行 2715 (`pm` 初始化), 行 3252–3269 (旧初始路由), 行 3300–3388 (顶部指标卡与两市成交/多方占比展示), 行 3620–3665 (雷达扫描与首屏裁决台调用)
  - `AGY2_FundAdvisory\data_loader.py`: 行 62–195 (`fetch_market_turnover_and_sentiment`), 行 2590–2665 (`fetch_realtime_usdcnh_fx`), 行 3020–3200 (`fetch_macro_cross_market_indicators`)
  - `AGY2_FundAdvisory\strategy_bridge.py`: 行 2565–2715 (`_refresh_derivatives_data`), 行 2724–3275 (`get_latest_market_snapshot`), 行 2864, 2888 (5.0000 / 6.6676 兜底)
  - `AGY2_FundAdvisory\multi_ledger_manager.py`: 行 198–275 (`_init_preset_combat_29_ledger`)
  - `tests\test_g17_advisory_real_data_and_ten_dimension.py`: 行 28–46 (违禁常量静态扫描), 行 79–121 (`compute_ten_dimension_votes` 测试)
  - `tests\test_adversarial_m3_combat29_challenger.py`: 行 87–113 (持仓天数与免赎核验)
  - `tests\test_g16_phase1_memo_and_combat29.py`: 行 207–220 (`test_memo_card_with_tab1_construction_mode` 断言缺陷剖析)
  - `data\cache\radar_sectors_cache.json`: 实测包含 14 赛道完整估值分位与拥挤度数据
- **Key findings**:
  1. 维度 6 恒真 Bug 确凿：`n_radar = len(radar_top3) if radar_top3 else 3`，`n_radar >= 2` 恒真，始终投多头。
  2. 维度 7 数据脱靶 Bug 确凿：读取单基 `snap.get("crowding_score", 85.0)`，脱离 14 赛道真实平均拥挤度，且未接入成交额与多方占比。
  3. 维度 10 衍生品失真 Bug 确凿：完全未读取 `option_iv_pct` 与 `ic_annualized_basis_rate`，仅判断相关性预警。
  4. 汇率 6.6676 与美债 5.0000 残留点全量排查完毕，合理性哨机制（低于 6.85 或高于 7.60 拦截并校准）已设计。
  5. 胶囊 4 与胶囊 5 左右互搏根因：`generate_chief_advisor_memo` 胶囊 5 仅看大盘乖离与 ERP，完全无视深套与尾仓。
  6. Task 3 熔断门禁（ivix>=32.0 或 dyn_corr>=0.80 或 usdcnh_chg>0.60%）接入位置确立。
- **Unexplored areas**: None (调研 100% 闭环)

## Key Decisions Made
- 汇率校准截面建议使用 `7.2385`（避开 `test_g17` 禁用的 `7.2450`）。
- 美债十年期校准截面建议使用 `4.42`（合规处于 `[3.5, 6.5]` 区间）。
- 梳理出精确修改代码行号、数据结构兼容链与测试方案，输出最终 handoff.md。

## Artifact Index
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_1\DISPATCH.md — 任务派发记录
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_1\BRIEFING.md — 运行记忆与状态
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_1\progress.md — 进度与存活心跳
- d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_1\handoff.md — 最终调查报告
