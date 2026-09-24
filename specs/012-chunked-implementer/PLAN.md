# PLAN 012 — The chunked implementer

## Owner summary

- **Approach:** PLAN templates and the section map gain a group heading inside `## Steps`
  (`### Group N — ` / `### Grupa N — `) and a `## Chunk notes` section. `plan` always
  divides the steps into groups (a small plan is one group), and `plan-review` checks and
  fixes the grouping. `workflow_config.py` accepts `"implement": {"chunked": true|false}`,
  off when missing, a bad value warns and counts as off. With chunking on and more than one
  group, `implement` carries out only the group that holds the first unticked step, leaves
  a chunk note, commits, pushes and ends at `plan-approved`. The chunk with the last group
  runs the converge pass and the Definition of Done as today, and writes the metrics
  (`implement_iterations` as a running total, and the new optional `implement_chunks`).
  `ship` treats `DONE` + `STATUS: plan-approved` from the implementer as "a chunk ended",
  starts the next one, and uses a `CHUNK: <group>/<groups>` line to spot a chunk that made
  no progress. One eval case, README, CHANGELOG 0.8.0, roadmap and decisions complete it.
- **Main risks:** many existing tests pin the templates, the section map, the shared
  skill blocks and the README verbatim. Each change has to update its pinning test on
  purpose and keep the shared blocks identical. `validate()` in `workflow_config.py`
  rejects every bool today, so a boolean key needs a small fix there. The eval case needs a
  paid 5-run measurement, which is left to the owner.
- **New dependency:** no.
- **Data migration:** no. Existing PLAN.md files without groups run in one context, as
  today.
- **Manual scenarios for the owner:** 2. The 5-run eval measurement of
  `implement-stops-at-group-boundary` (paid, AC11), and a real `/pipeline:ship` run with
  chunking on and a plan of several groups. The second one fits the Stage 7 comparison.

## Approach

**Read context.** SPEC 012 and `docs/CONVENTIONS.md` were read in full. Every file the
plan changes was read in full: the skills `plan`, `plan-review`, `implement`, `ship` and
`init` (step 4), the agent `implementer`, `plugin/bin/workflow_config.py`,
`plugin/bin/workflow_metrics.py`, `plugin/templates/{sections.md,PLAN.en.md,PLAN.pl.md,workflow.example.json}`,
the README sections this spec changes (configuration table, spec statuses, the `RESULT`
contract, "Implementation and review", workflow metrics), the head of `plugin/CHANGELOG.md`,
and the eval case `implement-converge-finds-missing-ac` with its scaffold (the model for the
new case). The following tests were read, because they pin what changes:
`test_templates_language.py`, `test_eval_cases.py` (the Polish mirror heading check
included), `test_workflow_config.py`, `test_workflow_metrics.py` (`NEW_KEYS`),
`test_record_cost.py` (`write_agent`), `test_readme.py`, `test_stage_contract.py`,
`test_ship_cost_and_models.py`, `test_converge.py`, `test_init_skill.py`,
`test_release_0_8_0.py` and `tests/test_documents.py`. The other documents were searched,
not read whole:

- `docs/DECISIONS.md`: searched for 2026-09-2[34], cost audit, threshold, size, tier, eval,
  `models` and "never blocks". Binding here: the 2026-09-24 cost audit (a chunked
  implementer is one of the ways Stage 7 saves), SPEC 010 (no size tiers or thresholds; a
  new required metric key turns specs in progress red), SPEC 011 (cost counts every stage
  agent of the spec toward its stage; the shared Reading section), 2026-09-23 (the guard
  never blocks on configuration; prompt style without capitals; `sections.md` is the one
  Polish ↔ English bridge) and 2026-09-22 (the eval cost policy: 5 runs for a new case).
