# PLAN 002 — A guard worth pointing at: close the known leaks, then document it

## Owner summary

- **Approach:** Three guard fixes in `plugin/bin/guard.py`, each a small function beside the
  code it corrects: push refspecs are expanded with the same variable map the removal rule
  uses (prefix assignments excluded, empty values dropped) and refused when anything stays
  unresolved; `git config` gets one parser that tells a read from a write, so reads of
  `core.hooksPath` pass while writes to it and to `alias.*` are refused; `git -c alias.*` is
  refused. Then a one-off measurement of string `deny` rules in a throwaway sandbox, and
  `plugin/docs/GUARD.md` built on its results, with its command table run through the guard
  by a test. Finally `plugin/README.md` in English with its guard section cut to a summary
  and a link, release 0.3.4 and the project-document follow-ups.
- **Main risks:** new refusals for consumers (`git push origin HEAD:$(git branch
  --show-current)`, `git push $(git remote) <branch>` and every other unresolvable
  refspec) — named in the CHANGELOG; the `deny`
  measurement depends on Claude Code behaviour and must run hooks-off in a sandbox so the
  0.3.3 guard does not mask the result; the README translation must not drift a key, default
  or status name (the existing tests pin them).
- **New dependency:** no — standard library only; no dev tool added (SPEC → "Owner decisions").
- **Data migration:** no (SPEC → "Owner decisions").
- **Manual scenarios for the owner:** 1 — after tagging 0.3.4 and moving `stable`, a fresh
  session refuses `B=main; git push origin $B` with the push-to-main reason.

## Approach

**Push refspecs (AC1–AC7).** `Analyzer.segment` already keeps two variable maps: `self.env`
(session environment, earlier bare assignments, `export`, with conditional assignments
turned into their own unresolvable `$NAME`) and a local `env` that additionally holds the
segment's prefix assignments and wrapper assignments (`env B=x …`). A real shell expands the
command's own arguments before the prefix assignments take effect, so the push check must use
`self.env` — exactly what `check_path` does for `rm`/`find` (`expand_variables(raw,
self.env)`, then `"$" in expanded` → refuse). `check_push` becomes a method (or takes
`self.env` as a parameter) and works on expanded positionals:

0. if any non-option arg — the remote included — ends in `$`, refuse with the new reason
   (below) before anything else: the lexer cut a `$(` off there, so everything after the
   substitution landed in other segments and the push segment is truncated
   (`git push $(git remote) main` tokenizes to the push segment `git push $` and a separate
   "command" `main` — measured; without this point it passes on a feature branch while the
   shell pushes `main`);
1. positionals = non-option args in order, each paired with its raw spelling and expanded
   with `expand_variables(raw, self.env)`;
2. each expansion is split on whitespace (`expanded.split()`), like the shell's field
   splitting of an unquoted expansion: `B="origin main"; git push $B` is
   `git push origin main` and `B="feat/x main"; git push origin $B` pushes `main` in a real
   shell (the assignment token is `B=origin main` — measured). A value that splits into
   nothing (`E=`, a quoted `""`) disappears — `shlex` has already removed the quotes, so a
   quoted value is split too; that errs on the protected side only;
3. the first remaining word is the remote and is **not** checked (AC6);
4. every remaining refspec word that still contains `$` or `` ` `` is refused with the new
   reason; otherwise the existing `+`/`:` and protected-branch checks run on the expanded
   words, unchanged (AC7).

Command substitution never reaches `check_push` whole: the tokenizer splits `$(echo main)`
into `$`, `(`, `echo`, `main`, `)` (measured), so the push segment's refspec is the token `$`
or `HEAD:$`, and a backtick form arrives as `` `echo `` — both contain an unresolvable
character. The reason shows the raw token, with `(...)` appended when the token ends in `$`
(the lexer cut a `$(` off), so the agent sees `$(...)`/`HEAD:$(...)` rather than a bare `$`.

New constant in `guard.py`:

```python
UNRESOLVED_REFSPEC = (
    "cannot verify a push refspec built from variables or command substitution: {}; "
    "spell the branch out"
)
```

Alternatives considered: resolving known variables and letting the rest through (rejected in
SPEC); doing the expansion inside `tokenize` for all rules (touches every rule and the
compound-refusal texts — far wider than this spec).

**`git config` reads and writes (AC8, AC9, AC11).** Today any `git config` argument starting
with `core.hookspath` is refused unless one of `CONFIG_READS` is present, so a bare-key read
is refused. Replace `CONFIG_READS` with one parser:

```python
def config_access(args: list[str]) -> tuple[str, bool]:
    # returns (lower-cased key or "", writes)
```

- options taking a value are skipped with their value: `-f`, `--file`, `--blob`, `--type`,
  `--default`, `--comment`, `--value`; any other `-…` token (including `--file=…`,
  `--global`, `--local`, `--show-origin`) is a flag;
- the first positional, if it is a git ≥ 2.46 subcommand, sets the action: `get`, `list` →
  read; `set`, `unset`, `rename-section`, `remove-section`, `edit` → write;
- otherwise flags decide: any of `--add`, `--replace-all`, `--unset`, `--unset-all`,
  `--rename-section`, `--remove-section`, `-e`, `--edit` → write; any of `--get`,
  `--get-all`, `--get-regexp`, `--get-urlmatch`, `--get-color`, `--get-colorbool`, `-l`,
  `--list` → read;
- otherwise the legacy form: a key plus at least one more positional (including the empty
  token `""`) → write, a key alone → read;
- the key is the first positional after the subcommand, lower-cased;
- a section operation (`--rename-section`, `--remove-section`, `rename-section`,
  `remove-section`) names sections, not keys: the parser returns every positional, and a
  section `core` counts as a `core.hooksPath` write, a section `alias` as an alias write —
  `git config --remove-section core` drops `core.hooksPath`, and
  `git config --rename-section x alias` writes persistent aliases. So the signature is
  `config_access(args) -> tuple[list[str], bool]` (lower-cased names, writes), and the
  checks below run over every name (`name == "core" or name.startswith("core.hookspath")`;
  `name == "alias" or name.startswith("alias.")`).

`Analyzer.git`: `if sub == "config"` → `names, writes = config_access(sub_args)`; `writes`
and a `core.hooksPath` name → `HOOKS_PATH`; `writes` and an alias name → `ALIAS`. Unsetting an alias is a write too and is refused — the rule stays one line and an
alias removal is rare; noted in Risks.

**`git -c alias.*` (AC10, AC12).** In the global-option loop of `Analyzer.git`, beside the
existing `core.hookspath` check: `option == "-c" and value.lower().startswith("alias.")` →
`ALIAS`. New constant:

```python
ALIAS = "a git alias cannot be verified by the guard; run the git command itself"
```

