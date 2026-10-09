"""Exercise loading options, optional data, and exception boundaries."""

from datetime import date

import fastf1
import pytest
from fastf1.exceptions import (
    DataNotLoadedError,
    InvalidSessionError,
    NoLapDataError,
    RateLimitExceededError,
)
from requests.exceptions import ConnectionError, Timeout

from f1companion.data import (
    DataUnavailableError,
    F1DataError,
    RaceData,
    RaceNotFoundError,
    cache,
    loader,
)

_SESSION = loader._get_session
_SCHEDULE = loader._get_schedule


def test_race(monkeypatch, session):
    monkeypatch.setattr(loader, "_get_session", lambda y, r: session)
    out = loader.load_race(2024, 1)
    assert isinstance(out, RaceData)
    assert (
        out.info.year,
        out.info.round_number,
        out.info.event_name,
        out.info.country,
        out.info.location,
        out.info.date,
    ) == (2024, 1, "Bahrain Grand Prix", "Bahrain", "Sakhir", date(2024, 3, 2))
    assert session.load_calls == [dict(laps=True, telemetry=False, weather=False, messages=True)]
    assert not out.track_status.empty
    assert not out.race_control.empty


@pytest.mark.parametrize("missing", [None, DataNotLoadedError()])
def test_missing_control(monkeypatch, session, missing):
    session.control = missing
    session.track_status = None
    monkeypatch.setattr(loader, "_get_session", lambda y, r: session)
    out = loader.load_race(2024, 1)
    assert out.race_control.empty
    assert out.track_status.empty


def test_empty_laps(monkeypatch, session):
    session.laps = session.laps.iloc[:0]
    monkeypatch.setattr(loader, "_get_session", lambda y, r: session)
    with pytest.raises(DataUnavailableError):
        loader.load_race(2024, 1)


@pytest.mark.parametrize("function", ["race", "telemetry", "schedule"])
@pytest.mark.parametrize(
    "exc, expected",
    [
        (ValueError("bad"), RaceNotFoundError),
        (InvalidSessionError(), RaceNotFoundError),
        (RateLimitExceededError(), DataUnavailableError),
        (ConnectionError(), DataUnavailableError),
        (Timeout(), DataUnavailableError),
        (DataNotLoadedError(), DataUnavailableError),
        (NoLapDataError(), DataUnavailableError),
    ],
)
def test_errors(monkeypatch, function, exc, expected):
    def fail(*args):
        raise exc

    monkeypatch.setattr(loader, "_get_session", fail)
    monkeypatch.setattr(loader, "_get_schedule", fail)
    with pytest.raises(expected) as caught:
        if function == "race":
            loader.load_race(2024, 1)
        elif function == "telemetry":
            loader.load_fastest_lap_telemetry(2024, 1, "VER")
        else:
            loader.list_races(2024)
    assert caught.value.__cause__ is exc


@pytest.mark.parametrize(
    "exc", [ValueError("normalization"), RuntimeError("unexpected"), F1DataError("friendly")]
)
def test_non_source_errors_preserved(monkeypatch, session, exc):
    monkeypatch.setattr(loader, "_get_session", lambda y, r: session)

    def fail(*args):
        raise exc

    monkeypatch.setattr(loader, "normalize_laps", fail)
    with pytest.raises(type(exc)) as caught:
        loader.load_race(2024, 1)
    assert caught.value is exc


@pytest.mark.parametrize(
    "exc",
    [
        DataNotLoadedError(),
        NoLapDataError(),
        RateLimitExceededError(),
        ConnectionError(),
        Timeout(),
        InvalidSessionError(),
    ],
)
def test_load_errors(monkeypatch, session, exc):
    monkeypatch.setattr(loader, "_get_session", lambda y, r: session)

    def fail(**kwargs):
        raise exc

    session.load = fail
    with pytest.raises(F1DataError) as caught:
        loader.load_race(2024, 1)
    assert caught.value.__cause__ is exc


def test_telemetry(monkeypatch, session):
    monkeypatch.setattr(loader, "_get_session", lambda y, r: session)
    out = loader.load_fastest_lap_telemetry(2024, 1, "ver")
    assert session.laps.selected == "VER"
    assert out.Distance.tolist() == [0, 100]
    assert session.load_calls == [dict(laps=True, telemetry=True, weather=False, messages=False)]


def test_no_fastest(monkeypatch, session):
    session.laps.fastest = None
    monkeypatch.setattr(loader, "_get_session", lambda y, r: session)
    with pytest.raises(DataUnavailableError, match="No valid lap"):
        loader.load_fastest_lap_telemetry(2024, 1, "VER")


def test_empty_telemetry(monkeypatch, session):
    session.laps.fastest.raw = session.laps.fastest.raw.iloc[:0]
    monkeypatch.setattr(loader, "_get_session", lambda y, r: session)
    with pytest.raises(DataUnavailableError, match="Telemetry"):
        loader.load_fastest_lap_telemetry(2024, 1, "VER")


def test_list_races(monkeypatch, raw_schedule):
    monkeypatch.setattr(loader, "_get_schedule", lambda year: raw_schedule)
    assert loader.list_races(2024, today=date(2024, 3, 2)).RoundNumber.tolist() == [1, 2]
    assert loader.list_races(2024).RoundNumber.tolist() == [1, 2, 3]


def test_source_seams(monkeypatch, session, raw_schedule):
    session_calls, schedule_calls = [], []

    def get_session(*args):
        session_calls.append(args)
        return session

    def get_schedule(*args, **kwargs):
        schedule_calls.append((args, kwargs))
        return raw_schedule

    # Restore the real wrappers while replacing their external dependencies.
    monkeypatch.setattr(fastf1, "get_session", get_session)
    monkeypatch.setattr(fastf1, "get_event_schedule", get_schedule)
    assert _SESSION(2024, 1) is session
    assert _SCHEDULE(2024) is raw_schedule
    assert session_calls == [(2024, 1, "R")]
    assert schedule_calls == [((2024,), {"include_testing": False})]


def test_load_race_keeps_explicit_cache_settings(monkeypatch, session, tmp_path):
    calls = []
    monkeypatch.setattr(fastf1.Cache, "enable_cache", lambda path: calls.append(path))
    monkeypatch.setattr(fastf1.Cache, "offline_mode", lambda offline: None)
    monkeypatch.setattr(fastf1, "set_log_level", lambda level: None)
    monkeypatch.setattr(loader, "ensure_cache", cache.ensure_cache)
    monkeypatch.setattr(loader, "_get_session", lambda y, r: session)
    explicit = tmp_path / "explicit"
    cache.enable_cache(explicit, offline=True)
    loader.load_race(2024, 1)
    loader.load_fastest_lap_telemetry(2024, 1, "VER")
    assert cache._enabled == (explicit.resolve(), True)
    assert calls == [str(explicit.resolve())]
