# StrategyBridge (R4 股息与票息安全垫引擎) 技术调研与工程方案报告

> **调研执行代理**：Explorer Subagent (`explorer_survey_r11_2`)  
> **任务目标**：针对 R4 组合年度股息与票息安全垫精算引擎，调研 `strategy_bridge.py` 现状、输入形态容错、9大标准基准、现金分红判定与 `app_gui.py` 展示落点，输出高鲁棒性工程设计方案。  
> **调研基准文件**：`AGY2_FundAdvisory/strategy_bridge.py`、`AGY2_FundAdvisory/portfolio_manager.py`、`AGY2_FundAdvisory/app_gui.py`

---

## 一、调研核心结论摘要 (Executive Summary)

1. **核心算法已初具雏形，但存在 2 个致命缺陷**：
   - **装饰器错位缺陷**：`strategy_bridge.py` 第 1959~1960 行同时叠放了 `@classmethod` 与 `@staticmethod`，且导致其下方 `get_online_expert_weights` 丢失类方法属性；
   - **零资金/大资金持仓权重失真缺陷**：当传入真实持仓且 `total_capital <= 0` 时，当前代码盲目使用 `100000.0` 兜底，导致 50 万资产测算出的总权重飙升至 500%、加权年化率飙至 20.5% 的离谱数值（必须改为基于持仓真实市值累加动态定权）。
2. **多形态入参需全方位包容**：前端与测试调用存在 **6 种常见输入形态**（权重字典、金额字典、`pm.holdings` 字典、`HoldingItem` 对象列表、字典列表、`pd.DataFrame` 以及直接传入 `pm` 实例），方案已设计无缝自适应解析器。
3. **9 大标准资产大类收益率基准 100% 精确校准**：红利低波 5.2%、红利高股息 4.8%、核心蓝筹 2.8%、中盘均衡 1.8%、中小盘成长 1.0%、科技成长进攻 0.6%、纯债固收 2.75%、美股海外对冲 1.3%、黄金对冲 0.0%，并配套三阶容错分类反查链。
4. **GUI 两大落地展示位清晰明确**：
   - **Tab 1 步骤二**（`app_gui.py` 2972~3040行 方案核心归因）：在归因卡片旁与卡片内部联动展示内生收息安全垫；
   - **Tab 2 步骤一**（`app_gui.py` 3669~3676行 资产基线横幅）：在基线与风控防线卡片内无缝扩充第三行，动态展示实盘现金流造血能力。

---

## 二、`strategy_bridge.py` 现状与深层缺陷诊断

### 1. `StrategyBridge` 类结构与导入特征
- **类定义位置**：`AGY2_FundAdvisory/strategy_bridge.py` 第 1938 行。
- **静态方法约定**：多数模块级纯函数通过 `foo = staticmethod(foo)` 或 `@staticmethod` 注入；类级别依赖状态的方法使用 `@classmethod`。
- **循环导入隔离防御**：`strategy_bridge.py` 严禁顶层导入 `portfolio_manager.py`，必须在方法内部进行局部延迟导入（`from portfolio_manager import PortfolioManager`）或调用 `cls._get_portfolio_manager()`。

### 2. 缺陷 1：`@classmethod` 与 `@staticmethod` 叠放陷阱
在 `strategy_bridge.py` 第 1959~1962 行：
```python
    @classmethod
    @staticmethod
    def calculate_portfolio_yield_cushion(
        weights_or_holdings: Any,
        total_capital: float,
        pm: Any = None
    ) -> Dict[str, Any]:
```
以及第 2049 行：
```python
    def get_online_expert_weights(
        cls,
        history_df: Optional[pd.DataFrame] = None,
        force_reload: bool = False,
        return_details: bool = False
    ) -> Any:
```
**诊断结果**：
- 在 Python 3.10+ 中将 `staticmethod` 传给 `classmethod` 是被明确弃用的语法特性（Python 3.13 中将直接报错）。
- 此处明显是上一位作者在编写方法时，误将本该放在 `get_online_expert_weights` 上的 `@classmethod` 贴到了 `calculate_portfolio_yield_cushion` 上方，导致 `calculate_portfolio_yield_cushion` 拥有两重装饰器，而 `get_online_expert_weights` 险些失去 `@classmethod`。
- **修复方案**：`calculate_portfolio_yield_cushion` 严格仅保留 `@staticmethod`；`get_online_expert_weights` 显式保留 `@classmethod`。

