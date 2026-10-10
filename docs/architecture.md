# Architecture

Three layers, with dependencies pointing one way only:

```
FastF1 API ──> data/ ──> analysis/ ──> charts/ ──> app/ (Streamlit pages)
```

| Layer | Location | Responsibility | May import |
|---|---|---|---|
| Data | `src/f1companion/data/` | Load FastF1 sessions, manage the cache, normalise into DataFrames | FastF1, pandas |
| Analysis | `src/f1companion/analysis/` | Pure functions: DataFrame in, DataFrame out | pandas, numpy |
| Charts | `src/f1companion/charts/` | Build Plotly figures from analysis output | plotly, pandas |
| UI | `app/` | Arrange charts, handle user input and URL state | everything above, Streamlit |

## Rules

- The UI never calls FastF1 directly; it goes through the data layer.
- Analysis functions have no network access and no Streamlit imports, so they are tested with small fixture data.
- Chart builders return figures; pages only lay them out.
- Cached FastF1 data lives in `data/`, which is gitignored.

## Data layer

A race is identified by `(year, round_number)`. The public API is exported from
`f1companion.data`; consumers receive frozen `RaceInfo` and `RaceData` containers
with plain pandas DataFrames. Downstream layers depend on the ordered columns and
dtypes in `schema.py`, never on FastF1 objects or source column names.

| Module | Responsibility |
|---|---|
| `__init__.py` | Export the public API |
| `cache.py` | Configure FastF1 disk caching and offline mode |
| `errors.py` | Friendly typed errors for callers |
| `schema.py` | Ordered columns, dtypes, labels, and empty frames |
| `models.py` | Frozen race metadata and data containers |
| `normalize.py` | Pure source-frame normalization |
| `loader.py` | FastF1 session loading and error translation |

`load_race` skips telemetry and weather. Missing optional track status or race
control messages produce empty frames with the same schema. Telemetry is fetched
separately through `load_fastest_lap_telemetry`. Invalid requests raise
`RaceNotFoundError`; unavailable data and known network errors raise
`DataUnavailableError`, preserving their original exception as the cause.

The cache directory defaults to `data/fastf1_cache` under the current working
directory. An explicit argument to `enable_cache` overrides `F1COMPANION_CACHE_DIR`,
which overrides that default. Repeated calls with the same path and offline setting
are no-ops. Loaders call `ensure_cache()`, which enables the default cache only if nothing has been enabled yet, so
an explicit `enable_cache(...)` call (custom directory or offline mode) is never overridden.

`list_races` includes dates through today, including a race on today's date; this
calendar filter does not guarantee that same-day timing data is already available.
Tests replace the FastF1 entry points with fakes and block socket connections. One
opt-in test (`pytest -m network`) checks the schemas against real FastF1 data and is excluded from CI.

## Core analysis

Analysis functions accept project-schema DataFrames, preserve inputs, and return
plain DataFrames with explicit dtypes. Optional values and empty frames are handled
without importing presentation or network libraries.

| Module | Responsibility |
|---|---|
| `analysis/recap.py` | Starting grid, lap positions, final results, driver colours, approximate key events |
| `analysis/strategy.py` | Tyre stints, numbered pit stops, finishing-order stop summary |
| `analysis/head_to_head.py` | Accurate undeleted fastest laps and distance-grid interpolation |
| `analysis/formatting.py` | Readable lap times rounded to milliseconds |

## Charts

Chart builders accept analysis outputs and return Plotly figures. They use no fixed
width or page/background colour. Driver colours are supplied by callers, teammates
use dashed lines, and empty inputs return annotated figures.

| Module | Responsibility |
|---|---|
| `charts/theme.py` | Compound colours, fallback driver colour, horizontal legend, empty figures |
| `charts/positions.py` | Position traces, starting grid at lap zero, leader on top |
| `charts/strategy.py` | Horizontal compound traces in finishing order |
| `charts/telemetry.py` | Shared-distance speed, throttle, and step-line brake traces |

## App

| Module | Responsibility |
|---|---|
| `app/main.py` | Shared race selector, season fallback, URL state, explicit navigation |
| `app/services.py` | Cached public data API wrappers and friendly known-error presentation |
| `app/components/race_header.py` | Race title, location/date, shared disclaimer |
| `app/pages/recap.py` | Final classification, position chart, key events and explanations |
| `app/pages/strategy.py` | Tyre timeline and complete driver pit-stop summary |
| `app/pages/head_to_head.py` | Driver selection, lap-time metrics, separate telemetry requests |

FastF1's disk cache remains in the data layer; `st.cache_data` now wraps the public
API in `app/services.py`. Calendars expire after one hour; race and per-driver
telemetry use separate cache keys. Known data failures propagate without being
cached and are displayed as short messages.

The shell accepts `year` and `round` on initial load, rejects invalid values, and
keeps the selected race in session state. It rewrites race query parameters after
navigation on each shell run and preserves unrelated parameters, including repeated
values. The head-to-head page owns `d1` and `d2`; its driver selection is saved
separately from widget state and scoped to the race. The shell preserves initial
driver URL values and restores saved driver choices when navigation clears query
parameters. See the AppTest limitation in `docs/decisions.md`.
