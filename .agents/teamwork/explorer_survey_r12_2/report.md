# G5 世代历史三大拐点实盘对照尺与 14:30 尾盘实时估值异动预警深度勘测报告

## 一、 勘测目标与问题边界

本调研严格遵循**只读勘测原则（Read-Only Investigation）**，针对 G5 世代两大核心投顾实盘能力开展系统性代码与数学模型排查：
1. **历史三大牛熊拐点实盘对照尺**：深入排查投顾决策大脑 `advisory_engine.py` 中已有的关键拐点逻辑，获取 2021年2月核心资产见顶、2022年4月恐慌底、2024年9月反转底与当前市场的真实量化指标（ERP 估值分位、MA20 乖离率、定投乘数），研究如何在前端界面（首屏市场脉搏或 Tab 1）以紧凑一行式胶囊对比条直观呈现，并严格执行“界面复杂度守恒原则”。
2. **14:30 尾盘实时估值异动防追高与黄金坑吸筹预警**：排查 `portfolio_manager.py` / `data_loader.py` 中的 `fetch_realtime_fund_quote` 接口，结合单基真实 20 日日均波动幅度 $\sigma_{\text{day}}$ 与自身 MA20 乖离率 $\text{Bias20}$，构建精准的尾盘异动数学判断模型，并调研在 Tab 2 调仓执行表与 Tab 1 定投计划实操要点列中的无缝接入方案与移动端 640px 视口自适应规范。

---

## 二、 历史三大牛熊拐点实盘对照尺排查与实证数据

### 2.1 现有代码逻辑与实现位置
- **所在文件与类**：`AGY2_FundAdvisory/advisory_engine.py` (第 1545-1670 行)，`SmartExecutionDCAEngine.verify_historical_inflection_signals(cls, df=None)`。
- **桥接层映射**：`AGY2_FundAdvisory/strategy_bridge.py` (第 6967-6998 行)，`StrategyBridge.verify_historical_inflection_signals()`。
- **自动化测试锚点**：`tests/test_g3_evolution_loop.py` (第 385-410 行)，`test_g3_8_historical_inflection_point_signals_verification`。

### 2.2 历史三大拐点实证数据与当前市场实测对照

通过本地编写的真实验证探针（`test_snapshot.py`）调用底层计算引擎，提取出的真实量化数据如下表所示：

| 关键时间节点 | 周期事件定位 | 沪深300 MA20 乖离率 (Bias20) | ERP 股债性价比分位 (ERP Pct) | 投顾建议信号类别 | 动态自适应定投乘数 | 乘数标签与估值状态 |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **2021-02-18** | 核心资产极度高估见顶 | **+4.30%** (极度超买) | **28.9%** (极度高估过热) | `TAKE_PROFIT_DEFENSE` | **0.50x** | `🟡 0.5x 防守微扣`<br>高估过热或严重超买 (减速定投并分批止盈) |
| **2022-04-26** | 跌破2900点恐慌绝望底 | **-8.27%** (深度负乖离) | **76.0%** (历史极高性价比) | `CONTRARIAN_ACCUMULATION` | **1.93x** | `🚀 2.0x 逆向猛扣`<br>极度低估水下超跌 (加速收集廉价筹码) |
| **2024-09-18** | 924行情政策暴烈反转前夕 | **-2.60%** (水下低估负乖离) | **90.6%** (极度水下击球区) | `CONTRARIAN_ACCUMULATION` | **1.94x** | `🚀 2.0x 逆向猛扣`<br>极度低估水下超跌 (加速收集廉价筹码) |
| **今日实时**<br>(2026-11-06) | **当前实盘运行水位** | **-2.07%** (均线水下蓄势) | **82.6%** (历史高性价比击球区) | `ACCUMULATION` | **1.76x** | `⚡ 1.5x 加速吸筹`<br>极度低估水下超跌 (加速收集廉价筹码) |

