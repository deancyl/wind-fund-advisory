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
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

# ── 路径定位 ──────────────────────────────────────────────────────
_THIS_DIR = Path(__file__).resolve().parent
_WORKSPACE_ROOT = _THIS_DIR.parent if _THIS_DIR.name == "AGY2_FundAdvisory" else _THIS_DIR

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
    def get_candidate_pool(cls, force_rebuild: bool = False) -> Optional[pd.DataFrame]:
        """
        读取候选池缓存。
        如果缓存不存在或超过 7 天或 force_rebuild，返回 None。
        """
        d = _ensure_dir(_CANDIDATE_POOL_DIR)
        cache_file = d / "candidate_pool.parquet"
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
            return pd.read_parquet(cache_file)
        except Exception:
            return None

    @classmethod
    def save_candidate_pool(cls, df: pd.DataFrame):
        """保存候选池，记录时间戳"""
        d = _ensure_dir(_CANDIDATE_POOL_DIR)
        cache_file = d / "candidate_pool.parquet"
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

        # 检查沪深300波动
        try:
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
        target_return: float, tier: str
    ) -> str:
        """生成胜率缓存键"""
        sorted_codes = sorted(fund_codes)
        raw = f"wr_{tier}_{holding_days}_{target_return:.4f}_{'_'.join(sorted_codes)}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    @classmethod
    def make_optimizer_key(
        cls, holding_days: int, target_return: float,
        tier: str, n_candidates: int
    ) -> str:
        """生成优化器缓存键"""
        raw = f"opt_{tier}_{holding_days}_{target_return:.4f}_{n_candidates}"
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
