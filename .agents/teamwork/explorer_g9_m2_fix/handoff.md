# 极速录基局部导入缺陷调查与整改方案报告 (handoff.md)

**调查智能体**: explorer_g9_m2_fix (Roles: explorer, analyst)  
**工作目录**: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g9_m2_fix\`  
**调查对象**: `AGY2_FundAdvisory/app_gui.py` 及相关模块导入逻辑  
**交接时间**: 2026-11-08  

---

## 1. Observation (客观观察与直接代码证据)

### 1.1 `search_funds_in_catalog` 的物理定义与源头定位
- **物理定义文件**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\portfolio_manager.py` 第 1199 行：
  ```python
  1199: def search_funds_in_catalog(keyword: str, limit: int = 10) -> List[Dict[str, str]]:
  1200:     """
  1201:     按基金代码、中文名、拼音缩写从本地 28,177 基金库中高速检索匹配标的
  1202:     """
  ```
  该函数在 `portfolio_manager.py` 内部同时被第 1386 行引用。
- **`data_loader.py` 检查结果**:
  经全文本正则检索，`data_loader.py` 中**完全不存在** `search_funds_in_catalog`，亦未通过模块级别名导出。

### 1.2 `app_gui.py` 对 `search_funds_in_catalog` 的导入与调用分布
在 `AGY2_FundAdvisory/app_gui.py` 中共有 4 处涉及 `search_funds_in_catalog`：
1. **顶层静态导入 (第 69 行)**：
   ```python
   61: from portfolio_manager import (
   ...
   69:     search_funds_in_catalog,
   ...
   77: )
   ```
2. **热重载动态初始化导入 (第 162 行)**：
   ```python
   159:     from portfolio_manager import (
   ...
   162:         search_funds_in_catalog, parse_smart_text_holdings,
   ...
   166:     )
   ```
3. **运维工具坞 Dock 正常调用 (第 6176 行)**：
   ```python
   6176: matched = search_funds_in_catalog(search_kw, limit=10) if search_kw.strip() else []
   ```
   此处直接调用全局导入的 `search_funds_in_catalog`，无局部导入，运行完全正常。
4. **【缺陷所在】Popover 极速录基按钮回调 (第 5100 行)**：
   ```python
   5092: raw_in = bar_fund_in.strip()
   5093: matched_code = None
   5094: if raw_in:
   5095:     import re
   5096:     m_c = re.search(r'\b\d{6}\b', raw_in)
   5097:     if m_c:
   5098:         matched_code = m_c.group(0)
   5099:     else:
   5100:         from data_loader import search_funds_in_catalog
   5101:         res_search = search_funds_in_catalog(raw_in, limit=1)
   5102:         if res_search:
   5103:             matched_code = res_search[0]["fund_code"]
   ```

### 1.3 `app_gui.py` 全文局部导入（Indented Imports）扫描结果
对 `app_gui.py` 中所有缩进导入语句进行 AST 与正则排查，结果如下：
| 行号 | 语句 | 模块归属验证 | 状态 |
|---|---|---|---|
| 55 | `from multi_ledger_manager import MultiLedgerManager` | 存在于 `multi_ledger_manager.py` | ✅ 合法 |
| 58 | `from portfolio_manager import MultiLedgerManager` | 存在于 `portfolio_manager.py` | ✅ 合法 |
| 158-182 | 动态重载模块级批量导入 | 均在各自主模块中存在 | ✅ 合法 |
| 2109 | `from advisory_engine import RADAR_SECTOR_CATALOG` | 存在于 `advisory_engine.py:26` | ✅ 合法 |
| 2135 | `from data_loader import DataLoader` | 存在于 `data_loader.py:906` | ✅ 合法 |
| 5095 | `import re` | 标准库 | ✅ 合法 |
| **5100** | `from data_loader import search_funds_in_catalog` | **`data_loader.py` 无此函数** | 🚨 **致命缺陷 (ImportError)** |
| 6450 | `import uuid` | 标准库 | ✅ 合法 |
| 6451 | `from portfolio_manager import PendingOrder` | 存在于 `portfolio_manager.py:327` | ✅ 合法 |
| 7127 | `from portfolio_manager import HoldingItem` | 存在于 `portfolio_manager.py:31` | ✅ 合法 |

### 1.4 【额外潜伏隐患发现】第 2766 行 `data_loader.get_fund_metadata` 假属性
在 `app_gui.py` 第 2766 行（首屏今日投顾行动总开关资产元数据提取处）：
```python
2764: for _c in pm_instance.holdings.keys():
2765:     try:
2766:         _f_metas[_c] = data_loader.get_fund_metadata(_c) or {}
2767:     except Exception:
2768:         _f_metas[_c] = {}
```
- **实测验证**:
  ```powershell
  py -3 -c "import sys; sys.path.insert(0, 'AGY2_FundAdvisory'); import data_loader; print(hasattr(data_loader, 'get_fund_metadata'))"
  ```
  **输出**: `False`！
- **分析**: `get_fund_metadata` 是 `DataLoader` 类中的 `@classmethod`（`DataLoader.get_fund_metadata`），而非 `data_loader` 模块级函数。虽然该行外覆 `try...except` 未导致界面崩溃，但导致 `_f_metas` 恒为空字典 `{}`，虽然 `ActiveRiskSentry` 后续有一级穿透保护兜底，但该行逻辑属于潜在的静默失效点。

