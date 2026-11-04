"""
智能分层缓存管理器 (cache_manager.py)
阶段三核心模块：管理全市场选基引擎的多层缓存，
支持事件驱动失效和强制重算。

缓存层级:
  - candidate_pool/  : 候选池缓存，每周重建
  - nav_cache/        : 单只基金 NAV 缓存，每日增量
  - winrate_cache/    : 胜率矩阵缓存，当日有效 + 事件驱动失效
  - optimizer_cache/  : 优化结果缓存，当日有效
"""

import json
import hashlib
import datetime
import copy
import re
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

# ── 路径定位 ──────────────────────────────────────────────────────
_THIS_DIR = Path(__file__).resolve().parent
_WORKSPACE_ROOT = _THIS_DIR.parent if _THIS_DIR.name == "AGY2_FundAdvisory" else _THIS_DIR

CACHE_ROOT = _WORKSPACE_ROOT / "data" / "cache"
FUND_PURCHASE_CACHE_PATH = CACHE_ROOT / "fund_purchase.parquet"
FUND_TRADING_RULES_FALLBACK = _WORKSPACE_ROOT / "data" / "master" / "fund_trading_rules.parquet"
FUNDS_META_DIR = CACHE_ROOT / "funds"

CACHE_BASE = _WORKSPACE_ROOT / "data" / "cache" / "market_screener"

# 子目录常量
_CANDIDATE_POOL_DIR = "candidate_pool"
_NAV_CACHE_DIR = "nav_cache"
_WINRATE_CACHE_DIR = "winrate_cache"
_OPTIMIZER_CACHE_DIR = "optimizer_cache"


def _ensure_dir(subdir: str) -> Path:
    """确保缓存子目录存在并返回路径"""
    p = CACHE_BASE / subdir
    p.mkdir(parents=True, exist_ok=True)
    return p


def _today_str() -> str:
    return datetime.date.today().isoformat()


def _file_date(path: Path) -> Optional[str]:
    """读取缓存文件的日期戳（存储在 .meta.json 中）"""
    meta = path.with_suffix(path.suffix + ".meta.json")
    if meta.exists():
        try:
            with open(meta, "r", encoding="utf-8") as f:
                return json.load(f).get("date")
        except Exception:
            pass
    return None


