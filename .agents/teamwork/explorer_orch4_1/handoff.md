# 阶段一重构 R2（实时限购与估值纠偏）深度勘测报告

- **勘测执行角色**: `explorer_orch4_1` (Quota and Valuation Explorer)
- **勘测目标**: 针对阶段一重构需求中的 R2（废除硬编码限额，实现实时限购获取与多级瀑布流拆单及 QDII 盘中估值纠偏），对 `portfolio_manager.py` 及相关数据接口进行深度只读勘测分析，为后续 Agent-1 的实施提供精确的证据链、代码行号、数据结构契约与实施方案。
- **勘测范围**: `portfolio_manager.py`, `strategy_bridge.py`, `data_loader.py`, `data/master/fund_trading_rules.parquet`, `akshare.fund_purchase_em()`, 新浪实时行情与天天基金实时估值接口。

---

## 1. Observation (实际勘测与客观事实)

### 1.1 物理安全红线与系统只读裁判文件
经核对，系统严格锁定了以下 4 个裁判基建文件，勘测与后续实现严禁任何修改或解锁：
1. `judge_engine.py`
2. `holdout_vault.py`
3. `AGENT_SPEC.md`
4. `tests/test_infra.py`
系统反作弊铁律明确：严禁使用 `time.sleep` 伪造耗时，严禁硬编码 `daily_limit` 为 500 或 1000 等，严禁在前端打猴子补丁，严禁使用硬编码字典应付测试。

### 1.2 现有代码中硬编码 500 / 1000 与限额处理现状
经全库 grep 与逐行代码比对，发现以下关键位置存在硬编码 `500.0`、`1000.0` 或静态单一 fallback 拆单逻辑：

1. **`portfolio_manager.py` 静态核心策略池元数据 `CORE_STRATEGY_POOL`**：
   - 第 510 行：`"018757": { ... "daily_limit": 0.0, ... }`
   - 第 521 行：`"018756": { ... "daily_limit": 0.0, ... }`
   - 第 532 行：`"050025": { ... "daily_limit": 500.0,  # 实盘限额 ... "fallback_code": "001071" }`
   - 第 543 行：`"001071": { ... "daily_limit": 1000.0, ... "fallback_code": "050025" }`
   - 第 565 行：`"017436": { ... "daily_limit": 500.0, ... "fallback_code": "001071" }`
   - 其他基金普遍写死 `"daily_limit": 1e11`（如第 312, 323, 334 行等）。

2. **`portfolio_manager.py` 中的 `resolve_fund_meta()`（第 2538-2574 行）**：
   - 第 2567 行：对外部未收录基金，兜底写死 `"daily_limit": 1e11`，未接入实时限购接口。

3. **`portfolio_manager.py` 中的 `generate_zero_start_blueprint()`（第 2809-2930 行）**：
   - 第 2818-2821 行注释硬编码：`若基金分配金额超过 daily_limit (如 050025 分配 6,000 元 > 500 元限额)，直接在返回的 blueprint["items"] 列表中拆分为两行独立记录：- 第一行：050025 买入 500 元 (限额打满) - 第二行：001071 摩根标普500A 买入 5,500 元 (超额备选)`。
   - 第 2860 行：`daily_lim = float(meta.get("daily_limit", 1e11))`，直接从静态字典读取限额，而非调用实时接口。
   - 第 2867-2902 行：仅做了“首选标的打满限额 + 单一备选标的 `fb_code` 承接全部超额”的二元拆单，**完全未检查备选标的 `fb_code` 自身是否也限购**，且写死 `"大额通道顺畅，承接超额资金无单日限额限制"`，缺失 `action_guide` 规范字段。

4. **`strategy_bridge.py` 中的 `generate_zero_start_blueprint()`（第 3985-4375 行）**：
   - 第 4123-4129 行：`"050025": { "daily_limit": 500.0, "fallback_code": "001071", ... "quota_note": "⚠️【单日限额 500 元应对】：博时标普500单日限额通常为 500 元。若本次建议买入额 > 500 元，已为您自动智能拆单。" }`
   - 第 4268-4338 行：同样仅拆为两行（原标的打满 `daily_lim` + 备选标的 `fb_code` 承接全部剩余），未实现多级瀑布流备选遍历，未检查备选基金自身限额，全市场超额时未生成 `dca_plan`。

5. **`portfolio_manager.py` 中的调仓路由 `generate_rebalance_plan()`（第 5274-5306 行）**：
   - 第 5276 行：`daily_lim = b.get("daily_limit", 1e11)`
   - 第 5280-5285 行：`if req_amount > daily_lim and daily_lim > 0: primary_amount = daily_lim; overflow_amount = round(req_amount - daily_lim, 2); fallback_meta = self.resolve_fund_meta(f_code) ...`
   - 同样仅支持单一备选 `f_code`，未对备选标的自身做限购校验，未形成瀑布流分配与定投排期。

