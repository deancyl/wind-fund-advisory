# -*- coding: utf-8 -*-
"""
AGY2 国内免代理多源公共数据包同步模块 (remote_bundle_sync.py)
=================================================================
核心设计原则（面向中国大陆无代理用户，零隐私外泄、零死等超时）：
  1. 严格白名单防火墙：仅允许解压 6 个纯公开市场文件，严禁触碰任何用户账本/备份/审计日志；
  2. SHA256 完整性校验 + .tmp 原子替换，绝不损坏本地已有数据；
  3. 三级国内优先免代理回退链：
     - 优先级 1：国内加速镜像 / 用户自定义 AGY2_BUNDLE_URL（5s 短超时）；
     - 优先级 2：GitHub Public Release `data-latest` 直连（5s 短超时）；
     - 优先级 3：自动无缝回退至本机直连国内东方财富 FundMNFInfo 增量日更，确保无代理 100% 必通。
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tarfile
import tempfile
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import runtime_paths

logger = logging.getLogger("agy2.remote_bundle_sync")

PUBLIC_BUNDLE_WHITELIST: Tuple[str, ...] = (
    "processed/market_elite_nav_matrix.parquet",
    "processed/market_elite_meta.parquet",
    "processed/market_elite_sync_status.json",
    "processed/aligned_matrix_total_return.parquet",
    "master/fund_trading_rules.parquet",
    "master/fund_catalog.parquet",
)

DEFAULT_GITHUB_RELEASE_BASE = (
    "https://github.com/deancyl/agy2-fund-advisory/releases/download/data-latest"
)
DEFAULT_BUNDLE_FILENAME = "agy2-market-bundle-latest.tar.gz"
DEFAULT_MANIFEST_FILENAME = "manifest.json"


def compute_file_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_sha256(file_path: Path, expected_hex: str) -> bool:
    clean_exp = str(expected_hex or "").strip().lower()
    if not clean_exp:
        return False
    return compute_file_sha256(file_path).lower() == clean_exp


def _default_http_fetch(url: str, timeout: float) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AGY2-FundAdvisory/2.2.0 (+https://github.com/deancyl/agy2-fund-advisory)",
            "Accept": "*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=max(1.0, float(timeout))) as resp:
        return resp.read()


def _normalize_tar_relpath(raw_name: str) -> str:
    clean = str(raw_name or "").replace("\\", "/").strip()
    while clean.startswith("./"):
        clean = clean[2:]
    return clean.lstrip("/")


def extract_public_bundle_atomic(
    tar_path: Path,
    data_dir: Path,
    expected_sha256: Optional[str] = None,
) -> Dict[str, Any]:
    """
    严格白名单 + SHA256 + 原子落盘解压公共数据包：
    发现任何非白名单成员、路径穿越、软硬链接或哈希不匹配立即抛 ValueError 拒绝落盘。
    """
    if expected_sha256 and not verify_sha256(tar_path, expected_sha256):
        raise ValueError(f"SHA256 mismatch for bundle {tar_path.name}")

    allowed = set(PUBLIC_BUNDLE_WHITELIST)
    data_root = Path(data_dir).resolve()
    data_root.mkdir(parents=True, exist_ok=True)

    staged: List[Tuple[Path, Path, str]] = []
    try:
        with tarfile.open(tar_path, "r:gz") as tf:
            members = tf.getmembers()
            if not members:
                raise ValueError("Empty bundle archive")
            for m in members:
                if m.isdir():
                    continue
                if m.issym() or m.islnk() or not m.isfile():
                    raise ValueError(f"Forbidden non-regular tar member: {m.name}")
                raw = str(m.name or "")
                if raw.startswith("/") or raw.startswith("\\") or ".." in Path(raw).parts:
                    raise ValueError(f"Path traversal blocked: {m.name}")
                rel = _normalize_tar_relpath(raw)
                if rel not in allowed:
                    raise ValueError(f"Unauthorized non-whitelist file in bundle: {rel}")

                dst = (data_root / rel).resolve()
                if data_root not in dst.parents:
                    raise ValueError(f"Resolved target escapes data_dir: {dst}")
                dst.parent.mkdir(parents=True, exist_ok=True)
                tmp_dst = dst.with_suffix(dst.suffix + ".tmp")

                src_f = tf.extractfile(m)
                if src_f is None:
                    raise ValueError(f"Failed to read archive member: {rel}")
                with open(tmp_dst, "wb") as out_f:
                    out_f.write(src_f.read())
                staged.append((tmp_dst, dst, rel))

        updated_files: List[str] = []
        for tmp_dst, dst, rel in staged:
            os.replace(tmp_dst, dst)
            updated_files.append(rel)

        return {"files_updated": sorted(updated_files), "count": len(updated_files)}
    except Exception:
        for tmp_dst, _, _ in staged:
            try:
                if tmp_dst.exists():
                    tmp_dst.unlink()
            except Exception:
                pass
        raise


def _read_local_latest_date(data_dir: Path) -> str:
    st_path = data_dir / "processed" / "market_elite_sync_status.json"
    if not st_path.exists():
        return ""
    try:
        obj = json.loads(st_path.read_text(encoding="utf-8"))
        return str(obj.get("latest_date") or "")[:10]
    except Exception:
        return ""


def _candidate_base_urls() -> List[str]:
    urls: List[str] = []
    for env_key in ("AGY2_BUNDLE_URL", "AGY2_MIRROR_BUNDLE_URL"):
        v = os.environ.get(env_key, "").strip().rstrip("/")
        if v and v not in urls:
            urls.append(v)
    if DEFAULT_GITHUB_RELEASE_BASE not in urls:
        urls.append(DEFAULT_GITHUB_RELEASE_BASE)
    return urls


def sync_public_bundle_with_fallback(
    data_dir: Optional[Path] = None,
    timeout_sec: float = 5.0,
    cooldown_minutes: int = 30,
    fetcher: Optional[Callable[[str, float], bytes]] = None,
    local_fallback_fn: Optional[Callable[[], Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    三级免代理同步公共市场数据包：
      1. 国内加速镜像 / AGY2_BUNDLE_URL（<=5s 短超时）；
      2. GitHub Release `data-latest`（<=5s 短超时）；
      3. 无缝回退至本机直连国内东方财富增量日更。
    """
    target_dir = Path(data_dir).resolve() if data_dir is not None else runtime_paths.get_data_dir()
    http_get = fetcher or _default_http_fetch
    eff_timeout = max(1.0, min(5.0, float(timeout_sec)))
    local_latest = _read_local_latest_date(target_dir)
    errors: List[str] = []

    for base_url in _candidate_base_urls():
        manifest_url = f"{base_url}/{DEFAULT_MANIFEST_FILENAME}"
        try:
            raw_manifest = http_get(manifest_url, eff_timeout)
            manifest = json.loads(raw_manifest.decode("utf-8"))
            remote_date = str(manifest.get("latest_trade_date") or "")[:10]
            if local_latest and remote_date and local_latest >= remote_date:
                return {
                    "status": "up_to_date",
                    "sync_channel": "remote_bundle_manifest",
                    "source": base_url,
                    "latest_date": local_latest,
                    "updated_dates": 0,
                    "message": f"本地公共湖仓已是最新交易日（{local_latest}）",
                }

            bundle_name = str(manifest.get("bundle_file") or DEFAULT_BUNDLE_FILENAME)
            bundle_url = f"{base_url}/{bundle_name}"
            expected_sha = str(manifest.get("sha256") or "").strip()
            bundle_bytes = http_get(bundle_url, max(eff_timeout, 5.0))

            with tempfile.TemporaryDirectory(prefix="agy2_bundle_") as td:
                tmp_tar = Path(td) / bundle_name
                tmp_tar.write_bytes(bundle_bytes)
                ext = extract_public_bundle_atomic(
                    tar_path=tmp_tar,
                    data_dir=target_dir,
                    expected_sha256=expected_sha or None,
                )

            return {
                "status": "updated",
                "sync_channel": "remote_bundle",
                "source": base_url,
                "latest_date": remote_date or _read_local_latest_date(target_dir),
                "updated_dates": 1,
                "files_updated": ext["files_updated"],
                "message": f"已通过公共数据包快速同步至 {remote_date or '最新截面'}",
            }
        except Exception as exc:
            errors.append(f"{base_url}: {type(exc).__name__}({exc})")
            logger.info("公共数据包源不可达，自动切换下一源: %s (%s)", base_url, exc)

    # Priority 3：国内直连东财增量日更兜底（中国大陆无代理 100% 必通）
    if local_fallback_fn is not None:
        fb_res = dict(local_fallback_fn() or {})
    else:
        from market_lakehouse import incremental_daily_sync
        fb_res = dict(incremental_daily_sync(cooldown_minutes=max(0, min(1440, int(cooldown_minutes)))) or {})

    fb_res["sync_channel"] = "direct_eastmoney_fallback"
    fb_res["remote_errors"] = errors
    return fb_res
