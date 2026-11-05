# 侧边栏核心指数行情走廊与全市场自由定制 (R1) 深度调研与架构分析报告

- **调研智能体**: Explorer Survey R8-1
- **生成时间**: 2026-11-05T01:48:00Z
- **目标工作区**: `d:\Google\Workspace\Wind`
- **调研范围**: 需求 R1（样式与实时点位获取、3 层专业卡片指标、全市场指数/ETF 自由定制、设置弹窗交互与持久化）以及配套 UI 细节修复

---

## 1. 核心调研摘要 (Executive Summary)

本调研针对用户原始需求与验收标准（`ORIGINAL_REQUEST.md` R1 需求及参考截图图 1），对当前系统中的样式表、行情接口、卡片 DOM 渲染、数据同源逻辑及持久化存储进行了逐行深度排查与实证测试：

1. **样式失效与徽章黑字/无边框根因**：
   - 在 `data_loader.py`（第 298 行）中，估值状态返回为下划线格式 `status = "very_low"` 与 `status = "very_high"`；
   - 在 `app_gui.py`（第 1370 行）中生成徽章类名 `class="index-pill-val-badge val-{v_status}"`，即输出了 `.val-very_low` 与 `.val-very_high`；
   - 然而在 `app_gui.py`（第 878、898 行）的 CSS 规则中仅定义了连字符版本 `.val-very-low` 与 `.val-very-high`，导致极低估与过热徽章类名匹配脱靶，背景色与边框完全失效。
2. **“整排 0.00% 假平盘”成因与两交易日真实回退算法**：
   - 现行 `fetch_batch_realtime_indices()` 仅硬编码了 6 只指数；且在非交易时段或离线测试中，接口返回 0.00% 或直接回退至硬编码静态值（如 `fb_chg: 0.0`），导致周末或收盘后整排显示 0.00%（截图图 1 中科创50、中证红利、中证500、中证1000均为 0.00%）；
   - 实测证明：本地湖仓 `data/processed/aligned_matrix_total_return.parquet` 及 `data/processed/indices/*.parquet` 具备完整的日度跨牛熊收盘价，提取最新两行（如 2026-11-02 与 2026-11-03）即可秒级精算真实历史涨跌幅（如 H00300 -0.20%, H00905 -1.45%, H00852 -1.71%, STAR50 -3.81%, AU9999 +0.60%），完全杜绝假平盘。
3. **卡片 3 层专业指标架构**：
   - 现有卡片仅为 1 层扁平左右结构（名称代码在左、点位与单一涨跌幅在右）；
   - 升级为 3 层纵向流：
     - **第一行**：指数名称 + 6 位代码（左），最新实时点位 + 涨跌幅防压扁药丸（右）；
     - **第二行**：真实 PE/PB 估值分位数微胶囊（左），近 20 日真实累计涨跌幅（右）；
     - **第三行**：MA20 生命线偏离趋势（如 `🟢 站上 MA20 偏离 +1.5%` 或 `🛡️ 跌破 MA20 防守 (-1.2%)`），以微细虚线分割。
4. **全市场 38+ 核心指数/ETF 目录与自选持久化**：
   - 规划覆盖宽基、红利、科技、医药、消费、金融、新能源、军工、周期、港股、美股、黄金、国债等 12 大板块共 38 只标的；
   - 严守基准真实性铁律：中证红利必须且仅映射为 `000922`（东财 `1.000922`，新浪 `s_sh000922`），严禁混淆为 `000015`（上证红利）；
   - 侧边栏设置弹窗实装：展示数量滑块（3 至 15 只）、支持拼音首字母检索的多选排序器、任意 6 位代码实时联网校验接入；
   - 自选配置持久化落盘至 `data/cache/custom_watchlist.json`。
5. **UI 细节修复定位**：
   - `button[kind="primary"]` 补齐 `#ffffff !important` 样式；
   - Tab 1 步骤一合并第 1840 行灰框与第 1850 行 caption 中的重复资产锚点与权益上限描述。

