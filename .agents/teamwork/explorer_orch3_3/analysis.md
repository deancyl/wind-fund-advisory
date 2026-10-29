# AGY2 投顾系统测试套件基线与红队架构测试规范勘测报告 (analysis.md)

## 勘测背景与使命
根据协同重构派发指令，本报告作为 **Test Suite & Red Team Explorer** 的只读勘测交付物，针对 `d:\Google\Workspace\Wind\AGY2_FundAdvisory` 项目的测试套件组织结构、4 个裁判基建文件完整性、既有 222 项测试通过基线进行全面摸底，并为后续执行架构级进化测试编写的 **Agent-4** 制定详尽、严密的测试落地蓝图。

---

## 1. 绝对红线：4 个只读裁判基建文件核验结果

根据最高准则与 R1 物理安全红线，严禁触碰、修改或解锁系统已设为只读的 4 个裁判基建文件。通过 Windows 原生文件系统属性与 SHA256 哈希比对，勘测结果如下：

| 文件名称 | 绝对物理路径 | 文件大小 (Bytes) | 只读属性 (IsReadOnly) | SHA256 内容哈希值 | 修改时间 |
| :--- | :--- | :---: | :---: | :--- | :---: |
| `judge_engine.py` | `D:\Google\Workspace\Wind\AGY2_FundAdvisory\judge_engine.py` | 42,175 | **True** (ReadOnly, Archive) | `76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF31CC07BE` | 2026/10/28 13:40:59 |
| `holdout_vault.py` | `D:\Google\Workspace\Wind\AGY2_FundAdvisory\holdout_vault.py` | 5,685 | **True** (ReadOnly, Archive) | `88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670BD031D2A` | 2026/10/27 21:47:43 |
| `AGENT_SPEC.md` | `D:\Google\Workspace\Wind\AGY2_FundAdvisory\AGENT_SPEC.md` | 8,237 | **True** (ReadOnly, Archive) | `A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B800CD63957` | 2026/10/28 13:39:36 |
| `tests/test_infra.py` | `D:\Google\Workspace\Wind\AGY2_FundAdvisory\tests\test_infra.py` | 10,524 | **True** (ReadOnly, Archive) | `B8D781BE8135BE05CF61E62E4B534E359985AD880F27FFB61228A33DF6B02A6A` | 2026/10/28 13:40:30 |

### 核验结论
1. **完全零侵入**：4 个裁判基建文件自 2026-10-27/28 固化以来，未发生任何字节级变动，只读属性 `IsReadOnly = True` 完好无损。
2. **Git 干净度**：`git status` 显示 `AGY2_FundAdvisory` 目录下为 Clean 状态，不存在任何脏修改或未跟踪文件。
3. **裁判引擎机制完整**：
   - `judge_engine.py` 内置未来函数因果探针（检验A）、日历年份 AST 反作弊锁（检验A+）、6 风格切片回归（检验B）、参数 ±15% 高原存活（检验C）、试错次数 DSR 递增惩罚（检验D）均处于最高防御戒备状态；
   - `holdout_vault.py` 内部硬计数器 `holdout_attempts` 严格锁死 3 次调用硬上限。

---

## 2. 现有测试套件架构与 222 项测试基线摸底

通过 `pytest --collect-only` 与沙箱运行，勘测了整个 `tests/` 目录组织结构与执行表现。

### 2.1 测试文件用例分布汇总（共 14 个模块，222 项测试）

