# G12 世代调查分析报告：移动止盈右侧破位逃顶、本地日线自愈与多源先行指标感知

- **调查专员**: `teamwork_explorer`
- **生成时间**: 2026-11-08T15:15:00Z
- **工作目录**: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g12_survey_2\`
- **对应里程碑**: G12 Survey Phase

---

## 1. 观察事实 (Observation)

### 1.1 `ActiveRiskSentry.inspect_portfolio` 维度 4 现状与坐过山车缺陷
- **文件路径**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\advisory_engine.py` (第 1706 至 1776 行)
- **代码逐字引用**:
  ```python
  # 维度 4: 个基阶梯止盈与深套诊断
  if bias_20 > 6.0:
      alerts.append({
          "level": "red",
          "dimension": "超买拥挤",
          "title": f"【{name} ({code})】短期暴涨超买 (Bias20: +{bias_20:.1f}%)",
          "desc": "短期正乖离率超过 +6.0% 阈值，处于结构性情绪过热区，警惕高位均值回归！",
          "action": "严禁单笔满仓追高，建议逢高阶梯兑现利润或设置止盈。",
          "action_type": "take_profit",
          "fund_code": code,
          "fund_name": name,
      })
  elif pnl_pct >= 15.0 and bias_20 > 5.0:
      alerts.append({
          "level": "yellow",
          "dimension": "阶梯止盈",
          "title": f"【{name} ({code})】浮盈达标 (+{pnl_pct:.1f}%) 触发阶梯止盈",
          "desc": f"进攻型基金持仓浮盈达 +{pnl_pct:.1f}% 且技术面正乖离偏高，宜分批锁定收益。",
          "action": "建议执行阶梯止盈减仓（赎回 30%~50% 转入纯债或红利低波）。",
          "action_type": "take_profit",
          "fund_code": code,
          "fund_name": name,
      })
  elif pnl_pct <= -12.0:
      # 深套诊断...
  ```
- **核心缺陷事实**:
  1. 当前逻辑仅在 `bias_20 > 6.0%` 或 `(pnl_pct >= 15.0% and bias_20 > 5.0%)` 处于高位超买时才提示止盈。
  2. 当标的累计浮盈丰厚（如 `pnl_pct >= 10.0%` 甚至 `+25%`）遇到突发急跌、大阴线直接跌破 20 日均线时，`bias_20` 转为负数（`bias_20 < 0`），超买与阶梯止盈条件全部失效；而深套诊断（`pnl_pct <= -12%`）同样不满足。
  3. **结果**: 系统在最关键的右侧破位逃顶时点**彻底失声**，用户无法收到任何警报，坐视浮盈全部抹平转为浮亏。
  4. 缺乏基于近 60 日最高净值（High-Water Mark, HWM）的回撤保护机制。

