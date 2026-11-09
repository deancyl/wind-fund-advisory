# BRIEFING — 2026-11-09T11:37:00Z

## Mission
Investigate 4 code bugs in advisory_engine.py and app_gui.py for G14 release and design exact code fix plans.

## 🔒 My Identity
- Archetype: explorer
- Roles: explorer
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g14_survey_1
- Original parent: 675b287a-9df2-4040-9227-01d56b1552b2
- Milestone: G14 4 code bugs investigation

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- 物理安全红线：严禁修改四个只读裁判文件 judge_engine.py、holdout_vault.py、AGENT_SPEC.md、tests/test_infra.py
- 严禁修改 DataLoader.simulate_execution 的默认函数签名与默认扣费逻辑
- 仅在自身专属目录写入报告与分析文件，严禁污染业务代码或向外部全局 GEMINI.md 溢出

## Current Parent
- Conversation ID: 675b287a-9df2-4040-9227-01d56b1552b2
- Updated: 2026-11-09T11:25:34Z

## Investigation State
- **Explored paths**:
  - `AGY2_FundAdvisory/advisory_engine.py` (lines 892-975, 984-1045, 1638-1655, 2037-3035)
  - `AGY2_FundAdvisory/app_gui.py` (lines 2760-2795, 2830-3076, 7425-7450)
  - `data/cache/radar_sectors_cache.json` & `data/cache/factor_evolution_cache.json`
  - `tests/test_causality_adversarial_m1.py`, `tests/test_challenger_g13_m1.py`, `tests/test_challenger_g13_m2_empirical.py`
- **Key findings**:
  1. Bug 1: `OpportunityRadarEngine.scan_all_sectors` lacks cache reading/writing; `app_gui.py` lines 2905 and 7435 have conflicting type assumptions (list vs dict) when reading cache.
  2. Bug 2: `render_dual_wing_advisory_dashboard` removed `ActiveRiskSentry.inspect_portfolio` and falsely reported "all passed" based only on 2 simplistic loops; `news_source_badge` was dead code. Need `holdings_hash` MD5 fingerprint (holdings + risk tier) to cache in session_state and watchdog.json, render all 12 dimensions, and add refresh button.
  3. Bug 3: `get_60d_rolling_nav_and_trajectory` at line 933 hardcodes `np.mean(r_day[:3])`, ignoring `w_opt`; line 934 hardcodes all-market average instead of static Top 3; neither deducted 20 bps turnover cost.
  4. Bug 4: Lines 2767-2792 in `app_gui.py` render `latest_plan` pseudo-trading banner between top 4 cards and dashboard. Safe to remove cleanly.
- **Unexplored areas**: None. All 4 bugs completely diagnosed and detailed fix designs formulated.

## Key Decisions Made
- Use dual-compatibility parsing (dict with `sectors` key vs raw list) for `radar_sectors_cache.json` to prevent crashes across all callers.
- Use `holdings_hash` over sorted holdings items + `active_tier_val` to cache 12-dimensional risk report for 1ms retrieval.
- Design `_calc_features_at_day` logic for out-of-sample days to compute genuine 4-dim feature vectors at $d-1$, select dynamic & static Top 3, and deduct `0.0020 * turnover`.

## Artifact Index
- DISPATCH.md — Task assignment
- progress.md — Liveness heartbeat
- BRIEFING.md — Situational awareness
- handoff.md — Final investigation report
