# G9 世代量化风控、雷达重算与信源验真模块深入调研手记 (Handoff Report)

## 0. 核心调研概述 (Executive Summary)
本调研针对 G9 世代量化投顾系统中四个核心缺陷与合规隐患进行了深度代码级排查与架构方案设计：
1. **ActiveRiskSentry 真实规模反查与清盘告警**：精准定位 `advisory_engine.py` 第 1420~1436 行中 `else: aum = 2.5` 假规模默认兜底代码，设计了穿透本地有效缓存、天天基金实时接口、DuckDB/Parquet主数据及 `CORE_STRATEGY_POOL` / `EXTENDED_FUND_CATALOG` 的三级真实反查机制与“规模待核验”安全闭合告警方案。
2. **投资者适当性越界预警与盘中异动安全垫传导**：在 `ActiveRiskSentry.inspect_portfolio` 中新增结合账本风险评级（C1 至 C5）的权益仓位上限（20%~95%）与高波科技标的越界巡检，设计组合级止盈止损与盘中估值异动（单基 $\ge 2\%$、组合 $\ge 1\%$）对浮盈安全垫实时消耗的定量传导机制与一键降波纠偏方案。
3. **OpportunityRadarEngine 盘中最后一根 K 线真实重算与动态证据链**：定位第 1007 行粗暴算术相加 `bias_20 = round(bias_20 + chg_pct, 2)`，设计融合盘中实时价末端重算序列，精准重算 MA20、Bias20、Slope20、ER20、20日年化波动率与20日最大回撤的技术方案；设计 4 维量化证据链动态合成器与首屏 Top 3 赛道卡风险收益对称披露规范。
4. **快讯信源验真**：定位 `data_loader.py` 第 404~428 行在离线模式下使用 `datetime.now()` 伪造实时时间戳的代码，设计 `is_realtime` 与 `source_type` 物理隔离架构，首屏晨报明确区分实时抓取信源与离线快照，彻底根除时间戳伪造。

---

## 1. 现场观测 (Observation)

### 1.1 假规模兜底与清盘掩盖代码定位
- **文件路径**：`d:\Google\Workspace\Wind\AGY2_FundAdvisory\advisory_engine.py`
- **代码行号**：第 1420 至 1449 行
- **原始代码实录**：
```python
            # 维度 6 (分支 A): 基金本体排雷预警 (迷你基规模 < 0.5亿)
            meta = fund_meta.get(code, {})
            aum = meta.get("aum_billion")
            if aum is None:
                raw_aum = meta.get("aum", meta.get("asset_size"))
                if raw_aum is not None:
                    try:
                        f_aum = float(raw_aum)
                        aum = f_aum / 1e8 if f_aum > 100000 else f_aum
                    except (ValueError, TypeError):
                        aum = 2.5
                else:
                    aum = 2.5
            else:
                try:
                    aum = float(aum)
                except (ValueError, TypeError):
                    aum = 2.5

            if aum < 0.50:
                alerts.append({
                    "level": "red",
                    "dimension": "本体排雷",
                    "title": f"【{name} ({code})】规模仅 {aum:.2f} 亿元 (<0.5亿清盘警戒线)",
                    "desc": "最新资产净值低于 5,000 万元法定警戒线，面临清盘终止运作的严重法律与流动性风险！",
                    "action": "择机置换为同赛道规模适中（10~50亿）的标杆公募基金。",
                    "action_type": "replace_fund",
                    "fund_code": code,
                    "fund_name": name,
                })
```
- **直接观测结论**：
  若外部调用者（如单元测试、新账本或外部模块）传入的 `fund_metadata` 字典缺少某个持仓代码，代码无条件执行 `aum = 2.5`（赋予 2.5 亿元安全规模），直接跳过 `if aum < 0.50`。这导致真实规模小于 5000 万元的濒临清盘迷你基金被虚假粉饰为“安全”，严重违反金融合规与排雷哨兵职责。

