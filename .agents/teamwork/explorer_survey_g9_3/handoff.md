# G9 世代 Brinson 归因、Tab 2 运维工具坞联动与测试基线法证调研报告

## 摘要 (Executive Summary)
本报告为 G9 世代金融量化投顾系统升级提供深度调研法证。重点审计了 `PortfolioManager.evaluate_rebalance_audit` 归因逻辑、Tab 2 账本运维复盘档案联动机制、四大只读裁判与契约文件（`judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py` 及 `DataLoader.simulate_execution`），以及全套自动化回归测试套件。当前 50 项基线测试全部 100% 通过（耗时约 88s），只读裁判文件零修改。针对 Brinson 三维超额归因（大类配置、优选选基、摩擦规避）以及 G9 新增量化风控需求，给出了精确的数学推导、数据结构契约与端到端改造方案。

---

## 1. 观察 (Observation)

### 1.1 `PortfolioManager.evaluate_rebalance_audit` 现状调查
- **文件位置**：`d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py` 第 6671 至 6729 行。
- **现有实现代码观察**：
  ```python
  6671:     def evaluate_rebalance_audit(self) -> Dict[str, Any]:
  6680:         cur_actual = float(self.total_equity or 0.0)
  6683:         snap = getattr(self, "initial_baseline_snapshot", None)
  6684:         if not snap or not snap.get("holdings"):
  6685:             init_h = {c: float(h.shares) for c, h in self.holdings.items()}
  6686:             init_c = float(self.available_cash)
  6687:             snap = {
  6688:                 "holdings": init_h,
  6689:                 "initial_cash": init_c,
  6690:                 "baseline_equity": cur_actual if cur_actual > 0 else 100000.0,
  6691:                 "date": getattr(self, "baseline_date", datetime.now().strftime("%Y-%m-%d"))
  6692:             }
  6693:             self.initial_baseline_snapshot = snap
  6695:         init_holdings = snap.get("holdings", {})
  6696:         init_cash = float(snap.get("initial_cash", 0.0))
  6699:         shadow_equity = init_cash
  6700:         for c, sh in init_holdings.items():
  6701:             if c in self.holdings:
  6702:                 nav = float(self.holdings[c].current_nav or 1.0)
  6703:             else:
  6704:                 meta = self.resolve_fund_meta(c)
  6705:                 nav = float(meta.get("current_nav", 1.0) or 1.0)
  6706:             shadow_equity += sh * nav
  6708:         rebal_val_add = round(cur_actual - shadow_equity, 2)
  6709:         rebal_val_add_pct = round((rebal_val_add / shadow_equity * 100.0), 2) if shadow_equity > 0 else 0.0
  6712:         saved_fees = 0.0
  6713:         for c, h in self.holdings.items():
  6714:             for b in (h.batches or []):
  6715:                 if getattr(b, "safety_lock", False) or getattr(b, "holding_days", 30) < 7:
  6716:                     saved_fees += float(b.shares) * float(h.current_nav or 1.0) * 0.0150
  6717:             if h.share_class == "C" and 7 <= getattr(h, "holding_days", 30) < 30:
  6718:                 saved_fees += float(h.market_value) * 0.0050
  6720:         return {
  6721:             "current_actual_equity": round(cur_actual, 2),
  6722:             "shadow_hold_equity": round(shadow_equity, 2),
  6723:             "rebalance_value_add": rebal_val_add,
  6724:             "rebalance_value_add_pct": rebal_val_add_pct,
  6725:             "saved_penalty_and_buffer_fees": round(saved_fees, 2),
  6726:             "baseline_date": snap.get("date", getattr(self, "baseline_date", "2026-11-06")),
  6727:             "shadow_holdings_count": len(init_holdings)
  6728:         }
  ```
- **关键缺陷与遗漏**：
  1. **缺少 Brinson 多资产归因模型**：仅计算了总差额 `rebalance_value_add = cur_actual - shadow_equity`，完全没有拆解大类资产配置效应（Allocation Effect）与优选基金超额效应（Selection Effect）。
  2. **基线快照持久化丢失**：`_export_state_dict`（第 3478 至 3513 行）与 `_import_state_dict`（第 3515 至 3540 行）均未序列化保存 `initial_baseline_snapshot`。服务重启或重新载入账本后，首度调用会使用当前已调仓后的持仓覆盖初始基线，导致历史复盘账单被抹平清零。
  3. **现有测试契约**：`tests/test_adv_final_closure.py`（第 85 至 131 行）严格断言了上述 7 个返回字段的键名与类型，因此改造必须保证 100% 向下兼容。

