# AGY2-FundAdvisory Phase 1 设计规格书：面向中国场外买基人的「真赚钱 + 守住果实」底层止血与云端数据/门禁基座

- **日期**：2026-11-27（中国实盘复核定稿版）
- **北极星原则（第一性原理）**：**一切模型、选基与工程决策，第一目标是为在中国购买场外公募基金的投资者「赚到钱 + 守住胜利果实（控回撤、能落袋）」**；100% 面向场外开放式基金（不向买单推荐券商场内 ETF，场内 ETF 仅作市场温度辅助研究），不把系统做成脱离中国现实的学院派展示台。
- **所属里程碑**：Phase 1（`v2.2.0` 底层止血与 GitHub Actions 公共数据/门禁基座）
- **总体演进路线（方案 A · 渐进统一）**：Phase 1 打穿量化真伪与云端每日公共数据流 → Phase 2 零混乱前端赚钱闭环（分批建仓/移动止盈/14:30 速决/XIRR）→ Phase 3 Tauri 2 桌面客户端 → Phase 4 轻内核（Rust/WASM）移植统一纯本地桌面与安卓 APK。
- **工作量评级**：**项目级（Project）**。

---

## 1. 意图与背景（Why Now）

实证审计（24 组严格时间切分 Walk-Forward + 266 只真净值湖仓穿透 + 全市场 27,884 只真实交易规则核验）表明：
- AGY2 的多资产低相关配置与风控骨架确实有效（24/24 样本外正收益、平均最大回撤 `-4.85%`），但现行 `v2.1.2` 存在 **4 项 P0 级硬伤**、**4 项 P1 级短板** 及 **6 项与中国场外买基现实脱节的隐患**：
  1. **伪 OOS 数据泄露**：`portfolio_optimizer.py` 切出 `train_nav` 却未传入（实际把 100% 含未来的 `sub_nav` 传进优化器）；`goal_driven_selector.py` 对拟合完毕的组合切尾 30% 冒充 OOS，致近 1 年实亏 `-2.78%`（夏普 `-0.59`）的组合虚报 `OOS 胜率 76.1%`；净值图错把拟合区间涂紫标为 `样本外区间`。
  2. **假分散与资产错配**：A 股红利 `008163`/`501029` 因含“标普”冒充海外 QDII（默认 C3 实际 0% 真海外、54% 三重堆叠 A/H 红利贡献 `86.5%` 风险）；`2.15%` 费率油气主动 FOF `161815` 与 **4 只高波周期有色金属股票基**（`017192`/`018489`/`016707`/`004432`）混入黄金避险槽位；C5 组合 `67.2%` 单押 AI 通信与芯片。
  3. **锁定期与低利率久期雷**：湖仓混入 **10 只锁定期基金**（含中文数字 `六个月持有`/`一年持有` 及种子基 `000086`），导致 C1 稳健型 `30.2%` 资金被锁半年不能赎回；42 只纯债中 **`short_bond` 中短债 = 0 只**（在 10Y 国债 `1.59%` 的低利率下，纯押长债隐含利率反弹回撤风险）；种子池混有场内 ETF `510300`；含 21 只发起式基金未设防清盘规模线。
  4. **条件核 11.7σ 空间错配 & 宏观双脑分裂**：`winrate_engine.py` 用真实宏观向量匹配单基伪代理特征，纯债偏离 `-11.68σ`；`island_ensemble` 报 `SEVERE_BEAR` 时 `ten_dim_votes` 仍报 `+23%` 激进加仓把 C3 纯债底线砸成 `0%`，且第 7 维含硬编码 `"16,763 亿"` / `64.5%`。
  5. **中国场外 QDII 限购与 A/C 份额脱节**：全市场 139 只真非中国海外 QDII 中，场外开放且日限额 `≥1,000元` 的纯被动宽基仅 3 只（不可强凑假海外/中概互联/REITs）；湖仓全为 A 类，短持有期（`≤12个月`）或波段操作未给出省费 C 类对应代码。
  6. **规则表过时 31 天 & 国内网络现实**：`fund_trading_rules.parquet` 停留在 `2026-10-27`，且普通中国用户无代理直连 `github.com` 易超时，需要国内免代理多源回退同步。

---

## 2. 目标、非目标与反目标

