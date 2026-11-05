## 2026-11-05T16:30:36Z
You are Worker Prod r10_m1 (teamwork_worker).
Working directory: d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r10_m1
Original user request path: d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
Project plan path: d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_1\PROJECT.md
Explorer 1 handoff path: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r10_1\handoff.md
Explorer 1 analysis path: d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r10_1\analysis.md

[MANDATORY INTEGRITY WARNING]
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

[PHYSICAL SAFETY REDLINES]
1. 严禁修改只读裁判文件（judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py），保持哈希完好无损。
2. 严禁修改 DataLoader.simulate_execution 的默认函数签名与默认扣费逻辑。

[EXCLUSIVE WRITE OWNERSHIP]
You exclusively own and may edit:
- AGY2_FundAdvisory/advisory_engine.py
- AGY2_FundAdvisory/data_loader.py
- AGY2_FundAdvisory/trading_clock_fee.py
- AGY2_FundAdvisory/portfolio_manager.py
- AGY2_FundAdvisory/strategy_bridge.py
- AGY2_FundAdvisory/winrate_engine.py
- src/analysis/market_temperature.py (if needed for compliance text)
DO NOT edit app_gui.py in this milestone (owned by M2/M3). DO NOT edit tests/test_infra.py.

[MILESTONE 1 TASKS]
1. 修正红利低波赛道错误指数代码：
   - 在 advisory_engine.py 中，将 RADAR_SECTOR_CATALOG["dividend_low_vol"] 的 benchmark_index 和 index_code 彻底修正为 "H30269"（绝非 000978，000978 为医药100！），symbol 设为 "H30269"，并添加 fallback_parquet 为 "data/processed/csindex_H30269.parquet"。
   - 在 data_loader.py 的 IndexValuationEngine 中，确保 H30269 正确映射，并从 aliases 列表中移除 "000978"，彻底杜绝交叉污染。
2. 区分 QDII 跨时区基金、纯债基金与普通 A 股基金的交割清算规则及估值可信度标签：
   - 在 trading_clock_fee.py 与 portfolio_manager.py 中：
     a. 实现 `is_qdii_fund(fund_code, fund_name="") -> bool`，准确识别 QDII 海外品种（如 050025 标普500、001071 华安纳指、013402 恒生科技等，包含代码或名称特征）。
     b. 对美股 QDII 基金推算交割时明确标注「T+2 确认份额 · 赎回 T+6~T+8 到账（跨时区清算，不可用于 T+2 极速换仓）」，确认周期设为 T+2，赎回周期推算为 T+6~T+8 到账。
     c. 在 portfolio_manager.py 与 strategy_bridge.py 的 `calculate_rebalance_routes` 与 `calculate_rebalance_net_utility` 中，若涉及 QDII 基金或跨 TA 品种，严禁列入同公司 T+1 转换候选（强制跳过 PRIORITY_1_SWITCH）。
     d. 在计算 Tab 2「T+2 在途踏空风险」时，自动排除 QDII 基金。
     e. 在 trading_clock_fee.py 或 portfolio_manager.py 中提供统一的基金估值可信度判定函数 `get_fund_valuation_credibility(fund_code, fund_name="", asset_class="") -> Tuple[str, str]`：
        - 指数联接基金 -> 「指数高准度」
        - 纯债基金 -> 「债基看久期票息」
        - 美股 QDII -> 「美股休市·看隔夜期指」
        - 主动混合基金 -> 「季报重仓估算」
3. 替换违规“保本”承诺词汇，符合证监会投顾合规要求：
   - 在 winrate_engine.py、strategy_bridge.py、src/analysis/market_temperature.py 中，将“保本率”严格替换为合规术语「正收益概率 (≥0%)」或「本金安全率」，保留合规免责声明（如“不构成保本保收益承诺”）。（app_gui.py 的文案替换留在 M3）。
4. 统一 14 大赛道动量与乖离率的价格口径（消除分红季全收益指数跃升偏误）：
   - 在 advisory_engine.py 的 `_calc_dynamic_sector_metrics` 中，计算 20 日短期均线乖离率 bias_20 时，对红利类指数优先使用价格指数（000922.SH / H30269）或经除权分红脉冲平滑的日度序列，避免全收益指数在分红集中派息日产生虚假的正乖离脉冲而误报超买。

[VERIFICATION]
Run targeted unit tests using run_command (e.g. pytest tests/ -k "dividend or qdii or winrate" or run existing tests). Ensure 100% pass!
Write a complete handoff.md in your working directory following the Handoff Protocol (Observation, Logic Chain, Caveats, Conclusion, Verification Method).
When done, call send_message to report back with summary and handoff.md path.