| 序号 | 测试文件名 | 用例数 | 覆盖核心职责与业务范畴 |
| :---: | :--- | :---: | :--- |
| 1 | `tests/test_infra.py` | 15 | **裁判基建底层契约 (只读)**：矩阵对齐、因果探针、四岛接口合规、无风险利率扣除、盲测金库额度等 |
| 2 | `tests/test_acceptance_r1_r7.py` | 8 | **R1~R7 端到端全量验收**：滑块即拉即变、建仓回撤归零、银行股排雷豁免、拆单重合度豁免、界面9列、六维评分与AppTest渲染 |
| 3 | `tests/test_adversarial_m1.py` | 17 | **红队对抗性测试**：非A股资产免疫机制、现金组合/零市值/单一资产极端组合穿透、重合度去重计算 |
| 4 | `tests/test_adversarial_m1_challenger2.py` | 41 | **挑战者红队模糊测试 (Fuzzing)**：无效基金代码防崩溃、异常类型输入兜底、商誉与质押极值边界、股票代码模糊解析 |
| 5 | `tests/test_dynamic_risk_and_metrics.py` | 29 | **动态风险与指标单元测试**：C1~C5风险分层、问卷测评映射、人话指标计算、智能文本持仓解析、零起点蓝图覆盖 |
| 6 | `tests/test_e2e_gui_render.py` | 8 | **GUI 端到端与 AppTest 渲染**：沪深300点位同口径折算、盘前时钟与状态机协调、消除重复层级名、全档位模拟与AppTest全渲染 |
| 7 | `tests/test_live_rebalance_upgrades.py` | 12 | **实盘调仓网格与升级测试**：10日调仓网格倒计时、盘中紧急破位阈值、ETF折溢价过滤、增量资金投资计划、盘中预估盈亏 |
| 8 | `tests/test_milestone_2_3.py` | 7 | **流动性与拥挤度集成测试**：流动性温度计指标、双轨雷达矩阵、防守型资产动态触发、基金持仓拥挤度报警 |
| 9 | `tests/test_portfolio_manager.py` | 21 | **账本核心功能测试**：模式A/B接管、FIFO赎回惩罚拦截、调仓优先级路由、限购分仓、分红处理、穿透行业矩阵 |
| 10 | `tests/test_realtime_and_upgrades.py` | 11 | **实时行情与交易时钟测试**：实时基金/指数行情抓取缓存、零起点蓝图生成与注入、盘中变盘信号评估、交易时钟动作指引 |
| 11 | `tests/test_strategy_bridge.py` | 9 | **策略大脑桥接测试**：真实市场快照拉取、Trial29回测指标加载、免赎回费份额精算、AI调仓单生成与安全截断 |
| 12 | `tests/test_toolkit_integration.py` | 35 | **WindToolkit 湖仓集成测试**：Tier 1~4 全级别湖仓视图查询、商誉/存贷双高/质押穿透、OMO逆回购与DR007利差、只读不变量 |
| 13 | `tests/test_trading_clock_fee.py` | 10 | **交易时钟与费用精算测试**：交易日判定、交易窗口时钟倒计时、阶梯赎回费精算、申购费精算、回本周期测算 |
| 14 | `tests/test_ui_and_logic_refinements.py` | 5 | **UI 交互与排版精简逻辑测试**：卡片颜色对比度、极端单边熊市严格判定、选基漏斗与备选冲突、首屏高度压缩 |
| **合计** | **14 个文件** | **222** | **全项目端到端与单元测试总数** |

### 2.2 测试执行实测基线
在沙箱中执行完整回归测试：
- **执行命令**：`pytest -q tests/ --tb=short`
- **执行耗时**：205.56s（约 3 分 25 秒）
- **执行结果**：`222 passed, 489 warnings in 205.56s (0:03:25)`
- **基线结论**：既有 222 项测试用例 **100% 全部通过**。测试套件整体健康稳定，为后续 M3 架构级重构提供了坚实的回归防护网。

---

## 3. 勘测发现的架构级硬编码与逻辑倒挂缺陷

在勘测过程中，对相关业务源码进行了只读审视，发现了 3 个直接违反通用量化原则的架构硬编码与逻辑问题，需由 Agent-1/2/3 进行修复并由 Agent-4 设立红队拦截网：

### 3.1 缺陷 1：`portfolio_manager.py` 内部硬编码 40+ 个银行与金融股代码
- **位置**：`portfolio_manager.py` 第 3581 ~ 3596 行
- **现状**：
  ```python
  financial_codes = {
      # 银行
      "600000", "600015", "600016", "600036", "600908", "600919", ...
      # 保险与综合金融
      "601318", "601601", ...
      # 证券
      "600030", "601688", ...
  }
  ```