### 目标（Goals）
1. **100% 场外可买、零锁定期、零假分散**：重构分类器与湖仓清洗，剔除全部场内 ETF、10 只锁定期、4 只伪黄金有色矿业股、高费油气 FOF 与迷你发起式清盘雷；补齐中短债 `short_bond` 与少量真开申高限额大厂全球 QDII；单风格权重 `≤ 35%`、单风格 PCR `≤ 45%`。
2. **真样本外核验（零数据泄露）**：修复 `train_nav` 死代码，上线真滚动 Walk-Forward 样本外核验，撤销拟合区间的误导性紫色“样本外”遮罩。
3. **条件核空间对齐 & 宏观双脑统一**：历史特征统一对齐真实宏观序列消除 `11.7σ` 错配；清除十维投票硬编码、更正“反拥挤安全分”文案、在 `compute_ten_dimension_votes` 内部落地熊市趋势-估值折减并硬保纯债底线，让“低位蓄力 + 高位守果”一致联动。
4. **拟投金额驱动的限购硬过滤 + 优雅降级 + A/C 智能省费匹配**：剔除暂停申购与超 10 日限购标的（极端市场全桶受限时优雅降级并显式拆单提示）；输出层按持有周期智能附带同基金省费 C 类对应代码（`≤12个月` 优先提示 C 类免高额赎回费）。
5. **双选基池透明可选 + 务实低利率默认预期**：保留「低费指数核心 (`index_only`)」与「全市场含主动 (`full_market`)」一键切换及紧凑利弊说明（前端首屏默认 `index_only`，后端 API 默认保留 `full_market` 向后兼容）；提供贴合当下 `1.59%` 无风险利率的务实默认目标与周期（可随时自调）。
6. **前瞻实盘审计自动落盘 + GitHub Actions 双流水线 + 国内免代理多源同步**：上线 `daily-market-data.yml`（`TZ: Asia/Shanghai`，发布 `data-latest` 与 Phase 4 紧凑 `float32` 预览包）和 `ci-quality-gate.yml`；解除 `.gitignore` 对 `fund_catalog.parquet` 与 `fund_trading_rules.parquet`（2 张纯公开表 ~2.4MB）的屏蔽；客户端同步支持国内镜像/GitHub/直连东财三级免代理回退。

### 非目标（Non-Goals）
- Phase 1 不做前端新增重交互页/弹窗（采纳建仓向导、交易流水 XIRR、持仓级移动止盈触发器、14:30 尾盘条归 Phase 2）；
- Phase 1 不做 Tauri 2 桌面打包与移动端响应式 UI 重塑 / 安卓 APK（归 Phase 3 & 4）；
- 严禁修改四大只读裁判文件（`judge_engine.py`、`holdout_vault.py`、`AGENT_SPEC.md`、`tests/test_infra.py`）与 `DataLoader.simulate_execution` 默认签名。

### 反目标（Anti-Goals）
- 严禁把任何场内 ETF（`51xxxx`/`159xxx`）推荐进场外买单；
- 严禁为了凑“海外槽位”塞入中概互联（`006327`/`164906`）、A 股标普红利（`008163`/`501029`）或冷门商业地产 REITs（`160140`/`005613`）；
- 严禁硬编码个基白名单凑测试、调宽门禁容差、伪造 OOS 或在公共包混入用户隐私数据；
- 严禁在前端左侧控制台堆砌文字墙破坏极简布局。

---

## 3. 备选架构与已选路线（Approaches）

- **方案 A（已选 · 渐进统一）**：Phase 1 先用 Python 修透量化核心 + 落地 GitHub Actions 每日公共数据流与防回归门禁（兼顾国内免代理直连兜底）→ Phase 2 零混乱前端赚钱与守果闭环 → Phase 3 Tauri 2 + 瘦身 Python Sidecar 桌面客户端 → Phase 4 轻量化核心算法（Rust/WASM）移植统一纯本地桌面与安卓 APK（消费同一套 `float32` 公共数据包）。
- **方案 B（一步到位先重写 Rust/WASM）**：延迟量化 P0 止血 2~3 周，未采纳。
- **方案 C（安卓只做伴侣连 NAS/PC）**：违背纯本地独立使用愿景且增高鉴权维护成本，未采纳。

---

## 4. 详细技术设计

