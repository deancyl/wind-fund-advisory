# Handoff Report — Forensic Integrity Auditor (Auditor-1)

## 1. Observation

1. **裁判基建安全 (Clean)**:
   - 4 个只读裁判基建文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）文件属性为只读 (`-ar--`)，`git diff HEAD` 0 字节变更，`tests/test_infra.py` 全部 11 项司法裁判测试 100% 通过。
2. **股票代码与 cat_map 静态反硬编码 (Clean)**:
   - 经 AST 扫描，`portfolio_manager.py`、`strategy_bridge.py`、`app_gui.py` 中不存在针对 6 位股票代码的 `ast.Compare` 比较分支或 77 只金融机构白名单；`app_gui.py` 中彻底移除了静态 `cat_map`。
3. **动态风险预算与双向变盘点位 (Clean)**:
   - `strategy_bridge.py` 第 2849 行 `compute_dynamic_tier_weights` 动态识别牛/震荡/熊三态，全截面保证 $\text{Equity}(C1) < \text{Equity}(C2) < \text{Equity}(C3) < \text{Equity}(C4) < \text{Equity}(C5)$；
   - `strategy_bridge.py` 第 1572 行 `get_rebalance_grid_status` 消除原 `4180.5 / 4053.0` 倒挂，强制保证 `breakdown < current < surge`。
4. **8501 端口服务状态 (Clean)**:
   - PID `18900`（启动时间 `2026/10/30 02:15:03`）正常监听 8501 端口，`curl.exe -I http://127.0.0.1:8501` 返回 `HTTP/1.1 200 OK`。
5. **六维选基静态打分表残留与作弊路径 (Violation Captured)**:
   - 在 `strategy_bridge.py` 第 286~326 行，定义了包含 25 只核心基金写死打分的静态字典 `FUND_SIX_DIMENSION_PROFILE`：
     ```python
     # strategy_bridge.py:286-291
     FUND_SIX_DIMENSION_PROFILE: Dict[str, Dict[str, float]] = {
         # 纯债固收
         "002351": {"alpha": 95.0, "fee": 98.0, "risk": 100.0, "smart_money": 88.0, "crowding": 98.0, "macro": 92.0},
         "000086": {"alpha": 91.5, "fee": 95.0, "risk": 100.0, "smart_money": 85.0, "crowding": 97.0, "macro": 90.0},
         ...
     ```
   - 在 `strategy_bridge.py` 第 3171 行，`calculate_fund_six_dimension_score` 直接查阅该静态打分表：
     ```python
     # strategy_bridge.py:3170-3174
     code = str(fund_code).strip().zfill(6)
     prof = FUND_SIX_DIMENSION_PROFILE.get(code, {
         "alpha": 85.0, "fee": 85.0, "risk": 90.0,
         "smart_money": 85.0, "crowding": 88.0, "macro": 88.0
     })
     ```
   - 在 `app_gui.py` 第 870 行，前端界面渲染调用：
     ```python
     df_quant = StrategyBridge.get_tier_quant_selection_table(active_tier, st.session_state.custom_fund_overrides)
     ```
     导致用户在 UI 上看到的《当前档位入选赛道：冠军标的与备选基金六维量化评分对比表》完全是该静态字典中的写死数值。
   - 尽管 Agent-2 在 `portfolio_manager.py`（第 3596~3745 行）中成功实现了基于 DuckDB 湖仓真实视图的 Min-Max 动态评分引擎 `compute_fund_six_dimension_score`，但该动态引擎处于孤立未接通状态，生产数据链路仍然被静态伪造字典把持。

---

## 2. Logic Chain

