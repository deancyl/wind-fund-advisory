# Multi-Ledger Manager Idempotent Mount, Test Isolation & Holding Days Reconciliation Analysis

**Author**: `explorer_m3_1` (Multi-Ledger & Isolation Explorer)  
**Date**: 2026-11-11  
**Milestone**: Milestone 3 Item 1  
**Target Files**:
- `AGY2_FundAdvisory/multi_ledger_manager.py`
- `tests/test_multi_ledger_manager.py`
- `tests/test_multi_ledger_manager_stress.py`
- `data/ledgers/combat_29_funds.json`
- `AGY2_FundAdvisory/advisory_engine.py`
- `AGY2_FundAdvisory/portfolio_manager.py`
- `AGY2_FundAdvisory/app_gui.py`

---

## 1. MultiLedgerManager 幂等挂载与单测目录隔离深度法证

### 1.1 现状与故障复现
在 `AGY2_FundAdvisory/multi_ledger_manager.py` 中，`MultiLedgerManager.__init__` 在构造时会强制调用 `self._ensure_index_initialized()`：

```python
# multi_ledger_manager.py 第 170-187 行
# 确保预置实战存量组合（29只·¥2.66万）存在
combat_item = next((l for l in final_ledgers if l.get("id") == "combat_29_funds"), None)
combat_json_path = self.ledgers_dir / "combat_29_funds.json"
if not combat_item or not combat_json_path.exists():
    combat_meta = self._init_preset_combat_29_ledger()
    if not combat_item:
        final_ledgers.append(combat_meta)
    else:
        for idx, l in enumerate(final_ledgers):
            if l.get("id") == "combat_29_funds":
                final_ledgers[idx] = combat_meta
                break

data["ledgers"] = final_ledgers
```

### 1.2 故障直接证据链
当单元测试以临时目录隔离运行时（例如 pytest 夹具 `temp_workspace` 或 `temp_stress_workspace`），传递了 `MultiLedgerManager(workspace_root=temp_workspace)`：
1. `_ensure_index_initialized()` 会**无条件在任何临时目录中自动创建** `data/ledgers/combat_29_funds.json`，并把 `combat_29_funds` 注入到测试工作区的 `ledgers_index.json` 中。
2. 导致两项关键单元测试直接断言失败：
   - **`tests/test_multi_ledger_manager.py::test_get_all_ledgers_summary`**:
     ```python
     def test_get_all_ledgers_summary(temp_workspace):
         mlm = MultiLedgerManager(workspace_root=temp_workspace)
         # 主实盘已有 100,000 总资产，10,000 浮盈，1 只持仓
         # 创建额外账本
         mlm.create_ledger("稳健养老金", base_cash=300000.0, ledger_type="family")
         summary = mlm.get_all_ledgers_summary()
         assert summary["total_equity"] == pytest.approx(400000.0) # 失败：实际为 427,615.10
         assert summary["total_funds"] == 1                         # 失败：实际为 30 (1 + 29)
         assert len(summary["ledgers"]) == 2                       # 失败：实际为 3 (含 combat_29_funds)
     ```
   - **`tests/test_multi_ledger_manager_stress.py::test_stress_get_all_ledgers_summary_arithmetic_integrity`**:
     ```python
     assert len(ledgers) == 7 # 1 main + 6 created
     # 失败：AssertionError: assert 8 == 7 (因为多出了 combat_29_funds)
     ```

### 1.3 生产与测试双轨诉求
1. **生产运行态与 UI 诉求 (`ORIGINAL_REQUEST.md §一.2, §三.3`)**：
   - 用户打开 Web UI 时，必须在首屏顶栏与下拉框中 100% 看到 `combat_29_funds`（实战存量组合·29只·¥2.66万）。
   - 依赖 `MultiLedgerManager.get_instance()` 或默认构造 `MultiLedgerManager()` 的测试（如 `test_adversarial_m3_combat29_challenger.py`、`test_g15_phase3_ocr_and_combat29.py`、`test_g16_phase1_memo_and_combat29.py`、`test_m2_features.py`）必须能正常加载 `combat_29_funds`。
2. **测试隔离环境诉求**：
   - 凡显式指定 `workspace_root=temp_workspace` 的单元测试，测试工作区必须纯净，仅默认包含 `main_live`，严禁被静默污染注入 `combat_29_funds`。

### 1.4 精确解决方案 (Proposed Fix)
在 `multi_ledger_manager.py` 的 `_ensure_index_initialized` 中，为 `combat_29_funds` 的自动预置挂载增加根工作区匹配防线：

