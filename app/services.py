"""Cached data access and friendly error presentation for the app."""

from typing import NoReturn

import pandas as pd
import streamlit as st

from f1companion.data import (
    F1DataError,
    RaceData,
    RaceInfo,
    list_races,
    load_fastest_lap_telemetry,
    load_race,
)

__all__ = [
    "F1DataError",
    "RaceData",
    "RaceInfo",
    "get_races",
    "get_race",
    "get_telemetry",
    "show_data_error",
]


@st.cache_data(ttl=3600, show_spinner="Loading the calendar...")
def get_races(year: int) -> pd.DataFrame:
    """Return a season's races whose dates have arrived."""
    return list_races(year)


@st.cache_data(show_spinner="Loading race data (the first load of a race can take a minute)...")
def get_race(year: int, round_number: int) -> RaceData:
    """Return normalized race data, cached separately from car telemetry."""
    return load_race(year, round_number)


@st.cache_data(show_spinner="Loading telemetry...")
def get_telemetry(year: int, round_number: int, driver: str) -> pd.DataFrame:
    """Return one driver's fastest-lap car samples."""
    return load_fastest_lap_telemetry(year, round_number, driver)


def show_data_error(err: F1DataError) -> NoReturn:
    """Explain a known data failure and stop this render without a traceback."""
    st.error(str(err))
    st.caption("Try another race or retry later; recently completed races can take time to appear.")
    st.stop()