### 1.2 前端 `app_gui.py` 对预警哨的渲染与 Tab 2 调仓联动链路
- **文件路径**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\app_gui.py`
  - **右翼预警卡渲染** (第 3046 至 3088 行):
    遍历 `report.get("alerts", [])`，对 `level == "red"` 渲染红框 `🔴`，`action_type == "take_profit"` 时渲染按钮 `📉 生成【{fcode}】阶梯止盈单`。
  - **跨区跳转与意图注入** (第 3098 至 3100 行):
    ```python
    elif act_type in ["take_profit", "deep_loss_rebalance", "rebalance_sector"]:
        st.session_state.tab2_pending_take_profit = {"fund_code": fcode, "ratio": 0.40}
    ```
  - **Tab 2 承接横幅** (第 4598 至 4602 行):
    `tp_info = st.session_state.tab2_pending_take_profit` 触发横幅：
    `阶梯止盈标的: {tp_info.get('fund_code')}（下调目标权重 {int(tp_info.get('ratio', 0.4)*100)}%，增配纯债/红利低波）`
  - **Tab 2 调仓路径优化器传参** (第 5398 行、第 5484 行):
    `pending_take_profit=st.session_state.get("tab2_pending_take_profit")`，在 `strategy_bridge.py` 第 3620 行解析并调降持仓权重。

### 1.3 `data_loader.py` 本地 Parquet 日线缓存与日期断层现状
- **文件路径**: `d:\Google\Workspace\Wind\AGY2_FundAdvisory\data_loader.py` (第 1031 至 1260 行 `sync_latest_market_data`)
- **Parquet 实际日期探针结果**:
  - `data/processed/aligned_matrix_total_return.parquet`: 行数 2145，最新日期 `2026-11-06 00:00:00` (已同步至最新收盘日)。
  - `data/processed/csindex_H00300.parquet`: 行数 2139，最新日期 `2026-10-27` (落后 8 个自然日/6 个交易日)。
  - `data/processed/csindex_H30269.parquet`: 行数 2139，最新日期 `2026-10-27` (落后)。
  - `data/processed/indices/000685.SH.parquet` (半导体芯片): 行数 1649，最新日期 `2026-10-26` (落后近 2 周)。
  - `data/global/global_indices.parquet`: 最新日期 `2026-10-27`。
- **原因分析**:
  `DataLoader.sync_latest_market_data()` 目前仅针对 `self.cache_file` (`aligned_matrix_total_return.parquet`) 执行增量拼接与写入，而 `OpportunityRadarEngine._calc_dynamic_sector_metrics` 优先从 `RADAR_SECTOR_CATALOG` 中的 `fallback_parquet` (`000685.SH.parquet` 等) 读取独立日线。由于独立日线存在且长度 >= 25，引擎并未回退到 `aligned_matrix_total_return.parquet`，导致细分赛道均线与波动率计算停留在 2026-10-26。
- **只读裁判文件与契约红线**:
  检查四大只读裁判文件（`AGY2_FundAdvisory/judge_engine.py`、`AGY2_FundAdvisory/holdout_vault.py`、`AGY2_FundAdvisory/AGENT_SPEC.md`、`tests/test_infra.py`），均未硬编码任何特定 Parquet 文件路径；`test_infra.py` 中的 `test_data_loader_matrix_alignment` 依赖 `dl.load_total_return_matrix()` 返回行数 >= 2100 且五大资产列无 NaN。

### 1.4 多源实时先行指标实测与接口验证
- **14 大赛道核心场内 ETF 采集实测** (`https://push2.eastmoney.com/api/qt/ulist.np/get?secids=...`):
  使用单次 HTTP 请求批量拉取 14 只核心 ETF (`512890`, `515080`, `510300`, `510500`, `512100`, `588000`, `512760`, `512010`, `512690`, `512800`, `518880`, `513500`, `513180`, `511010`)：
  - 成功返回 14/14 只标的全部有效字段。
  - `f10`: 成交量放量比 (Volume Surge Ratio / 量比)，如芯片 512760 为 1.26 (放量)，博时标普500 513500 为 1.53，国债ETF 511010 为 1.49，沪深300 510300 为 0.43 (缩量)。
  - `f2` (价格) 与 `f43` (IOPV): 盘中支持实时计算折溢价率 $(\text{Price} - \text{IOPV})/\text{IOPV} \times 100\%$；休市或周末 IOPV 为 0 时可平滑回退至 $(\text{Price} - \text{NAV})/\text{NAV} \times 100\%$。
- **宏观跨市场指标实测**:
  - 中国 10 年期国债收益率: 本地 `data/macro/chinabond_yield_curve.parquet` 中 `y_10y` 为 1.6233% (亦可通过场内 511010 实时涨跌校验)。
  - 黄金: 新浪 `sh518880` 实时价 8.253 元，当日涨跌幅 -1.98%。
  - 隔夜纳指与联动: 新浪 `gb_ixic` 隔夜涨跌幅 +1.09% (24,579.42 点)，场内联动的 `sh513100` (纳指ETF) 实时价 2.158 元。
- **财经快讯情绪得分 (0-100)**:
  `DataLoader.fetch_realtime_market_news_and_catalysts` 已具备东财 7x24 快讯实时抓取与金融白名单过滤，目前产出的快讯为纯净的机构研报与宏观催化（如中信建投医药、海通白酒），但尚未对快讯极性进行量化赋分。

---

## 2. 逻辑推导链 (Logic Chain)

### 2.1 移动止盈与右侧破位逃顶模型推导
- **推导步骤 1 (识别坐过山车病根)**:
  由 1.1 观察可知，传统阶梯止盈依赖 `bias_20 > 5%`。当高估值成长股在阶段顶部反转展开大阴线洗盘或主跌浪时，最新价迅速由均线上方下穿至均线下方 (`bias_20 < 0`)。若仅有正乖离超买警报，破位杀跌当天系统恰恰停止警报。
