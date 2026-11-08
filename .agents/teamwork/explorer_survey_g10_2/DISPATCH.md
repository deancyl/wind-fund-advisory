## 2026-11-08T03:19:15Z
You are a Codebase Survey Explorer (teamwork_explorer).
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_g10_2\
Mandatory inputs:
- Read d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- Read d:\Google\Workspace\Wind\GEMINI.md
- Read d:\Google\Workspace\Wind\AGENT_SPEC.md

Your mission:
Investigate data_loader.py and advisory_engine.py regarding Requirement R3 & R1:
- R1 Anti-cheating & safety bottom line:
  - 严禁修改四个只读裁判文件：judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py
  - 严禁修改 DataLoader.simulate_execution 的默认函数签名与默认扣费逻辑
  - 严禁使用伪随机数、线性插值伪序列或静态保底常数伪造金融指标
- R3 场外公募基金微观执行冲击与底层流动性折价惩罚:
  - 在 data_loader.py 与 advisory_engine.py 中升级微观执行冲击模型。
  - 针对场外公募基金，结合基金管理人季报披露的前五大重仓股日均成交额与基金规模比例，真实精算大额赎回对底层资产的流动性折价惩罚，杜绝使用单一线性换算。

Details to investigate:
1. Check DataLoader.simulate_execution in data_loader.py: verify its current signature and fee logic so we keep it 100% intact.
2. Check current execution simulation and slippage logic in advisory_engine.py and data_loader.py (e.g. calculate_vwap_execution_slippage, calculate_otc_fund_execution_slippage, or related methods).
3. Investigate how fund quarterly reported top 5 holding stocks, their daily trading volume (ADV), and fund AUM are currently loaded, stored in data/cache or metadata, or how they should be extracted from DataLoader / FundMetadata / Portfolio.
4. Formulate the mathematical model for the non-linear liquidity haircut penalty for large redemptions/orders based on order size, fund AUM, and top 5 holdings ADV ratio. Ensure:
   - Non-linear (e.g. square-root or power model, Almgren-Chriss / Kyle lambda style);
   - Monotonically increasing with order size;
   - Free of static fake constants (rule 19 & 22 in GEMINI.md);
   - Distinguishes between OTC mutual funds and ETFs.
5. Provide exact function names, line numbers, data structures, and concrete implementation recommendations.
