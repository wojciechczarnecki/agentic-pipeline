# PLAN 015 — Bootstrapping and the guard

## Owner summary

- **Approach:** Three parts. The guard comes first: interpreter code (a heredoc body, a
  here-string, or a `-c`/`-e` argument) that names a guardrail file is refused, every
  refused compound call suggests separate calls, and the once-per-session check adds an
  Alembic notice. The `init` templates come next. CI and Dependabot templates gain
  `<layer>`/`<dir>` placeholders and marked lines for the root and subdirectory forms.
  New per-stack placeholder jobs are added, the repository settings ship as JSON, and the
  settings template gets its `ask`/`deny` rules. The ADR template is added. Then the `init`
  skill, `NEW-PROJECT.md` and the eval case `init-subdirectory-project`. Release 0.10.0
  closes, with the new case measured on 5 runs.
- **Main risks:** Heredoc bodies are matched to the command that reads them by renaming
  the delimiters. A mistake here could refuse ordinary calls, such as a commit message in
  `"$(cat <<'EOF' … EOF)"` that names `.claude/workflow.json`, so regression tests pin
  those cases. `init` is skill prose: whether it fills `backend/` into all six places is
  measured only by the eval case. The case costs money, and the budget is capped at $8.
  `security.yml` is not in the six places of AC2, so it still runs at the root of a
  subdirectory project and stays red without a lock file. It is not fixed here; step 11
  records it in `docs/BACKLOG.md`.
- **New dependency:** no
- **Data migration:** no
- **Manual scenarios for the owner:** 1. The canary (AC22): `/pipeline:init` on the
  working-tree plugin in a fresh repository with only `backend/pyproject.toml`, then the
  first push, a green CI job `backend`, and the ruleset applied from
  `.github/repository/ruleset.json`.

## Approach

What the plan rests on:

- `specs/015-bootstrapping-and-guard/SPEC.md`: read in full, including `## Owner decisions`
  (12 binding decisions).
- `docs/CONVENTIONS.md`: read in full. The binding rules: standard library only in
  `plugin/bin`; the guard is tested as a subprocess and through `guard.evaluate`; tests
  check mechanisms and identifiers, not prose; `*.en.md`/`*.pl.md` templates are twins; a
  new eval case is measured with 5 runs on the default model (5/5 → `runs: 1`, 4/5 →
  `runs: 3`), every call carries `--max-cost-usd`, and the case names its wrong behaviour.
  A minor release needs the receipt and the canary, and both are the owner's.
- `docs/ROADMAP.md`: searched for "0.10.0". The Stage 10 item (lines 312–339) is this
  spec, minus the cuts of Owner decisions 6 and 7.
- `docs/DECISIONS.md`: searched for "interpreter", "write scope", "ci-placeholder",
  "ruleset" and "gh api --input". The 2026-09-17 row is the model for the ruleset
  template. The 2026-09-22 `gh api` writes row is why the owner, not `init`, applies the
  repository files. The last rows (2026-10-05) show the row format.
- `docs/BACKLOG.md`: searched for "interpreter" and "CI generator". Line 35 (Guard P3) is
  the item AC20 annotates. Line 41 (Init P3) stays.
- `plugin/skills/init/SKILL.md`, `plugin/templates/github/**`,
  `plugin/templates/settings.json`, `plugin/templates/pre-push`,
  `plugin/templates/workflow.example.json` and `plugin/docs/NEW-PROJECT.md`: read in full.
- `plugin/bin/guard.py`: read in full (1842 lines).
- `plugin/bin/workflow_config.py`: searched for `defaults`, `Config` and `format_command`.
  `migrations` has no default, so `config.get("migrations")` is `None` when the section is
  missing. `format[].match` is an fnmatch on the path relative to the root, and `*` spans
  slashes.
- `plugin/docs/GUARD.md`: searched for "interpreter", "Known limits", "heredoc" and
  "whole call". This found lines 21, 70, 81 and 234–238.
- `plugin/README.md`: searched for "init", "hosts", "migrations" and "Command guard"
  (lines 51, 63 and 96–123).
- `plugin/templates/CLAUDE.en.md` and `plugin/templates/docs/CONVENTIONS.en.md`: searched
  for "verif", "TODO" and "command". The fill points are the `## Commands` block
  (`bash scripts/verify.sh` under a TODO comment) and the "Full verification … TODO
  (`verify.command`)" line.
- Tests: `plugin/tests/test_init_templates.py` and `test_init_skill.py` read in full;
  `test_eval_cases.py` read in full up to the final-review tests;
  `test_guard.py` searched for "parts passed" (lines 296–335);
  `test_guard_read_rule.py` read up to the `Setup` helpers (lines 1–80);
  `test_no_domain_references.py`, `test_readme.py` (changelog pins) and
  `test_release_0_9_0.py` read in part; `tests/test_spec_metrics.py` read in full (the
  repository's 0.9.0 `--check` lints this PLAN: a matrix row per AC and a `Pass when:` line
  per manual scenario).
- Earlier plans: `specs/006-language-made-explicit/PLAN.md` steps 9–10 are the pattern for
  measuring a new `init` eval case, with a ledger, smoke runs and a budget.
- GitHub (read only): `gh api repos/{owner}/{repo}/rulesets/23598031` and
  `gh api repos/{owner}/{repo}` show this repository's own ruleset and merge settings. They
  are the model for the two JSON templates.

### Guard (AC16–AC19)

- **Compound suggestion (AC19).** `Analyzer.run` builds the refusal at `guard.py:668–676`.
  When no part passed, the suffix is empty today. Change: when one or more parts passed,
  the text stays as it is; when none passed, add `; send the commands as separate calls`.
  The word "passed" stays out of it, as `test_compound_refusal_without_a_passing_part`
  pins.
