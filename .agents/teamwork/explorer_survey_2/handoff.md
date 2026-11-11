# G16 世代第二阶段核心代码走查与架构探查报告 (Handoff Report)

## 1. Observation (客观实地走查与证据链)

通过对 `AGY2_FundAdvisory` 项目中核心模块 `app_gui.py`、`portfolio_manager.py`、`multi_ledger_manager.py` 以及 `advisory_engine.py` 的逐行代码走查与可复现探针实测，直接观测到以下事实：

### 1.1 `app_gui.py` 顶栏与视图控制层现状
1. **主界面顶部无全局顶栏**：
   - 在 `app_gui.py` 第 2948 行，主界面桌面模式直接以 `top_c1, top_c2, top_c3, top_c4 = st.columns(4)` 渲染 4 张指标大卡（交易时钟、市场定调、估值量能、总资产与预估），上方及左侧没有任何全局顶栏或控制条。
2. **账本切换与视图切换深藏**：
   - **视图模式切换**：目前仅存在于 `st.sidebar` 侧边栏（`app_gui.py` 第 2552~2558 行），使用 `st.radio("📱 视图模式切换", ["🖥️ 桌面专业模式", "📱 手机极简盯盘"], key="sb_view_layout_radio")`。由于应用启动时配置了 `initial_sidebar_state="collapsed"`，在窄屏或手机上侧边栏默认隐藏，用户根本找不到手机模式入口。
   - **账本切换控件**：侧边栏中**完全没有**账本切换选择器！账本切换选择器目前仅深藏在 Tab 2「持仓与调仓」底部的工具栏（`app_gui.py` 第 5010~5022 行，`col_tb_led` 内的 `st.selectbox("切换账本", ...)`）以及 Tab 1 的另存 Popover（第 4348 行）中。用户若处于首屏或手机模式，完全无法切换账本。
3. **手机极简盯盘视图现存 3 大缺陷**（`app_gui.py` 第 2828~2945 行）：
   - **缺陷 a（无导航控件与单向断头路）**：第 2828 行检测 `if st.session_state.get("app_view_layout_mode") == "📱 手机极简盯盘":` 后，第 2829 行仅渲染 `st.subheader("📱 手机极简盯盘")`，随后在第 2943 行执行 `st.stop()`。页面顶部既没有切换账本的下拉框，也没有「切回桌面专业模式」的按钮，用户进入手机模式后彻底被困，无法切换账本查看 `实战存量组合（29只·¥2.66万）`，也无法退回桌面。
   - **缺陷 b（尾盘操作指令卡片简陋，缺少五维备忘录与尾仓清扫）**：第 2850~2858 行的 `orders_brief` 仅由一个 5 行的 `for fc, h in list(pm.holdings.items()): min_days < 7` 循环构成，只要没有不满 7 天的基金，就一律显示“今日组合结构健康，维持底仓安心持仓吃息”。既没有调用 `generate_chief_advisor_memo` 注入宏观/估值/病灶等核心参谋，也没有展示当前账本的碎片尾仓（如 29 基账本中的 19 只免赎碎片尾仓合计 ¥442.70）与一键清扫归拢卡片。
   - **缺陷 c（假上传断头路）**：第 2938~2943 行代码如下：
     ```python
     st.markdown("##### 📸 手机持仓长截图一键更新")
     mob_img = st.file_uploader("上传支付宝/天天基金/招行/且慢手机长截图", type=["png", "jpg", "jpeg", "webp"], key="mob_uploader_feed")
     if mob_img:
         st.success(f"已接收截图【{mob_img.name}】，点击切换至【桌面专业模式】查看结构化切片解析与平账表。")
     st.stop()
     ```
     上传长截图后根本没有调用任何 OCR 解析函数，仅弹出一句让用户切回桌面模式的文字。而手机上传框的 key 为 `"mob_uploader_feed"`，桌面端 Tab 2 上传框的 key 为 `"pop_sc_img_uploader"`（第 5127 行），用户切回桌面后图片直接丢失，体验完全断裂。

---

