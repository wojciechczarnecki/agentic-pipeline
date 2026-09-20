---
status: implemented
metrics:
  started_at: "2026-09-20T12:30"
  escalations: 1
  plan_steps: 11
  plan_review_blockers: 1
  plan_review_majors: 5
  plan_changes: 19
  implement_steps: 11
  implement_iterations: 3
  deviations: 3
stage_history:
  - "spec-draft — 2026-09-20"
  - "spec-ready — 2026-09-20"
  - "plan-draft — 2026-09-20"
  - "plan-approved — 2026-09-20"
  - "implemented — 2026-09-20"
---

# SPEC 001 — Rules where the agent executes them, and install instructions that match reality

## Goal

A pipeline rule is followed when it is either named in the skill the stage executes or
checked by a program; a rule that lives only in prose someone else reads is not followed.
This spec moves the metrics rules into every stage skill, backs them with a machine check,
puts the stage contract where the harness loads it without a tool read, slims the prose
that has already drifted, and makes the install instructions produce a consumer
configuration that needs no SSH key and does not silently follow `main`. Success: the
metrics report has no holes for specs produced after this release, the stage skills carry
roughly 80 fewer lines into every stage's context, and a freshly initialised project gets
a marketplace entry pinned to a release tag.

## Context

Evidence from the only consumer today (an application repository pinned to
`pipeline--v0.2.0`), across 9 specs carrying a `metrics:` block:

- rules named in a SKILL.md are executed — metric keys correct 9/9; the "Context read"
  section, added as an `idea` guardrail in 0.2.0, present 2/2 since;
- rules living only in `plugin/README.md` are not — the value format (quoted timestamps)
  held in 2 of 9, `escalations` missing in 2 of 9, and nothing watches counter
  consistency: one spec reports 18 findings and 19 decisions;
- prose in `plugin/skills/plan/SKILL.md` mentioning `escalations` did not save it either.

The cause is therefore not "the rule sits in the wrong file" but "the rule is prose that
nothing checks". No new rules file (`RULES.md` or similar) is created.

State of the code this spec touches:

- `plugin/bin/workflow_metrics.py` — `COUNTERS` (13 counters), `TIME_FORMAT`
  `"%Y-%m-%dT%H:%M"`, `parse_metrics()` already strips surrounding quotes
  (`.strip("\"'")`), so unquoted timestamps already parse; the script has no flags today
  and always renders the report.
- `plugin/skills/*/SKILL.md` — six stage skills repeat a "Konfiguracja projektu" section
  (~50 lines) that has already drifted: `plan-review` omits `worktree`, `final-review`
  omits `worktree` and `migrations`. Visual-artifact prose is spread over
  `plan` (lines 59–62, 113–114), `plan-review` (46–47), `implement` (60–67),
  `final-review` (50–52) and `plugin/agents/implementer.md`.
- `plugin/skills/ship/SKILL.md` — "Kontrakt agenta etapu" points at `plugin/README.md`
  as the normative source of the metrics format (line 74–75); all four
  `plugin/agents/*.md` instruct the agent to read `plugin/skills/ship/SKILL.md`, a path
  outside the session's working directory, which `plugin/skills/init/SKILL.md` itself
  warns may be blocked or waiting for a consent a stage agent can never obtain.
- `plugin/templates/settings.json` — emits `"source": "github"` (SSH) with no `ref`,
  contradicting `docs/DECISIONS.md` (git + HTTPS) and `plugin/README.md`.
- `plugin/bin/guard.py` — `DB_COMMANDS = {upgrade, downgrade, stamp, revision, current,
  check}` and the variables `ENVIRONMENT`, `DATABASE_URL`, `DB_HOST` are hardcoded; only
  `migrations.command` and `migrations.localHosts` come from configuration.
- Test precedent: `plugin/tests/test_init_skill.py` pins a skill's contract through the
  identifiers it must name, explicitly not through its prose.

## Context read

- `docs/ROADMAP.md` — Stage 1 is complete; this is the first item of the next stage. The
  roadmap has no entry for it yet, so one is added under Stage 2 alongside the spec link.
- `docs/PROJECT.md` — touches the functional requirements "stage skills and agents",
  "`init` scaffolds a consumer project" and "command guard"; the non-functional
  requirements that bind here are plain `python3` with no runtime dependencies, project
  and domain independence, and `claude plugin validate --strict`.
