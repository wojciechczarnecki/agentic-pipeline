---
status: plan-approved
stage_history:
  - "spec-draft — 2026-09-22"
  - "spec-ready — 2026-09-22"
  - "plan-draft — 2026-09-23"
  - "plan-approved — 2026-09-23"
metrics:
  started_at: 2026-09-23T02:06
  escalations: 0
  plan_steps: 11
  plan_review_blockers: 0
  plan_review_majors: 1
  plan_changes: 4
---

# SPEC 006 — Language made explicit

## Goal

A consumer picks one language for what the pipeline writes into the repository, and gets
it everywhere: `/pipeline:init` asks for it and generates the project documents in it, and
every stage writes specs, plans, reports and PR descriptions in it. Commit messages, PR
titles and branch names stay English whatever the setting, and the conversation in the
terminal follows the Claude Code session language, not `language`. It works when a new
project initialised with `en` gets English documents, specs and plans while the owner is
asked questions in Polish, and a consumer with `"language": "pl"` sees no change.

## Context

- Stage 8 of `docs/ROADMAP.md`, release 0.5.0 — the first of two; 0.6.0 (skills, agents and
  tests translated into English) is a separate spec after this one ships and passes the
  canary. Skills stay Polish in this release.
- Today only `idea` names `language` (`plugin/skills/idea/SKILL.md`, step 4). `plan`,
  `plan-review`, `implement`, `final-review` and `ship` never mention it; in this
  repository (`"language": "en"`) plans 001–005 came out English only because the planner
  mirrored the English SPEC and `CLAUDE.md` — behaviour, not a rule.
- The SPEC template is inline in `plugin/skills/idea/SKILL.md`, the PLAN template inline in
  `plugin/skills/plan/SKILL.md`; both Polish. Stages name sections by their Polish
  headings (`## Decyzje właściciela`, "Streszczenie dla właściciela", `## Final review`,
  `## Review log`, `## Deviations`), while specs 001–005 here use English ones
  (`## Owner decisions`, `## Owner summary`, …). No script parses these headings
  (`plugin/bin`, `plugin/hooks` checked); only the model reads them. The English specs are
  not uniform: three say `## Read context`, two `## Context read`.
- Finding severities: `final-review` uses `blocker | warto poprawić | nit`, `plan-review`
  `blocker | major | minor`; metric keys are English already
  (`final_review_worth_fixing`). The final-review eval criteria accept the Polish label
  (`plugin/evals/final-review-finds-planted-defect/graders/criteria.md`).
- `/pipeline:init` copies `plugin/templates/CLAUDE.md` and `plugin/templates/docs/*`, all
  Polish, whatever `language` the owner answers (question 4 of its single round). The
  template `docs/CONVENTIONS.md` leaves the language of commit messages as `TODO`.
- `plugin/bin/workflow_config.py`: `language` is a free `str`, default `"pl"`
  (`defaults()`); the README configuration table says the same. A bad key only warns and
  falls back to its default — the guard never blocks on configuration
  (`plugin/bin/guard.py`, `read_config`).
- Consumers today: this repository (`"language": "en"`) and one private Polish consumer
  with an explicit `"language": "pl"` and 23 Polish specs whose headings match the current
  Polish templates. No known consumer relies on the missing-key default.
- Evals: `init-without-questions` runs `init` unattended with no language given and does
  not check the documents' language.

## Read context

- `docs/ROADMAP.md` — Stage 8 fixes the order (0.5.0 before 0.6.0) and the canary on a
  Polish consumer before `stable` moves; its 0.5.0 item said questions and escalations
  follow `language` and named only English `init` templates — both are revised by this
  spec's owner decisions, and the Stage 8 text is updated in this spec's commit.
- `docs/PROJECT.md` — "Project and domain agnostic" and "`init` scaffolds a consumer
  project" bind the change: the language is consumer configuration, and `init` is where it
  enters; no requirement conflicts.
- `docs/DECISIONS.md` — the 2026-09-17 row (`language` independent of the skills'
  language) and the 2026-09-21 rows (README quotes the Polish literals; skills translated
  only behind the eval gate) hold: this release changes what skills write, not the
  language they are written in; the 2026-09-22 row placed Stage 8 before Stage 6.
- `docs/CONVENTIONS.md` — "code, identifiers, comments and commit messages are English
  regardless of `language`" is already this repository's rule; this spec makes the commit
  and PR-title half of it the plugin's rule for every consumer.
- `plugin/README.md` — the configuration table (`language`, default `"pl"`) and the
  mechanics sections are the single source of truth this spec extends with a language
  contract and a section map.

## Scope

- A language contract, stated in `plugin/README.md` and applied by every stage skill and
  stage agent: what follows `language`, what is always English, what follows the session.
- SPEC and PLAN templates as files per language (`*.en.md`, `*.pl.md`), used by `idea` and
  `plan`, with a structure-parity test.
- A section map (key → Polish heading → English heading) so stages find sections in either
  language; severities as fixed English tokens.
