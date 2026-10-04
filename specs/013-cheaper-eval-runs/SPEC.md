---
status: implemented
stage_history:
  - "spec-draft — 2026-10-04"
  - "spec-ready — 2026-10-04"
  - "plan-draft — 2026-10-04"
  - "plan-approved — 2026-10-04"
  - "implemented — 2026-10-04"
metrics:
  started_at: 2026-10-04T23:12
  escalations: 0
  plan_steps: 11
  plan_review_blockers: 0
  plan_review_majors: 3
  plan_changes: 6
  implement_steps: 11
  implement_iterations: 3
  converge_gaps: 0
  deviations_minor: 3
  deviations_major: 0
  final_review_blockers: 0
  final_review_worth_fixing: 7
  final_review_nits: 5
  findings_accepted: 12
  findings_rejected: 0
---

# SPEC 013 — Cheaper eval runs

## Goal

A full eval run costs about $3.5–4.6, and today any failure means the whole suite runs
again. That includes a failure the plugin did not cause: twice between 2026-09-23 and
2026-09-24 the account's session limit failed every remaining case and forced a full
re-run. This spec changes `scripts/` so that only the cases that need it run again.
Results from the same plugin state are merged into the receipt. An infrastructure error
is recorded as an error and does not count as a FAIL. Development runs can pick only the
cases a change touches. Success: after a run cut short by a session limit, re-running only
the errored cases gives a green receipt that the `pre-push` hook accepts for a release
tag, and the merged receipt is the same one a single full run would have written. A real
FAIL still cannot be retried until it passes.

## Context

- `scripts/eval.sh` runs `claude plugin eval plugin/ … --json <raw>` and passes the raw
  result to `scripts/eval_receipt.py write`. That writes `plugin/evals/last-run.json`
  from scratch on every run, including a `--case X` run. Today the receipt records the
  plugin fingerprint (`git ls-tree -r HEAD -- plugin/` without the receipt), the commit,
  the version, the model and, per case, `runs` and `passed`.
- `eval_receipt.py` counts a run as passed only when `score >= 1` and no paid grader was
  skipped. A run the cost ceiling never started counts as failed, and a partial result is
  never green. A case passes by majority.
- In the raw result, an infrastructure error has two forms (measured on the results in
  `plugin/evals/results/`):
  - the run's `error` is set, e.g. `exit 1: You've hit your session limit · resets …`
    (2026-09-23T14:40, every case; 2026-09-24T08:40, the last three cases);
  - the run's `error` is `null`, but the grader's `explanation` reads
    `grader threw: judge call failed: You've hit your session limit …`. The run itself
    finished and only the judge gave no verdict (`init-without-questions`,
    2026-09-24T08:40).

  In both cases `score` is 0, so the receipt reads a failure.
- `scripts/git-hooks/pre-push` checks the receipt for a minor or major release tag. It
  checks that the fingerprint equals the tagged `plugin/`, that every case in the tagged
  suite is present with at least as many runs as its `case.yaml` asks, that the receipt is
  green, and that the model is `default`. It reads the receipt from the working tree.
- `claude plugin eval --case <glob>` takes one name glob (Claude Code 2.1.289). The CLI
  records only the judges' votes, not their reasons.
- Case names start with their subject: `implement-…`, `final-review-…`, `init-…`,
  `plan-review-…`, and `guard-…` for the hooks. The stage agents are `implementer.md`,
  `reviewer.md`, `plan-reviewer.md` and `planner.md`. The `idea`, `plan` and `ship`
  skills have no eval case.
- Tests: `tests/test_release_gate.py` (hook and receipt), fixture
  `tests/fixtures/eval-result.json`.
- An untracked file `pipeline-feedback-2026-09-29.md` in the repository root reports, as a
  separate P1, that `workflow_metrics.py` has no rate for `claude-sonnet-5-5`. That bug is
  outside this spec (see Out of scope).

## Read context

- `docs/ROADMAP.md` — read in full. The item is Stage 7, "Cheaper eval runs, in `scripts/`
  (no plugin version bump)", and it fixes the three parts: merging re-runs while the
  fingerprint is unchanged, an infrastructure error recorded as an error that does not
  trigger the five-run policy, and development runs that pick the changed cases while
  only the release receipt needs the full suite. The comparison item before it is a
  measurement series and does not block this one.
- `docs/PROJECT.md` — read in full. Runtime on plain `python3` and the standard library.
  The eval scripts are repository tooling, not plugin runtime, so nothing here touches
  the consumer.
- `docs/DECISIONS.md` — searched for: `eval`, `receipt`, `fingerprint`, `five`,
  `majority`, `session limit`, `infrastructure`. Binding rows:
  - 2026-09-20: eval runs locally and never in CI, and a minor or major tag is gated on a
    green receipt checked by `pre-push`. The hook compares `plugin/` contents, not shas.
  - 2026-09-22, the measurement policy: 5 runs for a new or failing case; `runs: 1` at
    5 of 5, `runs: 3` at 4 of 5, sharper criteria below that; receipts only on the default
    model; `--max-cost-usd` on every call. A run aborted by the usage limit already
    counted then as "no verdict" and was re-run.
