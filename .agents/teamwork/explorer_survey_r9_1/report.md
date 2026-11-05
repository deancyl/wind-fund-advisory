# Phase 0 技术调研报告：R1 与 R2 多账本体系设计与全站贯通方案

**调研负责人**：teamwork_explorer (`explorer_survey_r9_1`)  
**任务目标**：针对需求规范中的 R1（MultiLedgerManager 底层存储与管理实现）与 R2（多账本全站级动态热装配与跨 Tab 贯通），开展只读代码审计、系统架构设计、接口契约定义与数据流向追踪。

---

## 一、 执行概要 (Executive Summary)

本调研对当前 Wind 投顾系统的两大核心模块——组合管理底层 `AGY2_FundAdvisory/portfolio_manager.py` 和可视化主程序 `AGY2_FundAdvisory/app_gui.py` 进行了全面审计。

核心结论如下：
1. **R1 底层可行性与关键暗礁**：
   - 当前 `PortfolioManager` 初始化接收 `db_path="portfolio_state.db"` 和 `ledger_json_path="portfolio_ledger.json"`（注意：入参名称为 `ledger_json_path` 而非 `ledger_file`，需提供平滑别名兼容）。
   - **关键防踩踏陷阱**：`PortfolioManager.save_state()` 采用“SQLite + JSON 镜像”双轨持久化。若多账本仅区分 JSON 路径而共享同一个 `portfolio_state.db`，在保存时会执行 `DELETE FROM holdings`，导致不同账本在 SQLite 层面发生物理互踩冲刷！因此，必须为每个新建/克隆账本配套独立的 SQLite 文件（`data/ledgers/<ledger_id>.db`）。
   - 主实盘账本必须保持为根目录 `portfolio_ledger.json`（对应 `portfolio_state.db`），`MultiLedgerManager` 必须对其施加物理删除保护，确保现有所有单元测试与无参 `PortfolioManager()` 100% 保持现状零感知通过。
2. **R2 跨 Tab 贯通可行性与单源同真**：
   - `app_gui.py` 在首屏第 1366 行通过 `st.session_state.pm = PortfolioManager()` 完成单例绑定，全局看板、右翼预警哨、Tab 2、Tab 3 与 Tab 4 均直接或间接读取 `st.session_state.pm`。
   - 通过在 `st.session_state` 中引入 `active_ledger_id` 与 `MultiLedgerManager`，账本切换可瞬间完成 `st.session_state.pm` 实例热替换，并联动同步 `active_tier_val`、清空 `tab2_diag_cache` / `tab2_rebal_cache`，即可实现全站 100% 动态刷新。
   - Tab 2 顶部多账本管理吧台（选择器、新建、克隆、管理 Popover、沙盒警告条）与 Tab 1 步骤三底座保存双轨（覆盖 vs 另存为新账本）具备极清晰的 DOM 与组件挂载点。

---

## 二、 R1: MultiLedgerManager 底层存储与管理实现深度调研

### 2.1 `portfolio_manager.py` 底层机制与代码引用审计

在 `AGY2_FundAdvisory/portfolio_manager.py` 中：
- **初始化签名（第 2387-2406 行）**：
  ```python
  def __init__(
      self,
      db_path: Union[str, Path] = "portfolio_state.db",
      ledger_json_path: Union[str, Path] = "portfolio_ledger.json",
      storage_file: Optional[Union[str, Path]] = None
  ):
  ```
  - **现有入参**：`ledger_json_path`，**不存在** `ledger_file` 形参。
  - **建议改进**：在 `__init__` 中新增 `ledger_file: Optional[Union[str, Path]] = None` 与 `ledger_id: str = "main_live"`，若 `ledger_file is not None` 则自动赋值给 `ledger_json_path`；若 `ledger_json_path != "portfolio_ledger.json"` 且 `db_path` 未显式覆盖，自动派生 `db_path = Path(ledger_json_path).with_suffix(".db")`。
- **持久化保存 `save_state()`（第 2717-2808 行）**：
  - 核心逻辑：
    1. 提取当前持仓、批次、在途订单与元数据；
    2. 将当前快照压入 `self.snapshot_stack` 及 SQLite 表 `portfolio_snapshots`；
    3. 清空并重写 SQLite 表（`DELETE FROM holdings`, `holding_batches`, `pending_orders`, `portfolio_meta`）；
    4. 若 `not getattr(self, '_is_memory', False)`，将全量 JSON 导出写入 `self.ledger_json_path`。
  - **发现的暗礁**：若 `db_path == ":memory:"`，代码会跳过写入 JSON！因此持久化沙盒必须使用独立的磁盘 SQLite 文件。