def _write_meta(path: Path, extra: Dict[str, Any] = None):
    """写入缓存元数据"""
    meta = path.with_suffix(path.suffix + ".meta.json")
    data = {"date": _today_str(), "timestamp": datetime.datetime.now().isoformat()}
    if extra:
        data.update(extra)
    with open(meta, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class SmartCacheManager:
    """智能分层缓存 + 事件驱动失效"""

    # ─── 候选池缓存（每周重建）───────────────────────────────────

    @classmethod
    def get_candidate_pool(cls, force_rebuild: bool = False, min_aum: float = 2.0, min_years: float = 3.0) -> Optional[pd.DataFrame]:
        """
        读取候选池缓存。
        如果缓存不存在或超过 7 天或 force_rebuild，返回 None。
        """
        d = _ensure_dir(_CANDIDATE_POOL_DIR)
        _pool_hash = hashlib.md5(f"{min_aum}_{min_years}".encode()).hexdigest()[:8]
        cache_file = d / f"candidate_pool_{_pool_hash}.parquet"
        if not cache_file.exists() or force_rebuild:
            return None
        # 检查过期（>7 天）
        cached_date = _file_date(cache_file)
        if cached_date:
            try:
                age = (datetime.date.today() - datetime.date.fromisoformat(cached_date)).days
                if age > 7:
                    return None
            except ValueError:
                return None
        else:
            return None
        try:
            df = pd.read_parquet(cache_file)
            if df.empty:
                return None
            return df
        except Exception:
            return None

    @classmethod
    def save_candidate_pool(cls, df: pd.DataFrame, min_aum: float = 2.0, min_years: float = 3.0):
        """保存候选池，记录时间戳；空候选池自动拦截"""
        if df is None or df.empty:
            return
        d = _ensure_dir(_CANDIDATE_POOL_DIR)
        _pool_hash = hashlib.md5(f"{min_aum}_{min_years}".encode()).hexdigest()[:8]
        cache_file = d / f"candidate_pool_{_pool_hash}.parquet"
        df.to_parquet(cache_file, index=False)
        _write_meta(cache_file, {"row_count": len(df)})

    # ─── 单只基金 NAV 缓存（每日增量追加）─────────────────────────

    @classmethod
    def get_nav_cache(cls, fund_code: str) -> Optional[pd.DataFrame]:
        """
        获取单只基金的 NAV 缓存。
        返回 DataFrame，列至少含 date(datetime), nav(float)。
        """
        d = _ensure_dir(_NAV_CACHE_DIR)
        cache_file = d / f"{fund_code}.parquet"
        if not cache_file.exists():
            return None
        try:
            df = pd.read_parquet(cache_file)
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
            return df
        except Exception:
            return None

    @classmethod
    def save_nav_cache(cls, fund_code: str, df: pd.DataFrame):
        """保存/覆盖单只基金 NAV 缓存"""
        d = _ensure_dir(_NAV_CACHE_DIR)
        cache_file = d / f"{fund_code}.parquet"
        df.to_parquet(cache_file, index=False)
        _write_meta(cache_file)

    @classmethod
    def append_nav_cache(cls, fund_code: str, new_rows: pd.DataFrame):
        """增量追加 NAV 数据（去重）"""
        existing = cls.get_nav_cache(fund_code)
        if existing is not None and not existing.empty:
            combined = pd.concat([existing, new_rows], ignore_index=True)
            combined["date"] = pd.to_datetime(combined["date"])
            combined = combined.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
        else:
            combined = new_rows.copy()
            combined["date"] = pd.to_datetime(combined["date"])
            combined = combined.sort_values("date").reset_index(drop=True)
        cls.save_nav_cache(fund_code, combined)

    # ─── NAV 矩阵缓存 ──────────────────────────────────────────

    @classmethod
    def _matrix_cache_key(cls, fund_codes: List[str], start_date: str) -> str:
        """根据基金代码列表和起始日期生成缓存键"""
        sorted_codes = sorted(fund_codes)
        raw = f"{start_date}__{'_'.join(sorted_codes)}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    @classmethod
    def get_nav_matrix_cache(cls, cache_key: str) -> Optional[pd.DataFrame]:
        """获取对齐后的 NAV 矩阵缓存（当日有效）"""
        d = _ensure_dir(_NAV_CACHE_DIR)
        cache_file = d / f"matrix_{cache_key}.parquet"
        if not cache_file.exists():
            return None
        cached_date = _file_date(cache_file)
        if cached_date != _today_str():
            return None
        try:
            return pd.read_parquet(cache_file)
        except Exception:
            return None

    @classmethod
    def save_nav_matrix_cache(cls, cache_key: str, df: pd.DataFrame):
        """保存对齐后的 NAV 矩阵"""
        d = _ensure_dir(_NAV_CACHE_DIR)
        cache_file = d / f"matrix_{cache_key}.parquet"
        df.to_parquet(cache_file)
        _write_meta(cache_file)

    # ─── 胜率缓存（当日有效 + 事件驱动失效）────────────────────────

    @classmethod
    def should_invalidate_winrate(cls) -> bool:
        """
        事件驱动失效判定：
        1. 缓存不存在 → True
        2. 缓存日期非今日 → True
        3. 沪深300当日涨跌幅 > 3% → True (尝试通过 akshare 获取)
        """
        d = _ensure_dir(_WINRATE_CACHE_DIR)
        # 检查是否有任何今日缓存
        today = _today_str()
        found_today = False
        for f in d.glob("*.json"):
            if _file_date(f) == today:
                found_today = True
                break
        if not found_today:
            return True

        # 检查沪深300波动（优先复用本地轻量单点行情，避免拉取全市场指数表）
        try:
            from portfolio_manager import fetch_realtime_index_quote
            q_300 = fetch_realtime_index_quote("000300")
            if q_300 and hasattr(q_300, "gszzl"):
                if abs(float(q_300.gszzl or 0.0)) > 3.0:
                    return True
            else:
                import akshare as ak
                df_idx = ak.stock_zh_index_spot_em()
                row_300 = df_idx[df_idx["代码"] == "000300"]
                if not row_300.empty:
                    change_pct = abs(float(row_300.iloc[0].get("涨跌幅", 0)))
                    if change_pct > 3.0:
                        return True
        except Exception:
            pass  # 获取失败不影响，保留缓存

        return False

    @classmethod
    def get_winrate_cache(cls, cache_key: str) -> Optional[Dict]:
        """获取胜率缓存（当日有效）"""
        d = _ensure_dir(_WINRATE_CACHE_DIR)
        cache_file = d / f"{cache_key}.json"
        if not cache_file.exists():
            return None
        cached_date = _file_date(cache_file)
        if cached_date != _today_str():
            return None
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    @classmethod
    def save_winrate_cache(cls, cache_key: str, data: Dict):
        """保存胜率缓存"""
        d = _ensure_dir(_WINRATE_CACHE_DIR)
        cache_file = d / f"{cache_key}.json"
        # 确保 numpy 类型可序列化
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=_json_default)
        _write_meta(cache_file)

    # ─── 优化器结果缓存（当日有效）──────────────────────────────

    @classmethod
    def get_optimizer_cache(cls, cache_key: str) -> Optional[Dict]:
        """获取优化结果缓存（当日有效）"""
        d = _ensure_dir(_OPTIMIZER_CACHE_DIR)
        cache_file = d / f"{cache_key}.json"
        if not cache_file.exists():
            return None
        cached_date = _file_date(cache_file)
        if cached_date != _today_str():
            return None
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    @classmethod
    def save_optimizer_cache(cls, cache_key: str, data: Dict):
        """保存优化结果"""
        d = _ensure_dir(_OPTIMIZER_CACHE_DIR)
        cache_file = d / f"{cache_key}.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=_json_default)
        _write_meta(cache_file)

    # ─── 清理过期缓存 ──────────────────────────────────────────

    @classmethod
    def cleanup_expired(cls, max_age_days: int = 30):
        """清理超过 max_age_days 天的缓存文件"""
        today = datetime.date.today()
        cleaned = 0
        for subdir in [_NAV_CACHE_DIR, _WINRATE_CACHE_DIR, _OPTIMIZER_CACHE_DIR]:
            d = CACHE_BASE / subdir
            if not d.exists():
                continue
            for f in d.iterdir():
                if f.suffix == ".json" and f.stem.endswith(".meta"):
                    continue  # 跳过 meta 文件
                cached_date = _file_date(f)
                if cached_date:
                    try:
                        age = (today - datetime.date.fromisoformat(cached_date)).days
                        if age > max_age_days:
                            f.unlink(missing_ok=True)
                            meta = f.with_suffix(f.suffix + ".meta.json")
                            meta.unlink(missing_ok=True)
                            cleaned += 1
                    except ValueError:
                        pass
        return cleaned

    # ─── 缓存键生成工具 ───────────────────────────────────────

    @classmethod
    def make_winrate_key(
        cls, fund_codes: List[str], holding_days: int,
        target_return: float, tier: str, as_of_date: Optional[str] = None
    ) -> str:
        """生成胜率缓存键（含基准日）"""
        as_of = as_of_date or _today_str()
        sorted_codes = sorted(fund_codes)
        raw = f"wr_{as_of}_{tier}_{holding_days}_{target_return:.4f}_{'_'.join(sorted_codes)}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    @classmethod
    def make_optimizer_key(
        cls, holding_days: int, target_return: float,
        tier: str, n_candidates: int, as_of_date: Optional[str] = None
    ) -> str:
        """生成优化器缓存键（含基准日）"""
        as_of = as_of_date or _today_str()
        raw = f"opt_{as_of}_{tier}_{holding_days}_{target_return:.4f}_{n_candidates}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]


