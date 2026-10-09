# F1 Race Companion

Understand any Formula 1 race in under a minute: what happened, why, and who was fastest.

**Live demo:** _coming soon_

<!-- TODO: screenshots / GIF -->

## Features

MVP progress:

- [x] **Race recap:** position changes by lap, final results, safety cars and retirements
- [x] **Strategy:** tire stints and pit stops per driver as a timeline
- [x] **Head-to-head:** compare two drivers' fastest laps (speed, throttle, brake by distance)
- [ ] **Race pace analysis:** tire degradation per compound and race pace vs. finishing position
- [ ] **Story of the race:** a short plain-English summary generated from the data

## Run locally

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
streamlit run app/main.py
```

Optionally warm the disk cache for a season:

```bash
python scripts/precompute.py --year 2024
```

Checks:

```bash
ruff check .
ruff format --check .
pytest
```

## Architecture

Data → analysis → charts → UI. The UI never calls FastF1 directly, and analysis functions are pure so they are easy to test. See [docs/architecture.md](docs/architecture.md) and [docs/decisions.md](docs/decisions.md).

## Tech stack

Python, [FastF1](https://docs.fastf1.dev), pandas, numpy, Streamlit, Plotly, pytest, ruff, GitHub Actions.

## Limitations

_To be documented as features land._

## Credits and disclaimer

Data via [FastF1](https://github.com/theOehrly/Fast-F1).

Unofficial project. Not associated in any way with the Formula 1 companies. F1, FORMULA ONE and related marks are trademarks of Formula One Licensing B.V.
