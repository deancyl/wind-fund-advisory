# G6 世代 GUI 架构与测试套件深度调研报告 (Explorer 3 Technical Survey Report)

## 0. 调研概述与执行环境
- **调研智能体**: Explorer 3 (GUI Architecture & Test Suites)
- **目标工程**: Wind 投顾量化工作区 (G6 世代)
- **核心文件路径**: 
  - GUI 主程序: `AGY2_FundAdvisory/app_gui.py` (6,982 行，397 KB)
  - 投顾决策引擎: `AGY2_FundAdvisory/advisory_engine.py` (1,982 行，101 KB)
  - 核心测试套件: `tests/test_infra.py`, `tests/test_adv_final_closure.py`, `tests/test_g3_evolution_loop.py`, `tests/test_gui_multi_ledger_stress.py`
- **只读禁改校验**:
  - `AGY2_FundAdvisory/judge_engine.py` (未修改，只读锁定)
  - `AGY2_FundAdvisory/holdout_vault.py` (未修改，只读锁定)
  - `AGY2_FundAdvisory/AGENT_SPEC.md` (未修改，只读锁定)
  - `tests/test_infra.py` (未修改，只读锁定)
  - 基准测试验证结果: 50 项测试 100% 全绿通过 (耗时 93.17s)

---

## 1. 图 1 双翼看板 (Twin-wing Dashboard) 深度调研

### 1.1 今日市场脉搏晨报 (Morning Report Pulse)
- **代码渲染定位**:
  - 位于 `AGY2_FundAdvisory/app_gui.py` 第 2411 至 2456 行。
  - 处于 `with st.expander("🔭 全市场机会雷达 ｜ 🚨 主动风险预警哨 (双翼智能投顾看板)", expanded=True):` 下的 `col_radar, col_sentry = st.columns([6.2, 3.8])` 左翼 `col_radar` 容器中。
- **当前逻辑剖析**:
  - 目前仅拉取 `t_data = data_loader.fetch_market_turnover_and_sentiment()`，生成纯静态文字拼接：`两市成交{turnover_str}{vol_text}，{erp_zone}；{lead_str}领衔主线。`
  - 缺乏：精确到秒的实时抓取时间戳、两市成交额与主力情绪宽度的醒目指标、实时抓取的 2~3 条宏观/行业关键快讯、以及量价与资讯结合的操作定调量化依据。
  - 历史三大牛熊拐点实盘对照尺: 在第 2438~2442 行通过 `StrategyBridge.get_historical_inflection_ruler(current_erp=erp_pct, current_bias=bias_val)` 和 `render_historical_inflection_ruler_html(inflection_ruler)` 稳定渲染。
- **G6 升级方案**:
  1. **实时秒级感知时间戳**: 
     - 注入 `rt_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")`，展示于晨报头部，如 `📢 今日市场脉搏晨报 (实时感知: 2026-11-07 14:32:15)`。
  2. **两市量能与情绪宽度**:
     - 展示 `t_data.get("turnover_str")` (如 `12,350 亿`)，配合 `t_data.get("sentiment_label")` (如 `多方占优 (上涨3120家/下跌1850家)`)。
  3. **实时财经快讯与催化剂注入**:
     - 调用 `data_loader.fetch_realtime_market_news_and_catalysts()`，提取 2~3 条核心资讯快讯（含资讯发生时间与宏观/赛道关联标签），以紧凑列表形式渲染在脉搏叙述下方。
  4. **明确操作定调与量化依据**:
     - 依据实时 ERP 分位数（如 82.6%）与两市成交动向，输出操作定调，例如：
       `【操作定调】估值处高性价比击球区(ERP 82.6%)，两市放量活跃，建议维持 1.76x 逆向进攻节奏，重点布局左侧低估与右侧动量共振赛道。`
  5. **历史拐点对照尺绝对保护**:
     - 保持 `ruler_bar_html` 紧随其后在同一 `.decision-card` 内渲染，绝对杜绝丢失。

### 1.2 Top 3 优选赛道卡片 (Top 3 Track Cards)
- **代码渲染定位**:
  - 位于 `AGY2_FundAdvisory/app_gui.py` 第 2457 至 2498 行，通过 `cols_top3 = st.columns(3)` 渲染三张并列卡片。
