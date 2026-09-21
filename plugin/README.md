# Plugin `pipeline`

An agentic feature pipeline for Claude Code: idea → plan → plan review → implementation →
final review → PR. On top of that: a command guard (`main`, production, migrations, file
deletion), formatting and notification hooks, a workflow metrics report and a skill that
scaffolds a new project.

The plugin is independent of any stack and any domain: everything that concerns a
particular repository lives in its `.claude/workflow.json`.

## Installation

**From a local path** (preview, work on the plugin itself):

```bash
claude --plugin-dir ./plugin          # a one-off session with the plugin
claude plugin validate --strict ./plugin
```

**Through a marketplace — a local directory:**

```bash
claude plugin marketplace add /path/to/agentic-pipeline-clone
/plugin install pipeline@wcz-tools
```

**Through a marketplace — the GitHub repository** (public, HTTPS, no SSH key), release
channel `stable`:

```bash
claude plugin marketplace add 'https://github.com/wojciechczarnecki/agentic-pipeline.git#stable'
claude plugin install pipeline@wcz-tools --scope user
```

`stable` is a branch the owner moves to every new release tag (`pipeline--vX.Y.Z`).
Without a `ref` a consumer tracks `main`, that is unreleased code. A marketplace's `ref` is
global per machine (`~/.claude/plugins/known_marketplaces.json`), and `install` and
`update` take no version — hence a channel rather than a pin on a tag: a pin would force
`marketplace remove` and a reinstall in every project on each release.

**The `user` scope — one install per machine.** The plugin works in every directory,
without installing it separately in each repository and each clone. A `--scope project`
install is tied to a directory (an entry with `projectPath` in
`~/.claude/plugins/installed_plugins.json`; in another repository `claude plugin list`
shows the plugin as `enabled`, yet the `/pipeline:*` commands are missing) and
`claude plugin update --scope user` does not lift it — do not use it; the only install is
`user`.

In the project's `.claude/settings.json` (shaped like `templates/settings.json`) declare
only the source — that way a fresh clone on another machine learns where the plugin comes
from:

```json
{
  "extraKnownMarketplaces": {
    "wcz-tools": {
      "source": {
        "source": "git",
        "url": "https://github.com/wojciechczarnecki/agentic-pipeline.git",
        "ref": "stable"
      }
    }
  }
}
```

**A project does NOT declare `"enabledPlugins": {"pipeline@<name>": true}`.** A session
starting in a directory that enables the plugin this way creates a `--scope project`
install on its own — even beside an existing `user` install — and `claude plugin update
--scope user` lifts only the `user` entry, so the `project` duplicate stays on its old
version for good (measured 2026-09-21: `claude plugin list` shows the plugin twice; without
`enabledPlugins`, with `extraKnownMarketplaces` alone, no `project` entry appears and the
plugin loads from the `user` install as usual). Remove an existing duplicate like this:
first commit `.claude/settings.json` without `enabledPlugins` (otherwise `git checkout`
restores the declaration and the next session creates the duplicate again), then, in the
repository directory:

```bash
claude plugin uninstall pipeline@<name> --scope project
git checkout -- .claude/settings.json   # the command can strip the marketplace block
```

**Updating** to a new release, without registering again:

```bash
claude plugin marketplace update wcz-tools && claude plugin update pipeline@wcz-tools --scope user
```

Then start a new session — a running one keeps what it loaded at startup.

**One-time migration from a registration on a tag** (a marketplace added earlier as
`'<url>#pipeline--vX.Y.Z'` or without a `ref`). Check the marketplace entry in
`~/.claude/plugins/known_marketplaces.json`: its `source.ref` must read `"stable"`. If it
does not:

```bash
claude plugin marketplace remove <name>
claude plugin marketplace add '<url>#stable'
claude plugin install pipeline@<name> --scope user
git checkout -- .claude/settings.json   # in EVERY repository with the plugin
```

