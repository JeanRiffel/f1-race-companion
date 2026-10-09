# Phase 3 spec: core views (recap, strategy, head-to-head)

Status: ready to implement
Implementer: Codex
Reviewer: Claude (will verify against the acceptance checklist at the bottom)
Read first: `CLAUDE.md`, `docs/architecture.md`, `docs/decisions.md`, `src/f1companion/data/schema.py`,
`src/f1companion/data/models.py`

## Goal

Turn the placeholder app into three working views for one selected race: **Recap**, **Strategy**,
**Head-to-head**. A fan opens the link, picks a race, and understands it in under a minute. Everything is
built on the phase 2 data layer and its schemas. Nothing in this phase touches FastF1 directly.

## Scope

In scope:

- `src/f1companion/analysis/`: pure functions for recap, strategy, head-to-head (module list below)
- `src/f1companion/charts/`: Plotly figure builders
- `app/`: Streamlit shell (navigation, race selector, URL state), cached data access, three pages
- Tests for analysis, charts, and an app smoke test, all without network
- Doc updates

Out of scope (do NOT build; ask first if you think something here is needed):

- Race story summary, tire degradation, race-pace-vs-finish metric (phase 4)
- Changes to `src/f1companion/data/` (if you believe the data layer must change, stop and report why)
- Sprint/qualifying/practice sessions, weather, track map, deploy config, screenshots
- Changes to `scripts/precompute.py` or CI

## Branch and git

- Create branch `feat/core-views` from the current branch (`feat/data-layer`).
- Small commits with conventional messages (`feat: add position-by-lap analysis`). Suggested order:
  analysis -> charts -> app shell -> pages -> docs. Run lint and tests before each commit.
- Do not push, merge, or open a PR. Do not commit `data/` or any cache.
- End commit messages with the attribution line you normally use.

## Verified environment

Python 3.11 venv at `.venv` (use `.venv/bin/python`, `.venv/bin/pytest`, `.venv/bin/ruff`). Installed:
Streamlit 1.64.0, Plotly 7.1.0, pandas 2.3.x. Signatures below were checked against the installed
Streamlit:

| API | Signature (relevant part) |
|---|---|
| `st.navigation` | `(pages, *, position="sidebar", expanded=False) -> Page`; call `.run()` on the result |
| `st.Page` | `(page: str \| Path \| Callable, *, title=None, icon=None, url_path=None, default=False)` |
| `st.query_params` | dict-like proxy; assigning a value updates the URL |
| `st.cache_data` | `(func=None, *, ttl=None, max_entries=None, show_spinner=True, ...)`; `show_spinner` may be a string |
| `st.plotly_chart` | `(figure, *, width="stretch", height="content", theme="streamlit", key=None, config=None, ...)`; do not use the deprecated `use_container_width` |
| `st.selectbox` | `(label, options, index=0, format_func=str, key=None, help=None, ...)` |

Check any other Streamlit or Plotly call you are unsure about with `inspect.signature` before using it.

## Architecture rules (unchanged, enforced in review)

- `analysis/` imports only pandas/numpy (and `f1companion.data.schema` for column constants). No
  Streamlit, no Plotly, no FastF1, no network.
- `charts/` imports plotly and pandas only. Functions take analysis output and return `go.Figure`. They
  never call analysis or data code.
- `app/` is the only place that imports Streamlit. It reaches data only through `f1companion.data`, via
  the cached wrappers in `app/services.py`. It never imports `fastf1`.
- Pages arrange charts and text. They contain no DataFrame wrangling beyond selecting/passing frames.
- All public functions: type hints and a one-to-three line docstring.
- Do not mutate input DataFrames.
- Input frames follow the schemas in `f1companion.data.schema` (nullable dtypes: `Int64`, `string`,
  `boolean`). Handle `<NA>` explicitly.

## Analysis layer (`src/f1companion/analysis/`)

Add these modules and re-export the public functions from `analysis/__init__.py`.

### `recap.py`

```python
def position_by_lap(laps: pd.DataFrame, results: pd.DataFrame) -> pd.DataFrame
def final_results(results: pd.DataFrame) -> pd.DataFrame
def key_events(laps: pd.DataFrame, results: pd.DataFrame) -> pd.DataFrame
def driver_colors(results: pd.DataFrame) -> dict[str, str]
```

**`position_by_lap`**: long format, columns `Driver` (string), `LapNumber` (Int64), `Position` (Int64),
sorted by `Driver`, `LapNumber`.
- One row per driver per lap from `laps`, dropping rows where `Position` is `<NA>`.
- Plus a lap `0` row per driver from `results.GridPosition` (the starting grid), skipping `<NA>` grid
  positions (pit-lane starts).

