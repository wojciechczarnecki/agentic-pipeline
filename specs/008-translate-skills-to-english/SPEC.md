---
status: implemented
stage_history:
  - "spec-draft — 2026-09-23"
  - "spec-ready — 2026-09-23"
  - "plan-draft — 2026-09-23"
  - "plan-approved — 2026-09-23"
  - "implemented — 2026-09-23"
metrics:
  started_at: 2026-09-23T15:42
  escalations: 0
  plan_steps: 12
  plan_review_blockers: 0
  plan_review_majors: 0
  plan_changes: 5
  implement_steps: 12
  implement_iterations: 1
  deviations: 5
---

# SPEC 008 — Skills, agents and tests translated into English

## Goal

The plugin's skills and agents are the last Polish part of a public, English repository:
a reader or contributor cannot follow the pipeline's rules without Polish, and every stage
still quotes Polish headings next to the English ones. Success: skills, agents, tests and
eval graders are English, Polish survives only where a Polish consumer needs it (the
`*.pl.md` templates, the section map, the Polish eval fixture), and the full eval suite
stays green, proving that the translation changed the language and nothing else. This
closes Stage 8.

## Context

- SPEC 006 (0.5.0) made the language contract explicit; SPEC 007 (0.6.0, not yet tagged)
  moved the SPEC/PLAN templates and the section map out of the skills into
  `plugin/templates/{SPEC,PLAN}.{pl,en}.md` and `plugin/templates/sections.md`, read with
  `Read` at run time. 007 left to this spec the translation, the release eval receipt and
  the canary on the Polish consumer (SPEC 007 → Out of scope, Owner decisions).
- Polish today: all seven `plugin/skills/*/SKILL.md` (frontmatter `description` and
  `argument-hint` included) and four `plugin/agents/*.md`; test assertions pinned to Polish
  prose and headings (`plugin/tests/test_language_contract.py`, `test_stage_skills.py`,
  `test_stage_contract.py`, `test_init_skill.py`, `test_eval_cases.py`) and comments that
  say the skills are Polish (`test_readme.py`, `test_stage_skills.py`); three eval cases
  (`guard-blocks-main-push`, `init-keeps-manual-edits`, `init-without-questions`) with
  Polish prompts, descriptions and graders.
- Polish that stays by design: `plugin/templates/*.pl.md`, `plugin/templates/docs/*.pl.md`,
  `plugin/templates/sections.md`, the fixture of `plan-review-approves-polish-owner-decision`,
  and the test data that pins them (`test_templates_language.py` snapshot, the mirror-case
  checks in `test_eval_cases.py`). Generated `plugin/evals/results/` reports quote past runs.
- Already English: `plugin/bin/`, hooks, `plugin/README.md`, `plugin/docs/`,
  `plugin/CHANGELOG.md`, the English templates.
- Documents that describe the Polish skills as current: `CONTRIBUTING.md` (Language),
  `docs/CONVENTIONS.md` (the language bullets), `docs/DECISIONS.md` rows of 2026-09-17 and
  2026-09-21.

## Read context

- `docs/ROADMAP.md` — Stage 8, last open item: skills, agents and tests translated into
  English in 0.6.0, the Polish mirror eval re-run on the translated skills, Polish only in
  the `*.pl.md` templates and the section map; each Stage 8 release goes through the
  pre-release canary on a Polish consumer before `stable` moves. Stage 6 plans the prompt
  audit (0.7.0) right after, on the English text, and requires this translation to stay one
  to one so the eval gate proves parity.
- `docs/PROJECT.md` — no functional requirement changes: the same stages, guard and
  `init`; non-functional: project and domain agnostic, behaviour changes released as
  tagged versions — 0.6.0 is untagged, so this spec joins it.
