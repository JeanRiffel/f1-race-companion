# Phase 2 spec: data layer and caching

Status: ready to implement
Implementer: Codex
Read first: `CLAUDE.md`, `docs/architecture.md`, `docs/decisions.md`

## Goal

Build `src/f1companion/data/`, the only layer that talks to FastF1. It loads a race, normalizes FastF1's
objects into plain pandas DataFrames with a stable schema owned by this project, caches downloads on disk,
and turns FastF1 failures into friendly, typed errors. The analysis layer (phase 3+) must depend only on the
schema defined here, never on FastF1 column names or objects.

## Scope

In scope:

- Disk cache setup for FastF1
- Listing a season's completed races
- Loading one race (laps, results, track status, race control messages) into a `RaceData` object
- Loading one driver's fastest-lap car telemetry (for head-to-head)
- Error translation
- `scripts/precompute.py` to warm the cache
- Tests with fixture data, no network
- Doc updates (`docs/architecture.md`, `docs/decisions.md`)

Out of scope (do not build):

- Any analysis functions, charts, or Streamlit pages (phase 3)
- `st.cache_data` wrappers (phase 3, in `app/`; the data layer must not import Streamlit)
- Sprint races, qualifying, practice. Race session (`"R"`) only
- Weather data, position (X/Y) data, live timing

## Target versions

Verified against the installed environment: **FastF1 3.8.3**, pandas 2.3.3, Python 3.11. All signatures
below were checked against FastF1 3.8.3 source. Do not use any FastF1 API not listed here without checking
its signature in the installed package first.

| FastF1 API | Signature (3.8.3) | Notes |
|---|---|---|
| `fastf1.Cache.enable_cache` | `(cache_dir: str, ignore_version=False, force_renew=False, use_requests_cache=True)` | Raises `NotADirectoryError` if the dir doesn't exist, so create it first |
| `fastf1.Cache.offline_mode` | `(enabled: bool)` | Must be called after `enable_cache` |
| `fastf1.get_event_schedule` | `(year: int, *, include_testing=True, backend=None, force_ergast=False)` | Always pass `include_testing=False` |
| `fastf1.get_session` | `(year: int, gp: str \| int, identifier: int \| str \| None = None, *, backend=None, force_ergast=False)` | Raises `ValueError` for an invalid round |
| `Session.load` | `(*, laps=True, telemetry=True, weather=True, messages=True, livedata=None)` | |
| `Laps.pick_drivers` | `(identifiers: int \| str \| Iterable)` | Use this, not the deprecated `pick_driver` |
| `Laps.pick_fastest` | `(only_by_time=False) -> Lap \| None` | Returns `None` if there is no valid lap |
| `Lap.get_car_data` | `(**kwargs) -> Telemetry` | Needs `load(telemetry=True)` |
| `Telemetry.add_distance` | `(drop_existing=True) -> Telemetry` | Adds a `Distance` column (metres) |
| `fastf1.set_log_level` | `(level: str \| int)` | Set to `"WARNING"` when enabling the cache |
| `fastf1.exceptions` | `DataNotLoadedError`, `InvalidSessionError`, `NoLapDataError`, `RateLimitExceededError`, `FastF1CriticalError` | |

FastF1 source columns used (3.8.3):

- `session.laps`: `Driver`, `DriverNumber`, `Team`, `LapNumber`, `Position`, `LapTime` (timedelta),
  `Stint`, `Compound`, `TyreLife`, `FreshTyre`, `PitInTime`, `PitOutTime`, `TrackStatus`, `IsAccurate`,
  `Deleted`
- `session.results`: `DriverNumber`, `Abbreviation`, `FullName`, `TeamName`, `TeamColor` (hex without
  `#`, may be empty), `GridPosition`, `Position`, `ClassifiedPosition`, `Status`, `Points`, `Laps`
- `session.track_status`: `Time` (session timedelta), `Status` (string code), `Message`
- `session.race_control_messages`: `Time` (UTC datetime), `Category`, `Message`, `Status`, `Flag`,
  `Scope`, `Sector`, `RacingNumber`, `Lap`
- `session.event`: `RoundNumber`, `EventName`, `Country`, `Location`, `EventDate`
- event schedule: `RoundNumber`, `EventName`, `Country`, `Location`, `EventDate`
- car data: `Speed`, `Throttle`, `Brake`, `nGear`, plus `Distance` after `add_distance()`

