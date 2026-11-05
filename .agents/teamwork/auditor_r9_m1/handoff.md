# Forensic Integrity Audit Report: Milestone 1 多账本体系存储管理与全站热装配

**Auditor Agent**: `auditor_r9_m1` (teamwork_auditor)  
**Roles**: critic, specialist, auditor  
**Working Directory**: `d:\Google\Workspace\Wind\.agents\teamwork\auditor_r9_m1`  
**Parent Conversation ID**: `8849ddae-0421-48b2-aa8f-6d2c7b15dafe`  
**Audit Target**: Milestone 1 (M1: Features 1-4, R1 & R2)  
**Integrity Mode**: Development Mode (per `ORIGINAL_REQUEST.md`)  
**Verdict**: **CLEAN** (All physical redlines, anti-cheating, and empirical tests PASSED)

---

## 1. Observation (观测事实与物证链)

### 1.1 物理安全红线（4 大裁判文件 SHA256 与基线校验）
使用 SHA-256 算法对 4 大只读裁判文件进行逐字节哈希核验，并比对 git 状态：

```
AGY2_FundAdvisory/judge_engine.py: 
  actual:   76f930371176de7ee6a413174b030101e3210ac6e037f5d10fe229af31cc07be
  expected: 76f930371176de7ee6a413174b030101e3210ac6e037f5d10fe229af31cc07be
  match:    True

AGY2_FundAdvisory/holdout_vault.py:
  actual:   88122eaf647040a410e2fd95da81077db10149a498a47340ff40b670bd031d2a
  expected: 88122eaf647040a410e2fd95da81077db10149a498a47340ff40b670bd031d2a
  match:    True

AGY2_FundAdvisory/AGENT_SPEC.md:
  actual:   a346586f9bd2dc0ee83e665bd18e7a6471464c9f7b658e392b989b800cd63957
  expected: a346586f9bd2dc0ee83e665bd18e7a6471464c9f7b658e392b989b800cd63957
  match:    True

tests/test_infra.py:
  actual:   48bee0da300d7c0a0848ec1376e4b9b2e55224d2736081713b4340f0362cd100
  expected: 48bee0da300d7c0a0848ec1376e4b9b2e55224d2736081713b4340f0362cd100
  match:    True
```
- `git status --porcelain AGY2_FundAdvisory/judge_engine.py AGY2_FundAdvisory/holdout_vault.py AGY2_FundAdvisory/AGENT_SPEC.md tests/test_infra.py`: 输出完全为空，裁判文件 100% 保持只读锁定。

### 1.2 交易仿真执行算子基线校验 (`DataLoader.simulate_execution`)
- `git diff AGY2_FundAdvisory/data_loader.py`: 输出完全为空。
- 检查 `AGY2_FundAdvisory/data_loader.py` 第 1096-1103 行：
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
  默认入参、7天惩罚费逻辑、冲击成本计算完全未受任何篡改。

### 1.3 代码真实性与反作弊静态扫描 (AST Static Analysis)
对 M1 核心文件执行 Python 抽象语法树 (AST) 深度扫描：
- `AGY2_FundAdvisory/multi_ledger_manager.py`（510 行）：
  - 空 `pass` 函数数量：**0**
  - 仅返回常量的虚假实现：**0**
  - 硬编码伪造测试返回值：**0**
- `AGY2_FundAdvisory/portfolio_manager.py`（7472 行）：
  - 构造函数新增入参 `ledger_file` 与 `ledger_id`，保留完全向下兼容的默认值。
  - 当加载自定义账本时，自动派生 `db_path = ledger_json_path.with_suffix(".db")`，实现 SQLite 物理隔离。
  - 成功 re-export `MultiLedgerManager`。
- `AGY2_FundAdvisory/app_gui.py`（5737 行）：
  - 全局状态初始化正确绑定 `mlm`、`active_ledger_id` 与 `pm`。
  - Tab 2 顶部具备单行多账本管理吧台（选择器、➕新建 Popover、📋克隆 Popover、⚙️管理 Popover）。
  - Tab 1 步骤三提供「覆盖写入当前激活账本」与「另存为全新独立账本」双轨方案。
  - 未发现断层或空壳 UI 控件。

### 1.4 实盘文件落盘与 SQLite 隔离实测 (Empirical Verification)
运行实机独立脚本 `.agents/teamwork/auditor_r9_m1/empirical_test.py`：
1. **主实盘物理防删**：调用 `mlm.delete_ledger("main_live")` 立即抛出 `PermissionError("主实盘账本受物理保护，禁止删除！")`。
2. **沙盒真实落盘**：创建沙盒账本后，物理生成 `data/ledgers/sandbox_xxx.json`，可用现金与持仓真实存盘。
3. **SQLite 物理隔离防冲刷**：在沙盒中增持 `005561` 并调用 `save_state(record_snapshot=True)`，沙盒库 `data/ledgers/sandbox_xxx.db` 成功写入 1 行持仓；比对主实盘文件：
   - 主实盘 JSON 哈希在沙盒操作前后均为 `cae3b02f5f4444f0c7a2577f9c458c5579e5b15fec4cf3b09d1ee477c5d2dc9c`，0 改变。
   - 主实盘 SQLite `portfolio_state.db` 持仓表完全未变，未发生任何清空或冲刷。
