# G14 世代测试套件、物理安全红线、浏览器核验与发布运维调研报告 (handoff.md)

## 1. 观察事实 (Observation)

### 1.1 物理安全红线文件与数据资产核验事实
通过 PowerShell 原生命令 `Get-FileHash` 与 `git status` 直接核验 4 个只读裁判文件及关键执行算子，获取到如下精确路径与 SHA256 指纹：

| 文件绝对路径 | 作用与物理防线定位 | SHA256 校验指纹 | Git 跟踪状态 |
| :--- | :--- | :--- | :--- |
| `D:\Google\Workspace\Wind\AGY2_FundAdvisory\judge_engine.py` | 裁判裁决核心引擎（只读） | `76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF31CC07BE` | Clean, 零修改 |
| `D:\Google\Workspace\Wind\AGY2_FundAdvisory\holdout_vault.py` | 样本外保险库（只读） | `88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670BD031D2A` | Clean, 零修改 |
| `D:\Google\Workspace\Wind\AGY2_FundAdvisory\AGENT_SPEC.md` | 代理行为规范（只读） | `A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B800CD63957` | Clean, 零修改 |
| `D:\Google\Workspace\Wind\tests\test_infra.py` | 基础设施红线测试套件（只读） | `48BEE0DA300D7C0A0848EC1376E4B9B2E55224D2736081713B4340F0362CD100` | Clean, 零修改 |
| `D:\Google\Workspace\Wind\AGY2_FundAdvisory\tests\test_infra.py` | 子模块镜像基准测试（只读） | `B8D781BE8135BE05CF61E62E4B534E359985AD880F27FFB61228A33DF6B02A6A` | Clean, 零修改 |

- **`DataLoader.simulate_execution` 默认签名与扣费逻辑核验**：
  - 定位位置：`D:\Google\Workspace\Wind\AGY2_FundAdvisory\data_loader.py` 第 1437 行至 1540 行。
  - 函数签名：
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
  - 扣费阶梯逻辑（第 1516-1533 行）：
    - `< penalty_days` (7 天)：强制扣除 `penalty_rate` (1.50%)；
    - `< 30` 天：C 类 0.50%，A 类 0.75%；
    - `< 180` 天：C 类免赎回费 (0.00%)，A 类常规 0.50%；
    - `< 365` 天：C 类 0.00%，A 类 0.25%；
    - `>= 365` 天：全部 0.00%；
    - 场内 ETF 冲击成本：双边 `etf_impact` (0.0010)。
  - `git status -s AGY2_FundAdvisory/data_loader.py` 返回空（未发生任何修改）。

- **`data/ledgers_index.json` 纯净度核验**：
  - 文件路径：`D:\Google\Workspace\Wind\data\ledgers_index.json`。
  - 内容显示当前仅登记唯一主实盘账本 `main_live`（名称：“主实盘账本”，`is_protected: true`，`portfolio_ledger.json` 与 `portfolio_state.db`），历史沙盒测试遗留账本完全为零，账本目录绝对纯净。

---

### 1.2 现有测试套件运行实测数据
在 Windows PowerShell 下调用 `py -3.11 -m pytest`，对指定的四大核心自动化测试套件进行全量执行测试，全部 100% 通过（Total: 50 passed, 0 failed）：

| 测试文件路径 | 测试用例数 | 耗时 | 运行状态 | 关键验证范围 |
| :--- | :---: | :---: | :---: | :--- |
| `tests/test_infra.py` | 14 passed | 7.22s | **100% PASS** | 4 座孤岛一致性、因果泄露探测、样本外保险库配额、裁判引擎套利惩罚防线 |
| `tests/test_adv_final_closure.py` | 14 passed | 44.13s | **100% PASS** | 9 大标准资产类别覆盖、收益安全垫与影子调仓审计、防虚假估值分位、多账本原子切换 |
| `tests/test_g3_evolution_loop.py` | 12 passed | 25.25s | **100% PASS** | EWMA 动态相关性突变防御 (>0.75)、10,000次块重采样 CVaR 99%、VWAP 滑点优化、三大历史拐点对照尺、浮盈安全垫抗震模型、14:30 尾盘估值异动预警 |
| `tests/test_gui_multi_ledger_stress.py` | 10 passed | 67.77s | **100% PASS** | 多账本切换原子性与状态同步、另存为隔离、损毁索引自愈、Streamlit AppTest 端到端抗白屏测试 |
| **总计** | **50 passed** | **144.37s** | **100% PASS** | **当前主干测试套件基线完全健康稳定** |

