# PLAN 011 — Cost per stage, a model per stage and targeted reading

## Owner summary

- **Approach:** `workflow_metrics.py` gains seven optional counters, an either-or
  `deviations` rule in `--check`, three cost lines in the report and a
  `--record-cost <spec-dir> [--transcripts <dir>]` mode. That mode finds the spec's stage
  subagents in the transcripts by agent type, spec directory name and working directory,
  prices every API message once at a frozen table of 2026-09-24 list rates in integer
  arithmetic, and rewrites only the `cost_*` lines of SPEC.md. `workflow_config.py` accepts
  `models`, and a bad entry drops only that stage back to `inherit`. `ship` passes `model`
  to `Agent` and records cost in Closing. `implement` writes the new keys. Four stage skills
  share one identical Reading section, `idea` and `plan` list what they read and how, and
  the release is 0.8.0.
- **Main risks:** the transcript format is Claude Code's, not ours. Streamed replies log one
  message several times, the archive holds copies of the same session, and model ids can
  carry a date suffix. Each case is pinned by a fixture. A stage prompt without the spec
  directory name is not counted: the stdout table and the warning show it.
- **New dependency:** no.
- **Data migration:** no. Existing SPEC.md files do not change, and the old `deviations`
  key still passes `--check`.
- **Manual scenarios for the owner:** 1. The 0.8.0 canary: a real stage under
  `"models": {"implement": "sonnet"}` in a consumer, where the `--record-cost` table shows
  the model per stage.

## Approach

**Read context.** SPEC 011, `docs/CONVENTIONS.md`, and every code file the plan changes
were read in full: `plugin/bin/workflow_metrics.py`, `plugin/bin/workflow_config.py`, the
skills `ship`, `plan`, `plan-review`, `implement`, `final-review` and `idea`, the agents
`planner` and `implementer`, and the affected tests (`test_workflow_metrics.py`,
`test_workflow_config.py`, `test_stage_skills.py`, `test_converge.py`, `test_readme.py`,
`test_init_templates.py`, `test_language_contract.py`). The other documents were searched,
not read whole:

- `docs/DECISIONS.md`: searched for `2026-09-2[34]`, cost, `models`, effort, required key
  and `PATH`. Binding here are the 2026-09-24 cost audit and cost-unit rows, SPEC 010 (a
  new required key turns specs in progress red), 2026-09-23 (metric keys are English, the
  guard never blocks on configuration, the prompt style) and 2026-09-21 (scripts are called
  by name through `PATH`).
- `docs/ROADMAP.md`: searched for Stage 7, 0.8.0, `models`, `deviations` and cost. It gives
  the four items this spec ticks.
- `docs/BACKLOG.md`: searched for targeted, Sonnet, effort and `workflow_metrics`. P2 "by
  path" applies to the new `ship` call, and P2 "findable decisions" and P3 "perspectives
  on Sonnet" stay open.
- `docs/PROJECT.md`: searched for metric. The report requirement is extended.
- `plugin/README.md`: its configuration and metrics sections were read in full, because
  they change.

The transcripts were inspected on this machine on 2026-09-24. The facts below shape the
design.

- `subagents/agent-<id>.meta.json` holds `agentType` (`pipeline:planner` …) and, for
  nested agents, `parentAgentId` (the id without `agent-`). The implementer's converge
  subagents and the reviewer's perspectives have it.
- The first line of `agent-<id>.jsonl` is the prompt (`type: user`, `message.content` a
  string or a list of text blocks) with `cwd` and `gitBranch`. Prompts from `ship` name
  `specs/<NNN-slug>/SPEC.md`, both here and in the consumer.
- Assistant lines carry `message.id`, `message.model` and `message.usage`. One API message
  is logged once per content block (130 lines, 65 ids in one implementer transcript), and
  `output_tokens` grows on the last line. `<synthetic>` lines carry no usage. Models seen:
  `claude-opus-5`, `claude-opus-5-5` and `claude-haiku-4-5-20251001` (a date suffix).
- The archive `~/claude-transcripts-archive` nests one level deeper
  (`2026-09-24/<project slug>/…`), and dated snapshots can repeat a session.

Rates (`/claude-api` skill plus the live pricing page, fetched 2026-09-24) in cents per
million tokens, in the order input / cache write 5 min / cache write 1 h / cache read /
output:

| model id | input | write 5m | write 1h | read | output |
|---|---|---|---|---|---|
| `claude-opus-5-5` | 400 | 500 | 800 | 20 | 2000 |
| `claude-opus-5` | 500 | 625 | 1000 | 50 | 2500 |
| `claude-sonnet-5` | 200 | 250 | 400 | 20 | 1000 |
| `claude-haiku-4-5` | 100 | 125 | 200 | 10 | 500 |
| `claude-fable-5-1` | 1000 | 1250 | 2000 | 25 | 5000 |

`claude-opus-5` is added to the four models the SPEC names. Specs 001–010 and the
consumer's baseline ran on it, and without its rate the baseline could not be costed.
This answers the SPEC's open question.

**Cost (`--record-cost`), in `plugin/bin/workflow_metrics.py`.** The mode stays in the
existing script: one file on `PATH`, one allow rule, `Bash(workflow_metrics.py *)`, and no
new file for consumers to allow. It works like this:

1. **Source.** `--transcripts <dir>`, or else `$CLAUDE_CONFIG_DIR/projects` when that
   variable is set, or else `~/.claude/projects`. Claude Code keeps its transcripts in the
   same place, so a consumer with a moved config directory is not left without cost.
