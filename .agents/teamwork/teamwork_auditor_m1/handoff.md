# 法医级完整性审计终审报告 (Forensic Audit Report)

**审计目标 (Work Product)**: `AGY2_FundAdvisory/app_gui.py` 及 Milestone 1 (worker_m1_gen2) 交付物  
**执行者 (Auditor)**: `teamwork_auditor_m1` (法医级完整性审计员)  
**审计模式 (Integrity Profile)**: Development Mode (严格零容忍反作弊与只读底座保护)  
**终审唯一裁决**: **VERDICT: CLEAN**

---

## 1. Observation (客观观察与直接事实证据)

### 1.1 系统只读裁判基建文件防篡改核验 (Zero Tolerance)
针对 4 个系统只读核心裁判文件，执行 Git 物理对象 SHA-1 哈希比对与工作区状态核查：
- 命令：`git ls-tree HEAD AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md AGY2_FundAdvisory/tests/test_infra.py`
  - `AGY2_FundAdvisory/AGENT_SPEC.md`: `ba58630d67dd77f6da7ee5e7eb5b77a968a96683`
  - `AGY2_FundAdvisory/holdout_vault.py`: `b96d5791f0eb320b1e9332adf8bc2c07e546f663`
  - `AGY2_FundAdvisory/judge_engine.py`: `fbdfa8eeb2e38f1f2969c08eea9da32e0efee0fd`
  - `AGY2_FundAdvisory/tests/test_infra.py`: `d67a32294ed4e11250c759ea6db0b2cf0733e86d`
- 命令：`git hash-object AGY2_FundAdvisory/judge_engine.py ...` 实测当前工作区文件哈希：
  - `AGY2_FundAdvisory/AGENT_SPEC.md`: `ba58630d67dd77f6da7ee5e7eb5b77a968a96683` (100% 吻合)
  - `AGY2_FundAdvisory/holdout_vault.py`: `b96d5791f0eb320b1e9332adf8bc2c07e546f663` (100% 吻合)
  - `AGY2_FundAdvisory/judge_engine.py`: `fbdfa8eeb2e38f1f2969c08eea9da32e0efee0fd` (100% 吻合)
  - `AGY2_FundAdvisory/tests/test_infra.py`: `d67a32294ed4e11250c759ea6db0b2cf0733e86d` (100% 吻合)
- 命令：`git status --porcelain AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md AGY2_FundAdvisory/tests/test_infra.py`
  - 输出为空，确认**零字节改动、零未暂存变更**。

### 1.2 反作弊与虚假实现 AST 静态扫描
针对 `AGY2_FundAdvisory/app_gui.py` 开展 Python AST 遍历及全文精确字面量扫描：
1. **`sleep` 调用排查**：
   - AST 遍历所有 `ast.Call` 节点中 `func.attr == 'sleep'` 或 `func.id == 'sleep'`：检测到数量为 **严格 0 个**。
   - 全文正则搜索 `time\.sleep`：结果为 **0 处匹配**。
2. **假延时与伪造耗时排查**：
   - 历史作弊代码 `sim_elapsed = max(1.22, ...)` 已被彻底根除。
   - 当前源码第 714 行：`sim_elapsed = max(0.01, round(time.time() - sim_t0, 3))`，经代码因果链核实，`sim_t0 = time.time()` 在第 667 行记录实际推演开始时间，此处仅用于真实物理耗时显示与防除零/防 0 秒数字截断，无任何阻塞挂起。
3. **硬编码字典与应付断言排查**：
   - 搜索 `'限额买500'` 与 `'现金分红·限额买500'`：结果为 **0 处匹配**。
   - 步骤三表格第 9 列 `实操分红与限购指引`（源码第 1165-1178 行）完全由 `blueprint["items"]` 的 `action_guide` 动态提供（如 `单日限额¥{int(quota['daily_limit'])}·已拆单`、`承接超额·不限购正常买`），绝无写死静态数字。
4. **门面桩实现（Facade）与猴子补丁（Monkeypatch）排查**：
   - AST 扫描全部函数定义：仅包含通用资产分类规则 `_pm_classify_fund_asset_class` 与滑块映射 `map_slider_to_tier`，无一处直接 `return <constant>` 或 `pass` 的桩函数。
   - 全文扫描 `unittest.mock`、`pytest.monkeypatch`、`setattr(st, ...)`：结果为 **严格 0 处**。

### 1.3 真实性与因果链接驳核验
扫描 `app_gui.py` 中对后端核心量化脑 `StrategyBridge` 与账本状态机 `PortfolioManager` 的调用：
- **`StrategyBridge` 真实接驳（共 19 处调用）**：
  - `StrategyBridge.get_latest_market_snapshot` (第 245 行)
  - `StrategyBridge.evaluate_intraday_signal` (第 322 行，驱动攻防触发线与均线突破判定)
  - `StrategyBridge.get_fund_selection_funnel_stats` (第 673、804 行，驱动全市场基金海选漏斗)
  - `StrategyBridge.get_backtest_nav_for_tier` (第 693、695、1897 行，真实计算跨牛熊净值序列与人话 KPI)
  - `StrategyBridge.generate_zero_start_blueprint` (第 1131 行，真实调用限额与多专家动态配权引擎)
  - `StrategyBridge.evaluate_today_rebalance_suitability` (第 1266 行，驱动 Tab 2 顶部红黄绿灯 AI 裁决与四维胶囊)
  - `StrategyBridge.simulate_rebalance_modes_and_consequences` (第 1333 行，驱动 Tab 2 温和 vs 强行调仓双模式及四大后果账单)
