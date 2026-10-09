"""Pure conversion from source frames to project-owned schemas."""

from datetime import date

import pandas as pd

from . import schema
from .errors import DataUnavailableError

LAP_SOURCE = [
    "Driver",
    "DriverNumber",
    "Team",
    "LapNumber",
    "Position",
    "LapTime",
    "Stint",
    "Compound",
    "TyreLife",
    "FreshTyre",
    "PitInTime",
    "PitOutTime",
    "TrackStatus",
    "IsAccurate",
    "Deleted",
]
RESULT_SOURCE = [
    "DriverNumber",
    "Abbreviation",
    "FullName",
    "TeamName",
    "TeamColor",
    "GridPosition",
    "Position",
    "ClassifiedPosition",
    "Status",
    "Points",
    "Laps",
]


def _require(raw: pd.DataFrame, columns: list[str]) -> None:
    if any(name not in raw.columns for name in columns):
        raise DataUnavailableError("Required race data is missing. Try again later.")


def _finish(frame: pd.DataFrame, contract: dict[str, str], sort: list[str]) -> pd.DataFrame:
    return (
        frame.loc[:, list(contract)]
        .astype(contract)
        .sort_values(sort, kind="stable", na_position="last")
        .reset_index(drop=True)
    )


def normalize_laps(raw: pd.DataFrame) -> pd.DataFrame:
    """Normalize driver laps without modifying the source."""
    _require(raw, LAP_SOURCE)
    out = pd.DataFrame(raw).copy()
    out["LapTimeSeconds"] = out["LapTime"].dt.total_seconds()
    out["Compound"] = (
        out["Compound"].astype("string").str.upper().replace("", "UNKNOWN").fillna("UNKNOWN")
    )
    out["IsPitInLap"] = out["PitInTime"].notna()
    out["IsPitOutLap"] = out["PitOutTime"].notna()
    for name in ("IsAccurate", "Deleted"):
        out[name] = out[name].astype("boolean").fillna(False)
    return _finish(out, schema.LAPS, ["LapNumber", "Driver"])


def normalize_results(raw: pd.DataFrame) -> pd.DataFrame:
    """Normalize classification, colors, and pit-lane starts."""
    _require(raw, RESULT_SOURCE)
    out = (
        pd.DataFrame(raw)
        .rename(columns={"Abbreviation": "Driver", "TeamName": "Team", "Laps": "LapsCompleted"})
        .copy()
    )
    colors = out["TeamColor"].astype("string").str.lower()
    out["TeamColor"] = ("#" + colors).where(
        colors.str.fullmatch(r"[0-9a-f]{6}", na=False), schema.DEFAULT_TEAM_COLOR
    )
    out["GridPosition"] = out["GridPosition"].mask(out["GridPosition"].eq(0))
    out["Points"] = out["Points"].fillna(0.0)
    return _finish(out, schema.RESULTS, ["Position"])


def normalize_track_status(raw: pd.DataFrame | None) -> pd.DataFrame:
    """Normalize optional track status changes."""
    if raw is None or raw.empty:
        return schema.empty_frame(schema.TRACK_STATUS)
    out = pd.DataFrame(raw).copy()
    out["TimeSeconds"] = out["Time"].dt.total_seconds()
    out["Label"] = out["Status"].astype("string").map(schema.TRACK_STATUS_LABELS).fillna("Unknown")
    return _finish(out, schema.TRACK_STATUS, ["TimeSeconds"])


def normalize_race_control(raw: pd.DataFrame | None) -> pd.DataFrame:
    """Normalize optional race control messages to UTC."""
    if raw is None or raw.empty:
        return schema.empty_frame(schema.RACE_CONTROL)
    out = pd.DataFrame(raw).copy()
    out["Time"] = pd.to_datetime(out["Time"], utc=True)
    return _finish(out, schema.RACE_CONTROL, ["Time"])


def normalize_telemetry(raw: pd.DataFrame) -> pd.DataFrame:
    """Normalize car samples, ordered by distance in metres."""
    out = pd.DataFrame(raw).rename(columns={"nGear": "Gear"}).copy()
    return _finish(out, schema.TELEMETRY, ["Distance"])


def normalize_schedule(raw: pd.DataFrame, today: date) -> pd.DataFrame:
    """Return non-testing races dated on or before today."""
    out = pd.DataFrame(raw).copy()
    out["EventDate"] = pd.to_datetime(out["EventDate"]).dt.normalize()
    out = out.loc[out["RoundNumber"].ne(0) & out["EventDate"].dt.date.le(today)]
    return _finish(out, schema.RACES, ["RoundNumber"])