- **问题**：直接通过静态枚举 6 位股票代码来豁免金融股“存贷双高”。违背反硬编码最高准则！一旦组合持有未被硬编码收录的银行股（如宁波银行 002142、齐鲁银行 601665 等未列入或新股上市），将发生误判。必须改为基于申万行业或 DuckDB 行业属性动态识别。

### 3.2 缺陷 2：`app_gui.py` 内部写死静态 `cat_map`
- **位置**：`app_gui.py` 第 1869 ~ 1874 行
- **现状**：
  ```python
  cat_map = {
      "100032": "A股红利高股息", "005561": "A股红利低波", "011612": "科技成长进攻", ...
  }
  cat = cat_map.get(c, "其他存量资产")
  ```
- **问题**：采用写死的字典匹配核心池基金大类，任何扩展池基金或用户导入的自定义基金都会被草率归入“其他存量资产”，导致大类资产缺口图表失真。必须移除静态 `cat_map`，改为调用 `portfolio_manager.py` 的统一大类资产分类器。

### 3.3 缺陷 3：`strategy_bridge.py` 破位预警点位倒挂（防守线高于现价）
- **位置**：`strategy_bridge.py` 第 1613 ~ 1614 行
- **现状**：
  ```python
  if 3500.0 <= c300_price <= 4800.0:
      breakdown_c300 = round(c300_price * (4180.5 / 4053.0), 1)
  ```
- **问题**：`4180.5 / 4053.0 ≈ 1.031458 > 1`！计算出的“跌破防守点位”为 `c300_price * 1.0314`，居然比当前现价还要高 3.1%！向下跌破防守线本应严格低于现价，导致点位出现严重倒挂。必须严格基于当前指数点位与 MA20/MA60/MA120 真实相对位置动态计算输出向上进攻线（> 现价）与向下防守线（< 现价）。

---

## 4. 新增测试规范设计蓝图（供 Agent-4 落地参考）

建议 Agent-4 在 `tests/` 目录下新增专属的架构与红队审计测试套件 `tests/test_architecture_m3.py`，完整覆盖以下 4 大测试设计：

### 4.1 测试设计 1：AST 静态代码反硬编码审计
- **测试目的**：通过 Python AST 抽象语法树遍历扫描 `portfolio_manager.py`、`strategy_bridge.py`、`app_gui.py`，确保不存在硬编码的特定股票代码 if/else 分支或静态名单，且不存在静态 `cat_map`。
- **断言逻辑设计**：
  1. **扫描 `cat_map`**：
     - 在 `app_gui.py` 的 AST 树中扫描所有的 `ast.Assign` 节点；
     - 若赋值目标（`targets`）中包含变量名为 `'cat_map'` 的字典，直接断言失败；
     - 确保资产分类通过 `pm.resolve_fund_asset_category(...)` 或等价通用函数动态推导。
  2. **扫描 6 位股票代码硬编码豁免**：
     - 遍历 `portfolio_manager.py` 与 `strategy_bridge.py` 中所有的 `ast.Set`、`ast.List`、`ast.Tuple`、`ast.Compare` 节点；
     - 提取所有形如 `60XXXX`, `68XXXX`, `00XXXX`, `30XXXX` 的 6 位 A 股股票代码字面量；
     - 严禁出现像 `financial_codes = {"600000", ...}` 或 `if stock_code in {"600036", ...}` 形式的排雷豁免名单；
     - 验证排雷豁免完全通过行业属性（`industry in ["银行", "非银金融", ...]`）或财务公式（`cfo > 0`、利息保障倍数）动态计算。
