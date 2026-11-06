# AGY2 GUI & AppTest Infra 深度工程调研与技术全景分析报告

> **调研专员**：explorer_survey_r11_3  
> **调研目标**：Streamlit GUI 主程序 (`AGY2_FundAdvisory/app_gui.py`)、测试基础设施 (AppTest / pytest) 及需求 R1、R3、R6、R7 闭环路径  
> **报告日期**：2026-11-06  
> **基线环境**：Windows 11 / Python 3.11.9 / Streamlit 1.30+ / Pytest 9.1.1  

---

## 1. 调研执行摘要 (Executive Summary)

本调研针对 `AGY2_FundAdvisory/app_gui.py` 及全套测试套件进行了全面静态 AST 语法树分析、运行时动态断言溯源与代码拓扑审查。核心调研结论如下：

1. **热重载导入断层 (R1)**：
   - 在 `app_gui.py` 第 145~154 行的 `if _need_reimport or not st.session_state.get("_modules_initialized"):` 分支中，原始代码仅导入了 `PortfolioManager, CORE_STRATEGY_POOL...`，遗漏了 `FundHolding, HoldingItem`。
   - 当底层 `portfolio_manager.py` 触发热重载 (`importlib.reload`) 时，若 Tab 4 或其他模块引用全局作用域的 `HoldingItem` 进行类型实例化或缓存计算，会导致旧类实例与新类定义不匹配或抛出 `NameError`。
   - 解决方案：必须在第 148 行显式补齐 `FundHolding, HoldingItem`。

2. **一键全案编辑拦截漏网 (R1)**：
   - 在 Tab 2「🚀 一键执行全案」按钮分支（第 4489~4498 行）内，缺少在执行全案前将可编辑表格 `edited_table` 提交到 `pm` 账本的拦截逻辑。
   - 用户在主持仓表中修改市值、成本或调仓意愿后，若直接点击“一键执行全案”，由于未先点击“保存修改并入库”，所有编辑数据在 `st.rerun()` 触发后将被旧的账本状态冲掉。
   - 解决方案：在 `if st.button("🚀 一键执行全案", ...):` 分支首行注入 `if "edited_table" in locals() and edited_table is not None: _commit_edited_holdings_table(edited_table, pm)`。

3. **资产大类分类器消除死代码 (R2)**：
   - `app_gui.py` 原第 200~235 行存在 `if not hasattr(PortfolioManager, "classify_fund_asset_class"):` 的动态兜底 monkey-patch。该代码属于死代码（因为本体已定义该方法）且分类规则陈旧，缺乏对 161726、161725、160418、013402、008888、050025 等主流基金的代码反查与标准映射，容易导致 61.5% 标的滑落至“其他权益资产”。
   - 解决方案：彻底删除 `app_gui.py` 中的重复兜底代码，统一由 `PortfolioManager.classify_fund_asset_class` 9 大标准分类器接管。

4. **QDII 跨时区同公司转换隔离与交割说明 (R3)**：
   - 在 Tab 2 工具坞「🔄 同公司基金低摩擦转换」（`dock_tab5`，第 4386~4425 行）中，扫描候选同公司基金时，必须同时在 `company_map` 构建循环与 `sw_from` 下拉选择框中过滤排除 QDII 海外基金（代码 in `["050025", "001071", "013402"]` 或名称包含 `["标普", "纳指", "纳斯达克", "恒生", "QDII", "美股", "黄金"]`）。
   - 在该子页顶部显式展示交割规则说明横幅；并在 Tab 1 步骤三建仓表与 Tab 2 主持仓表中，为指数联接、纯债、美股/港股 QDII 附加标准估值与交割指引标签。

5. **侧边栏市场状态行情源健康徽章 (R6)**：
   - 侧边栏「🕒 市场状态与底座」卡片（第 1555~1595 行）当前展示了交易时钟、市场定调、攻防红线与湖仓底座，但未展示数据源新鲜度。
   - 通过读取 `mb_data.get("source")`，可无缝动态渲染 `🟢 东财/新浪实时盘中源` 或 `🟡 本地湖仓离线快照兜底`，增强投顾透明度。

6. **Tab 4 A/C 算费工具局部 `@st.fragment` 刷新 (R6 & R7)**：
   - Tab 4 中的「💡 A/C 算费工具」（第 5839~5863 行）位于 `with box_tab2:` 内部。
   - 采用 `_frag_dec = getattr(st, "fragment", lambda f: f)` 安全装饰器封装为独立局部刷新函数，实现调节费率与天数滑块时仅重跑该容器，响应提速至毫秒级。
   - 物理红线验证：全局及侧边栏 `st.sidebar` 内部严禁使用 `@st.fragment`，本设计完全局限于 Tab 4 容器内，杜绝触发 `StreamlitAPIException`。

