"""Validate schema semantics against small source-shaped frames."""

from datetime import date

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from f1companion.data import DataUnavailableError, schema
from f1companion.data.normalize import (
    normalize_laps,
    normalize_race_control,
    normalize_results,
    normalize_schedule,
    normalize_telemetry,
    normalize_track_status,
)


def assert_schema(frame, contract):
    assert list(frame.columns) == list(contract)
    assert {name: str(dtype) for name, dtype in frame.dtypes.items()} == contract


def test_laps(raw_laps):
    before = raw_laps.copy(deep=True)
    out = normalize_laps(raw_laps)
    assert_schema(out, schema.LAPS)
    assert_frame_equal(raw_laps, before)
    assert out["LapNumber"].tolist() == sorted(out["LapNumber"].tolist())
    assert out.loc[out.LapNumber.eq(1), "Driver"].tolist() == ["HAM", "LEC", "VER"]
    assert out.loc[out.LapNumber.eq(1), "LapTimeSeconds"].isna().all()
    assert out.loc[out.LapNumber.eq(3), "LapTimeSeconds"].eq(93).all()
    assert out.loc[out.LapNumber.le(2), "Compound"].eq("UNKNOWN").all()
    assert out.loc[out.LapNumber.eq(3), "Compound"].eq("SOFT").all()
    assert out.IsPitInLap.eq(out.LapNumber.eq(2)).all()
    assert out.IsPitOutLap.eq(out.LapNumber.eq(3)).all()
    assert not out.loc[out.LapNumber.eq(1), "IsAccurate"].any()
    assert not out.Deleted.any()
    assert out.loc[out.LapNumber.eq(1), "FreshTyre"].isna().all()
    assert out.loc[out.LapNumber.eq(3), "TrackStatus"].eq("41").all()


@pytest.mark.parametrize("column", ["Driver", "LapTime", "Deleted"])
def test_missing_lap_column(raw_laps, column):
    with pytest.raises(DataUnavailableError):
        normalize_laps(raw_laps.drop(columns=column))


def test_results(raw_results):
    before = raw_results.copy(deep=True)
    out = normalize_results(raw_results)
    assert_schema(out, schema.RESULTS)
    assert_frame_equal(raw_results, before)
    assert out.Driver.tolist() == ["VER", "HAM", "LEC"]
    assert out.TeamColor.tolist() == ["#abcdef", "#888888", "#888888"]
    assert pd.isna(out.iloc[1].GridPosition)
    assert pd.isna(out.iloc[-1].Position)
    assert out.iloc[-1].Points == 0.0


@pytest.mark.parametrize("color", ["", None, "#abcdef", "12345", "gggggg"])
def test_invalid_colors(raw_results, color):
    raw_results["TeamColor"] = color
    assert normalize_results(raw_results).TeamColor.eq(schema.DEFAULT_TEAM_COLOR).all()


def test_missing_results_column(raw_results):
    with pytest.raises(DataUnavailableError):
        normalize_results(raw_results.drop(columns="TeamColor"))


def test_track(raw_track):
    out = normalize_track_status(raw_track)
    assert_schema(out, schema.TRACK_STATUS)
    assert out.Label.tolist() == ["Green", "Safety Car", "Unknown"]
    assert out.TimeSeconds.tolist() == [0, 30, 60]


@pytest.mark.parametrize("raw", [None, pd.DataFrame()])
def test_optional_empty(raw):
    for normalizer, contract in [
        (normalize_track_status, schema.TRACK_STATUS),
        (normalize_race_control, schema.RACE_CONTROL),
    ]:
        out = normalizer(raw)
        assert out.empty
        assert_schema(out, contract)


def test_control(raw_control):
    out = normalize_race_control(raw_control)
    assert_schema(out, schema.RACE_CONTROL)
    assert out.Time.is_monotonic_increasing
    assert out.iloc[0].Time == pd.Timestamp("2024-03-02 12:00", tz="UTC")


def test_telemetry(raw_telemetry):
    out = normalize_telemetry(raw_telemetry)
    assert_schema(out, schema.TELEMETRY)
    assert out.Distance.tolist() == [0, 100]
    assert out.Gear.tolist() == [3, 5]


def test_schedule(raw_schedule):
    before = raw_schedule.copy(deep=True)
    out = normalize_schedule(raw_schedule, date(2024, 3, 2))
    assert_schema(out, schema.RACES)
    assert_frame_equal(raw_schedule, before)
    assert out.RoundNumber.tolist() == [1, 2]
    assert out.iloc[-1].EventDate == pd.Timestamp("2024-03-02")
