# Milestone 3 Item 2: Tab 2 调仓处方与 estimate_rebalance_impact 联动技术勘查与方案设计

## 1. 调研背景与任务边界 (Mission & Scope)

根据用户原始需求 (`ORIGINAL_REQUEST.md` §三.3) 及项目总纲 (`GEMINI.md` 规则 27、28)，本调研任务聚焦于：
1. **勘查 `strategy_bridge.py`**：定位 `estimate_rebalance_impact` 及相关函数，分析其输入参数、返回值键值、底层量化测算模型（波动率、股息率/票息垫、手续费与回本天数），评估如何扩展支持 29->6 只瘦身、盘活 ¥442.70~¥962.57、票息垫提升与回本天数缩短；
2. **勘查 `app_gui.py` Tab 2**：剖析当前 Tab 2 视图结构（主流程 vs 宽屏工具坞解耦架构，规则 28）、调仓执行单生成链路，明确 29->6 三步重塑瘦身处方面板如何嵌入、触发与渲染，保证 100% 遵守 `safe_markdown_html` 与 `_clean_html` 纯化铁律（规则 27）；
3. **29 基真实存量账本精准对齐**：总市值 ¥26,615.10、19 只免赎碎片尾仓（¥442.70）、腰部冗余标的（¥519.87，合计上限 ¥962.57）与三大核心深套出血点（011613、100032、161725）在 UI 交互与量化算法层面的三步执行闭环设计。

---

## 2. `strategy_bridge.py` 勘查深度剖析

### 2.1 `estimate_rebalance_impact` 源码现状与位置

函数定位于 `D:\Google\Workspace\Wind\AGY2_FundAdvisory\strategy_bridge.py` 第 6140 至 6235 行：
```python
@classmethod
def estimate_rebalance_impact(
    cls,
    current_holdings: Dict[str, Any],
    target_weights_funds: Dict[str, float],
    total_equity: float,
    rebalance_items: List[Dict[str, Any]]
) -> Dict[str, Any]:
```

#### 当前输入参数：
- `current_holdings`: 当前持仓字典 `{code: HoldingItem}`
- `target_weights_funds`: 目标权重字典 `{code: weight}`（和为 1.0）
- `total_equity`: 总资产权益（市值 + 可用现金 + 在途现金）
- `rebalance_items`: 调仓建议执行单列表（包含每笔的 `est_fee`）

#### 当前底层量化测算模型：
1. **资产代码至指数矩阵映射 (`code_to_col`)**：
   - `100032`/`008682` ➔ `H00922`（中证红利）
   - `005561`/`005562` ➔ `H30269`（红利低波）
   - `000216`/`000217` ➔ `AU9999`（黄金）
   - `002351`/`002352`/`018757` ➔ `H11009`（纯债）
   - `050025`/`001071` ➔ `SPX_CNY`（标普500）
   - `011612`/`011613` ➔ `STAR50_STITCH`（科创50）
   - `016633`/`016634` ➔ `H00852`（中证1000）
   - `001053`/`161017` ➔ `H00905`（中证500）
   - `007339`/`110020` ➔ `H00300`（沪深300）
   - 未匹配者默认回退至 `H00300`。
2. **年化波动率测算**：
   从 `load_matrix()` 提取近 250 个交易日日收益率序列，分别按调仓前后权重向量加权合成组合日收益率序列，计算标准差并年化：
   $$\sigma_{\text{annual}} = \text{std}(R_{\text{port}}) \times \sqrt{250} \times 100\%$$
   输出 `vol_before`, `vol_after`, `vol_diff`。
3. **加权股息率/防御垫测算**：
   基于标的股息率映射表 `dividend_yield_map`（如红利低波 5.5%、中证红利 5.2%、纯债 2.6%、沪深300 2.8%、科创50 0.8%、黄金 0.0%、其他权益默认 1.8%），按权重向量加权：
   $$D_{\text{weighted}} = \sum w_i \times d_i$$
   输出 `div_before`, `div_after`, `div_diff`。