2. **Scan.** A recursive scan finds every `subagents/agent-*.meta.json`, which covers
   every project slug, worktree lanes and the archive's extra level. A scan limited to
   project slugs was rejected, because the default `worktree.dir` (`../worktrees`) gives a
   slug that shares no prefix with the repository's.
3. **Stage agents.** An agent is a stage agent of the spec when all three hold:
   - its `agentType` is `pipeline:<name>` or the bare `<name>`, and `<name>` is one of
     `planner`, `plan-reviewer`, `implementer` or `reviewer`;
   - its prompt contains the spec directory name as a whole path segment:
     `(?<![\w.-])011-cost-metrics-and-stage-models(?![\w.-])`;
   - the `cwd` of its first line lies inside this repository. That means the main
     checkout root (the parent of `git rev-parse --path-format=absolute --git-common-dir`,
     or `workflow_config.project_root` when git fails), the spec's own checkout root, or
     the resolved `worktree.dir` of the configuration at the main root.

   The name matches this repository's spec and no other. A same-named spec in another
   repository is excluded by the `cwd` check (AC3).
4. **Descendants.** Every agent whose `parentAgentId` chain reaches a stage agent counts
   toward that stage. This covers the final review's perspectives (AC2) and, by the same
   rule, `implement`'s converge subagents. They are part of what the stage agent spent.
   A rule for perspectives alone would leave the converge pass outside every stage.
5. **Messages.** Assistant lines are keyed by `message.id` across all files, which removes
   the per-block repeats and the archive copies. The line with the largest `output_tokens`
   wins. Lines with model `<synthetic>`, and lines without usage, are skipped. Tokens per
   type:
   - `input_tokens`;
   - `cache_creation.ephemeral_5m_input_tokens` and `ephemeral_1h_input_tokens`. When
     `cache_creation` is absent, `cache_creation_input_tokens` counts as a 5-minute write;
   - `cache_read_input_tokens`;
   - `output_tokens`.
6. **Price.** The model id loses a trailing `-\d{8}` before the rate lookup. Each stage's
   numerator is the sum of tokens × rate (cents per million tokens), in integers, and the
   stage total is rounded half up exactly once: `(numerator + 500_000) // 1_000_000`.
   Integers leave no float error, and rounding only the total is AC1's rule.
7. **Write.** Only the keys computed in this run are written, as an exact line edit inside
   the `metrics:` block. An existing `  cost_<stage>_cents:` line has its value replaced,
   and a new key is appended after the block's last line with the block's indentation.
   With no `metrics:` block, one is added before the closing `---`. Every other byte stays
   as it was. A key whose stage has no transcripts this time is left as it was, so a
   re-run after transcripts expire keeps a value measured earlier. A file whose content
   does not change is not rewritten, so `ship` commits only a real change.
8. **Exit.** Exit 0 with a warning when nothing is found, a stage is missing or a model is
   unknown (AC6), and exit 1 only when the spec directory has no readable SPEC.md.

The rejected variant was a separate `workflow_cost.py`. It would add a second script to
allow and document, while the frontmatter parsing and writing already live in
`workflow_metrics.py`.

**`--check`.** `COUNTERS` gains `converge_gaps`, `deviations_minor`, `deviations_major` and
the four `cost_*` keys, so they are known, validated as integers and reported. `deviations`
leaves the `REQUIRED` lists. A separate rule for `implemented` and `done` is satisfied by
`deviations` or by both split keys. Without either form, it reports one problem naming
both forms, worded with "requires either" and not "missing", so the joined missing-keys
line stays one line. `done` requires the old counter list without `deviations`. The new
keys are never required (SPEC decision, SPEC 010 row). Two existing tests,
`test_the_required_table_is_exactly_ac9` and `test_every_missing_key_is_named`, pin the old
table. This plan changes them explicitly (step 1), because the SPEC changes the table.

**Report.** It keeps one column per counter, so the new keys show up by themselves. Three
lines are added after the existing ones, each shown only when its denominator is above
zero:

- `Plan review cost per significant finding: <n> cents (<cents>/<findings>)` over the specs
  with `cost_plan_review_cents`;
- the same for the final review over the specs with `cost_final_review_cents`;
- `Cost per plan step: <n> cents (<cents>/<steps>)` over the specs with all four cost keys
  and `plan_steps`.

`<n>` is rounded half up to an integer.

**`models`.** `SCHEMA` gains `"models": {"plan": str, "plan-review": str, "implement": str,
"final-review": str}`, and `validate` checks each value against
`MODEL_VALUES = ("inherit", "sonnet", "opus", "haiku", "fable")`, with the message
``` `models.<stage>` has to be one of: inherit, sonnet, opus, haiku, fable ```.
`load_sections`, used by the guard and the report, validates `models` entry by entry: a bad
entry is dropped with its own warning and the others stay. That is AC14's "that stage on
`inherit`", where the section-wise default would reset every stage. `load` and `--check`
stay strict, as for every key. A helper `stage_model(config, stage) -> str` returns the
value or `"inherit"`, and the tests pin the per-stage fallback through it. `ship` is prose,
so it reads `models.<stage>` itself with the same rule: a value outside the four aliases
means no `model` parameter. Stage keys map to agents like this: `plan` → `planner`,
`plan-review` → `plan-reviewer`, `implement` → `implementer`, `final-review` → `reviewer`
(report and apply).

