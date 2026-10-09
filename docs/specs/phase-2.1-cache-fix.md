# Phase 2.1 spec: cache settings fix and live schema check

Status: ready to implement
Implementer: Codex
Branch: continue on `feat/data-layer` (do not create a new branch)
Read first: `docs/specs/phase-2-data-layer.md` (the parent spec). Everything in it still applies unless this
file says otherwise.

Do exactly what this spec says. Do not refactor, rename, or reformat anything else. If something here seems
wrong or impossible, stop and report it instead of improvising.

## Task 1 (required): loaders must not override the caller's cache settings

### The bug

`loader.py` calls `enable_cache()` with no arguments at the start of `list_races`, `load_race`, and
`load_fastest_lap_telemetry`. With no arguments, `enable_cache` resolves the **default** path with
`offline=False`, so it re-enables FastF1's cache whenever the caller had configured something else.

Reproduced against real FastF1:

```python
enable_cache("/tmp/my_cache", offline=True)
load_race(2023, 1)
# cache._enabled is now (Path.cwd()/"data"/"fastf1_cache", False): custom dir and offline mode both lost
```

This bug comes from the parent spec, not from your implementation. The `F1COMPANION_CACHE_DIR` workaround
you added in `scripts/precompute.py` is removed by this task, because the root cause gets fixed.

### Required behaviour

- If the caller has already called `enable_cache(...)`, loaders use that configuration unchanged.
- If nothing has been enabled yet, loaders enable the default (argument, then env var, then
  `data/fastf1_cache`, exactly as today).

### Change 1: `src/f1companion/data/cache.py`

Add this function below `enable_cache`. Do not change `enable_cache` itself.

```python
def ensure_cache() -> Path:
    """Enable the default cache only if no cache is enabled yet; return the active cache path."""
    if _enabled is None:
        return enable_cache()
    return _enabled[0]
```

`ensure_cache` is internal. Do **not** export it from `f1companion/data/__init__.py`.

### Change 2: `src/f1companion/data/loader.py`

- Change the import `from .cache import enable_cache` to `from .cache import ensure_cache`.
- In `list_races`, `load_race`, and `load_fastest_lap_telemetry`, replace the line `enable_cache()` with
  `ensure_cache()`.
- Nothing else changes in this file.

### Change 3: `scripts/precompute.py`

Remove the environment-variable workaround. The script now passes the cache dir directly.

- Delete `import os`.
- Delete the `previous = os.environ.get(...)` line, the `try:` / `finally:` block, and the comment
  `# Loaders call enable_cache() without arguments; ...`. Dedent the body that was inside `try:`.
- Replace the two lines

  ```python
  if args.cache_dir is not None:
      os.environ["F1COMPANION_CACHE_DIR"] = args.cache_dir
  enable_cache()
  ```

  with the single line

  ```python
  enable_cache(args.cache_dir)
  ```

  (`enable_cache(None)` already falls back to the env var, then the default.)
- The rest of `main` (round selection, progress lines, exit code) is unchanged.

### Change 4: tests

**`tests/conftest.py`**: replace

```python
monkeypatch.setattr(loader, "enable_cache", lambda: tmp_path / "cache")
```

with

```python
monkeypatch.setattr(loader, "ensure_cache", lambda: tmp_path / "cache")
```

**`tests/data/test_cache.py`**: add these two tests.

```python
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
```

**`tests/data/test_loader.py`**: add this regression test. It deliberately restores the real `ensure_cache`
that `conftest.py` stubs out, so the loader-to-cache path is actually exercised. Add
`from f1companion.data import cache` to the imports (merge it into the existing
`from f1companion.data import ...` line).

```python
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
```

**`tests/data/test_precompute.py`**:

- In the `cli` fixture, the stub must accept the new argument. Replace
  `monkeypatch.setattr(module, "enable_cache", lambda: None)` with
  `monkeypatch.setattr(module, "enable_cache", lambda cache_dir=None: None)`.