### 1.2 投资者适当性约束缺失与盘中异动孤岛观测
- **文件路径**：`d:\Google\Workspace\Wind\AGY2_FundAdvisory\advisory_engine.py`（第 1104~1551 行）、`strategy_bridge.py`（第 191~285 行）、`portfolio_manager.py`（第 2840~2950 行）
- **直接观测**：
  1. `ActiveRiskSentry.inspect_portfolio` 当前巡检的 7 大维度（7天锁仓、C类临期、C类满30天、超买深套、赛道集中度、迷你基与大盘线、动态相关性）中，**完全没有接收或校验用户的风险等级档位（C1 至 C5）**。
  2. `strategy_bridge.py` 中虽然完整定义了 `RISK_TIERS_CONFIG`：
     - C1 安稳保守型：权益仓位区间 `[15, 20]`%，最大回撤限额 `5%`；
     - C2 稳健固收+型：权益仓位区间 `[30, 40]`%，最大回撤限额 `10%`；
     - C3 平衡进取型：权益仓位区间 `[50, 78]`%，最大回撤限额 `15%`；
     - C4 成长进攻型：权益仓位区间 `[75, 85]`%，最大回撤限额 `25%`；
     - C5 极限追击型：权益仓位区间 `[85, 95]`%，最大回撤限额 `40%`。
     但在 `ActiveRiskSentry` 中从未将实盘持仓的权益市值占比与客户风险等级进行比对。即使用户设定了 C1 保守型，若持仓中满配 80% 甚至全部是高波动科技成长基金（如 013841 银华集成电路或 011613 华夏科创50），预警哨也不会发出任何适当性越界警告。
  3. `portfolio_manager.py` 第 2840~2950 行虽然实装了浮盈安全垫计算 `calculate_portfolio_cushion_and_stress_model`，但仅在 Tab 2 作为静态模型展示；盘中交易时段单基发生超过 2% 的剧烈波动或组合异动超 1% 时，`ActiveRiskSentry` 未建立盘中实时估值（`gszzl`）变动对该安全垫消耗金额与消耗比例的实时传导警报。

### 1.3 机会雷达盘中粗暴算术相加与文案静态硬编码观测
- **文件路径**：`d:\Google\Workspace\Wind\AGY2_FundAdvisory\advisory_engine.py`
- **代码行号**：第 1003 至 1008 行，第 1072 行
- **原始代码实录**：
```python
            # 动态调整 bias_20
            if "bias_20" in rt_quote:
                bias_20 = float(rt_quote["bias_20"])
            else:
                bias_20 = round(bias_20 + chg_pct, 2)
...
            "core_logic": meta.get("core_logic", "赛道景气度与宏观流动性共振"),
```
- **前端 Top 3 卡片渲染（`app_gui.py` 第 2651 至 2656 行）**：
```html
<div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 4px;">
    综合得分: <b style="color: var(--text-primary);">{sec['total_score']}</b> ｜ 估值分位: {sec['val_percentile']:.0f}% ｜ 动量: {sub_s.get('momentum', 0.0):.0f}分
</div>
<div style="font-size: 11px; color: var(--text-primary); background: var(--bg-elevated); padding: 3px 6px; border-radius: 4px; margin-bottom: 4px;">
    💡 入选依据：<b>{core_logic_txt}</b>
</div>
```
- **直接观测结论**：
  1. `bias_20 = round(bias_20 + chg_pct, 2)` 直接将日内百分比变动粗暴加在历史 20 日乖离率上。因为 $\text{Bias}_{20} = \frac{P - \text{MA}_{20}}{\text{MA}_{20}} \times 100\%$，最新价 $P_{\text{rt}}$ 的变动会同时改变分子和分母（MA20 会吸收新价格）；并且均线斜率 `slope_20` 与考夫曼信噪比 `er_20` 完全未随盘中价格更新。
  2. `core_logic` 直接读取 `RADAR_SECTOR_CATALOG` 中的静态文本（如“精选高股息低波动标的...”），未结合当前动态演化出的真实估值分位、斜率强弱、信噪比纯净度与拥挤度生成动态量化证据链。
  3. 前端首屏 Top 3 机会赛道卡仅披露了“估值分位”与“动量”，信噪比分项、反拥挤度分项以及反映风险维度的“20日年化波动率”与“20日最大回撤”均被隐匿，未能实现“风险与收益对称呈现”。

