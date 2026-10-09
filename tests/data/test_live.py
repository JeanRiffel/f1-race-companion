"""Opt-in check that real FastF1 data matches our schemas. Run with: pytest -m network"""

import pytest

from f1companion.data import cache, enable_cache, load_fastest_lap_telemetry, load_race, schema

pytestmark = pytest.mark.network


def assert_schema(frame, contract):
    assert list(frame.columns) == list(contract)
    assert {name: str(dtype) for name, dtype in frame.dtypes.items()} == contract


def test_real_race_matches_schema(monkeypatch, tmp_path):
    monkeypatch.setattr(cache, "_enabled", None)
    enable_cache(tmp_path / "cache")
    race = load_race(2023, 1)
    assert race.info.event_name == "Bahrain Grand Prix"
    assert len(race.results) == 20
    assert not race.laps.empty
    assert_schema(race.laps, schema.LAPS)
    assert_schema(race.results, schema.RESULTS)
    assert_schema(race.track_status, schema.TRACK_STATUS)
    assert_schema(race.race_control, schema.RACE_CONTROL)
    telemetry = load_fastest_lap_telemetry(2023, 1, "VER")
    assert not telemetry.empty
    assert_schema(telemetry, schema.TELEMETRY)