---

## 2. 样式与实时点位获取调查 (Styles & Real-Time Fetching)

### 2.1 CSS 类名失配与修复依据

#### 现状调查
- `app_gui.py` CSS 样式定义（第 878-902 行）：
  ```css
  .val-very-low {
      background: rgba(16, 185, 129, 0.15) !important;
      color: #10b981 !important;
      border: 1px solid rgba(16, 185, 129, 0.35) !important;
  }
  .val-low { ... }
  .val-mid { ... }
  .val-high { ... }
  .val-very-high {
      background: rgba(239, 68, 68, 0.12) !important;
      color: #ef4444 !important;
      border: 1px solid rgba(239, 68, 68, 0.3) !important;
  }
  ```
- `data_loader.py` 输出逻辑（第 297-306 行）：
  ```python
  if pct_val <= 20.0:
      status, label = "very_low", f"PE {pe_val:.1f} ({pct_val:.0f}%极低)"
  ...
  else:
      status, label = "very_high", f"PE {pe_val:.1f} ({pct_val:.0f}%过热)"
  ```
- `app_gui.py` DOM 渲染逻辑（第 1370 行）：
  ```python
  v_badge_html = f'<span class="index-pill-val-badge val-{v_status}" style="font-size: 10px; margin-left: 4px;">{v_label}</span>'
  ```
- 生成的 HTML 标签为：`class="index-pill-val-badge val-very_low"` 与 `class="index-pill-val-badge val-very_high"`。由于下划线与 CSS 中的连字符不匹配，浏览器无法命中规则，徽章呈现透明背景与默认黑字。
- 另外，单元测试 `tests/test_adversarial_m1_2_prod_screener_liquidation_gui.py` 第 382 行显式断言了 `assert f".{sc}" in gui_source`，其中 `status_classes = ["val-very-low", "val-low", "val-mid", "val-high", "val-very-high"]`。

#### 修复方案
在 `app_gui.py` 中将选择器扩展为并集选择器，同时兼容两种命名：
```css
.val-very-low, .val-very_low {
    background: rgba(16, 185, 129, 0.15) !important;
    color: #10b981 !important;
    border: 1px solid rgba(16, 185, 129, 0.35) !important;
}
.val-very-high, .val-very_high {
    background: rgba(239, 68, 68, 0.12) !important;
    color: #ef4444 !important;
    border: 1px solid rgba(239, 68, 68, 0.3) !important;
}
```
同时在 Python 生成类名处可做标准化：`v_cls = f"val-{v_status.replace('_', '-')}"`，实现双保险。

---

### 2.2 批量实时获取与非交易时段真实涨跌幅计算

#### 现状调查
- `portfolio_manager.py` 中的 `fetch_batch_realtime_indices()` 仅支持 `CORE_MARKET_INDICES_CONFIG` 中的 6 只固定标的（000300, 000688, 000922, 000905, 000852, 518880）。
- 当网络异常或处于非交易时段时（如周末或清晨开盘前），东方财富/腾讯接口返回点位但涨跌幅可能为 `0.0` 或未开盘状态；兜底逻辑使用了静态写入的数值，导致整排标的显示 `0.00%`（见截图图 1）。

#### 实证测试与接口机制
在实测脚本 `scratch/test_batch_indices.py` 中验证：
- 东方财富批量接口：
  `https://push2.eastmoney.com/api/qt/ulist.np/get?secids={secids}&fields=f12,f14,f2,f3,f4`
  - 返回字段：
    - `f12`: 标的代码
    - `f14`: 标的名称
    - `f2`: 最新价格/点位（指数需除以 100.0，普通股票型/QDII/债券型 ETF 需除以 1000.0）
    - `f3`: 涨跌幅百分比 $\times 100$（即需除以 100.0 得到例如 `+1.25%`）
    - `f4`: 涨跌额（指数除以 100.0，ETF 除以 1000.0）
  - 实测可在 150ms 内单次并发拉取 30 只以上标的。
