# Worker Task Assignment: Milestone 1 量化核心算法升级与穿透计算

## 目标
实装 G5 世代四大核心量化投顾计算底座，消除伪常数与伪随机数，实现纯净真实时序驱动的量化引擎。

## 独占拥有的文件（Write Ownership）
- `AGY2_FundAdvisory/advisory_engine.py`
- `AGY2_FundAdvisory/portfolio_manager.py`
- `AGY2_FundAdvisory/strategy_bridge.py`

## 严禁修改的文件（Strict Read-Only）
- `judge_engine.py`
- `holdout_vault.py`
- `AGENT_SPEC.md`
- `tests/test_infra.py`
- `DataLoader.simulate_execution` 默认签名与扣费逻辑

## 实施要求与规范
1. **单基真实历史波动率与乖离率穿透 (`advisory_engine.py`)**：
   - 彻底消除 `calculate_vwap_execution_slippage` 中的三档固定常数回退（0.04、0.14、0.18）及 `else 0.18`。
   - 新增 `@classmethod def get_fund_real_volatility_and_bias(cls, fund_code, fund_name="") -> Dict[str, float]`：从本地单基净值 parquet、细分指数 parquet、`aligned_matrix_total_return.parquet` 或 9 大类映射中提取最近 21 个交易日时序，计算 20 日真实年化波动率（`std * sqrt(250)`）与自身 20 日均线乖离率 `bias_20 = (nav - ma20) / ma20 * 100`。
   - 当 `calculate_vwap_execution_slippage` 的入参 `volatility` 为 None 时，自动调用穿透方法；当 `bias_20` 为 None 时，自动穿透该标的自身乖离率；保持入参签名向下兼容。
   - 修改 `plan_smart_dca` 内部调用，确保各标的传入自身穿透的真实波动率与真实乖离率。

2. **历史三大拐点实盘对照尺 (`advisory_engine.py` & `strategy_bridge.py`)**：
   - 在 `SmartExecutionDCAEngine` 新增 `@classmethod def get_historical_inflection_ruler(cls, current_erp=None, current_bias=None, total_capital=100000.0) -> Dict[str, Any]`。
   - 聚合 2021-02-18 核心见顶 (0.50x)、2022-04-26 恐慌底 (1.93x)、2024-09-18 反转底 (1.94x) 及今日实时水位 (1.76x)；在 `StrategyBridge` 增加对应静态暴露。

3. **浮盈安全垫抗震承压与本金破净临界点模型 (`portfolio_manager.py` & `strategy_bridge.py`)**：
   - 纠偏 `FUND_INDEX_PRICE_MAP` 中 `013841` 映射为 `STAR50_STITCH`。
   - 在 `PortfolioManager` 实现标的历史 Beta 测算（基于 `aligned_matrix_total_return.parquet` 相对 `H00300` 的协方差/方差，涵盖 9 大资产类别：科创50 1.235、中证1000 1.032、中证500 1.018、沪深300 1.000、中证红利 0.667、红利低波 0.590、标普500 0.122、黄金 0.011、纯债 -0.012，现金=0）。
   - 实现 `calculate_portfolio_cushion_and_stress_model(self, custom_erp=None)`：
     - 计算组合加权 Beta $\beta_p = \sum \frac{m_i}{E} \beta_i$；
     - 结合累计浮盈 $\Delta P$ 与年化票息安全垫 $Y_{\text{ann}}$，得出综合安全垫 $S_{\text{cushion}} = \Delta P + Y_{\text{ann}}$ 与厚度比例 `cushion_ratio = S_cushion / C_total`；
     - 计算破净跌幅 $R_{m,\text{break}} = - \frac{S_{\text{cushion}}}{E \times \beta_p}$ 与点位，或回本涨幅 $R_{m,\text{recover}} = \frac{|\Delta P|}{E \times \beta_p}$；
     - 推演大盘急跌 -3%、周度回调 -5%、极端回调 -10% 三档压力测试下组合总值与剩余安全垫；
   - 在 `StrategyBridge` 增加对应静态接口。

