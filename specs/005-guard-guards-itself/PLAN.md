# PLAN 005 — A guard that guards itself and the release channel

## Owner summary

- **Approach:** Four additions to `plugin/bin/guard.py`, each with its own new pytest file
  so `plugin/tests/test_guard.py` stays byte-for-byte unchanged (AC2):
  `protectedBranches` joins `main`/`master` in one `Rules.protected_branches` set that every
  existing branch rule reads; a `claude plugin …` rule refuses detaching this plugin by
  target (name read from its own `plugin.json`, marketplaces from the install state, the
  cache layout and the enclosing `marketplace.json`); a path-based guardrail check covers
  the guard's own directory wherever it lies plus `installed_plugins.json` and
  `known_marketplaces.json`; `gh api` `POST`/`PUT`/`PATCH` on the owner's ground is refused
  by endpoint segment, like `DELETE`. Then documents, the 0.4.0 bump, and — last — this
  repository's `workflow.json`/`settings.json`.
- **Main risks:** the path-based rule must judge only what a command *writes*: a `cp`
  *source* inside the plugin is a read — `/pipeline:init` copies every template with
  `cp ${CLAUDE_PLUGIN_ROOT}/templates/…` in every consumer (plan review, B1), so `cp`,
  `install` and `ln` are judged by their destination only. The deny-table measurement (AC17) cannot use an isolated
  `CLAUDE_CONFIG_DIR` for the nested session itself (it is then logged out — probed while
  planning), so the isolation sits in a `claude` stub on `PATH` that runs the measured
  command against an isolated config dir; a probe must prove the isolation before any
  measured command runs. Step 11 edits files on this repository's `ask` list; a stage
  subagent may be unable to approve that prompt and would then escalate with the exact diff.
- **One skill edit:** `plugin/skills/init/SKILL.md` gets one clause (step 4: do not write
  `protectedBranches`). The SPEC's context says no skill is touched, but AC7 requires both
  that `workflow.example.json` shows the key and that init writes none, and init builds
  `workflow.json` from that example — without the clause AC7 is not guaranteed.
- **New dependency:** no.
- **Data migration:** no (the new key is optional; existing configurations are unchanged).
- **Manual scenarios for the owner:** 1 set, after merge — the 0.4.0 canary checks the PR
  description lists (AC26): D4, the plugin count, two harmless refusal probes.

## Approach

### Existing patterns reused

- `Rules` (`plugin/bin/guard.py`) already carries every configured piece of the guard; the
  new state (protected branches, plugin roots, config dir) goes there, computed once per
  call.
- Variable expansion and "unresolved = refused": `expand_variables` and the pattern of
  `check_path` / `gh api -X DELETE` (`"$" in …` → `GuardError`).
- Segment-name matching of the owner's ground: `owner_deletion` and `API_OWNER_DELETIONS`;
  the write rule reuses the same repository/organisation width logic.
- Section-wise config fallback: `workflow_config.load_sections` already drops a faulty
  top-level key with a warning; adding `protectedBranches` to `SCHEMA` as `list` gives AC1
  for free (`check_list` enforces `str` items with the existing messages).
- Tests: the fixtures of `plugin/tests/test_guard.py` (`make_repo`, `git`, `evaluate`,
  `BLOCKED_ANYWHERE`, `ALLOWED_ANYWHERE`) are imported by the new files
  (`from test_guard import …` — `plugin/tests` has no `__init__.py`, pytest's default
  `prepend` import mode puts the directory on `sys.path`, and the module object is the
  same one pytest collects). Every new test that touches the claude rules or the install
  state passes an explicit `CLAUDE_CONFIG_DIR` under `tmp_path` so the owner's real
  `~/.claude` is never read.
- The deny-versus-guard table is parsed and run through the guard by
  `test_every_deny_table_command_is_refused` (unchanged); new rows only have to be refused
  in that test's environment (`CLAUDE_PROJECT_DIR` only).

### Protected branches (AC1–AC7)

- `workflow_config.SCHEMA["protectedBranches"] = list`; **not** added to `defaults()`
  (absent = only `main`/`master`; the README row reads "absent", like `migrations`, so
  `test_every_config_key_is_documented_with_its_default` is not involved).
- `guard.py`: `DEFAULT_PROTECTED = {"main", "master"}` (renamed from `PROTECTED_BRANCHES`,
  or kept with that name — the implementer picks; no test imports it).
  `Rules.protected_branches = DEFAULT_PROTECTED | {name for name in configured if name}` —
  empty strings are dropped, because `git branch --show-current` prints `""` on a detached
  HEAD and `""` in the set would protect every detached checkout.
- Every use of the constant switches to `self.rules.protected_branches`: `git branch`
  rewrite, `update-ref`/`symbolic-ref`, `on_protected`, `push()` targets, and `check_gh`
  (which gains a `rules` parameter).
