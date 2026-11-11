# M1 里程碑交付报告：投顾备忘录 Bug 修复与首屏 1行5列横向情报矩阵重构

## 1. Observation (客观观测与证据记录)

本智能体按照 M1 里程碑契约与安全底线红线，针对独占所有权文件 `AGY2_FundAdvisory/advisory_engine.py` 与 `AGY2_FundAdvisory/app_gui.py` 开展了详尽实证与代码重构，直接观测到以下事实：

### 1.1 `advisory_engine.py` 中 `generate_chief_advisor_memo` 的历史缺陷
- **行号定位**：原函数定义位于 `AGY2_FundAdvisory/advisory_engine.py` 第 4170 至 4375 行。
- **原成本属性 Bug**：在第 4284 行代码：
  ```python
  cost_v = float(getattr(h, "cost_value", 0.0) or (h.get("cost_value", 0.0) if isinstance(h, dict) else 0.0))
  ```
  在系统真实对象 `FundHolding` / `HoldingItem`（定义于 `portfolio_manager.py:261-305`）及账本 JSON 中，总成本字段名为 `cost_basis`，单价为 `cost_price`，且计算了 `floating_pnl` 与 `floating_pnl_pct`，**根本不存在 `cost_value` 属性**。
  实测表明：在旧代码下直接传入 `combat_29_funds` 持仓，`cost_v` 永远读取为 `0.0`，导致 `pl_ratio` 恒为 `0.0`，`deep_loss_count` 恒为 `0`，真实账本中浮亏严重的 `011613` (-17.1%)、`100032` (-12.0%)、`161725` (-25.1%) 被 100% 漏检！
- **Tab 1 目标权重字典误判**：
  在 `app_gui.py:4080` 中，Tab 1 建仓方案传入 `holdings=opt_weights`（例如 `{"005561": 0.35, "002351": 0.20, ...}`）。
  旧代码遍历 `opt_weights.values()`，将权重浮点数 `0.35` 视为市值 `mv = 0.35 元`，落入 `0 < mv < 200.0` 区间，导致 6 只建仓标的全被计入碎片尾仓，合计报出“6只碎片尾仓合计 ¥1.00”的荒谬文案。
- **碎片判定未与 `ActiveRiskSentry` 对齐**：
  旧代码采用简单的 `0 < mv < 200.0`，导致腰部持仓 `#10 005827 易方达蓝筹精选混合`（市值 ¥124.14，A 类偏股混合）被错误计为碎片，总碎片数被虚高统计为 20 只。

### 1.2 `app_gui.py` 中 `render_chief_advisor_memo_card` 与首屏布局的遮蔽问题
- **原卡片布局**：在 `app_gui.py` 第 249~329 行，卡片 CSS 写死为单列纵向堆叠：
  ```html
  <div style="display: grid; grid-template-columns: 1fr; gap: 10px;">
  ```
  每个维度卡片高度达数百像素，整体垂直占用极大。
- **首屏默认折叠遮蔽**：在 `app_gui.py` 第 3186 行：
  ```python
  wing_expander = st.expander(f"{act_status_icon} {expander_title}", expanded=False)
  with wing_expander:
      ...
      render_chief_advisor_memo_card(memo_top, title="🧭 首席投顾五维全息决策备忘录")
  ```
  因处于 `expanded=False` 的折叠框内，用户打开首屏时备忘录处于完全不可见状态，必须手动点击折叠框。

---

## 2. Logic Chain (推理链条与修复推导)

1. **多字段兼容读取推导**：
   - 优先读取 `cost_basis`（真实 `FundHolding` 的成本总金额）；
   - 若 `cost_basis` 不存在或为 0，尝试 `cost_price * shares`（或 `cost_nav * shares`）；
   - 降级尝试 `cost_value`（确保旧 mock 桩类 100% 绿灯兼容）；
   - 同时支持直接读取 `floating_pnl_pct` 或 `pnl_pct`：若存在且非 0，直接换算为 `pl_ratio = float(raw_pnl_pct) / 100.0`；
   - 盈亏金额优先读取 `floating_pnl`，缺省回退至 `mv - cost_v`；
   - 对 `pl_ratio < -0.10` 的标的精确计入 `deep_loss_list`，按亏损金额由负大到负小排序，提取前三大出血点核心标的。
