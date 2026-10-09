"""Cache directory precedence and idempotency without network access."""

import fastf1

from f1companion.data import cache


def test_cache(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(fastf1.Cache, "enable_cache", lambda path: calls.append(("enable", path)))
    monkeypatch.setattr(
        fastf1.Cache, "offline_mode", lambda offline: calls.append(("offline", offline))
    )
    monkeypatch.setattr(fastf1, "set_log_level", lambda level: calls.append(("level", level)))
    env = tmp_path / "env"
    monkeypatch.setenv("F1COMPANION_CACHE_DIR", str(env))
    assert cache.enable_cache() == env.resolve()
    assert env.is_dir()
    cache.enable_cache()
    assert calls == [("enable", str(env.resolve())), ("level", "WARNING"), ("offline", False)]
    explicit = tmp_path / "explicit"
    assert cache.enable_cache(explicit, offline=True) == explicit.resolve()
    cache.enable_cache(explicit, offline=True)
    assert calls[-1] == ("offline", True)
    assert len(calls) == 6
    cache.enable_cache(explicit, offline=False)
    assert len(calls) == 9
    assert calls[-1] == ("offline", False)


def test_default_path(monkeypatch, tmp_path):
    monkeypatch.delenv("F1COMPANION_CACHE_DIR")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(fastf1.Cache, "enable_cache", lambda path: None)
    monkeypatch.setattr(fastf1.Cache, "offline_mode", lambda offline: None)
    monkeypatch.setattr(fastf1, "set_log_level", lambda level: None)
    assert cache.enable_cache() == tmp_path / "data" / "fastf1_cache"


def test_ensure_cache_enables_default_once(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(fastf1.Cache, "enable_cache", lambda path: calls.append(("enable", path)))
    monkeypatch.setattr(
        fastf1.Cache, "offline_mode", lambda offline: calls.append(("offline", offline))
    )
    monkeypatch.setattr(fastf1, "set_log_level", lambda level: None)
    env = tmp_path / "env"
    monkeypatch.setenv("F1COMPANION_CACHE_DIR", str(env))
    assert cache.ensure_cache() == env.resolve()
    assert cache.ensure_cache() == env.resolve()
    assert calls == [("enable", str(env.resolve())), ("offline", False)]


def test_ensure_cache_keeps_explicit_settings(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(fastf1.Cache, "enable_cache", lambda path: calls.append(("enable", path)))
    monkeypatch.setattr(
        fastf1.Cache, "offline_mode", lambda offline: calls.append(("offline", offline))
    )
    monkeypatch.setattr(fastf1, "set_log_level", lambda level: None)
    explicit = tmp_path / "explicit"
    cache.enable_cache(explicit, offline=True)
    calls.clear()
    assert cache.ensure_cache() == explicit.resolve()
    assert calls == []
    assert cache._enabled == (explicit.resolve(), True)