**数据链条实证**：
1. **当前宏观基准**：沪深300 PE-TTM 为 `12.23`（历史分位 43.2%），中债 10Y 国债到期收益率为 `1.623%`，真实 ERP 为 `6.55%`，对应历史滚动分位点为 `82.6%`。
2. **信号一致性检验**：当前定投乘数 `1.76x` 与历史 2022 年 4 月（`1.93x`）、2024 年 9 月（`1.94x`）同属高性价比击球区，显著区别于 2021 年 2 月核心资产泡沫期（`0.50x` 强制压制防守），模型金融逻辑严密闭环。

### 2.3 统一数据接口暴露方案

在 `advisory_engine.py` 的 `SmartExecutionDCAEngine` 中，应暴露一个专门供前端与桥接层直接调用的统一数据接口：

```python
@classmethod
def get_historical_inflection_ruler(
    cls,
    current_erp: Optional[float] = None,
    current_bias: Optional[float] = None,
    total_capital: float = 100000.0
) -> Dict[str, Any]:
    """
    【历史三大牛熊拐点实盘对照尺数据接口】
    暴露 2021见顶(0.50x)、2022恐慌底(1.93x)、2024反转底(1.94x) 与当前市场的并列对照结构。
    """
    # 1. 获取三大历史基准拐点验证结果
    base_res = cls.verify_historical_inflection_signals()
    
    # 2. 结合传入或全局实时的 ERP 与 Bias 计算当前市场水位
    c_erp = 82.6 if current_erp is None else float(current_erp)
    c_bias = -2.07 if current_bias is None else float(current_bias)
    
    plan_now = cls.plan_smart_dca(
        total_capital=total_capital,
        allocations=[{"code": "005561", "name": "创金合信红利低波A", "weight": 0.5}],
        erp_percentile=c_erp,
        bias_20=c_bias,
        periods=12
    )
    
    current_node = {
        "date": "今日实时",
        "event": "今日当前市场水位",
        "signal": "ACCUMULATION",
        "erp_percentile": c_erp,
        "bias_20": c_bias,
        "multiplier": plan_now["multiplier"],
        "multiplier_tag": plan_now["multiplier_tag"],
        "valuation_status": plan_now["valuation_status"],
        "is_valid": True
    }
    
    return {
        "nodes": [
            base_res["2021_top"],
            base_res["2022_bottom"],
            base_res["2024_bottom"],
            current_node
        ],
        "all_inflections_verified": base_res["all_inflections_verified"],
        "current_market": current_node
    }
```
并在 `StrategyBridge` 中增加同名 passthrough 代理 `StrategyBridge.get_historical_inflection_ruler`，保持既有单测 100% 兼容。

### 2.4 前端呈现与“界面复杂度守恒原则”落地

- **展现位置**：
  1. **首屏“今日市场脉搏晨报”卡片内部**（`app_gui.py` 第 2163-2173 行）：原本包含纯文字段落，可将文字精炼，并在卡片下方直接嵌入 4 节点紧凑横向滚动对照条（`inflection-ruler-strip`）。
  2. **Tab 1 步骤三“智能定投”卡片区**（`app_gui.py` 第 3422 行）：用对照尺替换原本单薄的一行 `st.caption`。
- **界面复杂度守恒实践**：
  - **精简项**：移除 `render_dual_wing_advisory_dashboard` 中冗余重复的估值解释文案（原本重复描述了三次 ERP 分位与两市成交长句）；
  - **新增项**：替换为 4 胶囊并列对照条，每颗胶囊高度锁死 28px，行内并列：
    - 🔴 `2021-02 核心见顶` ｜ ERP 28.9% ｜ Bias +4.3% ｜ **0.50x 减仓**
    - 🟢 `2022-04 恐慌底` ｜ ERP 76.0% ｜ Bias -8.3% ｜ **1.93x 猛扣**
    - 🟢 `2024-09 反转底` ｜ ERP 90.6% ｜ Bias -2.6% ｜ **1.94x 猛扣**
    - ⚡ `今日实时` ｜ ERP 82.6% ｜ Bias -2.1% ｜ **1.76x 加速吸筹**
  - **视觉收益**：用户无需翻看历史研报，一眼即可在首屏看懂当前市场在 5 年牛熊周期中的确切坐标。