**The `deny` measurement (AC17).** Claude Code's `deny` matching is not ours, so it is
measured, not inferred. A scratch sandbox (a git repo whose `origin` is a local bare repo, no
GitHub remote, outside this repository) makes every candidate harmless. Each candidate runs
twice through `claude -p --safe-mode` (plugins and hooks off — otherwise the installed 0.3.3
guard would refuse first and mask the `deny` result; permissions work normally): once with no
`deny` rule (baseline: it must run) and once with its rule in `--settings` (the row qualifies
only if it runs again). A control row (`gh pr merge 12 --squash` against
`Bash(gh pr merge*)`) must be denied, proving `--settings` takes effect. The harness is a
script in the scratchpad — the prompts carry `$(…)` and backticks, which the session's own
guard would otherwise analyse in the command line — and is not committed; its results are
recorded in this PLAN and GUARD.md records the date and `claude --version`.

**`plugin/docs/GUARD.md` (AC14–AC18).** English, built from the current README guard section
(`plugin/README.md` → "### Strażnik komend"), `plugin/bin/guard`, `plugin/bin/guard.py`
header comment, `plugin/templates/pre-push`, `scripts/git-hooks/pre-push`, `CLAUDE.md` → Git
(rulesets) and `docs/DECISIONS.md` rows of 2026-09-17/2026-09-21. Fixed headings, because the
test anchors on them:

- `# The pipeline guard`
- `## Threat model`
- `## Three layers` with `### The command guard`, `### The pre-push hook`,
  `### GitHub rulesets` — each states what it covers, when it runs, how it is bypassed
- `## Deny rules versus the guard` — one line `Measured on YYYY-MM-DD with Claude Code
  X.Y.Z (claude -p --settings).` and a table `| Command | Deny rule it gets past | Guard's
  reason |`; column 1 is one code span with the command (no backticks inside; a literal `|`
  written `\|`), column 2 one code span with the rule (`Bash(…)`), column 3 one code span
  with a fragment of the guard's reason (no backticks inside)
- `## Fail-open by design`
- `## Known limits` — at least the AC15 list, each with its `docs/BACKLOG.md` entry or
  roadmap stage; also git configuration channels the guard does not parse
  (`--config-env`, `GIT_CONFIG_COUNT`/`GIT_CONFIG_KEY_n`/`GIT_CONFIG_PARAMETERS`,
  `GIT_CONFIG_GLOBAL`, an `include.path`/`includeIf` entry pointing at another file)

The table test lives in `plugin/tests/test_guard.py` to reuse the `on_feature` fixture and the
case count: it parses the table, requires ≥ 5 rows, runs each command through
`guard.evaluate` and asserts the reason contains column 3's fragment.

**`plugin/README.md` in English (AC19–AC22).** A translation section by section, keeping
every heading's position and every code block's literal content except explanatory
comments; placeholders become English (`<nazwa>` → `<name>`, `/ścieżka/do/…` →
`/path/to/…`). The `RESULT` block stays byte-identical to the Polish contract the agents
emit (it is a literal inside a fence). Quoted Polish literals (`## Decyzje właściciela`)
stay in code spans. The guard section shrinks to a few sentences: what the guard is,
universal vs configured rules, fail-open, the Alembic-only migration scope with
`migrations.command` and `migrations.localHosts`, and a link `[docs/GUARD.md](docs/GUARD.md)`.
English headings (test anchors) — exact lines, code spans kept as in the Polish headings:
`## Installation`, `## Commands and agents`,
``## Project configuration — `.claude/workflow.json` ``, ``### Formatting (`format[]`)``,
`### Command guard`, `## Pipeline mechanics`, `### Spec statuses`,
``### The `RESULT` contract``, `### Escalation triggers`, `## Workflow metrics`,
``### Checking metrics (`--check`)``, `## CHANGELOG`. The configuration table header becomes `| key | default | meaning |`; the
`migrations` default cell becomes `no section`.

Patterns reused: `expand_variables` and the `"$" in expanded` refusal of `check_path`
(`plugin/bin/guard.py`); `make_repo`, `on_main`, `on_feature`, `evaluate`, `run_hook` and
the `BASELINE`/`collected_cases` regression check (`plugin/tests/test_guard.py`); the
section-splitting helpers of `plugin/tests/test_readme.py`; the `claude -p --settings`
measurement recorded in `docs/DECISIONS.md` (2026-09-21, `stable` deny rules).

## AC → steps matrix

| AC | Steps | Proving test |
|----|-------|--------------|
| AC1 | 1 | `test_guard.py::test_a_push_variable_resolving_to_main_is_refused` (+ `test_hook_refuses_a_push_variable_resolving_to_main`) |
| AC2 | 1 | `test_guard.py::test_an_unresolvable_push_refspec_is_refused` |
| AC3 | 1 | `test_guard.py::test_a_prefix_assignment_does_not_resolve_its_own_push` (on main and feature) |
| AC4 | 1 | `test_guard.py::test_an_empty_push_variable_pushes_the_current_branch` |
| AC5 | 1 | `test_guard.py::test_a_push_variable_resolving_to_a_feature_branch_is_allowed` |
| AC6 | 1 | `test_guard.py::test_a_variable_remote_with_literal_refspecs` |
| AC1/AC2 (review) | 1 | `test_guard.py::test_a_split_push_variable_is_checked_word_by_word`, `test_a_substitution_in_the_remote_position_is_refused` |
| AC7 | 1 | the existing push cases in `BLOCKED_ANYWHERE`, `UNIVERSAL_BLOCKED`, `test_feature_branch_work_is_allowed`, `test_changing_main_is_blocked` — unchanged and green |
| AC8 | 2 | `test_guard.py::test_reading_core_hooks_path_is_allowed` |
| AC9 | 2 | `test_guard.py::test_writing_core_hooks_path_is_refused` |
| AC10 | 2 | `test_guard.py::test_a_command_line_alias_is_refused` |
| AC11 | 2 | `test_guard.py::test_writing_a_persistent_alias_is_refused`, `test_reading_an_alias_is_allowed`, `test_section_operations_on_core_or_alias_are_refused` |
| AC12 | 2 | `test_guard.py::test_other_command_line_config_keys_pass` |
| AC13 | 6 | `test_readme.py::test_changelog_starts_at_the_manifest_version`, `test_the_changelog_names_the_consumer_impact`; step 6 grep for `0.3.4` |
| AC14 | 4 | `test_guard.py::test_guard_md_has_the_required_sections`; `test_readme.py::test_no_polish_outside_code[docs/GUARD.md]` |
| AC15 | 4 | `test_guard.py::test_guard_md_names_the_known_limits` |
| AC16 | 3, 4 | `test_guard.py::test_every_deny_table_command_is_refused`, `test_the_deny_table_has_at_least_five_rows` |
| AC17 | 3, 4 | measurement table in this PLAN (step 3 results); `test_guard.py::test_guard_md_records_the_deny_measurement` |
| AC18 | 4 | `test_no_domain_references.py::test_no_project_references[docs/GUARD.md]` (collected automatically) |
| AC19 | 5 | `test_readme.py::test_no_polish_outside_code[README.md]` |
| AC20 | 5 | `test_readme.py::test_the_readme_keeps_its_sections`, `test_every_status_is_documented`, `test_the_result_block_matches_the_contract`, existing key/default/metric tests |
| AC21 | 5 | `test_readme.py::test_the_guard_section_links_guard_md`, `test_the_guard_section_states_the_migration_scope` |
| AC22 | 5 | updated `test_readme.py` installation/metrics/guard tests on English anchors; step 5 greps on `CLAUDE.md` and `README.md` |
| AC23 | 7 | step 7 greps on `docs/DECISIONS.md` and `docs/CONVENTIONS.md` |
| AC24 | 7 | step 7 grep on `docs/BACKLOG.md` |
| AC25 | 7, 8 | step 7 grep on `docs/ROADMAP.md`; `bash scripts/check.sh` in step 8 |