### 1.5 对抗性测试套件失败现场复现
运行 `tests/test_challenger_g9_m2_adversarial.py`：
- **执行命令**: `py -3 -m pytest tests/test_challenger_g9_m2_adversarial.py`
- **运行结果**: `1 failed, 29 passed in 25.88s`
- **唯一失败用例**:
  ```
  FAILED tests/test_challenger_g9_m2_adversarial.py::TestPopoverQuickFundEntryAdversarial::test_app_gui_popover_fund_name_search_no_broken_import
  AssertionError: CRITICAL DEFECT FOUND: app_gui.py 第 5100 行存在错误的 'from data_loader import search_funds_in_catalog'！
  data_loader 模块并无此函数（应使用 portfolio_manager.search_funds_in_catalog），该缺陷导致用户通过中文名称极速录基时直接抛出 ImportError 击穿 Tab 2！
  ```

---

## 2. Logic Chain (逻辑推导链)

1. **缺陷触发路径**:
   - 当用户使用 Popover 录基输入纯 6 位数字（如 `005561`）时，`re.search(r'\b\d{6}\b', raw_in)` 匹配成功，走 `if` 分支，绕过了第 5100 行。
   - 当用户输入中文简称（如“红利低波”、“易方达蓝筹”）、全称或拼音简写时，正则是 `None`，必然走 `else` 分支。
   - 执行到第 5100 行 `from data_loader import search_funds_in_catalog` 时，Python 解释器抛出 `ImportError: cannot import name 'search_funds_in_catalog' from 'data_loader'`。
   - 异常被 Tab 2 的错误边界（Rule 9）捕获，导致 Tab 2 提示“渲染出现局部异常”并中断当前操作，使得中文/拼音极速录基功能完全瘫痪。

2. **多余导入与单源性**:
   - `search_funds_in_catalog` 在 `app_gui.py` 顶层（第 69 行）及热重载初始化区（第 162 行）均已显式导入至模块级命名空间。
   - 在第 6176 行（运维工具坞），代码就是直接调用 `search_funds_in_catalog` 而无需局部导入。
   - 第 5100 行添加局部导入既冗余又导入了错误的源模块（`data_loader` 而非 `portfolio_manager`）。

3. **修复充要性**:
   - 将第 5100 行修改为 `from portfolio_manager import search_funds_in_catalog`（或复用全局导入），可立即恢复中文/拼音搜索入库功能。
   - 实测调用 `search_funds_in_catalog("红利低波", limit=1)` 能精准返回 `[{'fund_code': '005561', 'fund_name': '创金合信中证红利低波动指数A', ...}]`，完全满足业务需求。

---

## 3. Caveats (约束边界与已知假设)

1. **只读红线遵守**:
   本 Explorer 智能体严格遵循只读约束，未对 `AGY2_FundAdvisory/` 源码进行任何物理修改。
2. **测试套件状态**:
   除第 1043 行该项 AST 静态与动态探针失败外，对抗测试套件中其余 29 项用例（包含 HTML 纯化、行动总开关四态、极简双输入、Tab 2 双视图隔离、极端数值防御等）均已 100% 绿灯。
3. **伴生优化项建议**:
   第 2766 行的 `data_loader.get_fund_metadata` 虽不阻断当前测试，但建议 Worker 顺手修复为 `DataLoader.get_fund_metadata`，以彻底根除静默失效。

---

## 4. Conclusion & Recommended Worker Fix Strategy (结论与精准修复建议)

### 4.1 核心结论
Challenger 开出的 `REQUEST_CHANGES` 裁决 100% 属实，该缺陷是阻断 Milestone 2 正式合流的**唯一阻断性缺陷**。

### 4.2 给 Worker 的最小化精准整改补丁 (Diff)

#### 补丁 1 (必须执行，修复阻断性缺陷):
**目标文件**: `AGY2_FundAdvisory/app_gui.py` 第 5100 行  
```diff
--- a/AGY2_FundAdvisory/app_gui.py
+++ b/AGY2_FundAdvisory/app_gui.py
@@ -5097,7 +5097,7 @@
                             if m_c:
                                 matched_code = m_c.group(0)
                             else:
-                                from data_loader import search_funds_in_catalog
+                                from portfolio_manager import search_funds_in_catalog
                                 res_search = search_funds_in_catalog(raw_in, limit=1)
                                 if res_search:
                                     matched_code = res_search[0]["fund_code"]
```

#### 补丁 2 (强烈建议同步执行，消除静默失效隐患):
**目标文件**: `AGY2_FundAdvisory/app_gui.py` 第 2766 行  
```diff
--- a/AGY2_FundAdvisory/app_gui.py
+++ b/AGY2_FundAdvisory/app_gui.py
@@ -2763,7 +2763,7 @@
             _f_metas = {}
             for _c in pm_instance.holdings.keys():
                 try:
-                    _f_metas[_c] = data_loader.get_fund_metadata(_c) or {}
+                    _f_metas[_c] = DataLoader.get_fund_metadata(_c) or {}
                 except Exception:
                     _f_metas[_c] = {}
```

---

## 5. Verification Method (独立可复现核验指令)

Worker 修改完成后，执行以下指令完成核验：

### 5.1 缺陷针对性测试运行
```powershell
py -3 -m pytest tests/test_challenger_g9_m2_adversarial.py -k "test_app_gui_popover_fund_name_search_no_broken_import"
```
**期望结果**: 1 passed。

### 5.2 对抗性测试套件全量验证
```powershell
py -3 -m pytest tests/test_challenger_g9_m2_adversarial.py
```
**期望结果**: 30 passed, 0 failed in ~25s (100% 绿灯)。

### 5.3 历史回归测试用例验证
```powershell
py -3 -m pytest tests/test_sidebar_remodel_and_bugfixes.py
```
**期望结果**: 6 passed, 41 warnings (100% 绿灯)。
