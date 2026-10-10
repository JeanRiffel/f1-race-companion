# Decisions

Short log of tradeoffs and why. Newest at the bottom.

## 2026-10-02: `pyproject.toml` over `requirements.txt`

One file holds metadata, dependencies, and tool config (ruff, pytest). Dev tools sit in a `dev` extra, installed with `pip install -e ".[dev]"`. If Streamlit Community Cloud needs a `requirements.txt` at deploy time, a minimal one will be added then.

## 2026-10-02: src layout

Code lives in `src/f1companion/`, so tests run against the installed package rather than whatever happens to be on the path. This catches packaging mistakes early.

## 2026-10-02: ruff for lint and format

One fast tool replaces black, isort, and flake8. Rule sets: `E`, `F`, `I`, `UP`, `B`, `SIM`.

## 2026-10-09: Own schema over FastF1 objects

Normalize to plain DataFrames so analysis can be tested without FastF1 and remains
insulated from its column changes. Ordered columns and nullable dtypes live in
`data/schema.py`; missing required lap or result columns raise a friendly error.

## 2026-10-09: Race session only for the MVP

Sprint, qualifying, and practice are deferred to keep the data layer scope tight.
Races use `(year, round_number)` rather than names for unambiguous selection.

## 2026-10-09: Two cache tiers

FastF1's disk cache belongs in the data layer. Streamlit's `st.cache_data` wrappers
will belong in `app/` in phase 3, keeping the data layer usable from scripts and
free of Streamlit dependencies.

## 2026-10-09: Telemetry loaded separately

Race loading skips telemetry because it dominates load time. Head-to-head views
will fetch fastest-lap car samples only when needed.

## 2026-10-09: Loaders respect explicit cache settings

Loaders call `ensure_cache()` instead of `enable_cache()`, so a caller's custom cache directory or offline
mode is never reset to the default. This replaced an environment-variable workaround in
`scripts/precompute.py`.

## 2026-10-09: Explicit navigation with a shared shell

Use `st.navigation` with three explicit `st.Page` entries in `app/pages/` rather
than automatic discovery. Race selectors live in the entrypoint so the same sidebar
runs on every page in the real app. Driver widgets stay in the comparison page.

## 2026-10-09: Approximate events from project-schema laps

Neutralisations come from lap-level `TrackStatus`, and retirements come from the
classification. This keeps analysis independent of upstream timestamp formats, but
a condition beginning mid-lap marks the whole lap; the recap explains this limit.

## 2026-10-09: Dashed teammate traces

Drivers keep their supplied team colour. The second driver sharing a colour uses
a dashed line so position and telemetry comparisons remain distinguishable.

## 2026-10-09: Durable selection and navigation testing

[Streamlit documents that query parameters can clear when changing pages](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.query_params).
Keep race and driver choices separately from widget state, and rewrite their URL
parameters on every shell run. AppTest 1.64.0 can render registered file pages, but
its fresh PagesManager selects the child script directly on a switch, omitting the
entrypoint; tests therefore cover child pages and shell restoration separately,
and full browser navigation remains a reviewer check.

## 2026-10-09: Pure pit-stop summary helper

The strategy view needs stop counts and lap lists for every classified driver,
including zero-stop drivers. Add `pit_stop_summary` to the analysis layer so pages
only arrange results instead of grouping DataFrames themselves.

## 2026-10-09: Preserve the phase 2 telemetry contract

Phase 3 metrics filter accurate, undeleted laps, while the existing telemetry
loader selects the source's recorded personal best without an explicit accuracy
filter. Keep the data layer unchanged as required by the spec and explain the
possible difference in the comparison caption. Matching the telemetry lap to the
metric is a known limitation. FastF1's personal-best flags already exclude deleted
laps, and no mismatch appeared on 2018 to 2024 races checked by hand. If one shows up,
the follow-up is a data-layer change that returns the lap number and loads telemetry
for the exact analysed lap, in its own PR with tests.
