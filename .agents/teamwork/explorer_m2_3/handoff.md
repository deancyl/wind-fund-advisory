# Milestone 2: Feature 11 深度法证审计与 88 项端到端测试用例全景架构映射报告

**报告编写代理**: Explorer 3 (Teamwork Explorer)  
**工作区路径**: `d:\Google\Workspace\Wind`  
**报告交付路径**: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_m2_3\handoff.md`  
**完成时间**: 2026-11-15T08:58:00Z  

---

## 一、直接观察证据 (Observation)

### 1. Feature 11: `portfolio_manager.py` OCR 截图解析与文本识别缺陷法证

#### 1.1 空间块聚类通道被早退强制丢弃缺陷 (Premature Early Return)
- **文件路径**: `AGY2_FundAdvisory/portfolio_manager.py:1894-1925`
- **直接代码切片**:
  ```python
  # 1. 尝试以聚合成的完整多行文本直接送入 parse_smart_text_holdings 提取
  raw_lines = [item[2] for item in all_ocr_items]
  aggregated_text = "\n".join(raw_lines)
  parsed_candidates = parse_smart_text_holdings(aggregated_text)
  if parsed_candidates:
      seen = set()
      clean_res = []
      for p in parsed_candidates:
          c = p.get("fund_code")
          if c and c not in seen:
              seen.add(c)
              clean_res.append(p)
      if len(clean_res) >= 1:
          return clean_res  # <--- 第 1906-1907 行：致命早退！

  # 2. 空间块聚类提取分支（针对多栏布局排版）
  blocks = []
  current_block = []
  ...
  ```
- **法证事实**: 只要第 1 通道（文本流拼接解析）识别出哪怕 1 只基金（`len(clean_res) >= 1`），函数便**直接 return 退出**。第 2 通道（多栏空间块聚类提取与模糊对齐 `fuzzy_match_fund_by_name`）被物理阻断跳过，导致复杂移动端截图中的其他栏目标的、昨日收益与多列尾仓全部丢失。

#### 1.2 持有期与指数数字污染金额缺陷 (Amount Pollution by Lockup Numbers)
- **文件路径**: `AGY2_FundAdvisory/portfolio_manager.py:1403-1410` 与 `1470-1534`
- **直接代码切片**:
  ```python
  # 第 1403-1410 行：过滤词表
  for alias_kw in [
      "科创50", "中证1000", "中证500", "沪深300", "标普500", "30天",
      "红利低波", "中证红利", "裕祥回报", "华安黄金", "黄金ETF", "白酒",
      "集成电路", "动漫游戏", "新能源", "半导体", "纳斯达克100", "纳指",
      "ETF联接", "ETF", "联接", "A类", "C类"
  ]:
      remain_line = remain_line.replace(alias_kw, " ")

  ...
  # 第 1470-1482 行：兜底提取金额
  if amount <= 0:
      remaining_numbers = re.findall(r'([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)', remain_line)
      valid_nums = []
      for n_s in remaining_numbers:
          try:
              val = float(n_s.replace(',', ''))
              if val > 0:
                  valid_nums.append(val)
          except Exception:
              pass
      if valid_nums:
          amount = valid_nums[0]  # <--- 此处提前抓取了数字！

  ...
  # 第 1518-1524 行：天数提取滞后在金额提取之后！
  h_days = 30
  day_match = re.search(r'(?:持有|已持|持仓|买了|买入|历时)?\s*(\d+)\s*(?:天|日)', remain_line)
  if day_match:
      h_days = int(day_match.group(1))
      remain_line = remain_line.replace(day_match.group(0), " ")
  ```
- **实测报错证据**:
  - `test_t11_2_2_complex_multi_number_interference` 传入 `"中证500增强C 001234 锁定180天 8888.88元"`：
    `AssertionError: Expected 8888.88, got 180.0`
  - `test_tier4_scenario_5_mobile_ocr_dual_channel_fusion` 传入 `"富国中证红利指数增强A 100032 锁定180天 35,000.00元"`：
    `AssertionError: assert 34820.0 < 1.0`（系统误将 `180.0` 作为持仓金额，`abs(180.0 - 35000.0) == 34820.0`）
- **根因**:
  1. `day_match` 提取持有天数逻辑（1518行）严重滞后于金额提取逻辑（1470行）。
  2. 词表与正则缺少 `"锁定\d+天"`、`"中证A500"`、`"中证2000"` 等常用锁定模式与宽基指数。
  3. 当文本无显式 `金额:` 前缀时，系统在 1471 行通过 `re.findall` 提取所有数字，`"180"` 排在 `"35,000.00"` 之前，直接被当成 `amount = 180.0` 捕获！

#### 1.3 `parse_smart_text_holdings` 缺少同基金去重聚合机制
- **文件路径**: `AGY2_FundAdvisory/portfolio_manager.py:1542-1562`
- **实测报错证据**:
  - `test_t11_2_3_dual_channel_deduplication_unification` 传入两行相同内容 `"005561 创金合信红利低波 50000元\n005561 创金合信红利低波 50000元"`：
    `AssertionError: assert 2 == 1`
  - **根因**: `parse_smart_text_holdings` 逐行解析后直接 `parsed_results.append(...)`，未对重复粘贴的同代码标的进行 `fund_code` 幂等去重。

---

### 2. E2E 全量测试套件 `tests/test_g19_m2_routing_and_rolling_dca.py` 执行法证
- **运行命令**: `py -3 -m pytest tests/test_g19_m2_routing_and_rolling_dca.py -q`
- **当前执行结果**: **74 passed, 14 failed in 16.60s** (总用例数: 88 个)
- **14 项失败用例法证清单**:
  1. `TestFeature9RollingDCA3YBacktest::test_t9_1_1_bimonthly_180d_rolling_dca_backtest` -> `StrategyBridge.calculate_rolling_dca_3y_backtest` 未实现
  2. `TestFeature9RollingDCA3YBacktest::test_t9_1_2_bimonthly_365d_rolling_dca_backtest` -> 同上
  3. `TestFeature9RollingDCA3YBacktest::test_t9_1_3_quarterly_180d_rolling_dca_backtest` -> 同上
  4. `TestFeature9RollingDCA3YBacktest::test_t9_1_4_quarterly_365d_rolling_dca_backtest` -> 同上
  5. `TestFeature9RollingDCA3YBacktest::test_t9_2_3_period_count_lower_bound` -> 同上（要求周期数 N >= 12）
  6. `TestFeature9RollingDCA3YBacktest::test_t9_3_2_orthogonal_rolling_dca_x_table_rendering` -> 同上
  7. `TestFeature10FrictionBillDynamicAndBacktestFees::test_t10_1_1_pure_bond_dynamic_cagr_and_mdd` -> `cagr_pct` 残留伪常数 16.85
  8. `TestFeature10FrictionBillDynamicAndBacktestFees::test_t10_1_2_pure_tech_dynamic_cagr_and_mdd` -> 同上
  9. `TestFeature10FrictionBillDynamicAndBacktestFees::test_t10_1_5_ast_scan_zero_fake_constants_in_friction_bill` -> 测试用例中正则表达式 `r"def calculate_mutual_fund_friction_bill\([^)]*\):"` 因原函数包含返回值注解 `-> Dict[str, Any]:` 而未匹配到代码块抛出 `assert None is not None`
  10. `TestFeature10FrictionBillDynamicAndBacktestFees::test_t10_3_1_orthogonal_dynamic_friction_bill_x_combat29` -> `StrategyBridge.get_combat_29_vs_reconstructed_6_preset` 返回字典缺少 `raw_29` 与 `reconstructed_6` 键
  11. `TestFeature11OCRDualChannelUnionAndStopwords::test_t11_2_2_complex_multi_number_interference` -> `锁定180天` 导致金额被误认为 `180.0`
  12. `TestFeature11OCRDualChannelUnionAndStopwords::test_t11_2_3_dual_channel_deduplication_unification` -> 重复代码未去重返回 2 条记录
  13. `TestTier4RealWorldWorkloads::test_tier4_scenario_4_historical_3y_rolling_dca_full_fees` -> 摩擦账单包含假常数 16.85
  14. `TestTier4RealWorldWorkloads::test_tier4_scenario_5_mobile_ocr_dual_channel_fusion` -> `锁定180天` 导致 35000 误提取为 180

---

## 二、逻辑推导链 (Logic Chain)

```
[Observation 1.1] 
portfolio_manager.py 第 1906 行存在 if len(clean_res) >= 1: return clean_res
     │
     ├── 逻辑推导 1.1.1: 只要文本解析通道命中 1 条记录，后续空间块聚类分支就被永久跳过。
     └── 落地设计 1.1.2: 彻底删除该早退 return，分别执行 Channel 1 (文本流) 与 Channel 2 (空间聚类)，
                       在函数末尾以 fund_code 为主键执行并集融合 (Union Fusion)。