def _json_default(obj):
    """JSON 序列化辅助：处理 numpy/pandas 类型"""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class FundQuotaDict(dict):
    """
    高性能全市场基金申购限额高速缓存字典。
    继承自 Python 原生 dict，基于底层 NumPy 列式并行索引构建。
    单只基金按需即时解析并就地回填底层原生哈希表，兼顾瞬时冷启动 (<15ms) 与亚微秒级热查询。
    """

    def __init__(self, df: pd.DataFrame):
        super().__init__()
        if df is None or df.empty:
            self._codes = []
            self._index_map = {}
            self._p_sts = []
            self._r_sts = []
            self._d_lims = []
            return

        codes = df["基金代码"].to_numpy()
        self._codes = codes
        self._index_map = {str(c): i for i, c in enumerate(codes)}
        self._p_sts = df["申购状态"].to_numpy()
        self._r_sts = df["赎回状态"].to_numpy()
        self._d_lims = df["日累计限定金额"].to_numpy()

    def __contains__(self, key: object) -> bool:
        return key in self._index_map

    def __len__(self) -> int:
        return len(self._index_map)

    def __bool__(self) -> bool:
        return bool(self._index_map)

    def __iter__(self):
        return iter(self._index_map)

    def keys(self):
        return self._index_map.keys()

    def _resolve(self, key: str) -> dict:
        idx = self._index_map[key]
        p_st = str(self._p_sts[idx])
        r_st = str(self._r_sts[idx])
        d_val = self._d_lims[idx]
        try:
            d_lim = float(d_val) if d_val is not None and not pd.isna(d_val) else 0.0
        except Exception:
            d_lim = 0.0

        is_limited = ("暂停" in p_st) or ("限" in p_st) or (d_lim < 1e8)
        norm_status = "暂停申购" if ("暂停" in p_st or "封闭" in p_st or d_lim <= 0) else ("限制大额" if (d_lim < 1e8 or "限" in p_st) else "开放申购")
        item = {
            "fund_code": key,
            "status": norm_status,
            "daily_limit": d_lim if norm_status != "暂停申购" else (d_lim if d_lim > 0 else 0.0),
            "is_limited": is_limited,
            "redemption_status": r_st
        }
        super().__setitem__(key, item)
        return item

    def __getitem__(self, key: str) -> dict:
        if super().__contains__(key):
            return super().__getitem__(key)
        if key in self._index_map:
            return self._resolve(key)
        raise KeyError(key)

    def get(self, key: str, default=None):
        if key in self._index_map:
            return self[key]
        return default

    def items(self):
        for k in self.keys():
            yield k, self[k]

    def values(self):
        for k in self.keys():
            yield self[k]

    def __deepcopy__(self, memo):
        return copy.deepcopy(dict(self.items()), memo)


