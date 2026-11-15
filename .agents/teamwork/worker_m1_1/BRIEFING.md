# BRIEFING — 2026-11-15T08:32:00Z

## Mission
完成 Milestone 1 (M1: 十维真实投票与汇率校验及胶囊联动) 全部 6 项核心特性开发与 100% 自动化测试验证。

## 🔒 My Identity
- Archetype: worker
- Roles: implementer, qa, specialist
- Working directory: d:\Google\Workspace\Wind
- State folder: d:\Google\Workspace\Wind\.agents\teamwork\worker_m1_1
- Original parent: a29ecba0-a4ab-4a58-a8c7-4276082800c0
- Milestone: M1 (十维真实投票与汇率校验及胶囊联动)

## 🔒 Key Constraints
- Physical security baseline: 严禁修改 judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py。
- 严禁修改 DataLoader.simulate_execution 的默认签名与默认费率逻辑。
- 专属修改文件范围: AGY2_FundAdvisory/advisory_engine.py, AGY2_FundAdvisory/data_loader.py, AGY2_FundAdvisory/strategy_bridge.py, AGY2_FundAdvisory/portfolio_manager.py, AGY2_FundAdvisory/app_gui.py, tests/test_g19_m1_ten_dimension_and_memo.py。
- Integrity Mandate: 严禁伪造测试、硬编码预期输出或使用虚拟外观模式；必须具备真实状态与真实行为。
- 全中文回复与交付。

## Current Parent
- Conversation ID: a29ecba0-a4ab-4a58-a8c7-4276082800c0
- Updated: not yet

## Task Summary
- **What to build**: 
  1. 维度6产业估值真数据驱动（读取全市场14大赛道真实估值分位、前3大机会赛道平均分位<=35%为BULL +5%，中位数>70%为BEAR -5%，其余NEUTRAL并上报真实数值）；
  2. 维度7资金情绪多维融合（真实成交额+多方上涨家数占比+14赛道平均拥挤度，<55或动量衰竭为BEAR -5%，>=72且未过热为BULL +2%，报出真实数值）；
  3. 维度10期权衍生品与避险（隐波>28%或相关性突变强制BEAR -8%，隐波<22%且贴水有安全垫无突变为BULL +2%，报出真实数值）；
  4. 熔断门禁（ivix>=32.0或dyn_corr>=0.80或usdcnh_chg>0.60%触发一票否决，物理冻结所有delta_pct>0归零，标记circuit_breaker_triggered: True）；
  5. 拔除 6.6676 与 5.0000 兜底常数并增加合理性校验哨（离岸人民币汇率点位必须在 [6.85, 7.60] 区间内，若异常校准为近期截面数据 7.2385，美债校准为 4.42%，中美利差校准为 -278.2 bp）；
  6. 胶囊4（持仓病灶）与胶囊5（今日行动准则）知行合一联动（存在免赎尾仓/深套出血点/红牌止盈预警时，胶囊5主副标题优先输出账户级实战指令）；
  7. 编写并运行自动化测试套件 tests/test_g19_m1_ten_dimension_and_memo.py。
- **Success criteria**: 6 大特性全部真实落地，单元测试 100% 通过，既有测试无回归。
- **Interface contracts**: PROJECT.md, SCOPE.md
- **Code layout**: AGY2_FundAdvisory/

## Key Decisions Made
- [Feature 1]: 维度 6 废除 `n_radar >= 2` 恒真条件，采用 `OpportunityRadarEngine.get_cached_sectors_fast()` 穿透 14 赛道真实估值分位数，Top 3 均值 <= 35% 判定 BULL (+5%)，全市场中位数 > 70% 判定 BEAR (-5%)。
- [Feature 2]: 维度 7 接入两市真实成交额（turnover_str）与多方上涨占比（up_pct），结合 14 赛道平均拥挤度评分，拥挤度 < 55 或动量衰竭为 BEAR (-5%)，>= 72 且未过热为 BULL (+2%)。
- [Feature 3]: 维度 10 接入 option_iv_pct 与 ic_annualized_basis_rate，隐波 > 28% 或动态相关性突变强制 BEAR (-8%)，隐波 < 22% 且贴水充足且无突变为 BULL (+2%)。
- [Feature 4]: 十维投票汇总门禁植入一票否决熔断，ivix >= 32.0 或 dyn_corr >= 0.80 或 usdcnh_chg > 0.60% 时物理冻结所有正向加仓为 0.0%，并打上熔断标记。
- [Feature 5]: 全工作区彻底清除 6.6676 和 5.0000（全局扫描 0 匹配），增加 [6.85, 7.60] 范围哨兵，异常校准为近期真实截面 7.2385、4.42% 与 -278.2 bp。
- [Feature 6]: generate_chief_advisor_memo 与 render_chief_advisor_memo_card 知行合一联动，检出尾仓或深套时主结论直显实战指令（如“清扫19只尾仓·置换深套”），副标题同步。
- [Testing]: 编写 tests/test_g19_m1_ten_dimension_and_memo.py 包含 6 大测试类共 28 项针对性用例，联合 33 项既有用例（共 61 项用例）100% 绿灯通过。

## Artifact Index
- `DISPATCH.md` — 派发指令
- `BRIEFING.md` — 运行态记忆与约束
- `progress.md` — 存活心跳与进度
- `handoff.md` — 交付报告与法证证据链
- `tests/test_g19_m1_ten_dimension_and_memo.py` — 新增全量 M1 自动化测试套件

## Change Tracker
- **Files modified**:
  - `AGY2_FundAdvisory/data_loader.py`: 拔除 6.6676/5.0000，注入汇率 [6.85, 7.60] 与美债校准哨。
  - `AGY2_FundAdvisory/strategy_bridge.py`: 拔除 6.6676/5.0000，注入快照校准哨。
  - `AGY2_FundAdvisory/portfolio_manager.py`: 拔除 6.6676，QDII 套利接入校准汇率。
  - `AGY2_FundAdvisory/advisory_engine.py`: 重构十维投票（维度6、7、10与熔断门禁），重构备忘录胶囊4与5知行合一联动，拔除 6.6676/5.0000。
  - `AGY2_FundAdvisory/app_gui.py`: 拔除 6.6676，胶囊4与5联动渲染对齐，防御 None 时间戳。
  - `tests/test_g15_phase2_memo_and_timemachine.py`: 更新断言对齐知行合一实战指令。
  - `tests/test_g19_m1_ten_dimension_and_memo.py`: 新建包含 28 项测试的综合测试套件。
- **Build status**: 全部通过 (61/61 PASSED)
- **Pending issues**: 无

## Quality Status
- **Build/test result**: 61 passed in 21.08s (100% 绿灯)
- **Lint status**: 0 stale constants across workspace
- **Tests added/modified**: tests/test_g19_m1_ten_dimension_and_memo.py (28 new tests)

## Loaded Skills
- None
