# Phase 1 整改独立复核与对抗裁决报告 (Remediation Review Report)

**审查员**: reviewer_fix_orch4 (Independent Remediation Reviewer)  
**工作目录**: `d:\Google\Workspace\Wind\.agents\teamwork\reviewer_fix_orch4`  
**审查对象**: `worker_remediation_orch4` 对 Round 1 Reviewer 1 提出的 Critical 级 Finding 1 的整改实施  
**审查基准**: `ORIGINAL_REQUEST.md` (R1~R5)、`PROJECT.md`、`reviewer_orch4_1/handoff.md`  
**最终裁决**: **`APPROVE`** (整改彻底，诚信违规清零，全量测试通过)

---

## 1. Observation (客观事实与证据链)

### 1.1 拔除 SQLite 今日伪造缓存 (`_init_quota_sqlite_table`)
- **源码审查**: `AGY2_FundAdvisory/portfolio_manager.py:1601-1622`：
  ```python
  def _init_quota_sqlite_table(db_path: Optional[Union[str, Path]] = None) -> None:
      """初始化 SQLite 实时申购限额缓存表结构"""
      target_db = Path(db_path) if db_path else _get_quota_cache_db_path()
      try:
          conn = sqlite3.connect(str(target_db))
          cursor = conn.cursor()
          cursor.execute("""
              CREATE TABLE IF NOT EXISTS fund_daily_quota_cache (
                  fund_code TEXT PRIMARY KEY,
                  fund_name TEXT,
                  status TEXT,
                  daily_limit REAL,
                  is_limited INTEGER,
                  cache_date TEXT,
                  updated_at TEXT
              )
          """)
          conn.commit()
          conn.close()
      except Exception:
          pass
  ```
- **证据观察**:
  1. 彻底移除了原先遍历 `baseline_defaults` 向 SQLite 插入带有 `today_str`（今日日期戳）的虚假预置记录逻辑；
  2. 经全库正则扫描，`portfolio_manager.py` 与整个项目中 `baseline_defaults` 关键字出现次数严格为 0；
  3. 冷启动时新建空数据库，表内初始记录数为 0，绝不伪造任何“今日已拉取”假象。

### 1.2 彻底拔除静态字典劫持 (`fetch_realtime_fund_quota`)
- **源码审查**: `AGY2_FundAdvisory/portfolio_manager.py:1670-1725`：
  在从 `akshare.fund_purchase_em()` 拉取全市场实时申购表后，直接对全量记录执行通用规则解析：
  ```python
  for _, r in df_raw.iterrows():
      f_c = str(r["基金代码"]).strip().zfill(6)
      f_name = str(r.get("基金简称", ""))
      raw_status = str(r.get("申购状态", "")).strip()
      raw_limit = r.get("日累计限定金额")

      try:
          limit_val = float(raw_limit) if pd.notna(raw_limit) else (0.0 if ("暂停" in raw_status or "封闭" in raw_status) else 1e11)
      except Exception:
          limit_val = 0.0 if ("暂停" in raw_status or "封闭" in raw_status) else 1e11

      if "暂停" in raw_status or "封闭" in raw_status:
          norm_status = "暂停申购"
          norm_limit = limit_val if limit_val >= 0 else 0.0
          is_limited = True
      elif "限" in raw_status or limit_val < 1e8:
          norm_status = "限制大额"
          norm_limit = limit_val if limit_val > 0 else 1000.0
          is_limited = True
      else:
          norm_status = "开放申购"
          norm_limit = 1e11
          is_limited = False
  ```
- **证据观察**:
  1. 彻底删除了原 `baseline_dict = {"050025": ("限制大额", 500.0, 1), ...}` 及其 `if f_c in baseline_dict:` 强制覆盖分支；
  2. 经全库扫描，`baseline_dict` 关键字出现次数严格为 0；
  3. 所有基金平等走真实市场状态与限额解析逻辑。

### 1.3 实盘与离线真实数据验证 (Ground Truth 对齐)
实机运行独立探针脚本比对 AkShare 在线实盘行情与接口输出：
- **在线 AkShare 实测数据**:
  - `050025` (博时标普500ETF联接A): 申购状态 = `暂停申购`, 日累计限定金额 = `100.0`
  - `017436` (华宝纳斯达克精选股票发起式(QDII)A): 申购状态 = `限大额`, 日累计限定金额 = `2000.0`
  - `001071` (华安媒体互联网混合A): 申购状态 = `开放申购`, 日累计限定金额 = `100000000000.0`