- `docs/DECISIONS.md` — binding: consumers install over git + HTTPS, not the `github`
  (SSH) source (2026-09-17); the release-tag pin is inert until the marketplace is
  re-registered with that `ref` (2026-09-17); the version grows with behaviour and the
  owner tags releases. The settings template contradicts the first of these — this spec
  aligns the template to the decision, it does not change the decision.
- `docs/CONVENTIONS.md` — "Test mechanisms, not the prose of skills" governs the new
  structural tests: they pin identifiers, not sentences. Line length 100, ruff `E,F,I,B,N`,
  no docstrings, runtime code standard library only, one branch per task, squash merge,
  semantic version in `plugin/.claude-plugin/plugin.json` with a CHANGELOG section.
- `docs/BACKLOG.md` — this spec closes two items whose triggers have fired: "Releases /
  document release pinning for consumers" (P3) and "Init / cover the cap on the first
  question round with a grader" (P3, triggered by any change to the `init` skill). The
  remaining `init` items (unsubstituted `<gitHooksDir>` in the copied `pre-push`, CI
  generator for other stacks) stay out of scope and keep their triggers.
- `plugin/README.md` (domain document from the map in `CLAUDE.md`) — holds the metrics
  block, the configuration key table, the `RESULT` contract and the guard description. It
  stays the human-facing description; after this spec it is no longer quoted by any skill
  as the source of a rule, and it gains the marketplace-registration caveat, the `ref` in
  the install example and one sentence on the migration module's real reach.

## Scope

1. **Metrics format inside every stage skill.** The closing step of each stage skill
   (`plan`, `plan-review`, `implement`, `final-review`, and `ship` step 3) states the
   format in two lines: flat `metrics:` block, integer counters, timestamps
   `%Y-%m-%dT%H:%M`, `escalations` present from the start. The normative reference to
   `plugin/README.md` disappears from `plugin/skills/ship/SKILL.md`.
2. **`workflow_metrics.py --check <spec-dir>`.** Verifies the complete set of keys due for
   the status reached, parsable timestamps, and the consistency
   `findings_accepted + findings_rejected == final_review_blockers +
   final_review_worth_fixing + final_review_nits`. Exit code 1 with a readable message
   naming every key and condition that failed. Stage closing steps run it; `final-review`
   in `apply` mode gates on it. A failure the stage cannot repair itself becomes
   `RESULT: ESCALATE` (or a STOP with a question in a standalone session).
3. **Stage contract where the harness already loads it.** The literal text of "Kontrakt
   agenta etapu" and "Wyzwalacze eskalacji" moves into all four `plugin/agents/*.md`; a
   test pins those copies to `plugin/skills/ship/SKILL.md` character for character. The
   agents stop instructing a read of `plugin/skills/ship/SKILL.md`.
4. **Slimming the prose that drifts.** The repeated "Konfiguracja projektu" section
   collapses to two lines in all six stage skills; the visual-artifact prose collapses to
   one imperative sentence, conditional on a UI scope in `verify.scopes` and delegating
   details to `<docs.conventions>`.
5. **Install and release pinning.** `plugin/templates/settings.json` emits a git + HTTPS
   source with a visible `ref` TODO; `plugin/README.md` shows `ref` in the declarative
   example and states the marketplace-registration caveat; `pipeline:init` substitutes the
   marketplace name and `ref` derived from `${CLAUDE_PLUGIN_ROOT}`, or leaves a TODO.
6. **Honest scope of the migration module.** One row in `docs/DECISIONS.md` and one
   sentence in `plugin/README.md` → "Strażnik komend".
7. **Release 0.3.0** — version bump plus a `plugin/CHANGELOG.md` section containing a
   "wpływ na konsumenta" line.
8. **Structural tests and one eval grader** covering points 1, 3, 4 and the `init`
   question cap.

## Out of scope

- A new rules file (`RULES.md`) or any new home for rules — explicitly rejected above.
- Generalising the migration module beyond Alembic's verbs and variables (point 6 records
  the limitation instead). Stays in `docs/BACKLOG.md` under Guard, trigger: the first
  consumer using another migration tool.
- Backfilling the metrics of specs that predate the checker — the escalation path from
  point 2 hands that to the owner, spec by spec.
