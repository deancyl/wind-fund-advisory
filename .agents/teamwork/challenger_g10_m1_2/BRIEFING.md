# BRIEFING — 2026-11-08T04:15:30Z

## Mission
Empirically stress-test and verify mathematical and financial correctness of multi-period Monte Carlo stress testing in PortfolioManager.simulate_portfolio_cvar_bootstrap across C1-C5 profiles, risk axioms, crisis scenarios, liquidity liquidation days, and risk tolerance triggers.

## 🔒 My Identity
- Archetype: EMPIRICAL CHALLENGER
- Roles: critic, specialist
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\challenger_g10_m1_2\
- Original parent: 22f2ddb7-c220-44ca-b889-a5c0901cc3b3
- Milestone: G10 M1 Stress Testing Verification
- Instance: 2 of 2 (Challenger)

## 🔒 Key Constraints
- Review-only — do NOT modify implementation code.
- Must execute empirical tests independently with `py -3 <script>`.
- Do NOT trust claims or logs without reproducing them.
- No files in `.agents/teamwork/` other than metadata.
- Handoff report in `handoff.md` with explicit APPROVE or REJECT verdict.

## Current Parent
- Conversation ID: 22f2ddb7-c220-44ca-b889-a5c0901cc3b3
- Updated: not yet

## Review Scope
- **Files to review**:
  - `AGY2_FundAdvisory/portfolio_manager.py` (specifically `simulate_portfolio_cvar_bootstrap` and `simulate_portfolio_cvar_bootstrap_instance`)
  - `tests/test_g10_correlation_liquidity_and_stress.py`
  - `worker_g10_m1/handoff.md`
- **Interface contracts**:
  - `d:\Google\Workspace\Wind\GEMINI.md` (Rule 7 FIFO locks, Rule 18 Bootstrap CVaR 99%)
  - `d:\Google\Workspace\Wind\AGENT_SPEC.md`
  - `d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_11\SCOPE.md`
- **Review criteria**:
  - Risk axioms: $CVaR_{99} \ge VaR_{99} \ge VaR_{95}$ across all scenarios and portfolios.
  - Realistic and differentiated drawdown for 2008, 2015, and 2024 crises.
  - Liquidity liquidation days deterministic and accounting for FIFO locks and top 5 ADV.
  - C1 conservative vs C5 aggressive `exceeds_risk_tolerance` gating.

## Attack Surface
- **Hypotheses tested**:
  - Risk axioms $CVaR_{99} \ge VaR_{99} \ge VaR_{95}$ across all portfolios: VERIFIED (90/90 pass).
  - Scenario differentiation (2008 deepest MDD, 2015 highest LiqDays, 2024 divergence): VERIFIED.
  - Top 5 ADV scaling with large position size: VERIFIED (10k -> 5.0d, 50B -> 28.0d).
  - C1 conservative triggers breach on equity, C5 aggressive compliant: VERIFIED.
  - FIFO 7-day lock penalty: FAILED (diff = 0.0 days for dict and FundHolding batches).
  - Calling `simulate_portfolio_cvar_bootstrap(holdings=None, pm_instance=pm)`: FAILED (`AttributeError`).
- **Vulnerabilities found**:
  - `portfolio_manager.py:8677` & `8687`: `getattr(v, "holding_days", 30)` returns default 30 on dicts and FundHolding objects, short-circuiting and ignoring `holding_days < 7` and batch holding days.
  - `portfolio_manager.py:8697`: `'holding_days': h.holding_days` crashes with `AttributeError` because `FundHolding` does not define `holding_days`.
- **Untested angles**:
  - Non-A-share QDII settlement days.

## Loaded Skills
- None requested.

## Key Decisions Made
- [2026-11-08T04:07:00Z] Initialized briefing and plan.
- [2026-11-08T04:14:00Z] Discovered and empirically confirmed FIFO lock failure and pm_instance crash in `simulate_portfolio_cvar_bootstrap`. Issued REJECT verdict.

## Artifact Index
- `DISPATCH.md` — Inbound instructions.
- `BRIEFING.md` — Current identity and persistent memory.
- `progress.md` — Heartbeat tracking.
- `scripts/verify_cvar_stress_testing.py` — Reproducible verification test harness.
- `handoff.md` — Final verification report.