- 新浪行情备用接口：
  `https://hq.sinajs.cn/list={syms}`
  - 支持 `s_sh` / `s_sz` 简易指数或个股格式。

#### 非交易时段两交易日真实回退算法
当盘中实时接口不可用，或处于非交易时段且接口返回 `change_pct == 0.0` 时：
1. **优先从 `data/processed/aligned_matrix_total_return.parquet` 提取**：
   - 读取最新两行（`iloc[-1]` 与 `iloc[-2]`）；
   - 列名映射：
     - `000300`: `H00300`
     - `000905`: `H00905`
     - `000852`: `H00852`
     - `000922`: `H00922`
     - `000688`: `STAR50_STITCH`
     - `518880`: `AU9999`
     - `513500`: `SPX_CNY`
     - `511260` / 固收: `H11009`
   - 计算公式：
     $$\text{change\_pct} = \frac{P_{\text{curr}} - P_{\text{prev}}}{P_{\text{prev}}} \times 100\%$$
     $$\text{change} = P_{\text{curr}} - P_{\text{prev}}$$
   - 实测结果（2026-11-02 到 2026-11-03）：
     - 沪深300: `-0.20%`
     - 中证500: `-1.45%`
     - 中证1000: `-1.71%`
     - 中证红利: `-0.16%`
     - 科创50: `-3.81%`
     - 黄金: `+0.60%`
2. **从 `data/processed/indices/{code}.SH.parquet` 或 `{code}.SZ.parquet` 提取**：
   - 针对非宽基指数（如 `000016.SH`, `399006.SZ` 等），直接读取本地 754 个指数 parquet 文件，读取其最后两行 `close` 价格并计算真实涨跌幅；
   - 彻底解决休市、周末或断网时的假平盘问题。

---

## 3. 丰富卡片 3 层专业指标调查 (3-Layer Professional Indicator Card)

### 3.1 截图对比与指标分层架构

参考图 1 现状：卡片只展示了名称、代码、点位、涨跌幅以及估值胶囊（堆在名称右侧导致横向拥挤）。

按照需求 R1，每张卡片必须升级为 **3 层专业纵向信息流**：

| 层级 | 左侧内容 | 右侧内容 | 样式与几何铁律约束 |
|---|---|---|---|
| **第一行 (核心行情)** | 指数名称（粗体 13px） + 6 位代码（等宽 11px 浅灰） | 最新实时点位（13px 粗体 tabular-nums） + 涨跌幅胶囊（红/绿/灰底） | 胶囊必须配置 `flex: 0 0 auto !important; white-space: nowrap !important;` 物理防挤压，严禁折行 |
| **第二行 (估值与动量)** | 真实 PE/PB 历史分位数标签（如 `PE 12.8 (67%适中)`，支持 `.val-*` 5 档配色） | 近 20 日累计收益率（如 `近20日 +3.5%` 或 `近20日 -6.2%`） | 左右对齐，字号 11px，收益率根据正负显示 `--color-up` / `--color-down` |
| **第三行 (均线攻防)** | MA20 趋势状态标签（如 `🟢 站上 MA20 偏离 +1.5%` 或 `🛡️ 跌破 MA20 防守 (-1.2%)`） | 辅助均线点位（如 `MA20: 3,945.2`） | 顶部附 1px 细虚线分割（`border-top: 1px dashed var(--border-subtle)`），增加视觉层次 |

### 3.2 卡片 DOM 结构与 CSS 设计