- **Interpreter code (AC16, AC17).** I considered three variants:
  1. Scan the whole call for an interpreter and a guardrail path. Rejected: `cat <<EOF >
     notes.md` naming the file next to an unrelated `python3 -c` would be refused, which
     AC17 forbids.
  2. Attribute heredoc bodies by line number. Rejected: `tokenize` joins lines with ` ; `,
     so the line-to-segment mapping is lost.
  3. **Chosen:** make each body traceable to its command. `ShellState.heredocs_opened_by`
     also returns where the delimiter word starts and ends. `strip_heredocs` replaces that
     word in the kept line with an indexed marker that cannot clash with a real word, such
     as `__pipeline_heredoc_<n>__`. It keeps the quote and the `-` as they were, so
     expansion and tab stripping do not change, and it returns the bodies in order (every
     body, quoted or not). This is why it was chosen: the marker survives `tokenize`, so
     `segment` sees `<<` followed by its own marker.

  `Analyzer` holds the bodies of the text its `run` is checking: an attribute set in `run`
  and restored when `run` returns, because `eval` re-enters `run` on the same instance.
  Nested analyzers (`$(…)`, `bash -c`) call `strip_heredocs` on their own text, so they
  have their own bodies.

  In `segment`, after `unwrap` (so `env`, `uv run`, `timeout`, `xargs` and `npx` are
  covered), a new `check_interpreter_code(program, tokens)` runs when the program is an
  interpreter. The interpreters are `python`, `python3` and `python3.N`, which match
  `^python(\d+(\.\d+)?)?$`, plus `node`, `perl` and `ruby`. The code it collects is:
  - the bodies whose marker follows a `<<`/`<<-` token in the segment's raw tokens;
  - the word after a `<<<` token;
  - the argument after `-c` (Python), or after `-e`, `-E` or `--eval` (Perl, Ruby, Node),
    and after `-p`/`--print` (Node, which evaluates its argument like `-e`), for each
    occurrence.

  Two details found at review. `tokenize` turns `<<-'EOF'` into `<<` and `-<marker>` (the
  quotes go, the `-` stays), so the marker is looked up in the word after `<<` by a
  search, not by equality. The code is matched both as written and after
  `expand_variables(code, env)`, because the shell expands an unquoted heredoc body and a
  double-quoted `-c` argument, so `$CLAUDE_PLUGIN_ROOT/…` names the plugin directory.

  The code is refused when it matches any of these patterns, all built in `Rules`:
  - `rules.protected_file` (`.claude/settings*.json`, `.claude/workflow.json`, and the
    in-project plugin directory);
  - every guarded root as an absolute path, and its `~/…` spelling when it lies under the
    home directory;
  - the install-state file names in `INSTALL_STATE_FILES`.

  The refusal is `interpreter code names a guardrail file — ` + `GUARDRAIL_FILES`, which
  already says "change only through Edit/Write with the owner's approval". The heredoc of
  a non-interpreter is never collected, so AC17 holds by construction.
- **Alembic notice (AC18).** A new function, `migrations_notice(session_id, config)`,
  follows the fail-open pattern of `read_rule_notice` (`guard.py:568–588`). When
  `config.found` and `config.get("migrations")` is `None`, it looks for `alembic.ini` at
  `config.root` and in its direct subdirectories, sorted. It skips hidden directories and
  `node_modules`. On the first hit in the session (marker `"alembic"` through
  `first_in_session`) it returns a notice. The notice names the relative path and the
  section to add: `"migrations": {"command": "alembic", "localHosts": [...]}` in
  `.claude/workflow.json`. In `main()`, `notice` becomes the notices joined by a newline,
  and it rides the same `systemMessage`/`additionalContext` JSON and the same
  stderr-on-refusal path. The once-per-session marker is set only when the notice is
  returned. This is the same order as `read_rule_notice`, so a project without
  `alembic.ini` never creates the marker.

### `init` (AC1–AC15)

- **Layer placeholders in templates.** `ci-python.yml`, `ci-node.yml` and the new
  `ci-python-placeholder.yml`/`ci-node-placeholder.yml` name their job `<layer>`. Lines
  that only one form needs end in a marker comment: `# subdirectory layer` or
  `# root layer`. Rendering is mechanical and the skill spells it out:
  - for a root layer, delete the lines ending `# subdirectory layer`, strip the
    ` # root layer` markers and replace `<layer>` with the stack name;
  - for a subdirectory layer, delete the `# root layer` lines, strip the
    ` # subdirectory layer` markers and replace `<layer>` and `<dir>` with the directory.

  The marked lines are `defaults:` / `run:` / `working-directory: <dir>` on the job, and
  `with:` / `working-directory: <dir>` on `astral-sh/setup-uv`. For Node, there is one
  `cache-dependency-path: package-lock.json  # root layer` line and one
  `cache-dependency-path: <dir>/package-lock.json  # subdirectory layer` line. A root
  layer renders to today's form (AC2's last sentence). A test re-implements the two
  renderings in Python and checks both outputs, so a template edit that breaks a form is
  caught without a model. The alternative was to keep the templates as they are and
  describe the subdirectory edits in prose, as the comment does today. It was rejected:
  that is exactly what failed at the consumer.
- **Placeholder jobs (AC4).** A placeholder job is `actions/checkout` plus one
  `run: echo …` step that passes, with the real steps of the stack's template kept as
  comments. It has a checkout because a subdirectory layer's
  `defaults.run.working-directory` must exist when the step runs: without the checkout,
  the job fails on a missing directory. A test checks that every real step of
  `ci-python.yml`/`ci-node.yml` appears commented in its placeholder, so the two cannot
  drift. `ci-placeholder.yml` (unknown stack, job `verify`) stays for an unknown stack.
- **Real job or placeholder (AC4), in the skill.** The real job is written only when two
  things hold. The manifest declares the lint and test tools: for Python, `ruff` and
  `pytest` in `pyproject.toml`, and the `black` step stays only when `black` is declared;
  for Node, `lint` and a test script in `scripts`, and the build step stays only with a
  `build` script. And the layer has a test file: `test_*.py`/`*_test.py`, or
  `*.test.*`/`*.spec.*`, outside `.venv` and `node_modules`. Otherwise the placeholder is
  written, and its job appears as a `TODO:` on the closing list.
- **Layer names (AC1).** A root manifest gives the stack name (`python`, `node`). A
  subdirectory gives the directory name. The SPEC does not cover one directory holding
  both manifests, so the plan names those layers `<dir>-python` and `<dir>-node`, which
  keeps job names unique. This is a naming detail inside AC1, not a scope change.
- **Dependabot (AC2).** The `uv` and `npm` entries in the template become
  `directory: /<dir>`, with one entry per layer. A root layer renders `<dir>` to nothing,
  which gives `/`. `github-actions` stays `directory: /`.
- **Repository settings (AC6, AC7).** There are two new templates:
  - `plugin/templates/github/repository/ruleset.json`: name `main`, target `branch`,
    enforcement `active`, `~DEFAULT_BRANCH`, and the rules `deletion`,
    `non_fast_forward`, `pull_request` and `required_status_checks`. `pull_request` has
    `allowed_merge_methods: ["squash"]`, review count 0 and the four other required
    booleans set to `false`. `required_status_checks` has
    `[{"context": "<job>"}]` and `strict_required_status_checks_policy: false`.
  - `plugin/templates/github/repository/settings.json`: `allow_squash_merge: true`, merge
    commits and rebase off, `squash_merge_commit_title: "PR_TITLE"`,
    `squash_merge_commit_message: "PR_BODY"`, and `delete_branch_on_merge` and
    `allow_update_branch` set to `true`.

  `init` copies both into `.github/repository/`. It replaces the single `<job>` entry with
  one entry per CI job it wrote, and it never overwrites an existing file there.