- **当前逻辑剖析**:
  - 仅展示赛道名称、语义标签、综合得分、估值分位、优选基金名称与代码以及一键入备选池按钮。
  - 缺乏：今日盘中实时涨跌幅、四维得分拆解（估值分、动量分、信噪比分、反拥挤分）、定性定量入选依据。
- **G6 升级方案**:
  1. **今日盘中实时涨跌幅**:
     - 从 `sec` 中提取盘中实时涨跌幅 `rt_change_pct`（如 `+1.85%` 或 `-0.42%`），在赛道名称右侧或标签旁以 A 股标准红涨绿跌胶囊呈现（`color: var(--color-up)` / `color: var(--color-down)`）。
  2. **四维得分拆解 (4D Factor Score Breakdown)**:
     - `advisory_engine.py` 中的 `OpportunityRadarEngine._score_sector` 已经计算并返回了 `s_val` (估值分)、`s_mom` (动量分)、`s_er` (信噪比分) 与 `s_crowd` (反拥挤分)。
     - 在卡片内新增四格紧凑拆解栏：
       `估值: 88.5 ｜ 动量: 78.0 ｜ 信噪比: 82.4 ｜ 反拥挤: 85.0`
  3. **定性与定量入选依据**:
     - 根据四维最高得分特征自适应生成定性定量入选依据：
       - 若低估击球：`估值分位仅 12%，安全边际深厚，左侧性价比突出`
       - 若右侧共振：`信噪比高达 82，MA20 斜率向上，右侧主升浪确立`
       - 若避险压舱：`与大盘相关性低，有效平抑组合整体波动`

### 1.3 右翼主动风险预警哨 (Active Risk Patrol)
- **代码定位与标题清理**:
  - 位于 `AGY2_FundAdvisory/app_gui.py` 第 2521 行：
    ```python
    st.markdown("<div style='font-size: 14px; font-weight: 700; color: var(--text-primary); margin-bottom: 8px;'>🚨 主动风险预警哨 · 六维主动巡检 <span style='font-size: 11px; font-weight: 400; color: var(--text-secondary);'>[主动风险预警哨 · 四维巡检升级版]</span></div>", unsafe_allow_html=True)
    ```
  - **修改点**: 立即将残留的灰色开发口号尾缀 `<span style='font-size: 11px; font-weight: 400; color: var(--text-secondary);'>[主动风险预警哨 · 四维巡检升级版]</span>` 彻底移除，标题保持专业干净：
    `🚨 主动风险预警哨 · 全维主动巡检`
- **预警卡片容器高度与滚动条截断修复**:
  - 当前容器代码（第 2531 行）：`with st.container(height=300):`
  - **截断机理分析**:
    - 在 `app_gui.py` 第 574~585 行的全局 CSS 中，`.decision-card` 声明了 `min-height: 108px; padding: 12px 14px;`。
    - 预警哨内的单张预警卡片加上处置按钮高度通常达到 130~150px。当有 2 张以上预警卡片或 1 张卡片配按钮时，总高度超过 300px，Streamlit 容器立即产生垂直滚动条。
    - 由于 Streamlit `st.container(height=300)` 内部存在默认 `overflow-y: auto` 且内边距较紧凑，当产生滚动条时，第一张卡片的顶部边框与标题文字极易被顶部视口或滚动条物理截断。
  - **修复调整策略**:
    - 将容器高度由 `height=300` 微调提升至 `height=360`（或 `380`），与左翼雷达卡片自然对齐；
    - 针对预警哨卡片，在内联样式中显式覆盖 `.decision-card` 的全局 `min-height`，指定 `min-height: auto !important; padding: 10px 12px; margin-top: 2px;`，杜绝任何上边缘截断。

---

## 2. 在线基因编程自适应进化白盒徽章 (Online Genetic Programming Whitebox Badge)

### 2.1 放置位置 (Placement)
- 最佳挂载位置：位于左翼 `col_radar` 容器顶部，紧邻 `🔭 全市场机会雷达` 标题正下方、晨报卡片与 Top 3 赛道卡片之上。
- 在用户视线进入雷达的一瞬间，直观展现底层因子的动态生命力。