4. **14:30 尾盘实时估值异动预警算法 (`advisory_engine.py` & `strategy_bridge.py`)**：
   - 实现 `@classmethod def evaluate_tail_valuation_anomaly(cls, fund_code, fund_name="", realtime_quote=None) -> Dict[str, Any]`：
     - 利用 `fetch_realtime_fund_quote` 真实 `gszzl`（盘中估算涨跌幅）；
     - 利用真实单基 20 日日均波动幅度 `sigma_day = ann_vol / sqrt(250)` 与自身 `bias_20`；
     - 当 `gszzl > 1.5 * sigma_day * 100` 且 `bias_20 > 0`：触发 `ANTI_CHASING`（防追高脉冲，建议当日买入额下调 30%~50%）；
     - 当 `gszzl < -1.5 * sigma_day * 100` 且 `bias_20 < 0`：触发 `GOLDEN_PIT`（黄金坑错杀，建议 14:30~14:50 正常或适度增配 10%~20%）；
     - 否则 `NORMAL`。

5. **验证方法**：
   - 编写或运行针对上述新方法的独立核验脚本；
   - 运行已有的 `pytest tests/test_infra.py` 和 `pytest tests/test_adv_final_closure.py`，确保原有全部用例 100% 保持绿色！

## MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.


## 2026-11-06T17:09:39Z
[Message] timestamp=2026-11-06T17:09:39Z sender=71f16351-ac4e-45f7-b8a4-89e38ec8863c priority=MESSAGE_PRIORITY_HIGH content=你是一个高级量化与软件工程师（teamwork_worker）。
你的专属工作目录是：d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r12_m1\
上级调度员 ID: 71f16351-ac4e-45f7-b8a4-89e38ec8863c

【必须阅读的基准文档】
- 原始需求：d:\Google\Workspace\Wind\.agents\teamwork\ORIGINAL_REQUEST.md
- 项目架构与契约：d:\Google\Workspace\Wind\.agents\teamwork\orchestrator_7\PROJECT.md
- 任务派发规范：d:\Google\Workspace\Wind\.agents\teamwork\worker_prod_r12_m1\DISPATCH.md
- 勘测报告参考：
  - d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r12_1\report.md (单基波动率与乖离率穿透方案代码草案)
  - d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r12_2\report.md (历史拐点对照与尾盘估值异动方案代码草案)
  - d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r12_3\report.md (加权Beta、安全垫破净承压数学模型代码草案)

【独占写权限文件】
- AGY2_FundAdvisory/advisory_engine.py
- AGY2_FundAdvisory/portfolio_manager.py
- AGY2_FundAdvisory/strategy_bridge.py

【只读禁改红线】
- judge_engine.py, holdout_vault.py, AGENT_SPEC.md, tests/test_infra.py 严禁做任何修改！
- DataLoader.simulate_execution 默认函数签名与扣费逻辑严禁修改！

【MANDATORY INTEGRITY WARNING】
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

【核心实施任务】
1. 消除 calculate_vwap_execution_slippage 中的固定常数（0.04、0.14、0.18 及 else 0.18），实装 get_fund_real_volatility_and_bias，打通真实 20 日波动率与自身 bias_20 穿透；
2. 实装 get_historical_inflection_ruler，提供历史三大拐点与当前市场水位的对照尺；
3. 实装 14:30 尾盘实时估值异动（防追高脉冲与黄金坑错杀）预警方法 evaluate_tail_valuation_anomaly；
4. 纠偏 FUND_INDEX_PRICE_MAP 中 013841 映射，实装标的真实历史 Beta 测算与组合加权 Beta、浮盈安全垫抗震承压与破净临界点模型 calculate_portfolio_cushion_and_stress_model；
5. 在 StrategyBridge 暴露上述新方法的静态桥接；
6. 运行验证测试（原有的 pytest tests/test_infra.py 和 tests/test_adv_final_closure.py 必须全部保持 100% 通过）；
7. 产出详尽的 handoff.md 并在完成后使用 send_message 向 71f16351-ac4e-45f7-b8a4-89e38ec8863c 汇报。