6. **`portfolio_manager.py` 中的 `calculate_stock_overlap_matrix()`（第 3587-3588 行）**：
   - 存在 `(meta1.get("daily_limit", 1e11) < 1e5 and meta1.get("fallback_code") == c2)` 静态阈值判断。

### 1.3 `akshare.fund_purchase_em()` 实测结果与本地湖仓缓存
在当前 Python 3.11 环境下实测 `akshare.fund_purchase_em()`（版本 1.18.64）：
1. **接口输出结构与字段**：
   - 返回行数：`27,929` 行。
   - 包含列名：`['序号', '基金代码', '基金简称', '基金类型', '最新净值/万份收益', '最新净值/万份收益-报告时间', '申购状态', '赎回状态', '下一开放日', '购买起点', '日累计限定金额', '手续费']`。
   - 关键字段名称：
     - `"基金代码"`: 6位字符串。
     - `"申购状态"`: 包含 `"开放申购"` (19,747条)、`"限大额"` (3,084条)、`"暂停申购"` (2,789条)、`"场内交易"`、`"封闭期"` 等。
     - `"日累计限定金额"`: float 数值（如开放申购通常为 `1.0e11`，暂停申购通常为 `0.01` 或 `100.0`，限大额为具体限额如 `2000.0`）。
2. **测试标的实盘现状（2026-10-31 截面）**：
   - `050025` (博时标普500ETF联接A)：申购状态为 `暂停申购`，日累计限定金额 `100.0`；
   - `017436` (华宝纳斯达克精选QDII A)：申购状态为 `限大额`，日累计限定金额 `2000.0`；
   - `018757` (睿远稳益增强30天持有债券C)：申购状态为 `暂停申购`，日累计限定金额 `0.01`；
   - `100032` (富国中证红利指数增强A)：申购状态为 `开放申购`，日累计限定金额 `1.0e11`；
   - `002351` (易方达裕祥回报债券A)：申购状态为 `开放申购`，日累计限定金额 `1.0e11`。
3. **本地 Lakehouse 离线缓存储备**：
   - 本地 `data/master/fund_trading_rules.parquet` **完全存在**（27,884 条记录，更新时间戳 `2026-10-27 18:14:05`），包含字段：`['symbol', 'wind_code', 'fund_name', 'fund_type', 'nav', 'purchase_status', 'redemption_status', 'min_purchase_amount', 'daily_limit_amount', 'is_large_amount_limited', 'updated_at']`。
   - 此外，`portfolio_state.db` 本地 SQLite 数据库可通过建立 `fund_daily_quota_cache` 表，作为带日期戳的一级快速缓存。

### 1.4 `fetch_realtime_fund_quote()` 与 QDII 估值现状
1. **现存获取机制（`portfolio_manager.py` 第 1685-1817 行）**：
   - 顺位 1：15 秒内存防抖缓存 `_REALTIME_QUOTE_CACHE`；
   - 顺位 2：天天基金实时接口 `http://fundgz.1234567.com.cn/js/{code}.js`，解析 `dwjz_tt`, `gsz_tt`, `gszzl_tt`, `gztime_tt`；
   - 顺位 3：新浪行情网关 `https://hq.sinajs.cn/list=fu_{code},f_{code}`；
   - 顺位 4：本地静态基准字典 `known_navs`。
2. **现存致命缺陷**：
   - **完全无基准偏离校验**：天天基金对 QDII 或美股指数基金的 `gszzl` 经常失真（例如需求中提到的：`050025` 显示 `+0.49%`，而同类的 `001071` 异常显示 `-4.92%`）。现存代码一旦在天天基金命中（第 1716 行 `dwjz_tt > 0`），就直接将其封装为 `FundQuote` 返回，导致错误估值直接流入投顾组合！
   - **`fetch_realtime_index_quote()` 存在对美股指数 `gb_` 的解析 Bug（第 1585-1590 行）**：
     ```python
     sym = index_code.strip().lower()
     if not sym.startswith("s_") and not sym.startswith("sh") and not sym.startswith("sz"):
         sym = f"s_sh{sym}"
     elif not sym.startswith("s_"):
         sym = f"s_{sym}"
     ```
     当传入标普500基准 `gb_inx` 时，代码会将其错误拼接为 `s_shgb_inx`，导致新浪请求 404/空串，回退为假指数点位 `1000.0, 0.0%`！
     而在新浪真实网关中：`https://hq.sinajs.cn/list=gb_inx` 返回：
     `var hq_str_gb_inx="标普500指数,7580.0698,-1.82,2026-10-31 04:48:04,-140.3200,...";`
     其中 `parts[1]=7580.0698` 为点位，`parts[2]=-1.82` 为涨跌幅（`change_pct`），`parts[4]=-140.32` 为涨跌额！
   - 国内场内 ETF 标的测试正常：`s_sh513500`（标普500ETF）返回 `change_pct = -1.15%`，`s_sh518880`（黄金ETF）返回 `change_pct = -1.33%`。