- **推导步骤 2 (构建右侧破位三要素触发器)**:
  结合用户真实持仓浮盈与趋势动量：
  - **要素 1: 存量浮盈充分**: $\text{pnl\_pct} \ge 10.0\%$ (存在丰厚利润，具备锁利必要性)。
  - **要素 2: 均线破位**: 最新净值或盘中实时估值跌破 20 日均线 ($\text{bias\_20} < 0.0\%$)。
  - **要素 3: 动量恶化或巨阴放量下挫**: 满足以下任一条件：
    1. 20 日均线斜率转负 ($\text{slope\_20} < 0.0\%$)；
    2. 单日急跌超过 1.5 倍日均波动率 ($\text{single\_day\_drop} > 1.5 \times \sigma_{\text{day}}$，其中 $\sigma_{\text{day}} = \text{vol\_20} / \sqrt{250}$)。
  - **推导结论 1**: 当三要素同时满足时，确定性判定为“右侧破位”，输出红色预警 (`level: "red"`)，建议减持 50% 浮盈仓位 (`ratio: 0.50`)，并将资金沉淀为纯债或现金压舱石。
- **推导步骤 3 (构建高水位 HWM 浮盈回撤保护)**:
  - 提取标的近 60 日历史价格序列 $s[-60:]$，求取高水位峰值 $NAV_{\max, 60d} = \max(s[-60:])$。
  - 测算当前最新价（或盘中实时估算价）相对高水位的回撤幅度：
    $$\text{DD}_{\text{hwm}} = \frac{NAV_{\max, 60d} - NAV_{\text{now}}}{NAV_{\max, 60d}} \times 100\%$$
  - 当持仓标的浮盈充足 ($\text{pnl\_pct} \ge 10.0\%$) 且从阶段最高点回撤超过阈值 ($\text{DD}_{\text{hwm}} \ge 8.0\%$) 时，触发黄色或红色“高水位浮盈回撤保护”移动止盈警报，建议落袋 30%~50% 利润。

### 2.2 本地 Parquet 日线自动增量自愈逻辑推导
- **推导步骤 1 (定位缺失边界)**:
  由 1.3 观察可知，A 股最新收盘日为 2026-11-06，而 `000685.SH.parquet` 等独立日线停留在 2026-10-26。
- **推导步骤 2 (设计自愈执行流)**:
  在 `DataLoader` 中实装通用的轻量自愈算子 `DataLoader.heal_daily_parquet_gaps(parquet_path, code, symbol_type="index")`：
  1. 读取 Parquet 文件的最新日期 `last_date`。
  2. 获取系统有效交易日历截至今日的最新已收盘交易日 `latest_trade_date`（由 `CalendarParser` 与当前时间 15:00 阈值共同判定）。
  3. 若 `last_date < latest_trade_date`，计算缺失交易日集合 `missing_dates`。
  4. 优先从已同步的 `aligned_matrix_total_return.parquet` 提取对应列对齐；若无对应列，通过东财日 K 线 API (`push2his.eastmoney.com/api/qt/stock/kline/get`) 或新浪历史接口拉取区间日 K 线。
  5. 按原始列名规范拼装，去重并按日期递增排序后写回原文件（通过 `.tmp` + `os.replace` 原子写入），确保长度严格递增且 0 NaN。
- **推导步骤 3 (契约与裁判隔离验证)**:
  四大裁判文件不依赖特定非基准 Parquet，只要 `DataLoader.simulate_execution` 签名与扣费逻辑只读，自愈仅增强本地数据湖仓的鲜活性，完全符合反作弊规范。

### 2.3 多源先行指标与新闻情绪得分融合推导
- **推导步骤 1 (14 赛道核心 ETF 动量雷达)**:
  由 1.4 观察可知，通过东财 push2 批量接口（单次 HTTP 耗时 < 0.3s）可一次性获取 14 大赛道核心 ETF 的价格、涨跌幅、量比 (`f10`) 与成交额。将量比注入 `OpportunityRadarEngine.dynamic_metrics`，能够无滞后感知盘中资金攻击方向（如芯片放量 1.26 倍、国债避险放量 1.49 倍）。
- **推导步骤 2 (宏观跨市场联动与先行定调)**:
  整合“10Y 国债收益率（中债估值/国债ETF）、黄金现货（518880）、隔夜美股纳指（gb_ixic）”，输出宏观环境联动标签（如“美股科技偏强 ｜ 国内股债跷跷板 ｜ 黄金稳健对冲”），置于首屏晨报。