## Steps

- [x] 1. **Push refspecs resolved or refused** — files: `plugin/bin/guard.py`,
      `plugin/tests/test_guard.py`.
      In `guard.py`: add `UNRESOLVED_REFSPEC`; move `check_push` to use `self.env` (make it
      an `Analyzer` method, or pass `self.env` from `Analyzer.git`) and implement the four
      points from Approach → Push refspecs. Do not use the segment-local `env` (it carries
      prefix and wrapper assignments). Keep the existing reasons and order of checks
      (destructive options first, then `+`/`:`, then protected targets) so AC7 holds.
      In `test_guard.py` add (commands verbatim from the SPEC; all via `evaluate`, no
      variables in the env beyond `CLAUDE_PROJECT_DIR`):
      - `PUSH_TO_MAIN_BY_VARIABLE` (AC1, 7 commands) →
        `test_a_push_variable_resolving_to_main_is_refused(on_feature, command)`: reason
        contains `"pushing to main"`;
      - `test_hook_refuses_a_push_variable_resolving_to_main(on_feature)`: `run_hook` with
        `B=main; git push origin $B` → exit 2, `"pushing to main"` in stderr;
      - `PUSH_UNRESOLVED` (AC2) as `(command, shown)` pairs: `$UNKNOWN`, `HEAD:$UNKNOWN`,
        `$(...)`, `` `echo ``, `$B` (for `false || B=feat/x; git push origin $B`) →
        `test_an_unresolvable_push_refspec_is_refused`: reason contains `"spell the branch
        out"` and `shown`;
      - `test_a_prefix_assignment_does_not_resolve_its_own_push` parametrized over
        `on_main`/`on_feature` (use `request.getfixturevalue`): `B=feat/x git push origin
        $B` refused with `"spell the branch out"`;
      - `test_an_empty_push_variable_pushes_the_current_branch`: `E=; git push origin $E`
        refused with `"pushing to main"` on `on_main`, `None` on a feature branch (two
        separate tests or one test switching branches — the `repo` fixture is
        module-scoped, so switch explicitly and in this order: feature, then main);
      - `test_a_push_variable_resolving_to_a_feature_branch_is_allowed` (AC5, 3 commands)
        → `None`;
      - `test_a_variable_remote_with_literal_refspecs`: `git push $REMOTE feat/002-x` and
        `R=origin; git push $R feat/002-x` → `None`; `git push $REMOTE main` → reason
        contains `"pushing to main"`;
      - `test_a_split_push_variable_is_checked_word_by_word` (review, point 2):
        `B="origin main"; git push $B` and `B="feat/x main"; git push origin $B` → reason
        contains `"pushing to main"`; `B="feat/x feat/y"; git push origin $B` → `None`;
      - `test_a_substitution_in_the_remote_position_is_refused` (review, point 0):
        `git push $(git remote) main` and `git push $(git remote) feat/002-x` → reason
        contains `"spell the branch out"` and `$(...)`.
      Automatic verification:
      `uv run pytest -q -p no:cacheprovider plugin/tests/test_guard.py`
      `uv run pytest -q -p no:cacheprovider plugin/tests/test_guard.py -k "push"`
      `uv run ruff check plugin/ && uv run black --check --quiet plugin/`

- [x] 2. **`git config` reads and writes, aliases** — files: `plugin/bin/guard.py`,
      `plugin/tests/test_guard.py`.
      In `guard.py`: add `ALIAS`, the option/flag/subcommand sets and `config_access` from
      Approach; remove `CONFIG_READS`; in `Analyzer.git` replace the `core.hookspath`
      `config` check with the `config_access` logic (hooksPath writes → `HOOKS_PATH`,
      `alias.` writes → `ALIAS`) and add the `-c alias.` check to the global-option loop.
      In `test_guard.py` add:
      - `test_reading_core_hooks_path_is_allowed` — the 7 AC8 commands → `None` (the two
        already in `ALLOWED_ANYWHERE` stay there too);
      - `test_writing_core_hooks_path_is_refused` — the 9 AC9 commands → reason contains
        `"core.hooksPath"` (use `feat/001-x` instead of `feat/x` where the fixture branch
        matters; `git config core.hooksPath ""` written as the Python string
        `'git config core.hooksPath ""'`);
      - `test_a_command_line_alias_is_refused` — the 3 AC10 commands → reason contains
        `"alias cannot be verified"` and `"run the git command itself"`;
      - `test_writing_a_persistent_alias_is_refused` — the 3 AC11 writes → same fragments;
        `test_reading_an_alias_is_allowed` — `git config alias.p`,
        `git config --get-regexp alias` → `None`;
      - `test_other_command_line_config_keys_pass` — `git -c user.name=x commit -m y` on
        `on_feature` → `None`;
      - `test_section_operations_on_core_or_alias_are_refused` (review) —
        `git config --remove-section core`, `git config --rename-section core x`,
        `git config remove-section core` → `"core.hooksPath"`;
        `git config --rename-section x alias` → `"alias cannot be verified"`;
        `git config --remove-section user` → `None`;
      - raise `BASELINE` to the new lengths of `BLOCKED_ANYWHERE`/`ALLOWED_ANYWHERE` and the
        new collected-case count only if those lists grew (a new list does not change
        them); leave the comment's history intact and add one line for 0.3.4.
      Automatic verification:
      `uv run pytest -q -p no:cacheprovider plugin/tests/test_guard.py`
      `uv run pytest -q -p no:cacheprovider plugin/tests/test_guard.py -k "config or alias or hooks"`
      `uv run ruff check plugin/ && uv run black --check --quiet plugin/`