### 4.1 资产分类重构、中短债补齐、锁定期清零与湖仓清洗（`market_lakehouse.py` & `runtime_paths.py`）

1. **升级风格桶为 12 桶（拆出中短债 `short_bond` + 港股离岸 `hk_offshore`）**：
   - `short_bond`（标签：`中短债现金垫`，`asset_class: "bond"`，`is_index_eligible: True`，低久期回撤小，对抗 `1.59%` 十年国债利率反弹风险，作为 C1/C2 压舱与波段止盈落袋池）；
   - `pure_bond`（标签：`中长纯债固收`，`asset_class: "bond"`，`is_index_eligible: True`）；
   - `hk_offshore`（标签：`港股与沪港深`，`asset_class: "hk_equity"`，计入广义权益但受单桶 `≤ 15%` 硬上限，不与 A 股宽基混算）。
2. **精准重写 `classify_fund_bucket_10(fund_type, fund_name)` 判定规则**：
   - **第 1 步（硬排除）**：货币/理财 → `EXCLUDE_MONEY`；场内 ETF/LOF 场内份额（`purchase_status == "场内交易"` 或代码以 `51`/`159`/`56`/`588` 开头且无联接字样）→ **`EXCLUDE_EXCHANGE_ONLY`**（100% 保证买单全是场外基金！）；
   - **第 2 步（纯黄金严控）**：仅当 `fund_type` 为商品/指数型-其他 且名称含 `黄金|上海金|AU9999` 且**不含** `矿|股|有色|油|通胀|农业|资源|FOF` 时，归 `commodity_gold`（`asset_class = "gold"`）。**彻底踢出** `161815`（油气主动 FOF）与 `017192`/`018489`/`016707`/`004432`（4 只周期有色金属股票基，重归 `sector_theme_index`）；
   - **第 3 步（真海外 QDII vs 国内/港股/中概隔离）**：
     - 含 `标普中国|标普A股|中国A股` → 强制不判海外，归本土 `dividend_value` / `broad_index`（根治 `008163`/`501029`）；
     - 含 `中概|海外中国互联|海外互联` → 归 `hk_offshore`（绝不冒充欧美分散对冲！）；
     - 含 `香港|恒生|港股`（不含红利低波主干）→ 归 `hk_offshore`；含 `沪港深`+`红利` → `dividend_value`；
     - 含 `REIT|房地产|抗通胀|原油|石油|天然资源|能源` → 归 `other_commodity`（不占美股/全球权益宽基槽位，且 `is_index_eligible = False`）；
     - 真 `overseas_qdii`：须 `"QDII" in ft.upper()` 或海外股票类型，且不含上述排除词、不含美元/港币现汇份额；
   - **第 4 步（短债 vs 中长纯债 vs 固收+）**：
     - 含 `中短债|超短债|短债|短融|同业存单` 且属债券型 → `short_bond`；
     - 其余纯债（长债/利率/信用/指数固收）→ `pure_bond`；
     - 混合债/二级债/偏债混合 → `fixed_income_plus`。
3. **锁定期全量清零 & 发起式防清盘门禁**：
   - 全量锁定期正则：`r"后端|定开|定期开放|封闭|持有期|个月持有|天持有|年持有|滚动持有"`（覆盖阿拉伯与中文数字，如 `6个月持有`/`六个月持有`/`180天持有期`/`一年持有`，将当前湖仓全部 **10 只**锁定期基金清零）；
   - **种子池净化**：从 `_ANCHOR_SEED_CODES` 删除 `000086`（1 年持有期债券）与 `510300`（场内 ETF），换入开放式大厂短债/纯债标杆；锁定期与场内排除规则对 `_ANCHOR_SEED_CODES` 同样硬生效；
   - **发起式清盘防护**：名称含 `发起` 的基金，在初筛中额外要求单基真实规模 **`≥ 5.0 亿`**（非发起式保持主动 `≥ 5 亿` / 被动 `≥ 2 亿`），规避 3 年满 `< 2 亿` 强制清盘风险。