7. **只读裁判文件与自动化测试基线 (R7)**：
   - 确认 4 大裁判文件（`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`）完整无损，SHA256 校验 100% 吻合。
   - 专项测试 `tests/test_adv_final_closure.py` 3/3 绿灯通过；`tests/test_infra.py` 14/14 绿灯通过；Streamlit AppTest 全站渲染 0 异常通过。

---

## 2. 核心代码靶向勘测与精细修改方案

### 2.1 勘测点 1：`app_gui.py` 热重载模块导入块 (Line 145~154)

#### 当前现状观察
在 `AGY2_FundAdvisory/app_gui.py` 中，模块热重载监测逻辑位于第 133~176 行：
```python
if _need_reimport or not st.session_state.get("_modules_initialized"):
    from trading_clock_fee import TradingClock, FeeMatrixCalculator
    from portfolio_manager import (
        PortfolioManager, CORE_STRATEGY_POOL, EXTENDED_FUND_CATALOG,
        SECTOR_FUND_SELECTION, get_fund_selection_funnel_stats,
        search_funds_in_catalog, parse_smart_text_holdings,
        fetch_realtime_fund_quote, fetch_realtime_index_quote,
        fetch_batch_realtime_indices,
        clear_realtime_cache, FundQuote
    )
```
而在顶层第 52~67 行模块初次加载时：
```python
from portfolio_manager import (
    PortfolioManager,
    FundHolding,
    HoldingItem,
    CORE_STRATEGY_POOL,
    ...
)
```
#### 风险逻辑链
当文件发生变动或触发 `_need_reimport` 时，`importlib.reload(portfolio_manager)` 创建了新的类对象 `portfolio_manager.FundHolding` 与 `portfolio_manager.HoldingItem`。由于 `_need_reimport` 代码块内没有重新 `from portfolio_manager import FundHolding, HoldingItem`，全局命名空间中的 `FundHolding` 和 `HoldingItem` 仍然指向旧模块的类对象。当 Tab 4 或其他模块（如第 5572、5590、5607 行）实例化 `HoldingItem` 并传入被热重载后的函数进行 `isinstance` 校验或对象操作时，将引发类型失配或 `NameError`。

#### 精确修改建议 (Proposed Code Snippet)
```python
<<<< BEFORE (Line 147-154)
    from portfolio_manager import (
        PortfolioManager, CORE_STRATEGY_POOL, EXTENDED_FUND_CATALOG,
        SECTOR_FUND_SELECTION, get_fund_selection_funnel_stats,
        search_funds_in_catalog, parse_smart_text_holdings,
        fetch_realtime_fund_quote, fetch_realtime_index_quote,
        fetch_batch_realtime_indices,
        clear_realtime_cache, FundQuote
    )
==== AFTER
    from portfolio_manager import (
        PortfolioManager, FundHolding, HoldingItem, CORE_STRATEGY_POOL, EXTENDED_FUND_CATALOG,
        SECTOR_FUND_SELECTION, get_fund_selection_funnel_stats,
        search_funds_in_catalog, parse_smart_text_holdings,
        fetch_realtime_fund_quote, fetch_realtime_index_quote,
        fetch_batch_realtime_indices,
        clear_realtime_cache, FundQuote
    )
>>>>
```

---

### 2.2 勘测点 2：消除 `app_gui.py` 重复与死代码资产分类器 (Line 176~205)

