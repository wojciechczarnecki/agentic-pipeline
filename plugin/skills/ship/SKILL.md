---
name: ship
description: The pipeline orchestrator — takes a feature from the SPEC (status spec-ready or later) to an open PR, running the stages as subagents with a fresh context; the owner steps in only on escalation and for the decisions after the final review.
argument-hint: <spec number or slug>
---

# /pipeline:ship — from SPEC to PR

Role: coordinator, not executor. You do not plan, do not implement and do not review
yourself — every stage is done by a separate subagent with a fresh context (it gives the
same as a new session after `/clear`). Your context has to stay light: you read the SPEC.md
frontmatter, `## Owner summary` from PLAN.md and the RESULT blocks from the subagents — not
the diff, not the code.

## Project configuration

- Read `.claude/workflow.json`; no file = the defaults from the plugin README → `/pipeline:init`.
- `<verify.command>`, `<docs.specsDir>` etc. = values from this configuration (keys in the README).

## Language

- Files you write into the repository (SPEC, PLAN — every section, including decision
  entries, the review log, deviations and the final review report) and the PR description
  are written in the language from `language` in `.claude/workflow.json`; a missing key or
  a value other than `en`/`pl` = `en`. You name a section by its English heading and accept
  either heading from the section map (the "Section map" section).
- Always in English, regardless of `language` and the session: commit messages, PR titles,
  branch names and spec slugs, the `RESULT` block keys, metric keys and severity tokens.
- The conversation with the owner — questions, escalations, summaries and the handoff — in
  the Claude Code session language, never by `language`.

## Section map

- Before you look for a section in a SPEC or PLAN, load the section map
  `${CLAUDE_PLUGIN_ROOT}/templates/sections.md` with the `Read` tool (key → Polish heading →
  English heading). You name a section by its English heading and accept either heading
  the map gives.
- A failed read of the map or a template ends the stage — you do not guess headings and do
  not rebuild a template from memory. Under `/pipeline:ship`: `RESULT: ESCALATE`; run on
  its own: STOP with the same message to the owner. The message gives the file path and
  the rule to add to `permissions.allow` (the project's `.claude/settings.json` or the user
  settings): `Read(~/.claude/plugins/cache/<marketplace>/pipeline/**)`, and for a
  `--plugin-dir` clone — `Read(//<plugin directory path without the leading />/**)`; you
  read `<marketplace>` from the expanded path `${CLAUDE_PLUGIN_ROOT}`
  (`…/plugins/cache/<marketplace>/pipeline/<version>`); when the guard has already shown a
  warning with a ready rule, you give that rule.

## State

The source of truth is `status:` in SPEC.md, not this conversation. `/pipeline:ship`
interrupted at any point resumes from the current status — also for specs started
by hand stage by stage.

| Status          | Agent           | Mode     | DONE result                             |
|-----------------|-----------------|----------|-----------------------------------------|
| `spec-ready`    | `planner`       | —        | `plan-draft`                            |
| `plan-draft`    | `plan-reviewer` | —        | `plan-approved` (itself, when there is no escalation) |
| `plan-approved` | `implementer`   | —        | `implemented`                           |
| `implemented`   | `reviewer`      | `report` | findings report → **owner gate**        |
| `implemented` + decisions recorded | `reviewer` | `apply` | PR with green CI; the status stays `implemented` |
| `implemented` + the `apply` RESULT in hand | `workflow_metrics.py --close` (Closing) | — | `done` |
| `done`          | —               | —        | STOP: nothing to do (give the PR link, if it exists) |

Status `spec-draft` or no SPEC → STOP: `/pipeline:idea` first.

## Start

1. Determine the spec (the argument; without an argument list `<docs.specsDir>/*/SPEC.md`
   with a status from `spec-ready` to `implemented` and ask which one to take).
2. `git status` clean. The lane branch `feat/NNN-<slug>`: it exists → `git switch` to it; it
   does not exist →
   `git switch main && git pull --ff-only && git switch -c feat/NNN-<slug>`. In parallel
   work the session already runs in the lane's worktree — do not switch branches.
3. No `metrics.started_at` in the SPEC → add it (`date +%Y-%m-%dT%H:%M`) and commit. The
   flat `metrics:` block holds counters as integers, and timestamps in the format
   `%Y-%m-%dT%H:%M`.