```html
<div class="sidebar-index-card">
    <!-- 第一行：名称代码 + 点位涨跌幅 -->
    <div class="sidebar-card-row-top">
        <div class="sidebar-card-title-box">
            <span class="sidebar-index-name">{name}</span>
            <span class="sidebar-index-code">{code}</span>
        </div>
        <div class="sidebar-card-quote-box">
            <span class="sidebar-index-pt">{point_fmt}</span>
            <span class="sidebar-index-badge {badge_cls}">{sign}{change_pct:.2f}%</span>
        </div>
    </div>

    <!-- 第二行：真实估值分位 + 近20日涨跌幅 -->
    <div class="sidebar-card-row-mid">
        <span class="index-pill-val-badge {val_badge_cls}">{val_label}</span>
        <span class="sidebar-card-ret20" style="color: {ret20_color};">近20日 {ret20_sign}{ret20_pct:.1f}%</span>
    </div>

    <!-- 第三行：均线趋势攻防状态 -->
    <div class="sidebar-card-row-bot">
        <span class="sidebar-card-trend-text" style="color: {trend_color};">{trend_status_text}</span>
        <span class="sidebar-card-ma-pt">MA20: {ma20_fmt}</span>
    </div>
</div>
```

#### CSS 空间几何不变量（符合 GEMINI.md Rule 14 & 15）
```css
.sidebar-index-card {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: 8px;
    padding: 8px 10px;
    margin-bottom: 8px;
    box-shadow: var(--shadow-card) !important;
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-height: 80px;
    height: auto !important;
    overflow: visible !important;
    box-sizing: border-box;
    transition: all 0.2s ease;
}
.sidebar-index-card:hover {
    border-color: var(--border-hover) !important;
    background: var(--bg-elevated) !important;
}
.sidebar-card-row-top, .sidebar-card-row-mid, .sidebar-card-row-bot {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
}
.sidebar-card-row-top {
    min-height: 22px;
}
.sidebar-card-title-box {
    display: flex;
    align-items: baseline;
    gap: 5px;
    min-width: 0;
}
.sidebar-card-quote-box {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
}
.sidebar-index-badge {
    flex: 0 0 auto !important;
    white-space: nowrap !important;
    padding: 2px 5px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
}
.sidebar-card-row-bot {
    border-top: 1px dashed var(--border-subtle);
    padding-top: 3px;
    margin-top: 1px;
    font-size: 10.5px;
}
```

### 3.3 数据计算来源与单源同真函数

为保证侧边栏卡片与 Tab 1、Tab 2、机会雷达数据 100% 同源，定义计算提取函数：
- **估值分位数**：调用 `data_loader.fetch_or_calc_index_valuations()`，获取 `pe_ttm`、`percentile`、`label` 与 `status`；
- **MA20 与 20日涨跌幅**：
  从本地湖仓或最新行情时序中截取最后 25 个交易日点位序列 $S = [p_{-25}, \dots, p_{-1}]$：
  $$\text{MA20} = \frac{1}{20} \sum_{i=1}^{20} p_{-i}$$
  $$\text{Bias20} = \frac{p_{\text{latest}} - \text{MA20}}{\text{MA20}} \times 100\%$$
  $$\text{Ret20D} = \frac{p_{\text{latest}} - p_{-21}}{p_{-21}} \times 100\%$$
  - 若 $\text{Bias20} \ge 0$：状态文字为 `🟢 站上 MA20 偏离 +{Bias20:.1f}%`
  - 若 $\text{Bias20} < 0$：状态文字为 `🛡️ 跌破 MA20 防守 ({Bias20:.1f}%)`

---

## 4. 全市场指数/ETF 自由定制与交互机制调查 (Catalog, Watchlist Dialog & Persistence)

### 4.1 全市场 38+ 核心指数与 ETF 目录规划

遵循基准真实性铁律（特别确保中证红利 `000922` 严禁混淆为上证红利 `000015`），构建涵盖全市场 12 大资产类别的标准内置目录：