**`remove` uninstalls the plugin in ALL projects** — the marketplace is the install's
source. **All three commands (`remove`, `add`, `install`) delete
`extraKnownMarketplaces` from `.claude/settings.json`** (the project's and
`~/.claude/settings.json`) and none of them restores it — hence `git checkout` in every
repository that has the block (without `enabledPlugins`, see above). Both effects are
silent: a session without the plugin has no command guard and reports nothing. After the
migration start a new session.

**Verification** after an install, an update or a migration, in a new session: `claude
plugin list` shows the plugin at the released version in the `user` scope — and only
there, with no `project` entry — and a command the guard blocks — e.g. `sed -i` on
`.claude/settings.json` — is actually refused, with the version in the path it reports.
Only the second test proves that the plugin is loaded in this repository; the first proves
only that the install is correct.

**Switching it off in a repository that does not want the plugin.** With a `user` install
the plugin — the command guard included — works everywhere, also where commits go straight
to `main` and the guard would block them. Switch it off in that repository's
`.claude/settings.json`:

```json
{ "enabledPlugins": { "pipeline@wcz-tools": false } }
```

This is the only legitimate project use of `enabledPlugins` — with the value `false` only.

In every project run `/pipeline:init` once to create `.claude/workflow.json` and the rest
of the scaffold. A non-interactive session (`claude -p`) needs
`--permission-mode bypassPermissions`: Claude Code treats files in `.claude/` as sensitive
and asks before writing them regardless of permission rules. In a weaker mode init writes
everything outside `.claude/` and prints the content of the files it skipped.

## Commands and agents

| Command | Stage |
|---|---|
| `/pipeline:init` | project scaffold: configuration, permissions, documents, git hook, CI |
| `/pipeline:idea` | critical review of an idea → SPEC.md (the only stage in a dialogue) |
| `/pipeline:plan` | SPEC → PLAN.md with steps and verification commands |
| `/pipeline:plan-review` | adversarial plan review, fixes in place, approval |
| `/pipeline:implement` | the plan carried out step by step in a self-correction loop |
| `/pipeline:final-review` | final review from three perspectives, fixes, PR |
| `/pipeline:ship` | orchestrator: takes a feature from SPEC to an open PR |

Stage agents (launched by `/pipeline:ship`): `pipeline:planner`,
`pipeline:plan-reviewer`, `pipeline:implementer`, `pipeline:reviewer`.

## Project configuration — `.claude/workflow.json`

The one place where a project describes itself. The file may be missing: then the defaults
apply, and the guard prints a warning on stderr once per session and **never blocks** for
that reason. An unknown key or a wrong type ends in a readable validation error
(`python3 bin/workflow_config.py --check`), again without blocking the session. Validation
goes section by section: a faulty section falls back to the defaults with a warning, and
the others keep configuring the rules — a typo in one key does not disarm the whole guard.

| key | default | meaning |
|---|---|---|
| `production.hosts` | `[]` | fragments of hosts/URLs out of the agent's reach (case-insensitive match); an empty list = the rule is inactive |
| `production.commands` | `[]` | CLI programs that operate production — blocked with a referral to the owner |
| `worktree.dir` | `"../worktrees"` | the worktree directory, **as a path relative** to the repository root — removal inside it is allowed and `git worktree add` outside it is blocked; an absolute value, or one that contains the repository root, is rejected with a warning and replaced by the default |
| `verify.command` | `"bash scripts/verify.sh"` | full verification of the stack; the signal of the self-correction loop |
| `verify.scopes` | `[]` | extra scopes passed to that command (e.g. `backend`, `ui`) |
| `format` | `[]` | a list of `{ "match": <glob>, "command": <command> }` for the formatting hook |
| `docs.roadmap` | `"docs/ROADMAP.md"` | the roadmap document |
| `docs.backlog` | `"docs/BACKLOG.md"` | the backlog with priorities and triggers |
| `docs.decisions` | `"docs/DECISIONS.md"` | the decision register |
| `docs.conventions` | `"docs/CONVENTIONS.md"` | code and process conventions |
| `docs.project` | `"docs/PROJECT.md"` | vision and requirements |
| `docs.specsDir` | `"specs"` | the specs directory |
| `migrations` | no section | `{ "command": <program>, "localHosts": [...] }`; no section = the migration module is inactive |
| `gitHooksDir` | `"scripts/git-hooks"` | the git hooks directory (an existing hook is protected from shell edits; named in the enable instruction) |
| `language` | `"pl"` | the language of the documents the skills generate and write |

