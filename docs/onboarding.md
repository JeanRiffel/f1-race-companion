# Onboarding

How to start contributing to F1 Race Companion, as a human engineer or an AI coding agent. The rules
themselves live in [`AGENTS.md`](../AGENTS.md). This page explains how to apply them.

## 1. What this repository is

A Streamlit app that explains one Formula 1 race at a time: a recap (positions, results, key events),
tire strategy, and a head-to-head telemetry comparison. Phase 4 will add an original race-pace
analysis and a rule-based "story of the race". Data comes from [FastF1](https://docs.fastf1.dev). It
is also a portfolio project, so tests, docs, and recorded decisions are part of every change.

## 2. Environment setup

Requires Python 3.11+ (CI uses 3.11) and git.

```bash
git clone https://github.com/JeanRiffel/f1-race-companion.git
cd f1-race-companion
python -m venv .venv
.venv/bin/pip install -e ".[dev]"

.venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/pytest
.venv/bin/streamlit run app/main.py
```

- The first race load downloads from FastF1 and is slow. Responses are cached under
  `data/fastf1_cache` (gitignored). Set `F1COMPANION_CACHE_DIR` to use another path.
- Warm the cache for a season with `.venv/bin/python scripts/precompute.py --year 2024`
  (`--help` lists the options).
- Tests run offline. `pytest -m network` runs one opt-in live schema check against real FastF1.

## 3. Architecture in one minute

```
FastF1 ──> src/f1companion/data/ ──> analysis/ ──> charts/ ──> app/ (Streamlit pages)
```

| Folder | What it does |
|---|---|
| `src/f1companion/data/` | Loads FastF1 sessions, manages the cache, and normalizes data into the schemas in `schema.py` |
| `src/f1companion/analysis/` | Pure DataFrame functions with no network or Streamlit, fully unit tested |
| `src/f1companion/charts/` | Plotly figure builders |
| `app/` | `main.py` shell (race selector, URL state), `services.py` cached wrappers, `pages/` views |
| `scripts/precompute.py` | Cache warming CLI |
| `tests/` | Mirrors the layers. Shared fakes and fixtures are in `tests/factories.py` and `conftest.py` |

Details: [`docs/architecture.md`](architecture.md).

## 4. Where to find context

| Question | Read |
|---|---|
| What are the rules? | `AGENTS.md` |
| How is the code organized, and what are the data contracts? | `docs/architecture.md`, `src/f1companion/data/schema.py` |
| Why was something done this way? | `docs/decisions.md` |
| What exactly should this feature do? | The spec in `docs/specs/` |
| What has changed recently? | `git log --oneline`, open PRs |
| What do users see? | `README.md`, the running app |

## 5. Picking up a task

1. Pick a task the human has assigned, or the next item in the build phases in `AGENTS.md`. Ask
   before starting anything outside the MVP.
2. If a spec exists, check that its status is `ready` and that you are its named implementer. If
   there is no spec and the change is more than a small fix, write one first (section 6).
3. Read the spec's "Read first" files, then the code you will touch and its tests.
4. Write down your plan (files, tests, how you will verify it). For large or ambiguous work, confirm
   it with the human before coding.

## 6. Writing and using specs

Specs live in `docs/specs/`. The template and conventions are in
[`docs/specs/README.md`](specs/README.md).

- **Writing one (human or planner agent):** state the problem and the acceptance criteria first.
  Then give precise contracts (signatures, columns, dtypes) for anything another layer depends on.
  Verify every external API against the installed version, and list open questions for the human.
- **Using one (implementer):** build exactly what it says. If it is wrong or impossible, stop and
  report instead of improvising. List any deviations in your completion report.
- **Reviewing against one (reviewer):** check each acceptance criterion, rerun the checks, and look
  for architecture rule violations. Report findings with file and line references.

## 7. Working with Claude Code

- Claude Code loads `CLAUDE.md`, which imports `AGENTS.md`. You do not need to paste the rules.
- Start in the repo root (or your worktree) and point it at the spec:
  "Implement `docs/specs/phase-4-race-pace.md`. Confirm the plan first."
- Use plan mode for multi-file tasks. Ask for checks to be run, and for the completion report
  defined in `AGENTS.md`.
- Claude Code does not commit, push, or open PRs unless you ask.

## 8. Working with Codex

- Codex reads `AGENTS.md` from the repo root automatically. `CLAUDE.md` is Claude-specific and can
  be ignored.
- Create the `.venv` before starting Codex. Its sandbox may block network access, and the checks
  need the installed dev dependencies (the tests themselves need no network).
- Give it the same kind of prompt: the spec path, the branch to use, and the request for the
  completion report.

## 9. Running agents concurrently

Use one git worktree and one branch per agent, so agents never share a working directory:

```bash
# implementer: new branch in its own directory
git worktree add ../f1rc-race-pace -b feat/race-pace main
cd ../f1rc-race-pace
python -m venv .venv && .venv/bin/pip install -e ".[dev]"

# reviewer: same commits, detached, in a separate directory
git worktree add --detach ../f1rc-review-race-pace feat/race-pace

# clean up after merge
git worktree remove ../f1rc-race-pace
```

- **Each worktree needs its own `.venv`.** The editable install points at one checkout's `src/`, so
  reusing another worktree's venv silently tests the wrong code.
- To share the FastF1 cache between worktrees, set `F1COMPANION_CACHE_DIR` to the same absolute
  path in each.
- Git does not allow one branch to be checked out in two worktrees, which is why the reviewer uses
  `--detach`. Refresh it with `git checkout --detach feat/race-pace` after new commits.

## 10. Testing and validation

The required checks are listed in `AGENTS.md`: lint, format, tests, and the layer-boundary greps.
Beyond that:

- Add tests next to the matching layer in `tests/`. Build inputs with `tests/factories.py` rather
  than real FastF1 data.
- For UI changes, run the app and check one recent race, one older race (2018), and a narrow mobile
  width (about 390px). Say in your report whether you used real data.
- CI (`.github/workflows/ci.yml`) runs `ruff check`, `ruff format --check`, and `pytest` on every
  push and PR.

## 11. Pull requests and review

1. The implementer commits in small conventional commits on the feature branch and writes the
   completion report.
2. When the human asks, push the branch and open a PR to `main`. Use the completion report as the PR
   description and link the spec.
3. A reviewer (a different agent or person) checks the branch against the spec and `AGENTS.md`,
   then posts findings in the PR.
4. The implementer fixes findings in new commits, and the reviewer rechecks.
5. CI must be green. The human reviews the result and merges. Agents never merge.