---

### 1.3 G14 目标修改点现场代码巡检
1. **假缓存漏洞观察**：
   - `AGY2_FundAdvisory/app_gui.py` 第 2900 行和第 7429 行尝试 `open(radar_cache_f, "r")` 读取 `data/cache/radar_sectors_cache.json`。
   - 但在 `AGY2_FundAdvisory/advisory_engine.py` 第 1638 行 `OpportunityRadarEngine.scan_all_sectors` 中，全方法仅进行内存循环与排序，**根本没有将扫描结果写入 `data/cache/radar_sectors_cache.json` 的代码，入口处也没有读取磁盘缓存并判断 4 小时 TTL 的逻辑**！这导致前端缓存永远未命中，每次加载均重复扫描。
2. **样本外轨迹选股偷工减料 Bug 观察**：
   - `AGY2_FundAdvisory/advisory_engine.py` 第 933-934 行：
     ```python
     # 动态策略（Top 3加权）与静态策略（全市场等权）
     oos_dynamic_returns.append(float(np.mean(r_day[:3])))
     oos_static_returns.append(float(np.mean(r_day)))
     ```
   - 现场代码直接对收益率矩阵切片 `r_day[:3]` 取算术平均，完全未结合前一日特征向量 $f_{vec}$ 与演化权重 $w_{opt}$ 点乘挑选动态 Top 3，且换手率惩罚完全漏扣。
3. **十二维主动风控在 GUI 呈现缺失观察**：
   - `advisory_engine.py` 第 2043-3030 行已完整编写了 12 个维度的巡检逻辑。
   - 但在 `AGY2_FundAdvisory/app_gui.py` 第 2840-2854 行与 3022-3028 行中，前端仅用简陋的 `if lock_funds` 与 `if c_free_funds` 进行判断，甚至直接在无锁仓无C类满期时硬编码展示 `🟢 主动风控巡检全通`，导致其余 10 个维度的真实风险（移动止盈、超买、深套、集中度、迷你基、攻防线、期权IV哨等）在 UI 上完全失明。

---

## 2. 逻辑链推演 (Logic Chain)

```
[观察事实 1.1: 4 只读裁判文件与 DataLoader.simulate_execution 签名/费率保持 100% 原始指纹]
         ↓ (推论 1: 物理安全红线未破，任何重构代码与新增测试严禁修改此 4+1 边界)
[观察事实 1.2: 现有四大测试套件 50 个用例全部绿灯通过]
         ↓ (推论 2: 现有工程基线稳定，新增 G14 单元测试必须在此基础上增量接入，不得破坏已有断言)
[观察事实 1.3: advisory_engine.py 存在雷达缓存未写、动态轨迹选股硬编码前三、UI未挂载完整12维风控]
         ↓ (推论 3: 必须针对 G14 提出的三大工程修补点，建立严格可独立执行、高对抗性的单元测试)
[推论 3 导出 G14 专项测试架构]:
  ├─ 专项 1: radar_sectors_cache.json 真实磁盘序列化与 4h TTL 缓存直读测试
  ├─ 专项 2: get_60d_rolling_nav_and_trajectory 动态因子权重 Top 3 挑选与 20 bps 换手扣除测试
  └─ 专项 3: ActiveRiskSentry 完整十二维风控巡检与 GUI holdings_hash 毫秒直读缓存测试
         ↓ (推论 4: 交付发布须遵从 Windows 端口防碰撞、无 Release 纯 Tag、分号锁定指令模板的硬门禁)
```

---

## 3. G14 专项新单元测试设计规范 (Test Suite Architecture)

建议在 `tests/test_g14_evolution_audit.py` 中建立针对 G14 缺陷修复的专项测试类 `TestG14EvolutionAudit`，覆盖以下三大测试模块：

### 3.1 专项测试 1: 14 赛道雷达磁盘缓存落盘与 TTL 机制 (`test_radar_sectors_cache_disk_persistence_and_ttl`)
- **被测对象**：`OpportunityRadarEngine.scan_all_sectors(force_refresh=...)`
- **Mock 与隔离策略**：
  - 使用 `tmp_path` 或临时目录重定向 `data/cache/radar_sectors_cache.json`；
  - 使用 `unittest.mock.patch` 探测底层 Parquet 加载函数（如 `DataLoader.load_total_return_matrix`）的调用次数。
