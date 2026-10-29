# Handoff Report: Core Quant Engine Architecture Survey

**From**: Core Quant Engine Explorer (`explorer_orch3_1`)  
**To**: Orchestrator (`6e8d54f5-05f1-4da4-a35e-9c3d019df46f`), Agent-1 (Strategy & Risk), Agent-2 (PM & Screening)  
**Date**: 2026-10-30  
**Handoff Type**: Hard (Investigation Completed)  
**Deliverable Document**: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_orch3_1\analysis.md`

---

## 1. Observation

1. **`strategy_bridge.py:compute_dynamic_tier_weights` 缺失**：
   - 全文 grep 检索 `def compute_dynamic_tier_weights` 结果为 0。
   - 现有档位权重通过硬编码字典 `TIER_TARGET_WEIGHTS` (`strategy_bridge.py:232-275`) 声明，并在 `get_tier_target_weights` (`strategy_bridge.py:2824-2845`) 中返回：
     ```python
     # strategy_bridge.py:2837-2845
     t = str(tier).upper().strip() if tier else "C3"
     if t == "C3":
         if market_state_code in ["GROWTH_BULL", "STRUCTURAL_500"]:
             return dict(TIER_TARGET_WEIGHTS["C3_ATTACK"])
         return dict(TIER_TARGET_WEIGHTS["C3"])
     elif t in TIER_TARGET_WEIGHTS:
         return dict(TIER_TARGET_WEIGHTS[t])
     return dict(TIER_TARGET_WEIGHTS["C3"])
     ```
   - C1、C2、C4、C5 均直接返回静态常量字典，完全不响应任何市场状态（包括 `SEVERE_BEAR` 破位防御态）。
   - 权重单调性倒挂：`C3_ATTACK` 中股票权益总权重为 `0.30 + 0.15 + 0.25 + 0.15 = 0.85` (85%)，而高风险等级的 `C4` 股票权益总权重仅为 `0.30 + 0.18 + 0.24 = 0.72` (72%)，导致 $C3 > C4$ 发生单调性违背。

2. **`strategy_bridge.py:get_rebalance_grid_status` 点位计算与倒挂**：
   - 源码观察 (`strategy_bridge.py:1613-1620`)：
     ```python
     c300_price = float(q_300.get("point", 4053.0)) if q_300.get("point", 0) > 0 else 4053.0
     if 3500.0 <= c300_price <= 4800.0:
         breakdown_c300 = round(c300_price * (4180.5 / 4053.0), 1)
     else:
         scale = (c300_price / c300_curr) if c300_curr > 0 else (4053.0 / 6100.0)
         breakdown_c300 = round(m20 * scale, 1)

     surge_c300 = round(c300_price * (1.0 + 0.039), 1)
     ```
   - 当 `c300_price = 4053.0` 时，`breakdown_c300 = 4180.5`。防守破位触发线严格高于当前现价（倒挂 +3.15%）。
   - 向上进攻线 `surge_c300` 仅为简单静态 `* 1.039`，未基于 MA20/60/120 真实相对位置计算。

3. **`portfolio_manager.py:screen_fund_look_through_risk` 硬编码名单**：
   - 源码观察 (`portfolio_manager.py:3581-3596`)：
     `financial_codes` 集合中穷举硬编码了 77 只金融机构股票代码（含 41 家银行、11 家险资及综合金融、25 家券商）。
   - 源码观察 (`portfolio_manager.py:3491-3495`)：
     `NON_ASHARE_CODES` 集合硬编码了 12 只非 A 股基金代码。
   - 源码观察 (`portfolio_manager.py:3056`)：
     `_evaluate_all_transition_tags` 包含 18 只基金代码的元组匹配。
   - 源码观察 (`portfolio_manager.py:3244-3264`)：
     `EXEMPT_OVERLAP_PAIRS` 包含 16 组 `frozenset` 静态代码对。
   - 缺失第二层与第三层通用基本面排雷逻辑：非金融标的直接取 `fin_data.get("double_high_risk")` 扣 40 分，未结合经营活动现金流净额 (CFO/OCF) 与重资产资本开支结构进行交叉校验。

4. **统一资产分类解析器缺失与 `cat_map` 硬编码**：
   - `portfolio_manager.py` 与 `strategy_bridge.py` 中不存在任何动态资产分类解析器函数（`classify_fund_asset_class` 为 0 结果）。
   - `app_gui.py:1869-1874` 存在仅包含 16 只基金的静态 `cat_map`。`000086`、`013841`、`090010` 等不在其中的标的全部被归入“其他存量资产”。

5. **六维量化选基评分伪造与硬编码**：
   - `strategy_bridge.py:285-325` 声明了 `FUND_SIX_DIMENSION_PROFILE` 静态字典，硬编码了 25 只基金的 6 维分值；
   - `calculate_fund_six_dimension_score` (`strategy_bridge.py:2905-2978`) 仅从该静态字典中取值加权，未利用 DuckDB (`v_scorecards`, `v_fund_trading_rules`, `v_northbound_holdings`, `v_futures_basis`) 真实数据进行 Min-Max 正规化。

6. **建仓蓝图生成函数重复**：
   - `generate_zero_start_blueprint` 在 `strategy_bridge.py:3062` 和 `portfolio_manager.py:2494` 双重定义，且各自内嵌了完全相同的静态权重字典。

---

## 2. Logic Chain

1. **从硬编码字典到 AST 静态审计失效**：
   - 项目后续验收标准中明确要求：“运行 AST 静态代码审计，确认不存在针对特定股票代码的硬编码 if/else 分支或静态豁免名单”。
   - 当前在 `portfolio_manager.py`（第 3581 行 `financial_codes`、第 3491 行 `NON_ASHARE_CODES`、第 3244 行 `EXEMPT_OVERLAP_PAIRS`）及 `strategy_bridge.py`（第 232 行 `TIER_TARGET_WEIGHTS`、第 285 行 `FUND_SIX_DIMENSION_PROFILE`）存在大量集合与字典硬编码。
   - 推论：若直接进行 AST 审计，系统将立即失败，重构必须彻底拔除这些静态名单，改为动态属性驱动。

2. **从伪线性插值到防守线点位倒挂**：
   - 开发者在 `strategy_bridge.py:1929` 将 4053.0 定义为 `BASE_C300`，4180.5 定义为 `BASE_M20`。
   - 在第 1614 行计算防守线时直接使用了 `c300_price * (4180.5 / 4053.0)`，由于该比例为 1.0315，导致在价格 4053 时，防守线算为 4180.5。
   - 推论：防守线本应在现价下方提供支撑警示，却被计算到了现价上方，造成“现价已低于跌破线”的反逻辑现象。必须改为根据实际 MA60/MA120 真实相对位置或百分比下界，严格保证 `breakdown < price < breakout`。

3. **从静态 `cat_map` 到大类分类失真**：
   - `app_gui.py` 的 `cat_map` 仅维护了 16 个键。当用户选择 C1（包含工银纯债 000086）或 C5（包含银华芯片 013841）时，这些核心基金由于不在字典中被赋予“其他存量资产”。
   - 推论：导致 Tab 1 中的大类配置条形图出现荒谬的“其他存量资产占比 35%”现象。必须由 `portfolio_manager.py` 提供统一的 `classify_fund_asset_class`，按基金名称和投资风格动态推导。

4. **从静态六维字典到真量化选基漏斗**：
   - 现有的六维选基展示数据来自手写静态分值，失去了实时行情、北向资金变动与期指基差的联动能力。
   - 推论：DuckDB 中已备齐所需视图，只需由 Agent-2 编写动态评分与 Min-Max 映射管道，即可消除伪造打分。

---

## 3. Caveats

1. **裁判基建物理隔离红线**：
   勘测确认了 4 个裁判基建文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）处于系统监控只读状态，重构过程中严禁任何改动或解锁。
2. **测试用例历史依赖性**：
   既有部分测试（如 `test_acceptance_r1_r7.py` 中测试招商银行、农业银行免存贷双高的用例）直接验证了相关函数输出结果，在重构为通用申万行业识别后，必须保证既有测试语义完全向下兼容且 100% 通过。
3. **DuckDB 视图查询开销与缓存**：
   动态六维选基若每次实时遍历全表会产生一定 I/O 开销，重构时需采用内存缓存机制（如 TTL 缓存或组合级批量查询），确保 GUI 渲染流畅。

---

## 4. Conclusion

1. **`strategy_bridge.py` 需由 Agent-1 完成重构**：
   - 移除 `TIER_TARGET_WEIGHTS`，实现真动态 `compute_dynamic_tier_weights`，以目标波动率和最大回撤为边界约束，实现主升浪进攻态、震荡收息态与破位防御态自适应，并数学保证 $C1 < C2 < C3 < C4 < C5$ 单调性；
   - 修复 `get_rebalance_grid_status` 点位计算，基于 MA20/60/120 真实相对位置，杜绝点位倒挂；
   - 将 DR007、利差、期指贴水与期权 IV 深度接入动态资产权重决策链。
2. **`portfolio_manager.py` 需由 Agent-2 完成重构**：
   - 彻底清除 77 只金融股硬编码白名单与 16 组静态豁免对，落地基于申万行业与现金流交叉验证的三层通用基本面排雷引擎；
   - 实现全局统一的 `classify_fund_asset_class`，支持任意公募基金的大类智能归属，彻底移除 `app_gui.py` 的静态 `cat_map`；
   - 打通 DuckDB，实现真多因子六维选基动态正规化评分，剔除 `FUND_SIX_DIMENSION_PROFILE` 伪造字典；
   - 收拢 `generate_zero_start_blueprint`，消除重复实现。

---

## 5. Verification Method

后续重构代码可执行以下独立验证：

1. **全项目自动化测试套件回归验证**：
   ```bash
   python -m pytest AGY2_FundAdvisory/tests
   ```
   断言全部 222+ 项测试用例 100% 通过。

2. **AST 反硬编码静态审计验证**：
   对 `portfolio_manager.py`、`strategy_bridge.py` 与 `app_gui.py` 进行 AST 遍历，断言不存在包含 6 位股票代码的静态集合与 if/else 豁免分支。

3. **双向触发点位倒挂验证**：
   针对任意当前指数点位调用 `StrategyBridge.get_rebalance_grid_status()`，断言：
   ```python
   assert grid["breakdown_threshold_c300"] < grid["c300_current"] < grid["surge_threshold_c300"]
   ```

4. **C1 至 C5 风险单调性验证**：
   在牛市、震荡、熊市不同行情截面下调用 `compute_dynamic_tier_weights`，断言：
   ```python
   assert equity_w["C1"] < equity_w["C2"] < equity_w["C3"] < equity_w["C4"] < equity_w["C5"]
   ```
