# Task Assignment: Explorer Survey r7_3 (Quant Modules, Invariants & Testing)

## Authoritative Request File
`d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md` (MUST read completely before proceeding)

## Objective
Thoroughly explore the codebase for Requirements R3, R4, R5:
1. 【🔭 全市场机会雷达】(Opportunity Radar):
   - Coverage: broad-base and core sectors (红利低波, 中证红利, 沪深300, 中证500, 中证1000, 科创50, 半导体芯片, 医药医疗, 消费白酒, 银行高股息, 国内黄金, 美股标普/纳指, 恒生科技, 纯债固收).
   - Valuation percentile score, Kaufman ER signal-to-noise ratio, MA20 momentum inflection, crowding safety score.
   - Auto-select Top 3 "Golden hitting zone / right-side resonance" opportunity sectors + highest 6D-scored OTC public fund.
   - UI placement (collapsible dashboard on main screen or embedded at top of Tab), one-click add to candidate pool.
2. 【🚨 主动风险预警哨】(Active Risk Watchdog):
   - 4D state inspection:
     * FIFO lot unlock alerts: <=3d caution against redemption, exactly 7d penalty-free escape, Class C exactly 30d zero redemption fee.
     * Sector crowding & overbought warnings.
     * Fund self risk screening (<0.5亿 liquidation risk, manager turnover, style drift).
     * Market attack/defense lines (MA20/MA60/MA120, Bias) breakthrough / breakdown warnings.
     * Green "All Passed" badge when clear.
3. 【🌊 分批建仓与智能定投算子】(Smart Execution & DCA):
   - Tab 1 Step 3 real-world execution order: add capital deployment rhythm selector:
     * Mode 1 (⚡ 一次性建仓): Full allocation today.
     * Mode 2 (🌊 稳健三步分批建仓): Batch 1 today base (50% capital: bonds, gold, dividends, half equity), Batch 2 grid dip-buy (30% capital: index pullback triggers and amounts), Batch 3 right-side momentum (20% capital: breakout trigger, parked in short debt/money market before trigger). Sum of 3 batches STRICTLY equals `total_capital`.
     * Mode 3 (📅 估值自适应智能定投): ERP percentile + Bias_20 dynamic multiplier (1.5x~2.0x deep undervaluation, 1.0x fair, 0.0x~0.5x overvalued profit-taking). Output periodic allocation schedule.
4. Physical Safety Redlines & Architectural Constraints:
   - Check `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py` (MUST NOT BE MODIFIED).
   - Check GEMINI.md invariants (Streamlit Tab independent try-except error boundaries, geometry non-truncation, FIFO holding days defense, transient port 8501 defense).
5. Testing Baseline & Strategy:
   - Investigate existing test suite in `AGY2_FundAdvisory/tests/` and root `tests/`.
   - Identify what new unit tests and Streamlit `AppTest` regression tests are needed.

## Working Directory
`d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r7_3/`

## Output Requirements
Write comprehensive analysis, file locations, mathematical formulas, and concrete implementation plan to:
`d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r7_3\report.md`
Then call `send_message` to parent.