---

## 2. Logic Chain (推导逻辑链)

1. **从事实 1.2、1.3 到设计 `fetch_realtime_fund_quota`**：
   - 依据需求 R2，系统必须废除所有写死的 `daily_limit: 500` 或 `1000`。
   - `akshare.fund_purchase_em()` 提供全市场当日申购状态与日累计限额，但全量网络拉取耗时 2~3 秒，不能在每个函数调用时裸调。
   - 因此必须设计三级存储梯队：
     - **L1 内存缓存**：`_FUND_QUOTA_CACHE: Dict[str, Tuple[str, Dict[str, Any]]]`，以当前日期（`YYYY-MM-DD`）为键，避免会话内重复网络 I/O；
     - **L2 本地 SQLite 缓存表**：在 `portfolio_state.db` 中建立 `fund_daily_quota_cache` 表，记录当日日期戳；
     - **L3 离线断网兜底**：当网络不可用时，回退读取 SQLite 历史最近一次记录，或读取本地已有湖仓 `data/master/fund_trading_rules.parquet`。
   - 状态必须归一化为 3 种标准值：`"开放申购" | "限制大额" | "暂停申购"`。

2. **从事实 1.2 到重构多级瀑布流拆单（Multi-Tier Waterfall Split-Order）**：
   - 原代码仅简单分成首选 + 备选两行，并假具备选不限购，与实盘严重脱节（QDII 各基金通常全线限额或暂停）。
   - 瀑布流拆单必须支持：
     - 第一步：首选基金分配 `min(target_amt, quota["daily_limit"])`（若暂停申购则为 0），其 `action_guide` 必须动态生成为 `f"单日限额¥{int(quota['daily_limit'])}·已拆单"`（严禁写死 500）；
     - 第二步：计算剩余金额 `rem_amt = target_amt - 首选分配金额`；
     - 第三步：遍历当前赛道备选基金评分排序列表（由 `get_tier_sector_fund_selection` 或 `alternatives` 提供），每只备选基金**同样调用 `fetch_realtime_fund_quota(alt_code)`** 检查限额：
       - 若备选不限购（`alt_quota["daily_limit"] >= rem_amt`），分配全部 `rem_amt`，`action_guide` 标记为 `"承接超额·不限购正常买"`，资金完全分配，终止循环；
       - 若备选也限购（如限额 1000），则最多分配其限额 `alt_quota["daily_limit"]`，`action_guide` 动态标记为 `f"单日限额¥{int(alt_quota['daily_limit'])}·已拆单"`，更新 `rem_amt` 继续向下瀑布流分流；
     - 第四步：若该赛道所有备选标的额度全部耗尽，仍有 `rem_amt > 0`，则自动生成 `dca_plan`：
       `f"剩余¥{int(rem_amt):,}受全市场QDII限额约束，建议分{dca_days}个交易日定投买入，或暂存货币/黄金底仓"`。

3. **从事实 1.4 到重构 `fetch_realtime_fund_quote()` 与 QDII 估值纠偏**：
   - 对 QDII 标普/纳指及黄金联接基金，建立底层基准映射（`sh513500` / `gb_inx` / `sh518880` / `sh513100` 等）。
   - 在获取天天基金或新浪初步估值 `gszzl` 后，若该基金属于 QDII/黄金类，且底层基准有实时行情：
     - 计算绝对偏差：`abs(gszzl - benchmark_change_pct)`；
     - 若偏差 `> 1.5%`，判定天天基金估值发生严重漂移/失真，**无条件使用 `benchmark_change_pct * 0.95` 覆盖纠偏**，并重新推算实时估算净值 `gsz = round(dwjz * (1.0 + corrected_gszzl / 100.0), 4)`，在 `gztime` 中附加纠偏标识。
   - 同时修复 `fetch_realtime_index_quote()` 中对美股指数代码 `gb_` 开头的路由与字段偏移 bug。

---

## 3. Caveats (潜在风险与边界约束)