- `docs/DECISIONS.md` — 2026-09-17 and 2026-09-21 (skills Polish until Stage 8) are
  superseded by this spec and get an amending row; 2026-09-22 (Stage 8 before Stage 6,
  releases 0.5.0 and 0.6.0); 2026-09-23 language contract, section map, severity tokens
  and run-time reads — all binding and unchanged: `language` still decides what is
  written, the map remains the Polish ↔ English bridge.
- `docs/BACKLOG.md` — the P2 item on calling `workflow_metrics.py` by name stays out
  (as in SPEC 007: no behaviour change beyond the translation); no backlog item is
  delivered by this spec.
- `docs/CONVENTIONS.md` — the language bullets say the skills are Polish until 0.6.0 and
  must be updated; a translation is a behaviour change and ships as a release.
- `plugin/README.md` — the language contract and the section map are the source of truth
  the translated skills must state unchanged; the `RESULT` block field names stay as they
  are.

## Scope

- Translate every `plugin/skills/*/SKILL.md` and `plugin/agents/*.md` into English, one to
  one, frontmatter `description` and `argument-hint` included.
- Stages name a SPEC/PLAN section by its English heading; the Polish twin comes only from
  the section map, which every stage keeps reading before it looks for a section and whose
  either heading it keeps accepting.
- Translate `plugin/tests` and `tests/`: comments, docstrings, test names and every
  assertion pinned to skill prose; Polish stays only as data that pins the Polish
  templates, the map and the Polish fixture.
- Eval cases: all graders and case descriptions in English; the prompts of
  `guard-blocks-main-push` and `init-keeps-manual-edits` in English with the same meaning
  (including "documents in Polish" for the latter); `init-without-questions` keeps its
  Polish prompt, because a Polish conversation that must not yield `language: pl` is what
  it tests.
- Update `CONTRIBUTING.md`, `docs/CONVENTIONS.md` and add a `docs/DECISIONS.md` row; extend
  the 0.6.0 section of `plugin/CHANGELOG.md`; tick the roadmap item.
- After the PR is open and before merge (gate 3), on the owner's command: a full
  `bash scripts/eval.sh` run whose receipt is committed on the PR branch.

## Out of scope

- The prompt audit and any rewording beyond what English needs — Stage 6, 0.7.0, its own
  spec.
- Calling `workflow_metrics.py` by name only — `docs/BACKLOG.md` P2, trigger unchanged.
- Translating existing specs, plans or eval result reports — history stays as written.
- Tagging 0.6.0, moving `stable`, the GitHub Release and the canary on the Polish
  consumer — the owner's release steps (`CLAUDE.md` → Commands).

## Requirements and acceptance criteria

- [ ] AC1: no file under `plugin/skills/` or `plugin/agents/` contains a Polish letter
  (`ąćęłńóśźż`, either case) — a pytest check.
- [ ] AC2: a pytest check lists every file under `plugin/` and `tests/` that contains a
  Polish letter (excluding `plugin/evals/results/`) and fails on any file outside an
  explicit allowlist: the `*.pl.md` templates, `templates/sections.md`, the
  `plan-review-approves-polish-owner-decision` fixture, the `init-without-questions`
  `case.yaml`, and the test modules that pin those files as data.
- [ ] AC3: in `plugin/tests/` and `tests/`, comments, docstrings and test function names
  contain no Polish letter — a pytest check over the Python tokens.
- [ ] AC4: every SPEC/PLAN heading a skill or agent quotes is the English literal of a
  `templates/sections.md` row; every stage skill still carries one identical block that
  reads the map with `Read` before looking for a section, accepts either heading, and ends
  the stage on a failed read (`RESULT: ESCALATE` / stop, the file and the allow rule) —
  pytest.
- [ ] AC5: the blocks pinned as identical today stay identical in English: the language
  block and the configuration block across the six stage skills, the stage contract and
  the escalation triggers across `ship` and the four agents — the existing structural
  tests, retargeted to the English headings, keep every assertion they have today.
