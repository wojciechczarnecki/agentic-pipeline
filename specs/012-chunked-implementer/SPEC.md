---
status: plan-approved
stage_history:
  - "spec-draft — 2026-09-24"
  - "spec-ready — 2026-09-24"
  - "plan-draft — 2026-09-24"
  - "plan-approved — 2026-09-24"
metrics:
  started_at: 2026-09-24T19:33
  escalations: 0
  plan_steps: 8
  plan_review_blockers: 0
  plan_review_majors: 2
  plan_changes: 2
---

# SPEC 012 — The chunked implementer

## Goal

The implementer takes about 40% of a spec's cost, and 52–69% of that is cache reads: one
long context re-read on every turn (the Stage 7 cost audit, `docs/DECISIONS.md`
2026-09-24). This spec lets `/pipeline:ship` run the implementer in chunks, one fresh
subagent per group of steps that the planner marks in PLAN.md. Each chunk starts from the
committed state and a note the chunk before it left. The feature is off by default: it is
a candidate for the Stage 7 comparison and is turned on per project until it measures no
worse. Success: with chunking on, a plan with three groups is carried out by three
implementer subagents. Each one stops at its group's boundary on a green, committed step,
and the last one runs the converge pass and the Definition of Done. `cost_implement_cents`
covers all three, and the spec's quality metrics are recorded as they are today.

## Context

- `plugin/skills/implement/SKILL.md` already resumes: a PLAN with ticked steps is
  continued from the first unticked one, and the rules for resuming the converge pass
  (one or two recorded passes) are written down. A chunk is a planned resumption.
- `plugin/skills/ship/SKILL.md`: the state table maps `plan-approved` → `implementer` →
  `implemented`. A `STATUS` that does not match the file triggers one re-run. `ship` reads
  only the SPEC frontmatter, the `## Owner summary` of PLAN.md and the RESULT blocks.
  `DONE` from the implementer with `STATUS: plan-approved` has no meaning today.
- `plugin/bin/workflow_metrics.py` (`stage_usage`) attributes every `implementer`
  subagent whose prompt names the spec directory to the `implement` stage and adds them
  up. Several chunks give one `cost_implement_cents` with no change to the script.
- `plugin/bin/workflow_config.py`: a schema per key, and a bad section warns and falls
  back to its defaults. `models` is checked entry by entry. The guard never blocks on
  configuration.
- `plugin/templates/PLAN.{en,pl}.md`: `## Steps` is a flat checkbox list with
  `Automatic verification:` per step. `plugin/templates/sections.md` is the one
  Polish ↔ English bridge for section literals.
- `implement_iterations` is counted by the one implementer context over all steps. A
  chunk sees only its own iterations.
- Eval cases for `implement` run the skill directly (`/pipeline:implement 001`) on a
  scaffolded fixture, not under `ship` (`plugin/evals/implement-*`).

## Read context

- `docs/ROADMAP.md` — searched for "Stage 7" and "chunk", with the Stage 7 section read
  whole. This spec delivers the 0.8.0 item "the chunked implementer", which leaves the
  step count or planner-marked groups to the spec: here, groups. The before/after
  comparison, cheaper eval runs and the write-up stay separate items. 0.8.0 is on `main`
  but not tagged, so this feature ships in 0.8.0.
- `docs/PROJECT.md` — read in full. It extends the requirement "stage skills and agents
  … with spec state kept in `SPEC.md` frontmatter so every stage resumes". Binding: plain
  `python3`, no consumer specifics in the plugin.
- `docs/DECISIONS.md` — searched for "cost audit", "chunk", "size", "tier", "threshold",
  "eval" and "2026-09-24". Binding: the cost audit keeps every stage, and Stage 7 saves on
  how stages run, including a chunked implementer. Plan and review depth follow the change
  by judgement, with no size tiers, threshold or size field (SPEC 010). That is why the
  "plans below a size threshold" of the roadmap becomes the planner's judgement here.
  A new required metric key would turn `--check` red for specs in progress (SPEC 010,
  SPEC 011). `--record-cost` counts every stage agent of the spec toward its stage
  (SPEC 011). The eval cost policy measures a new case with 5 runs (SPEC 004).
