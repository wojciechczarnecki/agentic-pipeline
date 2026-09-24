---
status: spec-ready
stage_history:
  - "spec-draft — 2026-09-24"
  - "spec-ready — 2026-09-24"
metrics:
  started_at: 2026-09-24T14:32
  escalations: 0
---

# SPEC 011 — Cost per stage, a model per stage and targeted reading

## Goal

Stage 7 has to make the pipeline cheaper without losing quality, and it can only
do that on numbers. This spec delivers what the comparison needs, in release 0.8.0: every spec
records what each stage cost, `deviations` separates minor from major, the converge pass
records its gaps, and a consumer can choose a model per stage. On top of that,
every stage stops reading the whole decision log and roadmap and searches them by the feature's
topic. Success: `/pipeline:ship` closes a spec with `cost_*` keys in its metrics; the
metrics report shows the cost per significant finding of the plan review and the final
review; a consumer with `"models": {"implement": "sonnet"}` gets an implementer on
Sonnet and every other stage on the session model.

## Context

- The Stage 7 cost audit (2026-09-24, `docs/DECISIONS.md`) was computed once from local
  transcripts, and the code it used is not in the repository. The implementer takes about 40% of a spec's cost, the final
  review 33–41%. Fresh subagents pay 25–43% of their cost in cache writes, much of it for
  documents they read whole (the consumer's documents are 271 KB).
- Metrics: `plugin/bin/workflow_metrics.py` — a flat `metrics:` block of integer counters
  and two timestamps, `--check` per status (`REQUIRED`), unknown keys refused, a report
  with totals and ratios. `deviations` is required from `implemented`.
- Orchestration: `plugin/skills/ship/SKILL.md` starts `pipeline:planner`,
  `pipeline:plan-reviewer`, `pipeline:implementer` and `pipeline:reviewer` with the `Agent`
  tool; all four agents have `model: inherit` (`plugin/agents/*.md`).
- Measured on Claude Code 2.1.281 (2026-09-24): the `Agent` tool takes `model` only as an
  alias (`sonnet`, `opus`, `haiku`, `fable`), with no effort level. A plugin agent's
  frontmatter takes `effort` (`low`, `medium`, `high`, `max` or an integer), but only as a fixed value that a consumer cannot override.
  Subagent transcripts live in `~/.claude/projects/<project slug>/<session>/subagents/`
  as `agent-<id>.jsonl` with `agent-<id>.meta.json` (`agentType`, e.g.
  `pipeline:implementer`; `parentAgentId` on the final review's perspectives). Every
  assistant entry carries `usage` with `input_tokens`, `cache_creation_input_tokens`
  (split into 5-minute and 1-hour writes), `cache_read_input_tokens` and `output_tokens`,
  and the model's name. A worktree lane has a project slug of its own.
- The owner keeps an archive of transcripts outside both repositories
  (`~/claude-transcripts-archive`, `cleanupPeriodDays` 365), because the baseline for
  the comparison is costed after the fact.
- Reading today: `plan` reads `<docs.decisions>` and the domain documents whole (step 3),
  `plan-review` checks the plan against the whole `<docs.decisions>`, `idea` lists
  the roadmap, the project document, the decisions and every domain document in
  `## Read context`.

## Read context

- `docs/ROADMAP.md` — Stage 7. This spec delivers four of the five 0.8.0 items: targeted
  reading, the `models` section, the `deviations` split, and cost per stage with
  `converge_gaps` and the cost per significant finding. The chunked implementer goes to
  a spec of its own, because it needs cost per stage to be measured. Cheaper eval runs,
  the before/after comparison and the write-up are separate items. The roadmap item on
  `models` asked to check whether an effort level can be passed before this spec was
  written: see Context.
- `docs/PROJECT.md` — the requirement "workflow metrics report across specs" is extended.
  The non-functional requirements bind: plain `python3` with no runtime dependencies,
  and no consumer specifics in the plugin (model and stage names are the plugin's own).
- `docs/DECISIONS.md` — 2026-09-24 cost audit: no stage is dropped, the savings come from
  model and effort, targeted reading and chunking; the baseline is costed from
  transcripts after the fact; the converge pass goes back to the owner when
  `converge_gaps` stays at zero. 2026-09-24 (SPEC 010): a new required key would turn
  `--check` red for specs started earlier. 2026-09-23: metric keys are English
  regardless of `language`. The guard never blocks on configuration, it only warns.
- `docs/BACKLOG.md` — P2 "Targeted reading needs findable decisions" fires only after
  this spec ships, so it stays in the backlog. P3 "final review perspectives on Sonnet"
  waits for the comparison. P2 "a stage calls `workflow_metrics.py` by path"
  applies to the new call in `ship` (by name).
- `docs/CONVENTIONS.md` — pytest for every behaviour change; a version bump and a
  CHANGELOG entry; skill text follows the normal-volume style.
- `plugin/README.md` — the section on configuration keys, the metrics format and
  `--check` is the documentation that changes.

## Scope

- **Cost per stage.** `workflow_metrics.py` gets a mode that finds a spec's stage subagents
  in the transcripts, adds up their tokens per stage and writes `cost_plan_cents`,
  `cost_plan_review_cents`, `cost_implement_cents` and `cost_final_review_cents` into
  `metrics:` in SPEC.md. The perspectives count toward the final review, and so do
  report and apply. The default source is `~/.claude/projects`, and an option takes another
  directory (the archive). Prices come from a rate table kept in the script, fixed at the
  API list rates of 2026-09-24. Old rates are never changed: the table only gains new
  models, at their launch rates, so a cent is a fixed unit and numbers from different
  years can be compared. The script prints the token breakdown per stage and type
  to stdout.
- `/pipeline:ship` runs that mode in Closing, after `reviewer/apply`, and commits and pushes the
  result to the PR branch. This is the one exception to "ship does not edit spec files":
  the script does the editing.
- **`converge_gaps`**: `implement` records the number of real gaps its converge passes
  reported.
- **`deviations` split** into `deviations_minor` and `deviations_major`.
- **Report**: new columns, the cost per significant finding of the plan review and of the
  final review, and the cost per plan step.
- **`models` in `.claude/workflow.json`**: a model per stage, passed by `/pipeline:ship`
  to the `Agent` tool. Without the section, or for a stage it does not name, the stage inherits
  the session model, as today. `/pipeline:init` writes `"implement": "sonnet"` for new
  projects, and the README marks this as a guess not yet measured. The README also
  describes effort: a plugin default, not configurable.
- **Targeted reading**: SPEC, PLAN and `<docs.conventions>` read in full;
  `<docs.decisions>`, `<docs.roadmap>` and domain documents searched by the feature's
  topic. `idea` lists what it read and how in `## Read context` of the SPEC, and `plan` does
  the same in PLAN.md. The other stages search by topic for their own checklist.
- Release 0.8.0: version, CHANGELOG with a consumer-impact line, README.

## Out of scope

- The chunked implementer: a separate spec (next number), 0.8.0 or later. It needs cost per
  stage to be measured.
- Cheaper eval runs (`scripts/`): a separate item of Stage 7 (fast path or its own spec).
- The before/after comparison, the measured defaults (the `models` section written by `init`,
  `effort` in the agents' frontmatter) and the write-up: after 0.8.0, in a later
  release. In this spec the agents do not get `effort`; they inherit it from the session.
- The cost of the `/pipeline:ship` orchestrator and the `idea` dialogue: they live in the main
  session mixed with other work. The measure is the four stage subagents.
- An effort level configured by the consumer: not possible in Claude Code 2.1.281 (see
  Context). It returns to the backlog if the `Agent` tool starts to accept it.
- An index at the top of `DECISIONS.md` (`docs/BACKLOG.md` P2): its trigger fires only after
  targeted reading ships.
- A new eval case: the new behaviours are pinned with pytest on the script and the skill
  texts.

## Requirements and acceptance criteria

Cost per stage

- [ ] AC1: `workflow_metrics.py --record-cost <spec-dir>` run over a transcript directory
      with subagents of all four stages for that spec writes `cost_plan_cents`,
      `cost_plan_review_cents`, `cost_implement_cents` and `cost_final_review_cents` into
      the SPEC.md frontmatter as integers equal to the sum of the stage's tokens × the
      rate table. It rounds only the stage total. The test uses a fixture with known
      tokens and an expected result computed by hand.
- [ ] AC2: the final review perspectives (subagents with `parentAgentId` of a
      `pipeline:reviewer` agent) count toward `cost_final_review_cents`, and so do both
      reviewer runs (report and apply). A stage run again after an escalation counts toward
      that stage.
- [ ] AC3: stage subagents of another spec, including one with the same number in another
      repository, are not counted. The fixture holds such a subagent, and the result does
      not change when it is added.
- [ ] AC4: the option `--transcripts <dir>` computes the cost from that directory. Without
      it, the source is `~/.claude/projects`, and lanes in worktrees are found too
      (a different project slug).
- [ ] AC5: running it a second time replaces the `cost_*` keys instead of adding
      them again. The rest of the frontmatter and the rest of the file are left byte for
      byte.
- [ ] AC6: a model missing from the rate table → that stage's key is not written, and
      stderr names the model. A stage with no transcripts → no key and a warning. No
      transcripts at all → the file is unchanged, exit 0 with a warning, because a
      missing cost must not stop the closing of a spec.
- [ ] AC7: stdout of `--record-cost` shows, per stage, the tokens by type (input, cache
      write 5 min, cache write 1 h, cache read, output), the model and the cost.
- [ ] AC8: the rate table in the script has a date (2026-09-24) and a comment saying that
      existing rates are never changed. A test pins the rates of the models from the
      audit.

Metrics and `--check`

- [ ] AC9: `converge_gaps`, `deviations_minor`, `deviations_major` and the four `cost_*`
      keys are known integer counters. `--check` does not refuse them and requires none
      of them, at any status.
- [ ] AC10: at `implemented` and `done`, `--check` accepts either `deviations` or
      both `deviations_minor` and `deviations_major`. With neither → an error naming
      both forms. The existing `specs/*/SPEC.md` of this repository still pass `--check`.
- [ ] AC11: `implement` (skill and agent METRICS) writes `converge_gaps`,
      `deviations_minor` and `deviations_major` instead of `deviations`. Major = a
      deviation that changes the scope, the architecture or the data schema (the one that
      escalates); minor = every other entry in `## Deviations`. Pinned with pytest on the
      texts.
- [ ] AC12: the report has columns for the new keys (a missing one = `-`) and the
      lines "Plan review cost per significant finding" (the sum of `cost_plan_review_cents`
      / the sum of `plan_review_blockers + plan_review_majors`) and "Final review
      cost per significant finding" (`cost_final_review_cents` /
      `final_review_blockers + final_review_worth_fixing`), each only over specs with
      the cost key, and a line "Cost per plan step" (the sum of the four costs /
      `plan_steps`, also only over specs with all four keys). With no
      data, the line is not shown.
- [ ] AC13: `/pipeline:ship` in Closing runs `workflow_metrics.py --record-cost` (by
      name, via `PATH`) after `reviewer/apply` returns DONE and before `PushNotification`,
      and commits (`chore: record stage cost for NNN`) and pushes the change when there is one
     . The guardrail "you do not edit spec files" names this
      exception. Pinned with pytest on the text of `ship`.

Model per stage

- [ ] AC14: `.claude/workflow.json` accepts `models` with the keys `plan`, `plan-review`,
      `implement` and `final-review` and the values `inherit`, `sonnet`, `opus`, `haiku`
      and `fable`. An unknown key or value → a configuration warning (like other bad
      keys) and that stage on `inherit`. The guard never blocks on it. Tested in
      `workflow_config`.
- [ ] AC15: `/pipeline:ship` passes `model` to the `Agent` tool for a stage whose `models`
      entry is other than `inherit`, and does not pass it otherwise. Pinned with pytest on
      the text of `ship`.
- [ ] AC16: `/pipeline:init` writes `"models": {"implement": "sonnet"}` into a new
      `.claude/workflow.json`. `plugin/templates/workflow.example.json` and the README
      show the section. The README says that it is a guess not yet measured (Stage 7
      comparison), that an effort level cannot be configured and why, and that effort
      stays a plugin default.
- [ ] AC17: the agents in `plugin/agents/*.md` do not get `effort` in this release
      (a pytest check that none of them sets the key, removed when the measured defaults
      land).

Targeted reading

- [ ] AC18: the skills `plan`, `plan-review`, `implement` and `final-review` say: SPEC,
      PLAN and `<docs.conventions>` are read in full; `<docs.decisions>`,
      `<docs.roadmap>` and domain documents are searched by the feature's topic (its
      terms and the names of the files it changes), and are read whole only when the
      search leaves the question open. Pinned with pytest on the texts.
- [ ] AC19: `idea` writes in each item of `## Read context` whether the document was read
      in full or searched, and for which terms. `plan` writes the same list into PLAN.md.
      `plan-review` checks the plan against the decisions it found by its own search.
      Pinned with pytest on the texts.

Release

- [ ] AC20: version `0.8.0` in `plugin/.claude-plugin/plugin.json`, an entry in
      `plugin/CHANGELOG.md` with a consumer-impact line (new optional keys; `models`
      is optional; a consumer who wants cost needs local transcripts), README
      updated, and `bash scripts/check.sh` green.

## Decisions and rejected alternatives

| Decision | Rejected alternatives | Rationale |
|----------|-----------------------|-----------|
| Cost in cents at API rates frozen on 2026-09-24: the table is never repriced, it only gains new models | current prices; tokens only; cents + 16 token keys in the frontmatter; cents + a token table in PLAN.md | A frozen unit keeps numbers from different years comparable when prices change. Tokens without their type mean nothing, and 16 keys crowd the frontmatter. Raw data stays in the transcript archive and on stdout |
| Four stages: plan, plan review, implement, final review (report + apply + perspectives) | adding the orchestrator; adding the orchestrator and `idea` | Stage subagents can be attributed without doubt from `agentType` and the prompt; the main session is mixed with other work, and the orchestrator is lightweight by design |
| The cost is recorded by `ship` in Closing through the script | `reviewer/apply` before `done`; only by hand | Only after apply are all the stages finished. The script edits the file, so `ship` stays a coordinator |
| `models` sets only the model; effort is a plugin default in the agents' frontmatter | agent variants per effort (planner-low …); dropping effort from Stage 7 | The `Agent` tool does not take effort (2.1.281), and variants would make 4 × 3 agent files |
| `init` writes the guess `implement: sonnet`, and the other stages inherit | every stage `inherit`; `implement` and `plan` on Sonnet; no section until the comparison | The implementer is ~40% of the cost and carries out a detailed plan with tests; the loop, converge and the final review catch its mistakes. Planning and both reviews are judgement, where Opus is worth its price. One variable keeps the comparison easy to read |
| `deviations_major` = a deviation that changes scope, architecture or schema; the old `deviations` still passes `--check` | the old key counted as minor | Nobody guesses the split for older specs |
| New keys are optional for `--check` | `converge_gaps` required from `implemented` | Cost may be missing (cloud, another machine, expired transcripts), and a required key would turn specs in progress red (SPEC 010) |
| `idea` and the planner list what they read in files; the other stages search without a list | every stage in SUMMARY; every stage in PLAN.md | The list stays in the repository where the plan review and the final review can check it, without growing PLAN.md |
| `--record-cost` takes a transcript directory | only `~/.claude/projects` | The baseline (closed specs, archive) and new specs are costed by the same code, not by the audit's one-off computation |

## Owner decisions

- 2026-09-24 — scope: four 0.8.0 items; the chunked implementer in a separate spec;
  cheaper evals, comparison and write-up outside this spec.
- 2026-09-24 — `models` only for the model; effort as the plugin default in the frontmatter.
- 2026-09-24 — cost as cents in a frozen unit (4 keys), tokens only on stdout.
- 2026-09-24 — idea and the planner list what they read in files.
- 2026-09-24 — defaults: a guess based on experience, `implement: sonnet`, the rest
  `inherit`. Measurement: the baseline is the consumer's ordinary specs before 0.8.0,
  costed from the archive; after 0.8.0 3–5 specs with `models`; effort through a
  `--plugin-dir` canary; the measured defaults in a later release.
- 2026-09-24 — cost of the four stage subagents only; `ship` records it in Closing.
- 2026-09-24 — `--transcripts <dir>` for the archive.
- 2026-09-24 — `deviations_major` = escalating; the old key passes.
- 2026-09-24 — new keys optional in `--check`.
- New dependency: none. Data migration: none (existing SPEC.md files do not change).

## Open questions (non-blocking)

- The rates of the models in the table (Opus 5.5, Sonnet 5, Haiku 4.5, Fable 5.1) are
  checked by the planner against the rate list current on 2026-09-24 (`/claude-api`),
  not from memory.