- **Other `init` points.**
  - `settings.json` template (AC9): new `ask` and `deny` rules.
  - Stack `allow` rules (AC10): added by the skill, not the template, because they depend
    on what the repository holds.
  - `<gitHooksDir>` (AC12): the skill substitutes it while copying, before the hook
    exists: `sed 's|<gitHooksDir>|<dir>|' <template> > <gitHooksDir>/pre-push`, then
    `chmod +x`. It never runs `sed -i` on the copied hook: the guard refuses a shell
    change to an existing hook under `gitHooksDir` ("an existing git hook changes only
    through Edit/Write"; checked at review on `guard.evaluate`), so a copy-then-`sed -i`
    order fails. An existing hook on a re-run is left alone (step 5 of the skill).
  - `.gitignore` (AC13): append-only through the shell. The skill gives the check
    (`grep -qxF` per line, and a newline first when the file does not end in one).
  - Closing list: the `hosts` warning (AC11), the README and licence TODOs (AC14) and how
    to copy the ADR template (AC15).
  - AC2 consistency: the skill fills the `## Commands` block of `CLAUDE.md` and the
    "Full verification" line of `docs/CONVENTIONS.md` with the same string as
    `verify.command`. The `format[]` entries are `{"match": "<dir>/*.py", "command":
    "uv run --project <dir> black -q {file}"}` and the same for `ruff check --fix`, as in
    `workflow.example.json`.

  The document templates stay as they are, so the twin tests do not churn.
- **ADR template (AC15):** `plugin/templates/docs/adr/ADR.en.md` and `ADR.pl.md`, twins
  (Polish is allowed in `*.pl.md`, `test_english_only.py`).

### Patterns to reuse

- `plugin/tests/test_guard_read_rule.py::Setup` (`HOME`, `CLAUDE_CONFIG_DIR`, session id,
  subprocess run) for the Alembic notice tests. `notice_of()` parses the JSON.
- `plugin/tests/test_guard.py`: `evaluate`, the `on_feature` fixture and `make_repo`/`WORKFLOW`
  for the interpreter and compound tests. `test_guard_own_files.py` has the fixtures that set
  `CLAUDE_PLUGIN_ROOT` for the plugin-directory cases. Take them from there and do not
  re-invent them.
- `plugin/tests/test_eval_cases.py`: `NEW_CASES`, `WRONG_BEHAVIOUR` and `scaffold()` for
  the new case.
- `plugin/tests/test_release_0_9_0.py` is the shape of the 0.10.0 release test.
  `tests/test_documents.py` has the per-spec DECISIONS row tests (SPEC 014 at line 648).

## AC → steps matrix

| AC | Steps | Proving test | Red before the change |
|----|-------|--------------|-----------------------|
| AC1 | 8, 10 | `plugin/tests/test_init_skill.py::test_layers_are_detected_at_depth_one`; eval `init-subdirectory-project` (step 12) | |
| AC2 | 5, 6, 8, 10 | `plugin/tests/test_init_layers.py::test_ci_renders_a_subdirectory_layer`, `::test_ci_renders_a_root_layer_as_today`, `::test_dependabot_renders_the_layer_directory`; `test_init_skill.py::test_verify_and_format_follow_the_layer_directory`; eval `init-subdirectory-project` | `uv run pytest -q plugin/tests/test_init_layers.py` → `assert "    defaults:\n      run:\n        working-directory: backend\n" in python` (CI part, step 5; Dependabot and skill parts follow in steps 6 and 8); `uv run pytest -q plugin/tests/test_init_layers.py -k dependabot` → `assert directory_of(layer, "uv") == "/backend"` (Dependabot part, step 6) |
| AC3 | 10, 12 | `plugin/tests/test_eval_cases.py::test_the_subdirectory_fixture_has_only_a_backend_manifest`, `::test_criteria_name_the_wrong_behaviour[init-subdirectory-project]`; eval measurement ledger (step 12) | |
| AC4 | 5, 8 | `plugin/tests/test_init_layers.py::test_placeholder_jobs_pass_and_list_the_real_steps`; `test_init_skill.py::test_the_real_job_needs_tools_and_a_test_file` | `uv run pytest -q plugin/tests/test_init_layers.py` → `assert len(runs) == 1 and runs[0].startswith("echo"), runs` (placeholder stubs added first) |
| AC5 | 5 | `plugin/tests/test_init_layers.py::test_every_ci_template_names_the_required_check` | `uv run pytest -q plugin/tests/test_init_layers.py` → `assert any("required check" in line and "ruleset" in line for line in comments), path.name` |
| AC6 | 6 | `plugin/tests/test_init_layers.py::test_the_ruleset_template`, `::test_the_repository_settings_template` |  `uv run pytest -q plugin/tests/test_init_layers.py -k 'ruleset or repository_settings'` → `KeyError: 'target'` and `assert {} == {'allow_squash_merge': …}` (stub files `{}` first) |
| AC7 | 8 | `plugin/tests/test_init_skill.py::test_init_copies_the_repository_settings` (GENERATED entries + idempotence wording) | |
| AC8 | 9 | `plugin/tests/test_new_project_doc.py::test_the_first_push_comes_before_the_hook`, `::test_the_scaffold_through_a_pr_path`, `::test_the_repository_settings_commands`, `::test_the_required_check_appears_after_the_first_run` | |
| AC9 | 7 | `plugin/tests/test_init_templates.py::test_settings_template_protects_the_guardrail_files` (rewritten), `::test_settings_template_denies_detaching_the_plugin` |  `uv run pytest -q plugin/tests/test_init_templates.py -k settings_template` → `assert 'Edit(**/.claude/workflow.json)' in ask` and `assert 'Bash(claude plugin disable*)' in deny` |
| AC10 | 8 | `plugin/tests/test_init_skill.py::test_allow_rules_follow_the_seen_stack` | |
| AC11 | 8 | `plugin/tests/test_init_skill.py::test_the_closing_warns_about_empty_hosts` | |
| AC12 | 8, 10 | `plugin/tests/test_init_skill.py::test_the_hooks_dir_is_substituted_in_pre_push`; eval criterion | |
| AC13 | 8 | `plugin/tests/test_init_skill.py::test_gitignore_is_append_only` (write scope + entries) | |
| AC14 | 8 | `plugin/tests/test_init_skill.py::test_readme_and_licence_are_closing_todos` | |
| AC15 | 7, 8, 9 | `plugin/tests/test_init_templates.py::test_the_adr_template_has_twins`; `test_init_skill.py::test_the_adr_template_is_offered_not_copied`; `test_new_project_doc.py::test_the_adr_template_is_described` |; `uv run pytest -q plugin/tests/test_init_templates.py -k adr` → `FileNotFoundError` on `ADR.en.md` (template part; a missing file is the red here, there is no symbol to stub); skill and `NEW-PROJECT.md` parts follow in steps 8 and 9 |
| AC16 | 2 | `plugin/tests/test_guard_interpreters.py::test_interpreter_code_naming_a_guardrail_file_is_refused` (parametrised: heredoc, here-string, `-c`, `-e`, `-E`, wrappers, plugin root, install state) `uv run pytest -q plugin/tests/test_guard_interpreters.py` → `assert reason is not None, command` (24 refused cases red) |
| AC17 | 2, 4 | `plugin/tests/test_guard_interpreters.py::test_interpreter_code_without_a_guardrail_path_passes`, `::test_a_heredoc_to_a_non_interpreter_keeps_todays_rules`, `::test_guard_doc_narrows_the_interpreter_limit` `uv run pytest -q plugin/tests/test_guard_interpreters.py -k guard_doc` → `assert "names a guardrail" in text` (doc test, red before the GUARD.md edit); the other AC17 tests are regression pins, `n/a — kept behaviour` |
| AC18 | 3, 4 | `plugin/tests/test_guard_alembic_notice.py` (root, subdirectory, once per session, never blocks, silent with `migrations`, silent without `workflow.json`, silent at depth 2) `uv run pytest -q plugin/tests/test_guard_alembic_notice.py` → `assert NOTICE in notice["systemMessage"]` (5 notice cases red; the silent cases are regression pins) |
| AC19 | 1 | `plugin/tests/test_guard.py::test_a_chained_uv_call_with_a_refused_part_suggests_separate_calls`, `::test_a_call_with_every_part_refused_suggests_separate_calls` | `uv run pytest -q plugin/tests/test_guard.py -k separate_calls` → `assert "separate calls" in reason` (only `::test_a_call_with_every_part_refused_suggests_separate_calls`; the chained `uv` test is a regression pin, green today) |
| AC20 | 11 | `plugin/tests/test_release_0_10_0.py`; `tests/test_documents.py::test_spec_015_decisions_rows`, `::test_spec_015_roadmap_and_backlog` | |
| AC21 | 11, 12 | `bash scripts/check.sh` | n/a — the gate over every other test |
| AC22 | — | manual (owner), End-to-end → Manual 1 | manual |

## Steps

### Group 1 — Guard

- [x] 1. **The compound suggestion (AC19).** Files: `plugin/bin/guard.py`,
      `plugin/tests/test_guard.py`.
      Tests first. Only the second test is the proving test and must be seen red; the
      first is a regression pin the SPEC asks for, and it is green before the change,
      because the some-parts-passed suffix already says "run them as a separate call"
      (checked at review on `guard.evaluate`). A green first test is expected and is not
      the "proving test green before the change" escalation.
      - `test_a_chained_uv_call_with_a_refused_part_suggests_separate_calls` (regression
        pin): `uv lock && uv sync && gh pr merge 1`. The reason names
        `` `gh pr merge 1` `` and contains "separate call".
      - `test_a_call_with_every_part_refused_suggests_separate_calls` (proving, red today):
        `gh pr merge 1 && sudo ls`. The reason contains "separate calls" and has no
        "passed".

      Then change the suffix in `Analyzer.run` (Approach → Guard). The existing tests at
      lines 296–335 stay green unchanged.
      Automatic verification: `uv run pytest -q plugin/tests/test_guard.py`

- [x] 2. **Interpreter code naming a guardrail file (AC16, AC17).** Files:
      `plugin/bin/guard.py`, `plugin/tests/test_guard_interpreters.py` (new).
      Tests first, then run them red.

      Refused cases, each with a reason that contains `Edit/Write`:
      - `python3 - <<'EOF'` with a body that reads `.claude/workflow.json`;
      - `node <<EOF` with a body naming `.claude/settings.local.json`;
      - `python3 -c "open('.claude/workflow.json', 'w')"`;
      - `perl -e`, `perl -E`, `ruby -e` and `node -e`/`--eval`/`-p`/`--print` naming
        `.claude/settings.json`;
      - an unquoted heredoc body to `python3` that names `$CLAUDE_PLUGIN_ROOT/hooks/x`,
        with `CLAUDE_PLUGIN_ROOT` set in the test env;
      - `python3 <<< "…workflow.json…"`;
      - `uv run python -c …`, `env python3 -c …` and `timeout 5 python3 -c …`;
      - `bash -c "python3 -c '…workflow.json…'"`;
      - code naming `$CLAUDE_PLUGIN_ROOT`'s absolute path, its `~/` spelling, and
        `installed_plugins.json`;
      - the same heredoc in the second part of a compound call, which is refused as a
        compound.

      Allowed cases (regression pins, green before the change; only the refused cases
      above must be seen red):
      - `python3 - <<'EOF'` printing 1;
      - `python3 -c "print(1)"`;
      - `cat <<EOF > notes.md` whose body names `.claude/workflow.json`;
      - `git commit -m "$(cat <<'EOF' … .claude/workflow.json … EOF\n)"`;
      - `cat <<EOF > a.md` (body naming the file) followed by `python3 - <<EOF` (body
        `print(1)`) in one call. This is the attribution check.

      Then implement it (Approach → Guard, variant 3): `heredocs_opened_by` returns the
      spans, `strip_heredocs` renames the delimiters and returns the bodies, `Analyzer`
      gets a bodies attribute, and `check_interpreter_code` runs from `segment` after
      `unwrap`. The rest of the suite must stay green, because every guard test
      exercises `strip_heredocs`.
      Automatic verification: `uv run pytest -q plugin/tests/test_guard_interpreters.py plugin/tests/test_guard.py plugin/tests/test_guard_own_files.py && uv run pytest -q plugin/tests`

- [x] 3. **Alembic notice (AC18).** Files: `plugin/bin/guard.py`,
      `plugin/tests/test_guard_alembic_notice.py` (new).
      Tests first, built on `test_guard_read_rule.Setup`, with a covering `Read` rule
      written so that the read-rule notice stays out of the way, then run them red. The
      silent cases (second call, `migrations` present, depth 2, no `workflow.json`) are
      regression pins and pass before the change; the notice cases must be seen red:
      - root `alembic.ini` with no `migrations`: the notice is in `systemMessage` and
        `additionalContext`, names `alembic.ini` and `migrations`, and the exit code is 0;
      - a second call in the same session is silent;
      - `backend/alembic.ini`: the notice names `backend/alembic.ini`;
      - a `migrations` section in the workflow file: silent;
      - `a/b/alembic.ini` (depth 2): silent;
      - a repository without `.claude/workflow.json`: no Alembic notice;
      - a refused call: the notice rides on stderr after the reason;
      - with the `Read` rule missing too: both notices appear in one `systemMessage`.

      Then implement `migrations_notice` and the joined notice in `main()`.
      Automatic verification: `uv run pytest -q plugin/tests/test_guard_alembic_notice.py plugin/tests/test_guard_read_rule.py`

- [x] 4. **Guard documentation (AC17, AC18, AC19).** Files: `plugin/docs/GUARD.md`,
      `plugin/README.md` (`### Command guard`), and
      `plugin/tests/test_guard_interpreters.py` (doc tests).
      Write the doc tests first, then run them red:
      - GUARD.md has a rule bullet naming the interpreters, `-c`, `-e`, heredoc and
        here-string;
      - the "Scripts, interpreters and shell functions" known limit says that code naming
        a guardrail path is refused, and that a path built at run time or a script file is
        not;
      - "How the refusal reads" mentions the separate-calls suggestion when nothing passed;
      - the README guard paragraph names the Alembic notice and `migrations`.

      Then edit the docs. Line 21 of GUARD.md ("call an interpreter") is narrowed the same
      way, and so are the interpreter mentions at lines 218 and 228 (the release-tag and
      evasion notes), so no passage still says every interpreter call goes unseen.
      Automatic verification: `uv run pytest -q plugin/tests/test_guard_interpreters.py plugin/tests/test_readme.py`

### Group 2 — `init`: templates, skill, documentation, eval case

- [x] 5. **CI templates (AC2 CI part, AC4, AC5).** Files:
      `plugin/templates/github/workflows/ci-python.yml`, `ci-node.yml`,
      `ci-placeholder.yml`, `ci-python-placeholder.yml` (new), `ci-node-placeholder.yml`
      (new), `plugin/tests/test_init_layers.py` (new),
      `plugin/tests/test_init_templates.py`.
      Tests first, then run them red:
      - `test_ci_renders_a_subdirectory_layer`: the Python rendering for `backend` has job
        `backend:`, `defaults:`/`run:`/`working-directory: backend` and setup-uv
        `working-directory: backend`. The Node rendering for `frontend` has
        `cache-dependency-path: frontend/package-lock.json` and no marker comment left.
      - `test_ci_renders_a_root_layer_as_today`: job `python`/`node`, no
        `working-directory`, `cache-dependency-path: package-lock.json`, and no `<dir>` or
        `<layer>` left.
      - `test_placeholder_jobs_pass_and_list_the_real_steps`: one `run:` step with `echo`,
        a checkout, every real step's `run:`/`uses:` line present as a comment, and no
        `continue-on-error`.
      - `test_every_ci_template_names_the_required_check`: every `ci-*.yml` has a comment
        with "required check" and "ruleset".

      In `test_init_templates.py`, add the two placeholders to `CI_VARIANTS` and rewrite
      `test_ci_variants_carry_separate_job_names`. The job names now come from the layer:
      the real templates and their placeholders share `<layer>`, and
      `ci-placeholder.yml` keeps `verify`. The rendering helper lives in
      `test_init_layers.py`, and step 6 imports it.

      Then edit the templates (Approach → `init`, layer placeholders) and drop the old
      "add `defaults:`" comment.
      Automatic verification: `uv run pytest -q plugin/tests/test_init_layers.py plugin/tests/test_init_templates.py`

- [x] 6. **Dependabot and repository-settings templates (AC2 Dependabot part, AC6).**
      Files: `plugin/templates/github/dependabot.yml`,
      `plugin/templates/github/repository/ruleset.json` (new),
      `plugin/templates/github/repository/settings.json` (new),
      `plugin/tests/test_init_layers.py`, `plugin/tests/test_init_templates.py`
      (`test_dependabot_template` keeps its counts).
      Tests first, then run them red:
      - `test_dependabot_renders_the_layer_directory`: the `uv` entry renders to
        `directory: /backend`, the root renders to `directory: /`, and `github-actions`
        stays `/`.
      - `test_the_ruleset_template`: valid JSON, with `~DEFAULT_BRANCH`, `deletion`,
        `non_fast_forward`, `pull_request` with `allowed_merge_methods == ["squash"]`, and
        `required_status_checks` with a `<job>` context.
      - `test_the_repository_settings_template`: valid JSON with the seven fields of
        Approach.

      Then write the files.
      Automatic verification: `uv run pytest -q plugin/tests/test_init_layers.py plugin/tests/test_init_templates.py`

- [x] 7. **Settings and ADR templates (AC9, AC15 template part).** Files:
      `plugin/templates/settings.json`, `plugin/templates/docs/adr/ADR.en.md` (new),
      `plugin/templates/docs/adr/ADR.pl.md` (new), `plugin/tests/test_init_templates.py`.
      Tests first, then run them red:
      - Rewrite `test_settings_template_protects_the_guardrail_files`: `ask` holds
        `Edit(**/.claude/workflow.json)`. Its comment ("init has to write it unattended")
        goes, because `init` writes the file with Write, and Claude Code asks for every
        `.claude/` write anyway.
      - `test_settings_template_denies_detaching_the_plugin`: the four `deny` rules of
        AC9, plus the existing `Bash(gh pr merge*)`.
      - `test_the_adr_template_has_twins`: both files exist with the same heading levels,
        and the English one has no Polish letters.

      Then edit the templates. The ADR has Status, Context, Decision and Consequences.
      Automatic verification: `uv run pytest -q plugin/tests/test_init_templates.py plugin/tests/test_english_only.py`

- [ ] 8. **The `init` skill (AC1, AC2, AC4, AC7, AC10–AC15).** Files:
      `plugin/skills/init/SKILL.md`, `plugin/tests/test_init_skill.py`.
      The tests come first. They pin identifiers, not prose, like the file's own header.
      Run them red:
      - `test_layers_are_detected_at_depth_one`: step 1 names `pyproject.toml`,
        `package.json`, "depth 1", `node_modules`, and the naming of root and subdirectory
        layers. Step 2's question 3 names the layers.
      - `test_verify_and_format_follow_the_layer_directory`: step 4 names
        `uv run --project <dir>`, `<dir>/`, `CLAUDE.md`, `docs/CONVENTIONS.md` and
        `verify.command`.
      - `test_the_real_job_needs_tools_and_a_test_file`: step 4 names
        `ci-python-placeholder.yml`, `ci-node-placeholder.yml`, the markers
        `# subdirectory layer` and `# root layer`, `ruff`, `pytest`, and a test file.
      - `test_init_copies_the_repository_settings`: add `.github/repository/ruleset.json`
        and `.github/repository/settings.json` to `GENERATED`. Step 4 names `<job>`.
      - `test_allow_rules_follow_the_seen_stack`: the settings bullet names `Bash(uv *)`,
        `Bash(npm *)`, `Bash(docker compose *)` and the four compose file names.
      - `test_the_closing_warns_about_empty_hosts`: step 7 names `production.hosts`.
      - `test_the_hooks_dir_is_substituted_in_pre_push`: step 4 names `<gitHooksDir>` in
        the pre-push bullet, and the bullet has no `sed -i` (Approach → Other `init`
        points: the guard refuses a shell edit of an existing hook).
      - `test_gitignore_is_append_only`: the write scope names `.gitignore` and "append".
        Step 4 or 6 names `.claude/settings.local.json`, `.venv/`, `__pycache__/`,
        `.pytest_cache/`, `.ruff_cache/` and `node_modules/`.
      - `test_readme_and_licence_are_closing_todos`: step 7 names `README.md` and the
        licence with `TODO:`, and the skill never lists them as generated.
      - `test_the_adr_template_is_offered_not_copied`: step 7 names `templates/docs/adr/`
        and `docs/adr/`.

      Update `WRITE_SCOPE` and the test that checks the write scope.

      Then rewrite the skill:
      - step 1: survey the layers;
      - step 2: question 3 shows the layers;
      - step 4: rendering with the markers, real job or placeholder, verify, format,
        `CLAUDE.md` and CONVENTIONS fill, repository files, `allow` rules, the pre-push
        substitution and `.gitignore`;
      - step 6: idempotence for `.github/repository/` and `.gitignore`;
      - step 7: the closing list items;
      - the write scope and guardrails.

      Keep the question cap at one round of four. Keep the rule that a line naming
      `docs/ROADMAP.md` sits inside "Generate the files"
      (`test_no_domain_references.py`).
      Automatic verification: `uv run pytest -q plugin/tests/test_init_skill.py plugin/tests/test_no_domain_references.py plugin/tests/test_prompt_style.py plugin/tests/test_prompt_audit.py && claude plugin validate --strict plugin/`

- [ ] 9. **`NEW-PROJECT.md` (AC8, AC15 documentation part).** Files:
      `plugin/docs/NEW-PROJECT.md`, `plugin/tests/test_new_project_doc.py` (new).
      Tests first, then run them red:
      - `test_the_first_push_comes_before_the_hook`: in section 3, the first push appears
        before `git config core.hooksPath`, with the reason (`pre-push` refuses `main`).
      - `test_the_scaffold_through_a_pr_path`: names `git commit --allow-empty` and a PR.
      - `test_the_repository_settings_commands`:
        - `gh api -X POST repos/{owner}/{repo}/rulesets --input .github/repository/ruleset.json`;
        - `gh api -X PATCH repos/{owner}/{repo} --input .github/repository/settings.json`;
        - `gh api -X PUT repos/{owner}/{repo}/vulnerability-alerts`;
        - `…/automated-security-fixes`;
        - `…/private-vulnerability-reporting`.
      - `test_the_required_check_appears_after_the_first_run`.
      - `test_the_adr_template_is_described`: names `templates/docs/adr/` and `docs/adr/`.

      Then rewrite sections 1–3: layers in subdirectories, the order of the first push,
      the repository files replacing the hand-made ruleset paragraph, and the ADR.
      Automatic verification: `uv run pytest -q plugin/tests/test_new_project_doc.py plugin/tests/test_readme.py`

- [ ] 10. **Eval case `init-subdirectory-project` (AC3, and AC1, AC2, AC4, AC12 in
      practice).** Files: `plugin/evals/init-subdirectory-project/case.yaml`,
      `scaffold.sh`, `graders/criteria.md` (new), `plugin/tests/test_eval_cases.py`.
      Tests first, then run them red:
      - add the case to `NEW_CASES`;
      - `WRONG_BEHAVIOUR`: `["python:", "directory: /", "pytest", "backend",
        "<gitHooksDir>"]`;
      - `test_the_subdirectory_fixture_has_only_a_backend_manifest`: after `scaffold()`,
        the tracked and untracked files outside `.git` are exactly
        `backend/pyproject.toml`; it declares `ruff` and `pytest` in
        `[dependency-groups] dev`; and there is no `test_*.py`.

      Then write the case:
      - `case.yaml`: schema `1.1`, `context.scaffold_script: scaffold.sh`, `runs: 1`
        (step 12 decides the final value), and timeout 900 and `max_turns: 80` as the other
        `init` cases.
      - The prompt is English, with no answers given. It asks to run
        `/pipeline:init Ledger — a small bookkeeping API`, to finish alone, and at the end
        to show:
        - `.github/workflows/ci.yml` and `.github/dependabot.yml` in full;
        - `verify.command` and `format` from `.claude/workflow.json`, or the content to
          paste;
        - the `## Commands` block of `CLAUDE.md`;
        - the verification line of `docs/CONVENTIONS.md`;
        - the first 6 lines of `scripts/git-hooks/pre-push`.
      - The criteria check:
        - a CI job named `backend` with `defaults.run.working-directory: backend` and a
          placeholder step that passes;
        - Dependabot `uv` at `directory: /backend`;
        - `verify.command` running in `backend`;
        - `format` matching `backend/` with `uv run --project backend`;
        - `CLAUDE.md` and CONVENTIONS carrying the verify command;
        - no `<gitHooksDir>` left.

        The "incorrect" paragraph names: a job named `python:`, `directory: /` for `uv`, a
        real `pytest` step on a layer with no tests, a missing `backend`, and a leftover
        `<gitHooksDir>`. It also carries the `.claude/` limitation paragraph of the other
        `init` cases.
      Automatic verification: `uv run pytest -q plugin/tests/test_eval_cases.py && claude plugin validate --strict plugin/`

### Group 3 — Release and measurement

- [ ] 11. **Release 0.10.0 and documents (AC20, AC21).** Files:
      `plugin/.claude-plugin/plugin.json`, `plugin/CHANGELOG.md`, `plugin/README.md`
      (the `/pipeline:init` row and the configuration notes, if the wording changes),
      `docs/DECISIONS.md`, `docs/ROADMAP.md`, `docs/BACKLOG.md`,
      `plugin/tests/test_release_0_10_0.py` (new), `tests/test_documents.py`.
      Tests first, then run them red:
      - `test_release_0_10_0.py`: the manifest is ≥ 0.10.0. The `## 0.10.0` section names
        `init-subdirectory-project`, `.github/repository/`, `.gitignore`, the interpreter
        rule, `alembic.ini` and the separate-calls suggestion, and has a
        `**consumer impact:**` paragraph. The impact paragraph says that the new `ask`
        and `deny` rules reach only newly initialised projects, so an existing project
        copies them by hand.
      - `tests/test_documents.py::test_spec_015_decisions_rows`: four rows mention
        SPEC 015 — the placeholder job, the repository settings files, `.gitignore`, and
        the interpreter rule.
      - `::test_spec_015_roadmap_and_backlog`: the 0.10.0 item is ticked and records the
        cuts of Owner decisions 6 and 7, and the Guard P3 backlog row mentions the
        narrowed interpreter case.

      Then edit. The CHANGELOG follows the 0.9.0 section's shape. `docs/BACKLOG.md` also
      gains the two debts this plan leaves on purpose (Risks and traps), each with a
      priority and a trigger: the security templates have no subdirectory and no
      lock-file-less form (`security.yml` red on a fresh subdirectory project), and
      `verify.command` with `pytest` exits 5 on a layer with no tests.
      Automatic verification: `uv run pytest -q plugin/tests/test_release_0_10_0.py tests/test_documents.py plugin/tests/test_readme.py && bash scripts/check.sh`

- [ ] 12. **Eval measurement (AC3) and smoke runs.** Files: this PLAN (a ledger under
      `## Deviations`, or a `### Eval ledger` under End-to-end → Automatic), and
      `plugin/evals/init-subdirectory-project/case.yaml` or its criteria, only when the
      policy requires it.

      Commit steps 1–11 first, because `eval.sh` refuses a dirty `plugin/` and the ledger
      names the commit. The measurement uses the default model and 5 runs:

      `claude plugin eval plugin/ --scaffold --allow-tools Bash Write Edit --trust-plugin --no-publish --ablation none --case init-subdirectory-project --runs 5 --max-cost-usd 4 --json <scratchpad>/eval/measure-init-subdirectory.json`

      The result decides the case:
      - 5 of 5: keep `runs: 1`;
      - 4 of 5: set `runs: 3`;
      - below 4: sharper criteria, or a skill fix inside this plan's scope when the
        transcript shows the skill at fault, then one more measurement.

      Then run one smoke each for the existing cases this plan touches: the `init` skill
      (`init-without-questions`, `init-keeps-manual-edits`,
      `init-writes-the-chosen-language`) and the guard (`guard-blocks-main-push`):

      `claude plugin eval plugin/ --scaffold --allow-tools Bash Write Edit --trust-plugin --no-publish --ablation none --case <name> --runs 1 --max-cost-usd 1 --json <scratchpad>/eval/smoke-<name>.json`

      A failed smoke gets the 5-run measurement of the policy. Do not commit a receipt from
      a `--case` run: restore `plugin/evals/last-run.json` when the CLI wrote it. The
      receipt is the owner's full `bash scripts/eval.sh` before the tag.

      Keep a ledger row per call: date, case, model, runs, passed, `--max-cost-usd`, cost
      from the JSON, and the running total. **Budget: $8 in total.** Escalate with the
      ledger when the budget would be exceeded, or when a case stays below 4 of 5 after
      one criteria revision.
      Automatic verification: the measurement JSON shows 5 runs with ≥ 4 passed, every
      smoke JSON shows 1 of 1 (or its follow-up measurement shows ≥ 4 of 5), the ledger
      total is ≤ $8, and `uv run pytest -q plugin/tests/test_eval_cases.py && bash scripts/check.sh`
      passes.

## Risks and traps

- **Heredoc renaming.** The marker must replace only the delimiter word on the opening line.
  The terminator is matched against the stored original delimiter. A heredoc inside double
  quotes (`"$(cat <<'EOF'`) is not opened in the outer text today, because
  `ShellState` sees the quote. It reaches the nested `$(…)` analyzer instead. Keep it that
  way, and pin it with the commit-message test of step 2.
- **`eval` re-enters `run` on the same `Analyzer`.** Save and restore the bodies
  attribute around `run`, or an `eval` inside a call would lose the outer bodies.
- **The `-c` of a shell versus an interpreter.** `bash -c` is already analysed as a
  command string. The interpreter rule must not treat `sh -c` as interpreter code.
- **False refusals for this repository's own work** arrive only after the owner installs
  0.10.0: an agent's `python3 -c` that reads `.claude/workflow.json` is refused then. That
  is intended (SPEC decision: reads count), and `Read` and `cat` stay open.
- **`ask` on `Edit(**/.claude/workflow.json)`** also applies to the Write tool. `init`
  already needs the owner's consent for every `.claude/` write, so unattended runs are
  unchanged. The eval sandbox blocks `.claude/` anyway, which is why the graders accept the
  printed content.
- **`sed -i` on the copied `pre-push`** is refused by the guard once the hook exists
  under `gitHooksDir`. The substitution happens in the copy itself (Approach → Other
  `init` points).
- **Placeholder job without checkout** fails with `defaults.run.working-directory` on a
  missing directory, so the placeholder keeps `actions/checkout`.
- **Node real job**: `npm run build` and `test:run` are not universal. The skill drops the
  build step without a `build` script and uses the test script the manifest has.
- **`verify.command` with `pytest` on a layer without tests** exits 5 locally, like CI did.
  The SPEC does not cover it, so step 11 records it in `docs/BACKLOG.md` instead.
- **`security.yml`** is not among AC2's six places. For a subdirectory layer it still runs
  at the root, and `uv export --frozen` fails without a lock file. This is why the canary's
  pass condition names the CI workflow explicitly. Step 11 records the debt in
  `docs/BACKLOG.md`: a subdirectory form and a no-lock-file form for the security
  templates.
- **Eval cost and flakiness.** `init` runs are long, at about $0.4–0.5 each (PLAN 006
  ledger). `--max-cost-usd` bounds the number of runs, not the cost of one, so keep it at
  the values in step 12.
- **Twin templates.** `ADR.pl.md` must keep the heading structure of `ADR.en.md`, and
  only `*.pl.md` may hold Polish.

## End-to-end verification

### Automatic (performed by /pipeline:implement)

1. `bash scripts/check.sh` is green: `validate --strict` for the plugin and the
   marketplace, ruff, black, and pytest in `plugin/tests` and `tests/`.
2. Guard smoke through the real hook (`python3 plugin/bin/guard.py` with a JSON payload on
   stdin, `cwd` at this repository):
   - `python3 - <<'EOF'` + `print(open('.claude/workflow.json').read())` + `EOF` → exit 2,
     with stderr containing `Edit/Write`;
   - `cat <<'EOF' > /tmp/x.md` + `.claude/workflow.json` + `EOF` → exit 0;
   - `uv lock && uv sync && gh pr merge 1` → exit 2, with stderr containing
     "separate call".
3. Template rendering by hand in the scratchpad: apply the subdirectory rendering of
   step 5 with `sed` to `ci-python.yml` for `backend`, and check that `grep -c
   'working-directory: backend'` gives 2 (the job defaults and setup-uv) and that
   `grep -c '<dir>\|<layer>\|# subdirectory layer\|# root layer'` gives 0. The commented
   steps of a placeholder carry the same markers, so they render the same way.
4. Step 12's ledger: `init-subdirectory-project` ≥ 4 of 5, the smoke runs green, total
   ≤ $8.

### Manual (performed by the owner)

1. The canary before the tag (AC22). In a fresh GitHub repository whose only file is
   `backend/pyproject.toml` (with `ruff` and `pytest` as dev dependencies), run
   `/pipeline:init` from `claude --plugin-dir <clone>/plugin`. Then make the first commit
   and push it to `main` from a terminal, as `NEW-PROJECT.md` describes, before enabling
   the hook. Then apply the ruleset with the `gh api … --input .github/repository/ruleset.json`
   command from `NEW-PROJECT.md`.
   Pass when: `gh run list --workflow ci.yml --limit 1` shows the run as `completed
   success` with a job named `backend` (`gh run view <id>`); `grep -rn 'backend'
   .github/dependabot.yml .claude/workflow.json` shows `directory: /backend`,
   `verify.command` and the `format` entries; and `gh api repos/{owner}/{repo}/rulesets`
   plus `gh api repos/{owner}/{repo}/rulesets/<id> --jq '.rules[] |
   select(.type=="required_status_checks") | .parameters.required_status_checks[].context'`
   prints `backend`. A red Security run on this fixture is a known limit, not a failure
   (Risks → `security.yml`).

## Definition of Done

- [ ] all steps ticked
- [ ] `bash scripts/check.sh` fully green
- [ ] end-to-end verification (automatic) performed, result recorded here
- [ ] `docs/ROADMAP.md` updated; `docs/DECISIONS.md`, `docs/BACKLOG.md`, `plugin/README.md`,
      `plugin/docs/GUARD.md` and `plugin/docs/NEW-PROJECT.md` updated
- [ ] spec status: `implemented`

## Owner decisions

_(appended by /pipeline:ship or a stage on escalation: date, stage, question, decision)_

## Review log

### 2026-10-05 — plan review

Anti-anchoring notes, made from the SPEC alone: (1) heredoc bodies are dropped by
`strip_heredocs` today, so the interpreter rule needs the bodies tied to their command;
(2) the compound suffix is one line in `Analyzer.run`; (3) the Alembic notice belongs beside
`read_rule_notice`; (4) `init` is prose, so the templates need a mechanically testable
subdirectory form and the eval case carries the rest; (5) the pre-push substitution must
survive the guard's own hook rule. The plan matched (1)–(4); (5) was the first lead.

Findings (severity counted before the fixes):

| # | Severity | Finding | Change |
|---|----------|---------|--------|
| 1 | `major` | Step 1 asked to run both AC19 tests red, but `uv lock && uv sync && gh pr merge 1` already yields "the other 2 of 3 parts passed — run them as a separate call" (checked on `guard.evaluate`). The implementer would hit the "proving test green before the change" escalation on a regression pin. The same holds for the allowed cases of step 2 and the silent cases of step 3. | Step 1 marks the chained test as a regression pin and the every-part-refused test as the proving one; the AC19 matrix row's fourth column says so; steps 2 and 3 mark their allowed/silent cases as regression pins. |
| 2 | `major` | The plan had the skill substitute `<gitHooksDir>` "in the copied `pre-push` with `sed`". The guard refuses `sed -i` on an existing hook under `gitHooksDir` (checked: "an existing git hook changes only through Edit/Write…"), so AC12 would fail in the eval and for consumers. | Approach → Other `init` points: substitute while copying (`sed … <template> > <hook>`, then `chmod +x`), never `sed -i`; step 8's test pins the absence of `sed -i`; a Risks entry. |
| 3 | `minor` | The interpreter rule missed `node -p`/`--print`, which evaluates code like `-e`, and the shell expands `$CLAUDE_PLUGIN_ROOT` inside an unquoted heredoc or a double-quoted `-c`; `tokenize` also leaves `<<-` delimiters as `-<word>`. | Approach → Guard: `-p`/`--print` added, code matched raw and after `expand_variables`, marker looked up by search; step 2 gains the two test cases. |
| 4 | `minor` | Step 4 narrowed GUARD.md lines 21 and 234–238 but not the interpreter mentions at lines 218 and 228. | Step 4 covers them. |
| 5 | `minor` | The `security.yml` and `pytest`-exit-5 debts were "backlog proposals" with no step writing them. | Step 11 adds both to `docs/BACKLOG.md`; Owner summary and Risks point there. |

Checked and found sound (later stages need not repeat it):

- **Coverage:** every AC1–AC22 has steps and a proving test; the matrix matches the steps;
  AC22 is the manual canary with a `Pass when:` line; AC3's six grader places are AC2's.
- **Compliance:** standard library only; the guard tested through `evaluate` and as a
  subprocess; tests pin identifiers, not prose; ADR twins; the eval cost policy (5 runs,
  `--max-cost-usd`, wrong behaviour named, receipt and canary left to the owner). DECISIONS
  searched for "interpreter", "write scope", "placeholder", "unattended", "ask": the
  2026-09-21 interpreter limit is narrowed with a new row (AC20); no row binds keeping
  `.claude/workflow.json` out of `ask` (the test comment dates from the 0.2.0 import), and
  only `init` writes that file, so a stage subagent never stalls on the new `ask`.
- **Minimality:** the delimiter-marker design is the smallest one that keeps AC17's
  attribution; per-stack placeholder templates reuse the real steps as comments.
- **Feasibility:** confirmed in code — `GUARDRAIL_FILES` already says "Edit/Write";
  `config.root`, `first_in_session` and the `read_rule_notice` order exist as described;
  `<<<` tokenizes as one token; a heredoc inside unquoted `$(…)` is already refused as
  unparseable, so nested analyzers lose no bodies; the commit-message heredoc inside `"…"`
  stays with the nested `cat` analyzer. The only `<gitHooksDir>` in the templates is
  `pre-push` line 5.
- **E2E:** automatic part runs on the real hook and on scratchpad renderings; the manual
  part is only the canary, which cannot be automated (a real GitHub repository and CI).
- **Testability:** every step has exact `Automatic verification:` commands.
- **Groups:** three groups, no boundary leaves work half done; step 12 needs every prior
  step committed and sits last.
- **Test-first:** every AC step writes its tests first; the fourth matrix column is present.
- **Summary:** no new dependency, no data migration, consistent with SPEC Owner
  decision 11.
- **Language:** `en`, matching `.claude/workflow.json`.

Decision: the plan is ready — both majors were fixed in the plan itself, no blocker
remains, and it adds no dependency or migration, so it is set to `plan-approved`.

## Chunk notes

_(filled in by /pipeline:implement in chunk mode — one entry per chunk that ends at a group boundary)_

## Deviations

_(filled in by /pipeline:implement — every deviation from the plan with its rationale)_

- Step 7 (minor): `plugin/tests/test_english_only.py` gets the allowlist entry
  `templates/docs/adr/*.pl.md`. The plan names `test_english_only.py` as the place where Polish is
  allowed in `*.pl.md`, but the allowlist globs match only `templates/docs/*.pl.md`, so the new
  Polish ADR twin needs its own entry (the allowlist test also requires the entry to be live).

## Final review

_(filled in by /pipeline:final-review)_
