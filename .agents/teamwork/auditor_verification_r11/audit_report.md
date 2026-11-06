# 司法取证级法医审计报告 (Forensic Audit Report)

**Work Product**: AGY2 实盘基金投顾系统与买方投顾模型闭环 (`AGY2_FundAdvisory/`, `tests/`)
**Auditor**: Forensic Auditor (Archetype: `forensic_auditor`, ID: `95db8632-cdda-4e34-bc96-3eb4c12a1afd`)
**Profile**: General Project
**Integrity Mode**: Development (严格依从 `ORIGINAL_REQUEST.md` 第 8 行)
**Verdict**: **CLEAN**

---

## 1. 审计概要与执行准则

本审计作为独立司法取证级法医审计，严格遵循以下原则：
- **Trust Nothing, Verify Everything**：不信任任何声称通过的结论，所有检查项均由审计员在当前物理环境下独立运行工具并提取底层哈希、源码与运行日志。
- **Ground-Truth Precedence**：以 `ORIGINAL_REQUEST.md` 约束为最高基准。
- **2-Phase Investigation Architecture**：第一阶段客观观测全量事实，第二阶段依据 Development 模式及物理安全红线实施判定。

---

## 2. 核心红线逐项取证与核验结果

### 专项 1：四大只读裁判文件物理完整性与 SHA256 哈希审计 (PASS)
- **审计目标**：验证 `judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py` 未被任何提交或未提交变更篡改。
- **取证命令 1 (Git 状态)**：
  ```powershell
  git diff HEAD -- AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md tests/test_infra.py AGY2_FundAdvisory/tests/test_infra.py
  ```
  **输出结果**：Diff 输出为空（0 行变动）。
- **取证命令 2 (Git 历史最近提交核查)**：
  ```powershell
  git log -n 5 --stat -- tests/test_infra.py AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md
  ```
  **输出证据**：四大裁判文件最后修改记录为 `c0cdb4e`（2026-10-30），后续历次业务迭代提交（包含 `fb23933`、`4dbab73`、`1f28b9b`、`ff99aba`、`63c4f00`）对其改动均为 0。
- **取证命令 3 (SHA256 物理哈希计算)**：
  ```powershell
  Get-FileHash -Algorithm SHA256 AGY2_FundAdvisory/judge_engine.py, AGY2_FundAdvisory/holdout_vault.py, AGY2_FundAdvisory/AGENT_SPEC.md, tests/test_infra.py, AGY2_FundAdvisory/tests/test_infra.py | Format-List
  ```
  **哈希证据链**：
  | 文件路径 | 算法 | SHA256 物理指纹 | 状态 |
  |---|---|---|---|
  | `AGY2_FundAdvisory/judge_engine.py` | SHA256 | `76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF31CC07BE` | **UNTOUCHED** |
  | `AGY2_FundAdvisory/holdout_vault.py` | SHA256 | `88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670BD031D2A` | **UNTOUCHED** |
  | `AGY2_FundAdvisory/AGENT_SPEC.md` | SHA256 | `A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B800CD63957` | **UNTOUCHED** |
  | `tests/test_infra.py` | SHA256 | `48BEE0DA300D7C0A0848EC1376E4B9B2E55224D2736081713B4340F0362CD100` | **UNTOUCHED** |
  | `AGY2_FundAdvisory/tests/test_infra.py` | SHA256 | `B8D781BE8135BE05CF61E62E4B534E359985AD880F27FFB61228A33DF6B02A6A` | **UNTOUCHED** |

---

### 专项 2：DataLoader.simulate_execution 默认签名与扣费逻辑审计 (PASS)
- **审计目标**：核验执行模拟算子 `simulate_execution` 签名与手续费扣除逻辑未被弱化或绕过。
- **源码审查 (`AGY2_FundAdvisory/data_loader.py` 第 1100~1215 行)**：
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
- **扣费机制审查**：
  1. `w_exec = w_df[asset_cols].shift(1)`：严格执行 T+1 次日确认机制；
  2. 买入交易：扣除 `dw * etf_impact` 冲击成本并记录买入时间戳；
  3. 卖出交易：严格根据持有天数与份额类别执行阶梯扣费：
     - `holding_days < penalty_days` (7天)：扣除 `penalty_rate` (1.50%) 严厉惩罚性赎回费；
     - `holding_days < 30` 天：C类 0.50% / A类 0.75%；
     - `holding_days < 180` 天：A类 0.50%，C类免赎回费 0.00%；
     - `holding_days < 365` 天：A类 0.25%，C类免赎回费 0.00%；
     - `>= 365` 天：免赎回费 0.00%；
  4. 净值更新：`cur_nav = cur_nav * (1.0 + day_ret) * (1.0 - friction)`，摩擦成本真实扣减入净值。
- **Git 变更审查**：该函数自 `0baa50c`（11月1日）以来未发生任何变动，签名与逻辑 100% 保持原样。

---

