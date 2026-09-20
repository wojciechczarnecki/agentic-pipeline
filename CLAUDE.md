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
a stable release guards work on unstable code. `.claude/settings.json` pins the source to
the release tag, but the pin only takes effect once the marketplace is registered with that
`ref`; a marketplace registered earlier without one keeps tracking `main`. Once per machine
(the owner, outside an agent session):

```bash
claude plugin marketplace remove wcz-tools
claude plugin marketplace add 'https://github.com/wojciechczarnecki/agentic-pipeline.git#pipeline--v0.3.0'
claude plugin install pipeline@wcz-tools --scope project
git checkout -- .claude/settings.json   # all three commands strip it — see below
```

**The marketplace is only the source: `remove` uninstalls the plugin too, so it has to be
installed again, at `--scope project`** (both `add` and `install` default to `user`, which
is not how this repository is set up). Verify with `claude plugin list`, or read
`~/.claude/plugins/installed_plugins.json`, where a project-scope install is recorded
under this `projectPath` with its version and `gitCommitSha` — that file, not
`.claude/settings.json`, is what the CLI acts on.

**All three commands delete `enabledPlugins` and `extraKnownMarketplaces` from
`.claude/settings.json`** — this project's and `~/.claude/settings.json` alike — **and
none of them puts the block back.** Restore it with `git checkout`: a fresh clone on
another machine has no entry in `installed_plugins.json`, so that block is the only place
it can learn where the plugin comes from.

Both failures are silent. A session missing the plugin has no command guard and no
`pre-push` rule, and says nothing about it. A running session also keeps whatever it
loaded at startup, so every step above needs a restart to take effect. Measured
2026-09-20 during the 0.3.0 release.

Two checks afterwards, in a fresh session:

```bash
git -C ~/.claude/plugins/marketplaces/wcz-tools describe --tags --exact-match HEAD
```

must name the release tag (an error means the marketplace tracks `main`, so the pin is
inert), and a command the guard blocks — `sed -i` on `.claude/settings.json`, say — must
actually be refused, with the version in the path it reports. The second check is the only
one that proves the plugin is loaded here; the rest prove the source is right.

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
`reset --hard`, `clean -f`, `--no-verify`, pushing release tags.

Two layers enforce this, and they do not cover the same ground.

**GitHub rulesets — server-side, no bypass actors, they hold for everyone:**

- `main` (the default branch): a pull request is required, squash is the only merge method,
  the `plugin` check must be green, and deletion and non-fast-forward pushes are blocked.
- `release tags` (`refs/tags/pipeline--v*`): an existing tag cannot be deleted, moved or
  force-updated.

**Only the local layer — the plugin's command guard and the `deny` list in
`.claude/settings.json` — stops the rest:**

- creating and pushing a *new* release tag: the tag ruleset has no `creation` rule, and the
  `pre-push` hook matches branches only, so GitHub accepts `pipeline--vX.Y.Z` from anyone
  who can push. Tagging stays the owner's move by agreement, not by mechanism.
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