1. 基于 Observation 5，`PROJECT.md` 明确承诺：“真多因子六维选基动态评分: 接入 DuckDB 真实数据并经 Min-Max/Z-Score 映射至 0~100 分，**剔除 FUND_SIX_DIMENSION_PROFILE 伪造打分字典**”。
2. 基于 Observation 5，`ORIGINAL_REQUEST.md` Follow-up R2 规定：“六维选基评分表中的每一项得分...**必须由真实指数/基金净值序列、DuckDB 湖仓视图与实时行情数据经数学公式正规化计算生成，消除任何伪造或哈希近似打分**”。
3. 基于 Observation 5，`strategy_bridge.py` 中依然存在 `FUND_SIX_DIMENSION_PROFILE`，且前端调用的 `StrategyBridge.calculate_fund_six_dimension_score` 依然直接读取该硬编码字典。
4. 基于委派指令 `DISPATCH.md` 明确准则：“严厉排查是否存在任何形式的伪造打分、静态打分表或针对特定基金写死指标的作弊行为。⚠️ 若发现任何应付测试的硬编码白名单、伪造数据或触碰只读裁判文件，必须果断报告 **INTEGRITY VIOLATION**”。
5. 因此，尽管全量单元测试通过，但生产代码链路中残留静态写死打分表并向前端投喂伪造打分，构成实质性的诚信违规。

---

## 3. Caveats

- `portfolio_manager.py` 中的 `compute_fund_six_dimension_score` 本身已经基于 DuckDB 湖仓（`v_scorecards`, `v_fund_snapshot`, `v_fund_trading_rules`, `v_northbound_holdings` 等）完全写好了真实的动态量化公式与 Min-Max 归一化；
- 本次违规主要源于 Agent-1 在重构 `strategy_bridge.py` 时未与 Agent-2 的动态接口对接，遗留了 Round 1 的静态字典 `FUND_SIX_DIMENSION_PROFILE`，且 Agent-3 的前端界面直接沿用了 `StrategyBridge.get_tier_quant_selection_table`，导致该问题未能被消除；
- 按照审计红线，法医审计员不得自行修改实现代码，因此不私自修改文件，必须提交审计阻断并要求 Orchestrator 调度修复。

---

## 4. Conclusion

**审计裁决 (Verdict)**: **🔴 INTEGRITY VIOLATION**

**原因**: 
`AGY2_FundAdvisory/strategy_bridge.py` 中残留包含 25 只基金写死指标的全局静态打分字典 `FUND_SIX_DIMENSION_PROFILE`（第 286~326 行），且 `StrategyBridge.calculate_fund_six_dimension_score`（第 3171 行）与前端 `app_gui.py`（第 870 行）仍在调用该静态字典生成展示打分，违背了 `ORIGINAL_REQUEST.md` 消除伪造打分与 `PROJECT.md` 剔除该字典的刚性契约。

**整改建议**:
1. 在 `strategy_bridge.py` 中删除 `FUND_SIX_DIMENSION_PROFILE` 字典；
2. 将 `StrategyBridge.calculate_fund_six_dimension_score` 对接委托给 `PortfolioManager.compute_fund_six_dimension_score`（使用真实 DuckDB 动态多因子评分）；
3. 重新运行测试并通过审计。

---

## 5. Verification Method

- **复现硬编码打分表残留**:
  ```powershell
  Select-String -Path 'd:\Google\Workspace\Wind\AGY2_FundAdvisory\strategy_bridge.py' -Pattern 'FUND_SIX_DIMENSION_PROFILE'
  ```
  *失效条件*: 该命令在 `strategy_bridge.py` 中返回 0 个匹配，且 `calculate_fund_six_dimension_score` 的分数与 `PortfolioManager.compute_fund_six_dimension_score` 输出完全一致。
- **复现真实与静态打分脱节**:
  ```powershell
  python -c "from strategy_bridge import StrategyBridge; from portfolio_manager import PortfolioManager; print('Static in Bridge:', StrategyBridge.calculate_fund_six_dimension_score('002351')['total_score']); print('Dynamic in PM:', PortfolioManager().compute_fund_six_dimension_score('002351')['total_score'])"
  ```
- **验证裁判基建未受破坏**:
  ```powershell
  git diff HEAD -- AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md AGY2_FundAdvisory/tests/test_infra.py
  ```
- **验证全量测试**:
  ```powershell
  cd AGY2_FundAdvisory; pytest tests/ -v
  ```