| 板块类别 | 标的代码 | 标的名称 | 东财 secid | 新浪代码 | 拼音检索码 | 资产属性 |
|---|---|---|---|---|---|---|
| **宽基核心** | `000300` | 沪深300 | `1.000300` | `s_sh000300` | `hs300` | 指数 |
| **宽基核心** | `000016` | 上证50 | `1.000016` | `s_sh000016` | `sz50` | 指数 |
| **宽基核心** | `000905` | 中证500 | `1.000905` | `s_sh000905` | `zz500` | 指数 |
| **宽基核心** | `000852` | 中证1000 | `1.000852` | `s_sh000852` | `zz1000` | 指数 |
| **宽基核心** | `000688` | 科创50 | `1.000688` | `s_sh000688` | `kc50` | 指数 |
| **宽基核心** | `399006` | 创业板指 | `0.399006` | `s_sz399006` | `cybz` | 指数 |
| **宽基核心** | `000001` | 上证指数 | `1.000001` | `s_sh000001` | `szzs` | 指数 |
| **宽基核心** | `399001` | 深证成指 | `0.399001` | `s_sz399001` | `szcz` | 指数 |
| **红利高股息** | `000922` | 中证红利 | `1.000922` | `s_sh000922` | `zzhl` | 指数（严禁混淆） |
| **红利高股息** | `H30269` | 红利低波 | `0.H30269` | `s_sh512890` | `hldb` | 指数 |
| **红利高股息** | `000015` | 上证红利 | `1.000015` | `s_sh000015` | `szhl` | 指数 |
| **红利高股息** | `512890` | 红利低波ETF | `1.512890` | `s_sh512890` | `hldbetf` | 场内ETF |
| **科技/半导体** | `512480` | 半导体ETF | `1.512480` | `s_sh512480` | `bdtetf` | 场内ETF |
| **科技/芯片** | `159995` | 芯片ETF | `0.159995` | `s_sz159995` | `xpetf` | 场内ETF |
| **科技/AI** | `515980` | 人工智能ETF | `1.515980` | `s_sh515980` | `rgznetf` | 场内ETF |
| **科技/计算机** | `512720` | 计算机ETF | `1.512720` | `s_sh512720` | `jsjetf` | 场内ETF |
| **医药生物** | `512010` | 医药ETF | `1.512010` | `s_sh512010` | `yyetf` | 场内ETF |
| **医药生物** | `159992` | 创新药ETF | `0.159992` | `s_sz159992` | `cxyetf` | 场内ETF |
| **医药生物** | `512170` | 医疗ETF | `1.512170` | `s_sh512170` | `yletf` | 场内ETF |
| **消费白酒** | `512690` | 酒ETF | `1.512690` | `s_sh512690` | `jetf` | 场内ETF |
| **消费大盘** | `512600` | 主要消费ETF | `1.512600` | `s_sh512600` | `zyxfetf` | 场内ETF |
| **家电龙头** | `159996` | 家电ETF | `0.159996` | `s_sz159996` | `jdetf` | 场内ETF |
| **金融证券** | `512880` | 证券ETF | `1.512880` | `s_sh512880` | `zqetf` | 场内ETF |
| **金融银行** | `512800` | 银行ETF | `1.512800` | `s_sh512800` | `yhetf` | 场内ETF |
| **新能源汽车** | `515030` | 新能源车ETF | `1.515030` | `s_sh515030` | `xnycetf` | 场内ETF |
| **新能源光伏** | `515790` | 光伏ETF | `1.515790` | `s_sh515790` | `gfetf` | 场内ETF |
| **绿色电力** | `561560` | 电力ETF | `1.561560` | `s_sh561560` | `dletf` | 场内ETF |
| **高端装备** | `512660` | 军工ETF | `1.512660` | `s_sh512660` | `jgetf` | 场内ETF |
| **传统能源** | `515220` | 煤炭ETF | `1.515220` | `s_sh515220` | `mtetf` | 场内ETF |
| **工业金属** | `512400` | 有色金属ETF | `1.512400` | `s_sh512400` | `ysjsetf` | 场内ETF |
| **海外互联** | `513180` | 恒生科技ETF | `1.513180` | `s_sh513180` | `hskjetf` | 跨境QDII |
| **港股大盘** | `159920` | 恒生ETF | `0.159920` | `s_sz159920` | `hsetf` | 跨境QDII |
| **美股科技** | `513100` | 纳斯达克100ETF | `1.513100` | `s_sh513100` | `nsdketf` | 跨境QDII |
| **美股大盘** | `513500` | 标普500ETF | `1.513500` | `s_sh513500` | `bp500etf` | 跨境QDII |
| **大宗避险** | `518880` | 黄金ETF | `1.518880` | `s_sh518880` | `hjetf` | 商品类 |
| **大宗贵金属** | `161226` | 白银LOF | `0.161226` | `s_sz161226` | `bylof` | 商品类 |
| **利率固收** | `511260` | 十年国债ETF | `1.511260` | `s_sh511260` | `sngzetf` | 纯债基准 |
| **超长久期** | `511090` | 30年国债ETF | `1.511090` | `s_sh511090` | `ssngzetf` | 纯债基准 |
| **货币现金** | `511360` | 短融ETF | `1.511360` | `s_sh511360` | `dretf` | 现金管理 |