- `docs/BACKLOG.md` — read in full. None of the items concerns chunking. The P2 item on
  `implement-converge-finds-missing-ac` (a judge reading only the final message) applies to
  the new eval case's grader: its criteria ask for what a final message shows.
- `docs/CONVENTIONS.md` — searched for "eval" and "release", with the eval and release
  sections read whole. pytest for every behaviour change; a new eval case is proven
  deterministic by `plugin/tests/test_eval_cases.py` and measured with 5 runs on the
  default model; a CHANGELOG entry with a consumer-impact line.
- `plugin/README.md` — searched: the configuration table, "Models and effort", spec
  statuses, the `RESULT` contract, "Implementation and review" and the metrics format
  are the documentation this spec changes.

## Scope

- **Groups in PLAN.md.** `## Steps` is divided into groups under a level-3 heading per
  group, `### Group N — <name>` (Polish `### Grupa N — <nazwa>`), with both literals in
  the section map and in both PLAN templates. Steps keep one numbering across
  groups.
- **The planner always marks groups**, whether chunking is on or off. A group is a
  coherent part of the change that ends on a green, committable state. A plan that is small
  by the planner's judgement is one group, because every chunk pays its cache writes again.
  The skill gives a rule of thumb for this but no numeric threshold.
- **The plan review checks the groups:** every step belongs to exactly one group, no group
  boundary leaves work half done for a later group to finish, and a small plan is one
  group. It fixes the grouping in place, like any other plan defect. A plan without
  groups gets them from the review.
- **The switch:** `"implement": {"chunked": true}` in `.claude/workflow.json`, off when missing. A value that is not a boolean warns
  and counts as off. It is validated like the other sections.
- **The implementer in chunk mode** reads the switch itself, from the configuration. With chunking on and a PLAN with more than one group, it carries out the
  group that holds the first unticked step. After that group's last step is green, ticked
  and committed, it writes the chunk note, commits and pushes, and ends with status
  `plan-approved`. The chunk that holds the last group runs the rest of the plan, the
  converge pass with the steps it adds, and the Definition of Done, as it does today.
  Chunking off, or a PLAN with one group or none → one context, as today.
- **The chunk note** goes in a new PLAN section, `## Chunk notes` (Polish
  `## Notatki chunków`, in the section map and both templates). Each chunk
  appends one entry: the group it carried out, decisions taken within the plan's
  latitude, traps met that the next group will meet too, and the running total of
  `implement_iterations`. Deviations stay in `## Deviations`.
- **`ship` loops over the chunks:** a `DONE` from the implementer with `STATUS:
  plan-approved` means that a chunk ended, so `ship` starts a new implementer with the
  same prompt. Every chunk's `RESULT` carries a `CHUNK: <group>/<groups>` line. When a chunk returns without progress (the same group as the chunk before
  it), `ship` handles it like a missing RESULT: it re-runs once, then escalates. An escalation inside a chunk goes through the Result protocol as today, and
  the agent started after the owner's decision is a chunk too.
- **Metrics:** the final chunk writes `implement_iterations` as the running total from
  the chunk notes plus its own. A new optional key, `implement_chunks`, holds the number
  of groups carried out as separate chunks, written only in chunk mode. It is
  never required by `--check`, and the report shows it as a column.
- **The standalone `/pipeline:implement`** follows the same switch: in chunk mode it stops
  at the group boundary and tells the owner to run it again after `/clear`.
- **An eval case** `implement-stops-at-group-boundary`: a fixture with
  chunking on and a two-group plan. The run carries out group 1, stops at its boundary with
  a chunk note, keeps status `plan-approved` and says so in its final message. Measured
  with 5 runs per the eval cost policy.
- **Release:** part of 0.8.0 (not yet tagged): a CHANGELOG entry under 0.8.0 with the
  consumer impact, the README (configuration table, mechanics, `RESULT` contract,
  metrics), and `docs/DECISIONS.md` rows.

## Out of scope

- Turning chunking on by default, and the measured defaults: after the Stage 7 comparison
  (roadmap item "Before/after comparison").
- Chunking by a step count, or a numeric threshold in the configuration. The owner chose
  planner groups and judgement, and the numeric variant stays in "Decisions and rejected
  alternatives".