[Observation 1.2] 
持有天数匹配 (1518 行) 位于金额匹配 (1470 行) 之后，且未覆盖 "锁定180天"
     │
     ├── 逻辑推导 1.2.1: 当文本无显式 "金额:" 时，re.findall 会把 "锁定180天" 中的 180 排在前面被误判为金额。
     └── 落地设计 1.2.2: 
           1. 将持有天数正则提前至第 1411 行 (金额提取之前)；
           2. 支持 "锁定\d+天"、"(\d+)天持有"、"(持有\d+天)" 并就地从 remain_line 剥离为空格；
           3. 扩充 alias_kw 清洗词表：加入 "中证A500", "A500", "中证2000", "中证800", "科创100" 等；
           4. 引入显式 "元" 匹配正则 (yuan_match: r'([0-9,.]+)\s*元') 优先捕获真实金额。

[Observation 1.3] 
parse_smart_text_holdings 尾部未执行去重
     │
     ├── 逻辑推导 1.3.1: 用户重复输入或文本流中多行出现相同基金会导致多份 duplicate holding。
     └── 落地设计 1.3.2: 在 parse_smart_text_holdings 返回前，按 fund_code 顺序去重，保留单条。

[Observation 2] 
88 项测试用例中 74 项已通过，仅 14 项失败，高度收敛于 F9, F10, F11
     │
     ├── 逻辑推导 2.1: F7 (自动路由), F8 (样式), F12 (移动布局), F13 (工具坞) 已完全就绪 (48/48 通过)。
     ├── 逻辑推导 2.2: F9 仅需在 StrategyBridge 实现 calculate_rolling_dca_3y_backtest (6项立即转绿)。
     ├── 逻辑推导 2.3: F10 需动态精算 CAGR/MDD 并补齐 preset 字典键与测试断言正则 (4项立即转绿)。
     └── 逻辑推导 2.4: F11 依上述推导修正后 (2项用例 + 2项场景立即转绿)。
