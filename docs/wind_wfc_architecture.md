# Wind 投顾终端 (WFC) 系统架构与运作机制逆向解析白皮书

本文档详细记录了万得投顾终端（Wind Financial Consultant / Client，简称 **WFC**）的底层进程架构、通信机制、网络拓扑与前端-宿主交互协议。

---

## 一、 终端核心进程拓扑与角色分工

Wind 投顾终端主要由 32 位（x86）原生宿主、容器托管桥接器与多进程 CEF 浏览器集群协同构成：

```
                    +------------------------------------+
                    |        WMain.exe (主窗口/主线程)     |
                    |  - 终端管理总线 / 登录身份验证     |
                    |  - Sky 行情长连接 (114.80.154.36)  |
                    |  - 本地 IPC 监听 (13970-13972 端口)|
                    +-----------------+------------------+
                                      |
                     (本地 TCP / 命名管道 / 共享内存)
                                      |
                    +-----------------v------------------+
                    |        WBox.exe (组件托管容器)      |
                    |  - 插件生命周期管理 / 模块调度     |
                    |  - 辅助总线 (13954-13961 端口)     |
                    +-----------------+------------------+
                                      |
                            (CEF IPC / Mojo 管道)
                                      |
         +----------------------------+----------------------------+
         |                                                         |
+--------v-----------------------+       +-------------------------v---------------------+
| wbrowser.exe (Network/Storage) |       | wbrowser.exe (Renderer 渲染进程集群)         |
|  - 负责 HTTP/HTTPS 协议栈网络  |       |  - 投顾首页、资产配置、AI理财师、基金报告     |
|  - 维护 Cookies / 本地缓存     |       |  - 挂载 window.external.ClientFunc 原生桥接   |
+--------------------------------+       +-----------------------------------------------+
```

### 1. 主进程 `WMain.exe` (PID: 36744)
* **核心职责**：终端核心引擎，负责处理用户登录鉴权、系统配置文件读写（`user.config`）、Sky 行情服务器长连接（`114.80.154.36:443`）、全局热键及托盘驻留。
* **架构特征**：32 位 PE 可执行文件，多线程驱动（约 70+ 个并发线程），提供终端总线与全局状态存储。

### 2. 容器宿主 `WBox.exe` (PID: 27996)
* **核心职责**：独立的应用托管容器与组件沙盒，通过本地环回地址（`127.0.0.1:1395x` 系列端口）与 `WMain.exe` 双向通信，解耦插件崩溃对主进程的影响。
* **架构特征**：拥有 150+ 个工作线程，管理辅助数据缓存与跨组件消息分发。

### 3. Chromium 内嵌浏览器集群 `wbrowser.exe`
* **版本与引擎**：Chromium 109 架构的 CEF (Chromium Embedded Framework) 定制版。
* **多进程模式**：
  * **Network Service**（网络服务进程）：负责所有 HTTPS 远程 API 请求与证书协商。
  * **Storage Service**（存储服务进程）：维护 LevelDB 本地键值库与 Chromium HTTP 缓存（`WFTWebkit109Cache1`）。
  * **GPU Process**（图形加速进程）：Angle / SwiftShader WebGL 渲染。
  * **Renderer Process**（页面渲染进程）：每个独立标签页或 Web 投顾模块对应一个隔离的渲染实例。

---

## 二、 云端网络通信拓扑

终端启动并登录后，与万得云端数据中心建立两条关键网络链路：

| 服务名称 | 目标服务器与端口 | 协议类型 | 承载业务数据 |
| :--- | :--- | :--- | :--- |
| **Sky 行情推送服务** | `114.80.154.36:443` / `shdxsky.wind.com.cn` | 专属加密 TCP 长连接 | A股/港股/基金/期货实时分笔行情、买卖盘口、闪电推送 |
| **Web 业务与投顾网关** | `114.80.154.45:443` / `wx.wind.com.cn` | 标准 HTTPS (REST/JSON) | 基金收益率曲线、AI理财规划、机构货架、要闻研报、CRM |
| **金融资讯与快讯快照** | `news.windin.com` / `snap.windin.com` | HTTP / HTTPS | 24小时全球财经滚动快讯、个股关联要闻、公告事件 |

---

## 三、 CEF 前端与原生 C++ 交互协议 (JS-Bridge)

现代 Wind 投顾终端的前端主要使用 Vue / React 技术栈构建，通过内嵌注入的 `windexternal.js` 与底层 C++ 宿主无缝通信。

### 1. 通信入口：`window.external.ClientFunc(cmdJson)`
前端向终端发起请求的核心机制：
```javascript
let res = null;
if (window.external && window.external.ClientFunc) {
    res = JSON.parse(window.external.ClientFunc(JSON.stringify(cmd)));
}
```

### 2. 核心指令集规范

#### (1) 会话凭证查询：`querydata -> sessionid`
* **前端请求**：`{ "func": "querydata", "isGlobal": "1", "name": "sessionid" }`
* **宿主返回**：`{ "func": "querydata", "name": "sessionid", "value": "596874900559...", "result": "1" }`
* **用途**：前端获取当前终端在万得云端的合法会话密钥，后续所有的 AJAX 请求均在 HTTP 请求头中注入 `wind.sessionid: <value>`。

#### (2) 终端类型与环境查询：`querydata -> apptype / version2`
* **请求**：`{ "func": "querydata", "name": "apptype", "isGlobal": "1" }`
* **返回**：`{ "apptype": "WFC", "result": "1" }`（表明当前运行在投顾终端环境）。

#### (3) 功能鉴权探测：`isauthorized`
* **请求**：`{ "func": "isauthorized", "isGlobal": "1", "functionid": "WFC_APL_FO" }`
* **返回**：`{ "result": "0" }`（0 表示已授权开通该投顾模块）。

#### (4) 宿主控制指令：`command`
* **请求**：`{ "func": "command", "isGlobal": "1", "cmdid": "223", "flat": 0 }`
* **用途**：控制主界面切换新版平铺菜单、弹出独立对话框或调整窗体尺寸。