- Moving this repository's own pin to `pipeline--v0.3.0` in `.claude/settings.json` and
  `CLAUDE.md`: the tag does not exist until the owner creates it after the merge. Follows
  as the owner's step, recorded in the PR description.
- Translating skills and agents into English (`docs/BACKLOG.md`, P2, unchanged trigger).
- The remaining `init` backlog items (`<gitHooksDir>` in the copied `pre-push`, CI
  generator for other stacks).

## Requirements and acceptance criteria

**Metrics rules in the skills**

- [ ] AC1: Each of `plan`, `plan-review`, `implement`, `final-review` states in its closing
      step: the flat `metrics:` block, integer counters, the timestamp format
      `%Y-%m-%dT%H:%M`, and the keys that stage writes.
- [ ] AC2: `plugin/skills/ship/SKILL.md` contains no reference to `plugin/README.md` as the
      source of the metrics format; `ship` step 3 keeps writing `started_at` and
      `escalations: 0` and states the format in the same two lines.
- [ ] AC3: A structural test asserts, for every stage skill, that its text names
      `metrics:`, the timestamp format and each metric key that stage owns; and that no
      stage skill points at `README` for the metrics format.

**The checker**

- [ ] AC4: `python3 workflow_metrics.py --check <spec-dir>` exits 0 and prints nothing on a
      spec whose `metrics:` block is complete for its status.
- [ ] AC5: Timestamps parse both quoted (`started_at: "2026-09-15T09:00"`) and unquoted
      (`started_at: 2026-09-15T09:00`); a spec with unquoted timestamps passes the check.
- [ ] AC6: A timestamp that does not match `%Y-%m-%dT%H:%M` (e.g. `2026-09-15 09:00`)
      exits 1 with a message naming the key and the expected format.
- [ ] AC7: A counter that is not a non-negative integer (empty, `two`, `3.5`, `-1`) exits 1
      naming the key.
- [ ] AC8: Given `findings_accepted + findings_rejected !=
      final_review_blockers + final_review_worth_fixing + final_review_nits`, the check
      exits 1 with a message showing both sums. The invariant is evaluated only once all
      five counters are present.
- [ ] AC9: The keys due per status are exactly: `plan-draft` → `started_at`, `escalations`,
      `plan_steps`; `plan-approved` → the above plus `plan_review_blockers`,
      `plan_review_majors`, `plan_changes`; `implemented` → the above plus
      `implement_steps`, `implement_iterations`, `deviations`; `done` → every key in
      `COUNTERS` plus `started_at` and `finished_at`. At `spec-draft` and `spec-ready`
      nothing is due and the check exits 0.
- [ ] AC10: A missing key exits 1 with a message naming every missing key and the status
      that made it due — the message is enough for the stage to raise an escalation
      without reading the code.
- [ ] AC11: A spec directory with no `SPEC.md`, or a `SPEC.md` with no frontmatter, exits 1
      with a message saying so — never a traceback.
- [ ] AC12: `--check` changes nothing about the default invocation: without the flag the
      script still prints the report and exits 0 (existing tests stay green).

**The checker inside the pipeline**

- [ ] AC13: The closing step of every stage skill runs `--check` on the spec directory
      before it reports success.
- [ ] AC14: `final-review` in `apply` mode does not set `done` while `--check` exits 1.
- [ ] AC15: The skills state that a `--check` failure the stage cannot repair from its own
      artifacts ends the stage with `RESULT: ESCALATE` (in `/pipeline:ship`) or a STOP with
      a question to the owner (standalone), naming the missing keys; the agent never
      invents a value it did not measure.

**Stage contract**

- [ ] AC16: Each of `plugin/agents/{planner,plan-reviewer,implementer,reviewer}.md`
      contains the literal text of "Kontrakt agenta etapu" and "Wyzwalacze eskalacji".
- [ ] AC17: A test asserts those sections are character-identical to the corresponding
      sections of `plugin/skills/ship/SKILL.md`; a change to one side alone fails CI.
- [ ] AC18: No file in `plugin/agents/` instructs reading `plugin/skills/ship/SKILL.md`
      (or the `ship` skill) to learn the contract.

**Slimmed prose**

- [ ] AC19: In all six stage skills the "Konfiguracja projektu" section is at most two
      lines: read `.claude/workflow.json`, and `<key>` means the value from it. The key
      table exists only in `plugin/README.md`.