4. **湖仓原位清洗与精准定向补强（< 10 秒）**：
   - 新增 `reclassify_and_clean_existing_lakehouse()` 原位清洗现存 266 只元数据、剔除全部 10 只锁定期与场内列并合入最新 `fund_trading_rules.parquet`；
   - 定向补拉两小批高价值场外标杆（无需全库重爬）：
     - ① **10~12 只**高流动性大厂开放中短债（`short_bond`，规模 `≥ 10 亿`、开放申购、费率 `≤ 0.45%`）入湖仓，补足低利率久期安全垫；
     - ② **6~8 只**真实高限额开申的大厂场外全球/美股 QDII（含主动如 `270023`/`012920`/`012060`/`005698` 与场外开申海外宽基指数如 `000614`/`021189`），确保 `full_market` 与 `index_only` 均有真实可买海外候选，绝不掺杂中概互联或美国 REITs。
5. **公开种子随仓托管（已拍板）**：
   - 解除 `.gitignore` 对 `data/master/fund_catalog.parquet` 与 `data/master/fund_trading_rules.parquet` 的屏蔽，并加入 `runtime_paths.PUBLIC_SEED_FILES`（纯公开表 ~2.4MB，零隐私），让新克隆、Docker、CI 与 Actions 零冷启动依赖。

---

### 4.2 根治伪 OOS 与上线真滚动 Walk-Forward（`portfolio_optimizer.py` & `goal_driven_selector.py`）

1. **彻底修复 `WinRateOptimizer.optimize()` 泄露（`portfolio_optimizer.py:610-694`）**：
   - 先切分 `train_nav = sub_nav.iloc[:split_idx]`（前 70%）与 `val_nav = sub_nav.iloc[split_idx:]`（后 30%）；
   - 个体指标计算、相关性去冗余、选基与 `_optimize_fixed_n`（第 654 行）**100% 仅使用 `train_nav`**；
   - 仅用 `train_nav` 锁定出的权重在未见过的 `val_nav` 上计算 `oos_win_rate`（保证修改 `val_nav` 绝不影响 `train_nav` 权重，由单元测试刚性锁死）。
2. **真实滚动 Walk-Forward 校验（`goal_driven_selector.py`）**：
   - 新增 `_evaluate_true_walk_forward_oos(...)`：在 2~3 个历史切点（如 `T-2Y`、`T-1Y`，带内存缓存保障总求解 `≤ 3.0s`）严格截断 `nav_df[nav_df.index <= cutoff]` 重跑选基定权，统计真实未来持有期收益/胜率/回撤，输出 `wf_oos_winrate_pct`、`wf_oos_positive_rate_pct`、`wf_splits`，替代原先事后切尾 30% 的伪 OOS，并附诚实的幸存者偏差提示。
3. **撤除误导性紫色遮罩（`api_server.py:2420`）**：
   - 实时全市场求解（`mode == "model_live"`）不再把 `2025-07~至今` 标为“样本外区间”，改为中性标签 `"近阶段结构市"`；仅冻结策略 Trial 29 对照模式保留“样本外区间”。

---

### 4.3 条件胜率高斯核对齐（`winrate_engine.py`）

- 新增带进程内存缓存的 `load_aligned_macro_feature_frame()`，从 `aligned_matrix_total_return.parquet` 预计算每日真实历史宏观特征（沪深 300 倒数估值分位代理、沪深 300 `bias_20`、`mom60`、`ewma_vol`；历史表无日频 DR007 时仅在真实同源 4 维上算核距离，**彻底废弃 `dr007_proxy = 2 × fund_bias20`**）。
- `compute_historical_feature_matrix(nav_series, holding_days)` 按 `DatetimeIndex` 对齐同一套宏观历史表，确保纯债 `006210` 与权益 `110020` 在计算宏观同温层条件胜率时处于完全一致的物理度量空间，消灭 `11.7σ` 错配。

---

### 4.4 防单赛道抱团、场外限购硬过滤、真全天候双保险与 A/C 省费映射（`goal_driven_selector.py` & `api_server.py`）

1. **单风格/单行业硬上限**：
   - 细粒度风格簇 `style_cluster`（`dividend_bank`、`ai_semi_tech`、`cn_broad`、`short_bond`、`pure_bond`、`gold`、`global_qdii`、`hk_offshore`、`other_active`）：
   - 非 `dividend_defense` 模型同簇权重硬上限 **`≤ 35%`**、风险贡献 PCR **`≤ 45%`**；`dividend_defense` 红利簇上限 `45%`；`barbell_growth` 科技成长簇上限 `45%`（彻底消灭 C5 `67.2%` 单押 AI 芯片与 C3 `86.5%` 风险押红利）。
   - `C1`/`C2` 档位债券配置优先纳入至少 1 只 `short_bond`（中短债现金垫）控久期风险；`C3`~`C5` 且 `n_funds <= 6` 时同质纯债最多占 1 席，释放名额给真分散。
