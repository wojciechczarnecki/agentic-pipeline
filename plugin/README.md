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
| `/pipeline:init` | project scaffold: configuration, permissions, documents, git hook, CI per layer (also for a project in a subdirectory), repository settings files |
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
| `implement.chunked` | retired | retired in 0.9.0: a boolean is still accepted and ignored, and `workflow_config.py --check` says on stderr that the `implement` section can be removed; any other key in `implement`, or a non-boolean value, is still a validation error. `/pipeline:init` does not write it |

Full example: `templates/workflow.example.json`.

### Models and effort

`/pipeline:ship` passes a stage's `models` entry to the `Agent` tool as its `model`; for
`inherit` or no entry it passes none, and the stage runs on the session model. The value
`/pipeline:init` writes, the implementer on Sonnet, is a guess not yet measured: the
implementer takes the largest share of a spec's cost and carries out a detailed plan with
tests, and the self-correction loop and the final review catch its mistakes. The Stage 7 comparison will measure it with the cost keys (see Workflow metrics).

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
(`claude plugin disable`, `uninstall`, `marketplace remove` aimed at it). Interpreter code
(`python3`, `node`, `perl`, `ruby`: a heredoc, a here-string, `-c`, `-e`) that names a
guardrail file is refused too, and a refused compound call always suggests sending its
commands as separate calls. The
configuration adds production hosts and commands, the worktree directory, the migration
module and `protectedBranches` — release-channel branches guarded exactly like `main`. The migration module recognises
ONLY Alembic's verbs and the variables `ENVIRONMENT`, `DATABASE_URL`, `DB_HOST`; only
`migrations.command` and `migrations.localHosts` are configurable, so a project on another
migration tool is not protected — the guard's silence is not protection. Fail-open is
deliberate: a missing `.claude/workflow.json`, a validation error and a missing `python3`
end with a warning on stderr and exit code 0. Once per session, in a project with
`.claude/workflow.json`, the guard also checks that a settings file allows `Read` on the
plugin's own directory (see the section map below) and, when none does, prints a notice naming the exact rule to add — as `systemMessage` for the
owner and `additionalContext` for the model, never blocking the call. The same once-per-session check notices an `alembic.ini` at the
repository root or one level down when the configuration has no `migrations` section, and
names the section to add.

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
| `implemented` + decisions | `reviewer` (`apply`) | PR with green CI (the status stays `implemented`) |
| `implemented` + PR with green CI | `workflow_metrics.py --close`, run by `ship` | `done` |
| `done` | owner | PR merge (gate 3) |

`plan-approved` is approval of every edit within the plan's scope — that is why the plan
reviewer does not approve a plan with a dependency or a migration nobody accepted.

### The `RESULT` contract

Every stage agent launched by `/pipeline:ship` ends its reply with this block:

```
RESULT: DONE | ESCALATE
STATUS: <spec status after the stage>
METRICS: <key=value; …>
KIND: <only with ESCALATE — decision | permission | tooling>
ESCALATION: <only with ESCALATE — problem; options (≤ 4); recommendation; why>
SUMMARY: <≤ 10 lines; for reviewer/report — findings table: id | severity | one sentence>
```

`STATUS` is the spec status after the stage; `METRICS` its `key=value` pairs; `ESCALATION`
appears only with `ESCALATE` — the problem, up to four options, a recommendation and why;
`SUMMARY` is at most ten lines, and for the reviewer in `report` mode a findings table
(id, severity, one sentence).

`KIND` says what the escalation is: `decision` is a question about the product or the plan,
`permission` a tool call refused or left unanswered by a permission rule or the auto-mode
classifier, and `tooling` a broken tool, environment or CI. A RESULT with `ESCALATE` and no
valid `KIND:` counts as `decision`. Only `decision` escalations count toward the third
escalation of one stage that stops the pipeline.

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
- a conflict on `git merge origin/main`.

### Implementation and review

**Test first.** `plan` orders each step so that its proving test is written and run before
the product change, and `plan-review` checks that order. `implement` keeps it as guidance: a
proving test that passes before the change either does not exercise the AC and is rewritten
until it fails on an assertion about the AC's behaviour, or it shows that the behaviour
already exists, which is a gap in the SPEC and escalates. The final review's tests
perspective still proves that tests test something, by breaking the code they cover.

**Dependencies.** A dependency that the SPEC or the PLAN accepts under `## Owner decisions`
is added by the implementer itself, and nothing beyond what the change needs. An unaccepted
one escalates. A plan writes no step for the owner to perform; a manual check goes into
`### Manual (performed by the owner)`, each item with a `Pass when:` line. Every
package-manager command (`uv add`, `uv lock`, `uv sync`, `npm install` and the like) runs as
its own Bash call, never chained with a file edit or another command, because the auto-mode
classifier judges a chain as a whole.

