---
status: implemented
stage_history:
  - "spec-draft — 2026-09-23"
  - "spec-ready — 2026-09-23"
  - "plan-draft — 2026-09-23"
  - "plan-approved — 2026-09-23"
  - "implemented — 2026-09-23"
metrics:
  started_at: 2026-09-23T12:45
  escalations: 1
  plan_steps: 10
  plan_review_blockers: 0
  plan_review_majors: 0
  plan_changes: 6
  implement_steps: 10
  implement_iterations: 3
  deviations: 4
  final_review_blockers: 0
  final_review_worth_fixing: 4
  final_review_nits: 10
  findings_accepted: 4
  findings_rejected: 10
---

# SPEC 007 — Stages read their templates and the section map at run time

## Goal

`idea` and `plan` carry both SPEC/PLAN templates inline, and every stage learns the section
headings from a map inside `plugin/README.md`. That puts two languages in every stage's
context and blocks the 0.6.0 translation: the Polish headings can only leave the skills once
the stages read them from a file. Success: each stage reads the one template it needs and a
standalone section map with `Read` from the plugin's own directory. A missing permission is
reported before it can stall a stage subagent. A Polish SPEC still passes `plan-review`.

## Context

- First of two specs for Stage 8's 0.6.0; SPEC 008 (translation of skills, agents and
  tests into English, the release receipt and the canary) follows it, and the tag waits for
  both. This spec translates nothing.
- Today: `plugin/skills/idea/SKILL.md` and `plugin/skills/plan/SKILL.md` embed
  `templates/{SPEC,PLAN}.{pl,en}.md` as fenced blocks, pinned byte for byte by
  `plugin/tests/test_templates_language.py`; the section map is the `### Section map`
  table in `plugin/README.md`, parsed by that test and referenced from the `## Język` block
  of all six stage skills (`plugin/tests/test_language_contract.py`).
- SPEC 006, `PLAN.md` deviation D1: a headless stage subagent was refused a `cat` of a
  plugin file, so the templates stayed inline (owner decision C). A later headless probe
  (2026-09-23, recorded in `docs/ROADMAP.md`) found `Read` refused from the skill's
  directory, the install cache and a `--plugin-dir` clone alike, and allowed by the narrow
  rule `Read(~/.claude/plugins/cache/wcz-tools/pipeline/**)`.
- The guard (`plugin/bin/guard.py`) already warns once per session about a missing or bad
  `.claude/workflow.json`, on stderr only; it never blocks on configuration.
- `plugin/templates/settings.json` is the project settings template `/pipeline:init`
  writes; its marketplace name is a placeholder that `init` fills in.

## Read context

- `docs/ROADMAP.md` — Stage 8, first unticked 0.6.0 item: its whole content is this
  spec's scope; the second item (translation and the Polish eval case) is split into SPEC
  008, except the eval case, which lands here (owner decision). Stage 8 runs before
  Stages 6–7.
