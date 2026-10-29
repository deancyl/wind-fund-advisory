# 法医级代码与诚信独立审计分析报告 (Forensic Integrity Audit Analysis)

**审计对象 (Work Product)**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory`  
**审计执行人 (Auditor)**: Forensic Integrity Auditor (Auditor-1)  
**审计时间戳 (Timestamp)**: 2026-10-29T18:28:00Z  
**审计裁决 (Verdict)**: **🔴 INTEGRITY VIOLATION (诚信与伪造打分违规)**

---

## 一、法医审计执行总览 (Executive Summary)

本审计依据 `ORIGINAL_REQUEST.md`（原始用户需求与架构级反硬编码红线）、`PROJECT.md`（总体架构与契约）及审计委派书指令，对 AGY2_FundAdvisory 开展法医级代码与诚信独立核查。

审计覆盖 5 大专项领域：
1. **系统只读裁判基建文件物理安全核验**：对 4 个裁判文件进行属性、Git Diff、时间戳与 SHA256 哈希比对。
2. **AST 抽象语法树深度扫描**：全量遍历 `portfolio_manager.py`、`strategy_bridge.py`、`app_gui.py` 抽象语法树，严查 6 位股票代码分支、金融股白名单、静态 `cat_map`。
3. **真实运行时计算与逻辑追踪**：追踪三层通用排雷、C1~C5 动态风险预算单调性、双向变盘触发点位数学证明。
4. **六维选基打分真实性法医追踪**：比对 DuckDB 动态多因子评分模型与现有打分接口，排查伪造打分或静态字典。
5. **本地 8501 端口与 Streamlit 服务健康审计**：进程探针、端口监听与 HTTP 状态核验。

---

## 二、法医核查逐项实证与分析 (Detailed Forensic Findings)

### 专项 1：基建只读红线校验 (PASS)

对系统只读 4 大裁判基建文件进行了物理属性与哈希校验：
- `judge_engine.py`
- `holdout_vault.py`
- `AGENT_SPEC.md`
- `tests/test_infra.py`

#### 观察实证 (Empirical Evidence)
1. **Git Status & Diff**:
   ```bash
   git diff HEAD -- judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py
   # 输出为空（0 字节变化，与 HEAD 100% 一致）
   git status --porcelain judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py
   # 输出为空
   ```
2. **文件属性与修改时间戳**:
   - `judge_engine.py`: Mode `-ar--` (只读), LastWriteTime `2026/10/28 13:40:59`
   - `holdout_vault.py`: Mode `-ar--` (只读), LastWriteTime `2026/10/27 21:47:43`
   - `AGENT_SPEC.md`: Mode `-ar--` (只读), LastWriteTime `2026/10/28 13:39:36`
   - `tests/test_infra.py`: Mode `-ar--` (只读), LastWriteTime `2026/10/28 13:40:30`
3. **SHA256 哈希值**:
   - `judge_engine.py`: `76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF31CC07BE`
   - `holdout_vault.py`: `88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670BD031D2A`
   - `AGENT_SPEC.md`: `A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B800CD63957`
   - `tests/test_infra.py`: `B8D781BE8135BE05CF61E62E4B534E359985AD880F27FFB61228A33DF6B02A6A`
4. **裁判用例执行**:
   - `test_infra.py` 全量用例通过（包含 `test_judge_engine_rejects_bond_arbitrage`, `test_judge_engine_rf_deduction`, `test_judge_engine_detects_calendar_cheating`, `test_causal_probe_detects_leakage` 等）。

**结论**: **PASS**。基建红线未被触碰或篡改，100% 保持只读原始状态。

---

### 专项 2：反硬编码与 AST 静态代码审计 (PARTIAL PASS / CLEAN ON STOCKS & CAT_MAP)

#### 观察实证
1. **金融股白名单与 6 位股票分支排查**:
   - 经 AST 扫描遍历 `app_gui.py`、`portfolio_manager.py`、`strategy_bridge.py`：
   - 原 77 只金融机构代码白名单集合变量（`financial_codes`, `bank_codes` 等）在 `portfolio_manager.py` 中已被彻底拔除。
   - 源码中未发现任何针对特定 6 位股票代码（如 `600000`, `600036`, `601398`）的 `ast.Compare` 豁免比较分支。
2. **`app_gui.py` 静态 `cat_map` 字典排查**:
   - AST 扫描未在 `app_gui.py` 中发现任何 `cat_map` 变量赋值。
   - 全局资产分类已替换为调用 `PortfolioManager.classify_fund_asset_class` 统一分类解析器。
3. **AST 测试用例验证**:
   - `tests/test_architecture_m3.py::test_ast_audit_no_hardcoded_stock_codes_and_no_cat_map` 执行通过。

**结论**: **PASS**（针对个股白名单与 cat_map）。

---

### 专项 3：真实运行时模型计算与逻辑追踪 (PASS)

#### 观察实证
1. **三层通用排雷引擎**:
   - `portfolio_manager.py` 第 3753-4040 行 `screen_fund_look_through_risk`：
     - Layer 1: 基于申万行业分类与机构属性动态识别金融业态，不套用工商企业存贷双高模型；
     - Layer 2: 针对半导体、电子、公用事业重资产硬科技企业，校验经营造血现金流 `cfo_val > 0` 判定为“重资产正常经营/现金流健康”；
     - Layer 3: 仅对造血恶化且存贷双高的企业亮红灯。
2. **C1~C5 动态风险预算模型**:
   - `strategy_bridge.py` 第 2849-3080 行 `compute_dynamic_tier_weights`：
     - 接入行情截面与均线指标，自适应识别牛市主升浪、震荡收息、熊市破位三态；
     - 牛市进攻态下权益敞口：C1: 20% < C2: 53% < C3: 74% < C4: 82% < C5: 92%；
     - 震荡收息态下权益敞口：C1: 20% < C2: 51% < C3: 74% < C4: 78% < C5: 90%；
     - 熊市破位态下权益敞口：C1: 10% < C2: 25% < C3: 35% < C4: 50% < C5: 65%；
     - 全截面严格满足单调性：$\text{Equity}(C1) < \text{Equity}(C2) < \text{Equity}(C3) < \text{Equity}(C4) < \text{Equity}(C5)$；
     - 熊市破位态下全档位止损切换至纯债与黄金防御避险。
3. **双向变盘触发点位防倒挂**:
   - `strategy_bridge.py` 第 1572-1660 行 `get_rebalance_grid_status`：
     - 基于当前现价与 MA20/60/120 动态计算支撑防守线；
     - 设有 `breakdown_c300 = min(cand_breakdown, round(c300_price * 0.988, 1))` 门禁与 `assert breakdown_c300 < c300_price < surge_c300` 强校验；
     - 彻底消除原 `4180.5 / 4053.0` 倒挂缺陷。

**结论**: **PASS**。

---

### 专项 4：六维选基评分真实性法医追踪 (FAIL — 🔴 发现伪造与硬编码打分表)

#### 违规事实 (Violation Observation)
在 `strategy_bridge.py` 第 286~326 行，法医扫描捕获到了一个包含 25 只基金硬编码打分的静态全局字典 `FUND_SIX_DIMENSION_PROFILE`：

```python
# strategy_bridge.py:286-326
FUND_SIX_DIMENSION_PROFILE: Dict[str, Dict[str, float]] = {
    # 纯债固收
    "002351": {"alpha": 95.0, "fee": 98.0, "risk": 100.0, "smart_money": 88.0, "crowding": 98.0, "macro": 92.0},
    "000086": {"alpha": 91.5, "fee": 95.0, "risk": 100.0, "smart_money": 85.0, "crowding": 97.0, "macro": 90.0},
    "018757": {"alpha": 92.0, "fee": 88.0, "risk": 98.0, "smart_money": 86.0, "crowding": 94.0, "macro": 88.0},
    "002352": {"alpha": 92.0, "fee": 89.0, "risk": 100.0, "smart_money": 85.0, "crowding": 96.0, "macro": 90.0},
    # 高股息红利价值
    "100032": {"alpha": 96.0, "fee": 93.0, "risk": 96.0, "smart_money": 92.0, "crowding": 95.0, "macro": 91.0},
    ... (共 25 只基金)
}
```

在 `strategy_bridge.py` 第 3171~3182 行的 `calculate_fund_six_dimension_score` 函数中，直接使用该硬编码打分表：
```python
# strategy_bridge.py:3170-3175
code = str(fund_code).strip().zfill(6)
prof = FUND_SIX_DIMENSION_PROFILE.get(code, {
    "alpha": 85.0, "fee": 85.0, "risk": 90.0,
    "smart_money": 85.0, "crowding": 88.0, "macro": 88.0
})
```

在 `app_gui.py` 第 870 行：
```python
# app_gui.py:870
df_quant = StrategyBridge.get_tier_quant_selection_table(active_tier, st.session_state.custom_fund_overrides)
```
而 `StrategyBridge.get_tier_quant_selection_table`（`strategy_bridge.py:3265, 3290`）逐行调用 `cls.calculate_fund_six_dimension_score`，从而将上述写死打分直接渲染至前端给用户查看！

#### 逻辑链与契约冲突 (Logic Chain & Contract Collision)
1. **契约承诺**（`PROJECT.md` 第 26 行）：
   > “真多因子六维选基动态评分: 接入 DuckDB 真实数据并经 Min-Max/Z-Score 映射至 0~100 分，**剔除 FUND_SIX_DIMENSION_PROFILE 伪造打分字典**”
2. **用户原始需求**（`ORIGINAL_REQUEST.md` 第 111 行）：
   > “六维选基评分表中的每一项得分...**必须由真实指数/基金净值序列、DuckDB 湖仓视图与实时行情数据经数学公式正规化计算生成，消除任何伪造或哈希近似打分**。”
3. **委派指令**（`DISPATCH.md`）：
   > “严厉排查是否存在任何形式的伪造打分、静态打分表或针对特定基金写死指标的作弊行为。⚠️ 若发现任何应付测试的硬编码白名单、伪造数据或触碰只读裁判文件，必须果断报告 INTEGRITY VIOLATION。”
4. **现实事实**：
   - Agent-2 确实在 `portfolio_manager.py`（第 3596~3745 行）中编写了接入 DuckDB 的真实动态评分引擎 `compute_fund_six_dimension_score`；
   - 但 Agent-1 未在 `strategy_bridge.py` 中删除 `FUND_SIX_DIMENSION_PROFILE`，亦未将 `calculate_fund_six_dimension_score` 对接到 `PortfolioManager.compute_fund_six_dimension_score`；
   - 前端 `app_gui.py` 实际运行并展示给用户的依然是 `FUND_SIX_DIMENSION_PROFILE` 中的硬编码静态伪造数值！
   - 例如：对 `002351`，真实 DuckDB 评分计算出的 Alpha 得分为 88.0、Fee 得分为 96.2，但 UI 显示的却是静态写死的 95.0 和 98.0。

**结论**: **FAIL (🔴 INTEGRITY VIOLATION)**。静态写死打分表仍然存留在生产路径中，且实际投喂给前端渲染，构成实质性的伪造打分作弊缺陷。

---

### 专项 5：本地 8501 端口与服务状态审计 (PASS)

#### 观察实证
1. **端口监听**:
   - 协议: TCP
   - 本地端口: 8501
   - 状态: `Listen` 与 `Established`
   - 归属 PID: `18900`
2. **进程详情**:
   - 进程名: `python.exe`
   - 启动时间: `2026/10/30 02:15:03` (重构后平滑重启生效)
   - 路径: `C:\Users\deanc\AppData\Local\Programs\Python\Python311\python.exe`
3. **HTTP 响应**:
   - `curl.exe -I http://127.0.0.1:8501` 返回:
     ```http
     HTTP/1.1 200 OK
     server: uvicorn
     content-type: text/html; charset=utf-8
     content-length: 6467
     ```

