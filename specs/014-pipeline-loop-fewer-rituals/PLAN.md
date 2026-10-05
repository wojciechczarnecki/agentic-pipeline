# PLAN 014 — Fewer rituals, more code in the pipeline loop

## Owner summary

- **Approach:** Code first, then text. `workflow_metrics.py` gains `--derive`, which reads the
  counters from fixed forms in SPEC.md and PLAN.md. It also gains a spec lint in `--check`
  and a `--close` subcommand: cost, `done`, derive and check, flaky check, commit, push, wait
  and one re-run. The loader retires `implement.chunked`. After that, the converge pass, the
  red column and the chunked implementer leave the skills, agents, templates, eval cases and
  README. The skills then give the fixed forms that `--derive` reads, the `KIND:` RESULT key
  and the new close. The release is 0.9.0.
- **Main risks:** `--close` runs `git push` and `gh` inside one allowed command, so the
  guard never sees them. The script itself refuses protected branches and never forces.
  The lint applies to this spec's own PLAN and to the eval fixtures from the step that adds
  it. `--derive` overwrites `escalations` from the decision entries, so an entry in an old
  free form is not counted, and the script then names the key instead of writing it.
- **New dependency:** no
- **Data migration:** no
- **Manual scenarios for the owner:** 1 — the canary before the tag (AC31): one small spec
  through `/pipeline:ship` in a consumer clone on the working-tree plugin.

## Approach

What the plan rests on:

- `specs/014-pipeline-loop-fewer-rituals/SPEC.md`: read in full, `## Owner decisions`
  included.
- `docs/CONVENTIONS.md`: read in full. Standard library only in `plugin/bin`. Scripts are
  tested as subprocesses. Tests are written before or with the code. Eval cases are measured
  before they ship, and none are added here. A minor release needs the receipt and the
  canary, which belong to the owner. Workflow metrics are called by name through `PATH`.
- `docs/ROADMAP.md`: searched for "0.9.0", "Stage 10" and "consumer". This found the Stage 10
  item, which is this spec bullet by bullet, and the 0.10.0 item, which stays out.
- `docs/DECISIONS.md`: searched for "2026-10-05", "converge", "chunk" and "SPEC 010/012". The
  2026-10-05 row is the rationale. The rows of SPEC 010 and 012 stay as history, and
  `tests/test_documents.py` pins them.
- `docs/BACKLOG.md`: searched for "0.9.0", "workflow_metrics.py" and "lower bound". This
  found the two P2 items with a 0.9.0 trigger and the P3 `Agent`-tool item.
- `plugin/README.md`, `plugin/skills/{implement,ship,plan,plan-review,final-review}/SKILL.md`,
  `plugin/agents/*.md`, `plugin/bin/workflow_metrics.py`, `plugin/bin/workflow_config.py`,
  `plugin/templates/{PLAN.en.md,PLAN.pl.md,sections.md,workflow.example.json}`: read in full.
- `plugin/skills/init/SKILL.md`: searched for "implement". This found the one sentence on
  the `implement` section in step 4.
- Tests: `plugin/tests/test_workflow_metrics.py`, `test_stage_skills.py`,
  `test_stage_contract.py`, `test_ship_cost_and_models.py`, `test_release_0_8_0.py` and
  `tests/test_spec_metrics.py` were read in full. The other test files were searched for
  "converge", "chunk", "Red before", "Group N", "Grupa" and "implement_chunks". The search
  found `test_eval_cases.py`, `test_templates_language.py`, `test_language_contract.py`,
  `test_readme.py`, `test_record_cost.py`, `test_workflow_config.py`, `test_init_*.py`,
  `test_review_depth.py`, `tests/test_documents.py` and `tests/test_eval_receipt.py`.
- The consumer's specs (`/home/czarny/Projects/gaffers-presser/specs/00{1..9}-*/SPEC.md`):
  read their frontmatter only. All nine are `done`. They carry `converge_gaps`, and three
  carry `implement_chunks`.

Patterns to reuse:

- `write_costs()` in `plugin/bin/workflow_metrics.py` makes an exact line edit inside the
  `metrics:` block. `--derive` and `--close` use it for every key they write (extend it to
  `str` values for `finished_at`). Keep the name, since `record_cost` and its tests use it.
- `parse_metrics`, `parse_status` and `FRONTMATTER` read the frontmatter.
- `workflow_config.load_sections(start)` returns `protectedBranches` and `docs.backlog`
  without failing on a faulty section.
- `record_cost(spec_dir, default_transcripts())` is called by `--close` in-process.
- Test helpers: `spec_dir()`/`run_check()` in `test_workflow_metrics.py`. The git-repo
  fixtures (`repo`, a bare remote) are in `test_record_cost.py` and
  `tests/test_release_gate.py`. The stub-`claude`-on-`PATH` pattern is in
  `tests/test_release_gate.py`, and the stub `gh` follows it.

Design choices:

- **Where the parsing lives:** a new standard-library module
  `plugin/bin/spec_forms.py` reads `templates/sections.md` at run time (the path is
  `Path(__file__).resolve().parent.parent / "templates" / "sections.md"`). It finds a
  section by either literal, and it parses the fixed forms. The close is a new module
  `plugin/bin/workflow_close.py`. Both are imported by `workflow_metrics.py`, the way
  `workflow_config` is imported. Rejected: all of it in `workflow_metrics.py`, which would
  pass 1200 lines. The command stays `workflow_metrics.py --derive|--close` (SPEC
  decision 9), so the existing allow rule covers it.
- **The fixed forms** (AC11). Every form is a code token, the same in both languages, like
  the severity tokens and metric keys. Only the pass line is bilingual, because AC13 names
  both literals:
  - step tick: `- [x] <n>. … — `iterations: <k>``. `<k>` is the count of loop iterations
    beyond the first attempt, so 0 when the step was green at once. The note can stand
    anywhere in the step's block.
  - deviation: `- `major` — …` or `- `minor` — …`. Every top-level `- ` entry without the
    `major` token counts as minor.
  - review log finding: a list item (`- ` or `<n>. `) that starts with
    `` `blocker` ``, `` `major` `` or `` `minor` ``.
  - final review finding: `- **F<n>** `<blocker|worth-fixing|nit>` …`. A distinct `F<n>`
    counts once. A false finding the reviewer rejects is listed without this form.
  - owner decision entry (SPEC.md and PLAN.md):
    `- YYYY-MM-DD — <stage> — `<kind>` — <question> — <decision>`. `<stage>` is one of
    `plan`, `plan-review`, `implement`, `final-review`. `<kind>` is one of `decision`,
    `permission`, `tooling`, `gate`. The gate entry carries
    `` `accepted`: F1, F2; `rejected`: F3 ``, with `none` for an empty list. The dash may
    be `—` or `-`.
  - manual scenario: each item in `### Manual (performed by the owner)` has a line starting
    with `Pass when:` / `Zaliczony, gdy:` (new `sections.md` row `pass-condition`). Another
    way to pass is a section of exactly one line `n/a — <reason>`.
- **When `--derive` writes a key** (AC9: only when its source is in the expected form):
  - `plan_steps`: when there is at least one `- [ ] <n>.`/`- [x] <n>.` line in `## Steps`.
  - `implement_steps`: when at least one step is ticked.
  - `implement_iterations`: when at least one step is ticked and every ticked step has its
    note.
  - `deviations_minor`/`deviations_major`: when the status is `implemented` or `done`, or
    the section has an entry.
  - `plan_review_*` and `final_review_*`: when their section holds more than the
    template's `_(…)_` placeholder.
  - `findings_*`: when there is a gate entry (the last one counts).
  - `escalations`, `escalations_permission`, `escalations_tooling`: always. They count the
    non-gate fixed-form entries of SPEC.md and PLAN.md. A top-level `- ` entry in PLAN.md's
    `## Owner decisions` that is not in the fixed form leaves all three unwritten, because
    the count would be ambiguous. Entries in SPEC.md that are not in the form (the `idea`
    dialogue) are ignored.

  Every key not written is named on stderr with its reason. The exit is 0, and 1 only
  for a missing or unreadable SPEC.md.
- **The lint** (AC12–AC14) only runs for `plan-draft`, `plan-approved` and
  `implemented`. A missing PLAN.md reads as empty, so every AC is then reported. A SPEC
  without ACs (the existing test fixtures) has nothing to report.
- **Escalations are counted, not incremented:** `ship` appends the fixed-form entry and no
  longer touches `metrics.escalations`. The next stage's `--derive` (or `--close`) writes
  it. Rejected: `ship` running `--derive` itself, because `ship` only reads, and every
  stage closes with `--derive` anyway.
- **`--close` exit codes:**
  - 0: green.
  - 1: refused, or derive/check red, with nothing changed or committed.
  - 3: a flaky job with no backlog entry, nothing committed.
  - 4: commit or push failed.
  - 5: the checks are red after the one re-run, or the wait timed out.

  Each non-zero exit prints one line:
  `close stopped at <step>: <reason>; committed: yes|no, pushed: yes|no`.