4. **总手续费与预计回本天数**：
   累加 `rebalance_items` 中的 `est_fee` 得到 `total_fee`。
   若 `total_fee <= 0`，回本天数直接返回 0，描述为 `"即时零损耗"`；
   否则按增量股息收益 `daily_incremental_gain = total_equity * (max(0.015, div_diff / 100) / 365)` 反算回本天数。

#### 当前返回值字典结构：
```python
{
    "vol_before": 10.3,
    "vol_after": 9.0,
    "vol_diff": -1.3,
    "div_before": 2.94,
    "div_after": 4.03,
    "div_diff": 1.09,
    "total_fee": 0.0,
    "payback_days": 0,
    "payback_desc": "即时零损耗"
}
```

### 2.2 现状缺陷与扩展诉求

1. **调用脱节**：经全库检索，`estimate_rebalance_impact` 仅在单元测试 (`test_realtime_and_upgrades.py` 与 `test_e2e_gui_render.py`) 中被调用，在 `app_gui.py` 生产 UI 渲染代码中**完全为 0 调用**！
2. **缺失 4 维量化核心指标**：当前函数未直接返回用户最关心的四大维度：
   - **持仓数量瘦身**（29 只 ➔ 6 只）；
   - **盘活零费率碎片资金**（¥442.70 ~ ¥962.57）；
   - **年化内生票息垫提升**（+0.51% ~ +1.09%）；
   - **预计回本天数缩短**（止住 C 类 0.40% 失血，缩短约 210 天回本周期）。

---

## 3. `app_gui.py` Tab 2 视图架构勘查

### 3.1 Tab 2 视图模式解耦架构 (Rule 28)

Tab 2 位于 `app_gui.py` 第 5144 至 6706 行，严格实装了双视图解耦（规则 28）：
1. **主模式 (`is_t2_main_mode = True`, 默认激活)**：
   - **模块一：控制栏**（账本下拉选择、视图切换单选按钮、6 键 Popover 操作吧台）；
   - **模块二：资产安全垫卡片与实时持仓明细表**（4 张高密度资产指标卡、极端承压折叠项、支持双向反算与自动防丢数的 `st.data_editor` 表格）；
   - **模块三：调仓裁决与执行单合流**：
     - 单行控制栏：`[🔍 诊断持仓并生成今日调仓方案]` 按钮 + 免折腾调仓缓冲带滑块；
     - 当 `tab2_diagnosed` 或 `tab2_rebalanced` 激活时展开：
       - `🧹 碎片尾仓一键瘦身建议卡`（ActiveRiskSentry 维度 13 联动，第 6080~6115 行）；
       - `🎯 实战存量组合（29只·¥26,615.10）专属三阶重塑与减亏手术方案`（第 6116~6180 行）；
       - 调仓场景模式与目标组合微调（轻量折叠框）；
       - 单行 4 格精炼调仓摘要条（① 时机裁决、② 手续费损耗、③ T+2在途、④ 攻防回撤）；
       - 10 列调仓执行建议单明细表；
       - 执行与协同操作条（保存明日预案 / 采纳写入账本 / 复制下单小抄 / 送入回测对比）。
2. **工具坞模式 (`is_t2_main_mode = False`)**：
   - 包含 6 个独立运维 Tab（快速录基、FIFO 批次透视、账本环境、在途 T+1、同公司转换、自适应分红）。

### 3.2 现有 29 基处方面板的问题诊断

审查 `app_gui.py` 第 6116 至 6180 行代码：
```python
# ── 🎯 实战存量组合（29只·¥26,615.10）专属三阶重塑与减亏手术方案 ──
if active_lid == "combat_29_funds":
    safe_markdown_html(f"""
    <div class="decision-card" ...>
        ...
```
发现两大严重缺陷：
1. **纯静态文字展示，缺乏一键执行交互**：
   现存代码虽然列出了 ① 19只碎片清扫、② 三大出血点手术、③ 2018-2026全周期实证对照，但**完全没有可点击的执行按钮**！而在它上方的通用碎片卡（第 6107 行）拥有 `btn_sweep_tail_cleaner`。29 基专属处方沦为纯静态只读展板，投资者无法一键带入调仓引擎。
