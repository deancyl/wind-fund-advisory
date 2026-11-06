# Handoff Report: Code Survey on PortfolioManager (R2 & R5)

## 1. Observation
- **`classify_fund_asset_class` 定义与行号**：
  在 `AGY2_FundAdvisory/portfolio_manager.py` 第 4647 行至第 4774 行。
  当前方法签名：
  ```python
  @classmethod
  def classify_fund_asset_class(
      self_or_cls,
      fund_code: Optional[str] = None,
      fund_name: Optional[str] = None
  ) -> str:
      code_s = str(fund_code or "").strip().zfill(6)
      name_s = fund_name
      if not name_s and hasattr(self_or_cls, "holdings") and code_s in self_or_cls.holdings:
          name_s = self_or_cls.holdings[code_s].fund_name
      return _CLASSIFY_ASSET_CLASS_CACHE.get((code_s, name_s or "")) or PortfolioManager._do_classify_asset_class(code_s, name_s)
  ```
- **实测类方法缺陷验证**：
  执行包含实例持仓名称查找的测试脚本：
  ```python
  pm = PortfolioManager(db_path=":memory:")
  pm.holdings["888881"] = FundHolding(fund_code="888881", fund_name="特别超短债理财A", ...)
  print(pm.classify_fund_asset_class("888881"))
  ```
  实测输出：`核心蓝筹`（错误命中兜底逻辑）；
  原因：方法使用 `@classmethod` 装饰，无论使用 `pm.classify(...)` 还是 `PortfolioManager.classify(...)`，首个形参 `self_or_cls` 接收到的均为 `PortfolioManager` 类，`hasattr(self_or_cls, "holdings")` 永远为 `False`。
- **目录元数据与导入观察**：
  - `CORE_STRATEGY_POOL`（第 322 行）：定义为字典，包含 050025、005561、002351、000216 等 13 只核心基金。
  - `EXTENDED_FUND_CATALOG`（第 722 行）：备选池。
  - `SECTOR_FUND_SELECTION`（第 730 行）：赛道基金选拔表。
  - `resolve_fund_meta`（第 3191 行）：基于天天基金盘中行情接口 `fetch_realtime_fund_quote` 具备真实基金名称反查能力，实测：
    `pm.resolve_fund_meta("161726")['fund_name'] == "招商国证生物医药指数A"`
    `pm.resolve_fund_meta("161725")['fund_name'] == "招商中证白酒指数A"`
  - `strategy_bridge` 顶层导入检查：全局静态搜索确认 `strategy_bridge` 仅在第 4805 行函数体局部导入，顶层未导入，无循环依赖风险。
  - 导入错误发现：第 4717 行 `from data_loader import get_fund_metadata` 抛出 `ImportError: cannot import name 'get_fund_metadata' from 'data_loader'`，被 `except Exception: pass` 静默捕获。
- **9 大测试标的实测结果**：
  在第 4727~4761 行规则中：
  - 161726 -> `中盘均衡` (代码匹配，名称含生物医药)
  - 161725 -> `核心蓝筹` (代码匹配，名称含白酒消费)
  - 160418 -> `A股红利高股息` (代码匹配，名称含银行金融)
  - 013402 -> `科技成长进攻` (代码匹配，名称含恒生科技)
  - 008888 -> `科技成长进攻` (代码匹配，名称含半导体芯片)
  - 050025 -> `美股海外对冲` (代码匹配，名称含标普500)
  - 005561 -> `A股红利低波` (代码匹配，名称含红利低波)
  - 002351 -> `纯债固收` (代码匹配，名称含债裕祥)
  - 000216 -> `黄金对冲` (代码匹配，名称含黄金)
  - 全部 9 只标的 100% 映射至 9 大标准大类，无一返回“其他权益资产”。