```

---

## 三、Feature 11 详细代码改造方案 (Proposed Diffs)

### 1. `AGY2_FundAdvisory/portfolio_manager.py` 改造

#### 改造点 1：扩充词表、持有天数前置提取剥离与金额匹配增强 (约 1403-1485 行)
```python
<<<<
        # 将已识别的中文名与大盘缩写从 remain_line 中清理，避免基金名中的数字（如科创50的50、中证1000的1000）被误识别为金额
        if fund_name in remain_line:
            remain_line = remain_line.replace(fund_name, " ")
        for alias_kw in [
            "科创50", "中证1000", "中证500", "沪深300", "标普500", "30天",
            "红利低波", "中证红利", "裕祥回报", "华安黄金", "黄金ETF", "白酒",
            "集成电路", "动漫游戏", "新能源", "半导体", "纳斯达克100", "纳指",
            "ETF联接", "ETF", "联接", "A类", "C类"
        ]:
            remain_line = remain_line.replace(alias_kw, " ")
====
        # 将已识别的中文名与大盘缩写从 remain_line 中清理，避免基金名中的数字（如科创50的50、中证A500的500）被误识别为金额
        if fund_name in remain_line:
            remain_line = remain_line.replace(fund_name, " ")
        # 宽基指数代码与持有期数字扩充词表 (长词优先，彻底阻断数字污染)
        for alias_kw in [
            "中证2000", "中证1000", "中证800", "中证500", "沪深300", "中证A500", "A500", "A50",
            "科创100", "科创50", "创业板50", "标普500", "富时100", "富时A50", "日经225", "纳斯达克100", "纳指100", "纳指",
            "红利低波100", "红利低波", "中证红利", "裕祥回报", "华安黄金", "黄金ETF", "白酒",
            "集成电路", "动漫游戏", "新能源", "半导体", "人工智能", "芯片", "恒生科技", "恒生指数",
            "30天持有", "60天持有", "90天持有", "180天持有", "360天持有", "365天持有",
            "1年持有", "2年持有", "3年持有", "6个月持有", "3个月持有", "12个月持有",
            "ETF联接", "ETF", "联接", "A类", "C类", "E类"
        ]:
            remain_line = remain_line.replace(alias_kw, " ")

        # ── 提前解析并剥离持有天数与锁定天数 (彻底杜绝持有期天数误充当持仓金额) ──
        h_days = 30
        lock_match = re.search(r'[\(（]?(?:锁定|持有|已持|持仓|买了|买入|历时)?\s*(\d+)\s*(?:天|日)(?:持有)?[\)）]?', remain_line)
        if lock_match:
            h_days = int(lock_match.group(1))
            remain_line = remain_line.replace(lock_match.group(0), " ")
        elif re.search(r'[\(（]?(\d+)\s*(?:个)?月(?:持有)?[\)）]?', remain_line):
            m_m = re.search(r'[\(（]?(\d+)\s*(?:个)?月(?:持有)?[\)）]?', remain_line)
            h_days = int(m_m.group(1)) * 30
            remain_line = remain_line.replace(m_m.group(0), " ")
        elif re.search(r'[\(（]?(\d+)\s*年(?:持有)?[\)）]?', remain_line):
            y_m = re.search(r'[\(（]?(\d+)\s*年(?:持有)?[\)）]?', remain_line)
            h_days = int(y_m.group(1)) * 365
            remain_line = remain_line.replace(y_m.group(0), " ")
        elif any(k in cleaned_line for k in ["已持满", "满30天", "免赎回费", "免赎"]):
            h_days = 45
        elif any(k in cleaned_line for k in ["刚买", "未满7天", "不满7天", "新买"]):
            h_days = 3
>>>>
```

并在金额匹配部分增加显式 `"元"` 匹配：
```python
        # 显式优先匹配带“元”或“¥”的金额数字 (如 15,200.00元, 35000元)
        if amount <= 0:
            yuan_match = re.search(r'(?:¥|￥)?\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)\s*元', remain_line)
            if yuan_match:
                amount = float(yuan_match.group(1).replace(',', ''))
                remain_line = remain_line.replace(yuan_match.group(0), " ")
```

并在 `parse_smart_text_holdings` 末尾增加去重：
```python
<<<<
    return parsed_results
====
    # 双通道单标的去重保护：按 fund_code 顺序去重
    seen_dedup = set()
    clean_dedup_results = []
    for item in parsed_results:
        fc = item.get("fund_code")
        if fc and fc not in seen_dedup:
            seen_dedup.add(fc)
            clean_dedup_results.append(item)
    return clean_dedup_results
>>>>
```

#### 改造点 2：双通道并集融合 (Dual-Channel Union Fusion) (约 1894-1925 行)
```python
<<<<
    # 1. 尝试以聚合成的完整多行文本直接送入 parse_smart_text_holdings 提取
    raw_lines = [item[2] for item in all_ocr_items]
    aggregated_text = "\n".join(raw_lines)
    parsed_candidates = parse_smart_text_holdings(aggregated_text)
    if parsed_candidates:
        seen = set()
        clean_res = []
        for p in parsed_candidates:
            c = p.get("fund_code")
            if c and c not in seen:
                seen.add(c)
                clean_res.append(p)
        if len(clean_res) >= 1:
            return clean_res

    # 2. 空间块聚类提取分支（针对多栏布局排版）
====
    # 1. 通道一：以聚合成的完整多行文本直接送入 parse_smart_text_holdings 提取
    raw_lines = [item[2] for item in all_ocr_items]
    aggregated_text = "\n".join(raw_lines)
    channel1_holdings = parse_smart_text_holdings(aggregated_text)

    # 2. 通道二：空间块聚类提取分支（针对多栏复杂布局排版，绝不早退）
>>>>
```
并在函数最后（第 2019 行原 `return structured_holdings` 处）改为双通道融合：
```python
<<<<
    return structured_holdings