### 1.4 快讯信源时间戳伪造观测
- **文件路径**：`d:\Google\Workspace\Wind\AGY2_FundAdvisory\data_loader.py`
- **代码行号**：第 403 至 428 行
- **原始代码实录**：
```python
    # 7. 极致离线保底结构体 (保底也提供真实宏观基线，保证 len(flash_news) >= 1)
    fallback_time = datetime.now().strftime("%H:%M:%S")
    fallback_items = [
        {
            "title": "央行持续投放逆回购呵护跨期流动性，银行间流动性合理充裕",
            "digest": "央行持续开展公开市场逆回购操作，保持流动性合理充裕，引导市场利率平稳运行。",
            "time": fallback_time,
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tags": ["宏观流动性"],
            "matched_sectors": ["pure_bond"]
        },
...
    offline_res = {
        "status": "cold_start_fallback",
        "source": "cold_start_fallback",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
```
- **直接观测结论**：
  在断网或离线兜底时，代码直接使用 `datetime.now()` 伪造快讯发布时间与系统抓取时间戳；在 `app_gui.py` 第 2618 行中，页面顶部展示的 `⏱️ 数据感知时间: {data_sense_time}` 直接渲染该伪造的时间戳，用户无法辨别眼前展示的是今日刚抓取的实时行情快讯，还是数天前的离线历史快照。

---

## 2. 推理逻辑链 (Logic Chain)

```
[观测 1.1: aum = 2.5 静态硬编码]
   │
   ├─► 根因: 代码为防止缺少元数据抛出 None 异常或触发假清盘告警，采用 2.5 亿元作为安全常数
   │
   └─► 推理: 真实迷你基若缺少本地缓存，直接被 2.5 亿掩盖；
       必须建立三级真数据穿透 (本地缓存 -> 实时API -> 核心池字典)；
       若仍无，必须显式输出“规模待核验”黄牌告警，落实金融合规故障闭合原则。

[观测 1.2: 适当性未纳入主动哨兵，盘中异动与安全垫脱节]
   │
   ├─► 根因: Sentry 仅按孤立基金和固定 35% 赛道集中度检查，缺少账户级风险等级约束 (C1~C5)
   │
   └─► 推理: 保守型客户 (C1) 容忍回撤 <=5%，配置高比例权益是严重合规错配；
       必须计算组合权益占比 sum(MV_equity) / MV_total 并与 tier["equity_range"][1] 校验；
       同时将盘中估值异动 delta_pnl 与综合安全垫绑定，实时暴露本金消耗程度。

[观测 1.3: bias_20 简单线性相加，静态入选文案，卡片信息不对称]
   │
   ├─► 根因: 盘中实时更新时偷懒未重算序列；静态字典代替动态归因；UI 空间未合理规划
   │
   └─► 推理: 必须将实时价追加到序列末尾构成 s_rt，基于统一数学公式重算 MA20、Bias20、Slope20、ER20；
       利用四维得分区间组合动态拼装 100% 自洽文案；
       在 Top 3 卡片中完整列出四维得分 (估、动、噪、拥) 与两项风险指标 (Vol20, MDD20)。

[观测 1.4: 离线新闻打当前时间戳 datetime.now()]
   │
   ├─► 根因: 缺少信源状态与时间戳真伪隔离标识，离线模式直接取系统当前时间
   │
   └─► 推理: 必须在返回字典注入 is_realtime 与 source_type；
       离线缓存严格保留 snapshot 写入时的原始时间 updated_at；
       UI 上用绿灯/黄灯徽章明确标注是实时联网还是离线快照。
```

---

## 3. 技术改造设计方案与具体实施蓝图 (Actionable Blueprints)

### 3.1 任务一：ActiveRiskSentry 真实规模反查与清盘告警改造
在 `AGY2_FundAdvisory/advisory_engine.py` 的 `ActiveRiskSentry.inspect_portfolio` 中，替换原有的第 1420~1449 行规模逻辑：