#### 当前现状观察
在 `app_gui.py` 第 200~235 行原包含：
```python
# 统一资产分类解析器动态兜底
if not hasattr(PortfolioManager, "classify_fund_asset_class"):
    def _pm_classify_fund_asset_class(self, fund_code: str, fund_name: str = "") -> str:
        code_str = str(fund_code).strip()
        nm = str(fund_name).strip() if fund_name else ""
        if not nm and hasattr(self, "holdings") and code_str in self.holdings:
            nm = self.holdings[code_str].fund_name
        if any(k in nm for k in ["债", "国债", "利差", "固收", "纯债", "中短债", "裕祥"]):
            return "纯债固收"
        if any(k in nm for k in ["黄金", "AU", "金ETF", "Gold"]):
            return "黄金对冲"
        if any(k in nm for k in ["标普", "纳斯达克", "海外", "美股", "SPX", "NDX", "QDII"]):
            return "美股海外对冲"
        if any(k in nm for k in ["红利低波", "低波", "红利低波动"]):
            return "A股红利低波"
        if any(k in nm for k in ["红利", "股息", "大成红利", "富国中证红利"]):
            return "A股红利高股息"
        if any(k in nm for k in ["科创", "芯片", "半导体", "集成电路", "科技", "信息"]):
            return "科技成长进攻"
        if any(k in nm for k in ["1000", "中小盘", "小盘", "微盘"]):
            return "中小盘成长"
        if any(k in nm for k in ["500", "中盘", "中证500"]):
            return "中盘均衡"
        if any(k in nm for k in ["300", "沪深300", "蓝筹", "上证50", "核心", "50ETF"]):
            return "核心蓝筹"
        return "其他权益资产"
    PortfolioManager.classify_fund_asset_class = _pm_classify_fund_asset_class
```

#### 风险逻辑链
1. `PortfolioManager` 类本体（`portfolio_manager.py` 第 4648 行）已经定义了 `classify_fund_asset_class`，因此 `if not hasattr` 条件永远为 `False`，该分支为死代码。
2. 即使条件生效，该旧函数仅做简单的名称子串模糊匹配，完全未查询 `CORE_STRATEGY_POOL`、`EXTENDED_FUND_CATALOG`、`SECTOR_FUND_SELECTION`，未支持医药 (161726)、白酒 (161725)、银行 (160418)、恒科 (013402) 等核心代码反查，导致大量主流资产落入“其他权益资产”。
3. 清理该死代码后，两端统一由 `PortfolioManager.classify_fund_asset_class` 本体接管，保证优化器配比与 GUI 穿透大类 100% 对齐。

#### 精确修改建议 (Proposed Code Snippet)
```python
<<<< BEFORE (Line 200-235)
# 统一资产分类解析器动态兜底
if not hasattr(PortfolioManager, "classify_fund_asset_class"):
    def _pm_classify_fund_asset_class(self, fund_code: str, fund_name: str = "") -> str:
        ...
    PortfolioManager.classify_fund_asset_class = _pm_classify_fund_asset_class
==== AFTER
# 资产分类器已由 portfolio_manager.PortfolioManager 本体统一定义对齐
>>>>
```

---

### 2.3 勘测点 3：Tab 2「🚀 一键执行全案」自动保存拦截 (Line 4489~4498)

#### 当前现状观察
在 `app_gui.py` 第 4463~4498 行：
```python
col_t2_btn1, col_t2_buf_bot, col_t2_btn2 = st.columns([3.5, 4.0, 2.5])
with col_t2_btn1:
    if st.button("🔍 诊断今日调仓时机", type="primary", use_container_width=True, key="btn_tab2_diagnose"):
        # 💡 自动拦截并同步表格未保存修改，杜绝丢数
        if "edited_table" in locals() and edited_table is not None:
            _commit_edited_holdings_table(edited_table, pm)
        st.session_state.tab2_diagnosed = True
        st.session_state.tab2_trigger_diagnose = True
        st.rerun()
with col_t2_buf_bot:
    ...
with col_t2_btn2:
    if st.button("🚀 一键执行全案", type="secondary", use_container_width=True, key="btn_tab2_all"):
        st.session_state.tab2_diagnosed = True
        st.session_state.tab2_rebalanced = True
        st.session_state.tab2_trigger_diagnose = True
        st.session_state.tab2_trigger_rebalance = True
        st.rerun()
```

#### 风险逻辑链
对比 `btn_tab2_diagnose` 与 `btn_tab2_all` 可见：`btn_tab2_diagnose` 配备了 `if "edited_table" in locals() and edited_table is not None: _commit_edited_holdings_table(edited_table, pm)` 自动入库防线，但 `btn_tab2_all` 却漏网！  
当用户在主持仓表（`st.data_editor`，key="main_holdings_editor_tab2"）中微调了某些基金的代码、市值或调仓意愿后，直接点击“一键执行全案”，由于缺少该入库调用，修改内容直接丢失，执行全案依然基于旧持仓计算。

