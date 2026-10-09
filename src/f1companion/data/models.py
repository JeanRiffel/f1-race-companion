"""Project-owned race containers."""

from dataclasses import dataclass
from datetime import date

import pandas as pd


@dataclass(frozen=True)
class RaceInfo:
    year: int
    round_number: int
    event_name: str
    country: str
    location: str
    date: date


@dataclass(frozen=True)
class RaceData:
    info: RaceInfo
    laps: pd.DataFrame
    results: pd.DataFrame
    track_status: pd.DataFrame
    race_control: pd.DataFrame