**`final_results`**: display-ready, same row order as `results`. Columns: `Position` (string, the
`ClassifiedPosition`), `Driver`, `FullName`, `Team`, `Grid` (Int64, from `GridPosition`),
`PositionsGained` (Int64, `Grid - Position`, `<NA>` if either is missing), `Status`, `Points` (float64).

**`key_events`**: columns `Type` (string), `StartLap` (Int64), `EndLap` (Int64), `Description` (string),
sorted by `StartLap`, then `Type`. Returns an empty frame with those columns (correct dtypes) if there are
no events. Two sources, both from the project schema only:
1. Neutralisations from `laps.TrackStatus`. For each `LapNumber`, a lap is "under" a condition if any
   driver's raw `TrackStatus` string contains the code: `"4"` -> `"Safety Car"`, `"6"` or `"7"` ->
   `"Virtual Safety Car"`, `"5"` -> `"Red Flag"`. Merge consecutive laps of the same type into one event.
   Description: `"Safety Car on lap 12"` or `"Safety Car on laps 12-15"`. Skip `<NA>` statuses.
2. Retirements from `results` rows where `ClassifiedPosition == "R"`. `StartLap == EndLap ==
   max(LapsCompleted, 1)` (`<NA>` laps counts as 1). `Type = "Retirement"`. Description:
   `"{FullName} ({Team}) retired after lap {n}: {Status}"`.

Document in the docstring that lap-level track status is approximate (a condition that starts mid-lap marks
that lap).

**`driver_colors`**: `{Driver: TeamColor}` from `results`.

### `strategy.py`

```python
def stints(laps: pd.DataFrame) -> pd.DataFrame
def pit_stops(laps: pd.DataFrame) -> pd.DataFrame
```

**`stints`**: one row per driver per stint. Columns `Driver`, `Team`, `Stint` (Int64), `Compound`
(string), `StartLap`, `EndLap`, `LapCount` (all Int64). Sorted by `Driver`, `Stint`. Drop rows where
`Stint` is `<NA>`. `StartLap`/`EndLap` are min/max `LapNumber` of the stint, `LapCount = EndLap -
StartLap + 1`. `Compound` is the first non-`"UNKNOWN"` compound in the stint (by lap order), else
`"UNKNOWN"`.

**`pit_stops`**: one row per lap where `IsPitInLap` is true. Columns `Driver`, `LapNumber` (Int64, the
in-lap), `StopNumber` (Int64, 1-based per driver in lap order). Sorted by `Driver`, `StopNumber`.

### `head_to_head.py`

```python
def fastest_laps(laps: pd.DataFrame) -> pd.DataFrame
def compare_telemetry(tel_a: pd.DataFrame, tel_b: pd.DataFrame, *, step_m: float = 10.0) -> pd.DataFrame
```

**`fastest_laps`**: one row per driver with their quickest valid lap. Valid = `IsAccurate` true,
`Deleted` false, `LapTimeSeconds` not NaN. Columns `Driver`, `LapNumber` (Int64), `LapTimeSeconds`
(float64), `Compound` (string). Sorted by `LapTimeSeconds`. Drivers with no valid lap are omitted.

**`compare_telemetry`**: inputs are two TELEMETRY-schema frames (from `load_fastest_lap_telemetry`).
Resample both onto a shared distance grid `0, step_m, 2*step_m, ... <= min(max Distance of a, max
Distance of b)` using `np.interp`. Output columns: `Distance`, `SpeedA`, `SpeedB`, `ThrottleA`,
`ThrottleB` (float64), `BrakeA`, `BrakeB` (bool; interpolate the 0/1 value, then `>= 0.5`), `SpeedDelta`
(`SpeedA - SpeedB`). If either input is empty or has fewer than 2 rows, return an empty frame with these
columns. Raise `ValueError` if `step_m <= 0`.

### `formatting.py`

```python
def format_lap_time(seconds: float) -> str   # 83.456 -> "1:23.456"; NaN/None -> "-"
```

## Charts layer (`src/f1companion/charts/`)

Common rules: no hard-coded page/background colours or Plotly templates (rely on the Streamlit theme so
light and dark modes both work), legend at the bottom horizontal (`orientation="h"`,
`y=-0.2`) so it works on a phone, no fixed pixel width, sensible fixed `height`, axis titles in plain
English, hover text readable. Team/driver colors come from the `colors` argument, never invented in the
chart. Constants shared by charts live in `charts/theme.py`.