- **状态恢复 `load_state()`（第 2809-2896 行）**：
  - 优先读取 `self.ledger_json_path`（若存在且非空则解析 JSON 导入持仓与批次），并从关联的 SQLite 读取历史 Undo 快照栈。
  - 若 JSON 不存在，则回退从 SQLite 恢复。

### 2.2 存储目录与元数据索引 Schema 规范

- **目录结构**：
  ```
  d:\Google\Workspace\Wind\
  ├── portfolio_ledger.json          # 主实盘账本 (id="main_live", 物理受保护)
  ├── portfolio_state.db            # 主实盘 SQLite 数据库
  └── data\
      ├── ledgers_index.json        # 账本元数据中央索引
      └── ledgers\                  # 所有新建/克隆账本存储目录
          ├── sandbox_20261105_001.json
          ├── sandbox_20261105_001.db
          ├── family_edu_fund.json
          └── family_edu_fund.db
  ```
- **`data/ledgers_index.json` 数据模式 (Schema)**：
  ```json
  {
    "version": "1.0",
    "active_ledger_id": "main_live",
    "ledgers": [
      {
        "id": "main_live",
        "name": "主实盘账本",
        "type": "live",
        "file": "portfolio_ledger.json",
        "db_file": "portfolio_state.db",
        "default_tier": "C3",
        "is_protected": true,
        "created_at": "2026-11-01 00:00:00",
        "updated_at": "2026-11-05 14:00:00",
        "description": "主实盘生产交易账本 (受物理写保护，禁止删除)"
      },
      {
        "id": "sandbox_20261105_a1b2",
        "name": "激进进攻演练沙盒",
        "type": "sandbox",
        "file": "data/ledgers/sandbox_20261105_a1b2.json",
        "db_file": "data/ledgers/sandbox_20261105_a1b2.db",
        "default_tier": "C4",
        "is_protected": false,
        "created_at": "2026-11-05 14:10:00",
        "updated_at": "2026-11-05 14:10:00",
        "description": "独立沙盒环境"
      }
    ]
  }
  ```

### 2.3 `MultiLedgerManager` 放置位置与架构建议

- **放置位置**：推荐创建独立专职模块 `AGY2_FundAdvisory/multi_ledger_manager.py`，同时在 `AGY2_FundAdvisory/portfolio_manager.py` 底部注入：
  ```python
  from multi_ledger_manager import MultiLedgerManager
  ```
  **理由**：
  1. `portfolio_manager.py` 已达 7,442 行，继续追加大段账本管理代码会加重代码审查与维护负担；
  2. 独立文件符合单一职责原则，测试针对性强（方便编写 `tests/test_multi_ledger_manager.py`）；
  3. 双向 re-export 确保既能 `from multi_ledger_manager import MultiLedgerManager`，也能 `from portfolio_manager import MultiLedgerManager`。

### 2.4 `MultiLedgerManager` 接口契约定义

