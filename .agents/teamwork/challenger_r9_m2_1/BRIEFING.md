# BRIEFING — 2026-11-05T15:47:00Z

## Mission
Adversarial Stress Testing of Rebalancing Scenarios (M2): Verify `new_cash_only`, `withdraw_cash_only`, `freeze_reserved_cash`, and cache key mutation under extreme/adversarial conditions.

## 🔒 My Identity
- Archetype: challenger
- Roles: critic, specialist
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\challenger_r9_m2_1
- Original parent: 8849ddae-0421-48b2-aa8f-6d2c7b15dafe
- Milestone: M2 (Rebalancing Scenarios)
- Instance: 1 of 1

## 🔒 Key Constraints
- Review and empirical stress-testing only — do NOT modify production implementation code directly unless asked to write tests in tests/
- Tests must be executed empirically; no unverified claims
- Workspace rules and GEMINI.md compliance (Look-Through, 7-day penalty lock, FIFO, Streamlit isolation, Windows paths)
- Deliver verdict: APPROVE or REQUEST_CHANGES

## Current Parent
- Conversation ID: 8849ddae-0421-48b2-aa8f-6d2c7b15dafe
- Updated: not yet

## Review Scope
- **Files to review**:
  - `src/rebalance_optimizer.py` (or rebalancing engine files modified in M2)
  - `web/app.py` / `src/` UI & scenario selection logic
  - `tests/test_rebalancing_scenarios.py`
  - Worker M2 handoff: `d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r9_m2\handoff.md`
- **Interface contracts**: `PROJECT.md`, `ORIGINAL_REQUEST.md`
- **Review criteria**: Boundary correctness, mathematical precision, 7-day penalty lock adherence, cache key isolation, error handling, strict scenario invariant preservation.

## Key Decisions Made
- Initialized challenger workspace and tracking.

## Artifact Index
- `.agents/teamwork/challenger_r9_m2_1/DISPATCH.md` — Incoming task instructions
- `.agents/teamwork/challenger_r9_m2_1/BRIEFING.md` — Agent state and memory
- `.agents/teamwork/challenger_r9_m2_1/progress.md` — Liveness & heartbeat
- `.agents/teamwork/challenger_r9_m2_1/handoff.md` — Final assessment and verdict

## Attack Surface
- **Hypotheses tested**: [TBD]
- **Vulnerabilities found**: [TBD]
- **Untested angles**: [TBD]

## Loaded Skills
- None requested in task dispatch.
