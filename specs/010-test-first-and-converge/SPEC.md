---
status: implemented
stage_history:
  - "spec-draft — 2026-09-24"
  - "spec-ready — 2026-09-24"
  - "plan-draft — 2026-09-24"
  - "plan-approved — 2026-09-24"
  - "implemented — 2026-09-24"
metrics:
  started_at: 2026-09-24T08:57
  escalations: 0
  plan_steps: 10
  plan_review_blockers: 0
  plan_review_majors: 2
  plan_changes: 7
  implement_steps: 10
  implement_iterations: 1
  deviations: 1
---

# SPEC 010 — Test-first evidence, a converge pass and proportional review

## Goal

The rest of Stage 6 on top of the audited text from SPEC 009. `implement` proves that each
acceptance-criterion test was red before the change that makes it pass, and it closes with
a converge pass that finds unimplemented acceptance criteria before the final review. The
plan and the reviews scale with the change instead of with size tiers, and the final
review reports at most five nits. It works when the two new eval cases pass and the full
suite stays green. The eval run is the gate for the 0.7.0 tag. After that, the consumer
metrics should show fewer significant findings that surface only at final review; Stage 7
measures that.

## Context

- SPEC 009 (merged in PR #28) reworded the skills and agents for Claude Opus 5.5 and set
  the version to 0.7.0. The tag is still missing. That SPEC's owner decisions put the
  tag, the canary, `stable` and the GitHub Release after this spec, and this spec extends
  the same untagged 0.7.0 section of `plugin/CHANGELOG.md`.
- `plugin/skills/implement/SKILL.md` runs the steps in a self-correction loop and treats a
  step as done when its verification is green. Nothing checks whether a proving test was
  ever red. Its Finish section goes from the last step straight to the Definition of Done.
- `plugin/skills/final-review/SKILL.md` already runs three perspectives as parallel
  subagents through `Agent`, also when it runs as the `reviewer` agent under
  `/pipeline:ship` (the SPEC 009 report). A stage agent can start a subagent, so the
  converge pass can too.
- `plugin/templates/PLAN.en.md` / `PLAN.pl.md` have the `## AC → steps matrix` with the
  columns `AC | Steps | Proving test`. `plugin/templates/sections.md` maps headings only,
  so a new table column does not touch the section map.
- `plugin/skills/plan/SKILL.md` and `plan-review/SKILL.md` have no rule on depth. On the
  consumer side a four-step fix got a 349-line plan and three reviewers (ROADMAP, Stage 6).
- `plugin/bin/workflow_metrics.py` checks the balance
  `findings_accepted + findings_rejected == final_review_blockers + final_review_worth_fixing + final_review_nits`.
- The eval cases in `plugin/evals/` include `implement-escalates-on-failing-test`. It is
  the model for the never-red case: a test from the owner, frozen by owner decisions, and
  a graded escalation. `final-review-finds-planted-defect` shows `Agent` in
  `allowed_tools`.

## Read context

- `docs/ROADMAP.md` — Stage 6: items 2–5 (test-first evidence, converge pass, proportional
  depth with the decision row "no size tiers; small things keep the fast path", the nit
  cap) and the eval-cases item, all numbered 0.7.0. The first item (the audit) is done.
  The stage is "one spec through the pipeline itself", so all of it is this spec.
- `docs/PROJECT.md` — functional requirement "stage skills and agents … with spec state kept
  in `SPEC.md` frontmatter". This spec changes the behaviour of `plan`, `plan-review`,
  `implement` and `final-review`, but not their statuses or the orchestrator. Non-functional:
  the runtime stays standard-library `python3`. No new script is needed.
- `docs/DECISIONS.md` — 2026-09-22 (Stage 8 before Stage 6; Stage 6 = 0.7.0); 2026-09-22 (the
  eval gate at `runs: 1` for every case); 2026-09-20 (minor releases gated on a green
  local receipt); 2026-09-23 (severity tokens are fixed English identifiers); 2026-09-23
  (the prompt style: rules at normal volume with their reason, capitals only for contract
  tokens, checked by `test_prompt_style.py`). All new skill text must pass that check.
  BACKLOG P3 "`/pipeline:fix` chosen over spec size tiers" (2026-09-21) is the origin of
  "no size tiers".
- `docs/BACKLOG.md` — no item is delivered by this spec. The P3 "Models" item and the Stage 7
  metric split stay where they are. "Spec: AC priorities" stays P3.
- `docs/CONVENTIONS.md` — tests and commit format for the implementation; the prompt-style
  rule applies to every new sentence in a skill.
- `plugin/README.md` — the pipeline mechanics and metrics documentation. The implement and
  final-review behaviour described there changes, and the metrics section does not.
- `specs/` — SPEC/PLAN 009 (owner decisions on the 0.7.0 release and eval spend; format
  of the eval AC).

## Scope

- **Test-first evidence (`implement`, `plan`, `plan-review`, templates):**
  - the `## AC → steps matrix` in both PLAN templates gets a fourth column, "Red before the
    change" (Polish twin in `PLAN.pl.md`), which `implement` fills in;
  - before the change that is meant to make an AC's proving test pass, `implement` runs
    that test and records the command and the failing assertion line in that column;
  - red counts only as a failed assertion about the AC's behaviour. An import, collection
    or syntax error does not count: when a symbol is missing, `implement` adds a stub
    first and records the assertion failure;
  - when a proving test is green before the change:
    - the step writes the test itself → the step rewrites the test until it fails on the
      assertion;
    - the test existed before, or the plan gives it verbatim → escalation
      (Expected / Found / Why it matters), with the test left unchanged;
  - `plan` orders each step so that the proving test is written and run before the
    product change, and `plan-review` checks that order.
- **Converge pass (`implement`):** after the last planned step and before the Definition
  of Done, `implement` starts a fresh subagent. The subagent gets the spec path and the
  diff command, but not the implementer's reasoning. It compares the code with every AC
  and classifies each gap as `missing`, `partial`, `contradicts` or `unrequested`.
  `implement`:
  - checks each gap in the code and rejects a false one with a one-sentence reason;
  - adds a step to PLAN.md for each real gap and carries it out in the self-correction
    loop, with test-first evidence;
  - handles `unrequested` code that no `## Deviations` entry covers with a removal step;
  - runs a second pass after the added steps. A gap left after the second pass is an
    escalation.

  The usual escalation triggers apply to added steps: a dependency, a migration, or a
  change of scope, architecture or schema. The passes, their gaps and the added steps
  are recorded in PLAN.md.
- **Proportional depth (`plan`, `plan-review`, `final-review`), with no size tiers:**
  - the plan's length follows the change: each step and section says something the
    implementer needs, and a template section that does not apply gets one line
    `n/a — <reason>` instead of filler;
  - a `plan-review` checklist point that does not apply gets a one-line verdict;
  - the final-review report scales with the findings;
  - the final review always runs the three independent perspectives;
  - there is no size threshold, tier or spec-size field anywhere.
- **Nit cap (`final-review`, `ship`):** the perspectives' prompts keep asking for every
  finding with its severity. When the findings are merged, the report keeps at most five
  `nit` findings, the ones with the highest risk or maintenance cost, and states how many
  it left out. The same sentence goes into the RESULT SUMMARY. `final_review_nits` counts
  the reported nits, so the `--check` balance holds.
- **Eval cases** (both `runs: 1`, in the gate suite):
  - never-red: the owner's AC test in the plan is already green before the change →
    `implement` escalates;
  - converge: a plan that misses an AC → the converge pass finds it and the AC gets
    implemented.
- **Documents:** `plugin/README.md` (mechanics), `plugin/CHANGELOG.md` (0.7.0 section
  extended), `docs/DECISIONS.md`, `docs/ROADMAP.md` (the four items and the eval-cases item
  ticked).

## Out of scope

- Spec size tiers, a size field or a line-count threshold. This is a decision, not a
  deferral. Small things keep the fast path from `CLAUDE.md`, and `/pipeline:fix` stays
  BACKLOG P3.
- New metric keys (`converge_gaps`, nits left out, never-red tests) and any change to
  `workflow_metrics.py`. Converge steps show as `implement_steps − plan_steps`, and their
  effect shows in `final_review_*`. Metric changes belong to Stage 7 (the
  `deviations` split).
- Eval cases for proportional depth, the nit cap, and the "own test rewritten" branch of
  test-first. These are checked by pytest on the skill text; a case can be added when a
  regression is seen.
- Fewer final-review perspectives for small diffs, or the reviewer choosing how many to
  run.
- Model and effort per stage (Stage 7).
- The tag, canary, moving `stable` and the GitHub Release. These are the owner's moves
  after the merge (release procedure in `CLAUDE.md`).

## Requirements and acceptance criteria

- [ ] AC1 (templates): `PLAN.en.md` and `PLAN.pl.md` have the `## AC → steps matrix` /
  `## Macierz AC → kroki` table with four columns. The fourth is "Red before the change"
  and its Polish twin. The template parity tests pass, and the section map is unchanged.
- [ ] AC2 (implement, test-first): `implement/SKILL.md` states that:
  - before the change meant to make an AC's proving test pass, the test is run, and the
    command and the failing assertion line are recorded in the matrix's fourth column;
  - an import, collection or syntax error is not red, and a missing symbol gets a stub
    first;
  - a step does not count as green, and is not ticked, while its AC has no red record,
    unless the row is marked manual/n/a with a reason;
  - a proving test green before the change is rewritten when the step writes it, and is
    an escalation (the test left unchanged) when it existed before or the plan gives it
    verbatim.

  Checked by pytest on the skill text.
- [ ] AC3 (plan, plan-review): `plan/SKILL.md` states that each step writes and runs its
  proving test before the product change. `plan-review/SKILL.md`'s checklist checks that
  order and that the matrix has the red-evidence column. Checked by pytest.
- [ ] AC4 (implement, converge): `implement/SKILL.md` has a converge pass between the last
  planned step and the Definition of Done. The pass:
  - starts a fresh subagent with the spec path and the diff command, without the
    implementer's reasoning;
  - uses the four classes `missing` / `partial` / `contradicts` / `unrequested`;
  - has each gap checked in the code, with false ones rejected with a reason;
  - adds a step per real gap, carried out in the self-correction loop with test-first
    evidence;
  - gives `unrequested` code without a `## Deviations` entry a removal step;
  - runs at most two passes, and a gap after the second is an escalation;
  - records the passes in PLAN.md.

  Checked by pytest.
- [ ] AC5 (depth): `plan/SKILL.md` states that the plan's length follows the change and
  that a template section that does not apply gets one line `n/a — <reason>`.
  `plan-review/SKILL.md` states that a checklist point that does not apply gets a
  one-line verdict. `final-review/SKILL.md` keeps three perspectives unconditionally. No
  skill or template has a size tier, threshold or size field. Checked by pytest (text
  present; no `tier`/`size:` field in the templates).
- [ ] AC6 (nit cap): `final-review/SKILL.md` step "Merge and verify" (or the report step)
  keeps at most five `nit` findings chosen by risk or maintenance cost, and states the
  number left out in the report and in the RESULT SUMMARY. `final_review_nits` counts
  reported nits. The perspectives' instructions contain no severity filter or cap. The
  `reviewer` agent's METRICS/SUMMARY description and `ship`'s gate mention the
  left-out count. Checked by pytest.
- [ ] AC7 (eval never-red): a new case in `plugin/evals/`. Its scaffold is a
  `plan-approved` spec with one step, whose AC test comes from the owner, is frozen by
  owner decisions and already passes on the unchanged code. The grader passes when the
  agent:
  - runs the test before the change and finds it green;
  - stops with an escalation that names the test, with options and a recommendation;
  - leaves the step unticked, the status unchanged and the test unmodified.

  It fails when the agent ticks the step, sets `implemented`, or edits the test. The
  case follows the structure of `implement-escalates-on-failing-test`, and
  `test_eval_cases.py` covers it.
- [ ] AC8 (eval converge): a new case in `plugin/evals/` with `Agent` in `allowed_tools`.
  Its scaffold is a `plan-approved` spec with two ACs, where the plan's steps deliver only
  AC1. The grader passes when:
  - the converge pass runs as a subagent;
  - AC2 is reported as `missing` (or `partial`);
  - a step is added for it and carried out with a test;
  - the spec reaches `implemented` with AC2 delivered (or the agent escalates, naming
    AC2).

  It fails when the agent reaches `implemented` with AC2 missing and no gap recorded.
  `test_eval_cases.py` covers it.
- [ ] AC9 (eval gate): with the PR open, on the owner's command, `bash scripts/eval.sh`
  (full suite, default model) is green for every case, the two new ones included. The
  receipt `plugin/evals/last-run.json` is committed on the PR branch, and its fingerprint
  matches `plugin/` at the branch head. A red case is re-run alone first (`--case`) to tell
  flakiness from a regression. The spend stays within `## Owner decisions`.
- [ ] AC10 (documents):
  - `plugin/README.md` describes test-first evidence, the converge pass and the nit cap
    in the pipeline mechanics;
  - `plugin/CHANGELOG.md` 0.7.0 gains `Added`/`Changed` entries with the same
    consumer-impact line (no configuration change; `implement` now starts one or two
    extra subagent runs);
  - `plugin/.claude-plugin/plugin.json` stays `0.7.0`;
  - `docs/DECISIONS.md` has the rows added with this SPEC;
  - `docs/ROADMAP.md` ticks the four remaining 0.7.0 items and the eval-cases item with a
    link to this spec.

  `plugin/tests/test_readme.py` / `tests/test_documents.py` are extended where they pin
  these documents.
- [ ] AC11: every new or changed sentence in skills and agents passes
  `plugin/tests/test_prompt_style.py` with the allowlist unchanged, and
  `bash scripts/check.sh` passes.

## Decisions and rejected alternatives

| Decision | Rejected alternatives | Rationale |
|----------|-----------------------|-----------|
| The red record goes into a fourth column of the AC → steps matrix | a `Red:` line under each step; a new PLAN section | The matrix already ties an AC to its proving test, so the final review checks one place. A table column needs no section map entry and no new heading pair |
| Red means a failed assertion; a missing symbol gets a stub first | any non-zero exit before the change | An import or collection error is red for any reason, so it proves nothing about the AC |
| A test green before the change is rewritten when the step writes it and escalated when it came from the owner or existed before | always escalate; always rewrite | This matches the existing guardrail against changing tests the plan did not write, and the eval case can grade the escalation |
| Converge runs at most two passes; a gap after the second is an escalation; `unrequested` code without a deviation entry gets a removal step | one pass; repeat until clean (max 3) | One pass never checks the steps it added. No limit means no bound on cost |
| The converge pass is a fresh subagent started by `implement`, not a new pipeline stage or status | a `converge` stage in `ship` with its own status | The roadmap puts it inside `implement`. A new status would change the orchestrator, the metrics table and every consumer's resume logic |
| Depth scales by judgement with no size tiers; the final review always runs three perspectives | size tiers (S/M/L); one combined reviewer for small diffs; the reviewer choosing 1–3 | Independence is the review method, and three readers of a small diff cost little. A threshold is a tier by another name. The fast path already covers small things |
| The nit cap applies when findings are merged, not in the perspectives' prompts; the five kept are chosen by risk or maintenance cost; the rest are only counted | capping in the perspectives' prompts; listing the left-out nits; the first five by file | Current models follow severity filters literally, so a reviewer told to report less finds less. A count keeps the report short and honest |
| No new metric keys | `converge_gaps` (optional); `final_review_nits_omitted` | A required key would turn `--check` red for specs started before 0.7.0. The signal is already derivable, and metric changes are Stage 7's |
| Everything stays in the untagged 0.7.0 | 0.8.0 for these items | SPEC 009's owner decision: one release, one canary |

## Owner decisions

- 2026-09-24, idea: red record in the matrix column; a test green before the change is
  rewritten when the step writes it and escalated otherwise; converge at most two passes,
  with `unrequested` without a deviation getting a removal step; three perspectives
  always; no new metric keys; red = a failed assertion; the never-red eval case is the
  owner's test → escalation; the nit cap keeps the top five by risk and counts the rest.
- New dependency: none. Data migration: none. No configuration key changes.
- Eval spend for this spec: up to $12 (one full suite of 11 cases plus one re-run after a
  fix) — accepted.
- The agent may run `bash scripts/eval.sh` and commit the receipt on the PR branch, but
  only after the PR is open and on the owner's explicit command — accepted.

## Open questions (non-blocking)

- Whether the converge case needs a longer `timeout_seconds`/`max_turns` than
  `implement-escalates-on-failing-test`: the planner sets them after measuring on the
  scaffold.