## Module layout

```
src/f1companion/data/
├── __init__.py      # re-exports the public API below; keep the existing docstring
├── cache.py         # FastF1 disk cache setup
├── errors.py        # project exception types
├── schema.py        # output column names, dtypes, track status labels, empty-frame helper
├── models.py        # RaceInfo, RaceData dataclasses
├── normalize.py     # pure functions: FastF1-shaped DataFrame in, project-schema DataFrame out
└── loader.py        # the only module that imports fastf1 (besides cache.py)
```

Rules:

- Only `cache.py` and `loader.py` import `fastf1`. `normalize.py` and `schema.py` import only pandas/numpy,
  so they can be tested with plain DataFrames.
- No Streamlit imports anywhere under `src/`.
- Every public function has type hints and a short docstring.

## Public API

Exported from `f1companion.data`:

```python
enable_cache(cache_dir: str | Path | None = None, *, offline: bool = False) -> Path
list_races(year: int, *, today: date | None = None) -> pd.DataFrame
load_race(year: int, round_number: int) -> RaceData
load_fastest_lap_telemetry(year: int, round_number: int, driver: str) -> pd.DataFrame
RaceInfo, RaceData
F1DataError, RaceNotFoundError, DataUnavailableError
```

A race is always identified by `(year, round_number)`, never by name. Round numbers are unambiguous and
make URLs easy to share in phase 3.

### `cache.py`: `enable_cache`

- Resolve the directory in this order: the `cache_dir` argument, then the `F1COMPANION_CACHE_DIR` env var,
  then `Path.cwd() / "data" / "fastf1_cache"`. (`data/` is already gitignored.)
- `mkdir(parents=True, exist_ok=True)`, then call `fastf1.Cache.enable_cache(str(path))`, then
  `fastf1.set_log_level("WARNING")`, then `fastf1.Cache.offline_mode(offline)`.
- Idempotent: track the enabled path in a module-level variable. A repeated call with the same resolved path
  and the same `offline` value does nothing. A call with a different path re-enables.
- Return the resolved absolute path.
- `loader.py` functions call `enable_cache()` (no args) at the start of every public function, so callers
  never have to remember. This relies on idempotency.

### `errors.py`

```python
class F1DataError(Exception):
    """Base class. `str(err)` is a short, friendly message safe to show to users."""


class RaceNotFoundError(F1DataError): ...  # bad year/round, or no race session exists


class DataUnavailableError(
    F1DataError
): ...  # race exists but data is missing, partial, rate-limited, or offline
```

Messages are plain English, no stack traces or FastF1 internals, for example
`"No race found for round 30 of 2024."` or `"Lap data isn't available for this race yet. Try again later."`.
Always chain the original exception (`raise ... from exc`) so debugging info isn't lost.

### `schema.py`

Define column-name constants (or one list per frame) and the dtype contract below. Provide
`empty_frame(columns: dict[str, str]) -> pd.DataFrame` that returns a zero-row DataFrame with the right
columns and dtypes, used whenever optional data is missing.

`TRACK_STATUS_LABELS: dict[str, str]`:

| Code | Label |
|---|---|
| `"1"` | `"Green"` |
| `"2"` | `"Yellow"` |
| `"4"` | `"Safety Car"` |
| `"5"` | `"Red Flag"` |
| `"6"` | `"VSC"` |
| `"7"` | `"VSC Ending"` |

Unknown codes map to `"Unknown"`.

`DEFAULT_TEAM_COLOR = "#888888"`.

### `models.py`

```python
@dataclass(frozen=True)
class RaceInfo:
    year: int
    round_number: int
    event_name: str
    country: str
    location: str
    date: datetime.date


@dataclass(frozen=True)
class RaceData:
    info: RaceInfo
    laps: pd.DataFrame  # LAPS schema
    results: pd.DataFrame  # RESULTS schema
    track_status: pd.DataFrame  # TRACK_STATUS schema, may be empty
    race_control: pd.DataFrame  # RACE_CONTROL schema, may be empty
```

### Output schemas (`normalize.py` produces these)

Use pandas nullable dtypes (`Int64`, `boolean`, `string`) where values can be missing. Output columns
appear in exactly this order, and no other columns are included.

**LAPS**, one row per driver per lap, sorted by `LapNumber` then `Driver`:

| Column | Dtype | Source / rule |
|---|---|---|
| `Driver` | string | `Driver` (3-letter abbreviation) |
| `DriverNumber` | string | `DriverNumber` |
| `Team` | string | `Team` |
| `LapNumber` | Int64 | `LapNumber` |
| `Position` | Int64 | `Position` (missing stays `<NA>`) |
| `LapTimeSeconds` | float64 | `LapTime.dt.total_seconds()`, NaN if missing |
| `Stint` | Int64 | `Stint` |
| `Compound` | string | `Compound`, upper-cased; missing or empty becomes `"UNKNOWN"` |
| `TyreLife` | float64 | `TyreLife` |
| `FreshTyre` | boolean | `FreshTyre` |
| `IsPitInLap` | bool | `PitInTime.notna()` |
| `IsPitOutLap` | bool | `PitOutTime.notna()` |
| `TrackStatus` | string | `TrackStatus` (may hold several codes, e.g. `"41"`; keep raw) |
| `IsAccurate` | bool | `IsAccurate`, missing becomes `False` |
| `Deleted` | bool | `Deleted`, missing becomes `False` |

**RESULTS**, one row per classified or entered driver, sorted by `Position` (missing last):

| Column | Dtype | Source / rule |
|---|---|---|
| `DriverNumber` | string | |
| `Driver` | string | `Abbreviation` |
| `FullName` | string | |
| `Team` | string | `TeamName` |
| `TeamColor` | string | `"#" + TeamColor`, lower-cased; empty/missing/invalid becomes `DEFAULT_TEAM_COLOR` |
| `GridPosition` | Int64 | `0` or missing becomes `<NA>` (pit lane start) |
| `Position` | Int64 | |
| `ClassifiedPosition` | string | e.g. `"1"`, `"R"`, `"D"` |
| `Status` | string | e.g. `"Finished"`, `"+1 Lap"`, `"Retired"` |
| `Points` | float64 | missing becomes `0.0` |
| `LapsCompleted` | Int64 | `Laps` |

A valid `TeamColor` is exactly 6 hex digits.

**TRACK_STATUS**, sorted by `TimeSeconds`:

| Column | Dtype | Source / rule |
|---|---|---|
| `TimeSeconds` | float64 | `Time.dt.total_seconds()` (session time) |
| `Status` | string | raw code |
| `Label` | string | `TRACK_STATUS_LABELS.get(code, "Unknown")` |
| `Message` | string | |

**RACE_CONTROL**, sorted by `Time`:

| Column | Dtype | Source / rule |
|---|---|---|
| `Time` | datetime64[ns, UTC] | `Time`, localized to UTC if naive |
| `Lap` | Int64 | |
| `Category` | string | |
| `Flag` | string | |
| `Message` | string | |

**TELEMETRY** (from `load_fastest_lap_telemetry`), sorted by `Distance`:

| Column | Dtype | Source / rule |
|---|---|---|
| `Distance` | float64 | metres from lap start |
| `Speed` | float64 | km/h |
| `Throttle` | float64 | 0 to 100 |
| `Brake` | bool | |
| `Gear` | Int64 | `nGear` |

**RACES** (from `list_races`), sorted by `RoundNumber`:

| Column | Dtype |
|---|---|
| `RoundNumber` | Int64 |
| `EventName` | string |
| `Country` | string |
| `Location` | string |
| `EventDate` | datetime64[ns] (date only, time 00:00) |

Normalize functions (all pure, each takes the raw FastF1-shaped DataFrame):

```python
normalize_laps(raw: pd.DataFrame) -> pd.DataFrame
normalize_results(raw: pd.DataFrame) -> pd.DataFrame
normalize_track_status(raw: pd.DataFrame | None) -> pd.DataFrame      # None/empty -> empty_frame
normalize_race_control(raw: pd.DataFrame | None) -> pd.DataFrame      # None/empty -> empty_frame
normalize_telemetry(raw: pd.DataFrame) -> pd.DataFrame
normalize_schedule(raw: pd.DataFrame, today: date) -> pd.DataFrame
```

- `normalize_schedule` drops rows with `RoundNumber == 0` and rows whose `EventDate` (as a date) is after
  `today`.
- `normalize_laps` and `normalize_results` raise `DataUnavailableError` if `raw` is missing a required
  source column, so FastF1 schema drift surfaces as a clear error rather than a `KeyError`.
- They must not modify their input.

### `loader.py`

