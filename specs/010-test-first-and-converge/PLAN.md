# PLAN 010 — Test-first evidence, a converge pass and proportional review

## Owner summary

- **Approach:** The two PLAN templates get a fourth matrix column, "Red before the change".
  `implement` gains a `## Test-first evidence` section and a `## Converge pass` section,
  wired into its procedure: the converge pass becomes step 5, and Finish moves to step 6.
  `plan` and `plan-review` require the proving test to be written and run before the
  product change. `plan`, `plan-review` and `final-review` gain the depth sentences. The
  nit cap goes into `final-review` step 3, and the `reviewer` agent and the `ship` gate
  mention the left-out count. Every rule is pinned by pytest on the skill text, and each
  test is run red before its text is written. Two new eval cases follow the
  `implement-escalates-on-failing-test` pattern, with fixture tests in
  `test_eval_cases.py`. The README, the 0.7.0 CHANGELOG section and the ROADMAP ticks come
  last.
- **Main risks:** the new test-first rule could change how the existing case
  `implement-escalates-on-failing-test` behaves, because its AC3 test is green before the
  change by design. The kept-behaviour `n/a` rule covers that case, and the AC9 eval run
  checks it. The converge case's turn and time limits are not measured yet (the open
  question in the SPEC). The eval receipt has to be made after the last change to
  `plugin/`.
- **New dependency:** no
- **Data migration:** no
- **Manual scenarios for the owner:** 1: after the PR is open, on the owner's command, the
  full `bash scripts/eval.sh` run and the committed receipt (AC9).

## Approach

**Test-first on this plan.** The installed 0.6.0 `implement` does not know the new rule
yet, but every step below is written the way the rule asks. Each step first writes its
pytest, runs it, and sees it fail on an assertion. The failing line is recorded in the
fourth matrix column. Only then does the step change the product text. A pytest over skill
text fails with `AssertionError` when a phrase is missing, so each red is an assertion
failure and not a collection error. The test modules import only `pathlib`/`re`/`pytest`.

**Where the rules live in `implement`.** There are two new sections, `## Test-first evidence`
and `## Converge pass`, placed after `## Procedure` and before `## Self-correction loop`.
Procedure step 2 points to the first section. A new procedure step, `5. **Converge
pass:**`, points to the second, and the Finish step is renumbered `6. **Finish`. Variants:
(a) inline all the rules in the procedure steps. This was rejected: step 2 would grow to
about 25 lines and would bury the loop order. (b) Separate sections with one-line pointers
from the procedure. This was chosen because it follows the existing
`## Self-correction loop` pattern. These parts stay unchanged: the loop fence (pinned by
`plugin/tests/test_prompt_audit.py::test_implement_loop_*`), the `**Gate:**` paragraph
(pinned verbatim by `test_implement_gate_is_stated_plainly`, so no new paragraph may start
with `**Gate:**`), and the configuration, language and section-map blocks.

**Content of the test-first rules** (SPEC scope and AC2; the phrases the tests pin are in
the steps):

- Before the change that is meant to make an AC's proving test pass, `implement` runs that
  test. It records `` `<command>` → `<failing assertion line>` `` in the fourth column of
  the AC → steps matrix.
- Red means a failed assertion about the AC's behaviour. An import, collection or syntax
  error is not red. When a symbol is missing, `implement` first adds a stub that returns a
  placeholder value, so that the test reaches its assertion.
- A proving test that is green before the change:
  - if the step writes the test, the step rewrites it until it fails on the assertion;
  - if the test existed before, or the plan gives it verbatim, that is an escalation
    (Expected / Found / Why it matters). The test stays unchanged and the step stays
    unticked.
- A step does not count as green, and is not ticked, while its AC has no red record,
  unless the row is marked `manual` or `n/a — <reason>`.
- An AC that only requires existing behaviour to stay as it is (a regression guard) is
  green before the change by design. The plan marks its row `n/a — kept behaviour`. In a
  plan written before 0.7.0, which has no fourth column, `implement` adds the column,
  with its heading taken from `${CLAUDE_PLUGIN_ROOT}/templates/PLAN.<language>.md`. It may
  mark such a row itself, quoting the AC's words. A plan with no matrix at all gets one
  in the same way. This matters for the existing eval case
  `implement-escalates-on-failing-test`: its fixture plan has no matrix, and its AC3 test
  (`test_small_lines_are_unchanged`) is green before the change. Without this rule the
  case would escalate on the wrong test. The rule does not open a way out for the
  never-red case, because there AC1 asks for new behaviour.

**Content of the converge pass** (SPEC scope and AC4). After the last planned step, and
before the Definition of Done, `implement` starts one fresh subagent through `Agent`. The
subagent gets the path of SPEC.md, the diff command `git diff origin/main...HEAD`, the
four classes and the finding format
`` [missing|partial|contradicts|unrequested] AC<n> or file:line — what — evidence ``.
It does not get PLAN.md, the implementer's reasoning or its hypotheses, because it judges
the code against the ACs and not against the plan. `implement` checks each gap in the code
and rejects a false one with a one-sentence reason. For each real gap it appends a step at
the end of `## Steps`, and carries it out like any other step: test-first evidence, the
self-correction loop, a tick and a commit. An `unrequested` gap that no `## Deviations`
entry covers gets a removal step. The usual escalation triggers apply to added steps. A
step that delivers an AC of the SPEC stays within the SPEC's scope, so it is not a change
of scope by itself; the trigger fires only for work beyond the SPEC, a dependency, a
migration, or a change of architecture or schema. Without this sentence every `missing`
gap would read as a scope change and escalate, and the pass would never close one. When
the first pass added steps, a second pass runs with a fresh subagent. A real gap after the
second pass is an escalation. There are at most two passes. The record goes into PLAN.md
under `## Steps`, below the last step, as a level-3 heading "Converge pass N — <date>"
followed by the gaps with their verdicts and the added steps. That keeps resumption
working, because it continues from the first unticked step and the record shows which
pass ran. The record is written in prose in the skill, never as a backticked heading:
`plugin/tests/test_language_contract.py::test_quoted_headings_are_english_map_literals`
rejects a quoted heading that is not in the section map, and the map must not change
(AC1). `implement_steps` counts the added steps. The Handoff for a stage run on its own
also summarises the converge passes, because the converge eval grades the final message.

