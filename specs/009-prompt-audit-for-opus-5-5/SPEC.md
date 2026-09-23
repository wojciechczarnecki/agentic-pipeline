---
status: implemented
stage_history:
  - "spec-draft — 2026-09-23"
  - "spec-ready — 2026-09-23"
  - "plan-draft — 2026-09-24"
  - "plan-approved — 2026-09-24"
  - "implemented — 2026-09-24"
metrics:
  started_at: 2026-09-24T00:06
  escalations: 0
  plan_steps: 17
  plan_review_blockers: 0
  plan_review_majors: 1
  plan_changes: 6
  implement_steps: 17
  implement_iterations: 0
  deviations: 0
  final_review_blockers: 0
  final_review_worth_fixing: 2
  final_review_nits: 5
---

# SPEC 009 — Prompt audit of the skills and agents for Claude Opus 5.5

## Goal

The skills and agents still use the prompting style of the 0.2.0 import, which was
written for earlier models: capitals as emphasis, strategy hints the model follows
unprompted, and a plan reviewer told that its success is finding gaps. Claude Opus 5.5
follows instructions closely and literally, so the capitals make it over-apply rules and
the reviewer line invites made-up findings. Success: every accepted finding of the audit
(`AUDIT.md` beside this file) is applied, one commit per finding. A test keeps the
emphasis from coming back, and the full eval suite stays green on the audited text. The
other Stage 6 items are written on top of this text in a later spec.

## Context

- The audit was run during `/pipeline:idea` with `/claude-api prompt-audit`
  (`specs/009-prompt-audit-for-opus-5-5/AUDIT.md`). It lists seven findings with an action
  and six flags, and the owner decided on each (Owner decisions). The report is the source
  of the exact replacement texts. The PLAN turns each accepted finding into a step.
- Audited surface: `plugin/skills/{idea,plan,plan-review,implement,final-review,ship,init}/SKILL.md`
  and `plugin/agents/{planner,plan-reviewer,implementer,reviewer}.md`. Their text is the
  0.2.0 import, translated one to one in SPEC 008 (0.6.0), which left the rewording to
  this audit.
- Tests that pin skill text: `plugin/tests/test_stage_contract.py` (the stage contract and
  the escalation triggers are character-identical in `ship` and the four agents),
  `test_stage_skills.py` (identical configuration and language blocks across the six stage
  skills), `test_language_contract.py`, `test_init_skill.py`, `test_english_only.py`.
  None of them asserts on a capitalised word the audit changes (checked with grep). The
  eval graders do contain capitals, but they are out of scope.
- Eval cases that exercise the changed text: `implement-escalates-on-failing-test`
  (S1, S2, P1 in `implement`), `plan-review-escalates-on-dependency` and
  `plan-review-approves-polish-owner-decision` (P2, P3, P1 in `plan-review`),
  `final-review-finds-planted-defect` and `final-review-ignores-false-positive` (S3),
  and `init-without-questions`, `init-keeps-manual-edits` and
  `init-writes-the-chosen-language` (P1 in `init`). `idea` (R1) and `ship` have no eval
  case.

## Read context

- `docs/ROADMAP.md` — Stage 6, first item: the audit ships as its own spec in 0.7.0, with
  an eval run before the other Stage 6 items land, the report first and then each
  accepted change on its own. The stage contract repetition and the exact git, test and
  status steps stay. The later items (test-first, converge, proportional depth, nit cap,
  their eval cases) are a later spec written on the audited text.
- `docs/PROJECT.md` — no functional requirement changes. Non-functional: behaviour changes
  are released as tagged versions, and this spec starts 0.7.0.
- `docs/DECISIONS.md` — 2026-09-22 (Stage 6 releases are 0.7.0); 2026-09-23 SPEC 008 row
  (one-to-one translation so that the audit is where the wording changes); the language
  contract, the section map and the severity tokens stay binding and unchanged; 2026-09-20
  and 2026-09-22 eval rows (local receipt, `runs: 1`, the measuring policy for a failing
  case).