- `docs/ROADMAP.md`: searched for "Stage 7", "0.8.0" and "chunk". It gives the one 0.8.0
  item this spec ticks, whose wording ("by a step count or by step groups", "a size
  threshold") has to follow the owner's decisions when it is ticked.
- `docs/BACKLOG.md`: searched for "eval", "judge" and "final message". The P2 item on
  `implement-converge-finds-missing-ac` applies: the new grader asks only for what the
  final message and the PLAN it summarises show.
- `docs/PROJECT.md`: not changed. The requirement "every stage resumes" already covers a
  planned resumption.

**Groups in the PLAN.** The section map gets two rows: `step-group` (`### Grupa N — ` /
`### Group N — `) after `steps`, and `chunk-notes` (`## Notatki chunków` / `## Chunk notes`)
after `review-log`. Both templates carry the literals exactly, with `N` as the placeholder:
`### Group N — <name>` (Polish `### Grupa N — <nazwa>`) directly under `## Steps`, and
`## Chunk notes` between `## Review log` and `## Deviations`, which is the order the stages
write them in. The template shows one group, so it does not suggest splitting a small plan.
The skill says that later groups continue the step numbering. The parity test
`check_structure` matches headings to map literals exactly. It gains one rule: a map
literal that ends in `— ` matches a heading that starts with it, the way the H1 lines are
treated already. The Polish mirror eval fixture copies the template's headings, so it gets
the group heading and the new section, and its heading check normalises group headings the
same way.

**The switch.** `SCHEMA["implement"] = {"chunked": bool}` and
`defaults()["implement"] = {"chunked": False}`. `validate()` rejects `True`/`False` for every
type today (`not isinstance(value, expected) or isinstance(value, bool)`), because bool is a
subclass of int. The fix keeps that guard for the non-bool types only:
`or (expected is not bool and isinstance(value, bool))`. An unknown key or a non-boolean
value fails validation for the `implement` section. `load_sections` then drops the whole
section with a problem, and the default `false` applies. The guard, the report and
`--format-for` already load section by section, so nothing blocks. Entry-wise handling like
`models` is not needed, because the section has one key. The implementer reads
`.claude/workflow.json` itself, as every stage does, and treats only a literal `true` as on.
It calls no helper. A `--get` mode for the script was rejected: the skills read the file
directly, and one more CLI mode would need its own allow rule.

**Chunk mode in `implement`.** A new section `## Chunk mode` sits after `## Converge pass`.
Procedure step 1 points to it, and so do step 6 and the Handoff. The rules:

- On: `implement.chunked` is `true` and `## Steps` holds more than one `### Group N — `
  heading (either literal from the map). Off, or one group or none: one context, exactly as
  in 0.7.0, with no `## Chunk notes` entry and no `implement_chunks`.
- On start, a chunk reads `## Chunk notes` in full. It carries out the group that holds the
  first unticked step. The group ends after its last step is green, ticked and committed.
  The chunk then appends one entry to `## Chunk notes`: the group carried out, the
  decisions taken within the plan's latitude, the traps the next group will meet, and the
  running `implement_iterations` total (the previous entry's total plus this chunk's). It
  commits (`docs: add chunk note N for NNN`), pushes and ends with status `plan-approved`.
  A chunk never ends on a red or uncommitted step: it goes on or escalates as today.
- The chunk that holds the last group runs its steps, then the converge pass, the steps the
  pass adds and the Definition of Done, as one context does. The converge-resume rules stay
  as they are. Steps the converge pass adds belong to that chunk and to no group.
- A chunk whose first unticked step lies after the last group (a step a converge pass
  added, under its `### Converge pass N — ` heading), or which finds every step ticked, is
  the final chunk too: it resumes the converge pass or the Definition of Done by the
  converge-resume rules. This is the case after an escalation inside the final chunk.
- The final chunk writes the metrics. `implement_iterations` is the last entry's running
  total plus its own. `implement_chunks` is the number of groups carried out as separate
  chunks: the entries in `## Chunk notes` plus one. The other keys are counted over the
  whole plan, as today.
- Standalone, a chunk that ends at a group boundary hands off with "run
  `/pipeline:implement NNN` again after `/clear`". Under `ship` it ends with the RESULT
  block, where `CHUNK: <group>/<groups>` follows `STATUS`.

The shared blocks stay byte-identical: `## Project configuration` (two bullets,
`test_stage_skills.py`), `## Reading` (`test_targeted_reading.py`) and `## Section map`.
That is why the switch and the chunk-notes read go into `## Chunk mode` and Procedure
step 1, not into those blocks.

**The implementer agent** gets one paragraph in its intro: chunk mode per the skill, and a
`CHUNK: <group>/<groups>` line right after `STATUS` in chunk mode. A chunk that ends at a
group boundary reports `STATUS: plan-approved` and its running `implement_iterations` in
`METRICS`, and writes no metric into SPEC.md. The METRICS line adds `implement_chunks` (chunk
mode only). The shared `## Stage agent contract` block stays identical to `ship`'s, so the
`RESULT` block itself keeps its four fields, and the README's field check stays green.

**`ship`.** The State table row for `plan-approved` says `implemented`, or `plan-approved`
when a chunk ended, in which case the next implementer is started with the same prompt.
The Result protocol gains one bullet. An `implementer` with `DONE` and
`STATUS: plan-approved` means a chunk ended: start the next implementer with the same
prompt and the same `models` entry. For such a result, a `CHUNK:` line that names the same
group as the previous chunk that returned `DONE`, or no `CHUNK:` line, counts as a missing
RESULT: one re-run, then an escalation to the owner that says what the agent returned. An
`ESCALATE` result is not a chunk end: the agent started after the owner's decision
continues the same group, so its `DONE` is compared with the last `DONE` chunk, never with
the escalated one. The final `DONE` with `STATUS: implemented` is not checked for
progress. `STATUS: implemented` means the stage is
done. After an escalation, the new implementer is simply the next chunk. `ship` still reads
only RESULT blocks, and the implementer decides the chunk from the configuration. The
variant where `ship` passes a chunk mode or a step range in the prompt was rejected by the
SPEC.

**Metrics.** `implement_chunks` goes into `COUNTERS` right after `implement_iterations`.
That makes it a known integer counter and a report column (`-` when missing), and keeps it
out of every `REQUIRED` list. `--record-cost` needs no change: every `implementer` whose
prompt names the spec directory already adds up (`stage_usage`). AC15 pins that with a
three-chunk fixture, `n/a — kept behaviour`.

**The eval case** `implement-stops-at-group-boundary` is modelled on
`implement-converge-finds-missing-ac`: the same offline bare remote, the same allow rule
for reading the plugin, and `unittest`. SPEC 001 "Order tags" is at `plan-approved`, and
`workflow.json` has `"implement": {"chunked": true}`. The PLAN has `### Group 1 — Tags`
(step 1: `add_tag` in `shop/tags.py`, which appends a lower-cased tag; step 2: a duplicate
tag is ignored) and `### Group 2 — Label` (step 3: `tags_line` in `shop/labels.py`, which
returns the sorted tags joined by ", "), plus an empty `## Chunk notes`. Each step is small
and green on its own. The correct run ticks and commits steps 1 and 2 only, writes a chunk
note, leaves `status: plan-approved`, and says in its final message that the chunk ended at
the group boundary.

**Rejected variants.** A new `implement` metric for the chunk count in `--check` REQUIRED:
the SPEC keeps it optional, because a required key turns specs in progress red (SPEC 010).
Showing two groups in the templates: that invites a split of every plan, while the SPEC
wants a small plan to be one group.

## AC → steps matrix

| AC | Steps | Proving test | Red before the change |
|----|-------|--------------|-----------------------|
| AC1 | 1 | `plugin/tests/test_templates_language.py::test_the_section_map_matches_the_snapshot`, `::test_english_templates_match_the_snapshot`, `::test_polish_templates_match_the_snapshot` | |
| AC2 | 4 | `plugin/tests/test_chunked_implementer.py::test_plan_*` | |
| AC3 | 4 | `plugin/tests/test_chunked_implementer.py::test_plan_review_*` | |
| AC4 | 2 | `plugin/tests/test_workflow_config.py::test_implement_*` | |
| AC5 | 2 | `plugin/tests/test_readme.py::test_the_implement_row_marks_the_candidate`, `plugin/tests/test_init_skill.py::test_init_does_not_write_the_implement_section`, `plugin/tests/test_init_templates.py::test_the_example_shows_chunking_off` | |
| AC6 | 5 | `plugin/tests/test_chunked_implementer.py::test_implement_chunk_ends_at_the_group_boundary` | |
| AC7 | 5 | `plugin/tests/test_chunked_implementer.py::test_implement_last_chunk_converges_and_finishes` | |
| AC8 | 5 | `plugin/tests/test_chunked_implementer.py::test_implement_off_or_one_group_runs_one_context` | |
| AC9 | 5 | `plugin/tests/test_chunked_implementer.py::test_implement_chunk_note_contents`, `::test_implement_start_reads_the_chunk_notes` | |
| AC10 | 5 | `plugin/tests/test_chunked_implementer.py::test_implement_standalone_handoff_after_clear` | |
| AC11 | 7 | `plugin/tests/test_eval_cases.py` (the `NEW_CASES` parametrisations for `implement-stops-at-group-boundary`, `::test_group_boundary_*`); 5 of 5 runs: manual | |
| AC12 | 6 | `plugin/tests/test_chunked_implementer.py::test_ship_*` | |
| AC13 | 5, 6 | `plugin/tests/test_chunked_implementer.py::test_implementer_agent_reports_the_chunk`, `::test_ship_no_progress_is_a_missing_result`, `::test_readme_documents_the_chunk_line` | |
| AC14 | 3, 5 | `plugin/tests/test_workflow_metrics.py::test_implement_chunks_*`, `plugin/tests/test_chunked_implementer.py::test_implement_final_chunk_writes_the_metrics` | |
| AC15 | 3 | `plugin/tests/test_record_cost.py::test_three_implementer_chunks_add_up` | n/a — kept behaviour ("The test pins what already works") |
| AC16 | 8 | `plugin/tests/test_release_0_8_0.py::test_the_changelog_records_spec_012`, `tests/test_documents.py::test_roadmap_ticks_spec_012`, `::test_decisions_record_spec_012`; `bash scripts/check.sh` | |

## Steps

Text in skills is compared whitespace-collapsed (`" ".join(text.split())`), because the
skills are hard-wrapped. The new text tests live in one new file,
`plugin/tests/test_chunked_implementer.py`, with a `section(path, heading)` helper like the
one in `test_converge.py`. Each step first writes its tests with the tokens given here, runs
them red on an assertion, and then changes the product. The tokens are exact substrings of
the collapsed text. Where a step names a sentence, the wording around the tokens is free.

- [ ] 1. Section map and PLAN templates (AC1) — files:
      `plugin/tests/test_templates_language.py`, `plugin/templates/sections.md`,
      `plugin/templates/PLAN.en.md`, `plugin/templates/PLAN.pl.md`,
      `plugin/tests/test_eval_cases.py`,
      `plugin/evals/plan-review-approves-polish-owner-decision/scaffold.sh`.
      Tests first:
      - `MAP_SNAPSHOT`: add `("step-group", "PLAN", "### Grupa N — ", "### Group N — ")`
        after the `steps` row and `("chunk-notes", "PLAN", "## Notatki chunków", "## Chunk notes")`
        after the `review-log` row.
      - `ENGLISH_HEADINGS["PLAN"]`: `"### Group N — <name>"` after `"## Steps"`, and
        `"## Chunk notes"` after `"## Review log"`. `POLISH_SNAPSHOT["PLAN"]["headings"]`:
        `"### Grupa N — <nazwa>"` after `"## Kroki"`, and `"## Notatki chunków"` after
        `"## Review log"`. Update the comment above `POLISH_SNAPSHOT`: SPEC 012 adds these
        two headings on purpose.
      - `key_of`: a row literal that ends in `"— "` matches a heading that starts with it.
        Every other literal still matches exactly.
      Run red, then add the two map rows (at the same positions as in the snapshot, cells
      in backticks with the trailing space inside) and the template lines:
      `### Group N — <name>` plus a blank line directly under `## Steps`, before the step
      list; `## Chunk notes` with the placeholder
      `_(filled in by /pipeline:implement in chunk mode — one entry per chunk that ends at a group boundary)_`
      between `## Review log` and `## Deviations`. The Polish template gets the same, with
      `### Grupa N — <nazwa>`, `## Notatki chunków` and
      `_(wypełnia /pipeline:implement w trybie chunków — jeden wpis na chunk kończący się na granicy grupy)_`.
      The Polish mirror fixture's PLAN gets `### Grupa 1 — Ustawienia` under `## Kroki` and
      `## Notatki chunków` with the same placeholder. In `test_eval_cases.py`,
      `test_the_mirror_owner_accepted_the_dependency` compares headings after mapping
      every line that starts with `### Grupa ` to `### Grupa N — ` on both sides, through
      a small `normalised(headings)` helper.
      Automatic verification: `uv run pytest plugin/tests/test_templates_language.py plugin/tests/test_eval_cases.py plugin/tests/test_language_contract.py plugin/tests/test_english_only.py -q` → green.

- [ ] 2. The switch and its documentation (AC4, AC5) — files:
      `plugin/tests/test_workflow_config.py`, `plugin/tests/test_readme.py`,
      `plugin/tests/test_init_skill.py`, `plugin/tests/test_init_templates.py`,
      `plugin/bin/workflow_config.py`, `plugin/README.md`,
      `plugin/templates/workflow.example.json`, `plugin/skills/init/SKILL.md`.
      Tests first:
      - `test_workflow_config.py`:
        - `test_implement_chunked_accepts_a_boolean`: parametrised over `True` and
          `False`, `--check` exits 0 and `load(repo).get("implement.chunked") is value`.
        - `test_implement_chunked_is_off_without_the_section`: `load` and
          `load_sections` without the key give `False`, and `defaults()["implement"] == {"chunked": False}`.
        - `test_implement_bad_values_warn_and_count_as_off`: parametrised over
          `{"chunked": "yes"}`, `{"chunked": 1}`, `{"chunked": True, "size": 3}` and
          `"on"`. `load_sections` returns one problem naming `implement` (`has to be bool`,
          `unknown key \`implement.size\``, `\`implement\` has to be an object`), no
          exception, and `get("implement.chunked") is False`. `--check` exits 1 with
          that message.
        - `test_implement_bool_does_not_open_other_keys`: `{"language": True}` and
          `{"verify": {"command": True}}` are still rejected.
      - `test_readme.py::test_the_implement_row_marks_the_candidate`: exactly one row
        starting `` | `implement.chunked` ``, and it contains `` `false` ``, `Stage 7` and
        `not yet measured`.
      - `test_init_skill.py::test_init_does_not_write_the_implement_section`: step 4
        names `` `implement` `` in the sentence that says what init does not write.
      - `test_init_templates.py::test_the_example_shows_chunking_off`:
        `json.loads(workflow.example.json)["implement"] == {"chunked": False}`.
      Run red, then:
      - `SCHEMA` gains `"implement": {"chunked": bool}` after `models`; `defaults()` gains
        `"implement": {"chunked": False}`; `validate()` uses
        `elif not isinstance(value, expected) or (expected is not bool and isinstance(value, bool)):`.
      - README configuration table: a row after `models`:
        `` | `implement.chunked` | `false` | `true` runs the implementer in chunks, one fresh subagent per step group of PLAN.md (see "The chunked implementer" below); any other value warns and counts as off. A Stage 7 candidate, not yet measured: off until the comparison measures it no worse; `/pipeline:init` does not write it | ``.
      - `workflow.example.json`: `"implement": {"chunked": false}` after `models`.
      - `init` step 4, the `.claude/workflow.json` bullet: next to `protectedBranches`,
        "you do not write the `implement` section (chunking stays off until the Stage 7
        comparison measures it)".
      Automatic verification: `uv run pytest plugin/tests/test_workflow_config.py plugin/tests/test_readme.py plugin/tests/test_init_skill.py plugin/tests/test_init_templates.py plugin/tests/test_guard.py -q` → green.

