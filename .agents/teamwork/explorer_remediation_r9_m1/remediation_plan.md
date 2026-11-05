# Milestone 1 (M1) 故障整改与代码加固执行方案 (Remediation Plan)

**Document**: `remediation_plan.md`  
**Author**: `explorer_remediation_r9_m1` (teamwork_explorer)  
**Target Worker**: `worker_remediation_r9_m1` (teamwork_implementer)  
**Status**: Ready for Surgical Execution  
**Timestamp**: 2026-11-05T15:02:00Z  

---

## 1. 故障全景汇总 (Failure Catalog & Root Cause Analysis)

基于 Challenger 1、Reviewer 2、Auditor 及 Challenger 2 提交的对抗压力测试与审计结果，本次 M1 共有 5 处需生产级外科手术式整改的核心问题点：

| 编号 | 模块 / 目标文件 | 故障性质 | 严重度 | 根因摘要 |
|---|---|---|---|---|
| **P1** | `multi_ledger_manager.py:324` | 物理保护绕过 | **HIGH** | `delete_ledger` 仅对完全相等的 `"main_live"` 拦截，大小写或首尾空格变体（如 `"MAIN_LIVE"`, `" main_live "`）未归一化导致未能抛出 `PermissionError`。 |
| **P2** | `multi_ledger_manager.py:337-350` | 路径遍历误删主实盘 | **CRITICAL** | `f_path != self.main_file` 未调用 `.resolve()`。当索引中含有未归一化路径（如 `"data/../portfolio_ledger.json"`）时比对为 `True`，触发 `f_path.unlink()` 抹除生产主实盘！ |
| **P3** | `multi_ledger_manager.py:371-376` | 静默回退主实盘踩踏隐患 | **MEDIUM** | `get_pm(ledger_id)` 当账本不存在时静默回退至 `main_live`，若调用方执行清空或修改持仓，将无意识污染或抹除主实盘。应抛出 `KeyError`。 |
| **P4** | `app_gui.py:1390-1412` | 账本切换状态逆反回弹 | **CRITICAL** | `switch_active_ledger` 未同步 `st.session_state.sel_tab2_active_ledger = target_id`，Tab 2 `st.selectbox` 在 rerun 时沿用旧控件状态将激活账本强行回退回 `main_live`。 |
| **P5** | `app_gui.py:1403-1405` | 风险档位单向冲刷洗白 | **CRITICAL** | `switch_active_ledger` 仅同步了 `active_tier_val`，未同步 `slider_target_return` 与 `target_return_val`。Tab 1 滑块在 rerun 时执行 `map_slider_to_tier(15.0)` 强行将非 C3 档位（C1/C2/C4/C5）重置回 `C3`。 |
| **P6** | `app_gui.py:3410-3435` | 孤儿/非法账本键致白屏崩溃 | **HIGH** | 当 `sel_tab2_active_ledger` 存有已删除或损坏的非法账本 ID 时，Streamlit 渲染 `selectbox` 因选项不包含该值抛出未捕获 `ValueError`，导致界面彻底白屏崩溃。 |

---

## 2. 目标文件 1: `AGY2_FundAdvisory/multi_ledger_manager.py` 整改方案

### 2.1 变更点 1: `delete_ledger` 规范化校验 `main_live` 防护
- **文件路径**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\multi_ledger_manager.py`
- **原代码行号**: 324-326
- **修改内容**: 使用 `str(ledger_id).strip().lower() == "main_live"` 拦截所有大小写及空白字符变体，无条件抛出 `PermissionError`。

#### Before:
```python
        if ledger_id == "main_live":
            raise PermissionError("主实盘账本受物理保护，禁止删除！")
```

#### After:
```python
        if str(ledger_id).strip().lower() == "main_live":
            raise PermissionError("主实盘账本受物理保护，禁止删除！")
```

---

### 2.2 变更点 2: `delete_ledger` 物理文件防遍历删除使用 `.resolve()`
- **文件路径**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\multi_ledger_manager.py`
- **原代码行号**: 336-351
- **修改内容**: 对 `f_path` 与 `db_path` 以及 `self.main_file` 与 `self.main_db` 均调用 `.resolve()` 后比对，物理杜绝以 `"data/../portfolio_ledger.json"` 等别名误删生产实盘文件。

