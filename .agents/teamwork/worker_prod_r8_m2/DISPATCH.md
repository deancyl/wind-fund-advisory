## 2026-11-05T02:43:14Z
You are Worker Prod R8-M2.
Your working directory is d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r8_m2\.
Read the original user request at: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md.
Read the project plan at: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md.
Read Explorer Survey R8-2 analysis at: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r8_2\analysis.md.
Also review the project rules at: d:\Google\Workspace\Wind\GEMINI.md.

YOUR TARGET: Milestone 2 - 估值动量单源同真与双翼看板升级 (Features 7-10)

FILE WRITE OWNERSHIP:
You have exclusive write ownership of:
- `AGY2_FundAdvisory/advisory_engine.py`
- `AGY2_FundAdvisory/app_gui.py`
You MUST NOT modify any other files without permission.

PHYSICAL SAFETY REDLINE:
NEVER touch or modify the 4 readonly referee files:
`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

SPECIFIC TASKS:
1. Feature 7 (数据同源单源同真):
   - In `AGY2_FundAdvisory/advisory_engine.py`:
     - Completely eliminate the static hardcoded constants in `RADAR_SECTOR_CATALOG` (`base_val_pct`, `er_20`, `bias_20`, `slope_20`). Retain only sector metadata (`sector_id`, `name`, `benchmark_index`, `symbol`, `top_fund_code`, `top_fund_name`, `core_logic`).
     - Fix parquet matrix discovery path: use `data/processed/aligned_matrix_total_return.parquet` (with fallback to `data/aligned_matrix_total_return.parquet` or `data/processed/indices/*.parquet`).
     - In `OpportunityRadarEngine.scan_all_sectors()`:
       - Query `IndexValuationEngine.fetch_or_calc_index_valuations()` for the benchmark index valuation percentile.
       - Dynamically compute 20D Kaufman ER, MA20 Bias, momentum slope, and crowding score from the parity matrix / index parquet.
       - Ensure valuation percentile is 100% identical between the sidebar corridor and the opportunity radar (diff < 1e-4).
2. Feature 8 (升级左翼全市场机会雷达):
   - In `AGY2_FundAdvisory/app_gui.py`:
     - Above Top 3 opportunity cards, render a concise morning market pulse brief (今日市场脉搏晨报, <=80 words) linking turnover change, ERP percentile, leading sector, and undervaluation zone.
     - Below Top 3 cards, provide an expandable container (`st.expander("📊 查看全市场 14 大赛道量化温度计总表", expanded=False)`) displaying the full 14-sector table (columns: 赛道名称、估值分位、趋势信噪比、20日乖离率、拥挤度评分、综合得分、状态标签、优选基金).
3. Feature 9 (补齐右翼六维主动风险预警哨):
   - In `AGY2_FundAdvisory/advisory_engine.py` (`ActiveRiskSentry.inspect_portfolio`):
     - Fully implement all 6 alert dimensions:
       1. 维度1 (未满7天惩罚锁仓红牌): Holding < 7 days (e.g. 011612), strictly prohibit redemption to prevent 1.50% penalty fee;
       2. 维度2 (临免赎期倒计时黄牌保护): A/C class holding 4-6 days (1-3 days to 7 days), or C class holding 23-29 days (1-7 days to 30 days zero fee, e.g. 011613), alert to hold a few more days;
       3. 维度3 (C类满30天零费率置换提醒): Holding >= 30 days C class, alert that fee is 0.00%, recommend switching to A class;
       4. 维度4 (个基阶梯止盈与深套诊断): Offensive fund profit >= 15% and Bias20 > 5% (or val_pct > 75%), recommend laddered profit taking (30-50% into bond/dividend); floating loss <= -12% (e.g. 013841), provide dilution or rebalancing diagnosis based on sector valuation percentile;
       5. 维度5 (赛道集中度与重仓股重叠预警): Single sector position > 35% or heavy holding overlap, issue concentration alert;
       6. 维度6 (基金本体清盘线与大盘攻防线): AUM < 0.5 亿 liquidation line & CSI 300 MA20/MA60 defense/offense line breakout/breakdown signals.
     - Backwards compatibility: retain keyword strings required by existing tests (`assert "主动风险预警哨"`, `assert "≤3天"`, `assert "已满 7 天"`, `assert "C类份额已满 30 天"`, `assert "超买"`, `assert "清盘警戒线"`).
4. Feature 10 (预警卡片可交互动作按钮):
   - In `AGY2_FundAdvisory/app_gui.py`:
     - Under each risk alert card, render interactive action buttons (e.g., jump to Tab 2 to lock holding <7d or generate laddered profit-taking sell order).
5. Verification:
   Run verification commands:
   - `py -3 scripts/verify_referee_hashes.py`
   - `py -3 -m pytest AGY2_FundAdvisory/tests/test_m3_advisory_modules.py`
   - `py -3 -m pytest AGY2_FundAdvisory/tests/test_m3_full_integration_apptest.py`
   - `py -3 -m pytest AGY2_FundAdvisory/tests/test_sidebar_remodel_and_bugfixes.py`
