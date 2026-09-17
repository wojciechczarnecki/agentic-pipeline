# CLAUDE.md

Instructions for agents working in this repository.

## Project

- **agentic-pipeline** — an agentic feature pipeline plugin for Claude Code: idea → plan →
  plan review → implementation → final review → pull request, with a command guard,
  formatting and notification hooks, workflow metrics and a project scaffold skill
- Owner: Wojciech Czarnecki
- Stack: Python 3.12 standard library only at runtime (hooks and `plugin/bin/`), Markdown
  skills and agents · dev tools through uv (ruff, black, pytest) · GitHub Actions (CI)

## Document map — what to read when

| Document | When |
|---|---|
| `docs/PROJECT.md` | purpose, requirements, architecture — at the start of work on a feature |
| `docs/ROADMAP.md` | stages and streams with their status — at the start of every task; **update when done** |
| `docs/BACKLOG.md` | deferred improvements and debt: priority P1–P3 + trigger |
| `docs/DECISIONS.md` | binding design decisions — before designing something differently; append new ones |
| `docs/CONVENTIONS.md` | code style, tests, git, releases — when writing code |
| `plugin/README.md` | the plugin's own documentation: configuration, pipeline mechanics, metrics |
| `specs/` | SPEC + PLAN per feature — see the workflow below |

## Agentic workflow

The workflow comes from the `pipeline` plugin **released** from this repository and
installed from GitHub (marketplace `wcz-tools`, git + HTTPS) — not from the working tree:
a stable release guards work on unstable code. The mechanics (statuses, the `RESULT`
contract, escalation triggers, metrics format) are described in `plugin/README.md` — the
single source of truth. Project configuration for the plugin lives in `.claude/workflow.json`.

```
/pipeline:idea (dialog)   → SPEC.md (spec-ready)   ← GATE 1: the owner approves the SPEC
/pipeline:ship NNN        → plan → plan review → implementation → review report
                                                   ← GATE 2: the owner decides on findings
                          → fixes, PR, green CI, done
merge PR                                           ← GATE 3: the owner
```

**Fast path** for small things (bugfix, docs, configuration — no new dependencies):
mini plan in the conversation → implementation → `bash scripts/check.sh` → `/code-review`
on the diff → owner decisions → PR. When in doubt → full pipeline.

### Approvals

- `plan-approved` = approval of every edit within the plan's scope.
- Outside the plan and on the fast path: present the intent and get approval before editing.
- ALWAYS ask before: deleting files outside the plan's scope; adding a dependency
  (including runtime dependencies of the plugin — it must keep running on plain `python3`).

### Git — agents on working branches, `main` belongs to the owner

The agent creates its branch, commits, pushes and opens the PR (`gh pr create`). It updates
the branch with `git merge origin/main` (not rebase). Out of the agent's reach: commit,
merge and push to `main` (only `git pull --ff-only`), merging PRs, force-push,
`reset --hard`, `clean -f`, `--no-verify`, pushing release tags. Enforced by the plugin's
command guard and the `pre-push` hook (enable once per clone:
`git config core.hooksPath scripts/git-hooks`).

## Iron rules

- Every change in behaviour MUST come with tests (pytest in `plugin/tests`).
- The plugin has no runtime dependencies: hooks and `plugin/bin/` use the standard library.
- The plugin stays independent of any project and domain: project specifics live in the
  consumer's `.claude/workflow.json` (`plugin/tests/test_no_domain_references.py`).
- A change in behaviour bumps the version in `plugin/.claude-plugin/plugin.json` and gets
  a `plugin/CHANGELOG.md` entry; the owner tags the release.
- When a task is done, tick it in `docs/ROADMAP.md` — the roadmap must not lie.
- Record architectural decisions in `docs/DECISIONS.md` in the same PR.
- Secrets never in code, logs, commits or tests.

## Commands

```bash
# Full verification (validate --strict when `claude` is on PATH, ruff, black, pytest)
bash scripts/check.sh

# Dev environment
uv sync
uv run pytest
uv run black . && uv run ruff check . --fix

# Plugin checks
claude plugin validate --strict plugin/
claude plugin validate --strict .
claude --plugin-dir ./plugin          # one-off session with the working-tree plugin

# Release (owner, clean clone on main)
claude plugin tag plugin --push
```

## Structure

```
.claude-plugin/marketplace.json  # marketplace `wcz-tools`, plugin from ./plugin
plugin/          # the plugin: skills, agents, hooks, bin, templates, evals, tests
docs/            # project documents (map above)
specs/           # SPEC/PLAN per feature (pipeline)
scripts/         # check.sh, git hooks
.claude/         # settings (plugin from GitHub) and workflow.json
```