### 4.2 侧边栏设置弹窗交互机制设计

在 `col_sb_opt` 中的 `st.popover("⚙️")` 内部实装三大核心控件：

1. **展示数量滑块**：
   ```python
   disp_limit = st.slider(
       "走廊展示数量",
       min_value=3,
       max_value=15,
       value=st.session_state.get("sb_corridor_display_limit", 6),
       step=1,
       key="sl_corridor_display_limit",
       help="控制侧边栏展示卡片的上限（3 至 15 只）"
   )
   ```
2. **全市场多选检索列表（支持按勾选顺序排列 + 拼音首字母检索）**：
   - 选项格式函数：`format_func=lambda k: f"{catalog[k]['name']} ({k}) [{catalog[k]['pinyin']}]"`；
   - 用户在 Streamlit 的 multiselect 搜索框中输入 `zzhl`、`中证`、`000922` 均可精确命中；
   - 勾选后的代码列表保持用户选择的前后顺序。
3. **任意 6 位代码实时接入输入框**：
   - 提供输入框与“添加”按钮；
   - 调用实测通过的 `validate_and_fetch_code(custom_code)` 函数，自动探针 Eastmoney/Sina 接口；
   - 探针成功后，动态把标的注入 `custom_items`，并自动勾选加入走廊前列；
   - 探针失败（如非有效 6 位代码或行情为 0）给出明确友好警告。

### 4.3 自选配置持久化文件结构与读写逻辑

文件路径定位于：`data/cache/custom_watchlist.json`。

#### JSON 结构规范
```json
{
  "version": "1.0",
  "updated_at": "2026-11-05T09:40:00",
  "display_limit": 6,
  "selected_codes": [
    "000300",
    "000688",
    "000922",
    "000905",
    "000852",
    "518880"
  ],
  "custom_items": {
    "159915": {
      "code": "159915",
      "name": "创业板ETF易方达",
      "secid": "0.159915",
      "sym": "s_sz159915",
      "pinyin": "cybetf"
    }
  }
}
```

#### 读写逻辑
- **加载 (Load)**：
  - 启动时若文件存在且非空，安全反序列化；
  - 若文件不存在，初始化默认 6 只核心指数与展示数量 6，并立刻写入磁盘创建初始配置；
- **保存 (Save)**：
  - 任何滑块调整、多选增删或代码接入，均触发原子写入（写至 `.tmp` 后替换）；
  - 同步更新 Streamlit `session_state`，确保热刷新或重启后配置不丢。

---

## 5. UI 细节修复定位 (UI Polish & Color Contrast Fixes)

