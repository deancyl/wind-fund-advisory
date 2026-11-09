# Handoff Report: G14 四大代码漏洞排查与技术方案设计

**Author**: `explorer_g14_survey_1`  
**Date**: 2026-11-09T11:38:00Z  
**Target Milestone**: G14 漏洞封堵与高定机构蓝审美统一  
**Working Directory**: `d:\Google\Workspace\Wind\.agents\teamwork\explorer_g14_survey_1\`

---

## 1. Observation (直接观测事实与精准定位)

### 漏洞 1: `radar_sectors_cache.json` 读写闭环缺失与类型冲突
- **文件路径**:
  - `AGY2_FundAdvisory/advisory_engine.py` (第 1638 - 1645 行)
  - `AGY2_FundAdvisory/app_gui.py` (第 2900 - 2914 行, 第 7429 - 7444 行)
- **源码实测观测**:
  1. `OpportunityRadarEngine.scan_all_sectors` 在 `advisory_engine.py` 第 1638 行定义如下：
     ```python
     1638:     def scan_all_sectors(self, realtime_quotes: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
     1639:         """全量扫描 14 大核心赛道并降序排序"""
     1640:         results = []
     1641:         for sec_id, meta in RADAR_SECTOR_CATALOG.items():
     1642:             ev = self.evaluate_sector(sec_id, meta, realtime_quotes=realtime_quotes)
     1643:             results.append(ev)
     1644:         results.sort(key=lambda x: x["total_score"], reverse=True)
     1645:         return results
     ```
     **问题**: 入口处完全没有检查 `radar_sectors_cache.json`，且执行完毕后也未将 `results` 写入磁盘文件；不支持 `force_refresh` 参数。
  2. `app_gui.py` 第 2900 - 2907 行：
     ```python
     2900:         radar_cache_f = Path(WORKSPACE_ROOT) / "data" / "cache" / "radar_sectors_cache.json"
     2901:         all_scanned_sectors = []
     2902:         if radar_cache_f.exists():
     2903:             try:
     2904:                 with open(radar_cache_f, "r", encoding="utf-8") as _rf:
     2905:                     all_scanned_sectors = json.load(_rf)
     2906:             except Exception:
     2907:                 pass
     ```
     **问题**: 这里直接假定 `json.load(_rf)` 返回 `list`。若落盘格式为带时间戳字典 `{"timestamp": ..., "sectors": [...]}`，`all_scanned_sectors` 将成为 `dict`，在第 2915 行执行 `[s for s in all_scanned_sectors if s.get(...)]` 时会抛出 `AttributeError: 'str' object has no attribute 'get'`。
  3. `app_gui.py` 第 7429 - 7436 行：
     ```python
     7429:         radar_cache_file = Path(WORKSPACE_ROOT) / "data" / "cache" / "radar_sectors_cache.json"
     7430:         sectors_data = []
     7431:         if radar_cache_file.exists():
     7432:             try:
     7433:                 with open(radar_cache_file, "r", encoding="utf-8") as f:
     7434:                     c_json = json.load(f)
     7435:                     sectors_data = c_json.get("sectors", [])
     7436:             except Exception:
     7437:                 pass
     ```
     **问题**: 这里反过来假定 `c_json` 必须是 `dict` 并调用 `.get("sectors")`。如果当前磁盘上的 `radar_sectors_cache.json` 是 `list`（当前磁盘正是 `list`），则触发 `AttributeError: 'list' object has no attribute 'get'`，导致 `except` 静默捕获后 `sectors_data` 为空，第 7442 行被迫现场同步实例化 `OpportunityRadarEngine().scan_all_sectors()` 读取十余个 Parquet 文件！

---

### 漏洞 2: 十二维主动风控巡检被阉割与信源徽章悬空未渲染
- **文件路径**:
  - `AGY2_FundAdvisory/app_gui.py` (第 2840 - 2876 行, 第 2954 - 2966 行, 第 3011 - 3070 行)
  - `AGY2_FundAdvisory/advisory_engine.py` (第 2037 - 3035 行)
- **源码实测观测**:
  1. `app_gui.py` 第 2840 - 2854 行仅通过原生 Python 循环检查 `h_days < 7` (lock_funds) 与 `C类满30天` (c_free_funds)：
     ```python
     2840:         lock_funds = []
     2841:         c_free_funds = []
     2842:         for c, h in pm_instance.holdings.items():
     ...
     2850:             if h_days < 7:
     2851:                 lock_funds.append({"fund_code": c, ...})
     2852:             elif str(getattr(h, "share_class", "A")).upper() == "C" and h_days >= 30:
     2853:                 c_free_funds.append({"fund_code": c, ...})
     ```
  2. `app_gui.py` 第 3022 - 3028 行直接判定：
     ```python
     3022:                 if not lock_funds and not c_free_funds and len(pm_instance.holdings) > 0:
     3023:                     safe_markdown_html("""
     3024:                     <div class="decision-card" style="border-left: 3px solid var(--color-down); padding: 8px 12px; margin-bottom: 4px;">
     3025:                         <div style="font-weight: 700; color: var(--color-down); font-size: 12px; margin-bottom: 2px;">🟢 主动风控巡检全通</div>
     3026:                         <div style="font-size: 11px; color: var(--text-secondary);">持仓批次无惩罚锁仓 ｜ 赛道无超买拥挤 ｜ 零迷你基清盘风险</div>
     3027:                     </div>
     3028:                     """)
     ```
     **严重缺陷**: 只要没有未满 7 天标的且没有 C 类满 30 天标的，界面立即武断汇报 `🟢 主动风控巡检全通`！然而 `ActiveRiskSentry` 中精心构建的 10 大核心风控维度（右侧破位锁利、高水位移动止盈、超买拥挤 Bias20>6%、深套诊断、赛道与管理人集中度 >35%、迷你基 <0.5 亿、投资者适当性越界、盘中异动安全垫传导、期权 IV 暴跌对冲哨、跨境 QDII 锁汇套利）在 UI 上被彻底架空，处于 100% 失明状态！
  3. `app_gui.py` 第 2954 - 2966 行计算了 `news_source_badge`（包含东方财富 7x24 实时快讯 / 离线快照指示），但在此行之后，第 2970 行直接进入 `cols_top3 = st.columns(3)`，变量 `news_source_badge` 从未被 `safe_markdown_html` 渲染，属于死代码。
  4. 当前双翼看板中缺少「刷新雷达与风控」的显式触发按钮。

---

### 漏洞 3: `get_60d_rolling_nav_and_trajectory` 动态因子选股被写死且漏扣换手费
- **文件路径**:
  - `AGY2_FundAdvisory/advisory_engine.py` (第 892 - 975 行，核心在 932 - 935 行)
- **源码实测观测**:
  ```python
  926:             for d in range(step):
  927:                 day_idx = train_end + d
  928:                 p_prev = price_matrix[day_idx - 1, :]
  929:                 p_curr = price_matrix[day_idx, :]
  930:                 r_day = (p_curr - p_prev) / np.maximum(1e-8, p_prev)
  931: 
  932:                 # 动态策略（Top 3加权）与静态策略（全市场等权）
  933:                 oos_dynamic_returns.append(float(np.mean(r_day[:3])))
  934:                 oos_static_returns.append(float(np.mean(r_day)))
  ```
  **严重缺陷**:
  1. 第 933 行的动态策略收益率竟然是 `np.mean(r_day[:3])`！它既没有使用切片遗传算法演化出的 `w_opt`，也没有根据多因子打分挑选最优 Top 3 赛道，而是永远机械抓取 `RADAR_SECTOR_CATALOG` 字典中前 3 个赛道（白酒、医药、银行）的固定均值！
  2. 第 934 行静态基准采用 `np.mean(r_day)`（全市场 14 赛道等权），而未按 Prompt 要求使用 `self.static_weights` ([0.30, 0.30, 0.25, 0.15]) 选出静态 Top 3 赛道进行对标。
  3. 动态和静态收益序列均完全漏扣了双边 20 bps 换手摩擦成本（`0.0020 * turnover_ratio`），严重违背因果律回测与反作弊铁律。

---

### 漏洞 4: 首屏残留伪交易待办预案横幅 (`latest_plan`)
- **文件路径**:
  - `AGY2_FundAdvisory/app_gui.py` (第 2767 - 2792 行)
- **源码实测观测**:
  ```python
  2767: # 盘后预案提醒
  2768: latest_plan = pm.get_latest_next_day_plan()
  2769: if latest_plan:
  2770:     with st.expander(f"📌 **您有已锁定的 {latest_plan.get('target_date')} 盯盘待办预案** (创建于 {latest_plan.get('created_at')})", expanded=True):
  2771:         st.write("系统已为您锁定昨日盘后生成的调仓预案。请核对今日 14:30 盘中实时估值后一键执行：")
  2772:         col_exec_p, col_discard_p = st.columns([3, 7])
  2773:         with col_exec_p:
  2774:             if st.button("✅ 采纳并执行此待办预案", key="btn_apply_next_plan", type="primary", use_container_width=True):
  ...
  2786:         with col_discard_p:
  2787:             if st.button("🗑️ 放弃并清理此待办预案", key="btn_discard_next_plan"):
  ...
  ```
  **严重缺陷**: 该代码段位于首屏顶部 4 卡与双翼看板之间，展示了让人误解为柜台真实下单的伪交易按钮（「✅ 采纳并执行此待办预案」、「生成在途单」）。在纯投顾参谋定位下，这属于必须被彻底清除的杂质。

---

## 2. Logic Chain (严密逻辑推导与工程设计)

```
[Observation 1] scan_all_sectors 无缓存读写 + 读端类型冲突
  ├── 证据: advisory_engine.py:1638 每次全量循环; app_gui.py:2905(盲信list) vs 7435(盲信dict)
  └── 推论: 必须在 scan_all_sectors 中增加 4 小时磁盘缓存 (data/cache/radar_sectors_cache.json)，
           格式统一为 {"timestamp": float, "updated_at": str, "sectors": list}，
           同时在 app_gui.py 两处读端做 isinstance(..., (dict, list)) 兼容解析。

[Observation 2] inspect_portfolio 被阉割，仅检查 2 个条件误报全通
  ├── 证据: app_gui.py:3022 仅根据 lock_funds 与 c_free_funds 渲染全通，10维核心风控完全脱靶
  └── 推论: 必须基于持仓指纹 (holdings_hash = md5(active_tier_val + fund_code:shares:nav:min_days))
           在 st.session_state 与 data/portfolio_watchdog.json 双层缓存完整报告。
           只要持仓与风险档位不变，首屏 1ms 直读；
           展开后真实渲染 sentry_rep["alerts"]，仅当 all_passed==True 时展示全通；
           恢复 news_source_badge 渲染并增加「🔄 刷新雷达与风控」按钮。

[Observation 3] get_60d_rolling_nav_and_trajectory 写死 r_day[:3] 且未扣换手费
  ├── 证据: advisory_engine.py:933 取前 3 列，934 取全市场平均，未乘权重未扣 0.0020*turnover
  └── 推论: 严格因果律 (Causal Invariant) 要求：在第 d 日 (day_idx)，必须基于 d-1 日及以前的
           sub_p = price_matrix[:day_idx, :] 计算 14 赛道四维特征矩阵 f_vec (14, 4)；
           分别用演化权重 w_opt 和 static_weights 点乘打分挑出真实的动态 Top 3 与静态 Top 3；
           每日计算换手率 turnover = 0.5 * sum(|P_t - P_{t-1}|) 并扣除 0.0020 * turnover；
           写回 data/cache/factor_evolution_cache.json。

[Observation 4] latest_plan 伪交易横幅干扰首屏
  ├── 证据: app_gui.py:2767-2792 在顶部4卡与看板之间插入伪执行按钮
  └── 推论: 直接整段物理删除，使首屏在 4 卡、投顾参谋折叠栏、四宫格主导航之间零阻塞衔接。
```

---

## 3. Detailed Proposed Code Changes (具体修改代码方案)

### 方案 1: `advisory_engine.py` 之 `OpportunityRadarEngine.scan_all_sectors` 读写闭环

在 `OpportunityRadarEngine`（第 1638 行）进行如下替换：

```python
    def scan_all_sectors(
        self,
        realtime_quotes: Optional[Dict[str, Any]] = None,
        force_refresh: bool = False,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        全量扫描 14 大核心赛道并降序排序，支持 4 小时磁盘缓存 (radar_sectors_cache.json) 毫秒级直读。
        """
        is_force = force_refresh or kwargs.get("force", False) or kwargs.get("force_refresh", False)
        cache_path = Path(self.cache_dir) / "radar_sectors_cache.json"

        # 1. 检查磁盘缓存是否有效 (默认有效期 4 小时 = 14400 秒)
        if not is_force and cache_path.exists():
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    c_data = json.load(f)
                cached_ts = 0.0
                sectors = []
                if isinstance(c_data, dict):
                    cached_ts = float(c_data.get("timestamp", 0.0))
                    sectors = c_data.get("sectors", [])
                elif isinstance(c_data, list):
                    cached_ts = cache_path.stat().st_mtime
                    sectors = c_data

                if sectors and len(sectors) == len(RADAR_SECTOR_CATALOG) and (time.time() - cached_ts < 14400.0):
                    return sectors
            except Exception:
                pass

        # 2. 缓存失效或强制刷新时，执行全量四维量化评估
        results = []
        for sec_id, meta in RADAR_SECTOR_CATALOG.items():
            ev = self.evaluate_sector(sec_id, meta, realtime_quotes=realtime_quotes)
            results.append(ev)
        results.sort(key=lambda x: x["total_score"], reverse=True)

        # 3. 序列化写入磁盘缓存
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "timestamp": time.time(),
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "sectors": results,
            }
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        return results
```

同时在 `app_gui.py` 的两处读端（第 2900 行与第 7429 行）确保兼容解析：
```python
# 第 2900 行改造：
radar_cache_f = Path(WORKSPACE_ROOT) / "data" / "cache" / "radar_sectors_cache.json"
all_scanned_sectors = []
if radar_cache_f.exists():
    try:
        with open(radar_cache_f, "r", encoding="utf-8") as _rf:
            disk_val = json.load(_rf)
            if isinstance(disk_val, dict):
                all_scanned_sectors = disk_val.get("sectors", [])
            elif isinstance(disk_val, list):
                all_scanned_sectors = disk_val
    except Exception:
        pass
```
```python
# 第 7429 行改造：
radar_cache_file = Path(WORKSPACE_ROOT) / "data" / "cache" / "radar_sectors_cache.json"
sectors_data = []
if radar_cache_file.exists():
    try:
        with open(radar_cache_file, "r", encoding="utf-8") as f:
            c_json = json.load(f)
            if isinstance(c_json, dict):
                sectors_data = c_json.get("sectors", [])
            elif isinstance(c_json, list):
                sectors_data = c_json
    except Exception:
        pass
```

---

### 方案 2: `app_gui.py` 之十二维主动风控巡检恢复与 1ms 缓存

在 `render_dual_wing_advisory_dashboard(pm_instance, snapshot_dict)` 中：

1. **构造持仓指纹与 1ms 缓存直读**：
```python
        # ── 持仓指纹与十二维风控报告缓存检索 (耗时 < 1ms) ──
        h_tokens = []
        for c, h in sorted(pm_instance.holdings.items()):
            h_days = getattr(h, "holding_days", 30)
            batches = getattr(h, "batches", []) or []
            if batches:
                try:
                    h_days = min((b.holding_days for b in batches), default=h_days)
                except Exception:
                    pass
            shares = float(getattr(h, "shares", 0.0) or (h.get("shares", 0.0) if isinstance(h, dict) else 0.0))
            nav = float(getattr(h, "current_nav", 0.0) or getattr(h, "cost_price", 0.0) or (h.get("current_nav", 0.0) if isinstance(h, dict) else 0.0))
            h_tokens.append(f"{c}_{shares:.4f}_{nav:.4f}_{h_days}")

        active_tier_val = str(st.session_state.get("active_tier_val") or getattr(pm_instance, "risk_tier", "C3"))
        raw_hash_str = f"{active_tier_val}|" + "|".join(h_tokens)
        holdings_hash = hashlib.md5(raw_hash_str.encode("utf-8")).hexdigest()

        force_refresh_sentry = bool(st.session_state.pop("force_refresh_radar_sentry", False))
        cached_sentry_rep = None

        if not force_refresh_sentry:
            if st.session_state.get("sentry_holdings_hash") == holdings_hash and "sentry_report" in st.session_state:
                cached_sentry_rep = st.session_state["sentry_report"]
            else:
                watchdog_p = Path(WORKSPACE_ROOT) / "data" / "portfolio_watchdog.json"
                if watchdog_p.exists():
                    try:
                        with open(watchdog_p, "r", encoding="utf-8") as _wf:
                            wd_data = json.load(_wf)
                        if wd_data.get("holdings_hash") == holdings_hash:
                            cached_sentry_rep = wd_data
                            st.session_state["sentry_holdings_hash"] = holdings_hash
                            st.session_state["sentry_report"] = wd_data
                    except Exception:
                        pass

        if cached_sentry_rep is not None:
            sentry_rep = cached_sentry_rep
        else:
            sentry = ActiveRiskSentry()
            sentry_rep = sentry.inspect_portfolio(
                holdings=pm_instance.holdings,
                market_snapshot=snapshot_dict,
                investor_risk_tier=active_tier_val,
            )
            sentry_rep["holdings_hash"] = holdings_hash
            st.session_state["sentry_holdings_hash"] = holdings_hash
            st.session_state["sentry_report"] = sentry_rep
```

2. **标题与图标动态映射**：
```python
        alerts = sentry_rep.get("alerts", [])
        red_alerts = [a for a in alerts if a.get("level") == "red"]
        yellow_alerts = [a for a in alerts if a.get("level") == "yellow"]
        erp_pct = float(snapshot_dict.get("erp_percentile", 82.0))

        if len(pm_instance.holdings) == 0:
            act_status_icon = "🚀"
            expander_title = f"今日投顾参谋：宏观 ERP 处于黄金击球区 ({erp_pct:.1f}%)，建议一键启动新资建仓 ｜ 点击展开市场机会与精选赛道"
        elif red_alerts:
            act_status_icon = "🔴"
            first_title = red_alerts[0].get("title", "高危风险")
            expander_title = f"今日投顾参谋：触发 {len(red_alerts)} 项高危主动风控预警（{first_title[:24]}...）｜ 点击展开市场机会与持仓体检"
        elif yellow_alerts:
            act_status_icon = "🟡"
            first_title = yellow_alerts[0].get("title", "关注提示")
            expander_title = f"今日投顾参谋：发现 {len(yellow_alerts)} 项优化参谋提示（{first_title[:24]}...）｜ 点击展开市场机会与持仓体检"
        elif sentry_rep.get("all_passed"):
            act_status_icon = "🟢"
            expander_title = "今日投顾参谋：主动风控十二维巡检全通，持仓结构健康，安心吃息无需调仓 ｜ 点击展开市场机会与持仓体检"
        else:
            act_status_icon = "🟡"
            expander_title = f"今日投顾参谋：主动风控巡检提示（{len(alerts)}项需关注）｜ 点击展开市场机会与持仓体检"
```

3. **左翼顶部渲染 `news_source_badge` 与刷新按钮**：
```python
        col_rad_head1, col_rad_head2, col_rad_head3 = st.columns([5.2, 3.3, 1.5])
        with col_rad_head1:
            safe_markdown_html("<div style='font-size: 13px; font-weight: 700; color: var(--text-primary); margin-bottom: 2px;'>🔭 全市场机会雷达 · Top 3 机会甄选</div>")
            safe_markdown_html(f"<div style='margin-bottom: 4px;'>{news_source_badge}</div>")
        with col_rad_head2:
            with st.popover(f"🧬 因子进化: 估{w_factors[0]*100:.0f}% 动{w_factors[1]*100:.0f}% 噪{w_factors[2]*100:.0f}% 拥{w_factors[3]*100:.0f}%", use_container_width=True):
                # 原有 popover 内容保持
                ...
        with col_rad_head3:
            if st.button("🔄 刷新", key="btn_refresh_radar_sentry", help="强制重新扫描 14 赛道雷达与十二维主动风控", use_container_width=True):
                st.session_state["force_refresh_radar_sentry"] = True
                st.rerun()
```

4. **右翼真实渲染十二维巡检全部预警**：
```python
        with col_sentry:
            safe_markdown_html("<div style='font-size: 13px; font-weight: 700; color: var(--text-primary); margin-bottom: 6px;'>🚨 主动风险预警哨 · 十二维巡检</div>")

            # 动态相关性突变指示卡 (若有)
            corr_eval_res = sentry_rep.get("correlation_mutation") or {}
            if corr_eval_res.get("is_triggered") or corr_eval_res.get("is_mutation_alarm"):
                safe_markdown_html(render_correlation_mutation_card_html(corr_eval_res))

            if len(pm_instance.holdings) == 0:
                safe_markdown_html("""
                <div class="decision-card" style="border-left: 3px solid var(--accent-primary); padding: 8px 10px; margin-bottom: 4px;">
                    <div style="font-size: 12px; font-weight: 700; color: var(--accent-primary); margin-bottom: 2px;">🚀【空仓状态指引】</div>
                    <div style="font-size: 11px; color: var(--text-secondary);">当前账本尚无持仓。可在【🌱 新资建仓】快速获取 AI 智能配置全案。</div>
                </div>
                """)
            elif sentry_rep.get("all_passed"):
                safe_markdown_html("""
                <div class="decision-card" style="border-left: 3px solid var(--color-down); padding: 8px 12px; margin-bottom: 4px;">
                    <div style="font-weight: 700; color: var(--color-down); font-size: 12px; margin-bottom: 2px;">🟢 主动风控巡检全通</div>
                    <div style="font-size: 11px; color: var(--text-secondary);">持仓批次无惩罚锁仓 ｜ 赛道无超买拥挤 ｜ 零迷你基清盘风险 ｜ 集中度契约完全合规</div>
                </div>
                """)
            else:
                for a in alerts:
                    lvl = a.get("level", "yellow")
                    if lvl == "red":
                        b_col = "var(--color-up)"
                        prefix = "🔴"
                    elif lvl == "green_notice":
                        b_col = "var(--color-down)"
                        prefix = "🟢"
                    else:
                        b_col = "var(--accent-primary)"
                        prefix = "🟡"
                    safe_markdown_html(f"""
                    <div class="decision-card" style="border-left: 3px solid {b_col}; padding: 8px 10px; margin-bottom: 6px;">
                        <div style="font-size: 12px; font-weight: 700; color: {b_col}; margin-bottom: 2px;">
                            {prefix} {a.get('title', '')}
                        </div>
                        <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 2px; line-height: 1.3;">
                            {a.get('desc', '')}
                        </div>
                        <div style="font-size: 11px; color: var(--text-primary); font-weight: 600;">
                            💡 应对建议: {a.get('action', '')}
                        </div>
                    </div>
                    """)
```

---

### 方案 3: `advisory_engine.py` 之 `get_60d_rolling_nav_and_trajectory` 动态多因子选股与换手费扣除

在 `OnlineHeuristicFactorEvolver.get_60d_rolling_nav_and_trajectory`（第 892 - 975 行）中，实现真实的因果律特征计算、动态/静态权重 Top 3 挑选与 20 bps 换手扣费：

```python
        price_matrix, sector_ids, dates = self._extract_sector_price_matrix(window_days=140)
        chart_dates = dates[-60:]
        T_oos = 60
        step = 5
        num_slices = T_oos // step  # 12 个走步切片
        S_num = len(sector_ids)

        val_cache = _get_index_valuation_cache()
        base_val_pcts = np.full(S_num, 50.0, dtype=float)
        for s_idx, sid in enumerate(sector_ids):
            meta = RADAR_SECTOR_CATALOG.get(sid, {})
            cands = [meta.get("benchmark_index"), meta.get("symbol"), meta.get("index_code"), meta.get("cs_code")]
            for c in cands:
                if c and str(c) in val_cache and val_cache[str(c)].get("percentile") is not None:
                    base_val_pcts[s_idx] = float(val_cache[str(c)]["percentile"])
                    break

        oos_dynamic_returns = []
        oos_static_returns = []
        trajectory = []

        p_dyn_prev = np.zeros(S_num, dtype=float)
        p_stat_prev = np.zeros(S_num, dtype=float)
        is_first_day = True

        for s in range(num_slices):
            train_end = len(dates) - T_oos + s * step
            # 在训练集求解最优基因
            sub_evolver = OnlineHeuristicFactorEvolver(population_size=16, generations=5, random_seed=self.random_seed + s)
            sub_res = sub_evolver.evolve_factor_weights(lookback_days=min(60, train_end - 25), force_refresh=True)
            w_opt = sub_res["weights"]

            # 计算后续 5 日样本外净值走势与每日轨迹 (train_end .. train_end + step - 1)
            for d in range(step):
                day_idx = train_end + d
                p_prev = price_matrix[day_idx - 1, :]
                p_curr = price_matrix[day_idx, :]
                r_day = (p_curr - p_prev) / np.maximum(1e-8, p_prev)

                # 严格因果律：基于 day_idx - 1 日收盘历史计算 14 赛道 4 维特征
                sub_p = price_matrix[:day_idx, :]  # 长度为 day_idx，严格排斥当日
                p_c = sub_p[-1, :]
                p_20_ago = sub_p[-20, :] if len(sub_p) >= 20 else sub_p[0, :]
                ma20 = np.mean(sub_p[-20:, :], axis=0) if len(sub_p) >= 20 else p_c
                ma20_prev = np.mean(sub_p[-25:-5, :], axis=0) if len(sub_p) >= 25 else ma20

                diffs = np.abs(np.diff(sub_p[-20:, :], axis=0))
                sum_diff = np.sum(diffs, axis=0)
                er = np.clip(np.abs(p_c - p_20_ago) / np.maximum(1e-8, sum_diff), 0.1, 0.95)
                s_er = np.minimum(100.0, er * 1.6 * 100.0)

                bias_20 = ((p_c - ma20) / np.maximum(1e-8, ma20)) * 100.0
                slope_20 = ((ma20 - ma20_prev) / np.maximum(1e-8, ma20_prev)) * 50.0 * 100.0

                s_mom20 = np.zeros(S_num, dtype=float)
                for s_i in range(S_num):
                    b = bias_20[s_i]
                    sl = slope_20[s_i]
                    if b > 6.0:
                        s_mom20[s_i] = max(20.0, 75.0 - (b - 6.0) * 12.0)
                    elif b >= 0.0 and sl > 0.0:
                        s_mom20[s_i] = 75.0 + 25.0 * min(1.0, sl / 20.0)
                    elif -8.0 <= b < 0.0 and sl > 0.0:
                        s_mom20[s_i] = 70.0 + 15.0 * (1.0 - abs(b) / 8.0)
                    else:
                        s_mom20[s_i] = max(20.0, 50.0 + sl)

                s_val = np.zeros(S_num, dtype=float)
                for s_i in range(S_num):
                    p_s = sub_p[:, s_i]
                    if len(p_s) >= 60:
                        ma_long_len = min(len(p_s), 120)
                        ma_long = np.mean(p_s[-ma_long_len:])
                        ratio = p_s[-ma_long_len:] / np.maximum(1e-8, ma_long)
                        dyn_pct = float(np.mean(ratio <= ratio[-1]) * 100.0)
                        final_pct = 0.5 * base_val_pcts[s_i] + 0.5 * dyn_pct
                    else:
                        p_bias = float((p_c[s_i] - ma20[s_i]) / np.maximum(1e-8, ma20[s_i]) * 100.0)
                        final_pct = float(np.clip(base_val_pcts[s_i] + 0.5 * p_bias, 5.0, 95.0))
                    s_val[s_i] = float(np.clip(100.0 - final_pct, 10.0, 95.0))

                d_rets = np.diff(sub_p[-25:, :], axis=0) / np.maximum(1e-8, sub_p[-25:-1, :])
                vol_5 = np.std(d_rets[-5:, :], axis=0) if len(d_rets) >= 5 else np.full(S_num, 0.01)
                vol_long = np.std(d_rets, axis=0) if len(d_rets) >= 15 else np.full(S_num, 0.01)
                vol_ratio = vol_5 / np.maximum(1e-6, vol_long)
                s_crowd = np.clip(
                    91.0 - 2.2 * np.maximum(0.0, bias_20 - 1.5) - 6.0 * np.maximum(0.0, vol_ratio - 1.1) + (1.0 - er) * 3.5,
                    42.0, 96.0
                )

                f_vec = np.column_stack([s_val, s_mom20, s_er, s_crowd])  # shape (S_num, 4)

                # 1. 动态策略：w_opt 打分选取 Top 3
                scores_dyn = f_vec @ np.array(w_opt, dtype=float)
                top3_dyn = np.argsort(-scores_dyn)[:3]
                p_dyn = np.zeros(S_num, dtype=float)
                p_dyn[top3_dyn] = 1.0 / 3.0
                gross_r_dyn = float(np.sum(p_dyn * r_day))
                to_dyn = 0.0 if is_first_day else 0.5 * float(np.sum(np.abs(p_dyn - p_dyn_prev)))
                net_r_dyn = gross_r_dyn - 0.0020 * to_dyn
                oos_dynamic_returns.append(net_r_dyn)
                p_dyn_prev = p_dyn

                # 2. 静态策略：self.static_weights 打分选取 Top 3
                scores_stat = f_vec @ np.array(self.static_weights, dtype=float)
                top3_stat = np.argsort(-scores_stat)[:3]
                p_stat = np.zeros(S_num, dtype=float)
                p_stat[top3_stat] = 1.0 / 3.0
                gross_r_stat = float(np.sum(p_stat * r_day))
                to_stat = 0.0 if is_first_day else 0.5 * float(np.sum(np.abs(p_stat - p_stat_prev)))
                net_r_stat = gross_r_stat - 0.0020 * to_stat
                oos_static_returns.append(net_r_stat)
                p_stat_prev = p_stat

                is_first_day = False

                curr_date = dates[day_idx]
                trajectory.append({
                    "date": curr_date,
                    "valuation": float(w_opt[0]),
                    "momentum": float(w_opt[1]),
                    "snr": float(w_opt[2]),
                    "anti_crowding": float(w_opt[3]),
                    "weights": w_opt,
                    "regime_mode": sub_res.get("regime_mode", "平稳蓄势态"),
                    "operator_rule_expression": sub_res.get("operator_rule_expression", ""),
                })
```

---

### 方案 4: `app_gui.py` 之清除 `latest_plan` 伪交易横幅

在 `AGY2_FundAdvisory/app_gui.py` 第 2767 至 2792 行：
直接彻底删除以下整段代码：
```python
# 盘后预案提醒
latest_plan = pm.get_latest_next_day_plan()
if latest_plan:
    with st.expander(f"📌 **您有已锁定的 {latest_plan.get('target_date')} 盯盘待办预案** (创建于 {latest_plan.get('created_at')})", expanded=True):
        st.write("系统已为您锁定昨日盘后生成的调仓预案。请核对今日 14:30 盘中实时估值后一键执行：")
        col_exec_p, col_discard_p = st.columns([3, 7])
        with col_exec_p:
            if st.button("✅ 采纳并执行此待办预案", key="btn_apply_next_plan", type="primary", use_container_width=True):
                _cur_buf = float(st.session_state.get("rebalance_buffer_pct", 3.0))
                plan_obj = pm.generate_rebalance_plan(snapshot["target_weights_funds"], min_buffer_pct=_cur_buf)
                routes = plan_obj.get("routes", [])
                if routes:
                    oids = pm.submit_rebalance_orders(routes)
                    pm.clear_next_day_plans()
                    st.balloons()
                    st.success(f"已成功执行待办预案，生成在途单：{', '.join(oids)}。")
                    st.rerun()
                else:
                    st.info(f"持仓偏离度在 {_cur_buf:.1f}% 缓冲阈值内，无需额外调仓。")
        with col_discard_p:
            if st.button("🗑️ 放弃并清理此待办预案", key="btn_discard_next_plan"):
                pm.clear_next_day_plans()
                st.info("已清理待办预案。")
                st.rerun()

st.markdown(" ")
```

---

## 4. Caveats (边界考量与边缘场景)

1. **缓存一致性与跨工作区路径**:
   在 `OpportunityRadarEngine._resolve_cache_dir()` 中，确保支持 `WORKSPACE_ROOT / "data" / "cache"`，即使在单测临时目录中通过 `OpportunityRadarEngine(cache_dir=str(tmp_path))` 注入也能无损落盘与命中。
2. **`radar_sectors_cache.json` 磁盘兼容性**:
   `app_gui.py` 的两处读端必须同时支持读取历史直接存储的 `list` 与新标准 `{"timestamp": ..., "sectors": [...]}` 两种结构，确保无论用户磁盘缓存处于何种状态均 100% 免疫崩溃。
3. **`holdings_hash` 敏感度**:
   包含各持仓的 `code`、`shares`、`current_nav`、`min_days` 以及 `active_tier_val`。当用户在 Tab 1 调节风险档位（例如从 C3 切到 C4）或在 Tab 2 买入/调仓导致持仓变化时，哈希自动改变，触发实时重新巡检；当持仓无变化时，毫秒级读取，首屏绝对零卡顿。
4. **回测序列长度**:
   在 `get_60d_rolling_nav_and_trajectory` 中，由于提取 140 日行情，最长可提供 60 日样本外走步。在 `sub_p` 截取时使用 `min(len(p_s), 120)`，所有分母项包裹 `np.maximum(1e-8, ...)`，杜绝零除异常。

---

## 5. Conclusion (总结与后续交接)

本轮调查对 G14 涉及的四大代码隐蔽漏洞进行了 100% 的实证下潜与代码行级定位，形成了完整闭环技术方案：
1. **漏洞 1**: 在 `OpportunityRadarEngine.scan_all_sectors` 增加 4 小时磁盘缓存读写闭环，统一序列化结构并在 `app_gui.py` 双向兼容；
2. **漏洞 2**: 在首屏恢复调用 `ActiveRiskSentry.inspect_portfolio`，基于 `holdings_hash` 在内存与 `portfolio_watchdog.json` 实现 1ms 直读，真实呈现十二维风控报警，恢复 `news_source_badge` 并在前端提供刷新按钮；
3. **漏洞 3**: 彻底废除 `get_60d_rolling_nav_and_trajectory` 中的硬编码 `r_day[:3]`，基于 $d-1$ 日真实四维特征打分，分别通过 `w_opt` 和 `static_weights` 挑选 Top 3 并扣除 20 bps 换手摩擦成本；
4. **漏洞 4**: 彻底移除 `latest_plan` 伪交易待办预案横幅，恢复干净清爽的高定金融终端体验。

---

## 6. Verification Method (独立核验与验收指令)

后续实现与审查代理可通过以下方式进行精确验证：

1. **测试用例 1: 验证 `radar_sectors_cache.json` 真实落盘与读写闭环**:
   ```bash
   py -3 -c "from AGY2_FundAdvisory.advisory_engine import OpportunityRadarEngine; radar = OpportunityRadarEngine(); res = radar.scan_all_sectors(force_refresh=True); assert len(res) == 14; import json, pathlib; data = json.loads(pathlib.Path('data/cache/radar_sectors_cache.json').read_text(encoding='utf-8')); assert 'timestamp' in data and len(data['sectors']) == 14; print('PASS: radar_sectors_cache verified')"
   ```
2. **测试用例 2: 验证 `get_60d_rolling_nav_and_trajectory` 动态多因子权重与换手扣费**:
   ```bash
   py -3 -c "from AGY2_FundAdvisory.advisory_engine import OnlineHeuristicFactorEvolver; evo = OnlineHeuristicFactorEvolver(population_size=16, generations=5, random_seed=42); res = evo.get_60d_rolling_nav_and_trajectory(force_refresh=True); assert len(res['dates']) == 60; assert 'nav_dynamic' in res and 'nav_static' in res; print('PASS: rolling nav trajectory verified')"
   ```
3. **测试用例 3: 运行因果性与基建回归测试套件**:
   ```bash
   py -3 -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_causality_adversarial_m1.py tests/test_challenger_g13_m1.py tests/test_challenger_g13_m2_empirical.py
   ```
4. **失效条件 (Invalidation Conditions)**:
   - 若 `scan_all_sectors` 在缓存命中时仍读取底层 Parquet 文件，则判定失败；
   - 若 `sentry.inspect_portfolio` 在持仓不变时首屏耗时超过 5ms，则判定缓存未生效；
   - 若 `get_60d_rolling_nav_and_trajectory` 收益依然等于 `np.mean(r_day[:3])`，则判定打假未完成；
   - 若首屏仍然出现「✅ 采纳并执行此待办预案」按钮，则判定伪交易残留。