- [x] 3. **Measure string `deny` rules against guard-refused commands** — files: none in
      the repository (scratchpad only); results into this PLAN → "End-to-end verification →
      Results → Deny measurement".
      a. Check `~/.claude/settings.json` for `permissions.deny` entries that would match a
         candidate; record them (the sandbox sits outside this repository, so project
         settings do not load).
      b. Build the sandbox in the scratchpad: `git init -b main sandbox`, two commits, a
         bare repo `remote.git` added as `origin`, a branch `feat/x`; confirm `git remote -v`
         shows only the local path; run with `GH_REPO` unset.
      c. Write `measure-deny.sh` in the scratchpad. For each candidate `(command, rule)`:
         run `claude -p --safe-mode --output-format stream-json --verbose --allowedTools
         Bash --max-turns 3 --settings <json>` from the sandbox (`--max-turns` is not listed
         in `claude --help` of 2.1.272; if the CLI rejects it, drop it — the prompt already
         says stop; if the control row is not `denied` under `--safe-mode`, retry the
         harness with `--setting-sources local` instead of `--safe-mode` — that skips the
         user settings which enable the `--scope user` plugin — and record which mode was
         used; a baseline `ran` on a guard-refused command is the proof hooks were off) with the prompt "Run exactly
         this one Bash command once, verbatim, as a single Bash tool call, then stop. Do not
         retry or change it: <command>", read the prompt from a file; once with
         `{"permissions":{"deny":[]}}` (baseline) and once with `{"permissions":{"deny":
         ["<rule>"]}}`. Classify from the stream: the Bash `tool_use` input must equal the
         command verbatim (otherwise re-run once, then mark "not measurable"); `denied` if
         the tool result is a permission denial or the final `result` event lists it in
         `permission_denials`, `ran` otherwise. Reset the sandbox (`git reset`/re-create)
         between runs where a command changes it. Run the script with
         `bash <scratchpad>/measure-deny.sh`.
      d. Candidates (command → rule): control `gh pr merge 12 --squash` →
         `Bash(gh pr merge*)` (must be `denied` with the rule; if not, the harness is
         broken: fix it before anything else);
         `env gh pr merge 12 --squash` → `Bash(gh pr merge*)`;
         `bash -c 'gh pr merge 12 --squash'` → `Bash(gh pr merge*)`;
         `echo $(gh pr merge 12)` → `Bash(gh pr merge*)`;
         `B=main; git push origin $B` → `Bash(git push origin main*)`;
         `git push origin HEAD:main` → `Bash(git push origin main*)`;
         `git push -u origin main` → `Bash(git push origin main*)`;
         `git -C . push origin main` → `Bash(git push origin main*)`;
         `git -c alias.p=push p origin main` → `Bash(git push origin main*)`;
         `eval 'git reset --hard HEAD~1'` → `Bash(git reset --hard*)`;
         `git clean -xdf` → `Bash(git clean -f*)`;
         `git -c core.hooksPath=/dev/null push origin feat/x` →
         `Bash(git config core.hooksPath*)`.
         A row qualifies when baseline = `ran` and with-rule = `ran`, and
         `guard.evaluate` refuses the command on a feature branch (check with the step-1/2
         guard via a pytest run of step 4, or a scratch `python3` script importing
         `plugin/bin/guard.py`).
      e. Record: date (`date +%Y-%m-%d`), `claude --version`, the user-settings finding from
         (a), and a table candidate | rule | baseline | with rule | qualifies.
      If fewer than 5 rows qualify, add candidates of the same shape (e.g. `command git push
      origin main`, `git push origin feat/x:main`, `nohup git push origin main` against
      `Bash(git push origin main*)`) and measure them; still fewer than 5 → `RESULT:
      ESCALATE` (AC16 cannot be met truthfully).
      Automatic verification: the control row is `denied` with its rule and `ran` without
      it; `grep -c "qualifies" specs/002-guard-hardening-and-docs/PLAN.md` ≥ 1 and the
      results table has ≥ 5 rows marked `yes`; `git status --short` shows only `PLAN.md`
      changed.

- [x] 4. **`plugin/docs/GUARD.md` and its checks** — files: `plugin/docs/GUARD.md` (new),
      `plugin/tests/test_guard.py`, `plugin/tests/test_readme.py`.
      Write GUARD.md with the headings from Approach → GUARD.md. Content requirements:
      threat model per AC14 (agent mistakes and shortcuts; not deliberate evasion; best
      effort, not a sandbox); for each layer — covers / runs / bypassed (guard: every Bash
      call of an agent session with the plugin loaded, bypassed by a session without the
      plugin, Edit/Write, scripts, interpreters; pre-push: every `git push` from a clone with
      `core.hooksPath` set, bypassed by `--no-verify` or a clone without it; rulesets:
      server side, `main` and release tags, cover everyone, do not cover tag creation or a
      PR merge with zero required approvals, `stable` bypassable by the Admin role); the
      deny table only with rows that qualified in step 3, the measurement line with the
      recorded date and version; fail-open (missing `.claude/workflow.json`, invalid
      configuration, missing `python3` → warning on stderr, exit 0); known limits per AC15
      with `docs/BACKLOG.md` (Guard rows: Alembic, `gh api -X DELETE`, the new AC24 row) and
      `docs/ROADMAP.md` Stage 5 (`protectedBranches`, `stable`) references; no consumer
      project or domain names.
      In `test_guard.py` add: `GUARD_DOC = BIN.parent / "docs" / "GUARD.md"`, a
      `deny_table_rows()` parser (section between `## Deny rules versus the guard` and the
      next `\n## `; table lines starting with `|`, header and separator skipped; cells split
      on unescaped `|`, `\|` unescaped; each cell's single code span extracted — a row
      without three code spans fails the test);
      `test_the_deny_table_has_at_least_five_rows`;
      `test_every_deny_table_command_is_refused(on_feature, command, rule, fragment)`
      parametrized over the rows (reason not `None`, `fragment in reason`, `rule` starts
      with `Bash(`); `test_guard_md_records_the_deny_measurement` (regex
      `Measured on \d{4}-\d{2}-\d{2} with Claude Code \d+\.\d+\.\d+` in that section);
      `test_guard_md_has_the_required_sections` (the seven headings);
      `test_guard_md_names_the_known_limits` (in `## Known limits`: `Alembic`, `stable`,
      `Edit`, `Write`, `script`, `interpreter`, `function`, `gh api -X DELETE`,
      `docs/BACKLOG.md`).
      In `test_readme.py` add `strip_code(text)` (drops fenced blocks and inline code spans)
      and `test_no_polish_outside_code` parametrized over `README.md` and `docs/GUARD.md`
      (no character of `ąćęłńóśźżĄĆĘŁŃÓŚŹŻ` left) — mark the `README.md` case
      `pytest.mark.xfail(strict=True)` until step 5 removes it.
      Automatic verification:
      `uv run pytest -q -p no:cacheprovider plugin/tests/test_guard.py -k "guard_md or deny_table"`
      `uv run pytest -q -p no:cacheprovider plugin/tests/test_no_domain_references.py`
      `uv run pytest -q -p no:cacheprovider plugin/tests/test_readme.py`
      Negative check (then revert): add a table row with `git status` → the table test goes
      red; remove it.