- **Resuming `--close`** (AC22): the run is a resume when the status is `done` and the last
  commit that touched SPEC.md (`git log -1 --format=%s -- <SPEC.md>`) is
  `docs: close SPEC NNN <slug>`. It then skips the cost, status, derive, check, flaky check
  and commit, and goes on from the push and the wait. A `done` without that commit is
  refused like any other status. This test survives a commit `ship` makes after the stop.
- **CI as `gh` sees it:** the checks are the Actions runs of the head commit,
  `gh run list --commit <sha> --json databaseId,status,conclusion,attempt,url,workflowName`,
  polled until there is at least one run and all are `completed`. Green means every
  conclusion is in `success`/`skipped`/`neutral`. The poll interval and the timeout come from
  `PIPELINE_CLOSE_POLL_SECONDS` (default 15) and `PIPELINE_CLOSE_TIMEOUT_SECONDS` (default
  3600), so the tests run with 0 and 5. A flaky job is one with `failure` in an earlier
  attempt (`gh run view <id> --attempt <k> --json jobs`) and `success` in the latest
  (`gh run view <id> --json jobs`). The open PR comes from
  `gh pr view --json number,state,url,headRefOid`.

## AC → steps matrix

| AC | Steps | Proving test | Red before the change |
|----|-------|--------------|-----------------------|
| AC1 | 8, 10, 13, 14, 15 | `plugin/tests/test_pipeline_loop.py::test_no_ritual_returns`, `tests/test_eval_receipt.py::test_no_rule_names_a_removed_case` |  `uv run pytest -q tests/test_eval_receipt.py` → `assert not (ROOT / "plugin" / "evals" / name).exists(), name`; `uv run pytest -q plugin/tests/test_stage_contract.py` → `assert trigger not in ship, trigger`; `uv run pytest -q plugin/tests/test_pipeline_loop.py` → `assert not found, found` (test_no_ritual_returns); `uv run pytest -q plugin/tests/test_readme.py` → `assert word.lower() not in README.lower(), word` (test_the_readme_has_no_ritual) |
| AC2 | 8, 9, 10, 11, 12, 13, 15 | `plugin/tests/test_templates_language.py::test_the_ac_matrix_has_three_columns`, `plugin/tests/test_pipeline_loop.py::test_no_ritual_returns`, `plugin/tests/test_stage_contract.py::test_the_removed_triggers_are_gone` |  `uv run pytest -q tests/test_eval_receipt.py` → `assert not (ROOT / "plugin" / "evals" / name).exists(), name`; `uv run pytest -q plugin/tests/test_templates_language.py` → `assert header in lines, (language, header)`; `uv run pytest -q plugin/tests/test_review_depth.py` → `assert "red record" not in text`; `uv run pytest -q plugin/tests/test_stage_contract.py` → `assert trigger not in ship, trigger` |
| AC3 | 10, 12 | `plugin/tests/test_pipeline_loop.py::test_implement_keeps_test_first_guidance`, `::test_final_review_tests_break_the_code` |  `uv run pytest -q plugin/tests/test_pipeline_loop.py` → `assert heading in text, "no section `## Test first`"`; `uv run pytest -q plugin/tests/test_pipeline_loop.py` → `assert heading in text, "no section `## Test first`"`; `uv run pytest -q plugin/tests/test_pipeline_loop.py` → `assert "Break the code" in tests` |
| AC4 | 8, 9, 10, 11, 13, 14, 15 | `plugin/tests/test_pipeline_loop.py::test_no_ritual_returns`, `plugin/tests/test_templates_language.py::test_the_section_map_has_no_group_rows` |  `uv run pytest -q tests/test_eval_receipt.py` → `assert not (ROOT / "plugin" / "evals" / name).exists(), name`; `uv run pytest -q plugin/tests/test_templates_language.py` → `assert not keys & {"step-group", "chunk-notes"}`; `uv run pytest -q plugin/tests/test_pipeline_loop.py` → `assert "chunk" not in state.lower()` |
| AC5 | 1, 15 | `plugin/tests/test_workflow_config.py::test_retired_chunked_passes_with_a_notice`, `::test_retired_chunked_is_silent_for_the_hooks`, `::test_implement_bad_values_still_fail`, `plugin/tests/test_init_templates.py::test_the_example_has_no_implement_section` |  `uv run pytest -q plugin/tests/test_workflow_config.py plugin/tests/test_init_templates.py` → `assert "retired in 0.9.0" in result.stderr` (and `assert "implement" not in example`); `uv run pytest -q plugin/tests/test_readme.py` → `assert token in rows[0], token` (`retired in 0.9.0`) |
| AC6 | 4 | `plugin/tests/test_spec_lint.py::test_consumer_specs_pass_the_check`, `tests/test_spec_metrics.py` |  n/a — kept behaviour (every consumer spec passes `--check` before and after the lint) |
| AC7 | 3 | `plugin/tests/test_derive.py::test_derive_writes_every_key` |  `uv run pytest -q plugin/tests/test_derive.py` → `assert result.returncode == 0, result.stderr` (--derive unknown, argparse exit 2) |
| AC8 | 3, 10 | `plugin/tests/test_derive.py::test_a_missing_iteration_note_leaves_iterations_unwritten`, `plugin/tests/test_pipeline_loop.py::test_implement_ticks_with_the_iteration_note` |  `uv run pytest -q plugin/tests/test_derive.py` → `assert metrics_of(spec)["implement_iterations"] == "9"` precondition run: `assert result.returncode == 0`; `uv run pytest -q plugin/tests/test_pipeline_loop.py` → `assert "`iterations: <k>`" in step` |
| AC9 | 3 | `plugin/tests/test_derive.py::test_derive_keeps_every_other_byte`, `::test_derive_is_idempotent`, `::test_missing_sources_are_named` |  `uv run pytest -q plugin/tests/test_derive.py` → `assert result.returncode == 0, result.stderr` (--derive unknown, argparse exit 2) |
| AC10 | 10, 11, 12, 13, 14 | `plugin/tests/test_pipeline_loop.py::test_every_stage_closes_with_derive_then_check`, `::test_no_skill_counts_a_derived_key` |  `uv run pytest -q plugin/tests/test_pipeline_loop.py` → `assert DERIVE in step and CHECK in step, name`; `uv run pytest -q plugin/tests/test_pipeline_loop.py` → `assert DERIVE in step and CHECK in step, name`; `uv run pytest -q plugin/tests/test_pipeline_loop.py` → `assert DERIVE in step and CHECK in step, name` (plan, plan-review); `uv run pytest -q plugin/tests/test_stage_contract.py` → `assert "`workflow_metrics.py --derive <spec-dir>`" in block`; `uv run pytest -q plugin/tests/test_pipeline_loop.py` → `assert "--derive" in sentence or "--close" in sentence` |
| AC11 | 3, 9 | `plugin/tests/test_derive.py::test_derive_writes_every_key` (en, pl), `plugin/tests/test_templates_language.py::test_templates_give_the_fixed_forms` |  `uv run pytest -q plugin/tests/test_derive.py` → `assert result.returncode == 0, result.stderr` (--derive unknown, argparse exit 2); `uv run pytest -q plugin/tests/test_templates_language.py` → `assert form in text, (language, form)` |
| AC12 | 4 | `plugin/tests/test_spec_lint.py::test_an_ac_without_a_matrix_row_is_reported` |  `uv run pytest -q plugin/tests/test_spec_lint.py` → `assert result.returncode == 1, result.stderr` |
| AC13 | 4, 9, 11 | `plugin/tests/test_spec_lint.py::test_a_manual_item_without_a_pass_line_is_reported`, `plugin/tests/test_pipeline_loop.py::test_plan_requires_the_pass_line` |  `uv run pytest -q plugin/tests/test_spec_lint.py` → `assert result.returncode == 1` (manual item without a pass line exits 0); `uv run pytest -q plugin/tests/test_pipeline_loop.py` → `assert "`Pass when:`" in text` |
| AC14 | 4 | `plugin/tests/test_spec_lint.py::test_unlinted_statuses_pass` |  n/a — kept behaviour (specs in `spec-draft`, `spec-ready` and `done` pass the check before and after) |
| AC15 | 3, 13 | `plugin/tests/test_derive.py::test_escalations_by_kind`, `plugin/tests/test_stage_contract.py::test_the_result_block_has_kind` |  `uv run pytest -q plugin/tests/test_derive.py` → `assert result.returncode == 0, result.stderr` (--derive unknown, argparse exit 2); `uv run pytest -q plugin/tests/test_stage_contract.py` → `assert fields == ["STATUS", "METRICS", "KIND", "ESCALATION", "SUMMARY"], fields` |
| AC16 | 2, 3, 14 | `plugin/tests/test_derive.py::test_escalations_by_kind`, `plugin/tests/test_workflow_metrics.py::test_escalation_kinds_are_optional`, `plugin/tests/test_pipeline_loop.py::test_ship_stops_on_the_third_decision` |  `uv run pytest -q plugin/tests/test_derive.py plugin/tests/test_workflow_metrics.py` → `assert key in workflow_metrics.COUNTERS` and `assert metrics["escalations"] == "4"`; `uv run pytest -q plugin/tests/test_pipeline_loop.py` → `assert "Increment `metrics.escalations`" not in skill("ship")` |
| AC17 | 10 | `plugin/tests/test_pipeline_loop.py::test_implement_installs_accepted_dependencies` |  `uv run pytest -q plugin/tests/test_pipeline_loop.py` → `assert "accepts you add yourself" in text`; `uv run pytest -q plugin/tests/test_pipeline_loop.py` → `assert "accepts you add yourself" in text` |
| AC18 | 11 | `plugin/tests/test_pipeline_loop.py::test_plan_writes_no_owner_step` |  `uv run pytest -q plugin/tests/test_pipeline_loop.py` → `assert "no step for the owner to perform" in text` |
| AC19 | 5 | `plugin/tests/test_close.py::test_close_refuses` (each case) |  `uv run pytest -q plugin/tests/test_close.py` → `assert result.returncode == 1, result.stderr` (--close unknown, exit 2) |
| AC20 | 6 | `plugin/tests/test_close.py::test_close_green_path`, `::test_a_red_check_restores_the_spec`, `::test_red_then_green_after_one_rerun` |  `uv run pytest -q plugin/tests/test_close.py` → `assert result.returncode == 0, result.stderr` (test_close_green_path, with the close steps stubbed to a stop) |
| AC21 | 7 | `plugin/tests/test_close.py::test_a_flaky_job_without_a_backlog_entry_stops`, `::test_a_flaky_job_in_the_backlog_passes` |  `uv run pytest -q plugin/tests/test_close.py` → `assert result.returncode == 3, result.stderr` (test_a_flaky_job_without_a_backlog_entry_stops) |
| AC22 | 5, 6, 7 | `plugin/tests/test_close.py::test_every_stop_prints_one_state_line`, `::test_resume_after_a_stop_at_the_wait`, `::test_resume_after_a_failed_push` |  `uv run pytest -q plugin/tests/test_close.py` → `assert result.returncode == 1, result.stderr` (--close unknown, exit 2) |
| AC23 | 12, 14, 15 | `plugin/tests/test_pipeline_loop.py::test_final_review_apply_ends_at_green_ci`, `plugin/tests/test_ship_cost_and_models.py::test_closing_runs_close_after_apply`, `plugin/tests/test_readme.py::test_the_status_table_names_close` |  `uv run pytest -q plugin/tests/test_pipeline_loop.py` → `assert "status stays `implemented`" in apply`; `uv run pytest -q plugin/tests/test_ship_cost_and_models.py` → `assert CLOSE in closing`; `uv run pytest -q plugin/tests/test_readme.py` → `assert "PR with green CI" in rows["`implemented` + decisions"]` (status table) |
| AC24 | 5, 6, 7 | `plugin/tests/test_close.py` (the whole file) |  `uv run pytest -q plugin/tests/test_close.py` → `assert result.returncode == 1, result.stderr` (--close unknown, exit 2) |
| AC25 | 14 | `plugin/tests/test_ship_cost_and_models.py::test_the_start_message_names_every_stage_model` |  `uv run pytest -q plugin/tests/test_ship_cost_and_models.py` → `assert token in start, token` (`session model`) |
| AC26 | 2 | `plugin/tests/test_workflow_metrics.py::test_cost_lines_are_labelled_a_lower_bound` |  `uv run pytest -q plugin/tests/test_workflow_metrics.py` → `assert line.endswith(" — a lower bound: output tokens are undercounted")` |
| AC27 | 12 | `plugin/tests/test_pipeline_loop.py::test_final_review_notes_one_context` |  `uv run pytest -q plugin/tests/test_pipeline_loop.py` → `assert "`Agent` tool" in final_review_step("Report mode", 2)` |
| AC28 | 2 | `plugin/tests/test_workflow_metrics.py::test_a_column_without_data_is_left_out` |  `uv run pytest -q plugin/tests/test_workflow_metrics.py` → `assert key not in cells` |
| AC29 | 16 | `plugin/tests/test_release_0_9_0.py`, `tests/test_documents.py::test_decisions_record_spec_014`, `::test_roadmap_ticks_spec_014`, `::test_backlog_after_spec_014` |  `uv run pytest -q plugin/tests/test_release_0_9_0.py tests/test_documents.py` → `assert tuple(int(part) for part in manifest["version"].split(".")) >= (0, 9, 0)` |
| AC30 | 17 | `bash scripts/check.sh` | n/a — the whole suite, green by definition at the end; n/a — the whole suite, green by definition at the end |
| AC31 | — | the canary in `### Manual` | manual |

