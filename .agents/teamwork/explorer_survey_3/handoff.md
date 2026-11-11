# G16 世代第二阶段后半段及第三、第四阶段只读实地走查深度调查报告 (handoff.md)

## 1. 核心观察 (Observation)

### 1.1 `multi_ledger_manager.py` 存量 29 基账本与幂等挂载机制

- **文件位置**: `D:\Google\Workspace\Wind\AGY2_FundAdvisory\multi_ledger_manager.py`
- **初始化与挂载逻辑 (第 170~187 行 与 189~312 行)**:
  ```python
  # AGY2_FundAdvisory/multi_ledger_manager.py:170-182
  # 确保预置实战存量组合（29只·¥2.66万）存在
  combat_item = next((l for l in final_ledgers if l.get("id") == "combat_29_funds"), None)
  combat_json_path = self.ledgers_dir / "combat_29_funds.json"
  if not combat_item or not combat_json_path.exists():
      combat_meta = self._init_preset_combat_29_ledger()
      if not combat_item:
          final_ledgers.append(combat_meta)
      else:
          for idx, l in enumerate(final_ledgers):
              if l.get("id") == "combat_29_funds":
                  final_ledgers[idx] = combat_meta
                  break
  ```
- **数据结构与数值核验 (`combat_29_funds.json` 与 `multi_ledger_manager.py` 第 196~229 行)**:
  - **总市值 (Total Market Value)**: 严格分厘平账为 **¥26,615.10**。
    - 7 大核心仓位 (`005561`, `110020`, `017436`, `002351`, `100032`, `011613`, `000216`): 市值合计 **¥25,128.29**。
    - 3 只腰部仓位 (`161725`, `000217`, `005827`): 市值合计 **¥1,044.11**。
    - 19 只碎片尾仓 (`016634` 至 `001551`, 单只 < ¥200): 市值合计 **¥442.70**。
    - $25,128.29 + 1,044.11 + 442.70 = 26,615.10$ 元。
  - **投入本金与累计收益核验**:
    - `ORIGINAL_REQUEST.md` (第 12、44 行) 规定目标: 总市值 ¥26,615.10，投入本金 ¥27,568.50，累计收益 -¥953.40 ($26,615.10 - 27,568.50 = -953.40$)。
    - 当前 `combat_29_funds.json` 实际数据: `cost_basis` 合计为 **¥27,372.20**，`floating_pnl` 合计为 **-¥757.10** ($26,615.10 - 27,372.20 = -757.10$)。
    - 差异分析: 存在 ¥196.30 差额。主要因原始核心标的中有盈利标的（`005561` 浮盈 +112.88, `110020` 浮盈 +137.52, `017436` 浮盈 +54.91, `000216` 浮盈 +34.81, `000217` 浮盈 +16.93）部分冲抵了亏损；且腰部 `005827` 在需求中记录为浮亏 -27.28，在代码中记录为 -23.86 (差额 3.42)。
    - 三大深套出血点数据完全一致: `#5 100032` 浮亏 -332.54, `#6 011613` 浮亏 -428.48, `#8 161725` 浮亏 -175.76，三大出血点浮亏严格等于 **-¥936.78**。
- **持有天数失配现状 (400 天 vs 1040 天)**:
  - 在 `multi_ledger_manager.py` 第 249、254 行，批次字段写死 `"buy_date": "2024-01-05"`，而 `holding_days` 静态填入 `400`。
  - 当 `PortfolioManager._recalculate_totals()` (见 `portfolio_manager.py:4053-4058`) 运行时，会基于当前自然日与 `buy_date` 动态重新计算:
    ```python
    b_dt = datetime.strptime(b.buy_date, "%Y-%m-%d").date()
    b.holding_days = max(0, (today_date - b_dt).days)
    ```
    当前为 2026 年 11 月，距离 2024-01-05 已达 **1040 天**！
  - 导致结果: 首屏主动风控哨与运行时显示“持有第 1040 天”，而 Tab 2 专属卡片文案（`app_gui.py:5798, 5809`）静态写死“持仓天数均已达 400 天”，产生界面上下文案数值不一致。
- **单测污染与崩溃实测**:
  - 运行 `pytest tests/test_multi_ledger_manager.py -v` 发现:
    `test_get_all_ledgers_summary FAILED` (报错: `Obtained: 427615.1, Expected: 400000.0`)。
  - 根因定位: `test_get_all_ledgers_summary` 依赖隔离的 `temp_workspace` fixture，预期只有 `main_live` (100,000) 与新创建的 `稳健养老金` (300,000)，合计 400,000。
  - 但因 `MultiLedgerManager.__init__` 内部无条件调用 `_ensure_index_initialized()`，将 `combat_29_funds` (资产 27,615.10) 自动强行注入到了该临时单测目录中，导致单测断言失败。