### 1.2 `portfolio_manager.py` OCR 与智能文本解析链路现状
1. **函数定义与调用关系**：
   - `slice_long_screenshot_for_ocr`：定义于第 1592~1635 行，基于 PIL 实现 100% 原始宽度横向无损切片（默认高度 1000px，重叠 150px），返回 `[(slice_img, y_offset), ...]`.
   - `fuzzy_match_fund_by_name`：定义于第 1638~1768 行，提取 A/C 份额特征，支持 29 只实战存量及核心池别名映射 `ALIAS_MAP`，并具备 28,177 基金字典 Bigram + SequenceMatcher 模糊匹配。
   - `parse_screenshot_ocr_holdings`：定义于第 1770~1930 行，在第 1786 行调用 `slice_long_screenshot_for_ocr` 切片并调用 `RapidOCR`，并在第 1823 行将聚合文本传入 `parse_smart_text_holdings(aggregated_text)`。第 1832 行写道：`if len(clean_res) >= 1: return clean_res`。
   - `parse_smart_text_holdings`：定义于第 1263~1560 行。
2. **P0 级链路断层与正则截断实测证据**：
   - **断层 1：未接入 `fuzzy_match_fund_by_name`**：`parse_smart_text_holdings`（第 1373~1392 行）使用独立的硬编码 `NAME_ALIAS_MAP`（第 1281~1299 行）。例如其定义了 `"黄金ETF": "000216"`（A 类），当输入 `"华安黄金ETF联接C (395.73元)"` 时，直接命中 `"黄金ETF"`，输出错误的 A 类代码 `000216`！经实机探针测试（`test_probe.py`）：
     - `fuzzy_match_fund_by_name("华安黄金ETF联接C (395.73元)")` -> 准确返回 `{'fund_code': '000217', 'share_class': 'C'}`；
     - 但 `parse_smart_text_holdings` -> 错误返回 `{'fund_code': '000216', 'share_class': 'A'}`。
   - **断层 2：纯数字词条盲搜与昨日收益截断**：
     - 在 `parse_smart_text_holdings` 第 1384 行：`words = re.findall(r'[\u4e00-\u9fa5A-Za-z0-9]+', cleaned_line)`，遍历每个词调用 `search_funds_in_catalog(w, limit=1)`。
     - 实测命令：`search_funds_in_catalog("05")` 返回了 `005561` 和 `050025`；`search_funds_in_catalog("0")` 返回了 `100032`。
     - 当输入包含 `"昨日收益 +0.05 34.50"` 时，切词得到的纯数字 `'05'` 或 `'0'` 命中了基金库，代码随即执行 `remain_line.replace(w, " ")`，将 `+0.05` 里的数字剥除，截断成 `0.` 和 `5`，导致金额和盈亏数据彻底错乱。
     - 第 1420 行的正则清洗 `remain_line = re.sub(r'(?:昨日收益|昨日盈亏|日收益)...', ' ', remain_line)` 被错误地放在了第 1384 行的切词搜索**之后**，导致“昨日收益”包含的数字提前参与了基金匹配。

---

### 1.3 `advisory_engine.py` 成本属性写错 Bug
- 在 `advisory_engine.py` 第 4284 行：
  ```python
  cost_v = float(getattr(h, "cost_value", 0.0) or (h.get("cost_value", 0.0) if isinstance(h, dict) else 0.0))
  pl_ratio = (mv / cost_v - 1.0) if cost_v > 0 else 0.0
  ```
- `HoldingItem`（`portfolio_manager.py` 第 34~68 行）及账本 JSON 字典中，真实持仓成本属性名为 `cost_price`（成本净值）与 `cost_basis`（成本总金额），根本不存在 `cost_value`！
- 这导致 `cost_v` 永远为 `0.0`，`pl_ratio` 永远为 `0.0`，第 4288 行 `if pl_ratio < -0.10:` 永远无法触发，五维备忘录对账户中深套超 10% 的亏损标的漏检率达 100%。

---

## 2. Logic Chain (推理与逻辑链)

1. **顶栏架构统一性**：
   - 观察 1.1 显示，当前顶栏缺失，且模式切换与账本切换分散在侧边栏和 Tab 2，导致移动端和首屏存在死胡同。
   - 因此，最合理的架构是将全局紧凑控制条提升到 `app_gui.py` 第 2825 行（即侧边栏渲染结束后、手机模式分支 `if st.session_state.get("app_view_layout_mode") == ...` 之前）。
   - 这样无论是桌面端还是手机端，都能在页面最顶部获得一致的品牌标识、实时行情源指示、账本切换下拉框以及桌面/手机视图切换胶囊。