- **推荐测试代码架构**：
  ```python
  def test_ast_audit_no_hardcoded_stock_codes_and_no_cat_map():
      import ast, re
      from pathlib import Path
      
      base_dir = Path(__file__).resolve().parent.parent
      
      # 1. 审计 app_gui.py 中不得存在 cat_map 静态字典
      gui_tree = ast.parse((base_dir / "app_gui.py").read_text(encoding="utf-8"))
      for node in ast.walk(gui_tree):
          if isinstance(node, ast.Assign):
              for target in node.targets:
                  if isinstance(target, ast.Name) and target.id == "cat_map":
                      pytest.fail("app_gui.py 中仍存在写死的 cat_map 静态映射字典！必须移除并调用通用分类解析器！")
      
      # 2. 审计 portfolio_manager.py 中不得存在 financial_codes 股票代码枚举
      pm_tree = ast.parse((base_dir / "portfolio_manager.py").read_text(encoding="utf-8"))
      stock_pattern = re.compile(r'^(60|68|00|30|83|92)\d{4}$')
      for node in ast.walk(pm_tree):
          # 检查 Assign 节点变量名不得为 financial_codes / bank_stock_codes 等
          if isinstance(node, ast.Assign):
              for target in node.targets:
                  if isinstance(target, ast.Name) and "financial_code" in target.id.lower():
                      pytest.fail(f"portfolio_manager.py 仍存在硬编码股票集合变量: {target.id}")
          # 检查比较表达式不得硬编码特定个股
          if isinstance(node, ast.Compare):
              # 遍历 comparator 中是否有特定个股代码
              for comp in node.comparators:
                  if isinstance(comp, ast.Constant) and isinstance(comp.value, str):
                      if stock_pattern.match(comp.value) and comp.value in ["600036", "601398", "601288"]:
                          pytest.fail(f"发现硬编码个股比较分支: {comp.value}")
  ```

### 4.2 测试设计 2：动态风险预算单调性与攻防状态机自适应
- **测试目的**：验证 C1 至 C5 的动态权益仓位权重在不同市场状态下，既能自适应宏观攻防，又严格满足风险单调性。
- **测试用例矩阵**：
  1. **情景 A：主升浪进攻态 (Bull Market)**
     - 构造或模拟市场快照：沪深300 在 MA20、MA60 之上，均线多头排列，期指贴水收敛（升水），期权 IV < 18%。
     - 计算 C1~C5 权重字典：
       `weights_c1 = compute_dynamic_tier_weights(df, "C1", snapshot_bull)` ... `weights_c5 = ...`
     - 统计各档位中权益类资产总权重 $W_{eq}$（包含沪深300、中证500、科创50、中证1000、红利资产等）；
     - 断言单调性：$W_{eq}(C1) < W_{eq}(C2) < W_{eq}(C3) < W_{eq}(C4) < W_{eq}(C5)$；
     - 断言进攻自适应：C5 权益仓位必须 $\ge 85\%$，且科创50与高弹性标的占比显著放大。
  2. **情景 B：震荡磨底态 (Oscillation/Bottoming)**
     - 构造市场快照：沪深300 在 MA20 附近缠绕，ERP 处于高分位数（>75%），DR007 流动性宽裕。
     - 断言单调性：$W_{eq}(C1) < W_{eq}(C2) < W_{eq}(C3) < W_{eq}(C4) < W_{eq}(C5)$；
     - 断言收息自适应：向红利低波与纯债收息资产倾斜，避免成长敞口高位损耗。
  3. **情景 C：熊市破位态 (Bear Market Breakdown)**
     - 构造市场快照：沪深300 跌破 MA60 与 MA120，均线向下发散，期权 IV 飙升（>25%），期指贴水扩大。
     - 断言单调性：$W_{eq}(C1) < W_{eq}(C2) < W_{eq}(C3) < W_{eq}(C4) < W_{eq}(C5)$；
     - 断言防守自适应：所有档位权益仓位较牛市自动压缩（含高进取型 C4/C5 自动降仓），高 Beta 权益敞口切换至纯债（H11009）与黄金（AU9999）避险。