## Steps

Every step writes its proving tests first and runs them red, then makes the change. Every
step ends with the full `uv run pytest -q` green. Several steps delete tests that pin removed
text, and a step that left them for later would end red.

### Group 1 — Configuration and the metrics script

- [x] 1. Retire `implement.chunked` (AC5). Files: `plugin/bin/workflow_config.py`, — `iterations: 1`
      `plugin/templates/workflow.example.json`, `plugin/skills/init/SKILL.md`,
      `plugin/tests/test_workflow_config.py`, `plugin/tests/test_init_templates.py`,
      `plugin/tests/test_init_skill.py`.
      Tests first. Replace the three SPEC 012 tests in `test_workflow_config.py`:
      - `test_retired_chunked_passes_with_a_notice[True|False]`: `--check` exits 0, and
        stderr holds `` `implement.chunked` ``, `retired in 0.9.0`, `ignored` and `remove`.
      - `test_retired_chunked_is_silent_for_the_hooks`: `load_sections` returns no problem,
        `"implement" not in workflow_config.defaults()`, and the guard hook, run the way
        `test_guard.py` runs it on a harmless command (`ls`) in that repo, exits 0 with no
        `implement` on stderr.
      - `test_implement_bad_values_still_fail`: `{"chunked": "yes"}`, `{"chunked": 1}`,
        `{"chunked": true, "size": 3}` and `"on"` give `--check` exit 1 with today's messages.
      - `test_the_example_has_no_implement_section`, which replaces
        `test_the_example_shows_chunking_off`.
      - In `test_init_skill.py`, step 4 still says "you do not write the `implement`
        section" and no longer says "chunking".

      Change: `SCHEMA` keeps `"implement": {"chunked": bool}`, `defaults()` drops
      `implement`, and `main --check` prints the notice when the loaded config has
      `implement.chunked`. The notice never comes from `load`/`load_sections`.
      `workflow.example.json` loses the section. The `init` sentence says the section was
      retired in 0.9.0.
      Automatic verification: `uv run pytest -q plugin/tests/test_workflow_config.py
      plugin/tests/test_init_templates.py plugin/tests/test_init_skill.py
      plugin/tests/test_guard.py && uv run pytest -q`
- [x] 2. The report: columns with data only, and cost as a lower bound (AC26, AC28, AC16). — `iterations: 1`
      Files: `plugin/bin/workflow_metrics.py`, `plugin/tests/test_workflow_metrics.py`.
      Tests first:
      - `test_a_column_without_data_is_left_out`: two specs with `COMPLETE` give no
        `converge_gaps`, `implement_chunks`, `cost_*` or `escalations_*` column. A third
        spec with `implement_chunks: 3` brings that column, with `-` for the others. The
        totals row has the same columns.
      - `test_cost_lines_are_labelled_a_lower_bound`: each of the three cost lines ends with
        ` — a lower bound: output tokens are undercounted`. Update the exact strings in
        the three existing cost tests.
      - `test_escalation_kinds_are_optional`: `escalations_permission` and
        `escalations_tooling` are in `COUNTERS`, in no `REQUIRED` list, and a non-integer
        is red. Add both to `NEW_KEYS`.
      - Rework `test_report_has_columns_for_the_new_keys` and
        `test_implement_chunks_is_a_report_column` to the new rule.

      Change: add the two keys to `COUNTERS` after `escalations`, keeping `converge_gaps`
      and `implement_chunks` as legacy keys, so old specs pass. `render` shows a counter
      column only when some row carries it, and the totals still cover every counter for
      the summary lines. `per_unit` appends the label.
      Automatic verification: `uv run pytest -q plugin/tests/test_workflow_metrics.py &&
      uv run pytest -q`