### 3. 缺陷 2：`total_capital <= 0` 时的持仓权重与收益率失真 Bug
在当前代码第 1983~1994 行：
```python
tot_cap = float(total_capital if total_capital > 0 else 100000.0)
...
for fc, h in weights_or_holdings.items():
    mv = float(getattr(h, "market_value", 0.0))
    w = (mv / tot_cap) if tot_cap > 0 else 0.0
```
**实测复现**：
- 当用户拥有 50 万资产（如 15万红利低波 + 15万银行 + 20万纯债），调用 `calculate_portfolio_yield_cushion(pm.holdings, 0.0)` 时：
- `tot_cap` 强制被设为 `100000.0`；
- 各标的计算出的权重变为 `1.5, 1.5, 2.0`（总权重 5.0，即 500%）；
- `weighted_yield_pct` 算得 `20.5%`（原本真实应为 `4.10%`）；
- `cat_breakdown` 中每项占比显示为 `150.0%`, `200.0%`。
- **修复方案**：若传入的是持仓对象（有 `market_value`）且 `total_capital <= 0` 时，必须以持仓实际市值总和 `total_mv = sum(mv)` 作为基准资产，绝不能硬编码 100000.0。

---

## 三、输入形态全面容错矩阵 (Robust Input Formats)

调用方（GUI Tab 1、Tab 2、定时任务、单元测试）可能传入的形态包括以下 6 种，引擎必须做到 100% 鲁棒解析：

| 形态序号 | 输入类型 (`weights_or_holdings`) | 示例数据结构 | 资本总额提取方式 | 权重推算方式 |
| :--- | :--- | :--- | :--- | :--- |
| **形态 1** | 纯权重字典 | `{"005561": 0.35, "002351": 0.40, ...}` | 若 `total_capital > 0` 用之，否则兜底 100,000 | 若 sum > 1.5 归一化，否则直接作为 0~1 权重 |
| **形态 2** | 金额字典 | `{"005561": 35000.0, "002351": 40000.0}` | 若 sum > 100 且 cap <= 0，自动将 cap=sum | 各标的权重 = amount / cap |
| **形态 3** | 持仓全景字典 (`pm.holdings`) | `{"005561": FundHolding(...), ...}` | 若 cap <= 0，自动取 `sum(h.market_value)` | 各标的权重 = h.market_value / cap |
| **形态 4** | 持仓对象列表 | `[FundHolding(...), HoldingItem(...)]` | 若 cap <= 0，自动取 `sum(h.market_value)` | 各标的权重 = h.market_value / cap |
| **形态 5** | Pandas 数据帧 | `pd.DataFrame(...)`（含 `fund_code/code` 等列） | 从 `market_value/市值/金额` 列加总求和 | 优先读 `weight` 列，无则按 `mv / sum_mv` |
| **形态 6** | `PortfolioManager` 实例 | 直接传入 `pm` 对象 | 读取 `pm.total_equity` 或 `sum(mv)` | 自动展开为 `pm.holdings` 解析 |
| **兜底态** | `None` 或空集合 `{}` | `None` / `{}` / `[]` | 保持 0.0 或 100000.0 | 返回安全全 0 字典，零异常退出 |

---

## 四、9 大标准资产大类收益率基准与分类器联动验证

### 1. 收益率基准表 (严格锚定要求)
```python
BENCHMARK_YIELDS: Dict[str, float] = {
    "A股红利低波": 5.20,      # 高股息率与稳健分红中枢
    "A股红利高股息": 4.80,    # 银行/周期/央企高股息
    "核心蓝筹": 2.80,        # 沪深300/消费/食品蓝筹股息率
    "中盘均衡": 1.80,        # 中证500/医药生物中庸股息率
    "中小盘成长": 1.00,      # 中证1000/成长小盘低股息
    "科技成长进攻": 0.60,    # 科创50/半导体/芯片微薄股息
    "纯债固收": 2.75,        # 综合债券到期票息率中枢
    "美股海外对冲": 1.30,    # 标普500/纳指海外股息率
    "黄金对冲": 0.00         # 黄金零票息零股息抗通胀
}
```