**The close.** The final review's `apply` ends at a PR with green CI and the status
`implemented`. `/pipeline:ship` then runs `workflow_metrics.py --close` (see "Closing a
spec" below), which sets `done`; run on its own, `apply` runs the same call as its last step.

**The final-review report.** The review always runs all three perspectives, for a small
change as for a large one, and each perspective reports every finding with its severity.
When the findings are merged, the report keeps at most five `nit` findings, the ones with
the highest risk or maintenance cost; the rest are left out and counted in the sentence
`Left out: N nit findings`, which also goes into the RESULT SUMMARY. `final_review_nits`
counts the reported nits. When the stage has no `Agent` tool, the three perspectives run in
one context, and the report and its SUMMARY say in one sentence that they are not
independent. The depth of the plan, its review and the report follows the
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
  plan_steps: 8                        # --derive: the steps of `## Steps`
  plan_review_blockers: 1              # --derive: the findings of `## Review log`
  plan_review_majors: 2
  plan_changes: 5                      # /pipeline:plan-review
  implement_steps: 8                   # --derive: the ticked steps
  implement_iterations: 3              # --derive: the `iterations: <k>` notes of the ticked steps
  deviations_minor: 1                  # --derive: the entries of `## Deviations`
  deviations_major: 0                  # the entries with the `major` token
  escalations: 1                       # --derive: the owner-decision entries; the total of all kinds
  escalations_permission: 0            # optional: the same entries by kind
  escalations_tooling: 0
  final_review_blockers: 0             # --derive: the findings `F<n>` of `## Final review`
  final_review_worth_fixing: 3
  final_review_nits: 2
  findings_accepted: 3                 # --derive: the ids of the `gate` entry
  findings_rejected: 2
  finished_at: "2026-09-15T14:30"      # --close
  cost_plan_cents: 180                 # --close, through `--record-cost`
  cost_plan_review_cents: 120
  cost_implement_cents: 950
  cost_final_review_cents: 610
```

Since 0.9.0 the counters that can be read from the spec files are derived, not counted by
an agent: `workflow_metrics.py --derive` writes them (see "Deriving counters" below), so a
count survives an escalated stage. A stage agent writes `plan_changes` and `started_at`
itself; the cost keys and `finished_at` come from `--close`.

Specs recorded before 0.8.0 carry one `deviations:` counter instead of the two split keys;
it still passes `--check`. The cost keys and `escalations_permission` and
`escalations_tooling` are never required, because a cost can be missing (another machine,
the cloud, expired transcripts). The legacy keys `converge_gaps` and `implement_chunks`,
which stages wrote before 0.9.0, stay valid in the specs that carry them and are no longer
written.

A report over all specs — a table per spec, totals, the share of significant findings
caught before code, and escalations per spec. A counter column shows only when some spec
carries that key. Where specs carry cost keys, three more lines follow: the plan review's
and the final review's cost per significant finding (each over the specs with that stage's
cost) and the cost per plan step (over the specs with all four costs), in cents rounded
half up; a line with no data is left out. Every cost line ends with the label "a lower
bound: output tokens are undercounted", because Claude Code often logs the output count
from the start of the stream:

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
For a spec in status `plan-draft`, `plan-approved` or `implemented` it also lints the plan:
every AC of the SPEC has a row in the PLAN's AC → steps matrix, and every item of
`### Manual (performed by the owner)` has a line starting with `Pass when:` (the Polish
literal comes from the section map), or the section is the single line `n/a — <reason>`
(as a list item or not). Items are `- ` or numbered list items; text with no item at all is
read as one scenario, so prose needs its pass line too.
Specs in the other statuses are not linted, so everything closed before 0.9.0 still passes.
Exit code: `0` and silence when everything holds; `1` with a description of EVERY problem on
stderr (never a traceback); `2` when the arguments are wrong. The closing step of every
stage runs `--derive` and then `--check` before reporting success, and `--close` will not
set `done` on red. Red that a stage cannot fix from its own artifacts must not be papered
over with an invented value — it is an escalation to the owner.

Keys due by status:

| status | required keys |
|---|---|
| `spec-draft`, `spec-ready` | none |
| `plan-draft` | `started_at`, `escalations`, `plan_steps` |
| `plan-approved` | the above + `plan_review_blockers`, `plan_review_majors`, `plan_changes` |
| `implemented` | the above + `implement_steps`, `implement_iterations`, and either `deviations` or both `deviations_minor` and `deviations_major` |
| `done` | `started_at`, `finished_at`, every counter from the block above except the optional ones (the legacy keys, `escalations_permission`, `escalations_tooling`, the `cost_*` keys), and either deviations form |

A consumer must have the rule `Bash(workflow_metrics.py *)` in `permissions.allow` — a stage
subagent cannot answer a permission prompt, so without it every `--check`, `--derive` and
`--close` stalls. `templates/settings.json` carries it for
new projects. A rule written with `${CLAUDE_PLUGIN_ROOT}` does not work: Claude Code does
not substitute permission rules.

### Deriving counters (`--derive`)

```bash
workflow_metrics.py --derive <spec-directory>
```