**Targeted reading.** One identical Reading section is added to `plan`, `plan-review`,
`implement` and `final-review`. It is pinned identical by a test, like the configuration
block (`test_stage_skills.py`). It says: SPEC, PLAN and `<docs.conventions>` in full;
`<docs.decisions>`, `<docs.roadmap>` and domain documents searched by the feature's topic
(its terms and the names of the files it changes), and read whole only when the search
leaves the question open. The reason stands beside the rule: fresh subagents paid for
documents read whole. Each skill then applies it at its own place:

- `plan` step 3 lists what it read and how in `## Approach`, as a "Read context" list like
  the one above. PLAN.md gains no new section, the templates and the section map stay
  unchanged, and the plan review can check the list there.
- `plan-review`'s compliance point checks against the decisions it found by its own search.
- `final-review` passes the rule to its perspectives.
- `idea` step 1 and its guardrail require each `## Read context` item to say "read in full"
  or "searched for <terms>".

Skill text must not quote heading-like spans outside the section map
(`test_language_contract.py`), so the new section is referred to as "the Reading section",
never in backticks.

**Patterns reused:** `section()`/`collapse()` helpers from `plugin/tests/test_converge.py`
and `plugin/tests/test_stage_skills.py` for text pins; `spec_dir()`/`run_check()` from
`plugin/tests/test_workflow_metrics.py`; `write_config()`/`repo` fixture from
`plugin/tests/test_workflow_config.py`; the "absent" README row style of `protectedBranches`.

## AC → steps matrix

| AC | Steps | Proving test | Red before the change |
|----|-------|--------------|-----------------------|
| AC1 | 3, 5 | `plugin/tests/test_record_cost.py::test_stage_cost_is_tokens_times_rates_rounded_once`, `::test_record_cost_writes_the_four_keys` | |
| AC2 | 4 | `plugin/tests/test_record_cost.py::test_perspectives_and_both_reviewer_runs_count_toward_the_final_review`, `::test_a_rerun_after_an_escalation_counts_toward_its_stage` | |
| AC3 | 4 | `plugin/tests/test_record_cost.py::test_other_specs_and_other_repositories_are_not_counted` | |
| AC4 | 4, 5 | `plugin/tests/test_record_cost.py::test_transcripts_option_reads_that_directory`, `::test_default_source_finds_worktree_lanes` | |
| AC5 | 5 | `plugin/tests/test_record_cost.py::test_a_second_run_replaces_the_keys_and_keeps_every_other_byte` | |
| AC6 | 5 | `plugin/tests/test_record_cost.py::test_an_unknown_model_skips_its_stage_and_is_named`, `::test_a_stage_without_transcripts_warns`, `::test_no_transcripts_leaves_the_file_unchanged` | |
| AC7 | 5 | `plugin/tests/test_record_cost.py::test_stdout_shows_tokens_by_type_model_and_cost` | |
| AC8 | 3 | `plugin/tests/test_record_cost.py::test_the_rate_table_is_dated_and_frozen` | |
| AC9 | 1 | `plugin/tests/test_workflow_metrics.py::test_new_counters_are_known_and_never_required` | `uv run pytest -q plugin/tests/test_workflow_metrics.py -k new_counters` → `assert 'converge_gaps' in ['plan_steps', 'plan_review_blockers', …] = workflow_metrics.COUNTERS` |
| AC10 | 1 | `plugin/tests/test_workflow_metrics.py::test_either_deviations_form_satisfies_the_check`, `::test_neither_deviations_form_names_both`; regression guard, green before by design and not the red record: `tests/test_spec_metrics.py::test_every_repository_spec_passes_the_check` (AC10: "still pass `--check`") | `uv run pytest -q plugin/tests/test_workflow_metrics.py -k either_deviations` → `AssertionError: assert ['014-e2e: status `implemented` requires metric keys that are missing: deviations', …] == []` |
| AC11 | 8 | `plugin/tests/test_stage_skills.py::test_implement_records_the_split_metrics`, `plugin/tests/test_stage_contract.py::test_the_implementer_metrics_line` | |
| AC12 | 2 | `plugin/tests/test_workflow_metrics.py::test_report_shows_cost_per_finding_and_per_step`, `::test_cost_lines_are_hidden_without_data`, `::test_report_has_columns_for_the_new_keys` | |
| AC13 | 7 | `plugin/tests/test_ship_cost_and_models.py::test_closing_records_cost_between_apply_and_notification`, `::test_the_guardrail_names_the_cost_exception` | |
| AC14 | 6 | `plugin/tests/test_workflow_config.py::test_models_accepts_every_stage_and_alias`, `::test_a_bad_models_entry_warns_and_only_that_stage_inherits`, `::test_models_errors_are_readable` | |
| AC15 | 7 | `plugin/tests/test_ship_cost_and_models.py::test_ship_passes_the_model_only_when_not_inherit` | |
| AC16 | 6 | `plugin/tests/test_init_skill.py::test_init_writes_the_implement_model_guess`, `plugin/tests/test_readme.py::test_the_models_row_marks_the_guess_and_effort` | |
| AC17 | 7 | `plugin/tests/test_plugin_structure.py::test_no_agent_sets_effort_yet` | n/a — kept behaviour: "the agents … do not get `effort` in this release" |
| AC18 | 9 | `plugin/tests/test_targeted_reading.py::test_the_reading_section_is_identical_in_four_skills`, `::test_the_reading_section_names_full_and_searched_documents` | |
| AC19 | 9 | `plugin/tests/test_targeted_reading.py::test_idea_states_how_each_document_was_read`, `::test_plan_lists_what_it_read_in_the_approach`, `::test_plan_review_checks_decisions_by_its_own_search` | |
| AC20 | 10 | `plugin/tests/test_readme.py::test_changelog_starts_at_the_manifest_version`, `::test_the_changelog_names_the_consumer_impact`, `plugin/tests/test_release_0_8_0.py::test_the_manifest_is_0_8_0`, `bash scripts/check.sh` | |