class FundPurchaseCacheManager:
    """全市场基金申购状态与限额 Parquet 缓存管理器 (满足 <50ms 读取)"""

    CACHE_FILE = FUND_PURCHASE_CACHE_PATH
    FALLBACK_FILE = FUND_TRADING_RULES_FALLBACK
    _MEMORY_DF: Optional[pd.DataFrame] = None
    _MEMORY_DICT: Optional[Dict[str, Dict[str, Any]]] = None
    _LAST_LOAD_DATE: Optional[str] = None

    @classmethod
    def get_purchase_table(cls, force_refresh: bool = False, max_age_hours: float = 24.0) -> pd.DataFrame:
        """
        获取全市场申购限额表 (DataFrame)。
        冷读取耗时 < 50ms，内存二次命中 < 0.01ms。
        """
        today = _today_str()
        if not force_refresh and cls._MEMORY_DF is not None and cls._LAST_LOAD_DATE == today:
            return cls._MEMORY_DF

        # 1. 尝试从本地 Parquet 读取
        if not force_refresh and cls.CACHE_FILE.exists():
            try:
                # 检查文件修改时间
                mtime = cls.CACHE_FILE.stat().st_mtime
                age_h = (datetime.datetime.now().timestamp() - mtime) / 3600.0
                if age_h < max_age_hours:
                    df = pd.read_parquet(cls.CACHE_FILE)
                    if all(col in df.columns for col in ["基金代码", "申购状态", "赎回状态", "日累计限定金额"]):
                        cls._update_memory_cache(df, today)
                        return df
            except Exception:
                pass

        # 2. 尝试联网同步
        try:
            df = cls.sync_purchase_table()
            return df
        except Exception:
            pass

        # 3. 降级模式：读取现有（即便过期）的缓存或 data/master/fund_trading_rules.parquet
        if cls.CACHE_FILE.exists():
            try:
                df = pd.read_parquet(cls.CACHE_FILE)
                cls._update_memory_cache(df, today)
                return df
            except Exception:
                pass

        # 4. 从本地主数据湖仓兜底恢复
        df_fallback = cls._load_from_trading_rules()
        cls._update_memory_cache(df_fallback, today)
        return df_fallback

    @classmethod
    def sync_purchase_table(cls, timeout: float = 20.0) -> pd.DataFrame:
        """从 akshare 同步最新申购限额并持久化为 Parquet"""
        import akshare as ak
        df_raw = ak.fund_purchase_em()
        if df_raw is None or df_raw.empty:
            raise ValueError("ak.fund_purchase_em 返回空数据")

        # 标准化字段与类型
        df_clean = pd.DataFrame()
        df_clean["基金代码"] = df_raw["基金代码"].astype(str).str.strip().str.zfill(6)
        if "基金简称" in df_raw.columns:
            df_clean["基金简称"] = df_raw["基金简称"].astype(str).str.strip()
        df_clean["申购状态"] = df_raw["申购状态"].astype(str).str.strip()
        df_clean["赎回状态"] = df_raw["赎回状态"].astype(str).str.strip()

        # 数值清洗
        def _parse_limit(val, status):
            if pd.isna(val) or val is None or str(val).strip() in ("", "--", "nan", "None"):
                return 0.0 if ("暂停" in status or "封闭" in status) else 1e11
            try:
                f_val = float(val)
                return f_val if f_val >= 0 else 0.0
            except Exception:
                return 0.0 if ("暂停" in status or "封闭" in status) else 1e11

        df_clean["日累计限定金额"] = [
            _parse_limit(v, s) for v, s in zip(df_raw["日累计限定金额"], df_clean["申购状态"])
        ]

        # 写入 Parquet
        cls.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        df_clean.to_parquet(cls.CACHE_FILE, index=False)
        cls._update_memory_cache(df_clean, _today_str())
        return df_clean

    @classmethod
    def _load_from_trading_rules(cls) -> pd.DataFrame:
        """从 data/master/fund_trading_rules.parquet 提取基准数据"""
        if not cls.FALLBACK_FILE.exists():
            # 极限保底空表
            return pd.DataFrame(columns=["基金代码", "申购状态", "赎回状态", "日累计限定金额"])

        df_master = pd.read_parquet(cls.FALLBACK_FILE)
        df_clean = pd.DataFrame()
        df_clean["基金代码"] = df_master["symbol"].astype(str).str.strip().str.zfill(6)
        if "fund_name" in df_master.columns:
            df_clean["基金简称"] = df_master["fund_name"].astype(str).str.strip()
        df_clean["申购状态"] = df_master["purchase_status"].astype(str).str.strip()
        df_clean["赎回状态"] = df_master["redemption_status"].astype(str).str.strip()
        df_clean["日累计限定金额"] = pd.to_numeric(df_master["daily_limit_amount"], errors="coerce").fillna(1e11)

        # 补写到 cache 文件供后续高速复用
        try:
            cls.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            df_clean.to_parquet(cls.CACHE_FILE, index=False)
        except Exception:
            pass

        return df_clean

    @classmethod
    def _update_memory_cache(cls, df: pd.DataFrame, today: str):
        cls._MEMORY_DF = df
        cls._LAST_LOAD_DATE = today
        # 预构建极速哈希索引字典 (列式并行索引，冷启动 < 15ms，热查询 < 3µs)
        cls._MEMORY_DICT = FundQuotaDict(df)

    @classmethod
    def get_fund_quota(cls, fund_code: str) -> Dict[str, Any]:
        """单只基金限额极速查询 (<0.01ms)"""
        code = str(fund_code).strip().zfill(6)
        if cls._MEMORY_DICT is None:
            cls.get_purchase_table()
        if cls._MEMORY_DICT and code in cls._MEMORY_DICT:
            return copy.deepcopy(cls._MEMORY_DICT[code])
        # 默认放行兜底
        return {
            "fund_code": code,
            "status": "开放申购",
            "daily_limit": 1e11,
            "is_limited": False,
            "redemption_status": "开放赎回"
        }


