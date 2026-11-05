# Task Assignment: Forensic Auditor M1 (Integrity Verification & Referee Hash Lock Auditor)

## Authoritative Request File
`d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md` (MUST read completely before proceeding)
`d:\Google\Workspace\Wind\.agents\teamwork\orchestrator\PROJECT.md` (Master Architecture & Milestone Contracts)
`d:\Google\Workspace\Wind\GEMINI.md` (Workspace Rules)
`d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_m1\handoff.md` (Worker M1 Handoff Report)

## Scope & Forensic Audit Objective
You are Forensic Auditor M1 (`teamwork_auditor`). Perform exhaustive, zero-tolerance integrity verification for Milestone 1:
1. **Physical Safety Redline Audit**:
   - Compute SHA-256 hashes of:
     * `tests/test_infra.py` (Must equal: `48bee0da300d7c0a0848ec1376e4b9b2e55224d2736081713b4340f0362cd100`)
     * `AGY2_FundAdvisory/judge_engine.py` (Must equal: `76f930371176de7ee6a413174b030101e3210ac6e037f5d10fe229af31cc07be`)
     * `AGY2_FundAdvisory/holdout_vault.py` (Must equal: `88122eaf647040a410e2fd95da81077db10149a498a47340ff40b670bd031d2a`)
     * `AGY2_FundAdvisory/AGENT_SPEC.md` (Must equal: `a346586f9bd2dc0ee83e665bd18e7a6471464c9f7b658e392b989b800cd63957`)
     * `AGY2_FundAdvisory/tests/test_infra.py` (Must equal: `b8d781be8135be05cf61e62e4b534e359985ad880f27ffb61228a33df6b02a6a`)
   - Check `git status --porcelain` on these 5 files.
2. **Cheating & Facade Audit**:
   - Check for hardcoded test returns or mocks in production source code (`data_loader.py`, `cache_manager.py`, `market_screener.py`, `portfolio_manager.py`).
   - Check that EastMoney live queries and fallback are authentic.
   - Check that `INDEX_PE_METAS` and `3210 / 1780` are completely purged from production code.
3. **Execution Validation**:
   - Run: `py -3 -m pytest tests/test_infra.py`
   - Run: `cmd /c "set PYTHONPATH=AGY2_FundAdvisory;. && py -3 -m pytest AGY2_FundAdvisory/tests/test_m1_open_data_and_cache.py -v"`
4. Give a clear verdict: `CLEAN` or `INTEGRITY VIOLATION`.

## Working Directory
`d:\Google\Workspace\Wind\.agents\teamwork\auditor_m1/`

## Output Requirements
Write your full forensic audit report to:
`d:\Google\Workspace\Wind\.agents\teamwork\auditor_m1\handoff.md`
Then call `send_message` to parent.