- [x] 3. `--derive` (AC7, AC8, AC9, AC11, AC15, AC16). Files: new — `iterations: 0`
      `plugin/bin/spec_forms.py`, `plugin/bin/workflow_metrics.py`, new
      `plugin/tests/test_derive.py`, new fixtures `plugin/tests/fixtures/derive/{en,pl}/`
      `{SPEC.md,PLAN.md}`.
      The fixtures come first. Both languages carry the same counts with their own headings
      and prose. SPEC.md has status `implemented`, a `metrics:` block with `started_at`,
      `plan_changes: 3` and `escalations: 0`, `AC1`–`AC3`, and a `## Owner decisions`
      section. That section holds two numbered `idea` entries (ignored) and one
      fixed-form `plan` `decision` entry. PLAN.md uses the forms of the Approach:
      - 4 ticked steps with notes 0, 2, 1 and 0;
      - a deviation section with one `minor` entry and one `major` entry;
      - a review log with `blocker` ×1, `major` ×2 and `minor` ×1;
      - a final review with F1 `blocker`, F2 and F3 `worth-fixing`, F4 `nit`, and one
        rejected false finding without an id;
      - owner decisions: `implement` `decision`, `implement` `permission`,
        `final-review` `tooling`, and a `gate` with `accepted`: F1, F2, F3 and
        `rejected`: F4;
      - an AC → steps matrix with a row for each of AC1–AC3 and a `### Manual` section
        whose item has its pass line (`Pass when:` / `Zaliczony, gdy:`), so that step 4's
        lint, which runs at status `implemented`, keeps `--check` green on these fixtures.

      Expected values: `plan_steps` 4, `implement_steps` 4, `implement_iterations` 3,
      `deviations_minor` 1, `deviations_major` 1, `plan_review_blockers` 1,
      `plan_review_majors` 2, `final_review_blockers` 1, `final_review_worth_fixing` 2,
      `final_review_nits` 1, `findings_accepted` 3, `findings_rejected` 1, `escalations` 4,
      `escalations_permission` 1, `escalations_tooling` 1.

      Tests (subprocess `workflow_metrics.py --derive <copy in tmp_path>`):
      - `test_derive_writes_every_key[en|pl]`: exactly the values above, and `--check`
        then exits 0.
      - `test_derive_keeps_every_other_byte`: the SPEC.md lines outside the metric lines,
        `plan_changes` and `started_at` included, are byte-identical.
      - `test_derive_is_idempotent`: a second run leaves identical bytes.
      - `test_a_missing_iteration_note_leaves_iterations_unwritten`: drop step 2's note.
        A pre-existing `implement_iterations: 9` stays 9, stderr names `step 2` and
        `implement_iterations`, and the exit is 0.
      - `test_missing_sources_are_named`: a PLAN with placeholder-only review log and final
        review, no tick and status `plan-approved` leaves the `plan_review_*`,
        `final_review_*`, `implement_*`, `deviations_*` and `findings_*` keys unwritten.
        Each is named on stderr, and the exit is 0.
      - `test_escalations_by_kind`: the kinds as above. An unknown kind token does not
        count. Without a PLAN.md, only SPEC entries count.
      - `test_an_unformed_plan_decision_leaves_escalations_unwritten`.
      - `test_derive_needs_a_spec`: exit 1 for a missing SPEC.md.
      - `test_derive_is_exclusive`: `--derive` with `--check` is an argparse error (exit 2).

      Change: `spec_forms.py` holds `section_map()`, `section(text, key)` and the parsers.
      `workflow_metrics.py` holds `derive(spec_dir) -> int`, the `--derive` option and the
      usage and exit-code header. Update the comment in `stage_usage` that names the
      converge pass.
      Automatic verification: `uv run pytest -q plugin/tests/test_derive.py
      plugin/tests/test_workflow_metrics.py plugin/tests/test_record_cost.py &&
      uv run pytest -q`
- [x] 4. The spec lint in `--check` (AC12, AC13, AC14, AC6). Files: — `iterations: 2`
      `plugin/bin/workflow_metrics.py`, `plugin/bin/spec_forms.py`, new
      `plugin/tests/test_spec_lint.py`, new fixtures
      `plugin/tests/fixtures/consumer-specs/00{1..9}-spec/SPEC.md`, and the eval scaffolds
      that the lint turns red.
      Copy the consumer fixtures with
      `awk 'NR==1,/^---$/ && NR>1' <consumer SPEC.md>` for each of the nine specs (path in
      the Approach), plus a line `# SPEC 00N — consumer`. Name the folders generically, so
      no domain word enters `plugin/`.
      Tests first:
      - `test_an_ac_without_a_matrix_row_is_reported[plan-draft|plan-approved|implemented]`:
        AC1–AC3 in SPEC, rows AC1 and AC3, so exit 1 and stderr names `AC2`. A row
        `| AC1, AC2 |` counts for both.
      - `test_a_manual_item_without_a_pass_line_is_reported`: two items, one with
        `Pass when:`, so the other is named. The Polish literal `Zaliczony, gdy:` passes in
        a Polish PLAN. A section of one `n/a — reason` line passes.
      - `test_unlinted_statuses_pass[spec-draft|spec-ready|done]`: the same broken PLAN
        passes, with the metrics each status needs.
      - `test_no_plan_reports_every_ac`.
      - `test_consumer_specs_pass_the_check`: each of the nine fixtures.

      Change: `check()` calls the lint for the three statuses. The pass literals come from
      a new `sections.md` row `pass-condition` (`Zaliczony, gdy:` / `Pass when:`), added in
      this step, not in step 9, because the lint reads it at run time. The parity tests in
      `test_templates_language.py` then need the row in `MAP_SNAPSHOT` and the literal in
      each PLAN template (`check_occurs`), so this step also gives the `### Manual` /
      `### Ręczna` placeholder of `PLAN.en.md` and `PLAN.pl.md` its pass line. The
      fixtures of step 3 already carry matrix rows and a pass line (see there). Then run
      `plugin/tests/test_eval_cases.py`, which runs `--check` on every stage scaffold.
      Make each red scaffold pass by giving its PLAN fixture the missing matrix rows or
      `Pass when:` lines. Change nothing else in a case.
      Automatic verification: `uv run pytest -q plugin/tests/test_spec_lint.py
      plugin/tests/test_eval_cases.py plugin/tests/test_templates_language.py
      plugin/tests/test_derive.py tests/test_spec_metrics.py && uv run pytest -q`

### Group 2 — The scripted close

- [x] 5. `--close` preconditions and the test harness (AC19, AC22, AC24). Files: new — `iterations: 0`
      `plugin/bin/workflow_close.py`, `plugin/bin/workflow_metrics.py`, new
      `plugin/tests/test_close.py`.
      The harness:
      - A fixture `lane`: a temporary repository with a bare remote. The branch
        `feat/001-demo` is pushed with upstream, git identity is set by `-c`/env, and no
        hooks run.
      - `.claude/workflow.json` holds `protectedBranches: ["stable"]` and
        `docs.backlog: "docs/BACKLOG.md"`, and `docs/BACKLOG.md` exists.
      - `specs/001-demo/SPEC.md` has status `implemented` and every key that `implemented`
        needs. `PLAN.md` is complete in the fixed forms, so `--derive` reproduces the block,
        and the balance holds at `done`. It has a matrix row per AC and a manual pass line,
        because the lint applies at `implemented`.
      - A stub `gh`: a Python script in a temporary `bin/` put first on `PATH`. It answers
        `pr view`, `run list`, `run view` and `run rerun` from a JSON state file
        (`GH_STUB_STATE`). `run list` answers come from a queue whose last entry repeats.
        Each call is appended to `GH_STUB_LOG`.
      - `CLAUDE_CONFIG_DIR` points at an empty directory. `PIPELINE_CLOSE_POLL_SECONDS=0`
        and `PIPELINE_CLOSE_TIMEOUT_SECONDS=5`.

      Tests first. `test_close_refuses[main|master|stable|status|dirty|untracked|no-pr|closed-pr]`:
      each exits 1. SPEC.md stays byte-identical, HEAD and the remote do not move, and stderr
      is one line `close stopped at <step>: …; committed: no, pushed: no`.
      Change: `close(spec_dir) -> int`, with the preconditions only so far, and
      `--close <spec-dir>` in `main`, exclusive with the other modes.
      Automatic verification: `uv run pytest -q plugin/tests/test_close.py &&
      uv run pytest -q`