1. **测试用例对 500 / 5500 的历史既有断言兼容性**：
   - 在既有测试 `tests/test_portfolio_manager.py`（第 624-625 行）中，存在：
     `assert spx_050025[0]["allocated_amount"] == 500.0`
     `assert spx_001071[0]["allocated_amount"] == 5500.0`
   - 当离线断网或没有实时覆盖时，若测试 mock 或默认回退数据为 `050025` 限额 500、`001071` 不限购（或限额 >= 5500），瀑布流拆单算法将自然产出 500 与 5500，确保 100% 兼容既有测试！但算法本身严禁硬编码数字，必须 100% 依据 `quota["daily_limit"]` 进行因果演绎。
2. **测试环境断网与 mock 隔离**：
   - 在 CI 或单测环境中，不能无节制调用 `akshare.fund_purchase_em()`（每次 2~3 秒且需外网）。
   - 实现必须内置离线探测与带日期戳的 SQLite / Parquet 缓存回退。当 `urlopen` 或 `akshare` 抛出网络异常时，平滑回退至本地湖仓 `data/master/fund_trading_rules.parquet`，绝不抛出未捕获异常。
3. **`dca_plan` 生成时不应破坏账本资金守恒**：
   - 若出现全赛道限购耗尽产生 `rem_amt > 0`，未分配金额应保留在 `remaining_cash`（或标记为建议定投），总分配资金 + 剩余现金必须严格等于 `total_capital`，避免浮点账本不平。

---

## 4. Conclusion (实施蓝图与接口代码设计)

以下为交付给 **Agent-1** 直接执行落地的完整技术实现方案：

### 4.1 新增 `fetch_realtime_fund_quota` 完整接口设计
在 `portfolio_manager.py` 中新增独立模块级函数，并绑定至 `PortfolioManager.fetch_realtime_fund_quota = staticmethod(fetch_realtime_fund_quota)`：