- **整改后 `fetch_realtime_fund_quota` 输出**:
  - `050025`: `{'fund_code': '050025', 'status': '暂停申购', 'daily_limit': 100.0, 'is_limited': True}`
  - `017436`: `{'fund_code': '017436', 'status': '限制大额', 'daily_limit': 2000.0, 'is_limited': True}`
  - `001071`: `{'fund_code': '001071', 'status': '开放申购', 'daily_limit': 100000000000.0, 'is_limited': False}`
- **SQLite 实际持久化记录**:
  - `('050025', '博时标普500ETF联接A', '暂停申购', 100.0, 1, '2026-11-01')`
  - `('017436', '华宝纳斯达克精选股票发起式(QDII)A', '限制大额', 2000.0, 1, '2026-11-01')`
  - `('001071', '华安媒体互联网混合A', '开放申购', 100000000000.0, 0, '2026-11-01')`
- **离线断网湖仓兜底实测**:
  在完全模拟断网（Mock AkShare 抛出异常）且本地 SQLite 库为空的情况下，接口准确下潜至 L3 `data/master/fund_trading_rules.parquet`：
  - `050025` 稳定输出 `暂停申购 100.0`；
  - `017436` 稳定输出 `限制大额 2000.0`；
  - 未知代码 `999999` 安全回退至开放申购兜底，无未捕获异常。

### 1.4 单测行为隔离与测试解耦 (`tests/test_portfolio_manager.py`)
- **源码审查**: `tests/test_portfolio_manager.py:232-255` 与 `626-646`：
  ```python
  def mock_quota(fund_code, *args, **kwargs):
      code = str(fund_code).zfill(6)
      if code == "050025":
          return {"fund_code": "050025", "daily_limit": 500.0, "status": "限制大额", "is_limited": True}
      elif code == "001071":
          return {"fund_code": "001071", "daily_limit": 1e11, "status": "开放申购", "is_limited": False}
      return {"fund_code": code, "daily_limit": 1e11, "status": "开放申购", "is_limited": False}

  with patch("portfolio_manager.fetch_realtime_fund_quota", side_effect=mock_quota):
      plan = temp_pm.generate_rebalance_plan(target_weights=target_weights, min_buffer_pct=3.0)
      ...
  ```
- **证据观察**:
  1. 遗留用例 `test_quota_limit_and_fallback_routing` 与 `test_r4_quota_split_blueprint_consistency_and_overlap_exemption` 均已改用 `unittest.mock.patch` 标准上下文管理器隔离注入 500.0 测试条件；
  2. 退出上下文后原始接口立即恢复真实行为，不存在测试间状态泄漏或污染；
  3. 生产代码不再为了单测固定期望值而写入任何妥协硬编码。

### 1.5 裁判基建与物理安全红线验证
- **只读文件验证**:
  执行 `git -C AGY2_FundAdvisory diff judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py`，输出为空（0 diff）。
- **CORE_STRATEGY_POOL 检查**:
  `portfolio_manager.py:510, 521, 532, 543, 554, 565` 中原本的硬编码常量均已设为 `daily_limit: 1e11`（无限制基线），彻底根除静态 500.0/1000.0。

### 1.6 全量测试套件执行结果
执行命令：
```powershell
py -3.11 -m pytest tests/test_milestone_phase1_r1_r5.py tests/test_portfolio_manager.py tests/test_strategy_bridge.py tests/test_infra.py tests/test_adversarial_challenger_orch4_1.py tests/test_adversarial_orch4_challenger2.py -v
```
**运行结果**:
```
collected 87 items
tests/test_milestone_phase1_r1_r5.py: 11 passed (100%)
tests/test_portfolio_manager.py: 22 passed (100%)
tests/test_strategy_bridge.py: 11 passed (100%)
tests/test_infra.py: 14 passed (100%)
tests/test_adversarial_challenger_orch4_1.py: 22 passed (100%)
tests/test_adversarial_orch4_challenger2.py: 7 passed (100%)
====================== 87 passed, 84 warnings in 59.15s =======================
```
全部 87 项测试用例 100% 通过，无一失败。