```python
# charts/positions.py
def position_chart(positions: pd.DataFrame, colors: dict[str, str]) -> go.Figure
# charts/strategy.py
def strategy_chart(stints: pd.DataFrame, driver_order: list[str]) -> go.Figure
# charts/telemetry.py
def telemetry_chart(comparison: pd.DataFrame, driver_a: str, driver_b: str,
                    color_a: str, color_b: str) -> go.Figure
```

- **`position_chart`**: one line per driver (`Scatter`, `mode="lines"`, `name=Driver`), x = lap
  (0 = grid), y = position with the axis **reversed** (P1 on top), integer ticks, y range 0.5 to
  max(position)+0.5. Hover shows driver, lap, position. Driver colour from `colors`, fallback
  `DEFAULT_TEAM_COLOR`. Teammates share a colour, so iterate drivers in sorted order and give any driver
  whose colour was already used by an earlier driver a `dash="dash"` line.
- **`strategy_chart`**: horizontal stacked-timeline using `go.Bar(orientation="h")`, one trace per
  compound (so the legend lists compounds), `base=StartLap - 1`, `x=LapCount`, `y=Driver`. y-axis
  categories follow `driver_order` with the first driver on top (finishing order). Compound colours from
  `COMPOUND_COLORS` in `charts/theme.py` (SOFT red, MEDIUM yellow, HARD light grey, INTERMEDIATE green,
  WET blue, UNKNOWN mid grey). Add a thin dark outline (`marker.line`) so light bars are visible on a
  white background. Show the compound's first letter as bar text. x-axis title "Lap".
- **`telemetry_chart`**: three stacked rows sharing the x-axis (`make_subplots(rows=3, shared_xaxes=True)`):
  Speed (km/h), Throttle (%), Brake (on/off, drawn as a step line `line_shape="hv"` with 0/1). Two traces
  per row (driver A, driver B). If `color_a == color_b` (teammates), draw driver B dashed. Legend shows each
  driver once (`legendgroup`, `showlegend` only on the first row). x-axis title "Distance along the lap
  (m)". Hover mode `x unified`.

Charts must handle an empty input frame by returning a figure with an annotation such as "No data to
show" instead of raising.

## App layer (`app/`)

### Structure

```
app/
├── main.py            # shell: page config, sidebar race selector, URL state, st.navigation
├── services.py        # st.cache_data wrappers around f1companion.data
├── components/
│   ├── __init__.py
│   └── race_header.py # title + date/location line + disclaimer footer helper
└── pages/
    ├── recap.py
    ├── strategy.py
    └── head_to_head.py
```

Streamlit puts the entry script's folder (`app/`) on `sys.path`, so inside `app/` import siblings as
top-level modules: `import services`, `from components.race_header import ...`. If ruff's isort grouping
then misclassifies them, add `"services"` and `"components"` to `known-first-party` in
`pyproject.toml`. Keep pages as plain scripts that Streamlit executes (each page ends up calling a
`render()` function or runs top-level; your choice, but be consistent).

### `services.py`

Cached wrappers; this is the only app module that imports `f1companion.data`:

```python
@st.cache_data(ttl=3600, show_spinner="Loading the calendar...")
def get_races(year: int) -> pd.DataFrame: ...

@st.cache_data(show_spinner="Loading race data (the first load of a race can take a minute)...")
def get_race(year: int, round_number: int) -> RaceData: ...

@st.cache_data(show_spinner="Loading telemetry...")
def get_telemetry(year: int, round_number: int, driver: str) -> pd.DataFrame: ...
```

Errors: these let `F1DataError` propagate (Streamlit does not cache exceptions). Add a helper
`def show_data_error(err: F1DataError) -> NoReturn` that renders `st.error(str(err))` plus a short hint
and calls `st.stop()`. Pages and the shell wrap data calls in `try/except F1DataError` and use it.
Users must never see a traceback for a known data failure.

### `main.py` (shell)

Runs on every rerun, before the selected page:

1. `st.set_page_config(page_title="F1 Race Companion", page_icon="🏁", layout="wide")`.
2. Sidebar race selector:
   - Year `selectbox`, options from 2018 to the current year, newest first (FastF1 lap data is reliable
     from 2018; mention this in the help text).
   - Race `selectbox` of that year's completed races from `get_races(year)`, labelled
     `"R{round}: {EventName}"`, passing `round_number` as the value via `format_func`.
   - If the year has no completed races yet (early season), show `st.info` and fall back to the previous
     year's list rather than failing.