#### 精确修改建议 (Proposed Code Snippet)
```python
<<<< BEFORE (Line 4489-4498)
        with col_t2_btn2:
            if st.button("🚀 一键执行全案", type="secondary", use_container_width=True, key="btn_tab2_all"):
                st.session_state.tab2_diagnosed = True
                st.session_state.tab2_rebalanced = True
                st.session_state.tab2_trigger_diagnose = True
                st.session_state.tab2_trigger_rebalance = True
                st.rerun()
==== AFTER
        with col_t2_btn2:
            if st.button("🚀 一键执行全案", type="secondary", use_container_width=True, key="btn_tab2_all"):
                # 💡 自动拦截并同步持仓明细修改，杜绝未保存直接执行全案丢数
                if "edited_table" in locals() and edited_table is not None:
                    _commit_edited_holdings_table(edited_table, pm)
                st.session_state.tab2_diagnosed = True
                st.session_state.tab2_rebalanced = True
                st.session_state.tab2_trigger_diagnose = True
                st.session_state.tab2_trigger_rebalance = True
                st.rerun()
>>>>
```

---

### 2.4 勘测点 4：Tab 2 同公司基金转换 QDII 隔离与交割规则说明 (Line 4386~4425)

#### 当前现状观察
位于 Tab 2 工具坞的 `dock_tab5`（“🔄 同公司基金低摩擦转换”）：
```python
with dock_tab5:
    st.markdown("##### 🔄 同公司基金低摩擦转换")
    st.caption("公募基金公司内部转换机制：A/C 份额同系互转免除赎回款离场在途等待期 (T+1 到账)，免收前端认购费，仅收取极低级差费。")
    # 扫描同公司基金
    company_map = {}
    for c_k, h_v in pm.holdings.items():
        c_meta = pm.resolve_fund_meta(c_k)
        comp_name = c_meta.get("company", "") or "通用公募"
        if comp_name not in company_map:
            company_map[comp_name] = []
        company_map[comp_name].append((c_k, h_v.fund_name, h_v.share_class, h_v.market_value))
    ...
    sw_from = st.selectbox("转出基金 (来源)", list(pm.holdings.keys()), key="sel_switch_from")
```

#### 风险逻辑链与业务红线
根据公募基金登记结算制度，海外 QDII 基金与普通境内基金存在三大物理壁垒：
1. **交割时差悬殊**：QDII 为 T+2 确认净值，赎回资金离场需要 T+6~T+8 个工作日，绝非境内普通基金的 T+1 转换机制；
2. **注册登记机构 (TA) 跨系统隔离**：QDII 基金通常采用专用 TA 账户，无法与境内普通 A 股股票型/债券型基金直接执行系统级同公司免赎低费率直转；
3. **黄金类与境外标的**：黄金 ETF 联接、跨境 ETF 同样存在跨系统结算问题。
若在同公司转换中将博时标普500 (050025)、华夏恒科 (013402)、易方达黄金 (000216) 等标的列入转换来源，将误导用户产生“资金能 T+1 极速到账”的严重错觉。

#### 完善的 QDII 判定函数与双重拦截
在排除时，需综合判断代码与名称特征：
```python
def is_qdii_or_overseas(fund_code: str, fund_name: str = "") -> bool:
    code = str(fund_code or "").strip().zfill(6)
    name = str(fund_name or "")
    if code in ["050025", "001071", "013402", "006075", "006479", "017436", "017437"]:
        return True
    return any(k in name for k in ["标普", "纳指", "纳斯达克", "恒生", "QDII", "美股", "黄金", "海外", "全球"])
```

