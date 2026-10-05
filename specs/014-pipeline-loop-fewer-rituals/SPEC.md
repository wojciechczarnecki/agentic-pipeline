---
status: implemented
stage_history:
  - "spec-draft — 2026-10-05"
  - "spec-ready — 2026-10-05"
  - "plan-draft — 2026-10-05"
  - "plan-approved — 2026-10-05"
  - "implemented — 2026-10-05"
metrics:
  started_at: 2026-10-05T12:48
  escalations: 0
  plan_steps: 17
  plan_review_blockers: 0
  plan_review_majors: 4
  plan_changes: 7
  implement_steps: 17
  implement_iterations: 13
  deviations_minor: 9
  deviations_major: 0
  escalations_permission: 0
  escalations_tooling: 0
  final_review_blockers: 1
  final_review_worth_fixing: 10
  final_review_nits: 5
  findings_accepted: 16
  findings_rejected: 0
---

# SPEC 014 — Fewer rituals, more code in the pipeline loop

## Goal

The first public consumer ran nine specs on 0.8.1 (implementer on Sonnet 5.5). The evidence
shows rituals that cost tokens and produced paperwork findings instead of catching defects:
the converge pass, the red-record column and the chunked implementer. It also shows
bookkeeping that an agent lost or a tool blocked: metrics dropped on an escalated stage,
escalations about tools counted as design questions, and a closing commit that took a whole
reviewer run. This spec removes the three rituals and moves the bookkeeping into code. It
also lets the implementer install accepted dependencies without help, and makes the final
review report say when its perspectives were not independent. Release: 0.9.0.

Success: a spec run on 0.9.0 has no converge pass, red column or chunk notes. Its counters
can be derived again from the spec files after any escalation. `--check` catches an AC
missing from the matrix and a manual scenario with no pass condition. Escalations are split
by kind. The spec closes with one script call that can be resumed alone. Every spec recorded
before 0.9.0 still passes `--check`.

## Context

Evidence (the consumer repository, `specs/001-…009-*/PLAN.md`, read only):