- `/pipeline:init`: the language question first, and `CLAUDE.md` plus `docs/*` generated
  from per-language templates.
- `language` validated to `en` / `pl`; default becomes `en`.
- One new eval case for `init` in a chosen language; `init-without-questions` criteria
  extended.
- Documentation and release: `plugin/README.md`, `docs/CONVENTIONS.md`,
  `docs/DECISIONS.md`, `docs/ROADMAP.md`, version 0.5.0, `plugin/CHANGELOG.md`.

## Out of scope

- Translating skills, agents and tests into English — 0.6.0, the next spec (Stage 8).
- Languages other than `en` and `pl` — no trigger; a new language is a template pair and a
  map column when a consumer asks for one.
- Translating a consumer's existing documents or specs when its `language` changes — the
  owner's move, not the plugin's.
- An eval case for `plan` writing in `language` over a SPEC in another language — pytest
  on the skill text plus the canary; `docs/BACKLOG.md` P3, trigger: a plan written in the
  wrong language after 0.5.0.

## Requirements and acceptance criteria

The language contract

- [ ] AC1: `plugin/README.md` has a language section stating three groups. Follows
      `language`: every file the pipeline writes into the repository — SPEC, PLAN (every
      section, including review log, deviations, final review and owner-decision entries),
      the documents `init` generates — and PR descriptions. Always English, regardless of
      `language` and the session: commit messages, PR titles, branch names and spec slugs,
      the `RESULT` block keys, metric keys and severity tokens. Follows the Claude Code
      session language, never `language`: questions to the owner, escalations shown to
      the owner, stage summaries and handoffs in the terminal.
- [ ] AC2: each stage skill (`idea`, `plan`, `plan-review`, `implement`, `final-review`,
      `ship`) and each stage agent states the part of the contract it acts on — writing
      its artefacts in `language`, committing (and, for `final-review`, titling the PR) in
      English, talking to the owner in the session language; a pytest test checks every
      skill that writes a spec file names `language` and every skill that commits or opens
      a PR names English for commit messages and PR titles.
- [ ] AC3: `plan` writes PLAN.md in the current `language`, even when SPEC.md is in another
      language (SPEC is not translated); `plan-review` checks the plan's language against
      `language` as a checklist item and fixes it in place.
- [ ] AC4: `final-review` (apply) opens the PR with an English conventional-commit title
      and a body in `language`; `ship` presents escalations and the gate-2 question in the
      session language.

Templates and sections

- [ ] AC5: SPEC and PLAN templates are files in `plugin/templates/` named `*.en.md` and
      `*.pl.md`; `idea` and `plan` read the one for `language` (through the shell, as
      `init` reads templates) and no longer carry an inline template.
- [ ] AC6: the Polish templates keep today's Polish headings and frontmatter verbatim, so a
      Polish consumer's new specs look like its existing ones. The English templates use
      the headings of specs 001–005 here: SPEC — `Goal`, `Context`, `Read context`,
      `Scope`, `Out of scope`, `Requirements and acceptance criteria`,
      `Decisions and rejected alternatives`, `Owner decisions`,
      `Open questions (non-blocking)`; PLAN — `Owner summary`, `Approach`,
      `AC → steps matrix`, `Steps`, `Risks and traps`, `End-to-end verification`
      (`Automatic (performed by /pipeline:implement)`, `Manual (performed by the owner)`),
      `Definition of Done`, `Owner decisions`, `Review log`, `Deviations`, `Final review`.
- [ ] AC7: `plugin/README.md` has a section map: one row per SPEC/PLAN section with a
      stable key, the Polish heading and the English heading. Stages name a section by
      both headings (or by the map) and accept either when reading, so a spec written
      before a language change, or before this release, is read correctly.
- [ ] AC8: a structure-parity test: for each template pair the headings, their levels and
      order map one-to-one through the section map, the frontmatter keys are identical,
      every map row occurs in its template, and the English templates contain no Polish
      letter (`ąćęłńóśźżĄĆĘŁŃÓŚŹŻ`) outside code spans.
- [ ] AC9: severities are the English tokens `blocker` / `worth-fixing` / `nit`
      (`final-review`) and `blocker` / `major` / `minor` (`plan-review`), written as code in
      every language; a report written before this release that says `warto poprawić` is
      read as `worth-fixing`; `ship`'s gate-2 options and the final-review eval criteria
      use the tokens.

`init`

- [ ] AC10: the language question is the first question of `init`'s single round (options
      `en` — recommended — and `pl`); the round stays at most four questions.
- [ ] AC11: `init` generates `CLAUDE.md` and `docs/*` from per-language templates
      (`*.en.md` / `*.pl.md`) matching the answer and writes that value to `language` in
      `.claude/workflow.json`; the English templates contain no Polish letter outside code
      spans; the Polish templates keep today's content.
- [ ] AC12: unattended (`claude -p`, no `AskUserQuestion`), `init` takes the language from
      its argument when the argument names one, and `en` otherwise — without a `TODO:`
      marker, since `en` is the default.
