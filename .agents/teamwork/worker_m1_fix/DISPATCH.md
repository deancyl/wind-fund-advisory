## 2026-10-29T09:46:31Z
You are Worker Milestone 1 Remediation (worker_m1_fix).
Your working directory is: d:\Google\Workspace\Wind\.agents\teamwork\worker_m1_fix
Your parent conversation ID is: 5fd996d1-bc98-447a-9f35-c5aef5be2e1c (Project Orchestrator).

MANDATORY FIRST STEP:
Read the following authoritative documents before starting work:
1. d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
2. d:\Google\Workspace\Wind\PROJECT.md
3. d:\Google\Workspace\Wind\.agents\teamwork\challenger_m1_2\handoff.md
4. d:\Google\Workspace\Wind\.agents\teamwork\challenger_m1_1\handoff.md
5. d:\Google\Workspace\Wind\.agents\teamwork\reviewer_m1_2\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

EXCLUSIVE WRITE OWNERSHIP:
You own `d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py`.
DO NOT modify read-only files (`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`).

OBJECTIVE:
Apply the targeted defensive bug fixes identified by Challenger 1, Challenger 2, and Reviewer 2 in `portfolio_manager.py`:
1. Add a safe numerical parsing helper:
   ```python
   def _safe_float(val: Any, default: float = 0.0) -> float:
       try:
           if val is None or pd.isna(val):
               return default
           return float(val)
       except Exception:
           return default
   ```
2. Safe `top_stocks` retrieval and non-empty check (around lines 2885-2892 and 2950):
   Ensure `top_stocks` is guaranteed to be a list, even if `look_data["top_stocks"]` is None.
3. Defensive non-A-share check (around line 2893-2901):
   Guard against `None` or `int` in `top_stocks`: use `s and any(k in str(s) for k in ...)` and `re.search(r"\([A-Z\.]+\)", str(s))`.
4. Financial and pledge metric parsing (around line 2983-2998):
   Use `_safe_float` for `goodwill_ratio_pct`, `fcf_billion`, `pledge_ratio_controlling_pct`.
   In pledge lookup, if stock is not found in `p_df`, do NOT fall back to `p_df.iloc[0]`; use empty dict / 0.0 default.
5. Lockup calendar parsing (around lines 3005-3020):
   Do not match empty string `name_or_code` against calendar dataframe.
   For `days_to_unlock`, handle `np.nan` safely:
   `raw_days = l_target.get("days_to_unlock")`
   `days_to_unlock = int(_safe_float(raw_days, 999)) if raw_days is not None and not pd.isna(raw_days) else None`
   Use `_safe_float` for `unlock_market_value_billion` and `unlock_ratio_total_pct`.

VERIFICATION:
Run the tests:
1. `python -m pytest AGY2_FundAdvisory/tests/test_adversarial_m1_challenger2.py`
2. `python -m pytest AGY2_FundAdvisory/tests`
Verify that ALL tests pass 100% without any failures!

Write your handoff report to `d:\Google\Workspace\Wind\.agents\teamwork\worker_m1_fix\handoff.md` and send a message to parent.