- `docs/PROJECT.md` — no new functional requirement; the non-functional ones bind: plain
  `python3` for the guard, project-agnostic plugin (the rule is written with the consumer's
  marketplace name, never `wcz-tools` hard-coded outside this repository's own settings),
  `claude plugin validate --strict` passes.
- `docs/DECISIONS.md` — 2026-09-23 "Sections are found through a section map in
  `plugin/README.md` … inline templates … nothing is read from the plugin at run time" is
  reversed by this spec and needs a new row; the language contract (2026-09-23) and the
  severity tokens stay as they are; 2026-09-20 (release gate) and 2026-09-22 (eval
  policy: 5 runs for a new case, receipts on the default model, `--max-cost-usd`) bind the
  new eval case; 2026-09-22 (canary via `--plugin-dir`) is why the warning must cover a
  clone as well as the cache.
- `docs/BACKLOG.md` — P2 "`plan-review-escalates-on-dependency` is flaky" matters for the
  smoke run beside the new mirror case; P2 "stage calls `workflow_metrics.py` by path" is
  the same failure class (a prompt a subagent cannot answer) but stays out of scope.
- `docs/CONVENTIONS.md` — a behaviour change bumps the version and gets a CHANGELOG
  section; the canary and receipt procedure applies to 0.6.0 as a whole (SPEC 008).
- `plugin/README.md` — holds the section map, the language contract and the configuration
  keys; the map moves out, the README links to it, and the sentence claiming nothing is
  read from the plugin at run time is replaced.

## Scope

- The section map moves out of `plugin/README.md` into `plugin/templates/sections.md`
  (the table alone, plus the severity table if it belongs with it — the planner decides);
  the README links to it; the map-to-template parity test follows the file.
- `idea` reads `templates/SPEC.<language>.md` and `plan` reads `templates/PLAN.<language>.md`
  with `Read` from the plugin's directory, for the current `language`; the inline template
  blocks are removed, with their byte-for-byte test replaced.
- Every stage skill (`idea`, `plan`, `plan-review`, `implement`, `final-review`, `ship`)
  reads `templates/sections.md` with `Read` before it looks for a section.
- A failed read stops the stage: under `/pipeline:ship` with `RESULT: ESCALATE` naming the
  file and the missing rule; in an interactive `idea` or `plan`, a stop with the same
  message to the owner.
- The allow rule `Read(~/.claude/plugins/cache/<marketplace>/pipeline/**)` in
  `plugin/templates/settings.json` (marketplace substituted by `/pipeline:init` like the
  existing placeholder) and in this repository's `.claude/settings.json` (`wcz-tools`).
- The guard warns once per session when no settings file it can read (user, project,
  project-local) holds a `Read` allow rule covering the directory the guard itself runs
  from — the install cache or a `--plugin-dir` clone — and the warning names the exact rule
  to add. The owner sees it in the terminal and the model gets it in its context.
- `plugin/docs/INSTALL.md` and `docs/CONVENTIONS.md` (canary): the rule, where it goes,
  the user-settings alternative, and the rule a `--plugin-dir` canary needs.
- A new eval case, the mirror of `plan-review-escalates-on-dependency`: a consumer with
  `"language": "pl"` and the allow rule, a Polish SPEC whose `## Decyzje właściciela`
  accepts a new dependency, a PLAN that adds it — `plan-review` approves without
  escalating.
- Version 0.6.0 in `plugin/.claude-plugin/plugin.json`, a `## 0.6.0` CHANGELOG section
  with a consumer-impact line (add the rule, or the stages stop); SPEC 008 extends the same
  unreleased section.
- A `docs/DECISIONS.md` row reversing the 2026-09-23 inline-template decision; the
  roadmap item ticked with a link to this spec.

## Out of scope

- Translating skills, agents, tests and eval criteria into English — SPEC 008 (Stage 8,
  second 0.6.0 item). The skills here stay Polish and may still name the Polish headings
  where they name them today; only the templates and the map move out.
- The eval receipt for the release and the canary on the Polish consumer — SPEC 008,
  once `plugin/` is final.
- Calling `workflow_metrics.py` by name only (`docs/BACKLOG.md` P2) — stays in the backlog
  with its trigger; a translation-free spec should not change unrelated skill behaviour.
- A rule supplied only through `claude --settings` or managed policy: the guard cannot see
  it and may warn falsely; documented as a known limit, not detected.
- `/pipeline:init` reading its `CLAUDE.*.md` and `docs/*` templates: it runs in the main
  session with the owner present and keeps copying them as today.

## Requirements and acceptance criteria

- [ ] AC1: `plugin/templates/sections.md` exists and holds every row of today's section map
  (key, document, Polish literal, English literal) unchanged; `plugin/README.md` has no
  section-map table and no Polish letter anywhere, and links to the file.
- [ ] AC2: the parity tests (each template pair has the same structure through the map;
  every map row occurs in its template; keys unique per document) parse
  `templates/sections.md` and pass; removing a row from it makes them fail.
- [ ] AC3: `idea` and `plan` contain no inline SPEC/PLAN template block; each names the
  template it reads by a path under `${CLAUDE_PLUGIN_ROOT}/templates/`, chosen by
  `language` (`en` for a missing or unsupported value), and says to use `Read` — pinned by a
  test.
- [ ] AC4: all six stage skills say to read `${CLAUDE_PLUGIN_ROOT}/templates/sections.md`
  with `Read` and no longer point at the README for the map — pinned by a test.
- [ ] AC5: every stage skill (and the stage contract in `plugin/agents/*.md`, if that is
  where the escalation rule lives) says that a failed read of a template or the map ends
  the stage with `RESULT: ESCALATE` naming the file and the rule, and that interactive
  `idea`/`plan` stop with the same message — pinned by a test.
- [ ] AC6: `plugin/templates/settings.json` allows
  `Read(~/.claude/plugins/cache/<marketplace>/pipeline/**)` with the same placeholder as
  its marketplace entry, and `/pipeline:init` fills both with one value; this repository's
  `.claude/settings.json` holds the rule with `wcz-tools`.
- [ ] AC7: with no settings file holding a `Read` allow rule that covers the guard's own
  plugin directory, the first guarded Bash call of a session produces a warning naming the
  exact rule to add; the call itself is not blocked; a second call in the same session does
  not warn again.
- [ ] AC8: the warning of AC7 reaches both the owner (visible in the terminal without
  verbose mode) and the model (in the context of the session or subagent that made the
  call). The planner confirms the hook output channel that delivers both on the current
  Claude Code, and records the measurement.
- [ ] AC9: no warning when the rule is present in any of user settings
  (`~/.claude/settings.json`), project settings (`.claude/settings.json`) or project-local
  settings (`.claude/settings.local.json`), in the cache form (`~/…`) or, for a
  `--plugin-dir` clone, in an absolute form covering the clone's plugin directory. The
  warning's suggested rule for a clone uses the form Claude Code reads as absolute
  (`//…`), not a settings-relative `/…`.
- [ ] AC10: an unreadable or malformed settings file neither blocks nor crashes the guard;
  it counts as holding no rule.
- [ ] AC11: measured once, headless, as the roadmap probe was: a stage subagent with the
  rule reads a template from the install cache (or the clone, with the clone rule) without
  a prompt, and without the rule the read is refused. The result is recorded in the PLAN.
- [ ] AC12: new eval case (`plan-review` approves on a Polish `## Decyzje właściciela`):
  passes 5 of 5 on the default model within the $8 ceiling for the spec's eval spend;
  its scaffold writes the allow rule, and removing the rule from the scaffold makes it fail
  (checked once, manually, and recorded).
- [ ] AC13: smoke run of `plan-review-escalates-on-dependency`,
  `implement-escalates-on-failing-test` and `final-review-finds-planted-defect` on the
  changed skills: each passes (a single failure of the known-flaky
  `plan-review-escalates-on-dependency` is re-run once before it counts), within the same
  $8 ceiling.
- [ ] AC14: `plugin/.claude-plugin/plugin.json` is `0.6.0`; `plugin/CHANGELOG.md` has a
  `## 0.6.0` section with a consumer-impact line telling existing consumers to add the rule
  to `.claude/settings.json` (or user settings), and what happens without it.
- [ ] AC15: `plugin/docs/INSTALL.md` documents the rule, project versus user settings, and
  the absolute clone rule for a `--plugin-dir` session; `docs/CONVENTIONS.md`'s canary
  procedure includes that clone rule.
- [ ] AC16: `docs/DECISIONS.md` has a new row: templates and the section map are read
  at run time with `Read` behind a narrow allow rule, reversing the 2026-09-23 inline
  decision, with the probe as the evidence and inline templates as the rejected
  alternative; the Stage 8 item in `docs/ROADMAP.md` is ticked with a link to this spec.
- [ ] AC17: `bash scripts/check.sh` is green.

## Decisions and rejected alternatives

| Decision | Rejected alternatives | Rationale |
|----------|-----------------------|-----------|
| Stage 8's 0.6.0 is two specs, one release: 007 (run-time reads), 008 (translation) | one spec for both items; two releases 0.6.0 and 0.7.0 | The mechanism and a one-to-one translation carry different risks, and a regression should point at one of them; the receipt and the canary must see the final `plugin/`, so they run once, in 008 |
| The mirror eval case lands in 007 | in 008 with the translation | It tests this spec's mechanism (the rule and the map read from a file); 008's receipt then re-runs it on the translated skills |
| The guard checks for a rule covering its own directory | checking the cache path only; documentation without a warning | The guard knows where it runs, so the same check covers a `--plugin-dir` canary with no extra procedure |
| The warning goes to both the owner and the model | stderr only, like the missing-config warning | A stage subagent that sees it can escalate instead of calling `Read` and stalling on a prompt nobody can answer |
| The rule goes into project settings (template, `init`, this repository); user settings documented as an alternative | user settings only | The rule travels with the repository, and a fresh machine works without an extra step |
| Stages stop on a failed read | falling back to a built-in template or heading | A missing template is visible anyway, but a missing map would silently miss `## Decyzje właściciela` and escalate on an accepted dependency |

## Owner decisions

- New dependency: none; the guard stays on the standard library.
- Data migration: none. Existing consumers change a settings file by hand (one allow rule),
  announced in the 0.6.0 consumer-impact line — accepted.
- Eval spend for this spec: up to $8 (the new case 5 times, smoke runs of three existing
  stage cases, drafting on Sonnet) — accepted.
- The release receipt and the canary are not part of this spec; they run in SPEC 008.

## Open questions (non-blocking)

- Whether the severity table moves into `templates/sections.md` together with the map or
  stays in the README — the planner decides; either way no Polish is left in the README.
