---
status: plan-approved
stage_history:
  - "spec-draft — 2026-10-05"
  - "spec-ready — 2026-10-05"
  - "plan-draft — 2026-10-05"
  - "plan-approved — 2026-10-05"
metrics:
  started_at: 2026-10-05T15:33
  escalations: 0
  plan_steps: 12
  plan_review_blockers: 0
  plan_review_majors: 2
  plan_changes: 14
---

# SPEC 015 — Bootstrapping and the guard

## Goal

The first public consumer ran `/pipeline:init` on a project whose code lives in `backend/`,
and the owner then fixed the scaffold by hand: CI's working directory, the Dependabot
directory, the job name the ruleset requires, the permissions the stack needs, and a guard
gap through which the agent edited `.claude/workflow.json`. This spec makes `init` produce
a scaffold that is consistent for a project in a subdirectory and green on its first CI run,
gives the owner the repository settings as files to apply, and closes three guard gaps the
consumer met. Release: 0.10.0.

Success: `init` run non-interactively in a repository with only `backend/pyproject.toml`
writes CI, Dependabot, `verify.command`, `format[].command`, `CLAUDE.md` and
`docs/CONVENTIONS.md` that all point at `backend/`, with a CI job named `backend` that passes
on a project with no tests yet. The guard refuses interpreter code that names a guardrail
file, and every refused compound call tells the agent to split it.

## Context

Evidence: the consumer repository (`gaffers-presser`, read only), its scaffold commit
`27a37cb` and the files the owner corrected afterwards:

- `.github/workflows/ci.yml`: the job was renamed `backend`, with
  `defaults.run.working-directory: backend` and `working-directory: backend` on
  `astral-sh/setup-uv`. The template only says in a comment "add `defaults: …`".
- `.github/dependabot.yml`: `directory: /backend` for `uv`.
- `.claude/workflow.json`: `verify.command` is `cd backend && uv run …`, `format` uses
  `uv run --project backend …`; `migrations` was added by hand (`backend/alembic.ini`).
- `.claude/settings.json`: added by hand — `ask` on `Edit(**/.claude/workflow.json)`, `deny`
  on `claude plugin disable|uninstall|remove|marketplace remove`, `allow` for `uv`,
  `docker compose` and the project's own tools.
- `scripts/git-hooks/pre-push`: the comment still says `<gitHooksDir>`.
- `.gitignore`: written by the owner; `.ruff_cache/` was missing at first.
- The scaffold PR noted that CI "has nothing to test yet": `pytest` exits 5 with no tests.

The code this spec changes:

- `plugin/skills/init/SKILL.md`: survey (step 1), questions (step 2), generated files
  (step 4), closing (step 7), the write scope and the guardrails.
- `plugin/templates/github/workflows/ci-{python,node,placeholder}.yml`,
  `plugin/templates/github/dependabot.yml`, `plugin/templates/settings.json`,
  `plugin/templates/pre-push`, `plugin/templates/docs/*`; new repository-settings
  templates under `plugin/templates/github/`.
- `plugin/docs/NEW-PROJECT.md`.
- `plugin/bin/guard.py`: `Analyzer.run` (compound refusal), `strip_heredocs` (heredoc
  bodies are dropped as data today), the guardrail-file check, and the once-per-session
  notices in `main()` (`warn_once`, `read_rule_notice`).
- `plugin/docs/GUARD.md` (known limits: interpreters) and `plugin/README.md`.
- Eval cases `init-*` and `plugin/tests/test_init_*.py`, `test_guard*.py`.

## Read context

- `docs/ROADMAP.md`: searched for open items and stage headings; Stages 7, 9 and 10 read in
  full. Stage 10, item "0.10.0, one spec — bootstrapping and the guard", is the scope of this
  spec, bullet by bullet, minus what the owner cut (Owner decisions 6 and 7). The Stage 7
  write-up is a document, not part of this spec.
- `docs/PROJECT.md`: read in full. "`init` scaffolds a consumer project" and the command
  guard's guardrail files apply; the non-functional "runtime on plain `python3`" and
  "project and domain agnostic" bind the guard change and the templates.
- `docs/DECISIONS.md`: searched for "init", "heredoc", "interpreter", "ruleset",
  "subdirector", "alembic", "write scope", "ci-placeholder". The 2026-09-21 row lists
  interpreters as a known guard limit — this spec narrows it for guardrail paths and adds
  a row. The 2026-09-20 rows bind: the migration module stays Alembic only; the question
  cap of `init` has no eval. The 2026-09-22 row: `init` never writes `protectedBranches`.