### 5.1 Primary 按钮文字白色穿透修复
- **问题现状**：在某些深色模式下，Streamlit 原生 `button[kind="primary"]` 文字偶现深色或低对比度；
- **定位**：`app_gui.py` 第 965 行定义了 `button[kind="secondary"]` 的颜色，但遗漏了 `button[kind="primary"]`；
- **修复方案**：在全局样式表中追加：
  ```css
  button[kind="primary"],
  button[kind="primary"] p,
  button[kind="primary"] span {
      color: #ffffff !important;
      font-weight: 600 !important;
  }
  ```

### 5.2 Tab 1 步骤一重复摘要文案消除
- **问题现状**：`app_gui.py` 第 1839-1845 行的灰框卡片中展示了：
  ```html
  <div><b>定权模型：</b>...</div>
  <div><b>资产锚点：</b>{cur_tier_meta['core_assets']}</div>
  <div><b>权益中枢：</b>{cur_tier_meta['equity_range_str']} ｜ <b>回撤上限：</b>...</div>
  ```
  而在紧接着的第 1850 行 `st.caption` 中再次出现：
  ```python
  st.caption(f"💡 目标收益 {target_ret_input:.0f}% ➔ 当前档位：【{active_tier} {cur_tier_meta['name']}】（权益上限 {cur_tier_meta['equity_range'][1]}% ｜ 预期年化 {cur_tier_meta['target_cagr']} ｜ 核心：{cur_tier_meta['core_assets']}）")
  ```
  同一屏上下两行重复出现“资产锚点/核心”和“权益上限/权益中枢”。
- **修复方案**：
  合并为一处精炼卡片，下方 caption 精简为纯目标收益与档位确认提示：
  ```python
  st.caption(f"💡 目标年化 {target_ret_input:.0f}% ➔ 匹配投资画像【{active_tier} {cur_tier_meta['name']}】，预期年化复合增速约 {cur_tier_meta['target_cagr']}。")
  ```

---

## 6. 只读裁判文件哈希基线核实 (Referee Integrity Baseline)

执行 `py -3 scripts/verify_referee_hashes.py` 核验结果：
```
PASS: AGY2_FundAdvisory/judge_engine.py matches expected hash.
PASS: AGY2_FundAdvisory/holdout_vault.py matches expected hash.
PASS: AGY2_FundAdvisory/AGENT_SPEC.md matches expected hash.
PASS: tests/test_infra.py matches expected hash.
ALL 4 READONLY REFEREE FILES ARE INTACT AND UNMODIFIED.
```
哈希基线 100% 完好，本次只读调研零触碰、零修改裁判文件。

---

## 7. 实施建议与代码演进路径 (Recommendations for Implementers)

为后续实施人员提供清晰的代码落位指引：

1. **`portfolio_manager.py` (数据层)**：
   - 保留原 `fetch_batch_realtime_indices(use_cache=True)`，保持单元测试 `test_fetch_batch_realtime_indices()` 严格兼容；
   - 增加 `fetch_custom_realtime_indices(codes: Optional[List[str]] = None, use_cache: bool = True) -> List[Dict[str, Any]]`；
   - 接入 `data/processed/aligned_matrix_total_return.parquet` 与本地指数 parquet，在非交易时段或返回 0.00% 时动态计算前两日涨跌幅。
2. **`data_loader.py` (估值与指标计算层)**：
   - 在 `IndexValuationEngine` 中补齐 `fetch_custom_realtime_indices` 的导入与暴露；
   - 提供 `get_index_corridor_metrics(code: str, latest_pt: float) -> Dict[str, Any]` 计算 MA20、Bias20、Ret20D。
3. **`app_gui.py` (前端渲染层)**：
   - 样式表中修补 `.val-very-low, .val-very_low` 与 `.val-very-high, .val-very_high`；
   - 样式表中添加 `button[kind="primary"]` 白色文字；
   - 重构第 1350-1400 行侧边栏走廊渲染循环，输出 3 层卡片结构；
   - 在右上角 `st.popover("⚙️")` 中实装滑块、多选检索、6 位接入与 `custom_watchlist.json` 持久化；
   - 精简第 1850 行 Tab 1 步骤一提示文案。
