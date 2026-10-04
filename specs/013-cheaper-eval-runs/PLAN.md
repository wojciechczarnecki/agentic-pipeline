# PLAN 013 — Cheaper eval runs

## Owner summary

- **Approach:** `scripts/eval_receipt.py` classifies every run as pass, fail or error
  (known infrastructure patterns or no verdict), keeps a verdict per case and merges a new
  run into the receipt when the fingerprint and model match, with a `fail` replaced only
  by a 5/5 measurement. Two new subcommands pick cases: `rerun` (errored and missing
  cases) and `changed` (a path → case mapping over the diff from the merge-base with
  `origin/main`). `scripts/eval.sh` gets `--rerun-errors` and `--changed`, which run the
  picked cases one `--case` call at a time, and it refuses untracked files under
  `plugin/`. `pre-push` reads the receipt from the tagged commit. Nothing under `plugin/`
  changes.
- **Main risks:** the infrastructure patterns are only as good as the messages they match.
  An unknown message falls to `fail`, so a miss makes the gate stricter, never looser.
  In the selective modes `--max-cost-usd` applies to each per-case call, not to the whole
  re-run. Every `pre-push` test now needs the receipt inside a throwaway commit.
- **New dependency:** no.
- **Data migration:** no. The old receipt format is not merged. The next run writes a
  fresh receipt, and `--rerun-errors` refuses an old one with a message.
- **Manual scenarios for the owner:** 1. A real `bash scripts/eval.sh --changed` or
  `--rerun-errors` against the CLI, at the owner's choice and cost. Every automatic test
  stubs `claude`.

## Approach

Read for this plan:

- `specs/013-cheaper-eval-runs/SPEC.md`: read in full.
- `docs/CONVENTIONS.md`: read in full. The eval paragraphs in "Tests" and "Releases"
  change in step 10.
- `docs/DECISIONS.md`: searched for `eval`, `receipt`, `2026-09-20`, `2026-09-22`. Found
  the local-only eval and the `pre-push` receipt gate (2026-09-20) and the five-run policy,
  where a usage-limit abort already counted as "no verdict" (2026-09-22). The table is
  append-only, so the new row goes at the end.
- `docs/ROADMAP.md`: searched for `eval` and `013`. The Stage 7 item already links the spec
  and is ticked in step 10.