## Steps

- [x] 1. Metric keys and the `deviations` rule in `--check` (AC9, AC10). Files:
      `plugin/bin/workflow_metrics.py`, `plugin/tests/test_workflow_metrics.py`,
      `tests/test_spec_metrics.py` (new), and the `plugin/README.md` metrics section.
      - Tests first. Add `test_new_counters_are_known_and_never_required`: every new key
        is in `COUNTERS`, in no `REQUIRED` list, accepted by `--check` at every status,
        and a non-integer value is refused. Add
        `test_either_deviations_form_satisfies_the_check`, parametrised over `implemented`
        and `done` with `deviations` alone and with both split keys. Add
        `test_neither_deviations_form_names_both`: with neither form, or only one split
        key, there is one problem naming `deviations`, `deviations_minor` and
        `deviations_major`.
      - Change the existing tests as the SPEC requires. In
        `test_the_required_table_is_exactly_ac9`, `implemented` drops `deviations`, and
        `done` becomes `["started_at", "finished_at", *REQUIRED_DONE_COUNTERS]`, the old
        thirteen counters without `deviations`. `test_keys_due_per_status` drops
        `deviations` from the `implemented` row. `test_every_missing_key_is_named`
        iterates the counters `done` requires, not all of `COUNTERS`.
      - Write `tests/test_spec_metrics.py`. It runs `plugin/bin/workflow_metrics.py
        --check` over every `specs/*/` and expects exit 0.
      - Then the code: `COUNTERS` extended, `REQUIRED` rebuilt, and the either-or rule
        applied in `check()`.
      - In the README: the YAML block gets every new key with its writer, and the
        keys-due table gets the either-or text for `implemented` and `done`.
        `test_metrics_block_lists_every_counter` goes red when `COUNTERS` grows and green
        with the README change.
      Automatic verification: `uv run pytest -q plugin/tests/test_workflow_metrics.py plugin/tests/test_readme.py tests/test_spec_metrics.py`
- [ ] 2. The report's cost lines (AC12). Files: `plugin/bin/workflow_metrics.py`
      (`render`), `plugin/tests/test_workflow_metrics.py`, and one README sentence on the
      three lines.
      - Tests first, over two or three specs built with `spec_dir()`.
        `test_report_shows_cost_per_finding_and_per_step`: one spec without cost keys
        must not enter the numerator or the denominator. Expected values are computed by
        hand in a comment.
      - `test_cost_lines_are_hidden_without_data`: no spec has the key, or the findings
        sum to 0, and the line is absent.
      - `test_report_has_columns_for_the_new_keys`: the header has every new key, and a
        missing value shows `-`.
      Automatic verification: `uv run pytest -q plugin/tests/test_workflow_metrics.py plugin/tests/test_readme.py`
- [ ] 3. The rate table and the stage price (AC8, AC1 arithmetic). Files:
      `plugin/bin/workflow_metrics.py`, `plugin/tests/test_record_cost.py` (new).
      - Add `RATES_DATE = "2026-09-24"`, with a comment above `RATES` saying that existing
        rates are never changed and a new model is only added at its launch rates.
      - Add `RATES: dict[str, tuple[int, int, int, int, int]]` (the Approach table) and
        `TOKEN_TYPES = ("input", "cache_write_5m", "cache_write_1h", "cache_read",
        "output")`.
      - Add `usage_tokens(usage: dict) -> tuple[int, ...]`, `rate_for(model: str) ->
        tuple[int, ...] | None` (strips `-\d{8}$`), and `stage_cents(tokens_by_model:
        dict[str, list[int]]) -> int | None` (None when a model has no rate).
      - Tests first. `test_the_rate_table_is_dated_and_frozen` pins the five rows
        literally, `RATES_DATE`, and the "never changed" comment in the source.
        `test_stage_cost_is_tokens_times_rates_rounded_once` uses two messages of 0.4 cent
        each, which make 1 cent and not 0, and one mixed-type case computed by hand in a
        comment. `test_a_dated_model_id_finds_its_rate` checks
        `claude-haiku-4-5-20251001`. `test_usage_without_the_ttl_split_counts_as_5m`
        covers the older usage shape.
      - Stub the functions first (returning `None`), so that the tests fail on their
        assertions.
      Automatic verification: `uv run pytest -q plugin/tests/test_record_cost.py`
