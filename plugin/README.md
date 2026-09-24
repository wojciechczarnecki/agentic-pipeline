# Plugin `pipeline`

An agentic feature pipeline for Claude Code: idea → plan → plan review → implementation →
final review → PR. On top of that: a command guard (`main`, production, migrations, file
deletion), formatting and notification hooks, a workflow metrics report and a skill that
scaffolds a new project.

The plugin is independent of any stack and any domain: everything that concerns a
particular repository lives in its `.claude/workflow.json`.

## Installation

```bash
claude plugin marketplace add 'https://github.com/wojciechczarnecki/agentic-pipeline.git#stable'
claude plugin install pipeline@wcz-tools --scope user
/pipeline:init   # once in each project, inside a Claude Code session
```

See the [install guide](docs/INSTALL.md) for updating, the release channel, the one-time
migration, verification, the opt-out and the known traps.
For a new repository, [starting a new project](docs/NEW-PROJECT.md) walks from an empty
directory to the first feature.

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
goes section by section: a faulty section falls back to the defaults with a warning (in
`models` only the faulty entry, which falls back to `inherit`), and
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
| `protectedBranches` | absent | extra branch names the guard treats exactly like `main`/`master` (which stay protected whatever the list says); exact names, no patterns; binds agent sessions only — the `pre-push` hook and `/pipeline:init` do not read or write it |
| `language` | `"en"` | the language of every file the pipeline writes into the repository and of PR descriptions — supported `en`, `pl`; any other value warns and falls back to `en` (see the language contract below) |
| `models` | absent | the model per stage agent started by `/pipeline:ship`: keys `plan`, `plan-review`, `implement`, `final-review`; values `inherit` (the session model), `sonnet`, `opus`, `haiku`, `fable`; a stage without an entry inherits; a bad entry warns and only that stage inherits. `/pipeline:init` writes `{"implement": "sonnet"}` — a guess not yet measured, until the Stage 7 comparison |
| `implement.chunked` | `false` | `true` runs the implementer in chunks, one fresh subagent per step group of PLAN.md (see "The chunked implementer" below); any other value warns and counts as off. A Stage 7 candidate, not yet measured: off until the comparison measures it no worse; `/pipeline:init` does not write it |

Full example: `templates/workflow.example.json`.

### Models and effort

`/pipeline:ship` passes a stage's `models` entry to the `Agent` tool as its `model`; for
`inherit` or no entry it passes none, and the stage runs on the session model. The value
`/pipeline:init` writes, the implementer on Sonnet, is a guess not yet measured: the
implementer takes the largest share of a spec's cost and carries out a detailed plan with
tests, and the self-correction loop, the converge pass and the final review catch its
mistakes. The Stage 7 comparison will measure it with the cost keys (see Workflow metrics).

An effort level cannot be configured. The `Agent` tool takes a model alias but no effort
level (measured on Claude Code 2.1.281), and a plugin agent's `effort` sits in its
frontmatter, which a consumer cannot override. Effort therefore stays a plugin default; in
this release the agents set none and inherit the session's.

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
owner-only GitHub changes, `gh api` writes (`POST`/`PUT`/`PATCH`) on the owner's ground
(repository and organisation settings, secrets, webhooks, collaborators, rulesets and the
like — CI re-runs, releases, deployments, issues and pulls stay open), `sudo`, removals
outside the repository and the scratch directory, shell edits of guardrail files — which
include the plugin's own directory wherever it is installed and the plugin install state
(`installed_plugins.json`, `known_marketplaces.json`) — and detaching the plugin
(`claude plugin disable`, `uninstall`, `marketplace remove` aimed at it). The
configuration adds production hosts and commands, the worktree directory, the migration
module and `protectedBranches` — release-channel branches guarded exactly like `main`. The migration module recognises
ONLY Alembic's verbs and the variables `ENVIRONMENT`, `DATABASE_URL`, `DB_HOST`; only
`migrations.command` and `migrations.localHosts` are configurable, so a project on another
migration tool is not protected — the guard's silence is not protection. Fail-open is
deliberate: a missing `.claude/workflow.json`, a validation error and a missing `python3`
end with a warning on stderr and exit code 0. Once per session, in a project with
`.claude/workflow.json`, the guard also checks that a settings file allows `Read` on the
plugin's own directory (see the section map below) and, when none does, prints a notice naming the exact rule to add — as `systemMessage` for the
owner and `additionalContext` for the model, never blocking the call.

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
| `plan-approved` | `implementer` | `implemented` (in chunk mode each chunk but the last returns `plan-approved`) |
| `implemented` | `reviewer` (`report`) | findings report → gate 2 |
| `implemented` + decisions | `reviewer` (`apply`) | PR with green CI → `done` |
| `done` | owner | PR merge (gate 3) |