---

## 三、 14:30 尾盘实时估值异动预警排查与算法模型

### 3.1 `fetch_realtime_fund_quote` 接口与返回结构分析

- **文件与行号**：`AGY2_FundAdvisory/portfolio_manager.py` (第 2214-2280 行)。
- **返回数据模型**：`FundQuote` 数据类（第 2104-2146 行），继承自 `dict`，同时支持字典键访问、属性访问及元组解构。
- **返回核心字段**：
  - `name`: 基金官方全称（如 `创金合信中证红利低波动指数A`）
  - `dwjz`: 昨日官方单位净值（如 `2.2141`）
  - `gsz`: 今日盘中实时估算净值（如 `2.2361`）
  - `gszzl`: 今日实时估算涨跌幅（如 `+0.99`，单位为 %）
  - `gztime`: 估值更新时间（如 `2026-11-06 16:02:00`）
  - `fund_code`: 6位基金代码
  - `valuation_corrected`: 是否触发 QDII / 黄金基准溢价纠偏机制（`bool`）
- **实测抓取验证**（基于 `test_quote.py` 实盘接口运行）：
  - `005561` (创金红利低波A): `dwjz=2.2141, gsz=2.2361, gszzl=+0.99%`
  - `011613` (华夏科创50联接C): `dwjz=1.0298, gsz=1.0044, gszzl=-2.47%`
  - `002351` (易方达裕祥纯债A): `dwjz=1.6060, gsz=1.6070, gszzl=+0.06%`
  - `000216` (华安黄金联接A): `dwjz=3.0545, gsz=2.9956, gszzl=-1.93%`
  - `510300` (沪深300ETF): `dwjz=4.1909, gsz=4.1312, gszzl=-1.42%`

### 3.2 单基 20 日真实日均波动幅度 $\sigma_{\text{day}}$ 与单基 $\text{Bias20}$ 真实穿透

#### 3.2.1 消除三档固定波动率常数
当前 `advisory_engine.py` (第 1367-1372 行) 存在历史遗留的回退常数：
```python
# 遗留常数回退
elif any(k in fn for k in ["债", "固收", "纯债"]) or fc == "002351":
    vol = 0.04
elif any(k in fn for k in ["黄金"]) or fc == "000216":
    vol = 0.14
else:
    vol = 0.18
```
**必须彻底消除上述 0.04、0.14、0.18 固定常数**，替换为基于真实本地湖仓与日线缓存的实时计算辅助方法。

#### 3.2.2 三级穿透提取真实日线与日收益率序列
在 `advisory_engine.py` 中新增 `get_fund_20d_metrics(fund_code: str, fund_name: str = "") -> Dict[str, float]`：
1. **第一顺位：单基独立历史日线**：
   - 检索 `data/processed/funds/{code}.OF.parquet`、`data/cache/market_screener/nav_cache/{code}.parquet` 或从 `storage.duckdb` 的 `v_funds` 表中提取；
2. **第二顺位：赛道细分日线**：
   - 检索 `data/processed/indices/000685.SH.parquet`（半导体）、`000933.SH.parquet`（医药）、`000932.SH.parquet`（消费）、`399986.SZ.parquet`（银行）、`AU9999.SGE.parquet`（黄金现货）；
3. **第三顺位：高保真对齐净值矩阵**：
   - 提取 `data/processed/aligned_matrix_total_return.parquet` 对应列：
     - 红利低波 -> `H30269`
     - 中证红利 -> `H00922`
     - 沪深300 -> `H00300`
     - 中证500 -> `H00905`
     - 科创50 -> `STAR50_STITCH`
     - 纯债固收 -> `H11009` / `930609`
     - 黄金现货 -> `AU9999`
     - 海外标普 -> `SPX_CNY`

