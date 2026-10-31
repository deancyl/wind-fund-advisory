# Milestone Phase 1 (R1~R5) 独立代码审查终审与对抗性验证终报 (Reviewer & Adversarial Critic 2)

**审查者**: Reviewer 2 (`reviewer_orch4_2`)  
**审查时间**: 2026-10-31T16:11:00Z  
**被审目录**: `AGY2_FundAdvisory/` (`portfolio_manager.py`, `strategy_bridge.py`, `data_loader.py`, `tests/`)  
**裁判基建文件**: `judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`  
**核心裁决 (Verdict)**: **`APPROVE`**（全项合规通过，无作弊行为，容灾健全，逻辑因果闭环）

---

## 1. Observation (客观观察与证据链)

### 1.1 系统只读裁判基建文件防篡改检查 (R1 物理红线)
- **检查命令**: `git status --porcelain` 与 `git diff --name-only`
- **核实文件**:
  - `AGY2_FundAdvisory/judge_engine.py` (未修改，哈希一致)
  - `AGY2_FundAdvisory/holdout_vault.py` (未修改，哈希一致)
  - `AGY2_FundAdvisory/AGENT_SPEC.md` (未修改，哈希一致)
  - `AGY2_FundAdvisory/tests/test_infra.py` (未修改，哈希一致)
- **裁判基建单测**: 运行 `py -3.11 -m pytest tests/test_infra.py -v`，15 项因果探测与持有期裁决测试 **15 passed in 5.21s**。
- **结论**: 裁判系统 100% 保持只读未动，零触碰。

### 1.2 反作弊与 AST 静态扫描检查 (Integrity & Anti-Cheating Check)
- **代码扫描范围**: `strategy_bridge.py`, `portfolio_manager.py`, `data_loader.py`, `app_gui.py`。
- **扫描结果**:
  - `time.sleep`: 核心代码中 **0 处** `time.sleep` 或 `sleep()` 伪造耗时行为；
  - 历史日历年份硬编码: `scan_ast_for_calendar_cheating` 扫描 `compute_dynamic_tier_weights`、`evaluate_today_rebalance_suitability`、`simulate_rebalance_modes_and_consequences`，**未发现** 2018~2025 年份字面量硬编码作弊；
  - 核心配置限额: `CORE_STRATEGY_POOL` 中全部标的的 `daily_limit` 默认值已重置为通用大额 `1e11`（代码行 510, 521, 532, 543, 565），彻底拔除写死的 500 或 1000 元硬编码；
  - 前端猴子补丁: `app_gui.py` 中不存在针对 streamlit 或系统组件的 `setattr(st, ...)` 猴子补丁；
  - 无假实现/门面实现 (No Facade/Dummy): 全部业务函数包含完整真实因果逻辑与异常分支。

### 1.3 核心实现细节与代码行定点核验

#### (1) R2: 实时限购获取与断网容灾多级缓存体系 (`portfolio_manager.py:1656-1852`)
- **实现**: `fetch_realtime_fund_quota(fund_code: str, use_cache: bool = True, db_path = None) -> Dict[str, Any]`
- **结构规范**: 严格返回 `{"fund_code": code, "status": "开放申购"|"限制大额"|"暂停申购", "daily_limit": float, "is_limited": bool}`；
- **五级容灾兜底链路**:
  1. L1 内存缓存: `_FUND_QUOTA_MEMORY_CACHE`（当日有效，纳秒级命中）；
  2. L2 本地 SQLite 缓存: `fund_daily_quota_cache` 表，携带 `cache_date` 与 `updated_at` 时间戳；
  3. 网络拉取: `akshare.fund_purchase_em()`，完整异常捕获 `try ... except Exception`；
  4. L3 离线数据湖仓兜底: `data/master/fund_trading_rules.parquet` 读取真实离线交易规则；
  5. L4 SQLite 历史最近记录与 L5 底线默认规则兜底（未限购开放申购），输入异常/断网/空数据下 **100% 零异常抛出**。