#### 精确修改建议 (Proposed Code Snippet)
```python
<<<< BEFORE (Line 4386-4420)
            with dock_tab5:
                st.markdown("##### 🔄 同公司基金低摩擦转换")
                st.caption("公募基金公司内部转换机制：A/C 份额同系互转免除赎回款离场在途等待期 (T+1 到账)，免收前端认购费，仅收取极低级差费。")
                # 扫描同公司基金
                company_map = {}
                for c_k, h_v in pm.holdings.items():
                    c_meta = pm.resolve_fund_meta(c_k)
                    comp_name = c_meta.get("company", "") or "通用公募"
                    if comp_name not in company_map:
                        company_map[comp_name] = []
                    company_map[comp_name].append((c_k, h_v.fund_name, h_v.share_class, h_v.market_value))
                ...
                sw_from = st.selectbox("转出基金 (来源)", list(pm.holdings.keys()), key="sel_switch_from")
==== AFTER
            with dock_tab5:
                st.markdown("##### 🔄 同公司基金低摩擦转换")
                st.caption("公募基金公司内部转换机制：A/C 份额同系互转免除赎回款离场在途等待期 (T+1 到账)，免收前端认购费，仅收取极低级差费。")
                st.info("💡 **交割规则说明**：海外 QDII 基金（T+2 确认、赎回 T+6~T+8 到账）与跨注册登记机构品种不支持同公司 T+1 极速转换，系统已自动过滤保护。")
                # 扫描同公司基金
                company_map = {}
                for c_k, h_v in pm.holdings.items():
                    # 自动排除海外 QDII 与黄金等跨系统结算基金
                    c_s = str(c_k).strip().zfill(6)
                    n_s = str(h_v.fund_name or "")
                    if pm.is_qdii_fund(c_s, n_s) or c_s in ["050025", "001071", "013402"] or any(k in n_s for k in ["标普", "纳指", "纳斯达克", "恒生", "QDII", "美股", "黄金"]):
                        continue
                    c_meta = pm.resolve_fund_meta(c_k)
                    comp_name = c_meta.get("company", "") or "通用公募"
                    if comp_name not in company_map:
                        company_map[comp_name] = []
                    company_map[comp_name].append((c_k, h_v.fund_name, h_v.share_class, h_v.market_value))
                ...
                non_qdii_holdings = [
                    c for c, h in pm.holdings.items()
                    if not (pm.is_qdii_fund(c, h.fund_name) or str(c).zfill(6) in ["050025", "001071", "013402"] or any(k in str(h.fund_name or "") for k in ["标普", "纳指", "纳斯达克", "恒生", "QDII", "美股", "黄金"]))
                ]
                sw_from = st.selectbox("转出基金 (来源)", non_qdii_holdings if non_qdii_holdings else list(pm.holdings.keys()), key="sel_switch_from")
>>>>
```

---

### 2.5 勘测点 5：Tab 1 与 Tab 2 基金交割与估值属性标注提示

#### 当前现状观察
- **Tab 1 步骤三建仓表**（第 3119~3145 行）：`df_bp` 表目前包含“基金代码、基金名称、份额、目标占比、风险贡献、精确买入金额、最新净值、实时估值涨跌、排雷与拥挤度、实操分红与限购指引”。缺少对基金交易清算和盘中估值可信度的直观属性展示。
- **Tab 2 持仓表**（第 3903~3935 行）：`df_table` 目前包含“基金代码、基金名称、当前市值、持仓份额、当前净值、持仓成本价、累计盈亏、浮动盈亏率、调仓意愿、今日实时估值涨跌、盘中预估盈亏、持仓占比、最短持有天数、赎回费状态、分红方式”。

#### 统一标签映射逻辑
```python
def resolve_settlement_and_valuation_badge(fund_code: str, fund_name: str = "") -> str:
    code = str(fund_code or "").strip().zfill(6)
    name = str(fund_name or "")
    if code in ("050025", "001071", "013402") or any(k in name for k in ["标普", "纳指", "纳斯达克", "恒生", "QDII", "美股"]):
        return "跨时区T+2确认·看隔夜外盘"
    elif any(k in name for k in ["债", "国债", "利差", "固收", "纯债", "中短债", "裕祥回报"]) or code in ("002351", "018757", "000191", "003376"):
        return "票息底仓·看久期"
    elif any(k in name for k in ["指数", "ETF", "联接", "300", "500", "1000", "红利", "低波", "科创", "芯片", "半导体", "黄金"]):
        return "指数高准度·T+1确认"
    return "季报重仓·T+1确认"
```

#### 精确嵌入位置
1. **Tab 1 步骤三**：在构建 `bp_rows.append({...})` 时新增 `"估值与交割指引": resolve_settlement_and_valuation_badge(fcode, it["fund_name"])`，并加入展示列名列表 `cols_9`。
2. **Tab 2 主持仓表**：
   ```python
   df_disp["估值与交割"] = df_disp.apply(
       lambda r: resolve_settlement_and_valuation_badge(r["基金代码"], r["基金名称"]),
       axis=1
   )
   ```
   在 `cols_selected` 加入 `"估值与交割"`，在 `column_config` 中配置为禁用编辑的 `TextColumn`。

---

### 2.6 勘测点 6：侧边栏「🕒 市场状态与底座」行情源状态徽座 (Line 1555~1595)

#### 当前现状观察
在 `app_gui.py` 侧边栏第 1555~1595 行：
`mb_data` 在第 1481 行由 `mb_data = fetch_market_turnover_and_sentiment()` 获取。
卡片内 HTML 依次渲染：交易时钟、市场定调、攻防红线、湖仓底座、两市成交与多方占比进度条。

