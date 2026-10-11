# Feature specifications

Non-trivial work starts from a spec in this folder. A spec is the hand-off between the human, the
planner, the implementer, and the reviewer (see "Multi-agent collaboration" in `AGENTS.md`). It must
be complete enough that an agent with no chat history can build and review the feature from the repo
alone.

Skip the spec for small fixes, typo-level docs changes, or one-file refactors. A clear issue or
task description is enough.

## Conventions

- **File name:** `phase-<n>[.<m>]-<slug>.md`, for example `phase-4-race-pace.md`. A follow-up fix to a
  phase gets a point number (`phase-2.1-cache-fix.md`).
- **Status:** `draft` (being written) -> `ready` (human approved, can be implemented) ->
  `in progress` -> `in review` -> `done`. Only the human sets `ready` and `done`.
- **Roles:** name the implementer and the reviewer (an agent such as Claude Code or Codex, or a
  person). They must be different agents or sessions.
- **Precise where it matters:** give function signatures, column names, and dtypes for public
  contracts. Leave internal details to the implementer.
- **Verify before marking ready:** check every external API the spec names (FastF1, Streamlit,
  Plotly) against the installed version, and record the versions.
- **Keep it after merge:** specs are a history of intent. Fix factual errors, but put later changes
  in a new spec.

`phase-2-data-layer.md`, `phase-2.1-cache-fix.md`, and `phase-3-core-views.md` predate this template
and are good worked examples.

## Template

Copy this into a new file and delete any guidance text in brackets.

```markdown
# Phase <n> spec: <feature name>

Status: draft
Author: <human>
Implementer: <agent or person>
Reviewer: <a different agent or person>
Branch: feat/<slug> from <base branch>
Read first: AGENTS.md, docs/architecture.md, <other relevant files>

## Problem statement

[What a fan (or developer) cannot do today, and why it matters. Two to five sentences.]

## Goals

- [Outcome the change must achieve]

## Non-goals

- [Related work that is explicitly out of scope; "ask first if you think it is needed"]

## Functional requirements

[What to build, layer by layer (data, analysis, charts, app). For public functions, give the
signature, inputs, output columns and dtypes, ordering, and edge cases (`<NA>`, empty,
single driver).]

## Acceptance criteria

[Numbered and checkable. Each one should be verifiable by a command, a test, or a specific manual
check.]

1. ...

## Technical constraints

- Architecture rules in AGENTS.md apply unchanged.
- [Verified library versions and signatures, files that must not change, performance limits]

## Testing expectations

- [Tests to add, fixtures to use, cases to cover; manual checks the reviewer will do]
- `ruff check .`, `ruff format --check .`, and `pytest` pass.

## Open questions

- [Decisions the human must make before or during implementation. Resolve all of them before
  marking the spec ready, or say which ones the implementer may decide.]
```

The implementer ends with the completion report defined in `AGENTS.md`. The reviewer checks the
branch against the acceptance criteria above, not against their own preferences.
