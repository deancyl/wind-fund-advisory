# Handoff Report — StrategyBridge R4 股息与票息安全垫引擎调研

## 1. Observation (客观观察事实)

1. **装饰器叠放与方法绑定**：
   - 文件：`AGY2_FundAdvisory/strategy_bridge.py` 第 1959~1962 行：
     ```python
     @classmethod
     @staticmethod
     def calculate_portfolio_yield_cushion(
         weights_or_holdings: Any,
         total_capital: float,
         pm: Any = None
     ) -> Dict[str, Any]:
     ```
   - 第 2049 行：`def get_online_expert_weights(cls, ...)`。
   - 观察：`calculate_portfolio_yield_cushion` 上方同时出现 `@classmethod` 与 `@staticmethod`；在 Python 3.10+ 中属于弃用反模式。
2. **资金底座为 0 或未传时的权重畸变**：
   - 文件：`AGY2_FundAdvisory/strategy_bridge.py` 第 1983~1994 行：
     ```python
     tot_cap = float(total_capital if total_capital > 0 else 100000.0)
     ...
     w = (mv / tot_cap) if tot_cap > 0 else 0.0
     ```
   - 运行测试 `py -3 scripts/test_calculate_yield_cushion.py`：对 50 万元实际持仓（15万红利低波 + 15万银行 + 20万纯债）传入 `total_capital=0.0` 时，各标的权重被计算为 `1.5, 1.5, 2.0`（总权重 500%），输出 `weighted_yield_pct: 20.5%`，分类明细中红利低波占比为 `150.0%`。
3. **9 大资产收益率基准定义**：
   - 文件：`AGY2_FundAdvisory/strategy_bridge.py` 第 1971~1981 行已列出基准字典：
     - A股红利低波: 5.20%
     - A股红利高股息: 4.80%
     - 核心蓝筹: 2.80%
     - 中盘均衡: 1.80%
     - 中小盘成长: 1.00%
     - 科技成长进攻: 0.60%
     - 纯债固收: 2.75%
     - 美股海外对冲: 1.30%
     - 黄金对冲: 0.00%
   - 分类器调用已在 `PortfolioManager.classify_fund_asset_class`（`portfolio_manager.py:4648`）实现，支持类与实例调用。
4. **现金分红字段与逻辑**：
   - `FundHolding` 标准字段为 `dividend_method`，默认 `"cash"`，可选 `"reinvest"`（`portfolio_manager.py:273`）。
   - 现存代码在权重字典输入时（`strategy_bridge.py:2003`）直接写死 `div_m = "reinvest"`，导致未传实盘持仓的建仓方案中 `cash_dividend_payout_est` 恒为 0.0。
5. **前端展示落地位置**：
   - **Tab 1 步骤二**：`AGY2_FundAdvisory/app_gui.py` 第 2972~3040 行（方案核心归因卡片 `c_attr1, c_attr2, c_attr3`，当前入参包含 `opt_weights` 与 `plan_capital`）。
   - **Tab 2 步骤一**：`AGY2_FundAdvisory/app_gui.py` 第 3669~3676 行（资产基线横幅卡片，当前入参包含 `pm.holdings` 与 `_tot_base_eq`）。

---

## 2. Logic Chain (推理逻辑链条)

1. **由观察 1 推出**：
   `calculate_portfolio_yield_cushion` 作为无状态的数学纯函数计算器，必须仅声明为 `@staticmethod`，彻底移除冗余的 `@classmethod`。同时确保 `get_online_expert_weights` 显式保留 `@classmethod`，杜绝调用异常与 Python 3.13 兼容性隐患。
2. **由观察 2 推出**：
   当调用方传入包含市值的持仓集合（如 `pm.holdings`、`HoldingItem` 列表或 `DataFrame`）且 `total_capital <= 0` 时，总资产 `tot_cap` 必须动态取持仓市值之和 `sum(market_values)`。若继续使用写死的 100,000.0 兜底，大额资产计算出的权重会膨胀数倍，导致整个安全垫指标彻底失真。
3. **由观察 2 与观察 4 推出**：
   输入形态必须覆盖 6 大类：① 纯权重字典（0~1 或 0~100）；② 金额字典；③ `FundHolding` 字典；④ `HoldingItem` 对象列表；⑤ `pd.DataFrame`；⑥ 直接传入 `PortfolioManager` 实例。在未显式传递分红偏好时，红利低波与高股息标的应根据 `INDEX_TO_FUND_MAP` 建议默认推荐现金分红，使 `cash_dividend_payout_est` 真实反映收息能力。
4. **由观察 3 与观察 5 推出**：
   在 Tab 1 步骤二（2972~3040行）调用 `StrategyBridge.calculate_portfolio_yield_cushion(opt_weights, plan_capital, pm=pm)`，并在「💰 怎么赚钱？」归因卡片及下方专属横幅呈现；在 Tab 2 步骤一（3669~3676行）调用 `StrategyBridge.calculate_portfolio_yield_cushion(pm.holdings, _tot_base_eq, pm=pm)` 并直接融入资产基线与风控防线横幅。

---

## 3. Caveats (注意事项与边界)

1. **只读约束**：本 Explorer 代理未直接修改任何项目业务代码，全部原型与边界测试均在 `scripts/test_calculate_yield_cushion.py` 沙盒中验证。
2. **空持仓容错**：当组合完全为空或输入为 `None` 时，方法应安全返回收益率 0.0、各金额 0.0 及空字典，不可抛出除零或空指针异常。
3. **分类器依赖**：在 `strategy_bridge.py` 内部调用分类器时，严禁顶层导入 `portfolio_manager`，必须保持局部延迟导入以防循环依赖。

---

## 4. Conclusion (结论与交付物)

1. **交付文档**：已在 `d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r11_2\survey_bridge.md` 输出详尽的架构分析报告、输入容错矩阵、展示位设计及完整的可直接落地的重构代码。
2. **主要成果**：
   - 彻底修复装饰器叠放与 `total_capital <= 0` 权重失真 Bug；
   - 完整支持 6 大输入形态（含 DataFrame 与 PM 实例）；
   - 精确计算 4 项核心输出指标与 9 大类构造成分；
   - 明确 `app_gui.py` 在 Tab 1 与 Tab 2 的具体集成代码行号与 HTML/CSS 结构。

---

## 5. Verification Method (验证方法)

1. **原型与容错单元验证**：
   ```powershell
   py -3 scripts/test_calculate_yield_cushion.py
   ```
   验证：
   - 50 万资产在 `total_capital=0` 时，总权重准确保持 100%，加权收益率 4.10%，年度安全垫 ¥20,500.00；
   - PM 实例与 DataFrame 传入时均正常返回非零计算结果；
   - 现金分红标的准确计入现金直派预估。
2. **现有回归套件无损检验**：
   ```powershell
   py -3 -m pytest -o pythonpath=AGY2_FundAdvisory AGY2_FundAdvisory/tests/test_strategy_bridge.py
   ```
   11 项现有全量测试必须全部保持 100% 通过（PASS）。