- [ ] 4. Finding the spec's stage transcripts (AC2, AC3, AC4 discovery). Files:
      `plugin/bin/workflow_metrics.py` and `plugin/tests/test_record_cost.py`.
      - Add `stage_usage(spec_dir: Path, source: Path) -> dict[str, dict[str,
        list[int]]]` (stage → model → token totals), plus the helpers `repository_roots`,
        `stage_of`, the prompt match and the descendant resolution described in the
        Approach.
      - Tests first. A fixture builder `write_agent(source, slug, session, agent_id,
        agent_type, prompt, cwd, messages, parent=None)` writes the meta file and the
        jsonl (a user line with `cwd`, then assistant lines with `message.id`, `model` and
        `usage`). The spec's repository is a `git init` in `tmp_path` with
        `.claude/workflow.json` setting `worktree.dir` to `../wt`.
      - `test_perspectives_and_both_reviewer_runs_count_toward_the_final_review`: two
        reviewer agents (report, apply) and three `general-purpose` children of the first.
      - `test_a_rerun_after_an_escalation_counts_toward_its_stage`: two planners, summed.
      - `test_other_specs_and_other_repositories_are_not_counted`: a planner of
        `012-other` in the same repository, and a planner whose prompt names the same
        spec directory with `cwd` in another `git init` directory. Assert the result
        with and without them is equal.
      - `test_repeated_lines_and_archive_copies_count_once`: one message id on three
        lines with growing `output_tokens`, and the same session copied under a second
        dated directory.
      - `test_synthetic_lines_are_skipped`.
      - `test_worktree_lane_cwd_is_accepted`: `cwd` under `tmp_path/wt/011-x`.
      Automatic verification: `uv run pytest -q plugin/tests/test_record_cost.py`
- [ ] 5. The `--record-cost` command (AC1 end to end, AC4 CLI, AC5, AC6, AC7). Files:
      `plugin/bin/workflow_metrics.py` (`record_cost`, `write_costs`, argparse
      `--record-cost` and `--transcripts`, the header usage comment),
      `plugin/tests/test_record_cost.py`, and a new README subsection
      ``### Recording cost (`--record-cost`)`` after ``### Checking metrics (`--check`)``,
      in the same heading style, and added to `HEADINGS` in `plugin/tests/test_readme.py`
      so `test_the_readme_keeps_its_sections` pins its place.
      - README subsection: what is counted, the source and the option, the frozen unit
        and the rate date, the warnings, and "local transcripts only".
      - Tests first, run as subprocesses on `sys.executable`.
        `test_record_cost_writes_the_four_keys` checks the hand-computed integers.
        `test_transcripts_option_reads_that_directory`.
        `test_default_source_finds_worktree_lanes`: the subprocess gets `HOME` set to a
        temp directory and `CLAUDE_CONFIG_DIR` removed. The transcripts sit under two
        project slugs, the main checkout and the worktree. A second case sets
        `CLAUDE_CONFIG_DIR`.
      - `test_a_second_run_replaces_the_keys_and_keeps_every_other_byte`: run twice with
        changed usage. The file equals the original with only the four lines changed or
        appended, stage history and body included, and no key appears twice.
      - `test_an_unknown_model_skips_its_stage_and_is_named`: stderr names the model, the
        other keys are written, and the exit is 0.
      - `test_a_stage_without_transcripts_warns`: no key and a warning naming the stage.
      - `test_no_transcripts_leaves_the_file_unchanged`: an empty and a missing source,
        exit 0, a warning, and the bytes unchanged.
      - `test_stdout_shows_tokens_by_type_model_and_cost`: a markdown table with the
        columns `stage | models | input | cache_write_5m | cache_write_1h | cache_read |
        output | cents`, one row per stage found, and `-` for a cost that could not be
        priced.
      - `test_record_cost_output_passes_the_check`: `--check` stays green after writing.
      Automatic verification: `uv run pytest -q plugin/tests/test_record_cost.py plugin/tests/test_workflow_metrics.py plugin/tests/test_readme.py`
- [ ] 6. `models` in the configuration, the template, `init` and the README (AC14, AC16).
      Files: `plugin/bin/workflow_config.py`, `plugin/tests/test_workflow_config.py`,
      `plugin/templates/workflow.example.json` (adds `"models": {"implement":
      "sonnet"}`), `plugin/skills/init/SKILL.md` step 4, `plugin/tests/test_init_skill.py`,
      `plugin/README.md` and `plugin/tests/test_readme.py`.
      - The README gets one `models` row in the configuration table. It is absent by
        default, and it says: the four stage keys, the five values, `inherit` = the
        session model, and that the value `/pipeline:init` writes is a guess not yet
        measured (Stage 7 comparison). A short subsection `### Models and effort` states
        that the `Agent` tool takes a model alias but no effort level (Claude Code
        2.1.281), that a consumer cannot override a plugin agent's frontmatter, and that
        effort therefore stays a plugin default.
      - `init` step 4 says the `models` section is written as `{"implement": "sonnet"}`
        and nothing else.
      - Tests first. `test_models_accepts_every_stage_and_alias` is parametrised.
        `test_a_bad_models_entry_warns_and_only_that_stage_inherits` uses
        `load_sections`: `{"implement": "gpt", "plan": "opus"}` gives one problem naming
        `models.implement`, `stage_model(config, "implement") == "inherit"` and
        `stage_model(config, "plan") == "opus"`, and an unknown stage key is dropped with
        its own warning.
      - `test_models_errors_are_readable`: `--check` exits 1 with the message.
        `test_stage_model_defaults_to_inherit` covers a missing section.
      - `test_init_writes_the_implement_model_guess` checks that step 4 names `models`,
        `implement` and `sonnet`.
      - `test_the_models_row_marks_the_guess_and_effort` checks the README row and the
        subsection for "guess", "effort" and `Agent`.
      - `test_workflow_example_covers_every_key_and_validates` and
        `test_every_schema_key_reaches_the_table` turn green again once the example and
        the README row are in place.
      Automatic verification: `uv run pytest -q plugin/tests/test_workflow_config.py plugin/tests/test_init_templates.py plugin/tests/test_init_skill.py plugin/tests/test_readme.py plugin/tests/test_guard.py`
