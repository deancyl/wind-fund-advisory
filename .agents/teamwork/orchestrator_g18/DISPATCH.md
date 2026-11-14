# Dispatch Log

## 2026-11-14T08:57:52Z

针对 Wind 投顾系统启动 G18 世代生产环境迭代：修复首屏裁决台手机端高度溢出重叠、打通十维投票与定权优化器知行合一闭环、校准汇率与美债真实最新数据、实装存量账本首屏自动路由，并升级截图导入双因子匹配引擎与完成端到端双视口实测验收。

Integrity mode: development
The team must NOT: 严禁修改四个只读裁判文件 judge_engine.py、holdout_vault.py、AGENT_SPEC.md、tests/test_infra.py；严禁修改 DataLoader.simulate_execution 的默认函数签名与默认扣费逻辑；绝对禁止输出带冒号的 slashCommand: 格式；严禁创建 GitHub Release。

## Requirements
### R1. 第一阶段：修复 UI 溢出重叠与首次加载智能路由（app_gui.py）
### R2. 第二阶段：打通「十维投顾投票 -> 组合定权优化器」知行合一闭环与真数据校准（data_loader.py, advisory_engine.py, portfolio_optimizer.py, strategy_bridge.py）
### R3. 第三阶段：强化截图导入「OCR文字 + 昨日收益率数学指纹」双因子精准匹配引擎（portfolio_manager.py, app_gui.py）
### R4. 第四阶段：物理安全红线、测试验收与交付约束
