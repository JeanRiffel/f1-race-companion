"""Isolate offline tests; tests marked network are exempt from the guard."""

import socket

import fastf1
import pytest

from f1companion.data import cache, loader


@pytest.fixture(autouse=True)
def isolate_data(monkeypatch, tmp_path, request):
    if request.node.get_closest_marker("network"):
        return

    def blocked(*args, **kwargs):
        raise AssertionError("network access in tests")

    monkeypatch.setattr(fastf1, "get_session", blocked)
    monkeypatch.setattr(fastf1, "get_event_schedule", blocked)
    monkeypatch.setattr(loader, "_get_session", blocked)
    monkeypatch.setattr(loader, "_get_schedule", blocked)
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
    monkeypatch.setenv("F1COMPANION_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(loader, "ensure_cache", lambda: tmp_path / "cache")
    monkeypatch.setattr(cache, "_enabled", None)