#### Before:
```python
        # 物理清理文件
        f_path = self.root / target.get("file", "")
        db_path = self.root / target.get("db_file", "")

        if f_path.exists() and f_path != self.main_file:
            try:
                f_path.unlink()
            except Exception:
                pass

        if db_path.exists() and db_path != self.main_db:
            try:
                db_path.unlink()
            except Exception:
                pass
```

#### After:
```python
        # 物理清理文件 (使用 .resolve() 严防路径遍历别名误删主实盘)
        f_path = (self.root / target.get("file", "")).resolve()
        db_path = (self.root / target.get("db_file", "")).resolve()
        main_file_res = self.main_file.resolve()
        main_db_res = self.main_db.resolve()

        if f_path.exists() and f_path != main_file_res:
            try:
                f_path.unlink()
            except Exception:
                pass

        if db_path.exists() and db_path != main_db_res:
            try:
                db_path.unlink()
            except Exception:
                pass
```

---

### 2.3 变更点 3: `get_pm` 对不存在账本抛出 `KeyError` 消除静默踩踏
- **文件路径**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\multi_ledger_manager.py`
- **原代码行号**: 368-376
- **修改内容**: 当 `ledger_id` 不是 `main_live` 且在索引中不存在时，严禁静默回退到 `main_live`，必须显式抛出 `KeyError(f"账本未找到: {ledger_id}")`。

#### Before:
```python
        if ledger_id in self._pm_cache:
            return self._pm_cache[ledger_id]

        meta = self.get_ledger_meta(ledger_id)
        if not meta:
            # 回退至主实盘
            ledger_id = "main_live"
            meta = self._get_default_main_meta()
```

#### After:
```python
        norm_lid = str(ledger_id).strip().lower()
        if norm_lid == "main_live":
            ledger_id = "main_live"

        if ledger_id in self._pm_cache:
            return self._pm_cache[ledger_id]

        meta = self.get_ledger_meta(ledger_id)
        if not meta:
            if ledger_id == "main_live":
                meta = self._get_default_main_meta()
            else:
                raise KeyError(f"账本未找到: {ledger_id}")
```

---

### 2.4 `multi_ledger_manager.py` 完整 Patch 差分

```diff
--- a/AGY2_FundAdvisory/multi_ledger_manager.py
+++ b/AGY2_FundAdvisory/multi_ledger_manager.py
@@ -324,3 +324,3 @@
-        if ledger_id == "main_live":
+        if str(ledger_id).strip().lower() == "main_live":
             raise PermissionError("主实盘账本受物理保护，禁止删除！")
@@ -337,15 +337,17 @@
-        # 物理清理文件
-        f_path = self.root / target.get("file", "")
-        db_path = self.root / target.get("db_file", "")
+        # 物理清理文件 (使用 .resolve() 严防路径遍历别名误删主实盘)
+        f_path = (self.root / target.get("file", "")).resolve()
+        db_path = (self.root / target.get("db_file", "")).resolve()
+        main_file_res = self.main_file.resolve()
+        main_db_res = self.main_db.resolve()
 
-        if f_path.exists() and f_path != self.main_file:
+        if f_path.exists() and f_path != main_file_res:
             try:
                 f_path.unlink()
             except Exception:
                 pass
 
-        if db_path.exists() and db_path != self.main_db:
+        if db_path.exists() and db_path != main_db_res:
             try:
                 db_path.unlink()
             except Exception:
                 pass
@@ -368,9 +370,16 @@
+        norm_lid = str(ledger_id).strip().lower()
+        if norm_lid == "main_live":
+            ledger_id = "main_live"
+
         if ledger_id in self._pm_cache:
             return self._pm_cache[ledger_id]
 
         meta = self.get_ledger_meta(ledger_id)
         if not meta:
-            # 回退至主实盘
-            ledger_id = "main_live"
-            meta = self._get_default_main_meta()
+            if ledger_id == "main_live":
+                meta = self._get_default_main_meta()
+            else:
+                raise KeyError(f"账本未找到: {ledger_id}")
```

---

## 3. 目标文件 2: `AGY2_FundAdvisory/app_gui.py` 整改方案

### 3.1 变更点 1: 初始化与 `switch_active_ledger` 状态机闭环
- **文件路径**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py`
- **原代码行号**: 1379-1413
- **修改内容**:
  1. 在第 1380-1385 行 `get_pm(_cur_lid)` 处增加 `try...except KeyError:` 保护：当会话中存有被外部删除或非法 ledger_id 时，优雅自愈回退至 `main_live`；
  2. 定义 `TIER_TARGET_RETURN_MAP` 字典：
     ```python
     TIER_TARGET_RETURN_MAP = {
         "C1": 6.5,
         "C2": 9.0,   # ⚠️ 注意：必须设为 9.0！若设为 10.0 会被 map_slider_to_tier 误判为 C3！
         "C3": 15.0,
         "C4": 22.0,
         "C5": 50.0,
     }
     ```
  3. 在 `switch_active_ledger` 内部：
     - 同步更新控件键：`st.session_state.sel_tab2_active_ledger = target_ledger_id`
     - 同步更新滑块与收益率数值：
       ```python
       target_tier = str(meta.get("default_tier", "C3")).upper()
       if target_tier not in TIER_TARGET_RETURN_MAP:
           target_tier = "C3"
       st.session_state.active_tier_val = target_tier
       target_ret = TIER_TARGET_RETURN_MAP.get(target_tier, 15.0)
       st.session_state.target_return_val = target_ret
       st.session_state.slider_target_return = target_ret
       ```

#### Before (第 1379-1412 行):
```python
_cur_lid = st.session_state.active_ledger_id
if "pm" not in st.session_state or getattr(st.session_state.pm, "ledger_id", None) != _cur_lid:
    if st.session_state.mlm:
        st.session_state.pm = st.session_state.mlm.get_pm(_cur_lid)
    else:
        st.session_state.pm = PortfolioManager()

pm: PortfolioManager = st.session_state.pm
clock = pm.clock
calc = pm.calculator

def switch_active_ledger(target_ledger_id: str):
    mlm_inst = st.session_state.get("mlm") or (MultiLedgerManager.get_instance() if MultiLedgerManager else None)
    if "pm" in st.session_state and st.session_state.pm:
        try:
            st.session_state.pm.save_state(record_snapshot=True)
        except Exception:
            pass

    st.session_state.active_ledger_id = target_ledger_id
    if mlm_inst:
        mlm_inst.set_active_ledger_id(target_ledger_id)
        new_pm = mlm_inst.get_pm(target_ledger_id)
        st.session_state.pm = new_pm
        meta = mlm_inst.get_ledger_meta(target_ledger_id) or {}
        st.session_state.active_tier_val = meta.get("default_tier", "C3")

    st.session_state.tab2_diag_cache = None
    st.session_state.tab2_rebal_cache = None
    st.session_state.tab2_diagnosed = False
    st.session_state.tab2_rebalanced = False
    st.session_state.tab2_trigger_diagnose = False
    st.session_state.tab2_trigger_rebalance = False
    st.rerun()
```