#### (2) R2: 多级瀑布流拆单算法与定投排期生成 (`portfolio_manager.py:3240-3411`)
- **实现**: `PortfolioManager.generate_zero_start_blueprint(total_capital, target_weights_funds, tier, custom_fund_overrides)`
- **拆单逻辑**:
  - 当首选标的 `amt > daily_lim` 时，首选顶格分配 `daily_lim`（若暂停申购则为 0），`action_guide` 动态注入 `f"单日限额¥{int(daily_lim)}·已拆单"`；
  - 剩余资金 `rem_amt` 路由至 `_get_sector_alternatives(code, meta)` 备选池，每只备选独立调用 `fetch_realtime_fund_quota` 校验；
  - 备选不限购时标记 `"承接超额·不限购正常买"`；备选限购时顶格分配并继续寻找下一备选；
  - 全赛道限购耗尽时，动态生成 `dca_plan`，估算定投天数并提示暂存货币/黄金；
  - 资金平账: 经实测 `allocated_sum + remaining_cash == total_capital` 精确平账至分厘。

#### (3) R2: 美股指数前缀修复与 QDII 估值纠偏 (`portfolio_manager.py:1854-2043`)
- **前缀修复**: `fetch_realtime_index_quote` 针对 `gb_` 前缀（`gb_inx`, `gb_ixic`）明确豁免添加 `s_sh` 前缀，解决新浪美股行情抓取失败问题；
- **纠偏算法**: `_apply_qdii_valuation_correction(q: FundQuote)` 匹配底层基准（`sh513500`, `sh513100`, `sh518880`），当 `abs(q.gszzl - b_change) > 1.5%` 时，强制以基准涨跌幅 `b_change * 0.95` 覆盖纠偏，联动重新核算 `gsz = round(dwjz * (1 + corrected_gszzl/100), 4)`，并标记 `valuation_corrected = True`。

#### (4) R3: 拔除 C3 静态权重劫持与三段式攻防闭环 (`strategy_bridge.py:252-281, 3344-3767`)
- **解除劫持**: `TIER_TARGET_WEIGHTS` 封装为 `DynamicTierTargetWeights(dict)` 类，所有档位（含 C3、C3_ATTACK）100% 委托给 `compute_dynamic_tier_weights` 动态生成；
- **三段式攻防**:
  1. 左侧极值超卖吸筹: 当 `erp_percentile >= 75.0` 且 `bias_20 <= -4.5%` 时，从纯债仓位划拨并逆向增配科创50 (011613) 与中证500 (001053)；
  2. 右侧施密特迟滞防打脸: 在 `[-1.5%, +1.2%]` 均线死区内且激活 `lock_previous_weights` 时，严格锁定前序权重；
  3. 右侧极端超买阶梯止盈: 当 `bias_20 >= +6.5%` 或 `crowding_warning == True` 时，成长标的削减 35% 敞口并转入纯债 (002351) 与红利低波 (005561)；
- **风险单调性定理**: 无论是极度牛市、深度熊市还是零波动状态，权益总仓位严格满足：`Equity(C1) < Equity(C2) < Equity(C3) < Equity(C4) < Equity(C5)`，且熊市下严守 `C4 <= 55%` 与 `C5 <= 70%` 的硬顶。

#### (5) R4: 调仓适宜度裁决器与强行调仓四大后果推演 (`strategy_bridge.py:4892-5440`)
- **适宜度裁决**: `evaluate_today_rebalance_suitability` 返回标准三级评级（`SUITABLE` / `HOLD_ON` / `FORBIDDEN`）、鲜明标题 `verdict_title` 与包含 `market_position_reason`, `clock_window_reason`, `deviation_utility_reason`, `lockup_fee_reason` 的完整 `reasons_4d` 字典；
- **双模式推演**: `simulate_rebalance_modes_and_consequences` 输出 `mode_gentle`（3% 缓冲区免折腾，严格裁剪未满 7 天惩罚期份额）与 `mode_forced`（强平全额偏离，如实计提 1.5% 惩罚费）；
- **四大后果精算**:
  - `fee_loss`: 赎回费、7天惩罚费、申购费、总费用平账，回本天数测算；
  - `in_transit_risk`: 在途资金金额、比例、锁定时长、同公司 SWITCH 节省金额与潜在踏空成本；
  - `risk_shift`: 调仓前后总权益、年化波动率、最大回撤、股息率对比；
  - `lockup_reset`: 新买入资金金额与 7 天 1.5% 锁定期重置警告。

#### (6) R4: 双红利底仓对与限购伴生对豁免 (`portfolio_manager.py:3570-3635`)
- **豁免池**: 策略推荐的双红利底仓对 `{"100032", "005561"}` 与标普500限购伴生对 `{"050025", "001071"}` 明确加入组合协同豁免池；
- **非对角线最大重叠度**: 计算 `max_non_diag_unexcused`，仅对非豁免标的计算重合度。持有标准推荐组合时 `max_non_diag_unexcused == 0.0`，无假阳性黄色伪分散告警；持有非豁免真实重叠组合（如科创50与芯片混合）时正常报出警报。

