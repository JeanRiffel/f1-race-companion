"""Fastest valid laps and distance-aligned car telemetry."""

import numpy as np
import pandas as pd

from f1companion.data.schema import empty_frame

FASTEST = dict(Driver="string", LapNumber="Int64", LapTimeSeconds="float64", Compound="string")
COMPARISON = dict(
    Distance="float64",
    SpeedA="float64",
    SpeedB="float64",
    ThrottleA="float64",
    ThrottleB="float64",
    BrakeA="bool",
    BrakeB="bool",
    SpeedDelta="float64",
)


def fastest_laps(laps: pd.DataFrame) -> pd.DataFrame:
    """Return each driver's quickest accurate, undeleted timed lap."""
    valid = laps.loc[
        laps.IsAccurate.fillna(False) & ~laps.Deleted.fillna(True) & laps.LapTimeSeconds.notna()
    ]
    return (
        valid.sort_values("LapTimeSeconds", kind="stable")
        .drop_duplicates("Driver")[list(FASTEST)]
        .astype(FASTEST)
        .reset_index(drop=True)
    )


def compare_telemetry(
    tel_a: pd.DataFrame, tel_b: pd.DataFrame, *, step_m: float = 10.0
) -> pd.DataFrame:
    """Interpolate both laps onto a common distance grid ending at the shorter lap."""
    if not np.isfinite(step_m) or step_m <= 0:
        raise ValueError("step_m must be a positive finite distance")
    frames = [
        frame.replace([np.inf, -np.inf], np.nan)
        .dropna(subset=["Distance", "Speed", "Throttle", "Brake"])
        .sort_values("Distance", kind="stable")
        .drop_duplicates("Distance", keep="last")
        for frame in (tel_a, tel_b)
    ]
    if any(len(frame) < 2 for frame in frames):
        return empty_frame(COMPARISON)
    end = min(frame.Distance.max() for frame in frames)
    if end < 0:
        return empty_frame(COMPARISON)
    distance = np.arange(int(np.floor(end / step_m)) + 1, dtype=float) * step_m
    out = pd.DataFrame({"Distance": distance})
    for suffix, frame in zip(("A", "B"), frames, strict=True):
        for channel in ("Speed", "Throttle", "Brake"):
            samples = np.interp(
                distance, frame.Distance.to_numpy(dtype=float), frame[channel].to_numpy(dtype=float)
            )
            out[channel + suffix] = samples >= 0.5 if channel == "Brake" else samples
    out["SpeedDelta"] = out.SpeedA - out.SpeedB
    return out[list(COMPARISON)].astype(COMPARISON)