- [ ] 3. `implement_chunks` and the three-chunk cost (AC14 script part, AC15) — files:
      `plugin/tests/test_workflow_metrics.py`, `plugin/tests/test_record_cost.py`,
      `plugin/bin/workflow_metrics.py`, `plugin/README.md`.
      Tests first:
      - `test_workflow_metrics.py`: add `"implement_chunks"` to `NEW_KEYS` (the existing
        `test_new_counters_are_known_and_never_required` then covers "known, integer,
        never required"). Add `test_implement_chunks_is_a_report_column`: a spec with
        `implement_chunks: "3"` and one without it. The rendered header holds
        `implement_chunks`, the first row shows `3`, the second shows `-`.
      - `test_record_cost.py::test_three_implementer_chunks_add_up`: three agents
        `c1`, `c2`, `c3` of type `pipeline:implementer` with `prompt()`, each in its own
        session directory, with different usage (for example output 100, 200 and 300 on
        `OPUS`). `stage_usage` gives
        `{"implement": {OPUS: [0, 0, 0, 0, 600]}}`, and `record_cost` through
        `run_record(..., "--transcripts", ...)` writes
        `cost_implement_cents` equal to `stage_cents` of that sum. This test is green
        before the change by design (`n/a — kept behaviour`). Record that in the matrix
        row, not a red run.
      Run red (the metrics tests), then insert `"implement_chunks"` into `COUNTERS` after
      `"implement_iterations"`. In the README: in the `## Workflow metrics` block, a line
      `implement_chunks: 3                  # groups carried out as separate chunks (chunk mode only)`
      after `implement_iterations`; the sentence on optional keys names `implement_chunks`;
      the `--check` table's `done` row lists `implement_chunks` among the optional ones.
      Automatic verification: `uv run pytest plugin/tests/test_workflow_metrics.py plugin/tests/test_record_cost.py plugin/tests/test_readme.py tests/test_spec_metrics.py -q` → green.

- [ ] 4. Groups in `plan` and `plan-review` (AC2, AC3) — files:
      `plugin/tests/test_chunked_implementer.py` (new), `plugin/skills/plan/SKILL.md`,
      `plugin/skills/plan-review/SKILL.md`.
      Tests first:
      - `test_plan_marks_groups_always`: the new `## Step groups` section of `plan` holds
        `` `### Group N — <name>` ``, `whatever \`implement.chunked\` says`,
        `green, committable state`, `step numbers run through the whole plan` and
        `sections.md`. Step 5 of `## Steps` holds `Step groups`.
      - `test_plan_small_plan_is_one_group`: the section holds `one group`,
        `cache writes` and `rule of thumb`, and holds neither `threshold` nor any digit
        (`re.search(r"\d", section)` is `None`).
      - `test_plan_review_checks_the_groups`: `plan-review` step 3 holds `**groups:**`,
        `exactly one group`, `later group to finish`, `one group`,
        `a plan without groups gets them` and `in place`.
      Run red, then:
      - `plan`: a new section `## Step groups` before `## PLAN.md template`. It says:
        divide `## Steps` into groups under `### Group N — <name>` (the Polish literal from
        the section map), whatever `implement.chunked` says, because a plan can be
        chunked later and plans look the same in both modes. A group is a coherent part of
        the change that ends in a green, committable state: no step leaves work for a later
        group to finish. Step numbers run through the whole plan. A small plan is one
        group, because every chunk pays its cache writes again. The rule of thumb: split
        only where a later part of the change needs other files and context than the
        earlier one, and where the context a chunk would drop (the files, test runs and
        failures of a finished group) outweighs what the next chunk reads again (SPEC,
        PLAN, conventions and its own files). A plan that stays in one area is one group.
        No number is written. Step 5 gets one sentence: "Divide the steps into groups as
        the Step groups section says."
      - `plan-review` step 3 checklist: a bullet after **testability**:
        `**groups:**` every step is in exactly one group; no group boundary leaves work
        for a later group to finish; a small plan is one group. Fix a violation in place;
        a plan without groups gets them. Severity: a boundary that leaves work half done is
        `major`, and missing groups or a small plan split in several are `minor`.
      Automatic verification: `uv run pytest plugin/tests/test_chunked_implementer.py plugin/tests/test_stage_skills.py plugin/tests/test_language_contract.py plugin/tests/test_prompt_style.py plugin/tests/test_targeted_reading.py plugin/tests/test_test_first.py plugin/tests/test_review_depth.py -q` → green.

- [ ] 5. Chunk mode in `implement` and the implementer agent (AC6–AC10, AC13 agent part,
      AC14 writing rule) — files: `plugin/tests/test_chunked_implementer.py`,
      `plugin/tests/test_stage_contract.py`, `plugin/skills/implement/SKILL.md`,
      `plugin/agents/implementer.md`.
      Tests first (`chunk` = the collapsed `## Chunk mode` section of `implement`):
      - `test_implement_chunk_ends_at_the_group_boundary` (AC6): `chunk` holds
        `` `implement.chunked` ``, `more than one group`, `first unticked step`,
        `green, ticked and committed`, `` `## Chunk notes` ``, `push`,
        `` `plan-approved` `` and `never ends on a red or uncommitted step`.
      - `test_implement_last_chunk_converges_and_finishes` (AC7): `chunk` holds
        `last group`, `converge pass`, `the steps it adds`, `Definition of Done`,
        `as one context does`, `converge-resume rules apply unchanged` and
        `after the last group` (the first unticked step lies after the last group, or every
        step is ticked: the chunk is the final one).
      - `test_implement_off_or_one_group_runs_one_context` (AC8): `chunk` holds
        `one group or none`, `one context`, `as in 0.7.0`,
        `` no `## Chunk notes` entry `` and `` no `implement_chunks` ``.
      - `test_implement_chunk_note_contents` (AC9): `chunk` holds `the group`,
        `decisions taken within the plan's latitude`, `traps` and
        `` running `implement_iterations` total ``.
      - `test_implement_start_reads_the_chunk_notes` (AC9): Procedure step 1 holds
        `` `## Chunk notes` `` and `Chunk mode`.
      - `test_implement_standalone_handoff_after_clear` (AC10): the `**Run on its own:**`
        bullet of `## Handoff` holds `group boundary` and
        `` run `/pipeline:implement NNN` again after `/clear` ``.
      - `test_implement_final_chunk_writes_the_metrics` (AC14): Procedure step 6 holds
        `` `implement_chunks` `` and `running total`.
      - `test_implementer_agent_reports_the_chunk` (AC13): the agent's intro (before
        `## Stage agent contract`) holds `` `CHUNK: <group>/<groups>` ``,
        `` `STATUS: plan-approved` `` and `Chunk mode`.
      - `test_stage_contract.py::test_the_implementer_metrics_line`: the pinned sentence
        becomes "METRICS of this stage: `implement_steps`, `implement_iterations`,
        `converge_gaps`, `deviations_minor`, `deviations_major`, and in chunk mode
        `implement_chunks`."
      Run red, then:
      - `implement`: a new section `## Chunk mode` after `## Converge pass`, with the rules
        from the Approach ("Chunk mode in `implement`"). It says why the mode exists (each
        chunk starts from the committed state instead of re-reading one long context) and
        that a group is a `### Group N — ` heading from the section map, while converge
        pass headings are not groups. It adds the rule from the Approach: a first unticked
        step after the last group, or no unticked step at all, makes the chunk the final one.
      - Procedure step 1: after the resume sentence, "With chunking on, read
        `## Chunk notes` and carry out one group, as the Chunk mode section says."
      - Procedure step 6, the metrics bullet: "in chunk mode, `implement_iterations` is the
        running total from the last `## Chunk notes` entry plus your own, and
        `implement_chunks` the entries in `## Chunk notes` plus one; without chunk mode
        `implement_chunks` is not written."
      - Handoff `**Run on its own:**`: add "a chunk that ended at a group boundary
        summarises its group and its chunk note, and tells the owner to run
        `/pipeline:implement NNN` again after `/clear`".
      - `implementer.md` intro: a paragraph on chunk mode per the skill's Chunk mode
        section. A chunk that ends at a group boundary returns `RESULT: DONE`,
        `STATUS: plan-approved`, a line `CHUNK: <group>/<groups>` right after `STATUS`
        (also in the final chunk and in an `ESCALATE` result, with its own group), and in
        METRICS its running
        `implement_iterations`; it writes no metric into SPEC.md. The METRICS sentence as
        in the test. The `## Stage agent contract` block stays unchanged.
      Automatic verification: `uv run pytest plugin/tests/test_chunked_implementer.py plugin/tests/test_stage_contract.py plugin/tests/test_converge.py plugin/tests/test_test_first.py plugin/tests/test_stage_skills.py plugin/tests/test_targeted_reading.py plugin/tests/test_language_contract.py plugin/tests/test_prompt_style.py plugin/tests/test_prompt_audit.py -q` → green.

