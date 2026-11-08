## 2026-11-08T09:09:55Z
You are Explorer 2 (explorer_g10_survey_14_2) in the G10 visual subtraction and UI elevation mission.

## Identity & Workspace
- Type: teamwork_explorer
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g10_survey_14_2\
- Authoritative user request file: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- You are read-only: do NOT edit source code or test files. Only write to your working directory.

## Objective
Survey `AGY2_FundAdvisory/advisory_engine.py`, `AGY2_FundAdvisory/data_loader.py`, and `AGY2_FundAdvisory/portfolio_manager.py`:
1. In `advisory_engine.py`:
   - Locate `_synthesize_quantitative_evidence` and examine how evidence text and rationale strings are generated.
   - Investigate the contradiction: when Kaufman Efficiency Ratio `er_20 < 0.35` (high-frequency oscillation), why does it output "右侧共振稳步上行"?
   - Design the logic: when `er_20 < 0.35`, forbid "右侧共振稳步上行"; when slope is positive but ER is low, phrase accurately as "底部震荡筑底、均线初现企稳".
   - Ensure the concise rationale is strictly <= 18 Chinese characters, removing verbose gray paragraph boxes.
2. In `data_loader.py`:
   - Locate `DataLoader.fetch_realtime_market_news_and_catalysts`.
   - Inspect the current scraping / fallback logic for 7x24 news.
   - Formulate the financial whitelist filter: only retain headlines containing A-share financial keywords:
     `A股, 沪深, 指数, 央行, 利率, 降准, 降息, LPR, 社融, PMI, 证监会, 公募, 基金, ETF, 红利, 科创, 半导体, 芯片, 医药, 消费, 银行, 黄金, 美股, 纳指, 国债, 分红, 净值, 主力, 北向, 研报, 估值, 流动性`.
   - Formulate the strict blacklist: filter out headlines containing:
     `无人机, 拦截, 联军, 导弹, 武装, 袭击, 交火, 赛事, 娱乐`.
   - When no headlines pass the filter, output a concise market overview based on actual day's turnover and index performance.
3. In `portfolio_manager.py`:
   - Locate `simulate_portfolio_cvar_bootstrap_instance` and right-wing CVaR calculation.
   - Investigate why right-wing calculated -36.1% while Tab 3 was -12.0%.
   - Analyze the daily volatility scaling factor and compounding formula in `simulate_portfolio_cvar_bootstrap_instance` vs Tab 3's Monte Carlo methodology.
   - Specify the exact calibration so that portfolio_manager's calculation is strictly aligned with Tab 3.

## Outputs
Write your detailed analysis to `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g10_survey_14_2\analysis.md` and a structured `handoff.md`.
Then send a completion message back with your findings summary.


## 2026-11-08T09:20:48Z
**Context**: Survey status check
**Content**: Checking in on your survey progress. Please report current status and write your analysis to analysis.md / handoff.md as soon as ready.
**Action**: Update progress.md and report status.