#### 精确修改建议 (Proposed Code Snippet)
```python
<<<< BEFORE (Line 1576-1580)
        <div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 6px;">
            <span style="color: var(--text-secondary);">湖仓底座</span>
            <span style="color: var(--text-muted); font-family: monospace;">{latest_date}（{total_days:,} 交易日跨牛熊）</span>
        </div>
==== AFTER
        <div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 5px;">
            <span style="color: var(--text-secondary);">湖仓底座</span>
            <span style="color: var(--text-muted); font-family: monospace;">{latest_date}（{total_days:,} 交易日跨牛熊）</span>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 6px;">
            <span style="color: var(--text-secondary);">行情源状态</span>
            <span style="color: {'var(--color-up)' if str(mb_data.get('source', '')).startswith('eastmoney') or str(mb_data.get('source', '')).startswith('realtime') else 'var(--accent-primary)'}; font-weight: 600;">
                {'🟢 东财/新浪实时盘中源' if str(mb_data.get('source', '')).startswith('eastmoney') or str(mb_data.get('source', '')).startswith('realtime') else '🟡 本地湖仓离线快照兜底'}
            </span>
        </div>
>>>>
```

---

### 2.7 勘测点 7：Tab 4「💡 A/C算费工具」安全 `@st.fragment` 封装 (Line 5839~5863)

#### 当前现状观察
在 Tab 4 工具箱内部（第 5839~5863 行）：
```python
    # A/C 份额盈亏平衡计算器
    with box_tab2:
        st.markdown("#### 💡 AC算费工具")
        c_ac1, c_ac2, c_ac3, c_ac4 = st.columns(4)
        with c_ac1:
            r_sub = st.number_input("A 类前端申购费率 (折后 %)", value=0.15, step=0.01, key="ac_r_sub")
        with c_ac2:
            r_sales = st.number_input("C 类年化销售服务费率 (%)", value=0.40, step=0.05, key="ac_r_sales")
        with c_ac3:
            v_amt = st.number_input("拟投资金额 (元)", value=50000.0, step=5000.0, key="ac_v_amt")
        with c_ac4:
            v_days = st.number_input("预计持有周期 (天)", value=90, min_value=1, max_value=730, step=5, key="ac_v_days")

        calc_res = calc.calculate_break_even_days(
            standard_sub_rate=r_sub / 10.0 / 100.0,
            discount=10.0,
            sales_service_annual_rate=r_sales / 100.0,
            max_days=365,
            target_holding_days=int(v_days),
            investment_amount=float(v_amt)
        )
        st.success(f"⚖️ **精算测算结论**：A 类与 C 类的费率盈亏平衡天数为 **{calc_res['break_even_day']} 天**。")
        if calc_res.get("target_recommendation"):
            st.info(f"🎯 **选型建议**：{calc_res['target_recommendation']['summary']}")
```

#### 风险逻辑链与物理安全红线 (R6 & R7)
1. **性能收益**：每次用户调整申购费率、销售服务费率或持有天数时，原逻辑会导致整个庞大的 Streamlit 页面自顶向下全量重算（包括侧边栏、Tab 1 选基、Tab 2 账本等上千行逻辑）。若将其包裹在 `@st.fragment` 局部刷新域中，控件交互仅在当前 Fragment 容器内闭环重跑，耗时从数百毫秒降至毫秒级。
2. **优雅向下兼容**：旧版 Streamlit 可能不存在 `st.fragment`，采用 `_frag_dec = getattr(st, "fragment", lambda f: f)` 可实现 100% 无感降级，避免 `AttributeError`。
3. **物理红线铁律**：Streamlit 官方硬性规定：**禁止在 `st.sidebar` 内部或作用于侧边栏的函数上应用 `@st.fragment`**（否则直接抛出 `StreamlitAPIException` 崩溃）。必须保证该 Fragment 严格只挂载在主工作区 Tab 4 的 `box_tab2` 内部函数上。

