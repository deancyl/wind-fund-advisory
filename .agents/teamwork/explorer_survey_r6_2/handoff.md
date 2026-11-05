# Handoff Report - Explorer 2 (R3: Tab 2「步骤一：持仓账本」人体工学深度重构调研)

## 1. Observation
1. **源码位置与既有实现**：
   - `AGY2_FundAdvisory/app_gui.py` 第 1775~1830 行：顶部存在 4 个独立全宽控制按钮：`btn_t2_load_demo` (加载演示组合)、`btn_t2_undo` (一键撤销快照)、`btn_t2_sync_nav` (同步真实净值)、`num_edit_cash_pool` (现金池管理 Popover)；其下方为 4 个独立指标卡：`_t2_mkt`、`pm.available_cash`、`_t2_pnl`、标的数。
   - `AGY2_FundAdvisory/app_gui.py` 第 1832~1842 行：在指标卡与表格之间突兀插入了折叠框 `with st.expander("📋 实盘接管档案", expanded=False):`。
   - `AGY2_FundAdvisory/app_gui.py` 第 1854~1878 行：`pm.export_snapshot_df()` 输出了 19 列数据，`st.data_editor` 的 `disabled` 列表中硬编码禁用了 `"当前市值(元)"`、`"今日实时估值"`、`"今日实时估值涨跌(%)"`、`"盘中预估盈亏(元)"`、`"今日预估盈亏率(%)"`、`"估值更新时间"` 等 10 个字段，造成桌面端严重横向滚动。
   - `AGY2_FundAdvisory/app_gui.py` 第 1880~1927 行：表格底部操作栏由 3 列组成，中间列直接渲染带有 Label 的 `st.selectbox`，选定后弹出删除按钮，导致高度极度不平整。
   - `AGY2_FundAdvisory/app_gui.py` 第 1930~2014 行：底部存在 2 个孤立折叠框：`✨ 快速录入持仓` 与 `📦 FIFO批次透视`。
2. **测试基线与断言**：
   - 执行 `py -3 -m pytest AGY2_FundAdvisory/tests/test_deep_remodel_final.py` 验证通过：`7 passed, 21 warnings in 71.37s`。
   - 测试文件中 `key_titles` 硬编码检查 `assert "实盘接管档案" in text`、`assert "FIFO批次透视" in text`、`assert "步骤一：持仓账本" in text`，且纯汉字长度 `<= 7`。
   - `tests/test_live_rebalance_upgrades.py` 第 304~305 行断言 `pm.export_snapshot_df()` 必须包含 `"盘中预估盈亏(元)"` 与 `"今日预估盈亏率(%)"`。

## 2. Logic Chain
1. **第一层重构逻辑**：
   - 根据需求 R2，演示组合载入、撤销快照已移入侧边栏全局领航台；同步净值属于表格工具，应收拢至表格操作栏；现金池管理应内嵌为 Card 2 的专属 Popover。
   - 由此可直接裁撤 `app_gui.py:1777-1820` 的 4 个按钮，将垂直空间释放给 4 张对齐看板卡：
     - Card 1 展示持仓总市值与仓位占比；
     - Card 2 展示可用现金与修改现金 Popover；
     - Card 3 展示累计盈亏、盈亏率及由盘中实时行情折算法规 95% 系数得到的今日盘中预估盈亏；
     - Card 4 动态统计穿透批次后的已满 7 天免罚标的数与未满 7 天 1.5% 强锁标的数，及接管期 Alpha。
2. **第二层表格精简与双向联动逻辑**：
   - 测试断言要求 `pm.export_snapshot_df()` 保持完整 19 列不变（保持底层契约）；但在 `app_gui.py` 传递给 `st.data_editor` 前，提取为 10 列精炼视图。
   - 剔除重复的盈亏率与低频列，将「持有天数」与「赎回费状态」格式化为 `f"{min_days}天 {badge}"` 单元格；用户双击该列时输入整数或天数文本，保存时通过正则 `re.search(r'\d+', str(val))` 解析整数，实现自然数修改与费率自适应刷新。
   - 解除 `disabled` 中对 `"当前市值(元)"` 的锁定。保存时通过状态机甄别修改来源：若市值发生改变且份额未改，以 `round(新市值 / 当前净值, 2)` 反算新份额；若份额被修改则以新份额重算市值；通过 `pm.add_or_update_holding` 原生批次等比缩放机制保护 FIFO 历史与持有天数，并触发 `_recalculate_totals()` 与 `st.rerun()` 实现全站总资产、权重与看板卡同步联动。
   - 将删除下拉框与确认操作收敛进 `st.popover("🗑️ 删除标的")`，与保存、同步净值、导出 CSV 组成 4 列等高（38px）标准操作栏。
3. **第三层工具坞整合逻辑**：
   - 将原先插在表格上方的「实盘接管档案」下移，与「快速录入持仓」、「FIFO批次透视」合并为单一折叠框 `with st.expander("🛠️ 账本工具坞", expanded=(not has_holdings)):`，内嵌 3 栏 Tabs。
   - 无持仓时自动展开并停留在快速录入，有持仓时紧凑收折于底部；Tab 名称完整保留 `"实盘接管档案"` 与 `"FIFO批次透视"`，完全满足既有测试断言。

## 3. Caveats
1. `pm.export_snapshot_df()` 内部实现不可删减列名（以免破坏既有单测），列裁剪必须作用于 `app_gui.py` 前端渲染层。
2. 若用户在持仓表新增空白行并仅输入市值，当前净值缺省为 1.0 时需容错保护避免除以零。
3. 调研过程严格遵循只读原则，未改动任何源码文件。

## 4. Conclusion
Tab 2「步骤一：持仓账本」人体工学重构方案全面闭环，已输出完整调研报告 `survey_report.md`。方案在视觉上彻底消除首屏拥挤与横向滚动，在交互上打通当前市值双向反算与等高操作栏，在架构上完美整合工具坞与状态自适应，已完全具备实施施工条件。

## 5. Verification Method
1. 检查调研报告文件：`d:\Google\Workspace\Wind\.agents\teamwork\explorer_survey_r6_2\survey_report.md`。
2. 运行既有测试套件：`py -3 -m pytest AGY2_FundAdvisory/tests/test_deep_remodel_final.py`，确认基线 100% 通过。
3. 待施工完成后，运行增量 Delta Test 验证：
   - 用户编辑当前市值反算持仓份额是否精准；
   - 持有天数正则提取与费率状态刷新是否生效；
   - 4 张指标卡与工具坞交互是否无异常。