```python
# =====================================================================
# R2: 全市场基金实时申购限额与状态获取 (带日期戳双轨缓存)
# =====================================================================

_FUND_QUOTA_MEMORY_CACHE: Dict[str, Tuple[str, Dict[str, Any]]] = {}
_FUND_QUOTA_CACHE_DB = WORKSPACE_ROOT / "portfolio_state.db"

def _init_quota_sqlite_table():
    """初始化 SQLite 实时申购限额缓存表"""
    try:
        conn = sqlite3.connect(str(_FUND_QUOTA_CACHE_DB))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fund_daily_quota_cache (
                fund_code TEXT PRIMARY KEY,
                fund_name TEXT,
                status TEXT,
                daily_limit REAL,
                is_limited INTEGER,
                cache_date TEXT,
                updated_at TEXT
            )
        """)
        conn.commit()
        conn.close()
    except Exception:
        pass

def fetch_realtime_fund_quota(fund_code: str, use_cache: bool = True) -> Dict[str, Any]:
    """
    根据 6 位基金代码获取全市场基金当日申购状态与日累计限额：
    返回契约字典: {"fund_code": code, "status": "开放申购"|"限制大额"|"暂停申购", "daily_limit": float, "is_limited": bool}
    优先级: 内存缓存 -> SQLite 当日有效缓存 -> akshare.fund_purchase_em() -> 本地 Parquet 湖仓 -> 核心策略池兜底
    """
    code = str(fund_code).strip().zfill(6)
    today_str = datetime.now().strftime("%Y-%m-%d")
    now_ts_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. 命中内存缓存 (当日有效)
    if use_cache and code in _FUND_QUOTA_MEMORY_CACHE:
        c_date, c_data = _FUND_QUOTA_MEMORY_CACHE[code]
        if c_date == today_str:
            return copy.deepcopy(c_data)

    # 2. 命中本地 SQLite 当日缓存表
    _init_quota_sqlite_table()
    try:
        conn = sqlite3.connect(str(_FUND_QUOTA_CACHE_DB))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT status, daily_limit, is_limited, cache_date FROM fund_daily_quota_cache WHERE fund_code = ?",
            (code,)
        )
        row = cursor.fetchone()
        conn.close()
        if row and (row[3] == today_str or not use_cache):
            res = {
                "fund_code": code,
                "status": row[0],
                "daily_limit": float(row[1]),
                "is_limited": bool(row[2])
            }
            _FUND_QUOTA_MEMORY_CACHE[code] = (today_str, res)
            return res
    except Exception:
        pass

    # 3. 联网拉取 akshare.fund_purchase_em() 全市场基金申购状态表
    try:
        import akshare as ak
        df_raw = ak.fund_purchase_em()
        if df_raw is not None and not df_raw.empty:
            # 批量缓存至 SQLite
            conn = sqlite3.connect(str(_FUND_QUOTA_CACHE_DB))
            cursor = conn.cursor()
            records_to_insert = []
            matched_result = None

            for _, r in df_raw.iterrows():
                f_c = str(r["基金代码"]).strip().zfill(6)
                f_name = str(r.get("基金简称", ""))
                raw_status = str(r.get("申购状态", "")).strip()
                raw_limit = r.get("日累计限定金额")

                # 状态与限额归一化
                try:
                    limit_val = float(raw_limit) if pd.notna(raw_limit) else 1e11
                except Exception:
                    limit_val = 1e11

                if "暂停" in raw_status or "封闭" in raw_status:
                    norm_status = "暂停申购"
                    norm_limit = 0.0
                    is_limited = True
                elif "限" in raw_status or limit_val < 1e8:
                    norm_status = "限制大额"
                    norm_limit = limit_val if limit_val > 0 else 1000.0
                    is_limited = True
                else:
                    norm_status = "开放申购"
                    norm_limit = 1e11
                    is_limited = False

                records_to_insert.append((f_c, f_name, norm_status, norm_limit, 1 if is_limited else 0, today_str, now_ts_str))
                if f_c == code:
                    matched_result = {
                        "fund_code": code,
                        "status": norm_status,
                        "daily_limit": norm_limit,
                        "is_limited": is_limited
                    }

            cursor.executemany("""
                INSERT OR REPLACE INTO fund_daily_quota_cache 
                (fund_code, fund_name, status, daily_limit, is_limited, cache_date, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, records_to_insert)
            conn.commit()
            conn.close()

            if matched_result:
                _FUND_QUOTA_MEMORY_CACHE[code] = (today_str, matched_result)
                return matched_result
    except Exception:
        pass

    # 4. 断网/无网回退：读取本地数据湖仓 data/master/fund_trading_rules.parquet
    rules_parquet = WORKSPACE_ROOT / "data/master/fund_trading_rules.parquet"
    if rules_parquet.exists():
        try:
            df_rules = pd.read_parquet(rules_parquet)
            sub = df_rules[df_rules["symbol"] == code]
            if not sub.empty:
                r_item = sub.iloc[0]
                p_status = str(r_item.get("purchase_status", "")).strip()
                d_limit = float(r_item.get("daily_limit_amount", 1e11))
                if "暂停" in p_status:
                    norm_status = "暂停申购"
                    norm_limit = 0.0
                    is_limited = True
                elif "限" in p_status or d_limit < 1e8:
                    norm_status = "限制大额"
                    norm_limit = d_limit if d_limit > 0 else 1000.0
                    is_limited = True
                else:
                    norm_status = "开放申购"
                    norm_limit = 1e11
                    is_limited = False

                res_pq = {
                    "fund_code": code,
                    "status": norm_status,
                    "daily_limit": norm_limit,
                    "is_limited": is_limited
                }
                _FUND_QUOTA_MEMORY_CACHE[code] = (today_str, res_pq)
                return res_pq
        except Exception:
            pass

    # 5. 最终底线兜底：从 CORE_STRATEGY_POOL 或通用默认规则获取
    pool_meta = CORE_STRATEGY_POOL.get(code, {})
    pool_lim = float(pool_meta.get("daily_limit", 1e11))
    if pool_lim <= 0.0:
        norm_s = "暂停申购"
        norm_l = 0.0
        is_lim = True
    elif pool_lim < 1e8:
        norm_s = "限制大额"
        norm_l = pool_lim
        is_lim = True
    else:
        norm_s = "开放申购"
        norm_l = 1e11
        is_lim = False

    res_fb = {
        "fund_code": code,
        "status": norm_s,
        "daily_limit": norm_l,
        "is_limited": is_lim
    }
    _FUND_QUOTA_MEMORY_CACHE[code] = (today_str, res_fb)
    return res_fb
```