3. **URL state**: read `year` and `round` from `st.query_params` on first load to preselect (ignore
   invalid values silently and fall back to defaults: latest year with races, last completed round).
   After every selection write `year` and `round` back to `st.query_params`. Do not drop other query
   params (the head-to-head page owns `d1`/`d2`). Opening `/?year=2023&round=5` must show that race.
4. Make the selection available to pages via `st.session_state["race_key"] = (year, round_number)`.
5. `pg = st.navigation([...])` with three `st.Page` entries from `app/pages/` (titles "Recap",
   "Strategy", "Head-to-head", with emoji icons; Recap is `default=True`), then `pg.run()`.
6. Sidebar footer: the disclaimer text (reuse the existing `DISCLAIMER` constant).

Note for you to verify while building: when switching pages through `st.navigation`, query params may be
reset by Streamlit. Test this (with `AppTest` and by reasoning; the reviewer will also check in a real
browser). Whatever the behaviour, ensure `year`/`round` survive page switches by re-writing them on every
run, and record the finding in `docs/decisions.md`.

### Pages

Every page: calls `get_race(*st.session_state["race_key"])` inside `try/except F1DataError`, renders
`race_header`, then its content. Each section has a one-sentence plain-English caption for casual fans.
Use `st.columns` / containers that stack on narrow screens (no side-by-side layouts that need width above
about 700px beyond a 2-column metric row). Charts use `st.plotly_chart(fig, width="stretch")`.

**Recap** (`pages/recap.py`)
1. Header: race name, location, date.
2. "Final classification": `st.dataframe` of `final_results` (hide index; use `column_config` for
   `Points`, `PositionsGained`). Caption: what Grid and Positions gained mean.
3. "How the race unfolded": `position_chart`. Caption: lines show each driver's position at the end of
   every lap; lap 0 is the starting grid.
4. "Key events": `key_events` table, or `st.info("No safety cars or retirements recorded.")` when empty.
   Caption explaining safety car / VSC / red flag in one line each (an `st.expander("What do these
   mean?")` is fine).

**Strategy** (`pages/strategy.py`)
1. `strategy_chart` with `driver_order` = `results.Driver` order (finishing order). Caption explaining
   compounds (soft = fastest but wears quickest, hard = slowest but lasts) and that each bar is a stint.
2. "Pit stops": a compact table of stops per driver (count and the laps), built from `pit_stops`.
   Drivers with zero stops still appear with `0`.

**Head-to-head** (`pages/head_to_head.py`)
1. Two `selectbox`es (driver A, driver B) listing `results.Driver` with full name via `format_func`.
   Defaults: P1 and P2 finishers, overridden by query params `d1`, `d2` when valid. Write the selection
   back to `d1`/`d2`.
2. If A == B: `st.warning("Pick two different drivers.")` and stop rendering the rest.
3. Row of fastest lap metrics from `fastest_laps` (`format_lap_time`, compound, lap number, and the gap).
   If a driver has no valid lap, show a friendly message for that driver instead.