#### After:
```python
_cur_lid = st.session_state.active_ledger_id
if "pm" not in st.session_state or getattr(st.session_state.pm, "ledger_id", None) != _cur_lid:
    if st.session_state.mlm:
        try:
            st.session_state.pm = st.session_state.mlm.get_pm(_cur_lid)
        except KeyError:
            # 容错自愈：当 active_ledger_id 已损坏或已删除时，平滑自愈回退至 main_live
            st.session_state.active_ledger_id = "main_live"
            st.session_state.sel_tab2_active_ledger = "main_live"
            st.session_state.pm = st.session_state.mlm.get_pm("main_live")
    else:
        st.session_state.pm = PortfolioManager()

pm: PortfolioManager = st.session_state.pm
clock = pm.clock
calc = pm.calculator

# 风险策略档位 -> 期望年化收益率基准映射表（双向映射绝对自洽，严禁 C2 设为 10.0 防漂移）
TIER_TARGET_RETURN_MAP = {
    "C1": 6.5,
    "C2": 9.0,   # 7.0 <= 9.0 < 10.0 -> map_slider_to_tier 严格返回 C2
    "C3": 15.0,  # 10.0 <= 15.0 < 16.0 -> map_slider_to_tier 严格返回 C3
    "C4": 22.0,  # 16.0 <= 22.0 < 30.0 -> map_slider_to_tier 严格返回 C4
    "C5": 50.0,  # 50.0 >= 30.0 -> map_slider_to_tier 严格返回 C5
}

def switch_active_ledger(target_ledger_id: str):
    mlm_inst = st.session_state.get("mlm") or (MultiLedgerManager.get_instance() if MultiLedgerManager else None)
    if "pm" in st.session_state and st.session_state.pm:
        try:
            st.session_state.pm.save_state(record_snapshot=True)
        except Exception:
            pass

    st.session_state.active_ledger_id = target_ledger_id
    st.session_state.sel_tab2_active_ledger = target_ledger_id
    if mlm_inst:
        mlm_inst.set_active_ledger_id(target_ledger_id)
        try:
            new_pm = mlm_inst.get_pm(target_ledger_id)
        except KeyError:
            target_ledger_id = "main_live"
            st.session_state.active_ledger_id = "main_live"
            st.session_state.sel_tab2_active_ledger = "main_live"
            new_pm = mlm_inst.get_pm("main_live")

        st.session_state.pm = new_pm
        meta = mlm_inst.get_ledger_meta(target_ledger_id) or {}
        target_tier = str(meta.get("default_tier", "C3")).upper()
        if target_tier not in TIER_TARGET_RETURN_MAP:
            target_tier = "C3"
        st.session_state.active_tier_val = target_tier
        target_ret = TIER_TARGET_RETURN_MAP.get(target_tier, 15.0)
        st.session_state.target_return_val = target_ret
        st.session_state.slider_target_return = target_ret

    st.session_state.tab2_diag_cache = None
    st.session_state.tab2_rebal_cache = None
    st.session_state.tab2_diagnosed = False
    st.session_state.tab2_rebalanced = False
    st.session_state.tab2_trigger_diagnose = False
    st.session_state.tab2_trigger_rebalance = False
    st.rerun()
```

---

### 3.2 变更点 2: Tab 2 下拉框选项防御性校验与非法键自愈清洗
- **文件路径**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py`
- **原代码行号**: 3409-3413
- **修改内容**:
  在渲染 Tab 2 顶部多账本管理吧台前，提取 `avail_lids = [l["id"] for l in all_ledgers]`，对 `st.session_state.sel_tab2_active_ledger` 进行存在性核验；若其不在 `avail_lids` 中（例如刚被删除或被外部会话破坏），强制复位回 `"main_live"`，防止 Streamlit `st.selectbox` 抛出 `ValueError` 引发全站白屏。

#### Before (第 3409-3413 行):
```python
        if mlm_inst:
            all_ledgers = mlm_inst.list_ledgers()
            active_lid = st.session_state.get("active_ledger_id", "main_live")
            active_idx = next((i for i, l in enumerate(all_ledgers) if l["id"] == active_lid), 0)
```

#### After:
```python
        if mlm_inst:
            all_ledgers = mlm_inst.list_ledgers()
            avail_lids = [l["id"] for l in all_ledgers]

            # 防御性清洗：若控件键残存已删除或非法账本 ID，立即重置为 main_live，杜绝 Streamlit ValueError 白屏崩溃
            if "sel_tab2_active_ledger" in st.session_state:
                if st.session_state.sel_tab2_active_ledger not in avail_lids:
                    st.session_state.sel_tab2_active_ledger = "main_live" if "main_live" in avail_lids else (avail_lids[0] if avail_lids else "main_live")

            active_lid = st.session_state.get("active_ledger_id", "main_live")
            if active_lid not in avail_lids:
                active_lid = "main_live" if "main_live" in avail_lids else (avail_lids[0] if avail_lids else "main_live")
                st.session_state.active_ledger_id = active_lid

            active_idx = next((i for i, l in enumerate(all_ledgers) if l["id"] == active_lid), 0)