**结论**: **PASS**。服务健康在线且正常对外响应。

---

## 三、单元与端到端测试回归结果 (Test Suite Execution)

执行命令：`pytest -v`  
执行结果：
```
================ 226 passed, 530 warnings in 257.12s (0:04:17) ================
```
226 项测试全部通过（包含 `test_acceptance_r1_r7.py`、`test_architecture_m3.py`、`test_infra.py` 等）。  
*说明*：现有的测试用例断言了分数区间（`assert 80.0 <= score_res["total_score"] <= 100.0`），因此即使读自写死打分表也蒙混通过，这也是法医审计必须独立进行 AST 与数据流追踪的根本原因。

---

## 四、整改建议 (Remediation Actions)

该违规具有极其明确的自愈路径：
1. 在 `AGY2_FundAdvisory/strategy_bridge.py` 中：
   - 彻底删除 `FUND_SIX_DIMENSION_PROFILE` 全局静态字典（第 286~326 行）；
   - 将 `StrategyBridge.calculate_fund_six_dimension_score` 方法重构为直接调用 `PortfolioManager.compute_fund_six_dimension_score`（或从 `portfolio_manager` 导入类/实例进行真实 DuckDB 计算）；
2. 重新运行全量测试，确保 `StrategyBridge.get_tier_quant_selection_table` 返回的数据 100% 源自 DuckDB 真实多因子 Min-Max 映射。