### 1.2 现有资产大类分类器能力
- **文件位置**：`portfolio_manager.py` 第 5185 至 5298 行。
- **观察**：
  系统已内置成熟的 9 大标准大类分类器 `PortfolioManager.classify_fund_asset_class`（缓存于 `_CLASSIFY_ASSET_CLASS_CACHE`）：
  1. `纯债固收`
  2. `黄金对冲`
  3. `美股海外对冲`
  4. `A股红利低波`
  5. `A股红利高股息`
  6. `科技成长进攻`
  7. `中小盘成长`
  8. `中盘均衡`
  9. `核心蓝筹`
  以及针对现金管理自动映射为 `现金管理`。分类器具有穿透基金代码与中文名称的完整字典映射规则，完全满足 Brinson-Fachler 归因的行业/大类切分需求。

### 1.3 Tab 2 账本运维复盘档案与前端渲染现状
- **文件位置**：`d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py` 第 5700 至 5935 行。
- **观察**：
  - Tab 2 顶部已实装双视图模式（主流程 vs 独立宽屏工具坞）。
  - 工具坞第 3 个子 Tab `dock_tab3` 为 `🗄️ 账本环境与实盘档案`（第 5840 行）。
  - 在第 5891 至 5931 行，调用 `audit_res = pm.evaluate_rebalance_audit()`，并在 `col_aud1, col_aud2, col_aud3` 中渲染了 3 张基础卡片：
    - `实盘总资产 vs 影子组合`
    - `主动调仓净增厚 (Alpha)`
    - `AI 风控规避损失与损耗`
  - 缺乏：
    - Brinson 三维归因卡片（配置效应、选基效应、摩擦规避）；
    - 多大类配置明细展开表（各分类实盘权重 vs 基准权重、收益率、配置贡献、选基贡献）；
    - 投顾级文字穿透复盘点评。

### 1.4 测试套件基线与只读裁判文件审计结果
- **执行命令与结果**：
  1. `py -3.11 -m pytest tests/test_infra.py -v` -> **14 passed in 5.98s**
  2. `py -3.11 -m pytest tests/test_adv_final_closure.py -v` -> **14 passed in 31.01s**
  3. `py -3.11 -m pytest tests/test_g3_evolution_loop.py -v` -> **12 passed in 17.02s**
  4. `py -3.11 -m pytest tests/test_gui_multi_ledger_stress.py -v` -> **10 passed in 34.14s**
  - **总计**：现有 50 项回归测试 100% 通过（0 失败），耗时约 88 秒。
- **四大只读裁判文件状态核查**：
  1. `AGY2_FundAdvisory/judge_engine.py` (844 行)：未修改，包含因果探针（浮点 1e-7）、AST 日历反作弊、6 风格切片回归、参数扰动爆破。
  2. `AGY2_FundAdvisory/holdout_vault.py` (162 行)：未修改，盲测切片 `2025-07-01` 至今，上限 3 次，熔断锁完好。
  3. `AGY2_FundAdvisory/AGENT_SPEC.md` (110 行)：未修改，定义了严禁未来函数、T+1 确认、7天 1.5% 惩罚费、Rf 2.0% 扣除等神圣契约。
  4. `tests/test_infra.py` (251 行)：未修改，覆盖底层裁判与执行算子自动化测试。
- **`DataLoader.simulate_execution` 契约核查**：
  - 文件：`AGY2_FundAdvisory/data_loader.py` 第 1364 至 1480 行。
  - 函数签名：`simulate_execution(weights_df, prices_df, is_otc=True, penalty_days=7, penalty_rate=0.015, etf_impact=0.001)` 严格保持默认参数与 T+1 及阶梯扣费逻辑不变。