- [ ] 7. `ship`: the model per stage and the cost in Closing, and the agents without
      `effort` (AC13, AC15, AC17). Files: `plugin/skills/ship/SKILL.md`,
      `plugin/tests/test_ship_cost_and_models.py` (new),
      `plugin/tests/test_plugin_structure.py`.
      - "Starting a stage agent" gains a paragraph with the stage key per agent. When
        `models.<stage>` in `.claude/workflow.json` is `sonnet`, `opus`, `haiku` or
        `fable`, pass it as `model` to `Agent`. When it is `inherit`, missing, or any
        other value, pass no `model`: the agent then runs on the session model, and a bad
        value has already been warned about by the guard. The rule holds for a stage run
        again under the Result protocol too. The same section says the prompt names the
        spec directory as `<docs.specsDir>/NNN-<slug>/SPEC.md`, because `--record-cost`
        attributes a stage agent to its spec by that name.
      - Closing gets a new step after step 1 (the apply RESULT) and before
        `PushNotification`. Run `workflow_metrics.py --record-cost
        <docs.specsDir>/NNN-<slug>` by name. When `git status --porcelain` shows SPEC.md
        changed: `git add` that file, commit `chore: record stage cost for NNN`,
        `git push`, then `gh pr checks <nr> --watch`, because the notification promises
        green CI on the PR's last commit. A red after this metrics-only commit is
        re-run like the reviewer's status commit (`gh run rerun <id> --failed`). A
        non-zero exit or a warning is reported in the summary and does not stop Closing.
      - Closing step 3's "You do not edit spec files or documents yourself" names the
        exception: the cost keys, which the script writes.
      - Tests first, whitespace-collapsed like `test_converge.py`.
        `test_closing_records_cost_between_apply_and_notification` checks the order of
        the `--record-cost` step against the apply result and `PushNotification`, the
        commit message, the push, and that the call is by name, not through
        `${CLAUDE_PLUGIN_ROOT}` and not with `python3`.
        `test_the_guardrail_names_the_cost_exception`.
      - `test_ship_passes_the_model_only_when_not_inherit` checks that the section names
        `models`, the four stage keys, the four aliases, `inherit` and the phrase that no
        `model` is passed. `test_the_stage_prompt_names_the_spec_directory` checks that
        the section names `<docs.specsDir>/NNN-<slug>/SPEC.md` and `--record-cost`.
      - `test_no_agent_sets_effort_yet`: no `effort` key in any `plugin/agents/*.md`
        frontmatter. A comment says it is removed when the measured defaults land.
      Automatic verification: `uv run pytest -q plugin/tests/test_ship_cost_and_models.py plugin/tests/test_plugin_structure.py plugin/tests/test_stage_skills.py plugin/tests/test_language_contract.py plugin/tests/test_prompt_style.py plugin/tests/test_stage_contract.py`
- [ ] 8. `implement` writes `converge_gaps` and the split deviations (AC11). Files:
      `plugin/skills/implement/SKILL.md` (Finish metrics bullet, Converge pass, Procedure
      step 3), `plugin/agents/implementer.md` (the METRICS line),
      `plugin/tests/test_stage_skills.py` and `plugin/tests/test_stage_contract.py`.
      - The Finish bullet lists `implement_steps`, `implement_iterations`, `converge_gaps`
        (the real gaps kept after your verdicts, summed over the passes; `0` when a pass
        found none), `deviations_minor` and `deviations_major`.
      - Step 3 on deviations defines major as an entry that changes the scope, the
        architecture or the data schema (the one that escalates) and minor as every other
        entry in `## Deviations`. `deviations` is no longer named as a key to write.
      - Tests first. `test_implement_records_the_split_metrics`: the closing step names
        the three new keys and no bare `deviations` key (a word-boundary regex that does
        not match `deviations_`). `CLOSING_STEPS["implement"]` is updated accordingly.
        `test_the_implementer_metrics_line` checks the agent's METRICS line.
      - A test for the major/minor definition checks the Procedure step 3 text for
        "scope", "architecture", "data schema" and both key names.
      Automatic verification: `uv run pytest -q plugin/tests/test_stage_skills.py plugin/tests/test_stage_contract.py plugin/tests/test_converge.py plugin/tests/test_prompt_style.py plugin/tests/test_language_contract.py`
- [ ] 9. Targeted reading (AC18, AC19). Files: `plugin/skills/plan/SKILL.md`,
      `plugin/skills/plan-review/SKILL.md`, `plugin/skills/implement/SKILL.md` and
      `plugin/skills/final-review/SKILL.md` (a Reading section after Project
      configuration, identical in all four), `plugin/skills/idea/SKILL.md` (step 1 and the
      Read context guardrail), and `plugin/tests/test_targeted_reading.py` (new).
      - `plan` step 3 points at the Reading section and says the list of what was read,
        in full or searched with the terms, goes into `## Approach`.
      - `plan-review`'s compliance point checks against the decisions found by its own
        search for the feature's topic.
      - `implement` step 1 and `final-review`'s perspective brief follow the section.
      - Tests first. `test_the_reading_section_is_identical_in_four_skills`.
        `test_the_reading_section_names_full_and_searched_documents`: SPEC, PLAN,
        `<docs.conventions>`, "in full", `<docs.decisions>`, `<docs.roadmap>`, "domain",
        "search", the names of the files it changes, and "whole only when".
        `test_idea_states_how_each_document_was_read`: step 1 and the guardrail name "in
        full" and "searched" with the terms. `test_plan_lists_what_it_read_in_the_approach`.
        `test_plan_review_checks_decisions_by_its_own_search`.
      Automatic verification: `uv run pytest -q plugin/tests/test_targeted_reading.py plugin/tests/test_stage_skills.py plugin/tests/test_language_contract.py plugin/tests/test_prompt_style.py plugin/tests/test_english_only.py`