### 4.3 测试设计 3：双向变盘触发点位逻辑校验
- **测试目的**：验证 `get_rebalance_grid_status()` 与 `evaluate_intraday_signal()` 输出的向上进攻线与向下防守线绝不倒挂。
- **断言逻辑设计**：
  - 选取多个具有代表性的指数现价输入（如 3000.0, 3500.0, 4053.0, 4500.0, 5000.0 点）：
  - 调用 `grid = StrategyBridge.get_rebalance_grid_status()`；
  - 提取：
    - 当前现价：`p_curr = grid["c300_current"]`
    - 向上进攻突破线：`p_surge = grid["surge_threshold_c300"]`
    - 向下防守破位线：`p_breakdown = grid["breakdown_threshold_c300"]`
  - 核心断言：
    - `assert p_surge > p_curr`（严格高于现价，严禁倒挂）
    - `assert p_breakdown < p_curr`（严格低于现价，彻底纠正原有 4180.5/4053.0 倒挂问题）
    - 触发动作方向说明校验：向上突破提示进攻加仓信号，向下跌破提示止损避险或锁定收益指令。

### 4.4 测试设计 4：界面无截断与 9 列规范在 AppTest 中的断言方法
- **测试目的**：使用 Streamlit 官方 `AppTest.from_file("app_gui.py")` 进行完整的无头渲染测试，从 UI 表现层断言零截断与 9 列规范。
- **断言方法与代码模板**：
  ```python
  def test_e2e_apptest_gui_zero_truncation_and_9_columns():
      from streamlit.testing.v1 import AppTest
      from pathlib import Path
      
      app_path = Path(__file__).resolve().parent.parent / "app_gui.py"
      at = AppTest.from_file(str(app_path), default_timeout=60)
      at.session_state.tier_determination_mode = "模式 A：按期望年化收益率滑块定档 (滑块即拉即变)"
      at.session_state.active_tier_val = "C3"
      at.run()
      
      assert len(at.exception) == 0, f"AppTest 运行异常: {[e.value for e in at.exception]}"
      
      # 1. 步骤三《建仓/调仓执行单》表格严格为 9 列
      expected_order_cols = [
          "基金代码", "基金名称", "份额", "目标占比(%)",
          "精确买入金额(元)", "最新净值", "实时估值涨跌(%)",
          "排雷与拥挤度", "实操分红与限购指引"
      ]
      found_9_col_df = False
      for df_elem in at.dataframe:
          df_val = df_elem.value
          if "基金代码" in df_val.columns:
              found_9_col_df = True
              assert len(df_val.columns) == 9, f"建仓执行单列数应为 9 列，实际为 {len(df_val.columns)}: {list(df_val.columns)}"
              assert list(df_val.columns) == expected_order_cols
      assert found_9_col_df, "未能在界面中捕获到建仓执行单 DataFrame"
      
      # 2. 存量调仓单控制在 9 列以内且带清晰图标
      # 3. 顶部 7 张核心卡片无 ... 截断
      for md in at.markdown:
          val = md.value
          if "main-metric-card" in val:
              assert "..." not in val and "…" not in val and "&hellip;" not in val, (
                  f"核心卡片中存在省略号截断: {val}"
              )
  ```

---

## 5. 勘测成果与交接指引

| 交付项目 | 状态 | 成果摘要 |
| :--- | :---: | :--- |
| **只读基建核验** | 100% 达标 | 4 个只读裁判基建文件只读属性与 SHA256 完整，绝无修改痕迹 |
| **既有测试基线** | 100% 达标 | 222 项测试用例全部通过（耗时 205.56s），基线稳固 |
| **硬编码与倒挂勘测** | 确诊完毕 | 捕获 `financial_codes`、`cat_map` 及防守点位倒挂 3 处缺陷 |
| **新增测试蓝图** | 交付就绪 | 为 Agent-4 提供了反硬编码 AST、风险单调性、变盘点位、AppTest 9列的完整方案 |

本分析报告已同步写入 `d:\Google\Workspace\Wind\.agents\teamwork\explorer_orch3_3\analysis.md`，并在同目录下输出交接文档 `handoff.md`。