4. Telemetry via `get_telemetry` for each driver (each in its own `try/except F1DataError`; if one fails,
   show that driver's message and skip the chart). `compare_telemetry` then `telemetry_chart` using
   `driver_colors`. Caption: speed, throttle (how far the accelerator is pressed), brake (on/off), and that
   the comparison is the two drivers' fastest laps of the race, which may have been on different tyres and
   fuel loads.
5. Wrap the telemetry section in a loading state (the cached wrapper's spinner is enough).

All pages: if a frame the page needs is empty (partial data), show `st.info` with a short explanation
rather than an empty chart or an exception.

## Tests

No test may touch the network (the existing autouse guard in `tests/conftest.py` stays). Do not weaken it.

- `tests/analysis/` and `tests/charts/`: build small schema-shaped fixtures with `f1companion.data.schema`
  (`empty_frame` plus appended rows, or a helper in `tests/factories.py`): 3 teams, 4 drivers (two
  teammates), 6 laps, one pit stop each for two drivers, one retirement (`ClassifiedPosition == "R"`),
  one pit-lane start (`GridPosition` `<NA>`), a Safety Car on laps 3-4 (`TrackStatus == "4"`) and a VSC on
  lap 6.
- Required analysis tests:
  - `position_by_lap`: lap-0 grid rows present; pit-lane start has no lap-0 row; `<NA>` positions dropped;
    columns, dtypes, sort order; input not mutated.
  - `final_results`: `PositionsGained` sign and `<NA>` handling; DNF row kept in place; columns.
  - `key_events`: SC laps 3-4 merge into one event; VSC single lap; combined statuses like `"41"` still
    detected; retirement lap and description; empty-frame schema when nothing happens; sorted.
  - `driver_colors`.
  - `stints`: stint boundaries, `LapCount`, compound fallback skips `UNKNOWN`, `<NA>` stints dropped.
  - `pit_stops`: in-laps only, `StopNumber` increments per driver, driver without a stop absent.
  - `fastest_laps`: inaccurate and deleted laps ignored; driver with no valid lap omitted; sorted.
  - `compare_telemetry`: grid length/step; interpolation values at a known point; different lap lengths use
    the shorter; brake boolean; `SpeedDelta`; empty input gives the empty schema; `step_m <= 0` raises.
  - `format_lap_time`: normal, over 1 minute, under 1 minute, NaN.
- Required chart tests (assert on the returned figure, no image rendering): trace counts and names;
  reversed y-axis for `position_chart`; teammate dash styling; strategy bars use the right `base`/`x`
  values and respect `driver_order`; telemetry chart has 3 rows and dashes driver B when colours match;
  empty input yields a figure with an annotation and no exception.
- App smoke tests in `tests/app/` using `streamlit.testing.v1.AppTest`: monkeypatch the functions in
  `services` (or the `f1companion.data` functions they call) with fakes that return fixture `RaceData`
  and telemetry. For each of the three pages assert there is no exception, and a few key elements render
  (title/header text, a dataframe on Recap). Also test: a `F1DataError` from `get_race` renders
  `st.error` and no exception. If AppTest cannot cleanly drive `st.navigation`, test each page by
  setting `st.session_state["race_key"]` and running the page script directly, and note this in
  `docs/decisions.md`.
- Keep all existing tests passing. Expect roughly 60+ new tests; quality over count.

## Docs to update

- `docs/architecture.md`: add the analysis, charts and app module tables and one paragraph on the
  URL-state design (`year`, `round`, `d1`, `d2`) and the two-tier caching now in place.
- `docs/decisions.md`, new dated entries (use today's date), each two to four sentences:
  1. `st.navigation` with an `app/pages/` folder instead of Streamlit's auto-discovered `pages/` (shared
     sidebar selector runs on every page).
  2. Key events derived from lap-level `TrackStatus` and results rather than timestamps (approximate, but
     depends only on the project schema).
  3. Teammates distinguished by dashed lines, since both share a team colour.
  4. Query-param behaviour finding from the navigation test above, and any AppTest limitation.
- `README.md`: only add or fix a "Run locally" section (`pip install -e ".[dev]"`,
  `streamlit run app/main.py`) and tick off the three features as implemented. Leave the rest.

## Definition of done

All must be true, and your final report must show the evidence (command output, not claims):

1. `.venv/bin/ruff check .` and `.venv/bin/ruff format --check .` pass.
2. `.venv/bin/pytest` passes (report the count).
3. `grep -rn "fastf1" app src/f1companion/analysis src/f1companion/charts` returns nothing, and
   `grep -rn "streamlit" src` returns nothing.
4. `.venv/bin/streamlit run app/main.py --server.headless true` starts without errors in the log and
   `/_stcore/health` returns `ok`. (You may not have network; the real-data check is the reviewer's job.
   Say clearly whether you could test with real data or not.)
5. Docs updated as listed. `data/` untracked/ignored; `git status` clean after the final commit.

## Final report format (to the reviewer)

1. Branch name and commit list (`git log --oneline feat/data-layer..HEAD`).
2. Command outputs for items 1-4 above.
3. Deviations from this spec, each with the reason. If none, say "none".
4. Open questions or risks, especially anything you could not verify (real-data behaviour, mobile layout,
   URL behaviour across page switches).

## Review checklist (what the reviewer will check)

- Layer boundaries by grep and by reading imports
- Every analysis function covered by a meaningful test, edge cases (`<NA>`, empty, single driver) included
- Behaviour on the real data: run the app on one recent race and one older race (2018), one race with a
  retirement and safety car, a pit-lane start, and a driver with no valid lap
- Friendly errors: bad URL params (`?year=abc&round=999`), a race with missing data, no traceback shown
- URL state round-trip: copy URL, open in a new tab, same race and drivers
- Mobile width (about 390px): no horizontal scroll, legends readable, tables usable
- Chart readability: teammates distinguishable, light-coloured tyres visible, P1 on top
- Docs match the code