2. **Tab 1 目标权重字典防护推导**：
   - 检测 `isinstance(holdings, dict) and all(0.0 <= float(v) <= 1.0) and abs(sum(v) - 1.0) < 0.05`；
   - 命中时定性为“拟建仓资产组合结构校验”：计算总本金（支持 `total_capital` 入参，默认 10 万元）、攻防配比（纯债固收 vs 弹性进攻）以及单标的最大分散度；
   - 强制将 `deep_loss_count = 0`、`frag_count = 0`、`frag_amt = 0.0`，从根本上杜绝“6 只碎片合计 ¥1.00”的不良展示。
3. **19 只免赎碎片与 ¥442.70 严格对齐推导**：
   - 规则与 `ActiveRiskSentry` 维度 13 物理对齐：
     `is_tail = (0 < mv < 100.0) or (100.0 <= mv < 200.0 and (s_cls == 'C' or any(k in fname for k in ['联接', 'ETF', '指数', '红包', '体验', '尾仓', '碎片'])))`；
   - 免赎持有天数检查：C 类满 30 天，A 类满 365 天（未指定时缺省已满期）；
   - `005827 易方达蓝筹`（¥124.14，A 类，主动权益）不满足上述特征，精准排除；
   - 真实 29 基账本中的 19 只碎片尾仓（89.60 元至 0.59 元）全部为 `< 100` 元，精准计入，合计资金严格等于 **¥442.70**。
4. **中美利差与宏观因果叙事推导**：
   - 在国际与汇率面（`international_fx`）补充读取 `us_10y`（美债 10Y 收益率，默认 4.40%），与国内 10Y 国债（1.63%）做差，精算中美利差深度倒挂（约 -277 bp），强化跨境大类资产配置逻辑。
5. **首屏 1 行 5 列横向矩阵与提权推导**：
   - 将 `render_chief_advisor_memo_card` 移出 `with wing_expander:`，直接在第 3028 行 4 张全局指标卡之后、`wing_expander` 之前渲染，首屏无需任何点击即可直视全景投顾参谋；
   - 重构 CSS 为横向网格：`grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px; width: 100%;`；
   - 引入媒体查询 `@media (max-width: 768px)`，窄屏移动端自适应折行为 `repeat(auto-fit, minmax(180px, 1fr))`；
   - 每张子卡片顶部带鲜明色标（宏观蓝、国际紫、产业青、病灶红、行动绿），高度控制在 115px 左右，正文设置 `line-height: 1.45; overflow-y: auto; max-height: 85px;`；
   - 渲染统一经由 `safe_markdown_html(html_code)`，配合 `_clean_html()` 物理剥离首尾空格，彻底消除 CommonMark 4 个前导空格代码块泄露风险（严格遵循规则 27）。

---

## 3. Caveats (风险防范与边界假设)

1. **向后兼容性保护**：
   老旧测试桩（如 `MockFundHolding` 与 `DummyHolding`）仅含 `cost_value` 属性，我们在成本读取链中保留了对 `cost_value` 的降级解析，确保旧测试用例 100% 绿灯。
2. **只读裁判文件零改动**：
   全程未触碰四个只读裁判文件：`judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py`，未修改 `DataLoader.simulate_execution` 签名。
3. **后续里程碑衔接**：
   - M2 将在首屏最顶部挂载当前激活账本选择器与桌面/手机切换胶囊；
   - M3 将在 Tab 2 与 Tab 3 实装 29 基的三阶手术面板与时光机回测；
   - 本里程碑已为后续功能提供了完美平滑的数据底层与 UI 顶层占位。

---

