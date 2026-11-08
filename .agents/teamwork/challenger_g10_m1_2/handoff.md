# 蒙特卡洛压力测试实证对抗检验报告 (handoff.md)

**执行智能体**: `challenger_g10_m1_2` (teamwork_challenger / critic & specialist)  
**被检验方**: `worker_g10_m1` (teamwork_worker)  
**上级调度方 (Caller)**: `22f2ddb7-c220-44ca-b889-a5c0901cc3b3` (orchestrator_11)  
**时间戳**: 2026-11-08T04:16:00Z  
**最终裁决 (Verdict)**: **REJECT (不予通过，存在阻断性缺陷)**

---

## 1. 事实观察 (Observation)

### 1.1 实证压测通过项观察 (Passing Items)
运行实证测试脚本 `py -3 scripts/verify_cvar_stress_testing.py`：
1. **极值风险统计公理验证**：
   在测试的 6 类代表性组合（高权益成长、核心均衡、稳健偏债、纯科创50、纯债、纯黄金）及 C1 至 C5 全评级矩阵下，90 项情景检验 100% 满足数学公理：
   $$CVaR_{99\%} \ge VaR_{99\%} \ge VaR_{95\%}$$
   且 $Pred\_MDD \ge VaR_{95\%}$，流动性折价损失累加 $Total\_CVaR_{99\%} \ge CVaR_{99\%}$ 恒成立。
2. **历史情景区分度与真实性验证**：
   - 2008 年金融危机在权益组合上产生最深最大回撤：高权益成长 75.74%、核心均衡 39.44%、纯科创50 78.50%；
   - 2015 年去杠杆流动性踩踏在各组合上产生最长变现天数：高权益成长 5.6 天、核心均衡 3.1 天、纯科创50 6.4 天，显著长于 2008 年与 2024 年；
   - 2024 年小盘股危机展现结构性分化：高波科技成长回撤 26.79%，而红利低波与纯债呈现避险防守韧性。
3. **ADV 承接力容量递增验证**：
   随着订单规模从 1 万元放大至 500 亿元（突破重仓股 5% ADV 门槛），华夏科创50变现天数从 5.0 天递增至 28.0 天，非线性流动性冲击生效。
4. **投资者适当性门禁验证**：
   中等权益组合（50% 红利低波 + 30% 纯债 + 20% 黄金）在 2008 情景下回撤为 25.80%：
   - 保守型 C1（容忍度 5.0%）触发 `exceeds_risk_tolerance = True`；
   - 进取型 C5（容忍度 40.0%）判定为 `exceeds_risk_tolerance = False`（合规安全）。

### 1.2 发现的致命代码与金融逻辑缺陷 (Critical Defects Observed)

#### 缺陷 1：字典与实盘持仓输入下 FIFO 7天安全锁完全失效 (t_lock 恒等于 0)
- **代码位置**: `AGY2_FundAdvisory/portfolio_manager.py:8677` 与 `8687`：
  ```python
  8677: hd = int(getattr(v, "holding_days", 30) or (v.get("holding_days", 30) if isinstance(v, dict) else 30))
  ...
  8687: hd = int(getattr(item, "holding_days", 30) or (item.get("holding_days", 30) if isinstance(item, dict) else 30))
  ```
- **实证运行与复现结果**:
  运行 `py -3 scripts/verify_cvar_stress_testing.py`：
  ```
  [CHECK 5] ADVERSARIAL TEST: FIFO 7-Day Lock Penalty Defense...
    Dict input (holding_days=2): liquidation_days=2.8
    Dict input (holding_days=30): liquidation_days=2.8
    Dict difference: 0.0 days (expected 5.0 days penalty)
    -> FAIL: simulate_portfolio_cvar_bootstrap fails to account for FIFO locks when holdings are passed as dicts! Got diff=0.0 days instead of 5.0 days.
  ```
  以及使用真实 `PortfolioManager` 持仓运行 `pm.simulate_portfolio_cvar_bootstrap_instance()`：
  ```
    PM instance (holding_days=2 in batch): liquidation_days=2.8
    PM instance (holding_days=30 in batch): liquidation_days=2.8
    PM instance difference: 0.0 days (expected 5.0 days penalty)
    -> FAIL: simulate_portfolio_cvar_bootstrap_instance fails to account for FIFO locks in real FundHolding batches! Got diff=0.0 days instead of 5.0 days.
  ```
- **机理分析**:
  1. 当 `v` 为字典时（如 `{"market_value": 100000.0, "holding_days": 2}`），Python 的 `getattr(v, "holding_days", 30)` 查找的是字典对象的属性，字典本身无 `holding_days` 属性，因此直接返回第 3 个形参默认值 `30`；
  2. 表达式 `30 or (...)` 中，`30` 为真值 (truthy)，Python 触发短路求值，**完全不执行后半段的 `v.get("holding_days", 30)`**，导致 `hd` 永远被短路赋值为 `30`；
  3. 当 `v` 为实盘持仓 `FundHolding` 实例时，`FundHolding`（定义于 261-281 行）本身没有 `holding_days` 属性（其实际持有天数存放在批次 `v.batches[i].holding_days` 中）。因此 `getattr(v, "holding_days", 30)` 同样返回默认值 `30`；
  4. 结果导致：第 8825 行 `t_lock = max(0, 7 - hd) if hd < 7 else 0` 永远为 `0`！无论是刚买入 0 天、2 天的新份额，全部被判定为无惩罚期满期份额，**彻底击穿 GEMINI.md 第 7 条铁律与 R4 变现天数约束**！

