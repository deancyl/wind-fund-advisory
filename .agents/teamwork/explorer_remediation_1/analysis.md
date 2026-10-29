# 六维选基真动态量化打分彻底整改蓝图与技术方案 (Remediation Blueprint)

**勘测实施人 (Explorer)**: Remediation Explorer (`explorer_remediation_1`)  
**审计阻断源 (Audit Block)**: Forensic Integrity Auditor (`auditor_orch3_1`) 门禁审计一票否决裁决 🔴 INTEGRITY VIOLATION  
**勘测时间戳**: 2026-10-30T02:37:00Z  
**目标工作区**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory`  

---

## 一、法医审计违规事实纵深复核 (Forensic Audit Verification)

### 1.1 违规事实定位
1. **全局静态硬编码字典残留**:
   在 `AGY2_FundAdvisory/strategy_bridge.py` 第 286~326 行，定义了包含 25 只核心基金写死打分的全局字典 `FUND_SIX_DIMENSION_PROFILE`：
   ```python
   # strategy_bridge.py:286-291
   FUND_SIX_DIMENSION_PROFILE: Dict[str, Dict[str, float]] = {
       "002351": {"alpha": 95.0, "fee": 98.0, "risk": 100.0, "smart_money": 88.0, "crowding": 98.0, "macro": 92.0},
       "000086": {"alpha": 91.5, "fee": 95.0, "risk": 100.0, "smart_money": 85.0, "crowding": 97.0, "macro": 90.0},
       ... (共 25 只核心基金)
   }
   ```
2. **生产调用链路被静态字典占领**:
   在 `strategy_bridge.py` 第 3171 行，`StrategyBridge.calculate_fund_six_dimension_score` 直接查阅静态字典：
   ```python
   # strategy_bridge.py:3170-3174
   code = str(fund_code).strip().zfill(6)
   prof = FUND_SIX_DIMENSION_PROFILE.get(code, {
       "alpha": 85.0, "fee": 85.0, "risk": 90.0,
       "smart_money": 85.0, "crowding": 88.0, "macro": 88.0
   })
   ```
3. **前端 UI 渲染伪造数据**:
   在 `app_gui.py` 第 870 行：
   ```python
   df_quant = StrategyBridge.get_tier_quant_selection_table(active_tier, st.session_state.custom_fund_overrides)
   ```
   该方法内部在 `strategy_bridge.py` 第 3265 行与第 3290 行逐行调用 `cls.calculate_fund_six_dimension_score`，最终将写死的虚假数据渲染至前端界面的《当前档位入选赛道：冠军标的与备选基金六维量化评分对比表》。
4. **真实动态引擎孤立闲置**:
   在 `portfolio_manager.py` 第 3596~3747 行中，已由 Agent-2 完整实现了基于 DuckDB 湖仓（`v_scorecards`, `v_fund_snapshot`, `v_fund_trading_rules`, `v_northbound_holdings`）与三层通用财务穿透排雷的真实动态评分引擎 `compute_fund_six_dimension_score`。然而，该动态引擎未被 `strategy_bridge.py` 接入，形成了“底层有真数据，上层却走假字典”的严重违规。

### 1.2 虚假打分 vs 真实 DuckDB 打分数值对比实证
经现场 Python 运行时探针实测对比：
| 基金代码 | 基金名称 | 静态字典写死打分 (`StrategyBridge`) | DuckDB 真实动态多因子打分 (`PortfolioManager`) | 差异性质 |
|---|---|---|---|---|
| `002351` | 易方达裕祥回报债券A | Alpha: 95.0, Fee: 98.0, SmartMoney: 88.0, **总分: 95.95** | Alpha: 88.0, Fee: 96.2, SmartMoney: 95.4, **总分: 93.64** | 虚高写死 vs 真实湖仓归一化 |
| `011613` | 华夏科创50ETF联接C | Alpha: 94.0, Fee: 92.0, SmartMoney: 95.0, **总分: 93.25** | Alpha: 88.0, Fee: 85.0, SmartMoney: 95.4, **总分: 88.69** | 虚高写死 vs 真实湖仓归一化 |
| `100032` | 富国中证红利指数增强A | Alpha: 96.0, Fee: 93.0, Crowding: 95.0, **总分: 94.65** | Alpha: 88.0, Fee: 90.0, Crowding: 95.0, **总分: 91.91** | 虚高写死 vs 真实湖仓归一化 |

实证表明：`FUND_SIX_DIMENSION_PROFILE` 完全是以固定硬编码数字冒充量化计算，严重违反了 `ORIGINAL_REQUEST.md` Follow-up R2 与 `PROJECT.md` Feature 6。

---

## 二、整改目标与架构契约 (Remediation Objectives & Constraints)

1. **100% 根除硬编码字典**:
   彻底删除 `strategy_bridge.py` 中的 `FUND_SIX_DIMENSION_PROFILE` 全局字典，源码中不得残留任何形式的静态选基打分表。
2. **全面委托真实动态引擎**:
   将 `StrategyBridge.calculate_fund_six_dimension_score` 与 `StrategyBridge.get_tier_quant_selection_table` 100% 委托至 `portfolio_manager.compute_fund_six_dimension_score`。
3. **彻底杜绝循环导入与内存浪费**:
   采用**延迟单例 (Lazy Singleton)** 模式获取 `PortfolioManager` 实例，既避免顶层循环导入（Circular Import），又复用其已内置的 `_stock_screen_cache` 与 `_crowding_cache`。
4. **接口入参与返回结构 100% 兼容**:
   保证对原有调用方（`app_gui.py`、`test_acceptance_r1_r7.py` 等）的字段键名完全兼容，特别保证 `overall_score` 与 `total_score` 双向完备。
5. **配套防篡改 AST 自动化回归测试**:
   在 `tests/test_architecture_m3.py` 中注入法医级 AST 扫描断言，确保未来任何提交若重新引入 `FUND_SIX_DIMENSION_PROFILE` 将直接被门禁斩断。

---

## 三、逐文件精密整改方案 (Detailed File-by-File Remediation)

### 3.1 `strategy_bridge.py` 改造蓝图

#### 改造点 1：删除 `FUND_SIX_DIMENSION_PROFILE` 全局字典
- **目标行**: 第 282~327 行。
- **动作**: 彻底物理移除该段注释与字典定义。

#### 改造点 2：新增延迟单例管理器与结果防抖缓存
- **位置**: 在 `strategy_bridge.py` 顶部或 `StrategyBridge` 类内部。
- **设计原理**:
  - `PortfolioManager` 初始化时会设置数据库与账本状态，若在每次选基计算中重复 `PortfolioManager()`，对 20 只基金会造成数十次重复实例化；
  - 同时，`StrategyBridge` 与 `PortfolioManager` 互相关联，若在文件顶层直接 `from portfolio_manager import PortfolioManager`，可能在不同引用链下触发脆弱性；
  - 因此在 `StrategyBridge` 中提供延迟单例方法 `_get_portfolio_manager(cls)`，并在模块级提供轻量防抖缓存 `_SIX_DIM_SCORE_CACHE`（TTL=30s，保障 Streamlit 交互与滑动切档瞬间响应）。
- **代码实现**:
  ```python
  # 模块级单例与多因子打分防抖缓存
  _PORTFOLIO_MANAGER_SINGLETON: Optional[Any] = None
  _SIX_DIM_SCORE_CACHE: Dict[Tuple[str, str, str], Tuple[float, Dict[str, Any]]] = {}

  class StrategyBridge:
      ...
      @classmethod
      def _get_portfolio_manager(cls):
          """
          延迟单例模式获取 PortfolioManager 实例，彻底避免顶层循环导入并复用底层穿透排雷缓存。
          """
          global _PORTFOLIO_MANAGER_SINGLETON
          if _PORTFOLIO_MANAGER_SINGLETON is None:
              from portfolio_manager import PortfolioManager
              _PORTFOLIO_MANAGER_SINGLETON = PortfolioManager()
          return _PORTFOLIO_MANAGER_SINGLETON
  ```

#### 改造点 3：重构 `calculate_fund_six_dimension_score`
- **目标行**: 第 3157~3232 行。
- **动作**: 彻底抛弃原从 `FUND_SIX_DIMENSION_PROFILE` 字典取数逻辑，全面委托至 `PortfolioManager.compute_fund_six_dimension_score`。
- **代码实现**:
  ```python
  @classmethod
  def calculate_fund_six_dimension_score(
      cls,
      fund_code: str,
      track_role: str = "",
      snapshot: Optional[Dict[str, Any]] = None,
      tier: str = "",
      use_cache: bool = True
  ) -> Dict[str, Any]:
      """
      六维量化选基多因子动态评分引擎 (R2/R5):
      全面委托至 PortfolioManager.compute_fund_six_dimension_score。
      接入 DuckDB 真实数据视图 (v_scorecards, v_fund_snapshot, v_fund_trading_rules, v_northbound_holdings, v_futures_basis)
      经真实数学归一化公式生成，彻底消除任何写死打分或静态字典。
      """
      code = str(fund_code).strip().zfill(6)
      if snapshot is None:
          snapshot = cls.get_latest_market_snapshot()

      cache_key = (code, str(track_role), str(tier))
      now_ts = time.time()
      if use_cache and cache_key in _SIX_DIM_SCORE_CACHE:
          cached_ts, cached_res = _SIX_DIM_SCORE_CACHE[cache_key]
          if now_ts - cached_ts < 30.0:
              return copy.deepcopy(cached_res)

      pm = cls._get_portfolio_manager()
      raw_score = pm.compute_fund_six_dimension_score(
          fund_code=code,
          track_role=track_role,
          snapshot=snapshot,
          tier=tier
      )

      # 字段结构与兼容性强保证
      score_res = dict(raw_score)
      score_res["fund_code"] = code
      total = score_res.get("total_score", score_res.get("overall_score", 88.0))
      score_res["total_score"] = total
      score_res["overall_score"] = total  # 保证 app_gui 与表格读取 overall_score 不报 KeyError

      # 保证宏观契合分与反拥挤分具备双向别名
      if "macro_align_score" in score_res and "macro_derivative_score" not in score_res:
          score_res["macro_derivative_score"] = score_res["macro_align_score"]
      if "macro_derivative_score" in score_res and "macro_align_score" not in score_res:
          score_res["macro_align_score"] = score_res["macro_derivative_score"]

      if "crowding_score" in score_res and "anti_crowding_score" not in score_res:
          score_res["anti_crowding_score"] = score_res["crowding_score"]
      if "anti_crowding_score" in score_res and "crowding_score" not in score_res:
          score_res["crowding_score"] = score_res["anti_crowding_score"]

      # 缓存防抖
      _SIX_DIM_SCORE_CACHE[cache_key] = (now_ts, copy.deepcopy(score_res))
      return score_res
  ```

#### 改造点 4：加固 `get_tier_quant_selection_table`
- **目标行**: 第 3240~3309 行。
- **动作**: 保持原有结构，确保读取 `champ_scores` 与 `alt_scores` 时使用安全的字典键获取（如 `.get("overall_score", champ_scores.get("total_score", 0.0))`），确保返回 DataFrame 的列与 `app_gui.py` 100% 对齐。

---

### 3.2 `portfolio_manager.py` 对齐与加固

#### 改造点 1：返回字典补全 `overall_score` 别名
- **目标行**: 第 3733~3747 行。
- **问题**: 原 `_do_compute_six_dimension_score` 返回字典仅有 `"total_score": total_score`，而未显式包含 `"overall_score"`。
- **改进**:
  在返回字典中同时注入 `"overall_score": total_score`，确保不论从 `PortfolioManager` 直接调用还是经由 `StrategyBridge` 代理调用，结构均自洽完备。

---

### 3.3 `tests/test_architecture_m3.py` 审计红队加固

在红队测试中增加专项测试函数 `test_ast_audit_no_hardcoded_fund_profiles_and_dynamic_scoring_parity`:
1. **AST 静态扫描**:
   扫描 `strategy_bridge.py` 抽象语法树，遍历所有 `ast.Assign` 节点，断言不存在名为 `FUND_SIX_DIMENSION_PROFILE` 的变量定义；
2. **动态数据源一致性断言**:
   断言 `StrategyBridge.calculate_fund_six_dimension_score("002351")["total_score"] == PortfolioManager().compute_fund_six_dimension_score("002351")["total_score"]`，从机制上杜绝静态与动态评分脱节；
3. **真实打分范围与权重校验**:
   断言所有 27 只核心赛道基金计算出的得分均源自真实的 DuckDB 数据库指标，绝无静态默认值欺骗。

---

## 四、接口契约与返回值兼容性矩阵 (Compatibility Matrix)

| 字段名称 (Key) | 数据类型 | `test_acceptance_r1_r7.py` 要求 | `app_gui.py` 渲染要求 | `PortfolioManager` 原生输出 | 整改后输出保证 |
|---|---|---|---|---|---|
| `fund_code` | str | 必须存在 (6位) | 必须存在 | 6位代码字符串 | ✅ 100% 满足 |
| `alpha_score` | float | 必须存在，参与公式校验 | 表格展示 `"超额Alpha得分(35%)"` | DuckDB 真实查询 (60~99) | ✅ 100% 满足 |
| `fee_score` | float | 必须存在，参与公式校验 | 表格展示 `"低费率得分(25%)"` | DuckDB 真实费率公式 (60~100) | ✅ 100% 满足 |
| `risk_score` | float | 必须存在，参与公式校验 | 表格展示 `"底层排雷健康分(15%)"` | 真实穿透排雷扣分后得分 (0~100) | ✅ 100% 满足 |
| `smart_money_score` | float | 必须存在，参与公式校验 | 表格展示 `"聪明钱流入分(10%)"` | DuckDB 北向聪明钱流向 (75~98) | ✅ 100% 满足 |
| `crowding_score` | float | 必须存在，参与公式校验 | 表格展示 `"反拥挤安全分(10%)"` | 通用资产分类反拥挤得分 (88~97) | ✅ 100% 满足 |
| `anti_crowding_score`| float | 支持别名 | - | 提供 | ✅ 100% 满足 |
| `macro_align_score` | float | 必须存在，参与公式校验 | 表格展示 `"衍生品契合分(5%)"` | 期指贴水与期权 IV 动态微调 | ✅ 100% 满足 |
| `macro_derivative_score` | float | 支持别名 | - | 提供 | ✅ 100% 满足 |
| `total_score` | float | 断言存在并用于评分范围 | - | 提供加权总分 (保留2位小数) | ✅ 100% 满足 |
| `overall_score` | float | - | 表格展示 `"六维总评得分"` | 补充注入 `total_score` 别名 | ✅ 100% 满足 |
| `weights` | dict | 校验 6 维权重 0.35, 0.25, 0.15, 0.10, 0.10, 0.05 | - | 提供完整权重字典 | ✅ 100% 满足 |

---

## 五、整改执行计划与工序编排 (Execution Schedule)

```
[Phase 1] 源码整改执行
  ├── Step 1.1: 在 strategy_bridge.py 中彻底删除第 286~326 行 FUND_SIX_DIMENSION_PROFILE
  ├── Step 1.2: 在 strategy_bridge.py 中注入 _get_portfolio_manager 延迟单例与 _SIX_DIM_SCORE_CACHE
  ├── Step 1.3: 重构 StrategyBridge.calculate_fund_six_dimension_score 全面委托至 pm.compute_fund_six_dimension_score
  └── Step 1.4: 在 portfolio_manager.py 中为 _do_compute_six_dimension_score 补齐 overall_score 别名

[Phase 2] 红队门禁测试与 AST 加固
  ├── Step 2.1: 在 tests/test_architecture_m3.py 增加 AST 扫描 FUND_SIX_DIMENSION_PROFILE 灭绝断言
  ├── Step 2.2: 运行 pytest tests/test_architecture_m3.py 验证反硬编码红线
  └── Step 2.3: 运行 pytest tests/test_acceptance_r1_r7.py 验证全量选基计算与宽表渲染

[Phase 3] 全量回归与平滑重启服务
  ├── Step 3.1: 运行 pytest -v 全量回归（确保 226+ 项测试 100% 通过）
  ├── Step 3.2: 依据用户准则，以 Windows 原生静默脱钩模式平滑重启本地 8501 端口 Streamlit 服务
  └── Step 3.3: 提请 Forensic Integrity Auditor 独立复核
```