Full example: `templates/workflow.example.json`.

### Formatting (`format[]`)

The `PostToolUse` hook asks `bin/workflow_config.py --format-for <file>` for the command for
the file that was just changed. The glob in `match` is matched against the path **relative
to the project root** (`*` spans slashes too), the command runs **from the project root**,
and `{file}` is replaced with the relative path — always quoted for the shell, so a file
name with a space or a semicolon is an argument, not a second command; without that
placeholder the path goes at the end of the command.
No map, no match, no `python3` or a configuration error = no formatting and exit code 0 —
the hook never blocks an edit.

### Command guard

A `PreToolUse: Bash` hook (`bin/guard`, a wrapper around `bin/guard.py`) that refuses a
command with exit code 2 and a reason. The universal rules work WITHOUT configuration —
pushes, commits and merges on `main`, force and delete pushes, `--no-verify`,
`git reset --hard`, `git clean -f`, `core.hooksPath`, push configuration and defining git
aliases (an alias already in the configuration is not checked), `gh pr merge` and
owner-only GitHub changes, `sudo`, removals outside the repository and the scratch
directory, shell edits of guardrail files; the configuration adds production hosts and
commands, the worktree directory and the migration module. The migration module recognises
ONLY Alembic's verbs and the variables `ENVIRONMENT`, `DATABASE_URL`, `DB_HOST`; only
`migrations.command` and `migrations.localHosts` are configurable, so a project on another
migration tool is not protected — the guard's silence is not protection. Fail-open is
deliberate: a missing `.claude/workflow.json`, a validation error and a missing `python3`
end with a warning on stderr and exit code 0.

What the guard defends against, the three layers behind it (guard, `pre-push`, GitHub
rulesets), the commands it stops that a string `deny` rule lets through, and its known
limits: [docs/GUARD.md](docs/GUARD.md).

## Pipeline mechanics

### Spec statuses

The source of truth is `status:` in the `SPEC.md` frontmatter — that is why every stage can
be resumed after an interruption.

| Status | Who acts | Result |
|---|---|---|
| `spec-draft` | owner + `/pipeline:idea` | `spec-ready` (gate 1) |
| `spec-ready` | `planner` | `plan-draft` |
| `plan-draft` | `plan-reviewer` | `plan-approved` (by itself when nothing escalates) |
| `plan-approved` | `implementer` | `implemented` |
| `implemented` | `reviewer` (`report`) | findings report → gate 2 |
| `implemented` + decisions | `reviewer` (`apply`) | PR with green CI → `done` |
| `done` | owner | PR merge (gate 3) |

`plan-approved` is approval of every edit within the plan's scope — that is why the plan
reviewer does not approve a plan with a dependency or a migration nobody accepted.

### The `RESULT` contract

Every stage agent launched by `/pipeline:ship` ends its reply with this block (the skills
are still in Polish, so the block is quoted as the agents emit it):

```
RESULT: DONE | ESCALATE
STATUS: <status speca po etapie>
METRICS: <klucz=wartość; …>
ESCALATION: <tylko przy ESCALATE — problem; opcje (≤ 4); rekomendacja; dlaczego>
SUMMARY: <≤ 10 linii; dla reviewer/report — tabela znalezisk: id | waga | jedno zdanie>
```

`STATUS` is the spec status after the stage; `METRICS` its `key=value` pairs; `ESCALATION`
appears only with `ESCALATE` — the problem, up to four options, a recommendation and why;
`SUMMARY` is at most ten lines, and for the reviewer in `report` mode a findings table
(id, severity, one sentence).

