"""Configure FastF1's on-disk cache."""

import os
from pathlib import Path

import fastf1

_enabled: tuple[Path, bool] | None = None


def enable_cache(cache_dir: str | Path | None = None, *, offline: bool = False) -> Path:
    """Enable an idempotent disk cache and optionally disable network requests."""
    global _enabled
    path = (
        Path(
            cache_dir
            if cache_dir is not None
            else os.environ.get("F1COMPANION_CACHE_DIR", Path.cwd() / "data" / "fastf1_cache")
        )
        .expanduser()
        .resolve()
    )
    if _enabled != (path, offline):
        path.mkdir(parents=True, exist_ok=True)
        fastf1.Cache.enable_cache(str(path))
        fastf1.set_log_level("WARNING")
        fastf1.Cache.offline_mode(offline)
        _enabled = (path, offline)
    return path