### 2.2 徽章样式与白盒信息呈现 (Styling & Content)
- **视觉风格**: 紧凑型白盒卡片，遵循 GEMINI.md 复杂度守恒，高度控制在 48~56px 以内，无大面积弹窗或刺眼色块。
- **信息分层**:
  - **第一行 (核心算子与演化状态)**:
    - `🧬 在线基因编程自适应进化引擎 (OnlineHeuristicFactorEvolver)`
    - 右侧胶囊：`🟢 60日真实日线已收敛 ｜ OOS 超额适应度 +18.4%`
  - **第二行 (因子权重动态分配与基准对照)**:
    - 展示当前代际胜出的最优 4 维权重：
      `动态因子配比: 估值 22% ｜ 动量 35% ｜ 信噪比 28% ｜ 反拥挤 15%`
    - 与原静态硬编码常数 (30%/30%/25%/15%) 形成白盒对照，明确废止静态加权。
  - **底层环境自适应状态标签**:
    - 如 `[环境适配: 震荡分化市自适应强化信噪比与动量企稳权重，防止左侧过早抄底]`。

---

## 3. Tab 1 与 Tab 2 界面调整深度调研

### 3.1 目标波动率超标预警与压降卡片 (Target Volatility Alert & Reduction Card)
- **业务依据**:
  - 用户风险档位 C1 至 C5 分别对应明确的目标年化波动率上限：
    - C1 安稳保守型: 波动率上限 $\le 6.0\%$ (目标区间 $5\% \sim 8\%$)
    - C2 稳健固收+型: 波动率上限 $\le 10.0\%$ (目标区间 $8\% \sim 12\%$)
    - C3 平衡进取型: 波动率上限 $\le 15.0\%$ (目标区间 $12\% \sim 18\%$)
    - C4 成长进攻型: 波动率上限 $\le 22.0\%$ (目标区间 $18\% \sim 30\%$)
    - C5 极限高Beta追击型: 波动率上限 $\le 32.0\%$ (目标区间 $30\% \sim 100\%+$)
- **Tab 1 新资建仓展示位置**:
  - 位于步骤二推演完成后的“方案核心归因”区（`app_gui.py` 约第 3428 行附近）。
  - 根据组合加权年化波动率 $\sigma_p$ 与当前档位上限进行对比：
    - 若超标：渲染黄色预警卡片，明确标出当前加权波动率（如 18.2%）与档位上限（15.0%），给出具体压降建议（如“建议将高波动的科技成长标的权重压降 17.6%，平移至 002351 纯债压舱石”）。
    - 若达标：渲染绿色达标徽章（如“🟢 组合年化波动率 13.8% 符合 C3 平衡进取型风险预算”）。
- **Tab 2 持仓调仓展示位置**:
  - 位于步骤二 AI 诊断（第 4900 行）及步骤三调仓后果（第 5420 行）前。
  - 对实盘持仓的实际 20 日真实波动率进行实时巡检，当发生组合风格漂移导致波动率超标时，在调仓要点中输出精准压降比例。

### 3.2 Tab 2 红利再投资与现金分红免损耗再平衡卡片
- **业务背景与买方价值**:
  - 针对持有满 1 年以上的红利资产（如 `005561` 创金合信红利低波A、`160418` 华安中证银行等），基金分红是零税负、零赎回费沉淀现金的绝佳途径。
  - 直接赎回换仓：通常产生赎回手续费（即便满 1 年免赎回费，也会损失底仓份额，触发 T+2 在途空窗期与踏空风险）。
  - 切换为“现金分红”：将分红方式从默认的“红利再投资”改为“现金分红”，分红直接以现金形式返还至可用现金账户，零赎回费、零在途损耗，本金持有期不被清零。
- **展示位置**:
  - 位于 Tab 2 步骤三调仓真实后果下方（`app_gui.py` 约第 5450 行）。
- **呈现设计**:
  - 自动扫描实盘持仓中持有天数 $\ge 365$ 天的红利/高股息类标的；
  - 测算标的年化股息现金分红预期（如 `005561` 年化约 5.2%，折算预计派现 ¥4,500 元）；
  - 输出对比账单：
    - 现金分红再配置：手续费 ¥0，在途风险 0 天，持有期清零 0 元；
    - 直接赎回换仓：手续费损失与 T+2 在途踏空成本；
  - 提供操作要点：“建议将上述标的在销售平台分红方式变更为【现金分红】，实现无摩擦资金再配置”。

---

## 4. 测试套件架构与 G6 增量用例规划

