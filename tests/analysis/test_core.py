"""Core analysis semantics, missing data, and immutability."""

import numpy as np
import pandas as pd
import pytest
from factories import race_data, telemetry
from pandas.testing import assert_frame_equal

from f1companion.analysis import (
    compare_telemetry,
    driver_colors,
    fastest_laps,
    final_results,
    format_lap_time,
    key_events,
    pit_stop_summary,
    pit_stops,
    position_by_lap,
    stints,
)
from f1companion.analysis.head_to_head import COMPARISON, FASTEST
from f1companion.analysis.recap import CLASSIFICATION, EVENTS, POSITIONS
from f1companion.analysis.strategy import STINTS, STOPS


def assert_schema(frame, contract):
    assert list(frame) == list(contract)
    assert {k: str(v) for k, v in frame.dtypes.items()} == contract


@pytest.mark.parametrize("empty", [False, True])
@pytest.mark.parametrize(
    "function,contract",
    [
        (position_by_lap, POSITIONS),
        (final_results, CLASSIFICATION),
        (key_events, EVENTS),
        (stints, STINTS),
        (pit_stops, STOPS),
        (fastest_laps, FASTEST),
    ],
)
def test_schema_and_no_mutation(function, contract, empty):
    race = race_data()
    laps = race.laps.iloc[:0] if empty else race.laps
    results = race.results.iloc[:0] if empty else race.results
    before_laps, before_results = laps.copy(deep=True), results.copy(deep=True)
    if function in (position_by_lap, key_events):
        out = function(laps, results)
    elif function is final_results:
        out = function(results)
    else:
        out = function(laps)
    assert_schema(out, contract)
    assert_frame_equal(laps, before_laps)
    assert_frame_equal(results, before_results)
    if empty:
        assert out.empty


def test_positions_grid_and_order():
    race = race_data()
    out = position_by_lap(race.laps, race.results)
    assert out.loc[out.LapNumber.eq(0), "Driver"].tolist() == ["AAA", "BBB", "DDD"]
    assert out.Position.notna().all()
    assert out.loc[out.Driver.eq("DDD"), "LapNumber"].tolist() == [0]
    assert_frame_equal(out, out.sort_values(["Driver", "LapNumber"]).reset_index(drop=True))


def test_classification():
    out = final_results(race_data().results)
    assert out.Driver.tolist() == ["AAA", "BBB", "CCC", "DDD"]
    assert out.PositionsGained.iloc[:2].tolist() == [1, -1]
    assert out.PositionsGained.iloc[2:].isna().all()
    assert out.Position.iloc[-1] == "R"


def test_events_merge_and_retirement():
    out = key_events(race_data().laps, race_data().results)
    assert out.Type.tolist() == ["Safety Car", "Retirement", "Virtual Safety Car"]
    assert out.StartLap.tolist() == [3, 4, 6]
    assert out.EndLap.tolist() == [4, 4, 6]
    assert out.Description.iloc[0] == "Safety Car on laps 3-4"
    assert out.Description.iloc[1] == "Driver DDD (Team Three) retired after lap 4: Retired"
    assert out.Description.iloc[2] == "Virtual Safety Car on lap 6"


@pytest.mark.parametrize("count", [pd.NA, 0, -1, 2])
def test_retirement_lap(count):
    race = race_data()
    race.results.loc[3, "LapsCompleted"] = count
    out = key_events(race.laps.iloc[:0], race.results)
    assert (
        out.StartLap.iloc[0] == (2 if count == 2 else 1)
        if not pd.isna(count)
        else out.StartLap.iloc[0] == 1
    )


@pytest.mark.parametrize(
    "status,label",
    [
        ("4", "Safety Car"),
        ("6", "Virtual Safety Car"),
        ("7", "Virtual Safety Car"),
        ("5", "Red Flag"),
        ("15", "Red Flag"),
    ],
)
def test_event_codes(status, label):
    race = race_data()
    laps = race.laps.iloc[:1].copy()
    laps["TrackStatus"] = status
    out = key_events(laps, race.results.iloc[:0])
    assert out.Type.tolist() == [label]


def test_events_missing_and_disjoint():
    race = race_data()
    race.laps["TrackStatus"] = pd.NA
    assert key_events(race.laps, race.results.iloc[:0]).empty
    race.laps.loc[race.laps.LapNumber.isin([2, 4]), "TrackStatus"] = "4"
    out = key_events(race.laps, race.results.iloc[:0])
    assert out.StartLap.tolist() == [2, 4]
    assert out.EndLap.tolist() == [2, 4]