- `docs/BACKLOG.md`: searched for `eval` and `receipt`. Found the two in-scope rows
  ("`pre-push` reads the receipt from the working tree" and "`eval.sh`'s clean check
  ignores untracked files"). The two flaky-case rows stay.
- `tests/test_documents.py`: searched for `eval`, `CLAUDE.md`, `roadmap_items`, `section`.
  Found the helpers `read`, `section`, `fenced_blocks` and `roadmap_items`, the pattern
  `test_roadmap_ticks_spec_012`, and `test_conventions_state_the_eval_cost_policy`, whose
  tokens must survive the step 10 edit.
- Read in full, as the files this plan changes: `scripts/eval.sh`,
  `scripts/eval_receipt.py`, `scripts/git-hooks/pre-push`, `tests/test_release_gate.py`,
  `tests/fixtures/eval-result.json`, `scripts/check.sh`, `plugin/evals/last-run.json`.
- The real raw results `plugin/evals/results/2026-09-24T08-40-16-458Z/aggregate-result.json`
  and `…/2026-09-23T14-40-36-930Z/…` (ignored by `plugin/evals/.gitignore`). They give the
  two error shapes: `error: "exit 1: You've hit your session limit · resets …"`, and
  `error: null` with `graders[0].explanation` set to
  `"grader threw: judge call failed: You've hit your session limit · resets …"`. In both
  shapes `score` is 0 and `skippedPaidGraders` is false.
- `git status --porcelain --ignored -- plugin/`. `plugin/evals/results/` and the
  `__pycache__` directories are ignored, so `git status --porcelain` (which leaves ignored
  files out) is a usable clean check for AC16.

Design:

- **One script, new subcommands.** The logic stays in `scripts/eval_receipt.py`, which
  gets the subcommands `write`, `summary`, `rerun` and `changed`. Rejected: a second
  module `scripts/eval_select.py`. `rerun` needs the receipt and verdict rules anyway, and
  one module keeps a single place to test. Tests for the module go into a new
  `tests/test_eval_receipt.py`, which loads it with `importlib.util.spec_from_file_location`
  (`scripts/` is not a package) and also runs it as a subprocess where the command line is
  the contract. `tests/test_release_gate.py` keeps the `eval.sh` and `pre-push` tests.
- **Run verdict** (`run_verdict(run) -> "pass" | "fail" | "error"`), in this order:
  1. a non-null `error` that matches `INFRA_PATTERNS` → `error`; any other non-null
     `error` → `fail`;
  2. `skippedPaidGraders` → `error`;
  3. a grader whose `explanation` starts with `grader threw:` and matches
     `INFRA_PATTERNS` → `error`;
  4. `score >= 1` → `pass`, otherwise `fail`.

  Runs a case planned (`runsPerCase`) but never started count as `error`.
  `INFRA_PATTERNS` is a module-level list of case-insensitive regexes, one per AC1 class:
  session or usage limit (`session limit|usage limit`), rate limit or 429
  (`rate.?limit|\b429\b`), overloaded or 529 (`overloaded|\b529\b`), and API 5xx
  (`api error:?\s*5\d\d|\b5\d\d\b.{0,3}(internal server error|bad gateway|service
  unavailable|gateway timeout)`). A bare 5xx number is not matched, so
  `timeout after 600s` or `500s` stays `fail`.
- **Case verdict** from `passed`, `errors` and `runs`:
  - `pass` when there are no errors and the passes are a majority (the existing
    `majority`);
  - `error` when there is at least one error and the errors could have changed the
    outcome, that is `majority(passed + errors, runs)`;
  - `fail` otherwise.

  A case that has already failed by majority stays `fail`, so a session limit on its last
  run cannot turn a real failure into a re-runnable error. The receipt entry is
  `{"runs": N, "passed": P, "errors": E, "verdict": V}`. `runs` keeps its meaning (planned
  runs), so `pre-push`'s runs check is unchanged.
- **Merge** (`write <raw.json>... <receipt.json> … [--evals-dir DIR]`). The `raw`
  positional takes one or more files, because the selective modes produce one result per
  case. With `--evals-dir`, the suite is the `case.yaml` files under DIR (the `name:` and
  `runs:` keys, read by regex as `pre-push` does, with the default 3 for `runs`). Without
  it, the suite is the cases of the merged receipt, so the existing tests keep working.
  - An existing receipt with the same `plugin_fingerprint` and `model`, and with a
    `verdict` on every case, is the base. Otherwise the base is empty (AC9, and the old
    format).
  - For each case of the new results: a base verdict `fail` is replaced only when the new
    entry has `runs >= 5`, `passed == runs` and `errors == 0`. Any other base (`error`,
    `pass`, missing) is replaced when the new `runs` is at least the `runs` its `case.yaml`
    asks (0 without `--evals-dir`). A kept entry is reported. The `runs` threshold and the
    5/5 rule apply only when merging into a matching base: with an empty base (another
    fingerprint or model, or the old format) every new case is written as it ran, as today
    (AC9), and a short case is left for `pre-push`'s runs check to refuse.
  - `green` is true when every suite case has the verdict `pass`, every receipt case is in
    the suite (when a suite is known), and no input result is `partial`. A partial run
    therefore writes a red receipt, as today (`test_a_partial_result_is_not_green` stays),
    and a later merge clears it. `cases_total` is the number of receipt cases,
    `cases_passed` the number with `pass`, `cost_usd` the base cost plus the new costs,
    and `commit`, `plugin_version` and `ran_at` come from the current run.
- **Re-run selection** (`rerun <receipt> --fingerprint F --evals-dir DIR -- <eval args>`).
  It prints the names of the suite cases whose verdict is `error` or that are missing from
  the receipt, one per line, and exits 0. "Nothing to re-run" goes to stderr with an empty
  stdout and exit 0. It refuses with a message on stderr and exit 1 when there is no
  receipt, when the receipt is in the old format (the message points to the full suite,
  per the SPEC's open question), or when the fingerprint or model differs from the
  current one. The current model comes from the existing `model_override(args, environ)`.
- **Changed-cases mapping** (`changed --evals-dir DIR`). It reads paths from stdin and
  prints the selected cases. `cases_for_paths(paths, cases) -> set[str]`, first matching
  rule per path:
  1. `NO_CASES`: `plugin/README.md`, `plugin/CHANGELOG.md`, `plugin/docs/`,
     `plugin/tests/`, `plugin/evals/last-run.json`, `plugin/skills/idea/`,
     `plugin/skills/plan/`, `plugin/skills/ship/` and `plugin/agents/planner.md` select no
     case.
  2. `plugin/evals/<x>/…` selects case `x` when it is in the suite. A directory that is no
     longer a case (a deleted case) selects nothing, since there is nothing to run.
  3. `PREFIX_RULES` select by prefix: `plugin/skills/<stage>/` → `<stage>-`,
     `plugin/agents/implementer.md` → `implement-`, `plugin/agents/reviewer.md` →
     `final-review-`, `plugin/agents/plan-reviewer.md` → `plan-review-`, and
     `plugin/hooks/` → `guard-`.
  4. Any other path under `plugin/`, including `plugin/bin/`, `plugin/templates/`,
     `plugin/.claude-plugin/` and `plugin/evals/.gitignore`, selects every case.

  `plan` is in `NO_CASES` deliberately: the prefix `plan-` would otherwise pick the
  `plan-review-` cases.
- **`eval.sh`.** It takes its own options out of `"$@"` before passing the rest to the CLI:
  `--rerun-errors` and `--changed`. Together, or with `--case`, it refuses. Both run
  `claude plugin eval … --case <name> --json <raw-i>` once per selected case, because
  `--case` takes one glob and a brace glob is not a documented form (rejected: one call
  with a composed glob). Then one `write` merges every raw file. Without either option the
  full suite runs as today, also through `write --evals-dir plugin/evals`, so a full run
  on an unchanged fingerprint merges too. The clean check becomes
  `git status --porcelain -- plugin/ ":(exclude)$receipt"`. The fingerprint is computed
  before the run, because `rerun` needs it.
- **`pre-push`.** It writes `git show "$tagged:$receipt"` to a `mktemp` file (removed by a
  trap). If that fails, the "no eval receipt" message stays. Every `json.load(open(...))`
  then reads that file instead of the working tree.
- Existing patterns reused: the `commit_with_runs` throwaway-commit technique
  (`git hash-object`/`read-tree`/`update-index`/`write-tree`/`commit-tree` with a
  temporary `GIT_INDEX_FILE`) for the `pre-push` tests, and the `eval.sh` harness of
  `test_eval_sh_passes_the_model_to_the_receipt` (a copy of the repository layout, stubs
  for `claude`, `socat` and `bwrap`). Both are in `tests/test_release_gate.py`.

## AC → steps matrix

| AC | Steps | Proving test | Red before the change |
|----|-------|--------------|-----------------------|
| AC1 | 1 | `tests/test_eval_receipt.py::test_infrastructure_error_is_an_error` (parametrized over each pattern) |  `uv run pytest -q tests/test_eval_receipt.py` (against a stub `run_verdict`) → `AssertionError: assert 'stub' == 'error'` |
| AC2 | 1 | `tests/test_eval_receipt.py::test_grader_threw_on_session_limit_is_an_error` (fixture `tests/fixtures/eval-result-session-limit.json`) |  `uv run pytest -q tests/test_eval_receipt.py` (against a stub `run_verdict`) → `AssertionError: assert 'stub' == 'error'` |
| AC3 | 1 | `tests/test_eval_receipt.py::test_no_verdict_is_an_error` (skipped grader and never-started run) |  `uv run pytest -q tests/test_eval_receipt.py` (against a stub `run_verdict`) → `AssertionError: assert 'stub' == 'error'` |
| AC4 | 1 | `tests/test_eval_receipt.py::test_other_errors_are_failures` (`timeout after 600s`, an unknown message) |  `uv run pytest -q tests/test_eval_receipt.py` (against a stub `run_verdict`) → `AssertionError: assert 'stub' == 'fail'` |
| AC5 | 2, 7 | `tests/test_eval_receipt.py::test_an_errored_case_is_not_passed`, `::test_write_lists_errored_and_failed_cases`, `::test_summary_lists_errored_cases`; `tests/test_release_gate.py::test_eval_sh_rerun_errors_runs_only_errored_and_missing_cases` (closing message) |  `uv run pytest -q tests/test_eval_receipt.py` → `AssertionError: assert 'errored: c' in '\neval.sh: receipt written to … (NOT green)\n'` |
| AC6 | 2 | `tests/test_eval_receipt.py::test_receipt_keeps_a_verdict_per_case` |  `uv run pytest -q tests/test_eval_receipt.py::test_receipt_keeps_a_verdict_per_case` → `AssertionError: assert {'a': {'runs'... 'passed': 2}} == {'a': {'runs'...ict': 'pass'}}` |
| AC7 | 3 | `tests/test_eval_receipt.py::test_a_rerun_of_errored_cases_merges_into_a_green_receipt` |  `uv run pytest -q tests/test_eval_receipt.py` (`write` accepting several files, no merge yet) → `assert 3 == 12` |
| AC8 | 3 | `tests/test_eval_receipt.py::test_a_failed_case_needs_five_of_five`, `::test_a_short_run_does_not_replace_a_case` |  `uv run pytest -q tests/test_eval_receipt.py` (`write` accepting several files, no merge yet) → `AssertionError: assert {'runs': 1, '...dict': 'pass'} == {'runs': 1, '...dict': 'fail'}` |
| AC9 | 3 | `tests/test_eval_receipt.py::test_a_different_fingerprint_or_model_starts_a_new_receipt`, `::test_an_old_format_receipt_is_not_merged` |  `uv run pytest -q tests/test_eval_receipt.py` (`write` accepting several files, no merge yet) → `assert True is False` |
| AC10 | 9 | `tests/test_release_gate.py::test_a_suite_merged_from_several_runs_passes_the_hook` |  `uv run pytest -q tests/test_release_gate.py -k "tagged_commit or merged_from"` (hook still reading the working tree) → `assert result.returncode == 0` (`assert 1 == 0`, stderr `plugin/ changed since the eval ran`) |
| AC11 | 4, 7 | `tests/test_eval_receipt.py::test_rerun_selects_errored_and_missing_cases`, `::test_rerun_refuses_a_different_fingerprint_or_model`, `::test_rerun_has_nothing_to_rerun`; `tests/test_release_gate.py::test_eval_sh_rerun_errors_runs_only_errored_and_missing_cases` |  `uv run pytest -q tests/test_eval_receipt.py -k rerun` (no `rerun` subcommand yet) → `assert 2 == 0`; `uv run pytest -q tests/test_release_gate.py -k eval_sh` (`eval.sh` passing `--rerun-errors` to the CLI) → `assert 1 == 2` (one CLI call instead of two) |
| AC12 | 8 | `tests/test_release_gate.py::test_eval_sh_changed_runs_the_cases_of_the_diff` |  `uv run pytest -q tests/test_release_gate.py -k "changed or whole_suite"` (`--changed` parsed, no selection yet) → `assert '--case init-keeps-manual-edits ' in ('plugin eval plugin/ … --json … --max-cost-usd 2' + ' ')` |
| AC13 | 5 | `tests/test_eval_receipt.py::test_changed_paths_map_to_cases` (one parameter per rule) |  `uv run pytest -q tests/test_eval_receipt.py -k "changed or rule"` (stub `cases_for_paths` returning an empty set) → `AssertionError: assert [] == ['init-keeps-manual-edits']` |
| AC14 | 5 | `tests/test_eval_receipt.py::test_every_case_has_a_rule_of_its_own` |  `uv run pytest -q tests/test_eval_receipt.py -k "changed or rule"` (stub `cases_for_paths` returning an empty set) → `AssertionError` on `assert set(cases) - reachable(cases) == set()` in `test_every_case_has_a_rule_of_its_own` |
| AC15 | 8 | `tests/test_release_gate.py::test_eval_sh_changed_without_origin_main_does_not_run`, `::test_eval_sh_changed_with_no_case_does_not_run` |  `uv run pytest -q tests/test_release_gate.py -k "changed or whole_suite"` (`--changed` parsed, no selection yet) → `assert 0 == 1` (no `origin/main`) and `assert 'no eval case' in ''` |
| AC16 | 6 | `tests/test_release_gate.py::test_eval_sh_refuses_untracked_files_under_plugin` |  `uv run pytest -q tests/test_release_gate.py -k eval_sh` → `assert 0 == 1` (`eval.sh` exited 0 with an untracked `plugin/new-file.md`) |
| AC17 | 9 | `tests/test_release_gate.py::test_the_hook_reads_the_receipt_from_the_tagged_commit` (both directions) |  `uv run pytest -q tests/test_release_gate.py -k "tagged_commit or merged_from"` (hook still reading the working tree) → `assert 'not green' in 'Traceback … KeyError: \'plugin_fingerprint\'\npre-push: plugin/ changed since the eval ran.'` |
| AC18 | 10 | `tests/test_documents.py::test_conventions_describe_errors_and_merging`, `::test_roadmap_ticks_spec_013`, `::test_decisions_record_spec_013`, `::test_backlog_drops_the_delivered_eval_items` |  `uv run pytest -q tests/test_documents.py -k "spec_013 or errors_and_merging or delivered_eval"` → `AssertionError: --rerun-errors`; `assert items[0].startswith("- [x]")`; `assert any("5 of 5" in row …)`; `assert 'reads the receipt from the working tree' not in '# Backlog…'` |
| AC19 | 11 | n/a — a final gate, not a behaviour: `bash scripts/check.sh` and `git diff --quiet origin/main -- plugin/` | |

## Steps

### Group 1 — Receipt verdicts, merging and case selection

- [x] 1. Run classification (AC1–AC4). First add the fixture
      `tests/fixtures/eval-result-session-limit.json`: a trimmed copy of the 2026-09-24T08:40
      raw result with three cases at `runsPerCase: 1`. `final-review-finds-planted-defect`
      passes, `init-without-questions` has `error: null` with the `grader threw: judge
      call failed: You've hit your session limit · resets 12:20pm (Europe/Warsaw)`
      explanation, and `init-writes-the-chosen-language` has
      `error: "exit 1: You've hit your session limit · resets 12:20pm (Europe/Warsaw)"`.
      Keep the top-level keys of `tests/fixtures/eval-result.json`. Then write the tests in
      the new `tests/test_eval_receipt.py`:
      - one `error` parameter per `INFRA_PATTERNS` class (session limit, usage limit, rate
        limit, 429, overloaded, 529, `API Error: 500`, `503 Service Unavailable`);
      - the AC2 shape → `error`;
      - `skippedPaidGraders` → `error`, and a planned run that never started → `error`;
      - `timeout after 600s` and `exit 1: something unknown` → `fail`;
      - `score` 1 → `pass`, `score` 0 → `fail`.

      Run the tests red, then add `INFRA_PATTERNS` and `run_verdict` to
      `scripts/eval_receipt.py` and replace `run_passed` (the receipt still counts
      `run_verdict(run) == "pass"`, so the receipt tests stay green unchanged) — files:
      `scripts/eval_receipt.py`, `tests/test_eval_receipt.py`,
      `tests/fixtures/eval-result-session-limit.json`.
      Automatic verification: `uv run pytest -q tests/test_eval_receipt.py tests/test_release_gate.py`
- [x] 2. Case verdict, receipt shape and messages (AC5, AC6). Tests first:
      - every case entry is `{runs, passed, errors, verdict}`, and `cases_total`, `green`,
        `model`, `plugin_fingerprint`, `plugin_version` and `commit` are still there;
      - a case with one error run and two passes of three → `error`;
      - a case failed by majority plus one error → `fail`;
      - a receipt with an `error` case is not green;
      - `write` prints the errored cases with `bash scripts/eval.sh --rerun-errors` and the
        failed cases with "five-run measurement policy" (`docs/CONVENTIONS.md`);
      - `summary` adds `(<n> error)` to a case line with errors and ends with `errored:`
        and `failed:` lines naming the cases; like `write`, it gives
        `bash scripts/eval.sh --rerun-errors` for the errored cases and names the five-run
        measurement policy for the failed ones (AC5 asks it of both).

      Then implement `case_verdict` and the new entry shape. In
      `tests/test_release_gate.py`, update
      `test_a_run_without_a_grader_verdict_counts_as_failed` and
      `test_runs_that_never_started_count_as_failed` to the new expectation (`errors` 1 or
      2 and the verdict `error`, not a failed run) and rename both (`…_is_an_error`); the
      entry carrying errors exists only from this step. Update the dict assertions in
      `tests/test_release_gate.py` (`test_two_of_three_runs_count_as_passed`,
      `test_one_of_three_runs_counts_as_failed`) to the new entry shape. In
      `test_summary_prints_one_line_per_case` the first three lines stay as they are,
      since the fixture has no errors — files: `scripts/eval_receipt.py`,
      `tests/test_eval_receipt.py`, `tests/test_release_gate.py`.
      Automatic verification: `uv run pytest -q tests/test_eval_receipt.py tests/test_release_gate.py`
- [x] 3. Merging (AC7–AC9). Tests first, with a helper that builds a raw result from
      `{name: [run verdict shapes]}` and a temporary evals dir of `case.yaml` files:
      - receipt A (12 cases: 9 pass, 3 session-limit errors), then a run of those 3 that
        pass → green, `cases_total == 12`, the 9 entries unchanged;
      - a `fail` case re-run 1/1 pass, or 4 of 5, stays `fail`, the output names the
        policy, and the receipt is not green;
      - the same case re-run 5 of 5 → `pass`;
      - a `runs: 3` case re-run with 1 run is kept and reported;
      - a different fingerprint, or a different model (`--model sonnet` after `default`),
        writes a receipt with only the new cases, including a case that ran fewer runs
        than its `case.yaml` asks (as today, AC9);
      - an old-format receipt (cases without `verdict`, like the current
        `plugin/evals/last-run.json`) is not merged;
      - two raw files in one `write` both land;
      - a partial input is not green.

      Then implement `write <raw>... <receipt>` (argparse `nargs="+"` followed by the
      receipt positional), `--evals-dir`, `suite_cases(evals_dir) -> dict[str, int]`
      (name → runs asked) and `merge(base, new, suite)` — files:
      `scripts/eval_receipt.py`, `tests/test_eval_receipt.py`.
      Automatic verification: `uv run pytest -q tests/test_eval_receipt.py tests/test_release_gate.py`
- [x] 4. `rerun` selection (the selection part of AC11). Tests first, through the
      subprocess:
      - errored and missing suite cases are printed and a `fail` case is not;
      - a different fingerprint, or `-- --model sonnet` against a `default` receipt, or
        `ANTHROPIC_MODEL` set, exits 1 with a message;
      - no receipt, and an old-format receipt, exit 1 with a message that names
        `bash scripts/eval.sh`;
      - nothing to re-run → empty stdout, "nothing to re-run" on stderr, exit 0.

      Then implement the subcommand — files: `scripts/eval_receipt.py`,
      `tests/test_eval_receipt.py`.
      Automatic verification: `uv run pytest -q tests/test_eval_receipt.py`
- [x] 5. `changed` mapping (AC13, AC14). Tests first:
      - one parametrized case per rule in the design (own directory; each skill stage;
        each of the three agents; `plugin/hooks/`; `plugin/bin/`, `plugin/templates/`,
        `plugin/.claude-plugin/` and an unlisted path → every case; each `NO_CASES` entry
        → none, including that `plugin/skills/plan/SKILL.md` does not pick a
        `plan-review-` case);
      - the subprocess form (paths on stdin);
      - AC14: for every case in the real `plugin/evals/` there is a path from
        `PREFIX_RULES` whose selection contains it and is not the whole suite. The
        candidate paths come from the real plugin tree, never from the case name:
        `plugin/skills/<dir>/SKILL.md` for each existing directory under `plugin/skills/`,
        the three mapped agent files and `plugin/hooks/hooks.json`. The own-directory rule
        does not count, since it matches every case by construction. A fake case
        `zzz-unknown` in a temporary evals dir fails that check, which proves the test can
        go red (a candidate built from the case name, `plugin/skills/zzz/`, would make the
        test vacuous).

      Then implement `NO_CASES`, `PREFIX_RULES`, `cases_for_paths` and the subcommand —
      files: `scripts/eval_receipt.py`, `tests/test_eval_receipt.py`.
      Automatic verification: `uv run pytest -q tests/test_eval_receipt.py && uv run ruff check scripts tests && uv run black --check scripts tests`

### Group 2 — eval.sh, the release gate and documents

- [x] 6. `eval.sh` refuses untracked files (AC16). First refactor the harness of
      `test_eval_sh_passes_the_model_to_the_receipt` into a helper
      `eval_repo(tmp_path, cases=...)` that builds the repository copy (optionally with
      `plugin/evals/<case>/case.yaml`) and returns `(repo, env)`. Make the stub `claude`
      append each invocation's arguments to `$STUB_LOG`, so a test can assert "no run".
      The existing parametrized test must stay green on the helper. Then write
      `test_eval_sh_refuses_untracked_files_under_plugin`: an untracked
      `plugin/new-file.md` makes `eval.sh` exit 1, the message names uncommitted or
      untracked files, and the log is empty. Change the clean check to
      `git status --porcelain -- plugin/ ":(exclude)$receipt"` — files: `scripts/eval.sh`,
      `tests/test_release_gate.py`.
      Automatic verification: `uv run pytest -q tests/test_release_gate.py -k eval_sh`
- [x] 7. `eval.sh --rerun-errors` (AC11, AC5 closing message). The stub `claude` keeps only
      the case named by `--case` when one is given (a short `python3` filter over
      `$STUB_RESULT`). Write the tests first:
      - with a committed harness repo of three cases and a receipt (same fingerprint,
        `default`) holding one `pass`, one `error` and one `fail` plus one case missing,
        `--rerun-errors` invokes the CLI exactly for the errored and the missing case
        (from the log), merges them, and the output lists the remaining failed case with
        the policy;
      - a receipt with another fingerprint → exit 1 with a message and no run;
      - nothing to re-run → exit 0 and no run;
      - `--rerun-errors --case x` and `--rerun-errors --changed` are refused.

      Then implement the option parsing, the fingerprint before the run, the per-case
      loop (a call that leaves an empty raw file is skipped with a message naming the
      case, which stays as the receipt had it; when no call produced a result, exit 1 with
      today's "no result file" message) and `write` with every non-empty raw file and `--evals-dir plugin/evals` (also for the
      default full run) — files: `scripts/eval.sh`, `tests/test_release_gate.py`.
      Automatic verification: `uv run pytest -q tests/test_release_gate.py -k eval_sh`
- [x] 8. `eval.sh --changed` (AC12, AC15). Tests first, in the harness:
      - with `refs/remotes/origin/main` set by `git update-ref` to the first commit and a
        second commit that touches `plugin/skills/init/…`, `--changed` runs only the
        `init-` case;
      - without `origin/main` → exit 1, a message naming `origin/main`, no run;
      - a diff that touches only `plugin/README.md` → "no case" message, exit 0, no run;
      - without the option the full suite runs (one call without `--case`).

      Then implement it with `git merge-base HEAD origin/main` and
      `git diff --name-only "$base" HEAD -- plugin/ | python3 scripts/eval_receipt.py changed --evals-dir plugin/evals`
      — files: `scripts/eval.sh`, `tests/test_release_gate.py`.
      Automatic verification: `uv run pytest -q tests/test_release_gate.py -k eval_sh`
- [x] 9. `pre-push` reads the receipt from the tagged commit (AC17), and a merged suite
      passes it (AC10). First rework the `receipt` fixture so that it returns a throwaway
      commit of HEAD carrying the receipt (`commit_with(receipt_text, runs=None)`, built
      like `commit_with_runs`). Point every hook test at that commit as `local_ref`, and
      give the fixture's case entries `errors` and `verdict`. Add a commit without the
      receipt for the "no receipt" test. New tests:
      - `test_the_hook_reads_the_receipt_from_the_tagged_commit`: a green working-tree
        receipt with a red one in the tagged commit → refused; a red working tree with a
        green tagged receipt → passes. The fixture still restores the working-tree file;
      - `test_a_suite_merged_from_several_runs_passes_the_hook`: two `write` calls over
        raw results built for the real 12 case names (9 pass and 3 session-limit errors,
        then the 3 passing), with `--fingerprint` of HEAD and `--evals-dir plugin/evals`,
        committed and pushed as `pipeline--v0.3.0` → exit 0.

      Then change `pre-push` to `git show "$tagged:$receipt"` into a temporary file, read
      by every check: the inline `json.load` calls and the runs-check script, whose
      `sys.argv[1]` becomes that file — files:
      `scripts/git-hooks/pre-push`, `tests/test_release_gate.py`.
      Automatic verification: `uv run pytest -q tests/test_release_gate.py`
- [x] 10. Documents (AC18). Tests first in `tests/test_documents.py`:
      - `test_conventions_describe_errors_and_merging`: the "Tests" section names
        `--rerun-errors`, `--changed`, `5 of 5`, `error` and `session limit`, and the
        existing tokens of `test_conventions_state_the_eval_cost_policy` stay;
      - `test_roadmap_ticks_spec_013`: the item with `specs/013-cheaper-eval-runs/SPEC.md`
        is `- [x]`;
      - `test_decisions_record_spec_013`: a row with `SPEC 013` names `5 of 5` and
        `infrastructure`;
      - `test_backlog_drops_the_delivered_eval_items`: neither "reads the receipt from the
        working tree" nor "clean check ignores untracked files" remains.

      Then edit:
      - `docs/CONVENTIONS.md`: in "Tests", error versus fail, the patterns, that errors are
        outside the five-run policy, merging, the 5/5 rule and both options; in
        "Releases", the receipt read from the tagged commit, and that a receipt can be
        assembled from several runs on one fingerprint;
      - `docs/DECISIONS.md`: an appended row dated 2026-10-04 with the merge, error and
        changed-cases rules and the rejected alternatives from the SPEC;
      - `docs/BACKLOG.md`: delete the two rows;
      - `docs/ROADMAP.md`: tick the item;
      - `CLAUDE.md` "Commands": a commented line
        `bash scripts/eval.sh --rerun-errors   # or --changed for development runs` after
        `bash scripts/eval.sh`, keeping the canary line before `claude plugin tag`
        (`test_claude_md_lists_the_canary`).

      Files: `docs/CONVENTIONS.md`, `docs/DECISIONS.md`, `docs/BACKLOG.md`,
      `docs/ROADMAP.md`, `CLAUDE.md`, `tests/test_documents.py`.
      Automatic verification: `uv run pytest -q tests/test_documents.py`
- [x] 11. Final gate (AC19) — files: none.
      Automatic verification: `bash scripts/check.sh && git diff --quiet origin/main -- plugin/ && git status --porcelain -- plugin/ | wc -l` (expect `ALL GREEN`, exit 0 and `0`)

### Converge pass 1 — 2026-10-04

A fresh subagent compared the diff with the SPEC. No `missing`, `partial` or `contradicts` gap. Findings and verdicts:

- `unrequested`, `case_verdict` records a case with an error run that cannot reach a majority as `fail` — rejected: the plan's design asks for it (a majority-failed case stays `fail`), and the SPEC asks only that an errored case is not passed.
- `unrequested`, `eval.sh` refuses `--rerun-errors`, `--changed` and `--case` together — rejected: the plan asks for it and a test covers it.
- AC13 edge: `plugin/evals/results/…` (ignored output) selects no case — rejected: it is not tracked, and a path that is no case directory selects nothing by the plan's rule 2.

Real gaps: 0. No step added, so no second pass.


- The hook tests run the real `pre-push` against the real repository. Throwaway commits
  come from `commit-tree` with a temporary `GIT_INDEX_FILE` and never move a ref. The
  working-tree `plugin/evals/last-run.json` must be restored by the fixture, or step 11's
  `git diff origin/main -- plugin/` goes red.
- `git show <commit>:path` prints nothing and fails for a missing path. Under `set -u`
  without `-e` in `pre-push`, check its exit status explicitly.
- `argparse` with `nargs="+"` followed by a single positional works, but the `--` split
  that already exists in `write` must stay before parsing.
- The 5xx pattern must not match durations (`500s`, `600s`) or counts. Keep the
  `api error` anchor and the status phrases, and test the negatives.
- `eval.sh` runs under `set -euo pipefail`. `git merge-base` failing, or the selection
  printing nothing, must give the AC15 messages and not a bare shell abort. Capture the
  output with `|| { …; exit 1; }`.
- In the selective modes each per-case call gets the user's `--max-cost-usd`. The
  CONVENTIONS text says so, because the ceiling then bounds each call, not the whole
  re-run.
- The CLI flag spelling `--rerun-errors` must not be passed through to
  `claude plugin eval`, which would reject an unknown flag.
- `test_no_domain_references` and `test_english_only` do not cover `scripts/`, but keep
  the messages in English anyway.

## End-to-end verification

### Automatic (performed by /pipeline:implement)

- `bash scripts/check.sh` → `ALL GREEN`.
- `python3 scripts/eval_receipt.py summary plugin/evals/results/2026-09-24T08-40-16-458Z/aggregate-result.json`
  (where the ignored directory exists locally) lists `init-without-questions`,
  `init-writes-the-chosen-language`, `plan-review-approves-polish-owner-decision` and
  `plan-review-escalates-on-dependency` under `errored:`, and
  `implement-converge-finds-missing-ac` under `failed:`. Record the output here.
- `git diff --name-only origin/main -- plugin/` → empty.

Result (2026-10-04): `bash scripts/check.sh` → `ALL GREEN` (2318 passed). The `summary` command on the real 2026-09-24T08:40 result lists `init-without-questions`, `init-writes-the-chosen-language`, `plan-review-approves-polish-owner-decision` and `plan-review-escalates-on-dependency` under `errored:` (with the `--rerun-errors` command) and `implement-converge-finds-missing-ac` under `failed:` (with the five-run measurement policy). `git diff --name-only origin/main -- plugin/` is empty and `git status --porcelain -- plugin/` is empty.

### Manual (performed by the owner)

- Optional, at the owner's cost: on a branch with a skill change, run
  `bash scripts/eval.sh --changed --max-cost-usd 2` and check that only the mapped cases
  run and merge into `plugin/evals/last-run.json`. After a session-limit failure, run
  `bash scripts/eval.sh --rerun-errors`.

## Definition of Done

- [x] all steps ticked
- [x] `bash scripts/check.sh` fully green
- [x] end-to-end verification (automatic) performed, result recorded here
- [x] `docs/ROADMAP.md` updated; `docs/DECISIONS.md`, `docs/CONVENTIONS.md`,
      `docs/BACKLOG.md`, `CLAUDE.md` updated
- [x] spec status: `implemented`

## Owner decisions

_(appended by /pipeline:ship or a stage on escalation: date, stage, question, decision)_

## Review log

### 2026-10-04 — plan review

Findings (severity counted before the fixes):

1. `major` — AC9: the merge design applied the `case.yaml` runs threshold to every case
   whose base is missing, and with an empty base (another fingerprint or model) every case
   is missing, so a `--runs 1` run of a `runs: 3` case would have written a receipt without
   that case instead of a new receipt with its own cases "as today". Fixed: the threshold
   and the 5/5 rule apply only when merging into a matching base; step 3 tests a short
   case on a new fingerprint.
2. `major` — AC14: the `plugin/skills/<stage>/` rule is generic, so a test that builds a
   candidate path from the case name (`plugin/skills/zzz/`) selects any case and can never
   go red. Fixed: step 5 takes candidate paths from the real plugin tree only and excludes
   the own-directory rule.
3. `major` — AC5 asks the summary and the closing message both to give the re-run command
   for errored cases and the five-run policy for failed ones; step 2 required that only of
   `write`. Fixed: the `summary` test asks for both.
4. `minor` — step 1 renamed and re-asserted two receipt tests as `error`, but the entry
   that carries errors arrives in step 2. Fixed: moved to step 2; step 1 keeps the receipt
   counting `run_verdict == "pass"`.
5. `minor` — step 7 did not say what happens when one per-case call leaves no raw file
   (today's single-call check would abort the whole merge). Fixed: skip with a message,
   exit 1 only when no call produced a result.
6. `minor` — step 9 said every `json.load(open(...))` reads the temporary file, but the
   runs check is a heredoc script that takes the receipt path as `sys.argv[1]`. Fixed:
   named explicitly.

Checked and found correct:

- Coverage: AC1–AC19 each have steps and a named proving test; the matrix matches the
  steps, and the fourth column is present (AC19 `n/a` with a reason).
- Classification order against the real 2026-09-24T08:40 raw result: both error shapes
  have `score` 0 and `skippedPaidGraders` false, `init-without-questions` has `error: null`
  with a `grader threw:` session-limit explanation; the E2E expectation (four errored, one
  failed among 11 cases) matches that file. The 5xx pattern is anchored so `600s` stays
  `fail`.
- Case verdict: a case with any error is never `pass` (AC5); keeping a majority-failed case
  `fail` despite an error run is stricter than the SPEC, not looser, and consistent with
  the owner decision that in doubt the gate refuses.
- Decisions: 2026-09-20 (local eval, `pre-push` gate on contents, not shas) and 2026-09-22
  (five-run policy, usage-limit abort as "no verdict") are kept; the new row is appended.
  No plugin change, no version bump (AC19, roadmap condition).
- Feasibility: `--case` takes one glob, so the per-case loop is the right call; `runs`
  keeps its meaning, so `pre-push`'s runs and case-count checks work unchanged on merged
  receipts; the fingerprint excludes the receipt, so committing the receipt or a
  throwaway commit carrying it keeps the fingerprint of HEAD (AC10 test). Clean check by
  `git status --porcelain` leaves the ignored `plugin/evals/results/` out.
- Mapping: `plan` in `NO_CASES` before the prefix rules keeps `plugin/skills/plan/` from
  picking `plan-review-` cases; skills on disk are `final-review`, `idea`, `implement`,
  `init`, `plan`, `plan-review`, `ship`, and every current case prefix maps to one of them
  or to `plugin/hooks/`.
- Groups: two groups; Group 1 leaves `write` backward compatible with today's `eval.sh`
  call and the hook, so no work is left half done at the boundary.
- Test-first: every behaviour step writes its tests before the change; step 6 refactors
  the harness first and keeps the existing parametrized test green.
- Owner summary: no new dependency and no data migration, consistent with the SPEC's owner
  decisions; the old receipt format is refused by `--rerun-errors` and replaced by the next
  run (the SPEC's open question, resolved within the options it allows).
- E2E: automatic part runs without a model (stubbed `claude`); the only manual scenario is
  a real paid run, which cannot be automated without cost.
- Language: English throughout, as `language: "en"` asks.

The plan is ready: every AC has a proving test, the three majors were fixable and are
fixed in place, and no escalation trigger (dependency, migration, SPEC gap) applies.

## Chunk notes

_(filled in by /pipeline:implement in chunk mode — one entry per chunk that ends at a group boundary)_

## Deviations

- Minor: the stub `claude` of `tests/test_release_gate.py` filters by `--case` and logs its arguments already in step 6 (the plan has it in step 7), because the harness helper is built once.
- Minor: `summary` prints the `errored:`/`failed:` lines after the `cost` line, not before it, so the existing `test_summary_prints_one_line_per_case` (cost on the fourth line) stays unchanged.
- Minor: a merge reads `cost_usd` of the base with a default of 0, so a base without that key does not crash (found by the step 7 tests).

## Final review

_(filled in by /pipeline:final-review)_