```python
class MultiLedgerManager:
    """多账本/多投资组合生命周期与资产聚合管理引擎"""

    def __init__(
        self,
        workspace_root: Optional[Union[str, Path]] = None,
        index_file: Optional[Union[str, Path]] = None,
        ledgers_dir: Optional[Union[str, Path]] = None
    ):
        ...

    def list_ledgers(self) -> List[Dict[str, Any]]:
        """获取全量账本元数据列表，确保 main_live 始终置顶且受物理保护"""
        ...

    def get_ledger_meta(self, ledger_id: str) -> Optional[Dict[str, Any]]:
        """按 ID 查询指定账本的元数据"""
        ...

    def get_active_ledger_id(self) -> str:
        """获取当前激活的账本 ID，默认为 main_live"""
        ...

    def set_active_ledger_id(self, ledger_id: str) -> bool:
        """设置当前激活账本 ID 并持久化至 ledgers_index.json"""
        ...

    def create_ledger(
        self,
        name: str,
        base_cash: float = 100000.0,
        ledger_type: str = "sandbox",     # "live" | "sandbox" | "family"
        default_tier: str = "C3",          # "C1" ~ "C5"
        description: str = "",
        initial_holdings: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        创建全新独立账本：
        1. 分配唯一 ledger_id (如 sandbox_20261105_xxxx)
        2. 在 data/ledgers/ 生成初始 json 与对应 db
        3. 写入账本元数据并更新 data/ledgers_index.json
        返回新建账本的元数据字典
        """
        ...

    def clone_ledger(
        self,
        src_id: str,
        target_name: str,
        ledger_type: Optional[str] = "sandbox",
        default_tier: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        深拷贝克隆现有账本副本：
        1. 读取源账本 JSON 运行态（持仓、批次、在途单、现金）
        2. 生成新 target_id 并深拷贝至 data/ledgers/<target_id>.json
        3. 建立全新独立 SQLite 数据库
        4. 追加索引元数据并返回
        """
        ...

    def rename_ledger(self, ledger_id: str, new_name: str) -> bool:
        """
        重命名指定账本：
        若 ledger_id == 'main_live'，严禁修改内部主键，但可允许更新 display_name，或严格保持 '主实盘账本'
        """
        ...

    def delete_ledger(self, ledger_id: str) -> bool:
        """
        删除账本：
        【物理防护红线】：若 ledger_id == 'main_live'，强制抛出 ValueError 或拦截，坚决禁止删除！
        对于普通账本，物理删除其 json 和 db 文件，并从索引清理
        """
        ...

    def get_portfolio_manager(self, ledger_id: str) -> "PortfolioManager":
        """
        工厂方法：装配并返回绑定该账本独立存储路径的 PortfolioManager 实例
        - main_live -> 绑定 portfolio_state.db 与 portfolio_ledger.json
        - 其他 -> 绑定 data/ledgers/<ledger_id>.db 与 data/ledgers/<ledger_id>.json
        """
        ...

    def get_all_ledgers_summary(self) -> Dict[str, Any]:
        """
        汇总全家庭/全账本维度的资产全景：
        返回字段：
        - total_equity: 全家庭汇总总资产
        - total_floating_pnl: 全账本汇总总浮盈
        - total_market_value: 全账本汇总市值
        - total_holdings_count: 全账本持仓基金总只数
        - ledgers: 包含每个账本细项指标的列表（名称、类型、资产、浮盈、标的数、更新时间）
        - df: 适配 Streamlit 直接渲染的宽表 DataFrame
        """
        ...
```

---

## 三、 R2: 多账本全站级动态热装配与跨 Tab 贯通深度调研

### 3.1 `app_gui.py` 初始化与激活账本生命周期

- **现状分析**：
  - `app_gui.py` 第 1365-1368 行：
    ```python
    if "pm" not in st.session_state:
        st.session_state.pm = PortfolioManager()
    pm: PortfolioManager = st.session_state.pm
    ```
- **改造方案**：
  - 引入 `MultiLedgerManager` 并在首屏完成状态机注册：
    ```python
    if "mlm" not in st.session_state:
        st.session_state.mlm = MultiLedgerManager()
    if "active_ledger_id" not in st.session_state:
        st.session_state.active_ledger_id = st.session_state.mlm.get_active_ledger_id()
    
    # 动态装配或同步当前激活的 pm 实例
    _cur_id = st.session_state.active_ledger_id
    if "pm" not in st.session_state or getattr(st.session_state.pm, "ledger_id", None) != _cur_id:
        st.session_state.pm = st.session_state.mlm.get_portfolio_manager(_cur_id)
    
    pm: PortfolioManager = st.session_state.pm
    ```

### 3.2 账本切换的六大下游连锁反应全景追踪