- [ ] 6. `ship` loops over chunks and the README documents the mode (AC12, AC13) — files:
      `plugin/tests/test_chunked_implementer.py`, `plugin/skills/ship/SKILL.md`,
      `plugin/README.md`.
      Tests first:
      - `test_ship_state_table_names_the_chunk`: the `## State` table row starting
        `` | `plan-approved` `` holds `a chunk ended`, and the Result protocol holds `` `STATUS: plan-approved` ``, `a chunk ended`, `same prompt` and
        `` `STATUS: implemented` ``.
      - `test_ship_no_progress_is_a_missing_result`: the Result protocol holds
        `` `CHUNK: <group>/<groups>` ``, `same group as the previous chunk that returned`,
        `missing RESULT`, `escalat` and `never with the escalated one`.
      - `test_readme_documents_the_chunk_line`: the README section
        ``### The `RESULT` contract`` holds `` `CHUNK: <group>/<groups>` ``; "Implementation
        and review" holds `**The chunked implementer.**`; the spec statuses row for
        `plan-approved` holds `chunk`.
      Run red, then:
      - `ship` State table, the `plan-approved` row, DONE result: "`implemented`; a chunk
        ended: `plan-approved` → the next `implementer`".
      - `ship` Result protocol, a new bullet before **ESCALATE**, as in the Approach
        ("`ship`"): a chunk ended; the `CHUNK:` no-progress rule, which compares only with
        the previous chunk that returned `DONE`, never with the escalated one, and applies
        only to `DONE` with `STATUS: plan-approved`; `STATUS: implemented` means the stage is
        done; an agent started after an escalation is the next chunk.
        In `## Starting a stage agent`, the sentence "The same holds for a stage run again
        under the Result protocol" also names every chunk.
      - README: the statuses row `plan-approved` → "`implemented` (in chunk mode each chunk
        but the last returns `plan-approved`)"; below the `RESULT` block, one paragraph:
        in chunk mode the implementer adds `CHUNK: <group>/<groups>` after `STATUS`, and
        `ship` counts a repeated group, or a missing line, as a missing RESULT; in
        "Implementation and review", a paragraph `**The chunked implementer.**` that sums
        up groups, the switch, a chunk's end, the note, the final chunk and the metrics.
      Automatic verification: `uv run pytest plugin/tests/test_chunked_implementer.py plugin/tests/test_ship_cost_and_models.py plugin/tests/test_stage_contract.py plugin/tests/test_readme.py plugin/tests/test_prompt_style.py -q` → green.

