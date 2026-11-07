# Explorer G8-3 技术深度调研与测试架构设计报告 (Analysis Report)

**报告撰写者**: Explorer G8-3 (Real-Time Radar & Test Explorer)  
**调研时间**: 2026-11-07  
**工作区目录**: `d:\Google\Workspace\Wind`  
**核心调研模块**: `AGY2_FundAdvisory/data_loader.py`, `AGY2_FundAdvisory/advisory_engine.py`, `AGY2_FundAdvisory/app_gui.py`, `AGY2_FundAdvisory/portfolio_manager.py`, `tests/`  

---

## 目录
1. [执行概览与使命目标](#一-执行概览与使命目标)
2. [只读铁律与防作弊契约核验](#二-只读铁律与防作弊契约核验)
3. [Item 6 (P1) 核心技术调研：盘中实时雷达融合与证据链](#三-item-6-p1-核心技术调研盘中实时雷达融合与证据链)
   - 3.1 `data_loader.py`: 实时资讯与宏观脉搏感知引擎深度解析
   - 3.2 `advisory_engine.py`: `OpportunityRadarEngine` 14 大赛道指标与盘中实时行情融合方案
   - 3.3 `app_gui.py`: 首屏晨报秒级时间戳与 Top 3 赛道卡片四维证据链呈现
4. [Tab 2 物理视图分支隔离与未保存修改保护调研](#四-tab-2-物理视图分支隔离与未保存修改保护调研)
   - 4.1 `is_t2_main_mode` 分支结构缺陷与平铺/隐藏整改逻辑
   - 4.2 表格未保存修改拦截与周边动作前置自动 Commit
   - 4.3 覆盖写入二次确认、Undo 历史快照与一键回滚护栏
   - 4.4 大额本金与调仓金额中文数量级防错提示
5. [现有测试资产审查与 G8 专属测试套件设计](#五-现有测试资产审查与-g8-专属测试套件设计)
   - 5.1 现有测试套件盘点
   - 5.2 G8 专项测试套件 `tests/test_g8_ux_and_realtime_fusion.py` 完整蓝图
6. [落地实施建议与执行计划](#六-落地实施建议与执行计划)

---

## 一、 执行概览与使命目标

根据主调度 Agent 派发指令与原始需求文档 `ORIGINAL_REQUEST.md`，G8 世代的核心任务是完成深度 UI/UX 审计整改（P0 至 P2 全量闭环）、Tab 2 物理视图真隔离、跨 Tab 真实路由跳转、盘中多源实时感知与四维评分证据链打通，并构建坚固的自动化测试护栏。

Explorer G8-3 的核心调查任务包括：
1. **Item 6 (P1)**：打通机会雷达盘中实时行情融合、实时快讯感知与四维评分证据链（涉及 `data_loader.py`, `advisory_engine.py`, `app_gui.py`）。
2. **测试审查与测试架构设计**：审查现有自动化测试，设计 G8 专用自动化测试套件（涵盖 Tab 2 物理视图隔离、未保存修改自动保存、盘中雷达实时行情融合与四维证据链、大额本金中文数量级防错、覆盖写入 Undo 回滚）。
3. **只读合规性审查**：核查 4 大只读裁判文件与 `DataLoader.simulate_execution` 扣费逻辑。

---

## 二、 只读铁律与防作弊契约核验

在启动技术设计前，对项目的只读约束和核心扣费模型进行了逐项代码核验：

### 1. 四大只读裁判文件状态核查

| 文件路径 | 状态 | 职责与保护内容 | 校验结果 |
| :--- | :---: | :--- | :---: |
| `AGY2_FundAdvisory/judge_engine.py` | 🔒 只读 | 未来函数因果探针、AST 静态反作弊扫描、6 大风格切片全量回归、参数扰动与 DSR 计数器 | 绝对只读，严禁修改 |
| `AGY2_FundAdvisory/holdout_vault.py` | 🔒 只读 | 2025-07-01 至今盲测数据物理隔离、3 次熔断锁 | 绝对只读，严禁修改 |
| `AGY2_FundAdvisory/AGENT_SPEC.md` | 🔒 只读 | 核心铁律、基准对标 (50/50)、6 大风格切片与 4 大门禁标准 | 绝对只读，严禁修改 |
| `tests/test_infra.py` | 🔒 只读 | 裁判基建自动化单元测试集（验证对齐矩阵、T+1 与 7 天惩罚扣费、未来函数探针、四岛策略接口） | 绝对只读，严禁修改 |

### 2. `DataLoader.simulate_execution` 函数签名与扣费逻辑核查

在 `AGY2_FundAdvisory/data_loader.py` 第 1354 至 1470 行：
```python
@staticmethod
def simulate_execution(
    weights_df: pd.DataFrame,
    prices_df: pd.DataFrame,
    is_otc: bool = True,
    penalty_days: int = 7,
    penalty_rate: float = 0.015,
    etf_impact: float = 0.001
) -> pd.DataFrame:
```
- **参数签名**：完全保留默认值，包含 `is_otc=True`，`penalty_days=7`，`penalty_rate=0.015`，`etf_impact=0.001`。
- **阶梯赎回扣费逻辑**：
  - 持有天数 $< 7$ 天：强制扣除 `penalty_rate` (1.50%)；
  - 持有天数 $7 \sim 29$ 天：C 类 0.50% / A 类 0.75%；
  - 持有天数 $30 \sim 179$ 天：A 类 0.50% / C 类 0.00%；
  - 持有天数 $180 \sim 364$ 天：A 类 0.25% / C 类 0.00%；
  - 持有天数 $\ge 365$ 天：全部免赎回费 (0.00%)；
  - 场内 ETF 冲击成本：单边 0.10% (`etf_impact`)。
- **核验结论**：此函数签名与扣费数学模型在后续修改中严禁产生任何字符级变动。

---

## 三、 Item 6 (P1) 核心技术调研：盘中实时雷达融合与证据链

### 3.1 `data_loader.py`: 实时资讯与宏观脉搏感知引擎深度解析

#### 1. 现状剖析
在 `AGY2_FundAdvisory/data_loader.py` 中：
- 第 205 至 224 行：已定义 14 大赛道关键字分类字典 `SECTOR_KEYWORD_RULES` 以及宏观关键词 `MACRO_KEYWORDS`、大盘关键词 `MARKET_KEYWORDS`。
- 第 247 至 432 行：实装了 `fetch_realtime_market_news_and_catalysts(limit=20, timeout=2.0, force_refresh=False, cache_ttl_sec=60.0)`。
  - **网络三轨设计**：第一优先请求东方财富 7x24 全球快讯 API (`https://newsapi.eastmoney.com/kuaixun/v1/getlist_102_ajaxResult_...`)；第二备选请求新浪财经 7x24 直播流 API (`https://zhibo.sina.com.cn/api/zhibo/feed...`)；
  - **超时与熔断**：网络调用统一受 `timeout=2.0` 秒严格约束；
  - **双层缓存架构**：
    - 内存级高速缓存：`_REALTIME_NEWS_MEM_CACHE`，TTL 默认 60 秒；
    - 磁盘级持久化缓存：`data/cache/realtime_news.json`；
    - 离线保底降级：极致离线无网时平滑降级至本地持久化文件；冷启动空库时返回真实宏观基线快讯（`pure_bond` 央行逆回购、`dividend_low_vol` 高股息央国企），保证 `len(flash_news) >= 2`，杜绝前端空列表白屏。
  - **解析产出**：
    ```python
    {
        "status": "success",
        "source": "eastmoney",
        "timestamp": "2026-11-07 15:30:00",  # 秒级感知时间戳
        "updated_at": "2026-11-07 15:30:00",
        "timestamp_sec": 1794036600.0,
        "flash_news": [...],                 # 清洗打标后的资讯列表
        "macro_items": [...],                # 宏观流动性资讯
        "sector_catalysts": {...},           # 14 大赛道对应的催化资讯列表
        "summary_bullets": [...],            # 高光要点（前 3 条快讯标题）
        "pulse_summary": "..."               # 综合宏观定调摘要
    }
    ```

#### 2. 指数实时行情抓取现状
- `data_loader.py` 第 1961 至 2178 行实装了 `fetch_custom_realtime_indices(codes, use_cache)` 与 `fetch_batch_realtime_indices(use_cache)`：
  - 批量调用东方财富 Push2 接口 (`https://push2.eastmoney.com/api/qt/ulist.np/get?secids=...`)，超时 2.5 秒；
  - 备选新浪行情接口；
  - 遇到非交易时段、休市或接口返回 0.00% 假平盘时，自动切入本地 parquet 基于最新两个真实交易日收盘价通过 `calc_offline_2day_return` 精算真实涨跌幅与点位；
  - 输出字典包含：`point`, `change`, `change_pct`, `ma20`, `bias_20`, `ret_20d`, `trend_status`, `trend_color`。

#### 3. 需补齐的封装细节
当前 `DataLoader` 类（第 860 行）仅绑定了：
```python
denoise_covariance_matrix = staticmethod(denoise_covariance_matrix)
fetch_market_turnover_and_sentiment = staticmethod(fetch_market_turnover_and_sentiment)
fetch_or_calc_index_valuations = staticmethod(fetch_or_calc_index_valuations)
```
建议在 `DataLoader` 类属性中显式挂载：
```python
fetch_realtime_market_news_and_catalysts = staticmethod(fetch_realtime_market_news_and_catalysts)
fetch_custom_realtime_indices = staticmethod(fetch_custom_realtime_indices)
fetch_batch_realtime_indices = staticmethod(fetch_batch_realtime_indices)
calc_offline_2day_return = staticmethod(calc_offline_2day_return)
```
确保外部调用无论是直接 `from data_loader import fetch_...` 还是 `DataLoader.fetch_...` 均能 100% 兼容。

---

### 3.2 `advisory_engine.py`: `OpportunityRadarEngine` 14 大赛道指标与盘中实时行情融合方案

#### 1. 现状分析
在 `AGY2_FundAdvisory/advisory_engine.py` 中：
- 第 26 至 225 行：`RADAR_SECTOR_CATALOG` 完整定义了 14 大赛道（`dividend_low_vol`, `csi_dividend`, `csi_300`, `csi_500`, `csi_1000`, `star_50`, `semiconductor`, `pharma_health`, `consumer_liquor`, `banking_dividend`, `domestic_gold`, `us_sp500_nasdaq`, `hstech`, `pure_bond`）。每个赛道均包含：
  - `name`: 中文名称
  - `symbol` / `benchmark_index` / `index_code`: 指数或 ETF 代码
  - `top_fund_code` / `default_fund`: 优选公募基金
  - `core_logic`: 核心入选逻辑依据说明文本（如：`精选高股息低波动标的，防御属性与股息分红双重安全边际`）
- 第 609 至 1020 行：`OpportunityRadarEngine`
  - `self.dynamic_metrics = self._calc_dynamic_sector_metrics()`：通过读取本地 Parquet/DuckDB 历史日线序列 `s` 计算 20 日 ER、MA20、Bias20、Slope20 与拥挤度；
  - `evaluate_sector(sec_id, meta)`：计算四维量化得分：
    - $S_{\text{val}}$: 估值分位得分（100 - 分位数，极端低估加权 10%）
    - $S_{\text{er}}$: 考夫曼信噪比（$\min(100, \text{er} \times 160)$）
    - $S_{\text{mom}}$: MA20 动量得分（包含 Bias20 > +6% 均值回归反超买惩罚）
    - $S_{\text{crowd}}$: 反拥挤度得分（波动放大倍数与过热惩罚）
    - 综合得分：$S_{\text{total}} = w_{\text{val}} S_{\text{val}} + w_{\text{mom}} S_{\text{mom}} + w_{\text{er}} S_{\text{er}} + w_{\text{crowd}} S_{\text{crowd}}$，权重来自 `OnlineHeuristicFactorEvolver` 的进化最优染色体。

#### 2. 存在的问题
1. **盘中行情断层**：`_calc_dynamic_sector_metrics` 仅基于本地历史静态 Parquet 日线（通常停留在昨日收盘），当盘中（如 10:30 或 14:30）指数大涨或大跌时，`Bias20`、点位及四维评分未融入今日盘中实时变动。
2. **证据链字段未完全透传至顶层输出**：`evaluate_sector` 返回的字典中，未携带 `core_logic`（核心推荐逻辑依据），且未输出该赛道今日实时涨跌幅 `realtime_chg_pct` 与最新点位 `realtime_point`。

#### 3. 盘中实时行情融合设计方案
在 `OpportunityRadarEngine` 中引入**盘中实时行情注入算子**：
1. **代码映射准备**：
   从 `RADAR_SECTOR_CATALOG` 中提取 14 大赛道对应的可观测行情代码列表：
   ```python
   sector_quote_codes = {
       "dividend_low_vol": "H30269", # 或 512890
       "csi_dividend": "000922",
       "csi_300": "000300",
       "csi_500": "000905",
       "csi_1000": "000852",
       "star_50": "000688",
       "semiconductor": "512480",    # 关联半导体芯片 ETF
       "pharma_health": "512010",    # 医药 ETF
       "consumer_liquor": "512690",  # 酒 ETF
       "banking_dividend": "512800", # 银行 ETF
       "domestic_gold": "518880",    # 黄金 ETF
       "us_sp500_nasdaq": "513500",  # 标普500 ETF
       "hstech": "513180",           # 恒生科技 ETF
       "pure_bond": "511260"         # 十年国债 ETF
   }
   ```
2. **实时行情批量感知**：
   在 `OpportunityRadarEngine.__init__` 或 `scan_all_sectors(realtime_quotes=None)` 中：
   - 若未传入 `realtime_quotes`，调用 `data_loader.fetch_custom_realtime_indices(list(set(sector_quote_codes.values())))`；
   - 构造 `{code: {"point": pt, "change_pct": chg_pct, "change": chg}}` 字典；
3. **指标微调与实时融入**：
   针对每个赛道，当获取到今日实时涨跌幅 $r_{\text{today}}$ 与实时点位 $P_{\text{rt}}$ 时：
   - 价格序列注入：若历史序列最后一日非今日，将 $P_{\text{rt}}$ 增量挂载到序列末端生成 $s_{\text{infused}} = [s, P_{\text{rt}}]$；
   - 动态更新 $P_t = P_{\text{rt}}$，重新精算均线 $\text{MA20}_{\text{rt}}$ 与实时乖离率：
     $$\text{Bias20}_{\text{rt}} = \frac{P_{\text{rt}} - \text{MA20}_{\text{rt}}}{\text{MA20}_{\text{rt}}} \times 100\%$$
   - 动量与超买评分联动更新：若盘中急涨致使 $\text{Bias20}_{\text{rt}} > +6\%$，自动触发均值回归惩罚机制；
4. **输出字典完整性升级**：
   在 `evaluate_sector` 的返回值中，补齐以下证据链字段：
   ```python
   return {
       "sector_id": sec_id,
       "name": meta["name"],
       "category": meta.get("category", "权益核心"),
       "val_percentile": val_pct,
       "s_val": round(s_val, 1),
       "s_mom": round(s_mom, 1),
       "s_er": round(s_er, 1),
       "s_crowd": round(s_crowd, 1),
       "total_score": total_score,
       "tag": tag,
       "tag_class": tag_class,
       "fund": fund_dict,
       "bias_20": bias_20,
       "slope_20": slope_20,
       "er_20": er,
       "crowding_score": round(s_crowd, 1),
       # ── G8 新增四维证据链与实时行情字段 ──
       "realtime_point": round(float(p_rt), 3 if p_rt < 100.0 else 2),
       "realtime_chg_pct": round(float(chg_pct), 2),
       "realtime_change": round(float(chg_val), 3 if p_rt < 100.0 else 2),
       "core_logic": meta.get("core_logic", "赛道景气度与宏观流动性共振"),
       "sub_scores": {
           "valuation": round(s_val, 1),
           "momentum": round(s_mom, 1),
           "snr": round(s_er, 1),
           "anti_crowding": round(s_crowd, 1)
       }
   }
   ```

---

### 3.3 `app_gui.py`: 首屏晨报秒级时间戳与 Top 3 赛道卡片四维证据链呈现

#### 1. "今日市场脉搏晨报" 渲染定位与整改（第 2434 至 2479 行）
- **当前代码现状**：
  在第 2468 至 2478 行，使用 `pulse_card_html` 渲染晨报卡片，右上角显示固定的 `"全景量化串联 ｜ 历史拐点并列对照"`，卡片内部仅有一行拼装的 `pulse_brief`，未展示秒级数据感知时间，也未展示最新实时快讯。
- **整改设计**：
  1. 调用 `data_loader.fetch_realtime_market_news_and_catalysts()` 获取最新资讯结构；
  2. 提取秒级时间戳：`news_ts = news_data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))`；
  3. 提取最新快讯标题与时间：
     ```python
     flash_list = news_data.get("flash_news", [])
     latest_news = flash_list[0] if flash_list else {}
     news_title = latest_news.get("title", "宏观政策持续发力，A股估值处于长期价值配置区间")
     news_time = latest_news.get("time", "")
     ```
  4. 升级卡片 HTML：
     - 右上角展示带时钟图标的秒级时间戳：`⏱️ 数据感知时间: {news_ts}`；
     - 在晨报正文下方，新增一条紧凑的快讯摘要条：
       `<div style="font-size: 11px; color: var(--text-secondary); margin-top: 4px; padding-top: 4px; border-top: 1px dashed var(--border-subtle); display: flex; align-items: center;"><span style="color: var(--accent-primary); font-weight: 700; margin-right: 6px;">⚡ 实时快讯</span><span style="color: var(--text-primary); text-overflow: ellipsis; white-space: nowrap; overflow: hidden;">{news_title}</span><span style="font-size: 10px; margin-left: 6px; opacity: 0.7;">[{news_time}]</span></div>`
     - 保持卡片紧凑，兼顾下方 `ruler_bar_html` 牛熊拐点对照尺，完全符合首屏信息密度守恒铁律。

#### 2. Top 3 赛道卡片渲染定位与整改（第 2481 至 2520 行）
- **当前代码现状**：
  在第 2486 至 2502 行：
  ```python
  <div class="decision-card" style="padding: 10px 12px; height: 100%; border-top: 2px solid {tag_color};">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
          <span style="font-size: 13px; font-weight: 700; color: var(--text-primary);">{sec['name']}</span>
          <span style="font-size: 11px; padding: 1px 6px; border-radius: 4px; background: var(--bg-canvas); color: {tag_color}; border: 1px solid var(--border-subtle);">{sec['tag']}</span>
      </div>
      <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 6px;">
          综合得分: <b style="color: var(--text-primary);">{sec['total_score']}</b> ｜ 估值分位: {sec['val_percentile']:.0f}%
      </div>
      ...
  ```
- **整改设计**：
  在卡片中增补三维信息，构建无懈可击的买方投顾证据链：
  1. **今日实时涨跌幅胶囊**：
     在赛道名称右侧展示实时涨跌幅：
     `chg_color = "var(--color-up)" if sec.get('realtime_chg_pct', 0.0) >= 0 else "var(--color-down)"`
     `<span style="font-size: 11px; font-weight: 700; color: {chg_color}; margin-left: 6px;">{sec.get('realtime_chg_pct', 0.0):+.2f}%</span>`
  2. **基因进化四维子项得分明细拆解**：
     在综合得分下方，展示一行紧凑四维胶囊（估值、动量、信噪比、反拥挤）：
     `<div style="display: flex; gap: 4px; margin: 4px 0; font-size: 10px; background: var(--bg-canvas); padding: 3px 6px; border-radius: 4px; border: 1px solid var(--border-subtle); justify-content: space-between;">`
     `<span>估 <b>{sec['s_val']}</b></span>`
     `<span>动 <b>{sec['s_mom']}</b></span>`
     `<span>噪 <b>{sec['s_er']}</b></span>`
     `<span>拥 <b>{sec['s_crowd']}</b></span>`
     `</div>`
  3. **核心入选逻辑依据**：
     在卡片底部代码下方，展示优雅紧凑的推荐逻辑：
     `<div style="font-size: 10.5px; color: var(--text-secondary); line-height: 1.35; margin-top: 4px; border-top: 1px dashed var(--border-subtle); padding-top: 4px;">💡 <b>入选逻辑</b>: {sec.get('core_logic', '')}</div>`

---

## 四、 Tab 2 物理视图分支隔离与未保存修改保护调研

### 4.1 `is_t2_main_mode` 分支结构缺陷与平铺/隐藏整改逻辑

#### 现状缺陷定位
在 `app_gui.py`：
- 第 4204 至 4213 行：用户通过单选按钮 `rad_tab2_view_mode` 切换模式：
  - 模式 1：`"🎯 持仓诊断与智能调仓 (主流程)"`（`is_t2_main_mode = True`）
  - 模式 2：`"💼 账本运维与实盘复盘档案 (宽屏工具坞)"`（`is_t2_main_mode = False`）
- **严重逻辑冲突点 1**：第 4649 行的 `with st.expander("🛠️ 账本工具坞...", expanded=(not is_t2_main_mode or not has_holdings)):`
  在 `is_t2_main_mode` 为 True 时，该 Expander 仍然存在于页面 DOM 中！即使折叠，依然占用了渲染资源并存在于页面底部。更严重的是，当 `not has_holdings`（空仓）时强制展开，直接破坏了主流程的简洁性。
- **严重逻辑冲突点 2**：第 5053 行的 `btn_tab2_diagnose`（诊断今日调仓时机）和第 5079 行的 `btn_tab2_all`（一键执行全案）在 `is_t2_main_mode` 为 False 时依然被无条件渲染；但下游第 5091 行和第 5213 行却被包裹在 `if is_t2_main_mode:` 内。导致用户在宽屏工具坞模式下点击诊断按钮，页面刷新后没有任何诊断结果出现（白点击假死现象）。

#### 整改方案
1. **主流程分支（`if is_t2_main_mode:`）**：
   - 渲染：多账本吧台、浮盈安全垫抗震看板、4 张概览卡、极速录基吧台、持仓明细表（含编辑操作栏）、步骤一推进栏（含诊断按钮）、步骤二时机裁决、步骤三调仓执行单。
   - **严禁**渲染第 4649 行的 `with st.expander("🛠️ 账本工具坞")`。取而代之的是在底部提供一条轻量提示：`st.info("🛠️ 需快速记账、检视 FIFO 批次或对账？请点击上方切换至【💼 账本运维与实盘复盘档案】。")`。
2. **宽屏工具坞分支（`else:` 即 `not is_t2_main_mode`）**：
   - 隐藏：步骤一持仓大表、极速录基吧台、步骤二与步骤三。
   - 平铺平铺渲染 6 大运维模块（无需 Expander 包裹）：直接在主画布渲染 `st.tabs`（`dock_tab1` 至 `dock_tab6`），让用户在首屏平铺检视快速粘贴导入、FIFO 批次透视、影子账本曲线、T+1 对账中心、同公司低摩擦转换与宏观估值分红。
3. **按钮自愈路由**：
   在 `btn_tab2_diagnose` 与 `btn_tab2_all` 的点击处理中，若当前处于工具坞模式，自动设置 `st.session_state["tab2_view_mode"] = "🎯 持仓诊断与智能调仓 (主流程)"` 与 `st.session_state["rad_tab2_view_mode"] = "🎯 持仓诊断与智能调仓 (主流程)"`，确保用户点击后无缝切回主流程展示诊断结果。

---

### 4.2 表格未保存修改拦截与周边动作前置自动 Commit

#### 现状缺陷定位
在 `app_gui.py`：
- 第 4575 行渲染了 `edited_table = st.data_editor(..., key="main_holdings_editor_tab2")`。
- 用户在表格中修改了份额、成本、分红方式或调仓意愿后，数据暂存在 `edited_table`。
- 如果用户未点击第 4581 行的 `"💾 保存修改并入库"`，而是点击了：
  - 第 4612 行 `"🔄 同步真实净值"`（`btn_sync_holdings_tab2`）
  - 第 4603 行 `"确认保存现金"`（`btn_confirm_cash_pop_tb`）
  - 第 4405 行极速录基吧台的 `"加入账本"`
  - 第 4630 行的删除指定标的
  这些按钮直接调用相应函数并触发 `st.rerun()`，导致用户在表格中辛苦输入的数据瞬间被旧快照冲刷丢失！

#### 整改方案
1. **未保存差异智能比对与动态醒目提醒**：
   对比 `edited_table` 与 `pm.export_snapshot_df()`：
   ```python
   def _has_uncommitted_table_changes(edited_df: pd.DataFrame, pm_inst: PortfolioManager) -> bool:
       if edited_df is None or edited_df.empty:
           return False
       snap_df = pm_inst.export_snapshot_df()
       if len(edited_df) != len(snap_df):
           return True
       # 比较核心字段：市值、份额、成本、调仓意愿
       for _, row in edited_df.iterrows():
           code = str(row.get("基金代码", "")).strip().zfill(6)
           if code not in pm_inst.holdings:
               return True
           cur_h = pm_inst.holdings[code]
           if abs(float(row.get("持有份额", 0.0)) - float(cur_h.shares)) > 0.01:
               return True
           if abs(float(row.get("持仓成本", 0.0)) - float(cur_h.cost_price)) > 0.0001:
               return True
           intent_raw = str(row.get("调仓意愿", "正常参与"))
           cur_intent = "lock" if "锁" in intent_raw else ("liquidate" if "清" in intent_raw else "normal")
           if cur_intent != getattr(cur_h, "rebalance_intent", "normal"):
               return True
       return False
   ```
   若检测到未保存修改，在表格正上方渲染醒目的黄色警示条：
   `st.warning("⚠️ 检测到持仓表格存在未提交修改，点击周边操作前系统将为您自动保存落库。")`
2. **所有周边动作执行前强制自动 Commit**：
   在点击 `"🔄 同步真实净值"`、`"确认保存现金"`、`"加入账本"` 等按钮的回调逻辑前，统一前置调用：
   ```python
   if "edited_table" in locals() and edited_table is not None:
       _commit_edited_holdings_table(edited_table, pm)
   ```
   彻底消除数据冲刷丢失隐患。

---

### 4.3 覆盖写入二次确认、Undo 历史快照与一键回滚护栏

#### 现状缺陷定位
在 `app_gui.py` 第 3837 行：
```python
if st.button(f"📥 覆盖写入当前激活账本 ({cur_name})", type="primary", use_container_width=True, key="btn_apply_bp_tier"):
    plan_data = three_step_plan if ... else None
    res_apply = pm.apply_zero_start_blueprint(...)
    st.success(...)
    st.rerun()
```
- **高危操作无摩擦**：单击按钮即直接调用 `pm.apply_zero_start_blueprint()`，瞬间清空 `self.holdings` 与 `self.pending_orders`！
- **快照缺失**：`apply_zero_start_blueprint()` 内部在清空前未调用 `self.save_state(record_snapshot=True)`，导致如果用户误触，甚至无法通过 `pm.undo()` 回滚！

#### 整改方案
1. **二次确认门禁（良性摩擦）**：
   当当前激活账本为实盘或已有持仓时（`len(pm.holdings) > 0`），使用 `st.popover` 承载二次确认：
   - 明确高亮提示：即将覆盖【{cur_name}】，当前账本中原有的 **{len(pm.holdings)} 只持仓**及所有历史批次将被清空替换！
   - 提供二次确认复选框：`chk_confirm = st.checkbox("我已知晓覆盖将清空存量持仓与免赎批次，确认覆盖", key="chk_confirm_overwrite")`；
   - 仅当勾选后，才激活确认覆盖按钮；同时提供 `"建议：另存为全新独立账本"` 引导分流。
2. **强制推栈 Undo 快照**：
   在执行 `apply_zero_start_blueprint()` 前，强制调用 `pm.save_state(record_snapshot=True)` 将原状态压入 SQLite 快照栈。
3. **覆写成功横幅自带一键撤销按钮**：
   在覆写成功的通知提示旁，提供快捷撤销按钮：
   `if st.button("↩️ 误触覆盖？一键撤销并恢复原持仓", key="btn_undo_overwrite"): pm.undo(); st.rerun()`。

---

### 4.4 大额本金与调仓金额中文数量级防错提示

#### 需求定位
在以下关键金额输入框下方：
1. Tab 1 拟投资总本金输入框（第 2826 行 `plan_capital_input`）；
2. Tab 2 现金池修改输入框（第 4596 行 `pop_edit_cash_pool_tb`）；
3. Tab 2 极速录基持有金额输入框（第 4392 行）；
4. Tab 2 新增补仓金额与提现金额输入框（第 5294、5301 行）；
5. Tab 4 AC算费金额输入框（第 6963 行）。

#### 防错转换函数设计
编写纯净、健壮的金融大额数字格式化函数：
```python
def format_chinese_amount_hint(amount: Union[float, int]) -> str:
    """
    金融级金额中文数量级核对提示：
    例如:
    100000.0  -> "¥100,000.00 (折合 10.00 万元 / 壹拾万元整)"
    1250000.0 -> "¥1,250,000.00 (折合 125.00 万元 / 壹佰贰拾伍万元整)"
    50000.0   -> "¥50,000.00 (折合 5.00 万元 / 伍万元整)"
    """
    amt = float(amount or 0.0)
    if amt < 0:
        return "¥0.00"
    
    # 基础千分位
    comma_str = f"¥{amt:,.2f}"
    
    # 数量级折算
    if amt >= 100000000.0:
        yi_val = amt / 100000000.0
        wan_val = (amt % 100000000.0) / 10000.0
        unit_str = f"折合 {yi_val:.2f} 亿元" if wan_val < 0.01 else f"折合 {yi_val:.2f} 亿 {wan_val:.2f} 万元"
    elif amt >= 10000.0:
        wan_val = amt / 10000.0
        unit_str = f"折合 {wan_val:.2f} 万元"
    else:
        unit_str = f"折合 {amt:.2f} 元"
        
    return f"{comma_str} ({unit_str})"
```
在 Streamlit 中紧随输入框下方以 `st.caption` 或带背景底色的微标签呈现：
`<div style='font-size: 11px; color: var(--accent-primary); font-weight: 600; margin-top: -6px; margin-bottom: 6px;'>💰 核对金额: {format_chinese_amount_hint(val)}</div>`

---

## 五、 现有测试资产审查与 G8 专属测试套件设计

### 5.1 现有测试套件盘点

我们全面核查了 `tests/` 目录下的核心自动化测试：
1. `tests/test_infra.py` (251 行): **只读基建测试**。覆盖对齐矩阵、T+1 与 7 天锁定期扣费（`test_simulation_operator_friction`）、因果探针反未来函数（`test_causal_probe_detects_leakage`）、四岛策略输出合规性、盲测金库额度上限、纯债套利拦截、A股权益仓位底线等。
2. `tests/test_adv_final_closure.py` (466 行): 覆盖 9 大标准资产类别分类（`test_specialized_1_all_nine_standard_asset_classes_covered`）、安全垫加权息率与影子调仓审计动态计算（`test_specialized_2`）、双模存量组合接管、现金池原子扣减与资产守恒等。
3. `tests/test_g3_evolution_loop.py` (638 行): 覆盖 EWMA 动态协方差与突变防御（`test_g3_1`）、主动风险预警哨巡检（`test_g3_2`）、10,000 次蒙特卡洛块重采样 CVaR 99%（`test_g3_3`）、智能微观执行滑点 VWAP 调度（`test_g3_4`）等。
4. `tests/test_gui_multi_ledger_stress.py` (573 行): 对抗性测试多账本高频切换原子性、Tab 1 步骤三另存为新账本 SHA256 完好性、异常与损坏账本容错回退等。
5. `tests/test_g7_architecture_and_decoupling.py` (121 行): 覆盖 `OnlineHeuristicFactorEvolver` 换手率惩罚与最大回撤、`OpportunityRadarEngine` 基因因子动态权重接入、Tab 2 双视图解耦契约及 `app_gui.py` 静态代码契约断言。

---

### 5.2 G8 专项测试套件 `tests/test_g8_ux_and_realtime_fusion.py` 完整蓝图

为确保 G8 世代的所有改动具备可验证性与防回归能力，特设计全新的自动化测试套件 `tests/test_g8_ux_and_realtime_fusion.py`。该套件包含以下六大核心测试用例：

#### Test Case 1: Tab 2 物理视图真隔离与分支结构测试
```python
def test_g8_tab2_view_mode_physical_isolation():
    """
    验证 Tab 2 双视图模式的物理分支隔离契约：
    1. 当 is_t2_main_mode 为 True (持仓诊断与智能调仓主流程) 时：
       - 主流程持仓表、诊断按钮、时机裁决、调仓执行单处于主分支；
       - 底部的重型 6-dock 账本工具坞必须被物理隔离/隐藏；
    2. 当 is_t2_main_mode 为 False (账本运维与实盘复盘档案) 时：
       - 主流程步骤一持仓表、步骤二、步骤三被折叠或隐藏；
       - 6 大工具坞 (dock_tab1 到 dock_tab6) 在首屏平铺展开；
    3. 验证诊断按钮具备自愈切换能力，在工具坞视图点击时自动将模式切回主流程。
    """
```

#### Test Case 2: 持仓表未保存修改自动保护与前置 Commit 测试
```python
def test_g8_holdings_table_uncommitted_protection_and_auto_commit():
    """
    验证可编辑持仓表格未保存修改保护机制：
    1. 构造 edited_table 包含修改后的份额 (如从 10000 改为 15000) 或修改调仓意愿；
    2. 验证 _has_uncommitted_table_changes 准确识别出存在未提交修改；
    3. 模拟用户点击“同步真实净值”或“修改现金池”，验证前置触发 _commit_edited_holdings_table；
    4. 验证 pm.holdings 中的份额与意愿被准确写入且持久化，数据未被冲刷丢失。
    """
```

#### Test Case 3: 盘中实时雷达行情融合、快讯感知与四维评分证据链测试
```python
def test_g8_realtime_radar_fusion_and_evidence_chain():
    """
    验证机会雷达实时资讯感知与盘中行情融合证据链：
    1. 验证 fetch_realtime_market_news_and_catalysts 具备 <= 2.0s 超时、秒级时间戳 (YYYY-MM-DD HH:MM:SS)、
       资讯条数 >= 1、宏观与赛道打标准确，且离线具备磁盘快照与保底回退；
    2. 验证 OpportunityRadarEngine.scan_all_sectors() 输出的 14 大赛道均携带：
       - realtime_chg_pct 与 realtime_point
       - 四维子项得分 (s_val, s_mom, s_er, s_crowd)
       - 核心入选逻辑说明 core_logic (非空字符串)
    3. 验证当盘中注入大涨行情 (Bias20 > +6%) 时，动量得分触发均值回归惩罚机制。
    """
```

#### Test Case 4: 大额资金中文数量级防错提示测试
```python
def test_g8_large_capital_chinese_amount_formatting():
    """
    验证金融级大额金额中文数量级防错转换：
    1. 输入 100000.0 返回含“¥100,000.00”与“折合 10.00 万元”；
    2. 输入 1250000.0 返回含“¥1,250,000.00”与“折合 125.00 万元”；
    3. 输入 50000000.0 返回含“¥50,000,000.00”与“折合 5000.00 万元 / 0.50 亿元”；
    4. 输入 500.0 返回含“¥500.00”；
    5. 边界值测试: 0.0, 负数, 浮点精度。
    """
```

#### Test Case 5: 覆盖写入 Undo 历史快照与一键回滚护栏测试
```python
def test_g8_overwrite_undo_snapshot_and_rollback_safety():
    """
    验证覆写主实盘账本的高危操作护栏与 Undo 回滚能力：
    1. 初始化一个拥有 3 只基金的主实盘账本，记录当前 holdings 状态与 SHA256；
    2. 执行 apply_zero_start_blueprint 或覆盖建仓操作；
    3. 验证在覆写发生前强制保存了 Undo 快照；
    4. 模拟误触后调用 pm.undo()；
    5. 验证 pm.holdings 100% 完美复原为覆盖前的 3 只标的及原份额、原成本，会计账本无损自愈！
    """
```

#### Test Case 6: 只读文件与核心算子签名防篡改核验测试
```python
def test_g8_readonly_files_and_simulate_execution_signature():
    """
    验证 G8 世代核心安全底线与反作弊契约：
    1. 验证四大只读裁判文件存在且不可破坏；
    2. 验证 DataLoader.simulate_execution 的函数签名参数完全一致；
    3. 验证 7 天未满卖出严格扣除 1.50% 惩罚费。
    """
```

---

## 六、 落地实施建议与执行计划

### 1. 修改文件与职责划分建议
- **`AGY2_FundAdvisory/data_loader.py`**：
  - 在 `DataLoader` 类上显式挂载 `fetch_realtime_market_news_and_catalysts`、`fetch_custom_realtime_indices`、`fetch_batch_realtime_indices`；
  - 确保 2 秒超时、内存 60s TTL 与本地 `data/cache/realtime_news.json` 磁盘回退完好。
- **`AGY2_FundAdvisory/advisory_engine.py`**：
  - 在 `OpportunityRadarEngine` 中引入实时行情注入；
  - 在 `evaluate_sector` 中输出 `realtime_point`, `realtime_chg_pct`, `realtime_change`, `sub_scores`, `core_logic`；
  - 确保 14 大赛道扫描保持极速（NumPy 优化，耗时严格 $< 100\text{ms}$）。
- **`AGY2_FundAdvisory/portfolio_manager.py`**：
  - 在 `apply_zero_start_blueprint` 清空持仓前，显式调用 `self.save_state(record_snapshot=True)` 确保覆写前状态入快照栈；
  - 确保 `pm.undo()` 能无缝恢复覆盖前的账本持仓。
- **`AGY2_FundAdvisory/app_gui.py`**：
  - 封装 `format_chinese_amount_hint`，并在本金、现金池、补仓提现输入框下方渲染中文万元防错提示；
  - 修正 Tab 2 双视图分支，`is_t2_main_mode` 下隐藏 6-dock 工具坞，`not is_t2_main_mode` 下在首屏平铺展示工具坞；在诊断按钮点击逻辑中加入自动切回主流程；
  - 在 Tab 2 表格上方添加未提交变动预警，并在同步真实净值、修改现金、加入账本按钮前自动前置执行 `_commit_edited_holdings_table`；
  - Tab 1 覆盖写入增加确认弹窗/Popover 二次确认，并在成功横幅旁附带撤销回滚按钮；
  - 首屏晨报展示秒级时间戳与实时快讯摘要；Top 3 赛道卡片展示实时涨跌幅胶囊、四维子项得分（估/动/噪/拥）与入选逻辑依据；
  - 清理 Tab 2 重复出现的滑块与重复按钮，清除预警哨开发口号。
- **`tests/test_g8_ux_and_realtime_fusion.py`**：
  - 编写上述设计的 G8 专属测试套件，接入项目自动化测试工作流。

---
*本技术调研报告由 Explorer G8-3 独立完成，严格遵循只读准则与工作区规范。*
