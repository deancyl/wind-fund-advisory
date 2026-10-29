# Handoff Report — Remediation Explorer (explorer_remediation_1)

## 1. Observation

1. **违规字典与假打分直接源头 (Verbatim Observation)**:
   - 文件：`d:\Google\Workspace\Wind\AGY2_FundAdvisory\strategy_bridge.py`，第 286~326 行：
     ```python
     FUND_SIX_DIMENSION_PROFILE: Dict[str, Dict[str, float]] = {
         # 纯债固收
         "002351": {"alpha": 95.0, "fee": 98.0, "risk": 100.0, "smart_money": 88.0, "crowding": 98.0, "macro": 92.0},
         "000086": {"alpha": 91.5, "fee": 95.0, "risk": 100.0, "smart_money": 85.0, "crowding": 97.0, "macro": 90.0},
         ... (共 25 只核心基金静态数值)
     }
     ```
   - 第 3171 行 `StrategyBridge.calculate_fund_six_dimension_score`：
     ```python
     code = str(fund_code).strip().zfill(6)
     prof = FUND_SIX_DIMENSION_PROFILE.get(code, {
         "alpha": 85.0, "fee": 85.0, "risk": 90.0,
         "smart_money": 85.0, "crowding": 88.0, "macro": 88.0
     })
     ```
   - 前端调用位置：`d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py` 第 870 行：
     ```python
     df_quant = StrategyBridge.get_tier_quant_selection_table(active_tier, st.session_state.custom_fund_overrides)
     ```
     通过 `strategy_bridge.py` 第 3265、3290 行将假字典打分逐行投喂至用户可见前端。

2. **真实多因子评分引擎状态 (Verbatim Observation)**:
   - 文件：`d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py`，第 3596~3747 行已完整实现 `compute_fund_six_dimension_score`。
   - 接入底层：`data/storage.duckdb` 真实视图（`v_scorecards`, `v_fund_snapshot`, `v_fund_trading_rules`, `v_northbound_holdings`）与三层通用财务排雷 `screen_fund_look_through_risk`。
   - 独立运行时测试：
     `PortfolioManager().compute_fund_six_dimension_score('002351')` 返回动态结果：
     ```python
     {
         'fund_code': '002351', 'track_role': '', 'asset_class': '纯债固收',
         'alpha_score': 88.0, 'fee_score': 96.2, 'risk_score': 100.0,
         'smart_money_score': 95.4, 'crowding_score': 97.0, 'anti_crowding_score': 97.0,
         'macro_align_score': 91.0, 'macro_derivative_score': 91.0,
         'weights': {'alpha': 0.35, 'fee': 0.25, 'risk': 0.15, 'smart_money': 0.1, 'crowding': 0.1, 'macro_align': 0.05},
         'total_score': 93.64
     }
     ```
   - 对 `SECTOR_FUND_SELECTION_BY_TIER` 全量 27 只入选赛道基金运行批处理打分测试，全部在合法区间 [60.0, 100.0] 内计算成功，无任何异常。

3. **双端调用差异与 KeyError 风险**:
   - `strategy_bridge.py` 中的 `get_tier_quant_selection_table` 使用了 `champ_scores["overall_score"]`；
   - `portfolio_manager.py` 的 `compute_fund_six_dimension_score` 返回字典仅含 `"total_score"`，缺失 `"overall_score"` 别名；
   - 若直接无缝替换而不做别名对齐，会触发 `KeyError: 'overall_score'`。

---

## 2. Logic Chain

1. 基于 Observation 1，`strategy_bridge.py` 中的静态字典 `FUND_SIX_DIMENSION_PROFILE` 是导致 Forensic Auditor 门禁一票否决 🔴 INTEGRITY VIOLATION 的唯一根因。
2. 基于 Observation 2，`portfolio_manager.py` 已具备完备的真实动态 DuckDB 多因子评分引擎 `compute_fund_six_dimension_score`，全量 27 只标的实测 100% 具备真实数据支撑与计算能力，完全无需任何静态假数据兜底。
3. 基于 Observation 3，在委托过程中必须在桥接层或数据源层将 `overall_score` 与 `total_score` 双向对齐映射，以保证对 `app_gui.py` 与 `test_acceptance_r1_r7.py` 的 100% 零破坏兼容。
4. 为防止顶层模块导入时的潜在循环依赖与高频重复实例化开销，必须在 `StrategyBridge` 内部采用 `_get_portfolio_manager(cls)` 延迟单例模式，并引入 30 秒短时防抖缓存 `_SIX_DIM_SCORE_CACHE`。
5. 因此，整改路径清晰明确、技术风险为零、对既有代码体系零负面影响。

---

## 3. Caveats

- 本次勘测为纯只读模式，未对 `AGY2_FundAdvisory` 下任何源码执行物理修改；
- `compute_fund_six_dimension_score` 在对全量 20 只基金逐一进行穿透排雷时涉及底层 DuckDB 磁盘查询，单次全量耗时约 5~10 秒；通过单例复用 `PortfolioManager` 的内生缓存与桥接层 30 秒防抖缓存，可实现界面交互与切档时的毫秒级零延迟。

---

## 4. Conclusion

1. **整改方案定稿**:
   - 彻底删除 `strategy_bridge.py` 第 286~326 行的 `FUND_SIX_DIMENSION_PROFILE` 全局字典；
   - 在 `strategy_bridge.py` 中引入 `_get_portfolio_manager` 延迟单例方法与 `_SIX_DIM_SCORE_CACHE` 防抖缓存；
   - 将 `StrategyBridge.calculate_fund_six_dimension_score` 重构为直接委托 `pm.compute_fund_six_dimension_score`，并自动对齐 `overall_score` / `total_score`；
   - 在 `portfolio_manager.py` 的返回字典中补充注入 `"overall_score": total_score`；
   - 在 `tests/test_architecture_m3.py` 中增加 AST 扫描断言与打分一致性断言。
2. **完整技术蓝图交付**:
   已将包含逐行改造代码、兼容性矩阵与执行工序的详细蓝图完整沉淀在：
   `d:\Google\Workspace\Wind\.agents\teamwork\explorer_remediation_1\analysis.md`。

---

## 5. Verification Method

整改实施后，按以下步骤进行独立验证：

1. **验证硬编码字典被彻底清除 (AST & Text Inspection)**:
   ```powershell
   # 必须返回 0 个匹配
   Select-String -Path 'd:\Google\Workspace\Wind\AGY2_FundAdvisory\strategy_bridge.py' -Pattern 'FUND_SIX_DIMENSION_PROFILE'
   ```
2. **验证 Bridge 与 PM 动态打分 100% 对齐**:
   ```powershell
   cd d:\Google\Workspace\Wind\AGY2_FundAdvisory
   python -c "from strategy_bridge import StrategyBridge; from portfolio_manager import PortfolioManager; s1 = StrategyBridge.calculate_fund_six_dimension_score('002351')['total_score']; s2 = PortfolioManager().compute_fund_six_dimension_score('002351')['total_score']; assert s1 == s2, f'Mismatched: {s1} vs {s2}'; print('Parity Verified:', s1)"
   ```
3. **验证只读裁判基建文件 0 字节变更**:
   ```powershell
   git diff HEAD -- AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md AGY2_FundAdvisory/tests/test_infra.py
   ```
4. **运行全量测试回归**:
   ```powershell
   cd d:\Google\Workspace\Wind\AGY2_FundAdvisory
   pytest tests/ -v
   ```
