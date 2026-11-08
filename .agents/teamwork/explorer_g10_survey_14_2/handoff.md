# Handoff Report — G10 Visual Subtraction & Quant Calibration Survey

## 1. Observation

直接观测到的文件路径、代码行号、数值与行为：

1. **`advisory_engine.py` 行号 1135 ~ 1185 (`_synthesize_quantitative_evidence`)**：
   - 第 1160-1161 行：
     ```python
     elif bias_20 >= 0.0 and slope_20 > 5.0:
         mom_txt = f"均线斜率 +{slope_20:.1f} 右侧共振稳步上行"
     ```
   - 第 1171-1172 行：
     ```python
     elif er_20 <= 0.35:
         snr_txt = f"信噪比 {er_20:.2f} 处于高频震荡博弈"
     ```
   - 第 1183 行：
     ```python
     evidence = f"【量化因果链】{val_txt}，{mom_txt}；{snr_txt}，{crowd_txt}。"
     ```
   - 观测现象：当标的处于低信噪比高频震荡区（`er_20 < 0.35`）时，若 20 日均线斜率 > 5.0，系统输出“右侧共振稳步上行”与“信噪比处于高频震荡博弈”同屏冲突。
   - 在 `app_gui.py` 第 2974 ~ 2976 行，该长文本直接作为灰色段落框渲染在大屏上，垂直占用高达 50px。

2. **`data_loader.py` 行号 247 ~ 450 (`fetch_realtime_market_news_and_catalysts`)**：
   - 抓取东财快讯 `kuaixun/v1/getlist_102_ajaxResult_{limit}_1_.html`。
   - 第 338-354 行遍历 `raw_news`，仅调用 `_tag_news_item(t, d)` 打标，若未命中任何板块，打上“市场快讯”并全部推入 `parsed_items`。
   - 观测现象：未进行金融业务白名单过滤与军事/娱乐黑名单过滤，国际局势快讯（如“沙特联军拦截无人机”）直接流入 A 股早报首条。

3. **`portfolio_manager.py` 行号 8674 ~ 8995 (`simulate_portfolio_cvar_bootstrap`)**：
   - 实盘组合（6只标的，含纯债与黄金）运行结果：
     - `overall_cvar_99`: `36.12%`
     - 2008危机情景 `total_cvar_99_pct`: `36.12%`
     - 第 8895 行：`daily_drift = port_ret / max(20.0, float(h_days))`，`h_days = 60`。
     - 第 8896 行：`daily_vol = max(0.005, abs(port_ret) * 0.15 / np.sqrt(h_days))`。
     - 第 8916 行：`pred_mdd = max(var_95, abs(port_ret) * 100.0 if port_ret < 0 else var_95)`。
   - 对比 Tab 3 (`winrate_engine.py` 第 935 行 `simulate_monte_carlo_block_bootstrap_stress`)：
     - 基于 2,144 个交易日真实历史收益率，`cvar_99_pct = 12.81%`，`liquidity_discount_pct = 1.32%`，`total_extreme_loss_pct = 14.13%`（基线配置下为 12.0%）。
     - 右翼显示的 -36.1% 比 Tab 3 高出近 3 倍。

## 2. Logic Chain

1. **信噪比与动量冲突推导**：
   - 考夫曼信噪比 $ER_{20} = \frac{|P_t - P_{t-20}|}{\sum | \Delta P |}$ 衡量趋势效率。$ER < 0.35$ 意味着价格路径充斥高频来回锯齿，净位移极小。
   - 此时即便短期 20 日均线因微幅基数向上呈现正斜率，也仅代表价格在底部做箱体宽幅拉锯，绝非稳步上行的单边共振趋势。
   - 因此当 $ER < 0.35$ 且 $slope > 0$ 时，必须强制改写为“底部震荡筑底、均线初现企稳”，禁止出现“右侧共振”伪结论。

2. **快讯信源污染推导**：
   - 东财 7x24 小时快讯接口为全天候全球大盘流，包含海外时政与综合新闻。
   - 现存逻辑仅提取关键词做正向分类，未做反向拒绝与财经强约束。
   - 必须通过 32 个 A 股核心金融白名单词库（要求命中 $\ge 1$）与 9 个涉军/赛事黑名单（命中 $\ge 1$ 即丢弃）形成双向防火墙。若全量丢弃后无匹配，无缝降级至基于当日真实两市成交额与涨跌家数情绪宽度合成的市场综述。