- [x] 5. **`plugin/README.md` in English; references to it** — files: `plugin/README.md`,
      `plugin/tests/test_readme.py`, `CLAUDE.md`, `README.md`.
      Translate per Approach → README; keep every configuration key, default, status name,
      `RESULT` field, metric key and command literal byte-identical; keep the `RESULT` block
      identical to the one in `plugin/skills/ship/SKILL.md`; the guard section becomes the
      summary with the link to `docs/GUARD.md`; the full `gh api -X DELETE` list and the
      compound-refusal paragraph move to GUARD.md (step 4 content, add there if missing).
      `test_readme.py`: switch anchors to `## Installation`, `### Command guard`,
      `## Workflow metrics`; `"brak sekcji"` → `"no section"`; `pipeline@<nazwa>` →
      `pipeline@<name>`; `"izolacji wersji"` → `"version isolation"`; drop the step-4 xfail;
      add `test_the_readme_keeps_its_sections` (the twelve English headings),
      `test_every_status_is_documented` (the six status names of the status table: `spec-draft`,
      `spec-ready`, `plan-draft`, `plan-approved`, `implemented`, `done` each in a table row
      starting with `` | ` ``), `test_the_result_block_matches_the_contract` (the fenced block
      starting with `RESULT: DONE | ESCALATE` in the README equals the one in
      `skills/ship/SKILL.md`), `test_the_guard_section_links_guard_md`
      (`](docs/GUARD.md)` in the `### Command guard` section and the target exists).
      `CLAUDE.md`: `plugin/README.md` → Instalacja → `plugin/README.md` → Installation.
      Root `README.md`: `Documentation (currently in Polish): …` → `Documentation:
      [plugin/README.md](plugin/README.md); the command guard, its layers and its limits:
      [plugin/docs/GUARD.md](plugin/docs/GUARD.md).`
      Automatic verification:
      `uv run pytest -q -p no:cacheprovider plugin/tests/test_readme.py plugin/tests/test_stage_skills.py plugin/tests/test_stage_contract.py`
      `grep -n "Instalacja" CLAUDE.md` → no output; `grep -n "Installation" CLAUDE.md` → 1 line
      `grep -n "in Polish" README.md` → no output
      `grep -c "^| \`" plugin/README.md` equals the count before translation (record it
      first with `git show HEAD:plugin/README.md | grep -c "^| \`"`)

- [x] 6. **Release 0.3.4** — files: `plugin/.claude-plugin/plugin.json`, `plugin/CHANGELOG.md`.
      Version `0.3.4`. New top section `## 0.3.4` (Polish, like the file) with a one-line
      summary, `**wpływ na konsumenta:**` naming the new refusals (push refspec built from
      variables or command substitution that the guard cannot resolve — e.g.
      `git push origin HEAD:$(git branch --show-current)` and `git push $(git remote)
      <branch>`; a prefix assignment for the push's own refspec; `git -c alias.*`;
      persistent alias writes including `--unset` and `--rename-section … alias`; removing
      or renaming the `core` section) and
      that no migration step is needed; `### Naprawione` listing AC1–AC12 (refspecs resolved
      or refused, empty value = current branch, prefix assignments, variable remote,
      `core.hooksPath` reads allowed, alias refusals); `### Zmienione`/`### Dodane` for
      `docs/GUARD.md` and the English README.
      Automatic verification:
      `uv run pytest -q -p no:cacheprovider plugin/tests/test_readme.py -k changelog`
      `python3 -c "import json;assert json.load(open('plugin/.claude-plugin/plugin.json'))['version']=='0.3.4'"`
      `claude plugin validate --strict plugin/ && claude plugin validate --strict .`

- [x] 7. **Project documents** — files: `docs/DECISIONS.md`, `docs/CONVENTIONS.md`,
      `docs/BACKLOG.md`, `docs/ROADMAP.md`.
      `DECISIONS.md`: append four rows (date of implementation) — `plugin/README.md` in
      English ahead of the skills, amending 2026-09-17 (skills and agents stay Polish until
      Stage 8); push refspecs resolved like removal paths with shell expansion semantics and
      refused when unresolvable; command-line and persistent git aliases refused, scripts,
      interpreters and functions documented as limits; GUARD.md's deny table parsed and run
      through the guard by a test, its deny side measured with `claude -p --safe-mode
      --settings` (record date, version and the qualifying count). Each row with rejected
      alternatives and rationale from the SPEC table.
      `CONVENTIONS.md` → Language: skills and agents Polish until translated (Stage 8);
      `plugin/README.md` and `plugin/docs/` English.
      `BACKLOG.md` → P3: a `Guard` row — scripts written to files, interpreters (`python3
      -c`, `node -e`), shell functions from earlier calls, and git configuration channels
      the guard does not parse (`--config-env`, `GIT_CONFIG_*`, `include.path`/`includeIf`);
      trigger: the first session seen reaching a guarded action through one of them;
      context: GUARD.md known limits, `pre-push` and rulesets behind it on `main`.
      `ROADMAP.md` → Stage 3: tick the three open items (they already link the spec); extend
      the 0.3.4 sub-bullets with the alias refusals.
      Automatic verification:
      `grep -c "GUARD.md" docs/DECISIONS.md` ≥ 1; `grep -n "alias" docs/DECISIONS.md` ≥ 1 line;
      `grep -n "refspec" docs/DECISIONS.md` ≥ 1 line
      `grep -n "plugin/README.md" docs/CONVENTIONS.md` shows the English wording
      `grep -n "interpreters" docs/BACKLOG.md` → 1 line in the P3 table
      `sed -n '/## Stage 3/,/## Stage 4/p' docs/ROADMAP.md | grep -c "\- \[ \]"` → 0

- [x] 8. **Full verification and end-to-end** — files: this PLAN (results).
      Run the automatic end-to-end section below, record its output under Results; tick the
      Definition of Done; set SPEC status `implemented` (by /pipeline:implement).
      Automatic verification: `bash scripts/check.sh` → `ALL GREEN`.

## Risks and traps

- **The session's own guard (0.3.3) analyses your commands.** Anything with `$(…)`,
  backticks or `git push … main` in a Bash command line may be refused before it runs. Put
  hook payloads and the measurement prompts in files in the scratchpad and pass them via
  stdin or a script; never try to get around a refusal on the real repository.
- **`claude -p` from a stage subagent.** `claude -p` is not in this repository's
  `permissions.allow`; if the implementer cannot run it without a prompt, that is an
  escalation (the owner accepted the measurement, not a way around permissions).
- **Measurement validity.** Without `--safe-mode` the installed guard refuses first and the
  `deny` rule is never consulted, so every row would look "not caught" for the wrong reason.
  The baseline run and the control row are what make the result trustworthy; do not skip
  them. Commands must match verbatim — the model may "fix" a command; re-run, never edit
  the table by hand.
- **Measurement safety.** The sandbox must have no GitHub remote and `GH_REPO` unset;
  `gh pr merge` then fails locally, pushes go to the local bare repo. Never run the harness
  from this repository.
- **Module-scoped `repo` fixture.** Tests switch branches on a shared repository; a test
  that needs `main` must switch explicitly (use `on_main`), and the empty-variable test must
  not leave the repo on `main` for a later test that assumes otherwise — existing fixtures
  switch on every use, so always depend on one of them.
- **Variables from the hook's process environment.** The hook resolves `$NAME` from the
  Claude Code process environment, which may differ from the Bash tool's shell; the removal
  rule already accepts this. Not changed here.
- **Consumer impact.** `git push origin HEAD:$(git branch --show-current)` and
  `git push -u origin "$BRANCH"` in skills or habits now get refused; check
  `grep -rn 'git push' plugin/skills plugin/agents plugin/templates` for such forms in step
  1 and, if any exist, report them — do not rewrite skills in this spec without an entry in
  Deviations.
- **Alias unset is refused.** `git config --unset alias.p` counts as a write; stated in the
  CHANGELOG and GUARD.md.
- **README drift.** The translation must not change a default or key; the existing
  parametrized `test_every_config_key_is_documented_with_its_default` catches it, and the
  table-row count check in step 5 catches a lost row.