- **推导步骤 3 (财经新闻情绪极性评分模型)**:
  针对已过白名单的财经快讯，构建金融极性词典：
  - 看多极性词 $W^+$: `[增持, 回购, 利好, 超预期, 降准, 降息, 净买入, 突破, 创新高, 支持, 扩容, 注资, 回升, 反弹, 放量, 改善, 高质量, 底部, 企稳, 提振, 复苏]`
  - 看空极性词 $W^-$: `[减持, 利空, 低于预期, 违约, 立案, 下调, 破位, 跳水, 踩踏, 警示, 缩量, 暴跌, 抛售, 清盘, 承压, 下挫, 回落, 问询, 处罚, 亏损]`
  - 计算各条快讯命中词频，全市场加权归一化：
    $$\text{Score} = \text{clip}\left(50.0 + 10.0 \times \frac{\sum N^+ - \sum N^-}{\max(\sum N^+ + \sum N^-, 1)}, 10.0, 95.0\right)$$
  - 将情绪分与温度标签（如 `🔥 今日舆情情绪温度: 68分 (温和看多)`）紧凑呈现在首屏双翼晨报卡片中，形成宏观、盘面、舆情三位一体的立体感知。

---

## 3. 注意事项与边界假设 (Caveats)

1. **盘中 vs 盘后指标差异**:
   在交易日 09:30 至 15:00 期间，ETF 场内有实时点位与量比，天天基金有估算净值 `gszzl`；在非交易时间（如周末或夜间），ETF 行情保持在上一交易日 15:00 收盘态，IOPV 实时推送暂停。系统必须具备平滑判别机制，非交易时段自动展示上一收盘日确定性指标，严禁展示 `NaN` 或空白。
2. **`tab2_pending_take_profit` 止盈比例向下兼容**:
   目前 `app_gui.py` 内部硬编码 `ratio: 0.40`，右侧破位止盈要求果断减持 50% 仓位。调仓引擎需要支持动态读取预警指令中携带的 `ratio`（若为右侧破位或移动止盈，设定为 0.50；常规阶梯止盈设定为 0.40），且若为 C 类份额优先全额清理。
3. **Parquet 文件读写并发锁**:
   在 Streamlit 网页渲染与可能存在的后台进程并发访问时，写入 Parquet 必须使用临时文件原子覆盖（`tmp` + `os.replace`），防范文件损坏。

---

## 4. 结论与落地方案设计 (Conclusion)

### 4.1 核心结论
1. `ActiveRiskSentry.inspect_portfolio` 维度 4 存在明确的右侧破位逃顶逻辑盲区，必须补齐“浮盈 $\ge 10\%$ + 跌破 MA20 + (斜率转负 或 单日急跌 $>1.5\sigma$)”红色警报，并叠加近 60 日高水位回撤 $\ge 8\%$ 移动止盈机制。
2. `data_loader.py` 本地 Parquet 日线底座存在日期落后问题，需要实装轻量级自动补缺（Auto-Heal）管道，检测到落后交易日自动拉取补齐，彻底杜绝均线断层。
3. 14 赛道核心 ETF 放量比与折溢价率、宏观三大跨市场指标（10Y国债、黄金、纳指）、以及基于白名单快讯的 0-100 情绪温度模型，可在不侵入裁判文件的前提下无缝集成至 `DataLoader`，并在首屏双翼看板的晨报区域紧凑呈现。

### 4.2 建议实现伪代码与代码修改定位