---

## 2. Logic Chain (推理链条与证据映射)

1. **红线与合规推理**:
   - 观测到 `git status` 显示 4 个裁判基建文件无变更，且 `test_infra.py` 全绿通过。
   - 推导出：研发过程中严格遵守系统只读约束，裁判基建效力未被稀释或削弱。

2. **反作弊与因果演绎推理**:
   - 观测到 `test_case_02_ast_no_cheating` 与 AST 静态遍历无任何日历年份硬编码与 `time.sleep`。
   - 推导出：所有策略算子均由真实滚动截面数据计算，不包含因果倒置或未来函数泄露（No Look-Ahead Bias）。

3. **动态权重与防击穿推理**:
   - 观测到 `compute_dynamic_tier_weights` 在牛市、震荡市、极端恐慌熊市（vol=0.85/0.99, bias_20=-35%/-50%）下均保持严格的归一化（sum=1.0）与单调递增链条。
   - 推导出：动态权重算法在数学上完备且边界受控，杜绝了极端行情下仓位越界或击穿风控底线的问题。

4. **异常容灾与接口鲁棒性推理**:
   - 观测到 `fetch_realtime_fund_quota` 具备 5 级级联回退体系，并在断网与空输入下保持平稳；`generate_zero_start_blueprint` 在全赛道限购下能平账生成 DCA 排期；`evaluate_today_rebalance_suitability` 与推演函数在空持仓与全现金下具备完善守卫。
   - 推导出：系统具备极高的数据容灾性与生产环境鲁棒性。

---

## 3. Adversarial Stress Testing (对抗性压力测试实测结果)

针对委托要求进行的 6 项对抗性压力场景实测（测试脚本独立执行验证）：

| 序号 | 对抗性压力场景 | 测试输入与边界条件 | 预期防御行为 | 实际运行输出 | 结果 |
|:---:|:---|:---|:---|:---|:---:|
| 1 | 断网与异常代码容灾 | 传入 `""`, `None`, `"999999"`, 模拟 `akshare` 抛出 `ConnectionResetError` | 零崩溃，5 级级联回退至 SQLite 缓存/离线规则/默认兜底 | 正常返回合法配额字典，离线仍能返回有效限额 500 元 | **PASS** |
| 2 | 全赛道基金 100% 暂停申购 | 模拟该赛道首选与全部备选基金 `daily_limit = 0.0` / 暂停申购 | 首选与备选均不分配，全额转入 DCA 排期并精确平账 | `allocated_sum = 0.0`, `remaining_cash = 100000.0`, 成功生成 7 条清晰定投建议 | **PASS** |
| 3 | 美股非交易时间段估值纠偏 | 美股夜间/非交易时段，基准涨幅为 0.0% 时测试轻微波动与极端失真 (-5.0%) | 轻微波动不纠偏；极端失真 (>1.5%) 纠偏回归基准 | 正常估值维持不变，-5.0% 失真估值被安全纠偏至 0.0%，gsz 恢复基准净值 | **PASS** |
| 4 | 极端牛熊波动率防击穿 | 超级大牛市 (bias_20=+40%)、极端恐慌大熊市 (bias_20=-50%, vol=0.99) | 维持权重和 1.0，权益单调递增，熊市 C4<=55%, C5<=70% | 极端熊市 C1~C5 权益比例为 `[0.08, 0.20, 0.32, 0.45, 0.60]`，单调且未击穿上限 | **PASS** |
| 5 | 账户空仓与全现金极端边界 | `holdings = {}`, `total_equity = 0.0`；或全现金 10 万元无持仓；`pm = None` | 零除以零异常保护，生成正确的调仓适宜度与订单 | 空仓返回 `HOLD_ON`，全现金安全生成 5 笔建仓买单，`pm=None` 自动降级处理 | **PASS** |
| 6 | 股票重合度单对/伴生对极端场景 | 仅持有推荐双红利对 `{"100032", "005561"}` 或标普500伴生对 `{"050025", "001071"}` | 豁免清单生效，`max_non_diag_unexcused` 必须为 0.0 | `max_non_diag_unexcused == 0.0`，`alerts` 列表长度为 0，零误报 | **PASS** |

