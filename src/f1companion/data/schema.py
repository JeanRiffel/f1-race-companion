"""Stable column order and dtype contracts for downstream layers."""

import pandas as pd

LAPS = dict(
    Driver="string",
    DriverNumber="string",
    Team="string",
    LapNumber="Int64",
    Position="Int64",
    LapTimeSeconds="float64",
    Stint="Int64",
    Compound="string",
    TyreLife="float64",
    FreshTyre="boolean",
    IsPitInLap="bool",
    IsPitOutLap="bool",
    TrackStatus="string",
    IsAccurate="bool",
    Deleted="bool",
)
RESULTS = dict(
    DriverNumber="string",
    Driver="string",
    FullName="string",
    Team="string",
    TeamColor="string",
    GridPosition="Int64",
    Position="Int64",
    ClassifiedPosition="string",
    Status="string",
    Points="float64",
    LapsCompleted="Int64",
)
TRACK_STATUS = dict(TimeSeconds="float64", Status="string", Label="string", Message="string")
RACE_CONTROL = dict(
    Time="datetime64[ns, UTC]", Lap="Int64", Category="string", Flag="string", Message="string"
)
TELEMETRY = dict(
    Distance="float64", Speed="float64", Throttle="float64", Brake="bool", Gear="Int64"
)
RACES = dict(
    RoundNumber="Int64",
    EventName="string",
    Country="string",
    Location="string",
    EventDate="datetime64[ns]",
)
TRACK_STATUS_LABELS = {
    "1": "Green",
    "2": "Yellow",
    "4": "Safety Car",
    "5": "Red Flag",
    "6": "VSC",
    "7": "VSC Ending",
}
DEFAULT_TEAM_COLOR = "#888888"


def empty_frame(columns: dict[str, str]) -> pd.DataFrame:
    """Return an empty frame with the specified ordered columns and dtypes."""
    return pd.DataFrame({name: pd.Series(dtype=dtype) for name, dtype in columns.items()})