- **`test_no_domain_references` covers `plugin/docs/`** automatically (it walks `plugin/`);
  also avoid the literal `scripts/check.sh` in GUARD.md — that pattern is on the list.
- **CHANGELOG language.** The 0.3.4 section is Polish (SPEC → Out of scope); the English
  documents must not copy Polish phrasing.

## End-to-end verification

### Automatic (performed by /pipeline:implement)

1. The hook itself on the working tree, in a scratch repo on a feature branch (payload files
   written with Write, each with `"cwd"` set to the scratch repo — the guard reads the
   branch from the payload's `cwd`, not from `CLAUDE_PROJECT_DIR` — and `CLAUDE_PROJECT_DIR`
   set to the scratch repo too):
   `plugin/bin/guard < payload.json; echo $?` for:
   - `B=main; git push origin $B` → exit 2, stderr names pushing to main;
   - `git push origin $(echo main)` → exit 2, stderr contains `spell the branch out`;
   - `B=feat/x git push origin $B` → exit 2;
   - `E=; git push origin $E` → exit 0 (feature branch);
   - `B=feat/002-x; git push origin HEAD:$B` → exit 0;
   - `git config core.hooksPath` → exit 0; `git config core.hooksPath x` → exit 2;
   - `git -c alias.p=push p origin main` → exit 2, stderr contains `alias cannot be
     verified`.
2. The deny table end to end: `uv run pytest -q -p no:cacheprovider
   plugin/tests/test_guard.py -k deny_table` → all rows pass.
3. `claude plugin validate --strict plugin/` and `claude plugin validate --strict .` → valid.
4. `bash scripts/check.sh` → `ALL GREEN`.

### Manual (performed by the owner)

1. After tagging `pipeline--v0.3.4` and moving `stable`, update the user install and open a
   new session on a feature branch: `B=main; git push origin $B` is refused with the
   push-to-main reason, and `git config core.hooksPath` prints the value.

### Results

#### Deny measurement (step 3)

- Date 2026-09-21, Claude Code 2.1.272. Mode: `claude -p --safe-mode --output-format
  stream-json --verbose --allowedTools Bash --max-turns 3 --settings <json>` (`--max-turns`
  was accepted; `--safe-mode` was enough — the fallback `--setting-sources local` was not
  needed). Every baseline run of a guard-refused command `ran`, which proves hooks were off.
- `~/.claude/settings.json` has no `permissions` entries, so no user-level `deny` rule
  could interfere.
- Sandbox: a fresh `git init -b main` repository with two commits, `origin` a local bare
  repository, branch `feat/x`, `GH_REPO` unset — recreated before every run. Harness
  (scratchpad, not committed): `measure-deny.sh` → `measure.py`.
- Control `gh pr merge 12 --squash` vs `Bash(gh pr merge*)`: baseline `ran`, with rule
  `denied` — `--settings` takes effect.

| candidate | rule | baseline | with rule | qualifies |
|---|---|---|---|---|
| `gh pr merge 12 --squash` (control) | `Bash(gh pr merge*)` | ran | denied | no (control) |
| `env gh pr merge 12 --squash` | `Bash(gh pr merge*)` | ran | denied | no |
| `bash -c 'gh pr merge 12 --squash'` | `Bash(gh pr merge*)` | ran | ran | yes |
| `echo $(gh pr merge 12)` | `Bash(gh pr merge*)` | ran | denied | no |
| `B=main; git push origin $B` | `Bash(git push origin main*)` | ran | denied | no |
| `git push origin HEAD:main` | `Bash(git push origin main*)` | ran | ran | yes |
| `git push -u origin main` | `Bash(git push origin main*)` | ran | ran | yes |
| `git -C . push origin main` | `Bash(git push origin main*)` | ran | ran | yes |
| `git -c alias.p=push p origin main` | `Bash(git push origin main*)` | ran | ran | yes |
| `eval 'git reset --hard HEAD~1'` | `Bash(git reset --hard*)` | ran | ran | yes |
| `git clean -xdf` | `Bash(git clean -f*)` | ran | ran | yes |
| `git -c core.hooksPath=/dev/null push origin feat/x` | `Bash(git config core.hooksPath*)` | ran | ran | yes |
| `command git push origin main` | `Bash(git push origin main*)` | not measurable (model changed the command twice) | denied | no |
| `git push origin feat/x:main` | `Bash(git push origin main*)` | ran | ran | yes |
| `git push origin refs/heads/main` | `Bash(git push origin main*)` | ran | ran | yes |
| `git push origin feat/x --no-verify` | `Bash(git push --no-verify*)` | ran | ran | yes |
| `git reset -q --hard HEAD~1` | `Bash(git reset --hard*)` | ran | ran | yes |
| `git push -f origin feat/x` | `Bash(git push --force*)` | ran | ran | yes |
| `git push origin +feat/x` | `Bash(git push --force*)` | ran | ran | yes |

14 rows qualify; each is refused by the step-1/2 guard on a feature branch (checked with a
scratch script importing `plugin/bin/guard.py`). The last seven candidates were measured
up front, beside the planned twelve, rather than only after a shortfall — see Deviations.

#### Automatic end-to-end (step 8)

1. Hook on the working tree (`plugin/bin/guard` with payload JSON on stdin, `cwd` and
   `CLAUDE_PROJECT_DIR` = a scratch repository on `feat/002-x`, no `workflow.json`):
   `B=main; git push origin $B` → exit 2, "pushing to main"; `git push origin $(echo main)`
   → exit 2, "spell the branch out" with `$(...)`; `B=feat/x git push origin $B` → exit 2;
   `E=; git push origin $E` → exit 0; `B=feat/002-x; git push origin HEAD:$B` → exit 0;
   `git config core.hooksPath` → exit 0; `git config core.hooksPath x` → exit 2;
   `git -c alias.p=push p origin main` → exit 2, "alias cannot be verified". All 8 as
   expected. Observation: for `git push origin $(echo main)` the compound refusal adds "the
   other 1 of 2 parts passed" — the lexer's leftover `echo main )` counts as a part; the
   refusal itself is right (pre-existing compound-message behaviour, not changed here).
2. `uv run pytest -q -p no:cacheprovider plugin/tests/test_guard.py -k deny_table` →
   15 passed (14 table rows + the row count).
3. `claude plugin validate --strict plugin/` and `.` → passed (in `check.sh` too).
4. `bash scripts/check.sh` → `ALL GREEN` (727 passed).

## Definition of Done

- [x] all steps ticked
- [x] `bash scripts/check.sh` fully green
- [x] end-to-end verification (automatic) done, result recorded here
- [x] `docs/ROADMAP.md` updated; `docs/DECISIONS.md`, `docs/CONVENTIONS.md`,
      `docs/BACKLOG.md` updated
- [x] spec status: `implemented`

## Owner decisions

_(appended by /pipeline:ship or a stage on escalation: date, stage, question, decision)_

## Review log

### 2026-09-21 — /pipeline:plan-review

Findings (severity counted before the fixes; blockers 0, majors 2, minors 5):

