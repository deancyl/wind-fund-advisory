# Forensic Audit Report — Milestone 1 (Top Area & Tab 1 Three-Block Refactoring)

**Work Product**: `AGY2_FundAdvisory/app_gui.py` (Top Area & Tab 1), referee files, `DataLoader.simulate_execution`, global config  
**Profile**: General Project (development mode)  
**Verdict**: **CLEAN**

---

## 1. Observation (直观观测事实与证据)

### 1.1 四大只读裁判文件 SHA256 哈希与 Git Diff 校验
通过 PowerShell `Get-FileHash` 与 `git diff HEAD` 独立核验：
- `AGY2_FundAdvisory/judge_engine.py`:
  - SHA256: `76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF31CC07BE`
  - Git Diff: `0` 行修改 (`git diff HEAD -- AGY2_FundAdvisory/judge_engine.py` 无任何输出)
- `AGY2_FundAdvisory/holdout_vault.py`:
  - SHA256: `88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670BD031D2A`
  - Git Diff: `0` 行修改 (`git diff HEAD -- AGY2_FundAdvisory/holdout_vault.py` 无任何输出)
- `AGY2_FundAdvisory/AGENT_SPEC.md`:
  - SHA256: `A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B800CD63957`
  - Git Diff: `0` 行修改 (`git diff HEAD -- AGY2_FundAdvisory/AGENT_SPEC.md` 无任何输出)
- `tests/test_infra.py`:
  - SHA256: `48BEE0DA300D7C0A0848EC1376E4B9B2E55224D2736081713B4340F0362CD100`
  - Git Diff: `0` 行修改 (`git diff HEAD -- tests/test_infra.py` 无任何输出)

### 1.2 `DataLoader.simulate_execution` 签名与扣费逻辑校验
- 文件路径: `AGY2_FundAdvisory/data_loader.py` (行 1436–1553)
- Git Diff: `0` 行修改 (`git diff HEAD -- AGY2_FundAdvisory/data_loader.py` 无任何输出)
- 函数签名完全未改动：
  ```python
  @staticmethod
  def simulate_execution(
      weights_df: pd.DataFrame,
      prices_df: pd.DataFrame,
      is_otc: bool = True,
      penalty_days: int = 7,
      penalty_rate: float = 0.015,
      etf_impact: float = 0.001
  ) -> pd.DataFrame:
  ```
- 扣费逻辑完整保持真实阶梯赎回机制（持有天数 < 7 天 1.50% 惩罚费；7~29 天 0.50% C 类 / 0.75% A 类；30~179 天 A 类 0.50% / C 类 0.00%；>=180 天梯级减免；包含 ETF 冲击成本 0.10%）。

### 1.3 全局配置文件零变更校验
- 文件路径: `C:\Users\deanc\.gemini\GEMINI.md`
- 属性校验:
  - Length: `5811` bytes
  - LastWriteTime: `2026/11/3 18:44:33` (距今 5 天前，本工作周期内零触碰)
  - SHA256: `9BECD134C885E623711A3F8D4892B80C87D8E8EB9F676A5EA52CC675ACBC09FB`

### 1.4 `AGY2_FundAdvisory/app_gui.py` 真实性与防作弊检查
- **静态代码审查**:
  - 全局 CSS 注入: `.main-metric-card` 高度锁死为 82px，`padding-top: 1.2rem !important;`，去除了卡片标题的装饰性 Emoji。
  - 双翼看板折叠: 今日投顾结论合入 `wing_expander` 标题，行内并排对齐跳转按钮 `btn_master_action_switch`，移除原本独立占行的行动横幅。
  - Tab 1 三块式重构:
    - **模块 1**: 单行紧凑控件（本金 `plan_capital_input`、档位 `tab1_tier_selector`、节奏 `radio_capital_deployment_mode`、Popover `⚙️ 高级微调` 内含 7 大标准模型名与参数调节、单一主按钮 `⚡ 生成实盘建仓方案` key=`btn_run_simulation_now`）。
    - **模块 2**: 3 张高对比度决策卡片（`收益与胜率`, `风险底线`, `攻防定权`）直接置顶于执行数据表上方，紧贴渲染 `st.dataframe(df_display)`。
    - **模块 3**: 单行平铺 4 个操作 Popover/按钮（`📥 覆盖写入当前账本`、`🆕 另存为全新独立账本`、`📱 下单小抄`、`📈 送入穿透回测`），底部收纳单一白盒抽屉 `with st.expander("🔬 展开机构级量化压力测试与选基白盒证据", expanded=False):`。
  - **真实计算流核验**:
    - 推演调用真实量化桥接函数 `StrategyBridge.compute_n_funds_model_portfolio`；
    - 执行单调用真实生成函数 `StrategyBridge.generate_zero_start_blueprint`；
    - 风险预算调用 `calculate_portfolio_risk_contributions`；
    - 稳健三步与智能定投调用 `SmartExecutionDCAEngine.plan_three_step_batches` 与 `SmartExecutionDCAEngine.plan_smart_dca`；
    - 账本写入调用真实底座 `pm.apply_zero_start_blueprint` 与 `mlm_inst.create_ledger`；
    - 流动性折价调用真实微观冲击模型 `data_loader.calculate_otc_fund_liquidity_haircut`；
    - 无任何 hardcoded 返回常量、无 facade 空壳实现、无对量化引擎的虚假绕过。
  - 语法编译通过: `py -3 -m py_compile AGY2_FundAdvisory/app_gui.py` 退出码 0，无语法错误。