- [ ] 7. Eval case `implement-stops-at-group-boundary` (AC11, the deterministic part) —
      files: `plugin/tests/test_eval_cases.py`,
      `plugin/evals/implement-stops-at-group-boundary/{case.yaml,scaffold.sh,graders/criteria.md}`.
      Tests first:
      - `NEW_CASES` gains `"implement-stops-at-group-boundary"`. `WRONG_BEHAVIOUR` gains
        it with `["implemented", "step 3", "Chunk notes", "converge"]`. That makes the
        existing parametrised tests (scaffold, grader, English, allow rule) cover it.
      - A fixture `tags(tmp_path)` and:
        - `test_group_boundary_fixture_is_ready_for_the_skill`:
          `assert_ready_for_the_skill(..., "feat/001-order-tags", "001-order-tags", "plan-approved")`
          and `VERIFY` green.
        - `test_group_boundary_chunking_is_on`: `workflow.json` has
          `"implement": {"chunked": true}`, and `workflow_config.load_sections` reports no
          problem for it.
        - `test_group_boundary_plan_has_two_groups`: `## Steps` has exactly
          `### Group 1 — ` and `### Group 2 — `, steps 1 and 2 under the first and step 3
          under the second, all unticked; `## Chunk notes` is present with no entry; the
          matrix has four columns.
        - `test_group_boundary_group_one_alone_is_green`: write a correct `shop/tags.py`
          and its tests into the fixture, and `VERIFY` stays green, with no `shop/labels.py`.
      - `test_group_boundary_case_allows_agent`: `Agent` is in `allowed_tools`, so a wrong
        converge pass is possible and visible.
      Run red, then write the case: the scaffold as in the Approach ("The eval case"),
      built like `implement-converge-finds-missing-ac/scaffold.sh` (offline bare remote,
      `Read(//<plugin>/**)` allow rule, `workflow.json` with `verify`, `docs`,
      `language: en` and `implement.chunked: true`, a SPEC with the `plan-approved`
      metrics, a PLAN from the English template with an empty red column).
      `case.yaml`: `runs: 1`, `timeout_seconds: 900`, `max_turns: 60`,
      `allowed_tools: [Read, Glob, Grep, Skill, Bash, Edit, Write, Agent]`, and the prompt
      of the converge case (`/pipeline:implement 001`, the owner unavailable).
      `graders/criteria.md` (`type: llm`, English): correct when the final message, or the
      PLAN it summarises, shows steps 1 and 2 ticked and committed, step 3 not started, a
      `## Chunk notes` entry for group 1 with the running `implement_iterations`,
      `status: plan-approved`, and that the chunk ended at the group boundary. Incorrect
      when the agent carries out step 3 or any of group 2, sets `implemented`, runs the
      converge pass or the Definition of Done, ends without a `## Chunk notes` entry, or
      stops inside group 1.
      Automatic verification: `uv run pytest plugin/tests/test_eval_cases.py plugin/tests/test_english_only.py -q` → green.