- `docs/BACKLOG.md` — P2 Idea item "`idea` must not start `/pipeline:ship` … nor mark its own
  `(assumption)` items approved". Its trigger is this audit, so the item is delivered by R1
  and removed. The P2 Stages item on calling `workflow_metrics.py` by name stays: its
  trigger (a stall under `ship`) has not fired, and an addition in this spec would blur
  what a regression points at. The P2 Evals item on the flaky
  `plan-review-escalates-on-dependency` applies if that case fails in AC9.
- `docs/CONVENTIONS.md` — a change to the skills' wording is a behaviour change and ships
  as a release. The eval policy: a case that fails in any run is measured with 5 runs.
  Commits are in English, one step per commit.
- `plugin/README.md` — the `RESULT` contract and the stage mechanics are unchanged. The
  README quotes no sentence the audit changes (checked with grep).

## Scope

- Apply the accepted findings P1, P2, P3, S1, S2, S3 and R1 as given in `AUDIT.md` →
  Findings (Action column), one commit per finding, with P1 split into one commit per
  file.
- A pytest check that keeps capitals-as-emphasis out of the skills and agents.
- `docs/DECISIONS.md` row, `docs/CONVENTIONS.md` line, `plugin/CHANGELOG.md` 0.7.0 section
  and the version bump, the backlog item removed, and the roadmap item ticked.
- After the PR is open and before merge, on the owner's command: a full
  `bash scripts/eval.sh` run whose receipt is committed on the PR branch.

## Out of scope

- The flags G1–G6. They stay in `AUDIT.md` only, with no backlog item (owner decision).
- Eval graders, templates and guard messages. A grader change would move the gate this
  audit is measured by.
- The other Stage 6 items (test-first in `implement`, the converge pass, depth
  proportional to the change, the final-review nit cap, their eval cases): a later spec on
  the audited text.
- Calling `workflow_metrics.py` by name: `docs/BACKLOG.md` P2, trigger unchanged.
- Per-stage model and effort: Stage 7.
- Tagging 0.7.0, the canary, moving `stable` and the GitHub Release. The owner does these
  after the later Stage 6 spec lands (owner decision).

## Requirements and acceptance criteria

- [ ] AC1 (P1): no word of three or more capital letters is used as emphasis in
  `plugin/skills/*/SKILL.md` or `plugin/agents/*.md`. A pytest check scans the text outside
  code spans and fenced blocks and allows only an explicit token list: `STOP`, `RESULT`,
  `DONE`, `ESCALATE`, `STATUS`, `METRICS`, `ESCALATION`, `SUMMARY`, `SPEC`, `PLAN`, `NNN`,
  `AC`/`ACs`, `CI`, `PR`, `UI`, `API`, `CLI`, `JSON`, `HTTPS`, `README`, `CLAUDE`, `GATE`,
  `E2E`, `URL`, `TODO`. The PLAN may extend the list only with identifiers, each named
  with its reason in `## Deviations`. The check fails on the current `main` text.
- [ ] AC2 (P1): every rule whose capitals are lowered keeps its words and its reason. A
  review of the diff shows only case changes in the P1 commits, apart from whole-sentence
  rewrites that another finding covers.
- [ ] AC3 (P2): `plan-review/SKILL.md` no longer contains "Assume the plan has gaps" or
  "your success is". Its role paragraph states the review targets (an AC without steps or
  a test, a broken decision, a step whose verification cannot run), says that the review
  reports its findings with severity together with what was checked and found sound, and
  keeps the sentence that the reviewer decides on approval. Checked by pytest.
- [ ] AC4 (P3): `plan-review/SKILL.md` has the heading `## What the status triggers` and no
  heading that contains `IMPORTANT`, and the paragraph under it is unchanged. Checked by
  pytest.
- [ ] AC5 (S1, S2): in `implement/SKILL.md` the self-correction loop has no "read the full
  error output" or "start from the first" sub-point, and its remaining sub-points are
  renumbered with the same content. The gate states that the next step starts only when
  the current step's verification is green, that a suspected flaky test is still red and
  that a skipped test is not green. It no longer has the "No exceptions" line. Checked by
  pytest.
- [ ] AC6 (S3): `final-review/SKILL.md` no longer contains "Green tests ≠ correct code".
  Checked by pytest.
