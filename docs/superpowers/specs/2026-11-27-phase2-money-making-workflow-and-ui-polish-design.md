# AGY2-FundAdvisory Phase 2 设计规格书：中国场外买基「赚钱 + 守果」交互闭环与全站机构级 WebUI 视觉升级

- **日期**：2026-11-27
- **里程碑**：Phase 2（`v2.3.0`）
- **北极星原则**：在零布局混乱（不增主 Tab、不堆文字墙）前提下，打通「选好组合 → 智能分批建仓 → 14:30 尾盘速决 → 持仓移动止盈落袋 → 真实资金加权 XIRR 复盘 → 前瞻实盘验真」赚钱闭环，并全面升级全站布局、字体、配色与响应式表格质感。

---

## 1. 赚钱与守果闭环（后端复利 + 零冗余复用）

严格遵循 Dopamine Solution Ladder，优先复用现有 `trading_clock_fee.py`、`forward_audit_logger.py`、`execution_tracker.py` 与 `domain_models.py`：

1. **智能分批建仓向导（`POST /api/v1/plan/staged_entry`）**：
   - 输入：实验室已求解组合 `items`（代码、名称、权重、限购、MA20乖离、C类对应代码）、拟投本金 `total_amount`、持有周期 `horizon_months`、建仓模式（`smart_3_tranche` 稳健 3 批 40%/30%/30% 默认推荐 | `dca_4_week` 均分 4 周定投 25%×4 | `lump_sum` 一次性建仓）。
   - 核心风控逻辑：
     - 若某只基金 `bias_20 > +3.5%`（短线偏热），首笔建仓权重自动压降至 `25%`，剩余资金后移至第 2/3 批或回调触发，避免买在短线情绪高点；
     - 自动结合 `daily_limit` 标注限购拆单天数；持有 `≤12 个月` 自动附带同基金 C 类省费代码；
     - 输出一键可复制的银行/支付宝执行清单文本，并支持联动调仓台作为对齐目标。
2. **14:30 尾盘实盘速决卡（`GET /api/v1/trading/cutoff_brief`）**：
   - 复用 `TradingClock().get_market_window_status()` 输出实时北京 15:00 申赎生死线状态（盘前/盘中观察/14:30~14:55 尾盘黄金执行窗/盘后顺延）、生效成交日与当前账本 Top 3 高优先动作（触发移动止盈落袋 / C转A零费置换 / 核心补仓或减仓 / 尾仓归拢）。
3. **持仓级三阶移动止盈与守果雷达（嵌入 `GET /api/v1/holdings`）**：
   - 对每只持仓结合本地湖仓 `first_buy_date` 以来真实最高净值（缺失时安全退回成本/现价）计算 `peak_nav` 与 `drawdown_from_peak_pct`，给出 5 类明确动作信号：
     - `LOCK_PARTIAL`：浮盈 `≥ +15%` 且从阶段高点回撤 `≥ 4.5%` 且满 7 天 → **建议止盈落袋 1/3 转入中短债安全垫**；
     - `TARGET_REACHED`：浮盈 `≥ +15%` 且回撤 `< 4.5%` → **已达止盈区 · 启动 -4.5% 移动回撤追踪**；
     - `HOLD_PENALTY`：持有 `< 7 天` → **未满 7 天禁赎（避 1.5% 惩罚费）**；
     - `DEEP_VALUE_ZONE`：浮亏 `≤ -10%` → **深套勿割 · 结合定投摊低成本**；
     - `NORMAL`：稳健持有。
4. **真实交易流水与资金加权年化 XIRR（`GET/POST/DELETE /api/v1/ledger/cashflows`）**：
   - 采用牛顿迭代 + 二分法兜底精准求解实盘年化资金加权收益率 `XIRR`（解决中途加仓/定投导致简单收益率严重失真问题）；
   - 按账本独立落盘至 `<data_dir>/cashflows_<ledger_id>.json`（受 `.gitignore` 严格隔离，0 隐私外泄）；无手工流水时自动基于持仓 `batches`/`first_buy_date` 计算估算 XIRR 并明文标明来源。
5. **前瞻实盘审计透明追踪面板**：
   - 直接复用 `/api/v1/audit/trackers` 已返回的 `forward_audit` 与 `recent_logs`，在「实盘与风控 → 极端压测与影子追踪」并列呈现，让用户每日可核验系统历史推荐的真实后续表现。

---

## 2. 全站 WebUI 视觉美化与现代化标准（基于 Modern Web Guidance）

1. **配色体系（Private-Wealth Institutional Palette）**：
   - 温润瓷白画布 `#F4F7FB` + 纯白精致卡片 `#FFFFFF`（发丝线边框 `#E2E8F0` + 双层轻投影）+ 深邃海蓝主色 `#0B192C` + 克制钴蓝强调 `#1D4ED8` + 琥珀金点缀 `#D97706`；
   - A 股语义红涨（`#C81E1E`）绿跌防守（`#047857`）确保文本对比度 `≥ 4.5:1`，且任何状态均配套文字/图标标签（绝不只靠颜色区分）；
   - 采用 `color-scheme: light`、`accent-color`、`scrollbar-color`（保持可访问默认宽度）、`color-mix(in oklab, ...)` 选区高亮及 `@media (forced-colors: active)` 高对比度兜底。
2. **排版与字号层级（Typography）**：
   - 统一 CJK + 金融等宽数字字体栈（`Inter` / `PingFang SC` / `Microsoft YaHei UI` + `JetBrains Mono` / `tabular-nums`）；
   - 采用 `rem` 尺度与无单位行高（正文 `1.55`、标题 `1.3`），标题/`<th>` 启用 `text-wrap: balance`，长句段落启用 `text-wrap: pretty`，避免固定高度截断文本。
3. **布局呼吸感与零横向滚动表格（Zero-HScroll at 1440px）**：
   - **消除量化实验室矩阵表在 1440px 下的横向滚动条**：将「目标权重 + 建议金额」合并为高可读双行主列「目标配比 / 建议金额」，压缩冗余留白，使全部列在 1440px 展开左侧控制台下 100% 一屏尽览；
   - 全部核心数据表包裹 `tabIndex={0} role="region" aria-labelledby` 并配置 `@container` 窄屏响应；
   - 分批建仓向导与记一笔流水弹窗均采用原生 `<dialog>` + `showModal()` + `closedby="any"` 及指针外点降级实现。