2. **手机模式真闭环设计**：
   - 观察 1.1 表明手机模式中当前长截图上传是仅含文字提示的空桩（第 2941 行）。
   - 同时观察 1.1 显示桌面端 Tab 2（第 5123~5205 行）已具备成熟的 `pm.parse_screenshot_ocr_holdings` 解析、表格预览与确认入库逻辑。
   - 因此，应将该完整链路平移至手机视图，并在手机视图下呈现紧凑预览表（含反推投入本金 `cost_basis = mv - pnl`）与「一键覆盖写入当前账本」/「追加合并」按钮，并与 Session State 状态管理深度闭环。
3. **OCR 与智能匹配链路打通**：
   - 观察 1.2 表明，`parse_screenshot_ocr_holdings` 优先调用 `parse_smart_text_holdings`，而后者因未调用 `fuzzy_match_fund_by_name` 导致 A/C 份额错乱且因纯数字搜索导致昨日收益数字截断。
   - 修复逻辑：必须在 `parse_smart_text_holdings` 行首优先剥离“昨日收益”及数值，并直接调用 `fuzzy_match_fund_by_name(cleaned_line)`，禁止对 `w.isdigit()` 的纯数字执行基金库搜索。由于 `parse_screenshot_ocr_holdings` 依赖该函数，此修复可一箭双雕同时修复文本导入与截图 OCR。

---

## 3. Caveats (限制条件与边界假设)

1. **只读保护红线**：
   - 本调查严格遵守只读契约，未修改任何项目业务代码。
   - 裁判文件 `judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py` 必须保持绝对零修改。
2. **OCR 运行环境依赖**：
   - `RapidOCR` 需要本地 `rapidocr_onnxruntime` 库及 ONNX 权重文件支持。若在无 GPU/低配机器上解析超大长截图，切片数量较多可能需要 2~4 秒执行时间，需在前端包裹 `st.spinner` 并利用 Session State 对同图哈希进行结果缓存。
3. **29 基账本幂等挂载**：
   - `multi_ledger_manager.py` 已内置 `combat_29_funds`（总市值 ¥26,615.10，投入本金 ¥27,568.50），在 `list_ledgers()` 中其 ID 为 `"combat_29_funds"`，系统已能稳定识别与切换。

---

## 4. Conclusion (重构设计与方案细则)

### 4.1 方案 A：`app_gui.py` 首屏全局顶栏与手机模式深度重构