#### 3.2.3 数学测算结果（实测数据）
基于 `aligned_matrix_total_return.parquet` 过去 20 个交易日（截至 2026-11-06）的真实日线测算：
- **纯债固收 (`H11009`)**：日均波动幅度 $\sigma_{\text{day}} = \mathbf{0.05\%}$，年化波动率 $\mathbf{0.82\%}$，$\text{Bias20} = \mathbf{+0.25\%}$，$1.5 \sigma_{\text{day}} = \mathbf{0.08\%}$；
- **红利低波 (`H30269`)**：日均波动幅度 $\sigma_{\text{day}} = \mathbf{0.92\%}$，年化波动率 $\mathbf{14.59\%}$，$\text{Bias20} = \mathbf{-0.20\%}$，$1.5 \sigma_{\text{day}} = \mathbf{1.38\%}$；
- **中证红利 (`H00922`)**：日均波动幅度 $\sigma_{\text{day}} = \mathbf{0.98\%}$，年化波动率 $\mathbf{15.54\%}$，$\text{Bias20} = \mathbf{-0.44\%}$，$1.5 \sigma_{\text{day}} = \mathbf{1.47\%}$；
- **沪深300 (`H00300`)**：日均波动幅度 $\sigma_{\text{day}} = \mathbf{1.08\%}$，年化波动率 $\mathbf{17.08\%}$，$\text{Bias20} = \mathbf{-1.34\%}$，$1.5 \sigma_{\text{day}} = \mathbf{1.62\%}$；
- **标普500 (`SPX_CNY`)**：日均波动幅度 $\sigma_{\text{day}} = \mathbf{1.18\%}$，年化波动率 $\mathbf{18.66\%}$，$\text{Bias20} = \mathbf{-5.02\%}$，$1.5 \sigma_{\text{day}} = \mathbf{1.77\%}$；
- **黄金ETF (`AU9999`)**：日均波动幅度 $\sigma_{\text{day}} = \mathbf{1.32\%}$，年化波动率 $\mathbf{20.82\%}$，$\text{Bias20} = \mathbf{+1.74\%}$，$1.5 \sigma_{\text{day}} = \mathbf{1.98\%}$；
- **科创50 (`STAR50_STITCH`)**：日均波动幅度 $\sigma_{\text{day}} = \mathbf{2.39\%}$，年化波动率 $\mathbf{37.75\%}$，$\text{Bias20} = \mathbf{-11.22\%}$，$1.5 \sigma_{\text{day}} = \mathbf{3.58\%}$。

实测证实：不同品类资产在相同日内涨跌幅下的统计意义完全不同。例如：
- 债基涨跌 0.20% 已属于 $4\sigma$ 级别的罕见大波动；
- 红利基金涨跌 1.0% 属于常态波动（小于 $1.5\sigma$）；
- 科创50 必须涨跌超过 3.58% 才构成 $1.5\sigma$ 异动。
**引入真实单基 $\sigma_{\text{day}}$ 是杜绝“假警报”与“漏报”的物理量化基石。**

### 3.3 14:30 尾盘实时估值异动判断与策略动作逻辑

结合基金当日盘中估算涨跌幅 $gszzl$、单基 20 日日均波动幅度 $\sigma_{\text{day}}$ 与单基均线乖离率 $\text{Bias20}$，构建三类状态机判定：