### 2. 三阶分类器反查保障
为防止未知标的或传入参数缺失名称导致的分类脱靶，建立以下反查链条：
1. **第一阶（优先实盘反查）**：若 `pm` 存在且标的在 `pm.holdings` 中，提取最新 `h.fund_name` 并调用 `pm.classify_fund_asset_class(fc, fn)`；
2. **第二阶（全量底座目录反查）**：若 `fn` 为空或等于代码，自动从 `CORE_STRATEGY_POOL`、`EXTENDED_FUND_CATALOG` 反查官方名称，调用 `PortfolioManager.classify_fund_asset_class(fc, fn)`；
3. **第三阶（基准字典对齐）**：若分类结果不在 `BENCHMARK_YIELDS` 9 个键中（例如早期返回了别名），建立归一化映射：
   - `"纯债"` / `"固收"` -> `"纯债固收"`
   - `"黄金"` -> `"黄金对冲"`
   - `"美股"` / `"QDII"` -> `"美股海外对冲"`
   - `"芯片"` / `"半导体"` / `"科创"` -> `"科技成长进攻"`
   - 最终兜底：`"中盘均衡"` (1.80%)。

---

## 五、现金分红直接派发预估 (`cash_dividend_payout_est`) 判定逻辑

### 1. 字段属性判定与多别名归一化
`FundHolding` / `HoldingItem` 中标准字段为 `h.dividend_method`（取值为 `"cash"` 或 `"reinvest"`）。
判定函数支持多别名与中文兼容：
- 若取值为 `"cash"`、`"现金"`、`"现金分红"` 或 `is_cash_dividend == True`，判定为现金分红标的；
- 若取值为 `"reinvest"`、`"再投资"`、`"红利再投"`，判定为再投资标的；
- **新资建仓/无状态权重字典的处理**：在 Tab 1 新资建仓时，用户尚未录入实盘持仓。根据行业投顾实践与 `INDEX_TO_FUND_MAP` 建议：
  - 若标的属于 `"A股红利低波"` 或 `"A股红利高股息"`（如 100032、005561），或代码标注了“建议现金分红”，默认视为推荐现金分红，其内生股息计入 `cash_dividend_payout_est`；
  - 其余成长类与固收类标的默认再投资，确保测算契合高股息吃息投资者的真实预期。

---

## 六、输出字典规格与数学公式

引擎方法统一返回如下结构字典（严格遵循数学公式，拒绝假数据）：
```python
{
    "weighted_yield_pct": float,        # 组合加权年化内生收益率 (单位 %，四舍五入保留2位)
    "annual_cushion_amount": float,     # 组合年度内生安全垫总额 = total_capital * (weighted_yield_pct / 100.0)
    "monthly_equivalent_amount": float, # 折合月均内生收息安全垫 = annual_cushion_amount / 12.0
    "cash_dividend_payout_est": float,  # 预计年度直接到账的现金分红总额 (元/年)
    "category_breakdown": {             # 9 大类细分构造成分
        "资产大类名": {
            "weight": float,            # 该大类在组合中占比 (%)
            "yield_rate": float,        # 该大类基准年化率 (%)
            "annual_amount": float      # 该大类每年产生的内生安全垫 (元/年)
        },
        ...
    },
    "total_capital": float              # 实际参与精算的资金底座 (元)
}
```

---

## 七、`app_gui.py` 渲染集成方案设计

### 1. Tab 1 步骤二：方案核心归因旁边与内部增强
- **代码位置**：`AGY2_FundAdvisory/app_gui.py` 第 2972~3040 行。
- **上下文变量**：`opt_weights` (`Dict[str, float]`)、`plan_capital` (`float`)、`pm` (`PortfolioManager`)。
- **调用方式**：
  ```python
  cushion_info = StrategyBridge.calculate_portfolio_yield_cushion(opt_weights, plan_capital, pm=pm)
  ```