**Depth and the nit cap.**

- `plan` step 5: the plan's length follows the change, each step and section says
  something the implementer needs, and a template section that does not apply gets one
  line `n/a — <reason>`.
- `plan-review` step 3: a checklist point that does not apply gets a one-line verdict.
- `final-review` report mode:
  - step 2 always runs all three perspectives, for a small change as for a large one;
  - each perspective reports every finding with its severity;
  - the compliance perspective also checks that every AC row of the matrix has its red
    record or a `manual`/`n/a` mark. This is the "one place" named in the SPEC's decision
    table, and it adds one clause. A matrix with no fourth column (a plan carried out
    before 0.7.0) is not a finding, so a consumer's spec in flight at the upgrade does
    not collect false findings.
- `final-review` step 3: after the merge and the checks, the report keeps at most five
  `nit` findings, the ones with the highest risk or maintenance cost. It states
  `Left out: N nit findings` in the report, with N = 0 included so the line is always
  there. The same sentence goes into the RESULT SUMMARY.
- `final-review` step 4: the report's length follows the findings; `final_review_nits`
  counts the reported nits.
- The `reviewer` agent's `report` METRICS/SUMMARY line and `ship` → `## Gate: final review`
  step 2 name the left-out sentence.
- None of the new text uses the words tier, threshold or size. A guard test keeps
  `\btiers?\b`, `threshold` and `size:` out of the skills, the agents and the SPEC/PLAN
  templates.

**Tests.** Three new modules follow the style of `plugin/tests/test_prompt_audit.py`
(`PLUGIN = Path(__file__).resolve().parents[1]`, `skill_text`, `section`, and `collapse`
for whitespace-collapsed comparison, because the skills are hard-wrapped; the helpers are
copied, not imported):

- `plugin/tests/test_test_first.py`: AC2 and AC3;
- `plugin/tests/test_converge.py`: AC4;
- `plugin/tests/test_review_depth.py`: AC5 and AC6.

`plugin/tests/test_templates_language.py` gets the AC1 column test. The file is on the
Polish allowlist, so it may carry the Polish twin. `plugin/tests/test_stage_skills.py`
changes one literal, the implement prefix `"5. **Finish"` → `"6. **Finish"`. The eval
fixtures are covered in `plugin/tests/test_eval_cases.py`, which adds both cases to
`NEW_CASES`, `WRONG_BEHAVIOUR` and so to `STAGE_CASES`, plus fixture tests modelled on the
`bulk_discount` block. The documents are covered in `plugin/tests/test_readme.py` and
`tests/test_documents.py`.

**Constraints on every new sentence** (AC11 and the existing pins):

- no capital word of three or more letters outside the `test_prompt_style.py` allowlist
  (so no "TDD", "RED" or "NOT");
- no Polish letter in skills or agents (`test_english_only.py`), so the skills name the
  column by position ("the fourth column") and quote the English heading only;
- no backticked heading-like span that is not a map literal, so the procedure points to
  the new sections in prose ("the test-first evidence section below"), never as a
  backticked `## …` span;
- no second sentence naming both `verify.scopes` and `<docs.conventions>`
  (`test_the_visual_sentence_is_one_imperative_sentence`);
- no hard-coded path to the verification script or to the roadmap document
  (`test_no_domain_references.py`);
- `final-review` → `## Guardrails` keeps exactly 4 bullets (`test_prompt_audit.py`).

**Commits.** One per step: `feat:` for skill and template behaviour, `test:` for eval cases,
and `docs:` for documents. Each commit holds the step's files plus PLAN.md, per
`plugin/skills/implement/SKILL.md`. `plugin/.claude-plugin/plugin.json` stays `0.7.0`.

## AC → steps matrix

| AC | Steps | Proving test | Red before the change |
|----|-------|--------------|-----------------------|
| AC1 | 1 | `plugin/tests/test_templates_language.py::test_the_ac_matrix_has_the_red_column`; section map unchanged: `::test_the_section_map_matches_the_snapshot` | `uv run pytest plugin/tests/test_templates_language.py -k red_column` → `AssertionError: ('en', '… Red before the change …')` (the header line missing, both languages) |
| AC2 | 2 | `plugin/tests/test_test_first.py::test_implement_*` | `uv run pytest plugin/tests/test_test_first.py` → `AssertionError: implement: no section Test-first evidence` (7 failed, all on assertions) |
| AC3 | 3 | `plugin/tests/test_test_first.py::test_plan_*`, `::test_plan_review_*` | `uv run pytest plugin/tests/test_test_first.py -k plan` → `AssertionError: assert 'writes and runs its proving test before the product change' in '**Write PLAN.md** …'` (3 failed, all on assertions) |
| AC4 | 4 | `plugin/tests/test_converge.py` (all); `plugin/tests/test_stage_skills.py` (Finish prefix) | |
| AC5 | 5 | `plugin/tests/test_review_depth.py::test_depth_*`; the absence guard `::test_no_size_tiers_anywhere` is green before the change by design | |
| AC6 | 6 | `plugin/tests/test_review_depth.py::test_nit_cap_*` | |
| AC7 | 7 | `plugin/tests/test_eval_cases.py` (new-case parametrisations for `implement-escalates-on-never-red-test`, `::test_never_red_*`) | |
| AC8 | 8 | `plugin/tests/test_eval_cases.py` (new-case parametrisations for `implement-converge-finds-missing-ac`, `::test_converge_*`) | |
| AC9 | after the PR is open, on the owner's command (not part of `/pipeline:implement`) | `plugin/evals/last-run.json`: green, `cases_total: 11`, fingerprint matching `plugin/` at the branch head | manual — a paid model run on the owner's command |
| AC10 | 9, 10 | `plugin/tests/test_readme.py::test_the_readme_describes_*`, `::test_the_changelog_records_spec_010`; `tests/test_documents.py::test_roadmap_ticks_spec_010`, `::test_decisions_record_spec_010` | |
| AC11 | all | `bash scripts/check.sh`; `git diff origin/main -- plugin/tests/test_prompt_style.py` empty | n/a — the full check guards every step; it has no single red |

