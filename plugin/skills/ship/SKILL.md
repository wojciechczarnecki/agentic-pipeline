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
| `implemented` + decisions recorded | `reviewer` | `apply` | PR with green CI + `done` |
| `done`          | —               | —        | STOP: nothing to do (give the PR link, if it exists) |

Status `spec-draft` or no SPEC → STOP: `/pipeline:idea` first.

## Start

1. Determine the spec (the argument; without an argument list `<docs.specsDir>/*/SPEC.md`
   with a status from `spec-ready` to `implemented` and ask which one to take).
2. `git status` clean. The lane branch `feat/NNN-<slug>`: it exists → `git switch` to it; it
   does not exist →
   `git switch main && git pull --ff-only && git switch -c feat/NNN-<slug>`. In parallel
   work the session already runs in the lane's worktree — do not switch branches.
3. No `metrics.started_at` in the SPEC → add it (`date +%Y-%m-%dT%H:%M`) together with
   `escalations: 0` and commit. The flat `metrics:` block holds counters as integers, and
   timestamps in the format `%Y-%m-%dT%H:%M`. The counter has to exist from the start, so
   that the metrics summary shows `0`, not `-` (no measurement).

## Starting a stage agent

The `Agent` tool with the agent type from the table. The agents come from this plugin, so in
a session they are visible under prefixed names: `pipeline:planner`,
`pipeline:plan-reviewer`, `pipeline:implementer`, `pipeline:reviewer` — use these names as
`subagent_type`. If the session does not know the prefixed name, use the bare agent name
(`planner` etc.).

The prompt contains only: the spec number and path, the mode (for `reviewer`), the working
directory and a reminder of the contract below. Do not pass the history of this conversation
or your own hypotheses — a fresh context is part of the method.

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
- You write the stage metrics yourself into the flat `metrics:` block in the SPEC.md
  frontmatter: counters are integers, timestamps `%Y-%m-%dT%H:%M`, `escalations` from the
  start. `escalations` is incremented only by the orchestrator — a stage agent does not
  change it.
- The final reply starts with the block:

```
RESULT: DONE | ESCALATE
STATUS: <spec status after the stage>
METRICS: <key=value; …>
ESCALATION: <only on ESCALATE — problem; options (≤ 4); recommendation; why>
SUMMARY: <≤ 10 lines; for reviewer/report — the findings table: id | severity | one sentence>
```

## Result protocol

- No RESULT block, or a `STATUS` that does not match the file → run the stage again once;
  the second time → escalate yourself, describing what the agent returned.
- **ESCALATE** → `AskUserQuestion`: the question from `ESCALATION`, the options from the
  agent, the recommended one first with the label suffix "(Recommended)" — asked in the
  session language, whatever the language the agent wrote them in. Append the answer (date,
  stage, question, decision) in the language from `language` to PLAN.md →
  `## Owner decisions`, and when PLAN.md does not exist yet — to the same section of
  SPEC.md. Increment `metrics.escalations`, commit (`docs: record owner decision for NNN`)
  and start a new agent of the same stage.
- The same stage escalates for the third time → STOP. Describe the situation to the owner
  and ask them to take over.

## Escalation triggers (binding on every agent)

- a new dependency or a major version bump of an existing one,
- a data migration (the `migrations` section of the configuration),
- a gap or contradiction in the SPEC,
- a blocker from the plan review that the reviewer cannot fix in the plan itself,
- a deviation from the plan that changes the scope, the architecture or the data schema,
- the self-correction loop exhausted (the 4th iteration on the same error),
- a test finds a product defect whose fix goes beyond the plan's scope or the owner
  decisions — instead of working around it by changing the test or the test data,
- a proving test from the owner or the plan that is green before the change it is meant to
  prove,
- a real gap left after the second converge pass,
- a conflict on `git merge origin/main`.

## Gate: final review

1. `reviewer` in `report` mode → the report in PLAN.md → `## Final review`.
2. Show the owner the findings table from SUMMARY, together with its sentence on how many
   `nit` findings were left out, and ask `AskUserQuestion` — both in the session language,
   severity tokens untranslated:
   "Accept `blocker` and `worth-fixing`, reject `nit` (Recommended)" / "Accept
   all" / "I will choose one by one" / "Only `blocker`". On "I will choose one by one" ask
   for the list of ids.
3. Record the decisions (accepted and rejected ids) in `## Owner decisions`
   in the language from `language`, commit.
4. `reviewer` in `apply` mode → fixes, push, PR, green CI, only then `done`.

No findings in the report → skip the gate: record in the decisions, in the language from
`language`, that there were no findings, and go on to `apply`.

## Closing

1. From the `reviewer/apply` RESULT take the PR link, the CI status and the link to the
   visual artifacts of the CI run.
2. `PushNotification`: "PR NNN ready to merge: <title>" — only with green CI. A PR
   with red CI does not get this notification; the reviewer then returns ESCALATE, which
   you handle through "Result protocol".
3. Green CI with a test passed only after a retry (flaky) → check that the reviewer added
   it to `<docs.backlog>`; if not, run `reviewer` (`apply` mode)
   again with that task. You do not edit spec files or documents yourself.
4. Summary for the owner: the PR link, the CI status, the link to the visual artifacts, the
   manual scenarios to check before the merge (from PLAN.md →
   `### Manual (performed by the owner)` in `## End-to-end verification`), the spec metrics.

## Guardrails

- You never merge the PR — that is the owner's gate (also enforced by this plugin's command
  guard).
- You do not skip stages and do not do a stage's work in your own context, not even "small"
  work.
- You do not set spec statuses for the agents — the stages do that; you only read.