- Chunking any other stage (the final review's perspectives already run as separate
  subagents).
- Cost per chunk as metric keys: the transcripts and the stdout of `--record-cost` keep
  the detail, and the spec records only the stage total.
- Cheaper eval runs (`scripts/`): a separate Stage 7 item, as a fast path or a spec of its
  own.

## Requirements and acceptance criteria

PLAN format

- [ ] AC1: `plugin/templates/sections.md` has the keys `step-group` (`### Grupa N — ` /
      `### Group N — `) and `chunk-notes` (`## Notatki chunków` / `## Chunk notes`), and
      `PLAN.en.md` and `PLAN.pl.md` carry exactly those literals: the group heading inside
      `## Steps` and `## Chunk notes` as a section. The existing template-to-map
      consistency test covers them.
- [ ] AC2: the `plan` skill tells the planner to divide `## Steps` into groups whenever
      the plan is written, whatever the switch says. A group ends on a green, committable
      state; a small plan is one group because each chunk pays its cache writes again;
      step numbers run through the whole plan. The skill states a rule of thumb, not a
      configured threshold. Pinned with pytest on the text.
- [ ] AC3: the `plan-review` skill checks that every step is in exactly one group, that
      no group boundary leaves work for a later group to finish, and that a small plan is
      one group, and it fixes a violation in place. A plan without groups gets them.
      Pinned with pytest on the text.

Configuration

- [ ] AC4: `workflow_config.py` accepts `"implement": {"chunked": true|false}`. A missing
      section means off. An unknown key in `implement`, or a non-boolean `chunked`, gives a
      configuration warning and off, never a block. Tested in `plugin/tests`.
- [ ] AC5: `templates/workflow.example.json` and the README configuration table show the
      key, off by default, and say it is a Stage 7 candidate not yet measured.
      `/pipeline:init` does not write it.

The implementer

- [ ] AC6: the `implement` skill (and the `implementer` agent) says: with chunking on and
      more than one group in PLAN.md, carry out the group that holds the first unticked
      step. After its last step is green, ticked and committed, append an entry to
      `## Chunk notes`, commit, push, and end with status `plan-approved`. A chunk never
      ends on a red or uncommitted step. Pinned with pytest on the text.
- [ ] AC7: the chunk holding the last group runs its steps, then the converge pass, the
      steps the pass adds and the Definition of Done, exactly as a single context does
      today. The existing converge-resume rules apply unchanged. Pinned with pytest on the
      text.
- [ ] AC8: chunking off, or a PLAN with one group or none → the skill runs the whole plan
      in one context. The behaviour and the metrics are those of 0.7.0, with no
      `## Chunk notes` entry and no `implement_chunks`. Pinned with pytest on the text.
- [ ] AC9: a chunk note holds the group carried out, decisions taken within the plan's
      latitude, traps the next group will meet, and the running `implement_iterations`
      total. A new chunk reads `## Chunk notes` before it starts. Pinned with pytest on the
      text.
- [ ] AC10: run standalone in chunk mode, `/pipeline:implement` stops at the group
      boundary and its Handoff tells the owner to run it again after `/clear`. Pinned with
      pytest on the text.
- [ ] AC11: eval case `implement-stops-at-group-boundary`, a fixture with
      `"implement": {"chunked": true}` and a two-group PLAN whose steps are green and
      small. The run ticks and commits every step of group 1 and no step of group 2,
      writes a `## Chunk notes` entry, leaves `status: plan-approved`, and its final
      message says the chunk ended at the group boundary. `test_eval_cases.py` proves the
      fixture deterministic, and the case passes 5 of 5 runs on the default model (or
      gets `runs: 3` at 4 of 5, per the eval cost policy).

The orchestrator

- [ ] AC12: `ship`'s state table and Result protocol say: `implementer` → `DONE` with
      `STATUS: plan-approved` = a chunk ended, start the next implementer with the same
      prompt. `STATUS: implemented` = the stage is done. Pinned with pytest on the text.
- [ ] AC13: the implementer's RESULT in chunk mode has a `CHUNK: <group>/<groups>` line.
      A chunk reporting the same group as the chunk before it is treated as a missing
      RESULT: one re-run, then an escalation described to the owner. The README's
      `RESULT` contract documents the line. Pinned with pytest on the texts.