```python
# -------------------------------------------------------------
# 维度 6 (分支 A): 基金本体排雷预警 (真实规模穿透反查与清盘警戒线)
# -------------------------------------------------------------
meta = fund_meta.get(code, {})
aum = meta.get("aum_billion")
if aum is None:
    raw_aum = meta.get("aum", meta.get("asset_size"))
    if raw_aum is not None:
        try:
            f_aum = float(raw_aum)
            aum = f_aum / 1e8 if f_aum > 100000 else f_aum
        except (ValueError, TypeError):
            aum = None

# 一级穿透：若仍为 None，主动调用 DataLoader.get_fund_metadata
if aum is None:
    try:
        from data_loader import DataLoader
        dl_meta = DataLoader.get_fund_metadata(code)
        if dl_meta and dl_meta.get("aum") is not None:
            aum = float(dl_meta["aum"])
        elif dl_meta and dl_meta.get("aum_billion") is not None:
            aum = float(dl_meta["aum_billion"])
    except Exception:
        pass

# 二级穿透：从 CORE_STRATEGY_POOL 与 EXTENDED_FUND_CATALOG 反查
if aum is None:
    try:
        from portfolio_manager import CORE_STRATEGY_POOL, EXTENDED_FUND_CATALOG
        pool_meta = CORE_STRATEGY_POOL.get(code) or EXTENDED_FUND_CATALOG.get(code)
        if pool_meta:
            pool_aum = pool_meta.get("aum_billion") or pool_meta.get("aum")
            if pool_aum is not None:
                aum = float(pool_aum)
    except Exception:
        pass

# 三级决策：严格区分 真实规模达标 / 真实迷你基(<0.5亿) / 规模待核验状态，彻底杜绝 2.5 假兜底
if aum is not None:
    if aum < 0.50:
        alerts.append({
            "level": "red",
            "dimension": "本体排雷",
            "title": f"【{name} ({code})】规模仅 {aum:.2f} 亿元 (<0.5亿清盘警戒线)",
            "desc": "最新资产净值低于 5,000 万元法定警戒线，面临清盘终止运作的严重法律与流动性风险！",
            "action": "择机置换为同赛道规模适中（10~50亿）的标杆公募基金。",
            "action_type": "replace_fund",
            "fund_code": code,
            "fund_name": name,
            "aum_billion": aum,
            "aum_status": "LIQUIDATION_DANGER",
        })
else:
    # 彻底杜绝 aum = 2.5！未获取到规模时显式输出黄色告警
    alerts.append({
        "level": "yellow",
        "dimension": "本体排雷",
        "title": f"【{name} ({code})】规模待核验",
        "desc": "未能从多级数据湖仓或实时接口获取到该基金最新资产规模，存在潜在迷你基清盘不可见风险！",
        "action": "建议手动核对基金公司季报净资产规模，确保规模大于 5,000 万元法定警戒线。",
        "action_type": "replace_fund",
        "fund_code": code,
        "fund_name": name,
        "aum_billion": None,
        "aum_status": "PENDING_VERIFICATION",
    })
```

### 3.2 任务二：投资者适当性越界预警与盘中异动安全垫传导
在 `ActiveRiskSentry.inspect_portfolio` 方法签名与实现中：
1. **入参扩充**：支持 `investor_risk_tier: Optional[str] = None`（若未传则从 `kwargs.get("risk_tier")` 或账本元数据获取，默认 `"C3"`）。
2. **适当性越界检验**：
   - 提取权益类资产总市值 $MV_{\text{equity}}$（排除纯债固收、黄金对冲与货币现金），计算组合实盘权益占比 $R_{\text{equity}} = \frac{MV_{\text{equity}}}{MV_{\text{total}}}$。
   - 读取 `RISK_TIERS_CONFIG[tier]` 的权益仓位上限（如 C1 为 20%、C2 为 40%、C3 为 78%）。
   - 若 $R_{\text{equity}} > \text{max\_equity}$，触发适当性越界预警：
     - 若超出幅度 $\ge 15\%$ 或 C1 客户持仓包含半导体/科创等高波科技基金，定性为红色严重越界（`level="red"`）；
     - 否则定性为黄色常规超配（`level="yellow"`）。
     - 提供一键降波纠偏动作建议（计算超配权益金额 $(R_{\text{equity}} - \text{max\_equity}) \times MV_{\text{total}}$ 并建议平移至纯债 `002351`）。