### 1.5 其他待整改量化点代码定位
- `OnlineHeuristicFactorEvolver._evaluate_population`：`advisory_engine.py` 第 426 行 `R_p = np.sum(P * R[:, :, None], axis=1)` 存在同日收盘特征乘同日收益率未来函数，第 444 行计算夏普时未扣除无风险利率 `0.02 / 250.0`。
- `OnlineHeuristicFactorEvolver.get_60d_rolling_nav_and_trajectory`：`advisory_engine.py` 第 577 行使用 `lam = (t + 1) / 60.0` 伪造线性轨迹。
- `ActiveRiskSentry.inspect_portfolio`：`advisory_engine.py` 第 1429、1431、1436 行存在 `aum = 2.5` 假规模兜底，且缺失投资者适当性（C1-C5）持仓越界检查。

---

## 2. 逻辑链 (Logic Chain)

### 2.1 从业务目标到 Brinson 归因数学模型
1. **对比基准界定**：
   实盘主动复盘的目标是量化“主动调仓相比躺平不调仓产生了多少净增厚”。因此基准组合（Benchmark）正是持有接管首日初始份额不变的影子组合（Shadow Portfolio）。
2. **Brinson-Fachler 经典模型映射**：
   - 设全组合划分至 $K$ 个资产大类（9 大标准类 + 现金管理）。
   - 实际组合总资产 $V_P = \sum_k V_{P,k}$，大类权重 $w_{P,k} = V_{P,k} / V_P$。
   - 影子基准总资产 $V_B = \sum_k V_{B,k}$，大类权重 $w_{B,k} = V_{B,k} / V_B$。
   - 各大类区间收益率：基准收益率 $R_{B,k} = (V_{B,k} - V_{0,B,k}) / V_{0,B,k}$，全基准收益率 $R_B = (V_B - V_0) / V_0$；实盘收益率 $R_{P,k} = (V_{P,k} - V_{0,P,k}) / V_{0,P,k}$，全组合收益率 $R_P = (V_P - V_0) / V_0$。
3. **效应拆解公式**：
   - **大类资产配置效应 (Allocation Effect)**：
     $$AR_k = (w_{P,k} - w_{B,k}) \times (R_{B,k} - R_B)$$
     $$AR = \sum_k AR_k, \quad \Delta V_{\text{alloc}} = AR \times V_B$$
     解释：买方投顾通过调仓超配高收益大类或低配弱势大类所获得的资产配置超额。
   - **优选基金超额效应 (Selection Effect)**：
     $$SR_k = w_{P,k} \times (R_{P,k} - R_{B,k})$$
     $$SR = \sum_k SR_k, \quad \Delta V_{\text{select}} = SR \times V_B$$
     解释：在同一大类内部，精选基金战胜该大类基准的阿尔法贡献（含交互效应）。
   - **数学恒等式自洽性保证**：
     $$AR + SR = \sum_k \left[ (w_{P,k} - w_{B,k})(R_{B,k} - R_B) + w_{P,k}(R_{P,k} - R_{B,k}) \right]$$
     展开后交叉项精准抵消，严格得出：
     $$AR + SR = \sum_k w_{P,k} R_{P,k} - \sum_k w_{B,k} R_{B,k} = R_P - R_B = \Delta R$$
     因此：$(\Delta V_{\text{alloc}} + \Delta V_{\text{select}}) \equiv \Delta V_{\text{gross}}$，在浮点精度 $10^{-6}$ 内绝对勾稽平账！
   - **交易摩擦及惩罚费规避贡献 (Friction Saving)**：
     $$FS = \text{saved\_penalty\_and\_buffer\_fees}$$
     包括 7 天内赎回硬拦截保住的 1.50% 巨额惩罚扣款，以及 C 类临期保护省下的阶梯赎回费。这是买方投顾风控守底线为客户保住的真金白银。

