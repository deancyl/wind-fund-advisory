# 对抗性复核与应力测试审查报告 (handoff.md)

**审查智能体**: challenger_g9_m2_13_1 (Roles: critic, specialist)  
**工作目录**: `d:\Google\Workspace\Wind\.agents\teamwork\challenger_g9_m2_13_1\`  
**审查标的**: `AGY2_FundAdvisory/app_gui.py` 及相关测试套件  
**裁决结果**: **REQUEST_CHANGES (请求整改)**  
**交付时间**: 2026-11-08  

---

## 1. Observation (客观观察与直接代码证据)

### 1.1 HTML 纯化与 CommonMark 4+ 空格缩进防线 AST 静态扫描
- **工具指令与输出**:
  编写并运行 AST 审查脚本 `scripts/audit_ast_html_purification.py`：
  ```powershell
  py -3 scripts/audit_ast_html_purification.py
  ```
  **实测结果**:
  - `Total markdown calls`: 74
  - `Unsafe markdown calls (unsafe_allow_html=True)`: 1 (仅在 `app_gui.py` 行 204-208 的 `def safe_markdown_html` 唯一定义处)
  - `safe_markdown_html calls`: 101
  - `Violations count`: 0
- **边缘输入应力测试**:
  在 `tests/test_challenger_g9_m2_adversarial.py` 的 `TestHTMLPurificationAdversarialAST` 中：
  - 测试 4、8、16、24 个前导空格的多层嵌套 f-string，清洗后各行 100% 消除 4+ 空格与制表符前缀；
  - 测试 `None`、`""`、空白符多行输入，均安全返回 `""`；
  - 测试超长 50KB+ HTML 字符串，无内存泄漏与截断；
  - 测试 `render_historical_inflection_ruler_html` 输出，各行首尾空格已严格 `strip()`，即使嵌入深层缩进模板中经 `_clean_html` / `safe_markdown_html` 处理亦零源码泄露。

### 1.2 "今日投顾行动总开关" 四态覆盖推演
- **代码位置**: `AGY2_FundAdvisory/app_gui.py` 行 2760-2838 (`render_dual_wing_advisory_dashboard`)
- **推演实测结果**:
  在 `TestActionMasterSwitchFourStatesAdversarial` 中完整覆盖 4 种状态机分支：
  1. **状态 1 (🔴 锁定防御)**: 持仓中存在持有天数 < 7 天标的（如 2 天锁定期批次），触发 `action_type == "lock_shares"` 警报，总开关显示 `🔴 【锁定防御】存在未满 7 天惩罚期标的，已启动锁定保护严禁卖出`，按钮跳转 Tab 1 (`💼 持仓调仓`)。
  2. **状态 2 (🟡 时机就绪)**: 无 < 7 天锁仓，但存在持仓预警（如 C 类持有满 35 天高费率预警），总开关显示 `🟡 【时机就绪】主动风控检测到 1 项持仓异动优化机会`，建议 14:30 尾盘置换，按钮跳转 Tab 1。
  3. **状态 3 (🚀 空仓建仓)**: 实盘账本持仓数 `len(holdings) == 0`，总开关显示 `🚀 【空仓建仓】宏观 ERP 处于黄金击球区，建议一键启动新资建仓`，按钮跳转 Tab 0 (`🌱 新资建仓`)。
  4. **状态 4 (🟢 按兵不动)**: 持仓资产结构健康且均已满期无异动，总开关显示 `🟢 【按兵不动】持仓资产结构健康，安全垫充沛，今日安心吃息`，无需频繁折腾换仓。

### 1.3 Tab 1 L1 极简双输入与 C1 至 C5 档位参数匹配
- **代码位置**: `AGY2_FundAdvisory/app_gui.py` 行 3350-3418
- **推演实测结果**:
  在 `TestTab1L1InputsAndTiersAdversarial` 中：
  - `format_chinese_amount` 极端数值验证：0 元 -> `¥0.00 折合 0.00 万元`；-50,000 元 -> `-¥50,000.00 折合 -5.00 万元`；1 亿元 (1e8) -> `¥100,000,000.00 折合 10,000.00 万元 (1.00 亿元)`；小数 float `12345.6789` -> 四舍五入保留 2 位小数；非法类型优雅降级为 0 元无崩溃。
  - C1 至 C5 档位全域映射：`map_slider_to_tier` 针对 6.0% (C1)、8.5% (C2)、15.0% (C3)、22.0% (C4)、35.0% (C5) 映射自洽；`RISK_TIERS_CONFIG` 元数据齐备。
  - AI 自动托管只数规则：本金 <= 5 万元建议 4 只；5~30 万元建议 6 只；> 30 万元建议 8 只。

### 1.4 Tab 2 双视图解耦模式物理隔离
- **代码位置**: `AGY2_FundAdvisory/app_gui.py` 行 4927-6086 (`if is_t2_main_mode:`) 与行 6086-6547 (`else:`)
- **推演实测结果**:
  在 `TestTab2ViewModeDecouplingAdversarial` 中：
  - AST 严格确认：`dock_tab1, dock_tab2, dock_tab3, dock_tab4, dock_tab5, dock_tab6 = st.tabs(...)` 及其子模块完整置于 `else:` 分支内部，主模式下物理跳过，绝不渲染底部 6 大宽屏运维工具坞。
  - 单源滑块核验：`tab2_rebal_buf_slider` 全局仅存在 1 处真实控件定义，并保留 `# tab2_rebal_buf_slider_bot` 兼容标记。