#### 1. 全局顶栏插入位置与组件设计（插入于 `app_gui.py` 约第 2826 行）
在进入 `if st.session_state.get("app_view_layout_mode") == "📱 手机极简盯盘":` 分支前，渲染全局紧凑顶栏：
```python
# -------------------------------------------------------------
# 🌐 全局紧凑顶栏：品牌标识 + 行情源角标 + 激活账本切换 + 视图模式切换
# -------------------------------------------------------------
mlm_inst = st.session_state.get("mlm") or (MultiLedgerManager.get_instance() if MultiLedgerManager else None)
all_ledgers = mlm_inst.list_ledgers() if mlm_inst else []
avail_lids = [l["id"] for l in all_ledgers]
active_lid = st.session_state.get("active_ledger_id", "main_live")
if active_lid not in avail_lids:
    active_lid = "main_live" if "main_live" in avail_lids else (avail_lids[0] if avail_lids else "main_live")
    st.session_state.active_ledger_id = active_lid

col_top_brand, col_top_ledger, col_top_mode = st.columns([4.2, 3.8, 2.0])

with col_top_brand:
    # 品牌与行情源角标单行渲染
    safe_markdown_html(f"""
    <div style="display: flex; align-items: center; gap: 8px; padding-top: 4px;">
        <span style="font-size: 15px; font-weight: 800; color: var(--text-primary); white-space: nowrap;">🧭 AGY2 智投量化终端</span>
        <span style="font-size: 11px; padding: 2px 6px; border-radius: 4px; background: rgba(16,185,129,0.1); color: var(--color-down); border: 1px solid rgba(16,185,129,0.25); white-space: nowrap;">
            {data_src_badge} ｜ {latest_date}
        </span>
    </div>
    """)

with col_top_ledger:
    def _fmt_topbar_ledger(lid: str) -> str:
        m = mlm_inst.get_ledger_meta(lid) or {}
        tag = "🟢 [实盘]" if m.get("type") == "live" else ("🧪 [沙盒]" if m.get("type") == "sandbox" else "👨‍👩‍👧 [家庭]")
        try:
            eq = float(mlm_inst.get_pm(lid).total_equity)
        except Exception:
            eq = 0.0
        return f"{tag} {m.get('name', lid)} (¥{eq:,.0f})"

    active_idx = next((i for i, l in enumerate(all_ledgers) if l["id"] == active_lid), 0)
    selected_lid = st.selectbox(
        "当前激活账本",
        options=[l["id"] for l in all_ledgers],
        index=active_idx,
        format_func=_fmt_topbar_ledger,
        key=f"topbar_ledger_select_{active_lid}",
        label_visibility="collapsed"
    )
    if selected_lid != active_lid:
        switch_active_ledger(selected_lid)
        st.rerun()

with col_top_mode:
    # 视图模式切换胶囊
    cur_mode = st.session_state.get("app_view_layout_mode", "🖥️ 桌面专业模式")
    mode_opts = ["🖥️ 桌面专业", "📱 手机盯盘"]
    cur_idx = 0 if "桌面" in cur_mode else 1
    if hasattr(st, "segmented_control"):
        sel_mode = st.segmented_control(
            "视图模式",
            options=mode_opts,
            default=mode_opts[cur_idx],
            key="seg_topbar_view_mode",
            label_visibility="collapsed"
        )
    else:
        sel_mode = st.radio(
            "视图模式",
            options=mode_opts,
            index=cur_idx,
            horizontal=True,
            key="rad_topbar_view_mode",
            label_visibility="collapsed"
        )
    target_full_mode = "🖥️ 桌面专业模式" if "桌面" in (sel_mode or "") else "📱 手机极简盯盘"
    if target_full_mode != cur_mode:
        st.session_state.app_view_layout_mode = target_full_mode
        st.rerun()

st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
```

#### 2. 手机极简盯盘视图重构（`app_gui.py` 第 2828~2945 行）
在 `if st.session_state.get("app_view_layout_mode") == "📱 手机极简盯盘":` 分支内，构建 5 张垂直流式卡片：
1. **卡片 1：总资产与预估盈亏卡**（保留并微调间距与大字号）。
2. **卡片 2：🧭 首席投顾五维决策备忘录摘要卡**：
   - 提取 `generate_chief_advisor_memo(snapshot=snapshot, holdings=pm.holdings, ...)` 结果；
   - 渲染宏观政策、产业估值、持仓病灶及 14:30 明确行动的紧凑徽章与 1 行核心人话结论。
3. **卡片 3：🧹 碎片尾仓一键清扫卡**：
   - 检查 `pm.holdings` 中市值 `< 200.0` 且持有天数 `>= 30` 的标的；
   - 若存在（如 29 基账本命中 19 只共 ¥442.70），渲染橙色清扫提示卡与 `st.button("🧹 一键模拟/清扫碎片尾仓归拢至纯债", key="btn_mob_sweep_tails")`。
4. **卡片 4：⏱️ 14:30 尾盘关键操作指令与核心风险提醒**：
   - 结合交易时钟状态、未满 7 天锁仓保护与主动风控哨前 3 条告警，提供可一键复制的下单小抄。
