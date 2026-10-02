# Decisions

Short log of tradeoffs and why. Newest at the bottom.

## 2026-10-02: `pyproject.toml` over `requirements.txt`

One file holds metadata, dependencies, and tool config (ruff, pytest). Dev tools sit in a `dev` extra, installed with `pip install -e ".[dev]"`. If Streamlit Community Cloud needs a `requirements.txt` at deploy time, a minimal one will be added then.

## 2026-10-02: src layout

Code lives in `src/f1companion/`, so tests run against the installed package rather than whatever happens to be on the path. This catches packaging mistakes early.

## 2026-10-02: ruff for lint and format

One fast tool replaces black, isort, and flake8. Rule sets: `E`, `F`, `I`, `UP`, `B`, `SIM`.