A stage agent cannot ask the owner: wherever a skill says to ask or to STOP, it ends with a
`RESULT: ESCALATE` block. The orchestrator turns that into a question for the owner and
records the decision in PLAN.md → `## Decyzje właściciela`.

### Escalation triggers

- a new dependency, or a major version bump of an existing one,
- a data migration,
- a gap or a contradiction in the SPEC,
- a blocker from the plan review that the reviewer cannot fix in the plan itself,
- a deviation from the plan that changes scope, architecture or the data schema,
- an exhausted self-correction loop (the 4th iteration on the same error),
- a test finds a product defect whose fix goes beyond the plan's scope or the owner's
  decisions — instead of working around it by changing the test or the test data,
- a conflict on `git merge origin/main`.

## Workflow metrics

Every spec carries a flat `metrics:` block in its `SPEC.md` frontmatter; every stage writes
its own keys.

```yaml
metrics:
  started_at: "2026-09-15T09:00"      # /pipeline:ship or /pipeline:plan
  plan_steps: 8                        # /pipeline:plan
  plan_review_blockers: 1              # /pipeline:plan-review — counted before the fixes
  plan_review_majors: 2
  plan_changes: 5
  implement_steps: 8                   # /pipeline:implement
  implement_iterations: 3              # self-correction iterations beyond the first attempt
  deviations: 1
  escalations: 1                       # /pipeline:ship — questions to the owner
  final_review_blockers: 0             # /pipeline:final-review report
  final_review_worth_fixing: 3
  final_review_nits: 2
  findings_accepted: 3                 # /pipeline:final-review apply
  findings_rejected: 2
  finished_at: "2026-09-15T14:30"      # /pipeline:final-review apply (green CI on the PR)
```

A report over all specs — a table per spec, totals, the share of significant findings
caught before code, and escalations per spec:

```bash
workflow_metrics.py [specs-directory]
```

Without an argument the directory comes from `docs.specsDir`. The script is called by name:
Claude Code appends an enabled plugin's `bin/` to the session's `PATH`, in consumers too.
Not through `${CLAUDE_PLUGIN_ROOT}` — skill text gets that variable substituted, but
`permissions` rules do not, so a call by absolute path matches no `allow` rule (and the
Bash tool's shell does not have the variable at all).

### Checking metrics (`--check`)

```bash
workflow_metrics.py --check <spec-directory>
```

Checks ONE spec: every key due for the status reached, the timestamp format
(`%Y-%m-%dT%H:%M`), counters as non-negative integers, no keys outside the metrics list (a
typo would lose a value silently) and the balance
`findings_accepted + findings_rejected == final_review_blockers +
final_review_worth_fixing + final_review_nits` (computed only once all five are present).
Exit code: `0` and silence when everything holds; `1` with a description of EVERY problem on
stderr (never a traceback); `2` when the arguments are wrong. The closing step of every
stage runs `--check` before reporting success, and `final-review` in `apply` mode will not
set `done` on red. Red that a stage cannot fix from its own artifacts must not be papered
over with an invented value — it is an escalation to the owner.

Keys due by status:

| status | required keys |
|---|---|
| `spec-draft`, `spec-ready` | none |
| `plan-draft` | `started_at`, `escalations`, `plan_steps` |
| `plan-approved` | the above + `plan_review_blockers`, `plan_review_majors`, `plan_changes` |
| `implemented` | the above + `implement_steps`, `implement_iterations`, `deviations` |
| `done` | `started_at`, `finished_at` and every counter from the block above |

A consumer must have the rule `Bash(workflow_metrics.py *)` in `permissions.allow` — a stage
subagent cannot answer a permission prompt, so without it every `--check` stalls and
`final-review` in `apply` mode never sets `done`. `templates/settings.json` carries it for
new projects. A rule written with `${CLAUDE_PLUGIN_ROOT}` does not work: Claude Code does
not substitute permission rules.

## CHANGELOG

Full version history: [CHANGELOG.md](CHANGELOG.md).