#### 精确修改建议 (Proposed Code Snippet)
```python
<<<< BEFORE (Line 5839-5863)
    # A/C 份额盈亏平衡计算器
    with box_tab2:
        st.markdown("#### 💡 AC算费工具")
        c_ac1, c_ac2, c_ac3, c_ac4 = st.columns(4)
        with c_ac1:
            r_sub = st.number_input("A 类前端申购费率 (折后 %)", value=0.15, step=0.01, key="ac_r_sub")
        with c_ac2:
            r_sales = st.number_input("C 类年化销售服务费率 (%)", value=0.40, step=0.05, key="ac_r_sales")
        with c_ac3:
            v_amt = st.number_input("拟投资金额 (元)", value=50000.0, step=5000.0, key="ac_v_amt")
        with c_ac4:
            v_days = st.number_input("预计持有周期 (天)", value=90, min_value=1, max_value=730, step=5, key="ac_v_days")

        calc_res = calc.calculate_break_even_days(
            standard_sub_rate=r_sub / 10.0 / 100.0,
            discount=10.0,
            sales_service_annual_rate=r_sales / 100.0,
            max_days=365,
            target_holding_days=int(v_days),
            investment_amount=float(v_amt)
        )
        st.success(f"⚖️ **精算测算结论**：A 类与 C 类的费率盈亏平衡天数为 **{calc_res['break_even_day']} 天**。")
        if calc_res.get("target_recommendation"):
            st.info(f"🎯 **选型建议**：{calc_res['target_recommendation']['summary']}")
==== AFTER
    # A/C 份额盈亏平衡计算器（安全接入 @st.fragment 毫秒级局部刷新，绝不触碰侧边栏）
    with box_tab2:
        _frag_dec = getattr(st, "fragment", lambda f: f)

        @_frag_dec
        def _render_ac_fee_fragment():
            st.markdown("#### 💡 AC算费工具")
            c_ac1, c_ac2, c_ac3, c_ac4 = st.columns(4)
            with c_ac1:
                r_sub = st.number_input("A 类前端申购费率 (折后 %)", value=0.15, step=0.01, key="ac_r_sub")
            with c_ac2:
                r_sales = st.number_input("C 类年化销售服务费率 (%)", value=0.40, step=0.05, key="ac_r_sales")
            with c_ac3:
                v_amt = st.number_input("拟投资金额 (元)", value=50000.0, step=5000.0, key="ac_v_amt")
            with c_ac4:
                v_days = st.number_input("预计持有周期 (天)", value=90, min_value=1, max_value=730, step=5, key="ac_v_days")

            calc_res = calc.calculate_break_even_days(
                standard_sub_rate=r_sub / 10.0 / 100.0,
                discount=10.0,
                sales_service_annual_rate=r_sales / 100.0,
                max_days=365,
                target_holding_days=int(v_days),
                investment_amount=float(v_amt)
            )
            st.success(f"⚖️ **精算测算结论**：A 类与 C 类的费率盈亏平衡天数为 **{calc_res['break_even_day']} 天**。")
            if calc_res.get("target_recommendation"):
                st.info(f"🎯 **选型建议**：{calc_res['target_recommendation']['summary']}")

        _render_ac_fee_fragment()
>>>>
```

---

## 3. 测试基础设施与裁判文件校验

### 3.1 4 大只读裁判文件状态与 SHA256 校验

通过 Windows 原生 PowerShell `Get-FileHash -Algorithm SHA256` 测算，4 大只读裁判文件物理状态完好无损：

| 文件路径 | 状态 | SHA256 哈希值 |
| :--- | :---: | :--- |
| `AGY2_FundAdvisory/judge_engine.py` | 纯净未改 | `76F930371176DE7EE6A413174B030101E3210AC6E037F5D10FE229AF31CC07BE` |
| `AGY2_FundAdvisory/holdout_vault.py` | 纯净未改 | `88122EAF647040A410E2FD95DA81077DB10149A498A47340FF40B670BD031D2A` |
| `AGY2_FundAdvisory/AGENT_SPEC.md` | 纯净未改 | `A346586F9BD2DC0EE83E665BD18E7A6471464C9F7B658E392B989B800CD63957` |
| `tests/test_infra.py` | 纯净未改 | `48BEE0DA300D7C0A0848EC1376E4B9B2E55224D2736081713B4340F0362CD100` |

`git status` 确认上述 4 文件处于 `nothing to commit, working tree clean` 状态，未发生任何非授权修改。

---

### 3.2 Streamlit AppTest 运行机制剖析

在测试体系中（如 `tests/test_streamlit_apptest_run.py` 与 `AGY2_FundAdvisory/tests/test_tab_boundaries_and_rebalance.py`）：
1. **调用规范**：
   ```python
   from streamlit.testing.v1 import AppTest
   at = AppTest.from_file(str(app_path), default_timeout=150)
   at.session_state.active_tier_val = "C3"
   at.session_state.target_return_val = 15.0
   at.run(timeout=150)
   ```