- `docs/BACKLOG.md` — read in full. Two items have a fired trigger and come into scope
  (owner decision): "the clean check in `eval.sh` ignores untracked files under
  `plugin/`" (trigger: the next change to `eval.sh`) and "`pre-push` reads the receipt
  from the working tree" (trigger: the next change to the release gate). The item
  "record the judges' reasons" stays in the backlog, because the CLI does not provide
  them.
- `docs/CONVENTIONS.md` — searched for: `eval`, `receipt`. The "Eval cost policy" and
  "minor or major tag" paragraphs describe the receipt and the policy, and they change
  together with this spec.
- `plugin/README.md` — searched for: `eval`, `receipt`. No match, so the plugin
  documentation does not apply.

## Scope

- Classifying a run as pass, fail or error in `scripts/eval_receipt.py`. An error is a
  known infrastructure failure or a run without a verdict.
- A receipt that keeps a result per case and merges a later run on the same fingerprint
  and model, under the rules in the requirements.
- An `eval.sh` option that re-runs only the cases the receipt records as an error or does
  not have yet.
- An `eval.sh` option that runs only the cases a change touches, measured against the
  merge-base with `origin/main`.
- `eval.sh` refuses to run when `plugin/` has untracked files (backlog item).
- `pre-push` reads the receipt from the tagged commit (backlog item).
- `docs/CONVENTIONS.md` (eval policy and release), `CLAUDE.md` (Commands, if a new
  invocation is shown there), `docs/DECISIONS.md` (a row for the merge and error rules),
  `docs/BACKLOG.md` (remove the two delivered items) and `docs/ROADMAP.md` (tick the item).

## Out of scope

- Any change under `plugin/`, including `case.yaml` metadata, and a plugin version bump.
  The case-to-files mapping lives in `scripts/`.
- The missing rate for `claude-sonnet-5-5` in `workflow_metrics.py`, and the other items
  in `pipeline-feedback-2026-09-29.md`. They go to a separate fast-path fix (a release
  patch), because they block the Stage 7 comparison and do not belong to `scripts/`.
- Recording the judges' reasons. The CLI does not provide them, so the item stays in
  `docs/BACKLOG.md`.
- Concurrency (`-j`): it shortens the time, not the cost, and runs share one rate limit.
- An eval in CI (`docs/DECISIONS.md` 2026-09-20 stands).

## Requirements and acceptance criteria

Classification

- [ ] AC1: A run whose `error` matches a known infrastructure pattern is recorded as
      `error`, not `fail`. The patterns are the session or usage limit, a rate limit or
      429, overloaded or 529, and an API 5xx. The list lives in `scripts/` and each
      pattern has a test.
- [ ] AC2: A run with `error: null` whose grader `explanation` starts with
      `grader threw:` and matches a pattern from AC1 is recorded as `error`. Fixture: the
      `init-without-questions` shape from 2026-09-24T08:40.
- [ ] AC3: A run the cost ceiling never started, and a run whose paid grader was skipped,
      are recorded as `error` (no verdict) instead of today's failure.
- [ ] AC4: Any other non-null `error` is recorded as `fail`, for example a timeout or an
      unknown message. Test: `error: "timeout after 600s"` gives `fail`.
- [ ] AC5: A case with at least one `error` run is not counted as passed. A receipt with
      an `error` case is not green. The summary and the closing message of `eval.sh` list
      the errored cases separately from the failed ones. For errored cases they give the
      re-run command, and for failed cases they say the five-run measurement policy
      applies.

Receipt and merging

- [ ] AC6: The receipt keeps, per case, the number of runs, the passes, the errors and a
      verdict (`pass` / `fail` / `error`). It still keeps `cases_total`, `green`, `model`,
      `plugin_fingerprint`, `plugin_version` and `commit`. The existing `pre-push` checks
      (fingerprint, case count, runs per case, model, green) work on it.
- [ ] AC7: A run whose fingerprint and model equal the receipt's merges per case. Cases
      the run did not include keep their earlier result, and an included case replaces
      its result under AC8. `green` is recomputed from all cases: it is true when every
      case in the suite has the verdict `pass`. Test: receipt A (9 pass, 3 error), then a
      run of those 3 with `pass` gives a green receipt with 12 cases.
- [ ] AC8: A case whose verdict in the receipt is `fail` is replaced only by a run of at
      least 5 runs that passed 5 of 5. A shorter run, or one that did not pass every time,
      leaves `fail` and the merge reports that the policy applies. A case recorded as
      `error`, missing or `pass` is replaced by any run with at least the number of runs
      its `case.yaml` asks, except that a run with the verdict `error` does not replace a
      `pass` (amended by the owner at the final review, 2026-10-04: an infrastructure error
      says nothing about the plugin, so it must not cost an earlier pass).
- [ ] AC9: A run on a different fingerprint or model writes a new receipt with only its
      own cases, as today.
- [ ] AC10: A full suite assembled from several runs on the same fingerprint and the
      default model passes `pre-push` for a minor tag. Test through the hook, like the
      existing ones in `tests/test_release_gate.py`.