当用户在界面切换账本（例如从 `main_live` 切换至 `sandbox_xxx`）时，执行标准热切换流程：
```python
def switch_active_ledger(target_ledger_id: str):
    mlm = st.session_state.mlm
    # 1. 保存旧账本运行态
    if "pm" in st.session_state and st.session_state.pm:
        st.session_state.pm.save_state(record_snapshot=True)
    
    # 2. 切换 active_ledger_id 并持久化
    st.session_state.active_ledger_id = target_ledger_id
    mlm.set_active_ledger_id(target_ledger_id)
    
    # 3. 热装配全新 pm 实例
    new_pm = mlm.get_portfolio_manager(target_ledger_id)
    st.session_state.pm = new_pm
    
    # 4. 同步默认风险档位 default_tier -> active_tier_val
    meta = mlm.get_ledger_meta(target_ledger_id) or {}
    st.session_state.active_tier_val = meta.get("default_tier", "C3")
    
    # 5. 彻底清空 Tab 2 诊断与调仓计算缓存
    st.session_state.tab2_diag_cache = None
    st.session_state.tab2_rebal_cache = None
    st.session_state.tab2_diagnosed = False
    st.session_state.tab2_rebalanced = False
    st.session_state.tab2_trigger_diagnose = False
    st.session_state.tab2_trigger_rebalance = False
    
    # 6. 触发全局平滑重载
    st.rerun()
```

各业务下游响应机制审计：
1. **全局 `pm` 实例**：`st.session_state.pm` 切换为目标账本实例。
2. **顶部第 4 张大卡片「总资产与今日预估」（第 1813-1833 行）**：
   - 依赖变量：`total_cur_equity`, `pm.available_cash`, `pm.in_transit_cash`, `_t2_cost`, `est_pnl`, `_t2_pnl`。
   - 这些变量在第 1397-1444 行完全基于 `pm.total_equity`、`pm.calculate_intraday_pnl()` 和 `pm.holdings` 计算。当 `pm` 热替换后，重新执行第 1397 行，卡片数值 100% 自动对齐新账本！
3. **右翼「主动风险预警哨」`ActiveRiskSentry`（第 2008-2046 行）**：
   - 传入参数：`pm_instance.holdings`（即 `pm.holdings`）。
   - 实例热替换后，主动风险哨扫描的正是新账本持仓，锁定与预警标的完全与新账本一致。
4. **Tab 2「持仓账本与调仓」（第 3254-4770 行）**：
   - 持仓账本表格读取 `pm.holdings` 与 `pm.available_cash`；
   - 演示组合、撤销上次修改、添加/修改/删除基金均针对新账本独立生效；
   - 清空 `tab2_diag_cache` 和 `tab2_rebal_cache` 后，工作流步骤指示器重置为步骤一，引导用户为新账本启动全新 AI 诊断与调仓模拟。
5. **Tab 3「组合回测」中的「当前实盘持仓」（第 4806-4826 行）**：
   - 核心代码：
     ```python
     if pm.holdings:
         tot_h_val = sum(h.market_value for h in pm.holdings.values())
         if tot_h_val > 0:
             hold_w = {c: round(h.market_value / tot_h_val, 4) for c, h in pm.holdings.items()}
     ```
   - 切换账本后，Tab 3 选定「当前实盘持仓」回测对象时，自动按新账本权重回测。
6. **Tab 4「穿透工具箱」中的「当前实盘持仓」（第 5190-5194 行）**：
   - 核心代码：
     ```python
     if sel_tb_target == "当前实盘持仓":
         if pm.holdings:
             active_examine_holdings = dict(pm.holdings)
     ```
   - 切换账本后，Tab 4 行业穿透、前十大重仓穿透与聪明钱巡检自动切换至新账本底层资产。

### 3.3 Tab 2 顶部多账本管理吧台与 Popover 界面规范

在 Tab 2「步骤一：持仓账本」标题正下方（第 3326 行），新增单行多账本管理吧台：
- **布局划分**：
  ```python
  col_led_sel, col_led_new, col_led_clone, col_led_mgr = st.columns([4.2, 1.8, 1.8, 2.2])
  ```
- **1. 当前账本选择器（`col_led_sel`）**：
  - 选项展示格式：`f"{icon} {name} (¥{tot_equity:,.0f})"`
    - 实盘：`🟢 [实盘] 主实盘账本 (¥191,445)`
    - 沙盒：`🧪 [沙盒] 激进进攻演练沙盒 (¥100,000)`
    - 家庭：`👨‍👩‍👧 [家庭] 父母养老专项金 (¥250,000)`
  - 监听选择变更，若与 `active_ledger_id` 不同则触发 `switch_active_ledger()`。
- **2. 【➕ 新建账本】Popover（`col_led_new`）**：
  - 控件项：
    - 文本输入：`账本名称`（如“子女教育金”）
    - 数值输入：`初始现金`（缺省 ¥100,000.0）
    - 单选/下拉：`账本类型`（沙盒 / 实盘 / 家庭专项）
    - 下拉选择：`专属风险档位`（C1~C5，缺省 C3）
    - 提交按钮：`确认创建并切换`
