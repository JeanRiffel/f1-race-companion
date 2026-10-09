"""App services are replaced with project-schema fixtures; network guard stays active."""

import importlib
from pathlib import Path

import pandas as pd
import pytest
from factories import race_data, telemetry

APP = Path(__file__).resolve().parents[2] / "app"


@pytest.fixture
def app_services(monkeypatch):
    monkeypatch.syspath_prepend(str(APP))
    services = importlib.import_module("services")
    race = race_data()
    monkeypatch.setattr(services, "get_race", lambda year, round_number: race)
    monkeypatch.setattr(services, "get_telemetry", lambda *args: telemetry())
    monkeypatch.setattr(
        services,
        "get_races",
        lambda year: pd.DataFrame(
            {"RoundNumber": [1, 5], "EventName": ["First Grand Prix", "Fixture Grand Prix"]}
        ),
    )
    return services
