# Phase 3 implementation review

Branch: `feat/core-views`. Base: merged `main` at `b6065fb`.

Implemented Recap, Strategy, and Head-to-head with pure analysis, Plotly figures,
Streamlit cached services, a shared race selector, URL state, explanations, and
friendly data errors. Added 93 offline tests. No data-layer, CLI, or CI changes.

## Commits

Implementation commits (`git log --oneline main..HEAD` before the documentation commit):

```text
5f539aa feat: implement race navigation and three core views
a4ab4cc feat: add responsive core race charts
fc93bc1 feat: add core race analysis with offline tests
```

The requested `git log --oneline feat/data-layer..HEAD` also includes `b6065fb`,
the merge already present on the user-selected `main` base. A final documentation
commit contains this report, the questions file, README, architecture, and decisions.

## Verification output

```text
$ .venv/bin/ruff check .
All checks passed!

$ .venv/bin/ruff format --check .
36 files already formatted

$ .venv/bin/pytest
collected 162 items / 1 deselected / 161 selected
=============== 161 passed, 1 deselected, 352 warnings in 31.35s ===============
```

The deselected test is the existing opt-in live-data check. Warnings are the
existing NumPy timedelta deprecations from phase 2 fixtures. All app, analysis,
and figure checks used project-schema fixtures with the existing network guard.

```text
$ grep -rn 'fastf1' app src/f1companion/analysis src/f1companion/charts
(no output; exit 1)

$ grep -rn --include='*.py' 'streamlit' src
(no output; exit 1)

$ git diff --name-only main -- src/f1companion/data scripts/precompute.py .github/workflows/ci.yml
(no output)

$ git ls-files data
(no output)
```

The spec's unfiltered `grep -rn 'streamlit' src` matches only generated, gitignored
`src/f1companion.egg-info/PKG-INFO` and `requires.txt` dependency metadata. There is
no matching Python source and no presentation import under `src/`.

The initial server launch was blocked by the sandbox's socket restriction. The
approved rerun found port 8501 already occupied, so this app was verified on 8513:

```text
$ .venv/bin/streamlit run app/main.py --server.headless true --server.address 127.0.0.1 --server.port 8513
2026-10-09 20:41:12.470 Uvicorn server started on 127.0.0.1:8513

  You can now view your Streamlit app in your browser.

  URL: http://127.0.0.1:8513

$ curl --fail --silent http://127.0.0.1:8513/_stcore/health
ok
```

No startup errors on the successful launch. The verification server was stopped
once its health check was complete.

## Deviations and implementation choices

- Branch from `main`, which already contains phase 2, following the user's latest
  branch selection. The older spec names `feat/data-layer` as the current branch.
- Added `pit_stop_summary` to keep DataFrame grouping out of the Strategy page.
- AppTest's file-page transitions skip the shell in this environment. Test pages
  directly through its registered-page switch, and separately test shell URL
  restoration, repeated query parameters, selection changes, and new sessions.
- Use port 8513 for health verification because 8501 was occupied. Limit the
  Streamlit boundary grep to Python source because generated metadata names the
  dependency.
- Installed Python is 3.14.4 rather than the spec's 3.11; no dependency versions
  or CI configuration were changed.

## Questions and verification limits

See [phase-3-questions.md](phase-3-questions.md). No blocking questions remain for
implementing the specified scope. The existing telemetry selector can choose a
different lap from the accuracy-filtered metric; the page explains this and the
questions file asks whether a future data API should align the selections.

Phase 3 was not exercised with real race data. The phase 2 live schema test passed
earlier in this session, but that does not verify the new pages with live inputs.
A reviewer should check a recent race and a 2018 race, safety cars, retirements,
pit-lane starts, missing valid laps, full browser navigation and URL copying, and
mobile layout at about 390px. AppTest verifies behaviour and figure structure,
not pixel layout or a browser's actual navigation lifecycle.

No push, merge, or PR was performed.