Reads SPEC.md and PLAN.md and writes the counters it can read into the `metrics:` block, by
the same exact line edit as `--record-cost`. It reads fixed forms, which the templates
carry and the skills write: a ticked step ends with the note `iterations: <k>` in
backticks (the iterations beyond the first attempt, 0 when green at once); a deviation is
`- `minor` — …` or `- `major` — …`; a review-log finding is a list item that starts with
`blocker`, `major` or `minor` in backticks, and a review with no finding says so with the
item `- `none` — no findings`; a final-review finding is
`- **F<n>** `<blocker|worth-fixing|nit>` — …`; an owner-decision entry is
`- YYYY-MM-DD — <stage> — `<kind>` — <question> — <decision>`, with the kind `decision`,
`permission`, `tooling` or `gate`, and a `gate` entry ends with `accepted`: F1, F2;
`rejected`: F3 (`none` for an empty list; a review with no findings records
`accepted`: none; `rejected`: none). The dashes of an entry may be `—`, `–` or `-`.
Headings are found in either language through the section map.

It writes only the keys whose source it finds in the expected form, names every key it did
not write on stderr with the reason, leaves every other byte of SPEC.md as it was, and
exits `0`; run twice, it writes the same values, so a stage agent started after an
escalation gets back the counts of the agents before it. A ticked step without its
`iterations` note leaves `implement_iterations` unwritten, and a missing note is never
counted as zero. In the same way a PLAN with no `## Deviations` section leaves the
deviation counters unwritten, and a review log with neither a finding item nor a `none`
item leaves the plan-review counters unwritten. `escalations` counts the non-gate entries of SPEC.md and PLAN.md and
`escalations_permission` and `escalations_tooling` the same entries by kind; a top-level
entry of PLAN.md's owner decisions that is not in the fixed form leaves all three
unwritten. It exits `1` only for a SPEC.md it cannot read.

### Recording cost (`--record-cost`)

```bash
workflow_metrics.py --record-cost <spec-directory> [--transcripts <dir>]
```

Prices what the spec's four stage subagents spent and writes `cost_plan_cents`,
`cost_plan_review_cents`, `cost_implement_cents` and `cost_final_review_cents` into its
`metrics:` block. `--close` runs it, and a spec closed by hand is costed with the same call.

- **What counts.** A subagent whose type is `planner`, `plan-reviewer`, `implementer` or
  `reviewer`, whose prompt names the spec directory (`NNN-<slug>`) and which ran inside this
  repository — the main checkout, the spec's checkout or `worktree.dir` — plus every
  subagent it started (the final review's perspectives). Report and
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

### Closing a spec (`--close`)

```bash
workflow_metrics.py --close <spec-directory>
```

`/pipeline:ship` runs it in Closing, after the reviewer's `apply` returned `DONE`, as a
background Bash call (`run_in_background`): the wait for CI outlasts the foreground Bash
limit. It refuses (exit `1`, nothing changed) on `main`, `master` or a name in
`protectedBranches`, when the status is not `implemented`, when the working tree is not
clean, or when the branch has no open PR. Then, in this order, it records the cost (its
warnings never stop the close), sets the status `done`, a `stage_history` entry and
`finished_at`, runs `--derive` and `--check` (on red it restores SPEC.md and exits `1`
without committing), reads the attempt numbers of the PR head's checks, commits
`docs: close SPEC NNN <slug>` with SPEC.md only, pushes the lane branch without force, waits
for the checks of the new head and re-runs the failed jobs once (`gh run rerun <id>
--failed`). A consumer needs CI checks on the PR: a branch with no Actions run never goes
green, so the wait ends at its timeout. The poll interval and the timeout come from
`PIPELINE_CLOSE_POLL_SECONDS` (default 15) and `PIPELINE_CLOSE_TIMEOUT_SECONDS` (default
3600); a re-run run is judged only once its attempt number has grown. Every `git` and `gh`
call ends after `PIPELINE_CLOSE_CALL_TIMEOUT_SECONDS` (default 300) and never prompts
(`GIT_TERMINAL_PROMPT=0`, `GH_PROMPT_DISABLED=1`). The backlog excuses a flaky job only
when an entry names it as a code span, as `gh pr checks` shows it (`` `plugin` ``): a bare
word in prose does not.

| exit | meaning |
|---|---|
| `0` | the checks of the new head are green; a job that passed only on the re-run is printed |
| `1` | refused, or derive or check was red; nothing was changed or committed |
| `3` | a job on the PR head passed only on a later attempt and `docs.backlog` does not name it as a code span; nothing committed |
| `4` | the commit or the push failed |
| `5` | the checks are red after the one re-run, or the wait timed out |

Every non-zero exit prints one line, `close stopped at <step>: <reason>; committed:
yes|no, pushed: yes|no`, and names the way out. Every stop before the commit restores
SPEC.md, so a second run is not refused. An unexpected error or a SIGTERM stops the same
way, with the code of the state it left: `1` before the commit (SPEC.md restored), `4`
before the push, `5` after it. A second `--close` after a stop that committed does not commit again: it
resumes from the push or the wait. The script runs `git push` and `gh` itself, outside the
command guard's view, so it checks the protected branches on its own, pushes only
`origin <current branch>` and never uses force.

## CHANGELOG

Full version history: [CHANGELOG.md](CHANGELOG.md).