### 4.1 四大核心测试套件现状调研
当前工作区经全量运行验证，4 大核心测试套件共计 50 个用例全部通过（50 passed in 93.17s）：
1. **`tests/test_infra.py` (只读禁改裁判套件)**:
   - 包含 14 个测试用例，覆盖数据加载器全收益矩阵对齐、模拟算子摩擦费率与 7 天惩罚、因果探针前瞻偏差拦截、四岛流派合规性、盲测金库上限、纯债套利与低A股权益拦截等。
   - **状态**: 严格只读，git status 确认 100% 干净未触碰。
2. **`tests/test_adv_final_closure.py` (买方投顾工程闭环套件)**:
   - 包含 14 个专门测试用例 (`test_specialized_1` 至 `test_specialized_14`)，覆盖 9 大资产标准分类、安全垫与影子组合动态审计、自动提交重导兼容性、真实估值防作弊、多账本原子同步与隔离等。
3. **`tests/test_g3_evolution_loop.py` (量化进阶演进闭环套件)**:
   - 包含 12 个进阶测试用例（`test_g3_1` 至 `test_g3_8`，以及 G5 新增的 `test_g5_1` 至 `test_g5_4`），覆盖 EWMA 动态协方差突变、极端黑天鹅块重采样 CVaR99%、单基真实波动率穿透、历史三大牛熊拐点对照尺、浮盈安全垫破净承压推演及 14:30 尾盘估值异动。
4. **`tests/test_gui_multi_ledger_stress.py` (GUI 多账本压力测试套件)**:
   - 包含 10 个用例，覆盖多账本高频切换原子性、跨 Tab 同步、Tab 1 新建账本隔离、异常损毁账本容错自愈，以及 Streamlit AppTest 真实无缝交互走查。

### 4.2 G6 世代在 `tests/test_g3_evolution_loop.py` 中新增用例规划
为了严密覆盖 G6 世代核心功能，规划在 `tests/test_g3_evolution_loop.py` 中新增 3 大专项测试用例：
1. **`test_g6_1_realtime_news_and_quotes_fusion`**:
   - 验证 `data_loader.fetch_realtime_market_news_and_catalysts()` 接口的联网抓取、2秒超时保护与本地持久化缓存自愈机制；
   - 验证盘中最新点位与涨跌幅动态拼接入 `OpportunityRadarEngine` 的最后一根 K 线，使得赛道乖离率与综合得分随行情动态跳动；
   - 验证晨报区时间戳精确到秒，两市成交额与主力情绪宽度真实挂载，历史三大牛熊拐点对照尺 4 节点完整保留。
2. **`test_g6_2_online_heuristic_factor_evolver`**:
   - 验证 `OnlineHeuristicFactorEvolver` 在线进化算子：
     - 构建 32 个候选基因个体（因子权重向量与参数）；
     - 利用近 60 个交易日 14 大赛道真实收益率矩阵，纯 NumPy 向量化评估夏普比率、胜率与最大回撤；
     - 50ms 内完成锦标赛选择、交叉与变异；
     - 验证废止 0.30/0.30/0.25/0.15 静态常数，权重严格归一化 $\sum w_i = 1.0$；
     - 验证输出 OOS 样本外超额适应度提升幅度 $\ge 5.0\%$。
3. **`test_g6_3_target_volatility_risk_control_and_dividend_mode`**:
   - 验证 C1 至 C5 档位目标波动率预算上限与超标判定；
   - 验证组合年化波动率超标时高波资产向纯债或现金平移的压降比例测算；
   - 验证持有满 1 年红利底仓基金的现金分红派现再配置测算，量化零赎回费与零在途损耗优势。

---

## 5. 调研结论与下一步实施建议
1. **架构清晰，修改点高度内聚**:
   - 所有 GUI 调整集中于 `AGY2_FundAdvisory/app_gui.py` 的首屏双翼看板（第 2400~2600 行）与 Tab 1/Tab 2（第 3400 行与第 5400 行）；
   - 测试用例集中于 `tests/test_g3_evolution_loop.py`，四大只读裁判文件绝不触碰。
2. **视觉走查要求**:
   - 实施阶段需彻底杀掉旧 8501 进程，清理 Streamlit 缓存后重新拉起，并调用 `/browser` 进行桌面端与移动端多模态真实核验。
