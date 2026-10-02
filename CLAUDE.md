
# F1 Race Companion

A free, public web app that helps Formula 1 fans understand a race: what happened, why, and who was fastest. It is also a portfolio project, so code quality, tests, and documentation matter as much as features.

> Unofficial project. Not associated with Formula 1 companies. Do not use F1 logos or trademarked assets.

## Goals

1. **Fans:** open a link, pick a race, understand it in under a minute. No setup, mobile friendly.
2. **Portfolio:** clean architecture, tests, CI, documented decisions, one original analysis.

## Stack

- Python 3.11+
- [FastF1](https://docs.fastf1.dev) for data (use the official docs; check the current API before writing code)
- pandas, numpy
- Streamlit for the UI, Plotly for charts
- pytest for tests, ruff for lint/format
- GitHub Actions for CI
- Deploy: Streamlit Community Cloud

## Project structure

```
f1-race-companion/
├── CLAUDE.md
├── README.md
├── pyproject.toml          # or requirements.txt + requirements-dev.txt
├── .github/workflows/ci.yml
├── app/
│   ├── main.py             # Streamlit entry point
│   ├── pages/              # one file per view
│   └── components/         # reusable chart/UI pieces
├── src/f1companion/
│   ├── data/               # loading + caching FastF1 sessions
│   ├── analysis/           # pure functions: DataFrame in, DataFrame out
│   └── charts/             # Plotly figure builders
├── scripts/
│   └── precompute.py       # pre-process popular races for fast loading
├── tests/
├── docs/
│   ├── architecture.md
│   └── decisions.md        # short log of tradeoffs and why
└── data/                   # gitignored cache
```

## Architecture rules

- **Three layers:** data -> analysis -> UI. The UI never calls FastF1 directly.
- Analysis functions are **pure** (no network, no Streamlit imports) so they are easy to test.
- Chart builders return Plotly figures; pages only arrange them.
- Keep functions small, typed (type hints), and documented with short docstrings.
- Never commit cached FastF1 data or API output. Use `.gitignore`.

## MVP features

1. **Race recap:** position changes by lap, final results, key events (safety cars, retirements).
2. **Strategy:** tire stints and pit stops per driver, shown as a timeline.
3. **Head-to-head:** compare two drivers' fastest laps (speed, throttle, brake traces by distance).
4. **Original analysis (the portfolio centerpiece):** tire degradation estimate per compound and a "race pace vs. finishing position" metric. Document the method and its limitations in `docs/`.

Also: a short plain-English "story of the race" summary generated from the data (rule-based, no external AI dependency).

## Performance and reliability

- FastF1 is slow on first load. Enable its cache and pre-compute popular races with `scripts/precompute.py`.
- Use `st.cache_data` for expensive computations.
- Handle missing or partial data gracefully (older seasons, incomplete telemetry). Show a friendly message, never a stack trace.
- Show a loading state for slow operations.

## Testing and CI

- Tests for every analysis function, using small fixture data (do not hit the network in tests).
- CI runs on every push and PR: `ruff check`, `ruff format --check`, `pytest`.
- Aim for meaningful coverage of `src/`, not a vanity number.

## Git workflow

- Small, focused commits with clear messages (e.g. `feat: add tire stint timeline`).
- Work on feature branches, merge via PR where practical.
- Never commit secrets or large data files.

## Documentation standards

- **README:** one-line pitch, live demo link, screenshots/GIF, features, how to run locally, architecture overview, tech stack, limitations, credits and disclaimer.
- `docs/decisions.md`: short entries like "Chose Streamlit over Dash because...".
- Explain the original analysis method in plain language with its assumptions.

## UX principles

- Explain F1 terms briefly for casual fans (tooltips or captions).
- Mobile friendly layouts, readable charts, consistent team/driver colors.
- Shareable state: race and drivers selected should be reflected in the URL where possible.

## Build phases

1. Repo setup, structure, linting, CI skeleton
2. Data layer + caching, with tests
3. Core views (recap, strategy, head-to-head)
4. Original analysis feature + race story summary
5. Deploy, README, screenshots, short write-up

## How to work with me

- Start by confirming the plan for the current phase, then implement.
- Before using any FastF1 function, check its current signature in the docs.
- Run tests and lint before declaring a task done.
- Prefer simple, readable solutions over clever ones.
- When a design tradeoff comes up, propose options and add the choice to `docs/decisions.md`.
- Keep scope tight. Do not add features outside the MVP without asking.