3. **CVaR 严重失真推导**：
   - 2008 全球金融危机累计跌幅（-35%）历时 210 个交易日。
   - `portfolio_manager.py` 将 -35% 强行除以 60 天，得到 `-0.50%/天` 的日均跌幅，并按 60 天复利累乘 $(1 - 0.0050)^{60} = 0.74$，人为制造出 60 天暴跌 26% 的严重假象，再加上波动率与硬编码 `max(abs(port_ret))` 下界，强行锁死在 36.1%。
   - Tab 3 是针对 2018-2026 实盘真实多资产每日波动的 60 天极限回撤，因此为 12.0%。
   - 解决路径：前端右翼预警哨彻底做减法，移除该卡片；后端将 60 天推演的日度漂移率校准至危机真实天数（210/52/25 天）并对齐真实日度波动（0.0075），实现与 Tab 3 的数学口径彻底统一。

## 3. Caveats

1. **测试断言兼容性**：
   - `tests/test_challenger_g9_m1_adversarial.py` 第 363 行明确断言：`assert "【量化因果链】" in rt_eval["core_logic"]`。
   - 因此 `advisory_engine.py` 的 `evaluate_sector` 必须同时保留 `core_logic`（供测试校验因果链）并新增 `concise_logic`（供前端渲染 <= 18 汉字的一句话依据）。
2. **离线与冷启动保底快照**：
   - `data_loader.py` 的冷启动离线预置项（第 417-436 行）已严格满足金融白名单，且时间戳标注为离线预置，严禁使用 `datetime.now()` 破坏已有的防未来时间测试。
3. **右翼预警哨定位**：
   - 右翼预警哨的职责是实盘当前持仓的即时风控（未满 7 天锁定、超买超卖、清盘风险），去除压力测试卡片与未报警的大绿卡后，右翼高度更加紧凑，主工作区 Tab 可以整体上提进入首屏。

## 4. Conclusion

1. **advisory_engine.py**：在 `_synthesize_quantitative_evidence` 中，当 `er_20 < 0.35 and slope_20 > 0.0` 时，强制输出“底部震荡筑底、均线初现企稳”；并在 `evaluate_sector` 中输出严格 $\le 18$ 汉字的 `concise_logic`。
2. **data_loader.py**：在 `fetch_realtime_market_news_and_catalysts` 中实装 32 词金融白名单与 9 词严格黑名单，并在无匹配时输出真实两市量能与情绪综合大盘快讯。
3. **portfolio_manager.py 与 app_gui.py**：从首屏右翼预警哨中彻底移除 `render_stress_liquidity_card_html`；校准 `simulate_portfolio_cvar_bootstrap` 的日度漂移与波动缩放，使极限 CVaR 99% 精确校准至 ~12.0%，与 Tab 3 保持完全一致。

## 5. Verification Method

1. **自动化测试套件回归**：
   - 运行针对多资产相关性与压力测试的专项测试：
     `py -3 -m pytest tests/test_g10_correlation_liquidity_and_stress.py`
   - 运行因果链与信源验证测试：
     `py -3 -m pytest tests/test_challenger_g9_m1_adversarial.py`
   - 运行全量核心套件回归：
     `py -3 -m pytest tests/test_infra.py tests/test_adv_final_closure.py tests/test_g3_evolution_loop.py`
2. **数据一致性探针**：
   - 运行 Python 脚本验证 `simulate_portfolio_cvar_bootstrap` 与 `simulate_monte_carlo_block_bootstrap_stress` 输出的 CVaR 99% 均处于 12% 附近区间。
   - 验证快讯过滤：传入包含“沙特联军拦截无人机”与“央行降准”的测试列表，验证拦截前者、放行后者。
3. **服务存活与渲染走查**：
   - 重启 Streamlit 8501 端口服务，检查 `http://127.0.0.1:8501/_stcore/health` 返回 `ok`。
   - 打开页面审查首屏：Top 3 赛道无断字、无灰色长文框；右翼无 -36.1% 冗余卡片；无军事快讯。