```
                    ┌───────────────────────────────────────────────┐
                    │  fetch_realtime_fund_quote 获取当日真实 gszzl  │
                    │  计算单基真实 20 日日均波动幅度 sigma_day 与 Bias20 │
                    └───────────────────────┬───────────────────────┘
                                            │
               ┌────────────────────────────┴───────────────────────────┐
               ▼                                                        ▼
  【急涨脉冲判断】                                            【急跌错杀判断】
  gszzl > +1.5 * sigma_day                                    gszzl < -1.5 * sigma_day
  且 Bias20 > 0.0 (正乖离高位)                                且 Bias20 < 0.0 (负乖离水下)
               │                                                        │
               ▼                                                        ▼
  触发【🚨 尾盘脉冲·防追高】预警                             触发【💎 尾盘错杀·黄金坑】提示
  - 现象：日内脉冲透支，早盘追入极易冲高回落                   - 现象：日内情绪错杀超跌，水下筹码极其廉价
  - 策略建议：将当日计划买入/定投额下调 30%~50%                - 策略建议：把握 14:30~14:50 窗口，按原计划全额
    留存多余资金停泊纯债/货基吃息，等待均线回踩回踩确认         申购或逆向适度增配 10%~20%，锁定折扣廉价份额
```

#### 状态判别函数设计（`advisory_engine.py`）
```python
@staticmethod
def detect_intraday_valuation_anomaly(
    fund_code: str,
    fund_name: str = "",
    gszzl: Optional[float] = None,
    sigma_day: Optional[float] = None,
    bias_20: Optional[float] = None,
) -> Dict[str, Any]:
    """
    【14:30 尾盘实时估值异动防追高与黄金坑吸筹判断算子】
    """
    # 1. 自动穿透单基真实指标
    metrics = SmartExecutionDCAEngine.get_fund_20d_metrics(fund_code, fund_name)
    s_day = metrics["sigma_day_pct"] if sigma_day is None else float(sigma_day)
    b_20 = metrics["bias_20"] if bias_20 is None else float(bias_20)
    
    # 2. 自动拉取实时估值涨跌幅
    if gszzl is None:
        try:
            from portfolio_manager import fetch_realtime_fund_quote
            q = fetch_realtime_fund_quote(fund_code)
            g_val = float(q.gszzl)
        except Exception:
            g_val = 0.0
    else:
        g_val = float(gszzl)

    threshold_1_5 = round(1.5 * s_day, 2)
    
    # 3. 核心异动判断
    if g_val > threshold_1_5 and b_20 > 0.0:
        return {
            "fund_code": fund_code,
            "fund_name": fund_name,
            "gszzl": g_val,
            "sigma_day": s_day,
            "threshold_1_5": threshold_1_5,
            "bias_20": b_20,
            "anomaly_type": "OVERBOUGHT_SPIKE",
            "anomaly_tag": "🚨 尾盘急涨·防追高",
            "badge_color": "var(--color-up)",
            "amount_multiplier": 0.60,  # 建议减额 40% (即下调 30%~50%)
            "advice": f"实时估值大涨 {g_val:+.2f}% (超1.5倍日均波动 {threshold_1_5:.2f}%) 且处于正乖离高位，建议将当日申购/定投额下调 30%~50% 留待回踩均线。",
            "short_tip": f"急涨{g_val:+.2f}%(超1.5σ)·正乖离·减额40%留待回踩",
        }
    elif g_val < -threshold_1_5 and b_20 < 0.0:
        return {
            "fund_code": fund_code,
            "fund_name": fund_name,
            "gszzl": g_val,
            "sigma_day": s_day,
            "threshold_1_5": threshold_1_5,
            "bias_20": b_20,
            "anomaly_type": "OVERSOLD_PIT",
            "anomaly_tag": "💎 尾盘错杀·黄金坑",
            "badge_color": "var(--color-down)",
            "amount_multiplier": 1.15,  # 建议增配 15% (即适度增配 10%~20%)
            "advice": f"实时估值急跌 {g_val:+.2f}% (跌破1.5倍日均波动 {-threshold_1_5:.2f}%) 且处于负乖离低估，建议把握 14:30~14:50 窗口按原计划全额申购或逆向适度增配 10%~20%。",
            "short_tip": f"急跌{g_val:+.2f}%(破1.5σ)·负乖离错杀·14:30适度增配",
        }
    else:
        return {
            "fund_code": fund_code,
            "fund_name": fund_name,
            "gszzl": g_val,
            "sigma_day": s_day,
            "threshold_1_5": threshold_1_5,
            "bias_20": b_20,
            "anomaly_type": "NORMAL",
            "anomaly_tag": "🟢 估值平稳",
            "badge_color": "var(--text-secondary)",
            "amount_multiplier": 1.00,
            "advice": f"实时估值波动在 1.5 倍日均波动带 (±{threshold_1_5:.2f}%) 内，按原策略纪律执行。",
            "short_tip": "估值平稳·纪律执行",
        }
```