Re-running errors

- [ ] AC11: The re-run option of `eval.sh` runs only the cases whose verdict in the
      receipt is `error`, plus the cases of the suite missing from the receipt. It merges
      the result under AC7. It refuses with a message when the current fingerprint or
      model differs from the receipt's, and it says "nothing to re-run" when there is no
      such case. A `fail` case is not selected.

Changed cases

- [ ] AC12: The changed-cases option of `eval.sh` selects cases from
      `git diff --name-only $(git merge-base HEAD origin/main) HEAD -- plugin/`. The full
      suite stays the default, without the option.
- [ ] AC13: Mapping, defined in `scripts/` and covered by a test for every rule:
      - the case's own directory `plugin/evals/<case>/` selects that case;
      - `plugin/skills/<stage>/` selects the cases with the prefix `<stage>-`, with the
        agents `implementer.md` → `implement-`, `reviewer.md` → `final-review-` and
        `plan-reviewer.md` → `plan-review-`;
      - `plugin/hooks/` selects `guard-`;
      - a change under `plugin/bin/`, `plugin/templates/`, `plugin/.claude-plugin/` or in
        another path not listed here selects every case;
      - `plugin/README.md`, `plugin/CHANGELOG.md`, `plugin/docs/`, `plugin/tests/`,
        `plugin/evals/last-run.json`, the skills `idea`, `plan` and `ship` and
        `planner.md` select none.
- [ ] AC14: A test checks that every case in `plugin/evals/` maps to at least one rule
      other than "everything", so a new case with an unknown prefix fails the test.
- [ ] AC15: When `origin/main` or the merge-base cannot be found, the changed-cases option
      ends with a message and without a run. When it selects no case, it says so and does
      not run.

Release gate and clean tree

- [ ] AC16: `eval.sh` refuses to run when `plugin/` has uncommitted changes, untracked
      files included (`git status --porcelain -- plugin/`, without the receipt). Test with
      an untracked file under `plugin/`.
- [ ] AC17: `pre-push` reads the receipt from the tagged commit
      (`git show <tag>:plugin/evals/last-run.json`), not from the working tree. Test: a
      green receipt in the working tree with a red one in the tagged commit is refused,
      and the reverse passes.

Documentation

- [ ] AC18: `docs/CONVENTIONS.md` describes error versus fail, which errors are outside
      the five-run policy, merging and the 5/5 rule for a failed case, and both options.
      `docs/DECISIONS.md` gets a row with these rules and the rejected alternatives.
      `docs/BACKLOG.md` loses the two delivered items, and `docs/ROADMAP.md` gets the item
      ticked with a link to this spec.
- [ ] AC19: `bash scripts/check.sh` is green, and `git diff origin/main -- plugin/` is
      empty: no plugin change and no version bump.

## Decisions and rejected alternatives

| Decision | Rejected alternatives | Rationale |
|----------|-----------------------|-----------|
| A subset run on the same fingerprint and model merges per case. A `fail` case is replaced only by a measurement of ≥5 runs that passed 5/5. | merging only errored cases; any re-run replaces | Retrying a flaky case until it passes would erode the gate. The 5/5 rule is the 2026-09-22 policy, so a case that passes it could keep `runs: 1` without changing `plugin/`. A case measured at 4/5 needs `runs: 3`, which changes the fingerprint and needs a new suite anyway. |
| An infrastructure error means known patterns plus "no verdict". Any other error is `fail`. | every non-null `error` is an infrastructure error | A skill's timeout is a real plugin problem. In doubt, the release gate refuses rather than lets through. |
| Changed cases are chosen by a diff against the merge-base with `origin/main`, through a mapping in `scripts/`, as an opt-in option. | the changed-cases mode as the default; per-case path lists in `case.yaml` | Keeping the mapping in `scripts/` leaves `plugin/` unchanged and needs no version bump (the roadmap's condition). A full default avoids an incomplete run by mistake, although `pre-push` would refuse it anyway. |
| The two eval backlog items whose triggers fired are in scope. | leaving them in the backlog | They touch the same files, and merging makes the right fingerprint even more important. |

## Owner decisions

- Merging: a subset run on the same fingerprint and model; a `fail` only by a 5/5
  measurement — accepted (2026-10-04).
- Infrastructure error: known patterns plus no verdict; any other error is `fail` —
  accepted (2026-10-04).
- Changed cases: a diff against the merge-base with `origin/main`, the mapping in
  `scripts/`, opt-in — accepted (2026-10-04).
- In scope from the backlog: untracked files in `eval.sh` and the receipt from the tagged
  commit in `pre-push` — accepted (2026-10-04).
- New dependency: none. Data migration: none (the old receipt format is replaced by the
  next run).

## Open questions (non-blocking)

- The names of the `eval.sh` options (e.g. `--rerun-errors`, `--changed`) are for the
  planner to choose.
- Whether a receipt in the old format, without per-case verdicts, is read as "every case
  missing" (the re-run option then runs the full suite) or refused with a message. Either
  way it does not merge. The planner chooses.