All three functions call `enable_cache()` first. The FastF1 entry points are reached through two
module-level functions so tests can monkeypatch one seam:

```python
def _get_session(year: int, round_number: int) -> "fastf1.core.Session":
    return fastf1.get_session(year, round_number, "R")


def _get_schedule(year: int) -> pd.DataFrame:
    return fastf1.get_event_schedule(year, include_testing=False)
```

**`list_races(year, *, today=None)`**: `today` defaults to `date.today()`. Returns
`normalize_schedule(_get_schedule(year), today)`. Translate errors as below.

**`load_race(year, round_number)`**:

1. `session = _get_session(year, round_number)`
2. `session.load(laps=True, telemetry=False, weather=False, messages=True)`. Telemetry is the slow part
   and isn't needed here.
3. If `session.laps` is empty, raise `DataUnavailableError`.
4. Build `RaceInfo` from `session.event` (`EventDate` becomes `.date()`).
5. `track_status` and `race_control_messages`: read inside `try/except DataNotLoadedError`; on failure or
   `None`, pass `None` to the normalizer (empty frame). Missing optional data must never fail the load.
6. Return `RaceData`.

**`load_fastest_lap_telemetry(year, round_number, driver)`**:

1. `session = _get_session(...)`, `session.load(laps=True, telemetry=True, weather=False, messages=False)`
2. `lap = session.laps.pick_drivers(driver.upper()).pick_fastest()`
3. If `lap is None`, raise `DataUnavailableError(f"No valid lap found for {driver} in this race.")`
4. `normalize_telemetry(lap.get_car_data().add_distance())`
5. An empty telemetry result raises `DataUnavailableError`

**Error translation** (one private helper or context manager used by all three functions):

| Raised by FastF1 / stack | Becomes |
|---|---|
| `ValueError` from `get_session` / `get_event_schedule` (invalid round or year) | `RaceNotFoundError` |
| `fastf1.exceptions.InvalidSessionError` | `RaceNotFoundError` |
| `fastf1.exceptions.NoLapDataError`, `DataNotLoadedError` | `DataUnavailableError` |
| `fastf1.exceptions.RateLimitExceededError` | `DataUnavailableError("Data source is rate-limiting requests. Try again in a few minutes.")` |
| `requests.exceptions.ConnectionError`, `requests.exceptions.Timeout` | `DataUnavailableError` (offline / network) |
| `F1DataError` | re-raised unchanged |

Translate only `ValueError`s raised by the FastF1 calls themselves (wrap just those calls), not ones from
our own normalization code. Anything else propagates unchanged. Don't swallow unknown exceptions.

## `scripts/precompute.py`

Replace the stub. CLI using `argparse`:

```
python scripts/precompute.py --year 2024 [--rounds 1 2 5] [--with-telemetry DRIVER [DRIVER ...]] [--cache-dir PATH]
```

