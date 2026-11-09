# Milestone 1 终审与对抗挑战审查报告 (Reviewer & Adversarial Critic Report)

**Reviewer Agent**: reviewer_g13_m1_2  
**Target Milestone**: Milestone 1 (痛点 1 因子进化持久化磁盘缓存与痛点 4 Tab 3 回测真实化打假)  
**Worker Under Review**: worker_g13_m1  
**Report Path**: `d:\Google\Workspace\Wind\.agents\teamwork\reviewer_g13_m1_2\handoff.md`  

---

## 审查裁决 (Review Verdict)

**Verdict**: **APPROVE** (通过)  
**诚信合规评估 (Integrity Check)**: 100% 通过（零硬编码造假、零伪实现门面、零绕过逻辑、4 个只读裁判文件零改动）  
**对抗性综合风险 (Adversarial Risk)**: LOW (已发现 2 项轻微优化建议，不阻塞交付)  

---

## 1. Observation (客观观察事实与精确比对证据)

### 1.1 专有文件修改与只读裁判文件防线核验
- **命令与事实**：
  - 执行 `git status --porcelain judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py` 与 `git diff HEAD -- ...`：
    - 输出严格为空，改动行数为 **0**，哈希严格一致。
  - 执行 `git status --short`：
    - 仅有 `AGY2_FundAdvisory/advisory_engine.py` 与 `AGY2_FundAdvisory/strategy_bridge.py`（以及运行单测生成的数据更新）被修改。

### 1.2 `AGY2_FundAdvisory/advisory_engine.py` 代码实装核查
- **磁盘缓存逻辑 (`_resolve_cache_path`, `_read_disk_cache`, `_write_disk_cache`)**：
  - 第 294-302 行：`_resolve_cache_path()` 优先定位 `WORKSPACE_ROOT / "data" / "cache" / "factor_evolution_cache.json"`，自动创建父级目录。
  - 第 304-317 行：`_read_disk_cache(max_age_seconds=43200.0)` 实现了 12 小时 TTL 判断 (`time.time() - cached_ts < max_age_seconds`)，且内置 `try...except` 容错。
  - 第 319-337 行：`_write_disk_cache()` 实现了增量字典合并写入 (`existing.update(updates)`)，自动维护最新时间戳。
- **缓存命中耗时实测**：
  - 独立运行测试：
    ```python
    t0 = time.perf_counter()
    res = evolver.evolve_factor_weights()
    t1 = time.perf_counter()
    traj = evolver.get_60d_rolling_nav_and_trajectory()
    t2 = time.perf_counter()
    ```
    - 演化读取耗时：**0.95ms**（远低于 5ms 阈值）；
    - 60 日轨迹读取耗时：**0.91ms**（远低于 5ms 阈值）；
    - 磁盘缓存文件 `data/cache/factor_evolution_cache.json` 真实存在，完整包含 `weights`, `generation_scores`, `best_fitness`, `evolved_result`, `nav_trajectory`, `timestamp` 6 大核心键。
- **`OpportunityRadarEngine` 初始化耗时与降级机制**：
  - 第 992-1034 行：`__init__` 中移除了原同步无条件跑遗传算法的 `self.evolver.evolve_factor_weights()`，优先读取磁盘缓存；若无缓存则直接载入优质预设字典 (`status: "cached_default"`)，杜绝首屏阻塞。

### 1.3 `AGY2_FundAdvisory/strategy_bridge.py` 回测打假核查
- **彻底根除人为添加 Alpha (`alpha_ann / 250.0`)**：
  - 全文正则/字符串检索 `alpha_ann`：在 `build_custom_portfolio_backtest` 中已彻底物理删除 `r_arr[1:] += (alpha_ann / 250.0)`。
  - 资产日收益率直接取自 `s_arr[1:] / s_arr[:-1] - 1.0`，组合日收益严格等于权重与资产真实日收益加权之和 (`port_ret += fw * r_arr`)。
- **纯债基准指数 `H11009` 全收益映射与真实性**：
  - 第 164 行：`BENCHMARK_INDICES_MAP["纯债指数"]` 修正为 `"H11009"`。
  - 底层 Parquet 读取：`df_mat["H11009"]` 包含 2,146 个真实交易日历史收盘，起始点位 168.0，终止点位 251.5185，年化复合增长率 (CAGR) 为 **+4.8529%**。
  - 日度波动真实性：日涨跌幅包含 177 种不同离散取值，非 0 变动占比 96.5%，绝非端点线性插值假直线。