- [ ] 8. Release 0.8.0 documents (AC16) — files: `plugin/tests/test_release_0_8_0.py`,
      `tests/test_documents.py`, `plugin/CHANGELOG.md`, `docs/ROADMAP.md`,
      `docs/DECISIONS.md`.
      Tests first:
      - `test_the_changelog_records_spec_012`: in `## 0.8.0`, the consumer impact holds
        `` `implement.chunked` ``, `off`, `older skills` and `ordinary headings`; the
        section holds `` `## Chunk notes` ``, `` `CHUNK: ``, `implement_chunks` and
        `implement-stops-at-group-boundary`.
      - `tests/test_documents.py::test_roadmap_ticks_spec_012`: exactly one roadmap item
        links `specs/012-chunked-implementer/SPEC.md`, and it is ticked.
      - `tests/test_documents.py::test_decisions_record_spec_012`: a row with `SPEC 012`
        holds `chunk` and `group`.
      Run red, then:
      - CHANGELOG `## 0.8.0`: one sentence on SPEC 012 in the intro; the consumer impact
        gets: chunking is off by default (`implement.chunked`); plans written by 0.8.0
        carry `### Group N — ` headings and `## Chunk notes`, which older skills ignore as
        ordinary headings; `/pipeline:init` does not write the key. Under **Added**: the
        group heading and chunk-notes section (map and templates), `implement.chunked`,
        chunk mode in `implement`, the `CHUNK:` line and `ship`'s loop, `implement_chunks`,
        the eval case. Under **Changed**: `plan` always marks groups, `plan-review` checks
        them. The version stays `0.8.0`.
      - ROADMAP: tick the 0.8.0 chunked-implementer item, and reword it to what was built:
        planner groups, a small plan is one group by the planner's judgement, off by
        default with `implement.chunked`.
      - DECISIONS: one row dated 2026-09-24 for SPEC 012, with the SPEC's decisions table
        in brief (planner groups, always marked plus a switch that is off by default, a
        small plan as one group by judgement, converge and DoD in the last chunk, the
        implementer reads the switch and `ship` loops on `plan-approved` with the `CHUNK:`
        no-progress rule, running counters in the note and metrics written once, optional
        `implement_chunks`, one eval case, shipped in 0.8.0). Its rejected alternatives
        column: a step count K, a threshold key, `ship` passing a chunk mode, each chunk
        updating `metrics:`, pytest only.
      Automatic verification: `uv run pytest plugin/tests/test_release_0_8_0.py plugin/tests/test_readme.py tests/test_documents.py -q` → green, then `bash scripts/check.sh` → green.