- `docs/BACKLOG.md`: read in full. The P3 guard item "scripts, interpreters…" stays, with
  its context noting the narrowed case. "CI generator for other stacks" stays P3. No item
  is delivered in full by this spec.
- `docs/CONVENTIONS.md`: searched for "init", "canary", "eval receipt", "minor". A minor
  release needs the eval receipt and the canary before the tag; both are the owner's.
- `plugin/README.md`: searched for "init", "production", "hosts", "eval", "canary". The
  configuration table (`production.hosts`: empty list = rule inactive; `migrations`: no
  section = module inactive) is the ground for the two new warnings.

## Scope

- `init`: project layers detected at the root and one level down, filled consistently into
  CI, Dependabot, `verify`, `format`, `CLAUDE.md` and `docs/CONVENTIONS.md`.
- CI templates green on a new project: real steps when the layer is ready, a passing
  placeholder job otherwise; jobs named after layers; a note on renaming a required job.
- Repository settings as files copied by `init` into the project, applied by the owner with
  `gh api --input`, documented in `NEW-PROJECT.md` together with the first push and the
  "scaffold through a PR" path.
- `settings.json` template: `ask`, `deny` and stack `allow` rules.
- `production`: a warning in the closing when `hosts` stays empty.
- `<gitHooksDir>` substituted in the copied `pre-push`; `.gitignore` entries appended;
  README and licence as closing TODOs; an optional ADR template.
- Guard: interpreter code naming a guardrail file is refused; the once-per-session check
  warns about Alembic without a `migrations` section; every refused compound call suggests
  separate calls.
- One new eval case; version 0.10.0, CHANGELOG, DECISIONS, ROADMAP.

## Out of scope

- A minimal project skeleton (dev tools, lock file, smoke test) written by `init`: rejected
  for the placeholder job (Owner decision 1); `init` stays an installer.
- `init` writing `README.md` or a licence (Owner decision 6): closing TODOs only.
- A table of hosting providers with their domains and CLIs (Owner decision 7): only the
  empty-`hosts` warning.
- Monorepos deeper than one level (`apps/web`): not detected; the owner answers the stack
  question. No backlog item until a consumer needs it.
- `init` or an agent applying repository settings: the guard refuses those `gh api` writes
  by design (`docs/DECISIONS.md` 2026-09-22); the owner applies them.
- Interpreter code that reaches a guardrail file without naming it (a path built at run
  time, a script file): stays a known limit (`docs/BACKLOG.md` Guard P3).
- CI generators for stacks other than Python and Node (`docs/BACKLOG.md` Init P3).

## Requirements and acceptance criteria

Layers and subdirectories

- [ ] AC1: `init` detects layers from `pyproject.toml` and `package.json` at the repository
  root and in its direct subdirectories (depth 1, skipping hidden directories and
  `node_modules`). Each manifest is one layer. A layer at the root is named after its stack
  (`python`, `node`); a layer in a subdirectory is named after the directory (`backend`,
  `frontend`). The detected layers are shown for confirmation in the existing stack
  question; the question cap stays one round of at most four.
- [ ] AC2: For every layer in a subdirectory `<dir>`, the generated files say so
  consistently: the CI job has `defaults.run.working-directory: <dir>`, and its
  `astral-sh/setup-uv` step (Python) has `working-directory: <dir>`, or its
  `actions/setup-node` step (Node) has `cache-dependency-path: <dir>/package-lock.json`;
  the Dependabot entry for the layer's ecosystem has `directory: /<dir>`; `verify.command`
  runs the layer's checks in `<dir>`; every `format[]` entry for the layer matches
  `<dir>/…` files and runs its tool for the project in `<dir>` (`uv run --project <dir> …`
  for Python); the verification commands in `CLAUDE.md` and `docs/CONVENTIONS.md` are the
  same commands as `verify.command`. A root layer keeps today's form.
- [ ] AC3: The eval case `init-subdirectory-project` (non-interactive, a repository with
  only `backend/pyproject.toml` declaring `ruff` and `pytest` as dev dependencies and no
  test files) passes: the graders check AC2 for `backend` across all six places and AC4's
  placeholder job named `backend`.

CI green on a new project

- [ ] AC4: For each layer `init` writes the real job (install, lint, format check, tests)
  only when the layer declares its lint and test tools in its manifest and has at least one
  test file; otherwise it writes a placeholder job with the layer's name, one step that
  passes, and a comment listing the real steps to restore. A placeholder job is named on
  the closing list as a `TODO:` to replace once the layer has tests.