- **Converge pass:** it ran in all nine specs, and in 008 and 009 without the `Agent` tool,
  as a self-review. It reported gaps in 001, 004, 005, 006 and 007, and the implementer
  rejected every one (`converge_gaps: 0` everywhere, also in this repository's 013). The
  final review of the same specs still found 5–14 `worth-fixing` findings.
- **Red records:** in 009 the column holds `(stub …)` reds, recorded after the code was
  written and then stubbed out. The empty or partial column became the final-review findings
  004 F13 and 007 F5. The defect a red record should have caught (a test that passes with
  the code stubbed out) was found by the final review's tests perspective, which broke the
  code: 004 F8.
- **Spec 005:** four escalations. Two were the auto-mode classifier refusing a chained
  `uv lock` / `uv sync` call; after the second, the owner ran step 3 by hand. One was a
  closing commit the classifier never answered, which cost a whole reviewer `apply` run.
  Only one (the AC17 fallback model) was a design decision. The implement stage ran as four
  agents, and its counts were lost. AC22, a manual scenario, says what to run but not how the
  owner sees that it passed.
- **Chunked implementer:** Stage 7 measured about 25% more per plan step (80 against 64
  cents) with no fewer iterations or findings (`docs/DECISIONS.md`, 2026-10-05). The
  consumer's `.claude/workflow.json` still has `"implement": {"chunked": false}`.

The code this spec changes:

- `plugin/skills/implement/SKILL.md`: the Test-first evidence, Converge pass and Chunk mode
  sections, and Procedure steps 1, 2, 5 and 6.
- `plugin/skills/ship/SKILL.md`: the State table, the RESULT contract (`CHUNK:`), the Result
  protocol (chunks, third-time STOP), the escalation triggers and Closing.
- `plugin/skills/plan/SKILL.md` (Step groups, the fourth column), `plugin/skills/plan-review/SKILL.md`
  (grouping and fourth-column checks) and `plugin/skills/final-review/SKILL.md` (the red
  record check in the compliance perspective, Apply step 5 closing).
- `plugin/agents/*.md`: the RESULT block with `CHUNK:`, and the implementer's chunk rules.
- `plugin/bin/workflow_metrics.py`: `COUNTERS`, `REQUIRED`, `check()`, `render()`; the cost
  lines; `--record-cost`. `plugin/bin/workflow_config.py`: `SCHEMA` and `defaults()` with
  `implement.chunked`.
- `plugin/templates/PLAN.{en,pl}.md` (the fourth column, `### Group N`, `## Chunk notes`),
  `plugin/templates/sections.md`, `plugin/templates/workflow.example.json` and
  `plugin/skills/init/SKILL.md` (the sentence on the `implement` section).
- `plugin/README.md`: configuration, the RESULT contract, the triggers, Implementation and
  review, Workflow metrics.
- Eval cases `implement-converge-finds-missing-ac`, `implement-escalates-on-never-red-test`
  and `implement-stops-at-group-boundary`, the case mapping in `scripts/eval_receipt.py`,
  and the tests `test_converge.py`, `test_test_first.py`, `test_chunked_implementer.py` and
  the assertions on these features in the other test files.

## Read context

- `docs/ROADMAP.md`: read in full. Stage 10, item "0.9.0, one spec — fewer rituals, more
  code in the pipeline loop", is the scope of this spec, bullet by bullet. The 0.10.0 item
  (bootstrapping and the guard) is a separate spec and stays out.
- `docs/PROJECT.md`: read in full. The functional requirement "workflow metrics report
  across specs" and the non-functional "runtime on plain `python3`" apply: `--derive` and
  `--close` use the standard library and call `git` and `gh` as subprocesses.
- `docs/DECISIONS.md`: searched for "converge", "red", "test-first", "chunk", "metrics",
  "escalat", "dependency", "close", "Agent". The 2026-10-05 row is this spec's rationale;
  the rows that introduced the converge pass and test-first (SPEC 010) and chunking
  (SPEC 012) are superseded by it.
- `docs/BACKLOG.md`: read in full. Two P2 items name 0.9.0 as their trigger: calling
  `workflow_metrics.py` by name, and the lower-bound label on cost. The P3 item on stages
  without the `Agent` tool is limited here to a note in the report.
- `docs/CONVENTIONS.md`: searched for "eval", "canary", "version", "CHANGELOG". A minor
  release needs the eval receipt and the canary before the tag. Both are the owner's.
- `plugin/README.md`: read in full. It is the single source of truth for the mechanics, and
  every change in this spec changes it.

## Scope

- Removal of the converge pass, the red-record column with its Test-first evidence
  procedure, and the chunked implementer, with their eval cases, tests, template sections
  and documentation.
- Test-first stays as one guidance paragraph in `implement`.
- Derived metrics: `workflow_metrics.py --derive <spec-dir>` writes the counters it can read
  from the spec files.
- The spec lint in `--check`.
- Escalations with a kind.
- Dependencies the implementer installs itself.
- The scripted close: `workflow_metrics.py --close <spec-dir>`, run by `ship`.
- The `ship` start message with the model of every stage, and the lower-bound label on cost.
- The final-review report notes when the perspectives ran in one context.
- Version 0.9.0, `plugin/CHANGELOG.md`, `docs/DECISIONS.md` rows, `docs/ROADMAP.md` ticked,
  and the delivered `docs/BACKLOG.md` items removed.

## Out of scope

- Everything in the 0.10.0 item of Stage 10 (bootstrapping and the guard): its own spec.
- Restructuring the final review so the orchestrator starts its perspectives: stays in
  `docs/BACKLOG.md` (P3, trigger unchanged).
- A real fix for undercounted output tokens: stays in `docs/BACKLOG.md` (P2). This spec
  only labels the cost.
- Rewriting or re-deriving the metrics of specs closed before 0.9.0. Their recorded values
  stay as they are.
- New eval cases for the new behaviour. The changes are code (`--derive`, `--close`,
  the lint) proven by pytest, or deletions. The canary run covers the whole loop.

## Requirements and acceptance criteria

Removal

- [ ] AC1: No skill, agent, template, README section or test fixture describes the
  converge pass, the "real gap after the second converge pass" trigger or the
  `converge_gaps` key as current behaviour. The eval case `implement-converge-finds-missing-ac`
  is gone, and `scripts/eval_receipt.py` maps no rule to it. A test fails if the text
  "converge pass" returns to `plugin/skills/` or `plugin/agents/`.
- [ ] AC2: No skill, agent, template or README section describes the "Red before the change"
  column, the Test-first evidence procedure or the stub-to-red rule. The PLAN templates have
  a three-column AC → steps matrix (AC, steps, proving test), and the eval case
  `implement-escalates-on-never-red-test` is gone. The trigger "a proving test … green before
  the change" is gone from `ship` and the README.
- [ ] AC3: `implement` keeps a test-first paragraph as guidance: write the step's proving
  test before the product change and run it. A test that passes before the change either
  does not exercise the AC and is rewritten, or shows that the behaviour already exists,
  which is a gap in the SPEC and escalates under the existing trigger. The final review's
  tests perspective still proves that tests test something by breaking the code they cover.
- [ ] AC4: No skill, agent, template or README section describes chunk mode, the chunk
  protocol, step groups, `## Chunk notes`, the `CHUNK:` RESULT line or the
  `implement_chunks` key as current behaviour. `sections.md` has no `step-group` or
  `chunk-notes` row, and the eval case `implement-stops-at-group-boundary` is gone.
- [ ] AC5: A `.claude/workflow.json` whose `implement` section holds only `chunked` (any
  boolean) passes `workflow_config.py --check` with exit code 0. A notice on stderr says the
  key was retired in 0.9.0, is ignored and can be removed. The guard prints nothing for it.
  Any other key in `implement`, or a non-boolean `chunked`, is still a validation error.
  `/pipeline:init` and `workflow.example.json` no longer write the section.
- [ ] AC6: `--check` passes on every spec in this repository's `specs/` and on copies of
  the consumer's nine specs (test fixtures with their frontmatter), including specs that
  carry `converge_gaps` and `implement_chunks`.

Derived metrics

- [ ] AC7: `workflow_metrics.py --derive <spec-dir>` reads SPEC.md and PLAN.md and writes
  these keys into the `metrics:` block, by the same line edit `--record-cost` uses:
  `plan_steps` (the steps in `## Steps`), `implement_steps` (ticked steps),
  `implement_iterations` (the sum of the iteration notes on ticked steps, AC8),
  `deviations_minor` and `deviations_major` (the entries in `## Deviations`, the major ones by
  a fixed token), `final_review_blockers`, `final_review_worth_fixing` and
  `final_review_nits` (the findings `F<n>` in `## Final review` by severity token),
  `findings_accepted` and `findings_rejected` (the ids in the final-review gate entry of
  `## Owner decisions`), and `escalations`, `escalations_permission` and
  `escalations_tooling` (the escalation entries of `## Owner decisions` in PLAN.md and
  SPEC.md, by kind). It also writes `plan_review_blockers` and `plan_review_majors` (the
  findings in `## Review log` by severity token). Headings are matched in
  both languages through `sections.md`.
- [ ] AC8: A ticked step in PLAN.md carries its iteration count as a fixed note (for
  example `— iterations: 2`), written when the step is ticked. A ticked step without the note
  leaves `implement_iterations` unwritten, and `--derive` names the steps on stderr. A
  missing note never counts as zero.
- [ ] AC9: `--derive` writes only the keys whose source it finds in the expected form. It
  leaves every other key and every other byte of SPEC.md as they were, names each key it
  did not write on stderr, and exits 0. Run twice on the same files, it writes the same
  values, so a stage agent started after an escalation gets back the counts of the agents
  before it.
- [ ] AC10: Every stage skill closes with `workflow_metrics.py --derive <spec-dir>` and then
  `--check`, both called by name through `PATH`. No skill tells an agent to count a key that
  `--derive` writes. Agents still write `plan_changes`, `started_at` (`ship` or `plan`) and
  the cost keys (the script).
- [ ] AC11: The templates and skills give the fixed forms that `--derive` reads: the
  iteration note, the major-deviation token, the finding line in the final review and the
  review log, the gate entry with accepted and rejected ids, and the escalation entry with
  its kind. A test runs `--derive` on a fixture PLAN in each language and checks every key.

Spec lint

- [ ] AC12: For a spec with status `plan-draft`, `plan-approved` or `implemented`, `--check`
  reports every AC of SPEC.md (`AC<n>`) that has no row in PLAN.md's AC → steps matrix,
  naming the ACs. It exits 1.
- [ ] AC13: For the same statuses, `--check` reports every item in PLAN.md's
  `### Manual (performed by the owner)` that has no pass-condition line. The line starts
  with a literal from `sections.md` (`Pass when:` / `Zaliczony, gdy:`) and names a command,
  a query or a place in the UI with the expected result. A section with one line
  `n/a — <reason>` passes. The PLAN templates and `plan` require the line, and `plan-review`
  checks it.
- [ ] AC14: A spec with status `spec-draft`, `spec-ready` or `done` is not linted, so every
  spec closed before 0.9.0 still passes.

Escalations with a kind

- [ ] AC15: An `ESCALATE` RESULT carries a line `KIND: decision | permission | tooling`
  as a separate RESULT key, like `STATUS`. `decision` is a question about the
  product or the plan. `permission` is a tool call refused or left unanswered by a
  permission rule or the auto-mode classifier. `tooling` is a broken tool, environment or
  CI. A RESULT with `ESCALATE` and no valid `KIND:` counts as `decision`.
- [ ] AC16: `ship` records the kind in the `## Owner decisions` entry. Only `decision`
  entries count toward the third escalation of the same stage that stops the pipeline.
  `escalations` stays the total of all kinds. `escalations_permission` and
  `escalations_tooling` are optional keys: `--check` never requires them, and the report
  shows them as columns.

Dependencies

- [ ] AC17: `implement` and the implementer agent say: a dependency that SPEC or PLAN
  `## Owner decisions` accepts is added by the implementer itself. An unaccepted one
  escalates as before. No dependency is added beyond what the change needs. Every
  package-manager command (`uv add`, `uv lock`, `uv sync`, `npm install` and the like) runs
  as its own Bash call, never chained with a file edit or another command.
- [ ] AC18: `plan` writes no step for the owner to perform, and `plan-review` treats such a
  step as a finding it fixes in place (severity `major`). Manual verification by the owner
  in `### Manual` is not a step and stays allowed.

Scripted close

- [ ] AC19: `workflow_metrics.py --close <spec-dir>` refuses to run (exit 1, nothing
  changed) when the current branch is `main`, `master` or a name in `protectedBranches`,
  when the status is not `implemented`, when the working tree is not clean, or when no open
  PR exists for the branch.
- [ ] AC20: Otherwise, in this order, it: records the cost (as `--record-cost`; its
  warnings never stop the close); sets `status: done`, a `stage_history` entry and
  `finished_at`; runs `--derive` and then `--check`, and on red restores SPEC.md and exits
  non-zero without committing; reads the attempt numbers of the PR head's checks; commits
  `docs: close SPEC NNN <slug>` with SPEC.md only; pushes the lane branch without force;
  waits for the checks of the new head; re-runs failed jobs once (`gh run rerun <id>
  --failed`) and waits again. Exit 0 only when the head's checks are green.
- [ ] AC21: A job on the PR head that passed only on a later attempt stops the close before
  the commit, unless `<docs.backlog>` contains that job's name. The script exits with its
  own code, naming the job and the run link.
- [ ] AC22: Every exit other than 0 prints one line that says which step stopped and what
  state is left: committed or not, pushed or not. A second `--close` after a stop that
  committed but did not go green does not commit again. It resumes from the push or the wait.
- [ ] AC23: `final-review` in `apply` mode ends at a PR with green CI and status
  `implemented`. The flaky-retry check and the backlog entry stay there. `ship`'s Closing
  runs `--close` after the reviewer's `apply` returns `DONE`. On a non-zero exit, `ship` asks
  the owner, with "resume the closing step only" (run `--close` again) as the recommended
  option and no new reviewer. Run on its own, `final-review` `apply` runs `--close` as its
  last step. The State table, the README status table and the guardrail "you do not set
  spec statuses" in `ship` are updated to match.
- [ ] AC24: `--close` is tested with `git` against a temporary repository and a remote, and
  with a stub `gh` on `PATH` (green, red then green after a re-run, red twice, a job green
  on attempt 2 with and without a backlog entry, a resume after a stop at the wait).

Reporting

- [ ] AC25: The `ship` start message names the model of every stage (`plan`, `plan-review`,
  `implement`, `final-review`), resolved as `ship` passes it to `Agent`. `inherit` or no
  entry shows as "session model".
- [ ] AC26: The metrics report labels each cost line as a lower bound because output tokens
  are undercounted.
- [ ] AC27: When the stage has no `Agent` tool, the final-review report in PLAN.md and its
  RESULT SUMMARY say in one sentence that the three perspectives ran in one context and are
  not independent.
- [ ] AC28: The report leaves out a counter column when no spec in the directory carries
  that key, so `converge_gaps` and `implement_chunks` show only where old specs have them
 .

Release

- [ ] AC29: `plugin/.claude-plugin/plugin.json` is `0.9.0`, and `plugin/CHANGELOG.md` has a
  `## 0.9.0` section naming every removal and the retired key. `docs/DECISIONS.md` gains
  rows for `--close` setting `done` (moved from the reviewer) and for derived metrics stored
  in the frontmatter. `docs/ROADMAP.md` ticks the item. `docs/BACKLOG.md` loses the P2 item
  on calling `workflow_metrics.py` by name (delivered by AC10), and its
  cost-label item says the label is done and the real fix waits.
- [ ] AC30: `bash scripts/check.sh` is green, including `claude plugin validate --strict`
  for the plugin and the marketplace.

Manual (owner)

- [ ] AC31: Before the tag, the owner runs the canary from `docs/CONVENTIONS.md`: one small
  spec through `/pipeline:ship` in a consumer clone on the working-tree plugin.
  Pass when: the spec reaches `done` with no converge pass, red column or chunk note in its
  PLAN.md; `workflow_metrics.py --check <spec-dir>` exits 0; the `metrics:` block carries
  the keys of AC7; and the PR's last commit is `docs: close SPEC NNN <slug>` with green
  checks (`gh pr checks <nr>`).

## Decisions and rejected alternatives

| Decision | Rejected alternatives | Rationale |
|----------|-----------------------|-----------|
| The "green before the change" trigger is removed and absorbed into "a gap or contradiction in the SPEC" | Keep it for tests the owner or plan gives verbatim; remove it without a trace | Without red records nothing runs the proving test before the change systematically, so the trigger would rarely fire. A test that is green because the behaviour exists is a SPEC gap anyway |
| `implement.chunked` is a retired key: accepted, ignored, a notice on `--check` | A plain unknown key (`--check` exits 1); ignored silently forever | `workflow.json` is a guardrail file only the owner edits, so it should not turn `--check` red. A notice still tells the owner the key can go |
| `--close` (code) sets `done`, run by `ship` after the reviewer's `apply` | The reviewer runs the script; move the close to the backlog | Resuming the close is then one script call, not a new reviewer (005). The cost is recorded after `apply` has finished, and cost and `done` go into one commit and one CI run |
| `--close` is a subcommand of `workflow_metrics.py` | A new script in `bin/` | Every consumer already allows `Bash(workflow_metrics.py *)`, so the call matches an allow rule and the auto-mode classifier is not asked. A new script would need a new rule in every consumer |
| Derived counters are written into the frontmatter by `--derive` | Computed at read time by the report and `--check` | The frontmatter stays the single store. Old specs and the report work unchanged, and after an escalation the next agent derives again from the files |
| The lint covers statuses `plan-draft` to `implemented` | A version marker in the frontmatter | Every existing spec is `done` and keeps passing without a new field to maintain |
| `escalations` stays the total; `escalations_permission` and `escalations_tooling` are optional | `escalations` counts only `decision` | Old specs stay comparable, and the kinds are still visible apart |
| `implement_iterations` comes from a note on each ticked step | The agent keeps writing it | It is the one implementer counter that was lost on escalation. The note is committed with the tick that is already made |

## Owner decisions

Given in the brief for this spec (2026-10-05):

1. The converge pass is removed in full: the step in `implement`, the escalation trigger
   "a real gap left after the second converge pass", the `converge_gaps` metric (old specs
   still pass `--check`) and the eval case `implement-converge-finds-missing-ac`.
2. The red-record column of the AC → steps matrix and the whole Test-first evidence
   procedure are removed, with their eval case. Test-first stays as guidance in `implement`.
   Proof that a test tests something stays with the final review's tests perspective.
3. The chunked implementer is removed in full: chunk mode in `implement`, the chunk
   protocol in `ship`, step groups in `plan` and `plan-review`, the `implement.chunked` key,
   the `implement_chunks` metric and the Chunk notes section in the templates.
4. Dependencies: the implementer adds the ones the SPEC accepted itself. No step is
   performed by the owner. An unaccepted dependency still escalates. Nothing is added
   beyond what the change needs. Every package-manager command is its own Bash call, never
   chained with a file edit.
5. A cloud environment without the `Agent` tool gets only a note in the final-review
   report, with no restructuring (`docs/BACKLOG.md`, P3).

Decided in the `idea` dialogue (2026-10-05):

6. The "green before the change" trigger is removed and absorbed into the SPEC-gap trigger
   (AC2, AC3).
7. `implement.chunked` is a retired key: accepted, ignored, with a notice on `--check`
   (AC5).
8. The close is a script run by `ship`; the reviewer's `apply` ends at a PR with green CI
   (AC19–AC23).
9. The script is `workflow_metrics.py --close`, so the existing allow rule covers it (AC19).
10. Derived counters are written into the frontmatter by `--derive` (AC7–AC10).
11. The spec lint covers statuses `plan-draft` to `implemented`. A manual scenario carries
    a `Pass when:` line (AC12–AC14).
12. `escalations` stays the total, with optional `escalations_permission` and
    `escalations_tooling` (AC16).
13. `implement_iterations` comes from a note on each ticked step (AC8).
14. New dependency: none. Data migration: none.

## Open questions (non-blocking)

- none
