# Development conventions

Binding conventions for code and process. The iron rules are summarised in CLAUDE.md;
this document holds the details.

## Language

- Project documents (`docs/`, `specs/`, `CLAUDE.md`, root `README.md`) follow
  `language: "en"` in `.claude/workflow.json`; code, identifiers, comments and commit
  messages are English regardless of it.
- Plugin skills, agents and `plugin/README.md` are in Polish until translated
  (`docs/BACKLOG.md`); a translation is a behaviour change and ships as a release.
- No mixing of languages within one document.

## Code style

- Line length: 100.
- Formatting and lint: `uv run black` and `uv run ruff check --fix` (the same commands as
  `format[]` in `.claude/workflow.json`); ruff rules `E, F, I, B, N`, target Python 3.12.
- No docstrings; self-documenting code.
- Comments only where the code cannot express a constraint.
- Runtime code (`plugin/hooks`, `plugin/bin`) imports only the standard library.

## User-facing text

Messages printed by hooks and `bin/` scripts are English and name the rule that fired
and the way out (for the guard: which configuration or approval unlocks the action).

## Tests

- `plugin/tests` (pytest), run by `uv run pytest`; hooks and scripts are exercised as
  subprocesses on plain `python3` where their contract is the command line.
- Test mechanisms, not the prose of skills: structure, frontmatter, templates, the guard's
  verdicts, configuration handling.
- Write tests BEFORE or TOGETHER with the implementation.
- Cover key paths and edge cases; assertions check content where content matters.
- Full verification in one command: `bash scripts/check.sh`.
- `claude plugin eval` runs a real model and is manual only (`plugin-eval` workflow).

## Commits and branches

- Commit types: `feat` / `fix` / `test` / `docs` / `refactor` / `chore` / `ci`.
- Imperative mood (`add`, `fix`, `harden`).
- One branch per task: `feat/NNN-<slug>`, `fix/...`, `chore/...`, `docs/...`.
- PRs to `main` are **squash** merged; CI must be green before merge.
- The PR title becomes the commit message after the squash, so it follows the commit rules:
  a type prefix and imperative mood (`chore: add the project scaffold`).
- Agent commits: after every green step, only the files of that step.
- Updating a branch: `git merge origin/main`, not rebase.

## Releases

- Semantic versioning in `plugin/.claude-plugin/plugin.json`; the version grows with
  behaviour (skills, agents, hooks, guard, templates), not with docs or tests.
- Every release has a `plugin/CHANGELOG.md` section.
- The owner tags a clean `main` with `claude plugin tag plugin --push` (`pipeline--vX.Y.Z`).

## Parallel work

Each lane gets its own branch and working directory (git worktree) in `worktree.dir`.
The agent takes the first spec number free across the specs directory, branch names and
worktrees.

## Workflow metrics

Every spec carries a flat `metrics:` block in its SPEC.md frontmatter, filled in by the
pipeline stages. Keys and report: `plugin/README.md` → metrics section
(`workflow_metrics.py`, on `PATH` inside a Claude Code session with the plugin).

## Dependencies

- Dev tools only, pinned exactly in `pyproject.toml` (`[dependency-groups] dev`) with
  `uv.lock` committed; the plugin has no runtime dependencies.
- Dependabot: monthly grouped minor/patch updates for uv and GitHub Actions; major
  versions are upgraded deliberately as their own task.