def test_driver_colors():
    assert driver_colors(race_data().results)["AAA"] == "#112233"
    assert driver_colors(race_data().results.iloc[:0]) == {}


def test_stint_boundaries_and_compound():
    out = stints(race_data().laps)
    first = out.iloc[0]
    assert (first.Driver, first.StartLap, first.EndLap, first.LapCount, first.Compound) == (
        "AAA",
        1,
        2,
        2,
        "SOFT",
    )
    assert out.iloc[1].LapCount == 4
    assert out.iloc[-1].LapCount == 2


def test_unknown_and_missing_stints():
    laps = race_data().laps
    laps["Compound"] = "UNKNOWN"
    laps.loc[laps.Driver.eq("DDD"), "Stint"] = pd.NA
    out = stints(laps)
    assert out.Compound.eq("UNKNOWN").all()
    assert "DDD" not in out.Driver.tolist()


def test_pit_stop_numbering_and_summary():
    race = race_data()
    race.laps.loc[race.laps.Driver.eq("AAA") & race.laps.LapNumber.eq(5), "IsPitInLap"] = True
    out = pit_stops(race.laps)
    assert out.Driver.tolist() == ["AAA", "AAA", "BBB"]
    assert out.LapNumber.tolist() == [2, 5, 2]
    assert out.StopNumber.tolist() == [1, 2, 1]
    summary = pit_stop_summary(out, race.results)
    assert summary.Stops.tolist() == [2, 1, 0, 0]
    assert summary.Laps.tolist() == ["2, 5", "2", "-", "-"]


def test_fastest_valid_laps():
    race = race_data()
    race.laps.loc[race.laps.Driver.eq("DDD"), "IsAccurate"] = False
    race.laps.loc[race.laps.Driver.eq("AAA") & race.laps.LapNumber.eq(2), "Deleted"] = True
    out = fastest_laps(race.laps)
    assert out.Driver.tolist() == ["AAA", "BBB", "CCC"]
    assert out.LapNumber.tolist() == [3, 2, 2]


def test_fastest_missing_times():
    laps = race_data().laps
    laps["LapTimeSeconds"] = np.nan
    assert fastest_laps(laps).empty


@pytest.mark.parametrize("step", [10.0, 25.0, 30.0, 200.0])
def test_telemetry_grid(step):
    tel = telemetry()
    before = tel.copy(deep=True)
    out = compare_telemetry(tel, tel, step_m=step)
    assert_schema(out, COMPARISON)
    assert out.Distance.tolist() == np.arange(0, 101, step).tolist()
    assert out.SpeedDelta.eq(0).all()
    assert_frame_equal(tel, before)


def test_telemetry_interpolation_and_shorter_lap():
    a, b = telemetry(), telemetry()
    b["Distance"] = [0.0, 60.0]
    b["Speed"] = [90.0, 150.0]
    out = compare_telemetry(a, b)
    assert out.Distance.iloc[-1] == 60
    assert out.SpeedA.iloc[3] == 130
    assert out.SpeedB.iloc[3] == 120
    assert out.ThrottleA.iloc[3] == 30
    assert out.SpeedDelta.iloc[3] == 10
    assert not out.BrakeA.iloc[4] and out.BrakeA.iloc[5]


@pytest.mark.parametrize("size", [0, 1])
@pytest.mark.parametrize("side", ["a", "b"])
def test_telemetry_insufficient(size, side):
    tel = telemetry()
    out = compare_telemetry(
        tel.iloc[:size] if side == "a" else tel, tel.iloc[:size] if side == "b" else tel
    )
    assert out.empty
    assert_schema(out, COMPARISON)


@pytest.mark.parametrize("step", [0, -10, np.nan, np.inf])
def test_bad_step(step):
    with pytest.raises(ValueError):
        compare_telemetry(telemetry(), telemetry(), step_m=step)


@pytest.mark.parametrize(
    "seconds,expected",
    [
        (83.456, "1:23.456"),
        (23.456, "0:23.456"),
        (0.0, "0:00.000"),
        (120.0, "2:00.000"),
        (59.9996, "1:00.000"),
        (np.nan, "-"),
        (None, "-"),
    ],
)
def test_format_lap_time(seconds, expected):
    assert format_lap_time(seconds) == expected