`plan-approved` is approval of every edit within the plan's scope — that is why the plan
reviewer does not approve a plan with a dependency or a migration nobody accepted.

### The `RESULT` contract

Every stage agent launched by `/pipeline:ship` ends its reply with this block:

```
RESULT: DONE | ESCALATE
STATUS: <spec status after the stage>
METRICS: <key=value; …>
ESCALATION: <only with ESCALATE — problem; options (≤ 4); recommendation; why>
SUMMARY: <≤ 10 lines; for reviewer/report — findings table: id | severity | one sentence>
```

`STATUS` is the spec status after the stage; `METRICS` its `key=value` pairs; `ESCALATION`
appears only with `ESCALATE` — the problem, up to four options, a recommendation and why;
`SUMMARY` is at most ten lines, and for the reviewer in `report` mode a findings table
(id, severity, one sentence).

In chunk mode the implementer adds a line `CHUNK: <group>/<groups>` right after `STATUS`:
the group it carried out and the number of groups. `ship` reads `DONE` with
`STATUS: plan-approved` as the end of a chunk and starts the next implementer with the same
prompt; a chunk end that repeats the group of the previous chunk that returned `DONE`, or
has no `CHUNK:` line, counts as a missing RESULT (one re-run, then an escalation).

A stage agent cannot ask the owner: wherever a skill says to ask or to STOP, it ends with a
`RESULT: ESCALATE` block. The orchestrator turns that into a question for the owner and
records the decision in the owner decisions section of PLAN.md.

### Escalation triggers

- a new dependency, or a major version bump of an existing one,
- a data migration,
- a gap or a contradiction in the SPEC,
- a blocker from the plan review that the reviewer cannot fix in the plan itself,
- a deviation from the plan that changes scope, architecture or the data schema,
- an exhausted self-correction loop (the 4th iteration on the same error),
- a test finds a product defect whose fix goes beyond the plan's scope or the owner's
  decisions — instead of working around it by changing the test or the test data,
- a proving test from the owner or the plan that is green before the change it is meant to
  prove,
- a real gap left after the second converge pass,
- a conflict on `git merge origin/main`.

### Implementation and review

**Test-first evidence.** The AC → steps matrix of a PLAN has a fourth column, "Red before
the change". Before the change meant to make an AC's proving test pass, `implement` runs
that test and records the command and the failing assertion line there. Only a failed
assertion counts: an import, collection or syntax error is red for any reason, so a missing
symbol gets a stub first. The step that makes an AC's proving test pass is not ticked while
that AC has no red record, unless the row is marked `manual` or `n/a — <reason>` (for
example `n/a — kept behaviour`). A proving test that is green before the change is
rewritten when the step writes it and it does not exercise the AC; a test that does
exercise the AC and still passes shows a gap in the SPEC and is escalated, as is a test
that existed before or that the plan gives verbatim, which stays unchanged. `plan`
orders each step so the proving test is written and run before the product change, and
`plan-review` checks that order and the column.

**The converge pass.** After the last planned step and before the Definition of Done,
`implement` starts a fresh subagent with the SPEC path and a diff command that leaves out
the spec directory, without its own reasoning or the plan; an AC the plan leaves out is
left to this pass rather than escalated at the start. The subagent compares the code with
every AC and reports gaps as `missing`, `partial`, `contradicts` or `unrequested`.
`implement` checks each gap in the code, rejects false ones with a reason, and adds a step
for each real one, carried out test-first in the self-correction loop, with its row in the
AC → steps matrix; `unrequested` code that no plan step and no `## Deviations` entry covers
gets a removal step. There are at most two passes, and a gap left after the second is an
escalation; after the owner decides on it, the decided steps are carried out without a
third pass. Each pass is recorded in PLAN.md, and the added steps count in
`implement_steps`.

