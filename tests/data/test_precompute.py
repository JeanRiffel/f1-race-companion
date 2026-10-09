"""CLI success, failure continuation, and cache path selection."""

import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from f1companion.data import F1DataError


@pytest.fixture
def cli(monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "precompute", Path(__file__).resolve().parents[2] / "scripts" / "precompute.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "enable_cache", lambda: None)
    return module


@pytest.mark.parametrize("failure", [False, True])
def test_continue(cli, monkeypatch, capsys, failure):
    calls, telemetry = [], []
    monkeypatch.setattr(cli, "list_races", lambda year: pd.DataFrame({"RoundNumber": [1, 2, 3]}))

    def load(year, round_number):
        calls.append((year, round_number))
        if failure and round_number == 2:
            raise F1DataError("Unavailable")
        return SimpleNamespace(info=SimpleNamespace(event_name="Grand Prix"))

    monkeypatch.setattr(cli, "load_race", load)
    monkeypatch.setattr(cli, "load_fastest_lap_telemetry", lambda *args: telemetry.append(args))
    assert cli.main(["--year", "2024", "--with-telemetry", "VER", "HAM"]) == int(failure)
    assert calls == [(2024, 1), (2024, 2), (2024, 3)]
    assert len(telemetry) == (4 if failure else 6)
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 3
    assert lines[-1].startswith("[3/3] 2024 R3 Grand Prix ... ok")
    assert "Unavailable" in lines[1] if failure else "ok" in lines[1]


def test_explicit_rounds_and_cache(cli, monkeypatch, tmp_path):
    seen = []
    old = os.environ["F1COMPANION_CACHE_DIR"]
    path = str(tmp_path / "custom")

    def load(year, round_number):
        seen.append((round_number, os.environ["F1COMPANION_CACHE_DIR"]))
        return SimpleNamespace(info=SimpleNamespace(event_name="Race"))

    monkeypatch.setattr(cli, "load_race", load)
    assert cli.main(["--year", "2024", "--rounds", "5", "1", "--cache-dir", path]) == 0
    assert seen == [(5, path), (1, path)]
    assert os.environ["F1COMPANION_CACHE_DIR"] == old


def test_schedule_failure(cli, monkeypatch, capsys):
    def fail(year):
        raise F1DataError("Schedule unavailable")

    monkeypatch.setattr(cli, "list_races", fail)
    assert cli.main(["--year", "2024"]) == 1
    assert "Schedule unavailable" in capsys.readouterr().out