- **核心断言设计**：
  1. **首次冷启动写入**：当缓存文件不存在时，调用 `scan_all_sectors()`，断言缓存文件成功创建，内容为有效 JSON，包含 `timestamp` 字符串与 14 赛道完整列表，每个赛道字典包含 `sector_id`, `name`, `total_score`, `tag`, `fund` 必备字段。
  2. **热读取秒开（<10ms）**：在缓存未过期（时间戳在 4 小时内）时再次调用 `scan_all_sectors(force_refresh=False)`，断言返回数据与磁盘缓存一致，且底层 Parquet 读取函数 `call_count == 0`，耗时 `< 15ms`。
  3. **过期 TTL 自动失效重新扫描**：将磁盘缓存的 `timestamp` 篡改为 5 小时前（超过 4 小时 TTL），调用 `scan_all_sectors()`，断言触发重新扫描，底层 Parquet 被读取，磁盘缓存时间戳被更新为当前时间。
  4. **强制刷新 `force_refresh=True`**：在缓存有效时显式传入 `force_refresh=True`，断言无视现有缓存强制全量重算。
  5. **坏道容错自愈**：写入非法 JSON 字符串 `{ corrupted :::: `，断言调用不崩溃且自愈覆盖写入新合法缓存。

```python
def test_radar_sectors_cache_disk_persistence_and_ttl(tmp_path, monkeypatch):
    from advisory_engine import OpportunityRadarEngine
    cache_file = tmp_path / "radar_sectors_cache.json"
    monkeypatch.setattr(OpportunityRadarEngine, "CACHE_FILE_PATH", str(cache_file))
    
    engine = OpportunityRadarEngine()
    # 1. 冷启动扫描与真实落盘
    res1 = engine.scan_all_sectors(force_refresh=True)
    assert cache_file.exists(), "scan_all_sectors 必须真实生成磁盘缓存文件！"
    with open(cache_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "timestamp" in data and "sectors" in data
    assert len(data["sectors"]) == 14

    # 2. 缓存直读零 Parquet 访问
    with patch.object(OpportunityRadarEngine, "_compute_sector_scores", wraps=engine._compute_sector_scores) as mock_compute:
        res2 = engine.scan_all_sectors(force_refresh=False)
        assert mock_compute.call_count == 0, "缓存有效期内严禁重复计算赛道分数！"
        assert len(res2) == 14
```

---

### 3.2 专项测试 2: 样本外动态选股算法真实性与 20 bps 换手扣除 (`test_rolling_nav_dynamic_weights_selection_and_turnover_friction`)
- **被测对象**：`OnlineHeuristicFactorEvolver.get_60d_rolling_nav_and_trajectory(force_refresh=True)`
- **核心断言设计**：
  1. **废除硬编码 `[:3]` 验证**：检验样本外每个交易日 $d$ 的动态 Top 3 是根据 $d-1$ 日四维因子矩阵与演化权重 $w_{opt}$ 点乘计算得出，静态 Top 3 根据静态基准权重计算得出。动态 Top 3 与静态 Top 3 选出赛道不同，两者的收益率序列差异显著，严禁出现两曲线数值完全相同的情况。
  2. **双边 20 bps 换手摩擦精准扣除**：
     - 当日收益公式必须满足：$r_{net} = r_{gross} - 0.0020 \times \text{turnover}$；
     - 验证调仓换手日，收益率严格扣除换手成本，不存在零摩擦虚假高收益。
  3. **指标输出完整性**：断言返回字典包含 `dates` (长度 60), `nav_dynamic`, `nav_static`, `final_nav_dynamic`, `final_nav_static`, `alpha_pct`, `mdd_dynamic_pct`, `trajectory`，且各项均为可序列化的原生浮点数。
  4. **磁盘持久化**：断言生成并更新 `data/cache/factor_evolution_cache.json`。

---

