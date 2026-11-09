# Milestone 1 终审与对抗挑战审查报告 (Reviewer & Adversarial Critic Report)

**Reviewer Agent**: reviewer_g13_m1_1  
**Role**: reviewer, critic  
**Target Milestone**: Milestone 1 (痛点 1 因子进化持久化磁盘缓存与痛点 4 Tab 3 回测真实化打假)  
**Worker Under Review**: worker_g13_m1  
**Report Path**: `d:\Google\Workspace\Wind\.agents\teamwork\reviewer_g13_m1_1\handoff.md`  

---

## 审查裁决 (Review Verdict)

**Verdict**: **APPROVE** (通过)  
**诚信合规评估 (Integrity Check)**: 100% 通过（零硬编码造假、零伪实现门面、零绕过逻辑、4 个只读裁判文件零修改）  
**对抗性综合风险 (Adversarial Risk)**: LOW (已完成多维度对抗压力测试，发现 1 项非阻塞性并发写入优化建议)  

---

## 1. Observation (直接观察事实与精确比对证据)

### 1.1 专有文件修改与 4 个只读裁判文件安全底线
- **核验指令**:
  ```powershell
  git status --porcelain judge_engine.py AGY2_FundAdvisory/judge_engine.py holdout_vault.py AGY2_FundAdvisory/holdout_vault.py AGENT_SPEC.md tests/test_infra.py
  ```
  **直接观察**: 输出严格为空字符，diff 行数为 **0**。4 个裁判文件保持绝对干净与未修改。
- **函数签名与费率契约**:
  - `DataLoader.simulate_execution` 签名包含 `(weights_df, prices_df, is_otc, penalty_days, penalty_rate, etf_impact)`，默认扣费与冲击逻辑 100% 保持不变。

### 1.2 痛点 1：因子进化 12h 磁盘持久化缓存与主线程零阻塞
- **缓存实现代码位置**:
  - `AGY2_FundAdvisory/advisory_engine.py` 第 294-337 行实装 `_resolve_cache_path`、`_read_disk_cache` 与 `_write_disk_cache`：
    ```python
    def _read_disk_cache(self, max_age_seconds: float = 43200.0) -> Optional[Dict[str, Any]]:
        cache_path = self._resolve_cache_path()
        if not cache_path.exists():
            return None
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            cached_ts = float(data.get("timestamp", 0.0))
            if time.time() - cached_ts < max_age_seconds:
                return data
        except Exception:
            pass
        return None
    ```
  - 有效期为 12 小时（43,200 秒），在 `evolve_factor_weights`（第 736 行）与 `get_60d_rolling_nav_and_trajectory`（第 903 行）入口处直接优先读取磁盘缓存。
- **实测响应延迟 (独立脚本 benchmark)**:
  - `evolve_factor_weights(force=False)` 命中耗时：**0.951 ms**（远低于 5.0 ms 契约）。
  - `get_60d_rolling_nav_and_trajectory(force=False)` 磁盘缓存命中耗时：**0.739 ms**（远低于 5.0 ms 契约）。
  - `data/cache/factor_evolution_cache.json` 磁盘持久化文件真实存在（大小 ~36.5 KB），包含全部关键顶级键：`['timestamp', 'weights', 'generation_scores', 'best_fitness', 'evolved_result', 'nav_trajectory']`。
- **`OpportunityRadarEngine.__init__` 非阻塞验证**:
  - 第 992-1034 行：`__init__` 移除了原无条件同步执行遗传算法的代码，重构为优先读取磁盘缓存，若缓存失效/缺失则立即使用高质量保底预设（`status: "cached_default"`）。
  - Mock 测试验证：在缓存存在及缓存被物理删除的两种场景下，实例化 `OpportunityRadarEngine` 时对 `OnlineHeuristicFactorEvolver.evolve_factor_weights` 的调用次数均为 **0**，彻底杜绝主线程同步跑 GA。

### 1.3 痛点 4：Tab 3 回测真实化打假与真实基准全收益
- **彻底根除人为硬加 Alpha**:
  - `AGY2_FundAdvisory/strategy_bridge.py` 原第 4929 行代码 `r_arr[1:] += (alpha_ann / 250.0)` 已被物理彻底删除，AST 语法树扫描与正则检索证实 0 匹配。
- **纯债基准指数 `H11009` 全收益映射与真实性**:
  - `BENCHMARK_INDICES_MAP["纯债指数"]` 严格映射为 `"H11009"`（中证综合债全收益指数）。
  - `UNIVERSE_18_CHAMPION_POOL` 中的纯债基金（`002351`, `000086`, `018757` 等）全部归一映射至 `H11009`，且 `alpha` 贡献设定为 `0.0`。
  - 数据源真实性：`df_mat["H11009"]` 来自 `data/processed/aligned_matrix_total_return.parquet` 真实历史日度收盘序列，历史 CAGR 为 **+4.85%**，每日收益率方差标准差 > 0.0001，二阶差分不恒为 0，彻底根除原端点两点连线假直线。
- **实盘账本后视镜免责声明与 C3 动态策略对照数据**:
  - `StrategyBridge.build_custom_portfolio_backtest` 在 `is_real_ledger=True` 或 `target_name` 包含“实盘/账本”时：
    - 返回的 DataFrame 挂载属性 `attrs["disclaimer"] = "当前持仓静态权重历史回溯（含历史后视镜权重效应，非滚动样本外实盘记录）"`；
    - 附带 `c3_dynamic_nav` 与 `c3_dynamic_drawdown` 对照序列，为 UI 同屏客观比对提供完整数据支持。