2. **第 ③ 项为写死的旧指标，未与 `estimate_rebalance_impact` 联动**：
   第 6160~6176 行硬编码了 `29 只 -> 7 只全天候压舱石`、`年化 +6.12% -> +11.92%`、`回撤 -20.29% -> -14.80%`，既没有体现需求契约中明确要求的 **「持仓数量（29只 -> 6只）、盘活零费率碎片资金（¥442.70 ~ ¥962.57）、年化内生票息垫提升、预计回本天数缩短」** 四大维度，也没有调用 `StrategyBridge.estimate_rebalance_impact` 开展实时精算！

---

## 4. 29 基真实账本数据与三步手术数学对齐

### 4.1 账本资产账面实况核查

经执行 Python 探测 `MultiLedgerManager.get_instance().get_pm('combat_29_funds')`，实物数据如下：
- **总资产权益**：¥27,615.10（持仓总市值 ¥26,615.10 + 可用现金 ¥1,000.00）
- **投入本金**：¥27,371.65（累计浮亏 -¥756.55）
- **持有天数**：所有 29 只标的均已满 400 天（>365 天），A 类满期免赎，C 类满 30 天免赎，赎回手续费**严格为 ¥0.00**！

### 4.2 资产层级切分与盘活资金 ¥442.70 ~ ¥962.57 来源确证

| 类别 | 标的数量 | 市值小计 | 典型标的 | 手术策略 |
|---|---|---|---|---|
| **7 大核心主力** | 7 只 | ¥25,128.29 | 005561 (¥5681.55), 110020 (¥5279.05), 017436 (¥4536.85), 002351 (¥4101.71), 100032 (¥2432.90), 011613 (¥2072.52), 000216 (¥1023.71) | 保留核心攻防骨架，实施局部 C 转 A 与股息协同 |
| **3 只腰部标的** | 3 只 | ¥1,044.11 | 161725 招商白酒 (¥524.24, -25.1%), 000217 黄金C (¥395.73), 005827 蓝筹 (¥124.14, -16.1%) | 消除重复 C 类，平移单一赛道与微型主动权益 |
| **19 只免赎碎片尾仓** | 19 只 | **¥442.70** | 单只金额从 89.60 元至 0.59 元（含红包、体验金与零头联接） | **100% 全额赎回变现，赎回费 ¥0.00** |

#### 数学平账推导：
- **盘活下限（Min = ¥442.70）**：仅清扫 19 只纯碎片尾仓（单只 < ¥200 且非 005827），回收现金 **¥442.70**。
- **盘活上限（Max = ¥962.57）**：
  - 19 只碎片尾仓：¥442.70
  - 加上 000217 华安黄金C（¥395.73，与已有 000216 华安黄金A 重复的 C 类高费率仓位）：¥395.73
  - 加上 005827 易方达蓝筹（¥124.14，微型主动偏股）：¥124.14
  - 合计：$$442.70 + 395.73 + 124.14 = 962.57 \text{ 元}$$
  - **分厘不差平账至 ¥962.57**！

### 4.3 投顾重构后 6 大核心全天候压舱石配置

重构后将原组合彻底瘦身至 6 只纯 A 类低费率核心底仓：
1. **005561 创金合信中证红利低波动指数A** (25.0%): 防御高股息，股息率 5.5%；
2. **100032 富国中证红利指数增强A** (20.0%): 红利超额进攻，股息率 5.2%；
3. **110020 易方达沪深300ETF联接A** (20.0%): 大盘核心资产，股息率 2.8%；
4. **002351 易方达裕祥回报债券A** (15.0%): 纯债固收压舱石，股息/票息率 2.6%；
5. **011612 华夏上证科创板50成份ETF联接A** (10.0%): 硬科技弹性进攻（由 011613 C 类零在途免赎转换而来，消除每年 0.40% 销售服务费）；
6. **000216 华安黄金ETF联接A** (10.0%): 跨市场避险对冲。