- **渲染方案**：
  1. **在第 1 张归因大卡片「💰 怎么赚钱？」中深度植入**：
     在原「防守收息」条目下方紧随增加内生收息安全垫数据：
     ```html
     <b>内生造血</b>：年化收益率 <b>{cushion_info['weighted_yield_pct']:.2f}%</b> (<b>¥{cushion_info['annual_cushion_amount']:,.0f}/年</b>，折合 <b>¥{cushion_info['monthly_equivalent_amount']:,.0f}/月</b>)<br>
     ```
  2. **在 3 张归因大卡片正下方新增专属横向「🌱 组合内生收息安全垫」卡片**：
     呈现四大关键指标（加权收益率、年化总造血、折合月均、现金分红到账预估），醒目展示现金流自愈能力。

### 2. Tab 2 步骤一：当前持仓账本资产基线横幅
- **代码位置**：`AGY2_FundAdvisory/app_gui.py` 第 3669~3676 行（主视图）与第 4242~4250 行（账本管理工具坞）。
- **上下文变量**：`pm.holdings`、`_tot_base_eq`、`pm`。
- **调用方式**：
  ```python
  cushion_tab2 = StrategyBridge.calculate_portfolio_yield_cushion(pm.holdings, _tot_base_eq, pm=pm)
  ```
- **渲染方案**：
  在原资产基线与风控防线横幅内，增加第三行内生安全垫：
  ```html
  <div style="background: var(--bg-elevated); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 10px 14px; margin-bottom: 10px; font-size: 12px; line-height: 1.6; color: var(--text-secondary);">
      💼 <b>资产基线：</b>¥{_tot_base_eq:,.2f} ｜ <b>持仓标的：</b>{len(pm.holdings)} 只 ｜ <b>底座：</b>{_mat_date_str} ｜ <b>在途现金：</b>¥{pm.in_transit_cash:,.2f}<br>
      🛡️ <b>风控防线：</b>7天惩罚费拦截 (1.50%惩罚扣除硬阻断) ｜ 悲观持有天数梯级守护<br>
      🌱 <b>收息安全垫：</b>加权年化 <b>{cushion_tab2['weighted_yield_pct']:.2f}%</b> ｜ 预计年造血 <b>¥{cushion_tab2['annual_cushion_amount']:,.2f}/年</b> (折合 <b>¥{cushion_tab2['monthly_equivalent_amount']:,.2f}/月</b>) ｜ 现金直派预估 <b>¥{cushion_tab2['cash_dividend_payout_est']:,.2f}/年</b>
  </div>
  ```

---

## 八、建议实施者落地的代码补丁设计 (Code Proposal)