### 1.5 🚨 发现的关键缺陷 (Critical Defect Found)
- **缺陷位置**: `AGY2_FundAdvisory/app_gui.py` 第 5100 行
- **缺陷代码**:
  ```python
  5096: m_c = re.search(r'\b\d{6}\b', raw_in)
  5097: if m_c:
  5098:     matched_code = m_c.group(0)
  5099: else:
  5100:     from data_loader import search_funds_in_catalog
  5101:     res_search = search_funds_in_catalog(raw_in, limit=1)
  5102:     if res_search:
  5103:         matched_code = res_search[0]["fund_code"]
  ```
- **真实运行时错误 (AppTest 捕获)**:
  ```
  Tab Error caught: 【💼 持仓调仓】渲染出现局部异常: cannot import name 'search_funds_in_catalog' from 'data_loader' (D:\Google\Workspace\Wind\AGY2_FundAdvisory\data_loader.py)
  ```
- **根因分析**:
  `search_funds_in_catalog` 函数位于 `portfolio_manager.py`（且在 `app_gui.py` 顶部第 69 行已经从 `portfolio_manager` 导入）。但在第 5100 行按钮事件处理中，开发人员误写了局部导入 `from data_loader import search_funds_in_catalog`。由于 `data_loader.py` 中不存在该函数，当用户在 Popover 极速录基框中输入中文名称或简称（例如“红利低波”）并点击“➕ 加入账本”时，将立即抛出 `ImportError` 导致 Tab 2 抛异常崩溃。

---

## 2. Logic Chain (逻辑推导链)

1. **HTML 纯化有效性**:
   - 观察：全站 AST 扫描确认所有富文本渲染均统一收口至 `safe_markdown_html`，`_clean_html` 在极端缩进、空行和特殊字符下均稳定抹除 4+ 空格。
   - 推导：M2 的 HTML 纯化防线（Rule 27）坚固可靠，彻底消灭了 CommonMark 引起的灰色代码块泄露。
2. **三项核心交互重构达标**:
   - 观察：“今日投顾行动总开关”四态准确切换，Tab 1 极简双输入与 C1-C5 托管正常，Tab 2 双视图物理分支隔离严格落实。
   - 推导：核心交互设计与外傻内精（L1+L2）架构原则已准确落地。
3. **极速录基局部导入致命 Bug**:
   - 观察：在极速录基 Popover 中，若用户未输入 6 位数字代码而是输入中文基金名称，触发 `else` 分支并执行第 5100 行 `from data_loader import search_funds_in_catalog`。
   - 推导：`data_loader` 模块无该属性，导致抛出 `ImportError`，用户无法使用中文名称极速录基，直接违反 M2 关于“极速录入支持代码或中文名”的交付契约。
4. **结论推导**:
   - 依据严苛复核铁律，存在确定性运行时崩溃缺陷时严禁带病审批上线，必须开出 `REQUEST_CHANGES` 单据要求立即纠偏。

---

## 3. Caveats (约束边界与已知假设)

1. **审查只读红线**:
   Challenger 严格遵守 Review-only 原则，未触碰或修改 `AGY2_FundAdvisory/` 下任何业务实现代码。
2. **测试用例覆盖边界**:
   所有测试均在本地真实环境与 Streamlit AppTest 沙箱中执行，未进行真实券商交易网关下单（无实盘资金消耗，符合测试规范）。

---

## 4. Conclusion (审查裁决结论)

**裁决**: **REQUEST_CHANGES (请求整改)**

虽然 M2 在 HTML 纯化、行动总开关、Tab 1 极简双输入、Tab 2 双视图隔离等大模块上表现优秀，但在 **Tab 2 极速录基 Popover** 中存在致命局部导入错误，导致中文基金录入崩溃。必须修复该单点缺陷后方可合流交付。

### 修复指导清单 (Actionable Fix)
修改 `AGY2_FundAdvisory/app_gui.py` 第 5100 行：
- **当前错误代码**:
  ```python
  from data_loader import search_funds_in_catalog
  ```
- **正确修复方案**:
  改为从 `portfolio_manager` 导入（或直接删除该行，直接复用第 69 行已全局导入的 `search_funds_in_catalog`）：
  ```python
  from portfolio_manager import search_funds_in_catalog
  ```

---

## 5. Verification Method (独立可复现核验指令)

### 5.1 缺陷复现指令 (Python 脚本一秒复现)
```powershell
py -3 -c "from data_loader import search_funds_in_catalog"
```
**复现输出**: `ImportError: cannot import name 'search_funds_in_catalog' from 'data_loader'`

### 5.2 对抗性测试套件运行指令
```powershell
# 运行 Challenger M2 对抗测试套件 (在修复前应有 1 项专项探针失败)
py -3 -m pytest tests/test_challenger_g9_m2_adversarial.py
```

### 5.3 侧边栏与历史回归测试运行指令
```powershell
py -3 -m pytest tests/test_sidebar_remodel_and_bugfixes.py
```
**实测结果**: `6 passed, 41 warnings in 22.62s` (100% 通过)