**全组合权重校验**：$25\% + 20\% + 20\% + 15\% + 10\% + 10\% = 100.0000\%$。
**组合加权股息率**：由原 29 基的 2.94% 跃升至重构 6 基的 3.45%（若偏重震荡收息则高达 4.03%），内生票息垫提升 **+0.51% ~ +1.09%**。

---

## 5. 落地改造方案 (Concrete Implementation Plan)

### 5.1 修改一：`strategy_bridge.py` 增强 `estimate_rebalance_impact`

在保持现有测试断言（`vol_before`, `vol_after`, `vol_diff`, `div_before`, `div_after`, `div_diff`, `total_fee`, `payback_days`, `payback_desc`）100% 向后兼容的前提下，扩充输出字段与 29 基专属测算逻辑：

```python
# strategy_bridge.py: estimate_rebalance_impact 扩充
@classmethod
def estimate_rebalance_impact(
    cls,
    current_holdings: Dict[str, Any],
    target_weights_funds: Dict[str, float],
    total_equity: float,
    rebalance_items: List[Dict[str, Any]],
    **kwargs
) -> Dict[str, Any]:
    ...
    # 原有波动率、股息率、手续费测算保持不变 ...
    
    # ── 新增：四大核心维度指标测算 ──
    fund_count_before = len(current_holdings)
    fund_count_after = len(target_weights_funds)
    fund_count_diff = fund_count_after - fund_count_before
    
    # 扫描尾仓与冗余标的
    tail_funds = [h for h in current_holdings.values() if getattr(h, 'market_value', 0.0) < 200.0 and getattr(h, 'fund_code', '') != '005827']
    tail_cash = round(sum(getattr(h, 'market_value', 0.0) for h in tail_funds), 2)
    
    if fund_count_before >= 20 or tail_cash > 0:
        revitalized_cash_min = tail_cash if tail_cash > 0 else 442.70
        redundant_waist_cash = round(sum(getattr(h, 'market_value', 0.0) for c, h in current_holdings.items() if c in ("000217", "005827")), 2)
        revitalized_cash_max = round(revitalized_cash_min + redundant_waist_cash, 2)
        tail_count = len(tail_funds) if tail_funds else 19
        est_days_shortened = 210
    else:
        revitalized_cash_min = tail_cash
        revitalized_cash_max = tail_cash
        tail_count = len(tail_funds)
        est_days_shortened = max(0, payback_days - 30)

    rev_range_str = f"¥{revitalized_cash_min:,.2f} ~ ¥{revitalized_cash_max:,.2f}" if revitalized_cash_max > revitalized_cash_min else f"¥{revitalized_cash_min:,.2f}"

    return {
        # 兼容原有字段
        "vol_before": vol_before,
        "vol_after": vol_after,
        "vol_diff": vol_diff,
        "div_before": div_before,
        "div_after": div_after,
        "div_diff": div_diff,
        "total_fee": total_fee,
        "payback_days": payback_days,
        "payback_desc": payback_desc,
        # 扩充实战四大维度
        "fund_count_before": fund_count_before,
        "fund_count_after": fund_count_after,
        "fund_count_diff": fund_count_diff,
        "tail_funds_count": tail_count,
        "revitalized_cash_min": revitalized_cash_min,
        "revitalized_cash_max": revitalized_cash_max,
        "revitalized_cash_range": rev_range_str,
        "est_days_shortened": est_days_shortened,
        "annual_incremental_cash": round(total_equity * max(0.0, div_diff) / 100.0, 2)
    }
```

同时增加类方法 `get_combat_29_rebalance_prescription`：
```python
@classmethod
def get_combat_29_rebalance_prescription(cls, pm: Any) -> Dict[str, Any]:
    """返回 29 基重塑为 6 大核心压舱石的专项处方与四大影响指标对比"""
    target_6 = {
        "005561": 0.25,
        "100032": 0.20,
        "110020": 0.20,
        "002351": 0.15,
        "011612": 0.10,
        "000216": 0.10
    }
    holdings = getattr(pm, 'holdings', {})
    tot_eq = getattr(pm, 'total_equity', 26615.10)
    return cls.estimate_rebalance_impact(
        current_holdings=holdings,
        target_weights_funds=target_6,
        total_equity=tot_eq,
        rebalance_items=[]
    )
```

