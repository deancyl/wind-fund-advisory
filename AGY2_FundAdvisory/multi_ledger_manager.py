"""
多账本与多组合资产聚合管理引擎 (AGY2_FundAdvisory/multi_ledger_manager.py)
核心功能：
1. 管理 data/ledgers_index.json 与 data/ledgers/ 目录生命周期；
2. 主实盘账本 (main_live, portfolio_ledger.json, portfolio_state.db) 物理写保护，严禁删除；
3. 新建与克隆账本落盘于 data/ledgers/<id>.json 并配对专属 SQLite data/ledgers/<id>.db，物理隔离防冲刷；
4. 全账本家庭资产汇总统计 (get_all_ledgers_summary)。
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import json
import uuid
import pandas as pd

CURRENT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = CURRENT_DIR.parent if CURRENT_DIR.name == "AGY2_FundAdvisory" else CURRENT_DIR


class MultiLedgerManager:
    """多账本/多投资组合生命周期与资产聚合管理引擎"""

    _instance: Optional["MultiLedgerManager"] = None
    _recently_created_lids: set = set()

    @classmethod
    def get_instance(cls, workspace_root: Optional[Union[str, Path]] = None) -> "MultiLedgerManager":
        """获取或创建全局单例"""
        if cls._instance is None:
            cls._instance = cls(workspace_root=workspace_root)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """重置单例（用于单元测试）"""
        cls._instance = None

    def __init__(
        self,
        workspace_root: Optional[Union[str, Path]] = None,
        index_file: Optional[Union[str, Path]] = None,
        ledgers_dir: Optional[Union[str, Path]] = None
    ):
        self.root = Path(workspace_root).resolve() if workspace_root else WORKSPACE_ROOT
        self.ledgers_dir = Path(ledgers_dir).resolve() if ledgers_dir else (self.root / "data" / "ledgers")
        self.index_file = Path(index_file).resolve() if index_file else (self.root / "data" / "ledgers_index.json")
        self.main_file = self.root / "portfolio_ledger.json"
        self.main_db = self.root / "portfolio_state.db"

        self.ledgers_dir.mkdir(parents=True, exist_ok=True)
        self.index_file.parent.mkdir(parents=True, exist_ok=True)

        self._pm_cache: Dict[str, Any] = {}
        self._ensure_index_initialized()

    def _get_default_main_meta(self) -> Dict[str, Any]:
        """主实盘账本默认元数据"""
        return {
            "id": "main_live",
            "name": "主实盘账本",
            "type": "live",
            "file": "portfolio_ledger.json",
            "db_file": "portfolio_state.db",
            "default_tier": "C3",
            "is_protected": True,
            "created_at": "2026-11-01 00:00:00",
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "description": "主实盘生产交易账本 (受物理写保护，禁止删除)"
        }

    def _read_index(self) -> Dict[str, Any]:
        """读取 ledgers_index.json"""
        if not self.index_file.exists():
            return {"version": "1.0", "active_ledger_id": "main_live", "ledgers": [self._get_default_main_meta()]}
        try:
            with open(self.index_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                data = {}
            if "ledgers" not in data or not isinstance(data["ledgers"], list):
                data["ledgers"] = [self._get_default_main_meta()]
            if "active_ledger_id" not in data:
                data["active_ledger_id"] = "main_live"
            return data
        except Exception:
            return {"version": "1.0", "active_ledger_id": "main_live", "ledgers": [self._get_default_main_meta()]}

    def _write_index(self, data: Dict[str, Any]) -> None:
        """安全写入 ledgers_index.json"""
        self.index_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _resolve_unique_name(self, name: str, exclude_id: Optional[str] = None) -> str:
        """解析并确保账本名称全局唯一，并严禁非主实盘账本冒充'主实盘账本'"""
        raw_name = str(name or "").strip() or "未命名账本"
        if raw_name in ("主实盘账本", "[实盘] 主实盘账本"):
            raw_name = "副实盘账本"

        existing = {
            str(l.get("name", "")).strip()
            for l in self._read_index().get("ledgers", [])
            if l.get("id") != exclude_id
        }
        if raw_name not in existing:
            return raw_name
        idx = 2
        while f"{raw_name} ({idx})" in existing:
            idx += 1
        return f"{raw_name} ({idx})"

    def _ensure_index_initialized(self) -> None:
        """确保索引文件与主实盘账本元数据存在且合规，并自动清洗幽灵重名及测试账本残留"""
        data = self._read_index()
        ledgers = data.get("ledgers", [])
        cleaned_ledgers = []
        main_item = None

        for l in ledgers:
            lid = str(l.get("id", "")).strip()
            lname = str(l.get("name", "")).strip()

            if lid == "main_live":
                l["name"] = "主实盘账本"
                l["is_protected"] = True
                l["type"] = "live"
                l["file"] = "portfolio_ledger.json"
                l["db_file"] = "portfolio_state.db"
                main_item = l
                continue

            # 幽灵残留与测试账本清洗判定 (含重名主实盘账本、历史测试/AppTest/压力测试残留)
            # 规则：主实盘名称受绝对保护，任何非 main_live 但名为“主实盘账本”者必须无条件物理清除；
            # 历史遗留的测试/压力测试账本（非当前活跃创建）自动清理，合法用户沙盒账本正常保留。
            # 精确时间戳甄别：区分历史遗留测试垃圾与当前正在运行的测试账本
            now_dt = datetime.now()
            try:
                c_dt = datetime.strptime(str(l.get("created_at", "")), "%Y-%m-%d %H:%M:%S")
                is_stale = (now_dt - c_dt).total_seconds() > 45.0
            except Exception:
                is_stale = True

            is_recent = (not is_stale) or (lid in MultiLedgerManager._recently_created_lids)
            is_ghost = (
                (lname in ("主实盘账本", "[实盘] 主实盘账本") or lid.startswith("main_live_")) or
                (not is_recent and ("测试" in lname or "apptest" in lname.lower() or "压力测试" in lname or lid.startswith("test_")))
            )

            if is_ghost:
                # 物理删除幽灵文件
                try:
                    f_path = (self.root / l.get("file", "")).resolve()
                    db_path = (self.root / l.get("db_file", "")).resolve()
                    if f_path.exists() and f_path != self.main_file.resolve():
                        f_path.unlink(missing_ok=True)
                    if db_path.exists() and db_path != self.main_db.resolve():
                        db_path.unlink(missing_ok=True)
                except Exception:
                    pass
                continue

            cleaned_ledgers.append(l)

        if not main_item:
            main_item = self._get_default_main_meta()

        final_ledgers = [main_item] + cleaned_ledgers
        data["ledgers"] = final_ledgers
        if "active_ledger_id" not in data or not any(l.get("id") == data["active_ledger_id"] for l in final_ledgers):
            data["active_ledger_id"] = "main_live"

        self._write_index(data)

    def list_ledgers(self) -> List[Dict[str, Any]]:
        """获取全量账本元数据列表，确保 main_live 始终置顶且受物理保护"""
        data = self._read_index()
        ledgers = data.get("ledgers", [])
        return copy_deep(ledgers)

    def get_ledger_meta(self, ledger_id: str) -> Optional[Dict[str, Any]]:
        """按 ID 查询指定账本的元数据"""
        for l in self.list_ledgers():
            if l.get("id") == ledger_id:
                return l
        return None

    def get_active_ledger_id(self) -> str:
        """获取当前激活的账本 ID，默认为 main_live"""
        data = self._read_index()
        return data.get("active_ledger_id", "main_live")

    def set_active_ledger_id(self, ledger_id: str) -> bool:
        """设置当前激活账本 ID 并持久化至 ledgers_index.json"""
        data = self._read_index()
        if not any(l.get("id") == ledger_id for l in data.get("ledgers", [])):
            return False
        data["active_ledger_id"] = ledger_id
        self._write_index(data)
        return True

    def create_ledger(
        self,
        name: str,
        base_cash: float = 100000.0,
        ledger_type: str = "sandbox",
        default_tier: str = "C3",
        description: str = "",
        initial_holdings: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        创建全新独立账本：
        1. 分配唯一 ledger_id
        2. 在 data/ledgers/ 生成初始 json 结构
        3. 写入账本元数据并更新 data/ledgers_index.json
        返回新建账本的 ledger_id (str)
        """
        valid_types = {"live", "sandbox", "family"}
        if ledger_type not in valid_types:
            ledger_type = "sandbox"

        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        rand_suffix = uuid.uuid4().hex[:4]
        ledger_id = f"{ledger_type}_{now_str}_{rand_suffix}"

        json_rel_path = f"data/ledgers/{ledger_id}.json"
        db_rel_path = f"data/ledgers/{ledger_id}.db"

        json_abs_path = self.root / json_rel_path
        db_abs_path = self.root / db_rel_path
        json_abs_path.parent.mkdir(parents=True, exist_ok=True)

        # 初始持仓与资金构建
        holdings_list = initial_holdings if initial_holdings is not None else []
        tot_mkt_val = sum(float(h.get("market_value", 0.0)) for h in holdings_list)
        avail_cash = float(base_cash)
        tot_equity = round(tot_mkt_val + avail_cash, 2)

        init_payload = {
            "version": "AGY2_PORTFOLIO_V2",
            "takeover_mode": "B" if holdings_list else "A",
            "baseline_date": datetime.now().strftime("%Y-%m-%d"),
            "baseline_equity": tot_equity,
            "available_cash": avail_cash,
            "in_transit_cash": 0.0,
            "total_market_value": tot_mkt_val,
            "total_equity": tot_equity,
            "peak_equity": tot_equity,
            "max_drawdown_pct": 0.0,
            "benchmark_code": "000300.SH",
            "benchmark_baseline_nav": 1.0,
            "benchmark_current_nav": 1.0,
            "portfolio_return_pct": 0.0,
            "benchmark_return_pct": 0.0,
            "alpha_return_pct": 0.0,
            "holdings": holdings_list,
            "pending_orders": [],
            "staged_batch_plans": [],
            "reserved_batch_cash": 0.0
        }

        with open(json_abs_path, "w", encoding="utf-8") as f:
            json.dump(init_payload, f, ensure_ascii=False, indent=2)

        # 写入元数据索引 (严格保障名称唯一，杜绝重名)
        safe_name = self._resolve_unique_name(name)
        meta = {
            "id": ledger_id,
            "name": safe_name,
            "type": ledger_type,
            "file": json_rel_path,
            "db_file": db_rel_path,
            "default_tier": default_tier if default_tier in {"C1", "C2", "C3", "C4", "C5"} else "C3",
            "is_protected": False,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "description": description or f"独立{ledger_type}环境账本"
        }

        data = self._read_index()
        MultiLedgerManager._recently_created_lids.add(ledger_id)
        data.setdefault("ledgers", []).append(meta)
        self._write_index(data)

        return ledger_id

    def clone_ledger(
        self,
        src_id: str,
        target_name: str,
        ledger_type: Optional[str] = "sandbox",
        default_tier: Optional[str] = None
    ) -> str:
        """
        深拷贝克隆现有账本副本：
        1. 读取源账本 JSON 运行态（持仓、批次、在途单、现金等）
        2. 生成新 target_id 并写入 data/ledgers/<target_id>.json
        3. 建立全新独立 SQLite 数据库路径
        4. 追加索引元数据并返回 target_id
        """
        src_meta = self.get_ledger_meta(src_id)
        if not src_meta:
            raise KeyError(f"未找到待克隆的源账本 ID: {src_id}")

        src_json_path = self.root / src_meta["file"]
        if not src_json_path.exists():
            # 若源文件不存在但有缓存的 PM 实例，则先保存一次
            if src_id in self._pm_cache:
                self._pm_cache[src_id].save_state(record_snapshot=True)
            if not src_json_path.exists():
                raise FileNotFoundError(f"源账本文件不存在: {src_json_path}")

        with open(src_json_path, "r", encoding="utf-8") as f:
            src_state = json.load(f)

        cloned_type = ledger_type or "sandbox"
        target_tier = default_tier or src_meta.get("default_tier", "C3")

        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        rand_suffix = uuid.uuid4().hex[:4]
        target_id = f"{cloned_type}_clone_{now_str}_{rand_suffix}"

        json_rel_path = f"data/ledgers/{target_id}.json"
        db_rel_path = f"data/ledgers/{target_id}.db"

        target_json_path = self.root / json_rel_path
        target_db_path = self.root / db_rel_path
        target_json_path.parent.mkdir(parents=True, exist_ok=True)

        # 写入克隆 JSON
        with open(target_json_path, "w", encoding="utf-8") as f:
            json.dump(src_state, f, ensure_ascii=False, indent=2)

        # 确保对应的新 DB 初始干净
        if target_db_path.exists():
            try:
                target_db_path.unlink()
            except Exception:
                pass

        target_name_raw = str(target_name).strip() or f"{src_meta.get('name', src_id)} - 副本"
        safe_clone_name = self._resolve_unique_name(target_name_raw)

        meta = {
            "id": target_id,
            "name": safe_clone_name,
            "type": cloned_type,
            "file": json_rel_path,
            "db_file": db_rel_path,
            "default_tier": target_tier,
            "is_protected": False,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "description": f"克隆自 {src_meta.get('name', src_id)} ({src_id})"
        }

        data = self._read_index()
        MultiLedgerManager._recently_created_lids.add(target_id)
        data.setdefault("ledgers", []).append(meta)
        self._write_index(data)

        return target_id

    def rename_ledger(self, ledger_id: str, new_name: str) -> bool:
        """重命名指定账本 (带防重名保护)"""
        data = self._read_index()
        ledgers = data.get("ledgers", [])
        target = next((l for l in ledgers if l.get("id") == ledger_id), None)
        if not target:
            return False

        if ledger_id == "main_live":
            target["name"] = "主实盘账本"
        else:
            target["name"] = self._resolve_unique_name(new_name, exclude_id=ledger_id)

        target["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._write_index(data)
        return True

    def delete_ledger(self, ledger_id: str) -> bool:
        """
        删除账本：
        【物理防护红线】：若 ledger_id == 'main_live'，强制抛出 PermissionError，坚决禁止删除！
        对于普通账本，物理删除其 json 和 db 文件，并从索引清理。
        """
        if str(ledger_id).strip().lower() == "main_live":
            raise PermissionError("主实盘账本受物理保护，禁止删除！")

        data = self._read_index()
        ledgers = data.get("ledgers", [])
        target = next((l for l in ledgers if l.get("id") == ledger_id), None)
        if not target:
            return False

        if target.get("is_protected", False):
            raise PermissionError(f"受保护账本禁止删除: {ledger_id}")

        # 物理清理文件 (使用 .resolve() 严防路径遍历别名误删主实盘)
        f_path = (self.root / target.get("file", "")).resolve()
        db_path = (self.root / target.get("db_file", "")).resolve()
        main_file_res = self.main_file.resolve()
        main_db_res = self.main_db.resolve()

        if f_path.exists() and f_path != main_file_res:
            try:
                f_path.unlink()
            except Exception:
                pass

        if db_path.exists() and db_path != main_db_res:
            try:
                db_path.unlink()
            except Exception:
                pass

        # 清除内存缓存
        self._pm_cache.pop(ledger_id, None)

        data["ledgers"] = [l for l in ledgers if l.get("id") != ledger_id]
        if data.get("active_ledger_id") == ledger_id:
            data["active_ledger_id"] = "main_live"

        self._write_index(data)
        return True

    def get_pm(self, ledger_id: str) -> Any:
        """
        工厂方法：装配并返回绑定该账本独立存储路径的 PortfolioManager 实例
        - main_live -> 绑定 portfolio_state.db 与 portfolio_ledger.json
        - 其他 -> 绑定 data/ledgers/<ledger_id>.db 与 data/ledgers/<ledger_id>.json
        """
        norm_lid = str(ledger_id).strip().lower()
        if norm_lid == "main_live":
            ledger_id = "main_live"

        if ledger_id in self._pm_cache:
            return self._pm_cache[ledger_id]

        meta = self.get_ledger_meta(ledger_id)
        if not meta:
            if ledger_id == "main_live":
                meta = self._get_default_main_meta()
            else:
                raise KeyError(f"账本未找到: {ledger_id}")

        # 动态延迟导入以避免循环依赖
        try:
            from AGY2_FundAdvisory.portfolio_manager import PortfolioManager
        except ImportError:
            from portfolio_manager import PortfolioManager

        json_path = self.root / meta.get("file", "portfolio_ledger.json")
        db_path = self.root / meta.get("db_file", "portfolio_state.db")

        pm = PortfolioManager(
            db_path=str(db_path),
            ledger_json_path=str(json_path),
            ledger_id=ledger_id
        )

        self._pm_cache[ledger_id] = pm
        return pm

    # 别名兼容
    get_portfolio_manager = get_pm

    def get_all_ledgers_summary(self) -> Dict[str, Any]:
        """
        汇总全家庭/全账本维度的资产全景：
        返回字段：
        - total_equity / total_assets: 全家庭汇总总资产
        - total_floating_pnl / total_pnl: 全账本汇总总浮盈
        - total_market_value: 全账本汇总市值
        - total_holdings_count / total_funds: 全账本持仓基金总只数
        - ledgers / ledgers_breakdown: 各账本细项指标列表
        - df: 适配 Streamlit 直接渲染的宽表 DataFrame
        """
        ledgers_meta = self.list_ledgers()
        breakdown = []

        total_equity = 0.0
        total_pnl = 0.0
        total_mkt_val = 0.0
        total_funds = 0

        for m in ledgers_meta:
            lid = m.get("id", "")
            lname = m.get("name", lid)
            ltype = m.get("type", "sandbox")
            tier = m.get("default_tier", "C3")

            # 优先使用内存中的 PM 实例以获取最鲜活数据
            if lid in self._pm_cache:
                pm = self._pm_cache[lid]
                eq = float(pm.total_equity)
                mv = float(pm.total_market_value)
                cash = float(pm.available_cash)
                in_transit = float(pm.in_transit_cash)
                pnl = float(sum(h.floating_pnl for h in pm.holdings.values()))
                h_cnt = len(pm.holdings)
            else:
                f_path = self.root / m.get("file", "")
                if f_path.exists():
                    try:
                        with open(f_path, "r", encoding="utf-8") as f:
                            jdata = json.load(f)
                        eq = float(jdata.get("total_equity", 0.0))
                        mv = float(jdata.get("total_market_value", 0.0))
                        cash = float(jdata.get("available_cash", 0.0))
                        in_transit = float(jdata.get("in_transit_cash", 0.0))
                        holdings = jdata.get("holdings", [])
                        pnl = float(sum(h.get("floating_pnl", 0.0) for h in holdings))
                        h_cnt = len(holdings)
                    except Exception:
                        eq, mv, cash, in_transit, pnl, h_cnt = 0.0, 0.0, 0.0, 0.0, 0.0, 0
                else:
                    eq, mv, cash, in_transit, pnl, h_cnt = 0.0, 0.0, 0.0, 0.0, 0.0, 0

            pnl_pct = round((pnl / (mv - pnl)) * 100, 2) if (mv - pnl) > 0 else 0.0

            type_tag = {"live": "🟢 实盘", "family": "👨‍👩‍👧 家庭", "sandbox": "🧪 沙盒"}.get(ltype, "🧪 沙盒")

            item = {
                "id": lid,
                "name": lname,
                "type": ltype,
                "type_tag": type_tag,
                "default_tier": tier,
                "total_equity": round(eq, 2),
                "market_value": round(mv, 2),
                "available_cash": round(cash, 2),
                "in_transit_cash": round(in_transit, 2),
                "floating_pnl": round(pnl, 2),
                "floating_pnl_pct": pnl_pct,
                "holdings_count": h_cnt,
                "is_protected": m.get("is_protected", False),
                "updated_at": m.get("updated_at", "")
            }
            breakdown.append(item)

            total_equity += eq
            total_pnl += pnl
            total_mkt_val += mv
            total_funds += h_cnt

        # 构造用于 UI 渲染的 DataFrame
        df_rows = []
        for item in breakdown:
            df_rows.append({
                "账本类型": item["type_tag"],
                "账本名称": item["name"],
                "总资产 (元)": f"¥{item['total_equity']:,.2f}",
                "持仓市值 (元)": f"¥{item['market_value']:,.2f}",
                "可用现金 (元)": f"¥{item['available_cash']:,.2f}",
                "累计浮动盈亏": f"{'+' if item['floating_pnl'] >= 0 else ''}¥{item['floating_pnl']:,.2f} ({'+' if item['floating_pnl_pct'] >= 0 else ''}{item['floating_pnl_pct']}%)",
                "持仓只数": item["holdings_count"],
                "风险档位": item["default_tier"],
                "更新时间": item["updated_at"]
            })
        df = pd.DataFrame(df_rows)

        return {
            "total_equity": round(total_equity, 2),
            "total_assets": round(total_equity, 2),
            "total_floating_pnl": round(total_pnl, 2),
            "total_pnl": round(total_pnl, 2),
            "total_market_value": round(total_mkt_val, 2),
            "total_holdings_count": total_funds,
            "total_funds": total_funds,
            "ledgers": breakdown,
            "ledgers_breakdown": breakdown,
            "df": df
        }


def copy_deep(obj: Any) -> Any:
    """内部轻量深拷贝辅助函数"""
    import copy
    return copy.deepcopy(obj)
