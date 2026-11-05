## 2026-11-05T16:15:54Z
Sender: f7b8d799-910f-4e70-94f5-3538a52207de
Priority: MESSAGE_PRIORITY_HIGH

You are Explorer 1 (Financial & Regulatory Facts Explorer).
Working directory: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r10_1
Original user request path: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md

[HARD CONSTRAINTS]
- Read-only technical investigation. DO NOT write or modify source code files.
- DO NOT run build/test execution yourself.
- Write your investigation findings to handoff.md and analysis.md in your working directory.
- When done, call send_message to report back to caller with a clear summary and the absolute path to your handoff.md.

[SURVEY OBJECTIVES]
Investigate Section 1 of ORIGINAL_REQUEST.md (修正 4 项金融事实错误与监管合规瑕疵):
1. Red dividend low-volatility index error in advisory_engine.py:
   - Inspect RADAR_SECTOR_CATALOG and IndexValuationEngine in advisory_engine.py.
   - Find where dividend_low_vol benchmark_index and index_code are defined as 000978 (which is CS CSI Medicine 100!).
   - Locate where H30269 (中证红利低波指数) is defined or mapped, and ensure IndexValuationEngine alias and data loading correctly maps H30269.
2. QDII fund cross-timezone delivery & clearing rules and valuation confidence labels:
   - Check trading_clock_fee.py, portfolio_manager.py, and app_gui.py.
   - How are QDII funds (e.g. 050025 S&P 500, 001071 HuaAn Nasdaq, 013402 Hang Seng Tech) identified?
   - Where are trade orders generated, on-the-way reconciliation center (在途对账), and Tab 2 T+2 on-the-way step-out risk & same-company fund conversion?
   - How to label US QDII: 「T+2 确认份额 · 赎回 T+6~T+8 到账（跨时区清算，不可用于 T+2 极速换仓）」 and exclude them from T+1 conversion and T+2 step-out risk calculation.
   - How to attach valuation confidence labels to Tab 1 & Tab 2:
     * Index feeder: 「指数高准度」
     * Pure bond: 「债基看久期票息」
     * US QDII (daytime): 「美股休市·看隔夜期指」
     * Active hybrid: 「季报重仓估算」
3. Eliminate non-compliant "保本" wording:
   - Grep for all occurrences of "保本" / "保本率" across app_gui.py and codebase (e.g. line 1372 rolling win rate card).
   - Propose precise replacements: 「正收益概率 (≥0%)」 or 「本金安全率」.
4. Harmonize 14 sector momentum & bias price index basis:
   - In advisory_engine.py _calc_dynamic_sector_metrics:
   - Check how 20-day bias (bias_20) is computed.
   - For dividend sectors, how to prioritize price index (000922.SH / H30269) or dividend-adjusted smoothed daily series to prevent fake positive bias pulses during dividend season.

Produce a detailed, structured handoff.md in your working directory.