class FundMetadataManager:
    """基金本体排雷与季报重仓元数据管理器 (带 24h 本地 TTL 缓存)"""

    CACHE_DIR = FUNDS_META_DIR
    MASTER_MANAGERS = _WORKSPACE_ROOT / "data" / "master" / "fund_managers.parquet"
    DUCKDB_PATH = _WORKSPACE_ROOT / "data" / "storage.duckdb"

    @classmethod
    def get_fund_metadata(cls, fund_code: str, force_refresh: bool = False, max_age_hours: float = 24.0) -> Dict[str, Any]:
        """获取基金元数据（规模/经理/股债仓位/重仓股），带 24h 本地 TTL 缓存与离线兜底"""
        code = str(fund_code).strip().zfill(6)
        cache_file = cls.CACHE_DIR / f"{code}_meta.json"

        # 1. 命中本地有效缓存 (<1ms)
        if not force_refresh and cache_file.exists():
            try:
                mtime = cache_file.stat().st_mtime
                age_h = (datetime.datetime.now().timestamp() - mtime) / 3600.0
                if age_h < max_age_hours:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        return json.load(f)
            except Exception:
                pass

        # 2. 联网调用天天基金接口
        try:
            data = cls.fetch_from_tiantian(code)
            cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return data
        except Exception:
            pass

        # 3. 降级模式：读取现有过期缓存
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                    cached["source"] = "local_cache_expired"
                    return cached
            except Exception:
                pass

        # 4. 离线主数据兜底
        fallback_data = cls.fallback_from_master(code)
        try:
            cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(fallback_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        return fallback_data

    @classmethod
    def fetch_from_tiantian(cls, fund_code: str, timeout: float = 3.0) -> Dict[str, Any]:
        """请求天天基金 JS 接口并解析元数据"""
        code = str(fund_code).strip().zfill(6)
        url = f"http://fund.eastmoney.com/pingzhongdata/{code}.js"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", errors="replace")

        def _extract_var(var_name: str):
            pattern = r"var\s+" + re.escape(var_name) + r"\s*=\s*([^;]+);"
            m = re.search(pattern, text)
            if not m:
                return None
            try:
                return json.loads(m.group(1).strip())
            except Exception:
                return None

        # 1. 规模与清盘排雷
        scale_data = _extract_var("Data_fluctuationScale")
        aum = None
        if scale_data and "series" in scale_data and len(scale_data["series"]) > 0:
            last_item = scale_data["series"][-1]
            if isinstance(last_item, dict) and "y" in last_item:
                aum = float(last_item["y"])

        liquidation_risk = (aum is not None and aum < 0.5)

        # 2. 基金经理与任期年限/回报
        mgr_data = _extract_var("Data_currentFundManager")
        manager_name = "未知"
        term_years = 0.0
        term_return = 0.0
        if mgr_data and isinstance(mgr_data, list) and len(mgr_data) > 0:
            m0 = mgr_data[0]
            manager_name = str(m0.get("name", "未知"))
            wt = str(m0.get("workTime", ""))
            # 解析年限
            m_wt = re.search(r"(?:(\d+)年)?(?:又?(\d+)天)?", wt)
            if m_wt:
                y = float(m_wt.group(1) or 0)
                d = float(m_wt.group(2) or 0)
                term_years = round(y + d / 365.25, 2)
            # 解析回报
            prof = m0.get("profit", {})
            s_list = prof.get("series", [])
            if s_list and len(s_list) > 0:
                d_list = s_list[0].get("data", [])
                if d_list and len(d_list) > 0:
                    term_return = round(float(d_list[0].get("y", 0.0) or 0.0), 2)

        is_novice_manager = (term_years < 1.0)

        # 3. 季报穿透股债配置
        alloc_data = _extract_var("Data_assetAllocation")
        asset_alloc = {"stock": 0.0, "bond": 0.0, "cash": 0.0}
        if alloc_data and "series" in alloc_data:
            for s in alloc_data["series"]:
                name = s.get("name", "")
                data_pts = s.get("data", [])
                val = float(data_pts[-1]) if data_pts else 0.0
                if "股票" in name:
                    asset_alloc["stock"] = round(val, 2)
                elif "债券" in name:
                    asset_alloc["bond"] = round(val, 2)
                elif "现金" in name:
                    asset_alloc["cash"] = round(val, 2)

        # 4. 前十大重仓
        stock_codes = _extract_var("stockCodesNew") or []
        if isinstance(stock_codes, list):
            top10_stocks = [str(s).strip() for s in stock_codes[:10]]
        else:
            top10_stocks = []

        return {
            "code": code,
            "aum": round(aum, 2) if aum is not None else None,
            "manager": manager_name,
            "term_years": term_years,
            "term_return": term_return,
            "asset_allocation": asset_alloc,
            "top10_stocks": top10_stocks,
            "liquidation_risk": bool(liquidation_risk),
            "is_novice_manager": bool(is_novice_manager),
            "updated_at": datetime.datetime.now().isoformat(),
            "source": "tiantian_realtime"
        }

    @classmethod
    def fallback_from_master(cls, fund_code: str) -> Dict[str, Any]:
        """从本地数据湖仓提取兜底元数据"""
        code = str(fund_code).strip().zfill(6)
        manager_name = "未知"
        term_years = 0.0
        aum = None
        term_return = 0.0

        if cls.MASTER_MANAGERS.exists():
            try:
                df_mgr = pd.read_parquet(cls.MASTER_MANAGERS)
                sub = df_mgr[df_mgr["fund_code"] == code]
                if not sub.empty:
                    row = sub.iloc[0]
                    manager_name = str(row.get("manager_name", "未知"))
                    career_days = float(row.get("career_days", 0) or 0)
                    term_years = round(career_days / 365.25, 2)
                    aum_val = row.get("aum_billion")
                    aum = round(float(aum_val), 2) if pd.notna(aum_val) else None
                    ret_val = row.get("best_return_pct")
                    term_return = round(float(ret_val), 2) if pd.notna(ret_val) else 0.0
            except Exception:
                pass

        return {
            "code": code,
            "aum": aum,
            "manager": manager_name,
            "term_years": term_years,
            "term_return": term_return,
            "asset_allocation": {"stock": 0.0, "bond": 0.0, "cash": 0.0},
            "top10_stocks": [],
            "liquidation_risk": (aum is not None and aum < 0.5),
            "is_novice_manager": (term_years < 1.0),
            "updated_at": datetime.datetime.now().isoformat(),
            "source": "offline_master_fallback"
        }