#### 模块 1: `AGY2_FundAdvisory/advisory_engine.py` (ActiveRiskSentry 维度 4 升级)
- **定位**: 第 1706 至 1735 行
- **升级代码方案**:
  ```python
  # -------------------------------------------------------------
  # 维度 4: 个基阶梯止盈、移动止盈/右侧破位与深套诊断
  # -------------------------------------------------------------
  # 提取该标的或所属赛道的趋势与波动特征
  sec_metrics = radar_dynamic.get(sec_id, {})
  slope_20 = float(sec_metrics.get("slope_20", 0.0))
  vol_20 = float(sec_metrics.get("vol_20", 15.0))
  daily_vol = max(vol_20 / 15.811, 0.5) # 日均波动率百分比 (vol_20 / sqrt(250))

  # 获取当日单日跌幅 (结合实时估值 gszzl 或日涨跌幅)
  single_day_drop = 0.0
  q_item = fund_quotes.get(code, {})
  if isinstance(q_item, dict):
      gz_val = q_item.get("gszzl") or q_item.get("change_pct")
      if gz_val is not None:
          try:
              gz_f = float(gz_val)
              if gz_f < 0.0:
                  single_day_drop = abs(gz_f)
          except (ValueError, TypeError):
              pass

  # 计算近 60 日高水位净值回撤 (HWM Drawdown)
  hwm_dd = 0.0
  peak_nav_60 = cur_nav
  sec_series = getattr(radar_engine, "sector_price_series", {}).get(sec_id) if radar_engine else None
  if sec_series is not None and len(sec_series) >= 20:
      s_60 = sec_series[-60:]
      peak_nav_60 = float(np.max(s_60))
      cur_p = float(s_60[-1])
      if peak_nav_60 > 1e-6:
          hwm_dd = round((peak_nav_60 - cur_p) / peak_nav_60 * 100.0, 2)

  # 1. 右侧破位止盈逃顶 (浮盈 >= 10% 且 跌破 MA20 且 (斜率转负 或 大阴线跌破 > 1.5 * daily_vol))
  is_right_side_breakdown = (
      pnl_pct >= 10.0
      and bias_20 < 0.0
      and (slope_20 < 0.0 or single_day_drop > 1.5 * daily_vol)
  )

  # 2. 高水位浮盈回撤保护 (浮盈 >= 10% 且 阶段高点回撤 >= 8.0%)
  is_hwm_drawdown_risk = (
      pnl_pct >= 10.0
      and hwm_dd >= 8.0
  )

  if is_right_side_breakdown:
      alerts.append({
          "level": "red",
          "dimension": "移动止盈",
          "title": f"【{name} ({code})】右侧破位锁利预警 (浮盈 +{pnl_pct:.1f}%, 跌破MA20)",
          "desc": f"标的累计浮盈 +{pnl_pct:.1f}%，最新跌破20日均线(Bias20: {bias_20:+.1f}%)，且均线斜率转负({slope_20:+.1f}%)或单日急跌({single_day_drop:.1f}% > 1.5倍日均波幅)，右侧破位确立！",
          "action": "启动右侧破位锁利：果断兑现 50% 浮盈仓位，利润沉淀为纯债或现金压舱石。",
          "action_type": "take_profit",
          "take_profit_ratio": 0.50,
          "fund_code": code,
          "fund_name": name,
          "pnl_pct": pnl_pct,
          "bias_20": bias_20,
          "slope_20": slope_20,
      })
  elif is_hwm_drawdown_risk:
      alerts.append({
          "level": "yellow",
          "dimension": "移动止盈",
          "title": f"【{name} ({code})】高水位浮盈回撤保护 (较60日高点回撤 -{hwm_dd:.1f}%)",
          "desc": f"标的较近60日最高点累计回撤达 {hwm_dd:.1f}%（当前仍保留 +{pnl_pct:.1f}% 浮盈），触碰移动止盈保护线，防范利润全部回吐！",
          "action": "建议执行移动止盈：减持 30%~50% 浮盈仓位锁定战果。",
          "action_type": "take_profit",
          "take_profit_ratio": 0.40,
          "fund_code": code,
          "fund_name": name,
          "pnl_pct": pnl_pct,
          "hwm_dd": hwm_dd,
      })
  elif bias_20 > 6.0:
      alerts.append({
          "level": "red",
          "dimension": "超买拥挤",
          "title": f"【{name} ({code})】短期暴涨超买 (Bias20: +{bias_20:.1f}%)",
          "desc": "短期正乖离率超过 +6.0% 阈值，处于结构性情绪过热区，警惕高位均值回归！",
          "action": "严禁单笔满仓追高，建议逢高阶梯兑现利润或设置止盈。",
          "action_type": "take_profit",
          "take_profit_ratio": 0.40,
          "fund_code": code,
          "fund_name": name,
      })
  elif pnl_pct >= 15.0 and bias_20 > 5.0:
      alerts.append({
          "level": "yellow",
          "dimension": "阶梯止盈",
          "title": f"【{name} ({code})】浮盈达标 (+{pnl_pct:.1f}%) 触发阶梯止盈",
          "desc": f"进攻型基金持仓浮盈达 +{pnl_pct:.1f}% 且技术面正乖离偏高，宜分批锁定收益。",
          "action": "建议执行阶梯止盈减仓（赎回 30%~50% 转入纯债或红利低波）。",
          "action_type": "take_profit",
          "take_profit_ratio": 0.40,
          "fund_code": code,
          "fund_name": name,
      })
  elif pnl_pct <= -12.0:
      # 深套诊断 (保持原样)
  ```