- [ ] AC13: a re-run of `init` whose language answer differs from the existing `language`
      updates only `language` in `.claude/workflow.json`, leaves existing documents
      untouched (idempotence, step 6) and tells the owner they stay in the old language.
- [ ] AC14: the `docs/CONVENTIONS.md` templates state commit messages, PR titles and branch
      names as English (no `TODO`), documentation as `language`, and that the conversation
      language is not set by the project.

Configuration

- [ ] AC15: `workflow_config.py` defaults `language` to `"en"`; a value other than `"en"`
      or `"pl"` produces the warning `` `language` has to be one of: en, pl `` and falls
      back to `"en"`, like any other bad key; tested in
      `plugin/tests/test_workflow_config.py`. The README configuration table says
      default `"en"`, supported `en`, `pl`.

Evals

- [ ] AC16: a new eval case runs `init` unattended with an argument naming `pl` and passes
      when `.claude/workflow.json` has `"language": "pl"` and `CLAUDE.md` and `docs/*` are
      Polish; `init-without-questions` (no language given, Polish prompt) additionally
      passes only when `language` is `"en"` and the documents are English — the prompt's
      language must not leak into the documents.

No regression for a Polish consumer

- [ ] AC17: with `"language": "pl"`, the SPEC and PLAN the stages produce have exactly the
      headings and frontmatter of today's inline templates — a test compares the Polish
      template files against a snapshot of those headings taken before the templates move.
- [ ] AC18: the PR description lists the owner's 0.5.0 canary on the Polish consumer: a
      `/pipeline:plan` (or `ship` up to `plan-draft`) on a Polish spec yields a Polish PLAN
      with the Polish headings, questions come in the session language, and the
      `Found N plugins` count equals a plain session.

Documentation and release

- [ ] AC19: `docs/ROADMAP.md` Stage 8 matches this spec (updated in the spec commit; the
      0.5.0 item ticked in the PR); `docs/DECISIONS.md` gets rows for the language contract,
      the section map, the severity tokens and the default `en`; `docs/CONVENTIONS.md`
      says templates exist per language while skills stay Polish until 0.6.0.
- [ ] AC20: `plugin/.claude-plugin/plugin.json` reads `0.5.0`; `plugin/CHANGELOG.md` has a
      `## 0.5.0` section whose consumer impact says: a consumer without `language` now
      gets English — add `"language": "pl"` to keep Polish; `init` generates documents in
      the chosen language; commit messages and PR titles are English everywhere.
- [ ] AC21: `plugin/` stays on the standard library and names no consumer project;
      `bash scripts/check.sh` is green; the PR's last commit is a green receipt from
      `bash scripts/eval.sh` whose fingerprint matches the final `plugin/` tree.

## Decisions and rejected alternatives

| Decision | Rejected alternatives | Rationale |
|---|---|---|
| Three groups: files and PR bodies follow `language`; commits, PR titles, branch names and tokens always English; conversation follows the session | everything, questions included, in `language` (the old roadmap text) | The owner wants English artefacts and a Polish terminal; commit history and PR titles are read by tools and outsiders, the terminal only by the owner |
| PLAN follows the current `language`, not the SPEC's language | PLAN mirrors its SPEC | The owner's rule: spec and plan are always in `language`; a change in between is rare, and the setting wins |
| A section map (key → pl → en) plus parity test; stages accept either heading | hidden `<!-- section: … -->` markers; English headings in every language | Only the model reads sections, so a map is enough; markers would still need a fallback for the existing specs; English headings over Polish content break "no mixing of languages within one document" |
| English headings = those already in specs 001–005 (`Read context` over `Context read`) | new wording | Existing English specs keep matching without edits |
| Severities as fixed English tokens, old Polish label read as `worth-fixing` | translated labels per language | They are identifiers like metric keys; one set for skills, the ship gate and evals |
| Only `en` and `pl`; other values warn and fall back to `en` | any language, model-translated from the `en` templates | No template, no parity test, no eval for a third language; the guard's fail-open handling of bad keys already exists |
| One eval case (`init` with `pl`) plus stricter `init-without-questions` | two cases incl. `plan`; none | `init` is the only new path fully inside the plugin; the unattended default and the argument are then both covered |

## Owner decisions

- No new dependency (runtime or dev) and no data migration; if the plan needs either, it
  escalates. The default flip to `en` is accepted: the only Polish consumer sets
  `"language": "pl"` explicitly.
- Commit messages and PR titles are English regardless of `language` or anything else.
- Conversation (questions, escalations, summaries) follows the Claude Code session
  language, not `language`.
- `init` asks for the language and generates the documents in it; Polish templates (SPEC,
  PLAN and `init`) survive 0.6.0.
- The Stage 8 text of `docs/ROADMAP.md` is rewritten in this spec's commit at the owner's
  request, beyond the usual spec link.
- The agent runs `bash scripts/eval.sh` for the final receipt, as the PR's last commit
  after gate 2.

## Open questions (non-blocking)

- none