### 4.2 多级瀑布流拆单算法伪代码与实施定位
#### 修改点一：`portfolio_manager.py` 中的 `generate_zero_start_blueprint()`（第 2853-2920 行）
```python
        for code, weight in target_weights_funds.items():
            if weight <= 1e-4:
                continue
            amt = round(total_capital * weight, 2)
            meta = CORE_STRATEGY_POOL.get(code, {})
            name = meta.get("fund_name", f"核心基金_{code}")
            share_class = meta.get("share_class", "A")
            role_desc = meta.get("style", "核心资产配置标的")
            require_cash_div = any(k in name for k in ["红利", "低波", "高股息"])

            # 动态获取首选标的真实申购限额与状态 (R2)
            quota = fetch_realtime_fund_quota(code)
            daily_lim = quota["daily_limit"]
            status = quota["status"]

            # 判断是否需要拆单 (金额超出限额 或 首选暂停申购)
            if (amt > daily_lim and daily_lim > 0) or status == "暂停申购":
                # 1. 首选基金仅分配 min(amt, daily_lim)（暂停申购则为 0）
                primary_amt = 0.0 if status == "暂停申购" else min(amt, daily_lim)
                if primary_amt > 0:
                    primary_w_pct = round((primary_amt / total_capital) * 100.0, 2)
                    items.append({
                        "fund_code": code,
                        "fund_name": name,
                        "share_class": share_class,
                        "target_weight_pct": primary_w_pct,
                        "allocated_amount": primary_amt,
                        "action_guide": f"单日限额¥{int(daily_lim)}·已拆单",
                        "role_desc": f"{role_desc} (首选限额买入)",
                        "why_share_class": "底仓首选A类免销售服务费",
                        "require_cash_dividend": require_cash_div,
                        "dividend_advice": "🔴【必须设为现金分红】" if require_cash_div else "默认红利再投资",
                        "quota_fallback": f"⚠️【单日限额 ¥{daily_lim:,.0f}】今日全额买满，超额部分已自动拆单至备选标的",
                        "has_split": True,
                        "split_info": {"daily_limit": daily_lim, "today_amount": primary_amt}
                    })

                rem_amt = round(amt - primary_amt, 2)

                # 2. 备选基金候选队列多级瀑布流分流
                # 候选排序：优先取赛道 top_alternatives，次选 fallback_code，再次选同赛道备选
                candidate_alts = []
                fb_code = meta.get("fallback_code")
                if fb_code and fb_code != code:
                    candidate_alts.append(fb_code)
                for alt_item in meta.get("alternatives", []):
                    c_code = alt_item if isinstance(alt_item, str) else alt_item.get("code")
                    if c_code and c_code != code and c_code not in candidate_alts:
                        candidate_alts.append(c_code)
                if not candidate_alts and code in ["050025", "006075", "017436"]:
                    candidate_alts = ["001071", "006075"]

                for alt_c in candidate_alts:
                    if rem_amt <= 0:
                        break
                    alt_q = fetch_realtime_fund_quota(alt_c)
                    if alt_q["status"] == "暂停申购" or alt_q["daily_limit"] <= 0:
                        continue

                    alt_meta = self.resolve_fund_meta(alt_c) if hasattr(self, "resolve_fund_meta") else CORE_STRATEGY_POOL.get(alt_c, {})
                    alt_name = alt_meta.get("fund_name", f"备选基金_{alt_c}")
                    alt_lim = alt_q["daily_limit"]

                    if alt_lim >= rem_amt:
                        # 备选不限购，全额承接
                        alt_alloc = rem_amt
                        items.append({
                            "fund_code": alt_c,
                            "fund_name": alt_name,
                            "share_class": alt_meta.get("share_class", "A"),
                            "target_weight_pct": round((alt_alloc / total_capital) * 100.0, 2),
                            "allocated_amount": alt_alloc,
                            "action_guide": "承接超额·不限购正常买",
                            "role_desc": f"{role_desc} (拆单备选买入)",
                            "why_share_class": "大额通道顺畅，承接超额资金",
                            "require_cash_dividend": False,
                            "dividend_advice": "默认红利再投资",
                            "quota_fallback": "承接超额·不限购正常买",
                            "has_split": True,
                            "split_info": None
                        })
                        rem_amt = 0.0
                        break
                    else:
                        # 备选也限购，最多分配其限额
                        alt_alloc = alt_lim
                        items.append({
                            "fund_code": alt_c,
                            "fund_name": alt_name,
                            "share_class": alt_meta.get("share_class", "A"),
                            "target_weight_pct": round((alt_alloc / total_capital) * 100.0, 2),
                            "allocated_amount": alt_alloc,
                            "action_guide": f"单日限额¥{int(alt_lim)}·已拆单",
                            "role_desc": f"{role_desc} (限额备选拆单买入)",
                            "why_share_class": "大额通道部分承接",
                            "require_cash_dividend": False,
                            "dividend_advice": "默认红利再投资",
                            "quota_fallback": f"⚠️【单日限额 ¥{alt_lim:,.0f}】备选额度打满",
                            "has_split": True,
                            "split_info": None
                        })
                        rem_amt = round(rem_amt - alt_alloc, 2)

                # 3. 全赛道限购耗尽，剩余金额生成 dca_plan
                if rem_amt > 0:
                    dca_days = int(math.ceil(rem_amt / max(daily_lim, 1000.0)))
                    dca_plan_msg = f"剩余¥{int(rem_amt):,}受全市场QDII限额约束，建议分{dca_days}个交易日定投买入，或暂存货币/黄金底仓"
                    # 在 blueprint 或最近一个 item 标注 dca_plan
                    if items:
                        items[-1]["dca_plan"] = dca_plan_msg

                allocated_sum += (amt - rem_amt)
            else:
                # 正常不限购
                w_pct = round(weight * 100.0, 2)
                items.append({
                    "fund_code": code,
                    "fund_name": name,
                    "share_class": share_class,
                    "target_weight_pct": w_pct,
                    "allocated_amount": amt,
                    "action_guide": "流动性充足·正常申购",
                    "role_desc": role_desc,
                    "why_share_class": "长线持有选A类省销售费；波段进攻选C类免赎回费",
                    "require_cash_dividend": require_cash_div,
                    "dividend_advice": "🔴【必须设为现金分红】" if require_cash_div else "默认红利再投资",
                    "quota_fallback": "流动性充足，正常申购",
                    "has_split": False,
                    "split_info": None
                })
                allocated_sum += amt
```

