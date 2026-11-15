# Scope: Milestone 2 (M2: 首次自动路由、滚动发车盲测与交互精修)

## Architecture
- `app_gui.py`: UI entry point, session state, automatic routing, responsive mobile layouts, styling consolidation, Tab 2/4 tool dock & narrative cards.
- `strategy_bridge.py`: Strategy execution, rolling DCA blind backtest table, friction bill calculation, backtest fee deduction.
- `portfolio_manager.py`: Portfolio parsing, OCR dual-channel union, vocabulary filtering for fund names & holding periods.
- `tests/test_g19_m2_routing_and_rolling_dca.py`: Authoritative E2E test suite (88 test cases across Tiers 1-4).

## Feature Inventory
| # | Feature | Description | Target Files | Status |
|---|---------|-------------|--------------|--------|
| 7 | 首次加载存量持仓账本自动路由 | 在 app_gui.py 初始化 pm 后检查持仓，>=10只持仓且未执行初始路由时自动跳转 Tab 2 主流程并触发诊断与调仓 | app_gui.py | IN_PROGRESS |
| 8 | 样式集中合并与手机端列选择器 | 将 render_chief_advisor_memo_card 内部样式移至全局主样式表；手机端按钮组补齐 stColumn 选择器并排除 numberInput 按钮 | app_gui.py | IN_PROGRESS |
| 9 | 近 3 年滚动发车盲测胜率实证表 | 严格扣费、切断未来函数，统计近三年双月/季度滚动发车持有 180天、365天胜率/净收益/超额收益，并渲染卡片表格 | strategy_bridge.py, app_gui.py | IN_PROGRESS |
| 10 | 摩擦账单动态精算与回测全额扣费 | 清除 calculate_mutual_fund_friction_bill 伪常数，改由 weights 动态计算；补齐日度管理托管费与阶梯赎回费 | strategy_bridge.py | IN_PROGRESS |
| 11 | OCR 识别双通道并集与词表扩充 | 修复 OCR 中提前 return 丢弃空间块聚类缺陷，改为双通道并集融合；扩充指数代码与持有期数字词表 | portfolio_manager.py | IN_PROGRESS |
| 12 | IS_MOBILE_VIEW 激活与响应式布局 | 激活 app_gui.py 中 IS_MOBILE_VIEW 变量响应式布局，在关键分栏自适应切换单列容器 | app_gui.py | IN_PROGRESS |
| 13 | Tab 2 工具坞扁平化与前置人话解读卡片 | 精简 Tab 2 运维工具坞三层录入套娃（扁平化为 st.radio）；为 Brinson 归因、重仓交叉热力图、四象限散点图注入人话解读卡片 | app_gui.py | IN_PROGRESS |

## Test Verification Target
- `pytest tests/test_g19_m2_routing_and_rolling_dca.py` -> 88 passed.