- [ ] 10. Release 0.8.0 and project documents (AC20). Files:
      `plugin/.claude-plugin/plugin.json` (`0.8.0`), `plugin/CHANGELOG.md` (`## 0.8.0`),
      `plugin/tests/test_release_0_8_0.py` (new, `test_the_manifest_is_0_8_0`),
      `docs/ROADMAP.md` (tick the four 0.8.0 items of this spec), `docs/DECISIONS.md` and
      `docs/CONVENTIONS.md` (the metrics paragraph names `--record-cost`).
      - The CHANGELOG entry gets `**consumer impact:**`: the new keys are optional, `models`
        is optional and without it every stage inherits as before, `/pipeline:init` writes
        `implement: sonnet` for new projects only, and cost needs local transcripts.
      - The DECISIONS row covers targeted reading with the Reading section and the lists
        in `idea` and `plan`, the `deviations` split with the old key still passing, the
        new keys staying optional, and descendants counting toward their stage.
      - Test first: `test_the_manifest_is_0_8_0` is red on 0.7.0.
      Automatic verification: `uv run pytest -q plugin/tests/test_release_0_8_0.py plugin/tests/test_readme.py tests/test_documents.py && bash scripts/check.sh`

## Risks and traps

- **The transcript format is not a contract.** Only the fields listed in the Approach are
  used. A line that is not JSON, or lacks a field, is skipped rather than failing: the cost
  is a measurement and must never stop Closing (AC6).
- **Double counting** comes from the per-block repeats and the archive snapshots. Keying by
  `message.id` across all files handles both, and a fixture pins each (step 4).
- **Under-counting** comes from a stage prompt that does not name the spec directory, for
  example a hand-started agent. The stdout table and the missing-stage warning make it
  visible. Matching by number alone was rejected: a consumer repository reuses the
  numbers.
- **Git in tests.** Step 4 and step 5 need `git init` in `tmp_path`. `git` is present in
  CI (the pre-push tests use it). When `git rev-parse` fails, the fallback is
  `workflow_config.project_root`.
- **Scan cost.** A recursive scan of `~/.claude/projects` opens only the meta files, plus
  the jsonl of stage agents and their descendants. On this machine that is a few hundred
  meta files.
- **Existing tests change.** Step 1 changes three tests of `test_workflow_metrics.py`,
  because the SPEC changes `REQUIRED`. Step 8 changes `CLOSING_STEPS`. Nothing else
  existing is weakened.
- **The eval scaffolds** (`final-review-*`) write `deviations: 0`. That still passes
  (AC10), so they stay untouched.
- **The skill-text rules.** No capitals for emphasis (`test_prompt_style.py`), and no
  backticked heading-like span outside the section map (`test_language_contract.py`).
  Every text step runs both.
- **`ship` pushes after the reviewer's green CI.** The extra commit reruns CI, so `ship`
  waits for it before notifying, because the notification says "ready to merge".
- **A late `apply` run is not costed.** Closing step 3 can start `reviewer` (`apply`)
  again for a flaky test after the cost is recorded, as AC13 places the recording before
  `PushNotification`. That run is left out of `cost_final_review_cents`. It is rare, and
  a later manual `--record-cost` picks it up.

## End-to-end verification

### Automatic (performed by /pipeline:implement)

1. Run `bash scripts/check.sh`. Expected: `ALL GREEN`.
2. Cost a closed spec from both sources, then discard the edit:
   ```bash
   python3 plugin/bin/workflow_metrics.py --record-cost specs/010-test-first-and-converge
   python3 plugin/bin/workflow_metrics.py --check specs/010-test-first-and-converge
   python3 plugin/bin/workflow_metrics.py --record-cost specs/010-test-first-and-converge \
     --transcripts ~/claude-transcripts-archive
   git diff --stat specs/010-test-first-and-converge/SPEC.md
   git checkout -- specs/010-test-first-and-converge/SPEC.md
   ```
   Expected:
   - the stdout table has the four stages, each on a priced model, with non-zero
     tokens in the input, cache and output columns;
   - `--check` exits 0;
   - the archive run gives the same four values as the default run, because the copies
     are deduplicated. A difference is acceptable only when the stdout tables show a
     session one source lacks (the archive is a dated snapshot); record which one;
   - the diff touches only four `cost_*` lines.

   The working-tree script is called by path here on purpose: the session's `PATH`
   carries the installed 0.7.0 plugin, which has no `--record-cost`. Record the table in
   PLAN.md. The checkout leaves a closed spec as it was: costing the
   baseline belongs to the Stage 7 comparison, not to this PR.
3. Run `python3 plugin/bin/workflow_metrics.py specs`. Expected: the table has the new
   columns, with `-` for specs without them, and no cost line, because no committed spec
   has cost keys.
4. Run `python3 plugin/bin/workflow_config.py --check` in a temp repository with
   `{"models": {"implement": "sonnet"}}` (exit 0) and with `{"models": {"implement":
   "gpt"}}` (exit 1 and the readable message).

### Manual (performed by the owner)

1. The 0.8.0 canary (`docs/CONVENTIONS.md`, Releases) in a consumer whose
   `.claude/workflow.json` has `"models": {"implement": "sonnet"}`, run on one stage.
   Afterwards, `workflow_metrics.py --record-cost <spec-dir>` shows the model per stage:
   `claude-sonnet-5` for `implement` once an implementer has run under `ship`. `ship`
   passing `model` needs a real orchestrated run, which no test can start.

