# Wind 投顾终端数据分析与智能投顾建议工作区

本工作区专为 **Wind 投顾终端 (WFC)** 量身定制，具备万得客户端运作机制深度逆向解析、全市场标的主字典与离线缓存秒级提取、基金量化多维诊断评分、大类资产配置以及智能投资建议书自动生成等全套能力。

---

## ⚡ 核心能力与特色

1. **终端机制与架构透明化**：
   - 逆向解析了 `WMain.exe` (主进程) + `WBox.exe` (托管外壳) + `wbrowser.exe` (Chromium 109 CEF 浏览器集群) 的多进程协作模式。
   - 完整还原了内嵌 Web 视图与原生宿主之间的 `window.external.ClientFunc(JSON)` 桥接协议规范。
   - 梳理了云端 `114.80.154.45` 投顾网关与 `114.80.154.36` Sky 行情服务的鉴权机制 (`wind.sessionid`)。

2. **多源数据获取双轨制**：
   - **离线主数据直读**：毫秒级解析终端内置的 `FreqUsedCodeFile.codecache` (40MB 全市场 6000+ 标的代码字典)、`sysgrp.dat` (12MB 行业与板块树)、`CNTradeDates.dat` (1990年至今 8750 天法定交易日历)。
   - **CEF 缓存与网络无缝提取**：自动从 Chromium 磁盘块存储中提取真实公募基金净值走势曲线、高管图谱与财经要闻。
   - **云端 REST API 与 32位 WindPy 桥接**：具备对 `pac-web` 接口的访问能力，并提供 32 位子进程桥接规范。

3. **量化投研与建议生成引擎**：
   - **基金量化体检**：计算年化复合收益率、年化波动率、历史最大回撤、夏普比率 (Sharpe Ratio)、卡玛比率 (Calmar Ratio) 等多维指标，输出 0-100 综合雷达评分与星级评定。
   - **智能资产配置**：基于马科维茨现代投资组合与风险平价逻辑，提供保守型、稳健型、平衡型、成长型、进取型五档配置方案。
   - **投顾报告生成**：自动出具符合专业机构合规规范的 Markdown 投资建议书。

---

## 📂 项目结构全景

```
D:\Google\Workspace\Wind\
├── wind_cli.py                        # 统一命令行入口工具 (CLI)
├── requirements.txt                   # 项目依赖清单
├── pyproject.toml                     # Python 包与测试配置
├── README.md                          # 项目说明文档
│
├── docs/                              # 投顾终端逆向与算法白皮书
│   ├── wind_wfc_architecture.md       # 终端进程架构、IPC 与网络拓扑
│   ├── api_and_protocols.md           # 投顾网关 API、Session 鉴权与协议规范
│   ├── local_data_cache_spec.md       # 本地 .codecache, .dat, CEF 缓存规格
│   └── investment_advisory_guide.md   # 投顾分析指标体系与资产配置实操指南
│
├── src/                               # 核心源码包
│   ├── config.py                      # 终端安装路径自适应探测与配置中心
│   ├── core/                          # 核心底层与探针
│   │   ├── terminal_probe.py          # 毫秒级终端进程与内存探针
│   │   ├── session_manager.py         # 活体 SessionID 提取与云端健康自检
│   │   └── client_bridge.py           # window.external.ClientFunc 协议模拟器
│   ├── parsers/                       # 本地离线与网络缓存解析器
│   │   ├── master_dict_parser.py      # 解析 FreqUsedCodeFile.codecache
│   │   ├── sector_parser.py           # 解析 sysgrp.dat
│   │   ├── calendar_parser.py         # 解析 CNTradeDates.dat (交易日计算)
│   │   └── cef_cache_parser.py        # 解析 Chromium 磁盘缓存与 LevelDB
│   ├── api/                           # 投顾 REST API 客户端
│   │   ├── wfc_client.py              # WFC REST 接口客户端与离线双轨自愈
│   │   └── schemas.py                 # Pydantic 数据模型定义
│   ├── sidecar/                       # 32位 WindPy 原生接口跨进程桥接
│   │   ├── windpy_worker.py           # 32位子进程 Worker
│   │   └── windpy_client.py           # 64位客户端 RPC 代理
│   ├── analysis/                      # 量化模型与基金诊断
│   │   ├── metrics.py                 # 年化收益/波动/最大回撤/夏普/卡玛/Alpha
│   │   ├── fund_analyzer.py           # 基金多维评分卡与批量排行榜
│   │   └── asset_allocation.py        # 大类资产配置优化与回测预估
│   └── advisory/                      # 投资建议书与报告输出
│       ├── rules_engine.py            # 适当性矩阵与产品匹配规则引擎
│       └── report_generator.py        # Markdown 与富文本控制台建议书生成器
│
├── scripts/                           # 实用独立脚本
│   ├── doctor.py                      # 一键体检终端与环境健康状态
│   ├── export_master_dict.py          # 一键导出全市场标的表至 CSV
│   ├── inspect_fund.py                # 快速量化诊断基金并出具配置建议
│   └── sync_terminal_cache.py         # 一键同步并归档终端最新网络缓存
│
├── data/                              # 数据落地存储目录
│   ├── master/                        # 证券主数据表 (securities.csv)
│   ├── cache/                         # 离线解析的基金历史收益率与快讯
│   └── reports/                       # 生成的投资建议书 (Markdown)
│
└── tests/                             # 自动化单元测试套件 (9项全通)
    ├── test_doctor.py
    ├── test_metrics.py
    └── test_parsers.py
```

---

## 🚀 快速上手指南

### 1. 环境准备与体检
```bash
# 运行环境一键体检 (自动探测 Wind 运行状态、离线数据与会话凭证)
python wind_cli.py doctor
```

### 2. 全市场证券标的检索
```bash
# 支持股票代码、中文简称或拼音首字母检索
python wind_cli.py search 茅台
python wind_cli.py search 000001
python wind_cli.py search PAYH
```

### 3. 单只基金量化深度诊断
```bash
# 对指定基金进行历史年化、波动率、最大回撤与夏普比率综合评分
python wind_cli.py analyze 002910.OF
```

### 4. 生成专业投资建议书
```bash
# 支持可选风险等级: 保守型 / 稳健型 / 平衡型 / 成长型 / 进取型
python wind_cli.py advice --risk 平衡型

# 输出建议书将自动保存至: data/reports/investment_advice_平衡型.md
```

### 5. 投资组合全景分析与现代资产配置优化
```bash
# 1. 基于投顾标准模板分析（支持: 保守型/稳健型/平衡型/成长型/进取型），包含优化与研报导出
python wind_cli.py portfolio --template 平衡型 --optimize --export

# 2. 定制任意权重多资产组合回测（支持基金、ETF、指数与固收）
python wind_cli.py portfolio --weights "000300.SH:0.4,000905.SH:0.2,CBA00101.CS:0.4" --benchmark 000300.SH --rebalance quarterly

# 3. 求解现代资产组合优化前沿配置（最大夏普比率、全局最小方差、风险平价/ERC）
python wind_cli.py portfolio --template 成长型 --optimize
```

### 6. 导出全市场证券代码表
```bash
# 将 Wind 内置的 6000+ A股股票与基金代码表导出为结构化 CSV
python wind_cli.py export-dict
```

### 7. 同步终端缓存数据
```bash
# 提取终端最近加载的基金业绩走势和财经要闻
python wind_cli.py sync-cache
```

### 8. 运行自动化测试
```bash
pytest -v
```