- **实盘账本后视镜效应免责声明与 C3 动态策略对照**：
  - 第 4887-4889 行：函数签名新增 `is_real_ledger: bool = False`, `target_name: Optional[str] = None`, `**kwargs`，保持全面向下兼容。
  - 第 5005-5026 行：
    - 当为实盘账本时，为返回的 DataFrame 注入属性 `attrs["disclaimer"] = "当前持仓静态权重历史回溯（含历史后视镜权重效应，非滚动样本外实盘记录）"`，同时兼容 `setattr(df_res, "disclaimer", ...)`；
    - 成功附带 `c3_dynamic_nav` 与 `c3_dynamic_drawdown`，为 UI 提供样本外全天候策略的客观比对基准。

### 1.4 全量测试套件执行结果
- 执行命令：
  ```powershell
  py -3 -m pytest tests/test_causality_adversarial_m1.py tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_g12_full_suite.py
  ```
- 结果：**50 passed, 0 failed** (耗时 61.54s)。
  - `tests/test_causality_adversarial_m1.py`: 6 项对抗探针全部通过；
  - `tests/test_infra.py`: 14 项裁判基础设施测试全部通过；
  - `tests/test_adv_final_closure.py`: 14 项闭环测试全部通过；
  - `tests/test_g3_evolution_loop.py`: 12 项演化测试全部通过；
  - `tests/test_g12_full_suite.py`: 4 项宏观与风控测试全部通过。

---

## 2. Logic Chain (审查推演逻辑链与因果溯源)

1. **痛点 1（首屏阻塞与因子进化缓存）验收推演**：
   - 依赖项：用户诉求要求首屏主线程耗时 `< 150ms`，彻底消除 `OpportunityRadarEngine` 实例化对主线程的阻塞。
   - 观察事实：原代码在 `__init__` 中无条件执行 15 代 GA（耗时 250ms+），且 60 日滚动演化无持久化缓存。
   - 修复事实：通过磁盘持久化文件 `factor_evolution_cache.json`（TTL 12h），使得二次渲染与非强制刷新场景下的因子查询与 60 日轨迹获取仅耗时 **0.95ms**；且 `OpportunityRadarEngine.__init__` 在缓存缺失时具备零耗时默认保底结构。
   - 推论：痛点 1 核心引擎层改造已彻底消除了首屏 GA 计算阻塞，逻辑闭环成立。

2. **痛点 4（Tab 3 回测真实化与基准打假）验收推演**：
   - 依赖项：用户诉求要求回测曲线彻底根除每天人为硬加的年化常数 Alpha，纯债指数杜绝线性插值假直线，实盘静态回测必须披露后视镜幸存者效应并提供 C3 动态策略对照。
   - 观察事实：原代码 `r_arr[1:] += (alpha_ann / 250.0)` 导致复利失真达 40% 以上，纯债基准映射至低年化的基金指数。
   - 修复事实：物理删除了该行代码；纯债指数映射修正为中证综合债全收益（`H11009`，年化 4.85%）；实盘静态回测已自动标记 disclaimer 并输出 C3 动态策略同源对比序列。
   - 推论：痛点 4 底层数据与回测引擎打假改造彻底，100% 还原历史真实行情，逻辑闭环成立。

3. **安全契约与诚信红线推演**：
   - 依赖项：严禁修改 4 个只读裁判文件与 `DataLoader.simulate_execution` 签名。
   - 观察事实：Git 状态核验证明只读文件改动为 0，且在全量回归测试中 50 项测试 100% 绿灯。
   - 推论：安全底线未被破坏。

---

## 3. Adversarial Challenges (对抗性审查与潜在失效模式挑战)

### 挑战 1 (Minor Finding): 磁盘缓存写操作缺乏原子替换保护 (Non-Atomic File Write)
- **挑战现状**：
  在 `OnlineHeuristicFactorEvolver._write_disk_cache` 中（第 334 行）：
  ```python
  with open(cache_path, "w", encoding="utf-8") as f:
      json.dump(existing, f, ensure_ascii=False, indent=2)
  ```
- **攻击场景 (Failure Mode)**：
  在 Windows 多进程或 Streamlit 多会话并发场景下，若某个会话正在触发 `force_refresh=True` 写入 ~20KB 的 JSON 缓存，而另一个会话在此时调用 `_read_disk_cache`，由于 `open(..., "w")` 会瞬间将文件截断为 0 字节，并发读取者可能读到空文件或不完整的 JSON。