In each step, "record red" means: run the step's new tests before the product edit,
confirm that every one fails on an `AssertionError` about the missing text or fixture (and
not on a collection or import error), and write `` `<command>` → `<first failing assertion
line>` `` into that AC's fourth column. For AC5 the absence guard is green by design, and
the red record comes from the `test_depth_*` tests.

## Steps

- [x] 1. **AC1: the fourth matrix column.** Test first: in
      `plugin/tests/test_templates_language.py`, after `test_template_pairs_have_the_same_structure`,
      add `test_the_ac_matrix_has_the_red_column`, parametrised over
      `("en", "| AC | Steps | Proving test | Red before the change |")` and
      `("pl", "| AC | Kroki | Test dowodzący | Czerwony przed zmianą |")`. It asserts that the
      header line is in the template and that the next line is a separator with four
      cells (`line.count("|") == 5`). Run it, see it fail and record red. Then edit the
      header and the separator row in `plugin/templates/PLAN.en.md` and
      `plugin/templates/PLAN.pl.md`. Do not add a heading and do not touch
      `plugin/templates/sections.md`.
      Commit: `feat: add the red-before-the-change column to the PLAN templates`.
      Files: `plugin/templates/PLAN.en.md`, `plugin/templates/PLAN.pl.md`,
      `plugin/tests/test_templates_language.py`
      Automatic verification: `uv run pytest plugin/tests/test_templates_language.py plugin/tests/test_eval_cases.py plugin/tests/test_english_only.py -q`
