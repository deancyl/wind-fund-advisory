# Handoff Report: Phase 0 Technical Survey (R5, R6, R8)

## 1. Observation
1. **R5 穿透函数未暴露注入接口**:
   - `AGY2_FundAdvisory/portfolio_manager.py:4162` (`calculate_look_through_industry_exposure`) 硬编码循环 `for code, h in self.holdings.items():`。
   - `AGY2_FundAdvisory/portfolio_manager.py:4268` (`calculate_stock_overlap_matrix`) 硬编码读取 `self.holdings`。
   - `AGY2_FundAdvisory/portfolio_manager.py:4426` (`get_portfolio_look_through_stocks`) 与第 4518 行 (`get_portfolio_look_through_stocks_df`) 硬编码读取 `self.holdings`。
   - `AGY2_FundAdvisory/portfolio_manager.py:5327` (`calculate_portfolio_penetration_risk`) 硬编码读取 `self.holdings`。
   - `AGY2_FundAdvisory/portfolio_manager.py` 内部持仓类定义为 `FundHolding` (第 260 行)，不存在 `HoldingItem` 类。然而 `AGY2_FundAdvisory/app_gui.py` 在第 5210、5228、5245 行执行了 `from portfolio_manager import HoldingItem`，当切换到“新建仓组合”或“调仓后组合”时直接触发 `ImportError: cannot import name 'HoldingItem'`。
   - `AGY2_FundAdvisory/app_gui.py:1871-1886` 中的 4 个缓存函数 (`_cached_look_through_industry`, `_cached_stock_overlap`, `_cached_penetration_risk`, `_cached_stocks_df`) 接收 `holdings_repr: str` 但在函数体内部完全未向 `pm` 传递持仓；且第 5451 行的聪明钱拥挤度监控错误循环了 `pm.holdings.items()` 而非 `active_examine_holdings.items()`。
   - `PortfolioManager.classify_fund_asset_class` 在 `portfolio_manager.py:4526-4745` 缺乏对 `UNIVERSE_18_CHAMPION_POOL` (定义在 `strategy_bridge.py:170`) 与细分赛道反查机制，导致缺少名称时无法识别医药 (161726)、白酒 (161725)、银行 (160418)、恒科 (013402)、芯片 (008888)。
2. **R6 动态指标与估值分位兜底分析**:
   - `AGY2_FundAdvisory/advisory_engine.py:440-443` 在动态指标缺失时兜底为常数：`er_20: 0.50, bias_20: 1.0, crowding_score: 85.0`。
   - `AGY2_FundAdvisory/advisory_engine.py:350-356` 中存在写死常数与空 `pass`：
     ```python
     if sec_id in ("pure_bond", "bond"):
         return 40.0
     elif sec_id in ("domestic_gold", "gold"):
         return 52.0
     elif sec_id in ("dividend_low_vol", "csi_dividend", "banking_dividend"):
         pass
     ```
   - 本地 `data/storage.duckdb` 包含视图 `v_indices`（内含 754 个指数日线数据，覆盖 000933, 000932, 399986, 000685 等数千行真实日线）与 `v_chinabond_yield_curve`（国债收益率与期限利差）；`data/global/global_indices.parquet` 覆盖 HSTECH 与 SPX；`data/processed/aligned_matrix_total_return.parquet` 覆盖 10 个关键指数的日度总回报序列。
3. **R8 物理安全红线基线**:
   - 4 大裁判文件的现行 SHA256 为：
     - `AGY2_FundAdvisory/judge_engine.py`: `76f930371176de7ee6a413174b030101e3210ac6e037f5d10fe229af31cc07be`
     - `AGY2_FundAdvisory/holdout_vault.py`: `88122eaf647040a410e2fd95da81077db10149a498a47340ff40b670bd031d2a`
     - `AGY2_FundAdvisory/AGENT_SPEC.md`: `a346586f9bd2dc0ee83e665bd18e7a6471464c9f7b658e392b989b800cd63957`
     - `tests/test_infra.py`: `48bee0da300d7c0a0848ec1376e4b9b2e55224d2736081713b4340f0362cd100`
   - `DataLoader.simulate_execution` 位于 `AGY2_FundAdvisory/data_loader.py:1096`，其默认入参为 `(weights_df, prices_df, is_otc=True, penalty_days=7, penalty_rate=0.015, etf_impact=0.001)`，具有不可篡改性约束。