### 2.2 数据结构设计契约
在 `evaluate_rebalance_audit` 的返回字典中注入结构化归因对象，保持原有顶级键不变：
```python
{
    # ─── 保持向下兼容的已有字段 ───
    "current_actual_equity": 116000.0,
    "shadow_hold_equity": 120000.0,
    "rebalance_value_add": -4000.0,
    "rebalance_value_add_pct": -3.33,
    "saved_penalty_and_buffer_fees": 1250.0,
    "baseline_date": "2026-11-06",
    "shadow_holdings_count": 4,

    # ─── G9 新增 Brinson 归因账单 ───
    "brinson_attribution": {
        "allocation_effect_yuan": -4000.0,
        "allocation_effect_pct": -3.33,
        "selection_effect_yuan": 0.0,
        "selection_effect_pct": 0.0,
        "friction_saving_yuan": 1250.0,
        "friction_saving_pct": 1.04,
        "total_active_add_yuan": -4000.0,
        "total_active_add_pct": -3.33,
        "primary_driver": "大类资产配置效应",
        "category_breakdown": [
            {
                "category": "美股海外对冲",
                "portfolio_weight_pct": 17.24,
                "benchmark_weight_pct": 33.33,
                "weight_diff_pct": -16.09,
                "portfolio_return_pct": 25.0,
                "benchmark_return_pct": 25.0,
                "allocation_effect_yuan": -4000.0,
                "allocation_effect_pct": -3.33,
                "selection_effect_yuan": 0.0,
                "selection_effect_pct": 0.0,
                "total_effect_yuan": -4000.0
            },
            ...
        ]
    }
}
```

### 2.3 Tab 2 前端界面联动方案
在 `app_gui.py` 的 `dock_tab3` 中（第 5891 行买方投顾复盘账单）：
1. **三维归因核心卡片**：
   - 卡片 1：🏛️ 大类资产配置效应 (Allocation Effect)
   - 卡片 2：🎯 优选基金超额效应 (Selection Effect)
   - 卡片 3：🛡️ 交易摩擦及惩罚规避 (Friction Saving)
2. **多大类归因明细表**：
   使用 `st.dataframe(pd.DataFrame(category_breakdown))` 展示各资产类别的权重偏离、收益率及贡献额，支持排序与自适应宽度。
3. **投顾穿透复盘点评**：
   根据收益主导项（配置效应主导 vs 选基效应主导）自动生成买方投顾专业话术，告知客户当前超额驱动力与规避惩罚费成绩。
4. **HTML 安全与格式防御**：
   严格收口至 `safe_markdown_html`，返回值强制包裹 `_clean_html`，卡片增加 `min-height` 与 `overflow: visible`，完美防御 CommonMark 4+ 空格缩进代码块缺陷（规则 14、15、27）。

---

## 3. 局限与前提假设 (Caveats)

1. **历史净值缺失处理**：若某存量基金在初始基线日之后被调入、或缺少基线日历史净值，以该基金第一笔买入批次的 `cost_price` 作为基线成本净值，确保基线收益率计算不报 `ZeroDivisionError`。
2. **无外部出入金假设**：当前影子组合建立在无外部大额增量出入金的接管期内。若发生增量入金，`rebalance_value_add` 会按净资产增量折算；为保证严谨性，建议在后续版本中引入时间加权收益率 (TWRR) 影子现金流校准。
3. **只读文件保护原则**：四大只读裁判文件与 `simulate_execution` 签名严禁触碰，所有新测试必须单独写入新建的测试文件 `tests/test_g9_causal_brinson_and_suitability.py`。

---

## 4. 结论与技术实施方案 (Conclusion & Implementation Blueprint)

### 4.1 代码修改清单与精准定位