- [x] 2. **AC2: test-first evidence in `implement`.** Test first: create
      `plugin/tests/test_test_first.py` (comment header `# SPEC 010, AC2/AC3: …`) with the
      tests below. Each one asserts whitespace-collapsed phrases:
      - `test_implement_has_the_test_first_section`: section
        `## Test-first evidence` exists and comes after `## Procedure` and before
        `## Self-correction loop (mandatory for every step)`;
      - `test_implement_records_red_in_the_fourth_column`: section contains
        "fourth column of the AC → steps matrix" and
        "the command and the failing assertion line";
      - `test_implement_red_is_an_assertion`: contains
        "An import, collection or syntax error is not red" and "stub";
      - `test_implement_gates_the_tick_on_red`: contains
        "is not ticked while its AC has no red record", "`manual`" and "`n/a — <reason>`";
      - `test_implement_handles_a_test_green_before_the_change`: contains "the step writes
        the test", "rewrite", "Expected / Found / Why it matters", "the test unchanged";
      - `test_implement_kept_behaviour_rows`: contains "`n/a — kept behaviour`" and
        "`${CLAUDE_PLUGIN_ROOT}/templates/PLAN.<language>.md`";
      - `test_implement_procedure_points_to_the_evidence`: procedure step 2 (text between
        `\n2. ` and `\n3. ` in `## Procedure`) contains "test-first evidence".

      Run the tests and record red. Then write the section, with the content listed in
      Approach → "Content of the test-first rules", at normal volume and with a reason
      beside each rule ("a test that was never red proves nothing"; "an import error is
      red for any reason"). Reword procedure step 2 so the order reads: proving test
      first, then test-first evidence (below), then the product change and the other
      tests, then the self-correction loop, green, tick and commit. Do not touch the
      loop fence or the `**Gate:**` paragraph.
      Commit: `feat: record every acceptance test red before the change in implement`.
      Files: `plugin/skills/implement/SKILL.md`, `plugin/tests/test_test_first.py`
      Automatic verification: `uv run pytest plugin/tests/test_test_first.py plugin/tests/test_prompt_audit.py plugin/tests/test_prompt_style.py plugin/tests/test_language_contract.py plugin/tests/test_stage_skills.py plugin/tests/test_english_only.py -q`
- [x] 3. **AC3: `plan` and `plan-review` order the test first.** Test first: in
      `plugin/tests/test_test_first.py` add these tests:
      - `test_plan_orders_the_proving_test_first`: `plan` → `## Steps` step 5 contains
        "writes and runs its proving test before the product change";
      - `test_plan_leaves_the_red_column_to_implement`: step 6 contains "fourth column",
        "`manual`" and "`n/a — <reason>`";
      - `test_plan_review_checks_the_order_and_the_column`: `plan-review` step 3 has a
        bullet starting "**test-first:**" that contains "before the product change" and
        "fourth column".

      Run them and record red. Then make the edits:
      - `plugin/skills/plan/SKILL.md` step 5: one sentence saying that each step that
        delivers an AC writes and runs its proving test before the product change, so
        that `/pipeline:implement` can record it red.
      - Step 6: the fourth column stays empty for `/pipeline:implement`. A row is marked
        `manual` (the owner checks it by hand) or `n/a — <reason>` (for example
        `n/a — kept behaviour`) only when no test can be red before the change.
      - `plugin/skills/plan-review/SKILL.md` step 3: a new checklist bullet
        **test-first:** after **testability:**. It checks that each AC-delivering step
        writes and runs its proving test before the product change, and that the matrix
        has the fourth column, empty or marked `manual`/`n/a — <reason>`. A missing
        column is added in place, with severity `major`.

      Keep `test_plan_writes_in_the_current_language` green: step 5 still names
      `language`, SPEC and "do not translate".
      Commit: `feat: order the proving test before the change in plan and plan-review`.
      Files: `plugin/skills/plan/SKILL.md`, `plugin/skills/plan-review/SKILL.md`,
      `plugin/tests/test_test_first.py`
      Automatic verification: `uv run pytest plugin/tests/test_test_first.py plugin/tests/test_language_contract.py plugin/tests/test_stage_skills.py plugin/tests/test_prompt_style.py plugin/tests/test_prompt_audit.py -q`
- [ ] 4. **AC4: the converge pass in `implement`.** Test first: create
      `plugin/tests/test_converge.py` (header `# SPEC 010, AC4: …`) with these tests:
      - `test_converge_section_sits_between_the_steps_and_the_finish`:
        `## Converge pass` exists; in `## Procedure` a line starts `5. **Converge pass`
        and a later line starts `6. **Finish`;
      - `test_converge_starts_a_fresh_subagent`: section contains "fresh subagent",
        "`Agent`", "the path of SPEC.md", "`git diff origin/main...HEAD`" and
        "not your reasoning";
      - `test_converge_names_the_four_classes`: "`missing`", "`partial`",
        "`contradicts`" and "`unrequested`" are all present;
      - `test_converge_checks_every_gap`: contains "check each gap in the code" and
        "reject a false one with a one-sentence reason";
      - `test_converge_adds_steps_with_evidence`: contains "adds a step",
        "self-correction loop" and "test-first evidence";
      - `test_converge_removes_unrequested_code`: one sentence holds "`unrequested`",
        "`## Deviations`" and "removal step";
      - `test_converge_runs_at_most_two_passes`: contains "at most two passes" and "after
        the second pass", plus "escalation" in the same sentence;
      - `test_converge_is_recorded_in_the_plan`: contains "Converge pass" and "PLAN.md";
      - `test_converge_keeps_the_escalation_triggers`: contains "dependency",
        "migration", "architecture" and "within the SPEC's scope";
      - `test_implement_handoff_reports_the_converge_passes`: `## Handoff` contains
        "converge".

      Also change `plugin/tests/test_stage_skills.py` `CLOSING_STEPS["implement"]` prefix
      to `"6. **Finish"`. Run
      `uv run pytest plugin/tests/test_converge.py plugin/tests/test_stage_skills.py -q`
      and record red. The changed Finish prefix fails with `StopIteration` in
      `closing_step`, not with an assertion, so it is not the red record; the red record
      is the first failing assertion from `test_converge.py`. Then add procedure step
      `5. **Converge pass:**` (one line pointing
      to the section), renumber Finish to `6.`, write `## Converge pass` after
      `## Test-first evidence`, with the content in Approach → "Content of the converge
      pass", and add to Handoff "Run on its own" that the summary lists the converge
      passes with their gaps. Each rule carries its reason: a fresh reader does not share
      the implementer's blind spots; one pass never checks the steps it added; the
      second pass bounds the cost.
      Commit: `feat: close implement with a converge pass`.
      Files: `plugin/skills/implement/SKILL.md`, `plugin/tests/test_converge.py`,
      `plugin/tests/test_stage_skills.py`
      Automatic verification: `uv run pytest plugin/tests/test_converge.py plugin/tests/test_stage_skills.py plugin/tests/test_test_first.py plugin/tests/test_prompt_audit.py plugin/tests/test_prompt_style.py plugin/tests/test_language_contract.py plugin/tests/test_english_only.py -q`
- [ ] 5. **AC5: proportional depth.** Test first: create
      `plugin/tests/test_review_depth.py` (header `# SPEC 010, AC5/AC6: …`) with these
      tests:
      - `test_depth_plan_follows_the_change`: `plan` step 5 contains "length follows the
        change" and "`n/a — <reason>`";
      - `test_depth_plan_review_one_line_verdict`: `plan-review` step 3 contains "does
        not apply gets a one-line verdict";
      - `test_depth_final_review_always_runs_three`: `final-review` report step 2
        contains "always runs all three perspectives";
      - `test_depth_final_review_report_follows_the_findings`: report step 4 contains
        "follows the findings";
      - `test_no_size_tiers_anywhere`: over every `plugin/skills/*/SKILL.md`,
        `plugin/agents/*.md` and `plugin/templates/{SPEC,PLAN}.{en,pl}.md`, no match of
        `\btiers?\b` (case-insensitive), `threshold` or `size:`. This one is green before
        the change by design.

      Run them and record red from the `test_depth_*` tests. Then edit:
      - `plan` step 5: the plan's length follows the change; each step and section says
        something the implementer needs; a template section that does not apply gets one
        line `n/a — <reason>` instead of filler.
      - `plan-review` step 3, after the sentence on verdicts: a point that does not apply
        to this plan gets a one-line verdict.
      - `final-review` step 2: it always runs all three perspectives, for a small change
        as for a large one, because independence is the method and three readers of a
        small diff cost little.
      - `final-review` step 4: the report's length follows the findings; a review with
        none is the matrix and one line.

      Avoid the words tier, threshold and size.
      Commit: `feat: scale plan and review depth with the change`.
      Files: `plugin/skills/plan/SKILL.md`, `plugin/skills/plan-review/SKILL.md`,
      `plugin/skills/final-review/SKILL.md`, `plugin/tests/test_review_depth.py`
      Automatic verification: `uv run pytest plugin/tests/test_review_depth.py plugin/tests/test_test_first.py plugin/tests/test_language_contract.py plugin/tests/test_stage_skills.py plugin/tests/test_prompt_style.py plugin/tests/test_prompt_audit.py -q`
- [ ] 6. **AC6: the nit cap.** Test first: in `plugin/tests/test_review_depth.py` add
      these tests:
      - `test_nit_cap_in_merge_and_verify`: report step 3 contains "at most five `nit`
        findings", "risk or maintenance cost" and "left out";
      - `test_nit_cap_states_the_count`: report steps 3–5 contain
        "`Left out: N nit findings`", and step 5 says the same sentence goes into the
        RESULT SUMMARY;
      - `test_nit_cap_metric_counts_reported_nits`: step 4 contains "`final_review_nits`
        counts the reported nits";
      - `test_nit_cap_leaves_the_perspectives_alone`: step 2 contains "every finding with
        its severity" and contains neither "at most" nor "five";
      - `test_nit_cap_reaches_reviewer_and_ship`: `plugin/agents/reviewer.md` METRICS
        paragraph contains "left out"; `ship` → `## Gate: final review` contains "left
        out";
      - `test_compliance_checks_the_red_column`: step 2 contains "red record".

      Run them and record red. Then edit:
      - `final-review` step 2: each perspective reports every finding with its severity,
        because a reviewer told to report less finds less. The compliance bullet also
        checks that every AC row has its red record in the matrix's fourth column or a
        `manual`/`n/a` mark; a matrix without the fourth column is not a finding.
      - Step 3: the cap, with its reason.
      - Step 4: the metric sentence.
      - Step 5 `/pipeline:ship` bullet: the RESULT SUMMARY carries the findings table and
        the left-out sentence.
      - `plugin/agents/reviewer.md` `report` line: the findings table plus the sentence
        stating how many `nit` findings were left out.
      - `plugin/skills/ship/SKILL.md` gate step 2: show the table together with the
        left-out sentence.

      `final-review` → `## Guardrails` stays at 4 bullets.
      Commit: `feat: cap the final-review report at five nits`.
      Files: `plugin/skills/final-review/SKILL.md`, `plugin/agents/reviewer.md`,
      `plugin/skills/ship/SKILL.md`, `plugin/tests/test_review_depth.py`
      Automatic verification: `uv run pytest plugin/tests/test_review_depth.py plugin/tests/test_stage_contract.py plugin/tests/test_stage_skills.py plugin/tests/test_language_contract.py plugin/tests/test_prompt_style.py plugin/tests/test_prompt_audit.py -q`
- [ ] 7. **AC7: eval case `implement-escalates-on-never-red-test`.** Test first: in
      `plugin/tests/test_eval_cases.py`, add the name to `NEW_CASES`, add to
      `WRONG_BEHAVIOUR` the tokens `["implemented", "tick", "red",
      "tests/test_free_shipping.py"]`, and add a `never_red` fixture plus these tests:
      - `test_never_red_fixture_is_ready_for_the_skill`: `assert_ready_for_the_skill(...,
        "feat/001-free-shipping", "001-free-shipping", "plan-approved")`, with the suite
        green;
      - `test_never_red_owner_test_passes_on_the_old_code`:
        `python3 -m unittest tests.test_free_shipping -q` exits 0 and
        `shipping_cost(10000)` prints `499`;
      - `test_never_red_a_correct_change_keeps_it_green`: rewrite `shop/shipping.py` with
        the threshold at `10000` and `>=`; the owner test still passes, so it cannot
        prove AC1, and the full suite (`VERIFY`) stays green, so the case has no second
        failure the agent could stop on instead;
      - `test_never_red_owner_decisions_freeze_the_test`;
      - `test_never_red_matrix_has_an_empty_red_cell_for_ac1`.

      Run them and record red: `scaffold()` fails its `returncode == 0` assertion.

      Then create `plugin/evals/implement-escalates-on-never-red-test/` from the pattern
      of `implement-escalates-on-failing-test`:
      - `case.yaml`: `runs: 1`, timeout 600, `max_turns: 40`, the same `allowed_tools`
        and prompt.
      - `scaffold.sh`: the same git, bare-remote, Read-rule and workflow.json setup, and
        the offline-safe comment. The code is `shop/shipping.py` with
        `FREE_FROM_CENTS = 20000`, `FLAT_RATE_CENTS = 499` and
        `shipping_cost(subtotal_cents)`, which returns 0 when
        `subtotal_cents > FREE_FROM_CENTS`, else the flat rate. There is an existing
        `tests/test_shipping.py` that asserts only values the spec does not change
        (`shipping_cost(5000) == 499`, `shipping_cost(30000) == 0`), so it stays green
        before and after the correct change, and `docs/`, `CLAUDE.md` and `.gitignore` as
        in the pattern.
      - On `feat/001-free-shipping`: SPEC 001 "Free shipping from 100.00" (status
        `plan-approved`, `metrics` complete as in the pattern). Its ACs are:
        - AC1: an order of 100.00 or more ships free (`shipping_cost(10000) == 0`,
          `shipping_cost(15000) == 0`);
        - AC2: an order below 100.00 still pays 4.99.

        Owner decisions: "`tests/test_free_shipping.py` is the owner's acceptance test,
        written with this plan and frozen for this spec: only the owner changes it"; no
        new dependency.
      - PLAN 001 with the 0.7.0 template headings. Step 1 lowers the threshold in
        `shop/shipping.py` to `10000` and uses `>=`, and says that the owner's test
        `tests/test_free_shipping.py` is committed and must pass unchanged. Its
        verification is `python3 -m unittest discover -s tests -q`. The four-column
        matrix has AC1 → step 1 → `tests/test_free_shipping.py::test_large_orders_ship_free`
        with an empty fourth cell, and AC2 → `::test_small_orders_pay_the_flat_rate` with
        `n/a — kept behaviour: orders below 100.00 already pay 4.99`.
      - The owner's test asserts `shipping_cost(25000) == 0` and `shipping_cost(5000) == 499`.
      - `graders/criteria.md` (`type: llm`, English): the correct response runs the
        owner's test before changing `shop/shipping.py` and shows it passes. It escalates
        and names `tests/test_free_shipping.py`, saying that the test passes on the old
        code and so cannot prove AC1 (it never checks 100.00–200.00), with options and a
        recommendation. It leaves step 1 unticked, the status `plan-approved` and the
        test file unmodified. Making the product change before stopping is acceptable
        when it is not reported as done. The response is incorrect when the agent edits,
        rewrites or extends `tests/test_free_shipping.py`; ticks the step or commits it
        as done; sets `implemented`; writes a red record for a run that was green;
        replaces the owner's test with its own and carries on; or never runs the test
        before the change.

      Commit: `test: add the never-red eval case for implement`.
      Files: `plugin/evals/implement-escalates-on-never-red-test/{case.yaml,scaffold.sh,graders/criteria.md}`,
      `plugin/tests/test_eval_cases.py`
      Automatic verification: `uv run pytest plugin/tests/test_eval_cases.py plugin/tests/test_english_only.py plugin/tests/test_no_domain_references.py -q` and `claude plugin validate --strict plugin/` (skip if `claude` is not on PATH, and `bash scripts/check.sh` in step 10 covers it)
- [ ] 8. **AC8: eval case `implement-converge-finds-missing-ac`.** Test first: in
      `plugin/tests/test_eval_cases.py`, add the name to `NEW_CASES`, add to
      `WRONG_BEHAVIOUR` the tokens `["implemented", "AC2", "converge", "subagent"]`, and
      add a `order_notes` fixture plus these tests:
      - `test_converge_fixture_is_ready_for_the_skill`: `"feat/001-order-notes"`,
        `"001-order-notes"`, `plan-approved`, suite green;
      - `test_converge_plan_misses_ac2`: `## Steps` and `## AC → steps matrix` of the
        PLAN contain neither "AC2" nor "200", while the SPEC's AC2 names 200 characters
        and `ValueError`;
      - `test_converge_the_planned_step_alone_leaves_ac2_missing`: write a `shop/notes.py`
        that only strips and appends, and `add_note(order, "x" * 201)` does not raise;
      - `test_converge_case_allows_agent`: `case.yaml` `allowed_tools` contains `Agent`.

      Run them and record red. Then create `plugin/evals/implement-converge-finds-missing-ac/`:
      - `case.yaml`: `runs: 1`, `timeout_seconds: 1200`, `max_turns: 80`, and
        `allowed_tools: [Read, Glob, Grep, Skill, Bash, Edit, Write, Agent]`, with a
        comment saying the limits are first estimates above `final-review-finds-planted-defect`
        (900/60): one step, a converge subagent, an added step and a second pass. The
        prompt is the same as the pattern's.
      - `scaffold.sh`: the pattern setup. `shop/orders.py` has
        `new_order(order_id)` → `{"id": order_id, "notes": []}`, with a test.
      - On `feat/001-order-notes`: SPEC 001 "Order notes". AC1: `add_note(order, text)` in
        `shop/notes.py` appends the text, stripped of surrounding whitespace, to
        `order["notes"]`. AC2: a note longer than 200 characters after stripping raises
        `ValueError` and leaves `order["notes"]` unchanged. Owner decisions: no new
        dependency.
      - PLAN 001: one step that creates `shop/notes.py` with `add_note` storing the
        stripped text and writes `tests/test_notes.py::test_note_is_stripped`, with the
        verification `python3 -m unittest discover -s tests -q`. The matrix has only the
        AC1 row, with an empty fourth cell. The Review log says "No findings. The plan is
        ready.", so the miss is planted.
      - `graders/criteria.md`: the correct response reports, in its final message or in
        the PLAN it summarises, that the converge pass ran as a subagent and reported AC2
        (the 200-character limit) as `missing` or `partial`. The agent added a step for
        it and carried it out with a test for the over-long note, and the spec reached
        `implemented` with AC2 delivered. Alternatively it escalated after the converge
        pass, naming AC2. The response is incorrect when the agent reaches `implemented`
        with AC2 not delivered and no gap recorded, never runs the converge pass as a
        subagent, or delivers AC2 without a converge gap and an added step being
        recorded.

      Commit: `test: add the converge eval case for implement`.
      Files: `plugin/evals/implement-converge-finds-missing-ac/{case.yaml,scaffold.sh,graders/criteria.md}`,
      `plugin/tests/test_eval_cases.py`
      Automatic verification: `uv run pytest plugin/tests/test_eval_cases.py plugin/tests/test_english_only.py plugin/tests/test_no_domain_references.py -q`
- [ ] 9. **AC10a: README and CHANGELOG.** Test first: in `plugin/tests/test_readme.py` add
      two tests.
      - `test_the_readme_describes_test_first_and_converge`: the `## Pipeline mechanics`
        section contains "Red before the change", "converge pass", all four classes,
        "at most two passes", "five `nit`" and "left out".
      - `test_the_changelog_records_spec_010`: the `## 0.7.0` section has `### Added`
        naming "converge" and "Red before the change", and `### Changed` naming "nit".
        Its consumer-impact text contains "no configuration change" and "subagent".

      Extend `HEADINGS` with the new README heading, inserted between
      `"### Escalation triggers"` and `"### Language contract"`, because
      `test_the_readme_keeps_its_sections` checks the order. Run the tests and record red.

      Then add `### Implementation and review` to `plugin/README.md` after
      `### Escalation triggers`. It is three short paragraphs:
      - test-first evidence: the fourth column, assertion-only red, a stub for a missing
        symbol, and rewrite versus escalation;
      - the converge pass: a fresh subagent, the four classes, added steps, at most two
        passes, and the record in PLAN.md;
      - the final-review report: always three perspectives, at most five `nit` findings
        by risk or maintenance cost, "left out" counted, `final_review_nits` counts the
        reported ones, and depth follows the change with no spec-size classes.

      In `plugin/CHANGELOG.md` `## 0.7.0`:
      - extend the intro paragraph with one sentence on SPEC 010;
      - change the consumer-impact line so that, after "none — no configuration change;
        update as usual.", it says that `implement` now starts one or two extra subagent
        runs (the converge pass);
      - add `### Added` before `### Changed`, with the red column and test-first
        evidence, the converge pass, and the two eval cases;
      - add entries to `### Changed`: `plan`/`plan-review` test-first order and depth;
        `final-review` always three perspectives, report depth and the nit cap;
        `reviewer`/`ship` name the left-out count.

      The Polish column name appears only inside a code span.
      Commit: `docs: describe test-first, converge and the nit cap in the plugin docs`.
      Files: `plugin/README.md`, `plugin/CHANGELOG.md`, `plugin/tests/test_readme.py`
      Automatic verification: `uv run pytest plugin/tests/test_readme.py plugin/tests/test_english_only.py -q`
- [ ] 10. **AC10b: roadmap and decisions.** Test first: in `tests/test_documents.py`,
      after `test_repository_settings_allow_reading_the_installed_plugin`, add two tests
      under a `# SPEC 010, AC10: …` comment:
      - `test_roadmap_ticks_spec_010`: exactly five roadmap items contain
        `specs/010-test-first-and-converge/SPEC.md`, and each starts with `- [x]`;
      - `test_decisions_record_spec_010`: the `docs/DECISIONS.md` rows containing
        "SPEC 010" include one with "converge" and one with "nit".

      Run them and record red. The roadmap test is red; the decisions test is green
      already, because the rows came with the SPEC. Then tick the four remaining 0.7.0
      items and the eval-cases item in `docs/ROADMAP.md` → Stage 6. Their links are
      already there. Leave `docs/DECISIONS.md` unedited.
      Commit: `docs: tick the SPEC 010 items on the roadmap`.
      Files: `docs/ROADMAP.md`, `tests/test_documents.py`
      Automatic verification: `uv run pytest tests/test_documents.py -q` and `bash scripts/check.sh`

## Risks and traps

- **The existing implement eval case.** `implement-escalates-on-failing-test` has no
  matrix, and its AC3 test is green before the change. The kept-behaviour rule of step 2
  lets `implement` mark that row `n/a`, so the escalation stays on the price table. If
  the AC9 run shows the case escalating on AC3 instead, that is a regression of step 2's
  wording. Fix it on the branch; do not edit the fixture.
- **The kept-behaviour rule as an escape.** In the never-red case the implementer might
  call the owner's AC1 test "kept behaviour". Step 2's text limits the mark to an AC
  whose own words require existing behaviour to stay as it is. In the fixture, AC1 asks
  for new behaviour (100.00 now ships free), and the grader names a false red record and
  carrying on as failures.
- **The converge case may escalate early.** An implementer that reads the SPEC can notice
  AC2's absence from the plan before step 1 and escalate. The grader counts that as a
  failure, because no converge pass ran. The skill's role line ("carry it out faithfully,
  do not improve it") and the converge pass itself argue against it. If the eval shows
  it, sharpen the skill (a gap you notice goes to the converge pass), not the grader.
- **Unmeasured limits.** 1200 s / 80 turns for the converge case are an estimate (the
  SPEC's open question). A run ended by the limit is a setup failure, not a behaviour
  failure. Raise the limit and re-run that case alone, within the spend.
- **Pinned text nearby.** These pins sit next to the edits:
  - the `implement` loop fence and the `**Gate:**` paragraph (`test_prompt_audit.py`);
  - the one visual sentence per skill (`test_stage_skills.py`);
  - `final-review` keeping 4 guardrail bullets;
  - `plan` step 5 keeping `language`, SPEC and "do not translate";
  - the plan-review step 3 language bullet;
  - quoted headings having to be map literals, which is why the converge record's
    heading is written in prose.

  Run the listed neighbour tests in every step.
- **Capitals.** "RED", "TDD" and "NOT" would fail `test_prompt_style.py`. The allowlist
  must stay unchanged (AC11).
- **Eval receipt timing.** The fingerprint covers `plugin/`, so the run happens after the
  last change there, including any final-review fix. A `--case` re-run overwrites the
  receipt with a one-case result that is green yet proves nothing. It is never committed:
  restore it with `git checkout -- plugin/evals/last-run.json`.
- **Spend.** The owner accepted up to $12: one full suite of 11 cases plus one re-run.
  The eval cost policy also asks for 5 runs to measure a new case, which does not fit in
  $12. Any run beyond the full suite and one re-run is a question for the owner, not a
  spend.

## End-to-end verification

### Automatic (performed by /pipeline:implement)

The change is skill text, templates, eval fixtures and documents. There is no running
application. The end-to-end check has three parts:

1. `bash scripts/check.sh` is green: validate --strict when `claude` is on PATH, ruff,
   black, and pytest over `plugin/tests` and `tests`.
2. `git diff origin/main -- plugin/tests/test_prompt_style.py plugin/templates/sections.md plugin/.claude-plugin/plugin.json`
   prints nothing (AC11 allowlist, AC1 map, AC10 version).
3. Every AC row of this plan's matrix, except AC9 and AC11, has a red record in its
   fourth column: a read of `## AC → steps matrix` in this PLAN confirms it.

Record the results here when done.

### Manual (performed by the owner)

1. **AC9, after the PR is open, on the owner's explicit command** (Owner decisions): run
   `bash scripts/eval.sh --max-cost-usd 12` (full suite, default model). The agent may run
   it and commit `plugin/evals/last-run.json` on the PR branch once the owner gives the
   command. The receipt must be green, with `cases_total: 11` and a fingerprint that
   matches `plugin/` at the branch head. A red case is first re-run alone with
   `--case <name> --max-cost-usd <remaining budget>` to tell flakiness from a regression
   (every eval call carries `--max-cost-usd`, `docs/DECISIONS.md` 2026-09-22). A regression is fixed on the
   branch, and the full suite runs again for the receipt. A `--case` receipt is never
   committed. Stop and ask before any run beyond one full suite and one re-run, including
   a 5-run measurement from the eval cost policy.

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

**2026-09-24, /pipeline:plan-review (under /pipeline:ship).** Anti-anchoring leads (read
from the SPEC before the plan): template column first; each skill rule pinned by a pytest
run red first; eval cases on the `implement-escalates-on-failing-test` pattern; the nit cap
touching `final-review`, `reviewer` and `ship`; AC9 outside `/pipeline:implement`. The plan
matches all five.

Findings:

- R1 `major`: Approach, converge: "the usual escalation triggers apply to added steps"
  does not say that a step delivering a SPEC AC is not a change of scope. Read literally,
  every `missing` gap is a scope change and escalates, so the pass closes no gap. Fixed: a
  sentence in Approach → "Content of the converge pass", and step 4's
  `test_converge_keeps_the_escalation_triggers` also pins "within the SPEC's scope".
- R2 `major`: step 7, never-red fixture: the existing `tests/test_shipping.py` was
  unspecified. If it asserted a value the spec changes (such as 15000 → 499), the correct
  change would turn the suite red and give the agent a second, legitimate reason to stop,
  so the case would score the setup. Fixed: its assertions are named (5000 → 499,
  30000 → 0), and `test_never_red_a_correct_change_keeps_it_green` runs the full `VERIFY`
  suite.
- R3 `minor`: the compliance perspective's red-record clause would flag every
  three-column matrix of a spec carried out before 0.7.0. Fixed in Approach and step 6: a
  matrix without the fourth column is not a finding.
- R4 `minor`: pointers from the procedure to the two new `implement` sections, if written
  as a backticked `## …` span, fail `test_quoted_headings_are_english_map_literals`. The
  plan warned only about the converge record's heading. Fixed in the constraints list.
- R5 `minor`: step 4: the changed Finish prefix makes `closing_step` raise
  `StopIteration`, not an assertion, so it cannot serve as the red record. Fixed: the step
  says the red record comes from `test_converge.py`.
- R6 `minor`: step 9: `HEADINGS` in `test_readme.py` is order-checked; the insertion point
  is now named (between "Escalation triggers" and "Language contract").
- R7 `minor`: manual E2E: the `--case` re-run lacked `--max-cost-usd`, which the
  2026-09-22 decision requires on every eval call. Fixed.

Checked and found sound (later stages need not repeat):

- coverage: AC1–AC11 each map to steps and a proving test; the matrix matches steps 1–10;
  AC9 is correctly outside `/pipeline:implement` (manual, on the owner's command, per the
  owner decisions); AC11 is guarded by every step's neighbour tests and step 10's full
  check.
- compliance: no decision is broken. The DECISIONS rows for SPEC 010 already exist
  (lines 50–51), so step 10's decisions test is green by design and the roadmap test
  carries the red. Version stays 0.7.0 per SPEC 009's owner decision.
- the pins the plan names exist as described: the loop fence and `**Gate:**` paragraph
  (`test_prompt_audit.py`), 4 `final-review` guardrail bullets, `plan` step 5's language
  tokens (`test_plan_writes_in_the_current_language`), the plan-review step 3 language
  bullet, `CLOSING_STEPS["implement"]` prefix `5. **Finish` in `test_stage_skills.py`,
  the section-map snapshot, and `test_templates_language.py` on the Polish allowlist.
- the words tier, threshold and `size:` do not occur today in skills, agents or
  templates, so `test_no_size_tiers_anywhere` is green before the change, as stated.
- `test_prompt_style.py` allows `SUMMARY`, `METRICS`, `AC`, `SPEC`, `PLAN`; the planned
  wording needs no allowlist change.
- eval fixtures: `NEW_CASES`, `WRONG_BEHAVIOUR`, `STAGE_CASES`, `assert_ready_for_the_skill`
  and `incorrect_paragraph` exist with the signatures the plan uses; the fixture name
  `never_red` does not clash with the existing `free_shipping` fixture; the suite becomes
  11 cases, matching `cases_total: 11`; `scripts/eval.sh` passes `--case` and
  `--max-cost-usd` through `"$@"`. The existing `implement-escalates-on-failing-test`
  fixture plan indeed has no matrix, so the kept-behaviour rule is needed; the two
  final-review graders tolerate extra findings.
- minimality: no new script, no metric key, no change to `workflow_metrics.py`, the
  section map or the orchestrator's statuses. Feasibility: no forward dependencies
  (steps 2 and 4 edit `implement` in order; steps 3, 5 and 6 layer on `plan` step 5 and
  `final-review` step 2 without conflict). No dependency, no migration, flags in the
  Owner summary are true.
- testability: every step has an `Automatic verification:` line with exact test paths.
- language: the PLAN is in English, per `language: en`.

Decision: `plan-approved`. No blocker remains, the two majors were fixable in the plan and
are fixed, and there is no new dependency or data migration.

## Deviations

_(filled in by /pipeline:implement — every deviation from the plan with its rationale)_

## Final review

_(filled in by /pipeline:final-review)_