- [ ] AC20: The two-line section keeps the fallback the `idea` and `ship` skills have
      today: no file → defaults from the plugin README and a suggestion to run
      `/pipeline:init`.
- [ ] AC21: Visual artifacts, wide and narrow views and the review scenario are described
      by one sentence per skill, in the imperative (an order such as "run … and look at
      …", never "consider" or "it is worth"), conditional on a UI scope being present in
      `verify.scopes`, and referring to `<docs.conventions>` for the details. The sentence
      appears in `plan`, `plan-review`, `implement`, `final-review` and
      `plugin/agents/implementer.md`.
- [ ] AC22: A structural test asserts each of those five files names `verify.scopes` and
      `<docs.conventions>` in that sentence, and that no stage skill still enumerates
      required views of its own.
- [ ] AC23: The configuration and visual-artifact prose in `plugin/skills/*/SKILL.md`
      loses at least 50 lines gross, and the six stage skills shrink by at least 12 lines
      net against `main`; no rule named in AC1–AC22 is lost in the process.
      (Owner decision, 2026-09-20 — see "Owner decisions".)

**Install and pinning**

- [ ] AC24: `plugin/templates/settings.json` declares `"source": "git"` with an
      `https://` URL and a `ref`; all three values stay visible `TODO` placeholders, so
      `plugin/tests/test_init_templates.py::test_settings_template_names_no_marketplace_of_its_own`
      stays green.
- [ ] AC25: The declarative example in `plugin/README.md` → "Instalacja" carries
      `"ref": "pipeline--vX.Y.Z"` and one sentence explaining that without `ref` the
      consumer follows `main`.
- [ ] AC26: `plugin/README.md` states that the pin only takes effect once the marketplace
      is registered with that `ref`, that a marketplace registered earlier without one
      keeps tracking `main`, and gives the commands to re-register plus the check
      (`git -C ~/.claude/plugins/marketplaces/<name> log --oneline -1`).
- [ ] AC27: `pipeline:init` substitutes into the generated `.claude/settings.json` the
      marketplace name and `"ref": "<plugin>--v<version>"` read from the
      `${CLAUDE_PLUGIN_ROOT}` path (`…/<marketplace>/<plugin>/<version>/`); when the path
      does not have that shape it leaves `TODO:` and lists it among the values to fill in.
- [ ] AC28: `plugin/tests/test_init_skill.py` asserts the `init` skill names the `ref`
      substitution and its `TODO:` fallback.
- [ ] AC29: A new eval case in `plugin/evals` grades that `init`'s first question round is
      a single round of at most 4 questions, with a second round only when stack detection
      failed.

**Migration module honesty**

- [ ] AC30: `docs/DECISIONS.md` gains a row stating that the migration module recognises
      only Alembic's verbs (`upgrade`, `downgrade`, `stamp`, `revision`, `current`,
      `check`) and the variables `ENVIRONMENT`, `DATABASE_URL`, `DB_HOST`, that only
      `migrations.command` and `migrations.localHosts` are configurable, and that it is
      deliberately not generalised.
- [ ] AC31: `plugin/README.md` → "Strażnik komend" states the same in one sentence, so a
      project on another migration tool cannot mistake the guard's silence for protection.

**Release**

- [ ] AC32: `plugin/.claude-plugin/plugin.json` is at `0.3.0` and `plugin/CHANGELOG.md` has
      a `## 0.3.0` section containing a line labelled "wpływ na konsumenta" that names what
      the consumer must do on upgrade (re-register the marketplace with the new `ref`; old
      specs may escalate once over missing metric keys).
- [ ] AC33: `bash scripts/check.sh` is green (`claude plugin validate --strict` for the
      plugin and the marketplace, ruff, black, pytest).
- [ ] AC34: No new runtime or dev dependency appears in `pyproject.toml` or `uv.lock`, and
      nothing in `plugin/` imports outside the standard library.
- [ ] AC35: `plugin/tests/test_no_domain_references.py` stays green — naming Alembic
      describes the guard's own code, not a consumer project.

**Consumer safety net**

- [ ] AC36: Every behaviour the consumer relies on today survives: the UI sentence stays an
      order, the metrics keys are unchanged (no key added, removed or renamed), the config
      keys are unchanged, and the guard's verdicts are unchanged (`plugin/tests/test_guard.py`
      untouched and green).