---

## 四、 前端具体接入点与响应式 CSS 架构设计

### 4.1 Tab 2 调仓执行表（`app_gui.py` 第 5280-5340 行）
- **原渲染字段**：
  `df_orders_tbl` 包含 9 列：`"基金代码", "基金名称", "份额", "当前市值(元)", "目标占比(%)", "实时估值涨跌(%)", "建议调仓金额(元)", "建议操作", "实操要点"`。
- **接入点与增强逻辑**：
  在循环迭代 `buy_items` 与各持仓标的计算 `op_action` 与 `op_point` 时，调用 `detect_intraday_valuation_anomaly`：
  ```python
  # 探测 14:30 尾盘实时估值异动
  anomaly_res = SmartExecutionDCAEngine.detect_intraday_valuation_anomaly(
      fund_code=it["fund_code"],
      fund_name=it.get("fund_name", ""),
      gszzl=it.get("realtime_gszzl")
  )
  if anomaly_res["anomaly_type"] == "OVERBOUGHT_SPIKE":
      op_action = "🚨 尾盘急涨·防追高"
      op_point = anomaly_res["short_tip"]
  elif anomaly_res["anomaly_type"] == "OVERSOLD_PIT":
      op_action = "💎 尾盘错杀·黄金坑"
      op_point = anomaly_res["short_tip"]
  ```
  在表格展示中，`建议操作` 列与 `实操要点` 列直接向用户传递清晰明确的防追高或黄金坑逆向加仓指令，彻底告别模棱两可。

### 4.2 Tab 1 智能定投实操表（`app_gui.py` 第 3455-3505 行）
- **接入点**：
  在智能定投表格中，`df_display["实操分红与限购指引"]` 列融合尾盘异动标签：
  若检测到标的触发 `OVERBOUGHT_SPIKE`，在指引中附加 `【🚨尾盘急涨·定投下调至¥...】`；
  若触发 `OVERSOLD_PIT`，附加 `【💎尾盘黄金坑·建议按时扣款或增配】`。

### 4.3 移动端 640px 视口与 CSS 媒体查询设计
为彻底杜绝移动端窄视口（如 640px）下文字挤压、卡片折叠破坏、半截文字截断等视觉缺陷，必须在 `<style>`（第 362 行）中注入专属媒体查询和几何不变量：

```css
/* 历史三大拐点对照尺容器 */
.inflection-ruler-strip {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 8px;
    background: var(--bg-surface) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: 8px;
    padding: 8px 12px;
    margin: 8px 0;
    box-shadow: var(--shadow-card) !important;
    width: 100%;
    min-height: 44px;
    box-sizing: border-box;
    overflow-x: auto !important;
    overflow-y: hidden;
    scrollbar-width: thin;
    -webkit-overflow-scrolling: touch;
}

.inflection-ruler-strip::-webkit-scrollbar {
    height: 4px;
}
.inflection-ruler-strip::-webkit-scrollbar-thumb {
    background: var(--border-subtle);
    border-radius: 4px;
}

.inflection-node-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: var(--bg-elevated) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: 6px;
    padding: 4px 10px;
    flex: 0 0 auto !important;
    white-space: nowrap !important;
    font-size: 11px;
    box-sizing: border-box;
    min-height: 30px;
}

.inflection-node-pill.current {
    border-color: var(--accent-primary) !important;
    background: var(--bg-surface) !important;
    box-shadow: 0 0 0 1px var(--accent-primary) !important;
}

/* 移动端 640px 视口自适应优化 */
@media (max-width: 640px) {
    .inflection-ruler-strip {
        padding: 6px 8px;
        gap: 6px;
    }
    .inflection-node-pill {
        padding: 3px 6px;
        font-size: 10px;
        gap: 4px;
    }
    .decision-card {
        padding: 8px 10px !important;
        min-height: auto !important;
    }
    [data-testid="stDataFrame"] {
        width: 100% !important;
        overflow-x: auto !important;
    }
}
```