### 1.4 全量测试套件执行证据
- 执行命令：
  ```powershell
  py -3 -m pytest tests/test_causality_adversarial_m1.py tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_g12_full_suite.py
  ```
  **直接观察**: **50 passed, 0 failed** in 63.09s。
- 执行对抗挑战单测：
  - `tests/test_challenger_g13_m1.py`: **14 passed** in 5.33s。
  - `tests/test_challenger_g13_m1_2_adversarial.py`: **9 passed** in 9.07s。
  - 综合独立核验脚本 `scripts/verify_m1_reviewer_comprehensive.py`: 4 个大项全部 **PASS**。

---

## 2. Logic Chain (审查推演逻辑链与因果溯源)

1. **首屏零阻塞推演 (Pain Point 1)**:
   - [推演前置]: 原首屏瓶颈在于默认实例化 `OpportunityRadarEngine` 时在主线程同步触发 32 种群 $\times$ 15 代遗传算法，且未展开的 Popover 触发 12 个 Walk-Forward 滚动切片重算。
   - [实装事实]: Worker 在 `advisory_engine.py` 引入 12 小时持久化磁盘缓存；`_read_disk_cache` 实测读取在 0.7~0.9ms 内完成；`OpportunityRadarEngine.__init__` 在无缓存时走 `cached_default` 预设，GA 调用数为 0。
   - [推论]: 因子进化计算已完全与主线程解耦，痛点 1 核心引擎层改造彻底成立。

2. **回测去假与基准保真推演 (Pain Point 4)**:
   - [推演前置]: 原系统在计算收益率时每日强行累加 `(alpha_ann / 250.0)`，导致 8 年复利虚增 35%~45%；且纯债指数被画成假直线。
   - [实装事实]: 源代码中已彻底物理剔除该行；纯债映射至 `H11009` 中证综合债真实全收益序列（年化 +4.85%）；静态实盘账本注入后视镜免责声明，并挂载 C3 全天候动态策略对照序列。
   - [推论]: 回测曲线彻底还原历史真实行情，消灭了后视镜幸存者错觉与人为造假，痛点 4 彻底闭环。

3. **安全契约与诚信红线推演 (Integrity Invariant)**:
   - [推演前置]: 审查规则严格禁止硬编码测试结果、虚假实现、绕过核心逻辑，且 4 个只读裁判文件零改动。
   - [实装事实]: 4 个只读裁判文件 Git diff 为 0；`factor_evolution_cache.json` 包含真实演化生成的特征权重与 60 日动态切片，二阶差分证明非线性插值；全量测试 50 项 100% 绿灯。
   - [推论]: 无任何诚信违规，代码质量与合规性达标。

---

## 3. Caveats (对抗性挑战、边界与潜在风险)

### 3.1 挑战 1 (Minor / Non-blocking): 磁盘缓存非原子写入风险
- **现状观察**: `OnlineHeuristicFactorEvolver._write_disk_cache` 当前采用 `open(cache_path, "w")` 直接写入。
- **攻击场景**: 在多进程高并发场景下，若写操作被意外中断或正处于瞬间截断窗口，并发读操作可能读取到不完整 JSON。
- **爆炸半径评估**: `_read_disk_cache` 具备全局 `try...except` 保护，损坏时自动回退为 `None`，不会抛出未捕获异常；且日常运行仅在用户主动点击刷新时低频写入。
- **建议**: 在未来迭代中可升级为 `write to temp file + os.replace` 原子替换。

### 3.2 挑战 2 (Downstream Dependency): GUI 表现层首屏调用约束
- **现状观察**: 虽然 `OpportunityRadarEngine` 的 GA 演化已被移除，但冷启动时其内部的行情加载 `_load_realtime_quotes()` 仍需约 500ms。
- **下游建议**: Milestone 2 Worker 在改造 `app_gui.py` 时，必须严格执行 `ORIGINAL_REQUEST.md` 约束：首屏折叠框默认关闭时彻底禁止实例化 `OpportunityRadarEngine()`，投顾提示条仅基于内存中已有的 `snapshot` 运行轻量纯内存逻辑。

---

## 4. Conclusion (综合结论)

- **最终裁决**: **APPROVE** (通过)
- **结论说明**:
  Worker M1 的代码修改针对性强、逻辑严密、证据链完整，彻底根除了因子计算重复演化阻塞与回测虚假 Alpha 两大历史痛点，严守全部物理安全红线，全量回归测试与对抗压力测试 100% 通过。同意 Milestone 1 正式验收闭环，并建议 Orchestrator 启动 Milestone 2。

---

## 5. Verification Method (独立可复现核验指令)

Orchestrator 或任一后续评审员可执行以下指令完整独立复现验证：

### 5.1 4 个只读裁判文件零改动核验
```powershell
git status --porcelain judge_engine.py AGY2_FundAdvisory/judge_engine.py holdout_vault.py AGY2_FundAdvisory/holdout_vault.py AGENT_SPEC.md tests/test_infra.py
```
*预期输出*: 输出为空（0 行改动）。

### 5.2 评审员综合核验脚本 (覆盖痛点 1、痛点 4 与对抗边界)
```powershell
py -3 scripts/verify_m1_reviewer_comprehensive.py
```
*预期输出*: 打印 `>>> REVIEWER R13-M1-1 ALL CHECKS PASSED: 100% <<<`。

### 5.3 全量自动化测试回归
```powershell
py -3 -m pytest tests/test_causality_adversarial_m1.py tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_g12_full_suite.py
```
*预期输出*: `50 passed in ~60s`。
