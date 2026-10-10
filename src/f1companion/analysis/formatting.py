"""Readable lap-time formatting."""

import numpy as np
import pandas as pd


def format_lap_time(seconds: float | None) -> str:
    """Format seconds as minutes and milliseconds, or a dash for missing values."""
    if pd.isna(seconds) or not np.isfinite(seconds):
        return "-"
    milliseconds = round(float(seconds) * 1000)
    minutes, remainder = divmod(milliseconds, 60000)
    return f"{minutes}:{remainder // 1000:02d}.{remainder % 1000:03d}"
