# Auditor Fix Plan

1. Read ORIGINAL_REQUEST.md, PROJECT.md, and auditor_orch3_1/handoff.md.
2. Scan strategy_bridge.py for FUND_SIX_DIMENSION_PROFILE or any hardcoded score dictionaries via AST.
3. Verify 4 referee files remain 100% untouched.
4. Verify dynamic score computation and de-mining logic integrity.
5. Provide handoff report with clear CLEAN or INTEGRITY VIOLATION verdict.