- [ ] AC6: one to one — for every skill and agent, the code spans (`` `…` ``) of the
  version on `main` at the branch point and of the translated version differ only by the
  dropped Polish headings and by Polish text inside spans; every other difference is listed
  and justified in the PLAN's `## Deviations`. Checked once, by a comparison run during
  implementation whose output goes into the PLAN.
- [ ] AC7: eval cases — no Polish letter in any `graders/criteria.md` or case
  `description`; the prompts of `guard-blocks-main-push` and `init-keeps-manual-edits`
  are English; `init-without-questions` keeps its Polish prompt and its grader still
  names `"pl"` and a Polish conversation as the wrong behaviour — pytest.
- [ ] AC8: with the PR open, on the owner's command, `bash scripts/eval.sh` (full suite,
  default model) is green for every case, `plan-review-approves-polish-owner-decision` and
  `init-without-questions` included; the receipt `plugin/evals/last-run.json` is committed
  on the PR branch and its fingerprint matches `plugin/` at the branch head. A red case is
  fixed on the branch and the suite re-run, within the spend in Owner decisions.
- [ ] AC9: documents — `CONTRIBUTING.md` and `docs/CONVENTIONS.md` state that skills and
  agents are English and that Polish lives in the `*.pl.md` templates and the section map;
  `docs/DECISIONS.md` gains a row that amends the 2026-09-17 and 2026-09-21 rows;
  `plugin/CHANGELOG.md` 0.6.0 gains a `Changed` entry and a consumer-impact sentence (no
  configuration change; a `"language": "pl"` consumer keeps Polish specs, plans and
  documents); the version stays `0.6.0`; the Stage 8 item in `docs/ROADMAP.md` is ticked
  with a link to this spec.
- [ ] AC10: skill `description`s in English still trigger the right skill from a Polish
  request — checked in the canary (owner, release) rather than by a new eval case
- [ ] AC11: `bash scripts/check.sh` passes.

## Decisions and rejected alternatives

| Decision | Rejected alternatives | Rationale |
|----------|-----------------------|-----------|
| Stages name a section by its English heading only; the map is the one Polish ↔ English bridge | keeping both headings in the skills; naming sections by map key | The roadmap's end state (Polish only in templates and the map); the map read is already mandatory and a failed read stops the stage, and the Polish mirror eval proves a Polish SPEC is still found |
| One-to-one translation | rewording while translating | Parity must be provable by the eval gate; the wording changes in the Stage 6 audit, so a regression points at one change, not two |
| The eval suite runs after the PR opens, before merge, on the owner's command; its receipt is committed on the PR branch | a parity run during implementation plus a separate release receipt; the receipt only at release; a receipt in the PR re-run after apply | It runs on the final `plugin/` state, so one run is both the parity proof and the 0.6.0 release receipt (the fingerprint survives the squash merge); the roadmap tick reaches `main` only together with a green run. Cost accepted: a regression is fixed on the branch outside the autonomous loop, and the spec reaches `done` before the eval |
| `init-without-questions` keeps its Polish prompt; all graders are English | translating every prompt; leaving the old eval cases Polish | That prompt is what the case tests (a Polish conversation must not yield `language: pl`); graders are instructions to a model, like the skills |
| The translation joins the untagged 0.6.0 | a separate 0.6.1 or 0.7.0 | The roadmap puts both Stage 8 items in 0.6.0; one canary covers the run-time reads and the translation, which 007 prepared for |

## Owner decisions

- New dependency: none. Data migration: none; no configuration key changes.
- Eval spend for this spec: up to $10 (one full suite plus one re-run after a fix) —
  accepted.
- The agent may run `bash scripts/eval.sh` and commit the receipt on the PR branch, only
  after the PR is open and on the owner's explicit command — accepted.
- The canary on the Polish consumer, the tag, `stable` and the GitHub Release stay the
  owner's release steps.

## Open questions (non-blocking)

- none
