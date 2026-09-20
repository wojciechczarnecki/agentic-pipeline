# PLAN 001 — Rules where the agent executes them, and install instructions that match reality

## Owner summary

- **Approach:** Every rule this spec touches lands in the file the harness already loads for
  the agent that must obey it, and gets a program or a structural test behind it. The metrics
  format moves into each stage skill's closing step and is backed by
  `workflow_metrics.py --check`; the stage contract is duplicated into `plugin/agents/*.md`
  and pinned character for character to `plugin/skills/ship/SKILL.md` by a test; the
  configuration and visual-artifact prose collapses to a fixed short block that a test
  measures. The install template, `plugin/README.md` and `pipeline:init` are aligned with
  the git + HTTPS + `ref` decision already recorded in `docs/DECISIONS.md`.
- **Main risks:** the AC23 line budget is tight (≈59 lines removable against ≈41 added), so
  step 6 measures it explicitly and tightens wording before the release step; the AC17 test
  makes `ship` and the four agent files a single unit that must always be edited together.
- **New dependency:** no — `argparse`, `re`, `datetime` and `pathlib` are standard library;
  no dev tool is added (confirmed in SPEC → "Owner decisions").
- **Data migration:** no — no metric block of an existing spec is rewritten by an agent; old
  specs reach the owner through the escalation path (SPEC → "Owner decisions").
- **Manual scenarios for the owner:** 2 — tagging and re-registering the marketplace at
  `pipeline--v0.3.0` after the merge, and the manual `plugin-eval` run of the new `init`
  question-cap case (a real model, out of CI by decision).

## Approach

The spec's own diagnosis drives the shape: a rule is followed when it is named in the file
the executing agent loads, or checked by a program. So each change has two halves — the text
in the loaded file, and a mechanism.

**The checker.** `plugin/bin/workflow_metrics.py` already parses the `metrics:` block
(`parse_metrics`, quote-stripping included) and knows `COUNTERS` and `TIME_FORMAT`. `--check`
reuses both and adds only a `status` reader and a table of keys due per status; the report
path is untouched, so AC12 holds by construction. Errors go to stderr, like the existing
`workflow.json:` error in `main()`; exit 0 with empty output is the success signal (AC4).
Argument shape: `--check` as a flag plus the existing optional positional directory, so
`workflow_metrics.py --check <spec-dir>` parses exactly as AC4 writes it and no existing
invocation changes.

**Structural tests over identifiers.** The precedent is
`plugin/tests/test_init_skill.py` (its comment at line 29 states the rule: pin the
identifiers the skill must name, never its prose). Two new files follow it:
`plugin/tests/test_stage_contract.py` (the `ship` ↔ agents pinning) and
`plugin/tests/test_stage_skills.py` (metrics format, configuration block, visual sentence).
Both reuse the `section()` / `step()` helper shape from `test_init_skill.py` rather than
inventing another parser.

**One canonical configuration block.** Instead of six drifting paragraphs, one three-line
block is pasted verbatim into all six stage skills, and the test asserts the six copies are
byte-identical. Drift then fails CI instead of accumulating. Per the owner's decision of
2026-09-20 the "at most two lines" of AC19 is read as two bullets, and the test counts
bullets.

**One canonical visual sentence.** The same trick, four skills plus
`plugin/agents/implementer.md`: an imperative sentence conditional on a UI scope in
`verify.scopes`, delegating the list of required views to `<docs.conventions>`. This project
has no `verify.scopes`, so the sentence is inert here — that is intended; it is the
consumer's rule.

**The contract in the agent files.** `plugin/agents/*.md` are loaded by the harness with no
tool read, which removes the failure cause named in the spec. The test extracts the two
sections from `plugin/skills/ship/SKILL.md` by heading and asserts each block appears
verbatim in each of the four agent files.

**Install and pinning** are text changes plus assertions in the two existing template/skill
test files; nothing about the marketplace name of this repository enters the template, so
`test_settings_template_names_no_marketplace_of_its_own` stays green (AC24).

Reused patterns, with paths:

- `plugin/tests/test_init_skill.py:33-41` — `step()` and `section()` extraction helpers.
- `plugin/tests/test_workflow_metrics.py:5-8` — loading the script as a module through
  `importlib.util.spec_from_file_location`, alongside subprocess runs for the CLI contract.
- `plugin/bin/workflow_metrics.py:33-46` — `parse_metrics()`, reused by `--check` unchanged.
- `plugin/evals/init-without-questions/` — the `case.yaml` + `graders/criteria.md` shape for
  the new eval case.