4. Tell the owner which model each stage runs on, in one message before the first stage
   agent starts: `plan`, `plan-review`, `implement` and `final-review`, each with the alias
   you will pass to `Agent` as `model` (from `models.<stage>`, as the next section says).
   `inherit`, a missing entry or any other value shows as "session model".

## Starting a stage agent

The `Agent` tool with the agent type from the table. The agents come from this plugin, so in
a session they are visible under prefixed names: `pipeline:planner`,
`pipeline:plan-reviewer`, `pipeline:implementer`, `pipeline:reviewer` — use these names as
`subagent_type`. If the session does not know the prefixed name, use the bare agent name
(`planner` etc.).

The prompt contains only: the spec number and path, the mode (for `reviewer`), the working
directory and a reminder of the contract below. Do not pass the history of this conversation
or your own hypotheses — a fresh context is part of the method. The path is written as
`<docs.specsDir>/NNN-<slug>/SPEC.md`, because `--close` in Closing, which runs
`--record-cost`, attributes a stage agent to its spec by the spec directory named in its
prompt; an agent started without it is left out of the cost.

The model per stage comes from `models.<stage>` in `.claude/workflow.json`, with the stage
keys `plan` → `planner`, `plan-review` → `plan-reviewer`, `implement` → `implementer` and
`final-review` → `reviewer` (both `report` and `apply`). When the entry is `sonnet`, `opus`,
`haiku` or `fable`, pass it to `Agent` as `model`. When it is `inherit`, missing, or any
other value, pass no `model`: the agent then runs on the session model. The guard's warning
about a bad value goes to stderr, which a normal session does not show, so name every
`models` entry you ignored, with its value, in the summary for the owner. The same holds for
a stage run again under the Result protocol.

You wait for the stage agent's result before you go on.

## Stage agent contract

Binding on every agent started by `/pipeline:ship`:

- You carry out the loaded stage skill. You cannot ask the owner (`AskUserQuestion` is
  unavailable). Wherever the skill says to ask, to wait or to STOP — you end your work
  with a `RESULT: ESCALATE` block.
- Owner decisions from SPEC.md and PLAN.md → `## Owner decisions` are binding; do not
  escalate again a matter already settled.
- You record state in the spec files and in commits, never only in the reply.
- Language: spec files and the PR description in `language`; commits, the PR title and the
  RESULT block keys in English; the orchestrator shows the ESCALATION and SUMMARY text to
  the owner in the session language.
- The counters of the flat `metrics:` block in the SPEC.md frontmatter that
  `workflow_metrics.py --derive <spec-dir>` can read — `escalations` among them — come from
  the fixed forms in SPEC.md and PLAN.md, not from a count of yours: you run `--derive` and
  write only the keys your skill names itself. Counters are integers, timestamps
  `%Y-%m-%dT%H:%M`.
- The final reply starts with the block:

```
RESULT: DONE | ESCALATE
STATUS: <spec status after the stage>
METRICS: <key=value; …>
KIND: <only on ESCALATE — decision | permission | tooling>
ESCALATION: <only on ESCALATE — problem; options (≤ 4); recommendation; why>
SUMMARY: <≤ 10 lines; for reviewer/report — the findings table: id | severity | one sentence>
```

`KIND` says what the escalation is. `decision` is a question about the product or the plan.
`permission` is a tool call refused or left unanswered by a permission rule or the auto-mode
classifier. `tooling` is a broken tool, environment or CI. A RESULT with `ESCALATE` and no
valid `KIND:` counts as `decision`.

## Result protocol

- No RESULT block, or a `STATUS` that does not match the file → run the stage again once;
  the second time → escalate yourself, describing what the agent returned.
- **ESCALATE** → read `KIND` (a missing or invalid `KIND:` counts as `decision`) and ask
  with `AskUserQuestion`: the question from `ESCALATION`, the options from the agent, the
  recommended one first with the label suffix "(Recommended)" — asked in the session
  language, whatever the language the agent wrote them in. Append the answer to PLAN.md →
  `## Owner decisions` (when PLAN.md does not exist yet — to the same section of SPEC.md)
  in the language from `language`, as one entry in the fixed form
  `- YYYY-MM-DD — <stage> — `<kind>` — <question> — <decision>`, with the `KIND` of the
  RESULT as `<kind>`: `--derive` counts these entries into `escalations`, so you do not
  touch `metrics.escalations`. Commit (`docs: record owner decision for NNN`) and start a
  new agent of the same stage.