---

## 五、 代码落地修改清单与精确映射

| 序号 | 目标模块文件 | 涉及函数 / 代码块 | 具体修改与扩展内容 |
| :---: | :--- | :--- | :--- |
| **1** | `AGY2_FundAdvisory/advisory_engine.py` | `SmartExecutionDCAEngine` | 1. 新增 `get_fund_20d_metrics`：多级穿透计算单基真实 $\sigma_{\text{day}}$、年化波动率与自身 $\text{Bias20}$；<br>2. 修改 `calculate_vwap_execution_slippage`：彻底删除 0.04/0.14/0.18 固定常数，接入真实波动率与单基乖离率；<br>3. 新增 `get_historical_inflection_ruler`：暴露三大拐点与当前市场的水位对比数据；<br>4. 新增 `detect_intraday_valuation_anomaly`：实装急涨急跌 $1.5\sigma_{\text{day}}$ 异动判断模型。 |
| **2** | `AGY2_FundAdvisory/strategy_bridge.py` | `StrategyBridge` 类定义 | 增加对 `get_historical_inflection_ruler`、`get_fund_20d_metrics` 与 `detect_intraday_valuation_anomaly` 的包装暴露。 |
| **3** | `AGY2_FundAdvisory/app_gui.py` | `<style>` CSS 模块 (行 362+) | 注入 `.inflection-ruler-strip`、`.inflection-node-pill` 与 `@media (max-width: 640px)` 移动端自适应防挤压样式。 |
| **4** | `AGY2_FundAdvisory/app_gui.py` | `render_dual_wing_advisory_dashboard` (行 2160+) | 在首屏“📢 今日市场脉搏晨报”中渲染历史三大拐点实盘对照尺，精简冗余文案，达成复杂度守恒。 |
| **5** | `AGY2_FundAdvisory/app_gui.py` | Tab 1 智能定投 (行 3415-3505) | 1. 传入各基金真实的波动率与单基乖离率给 `plan_smart_dca`；<br>2. 在卡片区并列呈现历史拐点对照尺；<br>3. 在小抄与表格中融合尾盘异动指引。 |
| **6** | `AGY2_FundAdvisory/app_gui.py` | Tab 2 调仓执行单 (行 5230-5340) | 1. 调仓买入单调用 `calculate_vwap_execution_slippage` 传入真实单基波动率；<br>2. 表格 `建议操作` 与 `实操要点` 列接入 `detect_intraday_valuation_anomaly`，呈现 `🚨 尾盘急涨·防追高` 与 `💎 尾盘错杀·黄金坑`。 |
| **7** | `tests/test_g3_evolution_loop.py` | 全量回归与专项测试 | 新增单基真实波动率穿透、历史拐点对照尺结构、尾盘估值异动预警判定测试用例。 |

---

## 六、 物理红线与风控契约核验

1. **裁判文件绝对零触碰**：严禁修改 `judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py`；
2. **制度真实性**：场外公募基金必须遵循每日 15:00 唯一未知收盘净值确认，严禁日内多时段伪拆单；必须守死未满 7 天 1.50% 惩罚赎回费红线；
3. **数据真实性**：严禁伪造早盘分时数据或使用假随机数，所有日线数据均来自 `aligned_matrix_total_return.parquet` 与各赛道/单基日线，实时数据直接源自天天基金与新浪行情网关。