- [ ] AC37: Resuming a stage on a consumer spec that has unquoted timestamps does not fail
      the check (AC5); a consumer spec missing `escalations` produces the named escalation
      from AC15, not a crash and not a fabricated `0`.

## Decisions and rejected alternatives

| Decision | Rejected alternatives | Rationale |
|---|---|---|
| No new home for rules; the rule goes into the skill that executes it and into a checker | `RULES.md` shared by all skills; keeping the rules in `plugin/README.md` | The measured failure is prose nothing checks, not prose in the wrong file; a new file would add a third place to drift |
| `--check` demands the complete set of keys due for the status reached | checking only the current stage's keys, with older gaps as warnings | The report's holes are the point of the spec; a warning reproduces exactly today's outcome |
| A check failure the stage cannot repair becomes an escalation | the agent backfilling missing keys (`0` when unknown); a leniency window keyed on `stage_history` dates | A fabricated metric is worse than a visible gap, and the pipeline already has an escalation path; a date-keyed window is a rule that itself needs remembering |
| The stage contract lives in `plugin/agents/*.md`, pinned to `ship` by a test | `ship` pasting the literal text into the agent's prompt; leaving the read instruction in place | Agent files are loaded by the harness with no tool read, which removes the cause; and a test can verify a file, while nothing can verify what an orchestrator pasted |
| Regression cover is structural tests over identifiers in `SKILL.md` | eval graders only; no cover beyond the checker | `docs/CONVENTIONS.md` mandates testing mechanisms rather than prose, and `plugin/tests/test_init_skill.py` is the precedent; evals run a real model and are manual |
| `init` derives `ref` from the `${CLAUDE_PLUGIN_ROOT}` path, falling back to `TODO:` | always leaving `TODO:`; asking the owner a fifth question | The path carries the marketplace and version, and `<plugin>--vX.Y.Z` is the tag convention recorded in `docs/DECISIONS.md`; always-TODO would ship every new project with the very defect this spec closes |
| The template keeps visible `TODO` placeholders for marketplace, URL and `ref` | shipping this repository's real marketplace in the template | A non-existent or foreign source would fail silently in every initialised project (`test_settings_template_names_no_marketplace_of_its_own`) |
| The migration module stays Alembic-shaped and says so | generalising verbs and variables through configuration | The owner uses Alembic; an honest limitation beats an abstraction nobody exercises |

## Owner decisions

- No new dependency, runtime or dev — `--check` is built on the standard library
  (`argparse`/`re`/`datetime`), tests go into the existing pytest suite, the eval grader is
  Markdown. Approved up front.
- No data migration. Metric blocks of existing specs are changed by the owner through the
  escalation path, never by an agent on its own.
- `--check` is strict: the complete key set due for the status reached, with escalation
  rather than backfilling when a spec predates the checker.
- The stage contract is duplicated into the agent files, with a test pinning it to
  `plugin/skills/ship/SKILL.md`.
- Regression cover: structural tests over identifiers, plus the one eval grader for the
  `init` question cap.
- `init` derives `ref` from the plugin cache path, `TODO:` otherwise.

### 2026-09-20 — plan stage

- **AC23 line threshold.** Question: the 70-line shrink of `plugin/skills/*/SKILL.md`
  is unreachable — removable prose measures 59 lines gross, while the same spec adds
  ~44 lines (AC1, AC2, AC13, AC15 and the AC19–AC21 replacements), leaving ~15 net; the
  only blocks large enough to close the gap are pinned by AC17 or protected by AC36.
  Decision: restate AC23 as "the configuration and visual-artifact prose in
  `plugin/skills/*/SKILL.md` loses at least 50 lines gross, and the six skills shrink by
  at least 12 lines net against `main`; no rule named in AC1–AC22 is lost." The goal
  (less context carried into every stage) and the machine-checkable measurement both stay.
- **AC19 "at most two lines".** Question: two physical lines would run past the
  100-column convention. Decision: read it as two wrapped bullets — the structural test
  counts bullets, not physical lines.

## Open questions (non-blocking)

- Whether `--check` should also be wired into `bash scripts/check.sh` for this
  repository's own specs once more than one spec exists here. Today the stage steps cover
  it; a CI gate can follow when it pays off.
- Whether the consumer's 9 existing specs are worth backfilling by hand after the upgrade,
  or whether the report simply starts clean from the specs that follow.