- Messages: for `main`/`master` the 0.3.4 texts stay exactly (`MAIN_OWNER_ONLY`,
  "pushing to main", "on main only `git pull --ff-only` is allowed", "deleting, renaming
  or resetting main") — existing tests assert them. A configured branch gets
  `CHANNEL_OWNER_ONLY = "{branch} is listed in protectedBranches (.claude/workflow.json)
  and only the owner changes it; work on a feature branch"` and the same shapes with its
  name: "pushing to stable: …", "on stable only `git pull --ff-only` is allowed",
  "deleting, renaming or resetting stable is off limits", "`git commit` on stable: …".
  A helper `owner_only(branch) -> str` and a display rule: a push that hits `main`/`master`
  names "main" (0.3.4 behaviour, also for `master`); otherwise it names the configured
  branch it hit (the first in sorted order when several).
- `push()` gets the current branch name instead of the `on_protected` bool, so a bare push
  on `stable` can name `stable`.
- `gh api` write regex: keep `refs/heads/(main|master)\b` as is, and add
  `refs/heads/(?:<escaped configured names>)(?=$|[/?#])` — exact names (AC6), so
  `refs/heads/stable-next` is not caught by `["stable"]`.
- Not touched: `scripts/git-hooks/pre-push`, `plugin/templates/pre-push` (AC7).
- `plugin/skills/init/SKILL.md` step 4, the `.claude/workflow.json` bullet: one Polish
  clause — `klucza \`protectedBranches\` nie zapisujesz (kanał wydań chroni właściciel
  ręcznie, po \`/pipeline:init\`)` — pinned by a test that `protectedBranches` appears in
  step 4 (the file's convention: identifiers, not prose).

### Detaching the plugin (AC8–AC10)

Measured while planning on Claude Code 2.1.280: `claude plugin|plugins`;
`disable [options] [plugin]` with `-a, --all` and `-s, --scope <scope>`;
`uninstall|remove [options] <plugin>` with `-s, --scope`, `--keep-data`, `--prune`, `-y`,
`--json`; `marketplace remove|rm [options] <name>` with `--scope <scope>`; `help [command]`
at both levels; `-h, --help` everywhere. (`claude plugin help disable` printed the disable
options — the SPEC's open question: `--all` exists, and a bare `disable` is refused either
way.)

- `segment()`: `elif program == "claude": check_claude(args, self.env, self.rules)`.
  Wrappers, `bash -c`, `eval` and absolute paths already reach it (`unwrap`, `basename`).
- `check_claude`: find the first arg equal to `plugin` or `plugins` (global options may come
  before it); none → return. If any later arg is `-h`/`--help` → return. The first
  positional after it is the subcommand (`help` → return). Option values skipped:
  `-s`, `--scope` (and the `--scope=x` form).
  - `disable`: `-a`/`--all` (or a short cluster containing `a`) → refuse; no positional
    target → refuse; otherwise judge the targets.
  - `uninstall`/`remove`: judge the targets.
  - `marketplace` → next positional `remove`/`rm` → judge the marketplace targets.
  - everything else (`list`, `details`, `validate`, `eval`, `update`, `install`, `i`,
    `enable`, `init`, `prune`, `tag`, `marketplace add|list|update`) → pass.
- Plugin target: `expand_variables`; `$` or `` ` `` left → refuse ("cannot verify a plugin
  name built from variables"); `target.split("@", 1)[0] == plugin name` → refuse.
- Marketplace target: expanded as above; unresolved → refuse; install state unreadable →
  refuse ("cannot read the plugin install state to tell whether <m> is this plugin's
  marketplace"); in `plugin_marketplaces(...)` → refuse.
- Refusal text (fragment asserted by tests and the table): `PLUGIN_INSTALL = "the {name}
  plugin's install is the owner's to change — disabling or uninstalling it, or removing
  its marketplace, switches the guard off; the owner runs that in a terminal"`.
- Identity, computed lazily (only for `claude plugin …`):
  - `plugin roots` = `Path(__file__).resolve().parents[1]` (the running guard's own
    directory) plus `CLAUDE_PLUGIN_ROOT` resolved, when set.
  - `plugin name` = `name` from the first readable `<root>/.claude-plugin/plugin.json`,
    fallback `"pipeline"`.
  - `config dir` = `env["CLAUDE_CONFIG_DIR"]` or `~/.claude`.
  - Resolution order (plan review, m5): (c) and (b) first; a hit refuses without reading
    the install state, so the deny-table rows in the frozen `test_guard.py` (which passes
    no `CLAUDE_CONFIG_DIR`) never read the owner's real `~/.claude`.
  - `plugin_marketplaces(...) -> set[str] | None`: (a) keys `<name>@<m>` of
    `<config dir>/plugins/installed_plugins.json` → `plugins`; a missing file counts as
    empty, an unreadable or malformed one returns `None`; (b) each root laid out as
    `…/plugins/cache/<m>/<name>/<version>` → `<m>`; (c) each root whose parent holds
    `.claude-plugin/marketplace.json` listing a plugin with this name → that manifest's
    `name` (a `--plugin-dir` clone of this repository → `wcz-tools`). (c) is what makes the
    deny-table row `claude plugin marketplace rm wcz-tools` refused deterministically in
    `test_guard.py`'s environment, in CI and in a cache install alike.

### The guard's own files and the install state (AC11, AC12)

- Kept unchanged: `protected_file_pattern` (the regex for `.claude/settings*.json`,
  `.claude/workflow.json`, the inside-project plugin directory) — narrowing it would change
  0.3.4 decisions. `~/.claude/settings.json` (where `enabledPlugins` could switch the
  plugin off) is already matched by it.
- Added: `Rules.guarded_paths` = the plugin roots (realpath) and the install-state files
  `<config dir>/plugins/installed_plugins.json`, `known_marketplaces.json`, plus the same
  two files in the `plugins` directory a cache-layout root sits in (when it differs).
- **What counts as written (plan review, B1).** The new path check gets its own target
  list, narrower than `touched`: for `cp`, `install` and `ln` only the destination — the
  value of `-t`/`--target-directory` when given, else the last non-option argument; the
  sources are reads (`/pipeline:init` step 4 copies `${CLAUDE_PLUGIN_ROOT}/templates/…`
  into the project with `cp` in every consumer, and `ln -s <root>/x link` changes nothing
  in the plugin). `mv`, `tee`, `truncate`, `chmod`, `chown`, `dd`, the removal programs and
  `sed -i`/`perl -i` keep every argument. `dd` operands `of=<path>` (any `key=value` word)
  are judged by their value. Redirect targets that are file-descriptor duplications
  (`2>&1`, `>&2`, `<&-`: a target of digits or `-` after an operator ending in `&`, or
  after `>&`) are skipped — otherwise every `… 2>&1` run from a cwd inside the plugin is
  refused (plan review, M1). The 0.3.4 regex check (`protected_file_pattern`) keeps its
  own, unchanged `touched` list.
- `reject_guardrail_targets(touched, check_hooks, cwd)` gains a path check per target:
  skip a plain option word; for `--opt=value` check the value; `expand_variables`; a target
  still holding `$` is left to the other rules (as today — unknown variables in a write
  target are not refused by this rule; documented as a known limit); `resolve()` against
  the command's cwd (`self.cwd`, or the `-C` directory for `git checkout`/`restore`), then
  `os.path.realpath`. Refused with `GUARDRAIL_FILES` when:
  - the path is within a guarded root or equals a guarded file;
  - the target has glob characters: expand it with `glob` against the cwd (as
    `hook_target_exists` does) and refuse when any match is guarded; only when expansion is
    impossible (braces, `OSError`) fall back to the prefix test — its literal prefix is
    within a guarded root, or a guarded root/file is within that prefix (plan review, m6:
    the bare prefix test refuses `sed -i … *.py` at a project root that holds a
    `--plugin-dir` clone);
  - the program is `mv` or a removal program and a guarded root/file is within the path
    (moving or removing a directory that contains the plugin).
- `GUARDRAIL_FILES` text extends to name the new ground: "guardrail files
  (.claude/settings*.json, .claude/workflow.json, this plugin's directory and its install
  state) change only through Edit/Write with the owner's approval". The fragment
  "guardrail files" that existing tests assert stays.
- Which programs count as writes is unchanged: `MUTATING_PROGRAMS`, `sed -i`/`perl -i`,
  redirects, `git checkout`/`restore`. Reading (`cat`, `grep`, `sed -n`) never reaches the
  check.

### `gh api` writes (AC13–AC15)

- `api_endpoint(args) -> str | None`: the first positional after `api`, skipping options
  with values (`-X`, `--method`, `-H`, `--header`, `-f`, `-F`, `--field`, `--raw-field`,
  `--input`, `-q`, `--jq`, `-t`, `--template`, `--hostname`, `-p`, `--preview`, `--cache`)
  and single words starting with `-` (flags, `--opt=value`, `-XPATCH`).
- `API_OWNER_WRITES` = `API_OWNER_DELETIONS` minus `releases`, `runs`, `deployments`, plus
  `topics` ("repository topics"), `transfer` ("the repository's ownership"),
  `permissions` ("Actions permissions"). `owner_write(endpoint)`: the same
  `repos/<o>/<r>`, `repositories/<id>`, `orgs/<o>` width logic as `owner_deletion`; no rest
  → "the repository's settings" / "the organization's settings"; otherwise a segment **of
  `rest`** (the path after `repos/<o>/<r>`, `repositories/<id>` or `orgs/<o>`) in
  `API_OWNER_WRITES` → its label; with no such prefix (e.g. `user/keys`), every segment,
  as for `DELETE`. Unlike `owner_deletion`, the owner and repository names are not
  scanned — a consumer repository named `pages` or `hooks` would otherwise have every
  comment write refused (plan review, M2). `git/refs` is **not** on the write ground, and a
  `rest` starting with `git/refs` is not scanned for keywords at all (branch creation
  and updates through the API stay open — a branch `fix/hooks` is not "webhooks";
  protected refs stay covered by the ref regex).
- `check_gh`: method `POST`/`PUT`/`PATCH` → endpoint with `$`, `` ` `` or ending in `$`
  (a `$(` the lexer cut) → refuse ("`gh api` write on an endpoint built from variables
  cannot be verified; spell the endpoint out"); `owner_write` hit → refuse
  "`gh api -X <M> <endpoint>`: changing <label> is the owner's call". A method that itself
  holds `$` is judged as both a write and a `DELETE`. Only the endpoint is checked for
  writes — field values (`-f body=…`) are data, so a comment mentioning `secrets` passes.
  The existing `sensitive` regex check (merges, protection, rulesets, protected refs, all
  args) stays as it is, after the new check.
- `DELETE` handling is unchanged.

## AC → steps matrix

| AC | Steps | Proving test |
|----|-------|--------------|
| AC1 | 1, 2 | `test_workflow_config.py::test_protected_branches_*`; `test_guard_protected_branches.py::test_an_invalid_value_falls_back_for_that_key_only` |
| AC2 | 2 | `test_guard.py` unchanged and green (`git diff --exit-code origin/main -- plugin/tests/test_guard.py`); `test_guard_protected_branches.py::test_an_empty_list_decides_like_0_3_4` |
| AC3 | 2 | `test_guard_protected_branches.py::test_main_stays_protected` |
| AC4 | 2 | `test_guard_protected_branches.py::test_a_configured_branch_is_guarded_like_main`, `::test_work_around_a_configured_branch_passes` |
| AC5 | 2 | `test_guard_protected_branches.py::test_the_refusal_names_the_configured_branch` |
| AC6 | 2 | `test_guard_protected_branches.py::test_names_match_exactly` |
| AC7 | 1, 7 | `test_readme.py` (row), `test_init_templates.py::test_workflow_example_covers_every_key_and_validates`, `test_init_skill.py::test_init_does_not_write_protected_branches`; `git diff --exit-code origin/main -- scripts/git-hooks/pre-push plugin/templates/pre-push` |
| AC8 | 3 | `test_guard_detach.py::test_detaching_this_plugin_is_refused` |
| AC9 | 3 | `test_guard_detach.py::test_removing_this_plugins_marketplace_is_refused`, `::test_an_unresolved_marketplace_is_refused` |
| AC10 | 3 | `test_guard_detach.py::test_other_plugin_commands_pass` |
| AC11 | 4 | `test_guard_own_files.py::test_writing_the_plugin_directory_is_refused`, `::test_reading_the_plugin_directory_passes`, `::test_the_running_guards_own_directory_is_guarded`, `::test_a_plugin_dir_clone_inside_the_project_is_guarded`, `::test_copying_out_of_the_plugin_passes`, `::test_descriptor_redirects_inside_the_plugin_pass` |
| AC12 | 4 | `test_guard_own_files.py::test_writing_the_install_state_is_refused`, `::test_reading_the_install_state_passes` |
| AC13 | 5 | `test_guard_api_writes.py::test_a_write_on_the_owners_ground_is_refused` |
| AC14 | 5 | `test_guard_api_writes.py::test_ordinary_writes_and_reads_pass` |
| AC15 | 5 | `test_guard_api_writes.py::test_a_write_on_a_variable_endpoint_is_refused` |
| AC16 | 6 | `test_guard.py::test_guard_md_*` (unchanged); `test_guard_own_files.py::test_guard_md_covers_the_0_4_0_rules` |
| AC17 | 6 | `test_guard.py::test_every_deny_table_command_is_refused`, `::test_guard_md_records_the_deny_measurement`; measurement log in this plan (Results) |
| AC18 | 8 | `test_readme.py::test_install_guide_leaves_detaching_to_the_owners_terminal` |
| AC19 | 11 | `tests/test_documents.py::test_repository_settings_leave_stable_and_detaching_to_the_guard` |
| AC20 | 8 | `tests/test_documents.py::test_claude_md_and_conventions_name_protected_branches` |
| AC21 | 9 | `grep -c` checks in step 9 |
| AC22 | 9 | `grep` checks in step 9; `tests/test_documents.py` |
| AC23 | 10 | `test_readme.py::test_changelog_starts_at_the_manifest_version`, `::test_the_changelog_names_the_consumer_impact` |
| AC24 | 10, 11 | `test_no_domain_references.py`; `bash scripts/check.sh` |
| AC25 | after gate 2 | `bash scripts/eval.sh` receipt; `tests/test_release_gate.py` |
| AC26 | after gate 2 | PR description checklist (below) |

## Steps

- [x] 1. **`protectedBranches` in the schema, the README table and the example** — files:
      `plugin/bin/workflow_config.py`, `plugin/tests/test_workflow_config.py`,
      `plugin/README.md` (configuration table only), `plugin/templates/workflow.example.json`.
      `SCHEMA["protectedBranches"] = list`; not in `defaults()`. The README row and the
      example land in the same step because `test_every_schema_key_reaches_the_table` and
      `test_workflow_example_covers_every_key_and_validates` go red the moment the schema
      grows. README row: `` | `protectedBranches` | absent | extra branch names the guard
      treats exactly like `main`/`master` (which stay protected whatever the list says);
      exact names, no patterns; binds agent sessions only — the `pre-push` hook and
      `/pipeline:init` do not read or write it | `` (after `gitHooksDir`). Example:
      `"protectedBranches": ["stable"]`. Tests:
      `test_protected_branches_is_accepted` (`--check` exit 0 with `["stable"]` and with
      `[]`), `test_protected_branches_must_be_a_list_of_strings` (`"stable"` → "`protectedBranches`
      has to be list"; `["stable", 1]` → "`protectedBranches[1]` has to be str"; `--check`
      exit 1), `test_load_sections_drops_only_a_bad_protected_branches` (other sections
      kept, one problem reported).
      Verification: `uv run pytest -q plugin/tests/test_workflow_config.py plugin/tests/test_readme.py plugin/tests/test_init_templates.py`

- [ ] 2. **Guard: configured protected branches** — files: `plugin/bin/guard.py`,
      `plugin/tests/test_guard_protected_branches.py` (new).
      Implement per Approach → Protected branches. New tests (fixture: `make_repo` with
      `{**WORKFLOW, "protectedBranches": ["stable"]}`, a `stable` branch created, switched
      per test):
      - `test_a_configured_branch_is_guarded_like_main` — parametrized over every refused
        command of AC4 (on a feature branch: the four pushes, `B=stable; git push origin $B`,
        `git branch -D stable`, `git update-ref refs/heads/stable HEAD`,
        `gh api -X PATCH repos/o/r/git/refs/heads/stable -f sha=x`; on `stable`: `git push`,
        `git commit -m x`, `git merge feat/001-x`, `git rebase feat/001-x`, `git pull`);
      - `test_work_around_a_configured_branch_passes` — `git push origin feat/x` on a
        feature branch; `git pull --ff-only` and `git switch -c feat/y` on `stable`;
      - `test_main_stays_protected` — `git push origin HEAD:main` → "pushing to main";
      - `test_the_refusal_names_the_configured_branch` — reasons contain "pushing to
        stable", "on stable only", "resetting stable", and never "main";
      - `test_names_match_exactly` — `git push origin stable-next`,
        `git push origin feat/stable`, `git branch -D stable-next`, a commit on
        `stable-next`, `gh api -X PATCH repos/o/r/git/refs/heads/stable-next -f sha=x` pass;
      - `test_an_empty_list_decides_like_0_3_4` — with `{**WORKFLOW, "protectedBranches": []}`
        every `BLOCKED_ANYWHERE` command is refused with its fragment and every
        `ALLOWED_ANYWHERE` command passes (imported from `test_guard`);
      - `test_an_empty_name_does_not_protect_a_detached_head` — `[""]`, detached HEAD,
        `git commit --allow-empty -m x` passes;
      - `test_an_invalid_value_falls_back_for_that_key_only` — `"protectedBranches": "stable"`
        plus the `production` section: the push to `stable` passes, the push to `main` and
        `curl https://api.example.com` are refused; through `run_hook` the stderr carries
        the "`protectedBranches` has to be list" warning.
      Verification: `uv run pytest -q plugin/tests/test_guard_protected_branches.py plugin/tests/test_guard.py && git diff --exit-code origin/main -- plugin/tests/test_guard.py`

- [ ] 3. **Guard: detaching the plugin** — files: `plugin/bin/guard.py`,
      `plugin/tests/test_guard_detach.py` (new).
      Implement per Approach → Detaching the plugin. Tests (every `evaluate` passes
      `CLAUDE_CONFIG_DIR=<tmp>/config`; a helper writes `installed_plugins.json`):
      - `test_detaching_this_plugin_is_refused` — parametrized: `claude plugin disable
        pipeline@any-m`, `claude plugin disable pipeline`, `claude plugin disable`,
        `claude plugin disable --all`, `claude plugin disable -a`, `claude plugin uninstall
        pipeline@m`, `claude plugins remove pipeline@m`, `claude plugins uninstall
        pipeline@wcz-tools`, each × {no scope, `--scope user`, `-s project`,
        `--scope=local`}; plus the wrappers `env claude plugin disable pipeline@m`,
        `bash -c 'claude plugin uninstall pipeline@m'`, `eval claude plugin disable
        pipeline`, `/usr/local/bin/claude plugins remove pipeline@m`,
        `claude --debug plugin uninstall pipeline@m`, `claude plugin uninstall "$P"`; the
        reason holds "install is the owner's to change";
      - `test_removing_this_plugins_marketplace_is_refused` — `marketplace remove|rm <m>`
        for `<m>` from (a) the install state, (b) a cache-layout `CLAUDE_PLUGIN_ROOT`
        (`<tmp>/config/plugins/cache/cache-m/pipeline/0.4.0` with a copied `plugin.json`),
        (c) the enclosing `marketplace.json` of the working tree (`wcz-tools`, no install
        state);
      - `test_an_unresolved_marketplace_is_refused` — `marketplace rm $M`,
        `marketplace remove "$(echo m)"`, and any name with a malformed
        `installed_plugins.json`;
      - `test_other_plugin_commands_pass` — `disable other@m`, `uninstall other@m`,
        `marketplace remove other-m` (install state lists only `pipeline@wcz-tools`),
        `claude plugin list`, `details pipeline`, `validate plugin/`, `eval plugin/`,
        `update pipeline@wcz-tools --scope user`, `install pipeline@wcz-tools --scope user`,
        `i pipeline@wcz-tools`, `enable pipeline@wcz-tools`, `marketplace add x`,
        `marketplace list`, `marketplace update wcz-tools`, `claude plugin disable --help`,
        `claude plugin uninstall pipeline@m -h`, `claude plugins remove pipeline@m --help`,
        `claude plugin marketplace rm wcz-tools --help`, `claude plugin help disable`,
        `claude -p 'say hi'`.
      Verification: `uv run pytest -q plugin/tests/test_guard_detach.py plugin/tests/test_guard.py`

- [ ] 4. **Guard: its own directory and the install state** — files: `plugin/bin/guard.py`,
      `plugin/tests/test_guard_own_files.py` (new).
      Implement per Approach → The guard's own files. Tests (a fake plugin root under
      `tmp_path` with `bin/guard.py` and `hooks/hooks.json`, passed as
      `CLAUDE_PLUGIN_ROOT`; `CLAUDE_CONFIG_DIR` under `tmp_path`):
      - `test_writing_the_plugin_directory_is_refused` — parametrized: `sed -i 's/a/b/'`,
        `perl -i -pe 's/a/b/'`, `tee`, `mv /dev/null`, `cp /dev/null`, `truncate -s 0`,
        `chmod -x`, `ln -sf /dev/null`, `echo x >`, `echo x >>`, `git checkout --`,
        `git restore` onto `<root>/bin/guard.py` and `<root>/hooks/hooks.json`; also
        `cd <root> && sed -i s/a/b/ bin/guard.py`, `P=<root>; tee $P/bin/guard.py`,
        `cp /dev/null <root>/bin/*`, `mv <root>/.. /tmp/x`; reason holds "guardrail files";
        plus `cp x <root>/bin/guard.py`, `cp -t <root>/bin x`,
        `install -m 755 x <root>/bin/guard`, `ln -sf /dev/null <root>/bin/guard.py`,
        `dd if=/dev/null of=<root>/bin/guard.py`;
      - `test_reading_the_plugin_directory_passes` — `cat`, `grep -n x`, `sed -n 1p`,
        `cp <tmp>/x <tmp>/y` next to it, `diff` on those files;
      - `test_copying_out_of_the_plugin_passes` (B1) — the `/pipeline:init` shapes:
        `cp <root>/templates/pre-push scripts/git-hooks/pre-push`,
        `cp -r <root>/templates/docs docs`, `cp $CLAUDE_PLUGIN_ROOT/templates/x y`,
        `cat <root>/templates/x > y`, `ln -s <root>/bin/guard.py <tmp>/link`;
      - `test_descriptor_redirects_inside_the_plugin_pass` (M1) — `cd <root> && ls 2>&1`,
        `cd <root> && git status >&2`, `cd <root> && cat x 2>/dev/null`;
      - `test_the_running_guards_own_directory_is_guarded` — no `CLAUDE_PLUGIN_ROOT`:
        `sed -i s/a/b/ <BIN>/guard.py` (the working tree's real guard; evaluated, never
        run) is refused;
      - `test_a_plugin_dir_clone_inside_the_project_is_guarded` —
        `CLAUDE_PLUGIN_ROOT=<repo>/plugin`, `sed -i s/a/b/ plugin/bin/guard.py` refused;
      - `test_writing_the_install_state_is_refused` — the same writes on
        `<config>/plugins/installed_plugins.json` and `known_marketplaces.json`, via the
        absolute path and via `$CLAUDE_CONFIG_DIR/plugins/…`;
      - `test_reading_the_install_state_passes` — `cat`, `grep`, `python3 -m json.tool`
        on them.
      Verification: `uv run pytest -q plugin/tests/test_guard_own_files.py plugin/tests/test_guard.py`

- [ ] 5. **Guard: `gh api` writes on the owner's ground** — files: `plugin/bin/guard.py`,
      `plugin/tests/test_guard_api_writes.py` (new).
      Implement per Approach → `gh api` writes. Tests:
      - `test_a_write_on_the_owners_ground_is_refused` — every AC13 example verbatim, and
        parametrized endpoints × methods (`-X POST`, `--method PUT`, `-XPATCH`,
        `--method=patch`): `repos/o/r`, `repositories/1`, `orgs/o`, `repos/o/r/topics`,
        `repos/o/r/transfer`, `repos/o/r/actions/secrets/T`, `repos/o/r/actions/variables/V`,
        `repos/o/r/environments/prod`, `repos/o/r/hooks`, `repos/o/r/keys`,
        `repos/o/r/collaborators/u`, `repos/o/r/invitations/1`, `repos/o/r/pages`,
        `repos/o/r/vulnerability-alerts`, `repos/o/r/private-vulnerability-reporting`,
        `repos/o/r/actions/permissions`, `repos/o/r/rulesets`,
        `repos/o/r/branches/main/protection`, `orgs/o/teams`, `orgs/o/members/u`,
        `orgs/o/actions/secrets/T`; the reason holds "owner's call" and the endpoint;
      - `test_ordinary_writes_and_reads_pass` — every `GET` of those endpoints (explicit and
        implicit), `gh api -X POST repos/o/r/actions/runs/1/rerun`,
        `gh api -X POST repos/o/r/issues/1/comments -f body=x`,
        `gh api -X POST repos/o/r/issues/1/comments -f body='see the secrets page'`,
        `gh api -X PATCH repos/o/r/pulls/1 -f title=x`, `gh api -X POST repos/o/r/labels -f
        name=x`, `gh api -X POST repos/o/r/issues -f title=x`, `gh api -X POST
        repos/o/r/releases -f tag_name=v1`, `gh api -X POST repos/o/r/deployments -f ref=x`;
        (M2) `gh api -X POST repos/o/pages/issues/1/comments -f body=x`,
        `gh api -X POST repos/hooks/r/labels -f name=x`,
        `gh api -X PATCH repos/o/r/git/refs/heads/fix/hooks -f sha=x`,
        `gh api -X POST repos/{owner}/{repo}/issues/1/comments -f body=x`;
        and refused alongside: `gh api -X PATCH repos/{owner}/{repo} -f visibility=public`;
      - `test_a_write_on_a_variable_endpoint_is_refused` — `gh api -X PATCH "$EP" -f x=y`,
        `gh api -X POST repos/o/${R}/topics`, `gh api -f name=x repos/o/$(echo r)`,
        `gh api -X $M repos/o/r`.
      Verification: `uv run pytest -q plugin/tests/test_guard_api_writes.py plugin/tests/test_guard.py`

- [ ] 6. **Deny-table measurement and `GUARD.md`** — files: `plugin/docs/GUARD.md`,
      `plugin/tests/test_guard_own_files.py` (one doc test); measurement log into this
      plan's Results.
      a) Measure before adding a row (method of the 2026-09-21 decision row, with the
      command run against an isolated `CLAUDE_CONFIG_DIR`). In the scratchpad: a sandbox
      `git init` repository, an empty `<S>/config`, and `<S>/stub/claude`:
      `#!/bin/sh` + `CLAUDE_CONFIG_DIR=<S>/config exec <absolute path of the real claude> "$@"`
      (`chmod +x`). Every nested run: `cd <S>/repo && PATH=<S>/stub:$PATH <real claude> -p
      --safe-mode --max-turns 3 --settings '<json>' 'Run exactly this Bash command, nothing
      else, and report its output verbatim: <command>'`. Probe first, with
      `allow: ["Bash(claude *)"]` and command `claude plugin list`: the output must show the
      **isolated, empty** state; if it lists the owner's plugins, stop — do not run any
      measured command — and escalate. Then, for each candidate, one run with
      `allow: ["Bash(claude *)"]` only and one with the rule added to `deny`:
      `claude plugins uninstall pipeline@wcz-tools` vs `Bash(claude plugin uninstall*)`;
      `claude plugin marketplace rm wcz-tools` vs `Bash(claude plugin marketplace remove*)`;
      control `claude plugin uninstall pipeline@wcz-tools` vs `Bash(claude plugin
      uninstall*)` (must be denied — proves `--settings` took effect). Record per run: ran
      (the CLI's own "not found" output) or denied. Afterwards the real `claude plugin list`
      still shows `pipeline@wcz-tools` at `user` scope. A candidate the rule catches is left
      out of the table. If the nested session cannot run at all (login, sandbox), escalate:
      AC17 cannot be proven otherwise.
      b) `GUARD.md`: *The command guard* → **Covers** names `protectedBranches` (configured
      names treated like `main`), detaching the plugin, the plugin's own directory wherever
      it lies and the install state as guardrail files; a new bullet **`gh api` writes**
      beside the `DELETE` one (the ground, runs/releases/deployments/comments/labels/
      issues/pulls open, endpoint-only matching, variable endpoint refused);
      *The pre-push hook* says it does not read `protectedBranches` (it binds the owner,
      who moves a channel by a direct push). *Deny rules versus the guard*: the measured
      rows appended; a second measurement sentence "Measured on <date> with Claude Code
      <version> (…isolated CLAUDE_CONFIG_DIR…)" for them; the closing paragraph no longer
      names `claude plugin uninstall` or a release-channel push as `deny` territory (its
      example becomes `gh pr merge`/`claude plugin enable`). *Known limits*: the "Only
      `main` and `master` …" bullet removed; added: `protectedBranches` takes exact names,
      binds agent sessions only (the pre-push hook refuses only `main`/`master`, so the
      owner's direct push to a channel such as `stable` passes — keeps the token `stable`
      that `test_guard_md_names_the_known_limits` requires), release tags unprotected;
      `gh api graphql` mutations (`updateRepository`) unchecked; a nested session
      (`claude -p --safe-mode`, `--dangerously-skip-permissions`, `--bare`) runs without
      this session's hooks — deliberate evasion, beside interpreters; a write target built
      from an unknown variable is not resolved against the plugin directory; `gh`'s own
      `{branch}` placeholder in a write endpoint (`…/git/refs/heads/{branch}`) is resolved
      by `gh` from the current branch, so the guard cannot see it names a protected branch
      (plan review, m4 — the rulesets stand behind `main`, nothing behind a configured
      channel).
      `test_guard_md_covers_the_0_4_0_rules`: tokens `protectedBranches`,
      `installed_plugins.json`, `gh api graphql`, `nested`, and "Only `main` and `master`"
      absent.
      Verification: `uv run pytest -q plugin/tests/test_guard.py plugin/tests/test_guard_own_files.py && git diff --exit-code origin/main -- plugin/tests/test_guard.py && ! grep -n "Only \`main\` and \`master\`" plugin/docs/GUARD.md`

- [ ] 7. **README guard section and init** — files: `plugin/README.md` (*Command guard*),
      `plugin/skills/init/SKILL.md`, `plugin/tests/test_init_skill.py`.
      The *Command guard* paragraph names `protectedBranches`, detaching the plugin, the
      plugin's own files and install state, and `gh api` writes (the Alembic sentence and
      its tokens stay). Init: the clause from Approach; test
      `test_init_does_not_write_protected_branches` (`"protectedBranches"` in `step(4)`).
      Verification: `uv run pytest -q plugin/tests/test_readme.py plugin/tests/test_init_templates.py plugin/tests/test_init_skill.py plugin/tests/test_no_domain_references.py && git diff --exit-code origin/main -- scripts/git-hooks/pre-push plugin/templates/pre-push`