## Definition of Done

- [ ] all steps ticked
- [ ] `bash scripts/check.sh` fully green
- [ ] end-to-end verification (automatic) performed, result recorded here
- [ ] `docs/ROADMAP.md` updated; `docs/DECISIONS.md` row added; `docs/CONVENTIONS.md`
      metrics paragraph updated
- [ ] spec status: `implemented`

## Owner decisions

_(appended by /pipeline:ship or a stage on escalation: date, stage, question, decision)_

## Review log

**2026-09-24, /pipeline:plan-review.** The SPEC was read in full first, before the plan. My
own approach agreed with the plan on the main points: the mode lives in
`workflow_metrics.py`; attribution goes by `agentType`, the spec directory in the prompt and
`cwd`; descendants count through `parentAgentId`; the frontmatter is edited line by line.
The differences I followed up: the spec name in `ship`'s prompt (F4), the timing of a late
`apply` run (F5), and whether the new AC10 and AC17 tests are red before the change (F1).

Findings (counted before the fixes):

| id | severity | finding | change |
|---|---|---|---|
| F1 | `major` | AC17's only proving test (`test_no_agent_sets_effort_yet`) is green before the change by design, but the `n/a — kept behaviour` mark was in the third column and the fourth was empty. `/pipeline:implement` would then escalate a proving test that is green before its change. AC10's repository-specs guard had the same misplaced note. | AC17: `n/a — kept behaviour` with the AC's words in the fourth column. AC10: the note now says the guard is not the red record. The either-form tests are red today, so that row's fourth column stays empty. |
| F2 | `minor` | Step 5 named the README heading `### Recording cost (--record-cost)` without backticks, unlike ``### Checking metrics (`--check`)``, and did not pin where it goes. | The heading now uses backticks and is added to `HEADINGS` in `test_readme.py`. |
| F3 | `minor` | End-to-end check 2 expected the archive run and the default run to match exactly. The archive is a dated snapshot, so a session missing from one source would make the check fail even though the code is correct. | A difference is accepted only when the stdout tables show the missing session, and it is recorded. |
| F4 | `minor` | Attribution relies on the stage prompt naming the spec directory, but `ship` only said "the spec number and path", and nothing pinned it. | Step 7: "Starting a stage agent" names `<docs.specsDir>/NNN-<slug>/SPEC.md` and why. New pin `test_the_stage_prompt_names_the_spec_directory`. |
| F5 | `minor` | Closing step 3 can start `apply` again after the cost is recorded (AC13 puts the recording before `PushNotification`), so that run is not costed. | Added to Risks and traps as an accepted gap. It is rare, and a manual re-run covers it. |

Checked and found sound, so later stages need not check these again:

- **Coverage:** AC1–AC20 each have steps and a proving test. The matrix's step numbers
  match the steps.
- **Rates:** checked against the `/claude-api` model table (cached 2026-06-24). Opus 5.5 costs
  $4 / $20 with cache reads at $0.20, Fable 5.1 $10 / $50 with cache reads at $0.25,
  Opus 5 $5 / $25, Sonnet 5 $2 / $10 and Haiku 4.5 $1 / $5. Cache writes are 1.25× input
  for 5 minutes and 2× input for one hour. Every row of the Approach table matches. Adding
  `claude-opus-5` for the baseline is right.
- **Transcript facts:** checked on this machine against this session's own subagents.
  `meta.json` holds `agentType`, and `parentAgentId` on nested agents. The first jsonl
  line is `type: user` and carries `cwd`, `gitBranch` and the prompt, which names
  `specs/011-cost-metrics-and-stage-models/SPEC.md`.
- **Compliance:** `docs/DECISIONS.md` was searched for `PATH`, cost, `converge_gaps`,
  required keys and prompt style. The plan keeps the 2026-09-21 rule (`ship` calls the
  script by name). The end-to-end check calls it by path, with a stated reason. The plan
  keeps the new keys optional, as SPEC 010 requires, and it adds `converge_gaps`, which
  SPEC 010 rejected but the 2026-09-24 audit row and SPEC 011 now ask for.
  `CLAUDE_CONFIG_DIR` as a fallback source does not contradict AC4, because without it
  the default is `~/.claude/projects`.
- **Existing tests:** `REQUIRED["done"]` spreads `COUNTERS`, so without
  `REQUIRED_DONE_COUNTERS` the new keys would become required. The plan handles this.
  `test_every_missing_key_is_named` and `test_keys_due_per_status` are adjusted as the
  SPEC requires. The "requires either" wording keeps the single "missing" line.
  `CLOSING_STEPS` prefixes are unaffected by the new Reading section. `pyproject.toml`
  collects `tests/`, so `tests/test_spec_metrics.py` runs in `check.sh`.
- **Configuration:** the `models` row stays out of `defaults()`, like `protectedBranches`.
  `test_every_config_key_is_documented_with_its_default` still holds, and the example
  template covers the new SCHEMA key.
- **Feasibility:** no step depends on a later one. There is no migration and no new
  dependency. The owner summary's flags are correct.
- **Language:** the plan is in English, as `language` requires.

The plan is ready. It has no blocker, adds no dependency and no migration, and every
finding above was fixed in the plan itself.

## Deviations

_(filled in by /pipeline:implement — every deviation from the plan with its rationale)_

## Final review

_(filled in by /pipeline:final-review)_