3. **组合级止盈止损巡检**：
   - 计算组合累计浮盈率 $P_{\text{pnl}} = \frac{MV_{\text{total}} - Cost_{\text{total}}}{Cost_{\text{total}}} \times 100\%$。
   - 组合止盈：若 $P_{\text{pnl}} \ge 20.0\%$，触发 `dimension="组合级止盈"`，`action_type="take_profit"`，提示分批锁定收益。
   - 组合止损：若 $P_{\text{pnl}} \le \text{tier\_cfg['max\_tolerated\_loss']}$（如 C1 $\le -5\%$，C2 $\le -10\%$，C3 $\le -15\%$），触发 `dimension="组合级止损"`，`level="red"`，`action_type="defense_mode"`。
4. **盘中异动对安全垫实时消耗传导**：
   - 遍历持仓提取实时盘中估值变动 `gszzl`（通过 `snapshot.get("fund_quotes")` 或实时行情字典）。
   - 检测单基异动（$|gszzl| \ge 2.0\%$）与组合加权异动 $\Delta P_{\text{intraday}} = \sum MV_i \times \frac{gszzl_i}{100.0}$。
   - 若组合浮盈安全垫 $S_{\text{cushion}} > 0$ 且 $\Delta P_{\text{intraday}} < 0$：
     - 精算安全垫实时消耗金额 $|\Delta P_{\text{intraday}}|$ 与消耗比例 $\frac{|\Delta P_{\text{intraday}}|}{S_{\text{cushion}}} \times 100\%$。
     - 若消耗比例 $\ge 20\%$ 或组合估值单日跌超 1.0%，触发 `dimension="盘中异动安全垫传导"` 预警。

### 3.3 任务三：OpportunityRadarEngine 盘中末端 K 线重算与动态证据链
1. **价格序列保留与末端重算**：
   - 在 `OpportunityRadarEngine._calc_dynamic_sector_metrics` 中，将用于计算的真实价格序列缓存至 `self.sector_price_series[sec_id] = s`。
   - 在 `evaluate_sector` 中：
     若获取到盘中实时行情 `rt_quote`（包含 `change_pct` 或 `point`）：
     - 计算盘中最新价格 $P_{\text{rt}}$；
     - 构造包含盘中最新价的完整序列 $s_{\text{rt}} = np.append(s[:-1], P_{\text{rt}})$（若末尾同日）或 $np.append(s, P_{\text{rt}})$；
     - 精确重算：
       $$\text{MA}_{20} = \text{mean}(s_{\text{rt}}[-20:])$$
       $$\text{Bias}_{20} = \frac{P_{\text{rt}} - \text{MA}_{20}}{\text{MA}_{20}} \times 100.0$$
       $$\text{Slope}_{20} = \frac{\text{MA}_{20} - \text{mean}(s_{\text{rt}}[-25:-5])}{\text{mean}(s_{\text{rt}}[-25:-5])} \times 5000.0$$
       $$\text{ER}_{20} = \frac{|P_{\text{rt}} - s_{\text{rt}}[-20]|}{\sum_{k=1}^{19} |s_{\text{rt}}[-k] - s_{\text{rt}}[-k-1]|}$$
       $$\text{Vol}_{20} = \text{std}(\text{diff}(s_{\text{rt}}[-21:]) / s_{\text{rt}}[-21:-1]) \times \sqrt{252} \times 100.0$$
       $$\text{MDD}_{20} = \max_{\tau \le t} \frac{\max s_{\text{rt}} - s_{\text{rt}}}{\max s_{\text{rt}}} \times 100.0$$
