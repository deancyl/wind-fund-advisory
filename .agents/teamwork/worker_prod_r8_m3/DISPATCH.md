## 2026-11-05T03:12:55Z
[Message] timestamp=2026-11-05T03:12:55Z sender=3ef18151-e1aa-4330-83a1-353aa7bcc35e priority=MESSAGE_PRIORITY_HIGH content=You are Worker Prod R8-M3.
Your working directory is d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r8_m3\.
Read the original user request at: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md.
Read the project plan at: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md.
Read Explorer Survey R8-3 analysis at: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r8_3\analysis.md.
Also review the project rules at: d:\Google\Workspace\Wind\GEMINI.md.

YOUR TARGET: Milestone 3 - 7 大机构级量化定权模型与历史黑天鹅压力测试器 (Features 11-13)

FILE WRITE OWNERSHIP:
You have exclusive write ownership of:
- `AGY2_FundAdvisory/winrate_engine.py`
- `AGY2_FundAdvisory/portfolio_optimizer.py`
- `AGY2_FundAdvisory/app_gui.py`
You MUST NOT modify any other files without permission.

PHYSICAL SAFETY REDLINE:
NEVER touch or modify the 4 readonly referee files:
`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

SPECIFIC IMPLEMENTATION TASKS:
1. Feature 11 (实装 7 大机构量化定权求解算子):
   - In `QUANT_MODELS_CATALOG` and `WinRateOptimizer` in `winrate_engine.py` / `portfolio_optimizer.py`:
     - Implement the 7 institutional weighting mathematical solvers:
       1. Model 1: 鲁棒双核HRP (`hrp_robust`: Hierarchical Risk Parity + CVaR)
       2. Model 2: 核心-卫星杠铃模型 (`core_satellite`: 70%~80% 纯债红利核心底仓 + 20%~30% 高弹性成长/雷达精选卫星仓)
       3. Model 3: 全天候风险平价模型 (`all_weather`: 跨 A 股宽基、红利、纯债、黄金、海外 QDII 等风险贡献度配置)
       4. Model 4: BL 主客观观点融合模型 (`black_litterman`: 以市场均衡配置为先验，贝叶斯融合机会雷达 Top 赛道与自选观点)
       5. Model 5: 条件胜率最优模型 (`conditional_winrate`: 同温层状态机核密度加权)
       6. Model 6: 尾部风控CVaR模型 (`cvar_tail`: 最小化 95% 极端尾部亏损)
       7. Model 7: 凯利动量增强模型 (`kelly_momentum`: 考夫曼信噪比自适应半凯利公式)
     - MATHEMATICAL INVARIANT: Every model's output weights MUST strictly sum to 1.0 (`abs(sum(weights.values()) - 1.0) < 1e-6`), and weights must be non-negative (`w_i >= 0.0`).
2. Feature 12 (步骤一模型对比与宏观路由更新):
   - In `app_gui.py` Tab 1 Step 1, update the model comparison card to describe all 7 models (mathematical principle, source institution, and target regime).
   - Update the macro recommendation routing logic to recommend the best model based on ERP, valuation temperature, and volatility.
3. Feature 13 (历史黑天鹅压力测试器):
   - In `winrate_engine.py` / `portfolio_optimizer.py`, implement `simulate_black_swan_stress(holdings, total_capital)`:
     - Historical slice 1: 2018 Trade Friction Bear Market (2018-01-29 ~ 2019-01-04)
     - Historical slice 2: 2022 Valuation Kill Bear Market (2021-12-13 ~ 2022-10-31)
     - Historical slice 3: 2024 Early Micro-Cap Liquidity Crisis (2024-01-02 ~ 2024-02-05)
     - Accurately calculate the maximum floating loss amount, max drawdown, and estimated recovery trading days for the current portfolio under each slice using aligned parquet returns or realistic stress drawdowns.
   - In `app_gui.py`, render the Historical Black Swan Stress Test card in Tab 1 Step 2 and Tab 3 推演结果.
4. Verification:
   Run verification commands:
   - `py -3 scripts/verify_referee_hashes.py`
   - Test that all 7 model weights sum to 1.0 within floating error.
   - Run AppTest to ensure Tab 1 and Tab 3 render without any exceptions.

When finished, write a detailed handoff report to `d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r8_m3\handoff.md` and send a message to the orchestrator.