## 4. Conclusion (实现结论)

1. `advisory_engine.py` 中的 `generate_chief_advisor_memo` 已完成实质性修复：
   - 彻底修复 `cost_value` 缺陷，多字段兼容读取成本与盈亏率；
   - 29 基账本实测报出 `deep_loss_count = 18 >= 3`，核心亏损拖累源准确点名 `011613` (-17.1%)、`100032` (-12.0%)、`161725` (-25.1%)；
   - 目标权重字典自适应切换为“拟建仓组合结构校验”，零碎片、零亏损报错，彻底消除“6 只碎片合计 ¥1.00”现象；
   - 碎片尾仓严格与 `ActiveRiskSentry` 对齐，锁定 19 只免赎碎片、金额精准平账至 ¥442.70；
   - 补充中美利差 (-277 bp) 与十维宏观叙事。
2. `app_gui.py` 中的 `render_chief_advisor_memo_card` 已成功提权与重构：
   - 移出 `wing_expander`，位于 4 张指标卡正下方，首屏直显无需点击；
   - 重构为 1 行 5 列横向等高矩阵（子卡高度约 115px，窄屏流式自适应折行）；
   - 严格遵循规则 27，CommonMark 4 空格泄露防御 100% 达标。
3. 测试套件全量通过：
   - 新增专项测试 `tests/test_g16_phase1_memo_and_combat29.py`（6/6 passed）；
   - 备忘录回归测试 `tests/test_adversarial_m2_challenger2_timemachine_and_memo.py`（12/12 passed）；
   - 备忘录对抗测试 `tests/test_challenger_m2_adversarial.py`（24/24 passed）；
   - 基础架构与裁判测试 `tests/test_infra.py`（14/14 passed）。

---

## 5. Verification Method (独立复核方法与命令)

后续审查智能体可按以下步骤进行独立法证核验：

### 5.1 运行备忘录专项全量测试命令
```powershell
# 1. 运行 M1 新增专属针对性单测 (覆盖 HoldingItem, 29基真实账本, Tab 1 字典保护, 1行5列矩阵布局)
py -3 -m pytest tests/test_g16_phase1_memo_and_combat29.py -v

# 2. 运行备忘录全量回归与对抗测试套件 (共 42 项全部通过)
py -3 -m pytest tests/test_adversarial_m2_challenger2_timemachine_and_memo.py tests/test_challenger_m2_adversarial.py tests/test_g16_phase1_memo_and_combat29.py -v

# 3. 运行基础架构与物理安全红线单测 (14 项全部通过)
py -3 -m pytest tests/test_infra.py -v
```

### 5.2 独立 Python 探针核验实战账本
```powershell
py -3 -c "from AGY2_FundAdvisory.multi_ledger_manager import MultiLedgerManager; from AGY2_FundAdvisory.advisory_engine import generate_chief_advisor_memo; mlm = MultiLedgerManager(); pm = mlm.get_pm('combat_29_funds'); memo = generate_chief_advisor_memo(holdings=pm.holdings); p = memo['portfolio_pathology']; assert p['deep_loss_count'] >= 3; assert p['frag_count'] == 19; assert abs(p['frag_amt'] - 442.70) < 0.01; print('PROBE VERIFICATION SUCCESS: deep_loss >= 3, fragments == 19 (¥442.70)')"
```

### 5.3 失效判定准则 (Invalidation Conditions)
若出现以下任一现象，即判定实现失败：
1. `combat_29_funds` 在备忘录中报出 `deep_loss_count < 3` 或漏掉 `011613`、`100032`、`161725`；
2. `frag_count != 19` 或 `frag_amt != 442.70`（如误将 `005827 易方达蓝筹` 计入）；
3. Tab 1 建仓方案输入权重字典时仍报出“6只碎片尾仓合计 ¥1.00”；
4. 首屏在未点击折叠框时看不到备忘录卡片；
5. `test_infra.py` 或备忘录单测出现任何断言失败。