5. **卡片 5：📸 手机持仓长截图真 OCR 切片解析与一键入库闭环**：
   ```python
   st.markdown("##### 📸 手机持仓长截图智能切片识别")
   mob_img = st.file_uploader("上传支付宝/天天基金/招行等长截图", type=["png", "jpg", "jpeg", "webp"], key="mob_ocr_file_uploader")
   if mob_img is not None:
       img_bytes = mob_img.getvalue()
       cache_key = f"mob_ocr_parsed_{mob_img.name}_{len(img_bytes)}"
       if cache_key not in st.session_state:
           with st.spinner("🔍 正在执行高清切片 OCR 识别与基金字典智能对齐..."):
               try:
                   parsed_ocr = pm.parse_screenshot_ocr_holdings(img_bytes)
                   st.session_state[cache_key] = parsed_ocr
                   st.session_state["shared_ocr_parsed_items"] = parsed_ocr
               except Exception as e_ocr:
                   st.error(f"截图解析异常: {e_ocr}")
                   st.session_state[cache_key] = []
       
       parsed_items = st.session_state.get(cache_key) or []
       if parsed_items:
           tot_ocr_mv = sum(float(it.get("market_value", 0.0)) for it in parsed_items)
           tot_ocr_pnl = sum(float(it.get("floating_pnl", 0.0)) for it in parsed_items)
           tot_ocr_cost = tot_ocr_mv - tot_ocr_pnl
           st.success(f"✅ 成功识别 {len(parsed_items)} 只基金！合计市值 ¥{tot_ocr_mv:,.2f} ｜ 投入本金 ¥{tot_ocr_cost:,.2f} ｜ 累计盈亏 ¥{tot_ocr_pnl:+,.2f}")
           
           df_preview = pd.DataFrame([{
               "基金代码": it.get("fund_code", ""),
               "基金名称": it.get("fund_name", ""),
               "持有市值(元)": float(it.get("market_value", 0.0)),
               "持有收益(元)": float(it.get("floating_pnl", 0.0)),
               "投入成本(元)": float(it.get("cost_basis", 0.0)),
               "份额类别": it.get("share_class", "A"),
               "持有天数": int(it.get("holding_days", 365)),
           } for it in parsed_items])
           
           edited_ocr_df = st.data_editor(df_preview, use_container_width=True, num_rows="dynamic", key="mob_ocr_editor")
           
           c_mob_act1, c_mob_act2 = st.columns(2)
           with c_mob_act1:
               if st.button("✅ 一键覆盖写入当前账本", type="primary", use_container_width=True, key="btn_mob_ocr_replace"):
                   rows = edited_ocr_df.to_dict(orient="records")
                   pm.import_from_smart_text(rows, replace_existing=True)
                   pm.save_state()
                   st.session_state.tab2_diag_cache = None
                   st.session_state.tab2_rebal_cache = None
                   st.success(f"✅ 已成功覆盖写入【{active_lid}】！")
                   st.rerun()
           with c_mob_act2:
               if st.button("➕ 追加合并写入当前账本", use_container_width=True, key="btn_mob_ocr_append"):
                   rows = edited_ocr_df.to_dict(orient="records")
                   pm.import_from_smart_text(rows, replace_existing=False)
                   pm.save_state()
                   st.session_state.tab2_diag_cache = None
                   st.session_state.tab2_rebal_cache = None
                   st.success(f"✅ 已成功追加合并至【{active_lid}】！")
                   st.rerun()
   ```

---

### 4.2 方案 B：`portfolio_manager.py` 解析主干与模糊匹配器闭环打通

1. **`parse_smart_text_holdings`（第 1360~1395 行）重构要点**：
   - **第一步：前置剔除“昨日收益”干扰**：
     在行首匹配基金代码前，先执行：
     ```python
     remain_line = re.sub(r'(?:昨日收益|昨日盈亏|日收益)\s*[+-]?\d+(?:,\d{3})*(?:\.\d+)?', ' ', cleaned_line)
     ```
   - **第二步：优先提取 6 位数字基金代码**（保留原有 `re.search(r'\b(\d{6})\b', remain_line)`）。
   - **第三步：若无 6 位代码，直接调用 `fuzzy_match_fund_by_name`**：
     彻底删除旧的 `NAME_ALIAS_MAP` 遍历与切词数字盲搜，直接调用：
     ```python
     f_match = fuzzy_match_fund_by_name(remain_line)
     if f_match and f_match.get("score", 0) >= 0.50:
         fund_code = f_match["fund_code"]
         fund_name = f_match["fund_name"]
         share_class = f_match.get("share_class", "A")
         # 从 remain_line 中安全剔除匹配到的名称与代码
         remain_line = remain_line.replace(fund_code, " ")
         if f_match.get("raw_keyword"):
             remain_line = remain_line.replace(f_match["raw_keyword"], " ")
     ```
   - **第四步：切词搜索安全防护**：
     若必须保留分词兜底，强制增加防护：
     ```python
     words = [w for w in re.findall(r'[\u4e00-\u9fa5A-Za-z0-9]+', remain_line) if not w.isdigit() and len(w) >= 2]
     ```
     彻底杜绝将 `'05'`、`'34'` 等数值误当成基金名称送入 `search_funds_in_catalog`。

