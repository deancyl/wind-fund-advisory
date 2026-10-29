# DEAD_ENDS.md — Append-Only Log of Failed Approaches

| Iteration | Approach Tried | Why It Failed | Files Touched |
|-----------|---------------|---------------|---------------|
| 1 | 保留 `FUND_SIX_DIMENSION_PROFILE` 静态字典并让 `StrategyBridge.calculate_fund_six_dimension_score` 读取该硬编码字典 | 法医审计一票否决 (INTEGRITY VIOLATION)：生产链路依然被静态伪造打分字典占领，违背 PROJECT.md 与 ORIGINAL_REQUEST.md 消除伪造打分的刚性契约 | `strategy_bridge.py` |