**The chunked implementer.** `plan` always divides `## Steps` into groups under
`### Group N — <name>` headings, and a small plan is one group, because every chunk pays
its cache writes again; `plan-review` checks the grouping. With `"implement": {"chunked":
true}` in `.claude/workflow.json` (off by default) and more than one group, `implement`
carries out only the group that holds the first unticked step. When that group's last step
is green, ticked and committed, it appends an entry to `## Chunk notes` (the group, the
decisions taken within the plan's latitude, the traps the next group will meet, and the
running `implement_iterations` total), commits, pushes and ends at `plan-approved`. The next
chunk starts in a fresh context from the committed state and reads the notes. The chunk
with the last group runs the converge pass and the Definition of Done as one context does,
and writes the metrics once: `implement_iterations` as the running total and the optional
`implement_chunks`. Run on its own, `/pipeline:implement` stops at the group boundary and
asks to be run again after `/clear`. `cost_implement_cents` adds up every chunk.

**The final-review report.** The review always runs all three perspectives, for a small
change as for a large one, and each perspective reports every finding with its severity.
When the findings are merged, the report keeps at most five `nit` findings, the ones with
the highest risk or maintenance cost; the rest are left out and counted in the sentence
`Left out: N nit findings`, which also goes into the RESULT SUMMARY. `final_review_nits`
counts the reported nits. The depth of the plan, its review and the report follows the
change, with no spec-size classes: a section that does not apply gets one line
`n/a — <reason>`, and small things keep the fast path.

### Language contract

`language` in `.claude/workflow.json` (`en` or `pl`) decides the language of what the
pipeline leaves in the repository; it does not decide the language the agent talks in.

- **Follows `language`:** every file the pipeline writes into the repository — SPEC, PLAN
  (every section, including the review log, deviations, the final review and
  owner-decision entries), the documents `/pipeline:init` generates — and PR descriptions.
  A missing key or a value other than `en`/`pl` means `en`.
- **Always English, regardless of `language` and the session:** commit messages,
  PR titles, branch names and spec slugs, the `RESULT` block keys, metric keys and
  severity tokens.
- **Follows the Claude Code session language, never `language`:** questions to the owner,
  escalations shown to the owner, stage summaries and handoffs in the terminal.

PLAN follows the current `language` even when its SPEC was written in another one; nothing
already written is translated.

### Section map

Stages name a section by its English literal and accept either when reading, so a spec
written before a language change, or before 0.5.0, still reads correctly. The literals of
every SPEC and PLAN section live in [templates/sections.md](templates/sections.md), and the
SPEC and PLAN templates (`templates/SPEC.<language>.md`, `templates/PLAN.<language>.md`)
carry exactly those literals. Everything is read at run time with `Read`: `idea` and `plan`
read the one template for the current `language`, and every stage reads the section map
before it looks for a section.

A stage subagent cannot answer a permission prompt, so a consumer needs an allow rule for
the plugin's directory in `permissions.allow`:
`Read(~/.claude/plugins/cache/<marketplace>/pipeline/**)` for the install, and for a
`--plugin-dir` clone the absolute form `Read(//<clone>/plugin/**)` (`//` is absolute, a
single `/` is relative to the settings file). A read that fails stops the stage: under
`/pipeline:ship` with `RESULT: ESCALATE` naming the file and the rule to add, and in an
interactive `idea` or `plan` with the same message to the owner. The command guard warns
once per session when no user, project or project-local settings file holds such a rule.

### Severity tokens

Finding severities are fixed English tokens, written as code in every language, like metric
keys:

| token | stage |
|---|---|
| `blocker` | plan-review, final-review |
| `major` | plan-review |
| `minor` | plan-review |
| `worth-fixing` | final-review |
| `nit` | final-review |

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
  implement_chunks: 3                  # groups carried out as separate chunks (chunk mode only)
  converge_gaps: 1                     # real gaps kept from the converge passes
  deviations_minor: 1                  # every other entry in `## Deviations`
  deviations_major: 0                  # deviations that change scope, architecture or schema
  escalations: 1                       # /pipeline:ship — questions to the owner
  final_review_blockers: 0             # /pipeline:final-review report
  final_review_worth_fixing: 3
  final_review_nits: 2
  findings_accepted: 3                 # /pipeline:final-review apply
  findings_rejected: 2
  finished_at: "2026-09-15T14:30"      # /pipeline:final-review apply (green CI on the PR)
  cost_plan_cents: 180                 # /pipeline:ship in Closing, `--record-cost`
  cost_plan_review_cents: 120
  cost_implement_cents: 950
  cost_final_review_cents: 610