- [x] 6. `--close` from cost to green (AC20, AC22). Files: `plugin/bin/workflow_close.py`, — `iterations: 2`
      `plugin/tests/test_close.py`.
      Tests first:
      - `test_close_green_path`: exit 0. HEAD's subject is `docs: close SPEC 001 demo`,
        and that commit changes `specs/001-demo/SPEC.md` only. The status is `done`, there
        is a `stage_history` entry `"done — <today>"`, and `finished_at` matches
        `%Y-%m-%dT%H:%M`. The remote branch equals HEAD, and the `gh` log has a `run list`
        for the new head after the push.
      - `test_a_red_check_restores_the_spec`: a gate entry that leaves the balance off. The
        exit is non-zero, SPEC.md is byte-identical to the start, and there is no commit.
      - `test_red_then_green_after_one_rerun`: exactly one `run rerun <id> --failed`, and
        exit 0.
      - `test_red_twice_stops`: exit 5, with `committed: yes, pushed: yes`.
      - `test_a_failed_push_stops`: the remote URL is broken after setup. Exit 4, with
        `committed: yes, pushed: no`.
      - `test_every_stop_prints_one_state_line`: across the cases above, stderr has
        exactly one `close stopped at` line.
      - `test_cost_warnings_do_not_stop_the_close`: no transcripts, and exit 0 anyway.
      - `test_a_failed_commit_restores_the_spec`: the commit is made to fail (for example
        a `pre-commit` hook in the fixture repository that exits 1). Exit 4,
        `committed: no, pushed: no`, SPEC.md byte-identical to the start, and the tree
        clean, so a second `--close` is not refused for a dirty tree.

      Change, in the order of AC20:
      1. `record_cost(spec_dir, default_transcripts())`, ignoring its return.
      2. Status, `stage_history` and `finished_at` (`write_costs`).
      3. `derive` then `check`, with a restore on red.
      4. A flaky-check placeholder, which step 7 fills.
      5. `git add <SPEC.md>` and commit. Every stop before the commit lands (red check,
         flaky job, failed commit) restores SPEC.md to its bytes at the start and unstages
         it, so the tree is clean and the status is still `implemented` for the next run.
      6. `git push origin <branch>`.
      7. Wait, then re-run once with `gh run rerun <id> --failed` for every failed run, and
         wait again.

      Print the name of a job that passed only on that re-run on stdout, and exit 0.
      Automatic verification: `uv run pytest -q plugin/tests/test_close.py &&
      uv run pytest -q`
- [x] 7. The flaky check and resuming (AC21, AC22). Files: `plugin/bin/workflow_close.py`, — `iterations: 0`
      `plugin/tests/test_close.py`.
      Tests first:
      - `test_a_flaky_job_without_a_backlog_entry_stops`: the PR head's run has attempt 2,
        and job `plugin` is `failure` in attempt 1 and `success` in attempt 2. Exit 3,
        stderr names `plugin` and the run URL, there is no commit, and SPEC.md is
        byte-identical to the start with a clean tree (a status left at `done` without the
        close commit would make every later `--close` refuse).
      - `test_a_flaky_job_in_the_backlog_passes`: `docs/BACKLOG.md` contains `plugin`, and
        the exit is 0.
      - `test_resume_after_a_stop_at_the_wait`: after the exit 5 of step 6, switch the stub
        to green and run again. Exit 0, the commit count is unchanged, and the push is
        repeated without error.
      - `test_resume_after_a_failed_push`: repair the remote, run again, and get exit 0 with
        the remote equal to HEAD.
      - `test_done_without_the_close_commit_is_refused`.

      Change: the flaky check reads `docs.backlog` through `load_sections`, and the resume
      detection follows the Approach.
      Automatic verification: `uv run pytest -q plugin/tests/test_close.py &&
      uv run pytest -q`

### Group 3 — Removing the rituals from the stage text

- [x] 8. Delete the three eval cases (AC1, AC2, AC4). Files: — `iterations: 1`
      `plugin/evals/implement-converge-finds-missing-ac/`,
      `plugin/evals/implement-escalates-on-never-red-test/` and
      `plugin/evals/implement-stops-at-group-boundary/` (deleted),
      `plugin/tests/test_eval_cases.py`, `tests/test_eval_receipt.py`.
      Tests first: `tests/test_eval_receipt.py::test_no_rule_names_a_removed_case` checks
      that the three directories are absent and that no name of them is in
      `scripts/eval_receipt.py` or in `tests/test_eval_receipt.py`'s `SUITE`. Replace that
      synthetic entry with `implement-example-case`.
      Change: delete the directories. Remove the three cases from `NEW_CASES` and
      `WRONG_BEHAVIOUR`, and their fixture tests (the sections headed
      `# implement-escalates-on-never-red-test`, `# implement-converge-finds-missing-ac` and
      `# implement-stops-at-group-boundary`). Leave `plugin/evals/last-run.json` as it is,
      because the owner's release run rewrites it.
      Delete `plugin/tests/test_converge.py`, `plugin/tests/test_test_first.py` and
      `plugin/tests/test_chunked_implementer.py` in this step, not in step 10:
      `test_chunked_implementer.py` reads the grader of the deleted
      `implement-stops-at-group-boundary` case and asserts `### Group 1 — ` and
      `## Chunk notes` in the plan-review fixture that step 9 changes, so it would turn the
      suite red here and in step 9. The three files pin only ritual text that steps 9–15
      remove.
      Automatic verification: `uv run pytest -q tests/test_eval_receipt.py
      plugin/tests/test_eval_cases.py && uv run pytest -q`
- [x] 9. Templates and the section map (AC2, AC4, AC11, AC13). Files: — `iterations: 1`
      `plugin/templates/{PLAN.en.md,PLAN.pl.md,sections.md}`,
      `plugin/tests/test_templates_language.py`, `plugin/tests/test_language_contract.py`,
      `plugin/tests/test_derive.py`, the PLAN fixtures in
      `plugin/evals/plan-review-escalates-on-dependency/scaffold.sh` and
      `plugin/evals/plan-review-approves-polish-owner-decision/scaffold.sh`,
      `plugin/tests/test_eval_cases.py`.
      Tests first:
      - `test_the_ac_matrix_has_three_columns`: `| AC | Steps | Proving test |` and
        `| AC | Kroki | Test dowodzący |`. It replaces `test_the_ac_matrix_has_the_red_column`.
      - `test_the_section_map_has_no_group_rows`: no `step-group` or `chunk-notes`, and a
        `pass-condition` row with `Zaliczony, gdy:` and `Pass when:`.
      - `test_templates_give_the_fixed_forms[en|pl]`: each template carries
        `` `iterations: ``, `` `major` ``, `- **F`, `` `gate` ``, `` `accepted`: ``,
        `` `decision` ``, `` `permission` ``, `` `tooling` ``, its pass literal, and no
        `### Group`/`### Grupa` or chunk-notes heading.
      - `test_derive.py::test_the_bare_template_derives_nothing`: a PLAN copied from each
        template counts no step, entry or finding.
      - Update the snapshots in `test_templates_language.py`.

      Change, in both templates:
      - a three-column matrix;
      - `## Steps` without a group heading, with the step line showing the iteration note;
      - `### Manual` with an item and its `Pass when:` line, or `n/a — <reason>`;
      - `## Chunk notes` removed;
      - each placeholder (`_(…)_`, one line, which `--derive` ignores) giving its fixed
        form: owner decisions, review log, deviations and final review.

      Edit `sections.md` as tested (the `pass-condition` row is already there from step 4;
      this step removes `step-group` and `chunk-notes`). Bring the two plan-review fixtures to the new
      headings. Simplify `normalised()` in `test_eval_cases.py`, and give the prefix-literal
      test in `test_language_contract.py` a synthetic literal in place of `### Group N — `.
      Automatic verification: `uv run pytest -q plugin/tests/test_templates_language.py
      plugin/tests/test_language_contract.py plugin/tests/test_derive.py
      plugin/tests/test_eval_cases.py && uv run pytest -q`
- [x] 10. `implement` and the implementer's body (AC1–AC4, AC8, AC10, AC17). Files: — `iterations: 0`
      `plugin/skills/implement/SKILL.md`, `plugin/agents/implementer.md` (outside its
      contract sections), new `plugin/tests/test_pipeline_loop.py`,
      `plugin/tests/test_stage_skills.py`, `plugin/tests/test_stage_contract.py`,
      `plugin/tests/test_record_cost.py` (comment only).
      Tests first, in `test_pipeline_loop.py`, with text compared whitespace-collapsed:
      - `test_implement_has_no_ritual_sections`: no `## Test-first evidence`,
        `## Converge pass` or `## Chunk mode`, and the implementer body has no `CHUNK`,
        `chunk` or `converge`.
      - `test_implement_keeps_test_first_guidance`: one paragraph naming the proving test
        written and run before the product change. A green-before test either does not
        exercise the AC and is rewritten, or the behaviour exists, which is a gap in the
        SPEC.
      - `test_implement_ticks_with_the_iteration_note`: the Procedure's tick names
        `` `iterations: <k>` ``, says that a missing note is never zero, and says the note
        counts iterations beyond the first attempt.
      - `test_implement_installs_accepted_dependencies`: names `## Owner decisions`,
        "unaccepted" plus escalation, "beyond what the change needs", "its own Bash call",
        and `uv add`, `uv lock`, `uv sync` and `npm install`.
      - `test_implement_deviation_form`: the `major` token.
      - `test_every_stage_closes_with_derive_then_check` and
        `test_no_skill_counts_a_derived_key`, both parametrized over the stage skills,
        with only `implement` enabled in this step. The other skills join in steps 11–14.
        The closing step has `workflow_metrics.py --derive <spec-dir>` before
        `workflow_metrics.py --check <spec-dir>`, and names no key from
        `workflow_metrics.DERIVED` (a new tuple; see the Risks).

      Change: rewrite the skill. Procedure step 1 drops chunk mode. Step 2 becomes test
      first → change → loop → tick with the note → commit. Step 3 uses the deviation form.
      Step 5 (converge) goes. Finish: status `implemented` + `stage_history`, then
      `--derive`, then `--check`, the escalation path and the push. Add a short
      "Dependencies" rule to Overriding rules. The Handoff drops the converge passes and the
      chunk. (The three ritual test files are already gone in step 8.) Update `CLOSING_STEPS["implement"]`,
      `test_implement_steps_counts_the_planned_steps_too` and
      `test_implement_records_the_split_metrics` in `test_stage_skills.py`. Update the
      implementer metrics-line test in `test_stage_contract.py`, whose new line is
      `implement_steps`, `implement_iterations`, `deviations_minor`, `deviations_major`.
      Reword the chunk comment in `test_record_cost.py` to "several implementer agents".
      Automatic verification: `uv run pytest -q plugin/tests/test_pipeline_loop.py
      plugin/tests/test_stage_skills.py plugin/tests/test_stage_contract.py
      plugin/tests/test_prompt_audit.py plugin/tests/test_prompt_style.py && uv run pytest -q`