4. **账本克隆真实性**：成功深拷贝持仓并写入全新独立 target_id。
5. **家庭总资产汇总**：`get_all_ledgers_summary()` 真实遍历所有账本，输出聚合后的 `total_equity`, `total_funds`, 并生成供 UI 渲染的 DataFrame。
6. **物理文件清理**：调用 `delete_ledger()` 成功彻底 unlink 沙盒的 json 与 db 文件，并自动回退 `active_ledger_id` 至 `main_live`。

### 1.5 独立测试套件执行结果
- 执行核心回归测试：
  ```
  py -3 -m pytest tests/test_infra.py tests/test_multi_ledger_manager.py tests/test_portfolio.py tests/test_streamlit_apptest_run.py -v
  ======================= 29 passed, 6 warnings in 25.69s =======================
  ```
- 执行防作弊测试套件中的 Test C：
  ```
  py -3 -m pytest tests/test_anticheat_suite.py -k "TestMultiLedgerIsolationAndProtection" -v
  ======================= 2 passed, 9 deselected in 1.79s =======================
  ```

---

## 2. Logic Chain (推演逻辑链)

1. **红线守卫结论**：
   - 观测事实 1.1 表明 4 大裁判文件的哈希值与预设真值 100% 吻合，git status 为空；
   - 观测事实 1.2 表明仿真执行算子签名与费率参数未被修改；
   - 由此推导：**物理安全红线 100% 未被逾越，无任何基线篡改行为。**

2. **代码真实性与非迎合结论**：
   - 观测事实 1.3 经 AST 全文语法树遍历，`multi_ledger_manager.py` 与修改的 `portfolio_manager.py` 均无伪造常数、无空 pass 占位、无假 mock；
   - 观测事实 1.4 实测证明，新建、修改、克隆账本时，操作系统磁盘上均产生了真实存在的 JSON 与 SQLite DB 文件，数据库中均有真实数据行被持久化，资产汇总函数亦基于真实数据逐账本累加；
   - 由此推导：**实现绝非迎合性假代码或门面代码，而是具备端到端完整数据流与物理落盘能力的生产级模块。**

3. **隔离性与主实盘保护结论**：
   - 观测事实 1.4 与 1.5 证明，主实盘账本不仅在元数据层受保护，在 API 层尝试删除时被显式抛错拦截，且在任何沙盒执行 `save_state()` 时，其派生的独立 `.db` 物理隔绝了对根目录 `portfolio_state.db` 的访问，消除了多账本共享主实盘 SQLite 导致的被清空隐患；
   - 由此推导：**多账本底层隔离性完全达标，主实盘安全防御机制真实生效。**

---

## 3. Caveats (注意事项与防御性加固建议)

在对抗性压力测试与深入审查中，审计员识别出以下 3 项边界防御建议（属于代码鲁棒性与异常防御范畴，不构成作弊违规）：

1. **路径遍历防护加强 (`.resolve()`)**：
   在 `multi_ledger_manager.py` 的 `delete_ledger` 中，判断待删除文件是否为主实盘文件目前采用 `f_path != self.main_file`。若索引中被恶意注入形如 `"data/../portfolio_ledger.json"` 的相对路径，未经 `.resolve()` 的路径比对可能绕过判断。建议加固为：`f_path.resolve() == self.main_file.resolve()`。
2. **账本 ID 大小写与空白防御**：
   `delete_ledger("main_live")` 目前采用全等比对。若传入 `" MAIN_LIVE "`，虽不会删除主实盘（因为索引中找不到该 ID 会返回 False），但建议使用 `ledger_id.strip().lower() == "main_live"` 统一抛出 `PermissionError`，保持防御语义的一致性。
3. **持仓批次原始 Dict 兼容性**：
   在 `portfolio_manager.py:3040` 的 `_recalculate_totals` 中，批次排序采用了 `lambda b: str(b.buy_date)`，当测试直接注入原始 `dict` 结构的 batch 时会因缺少属性抛出 `AttributeError`。建议兼容 `getattr(b, "buy_date", b.get("buy_date"))`。

---

## 4. Conclusion (终审裁决)

基于独立的物证检验、AST 语法树扫描、实机落盘比对以及回归测试：
- 4 大裁判基线文件 SHA256 **完好无损**；
- `DataLoader.simulate_execution` 签名与扣费逻辑 **完好无损**；
- 多账本管理引擎与 GUI 热装配 **100% 真实实现**，无假常量、无空 pass、无前后端断层；
- 存储隔离性经 SQLite 实机验证 **100% 有效**；
- 全套测试（29 项回归用例 + 2 项防作弊 Test C 用例）**100% 通过**。

**最终裁决：`CLEAN`（予以全额通过）**

---

## 5. Verification Method (独立复现核验指令)

下游评审员或主编排代理可运行以下命令复现本次审计全部核验过程：

```powershell
# 1. 运行 SHA256 哈希物理安全核验脚本
py -3 .agents/teamwork/auditor_r9_m1/check_hashes.py

# 2. 运行静态 AST 反作弊扫描脚本
py -3 .agents/teamwork/auditor_r9_m1/forensic_scan.py

# 3. 运行实机落盘与 SQLite 隔离检验脚本
py -3 .agents/teamwork/auditor_r9_m1/empirical_test.py

# 4. 运行全量核心回归测试套件 (29 项测试)
py -3 -m pytest tests/test_infra.py tests/test_multi_ledger_manager.py tests/test_portfolio.py tests/test_streamlit_apptest_run.py -v

# 5. 运行专项防作弊 Test C 测试
py -3 -m pytest tests/test_anticheat_suite.py -k "TestMultiLedgerIsolationAndProtection" -v
```