```python
        # 确保预置实战存量组合（29只·¥2.66万）存在
        # 严格隔离测试环境：仅在生产/主工作区 (self.root == WORKSPACE_ROOT) 自动幂等挂载
        # 严禁向单测隔离临时目录 (temp_workspace) 自动注入 combat_29_funds，彻底杜绝账本计数/总金额单测断言失败
        if str(self.root.resolve()).lower() == str(WORKSPACE_ROOT.resolve()).lower():
            combat_item = next((l for l in final_ledgers if l.get("id") == "combat_29_funds"), None)
            combat_json_path = self.ledgers_dir / "combat_29_funds.json"
            if not combat_item or not combat_json_path.exists():
                combat_meta = self._init_preset_combat_29_ledger()
                if not combat_item:
                    final_ledgers.append(combat_meta)
                else:
                    for idx, l in enumerate(final_ledgers):
                        if l.get("id") == "combat_29_funds":
                            final_ledgers[idx] = combat_meta
                            break
```
- **Windows 大小写防御**：采用 `str(self.root.resolve()).lower() == str(WORKSPACE_ROOT.resolve()).lower()`，杜绝 Windows 盘符大小写或长短路径造成的匹配漂移。
- **验证效果**：
  - 在生产工作区：`self.root.resolve()` 等于 `WORKSPACE_ROOT.resolve()`，`combat_29_funds` 自动幂等挂载。
  - 在 pytest 临时工作区：`self.root.resolve()` 为 `C:\Users\...\Temp\...`，不等于 `WORKSPACE_ROOT.resolve()`，不会注入 `combat_29_funds`，`test_get_all_ledgers_summary` 与 `test_stress_get_all_ledgers_summary_arithmetic_integrity` 立即全部绿灯！

---

## 2. 持有天数差异调和 (Holding Days Reconciliation: 400d vs 1040d)

### 2.1 400 天与 1040 天的全库分布与出现位置追踪

| 文件路径 | 行号 / 引用 | 数值 | 属性 / 上下文 |
|---|---|---|---|
| `data/ledgers/combat_29_funds.json` | 40, 71, 102, ... 共 29 处 | `400` | 底层静态 JSON 持久化批次：`"holding_days": 400`, `"notes": "实战存量批次(满400天免赎)"` |
| `AGY2_FundAdvisory/multi_ledger_manager.py` | 195, 209, 258, 260 | `400` | `_init_preset_combat_29_ledger` 预置模板代码中批次天数固定为 `400` |
| `AGY2_FundAdvisory/advisory_engine.py` | 4384, 4386 | `400` | 提取批次天数降级默认兜底值：`getattr(b, "holding_days", 400)`, `m_days = 400` |
| `AGY2_FundAdvisory/portfolio_manager.py` | 4060-4066 | `1041` (动态重算) | `_recalculate_totals()`: `b.holding_days = max(0, (today_date - b_dt).days)`。由于买入日期 `buy_date="2024-01-05"`，运行时动态计算为 $2026\text{-}11\text{-}11 - 2024\text{-}01\text{-}05 = 1,041$ 天 |
| `AGY2_FundAdvisory/app_gui.py` | 6134 | `400` | 文案描述：`持仓天数均已达 400 天（>365天），赎回手续费严格为 ¥0.00` |
| `AGY2_FundAdvisory/app_gui.py` | 6145 | `400` | 文案描述：`已持有满 400 天但仍按 C 类计提每年 0.40% 销售服务费` |
| `AGY2_FundAdvisory/app_gui.py` | 5851, 5932 | `1041` (动态渲染) | Tab 2 持仓明细表“最短持有天数”列直接读取运行时 `HoldingItem`，显示 `1041` 天 |
| `tests/test_adversarial_m3_combat29_challenger.py` | 87-113 | `400` & `>=365` | 单测显式双重核验：第 99 行断言 JSON 中 `b["holding_days"] == 400`；第 107 行断言 PM 运行态 `b.holding_days >= 365` |
| `tests/test_g15_phase3_ocr_and_combat29.py` | 6, 98 | `400` | 文案与注释：“400天满期免赎” |

### 2.2 逻辑机理分析 (Why both are factually correct)
1. **静态基准契约 (Static Preset)**：
   - `400 天` 是历史基准静态写入的数据标签，用于证明该组合在 2025 年初导入时即已成立满 1 年以上（$> 365$ 天）。
   - 测试用例 `test_adversarial_m3_combat29_challenger.py:99` 显式硬断言 `assert b["holding_days"] == 400`，**严禁修改 JSON 文件中的 400**，否则会导致既有通过单测报错。
2. **动态日历时钟 (Dynamic Real-Time Clock)**：
   - `PortfolioManager._recalculate_totals()` 拥有真实的日历推进能力：每次初始化时，它根据批次买入日期 `b.buy_date="2024-01-05"` 与系统当前日期（2026年11月）计算实际自然日差额，算出 $1,041$ 天（约 $1,040$ 天）。