- [x] 11. `plan` and `plan-review` (AC2, AC4, AC10, AC13, AC18). Files: — `iterations: 0`
      `plugin/skills/plan/SKILL.md`, `plugin/skills/plan-review/SKILL.md`,
      `plugin/tests/test_pipeline_loop.py`, `plugin/tests/test_stage_skills.py`.
      Tests first:
      - `test_plan_requires_the_pass_line` (both skills name `Pass when:` and the
        section map).
      - `test_plan_writes_no_owner_step`: `plan` says that no step is performed by the
        owner. `plan-review` treats such a step as `major`, fixes it in place, and says that
        `### Manual` stays allowed.
      - `test_plan_review_finding_form` (the list item that starts with the severity token).
      - `plan` and `plan-review` join the two step-10 parametrized tests.
      - No `## Step groups`, `**groups:**`, `**test-first:**` or "fourth column".

      Change. `plan`:
      - drop the Step groups section and the step-5 grouping sentence;
      - make step 6 three columns;
      - step 5 requires the pass line, and no owner step;
      - step 8 sets `started_at` if missing, runs `--derive` then `--check`, and no longer
        sets `plan_steps` or `escalations`.

      `plan-review`:
      - drop the groups and test-first checklist points;
      - add a point that the proving test comes before the change (without the column),
        and a point on the manual pass line and owner steps;
      - step 4 uses the finding form;
      - step 6 writes `plan_changes`, runs `--derive` then `--check`, and no longer
        counts the blockers and majors.

      Update `CLOSING_STEPS`.
      Automatic verification: `uv run pytest -q plugin/tests/test_pipeline_loop.py
      plugin/tests/test_stage_skills.py plugin/tests/test_prompt_audit.py
      plugin/tests/test_language_contract.py && uv run pytest -q`
- [x] 12. `final-review` and the reviewer's body (AC2, AC3, AC10, AC23, AC27). Files: — `iterations: 0`
      `plugin/skills/final-review/SKILL.md`, `plugin/agents/reviewer.md` (outside the
      contract sections), `plugin/tests/test_pipeline_loop.py`,
      `plugin/tests/test_stage_skills.py`, `plugin/tests/test_review_depth.py`.
      Tests first:
      - `test_final_review_tests_break_the_code`: the tests perspective proves that a test
        tests something by breaking the code it covers.
      - `test_final_review_notes_one_context`: without the `Agent` tool, the report and
        SUMMARY carry the sentence that the three perspectives ran in one context and are
        not independent.
      - `test_final_review_finding_form` (`- **F<n>**`).
      - `test_final_review_apply_ends_at_green_ci`: apply ends at a PR with green CI and
        status `implemented`, the flaky-retry backlog entry goes into apply's own commit,
        apply never sets `done`, and run on its own it runs `workflow_metrics.py --close
        <spec-dir>` last, as a background Bash call (`run_in_background`), the same rule
        as in step 14.
      - `final-review` joins the two step-10 tests.
      - Replace `test_compliance_checks_the_red_column` with a check that the compliance
        perspective names no red record.
      - Rework `test_apply_mode_gates_done_on_the_checker` into "apply runs `--derive`
        and `--check` before its commit".

      Change: report step 4 uses the finding form, runs `--derive`/`--check`, and adds the
      one-context sentence. The reviewer body names the same sentence for SUMMARY.
      Apply step 2 drops the counting. Steps 4–5 end at green CI with
      status `implemented`. Step 6 adds the standalone `--close`. Update the description
      line and the Input/output. Update `CLOSING_STEPS`.
      Automatic verification: `uv run pytest -q plugin/tests/test_pipeline_loop.py
      plugin/tests/test_stage_skills.py plugin/tests/test_review_depth.py && uv run pytest -q`
- [x] 13. The stage contract in five files (AC1, AC2, AC4, AC10, AC15). Files: — `iterations: 1`
      `plugin/skills/ship/SKILL.md` and `plugin/agents/{planner,plan-reviewer,implementer,
      reviewer}.md` (the `## Stage agent contract` and `## Escalation triggers` sections),
      `plugin/README.md` (only `### The \`RESULT\` contract` and `### Escalation triggers`),
      `plugin/tests/test_stage_contract.py`, `plugin/tests/test_readme.py`,
      `plugin/tests/test_prompt_style.py`.
      Tests first:
      - `test_the_result_block_has_kind`: in ship and README the fields are `STATUS`,
        `METRICS`, `KIND`, `ESCALATION`, `SUMMARY`, with the values `decision`,
        `permission` and `tooling`. A missing or invalid `KIND` counts as `decision`.
      - `test_the_removed_triggers_are_gone`: no "green before the change" and no "second
        converge pass", in ship or README. It replaces `test_the_trigger_list_names_the_spec_010_escalations`.
      - The contract states that the derived counters come from `--derive`. It replaces
        `test_the_contract_leaves_escalations_to_the_orchestrator`.
      - Update `test_the_result_block_matches_the_contract`.

      Change: the identical contract text in all five files. The `CHUNK:` line is out and
      `KIND:` is in. The metrics bullet says that the derived keys (`escalations` among
      them) come from the forms and `--derive`, and that agents write only the keys their
      skill names. Two triggers go. README: the same block, the chunk paragraph out, a
      `KIND` sentence in. Add `KIND` to `ALLOWED` in `test_prompt_style.py`.
      Automatic verification: `uv run pytest -q plugin/tests/test_stage_contract.py
      plugin/tests/test_readme.py plugin/tests/test_prompt_style.py && uv run pytest -q`
- [x] 14. `ship`: state, result protocol, start and closing (AC1, AC4, AC10, AC16, AC23, — `iterations: 1`
      AC25). Files: `plugin/skills/ship/SKILL.md`,
      `plugin/tests/test_ship_cost_and_models.py`, `plugin/tests/test_pipeline_loop.py`.
      Tests first:
      - `test_the_start_message_names_every_stage_model`: Start names `plan`,
        `plan-review`, `implement` and `final-review`, the alias passed to `Agent`, and
        "session model" for `inherit` or no entry.
      - `test_ship_stops_on_the_third_decision`: the Result protocol records `KIND` in the
        fixed-form entry, counts only `decision` entries of the same stage toward the third
        STOP, and has no "Increment `metrics.escalations`".
      - `test_closing_runs_close_after_apply`: `workflow_metrics.py --close
        <docs.specsDir>/NNN-<slug>` comes after the `reviewer/apply` RESULT and before
        `PushNotification`. A non-zero exit asks the owner with "resume the closing step
        only" first, "(Recommended)", and no new reviewer. No `--record-cost` commit step
        remains. `--close` runs as a background Bash call (`run_in_background`), and
        `ship` reads its exit code and its stop line when the call ends: the wait for CI
        (timeout 3600 s by default, twice with the re-run) outlasts the foreground Bash
        limit (120 s by default, 600 s at most), and a killed call would read as a stop
        with no state line. Rework the five Closing tests in this file.
      - The State table names `--close` → `done` and no chunk.
      - The guardrail says that `--close`, not `ship`, sets `done`.
      - The gate step records the `gate` entry form.
      - `ship` joins `test_no_skill_counts_a_derived_key`.
      - `test_no_ritual_returns`: no "converge pass", `converge_gaps`, "Red before the
        change", "Czerwony przed zmianą", "Test-first evidence", "chunk mode", "Chunk
        notes", "Notatki chunków", `CHUNK:`, `implement_chunks`, `### Group N` or
        `### Grupa N` in `plugin/skills/`, `plugin/agents/` or `plugin/templates/`.

      Change: rewrite the State table, Start (step 3 writes `started_at` only, and a new
      step 4 is the model message), "Starting a stage agent" (drop "every chunk"), the
      Result protocol, the Gate and Closing:
      1. Take the PR link and CI status from the RESULT.
      2. Run `--close` in the background (`run_in_background`) and wait for it to end.
      3. On exit 0 send the notification.
      4. On a non-zero exit ask the owner, with options: resume the closing step only
         (Recommended), `reviewer` `apply` again with the stop line, or the owner takes over.
      5. Write the summary, with any job `--close` named.

      Then the Guardrails.
      Automatic verification: `uv run pytest -q plugin/tests/test_ship_cost_and_models.py
      plugin/tests/test_pipeline_loop.py plugin/tests/test_stage_contract.py
      plugin/tests/test_review_depth.py && uv run pytest -q`