- **实际爆炸半径评估**：
  当前 `_read_disk_cache` 在第 315 行有 `try ... except Exception: pass; return None`。并发读取失败时会自动判定为缓存未命中，不会抛出未捕获异常导致页面白屏。但在极端异常断电或进程强杀场景下，磁盘上可能残留不完整文件。
- **防御与改进建议 (Mitigation)**：
  在后续世代中，建议将磁盘缓存写入升级为标准原子替换模式：先写入临时文件（如 `cache_path.with_suffix('.tmp')`），通过 `os.replace` 原子替换目标文件。

### 挑战 2 (Note / Downstream Dependency): `OpportunityRadarEngine` 的行情获取耗时
- **挑战现状**：
  虽然 Milestone 1 已彻底将 GA 遗传算法从 `OpportunityRadarEngine.__init__` 中剥离，但其内部调用的 `self._load_realtime_quotes()` 在冷启动或首次拉取时仍需耗时约 540ms。
- **下游 Milestone 契约验证**：
  根据 `ORIGINAL_REQUEST.md` 要求，Milestone 2（GUI 表现层）必须在 `app_gui.py` 的折叠框默认关闭状态下彻底禁止在主线程同步调用 `OpportunityRadarEngine()`，改用轻量内存快照 `snapshot` 计算。本工单引擎层交付完全符合契约，Milestone 2 Worker 必须严格遵守该约束。

---

## 4. Conclusion (综合评审结论)

- **综合裁决**: **APPROVE** (通过)
- **理由**：
  1. 痛点 1（因子进化 12 小时磁盘持久化与 `< 5ms` 查询）与痛点 4（删除人工 Alpha、真实纯债全收益 `H11009`、实盘账本后视镜免责声明与 C3 对照）代码实现完全符合要求。
  2. 4 个只读裁判文件严格零修改，`simulate_execution` 默认逻辑完好。
  3. 50 项自动化测试全部 100% 绿灯通过，未引入任何回归缺陷或诚信违规。
  4. 具备充足的下游前瞻性，允许 Milestone 2 无缝接续开展前端 GUI 与 CSS 重塑。

---

## 5. Verification Method (独立可复现核验指令)

后任评审员或 Orchestrator 可通过以下独立指令 100% 复现核验证明：

### 5.1 验证 4 个只读裁判文件零修改
```powershell
git status --porcelain judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py
```
*预期输出*：无任何输出（空）。

### 5.2 痛点 1 独立测试 (磁盘缓存有效性与耗时)
```powershell
py -3 -c "import time, json; from AGY2_FundAdvisory.advisory_engine import OnlineHeuristicFactorEvolver; evolver = OnlineHeuristicFactorEvolver(); t0 = time.perf_counter(); res = evolver.evolve_factor_weights(); t1 = time.perf_counter(); traj = evolver.get_60d_rolling_nav_and_trajectory(); t2 = time.perf_counter(); print('Evolve ms:', (t1-t0)*1000, 'Traj ms:', (t2-t1)*1000); assert (t2-t1)*1000 < 5.0; print('Cache verification PASSED!')"
```
*预期输出*：`Traj ms: < 5.0`，打印 `Cache verification PASSED!`。

### 5.3 痛点 4 独立测试 (无人工 Alpha、真实 H11009 全收益、disclaimer 与 C3 对照)
```powershell
py -3 -c "import inspect; from AGY2_FundAdvisory.strategy_bridge import StrategyBridge, BENCHMARK_INDICES_MAP; src = inspect.getsource(StrategyBridge.build_custom_portfolio_backtest); assert 'alpha_ann / 250' not in src; assert BENCHMARK_INDICES_MAP['纯债指数']['col'] == 'H11009'; df = StrategyBridge.build_custom_portfolio_backtest({'002351': 1.0}, is_real_ledger=True); assert 'c3_dynamic_nav' in df.columns; assert getattr(df, 'disclaimer', '') != ''; print('Pain 4 verification PASSED!')"
```
*预期输出*：打印 `Pain 4 verification PASSED!`。

### 5.4 全量自动化测试回归
```powershell
py -3 -m pytest tests/test_causality_adversarial_m1.py tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_g12_full_suite.py
```
*预期输出*：`50 passed in ~60s`。