### 3.3 专项测试 3: 十二维主动风控巡检全量覆盖与 GUI 状态机缓存直读 (`test_active_risk_sentry_twelve_dimensions_and_holdings_hash_caching`)
- **被测对象**：`ActiveRiskSentry.inspect_portfolio` 以及 `app_gui.py` 中的 `holdings_hash` 缓存逻辑。
- **核心断言设计**：
  1. **十二维全覆盖测试表**：构造包含 12 组特征的特定测试账本或市场快照，断言全部 12 个维度均能被确定性触发并产出结构化 Alert：
     - 维度 1: 未满 7 天锁仓（红牌，`min_days < 7`，`lock_shares`）
     - 维度 2: 临免赎期倒计时（黄牌，C 类 23~29 天，`countdown_hold`）
     - 维度 3: C 类满 30 天零费率置换（黄牌，C 类 >= 30 天，`switch_a_class`）
     - 维度 4: 个基移动止盈（右侧破位红牌 / 高水位回撤黄牌 / 暴涨超买红牌 / 阶梯止盈黄牌 / 深套诊断黄牌）
     - 维度 5: 赛道集中度 (>35%) 与重仓股同质化重叠
     - 维度 6: 基金本体清盘警戒线 (AUM < 0.5亿) 与大盘攻防线跌破/突破
     - 维度 7: 动态相关性突变防御 (EWMA 相关系数突破 0.75)
     - 维度 8: 投资者适当性匹配（权益占比超标红/黄牌）与组合级止盈止损
     - 维度 9: 盘中异动安全垫实时传导 (gszzl 跌幅消耗安全垫 >20%)
     - 维度 10: 基金管理人集中度 (>35%) 与高波科技行业暴露上限 (>35%)
     - 维度 11: 50ETF/300ETF 认沽期权 IV 突升超 30% 防暴跌哨
     - 维度 12: 跨境 QDII 溢价与外汇期货锁汇成本套利机会
  2. **`holdings_hash` 唯一性与缓存击中**：
     - 测算当前账本持仓各基金代码、份额、净值、最小持有天数及 `active_tier_val` 拼接生成的 SHA256 哈希值；
     - 验证当持仓发生变动（增减份额、净值变动）或风险档位切换（如 C3 变 C1）时，`holdings_hash` 必然改变，触发风控重算；
     - 验证持仓未变动时，首屏直接从 `st.session_state` 或 `data/portfolio_watchdog.json` 直读缓存报告，耗时 `< 1ms`。
  3. **健康账本全通徽章**：当持仓各项指标均正常（无红牌、无黄牌）时，`all_passed` 必须为 `True`，只有此时才允许在前端渲染 `🟢 主动风控巡检全通`。

---

## 4. 交付与运维规范 (Operational & Delivery Specification)

### 4.1 服务平滑重启与 Windows 端口防碰撞规范
根据用户规则 12（Windows 瞬态出站端口碰撞与非破坏性甄别）及规则 2（后台静默托管），服务重启与调试步骤如下：

1. **非破坏性探针先行**：
   在 PowerShell 中运行以下命令甄别端口状态：
   ```powershell
   $portConn = Get-NetTCPConnection -LocalPort 8501 -ErrorAction SilentlyContinue | Where-Object { $_.State -eq 'Listen' }
   if ($portConn) {
       $procId = $portConn.OwningProcess
       Write-Host "检测到 8501 端口处于监听状态，进程 PID: $procId，执行优雅释放..."
       Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
       Start-Sleep -Seconds 1
   } else {
       Write-Host "8501 端口当前空闲，无需强杀。"
   }
   ```
2. **清理旧缓存并启动 Streamlit 守护进程**：
   ```powershell
   # 启动 Streamlit（无窗口模式，监听 8501 端口）
   Start-Process -FilePath "py" -ArgumentList "-3.11", "-m", "streamlit", "run", "AGY2_FundAdvisory/app_gui.py", "--server.port", "8501", "--server.headless", "true" -WindowStyle Hidden
   # 验证健康探针
   Start-Sleep -Seconds 2
   (Invoke-WebRequest -Uri "http://localhost:8501" -UseBasicParsing -TimeoutSec 5).StatusCode
   ```

---

### 4.2 浏览器验收核验标准 (`/browser` 4 核心场景)
调用 `/browser` 访问 `http://localhost:8501`，必须逐一核验以下 4 项直观交付标准：

1. **首屏秒开与开箱即用 (< 1秒)**：
   - 页面加载 1 秒内无白屏、不阻塞，顶部 4 张全局指标卡、投顾参谋折叠栏、四宫格主导航栏瞬间加载完毕；
   - 首次打开 Tab 1 时，直接静默呈现默认参数（10万元、C3平衡型）的完整建仓执行表与核心 3 格指标条，下半屏绝无空白大坑。
2. **按钮高定配色与控制栏水平对齐**：
   - Tab 1 右侧的「生成实盘建仓方案」Primary 按钮必须为机构蓝（`background: var(--accent-primary) !important`），彻底消除原生 `#ff4b4b` 番茄红；
   - Tab 1 顶部 5 列控件（金额、风险、建仓节奏、高级参数、生成按钮）垂直基线完全等高平齐，无高低错位。