## AC → steps matrix

| AC | Steps | Proving test |
|----|-------|----------------|
| AC1 | 5 | `test_stage_skills.py::test_closing_step_states_the_metrics_format` |
| AC2 | 2, 5 | `test_stage_skills.py::test_no_stage_skill_sends_metrics_rules_to_the_readme`, `test_stage_contract.py::test_the_contract_states_the_metrics_format` |
| AC3 | 5 | `test_stage_skills.py::test_closing_step_states_the_metrics_format`, `::test_no_stage_skill_sends_metrics_rules_to_the_readme` |
| AC4 | 1 | `test_workflow_metrics.py::test_check_is_silent_on_a_complete_spec` |
| AC5 | 1 | `test_workflow_metrics.py::test_check_accepts_unquoted_timestamps` |
| AC6 | 1 | `test_workflow_metrics.py::test_check_rejects_a_malformed_timestamp` |
| AC7 | 1 | `test_workflow_metrics.py::test_check_rejects_a_non_integer_counter` |
| AC8 | 1 | `test_workflow_metrics.py::test_check_reports_unbalanced_findings`, `::test_the_balance_needs_all_five_counters` |
| AC9 | 1 | `test_workflow_metrics.py::test_keys_due_per_status`, `::test_early_statuses_require_nothing` |
| AC10 | 1 | `test_workflow_metrics.py::test_missing_keys_are_named_with_the_status` |
| AC11 | 1 | `test_workflow_metrics.py::test_a_directory_without_a_readable_spec_fails_cleanly` |
| AC12 | 1 | `test_workflow_metrics.py::test_report_skips_legacy_specs_and_computes_ratios` (existing), `::test_empty_specs_dir_reports_missing_metrics` (existing) |
| AC13 | 5 | `test_stage_skills.py::test_closing_step_runs_the_checker` |
| AC14 | 5 | `test_stage_skills.py::test_apply_mode_gates_done_on_the_checker` |
| AC15 | 5 | `test_stage_skills.py::test_closing_step_names_the_escalation_path` |
| AC16 | 2 | `test_stage_contract.py::test_every_agent_carries_the_contract` |
| AC17 | 2 | `test_stage_contract.py::test_every_agent_carries_the_contract` (verbatim comparison) |
| AC18 | 2 | `test_stage_contract.py::test_no_agent_sends_the_reader_to_the_ship_skill` |
| AC19 | 3 | `test_stage_skills.py::test_the_configuration_block_is_two_bullets_everywhere` |
| AC20 | 3 | `test_stage_skills.py::test_the_configuration_block_keeps_the_fallback` |
| AC21 | 4 | `test_stage_skills.py::test_the_visual_sentence_is_one_imperative_sentence` |
| AC22 | 4 | `test_stage_skills.py::test_the_visual_sentence_is_one_imperative_sentence`, `::test_no_stage_skill_enumerates_views` |
| AC23 | 3, 4, 5, 6 | step 6 measurement command recorded in "End-to-end verification"; `test_stage_skills.py::test_the_configuration_block_is_two_bullets_everywhere` guards the shrink from regrowing |
| AC24 | 7 | `test_init_templates.py::test_settings_template_pins_a_git_https_source`, `::test_settings_template_names_no_marketplace_of_its_own` (existing) |
| AC25 | 7 | `test_readme.py::test_installation_pins_the_release_tag` |
| AC26 | 7 | `test_readme.py::test_installation_explains_the_marketplace_registration` |
| AC27 | 7 | `test_init_skill.py::test_the_marketplace_ref_is_derived_from_the_plugin_root` |
| AC28 | 7 | `test_init_skill.py::test_the_marketplace_ref_is_derived_from_the_plugin_root` |
| AC29 | 8 | `plugin/evals/init-question-cap/` (manual `plugin-eval`); `test_plugin_structure.py::test_every_eval_case_has_a_grader` |
| AC30 | 9 | `docs/` lies outside the plugin, so no pytest case may assert on it (`test_no_domain_references.py` scans `plugin/` only); the proof is step 9's `grep -n "Alembic" docs/DECISIONS.md`, its output recorded in the step |
| AC31 | 9 | `test_readme.py::test_the_guard_section_states_the_migration_scope` |
| AC32 | 10 | `test_readme.py::test_changelog_starts_at_the_manifest_version` (existing), `::test_the_changelog_names_the_consumer_impact` |
| AC33 | 11 | `bash scripts/check.sh` |
| AC34 | 11 | `test_no_domain_references.py` (existing) + the grep in step 11 |
| AC35 | 9, 11 | `test_no_domain_references.py` (existing) |
| AC36 | 11 | `test_readme.py::test_metrics_block_lists_every_counter` (existing), `test_workflow_config.py` (existing), `test_guard.py` (existing, untouched — verified by diff in step 11) |
| AC37 | 1 | `test_workflow_metrics.py::test_check_accepts_unquoted_timestamps`, `::test_missing_keys_are_named_with_the_status` |