- **3. 【📋 克隆当前副本】Popover（`col_led_clone`）**：
  - 控件项：
    - 文本输入：`副本名称`（缺省 `f"{cur_name} - 副本"`）
    - 单选/下拉：`账本类型`（缺省 `sandbox` 沙盒）
    - 提交按钮：`一键克隆并切换`
- **4. 【⚙️ 账本管理】Popover（`col_led_mgr`）**：
  - 若当前为 `main_live`：展示 `🛡️ 主实盘账本受系统物理保护，禁止删除`；
  - 若为其他账本：
    - 文本输入与按钮：`重命名当前账本`
    - 危险按钮：`🗑️ 删除当前账本`（带确认弹窗/复选框，删除后自动回退至 `main_live`）
  - 折叠展开区：`👨‍👩‍👧‍👦 查看全账本家庭资产汇总表`
    - 调用 `mlm.get_all_ledgers_summary()` 展示全家庭总资产、总浮盈、总标的数，并用 `st.dataframe` 呈现账本汇总明细表。
- **5. 沙盒隔离黄色醒目提示条**：
  - 若当前账本类型为 `sandbox`，在吧台下方立刻渲染：
    ```html
    <div style="background: rgba(234, 179, 8, 0.15); border-left: 4px solid #eab308; padding: 10px 14px; border-radius: 6px; margin-bottom: 12px; font-size: 13px; color: var(--text-primary);">
        🧪 <b>当前为独立沙盒环境</b>：任何调仓、录基演练与资产变动均隔离存储于独立账本，绝不影响主实盘生产数据。
    </div>
    ```

### 3.4 Tab 1 步骤三底座保存双轨机制（覆盖 vs 另存为）

在 `app_gui.py` 第 3201-3220 行（Tab 1 步骤三执行单下方），目前仅有一个「🚀 设为初始持仓」按钮。
改造为双轨保护布局：
- **选项 A：覆盖写入当前激活账本**：
  - 按钮文案：`🚀 覆盖写入当前账本 (【{active_ledger_name}】)`
  - 若当前账本为 `main_live`，提示 Secondary 警示确认，防止用户失误把主实盘持仓冲刷掉。
- **选项 B：🆕 另存为全新独立账本**（Popover 交互）：
  - 弹出输入框：`输入新账本名称`（如“2026新春定投组合”）
  - 下拉选择：`账本类型`（沙盒/家庭专项/实盘）与 `专属风险档位`
  - 按钮：`一键创建并写入此建仓方案`
  - 点击后：
    1. 调用 `mlm.create_ledger(name, base_cash=plan_capital, ...)`
    2. 获取新实例 `new_pm`，调用 `new_pm.apply_zero_start_blueprint(blueprint, ...)`
    3. 切换 `st.session_state.active_ledger_id = new_id` 与 `st.session_state.pm = new_pm`
    4. 同步 `active_tier_val` 并提示气球特效，无损过渡。

---

## 四、 核心代码差异与实施蓝图对比 (Before vs After)

### 4.1 `PortfolioManager.__init__` 参数兼容性对比

```python
# ==================== BEFORE ====================
class PortfolioManager:
    def __init__(
        self,
        db_path: Union[str, Path] = "portfolio_state.db",
        ledger_json_path: Union[str, Path] = "portfolio_ledger.json",
        storage_file: Optional[Union[str, Path]] = None
    ):
        ...
        self.ledger_json_path = Path(ledger_json_path)

# ==================== AFTER ====================
class PortfolioManager:
    def __init__(
        self,
        db_path: Optional[Union[str, Path]] = None,
        ledger_json_path: Union[str, Path] = "portfolio_ledger.json",
        storage_file: Optional[Union[str, Path]] = None,
        ledger_file: Optional[Union[str, Path]] = None,     # 新增平滑兼容别名
        ledger_id: str = "main_live"                         # 新增账本标识
    ):
        if ledger_file is not None:
            ledger_json_path = ledger_file
        if storage_file is not None:
            db_path = storage_file

        self.ledger_id = str(ledger_id)
        self.ledger_json_path = Path(ledger_json_path)

        # 智能 SQLite 隔离防踩踏：若未显式指定 db_path 且非主实盘账本，自动绑定专属 db
        if db_path is None:
            if str(self.ledger_json_path.name) == "portfolio_ledger.json":
                db_path = "portfolio_state.db"
            else:
                db_path = self.ledger_json_path.with_suffix(".db")

        if str(db_path) == ":memory:":
            self._is_memory = True
            ...
```