| id | severity | finding | change |
|----|----------|---------|--------|
| R1 | major | Push expansion ignored field splitting: `B="origin main"; git push $B` and `B="feat/x main"; git push origin $B` would pass on a feature branch while the shell pushes `main` (tokenizer measured: the assignment token is `B=origin main`). Contrary to AC1's intent | Approach → Push refspecs point 2 now splits each expansion on whitespace (which also subsumes the empty-value rule of AC4); step 1 gets `test_a_split_push_variable_is_checked_word_by_word` |
| R2 | major | A command substitution in the remote position truncates the push segment: `git push $(git remote) main` tokenizes to `git push $` plus a separate "command" `main` (measured), so the plan's "remote is not checked" lets it through while the shell pushes `main` | new point 0: any push positional ending in `$` is refused with `UNRESOLVED_REFSPEC`; step 1 test `test_a_substitution_in_the_remote_position_is_refused`; CHANGELOG consumer impact and owner summary name the new refusal |
| R3 | minor | `config_access` read only the first positional, so `--remove-section core` (drops `core.hooksPath`) and `--rename-section x alias` (writes persistent aliases) passed and were only documented | section operations return every positional; `core`/`alias` sections refused; step 2 test added; the limit dropped from GUARD.md/BACKLOG lists, `include.path`/`includeIf`, `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_PARAMETERS` added instead |
| R4 | minor | English README headings listed without the code spans the Polish headings carry — test anchors and README could disagree | exact heading lines given |
| R5 | minor | AC15 names "scripts written to files", the known-limits test did not assert it | `script` added to the asserted tokens |
| R6 | minor | `--max-turns` is not in `claude --help` of 2.1.272; no fallback if `--safe-mode` also drops `--settings` | step 3c: drop `--max-turns` if rejected; fallback `--setting-sources local`; the mode used is recorded |
| R7 | minor | E2E hook runs: the guard reads the branch from the payload's `cwd`, not `CLAUDE_PROJECT_DIR` | payloads carry `"cwd"` |

Checked and found correct (no need to redo): AC→steps matrix covers AC1–AC25 with named
tests or greps; `self.env` vs segment-local `env` is the right split (prefix/wrapper
assignments live only in the local map; conditional assignments become `$NAME` in
`self.env`, so `false || B=feat/x; …` stays unresolved); `$(…)` and backtick tokenization as
described (measured); `git config core.hooksPath ""` yields an empty token, so the legacy
two-positional write rule holds; `git -c alias.x='!…'` arrives as one token; `HOOKS_PATH`
contains `core.hooksPath` (AC9 fragment); the compound refusal keeps the inner reason, so
fragment assertions hold for `B=main; …` forms; `--safe-mode` exists in Claude Code 2.1.272
and keeps permissions; no user-level `deny` rules in `~/.claude/settings.json` today;
`README.md` and `skills/ship/SKILL.md` `RESULT` blocks are byte-identical now; the version
is pinned only in `plugin/.claude-plugin/plugin.json`; `test_no_domain_references` walks
`plugin/docs/` automatically; skills push only literal branches
(`git push -u origin feat/NNN-<slug>`), so no skill is broken by the new refusals; no new
dependency and no migration (SPEC → Owner decisions).

Verdict: the plan is ready — both majors were fixable inside the plan's own approach (same
step, same files, no scope change beyond what AC1/AC2/AC11 already demand), no blocker
remains and nothing requires an owner decision.

## Deviations

- Step 3: the extra candidates the plan reserves for a shortfall (fewer than 5 qualifying
  rows) were measured in parallel with the planned twelve, to save a second round of
  `claude -p` runs; the planned twelve alone gave 8 qualifying rows. More measured rows,
  same method — no scope change. The harness is a small Python script behind
  `measure-deny.sh` (stream-json parsing is simpler in Python).

## Final review

### 2026-09-21 — /pipeline:final-review (report)

Material: `git diff origin/main...HEAD` (15 files, +1829/−250). Three independent
perspectives (SPEC/PLAN compliance, quality, tests); every finding below was re-checked
with `guard.evaluate` on a scratch repository, on `main` and on a feature branch, and — where
it says "pre-existing" — against the `origin/main` guard (0.3.3). `bash scripts/check.sh`:
ALL GREEN (727 passed); ruff and black clean.

#### AC → evidence

| AC | Evidence | ok |
|----|----------|----|
| AC1 | `test_guard.py::test_a_push_variable_resolving_to_main_is_refused` (all 7 forms), `test_hook_refuses_a_push_variable_resolving_to_main`; `Analyzer.push` | ok |
| AC2 | `test_an_unresolvable_push_refspec_is_refused` (5 cases, reason names the refspec) | ok |
| AC3 | `test_a_prefix_assignment_does_not_resolve_its_own_push` (main + feature) | ok |
| AC4 | `test_an_empty_push_variable_pushes_the_current_branch` | ok |
| AC5 | `test_a_push_variable_resolving_to_a_feature_branch_is_allowed` | ok |
| AC6 | `test_a_variable_remote_with_literal_refspecs` | ok |
| AC7 | only additions in `test_guard.py`; `test_case_count_not_regressed` | ok |
| AC8 | `test_reading_core_hooks_path_is_allowed` (7); `config_access` | ok |
| AC9 | `test_writing_core_hooks_path_is_refused` (9) | ok |
| AC10 | `test_a_command_line_alias_is_refused` (incl. `Alias.P`) | ok |
| AC11 | `test_writing_a_persistent_alias_is_refused`, `test_reading_an_alias_is_allowed`, `test_section_operations_on_core_or_alias_are_refused` | ok |
| AC12 | `test_other_command_line_config_keys_pass` | ok |
| AC13 | `plugin.json` 0.3.4; `CHANGELOG.md` `## 0.3.4` with `wpływ na konsumenta`; `test_changelog_*` | ok |
| AC14 | `plugin/docs/GUARD.md`; `test_guard_md_has_the_required_sections`, `test_no_polish_outside_code[docs/GUARD.md]` | ok |
| AC15 | `test_guard_md_names_the_known_limits`; links to BACKLOG / Stage 5 | ok |
| AC16 | 14 rows; `test_the_deny_table_has_at_least_five_rows`, `test_every_deny_table_command_is_refused` | ok |
| AC17 | Results → deny measurement (14 `yes` rows = GUARD.md table); `test_guard_md_records_the_deny_measurement` | ok |
| AC18 | `test_no_domain_references.py` walks `plugin/docs/` | ok |
| AC19 | `test_no_polish_outside_code[README.md]`; `## Decyzje właściciela` in a code span | ok |
| AC20 | `test_the_readme_keeps_its_sections`, `test_every_status_is_documented`, `test_the_result_block_matches_the_contract`, key/default/metric tests | ok |
| AC21 | README guard section (summary + link); `test_the_guard_section_links_guard_md`, `test_the_guard_section_states_the_migration_scope` | ok |
| AC22 | `test_readme.py` on English anchors; `CLAUDE.md` → Installation; root `README.md` | ok |
| AC23 | 4 rows in `docs/DECISIONS.md`; `docs/CONVENTIONS.md` → Language | ok |
| AC24 | `docs/BACKLOG.md` P3 Guard row with a trigger | ok |
| AC25 | Stage 3 ticked in `docs/ROADMAP.md`; check.sh green | ok |