## Steps

- [ ] 1. **`workflow_metrics.py --check <spec-dir>`** — files: `plugin/bin/workflow_metrics.py`,
      `plugin/tests/test_workflow_metrics.py`.
      Add, above `main()`:
      `REQUIRED: dict[str, list[str]]` keyed by status and cumulative —
      `spec-draft`/`spec-ready` → `[]`;
      `plan-draft` → `["started_at", "escalations", "plan_steps"]`;
      `plan-approved` → the above + `plan_review_blockers`, `plan_review_majors`,
      `plan_changes`; `implemented` → the above + `implement_steps`,
      `implement_iterations`, `deviations`; `done` → `["started_at", "finished_at", *COUNTERS]`.
      `TIMESTAMPS = ("started_at", "finished_at")`;
      `BALANCE = (("findings_accepted", "findings_rejected"),
      ("final_review_blockers", "final_review_worth_fixing", "final_review_nits"))`.
      New functions: `parse_status(text: str) -> str | None` (same frontmatter regex as
      `parse_metrics`, top-level `status:` key, quotes stripped) and
      `check(spec_dir: Path) -> list[str]` returning one message per failure, each prefixed
      with the spec directory name. Messages:
      missing keys → `status \`done\` requires metric keys that are missing: finished_at, deviations`;
      timestamp → `metrics.started_at "2026-09-15 09:00" does not match %Y-%m-%dT%H:%M`;
      counter → `metrics.plan_steps "two" is not a non-negative integer` (regex `^\d+$` on the
      stripped value — rejects empty, `two`, `3.5`, `-1`); balance → both sums spelled out,
      evaluated only when all five counters are present and integral; no `SPEC.md` →
      `no SPEC.md in <dir>`; no frontmatter → `<dir>/SPEC.md has no frontmatter`; unknown
      status → `<dir>/SPEC.md: unknown status "<value>"`. No exception escapes `check()`.
      `main()` switches to `argparse` with `--check` (`action="store_true"`) and the existing
      optional positional directory; with `--check` and no directory, print a usage message to
      stderr and return 1. With `--check`: print each message to stderr, return 1 if any,
      otherwise print nothing and return 0. Without `--check` the current behaviour is
      untouched.
      Tests (new, in the existing file, reusing its module-loading preamble and a
      `spec_dir(tmp_path, status, metrics)` helper that writes a minimal SPEC.md):
      `test_check_is_silent_on_a_complete_spec`, `test_check_accepts_unquoted_timestamps`,
      `test_check_rejects_a_malformed_timestamp`, `test_check_rejects_a_non_integer_counter`
      (parametrised over `""`, `two`, `3.5`, `-1`), `test_check_reports_unbalanced_findings`,
      `test_the_balance_needs_all_five_counters`, `test_keys_due_per_status` (parametrised
      over the four statuses), `test_early_statuses_require_nothing`,
      `test_missing_keys_are_named_with_the_status` (asserts the message names the status and
      every missing key, including the AC37 case of a spec missing only `escalations`),
      `test_a_directory_without_a_readable_spec_fails_cleanly` (missing file and
      frontmatter-less file; asserts `Traceback` not in stderr). At least one test runs the
      CLI as a subprocess on plain `python3` to pin the exit codes and the empty stdout.
      Automatic verification: `uv run pytest -q plugin/tests/test_workflow_metrics.py`;
      `python3 plugin/bin/workflow_metrics.py --check specs/001-executable-rules-and-release-pinning; echo "exit=$?"`
      (at this point the spec is `plan-draft` with `started_at`, `escalations` and
      `plan_steps` set → expected exit 0 and no output);
      `uv run ruff check plugin/bin/workflow_metrics.py && uv run black --check plugin/bin/workflow_metrics.py`