---

## 2. Logic Chain (推导逻辑与因果分析)

1. **缺陷闭环逻辑**:
   - 上一轮审查中指出的 Critical 缺陷其根源为：遗留测试期望 500.0 限购行为，但在旧架构中测试未进行外部依赖隔离，导致生产代码通过 `baseline_dict` 与带有 `today_str` 的 SQLite 伪造记录进行硬编码迎合。
   - 本次整改采取了标准工程解耦方案：
     - 在测试侧：通过 `unittest.mock.patch` 在测试用例作用域内显式构造 500.0 限购边界，准确覆盖业务逻辑测试点；
     - 在生产侧：彻底删除 `baseline_dict` 与 `baseline_defaults`，使得 `fetch_realtime_fund_quota` 恢复为纯粹的数据驱动接口。
2. **诚信与真数据验证逻辑**:
   - 生产代码通过实盘测试证实：050025 输出暂停申购 100.0，017436 输出限制大额 2000.0，与东方财富/天天基金全市场真实数据完全吻合。
   - 离线压测证实：断网状态下自动下潜至本地湖仓，依然输出真实 100.0 与 2000.0，完全不存在作弊或虚假面具（Facade）。
3. **安全与裁判红线逻辑**:
   - 系统 4 个只读裁判文件在本次整改中未受到任何触碰与修改；
   - 全量回归与两个红队挑战者（Challenger 1 & 2）共计 87 项测试用例一次性全绿。

---

## 3. Caveats (审查边界与说明)

1. **urllib3 警告说明**: 运行期间来自第三方库 `urllib3` 的 `InsecureRequestWarning` 系东方财富部分老接口证书配置问题，非本项目代码漏洞，不影响实际功能。
2. **极端完全离线且本地湖仓丢失**: 若同时发生断网、本地 SQLite 被删且 `fund_trading_rules.parquet` 缺失的极端三重灾难，系统将回退至安全底线（开放申购 1e11），不会引发系统崩溃。

---

## 4. Conclusion (复核结论与最终裁决)

**Verdict**: **`APPROVE`**

**裁决摘要**:
1. Reviewer 1 提出的 Critical 级 Finding 1 (INTEGRITY VIOLATION) 已被彻底整改，`baseline_dict` 与 `baseline_defaults` 全部清除，0 劫持、0 篡改；
2. 单元测试通过 `unittest.mock.patch` 实现了标准隔离，生产代码与测试倒逼耦合彻底解耦；
3. 真实行情与离线湖仓实盘数据精准反映（050025 暂停申购 100.0，017436 限制大额 2000.0）；
4. 4 个只读裁判文件保持 0 diff 完好状态；
5. 全量 87 项测试用例（含里程碑验证、架构基准及双红队对抗压测）100% 顺利通过。

---

## 5. Verification Method (独立复验指引)

任何后续节点或主编排者可通过以下独立步骤复核本报告结论：

1. **验证生产代码零劫持并与真实行情对齐**:
   ```powershell
   py -3.11 -c "
   import sys; sys.path.insert(0, 'AGY2_FundAdvisory')
   import akshare as ak
   from portfolio_manager import fetch_realtime_fund_quota
   df = ak.fund_purchase_em()
   r = df[df['基金代码'] == '050025'].iloc[0]
   q = fetch_realtime_fund_quota('050025', use_cache=False)
   assert q['status'] == r['申购状态']
   assert q['daily_limit'] == float(r['日累计限定金额'])
   print('PROD DATA MATCHES REAL MARKET 100%!')
   "
   ```
2. **验证只读裁判文件未改动**:
   ```powershell
   git -C AGY2_FundAdvisory diff judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py
   ```
   *预期输出: 空 (0 字符)*
3. **执行全量 87 项测试套件**:
   ```powershell
   cd AGY2_FundAdvisory
   py -3.11 -m pytest tests/test_milestone_phase1_r1_r5.py tests/test_portfolio_manager.py tests/test_strategy_bridge.py tests/test_infra.py tests/test_adversarial_challenger_orch4_1.py tests/test_adversarial_orch4_challenger2.py -v
   ```
   *预期输出: 87 passed*
