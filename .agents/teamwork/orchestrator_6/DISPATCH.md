## 2026-11-06T01:01:47Z
启动终极专业度与工程闭环校准：修复热重载与一键全案漏网Bug、打通全目录资产分类对齐、实装真实数学公式驱动的股息安全垫与影子组合调仓复盘、以及安全局部刷新。

Working directory: d:\Google\Workspace\Wind
Integrity mode: development

## Reference Materials
- 核心代码路径：
  - Streamlit GUI 主程序：`AGY2_FundAdvisory/app_gui.py` (端口 8501)
  - 核心策略与模型：`portfolio_manager.py`, `strategy_bridge.py`, `data_loader.py`
  - 只读裁判文件：`judge_engine.py`, `holdout_vault.py`, `AGENT_SPEC.md`, `tests/test_infra.py`

## Verification Resources
- 自动化测试套件：pytest 全量测试（含只读 `tests/test_infra.py`）
- 专项测试 1：验证 `pm.classify_fund_asset_class` 对 161726、161725、160418、013402、008888、050025、005561、002351、000216 全部返回 9 大标准类别，无一返回“其他权益资产”
- 专项测试 2：验证 `StrategyBridge.calculate_portfolio_yield_cushion` 与 `pm.evaluate_rebalance_audit` 返回真实动态计算数值，且修改持仓 `current_nav` 时影子资产与实盘资产随之真实联动
- 专项测试 3：运行 Streamlit `AppTest` 验证全站 4 个 Tab 零异常报错，8501 端口服务平滑重启

## Requirements
- R1. 精准修复热重载导入遗漏与一键全案表格自动保存拦截
- R2. 升级资产大类分类器消除死代码，实现全基金池标准大类对齐
- R3. QDII 跨时区交割标注与同公司 T+1 转换隔离
- R4. 实装组合年度股息与票息安全垫精算引擎（真实数学公式）
- R5. 实装实盘调仓决策复盘 vs 初始躺平影子组合（真实数学公式）
- R6. 数据源健康度徽座与安全的 @st.fragment 局部刷新
- R7. 物理安全红线与开发质量约束

## 2026-11-06T01:15:34Z
【主干同步与协调指令】
来自上级 caller 的最新指令：
主干工程师已完成所有 4 处工程漏洞修复与三大买方投顾实战能力升级（包含 calculate_portfolio_yield_cushion、evaluate_rebalance_audit、9 大标准资产大类反查对齐、热重载导入补齐、一键全案自动保存拦截、A/C算费 fragment 局部刷新与行情源状态徽章）。
同时已编写并固化测试用例 tests/test_adv_final_closure.py。
请协调员团队：
1. 立即停止重复实装代码，避免对同一工作区文件产生写入冲突；
2. 调度测试员运行轻量三阶核验：py -3 -m pytest tests/test_adv_final_closure.py tests/test_adv_upgrade_suite.py tests/test_infra.py；
3. 核验通过后，直接生成验收复盘报告并收口完成任务。