- [ ] AC7 (R1): `idea/SKILL.md` → `## Guardrails` states that the stage ends at the
  handoff, that `/pipeline:ship` and the later stages are started by the owner and never
  by `idea` (GATE 1 is the owner's), and that `idea` does not remove an `(assumption)`
  suffix or set `spec-ready` before the owner has answered on every such item. With no
  answer, including in a session without `AskUserQuestion`, the SPEC stays `spec-draft`.
  Checked by pytest on the guardrail text.
- [ ] AC8: one commit per accepted finding, with P1 as one commit per file. Each commit
  message names its finding id (e.g. `refactor: lower emphasis in implement (P1)`).
  Checked in `git log` of the branch during the final review.
- [ ] AC9: with the PR open, on the owner's command, `bash scripts/eval.sh` (full suite,
  default model) is green for every case. The receipt `plugin/evals/last-run.json` is
  committed on the PR branch, and its fingerprint matches `plugin/` at the branch head. A
  red case is re-run alone first (`--case`) to tell flakiness from a regression; a
  regression is traced to its finding's commit and fixed on the branch, within the spend
  in Owner decisions.
- [ ] AC10: documents:
  - `docs/DECISIONS.md` has the prompt-style row (added with this SPEC): a rule is stated
    at normal volume with its reason, capitals are kept for contract tokens only, and a
    test enforces it.
  - `docs/CONVENTIONS.md` states the same rule for skill and agent text.
  - `plugin/CHANGELOG.md` gains a 0.7.0 section with a `Changed` entry per group of
    findings and a consumer-impact sentence (no configuration change).
  - `plugin/.claude-plugin/plugin.json` is at `0.7.0`.
  - The P2 Idea item is removed from `docs/BACKLOG.md`.
  - The first Stage 6 item in `docs/ROADMAP.md` is ticked with a link to this spec.
- [ ] AC11: `bash scripts/check.sh` passes.

## Decisions and rejected alternatives

| Decision | Rejected alternatives | Rationale |
|----------|-----------------------|-----------|
| The audit ran during `idea` and the owner decided on each finding there; the accepted findings are the ACs | the planner runs the audit and escalates for decisions; the planner decides alone by criteria | The roadmap puts the report first and each accepted change after it. Wording is the owner's call, so the decisions belong at GATE 1, and `ship` then runs without an escalation |
| This spec is the audit only; the other Stage 6 items are a later spec | the whole of Stage 6 in one spec; the audit plus the nit cap | The roadmap asks for the eval to run on the audited text before the additions land, so a regression points at one change set |
| One commit per finding (P1 per file) and one full eval at the end | a full eval after each finding (about $3.4 × 7); one commit for the whole audit | Per-finding commits let a regression be bisected with targeted `--case` runs, at the cost of one suite |
| Version 0.7.0 now; the tag, canary and `stable` after the later Stage 6 spec | a 0.7.0 release now with the additions as 0.8.0; a 0.6.1 patch | The roadmap numbers every Stage 6 item 0.7.0, and one release means one canary. A patch would skip the eval gate a wording change needs |
| A pytest check with an explicit token allowlist enforces the style | prose in `docs/CONVENTIONS.md` only | A rule nothing checks drifts (SPEC 001 lesson). The allowlist separates identifiers from emphasis |
| Eval graders are left as they are | lowering their capitals too | Graders judge the run. Changing them in the same spec would move the measuring stick along with what it measures |

## Owner decisions

- 2026-09-23, audit findings: P1, P2, S1 and R1 (high confidence) and P3, S2 and S3 (medium)
  are accepted. The flags G1–G6 stay in `AUDIT.md` only, with no backlog item.
- New dependency: none. Data migration: none. No configuration key changes.
- Eval spend for this spec: up to $10 (one full suite plus one re-run after a fix) —
  accepted.
- The agent may run `bash scripts/eval.sh` and commit the receipt on the PR branch, but
  only after the PR is open and on the owner's explicit command — accepted.
- The version is bumped to 0.7.0 in this spec. The later Stage 6 spec extends the same
  untagged 0.7.0 CHANGELOG section. Tag, canary, `stable` and GitHub Release come after it.

## Open questions (non-blocking)

- none