- `--rounds` defaults to every round returned by `list_races(year)`.
- For each round: `load_race`. If `--with-telemetry` is given, also call `load_fastest_lap_telemetry` for
  each listed driver (this warms FastF1's telemetry cache for that session).
- Print one progress line per race (`[3/24] 2024 R3 Australian Grand Prix ... ok (12.4s)`). On an
  `F1DataError`, print the message, continue, and remember the failure.
- Exit code `0` if everything succeeded, `1` if any race failed.
- Use only `f1companion.data`, never `fastf1` directly.
- Keep `main(argv: list[str] | None = None) -> int` so it's testable, with
  `if __name__ == "__main__": raise SystemExit(main())`.

## Tests

Location: `tests/data/`. No test may touch the network.

- `tests/conftest.py`: an **autouse** fixture that monkeypatches `fastf1.get_session`,
  `fastf1.get_event_schedule`, and `f1companion.data.loader._get_session` / `_get_schedule` to raise
  `AssertionError("network access in tests")`. Tests that need them re-patch with fakes. Also autouse-patch
  `enable_cache` usage in the loader to point at `tmp_path` (or monkeypatch `F1COMPANION_CACHE_DIR`), so
  tests never create `./data`.
- `tests/data/fixtures.py` (or `conftest.py` under `tests/data/`): small builder functions returning
  FastF1-shaped raw DataFrames (3 drivers, about 5 laps, timedeltas, one pit stop, one DNF, one missing
  `TeamColor`, one SC track status), and a `FakeSession` / `FakeLaps` / `FakeLap` (simple classes or
  `SimpleNamespace`) with `load()`, `laps`, `results`, `track_status`, `race_control_messages`, `event`,
  `pick_drivers`, `pick_fastest`, `get_car_data`, `add_distance`. `FakeSession.load` records its kwargs so
  tests can assert `telemetry=False` in `load_race`.

Required test cases (at least):

- `normalize_laps`: exact columns and order; dtypes; `LapTimeSeconds` from timedelta; NaT becomes NaN;
  `Compound` missing becomes `"UNKNOWN"`; pit in/out flags; sort order; input not mutated; missing source
  column raises `DataUnavailableError`.
- `normalize_results`: `TeamColor` with `#`, plus fallback for empty and invalid values; `GridPosition` 0
  becomes `<NA>`; DNF row has `<NA>` position and sorts last; `Points` missing becomes `0.0`.
- `normalize_track_status`: known codes labelled; unknown code becomes `"Unknown"`; `None` and empty input
  give an empty frame with correct columns.
- `normalize_race_control`: naive datetimes become UTC; `None` gives an empty frame.
- `normalize_telemetry`: `nGear` becomes `Gear`; sorted by distance.
- `normalize_schedule`: future events and round 0 excluded; boundary (`EventDate == today`) included.
- `load_race`: happy path returns `RaceData` with correct `RaceInfo`; `load` called with `telemetry=False`;
  missing race control (property raises `DataNotLoadedError`) gives an empty frame, not an error; empty
  laps raise `DataUnavailableError`.
- Error translation: `ValueError`, `InvalidSessionError` become `RaceNotFoundError`;
  `RateLimitExceededError`, `requests.ConnectionError` become `DataUnavailableError`; original exception
  is preserved as `__cause__`.
- `load_fastest_lap_telemetry`: happy path; `pick_fastest` returning `None` raises `DataUnavailableError`;
  driver is upper-cased.
- `enable_cache`: creates the dir; env var respected; argument beats env var; idempotent (FastF1's
  `enable_cache` called once for repeated calls; monkeypatch `fastf1.Cache.enable_cache` and
  `offline_mode` to record calls).
- `precompute.main`: with `list_races` / `load_race` monkeypatched, returns `0` on success and `1` when one
  race raises `F1DataError`, and continues past the failure.

Keep `tests/test_smoke.py` passing.

### Optional live check (not run in CI)

Add one test in `tests/data/test_live.py` marked `@pytest.mark.network` that loads a real race (2023,
round 1) and asserts the output schemas. Register the marker in `pyproject.toml`
(`markers = ["network: hits the real FastF1 API; run with -m network"]`) and change `addopts` to
`"-ra -m 'not network'"` so it is skipped by default. It exists to catch drift between our fakes and real
FastF1. The conftest network guard must not block tests carrying this marker.

## Docs to update

- `docs/architecture.md`: add a "Data layer" section with the module table above, the
  `(year, round_number)` identity rule, and a note that downstream layers depend on the `schema.py`
  contract, not on FastF1.
- `docs/decisions.md`: append entries dated with the implementation date:
  1. **Own schema over FastF1 objects.** Normalize to plain DataFrames so analysis is testable without
     FastF1 and insulated from its column changes.
  2. **Race session only for the MVP.** Sprint and qualifying deferred to keep scope tight.
  3. **Two cache tiers.** FastF1's disk cache (in the data layer) plus `st.cache_data` (in `app/`,
     phase 3), so the data layer stays Streamlit-free and usable from scripts.
  4. **Telemetry loaded separately.** `load_race` skips telemetry because it dominates load time; it is
     fetched only for head-to-head.
- `README.md`: add `python scripts/precompute.py --year 2024` under "Run locally" as an optional step.

## Definition of done

- [ ] `ruff check .` and `ruff format --check .` pass
- [ ] `pytest` passes with no network access (try with networking disabled if possible)
- [ ] No file under `data/` is committed; nothing outside the files listed in this spec changed except
      `pyproject.toml` (marker and addopts only)
- [ ] `fastf1` is imported only in `data/cache.py` and `data/loader.py` (and `tests/`)
- [ ] No Streamlit import under `src/`
- [ ] Docs updated as listed
- [ ] Work done on a branch `feat/data-layer`, in small commits (e.g. `feat: add data layer schema and
      normalizers`, `feat: add race loader with error translation`, `feat: implement precompute script`,
      `docs: document data layer`)