#### 模块 2: `AGY2_FundAdvisory/data_loader.py` (本地 Parquet 自动增量自愈)
- **定位**: 在 `DataLoader` 类中追加 `auto_heal_sector_parquets()`
- **功能**:
  1. 扫描 `RADAR_SECTOR_CATALOG` 中定义的所有 `fallback_parquet` 文件。
  2. 获取日历中最新有效已收盘交易日 `T_close`。
  3. 对 `max_date < T_close` 的 Parquet 文件，若 `aligned_matrix_total_return.parquet` 存在对应列，自动前向填充截面补齐；若为独立行业代码（如 `000685.SH`），调用东财 K 线接口拉取补齐缺失日收盘点位，原子写回原路径。

#### 模块 3: `AGY2_FundAdvisory/data_loader.py` (多源先行指标采集器)
- **新增方法**:
  1. `DataLoader.fetch_sector_core_etf_metrics()`: 批量拉取 14 只核心 ETF 的量比 (`f10`)、实时价、涨跌幅、折溢价率。
  2. `DataLoader.fetch_macro_cross_market_indicators()`: 采集 10Y 国债、黄金、隔夜纳指联动三联指标。
  3. `DataLoader.calc_financial_news_sentiment(news_items)`: 输出 0-100 情绪分值与标签。

#### 模块 4: `AGY2_FundAdvisory/app_gui.py` (双翼晨报与 Tab 2 止盈比例联动)
- **定位**:
  - 第 2869 行晨报 HTML 卡片：并排嵌入 `🔥 舆情情绪温度: {sent_score}分 ({sent_label})` 与 `🌐 跨市场: 10Y国债 {cgb_10y:.2f}% ｜ 黄金ETF {gold_p:.2f}元 ｜ 隔夜纳指 {nasdaq_chg:+.2f}%`。
  - 第 3098 行：
    ```python
    elif act_type in ["take_profit", "deep_loss_rebalance", "rebalance_sector"]:
        tp_ratio = alert.get("take_profit_ratio", 0.40)
        st.session_state.tab2_pending_take_profit = {"fund_code": fcode, "ratio": tp_ratio}
    ```

---

## 5. 独立验证方法 (Verification Method)

### 5.1 自动化测试验证命令
在代码就绪后，执行以下针对性自动化测试：
```powershell
# 1. 验证四大裁判只读文件未受改动
py -3 -m pytest tests/test_infra.py -q

# 2. 验证防作弊与 ActiveRiskSentry 现有测试
py -3 -m pytest tests/test_anticheat_full_closure.py -q

# 3. 验证 G11 UI 交互与动作条完整性
py -3 -m pytest tests/test_challenger_g11_m1_actions.py -q

# 4. 专项回归与最终闭环测试
py -3 -m pytest tests/test_adv_final_closure.py -q
```

### 5.2 专项断言设计 (需新增在测试套件中)
1. **右侧破位逃顶专项断言**:
   构造持仓对象 `pnl_pct = 15.0%`、`bias_20 = -1.5%`、`slope_20 = -0.8%`。调用 `ActiveRiskSentry.inspect_portfolio()`，断言：
   - `alerts` 列表中必定包含 `dimension == "移动止盈"` 且 `level == "red"` 的警报；
   - `action_type == "take_profit"` 且 `take_profit_ratio == 0.50`。
2. **高水位回撤保护专项断言**:
   构造持仓对象 `pnl_pct = 12.0%`，从 60 日最高点回撤 9.0%，断言触发移动止盈保护黄牌。
3. **Parquet 自愈专项断言**:
   调用 `DataLoader.auto_heal_sector_parquets()`，验证所有存在 fallback 的 Parquet 最新行日期与 `aligned_matrix_total_return.parquet` 严格对齐至最新已收盘交易日，且无 NaN。
4. **多源先行指标专项断言**:
   调用 `DataLoader.fetch_sector_core_etf_metrics()`，验证返回字典包含 14 大赛道代码且 `volume_surge_ratio > 0`；验证 `sentiment_score` 处于 `[0.0, 100.0]` 闭区间内。

### 5.3 结论作废与失效条件 (Invalidation Conditions)
- 若修改导致 `tests/test_infra.py` 或 `tests/test_anticheat_full_closure.py` 中任何一项测试红灯，本方案作废并需调整。
- 若自愈逻辑尝试修改只读裁判文件或引入任何未来函数，必须立即阻断。