### 4.2 `MultiLedgerManager` 关键实现伪代码

```python
class MultiLedgerManager:
    def __init__(self, workspace_root=None, index_file=None, ledgers_dir=None):
        self.root = Path(workspace_root) if workspace_root else WORKSPACE_ROOT
        self.ledgers_dir = Path(ledgers_dir) if ledgers_dir else (self.root / "data" / "ledgers")
        self.index_file = Path(index_file) if index_file else (self.root / "data" / "ledgers_index.json")
        self.main_file = self.root / "portfolio_ledger.json"
        self.main_db = self.root / "portfolio_state.db"
        
        self.ledgers_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_index_initialized()

    def _ensure_index_initialized(self):
        if not self.index_file.exists():
            init_data = {
                "version": "1.0",
                "active_ledger_id": "main_live",
                "ledgers": [self._get_default_main_meta()]
            }
            self._write_index(init_data)
        else:
            # 校验并补齐 main_live
            data = self._read_index()
            has_main = any(l.get("id") == "main_live" for l in data.get("ledgers", []))
            if not has_main:
                data.setdefault("ledgers", []).insert(0, self._get_default_main_meta())
                self._write_index(data)

    def delete_ledger(self, ledger_id: str) -> bool:
        if ledger_id == "main_live":
            raise ValueError("主实盘账本受物理保护，禁止删除！")
        data = self._read_index()
        ledgers = data.get("ledgers", [])
        target = next((l for l in ledgers if l["id"] == ledger_id), None)
        if not target:
            return False
        
        # 物理清理文件
        f_path = self.root / target.get("file", "")
        db_path = self.root / target.get("db_file", "")
        if f_path.exists() and f_path != self.main_file:
            f_path.unlink()
        if db_path.exists() and db_path != self.main_db:
            db_path.unlink()

        data["ledgers"] = [l for l in ledgers if l["id"] != ledger_id]
        if data.get("active_ledger_id") == ledger_id:
            data["active_ledger_id"] = "main_live"
        self._write_index(data)
        return True
```

---

## 五、 专项防作弊测试 C（多账本隔离检验）契约对齐

针对规范中要求的：
> 专项防作弊测试 C（多账本隔离与全站联动检验）：使用 MultiLedgerManager 创建沙盒账本、克隆账本、修改沙盒持仓，断言主实盘账本完好无损，且删除保护生效。

本设计完全满足上述断言要求：
1. **沙盒创建与克隆**：文件独立落盘于 `data/ledgers/<id>.json`，不影响根目录 `portfolio_ledger.json`；
2. **修改沙盒持仓**：沙盒 `pm` 写入独立的 `data/ledgers/<id>.json` 与 `<id>.db`，主实盘 SHA256 与数据字段保持 100% 不变；
3. **删除保护生效**：调用 `delete_ledger("main_live")` 时严格抛出异常并拒绝执行；
4. **家庭全景聚合**：`get_all_ledgers_summary()` 正确汇总全账本资产、浮盈与标的数。

---

## 六、 调研结论与实施建议

1. **R1 建议实施步骤**：
   - 在 `AGY2_FundAdvisory/multi_ledger_manager.py` 完整实现 `MultiLedgerManager`；
   - 在 `AGY2_FundAdvisory/portfolio_manager.py` 支持 `ledger_file` 别名与自动派生 `db_path` 防踩踏，并导出 `MultiLedgerManager`；
   - 编写单元测试 `tests/test_multi_ledger_manager.py`，完整覆盖增删改查、克隆、删除保护与汇总。
2. **R2 建议实施步骤**：
   - 在 `app_gui.py` 顶部绑定 `st.session_state.active_ledger_id` 与 `MultiLedgerManager`；
   - 在 Tab 2「步骤一：持仓账本」顶部挂载单行多账本管理吧台与沙盒黄色隔离警示框；
   - 在 Tab 1 步骤三实现保存双轨选项（覆盖当前账本 vs 另存为新账本）；
   - 运行 AppTest 验证浅色与深色主题无白屏报错。