- Rewrite `test_explicit_rounds_and_cache` so it asserts the cache dir is **passed to `enable_cache`**
  rather than read from the environment:

  ```python
  def test_explicit_rounds_and_cache(cli, monkeypatch, tmp_path):
      enabled, seen = [], []
      path = str(tmp_path / "custom")
      monkeypatch.setattr(cli, "enable_cache", lambda cache_dir=None: enabled.append(cache_dir))

      def load(year, round_number):
          seen.append(round_number)
          return SimpleNamespace(info=SimpleNamespace(event_name="Race"))

      monkeypatch.setattr(cli, "load_race", load)
      assert cli.main(["--year", "2024", "--rounds", "5", "1", "--cache-dir", path]) == 0
      assert enabled == [path]
      assert seen == [5, 1]


  def test_default_cache_dir(cli, monkeypatch):
      enabled = []
      monkeypatch.setattr(cli, "enable_cache", lambda cache_dir=None: enabled.append(cache_dir))
      monkeypatch.setattr(
          cli, "load_race", lambda y, r: SimpleNamespace(info=SimpleNamespace(event_name="Race"))
      )
      assert cli.main(["--year", "2024", "--rounds", "1"]) == 0
      assert enabled == [None]
  ```

- Remove the `import os` from this test file if it is no longer used.

## Task 2 (required): live schema check against real FastF1

The parent spec listed this as optional, and it was skipped. It is now required: the fakes in
`tests/data/conftest.py` must be checked against real FastF1 data, or schema drift will go unnoticed.

### `pyproject.toml`

In `[tool.pytest.ini_options]`, change `addopts` and add `markers`. The result must be exactly:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra -m 'not network'"
markers = ["network: hits the real FastF1 API; run with -m network"]
```

No other changes to `pyproject.toml`.

### `tests/conftest.py`

The network guard must not apply to tests marked `network`. Add `request` to the fixture's parameters and
return early, before any patching, for those tests:

```python
@pytest.fixture(autouse=True)
def isolate_data(monkeypatch, tmp_path, request):
    if request.node.get_closest_marker("network"):
        return

    ...  # existing body unchanged
```

Update the module docstring to mention that tests marked `network` are exempt.

### New file `tests/data/test_live.py`

```python
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
```

This test downloads about 2 minutes of data on first run. It must **not** run in CI; the `addopts` change
above ensures that, and `.github/workflows/ci.yml` must not be modified.

## Task 3 (required): docs

- `docs/architecture.md`, in the "Data layer" section: replace the sentence
  "The CLI temporarily selects its custom cache through the environment so loaders' automatic cache setup
  uses the same directory." with:
  "Loaders call `ensure_cache()`, which enables the default cache only if nothing has been enabled yet, so
  an explicit `enable_cache(...)` call (custom directory or offline mode) is never overridden."
- In the same section, replace "Tests replace the FastF1 entry points with fakes and block socket
  connections." with: "Tests replace the FastF1 entry points with fakes and block socket connections. One
  opt-in test (`pytest -m network`) checks the schemas against real FastF1 data and is excluded from CI."
- `docs/decisions.md`: append

  ```markdown
  ## 2026-10-09: Loaders respect explicit cache settings

  Loaders call `ensure_cache()` instead of `enable_cache()`, so a caller's custom cache directory or offline
  mode is never reset to the default. This replaced an environment-variable workaround in
  `scripts/precompute.py`.
  ```

- Commit both spec files: `docs/specs/phase-2-data-layer.md` and `docs/specs/phase-2.1-cache-fix.md`.

## Commits

Make exactly these three commits, in this order, each ending with your normal attribution if any:

1. `fix: keep explicit cache settings when loaders run`: Task 1 (source and tests)
2. `test: add opt-in live FastF1 schema check`: Task 2
3. `docs: document cache fix and add phase 2 specs`: Task 3

## Verification (run all, report the output)

Before committing, run `.venv/bin/ruff format .` so new code (and Python blocks inside `docs/specs/*.md`,
which ruff also formats) is formatted.

Use `.venv/bin/python -m pytest`, not `.venv/bin/pytest` (the latter has a broken interpreter path in this
environment).

```bash
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m pytest                 # must pass; the live test must show as deselected
.venv/bin/python -m pytest -m network      # needs internet; must pass, report if it can't run
grep -rn "os.environ" scripts/precompute.py   # must print nothing
grep -rn "enable_cache()" src/f1companion/data/loader.py   # must print nothing
```

## Definition of done

- [ ] All verification commands above give the expected result
- [ ] `ensure_cache` exists in `cache.py`, is used by all three loader functions, and is not exported
- [ ] `scripts/precompute.py` contains no `os` import and no environment-variable handling
- [ ] The three new or rewritten regression tests exist and pass
- [ ] `tests/data/test_live.py` exists, is deselected by default, and passes with `-m network`
- [ ] `.github/workflows/ci.yml` unchanged
- [ ] No files changed other than those named in this spec
- [ ] Three commits on `feat/data-layer` with the messages above