2. **动态量化证据链合成器设计**：
   实现 `_synthesize_quantitative_evidence(val_pct, s_val, s_mom, s_er, s_crowd, bias_20, slope_20, er_20, sec_id)`：
   - 估值层：根据 `val_pct` 分位输出低估安全边际（$<20\%$ 黄金击球区、$<40\%$ 合理偏低、$>70\%$ 估值偏高）；
   - 动量层：根据 `bias_20` 与 `slope_20` 输出右侧共振、均线温和爬升或超跌反抽，以及超买均值回归约束；
   - 信噪比层：根据 `er_20`（$\ge 0.65$ 单边趋势纯净，$<0.4$ 高频震荡博弈）；
   - 反拥挤度层：根据 `s_crowd` 输出筹码清爽安全或交易拥挤度；
   - 将合成字符串赋给 `core_logic` 并在返回字典中携带。
3. **首屏 Top 3 卡片风险收益对称渲染（`app_gui.py`）**：
   在卡片 HTML 中完整并列展示：
   - 收益与景气四维分：估值 `{sub_s['valuation']:.0f}`分 ｜ 动量 `{sub_s['momentum']:.0f}`分 ｜ 信噪 `{sub_s['kaufman_snr']:.0f}`分 ｜ 拥挤 `{sub_s['anti_crowding']:.0f}`分；
   - 风险暴露双指标：20日年化波动 `{sec.get('vol_20', 0.0):.1f}%` ｜ 20日最大回撤 `-{sec.get('mdd_20', 0.0):.1f}%`；
   - 动态证据链：`💡 入选依据：<b>{core_logic_txt}</b>`。

### 3.4 任务四：快讯信源验真与时间戳隔离
1. **`data_loader.py` 数据结构改造**：
   - 当东方财富 / 新浪实时接口成功返回时：
     `is_realtime = True`，`source = "东方财富 7x24快讯"`（或新浪），`source_type = "online_realtime"`，`timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")`，每条快讯保留接口原始时间 `time_str` 与机构名称；
   - 当读取磁盘快照（`REALTIME_NEWS_CACHE_FILE`）兜底时：
     `is_realtime = False`，`source = "离线本地缓存快照"`，`source_type = "offline_cached_snapshot"`，`timestamp = cached.get("updated_at")`（**严禁使用 `datetime.now()` 覆写**），`snapshot_age_sec = (datetime.now() - cached_dt).total_seconds()`；
   - 当冷启动无任何磁盘缓存时：
     `is_realtime = False`，`source = "系统离线预置基线"`，`source_type = "offline_baseline"`，`timestamp = "2026-11-01 00:00:00 (离线预置)"`，明确标注为内置预置数据，**彻底根除 `datetime.now()` 冒充**。
2. **首屏晨报 UI 渲染改造（`app_gui.py`）**：
   - 若 `news_res.get("is_realtime")` 为真：
     展示绿色指示灯：`<span style="color: var(--color-down);">🟢 实时联网信源 ({source})</span> ⏱️ 抓取时间: {news_res['timestamp']}`；
   - 若为离线快照：
     展示琥珀色指示灯：`<span style="color: var(--accent-primary);">🟠 离线本地缓存快照 (网络未连接)</span> ⏱️ 快照时间: {news_res['timestamp']}`；
   - 快讯前缀标注信源机构与原始时间：`⚡ 快讯 [{item.get('source', '')} {item.get('time', '')}]: {latest_flash}`。

---

## 4. 边界条件与风险防范 (Caveats)

1. **测试断言兼容性 (Test Asset Invariants)**：
   - 在 `test_challenger_r8_m2_adversarial.py` 第 217 行中，断言了预警项的 `action_type` 必须属于枚举列表 `["lock_shares", "countdown_hold", "switch_a_class", "take_profit", "deep_loss_rebalance", "rebalance_sector", "replace_fund", "defense_mode", "offense_mode"]`。
   - **设计对齐**：新设立的“规模待核验”预警项必须将 `action_type` 设为已注册的 `"replace_fund"`；适当性权益超配设为 `"rebalance_sector"`；组合止盈设为 `"take_profit"`；组合止损与盘中异动设为 `"defense_mode"`。这样既满足功能拓展，又 100% 免疫现有对抗测试的断言抛错。