## 2. Logic Chain
1. 基于观察 1，由于 `calculate_look_through_industry_exposure`、`calculate_stock_overlap_matrix`、`calculate_portfolio_penetration_risk`、`get_portfolio_look_through_stocks_df` 均未提供 `holdings_override` 参数，Tab 4 界面上无论用户选择“新建仓组合”还是“调仓后组合”，后端始终只能拉取默认实盘持仓，导致前后端完全脱靶。
2. 基于观察 1，`HoldingItem` 类缺失将导致用户在前端点击切换非实盘组合时直接崩溃；且若 `HoldingItem` 没有在实例化时将 `shares * current_nav` 自动赋值给 `market_value`，则即使注入持仓，所有计算函数的 `total_market_val` 也将为 0。
3. 基于观察 1，`classify_fund_asset_class` 缺乏对 `UNIVERSE_18_CHAMPION_POOL` 和细分赛道的反向字典映射，在缺乏名称输入时无法解析赛道基金代码，从而触发模糊兜底。
4. 基于观察 2，`OpportunityRadarEngine` 的动态指标虽然在所有 Parquet 存在时能计算出结果，但代码层未接入 DuckDB 与 NAV Cache 提取，且估值分位存在 `pass` 空分支与 40.0/52.0 写死常数，不符合生产级真实动态要求。
5. 基于观察 3，裁判文件 SHA256 与 `simulate_execution` 签名已建立严密基线，后续实施必须原封不动予以保护。

## 3. Caveats
- 本次调研为 Phase 0 只读调研，未直接修改任何生产源码。
- 本地 `data/cache/market_screener/nav_cache` 目录目前文件数为 0，但 `data/processed/funds/` 存在基础基金 parquet，且本地 DuckDB `v_indices` 包含 754 个指数日线。后续动态指标流水线应优先使用 `v_indices` 与 `data/processed/indices/` 及 `aligned_matrix`。
- 部分老旧单测（如 `test_adversarial_orch3_challenger2.py`）包含对废弃分类名称的预期，后续实施时应以项目最新规范与 `test_ui_pro_redesign_verification.py` 为准。

## 4. Conclusion
1. **R5 方案明确可执行**:
   - 在 `portfolio_manager.py` 中为 4 个穿透函数增加可选参数 `holdings_override: Optional[Dict[str, Any]] = None`；
   - 显式声明 `HoldingItem` 类并支持 `market_value` 自动折算与属性兼容；
   - 升级 `classify_fund_asset_class`，纳入 `UNIVERSE_18_CHAMPION_POOL`、`SECTOR_FUND_SELECTION` 与 DuckDB 视图，彻底消除“其他权益资产”；
   - 修复 `app_gui.py` 缓存与聪明钱循环，将 `active_examine_holdings` 真实打通。
2. **R6 方案明确可执行**:
   - 在 `OpportunityRadarEngine._calc_dynamic_sector_metrics` 中建立 Parquet -> DuckDB -> NAV Cache -> 对齐矩阵的多级抽取流水线；
   - 重构 `get_sector_valuation_percentile`，删除 `pass`，纯债与黄金基于 120日/60日真实均线乖离率与利差动态精算。
3. **R8 基线已固化**:
   - 4 大裁判文件 SHA256 哈希值已完整归档，`simulate_execution` 签名已确认。
   - 专项防作弊测试 A、B、C、D 规范已在报告中详细定义。

## 5. Verification Method
- **报告与文档核验**:
  查看详细调研报告 `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r9_3\report.md`。
- **裁判文件防篡改核验**:
  运行命令 `py -3 -c "import hashlib; print(hashlib.sha256(open('AGY2_FundAdvisory/judge_engine.py', 'rb').read()).hexdigest())"`，核对是否等于 `76f930371176de7ee6a413174b030101e3210ac6e037f5d10fe229af31cc07be`。
- **动态指标与分类核验**:
  运行 `py -3 -m pytest tests/test_sectors_genuine_metrics.py tests/test_ui_pro_redesign_verification.py`。