Metrics

- [ ] AC14: `implement_chunks` is a known integer counter in `workflow_metrics.py`,
      required by `--check` at no status, and shown as a report column (`-` when
      missing). The final chunk writes it and writes `implement_iterations` as the running
      total over all chunks. Tested in `plugin/tests` for the script, and with pytest on
      the skill text for the writing rule.
- [ ] AC15: `--record-cost` over a fixture with three `implementer` subagents of one spec
      (three chunks) writes `cost_implement_cents` equal to their sum. The test pins what
      already works, so that chunking cannot break it later.

Release

- [ ] AC16: `plugin/CHANGELOG.md` → `## 0.8.0` describes the chunked implementer with the
      consumer impact (off by default; plans written by 0.8.0 carry groups, which older
      skills ignore as ordinary headings), the version stays `0.8.0`, `docs/ROADMAP.md`
      ticks the item, `docs/DECISIONS.md` records the decisions below, and
      `bash scripts/check.sh` is green.

## Decisions and rejected alternatives

| Decision | Rejected alternatives | Rationale |
|----------|-----------------------|-----------|
| Chunk boundaries are groups the planner marks in PLAN.md | a step count K from the configuration, split evenly; a fixed K plus a separate threshold key | The owner's choice: a group ends at a coherent boundary of the change, not at an arbitrary step, and the planner already knows that boundary |
| The planner always marks groups, and a switch in the configuration turns chunking on | groups only when the switch is on; chunking on by default | Chunking can then be turned on for a spec whose plan is already written, and plans look the same in the before and after runs of the comparison. Off by default until the comparison measures it no worse (roadmap) |
| A small plan is one group, by the planner's judgement with a rule of thumb | a numeric threshold in the configuration | Plan depth follows the change by judgement, with no size thresholds (SPEC 010, `docs/DECISIONS.md`). A threshold is a tier by another name |
| The converge pass, the steps it adds and the Definition of Done run in the chunk with the last group | counting added steps toward the chunk, which could start another chunk | This keeps "the converge pass and the Definition of Done run as today" (roadmap), and the existing converge-resume rules cover an interruption |
| The implementer reads the switch from the configuration, and `ship` only loops on `plan-approved` | `ship` passes a chunk mode or a step range in the prompt | One source of truth, and the standalone skill and the eval case behave like `ship` without a special prompt |
| Running counters go in the chunk note, and the final chunk writes the metrics | each chunk updating `metrics:` in SPEC.md | The metrics stay written once, at `implemented`, as `--check` expects; the note is where the next chunk looks anyway |
| One eval case for the group boundary | pytest only | Stopping at the boundary with a note and `plan-approved` is model behaviour that pytest on the text cannot show, and the whole Stage 7 comparison relies on it |
| Shipped in 0.8.0 | 0.9.0 after tagging 0.8.0 | 0.8.0 is not tagged: one canary and one eval receipt cover both specs |

## Owner decisions

- 2026-09-24 — scope: the chunked implementer only. Cheaper eval runs are a separate item.
- 2026-09-24 — chunk boundaries: groups the planner marks in PLAN.md.
- 2026-09-24 — the converge pass, the steps it adds and the Definition of Done run in the
  chunk with the last group.
- 2026-09-24 — one eval case for the new behaviour, measured per the eval cost policy.
- 2026-09-24 — the planner always marks groups, and a configuration key turns chunking on
  (off by default).
- 2026-09-24 — a small plan is one group, by the planner's judgement with a rule of thumb
  in the skill. No numeric threshold.
- 2026-09-24 — release: 0.8.0.
- 2026-09-24 — accepted: the group and chunk-note literals, the `implement.chunked`
  switch, the implementer reading it itself, the standalone stop, the `CHUNK:` line with
  its no-progress rule, the optional `implement_chunks` key, groups added by the plan
  review, and the eval case name.
- New dependency: none. Data migration: none (existing PLAN.md files without groups run
  in one context).

## Open questions (non-blocking)

- The rule of thumb for a group's size (how many steps, or how much context, before a
  split pays for its cache writes): the planner's wording, then corrected by the Stage 7
  comparison.