====
    # 3. ── 双通道并集融合与信息补全 (Dual-Channel Union Fusion) ──
    # 以 fund_code 为主键合并两路通道，互补空间块字段与文本流字段
    fused_map: Dict[str, Dict[str, Any]] = {}
    for h in channel1_holdings:
        code = h.get("fund_code")
        if code:
            fused_map[code] = dict(h)

    for h in structured_holdings:
        code = h.get("fund_code")
        if not code:
            continue
        if code not in fused_map:
            fused_map[code] = dict(h)
        else:
            # 融合：优先保留或增强空间块特有的昨日收益、收益率、校验标记
            existing = fused_map[code]
            for k, v in h.items():
                if k not in existing or existing[k] is None or (existing[k] == 0.0 and v not in (0.0, None)):
                    existing[k] = v
                elif k in ("yesterday_pnl", "yesterday_return", "cross_check_verified") and v is not None:
                    existing[k] = v

    return list(fused_map.values())
>>>>
```

---

## 四、88 项端到端测试用例全景架构映射 (Test Inventory & Architectural Mapping)

在 `tests/test_g19_m2_routing_and_rolling_dca.py` 中，88 个测试用例严格按照 TEST_INFRA.md 四阶系统化测试方法学构建：
- **Tier 1: Category-Partition (分类划分)**
- **Tier 2: Boundary Value Analysis (边界值分析)**
- **Tier 3: Pairwise Combinatorial (正交组合测试)**
- **Tier 4: Real-World Workload Testing (真实业务综合负载场景)**

### 全景映射表

| # | Feature / Group | Test Method | Tier | Expected Contract / Function / Keys | Current Status | Root Cause / Note |
|---|-----------------|-------------|------|-------------------------------------|----------------|-------------------|
| 1 | **F7: 存量账本自动路由** | `test_t7_1_1_combat29_auto_routes_to_tab2` | Tier 1 | `len(holdings)>=10` 触发跳转 Tab 2, 设置 `pending_cross_tab_jump`, `tab2_diagnosed=True` | **PASSED** | 逻辑正常 |
| 2 | F7 | `test_t7_1_2_empty_ledger_stays_tab1` | Tier 1 | 空账本 (0标的) 不跳转，留在 Tab 1 | **PASSED** | 边界正常 |
| 3 | F7 | `test_t7_1_3_small_ledger_stays_tab1` | Tier 1 | 3 只标的 (<10) 不跳转 | **PASSED** | 边界正常 |
| 4 | F7 | `test_t7_1_4_secondary_render_preserves_user_tab` | Tier 1 | 已完成首次路由 (`_initial_ledger_routed=True`)，用户点击 Tab 1 不强制回跳 | **PASSED** | 幂等正常 |
| 5 | F7 | `test_t7_1_5_manual_switch_ledger_routes` | Tier 1 | 静态代码扫描：`switch_active_ledger` 包含跳转持仓调仓逻辑 | **PASSED** | 源码正常 |
| 6 | F7 | `test_t7_2_1_boundary_9_funds_no_jump` | Tier 2 | 边界探测：`len=9` 不跳转 | **PASSED** | 边界阈值精准 |
| 7 | F7 | `test_t7_2_2_boundary_10_funds_triggers_jump` | Tier 2 | 边界探测：`len=10` 刚好触发跳转 | **PASSED** | 边界阈值精准 |
| 8 | F7 | `test_t7_2_3_boundary_11_funds_triggers_jump` | Tier 2 | 边界探测：`len=11` 触发跳转 | **PASSED** | 边界阈值精准 |
| 9 | F7 | `test_t7_2_4_combat29_real_production_ledger_routing` | Tier 2 | 生产实盘 `combat_29_funds` (29基) 触发跳转并在详情中含 "29" | **PASSED** | 真实数据验证 |
| 10 | F7 | `test_t7_2_5_pending_cross_tab_jump_consumption_lifecycle` | Tier 2 | `pop` 消费后清除 `pending_cross_tab_jump`，单次有效 | **PASSED** | 生命周期健全 |
| 11 | F7 | `test_t7_3_1_orthogonal_initial_routing_x_mobile_viewport` | Tier 3 | [正交] 自动路由 × 移动视口 (`view=mobile`) -> 双重标记正确 | **PASSED** | 正交组合健全 |
| 12 | F7 | `test_t7_3_2_orthogonal_initial_routing_x_pathology_alert` | Tier 3 | [正交] 自动路由 × 20只尾仓账本 -> 诊断就绪标记 True | **PASSED** | 正交组合健全 |
| 13 | **F8: 样式合并与手机端选择器** | `test_t8_1_1_memo_card_style_consolidation` | Tier 1 | 扫描 `.chief-memo-container`, `.chief-memo-grid`, `.chief-memo-capsule` | **PASSED** | 样式声明完备 |
| 14 | F8 | `test_t8_1_2_global_stylesheet_chief_memo_grid_declarations` | Tier 1 | 全局样式包含 `memo-desk` 容器查询与 5 列网格声明 | **PASSED** | 声明完备 |
| 15 | F8 | `test_t8_1_3_mobile_css_stcolumn_selector_present` | Tier 1 | 移动端包含 `div[data-testid="stColumn"]` 响应式声明 | **PASSED** | 选择器完备 |
| 16 | F8 | `test_t8_1_4_number_input_stepper_buttons_excluded_from_mobile_stretch` | Tier 1 | 移动端按钮规则排除数字输入框内部步进按钮 (`stNumberInput`) | **PASSED** | 排除保护有效 |
| 17 | F8 | `test_t8_1_5_desktop_viewport_grid_columns_preserved` | Tier 1 | 宽屏保留 5 列胶囊栅格 | **PASSED** | 宽屏结构有效 |
| 18 | F8 | `test_t8_2_1_viewport_640px_breakpoint` | Tier 2 | 存在 `@media (max-width: 640px)` 媒体查询断点 | **PASSED** | 断点完备 |
| 19 | F8 | `test_t8_2_2_viewport_641px_breakpoint` | Tier 2 | 存在 768px 或 680px 过渡断点 | **PASSED** | 断点完备 |
| 20 | F8 | `test_t8_2_3_multiple_number_inputs_button_protection` | Tier 2 | `stNumberInput` 容器样式安全 | **PASSED** | 安全 |
| 21 | F8 | `test_t8_2_4_memo_card_safe_breathing_zone` | Tier 2 | 备忘录卡片声明 `min-height` 与 `overflow: visible !important` | **PASSED** | 呼吸区安全 |
| 22 | F8 | `test_t8_2_5_clean_html_purification_contract` | Tier 2 | `_clean_html` 剥离每行首尾空格与空行，消除 4+ 空格代码块泄漏 | **PASSED** | 纯化机制安全 |
| 23 | F8 | `test_t8_3_1_orthogonal_style_consolidation_x_mobile_button_click` | Tier 3 | [正交] 样式合并 × 手机端按钮样式 | **PASSED** | 正交组合健全 |
| 24 | F8 | `test_t8_3_2_orthogonal_mobile_column_selector_x_tab2_tools_dock` | Tier 3 | [正交] 移动端列选择器 × Tab 2 工具坞切换 | **PASSED** | 正交组合健全 |
| 25 | **F9: 近3年滚动发车盲测胜率** | `test_t9_1_1_bimonthly_180d_rolling_dca_backtest` | Tier 1 | `StrategyBridge.calculate_rolling_dca_3y_backtest("bi-monthly", [180, 365])` 返回 `win_rate_180d` | **FAILED** | 缺少该类方法实现 |
| 26 | F9 | `test_t9_1_2_bimonthly_365d_rolling_dca_backtest` | Tier 1 | 同上，验证 `win_rate_365d` 与 `avg_net_return_365d_pct` | **FAILED** | 缺少该类方法实现 |
| 27 | F9 | `test_t9_1_3_quarterly_180d_rolling_dca_backtest` | Tier 1 | `frequency="quarterly"` 季度采样发车，返回周期列表 | **FAILED** | 缺少该类方法实现 |
| 28 | F9 | `test_t9_1_4_quarterly_365d_rolling_dca_backtest` | Tier 1 | 验证 365天净收益与相对沪深300超额 `alpha_vs_csi300_365d` | **FAILED** | 缺少该类方法实现 |
| 29 | F9 | `test_t9_1_5_point_in_time_zero_lookahead` | Tier 1 | 时点时光机零前瞻：切片严格截止于 $T$ | **PASSED** | 时光机回测正常 |
| 30 | F9 | `test_t9_2_1_redemption_fee_180d_zero_rate` | Tier 2 | 持有 180 天赎回费率阶梯免除 | **PASSED** | 费率模型正常 |
| 31 | F9 | `test_t9_2_2_redemption_fee_179d_step_rate` | Tier 2 | 持有 179 天按未满 180 天阶梯全额计提 (>0%) | **PASSED** | 阶梯正常 |
| 32 | F9 | `test_t9_2_3_period_count_lower_bound` | Tier 2 | 滚动发车周期总数 N >= 12 | **FAILED** | 缺少该类方法实现 |
| 33 | F9 | `test_t9_2_4_management_custody_fee_daily_compounding` | Tier 2 | 管理托管费日度计提累乘公理：(1 - 0.0075/250)^250 拖累约 0.747% | **PASSED** | 数学公理验证 |
| 34 | F9 | `test_t9_2_5_excess_return_benchmarked_to_csi300` | Tier 2 | 相对超额严格与同期沪深300收益相减 | **PASSED** | 超额基准对齐 |
| 35 | F9 | `test_t9_3_1_orthogonal_rolling_dca_x_sept2024_inflection_point` | Tier 3 | [正交] 滚动盲测 × 2024年9月暴涨历史拐点 | **PASSED** | 拐点验证正常 |
| 36 | F9 | `test_t9_3_2_orthogonal_rolling_dca_x_table_rendering` | Tier 3 | [正交] 滚动盲测 × 前端字典结构自洽 | **FAILED** | 缺少该类方法实现 |
| 37 | **F10: 摩擦账单动态精算与回测全额扣费** | `test_t10_1_1_pure_bond_dynamic_cagr_and_mdd` | Tier 1 | 纯债权重 CAGR 应动态为 2%~6%，无 16.85 假常数 | **FAILED** | 残留伪常数 16.85 |
| 38 | F10 | `test_t10_1_2_pure_tech_dynamic_cagr_and_mdd` | Tier 1 | 纯科技权重 MDD 动态反映高波动，无 16.85 假常数 | **FAILED** | 残留伪常数 16.85 |
| 39 | F10 | `test_t10_1_3_time_machine_daily_mgmt_fee_accrual` | Tier 1 | 时光机回测输出 `strategy_net_nav` 曲线 | **PASSED** | 回测曲线正常 |
| 40 | F10 | `test_t10_1_4_time_machine_7d_penalty_fee_deduction` | Tier 1 | 未满 7 天到手收益扣除 1.50% 惩罚赎回费 | **PASSED** | 惩罚红线正常 |
| 41 | F10 | `test_t10_1_5_ast_scan_zero_fake_constants_in_friction_bill` | Tier 1 | 正则扫描 `calculate_mutual_fund_friction_bill` 无 16.85 和 -16.76 | **FAILED** | 正则因返回值类型注解未匹配上 |
| 42 | F10 | `test_t10_2_1_holding_days_6_vs_7_penalty_boundary` | Tier 2 | 持有 6天 (1.50%) vs 7天 (正常阶梯) 边界 | **PASSED** | 边界正常 |
| 43 | F10 | `test_t10_2_2_holding_days_29_vs_30_c_share_boundary` | Tier 2 | C类 29天 (扣费) vs 30天 (0费) 边界 | **PASSED** | 边界正常 |
| 44 | F10 | `test_t10_2_3_subscription_scale_tiers` | Tier 2 | 申购费按 0.12% 计提 (1000元对应1.20元) | **PASSED** | 费率正常 |
| 45 | F10 | `test_t10_2_4_conservation_of_fen_and_li_accounting` | Tier 2 | 分厘平账守恒：分项费用之和与总费用残差 < 0.02元 | **PASSED** | 会计平账健全 |
| 46 | F10 | `test_t10_2_5_ultra_low_volatility_continuous_response` | Tier 2 | 超低波纯债摩擦基点 > 0 且平滑连续 | **PASSED** | 响应连续正常 |
| 47 | F10 | `test_t10_3_1_orthogonal_dynamic_friction_bill_x_combat29` | Tier 3 | [正交] 摩擦账单 × 29基预设返回 `raw_29` 与 `reconstructed_6` | **FAILED** | 字典键命名为 `raw_29_weights` |
| 48 | F10 | `test_t10_3_2_orthogonal_full_fee_deduction_x_time_machine_curve` | Tier 3 | [正交] 全额扣费 × 时光机回放曲线 | **PASSED** | 正常 |
| 49 | **F11: OCR 双通道并集与词表扩充** | `test_t11_1_1_stopwords_exclude_a500_index_code` | Tier 1 | "易方达中证A500ETF联接A 15,200.00元" 提取 15200.00，不误判 500 | **PASSED** | 词表匹配正常 |
| 50 | F11 | `test_t11_1_2_stopwords_exclude_holding_days` | Tier 1 | "华泰柏瑞中证红利低波(持有30天) 5,000元" 提取 5000.00，不误判 30 | **PASSED** | 括号提取正常 |
| 51 | F11 | `test_t11_1_3_dual_channel_no_early_return_union_fusion` | Tier 1 | 静态代码扫描：包含 `parse_screenshot_ocr_holdings` 与模糊对齐 | **PASSED** | 框架就绪 |
| 52 | F11 | `test_t11_1_4_complex_multiline_bill_parsing` | Tier 1 | 多行混合账单文本识别 (3只标的提取) | **PASSED** | 正常 |
| 53 | F11 | `test_t11_1_5_invalid_image_payload_graceful_handling` | Tier 1 | 空字节或损坏图片优雅返回 [] 不崩溃 | **PASSED** | 健壮性正常 |
| 54 | F11 | `test_t11_2_1_channel_1_single_item_boundary_continues_channel_2` | Tier 2 | 文本通道识别1条不放弃空间聚类通道 | **PASSED** | 框架调用正常 |
| 55 | F11 | `test_t11_2_2_complex_multi_number_interference` | Tier 2 | "中证500增强C 001234 锁定180天 8888.88元" 提取 8888.88 | **FAILED** | 180 抢先被提取为金额 |
| 56 | F11 | `test_t11_2_3_dual_channel_deduplication_unification` | Tier 2 | 重复输入相同标的去重返回 1 条记录 | **FAILED** | 未去重返回 2 条 |
| 57 | F11 | `test_t11_2_4_comma_separated_number_parsing` | Tier 2 | 解析千分位 "1,234,567.89元" 为浮点数 | **PASSED** | 正则支持正常 |
| 58 | F11 | `test_t11_2_5_micro_amount_preservation` | Tier 2 | 碎片尾仓 0.01元 完整保留不被丢弃 | **PASSED** | 尾仓保护正常 |
| 59 | F11 | `test_t11_3_1_orthogonal_dual_channel_ocr_x_combat29_ledger` | Tier 3 | [正交] OCR 导入 × 29基实盘账本载入 | **PASSED** | 正常 |
| 60 | F11 | `test_t11_3_2_orthogonal_ocr_import_x_auto_routing` | Tier 3 | [正交] OCR 导入标的 (>=10) × 自动路由判定 | **PASSED** | 正常 |
| 61 | **F12: IS_MOBILE_VIEW 激活与响应式** | `test_t12_1_1_mobile_viewport_iphone14_detection` | Tier 1 | 模拟 iPhone UA 或 `view=mobile` 参数 -> `_is_mobile_viewport=True` | **PASSED** | 探测准确 |
| 62 | F12 | `test_t12_1_2_desktop_viewport_detection` | Tier 1 | 模拟 Windows Chrome 或 `view=desktop` -> `_is_mobile_viewport=False` | **PASSED** | 探测准确 |
| 63 | F12 | `test_t12_1_3_tablet_viewport_detection` | Tier 1 | 模拟 iPad UA -> 识别为移动端 | **PASSED** | 探测准确 |
| 64 | F12 | `test_t12_1_4_horizontal_scroll_container_declarations` | Tier 1 | 存在 `overflow-x: auto` 横向平滑滚动声明 | **PASSED** | 样式声明完备 |
| 65 | F12 | `test_t12_1_5_card_container_overflow_visible_declaration` | Tier 1 | 卡片声明 `overflow: visible !important`, `height: auto` | **PASSED** | 样式声明完备 |
| 66 | F12 | `test_t12_2_1_viewport_width_640px_boundary` | Tier 2 | 存在 `(max-width: 640px)` 边界声明 | **PASSED** | 边界正常 |
| 67 | F12 | `test_t12_2_2_viewport_width_641px_boundary` | Tier 2 | 存在非移动端媒体查询断点 | **PASSED** | 边界正常 |
| 68 | F12 | `test_t12_2_3_narrow_screen_320px_layout_resilience` | Tier 2 | 极限窄屏 320px 包含 340px 容器查询单列降级 | **PASSED** | 弹性自适应 |
| 69 | F12 | `test_t12_2_4_inter_component_safety_margin` | Tier 2 | 间距声明安全：`gap: 6px` 或 `gap: 8px` | **PASSED** | 几何间距安全 |
| 70 | F12 | `test_t12_2_5_ultra_wide_2560px_containment` | Tier 2 | 超宽大屏包含 `max-width` 限制 | **PASSED** | 边界受控 |
| 71 | F12 | `test_t12_3_1_orthogonal_mobile_viewport_x_chief_memo_capsules` | Tier 3 | [正交] 移动视口 × 首席备忘录五大胶囊渲染 | **PASSED** | 渲染正常 |
| 72 | F12 | `test_t12_3_2_orthogonal_mobile_viewport_x_tab2_rebalance_table` | Tier 3 | [正交] 移动视口 × Tab 2 调仓清单表格 | **PASSED** | 渲染正常 |
| 73 | **F13: Tab 2 工具坞扁平化与人话卡片** | `test_t13_1_1_tab2_tools_dock_flattening_radio` | Tier 1 | Tab 2 使用 `st.radio` 扁平解耦主流程与工具坞 | **PASSED** | 解耦完备 |
| 74 | F13 | `test_t13_1_2_brinson_attribution_lead_interpretation_card` | Tier 1 | Brinson 归因包含配置效应与选基效应前置人话解读 | **PASSED** | 文案卡片完备 |
| 75 | F13 | `test_t13_1_3_cross_holding_heatmap_lead_interpretation_card` | Tier 1 | 重仓交叉热力图包含抱团风险与重叠度人话解读 | **PASSED** | 文案卡片完备 |
| 76 | F13 | `test_t13_1_4_four_quadrant_scatter_lead_interpretation_card` | Tier 1 | 四象限散点图包含象限含义与轮动方向人话解读 | **PASSED** | 文案卡片完备 |
| 77 | F13 | `test_t13_1_5_lead_card_plain_language_conciseness` | Tier 1 | 解读文案通俗直白，无晦涩数学公式堆叠 | **PASSED** | 风格达标 |
| 78 | F13 | `test_t13_2_1_brinson_zero_alpha_boundary` | Tier 2 | Brinson 超额收益 0.00% 临界点判定 | **PASSED** | 临界正常 |
| 79 | F13 | `test_t13_2_2_brinson_negative_alloc_positive_select_hedged` | Tier 2 | 配置效应负、选基效应正对冲人话区分 | **PASSED** | 区分正常 |
| 80 | F13 | `test_t13_2_3_heatmap_high_overlap_85pct_warning` | Tier 2 | 热力图高重合度预警阈值判定 | **PASSED** | 预警正常 |
| 81 | F13 | `test_t13_2_4_scatter_extreme_overbought_warning` | Tier 2 | 四象限极度过热超买背景与提示 | **PASSED** | 预警正常 |
| 82 | F13 | `test_t13_2_5_tools_dock_switch_idempotency` | Tier 2 | 工具坞主流程与运维模式切换幂等 | **PASSED** | 状态纯洁 |
| 83 | F13 | `test_t13_3_1_orthogonal_tools_dock_flattening_x_tab2_main_decision` | Tier 3 | [正交] 工具坞扁平化 × 默认主流程高度精简 | **PASSED** | 模式正常 |
| 84 | F13 | `test_t13_3_2_orthogonal_lead_cards_x_mobile_responsive` | Tier 3 | [正交] 前置人话卡片 × 移动端响应式排版 | **PASSED** | 排版正常 |
| 85 | **Tier 4: 综合业务负载场景** | `test_tier4_scenario_1_combat29_auto_route_and_memo_coherence` | Tier 4 | 真实 29 基账本载入 -> 首次自动路由 -> 工具坞主流程 -> 备忘录胶囊知行合一 | **PASSED** | 端到端全通 |
| 86 | Tier 4 | `test_tier4_scenario_4_historical_3y_rolling_dca_full_fees` | Tier 4 | 历史拐点时光机 + 动态摩擦账单精算 + 滚动发车盲测契约 | **FAILED** | 摩擦账单含 16.85 假常数 |
| 87 | Tier 4 | `test_tier4_scenario_5_mobile_ocr_dual_channel_fusion` | Tier 4 | 移动端复杂截图 OCR 导入·双通道并集与指数/持有期数字防污染 | **FAILED** | 180 误污染为持仓金额 |
| 88 | Tier 4 | `test_tier4_scenario_6_tab2_tools_dock_and_lead_cards_e2e` | Tier 4 | Tab 2 工具坞扁平化与多维图表前置人话解读端到端 | **PASSED** | 端到端全通 |

---

## 五、Worker 实施避坑指南与脆性断言分析 (Pitfalls & Brittle Assumptions)

为了协助后续 Worker 代理在一次性修复中达成 **88/88 (100% Passed)**，特梳理以下 4 个关键细节：

### 1. `test_t10_1_5` 正则匹配陷阱
- **陷阱**: 测试用例第 512 行使用了 `pattern = r"def calculate_mutual_fund_friction_bill\([^)]*\):.*?(?=\n    def |\Z)"`。
- **问题**: 原函数声明中包含了返回类型注解 `-> Dict[str, Any]:`，导致 `\):` 无法匹配到代码块！
- **避坑对策**: Worker 在同步维护非只读测试文件时，将正则表达式优化为 `pattern = r"def calculate_mutual_fund_friction_bill\([^:]*\):.*?(?=\n    def |\Z)"`（匹配括号到冒号之间的任意注解），或函数签名调整，使正则顺利命中函数体并核验 16.85/16.76 已彻底清除。

### 2. `test_t10_3_1` 字典键名匹配
- **陷阱**: `preset = StrategyBridge.get_combat_29_vs_reconstructed_6_preset()` 返回字典中，原键名为 `raw_29_weights` 与 `reconstructed_6_weights`。测试用例断言：
  ```python
  assert "raw_29" in preset
  assert "reconstructed_6" in preset
  assert preset["raw_29"]["fund_count"] == 29
  assert preset["reconstructed_6"]["fund_count"] == 6
  ```
- **避坑对策**: 在 `get_combat_29_vs_reconstructed_6_preset` 返回字典中直接补齐：
  ```python
  "raw_29": {"fund_count": 29, "weights": raw_29_weights},
  "reconstructed_6": {"fund_count": 6, "weights": reconstructed_6_weights},
  ```
  既不破坏已有消费者的 `raw_29_weights`，又完全满足测试断言。

### 3. Feature 9: `calculate_rolling_dca_3y_backtest` 契约规范
- **必须支持的入参**:
  - `frequency`: 可取 `"bi-monthly"`（双月发车）或 `"quarterly"`（季度发车）
  - `holding_horizons`: 默认 `[180, 365]`
- **必须返回的键值**:
  - `"win_rate_180d"`: float (0.0~1.0)
  - `"win_rate_365d"`: float (0.0~1.0)
  - `"avg_net_return_365d_pct"`: float
  - `"total_periods"`: int (必须 $\ge 12$)
  - `"alpha_vs_csi300_365d"`: float
  - `"periods"` 或 `"rolling_records"`: List[Dict]（每期的发车与到期明细）
- **扣费模型公理**:
  - 前端申购费：A类 0.12%，C类 0.0%
  - 日度公募托管与管理费：$(0.0075 / 250.0)$ 每日计提
  - C类日度销售服务费：$(0.0040 / 250.0)$ 每日计提
  - 180天持有期赎回费：A类按阶梯 0.00%（或 $\le 0.15\%$），365天按 0.00% 免除。

### 4. Feature 11: 持有天数与金额提取顺序绝对不可颠倒
- 任何情况下，必须**先解析并剥离持有期/锁定天数字符串**（`锁定180天`、`持有30天`），再执行剩余文本的金额正则捕获。
- 严禁在持有期数字剥离前调用 `re.findall(r'\d+', remain_line)`，否则首个数字必然误抓持有天数。

---

## 六、限制与假设 (Caveats)

1. **只读审计契约**: 本次调查严格遵守 Explorer 角色只读约束，所有代码切片与修改建议均记录于本报告及 `.agents/teamwork/explorer_m2_3/` 目录中，未触碰任何生产源码与裁判文件。
2. **只读裁判文件绝对保护**: `judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py` 四个只读裁判文件在整个生命周期内禁止修改。
3. **时钟漂移豁免**: 针对此前部分单测中硬编码 `2026-10-28` 相对当前执行日（`2026-11-15`）产生的天数漂移，本次 `test_g19_m2_routing_and_rolling_dca.py` 已全部使用动态计算，不存在时钟漂移阻碍。

---

## 七、结论 (Conclusion)

1. **当前测试基础坚实**: 88 项测试用例中已有 **74 项测试稳定通过 (84.1% 基础通过率)**，涵盖了 Feature 7（首次自动路由）、Feature 8（样式合并）、Feature 12（移动端响应式布局）、Feature 13（Tab 2 工具坞扁平化与人话卡片）以及场景 1 和场景 6 的全量验收。
2. **失败点高度集中且路径清晰**: 14 项失败用例百分之百归因于：
   - Feature 9 待实现的方法 `calculate_rolling_dca_3y_backtest`（影响 6 项）；
   - Feature 10 待清除的 16.85 假常数及 preset 键名补齐（影响 4 项）；
   - Feature 11 待修复的锁定天数前置剥离与去重（影响 2 项）；
   - Tier 4 复合场景（影响 2 项）。
3. **修复后可确定性实现 100% 绿灯**: 按照本报告提供的精确代码方案，Worker 代理实施后预计可一次性使全部 88 项测试 100% 绿灯全通。

---

## 八、独立验证方法 (Verification Method)

Worker 代理完成修改后，请使用以下命令进行独立核验：

```powershell
# 1. 运行 Milestone 2 核心 88 项端到端测试套件 (必须 88 passed)
py -3 -m pytest tests/test_g19_m2_routing_and_rolling_dca.py -q

# 2. 针对 Feature 11 专项核验 (必须 12 passed)
py -3 -m pytest tests/test_g19_m2_routing_and_rolling_dca.py -k "TestFeature11" -v

# 3. 针对 Feature 9 滚动发车胜率专项核验 (必须 12 passed)
py -3 -m pytest tests/test_g19_m2_routing_and_rolling_dca.py -k "TestFeature9" -v

# 4. 针对 Feature 10 摩擦账单动态精算专项核验 (必须 12 passed)
py -3 -m pytest tests/test_g19_m2_routing_and_rolling_dca.py -k "TestFeature10" -v

# 5. 针对 Tier 4 综合业务场景全量核验 (必须 4 passed)
py -3 -m pytest tests/test_g19_m2_routing_and_rolling_dca.py -k "TestTier4" -v
```
**失效条件 (Invalidation Conditions)**:
- 若 `test_t11_2_2_complex_multi_number_interference` 依旧报错 `got 180.0`，说明持有天数解析未前置或未就地从 `remain_line` 剥离。
- 若 `test_t9_1_1` 抛出 `AssertionError: StrategyBridge.calculate_rolling_dca_3y_backtest must be callable`，说明类方法尚未在 `strategy_bridge.py` 正确暴露。