### Group 4 — README and release

- [x] 15. The README (AC1, AC2, AC4, AC5, AC23, mechanics of AC7–AC28). Files: — `iterations: 3`
      `plugin/README.md`, `plugin/tests/test_readme.py`.
      Tests first:
      - `test_the_readme_has_no_ritual`: no "converge pass", "Red before the change",
        "Chunk notes", `CHUNK` or "The chunked implementer". `converge_gaps` and
        `implement_chunks` are allowed only in the one legacy-key sentence of Workflow
        metrics.
      - `test_the_status_table_names_close`: `implemented` + decisions → PR with green CI,
        and `--close` → `done`.
      - `test_the_readme_documents_derive_lint_and_close`: `--derive`, the fixed forms,
        `Pass when:`, `--close` with its exit codes, `escalations_permission`,
        `escalations_tooling` and "lower bound".
      - The `implement.chunked` row is marked retired in 0.9.0.
      - `test_the_readme_describes_test_first_and_converge` becomes a test-first-guidance
        and nit-cap test.

      Change, in order: the config row, Models and effort (no converge), the statuses
      table, Implementation and review (the three paragraphs out; test-first guidance,
      dependencies, the scripted close in), Workflow metrics (the example block, who writes
      what, `--derive`, the lint in `--check`, `--close` (with its need for CI checks on
      the PR and the background call), the lower-bound label, legacy keys).
      Automatic verification: `uv run pytest -q plugin/tests/test_readme.py &&
      uv run pytest -q`
- [x] 16. Release 0.9.0 and the documents (AC29). Files: — `iterations: 0`
      `plugin/.claude-plugin/plugin.json`, `plugin/CHANGELOG.md`, `docs/DECISIONS.md`,
      `docs/ROADMAP.md`, `docs/BACKLOG.md`, `docs/CONVENTIONS.md` (the Workflow metrics
      paragraph: `--close` runs the cost), new `plugin/tests/test_release_0_9_0.py`,
      `tests/test_documents.py`.
      Tests first:
      - `test_release_0_9_0.py`: the version is `0.9.0`, and `## 0.9.0` names the converge
        pass, the red column ("Red before the change"), the chunked implementer,
        `implement.chunked` as retired, the three eval cases, `--derive`, `--close`,
        `KIND` and a consumer impact.
      - `tests/test_documents.py`:
        - `test_decisions_record_spec_014`: one row for `--close` setting `done`, one for
          derived metrics in the frontmatter. The `--close` row also says that the script
          now reads `protectedBranches` and pushes outside the guard's view, because the
          2026-09-22 row says the key is read by the guard only;
        - `test_roadmap_ticks_spec_014`: the item is ticked;
        - `test_backlog_after_spec_014`: no P2 item about calling `workflow_metrics.py` by
          name, and the cost item says the label is done and the fix waits.

      Change accordingly. In `CONVENTIONS.md`, `ship` now runs `--close`, which runs
      `--record-cost`.
      Automatic verification: `uv run pytest -q plugin/tests/test_release_0_9_0.py
      tests/test_documents.py plugin/tests/test_readme.py && uv run pytest -q`
- [x] 17. Full verification (AC30). No new files. — `iterations: 0`
      Automatic verification: `bash scripts/check.sh`, then `git grep -n -i -E "converge
      pass|Red before the change|Chunk notes|CHUNK:" -- plugin/skills plugin/agents
      plugin/templates`, expecting no output.

## Risks and traps

- **`--close` bypasses the guard's view.** The Bash call is `workflow_metrics.py --close …`.
  The `git push` and `gh` calls inside it are not inspected. The script therefore checks
  `main`, `master` and `protectedBranches` itself, pushes only `origin <current branch>`
  without force, and touches only SPEC.md. Keep it that way, and record this in the
  DECISIONS row.
- **The lint on this spec.** From step 4, `tests/test_spec_metrics.py` lints
  `specs/014-…` at `plan-approved` and `implemented`. This PLAN has a matrix row for AC1–AC31
  and a `Pass when:` line for its manual item. Keep both when a deviation edits the plan.
- **The derived-key list is one tuple** (`DERIVED` in `workflow_metrics.py`).
  `test_no_skill_counts_a_derived_key` imports it, so the skills and the script cannot drift
  apart. A skill may still name a derived key to say that `--derive` writes it. The test
  therefore reads the closing step only, and forbids "set"/"count" next to a derived key,
  not the key itself.
- **`write_costs` with string values:** `finished_at` must be written unquoted
  (`2026-10-05T14:00`), as `--check` and the existing specs expect.
- **`gh` JSON fields:** `attempt` exists in `gh run list --json` and `gh run view --json`
  (gh ≥ 2.40), and `--attempt` exists in `gh run view`. When CI's `gh` is older, nothing
  breaks, because the tests use the stub. The canary in the manual section is the real
  check.
- **The `run list` queue in the stub:** a missing new-head run must not read as green.
  `wait` requires at least one run before it judges. A consumer with no Actions workflow
  never gets a run, so its `--close` ends at the timeout with exit 5 and
  `committed: yes, pushed: yes`. The README's `--close` paragraph says that the close
  needs CI checks on the PR, as the final review's green-CI rule already does.
- **`--close` and the Bash time limit:** a foreground Bash call ends at 600 s at most,
  and the CI wait can run longer. `ship` (step 14) and a standalone `final-review` apply
  (step 12) run `--close` in the background. A call that dies anyway leaves a state the
  resume path handles (step 7).
- **Stops before the commit restore SPEC.md** (steps 6 and 7). A stop that left the
  status at `done` without the close commit would be refused by every later run, both as
  a dirty tree and as `done` without the commit.
- **Eval fixtures:** after step 4, every stage scaffold must pass the lint. A fixture that
  fails is fixed by adding rows or pass lines, never by changing the case's point.
  `plugin/evals/last-run.json` still names the removed cases until the owner's release run.
  `pre-push` compares the receipt with `case.yaml` counts, so this is the owner's eval run
  before the tag, not this PR's.
- **Polish:** new Polish text goes only into `PLAN.pl.md` and `sections.md`
  (`test_english_only.py`).
- **Domain words:** the consumer fixtures carry frontmatter only, in generic folder names
  (`test_no_domain_references.py`).

## End-to-end verification

### Automatic (performed by /pipeline:implement)

- `bash scripts/check.sh` is green. It covers `claude plugin validate --strict` for the
  plugin and the marketplace, ruff, black and pytest.
- `python3 plugin/bin/workflow_metrics.py --derive specs/014-pipeline-loop-fewer-rituals`
  on this spec at `implemented` names `implement_iterations` as unwritten, because this
  plan's ticks come from 0.8.2 without notes, and exits 0. `git diff --stat` then shows
  only metric lines changed. Record the output here, then `git checkout` the file.
- `python3 plugin/bin/workflow_metrics.py specs` renders the report: legacy columns are
  present only because old specs carry them, and every cost line has the lower-bound label.
- `python3 plugin/bin/workflow_config.py --check` in a scratch copy of a repository whose
  `workflow.json` has `"implement": {"chunked": false}` exits 0 with the notice.

### Results

- 2026-10-05: `bash scripts/check.sh` -> ALL GREEN (2380 tests, `claude plugin validate --strict` for plugin and marketplace). `git grep` for the ritual words in skills, agents and templates -> no output.
- `workflow_metrics.py --derive` on a copy of this spec at `implemented` -> named `implement_iterations` (steps 1-17 ticked without an `iterations` note) and the five `final_review_*`/`findings_*` keys as unwritten, exit 0; the diff showed only metric lines (`implement_steps`, `deviations_*`, `escalations_*`). The notes were then added and the real run wrote the values.
- `workflow_metrics.py specs` -> report rendered; `converge_gaps` shows only because old specs carry it; all three cost lines end with the lower-bound label.
- `workflow_config.py --check` on a scratch repository with `"implement": {"chunked": false}` -> exit 0 and the retired-key notice on stderr.

### Manual (performed by the owner)

- The canary (AC31): before the tag, follow `docs/CONVENTIONS.md`. Run one small spec
  through `/pipeline:ship` in a consumer clone, on the working-tree plugin
  (`claude --plugin-dir <clone>/plugin`).
  Pass when: the spec reaches `done` with no converge pass, red column or chunk note in its
  PLAN.md, `workflow_metrics.py --check <spec-dir>` exits 0, the `metrics:` block carries
  the keys of AC7, and `gh pr checks <nr>` is green on the last commit
  `docs: close SPEC NNN <slug>`.