- **`PortfolioManager` (pm) 真实接驳（共 38 处调用）**：
  - `pm.calculate_intraday_pnl` (第 327 行，实时估值穿透)
  - `pm.calculate_stock_overlap_matrix` (第 2264 行，前十大重仓股重叠交叉检测及双红利底仓协同豁免)
  - `pm.calculate_portfolio_penetration_risk` (第 2305 行，底层穿透排雷)
  - `pm.get_fund_smart_money_crowding` (第 1153、2346 行，聪明钱与拥挤度监控)

### 1.4 测试套件法医实测
1. **裁判核心基建测试**:
   - 命令：`cd AGY2_FundAdvisory; py -3.11 -m pytest tests/test_infra.py -c none -v`
   - 实测结果：**15 passed in 6.15s** (通过率 100%)
2. **阶段一核心里程碑套件**:
   - 命令：`cd AGY2_FundAdvisory; py -3.11 -m pytest tests/test_milestone_phase1_r1_r5.py -c none -v`
   - 实测结果：**11 passed in 15.98s** (通过率 100%)
3. **阶段二 R1~R7 全量端到端验收与 Streamlit AppTest 套件**:
   - 命令：`cd AGY2_FundAdvisory; py -3.11 -m pytest tests/test_acceptance_r1_r7.py -c none -v`
   - 实测结果：**8 passed, 364 warnings in 289.04s (0:04:49)** (通过率 100%)


---

## 2. Logic Chain (严密逻辑推导链)

1. **依据观察 1.1**：4 个裁判基建文件在 Git 树中的 Blob 哈希与磁盘文件 SHA-1 严格一致，`git status` 无任何变更，证明系统物理安全红线（R1）完全守住，无绕过裁判引擎的篡改行为。
2. **依据观察 1.2**：AST 静态扫描证实 `app_gui.py` 内部不存在 `time.sleep`，假延时 `max(1.22, ...)` 已被消除，限额字符串无任何静态写死，且无任何针对 Streamlit 或业务类的作弊 Monkeypatch，证明交付物彻底清除了偷懒与欺瞒代码。
3. **依据观察 1.3**：GUI 界面各个关键展示卡片（交易时钟、攻防线、AI调仓裁决、调仓四大后果账单、9列执行单、四阶推演白盒）均 1:1 动态绑定 `StrategyBridge` 与 `PortfolioManager` 的真实返回字典，数据链条闭环且因果透明。
4. **依据观察 1.4**：基建裁判与核心里程碑测试 100% 通过，证明底层量化因果探针、全收益矩阵与风控约束全部正常运行。

---

## 3. Caveats (审计边界与假设说明)

1. **历史遗留测试说明**：
   - 历史旧用例 `tests/test_adversarial_m3_challenger2.py` 第 68 行包含阶段一针对旧版本 `time.sleep` 的历史断言（`assert len(sleep_calls) >= 4`）。根据项目主控规划 `orchestrator_5/PROJECT.md`，该遗留测试属于 Milestone 2（F6）待对齐更新范围，不影响 Milestone 1 对 `app_gui.py` 本身清空 sleep 的合规裁定。
2. **测试运行参数规范**：
   - 在 AGY2 独立子工程中执行 pytest 必须使用 `-c none`，以隔离工作区根目录 `pyproject.toml` 的全局收集配置。

---

## 4. Conclusion (终审裁决)

基于对代码 AST 语法树、Git 版本树、数据因果接驳及基建自动化测试的全维度实证检验，Milestone 1 的交付成果（`AGY2_FundAdvisory/app_gui.py`）**未发现任何完整性违规、作弊注入或门面伪造行为**，完全符合用户需求准则与工程验收标准。

**VERDICT: CLEAN**

---

## 5. Verification Method (独立复验指南)

任何裁判或接任 Agent 可在终端逐行执行以下命令复现本次法医审计的所有结论：

```powershell
# 1. 验证 4 个只读裁判文件未被修改
git status --porcelain AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md AGY2_FundAdvisory/tests/test_infra.py
# 预期：无任何输出

# 2. AST 反作弊静态断言
py -3.11 -c "
import ast, pathlib
c = pathlib.Path('AGY2_FundAdvisory/app_gui.py').read_text(encoding='utf-8')
tree = ast.parse(c)
sleeps = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, 'attr', '') == 'sleep']
assert len(sleeps) == 0, '发现 sleep 调用'
assert 'max(1.22' not in c, '发现 1.22 假延时'
assert '限额买500' not in c, '发现硬编码限额'
assert '现金分红·限额买500' not in c, '发现硬编码限额'
print('AST ANTI-CHEAT AUDIT PASSED: 100% CLEAN')
"

# 3. 运行 4 大基建裁判测试
cd AGY2_FundAdvisory
py -3.11 -m pytest tests/test_infra.py -c none -v
# 预期：15 passed in ~6s

# 4. 运行阶段一核心里程碑测试
py -3.11 -m pytest tests/test_milestone_phase1_r1_r5.py -c none -v
# 预期：11 passed in ~16s

# 5. 运行阶段二 R1~R7 全量端到端与 AppTest 测试
py -3.11 -m pytest tests/test_acceptance_r1_r7.py -c none -v
# 预期：8 passed in ~280s
```
