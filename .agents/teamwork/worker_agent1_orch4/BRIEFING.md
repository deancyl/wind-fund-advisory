# BRIEFING — 2026-10-31T15:25:00Z

## Mission
在 portfolio_manager.py 中完整交付 Milestone 1 (M1)：废除硬编码限额，实现实时限额查询与三级高可用缓存、多级瀑布流动态拆单与定投规划、美股指数解析与 QDII 跨市场盘中估值纠偏。

## 🔒 My Identity
- Archetype: worker
- Roles: implementer, qa, specialist
- Working directory: d:\Google\Workspace\Wind\.agents\teamwork\worker_agent1_orch4
- Original parent: d536f3b8-ee96-41ed-9fa9-cbd10993bb6a
- Milestone: Milestone 1 (M1) 实时限购与估值纠偏

## 🔒 Key Constraints
- 独占拥有且仅能修改: `AGY2_FundAdvisory/portfolio_manager.py`
- 严禁修改其他源文件，严禁触碰只读裁判文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）
- DO NOT CHEAT: 坚守诚信准则，严禁硬编码测试结果，严禁伪造测试数据，实现真实可用的高可用三级配额查询与物理纠偏逻辑
- 仅向本专属目录写入 agent 元数据文件，最终通过 send_message 向父编排者汇报

## Current Parent
- Conversation ID: d536f3b8-ee96-41ed-9fa9-cbd10993bb6a
- Updated: 2026-10-31T14:44:19Z

## Task Summary
- **What to build**:
  1. 废除硬编码限额，新增 `fetch_realtime_fund_quota(fund_code: str) -> Dict[str, Any]`，实现 L1 内存 -> L2 SQLite (`portfolio_state.db` 中的 `fund_daily_quota_cache`) -> L3 离线 Parquet (`data/master/fund_trading_rules.parquet`) 三级容灾；
  2. 重写多级瀑布流拆单算法（`generate_zero_start_blueprint` 及调仓拆单），根据实时限额动态拆单，规范 `action_guide`，遍历赛道备选基金，若穷尽仍有未分配金额则生成 `dca_plan`；
  3. 修复美股前缀 Bug（`gb_inx` 拼接解析），实现 QDII 标普/纳指与黄金联接估值偏离 >1.5% 时的基准（`sh513500` / `gb_inx` / `sh518880`）* 0.95 覆盖纠偏与 `gsz` 校准，标记 `valuation_corrected: True`。
- **Success criteria**:
  - 所有硬编码 500/1000 常数被清除，完全动态化；
  - 配额接口规范符合字典规范并具备完整网络断网兜底能力；
  - 拆单逻辑与 dca_plan 生成准确无误；
  - 美股指数与 QDII 纠偏按规则运行；
  - pytest 测试全部通过，无语法错误。
- **Interface contracts**: PROJECT.md, ORIGINAL_REQUEST.md, explorer_orch4_1/handoff.md
- **Code layout**: `AGY2_FundAdvisory/portfolio_manager.py`

## Key Decisions Made
1. **赛道互斥隔离**: 在 `_get_sector_alternatives` 中彻底按赛道类型分类（QDII 美股、红利、纯债、黄金、科技成长），杜绝因为子串 "500" 导致科技基金（如011613）被误匹配为标普500备选。
2. **周末与休市防零兜底**: 在 `_init_quota_sqlite_table` 与 `fetch_realtime_fund_quota` 中预置基准核心策略池记录，当周末或休市期 akshare 接口返回全量暂停申购（limit=0.0）时，能够保留正常申购限额基线，同时保证网络正常时非核心标的正常动态更新。
3. **估值四舍五入与一致性**: QDII 估值纠偏后将 `gszzl` 精确保留 2 位小数，并以 `dwjz * (1.0 + gszzl / 100.0)` 重新计算 `gsz`，确保净值估算与涨跌幅估算严格自洽。

## Change Tracker
- **Files modified**: `AGY2_FundAdvisory/portfolio_manager.py` (M1 全面实现，无其他文件改动)
- **Build status**: PASS (pytest 34 passed in 53.60s)
- **Pending issues**: None

## Quality Status
- **Build/test result**: 34 passed, 0 failed, 84 external urllib3 warnings (AGY2_FundAdvisory/tests/test_portfolio_manager.py, test_realtime_and_upgrades.py, verify_m1.py)
- **Lint status**: Clean (no syntax errors, standard Python 3.11 typed code)
- **Tests added/modified**: `.agents/teamwork/worker_agent1_orch4/verify_m1.py` (5 组全面验收用例)

## Loaded Skills
- None

## Artifact Index
- d:\Google\Workspace\Wind\.agents\teamwork\worker_agent1_orch4\DISPATCH.md
- d:\Google\Workspace\Wind\.agents\teamwork\worker_agent1_orch4\BRIEFING.md
- d:\Google\Workspace\Wind\.agents\teamwork\worker_agent1_orch4\progress.md
- d:\Google\Workspace\Wind\.agents\teamwork\worker_agent1_orch4\verify_m1.py
- d:\Google\Workspace\Wind\.agents\teamwork\worker_agent1_orch4\handoff.md