## Definition of Done

- [x] all steps ticked
- [x] `bash scripts/check.sh` fully green
- [x] end-to-end verification (automatic) performed, result recorded here
- [x] `docs/ROADMAP.md` updated; `docs/DECISIONS.md` / domain documents from the map
      in `CLAUDE.md`, if applicable
- [x] spec status: `implemented`

## Owner decisions

_(appended by /pipeline:ship or a stage on escalation: date, stage, question, decision)_

## Review log

2026-10-05, plan review (plugin 0.8.2). Findings are written in the fixed form this plan
introduces, so `--derive` can read them later.

Findings:

- `major` — Step 4 depended on step 9. The lint reads the pass literal from the
  `pass-condition` row of `sections.md`, which step 9 added. That row cannot be added
  alone, because `test_the_section_map_matches_the_snapshot` (`MAP_SNAPSHOT`) and
  `test_every_map_row_occurs_in_its_template` need it in the snapshot and in both PLAN
  templates. Fixed: step 4 adds the row, the snapshot entry and the templates' pass line.
  Step 9 only removes `step-group` and `chunk-notes`.
- `major` — Steps 8 and 9 would leave the suite red until step 10.
  `test_chunked_implementer.py::test_the_group_boundary_grader_asks_for_the_final_message`
  reads the grader of the case step 8 deletes, and
  `::test_the_english_plan_review_fixture_has_groups` asserts the groups that step 9
  removes from the fixture. Fixed: the three ritual test files are deleted in step 8, and
  step 10 no longer deletes them.
- `major` — `--close` waits up to 3600 s by default, twice with the re-run, but a
  foreground Bash call ends at 120 s by default and 600 s at most. `ship` would see a
  killed call with no state line. Fixed: steps 12 and 14 run `--close` as a background
  Bash call, and the tests check it. Added to Risks.
- `major` — A flaky-job stop (exit 3) or a failed commit (exit 4) happened after SPEC.md
  had been set to `done`, and only the red check restored it. The tree was then dirty and
  the status `done` without the close commit, so every later `--close` refused and the
  resume of AC22 was impossible. Fixed: every stop before the commit restores SPEC.md
  (step 6 change, item 5). The step 7 flaky test asserts it, and a new step 6 test
  `test_a_failed_commit_restores_the_spec` covers it too.
- `minor` — The step 3 `--derive` fixtures and the step 5 close harness have status
  `implemented`, and their `--check` would turn red once step 4's lint runs. Fixed: both
  carry a matrix row per AC and a manual pass line.
- `minor` — `docs/DECISIONS.md` 2026-09-22 says only the guard reads `protectedBranches`.
  `--close` now reads it too. Fixed: the step 16 decisions test requires the `--close` row
  to say so.
- `minor` — A consumer with no Actions workflow never gets a run for the head, so its
  `--close` always ends at the timeout. Fixed: added to Risks, and the step 15 README
  paragraph names the need for CI checks.

Checked and found sound:

- Anti-anchoring: my own approach was code first (`--derive`, lint, `--close`, retired
  key) with subprocess tests, then the text removals, then the docs and the release. I also
  expected a stub `gh` with a temporary git remote, and fixtures from the consumer's
  frontmatter. The plan does all of this. The differences I found were the four `major`
  findings above.
- Coverage: every AC from AC1 to AC31 has a matrix row, steps and a proving test, and the
  matrix matches the steps. AC30 is `n/a` and AC31 is `manual`.
- Compliance: `docs/CONVENTIONS.md` read in full. Standard library only in `plugin/bin`,
  scripts tested as subprocesses, no new eval case, receipt and canary left to the owner,
  calls by name through `PATH`. I searched `docs/DECISIONS.md` for "done", "record-cost",
  "escalations", "push" and "guard". The plan breaks no row: the language-contract row
  (code tokens in English, prose in `language`) fits the fixed forms, and the cost row
  (four stage subagents) is unchanged by `--close`.
- `scripts/git-hooks/pre-push` checks `last-run.json` only for release tags, so deleting
  three eval cases does not block the lane push. The Risks entry on this holds.
- `write_costs` formats values with an f-string, so a `str` `finished_at` is written
  unquoted, as the plan expects.
- The consumer frontmatter (nine specs) holds only statuses, dates and metric keys, with
  no domain word. With generic folder names, `test_no_domain_references.py` stays green.
- `gh` 2.101 is installed locally. `attempt` exists in `gh run list --json`.
- Minimality: the two new modules keep `workflow_metrics.py` readable, and the command
  stays `workflow_metrics.py`, as SPEC decision 9 needs. Nothing goes beyond the SPEC.
- Feasibility: once the fixes are in, no step depends on a later one. No migration and no
  new dependency, which matches the Owner summary and SPEC owner decision 14.
- E2E: the automatic part runs on the working tree. The only manual scenario is the
  canary, which cannot be automated, and it has a pass condition.
- Testability: every step has `Automatic verification:` with exact test paths.
- Groups: four groups and 17 steps, and no group boundary leaves work half done. The plan
  keeps the 0.8.2 groups and the fourth column on purpose, because 0.8.2 implements this
  spec. Both leave the templates only in this change.
- Test-first: every step writes its tests first, and the matrix has the fourth column.
- No step is performed by the owner.
- Language: English throughout, as `language: en` requires.

Decision: the plan is approved. All seven findings were fixed in the plan itself, none is
a blocker, and it adds no dependency and no migration, so nothing needs the owner.

### Converge pass 1 — 2026-10-05

A fresh subagent compared the diff with the SPEC and reported two gaps; I rejected both, so no step was added.

- `[contradicts] AC3 implement/SKILL.md:128` (a proving test the owner or plan gives verbatim is not rewritten, you escalate) — rejected: AC3 only asks that a test green before the change is rewritten or escalated as a SPEC gap; leaving an owner's test unrewritten and escalating is the same existing trigger, not the removed one.
- `[unrequested] workflow_close.py:227-247` (`PIPELINE_CLOSE_TIMEOUT_SECONDS`, `PIPELINE_CLOSE_POLL_SECONDS`) — rejected: the plan asks for them, AC24's tests need a zero poll, and a wait with no timeout could not end with the exit 5 AC20 and AC22 require; the README documents both.

## Deviations

- `minor` — Step 1: `test_workflow_example_covers_every_key_and_validates` in `test_init_templates.py` now expects the example to hold every schema key except the retired `implement` (the schema keeps the key so `--check` accepts it, the example omits it). The plan did not name that test, and it failed otherwise.
- `minor` — Step 3: the derive fixtures are one `plugin/tests/fixtures/derive/{SPEC,PLAN}.md`, and the Polish copy is built from `templates/sections.md` at test time, instead of a static `{en,pl}/` pair. `test_english_only.py` keeps Polish letters out of every file outside its allowlist, and the generated copy tests the same headings and pass literal without adding an allowlist entry.
- `minor` — Step 3: `spec_forms.steps()` treats a step line whose text starts with `<` or `…` as the template's placeholder, so a PLAN copied from a template counts no step (the plan's step 9 test needs it).
- `minor` — Step 4: the lint turned more eval scaffolds red than the plan listed. Three scaffolds spelled the matrix heading `## AC -> steps matrix` (the literal has `→`), `implement-escalates-on-failing-test` had no matrix, and the Polish mirror listed `brak — …` as a manual item; each was brought to the form the lint reads (`n/a — …` for the last), and nothing else in a case changed.
- `minor` — Order: step 8 was carried out before step 4's commit, because the lint made the converge eval fixture red by design (its plan misses AC2) and that case is deleted in step 8. Steps 10 and 11 were carried out before step 9, because step 9 removes the `step-group` and `chunk-notes` map rows while `plan`, `plan-review` and `implement` still quoted them, which turned the language-contract test red. Each commit is green on its own.
- `minor` — Steps 5 and 6: `workflow_close.close(spec_dir, metrics)` takes the `workflow_metrics` module as an argument rather than importing it, so there is no import cycle and the script runs as `__main__`. The stub `gh` answers `run list` for the PR head from its own `head_runs` entry, apart from the queue for the new head, so the flaky check and the wait do not consume each other's answers.
- `minor` — Step 13: `KIND:` was added to `OTHER_HEADINGS` in `test_language_contract.py`, because the contract text names the RESULT key in backticks with a colon and the test reads that as a heading.
- `minor` — Step 15: the README gained the sections `Deriving counters (--derive)` and `Closing a spec (--close)` (pinned in the heading list of `test_readme.py`), and `test_metrics_block_lists_every_counter` exempts the two legacy keys, which the README names once, in one sentence.
- `minor` — Metrics: this plan's ticks were made on 0.8.2 without `iterations` notes, so `--derive` left `implement_iterations` unwritten, as the end-to-end check expects. The notes were added at the end from the agent's own record of red runs after the first attempt of each step.

## Final review

_(filled in by /pipeline:final-review)_