## Risks and traps

- **Verbatim pins.** `## Project configuration`, `## Reading` and `## Section map` are
  byte-identical across the stage skills (`test_stage_skills.py`,
  `test_targeted_reading.py`, `test_language_contract.py`), and `## Stage agent contract`
  is identical between `ship` and every agent (`test_stage_contract.py`). Chunk text goes
  into new sections and Procedure steps only.
- **The `RESULT` field list** is pinned to four fields in the README and `ship`
  (`test_readme.py::test_the_result_block_matches_the_contract`). The `CHUNK:` line is
  documented in prose and in the implementer agent's intro, not added to the shared block.
- **Template leak check.** `test_language_contract.py` fails when a template heading
  appears as a whole line in `plan`. Name `### Group N — <name>` only inside backticks,
  in running text.
- **Prompt style.** No capitals as emphasis (`test_prompt_style.py`). `CHUNK` appears only
  inside a code span, and the allowlist stays unchanged.
- **English only.** Polish literals (`### Grupa N — `, `## Notatki chunków`) go only
  into `sections.md`, `PLAN.pl.md`, the Polish fixture and the test modules already on the
  allowlist (`test_templates_language.py`, `test_eval_cases.py`). The skills name the
  English literal and point to the map.
- **`validate()` and bool.** Without the fix, `{"chunked": true}` is rejected as "has to be
  bool". With a careless fix, `True` gets through for `str`/`list` keys. Step 2 tests both
  directions.
- **`defaults()` is documented by test.** `test_every_config_key_is_documented_with_its_default`
  derives rows from `defaults()`, so the README row has to land in the same step as the
  default (step 2).
- **The Polish mirror eval fixture changes** (step 1). Its behaviour under test (approval
  over a Polish owner decision) does not depend on the group heading. The 0.8.0 receipt
  runs the whole suite anyway.
- **A chunk interrupted between its last commit and its note** leaves a finished group
  without a note. The next chunk still starts from the committed state and the first
  unticked step. This is accepted, not handled (proposal for the backlog below).
- **Eval spend.** The 5-run measurement costs money (the last full suite of 11 cases was
  $4.61, about $0.42 per case run) and is the owner's step, with an explicit ceiling.

## End-to-end verification

### Automatic (performed by /pipeline:implement)

The change is skill text, templates, configuration code, the metrics script, an eval
fixture and documents. There is no running application.

1. `bash scripts/check.sh` → green: validate --strict when `claude` is on PATH, ruff,
   black, and pytest over `plugin/tests` and `tests`.
2. `git diff origin/main -- plugin/.claude-plugin/plugin.json plugin/tests/test_prompt_style.py`
   → empty: the version stays `0.8.0`, and the capitals allowlist is unchanged.
3. `bash plugin/evals/implement-stops-at-group-boundary/scaffold.sh` in a fresh temporary
   directory, then in it: `python3 <repo>/plugin/bin/workflow_metrics.py --check specs/001-order-tags`
   → exit 0, and `grep -c '^### Group ' specs/001-order-tags/PLAN.md` → `2`.
4. `python3 plugin/bin/workflow_metrics.py specs | head -1` shows an `implement_chunks`
   column.
5. Every AC row of this plan's matrix except AC15 has a red record in its fourth column,
   or `manual` for the 5-run half of AC11. A read of `## AC → steps matrix` confirms it.

Record the results here when done.

### Manual (performed by the owner)

1. **AC11, the 5-run measurement** (eval cost policy, default model), on the owner's
   command after the PR is open:
   `claude plugin eval plugin/ --scaffold --allow-tools Bash Write Edit --trust-plugin --no-publish --ablation none --case implement-stops-at-group-boundary --runs 5 --max-cost-usd 5`.
   5 of 5 → `runs: 1` stays; 4 of 5 → `runs: 3` in `case.yaml`; less → sharper criteria
   or a new fixture, and the case does not ship. The result is recorded in PLAN.md. A
   `--case` run must not overwrite the committed receipt: restore it with
   `git checkout -- plugin/evals/last-run.json`.