```

---

### 3.3 `app_gui.py` 完整 Patch 差分

```diff
--- a/AGY2_FundAdvisory/app_gui.py
+++ b/AGY2_FundAdvisory/app_gui.py
@@ -1381,3 +1381,8 @@
     if st.session_state.mlm:
-        st.session_state.pm = st.session_state.mlm.get_pm(_cur_lid)
+        try:
+            st.session_state.pm = st.session_state.mlm.get_pm(_cur_lid)
+        except KeyError:
+            st.session_state.active_ledger_id = "main_live"
+            st.session_state.sel_tab2_active_ledger = "main_live"
+            st.session_state.pm = st.session_state.mlm.get_pm("main_live")
     else:
@@ -1389,2 +1394,10 @@
 calc = pm.calculator
+
+TIER_TARGET_RETURN_MAP = {
+    "C1": 6.5,
+    "C2": 9.0,
+    "C3": 15.0,
+    "C4": 22.0,
+    "C5": 50.0,
+}
 
 def switch_active_ledger(target_ledger_id: str):
@@ -1398,8 +1411,20 @@
     st.session_state.active_ledger_id = target_ledger_id
+    st.session_state.sel_tab2_active_ledger = target_ledger_id
     if mlm_inst:
         mlm_inst.set_active_ledger_id(target_ledger_id)
-        new_pm = mlm_inst.get_pm(target_ledger_id)
+        try:
+            new_pm = mlm_inst.get_pm(target_ledger_id)
+        except KeyError:
+            target_ledger_id = "main_live"
+            st.session_state.active_ledger_id = "main_live"
+            st.session_state.sel_tab2_active_ledger = "main_live"
+            new_pm = mlm_inst.get_pm("main_live")
+
         st.session_state.pm = new_pm
         meta = mlm_inst.get_ledger_meta(target_ledger_id) or {}
-        st.session_state.active_tier_val = meta.get("default_tier", "C3")
+        target_tier = str(meta.get("default_tier", "C3")).upper()
+        if target_tier not in TIER_TARGET_RETURN_MAP:
+            target_tier = "C3"
+        st.session_state.active_tier_val = target_tier
+        target_ret = TIER_TARGET_RETURN_MAP.get(target_tier, 15.0)
+        st.session_state.target_return_val = target_ret
+        st.session_state.slider_target_return = target_ret
 
@@ -3410,3 +3435,12 @@
         if mlm_inst:
             all_ledgers = mlm_inst.list_ledgers()
+            avail_lids = [l["id"] for l in all_ledgers]
+
+            if "sel_tab2_active_ledger" in st.session_state:
+                if st.session_state.sel_tab2_active_ledger not in avail_lids:
+                    st.session_state.sel_tab2_active_ledger = "main_live" if "main_live" in avail_lids else (avail_lids[0] if avail_lids else "main_live")
+
             active_lid = st.session_state.get("active_ledger_id", "main_live")
+            if active_lid not in avail_lids:
+                active_lid = "main_live" if "main_live" in avail_lids else (avail_lids[0] if avail_lids else "main_live")
+                st.session_state.active_ledger_id = active_lid
+
             active_idx = next((i for i, l in enumerate(all_ledgers) if l["id"] == active_lid), 0)