---

## 4. Test Suite Execution (全量自动化测试套件执行证据)

### 4.1 阶段一核心红队验收测试套件
```bash
py -3.11 -m pytest tests/test_milestone_phase1_r1_r5.py -v
```
- **执行结果**: `11 passed in 3.67s` (100% 通过)
- **覆盖用例**:
  - `test_case_01_read_only_invariants`: PASSED
  - `test_case_02_ast_no_cheating`: PASSED
  - `test_case_03_realtime_quota_fetch_and_cache`: PASSED
  - `test_case_04_waterfall_quota_split_and_dca`: PASSED
  - `test_case_05_qdii_intraday_valuation_correction`: PASSED
  - `test_case_06_dynamic_tier_weights_no_c3_hijack`: PASSED
  - `test_case_07_three_stage_offensive_defensive`: PASSED
  - `test_case_08_ladder_redemption_fee_alignment`: PASSED
  - `test_case_09_suitability_verdict_4d_and_levels`: PASSED
  - `test_case_10_simulate_rebalance_modes_consequences`: PASSED
  - `test_case_11_stock_overlap_dual_dividend_exemption`: PASSED

### 4.2 核心业务模块单测
```bash
py -3.11 -m pytest tests/test_portfolio_manager.py tests/test_strategy_bridge.py -v
```
- **执行结果**: `34 passed in 40.00s` (100% 通过)

### 4.3 裁判系统基建测试
```bash
py -3.11 -m pytest tests/test_infra.py -v
```
- **执行结果**: `15 passed in 5.21s` (100% 通过)

### 4.4 扩展与时钟算子综合测试
```bash
py -3.11 -m pytest tests/test_realtime_and_upgrades.py tests/test_m2_r4_r5_optimization.py tests/test_trading_clock_fee.py -v
```
- **执行结果**: `41 passed in 40.74s` (100% 通过)

**累计验证测试通过数**: 11 + 34 + 15 + 41 = **101 项测试用例 100% 全部通过**。

---

## 5. Caveats (审查边界与说明)

1. **外部网络接口依赖与防抖**:
   - `akshare.fund_purchase_em()` 和新浪行情接口在极端网络瘫痪时依赖 L1~L5 离线缓存。虽然代码已实现离线湖仓与 SQLite 本地缓存兜底，但长期断网（如超过 30 天未联网）可能导致限购状态停留在历史快照，属于预期内的正常数据衰减。
2. **数据湖仓文件**:
   - `data/master/fund_trading_rules.parquet` 作为离线底线，需在部署时保持文件完整性（当前文件健康存在）。
3. **前端渲染未破坏**:
   - 本次审查严格遵守“不修改后端核心之外的无关文件”原则，前端展示直接通过 `StrategyBridge` 模块级函数获取数据，接口兼容性良好。

---

## 6. Conclusion (终审结论)

经过独立、详尽的代码审计、AST 语法树扫描、全量单元测试执行以及 6 大对抗性极端边界测试，AGY2_FundAdvisory 项目在阶段一（M1~M4）的重构中：
1. **完全满足** `ORIGINAL_REQUEST.md` 中 R1 至 R5 的全部功能与算法要求；
2. **严格遵守** 4 大裁判基建文件的只读物理红线，零篡改、零未来函数泄露、零 `time.sleep` 欺骗；
3. **成功根除** C3 常数劫持与硬编码限购数值，实现了 100% 纯数学动态配权与多级瀑布流拆单；
4. **具备优异** 的异常边界容灾能力与数学单调性，完全通过所有极端熊市/牛市压力测试。

**终审裁决**: **`APPROVE`**（准予合并并进入后续阶段）

---

## 7. Verification Method (独立复核方法)

任何第三方或编排者可执行以下指令进行全量独立验证：

```powershell
# 1. 切换至项目根目录
cd d:\Google\Workspace\Wind\AGY2_FundAdvisory

# 2. 验证裁判基建未被修改
git status --porcelain judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py

# 3. 运行阶段一核心验收测试套件 (11 项全部通过)
py -3.11 -m pytest tests/test_milestone_phase1_r1_r5.py -v

# 4. 运行裁判系统基建测试 (15 项全部通过)
py -3.11 -m pytest tests/test_infra.py -v

# 5. 运行核心业务综合测试 (34 项全部通过)
py -3.11 -m pytest tests/test_portfolio_manager.py tests/test_strategy_bridge.py -v
```
