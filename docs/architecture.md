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