2. **全通健康组合测试兼容性 (All-Passed Invariant)**：
   - `test_risk_sentry_all_passed()` 中传入了 `safe_holdings`（包含 005561 与 002351），且显式传入了 `fund_metadata={"005561": {"aum_billion": 15.6}, "002351": {"aum_billion": 280.0}}`。
   - **设计对齐**：当传入合法规模且无超买锁仓时，适当性默认在 C3 平衡型下（权益 15.6 亿对 280 亿，权益占比极低），必须保证 `all_passed` 依然稳定返回 `True`，确保回归测试通过。
3. **空组合与单标的容错 (Defensive Fallback)**：
   - 当组合为空 `{}` 或仅有 1 只标的时，适当性与集中度计算必须优雅跳过（`if total_portfolio_mv <= 0: return report`），绝不抛出除以零或索引越界异常。

---

## 5. 结论 (Conclusion)

1. **定性分析**：原系统中关于基金规模的 `else: aum = 2.5`、雷达乖离率的 `bias_20 = round(bias_20 + chg_pct, 2)` 以及离线新闻打 `datetime.now()` 的做法，是典型的“为求不报错而注入伪造常数与未来时间戳”的量化硬伤。
2. **架构闭环**：通过穿透式三级规模反查、投资者适当性双向约束、末端 K 线完整重算与信源真伪双轨隔离，能够彻底消灭事实幻觉，将系统提升至真实的买方机构级量化风控标准。
3. **实施就绪**：上述代码定位精确到具体行号，修改逻辑具备完整的输入输出规范与兼容性防御，可直接交由实施代理（coder）落地实施。

---

## 6. 独立验证方法 (Verification Method)

在实施完成后，可通过以下步骤执行独立验证：

### 6.1 单元测试与回归测试验证
在项目根目录运行 pytest 测试套件：
```powershell
py -3 -m pytest tests/test_infra.py tests/test_m3_advisory_modules.py tests/test_anticheat_full_closure.py tests/test_g8_ux_and_realtime_fusion.py -v
```

### 6.2 专项验证用例脚本设计
编写并运行专项核验脚本验证 4 大要点：
1. **反查规模与清盘告警验证**：
   - 构造持有一只全市场真实迷你基金（或规模为 0.35 亿元的标的，且不传 `fund_metadata`），调用 `sentry.inspect_portfolio`，验证返回包含 `【0.35 亿元 (<0.5亿清盘警戒线)】`；
   - 构造一只未知代码 `999999`，验证返回 `【规模待核验】`，绝不赋予 2.5 亿元通过。
2. **投资者适当性与盘中异动验证**：
   - 设定账本档位为 `C1`，持仓配置 60% 科技成长标的（如 013841），验证 `inspect_portfolio` 抛出 `【投资者适当性越界】` 红色/黄色预警；
   - 传入盘中估值异动 `gszzl = -3.5%`，验证预警哨输出 `【盘中异动预警】实时消耗安全垫`。
3. **雷达末端重算与证据链自洽验证**：
   - 传入盘中涨跌幅 `+5.0%`，断言 `evaluate_sector` 输出的 `bias_20`、`slope_20`、`er_20` 是由重算序列产生，且 `bias_20 != old_bias + 5.0`；
   - 断言 `core_logic` 动态包含当前分位数与信噪比字样；
   - 断言返回字典包含 `vol_20` 与 `mdd_20`。
4. **信源验真验证**：
   - 模拟网络断开，调用 `DataLoader.fetch_realtime_market_news_and_catalysts`，断言返回字典的 `is_realtime` 为 `False`，`source` 包含“离线”字样，且 `timestamp` 等于缓存文件的修改时间，绝不等于当前的系统秒数。

### 6.3 裁判文件与工作区隔离验证
- 验证四个只读裁判文件零修改：`judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py`；
- 验证全局配置文件 `c:\Users\deanc\.gemini\GEMINI.md` 零修改。