2. **拟投金额驱动的限购/停申硬过滤 + 场外海外两级优雅降级**：
   - `solve_goal_driven_portfolio` 接收 `investment_amount: float = 50000.0`，实时关联最新 `fund_trading_rules.parquet`：
     - 暂停申购 → **直接剔除**（显式锁定除外并标红牌）；
     - 预估买入额 `est_buy = investment_amount / n_funds` 需 `> 10` 个交易日买完 → 移出默认候选池，优先同桶高限额替代基；
   - **真全天候结构保底（C2~C4、`n_funds >= 4`）**：目标覆盖 4 类真低相关资产（本土权益 + 开放债基 + 纯黄金联接 + 真海外）；当中国场外 QDII 全市场收紧导致 `index_only` 下 10 日内可买完的真海外指数为空时，执行**两级优雅降级**：① 优先放宽海外槽位限购天数并明文输出分批日定投拆单提示；② 若全部暂停申购，透明提示“当前场外美股/海外指数普遍暂停申购”，自动将避险分散权重无缝承接至**不限购真黄金 + 港股通/红利 + 短债**，绝不无解报错、绝不塞假海外。
3. **A/C 类份额按持有周期智能省费映射（零膨胀矩阵）**：
   - 求解底层仍使用纯净 A 类复权净值；在 `_build_blueprint_payload` 输出层，当 `horizon_months <= 12` 时自动从 `fund_catalog.parquet` 检索同基金对应的 **C 类份额代码**（如 `005561` → 对应 C 类）附在 `share_class_tip` 字段中（提示：`持有 ≤ 1 年建议关注同基金 C 类份额（0 申购费 + 满 30 天免赎回费），长拿 ≥ 1.5 年首选 A 类`），帮场外/银行投资者实打实省下 `0.4%~0.6%` 波段与短期摩擦费。

---

### 4.5 宏观双脑统一、去硬编码与前瞻审计自动落盘（`advisory_engine.py` & `api_server.py`）