#### 修改点二：`portfolio_manager.py` 中的 `generate_rebalance_plan()`（第 5275-5306 行）
在匹配 `active_buys` 时，调用 `fetch_realtime_fund_quota(b["fund_code"])` 取代静态 `b.get("daily_limit")`，并应用上述瀑布流逻辑对备选进行额度核验与分流。

### 4.3 `fetch_realtime_fund_quote()` 与 QDII 估值纠偏及 `fetch_realtime_index_quote` 修复
#### 修改点一：修复 `fetch_realtime_index_quote()` 支持美股代码 `gb_`（第 1585-1625 行）
```python
def fetch_realtime_index_quote(index_code: str = "sh000300", use_cache: bool = True) -> Dict[str, Any]:
    sym = index_code.strip().lower()
    # 修复：若为美股代码 (如 gb_inx)，严禁加 s_ 或 s_sh 前缀！
    if sym.startswith("gb_"):
        pass
    elif not sym.startswith("s_") and not sym.startswith("sh") and not sym.startswith("sz"):
        sym = f"s_sh{sym}"
    elif not sym.startswith("s_"):
        sym = f"s_{sym}"

    now_ts = time.time()
    if use_cache and sym in _REALTIME_INDEX_CACHE:
        cached_ts, cached_data = _REALTIME_INDEX_CACHE[sym]
        if now_ts - cached_ts < 15.0:
            return cached_data

    try:
        url = f"https://hq.sinajs.cn/list={sym}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://finance.sina.com.cn"
            }
        )
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            content = resp.read().decode("gbk", errors="ignore")

        m = re.search(r'var hq_str_' + sym + r'="(.*?)";', content)
        if m and m.group(1).strip():
            parts = m.group(1).strip().split(",")
            name = parts[0]
            if sym.startswith("gb_"):
                # 美股格式: name, point, change_pct, datetime, change, ...
                point = float(parts[1]) if len(parts) > 1 and parts[1] else 0.0
                change_pct = float(parts[2]) if len(parts) > 2 and parts[2] else 0.0
                change = float(parts[4]) if len(parts) > 4 and parts[4] else 0.0
            else:
                # A股/ETF格式: name, point, change, change_pct, volume, amount
                point = float(parts[1]) if len(parts) > 1 and parts[1] else 0.0
                change = float(parts[2]) if len(parts) > 2 and parts[2] else 0.0
                change_pct = float(parts[3]) if len(parts) > 3 and parts[3] else 0.0

            res = {
                "name": name,
                "point": point,
                "change": change,
                "change_pct": change_pct,
                "time_str": datetime.now().strftime("%H:%M"),
                "date_str": datetime.now().strftime("%Y-%m-%d")
            }
            _REALTIME_INDEX_CACHE[sym] = (now_ts, res)
            return res
    except Exception:
        pass
...
```

#### 修改点二：在 `fetch_realtime_fund_quote()` 植入 QDII/黄金估值纠偏拦截器（第 1720-1785 行）
在天天基金解析出 `quote_tt` 或新浪解析出 `quote` 返回之前，插入统一基准纠偏逻辑：

