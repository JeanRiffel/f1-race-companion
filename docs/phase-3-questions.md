# Phase 3 questions for Claude

No questions block implementing the specified phase 3 scope. The implementation
keeps the phase 2 data layer, CLI, and CI unchanged.

## 1. Align lap-time metrics and telemetry selection? (non-blocking)

`analysis.fastest_laps` follows the phase 3 rule: `IsAccurate` true, `Deleted`
false, and a non-missing lap time. The existing `load_fastest_lap_telemetry`
uses the source's `pick_fastest()`, which selects a recorded personal-best lap
without explicitly filtering `IsAccurate`. Its return value has no lap number.
Metrics and traces can therefore refer to different laps in partial timing data.

Should a follow-up phase 2 contract change load telemetry for the exact analysed
lap (and expose its lap number), or should phase 3 retain the existing selection?
Current choice: use the specified public loader, leave the data layer unchanged,
and state the possible mismatch in the comparison caption. No mismatch against
real race data was established during phase 3; this is a selection-rule difference.

## 2. Browser navigation and mobile acceptance (review check)

AppTest 1.64.0 switches to file pages without executing the shared main shell on
that transition in this environment. Page rendering, shell URL restoration,
selection persistence, and copying query values into a new session are covered
separately. The local server starts and its health endpoint returns `ok`.

Please verify a real browser round-trip across all three pages and a new tab,
including `year`, `round`, `d1`, and `d2`, and check chart/table usability at 390px.
No browser-control tool is available here, so those visual and full navigation
checks remain for review.