- [ ] AC5: Every CI template carries a comment that the job name is the required check in
  the repository ruleset, so renaming the job means renaming it in the ruleset file
  (AC7) and on GitHub.

Repository settings and `NEW-PROJECT.md`

- [ ] AC6: The plugin ships the repository settings as JSON templates for `gh api --input`:
  a branch ruleset for the default branch (pull request required, squash only, required
  status checks, no deletion, no non-fast-forward) and the repository settings (squash
  merges only with the PR title and body as the commit message, `delete_branch_on_merge`,
  `allow_update_branch`). A pytest checks that each file is valid JSON with these fields.
- [ ] AC7: `init` copies them into `.github/repository/` (inside its write scope), with the
  ruleset's required checks set to the names of the CI jobs it wrote. Re-running `init`
  does not overwrite an existing file there (AC follows the idempotence rule of step 6).
- [ ] AC8: `plugin/docs/NEW-PROJECT.md` describes: the first push to `main` before enabling
  the `pre-push` hook (and why); the alternative "scaffold through a PR" path (an empty
  initial commit on `main`, the scaffold on a branch, a PR); the exact `gh api` commands
  that apply the two files from AC7 and turn on Dependabot alerts, Dependabot security
  updates and private vulnerability reporting; and that GitHub offers a required check only
  after the workflow has run once.

`settings.json` template

- [ ] AC9: `plugin/templates/settings.json` has `ask` on `Edit(**/.claude/workflow.json)` and
  `deny` on `Bash(claude plugin disable*)`, `Bash(claude plugin uninstall*)`,
  `Bash(claude plugin remove*)` and `Bash(claude plugin marketplace remove*)`.
- [ ] AC10: `init` adds `allow` rules for the stack it sees in the repository, broad per
  tool: `Bash(uv *)` for a Python layer, `Bash(npm *)` for a Node layer, and
  `Bash(docker compose *)` only when a compose file (`compose.yaml`, `compose.yml`,
  `docker-compose.yml`, `docker-compose.yaml`) exists at the root or in a layer directory.
  No rule for a tool not seen in the repository (the existing guardrail).

Smaller `init` items

- [ ] AC11: When `production.hosts` stays empty, the closing list carries a warning that the
  production-host rule is inactive until hosts are added (`plugin/README.md`, configuration
  table). `init` offers no list of hosting providers.
- [ ] AC12: The copied `scripts/git-hooks/pre-push` (or the `gitHooksDir` path) has the
  literal `<gitHooksDir>` replaced by the configured directory; no `<gitHooksDir>` remains
  in any generated file.
- [ ] AC13: `init` may append to `.gitignore` (create it when missing) and to nothing else
  outside its write scope; the write scope in the skill says so. It appends only missing
  lines, never reorders or removes: always `.claude/settings.local.json`; for a Python layer
  `.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`; for a Node layer
  `node_modules/`. A second run adds nothing.
- [ ] AC14: `init` writes no `README.md` and no licence file. When the repository has no
  `README.md` or no licence file, the closing list names each as a `TODO:` for the owner.
- [ ] AC15: The plugin ships an ADR template per language (`templates/docs/adr/`); `init`
  does not copy it, and the closing list and `NEW-PROJECT.md` say how to copy it into
  `docs/adr/` when the project wants ADRs.

Guard

- [ ] AC16: The guard refuses a call that feeds code to an interpreter (`python`, `python3`,
  `node`, `perl`, `ruby`, also behind the wrappers the guard already unwraps) when that code
  names a guardrail file: `.claude/workflow.json`, `.claude/settings*.json`, the plugin's
  own directory or its install state — the paths the existing guardrail-file rule covers.
  "Code" is a heredoc body or here-string fed to the interpreter's stdin (`python3 - <<'EOF'`,
  `node <<EOF`) and the argument of `-c` (Python) or `-e`/`-E` (Perl, Ruby, Node). The
  refusal says that guardrail files change only through Edit/Write with the owner's
  approval. A mention counts whether the code reads or writes the file.