```

Specs recorded before 0.8.0 carry one `deviations:` counter instead of the two split keys;
it still passes `--check`. The new keys (`converge_gaps`, the split deviations and the four
`cost_*` keys) are never required, because a cost can be missing (another machine, the
cloud, expired transcripts). `implement_chunks` is never required either: only a spec
implemented in chunk mode writes it.

A report over all specs — a table per spec, totals, the share of significant findings
caught before code, and escalations per spec. Where specs carry cost keys, three more lines
follow: the plan review's and the final review's cost per significant finding (each over the
specs with that stage's cost) and the cost per plan step (over the specs with all four
costs), in cents rounded half up; a line with no data is left out:

```bash
workflow_metrics.py [specs-directory]
```

Without an argument the directory comes from `docs.specsDir`; a faulty key in
`.claude/workflow.json` only warns and falls back to its default, as in the hooks. The
script is called by name: Claude Code appends an enabled plugin's `bin/` to the session's
`PATH`, in consumers too.
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
| `implemented` | the above + `implement_steps`, `implement_iterations`, and either `deviations` or both `deviations_minor` and `deviations_major` |
| `done` | `started_at`, `finished_at`, every counter from the block above except the optional ones (`converge_gaps`, `implement_chunks`, the `cost_*` keys), and either deviations form |

A consumer must have the rule `Bash(workflow_metrics.py *)` in `permissions.allow` — a stage
subagent cannot answer a permission prompt, so without it every `--check` stalls and
`final-review` in `apply` mode never sets `done`. `templates/settings.json` carries it for
new projects. A rule written with `${CLAUDE_PLUGIN_ROOT}` does not work: Claude Code does
not substitute permission rules.

### Recording cost (`--record-cost`)

```bash
workflow_metrics.py --record-cost <spec-directory> [--transcripts <dir>]
```

Prices what the spec's four stage subagents spent and writes `cost_plan_cents`,
`cost_plan_review_cents`, `cost_implement_cents` and `cost_final_review_cents` into its
`metrics:` block. `/pipeline:ship` runs it in Closing, after the final review's `apply`.

- **What counts.** A subagent whose type is `planner`, `plan-reviewer`, `implementer` or
  `reviewer`, whose prompt names the spec directory (`NNN-<slug>`) and which ran inside this
  repository — the main checkout, the spec's checkout or `worktree.dir` — plus every
  subagent it started (the final review's perspectives, the converge pass). Report and
  `apply` both count toward the final review, and a stage run again after an escalation
  counts toward that stage. The `/pipeline:ship` orchestrator and the `idea` dialogue run in
  the main session and are not counted.
- **Source.** Claude Code's local transcripts: `~/.claude/projects` (or
  `$CLAUDE_CONFIG_DIR/projects`), searched recursively so worktree lanes are found too;
  `--transcripts <dir>` reads another directory, such as an archive. Each API message is
  counted once, however many times it was logged or copied.
- **Unit.** Cents at the API list rates of 2026-09-24, from a table in the script. Its rates
  are never changed — a new model is only added at its launch rates — so a cent is a fixed
  unit and costs from different years compare. Only the stage total is rounded.
- **Output.** Stdout shows a table per stage: models, tokens by type (input, cache write
  5 min, cache write 1 h, cache read, output) and cents. A second run replaces the keys it
  writes; every other byte of SPEC.md stays as it was.
- **Output tokens are a lower bound.** Claude Code often logs a message's `output_tokens`
  from the start of the stream rather than its final count, so the output share of a cost
  is undercounted, by a share that differs by model and stage. When a stage's logged
  content (characters / 4) is at least twice its logged output and more than 1000 tokens
  above it, stderr says so; the estimate is never priced.
- **Warnings, never a stop.** No transcripts, a stage without transcripts, or a model missing
  from the rate table leaves that key unwritten — a value an earlier run wrote is kept —
  names the reason on stderr and exits `0`,
  because a missing cost must not stop the closing of a spec. Only a spec directory
  without a readable SPEC.md exits `1`. Cost needs local transcripts: a spec run in the
  cloud or on another machine has none here.

## CHANGELOG

Full version history: [CHANGELOG.md](CHANGELOG.md).