2. **`parse_screenshot_ocr_holdings` 与空间块聚类优化**：
   - 经过上述对 `parse_smart_text_holdings` 的升级，`parse_screenshot_ocr_holdings` 在第 1823 行调用聚合文本解析时，将直接享有 `fuzzy_match_fund_by_name` 带来的 100% 准确别名与 A/C 份额识别能力。

---

### 4.3 方案 C：`advisory_engine.py` 修复成本属性名 Bug

在 `advisory_engine.py` 第 4284 行：
将原代码：
```python
cost_v = float(getattr(h, "cost_value", 0.0) or (h.get("cost_value", 0.0) if isinstance(h, dict) else 0.0))
pl_ratio = (mv / cost_v - 1.0) if cost_v > 0 else 0.0
```
修改为安全兼容的多字段回退逻辑：
```python
# 优先读取 cost_basis 与 cost_price
cost_v = float(
    getattr(h, "cost_basis", 0.0)
    or (getattr(h, "cost_price", 0.0) * getattr(h, "shares", 0.0))
    or (getattr(h, "cost_nav", 0.0) * getattr(h, "shares", 0.0))
    or getattr(h, "cost_value", 0.0)
    or (h.get("cost_basis", 0.0) if isinstance(h, dict) else 0.0)
    or (h.get("cost_price", 0.0) * h.get("shares", 0.0) if isinstance(h, dict) else 0.0)
)
if cost_v > 0:
    pl_ratio = (mv / cost_v - 1.0)
elif hasattr(h, "floating_pnl_pct") and getattr(h, "floating_pnl_pct") is not None:
    pl_ratio = float(getattr(h, "floating_pnl_pct", 0.0)) / 100.0
elif isinstance(h, dict) and "floating_pnl_pct" in h:
    pl_ratio = float(h.get("floating_pnl_pct", 0.0)) / 100.0
else:
    pl_ratio = 0.0
```
并在 Tab 1 传入 `holdings` 为纯权重字典时，增加 `if all(isinstance(v, float) and v <= 1.0 for v in holdings.values())` 判断，跳过存量碎片与亏损检查，杜绝报出“6只碎片合计¥1.00”的乌龙。

---

## 5. Verification Method (独立核验与验收指令)

后续实现智能体（或终审验证者）可通过以下步骤独立复现与验证：

1. **静态代码核验**：
   - 检查 `app_gui.py` 是否在第 2826 行前后新增全局顶栏（包含 `st.selectbox` 切换 `combat_29_funds` 与 `main_live`，以及 `segmented_control` 切换模式）；
   - 检查手机模式第 2939 行是否已接入 `pm.parse_screenshot_ocr_holdings` 并具备 `st.data_editor` 与入库按钮；
   - 检查 `portfolio_manager.py` 第 1373 行是否调用 `fuzzy_match_fund_by_name`，且排除 `w.isdigit()`；
   - 检查 `advisory_engine.py` 第 4284 行是否修正为 `cost_basis` / `cost_price`。

2. **自动化测试命令**：
   在工作区根目录下执行测试套件：
   ```powershell
   pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_gui_multi_ledger_stress.py -v
   ```
   并运行探针脚本验证模糊匹配与 OCR：
   ```powershell
   py -3 d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_2\test_probe.py
   ```
   断言 `"华安黄金ETF联接C"` 解析结果之 `fund_code == '000217'` 且 `share_class == 'C'`。

3. **四裁判文件零修改验证**：
   ```powershell
   git status --porcelain judge_engine.py holdout_vault.py AGENT_SPEC.md tests/test_infra.py
   ```
   输出必须严格为空，确保物理安全红线零触碰。
