## 2026-11-08T15:04:09Z

You are teamwork_explorer for Survey Phase of G12 Generation.
Your Identity: teamwork_explorer
Your Working Directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_g12_survey_2\
Authoritative Request: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md

Please read ORIGINAL_REQUEST.md first (under ## Follow-up — 2026-11-08T14:57:27Z and the latest sections).
Your investigation focuses on: Trailing Stop-Profit, Right-Side Breakdown Exit & Multi-Source Leading Indicators:
1. ActiveRiskSentry.inspect_portfolio Dimension 4: Right-side breakdown trailing stop-profit. Current logic only triggers when bias_20 > 5%, fails when breaking MA on a big down candle. Investigate:
   - Floating profit >= 10%, latest NAV or realtime quote breaks MA20 (bias_20 < 0) AND (slope < 0 OR single-day drop > 1.5 * daily_vol) -> red exit alert to lock in 50% profit.
   - High-water mark drawdown protection based on 60-day peak NAV.
   - Examine how inspect_portfolio dimension 4 is structured, how alerts are returned, how app_gui renders it.
2. data_loader.py: Local daily line auto-heal: detect parquet max date < latest closed trading day, fetch missing daily candles via real-time/historical K-line APIs and append to sequence.
   - Check where daily parquet files are read/cached, how latest closed trading day is determined, how to safely append without modifying read-only referee files.
3. Multi-source leading indicators:
   - Volume Surge Ratio & premium/discount for 14 sector core ETFs.
   - Macro cross-market indicators: 10Y bond yield, gold, Nasdaq overnight/intraday linkage.
   - Financial news sentiment score (0-100) and Morning Brief rendering in double-wing header.

Investigate the exact code in the workspace, locate line numbers, analyze dependencies, check any potential test breakages, and design complete, safe implementation steps.
Write your full findings and recommendations to:
`d:\Google\Workspace\Wind\.agents\teamwork\explorer_g12_survey_2\handoff.md`
Remember to update `progress.md` in your working directory.
When finished, send a message to the orchestrator summarizing your report path and key findings.
