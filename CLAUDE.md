# CLAUDE.md

Instructions for agents working in this repository.

## Project

- **Spec-Driven Workflow** (repository `agentic-pipeline`, plugin `pipeline`) — an agentic
  feature pipeline plugin for Claude Code: idea → plan → plan review → implementation →
  final review → pull request, with a command guard, formatting and notification hooks,
  workflow metrics and a project scaffold skill
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
installed from GitHub (marketplace `wcz-tools`) — not from the working tree: a stable
release guards work on unstable code. `.claude/settings.json` points it at the `stable`
release channel; the owner installs it once per machine at `--scope user` and handles
installs, updates and migrations outside agent sessions — `plugin/docs/INSTALL.md`.
A session without the plugin has no command guard and no `pre-push` rule, and says nothing
about it; a session keeps the plugin it loaded at startup.

The mechanics (statuses, the `RESULT` contract, escalation triggers, metrics format) are
described in `plugin/README.md` — the single source of truth. Project configuration for
the plugin lives in `.claude/workflow.json`.

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
`reset --hard`, `clean -f`, `--no-verify`, pushing release tags, and pushing to the
`stable` release channel.

Two layers enforce this, and they do not cover the same ground.

**GitHub rulesets — server-side; `main` and `release tags` have no bypass actors and hold
for everyone:**

- `main` (the default branch): a pull request is required, squash is the only merge method,
  the `plugin` check must be green, and deletion and non-fast-forward pushes are blocked.
- `release tags` (`refs/tags/pipeline--v*`): an existing tag cannot be deleted, moved or
  force-updated.
- `stable` (the release channel): updates, deletion and non-fast-forward pushes are
  blocked, with the repository Admin role as the only bypass actor — unlike the two
  rulesets above — because moving the channel is a direct push, not a pull request. The
  bypass is the owner's account, so it keeps everyone else off the channel but lets
  through an agent pushing with the owner's credentials — to any commit, not only a tag.

**Only the local layer — the plugin's command guard and the `deny` list in
`.claude/settings.json` — stops the rest:**

- creating and pushing a *new* release tag: the tag ruleset has no `creation` rule, and the
  `pre-push` hook matches branches only, so GitHub accepts `pipeline--vX.Y.Z` from anyone
  who can push. Tagging stays the owner's move by agreement, not by mechanism.
- moving `stable`: with a `--scope user` install the channel feeds every project on the
  machine, and the guard protects `main`/`master` only; `deny` rules on `git push` to
  `stable` keep an agent off it. Moving the channel is the owner's move, like tagging.
- merging a PR: `required_approving_review_count` is 0, so a squash merge is server-side
  allowed; only the guard and `deny` keep an agent off it.

The `pre-push` hook makes the branch rules fail fast, before the network round trip — enable
it once per clone: `git config core.hooksPath scripts/git-hooks`.

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

# Release — the owner only: tag a clean clone on main, move the channel, publish the Release
# Minor/major first: eval receipt, then the canary — one real session in a consumer project
bash scripts/eval.sh
claude --plugin-dir <clone>/plugin --debug-file /tmp/canary.log   # run from the consumer
grep -E 'overrides installed version|Found [0-9]+ plugins' /tmp/canary.log   # 1 plugin: this one
claude plugin tag plugin --push
git push origin 'pipeline--vX.Y.Z^{commit}:refs/heads/stable'   # tags are annotated
awk -v v=X.Y.Z '$0 == "## " v {f=1; next} /^## /{f=0} f' plugin/CHANGELOG.md | gh release create pipeline--vX.Y.Z --verify-tag --title 'pipeline X.Y.Z' --notes-file -
```

## Structure

```
.claude-plugin/marketplace.json  # marketplace `wcz-tools`, plugin from ./plugin
plugin/          # the plugin: skills, agents, hooks, bin, templates, evals, tests
docs/            # project documents (map above)
specs/           # SPEC/PLAN per feature (pipeline)
tests/           # repository rules and documents (pytest)
scripts/         # check.sh, git hooks
.claude/         # settings (plugin from GitHub) and workflow.json
```