### 1.5 独立自动化测试实证结果
- `py -3 -m pytest tests/test_infra.py`:
  - 结果: `14 passed in 5.73s` (100% 通过)
- `py -3 -m pytest tests/test_anticheat_full_closure.py -k test_apptest_tab1_seven_models_and_black_swan_rendering`:
  - 结果: `1 passed, 4 deselected in 42.57s` (100% 通过)
- `py -3 -m pytest tests/test_g8_ux_and_realtime_fusion.py`:
  - 结果: `7 passed in 20.90s` (100% 通过)
- `py -3 -m pytest tests/test_g10_correlation_liquidity_and_stress.py`:
  - 结果: `6 passed, 41 warnings in 19.55s` (100% 通过)
- `py -3 -m pytest tests/test_gui_multi_ledger_stress.py -k test_tab1_save_to_new_ledger_isolation`:
  - 结果: `1 passed, 9 deselected in 1.73s` (100% 通过)

---

## 2. Logic Chain (推理链条)

1. **裁判文件不变性**: 基于 1.1，4 个裁判文件的 SHA256 哈希值与 git diff 均为 0，证明裁判规则与测试基准绝对未被篡改。
2. **算子真实性**: 基于 1.2，`data_loader.py` 的 `simulate_execution` 签名与赎回阶梯逻辑 100% 未动，符合底层量化因果律要求。
3. **全局隔离红线**: 基于 1.3，`C:\Users\deanc\.gemini\GEMINI.md` 的修改时间仍为 2026/11/3，未发生溢出污染。
4. **前端重构真实性**: 基于 1.4，`AGY2_FundAdvisory/app_gui.py` 的重构严格按照 ORIGINAL_REQUEST.md 的三块式极简架构完成，移除了旧版的步骤指示器、灰框说明、重复按钮与分割大标题，合并了横幅。所有交互按钮与数据表均完整挂载至真实量化计算逻辑，无欺骗性静态常量，各 session_state 键名完全兼容。
5. **行为验证一致性**: 基于 1.5，所有受影响的基建、防作弊、前端 AppTest 及压力测试全部绿灯通过，无功能回归。

---

## 3. Caveats (注意事项与上下文提示)

1. **工作区持仓账本观测**:
   在执行全库测试回归时观察到 `portfolio_ledger.json` 最新保存时间戳为 `2026-11-08 20:13:55`（在 G11 M1 启动前已被更新），其中的持仓示范代码已演化为 `['005561', '100032', '011612', '011613', '013841', '001071']`。此项属于 Milestone 2（Tab 2 持仓诊断与账本运维）的职责范畴，本审计员作为只读审计角色，未修改任何数据账本文件。
2. **审计范围边界**:
   本审计仅针对 Milestone 1 的交付物（Top Area 与 Tab 1 三块式架构、裁判文件、`DataLoader.simulate_execution` 与全局配置）。Tab 2 的三块式重构与账本管理由 Milestone 2 承接并独立审计。

---

## 4. Conclusion (审计结论)

**Verdict**: **CLEAN**

Milestone 1 工作产物完全符合反作弊与工程真实性契约：
- 四大裁判文件 0 修改，哈希完全一致；
- `DataLoader.simulate_execution` 保持只读与真实费率阶梯；
- 全局配置文件 0 触碰；
- `app_gui.py` 三块式极简架构实现真实、逻辑完备、无作弊绕过；
- 相关专项自动化测试 100% 绿灯通过。

---

## 5. Verification Method (独立复核指令)

后续代理或复核人员可使用以下命令独立复现本报告的检验事实：

```powershell
# 1. 检验四大裁判文件哈希与 git diff
git diff HEAD -- AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md tests/test_infra.py
Get-FileHash -Algorithm SHA256 AGY2_FundAdvisory/judge_engine.py, AGY2_FundAdvisory/holdout_vault.py, AGY2_FundAdvisory/AGENT_SPEC.md, tests/test_infra.py

# 2. 检验 DataLoader.simulate_execution 零修改
git diff HEAD -- AGY2_FundAdvisory/data_loader.py

# 3. 检验全局 GEMINI.md 修改时间与哈希
Get-Item "c:\Users\deanc\.gemini\GEMINI.md" | Select-Object FullName, Length, LastWriteTime
Get-FileHash -Algorithm SHA256 "c:\Users\deanc\.gemini\GEMINI.md"

# 4. 检验 app_gui.py 语法编译与核心测试
py -3 -m py_compile AGY2_FundAdvisory/app_gui.py
py -3 -m pytest tests/test_infra.py
py -3 -m pytest tests/test_anticheat_full_closure.py -k test_apptest_tab1_seven_models_and_black_swan_rendering
py -3 -m pytest tests/test_g8_ux_and_realtime_fusion.py
py -3 -m pytest tests/test_g10_correlation_liquidity_and_stress.py
py -3 -m pytest tests/test_gui_multi_ledger_stress.py -k test_tab1_save_to_new_ledger_isolation
```