#### 缺陷 2：通过 pm_instance 默认调用时触发未捕获崩溃 AttributeError
- **代码位置**: `AGY2_FundAdvisory/portfolio_manager.py:8697`：
  ```python
  8692: elif pm_instance and hasattr(pm_instance, "holdings") and pm_instance.holdings:
  8693:     tot = sum(h.market_value for h in pm_instance.holdings.values())
  8694:     for c, h in pm_instance.holdings.items():
  8695:         w = (h.market_value / tot) if tot > 0 else (1.0 / len(pm_instance.holdings))
  8696:         norm_w[str(c)] = w
  8697:         items_detail.append({"code": str(c), "name": h.fund_name, "market_value": h.market_value, "holding_days": h.holding_days, "weight": w})
  ```
- **实证运行与复现结果**:
  运行 `PortfolioManager.simulate_portfolio_cvar_bootstrap(holdings=None, pm_instance=pm)`：
  ```
  AttributeError: 'FundHolding' object has no attribute 'holding_days'
  ```
- **机理分析**:
  `h` 是 `FundHolding` 类型，不存在 `holding_days` 属性。直接点号访问 `h.holding_days` 必定抛出 `AttributeError` 崩溃。

---

## 2. 逻辑论证链 (Logic Chain)

1. **前提 1 (任务契约)**：
   调度指令明确要求：“Verify liquidity liquidation days calculation is deterministic and accounts for FIFO locks and top 5 ADV.”
   工作区铁律 GEMINI.md 第 7 条明确规定：“持仓批次天数与先进先出安全赎回铁律：悲观天数防线必须使用悲观保守的 min((b.holding_days for b in batches), default=30) 或严格基于 FIFO 批次精确拆分；免惩罚份额硬约束守死 1.50% 惩罚费红线。”
2. **前提 2 (实证检验)**：
   依据 Observation 1.2，实测传入 `holding_days=2` 的字典或在账本中增补持有 2 天的新批次，计算出的变现天数均为 2.8 天，与持有 30 天的结果完全一致（差值为 0.0 天，而非预期的 5.0 天惩罚锁定天数）。
3. **推理与影响**:
   - `getattr(dict, "holding_days", 30)` 默认返回 30 导致布尔短路，属于 Python 语法级低级误用；
   - `FundHolding` 批次数据未穿透提取，导致实盘账本在前端渲染或后台计算压力测试变现天数时，对 $<7$ 天带有 1.50% 赎回惩罚费的高危在途/新买份额毫不知情，无法体现流动性锁定风险；
   - `holdings=None, pm_instance=pm` 调用路径存在必现未捕获 `AttributeError` 崩溃。
4. **结论**:
   虽然极值统计公理、历史情景区分度与 ADV 大额承接力推演表现优异，但流动性变现天数的 FIFO 惩罚锁属于实盘安全底线与验收硬指标，未达标前必须拒收。

---

## 3. 注意事项与边界说明 (Caveats)

1. **只读裁判文件安全确认**：
   经核对 `git status AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGENT_SPEC.md tests/test_infra.py`，四大裁判文件保持 100% 原始只读，无任何篡改。
2. **纯债资产日度波动率下界说明**：
   在 8858 行 `daily_vol = max(0.005, ...)` 设有 0.5% 日波幅下界，导致纯债在 2024 年正收益情况下仍测得 8.23% 的 60 日回撤，建议后续可对纯债固收资产使用真实日波幅（约 0.02%~0.05%）而非统一 0.5% 兜底。但这不影响本次主要判定。
3. **No other caveats**。

---

## 4. 交付结论 (Conclusion)

- **综合裁决**: **REJECT (拒绝交付，需 worker 修复后重新提交审查)**
- **必须整改项**:
  1. 修复 `portfolio_manager.py:8677` 与 `8687`：正确提取持有天数，优先从批次或字典提取：
     ```python
     if hasattr(v, "batches") and v.batches:
         hd = min(b.holding_days for b in v.batches)
     elif isinstance(v, dict):
         hd = int(v.get("holding_days", 30))
     elif hasattr(v, "holding_days"):
         hd = int(v.holding_days)
     else:
         hd = 30
     ```
  2. 修复 `FundHolding` 数据模型（261 行）或 `portfolio_manager.py:8697`：为 `FundHolding` 添加 `@property def holding_days(self)` 返回 `min((b.holding_days for b in self.batches), default=30)`，并在 8697 行安全读取，彻底杜绝 `AttributeError`。
  3. 在 `tests/test_g10_correlation_liquidity_and_stress.py` 中补充测试用例，断言持有天数 $< 7$ 的标的变现天数显著大于满期标的（增加 $7 - hd$ 天）。

---

## 5. 独立复现与验证方法 (Verification Method)

### 5.1 复现命令
在 Windows PowerShell 终端中执行对抗压测套件：
```powershell
py -3 scripts/verify_cvar_stress_testing.py
```

### 5.2 预期输出（修复后验收基准）
- `[CHECK 1] Testing Mathematical Risk Axioms across portfolios and risk tiers...` -> 全部 PASS
- `[CHECK 2] Testing Scenario Realism and Differentiation...` -> 全部 PASS
- `[CHECK 3] Testing Determinism and Top 5 ADV Capacity Scaling...` -> 全部 PASS
- `[CHECK 4] Testing Investor Risk Tolerance Gating (C1 vs C5)...` -> 全部 PASS
- `[CHECK 5] ADVERSARIAL TEST: FIFO 7-Day Lock Penalty Defense...` -> `diff_dict == 5.0` 且 `diff_pm == 5.0` PASS
- `[CHECK 6] ADVERSARIAL TEST: simulate_portfolio_cvar_bootstrap(holdings=None, pm_instance=pm)...` -> 零异常 PASS
- 脚本最终输出: `VERDICT: APPROVE (All empirical adversarial checks passed)` 且退出码为 `0`。