- [ ] 8. **Install guide, `CLAUDE.md`, conventions** — files: `plugin/docs/INSTALL.md`,
      `CLAUDE.md`, `docs/CONVENTIONS.md`, `plugin/tests/test_readme.py`,
      `tests/test_documents.py`.
      INSTALL: one note where `uninstall`/`marketplace remove` first appear (and in
      *Switching it off* if it names `disable`): from 0.4.0 the guard refuses `claude
      plugin uninstall`, `disable` and `marketplace remove` of this plugin inside an agent
      session — the owner runs them in a terminal; the `stable` paragraph says the guard
      keeps agents off it through `protectedBranches` (not `deny` rules).
      `CLAUDE.md` Git section, "moving `stable`" bullet: the guard refuses it through
      `"protectedBranches": ["stable"]` in `.claude/workflow.json`, and refuses detaching
      the plugin; `deny` stays for `gh pr merge` and `claude plugin enable`.
      `docs/CONVENTIONS.md` release bullet: "an agent is kept off it by the guard
      (`protectedBranches`), like tagging by agreement". Tests:
      `test_install_guide_leaves_detaching_to_the_owners_terminal` (INSTALL holds
      "terminal" and "agent session" and "refuse"); `test_claude_md_and_conventions_name_protected_branches`
      (both hold `protectedBranches`; neither says `stable` is kept off by `deny` rules —
      assert absent in both files: "kept off it by `deny` rules" (CONVENTIONS' wording),
      "`deny` rules on `git push` to" and "the guard protects `main`/`master` only"
      (CLAUDE.md's wording, lines 89–91 today — plan review, m2)).
      Verification: `uv run pytest -q plugin/tests/test_readme.py tests/test_documents.py`

- [ ] 9. **Decisions, backlog, roadmap** — files: `docs/DECISIONS.md`, `docs/BACKLOG.md`,
      `docs/ROADMAP.md`.
      DECISIONS: four rows dated today, appended — (1) `protectedBranches` additive to
      `main`/`master`, exact names, guard-only, why `pre-push` does not read it (binds the
      owner, who moves the channel by direct push); (2) detaching refused by target (this
      plugin by name, no name, `--all`; its marketplaces from install state, cache layout,
      enclosing `marketplace.json`; unresolved refused), `update`/`install`/`enable` pass;
      (3) the running guard's own directory wherever it lies and the install-state files
      as guardrail files (path-based, beside the 0.3.4 regex); (4) `gh api`
      `POST`/`PUT`/`PATCH` on the owner's ground by endpoint segment, runs/releases/
      deployments open, the deny-table measurement through a `claude` stub with an isolated
      `CLAUDE_CONFIG_DIR`. BACKLOG: remove the `gh api` repository-endpoint row; add P3
      rows (Guard): branch patterns in `protectedBranches`; protecting release tags; `claude
      plugin enable|install --scope project` duplicate (the `deny` rule stays); `gh api
      graphql` mutations — triggers verbatim from the SPEC's Out of scope. The existing
      Guard row on `gh api -X DELETE` keyword matching gains one clause: writes match
      keywords only after the `repos/<o>/<r>` / `orgs/<o>` prefix and never under
      `git/refs` (plan review, M2). ROADMAP: tick both Stage 5 0.4.0 items (links already
      point at this spec).
      Verification: `test "$(grep -c '^| 20' docs/DECISIONS.md)" -ge "$(( $(git show origin/main:docs/DECISIONS.md | grep -c '^| 20') + 4 ))" && ! grep -n 'gh api. write calls on the repository endpoint' docs/BACKLOG.md && for t in protectedBranches graphql 'release tag' '--scope project'; do grep -q -e "$t" docs/BACKLOG.md || { echo "missing: $t"; exit 1; }; done && test "$(grep -c '\[x\] 0.4.0' docs/ROADMAP.md)" -ge 2 && ! grep -n '\[ \] 0.4.0' docs/ROADMAP.md && uv run pytest -q tests/test_documents.py`

- [ ] 10. **0.4.0 release readiness** — files: `plugin/.claude-plugin/plugin.json`,
      `plugin/CHANGELOG.md`.
      Version `0.4.0`; `## 0.4.0` section above `## 0.3.4` with a one-paragraph summary and
      `**consumer impact:**` — agent sessions can no longer disable, uninstall or remove the
      plugin's marketplace, edit the plugin's files or install state from the shell, or
      write repository settings through `gh api` (the ground listed); a consumer adds
      `protectedBranches` to protect a release channel; an older plugin reading a config
      with the key only warns. Then `### Added` bullets per rule.
      Verification: `uv run pytest -q plugin/tests/test_readme.py && bash scripts/check.sh`

- [ ] 11. **This repository's configuration — last implementation step** — files:
      `.claude/workflow.json`, `.claude/settings.json`, `tests/test_documents.py`.
      With the Edit tool (both are on the `ask` list; if the permission prompt cannot be
      answered in this session, escalate with the exact diff — do not work around it):
      `"protectedBranches": ["stable"]` in `workflow.json`; from `settings.json` remove the
      six `git push … stable` rules (`*:stable*`, `*/heads/stable*`, `* stable`,
      `* stable *`, `* 'stable'*`, `* "stable"*` — the SPEC says seven; the file holds
      six, all go), `claude plugin disable*`, `uninstall*`, `remove*`,
      `marketplace remove*`; keep `Bash(gh pr merge*)` and `Bash(claude plugin enable*)`.
      Test `test_repository_settings_leave_stable_and_detaching_to_the_guard`: `deny` ==
      `["Bash(gh pr merge*)", "Bash(claude plugin enable*)"]` and `workflow.json`
      `protectedBranches == ["stable"]`.
      Verification: `python3 plugin/bin/workflow_config.py --check && uv run pytest -q tests/test_documents.py && python3 -c "import sys;sys.path.insert(0,'plugin/bin');import guard,os;from pathlib import Path;r=guard.evaluate('git push origin HEAD:stable',Path.cwd(),dict(os.environ));print(r);assert r and 'pushing to stable' in r" && bash scripts/check.sh`

### After gate 2 (final-review apply mode, not the implementer)

- AC25: after the gate-2 fixes, `bash scripts/eval.sh` (full suite, default model) and
  commit `plugin/evals/last-run.json` as the PR's last commit; any later change under
  `plugin/` means running it again.
- AC26: the PR description carries this checklist for the owner's 0.4.0 canary:
  1. inside the canary session `command -v workflow_metrics.py` points into
     `<clone>/plugin/bin`, and no other `pipeline` is on `$PATH` (SPEC 004 D4);
  2. `grep -E 'Found [0-9]+ plugins' <log>` equals a plain session in the same consumer;
  3. `claude plugin uninstall pipeline@no-such-marketplace` is refused by the guard;
  4. with `protectedBranches` set in the consumer,
     `git push --dry-run origin HEAD:<protected branch>` is refused by the guard.

## Risks and traps

- **Over-refusal of the path rule — not only in `--plugin-dir` sessions.** The guard's
  own directory is the plugin root in *every* consumer, and skills read from it:
  `/pipeline:init` copies templates with `cp ${CLAUDE_PLUGIN_ROOT}/templates/…`. Judging
  `cp`'s source as a write (as the 0.3.4 regex does for an inside-project plugin) would
  break init everywhere and fail the `init-*` eval cases of the AC25 receipt — hence
  destination-only for `cp`/`install`/`ln` and the `test_copying_out_of_the_plugin_passes`
  cases. What stays fail-safe: a relative argument (a `sed` script, a `chmod` mode, a
  `git checkout` branch name) run from a cwd inside the plugin resolves into it and is
  refused.
- **Tests must never read the owner's `~/.claude`.** Every new test that reaches the claude
  rule or the install state sets `CLAUDE_CONFIG_DIR` under `tmp_path`. The deny-table rows
  are refused without any install state (plugin name from `plugin.json`, marketplace from
  the repository's `.claude-plugin/marketplace.json`), so `test_guard.py` stays unchanged
  and deterministic in CI.
- **`test_guard.py` is frozen (AC2).** Its doc tests pin `GUARD.md`: the section headings,
  "Measured on … with Claude Code x.y.z", and the Known-limits tokens including `stable` —
  the new `protectedBranches` limit carries that word.
- **Messages for `main` must not change**, including "main" for `master` pushes; only
  configured names get the new text.
- **`git branch --show-current` returns `""`** on a detached HEAD — empty names are
  dropped from the set.
- **The measurement's isolation.** Probed while planning (2026-09-22, Claude Code 2.1.280):
  `CLAUDE_CONFIG_DIR` alone, or in `--settings` `env`, logs the nested session out; a
  `PATH`-prefixed stub does reach the nested Bash tool. The probe in step 6 must show an
  empty `claude plugin list` before any measured command; without it, an unrouted
  `marketplace rm wcz-tools` would uninstall the plugin in every project. The model may
  rewrite a command (as in 2026-09-21) — such a run counts as not measured, retry once.
- **`ask` rules on `.claude/*.json`.** Step 11's edits may need the owner's click; the
  implementer escalates rather than editing through the shell (which the 0.3.4 guard
  refuses anyway).
- **From step 11 on**, every Bash call of a 0.3.4 session in this repository prints an
  "unknown key `protectedBranches`" warning, and nothing local keeps an agent off `stable`
  until 0.4.0 is installed — accepted in the SPEC's owner decisions.
- **Eval fingerprint.** Any change under `plugin/` after the receipt invalidates it.
- **Language.** New texts are English; the single init clause is Polish because the skill
  is (Stage 8 translates it).

## End-to-end verification

### Automatic (performed by /pipeline:implement)

After step 11, in this repository, feed the hook the way Claude Code does
(`printf '%s' '{"tool_input":{"command":"<cmd>"},"cwd":"'"$PWD"'"}' | python3 plugin/bin/guard.py; echo "exit=$?"`),
expected:

1. `git push origin HEAD:stable` → exit 2, "pushing to stable";
2. `git push origin feat/005-guard-guards-itself` → exit 0;
3. `claude plugins uninstall pipeline@wcz-tools` → exit 2, "install is the owner's to change";
4. `claude plugin marketplace rm wcz-tools` → exit 2;
5. `claude plugin update pipeline@wcz-tools --scope user` → exit 0;
6. `sed -i s/a/b/ plugin/bin/guard.py` with `CLAUDE_PLUGIN_ROOT=$PWD/plugin` in the
   environment → exit 2, "guardrail files";
   and, same environment, `cp plugin/templates/pre-push /tmp/pre-push-copy` → exit 0
   (the `/pipeline:init` copy shape — plan review, B1);
7. `gh api -X PATCH repos/o/r -f default_branch=x` → exit 2;
   `gh api -X POST repos/o/r/issues/1/comments -f body=x` → exit 0;
8. `python3 plugin/bin/workflow_config.py --check` → exit 0;
9. `bash scripts/check.sh` → ALL GREEN.

Record the outputs under Results below.

### Manual (performed by the owner)

- The 0.4.0 canary (after merge, before the tag) with the four checks of AC26.

### Results

_(filled by /pipeline:implement: the step-6 measurement log and the end-to-end outputs)_

## Definition of Done

- [ ] all steps ticked
- [ ] `bash scripts/check.sh` fully green
- [ ] end-to-end verification (automatic) done, results recorded here
- [ ] `docs/ROADMAP.md` updated; `docs/DECISIONS.md`, `docs/BACKLOG.md` updated
- [ ] spec status: `implemented`
- [ ] after gate 2: green eval receipt as the PR's last commit; canary checklist in the PR

## Owner decisions

_(appended by /pipeline:ship or a stage on escalation: date, stage, question, decision)_

## Review log

### 2026-09-22 — /pipeline:plan-review (inside /pipeline:ship)

Anti-anchoring notes taken from the SPEC alone before reading the plan: one protected set
fed from config; a `claude plugin` parser with aliases, `--help` passing and target
resolution from `plugin.json` / install state; a path-based check for the plugin root and
`~/.claude/plugins/*.json`; `gh api` writes by endpoint on the owner's ground with implicit
`POST`; the deny measurement isolated from the owner's install. The plan matches on all
five; the divergences found are in how the path check decides what a command *writes*.

Findings (weights counted before the fixes):

| id | weight | finding | change |
|----|--------|---------|--------|
| B1 | blocker | The path rule reused `touched`, where every `cp` argument — source included — counts. The guard's own directory is the plugin root in *every* consumer, and `plugin/skills/init/SKILL.md` step 4 tells the agent to copy templates with `cp ${CLAUDE_PLUGIN_ROOT}/templates/…`: 0.4.0 would refuse `/pipeline:init` everywhere and likely fail the `init-*` cases of the AC25 receipt. The plan's risk note ("bites only in a `--plugin-dir` session") was wrong. | Approach → own files: `cp`/`install`/`ln` judged by destination only (`-t` value or last positional); new test `test_copying_out_of_the_plugin_passes`; destination cases added to the refused list; E2E check 6 gains the init copy shape; risks and owner summary rewritten. |
| M1 | major | Redirect targets are checked for every program; `2>&1` / `>&2` yield the target `1`/`2`, which the new path check would resolve against the cwd — any `… 2>&1` from a cwd inside the plugin refused. | Descriptor duplications skipped; test `test_descriptor_redirects_inside_the_plugin_pass`. |
| M2 | major | `owner_write` reused `owner_deletion`'s scan of *every* path segment, so the owner/repository name and ref names count: in a consumer repository named `pages` or `hooks` every comment write is refused, and `PATCH …/git/refs/heads/fix/hooks` reads as "webhooks". The DELETE variant is accepted debt (BACKLOG); writes are far more frequent. | Keywords matched only in `rest` after the `repos/…`/`repositories/…`/`orgs/…` prefix, never under `git/refs`; four pass cases and a `{owner}/{repo}` refusal case in step 5; the BACKLOG row gets a clause in step 9. |
| m1 | minor | `dd of=<path>` escaped the path check (the value hides behind `of=`). | `key=value` operands judged by value; a `dd` refusal case. |
| m2 | minor | Step 8's test only asserted CONVENTIONS' phrase absent; CLAUDE.md words it differently ("`deny` rules on `git push` to", "the guard protects `main`/`master` only"). | Both phrases asserted absent too. |
| m3 | minor | Step 9's verification passed with one of four backlog tokens and one of two roadmap ticks (`grep -c` of an alternation). | Per-token loop; `[x] 0.4.0` count ≥ 2 and no `[ ] 0.4.0`. |
| m4 | minor | `gh`'s `{branch}` placeholder in a write endpoint is resolved by `gh`, invisible to the guard — unmentioned. | Known limit added to step 6's GUARD.md list. |
| m5 | minor | Marketplace resolution read the install state first, so the frozen deny-table test (no `CLAUDE_CONFIG_DIR`) would read the owner's real `~/.claude`. | Order: enclosing `marketplace.json` and cache layout first; a hit refuses without reading the install state. |
| m6 | minor | The glob fallback "a guarded root is within the literal prefix" refuses `sed -i … *.py` at a project root holding a `--plugin-dir` clone. | Expand with `glob` first (as `hook_target_exists`); prefix test only when expansion is impossible. |

Checked and found correct (no need to repeat downstream):

- Coverage: every AC1–AC26 has steps and a named test or command; the matrix matches the
  steps (AC11 row updated for the two new tests). AC25/AC26 are correctly left to gate 2.
- AC1/AC2: `load_sections` validates each top-level key alone, so a bad `protectedBranches`
  costs only that key; `check_list` already gives the "`protectedBranches[1]` has to be
  str" message. Keeping `test_guard.py` byte-for-byte unchanged is proven by
  `git diff --exit-code`; its existing plugin-directory tests (lines 911–917) still pass
  under the new rule (their targets resolve outside the guarded roots).
- Protected branches: every `PROTECTED_BRANCHES` use is listed (branch rewrite,
  update-ref/symbolic-ref, current branch, push targets, `gh api` regex); dropping `""`
  and keeping the 0.3.4 texts for `main`/`master` are right.
- Detaching: `unwrap`/`basename`/`bash -c`/`eval` reach a `claude` segment; the option
  list matches the CLI help recorded in the plan; unresolved targets refuse.
- `gh api`: `api_method` already yields implicit `POST`; checking only the endpoint for
  writes (not field values) is right; `/merges?` and protection/rulesets stay covered by
  the unchanged regex.
- Deny measurement: the stub-on-`PATH` isolation with a mandatory empty-`plugin list`
  probe before any measured command is safe (a profile that re-prepends the real `claude`
  is caught by the probe); it meets AC17's intent — the measured command never touches
  the owner's install — and the deviation from the SPEC's wording is flagged in the owner
  summary. The SPEC's "seven" `git push … stable` rules are six in the file; the plan
  removes all of them, matching AC19's intent.
- The init skill clause (AC7) is required: step 4 enumerates the sections it writes from
  the example, which will now show `protectedBranches`.
- Conventions/decisions: new texts English (init clause Polish, as its skill is), tests in
  `plugin/tests`, version bump and CHANGELOG `**consumer impact:**` (tested), DECISIONS
  rows, no runtime dependency, no domain references; `pre-push` untouched per the
  2026-09-22 design. Ordering has no forward dependency; step 11 last, with the `ask`
  escalation spelled out.
- Owner summary flags: no new dependency, no data migration — consistent with the SPEC's
  owner decisions.

Decision: `plan-approved` — the one blocker and both majors were fixable inside the plan
and are fixed, no SPEC gap needs the owner, and nothing triggers a dependency or
migration escalation.

## Deviations

_(filled by /pipeline:implement — every deviation from the plan with its rationale)_

## Final review

_(filled by /pipeline:final-review)_