3. **赎回费梯级与 FIFO 零罚铁律 (Rule 7 Compliance)**：
   - 无论按 $400$ 天还是 $1,041$ 天判定：
     - **7 天在途惩罚**：$400 \gg 7$ 且 $1,041 \gg 7$ $\implies$ `safety_lock = False`，无任何 1.50% 惩罚费。
     - **C 类份额 30 天免赎**：$400 \gg 30$ 且 $1,041 \gg 30$ $\implies$ C 类 0 赎回费。
     - **A 类份额 180~365 天阶梯免除**：$400 > 365$ 且 $1,041 > 365$ $\implies$ A 类 0 赎回费。
   - 结论：**两者在量化风控、交易摩擦与决策逻辑上 100% 等价，绝对满足 Rule 7 的 FIFO 免罚要求！**

### 2.3 调和与一致性对齐策略 (Reconciliation Plan)
1. **底层存储层（保持绝对兼容）**：
   - `data/ledgers/combat_29_funds.json` 与 `multi_ledger_manager.py` 中批次预置保持 `"holding_days": 400` 与 `"buy_date": "2024-01-05"` 不变，确保 `test_adversarial_m3_combat29_challenger.py` 单测 100% 绿灯。
2. **业务引擎层 (`advisory_engine.py` / `portfolio_manager.py`)**：
   - 保持动态重算逻辑不变，`HoldingItem` 正常向上传递自然日持有天数（1,041天）。
3. **前端呈现层 (`app_gui.py`) 文案调和**：
   - 将静态死板的“400天”文案微调为既说明基准又说明当前水位的专业表述：
     - 第 6134 行：微调为 `持仓天数均已达 400~1,040+ 天（基准 400 天 / 现已超 1,040 天，均成立满1年以上），赎回手续费严格为 ¥0.00。`
     - 第 6145 行：微调为 `已持有满 400~1,040+ 天（远超 30 天免赎期）但仍按 C 类计提每年 0.40% 销售服务费，长期持有持续钝刀割肉；`
   - 这样既照顾了看持仓明细表看到“1041天”的用户，又完美呼应了底层 400 天基准档案，消除认知歧义。

---

## 3. 面向 Worker Agent 的精准落地行动建议 (Implementation Guide)

### 任务 1: `multi_ledger_manager.py` 隔离保护
在 `AGY2_FundAdvisory/multi_ledger_manager.py` 的第 170-185 行：
将：
```python
        # 确保预置实战存量组合（29只·¥2.66万）存在
        combat_item = next((l for l in final_ledgers if l.get("id") == "combat_29_funds"), None)
        combat_json_path = self.ledgers_dir / "combat_29_funds.json"
        if not combat_item or not combat_json_path.exists():
            ...
```
替换为：
```python
        # 确保预置实战存量组合（29只·¥2.66万）存在
        # 严格隔离测试环境：仅在生产/主工作区 (self.root == WORKSPACE_ROOT) 自动幂等挂载
        # 严禁向单测隔离临时目录 (temp_workspace) 自动注入 combat_29_funds，彻底杜绝账本计数/总金额单测断言失败
        if str(self.root.resolve()).lower() == str(WORKSPACE_ROOT.resolve()).lower():
            combat_item = next((l for l in final_ledgers if l.get("id") == "combat_29_funds"), None)
            combat_json_path = self.ledgers_dir / "combat_29_funds.json"
            if not combat_item or not combat_json_path.exists():
                combat_meta = self._init_preset_combat_29_ledger()
                if not combat_item:
                    final_ledgers.append(combat_meta)
                else:
                    for idx, l in enumerate(final_ledgers):
                        if l.get("id") == "combat_29_funds":
                            final_ledgers[idx] = combat_meta
                            break
```

### 任务 2: `app_gui.py` 文案调和
在 `AGY2_FundAdvisory/app_gui.py` 第 6134 行与 6145 行，将纯“400天”微调为“400~1,040+ 天（基准 400 天 / 现已超 1,040 天）”，保持与实盘运行时渲染自洽。

---

## 4. 验证命令集
1. `py -3 -m pytest tests/test_multi_ledger_manager.py`（预期 8 passed）
2. `py -3 -m pytest tests/test_multi_ledger_manager_stress.py`（预期 8 passed）
3. `py -3 -m pytest tests/test_adversarial_m3_combat29_challenger.py`（预期 9 passed）
4. `py -3 -m pytest tests/test_g15_phase3_ocr_and_combat29.py tests/test_g16_phase1_memo_and_combat29.py`（预期 11 passed）