---

### 1.2 `strategy_bridge.py` 与 `app_gui.py` (Tab 2 与 Tab 3)

#### Tab 2: 瘦身重构面板与量化指标
- **现有实现 (`app_gui.py:5744-5845`)**:
  - 第 5744~5779 行: 渲染了 `🧹 碎片尾仓一键瘦身建议卡`，点击后直接激活 `btn_sweep_tail_cleaner`，将 `rad_tab2_scenario_mode` 设置为 `sweep_tail_and_c_class`，锚定到 `002351 易方达裕祥回报债券A`。
  - 第 5780~5845 行: 在 `active_lid == "combat_29_funds"` 时渲染 `🎯 实战存量组合（29只·¥26,615.10）三阶专项重塑与减亏手术方案`:
    1. ① 🧹 19 只免赎碎片尾仓全额清扫归拢 (回收 ¥442.70 · 零赎回费);
    2. ② 🩺 三大核心深套亏损源精准手术（#5、#6、#8 合计浮亏 -¥936.78);
    3. ③ 📊 调仓优化前后全周期对照（29 只 -> 7 只全天候压舱石，年化 +6.12% -> +11.92%，最大回撤 -20.29% -> -14.80%）。
- **指标缺失与未联动链条**:
  - 在 `strategy_bridge.py` 第 6140~6235 行，存在现成的 `estimate_rebalance_impact` 函数，专门精算 `vol_diff`、`div_diff`（票息垫提升）与 `payback_days`（回本天数缩短）。
  - **严重脱节**: `estimate_rebalance_impact` 在整个 `app_gui.py` 中**从未被调用**（全局调用次数为 0）！
  - 需求中明确指出的四个量化指标维度:
    1. 持仓数量: 29只 -> 6只 (清扫 19 只尾仓后剩 10 只，再置换合并 #6、#8 后精炼至 6 只);
    2. 盘活零费率碎片资金: ¥442.70 (仅19只碎片) ~ ¥962.57 (合并置换白酒及C类等非标尾部);
    3. 票息安全垫提升: 调仓后加权股息率/防御垫增加;
    4. 预计回本天数缩短: 依赖 `payback_days` 精算输出。

#### Tab 3: 组合回测与历史时点时光机盲测
- **回测入口与接入点 (`app_gui.py:6840-7250`)**:
  - 第 6857~6944 行: 顶部置顶了 `🕰️ 历史任意时点时光机盲测验证（检验投顾真赚钱能力）`。
  - 第 6948~7012 行: 下方提供了四种回测模式 (`["📒 单账本/方案回测", "🔄 调仓前 vs 调仓后对比", "🆚 双账本同屏 PK", "📊 C1~C5 策略基准档"]`)。
  - **缺失独立接入点**: 当前 Tab 3 **没有显式的「实战存量组合：原始29基 vs 投顾重构6基（近1年真规则回测对比）」一键对比预设选项**！用户必须手动将激活账本切换为 `combat_29_funds`，再在下拉框中选择“🔄 调仓前 vs 调仓后对比”，且对标目标默认仍是全天候 C3 策略而非重构 6 基。
  - **费率与交易规则支持度分析**:
    - `StrategyBridge.build_custom_portfolio_backtest` (第 4897~5030 行): 仅进行了静态日度收益率累乘 `np.cumprod(1.0 + port_ret)`，对场外公募仅粗暴扣除 5% 现金拖累（`0.95 * p_ret + 0.05 * cash_ret`），**完全未接入**真实前端申购费（0.12%）、持有期阶梯赎回费（1.50%惩罚等）、限购限制与 T+1 交易规则！
    - `run_historical_time_machine_backtest` (第 7194~7352 行): 完整支持了 0.12% 申购费、FIFO 阶梯赎回费（7天内1.50%、30天内0.50%、180天内0.35%、365天内0.15%）、C类日计提销售服务费（0.40%/250）与 5% 现金管理收益。
- **时光机盲测核心缺陷 (静态锁死权重致 2024.09 踏空 -30.46%)**:
  - **代码确切位置**: `strategy_bridge.py` 第 7223 行与第 7247~7260 行:
    ```python
    # 第 7223 行：仅在 t=0 起点日调用了一次策略函数
    weights_t = strategy_fn_for_tier(hist_slice, tier=tier)
    ...
    # 第 7247~7260 行：前推整个周期内 norm_w 完全静态恒定
    for t in range(1, n_fwd):
        day_ret = 0.0
        for a, w in norm_w.items():
            p_prev = float(fwd_slice[a].iloc[t - 1])
            p_curr = float(fwd_slice[a].iloc[t])
            r_a = (p_curr / p_prev - 1.0) if p_prev > 0 else 0.0
            day_ret += w * r_a
    ```
  - **实证后果**: 2024-09-18（9.24 史诗级反转前夕），当天市场尚未站上 MA20，起点权重偏重防守（纯债与红利重仓）；后续 250 个交易日内，虽然 9 月 24 日大盘出现暴烈放量突破，但由于静态权重从未再平衡，系统错失右侧加仓机会，导致前推 1 年收益仅 +19.94%，而同期沪深 300 暴涨 +50.40%，界面直接打出红字“跑输基准 (-30.46%)”。

---

### 1.3 物理红线与裁判文件完整性检验

- **四个只读裁判文件状态**:
  经过 SHA256 指纹校验与 `git status` 走查，四个只读裁判文件处于 100% 原始未修改保护状态:
  1. `D:\Google\Workspace\Wind\AGY2_FundAdvisory\judge_engine.py`:
     `SHA256: 76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF31CC07BE` (干净无修改)
  2. `D:\Google\Workspace\Wind\AGY2_FundAdvisory\holdout_vault.py`:
     `SHA256: 88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670BD031D2A` (干净无修改)
  3. `D:\Google\Workspace\Wind\AGY2_FundAdvisory\AGENT_SPEC.md`:
     `SHA256: A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B800CD63957` (干净无修改)
  4. `D:\Google\Workspace\Wind\tests\test_infra.py`:
     `SHA256: 48BEE0DA300D7C0A0848EC1376E4B9B2E55224D2736081713B4340F0362CD100` (干净无修改)
  5. （对照 `AGY2_FundAdvisory\tests\test_infra.py`: `SHA256: B8D781BE8135BE05CF61E62E4B534E359985AD880F27FFB61228A33DF6B02A6A` 亦完好存在）。
- **`DataLoader.simulate_execution` 签名与逻辑**:
  - 位置: `AGY2_FundAdvisory/data_loader.py:1437`
  - 签名: `simulate_execution(weights_df, prices_df, is_otc=True, penalty_days=7, penalty_rate=0.015, etf_impact=0.001) -> pd.DataFrame` 保持完全未动。

---

### 1.4 回归测试套件实测运行现状

| 测试文件 | 用例数 | 运行耗时 | 执行结果 | 关键发现与警告 |
|---|---|---|---|---|
| `tests/test_infra.py` | 14 | 9.03s | **100% PASSED** | 裁判基建因果探针、四岛接口、防套利红线全部绿灯 |
| `tests/test_adv_final_closure.py` | 14 | 47.20s | **100% PASSED** | 9大资产穿透分类、多账本绑定、智能别名全覆盖通过 |
| `tests/test_g3_evolution_loop.py` | 12 | 32.78s | **100% PASSED** | EWMA 动态相关、微观 VWAP 滑点、三大历史拐点信号通过 |
| `tests/test_gui_multi_ledger_stress.py` | 10 | 62.95s | **100% PASSED** | 账本快速切换原子性、AppTest 动态状态机与自愈容错通过 |
| `tests/test_adversarial_m3_combat29_challenger.py` | 9 | 13.98s | **100% PASSED** | 29基市值分厘平账(¥26,615.10)、19只碎片尾仓清理与3大深套亏损源通过 |
| `tests/test_multi_ledger_manager.py` | 8 | 27.10s | **1 FAILED, 7 PASSED** | 失败点: `test_get_all_ledgers_summary` 因 `combat_29_funds` 无条件挂载到 temp fixture 导致总资产不符 (427,615.1 vs 400,000.0) |

---

### 1.5 `generate_chief_advisor_memo` 深套识别 Bug 与单测位置探查

- **Bug 根因 (`advisory_engine.py:4284`)**:
  ```python
  # advisory_engine.py:4284
  cost_v = float(getattr(h, "cost_value", 0.0) or (h.get("cost_value", 0.0) if isinstance(h, dict) else 0.0))
  pl_ratio = (mv / cost_v - 1.0) if cost_v > 0 else 0.0
  ```
  `FundHolding` / `HoldingItem`（定义见 `portfolio_manager.py:261` 与 `323`）对象的真实字段是 `cost_basis`、`cost_price`、`cost_nav` 以及 `floating_pnl_pct`，根本不存在 `cost_value` 属性！
  导致 `cost_v` 永远为 `0.0`，`deep_loss_list` 永远为空，深套亏损超 10% 的病灶永远报不出来。
- **单测最佳编写位置探查**:
  - 推荐编写位置: **`tests/test_adv_final_closure.py`** 中的 `TestAdvFinalClosure` 测试类（行尾新增测试方法 `test_specialized_15_chief_advisor_memo_holding_item_deep_loss_detection`）。
  - **依据与优势**:
    1. `tests/test_adv_final_closure.py` 第 16 行已经显式引入了 `from portfolio_manager import PortfolioManager, FundHolding, HoldingItem`；
    2. 该文件正是第四阶段全量测试指令（`pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py`）中四个核心目标文件之一；
    3. 测试逻辑直接传入真实 `HoldingItem`（或直接载入 `combat_29_funds` 的持仓字典），强力断言 `memo["portfolio_pathology"]["deep_loss_count"] >= 3`，实现 100% 原位拦截闭环。

---

### 1.6 G17 世代进化指令输出格式门禁红线

- 规范约束（源自 `ORIGINAL_REQUEST.md` 第 60~66 行）:
  - 绝对禁止输出带冒号的客户端转义格式（如 `slashCommand:goal`、`slashCommand:boost`、`slashCommand:teamwork`、`slashCommand:browser`）；
  - 必须 100% 严格使用四个纯文本斜杠指令:
    - `/goal`
    - `/boost`
    - `/teamwork`
    - `/browser`
  - 终审与外审代理若检测到包含任何 `slashCommand:` 冒号形式字符串，一律视为阻断性违规。

---

## 2. 逻辑推导链 (Logic Chain)

```
[Observation 1.1] MultiLedgerManager.__init__ 内部无条件调用 _init_preset_combat_29_ledger
       ↓
[Observation 1.4] 临时工作区测试 test_get_all_ledgers_summary 被注入了 combat_29_funds (¥27,615.10)
       ↓
[Inference 1] 导致 test_get_all_ledgers_summary 断言 total_equity 400000.0 失败 (实际为 427615.1)
       ↓
[Actionable Recommendation 1] 必须在 MultiLedgerManager 初始化中增加工作区环境判定：
仅当 self.root == WORKSPACE_ROOT（即正式运行环境或 UI 调用 get_instance()）时自动幂等挂载 combat_29_funds；
若为 pytest 临时目录（temp_workspace）则不主动注入，彻底恢复单测 100% 绿灯。

-----------------------------------------------------------------------------------------

[Observation 1.1] multi_ledger_manager 中 buy_date 写死 2024-01-05
       ↓
[Observation 1.1] portfolio_manager._recalculate_totals 动态计算持仓天数为 (今日 - 2024-01-05) = 1040 天
       ↓
[Observation 1.2] app_gui.py:5798, 5809 卡片静态文本硬编码写死“均已达 400 天”
       ↓
[Inference 2] 首屏主动风控哨与运行时报“持有第 1040 天”，与卡片文案“400天”直接冲突
       ↓
[Actionable Recommendation 2] 在 multi_ledger_manager 预置批次中将 buy_date 设定为动态的
(datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")，或者将 UI 文案升级为自适应动态读取真实持仓天数，
实现全页面各模块天数 100% 自洽。

-----------------------------------------------------------------------------------------

[Observation 1.5] advisory_engine.py:4284 读取了不存在的 getattr(h, "cost_value", 0.0)
       ↓
[Observation 1.5] real HoldingItem 仅包含 cost_basis, cost_price, floating_pnl_pct
       ↓
[Inference 3] pl_ratio 恒为 0.0，deep_loss_list 恒为空，导致五维备忘录永远漏检深套标的
       ↓
[Actionable Recommendation 3] 升级 cost 计算逻辑：按优先级兼容 cost_price * shares, cost_basis, cost_nav * shares，
若存在 floating_pnl_pct 则直接读取；并在 tests/test_adv_final_closure.py 中新增 HoldingItem 测试断言 deep_loss_count >= 3。

-----------------------------------------------------------------------------------------

[Observation 1.2] Tab 3 run_historical_time_machine_backtest 在 t=0 静态冻结 norm_w
       ↓
[Observation 1.2] 2024-09-18 起点日为偏防守配置，9.24 暴烈突破后未动态加仓
       ↓
[Inference 4] 导致时光机前推 1 年严重踏空基准 30.46%，暴露出“假动态、真静态死拿”的伪盲测缺陷
       ↓
[Actionable Recommendation 4] 在前推循环中引入每 20 个交易日（或乖离率/ERP状态机切换点）的动态再平衡，
以截至当日的无未来切片动态更新目标权重，并计入换仓双边摩擦。
```

---

## 3. 局限与未探查项 (Caveats)

1. **真实行情外网连通性与证书警告**: 在执行单元测试过程中，终端打印出少量 `urllib3` 访问 `datacenter-web.eastmoney.com` 的 InsecureRequestWarning，系离线/模拟环境下未校验 HTTPS 证书所致，不影响本地量化计算。
2. **Tab 3 静态回测数据源跨度**: 本次回测探查基于当前本地 `data_loader.py` 加载的 2018 年至今历史矩阵，未对 2018 年以前的极端周期（如 2015 杠杆牛灾）在时光机盲测中进行全覆盖回放。
3. **只读约束遵守**: 本次走查严格遵守探索智能体只读准则，未修改任何工作区代码或测试文件。

---

## 4. 结论与执行建议 (Conclusion)

1. **多账本管理 (`multi_ledger_manager.py`)**:
   - `combat_29_funds` 数据市值精确分厘平账为 ¥26,615.10，但投入本金与累计收益存在 ¥196.30 差额（目前累计亏损 -¥757.10 vs 目标 -¥953.40），可通过在初始数据中对齐腰部与非主力标的成本使之严格等于 ¥27,568.50 与 -¥953.40。
   - `buy_date` 建议动态设为 400 天前，消除 1040 天与 400 天的界面冲突。
   - 挂载机制需增加 `if self.root == WORKSPACE_ROOT:` 条件防护，避免污染 pytest 的 `temp_workspace`，立即可修复 `test_get_all_ledgers_summary` 单测。
2. **Tab 2 瘦身面板与调仓精算 (`app_gui.py` & `strategy_bridge.py`)**:
   - Tab 2 已具备三阶手术方案静态骨架，但尚未接入 `estimate_rebalance_impact` 动态算子。
   - 建议在 Tab 2 中实装针对 29 基的一键模拟面板，直观呈现「持仓标的 29只 -> 6只、盘活零费率资金 ¥442.70~¥962.57、年化内生票息垫提升、回本天数缩短」四大核心量化指标。
3. **Tab 3 回测与时光机盲测动态化 (`strategy_bridge.py` & `app_gui.py`)**:
   - 在 Tab 3 回测模式下拉框或显著位置增加「实战存量组合：原始29基 vs 投顾重构6基（近1年真规则回测对比）」快捷预设。
   - 将 `run_historical_time_machine_backtest` 从“起点单次静态锁死”重构为“前推周期动态切片再平衡”，彻底解决 2024.09 踏空问题。
4. **全量测试与安全红线**:
   - 四大只读裁判文件零改动，哈希完好。
   - 推荐在 `tests/test_adv_final_closure.py` 中新增 `test_specialized_15_chief_advisor_memo_holding_item_deep_loss_detection`，断言 `deep_loss_count >= 3`。
   - 严守 G17 命令标签输出门禁（仅允许纯文本 `/goal`, `/boost`, `/teamwork`, `/browser`，严禁 `slashCommand:` 冒号形式）。

---

## 5. 独立验证方法 (Verification Method)

后续执行代理或内审代理可通过以下确定性步骤逐项复核本报告结论:

1. **裁判文件防篡改哈希核查**:
   ```powershell
   Get-FileHash -Algorithm SHA256 AGY2_FundAdvisory\judge_engine.py, AGY2_FundAdvisory\holdout_vault.py, AGY2_FundAdvisory\AGENT_SPEC.md, tests\test_infra.py
   ```
2. **29 基账本持仓数据与会计恒等式核验**:
   ```powershell
   py -3 -m pytest tests/test_adversarial_m3_combat29_challenger.py -v
   ```
3. **多账本单测失败复现**:
   ```powershell
   py -3 -m pytest tests/test_multi_ledger_manager.py::test_get_all_ledgers_summary -v
   ```
4. **四套核心回归套件一键验证**:
   ```powershell
   py -3 -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py -v
   ```
5. **时光机静态锁死代码位置复核**:
   查看 `AGY2_FundAdvisory/strategy_bridge.py` 第 7223 行与 7247~7260 行 `for t in range(1, n_fwd):` 循环中的 `norm_w` 变量作用域。