- [ ] 2. **Stage contract into the agent files** — files: `plugin/skills/ship/SKILL.md`,
      `plugin/agents/planner.md`, `plugin/agents/plan-reviewer.md`,
      `plugin/agents/implementer.md`, `plugin/agents/reviewer.md`,
      `plugin/tests/test_stage_contract.py` (new).
      In `plugin/skills/ship/SKILL.md` → "Kontrakt agenta etapu", replace the metrics bullet
      (today: "format opisany w README pluginu, sekcja „Metryki workflow"") with the format
      itself, in two lines: flat `metrics:` block, integer counters, timestamps
      `%Y-%m-%dT%H:%M`, `escalations` present from the start — no reference to README (AC2).
      Then copy both sections ("## Kontrakt agenta etapu" and "## Wyzwalacze eskalacji
      (wiążące dla wszystkich agentów)"), heading line included, verbatim to the end of each
      of the four agent files, and delete from each agent file the sentence ordering a read of
      the `ship` skill, keeping the agent-specific remainder ("Zamiast sekcji „Handoff"…
      kończysz blokiem RESULT" and the `METRICS tego etapu:` line).
      Also update `ship` step 3 so it states the same two-line format while still writing
      `started_at` and `escalations: 0` (AC2).
      New test `plugin/tests/test_stage_contract.py`: `section(heading_prefix)` extracts from
      the line starting with the prefix up to the next line starting with `## `, right-stripped;
      `test_every_agent_carries_the_contract` parametrised over the four agents × the two
      sections asserts the extracted block is a substring of the agent file (verbatim, AC16 +
      AC17); `test_no_agent_sends_the_reader_to_the_ship_skill` asserts no agent file contains
      `skills/ship` or the phrase `skill \`ship\`` (AC18);
      `test_the_contract_states_the_metrics_format` asserts the contract section names
      `metrics:`, `%Y-%m-%dT%H:%M` and `escalations`, and contains no `README`.
      Automatic verification: `uv run pytest -q plugin/tests/test_stage_contract.py plugin/tests/test_plugin_structure.py`;
      `claude plugin validate --strict plugin/`

- [ ] 3. **One configuration block in all six stage skills** — files:
      `plugin/skills/{idea,plan,plan-review,implement,final-review,ship}/SKILL.md`,
      `plugin/tests/test_stage_skills.py` (new).
      Replace the body of "## Konfiguracja projektu" in each of the six with exactly this
      block, byte-identical everywhere (two bullets, three physical lines, ≤ 100 columns):

      ```markdown
      - Zanim zaczniesz, przeczytaj `.claude/workflow.json` — tam projekt opisuje sam siebie;
        brak pliku = wartości domyślne z README pluginu, wtedy zaproponuj `/pipeline:init`.
      - `<verify.command>`, `<docs.specsDir>` itd. = wartości z tej konfiguracji (klucze w README).
      ```

      No key table, no per-skill enumeration of sections (AC19); the fallback and the
      `/pipeline:init` suggestion stay (AC20).
      New test `plugin/tests/test_stage_skills.py` with `STAGE_SKILLS` = the six names and a
      `section(name, heading)` helper: `test_the_configuration_block_is_two_bullets_everywhere`
      asserts every skill's section has exactly two lines starting with `- `, no `|` table row,
      and that all six blocks are identical; `test_the_configuration_block_keeps_the_fallback`
      asserts each block names `.claude/workflow.json`, `README` and `/pipeline:init`.
      Automatic verification: `uv run pytest -q plugin/tests/test_stage_skills.py`;
      `awk 'length > 100 {print FILENAME": "FNR}' plugin/skills/*/SKILL.md` (expected: no output)

- [ ] 4. **One visual-artifact sentence** — files: `plugin/skills/plan/SKILL.md`,
      `plugin/skills/plan-review/SKILL.md`, `plugin/skills/implement/SKILL.md`,
      `plugin/skills/final-review/SKILL.md`, `plugin/agents/implementer.md`,
      `plugin/tests/test_stage_skills.py`.
      Delete the existing visual-artifact prose: `plan` step 5 (the `verify.scopes` /
      artefakty passage) and the UI lines of the PLAN template's "Weryfikacja end-to-end";
      `plan-review` checklist bullet "weryfikacja E2E" (the UI clause only — the rest of the
      bullet stays); `implement` step 4 and the UI line of step 5; `final-review` mode
      `report`, perspective "Testy" (the UI clause only); the UI clause in
      `plugin/agents/implementer.md`. In its place put one sentence per file, adapted only in
      its verb to the stage's role, of this shape:

      > Gdy `verify.scopes` ma zakres UI, a zmiana dotyka interfejsu — uruchom
      > `<verify.command> <zakres UI>` i OBEJRZYJ artefakty wizualne wymagane przez
      > `<docs.conventions>`; wynik zapisz w PLAN.md.

      Imperative throughout ("uruchom", "obejrzyj", "wymagaj" for the reviewing stages), never
      "rozważ" / "warto"; it names no views of its own (AC22).
      Add to `test_stage_skills.py`: `test_the_visual_sentence_is_one_imperative_sentence`
      parametrised over the five files — asserts the file names `verify.scopes` and
      `<docs.conventions>`, that both appear within one sentence (the text between the
      surrounding sentence boundaries), and that neither `rozważ` nor `warto` occurs in it;
      `test_no_stage_skill_enumerates_views` asserts no stage skill and no agent file contains
      `widok szeroki` / `widok wąski` / `szeroki i wąski`.
      Automatic verification: `uv run pytest -q plugin/tests/test_stage_skills.py`;
      `grep -rn "widok szeroki\|szeroki i wąski" plugin/skills plugin/agents` (expected: no match, exit 1);
      `grep -c "verify.scopes" plugin/skills/plan/SKILL.md plugin/skills/plan-review/SKILL.md plugin/skills/implement/SKILL.md plugin/skills/final-review/SKILL.md plugin/agents/implementer.md`
      (expected: 1 occurrence beyond the configuration block in each)

- [ ] 5. **Metrics format and the checker in every closing step** — files:
      `plugin/skills/plan/SKILL.md` (step 8), `plugin/skills/plan-review/SKILL.md` (step 6),
      `plugin/skills/implement/SKILL.md` (step 5 "Finał"),
      `plugin/skills/final-review/SKILL.md` (`report` step 4 and `apply` steps 2 and 5),
      `plugin/tests/test_stage_skills.py`.
      Each closing step gains, in at most four lines: the flat `metrics:` block with integer
      counters and timestamps `%Y-%m-%dT%H:%M`, the keys that stage owns (named explicitly —
      `plan`: `started_at`, `escalations`, `plan_steps`; `plan-review`: the three
      `plan_review_*`/`plan_changes` keys; `implement`: `implement_steps`,
      `implement_iterations`, `deviations`; `final-review`: the three `final_review_*` keys in
      `report`, `findings_accepted`/`findings_rejected` and `finished_at` in `apply`), then
      `workflow_metrics.py --check <docs.specsDir>/NNN-<slug>` run before the stage reports
      success (AC13), and the sentence that a failure the stage cannot repair from its own
      artifacts ends the stage with `RESULT: ESCALATE` (standalone: STOP with a question),
      naming the missing keys, and that the agent never invents a value it did not measure
      (AC15). In `final-review` the `apply` closing step states that `status: done` is not set
      while `--check` exits non-zero (AC14). No skill refers to README for the metrics format.
      Add to `test_stage_skills.py`: `test_closing_step_states_the_metrics_format`
      (parametrised over the four stage skills × their owned keys, plus `metrics:` and
      `%Y-%m-%dT%H:%M`); `test_closing_step_runs_the_checker` (each names
      `workflow_metrics.py` and `--check`); `test_closing_step_names_the_escalation_path`
      (each names `RESULT: ESCALATE`); `test_apply_mode_gates_done_on_the_checker` (the
      `final-review` `apply` closing step names both `--check` and `done`);
      `test_no_stage_skill_sends_metrics_rules_to_the_readme` (no stage skill has `README`
      within a line that also mentions `metrics`, and `ship` mentions no README for the
      format at all — AC2/AC3).
      Automatic verification: `uv run pytest -q plugin/tests/test_stage_skills.py plugin/tests/test_stage_contract.py`;
      `awk 'length > 100 {print FILENAME": "FNR}' plugin/skills/*/SKILL.md` (expected: no output)

- [ ] 6. **Measure the AC23 budget** — files: possibly
      `plugin/skills/{idea,plan,plan-review,implement,final-review,ship}/SKILL.md` (wording
      tightened only).
      Run the measurement below. Gross deletions across the six stage skills must be ≥ 50 and
      the net change ≤ −12. If the net misses, tighten the wording of the blocks added in
      steps 3–5 (shorter sentences, fewer line breaks) — never by dropping a rule named in
      AC1–AC22; re-run the tests from steps 3–5 after each tightening. If the budget still
      cannot be met without losing a rule, escalate instead of trimming a rule.
      Record the measured numbers in this plan under "End-to-end verification".
      Automatic verification:
      `git fetch origin main && git diff --numstat origin/main -- plugin/skills/idea/SKILL.md plugin/skills/plan/SKILL.md plugin/skills/plan-review/SKILL.md plugin/skills/implement/SKILL.md plugin/skills/final-review/SKILL.md plugin/skills/ship/SKILL.md | awk '{a+=$1; d+=$2} END {print "added="a, "deleted="d, "net="a-d}'`
      (expected: `deleted` ≥ 50 and `net` ≤ −12);
      `grep -rn "to jedyne miejsce, w którym projekt" plugin/skills` (expected: no match);
      `uv run pytest -q plugin/tests/test_stage_skills.py plugin/tests/test_stage_contract.py`

- [ ] 7. **Install and release pinning** — files: `plugin/templates/settings.json`,
      `plugin/README.md`, `plugin/skills/init/SKILL.md`, `plugin/tests/test_init_templates.py`,
      `plugin/tests/test_init_skill.py`, `plugin/tests/test_readme.py`.
      `plugin/templates/settings.json` → `extraKnownMarketplaces` becomes

      ```json
      "TODO-marketplace": {
        "source": {
          "source": "git",
          "url": "TODO: https://github.com/<owner>/<repo>.git",
          "ref": "TODO: pipeline--vX.Y.Z"
        }
      }
      ```

      — `"source": "git"`, an `https://` URL and a `ref`, all three values visibly `TODO`
      (AC24); `enabledPlugins` stays `pipeline@TODO-marketplace`.
      `plugin/README.md` → "Instalacja": the declarative example gains
      `"ref": "pipeline--vX.Y.Z"` and one sentence that without `ref` the consumer follows
      `main` (AC25); a short paragraph states that the pin takes effect only once the
      marketplace is registered with that `ref`, that a marketplace registered earlier without
      one keeps tracking `main`, gives `claude plugin marketplace remove <name>` +
      `claude plugin marketplace add '<url>#<tag>'` and the check
      `git -C ~/.claude/plugins/marketplaces/<name> log --oneline -1` (AC26).
      `plugin/skills/init/SKILL.md` → step 4, `.claude/settings.json` bullet: read the
      marketplace name and version from `${CLAUDE_PLUGIN_ROOT}`
      (`…/<marketplace>/<plugin>/<version>/`) and substitute the marketplace name and
      `"ref": "<plugin>--v<version>"`; a path of another shape leaves `TODO:` and the value
      joins the list from step 7 (AC27).
      Tests: `test_init_templates.py::test_settings_template_pins_a_git_https_source`
      (source `git`, `https://` in the url, a `ref` key, `TODO` in the marketplace key, the
      url and the ref); `test_init_skill.py::test_the_marketplace_ref_is_derived_from_the_plugin_root`
      (step 4 names `ref`, `CLAUDE_PLUGIN_ROOT` and `TODO:` — AC28);
      `test_readme.py::test_installation_pins_the_release_tag` (the Instalacja section carries
      `"ref"` and `pipeline--v`) and `::test_installation_explains_the_marketplace_registration`
      (the section names `marketplace remove`, `marketplace add` and
      `~/.claude/plugins/marketplaces`).
      Automatic verification: `uv run pytest -q plugin/tests/test_init_templates.py plugin/tests/test_init_skill.py plugin/tests/test_readme.py`;
      `python3 -c "import json;json.load(open('plugin/templates/settings.json'))"`

- [ ] 8. **Eval case for the `init` question cap** — files:
      `plugin/evals/init-question-cap/case.yaml`,
      `plugin/evals/init-question-cap/graders/criteria.md`,
      `plugin/tests/test_plugin_structure.py`.
      `case.yaml` follows `plugin/evals/init-keeps-manual-edits/case.yaml`
      (`schema_version: "1.0"`, `runs: 1`, `execution.max_turns`, `allowed_tools` including
      `AskUserQuestion`), prompting a run of `/pipeline:init` in an empty repository **with a
      detectable stack** (a `pyproject.toml` present) and asking the agent to report every
      question it asked, grouped into rounds. `graders/criteria.md` (`type: llm`, `weight: 1`)
      marks the answer correct when there is exactly one round of at most four questions and
      no second round, and incorrect when a second round appears although stack detection
      succeeded, or when more than four questions are asked in the first round (AC29).
      Add `test_plugin_structure.py::test_every_eval_case_has_a_grader`: every directory in
      `plugin/evals` has `case.yaml` and at least one file in `graders/`, and every
      `case.yaml` names `schema_version`.
      Automatic verification: `uv run pytest -q plugin/tests/test_plugin_structure.py`;
      `python3 -c "import pathlib;[print(p) for p in sorted(pathlib.Path('plugin/evals').glob('*/case.yaml'))]"`
      (expected: three cases, including `init-question-cap`);
      `claude plugin validate --strict plugin/`

- [ ] 9. **Honest scope of the migration module** — files: `docs/DECISIONS.md`,
      `plugin/README.md`.
      Append one row to `docs/DECISIONS.md` (append-only, dated): the migration module
      recognises only Alembic's verbs (`upgrade`, `downgrade`, `stamp`, `revision`, `current`,
      `check`) and the variables `ENVIRONMENT`, `DATABASE_URL`, `DB_HOST`; only
      `migrations.command` and `migrations.localHosts` are configurable; deliberately not
      generalised, with the backlog trigger named (AC30).
      `plugin/README.md` → "Strażnik komend": one sentence saying the same, so a project on
      another migration tool cannot mistake the guard's silence for protection (AC31).
      Add `test_readme.py::test_the_guard_section_states_the_migration_scope`: the
      "Strażnik komend" section names `Alembic`, `migrations.command` and `migrations.localHosts`.
      Automatic verification: `uv run pytest -q plugin/tests/test_readme.py plugin/tests/test_no_domain_references.py`;
      `grep -n "Alembic" docs/DECISIONS.md plugin/README.md` (expected: one row and one sentence)

- [ ] 10. **Release 0.3.0 and project documents** — files:
      `plugin/.claude-plugin/plugin.json`, `plugin/CHANGELOG.md`, `docs/ROADMAP.md`,
      `docs/BACKLOG.md`, `plugin/tests/test_readme.py`.
      Version → `0.3.0`; a `## 0.3.0` CHANGELOG section (Polish, like the rest of the file)
      with "Zmienione"/"Dodane" subsections and a line labelled **wpływ na konsumenta**: the
      consumer re-registers the marketplace with the new `ref`, and a spec started before this
      release may escalate once over missing metric keys (AC32).
      `docs/ROADMAP.md`: add "Stage 2 — Rules the agent executes" with this spec's item,
      linked to `specs/001-executable-rules-and-release-pinning/SPEC.md`, ticked (the PR
      delivers it). `docs/BACKLOG.md`: remove the two delivered P3 items ("Releases / Document
      release pinning for consumers" and "Init / Cover the cap on `init`'s first question
      round"); the other `init` items stay untouched with their triggers.
      Add `test_readme.py::test_the_changelog_names_the_consumer_impact`: the section for the
      manifest version contains `wpływ na konsumenta`.
      Automatic verification: `uv run pytest -q plugin/tests/test_readme.py`;
      `python3 -c "import json;print(json.load(open('plugin/.claude-plugin/plugin.json'))['version'])"`
      (expected: `0.3.0`);
      `grep -n "## 0.3.0" plugin/CHANGELOG.md`

- [ ] 11. **Consumer safety net and full verification** — files: none expected (fixes only if
      something is red).
      Confirm nothing the consumer relies on moved: the metric keys, the configuration keys
      and the guard's verdicts (AC36); no new dependency and no import outside the standard
      library (AC34); `plugin/tests/test_guard.py` untouched.
      Automatic verification:
      `git diff --stat origin/main -- plugin/tests/test_guard.py pyproject.toml uv.lock` (expected: empty);
      `git diff origin/main -- plugin/bin/workflow_metrics.py | grep -E "^[-+].*COUNTERS = |^-\s+\"[a-z_]+\",$"` (expected: no removed counter);
      `grep -rnE "^\s*(import|from) " plugin/bin plugin/hooks | grep -vE "(argparse|json|os|re|sys|shlex|subprocess|datetime|pathlib|fnmatch|typing|importlib|workflow_config)"` (expected: no output);
      `bash scripts/check.sh` (expected: `ALL GREEN`)

## Risks and traps

- **The AC23 budget is tight.** Removable prose is ≈59 lines gross, additions ≈41; step 6
  measures instead of assuming, and names tightening (not rule-dropping) as the only remedy.
- **`ship` and the agents are now one unit.** After step 2 any edit of the contract in
  `plugin/skills/ship/SKILL.md` must be repeated in four files or CI fails — that is the
  point of AC17, but it will surprise a later editor; the test message must say so.
- **`--check` on this repository's own spec.** Spec 001 carries `escalations: 1` and
  `started_at`; at `plan-draft` `plan_steps` becomes due, so step 1's manual invocation is run
  against the spec directory before this plan's own metrics are written and must stay exit 0
  at `spec-ready` (nothing is due).
- **Line length.** Markdown in skills follows the 100-column convention; the three-line
  configuration block and the visual sentence were sized for it, and steps 3 and 5 verify it
  with `awk`.
- **`test_no_domain_references.py`.** Step 9 introduces the word "Alembic" into
  `plugin/README.md`; it is not among the forbidden patterns (they cover the owner's private
  domain), and the guard's own code already carries those verbs — verified in steps 9 and 11.
- **`claude plugin validate --strict`** may be skipped locally when `claude` is off PATH;
  CI runs it, so steps 2 and 8 call it explicitly and tolerate its absence.
- **The eval case is manual.** AC29 is satisfied by the case existing and being well formed;
  its verdict comes from the manual `plugin-eval` workflow, not from CI (a binding decision in
  `docs/DECISIONS.md`).

## End-to-end verification

### Automatic (performed by /pipeline:implement)

There is no application to bring up and no UI scope in `.claude/workflow.json`
(`verify.scopes` absent), so the end-to-end check is the plugin exercised as a consumer would
exercise it, on plain `python3`:

1. `bash scripts/check.sh` → `ALL GREEN` (plugin and marketplace validate, ruff, black,
   pytest).
2. The checker on a real spec tree, as a stage would call it:
   `python3 plugin/bin/workflow_metrics.py --check specs/001-executable-rules-and-release-pinning; echo "exit=$?"`
   → exit 0, no output, once this plan's metrics are written.
3. The checker's failure path, on a scratch copy — expected exit 1 and a message naming the
   key:
   `d=$(mktemp -d)/014-x && mkdir -p "$d" && printf -- '---\nstatus: plan-draft\nmetrics:\n  started_at: 2026-09-15T09:00\n  plan_steps: 3\n---\n' > "$d/SPEC.md" && python3 plugin/bin/workflow_metrics.py --check "$d"; echo "exit=$?"`
   → exit 1, stderr names `escalations` and the status `plan-draft`, no traceback (AC10, AC37).
4. The report path unchanged: `python3 plugin/bin/workflow_metrics.py specs; echo "exit=$?"`
   → the markdown table, exit 0 (AC12).
5. The AC23 measurement from step 6, with its numbers recorded here.
6. `python3 -c "import json,sys;json.load(open('plugin/templates/settings.json'))"` and
   `claude plugin validate --strict plugin/ && claude plugin validate --strict .`
   (skipped with a note if `claude` is off PATH; CI runs it).

Record each command's real output in this section.

### Manual (performed by the owner)

1. After the merge: tag `pipeline--v0.3.0`, then re-register the marketplace
   (`claude plugin marketplace remove wcz-tools`, `claude plugin marketplace add
   'https://github.com/wojciechczarnecki/agentic-pipeline.git#pipeline--v0.3.0'`) and move the
   pin in `.claude/settings.json` and `CLAUDE.md` — out of scope here by the SPEC, because the
   tag does not exist before the merge.
2. Run the manual `plugin-eval` workflow for `init-question-cap` (a real model, outside CI by
   decision) and confirm the grader's verdict.

## Definition of Done

- [ ] every step ticked
- [ ] `bash scripts/check.sh` green in full
- [ ] end-to-end verification (automatic) performed, its result recorded above
- [ ] `docs/ROADMAP.md` updated; `docs/DECISIONS.md` (the migration-scope row) updated;
      `docs/BACKLOG.md` pruned of the two delivered items
- [ ] spec status: `implemented`

## Owner decisions

_(appended by /pipeline:ship or by a stage on escalation: date, stage, question, decision)_

- 2026-09-20 — plan — AC23's line threshold and AC19's "at most two lines" were decided by the
  owner before this plan was written; see SPEC.md → "Owner decisions". The plan implements
  those decisions (steps 3 and 6).

## Review log

_(filled in by /pipeline:plan-review)_

## Deviations

_(filled in by /pipeline:implement — every departure from the plan with its rationale)_

## Final review

_(filled in by /pipeline:final-review)_