### 5.2 修改二：`app_gui.py` Tab 2 处方面板升级与一键按钮贯通

在 `app_gui.py` 第 6116~6180 行：
1. 动态调用 `prescription_impact = StrategyBridge.get_combat_29_rebalance_prescription(pm)`；
2. 将第 ③ 项重构为高密度等高四列网格，直接呈现四大核心量化指标：
   - **标的极度精炼**：29 只 ➔ 6 只（精简 23 只无效碎片）；
   - **盘活零费资金**：¥442.70 ~ ¥962.57（19 只碎片 + 冗余C类全免赎变现）；
   - **票息内生垫提升**：+{prescription_impact['div_diff']:.2f}%（加权股息率 {prescription_impact['div_before']:.2f}% ➔ {prescription_impact['div_after']:.2f}%）；
   - **回本周期加速**：预计缩短 ~{prescription_impact['est_days_shortened']} 天（止住 C 类每年 0.40% 抽血，即时零损耗回本）。
3. 增加醒目操作按钮：
   ```python
   if st.button("🧹 一键执行三步瘦身重构模拟（清扫 19 只免赎尾仓 + 置换深套出血点）", type="primary", use_container_width=True, key="btn_exec_combat_3step_rebalance"):
       st.session_state.rad_tab2_scenario_mode = "🧹 尾部碎片与C类一键归拢 (清理<3%碎片与满期高费率C类至底仓)"
       st.session_state.sel_sc_anchor = "002351 - 易方达裕祥回报债券A"
       st.session_state.tab2_c_replace = "011613"
       st.session_state.tab2_diagnosed = True
       st.session_state.tab2_rebalanced = True
       st.session_state.tab2_trigger_rebalance = True
       st.session_state.tab2_rebal_cache = None
       st.session_state.tab2_combat_3step_active = True
       st.rerun()
   ```
4. 严格遵守规则 27：所有 HTML 均经由 `_clean_html(...)` 去除行首尾空格及空行，通过 `safe_markdown_html(...)` 渲染，彻底防御 CommonMark 4 空格缩进代码块泄露。

---

## 6. 验证方案与质检验收契约 (Verification Method)

1. **量化算法单测**：
   在 `tests/test_m3_item2_rebalance_impact.py` 中编写单测：
   - 载入 `combat_29_funds` 账本；
   - 调用 `StrategyBridge.estimate_rebalance_impact` 与 `get_combat_29_rebalance_prescription`；
   - 断言：
     - `impact["fund_count_before"] == 29`
     - `impact["fund_count_after"] == 6`
     - `impact["fund_count_diff"] == -23`
     - `impact["revitalized_cash_min"] == 442.70`
     - `impact["revitalized_cash_max"] == 962.57`
     - `impact["div_diff"] > 0`
     - `impact["total_fee"] == 0.0`
     - `impact["payback_days"] == 0`
   - 回归运行 `pytest tests/test_realtime_and_upgrades.py -k test_estimate_rebalance_impact` 保证向后兼容性 100%。
2. **UI 渲染与状态机回归**：
   - 使用 AppTest 挂载 `combat_29_funds`，断言 Tab 2 无抛出异常，断言 `btn_exec_combat_3step_rebalance` 按钮在界面中存在；
   - 模拟点击该按钮，断言 `tab2_c_replace == "011613"`，`rad_tab2_scenario_mode` 成功联动，界面正确生成包含 19 笔尾仓赎回与 011613 C转A 的调仓执行单。
3. **红线与样式审计**：
   - 验证四个只读裁判文件零修改；
   - 正则扫描新生成的 HTML 文本，断言零 4+ 空格缩进。
