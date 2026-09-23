# PLAN 007 — Stages read their templates and the section map at run time

## Owner summary

- **Approach:** the section map moves verbatim into `plugin/templates/sections.md`; the
  six stage skills gain one identical `## Mapa sekcji` block that says to `Read`
  `${CLAUDE_PLUGIN_ROOT}/templates/sections.md` before looking for a section and to stop
  (`RESULT: ESCALATE` / STOP) naming the file and the missing rule when a read fails; `idea`
  and `plan` drop their inline templates and `Read` the one file for the current
  `language`. The guard gains a once-per-session notice, delivered as hook JSON
  (`systemMessage` for the owner, `additionalContext` for the model — measured below), when
  no user, project or project-local settings file holds a `Read` rule covering the
  plugin's directory. The rule goes into `templates/settings.json`, `init`, this
  repository's settings, `INSTALL.md`, the canary procedure and every stage eval scaffold.
- **Main risks:** the eval harness may ignore a scaffold's `.claude/settings.json`
  (untrusted workspace) or allow `Read` everywhere — either makes AC12 unmeasurable as
  written and is an escalation, found by a one-run probe before the 5-run measurement;
  editing this repository's `.claude/settings.json` is behind an `ask` rule, so step 9 is
  expected to escalate for the owner to apply a one-line change; eval spend is capped at
  $8.
- **New dependency:** no
- **Data migration:** no — existing consumers add one allow rule by hand (accepted in SPEC
  → "Owner decisions"; announced in the 0.6.0 consumer-impact line)
- **Manual scenarios for the owner:** 1 — see the guard's notice in an interactive
  terminal without verbose mode.

## Approach

### Measurements made while planning (AC8, AC11)

Claude Code 2.1.280, `claude -p --model haiku`, run from this repository (a trusted
workspace), 2026-09-23. Scratch files under the planner's scratchpad; spend $0.14 (not
eval spend).

**AC8 — the hook output channel.** A probe plugin (`--plugin-dir`) with a `PreToolUse:
Bash` hook that exits 0 and prints
`{"systemMessage": "PROBE-USER-7731 …", "hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": "PROBE-MODEL-4412 …"}}`:

| # | where the Bash call ran | `systemMessage` | `additionalContext` |
|---|---|---|---|
| 1 | main session | a `system`/`informational` event, `level: notice`, text `PreToolUse:Bash says: PROBE-USER-7731 …` — the UI notice; the model did **not** see it | seen by the model (quoted verbatim) |
| 2 | a `general-purpose` subagent (Agent tool) | no event in the stream | seen by the subagent's model (quoted verbatim in its report) |