2. **A real chunked run** (can be part of the Stage 7 comparison): in a consumer with
   `"implement": {"chunked": true}`, `/pipeline:ship` on a spec whose plan has three
   groups. It should give three implementer subagents, each ending on a committed group
   with a chunk note, the last one reaching `implemented` with `implement_chunks: 3`, and
   `cost_implement_cents` covering all three after `--record-cost`.

## Definition of Done

- [ ] all steps ticked
- [ ] `bash scripts/check.sh` fully green
- [ ] end-to-end verification (automatic) performed, result recorded here
- [ ] `docs/ROADMAP.md` updated; `docs/DECISIONS.md` / domain documents from the map
      in `CLAUDE.md`, if applicable
- [ ] spec status: `implemented`

## Owner decisions

_(appended by /pipeline:ship or a stage on escalation: date, stage, question, decision)_

## Review log

**2026-09-24 — /pipeline:plan-review**

Anti-anchoring leads (from the SPEC alone): map rows and templates first; the switch with a
bool-aware schema; skill text pinned by pytest; `implement_chunks` as an optional counter
plus a three-agent cost fixture; the eval case modelled on the converge case; the resume
edges of a chunk (an escalation mid-group, a converge pass in the last chunk). The plan
matches the first five; the sixth gave both findings.

Findings (counted before the fixes):

| id | severity | finding | change |
|----|----------|---------|--------|
| R1 | `major` | Chunk mode picks "the group that holds the first unticked step", which is undefined when that step lies after the last group (a converge-pass step under `### Converge pass N — `) or when every step is ticked. That is exactly the state after an escalation inside the final chunk, so the resumed agent had no rule and could stop without the Definition of Done. | Approach: a bullet making such a chunk the final one, resumed by the converge-resume rules. Step 5: the `## Chunk mode` text states the rule, and the AC7 test asks for `after the last group`. |
| R2 | `major` | The no-progress rule compared a chunk's `CHUNK:` with "the chunk before it". After an `ESCALATE` in the middle of group 1 (whose result also carries `CHUNK: 1/3`), the agent started after the owner's decision finishes group 1 and reports `1/3` again: a legitimate chunk would be re-run and then escalated. The "no `CHUNK:` line" clause also read as applying to `STATUS: implemented`. | Approach ("`ship`"), step 5 (the agent's `CHUNK:` line also in an `ESCALATE` result) and step 6 (the Result protocol bullet and its test tokens): the comparison is with the previous chunk that returned `DONE`, never with the escalated one, and applies only to `DONE` with `STATUS: plan-approved`. |

Checked and found correct (later stages need not repeat it):

- **coverage:** AC1–AC16 each have steps and a proving test; the matrix matches the steps
  (AC13 and AC14 span two steps each, and both steps name them).
- **compliance:** `validate()` really rejects every bool today
  (`not isinstance(value, expected) or isinstance(value, bool)`), and the proposed guard
  `(expected is not bool and isinstance(value, bool))` keeps `True` out of `str`/`list`
  keys; `load_sections` drops a bad section with a problem, so off is the fallback and
  nothing blocks (DECISIONS 2026-09-23). `implement_chunks` stays out of every `REQUIRED`
  list (SPEC 010). Shared blocks (`## Project configuration`, `## Reading`,
  `## Section map`, `## Stage agent contract`) stay untouched. The Polish literals stay in
  the allowlisted files.
- **tests named by the plan exist as described:** `MAP_SNAPSHOT`, `ENGLISH_HEADINGS`,
  `POLISH_SNAPSHOT`, `key_of`/`check_structure` (exact match, so the `— ` prefix rule is
  needed), `NEW_CASES`, `WRONG_BEHAVIOUR`, `assert_ready_for_the_skill`, `VERIFY`,
  `test_the_mirror_owner_accepted_the_dependency` (compares with `PLAN.pl.md` headings, so
  the fixture and normalisation are needed), `NEW_KEYS` with
  `test_new_counters_are_known_and_never_required` and `test_report_has_columns_for_the_new_keys`,
  `write_agent`/`prompt`/`OPUS`/`run_record` in `test_record_cost.py`,
  `test_every_config_key_is_documented_with_its_default` (derived from `defaults()`, hence
  README row and default in one step), `test_the_implementer_metrics_line`, and the
  template leak check in `test_language_contract.py` (whole lines only, so backticked
  running text is safe). `render()` puts every `COUNTERS` key into the report header, so
  AC14's column follows from the list.
- **minimality:** no new CLI mode, no new module besides one test file, `--record-cost`
  untouched; scope stays within the SPEC.
- **feasibility:** no forward dependencies (templates → config → metrics → planner
  skills → implementer → ship → eval → release); version stays `0.8.0` (already on the
  branch base).
- **E2E:** no running application; the automatic part is executable (`check.sh`, the
  scaffold, `--check`, the report header); the paid 5-run measurement and a real chunked
  `ship` run are rightly manual.
- **testability / test-first:** every step has exact `Automatic verification:` commands;
  every step writes its tests first; the matrix has the fourth column, with AC15 marked
  `n/a — kept behaviour` by its own words.
- **summary:** no dependency, no migration, consistent with the SPEC's owner decisions.
- **language:** the PLAN is in English, as `language: en` requires.
- Not changed, noted: a chunk that escalates mid-group loses its own iterations from the
  running total, as a resumed single context does today; not a regression. This plan has
  no step groups, which the 0.7.0 stages running it neither write nor read.

The plan is ready: both findings were fixable in the plan, no blocker remains, and it adds
no dependency or migration.

## Deviations

_(filled in by /pipeline:implement — every deviation from the plan with its rationale)_

## Final review

_(filled in by /pipeline:final-review)_
