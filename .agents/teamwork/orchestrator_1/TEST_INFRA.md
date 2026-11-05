# E2E Test Infra: Advisor Terminal Advanced Upgrade

## Test Philosophy
- Opaque-box, requirement-driven. Derives from ORIGINAL_REQUEST.md.
- Strict Invariants:
  1. Read-only judge files (`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`) SHA256 unchanged.
  2. `DataLoader.simulate_execution` signature & default fees unchanged.
  3. No "保本率" in UI source code.
  4. H30269 for dividend_low_vol (never 000978).
  5. QDII fund (050025) has T+2 confirm, T+6~T+8 arrive, excluded from same-company T+1 conversion.
  6. Streamlit 4-tab AppTest 0 exceptions.

## Feature Inventory
| # | Feature | Source | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|---|---------|--------|:------:|:------:|:------:|:------:|
| 1 | H30269 纠偏 | ORIGINAL_REQUEST 一.1 | ✓ | ✓ | ✓ | ✓ |
| 2 | QDII 跨时区清算与排除转换 | ORIGINAL_REQUEST 一.2a | ✓ | ✓ | ✓ | ✓ |
| 3 | 4档估值可信度标签 | ORIGINAL_REQUEST 一.2b | ✓ | ✓ | ✓ | ✓ |
| 4 | 全站去除“保本率” | ORIGINAL_REQUEST 一.3 | ✓ | ✓ | ✓ | ✓ |
| 5 | Bias20 价格口径分红平滑 | ORIGINAL_REQUEST 一.4 | ✓ | ✓ | ✓ | ✓ |
| 6 | @st.fragment 4大区块局部刷新 | ORIGINAL_REQUEST 二.1 | ✓ | ✓ | ✓ | ✓ |
| 7 | 数据源时效状态徽章 | ORIGINAL_REQUEST 二.2 | ✓ | ✓ | ✓ | ✓ |
| 8 | 首屏视觉提权与双翼折叠 | ORIGINAL_REQUEST 三.1 | ✓ | ✓ | ✓ | ✓ |
| 9 | 表格防丢数自动入库拦截器 | ORIGINAL_REQUEST 三.2 | ✓ | ✓ | ✓ | ✓ |
| 10 | nav_history 记账与走势图 | ORIGINAL_REQUEST 三.3 | ✓ | ✓ | ✓ | ✓ |
| 11 | 一键跟单打卡闭环 | ORIGINAL_REQUEST 三.3 | ✓ | ✓ | ✓ | ✓ |

## Test Architecture
- Test suite: `tests/test_adv_upgrade_suite.py`
- Test runner: `py -3 -m pytest tests/test_adv_upgrade_suite.py -v`
- Full regression: `py -3 -m pytest tests/test_infra.py -v`
- AppTest: `py -3 -m pytest tests/test_streamlit_apptest_run.py -v`