```

---

## 4. 压力测试套件核验与断言校准说明 (Test Suite Alignment)

在产品代码完成上述整改后，压力测试套件需同步进行断言对齐，以将“攻击暴露断言”转化为“加固防御成功断言”：

### 4.1 `tests/test_multi_ledger_manager_stress.py`
1. `test_protection_attack_case_and_whitespace_variants`:
   - 现行断言已为 `with pytest.raises(PermissionError)`，整改后将从 **FAILED 直接转为 PASSED**。
2. `test_protection_attack_path_traversal_and_file_alias`:
   - 现行断言已为 `assert main_json.exists()`，整改后将从 **FAILED 直接转为 PASSED**。
3. `test_get_pm_nonexistent_ledger_safety` (第 418-436 行):
   - 针对 `mlm.get_pm(fake_id)`，原先记录的是静默回退行为，现已升级为强安全规范抛出 `KeyError`。
   - Worker 需将断言对齐为：
     ```python
     with pytest.raises(KeyError, match="账本未找到"):
         mlm.get_pm(fake_id)
     ```

### 4.2 `tests/test_gui_multi_ledger_stress.py`
1. `test_invalid_ledger_id_fallback` (第 388-409 行):
   - 原先预期 `mlm.get_pm` 静默回退，现对齐为 `with pytest.raises(KeyError): mlm.get_pm(...)`。
2. `test_apptest_rapid_ledger_switch_and_metric_update` (第 480-547 行):
   - 原先 Challenger 2 实证断言 `reverted = True` 与 `tier_clobbered = True`。
   - 整改后修复生效，断言更新为：
     ```python
     # 验证切账本后控件键已同步且不再发生逆反回弹
     assert at.session_state.active_ledger_id == sb_id
     assert at.session_state.sel_tab2_active_ledger == sb_id
     # 验证专属风险档位 C5 完好保持，未被 Tab 1 滑块篡改回 C3
     assert at.session_state.active_tier_val == "C5"
     assert at.session_state.target_return_val == 50.0
     ```
3. `test_apptest_invalid_sel_tab2_active_ledger_unhandled_crash` (第 569-590 行):
   - 原先用 `with pytest.raises(ValueError)` 暴露白屏崩溃。
   - 整改后防御性清洗生效，断言更新为：
     ```python
     at.session_state["sel_tab2_active_ledger"] = "deleted_or_corrupted_ledger_0xDEAD"
     at.run()
     assert not at.exception, "非法控件键引发了异常白屏"
     assert at.session_state["sel_tab2_active_ledger"] == "main_live"
     ```

---

## 5. Remediation Worker 执行工序与门禁检查

### Step 1: 静态只读红线复核
确保 4 大裁判文件哈希完好无损：
```powershell
py -3 -c "import hashlib; [print(p, hashlib.sha256(open(p, 'rb').read()).hexdigest()[:12]) for p in ['AGY2_FundAdvisory/judge_engine.py', 'AGY2_FundAdvisory/holdout_vault.py', 'AGY2_FundAdvisory/AGENT_SPEC.md', 'tests/test_infra.py']]"
```

### Step 2: 实施 `multi_ledger_manager.py` 补丁
应用第 2 节中的 3 处修改。

### Step 3: 实施 `app_gui.py` 补丁
应用第 3 节中的 2 处修改。

### Step 4: 执行对抗压力测试套件
```powershell
# 1. 检验 MultiLedgerManager 对抗压力测试 (预期 8 passed in ~15s)
py -3 -m pytest tests/test_multi_ledger_manager_stress.py -v

# 2. 检验 GUI 对抗压力测试 (预期 8 passed in ~25s)
py -3 -m pytest tests/test_gui_multi_ledger_stress.py -v
```

### Step 5: 执行全量核心回归套件
```powershell
py -3 -m pytest tests/test_infra.py tests/test_portfolio.py tests/test_multi_ledger_manager.py tests/test_streamlit_apptest_run.py tests/test_anticheat_suite.py::TestMultiLedgerIsolationAndProtection -v
```
预期：31 passed 且 0 failed。

---

## 6. 预期整改成果与交付标准
1. **主实盘绝对零误删**：即使索引中被注入恶意路径遍历 `../portfolio_ledger.json`，`.resolve()` 强防线确保主实盘毫发无损。
2. **拒绝任何删除变体**：`" MAIN_LIVE "`、`"Main_Live"` 均被坚决抛出 `PermissionError` 物理拦截。
3. **消除静默回退污染**：非合法账本获取 `get_pm` 显式抛出 `KeyError`，GUI 层平滑自愈回退至 `main_live`。
4. **账本切换丝滑自洽**：新建、另存为、克隆账本切换后，控件键实时对齐，绝对不再逆反弹回主实盘。
5. **风险档位 100% 保持**：切换账本后滑块与收益率同步联动，彻底消灭 Tab 1 页面刷新重置为 C3 的缺陷。
6. **全站零白屏崩溃**：控件键残留已删除或非法账本 ID 时自动清洗回 `main_live`，杜绝 Streamlit `ValueError`。