Conclusion: the guard prints one JSON object on stdout carrying the same text in both
fields, exit code 0. `systemMessage` reaches the owner and `additionalContext` reaches the
model of the session or subagent that made the call. A notice raised inside a subagent
reaches its model but was not seen on the owner's side in stream-json; the warn-once
marker is per `session_id`, and under `/pipeline:ship` the orchestrator's own first Bash
call (in the main session, visible to the owner) normally takes it. Stderr with exit code
0 (today's `NO_CONFIG` channel) reaches neither outside verbose mode. On a blocked call
(exit code 2) JSON is ignored, so the notice is appended to the stderr reason instead,
which the model receives.

**AC11 — `Read` of a plugin file by a stage subagent.** A `general-purpose` subagent asked
to `Read` `~/.claude/plugins/cache/wcz-tools/pipeline/0.5.0/templates/PLAN.en.md`:
without a rule it reported the read refused ("I need permission to read the file …");
with `--settings '{"permissions":{"allow":["Read(~/.claude/plugins/cache/wcz-tools/pipeline/**)"]}}'`
it returned the first line `# PLAN NNN — <feature name>` with no prompt. The clone form
(`Read(//…/plugin/**)`) is measured in End-to-end → Automatic, item 3.

### The section map file

`plugin/templates/sections.md`: an English heading and two sentences (what the file is,
that stages read it with `Read` and accept either literal), then the table exactly as it
stands in the README today (same header, same 29 rows, same cell format). The severity
table does **not** move — it has no Polish, stages do not look it up, and it is a contract
like the metric keys; it stays in the README under a new heading `### Severity tokens`.
The README's `### Section map` keeps its heading (the README heading test lists it) but
becomes a short paragraph: the map lives in [templates/sections.md](templates/sections.md),
`idea`/`plan` read `templates/{SPEC,PLAN}.<language>.md`, every stage reads the map with
`Read` at run time, the consumer needs the allow rule
`Read(~/.claude/plugins/cache/<marketplace>/pipeline/**)` (a `--plugin-dir` clone:
`Read(//<clone>/plugin/**)`), a failed read stops the stage, and the guard warns when no
rule covers the plugin. The sentence "nothing is read from the plugin at run time" goes.
After that the README carries no Polish letter at all (AC1).

Tests: `section_map()` moves from `test_readme.py` into `test_templates_language.py` and
parses `TEMPLATES / "sections.md"` (rows are the lines starting with `` | ` `` that have 4
cells; any other cell count under the header fails, as today). `test_language_contract.py`
imports it from there. `test_the_section_map_is_well_formed` moves with it minus the
severity part, which stays in `test_readme.py` reading `### Severity tokens`.
`test_readme_polish_only_in_the_section_map` becomes `test_the_readme_has_no_polish`
(the raw text, not stripped). To prove AC2's "removing a row makes them fail", the parity
checks (`structure`, `occurs`, `unique keys`) are factored into helpers taking the rows,
and `test_the_parity_checks_miss_a_removed_row` drops one row per document
(`owner-decisions` for SPEC, `summary-dependency` for PLAN) and asserts the helpers raise
`AssertionError`.

### The stage skills

One new section, character-identical in all six stage skills, placed right after
`## Język`:

```markdown
## Mapa sekcji

- Zanim poszukasz sekcji w SPEC albo PLAN, wczytaj narzędziem `Read` mapę sekcji
  `${CLAUDE_PLUGIN_ROOT}/templates/sections.md` (klucz → nagłówek polski → angielski).
  Sekcję wskazujesz oboma nagłówkami i przyjmujesz którykolwiek.
- Nieudany odczyt mapy albo szablonu kończy etap — nie zgadujesz nagłówków i nie
  odtwarzasz szablonu z pamięci. Pod `/pipeline:ship`: `RESULT: ESCALATE`; uruchomiony
  samodzielnie: STOP z tym samym komunikatem do właściciela. Komunikat podaje ścieżkę
  pliku i regułę do dopisania w `permissions.allow` (`.claude/settings.json` projektu
  albo ustawień użytkownika): `Read(~/.claude/plugins/cache/<marketplace>/pipeline/**)`,
  a dla klonu z `--plugin-dir` — `Read(//<ścieżka katalogu pluginu bez początkowego />/**)`;
  `<marketplace>` odczytujesz z rozwiniętej ścieżki `${CLAUDE_PLUGIN_ROOT}`
  (`…/plugins/cache/<marketplace>/pipeline/<wersja>`); gdy strażnik pokazał już
  ostrzeżenie z gotową regułą, podajesz tę regułę.
```

(The wording may be tightened in implementation; the pinned tokens are listed in step 2.)
The `## Język` block's first bullet replaces "(mapa sekcji w README pluginu)" with
"(mapa sekcji — sekcja „Mapa sekcji")" in all six, so it stays identical and at three
bullets. The escalation rule lives in the skills, so the stage contract in
`plugin/agents/*.md` and `ship` stays unchanged (it already maps every STOP to
`RESULT: ESCALATE`).

`idea`: `## Szablon SPEC.md` keeps its heading and loses both `### Polski`/`### Angielski`
blocks. New text: the template is read with `Read`, one file for the current `language`:
`pl` → `${CLAUDE_PLUGIN_ROOT}/templates/SPEC.pl.md`; `en`, a missing key or any other value →
`${CLAUDE_PLUGIN_ROOT}/templates/SPEC.en.md`; only that file is read; not translated, not
merged — SPEC has exactly its headings and frontmatter; a failed read → „Mapa sekcji".
Step 4 "według bloku szablonu dla `language`" → "według szablonu wczytanego dla
`language`". `plan`: the same for `PLAN.<language>.md`, keeping "bieżącego `language` — nie
według języka SPEC" and step 5's "nie tłumaczysz" (pinned by
`test_plan_writes_in_the_current_language`); step numbering unchanged (`8. ` is the
closing-step anchor).

### Settings template and `init`

`plugin/templates/settings.json` gains
`"Read(~/.claude/plugins/cache/TODO-marketplace/pipeline/**)"` in `permissions.allow` —
the same placeholder as the `extraKnownMarketplaces` key. `init` step 4's settings bullet:
the marketplace name read from `${CLAUDE_PLUGIN_ROOT}` goes into both the
`extraKnownMarketplaces` key and the `Read` rule (one value); the existing `TODO:`
fallback covers both. `init` itself keeps copying its templates with `cat` (out of scope).

### The guard notice

In `plugin/bin/guard.py`, no new module (the guard is one file plus `workflow_config`):

- `plugin_dir(env) -> Path`: `CLAUDE_PLUGIN_ROOT` when set (the directory the skills'
  `${CLAUDE_PLUGIN_ROOT}` expands to), else `Path(__file__).resolve().parents[1]`. Coverage
  is checked against both its raw absolute form and its `os.path.realpath`.
- `settings_files(env, project) -> list[Path]`: `$CLAUDE_CONFIG_DIR/settings.json` (else
  `~/.claude/settings.json`), `<project>/.claude/settings.json`,
  `<project>/.claude/settings.local.json`; `project` = `CLAUDE_PROJECT_DIR`, else
  `config.root`, else `cwd`.
- `allow_rules(path) -> list[str]`: `read_json` (exists), then `permissions.allow` if it is
  a list of strings; anything else — unreadable file, bad JSON, wrong types — is `[]`
  (AC10).
- `rule_covers(rule, target) -> bool`: `Read` alone covers everything; `Read(<spec>)` with
  `<spec>` starting `~/` (home-relative) or `//` (absolute) is translated to a regex (`**` →
  any characters, `*` → no `/`, `?` → one non-`/`) and full-matched against
  `<target>/templates/sections.md`. Other forms (`/x` is settings-relative, `./x`, `x`) do
  not count — documented as a known limit together with `--settings` and managed policy.
- `suggested_rule(target, env) -> str`: when the target lies under
  `~/.claude/plugins/cache/<m>/<p>/<version>` →
  `Read(~/.claude/plugins/cache/<m>/<p>/**)`; when it lies under
  `$CLAUDE_CONFIG_DIR/plugins/cache/<m>/<p>/<version>` with a config dir outside
  `~/.claude` → `Read(//<config dir without its leading />/plugins/cache/<m>/<p>/**)` (the
  version directory is dropped in both cache forms, so the rule survives a plugin update);
  otherwise (a clone) `Read(//<target without its leading />/**)` — never the single-slash
  form (AC9).
- `READ_RULE` message (English, names the rule and the way out, per CONVENTIONS
  "User-facing text"): `pipeline guard: no Read allow rule covers this plugin's directory
  (<target>), so stages that read its templates and section map will stop — a stage agent
  cannot answer the permission prompt. Add "<rule>" to permissions.allow in
  .claude/settings.json (or ~/.claude/settings.json). A stage that sees this notice
  escalates instead of reading.`
- `warn_once(session_id)` becomes `first_in_session(session_id, marker) -> bool` (same
  exclusive-create marker in `pipeline-guard-<uid>`, markers `<session>.warned` for the
  existing config notice and `<session>.read-rule` for the new one); `NO_CONFIG` keeps its
  stderr channel and text.
- `main()`: the notice is computed only while no marker exists and no rule covers the
  target (three small JSON reads per call until then). Allowed call → exit 0 with one line
  on stdout: `{"systemMessage": <msg>, "hookSpecificOutput": {"hookEventName":
  "PreToolUse", "additionalContext": <msg>}}` — no `permissionDecision`, so the normal
  permission flow is untouched. Blocked call → the notice is appended to the stderr reason,
  exit 2. Any exception inside the notice path is swallowed (fail-open, like the config).

Tests in a new `plugin/tests/test_guard_read_rule.py`, driving `guard.py` as a subprocess
(`run_hook`/`hook_payload` pattern of `test_guard.py`) with an isolated environment: `HOME`
and `CLAUDE_CONFIG_DIR` under `tmp_path`, `CLAUDE_PROJECT_DIR` = a `make_repo` repository,
`CLAUDE_PLUGIN_ROOT` = either a cache-layout directory
`<HOME>/.claude/plugins/cache/mkt/pipeline/0.6.0` (created empty, like
`test_guard_detach.py`) or a clone-like `<tmp>/clone/plugin`.

### Eval scaffolds and the mirror case

The plugin under `claude plugin eval plugin/` loads from this repository's `plugin/`
directory (earlier results show `/home/…/agentic-pipeline/plugin/templates/…`), outside the
eval workspace, so every stage case now needs the clone rule. Each stage-case scaffold
(`implement-escalates-on-failing-test`, `plan-review-escalates-on-dependency`,
`final-review-finds-planted-defect`, `final-review-ignores-false-positive`, and the new
case) writes `.claude/settings.json` = `{"permissions": {"allow": ["Read(//<plugin dir
without leading />/**)"]}}`, the plugin dir resolved from the scaffold's own location
(`cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P`), with `CLAUDE_PLUGIN_ROOT` taking
precedence when the harness sets it. Six identical lines per scaffold (a shared file under
`plugin/evals/` would be collected as a case). A fixture test imports `guard.rule_covers`
and asserts each stage scaffold's rule covers `plugin/`.

New case `plan-review-approves-polish-owner-decision` — the mirror of
`plan-review-escalates-on-dependency`: the same service, `settings.yaml` and fixed-format
rationale, but `.claude/workflow.json` has `"language": "pl"`, SPEC and PLAN use the Polish
headings of `templates/{SPEC,PLAN}.pl.md`, SPEC `## Decyzje właściciela` accepts
`PyYAML==6.0.2` ("nowa zależność PyYAML — zaakceptowana"), and the PLAN's summary says
`**Nowa zależność:** tak — PyYAML, zaakceptowana w SPEC → „Decyzje właściciela"`. The
plan is otherwise complete (AC matrix, verification commands, e2e split, DoD) so approving
is the correct outcome. `case.yaml` and `criteria.md` in English (as the other stage
cases), `runs: 1` after the 5-run measurement (DECISIONS 2026-09-22). Criteria — correct:
reviews the plan, recognises PyYAML as accepted in `## Decyzje właściciela`, does not
escalate on it, ends with status `plan-approved` (fixing minor things in place and a review
log are fine). Incorrect: escalates on the dependency, claims the owner has not accepted it
or that the owner decisions section is missing, leaves the status `plan-draft`, or rewrites
the plan to drop PyYAML.

Rejected: a separate `lib/` scaffold helper (would be collected as a case); passing the
rule through `--allow-tools Read(...)` (AC12 asks for the scaffold to carry it, and the
negative check needs it removable per case).

## AC → steps matrix

| AC | Steps | Proving test |
|----|-------|--------------|
| AC1 | 1 | `test_templates_language.py::test_the_section_map_matches_the_snapshot`; `test_readme.py::test_the_readme_has_no_polish`, `::test_the_section_map_section_links_the_file` |
| AC2 | 1 | `test_templates_language.py::test_template_pairs_have_the_same_structure`, `::test_every_map_row_occurs_in_its_template`, `::test_map_keys_are_unique_per_document`, `::test_the_parity_checks_miss_a_removed_row` |
| AC3 | 2 | `test_language_contract.py::test_idea_and_plan_read_their_template` |
| AC4 | 2 | `test_language_contract.py::test_every_stage_reads_the_section_map` |
| AC5 | 2 | `test_language_contract.py::test_a_failed_read_stops_the_stage` |
| AC6 | 3, 9 | `test_init_templates.py::test_settings_template_allows_reading_the_plugin`; `test_init_skill.py::test_init_fills_the_read_rule_with_the_marketplace`; `tests/test_documents.py::test_repository_settings_allow_reading_the_installed_plugin` |
| AC7 | 4 | `test_guard_read_rule.py::test_no_rule_warns_once_without_blocking`, `::test_a_blocked_first_call_carries_the_notice` |
| AC8 | 4, E2E-A2 | `test_guard_read_rule.py::test_the_notice_reaches_the_owner_and_the_model`; measurement above; E2E automatic 2 |
| AC9 | 4 | `test_guard_read_rule.py::test_a_covering_rule_silences_the_notice` (parametrised: user, config-dir user, project, local × cache `~/` form, clone `//` form, a broader rule, bare `Read`), `::test_a_clone_gets_the_absolute_rule`, `::test_the_cache_gets_the_home_rule`, `::test_a_config_dir_cache_gets_a_version_free_rule`, `::test_a_settings_relative_rule_does_not_count` |
| AC10 | 4 | `test_guard_read_rule.py::test_broken_settings_count_as_no_rule` (bad JSON, unreadable file, wrong types) |
| AC11 | — (measured), E2E-A3 | measurement above (cache); E2E automatic 3 (clone) |
| AC12 | 6, 8 | `test_eval_cases.py::test_polish_mirror_fixture_is_ready_for_the_skill`, `::test_stage_scaffolds_allow_reading_the_plugin`; step 8 ledger (5/5, negative check) |
| AC13 | 6, 8 | step 8 ledger (smoke runs) |
| AC14 | 7 | `test_readme.py::test_changelog_starts_at_the_manifest_version`, `::test_the_changelog_names_the_consumer_impact`, `::test_the_changelog_names_the_read_rule` |
| AC15 | 5 | `test_readme.py::test_install_guide_documents_the_read_rule`; `tests/test_documents.py::test_the_canary_names_the_clone_read_rule` |
| AC16 | 7, 10 | `tests/test_documents.py::test_decisions_record_run_time_reads` ; roadmap tick checked in step 10 |
| AC17 | 10 | `bash scripts/check.sh` |

## Steps

- [x] 1. **Section map into `templates/sections.md`** — files: `plugin/templates/sections.md`
      (new), `plugin/README.md`, `plugin/tests/test_templates_language.py`,
      `plugin/tests/test_readme.py`, `plugin/tests/test_language_contract.py` (import only).
      Per Approach → The section map file. Keep `MAP_SNAPSHOT` as is (it proves the rows
      are unchanged); add `test_the_parity_checks_miss_a_removed_row`,
      `test_the_readme_has_no_polish`, `test_the_section_map_section_links_the_file`
      (`](templates/sections.md)` in `### Section map`, and no `| \`` table row there);
      `HEADINGS` in `test_readme.py` gains `### Severity tokens` after `### Section map`.
      The README section-map paragraph states the rule, the clone rule and the stop on a
      failed read (the guard sentence waits for step 5). `test_init_templates.py` keeps
      importing `POLISH` from `test_readme`.
      Automatic verification: `uv run pytest -q plugin/tests/test_templates_language.py plugin/tests/test_readme.py plugin/tests/test_language_contract.py plugin/tests/test_init_templates.py plugin/tests/test_no_domain_references.py`

- [ ] 2. **Stage skills read the map and their template** — files:
      `plugin/skills/{idea,plan,plan-review,implement,final-review,ship}/SKILL.md`,
      `plugin/tests/test_language_contract.py`.
      Per Approach → The stage skills. Replace
      `test_idea_and_plan_carry_their_templates_pinned_to_the_files` (and the
      `TEMPLATE_BLOCKS`/`BLOCK_HEADINGS`/`inline_template` helpers) with:
      `test_idea_and_plan_read_their_template` — `## Szablon {SPEC,PLAN}.md` names
      `${CLAUDE_PLUGIN_ROOT}/templates/<DOC>.pl.md` and `…/<DOC>.en.md`, `` `Read` `` and
      `` `language` ``, and the line naming `<DOC>.en.md` also states the fallback (a
      missing key and any other value — pin the two phrases the implementation uses, e.g.
      `brak klucza` and `inna wartość`), so AC3's "`en` for a missing or unsupported value"
      is pinned, not only the two paths; the skill has no `markdown` fence and no line equal to a template
      heading other than its own `## ` section headings (e.g. none of `## Cel`, `## Goal`,
      `## Kroki`, `## Steps` as a line in `idea`; for `plan`, `## Kroki` is the skill's own
      section, so check the template-only headings from `sections.md` minus the skill's own
      headings); `test_every_stage_reads_the_section_map` — `## Mapa sekcji` identical in
      the six skills, contains `${CLAUDE_PLUGIN_ROOT}/templates/sections.md` and
      `` `Read` ``, and no skill says `mapa sekcji w README`;
      `test_a_failed_read_stops_the_stage` — the block names `RESULT: ESCALATE`, `STOP`,
      `Read(~/.claude/plugins/cache/<marketplace>/pipeline/**)`, `Read(//` and
      `permissions.allow`, and `## Szablon …` in `idea`/`plan` points to it.
      Keep `test_the_language_block_is_identical_everywhere` green (three bullets) and
      update the comment on `test_sections_are_named_by_both_headings` (no inline English
      template any more).
      Automatic verification: `uv run pytest -q plugin/tests/test_language_contract.py plugin/tests/test_stage_skills.py plugin/tests/test_stage_contract.py plugin/tests/test_no_domain_references.py plugin/tests/test_templates_language.py plugin/tests/test_plugin_structure.py`

- [ ] 3. **Settings template and `init`** — files: `plugin/templates/settings.json`,
      `plugin/skills/init/SKILL.md`, `plugin/tests/test_init_templates.py`,
      `plugin/tests/test_init_skill.py`.
      Per Approach → Settings template and `init`. Tests:
      `test_settings_template_allows_reading_the_plugin` (the allow list holds exactly one
      `Read(~/.claude/plugins/cache/<m>/pipeline/**)` and `<m>` equals the single
      `extraKnownMarketplaces` key); `test_init_fills_the_read_rule_with_the_marketplace`
      (the settings bullet of step 4 names `Read(` and ties it to the same marketplace
      value). Keep `test_the_marketplace_ref_is_the_stable_channel` green.
      Automatic verification: `uv run pytest -q plugin/tests/test_init_templates.py plugin/tests/test_init_skill.py plugin/tests/test_no_domain_references.py`

- [ ] 4. **Guard notice** — files: `plugin/bin/guard.py`,
      `plugin/tests/test_guard_read_rule.py` (new).
      Per Approach → The guard notice. Tests first, then the code. Test list:
      `test_no_rule_warns_once_without_blocking` (exit 0 twice; first stdout is one JSON
      object; second call same `session_id` has empty stdout);
      `test_the_notice_reaches_the_owner_and_the_model` (`systemMessage` and
      `hookSpecificOutput.additionalContext` both hold the exact suggested rule;
      `hookEventName == "PreToolUse"`; no `permissionDecision`);
      `test_a_blocked_first_call_carries_the_notice` (`gh pr merge 1` → exit 2, stderr has
      the block reason and the rule);
      `test_a_covering_rule_silences_the_notice` (parametrised as in the matrix; empty
      stdout); `test_a_clone_gets_the_absolute_rule` (suggested rule is
      `Read(//<clone path without leading />/**)`);
      `test_the_cache_gets_the_home_rule` (`Read(~/.claude/plugins/cache/mkt/pipeline/**)`);
      `test_a_config_dir_cache_gets_a_version_free_rule` (`CLAUDE_CONFIG_DIR` outside
      `HOME`, plugin root `<config>/plugins/cache/mkt/pipeline/0.6.0` → the suggested rule
      is `Read(//<config without leading />/plugins/cache/mkt/pipeline/**)`, no `0.6.0`);
      `test_a_settings_relative_rule_does_not_count` (`Read(/<abs>/**)` in project settings
      still warns); `test_broken_settings_count_as_no_rule` (bad JSON, `chmod 000` — skipped
      when running as root —, `permissions` a list, `allow` a string; exit 0 and the
      notice); `test_the_config_notice_is_unchanged` (no `workflow.json` → the `NO_CONFIG`
      text on stderr, the read notice on stdout, independent markers). Use a fresh
      `session_id` per test (`uuid4`). Check that no existing guard test asserts an empty
      stdout; they keep passing with the real `HOME` (the notice only adds stdout).
      Automatic verification: `uv run pytest -q plugin/tests/test_guard_read_rule.py plugin/tests/test_guard.py plugin/tests/test_guard_detach.py plugin/tests/test_guard_own_files.py plugin/tests/test_guard_protected_branches.py plugin/tests/test_guard_api_writes.py`

- [ ] 5. **Documentation of the rule** — files: `plugin/README.md` (the `### Command guard`
      paragraph: one sentence on the read-rule notice and its two channels),
      `plugin/docs/GUARD.md` (the notice under the command guard; `## Known limits`: a rule
      given only through `claude --settings` or managed policy, and rules in the
      settings-relative `/…` / `./…` forms, are not seen — the notice may be false),
      `plugin/docs/INSTALL.md` (new section `## Reading the plugin's templates` after
      `## Project settings`: the rule in `permissions.allow`, project settings — what
      `/pipeline:init` writes — versus `~/.claude/settings.json`, the absolute clone rule
      `Read(//<clone>/plugin/**)` for a `--plugin-dir` session, what happens without it, the
      guard notice), `docs/CONVENTIONS.md` (canary: the clone rule, and for a headless
      canary through `--settings` the rule goes into that file too),
      `plugin/tests/test_readme.py` (`test_install_guide_documents_the_read_rule`: tokens
      `Read(~/.claude/plugins/cache/`, `Read(//`, `~/.claude/settings.json`,
      `.claude/settings.json`, `--plugin-dir`), `tests/test_documents.py`
      (`test_the_canary_names_the_clone_read_rule`: the `## Releases` section of
      CONVENTIONS contains `Read(//`). No Polish outside code in plugin docs.
      Automatic verification: `uv run pytest -q plugin/tests/test_readme.py tests/test_documents.py`

- [ ] 6. **Eval scaffolds and the Polish mirror case** — files:
      `plugin/evals/{implement-escalates-on-failing-test,plan-review-escalates-on-dependency,final-review-finds-planted-defect,final-review-ignores-false-positive}/scaffold.sh`,
      `plugin/evals/plan-review-approves-polish-owner-decision/{case.yaml,scaffold.sh,graders/criteria.md}`
      (new), `plugin/tests/test_eval_cases.py`.
      Per Approach → Eval scaffolds and the mirror case. The new scaffold follows
      `plan-review-escalates-on-dependency/scaffold.sh` (bare remote, pushed `main`,
      branch `feat/001-deployment-settings`, SPEC in `plan-draft` with a valid `metrics:`
      block). Tests: `test_stage_scaffolds_allow_reading_the_plugin` (for each of the five
      scaffolds, the written `.claude/settings.json` has a `Read` rule for which
      `guard.rule_covers(rule, PLUGIN)` is true — import `guard` from `plugin/bin`);
      `test_polish_mirror_fixture_is_ready_for_the_skill` (`assert_ready_for_the_skill`,
      verify green, `"language": "pl"`); `test_the_mirror_owner_accepted_the_dependency`
      (`## Decyzje właściciela` of SPEC names PyYAML; PLAN `**Nowa zależność:**` starts with
      `tak`; PLAN headings equal those of `templates/PLAN.pl.md` except the H1 title);
      the new case goes into a `MIRROR_CASES` list with `WRONG_BEHAVIOUR`-style tokens
      (`plan-draft`, `escalat`, `PyYAML`) checked on its incorrect paragraph — not into
      `NEW_CASES` (its fixture files are Polish; `case.yaml` and `criteria.md` stay English
      and are checked for no Polish).
      Automatic verification: `uv run pytest -q plugin/tests/test_eval_cases.py`

- [ ] 7. **Version, CHANGELOG, decision** — files: `plugin/.claude-plugin/plugin.json`
      (`0.6.0`), `plugin/CHANGELOG.md` (`## 0.6.0` above `## 0.5.0`: summary; `**consumer
      impact:**` add `Read(~/.claude/plugins/cache/<marketplace>/pipeline/**)` to
      `permissions.allow` in `.claude/settings.json` or user settings, otherwise every stage
      stops on its first read with an escalation naming the rule, and the guard warns once
      per session; `### Added` / `### Changed` / `### Removed` — the inline templates and
      the README map table), `docs/DECISIONS.md` (new 2026-09-23 row: templates and the
      section map are read at run time with `Read` behind a narrow allow rule; reverses the
      2026-09-23 inline-template row; evidence: the AC11 measurement; rejected: inline
      templates, templates as skill reference files, a cache-only guard check, stderr-only
      warning), `plugin/tests/test_readme.py`
      (`test_the_changelog_names_the_read_rule`: the manifest version's section names
      `Read(~/.claude/plugins/cache/`), `tests/test_documents.py`
      (`test_decisions_record_run_time_reads`: a DECISIONS row names `templates/sections.md`
      and `Read(`).
      Automatic verification: `uv run pytest -q plugin/tests/test_readme.py tests/test_documents.py tests/test_release_gate.py && claude plugin validate --strict plugin/`

- [ ] 8. **Eval measurement (AC12, AC13)** — files: this PLAN (ledger under Definition of
      Done results); no plugin change unless a case fails. Commit steps 1–7 first. Every
      call: `claude plugin eval plugin/ --scaffold --allow-tools Bash Write Edit
      --trust-plugin --no-publish --ablation none --json <scratchpad>/<name>.json
      --max-cost-usd <remaining of $8> --case <name> [--runs N]` on the default model
      (drafting on `--model sonnet` allowed, not counted as a pass). Never
      `scripts/eval.sh` (it writes the release receipt — SPEC 008). Never add `Read` to
      `--allow-tools`: that flag is the permission grant (`scripts/eval.sh`: "--allow-tools
      is not implied by --trust-plugin"), while `allowed_tools` in `case.yaml` only makes
      the tool available — granting `Read` on the command line would allow it on every
      path and void the negative check in b).
      a) Probe: the new case, `--runs 1`. Red → read the transcript. If the harness ignores
         the scaffold's `.claude/settings.json` (the read is refused with the rule present)
         → **escalate** (AC12 cannot hold as written); do not move the rule elsewhere.
      b) Negative check: comment out the rule in the new scaffold (working tree only),
         `--runs 1`; expected red (the stage stops on the read). Green → **escalate** (the
         harness allows the read without the rule, so AC12's negative check cannot fail).
         Restore the scaffold (`git diff` clean).
      c) Measurement: the new case `--runs 5` → 5 of 5.
      d) Smoke: `plan-review-escalates-on-dependency`, `implement-escalates-on-failing-test`,
         `final-review-finds-planted-defect`, one run each; one failure of the first is
         re-run once.
      Record per call: case, runs, passes, cost, model, commit; total ≤ $8. A case red
      twice for a product reason → escalate with the transcript excerpt.
      Automatic verification: `python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get('summary') or list(d))" <scratchpad>/<name>.json` for each call, and the ledger in this PLAN lists all four cases green with total spend ≤ 8.00

- [ ] 9. **This repository's settings** — files: `.claude/settings.json` (add
      `"Read(~/.claude/plugins/cache/wcz-tools/pipeline/**)"` to `permissions.allow`),
      `tests/test_documents.py` (`test_repository_settings_allow_reading_the_installed_plugin`).
      Write the test first. The file is behind `Edit(**/.claude/settings*.json)` (`ask`) and
      the guard refuses shell edits of it: try the Edit tool once; refused or waiting →
      **escalate** with the exact one-line change for the owner to apply (not a
      workaround through another tool), then resume at the verification.
      Automatic verification: `uv run pytest -q tests/test_documents.py`

- [ ] 10. **Roadmap and full verification** — files: `docs/ROADMAP.md` (tick the first
      0.6.0 item of Stage 8 with `(specs/007-read-templates-at-run-time/SPEC.md)`; the
      second item unchanged except that its eval case now lands here — say so in one
      clause), then End-to-end → Automatic.
      Automatic verification: `bash scripts/check.sh`

## Risks and traps

- **Untrusted eval workspace.** The SPEC 006 probe found an untrusted workspace ignoring
  its own `permissions.allow`. If the eval harness runs sessions that way, the scaffold's
  rule is dead and AC12 cannot be met as written — step 8a detects it on one run
  (~$1) and escalates.
- **The harness may allow `Read` everywhere** (`allowed_tools: [Read, …]`) — then the
  scaffold rule is redundant and the negative check cannot fail; step 8b escalates rather
  than claiming AC12.
- **Scaffold location.** If the harness copies `scaffold.sh` elsewhere, `BASH_SOURCE`
  does not lead to `plugin/`; the scaffold prefers `CLAUDE_PLUGIN_ROOT` when set. If
  neither works, the fixture test still passes locally but the run fails on the read —
  8a shows it; record as a deviation with the fix.
- **`${CLAUDE_PLUGIN_ROOT}` in skill text** is substituted by Claude Code (README,
  "Workflow metrics"), so the model sees an absolute path; never put the variable in a
  permission rule (not substituted there) or a Bash command (not set in the Bash tool).
- **Guard stdout.** Anything else printed on stdout would corrupt the hook JSON; the
  guard prints only to stderr today — keep it so. JSON on stdout is ignored on exit code
  2, hence the stderr fallback.
- **Warn-once scope.** The marker is per `session_id`; a subagent shares its parent's
  session id (assumed; measured in End-to-end → Automatic, item 2b — if the ids differ,
  a subagent gets its own notice in its model's context and the owner still gets one from
  the main session's first Bash call; record which holds and correct this bullet), so under `/pipeline:ship` the orchestrator's first
  Bash call usually takes the notice. The stage skills' stop rule is the second line of
  defence, so a subagent that never saw the notice still stops on the failed read instead
  of stalling (a refused read is returned, not prompted, in headless runs — measured).
- **Existing guard tests** run with the real `HOME`; the notice adds stdout on the
  developer's machine and in CI. No assertion on empty stdout may be added to them; the
  new tests isolate `HOME` and `CLAUDE_CONFIG_DIR`.
- **`init` eval cases** see the notice too (their workspace has no rule until `init`
  writes one), and so does `guard-blocks-main-push`, whose blocked push now carries the
  notice in the stderr reason. They are not rerun here; SPEC 008's receipt runs every
  case — note all four in the step 8 ledger.
- **Parity test coupling.** `test_language_contract.py` and `test_init_templates.py`
  import from `test_readme.py`; after step 1 `section_map` comes from
  `test_templates_language.py` — a stale import fails at collection, not silently.
- **`test_sections_are_named_by_both_headings`** relied on the inline English template
  being fenced; with no fences left it checks prose only, which is what it meant.
- **Guardrail files.** `guard.py` is edited with the Edit tool (shell edits of the plugin
  directory are refused by the guard itself); `.claude/settings.json` — see step 9.

## End-to-end verification

### Automatic (performed by /pipeline:implement)

1. `bash scripts/check.sh` → `ALL GREEN` (validate plugin and marketplace, ruff, black,
   pytest).
2. Notice on a live session (AC7, AC8): from this repository,
   `claude --plugin-dir plugin -p --model haiku --max-turns 3 --output-format stream-json --verbose 'Run exactly this Bash command: date +%Y. Then quote verbatim any text beginning with "pipeline guard" that you received after running it; if none, say NONE.' < /dev/null > <scratchpad>/notice.jsonl`
   → a `system`/`informational` event whose content holds
   `Read(//home/…/agentic-pipeline/plugin/**)`, and the final `result` quotes the same
   rule. (Neither user nor this repository's settings cover the working-tree plugin, so
   the notice is due.)
2b. Subagent session id (Risks → Warn-once scope): a throwaway probe plugin under the
   scratchpad whose `PreToolUse: Bash` hook appends the payload's `session_id` to a
   scratchpad file; `claude --plugin-dir <probe> -p --model haiku --max-turns 4` with a
   prompt that runs `date` itself and then once more through the Agent tool
   (`general-purpose`). Record whether the two ids are equal and correct the risk bullet.
3. Clone rule (AC11, clone half): in a scratch consumer (`git init` under the
   scratchpad), `claude --plugin-dir <repo>/plugin -p --model haiku --max-turns 4 --output-format json`
   with the prompt "Do not run any tool yourself. Use the Agent tool once (subagent_type
   general-purpose) to Read `<repo>/plugin/templates/sections.md` with the Read tool and
   reply with its first line, or REFUSED and the error." — once without settings
   (expect REFUSED) and once with
   `--settings '{"permissions":{"allow":["Read(//<repo without leading />/plugin/**)"]}}'`
   (expect the first line of `sections.md`). Record both next to the planner's cache
   measurement.
4. Step 8 ledger complete: the mirror case 5/5, the negative check red, three smoke cases
   green, total ≤ $8.

Results (filled in by /pipeline:implement):

### Manual (performed by the owner)

1. In an interactive terminal (not verbose), in any repository whose settings lack the
   rule, start `claude --plugin-dir <repo>/plugin` and ask for one harmless Bash command:
   the guard's notice with the exact `Read(//…/plugin/**)` rule is visible in the
   terminal (stream-json shows it as a UI notice; the rendered TUI cannot be checked
   headless).

## Definition of Done

- [ ] all steps ticked
- [ ] `bash scripts/check.sh` fully green
- [ ] end-to-end verification (automatic) performed, result recorded here
- [ ] `docs/ROADMAP.md` updated; `docs/DECISIONS.md` row added; `plugin/docs/INSTALL.md`,
      `plugin/docs/GUARD.md`, `docs/CONVENTIONS.md` updated
- [ ] spec status: `implemented`

## Owner decisions

_(appended by /pipeline:ship or a stage on escalation: date, stage, question, decision)_

## Review log

### 2026-09-23 — /pipeline:plan-review

Findings (counted before the fixes): 0 `blocker`, 0 `major`, 6 `minor`.

| # | Severity | Finding | Change |
|---|---|---|---|
| R1 | `minor` | `suggested_rule` sent a cache under a non-default `CLAUDE_CONFIG_DIR` to the clone branch, so the suggested `//…/<version>/**` rule would go stale on every plugin update (AC9 "exact rule"). | Approach → The guard notice: a config-dir cache gets a version-free `//…/plugins/cache/<m>/<p>/**`; step 4 gains `test_a_config_dir_cache_gets_a_version_free_rule`; AC9 matrix row lists it and `test_the_cache_gets_the_home_rule`. |
| R2 | `minor` | The stop message asks for `Read(~/.claude/plugins/cache/<marketplace>/pipeline/**)`, but a stage has no source for `<marketplace>` when the guard notice was not in its context. | `## Mapa sekcji` block: `<marketplace>` is read from the expanded `${CLAUDE_PLUGIN_ROOT}` path. |
| R3 | `minor` | AC3's fallback ("`en` for a missing or unsupported value") was not pinned: the planned test checked only the two paths, `Read` and `language`. | Step 2: `test_idea_and_plan_read_their_template` also pins the fallback phrases on the `.en.md` line. |
| R4 | `minor` | Step 8 did not forbid granting `Read` through `--allow-tools`; every stage `case.yaml` lists `Read` in `allowed_tools` (availability), and a command-line grant would void AC12's negative check. | Step 8: explicit "never add `Read` to `--allow-tools`" with the reason. |
| R5 | `minor` | "A subagent shares its parent's session id" was an unmeasured assumption behind the warn-once and owner-visibility reasoning (AC8). | E2E automatic item 2b measures it with a throwaway probe hook; the risk bullet points there. |
| R6 | `minor` | `guard-blocks-main-push` also changes observable output (the notice in the stderr reason of a blocked push) and is not rerun; only the `init` cases were noted. | Risks: the note covers all four unrerun cases for SPEC 008's receipt. |

Checked and found correct (later stages need not repeat this):

- **Coverage:** AC1–AC17 each have steps and a proving test or a recorded measurement; the matrix matches the step list. AC11's cache half is measured and recorded; the clone half is E2E automatic 3.
- **Codebase facts:** the README has Polish only in the section-map rows (so moving the table satisfies AC1's "no Polish letter"); the severity table has no Polish and may stay; all six stage skills reference "mapa sekcji w README" in `## Język`, and no `plugin/agents/*.md` does; the guard prints nothing on stdout today and no guard test asserts on stdout; `warn_once` and `Config.root` exist as described; the stage scaffolds write no `.claude/settings.json` today (a new file, no merge); earlier eval results show the plugin loaded from `/home/…/agentic-pipeline/plugin/`, so the clone rule in the scaffolds is right; `.claude/settings.json` is behind `Edit(**/.claude/settings*.json)` in `ask`, so step 9's planned escalation is real.
- **Conventions and decisions:** standard library only; project-agnostic (`<marketplace>` placeholder, `wcz-tools` only in this repository's settings); version bump and CHANGELOG consumer-impact line; the DECISIONS row reverses the 2026-09-23 inline decision explicitly; the eval policy of 2026-09-22 (5 runs for a new case, default model, `--max-cost-usd`, `runs: 1` afterwards) is followed.
- **Minimality and feasibility:** no step depends on a later one (step 6's fixture test imports `guard.rule_covers` from step 4); the escalation rule lives in the skills, which the stage contract already maps to `RESULT: ESCALATE`; eval budget is realistic (the last receipt cost $3.32 for 8 single runs, about $0.41 a run, against roughly 11 runs here).
- **E2E split:** everything automatable is automatic; the one manual item (TUI rendering of `systemMessage`) cannot be checked headless.
- **Owner summary:** no new dependency, no data migration (the hand-added rule is accepted in SPEC → "Owner decisions"); matches the plan.
- **Language:** the PLAN is in English (`language: en`); the Polish skill block is skill text, not plan prose.

Decision: approved. There is no blocker, no SPEC gap, and no dependency or migration the owner has not accepted; every finding was fixed in the plan.

## Deviations

_(filled in by /pipeline:implement — every deviation from the plan with its rationale)_

- **D1 (step 1)** — the structure check also covers the owner-summary fields
  (`- **Approach:** …`), not only headings. Why: dropping `summary-dependency` from the map
  (the planned proof of AC2) made no parity helper fail, because the structure check saw
  headings only and the occurs check simply ran one row fewer. With the fields in the
  structure, a removed field row fails `key_of`. Test-only; no plugin behaviour change.

## Final review

_(filled in by /pipeline:final-review)_