### 专项 3：拒绝假计算与常数硬编码审计 (PASS)
- **审计目标**：审查 `StrategyBridge.calculate_portfolio_yield_cushion` 与 `pm.evaluate_rebalance_audit` 是否存在写死常数（如固定 +1.2% 超额、固定 500 元手续费）或作弊表象。
- **审查证据 1 (`StrategyBridge.calculate_portfolio_yield_cushion`)**：
  - 代码位置：`AGY2_FundAdvisory/strategy_bridge.py` 第 1961~2047 行。
  - 逻辑分析：
    - 采用 R4 标准基准字典（红利低波 5.20%、红利高股息 4.80%、核心蓝筹 2.80%、中盘均衡 1.80%、中小盘成长 1.00%、科技成长进攻 0.60%、纯债固收 2.75%、美股海外对冲 1.30%、黄金对冲 0.00%）。
    - 动态解析 `weights_or_holdings` 中的每项标的市值 `mv` 与权重 `w = mv / tot_cap`。
    - 动态调用 `pm.classify_fund_asset_class(fc, fn)` 反查大类。
    - 严格按加权公式计算：`weighted_yield += w * y_rate`；
    - `annual_cushion_amount = tot_cap * (weighted_yield_pct / 100.0)`；
    - `monthly_equivalent_amount = annual_cushion_amount / 12.0`；
    - `cash_dividend_payout_est` 动态累加标的分红方式为 `cash` 的现金分红预期。
    - **无任何写死常数或假计算**。
- **审查证据 2 (`PortfolioManager.evaluate_rebalance_audit`)**：
  - 代码位置：`AGY2_FundAdvisory/portfolio_manager.py` 第 6267~6324 行。
  - 逻辑分析：
    - `current_actual_equity = float(self.total_equity or 0.0)`；
    - `shadow_equity = init_cash + sum(init_shares * latest_current_nav)`，保持接管首日份额不变动态乘以此标的今日最新净值；
    - `rebalance_value_add = round(cur_actual - shadow_equity, 2)`；
    - `saved_penalty_and_buffer_fees` 遍历持仓批次，对持有不足 7 天批次精准核算 `b.shares * nav * 0.0150`，对持有 7~30 天的 C 类标的精准核算 `market_value * 0.0050`。
- **实证测试验证 (`tests/test_adv_final_closure.py` 第 58~131 行)**：
  - 审计员运行测试实证：当修改标的 `current_nav` 从 1.50 -> 1.80 -> 2.00 时，影子资产与实盘资产严格按照动态数学关系发生线性联动，无任何常数硬编码迹象。

---

### 专项 4：Streamlit 安全与 @st.fragment 隔离审计 (PASS)
- **审计目标**：扫描 `AGY2_FundAdvisory/app_gui.py` 中 `fragment` 的使用情况，确认绝不在 `st.sidebar` 内部或影响侧边栏的函数上使用，杜绝 StreamlitAPIException 崩溃。
- **扫描结果**：
  - 执行全局文本正则扫描：`Select-String -Path AGY2_FundAdvisory/app_gui.py -Pattern "fragment"`
  - 命中行数：**0 行**。
  - 结果确认：`app_gui.py` 内部未在 `st.sidebar` 调用任何 `@st.fragment`。
- **运行时探针与渲染测试**：
  - 守护进程端口检测：`netstat -ano | findstr 8501` -> PID 5152 `LISTENING`；
  - HTTP 健康探针：`http://127.0.0.1:8501/_stcore/health` -> HTTP 200 ok；
  - 自动化 AppTest 渲染测试：`tests/test_streamlit_apptest_run.py` 运行通过（1 passed in 9.03s），全站 4 个 Tab 零异常报错。

---

## 3. 独立自动化测试套件回归结果

审计员在无任何 mock 干扰的环境下独立执行全部核心验证套件，结果如下：

| 测试文件 | 用例数 | 耗时 | 结果 | 关键验证点 |
|---|---|---|---|---|
| `tests/test_infra.py` | 14 passed | 7.18s | **PASS** | 只读裁判基线、风控模型与基础基础设施完整性 |
| `tests/test_adv_final_closure.py` | 3 passed | 1.23s | **PASS** | 9 大标准大类覆盖(0 其他权益)、股息垫与影子复盘真实数学联动、热重载导入安全 |
| `tests/test_adv_upgrade_suite.py` | 17 passed | 1.40s | **PASS** | 账本管理、同公司转换、FIFO 批次、动态调仓路径与边界安全 |
| `tests/test_anticheat_suite.py` | 11 passed | 24.74s | **PASS** | 防作弊多账本隔离、动态 14 板块真实行情联动与反欺诈断言 |
| `tests/test_streamlit_apptest_run.py` | 1 passed | 9.03s | **PASS** | Streamlit AppTest 全站无异常白屏、Tab 渲染安全 |

---

## 4. 模式特异性判定 (Phase 2 Mode-Specific Flagging)

依据 `ORIGINAL_REQUEST.md` 第 8 行，项目当前处于 **Development Mode**。

| 审查维度 | 规范要求 | 审计实测发现 | 违规判定 |
|---|---|---|---|
| Hardcoded test results | 严禁写死测试预期结果伪造通过 | 收益与股息垫随 NAV 真实变化，测试用例无固定常数硬编码 | ✅ CLEAN |
| Facade implementations | 严禁空壳函数或固定返回值假实现 | 资产分类器覆盖 9 大类，调仓复盘遍历批次与最新净值 | ✅ CLEAN |
| Fabricated verification outputs | 严禁伪造测试日志或历史凭证 | 审计员独立运行 pytest 与 http 探针并核实 200 ok | ✅ CLEAN |
| 裁判文件物理安全 | 严禁修改 4 大只读文件 | 4 大裁判文件 SHA256 完好，修改行为为 0 | ✅ CLEAN |
| 回测模拟算子安全 | 严禁改动 simulate_execution 签名与扣费 | 签名完整，1.50% 惩罚费与阶梯费率扣除机制完备 | ✅ CLEAN |

---

## 5. 终审裁决

**VERDICT: CLEAN**

本工作产品物理红线完好、计算逻辑纯净由真实数学公式驱动、测试套件 100% 真实绿灯通过，无任何伪造、作弊或完整性违规行为。准予验收。