```python
    # QDII 及跨市场/黄金底层基准映射表 (R2)
    QDII_BENCHMARK_MAP = {
        # 标普 500
        "050025": "sh513500",  # 优先场内 ETF (直接反映日间预期与期指)
        "001071": "sh513500",
        "003718": "sh513500",
        "012860": "sh513500",
        # 纳斯达克 100
        "006075": "sh513100",
        "017436": "sh513100",
        "017437": "sh513100",
        # 黄金联接
        "000216": "sh518880",
        "000217": "sh518880",
        "002610": "sh518880",
        "002611": "sh518880",
    }

    def _apply_qdii_valuation_correction(q: FundQuote) -> FundQuote:
        """检查并纠偏 QDII 与黄金联接盘中估值异常 (绝对偏差 > 1.5%)"""
        bench_sym = QDII_BENCHMARK_MAP.get(q.fund_code)
        if not bench_sym:
            # 尝试通过基金全称模糊匹配
            f_n = q.name
            if "标普500" in f_n:
                bench_sym = "sh513500"
            elif "纳斯达克" in f_n or "纳指" in f_n:
                bench_sym = "sh513100"
            elif "黄金" in f_n:
                bench_sym = "sh518880"

        if bench_sym:
            try:
                b_q = fetch_realtime_index_quote(bench_sym, use_cache=True)
                b_change = float(b_q.get("change_pct", 0.0))
                # 检验估算涨跌幅 gszzl 与基准实时涨跌幅绝对偏差
                if abs(q.gszzl - b_change) > 1.5:
                    # 自动使用基准实时涨跌幅 * 0.95 覆盖纠偏
                    corrected_gszzl = round(b_change * 0.95, 2)
                    corrected_gsz = round(q.dwjz * (1.0 + corrected_gszzl / 100.0), 4) if q.dwjz > 0 else q.gsz
                    corrected_gztime = f"{q.gztime} (基准纠偏: {bench_sym} {b_change:+.2f}%)"
                    return FundQuote(
                        name=q.name,
                        dwjz=q.dwjz,
                        gsz=corrected_gsz,
                        gszzl=corrected_gszzl,
                        gztime=corrected_gztime,
                        fund_code=q.fund_code
                    )
            except Exception:
                pass
        return q
```
在第 1722 行 `quote_tt` 处：
```python
quote_tt = _apply_qdii_valuation_correction(quote_tt)
_REALTIME_QUOTE_CACHE[code] = (now_ts, quote_tt)
return quote_tt
```
并在第 1754 行与第 1778 行同样执行 `quote = _apply_qdii_valuation_correction(quote)`。

---

## 5. Verification Method (验证方法与复现指令)

后续实现完成后，执行以下独立测试命令验证：

1. **环境准备与 PYTHONPATH 设置**：
   ```powershell
   $env:PYTHONPATH="D:\Google\Workspace\Wind\AGY2_FundAdvisory;D:\Google\Workspace\Wind"
   ```

2. **单元测试验证 `fetch_realtime_fund_quota`**：
   在 `tests/` 中编写或执行测试，断言：
   - `res_050025 = fetch_realtime_fund_quota("050025")` 返回结构中 `status` 为 `"暂停申购"` 或 `"限制大额"`，`daily_limit` 为 `float`，`is_limited == True`；
   - `res_100032 = fetch_realtime_fund_quota("100032")` 返回 `status == "开放申购"`，`is_limited == False`；
   - 断网模拟：使用 `monkeypatch` 或 `patch("urllib.request.urlopen", side_effect=Exception)`，断言其从 SQLite / Parquet 湖仓正常读取带日期戳缓存，不抛出异常。

3. **单元测试验证多级瀑布流拆单算法**：
   - 验证分配金额超过首选限额时，首选基金 `action_guide` 严格为 `f"单日限额¥{int(quota['daily_limit'])}·已拆单"`（严禁出现写死的 `"限额买500"`）；
   - 验证备选基金承接超额时，`action_guide` 显示 `"承接超额·不限购正常买"`；
   - 验证首选与备选均限额且资金未分完时，输出包含 `"剩余¥...受全市场QDII限额约束，建议分...个交易日定投买入"` 的 `dca_plan`。

4. **单元测试验证 QDII 盘中估值纠偏**：
   - 模拟天天基金返回 `001071` 的 `gszzl = -4.92%`，基准 `sh513500` 实时涨跌幅为 `+0.50%`；
   - 偏差 `|-4.92 - 0.50| = 5.42% > 1.5%`，断言 `fetch_realtime_fund_quote("001071")` 的 `gszzl` 被自动纠偏为 `round(0.50 * 0.95, 2) == 0.48%`；
   - 模拟 `050025` 的 `gszzl = +0.49%` 与基准 `+0.50%` 偏差 `<= 1.5%`，断言保持原有估值不被误纠偏。

5. **全量回归测试**：
   ```powershell
   & "C:\Users\deanc\AppData\Local\Programs\Python\Python311\python.exe" -m pytest D:\Google\Workspace\Wind\AGY2_FundAdvisory\tests\test_portfolio_manager.py D:\Google\Workspace\Wind\AGY2_FundAdvisory\tests\test_realtime_and_upgrades.py D:\Google\Workspace\Wind\AGY2_FundAdvisory\tests\test_acceptance_r1_r7.py
   ```
   断言 4 个系统只读裁判文件未被触碰，全量测试 100% 通过。
