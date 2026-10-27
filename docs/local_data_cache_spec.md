# Wind 终端本地离线数据与缓存规格说明书

Wind 投顾终端在本地磁盘驻留了丰富的底层主数据、分类树、交易日历以及 Chromium 网页缓存。当终端处于离线或网络断开状态时，本工作区解析器可 100% 纯本地离线解析这些数据。

---

## 一、 本地核心数据文件清单

| 文件路径 | 大小 | 编码格式 | 核心内容 |
| :--- | :---: | :--- | :--- |
| `tmp\FreqUsedCodeFile.codecache` | ~40.0 MB | UTF-16LE | 全市场 6000+ A股股票、公募基金、ETF、指数代码与中英文简称字典 |
| `tmp\sysgrp.dat` | ~12.1 MB | UTF-16LE | 官方行业与板块层级分类体系（全部A股、市场类、申万/万得行业） |
| `tmp\sectorindex.cache` | ~30.8 MB | 二进制整数倒排表 | 板块代码到标的证券偏移的倒排索引 |
| `tmp\CWboxTool\...\CNTradeDates.dat` | ~87 KB | ASCII 文本 | 1990年至今每一个 A 股法定交易日（YYYYMMDD 换行分隔） |
| `tmp\CWboxTool\...\AhStockList.dat` | ~4 KB | GB18030 键值对 | AH 两地上市股票代码映射表（如 `000002.SZ=2202.HK`） |
| `tmp\CWboxTool\...\RelatedSymbols.dat`| ~300 KB| 逗号分隔文本 | 跨市场关联证券及比对权重 |
| `tmp\WFTWebkit109Cache1\Cache\Cache_Data` | 多文件 | Chromium 块存储 | 包含公募基金业绩走势图、财经要闻快讯、企业图谱数据 |
| `tmp\WFTWebkit109Cache1\Local Storage` | LevelDB | Chromium Storage | 缓存了用户历史提问记录与部分图表配置 |

---

## 二、 核心文件结构逆向解析

### 1. `FreqUsedCodeFile.codecache` 结构
* **编码**：UTF-16LE
* **记录字段**：
  * `[6位代码].[2位市场后缀]` (例如 `000001.SZ`)
  * `\x00` (空字符截断)
  * `[标的中标简称]` (例如 `平安银行`)
  * `\x00`
  * `[拼音首字母缩写]` (例如 `PAYH`)
  * `\x00`
  * `[英文缩写]` (例如 `PAB`)
  * `\x00`
  * `[市场类型/币种]` (例如 `A`, `CNY`, `T0002`, `1|1|1|1|1|1`)

### 2. `CNTradeDates.dat` 结构
* **编码**：纯文本 ASCII
* **格式**：按时间升序排列的 8 位年月日数字，`\r\n` 分隔：
  ```
  19901219
  19901220
  ...
  20261026
  20261027
  ```
* **功能支持**：
  * 是否为交易日精准秒判：`calendar.is_trade_day("20261027")`
  * 交易日平移推算：`calendar.get_offset_trade_day("20261027", -20)`
  * 区间有效交易日统计：`calendar.count_trade_days("20240101", "20261027")`

### 3. Chromium Cache 文件解析说明
* Chromium 109 针对大于 16KB 的 HTTP 响应采用外部流文件命名（`f_xxxxxx`）。
* 文件头部通常为 HTTP 响应正文（部分使用 gzip 压缩，可通过 `1f 8b` 魔数识别并自动解压）。
* 文件末尾 1KB 存储 Chromium 格式的请求元数据（包括请求 URL、请求方法与响应头信息）。
* 工作区内自带的 `CEFCacheParser` 能自动提取所有符合 `{"data":` 结构的基金走势，并组装为 Pandas DataFrame。