| 模块文件 | 修改位置 | 核心改造要点 |
| :--- | :--- | :--- |
| `AGY2_FundAdvisory/portfolio_manager.py` | 第 3478-3540 行 | 在 `_export_state_dict` 与 `_import_state_dict` 中持久化 `initial_baseline_snapshot`，解决重启丢失基线缺陷。 |
| `AGY2_FundAdvisory/portfolio_manager.py` | 第 6671-6729 行 | 重构 `evaluate_rebalance_audit`：调用 `classify_fund_asset_class`，按 Brinson-Fachler 算法精算大类配置效应、选基效应及摩擦规避，输出自洽的三维归因数据结构。 |
| `AGY2_FundAdvisory/app_gui.py` | 第 5891-5931 行 | 在 `dock_tab3` 账单区域增加 Brinson 三维归因卡片、多大类资产归因明细表及买方投顾复盘点评文案。 |
| `AGY2_FundAdvisory/advisory_engine.py` | 第 420-447 行 | 根除同日未来函数（$P[t]$ 滞后一期作用于 $R[t+1]$）、从夏普日均收益率中扣除 $0.02/250.0$ 无风险利率、计提单边 10 bps 换手摩擦。 |
| `AGY2_FundAdvisory/advisory_engine.py` | 第 570-605 行 | 废除 `lam = (t + 1)/60.0` 线性插值，改为真实的 5 日步长推进式样本外演化轨迹 (Walk-Forward Trajectory)。 |
| `AGY2_FundAdvisory/advisory_engine.py` | 第 340 行 | 废除缺失数据时的 `np.linspace(1.0, 1.05)` 线性上涨直线假数据，改为收益率置 0 并标记缺失。 |
| `AGY2_FundAdvisory/advisory_engine.py` | 第 1420-1437 行 | 废除 `aum = 2.5` 默认规模，实装从元数据与底层字典穿透反查真实规模，查无数据标记待核验。 |
| `AGY2_FundAdvisory/advisory_engine.py` | 第 1450-1530 行 | 新增投资者适当性（C1-C5）持仓权益占比与波动率超限巡检，以及盘中估值异动对安全垫的传导预警。 |
| `tests/test_g9_causal_brinson_and_suitability.py` | 新建测试文件 | 全面覆盖 G9 新特性的 5 大专项自动化测试，确保 100% 通过。 |

### 4.2 G9 专项测试套件规划 (`tests/test_g9_causal_brinson_and_suitability.py`)

1. **测试用例 1：`test_g9_factor_evolver_anti_lookahead_and_causal_probe`**
   - 验证 $P[t]$ 作用于 $R[t+1]$（`P[:-1] * R[1:]`），杜绝偷看当日答案；
   - 验证动态净值计算扣除了换手摩擦成本；
   - 验证 60 日演化轨迹非线性插值伪造。
2. **测试用例 2：`test_g9_sharpe_deducts_risk_free_rate`**
   - 验证夏普比率严格扣除 2.0% 年化无风险利率（日均收益减 $0.02/250.0$）；
   - 验证纯债低波资产无法凭微小波动刷出虚假高夏普。
3. **测试用例 3：`test_g9_active_risk_sentry_real_aum_lookthrough_and_alert`**
   - 验证移除 `else: aum = 2.5` 假数据；
   - 验证从 `DataLoader.get_fund_metadata` 穿透反查真实规模；
   - 验证未知规模输出待核验告警，迷你基 (<0.5亿) 输出清盘风险红灯。
4. **测试用例 4：`test_g9_investor_suitability_boundary_alert_and_intraday_shock`**
   - 验证 C1 保守型客户高配权益基金触发适当性超配预警；
   - 验证提供一键降波纠偏动作；
   - 验证盘中异动对安全垫的消耗传导测算。
5. **测试用例 5：`test_g9_brinson_attribution_exact_decomposition_and_ui_linkage`**
   - 验证 `evaluate_rebalance_audit` 包含 `brinson_attribution` 完整三维拆解；
   - 验证数学恒等式 $\text{Allocation} + \text{Selection} \equiv \text{Gross Active Add}$；
   - 验证规避惩罚费金额与批次锁定状态对齐；
   - 验证原有 7 个顶级键向下兼容性；
   - 验证 `app_gui.py` 前端渲染安全与无异常。

---

## 5. 独立验证方法 (Verification Method)

后续执行代理或审计人员可直接运行以下命令独立复现并验证本报告的所有结论：

### 5.1 运行既有测试套件基线验证
```powershell
py -3.11 -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py -v
```
**期望结果**：50 项测试 100% PASSED，总耗时约 85~90 秒。

### 5.2 验证四大只读裁判文件未被篡改
```powershell
git diff --stat AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md tests/test_infra.py
```
**期望结果**：输出为空，确认只读裁判文件物理零改动。

### 5.3 验证 `DataLoader.simulate_execution` 契约未被破坏
检查 `AGY2_FundAdvisory/data_loader.py` 第 1364 至 1371 行，确认参数列表及默认值：
`simulate_execution(weights_df, prices_df, is_otc=True, penalty_days=7, penalty_rate=0.015, etf_impact=0.001)` 零改动。

### 5.4 G9 新增测试验证（实现后执行）
```powershell
py -3.11 -m pytest tests/test_g9_causal_brinson_and_suitability.py -v
```
**期望结果**：5 个新增专项测试全部通过。