1. 清除 [advisory_engine.py](file:///d:/Google/Workspace/Wind/AGY2_FundAdvisory/advisory_engine.py#L4350-L4351) 的 `"16,763 亿"` / `64.5` 硬编码兜底（实时广度抓取失败时显式置 `NEUTRAL` 并注明原因）；将第 7 维文案更正为语义准确的 **“反拥挤安全分（分越高越不拥挤）”**。
2. **熊市趋势-估值折减直接写入 `compute_ten_dimension_votes`**：当 `market_state_code` 含 `BEAR` 且原始正向 `equity_tilt_pct > 0` 时，折半且上限封顶 **`+0.08`**，同步更新 `target_equity_pct`、`suggested_equity_ratio` 与 `causal_formula`（保持全局单一口径 + 不破坏现有 `test_g17` 数学不变量）；同时 `apply_asset_class_constitutional_limits` 硬锁 **`bond_min >= tier_bond_min * 0.6`**（C3 纯债底线不低于 `9%`）。
3. 在 `api_server.py` 后台预热与盘后同步时幂等调用 `forward_audit_logger.record_daily_verdict_if_needed()`（每日最多 1 条）。

---

### 4.6 双选基池透明可选 + 务实低利率默认预期（`web/src/pages/QuantLabPage.tsx` & `WorkbenchContext.tsx`）

1. **双模式并列切换 + 零文字墙利弊提示**：
   - 保持左侧控制台原位置两按钮：**`低费指数核心`**（`index_only`，**前端首屏默认选中**）与 **`全市场含主动`**（`full_market`，**后端 API 默认值保留 `full_market` 兼容旧调用**）。
   - 按钮下方仅加 **1 条 2 行紧凑利弊提示（~34px）+ `?` 对比浮层**，明明白白告知用户两种选法的优势与局限，绝不增加页面杂乱度。
2. **贴合 `1.59%` 低利率的默认目标**：
   - 首屏默认组合调整为更稳健、更易达标的 `C3 · 2 年 · +15%`（年化约 `7.2%`），切换 C1~C5 时仅在用户未手改过目标时联动务实推荐区间（C1 `1年+3%`、C2 `1年+5%`、C3 `2年+15%`、C4 `2年+24%`、C5 `3年+45%`），同时保留完全自由修改权；在低利率纯债提示中坦诚告知“当前 10Y 国债处于低位，债基历史牛市高斜率不宜线性外推”。

---

### 4.7 GitHub Actions 每日公共数据流、防回归门禁与国内免代理多源同步（`.github/workflows/` & `remote_bundle_sync.py`）

1. **`.github/workflows/daily-market-data.yml`**：
   - 工作日 `13:40 UTC`（北京时间 `21:40`）定时 + 手动触发；全局锁定 **`TZ: Asia/Shanghai`**。
   - 调用 `scripts/build_daily_public_bundle.py`：① 刷新 `fund_trading_rules.parquet`（保留 `est_total_operating_fee` 与 `fund_type` 列）；② 执行 `reclassify_and_clean_existing_lakehouse()` + `incremental_daily_sync(cooldown_minutes=0)`；③ 同步指数基线；④ **运行 `tests/test_phase1_quant_integrity.py` 强门禁（不通过绝不覆盖线上稳定包！）**；⑤ 打包发布白名单 6 个纯公开表为 `agy2-market-bundle-latest.tar.gz` + `manifest.json`（SHA256），并同步产出独立资产 **`agy2-mobile-compact-v1.tar.gz`**（`nav_f32.bin` little-endian `float32` + `bundle_meta.json`，为 Phase 4 纯本地安卓/桌面 Rust 核预留零 Parquet 契约）至 `PUBLIC` 仓库 `data-latest` Release。
2. **`.github/workflows/ci-quality-gate.yml`**：每次 Push/PR 自动跑后端 `pytest` 量化防作弊/分类/OOS 门禁 + 前端 `npm ci && npm run build`。
3. **`AGY2_FundAdvisory/remote_bundle_sync.py`（国内免代理必通优先）**：
   - 同步优先级：**① 国内加速镜像 / 用户自定义 `AGY2_BUNDLE_URL`（5s 短超时）→ ② GitHub Release `data-latest` 直连（5s 短超时）→ ③ 无代理自动无缝回退至本机直连国内东财 `FundMNFInfo` 增量日更**，确保中国大陆无代理用户 100% 秒通不卡死。

---

## 5. 验收硬标准（Phase 1 完成定义）

1. **100% 场外开放式 & 零分类/锁定期错配**：全湖仓 `exchange_only == 0`、`fake_qdii == 0`、`non_gold_in_gold == 0`、`lockup_funds == 0`、`short_bond >= 8`；C1~C5 × 4 模型 × 2 池（40 组）无锁定期、无暂停申购、无场内 ETF、单风格权重 `≤ 35%`（防御/杠铃按档上限）。
2. **伪 OOS 彻底根治**：单测验证改动 `val_nav` 绝不改变 `train_nav` 选出的权重（零泄露）；Walk-Forward 盲测结果真实反映历史表现；拟合图无误导性紫色“样本外”遮罩。
3. **条件核对齐**：纯债 `006210` 与权益 `110020` 产生同一历史宏观特征矩阵（`|z|` 均值 `< 2.5`，消除 `11.7σ`）。
4. **宏观双脑与硬编码清零**：`advisory_engine.py` 零 `"16,763 亿"` / `64.5` 硬编码；`SEVERE_BEAR` 下 C3 纯债底线 `≥ 9%` 且看板与求解器口径一致；`forward_audit_logger` 每日幂等落盘。
5. **前端零混乱 + 省费提示**：`web` 编译零错，双选基池默认 `index_only` 且可 1 键切换并展示紧凑利弊对照，短期持有输出 C 类省费提示。
6. **云端数据脚本与 CI 本地演练通过**：`scripts/build_daily_public_bundle.py` 本地干跑产出有效 `agy2-market-bundle-latest.tar.gz` + `agy2-mobile-compact-v1.tar.gz` + `manifest.json`，全部新旧 `pytest` 门禁 100% 通过。
