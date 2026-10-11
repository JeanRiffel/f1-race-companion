# CLAUDE.md

Follow `AGENTS.md`, the shared contract for all agents in this repository. It is imported below so
Claude Code always loads it. This file only adds Claude Code-specific guidance. If anything here
seems to conflict with `AGENTS.md`, `AGENTS.md` wins. Report the conflict.

@AGENTS.md

## Working with me in Claude Code

- Start each task by reading the spec (if any) and confirming the plan for the current phase. Use
  plan mode for multi-file or ambiguous work, then implement.
- Use the project venv for every check: `.venv/bin/ruff check .`, `.venv/bin/ruff format --check .`,
  `.venv/bin/pytest`. Run them before declaring a task done.
- Commit only when asked. Never push, merge, or open a PR unless the human asks in this session.
- Do not use subagents unless the human asks. When asked to review, review the branch against its
  spec's acceptance criteria and the `AGENTS.md` rules, and report findings with
  `path:line` references.
- When working concurrently with another agent, use a separate git worktree on its own branch
  (`docs/onboarding.md` has the commands). Do not touch the other agent's checkout.
- Keep project rules in `AGENTS.md`, not in Claude memory, so every agent sees them.
