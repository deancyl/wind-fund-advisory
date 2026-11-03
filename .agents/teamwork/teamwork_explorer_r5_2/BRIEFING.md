# BRIEFING — 2026-11-03T01:36:00Z

## Mission
Investigate R3 (Random Matrix Theory & Ledoit-Wolf Shrinkage) and R4 (Jump-Diffusion & Circular Block Bootstrap) in data_loader.py, portfolio_optimizer.py, winrate_engine.py, and relevant tests.

## 🔒 My Identity
- Archetype: explorer
- Roles: Technical investigator and synthesizer for R3 & R4
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\teamwork_explorer_r5_2
- Original parent: eb6d3982-62c0-45bd-b619-b09722abdf49
- Milestone: R3/R4 Technical Investigation & Design

## 🔒 Key Constraints
- Read-only investigation — do NOT implement / modify project code
- Output handoff.md following 5-component Handoff Protocol
- Comply with Wind and User Rules (e.g. Chinese responses, no code changes in source)

## Current Parent
- Conversation ID: eb6d3982-62c0-45bd-b619-b09722abdf49
- Updated: not yet

## Investigation State
- **Explored paths**:
  - `AGY2_FundAdvisory/data_loader.py` (line 436 `compute_ewma_volatility_and_correlation`)
  - `AGY2_FundAdvisory/portfolio_optimizer.py` (line 667 `_compute_hrp_weights`, lines 685-700)
  - `AGY2_FundAdvisory/winrate_engine.py` (line 439 `monte_carlo_simulation`, line 346 `cvar_95`)
  - `AGY2_FundAdvisory/tests/` (`test_phase3_market_optimizer.py`, `test_m2_r4_r5_optimization.py`, `test_adversarial_m2_challenger2.py`)
- **Key findings**:
  - R3: Current `compute_ewma_volatility_and_correlation` and `_compute_hrp_weights` use raw sample correlation with no denoising. Prototype of Marchenko-Pastur + Ledoit-Wolf shrinkage ($\alpha=0.15$) reduced condition number by 84% on normal data and from $3.3 \times 10^8$ to 2.51 on near-singular data, with trace conservation and strict positive definiteness ($\lambda_{\min} \ge 0.15$).
  - R4: Current `monte_carlo_simulation` uses moving block bootstrap ($b=20$) with end-point bias, no Student-t perturbation, and lacks `cvar_95` in output. Upgrading to 70% Circular Block Bootstrap ($b=10$) + 30% Student-t ($\nu=5$) successfully preserves volatility clustering, accurately models fat tails, computes 95% CVaR, and maintains backward compatibility.
- **Unexplored areas**: None for R3/R4. Investigation complete.

## Key Decisions Made
- Confirmed mathematical specifications for RMT Marchenko-Pastur cutoff $\lambda_+ = (1 + \sqrt{N/T})^2$, constant residual eigenvalue replacement, trace preservation, and Ledoit-Wolf diagonal shrinkage.
- Confirmed Circular Block Bootstrap with modulo wrapping `(st + d) % n_returns` and Student-t ($\nu=5$) heavy-tail path mixture for Monte Carlo stress testing.
- Prepared complete 5-component handoff report in `handoff.md`.

## Artifact Index
- `d:\Google\Workspace\Wind\.agents\teamwork\teamwork_explorer_r5_2\DISPATCH.md` — incoming dispatch records
- `d:\Google\Workspace\Wind\.agents\teamwork\teamwork_explorer_r5_2\BRIEFING.md` — persistent state memory
- `d:\Google\Workspace\Wind\.agents\teamwork\teamwork_explorer_r5_2\progress.md` — heartbeat and task progress
- `d:\Google\Workspace\Wind\.agents\teamwork\teamwork_explorer_r5_2\handoff.md` — 5-component handoff analysis report
