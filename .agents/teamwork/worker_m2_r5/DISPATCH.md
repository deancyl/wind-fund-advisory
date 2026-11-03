## 2026-11-03T02:09:18Z
You are teamwork_worker (Agent-2, Worker M2).
Working directory: d:\Google\Workspace\Wind\.agents\teamwork\worker_m2_r5\
Original request path: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md (MANDATORY: read this first).
Explorer 2 handoff report: d:\Google\Workspace\Wind\.agents\teamwork\teamwork_explorer_r5_2\handoff.md (MANDATORY: read this carefully for exact mathematical formulas and integration code).

Task: Implement R3 and R4 in AGY2_FundAdvisory/data_loader.py, AGY2_FundAdvisory/portfolio_optimizer.py, and AGY2_FundAdvisory/winrate_engine.py.
Exclusive Write Boundary: You own data_loader.py, portfolio_optimizer.py, and winrate_engine.py. Do NOT modify any other files (especially the 4 read-only referee files: judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py).

Specific Requirements:
1. R3 (Random Matrix Theory & Ledoit-Wolf Shrinkage):
   - In `data_loader.py`:
     * Implement `denoise_covariance_matrix(corr_matrix, n_obs=60, shrink_alpha=0.15) -> Any`:
       - Preserve DataFrame index/columns or ndarray format.
       - Adaptively handle covariance vs correlation matrix (standardize, denoise correlation, restore covariance scale).
       - Eigenvalue decomposition via np.linalg.eigh.
       - Marchenko-Pastur theoretical upper bound lambda_+ = (1 + sqrt(N / T))**2 where T = max(n_obs, N + 1).
       - Replace eigenvalues <= lambda_+ with the mean of noise eigenvalues (preserving matrix trace).
       - Reconstruct, enforce symmetry, normalize diagonal to 1.0.
       - Apply Ledoit-Wolf diagonal shrinkage: (1 - shrink_alpha) * C + shrink_alpha * I (with shrink_alpha=0.15).
       - Edge cases: N=1, identity matrix (returns identity), ill-conditioned/near-singular matrices.
     * In `DataLoader.compute_ewma_volatility_and_correlation`:
       - Apply `denoise_covariance_matrix` to the calculated correlation matrix before returning.
   - In `portfolio_optimizer.py`:
     * In `WinRateOptimizer._compute_hrp_weights`:
       - Apply `denoise_covariance_matrix` to both `corr` and `cov` matrices to stabilize HRP hierarchical clustering.
2. R4 (Jump-Diffusion & Circular Block Bootstrap Stress Test):
   - In `winrate_engine.py`:
     * Upgrade `WinRateEngine.monte_carlo_winrate`:
       - Signature: `(nav_series: pd.Series, holding_days: int, target_annual_return: float, n_paths: int = 10000, block_size: int = 10, include_friction: bool = True, fund_type: str = "A", seed: int = 42) -> Dict[str, Any]`
       - 70% of paths: Circular Block Bootstrap with block_size=10, modular index `(st + d) % n_returns` preserving A-share volatility clustering.
       - 30% of paths: Student-t distribution with df nu=5 (normalized to unit variance via sqrt(5/3), scaled to historical mu and sigma) for heavy-tailed jump-diffusion stress.
       - Stack paths, compute returns, apply friction fees.
       - Calculate 95% CVaR (mean of worst 5% annualized returns) and return `cvar_95` and `cvar_95_annualized` in the result dictionary.
       - Backward compatibility: maintain alias `monte_carlo_simulation = monte_carlo_winrate`.
3. Verification:
   - Run tests:
     `cmd.exe /c "set PYTHONPATH=AGY2_FundAdvisory;.&& py -3.11 -m pytest AGY2_FundAdvisory/tests/test_phase3_market_optimizer.py AGY2_FundAdvisory/tests/test_m2_r4_r5_optimization.py AGY2_FundAdvisory/tests/test_adversarial_m2_challenger2.py"`
   - Verify condition number drop, strict positive-definiteness, trace conservation, and CVaR 95% calculation.

## 2026-11-03T02:18:41Z
**Context**: Milestone 2 (R3 RMT去噪 & R4 Bootstrap压力测试)
**Content**: 定时心跳检查：请汇报当前 R3 与 R4 算子实现及单测验证进度。
**Action**: 请同步当前状态与预计完成时间。