3. **双翼看板十二维风控与磁盘缓存生效**：
   - 点击展开首屏投顾参谋栏，左翼脉搏徽章与 Top 3 赛道卡正常展示；
   - 右翼展示完整的十二维主动风控巡检报告，涵盖真实红黄牌；
   - 检查磁盘文件，确认 `data/cache/radar_sectors_cache.json` 与 `data/cache/factor_evolution_cache.json` 真实存在并更新。
4. **回测图表文字零遮挡与全收益真实曲线**：
   - 切换至 Tab 3「组合回测」，确认图例位于图表外部上方，文字不压盖净值曲线；
   - 纯债指数与红利低波为真实日度波动曲线，绝无起止点插值的伪直线；
   - 移动端 640px 视口下横向滚动平滑，文字无截断穿模。

---

### 4.3 Git 归档与版本标签规范
严格遵循版本发布契约，**严禁创建任何 GitHub Release**：
```bash
git add -A
git commit -m "feat(G14): 封堵四大代码漏洞、恢复十二维风控缓存直读、纠偏样本外轨迹选股摩擦与统一高定机构蓝审美"
git tag -a v4.4-G14 -m "Release v4.4-G14: G14 Milestone Closure - Code Vulnerability Closure & Institutional Aesthetics"
git push origin HEAD
git push origin --tags
```

---

### 4.4 阻塞性门禁：分号锁定 G15 自举提示词模板 (Strict Semicolon SlashCommand)
按用户规则要求，下发下一代 G15 指令时，**绝对禁止使用带冒号的 `slashCommand:` 格式，必须 100% 严格使用英文分号 `slashCommand;` 格式**：

```markdown
[/goal](slashCommand;goal) 启动 G15 世代全天候自适应资产配置、智能网格动态做 T 与机构级投顾交付闭环任务

[/boost](slashCommand;boost) 深度调优多智能体协同流水线，确保量化引擎、前端渲染与合规风控全量绿灯通过

[/teamwork](slashCommand;teamwork) 启动主编排流水线，分发任务至架构师、开发人员、测试人员与审计人员协同闭环

[/browser](slashCommand;browser) 启动无头浏览器自动化审查，核验 8501 端口全屏视口与移动端适配质感
```

---

## 5. 局限与未调查区域 (Caveats)

1. **离线与内网实时行情源延迟**：测试套件中包含针对外部行情接口（如东方财富快讯与实时估值）的降级回退机制；若处于断网或严格离线环境，系统将自愈回退至本地湖仓快照，不影响代码逻辑的数学自洽性。
2. **Streamlit AppTest 运行耗时较长**：`tests/test_gui_multi_ledger_stress.py` 内部包含 Streamlit 完整运行周期的端到端仿真测试，全量运行需约 60~70 秒，在日常高频单元测试中可优先运行针对性 Delta 测试以精准剪枝。

---

## 6. 调查结论 (Conclusion)

1. **安全红线完好**：4 个裁判文件（`judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py`）及 `DataLoader.simulate_execution` 处于完全纯净状态，未受任何污染。
2. **基线全绿**：当前 4 大现有测试套件共计 50 个用例全部 PASS，为后续 G14 代码修复提供了极佳的验证地基。
3. **三大新单元测试方案已完备就绪**：针对雷达缓存落盘、样本外轨迹动态选股与 20 bps 换手扣除、十二维风控巡检全量覆盖与 `holdings_hash` 缓存直读，已制定精确到参数与断言的完整测试设计。
4. **发布运维门禁清晰**：已梳理 Windows 端口安全释放脚本、4 大浏览器验收项、`v4.4-G14` 标签同步命令、以及 100% 分号锁定的 G15 提示词模板。

---

## 7. 独立验证方法 (Verification Method)

后续执行代理或审计代理可运行以下标准命令独立复核本报告结论：

1. **红线哈希与数据纯净度核验**：
   ```powershell
   Get-FileHash AGY2_FundAdvisory/AGENT_SPEC.md, AGY2_FundAdvisory/holdout_vault.py, AGY2_FundAdvisory/judge_engine.py, tests/test_infra.py
   Get-Content data/ledgers_index.json
   ```
2. **现有 50 项核心自动化测试全量回归**：
   ```powershell
   py -3.11 -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py tests/test_gui_multi_ledger_stress.py -v
   ```
3. **失效条件 (Invalidation Conditions)**：
   - 若 4 个只读裁判文件或 `DataLoader.simulate_execution` 的 SHA256 哈希发生任何改变；
   - 若现有 50 个测试用例出现任意一个 FAIL 或 ERROR；
   - 若生成的 G15 提示词中出现带冒号的 `slashCommand:` 格式。