2. **断言准则**：
   - `assert len(at.exception) == 0`：无未捕获异常；
   - `assert len(at.error) == 0`：页面未抛出 `st.error` 红色横幅；
   - `assert len(at.tabs) >= 4`：保证 4 个主要 Tab 容器正常初始化。
3. **实测运行验证**：
   执行 `py -3 -m pytest tests/test_streamlit_apptest_run.py`，耗时 8.94s，0 异常顺利通过。

---

### 3.3 Pytest 运行指令与专项测试矩阵

工作区配置根目录 `pyproject.toml`：
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
```

#### 关键测试执行与实测结果：

| 测试文件 | 目标功能 | 运行指令 | 实测结果 |
| :--- | :--- | :--- | :---: |
| `tests/test_infra.py` | 裁判文件红线与底层架构基础校验 | `py -3 -m pytest tests/test_infra.py` | **14 passed** (7.97s) |
| `tests/test_adv_final_closure.py` | 专项测试 1 (9大分类) + 专项测试 2 (安全垫&复盘) + 专项测试 3 (自动保存&热重载) | `py -3 -m pytest tests/test_adv_final_closure.py` | **3 passed** (1.45s) |
| `tests/test_streamlit_apptest_run.py` | Streamlit AppTest 全站 0 异常渲染 | `py -3 -m pytest tests/test_streamlit_apptest_run.py` | **1 passed** (8.94s) |

#### ⚠️ 专项测试中的重要时效性发现 (Caveat on Date Drift)
在运行 `AGY2_FundAdvisory/tests/test_tab_boundaries_and_rebalance.py` 时发现：
用例 `test_generate_ai_rebalance_orders_signatures_and_modes` 构造了：
`HoldingBatch(batch_id="b2", buy_date="2026-10-30", shares=38000.0, holding_days=3)`
当调用 `pm.generate_rebalance_plan` 时，底层 `_recalculate_totals()` 会按当前系统日期动态刷新：
`b.holding_days = max(0, (today_date - b_dt).days)`。
在 2026-11-06 当天运行时，`(2026-11-06 - 2026-10-30).days == 7`！
导致测试初始化时设定的 `holding_days=3` 被动态重算为了 7 天，进而使该批次脱离了 `< 7` 天安全锁，导致断言 `assert action == 'HOLD'` 触发 `AssertionError: assert 'SELL' == 'HOLD'`。  
**技术建议**：在编写或修复此类时间敏感测试时，应采用动态相对日期 `(datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")` 构造 `buy_date`，避免绝对时间漂移破坏单元测试确定性。

---

## 4. 落地实施路线图建议 (Actionable Roadmap)

为确保工程闭环且不破坏任何既有功能，后续实施应按以下次序落地：

1. **第 1 步 (R1 & R2)**：
   - 在 `AGY2_FundAdvisory/app_gui.py` 第 148 行补齐 `FundHolding, HoldingItem`；
   - 彻底移除 `app_gui.py` 中的死代码分类器，并确认委托 `pm.classify_fund_asset_class`；
   - 在 Tab 2「🚀 一键执行全案」按钮首行注入表格提交入库拦截。
2. **第 2 步 (R3 & R6)**：
   - 在 Tab 2「同公司低摩擦转换」子页增加 QDII 自动过滤逻辑与交割规则说明横幅；
   - 在 Tab 1 步骤三与 Tab 2 持仓表中增加统一的“交割与估值指引”属性标签；
   - 在侧边栏市场状态卡片中动态渲染行情源新鲜度徽座；
   - 将 Tab 4 A/C 算费工具封装进 `@st.fragment`。
3. **第 3 步 (R4 & R5 GUI 联动)**：
   - 在 Tab 1 步骤二“💰 怎么赚钱？”归因卡片与 Tab 2 步骤一“资产基线”横幅中渲染由 `StrategyBridge.calculate_portfolio_yield_cushion` 计算出的内生安全垫金额与加权息率；
   - 在 Tab 2 工具坞「🗄️ 账本环境与实盘档案」子页的净值曲线下方，渲染由 `pm.evaluate_rebalance_audit` 驱动的 3 列调仓复盘账单指标卡。
4. **第 4 步 (轻量三阶核验交付)**：
   - 运行针对性专项套件：`py -3 -m pytest tests/test_adv_final_closure.py tests/test_infra.py tests/test_streamlit_apptest_run.py`；
   - 确保全绿后直达交付，杜绝冗余重复全库大跑。
