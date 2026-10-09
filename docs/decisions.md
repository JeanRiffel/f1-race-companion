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