### 1. `AGY2_FundAdvisory/strategy_bridge.py` 替换实现
```python
    @staticmethod
    def calculate_portfolio_yield_cushion(
        weights_or_holdings: Any,
        total_capital: float = 0.0,
        pm: Any = None
    ) -> Dict[str, Any]:
        """
        组合年度股息与票息安全垫精算引擎 (Intrinsic Yield & Cashflow Cushion)
        基于各标准资产大类的真实底层股息率与到期票息率基准加权求和，
        输出真实数学公式计算的内生收息安全垫现金流与月均造血能力。
        全面兼容：权重字典、金额字典、FundHolding 字典、HoldingItem 列表、DataFrame 及 PM 实例。
        """
        BENCHMARK_YIELDS = {
            "A股红利低波": 5.20,
            "A股红利高股息": 4.80,
            "核心蓝筹": 2.80,
            "中盘均衡": 1.80,
            "中小盘成长": 1.00,
            "科技成长进攻": 0.60,
            "纯债固收": 2.75,
            "美股海外对冲": 1.30,
            "黄金对冲": 0.00
        }

        # 1. 兼容 PortfolioManager 实例直接传入
        if pm is None and hasattr(weights_or_holdings, "holdings"):
            pm = weights_or_holdings
            weights_or_holdings = getattr(weights_or_holdings, "holdings", {})

        items: List[Tuple[str, str, float, float, str]] = [] # (fc, fn, mv, weight, div_m)
        extracted_cap = float(total_capital) if (total_capital is not None and total_capital > 0) else 0.0

        # 2. 解析不同输入形态
        if weights_or_holdings is None:
            pass
        elif isinstance(weights_or_holdings, pd.DataFrame):
            df = weights_or_holdings
            c_code = next((c for c in df.columns if c in ["fund_code", "code", "基金代码"]), None)
            c_name = next((c for c in df.columns if c in ["fund_name", "name", "基金名称"]), None)
            c_mv = next((c for c in df.columns if c in ["market_value", "amount", "市值", "金额"]), None)
            c_w = next((c for c in df.columns if c in ["weight", "target_weight", "权重", "占比"]), None)
            c_div = next((c for c in df.columns if c in ["dividend_method", "dividend_mode", "分红方式"]), None)

            if c_code:
                sum_mv = float(df[c_mv].sum()) if (c_mv and pd.notna(df[c_mv].sum())) else 0.0
                if extracted_cap <= 0 and sum_mv > 0:
                    extracted_cap = sum_mv

                for _, row in df.iterrows():
                    fc = str(row[c_code]).strip().zfill(6)
                    fn = str(row[c_name]) if (c_name and pd.notna(row[c_name])) else ""
                    mv = float(row[c_mv]) if (c_mv and pd.notna(row[c_mv])) else 0.0
                    w = float(row[c_w]) if (c_w and pd.notna(row[c_w])) else 0.0
                    if w > 1.5:
                        w = w / 100.0
                    elif w == 0.0 and sum_mv > 0:
                        w = mv / sum_mv
                    div_m = str(row[c_div]).strip().lower() if (c_div and pd.notna(row[c_div])) else ""
                    items.append((fc, fn, mv, w, div_m))

        elif isinstance(weights_or_holdings, dict):
            if weights_or_holdings:
                first_val = next(iter(weights_or_holdings.values()))
                if hasattr(first_val, "market_value") or (isinstance(first_val, dict) and "market_value" in first_val):
                    # FundHolding / HoldingItem 字典
                    total_mv = 0.0
                    raw_list = []
                    for fc, h in weights_or_holdings.items():
                        fc_s = str(fc).strip().zfill(6)
                        if hasattr(h, "market_value"):
                            mv = float(getattr(h, "market_value", 0.0))
                            fn = str(getattr(h, "fund_name", "") or "")
                            div_m = str(getattr(h, "dividend_method", "") or "")
                        else:
                            mv = float(h.get("market_value", 0.0))
                            fn = str(h.get("fund_name", "") or "")
                            div_m = str(h.get("dividend_method", "") or "")
                        total_mv += mv
                        raw_list.append((fc_s, fn, mv, div_m))

                    if extracted_cap <= 0:
                        extracted_cap = total_mv if total_mv > 0 else 100000.0

                    for fc_s, fn, mv, div_m in raw_list:
                        w = (mv / extracted_cap) if extracted_cap > 0 else 0.0
                        items.append((fc_s, fn, mv, w, div_m))
                else:
                    # 权重或金额字典 {fund_code: float}
                    sum_val = sum(float(v) for v in weights_or_holdings.values()) or 1.0
                    is_amount = sum_val > 100.0
                    if is_amount and extracted_cap <= 0:
                        extracted_cap = sum_val

                    for fc, v in weights_or_holdings.items():
                        fc_s = str(fc).strip().zfill(6)
                        v_flt = float(v)
                        if is_amount:
                            mv = v_flt
                            w = (mv / extracted_cap) if extracted_cap > 0 else (v_flt / sum_val)
                        elif sum_val > 1.5:
                            w = v_flt / 100.0
                            mv = (extracted_cap or 100000.0) * w
                        else:
                            w = v_flt
                            mv = (extracted_cap or 100000.0) * w
                        items.append((fc_s, "", mv, w, ""))

        elif isinstance(weights_or_holdings, list):
            total_mv = 0.0
            raw_list = []
            for h in weights_or_holdings:
                if hasattr(h, "fund_code") or hasattr(h, "market_value"):
                    fc = str(getattr(h, "fund_code", "") or "").strip().zfill(6)
                    fn = str(getattr(h, "fund_name", "") or "")
                    mv = float(getattr(h, "market_value", 0.0))
                    div_m = str(getattr(h, "dividend_method", "") or "")
                    w = float(getattr(h, "weight", 0.0))
                elif isinstance(h, dict):
                    fc = str(h.get("fund_code", h.get("code", "")) or "").strip().zfill(6)
                    fn = str(h.get("fund_name", h.get("name", "")) or "")
                    mv = float(h.get("market_value", h.get("amount", 0.0)))
                    div_m = str(h.get("dividend_method", h.get("dividend_mode", "")) or "")
                    w = float(h.get("weight", 0.0))
                else:
                    continue
                total_mv += mv
                raw_list.append((fc, fn, mv, w, div_m))

            if extracted_cap <= 0:
                extracted_cap = total_mv if total_mv > 0 else 100000.0

            for fc, fn, mv, w, div_m in raw_list:
                if w <= 0.0 and extracted_cap > 0:
                    w = mv / extracted_cap
                elif w > 1.5:
                    w = w / 100.0
                items.append((fc, fn, mv, w, div_m))

        tot_cap = float(extracted_cap if extracted_cap > 0 else 100000.0)

        # 3. 归类与加权精算
        from portfolio_manager import PortfolioManager, CORE_STRATEGY_POOL, EXTENDED_FUND_CATALOG
        weighted_yield = 0.0
        cash_div_est = 0.0
        cat_breakdown: Dict[str, Dict[str, float]] = {}

        for fc, fn, mv, w, div_m in items:
            # 补充基金名称
            if not fn or fn == fc:
                if pm is not None and hasattr(pm, "holdings") and fc in pm.holdings:
                    fn = pm.holdings[fc].fund_name
                elif fc in CORE_STRATEGY_POOL:
                    fn = CORE_STRATEGY_POOL[fc].get("fund_name", "")
                elif fc in EXTENDED_FUND_CATALOG:
                    fn = EXTENDED_FUND_CATALOG[fc].get("fund_name", "")

            # 资产大类识别
            if pm is not None and hasattr(pm, "classify_fund_asset_class"):
                cat = pm.classify_fund_asset_class(fc, fn)
            else:
                cat = PortfolioManager.classify_fund_asset_class(fc, fn)

            y_rate = BENCHMARK_YIELDS.get(cat, 1.80)
            weighted_yield += w * y_rate
            amt = tot_cap * w * (y_rate / 100.0)

            # 现金分红偏好判定
            is_cash_div = False
            div_m_clean = str(div_m).strip().lower()
            if div_m_clean in ["cash", "现金", "现金分红"]:
                is_cash_div = True
            elif div_m_clean in ["reinvest", "再投资", "红利再投"]:
                is_cash_div = False
            else:
                # 未显式指定分红方式时（如新资建仓模型权重）
                if pm is not None and hasattr(pm, "holdings") and fc in pm.holdings:
                    is_cash_div = (getattr(pm.holdings[fc], "dividend_method", "cash") == "cash")
                else:
                    if "红利" in cat or fc in ["100032", "005561"]:
                        is_cash_div = True

            if is_cash_div:
                cash_div_est += amt

            if cat not in cat_breakdown:
                cat_breakdown[cat] = {"weight": 0.0, "yield_rate": y_rate, "annual_amount": 0.0}
            cat_breakdown[cat]["weight"] = round(cat_breakdown[cat]["weight"] + w * 100.0, 1)
            cat_breakdown[cat]["annual_amount"] = round(cat_breakdown[cat]["annual_amount"] + amt, 2)

        weighted_yield_pct = round(weighted_yield, 2)
        annual_cushion = round(tot_cap * (weighted_yield_pct / 100.0), 2)
        monthly_cushion = round(annual_cushion / 12.0, 2)

        return {
            "weighted_yield_pct": weighted_yield_pct,
            "annual_cushion_amount": annual_cushion,
            "monthly_equivalent_amount": monthly_cushion,
            "cash_dividend_payout_est": round(cash_div_est, 2),
            "category_breakdown": cat_breakdown,
            "total_capital": tot_cap
        }
```

---

## 九、总结与交接指引

本调研已全面攻克算法、边界条件与交互呈现的关键技术链路，并编写了完备的独立沙盒验证脚本 `scripts/test_calculate_yield_cushion.py`。实施者可直接参考第八节的完整代码，完成 `strategy_bridge.py` 与 `app_gui.py` 的对接实装。