- The same stage escalates with kind `decision` for the third time → STOP. Describe the
  situation to the owner and ask them to take over. Only the `decision` entries of the same
  stage count toward the third one: `permission` or `tooling` escalations do not count,
  because a refused tool call or a broken runner is not a question the stage keeps asking.

## Escalation triggers (binding on every agent)

- a new dependency or a major version bump of an existing one,
- a data migration (the `migrations` section of the configuration),
- a gap or contradiction in the SPEC,
- a blocker from the plan review that the reviewer cannot fix in the plan itself,
- a deviation from the plan that changes the scope, the architecture or the data schema,
- the self-correction loop exhausted (the 4th iteration on the same error),
- a test finds a product defect whose fix goes beyond the plan's scope or the owner
  decisions — instead of working around it by changing the test or the test data,
- a conflict on `git merge origin/main`.

## Gate: final review

1. `reviewer` in `report` mode → the report in PLAN.md → `## Final review`.
2. Show the owner the findings table from SUMMARY, together with its sentence on how many
   `nit` findings were left out, and ask `AskUserQuestion` — both in the session language,
   severity tokens untranslated:
   "Accept `blocker` and `worth-fixing`, reject `nit` (Recommended)" / "Accept
   all" / "I will choose one by one" / "Only `blocker`". On "I will choose one by one" ask
   for the list of ids.
3. Record the decisions in `## Owner decisions` in the language from `language`, commit:
   one entry of kind `gate`,
   `- YYYY-MM-DD — final-review — `gate` — <question> — `accepted`: F1, F2; `rejected`: F3`
   (`none` for an empty list); `--derive` counts the accepted and rejected ids from it.
4. `reviewer` in `apply` mode → fixes, push, PR, green CI; the status stays `implemented`
   (`--close` in Closing sets `done`).

No findings in the report → skip the question, not the entry: record one `gate` entry with
two empty lists, `- YYYY-MM-DD — final-review — `gate` — <question> — `accepted`: none;
`rejected`: none`, commit, and go on to `apply`. Without it `--derive` writes no
`findings_accepted`/`findings_rejected` and `--close` stops at the check.

## Closing

1. From the `reviewer/apply` RESULT take the PR link, the CI status and the link to the
   visual artifacts of the CI run.
2. Close the spec: run `workflow_metrics.py --close <docs.specsDir>/NNN-<slug>` by name,
   through `PATH`, as a background Bash call (`run_in_background`) and wait for it to end.
   It records the cost, sets `done`, derives and checks the metrics, commits
   `docs: close SPEC NNN <slug>`, pushes and waits for the CI of the new head, re-running
   failed jobs once. The wait (3600 s by default, twice with the re-run) outlasts the
   foreground Bash limit, so a foreground call would be killed. When the call ends, read its
   exit code and its stop line (the last line of stderr).
3. Exit code 0 → `PushNotification`: "PR NNN ready to merge: <title>" — only with green CI.
   A job that `--close` printed as passed only on a re-run goes into the summary.
4. A non-zero exit → the stop line says which step stopped and what state is left: ask the
   owner with `AskUserQuestion`, in the session language, with the options "resume the
   closing step only" — run `--close` again, which resumes from the push or the wait, with
   no new `reviewer` — / "`reviewer` `apply` again" with the stop line as its task / "I will
   take over". The recommended option, first and marked "(Recommended)", follows the exit
   code. Exit 4 (the commit or the push failed) and exit 5 (red after the re-run, or the
   wait timed out) → resume, because the close commit is made or the spec is unchanged and a
   second run picks up from there. Exit 1 (refused, or derive/check red, SPEC.md restored)
   and exit 3 (a job passed only on a later attempt and `<docs.backlog>` does not name it)
   → `reviewer` `apply` again, because a resume would repeat the same stop: the reviewer
   fixes the spec files or adds the backlog entry, naming the job as a code span.
5. Summary for the owner: the PR link, the CI status, the link to the visual artifacts, the
   manual scenarios to check before the merge (from PLAN.md →
   `### Manual (performed by the owner)` in `## End-to-end verification`), the spec metrics,
   a job `--close` named, and the `models` entries you ignored.

## Guardrails

- You never merge the PR — that is the owner's gate (also enforced by this plugin's command
  guard).
- You do not skip stages and do not do a stage's work in your own context, not even "small"
  work.
- You never set a spec status: the stages do, and `workflow_metrics.py --close` sets `done`.
  You do not edit spec files or documents yourself, except for `started_at` and the entries
  of `## Owner decisions`.