- [ ] AC17: Interpreter code that names no guardrail file passes as before, and so does a
  heredoc fed to a non-interpreter (`cat <<EOF > notes.md` naming `.claude/workflow.json`
  in its text is judged by today's rules only). `plugin/docs/GUARD.md` describes the new
  rule and narrows the interpreter known limit to code that does not name the path.
- [ ] AC18: In a project with `.claude/workflow.json`, the guard's once-per-session check
  prints a notice (shown to the owner and the model, as the `Read`-rule notice is) when an
  `alembic.ini` exists at the repository root or in a direct subdirectory and the
  configuration has no `migrations` section. The notice names the file and the section to
  add. It never blocks, and it is printed at most once per session.
- [ ] AC19: Every refusal of a call with two or more commands ends with a suggestion to
  send the commands as separate calls — also when every part was refused. A test covers
  `uv lock && uv sync` chained with a refused part, and a call where all parts are refused.

Release

- [ ] AC20: `plugin/.claude-plugin/plugin.json` is `0.10.0`; `plugin/CHANGELOG.md` has a
  `## 0.10.0` section. `docs/DECISIONS.md` gains rows for: the placeholder CI job over a
  skeleton; repository settings as project files applied by the owner; `.gitignore`
  joining the `init` write scope; and the interpreter rule narrowing the known limit.
  `docs/ROADMAP.md` ticks the item; `docs/BACKLOG.md`'s Guard P3 item on interpreters notes
  the narrowed case.
- [ ] AC21: `bash scripts/check.sh` is green, including `claude plugin validate --strict`
  for the plugin and the marketplace, and `plugin/tests/test_no_domain_references.py`.

Manual (owner)

- [ ] AC22: Before the tag, the owner runs the canary: `/pipeline:init` on the working-tree
  plugin in a fresh repository with only `backend/pyproject.toml`, then the first push.
  Pass when: `gh run list --limit 1` shows the CI run green with a job named `backend`;
  `grep -rn 'backend' .github/dependabot.yml .claude/workflow.json` shows the directory in
  Dependabot, `verify` and `format`; and `gh api --input .github/repository/ruleset.json …`
  (the command from `NEW-PROJECT.md`) creates a ruleset whose required check is `backend`.

## Decisions and rejected alternatives

| Decision | Rejected alternatives | Rationale |
|----------|-----------------------|-----------|
| A passing placeholder job when a layer has no tests or tools yet | A minimal skeleton (dev tools, lock file, smoke test); both behind a question | `init` stays an installer: no source files, no package-manager calls, no network. The job name is right from day one, so the ruleset need not change when the real steps arrive |
| Layers detected at the root and depth 1 | Only from the owner's answer; any depth | Covers `backend/` and `frontend/`, the shape seen, with no walk into `node_modules` or fixtures |
| Repository settings copied into `.github/repository/` with the CI job names filled in | Kept only in the plugin; applied by `init` | The ruleset must name the jobs `init` just wrote; the guard refuses ruleset writes by agents, so the owner applies them |
| `.gitignore` joins the write scope, append-only | Unchanged scope with a closing reminder | The missing `.ruff_cache/` was a real first-commit miss; append-only keeps the owner's file intact |
| Broad `allow` per seen tool (`uv *`, `npm *`, `docker compose *`) | Granular rules per subcommand | The owner's choice: fewer prompts; the guard still stands behind the shell |
| Interpreter code is refused on any mention of a guardrail path | Heredocs only; a write heuristic | A read and a write cannot be told apart from text; reads have `Read` and `cat`. A heuristic is easier to get around |
| The compound suggestion is added to every compound refusal | Leave it as it is (only when some parts passed) | The consumer's chained `uv lock`/`uv sync` was refused whole; the agent should be told to split even when nothing passed |

## Owner decisions

Decided in the `idea` dialogue (2026-10-05):

1. CI on a new project: a passing placeholder job named after the layer, not a skeleton
   (AC4).
2. `init`'s write scope gains `.gitignore`, append-only (AC13).
3. Repository settings are templates `init` copies into `.github/repository/` with the job
   names filled in; the owner applies them with `gh api --input` (AC6–AC8).
4. The guard refuses interpreter code on any mention of a guardrail file (AC16).
5. Layers are detected at the root and one level down; root layers keep the stack name,
   subdirectory layers take the directory name (AC1).
6. README and licence: never written by `init`, always closing TODOs, no question (AC14).
   This cuts "an optional README and licence question" from the roadmap item.
7. No list of hosting providers: only the warning on an empty `hosts` (AC11). This cuts
   "the known domains and CLI offered" from the roadmap item.
8. One new eval case, `init-subdirectory-project` (AC3).
9. The compound suggestion is completed for calls where every part is refused, with a
   regression test (AC19).
10. `allow` rules are broad per tool: `uv *`, `npm *`, `docker compose *` (AC10).
11. New dependency: none. Data migration: none.
12. Accepted at the SPEC review: the placeholder criterion (AC4), the `.gitignore` entries
    (AC13), the ADR template left uncopied (AC15), the interpreter list and what counts as
    code (AC16), and the `alembic.ini` locations (AC18).

## Open questions (non-blocking)

- none