Plan steps 1–8 ticked with evidence; the single deviation (extra deny candidates measured
up front) is justified; nothing outside the plan's file list; no new dependency, no
migration. Owner decisions from the SPEC (AC6, AC11, AC16) are respected.

#### Findings

No blocker: none of the findings is a regression against 0.3.3 (checked on the old
guard), and on `main` the `pre-push` hook and the rulesets stay behind the guard. They are
holes in the claim this spec makes ("a variable is expanded the way the shell does it",
"git aliases are refused"), or cheap leaks next to the code it rewrote.

| id | severity | where | scenario (input → wrong behaviour) | fix |
|----|----------|-------|-------------------------------------|-----|
| F1 | worth fixing | `plugin/bin/guard.py` `segment`/`export`/`run` (~:314, :362–398); `plugin/docs/GUARD.md:52`; `plugin/CHANGELOG.md:27` | The guard keeps a "known" value where the shell drops or changes it, so on `main` these pass while the shell pushes `main`: `true \|\| export B=feat/x; git push origin $B` (conditional `export` applied unconditionally), `(B=feat/x); git push origin $B`, `B=feat/x \| true; git push origin $B`, `bash -c 'B=feat/x'; git push origin $B` (nested `run` shares `self.env`), `B=feat/x; bash -c 'git push origin $B'` (non-exported variable handed to the child shell), `B=feat/x; unset B; git push origin $B`; on a feature branch `B=feat/x; for B in main; do git push origin $B; done`, `B=ma; B+=in; …`, `read`/`declare`/`printf -v`, `IFS=…` | conservative: a conditional `export` stores `$KEY`; nested analyzers (`(…)`, pipeline parts, `bash -c`, `$(…)`) work on a copy and a child shell sees only exported names; a name touched by `for`/`read`/`declare`/`local`/`typeset`/`readonly`/`printf -v`/`unset`/`mapfile`/`NAME+=` becomes unresolved; an `IFS` assignment is refused; tests for each on `main`. Or qualify GUARD.md/CHANGELOG and list the rest in Known limits |
| F2 | worth fixing | `plugin/bin/guard.py:535–541` (`push`) | Destructive-flag checks run on raw arguments, not expanded words: `B=-f; git push origin $B`, `B=--delete; git push origin $B feat/x`, `B=--mirror; …` → allowed (a force/delete push of a feature branch; nothing else stops it). Pre-existing, but the new expansion makes it a one-line fix | run the force/mirror/delete checks over the expanded words too (or refuse an expanded word starting with `-`); tests |
| F3 | worth fixing | `plugin/bin/guard.py` `push`, `ref_name` (:881); `-c` parsing (:486–490) | Pushes that include `main` without spelling it pass on a feature branch: `git push --all origin`, `--branches`, `git push origin '*:*'` / `'refs/heads/*:refs/heads/*'`, brace expansion `git push origin {feat/x,main}` / `HEAD:ma{in,}`, git DWIM `git push origin HEAD:heads/main` (verified live: lands on `main`), `git -c remote.origin.push=HEAD:main push origin`. Pre-existing; not in Known limits | refuse `--all`/`--branches`, refspecs with `*`/`?`/`{`, strip `heads/` in `ref_name`, refuse `-c remote.*.push` and `-c push.default`; tests. Whatever stays open → GUARD.md Known limits |
| F4 | worth fixing | `plugin/bin/guard.py:543–549` (`push`) | Value-taking push options shift the remote into the refspec slot: on `main` `git push -o ci.skip origin` / `--push-option ci.skip origin` → allowed (pushes `main`); false refusals `git push -o ci.skip $REMOTE feat/002-x` and `git push origin feat/x -o 'ci.variable=A=$B'` | skip the values of `-o`/`--push-option`/`--repo`/`--receive-pack`/`--exec` (like `CONFIG_VALUE_OPTIONS`) before picking the remote; tests |
| F5 | worth fixing | `plugin/bin/guard.py:108–110`, `config_access` | `git config --edit`, `-e`, `git config edit` are classified as writes but name no key, so neither check fires → allowed; an editor command (`GIT_EDITOR=…`) can set `core.hooksPath` (verified) or an alias. The set entries imply coverage that is not there | refuse `--edit`/`-e`/`edit` with the `core.hooksPath` reason; test |
| F6 | worth fixing | `plugin/docs/GUARD.md:39`, `plugin/README.md:195` | Docs say "git aliases" are refused, but an alias already in a config file runs unchecked: `git p origin main` with `alias.p=push` configured → allowed. Known limits does not name it | add the limit to GUARD.md (and "aliases defined on the command line or written" in README); optionally refuse a non-builtin `sub` that `git config --get alias.<sub>` resolves |
| F7 | nit | `plugin/bin/guard.py:494`, `:537` | Git accepts abbreviated long options: `git push --del origin feat/x`, `--mir`, `--no-verif`, `git commit -n` → allowed. Pre-existing | match unambiguous prefixes; `-n` for `commit`/`merge` as `--no-verify` — or backlog |
| F8 | nit | `plugin/docs/GUARD.md:157–159` | "guardrail files are protected there by Claude Code's own `ask` rules" — the consumer template (`plugin/templates/settings.json:30–33`) asks only for `.claude/settings*.json` and `scripts/git-hooks/**`, not `.claude/workflow.json` or the plugin directory | name exactly what the template's `ask` rules cover; template change → backlog |
| F9 | nit | `plugin/bin/guard.py:543–549` | `git push $R` (unresolved remote, no refspec) → allowed; if `$R` holds `origin main` in the Bash tool's shell, it pushes `main`. AC6 covers a variable remote *with* literal refspecs only | refuse an unresolved remote with no refspec, or document it |
| F10 | nit | `plugin/tests/test_guard.py:891`, `:909–913`, `:433ff` | Test gaps: the deny-table parser skips an indented row (`line.startswith("\|")`); no sanity check that a row's command does not start with its own rule's prefix; no cases for `--unset alias.p`/`--add alias.p` (claimed in GUARD.md:173), resolved `+$B`/`:$B`, `export B=main; …`, a hook-environment variable in a refspec, `Core.HooksPath`, `--type bool core.hooksPath x` | `lstrip()` + row-count assertion; prefix sanity check; add the listed cases |
| F11 | nit | `plugin/bin/guard.py:545` | `git push origin feat/x$` (literal trailing `$`) → refused as `feat/x$(...)` — misleading reason, fails safe | word the reason neutrally, or check the lexer cut explicitly |

#### Rejected

- GUARD.md row `git -c core.hooksPath=/dev/null …` against `Bash(git config core.hooksPath*)`
  "shows a poorly chosen rule" — the row is measured and is exactly the point of the table:
  a string rule matches one spelling of an action.
- `git push origin 'HEAD:$B'` and `git push -u origin $(git branch --show-current)` refused
  — the fail-safe cost the SPEC decision table and `docs/DECISIONS.md` accept (shlex drops
  quoting); the option-value case is kept in F4.
- `test_readme.py` `strip_code` ignores `~~~` fences and double-backtick spans — only false
  positives are possible, and neither README nor GUARD.md uses them.
