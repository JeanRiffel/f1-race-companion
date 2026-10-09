"""Cached wrapper keys, returned values, and retry behaviour."""

import importlib

import pytest
from conftest import APP
from factories import race_data, telemetry


@pytest.fixture
def cached_services(monkeypatch):
    monkeypatch.syspath_prepend(str(APP))
    services = importlib.import_module("services")
    for name in ("get_races", "get_race", "get_telemetry"):
        getattr(services, name).clear()
    yield services
    for name in ("get_races", "get_race", "get_telemetry"):
        getattr(services, name).clear()


@pytest.mark.parametrize(
    "name,source,args,changed",
    [
        ("get_races", "list_races", (2023,), (2024,)),
        ("get_race", "load_race", (2023, 5), (2023, 1)),
        ("get_telemetry", "load_fastest_lap_telemetry", (2023, 5, "AAA"), (2023, 5, "BBB")),
    ],
)
def test_cache_keys(cached_services, monkeypatch, name, source, args, changed):
    calls = []
    result = race_data() if name == "get_race" else telemetry()

    def load(*values):
        calls.append(values)
        return result

    monkeypatch.setattr(cached_services, source, load)
    wrapper = getattr(cached_services, name)
    wrapper(*args)
    wrapper(*args)
    wrapper(*changed)
    assert calls == [args, changed]


@pytest.mark.parametrize(
    "name,source,args",
    [
        ("get_races", "list_races", (2023,)),
        ("get_race", "load_race", (2023, 5)),
        ("get_telemetry", "load_fastest_lap_telemetry", (2023, 5, "AAA")),
    ],
)
def test_failures_are_not_cached(cached_services, monkeypatch, name, source, args):
    calls = []

    def fail(*values):
        calls.append(values)
        raise cached_services.F1DataError("Unavailable")

    monkeypatch.setattr(cached_services, source, fail)
    wrapper = getattr(cached_services, name)
    for _ in range(2):
        with pytest.raises(cached_services.F1DataError, match="Unavailable"):
            wrapper(*args)
    assert calls == [args, args]
