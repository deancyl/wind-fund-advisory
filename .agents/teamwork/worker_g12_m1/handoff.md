# Milestone 1 Handoff Report: 4 Circuit-Breaker Bugs & Sentry Parameter Penetration

- **Agent**: `teamwork_worker` (`worker_g12_m1`)
- **Recipient**: `orchestrator_16` (`e873dbb9-9906-41d0-83a7-8e9eb7aaf59a`)
- **Timestamp**: 2026-11-08T15:42:00Z
- **Working Directory**: `d:\Google\Workspace\Wind\.agents\teamwork\worker_g12_m1\`
- **Milestone Status**: COMPLETED (100% Green, 57 passed across 5 test suites)

---

## 1. 观察事实 (Observation)

### 1.1 Bug 1: 相关性突变预警指示卡门禁与返回字典键名断路
- **修改前观察**:
  - `AGY2_FundAdvisory/app_gui.py` 第 2987 行使用幽灵键名：
    ```python
    if corr_eval_res.get("is_mutation_alarm") or corr_eval_res.get("is_regime_shift_risk"):
        safe_markdown_html(render_correlation_mutation_card_html(corr_eval_res))
    ```
  - `AGY2_FundAdvisory/portfolio_manager.py` 第 8628 行返回字典仅包含：
    ```python
    "is_triggered": is_triggered,
    "is_liquidity_shift_triggered": is_liquidity_shift_triggered,
    ```
  - 下游渲染器 `render_correlation_mutation_card_html` 依赖 `is_triggered` 与 `is_liquidity_shift_triggered`。原门禁导致预警卡在突破 0.75/0.80 时永远无法被渲染。
- **实施改动**:
  - `app_gui.py`: 将判断升级为四键兼容：
    ```python
    if corr_eval_res.get("is_triggered") or corr_eval_res.get("is_liquidity_shift_triggered") or corr_eval_res.get("is_mutation_alarm") or corr_eval_res.get("is_regime_shift_risk"):
        safe_markdown_html(render_correlation_mutation_card_html(corr_eval_res))
    ```
  - `portfolio_manager.py`: 返回字典中补齐别名键：
    ```python
    "is_triggered": is_triggered,
    "is_liquidity_shift_triggered": is_liquidity_shift_triggered,
    "is_mutation_alarm": is_triggered,
    "is_regime_shift_risk": is_liquidity_shift_triggered,
    ```

### 1.2 Bug 2: `sentry.inspect_portfolio` 缺少投资者风险等级与持仓实时报价注入
- **修改前观察**:
  - `AGY2_FundAdvisory/app_gui.py` 第 2725 行调用 `sentry.inspect_portfolio(pm_instance.holdings, snapshot_dict, fund_metadata=_f_metas)`，未传入 `investor_risk_tier`，且 `snapshot_dict` 来自 `StrategyBridge.get_latest_market_snapshot()`，不含单基实时行情字典 `fund_quotes`。
  - 导致 `ActiveRiskSentry` 维度 8 (适当性与组合止损巡检)因 `target_risk_tier=None` 被完全跳过；维度 9 (盘中实时异动与安全垫消耗传导)因 `fund_quotes={}` 恒为 0 被完全跳过。
- **实施改动**:
  - `app_gui.py`:
    ```python
    _cur_tier = str(st.session_state.get("active_tier_val", "C3")).upper()
    _f_metas = {}
    _f_quotes = {}
    for _c in pm_instance.holdings.keys():
        try:
            _f_metas[_c] = DataLoader.get_fund_metadata(_c) or {}
        except Exception:
            _f_metas[_c] = {}
        try:
            _q = fetch_realtime_fund_quote(_c, use_cache=True)
            if _q:
                _f_quotes[_c] = _q
        except Exception:
            pass

    _augmented_snapshot = dict(snapshot_dict) if isinstance(snapshot_dict, dict) else {}
    _augmented_snapshot["fund_quotes"] = _f_quotes
    _augmented_snapshot["investor_risk_tier"] = _cur_tier

    sentry_rep = sentry.inspect_portfolio(
        pm_instance.holdings,
        _augmented_snapshot,
        fund_metadata=_f_metas,
        investor_risk_tier=_cur_tier
    )
    ```

### 1.3 Bug 3: 指数与 ETF 联接基金盘中估值校准精度
- **修改前观察**:
  - `AGY2_FundAdvisory/portfolio_manager.py` 第 2176 至 2240 行的 `QDII_BENCHMARK_MAP` 与 `_apply_qdii_valuation_correction` 仅处理标普、纳指与黄金，未对国内主流宽基、行业指数及 ETF 联接基金（如科创50、中证红利、红利低波、芯片、沪深300等）提供基准校准，天天基金季报滞后估值无法得到实时修正。
  - 必须兼顾 `test_adv_qdii_micro_boundary_perturbation` (1.5% 阈值)、`test_adv_non_qdii_unaffected` (纯债 002351 不纠偏) 及 `test_calculate_intraday_pnl` (0.95 仓位折算)。
- **实施改动**:
  - `portfolio_manager.py`:
    - 建立扩展的 `INDEX_AND_FEEDER_BENCHMARK_MAP`（涵盖标普、纳指、黄金、科创50、芯片/半导体、红利低波、中证红利、沪深300、中证500、中证1000、白酒等），并保留 `QDII_BENCHMARK_MAP` 兼容别名。
    - 实装 `_apply_fund_valuation_calibration`（并保留 `_apply_qdii_valuation_correction` 别名）：
      - 针对联接基金 (`"联接" in f_n`)，按 `0.95` 仓位折算；纯指数基金按 `1.0` 折算。
      - 对 QDII/黄金标的，严格保持 `> 1.5%` 阈值纠偏；对 A 股指数与联接基金，当存在偏差 (`>0.1%` 或当前估算为 `0.0%`) 时结合实时基准涨跌幅进行纠偏覆盖。
      - 纯债/主动债标的（如 002351）不匹配基准，绝不误触发纠偏。

### 1.4 Bug 4: Tab 1 智能定投加权乖离率与 ERP 穿透
- **修改前观察**:
  - `AGY2_FundAdvisory/app_gui.py` 第 3887-3888 行直接使用 `snapshot.get("c300_bias_20", 1.0)` 和 `snapshot.get("erp_percentile", 78.0)`，使用单一沪深 300 替代整个建仓篮子，抹平了异质化组合的单基特性。
- **实施改动**:
  - `AGY2_FundAdvisory/advisory_engine.py`:
    - 在 `SmartExecutionDCAEngine` 类中实装 `compute_portfolio_weighted_bias_and_erp(allocations, snapshot)`：
      - 精算建仓标的加权 `bias_20`。
      - 纯债/黄金/固收对冲类资产对齐宏观中性 ERP，权益/行业资产结合自身乖离率动态调节 ERP，最终输出加权 `(weighted_erp_pct, weighted_bias_20)`。
  - `app_gui.py`:
    - 在智能定投模式下调用 `SmartExecutionDCAEngine.compute_portfolio_weighted_bias_and_erp(alloc_list_for_dca, snapshot)`，并将加权计算结果传入 `plan_smart_dca` 与 `get_historical_inflection_ruler`。

---

## 2. 逻辑推导链 (Logic Chain)

1. **依据 [1.1]**: `portfolio_manager.py` 与 `app_gui.py` 键名解耦导致卡片无法展示；在 GUI 端同时监听 `is_triggered` 与 `is_mutation_alarm`，并在底层同时返回两套键，建立互补双保险，彻底消除断路。
2. **依据 [1.2]**: `ActiveRiskSentry` 内部已具备完善的适当性 (D8) 与盘中安全垫传导 (D9) 计算逻辑，但缺乏输入参数。通过在 `app_gui.py` 中显式从 `st.session_state` 提取 `active_tier_val` 并拉取 `pm_instance.holdings` 实时估值注入 `_augmented_snapshot["fund_quotes"]`，使 D8 和 D9 在首屏双翼看板真实激活生效。
3. **依据 [1.3]**: ETF 联接基金法定 90%~95% 投资于目标 ETF，其实际日内波动严格等于场内 ETF 变动乘以 0.95。建立基准映射后，通过实时拉取场内 ETF/指数行情纠偏天天基金季报滞后估算，同时隔离纯债资产，并保持既有 QDII 1.5% 阈值，既修正了估值失真又保证了旧有单测 100% 兼容。
4. **依据 [1.4]**: 用户建仓通常为混合组合（如科技成长 + 红利低波 + 纯债），单基乖离率与估值分位各不相同。通过加权聚合各标的指标，定投乘数真实反映了建仓标的的整体估值位置，杜绝了宏观沪深 300 与组合标的脱节的误判风险。

---

## 3. 注意事项与边界说明 (Caveats)

1. **只读裁判文件零改动**: 四大只读裁判文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）哈希未变，只读锁定未受任何影响。
2. **全局 GEMINI.md 零触碰**: 未修改全局 `c:\Users\deanc\.gemini\GEMINI.md`。
3. **网络与防抖缓存**: 在单元测试中，由于 `fetch_realtime_index_quote` 具备 15 秒内存缓存，单测中使用 `clear_realtime_cache()` 与 `unittest.mock.patch("AGY2_FundAdvisory.portfolio_manager.fetch_realtime_index_quote")` 进行了环境隔离，防止真实网络或上一测试缓存污染测试结果。

---

## 4. 实施结论 (Conclusion)

Milestone 1 的 4 大断路 Bug 全部闭环修复，代码修改严格遵循最小化原则，在 `tests/test_g12_circuit_breakers_and_sentry.py` 中编写了 11 项高质量针对性单测，全量 5 项测试套件累计 57 项自动化测试 100% 绿灯通过，无任何回归问题。

---

## 5. 独立验证方法 (Verification Method)

在 PowerShell 终端执行以下测试命令，确认 100% 通过：

1. **基础设施与反作弊裁判校验 (14 tests passed)**:
   ```powershell
   py -3 -m pytest tests/test_infra.py -v
   ```
2. **新增 G12 M1 专项测试 (11 tests passed)**:
   ```powershell
   py -3 -m pytest tests/test_g12_circuit_breakers_and_sentry.py -v
   ```
3. **因子演化闭环与全量核心业务测试 (14 tests passed)**:
   ```powershell
   py -3 -m pytest tests/test_adv_final_closure.py -v
   ```
4. **G10 相关性突变与蒙特卡洛压力测试 (6 tests passed)**:
   ```powershell
   py -3 -m pytest tests/test_g10_correlation_liquidity_and_stress.py -v
   ```
5. **盘中盈亏计算与调仓升级测试 (12 tests passed)**:
   ```powershell
   py -3 -m pytest AGY2_FundAdvisory/tests/test_live_rebalance_upgrades.py -v
   ```