- **`initial_baseline_snapshot` 与调仓复盘审计现状**：
  - 声明位置：`__init__` 第 2480 行 `self.initial_baseline_snapshot: Dict[str, Any] = {}`。
  - 未在 `_export_state_dict`（第 3027 行）与 `_import_state_dict`（第 3064 行）中参与持久化。
  - `evaluate_rebalance_audit` 位于第 6267 行，采用当前实盘资产减影子资产。
  - 动态响应测试：`FundHolding.market_value` 为静态保存值，若外部修改 `h.current_nav` 但未调用 `_recalculate_totals()`，`pm.total_equity` 保持旧值。
- **单元测试实测结果**：
  执行命令：`py -3 -m pytest tests/test_adv_final_closure.py tests/test_anticheat_suite.py`
  结果：`tests/test_adv_final_closure.py` 全部 3 项通过 (100%)；`tests/test_anticheat_suite.py` 全部 11 项通过 (100%)。

## 2. Logic Chain
1. 基于观测中“`@classmethod` 将实例调用硬绑定为类”的事实，第 4661 行 `hasattr(self_or_cls, "holdings")` 在实例调用时永远为 `False`，导致持仓上下文丢失；
2. 引入 `_HybridAssetClassifier` 混合方法描述符可以在 `instance is not None` 时将 `instance` 传递给第一形参，而在 `instance is None` 时传递类，同时支持 `pm.classify(...)`、`PortfolioManager.classify(...)` 与 `classify_fund_asset_class(...)` 三种调用方式，且恢复对 `self.holdings` 的查询；
3. 基于观测中非核心池标的在静态字典均未登记且 `data_loader.get_fund_metadata` 导入失败，将 `resolve_fund_meta` 纳入反查备选链能够保证冷门或非标存量标的自动解析出官方名称；
4. 基于观测中 9 大测试标的均在规则中命中且测试通过，9 大资产分类规则已成熟可用；
5. 基于观测中 `_export_state_dict` / `_import_state_dict` 未导出快照，补齐快照字段可确保持久化与 Undo 回滚不丢失影子基准；
6. 基于观测中 `FundHolding.market_value` 静态赋值机制，在 `evaluate_rebalance_audit` 内部首先调用 `_recalculate_totals()`，可物理保证外部修改 `current_nav` 时实盘资产与影子资产 100% 同步联动。

## 3. Caveats
- 外部盘中实时行情接口 `fetch_realtime_fund_quote` 依赖东方财富/新浪行情网络。当网络完全断开时，未在字典内的孤立代码将退回本地离线已知净值表（第 2218 行 `known_navs`）与规则兜底。
- C 类份额免赎回费天数标准按公募普遍规则设为 30 天，若有个别特殊基金为 7 天免赎回费，统一遵循“7~29天计提 0.50% 缓卖省下费率”的保守风控口径。

## 4. Conclusion
1. `classify_fund_asset_class` 需升级为混合描述符模式，打通 `self.holdings` 访问，并在反查链中融合 `resolve_fund_meta`；
2. 9 大资产标准映射规则（R2）已完备有效，无一漏网进入“其他权益资产”；
3. `initial_baseline_snapshot` 需在 `_export_state_dict` 与 `_import_state_dict` 中建立持久化映射；
4. `evaluate_rebalance_audit`（R5）数学公式模型完整，入口加入 `self._recalculate_totals()` 即可确保与 `current_nav` 实时动态联动；
5. 详细方案与修改代码块已固化在 `survey_pm.md` 中。

## 5. Verification Method
- **针对性专项测试**：
  ```powershell
  py -3 -m pytest tests/test_adv_final_closure.py -v -k "test_specialized_1 or test_specialized_2"
  ```
- **防作弊全量资产覆盖测试**：
  ```powershell
  py -3 -m pytest tests/test_anticheat_suite.py -v -k "test_classify_fund_asset_class_zero_percent_other_equity"
  ```
- **关键文件与行号核查**：
  检查 `AGY2_FundAdvisory/portfolio_manager.py` 第 4647~4774 行分类器与第 6267 行调仓复盘审计函数。
- **失效判定条件**：
  若 9 只测试标的任一返回“其他权益资产”，或修改 `current_nav` 后 `audit["current_actual_equity"]` 与 `audit["shadow_hold_equity"]` 未同步变动，则判定验证失败。
